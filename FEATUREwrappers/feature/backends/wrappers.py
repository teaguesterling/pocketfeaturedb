from cStringIO import StringIO
from feature.io import (
    featurefile,
    pointfile
)
from feature import backends
from feature.backends.external import default_environ

def featurize_points(pointlist):
    points = pointfile.dumps(pointlist)
    result = backends.featurize_points(points, _iter=True)
    vectors = featurefile.load(result)
    return vectors
