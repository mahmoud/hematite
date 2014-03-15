# TODO

## Refactors

- BytestringHelper class decorator
- Get off of namedtuple as base class for parser components
- Switch off new-style formatting (up to 2x slower)

## Features

- Headers: most fundamental parsers done, but matching serialization is TBD
- CacheControl and WWWAuthenticate types

- Composable URL


## Big features

- Simple select() join
- Client (stateful)
  - Connection pooling
  - Cookie container
  - Pluggable cache
  - Other "session" variables (e.g., referer)
  - Profile (user-agent, browser stuff)
