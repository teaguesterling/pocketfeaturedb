#!/usr/bin/env python
from __future__ import absolute_import

import itertools

from Bio.PDB.Polypeptide import three_to_one
from pocketfeature.utils.pdb import (
    atom_name, 
    average_coords,
    residue_name, 
)


def get_center_code(name, idx, start=1):
    if start < 0:
        start = -start
        default_first = True
    else:
        default_first = False
    letter = three_to_one(name)
    if idx == 0 and default_first:
        num = ""
    else:
        num = idx + start
    return "{0}{1}".format(letter, num)


def get_center_codes(name, positions=(0,), get_code=get_center_code, **kwargs):
    return [get_code(name, i, **kwargs) for i in positions]


def get_center_code_set(residues_idx, centers, get_code=get_center_code, **kwargs):
    print locals()
    return [get_center_code(name, idx, **kwargs) for name, idx in residues_idx]


def make_vector_type_key(vector_types):
    return tuple(sorted(map(str, vector_types)))


def make_allowed_pair_sets(sets, get_code=get_center_code, **kwargs):
    pairs = []
    for single_set, residue_indices in sets.items():
        code_set = [get_code(res_name, res_idx, **kwargs) for res_name, res_idx in residue_indices]
        for codes in itertools.combinations_with_replacement(code_set, 2):
            type_key = make_vector_type_key(codes)
            pairs.append(type_key)
    return set(pairs)


class CenterCalculator(object):
    def __init__(self, centers, classes,
                 get_key=residue_name,
                 get_code=get_center_code,
                 get_name=atom_name,
                 get_point=average_coords,
                 ignore_unknown_residues=True,
                 start_numbers=1,
                 strict=True):
        self.calculators = {}
        self.centers = centers
        self.classes = classes
        self._get_key = get_key
        self._get_code = get_code
        self.get_name = get_name
        self.get_point = get_point
        self.strict = strict
        self.ignore_unknown = ignore_unknown_residues
        self._key_args = {
            'start': start_numbers,
        }

    def __getitem__(self, key):
        key = self.normalize_key(key)
        try:
            return self.calculators[key]
        except KeyError:
            if key in self.centers:
                fn = self._build_function(key)
                self.calculators[key] = fn
        return self.calculators[key]

    def normalize_key(self, key):
        return key.upper()

    def get_key(self, *args):
        return self._get_key(*args)

    def get_code(self, *args):
        return self._get_code(*args, **self._key_args)

    def get_codes(self, key, indexes):
        kwargs = self._key_args.copy()
        kwargs['get_code'] = self._get_code
        return get_center_codes(key, indexes, **kwargs)
    
    def _build_function(self, key):
        key = self.normalize_key(key)
        centers = self.centers[key]
        num_centers = len(centers)
        codes = self.get_codes(key, range(num_centers))

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

    def get_all_center_ids(self):
        return [(res_name, idx) for res_name, centers in self.centers for idx in range(len(centers))]

    def get_all_center_codes(self):
        codes = []
        for res_name, centers in self.centers:
            codes.extend(self.get_codes(res_name, len(centers)))
        return codes

    def get_comparable_center_codes(self):
        if self.classes is None:
            return [self.get_all_center_codes()]
        else:
            return self.get_codes_by_class().values()

    def make_code_pair(self, keys):
        return make_vector_type_key(keys)

    def get_class_code_pairs(self):
        kwargs = self._key_args.copy()
        kwargs['get_code'] = self._get_code
        if self.classes is None:
            return self.get_all_code_pairs()
        return make_allowed_pair_sets(self.classes, **kwargs)

    def get_all_code_pairs(self):
        kwargs = self._key_args.copy()
        kwargs['get_code'] = self._get_code
        classes = {'all': self.get_all_center_codes()}
        return make_allowed_pair_sets(classes, **kwargs)

    def get_codes_by_class(self):
        grouped = {}
        for class_name, keys in self.classes.items():
            grouped[class_name] = self.get_class_codes(class_name)
        return grouped

    def get_code_for(self, residue):
        key = self.normalize_key(self.get_key(residue))
        num_points = len(self.centers[key])
        codes = [self.get_code(key, idx) for idx in range(num_points)]
        return codes

    def get_class_codes(self, class_name):
        if self.classes is not None:
            return [self.get_code(residue_name, idx) for residue_name, idx in self.classes[class_name]]
        elif class_name is None:
            return self.get_all_center_codes()
        else:
            raise ValueError("Cannot get class codes when no classes defined")

    def __call__(self, arg, **kwargs):
        return self.get_center(arg, **kwargs)



