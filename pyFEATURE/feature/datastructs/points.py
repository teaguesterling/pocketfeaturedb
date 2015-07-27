from __future__ import absolute_import

import numpy as np


class Point3D(object):
    """
        Wrapper object for storing 3D coordinants. This may be worth
        replacing with a more refined 3D point representation
    """
    def __init__(self, x, y, z, *args, **kwargs):
        xyz = (x,y,z)
        self.coords = np.array(xyz, dtype=np.float, *args, **kwargs)

    def __iter__(self):
        return iter(self.coords)

    @property
    def x(self):
        return self.coords[0]

    @property
    def y(self):
        return self.coords[1]

    @property
    def z(self):
        return self.coords[2]

    def __repr__(self):
        cls_name = type(self).__name__
        return "{0}({1}, {2}, {3})".format(cls_name, *self.coords)

    def __str__(self):
        return "({0},{1},{2})".format(*self.coords)


class PDBPoint(Point3D):
    """ Container for FEATURE pointfile data """
    def __init__(self, x, y, z, pdbid, comment=""):
        super(PDBPoint, self).__init__(x, y, z)
        self.pdbid = pdbid
        self.comment = comment

    def __repr__(self):
        cls_name = type(self).__name__
        args = list(self.coords) + [repr(self.pdbid)]
        return "{0}({1}, {2}, {3}, pdbid={4})".format(cls_name, *args)
