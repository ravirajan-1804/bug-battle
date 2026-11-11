"""Export Bee_Racer.blend to UE-convention OBJs matching the BP_VehicleAdvSportsCar template.
Blender: front = -Y, left = +X, metres.  UE: +X fwd, +Y right, cm.  OBJ written like meshlib (y negated).
Template hubs: x +134/-130, y +-90, z 27, r 39."""
import bpy, sys, os
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--")+1]
HUB_Y_F, HUB_Y_R, HUB_X, HUB_Z, R = -1.43, 1.59, 0.93, 0.47, 0.47
SX = 264.0 / ((HUB_Y_R-HUB_Y_F)*100)      # wheelbase -> 264 cm
SY = 90.0 / (HUB_X*100)                    # track -> +-90 cm
SZ = 39.0 / (R*100)                        # tyre radius -> 39 cm
MIDY = (HUB_Y_F+HUB_Y_R)/2
print("SCALE", SX, SY, SZ)
dg = bpy.context.evaluated_depsgraph_get()

def collect(objs, xform):
    out = {}  # mat -> list of tris [(p,n)*3]
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        mw = o.matrix_world; nm = mw.to_3x3().inverted().transposed()
        cn = me.corner_normals
        mats = [s.material.name if s.material else "Paint_Black" for s in ev.material_slots] or ["Paint_Black"]
        for t in me.loop_triangles:
            mat = mats[min(t.material_index, len(mats)-1)]
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
        f.write("# exported from Bee_Racer.blend\n")
        f.writelines("v %.4f %.4f %.4f\n" % tuple(v) for v in vs)
        f.writelines("vn %.5f %.5f %.5f\n" % tuple(n) for n in ns)
        f.write("\n".join(lines) + "\n")
    print("WROTE", path, sum(len(t) for t in data.values()), "tris", {m: len(t) for m, t in data.items()})

def nrm(n):  # inverse-transpose of the axis map + scale, OBJ space
    v = Vector((-n.y/SX, n.x/SY, n.z/SZ)); return v.normalized()

def body_x(p, n):
    return ((-(p.y-MIDY)*100*SX + 2, p.x*100*SY, (p.z-HUB_Z)*100*SZ + 27), nrm(n))

root = bpy.data.objects["BeeRacer_Root"]
def under(o, a):
    while o:
        if o == a: return True
        o = o.parent
    return False
wheels = {o for o in bpy.data.objects if o.name.startswith("Wheel_")}
body = [o for o in bpy.data.objects if o.type in {'MESH','CURVE'} and under(o, root) and o not in wheels]
hub = bpy.data.objects["Wheel_FR"].matrix_world.translation
def wheel_x(p, n):
    d = p - hub
    return ((-d.y*100*SZ, d.x*100*SY, d.z*100*SZ), Vector((-n.y, n.x*SZ/SY, n.z)).normalized())
os.makedirs(OUT, exist_ok=True)
write(os.path.join(OUT, "SM_RGC_BeeRacer_Body.obj"), collect(body, body_x))
write(os.path.join(OUT, "SM_RGC_BeeRacer_Wheel.obj"), collect([bpy.data.objects["Wheel_Tire_FR"], bpy.data.objects["Wheel_Rim_FR"]], wheel_x))
