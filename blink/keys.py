"""Tus atama: profil tablolari ve donanim fonksiyonlari.

Profil 0: Slot 1..5 -> Blok 0x08 (byte 0..4), Slot 6 (DPI) -> Blok 0x10 (byte 0).
Fonksiyon kodlari (Gaming Mouse 3.0.exe RE ile cozuldu):
  1..6: Sol tik, Orta tik, Sag tik, Geri, Ileri, DPI dongusu
  9: Ates tusu (Fire)
  0x0b: DPI +
  0x0c: DPI -
  0x17: LED ac/kapa
  0x00: Devre disi
"""
import time
from . import protocol  # noqa: F401

KEY_FLAG = 0x20
PROFILE_BASES = {0: 0x08, 1: 0x44, 2: 0x50, 3: 0x60}
SLOT_NAMES = {
    1: "Sol tus",
    2: "Orta tus (tekerlek)",
    3: "Sag tus",
    4: "Arka yan tus",
    5: "On yan tus",
    6: "DPI tusu",
}

FUNCTIONS = {
    1: "Sol tik",
    2: "Orta tik",
    3: "Sag tik",
    4: "Geri",
    5: "Ileri",
    6: "DPI dongusu",
    9: "Ates tusu (Fire)",
    0x0b: "DPI +",
    0x0c: "DPI -",
    0x17: "LED ac/kapa",
    0x00: "Devre disi",
}
LEFT = 1


def read_keys(mouse, profile=0):
    """[(ham_bayt, fonksiyon_kodu), ...] slot 1..6."""
    base = PROFILE_BASES[profile]
    b_main = mouse.read_block(base)
    res = [(b_main[i], b_main[i] & 0x1f if b_main[i] != 0 else 0) for i in range(5)]
    if profile == 0:
        b_cpi = mouse.read_block(protocol.CPI_BLOCK)
        res.append((b_cpi[0], b_cpi[0] & 0x1f if b_cpi[0] != 0 else 0))
    return res


def write_keys(mouse, funcs, profile=0):
    """funcs: slot 1..6 icin fonksiyon kodlari.
    En az bir slot 'Sol tik' olmali. Degisiklik varsa True doner."""
    if len(funcs) != len(SLOT_NAMES):
        raise ValueError(f"{len(SLOT_NAMES)} slot icin fonksiyon verilmeli")
    for f in funcs:
        if f not in FUNCTIONS:
            raise ValueError(f"desteklenmeyen fonksiyon kodu: {f}")
    if LEFT not in funcs:
        raise ValueError("En az bir tus 'Sol tik' olmali.")

    base = PROFILE_BASES[profile]
    old_main = mouse.read_block(base)
    new_main = bytearray(old_main)
    for i in range(5):
        f = funcs[i]
        want = (KEY_FLAG | f) if f != 0 else 0
        new_main[i] = want

    changed = False
    if bytes(new_main) != old_main:
        mouse.write_block(base, bytes(new_main))
        changed = True

    if profile == 0:
        old_cpi = mouse.read_block(protocol.CPI_BLOCK)
        f_dpi = funcs[5]
        want_dpi = (KEY_FLAG | f_dpi) if f_dpi != 0 else 0
        if old_cpi[0] != want_dpi:
            new_cpi = bytearray(old_cpi)
            new_cpi[0] = want_dpi
            mouse.write_block(protocol.CPI_BLOCK, bytes(new_cpi))
            changed = True

    if not changed:
        return False

    mouse.apply()
    time.sleep(0.05)

    got_main = mouse.read_block(base)
    if got_main[:5] != bytes(new_main)[:5]:
        raise RuntimeError(f"slot 1..5 dogrulama basarisiz: yazilan {bytes(new_main)[:5].hex()} okunan {got_main[:5].hex()}")

    if profile == 0:
        got_cpi = mouse.read_block(protocol.CPI_BLOCK)
        if got_cpi[0] != (KEY_FLAG | funcs[5] if funcs[5] != 0 else 0):
            raise RuntimeError(f"slot 6 (DPI) dogrulama basarisiz: okunan {got_cpi[0]:02x}")

    return True
