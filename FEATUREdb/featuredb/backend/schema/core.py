import warnings
from sqlalchemy import (
    Boolean, 
    Column, 
    Date,
    Float,
    ForeignKey,
    func, 
    Integer, 
    MetaData,
    Numeric,
    String, 
)
from sqlalchemy.orm import (
    backref,
    relationship, 
)
from sqlalchemy.ext.declarative import (
    declarative_base,
    declared_attr,
)
from sqlalchemy.dialects.postgresql import ARRAY

try:
    from geoalchemy2 import Geometry
    Coords = Geometry(geometry_type='POINT', dimension=3)
except ImportError:
    warnings.warn("Geoalchemy not available for Geometry types")
    Coords = ARRAY[Float]

try:
    from rdalchemy.rdalchemy import Mol
    Molecule = Mol
except ImportError:
    warnings.warn("RDAlchemy not available for molecule types")
    Molecule = String

metadata = MetaData()
Base = declarative_base(metadata=metadata)

