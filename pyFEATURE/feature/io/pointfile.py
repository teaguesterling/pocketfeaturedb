from __future__ import absolute_import, print_function

from six import moves

from feature.datastructs.points import PDBPoint

COORDS_LINE = "{:.3f}\t{:.3f}\t{:.3f}"
POINT_LINE = "{}\t" + COORDS_LINE
NON_COMMENT_LINE = POINT_LINE + "\n"
COMMENT_LINE = POINT_LINE + "\t#\t{}" + "\n"


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


def dump(pointlist, io, **kwargs):
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
                line, comment = map(str.strip, line.split('#', 1))
            else:
                comment = ''
            if len(line) > 0:
                pdbid, x, y, z = line.split()
                x, y, z = map(float, (x, y, z))
            else:
                continue
            yield wrapper(x, y, z, pdbid=pdbid, comment=comment)
        except Exception:
            if not ignore_invalid:
                raise


def load(io, **kwargs):
    return tuple(loadi(io, **kwargs))


def dumps(pointlist, **kwargs):
    buf = moves.StringIO()
    dump(pointlist, buf, **kwargs)
    return buf.getvalue()


def loads(data, **kwargs):
    return load(str(data).splitlines(), **kwargs)


