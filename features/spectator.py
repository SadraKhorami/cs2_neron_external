import time
import os
from functions import memfuncs
from functions import fontpaths
from functions import logutil
from functions.process_watcher import ProcessConnector

_SPEC_LOG_LEVEL = 0  # 0: silent, 1: minimal, 2: verbose

def set_spec_log_level(level: int):
    global _SPEC_LOG_LEVEL
    try:
        _SPEC_LOG_LEVEL = max(0, min(2, int(level)))
    except Exception:
        _SPEC_LOG_LEVEL = 0

if logutil.is_debug_enabled():
    _SPEC_LOG_LEVEL = 2

def _log(level: int, msg: str):
    if _SPEC_LOG_LEVEL >= level:
        logutil.debug(msg)

# ---- optional custom font support for pyMeow overlay ------------------------
_SPEC_FONT_HANDLE = None
_SPEC_FONT_KEY = None  # (font_path, size) for caching
_SPEC_FONT_SIZE = 16
_SPEC_FONT_READY = False
_SPEC_FONT_LOGGED = False  # avoid log spam

def _pme_has(obj, name):
    return hasattr(obj, name)

def _log_once(msg):
    global _SPEC_FONT_LOGGED
    if _SPEC_LOG_LEVEL < 2:
        _SPEC_FONT_LOGGED = True
        return
    if not _SPEC_FONT_LOGGED:
        logutil.debug(msg)
        _SPEC_FONT_LOGGED = True

def _probe_pme_font_caps(pme):
    return {
        "direct_api": any(_pme_has(pme, nm) for nm in ("add_font","add_font_from_file","load_font","font_add","FontAdd")),
        "has_imgui": _pme_has(pme, "imgui") or _pme_has(pme, "ImGui"),
        "has_io": any(_pme_has(pme, nm) for nm in ("get_io","GetIO","io","IO"))
    }

def init_spec_font(pme, font_path=None, font_size=16):
    global _SPEC_FONT_HANDLE, _SPEC_FONT_KEY, _SPEC_FONT_SIZE, _SPEC_FONT_READY

    # normalize cache key; allow re-init if (path,size) changes
    key = (font_path or "", int(font_size or 16))
    if _SPEC_FONT_HANDLE is not None and _SPEC_FONT_KEY == key:
        return _SPEC_FONT_HANDLE

    _SPEC_FONT_SIZE = max(10, int(font_size or 16))
    handle = None
    caps = _probe_pme_font_caps(pme)

    # ensure absolute path (some ImGui wrappers reject relative paths)
    if font_path:
        try:
            font_path = os.path.abspath(font_path)
        except Exception:
            pass

    # path 1: direct pyMeow API (rare)
    if caps["direct_api"] and font_path:
        for nm in ("add_font","add_font_from_file","load_font","font_add","FontAdd"):
            f = getattr(pme, nm, None)
            if not f:
                continue
            # try str path then bytes path
            for path_variant in (font_path, font_path.encode("utf-8", "ignore")):
                try:
                    handle = f(path_variant, _SPEC_FONT_SIZE)
                    if handle:
                        break
                except TypeError:
                    try:
                        handle = f(path=path_variant, size=_SPEC_FONT_SIZE)
                        if handle:
                            break
                    except Exception:
                        handle = None
                except Exception:
                    handle = None
            if handle:
                break

    # path 2: via pme.imgui (common in some builds)
    if not handle and font_path and (caps["has_imgui"] or caps["has_io"]):
        try:
            imgui = getattr(pme, "imgui", None) or getattr(pme, "ImGui", None) or pme
            get_io = getattr(imgui, "get_io", None) or getattr(imgui, "GetIO", None)
            io = None
            if get_io:
                try:
                    io = get_io()
                except Exception:
                    io = None
            # some builds expose io object directly
            if io is None:
                io = getattr(imgui, "io", None) or getattr(imgui, "IO", None)

            fonts = None
            if io is not None:
                fonts = getattr(io, "fonts", None) or getattr(io, "Fonts", None)
            if fonts is None:
                fonts = getattr(imgui, "fonts", None) or getattr(imgui, "Fonts", None)

            if fonts:
                add_ttf = (
                    getattr(fonts, "add_font_from_file_ttf", None) or
                    getattr(fonts, "AddFontFromFileTTF", None) or
                    getattr(fonts, "add_font", None) or
                    getattr(fonts, "AddFont", None)
                )
                if add_ttf:
                    # try str then bytes
                    for path_variant in (font_path, font_path.encode("utf-8", "ignore")):
                        try:
                            handle = add_ttf(path_variant, _SPEC_FONT_SIZE)
                            if handle:
                                break
                        except Exception:
                            handle = None

                # try to build/upload font atlas if API exists
                if handle:
                    build = getattr(fonts, "build", None) or getattr(fonts, "Build", None)
                    if build:
                        try:
                            build()
                        except Exception:
                            pass
                    tex_update = (
                        getattr(imgui, "update_fonts_texture", None) or
                        getattr(imgui, "UpdateFontsTexture", None) or
                        getattr(imgui, "fonts_texture_upload", None) or
                        getattr(imgui, "FontsTextureUpload", None)
                    )
                    if tex_update:
                        try:
                            tex_update()
                        except Exception:
                            pass
        except Exception:
            handle = None

    _SPEC_FONT_HANDLE = handle
    _SPEC_FONT_KEY = key
    _SPEC_FONT_READY = True

    if handle:
        _log(2, f"[overlay/spec] custom font loaded (size={_SPEC_FONT_SIZE}).")
    else:
        _log_once("[overlay/spec] pyMeow build has no usable font API; using default overlay font.")
    return _SPEC_FONT_HANDLE

class _FontScope:
    def __init__(self, pme, font):
        self.pme = pme
        self.font = font
        self._pushed = False

    def __enter__(self):
        if not self.font:
            return self
        # prefer ImGui push if present
        imgui = getattr(self.pme, "imgui", None) or getattr(self.pme, "ImGui", None) or self.pme
        if imgui:
            for nm in ("push_font", "PushFont"):
                f = getattr(imgui, nm, None)
                if f:
                    try:
                        f(self.font)
                        self._pushed = True
                        return self
                    except Exception:
                        pass
        # fallback to any direct pme push
        for nm in ("push_font", "font_push", "PushFont"):
            f = getattr(self.pme, nm, None)
            if f:
                try:
                    f(self.font)
                    self._pushed = True
                    return self
                except Exception:
                    pass
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._pushed:
            return False
        imgui = getattr(self.pme, "imgui", None) or getattr(self.pme, "ImGui", None) or self.pme
        if imgui:
            for nm in ("pop_font", "PopFont"):
                f = getattr(imgui, nm, None)
                if f:
                    try:
                        f()
                        return False
                    except Exception:
                        pass
        for nm in ("pop_font", "font_pop", "PopFont"):
            f = getattr(self.pme, nm, None)
            if f:
                try:
                    f()
                    return False
                except Exception:
                    pass
        return False

# ---- styled text fallback (when custom font isn't available) ---------------
def _draw_text_styled(pme, text, x, y, fontSize, color):
    """Draw text with a soft outline/shadow so default overlay font looks cleaner."""
    try:
        base_col = color
        try:
            if isinstance(color, str):
                base_col = pme.get_color(color)
        except Exception:
            pass
        shadow = pme.fade_color(pme.get_color("#000000"), 0.6)
        pme.draw_text(text, x + 1, y + 1, fontSize=fontSize, color=shadow)
        pme.draw_text(text, x - 1, y + 1, fontSize=fontSize, color=shadow)
        pme.draw_text(text, x + 1, y - 1, fontSize=fontSize, color=shadow)
        pme.draw_text(text, x - 1, y - 1, fontSize=fontSize, color=shadow)
        pme.draw_text(text, x,     y,     fontSize=fontSize, color=base_col)
    except Exception:
        try:
            pme.draw_text(text, x, y, fontSize=fontSize, color=color)
        except Exception:
            pass

# ---- Observer modes
OBS_MODE_NONE      = 0
OBS_MODE_DEATHCAM  = 1
OBS_MODE_FREEZECAM = 2
OBS_MODE_FIXED     = 3
OBS_MODE_IN_EYE    = 4
OBS_MODE_CHASE     = 5
OBS_MODE_ROAMING   = 6

MODE_NAMES = {
    OBS_MODE_NONE:      "NONE",
    OBS_MODE_DEATHCAM:  "DEATHCAM",
    OBS_MODE_FREEZECAM: "FREEZECAM",
    OBS_MODE_FIXED:     "FIXED",
    OBS_MODE_IN_EYE:    "IN_EYE",
    OBS_MODE_CHASE:     "CHASE",
    OBS_MODE_ROAMING:   "ROAMING",
}

SCAN_INTERVAL_SEC = 0.30
MAX_ENTITIES      = 128

# ---- address sanitation / formatting
MASK64   = 0xFFFFFFFFFFFFFFFF
USER_LOW  = 0x0000000000100000   
USER_HIGH = 0x00007FFFFFFFFFFF  

def to_u64(x):
    try:
        return int(x) & MASK64
    except Exception:
        return 0

def fmtp(p):
    return f"0x{to_u64(p):016X}"

def is_valid_ptr(p):
    p = to_u64(p)
    return USER_LOW <= p <= USER_HIGH

# ---------- safe reads ----------
def rd_ptr(h, addr):
    try:
        p = memfuncs.ProcMemHandler.ReadPointer(h, addr)
        p = to_u64(p)
        return p if is_valid_ptr(p) else 0
    except Exception:
        return 0

def rd_int(h, addr):
    try:
        return memfuncs.ProcMemHandler.ReadInt(h, addr) & 0xFFFFFFFF
    except Exception:
        return 0

def rd_bool(h, addr):
    try:
        return bool(memfuncs.ProcMemHandler.ReadBool(h, addr))
    except Exception:
        return False

def rd_bytes(h, addr, n):
    try:
        return memfuncs.ProcMemHandler.ReadBytes(h, addr, n)
    except Exception:
        return b""

def read_cstr_utf8(h, addr, maxlen=64):
    if not addr:
        return ""
    bs = rd_bytes(h, addr, maxlen)
    if not bs:
        return ""
    try:
        return bs.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
    except Exception:
        return ""

def read_controller_name(h, ctrl, off):
    p = rd_ptr(h, ctrl + off.m_sSanitizedPlayerName)
    s = read_cstr_utf8(h, p, 64) if p else ""
    if s:
        return s
    return read_cstr_utf8(h, ctrl + off.m_sSanitizedPlayerName, 64) or "UNKNOWN"

# ---------- resolvers ----------
def ent_by_index_112(h, entlist_ptr, i):
    entry2 = rd_ptr(h, entlist_ptr + 0x8 * (i >> 9) + 0x10)
    if not entry2:
        return 0
    e = rd_ptr(h, entry2 + 112 * (i & 0x1FF))
    return e if is_valid_ptr(e) else 0

def handle_to_ent_stride(h, entlist_ptr, handle, stride):
    h32 = handle & 0xFFFFFFFF
    if h32 == 0 or h32 == 0xFFFFFFFF:
        return 0
    bucket = (h32 & 0x7FFF) >> 9
    idx    = (h32 & 0x1FF)
    entry2 = rd_ptr(h, entlist_ptr + 0x8 * bucket + 0x10)
    if not entry2:
        return 0
    e = rd_ptr(h, entry2 + stride * idx)
    return e if is_valid_ptr(e) else 0

def handle_to_ent_120(h, entlist_ptr, handle):
    return handle_to_ent_stride(h, entlist_ptr, handle, 120)

def handle_to_ent_112(h, entlist_ptr, handle):
    return handle_to_ent_stride(h, entlist_ptr, handle, 112)

def handle_to_ent_adaptive(h, entlist_ptr, handle):
    e = handle_to_ent_120(h, entlist_ptr, handle)
    if e:
        return e, 120
    e = handle_to_ent_112(h, entlist_ptr, handle)
    if e:
        return e, 112
    return 0, 0

def is_probably_pawn(h, ent_ptr, off):
    if not ent_ptr:
        return False
    cam = rd_ptr(h, ent_ptr + off.m_pCameraServices)
    if cam:
        return True
    obs = rd_ptr(h, ent_ptr + off.m_pObserverServices)
    return bool(obs)

# ---------- life/death ----------
def is_dead(h, pawn, off):
    if not pawn:
        return False
    life_off = getattr(off, "m_lifeState", 0)
    if life_off:
        life = rd_int(h, pawn + life_off)
        if life not in (0, 0xFFFFFFFF) and life != 0:
            return True
    hp_off = getattr(off, "m_iHealth", 0)
    if hp_off:
        hp = rd_int(h, pawn + hp_off)
        return hp <= 0
    return False

# ---------- strong local resolver ----------
def resolve_local_pawn(h, client, off, entlist_ptr):
    steps = []

    # A) via LocalPlayerController -> m_hPlayerPawn
    local_ctrl = rd_ptr(h, client + off.dwLocalPlayerController)
    steps.append(f"local_ctrl={fmtp(local_ctrl)}")
    if local_ctrl:
        hLocalPawn = rd_int(h, local_ctrl + off.m_hPlayerPawn)
        lp1, s1 = handle_to_ent_adaptive(h, entlist_ptr, hLocalPawn)
        steps.append(f"A) hLocalPawn=0x{hLocalPawn:08X} -> ent={fmtp(lp1)}/stride={s1}")
        if is_valid_ptr(lp1) and is_probably_pawn(h, lp1, off):
            return lp1, "A", steps

    # B) dwLocalPlayerPawn as POINTER
    lp2 = rd_ptr(h, client + off.dwLocalPlayerPawn)
    steps.append(f"B) dwLocalPlayerPawn(ptr)={fmtp(lp2)}")
    if is_valid_ptr(lp2) and is_probably_pawn(h, lp2, off):
        return lp2, "B(ptr)", steps

    # C) dwLocalPlayerPawn as HANDLE → entity
    hLocalPawn2 = rd_int(h, client + off.dwLocalPlayerPawn)
    lp3, s3 = handle_to_ent_adaptive(h, entlist_ptr, hLocalPawn2)
    steps.append(f"C) dwLocalPlayerPawn(handle)=0x{hLocalPawn2:08X} -> ent={fmtp(lp3)}/stride={s3}")
    if is_valid_ptr(lp3) and is_probably_pawn(h, lp3, off):
        return lp3, "C(handle)", steps

    # D) enumerate controllers (idx=112) to find exact local controller and reuse m_hPlayerPawn
    if local_ctrl:
        for i in range(1, 64):
            ctrl_i = ent_by_index_112(h, entlist_ptr, i)
            if ctrl_i == local_ctrl:
                hLP = rd_int(h, ctrl_i + off.m_hPlayerPawn)
                lp4, s4 = handle_to_ent_adaptive(h, entlist_ptr, hLP)
                steps.append(f"D) ctrl_match idx={i} hLP=0x{hLP:08X} -> ent={fmtp(lp4)}/stride={s4}")
                if is_valid_ptr(lp4) and is_probably_pawn(h, lp4, off):
                    return lp4, "D(ctrl-match)", steps

    return 0, "FAIL", steps

# ---------- main thread ----------
def SpectatorThreadFunction(Options, Offsets, Runtime):
    connector = ProcessConnector("cs2.exe", modules=["client.dll"])

    # Set log level from options
    try:
        set_spec_log_level(int(Options.get("SpectatorLogLevel", 0)))
    except Exception:
        set_spec_log_level(0)

    off = Offsets.offset
    _log(1, "[spectator] thread started (stable + handle-match + ctrl→pawn fallback).")
    try:
        _log(2, f"[spectator] dwLocalPlayerPawn={fmtp(off.dwLocalPlayerPawn)}, dwLocalPlayerController={fmtp(off.dwLocalPlayerController)}")
        _log(2, f"[spectator] dwEntityList={fmtp(off.dwEntityList)}")
        _log(2, f"[spectator] m_hPlayerPawn={fmtp(off.m_hPlayerPawn)}, m_hObserverPawn={fmtp(off.m_hObserverPawn)}")
        _log(2, f"[spectator] m_pObserverServices={fmtp(off.m_pObserverServices)}, m_iObserverMode={fmtp(off.m_iObserverMode)}, m_hObserverTarget={fmtp(off.m_hObserverTarget)}")
        _log(2, f"[spectator] m_pCameraServices={fmtp(off.m_pCameraServices)}, CPlayer_CameraServices::m_hViewEntity={fmtp(off.m_hViewEntity)}")
        _log(2, f"[spectator] name_field={fmtp(off.m_sSanitizedPlayerName)}")
    except Exception:
        pass

    try:
        allow_fixed = bool(Options.get("SpectatorAllowFixed", True))
    except Exception:
        allow_fixed = True
    ALLOWED_MODES = {OBS_MODE_IN_EYE, OBS_MODE_CHASE, OBS_MODE_FREEZECAM} | ({OBS_MODE_FIXED} if allow_fixed else set())

    last_sig = None
    last_local_print = 0
    last_local_tuple = (0, "")

    while True:
        try:
            hproc = connector.ensure_process()
            client = connector.ensure_module("client.dll")

            # Respect GUI toggle; keep CPU quiet when disabled
            try:
                if not bool(Options.get("EnableShowSpectators", False)):
                    Runtime.spectators = []
                    time.sleep(SCAN_INTERVAL_SEC)
                    continue
            except Exception:
                pass

            entlist_ptr = rd_ptr(hproc, client + off.dwEntityList)
            if not entlist_ptr:
                Runtime.spectators = []
                time.sleep(SCAN_INTERVAL_SEC)
                continue

            # --- detect match restart / waiting state and clear list
            game_rules = rd_ptr(hproc, client + getattr(off, "dwGameRules", 0))
            if game_rules:
                match_waiting = False
                match_restart = False
                mb_wait_off = getattr(off, "m_bMatchWaitingForResume", 0)
                mb_restart_off = getattr(off, "m_bGameRestart", 0)
                if mb_wait_off:
                    match_waiting = rd_bool(hproc, game_rules + mb_wait_off)
                if mb_restart_off:
                    match_restart = rd_bool(hproc, game_rules + mb_restart_off)
                if match_waiting or match_restart:
                    Runtime.spectators = []
                    time.sleep(SCAN_INTERVAL_SEC)
                    continue

            # strong local pawn resolution (throttled log)
            local_pawn, route, steps = resolve_local_pawn(hproc, client, off, entlist_ptr)

            # local handle index for index-compare
            local_ctrl_ptr = rd_ptr(hproc, client + off.dwLocalPlayerController)
            local_hpawn_handle = rd_int(hproc, local_ctrl_ptr + off.m_hPlayerPawn) if local_ctrl_ptr else 0
            local_handle_idx = (local_hpawn_handle & 0x7FFF) if local_hpawn_handle not in (0, 0xFFFFFFFF) else 0

            now = time.time()
            local_tuple = (local_pawn, route)
            if local_tuple != last_local_tuple or now - last_local_print > 3.0:
                if _SPEC_LOG_LEVEL >= 2:
                    _log(2, f"[spectator:local] route={route} pawn={fmtp(local_pawn)} | " + " | ".join(steps))
                    _log(2, f"[spectator:local] hLocalPawn=0x{local_hpawn_handle:08X} idx={local_handle_idx}")
                last_local_tuple = local_tuple
                last_local_print = now

            if not is_valid_ptr(local_pawn):
                Runtime.spectators = []
                time.sleep(SCAN_INTERVAL_SEC)
                continue

            spectators = []
            debug_rows = [] if _SPEC_LOG_LEVEL >= 2 else None
            scanned = had_handles = resolved_obs = matched = 0

            for i in range(1, MAX_ENTITIES):
                ctrl = ent_by_index_112(hproc, entlist_ptr, i)
                if not ctrl:
                    continue
                if ctrl == local_ctrl_ptr:  
                    continue

                scanned += 1

                name     = read_controller_name(hproc, ctrl, off)
                hObsPawn = rd_int(hproc, ctrl + off.m_hObserverPawn)
                hPawn    = rd_int(hproc, ctrl + off.m_hPlayerPawn)

                if (hObsPawn in (0, 0xFFFFFFFF)) and (hPawn in (0, 0xFFFFFFFF)):
                    if debug_rows is not None:
                        debug_rows.append(f"[spectator:scan] idx={i} NO_HANDLES ctrl={fmtp(ctrl)} name='{name}'")
                    continue

                had_handles += 1

                # resolve observer pawn (prefer hObsPawn; fallback hPawn)
                observer_pawn = 0
                used_stride_obs = 0
                if hObsPawn not in (0, 0xFFFFFFFF):
                    observer_pawn, used_stride_obs = handle_to_ent_adaptive(hproc, entlist_ptr, hObsPawn)
                if not observer_pawn and hPawn not in (0, 0xFFFFFFFF):
                    observer_pawn, used_stride_obs = handle_to_ent_adaptive(hproc, entlist_ptr, hPawn)

                if observer_pawn:
                    resolved_obs += 1

                dead = is_dead(hproc, observer_pawn, off) if observer_pawn else False

                obs_services = rd_ptr(hproc, observer_pawn + off.m_pObserverServices) if observer_pawn else 0
                mode = rd_int(hproc, obs_services + off.m_iObserverMode) if obs_services else 0

                # --- PRIMARY: ObserverTarget
                target_ent = 0
                used_stride_target = 0
                hTarget = 0
                target_idx = 0
                via = "-"

                if obs_services:
                    hTarget = rd_int(hproc, obs_services + off.m_hObserverTarget)
                    if hTarget not in (0, 0xFFFFFFFF):
                        target_ent, used_stride_target = handle_to_ent_adaptive(hproc, entlist_ptr, hTarget)
                        target_idx = (hTarget & 0x7FFF)

                        orig_stride = used_stride_target
                        need_promote = (orig_stride == 112) or (target_ent and not is_probably_pawn(hproc, target_ent, off))
                        if target_ent and need_promote:
                            t_hPawn = rd_int(hproc, target_ent + off.m_hPlayerPawn)
                            if t_hPawn not in (0, 0xFFFFFFFF):
                                target_ent2, used_stride_target2 = handle_to_ent_adaptive(hproc, entlist_ptr, t_hPawn)
                                if target_ent2:
                                    target_ent = target_ent2
                                    used_stride_target = f"{orig_stride}->{used_stride_target2}"
                        if target_ent:
                            via = "TARGET"

                # --- SECONDARY: ViewEntity
                view_entity = 0
                used_stride_view = 0
                hView = 0
                view_idx = 0
                if not target_ent and observer_pawn:
                    cam_services = rd_ptr(hproc, observer_pawn + off.m_pCameraServices)
                    if cam_services:
                        hView = rd_int(hproc, cam_services + off.m_hViewEntity)
                        if hView not in (0, 0xFFFFFFFF):
                            view_entity, used_stride_view = handle_to_ent_adaptive(hproc, entlist_ptr, hView)
                            view_idx = (hView & 0x7FFF)
                            if view_entity:
                                via = "VIEW"

                match_by_handle = (
                    dead and local_handle_idx and
                    ((target_idx and target_idx == local_handle_idx) or (view_idx and view_idx == local_handle_idx))
                )
                match_by_ptr = (
                    dead and (
                        (target_ent and target_ent == local_pawn) or
                        (view_entity and view_entity == local_pawn)
                    )
                )
                is_local = match_by_handle or match_by_ptr

                if debug_rows is not None:
                    debug_rows.append(
                        f"[spectator:scan] idx={i} ctrl={fmtp(ctrl)} name='{name}' "
                        f"hPawn=0x{hPawn:08X} hObsPawn=0x{hObsPawn:08X} "
                        f"obsPawn={fmtp(observer_pawn)}/stride={used_stride_obs} mode={MODE_NAMES.get(mode, mode)} "
                        f"hTarget=0x{hTarget:08X}/idx={target_idx} target={fmtp(target_ent)}/stride={used_stride_target} "
                        f"hView=0x{hView:08X}/idx={view_idx} view={fmtp(view_entity)}/stride={used_stride_view} "
                        f"dead={dead} local={fmtp(local_pawn)} local_idx={local_handle_idx} via={via} match={int(is_local)}"
                    )

                if is_local and (mode in ALLOWED_MODES):
                    matched += 1
                    spectators.append({
                        "pawn": observer_pawn,
                        "mode": mode,
                        "mode_name": MODE_NAMES.get(mode, f"MODE_{mode}"),
                        "name": name or "UNKNOWN",
                        "via": via
                    })

            Runtime.spectators = spectators

            sig = tuple(sorted((s["name"], s["pawn"], s["mode"]) for s in spectators))
            if sig != last_sig:
                if _SPEC_LOG_LEVEL >= 1:
                    if spectators:
                        names = ", ".join(s.get("name", "UNKNOWN") for s in spectators)
                        _log(1, f"[spectator] {len(spectators)} spectator(s): {names}")
                    else:
                        _log(1, "[spectator] no spectators")
                if _SPEC_LOG_LEVEL >= 2:
                    _log(2, f"[spectator:stat] scanned={scanned} had_handles={had_handles} resolved_pawn={resolved_obs} matched={matched}")
                    if debug_rows is not None:
                        for row in debug_rows:
                            _log(2, row)
                last_sig = sig

            time.sleep(SCAN_INTERVAL_SEC)

        except Exception as e:
            try:
                Runtime.spectators = []
            except Exception:
                pass
            logutil.debug(f"[spectator] exception: {e}")
            connector.invalidate()
            time.sleep(0.5)
        finally:
            # ensure list is cleared if thread exits
            try:
                current = locals().get("spectators")
                if not current:
                    Runtime.spectators = []
            except Exception:
                Runtime.spectators = []


def render_spectator_block(
    pme,
    spectators,
    enabled=True,
    screen_size=None,
    font_path=None,
    font_handle=None,
    font_size=16,
    font_id=None
):

    try:
        if not enabled or not spectators:
            return

        if not font_path:
            base_dir = os.path.dirname(__file__)
            repo_dir = os.path.abspath(os.path.join(base_dir, ".."))
            font_path = fontpaths.locate_font(anchors=[base_dir, repo_dir])

        font_handle = font_handle or init_spec_font(pme, font_path=font_path, font_size=font_size)

        # ----- screen size
        sw = sh = 0
        if isinstance(screen_size, (tuple, list)) and len(screen_size) >= 2:
            sw, sh = int(screen_size[0]), int(screen_size[1])
        else:
            try:
                sw, sh = pme.get_screen_size()
            except Exception:
                sw, sh = 1920, 1080

        # ----- collect display names (keep Unicode if font supports it)
        names = []
        max_label_width = 0
        for s in spectators:
            raw_name = (s.get("name") or "UNKNOWN").strip()
            if font_handle:
                safe_name = raw_name
            else:
                try:
                    raw_name.encode("ascii")
                    safe_name = raw_name
                except Exception:
                    safe_name = "".join(ch if ord(ch) < 128 else "?" for ch in raw_name)

            names.append(safe_name)

            try:
                width_candidate = pme.measure_text(safe_name, 15)
            except Exception:
                width_candidate = len(safe_name) * 8
            max_label_width = max(max_label_width, width_candidate)

        if not names:
            return

        # ----- layout (compact card)
        pad_x = 14
        pad_y = 12
        title_size = 16
        name_size = 15
        row_gap = 8
        radius = 9

        content_height = len(names) * name_size + max(0, len(names) - 1) * row_gap
        block_w = max(220, pad_x * 2 + max_label_width + 10)
        block_h = pad_y + title_size + 10 + content_height + pad_y

        x = sw - block_w - 24
        y = sh // 2 - block_h // 2

        # ----- colors via pyMeow (aligned with GUI palette)
        col_shadow = pme.fade_color(pme.get_color("#000000"), 0.28)
        col_border = pme.fade_color(pme.get_color("#588bc4"), 0.45)
        col_bg     = pme.fade_color(pme.get_color("#101726"), 0.92)
        col_accent = pme.fade_color(pme.get_color("#588bc4"), 0.85)
        col_title  = pme.get_color("#f0f4ff")
        col_name   = pme.get_color("#e3e9f7")

        # choose drawer depending on font availability
        def DT(txt, dx, dy, size, col):
            if font_id is not None and hasattr(pme, "draw_font"):
                try:
                    pme.draw_font(
                        fontId=font_id,
                        text=str(txt),
                        posX=int(round(dx)),
                        posY=int(round(dy)),
                        fontSize=int(round(size)),
                        spacing=0,
                        tint=col
                    )
                    return
                except Exception:
                    pass
            if font_handle:
                try:
                    pme.draw_text(txt, dx, dy, fontSize=size, color=col, font=font_handle)
                    return
                except TypeError:
                    pass
                except Exception:
                    pass
                try:
                    with _FontScope(pme, font_handle):
                        pme.draw_text(txt, dx, dy, fontSize=size, color=col)
                        return
                except Exception:
                    pass
            _draw_text_styled(pme, txt, dx, dy, size, col)

        # ----- draw
        with _FontScope(pme, font_handle):
            pme.draw_rectangle(x + 3, y + 5, block_w, block_h, col_shadow)
            pme.draw_rectangle(x, y, block_w, block_h, col_border)

            inner_x = x + 1
            inner_y = y + 1
            inner_w = block_w - 2
            inner_h = block_h - 2
            inner_radius = max(2, radius - 1)
            pme.draw_rectangle(inner_x, inner_y, inner_w, inner_h, col_bg)
            pme.draw_rectangle(inner_x, inner_y, 3, inner_h, col_accent)

            title_y = inner_y + pad_y
            DT(f"Spectators ({len(names)})", inner_x + pad_x, title_y, title_size, col_title)

            cy = title_y + title_size + 8
            for name in names:
                DT(name, inner_x + pad_x, cy, name_size, col_name)
                cy += name_size + row_gap

    except Exception as e:
        try:
            _log(1, f"[overlay/spec] draw error: {e}")
        except Exception:
            pass
