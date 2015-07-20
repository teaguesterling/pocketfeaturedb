
import itertools
import os
import warnings

from feature.io import (
    featurefile,
    pointfile
)
from feature.backends import external
from feature.backends.external import default_environ


__all__ = [
    'standard_config',
    'legacy_config',
    'current_config',
    'featurize_points_raw',
    'featurize_points',
    'featurize_pdb'
]

WORKING_FEATURIZE_METHOD = None

FEATURIZE_METHODS = [
    external.featurize_points,
    external.featurize_points_tempfile,
]

FEATURIZE_PTF_API = os.environ.get('FEATURIZE_PTF_API', 'modern').lower().strip()


def standard_config():
    global WORKING_FEATURIZE_METHOD
    WORKING_FEATURIZE_METHOD = external.featurize_points


def legacy_config():
    global WORKING_FEATURIZE_METHOD
    WORKING_FEATURIZE_METHOD = external.featurize_points_tempfile

def current_config():
    global WORKING_FEATURIZE_METHOD
    return WORKING_FEATURIZE_METHOD


def determine_correct_featurize_method(points, _iter=True, **kwargs):
    global WORKING_FEATURIZE_METHOD
    warnings.warn("Attempting to determine FEATURE pointfile calling method")
    errors = []
    error_indications = ('WARNING: ', 'ERROR: ', 'Usage: ')
    point_source = iter(points)
    test = itertools.islice(point_source, 1)
    points = itertools.chain(test, point_source)
    for method in FEATURIZE_METHODS:
        try:
            test_result = list(method(test, _iter=True, **kwargs))
            if not any(line.startswith(indication) for indication in error_indications for line in test_result):
                WORKING_FEATURIZE_METHOD = method
                result = method(points, _iter=True, **kwargs)
                return result
        except Exception as e:  # If anything goes wrong with streaming try tempfile
            errors.append(str(e))
    raise NotImplementedError("Failed to featurize. Errors were:\n{}".format('\n'.join(errors)))


def _try_to_featurize_points(points, _iter=True, **kwargs):
    global WORKING_FEATURIZE_METHOD
    if WORKING_FEATURIZE_METHOD is None:
        return determine_correct_featurize_method(points, **kwargs)
    else:
        return WORKING_FEATURIZE_METHOD(points, **kwargs)


def featurize_points_raw(pointlist, **kwargs):
    points = pointfile.dumpi(pointlist)
    result = _try_to_featurize_points(points, _iter=True, **kwargs)
    return result


def featurize_points(pointlist, feature_args={}, **kwargs):
    result = featurize_points_raw(pointlist, **feature_args)
    vectors = featurefile.load(result, **kwargs)
    return vectors

def featurize_pdb(pdbid, feature_args={}, **kwargs):
    result = external.featurize_pdb(pdbid, **feature_args)
    vectors = featurefile.load(result, **kwargs)
    return vectors


if FEATURIZE_PTF_API == 'legacy':
    legacy_config()
elif FEATURIZE_PTF_API == 'modern':
    standard_config()
else:
    warnings.warn("Invalid value for FEATURIZE_PTF_API enviornmental variable")
