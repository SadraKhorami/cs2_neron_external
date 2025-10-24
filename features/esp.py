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
    _OVERLAY_FONT_PATH = fontpaths.locate_font(
        anchors=[base_dir, repo_dir],
    )

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

    font_id = _ensure_raylib_font()
    if font_id is not None:
        try:
            pme.draw_font(
                fontId=font_id,
                text=str(text),
                posX=int(round(x)),
                posY=int(round(y)),
                fontSize=int(round(size)),
                spacing=0,
                tint=col
            )
            return
        except Exception:
            pass

    font_handle = _get_overlay_font_handle(size)
    if font_handle:
        try:
            pme.draw_text(text, x, y, fontSize=size, color=col, font=font_handle)
            return
        except TypeError:
            pass
        except Exception:
            pass
        try:
            with spectator._FontScope(pme, font_handle):
                pme.draw_text(text, x, y, fontSize=size, color=col)
                return
        except Exception:
            pass

    try:
        pme.draw_text(text, x, y, fontSize=size, color=col)
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

def _draw_shadowed_text(text, x, y, size=12, color="#FFFFFF"):
    base = _resolve_color(color)
    shadow = pme.fade_color(_resolve_color("#000000"), 0.65)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        _draw_text_with_font(text, x + ox, y + oy, size=size, color=shadow)
    _draw_text_with_font(text, x, y, size=size, color=base)

def draw_name(pme, player_name, x, y, color="#FFFFFF", font_size=12):
    if player_name:
        _draw_shadowed_text(player_name, x, y, size=font_size, color=color)

def draw_distance(pme, x, y, distance, color="#FFFFFF", font_size=12):
    _draw_shadowed_text(f"{distance:.1f}m", x, y, size=font_size, color=color)

def draw_health_text(pme, x, y, health, color="#FFFFFF", font_size=12):
    _draw_shadowed_text(f"HP: {int(health)}", x, y, size=font_size, color=color)

def draw_health_bar(pme, health, x, y, height, bar_width=6, background_color="#303030", health_color="#94F3BF", outline_color="#303030"):
	pme.draw_rectangle(x - bar_width - 5, y, bar_width, height, color=pme.get_color(background_color))
	health_percentage = min(1.0, health / 100.0)
	filled_height = height * health_percentage
	pme.draw_rectangle(x - bar_width - 5, y + (height - filled_height), bar_width, filled_height, color=pme.get_color(health_color))
	pme.draw_rectangle_lines(x - bar_width - 5, y, bar_width, height, color=pme.get_color(outline_color), lineThick=1)

def draw_tracer(pme, start_x, start_y, end_x, end_y, color, thickness=1.5):
    if end_y != -1:
        col = _resolve_color(color)
        pme.draw_line(start_x, start_y, end_x, end_y, color=pme.fade_color(col, 0.75), thick=thickness)
        pme.draw_line(start_x, start_y, end_x, end_y, color=col, thick=0.8)

def draw_skeleton(pme, bones, bone_connections, color):
    for start_bone, end_bone in bone_connections:
        if start_bone in bones and end_bone in bones:
            start = bones[start_bone]
            end = bones[end_bone]
            offset_x = (end.x - start.x)
            offset_y = (end.y - start.y)
            pme.draw_line(start.x + offset_x, start.y + offset_y, end.x - offset_x, end.y - offset_y, color=_resolve_color(color), thick=1.2)

def draw_box(pme, rect_left, rect_top, rect_width, rect_height, color):
    base_col = _resolve_color(color)
    fill_col = pme.fade_color(base_col, 0.22)
    soft_border = pme.fade_color(base_col, 0.6)
    pme.draw_rectangle(rect_left, rect_top, rect_width, rect_height, color=fill_col)
    pme.draw_rectangle_lines(rect_left, rect_top, rect_width, rect_height, color=soft_border, lineThick=1.2)
    pme.draw_rectangle_lines(rect_left - 1, rect_top - 1, rect_width + 2, rect_height + 2, color=base_col, lineThick=1.0)


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
    except Exception:
        return False


def ESP_Update(processHandle, clientBaseAddress, Options, Offsets, SharedBombState, SharedRuntime=None):
    # Only render when neron actually has focus (prevents overlay glitches under exclusive fullscreen)
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
        # If any of these fail, don't crash the frame; still begin/end drawing so the overlay stays alive
        viewMatrix = None
        EntityList = None

    # Begin frame
    try:
        pme.begin_drawing()
    except Exception:
        # Guard against begin failures
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
        # Never let HUD block break the ESP pass
        pass

    # --- entities loop ---
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

            if opt_box:
                draw_box(pme, rect_left, rect_top, rect_width, rect_height, color=resolved_color)

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
                draw_health_bar(pme, health, rect_left, rect_top, rect_height)

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

                draw_skeleton(pme, bones, boneConnections, color=resolved_color)
        except Exception:
            continue

    # FOV circle
    try:
        pme.draw_circle_lines(globals.SCREEN_WIDTH // 2, globals.SCREEN_HEIGHT // 2, Options["AimbotFOV"], pme.get_color(Options["FOV_color"]))
    except Exception:
        pass

    # Bomb timer block (modern card)
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

    # End frame
    try:
        pme.end_drawing()
    except Exception:
        pass
