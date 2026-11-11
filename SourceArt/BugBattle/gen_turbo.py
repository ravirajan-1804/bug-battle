"""Generates Turbo-style giant garden props: staked tomato plants and fallen tomatoes."""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_norm

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)


def tomato(m, mat, c, R, seed, tilt=(0.0, 0.0)):
    """Lobed, slightly squashed tomato with a star of sepals and a stub stem on top."""
    rng = Rng(seed)
    lobes = 5 + int(rng.r(0, 2))
    ph0 = rng.r(0, 6.28)

    def deform(p, d):
        sin_th = math.sqrt(max(0.0, 1 - d[2] * d[2]))
        ph = math.atan2(d[1], d[0])
        k = 1 + 0.055 * math.cos(lobes * ph + ph0) * sin_th ** 2
        z = p[2] * 0.82
        if d[2] > 0.75:                      # shoulder dimple around the stem
            z -= R * 0.12 * (d[2] - 0.75) / 0.25
        return (p[0] * k, p[1] * k, z)
    ellipsoid(m, mat, c, (R, R, R), 48, 28, deform=deform)
    top = v_add(c, (0, 0, R * 0.82 - R * 0.1))
    for i in range(5):
        a = 2 * math.pi * i / 5 + rng.r(-0.2, 0.2)
        L = R * rng.r(0.45, 0.6)

        def sepal(u, v, a=a, L=L):
            w = L * 0.22 * (1 - v) ** 0.8 * math.sin(math.pi * min(1.0, v * 3 + 0.2))
            off = (u - 0.5) * w
            r = v * L
            z = R * 0.05 * math.sin(v * math.pi) - L * 0.25 * v * v + abs(u - 0.5) * w * 0.3
            return v_add(top, (r * math.cos(a) - off * math.sin(a), r * math.sin(a) + off * math.cos(a), z + 4))
        m.grid("Stem", 3, 8, sepal)
    tube_along(m, "Stem", catmull([top, v_add(top, (R * 0.04, 0, R * 0.12)), v_add(top, (R * 0.12, R * 0.05, R * 0.22))], 4),
               [R * 0.07, R * 0.065, R * 0.06, R * 0.055, R * 0.05, R * 0.05, R * 0.045, R * 0.04, R * 0.04][:9], segs=10)


def compound_leaf(m, base, ang, L, droop, rng):
    """Tomato leaf: a curved midrib with jagged leaflets along it."""
    pts = []
    for i in range(9):
        s = i / 8
        x = s * L
        z = L * 0.25 * math.sin(s * 1.6) - droop * L * s * s
        pts.append(v_add(base, (x * math.cos(ang), x * math.sin(ang), z)))
    tube_along(m, "Stem", pts, [L * 0.018 * (1 - 0.6 * i / 8) for i in range(9)], segs=6)
    for k in range(1, 8):
        p0 = pts[k]
        for side in (-1, 1):
            if k == 7 and side == 1:
                continue
            la = ang + side * rng.r(0.9, 1.3) if k < 7 else ang
            Ll = L * (0.32 - 0.02 * k) * rng.r(0.85, 1.1)
            teeth = 5

            def leaflet(u, v, p0=p0, la=la, Ll=Ll):
                s = v
                tooth = 1 + 0.18 * abs(math.sin(s * teeth * math.pi))
                w = Ll * 0.42 * math.sin(math.pi * s) ** 0.7 * tooth
                off = (u - 0.5) * w
                x = s * Ll
                z = -Ll * 0.25 * s * s + abs(u - 0.5) * w * 0.35
                return (p0[0] + x * math.cos(la) - off * math.sin(la), p0[1] + x * math.sin(la) + off * math.cos(la), p0[2] + z)
            m.grid("Leaf", 4, 10, leaflet)


def tomato_plant(seed, H=7600.0):
    m = Mesh()
    rng = Rng(seed)
    # wooden garden stake
    lean = (rng.r(-120, 120), rng.r(-120, 120))
    stake = [(lean[0] * i / 6, lean[1] * i / 6, -80 + (H + 300) * i / 6) for i in range(7)]
    tube_along(m, "Stake", stake, [78] * 7, segs=6)
    # main vine winding round the stake
    vine = []
    for i in range(41):
        s = i / 40
        a = s * 2.6 * 2 * math.pi + seed
        rr = 130 + 40 * math.sin(s * 9)
        vine.append((lean[0] * s + rr * math.cos(a), lean[1] * s + rr * math.sin(a), -60 + H * 0.97 * s))
    tube_along(m, "Stem", vine, [62 - 30 * i / 40 for i in range(41)], segs=10)
    # leaves
    for k in range(9):
        s = 0.12 + 0.85 * k / 8
        p = vine[int(s * 40)]
        compound_leaf(m, p, rng.r(0, 6.28), rng.r(1500, 2300) * (1.1 - 0.4 * s), rng.r(0.25, 0.5), rng)
    # trusses of tomatoes hanging off the vine
    mats = ["TomatoRed", "TomatoRed", "TomatoRed", "TomatoOrange", "TomatoGreen"]
    for k in range(3):
        s = 0.3 + 0.22 * k + rng.r(-0.04, 0.04)
        p = vine[int(s * 40)]
        a = rng.r(0, 6.28)
        hub = v_add(p, (650 * math.cos(a), 650 * math.sin(a), -350))
        tube_along(m, "Stem", catmull([p, v_add(p, (320 * math.cos(a), 320 * math.sin(a), 60)), hub], 4), [34, 32, 30, 28, 26, 24, 22, 20, 18][:9], segs=8)
        for j in range(3 + int(rng.r(0, 2))):
            b = a + rng.r(-1.4, 1.4)
            R = rng.r(420, 620)
            c = v_add(hub, (R * 0.9 * math.cos(b), R * 0.9 * math.sin(b), -R * 1.3 - rng.r(0, 300)))
            tube_along(m, "Stem", [hub, v_add(c, (0, 0, R * 0.75))], [16, 14], segs=6)
            tomato(m, mats[int(rng.r(0, len(mats) - 0.01))], c, R, seed * 31 + k * 7 + j)
    return m


def fallen_tomato(seed, R=1000.0, mat="TomatoRed"):
    m = Mesh()
    tomato(m, mat, (0, 0, R * 0.78), R, seed)
    return m


# ---------- dense grass carpet + backyard fence ----------

# (x, y, radius) footprints the carpet must leave clear: pots, tomato plants, fallen tomatoes
CLEAR = [(7287, 1284, 900), (1915, 7147, 900), (-644, -7371, 900), (-5668, 4756, 900), (-6706, -3127, 900),
         (6408, -3700, 900), (8739, 3180, 650), (1684, 9552, 650), (-7124, 5977, 650), (-9115, -3317, 650),
         (-1614, -9158, 650), (7430, -6235, 650), (4724, 5630, 1150), (-7238, 1276, 1150), (2513, -6906, 1150)]
R0, R1 = 6380.0, 16800.0
SECTORS = 12


def smooth(e0, e1, x):
    k = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return k * k * (3 - 2 * k)


def grass_sector(seed, k, blades=3400):
    """One 30-degree slice of thick lawn: short blades at the arena edge rising to a tall grass jungle."""
    m = Mesh()
    rng = Rng(seed)
    span = 2 * math.pi / SECTORS
    placed = 0
    tries = 0
    while placed < blades and tries < blades * 3:
        tries += 1
        # uniform over the annulus sector
        r = math.sqrt(rng.r(R0 * R0, R1 * R1))
        a = k * span + rng.r(0, span)
        x, y = r * math.cos(a), r * math.sin(a)
        if any((x - cx) ** 2 + (y - cy) ** 2 < cr * cr for cx, cy, cr in CLEAR):
            continue
        placed += 1
        tall = smooth(R0, 9800.0, r)
        H = (420 + 4600 * tall) * rng.r(0.6, 1.25)
        wid = rng.r(90, 150) + 60 * tall
        bend = rng.r(0.15, 0.5) * H
        face = rng.r(0, 2 * math.pi)
        fx, fy = math.cos(face), math.sin(face)
        mat = "GrassA" if rng.f() < 0.55 else ("GrassB" if rng.f() < 0.75 else "GrassDry")
        base = (x, y, -30)

        def blade(u, v, base=base, H=H, wid=wid, bend=bend, fx=fx, fy=fy):
            w = wid * (1.0 - v ** 1.5) * 0.5
            off = (u - 0.5) * 2 * w
            fold = abs(u - 0.5) * 2 * w * 0.3
            lean = bend * v * v
            return (base[0] + fx * lean - fy * off, base[1] + fy * lean + fx * off, base[2] + H * v * (1 - 0.15 * v * v) + fold)
        m.grid(mat, 2, 8 if H > 1500 else 4, blade, uv_fn=lambda u, v: (u, v))
    return m


def plank_box(m, mat, c, sx, sy, sz, yaw, n=0.18):
    """Soft rounded block (superellipsoid) - Pixar-style bevelled wood."""
    ca, sa = math.cos(yaw), math.sin(yaw)

    def deform(p, d):
        q = [math.copysign(abs(d[i]) ** n, d[i]) for i in range(3)]
        lx, ly, lz = q[0] * sx, q[1] * sy, q[2] * sz
        return (lx * ca - ly * sa, lx * sa + ly * ca, lz)
    ellipsoid(m, mat, c, (1, 1, 1), 16, 12, deform=deform)


def fence(seed, R=17800.0, plank_w=950.0):
    """Weathered backyard fence ringing the garden, like the one behind Turbo's tomato patch."""
    m = Mesh()
    rng = Rng(seed)
    n = int(2 * math.pi * R / (plank_w + 70))
    for i in range(n):
        a = 2 * math.pi * i / n
        H = 9000 + rng.r(-250, 250)
        lean = rng.r(-0.012, 0.012)
        mat = "FenceWood" if rng.f() < 0.8 else "FenceWoodDark"
        c = (R * math.cos(a), R * math.sin(a), H * 0.5 - 200)
        plank_box(m, mat, c, 60, plank_w * 0.5, H * 0.5, a + lean)
        # rounded cap
        plank_box(m, mat, (c[0], c[1], H - 200), 62, plank_w * 0.5, 160, a, n=0.5)
    for z in (1800, 6800):
        for i in range(n):
            a0 = 2 * math.pi * i / n
            a1 = 2 * math.pi * (i + 1) / n
            am = (a0 + a1) * 0.5
            Rr = R + 140
            ln = Rr * (a1 - a0) * 0.5 + 30
            plank_box(m, "FenceWoodDark", (Rr * math.cos(am), Rr * math.sin(am), z), 70, ln, 220, am)
    return m


def turbo_main():
    jobs = {"SM_GrassCarpet_%02d" % k: (lambda k=k: grass_sector(41 + k * 13, k)) for k in range(SECTORS)}
    jobs["SM_BackyardFence"] = lambda: fence(7)
    for name, fn in jobs.items():
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


def main():
    jobs = {
        "SM_TomatoPlant_A": lambda: tomato_plant(3),
        "SM_TomatoPlant_B": lambda: tomato_plant(8, 8600.0),
        "SM_FallenTomato": lambda: fallen_tomato(5),
        "SM_CherryTomato": lambda: fallen_tomato(12, 480.0),
    }
    for name, fn in jobs.items():
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


if __name__ == "__main__":
    import sys
    turbo_main() if "carpet" in sys.argv else main()
