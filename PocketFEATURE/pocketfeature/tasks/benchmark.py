#!/usr/bin/env pythoe
from __future__ import absolute_import, print_function

import itertools
import logging
import multiprocessing
import os
import shutil
from six import (
    string_types,
    StringIO,
)

from feature.io.locate_files import pdbidFromFilename
from feature.io.common import open_compressed

from pocketfeature.algorithms import GaussianStats
from pocketfeature.io import (
    matrixvaluesfile,
    backgroundfile,
)
from pocketfeature.datastructs.matrixvalues import PassThroughItems
from pocketfeature.tasks.core import (
    Task,
    ensure_all_imap_unordered_results_finish,
)
from pocketfeature import defaults
from pocketfeature.tasks.align import AlignScores
from pocketfeature.tasks.compare import Compare
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
    token = "{0}-{1}".format(pdbidA, pdbidB)
    comp_dir = os.path.join(root, token)
    os.makedirs(comp_dir)

    # Fix issue with six and PyLint
    # noinspection PyCallingNonCallable
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
        modelA=0,
        modelB=0,
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
        comparison_method=params['compare_method'],
        alignment_method=params['alignment_method'],
        scale_method=params['scale_method'],
        log_level='error',
        **job_files
    )
    key = (pdbidA, pdbidB)
    try: 
        retcode = task.run()
    except Exception as e:
        retcode = 255
    if retcode != 0:
        return key, (0, 0, 0, 0), None, None
    try:
        buf.seek(0)
        results = matrixvaluesfile.load(buf, cast=float)
        key, values = results.items()[0]
        sizes = tuple(map(int, values[:4]))
        all_scores = map(float, values[4:6])
        scores = all_scores[:1]
        scaled_scores = all_scores[1:2]
    except (ValueError, IndexError):
        return key, (0, 0, 0, 0), None, None
    for f in job_files.values():
        if hasattr(f, 'close'):
            f.close()

    scores_file = os.path.join(comp_dir, token + ".scores")
    for cutoff in cutoffs:
        cutoff_token = token + '_{0}'.format(cutoff)
        align_path = os.path.join(comp_dir, "{}.align".format(cutoff_token))
        log_path = os.path.join(comp_dir, "{}.log".format(cutoff_token))
        job_files = {
            'scores': open(scores_file),
            'log': open(log_path, 'a'),
            'output': open(align_path, 'w'),
        }

        task = AlignScores.from_params(
            cutoff=cutoff,
            method=params['alignment_method'],
            scale_method=params['scale_method'],
            score_column=1,
            **job_files
        )
        task.run()
        for f in job_files.values():
            f.close()

        with open(log_path) as f:
            log_lines = list(f)
            try:
                score = float([l.split('\t')[1] for l in log_lines if l.startswith('Raw\t')][0])
            except ValueError:
                score = float('inf')
            try:
                scaled = float([l.split('\t')[1] for l in log_lines if l.startswith('Scaled\t')][0])
            except ValueError:
                scaled = float('inf')
            scores.append(score)
            scaled_scores.append(scaled)

    return key, sizes, scores, scaled_scores
        

def _run_pf_comparison_star(args, fail=True):
    try:
        return run_pf_comparison(*args)
    except:
        if fail:
            raise
        else:
            return ('Unknown', 'Unknown'), [], None, None


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
        if isinstance(self.cutoffs, string_types):
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
                log.warning("Resuming with feature vectors from BENCH_DIR")
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

        ps, ps_r = self.positive_stats
        cs, cs_r = self.control_stats

        with open(self.params.summary_out, 'w') as f:
            print('class', 'cutoff', 'mean', 'std', 'min', 'max', file=f, sep='\t')
            print('class', 'cutoff', 'mean', 'std', 'min', 'max', sep='\t')
            for c, cutoff in enumerate(self.cutoffs):
                print('Positive', cutoff, ps.mean[c], ps.std_dev[c], ps.mins[c], ps.maxes[c], sep='\t', file=f)
                print('Control ', cutoff, cs.mean[c], cs.std_dev[c], cs.mins[c], cs.maxes[c], sep='\t', file=f)
                print('Positive', cutoff, ps.mean[c], ps.std_dev[c], ps.mins[c], ps.maxes[c], sep='\t')
                print('Control ', cutoff, cs.mean[c], cs.std_dev[c], cs.mins[c], cs.maxes[c], sep='\t')
            
            for c, cutoff in enumerate(self.cutoffs):
                print('Positive', cutoff, ps_r.mean[c], ps_r.std_dev[c], ps_r.mins[c], ps_r.maxes[c], sep='\t', file=f)
                print('Control ', cutoff, cs_r.mean[c], cs_r.std_dev[c], cs_r.mins[c], cs_r.maxes[c], sep='\t', file=f)
                print('Positive', cutoff, ps_r.mean[c], ps_r.std_dev[c], ps_r.mins[c], ps_r.maxes[c], sep='\t')
                print('Control ', cutoff, cs_r.mean[c], cs_r.std_dev[c], cs_r.mins[c], cs_r.maxes[c], sep='\t')


    def compare_pdb_pairs(self, pairs, comp_name, output, output_scaled=None, ligA=None, ligB=None):
        pairs = list(pairs)
        num_comps = len(pairs)
        comp_dir = os.path.join(self.params.bench_dir, comp_name)

        self.log.info("Starting {0} comparison of {1} pairs".format(comp_name, num_comps))
        stats = GaussianStats()
        scaled_stats = GaussianStats()
        if not os.path.exists(comp_dir):
            os.makedirs(comp_dir)

        pf_params = {
            'background': self.params.background,
            'normalization': self.params.normalization,
            'distance': self.params.distance,
            'allowed_pairs': self.params.allowed_pairs,
            'std_threshold': self.params.std_threshold,
            'ligandA': ligA,
            'ligandB': ligB,
            'pdb_dir': self.params.pdb_dir,
            'dssp_dir': self.params.dssp_dir,
            'ff_cache': self.ff_cache,
            'ptf_cache': self.ptf_cache,
            'compare_method': self.params.compare_method,
            'alignment_method': self.params.alignment_method,
            'scale_method': self.params.scale_method,
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
            # Run the first in parallel for cache stability
            first_args, all_args = all_args[0], all_args[1:]
            first_score = _run_pf_comparison_star(first_args)
            num_comps -= 1

            self.pool = multiprocessing.Pool(self.params.num_processors)
            async_results = self.pool.imap_unordered(_run_pf_comparison_star, all_args)
            # Create a wrapper to ensure we don't prematurely exit
            all_scores = ensure_all_imap_unordered_results_finish(async_results, expected=num_comps)

            # Mix back in
            all_scores = itertools.chain([first_score], all_scores)
        else:
            all_scores = itertools.imap(_run_pf_comparison_star, all_args)

        all_scores = self.record_scores(all_scores, output, output_scaled)
        for idx, (key, sizes, scores, scaled) in enumerate(all_scores, start=1):
            print("\r{0} of {1} {2} alignments computed ({3} successful, {4} failed) ({5}) ".format(
                    idx, 
                    num_comps, 
                    comp_name, 
                    self.successful_scores,
                    self.failed_scores,
                    ":".join(key)), end="", file=sys.stderr)
            stats.record(scores)
            scaled_stats.record(scaled)
        print("", file=sys.stderr)

        all_scores = list(all_scores)

        with open(output) as f:
            scores = matrixvaluesfile.load(f, value_dims=self.cutoffs)

        self.log.info("Finished {0} (Mean score: {1})".format(comp_name, stats.mean))
    
        return scores, (stats, scaled_stats)

    def compare_positives(self):
        positives = get_pdb_files(self.params.positives, pdb_dir=self.params.pdb_dir,
                                                         log=self.log)
        pairs = itertools.combinations_with_replacement(positives, 2)
        output = self.params.positives_out
        scaled = output + "-scaled"
        scores, stats = self.compare_pdb_pairs(pairs, 'positives', 
                                               output, scaled,
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
        scaled = output + "-scaled"
        scores, stats = self.compare_pdb_pairs(pairs, 'controls', 
                                               output, scaled,
                                               ligA=self.params.positive_ligands)

        return stats
        

    def record_scores(self, scores, output, scaled_output):
        if scaled_output is None:
            scaled_output = os.devnull
        with open(output, 'w') as f,\
             open(scaled_output, 'w') as g:
            for item in scores:
                if len(item) == 4:
                    key, sizes, values, scaled = item
                else:
                    key = 'Unknown', 'Unknown'
                    self.failed_scores += 1
                    self.log.debug("Failure to compare {0}".format(":".join(key)))
                    continue

                self.successful_scores += 1
                row = tuple(sizes) + tuple(values)
                scaled_row = tuple(sizes) + tuple(scaled)
                passthough = PassThroughItems([(key, row)])
                matrixvaluesfile.dump(passthough, f)
                passthough = PassThroughItems([(key, scaled_row)])
                matrixvaluesfile.dump(passthough, g)
                yield item

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
                                      choices=defaults.ALLOWED_VECTOR_TYPE_PAIRS.keys(),
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
                                              default=[float('+inf'),.1,0,-0.1,-0.15,-0.2,-0.25,-0.3],
                                              help='Alignment score thresholds [default: %(default)s]')
        parser.add_argument('-C', '--compare-method', metavar='COMPARISON',
                                              default='tversky22',
                                              help='Comparisoin method to use [default: %(default)s]')
        parser.add_argument('-A', '--alignment-method', metavar='ALIGNMENT',
                                              default='onlybest',
                                              help='Alignment method to use [default: %(default)s]')
        parser.add_argument('-S', '--scale-method', metavar='SCALING',
                                              default='none',
                                              help='Scoring scaling method to use [default: %(default)s]')
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
        parser.add_argument('--rescale-scores', action='store_true',
                                          default=False,
                                          help='EXPERIMENTAL: Rescale scores based on pocket size [default: %(default)s')
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
    sys.exit(Compare.run_as_script())
