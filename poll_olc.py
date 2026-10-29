#!/usr/bin/env python3
"""Fare tarama (polling) hizini olc: hareket sirasinda saniyedeki rapor (SYN_REPORT) sayisi.

Kullanim: sudo python3 poll_olc.py [--sure 6]
Olcum boyunca fareyi masada HIZLI ve surekli daireler cizerek oynat; durursa rapor gelmez.
"""
import argparse
import select
import struct
import sys
import time

import dpi_olc

EV_SYN, SYN_REPORT = 0x00, 0x00


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sure", type=int, default=6, help="olcum suresi (sn)")
    args = ap.parse_args()

    dev = dpi_olc.find_event()
    if not dev:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        f = open(dev, "rb", buffering=0)
    except PermissionError:
        sys.exit("YETKI: sudo ile calistir.")
    size = struct.calcsize(dpi_olc.FMT)

    print(f"Aygit: {dev}")
    input(f"Enter'a bas, sonra {args.sure} sn boyunca fareyi hizli daireler cizerek oynat: ")
    counts = []
    start = time.monotonic()
    window_start, n = start, 0
    while time.monotonic() - start < args.sure:
        if select.select([f], [], [], 0.05)[0]:
            data = f.read(size)
            if len(data) == size:
                _, _, et, code, _ = struct.unpack(dpi_olc.FMT, data)
                if et == EV_SYN and code == SYN_REPORT:
                    n += 1
        now = time.monotonic()
        if now - window_start >= 1.0:
            counts.append(n)
            print(f"  {len(counts)}. sn: {n} rapor/sn")
            window_start, n = now, 0
    peak = max(counts) if counts else 0
    print(f"\n>>> tepe: {peak} rapor/sn  (yaklasik tarama hizi)")
    for hz in (125, 250, 500, 1000):
        if peak <= hz * 1.15:
            print(f">>> en yakin standart: {hz} Hz")
            break


if __name__ == "__main__":
    main()
