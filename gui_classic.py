#!/usr/bin/env python3
"""Blink Mouse - Linux GUI kontrol uygulamasi (PySide6)."""
import os
import sys

sys.dont_write_bytecode = True

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QPlainTextEdit, QMessageBox,
    QRadioButton, QCheckBox, QButtonGroup, QTabWidget, QSlider, QSpinBox,
    QListWidget, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog,
    QColorDialog,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blink import device, protocol, config, keys, profile, macro  # noqa: E402
from blink import __version__  # noqa: E402

UDEV_HINT = (
    "Fareye erisim yok (hidraw root-only).\n\n"
    "Kalici cozum: su kurali kur, sonra fareyi USB'den bir kez cikar-tak:\n"
    "  sudo cp 99-blink-mouse.rules /etc/udev/rules.d/\n"
    "  sudo udevadm control --reload-rules\n\n"
    "Ya da uygulamayi sudo ile calistir."
)


def code_label(code):
    cpi = protocol.hw_to_cpi(code)
    return f"0x{code:02x}  {cpi} CPI" if cpi else f"0x{code:02x}"


class DpiTab(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        lay = QVBoxLayout(self)
        box = QGroupBox("DPI Kademeleri (200 - 12800 CPI)")
        g = QGridLayout(box)
        for col, title in enumerate(("Aktif", "Acik", "Kademe", "CPI")):
            g.addWidget(QLabel(title), 0, col)

        self.group = QButtonGroup(self)
        self.radios, self.checks, self.combos = [], [], []
        for i in range(protocol.STAGES):
            r = QRadioButton()
            self.group.addButton(r, i)
            c = QCheckBox()
            cb = QComboBox()
            for code in protocol.HW_CODES:
                cb.addItem(code_label(code), code)
            g.addWidget(r, i + 1, 0)
            g.addWidget(c, i + 1, 1)
            g.addWidget(QLabel(f"Kademe {i}"), i + 1, 2)
            g.addWidget(cb, i + 1, 3)
            self.radios.append(r)
            self.checks.append(c)
            self.combos.append(cb)
        lay.addWidget(box)

        row = QHBoxLayout()
        reload_b = QPushButton("Fareden Oku")
        reload_b.clicked.connect(owner.refresh)
        apply_b = QPushButton("Uygula")
        apply_b.clicked.connect(self.apply)
        row.addWidget(reload_b)
        row.addWidget(apply_b)
        lay.addLayout(row)
        lay.addStretch(1)

    def load(self, state):
        for i in range(protocol.STAGES):
            self.checks[i].setChecked(bool((state.mask >> i) & 1))
            self.combos[i].setCurrentIndex(protocol.HW_CODES.index(state.codes[i]))
        self.radios[state.level].setChecked(True)

    def collect(self):
        mask = sum(1 << i for i, c in enumerate(self.checks) if c.isChecked())
        codes = [cb.currentData() for cb in self.combos]
        return config.State(codes, mask, max(self.group.checkedId(), 0))

    def apply(self):
        self.owner.write(self.collect())


class KeysTab(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        lay = QVBoxLayout(self)
        box = QGroupBox("Tus Atamalari")
        g = QGridLayout(box)
        self.combos = []
        for row, (slot, name) in enumerate(keys.SLOT_NAMES.items()):
            g.addWidget(QLabel(name), row, 0)
            cb = QComboBox()
            for code, label in keys.FUNCTIONS.items():
                cb.addItem(label, code)
            g.addWidget(cb, row, 1)
            self.combos.append(cb)
        lay.addWidget(box)
        note = QLabel("En az bir tus 'Sol tik' olmalidir. Degisiklikler fare donanimina dogrudan kaydedilir.")
        note.setWordWrap(True)
        lay.addWidget(note)
        row = QHBoxLayout()
        reload_b = QPushButton("Fareden Oku")
        reload_b.clicked.connect(owner.refresh)
        apply_b = QPushButton("Uygula")
        apply_b.clicked.connect(lambda: owner.write_keys([cb.currentData() for cb in self.combos]))
        row.addWidget(reload_b)
        row.addWidget(apply_b)
        lay.addLayout(row)
        lay.addStretch(1)

    def load(self, current):
        for cb, (raw, code) in zip(self.combos, current):
            idx = cb.findData(code)
            if idx < 0:
                cb.addItem(f"Ozel (0x{raw:02x})", code)
                idx = cb.count() - 1
            cb.setCurrentIndex(idx)


class PerfTab(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        lay = QVBoxLayout(self)

        poll_box = QGroupBox("Tarama Hizi (Polling Rate)")
        g_poll = QGridLayout(poll_box)
        g_poll.addWidget(QLabel("USB Tarama Hizi:"), 0, 0)
        self.combo = QComboBox()
        for hz in sorted(protocol.HZ_POLL):
            self.combo.addItem(f"{hz} Hz", hz)
        g_poll.addWidget(self.combo, 0, 1)
        lay.addWidget(poll_box)

        fire_box = QGroupBox("Ates Tusu / Cift Tik Hizi")
        g_fire = QGridLayout(fire_box)
        g_fire.addWidget(QLabel("Tiklama Araligi (ms):"), 0, 0)
        self.fire_spin = QSpinBox()
        self.fire_spin.setRange(10, 300)
        self.fire_spin.setSingleStep(5)
        self.fire_slider = QSlider(Qt.Horizontal)
        self.fire_slider.setRange(10, 300)
        self.fire_slider.setSingleStep(5)

        self.fire_spin.valueChanged.connect(self.fire_slider.setValue)
        self.fire_slider.valueChanged.connect(self.fire_spin.setValue)

        g_fire.addWidget(self.fire_slider, 0, 1)
        g_fire.addWidget(self.fire_spin, 0, 2)
        lay.addWidget(fire_box)

        note = QLabel("Not: Fare imlec hassasiyeti ve tekerlek kaydirma hizi host (isletim sistemi) tarafindadir.")
        note.setWordWrap(True)
        lay.addWidget(note)

        row = QHBoxLayout()
        reload_b = QPushButton("Fareden Oku")
        reload_b.clicked.connect(owner.refresh)
        apply_b = QPushButton("Uygula")
        apply_b.clicked.connect(self.apply)
        row.addWidget(reload_b)
        row.addWidget(apply_b)
        lay.addLayout(row)
        lay.addStretch(1)

    def load(self, hz, fire_time):
        idx = self.combo.findData(hz)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        if fire_time:
            self.fire_spin.setValue(fire_time)

    def apply(self):
        self.owner.write_polling(self.combo.currentData())
        self.owner.write_fire_time(self.fire_spin.value())


class MacroTab(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.current_macro = None

        lay = QHBoxLayout(self)

        # Sol taraf: Makro Listesi
        left_box = QGroupBox("Makrolar")
        l_lay = QVBoxLayout(left_box)
        self.macro_list = QListWidget()
        self.macro_list.currentTextChanged.connect(self.on_macro_selected)
        l_lay.addWidget(self.macro_list)

        btn_row1 = QHBoxLayout()
        new_btn = QPushButton("Yeni")
        new_btn.clicked.connect(self.new_macro)
        del_btn = QPushButton("Sil")
        del_btn.clicked.connect(self.del_macro)
        btn_row1.addWidget(new_btn)
        btn_row1.addWidget(del_btn)
        l_lay.addLayout(btn_row1)
        lay.addWidget(left_box, 1)

        # Sag taraf: Olay Listesi & Parametreler
        right_box = QGroupBox("Makro Olaylari ve Tekrar Ayari")
        r_lay = QVBoxLayout(right_box)

        rep_row = QHBoxLayout()
        rep_row.addWidget(QLabel("Tekrar Modu:"))
        self.rep_combo = QComboBox()
        self.rep_combo.addItem("Tus basili tutuldukca tekrarla", 1)
        self.rep_combo.addItem("Tekrar basilana kadar tekrarla (Aç/Kapa)", 2)
        self.rep_combo.addItem("Belirtilen sayida tekrarla", 4)
        rep_row.addWidget(self.rep_combo)

        rep_row.addWidget(QLabel("Sayi:"))
        self.rep_spin = QSpinBox()
        self.rep_spin.setRange(1, 9999)
        self.rep_spin.setValue(1)
        rep_row.addWidget(self.rep_spin)
        r_lay.addLayout(rep_row)

        self.events_table = QTableWidget(0, 4)
        self.events_table.setHorizontalHeaderLabels(["Sira", "Olay Turu", "Deger / Tus", "Gecikme (ms)"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        r_lay.addWidget(self.events_table)

        btn_row2 = QHBoxLayout()
        add_key_btn = QPushButton("Tus Ekle")
        add_key_btn.clicked.connect(self.add_key_event)
        add_delay_btn = QPushButton("Gecikme Ekle")
        add_delay_btn.clicked.connect(self.add_delay_event)
        del_ev_btn = QPushButton("Olay Sil")
        del_ev_btn.clicked.connect(self.del_event)
        save_btn = QPushButton("Makroyu Kaydet")
        save_btn.clicked.connect(self.save_current)

        btn_row2.addWidget(add_key_btn)
        btn_row2.addWidget(add_delay_btn)
        btn_row2.addWidget(del_ev_btn)
        btn_row2.addWidget(save_btn)
        r_lay.addLayout(btn_row2)

        lay.addWidget(right_box, 2)
        self.reload_list()

    def reload_list(self):
        self.macro_list.clear()
        names = macro.list_macros()
        for n in names:
            self.macro_list.addItem(n)
        if names:
            self.macro_list.setCurrentRow(0)

    def on_macro_selected(self, name):
        if not name:
            return
        try:
            m = macro.Macro.load(name)
            self.current_macro = m
            idx = self.rep_combo.findData(m.repeat_mode)
            if idx >= 0:
                self.rep_combo.setCurrentIndex(idx)
            self.rep_spin.setValue(m.repeat_count)
            self.render_events()
        except Exception as e:
            self.owner._log(f"makro yuklenemedi: {e}")

    def render_events(self):
        self.events_table.setRowCount(0)
        if not self.current_macro:
            return
        for i, ev in enumerate(self.current_macro.events):
            self.events_table.insertRow(i)
            self.events_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.events_table.setItem(i, 1, QTableWidgetItem(ev.kind))
            self.events_table.setItem(i, 2, QTableWidgetItem(str(ev.val) if ev.kind != "delay" else "-"))
            self.events_table.setItem(i, 3, QTableWidgetItem(str(ev.delay)))

    def new_macro(self):
        name, ok = QInputDialog.getText(self, "Yeni Makro", "Makro Adi:")
        if ok and name.strip():
            m = macro.Macro(name.strip())
            m.save()
            self.reload_list()
            self.macro_list.setCurrentRow(self.macro_list.count() - 1)

    def del_macro(self):
        curr = self.macro_list.currentItem()
        if not curr:
            return
        name = curr.text()
        fpath = os.path.join(macro.macro_dir(), f"{name}.json")
        if os.path.exists(fpath):
            os.remove(fpath)
        self.reload_list()

    def add_key_event(self):
        if not self.current_macro:
            return
        code, ok = QInputDialog.getInt(self, "Tus Kodu Ekle", "Windows VK / Donanim Kodu (örn: 65 = A tuşu):", 65, 1, 255)
        if ok:
            self.current_macro.add_key(code, press_duration=30, post_delay=20)
            self.render_events()

    def add_delay_event(self):
        if not self.current_macro:
            return
        ms, ok = QInputDialog.getInt(self, "Gecikme Ekle", "Gecikme suresi (ms):", 50, 1, 5000)
        if ok:
            self.current_macro.add_delay(ms)
            self.render_events()

    def del_event(self):
        row = self.events_table.currentRow()
        if row >= 0 and self.current_macro and row < len(self.current_macro.events):
            self.current_macro.events.pop(row)
            self.render_events()

    def save_current(self):
        if not self.current_macro:
            return
        self.current_macro.repeat_mode = self.rep_combo.currentData()
        self.current_macro.repeat_count = self.rep_spin.value()
        self.current_macro.save()
        self.owner._log(f"makro kaydedildi: {self.current_macro.name}")


class LedTab(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.colors = []
        self.color_buttons = []
        self.color_checks = []
        self._loading = False

        main_h = QHBoxLayout(self)
        main_h.setContentsMargins(10, 10, 10, 10)
        main_h.setSpacing(14)

        # Sol Kolon: Efekt, Yon, Hiz, Parlaklik, Islemler
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # 1. Mod & Efekt Ayarlari
        mode_box = QGroupBox("Efekt Modu ve Akis")
        mode_g = QGridLayout(mode_box)
        mode_g.setVerticalSpacing(8)
        mode_g.setHorizontalSpacing(10)

        mode_g.addWidget(QLabel("Efekt Modu:"), 0, 0)
        self.mode_combo = QComboBox()
        for mode_val, name in protocol.LED_MODES:
            self.mode_combo.addItem(f"{name} ({mode_val})", mode_val)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)
        mode_g.addWidget(self.mode_combo, 0, 1)

        mode_g.addWidget(QLabel("Akis Yonu:"), 1, 0)
        self.dir_combo = QComboBox()
        for dir_val, name in protocol.LED_DIRECTIONS:
            self.dir_combo.addItem(name, dir_val)
        self.dir_combo.currentIndexChanged.connect(self.on_live_change)
        mode_g.addWidget(self.dir_combo, 1, 1)

        self.sym_check = QCheckBox("Simetrik Akis Efekti")
        self.sym_check.stateChanged.connect(self.on_live_change)
        mode_g.addWidget(self.sym_check, 2, 1)

        left_col.addWidget(mode_box)

        # 2. Hiz ve Parlaklik
        adj_box = QGroupBox("Hiz ve Parlaklik")
        adj_g = QGridLayout(adj_box)
        adj_g.setVerticalSpacing(8)
        adj_g.setHorizontalSpacing(10)

        adj_g.addWidget(QLabel("Efekt Hizi:"), 0, 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 8)
        self.speed_slider.setValue(4)
        self.speed_lbl = QLabel("4 / 8")
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        adj_g.addWidget(self.speed_slider, 0, 1)
        adj_g.addWidget(self.speed_lbl, 0, 2)

        adj_g.addWidget(QLabel("Parlaklik:"), 1, 0)
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setRange(0, 7)
        self.bright_slider.setValue(7)
        self.bright_lbl = QLabel("7 / 7 (Maks)")
        self.bright_slider.valueChanged.connect(self._on_bright_changed)
        adj_g.addWidget(self.bright_slider, 1, 1)
        adj_g.addWidget(self.bright_lbl, 1, 2)

        left_col.addWidget(adj_box)

        # Butonlar
        btn_box = QGroupBox("Kontrol")
        btn_lay = QVBoxLayout(btn_box)
        btn_lay.setSpacing(8)

        self.apply_btn = QPushButton("Aydinlatmayi Hafizaya Kaydet")
        self.apply_btn.setStyleSheet("font-weight:bold; padding:8px;")
        self.apply_btn.clicked.connect(self.on_apply)
        btn_lay.addWidget(self.apply_btn)

        self.off_btn = QPushButton("LED Kapat")
        self.off_btn.clicked.connect(self.on_led_off)
        btn_lay.addWidget(self.off_btn)

        left_col.addWidget(btn_box)
        left_col.addStretch(1)

        # Sag Kolon: 7 Renk Paleti ve Dongu
        pal_box = QGroupBox("7 Renk Paleti ve Dongu Katilimi")
        pal_g = QGridLayout(pal_box)
        pal_g.setVerticalSpacing(8)
        pal_g.setHorizontalSpacing(10)
        pal_g.setContentsMargins(10, 14, 10, 14)

        pal_g.addWidget(QLabel("<b>No</b>"), 0, 0)
        pal_g.addWidget(QLabel("<b>Renk Secimi (Tikla)</b>"), 0, 1)
        pal_g.addWidget(QLabel("<b>Dongude Aktif</b>"), 0, 2)

        for i in range(7):
            lbl = QLabel(f"Renk {i+1}:")
            lbl.setStyleSheet("font-weight: bold;")
            pal_g.addWidget(lbl, i + 1, 0)

            btn = QPushButton()
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, idx=i: self.pick_color(idx))
            self.color_buttons.append(btn)
            pal_g.addWidget(btn, i + 1, 1)

            chk = QCheckBox("Aktif")
            chk.stateChanged.connect(self.on_live_change)
            self.color_checks.append(chk)
            pal_g.addWidget(chk, i + 1, 2)

        main_h.addLayout(left_col, 1)
        main_h.addWidget(pal_box, 1)

    def _on_mode_combo_changed(self):
        mode = self.mode_combo.currentData()
        if mode is not None:
            self._update_controls_state(mode)
        QTimer.singleShot(0, self.on_live_change)

    def _update_controls_state(self, mode):
        is_off = (mode == 13)
        self.bright_slider.setEnabled(mode in (2, 3, 4, 5))
        self.speed_slider.setEnabled(mode not in (2, 9, 12, 13))
        self.dir_combo.setEnabled(mode in (3, 4, 5, 7, 10))
        self.sym_check.setEnabled(mode in (3, 4, 5, 7, 10))
        for i, btn in enumerate(self.color_buttons):
            if is_off:
                btn.setEnabled(False)
            elif mode == 2:
                btn.setEnabled(i == 0)  # Sabit Isik yalnizca Renk 1'i kullanir
            elif mode in (1, 3, 4, 5, 9, 10):
                btn.setEnabled(True)
            else:
                btn.setEnabled(False)
        for chk in self.color_checks:
            chk.setEnabled(mode in (1, 3, 4, 5, 9, 10))

    def _on_speed_changed(self, v):
        self.speed_lbl.setText(f"{v} / 8")
        QTimer.singleShot(0, self.on_live_change)

    def _on_bright_changed(self, v):
        tag = " (Kapali)" if v == 0 else (" (Maks)" if v == 7 else "")
        self.bright_lbl.setText(f"{v} / 7{tag}")
        QTimer.singleShot(0, self.on_live_change)

    def get_current_config(self):
        mode = self.mode_combo.currentData()
        if mode is None:
            mode = 1
        direction = self.dir_combo.currentData()
        if direction is None:
            direction = 0
        symmetry = 1 if self.sym_check.isChecked() else 0
        speed = max(0, min(7, self.speed_slider.value() - 1))
        brightness = max(0, min(7, self.bright_slider.value()))

        if mode in (1, 3, 4, 5, 9, 10):
            mask = 0
            for i, chk in enumerate(self.color_checks):
                if chk.isChecked():
                    mask |= (1 << i)
            if mask == 0:
                mask = 0x7f
        else:
            mask = 0x7f

        return config.LedConfig(
            mode=mode,
            speed=speed,
            brightness=brightness,
            direction=direction,
            symmetry=symmetry,
            color_mask=mask,
            colors=self.colors,
        )

    def on_live_change(self):
        if self._loading or not self.owner.mouse:
            return
        cfg = self.get_current_config()
        try:
            config.live_led(self.owner.mouse, cfg)
        except Exception as e:
            if hasattr(self.owner, "_log"):
                self.owner._log(f"Canli LED hatasi: {e}")

    def load(self, cfg):
        self._loading = True
        try:
            idx = self.mode_combo.findData(cfg.mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)

            d_idx = self.dir_combo.findData(cfg.direction)
            if d_idx >= 0:
                self.dir_combo.setCurrentIndex(d_idx)

            self.sym_check.setChecked(bool(cfg.symmetry))

            self.speed_slider.setValue(cfg.speed + 1)
            self.speed_lbl.setText(f"{cfg.speed + 1} / 8")

            tag = " (Kapali)" if cfg.brightness == 0 else (" (Maks)" if cfg.brightness == 7 else "")
            self.bright_slider.setValue(min(7, cfg.brightness))
            self.bright_lbl.setText(f"{min(7, cfg.brightness)} / 7{tag}")

            self._update_controls_state(cfg.mode)

            self.colors = list(cfg.colors)
            mask = cfg.color_mask if cfg.color_mask else 0x7f
            for i in range(7):
                r, g, b = self.colors[i]
                self.update_btn_color(i, r, g, b)
                self.color_checks[i].setChecked(bool((mask >> i) & 1))
        finally:
            self._loading = False

    def update_btn_color(self, idx, r, g, b):
        self.color_buttons[idx].setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            f"color: {'black' if (r*0.299 + g*0.587 + b*0.114) > 150 else 'white'}; "
            f"border: 1px solid #555; border-radius: 4px; font-weight: bold;"
        )
        self.color_buttons[idx].setText(f"RGB({r}, {g}, {b})")

    def pick_color(self, idx):
        cur_r, cur_g, cur_b = self.colors[idx]
        col = QColorDialog.getColor(QColor(cur_r, cur_g, cur_b), self, f"Renk {idx+1} Sec")
        if col.isValid():
            self.colors[idx] = (col.red(), col.green(), col.blue())
            self.update_btn_color(idx, col.red(), col.green(), col.blue())
            self.on_live_change()

    def on_apply(self):
        if not self.owner.mouse:
            return
        cfg = self.get_current_config()
        try:
            config.write_led(self.owner.mouse, cfg)
            mname = protocol.LED_MODE_NAMES.get(cfg.mode, cfg.mode)
            self.owner._log(f"aydinlatma fare hafizasina kaydedildi: mod {mname}, hiz {cfg.speed+1}, parlaklik {cfg.brightness}")
        except Exception as e:
            QMessageBox.warning(self, "Aydinlatma Hatasi", str(e))
            self.owner._log(f"aydinlatma hatasi: {e}")

    def on_led_off(self):
        idx = self.mode_combo.findData(13)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.on_apply()


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Blink Mouse  -  v{__version__}")
        self.setMinimumWidth(740)
        self.setMinimumHeight(560)
        self.resize(780, 580)
        self.mouse = None
        self._backed_up = False

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Ust Bar: Baglanti durumu ve Profil Secici
        top_row = QHBoxLayout()
        self.status = QLabel("Baglanti bekleniyor...")
        self.status.setStyleSheet("font-weight:600;")
        top_row.addWidget(self.status, 1)

        top_row.addWidget(QLabel("Aktif Profil:"))
        self.prof_combo = QComboBox()
        for idx, name in profile.PROFILES.items():
            self.prof_combo.addItem(name, idx)
        self.prof_combo.currentIndexChanged.connect(self.on_profile_changed)
        top_row.addWidget(self.prof_combo)
        lay.addLayout(top_row)

        # Sekmeler
        self.tabs = QTabWidget()
        self.dpi_tab = DpiTab(self)
        self.tabs.addTab(self.dpi_tab, "DPI")
        self.keys_tab = KeysTab(self)
        self.tabs.addTab(self.keys_tab, "Tuslar")
        self.perf_tab = PerfTab(self)
        self.tabs.addTab(self.perf_tab, "Performans")
        self.macro_tab = MacroTab(self)
        self.tabs.addTab(self.macro_tab, "Makro")

        self.led_tab = LedTab(self)
        self.tabs.addTab(self.led_tab, "Aydinlatma")

        lay.addWidget(self.tabs)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(300)
        self.log.setFixedHeight(110)
        lay.addWidget(QLabel("Islem Kaydi (Log)"))
        lay.addWidget(self.log)

        self.connect_device()

    def connect_device(self):
        try:
            self.mouse = device.Mouse()
        except device.PermissionNeeded:
            self.mouse = None
            self.status.setText("Cihaz bulundu ama erisim yok (udev/sudo gerekli)")
            QMessageBox.warning(self, "Erisim", UDEV_HINT)
            return
        except device.DeviceError as e:
            self.mouse = None
            self.status.setText(str(e))
            return
        self.refresh()

    def refresh(self):
        if not self.mouse:
            self.connect_device()
            return
        try:
            state = config.read_state(self.mouse)
            active_prof = profile.read_profile(self.mouse)
            poll_hz = config.read_polling(self.mouse)
            fire_time = config.read_fire_time(self.mouse)
            current_keys = keys.read_keys(self.mouse, profile=active_prof)
        except OSError as e:
            self.status.setText(f"Okuma hatasi: {e}")
            return

        self.prof_combo.blockSignals(True)
        self.prof_combo.setCurrentIndex(active_prof)
        self.prof_combo.blockSignals(False)

        self.dpi_tab.load(state)
        self.keys_tab.load(current_keys)
        self.perf_tab.load(poll_hz, fire_time)
        led_cfg = config.read_led(self.mouse)
        if led_cfg.mode != 13:
            try:
                self.mouse.send(protocol.CMD_LED_POWER, [0x02, 0, 0, 0, 0, 0])
                self.mouse.send(0x16, [0x00, 0xff, 0, 0, 0, 0])
                self.mouse.send(protocol.CMD_LED_MODE, [0x01, 0x01, 0, 0, 0, 0])
            except Exception:
                pass
        self.led_tab.load(led_cfg)
        self.status.setText(f"Bagli: {self.mouse.path}")
        self._log(f"fareden okundu: profil {profile.PROFILES.get(active_prof)}, "
                  f"aktif kademe {state.level} ({protocol.hw_to_cpi(state.codes[state.level])} CPI), "
                  f"tarama {poll_hz} Hz, ates {fire_time} ms")

    def on_profile_changed(self, idx):
        if not self.mouse:
            return
        try:
            changed = profile.write_profile(self.mouse, idx)
            if changed:
                self._log(f"aktif profil {profile.PROFILES[idx]} olarak degistirildi")
                self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Profil Hatasi", str(e))
            self._log(f"profil hatasi: {e}")

    def write(self, state):
        if not self.mouse:
            QMessageBox.warning(self, "Cihaz yok", UDEV_HINT)
            return
        try:
            if not self._backed_up:
                self._log("yedek: " + config.backup(self.mouse, "gui"))
                self._backed_up = True
            changed = config.write_state(self.mouse, state)
        except (ValueError, RuntimeError, OSError) as e:
            QMessageBox.warning(self, "Yazilamadi", str(e))
            self._log(f"hata: {e}")
            return
        self._log("DPI yazildi ve dogrulandi: " + (", ".join(f"0x{a:02x}" for a in changed) or "degisiklik yok"))

    def write_polling(self, hz):
        if not self.mouse:
            QMessageBox.warning(self, "Cihaz yok", UDEV_HINT)
            return
        try:
            if not self._backed_up:
                self._log("yedek: " + config.backup(self.mouse, "gui"))
                self._backed_up = True
            changed = config.write_polling(self.mouse, hz)
        except (ValueError, RuntimeError, OSError) as e:
            QMessageBox.warning(self, "Yazilamadi", str(e))
            self._log(f"hata: {e}")
            return
        self._log(f"tarama hizi {hz} Hz yazildi ve dogrulandi" if changed else "tarama hizinda degisiklik yok")

    def write_fire_time(self, ms):
        if not self.mouse:
            return
        try:
            changed = config.write_fire_time(self.mouse, ms)
            if changed:
                self._log(f"ates suresi {ms} ms yazildi ve dogrulandi")
        except Exception as e:
            self._log(f"ates suresi yazilamadi: {e}")

    def write_keys(self, funcs):
        if not self.mouse:
            QMessageBox.warning(self, "Cihaz yok", UDEV_HINT)
            return
        try:
            if not self._backed_up:
                self._log("yedek: " + config.backup(self.mouse, "gui"))
                self._backed_up = True
            active_prof = profile.read_profile(self.mouse)
            changed = keys.write_keys(self.mouse, funcs, profile=active_prof)
        except (ValueError, RuntimeError, OSError) as e:
            QMessageBox.warning(self, "Yazilamadi", str(e))
            self._log(f"hata: {e}")
            return
        self._log("tuslar yazildi ve dogrulandi" if changed else "tuslarda degisiklik yok")

    def _log(self, msg):
        self.log.appendPlainText(msg)


def apply_dark(app):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(30, 31, 34))
    p.setColor(QPalette.Base, QColor(24, 25, 28))
    p.setColor(QPalette.Text, QColor(220, 221, 224))
    p.setColor(QPalette.WindowText, QColor(220, 221, 224))
    p.setColor(QPalette.Button, QColor(45, 46, 50))
    p.setColor(QPalette.ButtonText, QColor(220, 221, 224))
    p.setColor(QPalette.Highlight, QColor(60, 120, 216))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(p)


def main():
    app = QApplication(sys.argv)
    apply_dark(app)
    w = Main()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
