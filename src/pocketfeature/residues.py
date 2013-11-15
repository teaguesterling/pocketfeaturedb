#!/usr/bin/env python
# This module needs some cleanup

from pdb_utils import (
    atom_name, 
    average_coords,
    residue_name, 
)


CENTERS = {
    'GLY': 'CA',
    'CYS': 'SG',
    'ARG': 'CZ',
    'SER': 'OG',
    'THR': 'OG1',
    'LYS': 'NZ',
    'MET': 'SD',
    'ALA': 'CB',
    'LEU': 'CB',
    'ILE': 'CB',
    'VAL': 'CB',
    'ASP': ('OD1', 'CG', 'OD2'),
    'GLU': ('OE1', 'CD', 'OE2'),
    'HIS': ('NE2', 'ND1'),
    'ASN': ('OD1', 'CG', 'ND2'),
    'PRO': ('N', 'CA', 'CB', 'CD', 'CG'),
    'GLN': ('OE1', 'CD', 'NE2'),
    'PHE': ('CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ'),
    'TRP': (('CD2', 'CE2', 'CE3', 'CZ2', 'CZ3', 'CH2'),
            ('NE1',)),
    'TYR': (('CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ'),
            ('OH',)),
}


def center_at(*names):

    def calculate_fn(atoms):
        atoms = [atom for atom in atoms if atom_name(atom) in names]
        if len(atoms) == len(names):  # If make sure no atoms were missing
            return average_coords(atoms)
        else:
            return None
    return calculate_fn


def apply_center_fns(*center_fns):
    def calculate_fn(atoms):
        return [center_fn(atoms) for center_fn in center_fns]
    return calculate_fn


def atoms_to_center_fn(center_positions):
    # No positions for empty or definitions
    if not center_positions:
        center_fns = (center_at(),)
    # Center on specific atom
    elif isinstance(center_positions, basestring):
        center_fns = (center_at(center_positions),)
    # Center on a set of points
    elif all(isinstance(pos, basestring) for pos in center_positions):
        center_fns = (center_at(*center_positions),)
    # Multiple centers
    else:
        center_fns = [center_at(*atoms) for atoms in center_positions]

    return apply_center_fns(*center_fns)


def load(io):
    raise NotImplementedError("Loading of ResiduePoints not yet operational")


class CenterCalculator(dict):
    def __init__(self, centers=CENTERS):
        super(CenterCalculator, self).__init__(self._build_functions(centers))
        self.centers = centers

    def _build_functions(self, centers):
        for residue, center in centers.items():
            name = residue.upper()
            fn = atoms_to_center_fn(center)
            yield (name, fn)

    def get_center(self, residue):
        name = residue_name(residue).upper()
        fn = self[name]
        center = fn(residue)
        return center

    def __call__(self, arg):
        return self.get_center(arg)


CENTER_FUNCTIONS = CenterCalculator(CENTERS)
get_residue_center_coords = CENTER_FUNCTIONS.get_center

