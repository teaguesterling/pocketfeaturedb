#!/usr/bin/env python
from __future__ import print_function

import gzip
import itertools

from feature.io import featurefile
from pocketfeature.algorithms import Indexer
from pocketfeature.utils.ff import (
    get_vector_description,
    vectors_descriptions_in_file,
)
from pocketfeature.io import backgrounds
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io.matrixvaluesfile import PassThoughMatrixValues


def score_featurefiles(background, file1, file2):
    pairs = itertools.product(file1.vectors, file2.vectors)
    for vector1, vector2 in pairs:
        name1 = get_vector_description(vector1)
        name2 = get_vector_description(vector2)
        key = (name1, name2)
        scores = background.normalized_tanimoto_similarity(vector1, vector2)
        yield key, scores


def main(args, stdout, stderr):
    """
    This is just a simple usage example. Fancy argument parsing needs to be enabled
    """
    if len(args) < 2:
        print("Usage: ", file=stderr)
        print(" compare_features.py FF1 FF2 [BG_VECS [BG_NORMS]] -- Pairwise scores of vectors in FF1 and FF2", file=stderr)
        print("     BG_VECS - FEATURE file containing background statistics [default: background.ff]", file=stderr)
        print("     BG_NORMS - Sparse matrix containing normalization coefficents [default: background.coeffs]", file=stderr)
        return -1
    
    ff_path1 = args[0]
    ff_path2 = args[1]
    bg_vecs = args[2] if len(args) > 2 else 'background.ff'
    bg_norms = args[3] if len(args) > 3 else 'background.coeffs'
    
    with open(ff_path1) as ff1, open(ff_path2) as ff2,\
         open(bg_vecs) as ffbg, open(bg_norms) as coeffbg:
        stat_background = backgrounds.load(ffbg, coeffbg)  # All other args are default
        features1 = featurefile.load(ff1)
        features2 = featurefile.load(ff2)
    scores = score_featurefiles(stat_background, features1, features2)
    wrapper = PassThoughMatrixValues(scores)
    matrixvaluesfile.dump(wrapper, stdout)

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
