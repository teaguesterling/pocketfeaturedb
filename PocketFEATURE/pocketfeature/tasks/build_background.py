#!/usr/bin/env pythoe
from __future__ import print_function

import contextlib
import gzip
import itertools
import logging
import multiprocessing
import os
import sys
import random

from feature.backends.external import generate_dssp_file 
from feature.backends.wrappers import featurize_points_raw
from feature.io import (
    featurefile,
    pointfile,
)
from feature.io.locate_files import (
    pdbidFromFilename,
    find_pdb_file,
    find_dssp_file,
)

from pocketfeature.algorithms import (
    cutoff_tanimoto_similarity,
    GaussianStats,
)
from pocketfeature.io import (
    backgrounds,
    featurefile as featurefile_pf,
    pdbfile,
    matrixvaluesfile,
)
from pocketfeature.io.matrixvaluesfile import (
    MatrixValues,
    PassThroughItems,
)
from pocketfeature.residues import DEFAULT_CENTERS
from pocketfeature.tasks.core import Task
from pocketfeature.tasks.pocket import (
    pick_best_ligand,
    create_pocket_around_ligand,
)
from pocketfeature.utils.args import LOG_LEVELS
from pocketfeature.utils.ff import get_vector_type
from pocketfeature.utils.pdb import guess_pdbid_from_stream


@contextlib.contextmanager
def existing_file(path, mode='r', resume=False):
    if path == '-':
        if mode == 'r' and resume:
            yield sys.stdin, True
        else:
            yield sys.stdout, False
    elif resume and os.path.exists(path):
        mode = 'rw'
        with open(path, mode) as f:
            yield (f, True)
    else:
        with open(path, mode) as f:
            yield (f, False)


def pocket_from_pdb(pdb_path, find_ligand=pick_best_ligand,
                              residue_centers=DEFAULT_CENTERS,
                              distance_threshold=6.0):
    structure = pdbfile.load_file(pdb_path)
    ligand = find_ligand(structure)
    pocket = create_pocket_around_ligand(structure, ligand, cutoff=distance_threshold,
                                                            residue_centers=residue_centers)
    return pocket


def featurize_point_stream(points, featurize_args={}, load_args={}):
    results = featurize_points_raw(points, **featurize_args)
    ff = featurefile_pf.iload(results)
    return ff


def _featurize_point_stream_star(args):
    return featurize_point_stream(*args)


def calculate_residue_pair_normalization(key, std_dev, fileA, fileB):
    stats = GaussianStats()
    std = std_dev.features
    with gzip.open(fileA) as ioA, \
         gzip.open(fileB) as ioB:
        ffA = featurefile.load(ioA)
        ffB = featurefile.load(ioB)
        pairs = itertools.product(ffA.vectors, ffB.vectors)
        for vectorA, vectorB in pairs:
            a = vectorA.features
            b = vectorB.features
            raw_score = cutoff_tanimoto_similarity(std, a, b)
            stats.record(raw_score)

    mode = mean = float(stats.mean)  # Mean == Mode for Gaussian
    std = float(stats.std_dev)
    
    return key, (mode, std)


def _calculate_residue_pair_normalization_star(args):
    return calculate_residue_pair_normalization(*args)


def create_background_features_from_stats(stats, **metadata_fields):
    metadata = featurefile_pf.PocketFeatureBackgroundMetaData()
    metadata.update(metadata_fields)
    comment = ["{0}".format(stats.n)]

    vectors = [
        metadata.create_vector(
            name=backgrounds.MEAN_VECTOR,
            features=stats.mean,
            comments=comment),
        metadata.create_vector(
            name=backgrounds.VAR_VECTOR,
            features=stats.variance,
            comments=comment),
        metadata.create_vector(
            name=backgrounds.STD_DEV_VECTOR,
            features=stats.std_dev,
            comments=comment),
        metadata.create_vector(
            name=backgrounds.MIN_VECTOR,
            features=stats.mins,
            comments=comment),
        metadata.create_vector(
            name=backgrounds.MAX_VECTOR,
            features=stats.maxes,
            comments=comment),
    ]
    
    bg = featurefile.FeatureFile(metadata, vectors)
    return bg


class GeneratePocketFeatureBackground(Task):
    BACKGROUND_FF_DEFAULT = 'background.ff'
    BACKGROUND_COEFF_DEFAULT = 'background.coeffs'
    TEMP_FF_DIR_DEFAULT = os.path.join(os.getcwd(), 'ff')
    LIGAND_RESIDUE_DISTANCE = 6.0

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(LOG_LEVELS.get(params.log_level, 'debug'))
        self.log = log

        self._num_pdbs = 0
        self._num_points = 0
        self._num_vectors = 0

        log.warn("PDB_DIR is {0}".format(params.pdb_dir))
        log.warn("DSSP_DIR is {0}".format(params.dssp_dir))
        log.warn("FEATURE_DIR is {0}".format(params.feature_dir))
        log.warn("temporary FF_DIR is {0}".format(params.ff_dir))

        if os.path.exists(params.ff_dir):
            if params.resume:
                log.warn("Resuming with feature vectors from FF_DIR")
            else:
                log.warning("FF_DIR is not empty and NOT resuming. Erasing temp files")
                for ff in os.listdir(params.ff_dir):
                    ff_path = os.path.join(params.ff_dir, ff)
                    log.debug("Deleted {0}".format(ff_path))
                    os.unlink(ff_path)
        else:
            if params.resume:
                log.error("Cannot resume without populated FF_DIR")
                sys.exit(-1)
            else:
                log.debug("Creating directory {0}".format(params.ff_dir))
                os.mkdir(params.ff_dir)
                
        self.bg = self.generate_vector_stats()
        self.norms = self.generate_score_stats()

                
    def generate_vector_stats(self):
        params = self.params
        log = self.log
        if params.resume and os.path.exists(params.background):
            with open(params.background) as f:
                bg = backgrounds.load_stats_data(f)
        else:
            pdbs = self.get_pdb_files()
            self._num_pdbs = len(pdbs)
            log.info("Found {0} PDBs".format(self._num_pdbs))
            vectors = self.get_pocket_vectors(pdbs)
            stats, metadata, pdbs = self.process_vectors(vectors)
            bg = create_background_features_from_stats(stats,
                    NUM_SHELLS=metadata.num_shells,
                    SHELL_WIDTH=metadata.shell_width,
                    PROPERTIES=metadata.properties,
                    PDBID_LIST=pdbs)
            log.info("Extracted {0} vectors".format(stats.n))
            log.debug("Writing Background stats to {0}".format(params.background))
            with open(params.background, 'w') as f:
                featurefile.dump(bg, f)
        return bg
    
    def generate_score_stats(self):
        params = self.params
        log = self.log
        std_dev = self.bg.get(backgrounds.STD_DEV_VECTOR)
        pairs, resumed = self.get_allowed_ff_pairs()
        num_pairs = len(pairs)
        all_args = ((key, std_dev, fA, fB) for key, (fA, fB) in pairs.items())

        if self.params.resume:
            num_resumed = len(resumed)
            log.info("Ignoring {0} already completed pairs".format(num_resumed))
            write_mode = 'a'
        else:
            num_resumed = 0
            write_mode = 'w'

        if num_pairs == 0:
            log.info("All residue pairs previously completed. Nothing to compute")
            with open(params.normalization) as f:
                values = matrixvaluesfile.load(f, value_dims=('mode', 'std_dev'))
            return values

        def display_progress(items):
            for idx, item in enumerate(items, start=1):
                key = item[0]
                key = ":".join(key)
                print("\r{0} of {1} residue pairs processed ({2})".format(idx, num_pairs, key), 
                        end="", file=sys.stderr)
                sys.stderr.flush()
                yield item
            print("", file=sys.stderr)

        log.info("Computing background normalizations for {0} residue pairs".format(num_pairs))
        num_processors = min(params.num_processors, num_pairs)
        if params.num_processors is not None and num_processors > 1:
            log.info("Calculating with {0} workers".format(params.num_processors))
            pool = multiprocessing.Pool(num_processors)
            items = pool.imap(_calculate_residue_pair_normalization_star, all_args)
        else:
            log.debug("Calculating {0} pairs serially".format(num_pairs))
            items = itertools.imap(_calculate_residue_pair_normalization_star, all_args)
        
        # split results (to also write out incrementally)
        items, local_items = itertools.tee(items)
        if params.progress:
            items = display_progress(items)

        values_out = PassThroughItems(items, value_dims=('mode', 'std_dev'))
        log.debug("Writing Background normalization coefficients to {0}".format(params.normalization))
  
        with open(params.normalization, write_mode) as f:
            matrixvaluesfile.dump(values_out, f)

        # If resuming re-read all values
        if self.params.resume:
            with open(params.normalization) as f:
                values = matrixvaluesfile.load(f, value_dims=('mode', 'std_dev'))
        else:
            values = MatrixValues(local_items, value_dims=('mode', 'std_dev'))

        return values

    def get_pockets(self, pdbs):
        num_pdbs = len(pdbs)
        for idx, pdb in enumerate(pdbs, start=1):
            if self.params.progress:
                print("\r{0} of {1} PDBs processed ({2})".format(idx, num_pdbs, pdb), 
                        end="", file=sys.stderr)
                sys.stderr.flush()
            pocket = pocket_from_pdb(pdb, distance_threshold=self.params.distance)
            yield pocket
        if self.params.progress:
            print("", file=sys.stderr)

    def get_points(self, pockets):
        for pocket in pockets:
            for point in pocket.points:
                self._num_points += 1
                yield point

    def get_pocket_vectors(self, pdbs):
        if self.params.max_points is not None:
            self.log.info("Shuffling PDBs since max_points specified")
            random.shuffle(pdbs)
        pockets = self.get_pockets(pdbs)
        points = self.get_points(pockets)
        for vector in self.featurize_points(points):
            self._num_vectors += 1
            yield vector

    # This is a member function as it uses lots of task parameters
    def featurize_points(self, points):
        points = self.preprocess_points(points)
        points = self.record_points(points)
        
        if self.params.max_points is not None:
            self.log.info("Limiting number of points to {0}".format(self.params.max_points))
            points = itertools.islice(points, self.params.max_points)

        featurize_args = {
            'environ': {
                'PDB_DIR': self.params.pdb_dir,
                'DSSP_DIR': self.params.dssp_dir,
                'FEATURE_DIR': self.params.feature_dir,
            },
        }

        self.log.info("Computing FEATURE vectors")
        if self.params.num_processors is not None and self.params.num_processors > 1 and False:
            pass
#            self.log.info("Calculating with {0} workers".format(self.params.num_processors))
#            args = ((point, featurize_args) for point in points)
#            pool = multiprocessing.Pool(self.params.num_processors)
#            vectors = pool.imap(_featurize_point_stream_star, args)
        else:
            if self.params.num_processors is not None and self.params.num_processors > 1:
                self.log.warning("Parallel FEATURE vector calculation not yet implemented")
            self.log.debug("Calculating serially")
            vectors = featurize_point_stream(points, featurize_args=featurize_args)

        return vectors

            
    def process_vectors(self, vectors):
        stats = GaussianStats()
        pdbs = set()
        metadata = None
        for idx, vector in enumerate(vectors, start=1):
            stats.record(vector.features)
            pdbs.update(vector.pdbid)   # vector.pdbid should be returning a list
            metadata = vector.metadata  # Store for later use
            ff_file = self.get_ff_file(vector)
            new_file = not os.path.exists(ff_file)
            with gzip.open(ff_file, 'a') as ff:
                featurefile_pf.dump_vector(vector, ff, include_metadata=new_file)
            if self.params.progress:
                print("\r{0} of {1} FEATURE vectors processed".format(idx, self._num_points), 
                        end="", file=sys.stderr)
                sys.stderr.flush()
        if self.params.progress:
            print("", file=sys.stderr)
                
        return stats, metadata, pdbs

    def preprocess_points(self, points):
        ok_pdbs = set()
        bad_pdbs = set()
        for point in points:
            pdbid = point.pdbid
            if pdbid in bad_pdbs:
                continue
            if pdbid not in ok_pdbs:
                try:
                    point = self.check_protein_files(point)
                    if point is not None:
                        ok_pdbs.add(pdbid)
                    else:
                        self.log.warning("Skipping {0}".format(pdbid))
                        bad_pdbs.add(pdbid)
                        continue
                except ValueError as err:
                    self.log.warning("Skipping {0} ({1})".format(pdbid, err))
                    bad_pdbs.add(pdbid)
                    continue
            yield point

    def record_points(self, points):
        if self.params.all_data:
            point_file = os.path.join(self.params.ff_dir, 'points.ptf')
            self.log.debug("Dumping source points to {0}".format(point_file))
            with open(point_file, 'w') as f:
                for point in points:
                    pointfile.dump([point], f)
                    yield point
        else:
            for point in points:
                yield point
    
    def check_protein_files(self, point):
        pdbid = point.pdbid
        pdb = find_pdb_file(pdbid, pdbdirList=self.params.pdb_dir)
        try:
            dssp = find_dssp_file(pdbid, dsspdirList=self.params.dssp_dir)
        except ValueError:
            dssp = os.path.join(self.params.dssp_dir, pdbid + ".dssp")
            self.log.info("Creating DSSP file: {0}".format(dssp))
            try:
                dssp = generate_dssp_file(pdb, dssp)
            except Exception as err:
                self.log.error("Failed to generate DSSP for {0}".format(pdbid))
                return None
        if not os.path.exists(dssp):
            raise ValueError("Missing DSSP File: {0}".format(dssp))
        if not os.path.exists(pdb):
            raise ValueError("Missing PDB File: {0}".format(pdb))
        return point

    def get_allowed_ff_pairs(self):
        allowed_pairs = backgrounds.ALLOWED_VECTOR_TYPE_PAIRS[self.params.allowed_pairs]
        if self.params.resume and os.path.exists(self.params.normalization):
            with open(self.params.normalization) as f:
                completed = matrixvaluesfile.load(f)
            finished = set(completed.keys())
        else:
            finished = []

        ff_types = self.get_res_ff_files()
        all_pairs = itertools.product(ff_types.items(), ff_types.items())
        allowed_map = {}
        for (typeA, pathA), (typeB, pathB) in all_pairs:
            key = backgrounds.make_vector_type_key((typeA, typeB))
            if key in allowed_pairs and key not in finished:
                allowed_map[key] = (pathA, pathB)  # order isn't important
        return allowed_map, finished

    def get_pdb_files(self):
        pdb_src = self.params.pdbs
        if not os.path.exists(pdb_src):
            raise RuntimeError("{0} not found".format(pdb_src))
        elif os.path.isdir(pdb_src):
            self.log.info("Looking for PDBs in directory: {0}".format(pdb_src))
            pdb_names = os.listdir(pdb_src)
            pdb_paths = [os.path.join(pdb_src, pdb_name) for pdb_name in pdb_names]
            pdb_files = [find_pdb_file(pdb, pdbdirList=self.params.pdb_dir) for pdb in pdb_paths]
        else:
            self.log.info("Reading PDB IDs from file: {0}".format(pdb_src))
            with open(pdb_src) as f:
                pdbids = list(f)
            pdb_files = [find_pdb_file(pdbid, pdbdirList=self.params.pdb_dir) for pdbid in pdbids]
        return pdb_files

    def get_ff_file(self, vector):
        res_type = get_vector_type(vector)
        res_file = "{0}.ff.gz".format(res_type)
        res_path = os.path.join(self.params.ff_dir, res_file)
        return res_path

    def get_res_ff_files(self):
        ff_dir = self.params.ff_dir
        ff_files = os.listdir(ff_dir)
        ff_types = [ff.split('.')[0] for ff in ff_files]
        ff_paths = [os.path.join(ff_dir, ff) for ff in ff_files]
        ff_map = dict(zip(ff_types, ff_paths))
        return ff_map

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import (
            ArgumentParser,
            FileType,
        )
        from pocketfeature.utils.args import FileType

        if 'PDB_DIR' in os.environ:
            pdb_dir = os.environ.get('PDB_DIR')
        else:
            pdb_dir = '.'

        if 'DSSP_DIR' in os.environ:
            dssp_dir = os.environ.get('DSSP_DIR')
        else:
            dssp_dir = '.'

        if 'FEATURE_DIR' in os.environ:
            feature_dir = os.environ.get('FEATURE_DIR')
        else:
            feature_dir = '.'

        parser = ArgumentParser(
            """Generate background files for PocketFEATURE calculations""")
        parser.add_argument('pdbs', metavar='PDBS',
                                    help='Path to a file containing PDB ids or a directory of PDB files')
        parser.add_argument('--pdb-dir', metavar='PDB_DIR', 
                                         help='Directory to look for PDBs in [default: %(default)s|PDBS]',
                                         default=pdb_dir)
        parser.add_argument('--dssp-dir', metavar='PDB_DIR', 
                                          help='Directory to look for PDBs in [default: %(default)s]',
                                          default=dssp_dir)
        parser.add_argument('--feature-dir', metavar='FEATURE_DIR', 
                                          help='Directory to look for FEATURE data files in [default: %(default)s]',
                                          default=feature_dir)
        parser.add_argument('-b', '--background', metavar='FEATURESTATS',
                                                  default=cls.BACKGROUND_FF_DEFAULT,
                                                  help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalization', metavar='COEFFICIENTS',
                                      default=cls.BACKGROUND_COEFF_DEFAULT,
                                      help='Map of normalization coefficients for residue type pairs [default: %(default)s]')
        parser.add_argument('-f', '--ff-dir', metavar='FF_DIR',
                                              default=cls.TEMP_FF_DIR_DEFAULT,
                                              help='Directory to store temporary FEATURE files [default: %(default)s]')
        parser.add_argument('-p', '--allowed-pairs', metavar='PAIR_SET_NAME',
                                      choices=backgrounds.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
                                      default='classes',
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-r', '--resume', action='store_true',
                                              default=False,
                                              help='Resume with existing files if possible [default: %(default)s]')
        parser.add_argument('-d', '--distance', metavar='CUTOFF',
                                              type=float,
                                              default=cls.LIGAND_RESIDUE_DISTANCE,
                                              help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('--max-points', metavar='MAX_POINTS',
                                            type=int,
                                            default=None,
                                            help='Limit the number of points to include')
        parser.add_argument('--validation', metavar=('POS_PDBIDS', 'NEG_PDBIDS'), nargs=2,
                                           default=None,
                                           help='Lists PDBs containing positive/negative hits [default: None]')
        parser.add_argument('-P', '--num-processors', metavar='PROCS',
                                                      default=1,
                                                      type=int,
                                                      help='Number of processes to use [default: %(default)s]')
        parser.add_argument('--cleanup', action='store_true',
                                         default=False,
                                         help='Remove temporary FEATURE files upon completion [default: %(default)s]')
        parser.add_argument('--all-data', action='store_true',
                                          default=False,
                                          help='Write out all temporary files [default: %(default)s]')
        parser.add_argument('--progress', action='store_true',
                                          default=False,
                                          help='Show interactive progress [default: %(default)s]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     default=stderr,
                                     help='Path to log errors [default: STDERR]')
        parser.add_argument('--log-level', metavar='LEVEL',
                                           choices=LOG_LEVELS.keys(),
                                           default='debug',
                                           nargs='?',
                                           help="Set log level (%(choices)s) [default: %(default)s]")
        return parser


if __name__ == '__main__':
    import sys
    sys.exit(FeatureFileCompare.run_as_script())
