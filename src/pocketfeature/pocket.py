#!/usr/bin/env python

from feature.io.pointfile import PDBPoint

from pocketfeature.ff_utils import (
    residue_code_three_to_one,
    residue_to_typecode,
)
from pocketfeature.residues import CENTER_FUNCTIONS

class Pocket(object):

    def __init__(self, residues, pdbid=None,
                                 defined_by=None,
                                 name=None,
                                 residue_points=CENTER_FUNCTIONS):
        self._pdbid = pdbid
        self._residues = residues
        self._defined_by = defined_by
        self._name = name
        self._getResidueCenters = residue_points

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
            points = self._getResidueCenters(residue)
            for i, point in enumerate(points, 1):
                comment = self._getResidueComment(residue, i)
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

    def setResidueCenters(self, residue_points):
        self._getResidueCenters = residue_points

    def _getResiduePdb(self, residue):
        if self.pdbid is not None:
            return self.pdbid
        else:
            return residue.get_full_id()[0]

    def _getResidueComment(self, residue, idx=1):
        respdbid, resmodel, reschain, resid = residue.get_full_id()
        reshet, resnum, resins = resid
        resname = residue.get_resname().upper()
        try:
            resletter = residue_code_three_to_one(resname)
        except KeyError:
            resletter = '?'
        point_id = self.signature + (resnum, resletter, idx, reschain)
        point_id_text =  "_".join([str(token).strip() for token in point_id])
        point_type_text = residue_to_typecode(residue, idx)

        return " ".join((point_id_text, point_type_text))


