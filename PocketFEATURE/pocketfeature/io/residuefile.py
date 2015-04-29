from __future__ import print_function

from six import StringIO
from pocketfeature.utils.pdb import (
    find_residues_by_id,
    residue_id
)

DELIMITER = "/"
PDB_ID = 0


def write_residue_id(residue):
    res_id = residue_id(residue)
    return DELIMITER.join(map(str, res_id))


def read_residue_id(res_id):
    if isinstance(res_id, int):
        return res_id

    tokens = res_id.split(DELIMITER)
    if len(tokens) == 1:
        return tokens[0]
    else:
        pdb, model, chain, res, name = tokens
        return (pdb, int(model), chain, int(res), name)


def dump(residue_list, io):
    for residue in residue_list:
        res_id = write_residue_id(residue)
        print(res_id, file=io)


def loadi(io):
    for line in io:
        line = line.strip()
        tokens = map(str.strip, line.split('#'))
        if len(tokens) == 0 or len(tokens[0]) == 0:
            continue
        raw_id = tokens[0]
        res_id = read_residue_id(raw_id)
        yield res_id


def load(io):
    return list(loadi(io))


def find_in_structures(res_ids, structures, ignore_missing=False):
    grouped_by_struct = {}
    residues = {}
    for res_id in res_ids:
        pdb_id = res_id[PDB_ID]
        if pdb_id not in structures and not ignore_missing:
            raise KeyError("{0} not provided".format(pdb_id))
        grouped_by_struct.setdefault(pdb_id, []).append(res_id)
    for pdb_id, res_ids in grouped_by_struct.items():
        structure = structures[pdb_id]
        residues[pdb_id] = find_residues_by_id(structure, res_ids, full=True)
    return residues


def load_with_structures(io, *args, **options):
    options.setdefault('ignore_missing', False)
    structures = options.get('structures', {})
    for structure in args:
        pdb_id = structure.get_id()
        structures[pdb_id] = structure
    residue_ids = loadi(io)
    found_residues = find_in_structures(residue_ids, 
                                        structures, 
                                        options['ignore_missing'])
    
    return found_residues
        

def load_with_structure(io, structure, ignore_missing=False):
    pdb_id = structure.get_id()
    structures = {pdb_id: structure}
    residue_ids = loadi(io)
    found = find_in_structures(residue_ids, structures, ignore_missing)
    found.setdefault(pdb_id, [])
    return found[pdb_id]


def dumps(pointlist, **kwargs):
    buf = StringIO()
    dump(pointlist, buf, **kwargs)
    return buf.getvalue()


def loads(data, **kwargs):
    return load(str(data).splitlines(), **kwargs)

def loads_with_structure(data, structure, **kwargs):
    return load_with_structure(str(data).splitlines(), structure, **kwargs)


