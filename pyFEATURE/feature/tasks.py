#!/usr/bin/env python
from __future__ import absolute_import, print_function


import os
import sys

from taskbase import Task

try:
    from feature.backends.wrappers import featurize_points_raw
except ImportError as e:
    def featurize_points_raw(*args, **kwargs):
        raise e



def update_feature_environ_from_namespace(environ, namespace):
    if hasattr(namespace, 'feature_root') and namespace.feature_root is not None:
        environ['FEATURE_ROOT'] = os.path.expanduser(namespace.feature_root)
    if hasattr(namespace, 'feature_dir') and namespace.feature_dir is not None:
        environ['FEATURE_DIR'] = os.path.expanduser(namespace.feature_dir)
    if hasattr(namespace, 'feature_bin') and namespace.feature_bin is not None:
        environ['FEATURE_BIN'] = os.path.expanduser(namespace.feature_bin)
    if hasattr(namespace, 'pdb_dir') and namespace.pdb_dir is not None:
        environ['PDB_DIR'] = os.path.expanduser(namespace.pdb_dir)
    if hasattr(namespace, 'dssp_dir') and namespace.dssp_dir is not None:
        environ['DSSP_DIR'] = os.path.expanduser(namespace.dssp_dir)


def extract_feature_args_from_namespace(namespace):
    args = []
    kwargs = {}
    if namespace.point_file is not None:
        kwargs['P'] = namespace.point_file
    elif namespace.pdb is not None:
        args.append(namespace.pdb)
    if namespace.num_shells is not None:
        kwargs['shells'] = namespace.num_shells
    if namespace.verbose is not None:
        kwargs['verbose'] = namespace.verbose
    if namespace.shell_width is not None:
        kwargs['width'] = namespace.shell_width
    if namespace.exclude_residues is not None:
        kwargs['exclude'] = namespace.exclude_residues
    if namespace.properties is not None:
        kwargs['properties'] = namespace.properties
    if namespace.search_dir is not None:
        kwargs['search_in'] = namespace.search_dir
    return args, kwargs



class Featurize(Task):
    def setup(self, params=None, **kwargs):
        params = params or self.params
        self.setup_task(params, **kwargs)
        self.setup_environ(params)
        self.setup_args(params)
        self.setup_subprocess_kwargs(self.params)

    def setup_environ(self, params):
        new_environ = {}
        base_environ = self.conf.get('enviorn', os.environ).copy()
        update_feature_environ_from_namespace(new_environ, params)
        base_environ.update(new_environ)
        self.featurize_environ = base_environ

    def setup_args(self, params):
        args, kwargs = extract_feature_args_from_namespace(self.params)
        if self.debug:
            args.append('-v')
        self.featurize_args = args
        self.featurize_kwargs = kwargs

    def setup_subprocess_kwargs(self, params):
        self.featurize_kwargs.update(
            environ=self.featurize_environ,
            _out=self.output,
            _err=sys.stderr,
        )
        if self.params.point_file == '-':
            self.featurize_kwargs['_in'] = self.conf.get('stdin', sys.stdin)

    def execute(self):
        try:
            from feature.backends.external import featurize
            featurize(*self.featurize_args, **self.featurize_kwargs)
        except Exception as e:
            if hasattr(e, 'stderr'):
                self.log.write(e.stderr)
            raise self.failed("FEATURIZE subprocess failed ({!s})".format(e), reason=e)

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="Run featurize in a controlled/override-able environment")
        return parser

    @classmethod
    def featurize_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument('pdb',
                                 metavar='PDB',
                                 nargs='?',
                                 default=None)
        input_group.add_argument('-P', '--point-file',
                                 metavar='POINTILE',
                                 nargs='?',
                                 default=None)
        parser.add_argument('-n', '--num-shells',
                            metavar='SHELLS',
                            nargs='?')
        parser.add_argument('-w', '--shell-width',
                            metavar='WIDTH',
                            nargs='?')
        parser.add_argument('-x', '--exclude-residues',
                            metavar='EXCLUDE',
                            nargs='?')
        parser.add_argument('-l', '--properties',
                            metavar='PROPERTYFILE',
                            nargs='?')
        parser.add_argument('-s', '--search-dir',
                            metavar='SEARCH_DIR',
                            nargs='?')
        parser.add_argument('-v', '--verbose',
                            action='store_true')

    @classmethod
    def environment_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('--feature-root',
                            metavar='FEATURE_ROOT',
                            nargs='?')
        parser.add_argument('--feature-dir',
                            metavar='FEATURE_DIR',
                            nargs='?')
        parser.add_argument('--feature-bin',
                            metavar='FEATURE_BIN',
                            nargs='?')
        parser.add_argument('--pdb-dir',
                            metavar='PDB_DIR',
                            nargs='?')
        parser.add_argument('--dssp-dir',
                            metavar='DSSP_DIR',
                            nargs='?')

    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        cls.task_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.featurize_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.environment_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        return parser

    @classmethod
    def featurize_parameters_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            #'num_shells': 6,
            #'shell_width': 1.25,
            'num_shells': None,
            'shell_width': None,
            'exclude_residues': None,  # Default is actually HETATM
            'properties': None,
            'search_dir': None,
            'verbose': False,
        }

    @classmethod
    def featurize_environ_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'feature_root': environ.get('FEATURE_ROOT'),
            'feature_bin': environ.get('FEATURE_BIN'),
            'pdb_dir': environ.get('PDB_DIR'),
            'dssp_dir': environ.get('DSSP_DIR'),
        }

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        defaults = super(Featurize, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        defaults.update(cls.featurize_parameters_defaults(stdin, stdout, stderr, environ, **kwargs))
        defaults.update(cls.featurize_environ_defaults(stdin, stdout, stderr, environ, **kwargs))
        return defaults

if __name__ == '__main__':
    import sys
    sys.exit(Featurize.run_as_script())
