import contextlib

try:
    from flask.ext.sqlalchemy import SignallingSession as BaseSession
except ImportError:
    import warnings
    warnings.warn("Flask-SQLAlchemy not present! Using standard SQLAlchemy base classes")
    from sqlalchemy.orm import Session as BaseSession


class TransactionContextMixin(object):
    @property
    @contextlib.contextmanager
    def in_transaction(self):
        transaction = None
        try:
            transaction = self.session.begin(subtransactions=True)
            yield self, transaction
        except Exception:
            if transaction is not None:
                transaction.rollback()
            raise

    @property
    @contextlib.contextmanager
    def in_nested_transaction(self):
        transaction = None
        try:
            transaction = self.session.begin_nested()
            yield self, transaction
        except Exception:
            if transaction is not None:
                transaction.rollback()
            raise


class PostInitSessionQuery(object):
    def query(self, *entities, **kwargs):
        query = super(type(self), self).query(*entities, **kwargs)
        db = self.app.extensions.get('sqlalchemy')
        if hasattr(db, 'init_query'):
            query = db.init_query(query)
        return query


class Session(PostInitSessionQuery,
              TransactionContextMixin,
              BaseSession):
    pass
