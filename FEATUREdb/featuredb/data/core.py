# noinspection PyUnresolvedReferences

from datetime import datetime as dt

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
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import (
    Comparator,
    hybrid_property,
    hybrid_method,
)
from sqlalchemy.orm import (
    backref,
    foreign,
    join,
    mapper,
    remote,
)
from sqlalchemy.orm.exc import (
    NoResultFound,
    MultipleResultsFound,
)

from sqlalchemy.dialects.postgresql import (
    ARRAY,
    JSON,
)

from sqlalchemy_utils.types import (
    ArrowType,
    IPAddressType,
    JSONType,
    EncryptedType,
)

from featuredb.extensions.sqla import DynamicBindMixin
from drake.extensions import db

Null = text('NULL')
Now = text('NOW()')

BaseModel = db.Model
Query = db.Query
Session = db.Session

dynamic_loader = db.dynamic_loader
event = db.event
relation = db.relation
relationship = db.relationship
Table = db.Table


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
