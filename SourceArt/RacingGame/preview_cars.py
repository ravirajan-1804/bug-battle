"""Offline 3/4-view preview of the generated car OBJs (numpy z-buffer, flat shaded) -> cars_preview.png"""
import math, os, sys
import numpy as np
from pngplot import Canvas

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
from gen_bugcars import WXF, WXR, WY, WZ  # noqa: E402

COL = {"Paint": (230, 120, 40), "Trim": (40, 40, 48), "Accent": (240, 220, 60), "EyeWhite": (250, 250, 250),
       "EyePupil": (15, 15, 20), "EyeRed": (220, 20, 20), "Shell": (240, 120, 60), "ShellStripe": (255, 220, 120),
       "Wing": (210, 235, 255), "Sting": (255, 80, 200), "Tyre": (35, 35, 38), "Rim": (230, 230, 230), "Hub": (220, 60, 60)}
CAR_PAINT = {"Snail": {"Paint": (70, 200, 170), "Accent": (255, 120, 150)}, "Beetle": {"Paint": (30, 170, 110), "Accent": (60, 120, 230)},
             "Bee": {"Paint": (255, 200, 20)}, "Spider": {"Paint": (110, 50, 170), "Accent": (230, 30, 60)},
             "Scorpion": {"Paint": (235, 140, 40), "Accent": (180, 80, 30)}, "Ant": {"Paint": (215, 40, 30), "Accent": (255, 210, 40)},
             "Butterfly": {"Paint": (240, 60, 170), "Accent": (40, 200, 230), "Trim": (40, 40, 90)}}


def load(path):
    V, F = [], []
    mat = None
    for line in open(path):
        if line.startswith("v "):
            x, y, z = map(float, line.split()[1:4])
            V.append((x, -y, z))
        elif line.startswith("usemtl"):
            mat = line.split()[1]
        elif line.startswith("f "):
            F.append(([int(t.split("/")[0]) - 1 for t in line.split()[1:4]], mat))
    return np.array(V), F


def wheel_instances(V, F):
    out = []
    for (x, s) in ((WXF, 1), (WXF, -1), (WXR, 1), (WXR, -1)):
        W = V.copy()
        W[:, 1] *= s
        W += np.array([x, s * WY, WZ]) - np.array([0, 0, 0])
        out.append((W, F))
    return out


def render(parts, palette, W=420, H=300, yaw=-35, pitch=18):
    zb = np.full((H, W), 1e9)
    img = np.full((H, W, 3), 245, dtype=np.uint8)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    L = np.array([0.4, -0.5, 0.75]); L /= np.linalg.norm(L)
    sc = W / 720.0
    for V, F in parts:
        # rotate around Z (yaw) then tilt (pitch); camera looks along +X' after rotation
        x = V[:, 0] * cy - V[:, 1] * sy
        y = V[:, 0] * sy + V[:, 1] * cy
        z = V[:, 2]
        d = x * cp + z * sp
        zz = -x * sp + z * cp
        sx = W / 2 + y * sc
        syy = H * 0.7 - zz * sc
        for (ids, mat) in F:
            a, b, c = ids
            n = np.cross(V[b] - V[a], V[c] - V[a])
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                continue
            n /= ln
            shade = 0.35 + 0.65 * max(0.0, abs(float(n @ L)))
            col = np.array(palette.get(mat, COL.get(mat, (255, 0, 255)))) * shade
            xs = np.array([sx[a], sx[b], sx[c]]); ys = np.array([syy[a], syy[b], syy[c]]); ds = np.array([d[a], d[b], d[c]])
            x0, x1 = int(max(0, xs.min())), int(min(W - 1, xs.max()) + 1)
            y0, y1 = int(max(0, ys.min())), int(min(H - 1, ys.max()) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9:
                continue
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
            w2 = 1 - w0 - w1
            ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not ins.any():
                continue
            depth = -(w0 * ds[0] + w1 * ds[1] + w2 * ds[2])
            sub = zb[y0:y1, x0:x1]
            upd = ins & (depth < sub)
            sub[upd] = depth[upd]
            img[y0:y1, x0:x1][upd] = col.astype(np.uint8)
    return img


def main():
    names = ["Snail", "Beetle", "Bee", "Spider", "Scorpion", "Ant", "Butterfly"]
    tiles = []
    for nm in names:
        V, F = load(os.path.join(HERE, "obj_cars", "SM_RGC_%s_Body.obj" % nm))
        WV, WF = load(os.path.join(HERE, "obj_cars", "SM_RGC_%s_Wheel.obj" % nm))
        parts = [(V, F)] + wheel_instances(WV, WF)
        tiles.append(render(parts, CAR_PAINT[nm]))
    H, W = tiles[0].shape[:2]
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    cv = Canvas(W * cols, H * rows)
    big = np.full((H * rows, W * cols, 3), 245, dtype=np.uint8)
    for k, t in enumerate(tiles):
        r, c = divmod(k, cols)
        big[r * H:(r + 1) * H, c * W:(c + 1) * W] = t
    cv.px = bytearray(big.tobytes())
    cv.save(os.path.join(HERE, "cars_preview.png"))
    print("ok")


if __name__ == "__main__":
    main()
