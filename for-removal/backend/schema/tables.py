from .core import (
    ARRAY,
    backref,
    Boolean,
    ChemColumn, 
    Column, 
    Coords,
    Date,
    Float,
    ForeignKey, 
    Integer,
    Molecule,
    Numeric,
    relationship,
    String, 
    Base,
)


class Gene(Base):
    __tablename__ = 'gene'

    id = Column('id', Integer, primary_key=True)
    code = Column('code', String(15), index=True, nullable=False)
    description = Column('description', String)


class Target(Base):
    __tablename__ = 'target'

    id = Column('id', Integer, primary_key=True)
    chemblid = Column('chemblid', String(25), index=True, nullable=False)



##############################################################################


class Structure(Base):
    __tablename__ = 'structure'

    id = Column('id', Integer, primary_key=True)
    code = Column('code', String(4), nullable=False)
    title = Column('title', String)


class Residue(Base):
    __tablename__ = 'residue'

    id = Column('single', String(1), primary_key=True)
    short = Column('short', String(3), index=True)
    name = Column('name', String)


class ResidueAtom(Base):
    __tablename__ = 'residue_atom'

    id = Column('id', String(3), primary_key=True)
    residue_fk = Column('residue_fk', String(1), ForgeinKey(Residue.id), index=True)
    element = Column('element', String(2)


class StructureResidue(Base):
    __tablename__ = 'structure_residue'

    id = Column('id', Integer, primary_key=True)
    pdb_fk = Column('structure_fk', String(4), ForeignKey(Structure.id), index=True)
    residue_fk = Column('residue_fk', String(1), ForgeignKey(Residue.id), index=True)
    chain_id = Column('chain', String(1))
    res_id = Column('resid', Integer)


###############################################################################


class Ligand(Base):
    __tablename__ = 'ligand'

    id = Column('id', String(3), primary_key=True)
    name = Column('name', String, index=True)
    smiles = Column('smiles', Molecule)  # TODO: Should be rdkit::mol
    #TODO: PubChem ID


class LigandAtom(Base):
    __tablename__ = 'ligandatom'

    id = Column('id', Integer, primary_key=True)
    ligand_fk = Column('ligand_fk', String(3), ForeignKey(PdbLigand.id))
    element = Column('element', String(2))
    name = Column('name', String)


class LigandInstance(Base)
    __tablename__ = 'ligandinstance'

    id = Column('id', Integer, primary_key=True)
    ligand_fk = Column('ligand_fk', String(3), ForeignKey(Ligand.id))
    pdb_fk = Column('pdb_fk', String(4), ForeignKey(Structure.id), index=True)
    chain_id = Column('chain', String(1))
    res_id = Column('residue', Integer)


class LigandConformation(Base):
    __tablename__ = 'ligandconformation'

    id = Column('id', Integer, primary_key=True)
    ligand = Column('ligand', Integer, ForeignKey(LigandInstance.id))
    atom = Column('atom', Integer, ForeignKey(LigandAtom.id))
    atom_id = Column('atom_id', Integer)
    coords = Column('coords', Point)


##############################################################################


class ActiveSite(Base):
    __tablename__ = 'activesitetype'

    code = Column('code', String(2), primary_key=True)
    residue_fk = Column('residue_fk', String(1), ForgeignKey(Residue.id), index=True)
    number = Column('number', Integer, index=True)
    kind_fk = Column('kind_fk', Integer, ForeignKey(ActiveSiteKind.id), index=True)

    def __str__(self):
        return self.code


class ActiveSiteAtom(Base):
    __tablename__ = 'activesiteatom'

    id = Column('id', Integer, primary_key=True)
    activesite_fk = Column('activesite_fk', String(2), ForgeinKey(ActiveSite.code), index=True)
    atom_fk = Column('atom_fk', String(3), ForeignKey(ResidueAtom.id) index=True)


class Microenvironment(Base):
    __tablename__ = 'microenvironment'
    
    id = Column('id', Integer, primary_key=True)
    structure_fk = Column('pdb_fk', String(4), ForeignKey(Structure.pdb, index=True))
    name = Column('name', String)
    
    coords = Column('coords', Point)
    comment = Column('comment', String, default="")

    envronment_type = Column('type', String(15), index=True)

    __mapper_args__ = {
        'polymorphic_on': environment_type,
        'polymorphic_identity': 'microenvironment',
        'with_polymorphic': '*',
    }


class ActiveSiteEnvironment(Base):
    __tablename__ = 'activesite_microenvironment'

    id = Column('id', Integer, ForeignKey(Microenvironment.id), primary_key=True)
    site_fk = Column('site_fk', Integer, ForeignKey(ActiveSite.id), index=True)
    structue_residue_fk = Column('structure_residue_fk', Integer, ForeignKey(StructureResidue.id), index=True)

    __mapper_args__ = {
        'polymorphic_identity': 'activesite',
    }


class AtomEnvironment(Base):
    __tablename__ = 'atom_microenviroment'

    id = Column('id', Integer, ForeignKey(Microenvironment.id), primary_key=True)
    residue_fk = Column('residue_fk', String(1), ForeignKey(Residue.id), index=True)
    atom_fk = Column('atom_fk', String(3), ForeignKey(ResidueAtom.id), index=True)
    atom_index = Column('atom_number', Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'atom',
    }


class CuratedEnvironment(Base):
    __tablename__ = 'curated_microenvironment'

    id = Column('id', Integer, ForeignKey(Microenvironment.id), primary_key=True)
    notes = Column('notes', String)

    __mapper_args__ = {
        'polymorphic_identity': 'curated',
    }


class FeatureVector(Base):
    __tablename__ = 'featurevector'

    id = Column('id', Integer, primary_key=True)
    microenvironment_fk = Column('microenvironment_fk', Integer, ForeignKey(Microenvironment.id), index=True)
    features = Column('features', ARRAY(Float))
    representation = Column('representation', Integer)  # Should reference new table


class Pocket(Base):
    pass

