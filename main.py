import globals
from functions import memfuncs
from functions import logutil

from features import aimbot
from features import rcs
from features import esp
from features import bombtimer
from features import fovchanger
from features import antiflash
from features import triggerbot
from features import bhop
from features import discodrpc
from features import spectator

from GUI import gui_mainloop
from GUI import gui_util

import multiprocessing
import time

import serial
import serial.tools.list_ports

import win32con, win32process, win32api
import keyboard, os, json

from functions.process_watcher import ProcessConnector

keyboard.add_hotkey("end", callback=lambda: os._exit(0))
keyboard.add_hotkey("insert", callback=lambda: gui_util.hide_dpg())
keyboard.add_hotkey("home", callback=lambda: gui_util.streamproof_toggle())


class ManagedConfig:
    def __init__(self, managed_dict, save_function):
        self._dict = managed_dict
        self._save_function = save_function
    def update(self, *args, **kwargs):
        self._dict.update(*args, **kwargs)
        self._save_function(self._dict)
    def __setitem__(self, key, value):
        self._dict[key] = value
        self._save_function(self._dict)
    def __getitem__(self, key): return self._dict[key]
    def __delitem__(self, key):
        del self._dict[key]
        self._save_function(self._dict)
    def __contains__(self, key): return key in self._dict
    def get(self, key, default=None): return self._dict.get(key, default)
    def items(self): return self._dict.items()
    def keys(self): return self._dict.keys()
    def values(self): return self._dict.values()
    def __repr__(self): return repr(self._dict)


def SaveConfig(options):
    with open(globals.SAVE_FILE, 'w') as fp:
        json.dump(dict(options), fp, indent=4)

def LoadConfig():
    if not os.path.exists(globals.SAVE_FILE):
        with open(globals.SAVE_FILE, "w") as fp:
            json.dump(globals.CHEAT_SETTINGS, fp, indent=4)
    else:
        with open(globals.SAVE_FILE, "r") as fp:
            globals.CHEAT_SETTINGS = json.load(fp)




if __name__ == "__main__":

    print(" _   _ ______ _____   ____  _   _ \n| \\ | |  ____|  __ \\ / __ \\| \\ | |\n|  \\| | |__  | |__) | |  | |  \\| |\n| . ` |  __| |  _  /| |  | | . ` |\n| |\\  | |____| | \\ \\| |__| | |\\  |\n|_| \\_|______|_|  \\_\\\\____/|_| \\_|\n\n             - NERON v1.0\n             - developed by khorami.dev\n             - https://github.com/SadraKhorami/cs2_neron_external")

    win32process.SetPriorityClass(
        win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, win32api.GetCurrentProcessId()),
        win32process.HIGH_PRIORITY_CLASS
    )
    multiprocessing.freeze_support()

    COM_PORT = None
    use_arduino = "N"
    if use_arduino.upper() == "Y":
        for index, port in enumerate([p.device for p in serial.tools.list_ports.comports()]):
            print(f"[{index}] {port}")
        COM_PORT = input("Select COM Port: ")
        ARDUINO_HANDLE = serial.Serial([p.device for p in serial.tools.list_ports.comports()][int(COM_PORT)], 9600)
    else:
        ARDUINO_HANDLE = None

    # Process & module
    connector = ProcessConnector("cs2.exe", modules=["client.dll"])
    ProcessObject = connector.ensure_process()
    ClientModuleAddress = connector.ensure_module("client.dll")

    # Config
    LoadConfig()
    Manager = multiprocessing.Manager()
    SharedOptions_M = Manager.dict(globals.CHEAT_SETTINGS)
    SharedOptions = ManagedConfig(SharedOptions_M, save_function=SaveConfig)

    # Offsets
    SharedOffsets = Manager.Namespace()
    SharedOffsets.offset = globals.GAME_OFFSETS

    SharedRuntime = Manager.Namespace()
    SharedRuntime.spectators = []  # populated live by features/spectator.py
    SharedOptions["EnableShowSpectators"] = True
    DEBUG_FAKE_SPECS = False
    if DEBUG_FAKE_SPECS and not SharedRuntime.spectators and SharedOptions.get("EnableShowSpectators", False):
        SharedRuntime.spectators = [{"name": "Tired", "mode_name": "FREEZECAM", "pawn": 0xDEAD}]

    GUI_proc = multiprocessing.Process(target=gui_mainloop.run_gui, args=(SharedOptions, SharedRuntime,))
    GUI_proc.start()

    # Overlay
    esp.pme.overlay_init(title="ESP-Overlay")
    fps = esp.pme.get_monitor_refresh_rate()
    esp.pme.set_fps(fps)

    # FOV changer
    FOV_proc = multiprocessing.Process(target=fovchanger.FovChangerThreadFunction, args=(SharedOptions, SharedOffsets,))
    FOV_proc.daemon = True
    FOV_proc.start()

    # Anti-Flash (separate worker)
    AntiFlash_proc = multiprocessing.Process(target=antiflash.AntiFlashThreadFunction, args=(SharedOptions, SharedOffsets,))
    AntiFlash_proc.daemon = True
    AntiFlash_proc.start()

    # Triggerbot (separate worker)
    Trigger_proc = multiprocessing.Process(target=triggerbot.TriggerbotThreadFunction, args=(SharedOptions, SharedOffsets,))
    Trigger_proc.daemon = True
    Trigger_proc.start()

    # Bhop (separate thread to keep sleeps off overlay thread)
    Bhop_proc = multiprocessing.Process(target=bhop.BhopThreadFunction, args=(SharedOptions, SharedOffsets,))
    Bhop_proc.daemon = True
    Bhop_proc.start()

    # Bomb timer
    SharedBombState = Manager.Namespace()
    SharedBombState.bombPlanted = False
    SharedBombState.bombTimeLeft = -1
    Bomb_proc = multiprocessing.Process(target=bombtimer.BombTimerThread, args=(SharedBombState, SharedOffsets,))
    Bomb_proc.daemon = True
    Bomb_proc.start()

    # Discord RPC
    discord_rpc_proc = multiprocessing.Process(target=discodrpc.DiscordRpcThread, args=(SharedOptions,))
    discord_rpc_proc.daemon = True
    discord_rpc_proc.start()

    # Spectator monitor
    Spectator_proc = multiprocessing.Process(
        target=spectator.SpectatorThreadFunction,
        args=(SharedOptions, SharedOffsets, SharedRuntime,)
    )
    Spectator_proc.daemon = True
    Spectator_proc.start()
    logutil.debug("[main] spectator monitor: started")

    overlay_logged_once = False
    while esp.pme.overlay_loop():
        try:
            ProcessObject = connector.ensure_process()
            ClientModuleAddress = connector.ensure_module("client.dll")
        except Exception:
            connector.invalidate()
            time.sleep(0.5)
            continue

        if not overlay_logged_once:
            logutil.debug("[main] overlay loop entered; Spec List will be drawn from features/esp.py.")
            logutil.debug("[main] rendering Spec List on the game frame (inside ESP begin/end drawing)")
            overlay_logged_once = True

        try:
            esp.ESP_Update(ProcessObject, ClientModuleAddress, SharedOptions, SharedOffsets, SharedBombState, SharedRuntime)

            # NOTE: Spec List is rendered inside features/esp.py frame (between begin_drawing/end_drawing).
            # Do not draw it here; this runs outside the active frame. Just touch the runtime list
            # so we know it's alive; esp.ESP_Update will render it.
            try:
                _ = len(SharedRuntime.spectators)
            except Exception:
                pass

            if SharedOptions["EnableAimbot"] and win32api.GetAsyncKeyState(SharedOptions["AimbotKey"]) & 0x8000:
                aimbot.Aimbot_Update(ProcessObject, ClientModuleAddress, SharedOffsets, SharedOptions, ARDUINO_HANDLE=ARDUINO_HANDLE)

            # bhop and triggerbot/anti-flash are now handled in their own threads
            # to avoid sleeps inside the overlay frame
            rcs.RecoilControl_Update(ProcessObject, ClientModuleAddress, SharedOffsets, SharedOptions, ARDUINO_HANDLE=ARDUINO_HANDLE)
        except Exception:
            connector.invalidate()
            time.sleep(0.01)
            continue
