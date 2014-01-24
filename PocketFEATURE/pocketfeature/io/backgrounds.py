#!/usr/bin/env python

from feature.io import featurefile
from feature.io.featurefile import FeatureMetaData
from feature.properties import (
    ItemNameList,
    PropertyList, 
)
from pocketfeature.utils.ff import (
    has_vector,
    get_vector,
    get_vector_type,
)
from pocketfeature.io import matrixvaluesfile
from pocketfeature.algorithms import (
    cutoff_tanimoto_similarity, 
    normalize_score,
)

MEAN_VECTOR = 'MEAN'
STD_DEV_VECTOR = 'STD'
COUNT_COMMENT = 'N'


def make_vector_type_key(vector_types):
    return tuple(sorted(map(str, vector_types)))


class FeatureBackgroundMetaData(FeatureMetaData):
    """ MetaData container that is aware of FEATURE defaults """
    DEFAULTS = {
        'EXCLUDED_RESIDUES': ['HETATM'],
        'PDBID_LIST': [],
        'PROPERTIES': PropertyList(),
        'COMMENTS': ItemNameList([COUNT_COMMENT]),
        'SHELLS': 6,
        'SHELL_WIDTH': 1.25,
        'VERBOSITY': 0,
        'TEST': "YES",
    }


class BackgroundEnvironment(object):

    def __init__(self, std_dev, mean=None, 
                                normalizations=None, 
                                metadata=None,
                                vector_type=get_vector_type,
                                make_type_key=make_vector_type_key):
        self._std_dev = std_dev
        self._mean = mean
        self._normalizations = normalizations
        self._vector_type = vector_type
        self._type_pair_key = make_type_key
        self._metadata = metadata
    
    def zero_features(self, features):
        if self._mean is not None:
            return features - self._mean
        else:
            raise ValueError("No Mean Vector defined")

    def tanimoto_similarity(self, vectorA, vectorB, zeroed=False):
        featuresA = vectorA.features
        featuresB = vectorB.features
        cutoffs = self._std_dev.features
        return cutoff_tanimoto_similarity(cutoffs, featuresA, featuresB, zeroed)

    def normalized_similarity(self, vectorA, vectorB, zeroed=False):
        _, norm = self.normalized_tanimoto_similarity(vectorA, vectorB, zeroed=zeroed)
        return norm

    def normalized_tanimoto_similarity(self, vectorA, vectorB, zeroed=False):
        typeA = self._vector_type(vectorA)
        typeB = self._vector_type(vectorB)
        key = self._type_pair_key((typeA, typeB))
        normalization_coeff = self._normalizations[key]
        tanimoto = self.tanimoto_similarity(vectorA, vectorB, zeroed)
        normalized = normalize_score(tanimoto, normalization_coeff)
        return tanimoto, normalized


def load_normalization_data(io, column=0):
    norms = matrixvaluesfile.load(io, columns=[column], 
                                      cast=float,
                                      make_key=make_vector_type_key)
    return norms


def load(stats_io, norms_io, wrapper=BackgroundEnvironment, 
                             vector_type=get_vector_type,
                             std_dev_vector=STD_DEV_VECTOR,
                             mean_vector=MEAN_VECTOR,
                             metadata=None,
                             norm_mode_column=0):
    if metadata is None:
        metadata = FeatureBackgroundMetaData()
    stats_ff = featurefile.load(stats_io, metadata=metadata)
    coeffs = load_normalization_data(norms_io, column=norm_mode_column)

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
                         vector_type=vector_type)
    return background
