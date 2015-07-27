from __future__ import absolute_import

import functools

from pocketfeature.defaults import ALLOWED_ALIGNMENT_METHODS
from pocketfeature.algorithms import filter_scores
from pocketfeature.io.matrixvaluesfile import MatrixValues


def wrap_matrix_aligning_method(fn):
    @functools.wraps(fn)
    def wrapper(scores, *args, **kwargs):
        matrix = scores.to_array(default=float('inf'))
        aligned_matrix = fn(matrix, shift_negative=True, maximize=False)
        aligned = scores.subset_from_indexes(aligned_matrix).items()
        return aligned
    return wrapper


def make_updated_methods(methods=ALLOWED_ALIGNMENT_METHODS):
    methods = methods.copy()
    munkres = methods.get('munkres')
    if callable(munkres):
        wrapped_munkres = wrap_matrix_aligning_method(munkres)
        methods['munkres'] = wrapped_munkres
    return methods


def perform_alignment(method, scores, cutoff):
    filtered_scores = filter_scores(scores, cutoff=cutoff)
    score_matrix = MatrixValues(filtered_scores)
    aligned = method(score_matrix)
    alignment_matrix = MatrixValues(aligned)
    return alignment_matrix
