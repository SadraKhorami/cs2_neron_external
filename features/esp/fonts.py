import os
from functions import fontpaths
from functions import logutil
import pyMeow as pme

_OVERLAY_FONT_PATH = None
_OVERLAY_FONT_PROBED = False
_OVERLAY_FONT_CACHE = {}
_OVERLAY_FONT_WARNED = set()
_RAYLIB_FONT_ID = None
_RAYLIB_FONT_ATTEMPTED = False
_RAYLIB_FONT_TARGET_ID = 7


def _find_overlay_font():
    global _OVERLAY_FONT_PATH, _OVERLAY_FONT_PROBED
    if _OVERLAY_FONT_PROBED:
        return _OVERLAY_FONT_PATH
    base_dir = os.path.dirname(__file__)
    repo_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
    path = fontpaths.locate_font(anchors=[base_dir, repo_dir])
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
    if path:
        logutil.debug(f"[esp] overlay font found: {path}")
    else:
        logutil.debug("[esp] overlay font not found; using default")
    return path


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
        logutil.debug(f"[esp] raylib font loaded: {font_path}")
    except Exception:
        _RAYLIB_FONT_ID = None
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
        from features import spectator
        handle = spectator.init_spec_font(pme, font_path=font_path, font_size=key)
    except Exception:
        handle = None
    _OVERLAY_FONT_CACHE[key] = handle
    if handle is None and key not in _OVERLAY_FONT_WARNED:
        _OVERLAY_FONT_WARNED.add(key)
    return handle


def draw_text(text, x, y, *, size, color):
    try:
        col = color if isinstance(color, tuple) else pme.get_color(color)
    except Exception:
        col = color
    xi = int(round(x)); yi = int(round(y)); sz = max(10, int(round(size)))
    font_id = _ensure_raylib_font()
    if font_id is not None:
        try:
            pme.draw_font(fontId=font_id, text=str(text), posX=xi, posY=yi, fontSize=sz, spacing=0, tint=col)
            return
        except Exception:
            pass
    font_handle = _get_overlay_font_handle(sz)
    if font_handle:
        try:
            pme.draw_text(text, xi, yi, fontSize=sz, color=col, font=font_handle)
            return
        except Exception:
            pass
    try:
        pme.draw_text(text, xi, yi, fontSize=sz, color=col)
    except Exception:
        pass

