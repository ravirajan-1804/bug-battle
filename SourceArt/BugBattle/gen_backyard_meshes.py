"""Plan: import the converted Poly Haven scans (Saved/ClaudeScripts/dl/obj) as /Game/BugBattle/Backyard/Meshes/SM_BY_*,
assign their material instances, enable Nanite on the dense ones and build convex collision for the arena obstacles.
Also writes SM_BY_Motes.obj (2600 tiny pollen motes with a per-mote seed in the UV) and imports it."""
import json, os, random
from meshlib import Mesh

DL = "D:/PrisonerOfTommrow/Battle/Saved/ClaudeScripts/dl/"
FOLD = "/Game/BugBattle/Backyard/Meshes"
MATS = "/Game/BugBattle/Backyard/Materials/"
NANITE = {"boulder_01", "dead_tree_trunk", "tree_stump_01", "garden_gnome", "Lantern_01_0", "dirty_football"}
# obstacle meshes -> (hull_count, max_hull_verts)
COLL = {"dead_tree_trunk": (8, 24), "dirty_football": (1, 32), "food_apple_01": (1, 32), "baseball_01": (1, 32), "rubber_duck_toy": (4, 24),
        "watering_can_metal_01": (8, 24), "Lantern_01_0": (4, 16), "old_tyre": (8, 16), "trowel_01": (4, 16), "tree_stump_01": (8, 32),
        "boulder_01": (4, 32), "rock_07": (2, 24), "rock_09": (2, 24), "mousetrap": (2, 16), "garden_gnome": (4, 24), "planter_pot_clay": (4, 24),
        "wooden_bucket_01_0": (4, 24)}
for i in range(6):
    COLL["rock_moss_set_01_%d" % i] = (3, 32)
for i in range(4):
    COLL["rubber_boots_%d" % i] = (6, 24)


def mi(mat):
    if mat == "rubber_boots":
        mat = "rubber_boots_dirty"
    nm = "MI_BY_LanternGlow" if mat == "Lantern_01_glass" else "MI_BY_" + mat
    return {"refPath": MATS + nm + "." + nm}


def motes():
    rnd = random.Random(11)
    m = Mesh()
    for _ in range(2600):
        import math
        a = rnd.uniform(0, 2 * math.pi); r = 6600.0 * math.sqrt(rnd.random())
        z = 30.0 + 1100.0 * (rnd.random() ** 1.7)
        c = (r * math.cos(a), r * math.sin(a), z)
        s = rnd.uniform(3.5, 8.0)
        uv = (rnd.random(), rnd.random())
        ids = [m.vert((c[0] + dx * s, c[1] + dy * s, c[2] + dz * s), uv, (dx, dy, dz))
               for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
        px, nx, py, ny, pz, nz = ids
        for a_, b_, c_ in ((px, py, pz), (py, nx, pz), (nx, ny, pz), (ny, px, pz), (py, px, nz), (nx, py, nz), (ny, nx, nz), (px, ny, nz)):
            m.tri("Motes", a_, b_, c_)
    return m.write_obj(DL + "obj/Motes.obj", smooth_weld=False)


plan = []
man = json.load(open(DL + "scans_manifest.json"))
for e in man["meshes"]:
    o = e["obj"]
    key = "sm_" + o
    if o == "garden_gnome":
        plan.append({"t": "AS.load_asset", "a": {"asset_path": FOLD + "/SM_BY_garden_gnome"}, "n": key})
    else:
        plan.append({"t": "SM.import_file", "a": {"folder_path": FOLD, "asset_name": "SM_BY_" + o, "source_file": DL + "obj/" + o + ".obj",
                                                  "import_materials": False, "import_textures": False, "combine_meshes": True}, "n": key, "first": 1})
    for mat in e["mats"]:
        plan.append({"t": "SM.set_material", "a": {"mesh": "$" + key, "slot_name": mat + "Mat", "material": mi(mat)}, "show": 30})
    if o in COLL:
        plan.append({"t": "SM.generate_convex_collisions", "a": {"mesh": "$" + key, "hull_count": COLL[o][0], "max_hull_verts": COLL[o][1]}, "opt": 1})
    else:
        plan.append({"t": "SM.remove_collisions", "a": {"mesh": "$" + key}, "opt": 1})
    if o in NANITE:
        plan.append({"t": "SM.set_nanite_enabled", "a": {"mesh": "$" + key, "enabled": True}, "opt": 1})
print("motes tris", motes())
plan.append({"t": "SM.import_file", "a": {"folder_path": FOLD, "asset_name": "SM_BY_Motes", "source_file": DL + "obj/Motes.obj",
                                          "import_materials": False, "import_textures": False, "combine_meshes": True}, "n": "sm_motes", "first": 1})
plan.append({"t": "SM.set_material", "a": {"mesh": "$sm_motes", "slot_name": "MotesMat", "material": mi("Motes")}, "show": 30})
plan.append({"t": "SM.remove_collisions", "a": {"mesh": "$sm_motes"}, "opt": 1})
plan.append({"t": "AS.save_assets", "a": {"asset_paths": []}, "show": 40})
json.dump(plan, open("../../Saved/ClaudeScripts/plan.json", "w"))
print(len(plan), "steps", len(json.dumps(plan)))
