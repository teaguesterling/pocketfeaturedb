from __future__ import print_function

import os
import struct
import sys
import time


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

    def __init__(self, params):
        self.params = params
        self.output = getattr(params, 'output', sys.stdout)
        self.log = getattr(params, 'log', sys.stderr)

    @classmethod
    def task_name(cls):
        return cls.__name__

    def run(self):
        return 0

    @classmethod
    def from_namespace(cls, params):
        task = cls(params)
        return task

    @classmethod
    def from_params(cls, **kwargs):
        namespace = Namespace(**kwargs)
        task = cls.from_namespace(namespace)
        return task

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(task_name)
        return params

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
          conf['task_name'] = self.task_name()

        parser = cls.arguments(**conf)
        params = parser.parse_args(args)
        task = cls.from_namespace(params)
        return task.run()

    @classmethod
    def run_as_script(cls):
        try:
            return cls.main(args=sys.argv,
                            stdin=sys.stdin,
                            stdout=sys.stdout,
                            stderr=sys.stderr,
                            environ=os.environ,
                            _sys_args=True)
        except Exception as e:
            print("Error: {0}".format(e), file=sys.stderr)
            raise
            return -1
