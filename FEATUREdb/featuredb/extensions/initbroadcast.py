from .utils import register_extension

EXT_NAME = 'initbroadcast'


class InitBroadcaster(object):
    def __init__(self, listeners=[], app=None, strict=True):
        self.listeners = []
        self.listeners.extend(listeners)
        self._listeners_modules = self.listeners
        self.strict = strict
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        register_extension(app, EXT_NAME, self)
        self.app = app
        self.listeners = [self.resove_module(listener) for listener in self.listeners]
        for listener in self.listeners:
            if getattr(listener, 'init_app'):
                listener.init_app(app)

    def resolve_listener(self, listener):
        if isinstance(listener, basestring):
            listener = __import__(listener)
        elif callable(listener):
            listener = listener()
        if self.strict and not hasattr(listener, 'init_app'):
            raise ValueError("Could not resolve module from {!r}".format(listener))
        else:
            return listener

