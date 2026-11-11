import math
from collections import Counter
import gen_picnic as g
from meshlib import v_sub, v_cross, v_dot


def tris(m, mats=None):
    for mat, ts in m.tris.items():
        if mats and mat not in mats:
            continue
        for a, b, c in ts:
            n = v_cross(v_sub(m.p[b], m.p[a]), v_sub(m.p[c], m.p[a]))
            ln = math.sqrt(v_dot(n, n))
            if ln < 1e-6:
                continue
            p = [(m.p[a][i] + m.p[b][i] + m.p[c][i]) / 3 for i in range(3)]
            yield mat, p, (n[0] / ln, n[1] / ln, n[2] / ln)


def frac(name, vals):
    vals = list(vals)
    print("%-30s %.3f (%d)" % (name, sum(vals) / max(len(vals), 1), len(vals)))


m = g.melon_dome()
frac("melon up", (n[2] > 0 for _, p, n in tris(m)))
print(" melon mats", {k: len(v) for k, v in m.tris.items()})

m = g.melon_slice()
frac("slice top up", (n[2] > 0 for mat, p, n in tris(m) if p[2] > 400 and mat != "MelonSeed" and abs(n[2]) > 0.5))
frac("slice arc out", ((n[0] * p[0] + n[1] * p[1]) > 0 for mat, p, n in tris(m, ["RindDark"]) if abs(n[2]) < 0.3 and p[1] > 30))
frac("slice cut face -y", (n[1] < 0 for mat, p, n in tris(m) if abs(p[1]) < 1 and abs(n[2]) < 0.3))

m = g.wooden_spatula()
frac("spatula top up", (n[2] > 0 for _, p, n in tris(m) if abs(p[1]) < 150 and 800 < p[0] < 13600 and abs(n[2]) > 0.5
                         and p[2] > g.wooden_spatula.__defaults__[3] * 0 + max(q[2] for q in [(0, 0, -1e9)]) and n[2] > -2 and
                         p[2] >= max(z for (x, y, z) in m.p if abs(x - p[0]) < 60 and abs(y) < 150) - 60))
# underside clearance over the plate along the spatula axis (spatula x = r - 3200)
plate = g.platter()
rim = sorted(((p[0], p[2]) for p in plate.p if abs(p[1]) < 1 and p[0] > 0 and p[2] > -5))
worst = (1e9, 0)
for r, z in rim:
    sx = r - 3200
    if sx < 1000 or sx > 14400:
        continue
    low = [q[2] for q in m.p if abs(q[0] - sx) < 60 and abs(q[1]) < 400]
    if low:
        gap = min(low) - z
        if gap < worst[0]:
            worst = (gap, r)
print("min clearance over plate: %.0f cm at r=%.0f" % worst)
xs = sorted(set(round(p[0]) for p in m.p))
steep = 0
prev = None
for x in range(0, 14400, 100):
    top = max(q[2] for q in m.p if abs(q[0] - x) < 50 and abs(q[1]) < 100)
    if prev is not None:
        steep = max(steep, math.degrees(math.atan2(abs(top - prev), 100)))
    prev = top
print("max deck slope %.1f deg" % steep)
