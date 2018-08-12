# models.py
from decimal import Decimal
from jsonfield import JSONField
from payments import PurchasedItem
from payments.models import BasePayment
from django.db import models
from django.conf import settings




class Payment(BasePayment):
    items = JSONField()
    def get_failure_url(self):
        return "https://%s/failure/" % settings.TEST_HOSTNAME

    def get_success_url(self):
        return "https://%s/success/?paymentId=%s" % (settings.TEST_HOSTNAME, self.id)

    def get_purchased_items(self):
        if not self.items:
            yield PurchasedItem(name="Dekk", quantity=1, price=120, currency='USD', sku='')
            return
        for item in self.items or []:
            yield PurchasedItem(**item)
