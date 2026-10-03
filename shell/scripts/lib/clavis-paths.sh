#!/usr/bin/env bash

# Compatibility wrapper pointing to nyxuri-paths.sh.

_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=scripts/lib/nyxuri-paths.sh
source "$_dir/nyxuri-paths.sh"
