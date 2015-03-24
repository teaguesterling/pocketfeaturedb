from __future__ import absolute_import

import sqlalchemy.orm
from flask.ext.sqlalchemy import *
from flask.ext.sqlalchemy import (
    _BoundDeclarativeMeta,
    _EngineConnector,
    _make_table,
    _QueryProperty,
    _SQLAlchemyState,
)

_WRAPPED_SQLALCHEMY_FUNCS = ('Table', 'relationship', 'relation', 'dynamic_loader')

_OriginalSQLAlchemy = SQLAlchemy
_OriginalBoundDeclarativeMeta = _BoundDeclarativeMeta
_OriginalQueryProperty = _QueryProperty


def _set_default_query_class_to(d, query_cls=BaseQuery):
    if 'query_class' not in d:
        d['query_class'] = query_cls


def _wrap_with_query_class(fn, query_cls=BaseQuery):
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


def _replace_state_object(app, state_fn):
    old_state = app.extensions['sqlalchemy']
    state = state_fn(old_state.db, old_state.app)
    state.connectors.update(old_state.connectors)
    app.extensions['sqlalchemy'] = state
    del old_state
    return state


class PluggableSQLAlchemy(_OriginalSQLAlchemy):
    def __init__(self, app=None,
                 use_native_unicode=True,
                 session_options=None,
                 query_cls=BaseQuery,
                 model_cls=Model,
                 session_cls=SignallingSession,
                 engine_connector_cls=_EngineConnector,
                 state_cls=_SQLAlchemyState,
                 init_session=None,
                 init_query=None,
                 _override_model_query_class=True):

        self.Query = query_cls
        self.ModelBase = model_cls
        self.Session = session_cls
        self._EngineConnector = engine_connector_cls
        self._State = state_cls

        if init_session is None:
            init_session = lambda db, session: session

        if init_query is None:
            init_query = lambda db, query: query

        self._init_session = init_session
        self._init_query = init_query

        if _override_model_query_class and \
                        self.ModeBasel.query_class is not self.Query:
            self.ModelBase.query_class = self.Query

        super(PluggableSQLAlchemy, self).__init__(app=app,
                                                  use_native_unicode=use_native_unicode,
                                                  session_options=session_options)

        # Reset here to undo changes at the end of super __init__
        self.Query = query_cls
        _reinclude_sqlalchemy(self)

    def init_app(self, app):
        super(PluggableSQLAlchemy, self).init_app(app)
        if self._State is not _SQLAlchemyState:
            _replace_state_object(self.app, self._State)

    def init_session(self, session):
        return self._init_session(self, session)

    def init_query(self, query):
        return self._init_query(self, query)

    def make_declarative_base(self):
        model = self.ModelBase
        base = declarative_base(cls=model,
                                name=model.__name__,
                                metaclass=_BoundDeclarativeMeta)
        base.query = _QueryProperty(self)
        return base

    def create_session(self, options):
        options.setdefault('query_cls', self.Query)
        session = self.Session(self, **options)
        session = self.init_session(session)
        return session

    def make_connector(self, app, bind=None):
        return self._EngineConnector(self, app, bind=bind)

