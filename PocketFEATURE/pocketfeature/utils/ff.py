#!/usr/bin/env python

from six import string_types
from feature.io.featurefile import DESCRIPTION
from pocketfeature.datastructs.metadata import RESIDUE_TYPE
from pocketfeature.utils.pdb import (
    residue_code_one_to_three,
    residue_code_three_to_one,
)


def residue_to_typecode(residue, index=1):
    resname = residue.get_resname().upper()
    try:
        resletter = residue_code_three_to_one(resname)
    except KeyError:
        resletter = '?'
    return "{0}{1}".format(resletter, index)


def typecode_from_comment(comment, typecode_idx=-1):
    tokens = comment.split()
    return tokens[typecode_idx]


def get_vector_description(vector, comment_field=DESCRIPTION):
    try:
        comment = vector.get_named_comment(comment_field)
        description = comment.split()[0]
        return description
    except ValueError:
        return vector.name


def get_point_signature(point, signature_idx=0):
    signature = point.comment.split()[signature_idx]
    return signature


def get_pocket_signature(points, signature_idx=0, signature_parts=4, delimiter='_'):
    if len(points) < 1:
        raise ValueError("No signature for empty pocket")
    point = points[0]
    point_signature = get_point_signature(point, signature_idx=signature_idx)
    parts = point_signature.strip(delimiter).split(delimiter)
    signature = delimiter.join(parts[:signature_parts])
    return signature


def get_point_name_lookup(points, signature_idx=0):
    lookup = {}
    for point in points:
        name = get_point_signature(point, signature_idx=0)
        lookup[name] = point
    return lookup


def get_point_name_to_coords_lookup(points, signature_idx=0):
    lookup = get_point_name_lookup(points, signature_idx=signature_idx)
    to_coords = {key: point.coords for key, point in lookup.items()}
    return to_coords


def vectors_descriptions_in_file(feature_file, comment_field=DESCRIPTION):
    get_desc = lambda v: get_vector_description(v, comment_field=comment_field)
    desc = [get_desc(vector) for vector in feature_file.vectors]
    return desc


def get_vector_type(vector, comment_field=RESIDUE_TYPE):
    """ Given a DESCRIPTION comment like "2R6J_A_401_NDP_312_A_1_A A1"
        Extracts the A1 part unless the first character is not a valid
        one letter residue code
    """
    res_type = vector.get_named_comment(comment_field)
    return res_type


def get_vector(vectors, key):
    if isinstance(key, string_types):
        return vectors.get_by_name(key)
    else:
        return vectors[key]


def has_vector(vectors, key):
    if isinstance(key, string_types):
        return vectors.has_vector_named(key)
    else:
        return key < len(vectors)
