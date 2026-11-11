"""Extracts the four AntCar wheels (tire + rim + brake disc) from AntCar_Hybrid_Game.glb as OBJ files,
each centred on its own wheel pivot and authored in Unreal car space (X forward, Y right, Z up, cm),
so the vehicle can spin them on the physics wheel bones. Also prints wheel centres/radii for setup."""
import json, math, os, struct, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BugBattle"))
from meshlib import Mesh  # noqa: E402

SRC = os.environ.get("ANTCAR_GLB", r"C:\Users\RAGHU RAM\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude"
                     r"\scratch-workspaces\bc25013b-9f37-42a8-bf7c-0f240197bdfc\7df8c18c-a2cf-4535-b978-60cc8c8ce900"
                     r"\scratch-2026-10-03-dc8f14\AntCar_Hybrid_Game.glb")
OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)

raw = open(SRC, "rb").read()
jlen = struct.unpack("<I", raw[12:16])[0]
g = json.loads(raw[20:20 + jlen])
bin_off = 20 + jlen + 8
BIN = raw[bin_off:bin_off + struct.unpack("<I", raw[20 + jlen:24 + jlen])[0]]
CT = {5126: ("f", 4), 5125: ("I", 4), 5123: ("H", 2), 5121: ("B", 1)}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def acc(i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    fmt, size = CT[a["componentType"]]
    n = NC[a["type"]]
    stride = bv.get("byteStride", size * n)
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    out = []
    for k in range(a["count"]):
        vals = struct.unpack_from("<" + fmt * n, BIN, base + k * stride)
        out.append(vals if n > 1 else vals[0])
    return out


def qmat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def apply(n, p, normal=False):
    """Rotation*scale (no translation unless point) of node n applied to p."""
    s = n.get("scale", [1, 1, 1])
    R = qmat(n.get("rotation", [0, 0, 0, 1]))
    v = [p[0] * s[0], p[1] * s[1], p[2] * s[2]] if not normal else [p[0] / s[0], p[1] / s[1], p[2] / s[2]]
    r = [sum(R[i][j] * v[j] for j in range(3)) for i in range(3)]
    if not normal:
        t = n.get("translation", [0, 0, 0])
        r = [r[i] + t[i] for i in range(3)]
    return r


def to_ue(p, scale=100.0):
    """glTF (Y up, +Z forward, +X left) -> Unreal car space (X forward, Y right, Z up)."""
    return (p[2] * scale, -p[0] * scale, p[1] * scale)


nodes = g["nodes"]
by_name = {n["name"]: i for i, n in enumerate(nodes)}
mats = [m["name"] for m in g["materials"]]
report = {}
for tag in ("FL", "FR", "RL", "RR"):
    wi = by_name["ANTCAR_Wheel_" + tag]
    wn = nodes[wi]
    m = Mesh()
    ymin = ymax = 0.0
    radius = 0.0
    for ci in wn.get("children", []):
        cn = nodes[ci]
        if "mesh" not in cn:
            continue
        for prim in g["meshes"][cn["mesh"]]["primitives"]:
            P = acc(prim["attributes"]["POSITION"])
            N = acc(prim["attributes"]["NORMAL"])
            UV = acc(prim["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in prim["attributes"] else [(0, 0)] * len(P)
            I = acc(prim["indices"])
            mat = mats[prim.get("material", 0)]
            base = len(m.p)
            for p, nrm, uv in zip(P, N, UV):
                # child node transform, then wheel node rotation/scale (pivot stays at the wheel centre)
                lp = apply(cn, p)
                wp = apply({k: v for k, v in wn.items() if k != "translation"}, lp)
                wnrm = apply({k: v for k, v in wn.items() if k != "translation"}, apply(cn, nrm, True), True)
                up = to_ue(wp)
                ln = math.sqrt(sum(c * c for c in wnrm)) or 1.0
                m.vert(up, (uv[0], uv[1]), to_ue([c / ln for c in wnrm], 1.0))
                radius = max(radius, math.hypot(up[0], up[2]))
            for k in range(0, len(I), 3):
                m.tri(mat, base + I[k], base + I[k + 1], base + I[k + 2])
    ntri = m.write_obj(os.path.join(OUT, "SM_AntWheel_%s.obj" % tag))
    t = wn.get("translation", [0, 0, 0])
    report[tag] = {"tris": ntri, "centre_ue_cm": [round(c, 1) for c in to_ue(t)], "radius_cm": round(radius, 1),
                   "y_range": [round(min(q[1] for q in m.p), 1), round(max(q[1] for q in m.p), 1)]}
print(json.dumps(report, indent=1))
