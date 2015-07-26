from __future__ import absolute_import, print_function

import copy
import logging
import os
import sys

from .argtypes import FileType
from .utils import (
    LOG_LEVELS,
    Namespace,
    setdefaults,
    TaskFailure,
)


class Task(object):
    LOG_LEVELS = LOG_LEVELS

    def __init__(self, params=None, conf=None, **kwargs):
        if params is None and kwargs:
            params = self.make_namespace(**kwargs)
        self.params = params
        self.conf = self.fill_conf(conf)

        self._current_task_name = conf.get('task_name', None)

        self.logger = logging
        self.log = None
        self.debug = True

        self.output = None

        self.task_result = None
        self.task_status = TaskFailure.STATUS_NOT_STARTED

    @property
    def current_task_name(self):
        return self._current_task_name or self.task_name()

    @classmethod
    def task_name(cls):
        return cls.__name__

    def setup(self):
        pass

    def load_inputs(self):
        pass

    def execute(self):
        pass

    def produce_results(self):
        pass

    def setup_task(self, params, defaults=None, **kwargs):
        defaults = defaults or Task.defaults(**self.conf)
        self.apply_setup(params, kwargs, defaults, (
            'output',
            'log',
            'log_level',
            'debug',
        ))
        self.logger = logging.getLogger(self.current_task_name)
        self.logger.setLevel(params.log_level.upper())
        if self.log != sys.stderr:
            self.logger.addHandler(logging.StreamHandler(self.log))
            self.logger.propagate = False

    def apply_setup(self, params, overrides, defaults, mappings):
        if hasattr(mappings, 'items'):
            pairs = mappings.items()
        else:
            pairs = zip(mappings, mappings)

        for self_key, param_key in pairs:
            if overrides and param_key in overrides:
                value = overrides[param_key]
            elif params and hasattr(params, param_key):
                value = getattr(params, param_key)
            elif defaults and param_key in defaults:
                value = defaults[param_key]
            else:
                raise self.failed("Could not find {} in params (or overrides, or defaults)".format(param_key),
                                  code=TaskFailure.STATUS_SETUP_FAILURE)
            self.logger.debug("Setting Parameter: {} to {!r}".format(self_key, value))
            setattr(self, self_key, value)

    def generate_output(self, writer, data, destination, message=None, level='info'):
        if destination is not None:
            if message is not None:
                name = getattr(data, 'name', '<stream>')
                notify = getattr(self.logger, level)
                notify(message.format(name))
            writer(data, destination)
        return data

    def failed(self, message, reason=None, code=1):
        self.logger.error(message)
        return TaskFailure(message, code=code, reason=reason)

    def run(self):
        try:
            self.logger.debug("Setting up parameters")
            self.setup()
            self.logger.debug("Loading inputs")
            self.load_inputs()
            self.logger.debug("Executing task")
            self.execute()
            self.logger.debug("Generating output")
            r = self.produce_results()
            self.task_result = r
        except TaskFailure as e:
            self.task_status = e.code
            self.logger.critical("Failure Occurred {!s}".format(e))
            if self.debug:
                raise
        except Exception as e:
            self.task_status = TaskFailure.STATUS_GENERAL_FAILURE
            self.logger.critical("Error Occurred {!s}".format(e))
            if self.debug:
                raise
        else:
            self.task_status = TaskFailure.STATUS_OK
        return self.task_result

    @classmethod
    def task_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('-o', '--output',
                            metavar='OUTPUT',
                            nargs='?',
                            type=FileType.compressed('w'),
                            help='Path to output file [default: <STDOUT>]')
        parser.add_argument('--log',
                            nargs='?',
                            metavar='LOG',
                            type=FileType,
                            help='Path to log errors [default: <STDERR>]')
        parser.add_argument('--log-level',
                            metavar='LEVEL',
                            nargs='?',
                            choices=cls.LOG_LEVELS.keys(),
                            help="Level of information to display from task logger [default: %(default)s]")
        parser.add_argument('--debug',
                            action='store_true',
                            help="Show debugging information on failure [default: %(default)s]")
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
            'log_level': 'WARNING',
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
        environ = environ or os.environ
        conf = {
            'stdin': stdin,
            'stdout': stdout,
            'stderr': stderr,
            'environ': environ,
        }

        if _sys_args:
          conf['task_name'] = args[0]
          args = args[1:]
        else:
          conf['task_name'] = cls.task_name()

        parser = cls.parser(**conf)
        parser = cls.arguments(parser=parser, **conf)
        parser.set_defaults(**cls.defaults(stdin, stdout, stderr, environ))
        params = parser.parse_args(args)
        task = cls.from_namespace(params, conf=conf)
        try:
            task.run()
            status = task.task_status
        except Exception as e:
            task.logger.error(str(e))
            if task.debug:
                raise
            elif task.task_status == TaskFailure.STATUS_OK:
                status = TaskFailure.STATUS_GENERAL_FAILURE
            else:
                status = task.task_status
        return status

    @classmethod
    def create_subtask(cls, parent=None, params=None, conf=None, remap=None, override=None, hide=None, tag=None):
        conf = conf or getattr(parent, 'conf', {})
        params = params or getattr(parent, 'params', Namespace())

        new_params = copy.copy(params)
        new_conf = conf.copy()
        new_conf = cls.fill_conf(new_conf)

        task_name = cls.task_name()
        if parent:
            task_name = '{}.{}'.format(parent.current_task_name, task_name)
        if tag:
            task_name = '{}:{}'.format(task_name, tag)

        conf['task_name'] = task_name

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
        code =  cls.main(args=sys.argv,
                         stdin=sys.stdin,
                         stdout=sys.stdout,
                         stderr=sys.stderr,
                         environ=os.environ,
                         _sys_args=True)

        return code
