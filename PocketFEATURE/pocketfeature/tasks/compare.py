#!/usr/bin/env python
from __future__ import print_function

import gzip
import itertools
import os

from pocketfeature.algorithms import (
    cutoff_dice_similarity,
    cutoff_tanimoto_similarity, 
    cutoff_tversky22_similarity,
    Indexer,
    normalize_score,
)
from pocketfeature.io import (
    backgrounds,
    featurefile,
    matrixvaluesfile,
)
from pocketfeature.io.backgrounds import (
    ALLOWED_SIMILARITY_METRICS,
    make_allowed_pair_sets,
)
from pocketfeature.io.matrixvaluesfile import PassThroughItems

from pocketfeature.tasks.core import Task


class FeatureFileCompare(Task):
    BACKGROUND_FF_DEFAULT = 'background.ff'
    BACKGROUND_COEFF_DEFAULT = 'background.coeffs'

    COMPARISON_METHODS = ALLOWED_SIMILARITY_METRICS.copy()

    def run(self):
        params = self.params
        background = backgrounds.load(stats_file=params.background, 
                                      norms_file=params.normalization,
                                      allowed_pairs=params.allowed_pairs,
                                      compare_function=self.COMPARISON_METHODS[params.method])
        features1 = featurefile.load(params.features1)
        features2 = featurefile.load(params.features2)
        # Compute scores and store directly (no matrix representation)
        scores = background.get_comparison_matrix(features1, features2,
                                                  matrix_wrapper=PassThroughItems)
        matrixvaluesfile.dump(scores, params.output)
        return 0

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import (
            ArgumentParser,
            FileType,
        )
        from pocketfeature.utils.args import FileType

        background_ff = cls.BACKGROUND_FF_DEFAULT
        background_coeff = cls.BACKGROUND_COEFF_DEFAULT

        if 'FEATURE_DIR' in os.environ:
            feature_dir = os.environ.get('FEATURE_DIR')
            env_bg_ff = os.path.join(feature_dir, background_ff)
            env_bg_coeff = os.path.join(feature_dir, background_coeff)
            if not os.path.exists(background_ff) and os.path.exists(env_bg_ff):
                background_ff = env_bg_ff
            if not os.path.exists(background_coeff) and os.path.exists(env_bg_coeff):
                background_coeff = env_bg_coeff

        parser = ArgumentParser(
            """Compute tanimoto matrix for two FEATURE vectors with a background 
               and score normalizations. If background files are not provided, they 
               will be checked for in the current directory as well as FEATURE_DIR""")
        parser.add_argument('features1', metavar='FEATUREFILE1', 
                                          type=FileType.compressed('r'),
                                          help='Path to first FEATURE file')
        parser.add_argument('features2', metavar='FEATUREFILE2', 
                                         type=FileType.compressed('r'),
                                         help='Path to second FEATURE file')
        parser.add_argument('-b', '--background', metavar='FEATURESTATS',
                                      type=FileType.compressed('r'),
                                      default=background_ff,
                                      help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalization', metavar='COEFFICIENTS',
                                      type=FileType.compressed('r'),
                                      default=background_coeff,
                                      help='Map of normalization coefficients for residue type pairs [default: %(default)s]')
        parser.add_argument('-C', '--method', metavar='COMPARISON_METHOD',
                                      choices=cls.COMPARISON_METHODS.keys(),
                                      default='tversky22',
                                      help='Scoring mehtod to use (one of %(choices)s) [default: %(default)s]')
        parser.add_argument('-p', '--allowed-pairs', metavar='PAIR_SET_NAME',
                                      choices=backgrounds.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
                                      default='classes',
                                      help='Pair selection method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-o', '--output', metavar='VALUES',
                                              type=FileType.compressed('w'),
                                              default=stdout,
                                              help='Path to output file [default: STDOUT]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     default=stderr,
                                     help='Path to log errors [default: STDERR]')
        return parser


if __name__ == '__main__':
    import sys
    sys.exit(FeatureFileCompare.run_as_script())
