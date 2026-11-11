"""Plan: import the prepared Poly Haven textures (Saved/ClaudeScripts/dl/import) into /Game/BugBattle/Backyard/Textures."""
import json, os
D = "D:/PrisonerOfTommrow/Battle/Saved/ClaudeScripts/dl/import/"
FOLD = "/Game/BugBattle/Backyard/Textures"
plan = []
for f in sorted(os.listdir(D)):
    nm = f.rsplit(".", 1)[0]
    if nm == "T_dirt_floor_N":
        continue  # imported by hand as the first test
    plan.append({"t": "TX.import_file", "a": {"folder_path": FOLD, "asset_name": nm, "source_file": D + f}, "n": nm, "first": 1, "opt": 1})
    if nm.endswith("_ARM"):
        plan.append({"t": "OT.set_properties", "a": {"instance": "$" + nm, "values": {"sRGB": False, "compressionSettings": "TC_Masks"}}, "opt": 1})
plan.append({"t": "AS.save_assets", "a": {"asset_paths": []}, "show": 50})
json.dump(plan, open("../../Saved/ClaudeScripts/plan.json", "w"))
print(len(plan), "steps")
