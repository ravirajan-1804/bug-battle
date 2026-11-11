"""Generates the AntUpdatePose graph (Blueprint DSL) for BPC_AntPowers from the ant car GLB.

Every animated bone gets one AntApplyBone(Bone, Loc, Rot, Scale) call whose values are linear blends of the
power alphas (aQ armor, aE swarm, aR acid, aT speed) plus the mandible yaw / nozzle yaw / lunge inputs.
Space is SK_AntCar component space: X = car left, Y = forward, Z = up, metres (component scale 100).
Plates whose bone origin is the car origin are scaled about their own centre (offset compensation), so they
expand in place instead of drifting. Output: D:/Game/Saved/AntUpdatePose.txt (loaded by unreal-mcp)."""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import gen_swarm_ant as G  # noqa: E402  (GLB reader + node helpers; also refreshes SM_SwarmAnt.obj)

# Sign conventions, verified in the editor viewport with the vehicle's preview sliders.
LEAN = -1.0      # Root roll sign that pitches the nose down
ABD = 1.0        # Abdomen roll sign that lifts the tail
MAND = 1.0       # yaw sign that opens the LEFT mandible outward (right mandible uses the opposite)
HATCH_SIDE = 1.0
HATCH_REAR = 1.0

nodes = G.nodes
by = G.by_name


def comp(p):  # glTF -> component space
    return (p[0], p[2], p[1])


def bone_origin(name):
    i = by[name]
    p = [0.0, 0.0, 0.0]
    p = G.world_pt(i, p)
    return comp(p)


def center(name):
    lo = [1e9] * 3
    hi = [-1e9] * 3
    stack = [by[name]]
    while stack:
        k = stack.pop()
        n = nodes[k]
        if "mesh" in n:
            for prim in G.g["meshes"][n["mesh"]]["primitives"]:
                a = G.g["accessors"][prim["attributes"]["POSITION"]]
                for cx in (0, 1):
                    for cy in (0, 1):
                        for cz in (0, 1):
                            p = [a["min"][0] if cx == 0 else a["max"][0], a["min"][1] if cy == 0 else a["max"][1],
                                 a["min"][2] if cz == 0 else a["max"][2]]
                            q = comp(G.world_pt(k, p))
                            for c in range(3):
                                lo[c] = min(lo[c], q[c])
                                hi[c] = max(hi[c], q[c])
        stack.extend(n.get("children", []))
    return tuple((lo[c] + hi[c]) / 2 for c in range(3))


B = lambda s: "ANTCAR_" + s  # noqa: E731
bones = {}  # bone -> {"loc": {alpha: [x,y,z]}, "rot": {alpha: [roll,pitch,yaw]}, "scale": {alpha: ds}}
order = []


def entry(b):
    if b not in bones:
        bones[b] = {"loc": {}, "rot": {}, "scale": {}}
        order.append(b)
    return bones[b]


def plate(b, alpha, move=(0, 0, 0), s=1.0, about=None):
    """Move by `move` and scale by s about point `about` (default: the plate's own centre)."""
    e = entry(B(b))
    c = about if about is not None else center(B(b))
    o = bone_origin(B(b))
    d = [move[k] - (s - 1.0) * (c[k] - o[k]) for k in range(3)]
    acc = e["loc"].setdefault(alpha, [0.0, 0.0, 0.0])
    for k in range(3):
        acc[k] += d[k]
    if abs(s - 1.0) > 1e-6:
        e["scale"][alpha] = e["scale"].get(alpha, 0.0) + (s - 1.0)


def rot(b, alpha, roll=0.0, pitch=0.0, yaw=0.0, move=(0, 0, 0)):
    e = entry(B(b))
    r = e["rot"].setdefault(alpha, [0.0, 0.0, 0.0])
    r[0] += roll
    r[1] += pitch
    r[2] += yaw
    acc = e["loc"].setdefault(alpha, [0.0, 0.0, 0.0])
    for k in range(3):
        acc[k] += move[k]


# ---- whole body (Root is the parent of everything, so it goes first) ----
rot("Root", "aT", roll=LEAN * 4.0, move=(0, 0, -0.03))
rot("Root", "Lunge", roll=LEAN * 3.0, move=(0, 0.15, 0))

# ---- R acid: abdomen lifts, nozzle aims, tanks swell, tank armour slides open ----
rot("Abdomen_Pivot", "aR", roll=ABD * 20.0)
rot("Abdomen_Pivot", "aT", roll=ABD * -5.0)
rot("Abdomen_Pivot", "aQ", move=(0, 0, 0.03))
rot("Acid_Nozzle", "NozzleYaw", yaw=1.0)
rot("Acid_Nozzle", "aR", roll=ABD * -12.0)
for side, sx in (("L", 1.0), ("R", -1.0)):
    plate("Acid_Tank_" + side, "aR", s=1.06)
    plate("Acid_Liquid_" + side, "aR", s=1.08)
    plate("Acid_Pipe_" + side, "aR", s=1.05)
    plate("Acid_Tank_Armor_" + side, "aR", move=(sx * 0.10, 0, 0.03))
    plate("Acid_Tank_Armor_" + side, "aQ", move=(sx * 0.05, 0, 0), s=1.06)
plate("Acid_Pressure_Chamber", "aR", s=1.15)
for k in range(1, 5):
    seg = "Rear_Abdomen_%02d" % k
    c = center(B(seg))
    for part in (seg, seg + "_Crimson_Plate"):
        plate(part, "aQ", move=(0, 0, 0.04), s=1.08, about=c)
        plate(part, "aR", move=(0, -0.035 * (k - 1), 0.03 * (k - 1)), about=c)

# ---- E swarm: deployment hatches swing open ----
for k, sx in ((1, 1.0), (2, 1.0), (3, -1.0), (4, -1.0)):
    rot("Swarm_Port_%02d_Hatch" % k, "aE", pitch=HATCH_SIDE * sx * -75.0, move=(sx * 0.09, 0, 0.07))
for k in (5, 6):
    rot("Swarm_Port_%02d_Hatch" % k, "aE", roll=HATCH_REAR * 75.0, move=(0, -0.09, 0.07))

# ---- Q armour shell (T streamlines the same plates inward) ----
for side, sx in (("L", 1.0), ("R", -1.0)):
    c = center(B("Side_Armor_" + side))
    for part in ("Side_Armor_" + side, "Side_Armor_Stripe_" + side):
        plate(part, "aQ", move=(sx * 0.10, 0, -0.05), s=1.15, about=c)
        plate(part, "aT", move=(sx * -0.03, 0, -0.02), about=c)
    for w, wc in (("F", (sx * 1.0, 1.5, 0.48)), ("R", (sx * 1.04, -0.85, 0.55))):
        for k in (1, 2, 3):
            arch = "Wheel_Arch_%s%s_%02d" % (w, side, k)
            plate(arch, "aQ", move=(sx * 0.05, 0, -0.03), s=1.14, about=wc)
            plate(arch, "aT", move=(sx * -0.02, 0, -0.02), about=wc)
    for k in ("A", "B"):
        plate("Cheek_Armor_%s_%s" % (side, k), "aQ", move=(sx * 0.06, 0.02, 0), s=1.15)
    plate("Brow_Armor_" + side, "aQ", move=(0, 0, 0.04), s=1.12)
    plate("Propulsion_Unit_" + side, "aT", move=(0, -0.06, 0), s=1.12)
    plate("Propulsion_Fairing_" + side, "aT", move=(0, -0.06, 0), s=1.10)
    plate("Exhaust_" + side, "aT", move=(0, -0.05, 0), s=1.2)
plate("Front_Armor", "aQ", move=(0, 0.05, 0), s=1.25)
plate("Front_Bumper", "aQ", s=1.06)
plate("Front_Splitter", "aQ", s=1.06)
plate("Front_Splitter", "aT", move=(0, 0.05, -0.03))
plate("Head_Crest", "aQ", move=(0, 0, 0.05))
plate("Head_Crest", "aT", move=(0, 0, -0.04))
for k, nm in ((1, "01_Pronotum"), (2, "02_Mesonotum"), (3, "03_Propodeum")):
    c = center(B("Thorax_Plate_" + nm))
    for part in ("Thorax_Plate_" + nm, "Thorax_Stripe_%02d" % k):
        plate(part, "aQ", move=(0, 0, 0.06), s=1.10, about=c)
        plate(part, "aT", move=(0, 0, -0.03), about=c)

# ---- Y mandibles (armor folds them partly inward) ----
rot("Left_Mandible", "MandYaw", yaw=MAND * 1.0)
rot("Right_Mandible", "MandYaw", yaw=-MAND * 1.0)
rot("Left_Mandible", "aQ", yaw=MAND * -12.0)
rot("Right_Mandible", "aQ", yaw=-MAND * 12.0)


# ---- emit DSL ----
def f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".") if abs(v) > 1e-9 else "0.0"


def lin(terms):
    """terms: list of (alpha, coeff) -> DSL float expression"""
    terms = [(a, c) for a, c in terms if abs(c) > 1e-6]
    if not terms:
        return "0.0"
    parts = ["(* %s %s)" % (a, f(c)) if abs(c - 1.0) > 1e-9 else a for a, c in terms]
    expr = parts[0]
    for p in parts[1:]:
        expr = "(+ %s %s)" % (expr, p)
    return expr


lines = ["(fn AntUpdatePose (aQ aE aR aT MandYaw NozzleYaw Lunge)"]
for b in order:
    e = bones[b]
    loc = [lin([(a, v[k]) for a, v in e["loc"].items()]) for k in range(3)]
    r = [lin([(a, v[k]) for a, v in e["rot"].items()]) for k in range(3)]
    sc = lin([(a, v) for a, v in e["scale"].items()])
    sc = "1.0" if sc == "0.0" else "(+ 1.0 %s)" % sc
    lines.append('  (CallFunction|AntApplyBone :Bone "%s" :Loc (Math|Vector|MakeVector %s %s %s) '
                 ':Rot (Math|Rotator|MakeRotator %s %s %s) :Scale %s)' % (b, loc[0], loc[1], loc[2], r[0], r[1], r[2], sc))
lines[-1] += ")"
out = "\n".join(lines) + "\n"
dst = r"D:\Game\Saved\AntUpdatePose.txt"
open(dst, "w").write(out)
print("bones:", len(order), "chars:", len(out))

