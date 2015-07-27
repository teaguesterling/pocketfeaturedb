from __future__ import absolute_import

from collections import namedtuple


ALIGNMENT_RESULT_FIELDS = (
    'num_a',
    'num_b',
    'num_total',
    'num_aligned',
    'raw_score',
)

PF_RUN_RESULT_FIELDS = (
    'pocket_a',
    'pocket_b',
    'alignment',
    'rmsd',
    #mcss,
)

AlignmentResults = namedtuple('AlignmentResults', ALIGNMENT_RESULT_FIELDS)
PFRunResults = namedtuple('PFRunResults', PF_RUN_RESULT_FIELDS)
