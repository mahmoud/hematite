# Issues discovered with other implementations

## Werkzeug

* When Werkzeug detects an item is quoted, it prematurely unquotes it,
  leaving internal escaping in place. See parse_dict_header for
  example.
* ETags are also not internally unquoted. If quoted, quotes are just
  pulled off the ends, leaving internal escaping in place.

## Requests

* Don't even get me started.
