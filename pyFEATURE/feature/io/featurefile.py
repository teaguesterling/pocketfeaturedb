from __future__ import absolute_import, print_function

from six import moves
from feature.io.metadata import dump as dump_metadata
from feature.io.metadata import extract_metadata

from feature.datastructs.features import (
    FeatureMetaData,
    FeatureFile,
    ForwardFeatureFile,
    COORDINANTS,
    DESCRIPTION,
    DEFAULT_COMMENTS,
)


def rename_vector_from_comment(vector, comment):
    if vector.has_named_comment(comment):
        new_name = vector.get_named_comment(comment)
        vector.name = new_name
    return vector


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
    buf = moves.StringIO()
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
                

