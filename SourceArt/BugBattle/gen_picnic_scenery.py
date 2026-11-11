"""Picnic Arena backdrop: a giant couple enjoying their picnic, a ring of snow-capped mountains,
and a river that runs out of the north-east mountains, past the arena and into a lake.

All meshes are authored directly in world space of Lvl_PicnicArena (arena centre = origin,
ground top at z = -60), except the couple (real-life cm, scaled by COUPLE_SCALE) and the
mountains (local space, placed by MOUNTAINS below). Run: python gen_picnic_scenery.py
"""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_sub, v_mul, v_norm, v_len

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)

COUPLE_SCALE = 240.0     # fork is ~48 m in-game vs ~20 cm in life
GROUND_Z = -60.0

# ---------------------------------------------------------------- helpers

def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def mat_apply(R, p):
    return tuple(R[i][0] * p[0] + R[i][1] * p[1] + R[i][2] * p[2] for i in range(3))


def ell(m, mat, c, r, R=None, nu=32, nv=20):
    """Ellipsoid with optional rotation matrix R (applied about its centre)."""
    if R is None:
        return ellipsoid(m, mat, c, r, nu, nv)
    return ellipsoid(m, mat, (0, 0, 0), r, nu, nv, deform=lambda p, d: v_add(c, mat_apply(R, p)))


def limb(m, mat, pts, r0, r1, segs=16, samples=5):
    """Smooth tapered tube through control points."""
    path = catmull(pts, samples) if len(pts) > 2 else pts
    if len(path) == 2:
        path = [v_add(path[0], v_mul(v_sub(path[1], path[0]), k / 6.0)) for k in range(7)]
    n = len(path)
    tube_along(m, mat, path, [r0 + (r1 - r0) * i / (n - 1) for i in range(n)], segs)


def head(m, c, r, R, skin, hair_parts, eye_y, nose_r, lips=True):
    """Head centred at c with rotation R; feature offsets are in head-local space."""
    def at(o):
        return v_add(c, mat_apply(R, o))
    ell(m, skin, c, r, R, 36, 24)
    for (o, hr, mat) in hair_parts:
        ell(m, mat, at(o), hr, R, 36, 24)
    fx = r[0]
    for sy in (-1, 1):
        y = sy * eye_y
        x = fx * math.sqrt(max(0.0, 1 - (y / r[1]) ** 2 - (0.17) ** 2))
        ell(m, "EyeDark", at((x - 0.25, y, r[2] * 0.17)), (1.15, 1.15, 1.3), R, 12, 8)
        ell(m, skin, at((x - 1.2, y, r[2] * 0.30)), (2.0, 2.2, 0.8), R, 12, 8)      # brow ridge
        ell(m, skin, at((0.0, sy * (r[1] - 0.2), r[2] * -0.02)), (2.0, 1.2, 3.0), R, 12, 8)  # ears
    ell(m, skin, at((fx + 0.15, 0, -0.05 * r[2])), nose_r, R, 12, 8)
    if lips:
        x = fx * math.sqrt(max(0.0, 1 - 0.33 ** 2))
        ell(m, "Lips", at((x - 0.35, 0, -0.33 * r[2])), (0.8, 2.3, 0.65), R, 12, 8)


def torso(m, prof, mat_fn, na=40, sub=3):
    """Smooth closed body: prof = [(z, rx, ry, cx, cy)] bottom to top (end rows have ~0 radius).
    mat_fn(z) picks the material per band."""
    rows = []
    zs = []
    for k in range(len(prof) - 1):
        for s in range(sub):
            t = s / sub
            t = t * t * (3 - 2 * t)
            zs.append(tuple(prof[k][i] * (1 - t) + prof[k + 1][i] * t for i in range(5)))
    zs.append(prof[-1])
    for (z, rx, ry, cx, cy) in zs:
        row = []
        for i in range(na):
            a = 2 * math.pi * i / na
            row.append(m.vert((cx + rx * math.cos(a), cy + ry * math.sin(a), z), (i / na, z / 100.0)))
        rows.append((z, row))
    for j in range(len(rows) - 1):
        z0, r0 = rows[j]
        z1, r1 = rows[j + 1]
        mat = mat_fn(0.5 * (z0 + z1))
        for i in range(na):
            i2 = (i + 1) % na
            m.quad(mat, r0[i], r0[i2], r1[i2], r1[i])


def scaled(m, s):
    out = Mesh()
    out.append(m, lambda p, n: (v_mul(p, s), n))
    return out

# ---------------------------------------------------------------- the couple
# Local frame: they face +X, ground at z = 0, the man at y = 0 and the woman at y = +46 (his right).


def couple():
    m = Mesh()
    # ---- him: cross-legged, left hand on his knee, right arm around her
    torso(m, [(1, 0.5, 0.5, 0, 0), (4, 13, 15.5, 0, 0), (12, 15.5, 18, 0, 0), (21, 14, 17, 0.5, 0),
              (32, 13.2, 16.5, 0.5, 0), (44, 12.5, 18.5, 0, 0), (54, 11.5, 19.5, -1, 0), (60, 9.5, 17.5, -1.5, 0),
              (64, 5.5, 9, -1.5, 0), (65.5, 0.5, 0.5, -1.5, 0)],
          lambda z: "Denim" if z < 19 else "ShirtBlue")
    ell(m, "Denim", (2, 0, 19.5), (13.6, 16.4, 1.6), None, 32, 6)                     # belt line
    for sy in (-1, 1):
        ell(m, "ShirtBlue", (-1, sy * 17, 59), (7.5, 7.5, 6.5))
    ell(m, "ShirtBlue", (2.5, 0, 60), (6, 9, 3))                          # collar
    limb(m, "SkinTan", [(-1.5, 0, 60), (-0.5, 0, 74)], 5.6, 5.2)
    head(m, (0, 0, 84), (10.5, 9.0, 12.0), rot_x(0.0), "SkinTan",
         [((-2.2, 0, 3.2), (10.6, 9.6, 10.0), "HairBrown")], 3.4, (2.0, 1.6, 2.7))
    # thighs out to the knees, shins crossed in front, shoes
    for sy in (-1, 1):
        limb(m, "Denim", [(3, sy * 9, 9), (17, sy * 21, 9.5), (30, sy * 31, 9)], 8.5, 6.2)
    limb(m, "Denim", [(30, -31, 8), (25, -10, 7), (17, 9, 6)], 5.8, 4.0)
    limb(m, "Denim", [(30, 31, 9), (26, 10, 13), (20, -9, 11)], 5.8, 4.0)
    ell(m, "ShoeBrown", (17, 15, 5), (4.6, 8.0, 4.0))
    ell(m, "ShoeBrown", (20, -15, 10), (4.6, 8.0, 4.0))
    # left arm: short sleeve, hand resting on his knee
    limb(m, "ShirtBlue", [(-1, -20, 60), (1, -23, 52), (3, -25, 45)], 5.8, 5.0)
    limb(m, "SkinTan", [(3, -25, 46), (12, -26, 31), (25, -27, 20)], 4.2, 3.4)
    ell(m, "SkinTan", (28.5, -28, 17.5), (5.0, 3.4, 2.3))
    # right arm: around her back, hand on her far waist
    limb(m, "ShirtBlue", [(-1, 20, 60), (-5, 25, 57), (-9, 29, 54)], 5.8, 5.0)
    limb(m, "SkinTan", [(-9, 29, 54), (-15, 40, 48), (-12, 53, 45), (-5, 60, 44)], 4.2, 3.4)
    ell(m, "SkinTan", (-1.5, 61.5, 44), (4.2, 2.6, 3.2))

    # ---- her: knees up, head on his shoulder, glass of red wine in her outer hand
    W = 46
    torso(m, [(1, 0.5, 0.5, 0, W), (4, 12.5, 14.5, 0, W), (12, 14.5, 16.5, 0, W), (20, 11.5, 13.8, -0.5, W - 0.5),
              (28, 9.6, 12.2, -1, W - 1), (37, 10.2, 13.6, -0.5, W - 1.5), (46, 10.6, 15, 0, W - 2),
              (53, 9.2, 14.2, -0.5, W - 2.5), (57.5, 6, 9.5, -1, W - 3), (59, 0.5, 0.5, -1, W - 3)],
          lambda z: "DressSun" if z < 51 else "SkinLight")
    for sy in (-1, 1):
        ell(m, "SkinLight", (-1, W - 2 + sy * 13.5, 54), (5.5, 5.5, 5))
    limb(m, "SkinLight", [(-1, W - 4, 56), (0.2, 37, 64), (0.8, 34, 68)], 4.4, 4.0)
    R = rot_x(math.radians(-24))                                              # tilt toward him
    head(m, (1.5, 31, 75.5), (9.5, 8.3, 11.0), R, "SkinLight",
         [((-3.0, 0.4, 3.2), (10.4, 9.2, 10.3), "HairAuburn"),
          ((-6.5, 1.0, -7.0), (6.2, 10.0, 14.0), "HairAuburn")], 3.2, (1.6, 1.2, 2.0))
    # long hair falling down her back
    limb(m, "HairAuburn", [(-7, 37, 70), (-9, 42, 60), (-10, 45, 50)], 8.0, 6.0)
    # legs: skirt over the thighs, bare shins, sandals
    for sy in (-1, 1):
        limb(m, "DressSun", [(4, W + sy * 6, 10), (18, W + sy * 6, 22), (32, W + sy * 5.5, 34)], 9.5, 7.2)
        limb(m, "SkinLight", [(33, W + sy * 5.5, 33), (39, W + sy * 5.3, 19), (44, W + sy * 5, 5)], 4.8, 3.1)
        ell(m, "Sandal", (49, W + sy * 5, 2.8), (7.0, 3.6, 2.6))
    # inner arm: hand resting on her knees
    limb(m, "SkinLight", [(-1, W - 14, 55), (3, W - 15, 47), (6, W - 14, 40)], 4.6, 4.0)
    limb(m, "SkinLight", [(6, W - 14, 40), (18, W - 9, 40), (30, W - 2, 41)], 3.7, 3.0)
    ell(m, "SkinLight", (33, W, 42.5), (4.2, 3.0, 2.3))
    # outer arm: raising a glass
    limb(m, "SkinLight", [(-1, W + 14, 55), (1, W + 18, 47), (4, W + 20, 40)], 4.6, 4.0)
    limb(m, "SkinLight", [(4, W + 20, 40), (14, W + 18, 46), (20, W + 14, 51)], 3.7, 3.0)
    ell(m, "SkinLight", (22, W + 12.5, 52.5), (3.6, 2.6, 4.0))
    wine_glass(m, (23.5, W + 11, 47))

    # ---- picnic things in front of them
    wine_bottle(m, (54, 18, 0))
    wine_glass(m, (50, -8, 0))
    return scaled(m, COUPLE_SCALE)


def wine_glass(m, base):
    bx, by, bz = base
    ell(m, "GlassClear", (bx, by, bz + 0.3), (3.4, 3.4, 0.45), None, 20, 6)
    limb(m, "GlassClear", [(bx, by, bz), (bx, by, bz + 10)], 0.65, 0.65, 10)
    ell(m, "GlassClear", (bx, by, bz + 15.2), (4.1, 4.1, 5.4), None, 24, 14)
    ell(m, "RedWine", (bx, by, bz + 13.6), (3.55, 3.55, 3.3), None, 24, 12)


def wine_bottle(m, base):
    bx, by, bz = base
    prof = [(0, 0.0), (0, 3.9), (1.0, 4.2), (20, 4.2), (23, 3.6), (26, 2.0), (28, 1.5), (33, 1.5)]
    pts = [(bx, by, bz + h) for h, _ in prof]
    tube_along(m, "BottleGreen", pts, [max(r, 0.3) for _, r in prof], 24)
    limb(m, "BottleLabel", [(bx, by, bz + 8), (bx, by, bz + 17)], 4.32, 4.32, 24)
    limb(m, "Cork", [(bx, by, bz + 32.5), (bx, by, bz + 35)], 1.45, 1.45, 12)

# ---------------------------------------------------------------- mountains


def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy


def ridged(x, y, seed, octaves=5):
    s, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        n = 1.0 - abs(2.0 * vnoise(x, y, seed + o * 17) - 1.0)
        s += n * n * amp
        tot += amp
        x, y, amp = x * 2.03, y * 2.03, amp * 0.5
    return s / tot


def mountain(seed, R, peaks, nr=56, na=160):
    """peaks: list of (x, y, height, radius) in local cm. Polar grid out to R with a wobbly rim
    that sinks below the meadow; materials: grass foothills, rock, snow caps."""
    m = Mesh()
    rng = Rng(seed)
    wob = [rng.r(0, 6.283) for _ in range(4)]
    Hmax = max(p[2] for p in peaks)

    def height(x, y):
        h = 0.0
        for (px, py, ph, pr) in peaks:
            d = math.hypot(x - px, y - py) / pr
            if d < 1:
                h = max(h, ph * (1 - d) ** 1.35)
        n = ridged(x / 14000.0, y / 14000.0, seed)
        return h * (0.55 + 0.75 * n)

    rows = []
    for j in range(nr + 1):
        s = (j / nr) ** 0.85
        row = []
        for i in range(na):
            a = 2 * math.pi * i / na
            rr = R * s * (1 + 0.12 * math.sin(3 * a + wob[0]) + 0.07 * math.sin(5 * a + wob[1]))
            x, y = rr * math.cos(a), rr * math.sin(a)
            z = height(x, y)
            edge = max(0.0, (s - 0.86) / 0.14)
            z = z * (1 - edge) + (-700.0) * edge
            row.append(m.vert((x, y, z), (x / 4000.0, y / 4000.0)))
        rows.append(row)
    for j in range(nr):
        for i in range(na):
            i2 = (i + 1) % na
            a, b, c, d = rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]
            for (p, q, r_) in ((a, d, c), (a, c, b)):
                P, Q, Rr = m.p[p], m.p[q], m.p[r_]
                zc = (P[2] + Q[2] + Rr[2]) / 3.0
                nrm = v_norm(_cross(v_sub(Q, P), v_sub(Rr, P)))
                f = zc / Hmax + 0.08 * (vnoise(P[0] / 5000.0, P[1] / 5000.0, seed + 99) - 0.5)
                if f > 0.5 and nrm[2] > 0.3:
                    mat = "Snow"
                elif f > 0.3 or nrm[2] < 0.7:
                    mat = "MountainRock"
                else:
                    mat = "MountainGrass"
                m.tri(mat, p, q, r_)
    return m


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


MOUNTAIN_VARIANTS = {
    "SM_Mountain_A": (11, 40000.0, [(0, 0, 48000.0, 40000.0)]),
    "SM_Mountain_B": (23, 42000.0, [(-9000, -5000, 42000.0, 34000.0), (12000, 8000, 33000.0, 30000.0)]),
    "SM_Mountain_C": (37, 44000.0, [(-16000, 0, 30000.0, 30000.0), (2000, 6000, 34000.0, 30000.0),
                                     (18000, -4000, 26000.0, 28000.0)]),
}

# world placements: (label, mesh, x, y, yaw, scale)
MOUNTAINS = [
    ("Mountain_RiverSource", "SM_Mountain_A", 55000, 140000, 20, 1.15),
    ("Mountain_North", "SM_Mountain_B", -20000, 138000, 70, 1.35),
    ("Mountain_NorthWest", "SM_Mountain_C", -85000, 112000, 10, 1.15),
    ("Mountain_West", "SM_Mountain_A", -130000, 40000, 130, 1.25),
    ("Mountain_SouthWest", "SM_Mountain_B", -128000, -48000, 200, 1.0),
    ("Mountain_South", "SM_Mountain_C", -78000, -125000, 250, 1.2),
    ("Mountain_SouthFar", "SM_Mountain_A", 8000, -140000, 300, 0.95),
    ("Mountain_SouthEast", "SM_Mountain_B", 125000, -125000, 40, 1.15),
    ("Mountain_East", "SM_Mountain_C", 138000, -25000, 100, 1.3),
    ("Mountain_NorthEast", "SM_Mountain_A", 125000, 72000, 160, 1.05),
]

# ---------------------------------------------------------------- river + lake (world space)

RIVER_PTS = [(52000, 128000), (48000, 95000), (31000, 64000), (37000, 31000), (42000, 0),
             (36000, -30000), (47000, -57000), (62000, -76000)]
LAKE_C, LAKE_R = (70000, -88000), 17000.0
Z_SRC, Z_END = 260.0, -15.0          # the river falls gently toward the lake
LAKE_Z = -25.0


def river_path():
    pts = catmull([(x, y, 0.0) for x, y in RIVER_PTS], 18)
    out, dist = [], 0.0
    for i, p in enumerate(pts):
        if i:
            dist += v_len(v_sub(p, pts[i - 1]))
        out.append([p, dist])
    L = dist
    res = []
    for i, (p, d) in enumerate(out):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = v_norm(v_sub(b, a))
        side = (-t[1], t[0], 0.0)                       # left of the flow
        k = d / L
        half = 4300 + 900 * math.sin(k * 9.0) + 600 * math.sin(k * 23.0 + 1.0)
        z = Z_SRC + (Z_END - Z_SRC) * k
        res.append((p, side, half, z, d))
    return res


def river():
    m = Mesh()
    path = river_path()
    nx = 8
    rows = []
    for (p, side, half, z, d) in path:
        row = []
        for i in range(nx + 1):
            u = -1 + 2 * i / nx
            pos = v_add(p, v_mul(side, u * half))
            row.append(m.vert((pos[0], pos[1], z), (u * half / 1000.0, d / 1000.0), (0, 0, 1)))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(nx):
            a, b, c, d = rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]
            m.quad("Water", a, b, c, d)
    return m


BANK = [(-900, -220, "RiverMud"), (0, 30, "RiverMud"), (700, 260, "RiverMud"), (1500, 420, "BankGrass"),
        (2800, 300, "BankGrass"), (4200, -90, "BankGrass")]


def _bank_strip(m, frames, sign):
    """frames: list of (p, outward, z_water, uvoff); profile BANK is offset from the water edge."""
    rows = []
    for (p, out, zw) in frames:
        row = []
        for (d, z, _) in BANK:
            pos = v_add(p, v_mul(out, d))
            zz = zw + z if d < 2000 else z           # near profile follows the water, outer part meets the meadow
            row.append(m.vert((pos[0], pos[1], zz), (pos[0] / 2500.0, pos[1] / 2500.0)))
        rows.append(row)
    for j in range(len(rows) - 1):
        for k in range(len(BANK) - 1):
            a, b, c, d = rows[j][k], rows[j][k + 1], rows[j + 1][k + 1], rows[j + 1][k]
            mat = BANK[k][2]
            if sign > 0:
                m.quad(mat, a, d, c, b)
            else:
                m.quad(mat, a, b, c, d)


def rock(m, c, size, rng):
    sx, sy, sz = size * rng.r(0.8, 1.3), size * rng.r(0.7, 1.1), size * rng.r(0.45, 0.75)
    seed = int(rng.r(0, 9999))

    def deform(p, d):
        k = 0.78 + 0.4 * vnoise(d[0] * 2.2 + 5, d[1] * 2.2 + d[2] * 1.7, seed)
        return v_mul(p, k)
    yaw = rng.r(0, 6.283)
    cy, syw = math.cos(yaw), math.sin(yaw)
    ellipsoid(m, "Stone", (0, 0, 0), (sx, sy, sz), 18, 12,
              deform=lambda p, d: v_add(c, (lambda q: (q[0] * cy - q[1] * syw, q[0] * syw + q[1] * cy, q[2]))(deform(p, d))))


def river_banks():
    m = Mesh()
    path = river_path()
    for sign in (1, -1):
        frames = []
        for (p, side, half, z, d) in path:
            if math.hypot(p[0] - LAKE_C[0], p[1] - LAKE_C[1]) < LAKE_R - 1500:
                continue
            out = v_mul(side, sign)
            frames.append((v_add(p, v_mul(out, half)), out, z))
        _bank_strip(m, frames, sign)
    # lake shore, open where the river comes in
    entry = math.atan2(RIVER_PTS[-2][1] - LAKE_C[1], RIVER_PTS[-2][0] - LAKE_C[0])
    frames = []
    na = 96
    for i in range(na + 1):
        a = entry + 0.32 + (2 * math.pi - 0.64) * i / na
        rr = LAKE_R * (1 + 0.08 * math.sin(3 * a) + 0.05 * math.sin(7 * a + 1))
        out = (math.cos(a), math.sin(a), 0.0)
        frames.append(((LAKE_C[0] + rr * out[0], LAKE_C[1] + rr * out[1], 0.0), out, LAKE_Z))
    _bank_strip(m, frames, -1)
    # boulders along the water's edge
    rng = Rng(5)
    for (p, side, half, z, d) in path[::3]:
        if math.hypot(p[0] - LAKE_C[0], p[1] - LAKE_C[1]) < LAKE_R:
            continue
        for sign in (1, -1):
            if rng.f() < 0.55:
                off = half + rng.r(-300, 900)
                c = v_add(p, v_mul(side, sign * off))
                rock(m, (c[0], c[1], z + rng.r(-80, 120)), rng.r(500, 1300), rng)
    for i in range(14):
        a = entry + 0.5 + rng.r(0, 2 * math.pi - 1.0)
        rr = LAKE_R * rng.r(0.95, 1.08)
        rock(m, (LAKE_C[0] + rr * math.cos(a), LAKE_C[1] + rr * math.sin(a), LAKE_Z + rng.r(-50, 150)),
             rng.r(600, 1500), rng)
    return m


def lake():
    m = Mesh()
    na, nr = 96, 6
    c = m.vert((LAKE_C[0], LAKE_C[1], LAKE_Z), (LAKE_C[0] / 1000.0, LAKE_C[1] / 1000.0), (0, 0, 1))
    rows = []
    for j in range(1, nr + 1):
        row = []
        for i in range(na):
            a = 2 * math.pi * i / na
            rr = (LAKE_R + 1200) * (j / nr) * (1 + 0.08 * math.sin(3 * a) + 0.05 * math.sin(7 * a + 1))
            x, y = LAKE_C[0] + rr * math.cos(a), LAKE_C[1] + rr * math.sin(a)
            row.append(m.vert((x, y, LAKE_Z), (x / 1000.0, y / 1000.0), (0, 0, 1)))
        rows.append(row)
    for i in range(na):
        m.tri("Water", c, rows[0][(i + 1) % na], rows[0][i])
    for j in range(nr - 1):
        for i in range(na):
            i2 = (i + 1) % na
            m.quad("Water", rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i])
    return m


def river_clearance(x, y):
    """Distance from (x, y) to the river centreline minus its half width (for clearing props)."""
    best = 1e18
    for (p, side, half, z, d) in river_path():
        best = min(best, math.hypot(x - p[0], y - p[1]) - half)
    return best


def main():
    import sys
    jobs = {"SM_PicnicCouple": couple, "SM_River": river, "SM_RiverBanks": river_banks, "SM_Lake": lake}
    for name, (seed, R, peaks) in MOUNTAIN_VARIANTS.items():
        jobs[name] = (lambda seed=seed, R=R, peaks=peaks: mountain(seed, R, peaks))
    only = sys.argv[1:]
    for name, fn in jobs.items():
        if only and name not in only:
            continue
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


if __name__ == "__main__":
    main()
