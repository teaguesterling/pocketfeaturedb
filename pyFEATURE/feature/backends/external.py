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
from __future__ import print_function
import gzip

import sh

from six import iteritems
from six import moves

try:
    import tempfile
    from feature.io import pointfile
    CAN_USE_TEMP_POINTFILE = True
except ImportError as e:
    import warnings
    tempfile = None
    pointfile = None
    warnings.warn("Cannot use temporary pointfile with FEATURIZE: {}".format(str(e)))
    CAN_USE_TEMP_POINTFILE = False

from feature.environ import *

raw_which = sh.Command('which')

try:
    raw_featurize = str(raw_which('featurize'))
except Exception:
    raw_featurize = None

if 'FEATURE_DIR' not in os.environ and raw_featurize is not None:
    raw_featurize_root = os.path.dirname(raw_featurize)
    _check_dirs = ('', 'data', '..', '../data')
    for _dir in ('', 'data'):
        _test_dir = os.path.join(raw_featurize_root, _dir)
        if all(os.path.exists(os.path.join(_test_dir, item)) for item in FEATURE_DIR_FILES):
            os.environ['FEATURE_DIR'] = _test_dir
            break


def locate_subprocess_binary(name, expected_path, raise_error=True, 
                                                  environ=default_environ,
                                                  on_found_callback=None):
    try:
        if os.path.exists(expected_path):
            found_path = expected_path
        else:
            found_path = raw_which(name, _env=environ).stdout.strip()
        cmd = sh.Command(found_path)
        if on_found_callback is not None:
            on_found_callback(found_path)
        return cmd
    except (sh.CommandNotFound, sh.ErrorReturnCode):
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
raw_dssp = locate_subprocess_binary(DSSP_NAME, DSSP_BIN, raise_error=False)


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
raw_featurize = locate_subprocess_binary('featurize', FEATURIZE_BIN,
                                         on_found_callback=update_default_environ_from_feature_path)


def generate_dssp_file(pdb_file, dssp_file=None, environ=None, **exec_params):
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

    exec_params.update({
        '_env': environ,        # Run in the feature environment
    })

    if pdb_file.endswith('.gz'):
        with gzip.open(pdb_file) as f,\
             tempfile.NamedTemporaryFile() as t:
            for l in f:
                t.write(l)
            raw_dssp(i=t.name, o=dssp_file, **exec_params)
    else:
        raw_dssp(i=pdb_file, o=dssp_file, **exec_params)

    return dssp_file


def featurize(pdbid=None,
              shells=None,
              width=None,
              exclude=None,
              properties=None,
              search_in=None,
              working_dir=None,
              environ=None,
              with_errors=False,
              feature_dir=None,
              pdb_dir=None,
              dssp_dir=None,
              verbose=False,
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
    else:
        for key, value in iteritems(feature_environ):
            if key not in environ:
                environ[key] = value
    if feature_dir is not None:
        environ['FEATURE_DIR'] = feature_dir
    if pdb_dir is not None:
        environ['PDB_DIR'] = pdb_dir
    if dssp_dir is not None:
        environ['DSSP_DIR'] = dssp_dir
    for variable in REQUIRED_ENVIRONMENT:
        if variable not in environ:
            raise RuntimeError("Required environmental variable {} not available".format(variable))

    exec_params['_env'] = environ

    if pdbid is not None:
        exec_args = [pdbid] + list(exec_args)

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
    if verbose:
        exec_params['v'] = True

    likely_problems = any(var not in environ for var in ('PDB_DIR', 'DSSP_DIR', 'FEATURE_DIR'))

    if with_errors:
        errors = moves.StringIO()
        exec_params['_err'] = errors
        exec_params['_ok_code'] = range(255)  # Allow all errors
        results = raw_featurize(*exec_args, **exec_params)
        errors_log = errors.getvalue()
        errors.close()
        return results, errors_log
    elif likely_problems:
        errors = moves.StringIO()
        exec_params['_err'] = errors
        exec_params['_ok_code'] = range(255)  # Allow all errors
        results = raw_featurize(*exec_args, **exec_params)
        ok = results.exit_code
        if ok == 0:
            return results
        else:
            errors_log = errors.getvalue()
            raise RuntimeError(errors_log)
    else:
        if not exec_params.get('_err'):
            exec_params['_err'] = moves.StringIO()
        if verbose:
            err = exec_params.get('_err', sys.stderr)
            print(raw_featurize.bake(*exec_args, **exec_params), file=err)
        try:
            results = raw_featurize(*exec_args, **exec_params)
        except sh.ErrorReturnCode as e:
            raise RuntimeError("featurize reported a falure (see above)")
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
                     with_errors=with_errors,
                     **options)


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


def featurize_points_tempfile(points,
                              shells=None,
                              width=None,
                              exclude=None,
                              properties=None,
                              search_in=None,
                              working_dir=None,
                              environ=None,
                              with_errors=False,
                              **options):
    """ Run featurize on a given pointfile from a tempfile

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

    if not CAN_USE_TEMP_POINTFILE:
        raise NotImplementedError("Failure to import pointfile or tempfile module. Cannot featurize via file")

    with tempfile.NamedTemporaryFile() as f:
        for line in points:
            f.write(line)
        f.flush()
        result = featurize_pointfile(point_file=f.name,
                                     shells=shells,
                                     width=width,
                                     exclude=exclude,
                                     properties=properties,
                                     search_in=search_in,
                                     working_dir=working_dir,
                                     environ=environ,
                                     with_errors=with_errors,
                                     **options)
        for line in result:
            yield line 


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

