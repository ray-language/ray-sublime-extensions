#!/usr/bin/env python3
"""Checks every entry: its shape, and every zip it names, downloaded.

    python3 tools/validate.py [extensions/<id>.json …]

With no arguments, every entry. Exit 0 when all is well, 1 with the problems
said, one a line.
"""
import os
import sys

from common import artifact, entries, shape


def main(argv):
    only = {os.path.basename(a) for a in argv}
    problems = []
    for name, e in entries():
        if only and name not in only:
            continue
        found = shape(name, e)
        problems += found
        if found:
            continue
        for v in e["versions"]:
            for key, a in v["artifacts"].items():
                problems += artifact(name, e, v, key, a)
    for p in problems:
        print(p)
    if not problems:
        print("validate: every entry is as it says")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
