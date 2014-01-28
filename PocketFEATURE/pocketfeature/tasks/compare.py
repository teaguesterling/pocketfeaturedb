#!/usr/bin/env python
from __future__ import print_function

import gzip
import itertools

from feature.io import featurefile
from pocketfeature.algorithms import (
    cutoff_tanimoto_similarity, 
    Indexer,
    normalize_score,
)
from pocketfeature.io import backgrounds
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io.matrixvaluesfile import PassThoughMatrixValues
from pocketfeature.utils.ff import (
    get_vector_description,
    vectors_descriptions_in_file,
)

from pocketfeature.tasks.core import Task


def score_featurefiles(background, file1, file2):
    pairs = itertools.product(file1.vectors, file2.vectors)
    for vector1, vector2 in pairs:
        name1 = get_vector_description(vector1)
        name2 = get_vector_description(vector2)
        key = (name1, name2)
        scores = background.normalized_tanimoto_similarity(vector1, vector2)
        yield key, scores


class FeatureFileCompare(Task):
    BACKGROUND_FF_DEFAULT = 'background.ff'
    BACKGROUND_COEFF_DEFAULT = 'background.coeffs'
    def run(self):
        params = self.params
        stat_background = backgrounds.load(stats_file=params.background, 
                                           norms_file=params.normalization,
                                           compare_function=cutoff_tanimoto_similarity,
                                           normalize_function=normalize_score)
        features1 = featurefile.load(params.features1)
        features2 = featurefile.load(params.features2)
        scores = score_featurefiles(stat_background, features1, features2)
        wrapper = PassThoughMatrixValues(scores)
        matrixvaluesfile.dump(wrapper, params.output)
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
