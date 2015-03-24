from __future__ import absolute_import

from collections import defaultdict

from flask.ext.sqlalchemy import *
from flask.ext.sqlalchemy import (
    _EngineConnector,
    _SQLAlchemyState,
)
from .pluggable import PluggableSQLAlchemy


class _DynamicState(_SQLAlchemyState):
    def __init__(self, db, app):
        super(_DynamicState, self).__init__(db, app)
        self.dynamic_connectors = defaultdict(dict)


class _DynamicEngineConnector(_EngineConnector):
    def __init__(self, sa, app, bind=None, dynamic=None):
        super(_DynamicEngineConnector, self).__init__(sa, app, bind=bind)
        self._dynamic = dynamic

    def get_uri(self):
        dynamic_overrides = self._app.config.get('SQLALCHEMY_DYNAMIC_BINDS', ())
        if self._dynamic is not None and self._bind in dynamic_overrides:
            dynamic_override = self._dynamic.get_uri(self._app, bind_key=self._bind)
            if dynamic_override is not None:
                return dynamic_override
        return super(_DynamicEngineConnector, self).get_uri()


class DynamicBindMixin(object):
    def get_key(self):
        return None

    def get_uri(self, app=None, bind_key=None):
        return None

    def get_pool_options(self):
        return {}

    def init_session(self, app, session):
        return session

    def init_query(self, query):
        return query


class DynamicSQLAlchemy(PluggableSQLAlchemy):
    def __init__(self, app=None,
                 use_native_unicode=True,
                 session_options=None,
                 query_cls=BaseQuery,
                 model_cls=Model,
                 session_cls=SignallingSession,
                 engine_connector_cls=_DynamicEngineConnector,
                 state_cls=_DynamicState,
                 query_transformers=None,
                 get_dynamic_bind=lambda app: None,
                 _override_model_query_class=True):
        self.get_dynamic_bind = get_dynamic_bind
        if query_transformers is None:
            query_transformers = []
        query_transformers = [self._dynamic_init_query] + list(query_transformers)
        super(PluggableSQLAlchemy, self).__init__(app=app,
                                                  use_native_unicode=use_native_unicode,
                                                  session_options=session_options,
                                                  query_cls=query_cls,
                                                  model_cls=model_cls,
                                                  session_cls=session_cls,
                                                  engine_connector_cls=engine_connector_cls,
                                                  state_cls=state_cls,
                                                  query_transformers=query_transformers,
                                                  _override_model_query_class=_override_model_query_class)

    @property
    def dynamic_bind(self):
        return self.get_dynamic_bind(self.get_app())

    def create_session(self, options):
        session = super(DynamicSQLAlchemy, self).create_session(options)
        dynamic = self.dynamic_bind
        if dynamic:
            session = dynamic.init_session(session)
        return session

    def make_connector(self, app, bind=None, dynamic=None):
        return self.EngineConnector(self, app, bind=bind, dynamic=dynamic)

    def get_engine(self, app, bind=None):
        if bind in app.config.get('SQLALCHEMY_DYNAMIC_BINDS', ()):
            dynamic = self.get_dynamic_bind(app)
        else:
            dynamic = None
        with self._engine_lock:
            state = get_state(app)
            connectors = state.connectors
            if dynamic:
                dynamic_key = dynamic.get_key()
                if dynamic_key:
                    connectors = state.dynamic_connectors.get(dynamic_key)
            connector = connectors.get(bind)
            if connector is None:
                connector = self.make_connector(app, bind=bind, dynamic=dynamic)
                connectors[bind] = connector
            return connector.get_engine()

    def _dynamic_init_query(self, query):
        dynamic = self.dynamic_bind
        if dynamic:
            query = dynamic.init_query(query)
        return query

    def _apply_driver_hacks(self, app, options):
        super(DynamicSQLAlchemy, self)._apply_driver_hacks(app, options)

        # Shimming this in here to avoid changing _EngineConnector logic
        self._apply_dynamic_pool_overrides(app, options)

    def _apply_dynamic_pool_overrides(self, app, options):
        options.update(self.get_dynamic_bind(app).get_pool_options())
