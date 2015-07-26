from __future__ import absolute_import

import argparse
from gettext import gettext as _
import gzip

from .compressed import (
    decompress,
    open_compressed,
)


class FileType(argparse.FileType):
    def __init__(self, mode='r',
                       bufsize=-1,
                       encoding=None,
                       errors=None,
                       opener=open,
                       wrapper=None,
                       extraargs=None):
        super(FileType, self).__init__(mode=mode)
        if extraargs is None:
            extraargs = {}
        if wrapper is None:
            wrapper = lambda s: s
        self._wrapper = wrapper
        self._opener = opener
        self._extraargs = extraargs

    def __call__(self, string):
        if string == '-':
            stream = super(FileType, self).__call__(string)
        else:
            try:
                stream = self._opener(string, self._mode, **self._extraargs)
            except OSError as e:
                message = _("can't open '%s': %s")
                raise argparse.ArgumentTypeError(message % (string, e))
        wrapped = self._wrapper(stream)
        return wrapped

    @classmethod
    def compressed(cls, mode='r', **kwargs):
        return cls(mode=mode, opener=open_compressed,
                              wrapper=decompress,
                              **kwargs)

    @classmethod
    def gzip(cls, mode='rb', compresslevel=9, **kwargs):
        return cls(mode=mode, opener=gzip.open,
                              extraargs={'compresslevel': compresslevel},
                              **kwargs)
