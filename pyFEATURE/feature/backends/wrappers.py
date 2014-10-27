
import itertools
import os

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

FEATURIZE_PTF_API = os.environ.get('FEATURIZE_PTF_API', 'modern').lower().strip()


def standard_config():
    WORKING_FEATURIZE_METHOD = external.featurize_points


def legacy_config():
    WORKING_FEATURIZE_METHOD = external.featurize_points_tempfile


def determine_correct_featurize_method(points, _iter=True, **kwargs):
    errors = []
    error_indications = ('WARNING: ', 'ERROR: ', 'Usage: ')
    sources = itertools.tee(points, len(FEATURIZE_METHODS))
    for these_points, method in zip(sources, FEATURIZE_METHODS):
        try:
            result = method(these_points, _iter=True, **kwargs)  # TODO: Iter should not be passed in here for generality
            peek = list(itertools.islice(result, 3))
            if not any(line.startswith(indication) for indication in error_indications for line in peek):
                result = itertools.chain(peek, result)
                WORKING_FEATURIZE_METHOD = method
                del sources
                return result
        except Exception as e:  # If anything goes wrong with streaming try tempfile
            errors.append(str(e))
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


if FEATURIZE_PTF_API == 'legacy':
    legacy_config()
elif FEATURIZE_PTF_API == 'modern':
    standard_config()
