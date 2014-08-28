from sqlalchemy import (
    Boolean, 
    Column, 
    Date,
    Float,
    ForeignKey, 
    Integer, 
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
    Coords = ARRAY[Float]

FeatureDbBase = declarative_base()

