# TODO

## Refactors

- Get off of namedtuple as base class for parser components?

## Features

- status_code, version, and method fields (reason field?)
- CacheControl and WWWAuthenticate types
- Composable URL
- Gzip/deflate support
- Automatic charset/decoding handling

## Big features

- Simple select() join
- Client (stateful)
  - Connection pooling
  - Cookie container
  - Pluggable cache
  - Other "session" variables (e.g., referer)
  - Profile (user-agent, browser stuff)
- File upload
- Chardet
