"""Generic exporter for the user's Blender cars (Spider_Car.blend, Ant_Car.blend, ...) -> UE OBJs that fit the
BP_VehicleAdvSportsCar template, like export_beeracer.py but reading the hubs/tyre size from the file.

Blender convention of these models: front = -Y, left = +X, metres, four wheel empties.
UE: +X fwd, +Y right, cm. Template hubs: x +134/-130 (wheelbase 264), y +-90, z 27, tyre radius 39.

Usage:
  blender -b Car.blend --python export_blendcar.py -- <out_dir> <Name> <Root> <WheelPrefix> <TireFR> <RimFR> [exclude_regex]
  e.g. ... -- obj_cars SpiderRacer SpiderCar_Root Wheel_ Tyre_FR Rim_FR
Writes SM_RGC_<Name>_Body.obj, SM_RGC_<Name>_Wheel.obj and SM_RGC_<Name>_materials.json (Blender material colours).
"""
import bpy, sys, os, re, json
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT, NAME, ROOT, WPRE, TIRE, RIM = args[:6]
EXCLUDE = re.compile(args[6]) if len(args) > 6 else None

W = {k: bpy.data.objects[WPRE + k].matrix_world.translation.copy() for k in ("FL", "FR", "RL", "RR")}
HUB_Y_F = (W["FL"].y + W["FR"].y) / 2
HUB_Y_R = (W["RL"].y + W["RR"].y) / 2
HUB_X = (abs(W["FL"].x) + abs(W["FR"].x) + abs(W["RL"].x) + abs(W["RR"].x)) / 4
HUB_Z = sum(v.z for v in W.values()) / 4
tire = bpy.data.objects[TIRE]
tz = [(tire.matrix_world @ Vector(c)).z for c in tire.bound_box]
R = (max(tz) - min(tz)) / 2

SX = 264.0 / ((HUB_Y_R - HUB_Y_F) * 100)      # wheelbase -> 264 cm
SY = 90.0 / (HUB_X * 100)                     # track -> +-90 cm
SZ = 39.0 / (R * 100)                         # tyre radius -> 39 cm
MIDY = (HUB_Y_F + HUB_Y_R) / 2
print("HUBS yF %.3f yR %.3f x %.3f z %.3f r %.3f  SCALE %.3f %.3f %.3f" % (HUB_Y_F, HUB_Y_R, HUB_X, HUB_Z, R, SX, SY, SZ))
# Thin beveled curves (pinstripes, LED piping) are authored at render resolution (res 16 x bevel 4);
# lower it in this session only - the .blend is never saved - so the game meshes stay light.
for o in bpy.data.objects:
    if o.type == 'CURVE':
        thin = o.data.bevel_depth < 0.03
        o.data.resolution_u = min(o.data.resolution_u, 4 if thin else 6)
        o.data.bevel_resolution = min(o.data.bevel_resolution, 1 if thin else 2)
    # same for subdivision: at most 1 level, none on meshes that are already dense (Snail shell = 18k quads)
    elif o.type == 'MESH':
        for m in o.modifiers:
            if m.type == 'SUBSURF':
                m.levels = 0 if len(o.data.polygons) > 8000 else min(m.levels, 1)
dg = bpy.context.evaluated_depsgraph_get()


def zramp(mat):
    """(map_range, color_ramp) if Base Color is a ColorRamp over Object-space Z (Snail body gradient), else None."""
    if not (mat and mat.use_nodes):
        return None
    b = next((nd for nd in mat.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED'), None)
    lk = b and b.inputs['Base Color'].links
    ramp = lk and lk[0].from_node
    if not ramp or ramp.type != 'VALTORGB' or not ramp.inputs[0].links:
        return None
    mr = ramp.inputs[0].links[0].from_node
    if mr.type != 'MAP_RANGE' or not mr.inputs[0].links or mr.inputs[0].links[0].from_socket.name != 'Z':
        return None
    return mr, ramp


ZBANDS = 5  # gradient materials are split into this many height bands: <mat>_Z0 (low) .. _Z4 (high)


def zband(mat, z):
    mr, _ = zramp(mat)
    lo, hi = mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value
    t = min(max((z - lo) / (hi - lo), 0.0), 1.0)
    return min(int(t * ZBANDS), ZBANDS - 1)


def collect(objs, xform):
    out = {}
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        mw = o.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        cn = me.corner_normals
        slots = [s.material for s in ev.material_slots] or [None]
        for t in me.loop_triangles:
            m = slots[min(t.material_index, len(slots) - 1)]
            mat = m.name if m else "Default"
            if zramp(m):  # Object-space Z of the triangle centre picks the band
                mat += "_Z%d" % zband(m, sum(me.vertices[v].co.z for v in t.vertices) / 3)
            tri = []
            for li in t.loops:
                p = mw @ me.vertices[me.loops[li].vertex_index].co
                n = (nm @ Vector(cn[li].vector)).normalized()
                tri.append(xform(p, n))
            out.setdefault(mat, []).append(tri)
        ev.to_mesh_clear()
    return out


def write(path, data):
    vs, ns, lines = [], [], []
    for mat, tris in data.items():
        lines.append("usemtl %s\ng %s" % (mat, mat))
        for tri in tris:
            idx = []
            for p, n in tri:
                vs.append(p); ns.append(n); idx.append(len(vs))
            lines.append("f %d//%d %d//%d %d//%d" % (idx[0], idx[0], idx[1], idx[1], idx[2], idx[2]))
    with open(path, "w") as f:
        f.write("# exported from %s\n" % os.path.basename(bpy.data.filepath))
        f.writelines("v %.4f %.4f %.4f\n" % tuple(v) for v in vs)
        f.writelines("vn %.5f %.5f %.5f\n" % tuple(n) for n in ns)
        f.write("\n".join(lines) + "\n")
    print("WROTE", path, sum(len(t) for t in data.values()), "tris", {m: len(t) for m, t in data.items()})


def nrm(n):
    return Vector((-n.y / SX, n.x / SY, n.z / SZ)).normalized()


def body_x(p, n):
    return ((-(p.y - MIDY) * 100 * SX + 2, p.x * 100 * SY, (p.z - HUB_Z) * 100 * SZ + 27), nrm(n))


root = bpy.data.objects[ROOT]


def under(o, a):
    while o:
        if o == a:
            return True
        o = o.parent
    return False


wheel_parts = {o for o in bpy.data.objects if o.parent and o.parent.name.startswith(WPRE)}
body = [o for o in bpy.data.objects if o.type in {'MESH', 'CURVE'} and under(o, root) and o not in wheel_parts
        and not (EXCLUDE and EXCLUDE.search(o.name))]
hub = bpy.data.objects[WPRE + "FR"].matrix_world.translation


def wheel_x(p, n):
    d = p - hub
    return ((-d.y * 100 * SZ, d.x * 100 * SY, d.z * 100 * SZ), Vector((-n.y, n.x * SZ / SY, n.z)).normalized())


os.makedirs(OUT, exist_ok=True)
bd = collect(body, body_x)
wd = collect([bpy.data.objects[TIRE], bpy.data.objects[RIM]], wheel_x)
write(os.path.join(OUT, "SM_RGC_%s_Body.obj" % NAME), bd)
write(os.path.join(OUT, "SM_RGC_%s_Wheel.obj" % NAME), wd)

# material colours for the UE material instances
mats = {}
for mname in set(bd) | set(wd):
    band = re.match(r"(.*)_Z(\d)$", mname)
    m = bpy.data.materials.get(band.group(1) if band else mname)
    info = {"base": [0.5, 0.5, 0.5], "metal": 0.0, "rough": 0.5, "emis": [0, 0, 0]}
    if m and m.use_nodes:
        b = next((nd for nd in m.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED'), None)
        if b:
            info["base"] = list(b.inputs['Base Color'].default_value)[:3]
            src = b.inputs['Base Color'].links and b.inputs['Base Color'].links[0].from_node
            if band:  # colour at the band's centre of the ramp
                info["base"] = list(zramp(m)[1].color_ramp.evaluate((int(band.group(2)) + 0.5) / ZBANDS))[:3]
            elif src and src.type == 'MIX':  # procedural mix (Snail shell noise): average the mixed colours
                a = next(i for i in src.inputs if i.identifier == 'A_Color')
                while a.is_linked and a.links[0].from_node.type == 'MIX':
                    src = a.links[0].from_node
                    a = next(i for i in src.inputs if i.identifier == 'A_Color')
                cols = [i.default_value for i in src.inputs if i.type == 'RGBA' and not i.is_linked]
                if cols:
                    info["base"] = [sum(c[k] for c in cols) / len(cols) for k in range(3)]
            info["metal"] = b.inputs['Metallic'].default_value
            info["rough"] = b.inputs['Roughness'].default_value
            ec = b.inputs.get('Emission Color') or b.inputs.get('Emission')
            es = b.inputs.get('Emission Strength')
            s = es.default_value if es else 1.0
            info["emis"] = [c * s for c in list(ec.default_value)[:3]] if ec else [0, 0, 0]
    elif m:
        info["base"] = list(m.diffuse_color)[:3]
    mats[mname] = info
json.dump(mats, open(os.path.join(OUT, "SM_RGC_%s_materials.json" % NAME), "w"), indent=1)
print("MATS", json.dumps(mats))
