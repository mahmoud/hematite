
import time
import select

from hematite.client import Client
from hematite.request import Request
from hematite.response import ClientResponse

# TODO: noticed that sometimes RequestLine has .url = URL object,
# other times a string
# TODO: where to control automatic fetching of content and
# following of redirects? join arg, ClientResponse attr, Client
# default (internally falling back on ClientProfile)

"""
makuro.org = oldish Apache
hatnote.com = newish Nginx, issuing a redirect
blog.hatnote.com = ?? (tumblr)
wikipedia.org = Apache + Varnish
"""


def main():
    client = Client()
    req_count = 5
    req = Request('GET', 'http://makuro.org/')
    #req = Request('GET', 'http://hatnote.com/')
    # req = Request('GET', 'http://blog.hatnote.com/')
    # req = Request('GET', 'https://en.wikipedia.org/wiki/Main_Page')
    kwargs = dict(client=client, request=req,
                  autoload_body=False, nonblocking=True)
    resp_list = [ClientResponse(**kwargs) for i in range(req_count)]
    resp = resp_list[0]

    join(resp_list, timeout=5.0)

    print resp.raw_response
    print [resp.raw_response.status_code for r in resp_list]
    resp.autoload_body = True
    join(resp_list, timeout=1.0)
    print resp.raw_response.body
    #import pdb;pdb.set_trace()


def main_wp():
    client = Client()
    req = Request('GET', 'http://en.wikipedia.org/wiki/Main_Page')
    resp = ClientResponse(client=client, request=req)
    resp.nonblocking = True  # TODO: kwargs
    resp.autoload_body = False
    join([resp], timeout=5.0)
    print resp.raw_response
    resp.autoload_body = True
    print resp.raw_response.body
    join([resp])
    print resp.raw_response.body

    # true for wikipedia:
    # assert resp.raw_response.headers != resp2.raw_response.headers
    # assert resp.get_data() == resp2.get_data()
    import pdb;pdb.set_trace()


def join(reqs, timeout=5.0, raise_exc=True,
         follow_redirects=None, select_timeout=0.05):
    ret = list(reqs)
    cutoff_time = time.time() + timeout

    while True:
        readers = [r for r in reqs if r.want_read]
        writers = [r for r in reqs if r.want_write]

        # forced writers are e.g., resolving/connecting, don't have sockets yet
        forced_writers = [r for r in writers if r.fileno() is None]
        selectable_writers = [r for r in writers if r.fileno() is not None]

        if not (readers or writers):
            break
        if time.time() > cutoff_time:
            # TODO: is time.time monotonic? no, so... time.clock()?
            break

        if readers or selectable_writers:
            read_ready, write_ready, _ = select.select(readers,
                                                       selectable_writers,
                                                       [],
                                                       select_timeout)
            write_ready.extend(forced_writers)
        else:
            read_ready = []
            write_ready = forced_writers
        for wr in write_ready:
            while True:
                _keep_writing = wr.do_write()
                if not _keep_writing:
                    break
        for rr in read_ready:
            while True:
                _keep_reading = rr.do_read()
                if not _keep_reading:
                    break
    return ret


if __name__ == '__main__':
    main()


class Joinable(object):
    "just a sketch of an interface"

    def fileno():
        pass  # None if not selectable

    # TODO: attribute/property?
    def want_read(self):
        pass

    def want_write(self):
        pass

    def do_read(self):
        pass

    def do_write(self):
        pass

    def is_complete(self):
        # can this be implicit from not wanting read or write?
        pass
