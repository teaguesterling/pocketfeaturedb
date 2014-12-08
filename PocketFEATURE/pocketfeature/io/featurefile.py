
from feature.io import featurefile
from feature.io.featurefile import *
from feature.properties import (
    DefaultItemNameList,
)

COUNT_COMMENT = 'N'
RESIDUE_TYPE = 'RESIDUE_TYPE'


class PocketFeatureMetaData(FeatureMetaData):
    DEFAULTS = FeatureMetaData.clone_defaults_extend(  # Clone but extend comments
        COMMENTS=DefaultItemNameList(featurefile.DEFAULT_COMMENTS + [RESIDUE_TYPE])
    )


class PocketFeatureBackgroundMetaData(FeatureMetaData):
    """ MetaData container that is aware of FEATURE defaults """
    DEFAULTS = PocketFeatureMetaData.clone_defaults_overwrite(  # Clone but override
        COMMENTS=DefaultItemNameList([COUNT_COMMENT])
    )


def iload(src, container=ForwardFeatureFile, metadata=None, rename_from_comment=DESCRIPTION):
    if metadata is None:
        metadata = PocketFeatureMetaData()
    return featurefile.iload(src, container=container,
                                  metadata=metadata,
                                  rename_from_comment=rename_from_comment)

def load(src, container=FeatureFile, metadata=None, rename_from_comment=DESCRIPTION):
    if metadata is None:
        metadata = PocketFeatureMetaData()
    return featurefile.load(src, container=container,
                                 metadata=metadata,
                                 rename_from_comment=rename_from_comment)


def loads(src, container=FeatureFile, metadata=None, rename_from_comment=DESCRIPTION):
    if metadata is None:
        metadata = PocketFeatureMetaData()
    return featurefile.loads(src, container=container,
                                  metadata=metadata,
                                  rename_from_comment=rename_from_comment)

