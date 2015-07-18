#!/usr/bin/env python
from __future__ import print_function

from pocketfeature.algorithms import filter_scores
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io.backgrounds import (
    ALLOWED_ALIGNMENT_METHODS as _ALLOWED_ALIGNMENT_METHODS,
    ALLOWED_SCALE_FUNCTIONS,
)
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.tasks.core import Task


ALLOWED_ALIGNMENT_METHODS = _ALLOWED_ALIGNMENT_METHODS.copy()
_original_munkres = ALLOWED_ALIGNMENT_METHODS.get('munkres')
if callable(_original_munkres):
    def munkres_special_case(scores):
        matrix = scores.to_array(default=float('inf'))
        aligned_matrix = _original_munkres(matrix, shift_negative=True, maximize=False)
        aligned = scores.subset_from_indexes(aligned_matrix).items()
        return aligned
    ALLOWED_ALIGNMENT_METHODS['munkres'] = munkres_special_case


def align_scores(method, scores, cutoff):
    filtered_scores = filter_scores(scores, cutoff=cutoff)
    score_matrix = MatrixValues(filtered_scores)
    aligned = method(score_matrix)
    alignment_matrix = MatrixValues(aligned)
    return alignment_matrix


class AlignScores(Task):
    DEFAULT_CUTOFF = -0.15
    DEFAULT_COLUMN = 1  # Normalized in 2nd column


    def run(self):
        params = self.params
        align_fn = ALLOWED_ALIGNMENT_METHODS[params.method]
        scale_fn = ALLOWED_SCALE_FUNCTIONS[params.scale_method]
        columns = [params.score_column]
        scores = matrixvaluesfile.load(params.scores, columns=columns, cast=float)
        alignment = align_scores(align_fn, scores, params.cutoff)
        nA, nB = map(len, scores.indexes)
        num_total_points = len(scores)
        num_aligned_points = len(alignment)
        matrixvaluesfile.dump(alignment, params.output)
        raw_score = sum(alignment.values())
        scaled_score = scale_fn(nA, nB, num_aligned_points, raw_score)
        print("Points\t{0}".format(num_total_points), file=params.log)
        print("Aligned\t{0}".format(num_aligned_points), file=params.log)
        print("Raw\t{0:0.5f}".format(raw_score), file=params.log)
        print("Scaled\t{0:0.6g}".format(scaled_score), file=params.log)
        return 0

    @classmethod
    def defaults(cls, stdin, stdout, stderr, enviorn):
        from pocketfeature.utils.args import decompress
        return {
            'scores': decompress(stdin),
            'cutoff': cls.DEFAULT_CUTOFF,
            'score_column': cls.DEFAULT_COLUMN,
            'method': 'onlybest',
            'scale_method': 'none',
            'output': stdout,
            'log': stderr,
        }

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import FileType

        parser = ArgumentParser("Align scores from a PocketFEATURE score matrix")
        parser.add_argument('scores', metavar='SCOREFILE', 
                                      type=FileType.compressed('r'),
                                      help='Path to score file [default: STDIN]')
        parser.add_argument('-c', '--cutoff', metavar='CUTOFF',
                                              type=float,
                                              help='Minium score (cutoff) to align [default: %(default)s')
        parser.add_argument('-s', '--score-column', metavar='COLINDEX',
                                                    type=int,
                                                    help='Value column index in score file to use for aligning [default: 1]')
        parser.add_argument('-m', '--method', metavar='ALIGN_METHOD',
                                      choices=ALLOWED_ALIGNMENT_METHODS.keys(),
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-S', '--scale-method', metavar='SCALE_METHOD',
                                      choices=ALLOWED_SCALE_FUNCTIONS.keys(),
                                      help="Method to re-scale score based on pocket sizes (one of: %(choices)s) [default: %(default)s]")
        parser.add_argument('-o', '--output', metavar='VALUES',
                                              type=FileType.compressed('w'),
                                              help='Path to output file [default: STDOUT]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     help='Path to log errors [default: STDERR]')
        parser.set_defaults(**cls.defaults(stdin, stdout, stderr, environ))
        return parser


if __name__ == '__main__':
    import sys
    sys.exit(AlignScores.run_as_script())

