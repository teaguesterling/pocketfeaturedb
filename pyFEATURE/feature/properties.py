from __future__ import print_function

from cStringIO import StringIO
import numpy as np


def property_dtype(property):
    """ 
        STUB: Eventually this should create int or float types
    """
    return np.dtype(float)


class StaticDefaultMixin(object):
    @property
    def mutable_type(self):
        return type(self).__base__ 
    def redefine(self, *args, **kwargs):
        return self.mutable_type(*args, **kwargs)


class ItemNameList(list):
    """ 
    Base container for storing field names
    This could probably be better replaced with Pandas or something
    """

    def indexes(self, selected=None):
        """ Get a list of indexes of properties in 'selected'

            Keyword Arguments:
            selected -- Sequence of indexes to retrieve

            Return a dictionary of properties to their respective positions
            in the property list. An optional list of "selected" properties
            can be supplied to choose only a subset of properties.

        """
        if selected is None:
            selected = self
        positions = dict((prop, idx) for idx, prop in enumerate(self))
        return [positions[prop] for prop in selected if prop in positions]

    def intersect(self, other):
        """ Create a new PropertyList as the intersection of two lists

            Keyword Arguments:
            other -- PropertyList or sequence to interset this list with

            Returns: A new PropertyList with properties in both self and other

        """
        cls = type(self)
        return cls([self[idx] for idx in self.indexes(other)])

    def clone(self):
        """ Create a duplicate of this property list """
        cls = type(self)
        return cls(self)


class PropertyList(ItemNameList):
    """ Container to store lists of parameters used in FEATURE calcuations """

    def get_features(self, shells):
        return ["{0}_{1}".format(name, shell) for shell in range(shells) for name in self]

    def dtype(self):
        """ Construct a numpy dtype for this property list """
        #definition = [(prop, property_dtype(prop)) for prop in self]
        # TODO: Customize the FEATURE vector dtype for a property list
        return np.float


class DefaultItemNameList(ItemNameList, StaticDefaultMixin):
    mutable_type = ItemNameList

class DefaultPropertyList(PropertyList, StaticDefaultMixin):
    mutable_type = PropertyList



def loadi(src, container=PropertyList):
    """ Create a PropertyList from an iterator 

        Keyword Arguments:
        src -- Iterator to read properties from
        container -- Class to build the PropertyList (Default: PropertyList)

        Returns: Object of type 'container' (Default: PropertyList)

    """

    return container(p.strip() for p in src if not p.startswith('#'))


def loads(src, container=PropertyList):
    """ Create a PropertyList from a string (by lines)

        Keyword Arguments:
        src -- String to load properties from
        container -- Class to build the PropertyList (Default: PropertyList)

        Returns: Object of type 'container' (Default: PropertyList)

    """
    return loadi(src.splitlines(), container=container)


def load(path, container=PropertyList):
    """ Create a PropertyList from a file

        Keyword Arguments:
        src -- Path to properties file to load
        container -- Class to build the PropertyList (Default: PropertyList)

        Returns: Object of type 'container' (Default: PropertyList)

    """
    with open(path, 'r') as f:
        return loadi(f, container=container)


def dump(dest, props):
    """ Write a list of properties to a file-like object

        Keyword Arguments:
        dest -- File-like object to write properties to
        props -- PropertyList to write

    """
    for prop in props:
        print(prop, file=dest)


def dumps(props):
    """ Write a list of properties to a string

        Keyword Arguments:
        props -- PropertyList to write

        Returns: String representation of PropertyList

    """
    buf = StringIO()
    dump(buf, props)
    return buf.getvalue()


ALL = DefaultPropertyList([
    'ALIPHATIC_CARBON',
    'ALIPHATIC_CARBON_NEXT_TO_POLAR',
    'AMIDE',
    'AMIDE_CARBON',
    'AMIDE_NITROGEN',
    'AMIDE_OXYGEN',
    'AMINE',
    'AROMATIC_CARBON',
    'AROMATIC_NITROGEN',
    'ATOM_TYPE_IS_C',
    'ATOM_TYPE_IS_CA',
    'ATOM_TYPE_IS_CT',
    'ATOM_TYPE_IS_N',
    'ATOM_TYPE_IS_N2',
    'ATOM_TYPE_IS_N3',
    'ATOM_TYPE_IS_NA',
    'ATOM_TYPE_IS_O',
    'ATOM_TYPE_IS_O2',
    'ATOM_TYPE_IS_OH',
    'ATOM_TYPE_IS_OTHER',
    'ATOM_TYPE_IS_S',
    'ATOM_TYPE_IS_SH',
    'CARBONYL',
    'CARBOXYL_CARBON',
    'CARBOXYL_OXYGEN',
    'CHARGE',
    'CHARGE_WITH_HIS',
    'ELEMENT_IS_ANY',
    'ELEMENT_IS_C',
    'ELEMENT_IS_N',
    'ELEMENT_IS_O',
    'ELEMENT_IS_OTHER',
    'ELEMENT_IS_S',
    'HYDROPHOBICITY',
    'HYDROXYL',
    'HYDROXYL_OXYGEN',
    'MOBILITY',
    'NEG_CHARGE',
    'PARTIAL_CHARGE',
    'PARTIAL_POSITIVE_CARBON',
    'PEPTIDE',
    'POSITIVE_NITROGEN',
    'POS_CHARGE',
    'RESIDUE_CLASS1_IS_CHARGED',
    'RESIDUE_CLASS1_IS_HYDROPHOBIC',
    'RESIDUE_CLASS1_IS_POLAR',
    'RESIDUE_CLASS1_IS_UNKNOWN',
    'RESIDUE_CLASS2_IS_ACIDIC',
    'RESIDUE_CLASS2_IS_BASIC',
    'RESIDUE_CLASS2_IS_NONPOLAR',
    'RESIDUE_CLASS2_IS_POLAR',
    'RESIDUE_CLASS2_IS_UNKNOWN',
    'RESIDUE_NAME_IS_ALA',
    'RESIDUE_NAME_IS_ARG',
    'RESIDUE_NAME_IS_ASN',
    'RESIDUE_NAME_IS_ASP',
    'RESIDUE_NAME_IS_CYS',
    'RESIDUE_NAME_IS_GLN',
    'RESIDUE_NAME_IS_GLU',
    'RESIDUE_NAME_IS_GLY',
    'RESIDUE_NAME_IS_HIS',
    'RESIDUE_NAME_IS_HOH',
    'RESIDUE_NAME_IS_ILE',
    'RESIDUE_NAME_IS_LEU',
    'RESIDUE_NAME_IS_LYS',
    'RESIDUE_NAME_IS_MET',
    'RESIDUE_NAME_IS_OTHER',
    'RESIDUE_NAME_IS_PHE',
    'RESIDUE_NAME_IS_PRO',
    'RESIDUE_NAME_IS_SER',
    'RESIDUE_NAME_IS_THR',
    'RESIDUE_NAME_IS_TRP',
    'RESIDUE_NAME_IS_TYR',
    'RESIDUE_NAME_IS_VAL',
    'RING_SYSTEM',
    'SECONDARY_STRUCTURE1_IS_3HELIX',
    'SECONDARY_STRUCTURE1_IS_4HELIX',
    'SECONDARY_STRUCTURE1_IS_5HELIX',
    'SECONDARY_STRUCTURE1_IS_BEND',
    'SECONDARY_STRUCTURE1_IS_BRIDGE',
    'SECONDARY_STRUCTURE1_IS_COIL',
    'SECONDARY_STRUCTURE1_IS_HET',
    'SECONDARY_STRUCTURE1_IS_STRAND',
    'SECONDARY_STRUCTURE1_IS_TURN',
    'SECONDARY_STRUCTURE1_IS_UNKNOWN',
    'SECONDARY_STRUCTURE2_IS_BETA',
    'SECONDARY_STRUCTURE2_IS_COIL',
    'SECONDARY_STRUCTURE2_IS_HELIX',
    'SECONDARY_STRUCTURE2_IS_HET',
    'SECONDARY_STRUCTURE2_IS_UNKNOWN',
    'SOLVENT_ACCESSIBILITY',
    'SULFUR',
    'VDW_VOLUME',
])


PROTEINS = DefaultPropertyList([
    'ATOM_TYPE_IS_C',
    'ATOM_TYPE_IS_CT',
    'ATOM_TYPE_IS_CA',
    'ATOM_TYPE_IS_N',
    'ATOM_TYPE_IS_N2',
    'ATOM_TYPE_IS_N3',
    'ATOM_TYPE_IS_NA',
    'ATOM_TYPE_IS_O',
    'ATOM_TYPE_IS_O2',
    'ATOM_TYPE_IS_OH',
    'ATOM_TYPE_IS_S',
    'ATOM_TYPE_IS_SH',
    'ATOM_TYPE_IS_OTHER',
    'PARTIAL_CHARGE',
    'ELEMENT_IS_ANY',
    'ELEMENT_IS_C',
    'ELEMENT_IS_N',
    'ELEMENT_IS_O',
    'ELEMENT_IS_S',
    'ELEMENT_IS_OTHER',
    'HYDROXYL',
    'AMIDE',
    'AMINE',
    'CARBONYL',
    'RING_SYSTEM',
    'PEPTIDE',
    'VDW_VOLUME',
    'CHARGE',
    'NEG_CHARGE',
    'POS_CHARGE',
    'CHARGE_WITH_HIS',
    'HYDROPHOBICITY',
    'MOBILITY',
    'SOLVENT_ACCESSIBILITY',
    'RESIDUE_NAME_IS_ALA',
    'RESIDUE_NAME_IS_ARG',
    'RESIDUE_NAME_IS_ASN',
    'RESIDUE_NAME_IS_ASP',
    'RESIDUE_NAME_IS_CYS',
    'RESIDUE_NAME_IS_GLN',
    'RESIDUE_NAME_IS_GLU',
    'RESIDUE_NAME_IS_GLY',
    'RESIDUE_NAME_IS_HIS',
    'RESIDUE_NAME_IS_ILE',
    'RESIDUE_NAME_IS_LEU',
    'RESIDUE_NAME_IS_LYS',
    'RESIDUE_NAME_IS_MET',
    'RESIDUE_NAME_IS_PHE',
    'RESIDUE_NAME_IS_PRO',
    'RESIDUE_NAME_IS_SER',
    'RESIDUE_NAME_IS_THR',
    'RESIDUE_NAME_IS_TRP',
    'RESIDUE_NAME_IS_TYR',
    'RESIDUE_NAME_IS_VAL',
    'RESIDUE_NAME_IS_HOH',
    'RESIDUE_NAME_IS_OTHER',
    'RESIDUE_CLASS1_IS_HYDROPHOBIC',
    'RESIDUE_CLASS1_IS_CHARGED',
    'RESIDUE_CLASS1_IS_POLAR',
    'RESIDUE_CLASS1_IS_UNKNOWN',
    'RESIDUE_CLASS2_IS_NONPOLAR',
    'RESIDUE_CLASS2_IS_POLAR',
    'RESIDUE_CLASS2_IS_BASIC',
    'RESIDUE_CLASS2_IS_ACIDIC',
    'RESIDUE_CLASS2_IS_UNKNOWN',
    'SECONDARY_STRUCTURE1_IS_3HELIX',
    'SECONDARY_STRUCTURE1_IS_4HELIX',
    'SECONDARY_STRUCTURE1_IS_5HELIX',
    'SECONDARY_STRUCTURE1_IS_BRIDGE',
    'SECONDARY_STRUCTURE1_IS_STRAND',
    'SECONDARY_STRUCTURE1_IS_TURN',
    'SECONDARY_STRUCTURE1_IS_BEND',
    'SECONDARY_STRUCTURE1_IS_COIL',
    'SECONDARY_STRUCTURE1_IS_HET',
    'SECONDARY_STRUCTURE1_IS_UNKNOWN',
    'SECONDARY_STRUCTURE2_IS_HELIX',
    'SECONDARY_STRUCTURE2_IS_BETA',
    'SECONDARY_STRUCTURE2_IS_COIL',
    'SECONDARY_STRUCTURE2_IS_HET',
    'SECONDARY_STRUCTURE2_IS_UNKNOWN',
])


METALS = DefaultPropertyList([
    'ALIPHATIC_CARBON',
    'AROMATIC_CARBON',
    'PARTIAL_POSITIVE_CARBON',
    'ALIPHATIC_CARBON_NEXT_TO_POLAR',
    'AMIDE_CARBON',
    'CARBOXYL_CARBON',
    'AMIDE_NITROGEN',
    'POSITIVE_NITROGEN',
    'AROMATIC_NITROGEN',
    'AMIDE_OXYGEN',
    'CARBOXYL_OXYGEN',
    'HYDROXYL_OXYGEN',
    'SULFUR',
    'PARTIAL_CHARGE',
    'VDW_VOLUME',
    'CHARGE',
    'NEG_CHARGE',
    'POS_CHARGE',
    'CHARGE_WITH_HIS',
    'HYDROPHOBICITY',
    'SOLVENT_ACCESSIBILITY',
    'ELEMENT_IS_ANY',
    'RESIDUE_NAME_IS_ALA',
    'RESIDUE_NAME_IS_ARG',
    'RESIDUE_NAME_IS_ASN',
    'RESIDUE_NAME_IS_ASP',
    'RESIDUE_NAME_IS_CYS',
    'RESIDUE_NAME_IS_GLN',
    'RESIDUE_NAME_IS_GLU',
    'RESIDUE_NAME_IS_GLY',
    'RESIDUE_NAME_IS_HIS',
    'RESIDUE_NAME_IS_ILE',
    'RESIDUE_NAME_IS_LEU',
    'RESIDUE_NAME_IS_LYS',
    'RESIDUE_NAME_IS_MET',
    'RESIDUE_NAME_IS_PHE',
    'RESIDUE_NAME_IS_PRO',
    'RESIDUE_NAME_IS_SER',
    'RESIDUE_NAME_IS_THR',
    'RESIDUE_NAME_IS_TRP',
    'RESIDUE_NAME_IS_TYR',
    'RESIDUE_NAME_IS_VAL',
    'RESIDUE_NAME_IS_HOH',
    'RESIDUE_NAME_IS_OTHER',
])


# Set the proteins list as the default
DEFAULT_PROPERTIES = PROTEINS
