"""Plan: turn Lvl_GardenArena into the cinematic "backyard at golden hour" arena (2026-11-11).

Reads Saved/ClaudeScripts/arena_dump.json (labels -> actors as dumped from the level) and writes plan.json:
  * ground plane gets the world-aligned sandy-dirt material, log border lowered to ~4.5 m with PBR bark
  * cartoon pebbles / pots / tomatoes swapped for Poly Haven photoscans, new giant backyard props as obstacles
  * landmarks outside the border (garden gnome, bucket, clay pots, ferns and weeds)
  * drifting pollen motes, lantern light

    python gen_backyard_level.py [props|undo]
"""
import json, math, sys

SCR = "D:/PrisonerOfTommrow/Battle/Saved/ClaudeScripts/"
L = "/Game/BugBattle/Maps/Lvl_GardenArena.Lvl_GardenArena:PersistentLevel."
MESH = "/Game/BugBattle/Backyard/Meshes/SM_BY_"
MATS = "/Game/BugBattle/Backyard/Materials/"
FLOOR = -40.0
dump = json.load(open(SCR + "arena_dump.json"))
rows = {r["label"]: r for r in dump["rows"]}
mesh_path = {k.split(".")[-1]: k for k in dump["meshes"]}
plan = []


def step(t, a, n=None, opt=False, show=False, first=False):
    s = {"t": t, "a": a}
    if n:
        s["n"] = n
    if opt:
        s["opt"] = 1
    if show:
        s["show"] = show
    if first:
        s["first"] = 1
    plan.append(s)


def mat(n):
    return {"refPath": MATS + n + "." + n}


def act(label):
    return {"refPath": L + rows[label]["name"]}


def P(theta, r):
    a = math.radians(theta)
    return (r * math.cos(a), r * math.sin(a))


def xf(loc=None, rot=None, scale=None):
    x = {}
    if loc is not None:
        x["location"] = {"x": loc[0], "y": loc[1], "z": loc[2]}
    if rot is not None:
        x["rotation"] = {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]}
    if scale is not None:
        s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
        x["scale"] = {"x": s[0], "y": s[1], "z": s[2]}
    return x


N = [0]


def place(label, mesh, xy, z=FLOOR, yaw=0.0, scale=1.0, pitch=0.0, roll=0.0, folder="Backyard/Props", shadow=True):
    N[0] += 1
    key = "a%d" % N[0]
    step("SC.add_to_scene_from_asset", {"asset_path": MESH + mesh, "name": label,
                                        "xform": xf((xy[0], xy[1], z), (pitch, yaw, roll), scale)}, n=key)
    step("SC.set_actor_folder", {"actor": "$" + key, "folder_path": folder}, opt=True)
    if not shadow:
        step("OT.set_properties", {"instance": "@{%s}.StaticMeshComponent0" % key, "values": {"castShadow": False}}, opt=True)
    return key


def props():
    # ---------------- ground + border + existing procedural props
    step("OT.set_properties", {"instance": {"refPath": L + rows["MeadowGround"]["name"] + ".StaticMeshComponent0"},
                               "values": {"overrideMaterials": [mat("MI_BY_Ground")]}}, show=40)
    for lab in rows:
        if lab.startswith("LogBorder_"):
            step("AT.set_actor_transform", {"actor": act(lab), "xform": xf(scale=(1.0, 1.0, 0.35)), "worldspace": True})
    for m in ("SM_LogBorder_A", "SM_LogBorder_B", "SM_LogBorder_C", "SM_TreeStump"):
        step("SM.set_material", {"mesh": {"refPath": mesh_path[m]}, "slot_name": "BarkMat", "material": mat("MI_BY_TriBark")}, show=20)
    step("SM.set_material", {"mesh": {"refPath": mesh_path["SM_PotTunnel"]}, "slot_name": "TerracottaMat", "material": mat("MI_BY_TriTerracotta")}, show=20)
    step("SM.set_material", {"mesh": {"refPath": mesh_path["SM_PotTunnel"]}, "slot_name": "TerracottaInMat", "material": mat("MI_BY_TriTerracotta")}, show=20)
    step("SM.set_material", {"mesh": {"refPath": mesh_path["SM_Acorn_B"]}, "slot_name": "AcornCapMat", "material": mat("MI_BY_TriBark")}, opt=True)

    # ---------------- cartoon rocks -> mossy scans
    k = 0
    for lab, r in sorted(rows.items()):
        if lab.startswith("Pebble_"):
            sc = r["scale"][0] * (1.75 if "Pebble_C" in r["mesh"] else 1.45)
            place("MossRock_%d" % k, "rock_moss_set_01_%d" % (k % 6), r["loc"][:2], FLOOR - 22.0, r["yaw"], sc, folder="Backyard/Rocks")
            step("SC.remove_from_scene", {"actor": act(lab)}, opt=True)
            k += 1
    # ---------------- cartoon pots / tomatoes -> scans
    for lab, r in sorted(rows.items()):
        if lab.startswith("FlowerPot_"):
            place("ClayPot_" + lab[-1], "planter_pot_clay", r["loc"][:2], FLOOR - 30.0, r["yaw"], (54.7, 54.7, 60.5), folder="Backyard/Outside")
            step("SC.remove_from_scene", {"actor": act(lab)}, opt=True)
        if lab.startswith("CherryTomato_"):
            place("Apple_Edge_" + lab[-1], "food_apple_01", r["loc"][:2], FLOOR - 20.0, r["yaw"], 38.0, folder="Backyard/Props")
            step("SC.remove_from_scene", {"actor": act(lab)}, opt=True)
        if lab.startswith("FallenTomato_"):
            step("SC.remove_from_scene", {"actor": act(lab)}, opt=True)

    # ---------------- arena obstacles (keep the 8 starts on the r 4300 ring clear)
    place("FallenTrunk_E", "dead_tree_trunk", P(0, 3000), FLOOR - 25.0, 90.0, (6.0, 8.5, 8.5))
    place("FallenTrunk_W", "dead_tree_trunk", P(180, 3000), FLOOR - 25.0, 98.0, (6.0, 8.5, 8.5))
    place("Football", "dirty_football", P(45, 4550), FLOOR - 10.0, 30.0, 20.0)
    place("Baseball", "baseball_01", P(90, 3500), FLOOR - 8.0, 70.0, 38.0)
    place("TyreArch", "old_tyre", P(-90, 3500), FLOOR - 300.0, 0.0, 14.0)
    place("RubberDuck", "rubber_duck_toy", (2252.0, -1300.0), FLOOR - 25.0, 200.0, 15.0)
    place("OldStump", "tree_stump_01", P(-45, 4650), FLOOR - 15.0, 40.0, 4.5)
    place("WateringCan", "watering_can_metal_01", P(180, 4950), FLOOR - 10.0, 15.0, 24.0)
    bx, by = P(0, 5250)
    place("Boot_L", "rubber_boots_2", (bx, by - 150.0), FLOOR - 8.0, 80.0, 17.0)
    place("Boot_R", "rubber_boots_3", (bx - 60.0, by + 170.0), FLOOR - 8.0, 104.0, 17.0)
    place("Lantern", "Lantern_01", P(135, 5050), FLOOR - 6.0, -30.0, 27.0)
    place("Apple_A", "food_apple_01", P(-135, 4500), FLOOR - 18.0, 10.0, 36.0)
    place("Apple_B", "food_apple_01", P(-127, 3950), FLOOR - 18.0, 130.0, 30.0, pitch=25.0)
    place("Trowel", "trowel_01", P(22.5, 5600), FLOOR + 40.0, 112.0, 26.0, pitch=0.0, roll=-55.0)
    place("Boulder_N", "boulder_01", P(68, 5550), FLOOR - 30.0, 20.0, 2.2, folder="Backyard/Rocks")
    place("Boulder_S", "boulder_01", P(-68, 5550), FLOOR - 30.0, 140.0, 2.0, folder="Backyard/Rocks")
    place("Rock_Slab", "rock_07", P(158, 5500), FLOOR - 20.0, 60.0, 20.0, folder="Backyard/Rocks")
    place("Rock_Flat", "rock_09", P(-158, 5450), FLOOR - 12.0, -40.0, 36.0, folder="Backyard/Rocks")

    # ---------------- landmarks outside the border
    place("GardenGnome", "garden_gnome", P(90, 7900), FLOOR - 20.0, 180.0, 50.0, folder="Backyard/Outside")
    place("Bucket", "wooden_bucket_01", P(-22, 8700), FLOOR - 20.0, 30.0, 45.0, folder="Backyard/Outside")
    plants = [("fern_02_0", 20.0), ("shrub_03_0", 55.0), ("nettle_plant_4", 105.0), ("fern_02_1", 22.0), ("dandelion_01_0", 70.0),
              ("shrub_03_1", 60.0), ("weed_plant_02_0", 60.0), ("nettle_plant_5", 110.0), ("dandelion_01_1", 75.0), ("fern_02_2", 30.0),
              ("shrub_03_2", 70.0), ("weed_plant_02_1", 70.0)]
    for i in range(24):
        th = i * 15.0 + 7.5
        m, sc = plants[i % len(plants)]
        r = 6750.0 + 260.0 * ((i * 7) % 5)
        place("Plant_%02d" % i, m, P(th, r), FLOOR - 10.0, (i * 67) % 360, sc * (0.9 + 0.05 * ((i * 3) % 5)), folder="Backyard/Plants")

    # ---------------- pollen motes + lantern light
    place("PollenMotes", "Motes", (0.0, 0.0), 0.0, 0.0, 1.0, folder="Backyard/FX", shadow=False)
    lx, ly = P(135, 5050)
    step("SC.add_to_scene_from_class", {"actor_type": {"refPath": "/Script/Engine.PointLight"}, "name": "LanternLight",
                                        "xform": xf((lx, ly, FLOOR + 430.0))}, n="lantern_light")
    step("SC.set_actor_folder", {"actor": "$lantern_light", "folder_path": "Lighting"}, opt=True)
    step("OT.set_properties", {"instance": "@{lantern_light}.LightComponent0",
                               "values": {"intensity": 60000.0, "attenuationRadius": 3200.0, "sourceRadius": 60.0,
                                          "bUseTemperature": True, "temperature": 2400.0, "castShadows": False}}, opt=True, show=60)
    step("AS.save_assets", {"asset_paths": []}, show=40)


if __name__ == "__main__":
    props()
    json.dump(plan, open(SCR + "plan.json", "w"))
    print(len(plan), "steps", len(json.dumps(plan)), "bytes")
