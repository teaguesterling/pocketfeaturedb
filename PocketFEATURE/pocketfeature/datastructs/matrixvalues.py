from __future__ import print_function

from six import iteritems
from collections import OrderedDict

import numpy as np

from pocketfeature.algorithms import Indexer


class MatrixValues(OrderedDict):
    """ A cheap attempt at storing sparse matrix information """
    def __init__(self, entries=(), indexes=None, value_dims=None,
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
    def __init__(self, entries=(), indexes=(), dims=2, value_dims=(), dim_refs=None, metadata=None):
        dim_refs = dim_refs or {}
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

