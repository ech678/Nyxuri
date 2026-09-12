"""Optional installable modules — fcitx skin, greeter, GTK theme.

Each module ships the same install | status | uninstall triad. Re-exports keep
external imports shallow (§13: 子包用 __init__.py re-export 关键符号).
"""

from nyxniri.modules.fcitx import (
    fcitx5_installed,
    fcitx_enabled,
    fcitx_install,
    fcitx_status,
    fcitx_status_label,
    fcitx_uninstall,
    fcitx_templates_registered,
    fcitx_reload,
    fcitx_trigger_render,
)
from nyxniri.modules.fisher import (
    fisher_installed,
    fisher_status_label,
    fisher_install,
    fisher_status,
    fisher_uninstall,
)
from nyxniri.modules.greeter import (
    greeter_installed,
    greeter_install,
    greeter_status,
    greeter_status_label,
    greeter_uninstall,
)
from nyxniri.modules.gtktheme import (
    gtktheme_registered,
    gtktheme_rendered,
    gtktheme_status_label,
    gtktheme_trigger_render,
    gtktheme_install,
    gtktheme_status,
    gtktheme_uninstall,
)

__all__ = [
    "fcitx5_installed", "fcitx_enabled", "fcitx_install", "fcitx_status",
    "fcitx_status_label", "fcitx_uninstall",
    "fcitx_templates_registered", "fcitx_reload",
    "fcitx_trigger_render",
    "fisher_installed", "fisher_status_label", "fisher_install", "fisher_status",
    "fisher_uninstall",
    "greeter_installed", "greeter_install", "greeter_status",
    "greeter_status_label", "greeter_uninstall",
    "gtktheme_registered", "gtktheme_rendered", "gtktheme_status_label",
    "gtktheme_trigger_render", "gtktheme_install", "gtktheme_status",
    "gtktheme_uninstall",
]
