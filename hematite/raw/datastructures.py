
from hematite.compat import OrderedMultiDict as OMD
from hematite.compat.dictutils import PREV, NEXT, KEY, VALUE, _MISSING

ORIG_KEY = VALUE + 1


class Headers(OMD):
    """
    Headers is an OrderedMultiDict, a mapping that preserves order and
    subsequent values for the same key, built for string keys that one
    may want to query case-insensitively, but otherwise
    case-preservingly.
    """

    def _insert(self, k, v, orig_key):
        root = self.root
        cells = self._map.setdefault(k, [])
        last = root[PREV]
        cell = [last, root, k, v, orig_key]
        last[NEXT] = root[PREV] = cell
        cells.append(cell)

    def add(self, k, v, multi=False):
        self_insert = self._insert
        orig_key, k = k, k.lower()
        values = super(OMD, self).setdefault(k, [])
        if multi:
            for subv in v:
                self_insert(k, subv, orig_key)
            values.extend(v)
        else:
            self_insert(k, v, orig_key)
            values.append(v)

    def __getitem__(self, key):
        return super(Headers, self).__getitem__(key.lower())

    def get(self, k, default=None, multi=False):
        return super(Headers, self).get(k.lower(), default, multi)

    def getlist(self, k):
        return super(Headers, self).getlist(k.lower())

    def get_cased_items(self, k):
        k = k.lower()
        return [(cell[ORIG_KEY], cell[VALUE]) for cell in self._map[k]]

    def __setitem__(self, k, v):
        orig_key, k = k, k.lower()
        if super(Headers, self).__contains__(k):
            self._remove_all(k)
        self._insert(k, v, orig_key)
        super(OMD, self).__setitem__(k, [v])

    def iteritems(self, multi=False, preserve_case=True):
        root = self.root
        curr = root[NEXT]
        if multi:
            if preserve_case:
                while curr is not root:
                    yield curr[ORIG_KEY], curr[VALUE]
                    curr = curr[NEXT]
            else:
                while curr is not root:
                    yield curr[KEY], curr[VALUE]
                    curr = curr[NEXT]
        else:
            if preserve_case:
                yielded = set()
                yielded_add = yielded.add
                while curr is not root:
                    k = curr[KEY]
                    if k not in yielded:
                        yielded_add(k)
                        yield curr[ORIG_KEY], curr[VALUE]
                    curr = curr[NEXT]
            else:
                yielded = set()
                yielded_add = yielded.add
                while curr is not root:
                    k = curr[KEY]
                    if k not in yielded:
                        yielded_add(k)
                        yield k, curr[VALUE]
                    curr = curr[NEXT]

    def poplast(self, k=_MISSING, default=_MISSING):
        return super(Headers, self).poplast(k.lower())

    def items(self, multi=False, preserve_case=True):
        return list(self.iteritems(multi=multi,
                                   preserve_case=preserve_case))

    # TODO popall, etc.


class ChunkedBody(object):

    def __init__(self, chunks=None):
        self.chunks = chunks or []
        self.data = None

    def send_chunk(self):
        return iter(self.chunks)

    def chunk_received(self, chunk):
        self.chunks.append(chunk)

    def complete(self, length):
        self.data = ''.join(self.chunks)
        assert len(self.data) == length


class Body(object):

    def __init__(self, body=None):
        self.body = body or []
        self.data = None
        self.nominal_length = None

    def data_received(self, data):
        self.body.append(data)

    def send_data(self):
        return [self.body]

    def complete(self, length):
        self.data = ''.join(self.body)
        self.nominal_length = length
