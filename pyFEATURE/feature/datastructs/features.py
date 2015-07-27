#!/usr/bin/env python
from __future__ import absolute_import

import numpy as np

from feature.datastructs.metadata import MetaData
from feature.datastructs.points import (
    PDBPoint,
    Point3D,
)
from feature.properties import (
    DEFAULT_PROPERTIES,
    DefaultItemNameList,
    DefaultPropertyList,
)


class PropertyMismatchError(Exception):
    pass


COORDINANTS = 'COORDINANTS'
DESCRIPTION = 'DESCRIPTION'
REAL_NAME = 'REAL_NAME'

DEFAULT_COMMENTS = DefaultItemNameList([COORDINANTS, DESCRIPTION])


class FeatureMetaData(MetaData):
    """ MetaData container that is aware of FEATURE defaults """
    DEFAULTS = {
        'EXCLUDED_RESIDUES': ['HETATM'],
        'PDBID_LIST': [],
        'PROPERTIES': DEFAULT_PROPERTIES,  # Not mutable but replacable
        'COMMENTS': DEFAULT_COMMENTS,      # Not mutable but replacable
        'SHELLS': 6,
        'SHELL_WIDTH': 1.25,
        'VERBOSITY': 0,
    }

    def __init__(self, items=(), *args, **kwargs):
        items = items or []
        kwargs.setdefault('defaults', self.DEFAULTS)
        super(FeatureMetaData, self).__init__(items, *args, **kwargs)
        self.names_comment = None

    @property
    def _has_coords_comment(self):
        try:
            return self._found_coords_comment
        except AttributeError:
            self._found_coords_comment = COORDINANTS in self.comments
            return self._found_coords_comment

    # We special case when the COORDINANTS comment is present
    def get_comment_index(self, name):
        """ Given a comment name, find its index in the comment list """
        idx = self.comments.index(name)
        if self._has_coords_comment:
            return idx - 1
        else:
            return idx

    def get_property_index(self, name):
        """ Find the index of a specific property in the property list """
        return self.properties.index(name)

    def set_name_override_comment(self, comment):
        if comment in self.comments:
            self.names_comment = comment
        else:
            raise ValueError("Cannot rename FEATURE vectors to non-existent comment: {0}".format(comment))

    @property
    def properties_dtype(self):
        """ Create the numpy dtype of a vector for the given metadata configuration """
        return self.properties.dtype()

    @property
    def num_properties(self):
        return len(self.properties)

    @property
    def num_features(self):
        return self.num_properties * self.num_shells

    # Important Properties
    @property
    def properties(self):
        return self.get('PROPERTIES')

    @property
    def num_shells(self):
        return self.get('SHELLS')

    @property
    def shell_width(self):
        return self.get('SHELL_WIDTH')

    @property
    def comments(self):
        return self.get('COMMENTS', DEFAULT_COMMENTS)

    def build_feature_args(self):
        kwargs = {
            'shells': self.num_shells,
            'width': self.shell_width
        }
        if 'PROPERTIES_FILE' in self:
            kwargs['properties'] = self['PROPERTIES_FILE']
        exclude = set(self.get("EXCLUDE", ['HETATM']))
        if exclude != set('HETATM'):
            kwargs['exclude'] = tuple(self.get("EXCLUDE"))
        return kwargs

    def create_vector_template(self):
        """ Generate an empty FEATURE vector object for the given metadata """
        if COORDINANTS in self.comments:
            comments = ["-"] * len(self.comments)
        else:
            comments = ["-"] * (len(self.comments) - 1)
        return FeatureVector(metadata=self,
                             name="VECTOR",
                             features=np.zeros(shape=self.num_features,
                                               dtype=self.properties_dtype),
                             point=Point3D(0, 0, 0),
                             comments=comments)

    def create_vector(self, name=None, features=None, point=None, comments=None):
        # Create a template to ensure correct sizes
        template = self.create_vector_template()
        if name is not None:
            template.name = name
        if features is not None:
            template.features = features
        if point is not None:
            template.point = point
        if comments is not None:
            template.comments = comments

        return template


class FeatureVector(object):
    """ Container class to store FEATURE vector information """

    def __init__(self, metadata, name, features, point, comments):
        super(FeatureVector, self).__init__()
        self.name = name
        self.features = features
        self.point = point
        self.comments = comments
        self.set_metadata(metadata)

    def set_metadata(self, metadata):
        """ Simple sanity checks for consistent metadata """
        if self.num_features != metadata.num_features:
            raise ValueError("Invalid metadata for feature list")
        self.metadata = metadata

    @property
    def num_features(self):
        return len(self.features)

    @property
    def pdbid(self):
        """ Guessed PDBID """
        # This is an approximate method
        if self.has_named_comment('PDB'):
            return self.get_named_comment('PDB')
        elif self.has_named_comment('PDBID'):
            return self.get_named_comment('PDBID')
        elif self.name.startswith('Env_'):
            return self.name.split('_')[1]
        elif 'PDBID_LIST' in self.metadata:
            return self.metadata.get('PDBID_LIST')
        else:
            return []

    @property
    def pdb_point(self):
        pdbid = self.pdbid
        if pdbid is None:
            raise ValueError("Cound not determine source PDB")
        coords = self.coords
        if coords is None:
            raise ValueError("Cound not determine source coordinates")
        comment = "\t#".join(self.comments)
        point = PDBPoint(*coords, pdbid=pdbid, comment=comment)
        return point

    @property
    def coords(self):
        if self.point is not None:
            return self.point.coords
        else:
            return None

    def get_named_comment(self, name):
        return self.comments[self.metadata.get_comment_index(name)]

    def has_named_comment(self, name):
        return name in self.metadata.comments

    def set_named_comment(self, name, value):
        self.comments[self.metadata.comments.index(name)] = value

    def __repr__(self):
        cls_name = type(self).__name__
        return "{0}({1}, {2}, {3})".format(cls_name,
                                           self.name,
                                           self.point,
                                           ", ".join(self.comments))


class FeatureVectorCollection(list):
    """ A collection of FEATURE vectors that keeps track of name->index mappings
        TODO: This should simply be changed to a numpy array of FEATURE Vectors
    """
    def __init__(self, items):
        self.indexes = {}
        super(FeatureVectorCollection, self).__init__(items)
        self._record_indexes(start=0)

    def _record_indexes(self, start=0, end=None):
        updated_items = enumerate(self[start:end], start=start)
        indexes = ((fv.name, idx) for idx, fv in updated_items)
        self.indexes.update(indexes)

    def append(self, item):
        name = item.name
        self.indexes[name] = len(self)
        super(FeatureVectorCollection, self).append(item)

    def extend(self, items):
        old_len = len(self)
        super(FeatureVectorCollection, self).extend(items)
        self._record_indexes(start=old_len)

    def get_by_name(self, name):
        index = self.indexes[name]
        vector = self[index]
        return vector

    def has_vector_named(self, name):
        return name in self.indexes


class ForwardFeatureFile(object):
    """ A lazy FEATURE file container  intended for iterating over large files """
    def __init__(self, metadata=None, vectors=None,
                       set_name_from_comment=None):
        if metadata is None:
            metadata = FeatureMetaData()

        self._metadata = metadata
        self._vectors = vectors or []

    def __iter__(self):
        return self.vectors

    def to_array(self):
        return np.array([child.features for child in self.vectors])

    @property
    def vectors(self):
        return self._vectors

    @property
    def metadata(self):
        return self._metadata

    @property
    def features(self):
        return np.array([child.features for child in self.vectors])

    @property
    def coords(self):
        return np.array([child.coords for child in self.vectors])

    @property
    def pdb_points(self):
        return [child.pdb_point for child in self.vectors]


class FeatureFile(ForwardFeatureFile):
    """ A strict FEATURE file container that loads all vectors at once giving
        a normal array-like interface
    """

    def __init__(self, metadata=None, vectors=()):
        loaded_vectors = FeatureVectorCollection(vectors)
        super(FeatureFile, self).__init__(metadata, loaded_vectors)

    def __getitem__(self, index):
        return self.vectors[index]

    def append(self, vector):
        if vector.metadata.properties != self.metadata.properties:
            raise PropertyMismatchError()
        self.vectors.append(vector)

    def get(self, name):
        return self.vectors.get_by_name(name)
