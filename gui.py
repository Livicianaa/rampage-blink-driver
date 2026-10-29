#!/usr/bin/env python3
"""Rampage Blink - Core Architecture GUI (Futuristic Edition).
PySide6 QWebEngineView + QWebChannel ile Wuxi Instant A825 (30fa:1440) donanim kontrolcusu.
"""
import sys
sys.dont_write_bytecode = True

import os
import json
import time
import threading

from PySide6.QtCore import Qt, QObject, Slot, Property, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

from blink import protocol, config, profile, keys
from blink.device import Mouse, DeviceError, PermissionNeeded, find_path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_INDEX_PATH = os.path.join(BASE_DIR, "ui", "index.html")


class ConsolePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS] line {lineNumber}: {message}", flush=True)


class HardwareBridge(QObject):
    """Web arayuzu ile donanim arasindaki cift yonlu QWebChannel koprusu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mouse = None
        self._lock = threading.Lock()
        self._path = ""
        self._backed_up = False
        self._cached_led_cfg = None
        self.connect_mouse()

    def connect_mouse(self):
        try:
            self._path = find_path() or "/dev/hidraw5"
            self.mouse = Mouse(self._path)
        except Exception as e:
            print(f"Fare baglanti hatasi: {e}")
            self.mouse = None

    def _ensure_mouse(self):
        if not self.mouse:
            self.connect_mouse()
        if not self.mouse:
            raise RuntimeError("Rampage Blink faresi bulunamadi.")

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        return (255, 255, 255)

    def _rgb_to_hex(self, rgb):
        r, g, b = rgb
        return f"#{r:02x}{g:02x}{b:02x}"

    @Property(str, constant=True)
    def devicePath(self):
        return self._path if self.mouse else "BAGLI DEGIL"

    @Slot(result=str)
    def get_state(self):
        """Donanimin mevcut durumunu JSON olarak web arayuzune sunar."""
        print("[BRIDGE] get_state called by WebChannel", flush=True)
        with self._lock:
            try:
                self._ensure_mouse()
                st = config.read_state(self.mouse)
                active_prof = profile.read_profile(self.mouse)
                raw_keys = keys.read_keys(self.mouse, profile=active_prof)
                poll_hz = config.read_polling(self.mouse)
                fire_time = config.read_fire_time(self.mouse)
                led_cfg = config.read_led(self.mouse)
                self._cached_led_cfg = led_cfg
                dpi_cols = config.read_dpi_colors(self.mouse)

                # Slot listesi: [[1, code], [2, code], ..., [6, code]]
                key_list = [[i + 1, code] for i, (_, code) in enumerate(raw_keys)]

                data = {
                    "profile": active_prof,
                    "keys": key_list,
                    "dpiCodes": list(st.codes),
                    "dpiMask": st.mask,
                    "dpiLevel": st.level,
                    "dpiColors": [self._rgb_to_hex(c) for c in dpi_cols],
                    "polling": poll_hz,
                    "fireTime": fire_time,
                    "led": {
                        "mode": led_cfg.mode,
                        "speed": led_cfg.speed,
                        "brightness": led_cfg.brightness,
                        "direction": led_cfg.direction,
                        "symmetry": led_cfg.symmetry,
                        "colors": [self._rgb_to_hex(c) for c in led_cfg.colors]
                    }
                }
                return json.dumps(data)
            except Exception as e:
                print(f"Durum okuma hatasi: {e}")
                return json.dumps({
                    "profile": 0,
                    "keys": [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6]],
                    "dpiCodes": [0x06, 0x08, 0x0c, 0x0d, 0x11, 0x18],
                    "dpiMask": 0x3f,
                    "dpiLevel": 0,
                    "dpiColors": ["#fe0000", "#ff017e", "#7e01ff", "#012aff", "#017eff", "#00fff1"],
                    "polling": 1000,
                    "fireTime": 10,
                    "led": {
                        "mode": 3,
                        "speed": 5,
                        "brightness": 7,
                        "colors": ["#ff0000", "#ff5500", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#8800ff"]
                    }
                })

    @Slot(int)
    def set_profile(self, idx):
        with self._lock:
            try:
                self._ensure_mouse()
                profile.write_profile(self.mouse, idx)
            except Exception as e:
                print(f"Profil degistirme hatasi: {e}")

    @Slot(int, int)
    def set_key(self, slot, code):
        with self._lock:
            try:
                self._ensure_mouse()
                active_prof = profile.read_profile(self.mouse)
                raw_keys = keys.read_keys(self.mouse, profile=active_prof)
                funcs = [c for _, c in raw_keys]
                if 1 <= slot <= len(funcs):
                    funcs[slot - 1] = code
                    keys.write_keys(self.mouse, funcs, profile=active_prof)
            except Exception as e:
                print(f"Tus yazma hatasi: {e}")

    @Slot(str)
    def set_dpi_state(self, json_str):
        with self._lock:
            try:
                self._ensure_mouse()
                data = json.loads(json_str)
                st = config.State(
                    codes=data["codes"],
                    mask=data["mask"],
                    level=data["level"]
                )
                config.write_state(self.mouse, st)
            except Exception as e:
                print(f"DPI yazma hatasi: {e}")

    @Slot(int, str)
    def set_stage_color(self, stage, hex_color):
        """DPI kademe gostergesi rengini (Tekerlek LED'i) hem canli uygular hem de kaydeder."""
        with self._lock:
            try:
                self._ensure_mouse()
                r, g, b = self._hex_to_rgb(hex_color)
                config.write_dpi_stage_color(self.mouse, stage, (r, g, b))
                print(f"[BRIDGE] DPI stage {stage} color updated to {hex_color}", flush=True)
            except Exception as e:
                print(f"Kademe rengi hatasi: {e}")

    @Slot(int, int, int)
    def set_led_params(self, mode, speed, brightness):
        """Hiz, parlaklik veya mod degistiginde anlik 1ms HID komutu gonderir."""
        with self._lock:
            try:
                self._ensure_mouse()
                scolor = 1 if mode in (0, 2, 4, 5, 8, 12) else 0
                config.live_led_quick(self.mouse, mode, speed, brightness, scolor=scolor)
            except Exception as e:
                print(f"Canli LED parametre hatasi: {e}")

    @Slot(int)
    def set_polling(self, hz):
        with self._lock:
            try:
                self._ensure_mouse()
                config.write_polling(self.mouse, hz)
            except Exception as e:
                print(f"Polling hizi hatasi: {e}")

    @Slot(int)
    def set_fire_time(self, ms):
        with self._lock:
            try:
                self._ensure_mouse()
                config.write_fire_time(self.mouse, ms)
            except Exception as e:
                print(f"Ates suresi hatasi: {e}")

    @Slot(int, int, int, str)
    def set_led(self, mode, speed, brightness, colors_json):
        print(f"[BRIDGE] set_led called: mode={mode}, speed={speed}, brightness={brightness}, colors={colors_json}", flush=True)
        with self._lock:
            try:
                self._ensure_mouse()
                raw_colors = json.loads(colors_json)
                rgb_colors = [self._hex_to_rgb(c) for c in raw_colors]
                while len(rgb_colors) < 7:
                    rgb_colors.append((255, 255, 255))

                cfg = config.LedConfig(
                    mode=mode,
                    speed=max(0, min(7, speed)),
                    brightness=max(0, min(7, brightness)),
                    direction=0,
                    symmetry=0,
                    color_mask=0x7f,
                    colors=rgb_colors[:7]
                )
                self._cached_led_cfg = cfg

                config.live_led(self.mouse, cfg)
                print("[BRIDGE] set_led completed successfully", flush=True)
            except Exception as e:
                print(f"[BRIDGE ERROR] LED ayar hatasi: {e}", flush=True)

    @Slot()
    def save_flash(self):
        with self._lock:
            try:
                self._ensure_mouse()
                if not self._backed_up:
                    config.backup(self.mouse, "web_gui")
                    self._backed_up = True

                if self._cached_led_cfg:
                    config.write_led(self.mouse, self._cached_led_cfg)
                print("Tum yapilandirma farenin kalici hafizasina kaydedildi.")
            except Exception as e:
                print(f"Flash kayit hatasi: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAMPAGE BLINK // CORE ARCHITECTURE")
        self.resize(1280, 840)
        self.setMinimumSize(1024, 680)

        # WebEngine Görünümü
        self.web = QWebEngineView(self)
        self.page = ConsolePage(self.web)
        self.web.setPage(self.page)
        self.setCentralWidget(self.web)

        # WebEngine Ayarları
        s = self.web.settings()
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)

        # QWebChannel Kurulumu
        self.channel = QWebChannel(self.web.page())
        self.bridge = HardwareBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        # index.html dosyasını yükle
        self.web.setUrl(QUrl.fromLocalFile(UI_INDEX_PATH))


def main():
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --enable-zero-copy"
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
