"""Builds the Blueprint DSL for WBP_RG_Minimap, which is also the Garden Grand Prix HUD skin (v4, 2026-10-30), and the
CDO defaults from minimap.json (run gen_minimap.py first).
Outputs: minimap_onpaint.dsl, minimap_tick.dsl, minimap_attach.dsl, minimap_defaults.json (+ .txt copies in Saved/RacingGame
because AssetTools.read_file only reads .txt/.json under Content/ or Saved/).

v4 look (Forza Horizon / Speedstorm inspired, user request "improve only the visuals"):
- Panels, the speed dial and the gear badge are UI materials (hud_materials.py) on three Image widgets that AttachToHud
  creates in UI_Vehicle's root Overlay *before* adding this widget, so this widget's OnPaint text sits on top of them.
  Animated values go in through the Image tint: dial tint.r/g = 0.5 + 0.5 * (speed fill / redline pulse); badge tint =
  gear colour with alpha = 0.5 + 0.5 * pop. Slate multiplies the material output by the tint, so the materials divide it back out. (The v3 draft drew all of that with thousands of DrawLine nodes and hung the editor.)
- UI_Vehicle's SpeedLabel / UnitLabel / GearLabel keep updating exactly as before (UpdateSpeed / UpdateGear untouched) but
  their two boxes are drawn at opacity 0; Tick measures where the labels sit, so the new speedometer stays in the same
  screen place, and copies their text, which OnPaint draws in Roboto Bold Italic over the dial and badge.
- Minimap: same corner and size, now on a rounded glass plate, with a slimmer outlined road, a checkered start line with
  an accent chevron (the START / FINISH tag was removed to declutter), racer dots and a breathing halo on your arrow.
"""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "minimap.json")))
W, H = 300.0, 220.0
MARGIN = 24.0        # gap to the screen corner (slate units)
FONT = '"/Engine/EngineFonts/Roboto.Roboto"'
UI = "/Game/RacingGame/UI/"

# theme: dark glass, white type, hot-pink accent (no blue or yellow, earlier user request)
ACCENT = (1.0, 0.05, 0.35)
INK = (0.015, 0.015, 0.02)
RACER_COLORS = [(0.9, 0.03, 0.03), (1.0, 0.3, 0.0), (0.1, 0.75, 0.15), (1.0, 0.1, 0.55),
                (0.45, 0.1, 0.8), (0.0, 0.55, 0.35), (1.0, 0.45, 0.35)]
GEAR_COLS = {"R": (1.0, 0.12, 0.08), "N": (0.62, 0.65, 0.72)}

# Image sizes (slate units) and placement relative to the measured label centres
MAP_PAD, MAP_SH = 12.0, 14.0                      # glass padding around the map, shadow margin of the panel image
MAP_IMG = (W + 2 * (MAP_PAD + MAP_SH), H + 2 * (MAP_PAD + MAP_SH))    # 352 x 272 (Inset 14/272 in the material)
GAUGE = 210.0                                     # dial image, centred on the speed number
BADGE = 92.0                                      # gear badge image
BADGE_OFF = (-4.0, 6.0)                           # badge centre relative to the gear label centre
SPEED_FS, UNIT_FS, GEAR_FS, GTAG_FS = 42, 12, 30, 10
EM = 96.0 / 72.0                                  # Slate font size -> em in slate units


def col(r, g, b, a=1.0):
    return '"(R=%g,G=%g,B=%g,A=%g)"' % (r, g, b, a)


def txt(s):
    return '(Utilities|Text|ToText(String) "%s")' % s


def v2(x, y):
    return '"(X=%.2f,Y=%.2f)"' % (x, y)


def mv(x, y):
    return "(Math|Vector2D|MakeVector2D %s %s)" % (x, y)


L = []
add = L.append
add("(fn OnPaint (Context)")

# -- map: soft shadow, dark outline, light road
T_BODY, T_EDGE, T_SHADOW = 7.0, 11.0, 14.0
SHADOW_OFF = (1.2, 2.2)
add("  (Painting|DrawLines Context (Variables|Default|GetTrackShadow) %s true %g)" % (col(0, 0, 0, 0.32), T_SHADOW))
add("  (Painting|DrawLines Context (Variables|Default|GetTrackPoints) %s true %g)" % (col(*INK, 0.95), T_EDGE))
add("  (Painting|DrawLines Context (Variables|Default|GetTrackPoints) %s true %g)" % (col(0.95, 0.96, 0.97, 1.0), T_BODY))
# checkered start line across the road + accent chevron for the race direction
sx, sy = D["start"]
f = D["start_dir"]
r = (-f[1], f[0])
sq, n = 2.4, 5
half = n * sq / 2
c0 = (sx - r[0] * half, sy - r[1] * half)
add("  (Painting|DrawLine Context %s %s %s true %g)" % (v2(*c0), v2(sx + r[0] * half, sy + r[1] * half), col(1, 1, 1), 2 * sq))
for k in range(n):
    for row in (0, 1):
        if (k + row) % 2:
            continue
        o = (row - 0.5) * sq
        p0 = (c0[0] + r[0] * k * sq + f[0] * o, c0[1] + r[1] * k * sq + f[1] * o)
        add("  (Painting|DrawLine Context %s %s %s true %g)" % (v2(*p0), v2(p0[0] + r[0] * sq, p0[1] + r[1] * sq), col(*INK), sq))
cx = sx + f[0] * 10
add("  (Painting|DrawLine Context %s %s %s true 1.8)" % (v2(cx - 2.4, sy - 3.2), v2(cx + 1.0, sy), col(*ACCENT)))
add("  (Painting|DrawLine Context %s %s %s true 1.8)" % (v2(cx + 1.0, sy), v2(cx - 2.4, sy + 3.2), col(*ACCENT)))


# -- speedometer + gear text (positions measured in Tick, in the HUD root's space; PaintOff = this widget's translation)
def text(ind, t, x, y, size, face, color, shadow=True):
    if shadow:
        add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv("(+ %s 1.5)" % x, "(+ %s 2.0)" % y), FONT, size, face, col(0, 0, 0, 0.6)))
    add(ind + '(Painting|DrawText Context %s %s %s %d "%s" %s)' % (t, mv(x, y), FONT, size, face, color))


I2 = "    "
add("  (if (Variables|Default|GetSpeedoReady)")
add(I2 + "(bind po (Variables|Default|GetPaintOff))")
add(I2 + "(bind sc (Variables|Default|GetSpeedoC))")
add(I2 + "(bind gc (Variables|Default|GetGearC))")
add(I2 + "(bind scx (- (.x sc) (.x po)))")
add(I2 + "(bind scy (- (.y sc) (.y po)))")
add(I2 + "(bind gcx (- (+ (.x gc) %g) (.x po)))" % BADGE_OFF[0])
add(I2 + "(bind gcy (- (+ (.y gc) %g) (.y po)))" % BADGE_OFF[1])
# Roboto digits are tabular (0.56 em); the digit centre sits 0.572 em below the line top
add(I2 + "(bind ss (Variables|Default|GetSpeedStr))")
text(I2, "(Utilities|Text|ToText(String) ss)", "(- scx (* (Utilities|String|Len ss) %.3f))" % (0.28 * EM * SPEED_FS),
     "(- scy %.3f)" % (0.572 * EM * SPEED_FS + 6), SPEED_FS, "Bold Italic", col(1, 1, 1))
add(I2 + "(bind us (Variables|Default|GetUnitStr))")
text(I2, "(Utilities|Text|ToText(String) us)", "(- scx (* (Utilities|String|Len us) %.3f))" % (0.33 * EM * UNIT_FS),
     "(+ scy 22.0)", UNIT_FS, "Bold", col(*ACCENT), shadow=False)
add(I2 + "(bind gs (Variables|Default|GetGearStr))")
text(I2, "(Utilities|Text|ToText(String) gs)", "(- gcx (* (Utilities|String|Len gs) %.3f))" % (0.31 * EM * GEAR_FS),
     "(- gcy %.3f)" % (0.572 * EM * GEAR_FS), GEAR_FS, "Bold Italic", col(1, 1, 1))
text(I2, txt("GEAR"), "(- gcx %.3f)" % (4 * 0.33 * EM * GTAG_FS), "(+ gcy %.1f)" % (BADGE / 2 - 2), GTAG_FS, "Bold",
     col(1, 1, 1, 0.65), shadow=False)
L[-1] += ")"

# -- racers: every wheeled vehicle that is driven (has a controller or a player state)
add("  (bind scale (Variables|Default|GetMapScale))")
add("  (bind off (Variables|Default|GetMapOffset))")
add("  (bind colors (Variables|Default|GetRacerColors))")
add("  (bind me (Player|GetOwningPlayerPawn))")
add('  (bind cars (Actor|GetAllActorsOfClass "/Script/ChaosVehicles.WheeledVehiclePawn"))')
DISC_SEGS = 8


def disc(ind, cx, cy, radius, color):
    """Filled disc: a ring of DISC_SEGS segments at radius/2 drawn radius thick."""
    pts = [(radius / 2 * math.cos(2 * math.pi * k / DISC_SEGS), radius / 2 * math.sin(2 * math.pi * k / DISC_SEGS)) for k in range(DISC_SEGS + 1)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        add(ind + "(Painting|DrawLine Context (Math|Vector2D|MakeVector2D (+ %s %.3f) (+ %s %.3f)) (Math|Vector2D|MakeVector2D (+ %s %.3f) (+ %s %.3f)) %s true %g)"
            % (cx, x0, cy, y0, cx, x1, cy, y1, color, radius))


RACER_R, RACER_RIM = 5.0, 1.6


def racer(ind, ci, sfx):
    """Round marker for another racer, coloured by RacerColors[ci]. DSL binds are unique per copy (sfx)."""
    add(ind + "(bind loc{0} (Transformation|GetActorLocation :self car))".format(sfx))
    add(ind + "(bind mx{0} (+ (* (.x loc{0}) scale) (.x off)))".format(sfx))
    add(ind + "(bind my{0} (+ (* (.y loc{0}) scale) (.y off)))".format(sfx))
    add(ind + "(bind rc{0} (Utilities|Array|Get(acopy) colors {1}))".format(sfx, ci))
    disc(ind, "mx" + sfx, "my" + sfx, RACER_R + RACER_RIM, col(1, 1, 1))
    disc(ind, "mx" + sfx, "my" + sfx, RACER_R, "rc" + sfx)


# Blueprint IsValid is a branching macro here, so each branch carries its own copy of the drawing code.
add("  (for i (range (Utilities|Array|Length cars))")
add("    (bind car (Utilities|Array|Get(acopy) cars i))")
add("    (if (!= car me)")
add("      (bind ps (Class|Pawn|GetPlayerState car))")
add("      (Utilities|IsValid ps")
add('        (:"Is Valid"')
racer("          ", "(Math|Integer|%(Integer) (Class|PlayerState|GetPlayerId ps) 7)", "A")
add("          )")
add('        (:"Is Not Valid"')
add("          (Utilities|IsValid (Pawn|GetController car)")
add('            (:"Is Valid"')
racer("              ", "(Math|Integer|%(Integer) i 7)", "B")
add("              )")
add('            (:"Is Not Valid"))))))')

# -- local player: arrow pointing along the car's yaw, with a softly breathing halo
TIP, BACK, HALF, NOTCH = 13.0, -7.0, 7.5, -2.5
HALO_R, HALO_SEGS = 12.5, 16


def pt2v(cx, cy, rvar, ang):
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return "(Math|Vector2D|MakeVector2D (+ %s (* %s %.4f)) (+ %s (* %s %.4f)))" % (cx, rvar, c, cy, rvar, s)


def arrow(ind, ci, sfx):
    add(ind + "(bind pc%s (Utilities|Array|Get(acopy) colors %s))" % (sfx, ci))
    add(ind + "(bind hr%s (* %g (+ 1.0 (* 0.12 (Math|Trig|Sin(Degrees) (* (Utilities|Time|GetRealTimeSeconds) 250.0))))))" % (sfx, HALO_R))
    for k in range(HALO_SEGS):
        a0, a1 = 360.0 * k / HALO_SEGS, 360.0 * (k + 1) / HALO_SEGS
        add(ind + "(Painting|DrawLine Context %s %s pc%s true 1.6)" % (pt2v("px", "py", "hr" + sfx, a0), pt2v("px", "py", "hr" + sfx, a1), sfx))

    def pt(name, fa, fb):
        # map point = p + f*fa + r*fb, r = (-fy, fx)
        add(ind + "(bind %s%s (Math|Vector2D|MakeVector2D (+ px (- (* fx %g) (* fy %g))) (+ py (+ (* fy %g) (* fx %g)))))" % (name, sfx, fa, fb, fa, fb))

    pt("tip", TIP, 0)
    pt("bl", BACK, HALF)
    pt("nt", NOTCH, 0)
    pt("br", BACK, -HALF)
    fan = []
    for k in range(1, 6):
        t = k / 6
        fan.append(("fa%d" % k, BACK + (NOTCH - BACK) * t, HALF * (1 - t)))
        fan.append(("fb%d" % k, BACK + (NOTCH - BACK) * t, -HALF * (1 - t)))
    for nme, fa, fb in fan:
        pt(nme, fa, fb)
    edges = [("tip", "bl"), ("bl", "nt"), ("nt", "br"), ("br", "tip")]
    for e in edges:   # dark outline, colour fill (fan from the tip), white rim
        add(ind + "(Painting|DrawLine Context %s%s %s%s %s true 4.5)" % (e[0], sfx, e[1], sfx, col(*INK)))
    for nme in ["bl", "nt", "br"] + [x[0] for x in fan]:
        add(ind + "(Painting|DrawLine Context tip{0} {1}{0} pc{0} true 2.4)".format(sfx, nme))
    for e in edges:
        add(ind + "(Painting|DrawLine Context %s%s %s%s %s true 1.4)" % (e[0], sfx, e[1], sfx, col(1, 1, 1)))


add("  (Utilities|IsValid me")
add('    (:"Is Valid"')
add("      (bind ploc (Transformation|GetActorLocation :self me))")
add("      (bind px (+ (* (.x ploc) scale) (.x off)))")
add("      (bind py (+ (* (.y ploc) scale) (.y off)))")
# heading from the forward vector (the DSL's .yaw on a rotator picked the wrong BreakRotator pin)
add("      (bind fwd (Transformation|GetActorForwardVector :self me))")
add("      (bind fx (.x fwd))")
add("      (bind fy (.y fwd))")
add("      (bind mps (Class|Pawn|GetPlayerState me))")
add("      (Utilities|IsValid mps")
add('        (:"Is Valid"')
arrow("          ", "(Math|Integer|%(Integer) (Class|PlayerState|GetPlayerId mps) 7)", "A")
add("          )")
add('        (:"Is Not Valid"')
arrow("          ", "0", "B")
add("          )))")
add('    (:"Is Not Valid")))')
# Slate scales line positions by the DPI scale but not line thickness, so every thickness is
# multiplied by PixelScale (absolute/local size, measured in Tick) to keep proportions at any resolution.
L.insert(1, "  (bind pxs (Variables|Default|GetPixelScale))")
L = [re.sub(r"(true|false) ([0-9.]+)\)(\)*)$", r"\1 (* pxs \2))\3", ln) if "Painting|DrawLine" in ln else ln for ln in L]
open(os.path.join(HERE, "minimap_onpaint.dsl"), "w", encoding="utf-8").write("\n".join(L) + "\n")


# -- AttachToHud: find UI_Vehicle's labels from the speed label it passes in, create the three HUD images in the HUD's
# root Overlay (before this widget, so they draw underneath its text), add this widget full-size, hide the old boxes.
def image(var, mat, w, h, tint, vis):
    return """        (bind %s (Game|ConstructObjectfromClass :Class "/Script/UMG.Image"))
        (Class|Image|SetBrush :self %s :Brush (Widget|Brush|MakeBrushfromMaterial "%s%s.%s" %d %d))
        (Class|Image|SetColorandOpacity :self %s :ColorAndOpacity %s)
        (Widget|SetVisibility %s "%s")
        (bind %sslot (Widget|AddChildtoOverlay overlay %s))
        (Layout|OverlaySlot|SetHorizontalAlignment %sslot "HAlign_Left")
        (Layout|OverlaySlot|SetVerticalAlignment %sslot "VAlign_Top")
        (Variables|Default|Set%s %s)
""" % (var, var, UI, mat, mat, w, h, var, col(*tint), var, vis, var, var, var, var, VARN[var], var)


VARN = {"mapimg": "MapImg", "gaugeimg": "GaugeImg", "badgeimg": "BadgeImg"}   # local bind -> member variable
# DSL casts are exec casts: a failed cast silently ends the chain, so the map is attached first, the gear box is found by
# scanning the speed row for the panel whose first child is a TextBlock (the speed SizeBox's first child is a VerticalBox),
# and the dial / badge (created collapsed so they still sit under this widget's text) are only shown once the labels are found.
# The old label boxes go to opacity 0.004, not 0: a widget at opacity 0 is not painted, so its cached geometry reads (0,0).
A = """(fn AttachToHud (HudWidget)
  (if (not (Utilities|String|NotEqual,CaseInsenstive(String) (Game|GetCurrentLevelName true) "Lvl_GardenGrandPrix"))
    (CallFunction|ClimbtoRoot :Child HudWidget)
    (bind overlay (Utilities|Casting|CastToOverlay (Variables|Default|GetHostRoot))
      (:then
""" + image("mapimg", "M_RG_HUD_Panel", MAP_IMG[0], MAP_IMG[1], (1, 1, 1, 1), "HitTestInvisible") \
    + image("gaugeimg", "M_RG_HUD_Gauge", GAUGE, GAUGE, (0.5, 0.5, 1, 1), "Collapsed") \
    + image("badgeimg", "M_RG_HUD_Badge", BADGE, BADGE, ACCENT + (0.5,), "Collapsed") + """        (bind oslot (Widget|AddChildtoOverlay overlay self))
        (Layout|OverlaySlot|SetHorizontalAlignment oslot "HAlign_Fill")
        (Layout|OverlaySlot|SetVerticalAlignment oslot "VAlign_Fill")
        (Variables|Default|SetMapReady true)
        (bind sbox (Widget|GetParent HudWidget))
        (bind hb (Widget|GetParent (Widget|GetParent sbox)))
        (Variables|Default|SetSpeedBox sbox)
        (Variables|Default|SetSpeedRow hb)
        (for i (range (Widget|Panel|GetChildrenCount hb))
          (bind pw (Utilities|Casting|CastToPanelWidget (Widget|Panel|GetChildAt hb i))
            (:then
              (bind gt (Utilities|Casting|CastToTextBlock (Widget|Panel|GetChildAt pw 0))
                (:then
                  (Variables|Default|SetGearBox pw)
                  (Variables|Default|SetGearText gt))
                (:CastFailed)))
            (:CastFailed)))
        (bind st (Utilities|Casting|CastToTextBlock HudWidget)
          (:then
            (Variables|Default|SetSpeedText st)
            (bind ut (Utilities|Casting|CastToTextBlock (Widget|Panel|GetChildAt sbox 1))
              (:then
                (Variables|Default|SetUnitText ut)
                (Utilities|IsValid (Variables|Default|GetGearText)
                  (:"Is Valid"
                    (Widget|SetRenderOpacity :self sbox :InOpacity 0.004)
                    (Widget|SetRenderOpacity :self (Variables|Default|GetGearBox) :InOpacity 0.004)
                    (Widget|SetVisibility (Variables|Default|GetGaugeImg) "HitTestInvisible")
                    (Widget|SetVisibility (Variables|Default|GetBadgeImg) "HitTestInvisible")
                    (Variables|Default|SetSpeedoReady true))
                  (:"Is Not Valid")))
              (:CastFailed)))
          (:CastFailed)))
      (:CastFailed
        (bind canvas (Utilities|Casting|CastToCanvasPanel (Variables|Default|GetHostRoot))
          (:then
            (bind slot (CanvasPanel|AddChildtoCanvas canvas self))
            (Layout|CanvasSlot|SetAnchors slot "(Minimum=(X=0,Y=0),Maximum=(X=1,Y=1))")
            (Layout|CanvasSlot|SetOffsets slot "(Left=0,Top=0,Right=0,Bottom=0)"))
          (:CastFailed
            (UserInterface|Viewport|AddtoPlayerScreen self 5)))))))
"""
open(os.path.join(HERE, "minimap_attach.dsl"), "w", encoding="utf-8").write(A)


# -- Tick: pin the map to the corner, place the images on the label centres, copy the label text, animate.
# The labels report correct sizes but no position (their cached / paint-space geometry has an identity transform), so the
# centres come from UI_Vehicle's fixed layout: the speed row is anchored bottom-right with 32 padding, each box has 16
# slot padding; the speed box (SizeBox, fill) is on the right with the number at its top, the gear box is bottom-aligned
# on the left with the gear number at its top.
ROW_PAD, SLOT_PAD = 32.0, 16.0


def size(var, nm):
    return "    (bind %s (UserInterface|Geometry|GetLocalSize (Widget|GetCachedGeometry (Variables|Default|Get%s))))" % (nm, var)


CENTRES = [size("HostRoot", "hz"), size("SpeedRow", "rz"), size("SpeedBox", "sbz"), size("SpeedText", "sgz"),
           size("GearBox", "gbz"), size("GearText", "ggz"),
           "    (bind sgc %s)" % mv("(- (- (.x hz) %g) (* (.x sbz) 0.5))" % (ROW_PAD + SLOT_PAD),
                                  "(+ (- (- (.y hz) %g) (.y rz)) (* (.y sgz) 0.5))" % (ROW_PAD - SLOT_PAD)),
           "    (bind ggc %s)" % mv("(+ (- (- (.x hz) %g) (.x rz)) (* (.x gbz) 0.5))" % (ROW_PAD - SLOT_PAD),
                                  "(+ (- (- (.y hz) %g) (.y gbz)) (* (.y ggz) 0.5))" % (ROW_PAD + SLOT_PAD))]


def place(img, cx, cy, size):
    return "    (Widget|Transform|SetRenderTranslation (Variables|Default|Get%s) %s)" % (img, mv("(- %s %g)" % (cx, size / 2), "(- %s %g)" % (cy, size / 2)))


T = ["(event UserInterface|EventTick (MyGeometry InDeltaTime)",
     "  (bind local (UserInterface|Geometry|GetLocalSize MyGeometry))",
     "  (Variables|Default|SetPixelScale (/ (.x (UserInterface|Geometry|GetAbsoluteSize MyGeometry)) (Math|Float|Max(Float) (.x local) 1.0)))",
     "  (bind ty (- (.y local) %g))" % (H + MARGIN),
     "  (bind tr %s)" % mv(MARGIN, "ty"),
     "  (Widget|Transform|SetRenderTranslation self tr)",
     "  (Variables|Default|SetPaintOff tr)",
     "  (Variables|Default|SetPop (Math|Interpolation|FInterpTo (Variables|Default|GetPop) 0.0 InDeltaTime 4.0))",
     "  (if (Variables|Default|GetMapReady)",
     "    (Widget|Transform|SetRenderTranslation (Variables|Default|GetMapImg) %s))" % mv(MARGIN - MAP_PAD - MAP_SH, "(- ty %g)" % (MAP_PAD + MAP_SH)),
     "  (if (Variables|Default|GetSpeedoReady)"]
T += CENTRES
T += ["    (Variables|Default|SetSpeedoC sgc)",
      "    (Variables|Default|SetGearC ggc)",
      place("GaugeImg", "(.x sgc)", "(.y sgc)", GAUGE),
      place("BadgeImg", "(+ (.x ggc) %g)" % BADGE_OFF[0], "(+ (.y ggc) %g)" % BADGE_OFF[1], BADGE),
      "    (bind ss (Utilities|String|ToString(Text) (Widget|GetText(Text) (Variables|Default|GetSpeedText))))",
      "    (Variables|Default|SetSpeedStr ss)",
      "    (bind us (Utilities|String|ToString(Text) (Utilities|Text|TexttoUpper (Widget|GetText(Text) (Variables|Default|GetUnitText)))))",
      "    (Variables|Default|SetUnitStr us)",
      "    (bind gs (Utilities|String|ToString(Text) (Widget|GetText(Text) (Variables|Default|GetGearText))))",
      "    (if (Utilities|String|NotEqual,CaseInsenstive(String) gs (Variables|Default|GetLastGear))",
      "      (Variables|Default|SetPop 1.0)",
      "      (Variables|Default|SetLastGear gs))",
      "    (Variables|Default|SetGearStr gs)",
      # gear colour and dial range (if/elif: the DSL's select may invert its branches)
      '    (if (Utilities|String|Equal,CaseInsensitive(String) gs "R")',
      "      (Variables|Default|SetGearRGB (Math|Vector|MakeVector %g %g %g))" % GEAR_COLS["R"],
      '      (elif (Utilities|String|Equal,CaseInsensitive(String) gs "N")',
      "        (Variables|Default|SetGearRGB (Math|Vector|MakeVector %g %g %g))" % GEAR_COLS["N"],
      "        (else",
      "          (Variables|Default|SetGearRGB (Math|Vector|MakeVector %g %g %g)))))" % ACCENT,
      '    (if (Utilities|String|Equal,CaseInsensitive(String) us "MPH")',
      "      (Variables|Default|SetSpeedMax 125.0)",
      "      (else",
      "        (Variables|Default|SetSpeedMax 200.0)))",
      "    (bind fr (Math|Float|Clamp(Float) (/ (Utilities|String|StringToFloat ss) (Variables|Default|GetSpeedMax)) 0.0 1.0))",
      "    (Variables|Default|SetShownFrac (Math|Interpolation|FInterpTo (Variables|Default|GetShownFrac) fr InDeltaTime 8.0))",
      "    (bind sf (Variables|Default|GetShownFrac))",
      "    (Class|Image|SetColorandOpacity :self (Variables|Default|GetGaugeImg) :ColorAndOpacity (Utilities|Struct|MakeLinearColor (+ 0.5 (* 0.5 sf)) (+ 0.5 (* 0.5 (Math|Float|Clamp(Float) (* (- sf 0.85) 6.67) 0.0 1.0))) 1.0 1.0))",
      "    (bind grgb (Variables|Default|GetGearRGB))",
      "    (Class|Image|SetColorandOpacity :self (Variables|Default|GetBadgeImg) :ColorAndOpacity (Utilities|Struct|MakeLinearColor (.x grgb) (.y grgb) (.z grgb) (+ 0.5 (* 0.5 (Variables|Default|GetPop)))))))"]
open(os.path.join(HERE, "minimap_tick.dsl"), "w", encoding="utf-8").write("\n".join(T) + "\n")

A2 = """(fn ClimbToRoot (Child)
  (bind parent (Widget|GetParent Child))
  (Utilities|IsValid parent
    (:"Is Valid"
      (CallFunction|ClimbtoRoot :Child parent))
    (:"Is Not Valid"
      (Variables|Default|SetHostRoot Child))))
"""

defaults = {
    "TrackPoints": [{"x": x, "y": y} for x, y in D["points"]],
    "TrackShadow": [{"x": x + SHADOW_OFF[0], "y": y + SHADOW_OFF[1]} for x, y in D["points"]],
    "RacerColors": [{"r": r, "g": g, "b": b, "a": 1.0} for r, g, b in RACER_COLORS],
    "MapScale": D["scale"],
    "MapOffset": {"x": D["offset"][0], "y": D["offset"][1]},
}
json.dump(defaults, open(os.path.join(HERE, "minimap_defaults.json"), "w"))
SAVED = os.path.join(HERE, "..", "..", "Saved", "RacingGame")
os.makedirs(SAVED, exist_ok=True)
for nm in ("minimap_onpaint", "minimap_attach", "minimap_tick"):
    open(os.path.join(SAVED, nm + ".txt"), "w", encoding="utf-8").write(open(os.path.join(HERE, nm + ".dsl"), encoding="utf-8").read())
json.dump(defaults, open(os.path.join(SAVED, "minimap_defaults.json"), "w"))
print(len(L), "OnPaint lines,", sum(ln.count("(Painting|") for ln in L), "paint nodes")
