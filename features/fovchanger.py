from functions import memfuncs
from functions import logutil
from functions.process_watcher import ProcessConnector
import time


def FovChangerThreadFunction(Options, Offsets):
    """Dedicated FOV changer. Writes only when EnableFovChanger is true and FOV changes."""
    connector = ProcessConnector("cs2.exe", modules=["client.dll"])

    last_fov_written = None

    def _clamp(v, lo, hi):
        try:
            return max(lo, min(hi, int(v)))
        except Exception:
            return lo

    while True:
        try:
            process = connector.ensure_process()
            client = connector.ensure_module("client.dll")

            if not Options.get("EnableFovChanger", False):
                last_fov_written = None
                time.sleep(0.01)
                continue

            local_pawn = memfuncs.ProcMemHandler.ReadPointer(process, client + Offsets.offset.dwLocalPlayerPawn)
            if not local_pawn:
                time.sleep(0.005)
                continue

            camera_services = memfuncs.ProcMemHandler.ReadPointer(process, local_pawn + Offsets.offset.m_pCameraServices)
            if not camera_services:
                time.sleep(0.005)
                continue

            desired_fov = _clamp(Options.get("FovChangeSize", 90), 60, 140)
            if desired_fov != last_fov_written:
                try:
                    memfuncs.ProcMemHandler.WriteInt(process, camera_services + Offsets.offset.m_iFOV, desired_fov)
                    last_fov_written = desired_fov
                except Exception:
                    pass

            time.sleep(0.003)

        except Exception as exc:
            logutil.debug(f"[fovchanger] loop exception: {exc}")
            connector.invalidate()
            time.sleep(0.01)





















