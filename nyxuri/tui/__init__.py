"""Nyxuri TUI: record + activity area, one short inline Textual run per decision.

Textual lives only under nyxuri/tui/; the engine stays standard library.
Contract: llms-wiki/tui-design-system.md.
"""


def main() -> int:
    from nyxuri.tui.flow import run
    return run()
