from functions import memfuncs
from functions import logutil
from functions.process_watcher import ProcessConnector
import time

def BombTimerThread(SharedBombState, SharedOffsets):
    connector = ProcessConnector("cs2.exe", modules=["client.dll"])
    TOTAL_TIME = 40
    SharedBombState.bombTimeTotal = TOTAL_TIME
    while True:
        try:
            processHandle = connector.ensure_process()
            clientBaseAddress = connector.ensure_module("client.dll")

            gameRule = memfuncs.ProcMemHandler.ReadPointer(processHandle, clientBaseAddress + SharedOffsets.offset.dwGameRules)
            if not gameRule:
                SharedBombState.bombPlanted = False
                SharedBombState.bombTimeLeft = -1
                SharedBombState.bombTimeTotal = TOTAL_TIME
                time.sleep(0.1)
                continue

            if not memfuncs.ProcMemHandler.ReadBool(processHandle, gameRule + SharedOffsets.offset.m_bBombPlanted):
                SharedBombState.bombPlanted = False
                SharedBombState.bombTimeLeft = -1
                SharedBombState.bombTimeTotal = TOTAL_TIME
                time.sleep(0.1)
                continue

            SharedBombState.bombPlanted = True
            SharedBombState.bombTimeTotal = TOTAL_TIME
            for elapsed in range(TOTAL_TIME):
                if not memfuncs.ProcMemHandler.ReadBool(processHandle, gameRule + SharedOffsets.offset.m_bBombPlanted):
                    SharedBombState.bombPlanted = False
                    SharedBombState.bombTimeLeft = -1
                    break

                SharedBombState.bombTimeLeft = TOTAL_TIME - elapsed
                time.sleep(1)
            else:
                # loop completed without break; bomb still active so reset state afterwards
                SharedBombState.bombPlanted = False
                SharedBombState.bombTimeLeft = -1
                SharedBombState.bombTimeTotal = TOTAL_TIME

        except Exception as exc:
            logutil.debug(f"[bombtimer] loop exception: {exc}")
            SharedBombState.bombPlanted = False
            SharedBombState.bombTimeLeft = -1
            SharedBombState.bombTimeTotal = TOTAL_TIME
            connector.invalidate()
            time.sleep(1)
