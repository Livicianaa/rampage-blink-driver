"""hidraw erisim katmani: 30fa:1440 vendor arayuzunu bulup feature report okur/yazar."""
import fcntl
import glob
import time

VENDOR_PRODUCT = "000030FA:00001440"
REPORT_ID = 0x07
RLEN = 8  # descriptor: Report ID 7, Count 7, Size 8 -> 1 + 7 byte


def _IOC(d, t, nr, size):
    return (d << 30) | (size << 16) | (t << 8) | nr


def _HIDIOCSFEATURE(n):
    return _IOC(3, ord('H'), 0x06, n)


def _HIDIOCGFEATURE(n):
    return _IOC(3, ord('H'), 0x07, n)


class DeviceError(Exception):
    pass


class PermissionNeeded(DeviceError):
    """hidraw node root-only; udev kurali ya da sudo gerekiyor."""


def find_path():
    """Vendor feature arayuzunu (Report ID 0x07 iceren) dondur, yoksa None."""
    for path in sorted(glob.glob("/dev/hidraw*")):
        name = path.rsplit("/", 1)[-1]
        try:
            with open(f"/sys/class/hidraw/{name}/device/uevent") as f:
                if VENDOR_PRODUCT not in f.read():
                    continue
            with open(f"/sys/class/hidraw/{name}/device/report_descriptor", "rb") as f:
                desc = f.read()
        except OSError:
            continue
        if b"\x85\x07" in desc:  # Report ID 7
            return path
    return None


class Mouse:
    def __init__(self, path=None):
        self.path = path or find_path()
        if not self.path:
            raise DeviceError("Blink faresi bulunamadi (30fa:1440 feature arayuzu yok).")
        try:
            self._f = open(self.path, "wb+", buffering=0)
        except PermissionError as e:
            raise PermissionNeeded(str(e)) from e

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass

    def reconnect(self):
        self.close()
        new_path = None
        for _ in range(5):
            new_path = find_path()
            if new_path:
                break
            time.sleep(0.1)
        if not new_path:
            raise DeviceError("Blink faresi bulunamadi.")
        self.path = new_path
        try:
            self._f = open(self.path, "wb+", buffering=0)
        except PermissionError as e:
            raise PermissionNeeded(str(e)) from e

    def _ioctl(self, req, buf):
        if not getattr(self, "_f", None) or self._f.closed:
            self.reconnect()
        try:
            return fcntl.ioctl(self._f, req, buf)
        except OSError as e:
            if e.errno in (19, 5):  # ENODEV, EIO (cihaz cikarilip takildi)
                time.sleep(0.1)
                self.reconnect()
                return fcntl.ioctl(self._f, req, buf)
            raise

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def send(self, cmd, payload=()):
        buf = bytearray(RLEN)
        buf[0] = REPORT_ID
        buf[1] = cmd & 0xff
        for i, b in enumerate(bytes(payload)[:6]):
            buf[2 + i] = b & 0xff
        self._ioctl(_HIDIOCSFEATURE(RLEN), bytes(buf))
        return bytes(buf)

    def send_raw(self, data):
        buf = bytearray(RLEN)
        for i, b in enumerate(bytes(data)[:RLEN]):
            buf[i] = b & 0xff
        buf[0] = REPORT_ID
        self._ioctl(_HIDIOCSFEATURE(RLEN), bytes(buf))
        return bytes(buf)

    def get(self):
        buf = bytearray(RLEN)
        buf[0] = REPORT_ID
        self._ioctl(_HIDIOCGFEATURE(RLEN), buf)
        return bytes(buf)

    def read_addr(self, bank, index, count):
        """exe fcn.00425db0: 0x18 ile adres sec -> GetFeature -> cevap byte[1]."""
        sel = bytes([REPORT_ID, 0x18, 0x05, index & 0xff,
                     bank & 0xff, (bank >> 8) & 0xff, 0x00, (count - 1) & 0xff])
        self._ioctl(_HIDIOCSFEATURE(RLEN), sel)
        buf = bytearray(RLEN)
        buf[0] = REPORT_ID
        self._ioctl(_HIDIOCGFEATURE(RLEN), buf)
        return buf[1]

    def dump(self, bank, count):
        return [self.read_addr(bank, i, count) for i in range(count)]

    def _cmd18(self, flags, index, addr, value, count_m1):
        pkt = bytes([REPORT_ID, 0x18, flags & 0xff, index & 0xff,
                     addr & 0xff, (addr >> 8) & 0xff, value & 0xff, count_m1 & 0xff])
        self._ioctl(_HIDIOCSFEATURE(RLEN), pkt)
        time.sleep(0.002)

    def read_block(self, addr, count=8):
        """exe fcn.00425db0 dizisi: stage-init, adres sec + GetFeature, sonlandir."""
        for i in range(count):
            self._cmd18(0x03, i, addr, 0, count - 1)
        time.sleep(0.002)
        self._cmd18(0x00, 0, addr, 0, 0)
        out = []
        for i in range(count):
            self._cmd18(0x05, i, addr, 0, count - 1)
            buf = bytearray(RLEN)
            buf[0] = REPORT_ID
            self._ioctl(_HIDIOCGFEATURE(RLEN), buf)
            out.append(buf[1])
        time.sleep(0.002)
        self._cmd18(0x00, 0, 0, 0, 0)
        return bytes(out)

    def read_mem(self, start, length):
        """Config belleginden 8 byte'lik bloklarla oku (yalniz okuma)."""
        data = bytearray()
        for addr in range(start, start + length, 8):
            data += self.read_block(addr, 8)
        return bytes(data)

    def apply(self):
        """exe fcn.00425f30: 0x18 bayrak 0x10 (config'i uygula), 5 ms, sonlandir."""
        self._cmd18(0x10, 0, 0, 0, 0)
        time.sleep(0.005)
        self._cmd18(0x00, 0, 0, 0, 0)

    def write_block(self, addr, data8):
        """exe fcn.00425e80: her byte'i stage et (0x03), commit (0x09), sonlandir."""
        data8 = bytes(data8)
        assert len(data8) == 8
        for i in range(8):
            self._cmd18(0x03, i, addr, data8[i], 7)
        time.sleep(0.004)
        self._cmd18(0x09, 0, addr, 0, 7)
        time.sleep(0.002)
        self._cmd18(0x00, 0, addr, 0, 0)
