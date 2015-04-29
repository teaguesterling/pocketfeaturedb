#!/usr/bin/env python
from __future__ import print_function

from collections import OrderedDict
import operator

import numpy as np

from six import (
    iteritems,
    StringIO,
)
from feature.io import metadata

from pocketfeature.algorithms import Indexer


def _parse_entry(line, dims=2, delimiter=None):
    tokens = line.split(delimiter)
    key = tokens[:dims]
    value = tokens[dims:]
    return (key, value)


def _get_value_columns(values, accepted, cast):
    if accepted is not None:
        values = [values[idx] for idx in accepted]
    if len(values) == 0:
        return 1, None
    elif len(values) == 1:
        return 1, cast(values[0])
    else:
        values = tuple(map(cast, values))
        return len(values), values
    

class MatrixValues(OrderedDict):
    """ A cheap attempt at storing sparse matrix information """    
    def __init__(self, entries=[], indexes=None, value_dims=None, 
                       default=None, metadata=None):
        if indexes is None:
            indexes = []
        self.indexes = indexes 
        self.metadata = metadata
        super(MatrixValues, self).__init__(entries)
        # Try to guess correct "shape" from first provided key
        if value_dims is None:
            try:
                some_key = list(self.keys())[0]
                if isinstance(self[some_key], (list, tuple)):
                    value_dims = len(self[some_key])
                else:
                    value_dims = 1
            except IndexError:
                value_dims = 1
            dim_refs = {}
        elif isinstance(value_dims, (list, tuple)):
            dim_refs = dict(reversed(pair) for pair in enumerate(value_dims))
            value_dims = len(value_dims)
        else:
            dim_refs = {}
        self.value_dims = value_dims
        self.dim_refs = dim_refs
        self.shape = [len(dim) for dim in indexes]
        self.shape = self.shape + [self.value_dims]
        self.default = default

    def _get_indexer(self, i):
        try:
            return self.indexes[i]
        except IndexError:
            for j in range(i - len(self.indexes) + 1):
                self.indexes.append(Indexer())
            return self.indexes[i]

    def __setitem__(self, key, value):
        super(MatrixValues, self).__setitem__(key, value)
        for i, dim in enumerate(key):
            self._get_indexer(i).add(dim)

    def to_array(self, default=0, dtype=float):
        #raise NotImplementedError("Method does not yet work for some strange reason")
        if default == 0:
            matrix = np.zeros(self.shape, dtype=dtype)
        else:
            matrix = default * np.ones(self.shape, dtype=dtype)
        for key, value in iteritems(self):
            coords = tuple(self.indexes[i][pos] for i, pos in enumerate(key))
            matrix[coords] = value
        return matrix

    def slice_values(self, index, value_dims=None):
        cls = type(self)
        if index in self.dim_refs:
            index = self.dim_refs[index]
        items = ((k, v[index]) for k, v in iteritems(self))
        values = cls(items, value_dims=value_dims)
        return values

    def subset_from_keys(self, keys):
        cls = type(self)
        items = ((k, self[k]) for k in keys)
        values = cls(items, value_dims=self.value_dims)
        return values

    def subset_from_indexes(self, subset):
        """ Create a new matrixvaluesfile from a subset of keys """
        cls = type(self)
        indexes = [index.flip() for index in self.indexes]
        items = []
        for idx in subset:
            key = tuple(indexes[i][j] for i,j in enumerate(idx))
            if key in self:
                value = self[key]
                items.append((key, value))
        values = cls(items, value_dims=self.value_dims)
        return values

    @classmethod
    def from_array(cls, matrix, default=0, indexes=None, include_defaults=False):
        entries = []
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                if value != default or include_defaults:
                    entries.append(((i,j), value))
        return cls(entries, indexes)

    def __repr__(self):
        return 'MatrixValues({0})'.format(repr(self.items()))


class PassThroughItems(object):
    def __init__(self, entries=[], indexes=[], dims=2, value_dims=[], dim_refs={}, metadata=None):
        self.dims = dims
        self.indexes = indexes
        self.value_dims = value_dims
        self.dim_refs = dim_refs
        self.entries = entries
        self.metadata = metadata

    def iteritems(self):
        return self.entries

    def items(self):
        return self.entries


def load(io, dims=2, delimiter=None, 
                     columns=None, 
                     cast=None, 
                     make_key=tuple, 
                     value_dims=None, 
                     header=False,
                     load_metadata=False):
    if load_metadata:
        metadata, io = extract_metadata(io)
    else:
        metadata = None
    if not header and metadata is not None:
        column_names = metadata.get('COLUMNS')

    positions = []
    indexes = [Indexer() for i in range(dims)]
    if header:
        column_names = next(io).split(delimiter)[dims:]
        if columns is not None:
            columns = [column_names.index(name) if isinstance(column, string_types) else column for column in columns]
    else:
        column_names = None
    columns = list(columns) if columns is not None else None
    cast = cast if cast is not None else lambda x: x
    value_count = 0
    for entry in io:
        keys, values = _parse_entry(entry, dims=dims, delimiter=delimiter)
        num_values, values = _get_value_columns(values, columns, cast)
        keys = make_key(keys)
        value_count = max(value_count, num_values)
        for i, index in enumerate(indexes):
            index.add(keys[i])
        positions.append((keys, values))

    if value_dims is not None:
        value_dims = value_dims  # TODO: Clip and test
    elif column_names is not None:
        value_dims = column_names
    else:
        value_dims = value_count

    return MatrixValues(positions, indexes, value_dims=value_dims)


def dump(matrix_values, io, delimiter="\t", columns=None, tpl="{:.3f}", header=False):
    columns = set(columns) if columns is not None else None
    if header and len(matrix_values.dim_refs) > 0:
        row = ["INDEX"] * matrix_values.dims
        dims = sorted(matrix_values.dim_refs.items(), key=operator.itemgetter(0))
        row.extend(str(dim[1]) for dim in dims)
        print(delimiter.join(row), file=io)
    for key, values in iteritems(matrix_values):
        if matrix_values.value_dims == 1:
            values = (values,)
        if columns is not None:
            values = [item for i, item in enumerate(values) if i in columns]
        row = list(key) + map(tpl.format, values)
        print(delimiter.join(row), file=io)


def dumps(values, delimiter="\t", columns=None, tpl="{:f}"):
    buf = StringIO()
    dump(values, buf, delimiter=delimiter, columns=columns, tpl=tpl)
    return buf.getvalue()


