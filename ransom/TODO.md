# TODO

## Refactors

- Excise pyparser standin
- BytestringHelper class decorator
- Get off of namedtuple as base class for parser components
- Switch off new-style formatting (up to 2x slower)

## Features

- to_/from_raw_request
- Headers: most fundamental parsers done, but matching serialization is TBD

- Clarify high-level/low-level split
- Composable URL


## Big features

- Simple select() join
- Client (stateful)
  - Connection pooling
  - Cookie container
  - Pluggable cache
  - Other "session" variables (e.g., referer)
  - Profile (user-agent, browser stuff)
