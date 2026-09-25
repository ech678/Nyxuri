"""
Orbit Launcher Cairo Vector Rendering Engine
Modular, high-performance, frame-clock synchronized vector graphics rendering pipeline.
"""

import math
import cairo
from gi.repository import Pango, PangoCairo

from .config import CAPSULE_IDLE_H, CAPSULE_ACTIVE_H, FLOAT_SPRING, DEADZONE_RADIUS


def draw_rounded_pill(cr, x: float, y: float, w: float, h: float, r: float):
    """Draw a smooth stadium curve / rounded pill path."""
    r = min(r, w / 2.0, h / 2.0)
    cr.new_path()
    cr.arc(x + r, y + r, r, math.pi, 3.0 * math.pi / 2.0)
    cr.arc(x + w - r, y + r, r, 3.0 * math.pi / 2.0, 2.0 * math.pi)
    cr.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
    cr.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    cr.close_path()


def draw_scrim(cr, entry_val: float, is_dark: bool, dim_rgb: tuple):
    """Draw atmospheric dimmed background overlay."""
    dim_r, dim_g, dim_b = dim_rgb
    cr.save()
    cr.set_source_rgba(dim_r, dim_g, dim_b, (0.42 if is_dark else 0.22) * entry_val)
    cr.paint()
    cr.restore()


def draw_star_ring(cr, cx: float, cy: float, orbit_r: float, num_items: int, apps: list,
                   node_springs: list, active_idx: int, outer_alpha: float, outline_rgb: tuple):
    """Draw celestial orbit track, radial segment dividers, and active accent arcs."""
    out_r, out_g, out_b = outline_rgb

    # 1. Subtle glow track
    cr.save()
    cr.new_path()
    cr.arc(cx, cy, orbit_r, 0, 2 * math.pi)
    cr.set_line_width(18.0)
    if active_idx is not None and active_idx < num_items:
        ar, ag, ab = apps[active_idx]["color"]
        cr.set_source_rgba(ar, ag, ab, 0.06 * outer_alpha)
    else:
        cr.set_source_rgba(out_r, out_g, out_b, 0.02 * outer_alpha)
    cr.stroke()
    cr.restore()

    # 2. Continuous solid thin guide
    cr.save()
    cr.new_path()
    cr.arc(cx, cy, orbit_r, 0, 2 * math.pi)
    cr.set_line_width(1.0)
    cr.set_source_rgba(out_r, out_g, out_b, 0.10 * outer_alpha)
    cr.stroke()

    # 3. Precision dashed orbital path
    cr.new_path()
    cr.arc(cx, cy, orbit_r, 0, 2 * math.pi)
    cr.set_dash([3.0, 7.0])
    cr.set_line_width(1.2)
    cr.set_source_rgba(out_r, out_g, out_b, 0.18 * outer_alpha)
    cr.stroke()
    cr.restore()

    # 4. Sector dividers
    step_deg = 360.0 / num_items
    for i in range(num_items):
        div_rad = math.radians(-90.0 + (i + 0.5) * step_deg)
        tx1 = cx + (orbit_r - 6.0) * math.cos(div_rad)
        ty1 = cy + (orbit_r - 6.0) * math.sin(div_rad)
        tx2 = cx + (orbit_r + 6.0) * math.cos(div_rad)
        ty2 = cy + (orbit_r + 6.0) * math.sin(div_rad)
        cr.save()
        cr.new_path()
        cr.move_to(tx1, ty1)
        cr.line_to(tx2, ty2)
        cr.set_line_width(1.0)
        cr.set_source_rgba(out_r, out_g, out_b, 0.16 * outer_alpha)
        cr.stroke()
        cr.restore()

    # 5. Dynamic active accent arcs
    for i, app in enumerate(apps):
        if i < len(node_springs):
            prog = max(0.0, min(1.0, node_springs[i].current))
            if prog > 0.01:
                app_r, app_g, app_b = app["color"]
                ang_deg = app["center_angle"]
                half_span = (step_deg / 2.0) - 4.0
                start_rad = math.radians(ang_deg - half_span)
                end_rad = math.radians(ang_deg + half_span)

                cr.save()
                cr.new_path()
                cr.arc(cx, cy, orbit_r, start_rad, end_rad)
                cr.set_line_width(14.0)
                cr.set_source_rgba(app_r, app_g, app_b, 0.15 * prog * outer_alpha)
                cr.stroke()

                cr.new_path()
                cr.arc(cx, cy, orbit_r, start_rad, end_rad)
                cr.set_line_width(2.5 + prog * 1.5)
                cr.set_source_rgba(app_r, app_g, app_b, (0.50 + 0.45 * prog) * outer_alpha)
                cr.stroke()
                cr.restore()


def draw_tethers(cr, cx: float, cy: float, core_x: float, core_y: float, orbit_r: float,
                 apps: list, node_springs: list, outer_alpha: float, outline_rgb: tuple):
    """Draw dynamic dashed energy connection lines from center core to hovered nodes."""
    out_r, out_g, out_b = outline_rgb

    cr.save()
    cr.new_path()
    cr.arc(cx, cy, DEADZONE_RADIUS, 0, 2 * math.pi)
    cr.set_dash([2.0, 4.0])
    cr.set_line_width(0.8)
    cr.set_source_rgba(out_r, out_g, out_b, 0.12 * outer_alpha)
    cr.stroke()
    cr.restore()

    for i, app in enumerate(apps):
        if i < len(node_springs):
            prog = max(0.0, min(1.0, node_springs[i].current))
            if prog > 0.01:
                app_r, app_g, app_b = app["color"]
                ang_rad = math.radians(app["center_angle"])
                node_dist = orbit_r + prog * FLOAT_SPRING
                target_x = cx + node_dist * math.cos(ang_rad)
                target_y = cy + node_dist * math.sin(ang_rad)

                cr.save()
                cr.new_path()
                cr.move_to(core_x, core_y)
                cr.line_to(target_x, target_y)
                cr.set_dash([2.0, 5.0])
                cr.set_line_width(1.2 + prog * 0.8)
                cr.set_source_rgba(app_r, app_g, app_b, (0.15 + 0.65 * prog) * outer_alpha)
                cr.stroke()
                cr.restore()


def draw_submenu_return_core(cr, core_x: float, core_y: float, entry_val: float,
                             palette: dict, layout_back, back_ink_rect):
    """Draw submenu return button in center core."""
    out_r, out_g, out_b = palette["outline"]
    cr.save()
    core_radius = 18.0
    cr.new_path()
    cr.arc(core_x, core_y, core_radius, 0, 2 * math.pi)
    cr.set_source_rgba(out_r, out_g, out_b, 0.12 * entry_val)
    cr.fill()

    cr.new_path()
    cr.arc(core_x, core_y, 10.0, 0, 2 * math.pi)
    cr.set_source_rgba(palette["on_surface_var"][0], palette["on_surface_var"][1], palette["on_surface_var"][2], 0.40 * entry_val)
    cr.set_line_width(1.4)
    cr.stroke()

    bw, bh = back_ink_rect.width, back_ink_rect.height
    bx = core_x - back_ink_rect.x - (bw / 2.0)
    by = core_y - back_ink_rect.y - (bh / 2.0)
    cr.move_to(bx, by)
    cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], 0.95 * entry_val)
    PangoCairo.show_layout(cr, layout_back)
    cr.restore()


def draw_idle_center_dot(cr, core_x: float, core_y: float, entry_val: float,
                         active_idx: int, apps: list, num_items: int, palette: dict):
    """Draw idle triple-concentric center focal dot."""
    out_r, out_g, out_b = palette["outline"]
    cr.save()
    core_radius = 14.0
    cr.new_path()
    cr.arc(core_x, core_y, core_radius, 0, 2 * math.pi)
    if active_idx is not None and active_idx < num_items:
        ar, ag, ab = apps[active_idx]["color"]
        cr.set_source_rgba(ar, ag, ab, 0.22 * entry_val)
    else:
        cr.set_source_rgba(out_r, out_g, out_b, 0.08 * entry_val)
    cr.fill()

    cr.new_path()
    cr.arc(core_x, core_y, 8.0, 0, 2 * math.pi)
    if active_idx is not None and active_idx < num_items:
        ar, ag, ab = apps[active_idx]["color"]
        cr.set_source_rgba(ar, ag, ab, 0.85 * entry_val)
    else:
        cr.set_source_rgba(palette["on_surface_var"][0], palette["on_surface_var"][1], palette["on_surface_var"][2], 0.40 * entry_val)
    cr.set_line_width(1.4)
    cr.stroke()

    cr.new_path()
    cr.arc(core_x, core_y, 3.2, 0, 2 * math.pi)
    if active_idx is not None and active_idx < num_items:
        ar, ag, ab = apps[active_idx]["color"]
        cr.set_source_rgba(ar, ag, ab, 1.0 * entry_val)
    else:
        cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], 0.90 * entry_val)
    cr.fill()
    cr.restore()


def draw_search_hub(cr, cx: float, cy: float, search_prog: float, entry_val: float,
                    search_engines: list, current_engine_idx: int, engine_switch_spring,
                    search_query: str, cursor_time: float, layout_placeholder, placeholder_size: tuple,
                    palette: dict, create_pango_layout_fn, update_im_cursor_fn):
    """Draw Android Gemini Chubby Search Capsule with engine avatar island and breathing neon cursor."""
    surf_r, surf_g, surf_b = palette["surface"]
    dim_r, dim_g, dim_b = palette["surface_dim"]
    out_r, out_g, out_b = palette["outline"]

    sw = 36.0 + (390.0 - 36.0) * search_prog
    sh = 36.0 + (64.0 - 36.0) * search_prog
    sr = sh / 2.0
    sx = cx - sw / 2.0
    sy = cy - sh / 2.0

    # (1) Expressive Ambient Aura Glow
    cr.save()
    halo_radius = (sw / 2.0) + 48.0
    pattern = cairo.RadialGradient(cx, cy, 10.0, cx, cy, halo_radius)
    pattern.add_color_stop_rgba(0.0, surf_r, surf_g, surf_b, 0.60 * search_prog * entry_val)
    pattern.add_color_stop_rgba(0.5, out_r, out_g, out_b, 0.15 * search_prog * entry_val)
    pattern.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
    cr.set_source(pattern)
    cr.arc(cx, cy, halo_radius, 0, 2 * math.pi)
    cr.fill()
    cr.restore()

    # (2) Shadow
    cr.save()
    draw_rounded_pill(cr, sx, sy + 4.0 * search_prog, sw, sh, sr)
    cr.set_source_rgba(0.0, 0.0, 0.0, (0.32 * search_prog) * entry_val)
    cr.fill()
    cr.restore()

    # (3) Translucent Frosted Glass Surface Pill
    cr.save()
    draw_rounded_pill(cr, sx, sy, sw, sh, sr)
    fill_alpha = (0.92 + 0.06 * search_prog) * entry_val
    cr.set_source_rgba(surf_r, surf_g, surf_b, fill_alpha)
    cr.fill_preserve()

    out_alpha = (0.24 + 0.30 * search_prog) * entry_val
    cr.set_source_rgba(out_r, out_g, out_b, out_alpha)
    cr.set_line_width(1.2 + 0.3 * search_prog)
    cr.stroke()
    cr.restore()

    # (4) Left Circular Engine Avatar Island
    if search_prog > 0.25 and search_engines:
        tag_fade = min(1.0, (search_prog - 0.25) / 0.75) * entry_val
        cur_eng = search_engines[current_engine_idx % len(search_engines)]
        eng_layout = cur_eng.get("layout")
        ink_rect = cur_eng.get("icon_ink")

        avatar_d = 44.0
        avatar_r = avatar_d / 2.0
        avatar_cx = sx + 10.0 + avatar_r
        avatar_cy = cy

        switch_prog = max(0.8, min(1.25, engine_switch_spring.current))
        cr.save()
        cr.translate(avatar_cx, avatar_cy)
        cr.scale(switch_prog, switch_prog)
        cr.translate(-avatar_cx, -avatar_cy)

        # Circular Avatar Background
        cr.new_path()
        cr.arc(avatar_cx, avatar_cy, avatar_r, 0, 2 * math.pi)
        cr.set_source_rgba(dim_r, dim_g, dim_b, (0.55 + 0.15 * search_prog) * tag_fade)
        cr.fill_preserve()
        cr.set_source_rgba(out_r, out_g, out_b, (0.18 + 0.14 * search_prog) * tag_fade)
        cr.set_line_width(1.0)
        cr.stroke()

        # Engine Icon Centered
        if ink_rect:
            draw_icon_x = avatar_cx - ink_rect.x - (ink_rect.width / 2.0)
            draw_icon_y = avatar_cy - ink_rect.y - (ink_rect.height / 2.0)
        else:
            draw_icon_x = avatar_cx - 8.0
            draw_icon_y = avatar_cy - 8.0

        cr.move_to(draw_icon_x, draw_icon_y)
        cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], tag_fade)
        PangoCairo.show_layout(cr, eng_layout)
        cr.restore()

        # Text / Placeholder & Neon Caret
        text_start_x = avatar_cx + avatar_r + 14.0
        avail_w = max(20.0, (sx + sw - 22.0) - text_start_x)

        if search_query:
            lt_query = create_pango_layout_fn(search_query)
            lt_query.set_font_description(Pango.FontDescription("Noto Sans CJK SC, Inter Bold 13.5"))
            qw, qh = lt_query.get_pixel_size()

            cr.save()
            cr.rectangle(text_start_x, cy - sh / 2.0, avail_w, sh)
            cr.clip()

            draw_qx = text_start_x if qw <= avail_w else (text_start_x + avail_w - qw)
            cr.move_to(draw_qx, cy - qh / 2.0)
            cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], tag_fade)
            PangoCairo.show_layout(cr, lt_query)
            cr.restore()

            # Breathing Neon Caret
            cursor_x = min(draw_qx + qw + 2.0, sx + sw - 22.0)
            sin_val = (math.sin(cursor_time * 5.5) + 1.0) / 2.0
            cursor_alpha = (0.35 + 0.65 * sin_val) * tag_fade
            cr.save()
            cr.new_path()
            cr.move_to(cursor_x, cy - 12.0)
            cr.line_to(cursor_x, cy + 12.0)
            cr.set_line_width(1.8)
            cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], cursor_alpha)
            cr.stroke()
            cr.restore()

            # Update Native IME Location to track cursor position
            update_im_cursor_fn(cursor_x, cy + 16.0)
        else:
            _, placeholder_h = placeholder_size
            cr.save()
            cr.move_to(text_start_x, cy - placeholder_h / 2.0)
            cr.set_source_rgba(palette["on_surface_var"][0], palette["on_surface_var"][1], palette["on_surface_var"][2], 0.48 * tag_fade)
            PangoCairo.show_layout(cr, layout_placeholder)
            cr.restore()

            sin_val = (math.sin(cursor_time * 5.5) + 1.0) / 2.0
            cursor_alpha = (0.35 + 0.65 * sin_val) * tag_fade
            cr.save()
            cr.new_path()
            cr.move_to(text_start_x, cy - 12.0)
            cr.line_to(text_start_x, cy + 12.0)
            cr.set_line_width(1.8)
            cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], cursor_alpha)
            cr.stroke()
            cr.restore()

            update_im_cursor_fn(text_start_x, cy + 16.0)


def draw_capsules(cr, cx: float, cy: float, orbit_r: float, apps: list,
                  node_springs: list, outer_alpha: float, palette: dict):
    """Draw M3E Content-Aware Adaptive Streamline Capsules."""
    surf_r, surf_g, surf_b = palette["surface"]
    dim_r, dim_g, dim_b = palette["surface_dim"]
    out_r, out_g, out_b = palette["outline"]

    for i, app in enumerate(apps):
        prog = max(0.0, min(1.0, node_springs[i].current)) if i < len(node_springs) else 0.0
        app_r, app_g, app_b = app["color"]
        ang_rad = math.radians(app["center_angle"])

        cur_dist = orbit_r + prog * FLOAT_SPRING
        ix = cx + cur_dist * math.cos(ang_rad)
        iy = cy + cur_dist * math.sin(ang_rad)

        tw, th = app["title_w"], app["title_h"]
        dw, dh = app["desc_w"], app["desc_h"]
        kw, kh = app["badge_w"], app["badge_h"]
        ink_rect = app["icon_ink_rect"]

        cw = app["idle_w"] + (app["active_w"] - app["idle_w"]) * prog
        ch = CAPSULE_IDLE_H + (CAPSULE_ACTIVE_H - CAPSULE_IDLE_H) * prog
        cr_radius = ch / 2.0

        cx_box = ix - cw / 2.0
        cy_box = iy - ch / 2.0

        # Capsule Shadow
        cr.save()
        shadow_y = 2.5 + prog * 4.5
        draw_rounded_pill(cr, cx_box, cy_box + shadow_y, cw, ch, cr_radius)
        cr.set_source_rgba(0.0, 0.0, 0.0, (0.16 + 0.22 * prog) * outer_alpha)
        cr.fill()
        cr.restore()

        # Capsule Background Surface
        fill_r = surf_r + (app_r - surf_r) * (0.34 * prog)
        fill_g = surf_g + (app_g - surf_g) * (0.34 * prog)
        fill_b = surf_b + (app_b - surf_b) * (0.34 * prog)
        fill_alpha = ((0.88 if palette["is_dark"] else 0.94) + 0.08 * prog) * outer_alpha

        draw_rounded_pill(cr, cx_box, cy_box, cw, ch, cr_radius)
        cr.set_source_rgba(fill_r, fill_g, fill_b, fill_alpha)
        cr.fill_preserve()

        b_r = out_r + (app_r - out_r) * prog
        b_g = out_g + (app_g - out_g) * prog
        b_b = out_b + (app_b - out_b) * prog
        b_alpha = (0.16 + prog * 0.74) * outer_alpha
        b_width = 1.0 + prog * 1.2

        cr.set_source_rgba(b_r, b_g, b_b, b_alpha)
        cr.set_line_width(b_width)
        cr.stroke()

        # (A) Left Icon Chip Pill
        chip_cx = cx_box + (ch / 2.0)
        chip_cy = iy
        chip_r = 15.0 + 1.5 * prog

        cr.save()
        cr.new_path()
        cr.arc(chip_cx, chip_cy, chip_r, 0, 2 * math.pi)
        chip_bg_r = out_r + (app_r - out_r) * prog
        chip_bg_g = out_g + (app_g - out_g) * prog
        chip_bg_b = out_b + (app_b - out_b) * prog
        chip_bg_alpha = (0.10 + 0.78 * prog) * outer_alpha
        cr.set_source_rgba(chip_bg_r, chip_bg_g, chip_bg_b, chip_bg_alpha)
        cr.fill_preserve()
        cr.set_source_rgba(chip_bg_r, chip_bg_g, chip_bg_b, (0.18 + 0.65 * prog) * outer_alpha)
        cr.set_line_width(1.0)
        cr.stroke()
        cr.restore()

        cr.save()
        draw_icon_x = chip_cx - ink_rect.x - (ink_rect.width / 2.0)
        draw_icon_y = chip_cy - ink_rect.y - (ink_rect.height / 2.0)
        cr.move_to(draw_icon_x, draw_icon_y)

        if prog > 0.45:
            cr.set_source_rgba(dim_r, dim_g, dim_b, 1.0 * outer_alpha) if palette["is_dark"] else cr.set_source_rgba(1.0, 1.0, 1.0, 1.0 * outer_alpha)
        else:
            cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], 0.94 * outer_alpha)
        PangoCairo.show_layout(cr, app["layout_icon"])
        cr.restore()

        # (B) Middle Typography: Title & Subtitle
        text_x = chip_cx + chip_r + 9.0

        if prog < 0.18:
            title_y = iy - th / 2.0
            cr.save()
            cr.move_to(text_x, title_y)
            cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], 0.90 * outer_alpha)
            PangoCairo.show_layout(cr, app["layout_title"])
            cr.restore()
        else:
            title_y = iy - (th + dh + 1.0) / 2.0 + (1.0 - prog) * 2.0
            desc_y = title_y + th + 1.0

            cr.save()
            cr.move_to(text_x, title_y)
            cr.set_source_rgba(palette["on_surface"][0], palette["on_surface"][1], palette["on_surface"][2], 0.98 * outer_alpha)
            PangoCairo.show_layout(cr, app["layout_title"])

            desc_alpha = min(1.0, (prog - 0.18) / 0.82) * 0.85 * outer_alpha
            cr.move_to(text_x, desc_y)
            cr.set_source_rgba(palette["on_surface_var"][0], palette["on_surface_var"][1], palette["on_surface_var"][2], desc_alpha)
            PangoCairo.show_layout(cr, app["layout_desc"])
            cr.restore()

        # (C) Right Shortcut Badge Pill
        right_pad = 13.0
        key_x = cx_box + cw - right_pad - kw
        key_y = iy - kh / 2.0
        pill_w, pill_h = kw + 8.0, kh + 4.0
        pill_x, pill_y = key_x - 4.0, key_y - 2.0

        cr.save()
        draw_rounded_pill(cr, pill_x, pill_y, pill_w, pill_h, pill_h / 2.0)
        badge_bg_alpha = (0.12 + 0.18 * prog) * outer_alpha
        cr.set_source_rgba(palette["on_surface_var"][0], palette["on_surface_var"][1], palette["on_surface_var"][2], badge_bg_alpha)
        cr.fill()

        cr.move_to(key_x, key_y)
        badge_text_alpha = (0.65 + 0.35 * prog) * outer_alpha
        cr.set_source_rgba(palette["on_surface_var"][0], palette["on_surface_var"][1], palette["on_surface_var"][2], badge_text_alpha)
        PangoCairo.show_layout(cr, app["layout_badge"])
        cr.restore()
