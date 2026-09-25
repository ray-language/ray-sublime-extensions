#!/usr/bin/env python3
"""Puts every entry together into index.json, which is what the editor reads.

    python3 tools/build_index.py          # writes it
    python3 tools/build_index.py --check  # fails if it is not up to date
"""
import json
import os
import sys

from common import ROOT, entries


def built():
    return json.dumps({"extensions": [e for _name, e in entries()]}, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    path = os.path.join(ROOT, "index.json")
    text = built()
    if "--check" in argv:
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if current != text:
            print("index.json is not up to date: run python3 tools/build_index.py")
            return 1
        print("build_index: index.json is up to date")
        return 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"build_index: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
