from __future__ import print_function

import os
import sys


class Task(object):

    def __init__(self, params):
        self.params = params
        try:
            self.output = params.output
        except AttributeError:
            self.output = sys.stdout
        try:
            self.log = params.log
        except AttributeError:
            self.log = sys.log

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
