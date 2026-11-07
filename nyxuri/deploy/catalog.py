"""Plugin Catalog: discovery, blueprint loading, and dependency ordering."""

from pathlib import Path
from typing import List, Tuple

from nyxuri.system.env import get_env, safe_child
from nyxuri.deploy.manifest import ModuleManifest, load_manifest

_METADATA_NAMES = frozenset({"__pycache__"})
SHELL_NAMESPACE = "shell."
_RESERVED_PREFIXES = (SHELL_NAMESPACE, "nyxuri.")


def _namespace_roots() -> List[Tuple[Path, str]]:
    env = get_env()
    return [
        (env.plugins_src, ""),
        (env.shell_units_src, SHELL_NAMESPACE),
        (env.data_dir / "plugins", ""),
    ]


def _decisive_roots(plugin_id: str) -> List[Tuple[Path, str]]:
    matches = [(root, p) for root, p in _namespace_roots() if plugin_id.startswith(p)]
    if not matches:
        return []
    best = max(len(p) for _, p in matches)
    return [(root, p) for root, p in matches if len(p) == best]


def plugin_ids() -> list[str]:
    """Sorted ids of every directory plugin across all blueprint roots."""
    data_root = get_env().data_dir / "plugins"
    out: list[str] = []
    for root, prefix in _namespace_roots():
        if not root.is_dir():
            continue
        third_party = root == data_root
        out.extend(
            prefix + p.name
            for p in root.iterdir()
            if p.is_dir()
            and not p.is_symlink()
            and p.name not in _METADATA_NAMES
            and not (third_party and p.name.startswith(_RESERVED_PREFIXES))
        )
    return sorted(out)


def plugin_dir(plugin_id: str) -> Path | None:
    for root, prefix in _decisive_roots(plugin_id):
        src = safe_child(root, plugin_id[len(prefix):])
        if src is not None and src.is_dir():
            return src
    return None


def plugin_origin(plugin_id: str) -> str:
    src = plugin_dir(plugin_id)
    if src is None:
        return ""
    env = get_env()
    if src.is_relative_to(env.data_dir / "plugins"):
        return "third-party"
    if src.is_relative_to(env.shell_units_src):
        return "shell"
    return "official"


def load_plugin(plugin_id: str) -> ModuleManifest:
    for root, prefix in _decisive_roots(plugin_id):
        src = safe_child(root, plugin_id[len(prefix):])
        if src is not None and src.is_dir():
            origin = "third-party" if root == get_env().data_dir / "plugins" else "official"
            m = load_manifest(src, namespace=prefix, origin=origin)
            if root == get_env().data_dir / "plugins" and (m.post_install or m.post_remove):
                raise ValueError(
                    f"third-party plugin '{plugin_id}' declares lifecycle hooks "
                    "(post_install / post_remove) — not accepted in v1"
                )
            return m
    raise KeyError(f"unknown plugin: {plugin_id}")


def dependency_graph() -> dict[str, list[str]]:
    return {uid: load_plugin(uid).dependencies for uid in plugin_ids()}


def resolve_order(graph: dict[str, list[str]]) -> list[str]:
    """Return plugin ids in dependency-safe enable order (Kahn's algorithm)."""
    in_degree = {u: 0 for u in graph}
    for u, deps in graph.items():
        for d in deps:
            if d in in_degree:
                in_degree[u] += 1

    queue = [u for u, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        curr = queue.pop(0)
        order.append(curr)
        for u, deps in graph.items():
            if curr in deps:
                in_degree[u] -= 1
                if in_degree[u] == 0:
                    queue.append(u)

    if len(order) != len(graph):
        raise ValueError("Cyclic dependency detected in plugins")
    return order
