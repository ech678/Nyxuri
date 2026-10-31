"""Deploy subpackage — atomic swap, manifest, templates, forms, and the
deploy orchestrator.

Re-exports keep external imports shallow (§13). For test patching, address the
defining submodule directly (e.g. nyxuri.deploy.atomic.atomic_replace_item).
"""

from nyxuri.deploy.atomic import atomic_replace_item
from nyxuri.deploy.manifest import (
    ModuleManifest,
    load_manifest,
    load_manifest_for,
    discover_manifest_apps,
    discover_deployable_apps,
    discover_optional_apps,
)
from nyxuri.deploy.templates import _phase_render_templates
from nyxuri.deploy.forms import (
    InvalidActiveFormError,
    read_active_form,
    write_active_form,
    resolve_form_src,
)
from nyxuri.deploy.deploy import (
    config_item_dest,
    config_item_src,
    discover_config_items,
    _phase_atomic_deployment,
    _phase_post_install_services,
    render_completion_screen,
    deploy_selected_configs,
    run_user_hooks,
    test_deploy,
)

__all__ = [
    "atomic_replace_item", "discover_config_items", "deploy_selected_configs",
    "render_completion_screen",
    "run_user_hooks", "test_deploy",
    "read_active_form", "write_active_form", "InvalidActiveFormError", "resolve_form_src",
    "load_manifest", "load_manifest_for", "discover_manifest_apps",
    "discover_deployable_apps", "discover_optional_apps", "ModuleManifest",
]
