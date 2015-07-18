# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

from __future__ import absolute_import

from .initbroadcast import InitBroadcaster
from .sqla import (
    PluggableSQLAlchemy as SQLAlchemy,
    Query,
    Model,
    Session,
)

__author__ = 'Teague Sterling'

db = SQLAlchemy(query_cls=Query,
                model_cls=Model,
                session_cls=Session)
initboradcaster = InitBroadcaster(['featuredb.data'])
