"""Generates giant bug-scale wildflowers for the Picnic meadow: tulips, lavender, poppies, allium, bluebells, dandelion clocks."""
import math, os
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_sub, v_mul, v_norm, v_cross

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)


def align(p, n):
    """Rotate p (authored with +Z up) so +Z aligns with n."""
    z = v_norm(n)
    x = v_norm(v_cross((0, 0, 1) if abs(z[2]) < 0.95 else (1, 0, 0), z))
    y = v_cross(z, x)
    return (x[0] * p[0] + y[0] * p[1] + z[0] * p[2], x[1] * p[0] + y[1] * p[1] + z[1] * p[2],
            x[2] * p[0] + y[2] * p[1] + z[2] * p[2])


def stem(m, rng, H, lean=250.0, r0=60.0, r1=34.0, mat="Stem"):
    ctrl = [(0, 0, -40), (rng.r(-lean, lean) * 0.3, rng.r(-lean, lean) * 0.3, H * 0.45), (rng.r(-lean, lean), rng.r(-lean, lean), H)]
    pts = catmull(ctrl, 10)
    tube_along(m, mat, pts, [r0 + (r1 - r0) * i / (len(pts) - 1) for i in range(len(pts))], segs=10)
    return pts


def strap_leaf(m, rng, L, W, ang, mat="Leaf", base=(0, 0, 0), arch=0.55):
    """Long strap leaf rising from the base and arching over."""
    def f(u, v, ang=ang):
        s = v
        w = W * math.sin(math.pi * min(s * 1.05, 1.0)) ** 0.5 * (1 - 0.6 * s)
        off = (u - 0.5) * w
        r = L * arch * math.sin(s * math.pi * 0.6) + L * 0.25 * s
        z = L * (0.9 * s - 0.75 * s * s) + abs(u - 0.5) * w * 0.25
        return (base[0] + r * math.cos(ang) - off * math.sin(ang), base[1] + r * math.sin(ang) + off * math.cos(ang), base[2] + z)
    m.grid(mat, 4, 14, f)


def tulip(seed, mat="TulipRed", H=5200.0):
    m = Mesh()
    rng = Rng(seed)
    pts = stem(m, rng, H, 180, 70, 50)
    for k in range(2):
        strap_leaf(m, rng, H * 0.55, 520, rng.r(0, 6.28) + k * 3.0)
    head = pts[-1]
    Rc, Hc = 520.0, 1150.0
    for i in range(6):
        a = 2 * math.pi * i / 6 + (0.5 if i % 2 else 0.0) * 0.0
        inner = i % 2 == 1
        rr = Rc * (0.86 if inner else 1.0)

        def petal(u, v, a=a, rr=rr):
            # cupped petal: bulges out in the middle, tips curl in slightly
            w = rr * 1.25 * math.sin(math.pi * min(v * 1.04, 1.0)) ** 0.55
            off = (u - 0.5) * w
            r = rr * (0.35 + 0.75 * math.sin(math.pi * 0.85 * v)) - 30 * abs(u - 0.5) * 2
            z = Hc * v
            ca, sa = math.cos(a), math.sin(a)
            return v_add(head, (r * ca - off * sa, r * sa + off * ca, z - 40))
        m.grid(mat, 6, 12, petal, flip=True)
    return m


def lavender(seed, H=3600.0, stems=9):
    m = Mesh()
    rng = Rng(seed)
    for s in range(stems):
        a0 = rng.r(0, 6.28)
        spread = rng.r(150, 650)
        h = H * rng.r(0.8, 1.1)
        tip = (spread * math.cos(a0), spread * math.sin(a0), h)
        pts = catmull([(rng.r(-60, 60), rng.r(-60, 60), -30), (tip[0] * 0.4, tip[1] * 0.4, h * 0.5), tip], 8)
        tube_along(m, "Stem", pts, [26 - 10 * i / (len(pts) - 1) for i in range(len(pts))], segs=6)
        # spike of bud whorls along the top third
        n = len(pts)
        for w in range(9):
            t = 0.62 + 0.36 * w / 8
            p = pts[min(int(t * (n - 1)), n - 1)]
            rad = 70 * (1 - 0.4 * w / 8)
            for b in range(6):
                ang = 2 * math.pi * b / 6 + w * 0.5
                c = (p[0] + rad * math.cos(ang), p[1] + rad * math.sin(ang), p[2])
                ellipsoid(m, "Lavender", c, (48, 48, 62), 6, 4)
    for k in range(5):
        strap_leaf(m, rng, 900, 90, rng.r(0, 6.28), arch=0.35)
    return m


def poppy(seed, H=4800.0):
    m = Mesh()
    rng = Rng(seed)
    pts = stem(m, rng, H, 420, 40, 30)
    head = pts[-1]
    face = v_norm((rng.r(-0.4, 0.4), rng.r(-0.4, 0.4), 1.0))
    R = 900.0
    for i in range(4):
        a0 = 2 * math.pi * i / 4 + rng.r(-0.15, 0.15)
        ph = rng.r(0, 6.28)

        def petal(u, v, a0=a0, ph=ph):
            # broad, crinkled, slightly cupped petal
            ang = a0 + (u - 0.5) * 1.9
            r = R * v * (1 + 0.06 * math.sin(u * 17 + ph) * v)
            z = 260 * v * v + 35 * math.sin(u * 23 + v * 9 + ph) * v
            return v_add(head, align((r * math.cos(ang), r * math.sin(ang), z + (i % 2) * 18), face))
        m.grid("PoppyRed", 14, 8, petal, flip=True)
    # seed pod and black stamens
    ellipsoid(m, "PoppyPod", v_add(head, align((0, 0, 110), face)), (150, 150, 120), 16, 10)
    for k in range(30):
        ang = 2 * math.pi * k / 30
        a = v_add(head, align((140 * math.cos(ang), 140 * math.sin(ang), 60), face))
        b = v_add(head, align((260 * math.cos(ang), 260 * math.sin(ang), 190), face))
        tube_along(m, "PoppyCenter", [a, b], [10, 8], segs=4)
        ellipsoid(m, "PoppyCenter", b, (22, 22, 22), 6, 4)
    return m


def allium(seed, H=7200.0):
    """Ornamental onion: tall bare stem topped by a perfect purple pom-pom of star florets."""
    m = Mesh()
    rng = Rng(seed)
    pts = stem(m, rng, H, 140, 75, 55)
    head = v_add(pts[-1], (0, 0, 520))
    R = 620.0
    ellipsoid(m, "AlliumCore", head, (R * 0.8, R * 0.8, R * 0.8), 24, 16)
    golden = math.pi * (3 - math.sqrt(5))
    N = 170
    for k in range(N):
        y = 1 - 2 * (k + 0.5) / N
        rr = math.sqrt(1 - y * y)
        th = golden * k
        d = (rr * math.cos(th), rr * math.sin(th), y)
        base = v_add(head, v_mul(d, R * 0.78))
        tip = v_add(head, v_mul(d, R * 1.05))
        tube_along(m, "Stem", [base, tip], [8, 6], segs=4, cap=False)
        ellipsoid(m, "Allium", tip, (60, 60, 26), 8, 4, deform=lambda p, dd, d=d: align(p, d))
    for k in range(3):
        strap_leaf(m, rng, 1600, 220, rng.r(0, 6.28), arch=0.7)
    return m


def bluebell(seed, H=3800.0, bells=7):
    """Arching stem with a one-sided row of nodding blue bells."""
    m = Mesh()
    rng = Rng(seed)
    side = rng.r(0, 6.28)
    dx, dy = math.cos(side), math.sin(side)
    ctrl = [(0, 0, -30), (dx * 200, dy * 200, H * 0.55), (dx * 900, dy * 900, H * 0.95), (dx * 1500, dy * 1500, H * 0.8)]
    pts = catmull(ctrl, 10)
    tube_along(m, "Stem", pts, [38 - 16 * i / (len(pts) - 1) for i in range(len(pts))], segs=8)
    n = len(pts)
    for b in range(bells):
        t = 0.45 + 0.53 * b / (bells - 1)
        p = pts[min(int(t * (n - 1)), n - 1)]
        size = 1.0 - 0.35 * b / (bells - 1)
        Lb, Rb = 520 * size, 230 * size
        hang = v_add(p, (-dy * 160 * (1 if b % 2 else -1), dx * 160 * (1 if b % 2 else -1), -120))
        tube_along(m, "Stem", catmull([p, v_add(p, (0, 0, 40)), hang], 3), [12, 11, 10, 9, 8, 8, 8], segs=5)
        axis = v_norm((rng.r(-0.25, 0.25), rng.r(-0.25, 0.25), -1.0))

        def bell(u, v, hang=hang, Lb=Lb, Rb=Rb, axis=axis):
            a = u * 2 * math.pi
            r = Rb * (0.35 + 0.65 * v ** 0.6)
            if v > 0.8:                                          # flared, curled-back lobes at the mouth
                r *= 1 + 0.9 * (v - 0.8) ** 1.3 * (1 + 0.25 * math.cos(6 * a))
            z = Lb * v - (0.0 if v < 0.85 else 160 * (v - 0.85) ** 1.5 * size)
            return v_add(hang, align((r * math.cos(a), r * math.sin(a), z), axis))
        m.grid("Bluebell", 18, 10, bell, wrap_u=True, flip=True)
    for k in range(4):
        strap_leaf(m, rng, 1700, 260, rng.r(0, 6.28), arch=0.8)
    return m


def dandelion(seed, H=5600.0):
    """Dandelion clock: a hollow stem carrying a sphere of seed parachutes."""
    m = Mesh()
    rng = Rng(seed)
    pts = stem(m, rng, H, 350, 48, 40)
    head = v_add(pts[-1], (0, 0, 120))
    ellipsoid(m, "PoppyPod", head, (120, 120, 120), 14, 10)
    R = 700.0
    golden = math.pi * (3 - math.sqrt(5))
    N = 150
    for k in range(N):
        y = 1 - 2 * (k + 0.5) / N
        if y < -0.55:
            continue                                            # bald patch where the stem joins
        rr = math.sqrt(1 - y * y)
        th = golden * k
        d = (rr * math.cos(th), rr * math.sin(th), y)
        tip = v_add(head, v_mul(d, R))
        tube_along(m, "Fluff", [v_add(head, v_mul(d, 110)), tip], [6, 4], segs=3, cap=False)

        def umb(u, v, tip=tip, d=d):
            a = u * 2 * math.pi
            r = 150 * v
            return v_add(tip, align((r * math.cos(a), r * math.sin(a), 55 * v ** 0.6), d))
        m.grid("Fluff", 8, 2, umb, wrap_u=True, flip=True)
    for k in range(5):
        strap_leaf(m, rng, 1300, 260, rng.r(0, 6.28), arch=0.9)
    return m


def main():
    jobs = {
        "SM_TulipRed": lambda: tulip(3, "TulipRed", 5200),
        "SM_TulipYellow": lambda: tulip(9, "TulipYellow", 4600),
        "SM_Lavender": lambda: lavender(4),
        "SM_Poppy": lambda: poppy(6),
        "SM_Allium": lambda: allium(2),
        "SM_Bluebell": lambda: bluebell(5),
        "SM_Dandelion": lambda: dandelion(7),
    }
    import sys
    only = sys.argv[1:]
    for name, fn in jobs.items():
        if only and name not in only:
            continue
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


if __name__ == "__main__":
    main()
