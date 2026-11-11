"""HUD v6 (2026-11-01): Pixar-style toy HUD (v5 was the futuristic cyan look; backup in Saved/RG_backup_hud_v5)

Original v5 brief: futuristic cyan racing HUD for Lvl_GardenGrandPrix, all inside WBP_RG_Minimap.

User request: circular rotating minimap bottom-left, semicircular digital speedometer bottom-right, cyan / electric
blue / white neon on dark glass, real data only, no gameplay / physics / camera changes.

Data sources (all live, read every frame):
- Track: BP_RG_RaceManager's TrackPts in the level (the respawn centreline, every 4 m) -> InitMap keeps every 2nd
  point (8 m) and fits the whole circuit into the radar. The map rotates around the circuit centre so your heading
  always points up (heading smoothed with FInterpTo).
- Progress: nearest centreline point to your car; the part of the lap from the start line to you is drawn cyan,
  the rest white. Progress only counts after you cross the start line (the grid sits behind it).
- Racers: every WheeledVehiclePawn with a PlayerState or a Controller (same rule as v4), coloured per PlayerId.
- Speedometer: ChaosWheeledVehicleMovementComponent of the owning pawn: GetForwardSpeed (km/h), GetCurrentGear,
  GetEngineRotationSpeed / GetEngineMaxRotationSpeed (RPM), GetThrottleInput (accel bar), measured longitudinal
  acceleration (accel chevrons). The cars have no nitro mechanic, so BOOST is turbo pressure derived from the real
  throttle and RPM (spools up with lag, like a turbo), not a separate gameplay resource.
- Turn numbers, checkpoint bars (sector splits at 1/3 and 2/3 of the lap) and the finish line come from trackdef.py,
  the same centreline that generated the track meshes. There are no shortcuts on the current (v5 Losail) layout.

Outputs: hud5_{onpaint,tick,attach,initmap,updatemap,readcar}.dsl (+ .txt copies in Saved/RacingGame) and
hud5_materials_script.py (paste body for ProgrammaticToolset.execute_tool_script).
"""
import json, math, os, re
import numpy as np
from trackdef import Track, L as TL, HALF_W

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(HERE, "..", "..", "Saved", "RacingGame")
FONT = '"/Engine/EngineFonts/Roboto.Roboto"'
UI = "/Game/RacingGame/UI/"
RM_CLASS = "/Game/RacingGame/Gameplay/BP_RG_RaceManager.BP_RG_RaceManager_C"
EM = 96.0 / 72.0                 # Slate font size -> em (slate units)

# layout (slate units)
MARGIN = 40.0                    # gap to the screen edges
MAPR = 150.0                     # radar glass radius
RIMG = 336.0                     # radar image size (rim, ticks, glow)
FIT = 0.80 * MAPR                # the whole circuit fits inside this radius
SPW, SPH = 460.0, 292.0          # speedometer image
SC = (230.0, 236.0)              # speedometer arc centre inside its image
SPEED_MAX = 240.0                # dial range (cars top out around 195-215 km/h)
# hidden during the 3-2-1 cinematic: GO at 3 x 1.6 s, then 0.75 s swoop + 0.6 s camera blend (gen_racemanager.py)
HUD_IN, HUD_FADE = 3 * 1.6 + 0.75 + 0.6, 0.5

# v6 "Pixar" toy palette (warm, chunky, ink outlines; matches the garden track)
INK = (0.10, 0.055, 0.03)
BROWN_T = (0.30, 0.17, 0.08)
RED = (0.92, 0.12, 0.06)
ORANGE = (1.0, 0.5, 0.06)
ASPHALT = (0.27, 0.26, 0.29)
RIM_R = 153.5                    # radius of the cream bezel ring (the N badge sits on it)
RACER_COLORS = [(0.15, 0.55, 1.0), (0.6, 0.25, 0.95), (0.1, 0.8, 0.45), (1.0, 0.4, 0.75),
                (0.0, 0.7, 0.8), (0.55, 0.85, 0.1), (1.0, 0.65, 0.2)]   # bright toy colours; red is you


def col(r, g, b, a=1.0):
    return '"(R=%g,G=%g,B=%g,A=%g)"' % (r, g, b, a)


def mv(x, y):
    return "(Math|Vector2D|MakeVector2D %s %s)" % (x, y)


def V(n):
    return "(Variables|Default|Get%s)" % n


def S(n, v):
    return "(Variables|Default|Set%s %s)" % (n, v)


def name(s):
    return '(Utilities|Name|MakeLiteralName "%s")' % s


# ------------------------------------------------------------------ offline track features (same data as the meshes)
T = Track()
xy = np.asarray(T.xy)
hd = np.asarray(T.heading)
N = len(xy)
I_START = T.index_at(*TL(40, 67))
dh = np.angle(np.exp(1j * (np.roll(hd, -1) - hd)))
k = np.convolve(np.r_[dh[-30:], dh, dh[:30]], np.ones(31) / 31, "same")[30:-30]
mask = np.abs(k) > 0.004
segs, s0 = [], None
for j in range(N):
    if mask[j] and s0 is None:
        s0 = j
    if not mask[j] and s0 is not None:
        segs.append((s0, j))
        s0 = None
if s0 is not None:
    segs.append((s0, N))
if segs and segs[0][0] == 0 and segs[-1][1] == N:          # merge the corner that wraps over index 0
    a0, b0 = segs.pop(0)
    a1, _ = segs.pop()
    segs.append((a1, N + b0))
turns = []
for a, b in segs:
    ids = np.arange(a, b) % N
    ang = math.degrees(dh[ids].sum())
    if abs(ang) < 20:
        continue
    ap = ids[np.argmax(np.abs(k[ids]))]
    h = hd[ap]
    left = np.array([-math.sin(h), math.cos(h)])
    outside = -np.sign(dh[ids].sum()) * left
    turns.append(((ap - I_START) % N, xy[ap] + outside * (HALF_W + 2600.0)))
turns.sort(key=lambda x: x[0])
TURNS = [(str(i + 1), p) for i, (_, p) in enumerate(turns)]


def line_at(i, half):
    h = hd[i]
    r = np.array([-math.sin(h), math.cos(h)])
    return xy[i] - r * half, xy[i] + r * half


FIN = line_at(I_START, HALF_W * 1.25)
CPS = [line_at((I_START + N * q // 3) % N, HALF_W * 1.15) for q in (1, 2)]
START_W = xy[I_START]
START_F = (math.cos(hd[I_START]), math.sin(hd[I_START]))

# ------------------------------------------------------------------ InitMap: read the real track from the RaceManager
INIT = """(fn InitMap ()
  (bind tp (Class|BPRGRaceManager|GetTrackPts %(rm)s))
  (bind n (Utilities|Array|Length tp))
  (if (> n 20)
    (Utilities|Array|Clear %(wp)s)
    %(setmin)s
    %(setmax)s
    (for i (range n)
      (if (== (Math|Integer|%%(Integer) i 2) 0)
        (bind p (Utilities|Array|Get(acopy) tp i))
        (Utilities|Array|Add %(wp)s (Math|Vector2D|MakeVector2D (.x p) (.y p)))
        (bind mn %(minw)s)
        (Variables|Default|SetMinW (Math|Vector2D|MakeVector2D (Math|Float|Min(Float) (.x mn) (.x p)) (Math|Float|Min(Float) (.y mn) (.y p))))
        (bind mx %(maxw)s)
        (Variables|Default|SetMaxW (Math|Vector2D|MakeVector2D (Math|Float|Max(Float) (.x mx) (.x p)) (Math|Float|Max(Float) (.y mx) (.y p))))))
    (bind mn2 %(minw)s)
    (bind mx2 %(maxw)s)
    (Variables|Default|SetWorldC (Math|Vector2D|MakeVector2D (* 0.5 (+ (.x mn2) (.x mx2))) (* 0.5 (+ (.y mn2) (.y mx2)))))
    (Variables|Default|SetNPts (Utilities|Array|Length %(wp)s))
    (Variables|Default|SetBestD 0.0)
    (bind wc (Variables|Default|GetWorldC))
    (for i (range (Variables|Default|GetNPts))
      (bind w1 (Utilities|Array|Get(acopy) %(wp)s i))
      (bind ax (- (.x w1) (.x wc)))
      (bind ay (- (.y w1) (.y wc)))
      (bind d1 (+ (* ax ax) (* ay ay)))
      (if (> d1 (Variables|Default|GetBestD))
        (Variables|Default|SetBestD d1)))
    (Variables|Default|SetMapScale (/ %(fit).1f (+ (Math|Float|Sqrt (Math|Float|Max(Float) (Variables|Default|GetBestD) 1.0)) %(edge).1f)))
    (Variables|Default|SetBestD 1000000000000000.0)
    (for i (range (Variables|Default|GetNPts))
      (bind w2 (Utilities|Array|Get(acopy) %(wp)s i))
      (bind bx (- (.x w2) %(sx)g))
      (bind by (- (.y w2) %(sy)g))
      (bind d2 (+ (* bx bx) (* by by)))
      (if (< d2 (Variables|Default|GetBestD))
        (Variables|Default|SetBestD d2)
        (Variables|Default|SetStartI i)))
    (Variables|Default|SetMapU (Math|Vector2D|MakeVector2D %(fx)g %(fy)g))
    (Variables|Default|SetArmed false)
    (Variables|Default|SetMapInit true)))
""" % dict(rm=V("RaceMgr"), wp=V("WorldPts"), minw=V("MinW"), maxw=V("MaxW"),
           setmin=S("MinW", mv(1e12, 1e12)), setmax=S("MaxW", mv(-1e12, -1e12)),
           fit=FIT, edge=HALF_W + 200.0, sx=START_W[0], sy=START_W[1], fx=START_F[0], fy=START_F[1])

# ------------------------------------------------------------------ UpdateMap: rotate the track, find your progress
UPDATE = """(fn UpdateMap ()
  (if (Variables|Default|GetMapInit)
    (bind me (Player|GetOwningPlayerPawn))
    (Utilities|IsValid me
      (:"Is Valid"
        (bind loc (Transformation|GetActorLocation :self me))
        (Variables|Default|SetPLoc (Math|Vector2D|MakeVector2D (.x loc) (.y loc)))
        (bind fwd (Transformation|GetActorForwardVector :self me))
        (bind mu (Variables|Default|GetMapU))
        (bind dt (Variables|Default|GetDt))
        (bind ux0 (Math|Interpolation|FInterpTo (.x mu) (.x fwd) dt 3.5))
        (bind uy0 (Math|Interpolation|FInterpTo (.y mu) (.y fwd) dt 3.5))
        (bind ul (Math|Float|Max(Float) (Math|Float|Sqrt (+ (* ux0 ux0) (* uy0 uy0))) 0.001))
        (Variables|Default|SetMapU (Math|Vector2D|MakeVector2D (/ ux0 ul) (/ uy0 ul)))
        (bind u (Variables|Default|GetMapU))
        (bind ux (.x u))
        (bind uy (.y u))
        (bind wc (Variables|Default|GetWorldC))
        (bind mc (Variables|Default|GetMapC))
        (bind sc (Variables|Default|GetMapScale))
        (bind pl (Variables|Default|GetPLoc))
        (Utilities|Array|Clear (Variables|Default|GetRotPts))
        (Variables|Default|SetBestD 1000000000000000.0)
        (for i (range (Variables|Default|GetNPts))
          (bind w (Utilities|Array|Get(acopy) (Variables|Default|GetWorldPts) i))
          (bind dx (* (- (.x w) (.x wc)) sc))
          (bind dy (* (- (.y w) (.y wc)) sc))
          (Utilities|Array|Add (Variables|Default|GetRotPts) (Math|Vector2D|MakeVector2D (+ (.x mc) (- (* dy ux) (* dx uy))) (- (.y mc) (+ (* dx ux) (* dy uy)))))
          (bind ex (- (.x w) (.x pl)))
          (bind ey (- (.y w) (.y pl)))
          (bind d2 (+ (* ex ex) (* ey ey)))
          (if (< d2 (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d2)
            (Variables|Default|SetBestI i)))
        (bind n (Variables|Default|GetNPts))
        (bind kk (Math|Integer|%(Integer) (+ (- (Variables|Default|GetBestI) (Variables|Default|GetStartI)) n) n))
        (if (Variables|Default|GetArmed)
          (if (and (< (* (Variables|Default|GetLastK) 10) n) (> (* kk 10) (* n 9)))
            (Variables|Default|SetArmed false))
          (else
            (if (and (>= kk 1) (< (* kk 4) n))
              (Variables|Default|SetArmed true))))
        (Variables|Default|SetLastK kk)
        (if (Variables|Default|GetArmed)
          (Variables|Default|SetProg kk)
          (else
            (Variables|Default|SetProg 0)))
        (Utilities|Array|Clear (Variables|Default|GetCyanPts))
        (Utilities|Array|Clear (Variables|Default|GetWhitePts))
        (bind pr (Variables|Default|GetProg))
        (bind si (Variables|Default|GetStartI))
        (for j (range (+ n 1))
          (bind q (Utilities|Array|Get(acopy) (Variables|Default|GetRotPts) (Math|Integer|%(Integer) (+ si j) n)))
          (if (<= j pr)
            (Utilities|Array|Add (Variables|Default|GetCyanPts) q))
          (if (>= j pr)
            (Utilities|Array|Add (Variables|Default|GetWhitePts) q))))
      (:"Is Not Valid"))))
"""

# ------------------------------------------------------------------ ReadCar: real vehicle values
READ = """(fn ReadCar ()
  (Variables|Default|SetHaveCar false)
  (bind veh (Utilities|Casting|CastToWheeledVehiclePawn (Player|GetOwningPlayerPawn))
    (:then
      (bind vm (Utilities|Casting|CastToChaosWheeledVehicleMovementComponent (Class|WheeledVehiclePawn|GetVehicleMovementComponent veh))
        (:then
          (bind dt (Math|Float|Max(Float) (Variables|Default|GetDt) 0.0001))
          (Variables|Default|SetSpeedKmh (* (Math|Float|Absolute(Float) (Game|Components|ChaosVehicleMovement|GetForwardSpeed vm)) 0.036))
          (Variables|Default|SetAccel (Math|Interpolation|FInterpTo (Variables|Default|GetAccel) (/ (- (Variables|Default|GetSpeedKmh) (Variables|Default|GetPrevSpeed)) (* dt 3.6)) dt 5.0))
          (Variables|Default|SetPrevSpeed (Variables|Default|GetSpeedKmh))
          (Variables|Default|SetShownSpeed (Math|Interpolation|FInterpTo (Variables|Default|GetShownSpeed) (Variables|Default|GetSpeedKmh) dt 12.0))
          (Variables|Default|SetRpm (Game|Components|ChaosWheeledVehicleMovement|GetEngineRotationSpeed vm))
          (bind rmax (Math|Float|Max(Float) (Game|Components|ChaosWheeledVehicleMovement|GetEngineMaxRotationSpeed vm) 1.0))
          (Variables|Default|SetRpmFrac (Math|Interpolation|FInterpTo (Variables|Default|GetRpmFrac) (Math|Float|Clamp(Float) (/ (Variables|Default|GetRpm) rmax) 0.0 1.0) dt 14.0))
          (Variables|Default|SetThrottle (Math|Interpolation|FInterpTo (Variables|Default|GetThrottle) (Math|Float|Clamp(Float) (Game|Components|ChaosVehicleMovement|GetThrottleInput vm) 0.0 1.0) dt 10.0))
          (Variables|Default|SetGear (Game|Components|ChaosVehicleMovement|GetCurrentGear vm))
          (Variables|Default|SetBoost (Math|Interpolation|FInterpTo (Variables|Default|GetBoost) (* (Variables|Default|GetThrottle) (Math|Float|Clamp(Float) (* (- (Variables|Default|GetRpmFrac) 0.3) 1.8) 0.0 1.0)) dt 2.2))
          (Variables|Default|SetRpmStr (Utilities|String|Append (Utilities|String|ToString(Integer) (Math|Float|Round (Variables|Default|GetRpm))) " RPM"))
          (Variables|Default|SetBoostStr (Utilities|String|Append (Utilities|String|ToString(Integer) (Math|Float|Round (* (Variables|Default|GetBoost) 100.0))) "%%"))
          (bind g (Variables|Default|GetGear))
          (if (< g 0)
            (Variables|Default|SetGearStr "R")
            (elif (== g 0)
              (Variables|Default|SetGearStr "N")
              (else
                (Variables|Default|SetGearStr (Utilities|String|ToString(Integer) g)))))
          (if (Utilities|String|NotEqual,CaseInsenstive(String) (Variables|Default|GetGearStr) (Variables|Default|GetLastGear))
            (Variables|Default|SetPop 1.0)
            (Variables|Default|SetLastGear (Variables|Default|GetGearStr)))
          (Variables|Default|SetPop (Math|Interpolation|FInterpTo (Variables|Default|GetPop) 0.0 dt 4.0))
          (bind b (Variables|Default|GetBoost))
          (if (< b 0.08)
            (Variables|Default|SetBoostState "IDLE")
            (elif (< b 0.85)
              (Variables|Default|SetBoostState "SPOOL")
              (else
                (Variables|Default|SetBoostState "TURBO"))))
          (Variables|Default|SetHaveCar true))
        (:CastFailed)))
    (:CastFailed)))
""".replace("%%", "%")

# ------------------------------------------------------------------ Tick: layout, data, material parameters
RH = RIMG / 2


def param(mid, pn, val):
    return "    (Rendering|Material|InitializeScalarParameterandGetIndex %s %s %s)" % (V(mid), name(pn), val)


TICK = "\n".join([
    "(event UserInterface|EventTick (MyGeometry InDeltaTime)",
    "  (Variables|Default|SetDt InDeltaTime)",
    "  (bind hs (UserInterface|Geometry|GetLocalSize MyGeometry))",
    "  (Variables|Default|SetHostSize hs)",
    "  (Variables|Default|SetPixelScale (/ (.x (UserInterface|Geometry|GetAbsoluteSize MyGeometry)) (Math|Float|Max(Float) (.x hs) 1.0)))",
    "  (Variables|Default|SetMapC %s)" % mv(MARGIN + RH, "(- (.y hs) %g)" % (MARGIN + RH)),
    "  (Variables|Default|SetSpeedoO %s)" % mv("(- (.x hs) %g)" % (MARGIN + SPW), "(- (.y hs) %g)" % (MARGIN + SPH)),
    "  (CallFunction|ReadCar)",
    "  (CallFunction|UpdateMap)",
    # intro clock = replicated IntroStart vs. the shared server time (same as WBP_RG_StartLights)
    "  (Variables|Default|SetHudAlpha 0.0)",
    "  (if (Variables|Default|GetMapInit)",
    "    (bind st (Class|BPRGRaceManager|GetIntroStart (Variables|Default|GetRaceMgr)))",
    "    (if (> st 0.0)",
    "      (Variables|Default|SetHudAlpha (Math|Float|Clamp(Float) (/ (- (- (GameState|GetServerWorldTimeSeconds (Game|GetGameState)) st) %.2f) %.2f) 0.0 1.0))))" % (HUD_IN, HUD_FADE),
    "  (Widget|SetRenderOpacity :self self :InOpacity (Variables|Default|GetHudAlpha))",
    # render opacity alone does not stop OnPaint, so OnPaint also checks these
    "  (Variables|Default|SetShowSpeedo (and (Variables|Default|GetHaveCar) (> (Variables|Default|GetHudAlpha) 0.01)))",
    "  (Variables|Default|SetShowMap (and (Variables|Default|GetMapInit) (> (Variables|Default|GetHudAlpha) 0.01)))",
    "  (if (Variables|Default|GetMapReady)",
    "    (bind mc (Variables|Default|GetMapC))",
    "    (Widget|Transform|SetRenderTranslation (Variables|Default|GetMapImg) %s)" % mv("(- (.x mc) %g)" % RH, "(- (.y mc) %g)" % RH),
    "    (Widget|Transform|SetRenderTranslation (Variables|Default|GetGaugeImg) (Variables|Default|GetSpeedoO))",
    "    (Widget|SetRenderOpacity :self (Variables|Default|GetMapImg) :InOpacity (Variables|Default|GetHudAlpha))",
    "    (Widget|SetRenderOpacity :self (Variables|Default|GetGaugeImg) :InOpacity (Variables|Default|GetHudAlpha))",
    param("SpeedoMID", "Speed", "(Math|Float|Clamp(Float) (/ (Variables|Default|GetShownSpeed) %.1f) 0.0 1.0)" % SPEED_MAX),
    param("SpeedoMID", "Rpm", "(Variables|Default|GetRpmFrac)"),
    param("SpeedoMID", "Throttle", "(Variables|Default|GetThrottle)"),
    param("SpeedoMID", "Boost", "(Variables|Default|GetBoost)"),
    param("SpeedoMID", "Pop", "(Variables|Default|GetPop)"),
    "    (bind u (Variables|Default|GetMapU))",
    # screen direction of world +X ("N") is (-uy, -ux)
    param("RadarMID", "North", "(Math|Trig|Atan2(Radians) (- 0.0 (.x u)) (- 0.0 (.y u)))") + ")",
    "  (if (not (Variables|Default|GetMapInit))",
    '    (bind rm (Utilities|Casting|CastToBP_RG_RaceManager (Actor|GetActorOfClass "%s"))' % RM_CLASS,
    "      (:then",
    "        (Variables|Default|SetRaceMgr rm)",
    "        (CallFunction|InitMap))",
    "      (:CastFailed))))",
]) + "\n"

# ------------------------------------------------------------------ AttachToHud
def image(var, mat, mid, w, h):
    return """        (bind {v} (Game|ConstructObjectfromClass :Class "/Script/UMG.Image"))
        (Variables|Default|SetTmpBrush (Widget|Brush|MakeBrushfromMaterial "{ui}{m}.{m}" {w:d} {h:d}))
        (Variables|Default|Set{mid} (Widget|Brush|GetDynamicMaterial (Variables|Default|GetTmpBrush)))
        (Class|Image|SetBrush :self {v} :Brush (Variables|Default|GetTmpBrush))
        (Widget|SetVisibility {v} "HitTestInvisible")
        (bind {v}slot (Widget|AddChildtoOverlay overlay {v}))
        (Layout|OverlaySlot|SetHorizontalAlignment {v}slot "HAlign_Left")
        (Layout|OverlaySlot|SetVerticalAlignment {v}slot "VAlign_Top")
        (Variables|Default|Set{var} {v})
""".format(v=var.lower(), ui=UI, m=mat, mid=mid, w=int(w), h=int(h), var=var)


ATTACH = """(fn AttachToHud (HudWidget)
  (if (not (Utilities|String|NotEqual,CaseInsenstive(String) (Game|GetCurrentLevelName true) "Lvl_GardenGrandPrix"))
    (CallFunction|ClimbtoRoot :Child HudWidget)
    (bind overlay (Utilities|Casting|CastToOverlay (Variables|Default|GetHostRoot))
      (:then
""" + image("MapImg", "M_RG_HUD_Radar", "RadarMID", RIMG, RIMG) + image("GaugeImg", "M_RG_HUD_Speedo", "SpeedoMID", SPW, SPH) + """        (bind oslot (Widget|AddChildtoOverlay overlay self))
        (Layout|OverlaySlot|SetHorizontalAlignment oslot "HAlign_Fill")
        (Layout|OverlaySlot|SetVerticalAlignment oslot "VAlign_Fill")
        (Variables|Default|SetMapReady true)
        (bind sbw (UserInterface|CreateWidget :Class "/Game/RacingGame/UI/WBP_RG_Scoreboard.WBP_RG_Scoreboard_C" :OwningPlayer (Widget|GetOwningPlayer)))
        (Class|WBPRGScoreboard|SetHostOverlay :self sbw :HostOverlay overlay)
        (Class|WBPRGScoreboard|AttachTo :self sbw)
        (Variables|Default|SetScoreboard sbw)
        (bind sbox (Widget|GetParent HudWidget))
        (bind hb (Widget|GetParent (Widget|GetParent sbox)))
        (Widget|SetRenderOpacity :self sbox :InOpacity 0.0)
        (for i (range (Widget|Panel|GetChildrenCount hb))
          (bind pw (Utilities|Casting|CastToPanelWidget (Widget|Panel|GetChildAt hb i))
            (:then
              (bind gt (Utilities|Casting|CastToTextBlock (Widget|Panel|GetChildAt pw 0))
                (:then
                  (Widget|SetRenderOpacity :self pw :InOpacity 0.0))
                (:CastFailed)))
            (:CastFailed))))
      (:CastFailed
        (bind canvas (Utilities|Casting|CastToCanvasPanel (Variables|Default|GetHostRoot))
          (:then
            (bind slot (CanvasPanel|AddChildtoCanvas canvas self))
            (Layout|CanvasSlot|SetAnchors slot "(Minimum=(X=0,Y=0),Maximum=(X=1,Y=1))")
            (Layout|CanvasSlot|SetOffsets slot "(Left=0,Top=0,Right=0,Bottom=0)"))
          (:CastFailed
            (UserInterface|Viewport|AddtoPlayerScreen self 5)))))))
"""

# ------------------------------------------------------------------ OnPaint (v6 "Pixar" toy style)
P = []
add = P.append
OUTL = [(-1.7, 0), (1.7, 0), (0, -1.7), (0, 1.7), (-1.2, -1.2), (1.2, -1.2), (-1.2, 1.2), (1.2, 1.2)]


def text(ind, t, x, y, size, face, color, shadow=0.0, outline=None, ow=1.0, offs=None):
    """Draw text; outline = ink colour drawn at 8 (or offs) offsets scaled by ow for a cartoon border."""
    if shadow:
        add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv("(+ %s 0.5)" % x, "(+ %s 3.2)" % y), FONT, size, face, col(*INK, shadow)))
    if outline:
        for ox, oy in (offs or OUTL):
            add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv("(+ %s %g)" % (x, ox * ow), "(+ %s %g)" % (y, oy * ow)), FONT, size, face, outline))
    add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv(x, y), FONT, size, face, color))


def lit(s):
    return '(Utilities|Text|ToText(String) "%s")' % s


def ctext(ind, s_expr, s_len, cx, cy, size, face, color, wfac=0.28, **kw):
    """Text centred on (cx, cy); s_len = character count expression."""
    em = EM * size
    text(ind, s_expr, "(- %s (* %s %.3f))" % (cx, s_len, wfac * em), "(- %s %.3f)" % (cy, 0.572 * em), size, face, color, **kw)


add("(fn OnPaint (Context)")
add("  (bind pxs (Variables|Default|GetPixelScale))")

# --- speedometer text (all positions relative to the speedometer image origin)
I2 = "    "
add("  (if (Variables|Default|GetShowSpeedo)")
add(I2 + "(bind so (Variables|Default|GetSpeedoO))")
add(I2 + "(bind ox (.x so))")
add(I2 + "(bind oy (.y so))")


def at(x, y):
    return "(+ ox %g)" % x, "(+ oy %g)" % y


INKC = col(*INK)
BROWN = col(*BROWN_T)
for v in range(0, int(SPEED_MAX) + 1, 40):
    t = v / SPEED_MAX
    a = math.pi * (1 - t)
    x, y = SC[0] + 166 * math.cos(a), SC[1] - 166 * math.sin(a)
    s = str(v)
    ctext(I2, lit(s), str(len(s)), *at(x, y), 9, "Bold", BROWN)
add(I2 + "(bind ss (Utilities|String|ToString(Integer) (Math|Float|Round (Variables|Default|GetShownSpeed))))")
ctext(I2, "(Utilities|Text|ToText(String) ss)", "(Utilities|String|Len ss)", *at(SC[0], 182), 58, "Bold Italic", col(1, 1, 1),
      shadow=0.45, outline=INKC, ow=2.0)
ctext(I2, lit("KM/H"), "4", *at(SC[0], 224), 12, "Bold Italic", col(*RED), wfac=0.33)
add(I2 + "(bind rs (Variables|Default|GetRpmStr))")
ctext(I2, "(Utilities|Text|ToText(String) rs)", "(Utilities|String|Len rs)", *at(SC[0], 144), 11, "Bold", BROWN, wfac=0.3)
add(I2 + "(bind bst (Variables|Default|GetBoostState))")
add(I2 + "(bind bon (Math|Float|Clamp(Float) (* (- (Variables|Default|GetBoost) 0.6) 4.0) 0.0 1.0))")
ctext(I2, "(Utilities|Text|ToText(String) bst)", "(Utilities|String|Len bst)", *at(SC[0], 116), 9, "Bold Italic",
      "(Utilities|Struct|MakeLinearColor (+ %g (* %g bon)) (+ %g (* %g bon)) (+ %g (* %g bon)) 1.0)"
      % (BROWN_T[0], 1 - BROWN_T[0], BROWN_T[1], 1 - BROWN_T[1], BROWN_T[2], 1 - BROWN_T[2]), wfac=0.34)
add(I2 + "(bind gs (Variables|Default|GetGearStr))")
ctext(I2, "(Utilities|Text|ToText(String) gs)", "(Utilities|String|Len gs)", *at(SC[0], 262), 22, "Bold Italic", col(1, 1, 1),
      wfac=0.3, outline=INKC, ow=1.2, offs=OUTL[:4])
text(I2, lit("ACCEL"), *at(74, 241), 8, "Bold Italic", BROWN)
text(I2, lit("BOOST"), *at(270, 241), 8, "Bold Italic", BROWN)
add(I2 + "(bind bs (Variables|Default|GetBoostStr))")
text(I2, "(Utilities|Text|ToText(String) bs)", "(- (+ ox 390) (* (Utilities|String|Len bs) %.3f))" % (0.6 * EM * 8), "(+ oy 241)", 8,
     "Bold Italic", col(*RED))
add(I2 + "(bind acc (Variables|Default|GetAccel))")
for i in range(3):
    x0 = 160 + i * 9
    add(I2 + "(bind ca%d (Math|Float|Clamp(Float) (/ (- acc %g) 1.5) 0.15 1.0))" % (i, 0.3 + 1.6 * i))
    for (xa, ya), (xb, yb) in (((x0, 242), (x0 + 4, 246.5)), ((x0 + 4, 246.5), (x0, 251))):
        add(I2 + "(Painting|DrawLine Context %s %s (Utilities|Struct|MakeLinearColor %g %g %g ca%d) true 2.6)"
            % (mv(*at(xa, ya)), mv(*at(xb, yb)), ORANGE[0], ORANGE[1], ORANGE[2], i))
P[-1] += ")"

# --- minimap: toy road (ink border, white kerb line, asphalt) with an orange lap-progress line
add("  (if (Variables|Default|GetShowMap)")
for arr in ("WhitePts", "CyanPts"):
    add(I2 + "(Painting|DrawLines Context (Variables|Default|Get%s) %s true 11.5)" % (arr, col(*INK, 0.95)))
for arr in ("WhitePts", "CyanPts"):
    add(I2 + "(Painting|DrawLines Context (Variables|Default|Get%s) %s true 8.5)" % (arr, col(1, 1, 1)))
add(I2 + "(Painting|DrawLines Context (Variables|Default|GetWhitePts) %s true 5.0)" % col(*ASPHALT))
add(I2 + "(Painting|DrawLines Context (Variables|Default|GetCyanPts) %s true 5.0)" % col(*ORANGE))
add(I2 + "(Painting|DrawLines Context (Variables|Default|GetCyanPts) %s true 1.6)" % col(1.0, 0.85, 0.55, 0.9))
add(I2 + "(bind u (Variables|Default|GetMapU))")
add(I2 + "(bind ux (.x u))")
add(I2 + "(bind uy (.y u))")
add(I2 + "(bind wc (Variables|Default|GetWorldC))")
add(I2 + "(bind mc (Variables|Default|GetMapC))")
add(I2 + "(bind sc (Variables|Default|GetMapScale))")


def xf(ind, sfx, wx, wy):
    """World (wx, wy) -> rotated map point sx<sfx>, sy<sfx>."""
    add(ind + "(bind dx%s (* (- %s (.x wc)) sc))" % (sfx, wx))
    add(ind + "(bind dy%s (* (- %s (.y wc)) sc))" % (sfx, wy))
    add(ind + "(bind sx%s (+ (.x mc) (- (* dy%s ux) (* dx%s uy))))" % (sfx, sfx, sfx))
    add(ind + "(bind sy%s (- (.y mc) (+ (* dx%s ux) (* dy%s uy))))" % (sfx, sfx, sfx))


def seg(ind, a, b, color, th):
    add(ind + "(Painting|DrawLine Context %s %s %s true %g)" % (mv("sx" + a, "sy" + a), mv("sx" + b, "sy" + b), color, th))


# checkpoints: red-and-white candy bars across the road
for ci, (pa, pb) in enumerate(CPS):
    xf(I2, "c%da" % ci, "%.1f" % pa[0], "%.1f" % pa[1])
    xf(I2, "c%db" % ci, "%.1f" % pb[0], "%.1f" % pb[1])
    seg(I2, "c%da" % ci, "c%db" % ci, col(*INK), 7.0)
    for i in range(5):
        add(I2 + "(bind sxc%dp%d (+ sxc%da (* (- sxc%db sxc%da) %.3f)))" % (ci, i, ci, ci, ci, i / 4))
        add(I2 + "(bind syc%dp%d (+ syc%da (* (- syc%db syc%da) %.3f)))" % (ci, i, ci, ci, ci, i / 4))
    for i in range(4):
        seg(I2, "c%dp%d" % (ci, i), "c%dp%d" % (ci, i + 1), col(*RED) if i % 2 == 0 else col(1, 1, 1), 4.2)
# finish line: chunky checkered band with an ink border
NCH = 6
xf(I2, "fa", "%.1f" % FIN[0][0], "%.1f" % FIN[0][1])
xf(I2, "fb", "%.1f" % FIN[1][0], "%.1f" % FIN[1][1])
seg(I2, "fa", "fb", col(*INK), 8.0)
for i in range(NCH + 1):
    add(I2 + "(bind sxf%d (+ sxfa (* (- sxfb sxfa) %.4f)))" % (i, i / NCH))
    add(I2 + "(bind syf%d (+ syfa (* (- syfb syfa) %.4f)))" % (i, i / NCH))
for i in range(NCH):
    seg(I2, "f%d" % i, "f%d" % (i + 1), col(1, 1, 1) if i % 2 == 0 else col(*INK), 5.0)
# turn numbers: white with an ink border
for lbl, p in TURNS:
    sfx = "t" + lbl
    xf(I2, sfx, "%.1f" % p[0], "%.1f" % p[1])
    ctext(I2, lit(lbl), str(len(lbl)), "sx" + sfx, "sy" + sfx, 8, "Bold Italic", col(1, 1, 1), outline=INKC, ow=0.9, offs=OUTL[:4])
# compass N on the red rim badge (world +X)
add(I2 + "(bind nx (+ (.x mc) (* (- 0.0 uy) %g)))" % RIM_R)
add(I2 + "(bind ny (+ (.y mc) (* (- 0.0 ux) %g)))" % RIM_R)
ctext(I2, lit("N"), "1", "nx", "(+ ny 0.5)", 9, "Bold", col(1, 1, 1), wfac=0.33)

# opponents: bubbly dots (ink, white rim, colour)
add(I2 + "(bind me (Player|GetOwningPlayerPawn))")
add(I2 + "(bind colors (Variables|Default|GetRacerColors))")
add(I2 + '(bind cars (Actor|GetAllActorsOfClass "/Script/ChaosVehicles.WheeledVehiclePawn"))')
DISC = 6


def disc(ind, cx, cy, radius, color):
    pts = [(radius / 2 * math.cos(2 * math.pi * k / DISC), radius / 2 * math.sin(2 * math.pi * k / DISC)) for k in range(DISC + 1)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        add(ind + "(Painting|DrawLine Context %s %s %s true %g)" % (mv("(+ %s %.3f)" % (cx, x0), "(+ %s %.3f)" % (cy, y0)),
                                                                   mv("(+ %s %.3f)" % (cx, x1), "(+ %s %.3f)" % (cy, y1)), color, radius))


def racer(ind, ci, sfx):
    add(ind + "(bind loc{0} (Transformation|GetActorLocation :self car))".format(sfx))
    xf(ind, "r" + sfx, "(.x loc%s)" % sfx, "(.y loc%s)" % sfx)
    add(ind + "(bind rc{0} (Utilities|Array|Get(acopy) colors {1}))".format(sfx, ci))
    disc(ind, "sxr" + sfx, "syr" + sfx, 10.0, col(*INK))
    disc(ind, "sxr" + sfx, "syr" + sfx, 7.6, col(1, 1, 1))
    disc(ind, "sxr" + sfx, "syr" + sfx, 5.2, "rc" + sfx)


add(I2 + "(for i (range (Utilities|Array|Length cars))")
add(I2 + "  (bind car (Utilities|Array|Get(acopy) cars i))")
add(I2 + "  (if (!= car me)")
add(I2 + "    (bind ps (Class|Pawn|GetPlayerState car))")
add(I2 + "    (Utilities|IsValid ps")
add(I2 + '      (:"Is Valid"')
racer(I2 + "        ", "(Math|Integer|%(Integer) (Class|PlayerState|GetPlayerId ps) 7)", "A")
add(I2 + "        )")
add(I2 + '      (:"Is Not Valid"')
add(I2 + "        (Utilities|IsValid (Pawn|GetController car)")
add(I2 + '          (:"Is Valid"')
racer(I2 + "            ", "(Math|Integer|%(Integer) i 7)", "B")
add(I2 + "            )")
add(I2 + '          (:"Is Not Valid"))))))')

# you: chunky race-car-red arrow, white rim, ink border, soft white bounce ring
TIP, BACK, HALF, NOTCH = 13.0, -7.5, 8.0, -2.5
I3 = I2 + "    "
add(I2 + "(Utilities|IsValid me")
add(I2 + '  (:"Is Valid"')
add(I3 + "(bind ploc (Transformation|GetActorLocation :self me))")
xf(I3, "p", "(.x ploc)", "(.y ploc)")
add(I3 + "(bind pf (Transformation|GetActorForwardVector :self me))")
add(I3 + "(bind fx (- (* (.y pf) ux) (* (.x pf) uy)))")
add(I3 + "(bind fy (- 0.0 (+ (* (.x pf) ux) (* (.y pf) uy))))")
add(I3 + "(bind hr (* 14.0 (+ 1.0 (* 0.1 (Math|Trig|Sin(Degrees) (* (Utilities|Time|GetRealTimeSeconds) 260.0))))))")
HSEG = 12
for kseg in range(HSEG):
    a0, a1 = 2 * math.pi * kseg / HSEG, 2 * math.pi * (kseg + 1) / HSEG
    add(I3 + "(Painting|DrawLine Context %s %s %s true 3.0)" % (
        mv("(+ sxp (* hr %.4f))" % math.cos(a0), "(+ syp (* hr %.4f))" % math.sin(a0)),
        mv("(+ sxp (* hr %.4f))" % math.cos(a1), "(+ syp (* hr %.4f))" % math.sin(a1)), col(1, 1, 1, 0.75)))


def apt(nm, fa, fb):
    add(I3 + "(bind %s (Math|Vector2D|MakeVector2D (+ sxp (- (* fx %g) (* fy %g))) (+ syp (+ (* fy %g) (* fx %g)))))" % (nm, fa, fb, fa, fb))


apt("atip", TIP, 0)
apt("abl", BACK, HALF)
apt("ant", NOTCH, 0)
apt("abr", BACK, -HALF)
fan = []
for kf in range(1, 5):
    tf = kf / 5
    fan += [("afa%d" % kf, BACK + (NOTCH - BACK) * tf, HALF * (1 - tf)), ("afb%d" % kf, BACK + (NOTCH - BACK) * tf, -HALF * (1 - tf))]
for nm, fa, fb in fan:
    apt(nm, fa, fb)
edges = [("atip", "abl"), ("abl", "ant"), ("ant", "abr"), ("abr", "atip")]
for a, b in edges:
    add(I3 + "(Painting|DrawLine Context %s %s %s true 6.0)" % (a, b, col(*INK)))
for a, b in edges:
    add(I3 + "(Painting|DrawLine Context %s %s %s true 3.2)" % (a, b, col(1, 1, 1)))
for nm in ["abl", "ant", "abr"] + [x[0] for x in fan]:
    add(I3 + "(Painting|DrawLine Context atip %s %s true 2.4)" % (nm, col(*RED)))
add(I3 + ")")
add(I2 + '  (:"Is Not Valid"))))')

# Slate scales line positions by DPI but not thickness: scale every thickness by PixelScale
P = [re.sub(r"(true|false) ([0-9.]+)\)(\)*)$", r"\1 (* pxs \2))\3", ln) if "Painting|DrawLine" in ln else ln for ln in P]
ONPAINT = "\n".join(P) + "\n"

OUT = {"hud5_onpaint": ONPAINT, "hud5_tick": TICK, "hud5_attach": ATTACH, "hud5_initmap": INIT,
       "hud5_updatemap": UPDATE, "hud5_readcar": READ}
os.makedirs(SAVED, exist_ok=True)
for nm, code in OUT.items():
    open(os.path.join(HERE, nm + ".dsl"), "w", encoding="utf-8").write(code)
    open(os.path.join(SAVED, nm + ".txt"), "w", encoding="utf-8").write(code)
defaults = {"RacerColors": [{"r": r, "g": g, "b": b, "a": 1.0} for r, g, b in RACER_COLORS]}
json.dump(defaults, open(os.path.join(HERE, "hud5_defaults.json"), "w"))
print("turns", len(TURNS), "start idx", I_START, "OnPaint lines", len(P),
      "paint nodes", sum(ln.count("(Painting|") for ln in P))
