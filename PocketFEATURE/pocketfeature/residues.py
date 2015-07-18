#!/usr/bin/env python
# This module needs some cleanup

from Bio.PDB.Polypeptide import three_to_one
from pocketfeature.utils.pdb import (
    atom_name, 
    average_coords,
    residue_name, 
)


# Each residue consists of some number of "centers" or active sits
# Each of which is defined by one or more atoms in the residue
DEFAULT_CENTER_ATOMS = {
    'GLY': [['CA']],
    'CYS': [['SG']],
    'ARG': [['CZ']],
    'SER': [['OG']],
    'THR': [['OG1']],
    'LYS': [['NZ']],
    'MET': [['SD']],
    'ALA': [['CB']],
    'LEU': [['CB']],
    'ILE': [['CB']],
    'VAL': [['CB']],
    'ASP': [['OD1', 'CG', 'OD2']],
    'GLU': [['OE1', 'CD', 'OE2']],
    'HIS': [['NE2', 'ND1']],
    'ASN': [['OD1', 'CG', 'ND2']],
    'PRO': [['N', 'CA', 'CB', 'CD', 'CG']],
    'GLN': [['OE1', 'CD', 'NE2']],
    'PHE': [['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ']],
    'TRP': [['NE1'],
            ['CD2', 'CE2', 'CE3', 'CZ2', 'CZ3', 'CH2']],
    'TYR': [['OH'],
            ['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ']],
}


DEFAULT_CLASSES = {
    'positive': (('ARG', 0), ('HIS', 0), ('LYS', 0)),
    'negative': (('ASP', 0), ('GLU', 0)),
    'polar': (('SER', 0), ('THR', 0), 
              ('ASN', 0), ('GLN', 0), 
              ('TYR', 0), ('TRP', 0)),
    'non-polar': (('ALA', 0), ('CYS', 0), 
                  ('GLY', 0), ('ILE', 0), 
                  ('LEU', 0), ('MET', 0), 
                  ('PRO', 0), ('VAL', 0)),
    'aromatic': (('TYR', 1), ('TRP', 1), ('PHE', 0)),
}


ALL_DEFAULT_CENTERS = [(res, idx) for res, sites in DEFAULT_CENTER_ATOMS.items()
                                  for idx in range(len(sites))]


def get_center_code(name, idx):
    letter = three_to_one(name)
    return "{0}{1}".format(letter, idx+1)


def get_center_codes(name, positions=(0,), get_code=get_center_code):
    return [get_code(name, i) for i in positions]


def get_center_code_set(residues_idx, centers=DEFAULT_CENTER_ATOMS):
    return [get_center_code(name, idx) for name, idx in residues_idx]


def load(io):
    raise NotImplementedError("Loading of ResiduePoints not yet operational")


class CenterCalculator(object):
    def __init__(self, centers=DEFAULT_CENTER_ATOMS,
                       classes=DEFAULT_CLASSES,
                       get_key=residue_name,
                       get_code=get_center_code,
                       get_name=atom_name,
                       get_point=average_coords,
                       ignore_unknown_residues=True,
                       strict=True):
        self.calculators = {}
        self.centers = centers
        self.classes = classes
        self.get_key = get_key
        self.normalize_key = str.upper
        self.get_code = get_code
        self.get_name = get_name
        self.get_point = get_point
        self.strict = strict
        self.ignore_unknown = ignore_unknown_residues

    def __getitem__(self, key):
        key = self.normalize_key(key)
        try:
            return self.calculators[key]
        except KeyError:
            if key in self.centers:
                fn = self._build_function(key)
                self.calculators[key] = fn
        return self.calculators[key]

    def _get_codes(self, key, indexes):
        return get_center_codes(key, indexes, get_code=self.get_code)
    
    def _build_function(self, key):
        key = self.normalize_key(key)
        centers = self.centers[key]
        num_centers = len(centers)
        codes = self._get_codes(key, range(num_centers))

        # Create reusable function to calculate center point(s)
        def fn(atoms, skip_partial_residues=True):
            strict = self.strict and not skip_partial_residues
            points = []
            for code, center_atoms in zip(codes, centers):
                found_atoms = [atom for atom in atoms 
                                    if self.get_name(atom) in center_atoms]
                if len(found_atoms) == len(center_atoms):
                    point = self.get_point(found_atoms)
                    points.append((code, point))
                elif strict:
                    try:
                        res = "/".join(map(str, atoms.get_full_id()))
                    except AttributeError:
                        res = atoms
                    atoms = list(atoms)
                    expected = center_atoms
                    raise ValueError("Missing atoms in {0} ({1}): {2} != {3}".format(code, res, atoms, expected))
            return points
        return fn

    def _build_functions(self):
        for key in self.centers.keys():
            key = self.normalize_key(key)
            self[key] = self._build_function(key)

    def _default_fn(self):
        return []

    def get_center(self, residue, ignore_unknown_residues=True, **kwargs):
        ignore_unknown = self.ignore_unknown or ignore_unknown_residues
        key = self.normalize_key(self.get_key(residue))
        try:
            fn = self[key]
            centers = fn(residue, **kwargs)
            return centers
        except KeyError:
            if ignore_unknown:
                return []
            else:
                raise ValueError("No residue centers defined for {0} and ignore disabled".format(key))

    def get_code_for(self, residue):
        key = self.normalize_key(self.get_key(residue))
        num_points = len(self.centers[key])
        codes = [self.get_code(key, idx) for idx in range(num_points)]
        return codes

    def get_class_codes(self, klass):
        return self.get_code_list(self.classes[klass])

    def get_code_list(self, residues_idx):
        return [code for key, idx in residues_idx
                     for code in self.get_code(key, idx)]

    def __call__(self, arg, **kwargs):
        return self.get_center(arg, **kwargs)


DEFAULT_CENTERS = CenterCalculator(DEFAULT_CENTER_ATOMS, DEFAULT_CLASSES)
get_residue_center_coords = DEFAULT_CENTERS.get_center


