from features import spectator
from ext.datatypes import *
from functions import memfuncs
from functions import calculations
from functions import fontpaths
from functions import logutil

import globals
import os
import win32api, win32gui, win32process, win32con
import pyMeow as pme

_OVERLAY_FONT_PATH = None
_OVERLAY_FONT_PROBED = False

def _find_overlay_font():
    global _OVERLAY_FONT_PATH, _OVERLAY_FONT_PROBED
    if _OVERLAY_FONT_PROBED:
        return _OVERLAY_FONT_PATH

    base_dir = os.path.dirname(__file__)
    repo_dir = os.path.abspath(os.path.join(base_dir, ".."))

    # Try bundled first
    path = fontpaths.locate_font(anchors=[base_dir, repo_dir])

    # System fallback (Windows)
    if not path:
        try:
            windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
            if windir:
                fonts_dir = os.path.join(windir, "Fonts")
                for fname in ("segoeui.ttf", "arial.ttf", "verdana.ttf"):
                    cand = os.path.join(fonts_dir, fname)
                    if os.path.exists(cand):
                        path = cand
                        break
        except Exception:
            path = None

    _OVERLAY_FONT_PATH = path
    _OVERLAY_FONT_PROBED = True
    if _OVERLAY_FONT_PATH:
        logutil.debug(f"[esp] overlay font found: {_OVERLAY_FONT_PATH}")
    else:
        logutil.debug("[esp] overlay font not found; using pyMeow default for spectator HUD.")
    return _OVERLAY_FONT_PATH


_OVERLAY_FONT_CACHE = {}
_OVERLAY_FONT_WARNED = set()
_COLOR_CACHE = {}
_RAYLIB_FONT_ID = None
_RAYLIB_FONT_ATTEMPTED = False
_RAYLIB_FONT_TARGET_ID = 7 


def _ensure_raylib_font():
    global _RAYLIB_FONT_ID, _RAYLIB_FONT_ATTEMPTED
    if _RAYLIB_FONT_ATTEMPTED:
        return _RAYLIB_FONT_ID
    _RAYLIB_FONT_ATTEMPTED = True

    if not (hasattr(pme, "load_font") and hasattr(pme, "draw_font")):
        return None

    font_path = _find_overlay_font()
    if not font_path:
        return None

    try:
        pme.load_font(font_path, _RAYLIB_FONT_TARGET_ID)
        _RAYLIB_FONT_ID = _RAYLIB_FONT_TARGET_ID
        logutil.debug(f"[esp] overlay font loaded via Raylib API: {font_path} (id={_RAYLIB_FONT_ID})")
    except Exception as exc:
        _RAYLIB_FONT_ID = None
        logutil.debug(f"[esp] Raylib font load failed ({font_path}): {exc}")

    return _RAYLIB_FONT_ID


def _get_overlay_font_handle(size: int = 16):
    key = int(size)
    if key in _OVERLAY_FONT_CACHE:
        return _OVERLAY_FONT_CACHE[key]

    font_path = _find_overlay_font()
    if not font_path:
        _OVERLAY_FONT_CACHE[key] = None
        return None

    try:
        handle = spectator.init_spec_font(pme, font_path=font_path, font_size=key)
    except Exception:
        handle = None

    _OVERLAY_FONT_CACHE[key] = handle

    if handle is None and key not in _OVERLAY_FONT_WARNED:
        _OVERLAY_FONT_WARNED.add(key)
        logutil.debug(f"[esp] custom overlay font unavailable at size {key}; fallback to default.")

    return handle


def _draw_text_with_font(text, x, y, *, size, color):
    try:
        col = color if isinstance(color, tuple) else pme.get_color(color)
    except Exception:
        col = color

    xi = int(round(x))
    yi = int(round(y))
    sz = max(10, int(round(size)))

    font_id = _ensure_raylib_font()
    if font_id is not None:
        try:
            pme.draw_font(
                fontId=font_id,
                text=str(text),
                posX=xi,
                posY=yi,
                fontSize=sz,
                spacing=0,
                tint=col
            )
            return
        except Exception:
            pass

    font_handle = _get_overlay_font_handle(sz)
    if font_handle:
        try:
            pme.draw_text(text, xi, yi, fontSize=sz, color=col, font=font_handle)
            return
        except TypeError:
            pass
        except Exception:
            pass
        try:
            with spectator._FontScope(pme, font_handle):
                pme.draw_text(text, xi, yi, fontSize=sz, color=col)
                return
        except Exception:
            pass

    try:
        pme.draw_text(text, xi, yi, fontSize=sz, color=col)
    except Exception:
        pass


def _draw_bomb_status_card(pme, *, planted, time_left, total_time=40.0):
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
                detail_text = "Syncing timer..."
                show_progress = False
                remaining = 0.0
            else:
                remaining = max(0.0, float(time_left))
                detail_text = f"{int(round(remaining))}s until detonation"
                show_progress = True
        else:
            detail_text = "No active bomb detected."
            show_progress = False
            remaining = 0.0

        _draw_text_with_font("BOMB STATUS", inner_x + pad_x, title_y, size=title_size, color=col_title)
        _draw_text_with_font(status_text, inner_x + pad_x, status_y, size=status_size, color=status_accent)
        _draw_text_with_font(detail_text, inner_x + pad_x, detail_y, size=detail_size, color=col_muted)

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
            # _draw_text_with_font(f"{int(round(remaining))}s remaining", bar_x, bar_y - 18, size=13, color=col_muted)
    except Exception:
        pass

boneConnections = [
    ('head', 'neck_0'), ('neck_0', 'spine_1'), ('spine_1', 'spine_2'), ('spine_2', 'pelvis'),
    ('pelvis', 'leg_upper_L'), ('leg_upper_L', 'leg_lower_L'), ('leg_lower_L', 'ankle_L'),
    ('pelvis', 'leg_upper_R'), ('leg_upper_R', 'leg_lower_R'), ('leg_lower_R', 'ankle_R'),
    ('spine_2', 'arm_upper_L'), ('arm_upper_L', 'arm_lower_L'), ('arm_lower_L', 'hand_L'),
    ('spine_2', 'arm_upper_R'), ('arm_upper_R', 'arm_lower_R'), ('arm_lower_R', 'hand_R')
]

def _resolve_color(color):
    if isinstance(color, (tuple, list)):
        return color
    if not isinstance(color, str):
        return color
    cached = _COLOR_CACHE.get(color)
    if cached is not None:
        return cached
    try:
        resolved = pme.get_color(color)
    except Exception:
        resolved = pme.get_color("#FFFFFF")
    _COLOR_CACHE[color] = resolved
    return resolved


def _clamp(v, lo, hi):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color_hex(hex_a: str, hex_b: str, t: float) -> str:
    def to_rgb(h):
        h = h.lstrip('#')
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    def to_hex(rgb):
        r, g, b = [int(_clamp(x, 0, 255)) for x in rgb]
        return f"#{r:02X}{g:02X}{b:02X}"
    ra, ga, ba = to_rgb(hex_a)
    rb, gb, bb = to_rgb(hex_b)
    r = _lerp(ra, rb, t)
    g = _lerp(ga, gb, t)
    b = _lerp(ba, bb, t)
    return to_hex((r, g, b))


def _health_color_hex(health: int) -> str:
    h = int(_clamp(health, 0, 100))
    if h <= 50:
        # red (#FF3B30) to orange-yellow (#F59E0B)
        t = h / 50.0
        return _lerp_color_hex("#FF3B30", "#F59E0B", t)
    else:
        # orange-yellow to green (#22C55E)
        t = (h - 50) / 50.0
        return _lerp_color_hex("#F59E0B", "#22C55E", t)

def _draw_shadowed_text(text, x, y, size=12, color="#FFFFFF"):
    """Crisp text helper: minimal shadow for small sizes, fuller outline for larger."""
    base = _resolve_color(color)
    sz = int(round(size))
    if sz <= 15:
        # Minimal 1px drop for sharp small text
        shadow = pme.fade_color(_resolve_color("#000000"), 0.55)
        _draw_text_with_font(text, int(round(x))+1, int(round(y))+1, size=sz, color=shadow)
        _draw_text_with_font(text, int(round(x)), int(round(y)), size=sz, color=base)
    else:
        # Soft 4-direction outline for larger headings
        shadow = pme.fade_color(_resolve_color("#000000"), 0.65)
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _draw_text_with_font(text, x + ox, y + oy, size=sz, color=shadow)
        _draw_text_with_font(text, x, y, size=sz, color=base)

def draw_name(pme, player_name, x, y, color="#FFFFFF", font_size=12):
    if player_name:
        _draw_shadowed_text(player_name, x, y, size=font_size, color=color)

def draw_distance(pme, x, y, distance, color="#FFFFFF", font_size=12):
    _draw_shadowed_text(f"{distance:.1f}m", x, y, size=font_size, color=color)

def draw_health_text(pme, x, y, health, color="#FFFFFF", font_size=12):
    _draw_shadowed_text(f"HP: {int(health)}", x, y, size=font_size, color=color)

def draw_health_bar(pme, health, x, y, height, bar_width=None, thickness_scale=1.0, use_health_color=True, team_color=None):
    if bar_width is None:
        bw = _clamp(height * 0.02, 2.0, 6.0) 
    else:
        bw = float(bar_width)

    # Apply user scale
    try:
        bw *= float(thickness_scale or 1.0)
    except Exception:
        pass
    bw = _clamp(bw, 1.0, 8.0)

    track_x = int(round(x)) - (int(round(bw)) + 6)
    track_y = int(round(y))
    track_h = int(round(height))
    track_w = int(round(bw))

    # Colors
    col_bg = pme.get_color("#111418")
    col_border = pme.get_color("#29313A")
    if use_health_color:
        col_fill = pme.get_color(_health_color_hex(int(health)))
    else:
        col_fill = team_color if isinstance(team_color, tuple) else pme.get_color("#22C55E")

    # Track
    pme.draw_rectangle(track_x, track_y, track_w, track_h, color=col_bg)
    pme.draw_rectangle_lines(track_x, track_y, track_w, track_h, color=col_border, lineThick=1)

    # Fill (from bottom up)
    ratio = max(0.0, min(1.0, (health or 0) / 100.0))
    filled = int(round(track_h * ratio))
    if filled > 0:
        pme.draw_rectangle(track_x, track_y + (track_h - filled), track_w, filled, color=col_fill)

    # Segments (ticks)
    segs = 5
    tick_col = pme.fade_color(col_border, 0.9)
    for s in range(1, segs):
        yy = track_y + int(round(track_h * (s / segs)))
        pme.draw_line(track_x, yy, track_x + track_w, yy, color=tick_col, thick=1)

def draw_tracer(pme, start_x, start_y, end_x, end_y, color, thickness=1.5):
    if end_y != -1:
        col = _resolve_color(color)
        pme.draw_line(start_x, start_y, end_x, end_y, color=pme.fade_color(col, 0.75), thick=thickness)
        pme.draw_line(start_x, start_y, end_x, end_y, color=col, thick=0.8)

def draw_skeleton(pme, bones, bone_connections, color, thickness=None, joint_radius=None):
    """Stylized skeleton with distance-aware thickness and joint dots."""
    col = _resolve_color(color)

    # Auto-derive scale if not provided via rect height
    if thickness is None or joint_radius is None:
        try:
            xs = [pt.x for pt in bones.values()]
            ys = [pt.y for pt in bones.values()]
            scale = max(max(xs) - min(xs), max(ys) - min(ys))
        except Exception:
            scale = 50.0
        if thickness is None:
            thickness = _clamp(scale * 0.02, 1.0, 2.2)
        if joint_radius is None:
            joint_radius = int(round(_clamp(scale * 0.03, 1.0, 3.0)))

    # draw bone segments
    for start_bone, end_bone in bone_connections:
        if start_bone in bones and end_bone in bones:
            s = bones[start_bone]
            e = bones[end_bone]
            pme.draw_line(s.x, s.y, e.x, e.y, color=col, thick=thickness)
    # draw joints (filled circles)
    try:
        for _, pt in bones.items():
            pme.draw_circle(int(pt.x), int(pt.y), int(joint_radius), color=col)
    except Exception:
        pass

def draw_box(pme, rect_left, rect_top, rect_width, rect_height, color, thickness_scale=1.0):
    """Corner bracket box with distance-aware scaling to stay clean at range."""
    base = _resolve_color(color)
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
    col = pme.fade_color(base, fade)

    # top-left
    pme.draw_line(x1, y1, x1 + L, y1, color=col, thick=T)
    pme.draw_line(x1, y1, x1, y1 + L, color=col, thick=T)
    # top-right
    pme.draw_line(x2, y1, x2 - L, y1, color=col, thick=T)
    pme.draw_line(x2, y1, x2, y1 + L, color=col, thick=T)
    # bottom-left
    pme.draw_line(x1, y2, x1 + L, y2, color=col, thick=T)
    pme.draw_line(x1, y2, x1, y2 - L, color=col, thick=T)
    # bottom-right
    pme.draw_line(x2, y2, x2 - L, y2, color=col, thick=T)
    pme.draw_line(x2, y2, x2, y2 - L, color=col, thick=T)


def _neron_has_focus():
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        h = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
        try:
            exe = win32process.GetModuleFileNameEx(h, 0)
            return os.path.basename(exe).lower() == "cs2.exe"
        except Exception:
            title = (win32gui.GetWindowText(hwnd) or "").lower()
            return ("Counter-Strike 2" in title)
        finally:
            # Avoid handle leaks on frequent focus checks
            try:
                win32api.CloseHandle(h)
            except Exception:
                pass
    except Exception:
        return False


def ESP_Update(processHandle, clientBaseAddress, Options, Offsets, SharedBombState, SharedRuntime=None):
    if not _neron_has_focus():
        try:
            pme.end_drawing()
        except Exception:
            pass
        return

    try:

        localPlayerEnt_pawnAddress = memfuncs.ProcMemHandler.ReadPointer(processHandle, clientBaseAddress + Offsets.offset.dwLocalPlayerPawn)
        localPlayerEnt_controllerAddress = memfuncs.ProcMemHandler.ReadPointer(processHandle, clientBaseAddress + Offsets.offset.dwLocalPlayerController)
        localPlayerEnt_Team = memfuncs.ProcMemHandler.ReadInt(processHandle, localPlayerEnt_pawnAddress + Offsets.offset.m_iTeamNum)
        localPlayerEnt_origin = memfuncs.ProcMemHandler.ReadVec(processHandle, localPlayerEnt_pawnAddress + Offsets.offset.m_vOldOrigin)

        viewMatrix = memfuncs.ProcMemHandler.ReadMatrix(processHandle, clientBaseAddress + Offsets.offset.dwViewMatrix)
        EntityList = memfuncs.ProcMemHandler.ReadPointer(processHandle, clientBaseAddress + Offsets.offset.dwEntityList)
    except Exception:
        viewMatrix = None
        EntityList = None

    try:
        pme.begin_drawing()
    except Exception:
        return

    overlay_font_path = _find_overlay_font()
    overlay_font_id = _ensure_raylib_font()
    overlay_font_handle = _get_overlay_font_handle(16)

    try:
        specs_snapshot = []
        if SharedRuntime is not None:
            try:
                specs_snapshot = list(SharedRuntime.spectators)
            except Exception:
                specs_snapshot = []
        spectator.render_spectator_block(
            pme,
            specs_snapshot,
            enabled=Options.get("EnableShowSpectators", True),
            screen_size=(globals.SCREEN_WIDTH, globals.SCREEN_HEIGHT),
            font_path=overlay_font_path,
            font_id=overlay_font_id,
            font_handle=overlay_font_handle,
            font_size=16
        )
    except Exception:
        pass

    try:
        viewMatrix = memfuncs.ProcMemHandler.ReadMatrix(processHandle, clientBaseAddress + Offsets.offset.dwViewMatrix)
    except Exception:
        pass

    if viewMatrix is None or EntityList is None:
        try:
            pme.end_drawing()
        except Exception:
            pass
        return

    screen_w = globals.SCREEN_WIDTH
    screen_h = globals.SCREEN_HEIGHT

    opt_box = Options.get("EnableESPBoxRendering", False)
    opt_name = Options.get("EnableESPNameText", False)
    opt_distance = Options.get("EnableESPDistanceText", False)
    opt_health_text = Options.get("EnableESPHealthText", False)
    opt_health_bar = Options.get("EnableESPHealthBarRendering", False)
    opt_tracer = Options.get("EnableESPTracerRendering", False)
    opt_skeleton = Options.get("EnableESPSkeletonRendering", False)
    opt_team_check = Options.get("EnableESPTeamCheck", False)

    render_required = any((opt_box, opt_name, opt_distance, opt_health_text, opt_health_bar, opt_tracer, opt_skeleton))

    ct_color = Options.get("CT_color", "#4DA2FF")
    t_color = Options.get("T_color", "#FF6A5A")
    ct_color_resolved = _resolve_color(ct_color)
    t_color_resolved = _resolve_color(t_color)

    for i in range(64) if render_required else []:
        try:
            list_entry = memfuncs.ProcMemHandler.ReadPointer(processHandle, EntityList + (8 * (i & 0x7FFF) >> 9) + 16)
            if not list_entry:
                continue

            controller = memfuncs.ProcMemHandler.ReadPointer(processHandle, list_entry + 112 * (i & 0x1FF))
            if not controller or controller == localPlayerEnt_controllerAddress:
                continue

            pawnHandle = memfuncs.ProcMemHandler.ReadInt(processHandle, controller + Offsets.offset.m_hPlayerPawn)
            if not pawnHandle:
                continue

            list_entry2 = memfuncs.ProcMemHandler.ReadPointer(processHandle, EntityList + 0x8 * ((pawnHandle & 0x7FFF) >> 9) + 0x10)
            if not list_entry2:
                continue

            pawn = memfuncs.ProcMemHandler.ReadPointer(processHandle, list_entry2 + 0x70 * (pawnHandle & 0x1FF))
            if not pawn or pawn == localPlayerEnt_pawnAddress:
                continue

            health = memfuncs.ProcMemHandler.ReadInt(processHandle, pawn + Offsets.offset.m_iHealth)
            team = memfuncs.ProcMemHandler.ReadInt(processHandle, controller + Offsets.offset.m_iTeamNum)
            lifeState = memfuncs.ProcMemHandler.ReadInt(processHandle, pawn + Offsets.offset.m_lifeState)

            if lifeState != 256 or (opt_team_check and team == localPlayerEnt_Team):
                continue

            sceneNode = memfuncs.ProcMemHandler.ReadPointer(processHandle, pawn + Offsets.offset.m_pGameSceneNode)
            boneMatrix = memfuncs.ProcMemHandler.ReadPointer(processHandle, sceneNode + Offsets.offset.m_modelState + 0x80)
            origin = memfuncs.ProcMemHandler.ReadVec(processHandle, pawn + Offsets.offset.m_vOldOrigin)

            entity_head = memfuncs.ProcMemHandler.ReadVec(processHandle, boneMatrix + (6 * 32))
            screen_head = calculations.world_to_screen(viewMatrix, Vector3(entity_head.x, entity_head.y, entity_head.z + 7))
            screen_feet = calculations.world_to_screen(viewMatrix, origin)
            box_top = calculations.world_to_screen(viewMatrix, Vector3(origin.x, origin.y, origin.z + 70))

            if screen_head.x <= -1 or screen_feet.y <= -1 or screen_head.x >= screen_w or screen_head.y >= screen_h:
                continue

            distance = calculations.distance_vec3(origin, localPlayerEnt_origin)
            if distance < 35:
                continue

            box_height = screen_feet.y - box_top.y
            rect_left = screen_feet.x - box_height / 4
            rect_top = box_top.y
            rect_width = box_height / 2
            rect_height = box_height
            rect_center_x = rect_left + rect_width / 2
            rect_center_y = rect_top + rect_height / 2
            rect_right = rect_left + rect_width
            info_x = rect_right + 12
            info_y = rect_top + 4

            resolved_color = t_color_resolved if team == 2 else ct_color_resolved
            health_hex = _health_color_hex(int(health))
            try:
                sync_skel = bool(Options.get("ESP_HealthSyncSkeleton", True))
            except Exception:
                sync_skel = True
            try:
                sync_bar = bool(Options.get("ESP_HealthSyncBar", True))
            except Exception:
                sync_bar = True
            try:
                skel_scale = float(Options.get("ESP_SkeletonThicknessScale", 1.0) or 1.0)
            except Exception:
                skel_scale = 1.0
            try:
                box_scale = float(Options.get("ESP_BoxThicknessScale", 1.0) or 1.0)
            except Exception:
                box_scale = 1.0
            try:
                bar_scale = float(Options.get("ESP_HealthBarThicknessScale", 1.0) or 1.0)
            except Exception:
                bar_scale = 1.0

            if opt_box:
                draw_box(pme, rect_left, rect_top, rect_width, rect_height, color=resolved_color, thickness_scale=box_scale)

            info_cursor = info_y
            if opt_name:
                EntityNameAddress = memfuncs.ProcMemHandler.ReadPointer(processHandle, controller + Offsets.offset.m_sSanitizedPlayerName)
                name = memfuncs.ProcMemHandler.ReadString(processHandle, EntityNameAddress, 64) if EntityNameAddress else "?"
                draw_name(pme, name.strip(), info_x, info_cursor, color="#E8F1FF")
                info_cursor += 14

            if opt_distance:
                draw_distance(pme, info_x, info_cursor, distance, color="#A4B0C3")
                info_cursor += 14

            if opt_health_text:
                draw_health_text(pme, info_x, info_cursor, health, color="#82FFAE")

            if opt_health_bar:
                draw_health_bar(
                    pme,
                    health,
                    rect_left,
                    rect_top,
                    rect_height,
                    thickness_scale=bar_scale,
                    use_health_color=sync_bar,
                    team_color=resolved_color,
                )

            if opt_tracer:
                draw_tracer(pme, screen_w // 2, screen_h, rect_center_x, rect_center_y, color=resolved_color)

            if opt_skeleton:
                bone_array = memfuncs.ProcMemHandler.ReadPointer(processHandle, sceneNode + Offsets.offset.m_modelState + Offsets.offset.m_boneArray)
                if not bone_array:
                    continue

                bones = {}
                for bone_name, bone_index in PLAYER_BONES.items():
                    bone_pos = memfuncs.ProcMemHandler.ReadVec(processHandle, bone_array + bone_index * 32)
                    bones[bone_name] = calculations.world_to_screen(viewMatrix, bone_pos)

                sk_thick = max(0.9, min(1.8, rect_height * 0.012)) * skel_scale
                sk_radius = int(max(1.0, min(3.0, rect_height * 0.02)))
                skel_col = health_hex if sync_skel else (resolved_color if isinstance(resolved_color, str) else resolved_color)
                draw_skeleton(pme, bones, boneConnections, color=skel_col, thickness=sk_thick, joint_radius=sk_radius)
        except Exception:
            continue

    try:
        pme.draw_circle_lines(globals.SCREEN_WIDTH // 2, globals.SCREEN_HEIGHT // 2, Options["AimbotFOV"], pme.get_color(Options["FOV_color"]))
    except Exception:
        pass

    try:
        if Options.get("EnableESPBombTimer", False) and SharedBombState is not None:
            planted = getattr(SharedBombState, "bombPlanted", False)
            time_left = getattr(SharedBombState, "bombTimeLeft", -1)
            total_time = getattr(SharedBombState, "bombTimeTotal", 40)
            _draw_bomb_status_card(
                pme,
                planted=planted,
                time_left=time_left,
                total_time=total_time or 40
            )
    except Exception:
        pass

    try:
        pme.end_drawing()
    except Exception:
        pass
