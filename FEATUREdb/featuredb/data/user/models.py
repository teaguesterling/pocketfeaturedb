# -*- coding: utf-8 -*-
from datetime import datetime

from flask.ext.login import UserMixin
from drake.compat import text_type
from drake.extensions import bcrypt
from ..binds import AccessModel
from ..core import (
    backref,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    hybrid_property,
    relationship,
    Sequence,
    String,
)

__all__ = [
    'User',
    'Role',
    'UserRole',
]


class User(UserMixin, AccessModel):
    __tablename__ = 'users'

    id = Column('id', Sequence, primary_key=True, nullable=False)
    username = Column('username', String(80), unique=True, nullable=False)
    email = Column('email', String(80), unique=True, nullable=False)

    password_hash = Column('password_hash', String(128), nullable=True)
    created_at = Column('created_at', DateTime, nullable=False, default=datetime.utcnow)
    first_name = Column('first_name', String(30), nullable=True)
    last_name = Column('las_name', String(30), nullable=True)
    active = Column('active', Boolean(), default=False)
    is_admin = Column('is_admin', Boolean(), default=False)

    def __init__(self, username, email, password=None, **kwargs):
        super(User, self).__init__(self, username=username, email=email, **kwargs)
        self.password = password

    @property
    def is_active(self):
        return self.active

    @property
    def is_authenticated(self):
        return True

    def get_id(self):
        if self.user_id is not None:
            return text_type(self.user_id)
        else:
            return None

    @hybrid_property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, raw):
        if raw is None:
            self.password_hash = None
        else:
            hash = bcrypt.generate_password_hash(raw)
            self.password_hash = hash

    @password.expression
    def password(cls, raw):
        hash = bcrypt.generate_password_hash(raw)
        return cls.password_hash == hash

    def check_password(self, value):
        return bcrypt.check_password_hash(self.password, value)

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name)

    def __repr__(self):
        return '<User({username!r})>'.format(username=self.username)


class Role(AccessModel):
    __tablename__ = 'roles'

    role_id = Column('role_id', Sequence, primary_key=True, nullable=False)
    name = Column('name', String(80), unique=True, nullable=False)
    users = relationship(User,
                         backref=backref('roles'),
                         secondary=lambda:UserRole.__table___)

    def __init__(self, name, **kwargs):
        AccessModel.__init__(self, name=name, **kwargs)

    def __repr__(self):
        return '<Role(name={name})>'.format(name=self.name)


class UserRole(AccessModel):
    __tablename__ = 'user_role'

    user_role_id = Column('user_rol_id', Sequence, primary_key=True, nullable=False)
    user_fk = ForeignKey('user_fk', User.user_id)
    role_fk = ForeignKey('role_fk', Role.role_id)

    user = relationship(User)
    role = relationship(Role, backref=backref('user_mappings', viewonly=True))

    def __init__(self, **kwargs):
        if 'role' in kwargs:
            role = kwargs.pop('role')
            kwargs['role_fk'] = role.role_id if isinstance(role, Role) else role
        if 'user' in kwargs:
            user = kwargs.pop('user')
            kwargs['user_fk'] = user.user_id if isinstance(user, User) else user
        AccessModel.__init__(**kwargs)

    def __repr__(self):
        return '<UserRole(role_fk={role}, user_fk={user})>'.format(role=self.role_fk, user=self.user_fk)

