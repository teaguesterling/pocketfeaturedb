import argparse
from argparse import ArgumentTypeError
from collections import OrderedDict
from gettext import gettext as _
import gzip
import logging
import os

from feature.io.common import (
    decompress,
    open_compressed,
)

from feature.io.locate_files import (
    find_pdb_file,
    find_dssp_file,
)

LOG_LEVELS = {logging.getLevelName(level).lower(): level for level in range(10, 60, 10)}


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
        try:
            stream = self._opener(string, mode=self._mode, **self._extraargs)
        except OSError as e:
            message = _("can't open '%s': %s")
            raise ArgumentError(message % (string, e))
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
        
    
class ProteinFileType(FileType):
    TYPES = {
        'pdb': find_pdb_file,
        'dssp': find_dssp_file,
    }

    def __init__(self, file_format='pdb', mode='r', *args, **kwargs):
        super(ProteinFileType, self).__init__(mode=mode, *args, **kwargs)
        self.file_format = file_format.lower()
        self.locate = self.TYPES[self.file_format]

    def __call__(self, string):
        if string == '-':
            stream = super(FileType, self).__call__(string)
        try:
            located = self.locate(string)
            stream = self._opener(located, mode=self._mode, **self._extraargs)
        except OSError as e:
            message = _("can't open '%s': %s")
            raise ArgumentTypeError(message % (string, e))
        except ValueError as e:
            message = _("Couldn't locate {0} file {1}: {2}".format(self.file_format, string, e))
            raise ArgumentTypeError(message)
        wrapped = self._wrapper(stream)
        return wrapped

