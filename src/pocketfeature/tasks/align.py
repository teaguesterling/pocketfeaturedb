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
    aligned = MatrixValues(greedy_align(filtered))
    return aligned


def main(args, stdout, stderr):
    """
    This is just a simple usage example. Fancy argument parsing needs to be enabled
    """
    if len(args) == 0:
        print("Usage: ", file=stderr)
        print(" find_pocket.py SCORES [-c CUTOFF] [-m]", file=stderr)
        print("      -c CUTOFF  - Score Cutoff [default: -0.15]", file=stderr)
        print("      -m         - Munkres Align (Proof of concept)", file=stderr)
        return -1
    
    scores = args[0]
    cutoff = float(args[args.index('-c') + 1]) if '-c' in args else 6.0
    munkres = '-m' in args
    
    if munkres:
        align_method = align_scores_munkres
    else:
        align_method = align_scores_greed

    with open(scores_path) as score_f:
        scores = matrixvaluesfile.load(score_f, columns=[1], cast=float)
    aligned = align_scores_greedy(scores, cutoff)
    matrixvaluesfile.dump(aligned, stdout)

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))

