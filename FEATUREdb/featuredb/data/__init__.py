from featuredb.utils import set_defaults
from . import config


def init_app(app):
    set_defaults(app, config.__dict__)


