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

    def test_agents_md_exists_and_authoritative(self):
        """AGENTS.md must exist at repository root and contain imperative sections."""
        self.assertTrue(self.agents_md.is_file(), "AGENTS.md must exist at root")
        content = self.agents_md.read_text(encoding="utf-8")
        self.assertGreater(len(content), 2000, "AGENTS.md must not be empty or truncated")
        self.assertIn("最高优先级", content)
        self.assertIn("llms-wiki/llms.txt", content)

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
        """Ensure absorbed domain topics are strictly indexed in llms.txt."""
        content = self.llms_txt.read_text(encoding="utf-8")
        for topic in ("i18n.md", "assets-deploy.md", "backup-snapshot.md", "modules.md", "packaging.md"):
            self.assertIn(topic, content, f"Domain topic {topic} must be indexed in llms.txt")


if __name__ == "__main__":
    unittest.main()
