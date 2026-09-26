"""State management — configuration snapshots and uninstall.

backup: snapshot / rollback / delete (the "save state" verbs).
uninstall: checkbox-style removal (§8). Path primitives copy_path /
remove_path live in core (shared with deploy.atomic); re-exports here keep
external imports shallow (§13).
"""

from nyxuri.state.backup import (
    backup_configs,
    rollback_configs,
    list_backups,
    delete_backup,
    get_all_backups,
    get_backup_base_dir,
)
from nyxuri.state.uninstall import uninstall_nyxuri, uninstall_nyxniri
from nyxuri.state.ledger import active_shell, ledger_path, read_ledger, update_ledger

__all__ = [
    "backup_configs", "rollback_configs", "list_backups", "delete_backup",
    "get_all_backups", "get_backup_base_dir", "uninstall_nyxuri", "uninstall_nyxniri",
    "active_shell", "ledger_path", "read_ledger", "update_ledger",
]
