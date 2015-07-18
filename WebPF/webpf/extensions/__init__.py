# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

__author__ = 'Teague Sterling'

from flask.ext.admin import Admin
from flask.ext.bcrypt import Bcrypt
from flask.ext.cache import Cache
from flask.ext.debugtoolbar import DebugToolbarExtension
from flask.ext.login import LoginManager
from flask.ext.migrate import Migrate

from .celery import (
    Celery,
    RequestContextMixin,
)
from .initbroadcast import InitBroadcaster
from .sqla import (
    PluggableSQLAlchemy as SQLAlchemy,
    Query,
    Model,
    Session,
)

from featuredb.admin.auth import AuthenticatedAdminIndexView

admin = Admin(name='FEATUREdb Administration',
              index_view=AuthenticatedAdminIndexView())
bcrypt = Bcrypt()
celery = Celery(task_mixin_cls=RequestContextMixin)
login_manager = LoginManager()
db = SQLAlchemy(query_cls=Query,
                model_cls=Model,
                session_cls=Session)
migrate = Migrate()
cache = Cache()
debug_toolbar = DebugToolbarExtension()

initboradcaster = InitBroadcaster(['featuredb.data'])
