#!/usr/bin/env pythoe
from __future__ import print_function

from cStringIO import StringIO
import gzip
import itertools
import logging
import multiprocessing
import operator
import os
import shutil
import sys
import time
import random

from feature.io.locate_files import pdbidFromFilename
from feature.io.common import open_compressed

from pocketfeature.algorithms import GaussianStats
from pocketfeature.io import (
    matrixvaluesfile,
    backgrounds,
)
from pocketfeature.io.matrixvaluesfile import (
    MatrixValues,
    PassThroughItems,
)
from pocketfeature.tasks.core import (
    Task,
    ensure_all_imap_unordered_results_finish,
)
from pocketfeature.tasks.align import AlignScores
from pocketfeature.tasks.build_background import get_pdb_list
from pocketfeature.tasks.full_comparison import ComparePockets
from pocketfeature.utils.args import LOG_LEVELS


def get_pdb_files(source, pdb_dir=None, log=logging):
    pdb_info = get_pdb_list(source, pdb_dir=pdb_dir, log=log)
    pdbs = [path for (pdbid, path), lig in pdb_info]
    return pdbs


def run_pf_comparison(root, pdbA, pdbB, cutoffs, params):
    top_cutoff, cutoffs = cutoffs[0], cutoffs[1:]
    pdbidA = pdbidFromFilename(pdbA)
    pdbidB = pdbidFromFilename(pdbB)
    key = (pdbidA, pdbidB)
    token = "{0}-{1}".format(pdbidA, pdbidB)
    comp_dir = os.path.join(root, token)
    os.makedirs(comp_dir)

    buf = StringIO()
    job_files = {
        'pdbA': open_compressed(pdbA),
        'pdbB': open_compressed(pdbB),

        'background': open(params['background']),
        'normalization': open(params['normalization']),

        'ptfA': open(os.path.join(comp_dir, pdbidA + ".ptf"), 'w'),
        'ptfB': open(os.path.join(comp_dir, pdbidB + ".ptf"), 'w'),
        'ffA': open(os.path.join(comp_dir, pdbidA + ".ff"), 'w'),
        'ffB': open(os.path.join(comp_dir, pdbidB + ".ff"), 'w'),

        'raw_scores': open(os.path.join(comp_dir, token + ".scores"), 'w'),
        'alignment': open(os.path.join(comp_dir, token + "-{0}.align".format(top_cutoff)), 'w'),

        'pymolA': open(os.path.join(comp_dir, pdbidA + ".py"), 'w'),
        'pymolB': open(os.path.join(comp_dir, pdbidB + ".py"), 'w'),

        'log': open(os.path.join(comp_dir, token + ".log"), 'w'),
        'output': buf,

        'ptf_cache': params.get('ptf_cache'),
        'ff_cache': params.get('ff_cache'),
        
    }
    if params.get('pdb_dir'):
        job_files['pdb_dir'] = params['pdb_dir']
    if params.get('dssp_dir'):
        job_files['dssp_dir'] = params['dssp_dir']

    task = ComparePockets.from_params(
        modelA=None,
        modelB=None,
        chainA=None,
        chainB=None,
        ligandA=params['ligandA'],  # Extract positive ligands if specified
        ligandB=params['ligandB'], 
        cutoff=top_cutoff,
        allowed_pairs=params['allowed_pairs'],
        std_threshold=params['std_threshold'],
        distance=params['distance'],
        check_cached_first=params.get('ff_cache') is not None,
        link_cached=params.get('ff_cache') is not None,
        log_level='error',
        **job_files
    )
    if task.run() != 0:
        return key, None

    buf.seek(0)
    results = matrixvaluesfile.load(buf, cast=float)
    scores = results.values()
    for f in job_files.values():
        if hasattr(f, 'close'):
            f.close()

    for cutoff in cutoffs:
        align_path = os.path.join(comp_dir, token + '_{0}.align'.format(cutoff))
        job_files = {
            'scores': open(os.path.join(comp_dir, token + ".scores")),
            'log': open(os.path.join(comp_dir, token + ".log"), 'a'),
            'output': open(align_path, 'w'),
        }

        task = AlignScores.from_params(
            cutoff=cutoff,
            method=params['alignment'],
            score_column=1,
            **job_files
        )
        task.run()
        for f in job_files.values():
            f.close()

        with open(align_path) as f:
            score = sum(matrixvaluesfile.load(f, cast=float).values())
            scores.append(score)

    return key, scores
        

def _run_pf_comparison_star(args):
    return run_pf_comparison(*args)


class BenchmarkPocketFeatureBackground(Task):
    BACKGROUND_FF_DEFAULT = 'background.ff'
    BACKGROUND_COEFF_DEFAULT = 'background.coeffs'
    TEMP_BENCH_DIR_DEFAULT = os.path.join(os.getcwd(), 'bench')
    TEMP_FF_DIR_DEFAULT = os.path.join(os.getcwd(), 'ff')
    POS_OUT_DEFAULT = 'positives.scores'
    CONT_OUT_DEFAULT = 'control.scores'
    LIGAND_RESIDUE_DISTANCE = 6.0
    SUM_OUT_DEFAULT = 'bench.summary'

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pf_bench')
        log.setLevel(LOG_LEVELS.get(params.log_level, 'debug'))
        self.log = log

        self._num_positives = 0
        self._num_negatives = 0

        self.cutoffs = self.params.cutoffs
        if isinstance(self.cutoffs, basestring):
            self.cutoffs = sorted(map(float, self.cutoffs.split(',')), reverse=True)



        cache_dir = os.path.join(params.bench_dir, 'cache')
        if params.ff_cache:
            self.ff_cache = params.ff_cache
        else:
            self.ff_cache = os.path.join(cache_dir, '{signature}.ff.gz')
        if params.ptf_cache:
            self.ptf_cache = params.ptf_cache
        else:
            self.ptf_cache = os.path.join(cache_dir, '{pdbid}.ptf.gz')

        log.info("PDB_DIR is {0}".format(params.pdb_dir))
        log.info("DSSP_DIR is {0}".format(params.dssp_dir))
        log.info("temporary BENCH_DIR is {0}".format(params.bench_dir))
    
        log.info("FF_CACHE is {0}".format(self.ff_cache))
        log.info("PTF_CACHE is {0}".format(self.ptf_cache))

        if os.path.exists(params.bench_dir):
            if params.resume:
                log.waringn("Resuming with feature vectors from BENCH_DIR")
            else:
                log.warning("BENCH_DIR is not empty and NOT resuming. Erasing benchmark files")
                shutil.rmtree(params.bench_dir)
        else:
            if params.resume:
                log.error("Cannot resume without populated BENCH_DIR")
                sys.exit(-1)
            else:
                log.debug("Creating directory {0}".format(params.bench_dir))
                os.makedirs(params.bench_dir)
        if not os.path.exists(cache_dir):
	        os.makedirs(cache_dir)

                
        self.positive_stats = self.compare_positives()
        self.control_stats = self.compare_controls()

        ps = self.positive_stats
        cs = self.control_stats

        with open(self.params.summary_out, 'w') as f:
            print('class', 'cutoff', 'mean', 'std', 'min', 'max', file=f, sep='\t')
            print('class', 'cutoff', 'mean', 'std', 'min', 'max', sep='\t')
            for c, cutoff in enumerate(self.cutoffs):
                print('Positive', cutoff, ps.mean[c], ps.std_dev[c], ps.mins[c], ps.maxes[c], sep='\t', file=f)
                print('Control', cutoff, cs.mean[c], cs.std_dev[c], cs.mins[c], cs.maxes[c], sep='\t', file=f)
                print('Positive', cutoff, ps.mean[c], ps.std_dev[c], ps.mins[c], ps.maxes[c], sep='\t')
                print('Control', cutoff, cs.mean[c], cs.std_dev[c], cs.mins[c], cs.maxes[c], sep='\t')
            


    def compare_pdb_pairs(self, pairs, comp_name, output, ligA=None, ligB=None):
        pairs = list(pairs)
        num_comps = len(pairs)
        comp_dir = os.path.join(self.params.bench_dir, comp_name)

        self.log.info("Starting {0} comparison of {1} pairs".format(comp_name, num_comps))
        stats = GaussianStats()
        os.makedirs(comp_dir)

        pf_params = {
            'background': self.params.background,
            'normalization': self.params.normalization,
            'distance': self.params.distance,
            'allowed_pairs': self.params.allowed_pairs,
            'std_threshold': self.params.std_threshold,
            'ligandA': ligA,
            'ligandB': ligB,
            'alignment': self.params.alignment_method,
            'pdb_dir': self.params.pdb_dir,
            'dssp_dir': self.params.dssp_dir,
            'ff_cache': self.ff_cache,
            'ptf_cache': self.ptf_cache,
        }
        self.failed_scores = 0
        self.successful_scores = 0
        
        all_args = [(comp_dir, 
                     pdbA, 
                     pdbB, 
                     self.cutoffs, 
                     pf_params)
                    for pdbA, pdbB in pairs]

        if self.params.num_processors is not None and self.params.num_processors > 1:
            self.pool = multiprocessing.Pool(self.params.num_processors)
            async_results = self.pool.imap_unordered(_run_pf_comparison_star, all_args)
            # Create a wrapper to ensure we don't prematurely exit
            all_scores = ensure_all_imap_unordered_results_finish(async_results, expected=num_comps)
        else:
            all_scores = itertools.imap(_run_pf_comparison_star, all_args)

        all_scores = self.record_scores(all_scores, output)

        for idx, (key, score) in enumerate(all_scores, start=1):
            print("\r{0} of {1} {2} alignments computed ({3} successful, {4} failed) ({5}) ".format(
                    idx, 
                    num_comps, 
                    comp_name, 
                    self.successful_scores,
                    self.failed_scores,
                    ":".join(key)), end="", file=sys.stderr)
            stats.record(score)
        print("", file=sys.stderr)

        all_scores = list(all_scores)

        with open(output) as f:
            scores = matrixvaluesfile.load(f, value_dims=self.cutoffs)

        self.log.info("Finished {0} (Mean score: {1})".format(comp_name, stats.mean))
    
        return scores, stats

    def compare_positives(self):
        positives = get_pdb_files(self.params.positives, pdb_dir=self.params.pdb_dir,
                                                         log=self.log)
#        pairs = itertools.combinations(positives, 2)
        pairs = itertools.combinations_with_replacement(positives, 2)
        output = self.params.positives_out
        scores, stats = self.compare_pdb_pairs(pairs, 'positives', output,
                                               ligA=self.params.positive_ligands,
                                               ligB=self.params.positive_ligands)

        return stats
    
    def compare_controls(self):
        positives = get_pdb_files(self.params.positives, pdb_dir=self.params.pdb_dir,
                                                         log=self.log)
        controls = get_pdb_files(self.params.controls, pdb_dir=self.params.pdb_dir,
                                                       log=self.log)
        pairs = itertools.product(positives, controls)
        output = self.params.controls_out
        scores, stats = self.compare_pdb_pairs(pairs, 'controls', output,
                                               ligA=self.params.positive_ligands)

        return stats
        

    def record_scores(self, scores, output):
        with open(output, 'w') as f:
            for item in scores:
                key, values = item
                if values is None:
                    self.failed_scores += 1
                    self.log.debug("Failure to compare {0}".format(":".join(key)))
                else:
                    self.successful_scores += 1
                    passthough = PassThroughItems([item])
                    matrixvaluesfile.dump(passthough, f)
                    yield item
            

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

        parser = ArgumentParser(
            """Benchmark a PocketFEATURE background""")
        parser.add_argument('positives', metavar='POSITIVE',
                                          help='Path to a file containing PDB ids to treat as positives')
        parser.add_argument('controls', metavar='CONTROL',
                                        help='Path to a file containing PDB ids to treat as negatives')
        parser.add_argument('--pdb-dir', metavar='PDB_DIR', 
                                         help='Directory to look for PDBs in [default: %(default)s|PDBS]',
                                         default=pdb_dir)
        parser.add_argument('--dssp-dir', metavar='DSSP_DIR', 
                                         help='Directory to look for PDBs in [default: %(default)s|PDBS]',
                                         default=dssp_dir)
        parser.add_argument('-b', '--background', metavar='FEATURESTATS',
                                                  default=cls.BACKGROUND_FF_DEFAULT,
                                                  help='FEATURE file containing standard devations of background [default: %(default)s]')
        parser.add_argument('-n', '--normalization', metavar='COEFFICIENTS',
                                      default=cls.BACKGROUND_COEFF_DEFAULT,
                                      help='Map of normalization coefficients for residue type pairs [default: %(default)s]')
        parser.add_argument('-B', '--bench-dir', metavar='BENCH_DIR',
                                                 default=cls.TEMP_BENCH_DIR_DEFAULT,
                                                 help='Directory to store benchmark files [default: %(default)s]')
        parser.add_argument('-p', '--allowed-pairs', metavar='PAIR_SET_NAME',
                                      choices=backgrounds.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
                                      default='classes',
                                      help='Alignment method to use (one of: %(choices)s) [default: %(default)s]')
        parser.add_argument('-t', '--std-threshold', metavar='NSTD',
                                     type=float,
                                     default=1.0,
                                     help="Number of standard deviations between to features to allow as 'similar'")
        parser.add_argument('-L', '--positive-ligands', metavar='LIGANDS',
                                                        default=None,
                                                        help='Comma-separated list of ligands to extract from positives')
        parser.add_argument('-d', '--distance', metavar='CUTOFF',
                                              type=float,
                                              default=cls.LIGAND_RESIDUE_DISTANCE,
                                              help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-c', '--cutoffs', metavar='CUTOFFS',
                                              default=[.1, .1, 0, -0.1, -0.15, -0.2, -0.25, -0.3],
                                              help='Alignment score thresholds [default: %(default)s]')
        parser.add_argument('-A', '--alignment-method', metavar='ALIGNMENT',
                                              default='greedy',
                                              help='Alignment method to use [default: %(default)s]')
        parser.add_argument('-o', '--positives-out', metavar='POSITIVE_OUT',
                                                     default=cls.POS_OUT_DEFAULT,
                                                     help='Positive out scores [default: %(default)s]')
        parser.add_argument('-O', '--controls-out', metavar='CONTROL_OUT',
                                                    default=cls.CONT_OUT_DEFAULT,
                                                    help='Controls out scores [default: %(default)s]')
        parser.add_argument('-s', '--summary-out', metavar='SUMMARY_OUT',
                                                   default=cls.SUM_OUT_DEFAULT,
                                                   help='Score summary out [default: %(default)s]')
        parser.add_argument('-r', '--resume', action='store_true',
                                              default=False,
                                              help='Resume with existing files if possible [default: %(default)s]')
        parser.add_argument('--ff-cache', metavar='FF_CACHE_DIR', 
                                          help='Directory to cache FEATURE vectors [default: BENCH_DIR/cache]',
                                          default=None)
        parser.add_argument('--ptf-cache', metavar='PTF_CACHE_DIR', 
                                           help='Directory to cache Point files [default: BENCH_DIR/cache]',
                                           default=None)
        parser.add_argument('-P', '--num-processors', metavar='PROCS',
                                                      default=1,
                                                      type=int,
                                                      help='Number of processes to use [default: %(default)s]')
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
