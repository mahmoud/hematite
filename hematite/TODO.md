# TODO

## Refactors

- Get off of namedtuple as base class for parser components?

## Issues

- coverage/pytest-cov not seeing globals as covered (e.g., function
  defs or global regexes)

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

## HeaderValueWrappers

- CacheControl
- ContentType
- ContentDisposition
- Cookie
- ETagSet
- UserAgent
- WWWAuthenticate
- Warning
(more)


# Validation thoughts

- Need at least levels (notice/warning/error).
- Operate on Request/Response or RawRequest/RawResponse?

* Basic presence
  * Response.reason should not be blank
* Status code-specific headers
  * Location for redirects
* Unrecognized/unregistered values for certain headers/fields
  * Accept-Ranges: "bytes" or "none"
  * Allow: GET, POST, other known HTTP methods
  * Transfer-Encoding: "chunked"
  * Accept-Encoding/Content-Encoding: identity, gzip, compress, deflate, *
  * Warn on unknown status codes?
* Valid mimetype format for headers using media types
  * Content-Type
  * Content-Disposition
  * Accept
* Unrecognized charset
* URLs missing components (e.g, has a scheme, but no host)

* Maybe: validation for 1.0-compatibility
