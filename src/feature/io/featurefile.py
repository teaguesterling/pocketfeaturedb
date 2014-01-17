#!/usr/bin/env python
from __future__ import print_function

from cStringIO import StringIO
import re

import numpy as np

from feature.io.metadata import dump as dump_metadata
from feature.io.metadata import (
    extract_metadata,
    MetaData,
)
from feature.io.pointfile import (
    PDBPoint,
    Point3D,
)
from feature.properties import (
    ItemNameList,
    PropertyList, 
)


class PropertyMismatchError(Exception):
    pass


COORDINANTS = 'COORDINANTS'
DESCRIPTION = 'DESCRIPTION'


class FeatureMetaData(MetaData):
    """ MetaData container that is aware of FEATURE defaults """
    DEFAULTS = {
        'EXCLUDED_RESIDUES': ['HETATM'],
        'PDBID_LIST': [],
        'PROPERTIES': PropertyList(),
        'COMMENTS': ItemNameList([COORDINANTS, DESCRIPTION]),
        'SHELLS': 6,
        'SHELL_WIDTH': 1.25,
        'VERBOSITY': 0,
        'TEST': "YES",
    }

    def __init__(self, items=[], *args, **kwargs):
        kwargs.setdefault('defaults', self.DEFAULTS)
        super(FeatureMetaData, self).__init__(items, *args, **kwargs)

    @property
    def _has_coords_comment(self):
        try:
            return self._found_coords_comment
        except AttributeError:
            setattr(self, '_found_coords_comment', COORDINANTS in self.comments)
            return self._found_coords_comment

    # We special case when the COORDINANTS comment is present
    def get_comment_index(self, name):
        idx = self.comments.index(name)
        if self._has_coords_comment:
            return idx - 1
        else:
            return idx

    def get_property_index(self, name):
        return self.properties.index(name)

    @property
    def properties_dtype(self):
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
        return self.get('COMMENTS', ItemNameList())

    def create_vector_template(self):
        if COORDINANTS in self.comments:
            comments = [""] * len(self.comments)
        else:
            comments = [""] * (len(self.comments) - 1)
        return FeatureVector(metadata=self,
                             name="",
                             features=np.zeros(shape=self.num_features,
                                               dtype=self.properties_dtype),
                             point=Point3D(0, 0, 0),
                             comments=comments)


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
        # This is an approximate method
        if 'PDB' in self.comments:
            return self.get_named_comment('PDB')
        elif 'PDBID' in self.comments:
            return self.get_named_comment('PDBID')
        elif self.name.startswith('Env_'):
            return self.name.split('_')[1]
        else:
            return None

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
        self._record_indexes(items, start=old_len)

    def get_by_name(self, name):
        index = self.indexes[name]
        vector = self[index]
        return vector

    def has_vector_named(self, name):
        return name in self.indexes


class ForwardFeatureFile(object):
    """ A lazy FEATURE file container  intended for iterating over large files """
    def __init__(self, metadata=None, vectors=[]):
        if metadata is None:
            metadata = FeatureMetaData()

        self._metadata = metadata
        self._vectors = vectors

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

    def __init__(self, metadata=None, vectors=[]):
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


def iload(src, container=ForwardFeatureFile, metadata=None):
    """ Create a lazy-loading FEATURE file from a stream """
    if metadata is None:
        metadata = FeatureMetaData()
    metadata, body = extract_metadata(src, container=metadata.set_raw_fields)
    parsed_vectors = _load_vectors_using_metadata(metadata, body)
    return container(metadata, parsed_vectors)


def load(src, container=FeatureFile, metadata=None):
    """ Create a FEATURE file from a stream """
    return iload(src, container=container, metadata=metadata)


def loads(src, container=FeatureFile, metadata=None):
    """ Create a FEATURE file from a string """
    return load(src.splitlines(), container=container, metadata=metadata)


def dump(data, io):
    """ Write  a FEATURE file to a stream """
    dump_metadata(data.metadata, io)
    _dump_vectors_using_metadata(data.meatdata, data.vectors, io)


def dumps(data):
    """ Wreite a FEATURE file to a string """
    buf = StringIO()
    dump(data, buf)
    return buf.getvalue()


def extract_line_components(line):
    """ Spilt the main components (name, features, comments)
        up in a FEATURE file vector line """
    tokens = line.split("\t")
    try:
        comments_idx = tokens.index("#")
        print(comments_idx)
        return
        comments = [token for token in tokens[comments_idx:] if token != '#']
    except IndexError:
        comments = []
    name, features = tokens[0], tokens[1:]
    return name, features, comments


def _load_vectors_using_metadata(metadata, lines):
    """ Using metadata as a guide, generate FEATURE vectors from lines """
    comment_fields = metadata.get('COMMENTS', ItemNameList())
    if COORDINANTS in comment_fields:
        coords_at = comment_fields.index(COORDINANTS)
    else:
        coords_at = None
    for line in lines:
        vector = metadata.create_vector_template()
        components = extract_line_components(line)
        if components is None:
            continue
        else:
            name, features, comments = components

        vector.name = name
        
        # This will fail if number of features does not match metadata        
        vector.features[:] = features  # Parse as float and copy

        # Give special treatment to coords comment
        if coords_at is not None:
            xyz = comments[coords_at].split(None, 2)
            comments = [comment for idx, comment in enumerate(comments)
                                if idx != coords_at]
            vector.point.coords[:] = xyz
        else:
            vector.point = None

        # Split comments
        vector.comments = [s.strip() for s in comments]
        yield vector


def _dump_vectors_using_metadata(metadata, vectors, io):
    """ Using metadata as a guide generate FEATURE vector strings from a
        set of vectors and write to some stream """
    comment_fields = metadata.get('COMMENTS', ItemNameList())
    try:
        coords_at = comment_fields.index(COORDINANTS)
    except ValueError:
        coords_at = None
    for vector in vectors:
        print(vector.name, end='\t', file=io)
        print(*vector.features, sep='\t', end='\t', file=io)
        if coords_at is None and vector.coords is not None:
            print(*vector.coords, sep='\t', end='\t#\t', file=io)
            print(*vector.comments, sep='\t#\t', end='\n', file=io)
        else:
            tokens = []
            for idx, comment in vector.comments:
                if idx == coords_at:
                    tokens.append("\t".join(vector.coords))
                else:
                    tokens.append(comment)
            print(*tokens, sep='\t#\t', end='\n', file=io)

