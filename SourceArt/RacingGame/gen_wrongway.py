"""WRONG WAY warning for Lvl_GardenGrandPrix (2026-11-01).

User request: if the player drives the wrong direction for a certain time, show WRONG WAY with a Pixar-style animated UI.

WBP_RG_WrongWay is created by WBP_RG_Scoreboard.AttachTo into the vehicle HUD's root Overlay (sign Image first, then
the widget itself for the text). Each tick it reads the RaceManager: the player's nearest centreline point (LastIdx of
the player's slot in Cars) and its race direction (TrackYaw). Velocity along that direction below -3 m/s for WRONG_SECS
-> the sign pops in (damped-spring scale, then a gentle wobble and breathe); back above +1.5 m/s -> it shrinks away.
Only while the race runs (after GO, before you finish).

Writes wrongway_{attach,tick,onpaint}.dsl and wrongway_material.txt (+ Saved/RacingGame/*.txt).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(HERE, "..", "..", "Saved", "RacingGame")
RM_C = "/Game/RacingGame/Gameplay/BP_RG_RaceManager.BP_RG_RaceManager_C"
FONT = '"/Engine/EngineFonts/Roboto.Roboto"'
EM = 96.0 / 72.0
WRONG_SECS = 2.0
SW, SH = 560.0, 230.0           # sign image; the sign is centred on SignC
SIGN_Y = 0.16                    # top of the sign as a fraction of the screen height
INK = (0.10, 0.055, 0.03)


def col(r, g, b, a=1.0):
    return '"(R=%g,G=%g,B=%g,A=%g)"' % (r, g, b, a)


def mv(x, y):
    return "(Math|Vector2D|MakeVector2D %s %s)" % (x, y)


def mgr(n):
    return "(Class|BPRGRaceManager|Get%s mgr)" % n


def get(a, i):
    return "(Utilities|Array|Get(acopy) %s %s)" % (a, i)


ATTACH = """(fn AttachTo ()
  (bind ov (Variables|Default|GetHostOverlay))
  (bind img (Game|ConstructObjectfromClass :Class "/Script/UMG.Image"))
  (Variables|Default|SetTmpBrush (Widget|Brush|MakeBrushfromMaterial "/Game/RacingGame/UI/M_RG_HUD_WrongWay.M_RG_HUD_WrongWay" %d %d))
  (Class|Image|SetBrush :self img :Brush (Variables|Default|GetTmpBrush))
  (Widget|SetVisibility img "HitTestInvisible")
  (Widget|SetRenderOpacity :self img :InOpacity 0.0)
  (bind islot (Widget|AddChildtoOverlay ov img))
  (Layout|OverlaySlot|SetHorizontalAlignment islot "HAlign_Left")
  (Layout|OverlaySlot|SetVerticalAlignment islot "VAlign_Top")
  (Variables|Default|SetSignImg img)
  (bind sslot (Widget|AddChildtoOverlay ov self))
  (Layout|OverlaySlot|SetHorizontalAlignment sslot "HAlign_Fill")
  (Layout|OverlaySlot|SetVerticalAlignment sslot "VAlign_Fill")
  (Widget|SetVisibility self "HitTestInvisible")
  (Widget|SetRenderOpacity :self self :InOpacity 0.0)
  (Variables|Default|SetAttached true))
""" % (SW, SH)

TICK = """(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (bind ls (UserInterface|Geometry|GetLocalSize MyGeometry))
  (Variables|Default|SetScreenSize ls)
  (bind dt InDeltaTime)
  (if (and (Variables|Default|GetReady) (Variables|Default|GetAttached))
    (bind mgr (Variables|Default|GetMgr))
    (bind cars %(cars)s)
    (bind me (Player|GetOwningPlayerPawn))
    (Variables|Default|SetMeSlot -1)
    (for i (range (Utilities|Array|Length cars))
      (if (== (Utilities|Array|Get(acopy) cars i) me)
        (Variables|Default|SetMeSlot i)))
    (bind ms (Variables|Default|GetMeSlot))
    ; wrong way = moving against the race direction at the nearest centreline point
    (if (and (>= ms 0) (> %(racet)s 0.5))
      (bind yaw (Utilities|Array|Get(acopy) %(tyaw)s (Utilities|Array|Get(acopy) %(lidx)s ms)))
      (bind v (Transformation|GetVelocity me))
      (bind along (+ (* (.x v) (Math|Trig|Cos(Degrees) yaw)) (* (.y v) (Math|Trig|Sin(Degrees) yaw))))
      (if (and (< along -300.0) (<= (Utilities|Array|Get(acopy) %(fint)s ms) 0.0))
        (Variables|Default|SetWrongT (+ (Variables|Default|GetWrongT) dt))
        (elif (> along 150.0)
          (Variables|Default|SetWrongT 0.0)))
      (else
        (Variables|Default|SetWrongT 0.0)))
    (if (>= (Variables|Default|GetWrongT) %(secs).1f)
      (if (not (Variables|Default|GetShowing))
        (Variables|Default|SetShowing true)
        (Variables|Default|SetShowT 0.0))
      (Variables|Default|SetShowT (+ (Variables|Default|GetShowT) dt))
      (Variables|Default|SetA (Math|Interpolation|FInterpTo (Variables|Default|GetA) 1.0 dt 14.0))
      (else
        (Variables|Default|SetShowing false)
        (Variables|Default|SetA (Math|Interpolation|FInterpTo (Variables|Default|GetA) 0.0 dt 9.0))))
    ; Pixar-style motion: damped-spring pop-in (overshoot ~1.3), then breathe + wobble; shrinks as it fades out
    (bind t (Variables|Default|GetShowT))
    (bind pop (- 1.0 (* (Math|Float|Exp (* -6.5 t)) (Math|Trig|Cos(Radians) (* 13.0 t)))))
    (bind breathe (+ 1.0 (* 0.035 (Math|Trig|Sin(Radians) (* 6.0 t)))))
    (bind a (Variables|Default|GetA))
    (Variables|Default|SetScale (* (* pop breathe) (+ 0.55 (* 0.45 a))))
    (Variables|Default|SetAng (* 4.0 (Math|Trig|Sin(Radians) (* 4.5 t))))
    (Variables|Default|SetPaint (> a 0.01))
    (Variables|Default|SetSignC %(signc)s)
    (bind c (Variables|Default|GetSignC))
    (bind s (Variables|Default|GetScale))
    (bind img (Variables|Default|GetSignImg))
    (Widget|Transform|SetRenderTranslation img %(imgpos)s)
    (Widget|Transform|SetRenderScale img (Math|Vector2D|MakeVector2D s s))
    (Widget|Transform|SetRenderTransformAngle img (Variables|Default|GetAng))
    (Widget|SetRenderOpacity :self img :InOpacity a)
    (Widget|Transform|SetRenderTransformPivot self (Math|Vector2D|MakeVector2D 0.5 (/ (.y c) (Math|Float|Max(Float) (.y ls) 1.0))))
    (Widget|Transform|SetRenderScale self (Math|Vector2D|MakeVector2D s s))
    (Widget|Transform|SetRenderTransformAngle self (Variables|Default|GetAng))
    (Widget|SetRenderOpacity :self self :InOpacity a))
  (if (not (Variables|Default|GetReady))
    (bind m (Utilities|Casting|CastToBP_RG_RaceManager (Actor|GetActorOfClass "%(rm)s"))
      (:then
        (Variables|Default|SetMgr m)
        (Variables|Default|SetReady true))
      (:CastFailed))))
""" % dict(cars=mgr("Cars"), racet=mgr("RaceT"), tyaw=mgr("TrackYaw"), lidx=mgr("LastIdx"), fint=mgr("FinishT"),
           secs=WRONG_SECS, rm=RM_C,
           signc=mv("(* 0.5 (.x ls))", "(+ (* (.y ls) %.2f) %.1f)" % (SIGN_Y, SH / 2)),
           imgpos=mv("(- (.x c) %.1f)" % (SW / 2), "(- (.y c) %.1f)" % (SH / 2)))

P = []
add = P.append
OUTL = [(-1, 0), (1, 0), (0, -1), (0, 1), (-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)]


def text(ind, t, x, y, size, color, ow, shadow=0.0):
    if shadow:
        add(ind + '(Painting|DrawText Context %s %s %s %d "Bold Italic" %s)' % (t, mv("(+ %s 1.0)" % x, "(+ %s 5.0)" % y), FONT, size, col(*INK, shadow)))
    for ox, oy in OUTL:
        add(ind + '(Painting|DrawText Context %s %s %s %d "Bold Italic" %s)' % (t, mv("(+ %s %g)" % (x, ox * ow), "(+ %s %g)" % (y, oy * ow)), FONT, size, col(*INK)))
    add(ind + '(Painting|DrawText Context %s %s %s %d "Bold Italic" %s)' % (t, mv(x, y), FONT, size, color))


add("(fn OnPaint (Context)")
add("  (if (Variables|Default|GetPaint)")
add("    (bind c (Variables|Default|GetSignC))")
I = "    "
TX = 72.0                       # text block centre, right of the U-turn badge
s1, em1 = 46, EM * 46
text(I, '(Utilities|Text|ToText(String) "WRONG WAY!")', "(- (+ (.x c) %g) %.3f)" % (TX, 10 * 0.6 * em1 / 2), "(- (.y c) %.3f)" % (0.572 * em1 + 20),
     s1, col(1, 1, 1), 3.0, shadow=0.45)
s2, em2 = 18, EM * 18
text(I, '(Utilities|Text|ToText(String) "TURN AROUND")', "(- (+ (.x c) %g) %.3f)" % (TX, 11 * 0.6 * em2 / 2), "(- (.y c) %.3f)" % (0.572 * em2 - 36),
     s2, col(1, 0.9, 0.62), 1.8)
P[-1] += "))"
ONPAINT = "\n".join(P) + "\n"


def over(c, o):
    return '{ float oo = saturate(%s); col = col * (1.0 - oo) + (%s) * oo; al = al + oo * (1.0 - al); }\n' % (o, c)


# sign: red-orange rounded plate, thick ink outline, white inner stroke, gloss, pulsing outer glow, U-turn badge
MAT = '''
float3 col = 0; float al = 0;
float3 INK = float3(0.10, 0.055, 0.03);
float3 RED = float3(0.90, 0.10, 0.05);
float3 ORA = float3(1.0, 0.45, 0.12);
float2 q = UV * float2(560.0, 230.0);
float aa = max(length(fwidth(q)) * 0.7071, 1e-3);
float pulse = 0.5 + 0.5 * sin(Time * 7.0);
float2 d0 = abs(q - float2(280.0, 112.0)) - float2(258.0, 92.0) + 44.0;
float sd = length(max(d0, 0.0)) + min(max(d0.x, d0.y), 0.0) - 44.0;
float2 d1 = abs(q - float2(280.0, 120.0)) - float2(258.0, 92.0) + 44.0;
float sds = length(max(d1, 0.0)) + min(max(d1.x, d1.y), 0.0) - 44.0;
float2 p = q - float2(95.0, 112.0);
float rb = length(p);
// U-turn arrow: upper half ring, right stem, left stem with a downward arrowhead
float2 pa = p - float2(0.0, -4.0);
float arc = (pa.y < 0.0) ? abs(length(pa) - 22.0) - 5.5 : 1e3;
float2 rs = abs(p - float2(22.0, 12.0)) - float2(5.5, 16.0);
float stemR = length(max(rs, 0.0)) + min(max(rs.x, rs.y), 0.0);
float2 ls = abs(p - float2(-22.0, 2.0)) - float2(5.5, 6.0);
float stemL = length(max(ls, 0.0)) + min(max(ls.x, ls.y), 0.0);
float tri = max(max(p.y - 32.0, 8.0 - p.y), abs(p.x + 22.0) - (32.0 - p.y) * 0.62);
float icon = min(min(arc, stemR), min(stemL, tri));
''' + over('ORA', '(0.25 + 0.3 * pulse) * (1.0 - smoothstep(0.0, 16.0, sd)) * step(0.0, sd)') + \
    over('INK', '0.4 * (1.0 - smoothstep(-2.0, 12.0, sds))') + \
    over('INK', 'saturate(-sd / aa + 0.5)') + \
    over('lerp(RED, ORA, saturate((112.0 - q.y) / 92.0) * 0.8)', 'saturate((-sd - 6.0) / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.9 * saturate(1.0 - abs(sd + 12.0) / (aa + 1.2))') + \
    over('float3(1, 1, 1)', '0.28 * saturate((-sd - 14.0) / aa + 0.5) * saturate(1.0 - length((q - float2(300.0, 52.0)) / float2(230.0, 34.0)))') + \
    over('INK', 'saturate((61.0 - rb) / aa + 0.5)') + \
    over('float3(1, 0.98, 0.92)', 'saturate((56.0 - rb) / aa + 0.5)') + \
    over('RED', 'saturate(-icon / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.5 * saturate((10.0 - length(p - float2(-24.0, -30.0))) / aa + 0.5)') + \
    'return float4(col / max(al, 1e-4) / max(VC, 0.02), al / max(VA, 0.02));'

os.makedirs(SAVED, exist_ok=True)
for nm, code in (("wrongway_attach", ATTACH), ("wrongway_tick", TICK), ("wrongway_onpaint", ONPAINT), ("wrongway_material", MAT)):
    ext = ".txt" if nm.endswith("material") else ".dsl"
    open(os.path.join(HERE, nm + ext), "w", encoding="utf-8").write(code)
    open(os.path.join(SAVED, nm + ".txt"), "w", encoding="utf-8").write(code)
print("ok")
