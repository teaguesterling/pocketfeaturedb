from __future__ import absolute_import


from feature.datastructs import features
from feature.properties import (
    DefaultItemNameList,
)
from pocketfeature.defaults import (
    DEFAULT_LIGAND_RESIDUE_DISTANCE,
    DEFAULT_IGNORE_DISORDERED_RESIDUES,
    DEFAULT_SIMILARITY_METHOD,
    DEFAULT_ALIGNMENT_METHOD,
    DEFAULT_VECTOR_TYPE_PAIRS,
    DEFAULT_BACKGROUND_STATISTICS_FILE,
    DEFAULT_BACKGROUND_NORMALIZATION_FILE,
    DEFAULT_SCORE_CUTOFF,
    DEFAULT_SCORE_COLUMN,
    RAW_SCORE,
    NORMALIZED_SCORE,
    COUNT_COMMENT,
    RESIDUE_TYPE,
)


class PocketFeatureMetaDataBase(features.FeatureMetaData):
    pass


class PocketFeaturePointFileMetaData(PocketFeatureMetaDataBase):
    DEFAULTS = PocketFeatureMetaDataBase.clone_defaults_extend(  # Clone but extend comments
        COMMENTS=DefaultItemNameList([features.DESCRIPTION, RESIDUE_TYPE]),
        LIGAND_RESIDUE_DISTANCE=DEFAULT_LIGAND_RESIDUE_DISTANCE,
        IGNORE_DISORDERD=DEFAULT_IGNORE_DISORDERED_RESIDUES,
    )


class PocketFeatureFeatureFileMetaData(PocketFeatureMetaDataBase):
    DEFAULTS = PocketFeaturePointFileMetaData.clone_defaults_overwrite(  # Clone but extend comments
        COMMENTS=DefaultItemNameList(list(features.DEFAULT_COMMENTS) + [RESIDUE_TYPE])
    )


class PocketFeatureBackgroundStatisticsMetaData(PocketFeatureFeatureFileMetaData):
    """ MetaData container that is aware of FEATURE defaults """
    DEFAULTS = PocketFeatureFeatureFileMetaData.clone_defaults_overwrite(  # Clone but override
        COMMENTS=DefaultItemNameList([COUNT_COMMENT]),
        # TODO: ADD RESIDUE TYPE DEFINITIONS
    )


class PocketFeatureBackgroundNormalizationsMetaData(PocketFeatureBackgroundStatisticsMetaData):
    DEFAULTS = PocketFeatureBackgroundStatisticsMetaData.clone_defaults_overwrite(
        COMMENTS=DefaultItemNameList([]),
        COMPARISON_METHOD=DEFAULT_SIMILARITY_METHOD,
        RESIDUE_PAIR_TYPES=DEFAULT_VECTOR_TYPE_PAIRS,
    )


class PocketFeatureMatrixValuesMetaData(PocketFeatureMetaDataBase):
    DEFAULTS =PocketFeatureMetaDataBase.clone_defaults_overwrite(
        COMMENTS=DefaultItemNameList([]),
        KEY_SIZE=2,
    )


class PocketFeatureScoresMatrixMetaData(PocketFeatureMatrixValuesMetaData):
    DEFAULTS = PocketFeatureBackgroundNormalizationsMetaData.clone_defaults_overwrite(
        VALUE_FIELDS=DefaultItemNameList([RAW_SCORE, NORMALIZED_SCORE]),
        STATISTICS_FILE=DEFAULT_BACKGROUND_STATISTICS_FILE,
        NORMALIZATION_FILE=DEFAULT_BACKGROUND_NORMALIZATION_FILE,
        **PocketFeatureMatrixValuesMetaData.DEFAULTS
    )


class PocketFeatureAlignmentMatrixMetaData(PocketFeatureScoresMatrixMetaData):
    DEFAULTS = PocketFeatureScoresMatrixMetaData.clone_defaults_overwrite(
        SCORE_COLUMN=DEFAULT_SCORE_COLUMN,
        ALIGNMENT_METHOD=DEFAULT_ALIGNMENT_METHOD,
        SCORE_CUTOFF=DEFAULT_SCORE_CUTOFF,
    )
