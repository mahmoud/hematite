# -*- coding: utf-8 -*-

from hematite.constants import HEADER_CASE_MAP, FOLDABLE_HEADER_SET
from hematite.compat.dictutils import OrderedMultiDict


PREV, NEXT, KEY, VALUE, SPREV, SNEXT = range(6)


# Connection, Content-Encoding, Transfer-Encoding
# Additional: +Trailer +Expect +Upgrade


# Case-insensitive, but case-preserving
class HeadersDict(OrderedMultiDict):
    _tracked_keys = set(['Connection',
                         'Content-Encoding',
                         'Content-Length',
                         'Transfer-Encoding'])

    def _clear_ll(self):
        super(HeadersDict, self)._clear_ll()
        self._node_case_map = {}

    def _insert(self, k, v):
        canonical_key = HEADER_CASE_MAP[k]
        super(HeadersDict, self)._insert(canonical_key, v)
        node_id = id(self._map[canonical_key][-1])
        self._node_case_map[node_id] = k

    def _remove(self, k):
        canonical_key = HEADER_CASE_MAP[k]
        node = self._map[canonical_key][-1]
        node_id = id(node)
        self._node_case_map.pop(node_id)
        super(HeadersDict, self)._remove(k)

    def _remove_all(self, k):
        super(HeadersDict, self)._remove_all(k)
        canonical_key = HEADER_CASE_MAP[k]
        if canonical_key in self._tracked_keys:
            self._rebuild()

    def iget(self, k, default=None, multi=False):
        # convenience function
        return self.lower_map.get(k, default=default, multi=multi)

    def pop(self, k, default=_MISSING):
        return self.popall(k, default)[-1]

    def popall(self, k, default=_MISSING):
        if super(OrderedMultiDict, self).__contains__(k):
            self._remove_all(k)
        if default is _MISSING:
            return super(OrderedMultiDict, self).pop(k)
        return super(OrderedMultiDict, self).pop(k, default)

    def poplast(self, k=_MISSING, default=_MISSING):
        if k is _MISSING:
            if self:
                k = self.root[PREV][KEY]
            else:
                raise KeyError('empty %r' % type(self))
        try:
            self._remove(k)
        except KeyError:
            if default is _MISSING:
                raise KeyError(k)
            return default
        values = super(OrderedMultiDict, self).__getitem__(k)
        v = values.pop()
        if not values:
            super(OrderedMultiDict, self).__delitem__(k)
        return v


"""

    def _load_connection(self, value):
        try:
            for v in value.split(','):
                v = v.strip().lower()
                if v == 'close':
                    self.is_conn_close = True
                elif v == 'keep-alive':
                    self.is_conn_keep_alive = True
        except:
            self.is_conn_close = False
            self.is_conn_keep_alive = False

    def _load_transfer_encoding(self, value):
        try:
            for v in value.split(','):
                v = v.strip().lower()
                if v == 'chunked':
                    self.is_chunked = True
        except:
            self.is_chunked = False

    def _load_content_length(self, value):
        try:
            self.content_length = int(value)
        except:
            self.content_length = None

    def _load_content_encoding(self, value):
        pass
"""
