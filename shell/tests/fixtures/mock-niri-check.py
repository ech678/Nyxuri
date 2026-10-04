#!/usr/bin/env python3
import collections
import os
import re
import sys

INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"(.*)$')
BINDS = re.compile(r"binds\s*\{")


def parse(text):
    pending = None
    keys = []
    children = []
    optional = False
    depth = 0
    for token in re.findall(r'\{|\}|"[^"]*"|[^\s{}]+', text):
        if token == "{":
            depth += 1
            if depth == 1 and pending is not None:
                keys.append(pending)
                children.append(pending)
            pending = None
        elif token == "}":
            depth -= 1
            pending = None
        elif depth == 0:
            pending = token
        else:
            pending = None
    return keys, children, optional


def scan(text):
    keys = []
    for match in BINDS.finditer(text):
        depth = 1
        first = None
        for token in re.findall(r'\{|\}|"[^"]*"|[^\s{}]+', text[match.end():]):
            if token == "{":
                depth += 1
                if depth == 2 and first is not None:
                    keys.append(first)
                first = None
            elif token == "}":
                depth -= 1
                if depth == 0:
                    break
                first = None
            elif depth == 1:
                if token == ";":
                    first = None
                elif first is None:
                    first = token
            else:
                first = None
    return keys


def walk(path, seen):
    real = os.path.realpath(path)
    if real in seen:
        return 1
    seen.add(real)
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return 0
    if "unknown-niri-setting" in text:
        return 1
    base = os.path.dirname(os.path.abspath(path))
    for line in text.splitlines():
        match = INCLUDE.match(line)
        if not match:
            continue
        if "optional=true" in match.group(2):
            continue
        child = match.group(1)
        if not os.path.isabs(child):
            child = os.path.join(base, child)
        if not os.path.exists(child):
            return 1
        if walk(child, seen):
            return 1
    keys = scan(text)
    for count in collections.Counter(keys).values():
        if count > 1:
            return 1
    return 0


def main():
    if len(sys.argv) < 2:
        return 0
    return walk(sys.argv[1], set())


if __name__ == "__main__":
    sys.exit(main())