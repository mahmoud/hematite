# -*- coding: utf-8 -*-

from hematite.raw import RawRequest, Headers


def main():
    rreq = RawRequest(headers=Headers({'AccepT': 'lol'}))
    print repr(rreq.to_bytes())
    print '------'
    print rreq.to_bytes()

if __name__ == '__main__':
    main()
