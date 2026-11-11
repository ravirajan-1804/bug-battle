"""Generates the shared FX meshes for the Ant acid rework and the Spider car powers.

Unit conventions (all centred on the origin, Unreal space, cm):
  SM_FX_Goo      lumpy goo blob, radius ~50            slot Goo
  SM_FX_Drop     teardrop, head at origin, tail to -X  slot Goo
  SM_FX_Ring     flat torus R 50 in XY                 slot Goo
  SM_FX_Puff     cauliflower smoke puff, radius ~50    slot Smoke
  SM_FX_Strand   silk strand from x=0 to x=100, r=1    slot Silk   (scale X = length/100)
  SM_FX_WebShell web dome over a unit ellipsoid (100)  slots Silk, Sheet
  SM_FX_WebDisc  flat orb web, radius 100              slot Silk
  SM_FX_WebBall  wound ball of silk, radius ~30        slots Silk, Sheet
  SM_FX_Cocoon   silk-wrapped unit ellipsoid (100)     slots Silk, Sheet
  SM_FX_Fang     curved tapered fang along +X, 60 long slot Fang (UV v runs root->tip)
"""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_mul, v_norm, v_len

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)


def sph(u, v):
    th, ph = v * math.pi, u * 2 * math.pi
    return (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))


def goo():
    m = Mesh()

    def deform(p, d):
        w = 1.0 + 0.10 * math.sin(3 * d[0] + 1.3) * math.cos(2 * d[1] + 0.4) + 0.07 * math.sin(5 * d[2] + 2.1)
        return v_mul(p, w)
    ellipsoid(m, "Goo", (0, 0, 0), (50, 50, 50), 36, 22, deform)
    return m


def drop():
    m = Mesh()
    prof = []
    n = 18
    for i in range(n + 1):
        t = i / n                       # 0 tail .. 1 head front
        x = -40 + 50 * t
        r = 10 * math.sin(math.pi * min(1.0, 0.15 + 0.85 * t)) ** 0.8 if t < 1 else 0.0
        if t > 0.8:
            r = 10 * math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 2))
        prof.append((x, max(r, 0.01)))
    from meshlib import lathe_x
    lathe_x(m, "Goo", prof, segs=16)
    return m


def ring():
    m = Mesh()
    R, r = 50.0, 7.0

    def fn(u, v):
        a, b = u * 2 * math.pi, v * 2 * math.pi
        rr = R + r * math.cos(b)
        return (rr * math.cos(a), rr * math.sin(a), r * 0.55 * math.sin(b))
    m.grid("Goo", 40, 10, fn, wrap_u=False, flip=False)
    return m


def puff():
    m = Mesh()
    rng = Rng(7)
    ellipsoid(m, "Smoke", (0, 0, 0), (38, 38, 34), 20, 12)
    for k in range(6):
        a = k / 6 * 2 * math.pi + rng.r(-0.3, 0.3)
        c = (24 * math.cos(a), 24 * math.sin(a), rng.r(-8, 14))
        rr = rng.r(18, 26)
        ellipsoid(m, "Smoke", c, (rr, rr, rr * 0.92), 14, 9)
    ellipsoid(m, "Smoke", (0, 0, 26), (24, 24, 22), 14, 9)
    return m


def strand():
    m = Mesh()
    pts = [(x, 0, 0) for x in (0, 25, 50, 75, 100)]
    tube_along(m, "Silk", pts, [1, 1, 1, 1, 1], segs=6, cap=False)
    return m


def on_ellipsoid(d, sag=0.0):
    return v_mul(v_norm(d), 100.0 * (1.0 - sag))


def web_shell():
    m = Mesh()
    rng = Rng(11)
    spokes = 18
    lat = [-0.15, 0.12, 0.35, 0.55, 0.72, 0.86]           # z (unit) of rings
    pole = (0, 0, 100)
    # meridians from the lower edge to the top
    for s in range(spokes):
        a = s / spokes * 2 * math.pi + rng.r(-0.08, 0.08)
        pts = []
        for k in range(9):
            z = -0.25 + 1.25 * k / 8
            z = min(z, 0.995)
            rxy = math.sqrt(max(0.0, 1 - z * z))
            pts.append(on_ellipsoid((rxy * math.cos(a), rxy * math.sin(a), z), -0.03))
        pts.append(pole)
        tube_along(m, "Silk", catmull(pts, 3), [1.6] * len(catmull(pts, 3)), segs=5, cap=False)
    # sagging capture rings between the spokes
    for zi, z in enumerate(lat):
        rxy = math.sqrt(1 - z * z)
        pts = []
        for s in range(spokes + 1):
            for k in range(3):
                t = (s + k / 3.0) / spokes
                a = t * 2 * math.pi
                sag = 0.05 * math.sin(math.pi * k / 3.0)  # dips inward between spokes
                zz = z - 0.03 * math.sin(math.pi * k / 3.0)
                pts.append(on_ellipsoid((rxy * math.cos(a), rxy * math.sin(a), zz), sag - 0.02))
        tube_along(m, "Silk", pts, [1.1] * len(pts), segs=5, cap=False)
    # random cross threads for a messy, natural look
    for k in range(26):
        a0 = rng.r(0, 2 * math.pi)
        z0 = rng.r(-0.2, 0.8)
        a1 = a0 + rng.r(-1.0, 1.0)
        z1 = min(0.95, z0 + rng.r(-0.3, 0.4))
        pts = []
        for i in range(8):
            t = i / 7
            a = a0 + (a1 - a0) * t
            z = z0 + (z1 - z0) * t
            rxy = math.sqrt(max(0.0, 1 - z * z))
            pts.append(on_ellipsoid((rxy * math.cos(a), rxy * math.sin(a), z), 0.04 * math.sin(math.pi * t) - 0.04))
        tube_along(m, "Silk", pts, [0.8] * len(pts), segs=4, cap=False)
    # torn silk sheets stuck between threads
    for k in range(14):
        a0 = rng.r(0, 2 * math.pi)
        z0 = rng.r(0.0, 0.8)
        da, dz = rng.r(0.25, 0.55), rng.r(0.12, 0.25)

        def fn(u, v, a0=a0, z0=z0, da=da, dz=dz):
            a = a0 + da * (u - 0.5)
            z = z0 + dz * (v - 0.5)
            rxy = math.sqrt(max(0.0, 1 - z * z))
            edge = math.sin(math.pi * u) * math.sin(math.pi * v)
            return on_ellipsoid((rxy * math.cos(a), rxy * math.sin(a), z), -0.035 + 0.03 * edge)
        m.grid("Sheet", 6, 4, fn, flip=False)
        m.grid("Sheet", 6, 4, fn, flip=True)
    return m


def web_disc():
    m = Mesh()
    rng = Rng(3)
    spokes = 16
    angs = [s / spokes * 2 * math.pi + rng.r(-0.05, 0.05) for s in range(spokes)]
    for a in angs:
        pts = [(0, 0, 0.5), (50 * math.cos(a), 50 * math.sin(a), 0.5), (100 * math.cos(a), 100 * math.sin(a), 0.5)]
        tube_along(m, "Silk", pts, [0.9, 0.9, 0.9], segs=4, cap=False)
    # capture spiral, sagging between spokes
    pts = []
    turns = 9
    steps = spokes * turns
    for i in range(steps + 1):
        s = i % spokes
        a0 = angs[s]
        a1 = angs[(s + 1) % spokes] + (2 * math.pi if s == spokes - 1 else 0)
        for k in range(3):
            t = k / 3.0
            a = a0 + (a1 - a0) * t
            r = 14 + 84 * (i + t) / steps
            r *= 1.0 - 0.06 * math.sin(math.pi * t)
            pts.append((r * math.cos(a), r * math.sin(a), 0.5))
    tube_along(m, "Silk", pts, [0.6] * len(pts), segs=4, cap=False)
    return m


def web_ball():
    m = Mesh()
    rng = Rng(5)
    ellipsoid(m, "Sheet", (0, 0, 0), (19, 19, 19), 18, 12)
    for k in range(26):
        n = v_norm((rng.r(-1, 1), rng.r(-1, 1), rng.r(-1, 1)))
        t1 = v_norm((n[1], -n[0], 0.3)) if abs(n[2]) < 0.9 else (1, 0, 0)
        t2 = (n[1] * t1[2] - n[2] * t1[1], n[2] * t1[0] - n[0] * t1[2], n[0] * t1[1] - n[1] * t1[0])
        r = rng.r(20, 29)
        pts = []
        for i in range(25):
            a = i / 24 * 2 * math.pi
            w = r * (1 + 0.08 * math.sin(3 * a + k))
            pts.append(v_add(v_mul(t1, w * math.cos(a)), v_mul(t2, w * math.sin(a))))
        tube_along(m, "Silk", pts, [1.4] * len(pts), segs=5, cap=False)
    return m


def cocoon():
    m = Mesh()
    rng = Rng(9)

    def deform(p, d):
        return v_mul(p, 0.93 + 0.03 * math.sin(7 * d[2] + 3 * math.atan2(d[1], d[0])))
    ellipsoid(m, "Sheet", (0, 0, 0), (100, 100, 100), 40, 24, deform)
    for layer in range(5):
        tilt = rng.r(-0.35, 0.35)
        ph = rng.r(0, 2 * math.pi)
        turns = rng.r(6.0, 9.0)
        direction = 1 if layer % 2 == 0 else -1
        pts = []
        steps = int(turns * 26)
        for i in range(steps + 1):
            t = i / steps
            z = -0.92 + 1.84 * t
            a = direction * t * turns * 2 * math.pi + ph
            zz = z + tilt * math.cos(a) * math.sqrt(max(0.0, 1 - z * z))
            zz = max(-0.97, min(0.97, zz))
            rxy = math.sqrt(max(0.0, 1 - zz * zz))
            pts.append(v_mul((rxy * math.cos(a), rxy * math.sin(a), zz), 101.5 + rng.r(-0.6, 0.6)))
        tube_along(m, "Silk", pts, [rng.r(2.0, 3.2)] * len(pts), segs=5, cap=False)
    return m


def fang():
    m = Mesh()
    pts, rad = [], []
    n = 14
    for i in range(n + 1):
        t = i / n
        x = 60 * t
        z = -26 * t ** 2.2
        pts.append((x, 0, z))
        rad.append(7.0 * (1 - t) ** 0.9 + 0.4)
    tube_along(m, "Fang", pts, rad, segs=10, cap=True)
    return m


ALL = {
    "SM_FX_Goo": goo, "SM_FX_Drop": drop, "SM_FX_Ring": ring, "SM_FX_Puff": puff,
    "SM_FX_Strand": strand, "SM_FX_WebShell": web_shell, "SM_FX_WebDisc": web_disc,
    "SM_FX_WebBall": web_ball, "SM_FX_Cocoon": cocoon, "SM_FX_Fang": fang,
}

if __name__ == "__main__":
    for name, fn in ALL.items():
        n = fn().write_obj(os.path.join(OUT, name + ".obj"))
        print(name, n, "tris")
