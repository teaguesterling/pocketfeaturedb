#!/usr/bin/env python

from feature.io.featurefile import DESCRIPTION

from pdb_utils import (
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


def typecode_from_comment(comment):
    tokens = comment.split()
    return tokens[-1]


def get_vector_description(vector, comment_field=DESCRIPTION):
    try:
        comment = vector.get_named_comment(comment_field)
        description = comment.split()[0]
        return description
    except ValueError:
        return vector.name


def vectors_descriptions_in_file(feature_file, comment_field=DESCRIPTION):
    get_desc = lambda v: get_vector_description(v, comment_field=comment_field)
    desc = [get_desc(vector) for vector in feature_file.vectors]
    return desc


def get_vector_type(vector, comment_field=DESCRIPTION):
    """ Given a DESCRIPTION comment like "2R6J_A_401_NDP_312_A_1_A A1"
        Extracts the A1 part unless the first character is not a valid
        one letter residue code
    """
    comment = vector.get_named_comment(comment_field)
    typecode = typecode_from_comment(comment)
    restype = typecode[0]
    try:
        residue_code_one_to_three(restype)
        return typecode
    except KeyError:
        return None


def get_vector(vectors, key):
    if isinstance(key, basestring):
        return vectors.get_by_name(key)
    else:
        return vectors[key]


def has_vector(vectors, key):
    if isinstance(key, basestring):
        return vectors.has_vector_named(key)
    else:
        return key < len(vectors)
