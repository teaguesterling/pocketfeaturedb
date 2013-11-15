#!/usr/bin/env python
from __future__ import print_function

from numpy.linalg import norm
from Bio.PDB.NeighborSearch import NeighborSearch

from feature.io import pointfile

from pocketfeature.io import pdbfile
from pocketfeature.io import residuefile
from pocketfeature.utils.pdb import (
    find_residues_by_id,
    is_het_residue,
    list_ligands,
)
from pocketfeature.pocket import Pocket
from pocketfeature.residues import CENTER_FUNCTIONS


def find_neighboring_residues(structure, queries, cutoff=6.0, 
                                                  ordered=True,
                                                  excluded=is_het_residue,
                                                  residue_points=None):

    all_atoms = (a for a in structure.get_atoms())
    non_het = (a for a in all_atoms if not excluded(a.get_parent()))
    neighbors = NeighborSearch(list(non_het))
    residues = set()
    for query in queries:  # Search through query points
        found = neighbors.search(query, cutoff, 'R')  # Search of Residues
        found = (res for res in found if not excluded(res))  # Possibly redundant
        if residue_points is None:
            residues.add(found)
        else:  # Check if any active sites are within cutuff
            for residue in found:
                points = residue_points(residue)
                points = points if points is not None else []
                points = [point for point in points if point is not None]
                meets_cutoff = (norm(query - pt) <= cutoff for pt in points)
                if any(meets_cutoff):
                    residues.add(residue)
    if ordered:
        residues = sorted(residues, key=lambda r: r.get_id()[1])
    
    return list(residues)


def create_pocket_around_ligand(structure, ligand, cutoff=6.0, 
                                                   name=None,
                                                   residue_points=CENTER_FUNCTIONS, 
                                                   **options):
    points = [atom.get_coord() for atom in ligand]
    residues = find_neighboring_residues(structure, points, cutoff=cutoff, 
                                                            ordered=True, 
                                                            excluded=is_het_residue, 
                                                            residue_points=residue_points)
    pocket = Pocket(residues, pdbid=structure.get_id(),
                              defined_by=ligand,
                              name=name,
                              residue_points=residue_points)
    return pocket


def find_ligand_in_structure(structure, ligand_name, index=0):
    lig_id = residuefile.read_residue_id(ligand_name)
    found = find_residues_by_id(structure, [lig_id])
    if len(found) > index:
        return found[index]
    else:
        return None


def main(args, stdout, stderr):
    """
    This is just a simple usage example. Fancy argument parsing needs to be enabled
    """
    if len(args) == 0:
        print("Usage: ", file=stderr)
        print(" find_pocket.py PDB                  -- List ligand ids found in PDB", file=stderr)
        print(" find_pocket.py PDB LIG_ID [options] -- Print pocket found around ligand", file=stderr)
        print("     options:", file=stderr)
        print("      -c CUTOFF  - Change the neighboring residue distance cutoff [default: 6.0]", file=stderr)
        print("      -r         - Print neighboring residue IDs instead of points", file=stderr)
        print("      -p         - Print neighboring residue points [default]", file=stderr)
        return -1
    
    pdb_path = args[0]
    lig_name = args[1] if len(args) > 1 else None
    cutoff = float(args[args.index('-c') + 1]) if '-c' in args else 6.0
    print_residues = '-r' in args
    structure = pdbfile.open_file(pdb_path)
    if lig_name is None:
        ligands = list_ligands(structure)
        residuefile.dump(ligands, stdout)
        return 0
    ligand = find_ligand_in_structure(structure, lig_name)
    if ligand is None:
        print("Could not find {0} in {1}".format(lig_name, structure.get_id), file=stderr)
        return -1
    pocket = create_pocket_around_ligand(structure, ligand, cutoff=cutoff)
    if print_residues:
        residuefile.dump(pocket.residues, stdout)
    else:
        pointfile.dump(pocket.points, stdout)


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
