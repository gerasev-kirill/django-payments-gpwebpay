from __future__ import unicode_literals
from django import forms

from payments import PaymentStatus
from . import helpers

GATEWAY_PRCODE_PAYMENT_ERRORS = [
    '11',  # Unknown merchant
    '14',  # Duplicate order number
    '15',  # Object not found
    '17',  # Amount to deposit exceeds approved amount
    '18',  # Total sum of credited amounts exceeded deposited amount
    '25',  # Operation not allowed for user
    '26',  # Technical problem in connection to authorization centre
    '28',  # Declined in 3D
    '30',  # Declined in AC
    '35',  # Session expired
    '50',  # The cardholder cancelled the payment
    '1000',  # Technical problem
]


class ProcessPaymentForm(forms.Form):
    OPERATION = forms.CharField(required=True)
    ORDERNUMBER = forms.CharField(required=True)
    MERORDERNUM = forms.CharField(required=False)
    MD = forms.CharField(required=False)
    PRCODE = forms.CharField(required=True)
    SRCODE = forms.CharField(required=True)
    RESULTTEXT = forms.CharField(required=False)
    USERPARAM1 = forms.CharField(required=False)
    ADDINFO = forms.CharField(required=False)
    DETAILS = forms.CharField(required=False)
    DIGEST = forms.CharField(required=True)
    DIGEST1 = forms.CharField(required=True)

    def __init__(self, merchant_id, signature, payment, **kwargs):
        self.merchant_id = merchant_id
        self.signature = signature
        self.payment = payment
        super(ProcessPaymentForm, self).__init__(**kwargs)

    def clean(self):
        cleaned_data = super(ProcessPaymentForm, self).clean()
        if not self.errors:
            order_id = "%s" % self.payment.id
            if cleaned_data['ORDERNUMBER'] != order_id:
                self._errors['ORDERNUMBER'] = self.error_class(
                    ['Bad payment id (ORDERNUMBER field)'])

            digest = helpers.generate_digest(cleaned_data, [
                'OPERATION', 'ORDERNUMBER', 'MERORDERNUM', 'MD',
                'PRCODE', 'SRCODE', 'RESULTTEXT', 'DETAILS',
                'USERPARAM1', 'ADDINFO'
            ])
            digest1 = "%s|%s" % (digest, self.merchant_id)

            verified = self.signature.verify(
                digest,
                cleaned_data.get('DIGEST', '')
            )
            if not verified:
                self._errors['DIGEST'] = self.error_class(['Bad digest hash'])
            verified = self.signature.verify(
                digest1,
                cleaned_data.get('DIGEST1', '')
            )
            if not verified:
                self._errors['DIGEST1'] = self.error_class(['Bad digest1 hash'])
            if cleaned_data['PRCODE'] in GATEWAY_PRCODE_PAYMENT_ERRORS:
                self._errors['PRCODE'] = "Invalid response code from GpWebPay code '%s' - %s" % (
                    cleaned_data['PRCODE'],
                    cleaned_data.get('RESULTTEXT')
                )
        return cleaned_data

    def save(self, *args, **kwargs):
        if self.cleaned_data['PRCODE'] == '0':
            # all ok
            self.payment.change_status(PaymentStatus.CONFIRMED)
        else:
            self.payment.change_status(PaymentStatus.REJECTED)
