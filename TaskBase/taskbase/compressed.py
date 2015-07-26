from __future__ import absolute_import
import gzip
from io import BufferedReader
import os


GZIP_MAGIC = "\x1f\x8b"


def is_normal_file(stream):
    if hasattr(stream, 'isatty') and stream.isatty():
        return False
    if hasattr(stream, 'name') and os.path.exists(stream.name):
        return True
    return False


def decompress(stream):
    """ Try to read determine if a stream is compressed,
        if so use Gzip to decompress. Otherwise simply pass though
    """
    if isinstance(stream, gzip.GzipFile):
        magic = None
        checked = stream
    elif hasattr(stream, 'peek'):
        magic = stream.peek(2)
        checked = stream
    elif hasattr(stream, 'buffer'):
        buffered = stream.buffer
        magic = buffered.peek(2)
        checked = buffered
    else:
        try:
            buffered = BufferedReader(stream)
            magic = buffered.peek(2)
            checked = buffered.detach()
        except AttributeError as e:
            checked = stream
            magic = None

    if magic == GZIP_MAGIC:
        decompressed = gzip.GzipFile(fileobj=checked)
    # TODO: Other compression methods
    else:
        decompressed = checked
    return decompressed


def open_compressed(path, mode='r', **options):
    """ Determine if a given path should be opened with gzip """
    if path.endswith('.gz'):
        # Must open gzipped files in binary
        #if not mode.endswith('b'):
        #    mode += 'b'
        return gzip.open(path, mode=mode, **options)
    else:
        return open(path, mode=mode, **options)
