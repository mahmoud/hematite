
from hematite.async import join
from hematite.client import Client
from hematite.profile import HematiteProfile
from hematite.request import Request

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

DEFAULT_URL = 'https://en.wikipedia.org/wiki/Main_Page'


def main(url, number, output, do_pdb=False):
    client = Client(profile=HematiteProfile())
    # req = Request('GET', 'http://makuro.org/')
    #req = Request('GET', 'http://hatnote.com/')
    # req = Request('GET', 'http://blog.hatnote.com/')

    req = Request('GET', url)
    kwargs = dict(request=req, autoload_body=False, async=True)
    resp_list = [client.request(**kwargs) for i in range(number)]
    resp = resp_list[0]

    join(resp_list, timeout=5.0)

    print resp.raw_response
    print [r.raw_response.status_code for r in resp_list]
    resp.autoload_body = True
    # import pdb; pdb.set_trace()
    join(resp_list, timeout=1.0)
    print resp.raw_response.body
    if output == '-':
        print resp.raw_response.body.data
    elif output:
        with open(output, 'w') as f:
            f.write(resp.raw_response.body.data)
    if do_pdb:
        import pdb
        pdb.set_trace()


if __name__ == '__main__':
    import argparse

    a = argparse.ArgumentParser()
    a.add_argument('url', nargs='?', default=DEFAULT_URL)
    a.add_argument('--number', '-n', type=int, default=10)
    a.add_argument('--output', '-o', default=None,
                   help='path to output file: "-" means stdout')
    a.add_argument('--pdb', action='store_true', default=True)

    args = a.parse_args()

    main(args.url, args.number, args.output, args.pdb)


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
