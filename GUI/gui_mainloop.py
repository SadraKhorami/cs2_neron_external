import dearpygui.dearpygui as dpg
from functions import logutil
import threading
import time
import win32api
import os

from functions import fontpaths

ROOT_TAG = "neron_root_window"

KeyNames = [
    "OFF","VK_LBUTTON","VK_RBUTTON","VK_CANCEL","VK_MBUTTON","VK_XBUTTON1","VK_XBUTTON2","Unknown",
    "VK_BACK","VK_TAB","Unknown","Unknown","VK_CLEAR","VK_RETURN","Unknown","Unknown","VK_SHIFT","VK_CONTROL","VK_MENU",
    "VK_PAUSE","VK_CAPITAL","VK_KANA","Unknown","VK_JUNJA","VK_FINAL","VK_KANJI","Unknown","VK_ESCAPE","VK_CONVERT",
    "VK_NONCONVERT","VK_ACCEPT","VK_MODECHANGE","VK_SPACE","VK_PRIOR","VK_NEXT","VK_END","VK_HOME","VK_LEFT","VK_UP",
    "VK_RIGHT","VK_DOWN","VK_SELECT","VK_PRINT","VK_EXECUTE","VK_SNAPSHOT","VK_INSERT","VK_DELETE","VK_HELP",
    "0","1","2","3","4","5","6","7","8","9",
    "Unknown","Unknown","Unknown","Unknown","Unknown","Unknown","Unknown",
    "A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
    "VK_LWIN","VK_RWIN","VK_APPS","Unknown","VK_SLEEP",
    "VK_NUMPAD0","VK_NUMPAD1","VK_NUMPAD2","VK_NUMPAD3","VK_NUMPAD4","VK_NUMPAD5","VK_NUMPAD6","VK_NUMPAD7","VK_NUMPAD8","VK_NUMPAD9",
    "VK_MULTIPLY","VK_ADD","VK_SEPARATOR","VK_SUBTRACT","VK_DECIMAL","VK_DIVIDE",
    "VK_F1","VK_F2","VK_F3","VK_F4","VK_F5","VK_F6","VK_F7","VK_F8","VK_F9","VK_F10","VK_F11","VK_F12",
    "VK_F13","VK_F14","VK_F15","VK_F16","VK_F17","VK_F18","VK_F19","VK_F20","VK_F21","VK_F22","VK_F23","VK_F24",
    "Unknown","Unknown","Unknown","Unknown","Unknown","Unknown","Unknown","Unknown",
    "VK_NUMLOCK","VK_SCROLL",
    "VK_OEM_NEC_EQUAL","VK_OEM_FJ_MASSHOU","VK_OEM_FJ_TOUROKU","VK_OEM_FJ_LOYA","VK_OEM_FJ_ROYA",
    "Unknown","Unknown","Unknown","Unknown","Unknown","Unknown","Unknown","Unknown","Unknown",
    "VK_LSHIFT","VK_RSHIFT","VK_LCONTROL","VK_RCONTROL","VK_LMENU","VK_RMENU"
]

class NERON_GUI:
    def __init__(self, config, runtime):
        self.runtime = runtime
        self.n = 0
        self.ui_dragging = False
        self.viewport_width = 900
        self.viewport_height = 650
        self.root_window = None
        self.config = config
        self.control_width = 250
        self.card_padding = 3
        self.palette = {
            "background": (9, 11, 15, 255),
            "child": (17, 20, 27, 255),
            "panel": (23, 27, 36, 255),
            "frame": (35, 41, 54, 255),
            "frame_hover": (66, 92, 126, 160),
            "frame_active": (88, 128, 174, 255),
            "accent": (88, 139, 196, 255),
            "accent_hover": (120, 166, 219, 255),
            "accent_soft": (60, 85, 115, 200),
            "separator": (54, 59, 73, 220),
            "text_muted": (157, 165, 182, 255),
            "text_subtle": (126, 134, 149, 255),
        }
        self.init_context()
        self.create_theme()
        self.load_ui_font()
        self.build_ui()
        self.add_event_handlers()

    def hex_to_rgb(self, hex_code):
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        r, g, b = [int(round(x)) for x in rgb[:3]]
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return '#{:02X}{:02X}{:02X}'.format(r, g, b)

    def _color_value_to_hex(self, value):
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            return None
        try:
            rgb = [float(v) for v in value[:3]]
        except (TypeError, ValueError):
            return None
        if max(rgb, default=0.0) <= 1.0:
            rgb = [v * 255.0 for v in rgb]
        return self.rgb_to_hex(rgb)

    def init_context(self):
        dpg.create_context()
        self.viewport = dpg.create_viewport(
            title="NERON",
            width=self.viewport_width,
            height=self.viewport_height,
            vsync=True,
            decorated=False,
            resizable=False,
            max_width=self.viewport_width,
            max_height=self.viewport_height
        )
        dpg.setup_dearpygui()

    def load_ui_font(self, path=None, size=16):
        """Load and bind the custom UI font. Tries multiple fallback paths."""
        self.ui_font = None
        candidates = []
        if path:
            candidates.append(path)
        base_dir = os.path.dirname(__file__)
        repo_dir = os.path.abspath(os.path.join(base_dir, ".."))
        font_name = "inter-semibold.ttf"
        candidates.extend(
            fontpaths.font_candidates(
                font_filename=font_name,
                anchors=[base_dir, repo_dir],
            )
        )
        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]
        try:
            with dpg.font_registry():
                for cand in candidates:
                    try:
                        if os.path.exists(cand):
                            self.ui_font = dpg.add_font(cand, size)
                            logutil.debug(f"[gui] UI font loaded: {cand} (size={size})")
                            break
                    except Exception as e:
                        logutil.debug(f"[gui] font load failed for {cand}: {e}")
                        continue
        except Exception as e:
            logutil.debug(f"[gui] font registry error: {e}")
            self.ui_font = None
        if self.ui_font:
            try:
                dpg.bind_font(self.ui_font)
            except Exception as e:
                logutil.debug(f"[gui] bind_font failed: {e}")
        else:
            logutil.debug("[gui] No custom font found; using DearPyGui default font.")

    def keybind_use(self, sender, app_data, user_data):
        key_id = user_data
        dpg.set_item_label(sender, "...")

        waiting = True
        delay_counter = 0

        def capture_key():
            nonlocal waiting, delay_counter
            while waiting:
                time.sleep(0.05)
                delay_counter += 1
                if delay_counter > 3:
                    for i in range(256):
                        if win32api.GetAsyncKeyState(i) & 0x8000:
                            key_name = self._key_label(i)
                            dpg.set_item_label(sender, key_name)
                            waiting = False
                            self._config_set(key_id, i)
                            return
        threading.Thread(target=capture_key, daemon=True).start()

    def _key_label(self, key_code):
        if 0 <= key_code < len(KeyNames):
            return KeyNames[key_code]
        return f"Unknown({key_code})"

    def _config_get(self, key, default=None):
        try:
            return self.config[key]
        except KeyError:
            pass
        except Exception:
            pass
        try:
            return self.config.get(key, default)
        except Exception:
            return default

    def _config_set(self, key, value):
        try:
            self.config.update({key: value})
        except Exception:
            try:
                self.config[key] = value
            except Exception as e:
                logutil.debug(f"[gui] config set failed for {key}: {e}")

    def create_theme(self):
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, self.palette["text_subtle"])
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, self.palette["background"])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, self.palette["child"])
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_Border, self.palette["separator"])
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, self.palette["frame"])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, self.palette["frame_hover"])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, self.palette["frame_active"])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.palette["frame"])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, self.palette["accent_soft"])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, self.palette["accent"])
                dpg.add_theme_color(dpg.mvThemeCol_Header, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, self.palette["accent_soft"])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, self.palette["accent"])
                dpg.add_theme_color(dpg.mvThemeCol_Separator, self.palette["separator"])
                dpg.add_theme_color(dpg.mvThemeCol_Tab, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, self.palette["accent_soft"])
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, self.palette["accent"])
                dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, self.palette["panel"])
                dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, self.palette["frame"])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, self.palette["background"])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, self.palette["frame"])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, self.palette["frame_hover"])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, self.palette["frame_active"])
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 16)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, 12)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
        dpg.bind_theme(theme)

    def lerp(self, a, b, t): return a + (b - a) * t
    def is_dragging(self, _, data):
        if dpg.is_mouse_button_down(0):
            y = data[1]
            if -2 <= y <= 19:
                self.ui_dragging = True
                if dpg.is_viewport_vsync_on(): dpg.set_viewport_vsync(False)
        else:
            self.ui_dragging = False
            if not dpg.is_viewport_vsync_on(): dpg.set_viewport_vsync(True)
    def drag_logic(self, _, data):
        self.n += 1
        if self.n % 30 != 0: return
        self.n = 0
        if self.ui_dragging:
            pos = dpg.get_viewport_pos()
            x = data[1]; y = data[2]
            dpg.configure_viewport(self.viewport, x_pos=pos[0] + x, y_pos=pos[1] + y)

    def add_event_handlers(self):
        with dpg.handler_registry():
            dpg.add_mouse_drag_handler(0, callback=self.drag_logic)
            dpg.add_mouse_move_handler(callback=self.is_dragging)
        dpg.set_viewport_always_top(True)

    def run(self):
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

    def _on_toggle_spectators(self, sender, value):
        self._config_set("EnableShowSpectators", bool(value))

    def build_ui(self):
        with dpg.window(
            label="NERON v1.0 - developed by khorami.dev",
            width=self.viewport_width,
            height=self.viewport_height,
            no_move=True,
            no_resize=True,
            no_close=True,
            no_collapse=True,
            tag=ROOT_TAG,
        ) as root:
            self.root_window = root

            header_group = dpg.add_group()
            dpg.add_text("Control Panel", color=self.palette["accent"], parent=header_group)
            dpg.add_spacer(height=2, parent=header_group)
            dpg.add_separator(parent=header_group)

            with dpg.tab_bar():
                self._build_tab_aimbot()
                self._build_tab_visuals()
                self._build_tab_triggerbot()
                self._build_tab_recoil()
                self._build_tab_colors()
                self._build_tab_misc()

    def _tab_card(self, title, subtitle=None):
        with dpg.child_window(
            width=-1,
            autosize_y=True,
            no_scrollbar=True,
            border=True
        ) as container:
            header = dpg.add_group(parent=container)
            dpg.add_text(title, color=self.palette["accent"], parent=header)
            if subtitle:
                dpg.add_text(
                    subtitle,
                    color=self.palette["text_subtle"],
                    parent=header
                )
            dpg.add_separator(parent=container)
            dpg.add_spacer(height=10, parent=container)
            content = dpg.add_group(parent=container)
        return content

    def _build_tab_aimbot(self):
        with dpg.tab(label="Aimbot"):
            card = self._tab_card("Aimbot Suite", "Curate how the helper locks and eases onto targets.")
            self._config_checkbox("Enable Aimbot", "EnableAimbot", parent=card)
            self._config_checkbox("Team Check##Aimbot", "EnableAimbotTeamCheck", parent=card)
            self._config_checkbox("Visibility Check", "EnableAimbotVisibilityCheck", parent=card)
            self._config_slider_int("Aimbot FOV", "AimbotFOV", 90, 50, 200, parent=card)
            self._config_slider_int("Aimbot Smoothing", "AimbotSmoothing", 5, 1, 10, parent=card)
            self._config_checkbox("Prediction (Velocity-based)", "EnableAimbotPrediction", parent=card)
            self._config_combo("Aim Position", "AimPosition", ["Head", "Neck", "Torso", "Leg"], "Head", parent=card)
            dpg.add_spacer(height=8, parent=card)
            self._config_hotkey("Aimbot Hotkey", "AimbotKey", parent=card)

    def _build_tab_visuals(self):
        with dpg.tab(label="ESP & Visuals"):
            card = self._tab_card("ESP & Visuals", "Configure intel overlays for story or squad practice.")

            with dpg.group(horizontal=True, horizontal_spacing=18, parent=card):
                left_col = dpg.add_child_window(width=int(self.viewport_width*0.30), autosize_y=True, no_scrollbar=True, border=True)
                right_col = dpg.add_child_window(width=int(self.viewport_width*0.60), autosize_y=True, no_scrollbar=True, border=True)

                dpg.add_text("Renderers", color=self.palette["text_muted"], parent=left_col)
                with dpg.group(horizontal=True, horizontal_spacing=24, parent=left_col):
                    r1c1 = dpg.add_group()
                    r1c2 = dpg.add_group()
                    self._config_checkbox("Skeleton", "EnableESPSkeletonRendering", parent=r1c1)
                    self._config_checkbox("Box", "EnableESPBoxRendering", parent=r1c1)
                    self._config_checkbox("Tracer", "EnableESPTracerRendering", parent=r1c2)
                    self._config_checkbox("Team Check", "EnableESPTeamCheck", parent=r1c2)

             

                dpg.add_spacer(height=6, parent=left_col)
                dpg.add_text("Labels", color=self.palette["text_muted"], parent=left_col)
                with dpg.group(horizontal=True, horizontal_spacing=24, parent=left_col):
                    r2c1 = dpg.add_group()
                    r2c2 = dpg.add_group()
                    self._config_checkbox("Name", "EnableESPNameText", parent=r2c1)
                    self._config_checkbox("Distance", "EnableESPDistanceText", parent=r2c1)
                    self._config_checkbox("Health Text", "EnableESPHealthText", parent=r2c2)
                    self._config_checkbox("Health Bar", "EnableESPHealthBarRendering", parent=r2c2)

                dpg.add_text("Styling & Thickness", color=self.palette["text_muted"], parent=right_col)
                dpg.add_spacer(height=2, parent=right_col)
                dpg.add_text("Health Synchronization", color=self.palette["text_subtle"], parent=right_col)
                self._config_checkbox("Skeleton follows health", "ESP_HealthSyncSkeleton", default=True, parent=right_col)
                self._config_checkbox("Health bar follows health", "ESP_HealthSyncBar", default=True, parent=right_col)
                dpg.add_spacer(height=6, parent=right_col)
                dpg.add_separator(parent=right_col)
                dpg.add_spacer(height=6, parent=right_col)
                dpg.add_text("Thickness", color=self.palette["text_subtle"], parent=right_col)
                s1 = self._config_slider_float("Skeleton scale", "ESP_SkeletonThicknessScale", 1.0, 0.6, 2.0, parent=right_col)
                s2 = self._config_slider_float("Box scale", "ESP_BoxThicknessScale", 1.0, 0.6, 2.0, parent=right_col)
                s3 = self._config_slider_float("Health bar width", "ESP_HealthBarThicknessScale", 1.0, 0.6, 1.6, parent=right_col)
                try:
                    dpg.configure_item(s1, width=int(self.control_width*1.4))
                    dpg.configure_item(s2, width=int(self.control_width*1.4))
                    dpg.configure_item(s3, width=int(self.control_width*1.4))
                except Exception:
                    pass

    def _build_tab_triggerbot(self):
        with dpg.tab(label="Triggerbot"):
            card = self._tab_card("Triggerbot", "Automate shots only when the scenario is right.")
            self._config_checkbox("Enable Trigger Bot", "EnableTriggerbot", parent=card)
            self._config_checkbox("Team Check##Triggerbot", "EnableTriggerbotTeamCheck", parent=card)
            self._config_checkbox("Key Check", "EnableTriggerbotKeyCheck", parent=card)
            dpg.add_spacer(height=8, parent=card)
            self._config_hotkey("Triggerbot Hotkey", "TriggerbotKey", parent=card)

    def _build_tab_recoil(self):
        with dpg.tab(label="Recoil Control"):
            card = self._tab_card("Recoil Control", "Balance recoil assistance for reliable tracking.")
            self._config_checkbox("Enable Recoil Control", "EnableRecoilControl", parent=card)
            self._config_slider_float("Recoil Control Smoothing", "RecoilControlSmoothing", 1.5, 1.0, 3.0, parent=card, format="%.2f")

    def _build_tab_colors(self):
        with dpg.tab(label="Colors"):
            card = self._tab_card("Color Palette", "Tweak visual cues so silhouettes stay readable.")
            ct_color = self._config_get("CT_color", "#4DA2FF") or "#4DA2FF"
            t_color = self._config_get("T_color", "#FF6A5A") or "#FF6A5A"
            fov_color = self._config_get("FOV_color", "#FF3F88") or "#FF3F88"
            dpg.add_text("Player Colors", color=self.palette["text_muted"], parent=card)
            dpg.add_spacer(height=4, parent=card)
            with dpg.group(horizontal=True, horizontal_spacing=18, parent=card):
                dpg.add_color_picker(
                    label="Counter Terrorist",
                    default_value=self.hex_to_rgb(ct_color),
                    no_alpha=True,
                    no_inputs=True,
                    no_side_preview=True,
                    no_small_preview=True,
                    width=110,
                    height=110,
                    user_data=("CT_color", "color"),
                    callback=self._on_widget_change,
                )
                dpg.add_color_picker(
                    label="Terrorist",
                    default_value=self.hex_to_rgb(t_color),
                    no_alpha=True,
                    no_inputs=True,
                    no_side_preview=True,
                    no_small_preview=True,
                    width=110,
                    height=110,
                    user_data=("T_color", "color"),
                    callback=self._on_widget_change,
                )
            dpg.add_spacer(height=6, parent=card)
            dpg.add_separator(parent=card)
            dpg.add_spacer(height=6, parent=card)
            dpg.add_text("Misc Colors", color=self.palette["text_muted"], parent=card)
            dpg.add_color_picker(
                label="FOV Color",
                default_value=self.hex_to_rgb(fov_color),
                no_alpha=True,
                no_inputs=True,
                no_side_preview=True,
                no_small_preview=True,
                width=100,
                height=100,
                parent=card,
                user_data=("FOV_color", "color"),
                callback=self._on_widget_change,
            )

    def _config_checkbox(self, label, key, default=False, parent=None):
        kwargs = {
            "label": label,
            "default_value": bool(self._config_get(key, default)),
            "user_data": (key, bool),
            "callback": self._on_widget_change,
        }
        if parent is not None:
            kwargs["parent"] = parent
        return dpg.add_checkbox(**kwargs)

    def _config_slider_int(self, label, key, default, min_value, max_value, parent=None, format=None):
        current = self._config_get(key, default)
        if current is None:
            current = default
        kwargs = {
            "label": label,
            "default_value": int(current),
            "min_value": min_value,
            "max_value": max_value,
            "user_data": (key, int),
            "callback": self._on_widget_change,
            "width": self.control_width,
        }
        if format:
            kwargs["format"] = format
        if parent is not None:
            kwargs["parent"] = parent
        return dpg.add_slider_int(**kwargs)

    def _config_slider_float(self, label, key, default, min_value, max_value, parent=None, format="%.2f"):
        current = self._config_get(key, default)
        if current is None:
            current = default
        kwargs = {
            "label": label,
            "default_value": float(current),
            "min_value": min_value,
            "max_value": max_value,
            "format": format,
            "user_data": (key, float),
            "callback": self._on_widget_change,
            "width": self.control_width,
        }
        if parent is not None:
            kwargs["parent"] = parent
        return dpg.add_slider_float(**kwargs)

    def _config_combo(self, label, key, items, default, parent=None):
        current = self._config_get(key, default)
        if current not in items:
            current = default
        kwargs = {
            "label": label,
            "items": items,
            "default_value": current,
            "user_data": (key, "combo"),
            "callback": self._on_widget_change,
            "width": self.control_width,
        }
        if parent is not None:
            kwargs["parent"] = parent
        return dpg.add_combo(**kwargs)

    def _config_hotkey(self, heading, key, parent=None):
        group_kwargs = {}
        if parent is not None:
            group_kwargs["parent"] = parent
        group_id = dpg.add_group(**group_kwargs)
        dpg.add_text(heading, color=self.palette["text_muted"], parent=group_id)
        btn = dpg.add_button(
            label=self._key_label(self._config_get(key, 0)),
            user_data=key,
            callback=self.keybind_use,
            width=int(self.control_width * 0.66),
            parent=group_id,
        )
        return btn

    def _on_widget_change(self, sender, app_data, user_data):
        key, value_type = user_data
        if value_type is bool:
            value = bool(app_data)
        elif value_type is int:
            value = int(app_data)
        elif value_type is float:
            value = float(app_data)
        elif value_type == "color":
            hex_value = self._color_value_to_hex(app_data)
            if hex_value is None:
                return
            value = hex_value
        else:
            value = app_data
        self._config_set(key, value)

    def _build_tab_misc(self):
        with dpg.tab(label="Misc"):
            card = self._tab_card("Utilities", "Quality-of-life toggles and quick boosts.")
            self._config_checkbox("Enable Bomb Timer", "EnableESPBombTimer", parent=card)
            self._config_checkbox("Enable Anti Flashbang", "EnableAntiFlashbang", parent=card)
            self._config_checkbox("Enable Bhop", "EnableBhop", parent=card)
            
            self._config_checkbox("Enable Discord RPC", "EnableDiscordRPC", parent=card)
            
            dpg.add_checkbox(
                label="Show Spectators Watching Me (in-game)",
                default_value=self.config.get("EnableShowSpectators", False),
                callback=self._on_toggle_spectators,
                parent=card,
            )
            
            self._config_checkbox("Enable FOV Changer", "EnableFovChanger", parent=card)
            self._config_slider_int("Set FOV", "FovChangeSize", 90, 50, 170, parent=card)

    def _build_tab_triggerbot(self):
        with dpg.tab(label="Triggerbot"):
            card = self._tab_card("Triggerbot", "Automate shots only when the scenario is right.")
            self._config_checkbox("Enable Trigger Bot", "EnableTriggerbot", parent=card)
            self._config_checkbox("Team Check##Triggerbot", "EnableTriggerbotTeamCheck", parent=card)
            self._config_checkbox("Key Check", "EnableTriggerbotKeyCheck", parent=card)
            dpg.add_spacer(height=8, parent=card)
            self._config_hotkey("Triggerbot Hotkey", "TriggerbotKey", parent=card)

    def _build_tab_recoil(self):
        with dpg.tab(label="Recoil Control"):
            card = self._tab_card("Recoil Control", "Balance recoil assistance for reliable tracking.")
            self._config_checkbox("Enable Recoil Control", "EnableRecoilControl", parent=card)
            self._config_slider_float("Recoil Control Smoothing", "RecoilControlSmoothing", 1.5, 1.0, 3.0, parent=card, format="%.2f")


def run_gui(Options, Runtime):
    gui = NERON_GUI(Options, Runtime)
    gui.run()
