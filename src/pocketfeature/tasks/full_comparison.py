#!/usr/bin/env python
from __future__ import print_function

import logging
import os

from feature.backends.wrappers import featurize_points

from pocketfeature.io import backgrounds
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io import pdbfile
from pocketfeature.io import residuefile
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.tasks.pocket import create_pocket_around_ligand
from pocketfeature.tasks.compare import score_featurefiles
from pocketfeature.tasks.align import (
    align_scores_greedy,
    align_scores_munkres,
)


def compare_pockets(background, structureA, ligA_id, 
                                structureB, ligB_id, 
                                dist_cutoff=6.0,
                                score_cutoff=-0.15,
                                align_method=align_scores_greedy,
                                log=logging):
    log.info("Finding Ligands")
    ligA = residuefile.loads_with_structure(ligA_id, structureA)[0]
    ligB = residuefile.loads_with_structure(ligB_id, structureB)[0]

    log.info("Creating Pockets")
    pocketA = create_pocket_around_ligand(structureA, ligA, cutoff=dist_cutoff)
    pocketB = create_pocket_around_ligand(structureB, ligB, cutoff=dist_cutoff)

    log.info("FEATURIZING Pockets")
    log.debug("FEATURIZING Pocket 1")
    featurefileA = featurize_points(pocketA.points)
    log.debug("FEATURIZING Pocket 2")
    featurefileB = featurize_points(pocketB.points)

    log.info("Comparing Vectors")
    scores_iter = score_featurefiles(background, featurefileA, featurefileB)
    scores = MatrixValues(scores_iter, value_dims=2)
    normalized = scores.slice_values(1)  # Normalized in second position

    log.info("Aligning Pockets")
    alignment = align_method(normalized, cutoff=score_cutoff)
    total_score = sum(alignment.values())
    alignment_with_raw_scores = scores.subset_from_keys(alignment.keys())
    return alignment_with_raw_scores, total_score


def main(args, stdout, stderr):
    """
    This is just a simple usage example. Fancy argument parsing needs to be enabled
    """
    print(len(args))
    if len(args) in (0, 1, 3):
        print("Usage: ", file=stderr)

        print(" compare_features.py PDB1 LIG1 PDB2 LIG2 [BG_VECS [BG_NORMS]] [-m]", file=stderr)
        print("      -m      - Munkres Align (Proof of concept)", file=stderr)
        print("     BG_VECS  - FEATURE file containing background statistics [default: background.ff]", file=stderr)
        print("     BG_NORMS - Sparse matrix containing normalization coefficents [default: background.coeffs]", file=stderr)
        return -1

    logging.basicConfig(stream=stderr)
    log = logging.getLogger('pocketfeature')
    log.setLevel(logging.DEBUG)
    
    if len(args) == 2:
        lig_id1 = args[0]
        lig_id2 = args[1]
        pdb_id1 = lig_id1.split('/')[0]
        pdb_id2 = lig_id2.split('/')[0]
        pdb_path1 = os.path.join(os.environ.get('PDB_DIR', '.'), "{0}.pdb.gz".format(pdb_id1))
        pdb_path2 = os.path.join(os.environ.get('PDB_DIR', '.'), "{0}.pdb.gz".format(pdb_id2))
        bg_pos = 2
    else:
        pdb_path1 = args[0]
        lig_id1 = args[1]
        pdb_path2 = args[2]
        lig_id2 = args[3]
        bg_pos = 4
    bg_vecs = args[bg_pos] if len(args) > 4 else 'background.ff'
    bg_norms = args[bg_pos+1] if len(args) > 5 else 'background.coeffs'
    munkres = '-m' in args

    if munkres:
        align_method = align_scores_munkres
    else:
        align_method = align_scores_greedy

    log.debug("Loading background data")
    with open(bg_vecs) as stats, open(bg_norms) as coeffs:
        background = backgrounds.load(stats_io=stats, norms_io=coeffs)

    log.debug("Loading PDB Structures")
    structure1 = structure = pdbfile.open_file(pdb_path1)
    structure2 = structure = pdbfile.open_file(pdb_path2)
    
    alignment, score = compare_pockets(background, structureA=structure1, ligA_id=lig_id1,
                                                   structureB=structure2, ligB_id=lig_id2,
                                                   align_method=align_method,
                                                   log=log)

    matrixvaluesfile.dump(alignment, stdout)
    log.info("Alignment Score: {0}".format(score))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
