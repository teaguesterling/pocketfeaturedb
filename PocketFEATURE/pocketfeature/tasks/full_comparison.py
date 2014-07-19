#!/usr/bin/env python
from __future__ import print_function

import logging
import os

from feature.io import (
    pointfile,
)

from pocketfeature.io import (
    backgrounds,
    featurefile,
    matrixvaluesfile,
    pdbfile,
    residuefile,
)
from pocketfeature.io.backgrounds import NORMALIZED_SCORE
from pocketfeature.tasks.pocket import (
    create_pocket_around_ligand,
    find_one_of_ligand_in_structure,
    pick_best_ligand,
)
from pocketfeature.tasks.align import (
    align_scores_greedy,
    align_scores_munkres,
)
from pocketfeature.tasks.featurize import featurize_points
from pocketfeature.tasks.visualize import create_alignment_visualizations
from pocketfeature.utils.pdb import guess_pdbid_from_stream

from pocketfeature.utils.args import LOG_LEVELS
from pocketfeature.tasks.core import Task


def load_points(pdb_file,
                points_file,
                pdbid=None,
                ligands=None,
                distance_cutoff=6.0,
                point_cache=None,
                link_cached=False,
                log=logging,
                log_label="Pocket"):
    
    if point_cache is not None and os.path.exists(point_cache):
        log.info("Using cached pointfile for {label}: {cache}".format(label=log_label,
                                                                      cache=point_cache))
        ligand = None
        with gzip.open(point_cache) as f:
            points = pointfile.load(f)
    else:
        log.debug("Loading structure {label}".format(label=log_label))
        structure = pdbfile.load(pdb_file, pdbid=pdbid)

        log.info("Finding ligands in structure {label}".format(label=log_label))
        if ligands is None:
            log.debug("Guessing ligand {label}".format(label=log_label))
            ligand = pick_best_ligand(structure)
        else:
            log.debug("Searching for ligand {label} ({ligands})".format(label=log_label,
                                                                        ligands=" ".join(ligands)))
            ligand = find_one_of_ligand_in_structure(structure, ligands)

        log.debug("Creating pocket {label}".format(label=log_label))
        pocket = create_pocket_around_ligand(structure, ligand, cutoff=distance_cutoff)
        points = pocket.points
        
        if point_cache is not None:
            log.debug("Caching pocket {label}".format(label=log_label))
            with gzip.open(point_cache, 'w') as f:
                pointfile.dump(points, f)
    
    pdb_file.close()
    if points_file is not None:
        if link_cached:
            log.debug("Linking to cached pocket {label}".format(label=log_label))
            points_file.close()
            os.symlink(point_cache, points_file.name)
        else:
            log.debug("Writing pocket {label}".format(label=log_label))
            pointfile.dump(points, points_file)
            points_file.close()

    return points, ligand



def generate_featurefile(points,
                         feature_file,
                         pdbid=None,
                         ligand=None,
                         feature_cache=None,
                         link_cached=False,
                         log=logging,
                         log_label="Pocket"):
    if feature_cache is not None and os.path.exists(feature_cache):
        log.info("Using cached featurefile for {label}: {cache}".format(label=log_label,
                                                                        cache=feature_cache))
        with gzip.open(feature_cache) as f:
            features = featurefile.load(f)
    else:
             
        log.debug("FEATURIZING Pocket {label}".format(label=log_label))
        features = featurize_points(points, 
                                    featurefile_args={
                                        'rename_from_comment': 'DESCRIPTION'})
        if feature_cache is not None:
            log.debug("Caching features {label}".format(label=log_label))
            with gzip.open(feature_cache, 'w') as f:
                featurefile.dump(features, f)

    if feature_file is not None:
        if link_cached:
            log.debug("Linking to cached features {label}".format(label=log_label))
            feature_file.close()
            os.symlink(feature_cache, feature_file.name)
        else:
            log.debug("Writing features {label}".format(label=log_label))
            featurefile.dump(features, feature_file)
            feature_file.close()

    return features


class ComparePockets(Task):
    LIGAND_RESIDUE_DISTANCE = 6.0
    DEFAULT_CUTOFF = -0.15
    BACKGROUND_FF_DEFAULT = 'background.ff'
    BACKGROUND_COEFF_DEFAULT = 'background.coeffs'

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(LOG_LEVELS.get(params.log_level, 'debug'))

        log.info("Loading background")
        log.debug("Allowed residue pairs: {0}".format(params.allowed_pairs)) 
        background = backgrounds.load(stats_file=params.background,
                                      norms_file=params.normalization,
                                      allowed_pairs=params.allowed_pairs)

        log.info("Loading PDBs")
        log.debug("Extracting PDBIDs")
        pdbidA, pdbA = guess_pdbid_from_stream(params.pdbA)
        pdbidB, pdbB = guess_pdbid_from_stream(params.pdbB)

        ligandA = params.ligandA
        if ligandA is not None:
            ligandA = params.ligandA.split(',')

        ligandB = params.ligandB
        if ligandB is not None:
            ligandB = params.ligandB.split(',')

        ptfA_cache_file = None
        ptfB_cache_file = None
        if params.ptf_cache:
            log.debug("Checking for cached point files in: {0}".format(params.ptf_cache))
            ptfA_cache_file = params.ptf_cache.format(pdbid=pdbidA)
            ptfB_cache_file = params.ptf_cache.format(pdbid=pdbidB)

        log.info("Identifying Pocket Points")

        pointsA, ligandA = load_points(pdb_file=pdbA,
                                       pdbid=pdbidA,
                                       points_file=params.ptfA,
                                       ligands=ligandA,
                                       distance_cutoff=params.distance,
                                       point_cache=ptfA_cache_file,
                                       link_cached=params.link_cached,
                                       log=log,
                                       log_label='A')

        pointsB, ligandB = load_points(pdb_file=pdbB,
                                       pdbid=pdbidB,
                                       points_file=params.ptfB,
                                       ligands=ligandB,
                                       distance_cutoff=params.distance,
                                       point_cache=ptfB_cache_file,
                                       link_cached=params.link_cached,
                                       log=log,
                                       log_label='B')
                              
        log.info("Generating FEATURE vectors")
        ffA_cache_file = None
        ffB_cache_file = None
        if params.ff_cache:
            log.debug("Checking for cached FEATURE files in: {0}".format(params.ptf_cache))
            ffA_cache_file = params.ff_cache.format(pdbid=pdbidA)
            ffB_cache_file = params.ff_cache.format(pdbid=pdbidB)

        featurefileA = generate_featurefile(points=pointsA,
                                            feature_file=params.ffA,
                                            pdbid=pdbidA,
                                            feature_cache=ffA_cache_file,
                                            link_cached=params.link_cached,
                                            log=log,
                                            log_label='A')

        featurefileB = generate_featurefile(points=pointsB,
                                            feature_file=params.ffB,
                                            pdbid=pdbidB,
                                            feature_cache=ffB_cache_file,
                                            link_cached=params.link_cached,
                                            log=log,
                                            log_label='B')
    
        _numA = len(featurefileA.vectors)
        _numB = len(featurefileB.vectors)
    
        log.info("Comparing Vectors")
        scores = background.get_comparison_matrix(featurefileA, featurefileB)
        _num_scores = len(scores)
        log.info("Scored {0} vectors (out of {1}x{2}={3} total)".format(
                    _num_scores,
                    _numA,
                    _numB,
                    _numA * _numB))
        if params.raw_scores is not None:
            log.debug("Writing scores")
            matrixvaluesfile.dump(scores, params.raw_scores)
            params.raw_scores.close()
        normalized = scores.slice_values(NORMALIZED_SCORE)

        log.info("Aligning Pockets")
        alignment = align_scores_greedy(normalized, cutoff=params.cutoff)
        log.debug("Aligned {0} points".format(len(alignment)))
        total_score = sum(alignment.values())
        alignment_with_raw_scores = scores.subset_from_keys(alignment.keys())
        
        if params.alignment is not None:
            log.debug("Writing alignment")
            matrixvaluesfile.dump(alignment, params.alignment)
            params.alignment.close()
            
        log.info("Alignment Score: {0}".format(total_score))
        print("{0}\t{1}\t{2:0.5f}".format(pocketA.signature_string,
                                          pocketB.signature_string,
                                          total_score),
              file=params.output)
        
        log.info("Creating PyMol scripts")
        scriptA, scriptB = create_alignment_visualizations(pocketA.points, 
                                                 pocketB.points, 
                                                 alignment,
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
            ProteinFileType,
        )
        background_ff = cls.BACKGROUND_FF_DEFAULT
        background_coeff = cls.BACKGROUND_COEFF_DEFAULT

        if 'FEATURE_DIR' in os.environ:
            feature_dir = os.environ.get('FEATURE_DIR')
            env_bg_ff = os.path.join(feature_dir, background_ff)
            env_bg_coeff = os.path.join(feature_dir, background_coeff)
            if not os.path.exists(background_ff) and os.path.exists(env_bg_ff):
                background_ff = env_bg_ff
            if not os.path.exists(background_coeff) and os.path.exists(env_bg_coeff):
                background_coeff = env_bg_coeff

        parser = ArgumentParser("Identify and extract pockets around ligands in a PDB file")
        parser.add_argument('pdbA', metavar='PDBA', 
                                    type=ProteinFileType.compressed('r'),
                                    help='Path to first PDB file')
        parser.add_argument('pdbB', metavar='PDBB', 
                                    type=ProteinFileType.compressed('r'),
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
                                      default=background_ff,
                                      help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalization', metavar='COEFFICIENTS',
                                      type=FileType.compressed('r'),
                                      default=background_coeff,
                                      help='Map of normalization coefficients for residue type pairs [default: %(default)s')
        parser.add_argument('-p', '--allowed-pairs', metavar='PAIR_SET_NAME',
                                      choices=backgrounds.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
                                      default='classes',
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-d', '--distance', metavar='DISTANCE',
                                              type=float,
                                              default=cls.LIGAND_RESIDUE_DISTANCE,
                                              help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-c', '--cutoff', metavar='CUTOFF',
                                              type=float,
                                              default=cls.DEFAULT_CUTOFF,
                                              help='Minium score (cutoff) to align [default: %(default)s')
        parser.add_argument('-o', '--output', metavar='RESULTS',
                                              type=FileType.compressed('a'),
                                              default=stdout,
                                              help='Path to results file [default: STDOUT]')
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
        parser.add_argument('--ptf-cache', metavar='PTF_CACHE_TPL',
                                           type=str,
                                           default=None,
                                           nargs='?',
                                           help='Pattern to check for cached point files'
                                                ' (variables: {pdbid, ligid})'
                                                ' [default: None]')
        parser.add_argument('--ff-cache', metavar='FF_CACHE_TPL',
                                          type=str,
                                          default=None,
                                          nargs='?',
                                          help='Pattern to check for cached FEATURE files'
                                               ' (variables: {pdbid, ligid})'
                                               ' [default: None]')
        parser.add_argument('--pdb-dir', metavar='PDB_DIR',
                                         type=str,
                                         default=environ.get('PDB_DIR'),
                                         nargs='?',
                                         help='Directory in which to search for PDB files'
                                              ' [default: %(default)s')
        parser.add_argument('--dssp-dir', metavar='DSSP_DIR',
                                          type=str,
                                          default=environ.get('DSSP_DIR'),
                                          nargs='?',
                                          help='Directory in which to search for DSSP files'
                                              ' [default: %(default)s')
        parser.add_argument('--check-cached-first', default=False,
                                                    action='store_true',
                                                    help='Check for cache before extracting ligand')
        parser.add_argument('--link-cached', default=False,
                                             action='store_true',
                                             help='Link cache files when found')
        parser.add_argument('--raw-scores', metavar='SCORES',
                                            type=FileType.compressed('w'),
                                            default=None,
                                            nargs='?',
                                            help='Path to raw scores file [default: None]')
        parser.add_argument('--alignment', metavar='ALIGNMENT',
                                            type=FileType.compressed('w'),
                                            default=None,
                                            nargs='?',
                                            help='Path to alignment file [default: None]')
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
        parser.add_argument('--log-level', metavar='LEVEL',
                                           choices=LOG_LEVELS.keys(),
                                           default='debug',
                                           nargs='?',
                                           help="Set log level (%(choices)s) [default: %(default)s]")
        return parser



if __name__ == '__main__':
    import sys
    sys.exit(ComparePockets.run_as_script())
