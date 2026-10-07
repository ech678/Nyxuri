"""Opt-in real GTK fixture: ORBIT_GTK_ACCEPTANCE=1 python3 -m unittest ... ."""

from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import os
import time
import unittest
from unittest.mock import patch

from orbit_translate.config import parse_config
from orbit_translate.providers import ProviderOutcome


@unittest.skipUnless(os.environ.get("ORBIT_GTK_ACCEPTANCE") == "1", "opt-in GTK surface")
class NativePopupTests(unittest.TestCase):
    def setUp(self) -> None:
        from orbit_translate.ui import TranslationWindow, GLib, Gtk

        self.Window, self.GLib, self.Gtk = TranslationWindow, GLib, Gtk
        self.windows = []
        self.engine_patch = patch("orbit_translate.ui.ProviderEngine")
        self.engine = self.engine_patch.start().return_value
        self.engine.start.return_value = self.engine
        self.addCleanup(self.engine_patch.stop)
        self.clipboard_patch = patch.object(TranslationWindow, "_set_clipboard", return_value=True)
        self.clipboard = self.clipboard_patch.start()
        self.addCleanup(self.clipboard_patch.stop)
        self.addCleanup(self.destroy_windows)
        self.pointer_patch = patch.object(TranslationWindow, "_get_pointer_position", return_value=None)
        self.pointer_patch.start()
        self.addCleanup(self.pointer_patch.stop)
        # Live pointer events must not overwrite deliberately injected fixture
        # hover state while another desktop window is mapped or resized.
        for callback in ("_on_captured_enter", "_on_captured_motion", "_on_captured_leave"):
            controller_patch = patch.object(TranslationWindow, callback, return_value=None)
            controller_patch.start()
            self.addCleanup(controller_patch.stop)

    def destroy_windows(self) -> None:
        for window in self.windows:
            if not window.destroyed:
                window.destroy()
        self.pump(0.02)

    def pump(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        context = self.GLib.MainContext.default()
        while time.monotonic() < deadline:
            while context.pending():
                context.iteration(False)
            time.sleep(0.002)

    def window(self, providers, **options):
        config = parse_config({"dismiss_after_ms": 1000, "providers": providers, **options})
        window = self.Window(config, "Hello world. Fixture only.")
        self.assertEqual(window.motion_controller.get_propagation_phase(), self.Gtk.PropagationPhase.CAPTURE)
        self.assertEqual(window.scroll_controller.get_propagation_phase(), self.Gtk.PropagationPhase.BUBBLE)
        self.assertEqual(window.key_controller.get_propagation_phase(), self.Gtk.PropagationPhase.CAPTURE)
        self.assertEqual(window.button_gesture.get_propagation_phase(), self.Gtk.PropagationPhase.CAPTURE)
        self.assertFalse(window.button_gesture.get_exclusive())
        self.windows.append(window)
        return window

    @staticmethod
    def rendered_alpha(window) -> int:
        import cairo

        allocation = window.panel.get_allocation()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, allocation.width, allocation.height)
        context = cairo.Context(surface)
        context.translate(-allocation.x, -allocation.y)
        window.fade_surface.draw(context)
        surface.flush()
        return sum(bytes(surface.get_data())[3::4])

    def test_real_surface_idle_copy_feedback_and_bounded_exit(self) -> None:
        window = self.window([{"id": "mymemory", "name": "MyMemory", "type": "mymemory", "enabled": True}])
        window.start()
        self.pump(1.05)
        self.assertFalse(window.closed, "loading must not expire")
        window.pointer_inside_panel = True
        window._apply_outcome(ProviderOutcome("mymemory", "MyMemory", text="你好，世界。"), window.translation_generation)
        self.pump(0.25)
        self.assertFalse(window.dismiss_source_id)
        self.assertAlmostEqual(window.fade_surface.get_opacity(), 1.0, places=2)
        full_alpha = self.rendered_alpha(window)
        window.fade_surface.set_opacity(0.5)
        self.pump(0.02)
        half_alpha = self.rendered_alpha(window)
        self.assertGreater(half_alpha, full_alpha * 0.3)
        self.assertLess(half_alpha, full_alpha * 0.7)
        window.fade_surface.set_opacity(1.0)
        window.source_copy_button.clicked()
        self.pump(0.22)
        self.clipboard.assert_called_with("Hello world. Fixture only.")
        self.assertTrue(window.feedback_label.get_visible())
        self.assertEqual(window.feedback_label.get_text(), "已复制")
        self.assertEqual(window.source_copy_button.get_child().get_icon_name()[0], "emblem-ok-symbolic")
        result_button = window.cards["mymemory"][2]
        result_button.clicked()
        self.clipboard.assert_called_with("你好，世界。")
        self.assertEqual(result_button.get_child().get_icon_name()[0], "emblem-ok-symbolic")
        preview = os.environ.get("ORBIT_GTK_PREVIEW_PATH")
        if preview:
            import cairo

            self.pump(0.22)
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, window.panel.get_allocated_width(), window.panel.get_allocated_height())
            window.panel.draw(cairo.Context(surface))
            surface.write_to_png(preview)
        self.pump(1.5)
        self.assertFalse(window.closed, "hover must pause idle dismissal")
        self.assertEqual(result_button.get_child().get_icon_name()[0], "edit-copy")
        self.assertFalse(window.feedback_revealer.get_reveal_child())
        window.source_selector.clicked()
        self.pump(0.2)
        menu = window.language_menu
        self.assertTrue(menu.is_open())
        self.assertTrue(window.language_popup_open)
        self.assertFalse(window.dismiss_source_id)
        chip = window.source_selector.get_allocation()
        self.assertEqual(menu.get_margin_top() + menu.SHADOW, chip.y + chip.height + menu.GAP)
        self.assertFalse(window.closed)
        outside = window.panel.get_allocation()
        self.assertTrue(window._handle_pointer_press(1, outside.x + outside.width + 40, outside.y + 2, 0))
        self.assertFalse(menu.is_open())
        self.assertFalse(window.closed, "outside press only dismisses the menu")
        window.target_selector.clicked()
        self.pump(0.2)
        rows = menu._list.get_children()
        choice = next(row for row in rows if row.language == "ja")
        choice.activate()
        self.pump(0.05)
        self.assertFalse(menu.is_open())
        self.assertEqual(window.current_target, "ja")
        self.assertEqual(window.target_selector.get_active_id(), "ja")
        window._apply_outcome(ProviderOutcome("mymemory", "MyMemory", text="こんにちは"), window.translation_generation)
        self.pump(0.2)
        window.pointer_inside_panel = False
        window.held_buttons.add(1)
        window._mark_activity()
        self.assertFalse(window.dismiss_source_id)
        window.held_buttons.clear()
        window._mark_activity()
        self.assertTrue(window.dismiss_source_id)
        timer = window.dismiss_source_id
        window._on_captured_key(window.key_controller, 65364, 0, 0)  # No fabricated GDK event.
        self.assertNotEqual(timer, window.dismiss_source_id)
        window.close()
        self.assertTrue(window.closed)
        self.assertFalse(window.destroyed)
        self.pump(0.08)
        self.assertGreater(window.fade_surface.get_opacity(), 0.0)
        self.assertLess(window.fade_surface.get_opacity(), 1.0)
        self.pump(0.25)
        self.assertTrue(window.destroyed)
        self.assertFalse(window._source_ids)
        self.assertFalse(window.opacity_tick_id)
        self.engine.close.assert_called()

    def test_reduced_motion_and_close_before_start(self) -> None:
        with patch.object(self.Window, "_animations_enabled", return_value=False):
            window = self.window([])
            window.start()
            self.assertEqual(window.fade_surface.get_opacity(), 0.0)
            # Placement falls back to centering after 180ms without a pointer event.
            self.pump(0.4)
            self.assertEqual(window.fade_surface.get_opacity(), 1.0)
            self.assertFalse(window.opacity_tick_id)
            window.close()
            self.assertTrue(window.destroyed)
        early = self.window([])
        early.close()
        self.assertTrue(early.destroyed)


if __name__ == "__main__":
    unittest.main()
