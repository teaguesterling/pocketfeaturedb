from flask import current_app
from .core import (
    ArrowTimestamp,
    BaseModel,
    Column,
    declared_attr,
    DynamicBindMixin,
    ForeignKey,
    relationship,
    Sequence,
    String,
)

ACCESS_BIND = 'access'
CASE_DATA_BIND = 'case'


class AccessModel(BaseModel):
    __abstract__ = True
    __bind_key__ = ACCESS_BIND


class Tenant(AccessModel):
    id = Column('id', Sequence, primary_key=True, nullable=False)
    key = Column('key', String, unique=True, index=True, nullable=False)

    def get_bind_config(self):
        if not hasattr(self, '__bind_defn'):
            self.__bind_defn = TenantBind(self)
        return self.__bind_defn


class TenantBind(DynamicBindMixin):
    def __init__(self, tenant):
        self.__tenant = tenant

    def init_session(self, app, session):
        session.execute("SET search_path TO :schema", {'schema': self.__tenant.key})

    def init_query(self, query):
        if self.__tenant and self.__tenant.id:
            entities = query._entities
            tenant_entities = [ent for ent in entities if _is_tenant_entity(ent)]
            if len(tenant_entities) > 0:
                query = query.filter(*(ent.tenant_fk == self.__tenant.id for ent in tenant_entities))
        return query


class CaseModel(BaseModel, ArrowTimestamp):
    __abstract__ = True
    __bind_key__ = CASE_DATA_BIND

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('tenant_fk', )

    @declared_attr
    def tenant_fk(cls):
        return Column('tenant_fk', ForeignKey(Tenant.id))

    @declared_attr
    def tenant(cls):
        return relationship('Tenant')


def _is_tenant_entity(entity):
    # TODO: Add column level checks
    if isinstance(entity, CaseModel):
        return True
    else:
        return False

