Ransom Notes
============

Just some notes to myself. RFC stuff mostly.

Good practice for header order: general, then request/response, finally entity.

General headers:

- Cache-Control            ; Section 14.9
- Connection               ; Section 14.10
- Date                     ; Section 14.18
- Pragma                   ; Section 14.32
- Trailer                  ; Section 14.40
- Transfer-Encoding        ; Section 14.41
- Upgrade                  ; Section 14.42
- Via                      ; Section 14.45
- Warning                  ; Section 14.46

Request headers:

- Accept (and -Charset, -Encoding, -Language) (14.1-14.4)
- Authorization            ; Section 14.8
- Expect                   ; Section 14.20
- From                     ; Section 14.22
- Host                     ; Section 14.23
- If-*                     ; Section 14.24-14.28
- Max-Forwards             ; Section 14.31
- Proxy-Authorization      ; Section 14.34
- Range                    ; Section 14.35
- Referer                  ; Section 14.36
- TE (extension transfer encodings)  ; Section 14.39
- User-Agent               ; Section 14.43

Response headers:

- Accept-Ranges           ; Section 14.5
- Age                     ; Section 14.6
- ETag                    ; Section 14.19
- Location                ; Section 14.30
- Proxy-Authenticate      ; Section 14.33
- Retry-After             ; Section 14.37
- Server                  ; Section 14.38
- Vary                    ; Section 14.44
- WWW-Authenticate        ; Section 14.47

Entity headers:

- Allow                    ; Section 14.7
- Content-Encoding         ; Section 14.11
- Content-Language         ; Section 14.12
- Content-Length           ; Section 14.13
- Content-Location         ; Section 14.14
- Content-MD5              ; Section 14.15
- Content-Range            ; Section 14.16
- Content-Type             ; Section 14.17
- Expires                  ; Section 14.21
- Last-Modified            ; Section 14.29

HTTP payloads are sorta like:

Transfer-Encoding(Content-Encoding(Content-Type(entity data)))

e.g., chunked(gzip(html;utf-8([web page])))


RFC2616 3.1 Page 31:

Multiple message-header fields with the same field-name MAY be
present in a message if and only if the entire field-value for that
header field is defined as a comma-separated list [i.e., #(values)].
It MUST be possible to combine the multiple header fields into one
"field-name: field-value" pair, without changing the semantics of the
message, by appending each subsequent field-value to the first, each
separated by a comma. The order in which header fields with the same
field-name are received is therefore significant to the
interpretation of the combined field value, and thus a proxy MUST NOT
change the order of these field values when a message is forwarded.


RFC2616 3.2 Page 32:

For response messages, whether or not a message-body is included with
a message is dependent on both the request method and the response
status code (section 6.1.1). All responses to the HEAD request method
MUST NOT include a message-body, even though the presence of entity-
header fields might lead one to believe they do. All 1xx
(informational), 204 (no content), and 304 (not modified) responses
MUST NOT include a message-body. All other responses do include a
message-body, although it MAY be of zero length.
