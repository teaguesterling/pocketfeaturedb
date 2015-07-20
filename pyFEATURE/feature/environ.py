from __future__ import absolute_import

import os
import sys


SCRATCH_DIR = os.environ.get('TMP_DIR', '/tmp')

REQUIRED_ENVIRONMENT = ('FEATURE_DIR',)
FEATURE_DIR_FILES = ('residue_templates.dat',
                     'amberM2_params.data')


FEATURE_ROOT = os.environ.get('FEATURE_ROOT', '/usr/local/feature')

if not os.path.exists(FEATURE_ROOT):
    FEATURE_ROOT = os.path.join(sys.prefix, 'local', 'feature')

if not os.path.exists(FEATURE_ROOT):
    FEATURE_ROOT = os.path.join(sys.prefix, 'opt', 'feature')

FEATURE_DIR = os.environ.get('FEATURE_DIR', os.path.join(FEATURE_ROOT, 'data'))
FEATURE_BIN = os.environ.get('FEATURE_BIN', os.path.join(FEATURE_ROOT, 'bin'))
FEATURE_TOOLS_BIN = os.environ.get('FEATURE_TOOLS_BIN', FEATURE_BIN)

DSSP_NAME = 'dssp-2.0.4-linux-amd64'
DSSP_BIN = os.environ.get('DSSP', os.path.join(FEATURE_TOOLS_BIN, DSSP_NAME))
FEATURIZE_BIN = os.environ.get('FEATURIZE', os.path.join(FEATURE_BIN, 'featurize'))

PROTEIN_DB_DIR = os.environ.get('PROTEIN_DB_DIR', os.path.join(os.getcwd()))
DEFAULT_PDB_DIR = os.environ.get('PDB_DIR', os.path.join(PROTEIN_DB_DIR, 'pdb'))
DEFAULT_DSSP_DIR = os.environ.get('DSSP_DIR', os.path.join(PROTEIN_DB_DIR, 'dssp'))

ORIGINAL_PATH = os.environ.get('PATH')
AUGMENTED_PATH = os.pathsep.join((FEATURE_BIN,
                                  FEATURE_TOOLS_BIN,
                                  ORIGINAL_PATH))

""":
    A modified environment within which all FEATURE scripts should be run.
    This sets environmental variables expected by the FEATURE binaries
    as well as updating the path to allow locating of the FEAUTRE binaries
"""
feature_environ = {
    # Add external script path to environment PATH so external scripts
    # can find 'featurize'
    'PATH': AUGMENTED_PATH,

    # Where to find FEATURE parameter files
    'FEATURE_DIR': FEATURE_DIR,

    # These two are needed for FEATURE 1.9 as it does not have a CLI argument
    # for a search path
    'PDB_DIR': DEFAULT_PDB_DIR,    # Default PDB Dir (To Override)
    'DSSP_DIR': DEFAULT_DSSP_DIR,  # Default DSSP Dir (To Override)
}
default_environ = os.environ.copy()
default_environ.update(feature_environ)

def update_default_environ_from_feature_path(found_path):
    global FEATURE_DIR
    if not os.path.exists(default_environ['FEATURE_DIR']):

        feature_dir_file = 'amberM2_params.dat'
        feature_dir_checks = ('', '../', '../data')
        found_base = os.path.dirname(found_path)
        for check_dir in feature_dir_checks:
            feature_dir = os.path.join(found_base, check_dir)
            feature_dir_check = os.path.join(feature_dir, feature_dir_file)
            if os.path.exists(feature_dir_check):
                feature_dir_path = os.path.abspath(feature_dir)

                default_environ['FEATURE_DIR'] = feature_dir_path
                feature_environ['FEATURE_DIR'] = feature_dir_path
                FEATURE_DIR = feature_dir_path
                return
