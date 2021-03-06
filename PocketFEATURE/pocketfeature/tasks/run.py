#!/usr/bin/env python
from __future__ import absolute_import, print_function

from taskbase import (
    Task,
    TaskFailure,
    use_file,
)

import csv
import logging
import os

from feature.io import (
    pointfile,
)
from feature.io.common import open_compressed
from pocketfeature.io import (
    backgroundfile,
    featurefile,
    matrixvaluesfile,
    pdbfile,
)

from .extract import PocketExtraction
from .featurize import FeaturizePoints
from .compare import FeatureFileComparison
from .align import ScoreAlignment
from .rmsd import AlignmentRmsdComputation


class BaseTask(Task):

    def setup(self, params=None, **kwargs):
        params = params or self.params
        defaults = self.defaults(**self.conf)
        self.setup_task(params, defaults=defaults, **kwargs)
        self.setup_params(params, defaults=defaults, **kwargs)
        self.setup_inputs(params, defaults=defaults, **kwargs)

    def load_inputs(self):
        pass

    def prepare_subtasks(self):
        #TODO Finish parameter mapping
        self.subtask_pick_pocketA = PocketExtraction.create_subtask(self, tag='pocketA')
        self.subtask_pick_pocketB = PocketExtraction.create_subtask(self, tag='pocketB')

        self.subtask_featurizeA = FeaturizePoints.create_subtask(self, tag='pocketA')
        self.subtask_featurizeB = FeaturizePoints.create_subtask(self, tag='pocketB')

        self.subtask_compare_features = FeatureFileComparison.create_subtask(self)
        self.subtask_align_scores = ScoreAlignment.create_subtask(self)

        self.subtask_alignment_rmsd = AlignmentRmsdComputation(self)

    def execute(self):
        pass

    def produce_results(self):
        pass

    def setup_params(self, params, defaults=None, **kwargs):
        pass

    def setup_inputs(self, params, defaults=None, **kwargs):
        pass

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="")
        return parser

    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        cls.input_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.task_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.parameter_arguments(parser, stdin, stdout, stderr, environ, **kwargs)

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        defaults = super(BaseTask, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        defaults.update(cls.paremeter_defaults(stdin, stdout, stderr, environ, **kwargs))
        return defaults

    @classmethod
    def parameter_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        pass

    @classmethod
    def input_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        pass


    @classmethod
    def paremeter_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {}


if __name__ == '__main__':
    import sys
    sys.exit(BaseTask.run_as_script())


def load_points(pdb_file,
                points_file,
                pdbid=None,
                modelid=None,
                chainid=None,
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
        with open_compressed(point_cache) as f:
            points = pointfile.load(f)
    else:
        log.debug("Loading structure {label}".format(label=log_label))
        structure = pdbfile.load(pdb_file, pdbid=pdbid)
        structure = focus_structure(structure, model=modelid, chain=chainid)

        log.info("Finding ligands in structure {label}".format(label=log_label))
        if ligands is None:
            log.debug("Guessing ligand {label}".format(label=log_label))
            ligand = pick_best_ligand(structure)
        else:
            log.debug("Searching for ligand {label} ({ligands})".format(label=log_label,
                                                                        ligands=" ".join(ligands)))
            ligand = find_one_of_ligand_in_structure(structure, ligands)

        if ligand is None:
            log.warn("No ligand found in pocket {label}".format(label=log_label))
            return None, None

        log.debug("Creating pocket {label}".format(label=log_label))
        pocket = create_pocket_around_ligand(structure, ligand, cutoff=distance_cutoff)
        points = list(pocket.points)
        
        if point_cache is not None:
            log.debug("Caching pocket {label}".format(label=log_label))
            with open_compressed(point_cache, 'w') as f:
                pointfile.dump(points, f)
    
    pdb_file.close()
    if points_file is not None:
        if link_cached:
            points_file.close()
            original_name = points_file.name
            if not os.path.exists(original_name) and os.path.getsize(original_name) == 0:
                log.debug("Linking to cached pocket {label}".format(label=log_label))
                os.unlink(original_name)
                os.symlink(point_cache, original_name)
        else:
            log.debug("Writing pocket {label}".format(label=log_label))
            pointfile.dump(points, points_file)
            points_file.close()

    return points, ligand



def generate_featurefile(points,
                         feature_file,
                         feature_cache=None,
                         link_cached=False,
                         featurize_args=None,
                         environ=os.environ,
                         log=logging,
                         log_label="Pocket"):
    if feature_cache is not None and os.path.exists(feature_cache):
        log.info("Using cached featurefile for {label}: {cache}".format(label=log_label,
                                                                        cache=feature_cache))
        with open_compressed(feature_cache) as f:
            features = featurefile.load(f)
            using_cached = True
    else:
        log.debug("FEATURIZING Pocket {label}".format(label=log_label))
        featurize_args = featurize_args or {}
        featurize_args.setdefault('environ', environ)
        features = featurize_points(points, 
                                    featurize_args=featurize_args,
                                    featurefile_args={
                                        'rename_from_comment': 'DESCRIPTION'})
        using_cached = False

        if feature_cache is not None:
            log.debug("Caching features {label}".format(label=log_label))
            with open_compressed(feature_cache, 'w') as f:
                featurefile.dump(features, f)


    if feature_file is not None:
        if using_cached and link_cached:
            original_name = feature_file.name
            feature_file.close()
            if os.path.exists(original_name) and os.path.getsize(original_name) == 0:
                log.debug("Replacing {original} with previously cached".format(original=original_name))
                os.unlink(original_name)
            log.debug("Linking to cached features {label}".format(label=log_label))
            os.symlink(feature_cache, original_name)
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

    COULD_NOT_FIND_POCKET = 1

    def run(self):
        self.computed = {}

        params = self.params
        environ = dict(os.environ.items())
        update_environ_from_namespace(environ, params)

        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(LOG_LEVELS.get(params.log_level, 'debug'))

        log.info("Loading background")
        log.debug("Allowed residue pairs: {0}".format(params.allowed_pairs)) 
        comparison_method = Compare.COMPARISON_METHODS[params.comparison_method]
        alignment_method = AlignScores.ALIGNMENT_METHODS[params.alignment_method]
        scale_method = AlignScores.SCALE_METHODS[params.scale_method]

        background = backgroundfile.load(stats_file=params.background,
                                         norms_file=params.normalization,
                                         compare_function=comparison_method,
                                         allowed_pairs=params.allowed_pairs,
                                         std_threshold=params.std_threshold)

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
                                       modelid=params.modelA,
                                       chainid=params.chainA,
                                       points_file=params.ptfA,
                                       ligands=ligandA,
                                       distance_cutoff=params.distance,
                                       point_cache=ptfA_cache_file,
                                       link_cached=params.link_cached,
                                       log=log,
                                       log_label='A')

        pointsB, ligandB = load_points(pdb_file=pdbB,
                                       pdbid=pdbidB,
                                       modelid=params.modelB,
                                       chainid=params.chainB,
                                       points_file=params.ptfB,
                                       ligands=ligandB,
                                       distance_cutoff=params.distance,
                                       point_cache=ptfB_cache_file,
                                       link_cached=params.link_cached,
                                       log=log,
                                       log_label='B')

        if pointsA is None or pointsB is None:
            return self.COULD_NOT_FIND_POCKET

        log.info("Extrating pocket names")
        pointsA = list(pointsA)
        pointsB = list(pointsB)
        try:
            signature_stringA = get_pocket_signature(pointsA)
            signature_stringB = get_pocket_signature(pointsB)
        except (ValueError):
            return self.COULD_NOT_FIND_POCKET

        self.computed['pocketA'] = signature_stringA
        self.computed['pocketB'] = signature_stringB
                              
        log.info("Generating FEATURE vectors")
        ffA_cache_file = None
        ffB_cache_file = None
        if params.ff_cache:
            log.debug("Checking for cached FEATURE files in: {0}".format(params.ff_cache))
            ffA_cache_file = params.ff_cache.format(pdbid=pdbidA, signature=signature_stringA)
            ffB_cache_file = params.ff_cache.format(pdbid=pdbidB, signature=signature_stringB)

        featurefileA = generate_featurefile(points=pointsA,
                                            feature_file=params.ffA,
                                            feature_cache=ffA_cache_file,
                                            link_cached=params.link_cached,
                                            environ=environ,
                                            log=log,
                                            log_label='A')

        featurefileB = generate_featurefile(points=pointsB,
                                            feature_file=params.ffB,
                                            feature_cache=ffB_cache_file,
                                            link_cached=params.link_cached,
                                            environ=environ,
                                            log=log,
                                            log_label='B')
    
        numA = len(featurefileA.vectors)
        numB = len(featurefileB.vectors)

        self.computed['numA'] = numA
        self.computed['numB'] = numB
    
        log.info("Comparing Vectors")
        scores = background.get_comparison_matrix(featurefileA, featurefileB)
        num_scores = len(scores)
        self.computed['num_scored'] = num_scores

        log.info("Scored {0} vectors (out of {1}x{2}={3} total)".format(
                    num_scores,
                    numA,
                    numB,
                    numA * numB))
        if params.raw_scores is not None:
            log.debug("Writing scores")
            matrixvaluesfile.dump(scores, params.raw_scores)
            params.raw_scores.close()
        normalized = scores.slice_values(NORMALIZED_SCORE)

        log.info("Aligning Pockets")
        alignment = align_scores(alignment_method, normalized, cutoff=params.cutoff)
        num_aligned = len(alignment)
        self.computed['num_aligned'] = num_aligned
        log.debug("Aligned {0} points".format(len(alignment)))

        total_score = sum(alignment.values())
        self.computed['alignment_score'] = round(total_score, 3)

        scale_params = ()
        scale_sizes = (numA, numB, len(scores), num_aligned)
        scaled_score = scale_method(scale_params, scale_sizes, total_score)
        self.computed['scaled_score'] = round(scaled_score, 3)

        #alignment_with_raw_scores = scores.subset_from_keys(alignment.keys())
        
        if params.alignment is not None:
            log.debug("Writing alignment")
            matrixvaluesfile.dump(alignment, params.alignment)
            params.alignment.close()
            
        log.info("Alignment Score: {0}".format(total_score))

        alignment_rmsd = compute_alignment_rmsd(alignment, pointsA, pointsB)
        self.computed['alignment_rmsd'] = round(alignment_rmsd, 3)

        writer = csv.DictWriter(params.output,
                                dialect=csv.excel_tab,
                                fieldnames=('pocketA', 'pocketB', 'numA','numB',
                                            'num_scored', 'num_aligned',
                                            'alignment_score', 'scaled_score', 'alignment_rmsd'))
        writer.writeheader()
        writer.writerow(self.computed)

        if params.pymolA is not None or params.pymolB is not None:
            log.info("Creating PyMol scripts")
            scriptA, scriptB = create_alignment_visualizations(pointsA,
                                                               pointsB,
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
    def defaults(cls, stdin, stdout, stderr, environ):
        background_ff = cls.BACKGROUND_FF_DEFAULT
        background_coeff = cls.BACKGROUND_COEFF_DEFAULT

        if 'POCKETFEATURE_DIR' in os.environ:
            pocketfeature_dir = os.environ.get('POCKETFEATURE_DIR')
            env_bg_ff = os.path.join(pocketfeature_dir, background_ff)
            env_bg_coeff = os.path.join(pocketfeature_dir, background_coeff)
            if not os.path.exists(background_ff) and os.path.exists(env_bg_ff):
                background_ff = env_bg_ff
            if not os.path.exists(background_coeff) and os.path.exists(env_bg_coeff):
                background_coeff = env_bg_coeff

        if 'FEATURE_DIR' in os.environ:
            feature_dir = os.environ.get('FEATURE_DIR')
            env_bg_ff = os.path.join(feature_dir, background_ff)
            env_bg_coeff = os.path.join(feature_dir, background_coeff)
            if not os.path.exists(background_ff) and os.path.exists(env_bg_ff):
                background_ff = env_bg_ff
            if not os.path.exists(background_coeff) and os.path.exists(env_bg_coeff):
                background_coeff = env_bg_coeff

        if not os.path.exists(background_ff):
            background_ff = None

        if not os.path.exists(background_coeff):
            background_coeff = None

        return {
            'modelA': 0,
            'modelB': 0,
            'chainA': None,
            'chainB': None,
            'ligandA': None,
            'ligandB': None,
            'background': background_ff,
            'normalization': background_coeff,
            'allowed_pairs': 'classes',
            'comparison_method': 'tversky22',
            'alignment_method': 'onlybest',
            'scale_method': 'none',
            'std_threshold': 1.0,
            'distance': cls.LIGAND_RESIDUE_DISTANCE,
            'cutoff': cls.DEFAULT_CUTOFF,
            'output': stdout,
            'ptfA': None,
            'ptfB': None,
            'ffA': None,
            'ffB': None,
            'ptf_cache': None,
            'ff_cache': None,
            'pdb_dir': environ.get('PDB_DIR', '.'),
            'dssp_dir': environ.get('DSSP_DIR', '.'),
            'check_cache_first': False,
            'link_cached': False,
            'raw_scores': None,
            'alignment': None,
            'pymolA': None,
            'pymolB': None,
            'rescale': False,
            'log': stderr,
            'log_level': 'info',
        }


    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import (
            FileType,
            ProteinFileType,
        )

        parser = ArgumentParser("Identify and extract pockets around ligands in a PDB file")
        parser.add_argument('pdbA', metavar='PDBA', 
                                    type=ProteinFileType.compressed('r'),
                                    help='Path to first PDB file')
        parser.add_argument('pdbB', metavar='PDBB', 
                                    type=ProteinFileType.compressed('r'),
                                    help='Path to second PDB file')
        parser.add_argument('--modelA', metavar='MODELID',
                                         type=int,
                                         nargs='?',
                                         help='PDB Model to use from PDB A [default: <first>]')
        parser.add_argument('--modelB', metavar='MODELID',
                                         type=str,
                                         nargs='?',
                                         help='PDB Model to use from PDB B [default: <first>]')
        parser.add_argument('--chainA', metavar='CHAINID',
                                         type=str,
                                         nargs='?',
                                         help='Chain to restrict pocket to from PDB A [default: <any>]')
        parser.add_argument('--chainB', metavar='CHAINID',
                                         type=str,
                                         nargs='?',
                                         help='Chain to restrict pocket to from PDB B [default: <any>]')
        parser.add_argument('--ligandA', metavar='LIGA',
                                         type=str,
                                         nargs='?',
                                         help='Ligand ID to build first pocket around [default: <largest>]')
        parser.add_argument('--ligandB', metavar='LIGB',
                                         type=str,
                                         nargs='?',
                                         help='Ligand ID to build second pocket around [default: <largest>]')
        parser.add_argument('-b', '--background', metavar='FEATURESTATS',
                                      type=FileType.compressed('r'),
                                      help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalization', metavar='COEFFICIENTS',
                                      type=FileType.compressed('r'),
                                      help='Map of normalization coefficients for residue type pairs [default: %(default)s')
        parser.add_argument('-p', '--allowed-pairs', metavar='PAIR_SET_NAME',
                                      choices=Compare.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-C', '--comparison-method', metavar='COMPARISON_METHOD',
                                      choices=Compare.COMPARISON_METHODS.keys(),
                                      help='Scoring mehtod to use (one of %(choices)s) [default: %(default)s]')
        parser.add_argument('-A', '--alignment-method', metavar='ALIGN_METHOD',
                                      choices=AlignScores.ALIGNMENT_METHODS,
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-S', '--scale-method', metavar='SCALE_METHOD',
                                      choices=AlignScores.SCALE_METHODS.keys(),
                                      help="Method to re-scale score based on pocket sizes (one of: %(choices)s) [default: %(default)s]")
        parser.add_argument('-t', '--std-threshold', metavar='NSTD',
                                     type=float,
                                     help="Number of standard deviations between to features to allow as 'similar'")
        parser.add_argument('-d', '--distance', metavar='DISTANCE',
                                                type=float,
                                                help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-c', '--cutoff', metavar='CUTOFF',
                                              type=float,
                                              help='Minium score (cutoff) to align [default: %(default)s')
        parser.add_argument('-o', '--output', metavar='RESULTS',
                                              type=FileType.compressed('a'),
                                              default=stdout,
                                              help='Path to results file [default: STDOUT]')
        parser.add_argument('--ptfA', metavar='PTFA',
                                      type=FileType.compressed('w'),
                                      nargs='?',
                                      help='Path to first point file [default: None]')
        parser.add_argument('--ptfB', metavar='PTFB',
                                      type=FileType.compressed('w'),
                                      nargs='?',
                                      help='Path to second point file [default: None]')
        parser.add_argument('--ffA', metavar='FFA',
                                     type=FileType.compressed('w'),
                                     nargs='?',
                                     help='Path to first FEATURE file [default: None]')
        parser.add_argument('--ffB', metavar='FFB',
                                     type=FileType.compressed('w'),
                                     nargs='?',
                                     help='Path to second FEATURE file [default: None]')
        parser.add_argument('--ptf-cache', metavar='PTF_CACHE_TPL',
                                           type=str,
                                           nargs='?',
                                           help='Pattern to check for cached point files'
                                                ' (variables: {pdbid})'
                                                ' [default: None]')
        parser.add_argument('--ff-cache', metavar='FF_CACHE_TPL',
                                          type=str,
                                          nargs='?',
                                          help='Pattern to check for cached FEATURE files'
                                               ' (variables: {pdbid, ligid, signature})'
                                               ' [default: None]')
        parser.add_argument('--pdb-dir', metavar='PDB_DIR',
                                         type=str,
                                         nargs='?',
                                         help='Directory in which to search for PDB files'
                                              ' [default: %(default)s')
        parser.add_argument('--dssp-dir', metavar='DSSP_DIR',
                                          type=str,
                                          default=environ.get('DSSP_DIR'),
                                          nargs='?',
                                          help='Directory in which to search for DSSP files'
                                              ' [default: %(default)s')
        parser.add_argument('--check-cached-first', action='store_true',
                                                    help='Check for cache before extracting ligand')
        parser.add_argument('--link-cached', action='store_true',
                                             help='Link cache files when found')
        parser.add_argument('--raw-scores', metavar='SCORES',
                                            type=FileType.compressed('w'),
                                            nargs='?',
                                            help='Path to raw scores file [default: None]')
        parser.add_argument('--alignment', metavar='ALIGNMENT',
                                           type=FileType.compressed('w'),
                                           nargs='?',
                                           help='Path to alignment file [default: None]')
        parser.add_argument('--pymolA', metavar='PYMOLA',
                                        type=FileType('w'),
                                        nargs='?',
                                        help='Path to first PyMol script [default: None]')
        parser.add_argument('--pymolB', metavar='PYMOLB',
                                        type=FileType('w'),
                                        nargs='?',
                                        help='Path to second PyMol script [default: None]')
        parser.add_argument('--rescale', action='store_true',
                                         help='EXPERIMENTAL: Rescale score to pocket size [default: No]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     help='Path to log errors [default: %(default)s]')
        parser.add_argument('--log-level', metavar='LEVEL',
                                           choices=LOG_LEVELS.keys(),
                                           nargs='?',
                                           help="Set log level (%(choices)s) [default: %(default)s]")
        parser.set_defaults(**cls.defaults(stdin, stdout, stderr, environ))
        return parser



if __name__ == '__main__':
    import sys
    sys.exit(ComparePockets.run_as_script())
