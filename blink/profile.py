"""Fare profil yonetimi (Ofis, Oyun I, Oyun II, Oyun III).

Gaming Mouse 3.0.exe RE [Kesin]:
- Blok 0x00: byte 1 = (profil_index << 5) | 0x03
- 4 Profil: 0=Ofis, 1=Oyun I, 2=Oyun II, 3=Oyun III
"""
import time

PROFILES = {
    0: "Ofis",
    1: "Oyun I",
    2: "Oyun II",
    3: "Oyun III",
}


def read_profile(mouse) -> int:
    """Aktif profil indeksini (0..3) dondur."""
    b0 = mouse.read_block(0x00)
    return (b0[1] >> 5) & 0x03


def write_profile(mouse, profile_idx: int) -> bool:
    """Aktif profili ayarla (0..3). Degisiklik varsa True dondurur."""
    if profile_idx not in PROFILES:
        raise ValueError(f"gecersiz profil indeksi: {profile_idx}")
    b0 = mouse.read_block(0x00)
    curr = (b0[1] >> 5) & 0x03
    if curr == profile_idx:
        return False

    new_b0 = bytearray(b0)
    new_b0[1] = ((profile_idx & 0x03) << 5) | 0x03
    mouse.write_block(0x00, bytes(new_b0))
    mouse.apply()
    time.sleep(0.05)

    got = mouse.read_block(0x00)
    if ((got[1] >> 5) & 0x03) != profile_idx:
        raise RuntimeError(f"profil dogrulama basarisiz: yazilan {profile_idx} okunan {(got[1] >> 5) & 0x03}")
    return True
