from __future__ import print_function

import os
import struct
import sys
import time


class TaskFailure(RuntimeError):
    def __init__(self, *args, **kwargs):
        self.code = kwargs.get('code', -1)
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
    DEBUG = bool(os.environ.get('DEBUG', True))

    def __init__(self, params=None, **kwargs):
        if params is None and kwargs:
            params = self.make_namespace(**kwargs)
        self.params = params
        self.output = getattr(params, 'output', sys.stdout)
        self.log = getattr(params, 'log', sys.stderr)
        self.return_only = False

    @classmethod
    def task_name(cls):
        return cls.__name__

    def apply_setup(self, params, overrides, defaults, mappings):
        for self_key, param_key in mappings.items():
            if param_key in overrides:
                value = overrides[param_key]
            elif hasattr(param_key, params):
                value = getattr(params, param_key)
            elif param_key in defaults:
                value = defaults[param_key]
            else:
                raise AttributeError("Could not find {} in params (or overrides, or defaults)".format(param_key))
            setattr(self, self_key, value)

    def setup(self):
        pass

    def run(self):
        return 0

    def produce_output(self):
        return 0

    def finish_with_output(self, writer, data, destination, exitcode=0):
        if destination is None:
            return data
        else:
            writer(data, destination)
            return exitcode

    def failed(self, message, code=-1):
        self.log(message)
        raise TaskFailure(message, code=code)

    @classmethod
    def from_namespace(cls, params):
        task = cls(params)
        return task

    @classmethod
    def from_params(cls, **kwargs):
        namespace = cls.make_namespace(**kwargs)
        task = cls.from_namespace(namespace)
        return task

    @classmethod
    def make_namespace(cls, **kwargs):
        params = cls.defaults(sys.stdin, sys.stdout, sys.stderr, os.environ)
        params.update(**kwargs)
        namespace = Namespace(**params)
        return namespace

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ):
        return {}

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(task_name)
        return parser

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name, parser=None):
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
        parser = cls.arguments(**conf)
        params = parser.parse_args(args)
        task = cls.from_namespace(params)
        task.setup()
        return task.run()

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
            code = e.code
            if cls.DEBUG:
                raise
        except Exception as e:
            code = -1
            print("Error: {0}".format(e), file=sys.stderr)
            if cls.DEBUG:
                raise

        return code
