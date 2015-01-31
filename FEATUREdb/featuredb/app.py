# -*- coding: utf-8 -*-
'''The app module, containing the app factory function.'''
import os

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
    register_blueprints(app)
    register_errorhandlers(app)

    return app


def register_extensions(app):
    debug_toolbar.init_app(app)
    assets.init_app(app)
    cache.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    admin.init_app(app)
    db.init_app(app)
    celery.init_app(app)
    # This should always be last
    initboradcaster.init_app(app)


def register_blueprints(app):
    app.register_blueprint(views.public.blueprint)
    app.register_blueprint(views.users.blueprint)


def register_errorhandlers(app):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template("{0}.html".format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)


