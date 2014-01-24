import argparse
from gettext import gettext as _
import gzip
import os

from feature.io.common import (
    decompress,
    open_compressed,
)


def is_normal_file(stream):
    if hasattr(stream, 'isatty') and stream.isatty():
        return False
    if hasattr(stream, 'name') and os.path.exists(stream.name):
        return True
    return False


class FileType(argparse.FileType):
    def __init__(self, mode='r', 
                       bufsize=-1, 
                       encoding=None, 
                       errors=None, 
                       opener=open,
                       wrapper=None, 
                       extraargs=None):
        print("INIT")
        super(FileType, self).__init__(mode=mode)
        if extraargs is None:
            extraargs = {}
        if wrapper is None:
            wrapper = lambda s: s
        self._wrapper = wrapper
        self._opener = opener
        self._extraargs = extraargs
        print("DONE")

    def __call__(self, string):
        print ("CALL")
        if string == '-':
            stream = super(FileType, self).__call__(string)
        try:
            stream = self._opener(string, **self._extraargs)
        except OSError as e:
            message = _("can't open '%s': %s")
            raise ArgumentTypeError(message % (string, e))
        wrapped = self._wrapper(stream)
        return wrapper

    @classmethod
    def compressed(cls, mode='r'):
        return cls(mode=mode, opener=open_compressed, 
                              wrapper=decompress)

    @classmethod
    def gzip(cls, mode='rb', compresslevel=9):
        return cls(mode=mode, opener=gzip.open,
                              extraargs={'compresslevel': compresslevel})
        
    
