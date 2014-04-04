
#! /usr/bin/env python

# PDB utilities
# Shamelessly taken from FEATURE tools

import os
import re

_PDB_DIR = os.environ.get('PDB_DIR','').split(os.pathsep)
_DSSP_DIR = os.environ.get('DSSP_DIR','').split(os.pathsep)


def pdbidFromFilename(filename):
    root,ext = os.path.splitext(os.path.basename(filename))
    m = re.search(r'\d\w{3}',root)
    if m:
        return m.group()
    return root


def find_pdb_file(filename, pdbdirList=None):
    # first check if pdbid is really a file
    if os.path.exists(filename):
        return filename

    # extract pdbid from pdbid
    if pdbdirList is None:
        pdbdirList = _PDB_DIR
    if type(pdbdirList) == str:
        pdbdirList = pdbdirList.split(os.pathsep)
    pdbid = pdbidFromFilename(filename)
    pdbidl = pdbid.lower()
    branch = pdbidl[1:3]

    # generate filename variants
    basenames = [x%vars() for x in ( "%(filename)s", "%(pdbid)s", "%(pdbidl)s", "pdb%(pdbidl)s" )]
    basenames = list(set(basenames))
    extensions = ( "", ".pdb", ".ent", ".FULL" )
    compressions = ( "", ".gz", ".Z" )

    # generate subdirectory locations
    subdirs = []
    for pdbdir in pdbdirList:
        innerSubdirs = [x%vars() for x in (
            "",
            "%(branch)s",
            "%(pdbdir)s",
            os.path.join("%(pdbdir)s","%(branch)s"),
            os.path.join("%(pdbdir)s","divided","%(branch)s"),
            os.path.join("%(pdbdir)s","data","structures","divided","pdb","%(branch)s")
        )]
        subdirs.extend(innerSubdirs)
    subdirs = list(set(subdirs))

    # search tree
    for subdir in subdirs:
        for cmp in compressions:
            for base in basenames:
                for ext in extensions:
                    filename = os.path.join(subdir,"%(base)s%(ext)s%(cmp)s" % vars())
                    if os.path.exists(filename):
                        return filename

    raise ValueError("Could not find PDB file: {}".format(filename))


def find_dssp_file(filename, dsspdirList=None):
    # first check if pdbid is really a file
    if os.path.exists(filename):
        return filename

    # extract pdbid from pdbid
    if dsspdirList is None:
        dsspdirList = _DSSP_DIR
    if isinstance(dsspdirList, str):
        dsspdirList = dsspdirList.split(os.pathsep)

    pdbid = pdbidFromFilename(filename)
    pdbidl = pdbid.lower()
    branch = pdbidl[1:3]

    # generate filename variants
    basenames = [x%vars() for x in ( "%(filename)s", "%(pdbid)s", "%(pdbidl)s", "pdb%(pdbidl)s" )]
    basenames = list(set(basenames))
    extensions = ( "", ".dssp", ".DSSP" )
    compressions = ( "", ".gz", ".Z" )

    # generate subdirectory locations
    subdirs = []
    for dsspdir in dsspdirList:
        innerSubdirs = [x%vars() for x in (
            "",
            "%(branch)s",
            "%(dsspdir)s",
            os.path.join("%(dsspdir)s","%(branch)s"),
            os.path.join("%(dsspdir)s","divided","%(branch)s"),
            os.path.join("%(dsspdir)s","data","structures","divided","pdb","%(branch)s")
        )]
        subdirs.extend(innerSubdirs)
    subdirs = list(set(subdirs))

    # search tree
    for subdir in subdirs:
        for cmp in compressions:
            for base in basenames:
                for ext in extensions:
                    filename = os.path.join(subdir,"%(base)s%(ext)s%(cmp)s" % vars())
                    if os.path.exists(filename):
                        return filename

    raise ValueError("Could not find DSSP file: {}".format(filename))
