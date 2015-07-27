#!/usr/bin/env python
from __future__ import absolute_import, print_function

import csv

from taskbase import (
    Task,
    FileType,
    use_file,
)
from pocketfeature.datastructs.results import (
    AlignmentResults,
    ALIGNMENT_RESULT_FIELDS,
)
from pocketfeature.datastructs.metadata import PocketFeatureAlignmentMatrixMetaData
from pocketfeature.io import matrixvaluesfile
from pocketfeature.operations.align import (
    make_updated_methods,
    perform_alignment,
)

from pocketfeature.defaults import (
    ALLOWED_ALIGNMENT_METHODS,
    DEFAULT_SCORE_CUTOFF,
    DEFAULT_ALIGNMENT_METHOD,
    DEFAULT_SCORE_COLUMN,
)


class ScoreAlignment(Task):
    DEFAULT_CUTOFF = DEFAULT_SCORE_CUTOFF
    DEFAULT_COLUMN = DEFAULT_SCORE_COLUMN
    DEFAULT_ALIGNMENT_METHOD = DEFAULT_ALIGNMENT_METHOD

    ALIGNMENT_METHODS = make_updated_methods(ALLOWED_ALIGNMENT_METHODS)

    align_method_name = None
    align_method = None
    score_file = None
    score_column = None
    cutoff = None
    summary_file = None

    def setup(self, params=None, **kwargs):
        params = params or self.params
        defaults = self.defaults(**self.conf)
        self.setup_task(params, defaults=defaults, **kwargs)
        self.setup_inputs(params, defaults=defaults, **kwargs)
        self.setup_params(params, defaults=defaults, **kwargs)
        self.setup_output(params, defaults=defaults, **kwargs)

    def load_inputs(self):
        scores = matrixvaluesfile.load(use_file(self.score_file), cast=float)
        selected_scores = scores.slice_values(self.score_column)
        self.scores = scores
        self.selected_scores = selected_scores

    def execute(self):
        self.run_alignment()
        self.run_clean_annotate_results()
        self.run_summary()

    def produce_results(self):
        self.write_summary()
        return self.generate_output(matrixvaluesfile.dump,
                                    self.alignment,
                                    self.output,
                                    'Writing alignment to {}')

    def write_summary(self):
        if self.summary_file is not None:
            writer = csv.writer(self.summary_file, dialect='excel-tab')
            writer.writerow(ALIGNMENT_RESULT_FIELDS)
            writer.writerow(self.summary)

    def setup_params(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, {
            'align_method_name': 'align_method',
            'cutoff': 'cutoff'
        })

        self.align_method = self.ALIGNMENT_METHODS[self.align_method_name]

    def setup_inputs(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'score_file',
            'score_column',
        ))

    def setup_output(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'summary_file',
        ))


    def run_alignment(self):
        alignment = perform_alignment(self.align_method,
                                      self.selected_scores,
                                      self.cutoff)
        self.alignment = alignment

    def run_clean_annotate_results(self):
        alignment = self.alignment
        alignment = alignment.round_values(3)

        file_name = getattr(self.score_file, 'name', '<stream>')
        alignment.metadata = self.scores.metadata.propagate(kind=PocketFeatureAlignmentMatrixMetaData,
                                                            SCORE_FILE=file_name,
                                                            SCORE_COLUMN=self.score_column,
                                                            ALIGNMENT_METHOD=self.align_method_name,
                                                            SCORE_CUTOFF=self.cutoff)

    def run_summary(self):
        scores = self.scores
        alignment = self.alignment
        nA, nB = [len(index) for index in scores.indexes]
        num_total_points = len(scores)
        num_aligned_points = len(alignment)
        raw_score = round(sum(alignment.values()), 4)

        self.num_pointsA = nA
        self.num_pointsB = nB
        self.num_total_points = num_total_points
        self.num_aligned_points = num_aligned_points
        self.raw_score = raw_score

        self.summary = AlignmentResults(num_a=self.num_pointsA,
                                        num_b=self.num_pointsB,
                                        num_total=self.num_total_points,
                                        num_aligned=self.num_aligned_points,
                                        raw_score=self.raw_score)


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
        defaults = super(ScoreAlignment, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        defaults.update(cls.paremeter_defaults(stdin, stdout, stderr, environ, **kwargs))
        defaults.update(cls.input_defaults(stdin, stdout, stderr, environ, **kwargs))
        defaults.update(cls.output_defaults(stdin, stdout, stderr, environ, **kwargs))
        return defaults

    @classmethod
    def parameter_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('-c', '--cutoff',
                            metavar='CUTOFF',
                            type=float,
                            help='Minimum score (cutoff) to align [default: %(default)s')
        parser.add_argument('--align-method',
                            metavar='ALIGN_METHOD',
                            choices=cls.ALIGNMENT_METHODS.keys(),
                            help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')

    @classmethod
    def input_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('score_file',
                            metavar='SCOREFILE',
                            type=FileType.compressed('r'),
                            help='Path to score file [default: STDIN]')
        parser.add_argument('--score-column',
                            metavar='COL_NAME_INDEX',
                            type=lambda s: int(s) if s.isdigit() else s,
                            help='Value column index in score file to use for aligning [default: %(default)s]')

    @classmethod
    def output_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('--summary-file',
                            metavar='SUMMARY_FILE',
                            type=FileType('w'),
                            help='Path to score file [default: STDERR]')

    @classmethod
    def input_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'score_file': stdin,
            'score_column': cls.DEFAULT_COLUMN,
        }

    @classmethod
    def output_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'summary_file': stderr,
        }

    @classmethod
    def paremeter_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'cutoff': cls.DEFAULT_CUTOFF,
            'align_method': cls.DEFAULT_ALIGNMENT_METHOD,
        }


if __name__ == '__main__':
    import sys
    sys.exit(ScoreAlignment.run_as_script())
