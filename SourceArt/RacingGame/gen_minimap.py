"""Minimap data for WBP_RG_Minimap (Lvl_GardenGrandPrix).

Projects the real track centreline (trackdef.Track) top-down into a MAP_W x MAP_H
map space (X east -> right, Y south -> down) and writes minimap.json with the
polyline, the start/finish line and the world->map transform the widget uses.
"""
import json, math, os
import numpy as np
from trackdef import Track, L, HALF_W

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_W, MAP_H, PAD = 300.0, 220.0, 14.0   # widget design size (slate units)
STRIDE = 6                               # centreline samples are 100 cm apart

T = Track()
xy = np.asarray(T.xy)
I_START = T.index_at(*L(40, 67))
lo, hi = xy.min(0) - HALF_W, xy.max(0) + HALF_W
scale = min((MAP_W - 2 * PAD) / (hi - lo)[0], (MAP_H - 2 * PAD) / (hi - lo)[1])
off = np.array([MAP_W, MAP_H]) / 2 - (lo + hi) / 2 * scale     # map = world * scale + off


def to_map(p):
    return (np.asarray(p) * scale + off).round(2).tolist()


# run two samples past the start so the antialiased line has no cap seam where the loop closes
pts = [to_map(xy[i]) for i in range(0, len(xy), STRIDE)] + [to_map(xy[0]), to_map(xy[STRIDE])]
h = T.heading[I_START]
f = np.array([math.cos(h), math.sin(h)])
r = np.array([-f[1], f[0]])
c = xy[I_START]
out = dict(scale=float(scale), offset=off.round(3).tolist(), points=pts,
           start=to_map(c), start_l=to_map(c - r * HALF_W * 1.5), start_r=to_map(c + r * HALF_W * 1.5),
           start_dir=f.round(4).tolist(), road_px=float(2 * HALF_W * scale), n=len(pts))
json.dump(out, open(os.path.join(HERE, "minimap.json"), "w"), indent=1)
print({k: v for k, v in out.items() if k != "points"})
