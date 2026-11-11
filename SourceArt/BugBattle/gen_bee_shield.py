"""Honey Shield dome: a Goldberg-style honeycomb shell (hexagon cells + 12 pentagons) on a unit sphere (r 100).

Each cell is a shallow honey "cup" (centre dips to r 98.5) ringed by a raised wax wall (cell boundary at r 103),
so neighbouring cells share one rounded wax ridge like a real comb.
  UV.x = 0 at the cell centre .. 1 at the wax ridge          (material: panel vs wall)
  UV.y = build-order key 0..1 (bottom cells first + jitter)  (material: cells pop in from the ground up)
Cells whose centre is below z = -45 are dropped so the dome sits on the ground.
Output: obj/SM_BeeHexShield.obj (slot Shield)
"""
import math, os
from meshlib import Mesh, v_add, v_sub, v_mul, v_norm, v_dot

OUT = os.path.join(os.path.dirname(__file__), "obj")
FREQ = 7
CUT = -0.45


def icosa():
    t = (1 + 5 ** 0.5) / 2
    vs = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
          (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    fs = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
          (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
          (8, 6, 7), (9, 8, 1)]
    return [v_norm(v) for v in vs], fs


def geodesic(n):
    vs, fs = icosa()
    verts, key, tris = [], {}, []

    def vid(p):
        k = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        if k not in key:
            key[k] = len(verts)
            verts.append(p)
        return key[k]

    for a, b, c in fs:
        A, B, C = vs[a], vs[b], vs[c]
        grid = {}
        for i in range(n + 1):
            for j in range(n + 1 - i):
                k = n - i - j
                p = v_norm(v_add(v_add(v_mul(A, k / n), v_mul(B, i / n)), v_mul(C, j / n)))
                grid[(i, j)] = vid(p)
        for i in range(n):
            for j in range(n - i):
                tris.append((grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]))
                if i + j < n - 1:
                    tris.append((grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]))
    return verts, tris


def hash01(x):
    s = math.sin(x * 12.9898 + 78.233) * 43758.5453
    return s - math.floor(s)


def build():
    verts, tris = geodesic(FREQ)
    cent = [v_norm(v_add(v_add(verts[a], verts[b]), verts[c])) for a, b, c in tris]
    around = {}
    for ti, t in enumerate(tris):
        for v in t:
            around.setdefault(v, []).append(ti)
    m = Mesh()
    R = 100.0
    cells = 0
    for vi, c in enumerate(verts):
        if c[2] < CUT:
            continue
        # order the surrounding triangle centroids around the cell normal
        ref = v_norm(v_sub(cent[around[vi][0]], v_mul(c, v_dot(cent[around[vi][0]], c))))
        side = v_norm((c[1] * ref[2] - c[2] * ref[1], c[2] * ref[0] - c[0] * ref[2], c[0] * ref[1] - c[1] * ref[0]))
        ring = sorted(around[vi], key=lambda ti: math.atan2(v_dot(cent[ti], side), v_dot(cent[ti], ref)))
        corners = [cent[ti] for ti in ring]
        k = 0.75 * (c[2] - CUT) / (1 - CUT) + 0.25 * hash01(vi * 1.37)
        mid = m.vert(v_mul(c, R * 0.985), (0.0, k), c)
        inner, outer = [], []
        for p in corners:
            q = v_norm(v_add(c, v_mul(v_sub(p, c), 0.80)))
            inner.append(m.vert(v_mul(q, R * 0.99), (0.80, k), None))
            outer.append(m.vert(v_mul(p, R * 1.03), (1.0, k), p))
        n = len(corners)
        for i in range(n):
            j = (i + 1) % n
            m.tri("Shield", mid, inner[i], inner[j])
            m.quad("Shield", inner[i], outer[i], outer[j], inner[j])
        cells += 1
    return m, cells


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    mesh, cells = build()
    n = mesh.write_obj(os.path.join(OUT, "SM_BeeHexShield.obj"))
    print("SM_BeeHexShield", cells, "cells", n, "tris")
