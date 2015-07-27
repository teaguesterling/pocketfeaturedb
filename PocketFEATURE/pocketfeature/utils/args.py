from argparse import ArgumentTypeError
from gettext import gettext as _

from taskbase import (
    FileType,
    is_normal_file,
    decompress,
    open_compressed,
)

from feature.io.locate_files import (
    find_pdb_file,
    find_dssp_file,
)


def comma_delimited_list(data):
    return data.split(',')


class ProteinFileType(FileType):
    TYPES = {
        'pdb': find_pdb_file,
        'dssp': find_dssp_file,
    }

    def __init__(self, file_format='pdb', mode='r', *args, **kwargs):
        super(ProteinFileType, self).__init__(mode=mode, **kwargs)
        self.file_format = file_format.lower()
        self.locate = self.TYPES[self.file_format]

    def __call__(self, string):
        if string == '-':
            name = string
            stream = super(ProteinFileType, self).__call__(string)
        else:
            try:
                located = self.locate(string)
                stream = self._opener(located, self._mode, **self._extraargs)
            except OSError as e:
                message = _("can't open '%s': %s")
                raise ArgumentTypeError(message % (string, e))
            except ValueError as e:
                message = _("Couldn't locate {0} file {1}: {2}".format(self.file_format, string, e))
                raise ArgumentTypeError(message)
        wrapped = self._wrapper(stream)
        return wrapped

