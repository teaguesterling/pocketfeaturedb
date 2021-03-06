from __future__ import print_function

import copy
import logging
import os
import struct
import sys
import time

from pocketfeature.utils.args import (
    FileType,
    setdefaults,
)


class TaskFailure(RuntimeError):
    def __init__(self, *args, **kwargs):
        self.reason = kwargs.get('reason', None)
        self.code = kwargs.get('code', Task.STATUS_GENERAL_FAILURE)
        super(TaskFailure, self).__init__(*args, **kwargs)


class Namespace(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        vals = ', '.join("{0}={1}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "{0}({1})".format(type(self), vals)


# TODO: Move to util module
def ensure_all_imap_unordered_results_finish(result, expected=None, wait=0.5):
    just_started = True
    while True:
        try:
            yield next(result)
            just_started = False
        except StopIteration:
            if (hasattr(result, '_length') and result._length is None) \
              or (expected is not None and result._index < expected):
                time.sleep(wait)
            else:
                raise
        except IndexError:
            if not just_started:
                raise
        except struct.error:
            if not just_started:
                raise


class Task(object):
    STATUS_NOT_STARTED = -1
    STATUS_OK = 0
    STATUS_GENERAL_FAILURE= 1
    STATUS_SETUP_FAILURE = 2
    STATUS_INPUT_FAILURE = 3
    STATUS_EMPTY_DATA = 4

    LOG_LEVELS = dict((k, v) for k, v in logging._levelNames if isinstance(k, str) and v > 0)

    def __init__(self, params=None, conf=None, **kwargs):
        if params is None and kwargs:
            params = self.make_namespace(**kwargs)
        self.params = params
        self.conf = self.fill_conf(conf)

        self.logger = logging
        self.log = None
        self.debug = False

        self.output = None

        self.task_result = None
        self.task_status = self.STATUS_NOT_STARTED

    @classmethod
    def task_name(cls):
        return cls.__name__

    def setup(self):
        pass

    def execute(self):
        pass

    def produce_result(self):
        pass

    def setup_task(self, params, defaults, **kwargs):
        setdefaults(defaults, self.defaults(**self.conf))
        self.apply_setup(params, kwargs, defaults, (
            'output',
            'log',
            'log_level'
            'debug'
        ))
        self.logger = logging.getLogger(self.task_name())
        self.logger.setLevel(params.log_level)
        self.logger.addHandler(logging.StreamHandler(self.log))

    def apply_setup(self, params, overrides, defaults, mappings):
        if hasattr(mappings, 'items'):
            pairs = mappings.items()
        else:
            pairs = zip(mappings, mappings)

        for self_key, param_key in pairs:
            if overrides and param_key in overrides:
                value = overrides[param_key]
            elif params and hasattr(param_key, params):
                value = getattr(params, param_key)
            elif defaults and param_key in defaults:
                value = defaults[param_key]
            else:
                raise self.failed("Could not find {} in params (or overrides, or defaults)".format(param_key),
                                  code=self.STATUS_SETUP_FAILURE)
            setattr(self, self_key, value)

    def generate_output(self, writer, data, destination, exitcode=None):
        if destination is not None:
            writer(data, destination)
        return data

    def failed(self, message, reason=None, code=1):
        self.logger.error(message)
        return TaskFailure(message, code=code, reason=None)

    def run(self):
        try:
            self.setup()
            self.execute()
            r = self.produce_result()
            self.task_result = r
        except TaskFailure as e:
            self.task_status = e.code
            raise
        except Exception as e:
            self.task_status = self.STATUS_GENERAL_FAILURE
            raise
        else:
            self.task_status = self.STATUS_OK
        return self.task_result

    @classmethod
    def task_arguments(cls, stdin, stdout, stderr, environ, task_name, parser=None):
        parser.add_argument('-o', '--output',
                            metavar='OUTPUT',
                            nargs='?',
                            type=FileType.compressed('w'),
                            help='Path to output file [default: STDOUT]')
        parser.add_argument('--log',
                            nargs='?',
                            metavar='LOG',
                            type=FileType,
                            help='Path to log errors [default: STDERR]')
        parser.add_argument('--log-level',
                            metavar='LEVEL',
                            nargs='?',
                            type=lambda level: cls.LOG_LEVELS.get(level, level),
                            choices=cls.LOG_LEVELS.items(),
                            help="Level of information to display from task logger")
        parser.add_argument('--debug',
                            action='store_true',
                            help="Show debugging information on failure")
        return parser

    @classmethod
    def fill_conf(cls, conf=None):
        conf = conf or {}
        conf.setdefault('stdin', sys.stdin)
        conf.setdefault('stdout', sys.stdin)
        conf.setdefault('stderr', sys.stdin)
        conf.setdefault('environ', os.environ)
        conf.setdefault('task_name', cls.task_name())
        return conf

    @classmethod
    def from_namespace(cls, params, conf):
        task = cls(params, conf)
        return task

    @classmethod
    def from_params(cls, conf=None, **kwargs):
        conf = cls.fill_conf(conf)
        namespace = cls.make_namespace(conf=conf, **kwargs)
        task = cls.from_namespace(namespace, conf)
        return task

    @classmethod
    def make_namespace(cls, conf=None, **kwargs):
        conf = cls.fill_conf(conf)
        params = cls.defaults(**conf)
        params.update(**kwargs)
        namespace = Namespace(**params)
        return namespace

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'output': stdout,
            'log': stderr,
            'log_level': 'INFO',
            'debug': False,
        }

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(task_name)
        return parser


    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        return parser

    @classmethod
    def main(cls, args, stdin, stdout, stderr, environ=None, _sys_args=False):
        """
        This is just a simple usage example. Fancy argument parsing needs to be enabled
        """
        conf = {
          'stdin': stdin,
          'stdout': stdout,
          'stderr': stderr,
        }
        if environ is not None:
            conf['environ'] = environ
        else:
            conf['environ'] = os.environ

        if _sys_args:
          conf['task_name'] = args[0]
          args = args[1:]
        else:
          conf['task_name'] = cls.task_name()

        parser = cls.parser(**conf)
        parser = cls.arguments(parser=parser, **conf)
        params = parser.parse_args(args)
        task = cls.from_namespace(params, conf=conf)
        try:
            task.run()
            status = task.task_status
        except Exception:
            if task.debug:
                raise
            elif task.task_status == cls.STATUS_OK:
                status = cls.STATUS_GENERAL_FAILURE
            else:
                status = task.task_status
        return status

    @classmethod
    def create_subtask(cls, parent=None, params=None, conf=None, remap=None, override=None, hide=None):
        conf = conf or getattr(parent, 'conf', {})
        params = params or getattr(parent, 'params', Namespace())

        new_params = copy.copy(params)
        new_conf = conf.copy()
        new_conf = cls.fill_conf(new_conf)

        remap = remap or {}
        override = override or {}
        hide = hide or ()

        for old_key, new_key in remap.items():
            value = getattr(new_params, old_key)
            delattr(new_params, old_key)
            setattr(new_params, new_key, value)

        for new_key, value in override.items():
            setattr(new_params, new_key, value)

        for key in hide:
            delattr(new_params, key)

        task = cls(params=new_params, conf=new_conf)
        task.log = getattr(parent, 'log', conf.get('stderr', sys.stderr))
        task.debug = getattr(parent, 'debug', False)
        task.logger = getattr(parent, 'logger', logging)

        return task

    @classmethod
    def run_as_script(cls):
        try:
            code =  cls.main(args=sys.argv,
                             stdin=sys.stdin,
                             stdout=sys.stdout,
                             stderr=sys.stderr,
                             environ=os.environ,
                             _sys_args=True)
        except TaskFailure as e:
            print("Failure: {0}".format(e), file=sys.stderr)
            raise
        except Exception as e:
            print("Error: {0}".format(e), file=sys.stderr)
            raise

        return code
