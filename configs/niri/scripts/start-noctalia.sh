#!/usr/bin/env bash
# ==============================================================================
# Legacy Noctalia startup wrapper (retained for backward compatibility)
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/session-shell.sh"
