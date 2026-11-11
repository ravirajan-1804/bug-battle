"""Exports the Spider Car power animation from the user's SpiderCar_Abilities.blend to Unreal.

Nothing is re-modelled: every mesh is the evaluated geometry of the objects in the .blend, and every animation
curve is the .blend's own keyframes sampled once per frame (24 fps). Explosions (FX_Explosion_*, the venom blast
radius, the exploding enemy parts), enemy cars, the arena, cameras and the UI overlays are not exported.

Usage:
  E:/blender.exe -b SpiderCar_Abilities.blend --python export_spidercar_abilities.py -- <out_dir>

Writes into <out_dir>:
  fbx/SM_SpiderCar_*.fbx          one static mesh per power asset (FBX so the extra UV channels survive)
  SpiderCar_Abilities_Curves.csv  CurveTable source, rows = sampled channels, columns = seconds from the row start
  SpiderCar_Abilities_Export.json pivots, sizes, spark/puff parameters and the material values

Coordinates: Blender scene is +X forward, +Y left, metres. The FBX importer maps (x, y, z) -> UE (x, -y, z) cm,
so meshes are written in their Blender local space unchanged.

Extra mesh data (read by the M_SpiderCar_* materials):
  UV0.x  strand growth parameter = arc-length fraction along the strand (bevel_factor_end mapping 'SPLINE')
  UV1.xy / UV2.x  spark direction (UE space) for the spark bursts
"""
import bpy, bmesh, sys, os, json, math
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

OUT = sys.argv[sys.argv.index("--") + 1]
FBX = os.path.join(OUT, "fbx")
os.makedirs(FBX, exist_ok=True)
scene = bpy.context.scene
FPS = scene.render.fps
D = bpy.data.objects
SP = D["SPIDERCAR_Root"]

# frames from spidercar_abilities.py (the timeline the .blend was built with)
F_FIRE, F_HIT, F_FREE = 130, 141, 236
F_BITE, F_JAM = 325, 380
F_STORM, F_REL = 502, 640
F_WRAP, F_BREAK = 688, 830
D1, H1 = 875, 890


def ue(v):
    return [round(v.x * 100, 3), round(-v.y * 100, 3), round(v.z * 100, 3)]


# ---------------------------------------------------------------- 1. curves (sampled before anything is touched)
rows = {}


def sample(name, fn, f0, f1):
    vals = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        vals.append(float(fn()))
    rows[name] = vals


def fade(o):
    return lambda: o.get("fade", 1.0) if not o.hide_render else 0.0


def sx(o, i=0):
    return lambda: o.scale[i]


# Web Shot
mf = D["FX_WebShot_Muzzle_Flash"]
sample("Shot_Flash_Scale", sx(mf), F_FIRE - 2, F_FIRE + 6)
sample("Shot_Flash_Fade", fade(mf), F_FIRE - 2, F_FIRE + 6)
te = D["WEB_Shot_Tether"]
sample("Shot_Tether_FadeOut", lambda: te.get("fade", 1.0), F_HIT, F_HIT + 8)
tr = D["WEB_Trap_Net_WebShot"]
trs = D["WEB_Trap_Net_WebShot_Strands"]
sample("Trap_Scale_In", sx(tr), F_HIT, F_HIT + 9)
sample("Trap_Grow_In", lambda: trs.data.bevel_factor_end, F_HIT, F_HIT + 9)
sample("Trap_Fade_In", lambda: tr.get("fade", 1.0), F_HIT, F_HIT + 9)
sample("Trap_Fade_Out", lambda: tr.get("fade", 1.0), F_FREE, F_FREE + 12)
# Venom Bite
fl, fr = D["SPIDERCAR_Venom_Fang_L"], D["SPIDERCAR_Venom_Fang_R"]
for k, ax in enumerate("XYZ"):
    sample("Fang_L_Rot" + ax, (lambda k=k: fl.rotation_euler[k]), F_BITE - 15, F_BITE + 10)
    sample("Fang_R_Rot" + ax, (lambda k=k: fr.rotation_euler[k]), F_BITE - 15, F_BITE + 10)
vf, dr = D["FX_Venom_Bite_Flash"], D["FX_Venom_Droplets"]
sample("Venom_Flash_Scale", sx(vf), F_BITE, F_BITE + 10)
sample("Venom_Flash_Fade", lambda: vf.get("fade", 1.0), F_BITE, F_BITE + 10)
scene.frame_set(F_BITE)
bite_pt = vf.location.copy()
sample("Venom_Drops_DX", lambda: dr.location.x - bite_pt.x, F_BITE, F_BITE + 14)
sample("Venom_Drops_DZ", lambda: dr.location.z - bite_pt.z, F_BITE, F_BITE + 14)
sample("Venom_Drops_SXY", sx(dr), F_BITE, F_BITE + 14)
sample("Venom_Drops_SZ", sx(dr, 2), F_BITE, F_BITE + 14)
sample("Venom_Drops_Fade", lambda: dr.get("fade", 1.0), F_BITE, F_BITE + 14)
body2 = next(o for o in D if o.name.startswith("ENEMY_Venom_Target") and "venom" in o.keys())
sample("Venom_Veins", lambda: body2["venom"], F_BITE, F_JAM)
# engine-jam smoke puffs: world-space puffs, stored relative to the venom target car at their start frame
E2 = D["ENEMY_Venom_Target"]
PUFFS = []
for k in range(8):
    p = D.get("FX_Engine_Jam_Smoke_%d" % k)
    if not p:
        break
    f0 = F_JAM + 5 * k
    scene.frame_set(f0)
    base = E2.location.copy()
    a, s0 = p.location.copy(), p.scale.x
    scene.frame_set(f0 + 28)
    b, s1 = p.location.copy(), p.scale.x
    PUFFS.append(dict(t0=(f0 - F_BITE) / FPS, start=ue(a - base), end=ue(b - base), s0=s0, s1=s1, dur=28 / FPS))
sample("Venom_Puff_Fade", lambda: D["FX_Engine_Jam_Smoke_0"].get("fade", 1.0), F_JAM, F_JAM + 28)
JAM_SPARKS = []
for j in range(4):
    g = D.get("FX_Engine_Jam_Sparks_%d" % (2 * j))
    if g:
        f0 = F_JAM + 10 * j
        scene.frame_set(f0)
        JAM_SPARKS.append(dict(t0=(f0 - F_BITE) / FPS, at=ue(g.location - E2.location)))
# Web Storm
st = D["WEB_Storm_Field_Anim"]
sample("Storm_Scale_In", sx(st), F_STORM, F_STORM + 14)
sample("Storm_Fade_In", lambda: st.get("fade", 1.0), F_STORM, F_STORM + 14)
sample("Storm_Fade_Out", lambda: st.get("fade", 1.0), F_REL, F_REL + 14)
sf = D["FX_Storm_Spinneret_Flash"]
sample("Storm_Flash_Scale", sx(sf), F_STORM - 4, F_STORM + 8)
sample("Storm_Flash_Fade", fade(sf), F_STORM - 4, F_STORM + 8)
ew = D["WEB_Entangle_Wrap_0"]
FS0 = 538 + 16
sample("Entangle_Grow_In", lambda: ew.data.bevel_factor_end, FS0, FS0 + 6)
sample("Entangle_Fade_Out", lambda: ew.get("fade", 1.0), F_REL, F_REL + 12)
# Web Cocoon
co, cos_ = D["WEB_Cocoon_Shield_Anim"], D["WEB_Cocoon_Shield_Anim_Strands"]
cof = D["WEB_Cocoon_Shield_Anim_Film"]
sample("Cocoon_Grow_In", lambda: cos_.data.bevel_factor_end, F_WRAP, F_WRAP + 24)
sample("Cocoon_Film_In", lambda: cof.get("fade", 1.0), F_WRAP, F_WRAP + 24)
sample("Cocoon_Fade_Out", lambda: co.get("fade", 1.0), F_BREAK, F_BREAK + 10)
sample("Cocoon_Film_Out", lambda: cof.get("fade", 1.0), F_BREAK, F_BREAK + 10)
sample("Cocoon_ScaleXY_Out", sx(co), F_BREAK, F_BREAK + 10)
sample("Cocoon_ScaleZ_Out", sx(co, 2), F_BREAK, F_BREAK + 10)
fg = D["FX_Cocoon_Break_Fragments"]
sample("Cocoon_Frag_ScaleXY", sx(fg), F_BREAK, F_BREAK + 16)
sample("Cocoon_Frag_ScaleZ", sx(fg, 2), F_BREAK, F_BREAK + 16)
sample("Cocoon_Frag_Fade", lambda: fg.get("fade", 1.0), F_BREAK, F_BREAK + 16)
cf = D["FX_Cocoon_Spin_Flash"]
sample("Cocoon_Flash_Scale", sx(cf), F_WRAP - 3, F_WRAP + 10)
sample("Cocoon_Flash_Fade", fade(cf), F_WRAP - 3, F_WRAP + 10)
# Dash
sk = D["FX_Dash_Speed_Streaks"]
sample("Dash_Streak_In", lambda: sk.get("fade", 1.0), D1, D1 + 3)
sample("Dash_Streak_Out", lambda: sk.get("fade", 1.0), H1 + 5, H1 + 8)

# CurveTable CSV: one shared time grid, short rows hold their last value
n = max(len(v) for v in rows.values())
with open(os.path.join(OUT, "SpiderCar_Abilities_Curves.csv"), "w") as fh:
    fh.write("Name," + ",".join("%.5f" % (i / FPS) for i in range(n)) + "\n")
    for k, v in rows.items():
        v = v + [v[-1]] * (n - len(v))
        fh.write(k + "," + ",".join("%.5f" % x for x in v) + "\n")

# ---------------------------------------------------------------- 2. static, non-animated poses for the meshes
for o in D:
    if o.animation_data:
        o.animation_data_clear()
    if o.data is not None and getattr(o.data, "animation_data", None):
        o.data.animation_data_clear()
    if o.type == 'CURVE':
        o.data.bevel_factor_end = 1.0
        o.data.bevel_factor_start = 0.0
    o.hide_render = o.hide_viewport = False
for o in (fl, fr):
    o.rotation_euler = (0, 0, 0)
scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()


def strand_tree(o):
    """KD tree of points along every spline of a curve object, each tagged with its arc-length fraction."""
    pts, tags = [], []
    for sp in o.data.splines:
        P = [Vector(p.co[:3]) for p in sp.points] if sp.type == 'POLY' else [b.co.copy() for b in sp.bezier_points]
        if len(P) < 2:
            continue
        L = [0.0]
        for a, b in zip(P, P[1:]):
            L.append(L[-1] + (b - a).length)
        tot = max(L[-1], 1e-6)
        for i, (a, b) in enumerate(zip(P, P[1:])):
            seg = (b - a).length
            m = max(1, int(seg / 0.004))
            for j in range(m + 1):
                pts.append(a.lerp(b, j / m))
                tags.append((L[i] + seg * j / m) / tot)
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    return kd, tags


def add_object(bm, uv_g, o, M, mats, mat_index, spark_dir=None):
    """Append the evaluated mesh of `o` to `bm`, transformed by M (from o's object space)."""
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    kd = strand_tree(o) if o.type == 'CURVE' else None
    slots = [s.material for s in ev.material_slots] or [None]
    vmap = []
    for v in me.vertices:
        nv = bm.verts.new(M @ v.co)
        vmap.append(nv)
    bm.verts.ensure_lookup_table()
    grow = None
    if kd:
        grow = [kd[1][kd[0].find(v.co)[1]] for v in me.vertices]
    uv1 = bm.loops.layers.uv["DirXY"]
    uv2 = bm.loops.layers.uv["DirZ"]
    for p in me.polygons:
        try:
            f = bm.faces.new([vmap[i] for i in p.vertices])
        except ValueError:
            continue
        m = slots[min(p.material_index, len(slots) - 1)]
        f.material_index = mat_index[m.name if m else "Default"]
        f.smooth = p.use_smooth
        for loop, vi in zip(f.loops, p.vertices):
            loop[uv_g].uv = (grow[vi] if grow else 0.0, 0.0)
            if spark_dir is not None:
                loop[uv1].uv = (spark_dir[0], spark_dir[1])
                loop[uv2].uv = (spark_dir[2], 0.0)
    ev.to_mesh_clear()


def build(name, parts, sparks=None):
    """parts: list of (object, matrix from object space to the asset's space)."""
    bm = bmesh.new()
    uv_g = bm.loops.layers.uv.new("Grow")
    bm.loops.layers.uv.new("DirXY")
    bm.loops.layers.uv.new("DirZ")
    mats, mat_index = [], {}
    for o, M in parts:
        for s in o.material_slots:
            nm = s.material.name if s.material else "Default"
            if nm not in mat_index:
                mat_index[nm] = len(mats)
                mats.append(s.material)
    for o, M in parts:
        d = None
        if sparks:
            dv = o.matrix_basis.to_3x3() @ Vector((1, 0, 0))
            dv.normalize()
            d = (dv.x, -dv.y, dv.z)
        add_object(bm, uv_g, o, M, mats, mat_index, d)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(FBX, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=False, apply_scale_options='FBX_SCALE_NONE',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=False,
                             add_leaf_bones=False, bake_anim=False, use_custom_props=False)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    ys = [v.co.y for v in me.vertices]
    print("WROTE", name, tris, "tris", [m.name for m in mats], "y %.2f..%.2f" % (min(ys), max(ys)))
    bpy.data.objects.remove(ob, do_unlink=True)
    return [m.name for m in mats]


def under_root(root):
    inv = root.matrix_world.inverted()
    return [(o, inv @ o.matrix_world) for o in root.children if o.type in {'MESH', 'CURVE'}]


def own(o):
    return [(o, Matrix.Identity(4))]


EXPORTS = {}
EXPORTS["SM_SpiderCar_WebShot_Projectile"] = build("SM_SpiderCar_WebShot_Projectile", under_root(D["WEB_Shot_Projectile_Anim"]))
EXPORTS["SM_SpiderCar_WebShot_MuzzleFlash"] = build("SM_SpiderCar_WebShot_MuzzleFlash", own(mf))
# tether: cylinder along local +Y in the .blend; written along +X so it can be aimed with MakeRotFromX
EXPORTS["SM_SpiderCar_WebShot_Tether"] = build("SM_SpiderCar_WebShot_Tether", [(te, Matrix.Rotation(-math.pi / 2, 4, 'Z'))])
EXPORTS["SM_SpiderCar_WebTrap"] = build("SM_SpiderCar_WebTrap", under_root(tr))
EXPORTS["SM_SpiderCar_WebGround"] = build("SM_SpiderCar_WebGround", under_root(D["WEB_Storm_Patch_Dash"]))
EXPORTS["SM_SpiderCar_Fang_L"] = build("SM_SpiderCar_Fang_L", own(fl))
EXPORTS["SM_SpiderCar_Fang_R"] = build("SM_SpiderCar_Fang_R", own(fr))
EXPORTS["SM_SpiderCar_Venom_Flash"] = build("SM_SpiderCar_Venom_Flash", own(vf))
EXPORTS["SM_SpiderCar_Venom_Droplets"] = build("SM_SpiderCar_Venom_Droplets", own(dr))
EXPORTS["SM_SpiderCar_Venom_JamSmoke"] = build("SM_SpiderCar_Venom_JamSmoke", own(D["FX_Engine_Jam_Smoke_0"]))
EXPORTS["SM_SpiderCar_WebStorm"] = build("SM_SpiderCar_WebStorm", under_root(st))
EXPORTS["SM_SpiderCar_WebStorm_Flash"] = build("SM_SpiderCar_WebStorm_Flash", own(sf))
EXPORTS["SM_SpiderCar_Entangle_Wrap"] = build("SM_SpiderCar_Entangle_Wrap", own(ew))
EXPORTS["SM_SpiderCar_Cocoon"] = build("SM_SpiderCar_Cocoon", under_root(co))
EXPORTS["SM_SpiderCar_Cocoon_Fragments"] = build("SM_SpiderCar_Cocoon_Fragments", own(fg))
EXPORTS["SM_SpiderCar_Cocoon_Flash"] = build("SM_SpiderCar_Cocoon_Flash", own(cf))
EXPORTS["SM_SpiderCar_Dash_Streaks"] = build("SM_SpiderCar_Dash_Streaks", own(sk))
SPARKS = {"SM_SpiderCar_Sparks_WebShotImpact": "FX_WebShot_Impact_Silk", "SM_SpiderCar_Sparks_StormCatch": "FX_Storm_Catch_0",
          "SM_SpiderCar_Sparks_DashCollision": "FX_Dash_Collision_Sparks", "SM_SpiderCar_Sparks_EngineJam": "FX_Engine_Jam_Sparks_0"}
for nm, grp in SPARKS.items():
    kids = [o for o in D[grp].children if o.type == 'MESH']
    EXPORTS[nm] = build(nm, [(o, o.matrix_basis.to_3x3().to_4x4()) for o in kids], sparks=True)


# ---------------------------------------------------------------- 3. pivots, sizes, parameters, materials
def bounds(objs, inv):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            p = inv @ (o.matrix_world @ Vector(c))
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
    return lo, hi


def tree(o):
    out = [o]
    for c in o.children:
        out += tree(c)
    return out


FX_PREFIX = ("FX_", "WEB_", "SHIELD", "POP_", "UI_", "CAM_")
car = [o for o in tree(SP) if o.type in {'MESH', 'CURVE'} and not o.name.startswith(FX_PREFIX)]
lo, hi = bounds(car, SP.matrix_world.inverted())
en = D["ENEMY_WebShot_Target"]
eparts = [o for o in tree(en) if o.type in {'MESH', 'CURVE'} and not o.name.startswith(FX_PREFIX) and "_HP" not in o.name]
elo, ehi = bounds(eparts, en.matrix_world.inverted())


def matinfo(m):
    info = {"base": [0.5, 0.5, 0.5], "metal": 0.0, "rough": 0.5, "emis": [0, 0, 0], "coat": 0.0}
    b = next((nd for nd in m.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED'), None) if m and m.node_tree else None
    if b:
        info["base"] = list(b.inputs['Base Color'].default_value)[:3]
        info["metal"] = b.inputs['Metallic'].default_value
        info["rough"] = b.inputs['Roughness'].default_value
        es = b.inputs['Emission Strength'].default_value
        info["emis"] = [c * es for c in list(b.inputs['Emission Color'].default_value)[:3]]
        info["coat"] = b.inputs['Coat Weight'].default_value
    return info


spark_params = {"SM_SpiderCar_Sparks_WebShotImpact": dict(speed=0.25, dur=12), "SM_SpiderCar_Sparks_StormCatch": dict(speed=0.15, dur=10),
                "SM_SpiderCar_Sparks_DashCollision": dict(speed=0.32, dur=14), "SM_SpiderCar_Sparks_EngineJam": dict(speed=0.18, dur=9)}
scene.frame_set(1)
out = {
    "fps": FPS,
    "spider_bounds_cm": [ue(lo), ue(hi)],
    "enemy_bounds_cm": [ue(elo), ue(ehi)],
    "pivots_cm_spider_space": {
        "MuzzleFlash": ue(mf.location), "Tether": ue(te.location), "StormFlash": ue(sf.location), "CocoonFlash": ue(cf.location),
        "Cocoon": ue(co.location), "Fragments": ue(fg.location), "Streaks": ue(sk.location),
        "Fang_L": ue(fl.location), "Fang_R": ue(fr.location),
        "BitePoint": ue(bite_pt - Vector((1.1, 0, 0))),        # spider was at x=1.1 on the bite frame
    },
    "projectile_spin_rad_per_s": [6 * FPS / 11, 3 * FPS / 11, 9 * FPS / 11],
    "storm_radius_cm": 950, "venom_bite_point_enemy_space_cm": ue(Vector((-2.1, 0.0, 0.55))),
    "sparks": spark_params,
    "jam_puffs": PUFFS, "jam_sparks": JAM_SPARKS,
    "materials": {m.name: matinfo(m) for m in bpy.data.materials if m.name.startswith("SPIDER_")},
    "meshes": EXPORTS,
}
print("spider bounds", out["spider_bounds_cm"], "enemy", out["enemy_bounds_cm"])
json.dump(out, open(os.path.join(OUT, "SpiderCar_Abilities_Export.json"), "w"), indent=1)
print("DONE", len(rows), "curves")
