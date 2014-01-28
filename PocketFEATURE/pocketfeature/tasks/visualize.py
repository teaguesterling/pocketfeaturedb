#!/usr/bin/env python
from __future__ import print_function

import logging
import os
import random


from feature.io import pointfile
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io import residuefile

from pocketfeature.tasks.core import Task

def create_command(pdb, points, radii, colors):
    header = """
    from pymol.cgo import *
    from pymol import cmd
    pocket = ["""
    lines = []
    for point, radius, color in zip(points, radii, colors):
        lines.append("    COLOR, {0:.3f}, {1:.3f}, {2:.3f},".format(*color))
        lines.append("    SPHERE, {0:.3f}, {1:.3f}, {2:.3f}, {3:.3f},".format(point.x, 
                                                            point.y, 
                                                            point.z, 
                                                            radius))
    footer = """
    ]
    
    cmd.load({0})
    cmd.load_cgo(pocket, 'pocket')
    """.format(repr(pdb))

    return header + "\n" + "\n".join(lines) + footer


def get_point_name(point):
    return point.comment.split()[0]


class VisAlign(Task):

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(logging.DEBUG)

        pointsA = pointfile.load(params.pointsA)
        pointsB = pointfile.load(params.pointsB)
        alignment = matrixvaluesfile.load(params.alignment, cast=float)
        pointMapA = {get_point_name(p): p for p in pointsA}
        pointMapB = {get_point_name(p): p for p in pointsB}

        scores = alignment.values()
        minScore, maxScore = min(scores), max(scores)
        radii = [(minScore+score)/maxScore for score in scores]
        colors = [(random.random(),
                   random.random(),
                   random.random()) for _ in scores]
        
        if params.pdbA is None:
            pdbA = "{0}.pdb".format(pointsA[0].pdbid)
        else:
            pdbA = params.pdbA
        if params.pdbB is None:
            pdbB = "{0}.pdb".format(pointsB[0].pdbid)
        else:
            pdbB = params.pdbB

        print(create_command(pdbA, pointsA, radii, colors), file=params.outputA)
        print(create_command(pdbB, pointsB, radii, colors), file=params.outputB)


        return 0

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import (
            decompress,
            FileType,
        )
        parser = ArgumentParser("Identify and extract pockets around ligands in a PDB file")
        parser.add_argument('pointsA', metavar='POINTS1',
                                       type=FileType.compressed('r'),
                                       help='Path to FEATURE point file')
        parser.add_argument('pointsB', metavar='POINTS2',
                                       type=FileType.compressed('r'),
                                       help='Path to FEATURE point file')
        parser.add_argument('alignment', metavar='ALIGNMENT',
                                      type=FileType.compressed('r'),
                                      help='Path to PocketFEATURE alignment')
        parser.add_argument('-A', '--outputA', metavar='CMD1',
                                              type=FileType('w'),
                                              help='Path to first command output file')
        parser.add_argument('-B', '--outputB', metavar='CMD2',
                                              type=FileType('w'),
                                              help='Path to second command output file')
        parser.add_argument('pdbA', metavar='PDB1', 
                                    help='Path to first PDB file',
                                    nargs='?',
                                    default=None)
        parser.add_argument('pdbB', metavar='PDB2', 
                                    help='Path to second PDB file',
                                    nargs='?',
                                    default=None)
        parser.add_argument('--log', metavar='LOG',
                                     type=FileType,
                                     default=stderr,
                                     help='Path to log errors [default: %(default)s]')
        return parser



if __name__ == '__main__':
    import sys
    sys.exit(VisAlign.run_as_script())
