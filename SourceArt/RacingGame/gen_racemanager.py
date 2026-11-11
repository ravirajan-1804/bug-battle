"""Race start (cinematic intro + lights + timer) and off-track respawn for Lvl_GardenGrandPrix.

Writes:
  racemanager_defaults.json   TrackPts / TrackYaw for BP_RG_RaceManager (centreline every RESPAWN_STRIDE samples)
  racemanager.dsl             BP_RG_RaceManager event graph (server sets the replicated IntroStart time, creates the
                              start HUD, respawns cars off the track)
  startlights_tick.dsl        WBP_RG_StartLights event graph (cinematic 3-2-1-GO intro, holds the car until GO,
                              then the race timer)
  startlights_onpaint.dsl     WBP_RG_StartLights OnPaint (letterbox bars, red / yellow / green lamps + number, timer)
Copies of all four go to Saved/RacingGame/*.txt|json (AssetTools.read_file only reads there).

Multiplayer: the server writes IntroStart = server time + INTRO_LEAD once; it replicates with the race manager.
Every client times the intro from GameState.ServerWorldTimeSeconds - IntroStart, so all screens show the same
number and release the cars at the same moment. The cinematic camera is spawned locally on each client.
"""
import json, math, os
from trackdef import Track, HALF_W
from intro_shots import SHOTS

HERE = os.path.dirname(os.path.abspath(__file__))
RESPAWN_STRIDE = 4          # centreline samples are 100 cm apart -> a respawn point every 4 m
OFF_RADIUS = HALF_W + 650   # car centre this far from the centreline = past the barrier (road edge + 50 cm)
FALL_DEPTH = 400.0          # this far below the road = fell off
INTRO_LEAD = 1.0            # server waits this long before "3" so clients have joined and synced their clock
SHOT_SECS = 1.6             # each of 3 / 2 / 1 is one camera shot
GO_T = 3 * SHOT_SECS        # GO: cars released, timer starts
SWOOP_SECS = 0.75           # GO camera swoop from the "1" shot to behind the player's car
BLEND_SECS = 0.6            # then blend into the car's own (gameplay) camera
LETTERBOX_OPEN = 0.9        # cinematic bars slide away over this long after GO
LIGHTS_OFF = 1.8            # the lights and "GO!" stay up this long after GO; the timer stays
SWOOP_LIFT = 800.0          # the GO swoop arcs this high (cm) over the car
SWOOP_SIDE = 600.0          # and this far out to the car's right, so it orbits instead of passing over the roof
AUDIO = "/Game/RacingGame/Audio/%s.%s"

T = Track()
pts, yaws = [], []
for i in range(0, len(T.xy), RESPAWN_STRIDE):
    c, fwd, _, _ = T.frame(i)
    pts.append({"x": round(float(c[0]), 1), "y": round(float(c[1]), 1), "z": round(float(c[2]), 1)})
    yaws.append(round(math.degrees(math.atan2(fwd[1], fwd[0])), 2))
defaults = {"TrackPts": pts, "TrackYaw": yaws, "OffRadius": OFF_RADIUS, "FallDepth": FALL_DEPTH}

# ---------------------------------------------------------------- race manager
# Every driven car (has a controller) is checked each tick against the nearest centreline point.
# Past the barrier or below the road -> put it back on that point, facing the race direction, stopped.
MANAGER = """(event EventBeginPlay
  (if (Networking|HasAuthority)
    (Variables|Default|SetIntroStart (+ (GameState|GetServerWorldTimeSeconds (Game|GetGameState)) %g))
    (CallFunction|SpawnBots))
  (bind pc (Game|GetPlayerController 0))""" % INTRO_LEAD + """
  (bind w (UserInterface|CreateWidget :Class "/Game/RacingGame/UI/WBP_RG_StartLights.WBP_RG_StartLights_C" :OwningPlayer pc))
  (UserInterface|Viewport|AddtoViewport :self w :ZOrder 20))

(event EventTick (DeltaSeconds)
  (CallFunction|UpdateRace)
  (bind pts (Variables|Default|GetTrackPts))
  (bind n (Utilities|Array|Length pts))
  (bind cars (Actor|GetAllActorsOfClass "/Script/ChaosVehicles.WheeledVehiclePawn"))
  (for car cars
    (Utilities|IsValid (Pawn|GetController car)
      (:"Is Valid"
        (bind loc (Transformation|GetActorLocation :self car))
        (Variables|Default|SetBestD 1000000000000.0)
        (Variables|Default|SetBestI 0)
        (for i (range n)
          (bind d (Math|Vector|Distance2DSquared(Vector) loc (Utilities|Array|Get(acopy) pts i)))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestI i)))
        (bind bi (Variables|Default|GetBestI))
        (bind p (Utilities|Array|Get(acopy) pts bi))
        (bind r (Variables|Default|GetOffRadius))
        (if (or (> (Variables|Default|GetBestD) (* r r)) (< (.z loc) (- (.z p) (Variables|Default|GetFallDepth))))
          (bind mesh (Actor|GetComponentbyClass :self car :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
          (Physics|SetPhysicsLinearVelocity :self mesh :NewVel (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
          (Physics|SetPhysicsAngularVelocityinDegrees :self mesh :NewAngVel (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
          (Transformation|SetActorLocationAndRotation :self car
            :NewLocation (+ p (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 80.0))
            :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Utilities|Array|Get(acopy) (Variables|Default|GetTrackYaw) bi))
            :bSweep false :bTeleport true)))
      (:"Is Not Valid"))))
"""

# ---------------------------------------------------------------- start lights widget
RED, YEL, GRN, OFF = (1.0, 0.04, 0.02, 1.0), (1.0, 0.72, 0.0, 1.0), (0.1, 1.0, 0.2, 1.0), (0.07, 0.07, 0.08, 1.0)
NOGLOW = (0.03, 0.03, 0.035, 1.0)   # = housing body
WORLD_RED, WORLD_YEL, WORLD_GRN = (1.0, 0.05, 0.02, 1.0), (1.0, 0.65, 0.0, 1.0), (0.1, 1.0, 0.15, 1.0)


def col(c):
    return '"(R=%g,G=%g,B=%g,A=%g)"' % tuple(c)


def glow(c):
    # opaque: the glow sits on the black housing, and translucent scanlines would show overlap stripes
    return (c[0] * 0.35, c[1] * 0.35, c[2] * 0.35, 1.0)


def stage(sfx, lamps, lit, label, label_col, label_x, world):
    """One countdown step: lamp colours, glow rings, the label and the gantry point lights in the world."""
    s = []
    for k, (c, on) in enumerate(zip(lamps, lit)):
        s.append("(Variables|Default|SetLamp%d %s)" % (k, col(c)))
        s.append("(Variables|Default|SetGlow%d %s)" % (k, col(glow(c) if on else NOGLOW)))
    s += ['(Variables|Default|SetLabel "%s")' % label,
          "(Variables|Default|SetLabelColor %s)" % col(label_col),
          "(Variables|Default|SetLabelX %g)" % label_x,
          "(for lamp%s (Variables|Default|GetLamps)" % sfx,
          '  (bind lc%s (Actor|GetComponentbyClass :self lamp%s :ComponentClass "/Script/Engine.PointLightComponent"))' % (sfx, sfx),
          "  (Rendering|Components|Light|SetLightColor :self lc%s :NewLightColor %s :bSRGB true))" % (sfx, col(world))]
    return s


def hold(sfx, on):
    """Hold the owning car on the grid (input off, handbrake on) or let it go."""
    fn = "Input|DisableInput" if on else "Input|EnableInput"
    return ["(bind pawn%s (Player|GetOwningPlayerPawn))" % sfx,
            "(Utilities|IsValid pawn%s" % sfx,
            '  (:"Is Valid"',
            "    (%s :self pawn%s :PlayerController (Widget|GetOwningPlayer))" % (fn, sfx),
            '    (bind mv%s (Actor|GetComponentbyClass :self pawn%s :ComponentClass "/Script/ChaosVehicles.ChaosVehicleMovementComponent"))' % (sfx, sfx),
            "    (Game|Components|ChaosVehicleMovement|SetThrottleInput :self mv%s :Throttle 0.0)" % sfx,
            "    (Game|Components|ChaosVehicleMovement|SetHandbrakeInput :self mv%s :bNewHandbrake %s))" % (sfx, "true" if on else "false"),
            '  (:"Is Not Valid"))']


def block(lines, ind):
    return "\n".join(ind + ln for ln in lines)


def vec(p):
    return "(Math|Vector|MakeVector :X %g :Y %g :Z %g)" % tuple(p)


def sound(name, vol=1.0):
    return '(Audio|PlaySound2D :Sound "%s" :VolumeMultiplier %g)' % (AUDIO % (name, name), vol)


def once(k, lines):
    """Run lines the first tick the intro reaches stage k (sounds, cuts, release)."""
    return ["(if (< (Variables|Default|GetStage) %d)" % k, "  (Variables|Default|SetStage %d)" % k] + \
           ["  " + ln for ln in lines] + [")"]


def shot(k, sfx):
    """Camera move for countdown shot k (0 = "3"): smoothstep from start to end, always aimed at the target."""
    a, b, tgt, fov = SHOTS[k]
    return ["(bind al%s (Math|Float|Clamp(Float) (/ (- t %g) %g) 0.0 1.0))" % (sfx, k * SHOT_SECS, SHOT_SECS),
            "(bind sm%s (* (* al%s al%s) (- 3.0 (* 2.0 al%s))))" % (sfx, sfx, sfx, sfx),
            "(bind cp%s (Math|Vector|Lerp(Vector) %s %s sm%s))" % (sfx, vec(a), vec(b), sfx),
            "(Transformation|SetActorLocationAndRotation :self cam :NewLocation cp%s "
            ":NewRotation (Math|Rotator|FindLookatRotation cp%s %s) :bSweep false :bTeleport true)" % (sfx, sfx, vec(tgt))]


def fov(v):
    return "(Camera|SetFieldOfView :self ccomp :InFieldOfView %g)" % v


OFF_WORLD = (0.12, 0.02, 0.01, 1.0)
L = []
# pre-roll (server time not replicated yet, or before "3"): first frame of the "3" shot, lamps dark
L += ["(if (< t 0.0)"] + ["  " + x for x in stage("P", (OFF, OFF, OFF), (0, 0, 0), "", RED, 0, OFF_WORLD)]
L += ["  " + x for x in shot(0, "P")] + ["  " + x for x in hold("P", True)]
L += ["  (elif (< t %g)" % SHOT_SECS]
L += ["    " + x for x in stage("3", (RED, OFF, OFF), (1, 0, 0), "3", RED, -19, WORLD_RED)]
L += ["    " + x for x in once(1, [fov(SHOTS[0][3]), sound("SW_RG_CountHit"), sound("SW_RG_EngineIdle", 0.55)])]
L += ["    " + x for x in shot(0, "3")] + ["    " + x for x in hold("3", True)]
L += ["    (elif (< t %g)" % (2 * SHOT_SECS)]
L += ["      " + x for x in stage("2", (OFF, YEL, OFF), (0, 1, 0), "2", YEL, -19, WORLD_YEL)]
L += ["      " + x for x in once(2, [fov(SHOTS[1][3]), sound("SW_RG_CountHit")])]
L += ["      " + x for x in shot(1, "2")] + ["      " + x for x in hold("2", True)]
L += ["      (elif (< t %g)" % GO_T]
L += ["        " + x for x in stage("1", (OFF, OFF, GRN), (0, 0, 1), "1", GRN, -19, WORLD_GRN)]
L += ["        " + x for x in once(3, [fov(SHOTS[2][3]), sound("SW_RG_CountHit"), sound("SW_RG_EngineRev", 0.9),
                                         sound("SW_RG_Riser", 0.6)])]
L += ["        " + x for x in shot(2, "1")] + ["        " + x for x in hold("1", True)]
# GO: release, race timer, swoop from the "1" shot to behind the player's car, then blend into its camera
go = stage("G", (GRN, GRN, GRN), (1, 1, 1), "GO!", GRN, -58, WORLD_GRN)
# (an IsValid branch ends the exec chain in the DSL, so the release goes last)
go += once(4, [
    "(Variables|Default|SetRacing true)",
    "(Variables|Default|SetSwoopFrom (Transformation|GetActorLocation :self cam))",
    # log line for checking that every player got GO at the same server time
    '(Development|PrintString :InString (Utilities|String|Append "RG_INTRO GO at server time " '
    '(Utilities|String|ToString(Float) now)) :bPrintToScreen false :bPrintToLog true)',
    sound("SW_RG_GoHit"), sound("SW_RG_Whoosh", 0.8), sound("SW_RG_EngineLaunch", 0.9)] + hold("G", False))
go += ["(bind gt (- t %g))" % GO_T,
       "(Variables|Default|SetRaceTime gt)",
       "(Variables|Default|SetLetterbox (Math|Float|Clamp(Float) (- 1.0 (/ gt %g)) 0.0 1.0))" % LETTERBOX_OPEN,
       "(bind mins (Math|Float|Truncate (/ gt 60.0)))",
       "(bind secs (- gt (* mins 60.0)))",
       '(Variables|Default|SetTimerText (Utilities|String|Append "TIME  " (Utilities|String|Append '
       '(Utilities|String|Append (Utilities|String|ToString(Integer) mins) ":") '
       '(Utilities|String|ToString(Text) (Utilities|Text|ToText(Float) secs :bUseGrouping false '
       ':MinimumIntegralDigits 2 :MinimumFractionalDigits 2 :MaximumFractionalDigits 2)))))',
       "(if (< gt %g)" % SWOOP_SECS,
       # target = the car's active camera right now, so the hand-off blend afterwards is seamless
       "  (bind pawnS (Player|GetOwningPlayerPawn))",
       "  (Utilities|IsValid pawnS",
       '    (:"Is Valid"',
       '      (for cc (Actor|GetComponentsByClass :self pawnS :ComponentClass "/Script/Engine.CameraComponent")',
       "        (if (Components|Activation|IsActive :self cc)",
       "          (Variables|Default|SetHandoffCam (Utilities|Casting|CastToCameraComponent cc))))",
       "      (bind hc (Variables|Default|GetHandoffCam))",
       "      (bind sa (Math|Float|Clamp(Float) (/ gt %g) 0.0 1.0))" % SWOOP_SECS,
       "      (bind ss (* (* sa sa) (- 3.0 (* 2.0 sa))))",
       # arc up and over the car (a straight line from the front shot would pass through it), nose down at the top
       "      (bind arc (Math|Trig|Sin(Degrees) (* ss 180.0)))",
       "      (bind hr (Transformation|GetWorldRotation :self hc))",
       # keep the car in frame during the arc, line up with the car's camera only as it lands
       "      (bind swp (+ (Math|Vector|Lerp(Vector) (Variables|Default|GetSwoopFrom) (Transformation|GetWorldLocation :self hc) ss)"
       " (+ (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (* arc %g)) (* (Transformation|GetActorRightVector :self pawnS) (* arc %g)))))" % (SWOOP_LIFT, SWOOP_SIDE),
       "      (bind aim (Math|Rotator|FindLookatRotation swp (+ (Transformation|GetActorLocation :self pawnS) "
       "(Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 60.0))))",
       "      (Transformation|SetActorLocationAndRotation :self cam :NewLocation swp"
       " :NewRotation (Math|Rotator|Lerp(Rotator) aim hr (Math|Float|Clamp(Float) (/ (- ss 0.85) 0.15) 0.0 1.0) true) :bSweep false :bTeleport true)",
       "      (Camera|SetFieldOfView :self ccomp :InFieldOfView (Math|Float|Lerp %g (Class|CameraComponent|GetFieldOfView hc) ss)))"
       % SHOTS[2][3],
       '    (:"Is Not Valid"))',
       "  (else"]
go += ["    " + x for x in once(5, [
    "(bind pawnB (Player|GetOwningPlayerPawn))",
    "(Utilities|IsValid pawnB",
    '  (:"Is Valid"',
    "    (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget pawnB :BlendTime %g "
    ':BlendFunc "VTBlend_EaseInOut" :BlendExp 2.0))' % BLEND_SECS,
    '  (:"Is Not Valid"))'])]
go += ["    (if (> gt %g)" % LIGHTS_OFF, "      (Variables|Default|SetShowLights false))))"]
L += ["        (else"] + ["          " + x for x in go] + ["        )))))"]

# the car switcher (I/O/P/U) can swap the pawn mid-countdown, so the hold is re-applied every tick.
# Possessing the car at BeginPlay resets the view target, so during the intro it is re-asserted every tick.
TICK = """(event UserInterface|EventConstruct
  (Variables|Default|SetReleased false)
  (Variables|Default|SetStage 0)
  (Variables|Default|SetShowLights true)
  (Variables|Default|SetRacing false)
  (Variables|Default|SetLetterbox 1.0)
  (Variables|Default|SetLamps (Actor|GetAllActorswithTag "RG_StartLight"))
  (Variables|Default|SetManager (Utilities|Casting|CastToBP_RG_RaceManager (Actor|GetActorOfClass "/Game/RacingGame/Gameplay/BP_RG_RaceManager.BP_RG_RaceManager_C")))
  ; local cinematic camera: every client spawns its own, nothing to replicate
  (bind camA (Game|SpawnActorfromClass :Class "/Script/Engine.CameraActor"
    :SpawnTransform (Math|Transform|MakeTransform :Location %(start)s) :CollisionHandlingOverride "AlwaysSpawn"))
  (bind camC (Utilities|Casting|CastToCameraActor camA))
  (Variables|Default|SetIntroCam camC)
  (bind ccompC (Class|CameraActor|GetCameraComponent camC))
  (Camera|SetFieldOfView :self ccompC :InFieldOfView %(fov0)g)
  (Game|Player|SetViewTargetwithBlend :self (Widget|GetOwningPlayer) :NewViewTarget camC :BlendTime 0.0))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (bind local (UserInterface|Geometry|GetLocalSize MyGeometry))
  (Variables|Default|SetScreenSize local)
  (Variables|Default|SetPixelScale (/ (.x (UserInterface|Geometry|GetAbsoluteSize MyGeometry)) (Math|Float|Max(Float) (.x local) 1.0)))
  (Variables|Default|SetOrigin (Math|Vector2D|MakeVector2D (* (.x local) 0.5) 130.0))
  ; intro clock shared by all players: server time since the replicated IntroStart (-1 until it arrives)
  (bind st (Class|BPRGRaceManager|GetIntroStart (Variables|Default|GetManager)))
  (bind now (GameState|GetServerWorldTimeSeconds (Game|GetGameState)))
  (bind t (select (> st 0.0) (- now st) -1.0))
  (Variables|Default|SetT t)
  (bind pc (Widget|GetOwningPlayer))
  (bind cam (Variables|Default|GetIntroCam))
  (bind ccomp (Class|CameraActor|GetCameraComponent cam))
  (if (and (< t %(keep)g) (!= (Pawn|GetViewTarget pc) cam))
    (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget cam :BlendTime 0.0))
%(body)s)
""" % dict(start=vec(SHOTS[0][0]), fov0=SHOTS[0][3], keep=GO_T + SWOOP_SECS, body=block(L, "  "))

# OnPaint: a dark rounded housing with three lamps; each lamp is a black bezel, a soft glow ring when lit
# and the lamp disc. Discs are filled with horizontal scanlines (DrawLine only, no textures).
HOUSING_W, HOUSING_H, LAMP_GAP, LAMP_R, BEZEL_R, GLOW_R = 330.0, 116.0, 104.0, 38.0, 46.0, 56.0
SCAN = 3.0
FONT = '"/Engine/EngineFonts/Roboto.Roboto"'
_n = [0]


def disc(cx, cy, r, color):
    """Filled disc at (ox+cx, oy+cy); DSL loop/bind names must be unique, hence the counter."""
    _n[0] += 1
    k, y, hw = "k%d" % _n[0], "y%d" % _n[0], "hw%d" % _n[0]
    n = int(2 * r / SCAN)
    return ["  (for %s (range %d)" % (k, n),
            "    (bind %s (- (* (+ %s 0.5) %g) %g))" % (y, k, 2 * r / n, r),
            "    (bind %s (Math|Float|Sqrt (Math|Float|Max(Float) (- %g (* %s %s)) 0.0)))" % (hw, r * r, y, y),
            "    (Painting|DrawLine Context (Math|Vector2D|MakeVector2D (- (+ ox %g) %s) (+ (+ oy %g) %s)) "
            "(Math|Vector2D|MakeVector2D (+ (+ ox %g) %s) (+ (+ oy %g) %s)) %s true (* pxs %g)))"
            % (cx, hw, cy, y, cx, hw, cy, y, color, 2 * r / n + 0.6)]


LETTERBOX_H = 0.12          # each cinematic bar, as a fraction of the screen height
P = ["(fn OnPaint (Context)",
     "  (bind pxs (Variables|Default|GetPixelScale))",
     "  (bind org (Variables|Default|GetOrigin))",
     "  (bind ox (.x org))",
     "  (bind oy (.y org))",
     # cinematic bars (thick black lines; Slate line thickness is not DPI-scaled, hence * pxs)
     "  (bind scr (Variables|Default|GetScreenSize))",
     "  (bind bar (* (* (.y scr) %g) (Variables|Default|GetLetterbox)))" % LETTERBOX_H,
     "  (if (> bar 0.5)",
     "    (Painting|DrawLine Context (Math|Vector2D|MakeVector2D 0.0 (* bar 0.5)) (Math|Vector2D|MakeVector2D (.x scr) (* bar 0.5)) %s false (* pxs bar))" % col((0, 0, 0, 1)),
     "    (Painting|DrawLine Context (Math|Vector2D|MakeVector2D 0.0 (- (.y scr) (* bar 0.5))) (Math|Vector2D|MakeVector2D (.x scr) (- (.y scr) (* bar 0.5))) %s false (* pxs bar)))" % col((0, 0, 0, 1)),
     # race timer, top centre, from GO on
     "  (if (Variables|Default|GetRacing)",
     "    (bind ttx (Utilities|Text|ToText(String) (Variables|Default|GetTimerText)))",
     '    (Painting|DrawText Context ttx (Math|Vector2D|MakeVector2D (- ox 148.0) 16.0) %s 40 "Bold" %s)' % (FONT, col((0, 0, 0, 0.7))),
     '    (Painting|DrawText Context ttx (Math|Vector2D|MakeVector2D (- ox 150.0) 13.0) %s 40 "Bold" %s))' % (FONT, col((1, 1, 1, 1))),
     # start lights + number, only while ShowLights
     "  (if (Variables|Default|GetShowLights)"]
# housing: light-grey rim, dark body; a thick line with round ends drawn as discs
hx = HOUSING_W / 2 - HOUSING_H / 2
for dx, dy, extra, c in [(0, 0, 4, (0.6, 0.6, 0.62, 1.0)), (0, 0, 0, NOGLOW)]:
    rr = HOUSING_H / 2 + extra
    P.append("  (Painting|DrawLine Context (Math|Vector2D|MakeVector2D (+ ox %g) (+ oy %g)) (Math|Vector2D|MakeVector2D (+ ox %g) (+ oy %g)) %s true (* pxs %g))"
             % (-hx + dx, dy, hx + dx, dy, col(c), 2 * rr))
    for side in (-1, 1):
        P += disc(side * hx + dx, dy, rr, col(c))
for li in range(3):
    cx = (li - 1) * LAMP_GAP
    P += disc(cx, 0, GLOW_R, "(Variables|Default|GetGlow%d)" % li)
    P += disc(cx, 0, BEZEL_R, col((0.0, 0.0, 0.0, 1.0)))
    P += disc(cx, 0, LAMP_R, "(Variables|Default|GetLamp%d)" % li)
    # small highlight so the lamp reads as a glass bulb
    P.append("  (Painting|DrawLine Context (Math|Vector2D|MakeVector2D (+ ox %g) (- oy 18.0)) (Math|Vector2D|MakeVector2D (+ ox %g) (- oy 23.0)) %s true (* pxs 6.0))"
             % (cx - 16, cx - 6, col((1, 1, 1, 0.35))))
# number / GO! under the housing, with a dark drop shadow
LABEL_Y = HOUSING_H / 2 + 14
P += ["  (bind lx (+ ox (Variables|Default|GetLabelX)))",
      "  (bind txt (Utilities|Text|ToText(String) (Variables|Default|GetLabel)))",
      '  (Painting|DrawText Context txt (Math|Vector2D|MakeVector2D (+ lx 3.0) (+ oy %g)) %s 64 "Bold" %s)' % (LABEL_Y + 4, FONT, col((0, 0, 0, 0.7))),
      '  (Painting|DrawText Context txt (Math|Vector2D|MakeVector2D lx (+ oy %g)) %s 64 "Bold" (Variables|Default|GetLabelColor))))' % (LABEL_Y, FONT)]
ONPAINT = "\n".join(P) + "\n"

SAVED = os.path.join(HERE, "..", "..", "Saved", "RacingGame")
os.makedirs(SAVED, exist_ok=True)
for name, text in [("racemanager", MANAGER), ("startlights_tick", TICK), ("startlights_onpaint", ONPAINT)]:
    open(os.path.join(HERE, name + ".dsl"), "w", encoding="utf-8").write(text)
    open(os.path.join(SAVED, name + ".txt"), "w", encoding="utf-8").write(text)
for d in (HERE, SAVED):
    json.dump(defaults, open(os.path.join(d, "racemanager_defaults.json"), "w"))
print(len(pts), "respawn points; off radius", OFF_RADIUS)
