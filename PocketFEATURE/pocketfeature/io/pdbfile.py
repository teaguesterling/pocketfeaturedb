from __future__ import absolute_import

import gzip
import os
from Bio.PDB.PDBParser import PDBParser
from pocketfeature.utils.pdb import guess_pdbid_from_stream


class PDBReader(object):
    """ Collection of helper methods for loading PDBs """
    PARSER = PDBParser(PERMISSIVE=True, QUIET=True)

    @classmethod
    def pdbIdFromFilename(cls, path, override=None):
        base, ext = os.path.basename(path).split(".", 1)
        if base.startswith('ent'):  # Trim off old-style prefix
            base = base[3:]
        return base

    @classmethod
    def fromStream(cls, stream, pdbid):
        return cls.PARSER.get_structure(pdbid, stream)

    @classmethod
    def fromFile(cls, path, pdbid=None):
        pdbid = cls.pdbIdFromFilename(path) if pdbid is None else pdbid
        opener = gzip.open if path.endswith('.gz') else open
        with opener(path) as f:
            return cls.fromStream(f, pdbid)


def load(io, pdbid=None):
    if pdbid is None:
        pdbid, io = guess_pdbid_from_stream(io)
    return PDBReader.fromStream(io, pdbid)

def load_file(path, mode='r', pdbid=None):
    return PDBReader.fromFile(path, pdbid=pdbid)

