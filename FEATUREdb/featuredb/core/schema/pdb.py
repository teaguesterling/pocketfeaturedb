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
    FeatureDbBase,
)


class ResidueType(FeatureDbBase):
    __tablename__ = 'residuetype'

    code = Column('single', String(1), primary_key=True)
    short = Column('short', String(3), index=True)
    name = Column('name', String)


class Structure(FeatureDbBase):
    __tablename__ = 'structure'

    id = Column('id', String(4), nullable=False, primary_key=True)
    title = Column('title', String)
    uniprot = Column('uniprot', String, index=True)


class Residue(FeatureDbBase):
    __tablename__ = 'residue'

    id = Column('id', Integer, primary_key=True)
    pdb = Column('structure', String(4), ForeignKey(Structure.id), index=True)
    restype = Column('restype', String(1), ForgeignKey(ResidueType.code), index=True)
    chain = Column('chain', String(1))
    resid = Column('resid', Integer)


class ActiveSiteType(FeatureDbBase):
    __tablename__ = 'activesitetype'

    code = Column('code', String(2), primary_key=True)
    restype = Column('restype', String(1), ForgeignKey(ResidueType.code), index=True)
    index = Column('index', Integer, index=True)

    def __str__(self):
        return self.code


class ActiveSiteAtom(FeatureDbBase):
    __tablename__ = 'activesiteatom'

    id = Column('id', Integer, primary_key=True)
    residue = Column('residue', String(2), ForgeignKey(ActiveSiteType.code), index=True)
    atom = Column('atom', String(3), index=True)


class Microenvironment(FeatureDbBase):
    __tablename__ = 'microenvironment'
    
    id = Column('id', Integer, primary_key=True)
    structure = Column('pdb', String(4), ForeignKey(Structure.pdb, index=True))
    resdue = Column('residue', Integer, ForeignKey(Residue.id))
    name = Column('name', String)
    site = Column('site', Integer, ForeignKey(ActiveSiteAtom.id), index=True, nullable=True)
    atom = Column('atom', String(3), nullable=True)
    coords = Column('coords', Point)
    comment = Column('comment', String, default="")


class FeatureVector(FeatureDbBase):
    __tablename__ = 'featurevector'

    id = Column('id', Integer, primary_key=True)
    microenvironment = Column('microenvironment', Integer, ForeignKey(Microenvironment.id), index=True)
    features = Column('features', ARRAY(Float))
    representation = Column('representation', Integer)  # Should reference new table


class Ligand(FeatureDbBase):
    __tablename__ = 'ligand'

    id = Column('id', String(3), primary_key=True)
    name = Column('name', String, index=True)
    smiles = Column('smiles', String)  # TODO: Should be rdkit::mol
    #TODO: PubChem ID


class LigandAtom(FeatureDbBase):
    __tablename__ = 'ligandatom'

    id = Column('id', Integer, primary_key=True)
    ligand = Column('ligand', String(3), ForeignKey(Ligand.id))
    element = Column('element', String(2))
    name = Column('name', String)


class LigandInstance(FeatureDbBase)
    __tablename__ = 'ligandinstance'

    id = Column('id', Integer, primary_key=True)
    ligand = Column('ligand', String(3), ForeignKey(Ligand.id))
    pdb = Column('pdb', String(4), ForeignKey(Structure.id), index=True)
    chain = Column('chain', String(1), default='A')
    residue = Column('residue', Integer)


class LigandConformation(FeatureDbBase):
    __tablename__ = 'ligandconformation'

    id = Column('id', Integer, primary_key=True)
    ligand = Column('ligand', Integer, ForeignKey(LigandInstance.id))
    atom = Column('atom', Integer, ForeignKey(LigandAtom.id))
    atom_id = Column('atom_id', Integer)
    coords = Column('coords', Point)


class Pocket(FeatureDbBase):
    
