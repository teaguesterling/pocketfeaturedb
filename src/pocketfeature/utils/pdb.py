#!/usr/bin/env python

from numpy import average

from Bio.PDB.Polypeptide import (
    one_to_three,
    three_to_one,
)

residue_code_one_to_three = one_to_three
residue_code_three_to_one = three_to_one


IGNORED_LIGANDS = set((
    'W',
    'SO4',
    # Add more
))


def is_het_residue(residue):
    het, seq, ins = residue.get_id()
    return len(het.strip()) > 0


def is_water(residue):
    return residue.get_id()[0] == 'W'


def is_ligand_residue(residue):
    het, seq, ins = residue.get_id()
    return het.startswith("H_") \
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
    found = [r for r in structure.get_resiudes() if residue_name(r) == name]
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
