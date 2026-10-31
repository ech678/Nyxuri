#!/usr/bin/env python3
"""S0-0 spike: 注册表装载形态 vs Quickshell qs-import 静态扫描闭包缺陷（可复跑）。

背景（S0-0 门禁，ROADMAP）：Quickshell 0.3.2 上 Loader 动态装载的组件首次解析
qs.* import 图不可靠，SlotHost 静态预热名单是它的补丁。S0-2 运行时注册表要求
「新增插件 = 加目录 + manifest + 代码」的开放集合，静态名单原理上无法覆盖，
必须先验证注册表装载形态是否确定性成立。

根因假设（源码证据 src/core/scan.cpp + src/core/rootwrapper.cpp:60-61 +
src/core/qsintercept.cpp）：
1. QmlScanner 启动时只沿 shell.qml 的 import 语句静态递归，为闭包内目录合成
   qmldir（fileIntercepts 注入）。Loader { source: ... } 的 URL 不在解析范围 ——
   动态装载的组件若用 import qs.<own-module> 引用自己，qmldir 从未被合成 →
   module not installed。
2. Loader 相对路径 source 被 URL 拦截器解析为 qs: scheme；qs: URL 装载的组件
   连同目录隐式类型、相对 import 都可能失效（interceptor 黑洞/无法枚举）。
   file:// URL 装载不受影响。
3. config root 之外的目录不参与 qmldir 合成（scanner 警告 "outside of the
   config folder"）—— 第三方插件（~/.local/share/nyxuri/plugins/）天然只能
   以 file:// URL + 相对 import / 隐式类型形态装载。

本脚本生成最小 fixture 树、按形态矩阵冷启动 N 次（每次清 qmlcache，模拟
nyxuri-shell wrapper），统计每个探针的装载结果：

  baseline    Loader 相对路径（qs: URL）+ 插件 import 自有 qs.* 模块根（缺陷形态）
  warmup      同 baseline + shell.qml 静态 import 全部插件模块（SlotHost 预热补丁）
  url-relative Loader 相对路径（qs: URL）+ 相对 import / 隐式类型（无自有模块 import）
  url-file    插件在 config root 内、按绝对 file:// URL 装载 + 相对 import / 隐式类型
              （Omarchy entryPointUrl 形态 = S0-2 注册表候选装载形态）
  external    插件在 config root 之外按 file:// URL 装载（S1 第三方插件形态）
  prewarm     baseline 形态 + 启动期 Qt.createComponent 预编译（候选 B' 有效性检验）

探针 tag 语义：
  <p>        插件入口组件本身装载成功
  <p>.tool   相对目录 import "tools" 装载成功
  <p>.inner  同目录/当前目录类型装载成功（.inner=implicit 无 import；beta 用 import "."）

用法:
  python3 spike-loader-registry.py --case baseline --runs 20
  python3 spike-loader-registry.py --all --runs 20 [--qs /path/to/qs]
  python3 spike-loader-registry.py --case baseline --runs 1 --scanner-log

复跑触发条件: quickshell 升级（> 0.3.2）后重估装载形态定案。
输出即验收证据: 逐 run 原始标记行 + 末尾汇总矩阵。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPIKE_ROOT = Path(tempfile.gettempdir()) / "opencode" / "spike-loader-registry"
SPIKE_RE = re.compile(r"SPIKE (?P<tag>[A-Za-z0-9._-]+) (?P<verdict>OK|MISSING)\b")

CASES = ("baseline", "warmup", "url-relative", "url-file", "external", "prewarm")

# 每个探针 tag = 「谁在哪一步装载成功」。缺失即该步编译/解析失败。
PROBES = {
    "baseline": ["alpha", "alpha.inner", "alpha.tool", "beta", "beta.inner", "beta.tool", "gamma"],
    "warmup": ["alpha", "alpha.inner", "alpha.tool", "beta", "beta.inner", "beta.tool", "gamma"],
    "url-relative": ["alpha", "alpha.inner", "alpha.tool", "beta", "beta.inner", "gamma", "gamma.inner"],
    "url-file": ["alpha", "alpha.inner", "alpha.tool", "beta", "beta.inner", "gamma", "gamma.inner"],
    "external": ["delta", "delta.inner", "delta.tool", "epsilon", "epsilon.inner", "epsilon.tool"],
    "prewarm": ["alpha", "alpha.inner", "alpha.tool", "beta", "beta.inner", "beta.tool", "gamma"],
}


def qml_inner(tag: str) -> str:
    return f"""import QtQuick

Item {{
    Component.onCompleted: console.log("SPIKE {tag} OK");
}}
"""


def qml_entry(tag: str, imports: str, bodies: str) -> str:
    return f"""import QtQuick
{imports}
import qs.commons

Item {{
    Component.onCompleted: console.log("SPIKE {tag} OK");
    CommonMark {{ }}
{bodies}
}}
"""


def entry_module(name: str, tag: str, tools: bool) -> str:
    """缺陷形态 / 补丁形态：插件用 qs.plugins.<name>[.tools] 模块 import。"""
    cap = name.capitalize()
    imports = f"import qs.plugins.{name}\nimport qs.plugins.{name}.tools" if tools else f"import qs.plugins.{name}"
    bodies = f"    {cap}Inner {{ }}\n    {cap}Tool {{ }}" if tools else f"    {cap}Inner {{ }}"
    return qml_entry(tag, imports, bodies)


def entry_relative(name: str, tag: str, mode: str) -> str:
    """无自有模块 import 形态。
    mode: tools-both=相对目录 import + 同目录隐式；dot=import "."；implicit=同目录隐式。"""
    cap = name.capitalize()
    if mode == "tools-both":
        imports = 'import "tools"'
        bodies = f"    {cap}Inner {{ }}\n    {cap}Tool {{ }}"
    elif mode == "dot":
        imports = 'import "."'
        bodies = f"    {cap}Inner {{ }}"
    else:
        imports = ""
        bodies = f"    {cap}Inner {{ }}"
    return qml_entry(tag, imports, bodies)


def shell_qml(loaders: list, extra_imports: str, prewarm_urls: list) -> str:
    loader_rows = "\n".join(
        f'            ListElement {{ tag: "{tag}"; src: "{src}" }}' for tag, src in loaders
    )
    prewarm_block = ""
    if prewarm_urls:
        urls = ",\n        ".join(f'"{u}"' for u in prewarm_urls)
        prewarm_block = f"""
    Component.onCompleted: {{
        const urls = [
        {urls}
        ];
        for (const u of urls) {{
            const c = Qt.createComponent(Qt.resolvedUrl(u), Component.PreferSynchronous);
            console.log("SPIKE prewarm-compile " + u + " status=" + c.status
                        + " error=" + (c.errorString() ? c.errorString().replace(/\\n/g, " ") : "none"));
        }}
    }}
"""
    return f"""import QtQuick
import Quickshell
import qs.commons
{extra_imports}

Item {{
    id: root
{prewarm_block}
    ListModel {{
        id: probeModel
{loader_rows}
    }}

    Repeater {{
        id: slotRepeater
        model: probeModel
        delegate: Loader {{
            required property string tag
            required property string src
            source: src
            active: true
        }}
    }}

    Timer {{
        interval: 3000
        running: true
        onTriggered: {{
            for (let j = 0; j < probeModel.count; j++) {{
                const loader = slotRepeater.itemAt(j);
                const tag = probeModel.get(j).tag;
                if (!loader || loader.status !== Loader.Ready || !loader.item)
                    console.log("SPIKE " + tag + " MISSING");
            }}
            console.log("SPIKE DONE");
            Qt.quit();
        }}
    }}
}}
"""


def write_plugin(base: Path, name: str, tag: str, entry: str, tools: bool) -> None:
    cap = name.capitalize()
    (base / name).mkdir(parents=True)
    (base / name / f"{cap}Root.qml").write_text(entry, encoding="utf-8")
    (base / name / f"{cap}Inner.qml").write_text(qml_inner(f"{tag}.inner"), encoding="utf-8")
    if tools:
        (base / name / "tools").mkdir()
        (base / name / "tools" / f"{cap}Tool.qml").write_text(qml_inner(f"{tag}.tool"), encoding="utf-8")


def build_case(case: str, root: Path) -> None:
    ext_root = root.parent / "external-plugins"
    for stale in (root, ext_root):
        if stale.exists():
            shutil.rmtree(stale)
    root.mkdir(parents=True)
    (root / "commons").mkdir()
    (root / "commons" / "CommonMark.qml").write_text(
        'import QtQuick\n\nItem {}\n', encoding="utf-8"
    )

    if case == "external":
        write_plugin(ext_root, "delta", "delta", entry_relative("delta", "delta", "tools-both"), tools=True)
        write_plugin(ext_root, "epsilon", "epsilon", entry_relative("epsilon", "epsilon", "tools-both"), tools=True)
        loaders = [
            ("delta", f"file://{ext_root}/delta/DeltaRoot.qml"),
            ("epsilon", f"file://{ext_root}/epsilon/EpsilonRoot.qml"),
        ]
        return _write_shell(root, loaders, "", [])

    plugins = root / "plugins"
    if case in ("baseline", "warmup", "prewarm"):
        write_plugin(plugins, "alpha", "alpha", entry_module("alpha", "alpha", tools=True), tools=True)
        write_plugin(plugins, "beta", "beta", entry_module("beta", "beta", tools=True), tools=True)
        write_plugin(plugins, "gamma", "gamma", entry_module("gamma", "gamma", tools=False), tools=False)
        srcs = {
            "alpha": "plugins/alpha/AlphaRoot.qml",
            "beta": "plugins/beta/BetaRoot.qml",
            "gamma": "plugins/gamma/GammaRoot.qml",
        }
        extra = (
            "import qs.plugins.alpha\nimport qs.plugins.beta\nimport qs.plugins.gamma"
            if case == "warmup"
            else ""
        )
        prewarm = [srcs["alpha"], srcs["beta"], srcs["gamma"]] if case == "prewarm" else []
    else:
        # url-relative / url-file：无自有模块 import。alpha=tools+隐式；beta=import "."；gamma=隐式
        write_plugin(plugins, "alpha", "alpha", entry_relative("alpha", "alpha", "tools-both"), tools=True)
        write_plugin(plugins, "beta", "beta", entry_relative("beta", "beta", "dot"), tools=True)
        write_plugin(plugins, "gamma", "gamma", entry_relative("gamma", "gamma", "implicit"), tools=False)
        srcs = {
            "alpha": "plugins/alpha/AlphaRoot.qml",
            "beta": "plugins/beta/BetaRoot.qml",
            "gamma": "plugins/gamma/GammaRoot.qml",
        }
        extra, prewarm = "", []

    if case == "url-file":
        # Omarchy entryPointUrl 形态：绝对 file:// URL（不走 qs: 拦截）
        loaders = [(tag, f"file://{plugins}/{Path(src).parent.name}/{Path(src).name}") for tag, src in srcs.items()]
    else:
        loaders = list(srcs.items())
    _write_shell(root, loaders, extra, prewarm)


def _write_shell(root: Path, loaders: list, extra: str, prewarm: list) -> None:
    (root / "shell.qml").write_text(shell_qml(loaders, extra, prewarm), encoding="utf-8")


def run_once(qs: str, root: Path, expected: list, scanner_log: bool) -> dict:
    env = dict(os.environ)
    sandbox = root.parent / "sandbox-env"
    for sub in ("cache", "state", "data", "config"):
        (sandbox / sub).mkdir(parents=True, exist_ok=True)
    env["XDG_CACHE_HOME"] = str(sandbox / "cache")
    env["XDG_STATE_HOME"] = str(sandbox / "state")
    env["XDG_DATA_HOME"] = str(sandbox / "data")
    env["XDG_CONFIG_HOME"] = str(sandbox / "config")
    shutil.rmtree(sandbox / "cache" / "quickshell", ignore_errors=True)
    if scanner_log:
        env["QT_LOGGING_RULES"] = "quickshell.qmlscanner.debug=true;quickshell.interceptor.debug=true"

    try:
        proc = subprocess.run(
            [qs, "-p", str(root / "shell.qml")],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = proc.stdout + proc.stderr
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        # 超时也收集已产出的标记（探针 onCompleted 在 3s 内早已打完）
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        output = stdout + stderr
        returncode = -1

    marks = {}
    for line in output.splitlines():
        m = SPIKE_RE.search(line)
        if m and m.group("tag") in expected:
            marks[m.group("tag")] = m.group("verdict")
    return {"marks": marks, "output": output, "returncode": returncode}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", choices=CASES, help="装载形态 case")
    ap.add_argument("--all", action="store_true", help="跑全部 case")
    ap.add_argument("--runs", type=int, default=20, help="每 case 冷启动次数（默认 20）")
    ap.add_argument("--qs", default="qs", help="quickshell 可执行文件（候选 A 传 master 构建路径）")
    ap.add_argument("--scanner-log", action="store_true", help="输出 qmldir 合成 debug 日志（根因证据）")
    ap.add_argument("--keep", action="store_true", help="保留 fixture 树")
    args = ap.parse_args()

    if not args.case and not args.all:
        ap.error("--case 或 --all 必选其一")
    cases = CASES if args.all else (args.case,)

    qs = shutil.which(args.qs) or args.qs
    ver = subprocess.run([qs, "--version"], capture_output=True, text=True).stdout.strip()

    for case in cases:
        root = SPIKE_ROOT / case
        build_case(case, root)
        print(f"=== case {case} | {ver} | runs={args.runs} | fixture={root}")
        tally = {tag: {"OK": 0, "MISSING": 0} for tag in PROBES[case]}
        for i in range(args.runs):
            res = run_once(qs, root, PROBES[case], scanner_log=args.scanner_log and i == 0)
            row = " ".join(
                f"{tag}={res['marks'].get(tag, 'ABSENT')}" for tag in PROBES[case]
            )
            print(f"run {i + 1:02d}: {row}")
            for tag in PROBES[case]:
                verdict = res["marks"].get(tag, "MISSING")
                tally[tag][verdict if verdict in tally[tag] else "MISSING"] += 1
            if args.scanner_log and i == 0:
                for line in res["output"].splitlines():
                    if any(k in line for k in ("Synthesized qmldir", "outside of the config folder",
                                               "prewarm-compile", "not installed", "not a type")):
                        print(f"  [log] {line.strip()}")
        summary = " | ".join(
            f"{tag} OK {tally[tag]['OK']}/{args.runs}" for tag in PROBES[case]
        )
        print(f"SUMMARY {case}: {summary}")
        if not args.keep:
            shutil.rmtree(root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
