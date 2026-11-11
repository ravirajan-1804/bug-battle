"""Extracts one ground-pose swarm ant (ANTCAR_Swarm_Ant_07) from AntCar_Hybrid_Game.glb as SM_SwarmAnt.obj,
centred on its footprint (origin on the ground under the body), head pointing +X, in Unreal space (cm).
Used by BP_AntSwarmling for the E (Ant Swarm) power."""
import json, math, os, struct, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BugBattle"))
from meshlib import Mesh  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from gen_ant_wheels import SRC, acc, apply, g  # noqa: E402  (re-uses the GLB reader)

OUT = os.path.join(os.path.dirname(__file__), "obj")
SCALE = 100.0
nodes = g["nodes"]
by_name = {n["name"]: i for i, n in enumerate(nodes)}
parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
mats = [m["name"] for m in g["materials"]]


def world_pt(i, p, normal=False):
    """Apply node i and all its ancestors' transforms to p."""
    while i is not None:
        n = nodes[i]
        p = apply(n if not normal else {k: v for k, v in n.items() if k != "translation"}, p, normal)
        i = parent.get(i)
    return p


def collect(i, out):
    if "mesh" in nodes[i]:
        out.append(i)
    for c in nodes[i].get("children", []):
        collect(c, out)


meshes = []
collect(by_name["ANTCAR_Swarm_Ant_07"], meshes)
verts = []  # (gltf world pos, normal, uv, mat, local index)
tris = []
for ni in meshes:
    for prim in g["meshes"][nodes[ni]["mesh"]]["primitives"]:
        P = acc(prim["attributes"]["POSITION"])
        N = acc(prim["attributes"]["NORMAL"])
        UV = acc(prim["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in prim["attributes"] else [(0, 0)] * len(P)
        I = acc(prim["indices"])
        mat = mats[prim.get("material", 0)]
        base = len(verts)
        for p, nrm, uv in zip(P, N, UV):
            verts.append((world_pt(ni, p), world_pt(ni, nrm, True), uv, mat))
        for k in range(0, len(I), 3):
            tris.append((mat, base + I[k], base + I[k + 1], base + I[k + 2]))

# glTF: X left, Y up, Z forward(car).  Find the ant's head direction from its eye material.
cx = sum(v[0][0] for v in verts) / len(verts)
cz = sum(v[0][2] for v in verts) / len(verts)
eyes = [v[0] for v in verts if "EYE" in v[3].upper()]
ex = sum(p[0] for p in eyes) / len(eyes) - cx
ez = sum(p[2] for p in eyes) / len(eyes) - cz
ymin = min(v[0][1] for v in verts)
yaw = math.atan2(ex, ez)  # angle of head direction in the glTF X/Z plane, measured from +Z toward +X
cs, sn = math.cos(-yaw), math.sin(-yaw)


def to_ue(p, normal=False):
    x, y, z = p
    if not normal:
        x, y, z = x - cx, y - ymin, z - cz
    # rotate so the head points along glTF +Z, then glTF(+Z fwd, +X left, +Y up) -> UE(+X fwd, +Y right, +Z up)
    rx = x * cs + z * sn
    rz = -x * sn + z * cs
    s = 1.0 if normal else SCALE
    return (rz * s, -rx * s, y * s)


m = Mesh()
for p, nrm, uv, mat in verts:
    n = to_ue(nrm, True)
    ln = math.sqrt(sum(c * c for c in n)) or 1.0
    m.vert(to_ue(p), (uv[0], uv[1]), tuple(c / ln for c in n))
for mat, a, b, c in tris:
    m.tri(mat, a, b, c)
os.makedirs(OUT, exist_ok=True)
ntri = m.write_obj(os.path.join(OUT, "SM_SwarmAnt.obj"))
xs = [q[0] for q in m.p]; ys = [q[1] for q in m.p]; zs = [q[2] for q in m.p]
print(json.dumps({"tris": ntri, "materials": sorted({t[0] for t in tris}), "head_yaw_deg": round(math.degrees(yaw), 1),
                  "x": [round(min(xs), 1), round(max(xs), 1)], "y": [round(min(ys), 1), round(max(ys), 1)],
                  "z": [round(min(zs), 1), round(max(zs), 1)]}))
