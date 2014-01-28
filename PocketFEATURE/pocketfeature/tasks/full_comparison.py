#!/usr/bin/env python
from __future__ import print_function

import logging
import os

from feature.io import (
    featurefile,
    pointfile,
)
from feature.backends.wrappers import featurize_points

from pocketfeature.io import (
    backgrounds,
    matrixvaluesfile,
    pdbfile,
    residuefile,
)
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.tasks.pocket import (
    create_pocket_around_ligand,
    find_ligand_in_structure,
    pick_best_ligand,
)
from pocketfeature.tasks.compare import score_featurefiles
from pocketfeature.tasks.align import (
    align_scores_greedy,
    align_scores_munkres,
)
from pocketfeature.tasks.visualize import create_visualizations
from pocketfeature.utils.pdb import guess_pdbid_from_stream

from pocketfeature.tasks.core import Task


class ComparePockets(Task):
    LIGAND_RESIDUE_DISTANCE = 6.0
    DEFAULT_CUTOFF = -0.15

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(logging.DEBUG)

        log.info("Loading background")
        background = backgrounds.load(stats_file=params.background,
                                      norms_file=params.normalization)

        log.info("Loading PDBs")

        log.debug("Extracting PDBIDs")
        pdbidA, pdbA = guess_pdbid_from_stream(params.pdbA)
        pdbidB, pdbB = guess_pdbid_from_stream(params.pdbB)

        log.debug("Loading structure A")
        structureA = pdbfile.load(pdbA, pdbid=pdbidA)
        log.debug("Loading structure B")
        structureB = pdbfile.load(pdbB, pdbid=pdbidB)

        log.info("Finding ligands")
        if params.ligandA is None:
            log.debug("Guessing ligand A")
            ligandA = pick_best_ligand(structureA)
        else:
            log.debug("Searching for ligand A")
            ligandA = find_ligand_in_structure(structureA, params.ligandA)

        if params.ligandB is None:
            log.debug("Guessing ligand B")
            ligandB = pick_best_ligand(structureB)
        else:
            log.debug("Searching for ligand B")
            ligandB = find_ligand_in_structure(structureB, params.ligandB)
        
        if None in (ligandA, ligandB):
            log.error("Could not find both ligands")
            return -1
        
        log.info("Creating pockets")
        log.debug("Creating pocket A")
        pocketA = create_pocket_around_ligand(structureA, ligandA, cutoff=params.distance)
        if params.ptfA is not None:
            log.debug("Writing pocket A")
            pointfile.dump(pocketA.points, params.pftA)
            params.ptfA.close()
        log.debug("Creating pocket B")
        pocketB = create_pocket_around_ligand(structureB, ligandB, cutoff=params.distance)
        if params.ptfB is not None:
            log.debug("Writing pocket B")
            pointfile.dump(pocketB.points, params.pftB)
            params.ptfB.close()
    
        log.info("FEATURIZING Pockets")
        log.debug("FEATURIZING Pocket A")
        featurefileA = featurize_points(pocketA.points)
        if params.ffA is not None:
            log.debug("Wring FEATURE file A")
            featurefile.dump(featurefileA, params.ffA)
            params.ffA.close()
        log.debug("FEATURIZING Pocket B")
        featurefileB = featurize_points(pocketB.points)
        if params.ffB is not None:
            log.debug("Wring FEATURE file B")
            featurefile.dump(featurefileB, params.ffB)
            params.ffB.close()
    
        log.info("Comparing Vectors")
        scores_iter = score_featurefiles(background, featurefileA, featurefileB)
        scores = MatrixValues(scores_iter, value_dims=2)
        if params.scores is not None:
            log.debug("Writing scores")
            matrixvaluesfile.dump(scores, params.scores)
            params.scores.close()
        normalized = scores.slice_values(1)  # Normalized in second position

        log.info("Aligning Pockets")
        alignment = align_scores_greedy(normalized, cutoff=params.cutoff)
        total_score = sum(alignment.values())
        alignment_with_raw_scores = scores.subset_from_keys(alignment.keys())

        matrixvaluesfile.dump(alignment, params.output)
        log.info("Alignment Score: {0}".format(total_score))

        log.info("Creating PyMol scripts")
        scriptA, scriptB = create_visualizations(pocketA.points, pocketB.points, alignment,
                                                 pdbA=params.pdbA.name,
                                                 pdbB=params.pdbB.name)

        if params.pymolA is not None:
            log.debug("Writing first PyMol script") 
            print(scriptA, file=params.pymolA)
        if params.pymolB is not None:
            log.debug("Writing first PyMol script") 
            print(scriptB, file=params.pymolB)

        return 0

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import (
            decompress,
            FileType,
        )
        parser = ArgumentParser("Identify and extract pockets around ligands in a PDB file")
        parser.add_argument('pdbA', metavar='PDBA', 
                                    type=FileType.compressed('r'),
                                    help='Path to first PDB file')
        parser.add_argument('pdbB', metavar='PDBB', 
                                    type=FileType.compressed('r'),
                                    help='Path to second PDB file')
        parser.add_argument('--ligandA', metavar='LIGA',
                                         type=str,
                                         nargs='?',
                                         default=None,
                                         help='Ligand ID to build first pocket around [default: <largest>]')
        parser.add_argument('--ligandB', metavar='LIGB',
                                         type=str,
                                         nargs='?',
                                         default=None,
                                         help='Ligand ID to build second pocket around [default: <largest>]')
        parser.add_argument('-b', '--background', metavar='FEATURESTATS',
                                      type=FileType.compressed('r'),
                                      default='background.ff',
                                      help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalization', metavar='COEFFICIENTS',
                                      type=FileType.compressed('r'),
                                      default='background.coeffs',
                                      help='Map of normalization coefficients for residue type pairs [default: %(default)s')
        parser.add_argument('-d', '--distance', metavar='CUTOFF',
                                              type=float,
                                              default=cls.LIGAND_RESIDUE_DISTANCE,
                                              help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-c', '--cutoff', metavar='CUTOFF',
                                              type=float,
                                              default=cls.DEFAULT_CUTOFF,
                                              help='Minium score (cutoff) to align [default: %(default)s')
        parser.add_argument('-o', '--output', metavar='ALIGNMENT',
                                              type=FileType.compressed('w'),
                                              default=stdout,
                                              help='Path to alignment file [default: STDOUT]')
        parser.add_argument('--ptfA', metavar='PTFA',
                                      type=FileType.compressed('w'),
                                      default=None,
                                      nargs='?',
                                      help='Path to first point file [default: None]')
        parser.add_argument('--ptfB', metavar='PTFB',
                                      type=FileType.compressed('w'),
                                      default=None,
                                      nargs='?',
                                      help='Path to second point file [default: None]')
        parser.add_argument('--ffA', metavar='FFA',
                                     type=FileType.compressed('w'),
                                     default=None,
                                     nargs='?',
                                     help='Path to first FEATURE file [default: None]')
        parser.add_argument('--ffB', metavar='FFB',
                                     type=FileType.compressed('w'),
                                     default=None,
                                     nargs='?',
                                     help='Path to second FEATURE file [default: None]')
        parser.add_argument('--scores', metavar='SCORES',
                                        type=FileType.compressed('w'),
                                        default=None,
                                        nargs='?',
                                        help='Path to scores file [default: None]')
        parser.add_argument('--pymolA', metavar='PYMOLA',
                                     type=FileType('w'),
                                     default=None,
                                     nargs='?',
                                     help='Path to first PyMol script [default: None]')
        parser.add_argument('--pymolB', metavar='PYMOLB',
                                     type=FileType('w'),
                                     default=None,
                                     nargs='?',
                                     help='Path to second PyMol script [default: None]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     default=stderr,
                                     help='Path to log errors [default: %(default)s]')
        return parser



if __name__ == '__main__':
    import sys
    sys.exit(ComparePockets.run_as_script())
