#!/usr/bin/env python

from __future__ import absolute_import, print_function

import operator

from six import (
    iteritems,
    string_types,
    moves as six_moves
)

from feature.io import metadata

from pocketfeature.algorithms import Indexer
from pocketfeature.datastructs.matrixvalues import MatrixValues


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


def load(io, dims=2, delimiter=None, 
                     columns=None, 
                     cast=None, 
                     make_key=tuple, 
                     value_dims=None, 
                     header=False,
                     load_metadata=False):
    if load_metadata:
        md, io = metadata.extract_metadata(io)
    else:
        md = None
    column_names = None
    if not header and md is not None:
        column_names = md.get('COLUMNS')

    positions = []
    indexes = [Indexer() for _ in range(dims)]
    if header:
        column_names = next(io).split(delimiter)[dims:]
        if columns is not None:
            columns = [column_names.index(col) if isinstance(col, string_types) else col for col in columns]

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
    buf = six_moves.StringIO()
    dump(values, buf, delimiter=delimiter, columns=columns, tpl=tpl)
    return buf.getvalue()


