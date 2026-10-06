"""Tests verifying AI specification integrity and preventing documentation drift.

Gate set for llms-wiki/docs-charter.md:
  - AGENTS.md stays compact and routes to the wiki
  - llms-wiki/llms.txt links resolve and no live page is orphaned
  - Live-area relative links resolve (upstream/ + archive/ are frozen and exempt)
  - ROADMAP status vocabulary stays canonical
  - CLI commands stay documented in operation-map.md
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
            if page == self.llms_txt or page.parent != self.wiki_dir:
                continue
            name = page.relative_to(self.wiki_dir).as_posix()
            if name == "docs-charter.md":
                self.assertIn("(docs-charter.md)", content, f"Live page not indexed: {name}")
            else:
                self.assertIn(f"({name})", content, f"Live page not indexed: {name}")

    def test_new_domain_topics_indexed(self):
        """Ensure domain topics and guidelines are strictly indexed in llms.txt."""
        content = self.llms_txt.read_text(encoding="utf-8")
        for topic in (
            "i18n.md",
            "assets-deploy.md",
            "backup-snapshot.md",
            "modules.md",
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

    # ------------------------------------------------------------------
    # ROADMAP status vocabulary (docs-charter: canonical status words)
    # ------------------------------------------------------------------

    def test_shell_roadmap_status_vocabulary(self):
        """shell/ROADMAP.md ledger rows may only use the five canonical statuses."""
        roadmap = (self.root_dir / "shell" / "ROADMAP.md").read_text(encoding="utf-8")
        allowed = {"待开始", "进行中", "阻断", "待验收", "已完成"}
        for match in re.findall(r"^\| (R[^|*]+) \| ([^|]+) \| ([^|]+) \|$", roadmap, re.MULTILINE):
            stage, _, status = (part.strip() for part in match)
            self.assertIn(status, allowed, f"Non-canonical status for {stage}: {status}")

    # ------------------------------------------------------------------
    # CLI command mapping
    # ------------------------------------------------------------------

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


if __name__ == "__main__":
    unittest.main()
