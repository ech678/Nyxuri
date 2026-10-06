#!/usr/bin/env bash
# ==============================================================================
# Optional-dependency probe (probe-tool.sh)
# Exits 0 when the named tool exists in PATH, 1 when missing, 2 on bad usage.
# Services use this to degrade explicitly: Quickshell execDetached cannot
# report a spawn failure, so availability must be checked before dispatch.
# ==============================================================================
set -u

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo "Usage: $0 <tool>" >&2
    exit 2
fi
command -v -- "$1" >/dev/null 2>&1
