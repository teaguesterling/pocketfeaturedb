#!/usr/bin/env python
from __future__ import print_function

import itertools

from pocketfeature.algorithms import (
    greedy_align,
    munkres_align,
    only_best_align,
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

    def run(self):
        params = self.params
        align = self.ALIGNMENT_METHODS[params.method]
        columns = [params.score_column]
        scores = matrixvaluesfile.load(params.scores, columns=columns, cast=float)
        alignment = align(scores, params.cutoff)
        matrixvaluesfile.dump(alignment, params.output)
        print("Score: {0}".format(sum(alignment.values())), file=params.log)
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

