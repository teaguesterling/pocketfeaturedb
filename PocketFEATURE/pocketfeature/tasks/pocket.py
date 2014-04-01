#!/usr/bin/env python
from __future__ import print_function

from numpy.linalg import norm
from Bio.PDB.NeighborSearch import NeighborSearch

from feature.io import pointfile

from pocketfeature.io import (
    pdbfile,
    residuefile,
)
from pocketfeature.pocket import Pocket
from pocketfeature.residues import DEFAULT_CENTERS
from pocketfeature.utils.pdb import (
    find_residues_by_id,
    guess_pdbid_from_stream,
    is_het_residue,
    list_ligands,
)

from pocketfeature.tasks.core import Task


def find_neighboring_residues(structure, queries, cutoff=6.0, 
                                                  ordered=True,
                                                  excluded=is_het_residue,
                                                  residue_centers=None):

    all_atoms = (a for a in structure.get_atoms())
    non_het = (a for a in all_atoms if not excluded(a.get_parent()))
    neighbors = NeighborSearch(list(non_het))
    residues = set()
    for query in queries:  # Search through query points
        found = neighbors.search(query, cutoff, 'R')  # Search of Residues
        found = (res for res in found if not excluded(res))  # Possibly redundant
        if residue_centers is None:  # If adding any points
            residues.add(found)
        else:  # Check if any active sites are within cutuff
            for residue in found:
                points = [point for code, point in residue_centers(residue)]
                meets_cutoff = (norm(query - pt) <= cutoff for pt in points)
                if any(meets_cutoff):
                    residues.add(residue)
    if ordered:
        residues = sorted(residues, key=lambda r: r.get_id()[1])
    
    return list(residues)


def create_pocket_around_ligand(structure, ligand, cutoff=6.0, 
                                                   name=None,
                                                   residue_centers=DEFAULT_CENTERS, 
                                                   **options):
    points = [atom.get_coord() for atom in ligand]
    residues = find_neighboring_residues(structure, points, cutoff=cutoff, 
                                                            ordered=True, 
                                                            excluded=is_het_residue, 
                                                            residue_centers=residue_centers)
    pocket = Pocket(residues, pdbid=structure.get_id(),
                              defined_by=ligand,
                              name=name,
                              residue_centers=residue_centers)
    return pocket


def find_ligand_in_structure(structure, ligand_name, index=0):
    lig_id = residuefile.read_residue_id(ligand_name)
    found = find_residues_by_id(structure, [lig_id])
    if len(found) > index:
        return found[index]
    else:
        return None


def pick_best_ligand(structure):
    ligands = list_ligands(structure)
    try:
        return sorted(ligands, key=len, reverse=True)[0]
    except IndexError:
        return None


class PocketFinder(Task):
    LIGAND_RESIDUE_DISTANCE = 6.0

    def run(self):
        params = self.params
        if params.pdbid is None:
            params.pdbid, params.pdb = guess_pdbid_from_stream(params.pdb)

        structure = pdbfile.load(params.pdb, pdbid=params.pdbid)
        ligand = None
        if params.list_only:
            ligands = list_ligands(structure)
            residuefile.dump(ligands, params.output)
            return 0
        
        if ligand is None:
            ligand = pick_best_ligand(structure)
        else:
            ligand = find_ligand_in_structure(structure, params.ligand)
        
        if ligand is None:
            print("Error: Could not find ligand in structure", file=params.log)
            return -1

        pocket = create_pocket_around_ligand(structure, ligand, cutoff=params.distance)

        if len(pocket.residues) == 0:
            print("Error: No residues found within {0} angstroms of {1}".format(params.distance, ligand),
                    file=params.log)
            return -1

        if params.print_residues:
            residuefile.dump(pocket.residues, params.output)
        elif params.print_pointfile:
            pointfile.dump(pocket.points, params.output)

        return 0

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import (
            decompress,
            FileType,
        )
        parser = ArgumentParser("Identify and extract pockets around ligands in a PDB file")
        parser.add_argument('pdb', metavar='PDB', 
                                   type=FileType.compressed('r'),
                                   nargs='?',
                                   default=decompress(stdin),
                                   help='Path to PDB file [default: STDIN]')
        parser.add_argument('ligand', metavar='LIG',
                                      type=str,
                                      nargs='?',
                                      default=None,
                                      help='Ligand ID to build pocket around [default: <largest>]')
        parser.add_argument('-i', '--pdbid', metavar='PDBID',
                                      type=str,
                                      default=None,
                                      help='PDB ID to use for input structure [default: BEST GUESS]')
        parser.add_argument('-o', '--output', metavar='PTF',
                                              type=FileType.compressed('w'),
                                              default=stdout,
                                              help='Path to output file [default: STDOUT]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     default=stderr,
                                     help='Path to log errors [default: STDERR]')
        parser.add_argument('-d', '--distance', metavar='CUTOFF',
                                              type=float,
                                              default=cls.LIGAND_RESIDUE_DISTANCE,
                                              help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-P', '--print-pointfile', action='store_true',
                                                       default=True,
                                                       help='Print point file (default behavior)')
        parser.add_argument('-R', '--print-residues', action='store_true',
                                                      default=False,
                                                      help='Print residue ID list instead of point file')
        parser.add_argument('-L', '--list-only', action='store_true',
                                                 default=False,
                                                 help='List residues instead of creating pocket')
        return parser

if __name__ == '__main__':
    import sys
    sys.exit(PocketFinder.run_as_script())
