#!/usr/bin/env python3
"""DPI komutunu ampirik bul: her adayi uc degerle yolla, imlec hizi degisti mi diye sor."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blink import device

# (aciklama, komut, payload)  - DUSUK sonra YUKSEK ikilileri
PAIRS = [
    ("Kademe anahtari (0x14)", [
        ("stage 0", 0x14, [0x00, 0x00]),
        ("stage 7", 0x14, [0xE0, 0x00]),
    ]),
    ("16-bit ham CPI (0x17)", [
        ("200", 0x17, [0x00, 0xC8]),
        ("4800", 0x17, [0x12, 0xC0]),
    ]),
    ("16-bit DPI kodu (0x17)", [
        ("kod 1", 0x17, [0x00, 0x01]),
        ("kod 11", 0x17, [0x00, 0x0B]),
    ]),
    ("tek-byte DPI kodu (0x17 byte2)", [
        ("byte2=1", 0x17, [0x01, 0x00]),
        ("byte2=11", 0x17, [0x0B, 0x00]),
    ]),
]


def main():
    try:
        m = device.Mouse()
    except device.DeviceError as e:
        sys.exit(str(e))
    print(f"Cihaz: {m.path}\n")
    print("Her komuttan sonra fareyi masada oynat, imlec hizina bak.\n"
          "Bir ikilide DUSUK'te yavas, YUKSEK'te hizli oluyorsa o komut DPI'dir.\n")
    hits = []
    with m:
        for title, steps in PAIRS:
            print(f"--- {title} ---")
            for label, cmd, payload in steps:
                m.send(cmd, payload)
                input(f"  [{label}] yollandi. Fareyi oynat, sonra Enter...")
            ans = input(f"  >> Bu ikilide imlec hizi DUSUK->YUKSEK belirgin degisti mi? (e/h): ")
            if ans.strip().lower().startswith("e"):
                hits.append(title)
            print()
    print("=" * 40)
    if hits:
        print("DPI'yi degistiren komut(lar):")
        for h in hits:
            print("  -", h)
    else:
        print("Hicbiri hizi degistirmedi. Baska mekanizma (stage+apply dizisi) gerekebilir.")


if __name__ == "__main__":
    main()
