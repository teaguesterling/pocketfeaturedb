#!/usr/bin/env python
from __future__ import print_function

import os

from taskbase import (
    Task,
    FileType,
    use_file,
)

from pocketfeature.io import (
    backgroundfile,
    featurefile,
    matrixvaluesfile,
)
from pocketfeature.datastructs import PassThroughItems
from pocketfeature.datastructs.metadata import PocketFeatureScoresMatrixMetaData
from pocketfeature.defaults import (
    ALLOWED_SIMILARITY_METHODS,
    ALLOWED_VECTOR_TYPE_PAIRS,
    DEFAULT_BACKGROUND_STATISTICS_FILE,
    DEFAULT_BACKGROUND_NORMALIZATION_FILE,
    DEFAULT_SIMILARITY_METHOD,
    DEFAULT_VECTOR_TYPE_PAIRS,
)


class FeatureFileComparison(Task):
    BACKGROUND_STAT_DEFAULT = DEFAULT_BACKGROUND_STATISTICS_FILE
    BACKGROUND_COEFF_DEFAULT = DEFAULT_BACKGROUND_NORMALIZATION_FILE
    COMPARISON_METHOD_DEFAULT = DEFAULT_SIMILARITY_METHOD
    VECTOR_PAIRS_DEFAULT = DEFAULT_VECTOR_TYPE_PAIRS

    COMPARISON_METHODS = ALLOWED_SIMILARITY_METHODS
    VECTOR_TYPE_PAIRS = ALLOWED_VECTOR_TYPE_PAIRS

    feature_fileA = None
    feature_fileB = None
    statistics = None
    normalizations = None
    allowed_pairs_name = None
    comparison_method_name = None

    def setup(self, params=None, **kwargs):
        params = params or self.params
        defaults = self.defaults(**self.conf)
        self.setup_task(params, defaults=defaults, **kwargs)
        self.setup_params(params, defaults=defaults, **kwargs)
        self.setup_inputs(params, defaults=defaults, **kwargs)

    def load_inputs(self):
        self.load_background = backgroundfile.load(
            stats_file=use_file(self.statistics),
            norms_file=use_file(self.normalizations),
            allowed_pairs=self.allowed_pairs,
            compare_function=self.comparison_method)
        self.featuresA = featurefile.load(use_file(self.feature_fileA))
        self.featuresB = featurefile.load(use_file(self.feature_fileB))

    def execute(self):
        self.run_comparison_matrix()
        self.run_clean_annotate_results()

    def run_comparison_matrix(self):
        vectorsA = self.featuresA
        vectorsB = self.featuresB
        scores = self.background.get_comparison_matrix(vectorsA, vectorsB, matrix_wrapper=PassThroughItems)
        self.original_scores = scores

    def run_clean_annotate_results(self):
        scores = self.original_scores
        fileA_name = getattr(self.feature_fileA, 'name', '<stream>')
        fileB_name = getattr(self.feature_fileB, 'name', '<stream>')
        bg_stats_name = getattr(self.statistics, 'name', '<stream>')
        bg_norms_name = getattr(self.normalizations, 'name', '<stream>')
        scores = scores.round_values(4)
        scores.metadata = self.background.metadata.propagate(kind=PocketFeatureScoresMatrixMetaData,
                                                             FEATURE_FILE_A=fileA_name,
                                                             FEATURE_FILE_B=fileB_name,
                                                             BACKGROUND_STATS_FILE=bg_stats_name,
                                                             BACKGROUND_NORMS_FILE=bg_norms_name)
        self.scores = scores

    def produce_results(self):
        return self.generate_output(matrixvaluesfile.dump,
                                    self.scores,
                                    self.output,
                                    'Writing scores to {}')

    def setup_params(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, {
            'comparison_method_name': 'comparison_method',
            'allowed_pairs_name': 'allowed_pairs',
        })
        self.apply_setup(params, kwargs, defaults, (
            'statistics',
            'normalizations',
        ))

        if self.comparison_method_name is not None:
            self.comparison_method = self.COMPARISON_METHODS[self.comparison_method_name]
        else:
            self.comparison_method = None
        if self.allowed_pairs_name is not None:
            self.allowed_pairs = self.VECTOR_TYPE_PAIRS[self.allowed_pairs_name]
        else:
            self.allowed_pairs = None

    def setup_inputs(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'feature_fileA',
            'feature_fileB',
        ))

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="""Compute tanimoto matrix for two FEATURE vectors with a background
                                               and score normalizations. If background files are not provided, they
                                               will be checked for in the current directory as well as FEATURE_DIR.
                                               By default the comparison method will be chosen from the background""")
        return parser

    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        cls.input_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.task_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.parameter_arguments(parser, stdin, stdout, stderr, environ, **kwargs)

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        defaults = super(FeatureFileComparison, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        defaults.update(cls.paremeter_defaults(stdin, stdout, stderr, environ, **kwargs))
        return defaults

    @classmethod
    def parameter_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('-s', '--statistics',
                            metavar='FEATURESTATS',
                            type=FileType.compressed('r'),
                            help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalizations',
                            metavar='COEFFICIENTS',
                            type=FileType.compressed('r'),
                            help='Map of normalization coefficients for residue type pairs [default: %(default)s]')
        parser.add_argument('--comparison-method',
                            metavar='COMPARISON_METHOD',
                            choices=cls.COMPARISON_METHODS.keys(),
                            help='Scoring method to force (one of %(choices)s) [default: %(default)s]')
        parser.add_argument('--allowed-pairs',
                            metavar='PAIR_SET_NAME',
                            choices=cls.VECTOR_TYPE_PAIRS.keys(),
                            help='Pair selection method force (one of: %(choices)s) [default: %(default)s]')

    @classmethod
    def input_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('feature_fileA',
                            metavar='FEATURE_FILE_A',
                            type=FileType.compressed('r'),
                            help='Path to first FEATURE file')
        parser.add_argument('feature_fileB',
                            metavar='FEATURE_FILE_B',
                            type=FileType.compressed('r'),
                            help='Path to second FEATURE file')


    @classmethod
    def paremeter_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        background_ff = cls.BACKGROUND_STAT_DEFAULT
        background_coeff = cls.BACKGROUND_COEFF_DEFAULT

        if 'POCKETFEATURE_DIR' in os.environ:
            feature_dir = os.environ.get('POCKETFEATURE_DIR')
            env_bg_ff = os.path.join(feature_dir, background_ff)
            env_bg_coeff = os.path.join(feature_dir, background_coeff)
            if not os.path.exists(background_ff) and os.path.exists(env_bg_ff):
                background_ff = env_bg_ff
            if not os.path.exists(background_coeff) and os.path.exists(env_bg_coeff):
                background_coeff = env_bg_coeff
        elif 'FEATURE_DIR' in os.environ:
            feature_dir = os.environ.get('FEATURE_DIR')
            env_bg_ff = os.path.join(feature_dir, background_ff)
            env_bg_coeff = os.path.join(feature_dir, background_coeff)
            if not os.path.exists(background_ff) and os.path.exists(env_bg_ff):
                background_ff = env_bg_ff
            if not os.path.exists(background_coeff) and os.path.exists(env_bg_coeff):
                background_coeff = env_bg_coeff

        return {
            'statistics': background_ff,
            'normalizations': background_coeff,
            'comparison_method_name': cls.COMPARISON_METHOD_DEFAULT,
            'allowed_pairs_name': cls.VECTOR_PAIRS_DEFAULT,
        }


if __name__ == '__main__':
    import sys
    sys.exit(FeatureFileComparison.run_as_script())
