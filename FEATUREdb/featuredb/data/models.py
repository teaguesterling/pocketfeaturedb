from __future__ import absolute_import, division
from .user.models import *
from .core import (
    and_,
    ARRAY,
    association_proxy,
    attribute_mapped_collection,
    backref,
    Boolean,
    ChoiceType,
    Column,
    column_property,
    Comparator,
    Date,
    FeatureVectorType,
    Float,
    ForeignKey,
    func,
    HSTORE,
    hybrid_property,
    Integer,
    Model,
    MolType,
    MutableDict,
    Numeric,
    NULL,
    PointType,
    relationship,
    Sequence,
    String,
    SurrogatePK,
    Table,
    text_type,
)

# TODO Break into modules

#############################################################################


class FdbUseCase(Model, SurrogatePK):

    name = Column('name', String, index=True)
    description = Column('description', String)

    citation_pmids = Column('citation_pmids', ARRAY(String, dimensions=1))

    def __repr__(self):
        return "<FdbUseCase(name={0!r}, description={0!r})>".format(self)


##############################################################################


class PDB(Model):
    __tablename__ = 'structure'

    id = Column('id', String(4), primary_key=True)
    title = Column('title', String)
    aa_sequence = Column('aa_sequence', String)
    # TODO: Add protein information
    # Look in to PostBIS

    def __repr__(self):
        return "<Structure(id={0.id!r}, code={0.code!r})>".format(self)


class Residue(Model):
    __tablename__ = 'residue'

    id = Column('id', String(1), primary_key=True)
    code = Column('code', String(3), unique=True, index=True, nullable=False)
    name = Column('name', String, nullable=False)
    smiles = Column('smiles', MolType)

    def __repr__(self):
        return "<Residue(id={0.id!r}, code={0.code!r})>".format(self)


class ResidueAtom(Model, SurrogatePK):
    __tablename__ = 'residue_atom'

    residue_fk = Column('residue_fk', ForeignKey(Residue.id), index=True, nullable=False)
    name = Column('code', String(3), index=True, nullable=False)
    element = Column('element', String(2), nullable=False)
    serial = Column('serial', Integer, doc="RDKit atom index")

    def __repr__(self):
        return "<ResidueAtom(id={0.id!r}, residue_fk={0.residue_fk!r}, name={0.name!r})>".format(self)


class StructureResidue(Model, SurrogatePK):
    __tablename__ = 'structure_residue'

    pdb_fk = Column('pdb_fk', ForeignKey(PDB.id), index=True, nullable=False)
    residue_fk = Column('residue_fk', ForeignKey(Residue.id), index=True, nullable=False)
    model_id = Column('model_id', Integer, default=1, server_default=1, nullable=False)
    chain_id = Column('chain_id', String(1), default='A', server_default='A', nullable=False)
    res_id = Column('res_id', Integer, nullable=False)

    structure = relationship(PDB,
                             viewonly=True,
                             backref=backref('residues',
                                             lazy='dynamic',
                                             order_by=(model_id, chain_id, res_id)))

    def __repr__(self):
        return "<StructureResidue(id={0.id!r}, pdb_fk={0.pdb_fk!r}, residue_fk={0.residue_fk!r})>".format(self)


###############################################################################


class Ligand(Model):
    __tablename__ = 'ligand'

    id = Column('id', String(3), primary_key=True, nullable=False)
    name = Column('name', String, index=True, nullable=False)
    smiles = Column('smiles', MolType, nullable=False, index=True, postgresql_using='gist')

    def __repr__(self):
        return "<Ligand(id={0.id!r}, name={0.name!r}, smiles={1!r})>".format(self, self.smiles.as_smiles)


class LigandAtom(Model, SurrogatePK):
    __tablename__ = 'ligand_atom'

    ligand_fk = Column('ligand_fk', String(3), ForeignKey(BoundLigand.id), index=True, nullable=False)
    name = Column('name', String(3), nullable=True)
    serial = Column('serial', Integer, doc="RDKit atom index")

    ligand = relationship(Ligand, backref=backref('atoms', order_by=serial))

    def __repr__(self):
        return "<LigandAtom(ligand_fk={0.ligand_fk!r}, name={0.name!r}, serial={0.serial!r})>".format(self)


class BoundLigand(Model, SurrogatePK):
    __tablename__ = 'bound_ligand'

    ligand_fk = Column('ligand_fk', ForeignKey(Ligand.id), nullable=False)
    pdb_fk = Column('pdb_fk', String(4), ForeignKey(PDB.id), index=True, nullable=False)
    model_idx = Column('model_idx', Integer, default=1, server_default=1, nullable=False)
    chain_idx = Column('chain_idx', String(1), default='A', server_default='A', nullable=False)
    res_idx = Column('residue_idx', Integer, nullable=False)

    pdb = relationship(PDB, backref=backref('ligands'))
    ligand = relationship(Ligand, backref=backref('conformations'))

    def __repr__(self):
        return "<BoundLigand(id={0.id!r}, ligand_fk={0.ligand_fk!r}, pdb_fk={0.pdf_fk!r})>".format(self)


class LigandConformation(Model, SurrogatePK):
    __tablename__ = 'ligand_conf'

    bound_lig_fk = Column('bound_lig_fk', Integer, ForeignKey(BoundLigand.id), nullable=False)
    atom_fk = Column('atom_fk', Integer, ForeignKey(LigandAtom.id), nullable=False)
    coords = Column('coords', PointType, nullable=False)
    atom_idx = Column('atom_idx', Integer, nullable=False)

    conformation = relationship(BoundLigand, backref=backref('conformation'))
    atom = relationship(LigandAtom, backref=backref('instances'))
    ligand = relationship(Ligand,
                          secondary=BoundLigand.__table__,
                          primaryjoin=lambda: LigandConformation.bound_lig_fk == BoundLigand.id,
                          secondarjoin=lambda: BoundLigand.ligand_fk == Ligand.id)

    def __repr__(self):
        return "<LigandConformation(id={0.id!r}, ligand_fk={0.ligand_fk!r}, atom_fk={0.atom_fk!r})>".format(self)


##############################################################################


class ActiveSiteGroup(Model, SurrogatePK):
    __tablename__ = 'activesitegroup'

    name = Column('name', String)
    description = Column('description', String)
    codes = association_proxy('sites', 'code')

    atoms_by_code = association_proxy('sites_by_code', 'atoms')
    atom_names_by_code = association_proxy('sites_by_code', 'atoms_names')

    def __repr__(self):
        return "<ActiveSiteGroup(id={0.id!r}, name={0.name!r})".format(self)


class ActiveSite(Model, SurrogatePK):
    __tablename__ = 'activesite'

    residue_fk = Column('residue_fk', ForeignKey(Residue.id), index=True, nullable=False)
    group_fk = Column('group_fk', ForeignKey(ActiveSiteGroup.id), index=True, nullable=False)
    serial = Column('serial', Integer, default=1, server_default=1, index=True, nullable=False)

    group = relationship(ActiveSiteGroup, backref=backref('sites'))
    __group = relationship(ActiveSiteGroup,
                           backref=backref('sites_by_code',
                                           collectionclass=attribute_mapped_collection('code')))
    atoms = relationship(ResidueAtom,
                         secondary=lambda: ActiveSiteAtomTable,
                         primaryjoin=lambda: ActiveSite.id == ActiveSiteAtomTable.activesite_fk,
                         secondaryjoin=lambda: ActiveSiteAtomTable.atom_fk == ResidueAtom.id)

    atom_names = association_proxy('atoms', 'name')
    group_name = association_proxy('group', 'name')

    class CodeComparator(Comparator):
        def __eq__(self, other):
            if isinstance(other, ActiveSite):
                other_fk, other_serial = other.residue_fk, other.serial
            else:
                if len(other) > 1:
                    other_fk, other_serial = other
                else:
                    other_fk, other_serial = other, 1
            return and_(self.residue_fk == other_fk, self.serial == other_serial)

        def __in__(self, other):
            if isinstance(other, (list, tuple, set)):
                residue_fks, serials = zip(*other)
                return and_(self.residue_fk in residue_fks, self.serial in serials)
            else:
                return (self.residue_fk, self.serial) in other

    @hybrid_property
    def code(self):
        if self.serial == 1:
            return text_type(self.residue_fk)
        else:
            return u"{0.residue_fk:s}{0.serial:d}".format(self)

    @code.setter
    def code(self, code):
        if len(code) > 1:
            res_fk, serial_str = code
            serial = int(serial_str)
        else:
            res_fk, serial = code, 1
        self.residue_fk = res_fk
        self.serial = serial

    @code.comparator
    def code(cls):
        return cls.CodeComparator(cls)

    def __str__(self):
        return self.code

    def __repr__(self):
        return "<ActiveSite(id={0.id!r}, residue_fk={0.residue_fk!r}, serial={0.serial!r}>".format(self)


ActiveSiteAtomTable = Table('activesite_atoms', Model.metadata,
    Column('activesite_fk', ForeignKey(ActiveSite.id), index=True, nullable=False),
    Column('atom_fk', ForeignKey(ResidueAtom.id), index=True, nullable=False)
)


#######################################################################################################################


class LigandPocketExtractionParameters(Model, SurrogatePK):
    __tablename__ = 'extraction_params'

    name = Column('name', String)

    site_distance_default_cutoff = Column('site_distance_default_cutoff', Float)
    site_group_distance_overrides = Column('site_group_distance_overrides', MutableDict.as_mutable(HSTORE))
    force_model_id = Column('force_model_id', Integer, nullable=True, default=1, server_default=1)
    force_chain_id = Column('force_chain_id', Integer, nullable=True, default=None, server_default=NULL)

    excluded_ligands = relationship(Ligand,
                                    secondary=lambda: ExtractionExcludedLigandsTable,
                                    primaryjoin=lambda: LigandPocketExtractionParameters.id == \
                                                        ExtractionExcludedLigandsTable.params_fk,
                                    secondaryjoin=lambda: ExtractionExcludedLigandsTable.ligand_fk == Ligand.id,
                                    backref=backref('excluded_from_extraction'))

    active_site_groups = relationship(ActiveSiteGroup,
                                      secondary=lambda: ExtractionActiveSiteGroupsTable,
                                      primaryjoin=lambda: LigandPocketExtractionParameters.id == \
                                                          ExtractionActiveSiteGroupsTable.params_fk,
                                      secondaryjoin=lambda: \
                                          ExtractionActiveSiteGroupsTable.group_fk == ActiveSiteGroup.id,
                                      collection_class=attribute_mapped_collection('name'),
                                      backref=backref('used_in_extraction_params'))

    excluded_ligand_names = association_proxy('excluded_ligands', 'name')
    grouped_active_sites = association_proxy('active_site_groups', 'sites_by_code')
    grouped_active_site_atoms = association_proxy('active_site_groups', 'atom_names_by_code')

    def __repr__(self):
        return "<PocketExtractionParameters(id={0.id!r}, name={0.name!})>".format(self)


ExtractionExcludedLigandsTable = Table('extraction_excluded_ligand', Model.metadata,
    Column('params_fk', ForeignKey(LigandPocketExtractionParameters.id), index=True, nullable=False),
    Column('ligand_fk', ForeignKey(Ligand.id), index=True, nullable=False)
)


ExtractionActiveSiteGroupsTable = Table('extraction_active_site_groups', Model.metadata,
    Column('params_fk', ForeignKey(LigandPocketExtractionParameters.id), index=True, nullable=False),
    Column('group_fk', ForeignKey(ActiveSiteGroup.id), index=True, nullable=False)
)


######################################################################################################################


class MicroEnvironmentGroupSource(Model):
    pass


class MicroEnvironmentGroup(Model):
    __tablename__ = 'featurevectorset'

    FEATURE_VECTOR_SET_TYPE = [
        (u'V', u'FEATURE Vector Set'),
        (u'L', u'Ligand Pocket'),
        (u'I', u'Protein Protein Interface'),
    ]

    id = Column('id', Integer, nullable=False, primary_key=True)
    structure_fk = Column('pdb_fk', String(4), ForeignKey(PDB.pdb), nullable=False, index=True)

    name = Column('name', String, default='', server_default='', nullable=False)
    comment = Column('comment', String, default='', server_default='', nullable=False)
    origin = Column('origin', ChoiceType(FEATURE_VECTOR_SET_TYPE),
                    default='V', server_default='V',
                    index=True, nullable=False)

    pdb = relationship(PDB,
                       backref=backref('microenvironment_groups',
                                       lazy='dynamic'))

    __mapper_args__ = {
        'polymorphic_on': origin,
        'polymorphic_identity': u'V',
        'with_polymorphic': '*',
    }

    @hybrid_property
    def pdbid(self):
        return self.structure_fk

    @pdbid.comparator
    def pdbid(cls):
        return cls.structure_fk


class LigandPocket(MicroEnvironmentGroup):
    __tablename__ = 'pocket'

    id = Column('id', ForeignKey(MicroEnvironmentGroup.id), nullable=False, primary_key=True)
    source_ligand_fk = Column('source_ligand_fk', ForeignKey(BoundLigand.id), nullable=False, index=True)
    parameters_fk = Column('parameters_fk', ForeignKey(LigandPocketExtractionParameters), nullable=False, index=True)

    source_ligand = relationship(BoundLigand,
                                 backref=backref('pockets', lazy='dynamic'))
    parameters = relationship(LigandPocketExtractionParameters,
                              backref=backref('extracted_pockets', lazy='dynamic'))

    __pdb = relationship(PDB, backref=backref('pockets', lazy='dynamic'))
    ligand = association_proxy('source_ligand', 'ligand')

    ligand_id = association_proxy('source_ligand', 'ligand_fk')
    ligand_name = association_proxy('source_ligand', 'ligand_name')

    __mapper_args__ = {
        'polymorphic_identity': u'L',
    }

    def __repr__(self):
        return "<LigandPocket(id={0.id!r}, pdbid={0.pdbid!r}, source_ligand_fk={0.source_ligand_fk!r})>".format(self)


#######################################################################################################################


class MicroEnvironment(Model):
    __tablename__ = 'microenvironment'

    MICROENVIRONMENT_ORIGIN_TYPE = [
        (u'M', u'Microenvironment (Default)'),
        (u'R', u'Residue Active Site'),
        (u'A', u'Explicit Atom'),
        (u'C', u'Manually Curated'),
        (u'S', u'SeqFEATURE Defined'),
        (u'O', u'Other Environment'),
    ]

    id = Column('id', Integer, primary_key=True)
    structure_fk = Column('pdb_fk', String(4), ForeignKey(PDB.pdb), index=True)
    name = Column('name', String)

    coords = Column('coords', PointType, nullable=False)
    comment = Column('comment', String, default='', server_default='')

    group_fk = Column('group_fk', ForeignKey(MicroEnvironmentGroup.id), index=True, nullable=False)
    origin = Column('type', ChoiceType(MICROENVIRONMENT_ORIGIN_TYPE), index=True)

    pdb = relationship(PDB,
                       backref=backref('microenvironments', lazy='dynamic'))
    group = relationship(MicroEnvironmentGroup,
                         backref=backref('microenvironments', lazy='dynamic'))

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
        'polymorphic_identity': u'R',
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
    parameters_fk = Column('parameters_fk', ForeignKey(FeatureVectorParameters.id), index=True)
    features = Column('features', FeatureVectorType)

    microenvironment = relationship(MicroEnvironment, backref=backref('features'))
    microenvironment_set = relationship(MicroEnvironmentGroup,
                                        secondary=MicroEnvironment.__table__,
                                        backref=backref('features'))
    parameters = relationship(FeatureVectorParameters,
                              backref=backref('features', lazy='dynamic'))

    @hybrid_property
    def z_features(self):
        params = self.parameters
        if params is None:
            raise ValueError("Cannot calculate Z-Scores without parameters")
        return (self.features - params.mean) / params.std


#####################################################################################################################


class Fragment(Model):
    __tablename__ = 'fragment'

    pubchem_id = Column('pubchem_id', Integer, nullable=False, primary_key=True)
    smiles = Column('smiles', MolType, nullable=False, index=True, postgreql_using='gist')
    parent_srk = Column('parent_srk', ForeignKey(pubchem_id), index=True)
    in_use = Column('in_use', Boolean, nullable=False, default=False, server_default=False, index=True)

    children  = relationship(lambda: Fragment,
                           backref=backref('parent', remote_side=(pubchem_id,)))

    all_children = relationship(lambda: Fragment,
                                lazy='joined',
                                join_depth=5,
                                backref=backref('all_parents',
                                                lazy='joined',
                                                join_depth=5,
                                                remote_side=(pubchem_id,)))

    def __repr__(self):
        return "<Fragment(pubchem_id={0.pubchem_id!r}, smiles={1!r}, parent_srk={0.parent_srk!r})>"\
                    .format(self, self.smiles.as_smiles)


class LigandFragmentAtoms(Model, SurrogatePK):
    __tablename__ = 'ligand'

    ligand_fk = Column('ligand_fk', ForeignKey(Ligand.id), nullable=False)
    pubchem_fk = Column('pubchem_fk', ForeignKey(Fragment.pubchem_id), nullable=False)

    # Mapping of Ligand ID to Fragment ID
    raw_atom_idx_map = Column('atom_idx_map', HSTORE, nullable=False)

    @hybrid_property
    def atom_idx_map(self):
        return {int(k): int(v) for k, v in self.raw_atom_idx_map.iteritems()}

    @atom_idx_map.setter
    def atom_idx_map(self, value):
        self.raw_atom_idx_map = {text_type(k): text_type(v) for k, v in dict(value).iteritems()}

    @atom_idx_map.comparator
    def atom_idx_map(cls):
        # TODO: Implement text<->mappings
        return cls.raw_atom_idx_map

    ligand_atom_indexes = column_property(func.array_to_intarray(func.akeys(raw_atom_idx_map)))
    fragment_atom_indexes = column_property(func.array_to_intarray(func.akeys(raw_atom_idx_map)))

    num_ligand_atoms_mapped = column_property(func.array_length())

    def __repr__(self):
        return "<LigandFragmentAtoms(ligand_fk={0.ligand_fk!r}, pubchem_fk={0.pubchem_fk!r})>".format(self)
