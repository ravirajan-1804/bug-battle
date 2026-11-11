"""Generates the honey gel puddle and the honey-bee kart body meshes."""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_norm

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------------ honey gel
def honey_gel():
    """Thick, lobed honey puddle: flat-topped dome with a steep rounded
    (surface-tension) edge, irregular outline and satellite splash drops.
    Radius ~100 cm, height ~20 cm at scale 1."""
    m = Mesh()
    rng = Rng(7)
    R, H = 100.0, 20.0
    lob = [(3, 0.10, 0.4), (5, 0.06, 1.7), (7, 0.035, 2.9), (11, 0.02, 0.8)]

    def rim(a):
        return 1.0 + sum(amp * math.sin(k * a + ph) for k, amp, ph in lob)

    def hscale(a):
        return 1.0 + 0.12 * math.sin(2 * a + 1.1) + 0.06 * math.sin(5 * a + 0.3)

    def profile(rho, p=2.4, q=0.38):
        rho = min(max(rho, 0.0), 1.0)
        return (1.0 - rho ** p) ** q

    rings, segs = 30, 144

    def top(u, v):
        a = u * 2 * math.pi
        rho = 1.0 - (1.0 - v) ** 1.6  # denser rings near the rim
        rr = R * rim(a) * rho
        # tiny centre sag + soft swell so the top isn't perfectly flat
        z = H * hscale(a) * profile(rho) * (1.0 + 0.05 * math.cos(rho * 5.0))
        return (rr * math.cos(a), rr * math.sin(a), z - 0.6)

    m.grid("Honey", segs, rings, top,
           uv_fn=lambda u, v: (0.5 + 0.5 * math.cos(u * 6.283) * v, 0.5 + 0.5 * math.sin(u * 6.283) * v),
           wrap_u=True, flip=True)

    # satellite drops / splash beads
    for i in range(11):
        a = rng.r(0, 2 * math.pi)
        d = R * rim(a) * rng.r(1.06, 1.45)
        r = rng.r(4.0, 15.0)
        stretch = rng.r(1.0, 2.2)
        h = r * rng.r(0.45, 0.7)
        cx, cy = d * math.cos(a), d * math.sin(a)
        ca, sa = math.cos(a), math.sin(a)

        def drop(u, v, cx=cx, cy=cy, r=r, h=h, stretch=stretch, ca=ca, sa=sa):
            t = u * 2 * math.pi
            rho = 1.0 - (1.0 - v) ** 1.5
            lx, ly = math.cos(t) * r * stretch * rho, math.sin(t) * r * rho
            return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, h * profile(rho, 2.0, 0.5) - 0.6)
        m.grid("Honey", 24, 6, drop, wrap_u=True, flip=True)
    return m


# ------------------------------------------------------------------ bee parts
BODY_Z = 100.0


def bee_abdomen():
    m = Mesh()
    # (s, radius) along the abdomen, s=0 at the petiole, s=1 at the tail
    prof = [(0.0, 16), (0.04, 40), (0.12, 68), (0.25, 82), (0.45, 86), (0.62, 80),
            (0.76, 64), (0.88, 40), (0.96, 18), (1.0, 5)]
    x0, x1 = -8.0, -262.0
    bands = [0.0, 0.13, 0.29, 0.41, 0.56, 0.68, 0.81, 1.01]  # black/yellow alternation

    def rad(s):
        for i in range(len(prof) - 1):
            if prof[i][0] <= s <= prof[i + 1][0]:
                t = (s - prof[i][0]) / (prof[i + 1][0] - prof[i][0])
                t = t * t * (3 - 2 * t)
                r = prof[i][1] * (1 - t) + prof[i + 1][1] * t
                break
        else:
            r = prof[-1][1]
        # segment ridges: slight pinch at each band boundary
        for b in bands[1:-1]:
            r *= 1.0 - 0.045 * math.exp(-((s - b) / 0.018) ** 2)
        return r

    nv, segs = 120, 56
    rows = []
    for j in range(nv + 1):
        s = j / nv
        x = x0 + (x1 - x0) * s
        r = rad(s)
        zc = BODY_Z + 6.0 * s * s  # tail lifts slightly
        row = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            row.append(m.vert((x, r * 0.86 * math.sin(a), zc + r * 0.93 * math.cos(a)), (i / segs, s)))
        rows.append(row)
    for j in range(nv):
        s = (j + 0.5) / nv
        band = max(k for k in range(len(bands) - 1) if bands[k] <= s)
        mat = "Black" if band % 2 == 0 else "Yellow"
        for i in range(segs):
            i2 = (i + 1) % segs
            # outward winding (see meshlib lathe notes)
            m.quad(mat, rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i])
    # stinger
    sting = [(x1 + 4, 9.0), (x1 - 10, 6.0), (x1 - 28, 3.0), (x1 - 46, 0.6)]
    pts = [(x, 0.0, BODY_Z + 6.0 + (x1 - x) * 0.12) for x, _ in sting]
    tube_along(m, "Black", pts, [r for _, r in sting], segs=12)
    return m


def bee_thorax_head():
    m = Mesh()
    rng = Rng(3)

    def fuzz(p, d):
        k = 1.0 + 0.012 * math.sin(d[0] * 23 + d[1] * 17) * math.cos(d[2] * 19)
        return (p[0] * k, p[1] * k, p[2] * k)
    ellipsoid(m, "Fuzz", (42.0, 0.0, BODY_Z + 6), (72, 66, 66), 48, 28, fuzz)          # thorax
    ellipsoid(m, "Black", (8.0, 0.0, BODY_Z + 2), (24, 22, 22), 20, 12)                # petiole
    ellipsoid(m, "Black", (146.0, 0.0, BODY_Z + 2), (46, 56, 52), 44, 26)             # head
    # mandibles
    for sy in (-1, 1):
        pts = catmull([(176, sy * 20, BODY_Z - 32), (188, sy * 14, BODY_Z - 44), (194, sy * 4, BODY_Z - 48)], 4)
        tube_along(m, "Black", pts, [7, 6, 5, 4, 3.5, 3, 2.5, 2, 1.5][:len(pts)] + [1.5] * 20, segs=8)
    return m


def bee_eyes():
    m = Mesh()
    for sy in (-1, 1):
        ellipsoid(m, "Eye", (156.0, sy * 38.0, BODY_Z + 10), (32, 20, 42), 32, 20)
    # three ocelli on top of the head
    for (x, y) in ((150, 0), (140, 12), (140, -12)):
        ellipsoid(m, "Eye", (x, y, BODY_Z + 52), (5, 5, 4), 10, 6)
    return m


def bee_antennae():
    m = Mesh()
    for sy in (-1, 1):
        ctrl = [(182, sy * 14, BODY_Z + 30), (196, sy * 22, BODY_Z + 62), (206, sy * 30, BODY_Z + 96),
                (230, sy * 40, BODY_Z + 110), (262, sy * 48, BODY_Z + 104), (284, sy * 52, BODY_Z + 92)]
        pts = catmull(ctrl, 5)
        n = len(pts)
        radii = [5.5 - 1.8 * (i / (n - 1)) for i in range(n)]
        radii[-1] = 4.5
        radii[-2] = 4.6
        tube_along(m, "Black", pts, radii, segs=10)
    return m


def bee_legs():
    m = Mesh()
    roots = [(92, 14), (46, 0), (2, -16)]
    for li, (x, dx) in enumerate(roots):
        for sy in (-1, 1):
            ctrl = [(x, sy * 26, BODY_Z - 44), (x + dx * 0.5, sy * 70, BODY_Z - 50),
                    (x + dx, sy * 96, BODY_Z - 46), (x + dx * 1.6, sy * 104, BODY_Z - 74),
                    (x + dx * 2.2, sy * 108, BODY_Z - 92)]
            pts = catmull(ctrl, 4)
            n = len(pts)
            radii = [9.0 - 4.0 * (i / (n - 1)) for i in range(n)]
            tube_along(m, "Black", pts, radii, segs=10)
            if li == 2:  # pollen basket on the hind tibia
                ellipsoid(m, "Pollen", (x + dx * 1.3, sy * 104, BODY_Z - 64), (16, 11, 14), 18, 10)
    return m


def bee_wing(length=210.0, chord=86.0, name="fore"):
    """Wing sheet in the XY plane, root at origin, span along +Y."""
    m = Mesh()

    def le(s):   # leading edge (forward, +X)
        return 0.22 * chord * math.sin(math.pi * min(s * 1.05, 1.0)) ** 0.7 + 4.0

    def te(s):   # trailing edge (back, -X)
        return -chord * (math.sin(math.pi * min(s, 1.0) ** 0.75) ** 0.9) * (1.0 - 0.15 * s) - 2.0

    def fn(u, v):
        s = v
        sw = -0.32 * length * s * s  # swept back towards the tip
        x = te(s) + (le(s) - te(s)) * u + sw
        y = length * s
        z = 5.0 * math.sin(math.pi * s) * (1 - abs(u - 0.6))
        return (x, y, z)
    m.grid("Wing", 14, 30, fn, uv_fn=lambda u, v: (u, v))
    return m


def pollen_wheel():
    m = Mesh()

    def bumps(p, d):
        k = 1.0 + 0.05 * math.sin(d[0] * 11 + 1.3) * math.sin(d[1] * 13 + 0.4) * math.sin(d[2] * 12 + 2.0) \
            + 0.03 * math.sin(d[0] * 31 + d[2] * 27)
        return (p[0] * k, p[1] * k, p[2] * k)
    ellipsoid(m, "Pollen", (0, 0, 0), (38, 30, 38), 40, 26, bumps)
    return m


def main():
    jobs = {
        "SM_HoneyGel": honey_gel,
        "SM_BeeAbdomen": bee_abdomen,
        "SM_BeeThoraxHead": bee_thorax_head,
        "SM_BeeEyes": bee_eyes,
        "SM_BeeAntennae": bee_antennae,
        "SM_BeeLegs": bee_legs,
        "SM_BeeForeWing": lambda: bee_wing(210, 86),
        "SM_BeeHindWing": lambda: bee_wing(140, 52),
        "SM_PollenWheel": pollen_wheel,
    }
    for name, fn in jobs.items():
        n = fn().write_obj(os.path.join(OUT, name + ".obj"))
        print(name, n, "tris")


if __name__ == "__main__":
    main()
