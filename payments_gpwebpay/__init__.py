# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import hmac
import six
from django.utils.translation import get_language
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect

from payments.core import BasicProvider
from .forms import ProcessPaymentForm
from .helpers import to_bytes, RsaSignature


def normalize_url(url):
    _url = url.split('?')
    if _url[0][-1] == '/':
        _url[0] = url[:-1]
    return '?'.join(_url)


class GpwebpayProvider(BasicProvider):
    _method = 'get'

    def __init__(self, *args, **kwargs):
        self.merchant_id = kwargs.pop('merchant_id', None)
        self.private_key = kwargs.pop('private_key', None)
        self.public_key = kwargs.pop('public_key', None)
        self.passphrase_for_key = kwargs.pop('passphrase_for_key', None)
        self.use_redirect = kwargs.pop('use_redirect', True)

        self.language = kwargs.pop('language', None)
        self.operation_description = kwargs.pop('operation_description', None)
        sandbox = kwargs.pop('sandbox', True)
        if sandbox:
            self.endpoint = kwargs.pop(
                "endpoint", "https://test.3dsecure.gpwebpay.com/pgw/order.do")
        else:
            self.endpoint = kwargs.pop(
                "endpoint", "https://3dsecure.gpwebpay.com/pgw/order.do")
        self.endpoint = normalize_url(self.endpoint)

        if not self.merchant_id or not self.private_key \
                or not self.public_key \
                or not self.passphrase_for_key:
            raise ValueError(
                "Provide merchant_id, private_key, public_key and passphrase_for_key for GpwebpayProvider!"
            )

        super(GpwebpayProvider, self).__init__(*args, **kwargs)
        if not self._capture:
            raise ImproperlyConfigured(
                'GpWebPay provider does not support pre-authorization.'
            )

        self.signature = RsaSignature(
            self.private_key,
            self.public_key,
            self.passphrase_for_key
        )

    def get_language(self):
        lang = get_language() or self.language or 'en'
        lang = lang.split('-')[0].lower()
        allowed = [
            "ar", "bg", "hr", "cs", "da", "nl", "en", "fi", "fr", "de", "el",
            "hu", "it", "ja", "lv", "no", "pl", "pt", "ro", "ru", "sk", "sl",
            "es", "sv", "uk", "vi"
        ]
        if lang not in allowed:
            return "en"
        return lang

    def get_action(self, payment):
        return self.endpoint

    def get_currency(self, code):
        codes = {
            'CZK': 203, 'EUR': 978,
            'USD': 840, 'GBP': 826,
            'PLN': 985, 'HUF': 348,
            'LVL': 428
        }
        code = code.upper()
        if code not in codes:
            raise ValueError(
                "Currency '%s' is not allowed for GpWebPay provider!" % (
                    code
                )
            )
        return codes[code]

    def get_price(self, price):
        if not price:
            return 0
        return int(price * 100)

    def get_return_url(self, payment, extra_data=None):
        from django.conf import settings
        url = super(GpwebpayProvider, self).get_return_url(
            payment,
            extra_data=extra_data
        )
        if hasattr(settings, 'TEST_SITE_URL'):
            return settings.TEST_SITE_URL
        if hasattr(settings, 'TEST_HOSTNAME'):
            return url.replace('localhost:8000', settings.TEST_HOSTNAME)
        return url

    def get_hidden_fields(self, payment):
        order_id = "%s" % payment.id
        data = {
            'MERCHANTNUMBER': self.merchant_id,
            'OPERATION': 'CREATE_ORDER',
            'ORDERNUMBER': order_id,
            'MERORDERNUM': order_id,
            'AMOUNT': self.get_price(payment.total),
            'CURRENCY': self.get_currency(payment.currency),
            'DEPOSITFLAG': 1,
            'URL': self.get_return_url(payment),
            'LANG': self.get_language(),
            'MD': "PAYMENT-%s;%s;%s" % (
                payment.id,
                payment.total,
                payment.currency
            ),
        }
        if payment.description or self.operation_description:
            data['DESCRIPTION'] = payment.description or self.operation_description

        digest = helpers.generate_digest(data, [
            'MERCHANTNUMBER', 'OPERATION', 'ORDERNUMBER',
            'AMOUNT', 'CURRENCY', 'DEPOSITFLAG', 'MERORDERNUM',
            'URL', 'DESCRIPTION', 'MD'
        ])
        data['DIGEST'] = self.signature.sign(digest)
        return data

    def process_data(self, payment, request):
        form = ProcessPaymentForm(
            self.merchant_id,
            self.signature,
            payment,
            data=request.GET or {}
        )
        if not form.is_valid():
            cleaned_data = getattr(form, 'cleaned_data', None) or {}
            if self.use_redirect:
                url = payment.get_failure_url()
                params = {
                    'errorPrCode': cleaned_data['PRCODE']
                }
                if cleaned_data.get('SRCODE', None):
                    params['errorSrCode'] = cleaned_data['SRCODE']
                if cleaned_data.get('RESULTTEXT', None):
                    params['errorText'] = cleaned_data['RESULTTEXT']
                url = helpers.add_params_to_url(
                    payment.get_failure_url(),
                    params
                )
                return HttpResponseRedirect(url)
            else:
                return HttpResponseForbidden('<PaymentNotification>Rejected</PaymentNotification>')
        form.save()
        if self.use_redirect:
            url = payment.get_success_url()
            return HttpResponseRedirect(payment.get_success_url())
        return HttpResponse('<PaymentNotification>Accepted</PaymentNotification>')
