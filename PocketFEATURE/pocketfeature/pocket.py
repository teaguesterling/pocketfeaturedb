#!/usr/bin/env python

from feature.io.pointfile import PDBPoint

from pocketfeature.utils.ff import residue_code_three_to_one
from pocketfeature.residues import DEFAULT_CENTERS


class Pocket(object):
    """ Representation of a PocketFEATURE pocket as a list of 
        residues from a PDB, an (optional) defining ligand, and
        a method of mapping residues to active sites
    """

    def __init__(self, residues, pdbid=None,
                                 defined_by=None,
                                 name=None,
                                 residue_centers=DEFAULT_CENTERS,
                                 skip_partial_residues=True):
        self._pdbid = pdbid
        self._residues = residues
        self._defined_by = defined_by
        self._name = name
        self._centers = residue_centers
        self._skip_partial_residues = skip_partial_residues

    @property
    def pdbid(self):
        return self._pdbid

    @property
    def residues(self):
        return self._residues

    @property
    def defined_by(self):
        return self._defined_by

    @property
    def name(self):
        return self._name

    @property
    def points(self):
        for residue in self.residues:
            pdbid = self._getResiduePdb(residue)
            points = self._get_microenvironments(residue)
            for point_type, point in points:
                comment = self._getResidueComment(residue, point_type)
                yield PDBPoint(*point, pdbid=pdbid, comment=comment)

    @property
    def signature(self):
        if self.defined_by is not None:
            ligpdbid, ligmodel, ligchain, ligid = self.defined_by.get_full_id()
            lighet, lignum, ligins = ligid
            ligname = self.defined_by.get_resname()
        else:
            ligpdbid, ligmodel, ligchain = '-', '-', '-'
            lighet, lignum, ligins = '-', '-', 0
            ligname = '?'
        if self.name is not None:
            ligname = self.name

        return (self.pdbid, ligchain, lignum, ligname)

    @property
    def signature_string(self):
        return "_".join(map(str, self.signature))

    def _get_microenvironments(self, residue):
        skip = self._skip_partial_residues
        return self._centers(residue, skip_partial_residues=skip)

    def setResidueCenters(self, residue_centers):
        self._centers = residue_centers

    def _getResiduePdb(self, residue):
        if self.pdbid is not None:
            return self.pdbid
        else:
            return residue.get_full_id()[0]

    def _getResidueComment(self, residue, point_type):
        respdbid, resmodel, reschain, resid = residue.get_full_id()
        reshet, resnum, resins = resid
        resname = residue.get_resname().upper()
        resletter, idx = point_type
        res_sig = "_".join(str(x).strip() for x in (resnum, resletter, idx, reschain))
        point_sig = self.signature_string + '_' + res_sig

        return "\t#\t".join((point_sig, point_type))


