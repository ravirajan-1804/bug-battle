"""Generates the Hive Arena meshes (bee-scale honeycomb colosseum)."""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_sub, v_mul, v_norm, v_cross

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)

R_IN = 6000.0            # inner face radius of the hive wall
COLS_TOTAL = 192
PANELS = 24
COLS = COLS_TOTAL // PANELS
W = 2 * math.pi * R_IN / COLS_TOTAL      # across-flats width of one cell
RH = W / math.sqrt(3.0)                  # hex circumradius
ROW_H = 1.5 * RH
ROWS = 13
RIM = 9.0                                # half wall thickness between cells
RI = RH - RIM / math.cos(math.radians(30))
BACK = 170.0                             # wall depth


def cyl(u, v, d):
    """Panel-local (u along the wall, v up, d into the wall) -> world."""
    phi = u / R_IN
    rho = R_IN + d
    return (rho * math.cos(phi), rho * math.sin(phi), v)


def hex_pts(cx, cv, r):
    return [(cx + r * math.cos(math.radians(30 + 60 * k)), cv + r * math.sin(math.radians(30 + 60 * k)))
            for k in range(6)]


def cell_exists(c, r):
    c %= COLS
    if r < ROWS:
        return r >= 0
    if r == ROWS:
        return ((c * 7 + 3) % 5) in (0, 2)
    if r == ROWS + 1:
        return ((c * 7 + 3) % 5) == 0 and c % 2 == 0
    return False


def neighbour(c, r, k):
    """Neighbour across edge k (edge between vertex k and k+1, vertices at 30+60k deg)."""
    odd = r % 2 == 1
    if k == 5:   # right edge (330..30)
        return c + 1, r
    if k == 2:   # left edge (150..210)
        return c - 1, r
    up = k in (0, 1)
    rr = r + 1 if up else r - 1
    right = k in (0, 4)
    if odd:
        return (c + 1 if right else c), rr
    return (c if right else c - 1), rr


def hive_panel(seed):
    m = Mesh()
    rng = Rng(seed)

    def V(u, v, d, uvs=None):
        return m.vert(cyl(u, v, d), uvs if uvs else (u / 220.0, v / 220.0))

    for r in range(-1, ROWS + 2):
        for c in range(COLS):
            if not cell_exists(c, r):
                continue
            cu = c * W + (W * 0.5 if r % 2 else 0.0) + W * 0.5
            cv = r * ROW_H + RH * 0.3
            outer = hex_pts(cu, cv, RH)
            inner = hex_pts(cu, cv, RI)
            roll = rng.f()
            if r >= ROWS - 1 and roll < 0.55:
                kind = "cap"
            elif roll < 0.40:
                kind = "honey"
            elif roll < 0.48:
                kind = "over"
            elif roll < 0.80:
                kind = "cap"
            else:
                kind = "empty"
            if cv < 0:
                kind = "cap"
            lip = 5.0
            # front rim (bevelled lip)
            o_ids = [V(p[0], p[1], 0.0) for p in outer]
            i_ids = [V(p[0], p[1], lip) for p in inner]
            for k in range(6):
                k2 = (k + 1) % 6
                m.quad("Wax", o_ids[k], i_ids[k], i_ids[k2], o_ids[k2])
            # depth of contents
            if kind == "honey":
                depth = rng.r(20.0, 55.0)
            elif kind == "over":
                depth = 8.0
            elif kind == "cap":
                depth = rng.r(6.0, 14.0)
            else:
                depth = rng.r(110.0, 150.0)
            # inner walls
            w_top = [V(p[0], p[1], lip, ((k / 6.0), 0)) for k, p in enumerate(inner)]
            w_bot = [V(p[0], p[1], depth, ((k / 6.0), 1)) for k, p in enumerate(inner)]
            wall_mat = "WaxDark" if kind == "empty" else "Wax"
            for k in range(6):
                k2 = (k + 1) % 6
                m.quad(wall_mat, w_top[k], w_bot[k], w_bot[k2], w_top[k2])
            # contents surface (fan with a mid ring)
            if kind == "empty":
                ctr = V(cu, cv, depth + 10.0)
                ring = [V(p[0], p[1], depth) for p in inner]
                for k in range(6):
                    m.tri("WaxDark", ctr, ring[(k + 1) % 6], ring[k])
            else:
                mat = "Honey" if kind in ("honey", "over") else "Cap"
                if kind == "honey":
                    d_edge, d_mid, d_ctr = depth - 7.0, depth - 1.5, depth   # concave meniscus
                elif kind == "over":
                    d_edge, d_mid, d_ctr = depth - 2.0, -4.0, -9.0           # bulging out of the cell
                else:
                    d_edge, d_mid, d_ctr = depth, depth - 3.0, depth - 4.5   # slightly domed wax cap
                ring = [V(p[0], p[1], d_edge, (0.5 + 0.5 * math.cos(math.radians(30 + 60 * k)),
                                               0.5 + 0.5 * math.sin(math.radians(30 + 60 * k))))
                        for k, p in enumerate(inner)]
                mid = [V(cu + (p[0] - cu) * 0.6, cv + (p[1] - cv) * 0.6, d_mid) for p in inner]
                ctr = V(cu, cv, d_ctr, (0.5, 0.5))
                for k in range(6):
                    k2 = (k + 1) % 6
                    m.quad(mat, ring[k], mid[k], mid[k2], ring[k2])
                    m.tri(mat, mid[k], ctr, mid[k2])
                if kind == "over" and rng.f() < 0.75 and r > 0:
                    # honey drip running down the comb face from the bottom vertex
                    length = rng.r(70.0, 260.0)
                    bottom_v = cv - RI * 0.9
                    pts = []
                    n = 9
                    for i in range(n):
                        s = i / (n - 1)
                        pts.append((cu + 4.0 * math.sin(s * 3.0 + c), bottom_v - length * s, 0.0))
                    radii = [10.0 * (1.0 - 0.55 * s) for s in [i / (n - 1) for i in range(n)]]
                    radii[-1] = 9.0
                    radii[-2] = 8.5
                    world = [cyl(p[0], p[1], -4.0) for p in pts]
                    tube_along(m, "Honey", world, radii, segs=10)
            # outer side walls where a neighbour is missing
            for k in range(6):
                nc, nr = neighbour(c, r, k)
                if not cell_exists(nc, nr):
                    k2 = (k + 1) % 6
                    a, b = outer[k], outer[k2]
                    ids = [V(a[0], a[1], 0.0), V(b[0], b[1], 0.0), V(b[0], b[1], BACK), V(a[0], a[1], BACK)]
                    m.quad("Wax", ids[0], ids[1], ids[2], ids[3])
    # back plate
    top = (ROWS + 1) * ROW_H + RH
    segs = 16
    u1 = COLS * W
    def back(u, v):
        return cyl(u * u1 - W * 0.02, -200.0 + v * (top + 200.0), BACK)
    m.grid("Wax", segs, 6, back, uv_fn=lambda u, v: (u * 8, v * 8))
    # wax fillet where the wall meets the arena floor
    def fillet(u, v):
        a = v * math.pi * 0.5
        rad = 70.0
        d = -rad + rad * math.sin(a)
        z = rad - rad * math.cos(a)
        return cyl(u * u1, z - 1.0, d)
    m.grid("Wax", segs * 2, 6, fillet, uv_fn=lambda u, v: (u * 20, v), flip=True)
    return m


def arena_floor():
    m = Mesh()
    R = 6080.0
    segs = 256

    def top(u, v):
        a = u * 2 * math.pi
        rr = R * v
        return (rr * math.cos(a), rr * math.sin(a), 0.0)
    m.grid("Floor", segs, 24, top, uv_fn=lambda u, v: (0.5 + 0.5 * v * math.cos(u * 6.283), 0.5 + 0.5 * v * math.sin(u * 6.283)),
           wrap_u=True, flip=True)

    def side(u, v):
        a = u * 2 * math.pi
        return (R * math.cos(a), R * math.sin(a), -300.0 * v)
    m.grid("Floor", segs, 1, side, wrap_u=True, flip=True)
    return m


def hex_dais():
    m = Mesh()
    Rt, Rb, H, bev = 1000.0, 1060.0, 160.0, 14.0
    ang = [math.radians(60 * k) for k in range(6)]   # flat sides face 30, 90, ...

    def ring(r, z):
        return [(r * math.cos(a), r * math.sin(a), z) for a in ang]
    levels = [(Rb, 0.0), (Rb - (Rb - Rt) * 0.95, H - bev), (Rt - bev * 0.4, H - bev * 0.25), (Rt - bev, H)]
    rings = []
    for r, z in levels:
        rings.append([m.vert(p, (p[0] / 400.0, p[2] / 400.0)) for p in ring(r, z)])
    for j in range(len(rings) - 1):
        for k in range(6):
            k2 = (k + 1) % 6
            m.quad("Wax", rings[j][k], rings[j][k2], rings[j + 1][k2], rings[j + 1][k])
    # top face uses the hex-cap floor material
    toprim = [m.vert(p, (0, 0)) for p in ring(Rt - bev, H)]
    ctr = m.vert((0, 0, H), (0.5, 0.5))
    for k in range(6):
        m.tri("Floor", ctr, toprim[k], toprim[(k + 1) % 6])
    return m


def leaf(length, width, rise, kicker=False, seed=1):
    """Leaf ramp lying along +X: tip at x=0 on the floor, stem end at x=length raised by `rise`."""
    m = Mesh()

    def half_w(s):
        return width * 0.5 * (math.sin(math.pi * min(s * 1.08, 1.0)) ** 0.8) * (0.35 + 0.65 * s ** 0.35)

    def height(s):
        if kicker:
            return rise * (s ** 1.7)
        return rise * (0.5 - 0.5 * math.cos(math.pi * s)) ** 0.9

    def surf(u, v):
        s = v
        x = s * length
        hw = max(half_w(s), 2.0)
        y = (u - 0.5) * 2.0 * hw
        trough = 0.10 * hw * ((u - 0.5) * 2.0) ** 2           # leaf edges curl up a little
        rib = 7.0 * math.exp(-(((u - 0.5) * 2.0 * hw) / 9.0) ** 2) * min(1.0, s * 6)
        veins = 1.6 * math.sin(abs(y) * 0.05 - s * 30.0) * min(1.0, abs(y) / 40.0)
        return (x, y, height(s) + trough + rib + veins)
    m.grid("Leaf", 24, 48, surf, uv_fn=lambda u, v: (u, v), flip=True)

    def under(u, v):
        s = v
        hw = max(half_w(s), 2.0)
        return (s * length, (u - 0.5) * 2.0 * hw, -2.0)
    m.grid("Leaf", 4, 24, under, flip=False)
    # side skirts to close the volume (so the ramp has a body)
    for side in (0.0, 1.0):
        def skirt(u, v, side=side):
            s = u
            hw = max(half_w(s), 2.0)
            y = (side - 0.5) * 2.0 * hw
            top = height(s) + 0.10 * hw
            return (s * length, y, -2.0 + (top + 2.0) * v)
        m.grid("Leaf", 48, 2, skirt, flip=(side == 1.0))
    if kicker:
        def back(u, v):
            hw = max(half_w(1.0), 2.0)
            y = (u - 0.5) * 2.0 * hw
            return (length, y, -2.0 + (height(1.0) + 0.1 * hw * ((u - 0.5) * 2) ** 2 + 2.0) * v)
        m.grid("Leaf", 12, 2, back, flip=False)
    # stem
    if not kicker:
        tube_along(m, "Stem", [(length - 10, 0, rise - 6), (length + 160, 0, rise - 18), (length + 260, 0, rise - 60)],
                   [22, 18, 14], segs=12)
    return m


def pebble(seed, r=200.0, squash=0.62):
    m = Mesh()
    rng = Rng(seed)
    ks = [(rng.r(1.5, 3.0), rng.r(0, 6), rng.r(0, 6), rng.r(0.05, 0.12)) for _ in range(5)]

    def deform(p, d):
        k = 1.0
        for f, a, b, amp in ks:
            k += amp * math.sin(d[0] * f + a) * math.cos(d[1] * f + b) * math.sin(d[2] * f * 0.7 + a)
        z = p[2] * squash
        if z < -r * squash * 0.35:
            z = -r * squash * 0.35 - (z + r * squash * 0.35) * 0.15   # flattened base
        return (p[0] * k, p[1] * k * rng_y, z * k)
    rng_y = rng.r(0.75, 1.0)
    ellipsoid(m, "Rock", (0, 0, r * squash * 0.3), (r, r, r), 36, 20, deform)
    return m


def mushroom(seed):
    m = Mesh()
    rng = Rng(seed)
    H = rng.r(480, 620)
    lean = rng.r(-40, 40)
    pts = catmull([(0, 0, -10), (lean * 0.3, 0, H * 0.35), (lean * 0.8, 0, H * 0.7), (lean, 0, H)], 5)
    n = len(pts)
    radii = [70 - 25 * (i / (n - 1)) + 18 * math.exp(-((i / (n - 1)) / 0.12) ** 2) for i in range(n)]
    tube_along(m, "Stem", pts, radii, segs=20, cap=False)
    capR = rng.r(240, 320)
    capH = capR * 0.55
    top = (lean, 0, H - 30)

    def capf(u, v):
        a = u * 2 * math.pi
        th = v * math.pi * 0.5
        rr = capR * math.sin(th) * (1.0 + 0.03 * math.sin(a * 5 + seed))
        z = capH * math.cos(th) - (capR * 0.06) * (v ** 4)
        return (top[0] + rr * math.cos(a), top[1] + rr * math.sin(a), top[2] + z)
    m.grid("Cap", 48, 16, capf, wrap_u=True, flip=True)

    def gills(u, v):
        a = u * 2 * math.pi
        rr = capR * (1.0 - v * 0.82) * (1.0 + 0.03 * math.sin(a * 5 + seed))
        z = -capR * 0.06 + v * 26.0
        return (top[0] + rr * math.cos(a), top[1] + rr * math.sin(a), top[2] + z)
    m.grid("Stem", 48, 6, gills, wrap_u=True, flip=True)
    # white spots
    for i in range(14):
        a = rng.r(0, 2 * math.pi)
        th = rng.r(0.15, 1.15)
        rr = capR * math.sin(th)
        z = capH * math.cos(th)
        c = (top[0] + rr * math.cos(a), top[1] + rr * math.sin(a), top[2] + z)
        nrm = v_norm((math.cos(a) * math.sin(th) / capR, math.sin(a) * math.sin(th) / capR, math.cos(th) / capH))
        s = rng.r(14, 30)
        ellipsoid(m, "Spot", v_add(c, v_mul(nrm, -2.0)), (s, s, s * 0.35), 10, 6,
                  deform=lambda p, d, nrm=nrm: _align(p, nrm))
    return m


def _align(p, n):
    """Rotate p (authored with +Z up) so +Z aligns with n."""
    z = n
    x = v_norm(v_cross((0, 0, 1) if abs(n[2]) < 0.95 else (1, 0, 0), z))
    y = v_cross(z, x)
    return (x[0] * p[0] + y[0] * p[1] + z[0] * p[2], x[1] * p[0] + y[1] * p[1] + z[1] * p[2],
            x[2] * p[0] + y[2] * p[1] + z[2] * p[2])


def twig(seed):
    m = Mesh()
    rng = Rng(seed)
    L = rng.r(1500, 2100)
    ctrl = [(-L / 2, 0, 38), (-L / 6, rng.r(-60, 60), 44), (L / 6, rng.r(-60, 60), 40), (L / 2, 0, 34)]
    pts = catmull(ctrl, 8)
    n = len(pts)
    radii = [44 - 10 * (i / (n - 1)) + 6 * math.sin(i * 1.7) for i in range(n)]
    tube_along(m, "Bark", pts, radii, segs=14)
    b0 = pts[n // 3]
    tube_along(m, "Bark", catmull([b0, v_add(b0, (180, 160, 30)), v_add(b0, (300, 380, 50))], 5),
               [24, 20, 16, 13, 11, 9, 8, 7, 6, 5, 4][:11], segs=10)
    return m


def grass_clump(seed, n=9):
    m = Mesh()
    rng = Rng(seed)
    for i in range(n):
        a = rng.r(0, 2 * math.pi)
        d = rng.r(0, 260)
        base = (d * math.cos(a), d * math.sin(a), -20)
        H = rng.r(2600, 5600)
        wid = rng.r(110, 190)
        bend = rng.r(0.15, 0.45) * H
        face = rng.r(0, 2 * math.pi)
        fx, fy = math.cos(face), math.sin(face)

        def blade(u, v, base=base, H=H, wid=wid, bend=bend, fx=fx, fy=fy):
            s = v
            w = wid * (1.0 - s ** 1.4) * 0.5
            off = (u - 0.5) * 2 * w
            fold = abs(u - 0.5) * 2 * w * 0.25
            lean = bend * s * s
            return (base[0] + fx * lean - fy * off, base[1] + fy * lean + fx * off, base[2] + H * s * (1 - 0.15 * s * s) + fold)
        m.grid("Grass", 2, 16, blade, uv_fn=lambda u, v: (u, v))
    return m


def flower(seed, petal_mat="PetalWhite", petals=18, H=4200.0, R=900.0):
    m = Mesh()
    rng = Rng(seed)
    ctrl = [(0, 0, -50), (rng.r(-150, 150), rng.r(-150, 150), H * 0.4), (rng.r(-250, 250), rng.r(-250, 250), H * 0.8), (0, 0, H)]
    ctrl[3] = (ctrl[2][0] * 1.1, ctrl[2][1] * 1.1, H)
    pts = catmull(ctrl, 8)
    tube_along(m, "Stem", pts, [70 - 25 * i / (len(pts) - 1) for i in range(len(pts))], segs=12)
    head = pts[-1]
    tilt = rng.r(0.25, 0.5)
    # head normal tilted towards the arena (-X in flower space; rotated on placement)
    nrm = v_norm((-tilt, 0, 1))
    ellipsoid(m, "Center", head, (R * 0.28, R * 0.28, R * 0.1), 32, 12, deform=lambda p, d: _align(p, nrm))
    for i in range(petals):
        a = 2 * math.pi * i / petals + rng.r(-0.05, 0.05)
        L = R * rng.r(0.9, 1.05)
        pw = 2 * math.pi * R * 0.28 / petals * 1.25
        droop = rng.r(0.05, 0.2)

        def petal(u, v, a=a, L=L, pw=pw, droop=droop):
            s = v
            r = R * 0.22 + L * s
            w = pw * (math.sin(math.pi * min(s * 1.15, 1.0)) ** 0.6) * (0.6 + 0.6 * s)
            off = (u - 0.5) * w
            curl = -droop * L * s * s + 0.08 * w * ((u - 0.5) * 2) ** 2
            p = (r * math.cos(a) - off * math.sin(a), r * math.sin(a) + off * math.cos(a), curl + 10)
            return v_add(head, _align(p, nrm))
        m.grid(petal_mat, 4, 10, petal, uv_fn=lambda u, v: (u, v))
    # a few leaves on the stem
    for k in range(2):
        p0 = pts[len(pts) // 3 + k * 5]
        ang = rng.r(0, 2 * math.pi)
        Ll = rng.r(900, 1400)

        def stemleaf(u, v, p0=p0, ang=ang, Ll=Ll):
            s = v
            w = Ll * 0.22 * math.sin(math.pi * s) ** 0.8
            off = (u - 0.5) * w
            x = s * Ll
            z = 300 * math.sin(s * 1.4) - 260 * s * s
            return (p0[0] + x * math.cos(ang) - off * math.sin(ang), p0[1] + x * math.sin(ang) + off * math.cos(ang), p0[2] + z)
        m.grid("Stem", 4, 12, stemleaf)
    return m


def petal_debris(seed):
    m = Mesh()
    rng = Rng(seed)
    L, Wd = rng.r(420, 600), rng.r(160, 220)

    def p(u, v):
        s = v
        w = Wd * math.sin(math.pi * min(s * 1.1, 1.0)) ** 0.7
        off = (u - 0.5) * w
        z = 4 + 18 * ((u - 0.5) * 2) ** 2 + 30 * s * s
        return (s * L - L / 2, off, z)
    m.grid("Petal", 6, 12, p, uv_fn=lambda u, v: (u, v))
    return m


def main():
    jobs = {
        "SM_HiveWall_A": lambda: hive_panel(11),
        "SM_HiveWall_B": lambda: hive_panel(23),
        "SM_HiveWall_C": lambda: hive_panel(37),
        "SM_ArenaFloor": arena_floor,
        "SM_HexDais": hex_dais,
        "SM_LeafRamp": lambda: leaf(1500.0, 760.0, 166.0),
        "SM_LeafKicker": lambda: leaf(760.0, 520.0, 120.0, kicker=True),
        "SM_Pebble_A": lambda: pebble(5, 220, 0.6),
        "SM_Pebble_B": lambda: pebble(9, 160, 0.7),
        "SM_Pebble_C": lambda: pebble(14, 300, 0.5),
        "SM_Mushroom_A": lambda: mushroom(3),
        "SM_Mushroom_B": lambda: mushroom(8),
        "SM_Twig": lambda: twig(4),
        "SM_GrassClump_A": lambda: grass_clump(2),
        "SM_GrassClump_B": lambda: grass_clump(6, 12),
        "SM_Daisy": lambda: flower(5, "PetalWhite", 20, 4600, 950),
        "SM_PinkFlower": lambda: flower(12, "PetalPink", 9, 3800, 800),
        "SM_Sunflower": lambda: flower(21, "PetalYellow", 26, 6200, 1300),
        "SM_PetalDebris": lambda: petal_debris(3),
    }
    for name, fn in jobs.items():
        n = fn().write_obj(os.path.join(OUT, name + ".obj"))
        print(name, n)


if __name__ == "__main__":
    main()
