from __future__ import absolute_import, print_function

import itertools

from six import moves

from feature.datastructs.metadata import (
    MetaData,
    CONTAINER_TYPES,
)

LINE_TEMPLATE = "# {0}\t{1}"

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
    class in_metadata(object):
        def __init__(self):
            self.in_metadata = True
        def __call__(self, line):
            if not is_metadata(line):
                self.in_metadata = False
            return self.in_metadata

    # Split the source, assuming metadata is at the beginning
    # (Keep only the group data, i)
    grouping = itertools.groupby(source, key=in_metadata())
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
    buf = moves.StringIO()
    dump(metadata, buf)
    return buf.getvalue()

