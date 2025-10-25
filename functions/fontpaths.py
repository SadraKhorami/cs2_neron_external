import os
from typing import Iterable, List, Optional

DEFAULT_FONT_FILENAME = "inter-semibold.ttf"


def _unique_paths(paths: Iterable[str]) -> List[str]:
    seen = set()
    unique = []
    for path in paths:
        if not path:
            continue
        norm = os.path.normpath(path)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


def font_candidates(
    font_filename: str = DEFAULT_FONT_FILENAME,
    anchors: Optional[Iterable[str]] = None,
) -> List[str]:
    anchors = list(anchors or [])
    candidates = []

    for anchor in anchors:
        if not anchor:
            continue
        anchor = os.path.abspath(anchor)
        candidates.extend(
            [
                os.path.join(anchor, font_filename),
                os.path.join(anchor, "fonts", font_filename),
            ]
        )

    cwd = os.getcwd()
    candidates.extend(
        [
            os.path.join(cwd, "fonts", font_filename),
            os.path.join(cwd, font_filename),
        ]
    )

    return _unique_paths(candidates)


def locate_font(
    font_filename: str = DEFAULT_FONT_FILENAME,
    anchors: Optional[Iterable[str]] = None,
) -> Optional[str]:
    for cand in font_candidates(font_filename, anchors):
        if os.path.exists(cand):
            return cand
    return None
