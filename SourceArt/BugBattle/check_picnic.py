import math
import gen_picnic as g
from meshlib import v_sub, v_cross, v_dot


def stat(name, m, fn):
    good = tot = 0
    for mat, ts in m.tris.items():
        for a, b, c in ts:
            n = v_cross(v_sub(m.p[b], m.p[a]), v_sub(m.p[c], m.p[a]))
            if v_dot(n, n) < 1e-9:
                continue
            p = [(m.p[a][i] + m.p[b][i] + m.p[c][i]) / 3 for i in range(3)]
            r = fn(mat, p, n)
            if r is None:
                continue
            tot += 1
            good += bool(r)
    print("%-22s %.3f  (%d)" % (name, good / max(tot, 1), tot))


def centroid_out(m):
    c = [sum(p[i] for p in m.p) / len(m.p) for i in range(3)]
    return lambda mat, p, n: v_dot(n, v_sub(p, c)) > 0


def plate(mat, p, n):
    r = math.hypot(p[0], p[1])
    radial = (p[0] / max(r, 1), p[1] / max(r, 1), 0)
    if r < 4999 and abs(p[2]) < 1:
        return n[2] > 0
    if 5050 < r < 6900 and 5 < p[2] < 1300:
        return v_dot(n, radial) < 0
    return None


def can(mat, p, n):
    rad = (0, p[1], p[2] - (820 - 10))
    if mat == "CanPaint":
        return v_dot(n, rad) > 0
    if mat == "CanMetal" and math.hypot(rad[1], rad[2]) < 780 and abs(p[0]) < 1100:
        return v_dot(n, rad) < 0
    return None


stat("platter", g.platter(), plate)
stat("melon up", g.melon_dome(), lambda mat, p, n: n[2] > 0)
stat("can", g.soda_can(), can)
stat("blanket up", g.blanket(), lambda mat, p, n: n[2] > 0)
for name in ("toast_ramp", "cheese_wedge", "strawberry", "cookie"):
    m = getattr(g, name)(4) if name in ("toast_ramp", "cheese_wedge", "strawberry", "cookie") else getattr(g, name)()
    stat(name + " out", m, centroid_out(m))
m = g.grape_bunch(5)
stat("grape out", m, centroid_out(m))
m = g.basket()
stat("basket out", m, centroid_out(m))
m = g.fork()
stat("fork out", m, centroid_out(m))
