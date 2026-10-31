#!/usr/bin/env python3
"""将 Shell 内置模板的暂存结果提交给 Nyxuri 归属管理器。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from nyxuri.desktop.owned_outputs import commit_shell_template

if __name__ == "__main__":
    sys.exit(0 if commit_shell_template(sys.argv[1], Path(sys.argv[2])) else 1)
