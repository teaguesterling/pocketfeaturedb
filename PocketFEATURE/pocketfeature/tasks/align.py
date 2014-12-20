#!/usr/bin/env python
from __future__ import print_function

import itertools

from pocketfeature.algorithms import (
    greedy_align,
    munkres_align,
    only_best_align,
    scale_score_to_alignment_evalue,
    scale_score_to_alignment_tanimoto,
    scale_score_none,
)
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.tasks.core import Task


def align_scores_munkres(scores, cutoff):
    filtered_scores = ((k, v) for k, v in scores.items() if v <= cutoff)
    score_matrix = MatrixValues(filtered_scores).to_array(default=float('inf'))
    aligned = munkres_align(score_matrix, shift_negative=True, maximize=False)
    aligned_scores = scores.subset_from_indexes(aligned)
    return aligned_scores


def align_scores_greedy(scores, cutoff):
    filtered_scores = ((k, v) for k, v in scores.items() if v <= cutoff)
    filtered = MatrixValues(filtered_scores)
    aligned = MatrixValues(greedy_align(filtered))
    return aligned


def align_scores_only_best(scores, cutoff):
    filtered_scores = ((k, v) for k, v in scores.items() if v <= cutoff)
    filtered = MatrixValues(filtered_scores)
    aligned = MatrixValues(only_best_align(filtered))
    return aligned


class AlignScores(Task):
    DEFAULT_CUTOFF = -0.15
    DEFAULT_COLUMN = 1  # Normalized in 2nd column
    ALIGNMENT_METHODS = {
        'greedy': align_scores_greedy,
        'munkres': align_scores_munkres,
        'onlybest': align_scores_only_best,
    }
    SCALE_METHODS = {
        'none': scale_score_none,
        'tanimoto': scale_score_to_alignment_tanimoto,
        'evalue': scale_score_to_alignment_evalue,
    }

    def run(self):
        params = self.params
        align = self.ALIGNMENT_METHODS[params.method]
        scale = self.SCALE_METHODS[params.scale_method]
        columns = [params.score_column]
        scores = matrixvaluesfile.load(params.scores, columns=columns, cast=float)
        alignment = align(scores, params.cutoff)
        nA, nB = map(len, scores.indexes)
        num_total_points = len(scores)
        num_aligned_points = len(alignment)
        matrixvaluesfile.dump(alignment, params.output)
        raw_score = sum(alignment.values())
        scaled_score = scale(nA, nB, num_aligned_points, raw_score)
        print("Points\t{0}".format(num_total_points), file=params.log)
        print("Aligned\t{0}".format(num_aligned_points), file=params.log)
        print("Raw\t{0:0.5f}".format(raw_score), file=params.log)
        print("Scaled\t{0:0.6g}".format(scaled_score), file=params.log)
        return 0

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import (
            decompress,
            FileType,
        )
        parser = ArgumentParser("Align scores from a PocketFEATURE score matrix")
        parser.add_argument('scores', metavar='SCOREFILE', 
                                      type=FileType.compressed('r'),
                                      default=decompress(stdin),
                                      help='Path to score file [default: STDIN]')
        parser.add_argument('-c', '--cutoff', metavar='CUTOFF',
                                              type=float,
                                              default=cls.DEFAULT_CUTOFF,
                                              help='Minium score (cutoff) to align [default: %(default)s')
        parser.add_argument('-s', '--score-column', metavar='COLINDEX',
                                                    type=int,
                                                    default=cls.DEFAULT_COLUMN,
                                                    help='Value column index in score file to use for aligning [default: 1]')
        parser.add_argument('-m', '--method', metavar='ALIGN_METHOD',
                                      choices=cls.ALIGNMENT_METHODS,
                                      default='onlybest',
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-S', '--scale-method', metavar='SCALE_METHOD',
                                      choices=cls.SCALE_METHODS,
                                      default='none',
                                      help="Method to re-scale score based on pocket sizes (one of: %(choices)s) [default: %(default)s]")
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
    sys.exit(AlignScore.run_as_script())

