from __future__ import absolute_import

from feature.io import featurefile
from feature.properties import (
    DefaultItemNameList,
)

COUNT_COMMENT = 'N'
RESIDUE_TYPE = 'RESIDUE_TYPE'


class PocketFeatureMetaData(featurefile.FeatureMetaData):
    DEFAULTS = featurefile.FeatureMetaData.clone_defaults_extend(  # Clone but extend comments
        COMMENTS=DefaultItemNameList(featurefile.DEFAULT_COMMENTS + [RESIDUE_TYPE])
    )


class PocketFeatureBackgroundMetaData(featurefile.FeatureMetaData):
    """ MetaData container that is aware of FEATURE defaults """
    DEFAULTS = PocketFeatureMetaData.clone_defaults_overwrite(  # Clone but override
        COMMENTS=DefaultItemNameList([COUNT_COMMENT])
    )
