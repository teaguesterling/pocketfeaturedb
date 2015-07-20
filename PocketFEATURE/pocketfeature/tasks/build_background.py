#!/usr/bin/env pythoe
from __future__ import print_function

import contextlib
import gzip
import itertools
import logging
import multiprocessing
import os
import random

from six import string_types

from feature.backends.external import generate_dssp_file
from feature.backends.wrappers import featurize_points_raw
from feature.io import (
    featurefile,
    pointfile,
)
from feature.io.locate_files import (
    find_pdb_file,
    find_dssp_file,
)
from pocketfeature.algorithms import GaussianStats
from pocketfeature.datastructs import (
    MatrixValues,
    PassThroughItems,
    PocketFeatureBackgroundMetaData,
    MEAN_VECTOR,
    MIN_VECTOR,
    MAX_VECTOR,
    STD_DEV_VECTOR,
    VAR_VECTOR,
)
from pocketfeature.io import (
    backgroundfile,
    featurefile as featurefile_pf,
    pdbfile,
    matrixvaluesfile,
)
from pocketfeature import defaults
from pocketfeature.tasks.core import (
    Task,
    ensure_all_imap_unordered_results_finish,
)
from pocketfeature.tasks.pocket import (
    create_pocket_around_ligand,
    find_ligand_in_structure,
    focus_structure,
    pick_best_ligand,
)
from pocketfeature.utils.args import LOG_LEVELS
from pocketfeature.utils.ff import get_vector_type

NUM_DIGITS_FOR_MODE = 3
BG_COEFFS_COLUMNS = ('mode', 'mean', 'std_dev', 'n', 'min', 'max')


@contextlib.contextmanager
def maybe_open(path, mode='r', opener=open):
    if path is not None:
        yield opener(path, mode)
    else:
        yield None


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


def pocket_from_pocket_def(pocket_def, residue_centers,
                           if_no_ligand=pick_best_ligand,
                           distance_threshold=6.0):

    pdb_data, ligand_data = pocket_def
    
    if isinstance(pdb_data, string_types):
        pdb_path = pdb_data
    else:
        pdb_id, pdb_path = pdb_data
    structure = pdbfile.load_file(pdb_path)

    if ligand_data is None:
        ligand = if_no_ligand(structure)
    else:
        chain_id, res_id, ligand_name = ligand_data
        structure = focus_structure(structure, chain=chain_id)
        if res_id is not None:
            ligand = find_ligand_in_structure(structure, res_id)
        else:
            ligand = find_ligand_in_structure(structure, ligand_name)
        
    if ligand is not None:
        pocket = create_pocket_around_ligand(structure, 
                                             ligand, 
                                             cutoff=distance_threshold,
                                             residue_centers=residue_centers)
    else:
        pocket = None
    return pocket


def _pocket_from_pocket_def_star(packed):
    pocket_def, args, kwargs = packed
    pocket = pocket_from_pocket_def(pocket_def, *args, **kwargs) 
    if pocket is not None:
        return pocket.pickelable
    else:
        return None


def parse_pocket_def_line(line):
    tokens = line.split()
    pdbid = tokens[0].upper()
    lig_data = None

    # TODO: Clean this up. Create a pocket def file format
    if len(tokens) > 1:
        chainid = None
        resid = None
        ligid = None

        lig_info = tokens[1]
        lig_info = lig_info.split('#')[0]  # Remove comments/counds
        lig_info = lig_info.split('/')  # Only split twice incase ligand
                                           # ID contains an _
        lig_info.extend(tokens[2:])
        # XXX: Delimiter should be something other than an _, / would be good

        n_lig_fields = len(lig_info)
        
        if n_lig_fields > 0:
            ligid = lig_info[0]
            if len(ligid) < 3:
                ligid += "_" * (3 - len(ligid))
            elif len(ligid) > 3:
                raise ValueError("Ligand ID must be 3 characters: {0}".format(ligid))
        if n_lig_fields > 1:
            chainid = lig_info[1]
            if len(chainid) > 1:
                raise ValueError("Chain ID {0} is longer than 1 character".format(chainid))
        if n_lig_fields > 2:
            try:
                resid = int(lig_info[2])
            except ValueError as e:
                raise ValueError("Residue ID must be integer: {0}".format(str(e)))
            if resid == 0:
                resid = None

        lig_data = (chainid, resid, ligid)
    
    pocket_def = (pdbid, lig_data)
    return pocket_def


def get_pdb_list(pdb_src, pdb_dir=None, log=logging, fail_on_missing=True):
    """ Takes a list of PDB IDs, a directory of PDBs, or a PocketDef file (TBD)
        and returns a list of (PDB_Info, Ligand_Info)
        where:
            PDB_Info: (PDBID, PDB File)
            Ligand_Info: (ChainID, ResidueID, LigandId)
    """
    if not os.path.exists(pdb_src):
        raise RuntimeError("{0} not found".format(pdb_src))
    elif os.path.isdir(pdb_src):
        log.info("Looking for PDBs in directory: {0}".format(pdb_src))
        pdb_names = os.listdir(pdb_src)
        pdb_locs = [(os.path.join(pdb_src, pdb_name), None) for pdb_name in pdb_names]
    else:
        log.info("Reading PDB IDs from file: {0}".format(pdb_src))
        pdb_locs = []
        with open(pdb_src) as f:
            for line in f:
                pocket_def = parse_pocket_def_line(line)
                pdb_locs.append(pocket_def)

    found = []
    for pdbid, lig_info in pdb_locs:
        try:
            pdb_file = find_pdb_file(pdbid, pdbdirList=pdb_dir)
            pdb_data = (pdbid, pdb_file)
            pocket_data = pdb_data, lig_info
            found.append(pocket_data)
        except ValueError:
            if fail_on_missing:
                log.error("Could not find PDB: {0}".format(pdbid))
                raise
            else:
                log.warning("Could not find PDB: {0}".format(pdbid))
  
    return found


def get_ptf_list(ptf_src, log=logging):
    if not os.path.exists(ptf_src):
        raise RuntimeError("{0} not found".format(ptf_src))
    elif os.path.isdir(ptf_src):
        log.info("Looking for PTFs in directory: {0}".format(ptf_src))
        ptf_names = os.listdir(ptf_src)
        ptf_locs = [os.path.join(ptf_src, ptf_name) for ptf_name in ptf_names]
    else:
        log.info("Reading Points from file: {0}".format(ptf_src))
        ptf_locs = [ptf_src]
    return ptf_locs


def featurize_point_stream(points, featurize_args=None, load_args=None):
    featurize_args = featurize_args or {}
    load_args = load_args or {}
    results = featurize_points_raw(points, **featurize_args)
    ff = featurefile_pf.iload(results, **load_args)
    return ff


def _featurize_point_stream_star(args):
    return featurize_point_stream(*args)


def calculate_residue_pair_normalization(key, thresholds, fileA, fileB, storeFile=None, compare_method=None):
    compute_raw_cutoff_similarity = defaults.ALLOWED_SIMILARITY_METHODS[compare_method]
    with gzip.open(fileA) as ioA, \
         gzip.open(fileB) as ioB, \
         maybe_open(storeFile, 'w', gzip.open) as ioStore:
        stats = GaussianStats(store=ioStore, mode_binning=NUM_DIGITS_FOR_MODE)
        ffA = featurefile.load(ioA)
        ffB = featurefile.load(ioB)
        #if fileA == fileB:
        #    # TODO: Should we really be special-casing A==B to ensure we don't
        #    #       compare each pair twice or compare the identity
        #    pairs = unique_product(ffA.features, ffB.vectors, skip=1)
        #else:
        #    pairs = itertools.product(ffA.features, ffB.features)
        if hasattr(compute_raw_cutoff_similarity, 'stream_similarities'):
            logging.info("Optimized similarlity")
            raw_scores = compute_raw_cutoff_similarity.stream_similarities(thresholds, ffA.features, ffB.features)
            for raw_score in raw_scores:
                stats.record(raw_score)
        else:
            pairs = itertools.product(ffA.features, ffB.features)
            for a, b in pairs:
                raw_score = compute_raw_cutoff_similarity(thresholds, a, b)
                stats.record(raw_score)

    if stats.n > 0:
        mode = float(stats.mode)
        mean = float(stats.mean)
        std = float(stats.std_dev)
        n = int(stats.n)
        low = float(stats.mins)
        high = float(stats.maxes)
    else:
        mode = mean = std = n = low = high = 0
    
    return key, (mode, mean, std, n, low, high)


def _calculate_residue_pair_normalization_star(args):
    return calculate_residue_pair_normalization(*args)


def create_background_features_from_stats(stats, **metadata_fields):
    metadata = PocketFeatureBackgroundMetaData()
    metadata.update(metadata_fields)
    comment = ["{0}".format(stats.n)]

    vectors = [
        metadata.create_vector(
            name=MEAN_VECTOR,
            features=stats.mean,
            comments=comment),
        metadata.create_vector(
            name=VAR_VECTOR,
            features=stats.variance,
            comments=comment),
        metadata.create_vector(
            name=STD_DEV_VECTOR,
            features=stats.std_dev,
            comments=comment),
        metadata.create_vector(
            name=MIN_VECTOR,
            features=stats.mins,
            comments=comment),
        metadata.create_vector(
            name=MAX_VECTOR,
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

        self.residue_centers = defaults.DEFAULT_RESIDUE_CENTERS

        if isinstance(self.residue_centers, string_types):
            self.residue_centers = defaults.NAMED_RESIDUE_CENTERS[self.residue_centers]

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

        self.point_file = os.path.join(params.ff_dir, 'points.ptf')

        self.bg = self.generate_vector_stats()
        if not params.skip_normalization:
            self.norms = self.generate_score_stats()

                
    def generate_vector_stats(self):
        params = self.params
        log = self.log
        threshold = params.std_threshold
        point_file = os.path.join(self.params.ff_dir, 'points.ptf')
        
        if params.resume and os.path.exists(params.background):
            with open(params.background) as f:
                bg = backgroundfile.load_stats_data(f)
        else:
            if params.resume and os.path.exists(self.point_file):
                log.info("Found existing pointfile at {0}".format(self.point_file))
                with open(self.point_file) as f:
                    points = pointfile.load(f)
                    vectors = self.create_vectors(points)
            elif params.pdbs is not None:
                pdbs = get_pdb_list(params.pdbs, pdb_dir=params.pdb_dir, log=self.log)
                self._num_pdbs = len(pdbs)
                log.info("Found {0} PDBs".format(self._num_pdbs))
                vectors = self.get_pocket_vectors(pdbs)
            elif params.ptfs is not None:
                ptfs = get_ptf_list(params.ptfs, log=self.log)
                self._num_pdbs = len(ptfs)
                log.info("Found {0} Point Files".format(self._num_pdbs))
                vectors = self.get_pointfile_vectors(ptfs)
            else:
                raise RuntimeError("Could not load points")

            stats, metadata, pdbs = self.process_vectors(vectors)
            bg = create_background_features_from_stats(stats,
                    NUM_SHELLS=metadata.num_shells,
                    SHELL_WIDTH=metadata.shell_width,
                    PROPERTIES=metadata.properties,
                    PDBID_LIST=pdbs,
                    SIMILARITY_STD_THRESHOLD=threshold
            )  # Threshold should be part of coeffs
                                                         # Need to add metadata to coeefs first
            log.info("Extracted {0} vectors".format(stats.n))
            log.debug("Writing Background stats to {0}".format(params.background))
            with open(params.background, 'w') as f:
                featurefile.dump(bg, f)
        return bg
    
    def generate_score_stats(self):
        params = self.params
        threshold = params.std_threshold
        log = self.log

        std_dev = self.bg.get(backgroundfile.STD_DEV_VECTOR)
        thresholds = threshold * std_dev.features

        pairs, resumed = self.get_allowed_ff_pairs()
        statsFiles = self.get_ff_pair_scores_files(pairs)
        num_pairs = len(pairs)
        all_args = ((key, thresholds, fA, fB, statsFiles[key], params.compare_method) 
                           for key, (fA, fB) in pairs.items())

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
                values = matrixvaluesfile.load(f, value_dims=BG_COEFFS_COLUMNS)
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
            self.pool = multiprocessing.Pool(params.num_processors)
            raw_items = self.pool.imap_unordered(_calculate_residue_pair_normalization_star, all_args)
            items = ensure_all_imap_unordered_results_finish(raw_items, expected=num_pairs)
        else:
            log.debug("Calculating {0} pairs serially".format(num_pairs))
            items = itertools.imap(_calculate_residue_pair_normalization_star, all_args)
        
        # split results (to also write out incrementally)
        items, local_items = itertools.tee(items)
        if params.progress:
            items = display_progress(items)

        values_out = PassThroughItems(items, dims=2, dim_refs=dict(enumerate(BG_COEFFS_COLUMNS)))
        log.debug("Writing Background normalization coefficients to {0}".format(params.normalization))
  
        with open(params.normalization, write_mode) as f:
            matrixvaluesfile.dump(values_out, f, header=True)

        # If resuming re-read all values
        if self.params.resume:
            with open(params.normalization) as f:
                values = matrixvaluesfile.load(f, value_dims=BG_COEFFS_COLUMNS, header=True)
        else:
            values = MatrixValues(local_items, value_dims=BG_COEFFS_COLUMNS)

        return values

    def get_pockets(self, pocket_defs):
        num_pdbs = len(pocket_defs)
        num_successful = 0
        num_failed = 0
        num_processors = min(self.params.num_processors, num_pdbs)
        kwargs = {
            'residue_centers': self.residue_centers,
            'distance_threshold': self.params.distance,
        }
        all_args = [(pocket_def, (), kwargs) for pocket_def in pocket_defs]
        if self.params.num_processors is not None and num_processors > 1:
            self.log.info("Extracting pockets with with {0} workers".format(num_processors))
            self.pool = multiprocessing.Pool(num_processors)
            raw_pockets = self.pool.imap_unordered(_pocket_from_pocket_def_star, all_args, 5)
            pockets = ensure_all_imap_unordered_results_finish(raw_pockets)
        else:
            self.pool = None
            pockets = itertools.imap(_pocket_from_pocket_def_star, all_args)

        for idx, pocket in enumerate(pockets, start=1):
            if pocket is not None:
                num_successful += 1
                name = pocket.signature_string
            else:
                num_failed += 1
                name = "Unknown"
            if self.params.progress:
                print("\r{0} of {1} PDBs processed ({2} successful, {3} failed) ({4})".format(
                            idx, 
                            num_pdbs, 
                            num_successful,
                            num_failed,
                            name), 
                        end="", file=sys.stderr)
                sys.stderr.flush()
            if pocket is not None:
                yield pocket

        if self.pool:
            self.pool.close()
            
        if self.params.progress:
            print("", file=sys.stderr)

    def get_points(self, pockets):
        for pocket in pockets:
            points = list(pocket.points)
            if self.params.all_data:
                ptf_file = self.get_ptf_file(pocket)
                with gzip.open(ptf_file, 'w') as f:
                    pointfile.dump(points, f)
            for point in points:
                self._num_points += 1
                yield point

    def get_predefined_points(self, predefined):
        for path in predefined:
            with open(path) as f:
                points = pointfile.loadi(f)
                for point in points:
                    yield point

    def get_pocket_vectors(self, pocket_defs):
        if self.params.max_points is not None:
            self.log.info("Shuffling PDBs since max_points specified")
            random.shuffle(pocket_defs)
            pocket_defs = pocket_defs[:self.params.max_points]
        pockets = self.get_pockets(pocket_defs)
        points = self.get_points(pockets)
        vectors = self.create_vectors(points)
        for vector in vectors:
            yield vector

    def get_pointfile_vectors(self, pointfiles):
        points = self.get_predefined_points(pointfiles)
        vectors = self.create_vectors(points)
        for vector in vectors:
            yield vector

    def create_vectors(self, points):
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
            self.log.info("Calculating with {0} workers".format(self.params.num_processors))
            args = ((point, featurize_args) for point in points)
            pool = multiprocessing.Pool(self.params.num_processors)
            vectors = pool.imap(_featurize_point_stream_star, args)
        else:
            if self.params.num_processors is not None and self.params.num_processors > 1:
                self.log.warning("Parallel FEATURE vector calculation not yet implemented")
            self.log.debug("Calculating serially")
            vectors = featurize_point_stream(points, featurize_args=featurize_args)

        return vectors
            
    def process_vectors(self, vectors):
        stats = GaussianStats(mode_binning=None)
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
            self.log.debug("Dumping source points to {0}".format(self.point_file))
            with open(self.point_file, 'w') as f:
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
            if self.params.show_dssp_action:
                self.log.info("Creating DSSP file: {0}".format(dssp))
            try:
                dssp = generate_dssp_file(pdb, dssp)
            except Exception as err:
                if self.params.show_dssp_action:
                    self.log.error("Failed to generate DSSP for {0}".format(pdbid))
                return None
        if not os.path.exists(dssp):
            raise ValueError("Missing DSSP File: {0}".format(dssp))
        if not os.path.exists(pdb):
            raise ValueError("Missing PDB File: {0}".format(pdb))
        return point

    def get_allowed_ff_pairs(self):
        allowed_pairs = defaults.ALLOWED_VECTOR_TYPE_PAIRS[self.params.allowed_pairs]
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
            key = backgroundfile.make_vector_type_key((typeA, typeB))
            if key in allowed_pairs and key not in finished:
                allowed_map[key] = (pathA, pathB)  # order isn't important
        return allowed_map, finished

    def get_ff_pair_scores_files(self, pairs):
        scores_map = {}
        for (typeA, typeB), (ffA, ffB) in pairs.items():
            key = backgroundfile.make_vector_type_key((typeA, typeB))
            if self.params.all_data:
                scores_file = "{0}-{1}.scores.gz".format(*key)
                scores_path = os.path.join(self.params.ff_dir, scores_file)
            else:
                scores_path = None
            scores_map[key] = scores_path
        return scores_map

    def get_ptf_file(self, pocket):
        sig = pocket.signature_string
        ptf_file = "{}.ptf.gz".format(sig)
        ptf_path = os.path.join(self.params.ff_dir, ptf_file)
        return ptf_path

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
        from argparse import ArgumentParser
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
        input_parser = parser.add_mutually_exclusive_group(required=True)
        input_parser.add_argument('pdbs', metavar='PDBS',
                                          nargs='?',
                                          help='Path to a file containing PDB ids or a directory of PDB files')
        input_parser.add_argument('--ptfs', metavar='PTF_DIR',
                                            nargs='?',
                                            help='Path to a directory containing pre-extracted point files')
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
                                      choices=defaults.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
                                      default=defaults.DEFAULT_VECTOR_TYPE_PAIRS,
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-t', '--std-threshold', metavar='NSTD',
                                     type=float,
                                     default=1.0,
                                     help="Number of standard deviations between to features to allow as 'similar'")
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
        parser.add_argument('-C', '--compare-method', metavar='COMPARISON',
                                              choices=defaults.ALLOWED_SIMILARITY_METHODS,
                                              default=defaults.DEFAULT_SIMILARITY_METHOD,
                                              help='Comparisoin method to use [default: %(default)s]')
        parser.add_argument('-P', '--num-processors', metavar='PROCS',
                                                      default=1,
                                                      type=int,
                                                      help='Number of processes to use [default: %(default)s]')
        parser.add_argument('--cleanup', action='store_true',
                                         default=False,
                                         help='Remove temporary FEATURE files upon completion [default: %(default)s]')
        parser.add_argument('--skip-normalization', action='store_true', 
                                                    default=False,
                                                    help="Force skip the normalization calculation step")
        parser.add_argument('--all-data', action='store_true',
                                          default=False,
                                          help='Write out all temporary files [default: %(default)s]')
        parser.add_argument('--progress', action='store_true',
                                          default=False,
                                          help='Show interactive progress [default: %(default)s]')
        parser.add_argument('--show-dssp-action', action='store_true',
                                                  default=False,
                                                  help='Show DSSP generation [default: %(default)s]')
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
    sys.exit(GeneratePocketFeatureBackground.run_as_script())
