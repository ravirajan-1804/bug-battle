"""Bee accessories for the sports-car kart."""
import os, math
from meshlib import Mesh, tube_along, ellipsoid
OUT = os.path.join(os.path.dirname(__file__), "obj")

def stinger():
    m = Mesh()
    prof = [(0, 22), (-12, 20), (-30, 13), (-55, 6), (-80, 2.2), (-96, 0.4)]
    pts = [(x, 0.0, -abs(x) * 0.05) for x, _ in prof]
    tube_along(m, "Black", pts, [r for _, r in prof], segs=16)
    ellipsoid(m, "Black", (2, 0, 0), (12, 26, 26), 20, 12)   # mounting collar
    return m

print(stinger().write_obj(os.path.join(OUT, "SM_BeeStinger.obj")))
