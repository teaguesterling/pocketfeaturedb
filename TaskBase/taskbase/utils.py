from __future__ import absolute_import

import logging


LOG_LEVELS = {logging.getLevelName(level).lower(): level for level in range(10, 60, 10)}


def setdefaults(d, defaults):
    if hasattr(defaults, 'items'):
        defaults = defaults.items()

    for k, v in defaults:
        d.setdefault(k, v)

    return d



class TaskFailure(RuntimeError):
    STATUS_NOT_STARTED = -1
    STATUS_OK = 0
    STATUS_GENERAL_FAILURE= 1
    STATUS_SETUP_FAILURE = 2
    STATUS_INPUT_FAILURE = 3
    STATUS_EMPTY_DATA = 4

    def __init__(self, *args, **kwargs):
        self.reason = kwargs.pop('reason', None)
        self.code = kwargs.pop('code', self.STATUS_GENERAL_FAILURE)
        super(TaskFailure, self).__init__(*args, **kwargs)


class Namespace(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        vals = ', '.join("{0}={1}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "{0}({1})".format(type(self), vals)
