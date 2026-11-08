#!/usr/bin/env python3
"""Render a self-contained HTML report containing every benchmark number."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence


def _text(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _flatten(value: object, path: str = "") -> list[tuple[str, object]]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, object]] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            rows.extend(_flatten(child, child_path))
        return rows
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        rows = []
        for index, child in enumerate(value):
            rows.extend(_flatten(child, f"{path}[{index}]"))
        return rows
    return [(path, value)]


def _table(title: str, value: object, note: str = "") -> str:
    rows = _flatten(value)
    body = "".join(
        f'<tr><td><code>{html.escape(path)}</code></td><td class="value">{html.escape(_text(item))}</td></tr>'
        for path, item in rows
    )
    description = f'<p class="note">{html.escape(note)}</p>' if note else ""
    return (
        f'<section class="data-section"><div class="section-heading"><h2>{html.escape(title)}</h2>'
        f'<span class="count">{len(rows)} 项</span></div>{description}'
        '<div class="table-wrap"><table><thead><tr><th>路径</th><th>数值</th></tr></thead>'
        f'<tbody>{body}</tbody></table></div></section>'
    )


def _score_table(title: str, scores: object, ratios: object) -> str:
    if not isinstance(scores, Mapping) or not isinstance(ratios, Mapping):
        return _table(title, {"scores": scores, "ratios": ratios})
    rows = []
    for name, item in scores.items():
        ratio = ratios.get(name)
        width = max(0.0, min(100.0, float(item))) if isinstance(item, (int, float)) else 0.0
        rows.append(
            f'<tr><td><code>{html.escape(str(name))}</code></td>'
            f'<td class="value">{html.escape(_text(ratio))}</td>'
            f'<td class="score-value">{html.escape(_text(item))}</td>'
            f'<td><span class="score-track"><span style="width:{width:.2f}%"></span></span></td></tr>'
        )
    return (
        f'<section class="data-section"><div class="section-heading"><h2>{html.escape(title)}</h2>'
        f'<span class="count">{len(scores)} 个分项</span></div>'
        '<div class="table-wrap"><table class="score-table"><thead><tr>'
        '<th>维度</th><th>倍率</th><th>分数</th><th>刻度</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def _score_matrix(scores: object) -> str:
    if not isinstance(scores, Mapping):
        return ""
    groups: dict[str, list[float]] = {
        "执行": [], "内存": [], "系统": [], "可靠性": [], "IPC": [], "动作": []
    }
    for key, value in scores.items():
        if not isinstance(value, (int, float)):
            continue
        name = str(key)
        if name.startswith("ipc."):
            group = "IPC"
        elif name.startswith("action."):
            group = "动作"
        elif name in {"startup", "cpu", "user_cpu", "system_cpu", "cpu_util"}:
            group = "执行"
        elif any(token in name for token in ("rss", "pss", "memory", "vm_")):
            group = "内存"
        elif name in {
            "log_errors", "log_warnings", "compiled_empty", "process_start_failures",
            "optional_process_start_failures", "required_process_start_failures",
            "unattributed_process_start_failures", "success",
        }:
            group = "可靠性"
        else:
            group = "系统"
        groups[group].append(float(value))
    cards = []
    for name, values in groups.items():
        if not values:
            continue
        average = sum(values) / len(values)
        cards.append(
            f'<div class="matrix-card"><div class="matrix-head"><span>{name}</span>'
            f'<strong>{average:.1f}</strong></div><div class="matrix-bar"><span style="width:{max(0,min(100,average)):.2f}%"></span></div>'
            f'<small>{len(values)} 个分项 · 算术平均</small></div>'
        )
    return '<section class="matrix-section"><div class="section-heading"><h2>分组评分</h2><span class="count">按 workload family 聚合</span></div><div class="matrix-grid">' + "".join(cards) + "</div></section>"


def render_html(raw: Mapping[str, object], report: Mapping[str, object]) -> str:
    normalized = report.get("normalized", {})
    if not isinstance(normalized, Mapping):
        normalized = {}
    runtime = raw.get("runtime", {})
    scores = normalized.get("scores_0_100", {})
    raw_report = report.get("raw", {})
    profile_summaries = raw_report.get("profiles", {}) if isinstance(raw_report, Mapping) else {}
    runs = runtime.get("runs") if isinstance(runtime, Mapping) else None
    ipc_runs = runtime.get("ipc_runs") if isinstance(runtime, Mapping) else None
    composite = normalized.get("composite_score_0_100")
    score_count = len(scores) if isinstance(scores, Mapping) else 0
    sections = [
        _score_matrix(scores),
        _table("运行环境", runtime, "本次 benchmark 使用的容器、合成器和渲染器。"),
        _table("源码画像", raw.get("source_profile", {}), "用于描述 workload 规模的静态源码计数。"),
        _table("Baseline 运行明细", raw.get("baseline", []), "最小 Shell baseline 的每次运行和全部数值字段。"),
        _table("冷启动运行明细", raw.get("cold_start", []), "每次冷启动运行和全部数值字段。"),
        _table("暖启动运行明细", raw.get("warm_start", []), "复用 QML cache 的每次暖启动运行和全部数值字段。"),
        _table("IPC 测量明细", raw.get("ipc", {}), "全部 IPC 分位数和错误计数。"),
        _table("动作测量明细", raw.get("actions", {}), "全部动作延迟、错误数和资源峰值。"),
        _table("长稳态明细", raw.get("long_steady_state", {}), "容器内连续运行期间的逐样本进程树采样。"),
        _table("回收循环明细", raw.get("reclamation", {}), "容器内显式 open/close 循环及关闭后资源观察。"),
        _table("渲染帧探针", raw.get("frame_profile", {}), "容器内 Qt QQuickWindow.frameSwapped；Weston presentation feedback、纹理和离屏目标计数若不可用会明确保留为 partial/null。"),
        _score_table("冷启动归一化分数", scores, normalized.get("ratios_shell_over_baseline", {})),
        _score_table("暖启动归一化分数", normalized.get("warm_scores_0_100", {}), normalized.get("warm_ratios_shell_over_baseline", {})),
        _table("Shell 内部时间点", normalized.get("internal_shell_ms", {})),
    ]
    if profile_summaries:
        sections.insert(
            2,
            _table("Profile summaries", profile_summaries,
                   "按 profile 保留启动数据与指标可用性；N/A 不参与综合评分。"),
        )
    body = "".join(sections)
    composite_text = "N/A" if composite is None and profile_summaries else _text(composite)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nyxuri Shell Benchmark</title>
<style>
:root {{ color-scheme:light; --bg:#fff; --surface:#fff; --surface2:#fafafa; --line:#ebebeb; --text:#171717; --muted:#666; --accent:#0070f3; --blue:#0070f3; --amber:#f5a623; --shadow:rgba(0,0,0,.08) 0 0 0 1px,rgba(0,0,0,.04) 0 2px 2px; }}
* {{ box-sizing:border-box }} html {{ background:var(--bg) }} body {{ margin:0; color:var(--text); background:var(--bg); font:14px/1.5 Geist,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; font-variant-numeric:tabular-nums; font-feature-settings:"liga" 1; }}
button,input {{ font:inherit }} button {{ color:var(--text); background:var(--surface); box-shadow:var(--shadow); border:0; border-radius:6px; padding:8px 12px; cursor:pointer }} button:hover {{ background:#fafafa }} button:focus-visible,input:focus-visible {{ outline:2px solid #0070f3; outline-offset:2px }} input {{ width:min(100%,520px); color:var(--text); background:var(--surface); box-shadow:var(--shadow); border:0; border-radius:6px; padding:10px 12px }}
::selection {{ background:#0070f322; color:#171717 }} .shell {{ width:min(1280px,100%); margin:auto; padding:32px clamp(16px,4vw,48px) 64px }} .masthead {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-start; padding:12px 0 32px; border-bottom:1px solid #171717 }}
.eyebrow {{ color:var(--muted); font:500 12px/1.2 Geist Mono,ui-monospace,monospace; letter-spacing:.06em; text-transform:uppercase }} h1 {{ margin:12px 0 10px; max-width:760px; font-size:clamp(36px,5vw,64px); font-weight:600; line-height:1.03; letter-spacing:-.055em }} .lede {{ max-width:720px; margin:0; color:var(--muted); font-size:16px }} .tools {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; min-width:250px }}
.hero-grid {{ display:grid; grid-template-columns:minmax(0,1.2fr) repeat(3,minmax(150px,1fr)); gap:16px; margin:32px 0 24px }} .hero-score,.metric {{ background:var(--surface); box-shadow:var(--shadow); border:0; border-radius:8px; padding:20px }} .hero-score {{ background:#171717; color:#fff; box-shadow:0 0 0 1px #171717,0 2px 2px rgba(0,0,0,.04) }} .hero-score .label {{ color:#a1a1aa }} .label {{ color:var(--muted); font-size:12px }} .hero-number {{ display:block; margin:7px 0 2px; color:#fff; font:600 52px/1 Geist,ui-sans-serif,sans-serif; letter-spacing:-.055em }} .metric-number {{ display:block; margin-top:8px; font-size:26px; font-weight:600; letter-spacing:-.03em }}
.matrix-section {{ margin:0 0 30px }} .matrix-grid {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:12px }} .matrix-card {{ min-width:0; padding:16px; background:var(--surface); box-shadow:var(--shadow); border:0; border-radius:8px }} .matrix-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:8px }} .matrix-head span {{ color:var(--muted); font-size:12px }} .matrix-head strong {{ color:var(--text); font-size:22px; font-weight:600; letter-spacing:-.03em }} .matrix-card small {{ display:block; margin-top:8px; color:var(--muted); font-size:11px }} .matrix-bar {{ height:5px; margin-top:12px; background:#ebebeb; border-radius:99px; overflow:hidden }} .matrix-bar span {{ display:block; height:100%; background:var(--blue); border-radius:inherit }}
.section-heading {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; margin:40px 0 12px }} h2 {{ margin:0; font-size:24px; font-weight:600; line-height:1.2; letter-spacing:-.03em }} .count,.note {{ color:var(--muted); font-size:12px }} .note {{ margin:0 0 10px }} .table-wrap {{ overflow:auto; box-shadow:var(--shadow); border:0; border-radius:8px; background:var(--surface) }} table {{ width:100%; border-collapse:collapse; min-width:560px }} th,td {{ padding:10px 14px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top }} th {{ color:var(--muted); background:#fafafa; font:500 11px/1.2 Geist Mono,ui-monospace,monospace; letter-spacing:.06em; text-transform:uppercase; position:sticky; top:0 }} tr:last-child td {{ border-bottom:0 }} tbody tr:hover {{ background:#fafafa }} code,.value,.score-value {{ font-family:Geist Mono,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace }} code {{ color:#0070f3; overflow-wrap:anywhere }} .value,.score-value {{ text-align:right; white-space:nowrap }} .score-value {{ color:#0070f3; font-weight:600 }} .score-track {{ display:block; width:180px; max-width:22vw; height:6px; background:#ebebeb; border-radius:99px; overflow:hidden }} .score-track span {{ display:block; height:100%; background:#0070f3; border-radius:inherit }} .footer {{ margin-top:64px; color:var(--muted); font-size:12px; border-top:1px solid #171717; padding-top:16px }}
@media (max-width:1100px) {{ .matrix-grid {{ grid-template-columns:repeat(3,minmax(0,1fr)) }} }} @media (max-width:850px) {{ .masthead {{ display:block }} .tools {{ justify-content:flex-start; margin-top:16px }} .hero-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)) }} .hero-score {{ grid-column:1/-1 }} }} @media (max-width:480px) {{ .shell {{ padding-inline:12px }} .hero-grid {{ grid-template-columns:1fr }} .hero-score {{ grid-column:auto }} .matrix-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)) }} h1 {{ font-size:34px }} .score-track {{ max-width:120px }} }}
</style></head><body><main class="shell">
<header class="masthead"><div><div class="eyebrow">NYXURI / 性能基准</div><h1>Shell 运行画像</h1><p class="lede">先看关键指标和分组评分，再查看完整数字证据。</p></div><div class="tools"><input id="filter" type="search" placeholder="筛选数字路径…" aria-label="筛选数字路径"><button id="theme" type="button">深色模式</button></div></header>
<section class="hero-grid" aria-label="Benchmark summary"><div class="hero-score"><span class="label">综合得分</span><strong class="hero-number">{html.escape(composite_text)}</strong><span class="label">满分 100</span></div><div class="metric"><span class="label">分项数量</span><strong class="metric-number">{score_count}</strong></div><div class="metric"><span class="label">冷启动轮数</span><strong class="metric-number">{html.escape(_text(runs))}</strong></div><div class="metric"><span class="label">每个 IPC 方法轮数</span><strong class="metric-number">{html.escape(_text(ipc_runs))}</strong></div></section>
<div id="report">{body}</div><footer class="footer">数据由 Nyxuri Shell Benchmark 生成。<code>null</code> 表示当前环境不可用或无法进行合法比较。</footer>
</main><script>
const filter=document.querySelector('#filter');filter.addEventListener('input',()=>{{const q=filter.value.trim().toLowerCase();document.querySelectorAll('tbody tr').forEach(row=>row.hidden=Boolean(q&&!row.textContent.toLowerCase().includes(q)))}});
document.querySelector('#theme').addEventListener('click',event=>{{const root=document.documentElement;const dark=root.dataset.theme==='dark';root.dataset.theme=dark?'light':'dark';event.target.textContent=dark?'深色模式':'浅色模式';if(!dark){{root.style.setProperty('--bg','#0a0a0a');root.style.setProperty('--surface','#111');root.style.setProperty('--surface2','#1a1a1a');root.style.setProperty('--line','#2e2e2e');root.style.setProperty('--text','#ededed');root.style.setProperty('--muted','#a1a1aa');root.style.setProperty('--accent','#3291ff');root.style.setProperty('--blue','#3291ff');root.style.setProperty('--shadow','rgba(255,255,255,.12) 0 0 0 1px,rgba(0,0,0,.35) 0 2px 2px')}}else location.reload()}});
</script></body></html>'''
