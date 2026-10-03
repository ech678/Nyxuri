#!/usr/bin/env python3
"""Nyxuri Shell Tree Inventory & Migration Map Generator (R4-C-01 / R4-C-02).

Generates shell/wiki/tree-inventory.md covering:
  1. R4-C-01 Baseline 631-file Inventory & Migration Mapping
  2. R4-C-02 Domain Reorganization Executed Results
  3. Current Tree State (629 files)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from collections import defaultdict

TARGET_DIRS = ["app", "modules", "shared", "native", "bin", "packaging"]

MIGRATED_SERVICES = {
    "app/services/FileSearchService.qml": ("移动", "modules/launcher/FileSearchService.qml", "仅 launcher 消费的专属文件检索后台"),
    "app/services/SpotlightSearchService.qml": ("移动", "modules/launcher/SpotlightSearchService.qml", "仅 launcher 消费的聚焦搜索执行后台"),
    "app/services/SpotlightToolService.qml": ("移动", "modules/launcher/SpotlightToolService.qml", "仅 launcher 消费的数学/时区工具后台"),
    "app/services/AudioRecordingService.qml": ("移动", "modules/keystone/tools/AudioRecordingService.qml", "仅 keystone 消费的音频录制后台"),
    "app/services/RecordingService.qml": ("移动", "modules/keystone/tools/RecordingService.qml", "仅 keystone 消费的屏幕录制后台"),
    "app/services/MediaPalette.qml": ("移动", "modules/keystone/media/MediaPalette.qml", "仅 keystone 消费的媒体色板辅助"),
    "app/services/TrayService.qml": ("移动", "modules/bar/tray/TrayService.qml", "仅 bar 托盘消费的系统托盘服务"),
    "app/services/QuickToggleConfig.qml": ("移动", "modules/quicksettings/QuickToggleConfig.qml", "仅 quicksettings 消费的快捷开关配置"),
    "app/services/NetworkInterfaceHistoryService.qml": ("移动", "modules/systemcards/NetworkInterfaceHistoryService.qml", "仅 systemcards 消费的网络流量历史服务"),
    "app/services/TodoService.qml": ("移动", "modules/sidebars/dashboard/infotools/TodoService.qml", "仅 sidebars 消费的待办事项服务"),
    "app/services/AutostartService.qml": ("移动", "modules/settings/AutostartService.qml", "仅 settings 自启动页消费的配置服务"),
    "app/services/DisplayConfigService.qml": ("移动", "modules/settings/DisplayConfigService.qml", "仅 settings 显示设置页消费的显示配置服务"),
    "modules/keystone/tools/ToolsBackend.qml": ("删除", "-", "纯转发代理，直连录制服务，取色走 ActionGateway"),
    "modules/settings/SplitMenuButton.qml": ("删除", "-", "重复包装壳，直接使用 shared/controls/SplitMenuButton"),
    "app/services/weather/WeatherBackend.qml": ("合并", "app/services/WeatherPlugin.qml", "9 行纯 Loader 壳，合并入天气组件或 R4-C-05 消除"),
}


def analyze_file(rel_path: str, content: str) -> dict:
    parts = rel_path.split("/")
    layer = parts[0]

    if layer == "app":
        owner = "app"
    elif layer == "modules":
        owner = parts[1] if len(parts) > 1 else "modules"
    elif layer == "shared":
        owner = f"shared/{parts[1]}" if len(parts) > 1 else "shared"
    elif layer == "native":
        owner = f"native/{parts[1]}" if len(parts) > 1 else "native"
    elif layer == "bin":
        owner = "bin"
    elif layer == "packaging":
        owner = "packaging"
    else:
        owner = layer

    # Check if this file was moved here from app/services/
    moved_from = None
    for orig, (act, tgt, rat) in MIGRATED_SERVICES.items():
        if tgt == rel_path and act == "移动":
            moved_from = orig
            break

    if moved_from:
        action = "移动"
        target = rel_path
        rationale = f"已由 {moved_from} 迁入本功能域，保持内聚"
    elif rel_path in MIGRATED_SERVICES:
        action, target, rationale = MIGRATED_SERVICES[rel_path]
    elif layer == "shared":
        action = "保留"
        target = rel_path
        rationale = "复用原子控件/设计Token/纯数学，零副作用"
    elif layer == "bin":
        action = "保留"
        target = rel_path
        rationale = "薄启动脚本与 Action Gateway 入口"
    elif layer == "packaging":
        action = "保留"
        target = rel_path
        rationale = "系统打包与 systemd 单元元数据"
    elif layer == "native":
        if "fallback" in rel_path:
            action = "保留"
            target = rel_path
            rationale = "纯 QML 零依赖降级安全桩"
        else:
            action = "保留"
            target = "R4-C-05 移除"
            rationale = "待 R4-C-04/05 消除 C++ 依赖链时统一替换"
    else:
        action = "保留"
        target = rel_path
        rationale = "功能域自治代码"

    # Side-effects
    side_effects = []
    if "Quickshell.execDetached" in content:
        side_effects.append("execDetached")
    if "ActionGateway.execute" in content:
        side_effects.append("GatewayExec")
    if re.search(r"\bProcess\s*\{", content):
        side_effects.append("Process")
    if re.search(r"\bTimer\s*\{", content):
        side_effects.append("Timer")
    if re.search(r"\bFileView\s*\{", content):
        side_effects.append("FileView")
    if "Quickshell.env" in content:
        side_effects.append("Env")
    if "Socket" in content or "WlSessionLock" in content:
        side_effects.append("IPC/Wayland")
    side_effects_str = ", ".join(side_effects) if side_effects else "无"

    # Inputs / Outputs
    props = re.findall(r"property\s+(?:alias\s+|var\s+|bool\s+|string\s+|int\s+|real\s+)(\w+)", content)
    signals = re.findall(r"signal\s+(\w+)", content)
    funcs = re.findall(r"function\s+(\w+)\s*\(", content)

    io_desc = []
    if props:
        io_desc.append(f"属性({len(props)})")
    if signals:
        io_desc.append(f"信号({len(signals)})")
    if funcs:
        io_desc.append(f"方法({len(funcs)})")
    io_desc_str = "/".join(io_desc) if io_desc else "-"

    return {
        "rel_path": rel_path,
        "layer": layer,
        "owner": owner,
        "action": action,
        "target": target,
        "rationale": rationale,
        "side_effects": side_effects_str,
        "io": io_desc_str,
    }


def find_consumers(all_files: list[str], file_contents: dict[str, str]) -> dict[str, list[str]]:
    word_index = {}
    for q, content in file_contents.items():
        word_index[q] = set(re.findall(r"\b\w+\b", content))

    consumers = defaultdict(set)
    for p in all_files:
        stem = Path(p).stem
        if not stem or len(stem) < 3:
            continue
        for q, tokens in word_index.items():
            if q == p:
                continue
            if stem in tokens:
                q_parts = q.split("/")
                domain = q_parts[0]
                if domain == "modules" and len(q_parts) > 1:
                    domain = f"modules/{q_parts[1]}"
                elif domain == "shared" and len(q_parts) > 1:
                    domain = f"shared/{q_parts[1]}"
                consumers[p].add(domain)
    return {k: sorted(v) for k, v in consumers.items()}


def generate_markdown(entries: list[dict], consumers: dict[str, list[str]]) -> str:
    lines = []
    lines.append("# Nyxuri Shell 全树结构清单与迁移映射")
    lines.append("")
    lines.append("> 契约依据：[ROADMAP.md](../ROADMAP.md) R4-C 结构收敛与全面去 C++。")
    lines.append("> 本清单覆盖 `app/`、`modules/`、`shared/`、`native/`、`bin/`、`packaging/` 六大代码分支。")
    lines.append("> 逐文件标定 `保留`、`移动`、`合并`、`删除`、`阻断` 处置动作，记录所有者、消费者、I/O 与副作用。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 统计概览")
    lines.append("")

    total_files = len(entries)
    by_layer = defaultdict(int)
    by_action = defaultdict(int)
    for e in entries:
        by_layer[e["layer"]] += 1
        by_action[e["action"]] += 1

    lines.append(f"- **现存文件总数**：{total_files} 个（基线 631 文件，物理删除 2 个冗余代理，迁入 12 个服务）")
    lines.append("- **分层分布**：")
    for l in TARGET_DIRS:
        lines.append(f"  - `{l}/`：{by_layer[l]} 个文件")
    lines.append("- **处置状态分布**：")
    for act, count in sorted(by_action.items()):
        lines.append(f"  - **{act}**：{count} 个文件")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. R4-C-02 功能域内聚重组执行记录")
    lines.append("")
    lines.append("| 原文件路径 | 处置动作 | 目标路径 | 处置原因与验收结果 |")
    lines.append("|---|---|---|---|")
    for orig, (act, tgt, rat) in sorted(MIGRATED_SERVICES.items()):
        lines.append(f"| `{orig}` | **{act}** | `{tgt}` | {rat} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. 逐层结构清单与实时映射")
    lines.append("")

    for layer in TARGET_DIRS:
        layer_entries = [e for e in entries if e["layer"] == layer]
        lines.append(f"### {layer}/ （共 {len(layer_entries)} 文件）")
        lines.append("")
        lines.append("| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |")
        lines.append("|---|---|---|---|---|---|---|")
        for e in sorted(layer_entries, key=lambda x: x["rel_path"]):
            c_list = consumers.get(e["rel_path"], [])
            c_str = ", ".join(c_list) if c_list else "内部/自包含"
            lines.append(
                f"| `{e['rel_path']}` | **{e['action']}** | `{e['owner']}` | {c_str} | {e['io']} | {e['side_effects']} | {e['rationale']} |"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    shell_dir = repo_root

    all_target_files = []
    file_contents = {}
    for t in TARGET_DIRS:
        p = shell_dir / t
        for f in sorted(p.rglob("*")):
            if f.is_file():
                rel = f.relative_to(shell_dir).as_posix()
                all_target_files.append(rel)
                try:
                    file_contents[rel] = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    file_contents[rel] = ""

    consumers = find_consumers(all_target_files, file_contents)

    entries = []
    for rel in all_target_files:
        content = file_contents.get(rel, "")
        entries.append(analyze_file(rel, content))

    md_content = generate_markdown(entries, consumers)
    output_path = shell_dir / "wiki" / "tree-inventory.md"
    output_path.write_text(md_content, encoding="utf-8")
    print(f"Generated {output_path} with {len(entries)} entries.")


if __name__ == "__main__":
    main()
