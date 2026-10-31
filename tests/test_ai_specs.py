"""Tests verifying AI specification integrity and preventing documentation drift.

Gate set for llms-wiki/docs-charter.md:
  - AGENTS.md stays compact and routes to the wiki
  - llms-wiki/llms.txt links resolve and no live page is orphaned
  - Live-area relative links resolve (upstream/ + archive/ are frozen and exempt)
  - ROADMAP status vocabulary stays canonical
  - CLI commands stay documented in operation-map.md
  - Humans-wiki and README links resolve and anchors are valid
  - Dissolved paths (configs/, assets/wallpapers) banned from docs
  - CLI help text clean of retired commands
  - Presets and modular Parts match declared contract
"""

import re
import unittest
from pathlib import Path


class TestAISpecs(unittest.TestCase):
    """Ensure AI directives, architecture wiki, and index links stay unbroken."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.wiki_dir = self.root_dir / "llms-wiki"
        self.llms_txt = self.wiki_dir / "llms.txt"
        self.agents_md = self.root_dir / "AGENTS.md"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _live_md_files(self):
        """Live-area markdown: both AGENTS, both ROADMAPs, docs-charter, and
        every llms-wiki page outside upstream/ and archive/."""
        files = [
            self.root_dir / "AGENTS.md",
            self.root_dir / "ROADMAP.md",
            self.root_dir / "shell" / "AGENTS.md",
            self.root_dir / "shell" / "ROADMAP.md",
        ]
        for page in self.wiki_dir.rglob("*.md"):
            rel = page.relative_to(self.wiki_dir).as_posix()
            if rel.startswith(("upstream/", "archive/")):
                continue
            files.append(page)
        return files

    @staticmethod
    def _relative_links(text):
        for match in re.findall(r"\]\(([^)]+)\)", text):
            link = match.split("#", 1)[0].strip()
            if link and not link.startswith(("http://", "https://", "mailto:")):
                yield link

    # ------------------------------------------------------------------
    # AGENTS.md contract
    # ------------------------------------------------------------------

    def test_agents_md_exists_and_compact(self):
        """AGENTS.md must exist at root, be concise (~100 lines), and reference routing."""
        self.assertTrue(self.agents_md.is_file(), "AGENTS.md must exist at root")
        content = self.agents_md.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        self.assertLess(len(lines), 150, f"AGENTS.md should stay concise, got {len(lines)} lines")
        self.assertIn("llms-wiki/llms.txt", content)
        self.assertIn("必读 Wiki 契约", content)

    def test_agents_md_links_resolve(self):
        """Every relative link in both AGENTS.md files must resolve."""
        for agents in (self.agents_md, self.root_dir / "shell" / "AGENTS.md"):
            for link in self._relative_links(agents.read_text(encoding="utf-8")):
                target = (agents.parent / link).resolve()
                self.assertTrue(target.exists(), f"Broken link in {agents.name}: {link} -> {target}")

    # ------------------------------------------------------------------
    # llms.txt index
    # ------------------------------------------------------------------

    def test_llms_txt_links_resolve(self):
        """Every link referenced in llms-wiki/llms.txt must resolve to an existing non-empty file."""
        self.assertTrue(self.llms_txt.is_file(), "llms-wiki/llms.txt must exist")
        content = self.llms_txt.read_text(encoding="utf-8")
        links = re.findall(r"\[.*?\]\((.*?)\)", content)
        self.assertGreater(len(links), 15, "llms.txt should index core architecture topics")

        for link in links:
            target = (self.wiki_dir / link).resolve()
            self.assertTrue(target.exists(), f"Broken link in llms.txt: {link} -> {target}")
            self.assertGreater(target.stat().st_size, 0, f"Referenced file is empty: {target}")

    def test_llms_txt_covers_all_live_pages(self):
        """Bidirectional index closure: every live wiki page is indexed in llms.txt."""
        content = self.llms_txt.read_text(encoding="utf-8")
        for page in self._live_md_files():
            if page == self.llms_txt or not page.is_relative_to(self.wiki_dir):
                continue
            name = page.relative_to(self.wiki_dir).as_posix()
            self.assertIn(f"({name})", content, f"Live page not indexed: {name}")

    def test_new_domain_topics_indexed(self):
        """Ensure domain topics and guidelines are strictly indexed in llms.txt."""
        content = self.llms_txt.read_text(encoding="utf-8")
        for topic in (
            "i18n.md",
            "assets-deploy.md",
            "backup-snapshot.md",
            "packaging.md",
            "writing-voice.md",
            "changelog-spec.md",
            "tui-charter.md",
            "vision.md",
            "agent-rules-provenance.md",
            "docs-charter.md",
        ):
            self.assertIn(topic, content, f"Domain topic {topic} must be indexed in llms.txt")

    # ------------------------------------------------------------------
    # Live-area link hygiene (docs-charter: L2 pages must not dangle)
    # ------------------------------------------------------------------

    def test_live_docs_links_resolve(self):
        """Every relative link in the live area must resolve; upstream/ and archive/ are frozen-exempt."""
        checked = 0
        for page in self._live_md_files():
            for link in self._relative_links(page.read_text(encoding="utf-8")):
                target = (page.parent / link).resolve()
                self.assertTrue(
                    target.exists(),
                    f"Broken live-area link in {page.relative_to(self.root_dir)}: {link} -> {target}",
                )
                checked += 1
        self.assertGreater(checked, 30, "Live-area link scan should cover the real doc graph")

    def test_live_docs_do_not_reference_dissolved_paths(self):
        """Retired locations must not creep back into live docs."""
        banned = ("shell/wiki/", "wiki/tree-inventory", "wiki/upstream-docs", "noctalia-llm-docs")
        for page in self._live_md_files():
            text = page.read_text(encoding="utf-8")
            for fragment in banned:
                self.assertNotIn(
                    fragment,
                    text,
                    f"{page.relative_to(self.root_dir)} still references retired path: {fragment}",
                )

        # Stricter checks for paths retired in KM3.5 (exempting plugin-model.md §7 death registry and ROADMAP ledger)
        km35_banned = ("configs/", "template_registry")
        for page in self._live_md_files():
            if page.name in ("plugin-model.md", "ROADMAP.md"):
                continue
            text = page.read_text(encoding="utf-8")
            for fragment in km35_banned:
                self.assertNotIn(
                    fragment,
                    text,
                    f"{page.relative_to(self.root_dir)} still references retired path: {fragment}",
                )

    # ------------------------------------------------------------------
    # ROADMAP status vocabulary (docs-charter: canonical status words)
    # ------------------------------------------------------------------

    def test_roadmap_status_vocabulary(self):
        """ROADMAP.md ledger rows may only use the five canonical statuses."""
        allowed = {"待开始", "进行中", "阻断", "待验收", "已完成"}
        # 1. shell/ROADMAP.md
        shell_roadmap = (self.root_dir / "shell" / "ROADMAP.md").read_text(encoding="utf-8")
        for match in re.findall(r"^\| (R[^|*]+) \| ([^|]+) \| ([^|]+) \|$", shell_roadmap, re.MULTILINE):
            stage, _, status = (part.strip() for part in match)
            self.assertIn(status, allowed, f"Non-canonical status for {stage}: {status}")

        # 2. root ROADMAP.md
        root_roadmap = (self.root_dir / "ROADMAP.md").read_text(encoding="utf-8")
        for match in re.findall(r"^\| (KM[^|*]+) \| ([^|]+) \| ([^|]+) \|$", root_roadmap, re.MULTILINE):
            stage, _, status = (part.strip() for part in match)
            self.assertIn(status, allowed, f"Non-canonical status for {stage}: {status}")

    # ------------------------------------------------------------------
    # Plugin-model death registry (plugin-model.md §7, two-step enforcement)
    # ------------------------------------------------------------------

    def test_death_registry_cleared(self):
        """KM5 gate: the death registry (plugin-model.md §7) must be EMPTY of
        un-enforced rows — every registered object has reached its execution
        stage and carries the (已执法) mark. 退役清单不空，KM5 不算完成."""
        content = (self.wiki_dir / "plugin-model.md").read_text(encoding="utf-8")
        death_table_started = False
        for line in content.splitlines():
            if line.startswith("| 死刑对象"):
                death_table_started = True
                continue
            if not death_table_started:
                continue
            if not line.startswith("|"):
                break  # end of the §7 table
            if "---" in line:
                continue
            self.assertIn(
                "已执法", line,
                f"un-enforced death-row object remains: {line}",
            )

    def test_km5_death_row_enforced(self):
        """KM5 enforcement step: install.sh demoted to a one-time bootstrap
        handing off to the dedicated launcher; nyxuri/migrations/ liquidated;
        the §7 install.sh row marked enforced. The interactive menu world was
        retained by author ruling — the cli.py death-row registration was
        withdrawn (see ROADMAP KM5)."""
        root = self.root_dir
        # 1. §7 install.sh row marked enforced; the withdrawn cli.py row is gone.
        content = (self.wiki_dir / "plugin-model.md").read_text(encoding="utf-8")
        rows = [line for line in content.splitlines() if line.startswith("|")]
        self.assertTrue(
            any("`install.sh` 安装器职责" in row and "KM5（已执法" in row for row in rows),
            "death-row object 'install.sh' must be marked KM5（已执法） in plugin-model.md §7",
        )
        self.assertFalse(
            any("硬编码专用命令" in row for row in rows),
            "the withdrawn cli.py death-row registration must be deleted from §7",
        )

        # 2. Physical absence of migrations; presence of the launcher.
        self.assertFalse((root / "nyxuri" / "migrations").exists())
        launcher = root / "nyxuri" / "launcher.sh"
        self.assertTrue(launcher.is_file())
        self.assertTrue(launcher.stat().st_mode & 0o111, "launcher must be executable")

        # 3. Engine holds zero references to the retired package.
        for py in sorted((root / "nyxuri").rglob("*.py")):
            text = py.read_text(encoding="utf-8")
            self.assertNotIn(
                "nyxuri.migrations", text,
                f"{py.relative_to(root)} still references nyxuri.migrations",
            )

        # 4. install.sh = one-time bootstrap: hands off to the launcher with no
        # argument passthrough, and its completeness checklist no longer
        # enumerates the retired migrations package.
        install_sh = (root / "install.sh").read_text(encoding="utf-8")
        self.assertIn("nyxuri/launcher.sh", install_sh)
        self.assertNotIn("migrations", install_sh)

    def test_km3_module_death_row_enforced(self):
        """KM3 enforcement step: nyxuri/modules/ is physically deleted — the
        dedicated business modules live on as configs/<plugin>/hooks/ scripts,
        the engine holds zero references, and §7 marks the row enforced.
        """
        # 1. §7 row marked enforced.
        content = (self.wiki_dir / "plugin-model.md").read_text(encoding="utf-8")
        rows = [line for line in content.splitlines() if line.startswith("|")]
        self.assertTrue(
            any("nyxuri/modules/" in row and "KM3（已执法" in row for row in rows),
            "death-row object 'nyxuri/modules/' must be marked KM3（已执法） in plugin-model.md §7",
        )

        # 2. Physical absence of the package.
        self.assertFalse((self.root_dir / "nyxuri" / "modules").exists())

        # 3. Zero engine references to the retired package.
        for py in (self.root_dir / "nyxuri").rglob("*.py"):
            self.assertNotIn(
                "nyxuri.modules",
                py.read_text(encoding="utf-8"),
                f"{py.relative_to(self.root_dir)} still references the retired nyxuri.modules package",
            )

        # 4. The retired wiki page is gone and not indexed.
        self.assertFalse((self.wiki_dir / "modules.md").exists())
        llms_txt = (self.wiki_dir / "llms.txt").read_text(encoding="utf-8")
        self.assertNotIn("modules.md", llms_txt)

        # 5. The plugin-owned hook scripts took over.
        hooks = self.root_dir / "plugins"
        for plugin, name in (
            ("fcitx5-rime", "activate"), ("fcitx5-rime", "deactivate"),
            ("fish", "install-fisher"), ("fish", "remove-fisher"),
            ("greeter", "activate"), ("greeter", "deactivate"),
            ("noctalia", "render-gtk"), ("noctalia", "remove-gtk-css"),
        ):
            self.assertTrue((hooks / plugin / "hooks" / name).is_file(), f"{plugin}/hooks/{name}")

    def test_km1_death_row_enforced(self):
        """KM1 enforcement step: the three sidecar mechanisms are physically
        deleted — their registration rows are retired, §7 marks them enforced,
        the blueprint carries no trace, and the engine holds zero references.
        """
        # 1. §7 rows marked enforced.
        content = (self.wiki_dir / "plugin-model.md").read_text(encoding="utf-8")
        rows = [line for line in content.splitlines() if line.startswith("|")]
        for name in (".optional-apps.toml", "starship.toml.module.toml", "*.module.toml"):
            self.assertTrue(
                any(name in row and "KM1（已执法" in row for row in rows),
                f"death-row object '{name}' must be marked KM1（已执法） in plugin-model.md §7",
            )

        # 2. Physical absence in the blueprint.
        configs = self.root_dir / "plugins"
        self.assertFalse((configs / ".optional-apps.toml").exists())
        self.assertFalse((configs / "starship.toml").exists())
        self.assertEqual(list(configs.glob("**/*.module.toml")), [])
        # The single-file degenerate was upgraded to a proper plugin directory.
        self.assertTrue((configs / "starship" / "starship.toml").is_file())
        self.assertTrue((configs / "starship" / "manifest.toml").is_file())

        # 3. Engine source holds zero references to the dead names.
        for py in sorted((self.root_dir / "nyxuri").rglob("*.py")):
            text = py.read_text(encoding="utf-8")
            for dead in (".module.toml", ".optional-apps.toml"):
                self.assertNotIn(dead, text, f"{py.relative_to(self.root_dir)} still references {dead}")

    # ------------------------------------------------------------------
    # CLI command mapping
    # ------------------------------------------------------------------

    def test_km3_5_death_row_enforced(self):
        """KM3.5 enforcement step: the old world is physically gone — blueprint
        renamed, assets bypass executed, zero-file fake plugins relocated,
        template registry deleted, kernel physically layered. R0-2 supersedes
        the catalog relocation: the declarations moved back into the blueprint
        as manifest-only plugin dirs."""
        root = self.root_dir
        # 1. §7 rows marked enforced.
        content = (self.wiki_dir / "plugin-model.md").read_text(encoding="utf-8")
        rows = [line for line in content.splitlines() if line.startswith("|")]
        for name in ("RETIREMENTS", "template_registry", "17 个零文件假单元",
                     "`assets/` + `nyxuri/deploy/assets.py`", "蓝图正名 `configs/` → `units/`",
                     "根 `catalog.toml`"):
            stage = "KM3.5（已执法" if name != "根 `catalog.toml`" else "R0-2（已执法"
            self.assertTrue(
                any(name in row and stage in row for row in rows),
                f"death-row object '{name}' must be marked enforced in plugin-model.md §7",
            )

        # 2. Physical absence / presence.
        self.assertFalse((root / "configs").exists(), "blueprint must be renamed")
        plugins = root / "plugins"
        self.assertTrue(plugins.is_dir())
        self.assertFalse((root / "assets").exists())
        self.assertTrue((plugins / "wallpapers" / "hooks" / "install-pack").is_file())
        self.assertTrue((plugins / "wallpapers" / "manifest.toml").is_file())
        self.assertFalse((root / "nyxuri" / "template_registry.py").exists())
        self.assertFalse((root / "nyxuri" / "deps.py").exists(), "supply must live in pkg/")
        self.assertFalse((root / "nyxuri" / "network.py").exists())
        self.assertFalse((root / "nyxuri" / "doctor.py").exists())
        self.assertTrue((root / "nyxuri" / "sysdoctor.py").is_file())
        self.assertTrue((root / "nyxuri" / "core.py").is_file())
        self.assertFalse((root / "nyxuri" / "constants.py").exists(), "merged into core")
        self.assertFalse((root / "nyxuri" / "i18n.py").exists(), "merged into core")
        for sub in ("kernel", "desktop", "installer"):
            self.assertTrue((root / "nyxuri" / sub).is_dir(), sub)
        self.assertTrue((root / "packaging" / "gen-deps.py").is_file())
        self.assertFalse((root / "nyxuri" / "packaging").exists())
        self.assertFalse((root / "catalog.toml").exists(),
                         "R0-2 catalog 并轨：供给声明住各插件 manifest，根清单处决")
        self.assertFalse((root / "nyxuri" / "pkg" / "catalog.py").exists())

        # 3. The packages-only supply surface is executed: the 18 manifest-only
        # recommendation plugins are gone, no shipped manifest declares the
        # retired keys, and the blueprint is 13 real plugins.
        retired_keys = ("deploy", "detect")
        shipped = [d for d in plugins.iterdir() if d.is_dir()]
        for d in shipped:
            mpath = d / "manifest.toml"
            if mpath.is_file():
                text = mpath.read_text(encoding="utf-8")
                for dead in retired_keys:
                    for line in text.splitlines():
                        self.assertNotRegex(
                            line, rf"^\s*{dead}\s*=",
                            f"{d.name} still declares the retired key '{dead}'",
                        )
        self.assertEqual(len(shipped), 13, "supply execution must leave 13 real plugins")
        for gone in ("telegram", "steam", "vscode", "nautilus", "shelly", "quickshell"):
            self.assertFalse((plugins / gone).exists(), f"{gone} supply plugin must be gone")

        # 4. The engine holds zero references to the dead names.
        for py in sorted((root / "nyxuri").rglob("*.py")):
            text = py.read_text(encoding="utf-8")
            for dead in ("template_registry", "nyxuri.constants", "nyxuri.i18n",
                         "nyxuri.deps", "nyxuri.network", "deploy_wallpapers",
                         "pkg.catalog", "install_optional_apps",
                         "run_optional_apps_menu_loop", "deploy_declared"):
                self.assertNotIn(dead, text, f"{py.relative_to(root)} still references {dead}")
            # R0-2 步 5 追加：退役字段可能只剩「属性访问」消费者（字符串扫描
            # 抓不到）——`m.detect` 漏网曾让组件菜单在真实运行中直接崩溃。
            for dead_attr in (r"\.detect\b", r"\.deploy_declared\b"):
                self.assertNotRegex(
                    text, dead_attr,
                    f"{py.relative_to(root)} still reads the retired attribute {dead_attr}",
                )

        # 5. Contract line: declaration-only units keep their install path.
        self.assertIn("declaration-only", content)

        # 6. Test tree mirrors the source tree.
        tests = root / "tests"
        for sub in ("kernel", "deploy", "pkg", "state", "desktop", "installer",
                    "shell", "tools"):
            self.assertTrue((tests / sub).is_dir(), f"tests/{sub}")

    def test_cli_commands_documented_in_operation_map(self):
        """Ensure all CLI commands in cli.py COMMANDS are documented in operation-map.md."""
        from nyxuri.cli import COMMANDS

        op_map = (self.wiki_dir / "operation-map.md").read_text(encoding="utf-8")
        for cmd in COMMANDS:
            if cmd in ("-h", "--help"):
                continue
            self.assertIn(
                f"`{cmd}",
                op_map,
                f"CLI command '{cmd}' is implemented in cli.py but missing from operation-map.md",
            )

    # ------------------------------------------------------------------
    # Humans-wiki and README integrity gates
    # ------------------------------------------------------------------

    def test_human_docs_and_readme_links_resolve(self):
        """Relative links in humans-wiki/ and READMEs must resolve (with .md fallback)."""
        doc_files = [
            self.root_dir / "README.md",
            self.root_dir / "README.zh-CN.md",
        ] + list((self.root_dir / "humans-wiki").glob("*.md"))

        for doc in doc_files:
            text = doc.read_text(encoding="utf-8")
            for link in self._relative_links(text):
                target = (doc.parent / link).resolve()
                target_md = (doc.parent / f"{link}.md").resolve()
                self.assertTrue(
                    target.exists() or target_md.exists(),
                    f"Broken relative link in {doc.relative_to(self.root_dir)}: {link}",
                )

    def test_readme_wiki_anchors_valid(self):
        """GitHub Wiki URLs with anchors in READMEs must match actual heading slugs."""
        humans_wiki = self.root_dir / "humans-wiki"

        def _slugify(heading: str) -> str:
            slug = heading.strip().lower()
            slug = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", slug)
            return re.sub(r"\s+", "-", slug)

        for readme in (self.root_dir / "README.md", self.root_dir / "README.zh-CN.md"):
            content = readme.read_text(encoding="utf-8")
            wiki_links = re.findall(
                r"https://github\.com/[^/]+/Nyxuri/wiki/([A-Za-z0-9_-]+)(?:#([^\s\)\"]+))?",
                content,
            )
            for page_name, anchor in wiki_links:
                page_file = humans_wiki / f"{page_name}.md"
                self.assertTrue(
                    page_file.is_file(),
                    f"README references non-existent wiki page: {page_name} ({page_file})",
                )
                if anchor:
                    headings = re.findall(
                        r"^#+\s+(.+)$",
                        page_file.read_text(encoding="utf-8"),
                        re.MULTILINE,
                    )
                    slugs = [_slugify(h) for h in headings]
                    self.assertIn(
                        anchor,
                        slugs,
                        f"Anchor #{anchor} not found in headings of {page_name}.md (valid: {slugs})",
                    )

    def test_docs_banned_dissolved_paths(self):
        """Humans-wiki, READMEs, and plugin READMEs must not reference dissolved paths."""
        banned = ("configs/", "assets/wallpapers", "template_registry", "modules/gtktheme")
        doc_files = [
            self.root_dir / "README.md",
            self.root_dir / "README.zh-CN.md",
            self.root_dir / "plugins" / "noctalia" / "README.md",
        ] + list((self.root_dir / "humans-wiki").glob("*.md"))

        for doc in doc_files:
            text = doc.read_text(encoding="utf-8")
            for fragment in banned:
                self.assertNotIn(
                    fragment,
                    text,
                    f"{doc.relative_to(self.root_dir)} still references dissolved path: {fragment}",
                )

    def test_cli_help_no_retired_commands(self):
        """CLI help in translations.toml must not advertise retired commands."""
        import tomllib

        data = tomllib.loads(
            (self.root_dir / "nyxuri" / "translations.toml").read_text(encoding="utf-8")
        )
        cli_help = data.get("cli_help", {})
        retired = (
            "nyxuri purge",
            "nyxuri apps",
            "nyxuri wallpapers",
            "nyxuri report",
            "  purge ",
            "  apps ",
            "  wallpapers ",
            "  report ",
        )

        for lang in ("zh", "en"):
            help_text = cli_help.get(lang, "")
            for cmd in retired:
                self.assertNotIn(
                    cmd,
                    help_text,
                    f"cli_help[{lang}] contains retired command reference: '{cmd}'",
                )

    def test_documented_forms_contract(self):
        """Whole-axis forms and slot axes must adhere to the documented contract."""
        from nyxuri.desktop.forms import collect_forms
        from nyxuri.deploy.forms import list_slots

        kitty_forms = [name for name, _, _ in collect_forms("kitty")]
        self.assertIn("default", kitty_forms)
        self.assertIn("transparent", kitty_forms)

        niri_forms = [name for name, _, _ in collect_forms("niri")]
        self.assertEqual(niri_forms, ["default"])

        slots = list_slots("niri")
        self.assertIn("glow", slots)
        self.assertIn("effects", slots)
        self.assertEqual(
            set(slots["glow"]["variants"]),
            {"default", "glow", "glow-material-you"},
        )
        self.assertEqual(
            set(slots["effects"]["variants"]),
            {"default", "xray-blur"},
        )


if __name__ == "__main__":
    unittest.main()
