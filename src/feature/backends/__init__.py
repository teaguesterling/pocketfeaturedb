"""
This script is intended to find the correct backed to use.
Currently there is only one backend... so we'll use that
"""
try:
    from feature.backends.native import *
except ImportError:
    from feature.backends.external import (
        generate_dssp_file,
        featurize,
        featurize_points,
        featurize_pointfile,
        featurize_pdb,
    )
    from feature.backends.external import default_environ as FEATURE_ENV