#!/usr/bin/env python
"""
    This is a series of wrappers around external perl scripts. This is not
    intended to be the final incarnation of this module, but instead to be
    a single location to capture environmental dependencies and calling
    conventions while providing a single, simple interface to python.

    This API is still very file-dependent and not well tailored to a job-based
    work flow. Future versions of this script will depend on a unified set
    of data structures for passing/returning results.
"""

from cStringIO import StringIO
import os
import sys

import sh

SCRATCH_DIR = '/tmp'

REQUIRED_ENVIRONMENT = ('FEATURE_DIR', 'PDB_DIR', 'DSSP_DIR')

FEATURE_ROOT = os.environ.get('FEATURE_ROOT', '/usr/local/feature')

# Using bundled FEATURE in case nothing was found
#if not os.path.exists(FEATURE_ROOT):
FEATURE_ROOT = os.path.join(sys.prefix, 'opt', 'feature')

FEATURE_DIR = os.environ.get('FEATURE_DIR', os.path.join(FEATURE_ROOT, 'data'))
FEATURE_BIN = os.environ.get('FEATURE_BIN', os.path.join(FEATURE_ROOT, 'bin'))
FEATURE_TOOLS_BIN = os.environ.get('FEATURE_TOOLS_BIN', FEATURE_BIN)

DSSP_NAME = 'dssp-2.0.4-linux-amd64'
DSSP_BIN = os.environ.get('DSSP', os.path.join(FEATURE_TOOLS_BIN, DSSP_NAME))
FEATURIZE_BIN = os.environ.get('FEATURIZE', os.path.join(FEATURE_BIN, 'featurize'))

FEATURE_DATA_DIR = os.environ.get('FEATURE_DATA_DIR', FEATURE_DIR)
PROTEIN_DB_DIR = os.environ.get('PROTEIN_DB_DIR', os.path.join(os.getcwd(), 'db'))
DEFAULT_PDB_DIR = os.environ.get('PDB_DIR', os.path.join(PROTEIN_DB_DIR, 'pdb'))
DEFAULT_DSSP_DIR = os.environ.get('DSSP_DIR', os.path.join(PROTEIN_DB_DIR, 'dssp'))

""":
    A modified environment within which all FEATURE scripts should be run.
    This sets environmental variables expected by the FEATURE binaries
    as well as updating the path to allow locating of the FEAUTRE binaries
"""
default_environ = os.environ.copy()
default_environ.update({
    # Add external script path to environment PATH so external scripts
    # can find 'featurize'
    'PATH': os.pathsep.join((FEATURE_BIN, default_environ.get("PATH"))),

    # Where to find FEATURE parameter files
    'FEATURE_DIR': FEATURE_DATA_DIR,

    # These two are needed for FEATURE 1.9 as it does not have a CLI argument
    # for a search path
    'PDB_DIR': DEFAULT_PDB_DIR,    # Default PDB Dir (To Override)
    'DSSP_DIR': DEFAULT_DSSP_DIR,  # Default DSSP Dir (To Override)
})


def locate_subprocess_binary(name, expected_path, raise_error=True):
    try:
        if os.path.exists(expected_path):
            return sh.Command(expected_path)
        else:
            return sh.Command(name)
    except sh.CommandNotFound:
        def error(*args, **kwargs):
            raise NotImplementedError("{0} not available in {1}".format(
                name, os.environ.get('PATH', [])))
        if raise_error:
            error()
        else:
            return error


""":
    DSSP generator from http://swift.cmbi.ru.nl/gv/dssp/

    Args:
      -i INFILE: PDB
      -o OUTFILE: DSSP
    Ex: -i /db/pdb/1qhx.pdb -o /db/dssp/1qrx.dssp
"""
raw_dssp = locate_subprocess_binary(DSSP_NAME, DSSP_BIN)


""":
  Internal wrapper for running featurize

    Must exclude .ent or other filename extension in PDBID

    Options:
        -v  Increase verbosity
        -n NUMSHELLS [Default: 6]
            Set number of shells to NUMSHELLS
        -w SHELLWIDTH [Default: 1.25]
            Set thickness of each shell to SHELLWIDTH Angstroms
        -x EXCLUDERESIDUES [Default: HETATM]
            Set residues to exclude to comma separated list of
            EXCLUDERESIDUES
        -f PDBIDFILE
            Read PDBIDs from PDBIDFILE
        -P POINTFILE
            Read point list from POINTFILE
        -H  Print header
"""
raw_featurize = locate_subprocess_binary('featurize', FEATURIZE_BIN)


def generate_dssp_file(pdb_file, dssp_file=None,
                        working_dir=SCRATCH_DIR,
                        environ=None):
    """
        pdb_file -> dssp_file (in working_dir if dssp_file is not provided)

        Generates a DSSP file from a PDB using the external DSSP binary

        Parameters:
            pdb_file: Path to a source PDB file
            dssp_file: Path to destination DSSP file (optional)
        Optional Parameters:
            working_dir: Directory within which to run DSSP
                         and parent directory if dssp_file is not provided

        Returns: Path to generated DSSP file
    """

    if environ is None:
        environ = default_environ

    if dssp_file is None:
        pdb_name, _ = os.path.splitext(os.path.basename(pdb_file))
        dssp_file = "{0}.dssp".format(pdb_name)

    exec_params = {
        '_env': environ,        # Run in the feature environment
        '_cwd': working_dir,    # Run in the supplied working directory
    }

    raw_dssp(i=pdb_file, o=dssp_file, **exec_params)

    return os.path.join(working_dir, dssp_file)


def featurize(shells=None,
              width=None,
              exclude=None,
              properties=None,
              search_in=None,
              working_dir=None,
              environ=None,
              with_errors=False,
              *exec_args,
              **exec_params):
    """ A base function for running featurize

        Optional Parameters:
            shells:      Number of shells to featurize [Inmplicit: 6]
            width:       Shell width to for each shell [Inmplicit: 1.5]
            exclude:     Residues to exclude [Implicit: [HETATM]]
            properties:  Properties file to use
            search:      Directory to search first for PDBs/DSSPs
            working_dir: Directory to run featurize in

        Returns: File-like object of FEATURIZE results
    """

    if environ is None:
        environ = default_environ
    
    for variable in REQUIRED_ENVIRONMENT:
        if variable not in environ or not os.path.exists(environ.get(variable)):
            raise RuntimeError("Required environmental variable {} not available".format(variable))

    exec_params['_env'] = environ

    if shells is not None:
        exec_params['n'] = shells
    if width is not None:
        exec_params['w'] = width
    if exclude is not None:
        exec_params['x'] = ','.join(exclude)
    if properties is not None:
        exec_params['l'] = properties
    if search_in is not None:
        exec_params['s'] = search_in
    if working_dir is not None:
        exec_params['_cwd'] = working_dir

    likely_problems = any(var not in environ for var in ('PDB_DIR', 'DSSP_DIR', 'FEATURE_DIR'))

    if with_errors:
        errors = StringIO()
        exec_params['_err'] = errors
        exec_params['_ok_code'] = range(255)  # Allow all errors
        results = raw_featurize(*exec_args, **exec_params)
        errors_log = errors.getvalue()
        errors.close()
        return results, errors_log
    elif likely_problems:
        errors = StringIO()
        exec_params['_err'] = errors
        exec_params['_ok_code'] = range(255)  # Allow all errors
        try:
            results = raw_featurize(*exec_args, **exec_params)
            ok = results.exit_code
        except sh.ErrorReturnCode:
            errors_log = errors.getvalue()
            raise RuntimeError(errors_log)
        else:
            return results
    else:
        if '_err' not in exec_params:
            exec_params['_err'] = os.devnull
        results = raw_featurize(*exec_args, **exec_params)
        return results


def featurize_pointfile(point_file=None,
                        shells=None,
                        width=None,
                        exclude=None,
                        properties=None,
                        search_in=None,
                        working_dir=None,
                        environ=None,
                        with_errors=False,
                        **options):
    """ Run featurize on a given pointfile

        Runs featurize from a pointfile using external binaries

        Parameters:
            point_file: pointfile to featurize
        Optional Parameters:
            shells:      Number of shells to featurize [Inmplicit: 6]
            width:       Shell width to for each shell [Inmplicit: 1.5]
            exclude:     Residues to exclude [Implicit: [HETATM]]
            properties:  Properties file to use
            search:      Directory to search first for PDBs/DSSPs
            working_dir: Directory to run featurize in

        Returns: File-like object of FEATURIZE results
    """

    return featurize(P=point_file,
                     shells=shells,
                     width=width,
                     exclude=exclude,
                     properties=properties,
                     search_in=search_in,
                     working_dir=working_dir,
                     environ=environ,
                     with_errors=with_errors)


def featurize_points(points,
                     shells=None,
                     width=None,
                     exclude=None,
                     properties=None,
                     search_in=None,
                     working_dir=None,
                     environ=None,
                     with_errors=False,
                     **options):
    """ Run featurize on a given pointfile from standard in

        Runs featurize from a pointfile using external binaries

        Parameters:
            point_file: pointfile stream to featurize
        Optional Parameters:
            shells:      Number of shells to featurize [Inmplicit: 6]
            width:       Shell width to for each shell [Inmplicit: 1.5]
            exclude:     Residues to exclude [Implicit: [HETATM]]
            properties:  Properties file to use
            search:      Directory to search first for PDBs/DSSPs
            working_dir: Directory to run featurize in

        Returns: File-like object of FEATURIZE results
    """

    return featurize(P='-',
                     shells=shells,
                     width=width,
                     exclude=exclude,
                     properties=properties,
                     search_in=search_in,
                     working_dir=working_dir,
                     environ=environ,
                     with_errors=with_errors,
                     _in=points,
                     **options)


def featurize_pdb(pdb,
                  shells=None,
                  width=None,
                  exclude=None,
                  properties=None,
                  search_in=None,
                  working_dir=None,
                  environ=None,
                  with_errors=False):
    """ Run featurize on a given PDB

        Runs featurize for a PDB using external binaries

        Parameters:
            pdb: PDB ID to featurize
        Optional Parameters:
            shells:      Number of shells to featurize [Inmplicit: 6]
            width:       Shell width to for each shell [Inmplicit: 1.5]
            exclude:     Residues to exclude [Implicit: [HETATM]]
            properties:  Properties file to use
            search:      Directory to search first for PDBs/DSSPs
            working_dir: Directory to run featurize in

        Returns: File-like object of FEATURIZE results
    """

    return featurize(pdb,
                     shells=shells,
                     width=width,
                     exclude=exclude,
                     properties=properties,
                     search_in=search_in,
                     working_dir=working_dir,
                     environ=environ,
                     with_errors=with_errors)

