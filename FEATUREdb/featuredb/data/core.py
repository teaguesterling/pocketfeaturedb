# noinspection PyUnresolvedReferences
from __future__ import absolute_import

from datetime import datetime as dt
import warnings

import numpy as np

from sqlalchemy import (
    Boolean,
    cast,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    func,
    Integer,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    Sequence,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.sql import (
    and_,
    or_,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import (
    Comparator,
    hybrid_property,
    hybrid_method,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import (
    backref,
    column_property,
    foreign,
    join,
    mapper,
    remote,
)
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import (
    NoResultFound,
    MultipleResultsFound,
)

from sqlalchemy.dialects.postgresql import (
    ARRAY,
    array,
    HSTORE,
    hstore,
)
from sqlalchemy.sql.elements import NULL

from sqlalchemy_utils.types import (
    ArrowType,
    ChoiceType,
    IPAddressType,
    JSONType,
    EncryptedType,
)

from ..compat import (
    binary_type,
    text_type,
)


Now = text('NOW()')


class CollectionArray(ARRAY):
    def __init__(self, item_type,
                 collection_type=list,
                 dimensions=None,
                 zero_indexes=False):
        super(CollectionArray, self).__init__(item_type,
                                              as_tuple=True,
                                              dimensions=dimensions,
                                              zero_indexes=zero_indexes)
        self.collection_type = collection_type

    @property
    def python_type(self):
        if isinstance(self.collection_type, type):
            return self.collection_type
        elif self.as_tuple:
            return tuple
        else:
            return list

    def _proc_array(self, arr, itemproc, dim, collection):
        processed = super(CollectionArray, self)._proc_array(arr, itemproc, dim, collection)
        if dim is None:
            return collection(processed)
        else:
            return processed

    def result_processor(self, dialect, coltype):
        item_proc = self.item_type.\
            dialect_impl(dialect).\
            result_processor(dialect, coltype)

        def process(value):
            if value is None:
                return value
            else:
                return self._proc_array(
                    value,
                    item_proc,
                    self.dimensions,
                    self.collection_type)
        return process


FeatureVectorType = CollectionArray(Float,
                                    collection_type=np.array,
                                    zero_indexes=True)

try:
    from geoalchemy2 import Geometry
    PointType = Geometry(geometry_type='POINT', dimension=3)
except ImportError:
    warnings.warn("Geoalchemy not available for Geometry types")
    PointType = ARRAY(Float, dimensions=3, as_tuple=True)

try:
    from rdalchemy.rdalchemy import MolType as MolType
except ImportError:
    warnings.warn("RDAlchemy not available for molecule types")
    MolType = String

from featuredb.extensions import db



dynamic_loader = db.dynamic_loader
event = db.event
relation = db.relation
relationship = db.relationship
Table = db.Table

Model = db.Model
Query = db.Query
Session = db.Session


class SurrogatePK(object):
    id = Column('id', Integer, primary_key=True, nullable=False)
    __table_args__ = {
        'extend_existing': True,
    }


class ArrowTimestamp(object):
    """Adds `created` and `updated` columns to a derived declarative model.

    The `created` column is handled through a default and the `updated`
    column is handled through a `before_update` event that propagates
    for all derived declarative models.

    ::
        import sqlalchemy as sa
        from sqlalchemy_utils import Timestamp


        class SomeModel(Base, Timestamp):
            __tablename__ = 'somemodel'
            id = sa.Column(sa.Integer, primary_key=True)
    """

    created = Column(ArrowType, server_default=Now, default=dt.utcnow, nullable=False)
    updated = Column(ArrowType, server_default=Now, default=dt.utcnow, nullable=False)


@event.listens_for(ArrowType, 'before_update', propagate=True)
def timestamp_before_update(mapper, connection, target):
    # When a model with a timestamp is updated; force update the updated
    # timestamp.
    target.updated = dt.utcnow()
