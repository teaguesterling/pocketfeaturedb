#!/usr/bin/env python
from __future__ import print_function

import contextlib
import gzip
import itertools
import multiprocessing
import os
import sys

from feature.backends.wrappers.external import generate_dssp_file 
from feature.backends.wrappers import featurize_points_raw
from feature.io import featurefile
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
from pocketfeature.io.matrixvaluesfile import MatrixValues
from pocketfeature.residues import DEFAULT_CENTERS
from pocketfeature.tasks.featurize import featurize_points
from pocketfeature.tasks.core import Task
from pocketfeature.tasks.pocket import (
    pick_best_ligand,
    create_pocket_around_ligand,
)
from pocketfeature.utils.ff import get_vector_type


@contextlib.contextmanager
def existing_file(path, mode='r', resume=False):
    if path == '-'
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


def pocket_from_pdb(pdb_file, find_ligand=pick_best_ligand,
                              residue_centers=DEFAULT_CENTERS,
                              distance_threshold=6.0):
    with open(path) as pdb:
        pdbid, pdb = guess_pdbid_from_stream(pdb)
        structure = pdbfile.load(pdb)
    ligand = find_ligand(structure)
    pocket = create_pocket_around_ligand(structure, ligand, cutoff=distance_threshold,
                                                            residue_centers=residue_centers)
    return pocket


def calculate_residue_pair_normalization(std_dev fileA, fileB):
    stats = OnlineStatistics()
    with gzip.open(fileA) as ioA, \
         gzip.open(fileB) as ioB:
        ffA = featurefile.load(ioA)
        ffB = featurefile.load(ioB)
        pairs = itertools.product(ffA.vectors, ffB.vectors)
        for vectorA, vectorB in pairs:
            raw_score = cutoff_tanimoto_similarity(std_dev, vectorA, vectorB)
            stats.record(raw_score)

    mode = mean = stats.mean  # Mean == Mode for Gaussian
    std = stats.std
    
    return mode, std


def _calculate_residue_pair_normalization_star(args):
    return calculate_residue_pair_normalization(*args)


def create_background_from_stats(stats, **metadata_fields):
    metadata = featurefile_pf.PocketFeatureBackgroundMetaData()
    metadata.update(metadata_fields)
    comment = "{0}".format(stats.n)

    mean = metadata.create_vector_template()
    mean.name = background.MEAN_VECTOR
    mean.features = stats.mean
    mean.comment = comment

    var = metadata.create_vector_template()
    var.name = background.VAR_VECTOR
    var.features = stats.variance
    var.comment = comment


    std = metadata.create_vector_template()
    std.name = background.STD_DEV_VECTOR
    std.features = stats.std_dev
    std.comment = comment

    bg = featurefile.FeatureFile(metadata, [mean, var, std])
    return bg


class FeatureFileBackgroundGen(Task):
    BACKGROUND_FF_DEFAULT = 'background.ff'
    BACKGROUND_COEFF_DEFAULT = 'background.coeffs'
    TEMP_FF_DIR_DEFAULT = os.path.join(os.getcwd(), 'ff')
    LIGAND_RESIDUE_DISTANCE = 6.0

    def run(self):
        params = self.params
        self.bg = self.generate_vector_stats()
        self.norms = self.generate_score_stats()        
                
    def generate_vector_stats(self):
        params = self.params
        if params.resume and os.path.exists(params.background):
            raise NotImplementedError("Resume not yet implemented")
        else:
            background = featurefile.load
            pdbs = self.get_pdb_files()
            vectors = self.get_pocket_vectors(pdbs)
            stats, metadata, pdbs = self.process_vectors(vectors)
            bg = create_background_from_stats(stats,
                    NUM_SHELLS=metadata.num_shells,
                    SHELL_WIDTH=metadata.shell_width,
                    PDBID_LIST=pdbs)
            with open(params.background, w) as f:
                featurefile.dump(bg, f)
        return bg
    
    def generate_score_stats(self):
        parmas = self.params
        std_dev = self.bg.std_dev
        pairs = self.get_allowed_ff_pairs()
        all_keys = pairs.keys()
        all_args = ((std_dev, fA, fB) for fA, fB in pairs.values())
        if self.params.num_processors > 1:
            pool = multiprocessing.Pool(params.num_processors)
            all_stats = pool.map(_calculate_residue_pair_normalization_star, all_args)
        else:
            all_stats = map(_calculate_residue_pair_normalization_star, all_args)
        values = MatrixValues(zip(all_keys, all_stats), value_dims=('mode', 'std_dev'))
        
        with open(params.normalization, 'w') as f:
            matrixvaluesfile.dump(values, f)
        return values
            
    def process_vectors(self, vectors):
        stats = GaussianStats()
        pdbs = set()
        metadata = None
        for vector in vectors:
            stats.record(vector)
            pdbs.update(vector.pdbid)   # vector.pdbid should be returning a list
            metadata = vector.metadata  # Store for later use
            ff_file = self.get_ff_file(vector)
            new_file = not os.path.exists(ff_file)
            with gzip.open(ff_file, 'a') as ff:
                featurefile_pf.dump_vector(vector, ff, include_metadata=new_file)
        return stats, metadata, pdbs

    # This is a member function as it uses lots of task parameters
    def featurize_pocket(self, pocket):
        pdbid = pocket.pdbid
        pdb = find_pdb_file(pdbid, pdbdirList=self.params.pdb_dir)  # Sanity checks
        try:
            dssp = find_dssp_file(pdbid, dsspdirList=self.params.dssp_dir)
        except ValueError:
            dssp = os.path.join(pdbid + ".dssp")
            dssp = generate_dssp_file(pdb, dssp)
        
        featurize_args = {
            'environ': {
                'PDB_DIR': self.params.pdb_dir,
                'DSSP_DIR': self.params.dssp_dir,
            }
        }

        features = featurize_points(pocket.points, **featurize_args)
        return features

    def get_pdb_files(self):
        pdb_src = self.params.pdbs
        if not os.path.exists(pdb_src):
            raise RuntimeError("{0} not found".format(pdbs))
        elif os.isdir(pdbs):
            pdb_files = os.listdir(pdb_src)
        else:
            with open(pdb_src) as f:
                pdbids = list(f)
            pdb_files = [find_pdb_file(pdbid, pdbdirList=self.params.pdb_dir) for pdbid in pdbids]
        return pdb_files

    def get_pocket_vectors(self, pdbs):
        for pdb in pdbs:
            pocket = pocket_from_pdb(pdb, distance_threshold=self.params.distance)
            ff = self.featurize_pocket(pocket)
            for vector in ff.vectors:
                yield vector

    def get_ff_file(self, vector):
        res_type = get_vector_type(vector)
        res_file = "{0}.ff.gz".format(res_type)
        res_path = os.path.join(self.params.ff_dir, res_file)
        return res_path

    def get_res_ff_files(self):
        ff_dir = self.params.ff_dir
        ff_files = os.dirlist(ff_dir)
        ff_types = [ff.split('.')[0] for ff in ff_files]
        ff_paths = [os.path.join(ff_dir, ff) for ff in ff_files]
        ff_map = dict(zip(ff_types, ff_paths))
        return ff_map

    def get_allowed_ff_pairs(self):
        classes = backgrounds.ALLOWED_VECTOR_TYPE_PAIRS[self.params.allowed_pairs]
        allowed_pairs = backgrounds.make_allowed_pair_sets(classes)
        ff_types = self.get_res_ff_files()
        all_pairs = itertools.product(ff_types.items(), ff_types.items())
        allowed_map = {}
        for (typeA, pathA), (typeB, pathB) in all_pairs:
            key = backgrounds.make_vector_type_key((typeA, typeB))
            if key in allowed_pairs:
                allowed_map[key] = (pathA, pathB)  # order isn't important
        return allowed_map
        

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import (
            ArgumentParser,
            FileType,
        )
        from pocketfeature.utils.args import FileType

        if PDB_DIR in os.environ:
            pdb_dir = os.environ.get('PDB_DIR')
        else:
            pdb_dir = '.'

        if DSSP_DIR in os.environ:
            dssp_dir = os.environ.get('DSSP_DIR')
        else:
            dssp_dir = '.'

        parser = ArgumentParser(
            """Generate background files for PocketFEATURE calculations""")
        parser.add_argument('pdbs', metavar='PDBS',
                                    help='Path to a file containing PDB ids or a directory of PDB files')
        parser.add_argument('--pdb-dir', metavar='PDB_DIR', 
                                         help='Directory to look for PDBs in [default: %(default)s|PDBS]'
                                         default=pdb_dir)
        parser.add_argument('--dssp-dir', metavar='PDB_DIR', 
                                          help='Directory to look for PDBs in [default: %(default)s]'
                                          default=dssp_dir)
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
                                      default='residue_classes',
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-r', '--resume', action='store_true'
                                              default=False,
                                              help='Resume with existing files if possible [default: %(default)s]')
        parser.add_argument('-d', '--distance', metavar='CUTOFF',
                                              type=float,
                                              default=cls.LIGAND_RESIDUE_DISTANCE,
                                              help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-P', '--num-processors', metavar='PROCS',
                                                      default=1,
                                                      help='Number of processes to use [default: %(default)s]')
        parser.add_argument('--cleanup', action='store_true'
                                         default=False,
                                         help='Remove temporary FEATURE files upon completion [default: %(default)s]')
        parser.add_argument('--all-data', action='store_true'
                                          default=False,
                                          help='Write out all temporary files [default: %(default)s]')
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     default=stderr,
                                     help='Path to log errors [default: STDERR]')
        return parser


if __name__ == '__main__':
    import sys
    sys.exit(FeatureFileCompare.run_as_script())
