"""Generates the Garden Arena meshes: a bug-scale garden bed fenced by log-roll edging."""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_norm

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)

R_IN = 6000.0
PANELS = 24
LOGS = 7
LOG_R = 2 * math.pi * (R_IN + 112.0) / (PANELS * LOGS) * 0.5   # touching logs


def log(m, cx, cy, H, R, seed, z0=-120.0):
    """Vertical log with bark ridges and a cut top (WoodEnd, UV centred)."""
    rng = Rng(seed)
    ph = [rng.r(0, 6.28) for _ in range(4)]

    def rad(a, z):
        return R * (1.0 + 0.035 * math.sin(a * 13 + ph[0] + z * 0.004) + 0.02 * math.sin(a * 29 + ph[1])
                    + 0.015 * math.sin(z * 0.02 + ph[2]))
    top = H

    def side(u, v):
        a = u * 2 * math.pi
        z = z0 + (top - z0) * v
        r = rad(a, z)
        return (cx + r * math.cos(a), cy + r * math.sin(a), z)
    m.grid("Bark", 36, 14, side, uv_fn=lambda u, v: (u * 3, v * (top - z0) / 300.0), wrap_u=True, flip=False)
    # bevelled cut top
    rings = [(1.0, top), (0.96, top + 8), (0.0, top + 14 + rng.r(-4, 4))]
    prev = None
    for k, (f, z) in enumerate(rings):
        row = []
        for i in range(36):
            a = 2 * math.pi * i / 36
            r = rad(a, top) * f
            uvr = 0.5 * (0.93 if k == 1 else (1.0 if k == 0 else 0.0))
            mat_uv = (0.5 + uvr * math.cos(a), 0.5 + uvr * math.sin(a))
            row.append(m.vert((cx + r * math.cos(a), cy + r * math.sin(a), z), mat_uv))
        if prev:
            for i in range(36):
                i2 = (i + 1) % 36
                m.quad("WoodEnd", prev[i], prev[i2], row[i2], row[i])
        prev = row


def log_panel(seed):
    m = Mesh()
    rng = Rng(seed)
    step = 2 * math.pi / (PANELS * LOGS)
    for i in range(LOGS):
        a = step * (i + 0.5)
        H = rng.r(950, 1350)
        d = R_IN + LOG_R
        log(m, d * math.cos(a), d * math.sin(a), H, LOG_R * 1.01, seed * 31 + i)
    return m


def tree_stump():
    m = Mesh()
    H, R = 166.0, 880.0
    rng = Rng(77)

    def rad(a, z):
        flare = 1.0 + 0.18 * max(0.0, 1.0 - (z + 40) / 140.0) ** 2
        return R * flare * (1.0 + 0.03 * math.sin(a * 9 + 1.0) + 0.012 * math.sin(a * 41))

    def side(u, v):
        a = u * 2 * math.pi
        z = -60 + (H + 60) * v
        r = rad(a, z)
        return (r * math.cos(a), r * math.sin(a), z)
    m.grid("Bark", 96, 8, side, uv_fn=lambda u, v: (u * 14, v), wrap_u=True, flip=False)
    prev = None
    for k, (f, dz, uvr) in enumerate([(1.0, 0, 0.5), (0.97, 6, 0.47), (0.0, 10, 0.0)]):
        row = []
        for i in range(96):
            a = 2 * math.pi * i / 96
            r = rad(a, H) * f
            row.append(m.vert((r * math.cos(a), r * math.sin(a), H + dz), (0.5 + uvr * math.cos(a), 0.5 + uvr * math.sin(a))))
        if prev:
            for i in range(96):
                i2 = (i + 1) % 96
                m.quad("WoodEnd", prev[i], prev[i2], row[i2], row[i])
        prev = row
    # roots between the ramps (ramps arrive at 30, 150, 270 deg)
    for base_ang in (90, 210, 330, 0, 120, 240):
        ang = math.radians(base_ang + rng.r(-14, 14))
        L = rng.r(500, 900)
        pts = []
        for s in [i / 8 for i in range(9)]:
            d = R * 0.92 + L * s
            z = 70 * (1 - s) ** 1.5 - 18
            pts.append((d * math.cos(ang) + 40 * math.sin(s * 5) * -math.sin(ang),
                        d * math.sin(ang) + 40 * math.sin(s * 5) * math.cos(ang), z))
        tube_along(m, "Bark", pts, [95 * (1 - s) ** 0.8 + 12 for s in [i / 8 for i in range(9)]], segs=14)
    return m


def pot_profile(H=1100.0, rb=380.0, rt=520.0, wall=34.0, lip=70.0):
    """Returns outer and inner radius functions along the pot axis (0 = base, H = rim)."""
    def outer(x):
        r = rb + (rt - rb) * x / H
        if x > H - lip:
            r += 40.0
        return r

    def inner(x):
        return rb + (rt - rb) * x / H - wall
    return outer, inner


def pot_tunnel():
    """Terracotta pot lying on its side with the base broken out: a drive-through tunnel."""
    m = Mesh()
    H = 1100.0
    outer, inner = pot_profile(H)
    wall = 34.0
    segs = 64
    xs = [0, 60, 200, 400, 600, 800, H - 70, H - 69, H - 10, H]

    def centre_z(x):
        return outer(min(x, H - 71)) - wall - 4.0   # outer bottom line sits just under the ground

    def ring(x, r, lump):
        pts = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            rr = r * (1 + lump * math.sin(a * 7 + x * 0.01))
            pts.append((x - H / 2, rr * math.sin(a), centre_z(x) + rr * math.cos(a)))
        return pts

    orings = [[m.vert(p, (i / segs * 4, x / 400.0)) for i, p in enumerate(ring(x, outer(x), 0.004))] for x in xs]
    irings = [[m.vert(p, (i / segs * 4, x / 400.0)) for i, p in enumerate(ring(x, inner(min(x, H - 10)), 0.0))] for x in xs]
    for j in range(len(xs) - 1):
        for i in range(segs):
            i2 = (i + 1) % segs
            a, b, c, d = orings[j][i], orings[j][i2], orings[j + 1][i2], orings[j + 1][i]
            m.quad("Terracotta", a, d, c, b)       # outward
            a, b, c, d = irings[j][i], irings[j][i2], irings[j + 1][i2], irings[j + 1][i]
            m.quad("TerracottaIn", a, b, c, d)     # inward
    # rim faces (both ends), base end is jagged where it broke
    rng = Rng(5)
    for end in (0, len(xs) - 1):
        o, inn = orings[end], irings[end]
        for i in range(segs):
            i2 = (i + 1) % segs
            if end == 0:
                m.quad("Terracotta", o[i], o[i2], inn[i2], inn[i])
            else:
                m.quad("Terracotta", o[i], inn[i], inn[i2], o[i2])
    return m


def flower_pot():
    """Upright pot filled with soil (outside decor)."""
    m = Mesh()
    H = 1100.0
    outer, inner = pot_profile(H)
    segs = 48

    def side(u, v):
        a = u * 2 * math.pi
        x = H * v
        r = outer(x)
        return (r * math.cos(a), r * math.sin(a), x - 40)
    m.grid("Terracotta", segs, 12, side, uv_fn=lambda u, v: (u * 4, v * 3), wrap_u=True, flip=False)

    def rimtop(u, v):
        a = u * 2 * math.pi
        r = outer(H) * (1 - v) + inner(H) * v
        return (r * math.cos(a), r * math.sin(a), H - 40)
    m.grid("Terracotta", segs, 1, rimtop, wrap_u=True, flip=False)

    def soil(u, v):
        a = u * 2 * math.pi
        r = inner(H) * (1 - v)
        return (r * math.cos(a), r * math.sin(a), H - 120 + 25 * v * v + 6 * math.sin(a * 5) * (1 - v))
    m.grid("Soil", segs, 6, soil, wrap_u=True, flip=False)
    return m


def acorn(seed):
    m = Mesh()
    rng = Rng(seed)
    L = rng.r(230, 290)

    def nut(p, d):
        k = 1.0 - 0.25 * max(0.0, -d[2]) ** 2
        return (p[0] * k, p[1] * k, p[2])
    ellipsoid(m, "Acorn", (0, 0, 0), (L * 0.36, L * 0.36, L * 0.5), 32, 20, nut)

    def cap(p, d):
        k = 1.0 + 0.04 * math.sin(d[0] * 30) * math.sin(d[1] * 30) * math.sin(d[2] * 30)
        return (p[0] * k, p[1] * k, max(p[2], -L * 0.05) * k)
    ellipsoid(m, "AcornCap", (0, 0, L * 0.33), (L * 0.40, L * 0.40, L * 0.22), 32, 14, cap)
    tube_along(m, "AcornCap", [(0, 0, L * 0.5), (6, 0, L * 0.6), (14, 0, L * 0.68)], [10, 8, 6], segs=8)
    return m


def clover(seed):
    m = Mesh()
    rng = Rng(seed)
    H = rng.r(120, 260)
    tube_along(m, "Clover", catmull([(0, 0, -5), (10, 0, H * 0.6), (0, 0, H)], 4), [10, 9, 8, 7, 7, 6, 6, 6, 5], segs=6)
    for k in range(3):
        a0 = math.radians(k * 120 + rng.r(-10, 10))
        L = rng.r(200, 260)

        def leafl(u, v, a0=a0, L=L):
            s = v
            # heart-shaped leaflet: two lobes at the outer end
            w = L * 0.55 * math.sin(math.pi * s) ** 0.7 * (0.6 + 0.4 * s)
            off = (u - 0.5) * w
            notch = 0.12 * L * math.exp(-((u - 0.5) / 0.12) ** 2) * s ** 6
            r = s * L - notch
            z = H + 25 * math.sin(s * 2.5) - 8 * ((u - 0.5) * 2) ** 2 * s
            return (r * math.cos(a0) - off * math.sin(a0), r * math.sin(a0) + off * math.cos(a0), z)
        m.grid("Clover", 6, 10, leafl, uv_fn=lambda u, v: (u, v))
    return m


def stepping_stone(seed, R=320.0, Hs=24.0):
    m = Mesh()
    rng = Rng(seed)
    ph = [rng.r(0, 6.28) for _ in range(3)]

    def rim(a):
        return R * (1 + 0.08 * math.sin(3 * a + ph[0]) + 0.05 * math.sin(5 * a + ph[1]) + 0.03 * math.sin(9 * a + ph[2]))

    def top(u, v):
        a = u * 2 * math.pi
        rho = 1 - (1 - v) ** 1.5
        z = Hs * (1 - rho ** 6) ** 0.5 + 2.5 * math.sin(a * 4 + rho * 6) * rho
        return (rim(a) * rho * math.cos(a), rim(a) * rho * math.sin(a), z - 2)
    m.grid("Stone", 64, 8, top, uv_fn=lambda u, v: (0.5 + 0.5 * v * math.cos(u * 6.28), 0.5 + 0.5 * v * math.sin(u * 6.28)),
           wrap_u=True, flip=True)
    return m


def rain_puddle(seed):
    m = Mesh()
    rng = Rng(seed)
    ph = [rng.r(0, 6.28) for _ in range(4)]

    def rim(a):
        return 900 * (1 + 0.15 * math.sin(2 * a + ph[0]) + 0.1 * math.sin(3 * a + ph[1]) + 0.05 * math.sin(7 * a + ph[2]))

    def top(u, v):
        a = u * 2 * math.pi
        return (rim(a) * v * math.cos(a), rim(a) * v * math.sin(a), 1.5)
    m.grid("Water", 96, 4, top, uv_fn=lambda u, v: (0.5 + 0.5 * v * math.cos(u * 6.28), 0.5 + 0.5 * v * math.sin(u * 6.28)),
           wrap_u=True, flip=True)
    return m


def main():
    jobs = {
        "SM_LogBorder_A": lambda: log_panel(3),
        "SM_LogBorder_B": lambda: log_panel(8),
        "SM_LogBorder_C": lambda: log_panel(15),
        "SM_TreeStump": tree_stump,
        "SM_PotTunnel": pot_tunnel,
        "SM_FlowerPot": flower_pot,
        "SM_Acorn_A": lambda: acorn(2),
        "SM_Acorn_B": lambda: acorn(9),
        "SM_Clover_A": lambda: clover(1),
        "SM_Clover_B": lambda: clover(6),
        "SM_SteppingStone_A": lambda: stepping_stone(4),
        "SM_SteppingStone_B": lambda: stepping_stone(11, 260),
        "SM_RainPuddle": lambda: rain_puddle(3),
    }
    for name, fn in jobs.items():
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


if __name__ == "__main__":
    main()
