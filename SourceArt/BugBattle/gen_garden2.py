"""Generates the Garden 2 map (Lvl_Garden2): a bug's-eye backyard dirt loop modelled on the
D:/REF_Images references - rutted sandy track round a pebble/bottle-cap island, a drive-through
soda can, fallen mossy logs and branches, brown mushrooms, dandelion clocks, clover and a wall of
giant grass blades, with a fence, house and trees far behind in the golden haze.

python gen_garden2.py            -> obj/garden2/*.obj + garden2_plan.json (actor placements)
"""
import json, math, os
from meshlib import Mesh, tube_along, catmull, Rng, v_add, v_sub, v_mul, v_dot, v_cross, v_norm

OUT = os.path.join(os.path.dirname(__file__), "obj", "garden2")
os.makedirs(OUT, exist_ok=True)
TAU = 2 * math.pi


# ---------- helpers ----------

def smooth(e0, e1, x):
    k = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return k * k * (3 - 2 * k)


def _h(ix, iy, seed):
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n ^ (n >> 16)) / 4294967296.0


def vnoise(x, y, seed=0):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _h(ix, iy, seed), _h(ix + 1, iy, seed)
    c, d = _h(ix, iy + 1, seed), _h(ix + 1, iy + 1, seed)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


def fbm(x, y, seed=0, oct=4):
    s, amp, tot = 0.0, 0.5, 0.0
    for k in range(oct):
        s += amp * vnoise(x, y, seed + k * 17)
        tot += amp
        x, y, amp = x * 2.03 + 5.3, y * 2.03 + 1.7, amp * 0.5
    return s / tot


def patch(m, mat, nu, nv, fn, out, wrap_u=False, uv_fn=None):
    """m.grid, but the front face is chosen to agree with out(p) sampled mid-patch."""
    u, v, e = 0.37, 0.53, 1e-3
    p = fn(u, v)
    n = v_cross(v_sub(fn(u + e, v), p), v_sub(fn(u, v + e), p))
    return m.grid(mat, nu, nv, fn, uv_fn=uv_fn, wrap_u=wrap_u, flip=v_dot(n, out(p)) < 0)


def lathe_z(m, mat, prof, nu, nv, sign=1, c=(0, 0, 0), up=None):
    """Surface of revolution round Z. prof(v, a) -> (r, z). Faces point radially out (sign=1) or in (-1);
    up=+1/-1 instead makes it face up/down (discs)."""
    def fn(u, v):
        a = u * TAU
        r, z = prof(v, a)
        return (c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2] + z)
    if up:
        out = lambda p: (0, 0, up)
    else:
        out = lambda p: (sign * (p[0] - c[0]), sign * (p[1] - c[1]), 0)
    return patch(m, mat, nu, nv, fn, out, wrap_u=True)


def blob(m, mat, c, radii, nu, nv, rough, seed, flat_bottom=None):
    """Rounded noisy pebble/boulder. flat_bottom: clamp z below this (local) to sit on the ground."""
    ph = [Rng(seed).r(0, 6.28) for _ in range(6)]

    def fn(u, v):
        th, a = v * math.pi, u * TAU
        d = (math.sin(th) * math.cos(a), math.sin(th) * math.sin(a), math.cos(th))
        k = 1 + rough * (0.6 * math.sin(3 * a + ph[0]) * math.sin(2 * th + ph[1]) + 0.4 * math.sin(5 * a + ph[2]) * math.sin(4 * th + ph[3]))
        p = [d[0] * radii[0] * k, d[1] * radii[1] * k, d[2] * radii[2] * k]
        if flat_bottom is not None and p[2] < flat_bottom:
            p[2] = flat_bottom + (p[2] - flat_bottom) * 0.15
        return (c[0] + p[0], c[1] + p[1], c[2] + p[2])
    return patch(m, mat, nu, nv, fn, lambda p: v_sub(p, c), wrap_u=True)


def rot_z(p, yaw):
    ca, sa = math.cos(yaw), math.sin(yaw)
    return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2])


def xform_mesh(src, pos, yaw=0.0, s=1.0):
    def xf(p, n):
        q = rot_z((p[0] * s, p[1] * s, p[2] * s), yaw)
        return (q[0] + pos[0], q[1] + pos[1], q[2] + pos[2]), (rot_z(n, yaw) if n else None)
    return xf


# ---------- arena layout ----------

# open arena sized like Lvl_GardenArena: the whole disc out to ~r 6000 (its log wall) is drivable dirt,
# with the props scattered over it instead of piled on a centre island
ARENA_R = 6000.0
START_R = 4300.0     # player starts sit on the same r 4300 ring as Lvl_GardenArena


def edge_r(th):
    return ARENA_R + 120 * math.sin(3 * th + 0.6) + 60 * math.sin(5 * th + 2.1)


RUT_R = (1300, 1750, 2350, 2800, 3500, 3950, 4650, 5100, 5550)   # broken worn rings where cars circle


def ground_h(x, y):
    r = math.hypot(x, y)
    th = math.atan2(y, x)
    d = r - edge_r(th)
    track = 1 - smooth(-220, 160, d)
    ruts = 0.0
    for k, o in enumerate(RUT_R):
        oc = o + 55 * math.sin(th * 4 + o * 0.013)
        ruts -= 15.0 * math.exp(-((r - oc) / 55.0) ** 2) * smooth(0.42, 0.58, fbm(x / 1400.0, y / 1400.0, 50 + k, 2))
    micro = 6 * (fbm(x / 260.0, y / 260.0, 3, 3) - 0.5)
    berm = 42 * math.exp(-((d - 140) / 180.0) ** 2) * (0.55 + 0.9 * fbm(x / 900.0, y / 900.0, 9, 2))
    und = 70 * (fbm(x / 2600.0, y / 2600.0, 21, 3) - 0.5)
    return track * (ruts + micro) + berm + (1 - track) * und


def on_track(x, y, margin=0.0):
    return math.hypot(x, y) < edge_r(math.atan2(y, x)) + margin


def ground():
    m = Mesh()
    rs = [0.0, 150.0]
    r = 300.0
    while r < 19500:
        rs.append(r)
        r += 160 if r < 1200 else (32 if r < 6600 else (160 if r < 9000 else 520))
    segs = 576
    rows = []
    for r in rs:
        row = []
        for i in range(segs):
            a = TAU * i / segs
            x, y = r * math.cos(a), r * math.sin(a)
            row.append(m.vert((x, y, ground_h(x, y)), (x / 800.0, y / 800.0)))
        rows.append(row)
    for j in range(len(rs) - 1):
        for i in range(segs):
            i2 = (i + 1) % segs
            am = TAU * (i + 0.5) / segs
            rm = (rs[j] + rs[j + 1]) * 0.5
            mat = "TrackDirt" if on_track(rm * math.cos(am), rm * math.sin(am), 230) else "Soil"
            a, b, c, d = rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]
            m.quad(mat, a, d, c, b)
    return m


# ---------- soda can tunnel ----------

def soda_can(R=820.0, L=2900.0, wall=22.0, seed=5):
    """Battered tipped-over red soda can, open both ends, white shard graphics, dirt banked up its sides."""
    m = Mesh()
    rng = Rng(seed)
    segs, nx = 96, 46
    neck = 230.0
    cz = R - 10.0
    dents = [(rng.r(-900, 900), rng.r(0.6, TAU - 0.6), rng.r(25, 70), rng.r(160, 320), rng.r(0.25, 0.5)) for _ in range(7)]
    dents.append((1050, 0.0, 60, 260, 0.4))      # crumple on top near one end

    def prof_r(x):
        ax = L / 2 - abs(x)
        if ax < neck * 0.5:
            return R - 70 + 52 * smooth(0, neck * 0.5, ax)
        return R - 18 + 18 * smooth(neck * 0.5, neck, ax)

    def dent(x, a):
        s = 0.0
        for dx, da, dd, sx, sa in dents:
            daa = math.atan2(math.sin(a - da), math.cos(a - da))
            s += dd * math.exp(-((x - dx) / sx) ** 2 - (daa / sa) ** 2)
        return s * smooth(L / 2, L / 2 - neck * 1.5, abs(x))

    def P(x, a, off=0.0):
        r = prof_r(x) - dent(x, a) + off
        return (x, r * math.sin(a), cz + r * math.cos(a))
    xs = [-L / 2 + L * k / nx for k in range(nx + 1)]

    def band(mat, x0, x1, off, out_sign, n):
        fn = lambda u, v: P(x0 + (x1 - x0) * v, u * TAU, off)
        patch(m, mat, segs, n, fn, lambda p: (0, out_sign * p[1], out_sign * (p[2] - cz)), wrap_u=True)
    body0, body1 = -L / 2 + neck * 1.1, L / 2 - neck * 1.1
    band("CanMetal", -L / 2, body0, 0, 1, 8)
    band("CanRed", body0, body1, 0, 1, 36)
    band("CanMetal", body1, L / 2, 0, 1, 8)
    band("CanInside", -L / 2, L / 2, -wall, -1, nx)
    # rolled rims
    for x0, sg in ((-L / 2, -1), (L / 2, 1)):
        def rim(u, v, x0=x0, sg=sg):
            a = u * TAU
            t = math.pi * v
            r = prof_r(x0) - wall * 0.5 + (wall * 0.5 + 12) * math.cos(t)
            x = x0 + sg * 22 * math.sin(t)
            return (x, r * math.sin(a), cz + r * math.cos(a))
        patch(m, "CanMetal", segs, 6, rim, lambda p, x0=x0: (p[0] - x0 * 0.98, p[1], p[2] - cz), wrap_u=True)
    # white shard graphics: a zigzag of long triangles round the label plus a few smaller flecks
    def tri(p0, p1, p2):
        def fn(u, v):
            q = [p1[k] * (1 - v) + p2[k] * v for k in range(2)]
            x = p0[0] * (1 - u) + q[0] * u
            a = p0[1] * (1 - u) + q[1] * u
            return P(x, a, 3.0)
        patch(m, "CanWhite", 5, 5, fn, lambda p: (0, p[1], p[2] - cz))
    n = 7
    for k in range(n):
        a0 = TAU * k / n + 0.2
        a1 = a0 + TAU / n
        tri((-560, a0), (380, a0 + 0.05), (520, a0 + TAU / n * 0.55))
        tri((640, a1 - 0.1), (-300, a0 + TAU / n * 0.45), (-460, a1 - 0.02))
    for k in range(9):
        x, a = rng.r(-1000, 1000), rng.r(0, TAU)
        tri((x, a), (x + rng.r(120, 260), a + rng.r(0.1, 0.2)), (x + rng.r(-60, 60), a + rng.r(0.25, 0.4)))
    # dirt banked against both sides (stops cars wedging under the curve)
    x0, x1 = -L / 2 + neck * 0.3, L / 2 - neck * 0.3
    for side in (1, -1):
        def bank(u, v, side=side):
            x = x0 + (x1 - x0) * u
            tp = smooth(0.0, 0.16, u) * smooth(1.0, 0.84, u)
            phi = math.radians(22 + 46 * tp)
            r = prof_r(x) - dent(x, side * phi)
            top = (x, side * r * math.sin(phi), cz - r * math.cos(phi) - 6)
            foot = (x, side * (r * math.sin(phi) + 160 + 520 * tp), -25)
            b = 1 - v
            hump = 50 * math.sin(math.pi * v) * tp
            return (x, top[1] * b + foot[1] * v, top[2] * b + foot[2] * v + hump)
        patch(m, "CanDirt", 30, 6, bank, lambda p: (0, 0, 1))
    return m


# ---------- bottle caps ----------

def bottle_cap(R=300.0, H=120.0, flutes=21):
    m = Mesh()
    nu = flutes * 6

    def crimp(a):
        return abs(math.sin(flutes * a / 2)) ** 0.7

    def skirt_r(a, z, inner=0.0):
        f = 1 - z / H
        return R * (1 + 0.075 * crimp(a) * f ** 0.6) + 10 * f - inner
    # domed top with a pressed ring near the edge
    lathe_z(m, "CapPaint", lambda v, a: (R * 0.93 * v, H + 6 * (1 - v * v) - 5 * math.exp(-((v - 0.82) / 0.05) ** 2)), nu, 10, up=1)
    lathe_z(m, "CapPaint", lambda v, a: (R * 0.93 + R * 0.07 * math.sin(v * math.pi / 2), H - 22 * (1 - math.cos(v * math.pi / 2))), nu, 4)
    lathe_z(m, "CapPaint", lambda v, a: (skirt_r(a, (H - 22) * (1 - v)), (H - 22) * (1 - v)), nu, 8)
    # bare metal rolled lip, inside wall, cork liner
    lathe_z(m, "CapMetal", lambda v, a: (skirt_r(a, 0) - 9 * v, -3 * math.sin(v * math.pi)), nu, 3, up=-1)
    lathe_z(m, "CapMetal", lambda v, a: (skirt_r(a, (H - 14) * v, 9), (H - 14) * v), nu, 6, sign=-1)
    lathe_z(m, "CapLiner", lambda v, a: ((R - 12) * (1 - v), H - 14), nu, 6, up=-1)
    return m


# ---------- mushrooms ----------

def mushroom(m, base, H, Rcap, seed, lean=(0.0, 0.0)):
    rng = Rng(seed)
    capH = Rcap * rng.r(0.42, 0.55)
    rs = Rcap * rng.r(0.16, 0.2)
    ph = rng.r(0, 6.28)
    top = (base[0] + lean[0], base[1] + lean[1], base[2] + H)

    def stem_pt(t):
        return (base[0] + lean[0] * t * t, base[1] + lean[1] * t * t, base[2] - 40 + (H - capH * 0.35 + 40) * t)
    pts = [stem_pt(i / 12) for i in range(13)]
    radii = [rs * (1.35 - 0.3 * t + 0.35 * math.exp(-((t - 0.02) / 0.1) ** 2)) for t in (i / 12 for i in range(13))]
    tube_along(m, "MushStem", pts, radii, segs=24, cap=False)

    def edge(a):
        return Rcap * (1 + 0.045 * math.sin(5 * a + ph) + 0.025 * math.sin(11 * a + ph * 2))
    zc = top[2] - capH * 0.35

    def cap(u, v):
        a = u * TAU
        th = v * math.pi / 2 * 1.04
        r = edge(a) * math.sin(th)
        z = zc + capH * max(0.0, math.cos(th)) ** 0.75 + 0.06 * capH * math.sin(v * math.pi) ** 2
        if v > 0.9:
            z += capH * 0.12 * (v - 0.9) / 0.1      # slightly upturned rim
        return (top[0] + r * math.cos(a), top[1] + r * math.sin(a), z)
    patch(m, "MushCap", 64, 18, cap, lambda p: (p[0] - top[0], p[1] - top[1], p[2] - zc + capH * 0.3), wrap_u=True)

    def gills(u, v):
        a = u * TAU
        rim = cap(u, 1.0)
        rr = edge(a) * 1.0 * (1 - v) + rs * 1.05 * v
        z = rim[2] * (1 - v) + (zc - capH * 0.02) * v - 18 * abs(math.sin(a * 45)) * math.sin(v * math.pi)
        return (top[0] + rr * math.cos(a), top[1] + rr * math.sin(a), z)
    patch(m, "MushGill", 270, 6, gills, lambda p: (0, 0, -1), wrap_u=True)


def mushroom_single(seed, H, Rcap):
    m = Mesh()
    rng = Rng(seed)
    mushroom(m, (0, 0, 0), H, Rcap, seed, (rng.r(-0.12, 0.12) * H, rng.r(-0.12, 0.12) * H))
    return m


def mushroom_cluster(seed):
    m = Mesh()
    rng = Rng(seed)
    for k in range(5):
        a = rng.r(0, TAU)
        d = 0 if k == 0 else rng.r(350, 900)
        s = 1.0 if k == 0 else rng.r(0.35, 0.7)
        mushroom(m, (d * math.cos(a), d * math.sin(a), 0), 1500 * s, 800 * s, seed * 7 + k,
                 (math.cos(a) * 160 * s, math.sin(a) * 160 * s))
    return m


# ---------- plants ----------

def align(p, n):
    z = v_norm(n)
    x = v_norm(v_cross((0, 0, 1) if abs(z[2]) < 0.95 else (1, 0, 0), z))
    y = v_cross(z, x)
    return (x[0] * p[0] + y[0] * p[1] + z[0] * p[2], x[1] * p[0] + y[1] * p[1] + z[1] * p[2], x[2] * p[0] + y[2] * p[1] + z[2] * p[2])


def toothed_leaf(m, rng, base, L, Wd, ang, mat, teeth=6, arch=0.6):
    """Dandelion-style leaf: long strap with backward-pointing teeth, arching out from the rosette."""
    def f(u, v, ang=ang):
        s = v
        tooth = 0.55 + 0.45 * abs(math.sin(s * teeth * math.pi)) ** 1.5
        w = Wd * math.sin(math.pi * min(s * 1.08, 1.0)) ** 0.6 * tooth
        off = (u - 0.5) * w
        r = L * s
        z = L * arch * (0.8 * s - 0.9 * s * s) + abs(u - 0.5) * w * 0.3
        return (base[0] + r * math.cos(ang) - off * math.sin(ang), base[1] + r * math.sin(ang) + off * math.cos(ang), base[2] + z)
    patch(m, mat, 4, 18, f, lambda p: (0, 0, 1))


def dandelion(seed, H=6200.0, R=760.0, N=950):
    m = Mesh()
    rng = Rng(seed)
    lean = 420
    ctrl = [(0, 0, -60), (rng.r(-lean, lean) * 0.3, rng.r(-lean, lean) * 0.3, H * 0.5), (rng.r(-lean, lean), rng.r(-lean, lean), H)]
    pts = catmull(ctrl, 12)
    tube_along(m, "Stem", pts, [62 - 18 * i / (len(pts) - 1) for i in range(len(pts))], segs=12)
    head = v_add(pts[-1], (0, 0, 110))
    # seed receptacle + soft inner haze ball so the clock reads dense and glows in back light
    blob(m, "Pod", head, (130, 130, 115), 18, 12, 0.05, seed)
    blob(m, "FluffCore", head, (R * 0.38, R * 0.38, R * 0.38), 28, 18, 0.03, seed + 1)
    golden = math.pi * (3 - math.sqrt(5))
    for k in range(N):
        y = 1 - 2 * (k + 0.5) / N
        if y < -0.62:
            continue
        rr = math.sqrt(1 - y * y)
        th = golden * k
        d = (rr * math.cos(th), rr * math.sin(th), y)
        Rk = R * rng.r(0.78, 1.06)
        tip = v_add(head, v_mul(d, Rk))
        tube_along(m, "Fluff", [v_add(head, v_mul(d, 120)), tip], [5, 3], segs=3, cap=False)

        def umb(u, v, tip=tip, d=d):
            a = u * TAU
            r = 150 * v
            return v_add(tip, align((r * math.cos(a), r * math.sin(a), 60 * v ** 0.55), d))
        m.grid("Fluff", 8, 2, umb, wrap_u=True, flip=True)
    for k in range(7):
        toothed_leaf(m, rng, (0, 0, -20), rng.r(1400, 2100), rng.r(280, 380), rng.r(0, TAU), "Leaf", arch=rng.r(0.35, 0.7))
    return m


def clover_plant(seed, n=5, Hmin=900.0, Hmax=3000.0):
    """Clump of giant white-clover leaves: trios of heart-shaped leaflets on arching stalks."""
    m = Mesh()
    rng = Rng(seed)
    for t in range(n):
        H = rng.r(Hmin, Hmax)
        a0 = rng.r(0, TAU)
        off = (rng.r(-260, 260), rng.r(-260, 260), -30)
        lean = H * rng.r(0.08, 0.22)
        top = v_add(off, (lean * math.cos(a0), lean * math.sin(a0), H))
        stalk = catmull([off, v_add(off, (lean * 0.2 * math.cos(a0), lean * 0.2 * math.sin(a0), H * 0.55)), top], 6)
        tube_along(m, "CloverStem", stalk, [32 - 10 * i / (len(stalk) - 1) for i in range(len(stalk))], segs=8)
        L = rng.r(560, 900) * (0.7 + 0.3 * H / Hmax)
        tilt = rng.r(0.05, 0.3)
        for k in range(3):
            ak = a0 + math.radians(k * 120 + rng.r(-12, 12))

            def leaf(u, v, ak=ak, L=L):
                s = v
                w = L * 0.95 * math.sin(math.pi * s) ** 0.75 * (0.45 + 0.55 * s)
                off_ = (u - 0.5) * w
                notch = 0.16 * L * math.exp(-((u - 0.5) / 0.1) ** 2) * s ** 5
                r = s * L - notch
                cup = 0.07 * L * ((u - 0.5) * 2) ** 2
                z = top[2] + L * tilt * s * (1 - s * 0.6) + cup - 0.12 * L * s * s
                return (top[0] + r * math.cos(ak) - off_ * math.sin(ak), top[1] + r * math.sin(ak) + off_ * math.cos(ak), z)
            patch(m, "Clover", 8, 12, leaf, lambda p: (0, 0, 1))
            # pale chevron mark that white clover carries on each leaflet
            def mark(u, v, ak=ak, L=L):
                s = 0.42 + 0.1 * v
                p = leaf(0.5 + (u - 0.5) * 0.7, s)
                bend = 0.06 * L * abs(u - 0.5) * 2
                return (p[0] - bend * math.cos(ak), p[1] - bend * math.sin(ak), p[2] + 2.5)
            patch(m, "CloverMark", 6, 1, mark, lambda p: (0, 0, 1))
    return m


def blade(m, mat, base, H, Wd, face, bend, fold=0.22, nv=10, twist=0.0):
    """Grass blade with a V-fold midrib, tapering to a point and arching over toward `face`."""
    fx, fy = math.cos(face), math.sin(face)
    sx, sy = -fy, fx

    def fn(u, v):
        w = Wd * (1 - v ** 2.2) ** 0.7 * (0.75 + 0.25 * smooth(0, 0.15, v))
        off = (u - 0.5) * w
        tw = twist * v
        ox, oy = sx * math.cos(tw) - fx * math.sin(tw), sy * math.cos(tw) - fy * math.sin(tw)
        lean = bend * v * v
        drop = H * (0.2 * v * v * bend / max(H, 1.0))
        vf = fold * w * (1 - abs(u - 0.5) * 2)
        return (base[0] + fx * (lean - vf) + ox * off, base[1] + fy * (lean - vf) + oy * off, base[2] + H * v * (1 - 0.18 * v * v) - drop)
    patch(m, mat, 2, nv, fn, lambda p: (fx, fy, 0.3))


GRASS_MATS = ("GrassA", "GrassA", "GrassB", "GrassB", "GrassDry")
G_R0, G_R1, SECTORS = 6500.0, 17300.0, 12
CLEAR = []           # (x, y, r) filled by layout(): logs, dandelions etc. sitting in the grass


def grass_sector(k, seed):
    m = Mesh()
    rng = Rng(seed)
    span = TAU / SECTORS
    tall, fringe = 0, 0
    tries = 0
    while (tall < 1900 or fringe < 900) and tries < 30000:
        tries += 1
        is_fringe = fringe < 900 and (tall >= 1900 or rng.f() < 0.35)
        if is_fringe:
            r = rng.r(6050, 7300)
        else:
            r = math.sqrt(rng.r(G_R0 ** 2, G_R1 ** 2))
        a = k * span + rng.r(0, span)
        x, y = r * math.cos(a), r * math.sin(a)
        if any((x - cx) ** 2 + (y - cy) ** 2 < cr * cr for cx, cy, cr in CLEAR):
            continue
        if is_fringe and on_track(x, y, 300):
            continue
        z = ground_h(x, y) - 25
        mat = GRASS_MATS[int(rng.r(0, len(GRASS_MATS) - 0.01))]
        if is_fringe:
            fringe += 1
            H = rng.r(250, 1300)
            blade(m, mat, (x, y, z), H, rng.r(70, 150), rng.r(0, TAU), H * rng.r(0.15, 0.45), nv=4)
        else:
            tall += 1
            depth = smooth(G_R0, 10500.0, r)
            H = (2200 + 6800 * depth) * rng.r(0.55, 1.2)
            Wd = rng.r(220, 420) + 260 * depth * rng.f()
            # the inner rows lean in over the arena like the big foreground blades in the reference
            inward = math.atan2(-y, -x)
            face = inward + rng.r(-0.9, 0.9) if r < 8500 and rng.f() < 0.6 else rng.r(0, TAU)
            blade(m, mat, (x, y, z), H, Wd, face, H * rng.r(0.12, 0.42), nv=12 if H > 4000 else 8,
                  twist=rng.r(-0.5, 0.5))
    return m


def tufts(seed, n=420):
    """Little grass sprouts and seedlings dotted over the dirt off the racing line."""
    m = Mesh()
    rng = Rng(seed)
    placed = 0
    while placed < n:
        r = math.sqrt(rng.r(300 ** 2, 7000 ** 2))
        a = rng.r(0, TAU)
        x, y = r * math.cos(a), r * math.sin(a)
        if on_track(x, y, 80):
            continue
        placed += 1
        z = ground_h(x, y) - 10
        for b in range(int(rng.r(5, 13))):
            H = rng.r(110, 520)
            blade(m, GRASS_MATS[int(rng.r(0, 4.99))], (x + rng.r(-50, 50), y + rng.r(-50, 50), z), H,
                  rng.r(26, 60), rng.r(0, TAU), H * rng.r(0.2, 0.6), fold=0.15, nv=4)
    return m


# ---------- stones, moss ----------

def pebble_scatter(seed, n=2600):
    m = Mesh()
    rng = Rng(seed)
    placed = 0
    while placed < n:
        mode = rng.f()
        th = rng.r(0, TAU)
        rc = edge_r(th)
        if mode < 0.55:                                   # both sides of the arena edge
            r = rc + rng.r(-60, 700) * (1 if rng.f() < 0.6 else -1)
        elif mode < 0.8:                                  # sprinkled over the arena floor
            r = rng.r(300, rc - 300)
        elif mode < 0.9:                                  # a few tiny strays anywhere
            r = rng.r(0, rc)
        else:
            r = rc + rng.r(700, 2200)
        x, y = r * math.cos(th), r * math.sin(th)
        s = rng.r(25, 130) if mode < 0.55 else (rng.r(20, 90) if mode < 0.8 else (rng.r(10, 30) if mode < 0.9 else rng.r(30, 110)))
        z = ground_h(x, y)
        placed += 1
        mat = "Stone" if rng.f() < 0.6 else ("StoneDark" if rng.f() < 0.6 else "StoneWarm")
        blob(m, mat, (x, y, z + s * 0.25), (s * rng.r(0.9, 1.4), s * rng.r(0.8, 1.2), s * rng.r(0.45, 0.75)), 10, 6, 0.12,
             seed + placed, flat_bottom=-s * 0.3)
    return m


def moss_patch(m, rng, x, y, R):
    z0 = ground_h(x, y) - 12
    ph = [rng.r(0, 6.28) for _ in range(4)]
    H = rng.r(30, 70)

    def fn(u, v):
        a = u * TAU
        e = R * (1 + 0.25 * math.sin(3 * a + ph[0]) + 0.15 * math.sin(7 * a + ph[1]))
        rr = e * v
        px, py = x + rr * math.cos(a), y + rr * math.sin(a)
        lump = H * (1 - v ** 3) * (0.7 + 0.6 * fbm(px / 90.0, py / 90.0, 11, 3))
        return (px, py, max(z0, ground_h(px, py) - 12) + lump)
    patch(m, "Moss", 28, 6, fn, lambda p: (0, 0, 1), wrap_u=True)


def moss_scatter(seed, spots):
    m = Mesh()
    rng = Rng(seed)
    for x, y, R in spots:
        moss_patch(m, rng, x, y, R)
    return m


def boulder(seed, R):
    m = Mesh()
    blob(m, "Stone", (0, 0, R * 0.42), (R * 1.15, R, R * 0.68), 32, 20, 0.14, seed, flat_bottom=-R * 0.45)
    return m


# ---------- wood ----------

def bark_r(R, a, x, ph):
    """Bark radius with long furrows running down the trunk."""
    f = abs(math.sin(a * 9 + 0.4 * math.sin(x * 0.0021 + ph))) ** 0.6
    return R * (1 - 0.055 * f + 0.02 * math.sin(a * 23 + x * 0.004 + ph))


def log_body(m, L, R0, R1, seed, cz, jag0=False, jag1=True, moss=True):
    """Log along X from -L/2..L/2, resting on the ground (centre at cz). Jagged broken ends show pale wood."""
    rng = Rng(seed)
    ph = rng.r(0, 6.28)
    jag = [rng.r(0, 1) for _ in range(40)]

    def endx(a, sgn, on):
        if not on:
            return 0.0
        k = (a / TAU) * 13
        i = int(k) % 13
        t = k - int(k)
        s = jag[i] * (1 - t) + jag[(i + 1) % 13] * t
        spike = max(0.0, math.sin(a * 13 + ph)) ** 4
        return sgn * (R0 * 0.35 * s + R0 * 0.55 * spike)

    def R(x):
        t = (x + L / 2) / L
        return R0 + (R1 - R0) * t

    def body(u, v):
        a = u * TAU
        x0 = -L / 2 + endx(a, -1, jag0) * -1
        x1 = L / 2 + endx(a, 1, jag1)
        x = x0 + (x1 - x0) * v
        sag = 0.0
        r = bark_r(R(x), a, x, ph)
        return (x, r * math.sin(a), cz + sag + r * math.cos(a))
    patch(m, "Bark", 72, 40, body, lambda p: (0, p[1], p[2] - cz), wrap_u=True)
    # end faces: splintered pale wood
    for sgn, on in ((-1, jag0), (1, jag1)):
        xe = -L / 2 if sgn < 0 else L / 2

        def cap(u, v, sgn=sgn, xe=xe, on=on):
            a = u * TAU
            ex = (-endx(a, -1, on) * -1) if sgn < 0 else endx(a, 1, on)
            r = bark_r(R(xe), a, xe, ph) * (1 - v) * 0.97
            dip = (-sgn) * (R0 * 0.25 * v * (0.5 + 0.5 * math.sin(a * 5 + ph))) if on else 0.0
            return (xe + ex * (1 - v) + dip, r * math.sin(a), cz + r * math.cos(a))
        patch(m, "WoodInner", 72, 6, cap, lambda p, sgn=sgn: (sgn, 0, 0), wrap_u=True)
    if moss:
        def mfn(u, v):
            x = -L / 2 * 0.9 + L * 0.9 * v
            span = 0.9 + 0.35 * math.sin(x * 0.0013 + ph) + 0.2 * math.sin(x * 0.0041)
            a = (u - 0.5) * span
            r = bark_r(R(x), a, x, ph) + 14 + 18 * fbm(x / 120.0, a * 4, 5, 2)
            return (x, r * math.sin(a), cz + r * math.cos(a))
        patch(m, "Moss", 18, 60, mfn, lambda p: (0, p[1], p[2] - cz))
    return R


def big_log(seed, L=10500.0, R0=780.0, R1=640.0):
    m = Mesh()
    rng = Rng(seed)
    cz = R0 * 0.78
    R = log_body(m, L, R0, R1, seed, cz, jag0=False, jag1=True)
    # snapped-off branch stubs and one long limb reaching up
    for k in range(3):
        x = rng.r(-L * 0.3, L * 0.35)
        a = rng.r(-1.2, 1.2)
        base = (x, R(x) * 0.8 * math.sin(a), cz + R(x) * 0.8 * math.cos(a))
        dirn = v_norm((rng.r(-0.3, 0.6), math.sin(a), math.cos(a) + 0.3))
        ln = rng.r(500, 1100) if k else 3400
        pts = [v_add(base, v_mul(dirn, ln * i / 6)) for i in range(7)]
        if k == 0:
            pts = catmull([base, v_add(base, v_mul(dirn, ln * 0.5)), v_add(base, v_add(v_mul(dirn, ln), (600, 0, -300)))], 4)
        rad = [R(x) * 0.3 * (1 - 0.6 * i / (len(pts) - 1)) for i in range(len(pts))]
        tube_along(m, "Bark", pts, rad, segs=14, cap=True)
    return m


def split_ramp(seed, L=4600.0, Wd=1700.0, rise=700.0):
    """Huge half-log lying split-face up, one end buried, the broken end propped up: a jump ramp."""
    m = Mesh()
    rng = Rng(seed)
    R = Wd / 2
    ph = rng.r(0, 6.28)

    def zbase(x):
        t = (x + L / 2) / L
        return -120 + rise * smooth(0.0, 1.0, t) ** 0.9

    def top(u, v):
        x = -L / 2 + L * v
        y = (u - 0.5) * 2 * R * 0.96
        grain = 7 * math.sin(y * 0.09 + 3 * math.sin(x * 0.002)) + 5 * fbm(x / 60.0, y / 25.0, 4, 2)
        crown = -0.05 * R * ((u - 0.5) * 2) ** 2
        return (x, y, zbase(x) + grain + crown)
    patch(m, "WoodInner", 24, 60, top, lambda p: (0, 0, 1))
    # bark shell below the split face
    def shell(u, v):
        x = -L / 2 + L * v
        a = math.pi * (u - 0.5)        # -90..90 deg around the underside
        r = bark_r(R, a, x, ph)
        return (x, r * math.sin(a) * 0.96, zbase(x) - r * math.cos(a) * 0.7)
    patch(m, "Bark", 40, 60, shell, lambda p: (0, p[1], -1))
    # splintered high end
    def endf(u, v):
        a = math.pi * (u - 0.5)
        r = bark_r(R, a, L / 2, ph) * (1 - v)
        jag = 140 * max(0.0, math.sin(u * 17 + ph)) ** 3 * (1 - v) + 60 * v
        return (L / 2 + jag, r * math.sin(a) * 0.96, zbase(L / 2) - r * math.cos(a) * 0.7 * (1 - v))
    patch(m, "WoodInner", 40, 4, endf, lambda p: (1, 0, 0))
    return m


def branch(seed, L=4200.0, R0=170.0):
    """Fallen dead branch lying on the ground with a couple of forks."""
    m = Mesh()
    rng = Rng(seed)
    ctrl = [(-L / 2, 0, R0 * 0.75), (-L / 6, rng.r(-300, 300), R0 * 0.7), (L / 6, rng.r(-300, 300), R0 * 0.6), (L / 2, rng.r(-200, 200), R0 * 0.45)]
    pts = catmull(ctrl, 8)
    rad = [R0 * (1 - 0.55 * i / (len(pts) - 1)) for i in range(len(pts))]
    tube_along(m, "Bark", pts, rad, segs=14, cap=True)
    for k in range(int(rng.r(2, 4.99))):
        i = int(rng.r(4, len(pts) - 6))
        b = pts[i]
        side = 1 if rng.f() < 0.5 else -1
        dirn = v_norm((rng.r(0.4, 1.0), side * rng.r(0.5, 1.0), rng.r(0.0, 0.5)))
        ln = rng.r(700, 1600)
        sub = catmull([b, v_add(b, v_mul(dirn, ln * 0.5)), v_add(v_add(b, v_mul(dirn, ln)), (0, 0, -ln * 0.15))], 4)
        tube_along(m, "Bark", sub, [rad[i] * 0.55 * (1 - 0.7 * j / (len(sub) - 1)) for j in range(len(sub))], segs=8, cap=True)
    return m


def tire(R=270.0, r=95.0, treads=28):
    m = Mesh()

    def fn(u, v):
        a = u * TAU
        b = v * TAU
        tread = 9 * max(0.0, math.cos(b)) ** 2 * (1 if math.sin(a * treads) > 0 else 0.2)
        rr = r + tread
        cr = R + rr * math.cos(b)
        return (cr * math.cos(a), cr * math.sin(a), r + rr * 0.85 * math.sin(b))
    patch(m, "Rubber", 140, 24, fn, lambda p: (p[0], p[1], 0) if math.hypot(p[0], p[1]) > R else (-p[0], -p[1], 0), wrap_u=True)
    lathe_z(m, "Hub", lambda v, a: (R * 0.75 * (1 - v) + 40, r * 0.9 + 25 * v), 48, 3, up=1)
    return m


# ---------- far background ----------

def house(W_=90000.0, D=50000.0, Hw=52000.0, Hr=30000.0):
    """Big blurry backyard house silhouette: siding walls, gable roof, windows, door."""
    m = Mesh()

    def box(mat, c, s, out=None):
        x0, y0, z0 = c[0] - s[0], c[1] - s[1], c[2] - s[2]
        x1, y1, z1 = c[0] + s[0], c[1] + s[1], c[2] + s[2]
        faces = [((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)),
                 ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (0, 1, 0)),
                 ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (-1, 0, 0)),
                 ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0)),
                 ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1))]
        for a, b, c_, d, n in faces:
            ia, ib, ic, id_ = (m.vert(p, (0, 0), n) for p in (a, b, c_, d))
            m.quad(mat, ia, ib, ic, id_)
    box("Siding", (0, 0, Hw / 2), (W_ / 2, D / 2, Hw / 2))
    # gable roof planes (ridge along X), overhanging
    ov = 2500
    for sg in (1, -1):
        def roof(u, v, sg=sg):
            x = -W_ / 2 - ov + (W_ + 2 * ov) * u
            y = sg * (D / 2 + ov) * (1 - v)
            z = Hw - ov * 0.5 + (Hr + ov * 0.5) * v
            return (x, y, z)
        patch(m, "Roof", 4, 4, roof, lambda p, sg=sg: (0, sg, 1))
    for sg in (1, -1):
        def gable(u, v, sg=sg):
            y = (u - 0.5) * D * (1 - v)
            return (sg * W_ / 2, y, Hw + Hr * v)
        patch(m, "Siding", 4, 4, gable, lambda p, sg=sg: (sg, 0, 0))
    # windows and door on the -Y (garden-facing) side
    for wx in (-30000, -12000, 12000, 30000):
        box("Trim", (wx, -D / 2 - 150, Hw * 0.6), (5200, 200, 6800))
        box("Window", (wx, -D / 2 - 360, Hw * 0.6), (4400, 60, 6000))
    box("Trim", (0, -D / 2 - 150, 11000), (5200, 200, 11000))
    box("Door", (0, -D / 2 - 360, 10400), (4400, 60, 10400))
    return m


def bg_tree(seed, H=70000.0, R=2600.0):
    m = Mesh()
    rng = Rng(seed)
    pts = catmull([(0, 0, -500), (rng.r(-1500, 1500), rng.r(-1500, 1500), H * 0.5), (rng.r(-2500, 2500), rng.r(-2500, 2500), H * 0.8)], 6)
    tube_along(m, "TreeBark", pts, [R * (1.3 - 0.6 * i / (len(pts) - 1)) for i in range(len(pts))], segs=20)
    top = pts[-1]
    for k in range(14):
        a = rng.r(0, TAU)
        d = rng.r(0, 16000)
        c = v_add(top, (d * math.cos(a), d * math.sin(a), rng.r(-9000, 9000)))
        s = rng.r(9000, 16000)
        blob(m, "Canopy", c, (s, s, s * 0.7), 24, 14, 0.18, seed * 13 + k)
    return m


# ---------- layout ----------

def tangent_yaw(th):
    """Yaw (deg) of the track direction (counter-clockwise travel) at polar angle th."""
    e = 1e-3
    p0 = (edge_r(th) * math.cos(th), edge_r(th) * math.sin(th))
    p1 = (edge_r(th + e) * math.cos(th + e), edge_r(th + e) * math.sin(th + e))
    return math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))


def polar(r, th):
    return r * math.cos(th), r * math.sin(th)


def layout():
    rng = Rng(2024)
    P = []
    moss = []

    def add(mesh, label, folder, x, y, yaw=0.0, s=1.0, dz=0.0, pitch=0.0, roll=0.0, sx=None):
        z = ground_h(x, y) + dz
        sc = sx or (s, s, s)
        P.append({"mesh": mesh, "label": label, "folder": folder, "loc": [round(x, 1), round(y, 1), round(z, 1)],
                  "rot": [round(pitch, 2), round(yaw, 2), round(roll, 2)], "scale": list(sc)})

    # player starts / bots evenly round the r 4300 ring; field props keep clear of them
    starts = []
    for i in range(13):
        th = TAU * i / 13 + 0.07
        x, y = polar(START_R, th)
        starts.append({"loc": [round(x, 1), round(y, 1), round(ground_h(x, y) + 90, 1)], "yaw": round(tangent_yaw(th), 2)})
    busy = [(s["loc"][0], s["loc"][1], 450) for s in starts]
    fr = Rng(77)

    # candidate spots spread over rings across the whole floor (centre, mid, outer between the starts), shuffled
    spots = []
    for rr, n, off in ((0, 1, 0.0), (1300, 5, 0.4), (2600, 9, 0.1), (3550, 13, 0.07 + TAU / 26), (5400, 13, 0.07 + TAU / 26)):
        for j in range(n):
            a = TAU * j / n + off
            spots.append((rr * math.cos(a) + fr.r(-150, 150), rr * math.sin(a) + fr.r(-150, 150)))
    for j in range(len(spots) - 1, 0, -1):
        q = int(fr.r(0, j + 0.999))
        spots[j], spots[q] = spots[q], spots[j]

    def field_spot(foot):
        for j, (x, y) in enumerate(spots):
            if all((x - bx) ** 2 + (y - by) ** 2 > (foot + br + 350) ** 2 for bx, by, br in busy):
                busy.append((x, y, foot))
                spots.pop(j)
                return x, y
        raise RuntimeError("no room for field prop")

    # soda can tunnel lying out in the field
    th = math.radians(105)
    x, y = polar(3000, th)
    for t in (-850, 0, 850):
        busy.append((x + t * math.cos(math.radians(tangent_yaw(th))), y + t * math.sin(math.radians(tangent_yaw(th))), 850))
    add("SM_G2_SodaCan", "SodaCan_Tunnel", "Garden2/Track", x, y, tangent_yaw(th), dz=-30)
    CLEAR.append((x, y, 0))
    # split-log jump ramp out in the field
    th = math.radians(-35)
    x, y = polar(3000, th)
    for t in (-1500, 0, 1500):
        busy.append((x + t * math.cos(math.radians(tangent_yaw(th))), y + t * math.sin(math.radians(tangent_yaw(th))), 900))
    add("SM_G2_SplitRamp", "LogRamp_Jump", "Garden2/Track", x, y, tangent_yaw(th), dz=-10)
    # big fallen logs framing the outside of the loop
    for i, (deg, dr, yo) in enumerate(((20, 1150, 8), (160, 1300, -10), (250, 1050, 14), (-80, 1350, -6))):
        th = math.radians(deg)
        r = edge_r(th) + dr
        x, y = polar(r, th)
        yaw = tangent_yaw(th) + yo
        add("SM_G2_BigLog", "FallenLog_%d" % i, "Garden2/Logs", x, y, yaw, s=rng.r(0.9, 1.1), dz=-20)
        for t in (-0.4, -0.2, 0.0, 0.2, 0.4):
            CLEAR.append((x + math.cos(math.radians(yaw)) * 10500 * t, y + math.sin(math.radians(yaw)) * 10500 * t, 1100))
        for t in (-0.35, -0.05, 0.3):
            px = x + math.cos(math.radians(yaw)) * 10000 * t
            py = y + math.sin(math.radians(yaw)) * 10000 * t
            nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
            for sd in (1, -1):
                moss.append((px + nx * sd * 950, py + ny * sd * 950, rng.r(300, 650)))
    # fallen branches edging both sides of the track
    k = 0
    for deg in range(0, 360, 24):
        th = math.radians(deg + rng.r(-6, 6))
        if 92 < deg < 120:
            continue
        r = edge_r(th) + rng.r(250, 450)
        x, y = polar(r, th)
        add("SM_G2_Branch_%s" % "ABC"[k % 3], "Branch_Out_%d" % k, "Garden2/Branches", x, y, tangent_yaw(th) + rng.r(-14, 14), s=rng.r(0.8, 1.15), dz=-25)
        k += 1
    for deg in range(10, 360, 34):
        rng.r(-8, 8), rng.r(350, 520), rng.r(-10, 10), rng.r(0.6, 0.8)   # no inner track edge any more; keep the stream
        k += 1
    # field: bottle caps, toy tyre, stones, a mushroom cluster and clover scattered over the whole arena floor
    caps = ["Red", "Blue", "Green", "Yellow", "White", "Red", "Blue", "Green", "Yellow", "Blue"]
    for i, c in enumerate(caps):
        x, y = field_spot(380)
        flip = i in (2, 7)
        tilt = rng.r(-9, 9) if not flip else 0
        add("SM_G2_Cap_" + c, "BottleCap_%s_%d" % (c, i), "Garden2/Field", x, y, rng.r(0, 360), s=rng.r(1.0, 1.35),
            dz=(150 if flip else -6), roll=(180 if flip else tilt))
    x, y = field_spot(500)
    add("SM_G2_Tire", "ToyTire", "Garden2/Field", x, y, 20, s=1.0, dz=-10, roll=8)
    for i, s in enumerate((0.8, 0.6, 0.55, 0.5, 0.7)):
        x, y = field_spot(520 * s)
        add("SM_G2_Boulder_%s" % "ABC"[i % 3], "IslandStone_%d" % i, "Garden2/Field", x, y, rng.r(0, 360), s=s, dz=-20)
    x, y = field_spot(800)
    add("SM_G2_MushCluster", "IslandMushrooms", "Garden2/Field", x, y, 40, s=0.75, dz=-20)
    x, y = field_spot(500)
    add("SM_G2_Clover", "IslandClover", "Garden2/Field", x, y, 0, s=0.55, dz=-20)
    x, y = field_spot(450)
    add("SM_G2_Clover", "IslandClover2", "Garden2/Field", x, y, 90, s=0.45, dz=-20)
    for bx, by, br in busy[len(starts):]:
        rng.r(0, TAU), rng.r(0, 1500)
        moss.append((bx + fr.r(-250, 250), by + fr.r(-250, 250), rng.r(200, 520)))
    # bottle caps and stones scattered at the track edges
    for i, (deg, c) in enumerate(((40, "Blue"), (55, "Red"), (140, "Green"), (200, "Yellow"), (215, "Red"), (300, "White"), (330, "Blue"))):
        th = math.radians(deg)
        r = edge_r(th) + rng.r(150, 500) * (1 if i % 2 == 0 else -1)
        x, y = polar(r, th)
        add("SM_G2_Cap_" + c, "EdgeCap_%d" % i, "Garden2/Edges", x, y, rng.r(0, 360), s=rng.r(1.0, 1.4), dz=-6, roll=rng.r(-6, 6))
    for i in range(34):
        th = rng.r(0, TAU)
        r = edge_r(th) + rng.r(250, 800) * (1 if rng.f() < 0.65 else -1)
        x, y = polar(r, th)
        add("SM_G2_Boulder_%s" % "ABC"[i % 3], "EdgeStone_%d" % i, "Garden2/Edges", x, y, rng.r(0, 360), s=rng.r(0.35, 1.1), dz=-30)
        moss.append((x + rng.r(-300, 300), y + rng.r(-300, 300), rng.r(250, 450)))
    # brown mushrooms at the edge of the grass
    for i, deg in enumerate((5, 48, 75, 130, 178, 228, 268, 310, 345)):
        th = math.radians(deg + rng.r(-5, 5))
        r = edge_r(th) + rng.r(2150, 2700)
        x, y = polar(r, th)
        big = i % 3 != 1
        add("SM_G2_Mushroom_A" if big else "SM_G2_MushCluster", "Mushroom_%d" % i, "Garden2/Mushrooms", x, y, rng.r(0, 360),
            s=rng.r(0.85, 1.3) if big else rng.r(0.9, 1.2), dz=-30)
        add("SM_G2_Mushroom_B", "MushroomSmall_%d" % i, "Garden2/Mushrooms", x + rng.r(-900, 900), y + rng.r(-900, 900), rng.r(0, 360), s=rng.r(0.6, 1.0), dz=-25)
        CLEAR.append((x, y, 800))
    # dandelion clocks and clover rising out of the grass jungle
    for i in range(18):
        th = TAU * i / 18 + rng.r(-0.12, 0.12)
        r = rng.r(7700, 12500)
        x, y = polar(r, th)
        add("SM_G2_Dandelion_%s" % "AB"[i % 2], "Dandelion_%d" % i, "Garden2/Flowers", x, y, rng.r(0, 360), s=rng.r(1.0, 1.55), dz=-20)
        CLEAR.append((x, y, 450))
    for i in range(20):
        th = TAU * (i + 0.5) / 20 + rng.r(-0.1, 0.1)
        r = rng.r(6700, 9500)
        x, y = polar(r, th)
        add("SM_G2_Clover", "Clover_%d" % i, "Garden2/Flowers", x, y, rng.r(0, 360), s=rng.r(0.9, 1.6), dz=-20)
        CLEAR.append((x, y, 700))
    # backdrop: fence ring (existing), house, giant trees
    P.append({"mesh": "/Game/BugBattle/Meshes/Garden/SM_BackyardFence", "label": "BackyardFence", "folder": "Garden2/Backdrop",
              "loc": [0, 0, 0], "rot": [0, 0, 0], "scale": [1, 1, 1.05]})   # same r 18000 footprint as Lvl_GardenArena
    P.append({"mesh": "SM_G2_House", "label": "House", "folder": "Garden2/Backdrop", "loc": [-30000, 190000, -2000],
              "rot": [0, -12, 0], "scale": [1, 1, 1]})
    for i in range(11):
        th = TAU * i / 11 + rng.r(-0.15, 0.15)
        if 1.35 < th < 2.0:
            continue
        r = rng.r(36000, 70000)
        x, y = polar(r, th)
        P.append({"mesh": "SM_G2_BgTree_%s" % "AB"[i % 2], "label": "BgTree_%d" % i, "folder": "Garden2/Backdrop",
                  "loc": [round(x), round(y), -1000], "rot": [0, rng.r(0, 360), 0], "scale": [rng.r(0.8, 1.2)] * 3})
    return P, moss, starts


def main():
    import sys
    only = set(sys.argv[1:])
    P, moss, starts = layout()
    jobs = {
        "SM_G2_Ground": ground,
        "SM_G2_SodaCan": soda_can,
        "SM_G2_Cap": bottle_cap,
        "SM_G2_Mushroom_A": lambda: mushroom_single(3, 2300.0, 1150.0),
        "SM_G2_Mushroom_B": lambda: mushroom_single(8, 1100.0, 560.0),
        "SM_G2_MushCluster": lambda: mushroom_cluster(5),
        "SM_G2_Dandelion_A": lambda: dandelion(7),
        "SM_G2_Dandelion_B": lambda: dandelion(19, 5200.0, 680.0),
        "SM_G2_Clover": lambda: clover_plant(4, 6),
        "SM_G2_BigLog": lambda: big_log(6),
        "SM_G2_SplitRamp": lambda: split_ramp(3),
        "SM_G2_Branch_A": lambda: branch(2),
        "SM_G2_Branch_B": lambda: branch(9, 3400.0, 140.0),
        "SM_G2_Branch_C": lambda: branch(17, 5000.0, 190.0),
        "SM_G2_Boulder_A": lambda: boulder(3, 420.0),
        "SM_G2_Boulder_B": lambda: boulder(11, 330.0),
        "SM_G2_Boulder_C": lambda: boulder(27, 520.0),
        "SM_G2_Tire": tire,
        "SM_G2_Tufts": lambda: tufts(13),
        "SM_G2_Pebbles": lambda: pebble_scatter(31),
        "SM_G2_Moss": lambda: moss_scatter(41, moss),
        "SM_G2_House": house,
        "SM_G2_BgTree_A": lambda: bg_tree(3),
        "SM_G2_BgTree_B": lambda: bg_tree(12, 82000.0, 3000.0),
    }
    for k in range(SECTORS):
        jobs["SM_G2_Grass_%02d" % k] = (lambda k=k: grass_sector(k, 101 + 37 * k))
    for name, fn in jobs.items():
        if only and name not in only:
            continue
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))
    # world-space scatter meshes are placed at the origin
    for name in ["SM_G2_Ground", "SM_G2_Tufts", "SM_G2_Pebbles", "SM_G2_Moss"] + ["SM_G2_Grass_%02d" % k for k in range(SECTORS)]:
        P.append({"mesh": name, "label": name[3:], "folder": "Garden2/Ground" if "Grass" not in name else "Garden2/Grass",
                  "loc": [0, 0, 0], "rot": [0, 0, 0], "scale": [1, 1, 1]})
    with open(os.path.join(os.path.dirname(__file__), "garden2_plan.json"), "w") as f:
        json.dump({"actors": P, "starts": starts}, f, indent=1)
    print("actors", len(P))


if __name__ == "__main__":
    main()
