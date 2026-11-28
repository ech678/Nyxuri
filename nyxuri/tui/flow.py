"""Glue between inline runs: decide in the activity area, act, write the record."""

from nyxuri.system.i18n import msg
from nyxuri.tui.app import CANCEL, Confirm
from nyxuri.tui.record import Record
from nyxuri.tui.workshop import Workshop
from nyxuri.ui.tui import describe_steps


def _confirm(record: Record, body, choices, default=0):
    answer = Confirm(body, choices, default).run_inline()
    if answer == CANCEL:
        record.result(None, msg("tui_cancelled"))
    return answer


def _report(record: Record, steps) -> None:
    for kind, line in describe_steps(steps):
        record.result(kind, line)


def _switch_on(record: Record, uid: str) -> bool:
    from nyxuri.deploy import catalog, engine
    from nyxuri.state import store
    from nyxuri.system.pkg import plugin_package_installer

    record.step(msg("tui_step_on", uid))
    enabled = {u for u, r in store.all_plugins().items() if r.get("state") == "enabled"}
    incoming = [u for u in engine.plan_on(uid) if u not in enabled]
    missing = [p for u in incoming for p in engine.missing_packages(catalog.load_plugin(u))]
    if missing:
        body = [msg("tui_on_packages", " ".join(missing))]
        if len(incoming) > 1:
            body.insert(0, msg("tui_on_closure", " → ".join(incoming)))
        answer = _confirm(record, body, [msg("tui_choice_install"), msg("tui_choice_cancel")])
        if answer == CANCEL:
            return False
        if answer != 0:
            record.result(None, msg("tui_skipped"))
            return True
    _report(record, engine.plugin_on(uid, install_packages=plugin_package_installer))
    return True


def _switch_off(record: Record, uid: str) -> bool:
    from nyxuri.deploy import engine

    record.step(msg("tui_step_off", uid))
    dependents = [u for u in engine.plan_off(uid) if u != uid]
    body = [msg("tui_off_body")]
    if dependents:
        body.append(msg("tui_off_cascade", ", ".join(dependents)))
    answer = _confirm(record, body, [msg("tui_choice_cancel"), msg("tui_choice_off")], default=0)
    if answer == CANCEL:
        return False
    if answer != 1:
        record.result(None, msg("tui_skipped"))
        return True
    _report(record, engine.plugin_off(uid, cascade=bool(dependents)))
    return True


def workshop(record: Record) -> bool:
    focus = None
    while True:
        answer = Workshop(focus).run_inline()
        if answer == CANCEL:
            record.step(msg("tui_workshop_title"))
            record.result(None, msg("tui_cancelled"))
            return False
        if answer is None:
            return True
        verb, focus = answer
        go = _switch_on if verb == "on" else _switch_off
        if not go(record, focus):
            return False


def run() -> int:
    return 0 if workshop(Record()) else 130
