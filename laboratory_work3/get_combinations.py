#!/usr/bin/env python3

from __future__ import annotations

import argparse
import itertools
import re
import sys
from typing import Iterator

# (c* | bc)(b | aa)*(a | b)
PATTERN = re.compile(r'^(?:c*|bc)(?:b|aa)*(?:a|b)$')
ALPHABET = "abc"


def words(min_len: int, max_len: int) -> Iterator[str]:
    for n in range(min_len, max_len + 1):
        for tup in itertools.product(ALPHABET, repeat=n):
            s = "".join(tup)
            if PATTERN.fullmatch(s):
                yield s


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate words of the language (c*|bc)(b|aa)*(a|b) up to a maximum length."
    )
    parser.add_argument(
        "--min", type=int, default=1, metavar="M",
        help="minimum word length to generate (default: 1)",
    )
    parser.add_argument(
        "--max", type=int, default=20, metavar="N",
        help="maximum word length to generate (default: 20)",
    )
    ns = parser.parse_args(argv)

    if ns.min < 1 or ns.max < ns.min:
        print("Invalid length range: --min must be >=1 and --max >= --min", file=sys.stderr)
        sys.exit(1)

    for w in words(ns.min, ns.max):
        print(w)


if __name__ == "__main__":
    main()
