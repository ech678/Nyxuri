"""Failure boundary for module install and uninstall hooks."""

import configparser
from functools import wraps

from nyxniri.core import log_msg
from nyxniri.i18n import text


def module_action(action):
    """Expected file/config failures return False; interruption still propagates."""
    @wraps(action)
    def run(*args, **kwargs) -> bool:
        try:
            return action(*args, **kwargs)
        except (OSError, ValueError, configparser.Error) as error:
            log_msg("ERROR", f"{action.__name__}: {error}")
            print(text(f"操作未完成: {error}", f"Operation incomplete: {error}"))
            return False
    return run
