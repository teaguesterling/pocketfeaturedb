import functools

from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import Query as ORMQuery
try:
    from flask.ext.sqlalchemy import (
        BaseQuery,
        Pagination,
    )
except ImportError:
    import warnings
    warnings.warn("Flask-SQLAlchemy not present! Using standard SQLAlchemy base classes")
    from sqlalchemy.orm import Query as BaseQuery

    def Paginaition(*args, **kwargs):
        raise NotImplementedError("Pagination not supported without Flask-SQLAlchemy")


from .errors import abort_not_found


class LookupQueryMixin(object):

    @property
    def datatype(self):
        return self._entities[0]

    def lookup_or_error(self, key, onerror=abort_not_found):
        target = self.datatype
        lookup_map = getattr(target, 'GET_BY_TYPE_MAP', {})
        key_type = type(key)
        try:
            column = lookup_map[key_type]
        except KeyError:
            try:
                pk_type = type(target.get_primary_key())
                if key_type == type(pk_type) or issubclass(key_type, pk_type):
                    return self.get_or_error(key, onerror=onerror)
            except (TypeError, AttributeError):
                pass
            raise NotImplementedError("Cannot 'lookup' {} with type {}".format(target, key_type))

        rv = self.filter(column == key).first()
        if rv is None and onerror:
            onerror()
        return rv


    def get_or_error(self, key, onerror=abort_not_found):
        rv = self.get(key)
        if rv is None and onerror:
            onerror()
        return rv

    def first_or_error(self, onerror=abort_not_found):
        rv = self.first()
        if rv is None and onerror:
            onerror()
        return rv


class PaginateQueryMixin(object):
    def paginate(self, page, per_page=20, error_out=True, onerror=abort_not_found):
        """Returns `per_page` items from page `page`.  By default it will
        abort with 404 if no items were found and the page was larger than
        1.  This behavor can be disabled by setting `error_out` to `False`.
        Returns an :class:`Pagination` object.
        """
        if error_out and page < 1 and onerror is not None:
            onerror()
        items = self.limit(per_page).offset((page - 1) * per_page).all()
        if not items and page != 1 and error_out and onerror is not None:
            onerror()

        # No need to count if we're on the first page and there are fewer
        # items than we expected.
        if page == 1 and len(items) < per_page:
            total = len(items)
        else:
            total = self.order_by(None).count()

        return Pagination(self, page, per_page, total, items)


class JoinSearchMixin(object):
    #TODO: Integrate join path
    pass


class AnnotateMixin(object):
    _annotations = ()

    def annotate(self, key, expr):
        existing_annotations = self._annotations
        new_annotations = existing_annotations + (key,)

        query = self.add_column(expr)
        query._annotations = new_annotations

        return query

    def __iter__(self):
        base_iter = super(AnnotateMixin, self).__iter__()
        if not self._annotations:
            return base_iter
        else:
            def gen():
                labels = self._annotations
                for row in base_iter:
                    item, annotations = row[0], row[1:]
                    for key, value in zip(labels, annotations):
                        setattr(item, key, value)
                    yield item
            return gen()


class Query(AnnotateMixin,
            JoinSearchMixin,
            Pagination,
            LookupQueryMixin,
            BaseQuery):
    pass
