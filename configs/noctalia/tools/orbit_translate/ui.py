"""GTK3 GtkLayerShell result surface."""

from __future__ import annotations

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell, Pango

from .config import AppConfig, ProviderConfig
from .engine import ProviderEngine, ResultRelay
from .geometry import PanelPlacement, center_panel, clamp_panel, place_panel
from .presentation import PresentationState
from .providers import ProviderOutcome
from .theme import gtk_css, load_palette
from .widgets import FitScrolledWindow, LanguageChip, LanguageMenu


class TranslationWindow(Gtk.Window):
    PANEL_WIDTH = 340
    # Default panel height; with less room below the panel may flip up.
    COMFORTABLE_HEIGHT = 520
    SOURCE_MAX_HEIGHT = 76
    RESULT_MIN_HEIGHT = 96
    RESULT_DEFAULT_HEIGHT = 340
    RESULT_MAX_HEIGHT = 520
    LANGUAGE_OPTIONS = (
        ("auto", "自动检测"),
        ("en", "英语"),
        ("zh-CN", "简体中文"),
        ("zh-TW", "繁体中文"),
        ("ja", "日语"),
        ("ko", "韩语"),
        ("fr", "法语"),
        ("de", "德语"),
        ("es", "西班牙语"),
        ("it", "意大利语"),
        ("pt", "葡萄牙语"),
        ("ru", "俄语"),
        ("ar", "阿拉伯语"),
        ("th", "泰语"),
        ("vi", "越南语"),
    )

    def __init__(
        self,
        config: AppConfig,
        selected_text: str,
        message: str = "",
        prestarted: tuple[ProviderEngine, ResultRelay] | None = None,
    ):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.config = config
        # Engine started by the entrypoint before GTK loaded; owned from here.
        self.engine: ProviderEngine | None = prestarted[0] if prestarted else None
        self.prestarted_relay = prestarted[1] if prestarted else None
        self.selected_text = selected_text
        self.message = message
        self.closed = False
        self.destroyed = False
        self.panel_positioned = False
        self.drag_mode: str | None = None
        self.drag_pointer = (0, 0)
        self.drag_origin = (0, 0)
        self.resize_size = (0, 0)
        self.cards: dict[
            str,
            tuple[Gtk.Label, Gtk.Label, Gtk.Button, Gtk.Revealer, Gtk.Button, Gtk.Revealer],
        ] = {}
        self.auto_copied = False
        self.current_source = config.source
        self.current_target = config.target
        self.source_selector: LanguageChip | None = None
        self.target_selector: LanguageChip | None = None
        self.language_menu: LanguageMenu | None = None
        self.started = False
        self.updating_languages = False
        self.translation_generation = 0
        self.dismiss_source_id = 0
        self.position_idle_source_id = 0
        self.position_fallback_source_id = 0
        self.scroll_restore_source_id = 0
        self.feedback_hide_source_id = 0
        self._source_ids: set[int] = set()
        self.requests_pending = False
        self.pointer_inside_panel = False
        self.held_buttons: set[int] = set()
        self.language_popup_open = False
        self.idle_timeout_ms = min(config.dismiss_after_ms, 6000) if message else config.dismiss_after_ms
        self.opacity_tick_id = 0
        self.opacity_transition: tuple[float, float, int, int | None, object | None] | None = None
        self.entry_transition_started = False
        self.animations_enabled = self._animations_enabled()
        self.copy_button_tooltips: dict[Gtk.Button, str] = {}
        self.copy_feedback_sources: dict[Gtk.Button, tuple[int, int]] = {}
        self.copy_feedback_generation = 0
        self.feedback_generation = 0
        self.scroll_anchor: tuple[Gtk.Widget, float] | None = None
        self.card_transition_duration_ms = self._card_transition_duration()
        self.enabled_providers = tuple(
            provider for provider in config.providers if provider.enabled
        )
        self.provider_by_id = {provider.id: provider for provider in self.enabled_providers}
        self.provider_priority = {
            provider.id: index for index, provider in enumerate(self.enabled_providers)
        }
        self.presentation = PresentationState(self.provider_by_id, config.max_cards)
        self.result_box: Gtk.Box | None = None
        self.result_scroll: Gtk.ScrolledWindow | None = None
        self.aggregate_label: Gtk.Label | None = None
        self.rendered_visible_ids: tuple[str, ...] = ()

        self._load_css()
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        for edge in (
            GtkLayerShell.Edge.LEFT,
            GtkLayerShell.Edge.RIGHT,
            GtkLayerShell.Edge.TOP,
            GtkLayerShell.Edge.BOTTOM,
        ):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
        )
        self.connect("grab-broken-event", self._on_grab_broken)
        self.connect("destroy", self._on_destroy)

        self.motion_controller = Gtk.EventControllerMotion.new(self)
        self.motion_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.motion_controller.connect("enter", self._on_captured_enter)
        self.motion_controller.connect("motion", self._on_captured_motion)
        self.motion_controller.connect("leave", self._on_captured_leave)

        self.scroll_controller = Gtk.EventControllerScroll.new(
            self, Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        # Scrollbars and ScrolledWindow must see wheel/drag input first.  A
        # toplevel capture controller runs before the target widget and can
        # make the scrollbar thumb appear inert even when this handler returns
        # False.  Bubble still lets us reset the idle-dismiss timer afterward.
        self.scroll_controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        self.scroll_controller.connect("scroll", self._on_captured_scroll)

        self.key_controller = Gtk.EventControllerKey.new(self)
        self.key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.key_controller.connect("key-pressed", self._on_captured_key)

        self.button_gesture = Gtk.GestureMultiPress.new(self)
        self.button_gesture.set_button(0)
        # Observe presses before native child handlers can stop bubbling.
        # Non-exclusive, unclaimed sequences still reach the target controls;
        # only an explicit Super drag takes the sequence.
        self.button_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.button_gesture.set_exclusive(False)
        self.button_gesture.connect("pressed", self._on_captured_button_press)
        self.button_gesture.connect("released", self._on_captured_button_release)

        self._build_layout()

    def start(self) -> None:
        if self.closed:
            return
        self.started = True
        self.fade_surface.set_opacity(0.0)
        self.show_all()
        # Pot's default is mouse-relative placement. The pointer query is a
        # best-effort Wayland convenience; the overlay's first pointer event
        # remains the portable source of truth, with centering as a late fallback.
        self.position_idle_source_id = self._schedule_idle(
            self._position_from_pointer, field="position_idle_source_id"
        )
        self.position_fallback_source_id = self._schedule_timeout(
            180, self._center_if_needed, field="position_fallback_source_id"
        )
        if self.message:
            self._refresh_idle_dismiss(reset=True)
            return
        self._start_provider_requests()

    def close(self) -> bool:
        if self.closed:
            return False
        self.closed = True
        self.started = False
        self._cancel_pending_callbacks()
        self._cancel_opacity_animation()
        self.scroll_anchor = None
        self.drag_mode = None
        self.held_buttons.clear()
        if self.engine:
            self.engine.close()
        self._animate_opacity(0.0, 160, self._destroy_once)
        return False

    def _start_provider_requests(self, generation: int | None = None) -> None:
        if generation is None:
            self.translation_generation += 1
            generation = self.translation_generation
        if not self.enabled_providers:
            self.requests_pending = False
            self._refresh_idle_dismiss(reset=True)
            return
        self.requests_pending = True
        relay, self.prestarted_relay = self.prestarted_relay, None
        if relay is not None and self.engine is not None:
            relay.attach(lambda outcome: self._on_worker_result(outcome, generation))
            return
        self.engine = ProviderEngine(
            self.enabled_providers,
            self.selected_text,
            self.current_source,
            self.current_target,
            self.config.request_timeout_ms,
            self.config.max_parallel,
            lambda outcome: self._on_worker_result(outcome, generation),
        ).start()

    @staticmethod
    def _animations_enabled() -> bool:
        settings = Gtk.Settings.get_default()
        if settings is None:
            return True
        try:
            return bool(settings.get_property("gtk-enable-animations"))
        except (AttributeError, GLib.Error, TypeError):
            return True

    @staticmethod
    def _card_transition_duration() -> int:
        return 180 if TranslationWindow._animations_enabled() else 0

    def _schedule_source(self, add_source, callback, args: tuple, field: str | None = None) -> int:
        if self.closed:
            return 0
        holder: dict[str, int | bool] = {"id": 0, "done": False}

        def dispatch() -> bool:
            holder["done"] = True
            source_id = int(holder["id"])
            if source_id:
                self._source_ids.discard(source_id)
                if field and getattr(self, field) == source_id:
                    setattr(self, field, 0)
            if self.closed:
                return False
            return bool(callback(*args))

        source_id = int(add_source(dispatch))
        holder["id"] = source_id
        if not source_id:
            return 0
        if holder["done"]:
            return 0
        if self.closed:
            GLib.source_remove(source_id)
            return 0
        self._source_ids.add(source_id)
        if field:
            setattr(self, field, source_id)
        return source_id

    def _schedule_idle(self, callback, *args, field: str | None = None) -> int:
        return self._schedule_source(GLib.idle_add, callback, args, field)

    def _schedule_timeout(self, timeout_ms: int, callback, *args, field: str | None = None) -> int:
        return self._schedule_source(
            lambda dispatch: GLib.timeout_add(timeout_ms, dispatch), callback, args, field
        )

    def _remove_source(self, source_id: int) -> None:
        if source_id and source_id in self._source_ids:
            self._source_ids.discard(source_id)
            GLib.source_remove(source_id)

    def _cancel_pending_callbacks(self) -> None:
        for source_id in tuple(self._source_ids):
            GLib.source_remove(source_id)
        self._source_ids.clear()
        self.dismiss_source_id = 0
        self.position_idle_source_id = 0
        self.position_fallback_source_id = 0
        self.scroll_restore_source_id = 0
        self.feedback_hide_source_id = 0
        self.copy_feedback_sources.clear()
        self.copy_feedback_generation += 1
        self.feedback_generation += 1

    def _cancel_opacity_animation(self) -> None:
        if self.opacity_tick_id:
            try:
                self.remove_tick_callback(self.opacity_tick_id)
            except (GLib.Error, TypeError):
                pass
        self.opacity_tick_id = 0
        self.opacity_transition = None

    def _animate_opacity(self, target: float, duration_ms: int, on_complete=None) -> None:
        self._cancel_opacity_animation()
        if not self.animations_enabled or duration_ms <= 0 or not self.get_mapped():
            self.fade_surface.set_opacity(target)
            if on_complete:
                on_complete()
            return
        self.opacity_transition = (
            self.fade_surface.get_opacity(),
            target,
            duration_ms * 1000,
            None,
            on_complete,
        )
        self.opacity_tick_id = self.add_tick_callback(self._on_opacity_tick)

    def _on_opacity_tick(self, _widget, frame_clock, _user_data=None) -> bool:
        transition = self.opacity_transition
        if transition is None:
            self.opacity_tick_id = 0
            return False
        start, target, duration_us, started_at, on_complete = transition
        frame_time = frame_clock.get_frame_time()
        if started_at is None:
            started_at = frame_time
            transition = (start, target, duration_us, started_at, on_complete)
            self.opacity_transition = transition
        progress = min(1.0, max(0.0, (frame_time - started_at) / duration_us))
        eased = progress * progress * (3.0 - 2.0 * progress)
        self.fade_surface.set_opacity(start + (target - start) * eased)
        if progress < 1.0:
            return True
        self.fade_surface.set_opacity(target)
        self.opacity_tick_id = 0
        self.opacity_transition = None
        if on_complete:
            on_complete()
        return False

    def _start_entry_animation(self) -> None:
        if self.entry_transition_started or self.closed:
            return
        self.entry_transition_started = True
        self._animate_opacity(1.0, 220)

    def _on_dismiss_timeout(self) -> bool:
        self.dismiss_source_id = 0
        if self._dismiss_is_paused():
            self._refresh_idle_dismiss()
        else:
            self.close()
        return False

    def _dismiss_is_paused(self) -> bool:
        return (
            self.requests_pending
            or self.pointer_inside_panel
            or bool(self.held_buttons)
            or self.drag_mode is not None
            or self.language_popup_open
        )

    def _refresh_idle_dismiss(self, reset: bool = False) -> None:
        if self.closed or not self.started:
            return
        if self._dismiss_is_paused():
            if self.dismiss_source_id:
                self._remove_source(self.dismiss_source_id)
                self.dismiss_source_id = 0
            return
        if self.dismiss_source_id and not reset:
            return
        if self.dismiss_source_id:
            self._remove_source(self.dismiss_source_id)
        self.dismiss_source_id = self._schedule_timeout(
            self.idle_timeout_ms, self._on_dismiss_timeout, field="dismiss_source_id"
        )

    def _mark_activity(self) -> None:
        self._refresh_idle_dismiss(reset=True)

    def _load_css(self) -> None:
        self.palette = load_palette()
        provider = Gtk.CssProvider()
        provider.load_from_data(gtk_css(self.palette).encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_layout(self) -> None:
        overlay = Gtk.Overlay()
        # Fade GTK's rendered content, not a compositor-specific window opacity.
        self.fade_surface = overlay
        overlay.get_style_context().add_class("translate-overlay")
        self.add(overlay)

        # The panel is the overlay's windowless main child, aligned by margins
        # in surface coordinates: START/START for a top-left anchor, START/END
        # when it opens above the pointer so late results grow it upward within
        # the same layout pass. (add_overlay children get their own GdkWindow,
        # which would make allocations panel-relative.)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        panel.set_size_request(self.PANEL_WIDTH, -1)
        panel.set_halign(Gtk.Align.START)
        panel.set_valign(Gtk.Align.START)
        panel.get_style_context().add_class("translate-panel")
        overlay.add(panel)
        self.panel = panel
        # Shared downward language menu, placed by margins in surface coordinates.
        self.language_menu = LanguageMenu(150 if self.animations_enabled else 0)
        overlay.add_overlay(self.language_menu)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.get_style_context().add_class("translate-topbar")
        # Nerd Font md-creation sparkles, matching Orbit's Nerd Font icon set.
        title_icon = Gtk.Label(label="\U000f0674")
        title_icon.get_style_context().add_class("translate-title-icon")
        header.pack_start(title_icon, False, False, 0)
        title = Gtk.Label(label="划词翻译")
        title.set_xalign(0)
        title.get_style_context().add_class("translate-title")
        header.pack_start(title, True, True, 0)
        close_button = self._icon_button("window-close", "关闭", "translate-close")
        close_button.connect("clicked", lambda *_args: self.close())
        header.pack_end(close_button, False, False, 0)
        panel.pack_start(header, False, False, 0)

        feedback_revealer = Gtk.Revealer()
        feedback_revealer.set_valign(Gtk.Align.CENTER)
        feedback_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        feedback_revealer.set_transition_duration(self.card_transition_duration_ms)
        feedback_revealer.set_no_show_all(True)
        feedback_label = Gtk.Label(label="")
        feedback_label.set_xalign(0)
        feedback_label.get_style_context().add_class("translate-copy-feedback")
        feedback_revealer.add(feedback_label)
        feedback_revealer.set_reveal_child(False)
        header.pack_end(feedback_revealer, False, False, 0)
        self.feedback_revealer = feedback_revealer
        self.feedback_label = feedback_label

        if self.message:
            self._add_message(panel, self.message)
            return

        if self.config.show_source:
            source_surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            source_surface.get_style_context().add_class("translate-source-surface")

            source_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            source_label = Gtk.Label(label="原文")
            source_label.set_xalign(0)
            source_label.get_style_context().add_class("translate-section-label")
            source_header.pack_start(source_label, True, True, 0)
            source_copy = self._icon_button("edit-copy", "复制原文")
            self.source_copy_button = source_copy
            self.copy_button_tooltips[source_copy] = "复制原文"
            source_copy.connect("clicked", self._copy_source)
            source_header.pack_end(source_copy, False, False, 0)
            source_surface.pack_start(source_header, False, False, 0)

            source_scroll = FitScrolledWindow(self.SOURCE_MAX_HEIGHT)
            source_scroll.get_style_context().add_class("translate-source-scroll")

            source = Gtk.Label(label=self._display_source())
            source.set_xalign(0)
            source.set_yalign(0)
            source.set_line_wrap(True)
            source.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            source.set_selectable(True)
            # Fill the fixed panel width instead of widening it.
            source.set_max_width_chars(1)
            source.get_style_context().add_class("translate-source")
            source_scroll.add(source)
            source_surface.pack_start(source_scroll, False, False, 0)
            panel.pack_start(source_surface, False, False, 0)

        language_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        language_bar.get_style_context().add_class("translate-language-bar")
        source_language = self._language_selector(self.current_source, include_auto=True)
        source_language.connect("changed", self._on_source_language_changed)
        self.source_selector = source_language
        language_bar.pack_start(source_language, True, True, 0)
        direction = Gtk.Button(label="⇄")
        direction.set_relief(Gtk.ReliefStyle.NONE)
        direction.set_tooltip_text("切换源语言和目标语言")
        direction.set_valign(Gtk.Align.CENTER)
        direction.get_style_context().add_class("translate-language-swap")
        direction.connect("clicked", self._swap_languages)
        language_bar.pack_start(direction, False, False, 0)
        target_language = self._language_selector(self.current_target, include_auto=False)
        target_language.connect("changed", self._on_target_language_changed)
        self.target_selector = target_language
        language_bar.pack_end(target_language, True, True, 0)
        panel.pack_start(language_bar, False, False, 0)

        if not self.enabled_providers:
            self._add_message(panel, "没有启用 Provider。请编辑 orbit-translate__custom__.toml 后重试。")
            return

        result_scroll = FitScrolledWindow(self.RESULT_MAX_HEIGHT, self.RESULT_DEFAULT_HEIGHT)
        result_scroll.get_style_context().add_class("translate-results-scroll")
        result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        result_scroll.add(result_box)
        panel.pack_start(result_scroll, True, True, 0)
        self.result_box = result_box
        self.result_scroll = result_scroll
        aggregate_label = Gtk.Label(label="正在等待可用译文…")
        aggregate_label.set_xalign(0)
        aggregate_label.set_line_wrap(True)
        aggregate_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        aggregate_label.set_max_width_chars(1)
        aggregate_label.get_style_context().add_class("translate-message")
        result_box.pack_start(aggregate_label, False, False, 0)
        self.aggregate_label = aggregate_label

    def _add_message(self, panel: Gtk.Box, message: str) -> None:
        label = Gtk.Label(label=message)
        label.set_xalign(0)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_max_width_chars(1)
        label.get_style_context().add_class("translate-message")
        panel.pack_start(label, False, False, 4)

    def _display_source(self) -> str:
        if len(self.selected_text) <= 360:
            return self.selected_text
        return self.selected_text[:360].rstrip() + "..."

    def _icon_button(self, icon_name: str, tooltip: str, style_class: str = "translate-action") -> Gtk.Button:
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_tooltip_text(tooltip)
        button.get_style_context().add_class(style_class)
        button.add(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
        return button

    def _language_selector(self, active_language: str, include_auto: bool) -> LanguageChip:
        options = self.LANGUAGE_OPTIONS if include_auto else tuple(
            option for option in self.LANGUAGE_OPTIONS if option[0] != "auto"
        )
        chip = LanguageChip(options, active_language, self._language_label)
        chip.connect("clicked", self._toggle_language_menu)
        return chip

    def _on_source_language_changed(self, selector: LanguageChip) -> None:
        self._on_language_changed(selector, source=True)

    def _on_target_language_changed(self, selector: LanguageChip) -> None:
        self._on_language_changed(selector, source=False)

    def _toggle_language_menu(self, chip: LanguageChip) -> None:
        menu = self.language_menu
        if menu is None or self.closed:
            return
        if menu.chip is chip:
            self._close_language_menu()
            return
        menu.open_for(
            chip,
            self.get_allocated_width() or 1920,
            self.get_allocated_height() or 1080,
            lambda language: self._select_language(chip, language),
            self.panel.get_allocation(),
        )
        self._set_language_popup_open(True)

    def _select_language(self, chip: LanguageChip, language: str) -> None:
        self._set_language_popup_open(False)
        chip.set_active_id(language)

    def _close_language_menu(self) -> None:
        if self.language_menu is not None and self.language_menu.is_open():
            self.language_menu.close()
        self._set_language_popup_open(False)

    def _set_language_popup_open(self, opened: bool) -> None:
        if self.language_popup_open != opened:
            self.language_popup_open = opened
            self._refresh_idle_dismiss(reset=True)

    def _on_language_changed(self, selector: LanguageChip, source: bool) -> None:
        if self.updating_languages or not self.started or self.closed:
            return
        language = selector.get_active_id()
        if not language:
            return
        self._mark_activity()
        if source:
            self.current_source = language
        else:
            self.current_target = language
        self._restart_translation()

    def _swap_languages(self, _button: Gtk.Button) -> None:
        if not self.started or self.closed:
            return
        self._close_language_menu()
        self._mark_activity()
        source = self.current_source
        target = self.current_target
        if source == "auto":
            fallback = self.config.source if self.config.source != "auto" else "en"
            source, target = target, fallback
        else:
            source, target = target, source
        if source == "auto":
            source = self.config.target if self.config.target != "auto" else "en"
        self.current_source = source
        self.current_target = target
        self.updating_languages = True
        try:
            if self.source_selector:
                self.source_selector.set_active_id(source)
            if self.target_selector:
                self.target_selector.set_active_id(target)
        finally:
            self.updating_languages = False
        self._restart_translation()

    def _restart_translation(self) -> None:
        if not self.started or self.closed or self.message:
            return
        if self.engine:
            self.engine.close()
        self.translation_generation += 1
        generation = self.translation_generation
        self._clear_copy_feedback()
        self._reset_cards()
        self.auto_copied = False
        self._start_provider_requests(generation)
        self._refresh_idle_dismiss(reset=True)

    def _reset_cards(self) -> None:
        self.presentation.reset()
        self.rendered_visible_ids = ()
        if self.scroll_restore_source_id:
            self._remove_source(self.scroll_restore_source_id)
            self.scroll_restore_source_id = 0
        self.scroll_anchor = None
        for (
            state,
            result,
            copy_button,
            body_revealer,
            expand_button,
            card_revealer,
        ) in self.cards.values():
            state.set_text("")
            state.get_style_context().remove_class("translate-status-success")
            result.set_text("")
            result.get_style_context().remove_class("translate-error")
            copy_button.set_sensitive(False)
            body_revealer.set_transition_duration(0)
            body_revealer.set_reveal_child(False)
            body_revealer.set_transition_duration(self.card_transition_duration_ms)
            card_revealer.set_transition_duration(0)
            card_revealer.set_reveal_child(False)
            card_revealer.hide()
            card_revealer.set_transition_duration(self.card_transition_duration_ms)
            self._set_expand_icon(expand_button, expanded=False)
        if self.aggregate_label:
            self.aggregate_label.set_text("正在等待可用译文…")
            self.aggregate_label.show()

    def _toggle_card(self, _button: Gtk.Button, provider_id: str) -> None:
        if self.closed:
            return
        card = self.cards.get(provider_id)
        if card is None:
            return
        _state, _result, _copy_button, body_revealer, expand_button, _card_revealer = card
        expanded = not body_revealer.get_reveal_child()
        body_revealer.set_reveal_child(expanded)
        self._set_expand_icon(expand_button, expanded)

    @staticmethod
    def _language_label(language: str) -> str:
        labels = dict(TranslationWindow.LANGUAGE_OPTIONS)
        labels.update({"en-US": "英语", "en-GB": "英语", "zh": "中文"})
        return labels.get(language, language)

    def _on_worker_result(self, outcome: ProviderOutcome, generation: int) -> None:
        if not self.closed and generation == self.translation_generation:
            # Worker posting must not mutate the main-thread source registry.
            GLib.idle_add(self._apply_outcome, outcome, generation)

    def _apply_outcome(self, outcome: ProviderOutcome, generation: int) -> bool:
        if self.closed or generation != self.translation_generation:
            return False
        if not self.presentation.accept(outcome):
            return False
        if outcome.ok and self.config.auto_copy and not self.auto_copied:
            self._set_clipboard(outcome.text)
            self.auto_copied = True
        self.requests_pending = not self.presentation.complete
        self._sync_success_cards(generation)
        self._refresh_idle_dismiss()
        return False

    def _create_success_card(
        self, provider: ProviderConfig
    ) -> tuple[Gtk.Label, Gtk.Label, Gtk.Button, Gtk.Revealer, Gtk.Button, Gtk.Revealer]:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.get_style_context().add_class("translate-card")
        card_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        card_header.get_style_context().add_class("translate-card-header")
        provider_label = Gtk.Label(label=provider.name)
        provider_label.set_xalign(0)
        provider_label.get_style_context().add_class("translate-provider")
        card_header.pack_start(provider_label, True, True, 0)
        state = Gtk.Label(label="完成")
        state.set_xalign(0.5)
        state.set_valign(Gtk.Align.CENTER)
        state.get_style_context().add_class("translate-status")
        state.get_style_context().add_class("translate-status-success")
        card_header.pack_start(state, False, False, 0)
        copy_button = self._icon_button("edit-copy", "复制结果")
        copy_button.set_sensitive(False)
        self.copy_button_tooltips[copy_button] = "复制结果"
        copy_button.connect("clicked", self._copy_result, provider.id)
        expand_button = self._icon_button("pan-down-symbolic", "展开结果", "translate-expand")
        expand_button.connect("clicked", self._toggle_card, provider.id)
        card_header.pack_end(expand_button, False, False, 0)
        card_header.pack_end(copy_button, False, False, 0)
        card.pack_start(card_header, False, False, 0)

        result = Gtk.Label(label="")
        result.set_xalign(0)
        result.set_line_wrap(True)
        result.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        result.set_max_width_chars(1)
        result.set_selectable(True)
        result.get_style_context().add_class("translate-result")

        result_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        result_body.get_style_context().add_class("translate-card-body")
        result_body.pack_start(result, False, False, 0)
        body_revealer = Gtk.Revealer()
        body_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        body_revealer.set_transition_duration(self.card_transition_duration_ms)
        body_revealer.add(result_body)
        body_revealer.set_reveal_child(False)
        card.pack_start(body_revealer, False, False, 0)

        card_revealer = Gtk.Revealer()
        card_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        card_revealer.set_transition_duration(self.card_transition_duration_ms)
        card_revealer.set_no_show_all(True)
        card_revealer.add(card)
        card_revealer.set_reveal_child(False)
        if self.result_box is not None:
            self.result_box.pack_start(card_revealer, False, False, 0)

        widgets = (state, result, copy_button, body_revealer, expand_button, card_revealer)
        self.cards[provider.id] = widgets
        return widgets

    def _sync_success_cards(self, generation: int) -> None:
        if self.result_box is None or self.aggregate_label is None:
            return
        outcomes = self.presentation.visible_successes
        visible_ids = tuple(outcome.provider_id for outcome in outcomes)
        changed = visible_ids != self.rendered_visible_ids
        previously_visible = set(self.rendered_visible_ids)
        if changed and self.scroll_anchor is None:
            self.scroll_anchor = self._capture_scroll_anchor()

        for outcome in outcomes:
            provider_id = outcome.provider_id
            widgets = self.cards.get(provider_id)
            if widgets is None:
                widgets = self._create_success_card(self.provider_by_id[provider_id])
            state, result, copy_button, body_revealer, expand_button, _card_revealer = widgets
            state.set_text("完成")
            state.get_style_context().add_class("translate-status-success")
            result.set_text(outcome.text)
            copy_button.set_sensitive(True)
            if provider_id not in previously_visible:
                body_revealer.set_transition_duration(0)
                body_revealer.set_reveal_child(True)
                body_revealer.set_transition_duration(self.card_transition_duration_ms)
                self._set_expand_icon(expand_button, expanded=True)

        ordered_ids = sorted(self.cards, key=self.provider_priority.__getitem__)
        for position, provider_id in enumerate(ordered_ids):
            self.result_box.reorder_child(self.cards[provider_id][5], position)
        self.result_box.reorder_child(self.aggregate_label, len(ordered_ids))

        for provider_id, widgets in self.cards.items():
            card_revealer = widgets[5]
            if provider_id not in visible_ids:
                widgets[2].set_sensitive(False)
                card_revealer.set_transition_duration(0)
                card_revealer.set_reveal_child(False)
                card_revealer.hide()
                card_revealer.set_transition_duration(self.card_transition_duration_ms)

        for provider_id in visible_ids:
            card_revealer = self.cards[provider_id][5]
            card_widget = card_revealer.get_child()
            if card_widget is not None:
                card_widget.show_all()
            card_revealer.show()
            card_revealer.set_reveal_child(True)

        if self.presentation.loading:
            self.aggregate_label.set_text("正在等待可用译文…")
            self.aggregate_label.show()
        elif self.presentation.no_result:
            self.aggregate_label.set_text("暂时无可用译文")
            self.aggregate_label.show()
        else:
            self.aggregate_label.hide()

        self.rendered_visible_ids = visible_ids
        if changed and self.scroll_anchor is not None:
            self._schedule_scroll_restore(generation)

    def _capture_scroll_anchor(self) -> tuple[Gtk.Widget, float] | None:
        if self.result_scroll is None:
            return None
        adjustment = self.result_scroll.get_vadjustment()
        value = adjustment.get_value()
        if value <= adjustment.get_lower():
            return None
        for provider_id in self.rendered_visible_ids:
            revealer = self.cards[provider_id][5]
            allocation = revealer.get_allocation()
            if revealer.get_child_revealed() and allocation.y + allocation.height > value:
                return revealer, value - allocation.y
        return None

    def _schedule_scroll_restore(self, generation: int) -> None:
        self._remove_source(self.scroll_restore_source_id)
        delay = self.card_transition_duration_ms + 24
        self.scroll_restore_source_id = self._schedule_timeout(
            delay,
            self._restore_scroll_anchor,
            generation,
            field="scroll_restore_source_id",
        )

    def _restore_scroll_anchor(self, generation: int) -> bool:
        self.scroll_restore_source_id = 0
        anchor = self.scroll_anchor
        self.scroll_anchor = None
        if (
            anchor is None
            or self.closed
            or generation != self.translation_generation
            or self.result_scroll is None
        ):
            return False
        revealer, offset = anchor
        if not revealer.get_child_revealed():
            return False
        allocation = revealer.get_allocation()
        adjustment = self.result_scroll.get_vadjustment()
        maximum = max(adjustment.get_lower(), adjustment.get_upper() - adjustment.get_page_size())
        adjustment.set_value(max(adjustment.get_lower(), min(maximum, allocation.y + offset)))
        return False

    @staticmethod
    def _set_expand_icon(button: Gtk.Button, expanded: bool) -> None:
        TranslationWindow._set_button_icon(
            button,
            "pan-up-symbolic" if expanded else "pan-down-symbolic",
            "收起结果" if expanded else "展开结果",
        )

    @staticmethod
    def _set_button_icon(button: Gtk.Button, icon_name: str, tooltip: str) -> None:
        for child in button.get_children():
            button.remove(child)
        button.add(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
        button.set_tooltip_text(tooltip)
        context = button.get_style_context()
        if icon_name == "emblem-ok-symbolic":
            context.add_class("translate-copied")
        else:
            context.remove_class("translate-copied")
        button.show_all()

    def _copy_source(self, _button: Gtk.Button) -> None:
        if self.closed:
            return
        button = self.source_copy_button
        succeeded = self._set_clipboard(self.selected_text)
        self._show_copy_feedback(button, succeeded)

    def _copy_result(self, _button: Gtk.Button, provider_id: str) -> None:
        if self.closed:
            return
        card = self.cards.get(provider_id)
        if card:
            succeeded = self._set_clipboard(card[1].get_text())
            self._show_copy_feedback(card[2], succeeded)

    def _show_copy_feedback(self, button: Gtk.Button, succeeded: bool) -> None:
        if self.closed:
            return
        self._mark_activity()
        tooltip = self.copy_button_tooltips.get(button, "复制")
        self._cancel_copy_button_feedback(button)
        self._set_button_icon(
            button,
            "emblem-ok-symbolic" if succeeded else "edit-copy",
            "已复制" if succeeded else tooltip,
        )
        self.feedback_label.set_text("已复制" if succeeded else "复制失败")
        self.feedback_label.show()
        self.feedback_revealer.show()
        self.feedback_revealer.set_reveal_child(True)

        self.feedback_generation += 1
        feedback_generation = self.feedback_generation
        if self.feedback_hide_source_id:
            self._remove_source(self.feedback_hide_source_id)
        self.feedback_hide_source_id = self._schedule_timeout(
            1400,
            self._hide_copy_feedback,
            feedback_generation,
            field="feedback_hide_source_id",
        )

        if succeeded:
            self.copy_feedback_generation += 1
            button_generation = self.copy_feedback_generation
            source_id = self._schedule_timeout(
                1400,
                self._restore_copy_button,
                button,
                tooltip,
                button_generation,
            )
            self.copy_feedback_sources[button] = (source_id, button_generation)

    def _cancel_copy_button_feedback(self, button: Gtk.Button) -> None:
        feedback = self.copy_feedback_sources.pop(button, None)
        if feedback is not None:
            self._remove_source(feedback[0])
            self._set_button_icon(button, "edit-copy", self.copy_button_tooltips.get(button, "复制"))

    def _restore_copy_button(self, button: Gtk.Button, tooltip: str, generation: int) -> bool:
        feedback = self.copy_feedback_sources.get(button)
        if feedback is not None and feedback[1] == generation:
            self.copy_feedback_sources.pop(button, None)
            self._set_button_icon(button, "edit-copy", tooltip)
        return False

    def _hide_copy_feedback(self, generation: int) -> bool:
        if generation == self.feedback_generation and not self.closed:
            self.feedback_revealer.set_reveal_child(False)
        return False

    def _clear_copy_feedback(self) -> None:
        for button, (source_id, _generation) in tuple(self.copy_feedback_sources.items()):
            self._remove_source(source_id)
            self._set_button_icon(button, "edit-copy", self.copy_button_tooltips.get(button, "复制"))
        self.copy_feedback_sources.clear()
        if self.feedback_hide_source_id:
            self._remove_source(self.feedback_hide_source_id)
            self.feedback_hide_source_id = 0
        self.feedback_generation += 1
        self.feedback_revealer.set_reveal_child(False)

    @staticmethod
    def _set_clipboard(text: str) -> bool:
        try:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            clipboard.store()
        except Exception:
            return False
        return True

    def _center_if_needed(self) -> bool:
        self.position_fallback_source_id = 0
        if not self.panel_positioned:
            surface_width, surface_height, panel_width, panel_height = self._panel_metrics()
            self._apply_placement(
                center_panel(surface_width, surface_height, panel_width, panel_height)
            )
            self._start_entry_animation()
        return False

    def _position_from_pointer(self) -> bool:
        if self.closed or self.panel_positioned:
            return False
        pointer = self._get_pointer_position()
        if pointer is not None:
            self._position_panel(*pointer)
        return False

    def _get_pointer_position(self) -> tuple[int, int] | None:
        """Read the current GDK pointer without relying on compositor APIs."""
        try:
            display = Gdk.Display.get_default()
            seat = display.get_default_seat() if display is not None else None
            pointer = seat.get_pointer() if seat is not None else None
            position = pointer.get_position() if pointer is not None else None
            if not position or len(position) < 3:
                return None
            _screen, pointer_x, pointer_y = position
            window = self.get_window()
            if window is not None:
                origin_x, origin_y = window.get_origin()
                pointer_x -= origin_x
                pointer_y -= origin_y
            # GDK's Wayland backend may return the origin when the compositor
            # does not expose a global pointer query. Let the overlay event
            # path handle that case instead of opening at the top-left corner.
            if pointer_x == 0 and pointer_y == 0:
                return None
            surface_width = self.get_allocated_width()
            surface_height = self.get_allocated_height()
            if not (0 <= pointer_x <= surface_width and 0 <= pointer_y <= surface_height):
                return None
            return int(pointer_x), int(pointer_y)
        except (AttributeError, GLib.Error, TypeError, ValueError):
            return None

    def _on_captured_enter(self, _controller, x: float, y: float) -> None:
        if self.closed:
            return
        pointer_x, pointer_y = int(x), int(y)
        self._update_pointer_inside_panel(pointer_x, pointer_y)
        if not self.panel_positioned:
            self._position_panel(pointer_x, pointer_y)

    def _on_captured_motion(self, _controller, x: float, y: float) -> None:
        if self.closed:
            return
        self._handle_pointer_motion(int(x), int(y))

    def _on_captured_leave(self, _controller) -> None:
        if self.closed:
            return
        if self.pointer_inside_panel:
            self.pointer_inside_panel = False
            self._refresh_idle_dismiss(reset=True)

    def _on_captured_scroll(self, _controller, _delta_x: float, _delta_y: float) -> bool:
        if self.closed:
            return False
        self._mark_activity()
        return False

    def _on_captured_button_press(
        self, gesture: Gtk.GestureMultiPress, _press_count: int, x: float, y: float
    ) -> None:
        if self.closed:
            return
        button = gesture.get_current_button()
        self.held_buttons.add(button)
        self._update_pointer_inside_panel(int(x), int(y))
        self._mark_activity()
        event = gesture.get_last_event(None)
        state = event.state if event is not None else Gdk.ModifierType(0)
        claimed = self._handle_pointer_press(button, int(x), int(y), state)
        if self.drag_mode or claimed:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_captured_button_release(
        self, gesture: Gtk.GestureMultiPress, _press_count: int, x: float, y: float
    ) -> None:
        if self.closed:
            return
        button = gesture.get_current_button()
        self.held_buttons.discard(button)
        if self.drag_mode and button in (1, 3):
            self.drag_mode = None
        self._update_pointer_inside_panel(int(x), int(y))
        self._mark_activity()

    def _on_grab_broken(self, _widget, _event) -> bool:
        self.held_buttons.clear()
        self.drag_mode = None
        if self.pointer_inside_panel:
            self.pointer_inside_panel = False
        self._refresh_idle_dismiss(reset=True)
        return False

    def _update_pointer_inside_panel(self, pointer_x: int, pointer_y: int) -> None:
        allocation = self.panel.get_allocation()
        inside = (
            allocation.x <= pointer_x <= allocation.x + allocation.width
            and allocation.y <= pointer_y <= allocation.y + allocation.height
        )
        if inside != self.pointer_inside_panel:
            self.pointer_inside_panel = inside
            self._refresh_idle_dismiss(reset=True)

    def _handle_pointer_motion(self, pointer_x: int, pointer_y: int) -> None:
        self._update_pointer_inside_panel(pointer_x, pointer_y)
        if self.drag_mode:
            delta_x = pointer_x - self.drag_pointer[0]
            delta_y = pointer_y - self.drag_pointer[1]
            if self.drag_mode == "move":
                self._move_panel(
                    self.drag_origin[0] + delta_x,
                    self.drag_origin[1] + delta_y,
                )
            else:
                width = max(300, min(560, self.resize_size[0] + delta_x))
                height = max(240, min(860, self.resize_size[1] + delta_y))
                self.panel.set_size_request(width, height)
                self._move_panel(*self.drag_origin)
            return
        if not self.panel_positioned:
            self._position_panel(pointer_x, pointer_y)

    def _position_panel(self, pointer_x: int, pointer_y: int) -> None:
        if self.panel_positioned:
            return
        if self.position_fallback_source_id:
            self._remove_source(self.position_fallback_source_id)
            self.position_fallback_source_id = 0
        surface_width, surface_height, panel_width, _panel_height = self._panel_metrics()
        self._apply_placement(
            place_panel(
                pointer_x,
                pointer_y,
                surface_width,
                surface_height,
                panel_width,
                self.COMFORTABLE_HEIGHT,
            )
        )
        self._update_pointer_inside_panel(pointer_x, pointer_y)
        self._start_entry_animation()

    def _panel_metrics(self) -> tuple[int, int, int, int]:
        return (
            self.get_allocated_width() or 1920,
            self.get_allocated_height() or 1080,
            max(self.panel.get_allocated_width(), self.PANEL_WIDTH),
            self.panel.get_allocated_height() or self.COMFORTABLE_HEIGHT,
        )

    def _apply_placement(self, placement: PanelPlacement) -> None:
        """Anchor the panel and bound result height to the room on that side."""
        if self.result_scroll is not None:
            panel_height = self.panel.get_allocated_height()
            scroll_height = self.result_scroll.get_allocated_height()
            chrome = panel_height - scroll_height if panel_height > 1 else 200
            maximum = max(
                self.RESULT_MIN_HEIGHT,
                min(self.RESULT_MAX_HEIGHT, placement.max_height - chrome),
            )
            self.result_scroll.set_max_content_height(maximum)
            self.result_scroll.fit_min_height = min(self.RESULT_DEFAULT_HEIGHT, maximum)
            self.result_scroll.queue_resize()
        surface_height = self.get_allocated_height() or 1080
        self.panel.set_margin_start(max(0, placement.x))
        if placement.above:
            self.panel.set_valign(Gtk.Align.END)
            self.panel.set_margin_top(0)
            self.panel.set_margin_bottom(max(0, surface_height - placement.y))
        else:
            self.panel.set_valign(Gtk.Align.START)
            self.panel.set_margin_bottom(0)
            self.panel.set_margin_top(max(0, placement.y))
        self.panel_positioned = True

    def _move_panel(self, x: int, y: int) -> None:
        surface_width, surface_height, panel_width, panel_height = self._panel_metrics()
        x, y = clamp_panel(int(x), int(y), panel_width, panel_height, surface_width, surface_height, 0)
        self.panel.set_valign(Gtk.Align.START)
        self.panel.set_margin_bottom(0)
        self.panel.set_margin_start(x)
        self.panel.set_margin_top(y)
        self.panel_positioned = True

    def _handle_pointer_press(self, button: int, x: int, y: int, state) -> bool:
        """Return True when the press is consumed and must not reach children."""
        menu = self.language_menu
        if menu is not None and menu.is_open():
            if menu.contains(x, y, self.get_allocated_height()):
                return False
            # Like an M3 menu: an outside press only dismisses the menu. A
            # press on the owning chip is left to its own toggle handler.
            if menu.chip is not None and self._widget_contains(menu.chip, x, y):
                return False
            self._close_language_menu()
            return True
        if state & Gdk.ModifierType.MOD4_MASK and button in (1, 3):
            if not self.panel_positioned:
                self._position_panel(x, y)
            allocation = self.panel.get_allocation()
            inside = (
                allocation.x <= x <= allocation.x + allocation.width
                and allocation.y <= y <= allocation.y + allocation.height
            )
            if not inside:
                return False
            self.drag_pointer = (x, y)
            self.drag_origin = (allocation.x, allocation.y)
            if button == 1:
                self.drag_mode = "move"
            else:
                self.drag_mode = "resize"
                self.resize_size = (allocation.width, allocation.height)
            return False
        if button != 1:
            return False
        if not self._widget_contains(self.panel, x, y):
            self.close()
        return False

    @staticmethod
    def _widget_contains(widget: Gtk.Widget, x: int, y: int) -> bool:
        allocation = widget.get_allocation()
        return (
            allocation.x <= x <= allocation.x + allocation.width
            and allocation.y <= y <= allocation.y + allocation.height
        )

    def _on_captured_key(self, _controller, keyval: int, _keycode: int, _state) -> bool:
        self._mark_activity()
        if keyval == Gdk.KEY_Escape:
            if self.language_menu is not None and self.language_menu.is_open():
                chip = self.language_menu.chip
                self._close_language_menu()
                if chip is not None:
                    chip.grab_focus()
            else:
                self.close()
            return True
        return False

    def _destroy_once(self) -> None:
        if not self.destroyed:
            self.destroyed = True
            self.destroy()

    def _on_destroy(self, *_args) -> None:
        self.closed = True
        self.started = False
        self._cancel_pending_callbacks()
        self._cancel_opacity_animation()
        self.scroll_anchor = None
        self.drag_mode = None
        self.held_buttons.clear()
        if self.engine:
            self.engine.close()
        self.destroyed = True
        if Gtk.main_level() > 0:
            Gtk.main_quit()


def show_message(config: AppConfig, message: str) -> None:
    window = TranslationWindow(config, "", message=message)
    window.start()
    from gi.repository import Gtk

    Gtk.main()
