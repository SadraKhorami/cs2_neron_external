import threading
import time
from typing import Dict, Iterable, Optional

import pymem
from pymem.process import module_from_name

from functions import logutil


class ProcessConnector:
    def __init__(
        self,
        process_name: str,
        modules: Optional[Iterable[str]] = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.process_name = process_name
        self.poll_interval = max(0.1, float(poll_interval))
        self._lock = threading.Lock()
        self._proc: Optional[pymem.Pymem] = None
        self._module_cache: Dict[str, int] = {}
        self._module_whitelist = {m.lower() for m in modules} if modules else set()

    def _wait_for_process(self) -> pymem.Pymem:
        while True:
            try:
                proc = pymem.Pymem(self.process_name)
                return proc
            except Exception:
                logutil.debug(f"[proc] waiting for process {self.process_name} ...")
                time.sleep(self.poll_interval)

    def _wait_for_module(self, module_name: str) -> int:
        module_key = module_name.lower()
        while True:
            proc = self.ensure_process()
            try:
                module = module_from_name(proc.process_handle, module_name)
                if module:
                    return module.lpBaseOfDll
            except Exception:
                self.invalidate()
                continue

            logutil.debug(f"[proc] waiting for module {module_name} ...")
            time.sleep(self.poll_interval)

    def ensure_process(self) -> pymem.Pymem:
        with self._lock:
            if self._proc is not None:
                try:
                    _ = self._proc.process_handle
                    return self._proc
                except Exception:
                    self._proc = None
                    self._module_cache.clear()

            self._proc = self._wait_for_process()
            self._module_cache.clear()
            return self._proc

    def ensure_module(self, module_name: str) -> int:
        key = module_name.lower()
        with self._lock:
            cached = self._module_cache.get(key)
            if cached:
                return cached

        base = self._wait_for_module(module_name)
        with self._lock:
            self._module_cache[key] = base
        return base

    def invalidate(self) -> None:
        with self._lock:
            self._proc = None
            self._module_cache.clear()

    def process_handle(self) -> pymem.Pymem:
        return self.ensure_process()

    def module_base(self, module_name: str) -> int:
        return self.ensure_module(module_name)
