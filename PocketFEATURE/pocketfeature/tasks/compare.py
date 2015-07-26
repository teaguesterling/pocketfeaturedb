#!/usr/bin/env python
from __future__ import print_function

import os

from taskbase import (
    Task,
    FileType,
)

from pocketfeature.io import (
    backgroundfile,
    featurefile,
    matrixvaluesfile,
)
from pocketfeature.datastructs import PassThroughItems

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
        self.background = self.load_background()
        self.featuresA = featurefile.load(self.feature_fileA)
        self.featuresB = featurefile.load(self.feature_fileB)

    def execute(self):
        scores = self.background.get_comparison_matrix(self.featuresA,
                                                       self.featuresB,
                                                       matrix_wrapper=PassThroughItems)
        self.scores = scores

    def produce_result(self):
        return self.generate_output(matrixvaluesfile.dump,
                                    self.scores,
                                    self.output,
                                    'Writing scores to {}')

    def setup_params(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, {
            'comparison_method_name': 'method',
            'allowed_pairs_name': 'pairs',
        })
        self.apply_setup(params, kwargs, defaults, (
            'statistics',
            'normalizations',
        ))

        self.comparison_method = self.COMPARISON_METHODS[self.comparison_method_name]
        self.allowed_pairs = self.VECTOR_TYPE_PAIRS[self.allowed_pairs_name]

    def setup_inputs(self, params, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'feature_fileA',
            'feature_fileB',
        ))

    def load_background(self):
        return backgroundfile.load(stats_file=self.statistics,
                                   norms_file=self.normalizations,
                                   allowed_pairs=self.allowed_pairs,
                                   compare_function=self.comparison_method)

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="""Compute tanimoto matrix for two FEATURE vectors with a background
                                               and score normalizations. If background files are not provided, they
                                               will be checked for in the current directory as well as FEATURE_DIR""")
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
        parser.add_argument('-n', '--normalization',
                            metavar='COEFFICIENTS',
                            type=FileType.compressed('r'),
                            help='Map of normalization coefficients for residue type pairs [default: %(default)s]')
        parser.add_argument('-S', '--comparison-method',
                            metavar='COMPARISON_METHOD',
                            choices=cls.COMPARISON_METHODS.keys(),
                            help='Scoring mehtod to use (one of %(choices)s) [default: %(default)s]')
        parser.add_argument('-p', '--allowed-pairs',
                            metavar='PAIR_SET_NAME',
                            choices=cls.VECTOR_TYPE_PAIRS.keys(),
                            help='Pair selection method to use (one of: %(choices)s) [default: %(default)s]')

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
