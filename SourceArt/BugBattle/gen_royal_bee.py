"""Generates SM_RoyalBee: a tiny low-poly golden bee for the Royal Bee Swarm ability.

Facing +X, ~24 cm long. Material slots:
  Gold   - thorax, head and abdomen
  Stripe - two dark bands around the abdomen
  Wing   - two wing sheets; M_RoyalBeeWing flaps them with WPO (|local Y| drives the swing)
"""
import math, os
from meshlib import Mesh, ellipsoid, lathe_x

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)


def wing(m, side):
    """Flat teardrop wing in the XY plane, root near the thorax top, span along side*Y."""
    span, chord = 15.0, 7.0

    def fn(u, v):
        s = v
        half = chord * 0.5 * math.sin(math.pi * min(s * 0.95 + 0.05, 1.0)) ** 0.8
        x = 1.5 - 4.0 * s + (u - 0.5) * 2.0 * half
        y = side * (1.5 + span * s)
        z = 6.5 + 1.2 * s
        return (x, y, z)
    m.grid("Wing", 4, 6, fn, uv_fn=lambda u, v: (u, v), flip=(side < 0))
    # back face so the wing is visible from below without a two-sided material
    m.grid("Wing", 4, 6, fn, uv_fn=lambda u, v: (u, v), flip=(side > 0))


def royal_bee():
    m = Mesh()
    ellipsoid(m, "Gold", (3.0, 0, 1.0), (5.0, 4.4, 4.4), 14, 10)          # thorax
    ellipsoid(m, "Gold", (9.0, 0, 1.5), (3.2, 3.4, 3.2), 12, 8)           # head
    ellipsoid(m, "Gold", (-6.5, 0, 0.0), (8.5, 5.6, 5.4), 16, 10)         # abdomen
    for cx in (-4.5, -9.0):                                              # stripes
        lathe_x(m, "Stripe", [(cx - 1.4, 5.0), (cx, 5.9), (cx + 1.4, 5.0)], segs=16)
    wing(m, 1)
    wing(m, -1)
    return m


if __name__ == "__main__":
    n = royal_bee().write_obj(os.path.join(OUT, "SM_RoyalBee.obj"))
    print("SM_RoyalBee", n, "tris")
