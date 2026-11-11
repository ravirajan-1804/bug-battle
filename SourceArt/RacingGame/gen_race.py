"""3-lap race with 5 AI bots + scoreboard for Lvl_GardenGrandPrix (2026-11-01).

User request: 5 AI bots race the player over 3 laps from GO; a Pixar-style scoreboard top-left shows places 1-6.

Writes (+ .txt copies in Saved/RacingGame for AssetTools.read_file):
  race_spawnbots.dsl      BP_RG_RaceManager function SpawnBots (server, BeginPlay): 5 bots on grid slots 2-6, each with
                          its own AIController and a BPC_RG_RacerAI component
  race_update.dsl         BP_RG_RaceManager function UpdateRace (every machine, every tick): racers = Bots + every
                          PlayerState's pawn; nearest centreline point, lap count at the start line, finish order and
                          time, score -> Rank / Order
  racerai.dsl             BPC_RG_RacerAI event graph: held on the brakes until GO, then pure-pursuit driving along its
                          own lane with a corner speed cap (LatG per bot = skill), stuck reset, cruise after the finish
  board_attach.dsl        WBP_RG_Scoreboard AttachTo (card Image with a dynamic material, then itself, in the HUD overlay)
  board_tick.dsl          WBP_RG_Scoreboard EventGraph (finds the RaceManager, fades in after the intro, row strings)
  board_onpaint.dsl       WBP_RG_Scoreboard OnPaint (header, rows, finish banner)
  race_defaults.json      CDO values for the RaceManager and BPC_RG_RacerAI
  board_material.txt      Custom HLSL for M_RG_HUD_Board (Pixar card: ink outline, red header pill, medal badges)
"""
import json, math, os
import numpy as np
from trackdef import Track, L as TL

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(HERE, "..", "..", "Saved", "RacingGame")
RM_C = "/Game/RacingGame/Gameplay/BP_RG_RaceManager.BP_RG_RaceManager_C"
AI_C = "/Game/RacingGame/Gameplay/BPC_RG_RacerAI.BPC_RG_RacerAI_C"
FONT = '"/Engine/EngineFonts/Roboto.Roboto"'
EM = 96.0 / 72.0

GO_T = 3 * 1.6                     # gen_racemanager.py: GO after the three 1.6 s shots
HUD_IN, HUD_FADE = GO_T + 0.75 + 0.6, 0.5
NUM_LAPS = 3
RESPAWN_STRIDE = 4
# bots: class, name, skill (LatG = how hard it corners), lane (cm right of the centreline)
# v2 (user: "Flutter and Shelly are not doing great, make them all play good"): skills closer together. The Beetle and
# Butterfly karts (only used by these bots) were given the Snail Racer's driving setup in their BPs (kart_tune.py), so
# BotKart (runtime downforce / torque / centre-of-mass tune) is off; swapping wheel classes at runtime broke the cars.
BOTS = [("BeeRacer/BP_RGC_BeeRacer", "Buzzy Bee", 3.3, -320.0, False),
        ("AntRacer/BP_RGC_AntRacer", "Andy Ant", 3.2, 320.0, False),
        ("SnailRacer/BP_RGC_SnailRacer", "Shelly Snail", 3.2, -120.0, False),
        ("Beetle/BP_RGC_Beetle", "Bruno Beetle", 3.1, 120.0, False),
        ("Butterfly/BP_RGC_Butterfly", "Flutter", 3.1, 0.0, False)]
KART_TUNE = dict(down=3.0, torque=950.0, com_z=-30.0,
                 wf="/Game/RacingGame/Vehicles/BeeRacer/BP_RGC_BeeRacer_WheelFront.BP_RGC_BeeRacer_WheelFront_C",
                 wr="/Game/RacingGame/Vehicles/BeeRacer/BP_RGC_BeeRacer_WheelRear.BP_RGC_BeeRacer_WheelRear_C")
GRID = json.load(open(os.path.join(HERE, "placements.json")))["grid_slots"]   # slot 1 = pole = the player's car

T = Track()
I_START = T.index_at(*TL(40, 67))
START_I = int(math.ceil(I_START / RESPAWN_STRIDE))   # first respawn point at or past the start line
n_pts = len(range(0, len(T.xy), RESPAWN_STRIDE))


def V(n):
    return "(Variables|Default|Get%s)" % n


def S(n, v):
    return "(Variables|Default|Set%s %s)" % (n, v)


def mv(x, y):
    return "(Math|Vector2D|MakeVector2D %s %s)" % (x, y)


def col(r, g, b, a=1.0):
    return '"(R=%g,G=%g,B=%g,A=%g)"' % (r, g, b, a)


def get(arr, i):
    return "(Utilities|Array|Get(acopy) %s %s)" % (arr, i)


def setel(arr, i, v):
    return "(Utilities|Array|SetArrayElem %s %s %s true)" % (arr, i, v)


# ------------------------------------------------------------------ SpawnBots (server)
# only the first RaceManager spawns (the level has held two identical managers since 2026-10-30; GetActorOfClass in the
# AI and the scoreboard also returns this first one)
SP = ["(fn SpawnBots ()", '  (bind allm (Actor|GetAllActorsOfClass "%s"))' % RM_C,
      "  (if (and (not %s) (== (Utilities|Array|Get(acopy) allm 0) self))" % V("BotsSpawned"), "    " + S("BotsSpawned", "true"),
      "    (Utilities|Array|Clear %s)" % V("Bots")]
for k, (cls, nm, latg, lane, kart) in enumerate(BOTS):
    g = GRID[k + 1]
    x, y, z = g["loc"]
    p = cls.split("/")[1]
    SP += ['    (bind b%d (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/%s.%s_C" :SpawnTransform '
           '(Math|Transform|MakeTransform :Location (Math|Vector|MakeVector :X %.1f :Y %.1f :Z %.1f) '
           ':Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw %.3f)) :CollisionHandlingOverride "AlwaysSpawn"))'
           % (k, cls, p, x, y, z + 40.0, g["yaw"]),
           "    (Utilities|Array|Add %s b%d)" % (V("Bots"), k),
           "    (Pawn|SpawnDefaultController b%d)" % k,
           "    (Game|Components|ChaosVehicleMovement|SetRequiresControllerforInputs (Class|WheeledVehiclePawn|GetVehicleMovementComponent b%d) false)" % k,
           '    (Game|AddComponentbyClass :self b%d :Class "%s")' % (k, AI_C)]
SP[-1] += "))"
SPAWN = "\n".join(SP) + "\n"

# ------------------------------------------------------------------ UpdateRace (every machine)
ARRS = ["Laps", "LastRel", "LastIdx", "Seen", "FinishT", "FinishOrd", "Score", "Rank", "Order"]


def search(ind, rng, base, sfx):
    """Nearest centreline point to loc over range rng; j<sfx> = index expression from k<sfx> (binds unique per copy)."""
    return [ind + "(for k%s %s" % (sfx, rng),
            ind + "  (bind j%s %s)" % (sfx, base),
            ind + "  (bind d%s (Math|Vector|Distance2DSquared(Vector) loc (Utilities|Array|Get(acopy) pts j%s)))" % (sfx, sfx),
            ind + "  (if (< d%s %s)" % (sfx, V("RBestD")),
            ind + "    " + S("RBestD", "d" + sfx),
            ind + "    " + S("RBestI", "j" + sfx) + "))"]


U = ["(fn UpdateRace ()",
     "  (bind pts %s)" % V("TrackPts"),
     "  (bind n (Utilities|Array|Length pts))",
     "  (bind st %s)" % V("IntroStart"),
     "  " + S("RaceT", "(- (- (GameState|GetServerWorldTimeSeconds (Game|GetGameState)) st) %.2f)" % GO_T),
     "  (Utilities|Array|Clear %s)" % V("Cars"),
     "  (for b %s" % V("Bots"),
     "    (Utilities|Array|Add %s b))" % V("Cars"),
     "  (for p (Class|GameStateBase|GetPlayerArray (Game|GetGameState))",
     "    (Utilities|Array|Add %s (PlayerState|GetPawn p)))" % V("Cars"),
     "  (bind nc (Utilities|Array|Length %s))" % V("Cars")]
U += ["  (Utilities|Array|Resize %s nc)" % V(a) for a in ARRS]
U += ["  (for s (range nc)",
      "    (bind car (Utilities|Array|Get(acopy) %s s))" % V("Cars"),
      "    (Utilities|IsValid car",
      '      (:"Is Valid"',
      "        (bind loc (Transformation|GetActorLocation :self car))",
      "        " + S("RBestD", "1000000000000000.0"),
      "        (if %s" % get(V("Seen"), "s")]
U += search("          ", "(range 0 16)", "(Math|Integer|%%(Integer) (+ (+ %s ka) (- n 4)) n)" % get(V("LastIdx"), "s"), "a")
U[-1] += ")"
U += ["        (if (> %s 4000000.0)" % V("RBestD"),
      "          " + S("RBestD", "1000000000000000.0")]
U += search("          ", "(range n)", "kb", "b")
U[-1] += ")"
U += ["        (bind idx %s)" % V("RBestI"),
      "        " + setel(V("LastIdx"), "s", "idx"),
      "        (bind rel (Math|Integer|%%(Integer) (+ (- idx %s) n) n))" % V("StartI"),
      "        (if (not %s)" % get(V("Seen"), "s"),
      "          " + setel(V("Seen"), "s", "true"),
      "          " + setel(V("LastRel"), "s", "rel") + ")",
      "        (bind lr %s)" % get(V("LastRel"), "s"),
      "        (if (<= %s 0.0)" % get(V("FinishT"), "s"),
      "          (if (and (> (* lr 5) (* n 4)) (< (* rel 5) n))",
      "            " + setel(V("Laps"), "s", "(+ %s 1)" % get(V("Laps"), "s")),
      '            (Development|PrintString :InString (Utilities|String|Append "RG_LAP slot " (Utilities|String|Append (Utilities|String|ToString(Integer) s) (Utilities|String|Append " laps " (Utilities|String|ToString(Integer) %s)))) :bPrintToScreen false :bPrintToLog true)' % get(V("Laps"), "s"),
      "            (if (and (> %s %s) (> %s 0.0))" % (get(V("Laps"), "s"), V("NumLaps"), V("RaceT")),
      "              " + S("FinishCount", "(+ %s 1)" % V("FinishCount")),
      "              " + setel(V("FinishT"), "s", V("RaceT")),
      "              " + setel(V("FinishOrd"), "s", V("FinishCount")),
      '              (Development|PrintString :InString (Utilities|String|Append "RG_FINISH slot " (Utilities|String|ToString(Integer) s)) :bPrintToScreen false :bPrintToLog true)',
      # a bot that has finished its 3 laps leaves the track (server; its row and time stay on the scoreboard)
      "              (if (and (< s (Utilities|Array|Length %s)) (Networking|HasAuthority))" % V("Bots"),
      "                (Actor|DestroyActor (Pawn|GetController car))",
      "                (Actor|DestroyActor car)))",
      "            (elif (and (< (* lr 5) n) (> (* rel 5) (* n 4)))",
      "              " + setel(V("Laps"), "s", "(- %s 1)" % get(V("Laps"), "s")) + ")))",
      "        " + setel(V("LastRel"), "s", "rel"),
      "        (if (> %s 0.0)" % get(V("FinishT"), "s"),
      "          " + setel(V("Score"), "s", "(- 1000000000.0 (* (Math|Conversions|ToFloat(Integer) %s) 1000000.0))" % get(V("FinishOrd"), "s")),
      "          (else",
      "            " + setel(V("Score"), "s", "(Math|Conversions|ToFloat(Integer) (+ (* %s n) rel))" % get(V("Laps"), "s")) + ")))",
      '      (:"Is Not Valid")))',
      # rank = 1 + number of racers ahead (ties: lower slot first); Order[rank-1] = slot
      "  (for s (range nc)",
      "    " + S("RBestI", "1"),
      "    (bind sc %s)" % get(V("Score"), "s"),
      "    (for j (range nc)",
      "      (bind sj %s)" % get(V("Score"), "j"),
      "      (if (or (> sj sc) (and (== sj sc) (< j s)))",
      "        " + S("RBestI", "(+ %s 1)" % V("RBestI")) + "))",
      "    " + setel(V("Rank"), "s", V("RBestI")) + ")",
      "  (for s (range nc)",
      "    " + setel(V("Order"), "(- %s 1)" % get(V("Rank"), "s"), "s") + "))"]
UPDATE = "\n".join(U) + "\n"

# ------------------------------------------------------------------ BPC_RG_RacerAI
MGR = V("Mgr")


def mg(n):
    return "(Class|BPRGRaceManager|Get%s mgr)" % n


AI = """; BPC_RG_RacerAI (generated by gen_race.py). Added at runtime by BP_RG_RaceManager.SpawnBots (server only).
(event EventBeginPlay
  (bind m (Utilities|Casting|CastToBP_RG_RaceManager (Actor|GetActorOfClass "%(rm)s"))
    (:then
      (Variables|Default|SetMgr m))
    (:CastFailed)))

(event EventTick (DeltaSeconds)
  (bind owner (Components|GetOwner))
  (bind mgr (Variables|Default|GetMgr))
  (if (< (Variables|Default|GetSlot) 0)
    (bind bots %(bots)s)
    (for i (range (Utilities|Array|Length bots))
      (if (== (Utilities|Array|Get(acopy) bots i) owner)
        (Variables|Default|SetSlot i))))
  (if (>= (Variables|Default|GetSlot) 0)
    (bind slot (Variables|Default|GetSlot))
    (bind mc (Class|WheeledVehiclePawn|GetVehicleMovementComponent (Utilities|Casting|CastToWheeledVehiclePawn owner)))
    ; one-time race tune for the creature karts (more downforce, grip and torque, lower centre of mass)
    (if (and (not (Variables|Default|GetTuned)) (Utilities|Array|Get(acopy) (Class|BPRGRaceManager|GetBotKart mgr) slot))
      (bind wm (Utilities|Casting|CastToChaosWheeledVehicleMovementComponent mc)
        (:then
          (Game|Components|ChaosWheeledVehicleMovement|SetDownforceCoefficient wm %(down).1f)
          (Game|Components|ChaosWheeledVehicleMovement|SetMaxEngineTorque wm %(torque).1f)
          (Physics|SetCenterOfMass :self (Actor|GetComponentbyClass :self owner :ComponentClass "/Script/Engine.SkeletalMeshComponent") :CenterOfMassOffset (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z %(com_z).1f))
          (Variables|Default|SetTuned true))
        (:CastFailed)))
    (bind st %(intro)s)
    (bind rt (- (- (GameState|GetServerWorldTimeSeconds (Game|GetGameState)) st) %(go).2f))
    (if (or (<= st 0.0) (< rt 0.0))
      (Game|Components|ChaosVehicleMovement|SetSteeringInput mc 0.0)
      (Game|Components|ChaosVehicleMovement|SetThrottleInput mc 0.0)
      (Game|Components|ChaosVehicleMovement|SetBrakeInput mc 1.0)
      (Game|Components|ChaosVehicleMovement|SetHandbrakeInput mc true)
      (else
        (Game|Components|ChaosVehicleMovement|SetHandbrakeInput mc false)
        (bind pts (Variables|Default|GetPts))
        (bind n (Utilities|Array|Length pts))
        (bind loc (Transformation|GetActorLocation :self owner))
        (Variables|Default|SetBestD 1000000000000000.0)
        (if (>= (Variables|Default|GetIdx) 0)
          (bind i0 (Variables|Default|GetIdx))
          (for k (range 0 14)
            (bind j (Math|Integer|%%(Integer) (+ (+ i0 k) (- n 3)) n))
            (bind d (Math|Vector|Distance2DSquared(Vector) loc (Utilities|Array|Get(acopy) pts j)))
            (if (< d (Variables|Default|GetBestD))
              (Variables|Default|SetBestD d)
              (Variables|Default|SetBestI j))))
        (if (> (Variables|Default|GetBestD) 4000000.0)
          (Variables|Default|SetBestD 1000000000000000.0)
          (for j2 (range n)
            (bind d2 (Math|Vector|Distance2DSquared(Vector) loc (Utilities|Array|Get(acopy) pts j2)))
            (if (< d2 (Variables|Default|GetBestD))
              (Variables|Default|SetBestD d2)
              (Variables|Default|SetBestI j2))))
        (Variables|Default|SetIdx (Variables|Default|GetBestI))
        (bind idx (Variables|Default|GetIdx))
        (bind vel (Transformation|GetVelocity owner))
        (bind spd (Math|Vector|VectorLength vel))
        (bind kmh (* spd 0.036))
        ; pure pursuit on this bot's lane: look-ahead 6 m + 0.45 s of travel
        (bind ld (+ 600.0 (* spd 0.45)))
        (bind ti (Math|Integer|%%(Integer) (+ idx (+ (Math|Float|Truncate (/ ld 400.0)) 1)) n))
        (bind ty (Utilities|Array|Get(acopy) (Variables|Default|GetYaw) ti))
        (bind lane (Utilities|Array|Get(acopy) %(lanes)s slot))
        (bind tp (Utilities|Array|Get(acopy) pts ti))
        (bind tgt (Math|Vector|MakeVector :X (- (.x tp) (* (Math|Trig|Sin(Degrees) ty) lane)) :Y (+ (.y tp) (* (Math|Trig|Cos(Degrees) ty) lane)) :Z (.z tp)))
        (bind lp (Math|Transform|InverseTransformLocation (Transformation|GetActorTransform owner) tgt))
        (bind alpha (Math|Trig|Atan2(Degrees) (.y lp) (.x lp)))
        (bind ldist (Math|Float|Max(Float) (Math|Vector|VectorLength lp) 300.0))
        (bind delta (Math|Trig|Atan(Degrees) (/ (* 528.0 (Math|Trig|Sin(Degrees) alpha)) ldist)))
        (bind lock (* 32.0 (Math|Float|Max(Float) 0.42 (- 1.0 (* kmh 0.0046)))))
        (Game|Components|ChaosVehicleMovement|SetSteeringInput mc (Math|Float|Clamp(Float) (/ delta lock) -1.0 1.0))
        ; corner speed cap from the tightest radius ahead; after the finish line just cruise
        (bind rad (Utilities|Array|Get(acopy) (Variables|Default|GetRad) idx))
        (bind cap0 (* 0.036 (Math|Float|Sqrt (* (* (Utilities|Array|Get(acopy) %(latg)s slot) 981.0) rad))))
        (bind fin (> (Utilities|Array|Get(acopy) %(fint)s slot) 0.0))
        (bind cap (Math|Float|Min(Float) cap0 (+ 60.0 (* 1000.0 (- 1.0 (Math|Conversions|ToFloat(Boolean) fin))))))
        (if (> kmh cap)
          (Game|Components|ChaosVehicleMovement|SetThrottleInput mc 0.0)
          (else
            (Game|Components|ChaosVehicleMovement|SetThrottleInput mc 1.0)))
        (if (> kmh (+ cap 6.0))
          (Game|Components|ChaosVehicleMovement|SetBrakeInput mc 1.0)
          (else
            (Game|Components|ChaosVehicleMovement|SetBrakeInput mc 0.0)))
        ; telemetry once a second: RG_AI|slot|t|idx|kmh|cap|steer
        (if (> rt (Variables|Default|GetNextLog))
          (Variables|Default|SetNextLog (+ rt 1.0))
          (Development|PrintString :InString (Utilities|String|Append "RG_AI|" (Utilities|String|Append (Utilities|String|ToString(Integer) slot) (Utilities|String|Append "|" (Utilities|String|Append (Utilities|String|ToString(Float) rt) (Utilities|String|Append "|" (Utilities|String|Append (Utilities|String|ToString(Integer) idx) (Utilities|String|Append "|" (Utilities|String|Append (Utilities|String|ToString(Float) kmh) (Utilities|String|Append "|" (Utilities|String|ToString(Float) cap)))))))))) :bPrintToScreen false :bPrintToLog true))
        ; stuck for 1.5 s (spun into a wall or another car) -> back onto the centreline
        (if (and (< kmh 5.0) (> rt 2.0))
          (Variables|Default|SetStuckT (+ (Variables|Default|GetStuckT) DeltaSeconds))
          (else
            (Variables|Default|SetStuckT 0.0)))
        (if (> (Variables|Default|GetStuckT) 1.5)
          (Variables|Default|SetStuckT 0.0)
          (bind rp (Utilities|Array|Get(acopy) pts idx))
          (bind body (Actor|GetComponentbyClass :self owner :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
          (Physics|SetPhysicsLinearVelocity :self body :NewVel (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
          (Physics|SetPhysicsAngularVelocityinDegrees :self body :NewAngVel (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
          (Transformation|SetActorLocationAndRotation :self owner
            :NewLocation (+ rp (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 80.0))
            :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Utilities|Array|Get(acopy) (Variables|Default|GetYaw) idx))
            :bSweep false :bTeleport true)
          (Development|PrintString :InString (Utilities|String|Append "RG_AI_RESET|" (Utilities|String|ToString(Integer) slot)) :bPrintToScreen false :bPrintToLog true))))))
""" % dict(KART_TUNE, rm=RM_C, bots="(Class|BPRGRaceManager|GetBots mgr)", intro=mg("IntroStart"), go=GO_T,
           lanes=mg("BotLane"), latg=mg("BotLatG"), fint=mg("FinishT"))

# ------------------------------------------------------------------ Scoreboard (v2, 2026-11-01: "make it more attractive")
MARGIN = 40.0
BW, BH_MAX, MAXROWS = 330.0, 458.0, 8
ROW0, ROW_H = 92.0, 44.0
SKEW = 0.18                      # row pills lean like racing type (x shift per unit of y above the row centre)
INK = (0.10, 0.055, 0.03)
BROWN = (0.30, 0.17, 0.08)
RED = (0.92, 0.12, 0.06)
ORANGE = (1.0, 0.5, 0.06)
UP_C, DN_C = (0.2, 0.85, 0.3), (0.95, 0.2, 0.15)
CHG_SECS = 2.0                   # how long the gained / lost-a-place arrow shows

ATTACH = """(fn AttachTo ()
  (bind ov (Variables|Default|GetHostOverlay))
  (bind img (Game|ConstructObjectfromClass :Class "/Script/UMG.Image"))
  (Variables|Default|SetTmpBrush (Widget|Brush|MakeBrushfromMaterial "/Game/RacingGame/UI/M_RG_HUD_Board.M_RG_HUD_Board" %d %d))
  (Variables|Default|SetBoardMID (Widget|Brush|GetDynamicMaterial (Variables|Default|GetTmpBrush)))
  (Class|Image|SetBrush :self img :Brush (Variables|Default|GetTmpBrush))
  (Widget|SetVisibility img "HitTestInvisible")
  (Widget|SetRenderOpacity :self img :InOpacity 0.0)
  (bind islot (Widget|AddChildtoOverlay ov img))
  (Layout|OverlaySlot|SetHorizontalAlignment islot "HAlign_Left")
  (Layout|OverlaySlot|SetVerticalAlignment islot "VAlign_Top")
  (Variables|Default|SetBoardImg img)
  (bind sslot (Widget|AddChildtoOverlay ov self))
  (Layout|OverlaySlot|SetHorizontalAlignment sslot "HAlign_Fill")
  (Layout|OverlaySlot|SetVerticalAlignment sslot "VAlign_Fill")
  (Widget|SetVisibility self "HitTestInvisible")
  (Variables|Default|SetAttached true)
  (bind ww (UserInterface|CreateWidget :Class "/Game/RacingGame/UI/WBP_RG_WrongWay.WBP_RG_WrongWay_C" :OwningPlayer (Widget|GetOwningPlayer)))
  (Class|WBPRGWrongWay|SetHostOverlay :self ww :HostOverlay ov)
  (Class|WBPRGWrongWay|AttachTo :self ww)
  (Variables|Default|SetWrongWay ww))
""" % (BW, BH_MAX)


def fmt_time(t):
    return ('(Utilities|String|Append (Utilities|String|Append (Utilities|String|ToString(Integer) (Math|Float|Truncate (/ %s 60.0))) ":") '
            '(Utilities|String|ToString(Text) (Utilities|Text|ToText(Float) (- %s (* (Math|Conversions|ToFloat(Integer) (Math|Float|Truncate (/ %s 60.0))) 60.0)) '
            ':bUseGrouping false :MinimumIntegralDigits 2 :MinimumFractionalDigits 2 :MaximumFractionalDigits 2)))') % (t, t, t)


def mgr(n):
    return "(Class|BPRGRaceManager|Get%s mgr)" % n


def param(nm, val):
    return '(Rendering|Material|InitializeScalarParameterandGetIndex (Variables|Default|GetBoardMID) (Utilities|Name|MakeLiteralName "%s") %s)' % (nm, val)


TK = ["(event UserInterface|EventTick (MyGeometry InDeltaTime)",
      "  (bind ls (UserInterface|Geometry|GetLocalSize MyGeometry))",
      "  (Variables|Default|SetScreenSize ls)",
      "  (Variables|Default|SetPixelScale (/ (.x (UserInterface|Geometry|GetAbsoluteSize MyGeometry)) (Math|Float|Max(Float) (.x ls) 1.0)))",
      "  (Variables|Default|SetHudAlpha 0.0)",
      "  (Variables|Default|SetShowB false)",
      "  (if (and (Variables|Default|GetReady) (Variables|Default|GetAttached))",
      "    (bind mgr (Variables|Default|GetMgr))",
      "    (bind st %s)" % mgr("IntroStart"),
      "    (if (> st 0.0)",
      "      (Variables|Default|SetHudAlpha (Math|Float|Clamp(Float) (/ (- (- (GameState|GetServerWorldTimeSeconds (Game|GetGameState)) st) %.2f) %.2f) 0.0 1.0)))" % (HUD_IN, HUD_FADE),
      "    (Variables|Default|SetShowB (> (Variables|Default|GetHudAlpha) 0.01))",
      "    (Widget|SetRenderOpacity :self self :InOpacity (Variables|Default|GetHudAlpha))",
      "    (Widget|SetRenderOpacity :self (Variables|Default|GetBoardImg) :InOpacity (Variables|Default|GetHudAlpha))",
      "    (Widget|Transform|SetRenderTranslation (Variables|Default|GetBoardImg) %s)" % mv(MARGIN, MARGIN),
      "    (bind cars %s)" % mgr("Cars"),
      "    (bind nc (Utilities|Array|Length cars))",
      "    (bind nb (Utilities|Array|Length %s))" % mgr("Bots"),
      "    (bind npts (Utilities|Array|Length %s))" % mgr("TrackPts"),
      "    (bind now (Utilities|Time|GetGameTimeinSeconds))",
      "    (Variables|Default|SetRows (Math|Integer|Min(Integer) nc %d))" % MAXROWS,
      "    (Variables|Default|SetMeSlot -1)",
      "    (bind me (Player|GetOwningPlayerPawn))",
      "    (for i (range nc)",
      "      (if (== (Utilities|Array|Get(acopy) cars i) me)",
      "        (Variables|Default|SetMeSlot i)))",
      "    (bind ms (Variables|Default|GetMeSlot))",
      "    (bind nl %s)" % mgr("NumLaps"),
      # gained / lost a place: remember the time and direction per racer (only once the race is running)
      "    (Utilities|Array|Resize (Variables|Default|GetPrevRank) nc)",
      "    (Utilities|Array|Resize (Variables|Default|GetChgT) nc)",
      "    (Utilities|Array|Resize (Variables|Default|GetChgDir) nc)",
      "    (for s (range nc)",
      "      (bind rk0 %s)" % get(mgr("Rank"), "s"),
      "      (bind pr0 (Utilities|Array|Get(acopy) (Variables|Default|GetPrevRank) s))",
      "      (if (and (and (> pr0 0) (!= rk0 pr0)) (> %s 1.0))" % mgr("RaceT"),
      "        (Utilities|Array|SetArrayElem (Variables|Default|GetChgT) s now true)",
      "        (if (< rk0 pr0)",
      "          (Utilities|Array|SetArrayElem (Variables|Default|GetChgDir) s 1 true)",
      "          (else",
      "            (Utilities|Array|SetArrayElem (Variables|Default|GetChgDir) s -1 true))))",
      "      (Utilities|Array|SetArrayElem (Variables|Default|GetPrevRank) s rk0 true))",
      "    (Utilities|Array|Clear (Variables|Default|GetRowName))",
      "    (Utilities|Array|Clear (Variables|Default|GetRowRight))",
      "    (Utilities|Array|Clear (Variables|Default|GetRowMe))",
      "    (Utilities|Array|Clear (Variables|Default|GetRowUp))",
      "    (Utilities|Array|Clear (Variables|Default|GetRowDn))",
      "    (for r (range (Variables|Default|GetRows))",
      "      (bind s %s)" % get(mgr("Order"), "r"),
      "      (if (< s nb)",
      "        (Utilities|Array|Add (Variables|Default|GetRowName) %s)" % get(mgr("BotNames"), "s"),
      "        (elif (== s ms)",
      '          (Utilities|Array|Add (Variables|Default|GetRowName) "YOU")',
      "          (else",
      '            (Utilities|Array|Add (Variables|Default|GetRowName) (Utilities|String|Append "PLAYER " (Utilities|String|ToString(Integer) (+ (- s nb) 1)))))))',
      "      (bind ft %s)" % get(mgr("FinishT"), "s"),
      "      (if (> ft 0.0)",
      "        (Utilities|Array|Add (Variables|Default|GetRowRight) %s)" % fmt_time("ft"),
      "        (else",
      '          (Utilities|Array|Add (Variables|Default|GetRowRight) (Utilities|String|Append "LAP " (Utilities|String|ToString(Integer) (Math|Integer|Clamp(Integer) %s 1 nl))))))' % get(mgr("Laps"), "s"),
      "      (if (== s ms)",
      "        (Utilities|Array|Add (Variables|Default|GetRowMe) 1.0)",
      "        (else",
      "          (Utilities|Array|Add (Variables|Default|GetRowMe) 0.0)))",
      "      (bind ca (Math|Float|Clamp(Float) (- 1.0 (/ (- now (Utilities|Array|Get(acopy) (Variables|Default|GetChgT) s)) %.1f)) 0.0 1.0))" % CHG_SECS,
      "      (bind cd (Utilities|Array|Get(acopy) (Variables|Default|GetChgDir) s))",
      "      (if (> cd 0)",
      "        (Utilities|Array|Add (Variables|Default|GetRowUp) ca)",
      "        (Utilities|Array|Add (Variables|Default|GetRowDn) 0.0)",
      "        (elif (< cd 0)",
      "          (Utilities|Array|Add (Variables|Default|GetRowUp) 0.0)",
      "          (Utilities|Array|Add (Variables|Default|GetRowDn) ca)",
      "          (else",
      "            (Utilities|Array|Add (Variables|Default|GetRowUp) 0.0)",
      "            (Utilities|Array|Add (Variables|Default|GetRowDn) 0.0)))))",
]
# colour chips per row: bots by slot (0-4), you orange-red (7), other players blue (6)
for k in range(MAXROWS):
    TK += ["    (if (< %d (Variables|Default|GetRows))" % k,
           "      (bind sk%d %s)" % (k, get(mgr("Order"), str(k))),
           "      (if (< sk%d nb)" % k,
           "        " + param("C%d" % k, "(Math|Conversions|ToFloat(Integer) sk%d)" % k),
           "        (elif (== sk%d ms)" % k,
           "          " + param("C%d" % k, "7.0"),
           "          (else",
           "            " + param("C%d" % k, "6.0") + "))))"]
TK += [
      "    (Variables|Default|SetMeFinished false)",
      "    " + param("Final", "0.0"),
      "    " + param("Prog", "0.0"),
      "    (if (>= ms 0)",
      "      (bind rk %s)" % get(mgr("Rank"), "ms"),
      "      (bind ml %s)" % get(mgr("Laps"), "ms"),
      "      (bind mft %s)" % get(mgr("FinishT"), "ms"),
      "      (if (and (== ml nl) (<= mft 0.0))",
      '        (Variables|Default|SetHeadL "FINAL LAP!")',
      "        " + param("Final", "1.0"),
      "        (else",
      '          (Variables|Default|SetHeadL (Utilities|String|Append "LAP " (Utilities|String|Append (Utilities|String|ToString(Integer) (Math|Integer|Clamp(Integer) ml 1 nl)) (Utilities|String|Append "/" (Utilities|String|ToString(Integer) nl)))))))',
      '      (Variables|Default|SetHeadR (Utilities|String|Append "P" (Utilities|String|Append (Utilities|String|ToString(Integer) rk) (Utilities|String|Append "/" (Utilities|String|ToString(Integer) nc)))))',
      "      " + param("Hi", "(Math|Conversions|ToFloat(Integer) (- rk 1))"),
      "      (if (> mft 0.0)",
      "        " + param("Prog", "1.0"),
      "        (elif (>= ml 1)",
      "          " + param("Prog", "(Math|Float|Clamp(Float) (/ (Math|Conversions|ToFloat(Integer) (+ (* (- ml 1) npts) %s)) (Math|Conversions|ToFloat(Integer) (Math|Integer|Max(Integer) (* nl npts) 1))) 0.0 1.0)" % get(mgr("LastRel"), "ms")) + "))",
      "      (if (> mft 0.0)",
      "        (Variables|Default|SetMeFinished true)",
      "        (if (== rk 1)",
      '          (Variables|Default|SetBanner2 "1ST PLACE")',
      "          (elif (== rk 2)",
      '            (Variables|Default|SetBanner2 "2ND PLACE")',
      "            (elif (== rk 3)",
      '              (Variables|Default|SetBanner2 "3RD PLACE")',
      "              (else",
      '                (Variables|Default|SetBanner2 (Utilities|String|Append (Utilities|String|ToString(Integer) rk) "TH PLACE"))))))',
      '        (Variables|Default|SetBanner2 (Utilities|String|Append (Variables|Default|GetBanner2) (Utilities|String|Append "   " %s)))))' % fmt_time("mft"),
      "    " + param("Rows", "(Math|Conversions|ToFloat(Integer) (Variables|Default|GetRows))") + ")",
      "  (if (not (Variables|Default|GetReady))",
      '    (bind m (Utilities|Casting|CastToBP_RG_RaceManager (Actor|GetActorOfClass "%s"))' % RM_C,
      "      (:then",
      "        (Variables|Default|SetMgr m)",
      "        (Variables|Default|SetReady true))",
      "      (:CastFailed))))"]
TICK = "\n".join(TK) + "\n"

# OnPaint
P = []
add = P.append
OUTL = [(-1.6, 0), (1.6, 0), (0, -1.6), (0, 1.6), (-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)]


def text(ind, t, x, y, size, face, color, outline=None, ow=1.0, offs=None, shadow=0.0):
    if shadow:
        add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv("(+ %s 0.5)" % x, "(+ %s 3.0)" % y), FONT, size, face, col(*INK, shadow)))
    if outline:
        for ox, oy in (offs or OUTL):
            add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv("(+ %s %g)" % (x, ox * ow), "(+ %s %g)" % (y, oy * ow)), FONT, size, face, outline))
    add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv(x, y), FONT, size, face, color))


def ttext(s):
    return "(Utilities|Text|ToText(String) %s)" % s


INKC = col(*INK)
add("(fn OnPaint (Context)")
add("  (if (Variables|Default|GetShowB)")
I = "    "
add(I + "(bind pxs (Variables|Default|GetPixelScale))")
X0, Y0 = MARGIN, MARGIN
# header: "LAP x/3" / "FINAL LAP!" left, "P2/6" right (left of the checkered patch)
fs = 18
em = EM * fs
add(I + "(bind hl (Variables|Default|GetHeadL))")
text(I, ttext("hl"), "%g" % (X0 + 30), "%g" % (Y0 + 35 - 0.572 * em), fs, "Bold Italic", col(1, 1, 1), outline=INKC, ow=1.2, shadow=0.35)
add(I + "(bind hr (Variables|Default|GetHeadR))")
fs2 = 16
em2 = EM * fs2
text(I, ttext("hr"), "(- %g (* (Utilities|String|Len hr) %.3f))" % (X0 + 252, 0.6 * em2), "%g" % (Y0 + 35 - 0.572 * em2), fs2, "Bold Italic",
     col(1, 0.93, 0.75), outline=INKC, ow=1.1)
for r in range(MAXROWS):
    cy = Y0 + ROW0 + r * ROW_H + ROW_H / 2
    add(I + "(if (< %d (Variables|Default|GetRows))" % r)
    J = I + "  "
    num = str(r + 1)
    fsb = 15
    emb = EM * fsb
    text(J, '(Utilities|Text|ToText(String) "%s")' % num, "%g" % (X0 + 44 - 0.3 * emb), "%g" % (cy - 0.572 * emb), fsb, "Bold Italic", col(1, 1, 1),
         outline=INKC, ow=1.0, offs=OUTL[:4])
    add(J + "(bind me%d (Utilities|Array|Get(acopy) (Variables|Default|GetRowMe) %d))" % (r, r))
    add(J + "(bind nm%d (Utilities|Array|Get(acopy) (Variables|Default|GetRowName) %d))" % (r, r))
    namecol = "(Utilities|Struct|MakeLinearColor (+ %g (* %g me%d)) (+ %g (* %g me%d)) (+ %g (* %g me%d)) 1.0)" % (
        BROWN[0], 1 - BROWN[0], r, BROWN[1], 1 - BROWN[1], r, BROWN[2], 1 - BROWN[2], r)
    fsn = 14
    emn = EM * fsn
    add(J + '(Painting|DrawText Context %s %s %s %d "Bold Italic" (Utilities|Struct|MakeLinearColor 0.1 0.055 0.03 (* 0.85 me%d)))'
        % (ttext("nm%d" % r), mv("%g" % (X0 + 85.4), "%g" % (cy - 0.572 * emn + 1.8)), FONT, fsn, r))
    add(J + '(Painting|DrawText Context %s %s %s %d "Bold Italic" %s)' % (ttext("nm%d" % r), mv("%g" % (X0 + 84), "%g" % (cy - 0.572 * emn)), FONT, fsn, namecol))
    add(J + "(bind rr%d (Utilities|Array|Get(acopy) (Variables|Default|GetRowRight) %d))" % (r, r))
    fsr = 12
    emr = EM * fsr
    add(J + '(Painting|DrawText Context %s %s %s %d "Bold Italic" %s)' % (
        ttext("rr%d" % r), mv("(- %g (* (Utilities|String|Len rr%d) %.3f))" % (X0 + 290, r, 0.58 * emr), "%g" % (cy - 0.572 * emr)), FONT, fsr, namecol))
    # gained (green up) / lost (red down) a place
    ax = X0 + 304
    add(J + "(bind up%d (Utilities|Array|Get(acopy) (Variables|Default|GetRowUp) %d))" % (r, r))
    add(J + "(bind dn%d (Utilities|Array|Get(acopy) (Variables|Default|GetRowDn) %d))" % (r, r))
    for tag, c, sgn in (("up", UP_C, -1), ("dn", DN_C, 1)):
        tip = (ax, cy + sgn * 6.5)
        bl, br = (ax - 6.5, cy - sgn * 4.5), (ax + 6.5, cy - sgn * 4.5)
        mid = (ax, cy - sgn * 4.5)
        clr = "(Utilities|Struct|MakeLinearColor %g %g %g %s%d)" % (c[0], c[1], c[2], tag, r)
        ink = "(Utilities|Struct|MakeLinearColor 0.1 0.055 0.03 %s%d)" % (tag, r)
        for (p0, p1, th, cc) in ((tip, bl, 4.5, ink), (bl, br, 4.5, ink), (br, tip, 4.5, ink), (tip, mid, 7.5, clr), (tip, bl, 2.2, clr), (tip, br, 2.2, clr), (bl, br, 2.2, clr)):
            add(J + "(Painting|DrawLine Context %s %s %s true (* pxs %g))" % (mv("%g" % p0[0], "%g" % p0[1]), mv("%g" % p1[0], "%g" % p1[1]), cc, th))
    P[-1] += ")"
# finish banner, centre of the screen
add(I + "(if (Variables|Default|GetMeFinished)")
J = I + "  "
add(J + "(bind ss (Variables|Default|GetScreenSize))")
fsf = 60
emf = EM * fsf
text(J, '(Utilities|Text|ToText(String) "FINISH!")', "(- (* (.x ss) 0.5) %.3f)" % (7 * 0.6 * emf / 2), "(- (* (.y ss) 0.34) %.3f)" % (0.572 * emf), fsf, "Bold Italic",
     col(1, 1, 1), outline=INKC, ow=2.6, shadow=0.45)
add(J + "(bind b2 (Variables|Default|GetBanner2))")
fsb2 = 24
emb2 = EM * fsb2
text(J, ttext("b2"), "(- (* (.x ss) 0.5) (* (Utilities|String|Len b2) %.3f))" % (0.29 * emb2), "(- (* (.y ss) 0.34) %.3f)" % (0.572 * emb2 - 62), fsb2, "Bold Italic",
     col(*ORANGE), outline=INKC, ow=1.5, shadow=0.4)
P[-1] += ")))"
ONPAINT = "\n".join(P) + "\n"

# ------------------------------------------------------------------ board material (Pixar card, v2)
BOARD = '''
float3 col = 0; float al = 0;
float3 INK = float3(0.10, 0.055, 0.03);
float3 CREAM = float3(1.0, 0.94, 0.80);
float3 CREAM2 = float3(0.95, 0.80, 0.58);
float3 TAN = float3(0.80, 0.68, 0.52);
float3 RED = float3(0.92, 0.12, 0.06);
float3 ORA = float3(1.0, 0.55, 0.08);
float3 GOLD = float3(1.0, 0.76, 0.12);
float3 PILL = float3(1.0, 0.985, 0.94);
float2 q = UV * float2(330.0, 458.0);
float aa = max(length(fwidth(q)) * 0.7071, 1e-3);
float R = max(Rows, 1.0);
float H = 92.0 + R * 44.0 + 14.0;
float pulse = 0.5 + 0.5 * sin(Time * 6.0);
// card
float2 c = float2(165.0, (6.0 + H) * 0.5);
float2 hs = float2(159.0, (H - 6.0) * 0.5);
float2 d0 = abs(q - c) - hs + 22.0;
float sd = length(max(d0, 0.0)) + min(max(d0.x, d0.y), 0.0) - 22.0;
float2 d1 = abs(q - c - float2(0.0, 6.0)) - hs + 22.0;
float sds = length(max(d1, 0.0)) + min(max(d1.x, d1.y), 0.0) - 22.0;
// header pill + checkered patch
float2 hp = abs(q - float2(165.0, 35.0)) - float2(149.0, 23.0) + 18.0;
float sdh = length(max(hp, 0.0)) + min(max(hp.x, hp.y), 0.0) - 18.0;
float3 headC = lerp(RED, lerp(GOLD, float3(1.0, 0.45, 0.1), pulse), Final);
float chk = (fmod(floor(q.x / 7.0) + floor(q.y / 7.0), 2.0) < 0.5) ? 1.0 : 0.0;
float chkM = saturate((q.x - 262.0) / aa + 0.5) * saturate((302.0 - q.x) / aa + 0.5) * saturate((q.y - 19.0) / aa + 0.5) * saturate((51.0 - q.y) / aa + 0.5);
// race progress bar
float2 bp = abs(q - float2(165.0, 74.0)) - float2(145.0, 6.0) + 6.0;
float sdb = length(max(bp, 0.0)) + min(max(bp.x, bp.y), 0.0) - 6.0;
float fillB = saturate((20.0 + 290.0 * saturate(Prog) - q.x) / aa + 0.5);
float bchk = (fmod(floor(q.x / 4.0) + floor(q.y / 4.0), 2.0) < 0.5) ? 1.0 : 0.0;
// rows
float ri = floor((q.y - 92.0) / 44.0);
float inRows = step(0.0, ri) * step(ri, R - 1.0);
float cy = 92.0 + ri * 44.0 + 22.0;
float xs = q.x + (q.y - cy) * 0.18;
float2 rp = abs(float2(xs, q.y) - float2(167.0, cy)) - float2(149.0, 18.0) + 13.0;
float sdr = length(max(rp, 0.0)) + min(max(rp.x, rp.y), 0.0) - 13.0;
float2 rps = abs(float2(xs, q.y) - float2(167.0, cy + 3.5)) - float2(149.0, 18.0) + 13.0;
float sdrs = length(max(rps, 0.0)) + min(max(rps.x, rps.y), 0.0) - 13.0;
float isHi = (abs(ri - Hi) < 0.5) ? 1.0 : 0.0;
float rb = length(q - float2(44.0, cy));
float3 medal = (ri < 0.5) ? GOLD : ((ri < 1.5) ? float3(0.80, 0.82, 0.87) : ((ri < 2.5) ? float3(0.86, 0.50, 0.24) : float3(0.55, 0.40, 0.28)));
float ci = (ri < 0.5) ? C0 : ((ri < 1.5) ? C1 : ((ri < 2.5) ? C2 : ((ri < 3.5) ? C3 : ((ri < 4.5) ? C4 : ((ri < 5.5) ? C5 : ((ri < 6.5) ? C6 : C7))))));
float3 chip = (ci < 0.5) ? float3(1.0, 0.8, 0.1) : ((ci < 1.5) ? float3(0.85, 0.22, 0.15) : ((ci < 2.5) ? float3(0.1, 0.72, 0.68) : ((ci < 3.5) ? float3(0.35, 0.78, 0.2) : ((ci < 4.5) ? float3(0.68, 0.38, 0.98) : ((ci < 5.5) ? float3(1.0, 0.45, 0.7) : ((ci < 6.5) ? float3(0.2, 0.5, 1.0) : float3(1.0, 0.3, 0.05)))))));
float2 cq = abs(float2(xs, q.y) - float2(71.0, cy)) - float2(3.5, 12.0) + 3.0;
float sdc = length(max(cq, 0.0)) + min(max(cq.x, cq.y), 0.0) - 3.0;
// sparkle on the gold medal
float2 sq = q - float2(53.0, cy - 10.0);
float spark = (ri < 0.5) ? saturate(1.0 - (abs(sq.x) * abs(sq.y) * 0.9 + length(sq) * 0.28)) * (0.6 + 0.4 * pulse) : 0.0;
float gl = saturate((cy - q.y) / 16.0);
'''


def over(c, o):
    return '{ float oo = saturate(%s); col = col * (1.0 - oo) + (%s) * oo; al = al + oo * (1.0 - al); }\n' % (o, c)


BOARD += over('INK', '0.35 * (1.0 - smoothstep(-2.0, 10.0, sds))') + \
    over('INK', 'saturate(-sd / aa + 0.5)') + \
    over('lerp(CREAM2, CREAM, saturate(1.0 - q.y / H))', 'saturate((-sd - 3.5) / aa + 0.5)') + \
    over('INK', 'saturate((2.6 - sdh) / aa + 0.5)') + \
    over('lerp(headC, saturate(headC + 0.3), saturate((35.0 - q.y) / 24.0) * 0.6)', 'saturate(-sdh / aa + 0.5)') + \
    over('lerp(float3(1, 1, 1), INK, chk)', '0.9 * chkM * saturate(-sdh / aa + 0.5) * saturate((q.x - 262.0) / 14.0)') + \
    over('float3(1, 1, 1)', '0.28 * saturate(-sdh / aa + 0.5) * saturate((24.0 - q.y) / 6.0)') + \
    over('INK', 'saturate((2.0 - sdb) / aa + 0.5)') + \
    over('TAN', 'saturate(-sdb / aa + 0.5)') + \
    over('lerp(ORA, RED, saturate((q.x - 20.0) / 290.0))', 'saturate(-sdb / aa + 0.5) * fillB') + \
    over('float3(1, 1, 1)', '0.35 * saturate(-sdb / aa + 0.5) * fillB * saturate((72.0 - q.y) / 2.5)') + \
    over('lerp(float3(1, 1, 1), INK, bchk)', 'saturate(-sdb / aa + 0.5) * saturate((q.x - 300.0) / aa + 0.5)') + \
    over('INK', '0.25 * inRows * (1.0 - smoothstep(-1.0, 4.0, sdrs))') + \
    over('lerp(ORA, float3(1.0, 0.3, 0.05), 0.5 + 0.5 * pulse)', 'inRows * isHi * 0.55 * (1.0 - smoothstep(0.0, 7.0, sdr)) * step(0.0, sdr)') + \
    over('INK', 'inRows * saturate((2.3 - sdr) / aa + 0.5)') + \
    over('lerp(PILL, lerp(ORA, float3(1.0, 0.75, 0.32), gl * 0.7), isHi)', 'inRows * saturate(-sdr / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.35 * inRows * (1.0 - isHi) * saturate(-sdr / aa + 0.5) * saturate((cy - 8.0 - q.y) / 6.0)') + \
    over('INK', 'inRows * saturate((1.6 - sdc) / aa + 0.5)') + \
    over('chip', 'inRows * saturate(-sdc / aa + 0.5)') + \
    over('INK', 'inRows * saturate((17.5 - rb) / aa + 0.5)') + \
    over('lerp(medal, saturate(medal + 0.25), saturate((cy - q.y) / 14.0))', 'inRows * saturate((15.0 - rb) / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.45 * inRows * saturate((5.5 - length(q - float2(39.0, cy - 6.0))) / aa + 0.5)') + \
    over('float3(1, 1, 0.85)', 'inRows * spark') + \
    'return float4(col / max(al, 1e-4) / max(VC, 0.02), al / max(VA, 0.02));'

DEFAULTS = {
    "RaceManager": {"BotNames": [b[1] for b in BOTS], "BotLatG": [b[2] for b in BOTS], "BotLane": [b[3] for b in BOTS], "BotKart": [b[4] for b in BOTS],
                    "NumLaps": NUM_LAPS, "StartI": START_I, "GoT": GO_T},
    "RacerAI": {"Slot": -1, "Idx": -1},
}
OUT = {"race_spawnbots": SPAWN, "race_update": UPDATE, "racerai": AI, "board_attach": ATTACH, "board_tick": TICK,
       "board_onpaint": ONPAINT, "board_material": BOARD}
os.makedirs(SAVED, exist_ok=True)
for nm, code in OUT.items():
    ext = ".txt" if nm == "board_material" else ".dsl"
    open(os.path.join(HERE, nm + ext), "w", encoding="utf-8").write(code)
    open(os.path.join(SAVED, nm + ".txt"), "w", encoding="utf-8").write(code)
json.dump(DEFAULTS, open(os.path.join(HERE, "race_defaults.json"), "w"), indent=1)
json.dump(DEFAULTS, open(os.path.join(SAVED, "race_defaults.json"), "w"), indent=1)
print("StartI", START_I, "of", n_pts, "| OnPaint lines", len(P))
