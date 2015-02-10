from __future__ import absolute_import
from .user.models import *
from .core import (
    and_,
    ARRAY,
    backref,
    Boolean,
    ChoiceType,
    Column,
    Comparator,
    Date,
    FeatureVectorType,
    Float,
    ForeignKey,
    hybrid_property,
    Integer,
    Model,
    MolType,
    Numeric,
    PointType,
    relationship,
    Sequence,
    String,
    SurrogatePK,
)

# TODO Break into modules


##############################################################################


class Structure(Model):
    __tablename__ = 'structure'

    id = Column('id', String(4), primary_key=True)
    title = Column('title', String)
    # TODO: Add protein information
    # aa_sequence = Column('aa_sequence', String)

    def __repr__(self):
        return "<Structure(id={0.id!r}, code={0.code!r})>".format(self)


class Residue(Model):
    __tablename__ = 'residue'

    id = Column('id', String(1), primary_key=True)
    code = Column('code', String(3), unique=True, index=True, nullable=False)
    name = Column('name', String, nullable=False)

    def __repr__(self):
        return "<Residue(id={0.id!r}, code={0.code!r})>".format(self)


class ResidueAtom(Model, SurrogatePK):
    __tablename__ = 'residue_atom'

    residue_fk = Column('residue_fk', ForeignKey(Residue.id), index=True, nullable=False)
    name = Column('code', String(3), index=True, nullable=False)
    element = Column('element', String(2), nullable=False)

    def __repr__(self):
        return "<ResidueAtom(id={0.id!r}, residue_fk={0.residue_fk!r}, name={0.nam!r})>".format(self)


class StructureResidue(Model, SurrogatePK):
    __tablename__ = 'structure_residue'

    pdb_fk = Column('structure_fk', ForeignKey(Structure.id), index=True, nullable=False)
    residue_fk = Column('residue_fk', ForeignKey(Residue.id), index=True, nullable=False)
    model_id = Column('model_id', Integer, default=1, server_default=1, nullable=False)
    chain_id = Column('chain_id', String(1), default='A', server_default='A', nullable=False)
    res_id = Column('res_id', Integer, nullable=False)

    def __repr__(self):
        return "<StructureResidue(id={0.id!r}, pdb_fk={0.pdb_fk!r}, residue_fk={0.residue_fk!r})>".format(self)


###############################################################################


class Ligand(Model):
    __tablename__ = 'ligand'

    id = Column('id', String(3), primary_key=True, nullable=False)
    name = Column('name', String, index=True, nullable=False)
    smiles = Column('smiles', MolType, nullable=False)
    # TODO: PubChem ID


class LigandAtom(Model, SurrogatePK):
    __tablename__ = 'ligand_atom'

    ligand_fk = Column('ligand_fk', String(3), ForeignKey(BoundLigand.id), index=True, nullable=False)
    name = Column('name', String(3), nullable=False)
    serial = Column('serial', Integer, doc="RDKit atom index")

    ligand = relationship(Ligand, backref=backref('atoms', order_by=serial))


class BoundLigand(Model, SurrogatePK):
    __tablename__ = 'bound_ligand'

    ligand_fk = Column('ligand_fk', ForeignKey(Ligand.id), nullable=False)
    pdb_fk = Column('pdb_fk', String(4), ForeignKey(Structure.id), index=True, nullable=False)
    model_id = Column('model', Integer, default=1, server_default=1, nullable=False)
    chain_id = Column('chain', String(1), default='A', server_default='A', nullable=False)
    res_id = Column('residue', Integer, nullable=False)

    ligand = relationship(Ligand, backref=backref('conformations'))

    def __repr__(self):
        return "<BoundLigand(id={0.id!r}, ligand_fk={0.ligand_fk!r}, pdb_fk={0.pdf_fk!r})>".format(self)


class LigandConformation(Model, SurrogatePK):
    __tablename__ = 'ligand_conf'

    ligand_fk = Column('ligand_fk', Integer, ForeignKey(BoundLigand.id), nullable=False)
    atom_fk = Column('atom_fk', Integer, ForeignKey(LigandAtom.id), nullable=False)
    serial = Column('serial', Integer, nullable=False)
    coords = Column('coords', PointType, nullable=False)

    conformation = relationship(BoundLigand, backref=backref('atoms'))
    atom = relationship(LigandAtom, backref=backref('instances'))
    ligand = relationship(Ligand, secondary=BoundLigand.__table__)

    def __repr__(self):
        return "<LigandConformation(id={0.id!r}, ligand_fk={0.ligand_fk!r}, atom_fk={0.atom_fk!r})>".format(self)



##############################################################################


class ActiveSiteKind(Model, SurrogatePK):
    __tablename__ = 'activesite_kind'

    name = Column('name', String, nullable=False)
    description = Column('description', String)


class ActiveSite(Model, SurrogatePK):
    __tablename__ = 'activesite'

    kind_fk = Column('kind_fk', ForeignKey(ActiveSiteKind.id), index=True, nullable=False)
    residue_fk = Column('residue_fk', ForeignKey(Residue.id), index=True, nullable=False)
    serial = Column('serial', Integer, default=1, server_default=1, index=True, nullable=False)

    class CodeComparator(Comparator):
        def __eq__(self, other):
            if isinstance(other, ActiveSite):
                other_fk, other_serial = other.residue_fk, other.serial
            else:
                other_fk, other_serial = other
            return and_(self.residue_fk == other_fk, self.serial == other_serial)

        def __in__(self, other):
            if isinstance(other, (list, tuple, set)):
                residue_fks, serials = zip(*other)
                return and_(self.residue_fk in residue_fks, self.serial in serials)
            else:
                return (self.residue_fk, self.serial) in other

    @hybrid_property
    def code(self):
        return u"{0.residue_fk:s}{0.serial:d}".format(self)

    @code.setter
    def code(self, code):
        res_fk, serial_str = list(code)
        serial = int(serial_str)
        self.residue_fk = res_fk
        self.serial = serial

    @code.comparator
    def code(cls):
        return cls.CodeComparator(cls)

    def __str__(self):
        return self.code

    def __repr__(self):
        return "<ActiveSite(id={0.id!r}, residue_fk={0.residue_fk!r}, serial={0.serial!r}>".format(self)


class ActiveSiteAtom(Model, SurrogatePK):
    __tablename__ = 'activesiteatom'

    activesite_fk = Column('activesite_fk', ForeignKey(ActiveSite.id), index=True, nullable=False)
    atom_fk = Column('atom_fk', ForeignKey(ResidueAtom.id), index=True, nullable=False)

    activesite = relationship(ActiveSite, backref=backref('atoms'))
    atom = relationship(ResidueAtom, backref=backref('activesites'))

    def __repr__(self):
        return "<ActiveSiteAtom(id={0.id!r}, activesite_fk={0.activesite_fk!r}, atom_fk={0.atom_fk!r}>".format(self)


class ActiveSiteSet(Model, SurrogatePK):
    __tablename__ = 'activesiteset'

    name = Column('name', String)
    description = Column('description', String)

    sites = relationship(ActiveSite, secondary=lambda: ActiveSiteSetMember.__table__, backref=backref("sets"))

    def __repr__(self):
        return "<ActiveSiteSet(id={0.id!r}, name={0.name!r})".format(self)


class ActiveSiteSetMember(Model, SurrogatePK):
    __tablename__ = 'activesitesetmember'

    activesite_fk = Column('activesite_fk', ForeignKey(ActiveSite.id), index=True, nullable=False)
    set_fk = Column('set_fk', ForeignKey(ActiveSiteSet.id), index=True, nullable=False)


#######################################################################################################################


class ExcludedLigandSet(Model, SurrogatePK):
    __tablename__ = 'excluded_ligand_set'

    name = Column('name', String)


class ExcludedLigandSetMember(Model):
    __tablename__ = 'excluded_ligand_set_member'

    set_fk = Column('set_fk', ForeignKey(ExcludedLigandSet.id), index=True, nullable=False)
    ligand_fk = Column('ligand_fk', ForeignKey(Ligand.id), index=True, nullable=False)


class PocketExtractionParameters(Model, SurrogatePK):
    __tablename__ = 'extraction_params'

    name = Column('name', String)

    ligand_residue_distance_cutoff = Column('ligand_residue_distance_cutoff', Float)
    exclude_ligand_set_fk = Column('exclude_ligand_fk', ForeignKey(ExcludedLigandSet.id))


class MicroEnvironmentSet(Model):
    __tablename__ = 'featurevectorset'

    FEATURE_VECTOR_SET_TYPE = [
        (u'V', u'FEATURE Vector Set'),
        (u'L', u'Ligand Pocket'),
        (u'I', u'Protein Protein Interface'),
    ]

    id = Column('id', Integer, primary_key=True)
    structure_fk = Column('pdb_fk', String(4), ForeignKey(Structure.pdb), index=True)

    name = Column('name', String, default='', server_default='')
    comment = Column('comment', String, default='', server_default='')
    origin = Column('type', ChoiceType(FEATURE_VECTOR_SET_TYPE), index=True)

    __mapper_args__ = {
        'polymorphic_on': origin,
        'polymorphic_identity': u'V',
        'with_polymorphic': '*',
    }


class LigandPocket(MicroEnvironmentSet):
    __tablename__ = 'pocket'

    id = Column('id', ForeignKey(MicroEnvironmentSet.id), primary_key=True)
    ligand_fk = Column('ligand_fk', ForeignKey(BoundLigand.id), index=True)
    parameters_fk = Column('parameters_fk', ForeignKey(PocketExtractionParameters))

    __mapper_args__ = {
        'polymorphic_identity': u'L',
    }


#######################################################################################################################


class MicroEnvironment(Model):
    __tablename__ = 'microenvironment'

    MICROENVIRONMENT_ORIGIN_TYPE = [
        (u'M', u'Micro Environment'),
        (u'S', u'Residue Active Site'),
        (u'A', u'Explicit Atom'),
        (u'C', u'Manually Curated'),
        (u'O', u'Other Environment'),
    ]

    id = Column('id', Integer, primary_key=True)
    structure_fk = Column('pdb_fk', String(4), ForeignKey(Structure.pdb), index=True)
    name = Column('name', String)

    coords = Column('coords', PointType, nullable=False)
    comment = Column('comment', String, default='', server_default='')

    set_fk = Column('parent_fk', ForeignKey(MicroEnvironmentSet.id), index=True, nullable=False)
    origin = Column('type', ChoiceType(MICROENVIRONMENT_ORIGIN_TYPE), index=True)

    __mapper_args__ = {
        'polymorphic_on': origin,
        'polymorphic_identity': u'M',
        'with_polymorphic': '*',
    }


class ActiveSiteEnvironment(MicroEnvironment):
    __tablename__ = 'activesite_microenvironment'

    id = Column('id', Integer, ForeignKey(MicroEnvironment.id), primary_key=True)
    site_fk = Column('site_fk', Integer, ForeignKey(ActiveSite.id), index=True)
    structure_residue_fk = Column('structure_residue_fk', Integer, ForeignKey(StructureResidue.id), index=True)

    __mapper_args__ = {
        'polymorphic_identity': u'S',
    }


class AtomEnvironment(MicroEnvironment):
    __tablename__ = 'atom_microenvironment'

    id = Column('id', Integer, ForeignKey(MicroEnvironment.id), primary_key=True)
    residue_fk = Column('residue_fk', String(1), ForeignKey(Residue.id), index=True)
    atom_fk = Column('atom_fk', String(3), ForeignKey(ResidueAtom.id), index=True)
    atom_index = Column('atom_number', Integer)

    __mapper_args__ = {
        'polymorphic_identity': u'A',
    }


class CuratedEnvironment(MicroEnvironment):
    __tablename__ = 'curated_microenvironment'

    id = Column('id', Integer, ForeignKey(MicroEnvironment.id), primary_key=True)
    notes = Column('notes', String)
    # TODO: Add SeqFEATURE reference information

    __mapper_args__ = {
        'polymorphic_identity': u'C',
    }


class OtherEnvironment(MicroEnvironment):
    __tablename__ = 'other_microenvironment'

    id = Column('id', Integer, ForeignKey(MicroEnvironment.id), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': u'O',
    }


#######################################################################################################################


class FeatureVectorParameters(Model, SurrogatePK):
    __tablename__ = 'featurevector_parameters'

    num_shells = Column('num_shells', Integer)
    shell_width = Column('shell_width', Float)
    exclude_residues = Column('exclude_residues', ARRAY(String(3)))
    properties = Column('properties', ARRAY(String))

    mean = Column('mean', FeatureVectorType)
    std = Column('std', FeatureVectorType)


class FeatureVector(Model, SurrogatePK):
    __tablename__ = 'featurevector'

    microenvironment_fk = Column('microenvironment_fk', ForeignKey(MicroEnvironment.id), index=True)
    parameters_fk = Column('parameters_fk', ForeignKey(FeatureVectorParameters.id))
    features = Column('features', FeatureVectorType)

    microenvironment = relationship(MicroEnvironment, backref=backref('features'))
    microenvironment_set = relationship(MicroEnvironmentSet,
                                        secondary=MicroEnvironment.__table__,
                                        backref=backref('features'))
    parameters = relationship(FeatureVectorParameters,
                              backref=backref('features', lazy='dynamic'))

    @hybrid_property
    def z_features(self):
        if self.parameters is None:
            raise ValueError("Cannot calculate Z-Scores without parameters")
