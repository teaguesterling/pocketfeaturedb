from __future__ import absolute_import

from celery import (
    Celery as OriginalCeleryBase,
    signals,
    _state,
)
from flask import (
    current_app,
    request,
)
from flask.ext.celery import *
from flask.ext.celery import _CeleryState

from .utils import (
    extract_request_environment,
    setup_extracted_request_environment,
)

INJECTED_ENVIRON_KEY = '__flask_celery_request_environ'


class ContextMixin(object):
    def _get_context(self, args, kwargs):
        return None, args, kwargs

    def __call__(self, *args, **kwargs):
        actual_call = super(type(self), self).__call__
        ctx, args, kwargs = self._get_context(args, kwargs)
        if ctx is not None:
            with ctx:
                return actual_call(*args, **kwargs)
        else:
            return actual_call(*args, **kwargs)


class AppContextMixin(ContextMixin):
    app = None

    @classmethod
    def init_app(cls, app):
        cls.app = app

    def _get_context(self, *args, **kwargs):
        app = self.app or current_app
        ctx = None
        if app is not None:
            ctx = app.app_context()
        return ctx, args, kwargs


class RequestContextMixin(AppContextMixin):
    request_environ_key = INJECTED_ENVIRON_KEY

    @classmethod
    def init_app(cls, app):
        super(RequestContextMixin, cls).init_app(app)

        @signals.before_task_publish
        def inject_request_environment(body, **kwargs):
            environ = extract_request_environment(request)
            if environ:
                body['kwargs'][cls.request_environ_key] = environ

    def _get_context(self, args, kwargs):
        app = self.app or current_app._get_current_object()
        request_environ = None
        ctx = None
        if self.request_environ_key:
            request_environ = kwargs.pop(self.request_environ_key, None)
        if app:
            if request_environ:
                environ = setup_extracted_request_environment(request_environ)
                ctx = app.request_context(environ)
            else:
                ctx = app.app_context()
        return ctx, kwargs


class Celery(OriginalCeleryBase):
    def __init__(self,
                 app=None,
                 task_mixin_cls=AppContextMixin,
                 **kwargs):
        self.task_mixin_cls = task_mixin_cls
        self.original_register_app = _state._register_app  # Backup Celery app registration function.
        self._init_kwargs = kwargs
        _state._register_app = lambda _: None  # Upon Celery app registration attempt, do nothing.
        super(Celery, self).__init__()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Actual method to read celery settings from app configuration and initialize the celery instance.
        Positional arguments:
        app -- Flask application instance.
        """
        _state._register_app = self.original_register_app  # Restore Celery app registration function.
        if not hasattr(app, 'extensions'):
            app.extensions = dict()
        if 'celery' in app.extensions:
            raise ValueError('Already registered extension CELERY.')
        app.extensions['celery'] = _CeleryState(self, app)

        # Instantiate celery and read config.
        super(Celery, self).__init__(app.import_name,
                                     broker=app.config.get('CELERY_BROKER_URL'),
                                     **self._init_kwargs)

        # Set result backend default.
        if 'CELERY_RESULT_BACKEND' in app.config:
            self._preconf['CELERY_RESULT_BACKEND'] = app.config['CELERY_RESULT_BACKEND']

        self.conf.update(app.config)  # FIXME: Should this be self.config_from_object
        task_base = self.Task
        task_mixin = self.task_mixin_cls

        # Add Flask app context to celery instance.
        class MixinTask(task_mixin, task_base):
            abstract = True

        if hasattr(MixinTask, 'init_app'):
            MixinTask.init_app(app)

        self.Task = MixinTask
