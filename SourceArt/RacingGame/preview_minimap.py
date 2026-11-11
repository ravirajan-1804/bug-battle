"""Offline look-dev for WBP_RG_Minimap: renders minimap_dsl.STATIC plus sample racer dots and the
player arrow over a garden-coloured backdrop -> minimap_preview.png (text drawn as grey bars)."""
import json, math, os, sys, io, contextlib
import numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    import minimap_dsl as M
from pngplot import Canvas

S = 4                                   # pixels per map unit
W, H = int(M.W), int(M.H)
PAD = 30
img = np.zeros(((H + 2 * PAD) * S, (W + 2 * PAD) * S, 3))
yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
img[:] = (0.42, 0.52, 0.30)                                    # garden-ish backdrop
img[yy > img.shape[0] * 0.55] = (0.55, 0.52, 0.47)             # road-ish lower half
X = xx / S - PAD
Y = yy / S - PAD


def blend(mask, c):
    a = mask[..., None] * c[3]
    img[:] = img * (1 - a) + np.array(c[:3]) * a


def seg(a, b, t):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1e-9
    u = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
    d = np.hypot(X - (ax + u * dx), Y - (ay + u * dy))
    return np.clip(t / 2 - d + 0.5 / S * S / 2, 0, 1) if False else np.clip((t / 2 - d) * S + 0.5, 0, 1)


def poly(pts, t, c):
    m = np.zeros(X.shape)
    for a, b in zip(pts, pts[1:]):
        m = np.maximum(m, seg(a, b, t))
    blend(m, c)


defs = json.load(open(os.path.join(M.HERE, "minimap_defaults.json")))
arrays = {k: [(p["x"], p["y"]) for p in v] for k, v in defs.items() if k.startswith("Track")}
for p in M.STATIC:
    if p[0] == "poly":
        poly(arrays[p[1]], p[2], p[3])
    elif p[0] == "line":
        poly([p[1], p[2]], p[3], p[4])
    elif p[0] == "scan":   # one non-overlapping row of a glass panel
        (xa, y), (xb, _) = p[1], p[2]
        blend(((np.abs(Y - y) <= p[3] / 2) & (X >= xa) & (X <= xb)).astype(float), p[4])
    else:
        x, y = p[2]
        poly([(x, y + p[3] * 0.6), (x + 0.6 * p[3] * len(p[1]), y + p[3] * 0.6)], p[3] * 0.8, (0.8, 0.8, 0.8, 1))


def disc(c, r, col):
    blend(np.clip((r - np.hypot(X - c[0], Y - c[1])) * S + 0.5, 0, 1), col)


tp = arrays["TrackPoints"]
for k, i in enumerate((20, 60, 95, 130, 170, 210)):
    c = tp[i]
    disc(c, M.RACER_R + M.RACER_RIM, (1, 1, 1, 1))
    disc(c, M.RACER_R, M.RACER_COLORS[(k + 1) % 7] + (1,))
# player arrow at sample 240 heading along the track
i = 240
p, q = tp[i], tp[i + 2]
h = math.atan2(q[1] - p[1], q[0] - p[0])
f = (math.cos(h), math.sin(h)); r = (-f[1], f[0])
P = lambda a, b: (p[0] + f[0] * a + r[0] * b, p[1] + f[1] * a + r[1] * b)
pc = M.RACER_COLORS[0] + (1,)
ring = [(p[0] + M.HALO_R * math.cos(t), p[1] + M.HALO_R * math.sin(t)) for t in np.linspace(0, 2 * math.pi, M.HALO_SEGS + 1)]
poly(ring, 1.6, pc)
tip, bl, nt, br = P(M.TIP, 0), P(M.BACK, M.HALF), P(M.NOTCH, 0), P(M.BACK, -M.HALF)
poly([tip, bl, nt, br, tip], 4.0, M.INK + (1,))
for k in range(0, 13):
    t = k / 12
    a = (bl[0] + (nt[0] - bl[0]) * t, bl[1] + (nt[1] - bl[1]) * t)
    b = (nt[0] + (br[0] - nt[0]) * t, nt[1] + (br[1] - nt[1]) * t)
    poly([tip, a], 2.2, (1, 1, 1, 1)); poly([tip, b], 2.2, (1, 1, 1, 1))
poly([tip, bl, nt, br, tip], 1.3, pc)

cv = Canvas(img.shape[1], img.shape[0])
cv.px = bytearray((np.clip(img, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8).tobytes())
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(M.HERE, "minimap_preview.png")
cv.save(out)
print("wrote", out)
