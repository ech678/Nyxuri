"""Tests verifying AI specification integrity and preventing documentation drift."""

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

    def test_agents_md_exists_and_compact(self):
        """AGENTS.md must exist at root, be concise (~100 lines), and reference routing."""
        self.assertTrue(self.agents_md.is_file(), "AGENTS.md must exist at root")
        content = self.agents_md.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        self.assertLess(len(lines), 150, f"AGENTS.md should stay concise, got {len(lines)} lines")
        self.assertIn("llms-wiki/llms.txt", content)
        self.assertIn("必读 Wiki 契约", content)

    def test_llms_txt_links_resolve(self):
        """Every link referenced in llms-wiki/llms.txt must resolve to an existing non-empty file."""
        self.assertTrue(self.llms_txt.is_file(), "llms-wiki/llms.txt must exist")
        content = self.llms_txt.read_text(encoding="utf-8")
        links = re.findall(r"\[.*?\]\((.*?)\)", content)
        self.assertGreater(len(links), 15, "llms.txt should index core architecture topics")

        for link in links:
            if link.startswith("../"):
                target = (self.root_dir / link.replace("../", "")).resolve()
            else:
                target = (self.wiki_dir / link).resolve()
            self.assertTrue(target.exists(), f"Broken link in llms.txt: {link} -> {target}")
            self.assertGreater(target.stat().st_size, 0, f"Referenced file is empty: {target}")

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
        ):
            self.assertIn(topic, content, f"Domain topic {topic} must be indexed in llms.txt")

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
