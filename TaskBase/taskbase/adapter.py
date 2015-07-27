#!/usr/bin/env python
from __future__ import absolute_import

from taskbase import Task


class BaseTask(Task):

    def setup(self, params=None, **kwargs):
        params = params or self.params
        defaults = self.defaults(**self.conf)
        self.setup_task(params, defaults=defaults, **kwargs)
        self.setup_params(params, defaults=defaults, **kwargs)
        self.setup_inputs(params, defaults=defaults, **kwargs)

    def load_inputs(self):
        pass

    def execute(self):
        pass

    def produce_results(self):
        pass

    def setup_params(self, params, defaults=None, **kwargs):
        pass

    def setup_inputs(self, params, defaults=None, **kwargs):
        pass


    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="")
        return parser

    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        cls.input_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.task_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.parameter_arguments(parser, stdin, stdout, stderr, environ, **kwargs)

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        defaults = super(BaseTask, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        defaults.update(cls.paremeter_defaults(stdin, stdout, stderr, environ, **kwargs))
        return defaults

    @classmethod
    def parameter_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        pass

    @classmethod
    def input_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        pass


    @classmethod
    def paremeter_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {}


if __name__ == '__main__':
    import sys
    sys.exit(BaseTask.run_as_script())
