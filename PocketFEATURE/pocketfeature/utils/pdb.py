#!/usr/bin/env python

import itertools
import operator
import os

from numpy import average

from Bio.PDB.Polypeptide import (
    one_to_three,
    three_to_one,
)

residue_code_one_to_three = one_to_three
residue_code_three_to_one = three_to_one

MIN_ATOMS_IN_LIGAND = 2
IGNORED_LIGANDS = set((
    'W',
    'H_SO4',
    'H_PO4',
    # Add more
))


# From: https://stackoverflow.com/a/6658949
class IteratorIO(object):
    """
    File-like streaming iterator.
    """
    def __init__(self, generator):
        self.generator = generator
        self.iterator = iter(generator)
        self.leftover = ''

    def __len__(self):
        return self.generator.__len__()

    def __iter__(self):
        return self.iterator

    def next(self):
        return self.iterator.next()

    def read(self, size):
        data = self.leftover
        count = len(self.leftover)
        try:
            while count < size:
                chunk = self.next()
                data += chunk
                count += len(chunk)
        except StopIteration, e:
            self.leftover = ''
            return data

        if count > size:
            self.leftover = data[size:]

        return data[:size]

    def readlines(self):
        return list(self.iterator)


def extract_header_from_stream(stream):
    # Split the stream, assuming metadata is at the beginning
    # (Keep only the group data, i)
    grouping = itertools.groupby(stream, key=lambda line: line.startswith('HEADER    '))
    grouping = itertools.imap(operator.itemgetter(1), grouping)

    # We need to strictly consume all the group members here or
    # they will be lost to the groupby iterator process
    header_lines = list(next(grouping))
    body = IteratorIO(next(grouping))

    pdbid = title = date= None
    if len(header_lines) > 0:
        header = header_lines[0].strip()
        pdbid = header[-4:]
        try:
            title = header[10:-17].strip()
            date = header[-18:-7].strip()
        except IndexError:
            pass
    return (title, date, pdbid), body


def guess_pdbid_from_stream(stream):
    if hasattr(stream, 'name') and not stream.name.startswith('<'):
        filename = os.path.basename(stream.name)
        base = filename.split('.')[0]
        pdbid = base
    else:
        try:
            header, stream = extract_header_from_stream(stream)
            pdbid = header[2]
        except IndexError:
            pdbid = None
    if pdbid is None:
        pdbid = 'UNKN'
    return pdbid, stream


def is_het_residue(residue):
    het, seq, ins = residue.get_id()
    return len(het.strip()) > 0


def is_water(residue):
    return residue.get_id()[0] == 'W'


def is_ligand_residue(residue):
    het, seq, ins = residue.get_id()
    return het.startswith("H_") \
       and len(residue) > MIN_ATOMS_IN_LIGAND \
       and het not in IGNORED_LIGANDS


def is_organic_ligand(residue):
    het, seq, ins = residue.get_id()
    atoms = residue.get_list()
    return is_ligand_residue(residue) \
       and any(atom_name(atom) == 'C' for atom in atoms)


def is_metal_residue(residue):
    return is_het_residue(residue) \
        and not is_water(residue) \
        and not is_ligand_residue(residue)


def get_root_element(element):
    node, parent = element, element.get_parent()
    i, max_iter = 0, 10
    while parent is not None and node != parent and i < max_iter:
        i, node, parent = i+1, parent, node.get_parent()
    return node


def get_pdb_id(element):
    return get_root_element(element).get_id()


def atom_name(atom):
    return atom.get_name()


def residue_name(residue):
    return residue.get_resname().strip()


def residue_id(residue, full=True):
    full_id = residue.get_full_id()
    res_id = full_id[-1]
    res_idx = res_id[1]
    res_name = residue_name(residue)
    if full:
        return full_id[:-1] + (res_idx, res_name)
    else:
        return res_idx


def detach_residues(residues):
    residues = [residue.copy() for residue in residues]
    for residue in residues:
        residue.detach_parent()
    return residues


def average_coords(atoms):
    return average([a.get_coord() for a in atoms], axis=0)


def find_residues_by_name(structure, name):
    found = [r for r in structure.get_residues() if residue_name(r) == name]
    return found


def find_residues_by_id(structure, query, full=True):
    args = {'full': full}
    query = set(query)
    residues = structure.get_residues()
    found = [res for res in residues if residue_id(res, **args) in query]
    return found


def list_ligands(structure, is_ligand=is_ligand_residue):
    """ Get a 'ligands' from a structure """
    residues = structure.get_residues()
    ligands = [lig for lig in residues if is_ligand(lig)]
    return ligands


def list_ligand_names(structure, is_ligand=is_ligand_residue):
    ligands = list_ligands(structure)
    residue_names = [residue_name(lig) for lig in ligands]
    return residue_names


def flip_dict(d):
    return dict((reversed(pair) for pair in d.items()))
