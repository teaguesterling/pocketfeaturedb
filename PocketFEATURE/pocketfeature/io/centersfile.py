from __future__ import absolute_import, print_function

from collections import defaultdict

from six import moves

from pocketfeature.datastructs.residues import CenterCalculator


def load_from_metadata(metadata, key='RESIDUE_CENTERS'):
    if key not in metadata:
        raise KeyError()
    else:
        raise NotImplemented()


def loadi(it,
          wrapper=CenterCalculator,
          wrapper_args=None,
          use_classes=True,
          comments_delimiter='#',
          field_delimiter='\t',
          atom_delimiter=','):

    centers = defaultdict(list)
    classes = defaultdict(list)

    if use_classes:
        split_count = 2
    else:
        split_count = 1

    for line in it:
        data = line.split(comments_delimiter, 1)[0].strip()
        try:
            tokens = data.split(field_delimiter, split_count)
            res_name = tokens[0].upper()
            atoms = tuple(map(str.upper, tokens[1].split(atom_delimiter)))
            center_idx = len(centers[res_name])

            centers[res_name].append(atoms)

            if use_classes:
                class_name = tokens[2]
                center_id = (res_name,center_idx)
                classes[class_name].append(center_id)

        except IndexError:
            continue

    wrapper_args = wrapper_args or {}
    center_calculator = wrapper(centers, classes, **wrapper_args)

    return center_calculator


def load(data,
         wrapper=CenterCalculator,
         wrapper_args=None,
         use_classes=True,
         comments_delimiter='#',
         field_delimiter='\t',
         atom_delimiter=','):
    it = list(data)
    return loadi(it,
                 wrapper=wrapper,
                 wrapper_args=wrapper_args,
                 use_classes=use_classes,
                 comments_delimiter=comments_delimiter,
                 field_delimiter=field_delimiter,
                 atom_delimiter=atom_delimiter)


def loads(data,
          wrapper=CenterCalculator,
          wrapper_args=None,
          use_classes=True,
          comments_delimiter='#',
          field_delimiter='\t',
          atom_delimiter=','):
    it = moves.StringIO(data)
    return loadi(it,
                 wrapper=wrapper,
                 wrapper_args=wrapper_args,
                 use_classes=use_classes,
                 comments_delimiter=comments_delimiter,
                 field_delimiter=field_delimiter,
                 atom_delimiter=atom_delimiter)


def dumpi(calculator,
          use_classes=True,
          comments_delimiter='#',
          field_delimiter='\t',
          atom_delimiter=','):
    if use_classes:
        class_lookup = dict((center_id, cls)
                            for cls, center_ids in calculator.classes.items()
                            for center_id in center_ids)
    else:
        class_lookup = None

    for res_name, centers in calculator.centers.items():
        for center_idx, atoms in enumerate(centers):
            fields = [res_name, atom_delimiter.join(atoms)]
            if class_lookup:
                center_id = (res_name, center_idx)
                center_class = class_lookup[center_id]
                fields.append(center_class)
            line = field_delimiter.join(fields)
            yield line


def dump(out,
         calculator,
         use_classes=True,
         comments_delimiter='#',
         field_delimiter='\t',
         atom_delimiter=','):
    lines = dumpi(calculator,
                  use_classes=use_classes,
                  comments_delimiter=comments_delimiter,
                  field_delimiter=field_delimiter,
                  atom_delimiter=atom_delimiter)
    for line in lines:
        print(line, file=out)


def dumps(calculator,
          use_classes=True,
          comments_delimiter='#',
          field_delimiter='\t',
          atom_delimiter=','):
    buf = moves.StringIO()
    dump(buf, calculator,
         use_classes=use_classes,
         comments_delimiter=comments_delimiter,
         field_delimiter=field_delimiter,
         atom_delimiter=atom_delimiter)
    return buf.getvalue()


def dumpl(calculator,
          use_classes=True,
          comments_delimiter='#',
          field_delimiter='\t',
          atom_delimiter=','):
    lines = dumpi(calculator,
                  use_classes=use_classes,
                  comments_delimiter=comments_delimiter,
                  field_delimiter=field_delimiter,
                  atom_delimiter=atom_delimiter)
    return list(lines)
