from Bio.PDB.PDBParser import PDBParser

import gzip
import os

from pocketfeature.utils.pdb import guess_pdbid_from_stream


class PDBFocus(object):
    """ Provides a consistent interface for looking at a specific model or
        chain in a BioPython PDB Structure that can be easily changed.
        TODO: add a facility for easy iteraton (i.e. "next")
    """
    def __init__(self, structure, model_id=0, chain_id=0):
        self._structure = structure
        self.setFocus(model_id, chain_id)

    @property
    def structure(self):
        return self._structure

    @property
    def model(self):
        if self._model_id is not None:
            return self.structure.get_list()[self._model_id]
        else:
            return None

    @property
    def chain(self):
        if self._chain_id is not None:
            return self.model.get_list()[self._chain_id]
        else:
            return None

    @property
    def focus(self):
        if self._model_id is None:
            return self.structure
        elif self._chain_id is None:
            return self.model
        else:
            return self.chain

    @property
    def residues(self):
        return self.get_residues()

    @property
    def atoms(self):
        return self.get_atoms()

    def get_residues(self):
        if self._chain_id is None:  # Chain has no get_resiude method
            return self.focus.get_residues()
        else:
            return self.focus.get_list()

    def get_atoms(self):
        return self.focus.get_atoms()

    def setFocus(self, model_id=None, chain_id=None):
        """ PdbFcus.setFocus(int) -> None

        Sets the model that will be used for nearest-neighbor searching.
        If model_id is none, all models will be searched while generating
        pockets.

        """
        if model_id is not None:
            if model_id >= len(self.structure.get_list()):
                raise ValueError("Invalid model_id: {0}".format(model_id))
            else:
                self._model_id = model_id

            if isinstance(chain_id, basestring):
                chains = enumerate(self.model.get_list())
                found = [cid for cid in chains if cid[1].get_id() == chain_id]
                if found:
                    self._chain_id = found[0][0]
                else:
                    raise ValueError("Invalid chain_id: {0}".format(chain_id))
            elif isinstance(chain_id, int):
                if chain_id >= len(self.model.get_list()):
                    raise ValueError("Invalid chain_id: {0}".format(chain_id))
                self._chain_id = chain_id
            elif chain_id is None:
                self._chain_id = None
            else:
                raise ValueError("Invalid chain_id: {0}".format(chain_id))
        else:
            self._model_id = None
            self._chain_id = None


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

