"""PluginRegistry — the blueprint domain's single entry (plugin-model.md §2).

The only kernel module that scans plugin blueprints and reads manifests.
Adding a plugin = adding a directory (plus an optional ``manifest.toml``) —
zero kernel code change. TOML parsing is delegated to
``nyxuri.deploy.manifest`` (pure stdlib); state.json is never touched
here — that is ledger's monopoly.

Blueprint roots (KM4, plugin-model.md §6)::

    plugins/       → bare ids          (kitty, niri, ...)
    shell/plugins/ → ``shell.`` ids    (shell.bar, shell.dock, ...)
    data_dir/plugins/ → manifest-id ids (third-party, reverse-DNS; S1)

The prefix comes from the ROOT, not from per-id special-casing: the kernel
only ever sees dotted ids and resolves them back through the same table.
The third-party root derives ids from the directory name itself (the full
reverse-DNS id), and inside a prefix group the repo blueprint wins — a
third-party plugin can never shadow an official one, and reserved
namespaces stay unclaimable. Shell plugins are runtime by kinds (no
``config`` kind) — a payload-less existence whose living area is the
running host, never files under ~/.config.
"""

from pathlib import Path

from nyxuri.core import get_env
from nyxuri.deploy.manifest import ModuleManifest, load_manifest

_METADATA_NAMES = frozenset({"__pycache__"})
SHELL_NAMESPACE = "shell."

# Reserved id namespaces (manifest-schema.md): a third-party directory can
# never claim them — namespaces are declared by roots, and the data root
# derives ids from raw directory names.
_RESERVED_PREFIXES = (SHELL_NAMESPACE, "nyxuri.")


def _namespace_roots() -> "list[tuple[Path, str]]":
    """Blueprint roots with their id prefixes; longest prefix wins lookup.

    Order matters inside a prefix group: the repo blueprint is checked
    before the third-party data root, so an official plugin of the same
    name always wins (S1 shadow rule).
    """
    env = get_env()
    return [
        (env.plugins_src, ""),
        (env.shell_units_src, SHELL_NAMESPACE),
        (env.data_dir / "plugins", ""),
    ]


def _decisive_roots(plugin_id: str) -> "list[tuple[Path, str]]":
    """Roots that may resolve ``plugin_id``: the longest prefix group.

    The longest matching prefix is decisive — a ``shell.*`` id resolves
    only in the shell root and a bare id never falls into it, even when a
    same-named directory exists there (namespaces are declared by roots,
    never by directory names). Within the group, declaration order is
    preserved: official blueprint before third-party data root.
    """
    matches = [(root, p) for root, p in _namespace_roots() if plugin_id.startswith(p)]
    if not matches:
        return []
    best = max(len(p) for _, p in matches)
    return [(root, p) for root, p in matches if len(p) == best]


def plugin_ids() -> list[str]:
    """Sorted ids of every directory plugin across all blueprint roots.

    A plugin is a directory. Metadata entries are not plugins; symlinked
    entries are not plugins either (禁软链 is enforced at the scan layer,
    matching ``discover_manifest_apps``); a third-party directory claiming
    a reserved namespace stays invisible — the add verb rejects those
    loudly, the scan layer just never surfaces them.
    """
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
    """On-disk blueprint directory for a plugin, or None if it does not exist.

    The longest matching namespace prefix is decisive (``_decisive_roots``);
    inside that group the repo blueprint wins over the third-party data
    root. ``safe_child`` refuses symlinks, so a symlinked plugin directory
    is simply absent.
    """
    from nyxuri.core import safe_child

    for root, prefix in _decisive_roots(plugin_id):
        src = safe_child(root, plugin_id[len(prefix):])
        if src is not None and src.is_dir():
            return src
    return None


def plugin_origin(plugin_id: str) -> str:
    """Which root the plugin resolves from: ``official`` / ``shell`` / ``third-party``.

    The hook gate (v1 三方拒钩子) and the lifecycle verbs both key off this —
    origin is a property of the resolving root, never of the manifest content.
    """
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
    """Load one plugin's resolved manifest; zero-config defaults applied.

    The manifest ``id`` is the registry id itself — new-form manifests declare
    it and ``load_manifest`` rejects any drift from the root-derived id.
    Third-party plugins additionally reject lifecycle hooks at load time
    (v1 安全立场: 安装一步绝不执行包内代码, manifest-schema.md 钩子章) —
    the same check the add verb runs, because this IS the loader.
    """
    from nyxuri.core import safe_child

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
    """``{plugin id: declared plugin dependencies}`` for the whole blueprint.

    Feed this straight into ``nyxuri.resolver.resolve_order``; the two
    modules never import each other — the caller composes them.
    """
    return {uid: load_plugin(uid).dependencies for uid in plugin_ids()}
