"""Converts the downloaded Poly Haven glTF scans (CC0) into OBJ files Unreal's importer accepts, and prepares
their textures (OpenGL normal maps -> DirectX by flipping green).

Each glTF mesh becomes its own OBJ: Unreal space (X fwd, Y right, Z up, cm at real-world size), pivot at the centre
of the base. Writes scans_manifest.json describing every mesh (size, triangle count, material, texture files).

    python scan2obj.py            # converts everything under Saved/ClaudeScripts/dl/models
"""
import json, os, struct, sys
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved", "ClaudeScripts", "dl"))
SRC = os.path.join(ROOT, "models")
OUT = os.path.join(ROOT, "obj")
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
COMBINE = {"Lantern_01", "wooden_bucket_01"}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def accessor(g, bufs, idx):
    a = g["accessors"][idx]
    bv = g["bufferViews"][a["bufferView"]]
    dt = np.dtype(CT[a["componentType"]])
    n = NC[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0)
    buf = bufs[bv["buffer"]]
    if stride and stride != dt.itemsize * n:
        raw = np.frombuffer(buf, dtype=np.uint8, count=stride * (a["count"] - 1) + dt.itemsize * n, offset=off)
        idxs = (np.arange(a["count"])[:, None] * stride + np.arange(dt.itemsize * n)[None, :]).ravel()
        arr = np.frombuffer(raw[idxs].tobytes(), dtype=dt)
    else:
        arr = np.frombuffer(buf, dtype=dt, count=a["count"] * n, offset=off)
    arr = arr.reshape(a["count"], n).astype(np.float64 if dt == np.float32 else np.int64)
    if a.get("normalized") and dt != np.float32:
        arr = arr / float(np.iinfo(dt).max)
    return arr


def node_matrix(nd):
    if "matrix" in nd:
        return np.array(nd["matrix"], dtype=np.float64).reshape(4, 4).T
    t = np.array(nd.get("translation", [0, 0, 0]), dtype=np.float64)
    x, y, z, w = nd.get("rotation", [0, 0, 0, 1])
    s = np.array(nd.get("scale", [1, 1, 1]), dtype=np.float64)
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s[None, :]
    m[:3, 3] = t
    return m


def world_matrices(g):
    out = {}

    def walk(i, parent):
        m = parent @ node_matrix(g["nodes"][i])
        out[i] = m
        for c in g["nodes"][i].get("children", []):
            walk(c, m)

    scene = g["scenes"][g.get("scene", 0)]
    for r in scene["nodes"]:
        walk(r, np.eye(4))
    return out


def to_ue(p):
    """glTF (x right, y up, z front, metres) -> Unreal (cm): swap y/z (handedness change, not a mirror)."""
    return np.stack([p[:, 0], p[:, 2], p[:, 1]], axis=1)


def write_obj(path, pos, nrm, uv, tris_by_mat):
    """Same conventions as meshlib.Mesh.write_obj: Y negated, V flipped, winding reversed."""
    lines = ["# converted by scan2obj.py from a Poly Haven CC0 scan"]
    lines += ["v %.4f %.4f %.4f" % (x, -y, z) for x, y, z in pos]
    lines += ["vt %.5f %.5f" % (u, 1.0 - v) for u, v in uv]
    lines += ["vn %.5f %.5f %.5f" % (x, -y, z) for x, y, z in nrm]
    ntri = 0
    for mat, tris in tris_by_mat.items():
        lines.append("usemtl %s" % mat)
        lines.append("g %s" % mat)
        pa, pb, pc = pos[tris[:, 0]], pos[tris[:, 1]], pos[tris[:, 2]]
        gn = np.cross(pb - pa, pc - pa)
        want = nrm[tris[:, 0]] + nrm[tris[:, 1]] + nrm[tris[:, 2]]
        flip = (gn * want).sum(axis=1) < 0
        t = tris.copy()
        t[flip, 1], t[flip, 2] = tris[flip, 2], tris[flip, 1]
        t = t + 1
        lines += ["f %d/%d/%d %d/%d/%d %d/%d/%d" % (a, a, a, c, c, c, b, b, b) for a, b, c in t]
        ntri += len(t)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return ntri


def convert(name):
    folder = os.path.join(SRC, name)
    g = json.load(open(os.path.join(folder, name + ".gltf"), encoding="utf-8"))
    bufs = [open(os.path.join(folder, b["uri"]), "rb").read() for b in g["buffers"]]
    wm = world_matrices(g)
    mats = g.get("materials", [])
    entries = []
    parts = []
    mesh_nodes = [(i, nd) for i, nd in enumerate(g["nodes"]) if "mesh" in nd and i in wm]
    for k, (ni, nd) in enumerate(mesh_nodes):
        mesh = g["meshes"][nd["mesh"]]
        P, N, UV, T = [], [], [], {}
        base = 0
        m4 = wm[ni]
        nm3 = np.linalg.inv(m4[:3, :3]).T
        for prim in mesh["primitives"]:
            at = prim["attributes"]
            p = accessor(g, bufs, at["POSITION"])
            p = (m4[:3, :3] @ p.T).T + m4[:3, 3]
            n = accessor(g, bufs, at["NORMAL"]) if "NORMAL" in at else np.tile([0.0, 1.0, 0.0], (len(p), 1))
            n = (nm3 @ n.T).T
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
            uv = accessor(g, bufs, at["TEXCOORD_0"]) if "TEXCOORD_0" in at else np.zeros((len(p), 2))
            idx = accessor(g, bufs, prim["indices"]).astype(np.int64).reshape(-1, 3) if "indices" in prim else np.arange(len(p)).reshape(-1, 3)
            mname = mats[prim["material"]]["name"] if "material" in prim else name
            P.append(to_ue(p) * 100.0); N.append(to_ue(n)); UV.append(uv)
            T.setdefault(mname, []).append(idx + base)
            base += len(p)
        P = np.concatenate(P); N = np.concatenate(N); UV = np.concatenate(UV)
        T = {m: np.concatenate(v) for m, v in T.items()}
        parts.append((P, N, UV, T))
    if name in COMBINE and len(parts) > 1:      # multi-part props stay one mesh so the parts keep their relative placement
        off = 0; Pc, Nc, UVc, Tc = [], [], [], {}
        for P, N, UV, T in parts:
            Pc.append(P); Nc.append(N); UVc.append(UV)
            for m, v in T.items():
                Tc.setdefault(m, []).append(v + off)
            off += len(P)
        parts = [(np.concatenate(Pc), np.concatenate(Nc), np.concatenate(UVc), {m: np.concatenate(v) for m, v in Tc.items()})]
    for k, (P, N, UV, T) in enumerate(parts):
        mn, mx = P.min(axis=0), P.max(axis=0)
        P = P - np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])
        oname = name if len(parts) == 1 else "%s_%d" % (name, k)
        ntri = write_obj(os.path.join(OUT, oname + ".obj"), P, N, UV, T)
        entries.append({"obj": oname, "src": name, "size": [round(float(v), 2) for v in (mx - mn)], "tris": ntri,
                        "mats": list(T.keys())})
    # materials -> texture files
    tex = {}
    imgs = g.get("images", [])
    txs = g.get("textures", [])

    def img(ti):
        return imgs[txs[ti["index"]]["source"]]["uri"] if ti else None

    for m in mats:
        pbr = m.get("pbrMetallicRoughness", {})
        tex[m["name"]] = {"diff": img(pbr.get("baseColorTexture")), "arm": img(pbr.get("metallicRoughnessTexture")),
                          "nor": img(m.get("normalTexture")), "alpha": m.get("alphaMode", "OPAQUE")}
        nor = tex[m["name"]]["nor"]
        if nor:
            dst = os.path.join(folder, nor.replace("nor_gl", "nor_dx"))
            if not os.path.exists(dst):
                im = np.array(Image.open(os.path.join(folder, nor)).convert("RGB"))
                im[:, :, 1] = 255 - im[:, :, 1]
                Image.fromarray(im).save(dst, quality=95)
            tex[m["name"]]["nor"] = nor.replace("nor_gl", "nor_dx")
    return entries, tex


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
    manifest = {"meshes": [], "materials": {}}
    partial = bool(sys.argv[1:])
    for nm in names:
        e, t = convert(nm)
        manifest["meshes"] += e
        for k, v in t.items():
            manifest["materials"][k] = dict(v, src=nm)
        print(nm, [(x["obj"], x["size"], x["tris"]) for x in e])
    json.dump(manifest, open(os.path.join(ROOT, "scans_manifest_partial.json" if partial else "scans_manifest.json"), "w"), indent=1)
