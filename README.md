# NERON

External enhancement suite for Counter-Strike 2 featuring ESP overlay, aimbot, triggerbot, recoil control, FOV changer, bhop assist, spectator monitor.

> ⚠️ External cheats can violate Valve policies. Use at your own risk.

## Highlights
- ESP with boxes, skeletons, health, distance, bomb timer, spectator list.
- Aimbot with smoothing, prediction, recoil handoff, team/visibility checks, optional Arduino output.
- Triggerbot with anti-flash, standalone recoil control system, stream-proof toggle.
- DearPyGui UI with live configuration, stored automatically in `settings.json`.

## Gallery
<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1279421698571112542/1431076949828046980/864shots_so.png?ex=68fc19c4&is=68fac844&hm=89910bb9bdac4f5a406e4465bb5e01255ab4dd2092983bfbd7a70ad76997d5f7&" alt="NERON ESP Overlay preview" width="720">
</p>
<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1279421698571112542/1431074714909937785/telegram-cloud-document-4-6042136322448039029.jpg?ex=68fc17b0&is=68fac630&hm=63c8c4c837da967bd4d9d90da2af9983e7b01601a190599b2582b36f1dadfcb1&" alt="NERON DearPyGui control panel preview" width="720">
</p>

## Quick Start
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyMeow
```
1. Launch CS2 and join a session.
2. Run `python main.py` (recommended with admin privileges).
3. NERON waits for `cs2.exe`/`client.dll`, then spawns the GUI, overlay, and worker threads.

## Hotkeys
- `End` — terminate NERON.
- `Insert` — toggle GUI visibility.
- `Home` — toggle stream-proof mode for GUI and ESP overlay.

Additional keybinds (aimbot, triggerbot, etc.) are configurable inside the GUI. Custom UI fonts live in `fonts/inter-semibold.ttf`.

Offsets are fetched at runtime from the CS2 dumper repo; if the request fails, provide manual dumps under `output/`. Enable verbose logging with `NERON_DEBUG=1`.

## License & Credits
Crafted by [SadraKhorami](https://github.com/SadraKhorami). Visit the official site: [khorami.dev](https://khorami.dev). If this project helps you, please star the repository to support ongoing work.
