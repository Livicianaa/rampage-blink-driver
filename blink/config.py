"""Yuksek seviye config islemleri: durum oku, yedekle, yaz+dogrula."""
import os
import time
from datetime import datetime

from . import protocol


def backup_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "blink-mouse", "backups")


def backup(mouse, tag):
    os.makedirs(backup_dir(), exist_ok=True)
    path = os.path.join(backup_dir(), f"config-{tag}-{datetime.now():%Y%m%d-%H%M%S}.bin")
    with open(path, "wb") as f:
        f.write(mouse.read_mem(0, 0xA0))
    return path


class State:
    def __init__(self, codes, mask, level):
        self.codes = list(codes)
        self.mask = mask
        self.level = level


def read_state(mouse):
    cpi = mouse.read_block(protocol.CPI_BLOCK)
    gen = protocol.decode_general(mouse.read_block(protocol.GENERAL_BLOCK))
    return State(protocol.decode_cpi_block(cpi), gen["enable_mask"] & 0x3f, gen["level"])


def read_polling(mouse):
    return protocol.POLL_HZ.get(mouse.read_block(protocol.GENERAL_BLOCK)[6])


def write_polling(mouse, hz):
    """Tarama hizini (125/250/500/1000) yaz, geri okuyup dogrula. Degisiklik varsa True."""
    if hz not in protocol.HZ_POLL:
        raise ValueError("tarama hizi 125, 250, 500 veya 1000 olmali")
    old = mouse.read_block(protocol.GENERAL_BLOCK)
    code = protocol.HZ_POLL[hz]
    if old[6] == code:
        return False
    new = bytearray(old)
    new[6] = code
    mouse.write_block(protocol.GENERAL_BLOCK, bytes(new))
    mouse.apply()
    time.sleep(0.05)
    got = mouse.read_block(protocol.GENERAL_BLOCK)
    if got != bytes(new):
        raise RuntimeError(f"dogrulama basarisiz: yazilan {bytes(new).hex()} okunan {got.hex()}")
    return True


def read_fire_time(mouse):
    """Ates tusu / cift tik suresini ms cinsinden oku."""
    gen = mouse.read_block(protocol.GENERAL_BLOCK)
    return gen[2] | (gen[3] << 8)


def write_fire_time(mouse, ms):
    """Ates / cift tik suresini (10..300 ms) yaz, geri okuyup dogrula."""
    if not (10 <= ms <= 300):
        raise ValueError("ates suresi 10..300 ms arasinda olmali")
    old = mouse.read_block(protocol.GENERAL_BLOCK)
    val = int(ms) & 0xffff
    lo, hi = val & 0xff, (val >> 8) & 0xff
    if old[2] == lo and old[3] == hi:
        return False
    new = bytearray(old)
    new[2] = lo
    new[3] = hi
    mouse.write_block(protocol.GENERAL_BLOCK, bytes(new))
    mouse.apply()
    time.sleep(0.05)
    got = mouse.read_block(protocol.GENERAL_BLOCK)
    if got[2] != lo or got[3] != hi:
        raise RuntimeError(f"ates suresi dogrulama basarisiz: yazilan {ms}ms okunan {got[2] | (got[3] << 8)}ms")
    return True


def write_state(mouse, state):
    """Degisen bloklari yaz, apply et, geri okuyup dogrula. Hata durumunda ValueError/RuntimeError."""
    if not 0 <= state.level < protocol.STAGES:
        raise ValueError("aktif kademe 0..5 olmali")
    if not state.mask & 0x3f:
        raise ValueError("en az bir kademe aktif olmali")
    if not (state.mask >> state.level) & 1:
        raise ValueError("aktif kademe, aktif kademeler arasinda olmali")
    for c in state.codes:
        if c not in protocol.HW_CODES:
            raise ValueError(f"gecersiz donanim kodu: 0x{c:02x}")

    cpi_old = mouse.read_block(protocol.CPI_BLOCK)
    gen_old = mouse.read_block(protocol.GENERAL_BLOCK)
    cpi_new = protocol.encode_cpi_block(cpi_old, state.codes)
    gen_new = bytearray(gen_old)
    gen_new[0] = (gen_old[0] & ~0x07) | state.level
    gen_new[1] = (gen_old[1] & 0xc0) | (state.mask & 0x3f)
    gen_new = bytes(gen_new)

    changed = []
    if cpi_new != cpi_old:
        mouse.write_block(protocol.CPI_BLOCK, cpi_new)
        changed.append((protocol.CPI_BLOCK, cpi_new))
    if gen_new != gen_old:
        mouse.write_block(protocol.GENERAL_BLOCK, gen_new)
        changed.append((protocol.GENERAL_BLOCK, gen_new))
    if not changed:
        return []
    mouse.apply()
    time.sleep(0.05)
    for addr, want in changed:
        got = mouse.read_block(addr)
        if got != want:
            raise RuntimeError(f"dogrulama basarisiz @0x{addr:02x}: yazilan {want.hex()} okunan {got.hex()}")
    return [addr for addr, _ in changed]


class LedConfig:
    def __init__(self, mode=1, speed=2, brightness=4, direction=0, symmetry=0,
                 color_mask=0x7f, colors=None):
        self.mode = mode
        self.speed = speed
        self.brightness = brightness
        self.direction = direction
        self.symmetry = symmetry
        self.color_mask = color_mask
        self.colors = list(colors) if colors else [
            (0, 16, 255), (255, 143, 0), (0, 255, 128),
            (255, 0, 191), (0, 255, 255), (255, 240, 240), (255, 63, 0)
        ]


def read_dpi_colors(mouse):
    """Farenin EEPROM bloklarindan 6 kademenin DPI tekerlek renklerini oku."""
    b20 = mouse.read_block(0x20)
    b28 = mouse.read_block(0x28)
    b30 = mouse.read_block(0x30)
    return protocol.decode_dpi_colors(b20, b28, b30)


def write_dpi_stage_color(mouse, stage, color_rgb):
    """Bir DPI kademesinin rengini hem tekerlek gostergesine hem de EEPROM'a yazar."""
    stage = max(0, min(protocol.STAGES - 1, int(stage)))
    r, g, b = color_rgb

    # Instant A825 active-low PWM (0=tam acik, 15=tam kapali)
    dr_nib = 15 - ((r >> 4) & 0x0f)
    dg_nib = 15 - ((g >> 4) & 0x0f)
    db_nib = 15 - ((b >> 4) & 0x0f)

    # 1. Canli Tekerlek Gostergesi guncellemesi (CMD 0x14)
    b18 = mouse.read_block(protocol.GENERAL_BLOCK)
    active_stage = b18[0] & 7
    if stage == active_stage:
        try:
            mouse.send(protocol.CMD_DPI_STAGE, protocol.dpi_stage_payload(stage, dr_nib, dg_nib, db_nib))
        except Exception as e:
            print(f"Canli DPI tekerlek komutu hatasi: {e}")

    # 2. EEPROM Bloklarini (0x20, 0x28, 0x30) guncelle
    b20 = bytearray(mouse.read_block(0x20))
    b28 = bytearray(mouse.read_block(0x28))
    b30 = bytearray(mouse.read_block(0x30))
    raw18 = bytearray(b20 + b28 + b30[0:2])

    raw18[stage * 3]     = (raw18[stage * 3] & 0xf0) | dr_nib
    raw18[stage * 3 + 1] = (raw18[stage * 3 + 1] & 0xf0) | dg_nib
    raw18[stage * 3 + 2] = (raw18[stage * 3 + 2] & 0xf0) | db_nib

    mouse.write_block(0x20, bytes(raw18[0:8]))
    time.sleep(0.01)
    mouse.write_block(0x28, bytes(raw18[8:16]))
    time.sleep(0.01)
    b30[0] = raw18[16]
    b30[1] = raw18[17]
    mouse.write_block(0x30, bytes(b30))
    time.sleep(0.01)
    mouse.apply()


def read_led(mouse):
    """Farenin EEPROM bloklarindan aydinlatma profilini oku."""
    b18 = mouse.read_block(protocol.GENERAL_BLOCK)
    b30 = mouse.read_block(0x30)
    b38 = mouse.read_block(0x38)
    mode, speed = protocol.decode_led_mode(b18[4], b30[3])
    color_mask = b18[5] & 0x7f

    brightness, direction, symmetry = protocol.decode_led_params(b38)

    b20 = mouse.read_block(0x20)
    b28 = mouse.read_block(0x28)
    colors = protocol.decode_palette(b20, b28, b30, b38)

    return LedConfig(
        mode=mode,
        speed=speed,
        brightness=brightness,
        direction=direction,
        symmetry=symmetry,
        color_mask=color_mask,
        colors=colors,
    )


def write_led(mouse, cfg):
    """Aydinlatma ayarlarini EEPROM bloklarina yazar ve farenin PWM denetleyicisine uygular."""
    mode = cfg.mode
    speed = max(1, cfg.speed & 7)
    brightness = max(0, min(7, cfg.brightness))
    hw_bright = (7 - brightness) & 7
    # Tekil renk bayragi (scolor=1) gerektiren modlar:
    # 0: Tek Renk Nefes (DPI Breathing), 2: Sabit Isik (Static), 4: Mono Water Flow,
    # 5: Comet Tail, 8: Flashing Blink, 12: Key Reactive
    scolor = 1 if mode in (0, 2, 4, 5, 8, 12) else 0

    if mode == 13:  # LED Kapali
        b18 = bytearray(mouse.read_block(protocol.GENERAL_BLOCK))
        b18[4] = 0x87
        b18[5] = 0x00  # Bit 7 = 0 (LED donanimi devre disi)
        mouse.write_block(protocol.GENERAL_BLOCK, bytes(b18))
        time.sleep(0.01)
        live_pkt = [0x00, 0x87, 0x00, 0x07, 0x00, 0x02]
        try:
            mouse.send(protocol.CMD_LED_LIVE, live_pkt)
        except Exception:
            pass
        mouse.apply()
        return

    # 1. Blok 0x18 (Genel ayarlar + LED modu & hizi)
    b18 = bytearray(mouse.read_block(protocol.GENERAL_BLOCK))
    b18[4] = protocol.encode_led_mode(mode, speed)
    b18[5] = 0x80 | (cfg.color_mask & 0x7f)
    mouse.write_block(protocol.GENERAL_BLOCK, bytes(b18))
    time.sleep(0.01)

    # 2. Renk paleti bloklari (0x20, 0x28, 0x30)
    if cfg.colors:
        b20 = bytearray(mouse.read_block(0x20))
        b28 = bytearray(mouse.read_block(0x28))
        b30 = bytearray(mouse.read_block(0x30))
        existing18 = b20 + b28 + b30[0:2]

        # Tekil renk modlarinda tekerlek DPI gostergesini de bu renkle esitle
        dpi_cols = None
        if scolor and cfg.colors:
            dpi_cols = [cfg.colors[0]] * 6
            try:
                active_stage = b18[0] & 7
                r0, g0, b0 = cfg.colors[0]
                dr0 = 15 - ((r0 >> 4) & 0x0f)
                dg0 = 15 - ((g0 >> 4) & 0x0f)
                db0 = 15 - ((b0 >> 4) & 0x0f)
                mouse.send(protocol.CMD_DPI_STAGE, protocol.dpi_stage_payload(active_stage, dr0, dg0, db0))
            except Exception:
                pass

        raw18 = protocol.encode_palette_18(cfg.colors, existing_raw18=existing18, dpi_colors=dpi_cols)
        mouse.write_block(0x20, raw18[0:8])
        time.sleep(0.01)
        mouse.write_block(0x28, raw18[8:16])
        time.sleep(0.01)
        b30[0] = raw18[16]
        b30[1] = raw18[17]
        b30[2] = 0xff
        b30[3] = (0x3f | 0x80) if (8 <= mode <= 11) else 0x3f
        b30[4:8] = b"\x00\x00\x00\x00"
        mouse.write_block(0x30, bytes(b30))
        time.sleep(0.01)

        # 3. Blok 0x38 (SCOLOR, Yon, Simetri, Parlaklik, Tekil Renk / Renk 7)
        b38 = bytearray(mouse.read_block(0x38))
        b38_byte2, b38_b7_bright = protocol.encode_led_params(brightness, cfg.direction, cfg.symmetry, scolor=scolor)
        b38[0:2] = b"\x00\x00"
        b38[2] = b38_byte2
        b38[3:6] = b"\x00\x00\x00"

        if scolor and cfg.colors:
            r_s, g_s, b_s = cfg.colors[0]
            rn = 15 - ((r_s >> 4) & 0x0f)
            gn = 15 - ((g_s >> 4) & 0x0f)
            bn = 15 - ((b_s >> 4) & 0x0f)
            b38[6] = (rn << 4) | gn
            b38[7] = b38_b7_bright | bn
        elif len(cfg.colors) > 6:
            r7, g7, b7 = cfg.colors[6]
            rn7 = 15 - ((r7 >> 4) & 0x0f)
            gn7 = 15 - ((g7 >> 4) & 0x0f)
            bn7 = 15 - ((b7 >> 4) & 0x0f)
            b38[6] = (rn7 << 4) | gn7
            b38[7] = b38_b7_bright | bn7
        else:
            b38[7] = b38_b7_bright | (b38[7] & 0x0f)
        mouse.write_block(0x38, bytes(b38))
        time.sleep(0.01)

    # 4. Canli onizleme paketi (0x13) - Orijinal Windows fcn.00445730 ile birebir uyumlu
    flag = 1 if mode == 12 else 0
    b3 = 0x80 | ((mode & 7) << 4) | (flag << 3) | speed
    b4 = (scolor << 7) | ((cfg.symmetry & 1) << 6) | ((cfg.direction & 3) << 4) | 0x0a
    live_pkt = [0x80 | (cfg.color_mask & 0x7f), b3, b4, hw_bright, 0x00, 0x02]
    try:
        mouse.send(protocol.CMD_LED_LIVE, live_pkt)
    except Exception:
        pass

    # 5. Apply
    time.sleep(0.01)
    mouse.apply()
    time.sleep(0.01)


def live_led_quick(mouse, mode, speed, brightness, scolor=0, symmetry=0, direction=0, color_mask=0x7f):
    """Anlik HID paketi (CMD 0x13): EEPROM yazmadan mikro-saniyede mod/hiz/parlaklik uygular."""
    flag = 1 if mode == 12 else 0
    speed = max(1, speed & 7)
    b3 = 0x80 | ((mode & 7) << 4) | (flag << 3) | speed
    b4 = (scolor << 7) | ((symmetry & 1) << 6) | ((direction & 3) << 4) | 0x0a
    hw_bright = (7 - max(0, min(7, brightness))) & 7
    live_pkt = [0x80 | (color_mask & 0x7f), b3, b4, hw_bright, 0x00, 0x02]
    try:
        mouse.send(protocol.CMD_LED_LIVE, live_pkt)
    except Exception:
        pass


def live_led(mouse, cfg):
    """Anlik canli LED onizlemesi."""
    write_led(mouse, cfg)

