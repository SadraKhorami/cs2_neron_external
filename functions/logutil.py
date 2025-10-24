import os
import sys
from typing import Optional


def _is_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    value = value.strip().lower()
    return value not in ("", "0", "false", "no", "off")


_DEBUG_ENABLED = _is_truthy(os.getenv("NERON_DEBUG"))


def is_debug_enabled() -> bool:
    return _DEBUG_ENABLED


def debug(msg: str) -> None:
    if _DEBUG_ENABLED:
        try:
            print(msg)
        except Exception:
            pass


def info(msg: str) -> None:
    if _DEBUG_ENABLED:
        try:
            print(msg)
        except Exception:
            pass


def warning(msg: str) -> None:
    if _DEBUG_ENABLED:
        try:
            print(msg, file=sys.stderr)
        except Exception:
            pass


def error(msg: str) -> None:
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass
