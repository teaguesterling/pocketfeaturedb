from __future__ import absolute_import, print_function

from taskbase import (
    Task,
    FileType,
    use_file,
)

from feature.io import pointfile
from pocketfeature.io import matrixvaluesfile

from pocketfeature.operations.rmsd import compute_alignment_rmsd

class AlignmentRmsdComputation(Task):

    alignment_file = None
    pointfileA = None
    pointfileB = None

    def setup(self, params=None, **kwargs):
        params = params or self.params
        defaults = self.defaults(**self.conf)
        self.setup_task(params, defaults=defaults, **kwargs)
        self.setup_inputs(params, defaults=defaults, **kwargs)

    def load_inputs(self):
        alignment = matrixvaluesfile.load(use_file(self.alignment_file), cast=float)
        pointsA = pointfile.load(use_file(self.pointfileA))
        pointsB = pointfile.load(use_file(self.pointfileB))

        self.alignment = alignment
        self.pointsA = pointsA
        self.pointsB = pointsB

    def execute(self):
        rmsd = compute_alignment_rmsd(self.alignment,
                                      self.pointsA,
                                      self.pointsB)
        self.rmsd = rmsd

    def produce_results(self):
        printer = lambda data, io: print(data, file=io)
        return self.generate_output(printer, self.rmsd, destination=self.output)

    def setup_inputs(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'alignment_file',
            'pointfileA',
            'pointfileB',
        ))

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="Compute the Delta RMSD between the points selected in an alignment")
        return parser

    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        cls.input_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.task_arguments(parser, stdin, stdout, stderr, environ, **kwargs)

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        defaults = super(AlignmentRmsdComputation, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        return defaults

    @classmethod
    def input_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('alignment_file',
                            type=FileType('r'),
                            help='Alignment file to compute the RMSD from')
        parser.add_argument('pointfileA',
                            type=FileType('r'),
                            help='Original pointfile from the "left" (first) pocket')
        parser.add_argument('pointfileB',
                            type=FileType('r'),
                            help='Original pointfile from the "right" (second) pocket')



if __name__ == '__main__':
    import sys
    sys.exit(AlignmentRmsdComputation.run_as_script())
