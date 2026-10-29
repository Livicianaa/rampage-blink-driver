#!/usr/bin/env python3
"""Fare DPI'sini ham count'tan olc: bilinen bir mesafe boyunca surup |X| count'u mesafeye bol.

Kullanim: sudo python3 dpi_olc.py [--cm 29.7]
Mesafe icin A4 kagit uzun kenari 29.7 cm, kisa kenari 21 cm. Yuksek DPI'de ne kadar uzun mesafe
olursa o kadar hassas olcum gelir.
"""
import argparse
import struct
import sys
import select

EV_REL, REL_X, REL_Y = 0x02, 0x00, 0x01
FMT = "llHHi"
SZ = struct.calcsize(FMT)
NAME = "INSTANT USB GAMING MOUSE"


def find_event():
    with open("/proc/bus/input/devices") as f:
        for chunk in f.read().split("\n\n"):
            name = next((l for l in chunk.splitlines() if l.startswith("N: Name=")), "")
            if NAME not in name or "Keyboard" in name:
                continue
            for line in chunk.splitlines():
                if line.startswith("H: Handlers="):
                    for tok in line.split("=", 1)[1].split():
                        if tok.startswith("event"):
                            return f"/dev/input/{tok}"
    return None


def find_events():
    """Farenin tum event aygitlari (fare + klavye/medya arayuzu)."""
    paths = []
    with open("/proc/bus/input/devices") as f:
        for chunk in f.read().split("\n\n"):
            name = next((l for l in chunk.splitlines() if l.startswith("N: Name=")), "")
            if NAME not in name:
                continue
            for line in chunk.splitlines():
                if line.startswith("H: Handlers="):
                    for tok in line.split("=", 1)[1].split():
                        if tok.startswith("event"):
                            paths.append(f"/dev/input/{tok}")
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cm", type=float, default=29.7, help="kaydirilacak mesafe (cm)")
    args = ap.parse_args()

    dev = find_event()
    if not dev:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        f = open(dev, "rb", buffering=0)
    except PermissionError:
        sys.exit("YETKI: sudo ile calistir.")

    print(f"Aygit: {dev}")
    print(f"1) Fareyi mesafenin baslangicina koy (A4 icin kagidin bir ucu).")
    print(f"2) Yuzeyden KALDIRMADAN, duz bir cizgide {args.cm:g} cm sur.")
    print("3) Bitisine gelince DUR ve Ctrl+C bas. Y degeri X'e gore kucuk kalmali.\n")

    dx = dy = 0
    try:
        while True:
            if select.select([f], [], [], 0.1)[0]:
                data = f.read(SZ)
                if len(data) < SZ:
                    continue
                _, _, et, code, val = struct.unpack(FMT, data)
                if et == EV_REL and code == REL_X:
                    dx += val
                elif et == EV_REL and code == REL_Y:
                    dy += val
            sys.stdout.write(f"\r  X = {dx:8d}   Y = {dy:+7d}   ")
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass

    inch = args.cm / 2.54
    major = max(abs(dx), abs(dy))
    skew = min(abs(dx), abs(dy)) / major if major else 0
    print(f"\n\nX={dx}  Y={dy}  (yan kayma orani {skew:.2f})")
    print(f">>> {args.cm:g} cm icin OLCULEN DPI ~ {major / inch:.0f}")
    if skew > 0.1:
        print(">>> UYARI: yan kayma yuksek, cizgi duz degildi; sonuc kabaca bile guvenilmez.")


if __name__ == "__main__":
    main()
