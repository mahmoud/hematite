# -*- coding: utf-8 -*-

from dictutils import OrderedMultiDict

try:
    from compat import make_sentinel
    _MISSING = make_sentinel(var_name='_MISSING')
except ImportError:
    _MISSING = object()


PREV, NEXT, KEY, VALUE, SPREV, SNEXT = range(6)


class HeadersDict(OrderedMultiDict):
    """\
    >>> hd = HeadersDict()
    >>> hd['a'] = 1
    >>> hd['b'] = 2
    >>> hd.add('a', 3)
    >>> hd['a']
    3
    >>> omd
    OrderedMultiDict([('a', 1), ('b', 2), ('a', 3)])
    >>> omd.poplast('a')
    3
    >>> omd
    OrderedMultiDict([('a', 1), ('b', 2)])
    >>> omd.pop('a')
    1
    >>> omd
    OrderedMultiDict([('b', 2)])

    Note that dict()-ifying the OMD results in a dict of keys to
    _lists_ of values:

    >>> dict(OrderedMultiDict([('a', 1), ('b', 2), ('a', 3)]))
    {'a': [1, 3], 'b': [2]}

    If you want a flat dictionary, use ``todict()``.

    >>> OrderedMultiDict([('a', 1), ('b', 2), ('a', 3)]).todict()
    {'a': 3, 'b': 2}

    The implementation could be more optimal, but overall it's far
    better than other OMDs out there. Mad props to Mark Williams for
    all his help.
    """
    def __init__(self, *args, **kwargs):
        self.lower_cells = []
        self.lower_map = OrderedMultiDict()  # lolol
        super(HeadersDict, self).__init__(*args, **kwargs)

    def _clear_ll(self):
        super(HeadersDict, self)._clear_ll()
        self.lower_cells = list(self.root)
        self.lower_map.clear()

    def _insert(self, k, v):
        super(HeadersDict, self)._insert(k, v)
        last_cell = self.root[PREV]
        self.lower_cells.append(k.lower(), v)
        self.lower_map._insert(k.lower(), v)

    def _remove(self, k):
        values = self._map[k]
        cell = values.pop()
        cell[PREV][NEXT], cell[NEXT][PREV] = cell[NEXT], cell[PREV]
        if not values:
            del self._map[k]

    def _remove_all(self, k):
        values = self._map[k]
        while values:
            cell = values.pop()
            cell[PREV][NEXT], cell[NEXT][PREV] = cell[NEXT], cell[PREV]
        del self._map[k]

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
