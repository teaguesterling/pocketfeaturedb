#!/usr/bin/env python
from __future__ import print_function

from taskbase import (
    decompress,
    Task,
    TaskFailure,
)

from feature.io import pointfile
from pocketfeature.io import (
    pdbfile,
    residuefile,
)
from pocketfeature.utils.pdb import (
    guess_pdbid_from_stream,
    list_ligands,
)
from pocketfeature.utils.args import (
    decompress,
    ProteinFileType,
)

from pocketfeature.operations.pockets import (
    focus_structure,
    pick_best_ligand,
    find_ligand_in_structure,
    find_one_of_ligand_in_structure,
    create_pocket_around_ligand,
)

from pocketfeature.defaults import (
    IGNORE_DISORDERED_RESIDUES,
    LIGAND_RESIDUE_DISTANCE,
)


class PocketExtractor(Task):
    pdbid = None
    pdb = None
    model = None
    chain = None
    ligand = None
    distance = None
    ignore_disordered = None
    output = None
    list_only = None
    print_residues = None
    print_pointfile = None

    def setup(self, params=None, **kwargs):
        params = params or self.params
        defaults = self.defaults(**self.conf)
        self.setup_task(params, defaults=defaults, **kwargs)
        self.setup_inputs(params, defaults=defaults, **kwargs)
        self.setup_params(params, defaults=defaults, **kwargs)
        self.setup_outputs(params, defaults=defaults, **kwargs)

    def load_inputs(self):
        structure = pdbfile.load(self.pdb, pdbid=self.pdbid)
        self.structure = structure

    def execute(self):
        self.run_find_structure()

        if self.list_only:
            self.run_find_ligands()
        else:
            self.run_find_ligand()
            self.run_create_pocket()

    def produce_results(self):
        if self.print_residues:
            return self.generate_output(residuefile.dump,
                                        self.pocket.residues,
                                        self.output,
                                        'Writing pointfile to {}')
        else:
            return self.generate_output(pointfile.dump,
                                        self.pocket.points,
                                        self.output,
                                        'Writing residue list to {}')

    def setup_inputs(self, params=None, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'pdbid',
            'pdb',
            'model',
            'chain',
            'ligand'
        ))

        self.pdb = decompress(self.pdb)

        if self.pdbid is None:
            pdbid, pdb = guess_pdbid_from_stream(self.pdb)
            self.pdbid = pdbid
            self.pdb = pdb

        if self.model == -1:
            self.model = None

        if self.chain == '-':
            self.chain = None

    def setup_params(self, params=None, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'distance',
            'ignore_disordered',
        ))

    def setup_outputs(self, params=None, defaults=None, **kwargs):
        self.apply_setup(params, kwargs, defaults, (
            'list_only',
            'print_residues',
            'print_pointfile'
        ))

    def run_find_structure(self):
        structure = self.structure
        focus = focus_structure(structure, model=self.model, chain=self.chain)
        self.focus = focus

    def run_find_ligands(self):
        ligands = list_ligands(self.focus)
        self.ligands = ligands

    def run_find_ligand(self):
        if not self.ligand:
            self.logger.warning("No ligand provided. Making best guess.")
            self.ligand = pick_best_ligand(self.focus)
        elif len(self.ligand) == 1:
            self.ligand = find_ligand_in_structure(self.focus, self.ligand[0])
        else:
            self.ligand = find_one_of_ligand_in_structure(self.focus, self.ligand)

        if self.ligand is None:
            raise self.failed("Could not find ligand in structure", code=TaskFailure.STATUS_INPUT_FAILURE)
        else:
            self.logger.info("Found ligand: {}".format(self.ligand))

    def run_create_pocket(self):
        pocket = create_pocket_around_ligand(self.focus, self.ligand,
                                             cutoff=self.distance,
                                             expand_disordered=not self.ignore_disordered)
        self.pocket = pocket

        self.num_residues_found = len(pocket.residues)

        if self.num_residues_found == 0:
            raise self.failed("No residues found within {0} angstroms of {1}".format(self.distance, self.ligand),
                              code=TaskFailure.STATUS_EMPTY_DATA)
        else:
            self.logger.debug("Created pocket with {:d} residues".format(self.num_residues_found))

    @classmethod
    def input_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'ligand': None,
            'pdbid': None,
            'model': 0,
            'chain': '-',
        }

    @classmethod
    def parameter_defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        return {
            'distance': LIGAND_RESIDUE_DISTANCE,
            'ignore_disordered': IGNORE_DISORDERED_RESIDUES,
        }

    @classmethod
    def defaults(cls, stdin, stdout, stderr, environ, **kwargs):
        defaults = super(PocketExtractor, cls).defaults(stdin, stdout, stderr, environ, **kwargs)
        defaults.update(cls.input_defaults(stdin, stdout, stderr, environ, **kwargs))
        defaults.update(cls.parameter_defaults(stdin, stdout, stderr, environ, **kwargs))
        defaults.update({
            'pdb': stdin,
            'print_pointfile': True,
            'print_residues': False,
            'list_only': False,
        })
        return defaults

    @classmethod
    def parser(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=task_name,
                                description="Extract a pocket from a PDB file and write a point file")
        return parser

    @classmethod
    def input_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('pdb',
                            metavar='PDB',
                            type=ProteinFileType.compressed('r'),
                            nargs='?',
                            help='Path to PDB file [default: STDIN]')
        parser.add_argument('ligand',
                            metavar='LIG',
                            type=str,
                            nargs='?',
                            help='Ligand ID to build pocket around [default: <largest>]')
        parser.add_argument('-i', '--pdbid',
                            metavar='PDBID',
                            type=str,
                            help='PDB ID to use for input structure [default: BEST GUESS]')
        parser.add_argument('-m', '--model',
                            metavar='MODEL_NUMBER',
                            type=int,
                            help='Model index to input structure (-1 for all) [default: %(default)s]')
        parser.add_argument('-c', '--chain',
                            metavar='CHAIN_ID',
                            type=str,
                            help='Chain id to input structure (- for all) [default: %(default)s]')
        return parser

    @classmethod
    def parameter_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('-d', '--distance',
                            metavar='CUTOFF',
                            type=float,
                            help='Residue active site distance threshold [default: %(default)s]')
        parser.add_argument('-I', '--ignore-disordered',
                            action='store_true',
                            help='Ignore additional coordinates for atoms [default: %(default)s]')
        return parser

    @classmethod
    def output_arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        parser.add_argument('-P', '--print-pointfile',
                            action='store_true',
                            help='Print point file (default behavior)')
        parser.add_argument('-R', '--print-residues',
                            action='store_true',
                            help='Print residue ID list instead of point file')
        parser.add_argument('-L', '--list-only',
                            action='store_true',
                            help='List residues instead of creating pocket')

    @classmethod
    def arguments(cls, parser, stdin, stdout, stderr, environ, **kwargs):
        cls.task_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.input_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.parameter_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        cls.output_arguments(parser, stdin, stdout, stderr, environ, **kwargs)
        return parser

if __name__ == '__main__':
    import sys
    sys.exit(PocketExtractor.run_as_script())
