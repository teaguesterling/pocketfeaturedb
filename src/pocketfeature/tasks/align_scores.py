#!/usr/bin/env python
from __future__ import print_function

from pocketfeature.algorithms import (
    greedy_align,
    munkres_align,
)
from pocketfeature.io.matrixvaluesfile import MatrixValues


def align_scores_munkres(scores, cutoff):
    score_matrix = scores.to_array()
    aligned = munkres_align(score_matrix, shift_negative=True, maximize=False)
    aligned_scores = scores.subset_from_indexes(aligned)
    return aligned_scores


def align_scores_greedy(scores, cutoff):
    filtered_scores = ((k, v) for k, v in scores.items() if v <= cutoff)
    filtered = MatrixValues(filtered_scores)
    aligned = greedy_align(filtered)
    aligned_scores = MatrixValues(aligned)
    return aligned_scores


def main(args, stdout, stderr):
    """
    This is just a simple usage example. Fancy argument parsing needs to be enabled
    """
    if len(args) < 2:
        print("Usage: ", file=stderr)
        print(" compare_features.py SCORES [CUTOFF] -- Pairwise scores of vectors in FF1 and FF2", file=stderr)
        print("     CUTOFF - Score cutoff [default: -0.15]", file=stderr)
        return -1
    
    scores_path = args[0]
    cutoff = args[1] if len(args) > 1 else 0.15
    
    with open(scores_path) as score_f:
        scores = matrixvaluesfile.load(score_f, columns=[1], cast=float)
    aligned = align_scores_greedy(scores, cutoff)
    matrixvaluesfile.dump(aligned, stdout)

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))

