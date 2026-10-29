"""Makro veri modeli, depolama ve donanim kodlayicisi.

Gaming Mouse 3.0.exe tersine muhendislik bulgulari:
- Olay akisi:
  - Klavye bas: [gecikme | 0x80, keycode]
  - Klavye birak: [gecikme & 0x7F, keycode]
  - Fare hareketi (XY): [gecikme, 0xF6, dx_lo, dx_hi, dy_lo, dy_hi] (16-bit signed)
  - DPI olayi: [gecikme, 0xF8, dpi_kodu, 0]
  - Gecikme bolme: 127 tick (>127ms) uzeri gecikmeler [0x7F, 0x00] parcalarina ayrilir.
- Tanimlayici (Descriptor, 10 byte):
  - byte0: cozunurluk boleni - 1
  - byte1: tekrar modu (1: basiliyken, 2: toggle, 4: N kez)
  - byte2..4: olay sayaci/ofsetler
  - byte5..7: veri blogu ofseti
  - byte8: tekrar sayisi (16-bit)
"""
import json
import os
from typing import List, Dict, Any


def macro_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "blink-mouse", "macros")
    os.makedirs(path, exist_ok=True)
    return path


class MacroEvent:
    def __init__(self, kind: str, val: int = 0, delay: int = 20, dx: int = 0, dy: int = 0):
        self.kind = kind  # "down", "up", "delay", "xy", "mouse_click"
        self.val = val    # tus kodu / fare tusu
        self.delay = delay  # ms
        self.dx = dx
        self.dy = dy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "val": self.val,
            "delay": self.delay,
            "dx": self.dx,
            "dy": self.dy,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MacroEvent":
        return cls(
            kind=d.get("kind", "down"),
            val=d.get("val", 0),
            delay=d.get("delay", 20),
            dx=d.get("dx", 0),
            dy=d.get("dy", 0),
        )


class Macro:
    def __init__(self, name: str, repeat_mode: int = 1, repeat_count: int = 1):
        self.name = name
        self.repeat_mode = repeat_mode  # 1: basilana kadar, 2: toggle, 4: N defa
        self.repeat_count = repeat_count
        self.events: List[MacroEvent] = []

    def add_key(self, keycode: int, press_duration: int = 30, post_delay: int = 20):
        self.events.append(MacroEvent(kind="down", val=keycode, delay=press_duration))
        self.events.append(MacroEvent(kind="up", val=keycode, delay=post_delay))

    def add_delay(self, ms: int):
        self.events.append(MacroEvent(kind="delay", delay=ms))

    def add_xy(self, dx: int, dy: int, delay: int = 10):
        self.events.append(MacroEvent(kind="xy", dx=dx, dy=dy, delay=delay))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "repeat_mode": self.repeat_mode,
            "repeat_count": self.repeat_count,
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Macro":
        m = cls(
            name=d.get("name", "Yeni Makro"),
            repeat_mode=d.get("repeat_mode", 1),
            repeat_count=d.get("repeat_count", 1),
        )
        m.events = [MacroEvent.from_dict(e) for e in d.get("events", [])]
        return m

    def save(self):
        fpath = os.path.join(macro_dir(), f"{self.name}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return fpath

    @classmethod
    def load(cls, name: str) -> "Macro":
        fpath = os.path.join(macro_dir(), f"{name}.json")
        with open(fpath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def list_macros() -> List[str]:
    mdir = macro_dir()
    res = []
    for f in sorted(os.listdir(mdir)):
        if f.endswith(".json"):
            res.append(f[:-5])
    return res


def encode_macro_events(macro: Macro) -> bytes:
    """Makroyu farenin onboard bayt akisina cevir."""
    out = bytearray()
    # Tekrar sayisi (16-bit)
    rc = macro.repeat_count if macro.repeat_mode == 4 else 1
    out.extend([(rc & 0xff), ((rc >> 8) & 0xff)])

    for ev in macro.events:
        d = max(1, ev.delay)
        # 127 ms uzeri gecikmeler bolunur
        while d > 127:
            out.extend([0x7f, 0x00])
            d -= 127

        if ev.kind == "down":
            out.extend([(d | 0x80) & 0xff, ev.val & 0xff])
        elif ev.kind == "up":
            out.extend([d & 0x7f, ev.val & 0xff])
        elif ev.kind == "delay":
            out.extend([d & 0x7f, 0x00])
        elif ev.kind == "xy":
            dx = int(ev.dx) & 0xffff
            dy = int(ev.dy) & 0xffff
            out.extend([
                d & 0x7f,
                0xf6,
                dx & 0xff,
                (dx >> 8) & 0xff,
                dy & 0xff,
                (dy >> 8) & 0xff,
            ])

    return bytes(out)
