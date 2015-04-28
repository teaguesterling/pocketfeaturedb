from sqlalchemy.orm import class_mapper

try:
    from flask.ext.sqlalchemy import Model as BaseModel
except ImportError:
    import warnings
    warnings.warn("Flask-SQLAlchemy not present! Using standard SQLAlchemy base classes")
    BaseModel = object

from .query import Query
from .errors import abort_not_found


class SimpleGetMixin(object):
    __primary_key = None
    GET_BY_TYPE_MAP = {}

    @classmethod
    def get_primary_key(cls):
        if cls.__primary_key is None:
            mapper = class_mapper(cls)
            pk = mapper.primary_key
            if len(pk) == 1:
                cls.__primary_key = pk[0]
            else:
                cls.__primary_key = pk
        return cls.__primary_key

    @property
    def pk(self):
        pk = self.__mapper__.primary_key
        if len(pk) == 1:
            return pk[0]
        else:
            return tuple(pk)

    @classmethod
    def get(cls, value, onerror=abort_not_found):
        return cls.query.get(value, onerror=onerror)

    @classmethod
    def lookup(cls, value, onerror=abort_not_found):
        return cls.query.lookup(value, onerror=onerror)


class Model(SimpleGetMixin, BaseModel):
    query_class = Query


