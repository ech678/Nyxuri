#!/usr/bin/env bash
# ==============================================================================
# Nyxuri CLI 的永久入口，用户与系统包的 nyxuri 命令均指向此处。
# install.sh 只负责首次引导；-I 隔离 PYTHON* 注入，-S 跳过 sitecustomize。
# 在加载 CLI 前只读校验 XDG 布局，尚不支持的路径直接拒绝。
# ==============================================================================
set -euo pipefail

# XDG 布局由下方 Python 公共校验器只读检查；不静默改写调用者的环境。

# Repo root = parent of this file's directory (launcher lives at <repo>/nyxuri/).
self="${BASH_SOURCE[0]}"
resolved="$(readlink -f "$self" 2>/dev/null || echo "$self")"
repo_dir="$(cd -- "$(dirname -- "$resolved")/.." && pwd)"

exec python3 -I -S -c '
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 11):
    sys.stderr.write(
        "[✗] 需要 Python 3.11+（当前 %d.%d），请升级后重试。\n"
        "[✗] Python 3.11+ is required (found %d.%d). Please upgrade python3.\n"
        % (sys.version_info[0], sys.version_info[1], sys.version_info[0], sys.version_info[1])
    )
    sys.exit(1)
target = sys.argv.pop(1)
sys.path.insert(0, target)
sys.argv[0] = "nyxuri"
from nyxuri.core import XDGLayoutError, validate_xdg_layout
try:
    validate_xdg_layout()
except XDGLayoutError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(1)
from nyxuri.cli import main
main()
' "$repo_dir" "$@"
