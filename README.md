# Rampage Blink Gaming Mouse Driver // Linux & Windows (Instant A825 Controller)

Linux driver and futuristic desktop control suite for gaming mice built on the **Wuxi Instant A825** chipset (USB ID `30fa:1440`, reported as **"INSTANT USB GAMING MOUSE"**), marketed under brands such as **Rampage Blink Gaming Mouse**.

Official vendor software was strictly Windows-only (`Gaming Mouse 3.0.exe`). Neither `libratbag` nor `piper` supports this microcontroller. This driver communicates natively with the hardware over raw HID feature reports and EEPROM memory banks — allowing full onboard configuration on Linux without proprietary blobs or Wine.

> **Türkçe Özet**: Wuxi Instant A825 çipli Rampage Blink gaming mouse için tersine mühendislikle geliştirilmiş, donanım seviyesinde çalışan Linux/Windows sürücüsü (driver) ve fütüristik masaüstü arayüzü. 12800 CPI sensör kademeleri, 14 donanımsal LED aydınlatma modu, tuş atamaları ve kalıcı EEPROM flash kaydı içerir.

> [!NOTE]
> **Active Maintenance & Contributions**: This repository is actively maintained. If you encounter any issues, have hardware variants of the Instant A825, or wish to contribute fixes and improvements, feel free to **open an Issue** or submit a **Pull Request**!
>
> *Bu proje aktif olarak geliştirilmektedir. Herhangi bir sorun yaşarsanız, farklı bir donanım varyantına sahipseniz veya düzeltme/katkı göndermek isterseniz çekinmeden Issue açabilir ya da PR yollayabilirsiniz.*

---

## Downloads & Releases

Pre-compiled standalone packages for **Linux (AppImage)** and **Windows (Standalone EXE)** are automatically built on every release:

- **Linux**: [Download `Rampage-Blink-x86_64.AppImage`](https://github.com/Livicianaa/rampage-blink-driver/releases) (`chmod +x Rampage-Blink-x86_64.AppImage && ./Rampage-Blink-x86_64.AppImage`)
- **Windows**: [Download `Rampage-Blink.exe`](https://github.com/Livicianaa/rampage-blink-driver/releases) (Double click to run)

---

## Features

- **Futuristic Core GUI**: Ultra-crisp editorial architecture built with PySide6 (`QWebEngineView` + `QWebChannel`), HTML5, CSS3D, and dynamic SVG HUD vector lines.
- **Bilingual Interface**: Seamless one-click switching between **English (EN)** and **Turkish (TR)** from the top-left header.
- **23 Hardware CPI Levels (200 - 12800 CPI)**: Exact native sensor table mapping (`0x01`=200 to `0x18`=12800).
- **1–3 Customizable DPI Stages**: Dynamic stage creation with independent Scroll Wheel LED color palette.
- **14 Hardware LED Lighting Effects**:
  - `0`: Single Color Breathing / Tek Renk Nefes
  - `1`: 7-Color Rainbow Cycle / 7 Renk Döngülü Nefes
  - `2`: Static Solid / Sabit Işık
  - `3`: Flowing Stream / Su Akışı
  - `4`: Mono Water Flow / Tek Renk Su Akışı
  - `5`: Comet Tail / Kuyruklu Yıldız
  - `6`: Neon Wave / Neon Dalgası
  - `7`: Live Stream (Ambilight) / Canlı Akış
  - `8`: Flashing Blink / Flaşör
  - `9`: Star Trail / Yıldız İzi
  - `10`: Ripple Wave / Dalgalanma
  - `11`: Enthusiastic / Dans
  - `12`: Key Reactive / Tuş Tepki
  - `13`: LED Disabled / Kapalı
- **Active-Low PWM Inversion**: Correct color rendering eliminating washed-out or misregistered tints (e.g. green turning purple) via physical sink inversion (`hw_nibble = 15 - user_nibble`).
- **Precision In-App RGB Mixer**: Real-time R/G/B tuning and pure saturated hardware swatches.
- **Key Remapping**: 6 hardware slots configurable for Left, Right, Wheel, Forward, Backward, Rapid Fire, DPI Loop, DPI +/-, Media functions, or Disabled.
- **Performance Control**: USB Polling Rate (125 Hz, 250 Hz, 500 Hz, 1000 Hz) and Fire/Click Interval (10 ms - 300 ms).
- **Onboard EEPROM Flash Persistence**: Write changes directly to onboard memory (`SAVE TO FLASH`) so settings persist when moving the mouse to other PCs or operating systems.
- **Comprehensive CLI Tool (`blinkctl.py`)**: Scriptable command-line interface for headless servers and terminal enthusiasts.

---

## Requirements

- Python 3.9+
- `PySide6` (`sudo pacman -S python-pyside6` on Arch Linux, or `pip install PySide6`)
- Access to the mouse's hidraw node (see udev setup below)

---

## Device Access (udev Rule)

By default, Linux limits `/dev/hidraw*` access to `root`. To configure your mouse as a regular user, install the provided udev rule:

```bash
sudo cp 99-blink-mouse.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

*Then unplug and re-plug the mouse once.*

---

## Quick Start

### Graphical Interface (GUI)

```bash
python3 gui.py
```

### Command Line Interface (CLI)

```bash
# Locate the mouse hidraw device
python3 blinkctl.py find

# View active DPI and sensor stages
python3 blinkctl.py dpi

# Check current lighting mode and colors
python3 blinkctl.py led

# Set static red lighting
python3 blinkctl.py led --mode 2 --speed 5 --brightness 7

# Set polling rate to 1000 Hz
python3 blinkctl.py setpoll 1000 --yes
```

---

## Hardware Architecture & Protocol Details

Feature Report ID `0x07`, 8-byte payload: `[0x07, CMD, p0, p1, p2, p3, p4, p5]`.

- `CMD 0x18`: EEPROM Linear Memory Bank R/W and Commit (`0x10`=CPI table, `0x18`=Active DPI & Polling & Fire Time, `0x20/0x28/0x30`=Dual-nibble Palette & DPI wheel colors, `0x38`=Single-color register & Brightness & Mode flags).
- `CMD 0x13`: Instant zero-latency live lighting preview packet.
- `CMD 0x14`: Live DPI stage wheel LED update.

---

## License & Disclaimer

Reverse-engineered strictly for hardware interoperability. No proprietary vendor binaries or assets are redistributed.

Distributed under the **MIT License**. Created by **Liviciana**.

---
*Keywords: rampage blink driver, rampage blink gaming mouse linux driver, instant a825 driver, instant usb gaming mouse, wuxi instant a825 linux driver, rampage blink mouse software*
