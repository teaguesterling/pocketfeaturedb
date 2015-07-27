from __future__ import absolute_import

import copy
from collections import OrderedDict
import operator

from six import (
    string_types,
    iteritems,
)

from feature.io.common import attempt_cast


CONTAINER_TYPES = (list, set, dict)


def update_metadata_value(existing, value):
    if existing is None:
        return value

    existing_type = type(existing)
    if isinstance(existing, CONTAINER_TYPES):
        if not isinstance(value, CONTAINER_TYPES):
            value = [value]
        if hasattr(existing, 'redefine'):
            existing = existing.redefine(value)
        elif hasattr(existing, 'extend'):
            existing.extend(value)
        elif hasattr(existing, 'update'):
            existing.update(value)
        else:
            raise ValueError("Can't update container type {!r}".format(existing_type))
        return existing
    else:
        value = existing_type(value)
        return value



class MetaData(OrderedDict):

    def __init__(self, items=(), defaults=None, *args, **kwargs):
        super(MetaData, self).__init__(*args, **kwargs)
        if defaults is not None:
            self.update(copy.deepcopy(defaults))
        if hasattr(items, 'items'):
            items = items.items()
        for key, item in items:
            self[key] = item

    def modify(self, key, value):
        existing = self[key]
        changed = update_metadata_value(existing, value)
        self[key] = changed
        return self[key]

    def set_raw(self, key, value):
        value = str(value)

        if "," in value:
            value = value.strip(",\n ")
            value = [s.strip() for s in value.strip(", \n").split(",")]

        if key in self:
            existing = self[key]
            existing_type = type(existing)
            if not isinstance(existing, (list, set, dict)):
                value = existing_type(value)
        elif isinstance(value, CONTAINER_TYPES):
            casts = [attempt_cast(v, default=str) for v in value]
            value = map(operator.itemgetter(1), casts)
        elif isinstance(value, string_types):  # Parsed above
            new_type, value = attempt_cast(value, default=str)
        else:
            raise ValueError("Received unexpected raw type (should be string)")

        if key in self:
            return self.modify(key, value)
        else:
            self[key] = value
            return self[key]

    def set_raw_fields(self, fields):
        for key, value in fields:
            self.set_raw(key, value)
        return self

    def propagate(self, kind=None, **kwargs):
        kind = kind or type(self)
        metadata = kind(self)
        metadata.update(kwargs)
        return metadata


    @classmethod
    def from_raw_fields(cls, fields, defaults=None, *args, **kwargs):
        kwargs.setdefault('defaults', defaults)
        obj = cls(*args, **kwargs)
        obj.set_raw_fields(fields)
        return obj

    @classmethod
    def update_defaults(cls, _defaults=None, _extend_lists=True, **changes):
        defaults = _defaults or getattr(cls, 'DEFAULTS', {})
        for key, value in iteritems(changes):
            if key in defaults and _extend_lists:
                existing = defaults[key]
                value = update_metadata_value(existing, value)
            defaults[key] = value
        return defaults

    @classmethod
    def clone_defaults(cls, _defaults=None, _extend_lists=True, **changes):
        new = _defaults or copy.deepcopy(getattr(cls, 'DEFAULTS', {}))
        cls.update_defaults(_defaults=new, _extend_lists=_extend_lists, **changes)
        return new

    @classmethod
    def clone_defaults_extend(cls, **changes):
        return cls.clone_defaults(_extend_lists=True, **changes)

    @classmethod
    def clone_defaults_overwrite(cls, **changes):
        return cls.clone_defaults(_extend_lists=False, **changes)

    @classmethod
    def merge_defaults_extend(cls, **changes):
        cls.update_defaults(_extend_lists=True, **changes)
        return cls

    @classmethod
    def merge_defaults_overwrite(cls, **changes):
        return cls.update_defaults(_extend_lists=False, **changes)
