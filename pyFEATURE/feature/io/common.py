#!python

import contextlib
import gzip
from io import BufferedReader
import itertools

GZIP_MAGIC = "\x1f\x8b"

def decompress(stream):
    """ Try to read determine if a stream is compressed, 
        if so use Gzip to decompress. Otherwise simply pass though
    """
    if hasattr(stream, 'buffer'):
        buffered = stream.buffer
        magic = buffered.peek(2)
        checked = buffered
    else:
        try:
            buffered = BufferedReader(stream)
            magic = buffered.peek(2)
            checked = buffered
        except AttributeError as e:
            checked = stream
            magic = None

    if magic == GZIP_MAGIC:
        decompressed = gzip.GzipFile(fileobj=checked)
    # TODO: Other compression methods
    else:
        decompressed = stream
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


def attempt_cast(value, types=(int, float, complex), default=None):
    """ Given a list of types, attempt to cast to all until one is 
        successful. Otherwise return default.
    """
    for attempt in types:
        try:
            return attempt, attempt(value)
        except ValueError:
            pass
    return (default, default(value)) if default is not None else (None, None)


# EVERYTHING BELOW HERE IS EXPERIMENTAL... OR DOESN'T WORK

class splitby(object):
    # [k for k, g in splitby('AAAABBBCCDAABBB')] --> A B C D A B
    # [list(g) for k, g in splitby('AAAABBBCCD')] --> AAAA BBB CC D
    def __init__(self, iterable,
                 key=None,
                 with_keys=True,
                 expand=None,
                 limit=None):
        if key is None:
            key = lambda x: x
        if expand is None or expand == False:
            expand = self.__freeze_group
        elif expand is True:
            expand = list

        self.keyfunc = key
        self.with_keys = with_keys
        self.expand = expand
        self.limit = limit
        self.it = iter(iterable)
        self.marker = None
        self.targetkey = self.currkey = self.currvalue = object()
        self._set_mark()

    def __iter__(self):
        return self

    def _set_mark(self):
        self.marker, self.it = itertools.tee(self.it)

    def __freeze_group(self, group):
        self.marker, group = itertools.tee(self.marker)
        return group

    def next(self):
        while self.currkey == self.targetkey:
            self.currvalue = next(self.it)    # Exit on StopIteration
            self.currkey = self.keyfunc(self.currvalue)
        self.targetkey = self.currkey
        self._set_mark()
        return self._get_group()

    def _get_group(self):
        group = self.expand(self._grouper(self.targetkey))
        return (self.currkey, group) if self.with_keys else group

    def _grouper(self, targetkey):
        inner = self.marker
        currkey = self.currkey
        currvalue = self.currvalue
        while currkey == targetkey:
            yield currvalue
            currvalue = next(inner)    # Exit on StopIteration
            currkey = self.keyfunc(currvalue)


def iter_split(data,
               key=None,
               include_keys=True,
               expand_groups=False,
               limit=None):
    groups = []
    keys = []

    # If user chooses not to expand groups, create a new iterator (checkpoint)
    # for the current group using tee.
    # NOTE: This is not efficient in the event of many large groups
    if expand_groups:
        make_group = list
    else:
        make_group = lambda g: itertools.tee(g)

    for k, g in itertools.groupby(data, key):
        keys.append(k)
        if expand_groups:
            groups.append(list(g))
        else:
            g, checkpoint = itertools.tee(g)
            groups.append(checkpoint)
        

        if limit == 0:
            break
        if limit is not None:
            limit -= 1

    if include_keys:
        return zip(keys, groups)
    else:
        return groups
