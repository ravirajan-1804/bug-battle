"""Centreline definition for Lvl_GardenGrandPrix (UE space: X east, Y south, Z up, cm).

The main loop is a closed centripetal Catmull-Rom through hand-placed control
points, resampled at a fixed arc-length step. Banking is derived from signed
curvature (smoothed), per-zone limits keep straights/junctions flat, and the
elevation profile is a smooth function of arc length.
"""
import math
import os
import sys
import numpy as np

STEP = 100.0          # cm between cross-sections
HALF_W = 1200.0       # main road half width (2400 cm surface incl. kerbs)
LAYOUT_SCALE = 480.0  # v5: cm per pixel of the Losail reference image (ref/losail_ref.png)
ENV_SCALE = 1.45      # backyard (fence ring, ground, background scatter) grows with the layout
IMG_CENTRE = (50.5, 40.0)   # reference-image pixel that maps to the world origin

# v5 (2026-10-17): layout traced from the user's Losail circuit screenshot (ref/losail_ref.png,
# trace in ref/losail_trace.py, check with ref/trace_overlay.py). Image x -> UE +X (east),
# image y (down) -> UE +Y (south). Travel direction: east along the south start/finish straight,
# north up the east side, then the twisty sections along the north and west back to the straight.
# The previous layouts (with shortcut, two-way split and tunnels) are backed up in Saved/RG_backup_v4.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref"))
from losail_trace import PTS as _LOSAIL_PX  # noqa: E402


def L(x, y):
    """Reference-image pixel -> world xy (cm)."""
    return ((x - IMG_CENTRE[0]) * LAYOUT_SCALE, (y - IMG_CENTRE[1]) * LAYOUT_SCALE)


MAIN_PTS = [L(*p) for p in _LOSAIL_PX]

# Losail is flat: no elevation change (a smooth function of lap fraction if ever wanted).
ELEV_KEYS = [(0.0, 0.0), (1.0, 0.0)]

BANK_GAIN = 5200.0 * 1.4              # bank_deg = BANK_MAX * clamp(GAIN * curvature)
# Per-zone bank limit in degrees, keyed on lap fraction: flat on the start/finish straight,
# a light 5 deg everywhere else so the corners are not slippery.
BANK_ZONES = [(0.0, 0.0), (0.16, 0.0), (0.2, 5.0), (0.97, 5.0), (1.0, 0.0)]


def catmull_closed(pts, samples=60, alpha=0.5):
    P = np.array(pts, dtype=float)
    n = len(P)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** alpha
        t2 = t1 + np.linalg.norm(p2 - p1) ** alpha
        t3 = t2 + np.linalg.norm(p3 - p2) ** alpha
        for k in range(samples):
            t = t1 + (t2 - t1) * k / samples
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.array(out)


def resample(poly, step, closed=True):
    if closed:
        poly = np.vstack([poly, poly[:1]])
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    n = int(round(total / step))
    s = np.linspace(0, total, n, endpoint=not closed)
    x = np.interp(s, cum, poly[:, 0])
    y = np.interp(s, cum, poly[:, 1])
    return np.stack([x, y], 1), s, total


def smooth_closed(v, win):
    k = np.exp(-0.5 * (np.arange(-3 * win, 3 * win + 1) / win) ** 2)
    k /= k.sum()
    vv = np.concatenate([v[-3 * win:], v, v[:3 * win]])
    return np.convolve(vv, k, mode="same")[3 * win:-3 * win]


def keyed(keys, f):
    xs = [k[0] for k in keys]
    ys = [k[1] for k in keys]
    i = max(0, min(len(xs) - 2, int(np.searchsorted(xs, f, side="right") - 1)))
    t = (f - xs[i]) / (xs[i + 1] - xs[i])
    t = t * t * (3 - 2 * t)
    return ys[i] + (ys[i + 1] - ys[i]) * t


class Track:
    def __init__(self, pts=MAIN_PTS, step=STEP):
        dense = catmull_closed(pts)
        xy, s, total = resample(dense, step)
        xy = np.stack([smooth_closed(xy[:, 0], 3), smooth_closed(xy[:, 1], 3)], 1)
        xy, s, total = resample(xy, step)
        self.xy, self.s, self.length = xy, s, total
        self.step = total / len(xy)
        n = len(xy)
        d = np.roll(xy, -1, 0) - np.roll(xy, 1, 0)
        ang = np.arctan2(d[:, 1], d[:, 0])
        self.heading = ang
        dh = np.angle(np.exp(1j * (np.roll(ang, -1) - np.roll(ang, 1))))
        self.curv = smooth_closed(dh / (2 * self.step), 8)   # +: right turn (towards +Y), -: left turn
        frac = s / total
        self.frac = frac
        self.z = smooth_closed(np.array([keyed(ELEV_KEYS, f) for f in frac]), 10)
        bmax = np.array([keyed(BANK_ZONES, f) for f in frac])
        target = -np.sign(self.curv) * np.minimum(1.0, np.abs(self.curv) * BANK_GAIN) * bmax
        # bank (deg) > 0 lifts the right edge (left turns); smoothed so transitions are gradual
        self.bank = smooth_closed(target, 14)

    def frame(self, i):
        """Centre point, forward, right, up (banked) at sample i."""
        n = len(self.xy)
        i %= n
        x, y = self.xy[i]
        z = self.z[i]
        dz = (self.z[(i + 1) % n] - self.z[i - 1]) / (2 * self.step)
        h = self.heading[i]
        fwd = np.array([math.cos(h), math.sin(h), dz])
        fwd /= np.linalg.norm(fwd)
        right0 = np.array([-math.sin(h), math.cos(h), 0.0])
        right0 -= fwd * np.dot(right0, fwd)
        right0 /= np.linalg.norm(right0)
        up0 = np.cross(right0, fwd)
        if up0[2] < 0:
            up0 = -up0
        b = math.radians(self.bank[i])
        right = right0 * math.cos(b) + up0 * math.sin(b)
        up = up0 * math.cos(b) - right0 * math.sin(b)
        # pivot on the inner (lower) edge so the low edge stays at grade
        lift = HALF_W * abs(math.sin(b))
        c = np.array([x, y, z + lift])
        return c, fwd, right, up

    def nearest(self, p):
        d = np.linalg.norm(self.xy - np.asarray(p)[None, :2], axis=1)
        i = int(np.argmin(d))
        return i, d[i]

    def index_at(self, x, y):
        return self.nearest((x, y))[0]


def catmull_open(pts, samples=40, alpha=0.5):
    P = list(np.array(pts, dtype=float))
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t1 = np.linalg.norm(p1 - p0) ** alpha
        t2 = t1 + np.linalg.norm(p2 - p1) ** alpha
        t3 = t2 + np.linalg.norm(p3 - p2) ** alpha
        for k in range(samples):
            t = t1 + (t2 - t1) * k / samples
            a1 = (t1 - t) / t1 * p0 + t / t1 * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / t2 * a1 + t / t2 * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    return np.array(out)


class Branch:
    """Open path leaving and rejoining the main loop; flat (no bank) away from the main road,
    height blends between the two junction grades."""

    def __init__(self, main, frm, to, ctrl, half_w):
        self.half_w = half_w
        ia, ib = main.index_at(*frm), main.index_at(*to)
        self.ia, self.ib = ia, ib
        n = len(main.xy)
        lead = [main.xy[(ia - k) % n] for k in (12, 6)]
        tail = [main.xy[(ib + k) % n] for k in (6, 12)]
        pts = lead + [main.xy[ia]] + list(ctrl) + [main.xy[ib]] + tail
        dense = catmull_open(pts)
        xy, s, total = resample(dense, STEP, closed=False)
        # trim the lead/tail helper spans back to the junction points
        i0 = int(np.argmin(np.linalg.norm(xy - main.xy[ia], axis=1)))
        i1 = int(np.argmin(np.linalg.norm(xy - main.xy[ib], axis=1)))
        self.xy = xy[i0:i1 + 1]
        self.length = (i1 - i0) * (total / (len(xy) - 1))
        self.step = total / (len(xy) - 1)
        d = np.gradient(self.xy, axis=0)
        self.heading = np.arctan2(d[:, 1], d[:, 0])
        m = len(self.xy)
        t = np.linspace(0, 1, m)
        t = t * t * (3 - 2 * t)
        z_free = main.z[ia] + (main.z[ib] - main.z[ia]) * t
        # Near the junctions the shortcut lies on/under the main road: follow the main
        # surface height (slightly below it) so there is no step where it leaves/rejoins.
        z = np.zeros(m)
        zm, sp, bk = np.zeros(m), np.zeros(m), np.zeros(m)
        for k in range(m):
            j, sep = main.nearest(self.xy[k])
            c, f, r, u = main.frame(j)
            lat = float(np.clip(np.dot(self.xy[k] - c[:2], r[:2]) / max(1e-6, np.dot(r[:2], r[:2])), -HALF_W, HALF_W))
            z_main = c[2] + r[2] * lat - 8.0
            w = np.clip((sep - HALF_W - half_w) / 1500.0, 0.0, 1.0)
            w = w * w * (3 - 2 * w)
            z[k] = z_main * (1 - w) + z_free[k] * w
            zm[k], sp[k], bk[k] = z_main, sep, main.bank[j]
        # gentle vertical smoothing (edge-padded), then never rise above the main surface
        # while still inside the main road footprint
        win = 5
        kern = np.exp(-0.5 * (np.arange(-3 * win, 3 * win + 1) / win) ** 2)
        kern /= kern.sum()
        zz = np.concatenate([np.full(3 * win, z[0]), z, np.full(3 * win, z[-1])])
        z = np.convolve(zz, kern, mode="same")[3 * win:-3 * win]
        # re-pin to the main surface while any part of the shortcut overlaps the main road,
        # easing into the smoothed profile over the next few metres
        pin = np.clip((sp - HALF_W - half_w) / 400.0, 0.0, 1.0)
        pin = pin * pin * (3 - 2 * pin)
        z = zm * (1 - pin) + z * pin
        self.z_main_ref, self.sep = zm, sp
        self.z = z
        # share the main road's bank while overlapping so the two surfaces stay coplanar,
        # then roll out to flat over ~15 m once clear of the main road
        bfade = np.clip((sp - HALF_W - half_w) / 1500.0, 0.0, 1.0)
        bfade = bfade * bfade * (3 - 2 * bfade)
        self.bank = bk * (1 - bfade)

    def frame(self, i):
        m = len(self.xy)
        i = max(0, min(m - 1, i))
        x, y = self.xy[i]
        dz = (self.z[min(m - 1, i + 1)] - self.z[max(0, i - 1)]) / (2 * self.step)
        h = self.heading[i]
        fwd = np.array([math.cos(h), math.sin(h), dz])
        fwd /= np.linalg.norm(fwd)
        right0 = np.array([-math.sin(h), math.cos(h), 0.0])
        right0 -= fwd * np.dot(right0, fwd)
        right0 /= np.linalg.norm(right0)
        up0 = np.cross(right0, fwd)
        if up0[2] < 0:
            up0 = -up0
        b = math.radians(self.bank[i])
        right = right0 * math.cos(b) + up0 * math.sin(b)
        up = up0 * math.cos(b) - right0 * math.sin(b)
        return np.array([x, y, self.z[i]]), fwd, right, up


def plot(T, path, extra=None):
    from pngplot import Canvas
    W = 900
    sc = W / 52000.0
    cv = Canvas(W, W)
    tr = lambda p: ((p[0] + 26000) * sc, (p[1] + 26000) * sc)
    for g in range(-26000, 26001, 2000):
        cv.line(tr((g, -26000)), tr((g, 26000)), (225, 225, 225), 0)
        cv.line(tr((-26000, g)), tr((26000, g)), (225, 225, 225), 0)
    n = len(T.xy)
    for i in range(n):
        c, f, r, u = T.frame(i)
        for side in (-1, 1):
            e = c[:2] + side * HALF_W * r[:2]
            cv.dot(*tr(e), (40, 40, 40), 1)
        col = (int(min(255, abs(T.bank[i]) * 18)), 80, 200 - int(min(200, abs(T.bank[i]) * 14)))
        cv.dot(*tr(c), col, 0)
    for p in MAIN_PTS:
        cv.dot(*tr(p), (220, 30, 30), 3)
    if extra:
        extra(cv, tr)
    cv.save(path)


if __name__ == "__main__":
    T = Track()
    print("lap length cm", round(T.length), "samples", len(T.xy))
    print("min radius cm", round(1 / np.max(np.abs(T.curv))), "max bank", round(np.max(np.abs(T.bank)), 1))
    # closest approach between parts of the loop that are not neighbours along the road
    n = len(T.xy)
    worst = (1e12, 0, 0)
    for i in range(0, n, 2):
        d = np.linalg.norm(T.xy - T.xy[i], axis=1)
        k = np.arange(n)
        far = np.minimum(np.abs(k - i), n - np.abs(k - i)) * T.step > 6 * HALF_W
        j = int(np.argmin(np.where(far, d, 1e12)))
        if d[j] < worst[0]:
            worst = (d[j], i, j)
    print("min centreline gap between separate legs", round(worst[0]), "at", worst[1], worst[2],
          "(road needs", 2 * HALF_W + 100, "+ verge)")
    print("max radius of road edge", round(np.linalg.norm(T.xy, axis=1).max() + HALF_W),
          "fence radius", round(18000 * ENV_SCALE))
    plot(T, "layout.png", lambda cv, tr: cv.dot(*tr(T.xy[T.index_at(*L(40, 67))]), (0, 160, 0), 6))
    for f in np.linspace(0, 1, 41)[:-1]:
        i = int(f * n)
        print("%.3f s=%6d xy=(%6d,%6d) bank=%5.1f R=%6d" % (f, T.s[i], T.xy[i][0], T.xy[i][1], T.bank[i],
              min(99999, 1 / max(1e-6, abs(T.curv[i])))))
