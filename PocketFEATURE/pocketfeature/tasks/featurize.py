#!/usr/bin/env python
from __future__ import print_function

import os
import sys

from pocketfeature.tasks.core import Task

def update_environ_from_namespace(environ, namespace):
    if namespace.feature_root is not None:
        environ['FEATURE_ROOT'] = os.path.expanduser(namespace.feature_root)
    if namespace.feature_dir is not None:
        environ['FEATURE_DIR'] = os.path.expanduser(namespace.feature_dir)
    if namespace.feature_bin is not None:
        environ['FEATURE_BIN'] = os.path.expanduser(namespace.feature_bin)
    if namespace.pdb_dir is not None:
        environ['PDB_DIR'] = os.path.expanduser(namespace.pdb_dir)
    if namespace.dssp_dir is not None:
        environ['DSSP_DIR'] = os.path.expanduser(namespace.dssp_dir)


def extract_feature_args_from_namespace(namespace):
    args = []
    kwargs = {}
    if namespace.P is not None:
        kwargs['P'] = namespace.P
    elif namespace.pdb is not None:
        args.append(namespace.pdb)
    if namespace.n is not None:
        kwargs['shells'] = namespace.n
    if namespace.w is not None:
        kwargs['width'] = namespace.n
    if namespace.x is not None:
        kwargs['exclude'] = namespace.x
    if namespace.l is not None:
        kwargs['properties'] = namespace.l
    if namespace.s is not None:
        kwargs['search_in'] = namespace.s
    return args, kwargs


class Featurize(Task):
    def run(self):
        environ = os.environ
        namespace = self.params
        update_environ_from_namespace(environ, namespace)
        args, kwargs = extract_feature_args_from_namespace(namespace)
        from feature.backends.external import featurize
        kwargs['_out'] = sys.stdout
        kwargs['_err'] = sys.stderr
        try:
            featurize(*args, **kwargs)
            return 0
        except:
            return -1

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import (
            decompress,
            FileType,
        )
        parser = ArgumentParser("Call featurize in a custom environment")
        parser.add_argument('pdb', metavar='PDB', nargs='?', default=None)
        parser.add_argument('-P', metavar='POINTILE', nargs='?', default=None)
        parser.add_argument('-n', metavar='SHELLS', nargs='?', default=None)
        parser.add_argument('-w', metavar='WIDTH', nargs='?', default=None)
        parser.add_argument('-x', metavar='HETATMS', nargs='?', default=None)
        parser.add_argument('-l', metavar='PROPERTYFILE', nargs='?', default=None)
        parser.add_argument('-s', metavar='SEARCH_DIR', nargs='?', default=None)
        
        parser.add_argument('--feature-root', metavar='FEATURE_ROOT', nargs='?', default=None)
        parser.add_argument('--feature-dir', metavar='FEATURE_DIR', nargs='?', default=None)
        parser.add_argument('--feature-bin', metavar='FEATURE_BIN', nargs='?', default=None)
        parser.add_argument('--pdb-dir', metavar='PDB_DIR', nargs='?', default=None)
        parser.add_argument('--dssp-dir', metavar='DSSP_DIR', nargs='?', default=None)

        return parser

if __name__ == '__main__':
    import sys
    sys.exit(Featurize.run_as_script())
