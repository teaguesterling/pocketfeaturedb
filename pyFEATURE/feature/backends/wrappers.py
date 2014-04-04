
from feature.io import (
    featurefile,
    pointfile
)
from feature import backends
from feature.backends.external import default_environ


def featurize_points_raw(pointlist, **kwargs):
    points = pointfile.dumpi(pointlist)
    result = backends.featurize_points(points, _iter=True, **kwargs)
    return result


def featurize_points(pointlist, feature_args={}, **kwargs):
    result = featurize_points_raw(pointlist, **feature_args)
    vectors = featurefile.load(result, **kwargs)
    return vectors

