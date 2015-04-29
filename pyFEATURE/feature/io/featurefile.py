#!/usr/bin/env python
from __future__ import print_function
import re

import numpy as np

from six import StringIO
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

def rename_vector_from_comment(vector, comment):
    if vector.has_named_comment(comment):
        new_name = vector.get_named_comment(comment)
    vector.name = new_name
    return vector


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

    def __init__(self, items=[], *args, **kwargs):
        kwargs.setdefault('defaults', self.DEFAULTS)
        super(FeatureMetaData, self).__init__(items, *args, **kwargs)
        self.names_comment = None

    @property
    def _has_coords_comment(self):
        try:
            return self._found_coords_comment
        except AttributeError:
            setattr(self, '_found_coords_comment', COORDINANTS in self.comments)
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

    def create_vector_template(self):
        """ Generate an empty FEATURE vector object for the given metadata """
        if COORDINANTS in self.comments:
            comments = ["_"] * len(self.comments)
        else:
            comments = ["_"] * (len(self.comments) - 1)
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
        self._record_indexes(items, start=old_len)

    def get_by_name(self, name):
        index = self.indexes[name]
        vector = self[index]
        return vector

    def has_vector_named(self, name):
        return name in self.indexes


class ForwardFeatureFile(object):
    """ A lazy FEATURE file container  intended for iterating over large files """
    def __init__(self, metadata=None, vectors=[], 
                       set_name_from_comment=None):
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


def iload(src, container=ForwardFeatureFile, metadata=None, rename_from_comment=None):
    """ Create a lazy-loading FEATURE file from a stream """
    if metadata is None:
        metadata = FeatureMetaData()
    metadata, body = extract_metadata(src, container=metadata.set_raw_fields)
    if rename_from_comment:
        metadata.set_name_override_comment(rename_from_comment)
    parsed_vectors = _load_vectors_using_metadata(metadata, body)
    return container(metadata, parsed_vectors)


def load(src, container=FeatureFile, metadata=None, rename_from_comment=None):
    """ Create a FEATURE file from a stream """
    return iload(src, container=container, 
                      metadata=metadata,
                      rename_from_comment=rename_from_comment)


def loads(src, container=FeatureFile, metadata=None, rename_from_comment=None):
    """ Create a FEATURE file from a string """
    return load(src.splitlines(), container=container, 
                                  metadata=metadata,
                                  rename_from_comment=rename_from_comment)


def dump(data, io):
    """ Write  a FEATURE file to a stream """
    dump_metadata(data.metadata, io)
    _dump_vectors_using_metadata(data.metadata, data.vectors, io)


def dump_vector(vector, io, include_metadata=False):
    if include_metadata:
        dump_metadata(vector.metadata, io)
    _dump_vectors_using_metadata(vector.metadata, [vector], io)


def dumps(data):
    """ Wreite a FEATURE file to a string """
    buf = StringIO()
    dump(data, buf)
    return buf.getvalue()


def extract_line_components(line):
    """ Spilt the main components (name, features, comments)
        up in a FEATURE file vector line """
    parts = line.split("#")
    tokens = parts[0].strip().split("\t")
    comments = parts[1:]
    name, features = tokens[0], tokens[1:]
    return name, features, [c.strip() for c in comments]


def _load_vectors_using_metadata(metadata, lines):
    """ Using metadata as a guide, generate FEATURE vectors from lines """
    comment_fields = metadata.get('COMMENTS', DEFAULT_COMMENTS)
    if COORDINANTS in comment_fields:
        coords_at = comment_fields.index(COORDINANTS)
    else:
        coords_at = None

    if metadata.names_comment is not None:
        name_at = comment_fields.index(metadata.names_comment)
        if coords_at is not None:
            name_at -= 1
    else:
        name_at = None

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
        
        if name_at is not None:
            new_name = vector.comments[name_at]
            vector.name = new_name

        yield vector


def _dump_vectors_using_metadata(metadata, vectors, io):
    """ Using metadata as a guide generate FEATURE vector strings from a
        set of vectors and write to some stream """
    comment_fields = metadata.get('COMMENTS', DEFAULT_COMMENTS)
    try:
        coords_at = comment_fields.index(COORDINANTS)
    except ValueError:
        coords_at = 0
    for vector in vectors:
        print(vector.name, end='\t', file=io)
        print(*map("{:.3f}".format, vector.features), sep='\t', end='\t', file=io)
        comments = list(vector.comments)
        if vector.coords is not None:
            coords_str = "\t".join(['#'] + map("{:.3f}".format, vector.coords))
            comments.insert(coords_at, coords_str)
        print(*comments, sep='\t#\t', end='\n', file=io)
                

