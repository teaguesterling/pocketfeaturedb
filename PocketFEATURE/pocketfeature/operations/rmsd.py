from __future__ import absolute_import

from pocketfeature.algorithms import alignment_rmsd
from pocketfeature.utils.ff import get_point_name_to_coords_lookup


def compute_alignment_rmsd(alignment, pocketA, pocketB):
    coordsA = get_point_name_to_coords_lookup(pocketA)
    coordsB = get_point_name_to_coords_lookup(pocketB)
    aligned_points = alignment.items()

    rmsd = alignment_rmsd(aligned_points, coordsA, coordsB)

    return rmsd
