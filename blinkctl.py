#!/usr/bin/env python3
"""blinkctl - Blink (Wuxi Instant 30fa:1440) gaming mouse Linux CLI.

Erisim: 99-blink-mouse.rules kuruluysa sudo gerekmez (fareyi bir kez cikar-tak).
"""
import sys
import os

sys.dont_write_bytecode = True
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blink import device, protocol

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yedekler")


def hexs(b):
    return " ".join(f"{x:02x}" for x in b)


def fmt_code(c):
    cpi = protocol.hw_to_cpi(c)
    return f"0x{c:02x}" + (f" (~{cpi} CPI)" if cpi else " (CPI dogrulanacak)")


def show_dpi(m):
    cpi_blk = m.read_block(protocol.CPI_BLOCK)
    gen_blk = m.read_block(protocol.GENERAL_BLOCK)
    codes = protocol.decode_cpi_block(cpi_blk)
    gen = protocol.decode_general(gen_blk)
    print(f"0x{protocol.CPI_BLOCK:03x}: {hexs(cpi_blk)}")
    print(f"0x{protocol.GENERAL_BLOCK:03x}: {hexs(gen_blk)}")
    print(f"aktif kademe = {gen['level']}  |  aktif maskesi = {gen['enable_mask']:06b}")
    hz = gen["poll_hz"]
    print(f"tarama hizi = {str(hz) + ' Hz' if hz else 'bilinmeyen kod 0x%02x' % gen['poll_code']}"
          f"  |  ates suresi = {gen['fire_time']} ms")
    for i, c in enumerate(codes):
        on = "A" if (gen["enable_mask"] >> i) & 1 else "-"
        cur = "<- AKTIF" if i == gen["level"] else ""
        print(f"  kademe {i} [{on}] {fmt_code(c)} {cur}")


def backup(m, tag):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    data = m.read_mem(0, 0xA0)
    path = os.path.join(BACKUP_DIR, f"config-{tag}-{datetime.now():%Y%m%d-%H%M%S}.bin")
    with open(path, "wb") as f:
        f.write(data)
    return path


def cmd_setcpi(m, args):
    if not 0 <= args.stage < protocol.STAGES:
        sys.exit("kademe 0..5 olmali")
    if args.code not in protocol.HW_CODES:
        sys.exit("gecersiz donanim kodu (0x01..0x18, 0x0b yok)")
    old = m.read_block(protocol.CPI_BLOCK)
    codes = protocol.decode_cpi_block(old)
    new_codes = list(codes)
    new_codes[args.stage] = args.code
    new = protocol.encode_cpi_block(old, new_codes)
    print(f"kademe {args.stage}: {fmt_code(codes[args.stage])} -> {fmt_code(args.code)}")
    print(f"blok 0x{protocol.CPI_BLOCK:03x}: {hexs(old)}  ->  {hexs(new)}")
    if not args.yes:
        print("KURU CALISMA: yazilmadi. Yazmak icin --yes ekle.")
        return
    path = backup(m, "setcpi-oncesi")
    print(f"yedek: {path}")
    m.write_block(protocol.CPI_BLOCK, new)
    if not args.no_apply:
        m.apply()
    time.sleep(0.05)
    check = m.read_block(protocol.CPI_BLOCK)
    if check == new:
        print(f"yazildi ve dogrulandi: {hexs(check)}")
    else:
        print(f"UYARI: geri okuma farkli: {hexs(check)}")
        print("Geri almak icin: blinkctl.py restore --file", path, "--addr 0x10")


def cmd_tune(m, args):
    old = m.read_block(protocol.CPI_BLOCK)
    codes = protocol.decode_cpi_block(old)
    cur = codes[args.stage]
    idx = protocol.HW_CODES.index(cur)
    print(f"yedek: {backup(m, 'tune-oncesi')}")
    print("+ = hizlandir, - = yavaslat, Enter/q = bu degerde kal\n")
    while True:
        print(f"kademe {args.stage}: {fmt_code(protocol.HW_CODES[idx])}")
        key = input("[+/-/q] > ").strip().lower()
        if key in ("", "q"):
            break
        if key == "+" and idx < len(protocol.HW_CODES) - 1:
            idx += 1
        elif key == "-" and idx > 0:
            idx -= 1
        else:
            continue
        blk = m.read_block(protocol.CPI_BLOCK)
        new_codes = protocol.decode_cpi_block(blk)
        new_codes[args.stage] = protocol.HW_CODES[idx]
        m.write_block(protocol.CPI_BLOCK, protocol.encode_cpi_block(blk, new_codes))
        m.apply()
        time.sleep(0.05)
    print(f"son deger: kademe {args.stage} = {fmt_code(protocol.HW_CODES[idx])}")


def poke_byte(m, addr, value):
    base, off = addr & ~7, addr & 7
    blk = bytearray(m.read_block(base))
    blk[off] = value & 0xff
    m.write_block(base, bytes(blk))
    m.apply()
    time.sleep(0.05)
    return m.read_block(base)[off]


def check_addr(addr, force):
    if not 0 <= addr < 0xA0:
        sys.exit("adres 0x00..0x9f araliginda olmali")
    if addr < 8 and not force:
        sys.exit("0x00..0x07 baslik blogu: --force olmadan yazilmaz")


def cmd_poke(m, args):
    check_addr(args.addr, args.force)
    base, off = args.addr & ~7, args.addr & 7
    old = m.read_block(base)
    new = bytearray(old)
    new[off] = args.value & 0xff
    print(f"blok 0x{base:03x}: {hexs(old)}  ->  {hexs(new)}")
    if not args.yes:
        print("KURU CALISMA: yazilmadi. Yazmak icin --yes ekle.")
        return
    print(f"yedek: {backup(m, 'poke-oncesi')}")
    got = poke_byte(m, args.addr, args.value)
    print("yazildi ve dogrulandi" if got == args.value & 0xff else f"UYARI: geri okunan 0x{got:02x}")


def cmd_slotmap(m, args):
    import select
    import struct
    import dpi_olc

    ev = dpi_olc.find_event()
    if not ev:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        f = open(ev, "rb", buffering=0)
    except PermissionError:
        sys.exit("event aygitina erisim icin sudo ile calistir.")
    size = struct.calcsize(dpi_olc.FMT)
    base = 0x08
    buttons = [("ORTA tus (tekerlek tiki)", 0x112), ("SAG tus", 0x111),
               ("ARKA yan tus", 0x113), ("ON yan tus", 0x114)]
    print(f"yedek: {backup(m, 'slotmap-oncesi')}")
    print("Her slot gecici olarak SOL TIK yapilir; sirayla sorulan tusa bir kez bas, sonra Enter.")
    print("Sol tus dokunulmaz. Her slot kendiliginden geri yazilir.\n")

    def capture():
        codes = []
        while True:
            ready = select.select([f, sys.stdin], [], [])[0]
            if f in ready:
                data = f.read(size)
                if len(data) == size:
                    _, _, et, c, val = struct.unpack(dpi_olc.FMT, data)
                    if et == 1 and val == 1:
                        codes.append(c)
            if sys.stdin in ready:
                sys.stdin.readline()
                return codes

    summary = {}
    for slot in (2, 3, 4, 5):
        addr = base + slot - 1
        orig = m.read_block(base)[slot - 1]
        poke_byte(m, addr, 0x21)
        found = []
        try:
            for name, std in buttons:
                print(f"[slot {slot}] {name}'e bas, sonra Enter: ", end="", flush=True)
                codes = capture()
                got = codes[0] if codes else None
                print(f"   -> 0x{got:03x}" if got else "   -> basilmadi")
                if got == 0x110:
                    found.append(name)
        finally:
            restored = poke_byte(m, addr, orig)
            print(f"[slot {slot}] geri yazildi: 0x{restored:02x}\n")
        summary[slot] = found
    print("=== SONUC ===")
    for slot, found in summary.items():
        print(f"slot {slot} (adres 0x{base + slot - 1:02x}) -> {', '.join(found) if found else 'eslesme bulunamadi'}")


def cmd_fnprobe(m, args):
    import select
    import struct
    import dpi_olc

    ev = dpi_olc.find_event()
    if not ev:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        f = open(ev, "rb", buffering=0)
    except PermissionError:
        sys.exit("event aygitina erisim icin sudo ile calistir.")
    size = struct.calcsize(dpi_olc.FMT)
    slot_addr = 0x08 + args.slot - 1
    codes = [int(x, 0) for x in args.codes.split(",")]
    orig_key = m.read_block(0x08)[args.slot - 1]
    gen = m.read_block(protocol.GENERAL_BLOCK)
    stages = protocol.decode_cpi_block(m.read_block(protocol.CPI_BLOCK))
    print(f"yedek: {backup(m, 'fnprobe-oncesi')}")
    print(f"kademe CPI kodlari: {[hex(c) for c in stages]}; testte kademe 0 ve 4 acik olacak\n")

    def sweep(label, seconds):
        input(f"{label}: Enter'a bas, SONRA {seconds} sn boyunca fareyi sol-saga HIZLI ve duzgun salla... ")
        end = time.monotonic() + seconds
        total, keys = 0, []
        while time.monotonic() < end:
            if select.select([f], [], [], 0.05)[0]:
                data = f.read(size)
                if len(data) == size:
                    _, _, et, c, val = struct.unpack(dpi_olc.FMT, data)
                    if et == dpi_olc.EV_REL and c in (dpi_olc.REL_X, dpi_olc.REL_Y):
                        total += abs(val)
                    elif et == 1 and val == 1:
                        keys.append(c)
        return total, keys

    results = []
    try:
        poke_byte(m, protocol.GENERAL_BLOCK + 1, 0x11)
        for code in codes:
            poke_byte(m, slot_addr, 0x20 | code)
            print(f"\n=== fonksiyon 0x{code:02x} slot {args.slot}'e yazildi ===")
            a, _ = sweep("A turu (tusa basmadan once)", 3)
            print("   simdi arka/yan tusa BIR KEZ bas:")
            _, pressed = sweep("tus basisi (fareyi oynatmadan sadece tusa bas)", 2)
            b, _ = sweep("B turu (tusa bastiktan sonra, ayni sekilde)", 3)
            ratio = b / a if a else 0
            names = ", ".join(f"0x{k:03x}" for k in pressed) or "HIC OLAY GELMEDI"
            print(f"   A={a}  B={b}  oran B/A={ratio:.2f}   tus olayi: {names}")
            results.append((code, a, b, ratio, pressed))
    finally:
        poke_byte(m, slot_addr, orig_key)
        poke_byte(m, protocol.GENERAL_BLOCK + 1, gen[1])
        poke_byte(m, protocol.GENERAL_BLOCK, gen[0])
        print(f"\ngeri yazildi: tus 0x{orig_key:02x}, maske 0x{gen[1]:02x}, aktif kademe baytı 0x{gen[0]:02x}")
    print("\n=== SONUC ===")
    for code, a, b, ratio, pressed in results:
        verdict = "DPI DEGISTI" if ratio > 1.4 or (0 < ratio < 0.7) else "belirsiz (oran 1 civari)"
        ev_txt = "olay gelmedi" if not pressed else "olay geldi"
        print(f"fonksiyon 0x{code:02x}: oran {ratio:.2f} -> {verdict}; tus {ev_txt}")


def cmd_fnscan(m, args):
    import select
    import struct
    import dpi_olc

    paths = dpi_olc.find_events()
    if not paths:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        files = {p: open(p, "rb", buffering=0) for p in paths}
    except PermissionError:
        sys.exit("event aygitlarina erisim icin sudo ile calistir.")
    size = struct.calcsize(dpi_olc.FMT)
    slot_addr = 0x08 + args.slot - 1
    orig = m.read_block(0x08)[args.slot - 1]
    print(f"yedek: {backup(m, 'fnscan-oncesi')}")
    print(f"dinlenen aygitlar: {', '.join(paths)}")
    print("Her kod arka tusa yazilir; tusa BIR KEZ bas ve Enter. Olay yoksa sadece Enter.\n")

    def capture():
        events = []
        while True:
            ready = select.select(list(files.values()) + [sys.stdin], [], [])[0]
            for p, fh in files.items():
                if fh in ready:
                    data = fh.read(size)
                    if len(data) == size:
                        _, _, et, c, val = struct.unpack(dpi_olc.FMT, data)
                        if et == 1 and val == 1:
                            events.append((p.rsplit("/", 1)[1], "KEY", c))
                        elif et == 2 and c in (6, 8, 11):
                            events.append((p.rsplit("/", 1)[1], "REL", c))
            if sys.stdin in ready:
                sys.stdin.readline()
                return events

    results = {}
    try:
        for code in range(args.start, args.end + 1):
            poke_byte(m, slot_addr, 0x20 | code)
            print(f"[0x{code:02x}] arka tusa bas, sonra Enter: ", end="", flush=True)
            ev = capture()
            txt = ", ".join(f"{n}:{t}{c:#x}" for n, t, c in ev) or "olay yok"
            print(f"   -> {txt}")
            results[code] = ev
    finally:
        got = poke_byte(m, slot_addr, orig)
        print(f"\ngeri yazildi: 0x{got:02x}")
    print("\n=== OZET (kod -> olaylar) ===")
    for code, ev in results.items():
        txt = ", ".join(f"{n}:{t}{c:#x}" for n, t, c in ev) or "olay yok (fare icinde islendi/islevsiz)"
        print(f"0x{code:02x}: {txt}")


def cmd_setpoll(m, args):
    if args.hz not in protocol.HZ_POLL:
        sys.exit("hiz 125, 250, 500 veya 1000 olmali")
    code = protocol.HZ_POLL[args.hz]
    cur = m.read_block(protocol.GENERAL_BLOCK)[6]
    print(f"tarama hizi: {protocol.POLL_HZ.get(cur, '0x%02x' % cur)} -> {args.hz} Hz (kod 0x{cur:02x} -> 0x{code:02x})")
    if not args.yes:
        print("KURU CALISMA: yazilmadi. Yazmak icin --yes ekle.")
        return
    print(f"yedek: {backup(m, 'setpoll-oncesi')}")
    got = poke_byte(m, protocol.POLL_ADDR, code)
    print("yazildi ve dogrulandi" if got == code else f"UYARI: geri okunan 0x{got:02x}")


def cmd_explore(m, args):
    check_addr(args.addr, args.force)
    orig = m.read_block(args.addr & ~7)[args.addr & 7]
    cur = orig
    print(f"yedek: {backup(m, 'explore-oncesi')}")
    print(f"adres 0x{args.addr:02x}, baslangic degeri 0x{orig:02x} ({orig:08b})")
    print("+/-: +-1   ++/--: +-16   =HH: hex deger   r: ilk degere don   q: bu degerde kal\n")
    while True:
        key = input(f"[0x{cur:02x} {cur:08b}] > ").strip().lower()
        if key in ("q", ""):
            break
        if key == "r":
            cur = orig
        elif key == "+":
            cur = (cur + 1) & 0xff
        elif key == "-":
            cur = (cur - 1) & 0xff
        elif key == "++":
            cur = (cur + 16) & 0xff
        elif key == "--":
            cur = (cur - 16) & 0xff
        elif key.startswith("="):
            try:
                cur = int(key[1:], 16) & 0xff
            except ValueError:
                continue
        else:
            continue
        got = poke_byte(m, args.addr, cur)
        if got != cur:
            print(f"  UYARI: geri okunan 0x{got:02x}")
    print(f"son deger: 0x{cur:02x} (ilk deger 0x{orig:02x})")


def set_stage_code(m, stage, code):
    blk = m.read_block(protocol.CPI_BLOCK)
    codes = protocol.decode_cpi_block(blk)
    codes[stage] = code
    m.write_block(protocol.CPI_BLOCK, protocol.encode_cpi_block(blk, codes))
    m.apply()
    time.sleep(0.05)


def cmd_calibrate(m, args):
    import json
    import select
    import struct
    import dpi_olc

    ev = dpi_olc.find_event()
    if not ev:
        sys.exit("Fare event aygiti bulunamadi.")
    try:
        f = open(ev, "rb", buffering=0)
    except PermissionError:
        sys.exit("event aygitina erisim icin sudo ile calistir.")
    size = struct.calcsize(dpi_olc.FMT)
    inch = args.cm / 2.54
    codes = [int(x, 0) for x in args.codes.split(",")]
    orig = protocol.decode_cpi_block(m.read_block(protocol.CPI_BLOCK))[args.stage]
    print(f"yedek: {backup(m, 'calibrate-oncesi')}")
    print(f"kademe {args.stage} bitince eski degerine (0x{orig:02x}) donecek.")

    def drain():
        while select.select([f], [], [], 0)[0]:
            f.read(size)

    results = {}
    try:
        for code in codes:
            set_stage_code(m, args.stage, code)
            input(f"\n[0x{code:02x}] yazildi. Fareyi baslangica koy, Enter'a bas, sonra {args.cm:g} cm duz sur, bitince Enter: ")
            drain()
            dx = dy = 0
            print("  sayiyor...")
            while True:
                ready = select.select([f, sys.stdin], [], [])[0]
                if f in ready:
                    data = f.read(size)
                    if len(data) == size:
                        _, _, et, c, val = struct.unpack(dpi_olc.FMT, data)
                        if et == dpi_olc.EV_REL and c == dpi_olc.REL_X:
                            dx += val
                        elif et == dpi_olc.EV_REL and c == dpi_olc.REL_Y:
                            dy += val
                if sys.stdin in ready:
                    sys.stdin.readline()
                    break
            major = max(abs(dx), abs(dy))
            skew = min(abs(dx), abs(dy)) / major if major else 0
            cpi = major / inch
            known = protocol.hw_to_cpi(code)
            extra = f"  beklenen {known}, oran {cpi / known:.2f}" if known else ""
            warn = "  UYARI: cizgi duz degildi" if skew > 0.1 else ""
            print(f"  olculen ~{cpi:.0f} CPI (X={dx} Y={dy}){extra}{warn}")
            results[f"0x{code:02x}"] = {"counts": major, "cm": args.cm, "cpi": round(cpi), "skew": round(skew, 3)}
    finally:
        set_stage_code(m, args.stage, orig)
        print(f"\neski deger geri yazildi: 0x{orig:02x}")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    out = os.path.join(BACKUP_DIR, f"kalibrasyon-{datetime.now():%Y%m%d-%H%M%S}.json")
    with open(out, "w") as fh:
        json.dump(results, fh, indent=1)
    print(f"sonuclar: {out}")
    for k, v in results.items():
        print(f"  {k}: ~{v['cpi']} CPI")


def cmd_restore(m, args):
    with open(args.file, "rb") as f:
        data = f.read()
    if args.addr + 8 > len(data):
        sys.exit("adres yedek dosyasinin disinda")
    blk = data[args.addr:args.addr + 8]
    print(f"0x{args.addr:03x} <- {hexs(blk)}")
    if not args.yes:
        print("KURU CALISMA: yazilmadi. Yazmak icin --yes ekle.")
        return
    m.write_block(args.addr, blk)
    m.apply()
    time.sleep(0.05)
    print("geri okuma:", hexs(m.read_block(args.addr)))


def cmd_profile(m, args):
    from blink import profile
    if args.set is not None:
        changed = profile.write_profile(m, args.set)
        print(f"profil {args.set} ({profile.PROFILES[args.set]}) olarak ayarlandi" if changed else "zaten aktif profil")
    else:
        p = profile.read_profile(m)
        print(f"aktif profil: {p} ({profile.PROFILES[p]})")


def cmd_keys(m, args):
    from blink import keys, profile
    p = profile.read_profile(m)
    curr = keys.read_keys(m, profile=p)
    print(f"Profil {p} ({profile.PROFILES[p]}) tus haritasi:")
    for i, (raw, code) in enumerate(curr):
        sname = keys.SLOT_NAMES.get(i + 1, f"Tus {i+1}")
        fname = keys.FUNCTIONS.get(code, f"Ozel (0x{code:02x})")
        print(f"  Slot {i+1} [{sname}]: {fname} (ham: 0x{raw:02x})")


def cmd_led(m, args):
    from blink import config, protocol
    cfg = config.read_led(m)
    if args.off:
        cfg.mode = 13
        config.write_led(m, cfg)
        print("LED kapatildi.")
        return
    if args.on:
        if cfg.mode == 13:
            cfg.mode = 1
        config.write_led(m, cfg)
        print(f"LED acildi: {protocol.LED_MODE_NAMES.get(cfg.mode, cfg.mode)}")
        return

    modified = False
    if args.mode is not None:
        cfg.mode = args.mode
        modified = True
    if args.speed is not None:
        cfg.speed = max(0, min(7, args.speed))
        modified = True
    if args.brightness is not None:
        cfg.brightness = max(0, min(7, args.brightness))
        modified = True
    if args.direction is not None:
        cfg.direction = max(0, min(3, args.direction))
        modified = True
    if args.symmetry is not None:
        cfg.symmetry = 1 if args.symmetry else 0
        modified = True

    if modified:
        config.write_led(m, cfg)
        print("Aydinlatma ayari uygulandi.")

    mname = protocol.LED_MODE_NAMES.get(cfg.mode, f"Bilinmeyen (0x{cfg.mode:02x})")
    dname = protocol.LED_DIRECTION_NAMES.get(cfg.direction, f"Yon {cfg.direction}")
    print("LED Durumu:")
    print(f"  Mod:        {cfg.mode} ({mname})")
    print(f"  Hiz:        {cfg.speed + 1} / 8")
    print(f"  Parlaklik:  {cfg.brightness} / 7")
    print(f"  Yon:        {dname}")
    print(f"  Simetri:    {'Acik' if cfg.symmetry else 'Kapali'}")
    print(f"  Renk Maske: {cfg.color_mask:07b}")
    print("  Renkler:")
    for i, c in enumerate(cfg.colors):
        en = "+" if (cfg.color_mask >> i) & 1 else "-"
        print(f"    Renk {i+1} [{en}]: RGB{c} (#{c[0]:02x}{c[1]:02x}{c[2]:02x})")


def main():
    ap = argparse.ArgumentParser(description="Blink mouse kontrol (CLI)")
    ap.add_argument("--dev", help="hidraw yolu (bos=otomatik bul)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find", help="cihazi bul")
    sub.add_parser("get", help="mevcut feature report'u oku")
    sub.add_parser("dpi", help="kademe CPI kodlari ve aktif kademe (sadece okuma)")
    mm = sub.add_parser("mem", help="config bellegini oku (sadece okuma)")
    mm.add_argument("--start", type=lambda x: int(x, 0), default=0)
    mm.add_argument("--len", dest="length", type=lambda x: int(x, 0), default=0xA0)
    mm.add_argument("--save", help="ham baytlari bu dosyaya yedekle")
    sc = sub.add_parser("setcpi", help="bir kademenin CPI kodunu degistir (varsayilan kuru)")
    sc.add_argument("--stage", type=int, required=True)
    sc.add_argument("--code", type=lambda x: int(x, 0), required=True)
    sc.add_argument("--yes", action="store_true", help="gercekten yaz")
    sc.add_argument("--no-apply", action="store_true", help="apply (0x10) gonderme")
    tn = sub.add_parser("tune", help="CPI kodunu +/- tuslariyla canli ayarla")
    tn.add_argument("--stage", type=int, default=4)
    pk = sub.add_parser("poke", help="tek bayt yaz (varsayilan kuru)")
    pk.add_argument("--addr", type=lambda x: int(x, 0), required=True)
    pk.add_argument("--value", type=lambda x: int(x, 0), required=True)
    pk.add_argument("--yes", action="store_true")
    pk.add_argument("--force", action="store_true")
    sub.add_parser("slotmap", help="hangi slot hangi fiziksel tusu yonetir (rehberli test, sudo gerekir)")
    prof_p = sub.add_parser("profile", help="aktif profili oku veya ayarla")
    prof_p.add_argument("--set", type=int, choices=[0, 1, 2, 3], help="aktif profil (0: Ofis, 1..3: Oyun I..III)")
    sub.add_parser("keys", help="mevcut tus atamalarini goster")
    lp = sub.add_parser("led", help="LED aydinlatma durumunu goster veya ayarla")
    lp.add_argument("--mode", type=int, choices=range(14), help="LED modu (0..13)")
    lp.add_argument("--speed", type=int, choices=range(8), help="Hiz (0..7)")
    lp.add_argument("--brightness", type=int, choices=range(16), help="Parlaklik (0..15)")
    lp.add_argument("--direction", type=int, choices=range(4), help="Yon (0..3)")
    lp.add_argument("--symmetry", type=int, choices=[0, 1], help="Simetri (0 veya 1)")
    lp.add_argument("--on", action="store_true", help="LED'i ac")
    lp.add_argument("--off", action="store_true", help="LED'i kapat")
    fs = sub.add_parser("fnscan", help="tum fonksiyon kodlarini tara, hangi olay geliyor (sudo gerekir)")
    fs.add_argument("--slot", type=int, default=4)
    fs.add_argument("--start", type=lambda x: int(x, 0), default=0x07)
    fs.add_argument("--end", type=lambda x: int(x, 0), default=0x1f)
    fp = sub.add_parser("fnprobe", help="DPI fonksiyon kodlarini objektif ol (sudo gerekir)")
    fp.add_argument("--slot", type=int, default=4)
    fp.add_argument("--codes", default="0x06,0x0b,0x0c")
    sp = sub.add_parser("setpoll", help="USB tarama hizini ayarla (varsayilan kuru)")
    sp.add_argument("--hz", type=int, required=True)
    sp.add_argument("--yes", action="store_true")
    ex = sub.add_parser("explore", help="tek bayti +/- ile oynat, fiziksel sonucu gozle")
    ex.add_argument("--addr", type=lambda x: int(x, 0), required=True)
    ex.add_argument("--force", action="store_true")
    cl = sub.add_parser("calibrate", help="kod -> gercek CPI olcumu (sudo gerekir)")
    cl.add_argument("--stage", type=int, default=4)
    cl.add_argument("--cm", type=float, default=29.7)
    cl.add_argument("--codes", default="0x05,0x0d,0x0e,0x0f,0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18")
    rs = sub.add_parser("restore", help="yedek dosyasindan bir blogu geri yaz")
    rs.add_argument("--file", required=True)
    rs.add_argument("--addr", type=lambda x: int(x, 0), required=True)
    rs.add_argument("--yes", action="store_true")
    r = sub.add_parser("raw", help="ham gonder: cmd p0..p5 (hex/ondalik)")
    r.add_argument("bytes", nargs="+")

    args = ap.parse_args()

    if args.cmd == "find":
        print(device.find_path() or "Cihaz bulunamadi")
        return

    try:
        m = device.Mouse(args.dev)
    except device.PermissionNeeded:
        sys.exit("Erisim yok: 99-blink-mouse.rules kur ya da sudo ile calistir.")
    except device.DeviceError as e:
        sys.exit(str(e))

    with m:
        if args.cmd == "get":
            print(hexs(m.get()))
        elif args.cmd == "dpi":
            show_dpi(m)
        elif args.cmd == "mem":
            data = m.read_mem(args.start, args.length)
            for row in range(0, len(data), 8):
                print(f"0x{args.start + row:03x}: {hexs(data[row:row + 8])}")
            if args.save:
                with open(args.save, "wb") as f:
                    f.write(data)
                print(f"yedek yazildi: {args.save}")
        elif args.cmd == "setcpi":
            cmd_setcpi(m, args)
        elif args.cmd == "tune":
            cmd_tune(m, args)
        elif args.cmd == "poke":
            cmd_poke(m, args)
        elif args.cmd == "slotmap":
            cmd_slotmap(m, args)
        elif args.cmd == "fnprobe":
            cmd_fnprobe(m, args)
        elif args.cmd == "fnscan":
            cmd_fnscan(m, args)
        elif args.cmd == "setpoll":
            cmd_setpoll(m, args)
        elif args.cmd == "explore":
            cmd_explore(m, args)
        elif args.cmd == "calibrate":
            cmd_calibrate(m, args)
        elif args.cmd == "restore":
            cmd_restore(m, args)
        elif args.cmd == "profile":
            cmd_profile(m, args)
        elif args.cmd == "keys":
            cmd_keys(m, args)
        elif args.cmd == "led":
            cmd_led(m, args)
        elif args.cmd == "raw":
            vals = [int(x, 0) for x in args.bytes]
            print("gonderildi:", hexs(m.send(vals[0], vals[1:])))


if __name__ == "__main__":
    main()
