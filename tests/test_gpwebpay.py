# -*- coding: utf-8 -*-
import hashlib
import hmac
from decimal import Decimal

from django.test import TestCase
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings
from mock import MagicMock, Mock

from .models import Payment
from payments import PaymentStatus
from payments_gpwebpay import GpwebpayProvider, helpers

GPWEBPAY_CREDENTIALS = settings.GPWEBPAY_CREDENTIALS


def get_currency(currencyCode):
    codes = {
        'CZK': 203, 'EUR': 978,
        'USD': 840, 'GBP': 826,
        'PLN': 985, 'HUF': 348,
        'LVL': 428
    }
    return codes[currencyCode.upper()]


def get_getdata_with_sha1(signature, payment, **kwargs):
    order_id = "%s" % payment.id
    data = {
        'MERCHANTNUMBER': GPWEBPAY_CREDENTIALS['merchant_id'],
        'OPERATION': 'CREATE_ORDER',
        'ORDERNUMBER': order_id,
        'MERORDERNUM': order_id,
        'AMOUNT': int(payment.total * 100),
        'CURRENCY': get_currency(payment.currency),
        'DEPOSITFLAG': 0,
        'URL': settings.TEST_SITE_URL,
        'LANG': 'en',
        'MD': "PAYMENT-%s;%s;%s" % (
            payment.id,
            payment.total,
            payment.currency
        ),
    }
    if payment.description:
        data['DESCRIPTION'] = payment.description
    data['PRCODE'] = '0'
    data['SRCODE'] = '0'
    for k, v in kwargs.items():
        data[k] = v

    digest = helpers.generate_digest(data, [
        'OPERATION', 'ORDERNUMBER', 'MERORDERNUM', 'MD',
        'PRCODE', 'SRCODE', 'RESULTTEXT', 'DETAILS',
        'USERPARAM1', 'ADDINFO'
    ])
    digest1 = "%s|%s" % (digest, GPWEBPAY_CREDENTIALS['merchant_id'])
    data['DIGEST'] = signature.sign(digest)
    data['DIGEST1'] = signature.sign(digest1)
    return data


class RsaSignatureTest(TestCase):

    def setUp(self):
        from payments_gpwebpay.helpers import RsaSignature
        self.signature = RsaSignature(
            GPWEBPAY_CREDENTIALS['private_key'],
            GPWEBPAY_CREDENTIALS['public_key'],
            GPWEBPAY_CREDENTIALS['passphrase_for_key']
        )

    def test_sign(self):
        res = self.signature.sign("Hello world!")
        self.assertEqual(
            res,
            helpers.to_bytes(
                "huYW7D7950we5xdr9U1mMV8Q4FgOqgioMDvWbtglZKBivkgXolNnIY+wb6xx3kYXKaR2lIzGW7j8cXDFdlt4OCGkcixaaUCN0V5r4nBz6hpK+BcV9EFtKTV8DScDbMtLm16ziewZR3QsSXQJMDWUHrqZWep+QnM9JwKqPDtxK197Wuz4nmWu5HrSeaV0WK9gGmVDqJIaRJVVq3zvGh6+27sfwR/Xc+27IfgUsaE5Hkb2ZD4jWNUshMyDDBex81UDCd2Lgrk9vkKcdq4Y+oGJWcqBUlRgVajqmm8JktoUSLrcvz4OoOgFsJcbz/wrBfpmc2GngYdcbuO5GEEHgV+DTQ==")
        )

    def test_verify(self):
        res = self.signature.verify(
            "Hello world!",
            helpers.to_bytes(
                "huYW7D7950we5xdr9U1mMV8Q4FgOqgioMDvWbtglZKBivkgXolNnIY+wb6xx3kYXKaR2lIzGW7j8cXDFdlt4OCGkcixaaUCN0V5r4nBz6hpK+BcV9EFtKTV8DScDbMtLm16ziewZR3QsSXQJMDWUHrqZWep+QnM9JwKqPDtxK197Wuz4nmWu5HrSeaV0WK9gGmVDqJIaRJVVq3zvGh6+27sfwR/Xc+27IfgUsaE5Hkb2ZD4jWNUshMyDDBex81UDCd2Lgrk9vkKcdq4Y+oGJWcqBUlRgVajqmm8JktoUSLrcvz4OoOgFsJcbz/wrBfpmc2GngYdcbuO5GEEHgV+DTQ==")
        )
        self.assertEqual(res, True)

        res = self.signature.verify(
            "Hello wrong world!",
            helpers.to_bytes(
                "huYW7D7950we5xdr9U1mMV8Q4FgOqgioMDvWbtglZKBivkgXolNnIY+wb6xx3kYXKaR2lIzGW7j8cXDFdlt4OCGkcixaaUCN0V5r4nBz6hpK+BcV9EFtKTV8DScDbMtLm16ziewZR3QsSXQJMDWUHrqZWep+QnM9JwKqPDtxK197Wuz4nmWu5HrSeaV0WK9gGmVDqJIaRJVVq3zvGh6+27sfwR/Xc+27IfgUsaE5Hkb2ZD4jWNUshMyDDBex81UDCd2Lgrk9vkKcdq4Y+oGJWcqBUlRgVajqmm8JktoUSLrcvz4OoOgFsJcbz/wrBfpmc2GngYdcbuO5GEEHgV+DTQ==")
        )
        self.assertEqual(res, False)


class GatewayTest(TestCase):

    def setUp(self):
        from payments_gpwebpay.helpers import RsaSignature
        self.signature = RsaSignature(
            GPWEBPAY_CREDENTIALS['private_key'],
            GPWEBPAY_CREDENTIALS['public_key'],
            GPWEBPAY_CREDENTIALS['passphrase_for_key']
        )

        Payment.objects.all().delete()
        self.payment = Payment.objects.create(
            variant='default',
            description='Book purchase',
            total=Decimal(120),
            currency='USD',
            billing_first_name='Sherlock',
            billing_last_name='Holmes',
            billing_address_1='221B Baker Street',
            billing_address_2='',
            billing_city='London',
            billing_postcode='NW1 6XE',
            billing_country_code='UK',
            billing_country_area='Greater London',
            customer_ip_address='127.0.0.1'
        )
        self.payment2 = Payment.objects.create(
            variant='default',
            description='Book purchase #2',
            total=Decimal(120),
            currency='USD',
            billing_first_name='Sherlock',
            billing_last_name='Holmes',
            billing_address_1='221B Baker Street',
            billing_address_2='',
            billing_city='London',
            billing_postcode='NW1 6XE',
            billing_country_code='UK',
            billing_country_area='Greater London',
            customer_ip_address='127.0.0.1'
        )
        self.payment3 = Payment.objects.create(
            variant='default',
            description='Book purchase #3',
            total=Decimal(120),
            currency='USD',
            billing_first_name='Sherlock',
            billing_last_name='Holmes',
            billing_address_1='221B Baker Street',
            billing_address_2='',
            billing_city='London',
            billing_postcode='NW1 6XE',
            billing_country_code='UK',
            billing_country_area='Greater London',
            customer_ip_address='127.0.0.1'
        )

    def test_get_hidden_fields(self):
        """GpwebpayProvider.get_hidden_fields() returns a dictionary"""
        provider = GpwebpayProvider(**GPWEBPAY_CREDENTIALS)
        self.assertEqual(type(provider.get_hidden_fields(self.payment)), dict)

    def test_process_data_payment_accepted(self):
        """GpwebpayProvider.process_data() returns a correct HTTP response"""
        self.assertEqual(self.payment.status, PaymentStatus.WAITING)
        request = MagicMock()
        request.GET = get_getdata_with_sha1(
            self.signature,
            self.payment,
            OPERATION='CREATE_ORDER'
        )
        provider = GpwebpayProvider(**GPWEBPAY_CREDENTIALS)
        response = provider.process_data(self.payment, request)
        self.assertEqual(type(response), HttpResponse)
        self.assertEqual(self.payment.status, PaymentStatus.CONFIRMED)

    def test_process_data_payment_rejected(self):
        """GpwebpayProvider.process_data() returns a correct HTTP response"""
        self.assertEqual(self.payment2.status, PaymentStatus.WAITING)
        request = MagicMock()
        request.GET = get_getdata_with_sha1(
            self.signature,
            self.payment2,
            PRCODE='5'  # Missing required field
        )
        provider = GpwebpayProvider(**GPWEBPAY_CREDENTIALS)
        response = provider.process_data(self.payment2, request)
        self.assertEqual(type(response), HttpResponse)
        self.assertEqual(self.payment2.status, PaymentStatus.REJECTED)

    def test_incorrect_process_data(self):
        """GpwebpayProvider.process_data() checks GET signature"""
        self.assertEqual(self.payment3.status, PaymentStatus.WAITING)
        request = MagicMock()
        request.GET = get_getdata_with_sha1(
            self.signature,
            self.payment3
        )
        request.GET['DIGEST'] = 'INVALID'
        provider = GpwebpayProvider(**GPWEBPAY_CREDENTIALS)
        response = provider.process_data(self.payment3, request)
        self.assertEqual(type(response), HttpResponseForbidden)
