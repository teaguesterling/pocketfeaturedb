
try:
    from feature.backends.wrappers import featurize_points_raw
except ImportError as e:
    def featurize_points_raw(*args, **kwargs):
        raise e

from pocketfeature.io import featurefile


def featurize_points(pointslist, featurize_args=None, featurefile_args=None):
    featurize_args = featurize_args or {}
    featurefile_args = featurefile_args or {}
    data = featurize_points_raw(pointslist, **featurize_args)
    ff = featurefile.load(data, **featurefile_args)
    return ff
