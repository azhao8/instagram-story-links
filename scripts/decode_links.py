#!/usr/bin/env python3
"""Decode Instagram story-sticker redirect links.

Reads text on stdin (raw read_page output or one href per line), finds every
https://l.instagram.com/?u=... link, URL-decodes the destination, and drops
the fbclid tracking parameter. Prints one clean URL per line, in input order.
"""
import re
import sys
from urllib.parse import parse_qsl, quote, unquote, urlsplit, urlunsplit

LINK = re.compile(r"https://l\.instagram\.com/\?u=([^&\s\"']+)")


def clean(encoded):
    url = unquote(encoded)
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "fbclid"]
    q = "&".join(f"{k}={quote(v, safe='-_.~')}" if v != "" else k for k, v in query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, q, parts.fragment))


def main():
    for match in LINK.finditer(sys.stdin.read()):
        print(clean(match.group(1)))


if __name__ == "__main__":
    main()
