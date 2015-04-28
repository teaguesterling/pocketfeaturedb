#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from flask.ext.migrate import MigrateCommand
from flask.ext.script import (
    Manager,
    Shell,
    Server,
)

from featuredb.app import create_app
from featuredb.data import models

from featuredb.extensions import db
from featuredb.settings import (
    Development,
    Production,
)

if os.environ.get("FEATUREDB_ENV") == 'prod':
    app = create_app(Production)
else:
    app = create_app(Development)

manager = Manager(app)
TEST_CMD = "py.test tests"


def _add_namespace_to_context(namespace, context):
    for name, obj in namespace.__dict__.items():
        context[name] = obj
    return context


def _make_context():
    """Return context dict for a shell session so you can access
    app, db, and the User model by default.
    """
    context = {}
    _add_namespace_to_context(models, context)
    context.update(app=app, db=db)
    return context


@manager.command
def test():
    """Run the tests."""
    import pytest
    exit_code = pytest.main(['tests', '--verbose'])
    return exit_code

manager.add_command('server', Server())
manager.add_command('shell', Shell(make_context=_make_context))
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
