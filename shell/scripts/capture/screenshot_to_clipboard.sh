#!/usr/bin/env bash
set -euo pipefail

geometry="${1:?missing screenshot geometry}"
exec grim -g "$geometry" - | wl-copy
