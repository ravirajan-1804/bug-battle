# Creature Karts — `/Game/RacingGame/Vehicles`

Seven drivable, low-poly creature racing cars for `Lvl_GardenGrandPrix` (and any map
using the BugBattle vehicle setup). Existing vehicles and Blueprints are untouched.

| Car | Blueprint | Look | Mass (kg) |
|---|---|---|---|
| Snail | `Snail/BP_RGC_Snail` | teal slug racer, orange spiral shell, eye stalks, pink wing | 1650 |
| Beetle | `Beetle/BP_RGC_Beetle` | metallic emerald elytra dome, cobalt shield, rhino horn | 1700 |
| Bee | `Bee/BP_RGC_Bee` | yellow/black striped teardrop, wing spoiler, antennae, stinger | 1400 |
| Spider | `Spider/BP_RGC_Spider` | faceted purple body, 8 legs arching over the wheels, red eye cluster, fangs | 1500 |
| Scorpion | `Scorpion/BP_RGC_Scorpion` | armoured amber plates, pincer bumpers, tail arching over with glowing stinger | 1600 |
| Ant | `Ant/BP_RGC_Ant` | red three-segment body, elbowed antennae, mandibles, yellow wing | 1450 |
| Butterfly | `Butterfly/BP_RGC_Butterfly` | navy body, magenta/cyan wing panels with eye-spots, ball antennae | 1350 |

Each folder holds `BP_RGC_<Name>`, `SM_RGC_<Name>_Body`, `SM_RGC_<Name>_Wheel`, and
`MI_RGC_<Name>_*`. Shared eye, tyre and glow materials are in `Vehicles/Shared`. All
materials are instances of the project's existing `M_BB_Surface`.

## How they work

- Each Blueprint is a **duplicate** of `BP_VehicleAdvSportsCar`, so it inherits
  `BP_VehicleAdvPawnBase` (input, cameras, flip recovery, HoneyStatus). It keeps the
  template's Chaos setup: skeletal mesh `SKM_SportsCar`, physics asset, wheel classes,
  engine curve, transmission and suspension.
- Only the visual components changed: `Chasis_Main` uses the creature body,
  `Chasis_Glass` is empty, and the four `*_Wheel` components use the creature wheel.
  `VehicleMovementComp.Mass` varies per character (±15 % around the template's
  1500 kg) for a light handling difference.
- **Scale/orientation/pivot:** +X forward, Z up, origin on the car centre like
  `SM_SportsCar`. Wheels pivot on the hub with the axle along local Y (same
  convention as `SM_SportsCar_Wheel`). Hubs measured from the template: front x 134,
  rear x −130, track ±90, hub z 27, radius 39.
- **Collision:** the template physics asset (≈ 470 × 228 cm body) does all colliding.
  The visual meshes have no collision, so decorations can't snag the track. Wings,
  the Snail shell and the Scorpion tail stick out past the collider; they are
  decorative and pass through other cars and the barriers.
- Bodies stay inside the inner tyre faces (|y| < 76 cm near the wheels), so wheels
  steer and spin without clipping.
- Budget: 4.2k–7.3k triangles per body, about 1.4k per wheel. No Nanite or LODs
  needed at this size.

## Test results (PIE on `Lvl_GardenGrandPrix`, 2026-10-14)

All seven cars were spawned on grid slots 1–7. They settled level on the road
(z ≈ 20, pitch ≈ 0.3°) and stayed put.

`BP_RGC_Bee` was driven by `Test/BPC_RGC_DriveTest`, a scripted throttle/steer
component that is test-only and not used by any car:

- **Throttle:** a straight run reached ≈ 67 km/h in 2.5 s, holding heading within 0.1°.
  A longer earlier run hit ≈ 136 km/h by 4.3 s.
- **Steering:** +0.7 right turned yaw steadily from 10° to 77°; −0.6 left turned it left.
- **Collision:** steering into the right barrier, the car hit it, bounced back onto
  the road and stopped; it never went through. Hitting Turn 1's outer barrier at full
  speed with no steering threw it about 4 m up, then it landed back on the track.
- **Brake / handbrake:** the car stops and holds.

Only the Bee was driven. The other six share the identical physics setup and differ
only in mass and visual meshes.

## Using them

- Drop any `BP_RGC_*` into a level and set **Auto Possess Player = Player 0** to drive it.
- Or set a game mode's *Default Pawn Class* to one of them. This was not done here,
  so existing gameplay is unchanged.
- The existing ability cars (`BP_HoneyBeeVehicle`, `BP_AntCarVehicle`) are separate.
  The new Bee/Ant karts are cosmetic racing versions without abilities.

## Regenerating

```
cd SourceArt/RacingGame
python gen_bugcars.py [Name ...]   # writes obj_cars/SM_RGC_<Name>_Body/_Wheel.obj
python preview_cars.py             # offline turntable-style preview -> cars_preview.png
```

Reimport the OBJ over the matching asset (slot names: Paint, Trim, Accent, Shell,
ShellStripe, Wing, Sting, EyeWhite, EyePupil, EyeRed, Rim, Tyre, Hub), then remove the
auto-generated collision.

## Bee Racer (imported from Blender, 2026-10-16)

`BeeRacer/BP_RGC_BeeRacer` uses the user's model `Documents/BeeRacer_3D/Bee_Racer.blend`.
It is a duplicate of `BP_RGC_Bee` (same physics, mass 1400 kg) with `SM_RGC_BeeRacer_Body`
and `SM_RGC_BeeRacer_Wheel`. Its materials are `MI_RGC_BeeRacer_*`, built from the Blender
material colours; the tyres use the shared `MI_RGC_Tyre`.

Re-export after editing the .blend:
```
D:\blender.exe -b <Bee_Racer.blend> --python export_beeracer.py -- D:/newwgame/BBB/SourceArt/RacingGame/obj_cars
```
The model is scaled per axis so its wheel hubs land on the template's (length x0.874,
width x0.968, height x0.830). The car comes out about 433 x 262 x 152 cm, including the wings.
Simulate test on Lvl_GardenGrandPrix: it settled at z ≈ 20 and drove and turned exactly like
`BP_RGC_Bee` under `BPC_RGC_DriveTest`.

### F1-style handling (2026-10-16)
The Bee Racer has its own wheel classes, `BeeRacer/BP_RGC_BeeRacer_WheelFront/Rear`. They are copies of
the SportsCar wheels, so the template and the other karts are unchanged.
- **Wheels:** cornering stiffness 1800, friction 4.5 front / 5 rear, front lock 32°,
  springs 420 with 6 cm travel, damping 0.6, rollbar 0.6, brakes 6500 front / 3500 rear.
- **Movement:** mass 900 kg, downforce 2.5, linear steering input (rise 7 / fall 10),
  steering-vs-speed curve 1.0@0 → 0.9@40 → 0.6@100 → 0.42@180 → 0.32@300 km/h,
  torque 900, rev-up MOI 2.5, gear change 0.04 s at 6600 rpm.
- **Test against BP_RGC_Bee (same scripted inputs):** straight-line launch was equal; both
  launches are limited by grip. Into Turn 1 it turned sharper (yaw 70° vs 64°), carried
  about twice the distance through the corner, and stayed flat (roll under 8° on barrier contact).

### Corner retune (2026-10-30)
On request ("driving is not good for the game, test it at the corners"), the shared wheel classes and the
movement component of all four racers (Bee, Ant, Spider, Snail) were retuned. The values above are the old ones.
- **Wheels:** friction 6.0 front / 7.0 rear (rear grippier, so the car pushes wide instead of spinning),
  cornering stiffness 2600, ABS on all wheels, traction control on the rear.
- **Movement:** centre of mass override z −30, downforce 4.0, drag 0.6, torque 700 (top speed ≈ 195 km/h,
  was ≈ 214), steering-vs-speed 1.0@0 → 0.95@40 → 0.75@100 → 0.6@180 → 0.5@300 km/h.
- A low-friction body material was also tried. It made cars ride up and over the barriers, so it was removed.
- Placed racers keep their own copy of the movement settings: after changing the BP, copy the values onto
  placed instances (`BeeRacer_Player` was updated). `reset_properties` resets to the native C++ defaults
  (300 Nm etc.), not the BP values.

Test: `Test/BPC_RGC_AutoPilot` (test-only, from `gen_autopilot.py`) drives an unpossessed racer round
the centreline with pure-pursuit steering. It brakes for each corner so the cornering force stays under
`LatG` (in g), and logs telemetry. Summarise the last Simulate run with `python parse_autopilot.py`.
Bee Racer from waypoint 10, Simulate:

| Driver (`LatG`) | Before | After |
|---|---|---|
| Careful (1.0) | 93.9 s lap, clean | — |
| Aggressive (2.5) | — | 58.5 s lap, slip ≤ 2.2°, no wall hits |
| Overshooting (3.5) | — | 51.1 s lap, slip ≤ 1.6°, no wall hits |
| At the grip limit (5.0) | — | 48.6 s lap, runs wide (≤ 10.8 m of 12 m), slip ≤ 4.2°, no spins |
| Full throttle, never brakes (99) | 212 km/h into T1, spun 180° at T1 and T3, stuck at T3 | lap completed in 58 s; spins only at T1/T5/T8/T11 after hitting the wall at 165–190 km/h |

The editor drops to about 3 fps when it is in the background. Physics then runs in slow motion, and
`parse_autopilot.py` warns about it. Keep *Use Less CPU when in Background* off while testing.

## Ant Racer and Spider Racer (imported from Blender, 2026-10-17)

| Car | Blueprint | Source |
|---|---|---|
| Ant Racer | `AntRacer/BP_RGC_AntRacer` | `Documents/AntCar_3D/Ant_Car.blend` |
| Spider Racer | `SpiderRacer/BP_RGC_SpiderRacer` | `Documents/SpiderCar_3D/Spider_Car.blend` |
| Snail Racer (2026-10-22) | `SnailRacer/BP_RGC_SnailRacer` | `Documents/SnailCar_3D/Snail_Car.blend` |

Both are duplicates of `BP_RGC_BeeRacer`, so they share its F1 handling: the same
`BeeRacer/BP_RGC_BeeRacer_WheelFront/Rear` classes, mass 900 kg and downforce 2.5. Changing those wheel
classes changes all three cars. Their materials (`MI_RGC_<Car>_*`) are built from the Blender material colours;
the tyres use the shared `MI_RGC_Tyre`. The Ant's always-on nitro flame meshes are not exported.

Exporter (works for any of the user's cars that follow the same layout: front = -Y, four wheel empties):
```
D:\blender.exe -b <Car.blend> --python export_blendcar.py -- D:/newwgame/BBB/SourceArt/RacingGame/obj_cars <Name> <Root> <WheelPrefix> <TireFR> <RimFR> [exclude_regex]
# Spider: SpiderRacer SpiderCar_Root Wheel_ Tyre_FR Rim_FR
# Ant:    AntRacer AntCar_Root Ant_Wheel_ Ant_Tire_FR Ant_Rim_FR "^Nitro_Flame"
# Snail:  SnailRacer SnailCar_Root Wheel_ Tyre_FR Rim_FR
```
It reads the hub positions and tyre radius from the file, scales each axis so the hubs land on the template's,
lowers the resolution of thin bevelled curves (pinstripes, LED piping) in that session only, and writes the body
and wheel OBJs plus `SM_RGC_<Name>_materials.json`. Spider body ≈ 156k triangles, Ant ≈ 103k, Snail ≈ 153k.
It also caps subdivision at 1 level (0 on meshes over 8k faces; the Snail shell would otherwise be 147k triangles).
Procedural colours are approximated: a ColorRamp over Object Z (the Snail body's cream-to-green gradient) is split
into 5 height bands (`<Mat>_Z0..Z4` slots and `MI_RGC_<Car>_<Mat>_Z0..Z4`), and a Mix of colours (the Snail shell's
amber noise) uses the average colour.
The Snail Racer is a duplicate of `BP_RGC_SpiderRacer`, so it has the same F1 handling, camera and empty Drift component.

Drive test (Simulate, `Test/BPC_RGC_DriveTest`, same start slot, editor at 60 fps): all three end within about
1 m of each other after the straight and the right turn — Bee (1741, 12184) yaw 96°, Ant (1686, 12183) yaw 91°,
Spider (1660, 12184) yaw 103° — and stay upright (roll < 1°). Note: when the editor window is not focused it
throttles to 3 fps, and Chaos vehicles then barely move. Turn off *Editor Preferences > Performance > Use Less
CPU when in Background* while running scripted tests.

## Car switcher (I / O / P / U)

`Vehicles/BP_RGC_CarSwitcher` is placed in `Lvl_GardenGrandPrix` as `CarSwitcher`. Each tick it checks
I (Bee), O (Ant), P (Spider), U (Snail). If a different car is chosen, it stores the current car's position, heading
and velocity, turns the old car's collision off and moves it away, destroys it, spawns the new car 60 cm higher with
the same heading, possesses it and gives it the old velocity. Setting its `RequestedCar` variable to 1/2/3/4 does the
same, which is handy for menus or tests. The graph source is `car_switcher.dsl` (the 3-car version is in `Saved/car_switcher_backup_3cars.dsl`).
PIE test 2026-10-22: with `RequestedCar` = 4 the Bee Racer was replaced by the Snail Racer, which sat level on the
road and was possessed by the player. Drop the actor into any other map
to get the same keys there.

## Drift and speed cap (removed 2026-10-17)

Both the drift and the 120 km/h speed cap were removed on user request. The cars now use their normal handling
and top speed: stock handbrake, base wheel friction (front 4.5, rear 5) from the wheel classes.
`Vehicles/Shared/BPC_RGC_Drift` is still attached as the `Drift` component on the Bee/Ant/Spider racers, but its
graph is empty, so it does nothing. The old graph is backed up in `Saved/drift_withdrift_backup.dsl`.


## Camera (Smash Karts style, 2026-10-17)

On request, the Bee/Ant/Spider racers now use a high top-down chase camera like Smash Karts. I set it on each BP's
`BackSpringArm` and `BackCamera` components:
- BackSpringArm: TargetArmLength 1000, pitch -45, z 75, SocketOffset 0, CameraLagSpeed 8, CameraRotationLagSpeed 4
  (inherits yaw only, so the view stays level on bumps).
- BackCamera: location/rotation 0, FOV 70.
- Old values: arm 381, pitch 0, SocketOffset z 71.8, lag 10/2; camera at (-280, 0, 110), pitch -10, FOV 80.
- Tuning: increase TargetArmLength to zoom out, and set pitch closer to -60 for a more overhead view or closer to -30 for a flatter one.
