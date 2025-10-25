from functions import memfuncs
from functions import logutil
from functions.process_watcher import ProcessConnector
import time


def AntiFlashThreadFunction(Options, Offsets):
    connector = ProcessConnector("cs2.exe", modules=["client.dll"])

    last_value = None

    while True:
        try:
            process = connector.ensure_process()
            client = connector.ensure_module("client.dll")

            local_pawn = memfuncs.ProcMemHandler.ReadPointer(process, client + Offsets.offset.dwLocalPlayerPawn)
            if not local_pawn:
                time.sleep(0.005)
                continue

            desired = 0.0 if Options.get("EnableAntiFlashbang", False) else 255.0
            if desired != last_value:
                try:
                    memfuncs.ProcMemHandler.WriteFloat(
                        process,
                        local_pawn + Offsets.offset.m_flFlashMaxAlpha,
                        desired,
                    )
                    last_value = desired
                except Exception:
                    pass

            time.sleep(0.002)

        except Exception as exc:
            logutil.debug(f"[antiflash] loop exception: {exc}")
            connector.invalidate()
            time.sleep(0.01)

