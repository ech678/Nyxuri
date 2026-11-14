#!/usr/bin/env python3
"""Compare exact FontService results and operation counts from private QML runs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESULT = re.compile(r"^.*FONT_FAMILY_CACHE_RESULT (\{.*\})$", re.MULTILINE)


def read_result(path: Path) -> dict[str, object]:
    match = RESULT.search(path.read_text(encoding="utf-8", errors="replace"))
    if match is None:
        raise ValueError(f"missing FONT_FAMILY_CACHE_RESULT in {path}")
    return json.loads(match.group(1))


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: compare.py BASELINE_LOG CACHED_LOG")
    baseline = read_result(Path(sys.argv[1]))
    cached = read_result(Path(sys.argv[2]))
    for key in ("roles", "fixtureRoles", "availableFamilies", "fontOptionFamilies", "localeFallback",
                "localePriorityFixture", "configuredMissingRetained", "genericFallback"):
        if baseline[key] != cached[key]:
            raise SystemExit(f"FAIL: {key} differs: baseline={baseline[key]!r}, cached={cached[key]!r}")

    old = baseline["stats"]
    new = cached["stats"]
    if not isinstance(old, dict) or not isinstance(new, dict):
        raise SystemExit("FAIL: stats must be objects")
    if old["fontFamilyListCalls"] <= 1 or new["fontFamilyListCalls"] != 1:
        raise SystemExit(f"FAIL: family-list calls did not reduce to one: {old} -> {new}")
    if old["membershipLinearSteps"] <= 0 or new["membershipLinearSteps"] != 0:
        raise SystemExit(f"FAIL: cached membership still has linear scans: {old} -> {new}")
    if new["setMembershipLookups"] != new["membershipChecks"]:
        raise SystemExit(f"FAIL: cached membership checks were not all Set lookups: {new}")
    if old["dedupLinearSteps"] <= 0 or new["dedupLinearSteps"] != 0:
        raise SystemExit(f"FAIL: cached de-duplication still has linear scans: {old} -> {new}")
    if old["dedupChecks"] != new["dedupChecks"] or new["dedupSetLookups"] != new["dedupChecks"]:
        raise SystemExit(f"FAIL: de-duplication did not preserve check count with Set lookups: {old} -> {new}")

    result = {
        "same_roles_and_family_lists": True,
        "same_locale_and_fallback_behavior": True,
        "baseline_stats": old,
        "cached_stats": new,
        "family_list_calls_reduced": old["fontFamilyListCalls"] - new["fontFamilyListCalls"],
        "membership_linear_steps_removed": old["membershipLinearSteps"],
        "dedup_linear_steps_removed": old["dedupLinearSteps"],
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
