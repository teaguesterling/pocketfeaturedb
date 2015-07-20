from __future__ import absolute_import

from pocketfeature.algorithms import (
    normalize_score,
    greedy_align,
    munkres_align,
    only_best_align,
    cutoff_dice_similarity,
    cutoff_tanimoto_similarity,
    cutoff_tversky22_similarity,
    scale_score_none,
    scale_score_fitted_zscore,
    scale_score_fitted_evd,
    scale_score_to_alignment_tanimoto,
    scale_score_to_alignment_evalue,
)
from pocketfeature.datastructs.residues import CenterCalculator

# Each residue consists of some number of "centers" or active sits
# Each of which is defined by one or more atoms in the residue
DEFAULT_CENTERS = {
    'GLY': [['CA']],
    'CYS': [['SG']],
    'ARG': [['CZ']],
    'SER': [['OG']],
    'THR': [['OG1']],
    'LYS': [['NZ']],
    'MET': [['SD']],
    'ALA': [['CB']],
    'LEU': [['CB']],
    'ILE': [['CB']],
    'VAL': [['CB']],
    'ASP': [['OD1', 'CG', 'OD2']],
    'GLU': [['OE1', 'CD', 'OE2']],
    'HIS': [['NE2', 'ND1']],
    'ASN': [['OD1', 'CG', 'ND2']],
    'PRO': [['N', 'CA', 'CB', 'CD', 'CG']],
    'GLN': [['OE1', 'CD', 'NE2']],
    'PHE': [['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ']],
    'TRP': [['NE1'],
            ['CD2', 'CE2', 'CE3', 'CZ2', 'CZ3', 'CH2']],
    'TYR': [['OH'],
            ['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ']],
}


DEFAULT_CLASSES = {
    'positive': (('ARG', 0), ('HIS', 0), ('LYS', 0)),
    'negative': (('ASP', 0), ('GLU', 0)),
    'polar': (('SER', 0), ('THR', 0),
              ('ASN', 0), ('GLN', 0),
              ('TYR', 0), ('TRP', 0)),
    'non-polar': (('ALA', 0), ('CYS', 0),
                  ('GLY', 0), ('ILE', 0),
                  ('LEU', 0), ('MET', 0),
                  ('PRO', 0), ('VAL', 0)),
    'aromatic': (('TYR', 1), ('TRP', 1), ('PHE', 0)),
}


MEAN_VECTOR = 'MEAN'
STD_DEV_VECTOR = 'STD'
VAR_VECTOR = 'VAR'
MIN_VECTOR = 'MIN'
MAX_VECTOR = 'MAX'

RAW_SCORE = 'raw'
NORMALIZED_SCORE = 'normalized'

# None values represent defaults

NAMED_RESIDUE_CENTERS = {
    'standard': CenterCalculator(DEFAULT_CENTERS, DEFAULT_CLASSES),
}

ALLOWED_VECTOR_TYPE_PAIRS = {
    'all': CenterCalculator.get_all_code_pairs,
    'classes': CenterCalculator.get_class_code_pairs,
}

ALLOWED_SIMILARITY_METHODS = {
    'dice': cutoff_dice_similarity,
    'tanimoto': cutoff_tanimoto_similarity,
    'tversky22': cutoff_tversky22_similarity,
}


ALLOWED_NORMALIZE_METHODS = {
    'normalize': normalize_score,
}

ALLOWED_ALIGNMENT_METHODS = {
    'greedy': greedy_align,
    'munkres': munkres_align,
    'onlybest': only_best_align,
}

ALLOWED_SCALE_FUNCTIONS = {
    'none': scale_score_none,
    'tanimoto': scale_score_to_alignment_tanimoto,
    'evalue': scale_score_to_alignment_evalue,
    'fitted-z': scale_score_fitted_zscore,
    'fitted-evd': scale_score_fitted_evd,
}

DEFAULT_RESIDUE_CENTERS = 'standard'
DEFAULT_VECTOR_TYPE_PAIRS = 'classes'
DEFAULT_SIMILARITY_METHOD = 'tversky22'
DEFAULT_NORMALIZE_METHOD = 'normalize'
DEFAULT_ALIGNMENT_METHOD = 'onlybest'
DEFAULT_SCALE_FUNCTION = 'none'
