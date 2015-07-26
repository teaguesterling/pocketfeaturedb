#!/usr/bin/env python
from __future__ import print_function

from six import string_types
from numpy.linalg import norm
from Bio.PDB.NeighborSearch import NeighborSearch

from pocketfeature.io import (
    residuefile,
)
from pocketfeature.datastructs.pocket import Pocket
from pocketfeature import defaults
from pocketfeature.utils.pdb import (
    residue_name,
    find_residues_by_name,
    find_residues_by_id,
    is_het_residue,
    list_ligands,
)


def focus_structure(structure, model=0, chain=None):
    focus = structure
    models = list(structure.get_list())
    chains = list(structure.get_chains())
    if model is not None:
        found = [m for m in models if m.get_id() == model or m.get_id() == int(model)]
        if len(found) == 0:
            if model in (0, '0') and len(models) == 1:
                model = models[0]
            else:
                raise ValueError("Model {0!r} not found in {1}".format(model, structure))
        elif len(found) > 1:
            raise ValueError("Model {0} ambigous in {1}".format(model, structure))
        else:
            focus = found[0]

        if chain is not None:
            chains = list(focus.get_list())

    if chain is not None:
        if isinstance(chain, int):
            found = [chains[chain]]
        else:
            found = [c for c in chains if c.get_id() == chain]
        if len(found) == 0:
            raise ValueError("Chain {0} not found in {1}".format(chain, structure))
        elif len(found) > 1:
            raise ValueError("Chain {0} ambigous in {1}".format(chain, structure))
        else:
            focus = found[0]
    return focus


def find_neighboring_residues_and_points(structure, queries, cutoff=6.0,
                                                             ordered=True,
                                                             excluded=is_het_residue,
                                                             residue_centers=None,
                                                             skip_partial_residues=True):

    all_atoms = list(structure.get_atoms())
    neighbors = NeighborSearch(all_atoms)
    residues = []
    picked = set()
    for query in queries:  # Search through query points
        found = neighbors.search(query, cutoff, 'R')  # Search of Residues
        found = [res for res in found if not excluded(res) and res not in picked]
        if residue_centers is None:  # If adding any points
            picked.add(found)
            residues.extend(found)
        else:  # Check if any active sites are within cutuff
            for residue in found:
                centers = residue_centers(residue, skip_partial_residues=skip_partial_residues,
                                                   ignore_unknown_residues=True)

                meets_cutoff = [any((norm(q - pt) <= cutoff) for q in queries) for code, pt in centers]
                if any(meets_cutoff):
                    close_centers = [center for center, close in zip(centers, meets_cutoff) if close]
                    residue_points = (residue, close_centers)
                    residues.append(residue_points)
                    picked.add(residue)
    if ordered:
        residues = sorted(residues, key=lambda pair: pair[0].get_id()[1])

    return residues


def create_pocket_around_ligand(structure, ligand, cutoff=6.0,
                                                   name=None,
                                                   residue_centers=defaults.DEFAULT_RESIDUE_CENTERS,
                                                   exact_points=True,
                                                   expand_disordered=True,
                                                   **options):
    if isinstance(residue_centers, string_types):
        residue_centers = defaults.NAMED_RESIDUE_CENTERS[residue_centers]
    atoms = list(ligand)
    if expand_disordered:
        atoms = [atom_pos for atom in atoms
                          for atom_pos in (atom.disordered_get_list()
                           if atom.is_disordered() else [atom])]
    points = [atom.get_coord() for atom in atoms]

    residue_points = find_neighboring_residues_and_points(structure, points, cutoff=cutoff,
                                                                             ordered=True,
                                                                             excluded=is_het_residue,
                                                                             residue_centers=residue_centers)
    residue_points = list(residue_points)
    residues = [residue for residue, points in residue_points]

    if exact_points:
        point_map = dict(residue_points)
        selected_centers = lambda res, *args, **kwargs: point_map.get(res, [])
    else:
        selected_centers = residue_centers

    pdbid = structure.get_full_id()[0]
    pocket = Pocket(residues, pdbid=pdbid,
                              defined_by=ligand,
                              name=name,
                              residue_centers=selected_centers)
    return pocket


def find_ligand_in_structure(structure, ligand_name, index=0):
    lig_id = residuefile.read_residue_id(ligand_name)
    if isinstance(lig_id, string_types):
        found = find_residues_by_name(structure, lig_id)
    elif isinstance(lig_id, int):
        found = find_residues_by_id(structure, [lig_id], full=False)
    else:
        found = find_residues_by_id(structure, [lig_id])

    if len(found) > index:
        return found[index]
    else:
        return None


def find_one_of_ligand_in_structure(structure, ligand_names, index=0):
    ligands = list_ligands(structure)
    for ligand in ligands:
        if residue_name(ligand) in ligand_names:
            return ligand
    return None


def pick_best_ligand(structure):
    ligands = list_ligands(structure)
    try:
        return sorted(ligands, key=len, reverse=True)[0]
    except IndexError:
        return None
