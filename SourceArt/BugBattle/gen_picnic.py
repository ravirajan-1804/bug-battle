"""Generates the Picnic Platter Arena meshes: a bug-scale dinner plate (half-pipe rim) on a gingham blanket."""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_sub, v_mul, v_norm, v_cross

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)

R_FLAT = 7500.0          # flat well of the plate (the driving floor)
R_BANK = 2400.0          # horizontal run of the banked rim
H_BANK = 1800.0          # height of the banked rim


def revolve(m, profile, segs, uv_scale=2000.0):
    """profile: list of (r, z, mat) from the axis outwards; mat colours the band up to the next point.
    Front faces point to the left of the profile direction (up on the floor, inward on the wall)."""
    rings = []
    for r, z, _ in profile:
        row = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            x, y = r * math.cos(a), r * math.sin(a)
            row.append(m.vert((x, y, z), (x / uv_scale, y / uv_scale)))
        rings.append(row)
    for j in range(len(profile) - 1):
        mat = profile[j][2]
        for i in range(segs):
            i2 = (i + 1) % segs
            a, b, c, d = rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]
            m.quad(mat, a, d, c, b)
    return rings


# ---------- the plate ----------

def platter():
    """Dinner plate arena: flat well, half-pipe rim curling slightly inward, rounded lip, outer skirt."""
    m = Mesh()
    prof = []
    b0, b1 = R_FLAT * 0.91, R_FLAT * 0.94          # painted ring on the plate well
    radii = sorted(set([R_FLAT * (k / 16.0) ** 0.75 for k in range(17)] + [b0, b1]))
    for r in radii:
        prof.append((r, 0.0, "PlateBand" if b0 <= r < b1 - 1 else "Ceramic"))
    # banked rim: elliptical quarter-pipe that tips just past vertical
    n = 22
    for k in range(1, n + 1):
        th = math.radians(100.0 * k / n)
        r = R_FLAT + R_BANK * math.sin(th)
        z = H_BANK * (1 - math.cos(th))
        deg = 100.0 * k / n
        prof.append((r, z, "PlateBand" if 38.0 <= deg < 58.0 else "Ceramic"))
    # rounded lip and outer skirt down to the blanket
    top_r, top_z = prof[-1][0], prof[-1][1]
    for k in range(1, 9):
        a = math.pi * k / 8
        prof.append((top_r + 70 - 70 * math.cos(a), top_z + 70 * math.sin(a), "Ceramic"))
    outer_r = prof[-1][0]
    lip_z = prof[-1][1]
    for k in range(1, 9):
        s = k / 8
        prof.append((outer_r + 60 * math.sin(math.pi * s * 0.5), lip_z - (lip_z + 10) * s, "Ceramic"))
    prof.append((outer_r - 900, -10.0, "Ceramic"))    # underside, hidden under the blanket line
    revolve(m, prof, 320)
    return m


# ---------- centre hill ----------

def melon_dome(A=3000.0, B=2300.0, H=650.0, stripes=9):
    """Half watermelon cut lengthwise, lying cut-side down: oval drivable dome. The mesh is laid out in
    (t along the melon, phi around it) so the dark stripes are real quad columns with smooth, wavy,
    slightly feathered edges running pole to pole; a thin red / white edge shows the cut at the plate."""
    m = Mesh()
    nt = 90
    ts = [-math.cos(math.pi * i / nt) for i in range(nt + 1)]      # denser near the poles

    # column boundaries in phi: flesh, white, then alternating light/dark stripes, mirrored
    span0, span1 = 0.11, math.pi - 0.11
    cols = []                                                        # (phi0, phi1, mat, stripe index)
    cols.append((0.0, 0.06, "MelonFlesh", -1))
    cols.append((0.06, 0.11, "MelonWhite", -1))
    n = stripes * 2
    for k in range(n):
        a0 = span0 + (span1 - span0) * k / n
        a1 = span0 + (span1 - span0) * (k + 1) / n
        cols.append((a0, a1, "RindDark" if k % 2 else "RindLight", k))
    cols.append((span1, math.pi - 0.06, "MelonWhite", -1))
    cols.append((math.pi - 0.06, math.pi, "MelonFlesh", -1))

    def warp(phi, t, k):
        """Shift interior stripe boundaries so the edges wander and feather like a real rind."""
        if phi <= span0 + 1e-6 or phi >= span1 - 1e-6:
            return phi
        w = (0.04 * math.sin(4.3 * t + 1.7 * k) + 0.02 * math.sin(11.0 * t + 2.9 * k)
             + 0.01 * math.sin(27.0 * t + 5.1 * k))
        return phi + w * math.sqrt(max(0.0, 1 - t * t)) ** 0.3

    def surf(t, phi):
        c = math.cos(phi)
        x = A * t
        y = B * math.sqrt(max(0.0, 1 - t * t)) * c
        rho2 = t * t + (1 - t * t) * c * c
        return (x, y, H * max(0.0, 1 - rho2) ** 1.5 - 3.0)

    sub = 4
    for (p0, p1, mat, k) in cols:
        steps = sub if k >= 0 else 1
        grid = []
        for t in ts:
            row = []
            for s_ in range(steps + 1):
                ph = p0 + (p1 - p0) * s_ / steps
                if s_ == 0:
                    ph = warp(p0, t, k)
                elif s_ == steps:
                    ph = warp(p1, t, k + 1)
                else:
                    lo, hi = warp(p0, t, k), warp(p1, t, k + 1)
                    ph = lo + (hi - lo) * s_ / steps
                row.append(m.vert(surf(t, ph), (ph * 3, t * 4)))
            grid.append(row)
        for i in range(nt):
            for s_ in range(steps):
                a, b, c, d = grid[i][s_], grid[i][s_ + 1], grid[i + 1][s_ + 1], grid[i + 1][s_]
                m.quad(mat, a, b, c, d)
    return m

def melon_slice(seed=3, R=1700.0, T=420.0):
    """Half-moon slice of watermelon lying flat: red flesh with black seeds, white and green rind round the arc."""
    m = Mesh()
    rng = Rng(seed)

    def band(rho):
        return "MelonFlesh" if rho < 0.86 else ("MelonWhite" if rho < 0.93 else "RindDark")

    nu, nv = 64, 16
    top = [[m.vert((R * (j / nv) * math.cos(math.pi * i / nu), R * (j / nv) * math.sin(math.pi * i / nu),
                    T + 18 * (1 - (j / nv) ** 2)), (i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            m.quad(band((j + 0.5) / nv), top[j][i], top[j + 1][i], top[j + 1][i + 1], top[j][i + 1])
    # curved rind side
    m.grid("RindDark", nu, 3, lambda u, v: (R * math.cos(math.pi * u), R * math.sin(math.pi * u), T * v),
           uv_fn=lambda u, v: (u * 6, v))
    # straight cut face (y = 0), banded like the top
    for k in range(nv * 2):
        x0, x1 = -R + 2 * R * k / (nv * 2), -R + 2 * R * (k + 1) / (nv * 2)
        rho = abs((x0 + x1) * 0.5) / R
        a, b = m.vert((x0, 0, 0)), m.vert((x1, 0, 0))
        c, d = m.vert((x1, 0, T + 18 * (1 - (x1 / R) ** 2))), m.vert((x0, 0, T + 18 * (1 - (x0 / R) ** 2)))
        m.quad(band(rho), a, b, c, d)
    # teardrop seeds in loose rows, pointing towards the centre
    for row, rr in enumerate((0.42, 0.58, 0.72)):
        n = 7 + row * 3
        for k in range(n):
            ang = math.pi * (k + 0.5) / n + rng.r(-0.05, 0.05)
            r = R * (rr + rng.r(-0.03, 0.03))
            c = (r * math.cos(ang), r * math.sin(ang), T + 18 * (1 - (r / R) ** 2) - 6)
            ca, sa = math.cos(ang), math.sin(ang)
            ellipsoid(m, "MelonSeed", c, (1, 1, 1), 10, 6,
                      deform=lambda p, d, ca=ca, sa=sa: ((p[0] * 55 * (1 + 0.35 * d[0])) * ca - p[1] * 34 * sa,
                                                         (p[0] * 55 * (1 + 0.35 * d[0])) * sa + p[1] * 34 * ca, p[2] * 14))
    return m


def wooden_spatula(x_peak0=6450.0, x_peak1=6950.0, x_end=14400.0, z_peak=2215.0, T=110.0):
    """Giant wooden spatula laid over the plate rim along +X: wide blade resting on the plate floor at x=0,
    rising to clear the lip (plateau x_peak0..x_peak1), handle running down to the ground outside."""
    m = Mesh()
    nx, K = 160, 16
    xs = [x_end * i / nx for i in range(nx + 1)]

    ramp = 1100.0                                         # length of the gentle on-ramp at each end
    s1 = z_peak / (x_peak0 - ramp / 2)
    s2 = (z_peak + 45.0) / ((x_end - x_peak1) - ramp / 2)

    def raw(x):
        if x <= x_peak0:
            return s1 * x * x / (2 * ramp) if x < ramp else s1 * (x - ramp / 2)
        if x <= x_peak1:
            return z_peak
        d = x_end - x
        return -45.0 + (s2 * d * d / (2 * ramp) if d < ramp else s2 * (d - ramp / 2))

    # soften the kinks so wheels roll smoothly onto and off the slopes
    def zb(x):
        w = 420.0
        acc = 0.0
        for k in range(-6, 7):
            acc += raw(min(max(x + w * k / 6, 0.0), x_end))
        return acc / 13 if 600 < x < x_end - 600 else raw(x)

    def half_w(x):
        blade, neck = 900.0, 430.0
        if x < 4600:
            hw = blade
        elif x < 6200:
            s = (x - 4600) / 1600
            hw = blade + (neck - blade) * (3 * s * s - 2 * s ** 3)
        else:
            hw = neck
        # rounded blade tip and handle end
        if x < 250:
            hw *= math.sqrt(max(0.05, 1 - ((250 - x) / 250) ** 2))
        if x > x_end - 430:
            hw *= math.sqrt(max(0.05, 1 - ((x - (x_end - 430)) / 430) ** 2))
        return hw

    def thick(x):
        e = min(x, x_end - x) / 1200.0
        return max(6.0, T * min(1.0, e))

    rings = []
    for x in xs:
        z0 = zb(x)
        hw = half_w(x)
        tk = thick(x)
        zfloor = 0.0 if z0 < 240 else z0                 # solid near the ends so nothing wedges underneath
        if x > x_peak1 and z0 < 240:
            zfloor = -45.0
        row = []
        for k in range(K + 1):                            # flat-topped, rounded edges, from +y to -y
            a = math.pi * k / K
            y = hw * math.cos(a)
            z = z0 + tk * (1 - abs(math.cos(a)) ** 8) ** 0.35
            row.append(m.vert((x, y, z), (x / 900.0, k / K)))
        for k in range(1, K):
            y = -hw * math.cos(math.pi * k / K)
            row.append(m.vert((x, y, zfloor - 1.0 if z0 < 240 else z0), (x / 900.0, 1 + k / K)))
        rings.append(row)
    nr = len(rings[0])
    for i in range(nx):
        for k in range(nr):
            k2 = (k + 1) % nr
            m.quad("SpatulaWood", rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k])
    for i, sgn in ((0, -1), (nx, 1)):
        ring = rings[i]
        c = m.vert((xs[i], 0, sum(m.p[q][2] for q in ring) / nr))
        for k in range(nr):
            k2 = (k + 1) % nr
            m.tri("SpatulaWood", c, ring[k], ring[k2]) if sgn > 0 else m.tri("SpatulaWood", c, ring[k2], ring[k])
    return m

# ---------- ramps ----------

def toast_ramp(seed, L=1900.0, Wd=1700.0, T=130.0, rise=430.0):
    """Slice of toast propped on a sugar cube: tip at x=0 on the plate, back edge raised by `rise`."""
    m = Mesh()
    rng = Rng(seed)
    pitch = math.atan2(rise, L)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def outline(u):
        """Bread-slice outline in (x along slope, y across): square bottom, domed top lobes at the far end."""
        a = u * 2 * math.pi
        x = 0.5 + 0.5 * math.cos(a)
        y = 0.5 * math.sin(a)
        sx = math.copysign(abs(math.cos(a)) ** 0.35, math.cos(a)) * 0.5 + 0.5
        sy = math.copysign(abs(math.sin(a)) ** 0.35, math.sin(a)) * 0.5
        if sx > 0.75:                     # domed crown with two shoulders
            sy *= 1.0 + 0.08 * math.sin(math.pi * (sx - 0.75) / 0.25)
        return sx * L, sy * Wd

    def place(x, y, z):
        return (x * cp - z * sp, y, x * sp + z * cp)

    def thick(x):
        """Slice thins to a feather edge at the tip so wheels roll straight on."""
        k = min(1.0, max(0.0, x / (0.35 * L)))
        return max(4.0, T * k * k * (3 - 2 * k))

    segs = 64
    crust = 70.0
    for top in (True, False):
        def face(u, v, top=top):
            ox, oy = outline(u)
            cx, cy = L * 0.5, 0.0
            k = v
            x, y = cx + (ox - cx) * k, cy + (oy - cy) * k
            puff = 10.0 * (1 - k ** 4) if top else 0.0
            wob = 3 * math.sin(x * 0.02 + y * 0.015 + seed) * min(1.0, x / (0.35 * L))
            z = (thick(x) + puff + wob) if top else 0.0
            return place(x, y, z)
        mat_fn = None
        idx = m.grid("Bread", segs, 8, face, uv_fn=lambda u, v: (0.5 + 0.5 * v * math.cos(u * 6.28), 0.5 + 0.5 * v * math.sin(u * 6.28)),
                     wrap_u=True, flip=top)
    # crust rim
    def rim(u, v):
        ox, oy = outline(u)
        bulge = 1.0 + 0.02 * math.sin(math.pi * v)
        cx = L * 0.5
        return place(cx + (ox - cx) * bulge, oy * bulge, thick(ox) * v)
    m.grid("Crust", segs, 3, rim, uv_fn=lambda u, v: (u * 8, v), wrap_u=True, flip=False)
    # crust ring on top surface (toasted band)
    def band(u, v):
        ox, oy = outline(u)
        cx = L * 0.5
        k = 1.0 - (crust / (0.5 * Wd)) * v
        x = cx + (ox - cx) * k
        return place(x, oy * k, thick(x) + 2 + 3 * (1 - v) * min(1.0, x / (0.35 * L)))
    m.grid("Crust", segs, 1, band, uv_fn=lambda u, v: (u * 8, v), wrap_u=True, flip=False)
    # skirt from the underside down to the plate so cars cannot wedge beneath the slice
    def skirt(u, v):
        ox, oy = outline(u)
        p = place(ox, oy, 0.0)
        return (p[0], p[1], p[2] * (1 - v) - 2.0 * v)
    m.grid("Crust", segs, 2, skirt, uv_fn=lambda u, v: (u * 8, v), wrap_u=True, flip=True)
    # sugar cube under the raised edge
    sc = rise * 1.05
    cx = L * cp - sc * 0.55
    for (x0, y0) in ((cx, -Wd * 0.22), (cx + rng.r(-40, 40), Wd * 0.24)):
        cube(m, "Sugar", (x0, y0, sc * 0.5 - 15), sc * 0.5, rng.r(-0.3, 0.3))
    return m


def cube(m, mat, c, h, yaw, n=0.12):
    ca, sa = math.cos(yaw), math.sin(yaw)

    def deform(p, d):
        q = [math.copysign(abs(d[i]) ** n, d[i]) * h for i in range(3)]
        return (q[0] * ca - q[1] * sa, q[0] * sa + q[1] * ca, q[2])
    ellipsoid(m, mat, c, (1, 1, 1), 16, 12, deform=deform)


# ---------- soda can tunnel ----------

def soda_can(R=820.0, L=2900.0, wall=22.0):
    """Tipped-over soda can, both ends open: drive-through tunnel along X."""
    m = Mesh()
    segs = 72
    neck = 230.0
    # (x, radius) along the can; ends neck in a little like a real can
    xs = [(-L / 2, R - 70), (-L / 2 + neck * 0.5, R - 18), (-L / 2 + neck, R), (L / 2 - neck, R), (L / 2 - neck * 0.5, R - 18), (L / 2, R - 70)]
    cz = R - 10.0

    def ring(x, r):
        return [(x, r * math.sin(2 * math.pi * i / segs), cz + r * math.cos(2 * math.pi * i / segs)) for i in range(segs)]

    o_rings = [[m.vert(p, (i / segs * 3, (x + L / 2) / 900.0)) for i, p in enumerate(ring(x, r))] for x, r in xs]
    i_rings = [[m.vert(p, (i / segs * 3, (x + L / 2) / 900.0)) for i, p in enumerate(ring(x, r - wall))] for x, r in xs]
    for j in range(len(xs) - 1):
        omat = "CanPaint" if j == 2 else "CanMetal"
        for i in range(segs):
            i2 = (i + 1) % segs
            a, b, c, d = o_rings[j][i], o_rings[j][i2], o_rings[j + 1][i2], o_rings[j + 1][i]
            m.quad(omat, a, d, c, b)
            a, b, c, d = i_rings[j][i], i_rings[j][i2], i_rings[j + 1][i2], i_rings[j + 1][i]
            m.quad("CanMetal", a, b, c, d)
    # rolled rims at both open ends
    for end, sign in ((0, -1), (len(xs) - 1, 1)):
        x0, r0 = xs[end]
        pts = []
        for i in range(segs + 1):
            pts.append(None)
        lip = 26.0
        rows = []
        for k in range(7):
            a = math.pi * k / 6
            rr = r0 - wall * 0.5 + (wall * 0.5 + lip * 0.4) * math.cos(a)
            xx = x0 + sign * lip * math.sin(a)
            rows.append([m.vert(p, (i / segs, k / 6)) for i, p in enumerate(ring(xx, rr))])
        for k in range(6):
            for i in range(segs):
                i2 = (i + 1) % segs
                a, b, c, d = rows[k][i], rows[k][i2], rows[k + 1][i2], rows[k + 1][i]
                if sign > 0:
                    m.quad("CanMetal", a, b, c, d)
                else:
                    m.quad("CanMetal", a, d, c, b)
    # stripe band of a second colour round the middle of the label
    def stripe(u, v):
        a = u * 2 * math.pi
        x = -180 + 360 * v + 120 * math.sin(a * 2)
        r = R + 2.0
        return (x, r * math.sin(a), cz + r * math.cos(a))
    m.grid("CanStripe", segs, 2, stripe, uv_fn=lambda u, v: (u, v), wrap_u=True, flip=True)
    # solid flanks under the belly so cars cannot wedge into the gap beneath the curved sides
    phi = math.radians(70.0)
    yb, zt = R * math.sin(phi), cz - R * math.cos(phi)
    x0, x1 = -L / 2 + neck * 0.5, L / 2 - neck * 0.5
    for side in (1, -1):
        m.grid("CanPaint", 12, 2, lambda u, v, side=side: (x0 + (x1 - x0) * u, side * yb, (zt + 5) * v - 5),
               uv_fn=lambda u, v: (u * 3, v), flip=(side > 0))
    return m


# ---------- cover props ----------

def cheese_wedge(seed, R=2300.0, ang=42.0, H=1000.0):
    """Swiss cheese wedge: apex at origin pointing -X... wedge spans +X, rind on the curved back."""
    m = Mesh()
    rng = Rng(seed)
    half = math.radians(ang) * 0.5
    craters = {k: [(rng.r(0.15, 0.85), rng.r(0.15, 0.85), rng.r(0.06, 0.13)) for _ in range(7)] for k in ("top", "l", "r")}

    def dent(face, u, v, size):
        d = 0.0
        hole = False
        for cu, cv, cr in craters[face]:
            q = ((u - cu) ** 2 + ((v - cv) * 1.0) ** 2) ** 0.5
            if q < cr:
                d = max(d, size * cr * math.sqrt(1 - (q / cr) ** 2))
                hole = True
        return d, hole

    def add_face(face, fn, nrm_fn, nu, nv, uvs):
        idx = []
        holes = []
        for j in range(nv + 1):
            row = []
            hrow = []
            for i in range(nu + 1):
                u, v = i / nu, j / nv
                p = fn(u, v)
                d, h = dent(face, u, v, 2.6 * (R if face == "top" else H) * 0.5)
                n = nrm_fn(u, v)
                row.append(m.vert(v_sub(p, v_mul(n, d)), (u * uvs, v * uvs)))
                hrow.append(h)
            idx.append(row)
            holes.append(hrow)
        for j in range(nv):
            for i in range(nu):
                h = holes[j][i] and holes[j + 1][i + 1]
                m.quad("CheeseHole" if h else "Cheese", idx[j][i], idx[j + 1][i], idx[j + 1][i + 1], idx[j][i + 1])

    # top: polar patch, u across the angle, v along the radius
    def top(u, v):
        a = -half + 2 * half * u
        r = R * (0.02 + 0.98 * v)
        return (r * math.cos(a), r * math.sin(a), H)
    add_face("top", top, lambda u, v: (0, 0, 1), 40, 40, 4)

    # flat cut faces
    for face, sgn in (("l", -1), ("r", 1)):
        a = sgn * half
        dirv = (math.cos(a), math.sin(a), 0)
        nrm = (-math.sin(a) * sgn, math.cos(a) * sgn, 0.0)   # outward

        def f(u, v, dirv=dirv):
            r = R * (0.02 + 0.98 * u)
            return (dirv[0] * r, dirv[1] * r, H * v)
        if sgn > 0:
            add_face(face, f, lambda u, v, n=nrm: n, 40, 20, 4)
        else:
            add_face(face, lambda u, v, f=f: f(u, 1 - v), lambda u, v, n=nrm: n, 40, 20, 4)

    # curved rind
    def rind(u, v):
        a = -half + 2 * half * u
        return (R * math.cos(a), R * math.sin(a), H * v)
    m.grid("CheeseRind", 30, 4, rind, uv_fn=lambda u, v: (u * 4, v), flip=False)
    # apex sliver
    def apex(u, v):
        a = -half + 2 * half * u
        r = R * 0.02
        return (r * math.cos(a), r * math.sin(a), H * v)
    m.grid("Cheese", 4, 2, apex, flip=True)
    return m


def strawberry(seed, R=720.0):
    m = Mesh()
    rng = Rng(seed)

    def berry(p, d):
        # wider at the shoulders (+X), pointed at the tip (-X)
        s = d[0]
        k = 0.78 + 0.22 * s - 0.25 * max(0.0, -s) ** 2
        return (p[0] * 1.15, p[1] * k, p[2] * k)
    tilt = 0.35
    c = (0, 0, R * 0.68)
    ellipsoid(m, "Strawberry", c, (R, R, R), 40, 26, deform=berry)
    # seeds sit in little pits on the surface
    for i in range(70):
        th = math.acos(rng.r(-0.95, 0.85))
        ph = rng.r(0, 2 * math.pi)
        d = (math.cos(th), math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph))
        p = berry(v_mul(d, R), d)
        pos = v_add(c, v_mul(p, 0.995))
        n = v_norm(p)
        s = 26.0
        ellipsoid(m, "Seed", pos, (s, s, s), 6, 4, deform=lambda q, dd, n=n: (q[0] + n[0] * 4, q[1] + n[1] * 4, q[2] + n[2] * 4))
    # calyx leaves at the shoulder end
    top = v_add(c, (R * 1.12, 0, 0))
    for k in range(7):
        a = 2 * math.pi * k / 7 + rng.r(-0.15, 0.15)
        Lf = R * rng.r(0.65, 0.85)

        def leaf(u, v, a=a, Lf=Lf):
            w = Lf * 0.3 * math.sin(math.pi * v) ** 0.7
            off = (u - 0.5) * w
            r = v * Lf
            x = -Lf * 0.25 * v * v + 30
            return v_add(top, (x - 40, r * math.cos(a) - off * math.sin(a), r * math.sin(a) + off * math.cos(a)))
        m.grid("Calyx", 3, 8, leaf, flip=True)
    tube_along(m, "Calyx", [v_add(top, (0, 0, 0)), v_add(top, (160, 0, 40)), v_add(top, (260, 30, 120))], [40, 34, 28], segs=8)
    return m


def grape_bunch(seed, R=360.0):
    m = Mesh()
    rng = Rng(seed)
    spots = []
    # a loose pile lying on its side: big bottom layer, smaller top layer
    for layer, (count, z, spread) in enumerate(((7, 0.0, 1.9), (4, 1.25, 1.1), (1, 2.3, 0.0))):
        for i in range(count):
            a = 2 * math.pi * i / max(count, 1) + rng.r(-0.3, 0.3) + layer
            d = spread * R * (0.6 + 0.4 * rng.f()) if count > 1 else 0.0
            spots.append((d * math.cos(a) * 1.3, d * math.sin(a), R * 0.92 + z * R))
    for s in spots:
        r = R * rng.r(0.9, 1.08)
        ellipsoid(m, "Grape", s, (r * 1.08, r, r), 24, 16)
    stem = catmull([(spots[-1][0], spots[-1][1], spots[-1][2] + R * 0.8), (R * 1.6, 0, R * 3.2), (R * 2.6, R * 0.4, R * 3.0)], 4)
    tube_along(m, "Stem", stem, [34 - 2 * i for i in range(len(stem))], segs=8)
    return m


def cookie(seed, R=950.0, H=95.0):
    """Choc-chip cookie: a low drivable bump with a bevelled edge."""
    m = Mesh()
    rng = Rng(seed)
    ph = [rng.r(0, 6.28) for _ in range(3)]

    def rim(a):
        return R * (1 + 0.04 * math.sin(3 * a + ph[0]) + 0.03 * math.sin(7 * a + ph[1]))

    def top(u, v):
        a = u * 2 * math.pi
        rho = 1 - v
        z = H * min(1.0, (1 - rho) / 0.32) ** 0.8 + 8 * math.sin(a * 9 + rho * 11 + ph[2]) * (1 - rho)
        return (rim(a) * rho * math.cos(a), rim(a) * rho * math.sin(a), z - 6)
    m.grid("Cookie", 96, 14, top, uv_fn=lambda u, v: (0.5 + 0.5 * (1 - v) * math.cos(u * 6.28), 0.5 + 0.5 * (1 - v) * math.sin(u * 6.28)),
           wrap_u=True, flip=False)
    for i in range(16):
        a = rng.r(0, 2 * math.pi)
        d = math.sqrt(rng.f()) * R * 0.68
        s = rng.r(55, 95)
        ellipsoid(m, "Choc", (d * math.cos(a), d * math.sin(a), H - 30), (s, s * 0.85, s * 0.6), 10, 8)
    return m


# ---------- outside the plate ----------

def blanket(half=16000.0, cell=500.0):
    """Gingham picnic blanket with soft wrinkles; stays flat under the plate."""
    m = Mesh()
    n = int(2 * half / cell)
    idx = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x, y = -half + i * cell, -half + j * cell
            r = math.hypot(x, y)
            w = min(1.0, max(0.0, (r - 10200.0) / 1500.0))
            z = -6.0 + w * (14 * math.sin(x * 0.0011 + y * 0.0004) * math.sin(y * 0.0013) + 9 * math.sin(x * 0.0031 - y * 0.0023))
            if i in (0, n) or j in (0, n):
                z -= 30.0
            row.append(m.vert((x, y, z), (x / cell, y / cell)))
        idx.append(row)
    for j in range(n):
        for i in range(n):
            si, sj = (i // 2) % 2, (j // 2) % 2
            mat = "GinghamDark" if si and sj else ("GinghamMid" if si or sj else "GinghamLight")
            m.quad(mat, idx[j][i], idx[j][i + 1], idx[j + 1][i + 1], idx[j + 1][i])
    return m


def basket(Lx=6400.0, Ly=4200.0, H=3600.0, band=300.0):
    """Wicker picnic basket with a lid and an arched handle."""
    m = Mesh()

    def body(u, v, h0, h1, inset=0.0):
        a = u * 2 * math.pi
        sx = math.copysign(abs(math.cos(a)) ** 0.25, math.cos(a))
        sy = math.copysign(abs(math.sin(a)) ** 0.25, math.sin(a))
        z = h0 + (h1 - h0) * v
        taper = 1.0 - 0.05 * (1 - z / H)
        weave = 18 * math.sin(a * 140) * math.sin(z * 0.03)
        return ((Lx * 0.5 - inset) * sx * taper + weave * sx, (Ly * 0.5 - inset) * sy * taper + weave * sy, z)
    bands = int(H / band)
    for b in range(bands):
        mat = "WickerA" if b % 2 == 0 else "WickerB"
        m.grid(mat, 96, 3, lambda u, v, b=b: body(u, v, b * band - (40 if b == 0 else 0), (b + 1) * band), uv_fn=lambda u, v: (u * 30, v), wrap_u=True, flip=False)
    # lid
    def lid(u, v):
        a = u * 2 * math.pi
        sx = math.copysign(abs(math.cos(a)) ** 0.25, math.cos(a))
        sy = math.copysign(abs(math.sin(a)) ** 0.25, math.sin(a))
        k = 1.02 * (1 - v ** 3)
        return (Lx * 0.5 * sx * k, Ly * 0.5 * sy * k, H + 260 * math.sqrt(max(0.0, 1 - (1 - v) ** 2)) * 0.6 + 40)
    m.grid("WickerB", 96, 10, lid, uv_fn=lambda u, v: (u * 30, v * 6), wrap_u=True, flip=False)
    # handle
    pts = [(0, -Ly * 0.42, H + 120)]
    for k in range(1, 12):
        a = math.pi * k / 12
        pts.append((0, -Ly * 0.42 * math.cos(a), H + 120 + 1900 * math.sin(a)))
    pts.append((0, Ly * 0.42, H + 120))
    tube_along(m, "WickerA", pts, [90] * len(pts), segs=12)
    return m


def fork(L=4800.0):
    """Steel fork lying on the blanket along +X (tines at +X)."""
    m = Mesh()
    flat = lambda p, n: ((p[0], p[1], p[2] * 0.32 + 30), n)
    sub = Mesh()
    handle = catmull([(0, 0, 40), (L * 0.3, 0, 60), (L * 0.55, 0, 90), (L * 0.66, 0, 120)], 6)
    tube_along(sub, "Steel", handle, [150, 165, 175, 160, 140, 120, 95, 80, 72, 70, 72, 80, 95, 110, 120, 130, 140, 150, 160][:len(handle)], segs=16)
    m.append(sub, flat)
    head = Mesh()
    ellipsoid(head, "Steel", (L * 0.72, 0, 130), (260, 300, 70), 24, 12)
    m.append(head, flat)
    for k in range(4):
        y = (k - 1.5) * 150
        t = Mesh()
        tube_along(t, "Steel", catmull([(L * 0.72, y * 0.8, 140), (L * 0.85, y, 150), (L, y, 210)], 5), [52, 48, 44, 40, 36, 33, 30, 28, 26, 24, 22], segs=10)
        m.append(t, flat)
    return m


# ---------- realistic foods ----------

def align(p, n):
    """Rotate p (authored with +Z up) so +Z aligns with n."""
    z = v_norm(n)
    x = v_norm(v_cross((0, 0, 1) if abs(z[2]) < 0.95 else (1, 0, 0), z))
    y = v_cross(z, x)
    return (x[0] * p[0] + y[0] * p[1] + z[0] * p[2], x[1] * p[0] + y[1] * p[1] + z[1] * p[2],
            x[2] * p[0] + y[2] * p[1] + z[2] * p[2])


def extrude(m, mat, pts, z0, z1, top_mat=None, dome=0.0, zfn=None):
    """Closed prism from a CCW outline; optional domed top and per-point top offset zfn(i)."""
    n = len(pts)
    top_mat = top_mat or mat
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    zt = [z1 + (zfn(i) if zfn else 0.0) for i in range(n)]
    bot = [m.vert((p[0], p[1], z0), (p[0] / 300.0, p[1] / 300.0)) for p in pts]
    top = [m.vert((p[0], p[1], zt[i]), (p[0] / 300.0, p[1] / 300.0)) for i, p in enumerate(pts)]
    for i in range(n):
        i2 = (i + 1) % n
        m.quad(mat, bot[i], bot[i2], top[i2], top[i])
    # top: two rings so the dome stays soft
    mid = [m.vert((cx + (p[0] - cx) * 0.6, cy + (p[1] - cy) * 0.6, zt[i] + dome * 0.75), (0.5, 0.5)) for i, p in enumerate(pts)]
    c_top = m.vert((cx, cy, z1 + dome), (0.5, 0.5))
    c_bot = m.vert((cx, cy, z0), (0.5, 0.5))
    for i in range(n):
        i2 = (i + 1) % n
        m.quad(top_mat, top[i], top[i2], mid[i2], mid[i])
        m.tri(top_mat, c_top, mid[i], mid[i2])
        m.tri(mat, c_bot, bot[i2], bot[i])


def rounded_poly(corners, rad, per=6):
    """CCW polygon with rounded corners."""
    out = []
    n = len(corners)
    for i in range(n):
        p0, p1, p2 = corners[i - 1], corners[i], corners[(i + 1) % n]
        a = v_norm((p0[0] - p1[0], p0[1] - p1[1], 0))
        b = v_norm((p2[0] - p1[0], p2[1] - p1[1], 0))
        s = (p1[0] + a[0] * rad, p1[1] + a[1] * rad)
        e = (p1[0] + b[0] * rad, p1[1] + b[1] * rad)
        for k in range(per + 1):
            t = k / per
            # quadratic bezier through the corner
            x = (1 - t) ** 2 * s[0] + 2 * (1 - t) * t * p1[0] + t * t * e[0]
            y = (1 - t) ** 2 * s[1] + 2 * (1 - t) * t * p1[1] + t * t * e[1]
            out.append((x, y))
    return out


def scale_poly(pts, k, wob=0.0, freq=0, seed=0):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for i, p in enumerate(pts):
        f = k + wob * math.sin(i * freq * 2 * math.pi / len(pts) + seed)
        out.append((cx + (p[0] - cx) * f, cy + (p[1] - cy) * f))
    return out


def sandwich_half(m, ox, oy, yaw, seed):
    rng = Rng(seed)
    S = 1700.0
    tri = rounded_poly([(0, 0), (S, 0), (0, S)], 160, 6)
    tri = [(x - S / 3, y - S / 3) for x, y in tri]
    ca, sa = math.cos(yaw), math.sin(yaw)
    P = lambda pts: [(ox + x * ca - y * sa, oy + x * sa + y * ca) for x, y in pts]
    extrude(m, "Crust", P(tri), 0, 40)
    extrude(m, "Crust", P(scale_poly(tri, 0.97)), 40, 175, top_mat="Bread")
    extrude(m, "Cheese", P(scale_poly(tri, 1.06)), 175, 200)
    extrude(m, "Ham", P(scale_poly(tri, 1.03, 0.025, 9, seed)), 200, 245, zfn=lambda i: 8 * math.sin(i * 0.9))
    for k in range(2):
        tx, ty = rng.r(-250, 250), rng.r(-250, 250)
        circ = [(tx + 420 * math.cos(a), ty + 420 * math.sin(a)) for a in [2 * math.pi * i / 24 for i in range(24)]]
        extrude(m, "TomatoRed", P(circ), 245, 300, top_mat="TomatoFlesh")
    extrude(m, "Lettuce", P(scale_poly(tri, 1.1, 0.05, 14, seed + 1)), 300, 325, zfn=lambda i: 22 * math.sin(i * 1.7 + seed))
    extrude(m, "Crust", P(scale_poly(tri, 0.97)), 325, 470, top_mat="Crust", dome=70)


def sandwich():
    """Two triangle halves of a ham-cheese-tomato-lettuce sandwich, pulled apart so a car-wide lane runs between them."""
    m = Mesh()
    sandwich_half(m, -600, -600, 0.0, 3)
    sandwich_half(m, 600, 600, math.pi, 8)
    return m


def croissant(seed=4, R=950.0):
    m = Mesh()
    rng = Rng(seed)
    pts, radii = [], []
    n = 60
    for i in range(n + 1):
        s = i / n
        a = math.radians(205 + 130 * s)
        base = 90 + 430 * math.sin(math.pi * s) ** 0.9
        ridge = 0.86 + 0.14 * abs(math.cos(s * math.pi * 7))
        r = base * ridge
        pts.append((R * math.cos(a), R * math.sin(a) + R * 0.75, r * 0.78))
        radii.append(r)
    sub = Mesh()
    tube_along(sub, "Croissant", pts, radii, segs=24)
    m.append(sub, lambda p, nn: ((p[0], p[1], max(p[2] * 0.78 + 8, -10)), nn))
    return m


def drumstick(seed=6):
    m = Mesh()
    rng = Rng(seed)
    L, R = 1150.0, 430.0
    ph = [rng.r(0, 6.28) for _ in range(4)]

    def meat(p, d):
        s = (d[0] + 1) * 0.5                         # 0 at the bone end, 1 at the fat end
        k = 0.22 + 0.78 * s ** 0.55                 # teardrop: knuckle-thin at the bone, round at the thigh
        bump = 1 + 0.05 * math.sin(d[1] * 11 + ph[0]) * math.sin(d[2] * 9 + ph[1]) + 0.03 * math.sin(d[0] * 17 + ph[2])
        return (p[0], p[1] * k * bump, p[2] * k * bump * 0.85)
    ellipsoid(m, "FriedSkin", (0, 0, R * 0.82), (L * 0.5, R, R), 40, 24, deform=meat)
    bone = [(-L * 0.42, 0, R * 0.62), (-L * 0.75, 0, R * 0.55), (-L * 1.05, 0, R * 0.5)]
    tube_along(m, "Bone", bone, [80, 70, 75], segs=14)
    for dy in (-70, 70):
        ellipsoid(m, "Bone", (-L * 1.08, dy, R * 0.5), (110, 95, 95), 14, 10)
    return m


def egg_half(seed=2, a=540.0, b=390.0):
    """Boiled egg half lying cut-face up."""
    m = Mesh()

    def shell(u, v):
        ang = u * 2 * math.pi
        th = v * math.pi * 0.5                      # 0 at the rim, pi/2 at the bottom
        x = a * math.cos(th) * math.cos(ang) * (1.0 + 0.08 * math.cos(ang))
        y = b * math.cos(th) * math.sin(ang)
        z = b - b * math.sin(th)
        return (x, y, z)
    m.grid("EggWhite", 48, 12, shell, wrap_u=True, flip=True)
    # cut face: white ring then yolk dome
    rim = [shell(i / 48, 0) for i in range(48)]
    yolk_r = 0.55
    ring = [m.vert((p[0], p[1], b), (0, 0)) for p in rim]
    inner = [m.vert((p[0] * yolk_r, p[1] * yolk_r, b + 4), (0, 0)) for p in rim]
    for i in range(48):
        i2 = (i + 1) % 48
        m.quad("EggWhite", ring[i], ring[i2], inner[i2], inner[i])
    ellipsoid(m, "EggYolk", (a * 0.04, 0, b + 4), (a * yolk_r * 0.95, b * yolk_r * 0.95, 70), 32, 12,
              deform=lambda p, d: (p[0], p[1], max(p[2], 0.0)))
    return m


def donut(seed=5, R=760.0, r=300.0):
    m = Mesh()
    rng = Rng(seed)
    segs, rs = 64, 28
    ph = rng.r(0, 6.28)
    idx = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        row = []
        for j in range(rs):
            b = 2 * math.pi * j / rs
            rr = r * (1 + 0.04 * math.sin(a * 5 + ph))
            p = ((R + rr * math.cos(b)) * math.cos(a), (R + rr * math.cos(b)) * math.sin(a), r + rr * math.sin(b))
            row.append(m.vert(p, (i / segs * 4, j / rs)))
        idx.append(row)
    for i in range(segs):
        i2 = (i + 1) % segs
        a = 2 * math.pi * (i + 0.5) / segs
        for j in range(rs):
            j2 = (j + 1) % rs
            b = 2 * math.pi * (j + 0.5) / rs
            drip = 0.25 + 0.2 * math.sin(a * 7 + ph) + 0.1 * math.sin(a * 13)
            mat = "Icing" if math.sin(b) > -drip and not (math.cos(b) > 0.9 and math.sin(b) < 0.1) else "Dough"
            m.quad(mat, idx[i][j], idx[i2][j], idx[i2][j2], idx[i][j2])
    cols = ["SprinkleA", "SprinkleB", "SprinkleC"]
    for k in range(70):
        a = rng.r(0, 2 * math.pi)
        b = rng.r(0.25, 2.4)
        rr = r + 6
        c = ((R + rr * math.cos(b)) * math.cos(a), (R + rr * math.cos(b)) * math.sin(a), r + rr * math.sin(b))
        d = rng.r(0, 6.28)
        L = 45
        tube_along(m, cols[k % 3], [v_add(c, (-L * math.cos(d), -L * math.sin(d), 0)), v_add(c, (L * math.cos(d), L * math.sin(d), 0))],
                   [13, 13], segs=6)
    return m


def carrot_sticks(seed=3):
    m = Mesh()
    rng = Rng(seed)
    sticks = [(0, 0, 0, 0.1), (60, 260, 0, -0.15), (-80, -260, 0, 0.05), (40, 120, 1, 0.5), (-20, -120, 1, -0.4), (10, 0, 2, 0.2)]
    for x, y, layer, yaw in sticks:
        L, w = rng.r(650, 800), rng.r(95, 120)
        ca, sa = math.cos(yaw), math.sin(yaw)
        c = (x, y, w + layer * w * 1.8)

        def deform(p, d, ca=ca, sa=sa, L=L, w=w):
            q = [math.copysign(abs(d[i]) ** 0.25, d[i]) for i in range(3)]
            lx, ly, lz = q[0] * L, q[1] * w * (1 - 0.15 * (q[0] + 1) * 0.5), q[2] * w * (1 - 0.15 * (q[0] + 1) * 0.5)
            return (lx * ca - ly * sa, lx * sa + ly * ca, lz)
        ellipsoid(m, "Carrot", c, (1, 1, 1), 20, 10, deform=deform)
    return m


def breadstick_bridge(seed=11, L=4200.0, H=460.0, w=340.0, t=170.0):
    """Arched grissini bridge along +X: feather-thin ends on the plate, cars can pass under the middle."""
    m = Mesh()
    rng = Rng(seed)
    nx, K = 70, 14

    def base(s):
        return H * math.sin(math.pi * s)

    def thick(s):
        e = min(s, 1 - s) / 0.1
        return t * min(1.0, e) ** 0.7 if e < 1 else t

    rings = []
    for i in range(nx + 1):
        s = i / nx
        x = s * L
        zb = base(s)
        zfloor = 0.0 if zb < 230 else zb            # solid near the ends so nothing wedges underneath
        tk = max(thick(s), 3.0)
        wob = 1 + 0.04 * math.sin(x * 0.011 + seed) + 0.03 * math.sin(x * 0.037)
        row = []
        for k in range(K + 1):                      # top arc from +y to -y
            a = math.pi * k / K
            y = w * wob * math.cos(a)
            z = zb + tk * math.sin(a) ** 0.6
            row.append(m.vert((x, y, z), (x / 600.0, k / K)))
        for k in range(1, K):                       # flat underside back from -y to +y
            y = -w * wob * math.cos(math.pi * k / K)
            row.append(m.vert((x, y, zfloor - 1.0 if zfloor == 0.0 else zb), (x / 600.0, 1 + k / K)))
        rings.append(row)
    nr = len(rings[0])
    for i in range(nx):
        for k in range(nr):
            k2 = (k + 1) % nr
            m.quad("Breadstick", rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k])
    # end caps
    for i, sgn in ((0, -1), (nx, 1)):
        ring = rings[i]
        c = m.vert((sum(m.p[q][0] for q in ring) / nr, 0, sum(m.p[q][2] for q in ring) / nr), (0.5, 0.5))
        for k in range(nr):
            k2 = (k + 1) % nr
            if sgn > 0:
                m.tri("Breadstick", c, ring[k], ring[k2])
            else:
                m.tri("Breadstick", c, ring[k2], ring[k])
    # sesame seeds pressed flat into the top
    for _ in range(160):
        s = rng.r(0.06, 0.94)
        a = rng.r(0.2, math.pi - 0.2)
        x = s * L
        y = w * math.cos(a) * 0.95
        z = base(s) + thick(s) * math.sin(a) ** 0.6
        nrm = v_norm((0, math.cos(a) * 0.6, math.sin(a)))
        ang = rng.r(0, 6.28)
        ellipsoid(m, "Sesame", (x, y, z - 2), (26, 15, 6), 8, 5,
                  deform=lambda p, d, nrm=nrm, ang=ang: align((p[0] * math.cos(ang) - p[1] * math.sin(ang),
                                                                 p[0] * math.sin(ang) + p[1] * math.cos(ang), p[2]), nrm))
    return m


def main():
    jobs = {
        "SM_Platter": platter,
        "SM_MelonDome": melon_dome,
        "SM_ToastRamp": lambda: toast_ramp(4),
        "SM_SodaCan": soda_can,
        "SM_CheeseWedge": lambda: cheese_wedge(7),
        "SM_Strawberry": lambda: strawberry(3),
        "SM_GrapeBunch": lambda: grape_bunch(5),
        "SM_Cookie_A": lambda: cookie(2),
        "SM_Cookie_B": lambda: cookie(9, 760.0, 80.0),
        "SM_PicnicBlanket": blanket,
        "SM_PicnicBasket": basket,
        "SM_Fork": fork,
        "SM_Sandwich": sandwich,
        "SM_Croissant": croissant,
        "SM_Drumstick": drumstick,
        "SM_EggHalf": egg_half,
        "SM_Donut": donut,
        "SM_CarrotSticks": carrot_sticks,
        "SM_BreadstickBridge": breadstick_bridge,
        "SM_MelonSlice": melon_slice,
        "SM_WoodenSpatula": wooden_spatula,
    }
    import sys
    only = sys.argv[1:]
    for name, fn in jobs.items():
        if only and name not in only:
            continue
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


if __name__ == "__main__":
    main()
