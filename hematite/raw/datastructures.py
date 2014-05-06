from hematite.compat import OrderedMultiDict as OMD


class Headers(OMD):
    pass


class A(object):

    thing = otherthing

    def otherthing(self):
        return 'yep'
