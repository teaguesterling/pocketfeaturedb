#!/usr/bin/env python
from __future__ import print_function

import logging

from feature.backends.wrappers import featurize_points

from pocketfeature.io import backgrounds
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.io import pdbfile
from pocketfeature.io import residuefile
from pocketfeature.tasks.find_pocket import create_pocket_around_ligand
from pocketfeature.tasks.compare_features import score_featurefiles
from pocketfeature.tasks.align_scores import align_scores_greedy


def compare_pockets(background, structureA, ligA_id, 
                                structureB, ligB_id, 
                                dist_cutoff=6.0,
                                score_cutoff=-0.15,
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
    alignment = align_scores_greedy(normalized, cutoff=score_cutoff)
    total_score = sum(alignment.values())
    alignment_with_raw_scores = scores.subset_from_keys(alignment.keys())
    return alignment_with_raw_scores, total_score


def main(args, stdout, stderr):
    """
    This is just a simple usage example. Fancy argument parsing needs to be enabled
    """
    if len(args) < 4:
        print("Usage: ", file=stderr)

        print(" compare_features.py PDB1 LIG1 PDB2 LIG2 [BG_VECS [BG_NORMS]]", file=stderr)
        print("     BG_VECS - FEATURE file containing background statistics [default: background.ff]", file=stderr)
        print("     BG_NORMS - Sparse matrix containing normalization coefficents [default: background.coeffs]", file=stderr)
        return -1

    logging.basicConfig(stream=stderr)
    log = logging.getLogger('pocketfeature')
    log.setLevel(logging.DEBUG)
    
    pdb_path1 = args[0]
    lig_id1 = args[1]
    pdb_path2 = args[2]
    lig_id2 = args[3]
    bg_vecs = args[4] if len(args) > 2 else 'background.ff'
    bg_norms = args[5] if len(args) > 3 else 'background.coeffs'

    log.debug("Loading background data")
    with open(bg_vecs) as stats, open(bg_norms) as coeffs:
        background = backgrounds.load(stats_io=stats, norms_io=coeffs)

    log.debug("Loading PDB Structures")
    structure1 = structure = pdbfile.open(pdb_path1)
    structure2 = structure = pdbfile.open(pdb_path2)
    
    alignment, score = compare_pockets(background, structureA=structure1, ligA_id=lig_id1,
                                                   structureB=structure2, ligB_id=lig_id2,
                                                   log=log)

    matrixvaluesfile.dump(alignment, stdout)
    log.info("Alignment Score: {0}".format(score))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))