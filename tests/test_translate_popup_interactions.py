"""Focused lifecycle, idle-dismissal, and copy-feedback tests for the GTK popup."""

from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

try:
    from orbit_translate import ui
except ImportError:  # GTK/PyGObject is a system runtime dependency.
    ui = None


@unittest.skipIf(ui is None, "GTK3 runtime unavailable; use /usr/bin/python3")
class PopupInteractionTests(unittest.TestCase):
    @staticmethod
    def bind_methods(window: SimpleNamespace, *names: str) -> None:
        for name in names:
            setattr(window, name, MethodType(getattr(ui.TranslationWindow, name), window))

    def idle_window(self, *, pending: bool = False) -> SimpleNamespace:
        window = SimpleNamespace(
            closed=False,
            started=True,
            requests_pending=pending,
            pointer_inside_panel=False,
            held_buttons=set(),
            drag_mode=None,
            language_popup_open=False,
            dismiss_source_id=0,
            idle_timeout_ms=4200,
        )
        window._remove_source = Mock()
        window._schedule_timeout = Mock(side_effect=(71, 72, 73, 74))
        self.bind_methods(window, "_dismiss_is_paused", "_on_dismiss_timeout")
        return window

    def test_idle_dismiss_waits_and_rearms_after_each_interaction(self) -> None:
        window = self.idle_window(pending=True)

        ui.TranslationWindow._refresh_idle_dismiss(window)
        window._schedule_timeout.assert_not_called()

        window.requests_pending = False
        ui.TranslationWindow._refresh_idle_dismiss(window)
        self.assertEqual(window.dismiss_source_id, 71)
        window._schedule_timeout.assert_called_once_with(
            4200,
            ui.TranslationWindow._on_dismiss_timeout.__get__(window),
            field="dismiss_source_id",
        )

        window.pointer_inside_panel = True
        ui.TranslationWindow._refresh_idle_dismiss(window)
        window._remove_source.assert_called_once_with(71)
        self.assertEqual(window.dismiss_source_id, 0)

        window.pointer_inside_panel = False
        ui.TranslationWindow._refresh_idle_dismiss(window)
        self.assertEqual(window.dismiss_source_id, 72)

        window.held_buttons.add(1)
        ui.TranslationWindow._refresh_idle_dismiss(window)
        self.assertEqual(window.dismiss_source_id, 0)
        window.held_buttons.clear()
        window.language_popup_open = True
        ui.TranslationWindow._refresh_idle_dismiss(window)
        self.assertEqual(window._schedule_timeout.call_count, 2)

        window.language_popup_open = False
        window.drag_mode = "move"
        ui.TranslationWindow._refresh_idle_dismiss(window)
        self.assertEqual(window._schedule_timeout.call_count, 2)

        window.drag_mode = None
        ui.TranslationWindow._refresh_idle_dismiss(window)
        self.assertEqual(window.dismiss_source_id, 73)

    def test_close_marks_closed_cancels_workers_and_starts_one_exit(self) -> None:
        engine = SimpleNamespace(close=Mock())
        window = SimpleNamespace(
            closed=False,
            started=True,
            engine=engine,
            scroll_anchor=(object(), 0.0),
            drag_mode="move",
            held_buttons={1},
            _cancel_pending_callbacks=Mock(),
            _cancel_opacity_animation=Mock(),
            _animate_opacity=Mock(),
            _destroy_once=Mock(),
        )

        self.assertFalse(ui.TranslationWindow.close(window))
        self.assertTrue(window.closed)
        self.assertFalse(window.started)
        self.assertIsNone(window.scroll_anchor)
        self.assertIsNone(window.drag_mode)
        self.assertFalse(window.held_buttons)
        window._cancel_pending_callbacks.assert_called_once_with()
        window._cancel_opacity_animation.assert_called_once_with()
        engine.close.assert_called_once_with()
        self.assertEqual(window._animate_opacity.call_args.args[:2], (0.0, 160))
        self.assertIsNotNone(window._animate_opacity.call_args.args[2])

        ui.TranslationWindow.close(window)
        window._animate_opacity.assert_called_once()
        engine.close.assert_called_once_with()

    def test_expired_timer_rechecks_interaction_before_closing(self) -> None:
        window = self.idle_window(pending=True)
        window.close = Mock()
        window._refresh_idle_dismiss = Mock()
        ui.TranslationWindow._on_dismiss_timeout(window)
        window.close.assert_not_called()
        window._refresh_idle_dismiss.assert_called_once_with()
        window.requests_pending = False
        ui.TranslationWindow._on_dismiss_timeout(window)
        window.close.assert_called_once_with()

    def test_capture_phase_input_and_late_worker_guards(self) -> None:
        window = SimpleNamespace(closed=False, translation_generation=3, language_menu=None, _mark_activity=Mock(), close=Mock(), _handle_pointer_motion=Mock(), _apply_outcome=Mock())
        ui.TranslationWindow._on_captured_motion(window, None, 12.8, 45.2)
        window._handle_pointer_motion.assert_called_once_with(12, 45)
        self.assertFalse(ui.TranslationWindow._on_captured_scroll(window, None, 0, 1))
        self.assertFalse(ui.TranslationWindow._on_captured_key(window, None, ui.Gdk.KEY_Down, 0, 0))
        self.assertTrue(ui.TranslationWindow._on_captured_key(window, None, ui.Gdk.KEY_Escape, 0, 0))
        self.assertEqual(window._mark_activity.call_count, 3)
        window.close.assert_called_once_with()
        with patch.object(ui.GLib, "idle_add") as post:
            ui.TranslationWindow._on_worker_result(window, object(), 2)
            post.assert_not_called()
            window.closed = True
            ui.TranslationWindow._on_worker_result(window, object(), 3)
            post.assert_not_called()

    def test_escape_closes_open_language_menu_before_the_popup(self) -> None:
        chip = SimpleNamespace(grab_focus=Mock())
        menu = SimpleNamespace(is_open=Mock(return_value=True), chip=chip)
        window = SimpleNamespace(language_menu=menu, _mark_activity=Mock(), close=Mock(), _close_language_menu=Mock())
        self.assertTrue(ui.TranslationWindow._on_captured_key(window, None, ui.Gdk.KEY_Escape, 0, 0))
        window._close_language_menu.assert_called_once_with()
        chip.grab_focus.assert_called_once_with()
        window.close.assert_not_called()

    def test_external_destroy_cancels_callbacks_and_workers(self) -> None:
        window = SimpleNamespace(closed=False, started=True, destroyed=False, engine=SimpleNamespace(close=Mock()), held_buttons={1}, drag_mode="resize", scroll_anchor=object(), _cancel_pending_callbacks=Mock(), _cancel_opacity_animation=Mock())
        with patch.object(ui.Gtk, "main_level", return_value=0), patch.object(ui.Gtk, "main_quit") as quit_loop:
            ui.TranslationWindow._on_destroy(window)
            quit_loop.assert_not_called()
        self.assertTrue(window.closed)
        self.assertTrue(window.destroyed)
        self.assertFalse(window.started)
        self.assertFalse(window.held_buttons)
        window._cancel_pending_callbacks.assert_called_once_with()
        window._cancel_opacity_animation.assert_called_once_with()
        window.engine.close.assert_called_once_with()

    def test_opacity_transition_is_frame_clock_bounded_and_reduced_motion_is_immediate(self) -> None:
        completion = Mock()
        opacity_updates: list[float] = []
        window = SimpleNamespace(
            animations_enabled=True,
            opacity_tick_id=0,
            opacity_transition=None,
            get_mapped=lambda: True,
            fade_surface=SimpleNamespace(get_opacity=lambda: 0.0, set_opacity=opacity_updates.append),
            add_tick_callback=Mock(return_value=19),
            remove_tick_callback=Mock(),
        )
        self.bind_methods(window, "_cancel_opacity_animation", "_on_opacity_tick")

        ui.TranslationWindow._animate_opacity(window, 1.0, 220, completion)
        self.assertEqual(window.opacity_tick_id, 19)
        self.assertEqual(opacity_updates, [])

        frame_clock = SimpleNamespace(get_frame_time=Mock(side_effect=(10_000, 110_000, 230_000)))
        tick = ui.TranslationWindow._on_opacity_tick
        self.assertTrue(tick(window, window, frame_clock))
        self.assertTrue(tick(window, window, frame_clock))
        self.assertAlmostEqual(opacity_updates[-1], 0.432006)
        self.assertFalse(tick(window, window, frame_clock))
        self.assertEqual(opacity_updates[-1], 1.0)
        self.assertEqual(window.opacity_tick_id, 0)
        completion.assert_called_once_with()

        immediate_updates: list[float] = []
        immediate = SimpleNamespace(
            animations_enabled=False,
            opacity_tick_id=0,
            opacity_transition=None,
            get_mapped=lambda: True,
            fade_surface=SimpleNamespace(get_opacity=lambda: 0.4, set_opacity=immediate_updates.append),
            add_tick_callback=Mock(),
            remove_tick_callback=Mock(),
        )
        self.bind_methods(immediate, "_cancel_opacity_animation", "_on_opacity_tick")
        completed = Mock()
        ui.TranslationWindow._animate_opacity(immediate, 0.0, 160, completed)
        self.assertEqual(immediate_updates, [0.0])
        immediate.add_tick_callback.assert_not_called()
        completed.assert_called_once_with()

    def test_source_and_result_copy_report_only_clipboard_success(self) -> None:
        source_button = object()
        source = SimpleNamespace(
            closed=False,
            source_copy_button=source_button,
            selected_text="fixture source",
            _set_clipboard=Mock(return_value=True),
            _show_copy_feedback=Mock(),
        )
        ui.TranslationWindow._copy_source(source, source_button)
        source._set_clipboard.assert_called_once_with("fixture source")
        source._show_copy_feedback.assert_called_once_with(source_button, True)

        result_button = object()
        result_label = SimpleNamespace(get_text=Mock(return_value="fixture result"))
        result = SimpleNamespace(
            closed=False,
            cards={"fixture": (None, result_label, result_button)},
            _set_clipboard=Mock(return_value=False),
            _show_copy_feedback=Mock(),
        )
        ui.TranslationWindow._copy_result(result, result_button, "fixture")
        result._set_clipboard.assert_called_once_with("fixture result")
        result._show_copy_feedback.assert_called_once_with(result_button, False)
        source.closed = True
        ui.TranslationWindow._copy_source(source, source_button)
        source._set_clipboard.assert_called_once()
        result.closed = True
        ui.TranslationWindow._copy_result(result, result_button, "fixture")
        result._set_clipboard.assert_called_once()

    def test_copy_feedback_expires_and_a_failed_retry_cancels_success_state(self) -> None:
        button = object()
        reveal = SimpleNamespace(show=Mock(), set_reveal_child=Mock())
        label = SimpleNamespace(set_text=Mock(), show=Mock())
        window = SimpleNamespace(
            closed=False,
            copy_button_tooltips={button: "复制结果"},
            copy_feedback_sources={},
            copy_feedback_generation=0,
            feedback_generation=0,
            feedback_hide_source_id=0,
            feedback_label=label,
            feedback_revealer=reveal,
            _source_ids=set(),
            _remove_source=Mock(),
            _schedule_timeout=Mock(side_effect=(41, 42, 43)),
            _set_button_icon=Mock(),
            _mark_activity=Mock(),
        )
        window._cancel_copy_button_feedback = lambda target: ui.TranslationWindow._cancel_copy_button_feedback(window, target)
        self.bind_methods(window, "_hide_copy_feedback", "_restore_copy_button")

        ui.TranslationWindow._show_copy_feedback(window, button, True)
        self.assertEqual(label.set_text.call_args, call("已复制"))
        self.assertEqual(
            window._set_button_icon.call_args_list[0],
            call(button, "emblem-ok-symbolic", "已复制"),
        )
        self.assertEqual(window.copy_feedback_sources[button], (42, 1))

        ui.TranslationWindow._show_copy_feedback(window, button, False)
        self.assertIn(call(42), window._remove_source.call_args_list)
        self.assertIn(call(41), window._remove_source.call_args_list)
        self.assertEqual(label.set_text.call_args, call("复制失败"))
        self.assertEqual(window._set_button_icon.call_args_list[-1], call(button, "edit-copy", "复制结果"))
        self.assertNotIn(button, window.copy_feedback_sources)

    def test_clipboard_exception_is_a_safe_failure(self) -> None:
        clipboard = SimpleNamespace(set_text=Mock(side_effect=RuntimeError("private clipboard detail")))
        with patch.object(ui.Gtk.Clipboard, "get", return_value=clipboard):
            self.assertFalse(ui.TranslationWindow._set_clipboard("fixture text"))
        clipboard.set_text.assert_called_once_with("fixture text", -1)
        self.assertNotIn("private clipboard detail", repr(clipboard.set_text.call_args))

    def test_callback_cleanup_removes_all_registered_sources(self) -> None:
        window = SimpleNamespace(
            _source_ids={51, 52},
            dismiss_source_id=51,
            position_idle_source_id=52,
            position_fallback_source_id=53,
            scroll_restore_source_id=54,
            feedback_hide_source_id=55,
            copy_feedback_sources={object(): (56, 1)},
            copy_feedback_generation=1,
            feedback_generation=2,
        )
        with patch.object(ui.GLib, "source_remove") as remove:
            ui.TranslationWindow._cancel_pending_callbacks(window)
        self.assertCountEqual(remove.call_args_list, (call(51), call(52)))
        self.assertFalse(window._source_ids)
        self.assertEqual(window.dismiss_source_id, 0)
        self.assertEqual(window.position_idle_source_id, 0)
        self.assertEqual(window.position_fallback_source_id, 0)
        self.assertEqual(window.scroll_restore_source_id, 0)
        self.assertEqual(window.feedback_hide_source_id, 0)
        self.assertFalse(window.copy_feedback_sources)
        self.assertEqual(window.copy_feedback_generation, 2)
        self.assertEqual(window.feedback_generation, 3)


if __name__ == "__main__":
    unittest.main()
