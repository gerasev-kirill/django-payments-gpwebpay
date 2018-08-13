# -*- coding: utf-8 -*-
import django
import sys
import json
import os
from django.conf import settings

SECRET_KEY = '--'
BASE_DIR = os.path.dirname(__file__)
FIXTURE_DIR = os.path.join(BASE_DIR, 'fixtures')
ALLOWED_HOSTS = ['*']

TEST_HOSTNAME = "7e1b539d.ngrok.io"
TEST_SITE_URL = "http://uarm.com.ua/gp/index.php?action=response"

DEBUG = True

INSTALLED_APPS = (
    'django.contrib.sites',
    'payments',

    'tests'
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'db.sqlite3'),
    }
}
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True
    }
]
ROOT_URLCONF = 'tests.urls'

PAYMENT_HOST = 'localhost:8000'
PAYMENT_USES_SSL = True
PAYMENT_MODEL = 'tests.Payment'

with open(os.path.join(FIXTURE_DIR, 'gpwebpay_credentials.json')) as f:
    GPWEBPAY_CREDENTIALS = json.load(f)

GPWEBPAY_CREDENTIALS['sandbox'] = True
GPWEBPAY_CREDENTIALS['use_redirect'] = False


PAYMENT_VARIANTS = {
    'default': ('payments_gpwebpay.GpwebpayProvider', GPWEBPAY_CREDENTIALS)
}
