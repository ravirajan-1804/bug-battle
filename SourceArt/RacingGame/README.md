# Garden Grand Prix — `Lvl_GardenGrandPrix`

A miniature-garden racing circuit for BugBattle (UE 5.8). Everything new lives in
`/Game/RacingGame/` and `SourceArt/RacingGame/`. No existing map, mesh, material,
Blueprint or config file was modified. Existing BugBattle meshes and material
instances are only *referenced*.

## Open & test

1. Open `Content/RacingGame/Maps/Lvl_GardenGrandPrix`.
2. Press **Play**. The map keeps the arena's World Settings game mode
   (`BP_VehicleAdvGameMode`), so the existing vehicle pawn spawns on one of the
   seven grid slots behind the start line.
3. Drive east down the start/finish straight. The lap runs counter-clockwise (all
   main corners are left-handers).

The map is not referenced by `GameDefaultMap` or any menu. Open it directly.

## v5: Losail layout (2026-10-17)

On request, the circuit was redesigned to follow the Losail (Qatar) track from the user's screenshot
(`ref/losail_ref.png`). The traced centreline is in `ref/losail_trace.py`; `ref/trace_overlay.py` draws it over the
picture (`ref/overlay.png`). Hairpins are traced as arcs so the 24 m road never folds on the inside.

| Item | Value |
|---|---|
| Lap length | ≈ 157,100 cm (1,571 m); 480 cm per reference pixel (`LAYOUT_SCALE`) |
| Road width | 2,400 cm incl. kerbs, barriers unchanged |
| Tightest corner | ≈ 1,500 cm centreline radius (the chicane on the west side); hairpins ≈ 1,800–1,900 |
| Closest legs | ≈ 38 m centre to centre (the hairpin legs), about 14 m of verge between barriers |
| Elevation / banking | flat (like Losail); 5° banking in corners, flat start/finish straight |
| Environment | `ENV_SCALE` 1.45: fence ring r ≈ 26,100, ground and background scatter scaled to match |
| Start | south straight, driven east; start line at reference px (40, 67), 7 grid slots behind it |

Removed in v5: the shortcut, the two-way split, both tunnels and the hollow log, since Losail has none
(their actors were deleted; the meshes `SM_RG_Shortcut`, `SM_RG_LogTunnel`, `SM_RG_AltRoute`, `SM_RG_Tunnel_*` and
`SM_RG_Verge_SC/BR` are still in the content folder, unused). The v4 sources, OBJs and placements are backed up in
`Saved/RG_backup_v4`. Corner chevrons sit outside Turn 1, both hairpins and the chicane. Root arches span
the north-east straight and the long right-hand sweep.

**Tunnels + start glow (2026-10-17, later):** two hollow-log tunnels (`SM_RG_Tunnel_A` over the north-east corner,
lap fraction 0.325–0.386, actor `Tunnel_NE`; `SM_RG_Tunnel_B` over the long west corner, 0.745–0.822, actor
`Tunnel_West`; `TUNNELS` in `gen_grandprix.py`). They have no collision, since the road barriers still run inside.
Props and grass are kept out of the shells. The root arch moved to the east straight (px 79.5, 46). Start glow: 5 red
point lights under the start gantry (`StartLight_1..5`) and a warm light in each grid lantern (`LanternLight_*`),
all Movable without shadows, in `Track/Lighting/StartGlow`. Tuned after the user said the light looked bad (it
washed the grid out white): 5 red lights at intensity 1500 a few metres in front of the gantry, 12 lantern
lights at 700 (radius 1000), `MI_RG_LampRed` emissive (5, 0.02, 0.01), `MI_RG_LampWarm` (20, 11, 3.5). The arch
`top` was raised from 1250 to 2300 cm so the gantry sits above the high chase camera. ISM actors now sit at z = −50,000 with their instances raised by the same amount and one spare identity
instance at the end, because the editor resets the last instance to identity (this had put a tomato plant in the
middle of the road at the world origin).

The rest of this README describes v4 and is kept for reference.

## Layout (UE units, 1 uu = 1 cm)

| Item | Value |
|---|---|
| Lap length | ≈ 100,800 cm (1,008 m) — layout scaled ×1.4 (`LAYOUT_SCALE` in `trackdef.py`) |
| Footprint | outermost road edge ≈ 17,700 from centre; backyard fence scaled ×1.3 (r ≈ 23,400), ground/background scaled with `ENV_SCALE` |
| Road width | 2,400 cm incl. kerbs (v1 1,600, v2 1,900; cars are ≈ 470 × 230 cm) |
| Barriers | 90 cm tall, 50 cm thick, red/white blocks with a steel cap |
| Start/finish straight | ≈ 16,800 cm, flat, with centre lane dashes |
| Turn 1 | ≈ 4,900–8,100 cm radius, banked up to 15° (pivot on the inner edge) |
| Tightest corner | ≈ 2,350 cm radius |
| Elevation | 0 → ≈ 450 cm crest through the garden passage / NE corner, back to 0 |
| Shortcut | 1,400 cm wide, ≈ 14,900 cm long vs ≈ 16,500 cm of main road it bypasses |
| Two-way split (W) | tunnel route 1,800 cm wide, ≈ 9,400 cm, vs ≈ 13,500 cm of main road sweeping round the outside (≈ 30% shorter, the fast line) |
| Tunnels | north straight (≈ 60 m, roof ≈ 22 m), tunnel route (≈ 36 m, roof ≈ 17 m), hollow log on the shortcut |

Sections, in driving order:

- **A** Starting grid: 7 staggered boxes (2 wide, 520 cm apart), tally-bar slot
  numbers, checkered start/finish band. PlayerStarts `GridSlot_1..7` sit on the boxes.
- **B** High-speed straight: lane dashes, flag banners, bunting, lanterns.
- **C** Turn 1: big banked left-hander.
- **D** Garden passage: S-bend through giant flowers under a gnarled root arch.
- **F** Shortcut: splits right after Turn 1 (gore chevrons and glowing toadstools
  mark it). It runs on a clay surface with yellow/black kerbs through a hollow log
  with glowing fungus, then rejoins before the NE corner.
- NE corner, a root arch, then the north straight through a giant hollow-log tunnel.
- **E** Technical section: medium left, tight right (chevron boards), broad left exit.
- **W** Two-way split on the west side: the open-air main line sweeps wide round the
  outside; the tunnel route cuts almost straight through a log tunnel and is ~30% shorter
  (gore chevrons + glow mushrooms mark the fork). Both rejoin before the final corner.
- Final corner.
- **H** Final straight: lantern-lined run back to the finish arch. Two giant
  grass-stem pillars hold a checkered banner with a 5-light start gantry under it.

## Content

```
/Game/RacingGame/
  Maps/Lvl_GardenGrandPrix
  Meshes/   SM_RG_Road_00..09, SM_RG_Shortcut, SM_RG_LogTunnel, SM_RG_GridMarkings,
            SM_RG_Ground_00..33, SM_RG_Verge_00..09 + _SC, SM_RG_FinishArch,
            SM_RG_FlagBanner, SM_RG_Bunting, SM_RG_Lantern, SM_RG_ChevronBoard,
            SM_RG_RootArch, SM_RG_GroundRoot, SM_RG_FallenLeaf_A/B, SM_RG_SeedPod,
            SM_RG_GlowMushrooms
  Materials/ MI_RG_* (children of the existing M_BB_Surface / M_BB_Foliage)
```

Outliner folders: `Track/Road`, `Track/Shortcut`, `Track/StartFinish`, `Track/Banners`,
`Track/Lighting`, `Track/Signs`, `Environment/...`, `Gameplay/StartGrid`, `Lighting`.

## Collision & performance

- Road chunks, shortcut and ground use **complex-as-simple** collision. Barriers are
  part of the road mesh, so cars are contained everywhere except the two shortcut
  openings, which are intentional.
- All decorative meshes have **no collision**: they sit outside the barriers.
- Repeated scenery (flowers, mushrooms, pebbles, clover, acorns, lanterns, flags…)
  uses **InstancedStaticMeshComponents**, one `ISM_*` actor per mesh: 39 actors
  holding about 460 instances, all set to NoCollision.
- The giant grass verges are pre-batched meshes (10 chunks along the lap, ≈ 16k
  triangles each, Nanite enabled). The ground is 16 tiles (Nanite).
- The map has about 100 actors in total. No physics simulation runs on scenery.

## Verification

v3/v4 (bigger/wider, split + tunnels, faster tunnel route, 2026-10-14): 525 downward probes on main road, shortcut and
alternate route all hit a driving surface (branch junction probes land on the main road plane as
designed). Banked lateral probes hit the barrier at the road half-width everywhere except the
branch openings. Tunnel roofs: ≈ 21.5–22.5 m over the main road, ≈ 17–17.6 m over the tunnel
route. Scatter props are placed against their real (rotated, scaled) mesh footprint, so no
foliage overhangs any road.

v2 (wider/longer layout, 2026-10-14): 253 downward probes on the main road (centre and ±850 cm) and
shortcut all hit the surface within 20 cm, except one shortcut point under an overhanging
grass blade (visual only, verges have no simple collision). 261 of 264 banked lateral probes hit
the barrier at exactly 950 cm from centre; the other 3 are the shortcut openings. The v1
numbers below are kept for reference.


- **Collision sweep (editor traces):** 651 probes on the main road (centre ±600 cm)
  all hit the surface within 13 cm, i.e. kerb height. 138 lateral barrier probes
  all hit at exactly 800 cm from centre, except the two shortcut openings. Every
  1 m along the shortcut (centre and ±400 cm) hit a surface, with a worst
  metre-to-metre height change of 13.6 cm.
- **Shortcut junctions:** the shortcut surface is snapped per-vertex onto the main
  road plane (10 cm below it), so nothing pokes through. The step at the main road
  edge is ≤ 10 cm.
- **PIE:** the existing vehicle spawned on a grid slot and came to rest level on
  the road (z ≈ 39, pitch ≈ −1°). The chase camera has a clear view of the grid,
  arch and lights.
- **Not tested:** a full driven lap, lap timing, multiplayer and profiling.
  Automated input/driving isn't available through the editor tools used here.
  Drive a lap and run `stat unit` / `stat gpu` to confirm handling and frame time.

## Not included (by request: map/environment only)

Pickups, abilities, checkpoints/lap logic, start-light sequencing and character
assignment are not implemented. The start lights are static emissive lamps.
Suggested hook points:

- start-light BP over `FinishArch_StartLights`
- checkpoint volumes at section boundaries; keep one outside the shortcut span
  (e.g. in the garden passage) so it cannot skip required checkpoints
- pickups on the straights and the passage, using the `Gameplay/` outliner folder

## Regenerating geometry

Track and props are procedural (Python + numpy, reusing `SourceArt/BugBattle/meshlib.py`):

```
cd SourceArt/RacingGame
python trackdef.py          # prints lap stats, writes layout.png (top-down preview)
python gen_grandprix.py     # writes obj/*.obj and placements.json
```

`trackdef.py` holds the control points (`MAIN_PTS`, `SC_PTS`), elevation keys and bank
zones. After editing, regenerate, reimport the changed OBJs over the `SM_RG_*` assets,
and rebuild the `ISM_*` actors from `placements.json`. Before reimporting, remove the
auto-generated collision; road, shortcut and ground also need `CollisionTraceFlag =
UseComplexAsSimple`.

## Minimap HUD (2026-10-19)

`/Game/RacingGame/UI/WBP_RG_Minimap` is a 300 × 220 minimap pinned 24 units from the bottom-left corner. It is
drawn entirely in `OnPaint` (no textures). The style is neutral and has no panel, frame or title (v2, after the
user asked for a neater look without blue or yellow). It shows the real track centreline (`trackdef.Track`, every
6th sample) as a white line with a black outline and a soft drop shadow, a checkered start/finish band with a green
direction chevron, and a dark "START / FINISH" tag. Each other racer is a coloured dot with a white rim. The local
car is a colour-filled arrow with a white rim and a halo ring that follows its position and heading every frame.

- **Integration:** `UI_Vehicle` (the existing vehicle HUD) got an `Event Construct` that creates the minimap,
  stores it in `RaceMinimap` and calls `AttachToHud(speedLabel)`. `AttachToHud` returns early on any level other than
  `Lvl_GardenGrandPrix`, climbs to the HUD's root panel (an Overlay) and adds itself as a full-size child. Tick
  places it in the corner with a render translation and measures `PixelScale`, because Slate scales line positions
  by DPI but not line thickness. A backup of the original `UI_Vehicle.uasset` is in `Saved/RG_backup_minimap`.
- **Racers:** every `WheeledVehiclePawn` that has a PlayerState or a Controller, except your own car, gets a diamond.
  Colour = `RacerColors[PlayerId % 7]` (red, orange, green, pink, purple, teal-green, coral; no blue or yellow), so all clients agree. Your
  arrow uses your own slot colour. Unpossessed parked cars are not shown.
- **Regenerate after a track change:** `python gen_minimap.py && python minimap_dsl.py`, then write
  `Saved/RacingGame/minimap_onpaint.txt` into the `OnPaint` graph (delete its nodes first) and set `TrackPoints`,
  `TrackShadow`, `MapScale`, `MapOffset`, `RacerColors` on the CDO from `minimap_defaults.json`.
- **Tested in PIE (single player):** the minimap shows bottom-left, and teleporting the car to two places on the
  track moved the arrow to the matching spot with the right heading. Multiplayer markers have not been tested in a
  real network session.

## Start/finish lane dashes fixed (2026-10-19)

The centre dashes on the start/finish straight used to be picked per centreline sample (`(i*step) % 700 < step`).
Because the step is 100.005 cm and not exactly 100, some dashes merged into long ones or dropped out, and they also
ran through the starting grid. `gen_markings` now places 3 m dashes every 7 m by exact arc length, starting 4 m past
the line, and leaves the grid clear (from the line back to about 9 m behind the last grid box). Regenerated with
`python gen_grandprix.py marks` (placements.json unchanged) and reimported `SM_RG_GridMarkings` (same slots and
materials, no collision). The old OBJ is in `Saved/RG_backup_dashes`.

## Cinematic race intro (2026-10-30)

Pressing Play on `Lvl_GardenGrandPrix` runs a cinematic 3-2-1-GO intro, with no menu. `RaceManager` (a
`BP_RG_RaceManager` in the `Gameplay` outliner folder) creates `WBP_RG_StartLights` for the local player at BeginPlay.
The manager was not in the level before this, so its off-track respawn is now live too.

| Time after IntroStart | Number | Camera (`intro_shots.py`) | Sound |
|---|---|---|---|
| −1.0 to 0 | (lamps dark) | first frame of shot 3 | |
| 0 to 1.6 | 3 (red) | low close-up from the left kerb, sliding towards the pole car over the start line | hit + engine idle |
| 1.6 to 3.2 | 2 (yellow) | high crane over the grass: grid, gantry and garden | hit |
| 3.2 to 4.8 | 1 (green) | head-on telephoto at car height, pushing in on the grid | hit + engine revs + riser |
| 4.8 | GO! | 0.75 s arc up and around the player's car to its active camera, then a 0.6 s ease blend into it | GO hit + whoosh + launch |

- **Cars** are held (input off, handbrake on) until GO, then released. The race timer starts at GO and stays at the
  top centre (`TIME m:ss.cc`). Letterbox bars close the intro and slide away over 0.9 s after GO. The lights and "GO!"
  hide 1.8 s after GO. The five gantry point lights (tag `RG_StartLight`) turn red, yellow, then green with the lamps.
- **Multiplayer:** the server sets `IntroStart` (server time + 1 s) once. It is a replicated variable on the
  replicated, always-relevant RaceManager. Every client runs the whole timeline from
  `GameState.ServerWorldTimeSeconds − IntroStart`, so all players see the same number and are released together.
  Each client spawns its own local `CameraActor`. The log prints `RG_INTRO GO at server time …` on every machine.
- **Sounds** are generated by `gen_intro_audio.py` (`--install` copies the WAVs into `Content/RacingGame/Audio`,
  where the editor auto-imports them as `SW_RG_*`).
- **Regenerate:** `python gen_racemanager.py`. Then, in each graph, delete every node except the events and
  function entry/result, and write `Saved/RacingGame/racemanager.txt` (RaceManager EventGraph),
  `startlights_tick.txt` (widget EventGraph) and `startlights_onpaint.txt` (widget `OnPaint`). The graphs from
  before the intro are in `Saved/RacingGame/backup_intro_*.txt`.
- **Tested in PIE:** in single player, all three shots, the swoop, the hand-off and the timer were checked with
  screenshots, and GO comes 5.8 s after BeginPlay. A 2-player listen-server session gave GO on the client and the
  server two frames apart, and both timers showed the same time. In that session the client's own car (the game
  mode's default `BP_AntCarVehicle`) showed 99 km/h on the client while the server had it parked. That happens
  without the intro too, so it is an existing multiplayer issue.

## VSM non-Nanite marking overflow fixed (2026-10-30)

`[VSM] Non-Nanite Marking Job Queue overflow` was logged at the start of every Play session. The cause was the
non-Nanite geometry covering the directional light's virtual shadow map: the 10 road chunks (70–160 m each),
`SM_RG_GridMarkings` (270 m), `SM_RG_FinishArch` and the meshes behind the 39 instanced scenery actors (about 790
instances of 38–85 m flowers, grass, mushrooms, pebbles, lanterns, banners and so on). All of them render through the
per-instance non-Nanite path into every shadow page they cover. The ground, verges, fence and tunnels were already
Nanite. The 17 point lights don't cast shadows, so they weren't part of it.

**Fix:** Nanite was enabled on those 44 meshes. Every material is opaque (`M_BB_Surface`, `M_BB_Foliage` two-sided
foliage, `M_GardenGround`) and none uses World Position Offset, so Nanite renders them the same and their shadow pages
stay cached. `bUsedWithNanite` is now set and saved on those three base materials, so packaged builds don't fall back
to the default material.
- Each mesh uses Nanite fallback `PercentTriangles` 100 %, so the fallback mesh (used for complex collision) is the
  full mesh. 1,965 traces along the track (surface at the centre and ±8 m, plus both barriers at every 4 m waypoint)
  matched within 0.5 cm before and after. The one changed trace had hit the parked pole car, not the track.
- Nothing was deleted, hidden, moved or turned off. No shadow, light or cull-distance settings and no cvars were
  changed.
- The original Nanite settings of the 44 meshes are in `Saved/RacingGame/perf_nanite_backup.json`.
- The flower, grass, mushroom and pebble meshes are shared BugBattle assets (`/Game/BugBattle/...`), so the arena maps
  use them as Nanite too.

**Verified in PIE:** the warning went from 1 per run to 0 in two runs, with no other warnings. Screenshots of the
intro shots and the gameplay view look the same before and after. The editor frame rate stayed at 40–44 fps; that
number is set by editor overhead, and the tools can't read GPU timings, so the shadow-pass saving isn't measured here.

## HUD skin v4: minimap, speedometer, KM/H and gear (2026-10-30)

The user asked to make the existing minimap, speedometer, KM/H text and gear indicator look modern and premium (Forza
Horizon / Disney Speedstorm style). They asked for visuals only: same screen positions, no new features, no gameplay,
physics or camera changes. `UI_Vehicle` is untouched. Everything lives in `WBP_RG_Minimap`, which `UI_Vehicle` already
creates on `Lvl_GardenGrandPrix`.

- **Theme:** dark translucent glass, white Roboto Bold Italic numerals, hot-pink accent `(1, 0.05, 0.35)` (still no blue
  or yellow), orange-red for the redline and for reverse.
- **UI materials** (`hud_materials.py`, one Custom HLSL node each, anti-aliased with `fwidth`):
  - `M_RG_HUD_Panel`: rounded glass plate with a drop shadow, rim light, faint racing stripes, and an accent bar with a
    slow shimmer.
  - `M_RG_HUD_Gauge`: 240° speed dial with a glass disc, a dim track, a redline zone, ticks, and a lit arc that goes
    white → pink → red, with a glow, a bright leading head and a pulse in the redline.
  - `M_RG_HUD_Badge`: gear disc with a ring in the gear colour, a slowly rotating sheen, and a pop glow on gear change.
- **Data through the tint:** animated values come in through the Image tint, so there are no dynamic material
  instances. Slate multiplies a UI material's output by the tint, so each material divides the tint back out (`END` in
  `hud_materials.py`).
  - Dial: `tint.r` = 0.5 + 0.5 × speed fill, `tint.g` = 0.5 + 0.5 × redline pulse, `tint.b` = `tint.a` = 1 (no zero
    channels).
  - Badge: `tint.rgb` = gear colour, `tint.a` = 0.5 + 0.5 × pop.
- **AttachToHud:**
  1. Creates the map plate, dial and badge Images in the HUD's root Overlay *before* adding the widget itself, so its
     OnPaint text draws on top. The dial and badge start collapsed.
  2. Finds the labels from the `SpeedLabel` that `UI_Vehicle` passes in. The unit label is child 1 of the speed box. The
     gear box is found by scanning the speed row for the panel whose first child is a TextBlock.
  3. Only once the labels are found: fades the two original boxes to opacity 0.004, shows the dial and badge, and sets
     `SpeedoReady`.
  - DSL casts are exec casts, so a failed cast silently ends the chain. That is why the map is attached first.
  - The boxes go to 0.004, not 0, because Slate skips painting a widget at opacity 0. The labels keep updating through
    `UpdateSpeed` / `UpdateGear`.
- **Tick:**
  - Positions: the labels report their size but no position (identity transform in cached and paint-space geometry),
    so the centres come from `UI_Vehicle`'s fixed layout (row anchored bottom-right, 32 padding, 16 slot padding) plus
    the measured sizes of the HUD root, the row, the boxes and the labels. The dial (210 × 210) is centred on the speed
    number and the badge (92 × 92) on the gear number (4 left, 6 down).
  - Values: copies the label text and fills the dial from the displayed number (0–200 km/h, or 0–125 if the unit reads
    MPH, smoothed). The badge is red for R, grey for N and pink otherwise, and pops when the gear changes.
- **OnPaint:**
  - Map: shadow, dark outline, light road, a checkered start line, a pink direction chevron, racer dots, and your arrow
    with a breathing halo. The START / FINISH tag was removed to declutter it. The map sits on a 352 × 272 panel Image.
  - Text: speed (42 pt), unit (12 pt, pink), gear (30 pt) and "GEAR" (10 pt).
  - 123 paint nodes in total. The earlier v3 draft drew panels and the dial with thousands of DrawLine nodes, and
    writing that graph hung the editor.
- **Regenerate:**
  1. Run `python minimap_dsl.py`.
  2. Delete every non-event node in `OnPaint`, `AttachToHud` and `EventGraph`.
  3. Write `Saved/RacingGame/minimap_{onpaint,attach,tick}.txt` into those graphs.
  4. For material tweaks, write each `SPECS` code string into `<Material>:MaterialExpressionCustom_0.code` and
     recompile. To rebuild a material from scratch, paste `hud_materials.py` into `execute_tool_script`.
- **Tested:** in Play (floating window) with no log errors. A run with the speed forced to 150 km/h checked the lit
  arc. Not yet seen while actually driving (the real fill, gear changes, reverse).
- **Backup** of the pre-v4 widget, HUD and generator: `Saved/RG_backup_hud_v4`.

## HUD v5: cyan radar minimap + semicircular speedometer (2026-11-01)

The user asked for a premium futuristic racing HUD: a circular, rotating minimap at the bottom-left and a large
semicircular digital speedometer at the bottom-right, in cyan / electric blue / white neon on dark glass, driven only
by real gameplay values. Gameplay, vehicle physics and cameras are untouched. `UI_Vehicle` is untouched too: it still
creates `WBP_RG_Minimap` on `Lvl_GardenGrandPrix`, and its own speed and gear boxes are hidden (opacity 0).

- **Generators:** `hud5_dsl.py` (all graphs, offline turn / checkpoint / finish data from `trackdef.py`) and
  `hud5_materials.py` (paste body for `execute_tool_script`; builds `M_RG_HUD_Radar` and `M_RG_HUD_Speedo`).
- **Live data:**
  - Track line: `BP_RG_RaceManager.TrackPts` read from the placed actor at runtime (`InitMap`, every 2nd point = 8 m).
    The circuit is fitted into the radar and rotated about its centre so your heading points up (smoothed heading).
  - Lap progress: nearest centreline point; start line -> you is cyan, the rest of the lap white. It only counts after
    you cross the start line (the grid is behind it) and resets if you reverse back over it.
  - Racers: every `WheeledVehiclePawn` with a PlayerState or Controller (your car is the cyan arrow).
  - Speedometer (`ReadCar`): `GetForwardSpeed` (km/h), `GetCurrentGear` (R / N / 1..), `GetEngineRotationSpeed` /
    `GetEngineMaxRotationSpeed` (RPM arc + number), `GetThrottleInput` (ACCEL bar), measured acceleration (3 chevrons).
  - BOOST: the cars have no nitro mechanic, so BOOST / TURBO shows turbo pressure derived from real throttle x RPM
    (spools with lag; IDLE / SPOOL / TURBO). If a real boost system is added later, feed it into `Boost` in `ReadCar`.
  - Material values go through dynamic material instances (`Widget|Brush|GetDynamicMaterial` on a `TmpBrush` variable,
    then `InitializeScalarParameterAndGetIndex` every tick), so they are exact floats (the v4 tint trick was 8-bit).
- **Map markers:** 12 turn numbers (corners > 20° from the curvature of `trackdef`), two electric-blue checkpoint bars
  at 1/3 and 2/3 of the lap (sector splits; there is no checkpoint gameplay system), a checkered finish line, compass N
  (world +X) and a bezel that turns with the map. There are no shortcuts on the current layout (removed in v5 Losail).
- **Layout:** 40 units from the screen edges; radar 336 x 336 image (glass radius 150), speedometer 460 x 292.
- **Regenerate:** `python hud5_dsl.py`; delete non-event nodes of `OnPaint`, `AttachToHud`, `EventGraph`, `InitMap`,
  `UpdateMap`, `ReadCar`; write `Saved/RacingGame/hud5_*.txt` into them (writing OnPaint takes a few minutes).
- **Backup** of the v4 widget, materials and generators: `Saved/RG_backup_hud_v5`.

## HUD v6: Pixar / toy style + hidden during the intro (2026-11-01)

The user said the cyan sci-fi look did not fit the garden map and asked for a "Pixar type" minimap and speedometer,
hidden during the 3-2-1 cinematic. Same generators (`hud5_dsl.py`, `hud5_materials.py`), same data and positions.

- **Look:** warm toy palette with thick dark-brown ink outlines and soft drop shadows. The radar is a mown-lawn disc
  whose stripes turn with the map, with a cream bezel, ink tick dots and a red N badge. The road is drawn as asphalt
  with a white border, the lap progress is orange, and checkpoints are red-and-white bars. Your car is a red arrow
  with a white rim; opponents are bright bubbly dots. The speedometer is a cream dashboard with chunky yellow ->
  orange -> red segments, a red pointer, an RPM arc, a red gear roundel, a TURBO pill and ACCEL / BOOST bars.
  Numbers are white with ink outlines.
- **Material update without re-creating the assets:** write the code from `Saved/RacingGame/hud6_{radar,speedo}.txt`
  into `<Material>:MaterialExpressionCustom_0.code`, then recompile (deleting the assets would break the widget's
  references).
- **Intro:** Tick computes `HudAlpha` = clamp((server time - RaceManager.IntroStart - 6.15 s) / 0.5 s). 6.15 s =
  GO (3 x 1.6 s) + swoop 0.75 s + camera blend 0.6 s. It drives the render opacity of the widget and both images.
  Render opacity alone does not stop OnPaint, so OnPaint's two blocks check `ShowSpeedo` / `ShowMap`
  (HaveCar / MapInit and HudAlpha > 0.01).
- **Cyan v5 sources:** `Saved/RG_backup_hud_v5/hud5_*_cyan.py`.

## 3-lap race with 5 AI bots + scoreboard (2026-11-01)

The user asked for 5 AI bots racing the player over 3 laps from GO, with a Pixar-style scoreboard top-left showing
places 1-6. Generator: `gen_race.py` (writes the DSL, `race_defaults.json` and the `M_RG_HUD_Board` HLSL).

- **Bots** (`BP_RG_RaceManager.SpawnBots`, server, BeginPlay): Buzzy Bee (BeeRacer), Andy Ant (AntRacer), Shelly
  Snail (SnailRacer), Bruno Beetle (Beetle) and Flutter (Butterfly) on grid slots 2-6 behind the player's pole car.
  Each gets an AIController (`SpawnDefaultController`), `SetRequiresControllerforInputs false` and a
  `BPC_RG_RacerAI` component. Only the first RaceManager spawns (the level holds two identical managers, both saved
  2026-10-30; delete one when convenient).
- **Driver** (`BPC_RG_RacerAI`, from the test autopilot): it holds the brakes and handbrake until GO
  (IntroStart + 4.8 s), then uses pure-pursuit steering toward a point ahead on its own lane (`BotLane`, cm right of
  the centreline). It brakes for each corner using the corner speed cap: `BotLatG` = skill
  (3.1 / 2.8 / 2.5 / 2.3 / 2.1 g), so raise it for harder bots and lower it for easier ones. It is reset onto the
  centreline after being stuck for 1.5 s, and cruises at 60 km/h after finishing.
- **Race logic** (`UpdateRace`, every machine, every tick): racers = `Bots` (replicated) + every PlayerState's
  pawn. For each one it finds the nearest respawn point (a window around the last point, or a full search if more
  than 20 m away) and the position relative to `StartI` (20). A lap counts when a car crosses from the last 20% of
  the lap to the first 20%, and crossing back the other way takes it off. `NumLaps` = 3; finishing = crossing
  the line a 4th time. Score is lap x points + progress, finishers rank by finish order, and the rank goes into
  `Rank` / `Order`. The log prints `RG_LAP slot N laps L` and `RG_FINISH slot N`.
- **Scoreboard** (`WBP_RG_Scoreboard`): created by the minimap's `AttachToHud` into the same HUD overlay. A
  `M_RG_HUD_Board` card shows a red header with LAP x/3 and POS p/n, rows with gold / silver / bronze badges,
  names, and LAP n or the finish time, with your row highlighted orange. When you finish, a "FINISH!" banner
  shows your place and time. It is hidden during the intro and fades in with the other HUD pieces.
- **Tested in PIE (single player):** 5 bots launched at GO and lapped (bot laps logged about 60 s apart), and the
  scoreboard order and LAP 2/3 updated live. Not yet seen: a full 3-lap finish and the banner, or multiplayer
  clients (bots have no PlayerState, so the minimap shows them only where their controller exists, i.e. on the
  server).

### Crash respawn + scoreboard v2 (2026-11-01, later)

- **Crash respawn:** every car has the BugBattle damage component `BPC_HoneyStatus`. Ramming another car does
  damage, and enough damage wrecks the car. It then respawned at a *random PlayerStart* after about 8 s, which on
  this map is a grid slot. Now, on `Lvl_GardenGrandPrix` only, `FinishRespawn` calls the new `RaceRespawnPoint`
  (nearest `RaceManager.TrackPts` point to the wreck, facing `TrackYaw`). `RespawnVehicle` uses a 0.6 s delay, so
  you are back about 2 s after the crash. Arenas are unchanged. Generator: `honey_race.py`; originals in
  `Saved/RG_backup_honey` (graphs + .uasset). Writing these graphs needs `(Variables|Default|SetImmobilized ...)`;
  the read-back name `|SetwithNotifybImmobilized` cannot be written, and `Math|Vector|vector+vector` must be `+`.
- **Scoreboard v2** (user: "make it more attractive"): 330 x 458 `M_RG_HUD_Board` with
  - a red header with a checkered patch; on your last lap it turns gold, pulses and says FINAL LAP!
  - a race-progress bar (`Prog` = your laps and progress / 3 laps) with a checkered finish
  - slanted pills with an ink outline, one per racer, with a colour chip (`C0..C7`: bots by slot, you orange-red,
    other players blue)
  - medal badges, with a sparkle on 1st
  - your row orange with a pulsing glow
  - green ▲ / red ▼ arrows for 2 s when a racer gains or loses a place (Tick keeps `PrevRank` / `ChgT` / `ChgDir`
    per racer, after the first second of the race).
  The v1 generator is `Saved/RacingGame/gen_race_v1.py`.

### Crash rule + finished bots leave (2026-11-01, later)

- **Crash rule (race level only):** `BPC_HoneyStatus.HandleOwnerHit` now calls the new `RaceHit(OtherActor)` first;
  on `Lvl_GardenGrandPrix` it returns Handled = true, so the arena ram / damage rules are skipped. Another car
  closing at 1500 cm/s (54 km/h) or more wrecks this car at once (`BBApplyDamage` 1000), and it respawns at the
  same spot (`RaceRespawnPoint`) about 2 s later. Slower bumps and walls do nothing. The splice was done with
  create_node / connect_pins (entry -> RaceHit -> Branch, False -> the original first branch), so the original
  graph is untouched. Speed: `RACE_WRECK_SPEED` in `honey_race.py`, i.e. the `>= 1500.0` literal in `RaceHit`.
- **Finished bots leave:** in `UpdateRace`, when a bot (slot < number of bots) finishes, the server destroys it and
  its AIController. Its row and finish time stay on the scoreboard. The player's car is never removed.
- Tested with `NumLaps` = 1 (set back to 3): FINAL LAP header, RG_FINISH for bots and the player in order, no errors.

### Bot tuning (2026-11-01, later)

The user said Flutter and Shelly were not racing well. Each bot now logs `RG_AI|slot|t|idx|kmh|cap` once a second and
`RG_AI_RESET|slot` when it is put back on the track.
- The cause was the cars: Flutter (Butterfly) and Bruno (Beetle) were still stock template karts (1,350-1,700 kg,
  downforce 0.3, template tyres with friction 3 and cornering stiffness 1000). They spun or ran wide at six corners
  and Flutter got stuck at the start (20 resets). These two BPs are only used by the bots, so they got the
  Snail Racer's `VehicleMovementComp` setup: BeeRacer F1 wheels, 900 kg, downforce 2.5, engine, gearbox, steering
  and differential. The meshes are unchanged. Backups are in `Saved/RG_backup_karts`.
- Swapping wheel classes at runtime (`SetWheelClass`) broke the cars (about 5 km/h, 27 resets), so do not do that.
  `BotKart` (a runtime downforce / torque / centre-of-mass tune) is kept in the AI but off for all bots.
- Skills (`BotLatG`): Bee 3.3, Ant 3.2, Shelly 3.2 (was 2.5), Bruno 3.1, Flutter 3.1.
- Result over 100 s: average speed Bee 109, Ant 107, Shelly 106, Flutter 102, Bruno 95 km/h; 0-2 resets each;
  first laps 57 / 59 / 58 / 71 / 76 s (the karts start at the back of the grid).

## WRONG WAY warning (2026-11-01)

`WBP_RG_WrongWay` (generator `gen_wrongway.py`, material `M_RG_HUD_WrongWay`) is created by the scoreboard's
`AttachTo` in the same HUD overlay.
- **Trigger:** during the race only (after GO, before you finish). It measures your velocity along the race
  direction at your nearest centreline point (`RaceManager.LastIdx` / `TrackYaw`). Below -3 m/s it counts up, and
  above +1.5 m/s it resets. After `WRONG_SECS` (2 s) the sign shows.
- **Look and motion:** a red-orange plate with a thick ink outline, white inner stroke, gloss, a pulsing orange glow
  and a U-turn badge, with "WRONG WAY!" and "TURN AROUND". It pops in on a damped spring (overshoot about 1.3x),
  then breathes (±3.5%) and wobbles (±4°). The Image and the text widget get the same render scale, angle and pivot,
  so the text moves with the sign. It shrinks and fades away when you are back on course.
- **Tested in PIE:** with a temporary trigger (any car not moving forward) the sign appeared 2 s after GO and
  animated as above. The real trigger is restored. A real wrong-way drive has not been tested (no driver input in
  automated runs).
