import pyMeow as pme
from .colors import resolve_color
from .fonts import draw_text as _draw_text


def draw_shadowed_label(text, x, y, size=12, color="#FFFFFF"):
    base = resolve_color(color)
    shadow = pme.fade_color(resolve_color("#000000"), 0.65)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        _draw_text(text, x + ox, y + oy, size=size, color=shadow)
    _draw_text(text, x, y, size=size, color=base)


def draw_name(pme_module, player_name, x, y, color="#FFFFFF", font_size=12):
    if player_name:
        draw_shadowed_label(player_name, x, y, size=font_size, color=color)


def draw_distance(pme_module, x, y, distance, color="#FFFFFF", font_size=12):
    draw_shadowed_label(f"{distance:.1f}m", x, y, size=font_size, color=color)


def draw_health_text(pme_module, x, y, health, color="#FFFFFF", font_size=12):
    draw_shadowed_label(f"HP: {int(health)}", x, y, size=font_size, color=color)


def draw_health_bar(pme_module, health, x, y, height, bar_width=None, thickness_scale=1.0, use_health_color=True, team_color=None, color_from_hex=None):
    from .colors import clamp
    if bar_width is None:
        bw = clamp(height * 0.02, 2.0, 6.0)
    else:
        bw = float(bar_width)
    try:
        bw *= float(thickness_scale or 1.0)
    except Exception:
        pass
    bw = clamp(bw, 1.0, 8.0)
    track_x = int(round(x)) - (int(round(bw)) + 6)
    track_y = int(round(y))
    track_h = int(round(height))
    track_w = int(round(bw))

    col_bg = pme.get_color("#111418")
    col_border = pme.get_color("#29313A")
    if use_health_color and color_from_hex is not None:
        col_fill = pme.get_color(color_from_hex)
    else:
        col_fill = team_color if isinstance(team_color, tuple) else pme.get_color("#22C55E")

    pme.draw_rectangle(track_x, track_y, track_w, track_h, color=col_bg)
    pme.draw_rectangle_lines(track_x, track_y, track_w, track_h, color=col_border, lineThick=1)
    ratio = max(0.0, min(1.0, (health or 0) / 100.0))
    filled = int(round(track_h * ratio))
    if filled > 0:
        pme.draw_rectangle(track_x, track_y + (track_h - filled), track_w, filled, color=col_fill)
    segs = 5
    tick_col = pme.fade_color(col_border, 0.9)
    for s in range(1, segs):
        yy = track_y + int(round(track_h * (s / segs)))
        pme.draw_line(track_x, yy, track_x + track_w, yy, color=tick_col, thick=1)


def draw_box(pme_module, rect_left, rect_top, rect_width, rect_height, color, thickness_scale=1.0):
    base = resolve_color(color)
    x1, y1 = int(rect_left), int(rect_top)
    x2, y2 = int(rect_left + rect_width), int(rect_top + rect_height)

    size = max(1.0, float(min(rect_width, rect_height)))
    L = int(max(4.0, min(24.0, size * 0.22)))
    T = max(1.3, min(2.6, size * 0.018))
    try:
        T *= float(thickness_scale or 1.0)
    except Exception:
        pass
    T = max(0.8, min(3.2, T))

    fade = max(0.65, min(1.0, size / 120.0))
    col = pme.fade_color(base, 0.9 * fade + 0.1)

    pme.draw_line(x1, y1, x1 + L, y1, color=col, thick=T)
    pme.draw_line(x1, y1, x1, y1 + L, color=col, thick=T)
    pme.draw_line(x2, y1, x2 - L, y1, color=col, thick=T)
    pme.draw_line(x2, y1, x2, y1 + L, color=col, thick=T)
    pme.draw_line(x1, y2, x1 + L, y2, color=col, thick=T)
    pme.draw_line(x1, y2, x1, y2 - L, color=col, thick=T)
    pme.draw_line(x2, y2, x2 - L, y2, color=col, thick=T)
    pme.draw_line(x2, y2, x2, y2 - L, color=col, thick=T)


def draw_skeleton(pme_module, bones, bone_connections, color, thickness=None, joint_radius=None):
    from .colors import clamp
    col = resolve_color(color)
    if thickness is None or joint_radius is None:
        try:
            xs = [pt.x for pt in bones.values()]
            ys = [pt.y for pt in bones.values()]
            scale = max(max(xs) - min(xs), max(ys) - min(ys))
        except Exception:
            scale = 50.0
        if thickness is None:
            thickness = clamp(scale * 0.02, 1.0, 2.2)
        if joint_radius is None:
            joint_radius = int(round(clamp(scale * 0.03, 1.0, 3.0)))
    for s_name, e_name in bone_connections:
        if s_name in bones and e_name in bones:
            s = bones[s_name]; e = bones[e_name]
            pme.draw_line(s.x, s.y, e.x, e.y, color=col, thick=thickness)
    try:
        for _, pt in bones.items():
            pme.draw_circle(int(pt.x), int(pt.y), int(joint_radius), color=col)
    except Exception:
        pass


def draw_bomb_status_card(pme_module, *, planted, time_left, total_time=40.0):
    import globals
    try:
        screen_h = globals.SCREEN_HEIGHT
        card_w = 236
        card_h = 118 if planted else 104
        pad_x = 16
        pad_y = 12
        title_size = 16
        status_size = 18
        detail_size = 14
        x = 28
        y = (screen_h - card_h) // 2
        base_accent = pme.get_color("#588bc4")
        status_accent = pme.get_color("#f87171") if planted else pme.get_color("#34d399")
        col_shadow = pme.fade_color(pme.get_color("#000000"), 0.28)
        col_border = pme.fade_color(base_accent, 0.48)
        col_bg = pme.fade_color(pme.get_color("#101726"), 0.92)
        col_title = pme.get_color("#f0f4ff")
        col_muted = pme.fade_color(pme.get_color("#a3b5d3"), 0.9)
        col_bar_bg = pme.fade_color(pme.get_color("#111a2b"), 0.95)
        pme.draw_rectangle(x + 3, y + 5, card_w, card_h, col_shadow)
        pme.draw_rectangle(x, y, card_w, card_h, col_border)
        inner_x = x + 1
        inner_y = y + 1
        inner_w = card_w - 2
        inner_h = card_h - 2
        pme.draw_rectangle(inner_x, inner_y, inner_w, inner_h, col_bg)
        pme.draw_rectangle(inner_x, inner_y, 3, inner_h, base_accent)
        title_y = inner_y + pad_y
        status_y = title_y + title_size + 6
        detail_y = status_y + status_size + 6
        status_text = "PLANTED" if planted else "SAFE"
        if planted:
            if time_left < 0:
                detail_text = "Syncing timer..."; show_progress = False; remaining = 0.0
            else:
                remaining = max(0.0, float(time_left))
                detail_text = f"{int(round(remaining))}s until detonation"; show_progress = True
        else:
            detail_text = "No active bomb detected."; show_progress = False; remaining = 0.0
        _draw_text("BOMB STATUS", inner_x + pad_x, title_y, size=title_size, color=col_title)
        _draw_text(status_text, inner_x + pad_x, status_y, size=status_size, color=status_accent)
        _draw_text(detail_text, inner_x + pad_x, detail_y, size=detail_size, color=col_muted)
        if planted and show_progress:
            total = max(0.01, float(total_time or 40.0))
            ratio = max(0.0, min(1.0, remaining / total))
            bar_width = inner_w - pad_x * 2
            bar_height = 12
            bar_x = inner_x + pad_x
            bar_y = inner_y + inner_h - pad_y - bar_height
            pme.draw_rectangle(bar_x, bar_y, bar_width, bar_height, col_bar_bg)
            fill_width = int(round(bar_width * ratio))
            if fill_width > 0:
                pme.draw_rectangle(bar_x, bar_y, fill_width, bar_height, pme.fade_color(status_accent, 0.82))
            pme.draw_rectangle_lines(bar_x, bar_y, bar_width, bar_height, pme.fade_color(status_accent, 0.65), lineThick=1.0)
    except Exception:
        pass
