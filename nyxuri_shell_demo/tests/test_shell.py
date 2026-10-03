import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nyxuri_shell import actions, apps, color, ipc, motion, orbit, state as S, sysinfo, wallpaper  # noqa: E402
from nyxuri_shell.ui import gtk as gtk_ui  # noqa: E402


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._saved = {k: os.environ.get(k) for k in
                       ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR")}
        os.environ["HOME"] = str(self.tmp)
        os.environ["XDG_CACHE_HOME"] = str(self.tmp / ".cache")
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / ".config")
        os.environ["XDG_RUNTIME_DIR"] = str(self.tmp / "run")
        (self.tmp / "run").mkdir(parents=True, exist_ok=True)
        os.chmod(self.tmp / "run", 0o700)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestColor(unittest.TestCase):
    def test_self_check_clean(self):
        self.assertEqual(color._self_check(), [])

    def test_tone_extremes(self):
        self.assertEqual(color.hct_to_rgb(0.0, 0.0, 100.0), (255, 255, 255))
        self.assertEqual(color.hct_to_rgb(0.0, 0.0, 0.0), (0, 0, 0))

    def test_tone_is_monotonic(self):
        values = [color.rgb_to_lstar(color.hct_to_rgb(120.0, 0.1, t))
                  for t in range(0, 101, 10)]
        self.assertEqual(values, sorted(values))

    def test_out_of_gamut_chroma_is_clipped(self):
        rgb = color.hct_to_rgb(140.0, 0.37, 50.0)
        self.assertTrue(all(0 <= c <= 255 for c in rgb))

    def test_scheme_has_all_roles(self):
        scheme = color.generate_scheme((0x67, 0x50, 0xA4))
        for mode in ("dark", "light"):
            for role in color.PALETTE_ROLES:
                self.assertIn(role, scheme[mode])
                self.assertRegex(scheme[mode][role], r"^#[0-9a-f]{6}$")

    def test_seed_primary_matches_material_spec(self):
        scheme = color.generate_scheme((0x67, 0x50, 0xA4))
        self.assertEqual(scheme["light"]["primary"], "#66529e")
        self.assertEqual(scheme["light"]["on_primary"], "#ffffff")
        self.assertEqual(scheme["dark"]["on_surface"], "#e3e2e8")

    def test_hex_roundtrip(self):
        for value in ("#000000", "#ffffff", "#6750a4", "#012345"):
            self.assertEqual(color.hex_of(color.rgb_of(value)), value)

    def test_short_hex_expands(self):
        self.assertEqual(color.rgb_of("#abc"), (0xAA, 0xBB, 0xCC))

    def test_bad_hex_raises(self):
        for bad in ("", "#12", "#1234567", "zzzzzz"):
            with self.assertRaises(ValueError):
                color.rgb_of(bad)

    def test_light_and_dark_differ(self):
        scheme = color.generate_scheme((0x2E, 0x7D, 0x32))
        self.assertNotEqual(scheme["dark"]["surface"], scheme["light"]["surface"])

    def test_palette_toml_parsable_by_downstream(self):
        scheme = color.generate_scheme((0x67, 0x50, 0xA4))
        body = color.render_palette_toml(scheme, "dark")
        parsed = {}
        for line in body.splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                parsed[k.strip()] = v.strip().strip('"')
        self.assertEqual(parsed["primary"], scheme["dark"]["primary"])
        self.assertEqual(len(parsed), len(color.PALETTE_ROLES))


class TestMotion(unittest.TestCase):
    def test_self_check_clean(self):
        self.assertEqual(motion._self_check(), [])

    def test_spring_converges(self):
        s = motion.make_spring("sector_snap")
        s.set(5.0)
        for _ in range(600):
            s.step(1.0 / 60.0)
        self.assertAlmostEqual(s.value, 5.0, places=3)

    def test_spring_never_overshoots_wildly(self):
        s = motion.make_spring("ring_bloom")
        s.set(1.0)
        peak = 0.0
        for _ in range(300):
            peak = max(peak, s.step(1.0 / 60.0))
        self.assertLess(peak, 1.6)

    def test_critically_damped_has_no_overshoot(self):
        s = motion.make_spring("sector_snap")
        s.set(1.0)
        peak = 0.0
        for _ in range(300):
            peak = max(peak, s.step(1.0 / 60.0))
        self.assertLessEqual(peak, 1.001)

    def test_easings_are_bounded(self):
        for name, fn in motion.EASING.items():
            for i in range(11):
                v = fn(i / 10.0)
                self.assertGreaterEqual(v, -1e-9, name)
                self.assertLessEqual(v, 1.0 + 1e-9, name)

    def test_tween_fires_callback_once(self):
        calls = []
        t = motion.Tween(duration=0.1)
        t.on_done = lambda: calls.append(1)
        t.start()
        for _ in range(20):
            t.step(0.02)
        self.assertEqual(calls, [1])

    def test_frame_clock_clamps_huge_gaps(self):
        clock = motion.FrameClock(fps=60)
        clock._last -= 10.0
        self.assertLessEqual(clock.tick(), 3.0 / 60.0 + 1e-6)

    def test_motion_group_reports_settled(self):
        group = motion.MotionGroup()
        s = motion.make_spring("osd_pop")
        s.set(1.0)
        group.add(s)
        self.assertFalse(group.settled)
        for _ in range(600):
            group.step(1.0 / 60.0)
        self.assertTrue(group.settled)


class TestState(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(S._self_check(), [])

    def test_defaults(self):
        st = S.ShellState()
        self.assertEqual(st.appearance.mode, "dark")
        self.assertEqual(st.active_shell, "custom")

    def test_save_load_roundtrip(self):
        st = S.ShellState()
        st.appearance.mode = "light"
        st.appearance.source_color = "#2c7c34"
        self.assertTrue(S.save_state(st))
        loaded = S.load_state()
        self.assertEqual(loaded.appearance.mode, "light")
        self.assertEqual(loaded.appearance.source_color, "#2c7c34")

    def test_missing_file_yields_defaults(self):
        self.assertEqual(S.load_state().appearance.mode, "dark")

    def test_corrupt_json_yields_defaults(self):
        path = S.state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        self.assertEqual(S.load_state().appearance.mode, "dark")

    def test_unknown_keys_are_dropped(self):
        path = S.state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"appearance": {"mode": "light", "nope": 1}}', encoding="utf-8")
        loaded = S.load_state()
        self.assertEqual(loaded.appearance.mode, "light")
        self.assertFalse(hasattr(loaded.appearance, "nope"))

    def test_write_palette_matches_template_roles(self):
        st = S.ShellState()
        self.assertTrue(S.write_palette(st))
        body = S.palette_path().read_text(encoding="utf-8")
        for role in color.PALETTE_ROLES:
            self.assertIn(f'{role} = "', body)

    def test_auto_mode_resolves(self):
        st = S.ShellState()
        st.appearance.mode = "auto"
        self.assertIn(st.appearance.mode_effective(), ("dark", "light"))

    def test_idle_behaviors_sorted(self):
        behaviors = S.Idle().behaviors()
        timeouts = [b["timeout"] for b in behaviors]
        self.assertEqual(timeouts, sorted(timeouts))

    def test_idle_zero_disables(self):
        idle = S.Idle(lock_timeout=0, screen_off_timeout=0, suspend_timeout=0)
        self.assertEqual(idle.behaviors(), [])


class TestIpc(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(ipc._self_check(), [])

    def test_send_without_daemon(self):
        response = ipc.send("ping", name="absent.sock")
        self.assertFalse(response.ok)
        self.assertEqual(response.error, "daemon not running")

    def test_server_roundtrip(self):
        server = ipc.Server("t.sock")
        self.assertTrue(server.start())
        try:
            server.register("echo", lambda a: ipc.Response(True, a))
            self.assertTrue(ipc.send("ping", name="t.sock").ok)
            self.assertEqual(ipc.send("echo", {"x": 1}, name="t.sock").data, {"x": 1})
        finally:
            server.stop()

    def test_handler_exception_is_contained(self):
        server = ipc.Server("t2.sock")
        self.assertTrue(server.start())
        try:
            server.register("bad", lambda a: 1 / 0)
            response = ipc.send("bad", name="t2.sock")
            self.assertFalse(response.ok)
            self.assertIn("ZeroDivisionError", response.error)
        finally:
            server.stop()

    def test_socket_permissions(self):
        server = ipc.Server("t3.sock")
        self.assertTrue(server.start())
        try:
            mode = server.path.stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)
        finally:
            server.stop()

    def test_malformed_response_parsed(self):
        self.assertFalse(ipc.Response.from_json("garbage").ok)
        self.assertFalse(ipc.Response.from_json("[]").ok)


class TestWallpaper(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(wallpaper._self_check(), [])

    def test_quantize_groups_identical_pixels(self):
        palette, counts = wallpaper._quantize(bytes([0x67, 0x50, 0xA4] * 50))
        self.assertEqual(len(palette), 1)
        self.assertEqual(counts[0], 50)

    def test_extract_picks_population(self):
        colors = wallpaper.extract_source_colors(bytes([0x2E, 0x7D, 0x32] * 200))
        self.assertTrue(colors)
        self.assertGreater(colors[0].population, 0.9)

    def test_extremes_are_filtered(self):
        colors = wallpaper.extract_source_colors(bytes([0, 0, 0] * 100))
        self.assertEqual(colors, [])

    def test_is_video_and_image(self):
        self.assertTrue(wallpaper.is_video(Path("a.mp4")))
        self.assertFalse(wallpaper.is_video(Path("a.png")))
        self.assertTrue(wallpaper.is_image(Path("a.PNG")))

    def test_scan_skips_hidden(self):
        root = self.tmp / "Wallpapers"
        (root / ".hidden").mkdir(parents=True)
        (root / "a.png").write_bytes(b"x")
        (root / ".hidden" / "b.png").write_bytes(b"x")
        (root / ".dot.png").write_bytes(b"x")
        found = wallpaper.scan_directory(root)
        self.assertEqual([p.name for p in found], ["a.png"])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_solid_color_extraction_is_accurate(self):
        src = self.tmp / "solid.png"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "color=c=0x2E7D32:s=64x64:d=1",
             "-frames:v", "1", str(src)],
            check=True, timeout=30,
        )
        picked = wallpaper.pick_from_file(src)
        self.assertIsNotNone(picked)
        self.assertEqual(picked.hex, "#2c7c34")

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_video_frame_decodes(self):
        clip = self.tmp / "clip.mp4"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "color=c=0xB3261E:s=64x64:d=2",
             "-pix_fmt", "yuv420p", str(clip)],
            check=True, timeout=30,
        )
        self.assertTrue(wallpaper.is_video(clip))
        self.assertIsNotNone(wallpaper.pick_from_file(clip))


class TestActions(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(actions._self_check(), [])

    def test_every_action_maps(self):
        for action in actions.STANDARD_ACTIONS:
            self.assertIsNotNone(actions.daemon_command(action))

    def test_unknown_action_exit_code(self):
        self.assertEqual(actions.dispatch("nope"), actions.ACTION_EXIT_UNKNOWN)

    def test_no_daemon_exit_code(self):
        self.assertEqual(actions.dispatch("launcher"), actions.ACTION_EXIT_NO_DAEMON)

    def test_set_wallpaper_missing_file(self):
        ok, info = actions.set_wallpaper(self.tmp / "nope.png")
        self.assertFalse(ok)
        self.assertEqual(info, "file not found")

    def test_main_rejects_bad_action(self):
        self.assertEqual(actions.main(["nope"]), actions.ACTION_EXIT_UNKNOWN)

    def test_main_lists_actions(self):
        self.assertEqual(actions.main(["--list"]), actions.ACTION_EXIT_OK)

    def test_main_accepts_dash_action_flag(self):
        self.assertEqual(actions.main(["--action", "nope"]), actions.ACTION_EXIT_UNKNOWN)

    def test_main_status_returns_json(self):
        self.assertEqual(actions.main(["--status"]), actions.ACTION_EXIT_OK)


class TestDaemon(Isolated):
    def test_self_check_clean(self):
        from nyxuri_shell import daemon

        self.assertEqual(daemon._self_check(), [])

    def test_invalid_mode_rejected(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        response = shell.server.dispatch("theme-mode-set", {"mode": "purple"})
        self.assertFalse(response.ok)

    def test_theme_toggle_flips(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        before = shell.server.dispatch("theme-mode-get", {}).data["mode"]
        shell.server.dispatch("theme-toggle", {})
        after = shell.server.dispatch("theme-mode-get", {}).data["mode"]
        self.assertNotEqual(before, after)

    def test_wallpaper_set_via_ipc(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        response = shell.server.dispatch("wallpaper-set", {"path": str(self.tmp / "x.png")})
        self.assertFalse(response.ok)

    def test_missing_path_rejected(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        self.assertFalse(shell.server.dispatch("wallpaper-set", {}).ok)

    def test_panels_need_ui(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        self.assertFalse(shell.server.dispatch("panel-toggle", {}).ok)
        self.assertFalse(shell.server.dispatch("settings-toggle", {}).ok)

    def test_tool_commands_fall_back(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        self.assertTrue(shell.server.dispatch("wallpaper-picker", {}).ok)
        self.assertTrue(shell.server.dispatch("radial-launcher", {}).ok)

    def test_daemon_ends_to_end(self):
        from nyxuri_shell import daemon

        script = (
            "import sys; sys.path.insert(0, %r);"
            "from nyxuri_shell.daemon import main;"
            "sys.exit(main(['--no-ui']))" % str(Path(__file__).resolve().parent.parent)
        )
        proc = subprocess.Popen([sys.executable, "-c", script],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(60):
                if ipc.is_running():
                    break
                import time
                time.sleep(0.1)
            self.assertTrue(ipc.is_running(), "daemon never came up")
            self.assertTrue(ipc.send("status").ok)
            self.assertFalse(ipc.send("theme-mode-set", {"mode": "bad"}).ok)
            self.assertTrue(ipc.send("theme-mode-set", {"mode": "light"}).ok)
            self.assertEqual(ipc.send("theme-mode-get").data["mode"], "light")
        finally:
            proc.terminate()
            proc.wait(timeout=10)

        for _ in range(30):
            if not ipc.socket_path().exists():
                break
            import time
            time.sleep(0.1)
        self.assertFalse(ipc.socket_path().exists(), "socket left behind")


class TestGtkCss(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(gtk_ui._self_check(), [])

    def test_css_uses_material_roles(self):
        css = gtk_ui.build_css(S.ShellState())
        self.assertIn(".nyx-bar", css)
        self.assertIn("alpha(", css)

    def test_css_tracks_mode(self):
        dark = S.ShellState()
        light = S.ShellState()
        light.appearance.mode = "light"
        self.assertNotEqual(gtk_ui.build_css(dark), gtk_ui.build_css(light))

    def test_css_tracks_source_color(self):
        a = S.ShellState()
        b = S.ShellState()
        b.appearance.source_color = "#2c7c34"
        self.assertNotEqual(gtk_ui.build_css(a), gtk_ui.build_css(b))

    def test_css_tracks_scale(self):
        a = S.ShellState()
        b = S.ShellState()
        b.layout.scale = 1.4
        self.assertNotEqual(gtk_ui.build_css(a), gtk_ui.build_css(b))

    def test_panel_toggle_exclusive(self):
        model = gtk_ui.Model(S.ShellState())
        self.assertTrue(model.toggle_panel("launcher"))
        self.assertTrue(model.toggle_panel("settings"))
        self.assertEqual(model.visible_panel(), "settings")
        self.assertFalse(model.toggle_panel("settings"))
        self.assertFalse(model.any_panel_visible())

    def test_palette_lookup(self):
        model = gtk_ui.Model(S.ShellState())
        self.assertRegex(model.palette("primary"), r"^#[0-9a-f]{6}$")
        self.assertEqual(model.palette("nope", "#000000"), "#000000")

    def test_text_for_every_widget(self):
        model = gtk_ui.Model(S.ShellState())
        for name in ("launcher", "workspaces", "clock", "sysmon",
                     "volume", "battery", "notifications", "session"):
            self.assertIsInstance(model.text_for(name), str)

    def test_clock_format(self):
        model = gtk_ui.Model(S.ShellState())
        self.assertRegex(model.clock_text(), r"^\d{2}/\d{2}/\d{2} \d{2}:\d{2}$")

    def test_sysmon_degrades_without_proc(self):
        model = gtk_ui.Model(S.ShellState())
        self.assertIsInstance(model.sysmon_text(), str)

    def test_availability_probe_does_not_raise(self):
        self.assertIsInstance(gtk_ui.available(), bool)
        self.assertIsInstance(gtk_ui.layer_shell_available(), bool)


class TestSysinfo(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(sysinfo._self_check(), [])

    def test_probes_never_raise(self):
        for fn in (sysinfo.workspaces, sysinfo.focused_window, sysinfo.battery,
                   sysinfo.volume, sysinfo.backlight_percent,
                   sysinfo.memory_percent, sysinfo.focused_output_is_internal):
            fn()

    def test_memory_in_range(self):
        mem = sysinfo.memory_percent()
        if mem is not None:
            self.assertGreaterEqual(mem, 0.0)
            self.assertLessEqual(mem, 100.0)

    def test_cpu_in_range_or_none(self):
        cpu = sysinfo.cpu_percent(sample=0.05)
        if cpu is not None:
            self.assertGreaterEqual(cpu, 0.0)
            self.assertLessEqual(cpu, 100.0)

    def test_workspaces_is_list(self):
        self.assertIsInstance(sysinfo.workspaces(), list)

    def test_battery_shape(self):
        info = sysinfo.battery()
        if info is not None:
            self.assertGreaterEqual(info.percent, 0.0)
            self.assertLessEqual(info.percent, 100.0)
            self.assertIsInstance(info.charging, bool)

    def test_volume_shape(self):
        current = sysinfo.volume()
        if current is not None:
            self.assertIsInstance(current[0], int)
            self.assertIsInstance(current[1], bool)

    def test_backlight_bounds(self):
        percent = sysinfo.backlight_percent()
        if percent is not None:
            self.assertGreaterEqual(percent, 0)
            self.assertLessEqual(percent, 100)

    def test_set_backlight_clamps(self):
        result = sysinfo.set_backlight(999)
        if result is not None:
            self.assertLessEqual(result, 100)

    def test_workspace_label_prefers_name(self):
        ws = sysinfo.Workspace(1, 1, "web", True, False, True)
        self.assertEqual(ws.label, "web")
        self.assertEqual(sysinfo.Workspace(1, 3, "", True, False, True).label, "3")

    def test_window_label(self):
        self.assertEqual(sysinfo.Window("t", "a").label, "a: t")
        self.assertEqual(sysinfo.Window("", "a").label, "a")
        self.assertEqual(sysinfo.Window("t", "").label, "t")


class TestDaemonSysinfo(Isolated):
    def test_sysinfo_command_shape(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        data = shell.server.dispatch("sysinfo", {}).data
        for key in ("workspaces", "window", "volume", "battery", "backlight", "memory"):
            self.assertIn(key, data)

    def test_volume_get(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        self.assertTrue(shell.server.dispatch("volume", {"action": "get"}).ok)

    def test_brightness_get(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        self.assertTrue(shell.server.dispatch("brightness", {"action": "get"}).ok)

    def test_bogus_actions_rejected(self):
        from nyxuri_shell import daemon

        shell = daemon.Shell()
        self.assertFalse(shell.server.dispatch("volume", {"action": "x"}).ok)
        self.assertFalse(shell.server.dispatch("brightness", {"action": "x"}).ok)


class TestApps(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(apps._self_check(), [])

    def test_parse_valid_entry(self):
        path = self.tmp / "foo.desktop"
        path.write_text("[Desktop Entry]\nName=Foo Bar\nExec=foo --flag %U\nIcon=foo\n",
                        encoding="utf-8")
        entry = apps.parse_desktop(path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "Foo Bar")
        self.assertEqual(entry.command, ["foo", "--flag"])

    def test_rejects_nodisplay(self):
        path = self.tmp / "h.desktop"
        path.write_text("[Desktop Entry]\nName=H\nExec=h\nNoDisplay=true\n", encoding="utf-8")
        self.assertIsNone(apps.parse_desktop(path))

    def test_rejects_non_application(self):
        path = self.tmp / "l.desktop"
        path.write_text("[Desktop Entry]\nName=L\nExec=l\nType=Link\n", encoding="utf-8")
        self.assertIsNone(apps.parse_desktop(path))

    def test_rejects_action_group(self):
        path = self.tmp / "a.desktop"
        path.write_text("[Desktop Action new]\nName=N\nExec=n\n", encoding="utf-8")
        self.assertIsNone(apps.parse_desktop(path))

    def test_terminal_flag_parsed(self):
        path = self.tmp / "t.desktop"
        path.write_text("[Desktop Entry]\nName=T\nExec=htop\nTerminal=true\n", encoding="utf-8")
        entry = apps.parse_desktop(path)
        self.assertIsNotNone(entry)
        self.assertTrue(entry.terminal)
        cmd = entry.command
        self.assertTrue(cmd)
        if apps._terminal_command():
            self.assertNotEqual(cmd[0], "htop")
        else:
            self.assertEqual(cmd, ["htop"])

    def test_search_respects_limit(self):
        self.assertLessEqual(len(apps.search("", limit=2)), 2)

    def test_matches_is_case_insensitive(self):
        entry = apps.AppEntry("Firefox", "Firefox", "firefox")
        self.assertTrue(entry.matches("fire"))
        self.assertTrue(entry.matches("FIRE"))
        self.assertFalse(entry.matches("zzz"))

    def test_never_raises(self):
        apps.load_apps()
        apps.resolve_icon("definitely-not-an-icon-xyz")


class TestOrbit(Isolated):
    def test_self_check_clean(self):
        self.assertEqual(orbit._self_check(), [])

    def test_sector_boundaries(self):
        self.assertEqual(orbit.sector_of(0.0, 4), 0)
        self.assertEqual(orbit.sector_of(89.0, 4), 1)
        self.assertEqual(orbit.sector_of(270.0, 4), 3)
        self.assertEqual(orbit.sector_of(359.0, 4), 0)

    def test_deadzone(self):
        self.assertIsNone(orbit.hit_test(10.0, 10.0, 4))
        self.assertIsNotNone(orbit.hit_test(200.0, 0.0, 4))

    def test_hysteresis_holds_current(self):
        import math

        angle = 45.0 - orbit.HYSTERESIS_DEG / 2
        dx = math.cos(math.radians(angle)) * 200
        dy = math.sin(math.radians(angle)) * 200
        self.assertEqual(orbit.hit_test(dx, dy, 4, current=0), 0)

    def test_hysteresis_allows_real_move(self):
        import math

        angle = 45.0 + orbit.HYSTERESIS_DEG * 2
        dx = math.cos(math.radians(angle)) * 200
        dy = math.sin(math.radians(angle)) * 200
        self.assertEqual(orbit.hit_test(dx, dy, 4, current=0), 1)

    def test_angle_diff_wraps(self):
        self.assertAlmostEqual(orbit.angle_diff(10.0, 350.0), 20.0)
        self.assertAlmostEqual(orbit.angle_diff(0.0, 180.0), 180.0)

    def test_build_tree_nested(self):
        tree = orbit.build_tree(orbit.DEFAULT_ITEMS)
        self.assertEqual(len(tree), len(orbit.DEFAULT_ITEMS))
        folders = [i for i in tree if i.is_folder]
        self.assertTrue(folders)
        self.assertTrue(folders[0].children)

    def test_build_tree_rejects_junk(self):
        tree = orbit.build_tree([{"id": "a", "name": "A"}, "junk", None, 42])
        self.assertEqual(len(tree), 1)

    def test_state_navigation(self):
        tree = orbit.build_tree(orbit.DEFAULT_ITEMS)
        state = orbit.OrbitState()
        folder_index = next(i for i, it in enumerate(tree) if it.is_folder)
        self.assertFalse(state.enter(0, tree[0]))
        self.assertTrue(state.enter(folder_index, tree[folder_index]))
        self.assertEqual(state.depth, 1)
        self.assertTrue(state.current_items(tree))
        self.assertTrue(state.back())
        self.assertEqual(state.depth, 0)
        self.assertFalse(state.back())

    def test_state_hover_bounds(self):
        tree = orbit.build_tree(orbit.DEFAULT_ITEMS)
        state = orbit.OrbitState()
        state.hover = 999
        self.assertIsNone(state.current_item(tree))

    def test_search_url_encodes(self):
        engines, _meta = orbit.load_engines()
        url = orbit.search_url("a b&c", engines, "bing")
        self.assertNotIn(" ", url)
        self.assertIn("bing", url)

    def test_search_url_falls_back(self):
        self.assertEqual(orbit.search_url("x", [], ""), "")

    def test_resolve_target_url(self):
        item = orbit.Item(id="x", name="X", url="https://example.com")
        target = orbit.resolve_target(item)
        self.assertTrue(target)
        self.assertIn("https://example.com", target)

    def test_resolve_target_cmd(self):
        item = orbit.Item(id="x", name="X", cmd="echo hello")
        self.assertEqual(orbit.resolve_target(item), ["echo", "hello"])

    def test_resolve_target_empty(self):
        self.assertEqual(orbit.resolve_target(orbit.Item(id="x", name="X")), [])

    def test_folder_labels(self):
        tree = orbit.build_tree(orbit.DEFAULT_ITEMS)
        labels = orbit.folder_labels(tree)
        self.assertEqual(len(labels), len(tree))
        self.assertTrue(any("(" in label for label in labels))

    def test_digit_index(self):
        self.assertEqual(orbit.digit_index(0x31), 0)
        self.assertEqual(orbit.digit_index(0x39), 8)
        self.assertIsNone(orbit.digit_index(0x30))
        self.assertIsNone(orbit.digit_index(0x41))

    def test_rotate_wraps_both_ways(self):
        self.assertEqual(orbit.rotate(3, 4, 1), 0)
        self.assertEqual(orbit.rotate(0, 4, -1), 3)
        self.assertEqual(orbit.rotate(None, 4, 1), 0)
        self.assertEqual(orbit.rotate(None, 4, -1), 3)
        self.assertIsNone(orbit.rotate(0, 0, 1))

    def test_mnemonic_lookup(self):
        tree = orbit.build_tree(orbit.DEFAULT_ITEMS)
        self.assertEqual(orbit.mnemonic_index(tree, "k"), 0)
        self.assertEqual(orbit.mnemonic_index(tree, "K"), 0)
        self.assertIsNone(orbit.mnemonic_index(tree, "z"))
        self.assertIsNone(orbit.mnemonic_index(tree, ""))

    def test_digit_map_covers_ring(self):
        tree = orbit.build_tree(orbit.DEFAULT_ITEMS)
        mapping = orbit.digit_map(tree)
        self.assertEqual(sorted(int(k) for k in mapping), list(range(1, len(tree) + 1)))

    def test_digit_map_honours_explicit_shortcut(self):
        tree = orbit.build_tree([{"id": "a", "name": "A", "shortcut": "3"},
                                 {"id": "b", "name": "B"}])
        mapping = orbit.digit_map(tree)
        self.assertEqual(mapping["3"], 0)
        self.assertEqual(mapping["1"], 1)

    def test_flick_requires_button_press(self):
        flick = orbit.Flick()
        self.assertFalse(flick.active)
        flick.begin()
        self.assertTrue(flick.active)
        self.assertFalse(flick.release())
        flick.begin()
        flick.press()
        self.assertTrue(flick.release())
        self.assertFalse(flick.release())
        self.assertFalse(flick.active)

    def test_animator_reblooms_subring(self):
        anim = orbit.Animator()
        anim.show()
        for _ in range(600):
            if not anim.active:
                break
            anim.step(1.0 / 60.0)
        self.assertAlmostEqual(anim.bloom.value, 1.0, places=3)

        anim.enter_subring()
        self.assertTrue(anim.active)
        for _ in range(600):
            if not anim.active:
                break
            anim.step(1.0 / 60.0)
        self.assertAlmostEqual(anim.subring.value, 1.0, places=3)

    def test_animator_reset_settles(self):
        anim = orbit.Animator()
        anim.show()
        anim.set_hover(1)
        anim.reset()
        self.assertFalse(anim.active)
        self.assertFalse(anim.open)


class TestModel(Isolated):
    def test_launcher_rows_use_orbit(self):
        model = gtk_ui.Model(S.ShellState())
        rows = model.launcher_rows()
        self.assertEqual(len(rows), len(model.tree))

    def test_query_switches_to_app_search(self):
        model = gtk_ui.Model(S.ShellState())
        model.query = "zzz-no-such-app-zzz"
        self.assertEqual(model.launcher_rows(), [])

    def test_activate_folder_descends(self):
        model = gtk_ui.Model(S.ShellState())
        folder_index = next(i for i, it in enumerate(model.tree) if it.is_folder)
        kind, _ident = model.activate_launcher_row(folder_index)
        self.assertEqual(kind, "folder")
        self.assertEqual(model.orbit.depth, 1)

    def test_activate_item_returns_item(self):
        model = gtk_ui.Model(S.ShellState())
        leaf_index = next(i for i, it in enumerate(model.tree) if not it.is_folder)
        kind, ident = model.activate_launcher_row(leaf_index)
        self.assertEqual(kind, "item")
        self.assertTrue(ident)

    def test_activate_out_of_range(self):
        model = gtk_ui.Model(S.ShellState())
        self.assertEqual(model.activate_launcher_row(999)[0], "none")

    def test_panels_exclusive(self):
        model = gtk_ui.Model(S.ShellState())
        model.toggle_panel("launcher")
        model.toggle_panel("clipboard")
        self.assertEqual(model.visible_panel(), "clipboard")
        model.toggle_panel("clipboard")
        self.assertFalse(model.any_panel_visible())

    def test_wallpaper_panel_scans(self):
        root = S.wallpapers_dir()
        root.mkdir(parents=True, exist_ok=True)
        (root / "a.png").write_bytes(b"x")
        model = gtk_ui.Model(S.ShellState())
        model.toggle_panel("wallpaper")
        self.assertTrue(model.wallpaper_files)

    def test_text_for_all_widgets(self):
        model = gtk_ui.Model(S.ShellState())
        for name in ("launcher", "workspaces", "clock", "sysmon",
                     "volume", "battery", "session"):
            self.assertIsInstance(model.text_for(name), str)


class TestClipboard(Isolated):
    def test_history_degrades(self):
        self.assertIsInstance(gtk_ui.clipboard_history(), list)

    def test_copy_degrades(self):
        self.assertIsInstance(gtk_ui.copy_to_clipboard("x"), bool)


class TestIntegration(Isolated):
    def test_wallpaper_to_palette_pipeline(self):
        root = S.wallpapers_dir()
        root.mkdir(parents=True, exist_ok=True)
        src = root / "seed.png"
        shutil.copyfile(Path(__file__).resolve().parent.parent / "tests" / "seed.png", src)

        from nyxuri_shell import daemon

        shell = daemon.Shell()
        response = shell.server.dispatch("wallpaper-set", {"path": str(src)})
        self.assertTrue(response.ok, response.error)

        body = S.palette_path().read_text(encoding="utf-8")
        self.assertIn("#2c7c34", body)
        self.assertEqual(S.load_state().appearance.source_color, "#2c7c34")

    def test_state_survives_daemon_restart(self):
        from nyxuri_shell import daemon

        first = daemon.Shell()
        first.server.dispatch("theme-mode-set", {"mode": "light"})

        second = daemon.Shell()
        self.assertEqual(second.server.dispatch("theme-mode-get", {}).data["mode"], "light")


if __name__ == "__main__":
    unittest.main(verbosity=2)