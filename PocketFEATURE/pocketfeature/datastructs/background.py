#!/usr/bin/env python

#TODO: Integrate metadata into this format to automatically include dimension names
#TODO: Integrate this with residue definition files

import itertools

from six import (
    string_types,
    moves as six_moves,
)

from pocketfeature import defaults
from pocketfeature.datastructs.residues import CenterCalculator
from pocketfeature.datastructs.matrixvalues import MatrixValues
from pocketfeature.utils.ff import get_vector_type

MEAN_VECTOR = 'MEAN'
STD_DEV_VECTOR = 'STD'
VAR_VECTOR = 'VAR'
MIN_VECTOR = 'MIN'
MAX_VECTOR = 'MAX'

RAW_SCORE = 'raw'
NORMALIZED_SCORE = 'normalized'

NORM_COLUMN = 'mode'


class BackgroundEnvironment(object):
    """ An object containing information about a calculated PocketFEATURE background """

    def __init__(self, std_dev, mean=None,
                                normalizations=None,
                                metadata=None,
                                vector_type=get_vector_type,
                                residue_centers=defaults.DEFAULT_RESIDUE_CENTERS,
                                compare_function=defaults.DEFAULT_SIMILARITY_METHOD,
                                normalize_function=defaults.DEFAULT_NORMALIZE_METHOD,
                                scale_function=defaults.DEFAULT_SCALE_FUNCTION,
                                scale_params=(),
                                allowed_pairs=defaults.ALLOWED_VECTOR_TYPE_PAIRS,
                                std_threshold=1.0):
        if isinstance(residue_centers, string_types):
            residue_centers = CenterCalculator(*defaults.NAMED_RESIDUE_CENTERS[residue_centers])
        if isinstance(allowed_pairs, string_types):
            allowed_pairs = defaults.ALLOWED_VECTOR_TYPE_PAIRS[allowed_pairs]
        if isinstance(compare_function, string_types):
            compare_function = defaults.ALLOWED_SIMILARITY_METHODS[compare_function]
        if isinstance(normalize_function, string_types):
            normalize_function = defaults.ALLOWED_NORMALIZE_METHODS[normalize_function]

        self._std_dev = std_dev
        self._mean = mean
        self._normalizations = normalizations
        self._vector_type = vector_type
        self._metadata = metadata
        self._compare_fn = compare_function
        self._normalize_fn = normalize_function
        self._scale_fn = scale_function
        self._scale_params = scale_params
        self._centers = residue_centers

        allowed_center_pairs = allowed_pairs(residue_centers)
        if self._normalizations is not None:
            allowed_center_pairs = set(self._normalizations.keys()).intersection(allowed_center_pairs)

        self._allowed_pairs = allowed_center_pairs
        self._std_threshold_scale = std_threshold
        self._thresholds = None

    def normed_features(self, features):
        if self._mean is not None:
            return features - self._mean
        else:
            raise ValueError("No Mean Vector defined")

    def z_features(self, features):
        return self.normed_features(features) / self._std_dev

    def get_vector_pair_key(self, vectorA, vectorB):
        typeA = self._vector_type(vectorA)
        typeB = self._vector_type(vectorB)
        key = self._centers.make_code_pair((typeA, typeB))
        return key

    def is_allowed_pair(self, vectors):
        if self._allowed_pairs is None:
            return True
        else:
            key = self.get_vector_pair_key(*vectors)
            return key in self._allowed_pairs

    def get_allowed_pairs(self, fileA, fileB):
        pairs = itertools.product(fileA.vectors, fileB.vectors)
        allowed_pairs = six_moves.filter(self.is_allowed_pair, pairs)
        return allowed_pairs

    def vector_similarity(self, vectorA, vectorB):
        featuresA = vectorA.features
        featuresB = vectorB.features
        cutoffs = self.thresholds
        return self._compare_fn(cutoffs, featuresA, featuresB)

    def normalized_vector_similarity(self, vectorA, vectorB):
        _, norm = self.vector_and_normalized_similarity(vectorA, vectorB)
        return norm

    def vector_and_normalized_similarity(self, vectorA, vectorB):
        key = self.get_vector_pair_key(vectorA, vectorB)
        normalization_coeff = self._normalizations[key]
        score = self.vector_similarity(vectorA, vectorB)
        normalized = self._normalize_fn(score, normalization_coeff)
        return score, normalized

    def compare_featurefiles(self, vectorA, vectorB, normalize=True):
        if normalize:
            get_score = self.vector_and_normalized_similarity
        else:
            get_score = self.vector_similarity
        pairs = self.get_allowed_pairs(vectorA, vectorB)
        for vector1, vector2 in pairs:
            key = self.get_vector_pair_key(vector1, vector2)
            name = (vector1.name, vector2.name)
            scores = get_score(vector1, vector2)
            yield name, scores

    def get_comparison_matrix(self, vectorA, vectorB, normalize=True,
                                                      matrix_wrapper=MatrixValues):
        score_names = [RAW_SCORE]
        if normalize:
            score_names.append(NORMALIZED_SCORE)
        scores = self.compare_featurefiles(vectorA, vectorB, normalize=normalize)
        matrix = matrix_wrapper(scores, value_dims=score_names)
        return matrix

    @property
    def thresholds(self):
        if self._thresholds is None:
            std_dev = self._std_dev.features
            self._thresholds = std_dev * self._std_threshold_scale
        return self._thresholds

    @property
    def standard_deviations(self):
        return self._std_dev

    @property
    def mean(self):
        return self._mean

    @property
    def normalizations(self):
        return self._normalizations

    @property
    def metadata(self):
        return self._metadata

    def scale_alignment_score(self, sizes, score):
        return self._scale_fn(self._scale_params, sizes, score)
