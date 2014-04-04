from __future__ import print_function

from cStringIO import StringIO
import numpy as np

COORDS_LINE = "{:.3f}\t{:.3f}\t{:.3f}"
POINT_LINE = "{}\t" + COORDS_LINE
NON_COMMENT_LINE = POINT_LINE + "\n"
COMMENT_LINE = POINT_LINE + "\t#\t{}" + "\n"



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


def dumpi(pointlist):
    for point in pointlist:
        if point.comment:
            tpl = COMMENT_LINE
            if isinstance(point.comment, (tuple, list)):  # Multiple comments:
                comment = "\t#\t".join(point.comment)
            else:
                comment = point.comment
            line = (point.pdbid, point.x, point.y, point.z, comment)
        else:
            tpl = NON_COMMENT_LINE
            line = (point.pdbid, point.x, point.y, point.z)
        yield tpl.format(*line)


def dump(pointlist, io):
    """ Write a point list to a file-like object """
    lines = dumpi(pointlist)
    for line in lines:
        io.write(line)


def loadi(src, wrapper=PDBPoint, ignore_invalid=False):
    """ Load a pointfile list from an interator """
    for line in src:
        try:
            line = line.strip()
            if '#' in line:
                line, comment = map(str.strip, line.split('#'))
            if len(line) > 0:
                pdbid, x, y, z = line.split()
                x, y, z = map(float, (x, y, z))
        except Exception:
            if not ignore_invalid:
                raise
        yield wrapper(x, y, z, pdbid=pdbid, comment=comment)


def load(io, **kwargs):
    return tuple(loadi(io, **kwargs))


def dumps(pointlist, **kwargs):
    buf = StringIO()
    dump(pointlist, buf, **kwargs)
    return buf.getvalue()


def loads(data, **kwargs):
    return load(str(data).splitlines(), **kwargs)


