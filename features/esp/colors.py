import pyMeow as pme

_COLOR_CACHE = {}


def resolve_color(color):
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


def clamp(v, lo, hi):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color_hex(hex_a: str, hex_b: str, t: float) -> str:
    def to_rgb(h):
        h = h.lstrip('#')
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    def to_hex(rgb):
        r, g, b = [int(clamp(x, 0, 255)) for x in rgb]
        return f"#{r:02X}{g:02X}{b:02X}"
    ra, ga, ba = to_rgb(hex_a)
    rb, gb, bb = to_rgb(hex_b)
    r = lerp(ra, rb, t)
    g = lerp(ga, gb, t)
    b = lerp(ba, bb, t)
    return to_hex((r, g, b))


def health_color_hex(health: int) -> str:
    h = int(clamp(health, 0, 100))
    if h <= 50:
        t = h / 50.0
        return lerp_color_hex("#FF3B30", "#F59E0B", t)
    else:
        t = (h - 50) / 50.0
        return lerp_color_hex("#F59E0B", "#22C55E", t)

