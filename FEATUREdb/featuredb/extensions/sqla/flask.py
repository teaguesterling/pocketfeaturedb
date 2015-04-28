import sqlalchemy
import sqlalchemy.orm

from flask import current_app

from flask.ext.sqlalchemy import *
from flask.ext.sqlalchemy import (
    _BoundDeclarativeMeta,
    _make_table,
    _QueryProperty,
)
from werkzeug.local import LocalProxy

_WRAPPED_SQLALCHEMY_FUNCS = ('Table', 'relationship', 'relation', 'dynamic_loader')

_OriginalSQLAlchemy = SQLAlchemy
_OriginalBoundDeclarativeMeta = _BoundDeclarativeMeta
_OriginalQueryProperty = _QueryProperty

db = LocalProxy(lambda: _get_flask_sqla_db())


def _get_flask_sqla_db():
    if current_app and 'sqlalchemy' in current_app.extensions:
        return current_app.extensions['sqlalchemy'].db
    else:
        return None


def _set_default_query_class_to(d, query_cls=BaseQuery):
    if 'query_class' not in d:
        d['query_class'] = query_cls


def _wrap_with_query_class(fn):
    @functools.wraps(fn)
    def newfn(*args, **kwargs):
        _set_default_query_class_to(kwargs)
        if "backref" in kwargs:
            backref = kwargs['backref']
            if isinstance(backref, string_types):
                backref = (backref, {})
            _set_default_query_class_to(backref[1])
        return fn(*args, **kwargs)

    return newfn


def _reinclude_sqlalchemy(obj, force_overwrite=_WRAPPED_SQLALCHEMY_FUNCS):
    query_cls = getattr(obj, 'Query', BaseQuery)

    # Rewrite if changed by original Flask-SQLAlchemy
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key) or key in force_overwrite:
                setattr(obj, key, getattr(module, key))

    # Note: obj.Table does not attempt to be a SQLAlchemy Table class.
    obj.Table = _make_table(obj)
    obj.relationship = _wrap_with_query_class(obj.relationship, query_cls=query_cls)
    obj.relation = _wrap_with_query_class(obj.relation, query_cls=query_cls)
    obj.dynamic_loader = _wrap_with_query_class(obj.dynamic_loader, query_cls=query_cls)
    obj.event = event


class ExtendedSQLAlchemy(_OriginalSQLAlchemy):
    def __init__(self, app=None,
                 use_native_unicode=True,
                 session_options=None,
                 query_cls=BaseQuery,
                 model_cls=Model,
                 session_cls=SignallingSession,
                 _override_model_query_class=True):
        super(ExtendedSQLAlchemy, self).__init__(app=app,
                                                 use_native_unicode=use_native_unicode,
                                                 session_options=session_options)
        self.Query = query_cls
        self.Model = model_cls
        self.Session = session_cls

        if _override_model_query_class and \
                        self.Model.query_class is not self.Query:
            self.Model.query_class = self.Query

        _reinclude_sqlalchemy(self)


    def make_declarative_base(self):
        model = self.Model
        base = declarative_base(cls=model,
                                name=model.__name__,
                                metaclass=_BoundDeclarativeMeta)
        base.query = _QueryProperty(self)
        return base

    def create_session(self, options):
        return self.Session(self, **options)

