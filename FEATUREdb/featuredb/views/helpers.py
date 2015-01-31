# -*- coding: utf-8 -*-
'''Helper utilities and decorators.'''
import base64
from cStringIO import StringIO

from flask import flash

BASE64_URL_ALTCHARS = '-_'
BASE64_DATA_URL_TPL = 'data:{mimetype};base64,{data}'


def to_base64(decoded, altchars='+/', translation=None, clean=True):
    encoded = base64.b64encode(decoded, altchars=altchars)
    if translation is not None:
        encoded = encoded.translate(translation)
    if clean:
        encoded = encoded.strip().replace('\n', '')
    return encoded


def from_base64(encoded, altchars='+/', translation=None):
    if translation is not None:
        decoded = encoded.translate(translation)
    decoded = base64.b64decode(decoded, altchars=altchars)
    return decoded


def image_to_buffer(img, format='PNG'):
    buf = StringIO()
    img.save(buf, format.upper())
    buf.seek(0)
    return buf


def image_to_data(img, format='PNG', mimetype=None):
    if mimetype is None:
        mimetype = "image/{}".format(format.lower())
    buf = image_to_buffer(img, format)
    encoded = to_base64(buf.getvalue(), clean=True)
    data = BASE64_DATA_URL_TPL.format(mimetype=mimetype, data=encoded)
    return data


def flash_errors(form, category="warning"):
    '''Flash all errors for a form.'''
    for field, errors in form.errors.items():
        for error in errors:
            flash("{0} - {1}".format(getattr(form, field).label.text, error), category)

