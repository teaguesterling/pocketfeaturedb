# -*- coding: utf-8 -*-
'''The app module, containing the app factory function.'''

from flask import Flask, render_template

from featuredb import settings
from featuredb.assets import assets
from featuredb.compat import string_types
from featuredb.extensions import (
    admin,
    bcrypt,
    cache,
    celery,
    db,
    debug_toolbar,
    initboradcaster,
    login_manager,
)
from featuredb import views

_DEFAULT_NAME = __name__


def create_app(package_name=_DEFAULT_NAME,
               settings_object=settings.Production,
               settings_override=None):
    '''An application factory, as explained here:
        http://flask.pocoo.org/docs/patterns/appfactories/

    :param config_object: The configuration object to use.
    '''

    if isinstance(settings_object, string_types):
        settings_object = getattr(settings, settings_object.lower().capitalize())

    app = Flask(package_name, )
    app.config.from_object(settings_object)
    app.config.from_pyfile(app.config.get('DRAKE_LOCAL_CONFIG_PATH', None), silent=True)
    app.config.from_envvar(app.config.get('DRAKE_LOCAL_CONFIG_VAR', ''), silent=True)
    app.config.update(settings_override)

    register_extensions(app)

    return app


def register_extensions(app):
    db.init_app(app)
    initboradcaster.init_app(app)



