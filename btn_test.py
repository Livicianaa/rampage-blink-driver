#!/usr/bin/env python3
"""Fare tus olaylarini goster: hangi fiziksel tus hangi evdev koduna gidiyor.

Kullanim: sudo python3 btn_test.py     (Ctrl+C ile cik)
"""
import select
import struct
import sys

import dpi_olc

EV_KEY = 0x01
NAMES = {
    0x110: "BTN_LEFT (sol)", 0x111: "BTN_RIGHT (sag)", 0x112: "BTN_MIDDLE (orta)",
    0x113: "BTN_SIDE (yan, genelde geri)", 0x114: "BTN_EXTRA (yan, genelde ileri)",
    0x115: "BTN_FORWARD", 0x116: "BTN_BACK", 0x117: "BTN_TASK",
}


def main():
    dev = dpi_olc.find_event()
    if not dev:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        f = open(dev, "rb", buffering=0)
    except PermissionError:
        sys.exit("YETKI: sudo ile calistir.")
    size = struct.calcsize(dpi_olc.FMT)
    print(f"Aygit: {dev}\nSimdi fare tuslarina tek tek bas (Ctrl+C ile cik).\n")
    try:
        while True:
            if not select.select([f], [], [], 0.2)[0]:
                continue
            data = f.read(size)
            if len(data) != size:
                continue
            _, _, et, code, val = struct.unpack(dpi_olc.FMT, data)
            if et == EV_KEY and val == 1:
                print(f"  basildi: 0x{code:03x}  {NAMES.get(code, 'bilinmeyen')}")
    except KeyboardInterrupt:
        print("\ncikildi")


if __name__ == "__main__":
    main()
