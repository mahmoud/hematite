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


# Field thoughts

Things fields have:

* name
* attr_name
* duplicate behavior (fold or overwrite)
* from_* methods
* to_bytes method
* documentation
* validation

Question: Which of these are actually more a characteristic of the ValueWrapper (native_type)?
