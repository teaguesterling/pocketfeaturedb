#!/usr/bin/env python

#TODO: Integrate metadata into this format to automatically include dimension names
#TODO: Integrate this with residue definition files

import itertools

from pocketfeature.io import featurefile
from pocketfeature.algorithms import (
    cutoff_tanimoto_similarity, 
    normalize_score,
)
from pocketfeature.io.featurefile import PocketFeatureBackgroundMetaData
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.residues import (
    ALL_CENTERS,
    CENTERS,
    CLASSES,
    get_center_code_set,
) 
from pocketfeature.utils.ff import (
    has_vector,
    get_vector,
    get_vector_type,
)


MEAN_VECTOR = 'MEAN'
STD_DEV_VECTOR = 'STD'
VAR_VECTOR = 'VAR'
MIN_VECTOR = 'MIN'
MAX_VECTOR = 'MAX'

RAW_SCORE = 'raw'
NORMALIZED_SCORE = 'normalized'


def make_vector_type_key(vector_types):
    return tuple(sorted(map(str, vector_types)))

    
def make_allowed_pair_sets(sets, centers=CENTERS):
    pairs = []
    for single_set in sets:
        code_set = get_center_code_set(single_set, centers=centers)
        for codes in itertools.combinations_with_replacement(code_set, 2):
            type_key = make_vector_type_key(codes)
            pairs.append(type_key)
    return set(pairs)


ALLOWED_VECTOR_TYPE_PAIRS = {
    'all': make_allowed_pair_sets([ALL_CENTERS]),
    'classes': make_allowed_pair_sets(CLASSES.values()),
}


print(ALLOWED_VECTOR_TYPE_PAIRS)
print(map(len, ALLOWED_VECTOR_TYPE_PAIRS.values()))
import sys
sys.exit()


class BackgroundEnvironment(object):
    """ An object containing information about a calculated PocketFEATURE background """

    def __init__(self, std_dev, mean=None, 
                                normalizations=None, 
                                metadata=None,
                                vector_type=get_vector_type,
                                make_type_key=make_vector_type_key,
                                compare_function=cutoff_tanimoto_similarity,
                                normalize_function=normalize_score,
                                allowed_pairs=None):
        self._std_dev = std_dev
        self._mean = mean
        self._normalizations = normalizations
        self._vector_type = vector_type
        self._type_pair_key = make_type_key
        self._metadata = metadata
        self._compare_fn = compare_function
        self._normalize_fn = normalize_function
        if isinstance(allowed_pairs, basestring):
            allowed_pairs = ALLOWED_VECTOR_TYPE_PAIRS[allowed_pairs]
        self._allowed_pairs = allowed_pairs
    
    def zero_features(self, features):
        if self._mean is not None:
            return features - self._mean
        else:
            raise ValueError("No Mean Vector defined")

    def get_vector_pair_key(self, vectorA, vectorB):
        typeA = self._vector_type(vectorA)
        typeB = self._vector_type(vectorB)
        key = self._type_pair_key((typeA, typeB))
        return key

    def is_allowed_pair(self, vectors):
        if self._allowed_pairs is None:
            return True
        else:
            key = self.get_vector_pair_key(*vectors)
            return key in self._allowed_pairs

    def get_allowed_pairs(self, fileA, fileB):
        pairs = itertools.product(fileA.vectors, fileB.vectors)
        allowed_pairs = itertools.ifilter(self.is_allowed_pair, pairs)
        return allowed_pairs

    def tanimoto_similarity(self, vectorA, vectorB, zeroed=False):
        featuresA = vectorA.features
        featuresB = vectorB.features
        cutoffs = self._std_dev.features
        return self._compare_fn(cutoffs, featuresA, featuresB, zeroed)

    def normalized_similarity(self, vectorA, vectorB, zeroed=False):
        _, norm = self.normalized_tanimoto_similarity(vectorA, vectorB, zeroed=zeroed)
        return norm

    def normalized_tanimoto_similarity(self, vectorA, vectorB, zeroed=False):
        key = self.get_vector_pair_key(vectorA, vectorB)
        normalization_coeff = self._normalizations[key]
        tanimoto = self.tanimoto_similarity(vectorA, vectorB, zeroed)
        normalized = self._normalize_fn(tanimoto, normalization_coeff)
        return tanimoto, normalized

    def compare_featurefiles(self, vectorA, vectorB, normalize=True, 
                                                     zeroed=False):
        if normalize:
            get_score = self.normalized_tanimoto_similarity
        else:
            get_score = self.tanimoto_similarity
        pairs = self.get_allowed_pairs(vectorA, vectorB)
        for vector1, vector2 in pairs:
            key = self.get_vector_pair_key(vector1, vector2)
            name = (vector1.name, vector2.name)
            scores = get_score(vector1, vector2, zeroed=zeroed)
            yield name, scores

    def get_comparison_matrix(self, vectorA, vectorB, normalize=True,
                                                      zeroed=False,
                                                      matrix_wrapper=MatrixValues):
        score_names = [RAW_SCORE]
        if normalize:
            score_names.append(NORMALIZED_SCORE)
        scores = self.compare_featurefiles(vectorA, vectorB, normalize=normalize, zeroed=zeroed)
        matrix = matrix_wrapper(scores, value_dims=score_names)
        return matrix

    @property
    def standard_deviations(self):
        return self._std_dev

    @property
    def mean(self):
        return self._mean

    @property
    def normalizations(self):
        return self._normalizations


def load_normalization_data(io, column=0):
    norms = matrixvaluesfile.load(io, columns=[column], 
                                      cast=float,
                                      make_key=make_vector_type_key)
    return norms


def load_stats_data(io, metadata=None):
    if metadata is None:
        metadata = PocketFeatureBackgroundMetaData()
    stats_ff = featurefile.load(io, metadata=metadata, rename_from_comment=None)
    return stats_ff


def load(stats_file, norms_file, wrapper=BackgroundEnvironment, 
                                 vector_type=get_vector_type,
                                 make_type_key=make_vector_type_key,
                                 std_dev_vector=STD_DEV_VECTOR,
                                 mean_vector=MEAN_VECTOR,
                                 metadata=None,
                                 norm_mode_column=0,
                                 compare_function=cutoff_tanimoto_similarity,
                                 normalize_function=normalize_score,
                                 allowed_pairs=None):
    stats_ff = load_stats_data(stats_file, metadata)
    coeffs = load_normalization_data(norms_file, column=norm_mode_column)

    metadata = stats_ff.metadata
    if has_vector(stats_ff.vectors, std_dev_vector):
        std_dev = get_vector(stats_ff.vectors, STD_DEV_VECTOR)
    else:
        raise ValueError("Stats FEATURE file does not include standard deviations")
    if has_vector(stats_ff.vectors, mean_vector):
        mean = get_vector(stats_ff.vectors, mean_vector)
    else:
        mean = None

    background = wrapper(std_dev=std_dev,
                         mean=mean,
                         normalizations=coeffs,
                         metadata=metadata,
                         vector_type=vector_type,
                         make_type_key=make_type_key,
                         compare_function=compare_function,
                         normalize_function=normalize_function,
                         allowed_pairs=allowed_pairs)
    return background
