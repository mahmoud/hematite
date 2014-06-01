
class Profile(object):
    default_headers = []

    def populate_headers(self, request):
        if self.default_headers:
            request.headers.update(self.default_headers)


class HematiteProfile(Profile):  # TODO: naming? DefaultProfile?
    default_headers = [('User-Agent', 'Hematite/0.6')]
