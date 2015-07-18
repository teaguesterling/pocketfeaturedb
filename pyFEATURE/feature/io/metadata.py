#!python

from __future__ import print_function

import copy
from collections import OrderedDict, namedtuple
import operator
import itertools

from six import (
    string_types,
    iteritems,
    StringIO,
)

from feature.io.common import attempt_cast

LINE_TEMPLATE = "# {0}\t{1}"
CONTAINER_TYPES = (list, set, dict)


def _update_value(existing, value):
    if existing is None:
        return value

    existing_type = type(existing)
    if isinstance(existing, CONTAINER_TYPES):
        if not isinstance(value, CONTAINER_TYPES):
            value = [value]
        if hasattr(existing, 'redefine'):
            existing = existing.redefine(value)
        elif hasattr(existing, 'extend'):
            existing.extend(value)
        elif hasattr(existing, 'update'):
            existing.update(value)
        else:
            raise ValueError("Can't update container type {!r}".format(existing_type))
        return existing
    else:
        value = existing_type(value)
        return value


class MetaData(OrderedDict):

    def __init__(self, items=[], defaults=None, *args, **kwargs):
        super(MetaData, self).__init__(*args, **kwargs)
        if defaults is not None:
            self.update(copy.deepcopy(defaults))
        if isinstance(items, dict):
            self.update(items)
        else:
            for key, item in items:
                self[key] = item

    def modify(self, key, value):
        existing = self[key]
        changed = _update_value(existing, value)
        self[key] = changed
        return self[key]

    def set_raw(self, key, value):
        value = str(value)

        if "," in value:
            value = value.strip(",\n ")
            value = [s.strip() for s in value.strip(", \n").split(",")]

        if key in self:
            existing = self[key]
            existing_type = type(existing)
            if not isinstance(existing, (list, set, dict)):
                value = existing_type(value)
        elif isinstance(value, CONTAINER_TYPES):
            casts = [attempt_cast(v, default=str) for v in value]
            value = map(operator.itemgetter(1), casts)
        elif isinstance(value, string_types):  # Parsed above
            new_type, value = attempt_cast(value, default=str)
        else:
            raise ValueError("Received unexpected raw type (should be string)")

        if key in self:
            return self.modify(key, value)
        else:
            self[key] = value
            return self[key]

    def set_raw_fields(self, fields):
        for key, value in fields:
            self.set_raw(key, value)
        return self

    @classmethod
    def from_raw_fields(cls, fields, defaults=None, *args, **kwargs):
        kwargs.setdefault('defaults', defaults)
        obj = cls(*args, **kwargs)
        obj.set_raw_fields(fields)
        return obj

    @classmethod
    def clone_defaults(cls, _extend_lists=True, **changes):
        new = copy.deepcopy(getattr(cls, 'DEFAULTS', {}))
        for key, value in iteritems(changes):
            if key in new and _extend_lists:
                existing = new[key]
                value = _update_value(existing, value)
            new[key] = value
        return new


    @classmethod
    def clone_defaults_extend(cls, **changes):
        return cls.clone_defaults(_extend_lists=True, **changes)

    @classmethod
    def clone_defaults_overwrite(cls, **changes):
        return cls.clone_defaults(_extend_lists=False, **changes)


def is_metadata_line(line):
    return line.startswith('#')


def split_line_components(line):
    tokens = line.split('#', 1)
    return tokens[1].split(None, 1)


def get_metadata(source, split=split_line_components):
    for line in source:
        tokens = split(line.strip())
        try:
            key = tokens[0]
            value = tokens[1] if len(tokens) > 1 else None
        except ValueError:
            continue
        else:
            yield key, value


def extract_metadata(source,
                     is_metadata=is_metadata_line,
                     parser=get_metadata,
                     container=MetaData.from_raw_fields):
    """
    extract_metadata(iterator) -> container, iterator
    Split an iterator with FEATURE-style meta data into a dictionary of all
    meta data lines and an iterator containing the remainder of the source
    """

    # Split the source, assuming metadata is at the beginning
    # (Keep only the group data, i)
    grouping = itertools.groupby(source, key=is_metadata)
    #grouping = itertools.imap(operator.itemgetter(1), grouping)
    has_metadata, first_group = next(grouping)
    if has_metadata:
        # We need to strictly consume all the group members here or
        # they will be lost to the groupby iterator process
        metadata_lines = list(first_group)
        _, body_iterator = next(grouping)
    else:
        # Use the first group if no metadata was seen
        metadata_lines = []
        body_iterator = first_group

    parsed = load(metadata_lines,
                  is_metadata=is_metadata,
                  container=container,
                  parser=parser)
    return parsed, body_iterator


def load(io, is_metadata=is_metadata_line,
             parser=get_metadata,
             container=MetaData.from_raw_fields):
    data = parser(line for line in io if is_metadata(line))
    return container(data)


def loads(data, **kwargs):
    return load(data.splitlines(), **kwargs)


def dump(metadata, io):
    for key, value in metadata.items():
        if isinstance(value, CONTAINER_TYPES):
            if hasattr(value, 'items'):
                value = [":".join(pair) for pair in value.items()]
            value = map(str, list(value))
            value = ",".join(value)
        else:
            value = str(value)
        print(LINE_TEMPLATE.format(key, value), file=io)


def dumps(metadata):
    buf = StringIO()
    dump(metadata, buf)
    return buf.getvalue()

