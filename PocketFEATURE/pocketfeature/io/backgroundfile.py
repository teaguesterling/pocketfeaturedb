#!/usr/bin/env python

#TODO: Integrate metadata into this format to automatically include dimension names
#TODO: Integrate this with residue definition files

from pocketfeature import defaults

from pocketfeature.utils.ff import (
    has_vector,
    get_vector,
    get_vector_type,
)


from pocketfeature.datastructs.background import (
    BackgroundEnvironment,
    MEAN_VECTOR,
    STD_DEV_VECTOR,
    NORM_COLUMN,
)
from pocketfeature.datastructs.residues import make_vector_type_key
from pocketfeature.datastructs.metadata import PocketFeatureBackgroundMetaData

from pocketfeature.io import residuefile
from pocketfeature.io import featurefile
from pocketfeature.io import matrixvaluesfile


def load_normalization_data(io, column=0, metadata=None):
    if metadata is None:
        metadata = PocketFeatureBackgroundMetaData()
    norms = matrixvaluesfile.load(io, cast=float,
                                      make_key=make_vector_type_key,
                                      header=True)
    return norms


def load_stats_data(io, metadata=None):
    if metadata is None:
        metadata = PocketFeatureBackgroundMetaData()
    stats_ff = featurefile.load(io, metadata=metadata, rename_from_comment=None)
    return stats_ff


def load_fit_data(io, metadata=None):
    # TODO: Extract method and measure from metadata
    # First line is scaling method
    method_name = next(io).strip()
    params = [map(float, line.split()) for line in io]
    return method_name, params


def load(stats_file, norms_file,
         residues_file=None, scale_file=None,
         wrapper=BackgroundEnvironment,
         vector_type=get_vector_type,
         std_dev_vector=STD_DEV_VECTOR,
         mean_vector=MEAN_VECTOR,
         metadata=None,
         norm_column=NORM_COLUMN,
         compare_function=None,
         normalize_function=None,
         allowed_pairs=None,
         std_threshold=1.0):
    if metadata is None:
        metadata = PocketFeatureBackgroundMetaData()
    stats_ff = load_stats_data(stats_file, metadata)
    stats_bgs = load_normalization_data(norms_file, metadata)

    if scale_file:
        scale_method, scale_params = load_fit_data(scale_file)
    else:
        scale_method = None
        scale_params = ()

    if residues_file:
        centers = residuefile.load(residues_file)
    else:
        centers = None
 
    coeffs = stats_bgs.slice_values(norm_column)

    metadata = stats_ff.metadata
    if has_vector(stats_ff.vectors, std_dev_vector):
        std_dev = get_vector(stats_ff.vectors, STD_DEV_VECTOR)
    else:
        raise ValueError("Stats FEATURE file does not include standard deviations")
    if has_vector(stats_ff.vectors, mean_vector):
        mean = get_vector(stats_ff.vectors, mean_vector)
    else:
        mean = None

    compare_function = compare_function or defaults.DEFAULT_SIMILARITY_METHOD
    normalize_function = normalize_function or defaults.DEFAULT_NORMALIZE_METHOD
    allowed_pairs = allowed_pairs or defaults.ALLOWED_VECTOR_TYPE_PAIRS
    centers = centers or defaults.DEFAULT_RESIDUE_CENTERS

    background = wrapper(std_dev=std_dev,
                         mean=mean,
                         normalizations=coeffs,
                         metadata=metadata,
                         vector_type=vector_type,
                         compare_function=compare_function,
                         normalize_function=normalize_function,
                         allowed_pairs=allowed_pairs,
                         std_threshold=std_threshold,
                         scale_function=scale_method,
                         scale_params=scale_params,
                         residue_centers=centers)
    return background
