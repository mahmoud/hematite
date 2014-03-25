# -*- coding: utf-8 -*-

from hematite.constants import HEADER_CASE_MAP, FOLDABLE_HEADER_SET
from hematite.compat.dictutils import OrderedMultiDict


PREV, NEXT, KEY, VALUE, SPREV, SNEXT = range(6)


# Connection, Content-Encoding, Transfer-Encoding
# Additional: +Trailer +Expect +Upgrade


class HeadersDict(OrderedMultiDict):
    _tracked_keys = set(['Connection',
                         'Content-Encoding',
                         'Content-Length',
                         'Transfer-Encoding'])

    def _clear_ll(self):
        super(HeadersDict, self)._clear_ll()
        self.is_conn_close = False
        self.is_conn_keep_alive = False
        self.is_chunked = False
        self.content_length = None
        self.content_encodings = []

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

    def _insert(self, key, value):
        super(HeadersDict, self)._insert(key, value)
        canonical_key = HEADER_CASE_MAP[key]
        if canonical_key == 'Connection':
            self._load_connection(value)
        elif canonical_key == 'Transfer-Encoding':
            self._load_transfer_encoding(value)
        elif canonical_key == 'Content-Length':
            self._load_content_length(value)
        elif canonical_key == 'Content-Encoding':
            self._load_content_encoding(value)
        return

    def _reload(self):
        for noncanonical_key, val in self.iteritems(multi=True):
            key = HEADER_CASE_MAP[noncanonical_key]
            if key == 'Connection':
                self._load_connection(val)
            elif key == 'Transfer-Encoding':
                self._load_transfer_encoding(val)
            elif key == 'Content-Length':
                self._load_content_length(val)
            elif key == 'Content-Encoding':
                self._load_content_encoding(val)

    def _remove(self, k):
        super(HeadersDict, self)._remove(k)
        canonical_key = HEADER_CASE_MAP[k]
        if canonical_key in self._tracked_keys:
            self._rebuild()

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
