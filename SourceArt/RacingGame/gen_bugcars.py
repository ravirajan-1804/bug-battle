"""Seven creature kart bodies + wheels for the Garden Grand Prix (low-poly, Pixar-style).

Each car = SM_RGC_<Name>_Body (one mesh, several material slots) + SM_RGC_<Name>_Wheel.
Space matches the vehicle template's Chasis_Main: X forward, Y right, Z up, origin on the
ground at the car centre. Wheels: pivot at the hub, axle along local Y, tyre face at +Y
(same convention as SM_SportsCar_Wheel, so they drop into the template's wheel slots).
Bodies stay narrow between the wheels (karts with exposed wheels) so nothing clips tyres.
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "..", "BugBattle"))
from meshlib import Mesh, ellipsoid, tube_along, catmull, Rng, v_add, v_sub, v_mul, v_norm, v_cross  # noqa: E402

OUT = os.path.join(HERE, "obj_cars")
os.makedirs(OUT, exist_ok=True)

# Wheel hubs of the template skeleton (measured in-editor, see README)
WXF, WXR, WY, WZ, WR = 134.0, -130.0, 90.0, 27.0, 39.0
TYRE_IN = WY - 14.0          # inner tyre face is at WY-8; keep 6 cm clearance


# ------------------------------------------------------------------ primitives
def loft(m, mat, x0, x1, prof, nx=24, nr=20, exp=2.6):
    """Superellipse loft along X. prof(t)->(cz, hw, hh, cy). Ends are pinched closed by prof."""
    def fn(u, v):
        x = x0 + (x1 - x0) * v
        cz, hw, hh, cy = prof(v)
        a = u * 2 * math.pi
        c, s = math.cos(a), math.sin(a)
        e = 2.0 / exp
        y = cy + hw * math.copysign(abs(s) ** e, s)
        z = cz + hh * math.copysign(abs(c) ** e, c)
        return (x, y, z)
    return m.grid(mat, nr, nx, fn, wrap_u=True, flip=True)


def sphere(m, mat, c, r, nu=14, nv=9, sq=(1, 1, 1)):
    ellipsoid(m, mat, c, (r * sq[0], r * sq[1], r * sq[2]), nu, nv)


def cartoon_eye(m, c, r, look=(1, 0, 0.05), pupil=0.55):
    """Big Pixar eye: white ball, black pupil and a glint, looking along `look`."""
    sphere(m, "EyeWhite", c, r, 18, 12)
    d = v_norm(look)
    sphere(m, "EyePupil", v_add(c, v_mul(d, r * 0.62)), r * pupil, 14, 9, (0.55, 1, 1))
    sphere(m, "EyeWhite", v_add(v_add(c, v_mul(d, r * 0.95)), (0, r * 0.18, r * 0.25)), r * 0.16, 8, 6)


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def bump(t, a, b):
    """0 outside [a,b], 1 in the middle, smooth edges (for profiles)."""
    if t <= a or t >= b:
        return 0.0
    k = (t - a) / (b - a)
    return math.sin(math.pi * k)


def kart_tub(m, mat, trim, length=(-205, 215), hw=58, z0=26, top=70, nose_drop=0.6):
    """Shared low kart tub between the wheels + a contrasting bumper/sill band."""
    def prof(t):
        p = smooth01(t / 0.12) * smooth01((1 - t) / 0.1)
        h = (top - z0) * 0.5
        hh = h * (0.35 + 0.65 * p) * (1 - nose_drop * smooth01((t - 0.75) / 0.25) * 0.5)
        return (z0 + h, hw * (0.3 + 0.7 * p), hh, 0.0)
    loft(m, mat, length[0], length[1], prof, 28, 22, 3.2)
    # side sills (trim colour) just above ground, inside the tyres
    for s in (-1, 1):
        tube_along(m, trim, catmull([(WXR + 45, s * (hw - 4), 28), (0, s * (hw + 2), 26), (WXF - 45, s * (hw - 4), 28)], 5),
                   [9] * 11, segs=8)


def axle_pods(m, mat):
    """Little axle stubs so each wheel visibly connects to the body."""
    for x in (WXF, WXR):
        for s in (-1, 1):
            tube_along(m, mat, [(x, s * 30, WZ), (x, s * (TYRE_IN - 2), WZ)], [11, 9], segs=10)


def spoiler(m, mat, strut, x=-200, z=112, w=95, chord=55, tilt=0.18):
    def wing(u, v):
        y = (u - 0.5) * 2 * w
        xx = x - v * chord
        zz = z + v * chord * tilt + 6 * math.sin(math.pi * v)
        return (xx, y, zz)
    m.grid(mat, 8, 4, wing)
    m.grid(mat, 8, 4, lambda u, v: (lambda p: (p[0], p[1], p[2] - 5))(wing(u, v)), flip=True)
    for s in (-1, 1):
        tube_along(m, strut, [(x - chord * 0.4, s * w * 0.55, 60), (x - chord * 0.45, s * w * 0.55, z - 2)], [6, 5], segs=6)


def antenna(m, mat, tip_mat, base, mid, tip, r=4.5, ball=9):
    tube_along(m, mat, catmull([base, mid, tip], 5), [r] * 11, segs=6)
    sphere(m, tip_mat, tip, ball, 10, 7)


# ------------------------------------------------------------------ wheels
def wheel(rim_mat="Rim", tyre_mat="Tyre", hub_mat="Hub", spokes=5, style="disc"):
    """Chunky cartoon wheel, radius WR, tyre from y=-8 to y=27 (outer face at +Y)."""
    m = Mesh()
    y0, y1 = -8.0, 27.0
    R, Ri = WR, WR * 0.66
    seg = 22

    def tyre(u, v):
        a = u * 2 * math.pi
        # rounded tyre cross-section: v runs inner sidewall -> tread -> outer sidewall
        th = v * math.pi
        y = y0 + (y1 - y0) * (0.5 - 0.5 * math.cos(th))
        r = Ri + (R - Ri) * (math.sin(th) ** 0.45)
        return (r * math.cos(a), y, r * math.sin(a))
    m.grid(tyre_mat, seg, 8, tyre, wrap_u=True, flip=False)
    # tread blocks (low-poly lugs) for a toy look
    for k in range(14):
        a = 2 * math.pi * k / 14
        c, s = math.cos(a), math.sin(a)
        p0 = (R * c, (y0 + y1) / 2, R * s)
        ellipsoid(m, tyre_mat, p0, (4.5, 15, 4.5), 6, 4,
                  deform=lambda p, d, c=c, s=s: (p[0] * abs(c) + p[2] * 0 + 0, p[1], p[2]))
    # rim dish (outer face) + inner backing
    for yy, flip in ((y1 - 6, False), (y0 + 5, True)):
        def dish(u, v, yy=yy):
            a = u * 2 * math.pi
            r = Ri * 1.02 * (1 - v)
            return (r * math.cos(a), yy - (3 if style == "disc" else 0) * v, r * math.sin(a))
        m.grid(rim_mat, seg, 3, dish, wrap_u=True, flip=flip)
    # spokes / petals in hub colour
    for k in range(spokes):
        a = 2 * math.pi * (k + 0.5) / spokes
        tip = (Ri * 0.82 * math.cos(a), y1 - 4, Ri * 0.82 * math.sin(a))
        tube_along(m, hub_mat, [(0, y1 - 4, 0), tip], [5.5, 3.5], segs=6)
    sphere(m, hub_mat, (0, y1 - 3, 0), Ri * 0.3, 12, 8, (1, 0.55, 1))
    return m


# ------------------------------------------------------------------ the seven cars
def snail():
    m = Mesh()
    # foot/body: long, low, teal-green slug-like racer with a raised nose
    def prof(t):
        p = smooth01(t / 0.1) * smooth01((1 - t) / 0.08)
        nose = smooth01((t - 0.65) / 0.35)
        return (40 + 14 * nose, 60 * (0.35 + 0.65 * p), 20 * (0.4 + 0.6 * p) + 8 * nose, 0.0)
    loft(m, "Paint", -220, 235, prof, 30, 22, 2.4)
    axle_pods(m, "Trim")
    # spiral shell (lathe of a coiled tube) sitting on the back half
    pts, rad = [], []
    for k in range(64):
        t = k / 63
        ang = t * 2.6 * 2 * math.pi
        rr = 68 * (1 - 0.82 * t)
        pts.append((-55 + rr * math.cos(ang), 0, 112 + rr * math.sin(ang)))
        rad.append(max(6.0, 50 * (1 - 0.85 * t)))
    tube_along(m, "Shell", pts, rad, segs=16)
    # shell side spiral stripe (slightly inset rings on both faces)
    for s in (-1, 1):
        spts = [(p[0], s * (r * 0.92), p[2]) for p, r in zip(pts[::3], rad[::3])]
        tube_along(m, "ShellStripe", spts, [5] * len(spts), segs=6, cap=False)
    # eye stalks with big eyes
    for s in (-1, 1):
        base, tip = (175, s * 22, 58), (205, s * 40, 128)
        tube_along(m, "Paint", catmull([base, (195, s * 30, 95), tip], 5), [9, 9, 8, 8, 7, 7, 7, 6, 6, 6, 6], segs=8)
        cartoon_eye(m, v_add(tip, (4, 0, 10)), 19, (1, s * 0.15, 0.05))
    # smile + cheek spots
    tube_along(m, "EyePupil", catmull([(232, -22, 46), (240, 0, 40), (232, 22, 46)], 5), [2.5] * 11, segs=5)
    for s in (-1, 1):
        sphere(m, "Accent", (150, s * 56, 52), 10, 10, 7, (1, 0.4, 0.7))
    spoiler(m, "Accent", "Trim", x=-205, z=96, w=70, chord=40)
    return m


def beetle():
    m = Mesh()
    kart_tub(m, "Trim", "Accent", hw=56)
    axle_pods(m, "Trim")
    # domed elytra (two halves with a seam) - glossy metallic emerald
    for s in (-1, 1):
        ellipsoid(m, "Paint", (-30, s * 33, 78), (165, 52, 58), 26, 14,
                  deform=lambda p, d: (p[0], p[1] if d[1] * s > -0.2 else p[1] * 0.2, max(p[2], -10)))
    tube_along(m, "Trim", catmull([(-190, 0, 80), (-30, 0, 138), (125, 0, 95)], 6), [5] * 13, segs=6, cap=False)
    # pronotum (shield behind the head) and head
    ellipsoid(m, "Accent", (140, 0, 72), (55, 58, 34), 20, 12)
    ellipsoid(m, "Trim", (200, 0, 58), (40, 44, 28), 18, 10)
    # rhino horn curving up
    hp = catmull([(220, 0, 62), (250, 0, 85), (258, 0, 120), (240, 0, 142)], 5)
    tube_along(m, "Trim", hp, [16 - 1.0 * k for k in range(len(hp))], segs=10)
    for s in (-1, 1):
        cartoon_eye(m, (222, s * 28, 72), 14, (1, s * 0.2, 0.05))
    # spotted highlights on the shell
    for k, (x, y) in enumerate([(-80, 30), (-10, 52), (40, 28), (-130, 50)]):
        for s in (-1, 1):
            sphere(m, "Accent", (x, s * y, 128 - abs(x + 30) * 0.18), 9, 10, 6, (1, 1, 0.35))
    return m


def bee():
    m = Mesh()
    # teardrop body striped yellow/black (stripes as separate rings so colours stay crisp)
    def prof(t):
        p = math.sin(math.pi * min(1.0, t * 1.05)) ** 0.7
        return (60, 62 * p + 2, 42 * p + 2, 0.0)
    nst = 7
    edges = [-225 + k * (440 / nst) for k in range(nst + 1)]
    for k in range(nst):
        def pk(t, k=k):
            tt = (k + t) / nst
            return prof(tt)
        loft(m, "Paint" if k % 2 else "Trim", edges[k], edges[k + 1], pk, 4, 22, 2.2)
    axle_pods(m, "Trim")
    # fuzzy head with big eyes and antennae
    sphere(m, "Trim", (225, 0, 70), 34, 18, 12)
    for s in (-1, 1):
        cartoon_eye(m, (245, s * 20, 82), 15, (1, s * 0.2, 0.05))
        antenna(m, "Trim", "Trim", (235, s * 12, 100), (240, s * 26, 140), (262, s * 40, 160))
    # wings as a twin rear spoiler (white-blue, opaque)
    for s in (-1, 1):
        def wing(u, v, s=s):
            ang = 0.35 + 0.5 * v
            rlen = 140 * (0.25 + 0.75 * math.sin(math.pi * u) ** 0.6)
            return (-20 - 120 * u, s * (30 + rlen * math.cos(ang) * v + 10), 112 + rlen * math.sin(ang) * v * 0.6)
        m.grid("Wing", 8, 6, wing)
        m.grid("Wing", 8, 6, lambda u, v, s=s: (lambda p: (p[0], p[1], p[2] - 4))(wing(u, v, s)), flip=True)
        tube_along(m, "Trim", [(-40, s * 28, 96), (-60, s * 34, 114)], [7, 6], segs=6)
    # stinger
    tube_along(m, "Trim", [(-215, 0, 60), (-250, 0, 54), (-268, 0, 50)], [16, 8, 1.5], segs=10)
    return m


def spider():
    m = Mesh()
    kart_tub(m, "Trim", "Accent", hw=54, top=62)
    axle_pods(m, "Trim")
    # angular abdomen (low-poly faceted: few segments) with red hourglass
    ellipsoid(m, "Paint", (-95, 0, 88), (105, 72, 52), 10, 6)
    ellipsoid(m, "Accent", (-95, 0, 140), (34, 20, 6), 8, 4,
              deform=lambda p, d: (p[0], p[1] * (0.35 + abs(d[0]) ** 0.8), p[2]))
    # cephalothorax / cockpit
    ellipsoid(m, "Paint", (95, 0, 72), (85, 56, 38), 10, 6)
    # eight jointed legs arching over the wheels (fender struts)
    for s in (-1, 1):
        for k, x in enumerate((150, 85, 15, -55)):
            knee = (x + 10, s * 95, 150 - k * 6)
            foot = (x + (35 if k < 2 else -25), s * 128, 42)
            tube_along(m, "Trim", catmull([(x, s * 40, 85), knee, foot], 4), [9, 9, 8, 8, 7, 6, 5, 4, 3], segs=7)
            sphere(m, "Accent", knee, 9, 8, 6)
    # eye cluster: two big + six little red eyes
    for s in (-1, 1):
        cartoon_eye(m, (165, s * 20, 88), 15, (1, s * 0.15, 0.1))
        for j in range(3):
            sphere(m, "EyeRed", (150 - j * 10, s * (36 + j * 6), 102 + j * 6), 6 - j, 8, 6)
    # fangs
    for s in (-1, 1):
        tube_along(m, "Accent", [(178, s * 14, 56), (205, s * 12, 42), (214, s * 6, 30)], [8, 5, 1.5], segs=8)
    return m


def scorpion():
    m = Mesh()
    kart_tub(m, "Trim", "Accent", hw=57, top=66)
    axle_pods(m, "Trim")
    # armoured segmented back plates
    for k in range(6):
        x = 120 - k * 52
        w = 62 - k * 3
        ellipsoid(m, "Paint" if k % 2 == 0 else "Accent", (x, 0, 74), (34, w, 26), 12, 7)
    # head shield
    ellipsoid(m, "Paint", (175, 0, 62), (50, 58, 26), 14, 8)
    for s in (-1, 1):
        cartoon_eye(m, (205, s * 22, 78), 13, (1, s * 0.2, 0.08))
    # pincers as front bumpers
    for s in (-1, 1):
        arm = catmull([(180, s * 45, 50), (215, s * 72, 44), (242, s * 60, 44)], 4)
        tube_along(m, "Paint", arm, [13, 13, 12, 12, 12, 11, 11, 11, 10], segs=8)
        claw = (250, s * 55, 44)
        ellipsoid(m, "Accent", claw, (30, 18, 14), 12, 8)
        tube_along(m, "Accent", [(260, s * 62, 44), (282, s * 52, 46), (290, s * 38, 46)], [8, 6, 2], segs=6)
        tube_along(m, "Accent", [(260, s * 46, 40), (280, s * 40, 38), (286, s * 30, 38)], [7, 5, 2], segs=6)
    # raised segmented tail: rises from the rear and arcs forward over the cockpit
    C, R = (-105.0, 160.0), 85.0
    tail = [(-185, 0, 82)]
    for k in range(9):
        th = math.radians(205 - k * 22)
        tail.append((C[0] + R * math.cos(th), 0, C[1] + R * math.sin(th)))
    path = catmull(tail, 3)
    tube_along(m, "Paint", path, [17 - 9 * k / (len(path) - 1) for k in range(len(path))], segs=10)
    for k, p in enumerate(tail[1:]):
        sphere(m, "Paint" if k % 2 == 0 else "Accent", p, 22 - 1.4 * k, 12, 8)
    tip = tail[-1]
    d = v_norm(v_sub(tail[-1], tail[-2]))
    bulb = v_add(tip, v_mul(d, 18))
    sphere(m, "Sting", bulb, 15, 12, 8)
    tube_along(m, "Sting", [bulb, v_add(bulb, (22, 0, -8)), v_add(bulb, (34, 0, -26))], [10, 6, 1.5], segs=8)
    return m


def ant():
    m = Mesh()
    kart_tub(m, "Trim", "Accent", hw=52, top=60)
    axle_pods(m, "Trim")
    # three classic ant segments: gaster (rear), thorax (cockpit), head (front)
    ellipsoid(m, "Paint", (-120, 0, 88), (92, 60, 50), 22, 12)
    ellipsoid(m, "Paint", (25, 0, 80), (62, 42, 34), 18, 10)
    tube_along(m, "Trim", [(-35, 0, 82), (-25, 0, 80)], [20, 18], segs=10)
    ellipsoid(m, "Paint", (170, 0, 78), (58, 54, 44), 20, 12)
    # racing number disc on the gaster
    for s in (-1, 1):
        ellipsoid(m, "Accent", (-120, s * 58, 92), (32, 4, 32), 14, 6)
    for s in (-1, 1):
        cartoon_eye(m, (205, s * 26, 92), 16, (1, s * 0.25, 0.05))
        # elbowed antennae
        tube_along(m, "Trim", [(195, s * 18, 116), (205, s * 30, 160), (250, s * 48, 172)], [4.5, 4, 3], segs=6)
        sphere(m, "Trim", (252, s * 48, 172), 7, 8, 6)
        # mandibles
        tube_along(m, "Accent", catmull([(215, s * 22, 52), (250, s * 26, 46), (262, s * 8, 44)], 4), [9, 8, 7, 6, 5, 4, 3, 2, 1.5],
                   segs=7)
    spoiler(m, "Accent", "Trim", x=-210, z=118, w=85, chord=45)
    return m


def butterfly():
    m = Mesh()
    # slender body: thorax pod + long tapering abdomen
    def prof(t):
        p = math.sin(math.pi * min(1.0, t)) ** 0.6
        return (56 + 6 * t, 46 * p + 2, 30 * p + 2, 0.0)
    loft(m, "Trim", -215, 175, prof, 26, 18, 2.2)
    sphere(m, "Trim", (200, 0, 66), 30, 16, 10)
    axle_pods(m, "Trim")
    for s in (-1, 1):
        cartoon_eye(m, (215, s * 20, 78), 15, (1, s * 0.2, 0.05))
        antenna(m, "Trim", "Accent", (205, s * 12, 92), (220, s * 34, 150), (250, s * 62, 175), r=3.5, ball=10)
    # two pairs of colourful wing panels spreading outward with a little dihedral
    def wingpair(s, x0, length, span, dihedral, sweep, mat, edge, spot):
        tdh = math.tan(math.radians(dihedral))

        def fn(u, v):
            # u: leading -> trailing edge, v: root -> tip; rounded planform
            chord = length * (0.35 + 0.65 * math.sqrt(max(0.0, 1 - v ** 2.2)))
            x_le = x0 + sweep * v
            x = x_le - u * chord
            y = s * (36 + span * v)
            z = 96 + span * v * tdh + 10 * math.sin(math.pi * u) * (1 - v)
            return (x, y, z)
        m.grid(mat, 8, 8, fn)
        m.grid(mat, 8, 8, lambda u, v: (lambda p: (p[0], p[1], p[2] - 4))(fn(u, v)), flip=True)
        tube_along(m, edge, [fn(u, 1.0 - 1e-3) for u in [k / 8 for k in range(9)]] , [4] * 9, segs=5, cap=False)
        tube_along(m, edge, [fn(0.0, v) for v in [k / 8 for k in range(9)]], [3.5] * 9, segs=5, cap=False)
        for (u, v, r) in ((0.45, 0.62, 16), (0.6, 0.3, 10)):
            c = fn(u, v)
            ellipsoid(m, spot, (c[0], c[1], c[2] + 2.5), (r, r, 2.5), 12, 5)
    for s in (-1, 1):
        wingpair(s, 95, 130, 125, 24, 40, "Paint", "Trim", "Accent")
        wingpair(s, -35, 110, 95, 14, -45, "Accent", "Trim", "Paint")
    return m


CARS = {
    "Snail": snail, "Beetle": beetle, "Bee": bee, "Spider": spider,
    "Scorpion": scorpion, "Ant": ant, "Butterfly": butterfly,
}


def main():
    only = sys.argv[1:]
    for name, fn in CARS.items():
        if only and name not in only:
            continue
        m = fn()
        n = m.write_obj(os.path.join(OUT, "SM_RGC_%s_Body.obj" % name))
        w = wheel(spokes={"Snail": 3, "Beetle": 6, "Bee": 6, "Spider": 8, "Scorpion": 4, "Ant": 3, "Butterfly": 5}[name])
        nw = w.write_obj(os.path.join(OUT, "SM_RGC_%s_Wheel.obj" % name))
        xs = [p[0] for p in m.p]; ys = [p[1] for p in m.p]; zs = [p[2] for p in m.p]
        print("%-10s body %5d tris  wheel %4d tris  bounds x[%4d,%4d] y[%4d,%4d] z[%4d,%4d]" % (
            name, n, nw, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))


if __name__ == "__main__":
    main()
