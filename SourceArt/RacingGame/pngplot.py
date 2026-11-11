"""Minimal PNG canvas (no PIL in this Python) for top-down layout previews."""
import zlib, struct


class Canvas:
    def __init__(self, w, h, bg=(250, 250, 245)):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def dot(self, x, y, c, r=1):
        x, y = int(x), int(y)
        for j in range(-r, r + 1):
            for i in range(-r, r + 1):
                xx, yy = x + i, y + j
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    k = 3 * (yy * self.w + xx)
                    self.px[k:k + 3] = bytes(c)

    def line(self, a, b, c, r=1):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
        for i in range(n + 1):
            t = i / n
            self.dot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, c, r)

    def save(self, path):
        raw = b"".join(b"\x00" + bytes(self.px[3 * y * self.w:3 * (y + 1) * self.w]) for y in range(self.h))
        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)) \
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
        open(path, "wb").write(png)
