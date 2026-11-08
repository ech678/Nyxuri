#!/usr/bin/env python3
"""Instrument a private FontService copy without adding production diagnostics."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROBE_PROPERTIES = '''    property var _fontCacheProbeFamilies: null
    property var _fontCacheProbeFamilySet: new Set()
    property var _fontCacheProbeStats: ({
        "fontFamilyListCalls": 0,
        "membershipChecks": 0,
        "membershipLinearSteps": 0,
        "setMembershipLookups": 0,
        "dedupChecks": 0,
        "dedupLinearSteps": 0,
        "dedupSetLookups": 0
    })

    function _fontCacheProbeReadFamilies() {
        root._fontCacheProbeStats.fontFamilyListCalls += 1;
        return Qt.fontFamilies();
    }

    function _fontCacheProbeIndexOf(values, value) {
        root._fontCacheProbeStats.dedupChecks += 1;
        const index = values.indexOf(value);
        root._fontCacheProbeStats.dedupLinearSteps += index === -1 ? values.length : index + 1;
        return index;
    }

    function _fontCacheProbeSetHas(values, value) {
        root._fontCacheProbeStats.dedupChecks += 1;
        root._fontCacheProbeStats.dedupSetLookups += 1;
        return values.has(value);
    }
'''


def instrument(source: str, mode: str) -> str:
    source = source.replace("Qt.fontFamilies()", "root._fontCacheProbeReadFamilies()")
    config_anchor = '    property string configuredExpressive: ""\n'
    if source.count(config_anchor) != 1:
        raise ValueError("FontService configured-family anchor changed")
    source = source.replace(config_anchor, config_anchor + PROBE_PROPERTIES)
    start = source.index("    function familyAvailable(family) {")
    end = source.index("\n    function resolveFamily(", start)
    if mode == "baseline":
        lookup = '''        if (root._fontCacheProbeFamilies !== null) {
            root._fontCacheProbeStats.membershipChecks += 1;
            const index = root._fontCacheProbeFamilies.indexOf(value);
            root._fontCacheProbeStats.membershipLinearSteps += index === -1
                    ? root._fontCacheProbeFamilies.length : index + 1;
            return index !== -1;
        }
        const families = root._fontCacheProbeReadFamilies();
        root._fontCacheProbeStats.membershipChecks += 1;
        const index = families.indexOf(value);
        root._fontCacheProbeStats.membershipLinearSteps += index === -1 ? families.length : index + 1;
        return index !== -1;
'''
        if len(re.findall(r"result\.indexOf\(\s*family\s*\)", source)) != 1 or len(
                re.findall(r"result\.indexOf\(\s*root\.bundledExpressiveFamily\s*\)", source)) != 1:
            raise ValueError("baseline de-duplication anchors changed")
        source = re.sub(r"result\.indexOf\(\s*family\s*\)",
                        "root._fontCacheProbeIndexOf(result, family)", source)
        source = re.sub(r"result\.indexOf\(\s*root\.bundledExpressiveFamily\s*\)",
                        "root._fontCacheProbeIndexOf(result, root.bundledExpressiveFamily)", source)
    else:
        lookup = '''        if (root._fontCacheProbeFamilies !== null) {
            root._fontCacheProbeStats.membershipChecks += 1;
            root._fontCacheProbeStats.setMembershipLookups += 1;
            return root._fontCacheProbeFamilySet.has(value);
        }
        root._fontCacheProbeStats.membershipChecks += 1;
        root._fontCacheProbeStats.setMembershipLookups += 1;
        return root._familySet.has(value);
'''
        if source.count("seenFamilies.has(family)") != 1 or source.count(
                "seenFamilies.has(root.bundledExpressiveFamily)") != 1:
            raise ValueError("cached de-duplication anchors changed")
        source = source.replace("seenFamilies.has(family)",
                                "root._fontCacheProbeSetHas(seenFamilies, family)")
        source = source.replace("seenFamilies.has(root.bundledExpressiveFamily)",
                                "root._fontCacheProbeSetHas(seenFamilies, root.bundledExpressiveFamily)")
    source = source[:start] + '''    function familyAvailable(family) {
        const value = String(family || "").trim();
        if (value === "")
            return false;

''' + lookup + "    }" + source[end:]
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("mode", choices=("baseline", "cached"))
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    args.destination.write_text(instrument(source, args.mode), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
