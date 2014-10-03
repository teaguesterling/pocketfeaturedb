
import itertools

from feature.io import (
    featurefile,
    pointfile
)
from feature.backends import external
from feature.backends.external import default_environ


WORKING_FEATURIZE_METHOD = None

FEATURIZE_METHODS = [
    external.featurize_points,
    external.featurize_points_tempfile,
]


def standard_config():
    WORKING_FEATURIZE_METHOD = external.featurize_points

def legacy_config():
    WORKING_FEATURIZE_METHOD = external.featurize_points_tempfile


def determine_correct_featurize_method(points, _iter=True, **kwargs):
    errors = []
    error_indications = ('WARNING: ', 'ERROR: ', 'Usage: ')
    for method in FEATURIZE_METHODS:
        points, backup_points = itertools.tee(points)  # Make sure we don't lose any points
        try:
            result = method(points, _iter=True, **kwargs)  # TODO: Iter should not be passed in here for generality
            peek = list(itertools.islice(result, 3))
            if any(line.startswith(indication) for indication in error_indications for line in peek):
                points = backup_points
                continue
            else:
                result = itertools.chain(peek, result)
                WORKING_FEATURIZE_METHOD = method
                return result
        except Exception as e:  # If anything goes wrong with streaming try tempfile
            errors.append(str(e))
            points = backup_points
            continue
    raise NotImplementedError("Failed to featurize. Errors were:\n{}".format('\n'.join(errors)))


def _try_to_featurize_points(points, _iter=True, **kwargs):
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
