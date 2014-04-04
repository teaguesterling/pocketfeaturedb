#!/usr/bin/env python
from __future__ import print_function

import logging
import os
import random


from feature.io import pointfile
from pocketfeature.io import matrixvaluesfile
from pocketfeature.io import residuefile

from pocketfeature.tasks.core import Task


def pdb_name(pdb):
    return os.path.basename(pdb).split('.')[0]


def ligand_to_pymol_selector(ligand):
    if '`' in ligand:
        return ligand
    elif '_' in ligand and len(ligand) > 3:
        tokens = ligand.split('_')
        return "/{0}//{1}/{3}`{2}".format(*tokens)
    else:
        return "resn {}".format(ligand)


def render_pymol_python(pdb, points, radii, colors, ligand=None):
    name = pdb_name(pdb)
    res_selector = ligand_to_pymol_selector(ligand)

    lines = [
        "from pymol.cgo import *",
        "from pymol import cmd",
        "pocket = [",
    ]
    for point, radius, color in zip(points, radii, colors):
        lines.append("    COLOR, {0:.3f}, {1:.3f}, {2:.3f},".format(*color))
        lines.append("    SPHERE, {0:.3f}, {1:.3f}, {2:.3f}, {3:.3f},".format(point.x, 
                                                            point.y, 
                                                            point.z, 
                                                            radius))
    lines.append("]")
    lines.append("cmd.load('{0}', '{1}')".format(pdb, name))
    lines.append("cmd.load_cgo(pocket, 'pocket')")
    lines.append("cmd.hide('everything', selection='{0}')".format(name))
    lines.append("cmd.show('cartoon', selection='{0}')".format(name))
    lines.append("cmd.show('sticks', selection='{0}')".format(res_selector))
    lines.append("cmd.bg_color('white')")
    lines.append("cmd.ray()")
    return os.linesep.join(lines)


def get_point_name(point):
    return point.comment.split()[0]


def create_alignment_visualizations(pointsA, pointsB, alignment, pdbA=None, 
                                                                 pdbB=None,
                                                                 colors=None,
                                                                 radii=None):
        pointsA = list(pointsA)
        pointsB = list(pointsB)
        pointMapA = {get_point_name(p): p for p in pointsA}
        pointMapB = {get_point_name(p): p for p in pointsB}
        ligandA = ligand_to_pymol_selector(pointMapA.keys()[0])
        ligandB = ligand_to_pymol_selector(pointMapB.keys()[0])

        if radii is None:
            scores = alignment.values()
            minScore, maxScore = min(scores), max(scores)
            maxScore = max(maxScore, 1)  # prevent divide by zero
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
        
        scriptA = render_pymol_python(pdbA, pointsA, radii, colors, ligandA)
        scriptB = render_pymol_python(pdbB, pointsB, radii, colors, ligandB)

        return scriptA, scriptB 


def create_single_visualization(pointsA, pdbA=None, 
                                         colors=None,
                                         radii=None):
        pointsA = list(pointsA)
        pointMapA = {get_point_name(p): p for p in pointsA}
        ligandA = ligand_to_pymol_selector(pointMapA.keys()[0])

        if radii is None:
            radii = [1.25 for score in pointsA]
        else:
            radii = list(radii)

        if colors is None:
            colors = [(random.random(),
                       random.random(),
                       random.random()) for _ in pointsA]
        else:
            colors = list(colors)
        
        pdbA = "{0}.pdb".format(pointsA[0].pdbid) if pdbA is None else pdbA
        
        scriptA = render_pymol_python(pdbA, pointsA, radii, colors, ligandA)

        return scriptA


class VisAlign(Task):

    def run(self):
        params = self.params
        logging.basicConfig(stream=params.log)
        log = logging.getLogger('pocketfeature')
        log.setLevel(logging.DEBUG)

        pointsA = pointfile.load(params.pointsA)
        if params.pointsB is not None:
            pointsB = pointfile.load(params.pointsB)
        else:
            pointsB = None
        if params.alignment is not None:
            alignment = matrixvaluesfile.load(params.alignment, cast=float)
        else:
            alignment = None

        if params.colors is not None:
            colors = [map(float, l.split()) for l in params.colors]
        else:
            colors = None

        if params.radii is not None:
            radii = [float(l) for l in params.raii]
        else:
            radii = None
        
        if pointsB is not None and alignment is not None:
            scriptA, scriptB = create_alignment_visualizations(pointsA, 
                                                               pointsB, 
                                                               alignment,
                                                               pdbA=params.pdbA, 
                                                               pdbB=params.pdbB,
                                                               colors=colors,
                                                               radii=radii)

            print(scriptA, file=params.outputA)
            print(scriptB, file=params.outputB)

        else:
            scriptA = create_single_visualization(pointsA,
                                                  pdbA=params.pdbA,
                                                  colors=colors,
                                                  radii=radii)
            print(scriptA, file=params.outputA)


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
                                       nargs='?',
                                       default=None,
                                       help='Path to FEATURE point file')
        parser.add_argument('alignment', metavar='ALIGNMENT',
                                         type=FileType.compressed('r'),
                                         nargs='?',
                                         default=None,
                                         help='Path to PocketFEATURE alignment')
        parser.add_argument('-A', '--outputA', metavar='CMD1',
                                              type=FileType('w'),
                                              help='Path to first command output file')
        parser.add_argument('-B', '--outputB', metavar='CMD2',
                                              type=FileType('w'),
                                              nargs='?',
                                              default=None,
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
