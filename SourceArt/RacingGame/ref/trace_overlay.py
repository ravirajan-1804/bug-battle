"""Overlay the traced Losail centreline (image px) on the reference screenshot -> ref/overlay.png."""
import sys, zlib, struct
sys.path.insert(0, '..'); sys.path.insert(0, '.')
from pngplot import Canvas

def load(path):
    d = open(path, 'rb').read(); p = 8; idat = b''
    while p < len(d):
        L, = struct.unpack('>I', d[p:p + 4]); t = d[p + 4:p + 8]; c = d[p + 8:p + 8 + L]; p += 12 + L
        if t == b'IHDR': w, h = struct.unpack('>II', c[:8])
        if t == b'IDAT': idat += c
    raw = zlib.decompress(idat); st = w * 4; rows = []; prev = bytearray(st); i = 0
    for y in range(h):
        f = raw[i]; line = bytearray(raw[i + 1:i + 1 + st]); i += 1 + st
        for x in range(st):
            a = line[x - 4] if x >= 4 else 0; b = prev[x]; c = prev[x - 4] if x >= 4 else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c; pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line); prev = line
    return w, h, rows

if __name__ == '__main__':
    from losail_trace import PTS
    w, h, rows = load('ref/losail_ref.png')
    S = 8
    cv = Canvas(w * S, h * S)
    for y in range(h):
        for x in range(w):
            v = rows[y][4 * x]
            for j in range(S):
                k = 3 * ((y * S + j) * w * S + x * S)
                cv.px[k:k + 3 * S] = bytes((v, v, v)) * S
    for a, b in zip(PTS, PTS[1:] + PTS[:1]):
        cv.line((a[0] * S + S / 2, a[1] * S + S / 2), (b[0] * S + S / 2, b[1] * S + S / 2), (230, 30, 30), 1)
    for i, p in enumerate(PTS):
        cv.dot(p[0] * S + S / 2, p[1] * S + S / 2, (0, 120, 255) if i else (0, 200, 0), 3)
    cv.save('ref/overlay.png')
