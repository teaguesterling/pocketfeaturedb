#!/usr/bin/env python
from __future__ import print_function

import logging
import os
import random


from feature.io import pointfile
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io import residuefile

from pocketfeature.tasks.core import Task


HEADER = """
from pymol.cgo import *
from pymol import cmd
pocket = [
"""

FOOTER = """
]
cmd.load({0})
cmd.load_cgo(pocket, 'pocket')
"""

def create_command(pdb, points, radii, colors):
    lines = []
    for point, radius, color in zip(points, radii, colors):
        lines.append("    COLOR, {0:.3f}, {1:.3f}, {2:.3f},".format(*color))
        lines.append("    SPHERE, {0:.3f}, {1:.3f}, {2:.3f}, {3:.3f},".format(point.x, 
                                                            point.y, 
                                                            point.z, 
                                                            radius))
    footer = FOOTER.format(repr(pdb))

    return HEADER + "\n".join(lines) + footer


def get_point_name(point):
    return point.comment.split()[0]


def create_visualizations(pointsA, pointsB, alignment, pdbA=None, 
                                                       pdbB=None,
                                                       colors=None,
                                                       radii=None):
        pointsA = list(pointsA)
        pointsB = list(pointsB)
        pointMapA = {get_point_name(p): p for p in pointsA}
        pointMapB = {get_point_name(p): p for p in pointsB}

        if radii is None:
            scores = alignment.values()
            minScore, maxScore = min(scores), max(scores)
            radii = [score/(maxScore) for score in scores]
        else:
            radii = list(radii)

        if colors is None:
            colors = [(random.random(),
                       random.random(),
                       random.random()) for _ in scores]
        else:
            colors = list(colors)
        
        pdbA = "{0}.pdb".format(pointsA[0].pdbid) if pdbA is None else pdbA
        pdbB = "{0}.pdb".format(pointsB[0].pdbid) if pdbA is None else pdbB
        
        scriptA = create_command(pdbA, pointsA, radii, colors)
        scriptB = create_command(pdbB, pointsB, radii, colors)

        return scriptA, scriptB 


class VisAlign(Task):

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(logging.DEBUG)

        pointsA = pointfile.load(params.pointsA)
        pointsB = pointfile.load(params.pointsB)
        alignment = matrixvaluesfile.load(params.alignment, cast=float)

        if params.colors is not None:
            colors = [map(float, l.split()) for l in params.colors]
        else:
            colors = None

        if params.radii is not None:
            radii = [float(l) for l in params.raii]
        else:
            radii = None

        scriptA, scriptB = create_visualizations(pointsA, 
                                                 pointsB, 
                                                 alignment,
                                                 pdbA=params.pdbA, 
                                                 pdbB=params.pdbB,
                                                 colors=colors,
                                                 radii=radii)

        print(scriptA, file=params.outputA)
        print(scriptB, file=params.outputB)

        return 0

    @classmethod
    def arguments(cls, stdin, stdout, stderr, environ, task_name):
        from argparse import ArgumentParser
        from pocketfeature.utils.args import FileType
        parser = ArgumentParser("Create PyMol scripts to visualize an alignment")
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
        parser.add_argument('--pdbA', metavar='PDB1', 
                                      help='Path to first PDB file',
                                      nargs='?',
                                      default=None)
        parser.add_argument('--pdbB', metavar='PDB2', 
                                      help='Path to second PDB file',
                                      nargs='?',
                                      default=None)
        parser.add_argument('--colors', metavar='COLORFILE', 
                                        help='File of 0.0-1.0 RGB colors to use',
                                        type=FileType('r'),
                                        nargs='?',
                                        default=None)
        parser.add_argument('--radii', metavar='RADIIFILE', 
                                        help='File of point radii to use',
                                        type=FileType('r'),
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
