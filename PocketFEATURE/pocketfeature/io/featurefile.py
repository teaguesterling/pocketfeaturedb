from __future__ import absolute_import

from feature.io import featurefile
from feature.io.featurefile import (
    dump,
    dumps,
    dump_vector,
)
from pocketfeature.datastructs.metadata import PocketFeatureMetaData


def iload(src, container=featurefile.ForwardFeatureFile, metadata=None, rename_from_comment=featurefile.DESCRIPTION):
    if metadata is None:
        metadata = PocketFeatureMetaData()
    return featurefile.iload(src, container=container,
                                  metadata=metadata,
                                  rename_from_comment=rename_from_comment)

def load(src, container=featurefile.FeatureFile, metadata=None, rename_from_comment=featurefile.DESCRIPTION):
    if metadata is None:
        metadata = PocketFeatureMetaData()
    return featurefile.load(src, container=container,
                                 metadata=metadata,
                                 rename_from_comment=rename_from_comment)


def loads(src, container=featurefile.FeatureFile, metadata=None, rename_from_comment=featurefile.DESCRIPTION):
    if metadata is None:
        metadata = PocketFeatureMetaData()
    return featurefile.loads(src, container=container,
                                  metadata=metadata,
                                  rename_from_comment=rename_from_comment)

