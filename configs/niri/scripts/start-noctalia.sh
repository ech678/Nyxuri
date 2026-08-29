#!/usr/bin/env bash
# Noctalia runs in an app scope that can outlive niri.service. Clear any scope
# left by the previous compositor session before attaching a fresh instance.

set -u

systemctl --user stop 'app-niri-noctalia-*.scope' >/dev/null 2>&1 || true
exec noctalia
