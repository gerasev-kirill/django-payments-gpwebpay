# urls.py
from django.conf.urls import include, url
from .views import payment_details
urlpatterns = [
    url('^([0-9]+)/', payment_details),
    url('^failure/', payment_details),
    url('^payments/', include('payments.urls'))
]
