import six
import OpenSSL
from OpenSSL import crypto


from base64 import b64encode, b64decode


def to_bytes(data):
    if six.PY2:
        return data.encode('utf-8')
    return bytes(data, encoding='utf-8')


def to_str(data):
    if not isinstance(data, six.text_type) and not isinstance(data, six.string_types):
        return "%s" % data
    return data


def generate_digest(query_params, fields):
    digest = []
    for k in fields:
        if k in query_params and query_params[k] not in ['', None]:
            digest.append(query_params[k])
    return '|'.join([
        to_str(d)
        for d in digest
    ])


def add_params_to_url(url, params):
    try:
        import urlparse
        from urllib import urlencode
    except:  # For Python 3
        import urllib.parse as urlparse
        from urllib.parse import urlencode

    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)


class RsaSignature(object):

    def __init__(self, private_key, public_key, passphrase):
        self.private_key = crypto.load_privatekey(
            crypto.FILETYPE_PEM,
            to_bytes(private_key),
            to_bytes(passphrase)
        )
        self.public_key = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            to_bytes(public_key)
        )

    def sign(self, text):
        sign = OpenSSL.crypto.sign(self.private_key, text, "sha1")
        return b64encode(sign)

    def verify(self, data, signature):
        try:
            signature = b64decode(signature)
        except:
            return False
        try:
            OpenSSL.crypto.verify(
                self.public_key,
                signature,
                data,
                "sha1"
            )
            return True
        except crypto.Error:
            return False
