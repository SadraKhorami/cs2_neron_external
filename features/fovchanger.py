from functions import memfuncs
from functions import gameinput
from functions import logutil
from functions.process_watcher import ProcessConnector
import win32api, win32gui
import time

def FovChangerThreadFunction(Options, Offsets):

	connector = ProcessConnector("cs2.exe", modules=["client.dll"])

	while True:
		try:
			processHandle = connector.ensure_process()
			clientBaseAddress = connector.ensure_module("client.dll")

			localPlayer = memfuncs.ProcMemHandler.ReadPointer(processHandle, clientBaseAddress + Offsets.offset.dwLocalPlayerPawn)
			if not localPlayer:
				time.sleep(0.01)
				continue

			cameraServices = memfuncs.ProcMemHandler.ReadPointer(processHandle, localPlayer + Offsets.offset.m_pCameraServices)
			if not cameraServices:
				time.sleep(0.01)
				continue

			flash_alpha = 0.0 if Options["EnableAntiFlashbang"] else 255.0
			memfuncs.ProcMemHandler.WriteFloat(
				processHandle,
				localPlayer + Offsets.offset.m_flFlashMaxAlpha,
				flash_alpha
			)

			if (win32gui.GetWindowText(win32gui.GetForegroundWindow()) == "Counter-Strike 2"
					and Options["EnableTriggerbot"]
					and (win32api.GetAsyncKeyState(Options["TriggerbotKey"]) or not Options["EnableTriggerbotKeyCheck"])):
				localPlayerID = memfuncs.ProcMemHandler.ReadInt(processHandle, localPlayer + Offsets.offset.m_iIDEntIndex)
				if localPlayerID > 0:
					entityList = memfuncs.ProcMemHandler.ReadPointer(processHandle, clientBaseAddress + Offsets.offset.dwEntityList)
					if not entityList:
						time.sleep(0.01)
						continue
					entityListEntry = memfuncs.ProcMemHandler.ReadPointer(processHandle, entityList + 0x8 * (localPlayerID >> 9) + 0x10)
					if not entityListEntry:
						time.sleep(0.01)
						continue
					TargetEntity = memfuncs.ProcMemHandler.ReadPointer(processHandle, entityListEntry + 112 * (localPlayerID & 0x1FF))
					if not TargetEntity:
						time.sleep(0.01)
						continue

					TargetEntityTeam = memfuncs.ProcMemHandler.ReadInt(processHandle, TargetEntity + Offsets.offset.m_iTeamNum)
					localPlayerTeam = memfuncs.ProcMemHandler.ReadInt(processHandle, localPlayer + Offsets.offset.m_iTeamNum)

					if not Options["EnableTriggerbotTeamCheck"] or TargetEntityTeam != localPlayerTeam:
						TargetEntityHP = memfuncs.ProcMemHandler.ReadInt(processHandle, TargetEntity + Offsets.offset.m_iHealth)
						if TargetEntityHP > 0 and not win32api.GetAsyncKeyState(0x01):
							gameinput.LeftClick()

		except Exception as exc:
			logutil.debug(f"[fovchanger] loop exception: {exc}")
			connector.invalidate()
			time.sleep(0.05)






















