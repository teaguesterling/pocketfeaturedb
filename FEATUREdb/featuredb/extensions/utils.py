from cStringIO import StringIO

from flask import request

EXTENSION_PROPERTY = 'extensions'

def register_extension(app, name, extension, state=None):
    try:
        registry = getattr(app, EXTENSION_PROPERTY)
    except AttributeError:
        registry = {}
        setattr(app, EXTENSION_PROPERTY, registry)
    if state is None:
        state = SimpleAppExtensionState(extension, app, alias=name)
    registry[name] = state
    return state



class SimpleAppExtensionState(object):
    def __init__(self, ext, app, alias=None):
        self.extension = ext
        self.app = app
        if alias is not None:
            setattr(self, alias, ext)


def extract_request_environment(reference_request=None, include_wsgi_input=False):
    this_request = reference_request or request
    if not this_request:
        return None

    environ = this_request.environ.copy()

    if include_wsgi_input and 'wsgi.input' in environ:
        environ['wsgi.input.string'] = environ['wsgi.input'].read()

    for key in ('wsgi.input', 'wsgi.errors', 'werkzeug.request'):
        if key in environ:
            del environ[key]

    return environ


def setup_extracted_request_environment(incoming_environ):
    environ = incoming_environ.copy()

    if 'wsgi.input.string' in environ:
        environ['wsgi.input'] = StringIO(environ['wsgi.input.string'])
        del environ['wsgi.input.string']

    return environ


