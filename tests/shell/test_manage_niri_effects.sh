#!/bin/sh
set -eu
test_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$test_dir/test_niri_config.py" ConfigurationContracts.test_effects_wrapper
