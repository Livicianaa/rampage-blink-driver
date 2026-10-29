"""Blink mouse feature-report protokolu (Gaming Mouse 3.0.exe tersine muhendislik).

Feature report = [0x07, komut, p0..p5]. Komutlar exe'den:
  0x14  DPI kademe + gosterge rengi   byte2=(kademe<<5)|G  byte3=(R<<4)|B   (R/G/B 4-bit)
  0x15  RGB renk (6 byte payload)
  0x16  LED enable bit maskesi
  0x17  16-bit deger (byte2=hi byte3=lo)
  0x10  LED mod/efekt
  0x18  okuma-adres secme

DOGRULANMA DURUMU:
  [Kesin]   rapor yapisi, 0x14 bit paketleme, okuma dizisi, DPI deger tablosu.
  [Dogrulanacak] 0x15 byte sirasi, DPI-deger yazma komutu, polling komutu
                 -> gercek fare uzerinde test edilecek, gerekirse burada duzeltilir.
"""

CMD_DPI_STAGE = 0x14   # kademe + gosterge rengi
CMD_RGB = 0x15         # [Dogrulanacak] renk payload sirasi
CMD_LED_POWER = 0x11   # LED guc anahtari (0x02: acik, 0x00: kapali)
CMD_LED_ENABLE = CMD_LED_POWER
CMD_VALUE16 = 0x17     # [Dogrulanacak] DPI/CPI 16-bit adayi
CMD_LED_MODE = 0x10    # LED mod secici [0x01, 0x01, ...]
CMD_LED_LIVE = 0x13    # Canli LED efekti (0x80, mod_byte, param_byte, ...)

# LED Modlari (Orijinal LanguageText.ini ve fcn.00448840 / apply_all.c'den birebir cozum)
LED_MODES = [
    (0, "DPI Nefes Efekti"),
    (1, "Döngü Nefes Efekti"),
    (2, "Sabit Işık"),
    (3, "Su Akış Efekti"),
    (4, "Mono Su Akış Efekti"),
    (5, "Kuyruklu Yıldız"),
    (6, "Neon"),
    (7, "Canlı Akış (Ambilight)"),
    (8, "Yanıp Sönme (Flaş)"),
    (9, "Yıldız Geçidi"),
    (10, "Dalgalanma"),
    (11, "Dans / Coşku"),
    (12, "Tuşa Duyarlı"),
    (13, "LED Kapalı"),
]
LED_MODE_NAMES = {k: v for k, v in LED_MODES}

LED_DIRECTIONS = [
    (0, "Saat Yönü"),
    (1, "Ters Saat Yönü"),
    (2, "Çift Yol"),
    (3, "Sihirbaz"),
]
LED_DIRECTION_NAMES = {k: v for k, v in LED_DIRECTIONS}

def decode_led_mode(b18_byte4, b30_byte3=0x3f):
    """Blok 0x18 byte 4 ve Blok 0x30 byte 3'ten mod ve hiz dondur."""
    if b18_byte4 == 0x87:
        return 13, 7
    if (b18_byte4 & 0x08) and (((b18_byte4 >> 4) & 7) == 1):
        mode = 12
    else:
        base = (b18_byte4 >> 4) & 7
        if b30_byte3 & 0x80:
            mode = base + 8
        else:
            mode = base
    speed = b18_byte4 & 7
    return mode, speed

def encode_led_mode(mode, speed):
    """Mod ve hizdan Blok 0x18 byte 4 uret."""
    if mode == 13:
        return 0x87
    if mode == 12:
        return 0x80 | (1 << 4) | (1 << 3) | (speed & 7)
    return 0x80 | ((mode & 7) << 4) | (speed & 7)

def decode_led_params(b38):
    """Blok 0x38'den parlaklik, yon, simetri ve tekil renk modu (scolor) dondur."""
    b38_byte2 = b38[2]
    b38_byte7 = b38[7] if len(b38) > 7 else 0
    hw_bright = (b38_byte7 >> 4) & 7
    brightness = (7 - hw_bright) & 7
    direction = (b38_byte2 >> 4) & 3
    symmetry = (b38_byte2 >> 6) & 1
    scolor = (b38_byte2 >> 7) & 1
    return brightness, direction, symmetry

def encode_led_params(brightness, direction, symmetry, scolor=0):
    """Parlaklik, yon, simetri ve tekil renk bayragindan Blok 0x38 byte 2 ve byte 7 uret."""
    brightness = max(0, min(7, brightness))
    hw_bright = (7 - brightness) & 7
    scolor_bit = 0x80 if scolor else 0x00
    b38_byte2 = scolor_bit | ((symmetry & 1) << 6) | ((direction & 3) << 4) | 0x0a
    b38_b7_bright = hw_bright << 4
    return b38_byte2, b38_b7_bright

def decode_palette(b20, b28, b30, b38):
    """Blok 0x20, 0x28, 0x30 ve 0x38'den 7 adet (R, G, B) rengi dondur.
    Instant A825 LED PWM devresi active-low (0=tam acik, 15=tam kapali) calisir.
    Ilk 6 rengin her kanali byte'in ust 4 bitinde (high nibble) saklanir (0..15 -> 0..255).
    7. tekil renk Blok 0x38 byte 6 ve byte 7 icindedir.
    """
    raw18 = b20 + b28 + b30[0:2]
    colors = []
    for i in range(6):
        r_hw = (raw18[i * 3] >> 4) & 0x0f
        g_hw = (raw18[i * 3 + 1] >> 4) & 0x0f
        b_hw = (raw18[i * 3 + 2] >> 4) & 0x0f
        r = (15 - r_hw) * 17
        g = (15 - g_hw) * 17
        b = (15 - b_hw) * 17
        colors.append((r, g, b))
    # 7. renk Blok 0x38 byte 6 ve byte 7 icindedir (4-bit kanal)
    r7_hw = (b38[6] >> 4) & 0x0f
    g7_hw = b38[6] & 0x0f
    b7_hw = b38[7] & 0x0f
    r7 = (15 - r7_hw) * 17
    g7 = (15 - g7_hw) * 17
    b7 = (15 - b7_hw) * 17
    colors.append((r7, g7, b7))
    return colors

def decode_dpi_colors(b20, b28, b30):
    """Blok 0x20, 0x28, 0x30'un alt 4 bitlerinden (low nibble) 6 DPI kademe rengini dondur."""
    raw18 = b20 + b28 + b30[0:2]
    colors = []
    for i in range(6):
        r_hw = raw18[i * 3] & 0x0f
        g_hw = raw18[i * 3 + 1] & 0x0f
        b_hw = raw18[i * 3 + 2] & 0x0f
        r = (15 - r_hw) * 17
        g = (15 - g_hw) * 17
        b = (15 - b_hw) * 17
        colors.append((r, g, b))
    return colors

def encode_palette_18(colors, existing_raw18=None, dpi_colors=None):
    """Ilk 6 adet (R, G, B) rengini 18 byte ham veriye donustur.
    Instant A825 donanim PWM kanallari active-low (0=tam acik, 15=tam kapali) calisir.
    Ust 4 bit (high nibble): Inverted User LED rengi (0..15).
    Alt 4 bit (low nibble): Inverted DPI kademe rengi (0..15).
    """
    out = bytearray(18)
    if existing_raw18 and len(existing_raw18) >= 18:
        out[:] = existing_raw18[:18]
    for i, c in enumerate(colors[:6]):
        r, g, b = c
        r_nib = 15 - ((r >> 4) & 0x0f)
        g_nib = 15 - ((g >> 4) & 0x0f)
        b_nib = 15 - ((b >> 4) & 0x0f)
        if dpi_colors and i < len(dpi_colors):
            dr, dg, db = dpi_colors[i]
            dr_nib = 15 - ((dr >> 4) & 0x0f)
            dg_nib = 15 - ((dg >> 4) & 0x0f)
            db_nib = 15 - ((db >> 4) & 0x0f)
            out[i * 3]     = (r_nib << 4) | dr_nib
            out[i * 3 + 1] = (g_nib << 4) | dg_nib
            out[i * 3 + 2] = (b_nib << 4) | db_nib
        else:
            out[i * 3]     = (r_nib << 4) | (out[i * 3] & 0x0f)
            out[i * 3 + 1] = (g_nib << 4) | (out[i * 3 + 1] & 0x0f)
            out[i * 3 + 2] = (b_nib << 4) | (out[i * 3 + 2] & 0x0f)
    return bytes(out)

# exe'deki [DPI]:xxx tablosu; DPI_SET kodu bu listeye index
DPI_TABLE = [200, 400, 600, 800, 1000, 1200, 1600, 2000, 2400, 3200, 4000, 4800]

# Config bellegi dogrusal; "bank" aslinda 8 byte'lik blok adresi (exe fcn.00425e80/00425db0).
CPI_BLOCK = 0x10      # byte3=bit4 bayraklari, byte4=0x08, byte5..7=6 kademenin nibble'lari
GENERAL_BLOCK = 0x18  # byte0=(0x18|aktif kademe), byte1=kademe aktif maskesi, byte2..3=FIRE_TIME
DPI_BANK = GENERAL_BLOCK

# Donanim CPI kodu -> CPI. [Kesin] Exe fcn.00420190 @ 0x421450 donanim sensor tablosu.
# 0x01 (200) ile 0x18 (12800) arasi tum 23 kademe birebir exe'den cozuldu (0x0b atlanir).
HW_CPI = {
    0x01: 200,
    0x02: 400,
    0x03: 600,
    0x04: 800,
    0x05: 1000,
    0x06: 1200,
    0x07: 1400,
    0x08: 1600,
    0x09: 1800,
    0x0a: 2000,
    0x0c: 2400,
    0x0d: 3200,
    0x0e: 4000,
    0x0f: 4800,
    0x10: 5600,
    0x11: 6400,
    0x12: 7200,
    0x13: 8000,
    0x14: 8800,
    0x15: 9600,
    0x16: 10400,
    0x17: 11200,
    0x18: 12800,
}
HW_CODES = sorted(HW_CPI.keys())
STAGES = 6


def decode_cpi_block(b):
    """6 kademenin 5-bit donanim kodlarini dondur."""
    flags = b[3]
    nib = [b[5] >> 4, b[5] & 0xf, b[6] >> 4, b[6] & 0xf, b[7] >> 4, b[7] & 0xf]
    return [nib[i] | (((flags >> i) & 1) << 4) for i in range(STAGES)]


def encode_cpi_block(b, codes):
    """Mevcut 8 byte'i koruyup yalniz kademe kodlarini/bayraklarini degistir."""
    out = bytearray(b)
    flags = out[3] & ~0x3f
    for i, c in enumerate(codes):
        flags |= ((c >> 4) & 1) << i
    out[3] = flags
    out[5] = ((codes[0] & 0xf) << 4) | (codes[1] & 0xf)
    out[6] = ((codes[2] & 0xf) << 4) | (codes[3] & 0xf)
    out[7] = ((codes[4] & 0xf) << 4) | (codes[5] & 0xf)
    return bytes(out)


# USB tarama hizi: blok 0x18 byte6 = 1000/Hz - 1 (exe: USB_SPEED idx 3->0, 2->1, 1->3, 0->7)
POLL_HZ = {0: 1000, 1: 500, 3: 250, 7: 125}
HZ_POLL = {hz: code for code, hz in POLL_HZ.items()}
POLL_ADDR = GENERAL_BLOCK + 6


def decode_general(b):
    return {"level": b[0] & 7, "enable_mask": b[1], "fire_time": b[2] | (b[3] << 8),
            "poll_code": b[6], "poll_hz": POLL_HZ.get(b[6])}


def hw_to_cpi(code):
    return HW_CPI.get(code)


def clamp4(v):
    return max(0, min(15, int(v)))


def dpi_stage_payload(stage, r, g, b):
    """0x14 payload: byte2=(stage<<5)|G, byte3=(R<<4)|B. r/g/b 0..15."""
    r, g, b = clamp4(r), clamp4(g), clamp4(b)
    stage &= 0x07
    return [((stage << 5) | g) & 0xff, ((r << 4) | b) & 0xff, 0, 0, 0, 0]


def rgb_payload(r, g, b):
    """0x15 payload [Dogrulanacak]. 4-bit kanallar; sira fareyle test edilecek."""
    return [clamp4(r), clamp4(g), clamp4(b), 0, 0, 0]


def value16_payload(value):
    """0x17: byte2=hi, byte3=lo."""
    v = int(value) & 0xffff
    return [(v >> 8) & 0xff, v & 0xff, 0, 0, 0, 0]


def dpi_index_to_cpi(code):
    if 0 <= code < len(DPI_TABLE):
        return DPI_TABLE[code]
    return None


def cpi_to_index(cpi):
    try:
        return DPI_TABLE.index(int(cpi))
    except ValueError:
        return None
