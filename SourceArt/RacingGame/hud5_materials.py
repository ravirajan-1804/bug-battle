# HUD v6 (2026-11-01): UI materials for the Pixar-style toy HUD (v5 cyan version: Saved/RG_backup_hud_v5). Body for the unreal-mcp ProgrammaticToolset
# (paste inline; the sandbox has no exec). Same build recipe as hud_materials.py (one Custom HLSL node, signed
# distances anti-aliased with fwidth), but the live values come in as scalar parameters on a dynamic material
# instance (AttachToHud makes one per Image via Widget|Brush|GetDynamicMaterial), so they are exact floats.
#   M_RG_HUD_Radar   North (radians, screen angle of world +X) -> the compass bezel turns with the map
#   M_RG_HUD_Speedo  Speed, Rpm, Throttle, Boost (0..1), Pop (gear-change flash, 0..1)
import json
M = 'editor_toolset.toolsets.material.MaterialTools.'
O = 'editor_toolset.toolsets.object.ObjectTools.'
AT = 'editor_toolset.toolsets.asset.AssetTools.'
FOLD = '/Game/RacingGame/UI'


def t(n, a):
    return execute_tool(n, json.dumps(a))['returnValue']


def sp(obj, vals):
    return t(O + 'set_properties', {'instance': obj, 'values': json.dumps(vals)})


def expr(mat, cls, x, y, props=None):
    e = t(M + 'add_expression', {'material_or_function': mat, 'expression_class': {'refPath': '/Script/Engine.MaterialExpression' + cls}, 'x': x, 'y': y})
    if props:
        sp(e, props)
    return e


def link(mat, s, so, d, di):
    t(M + 'connect_expressions', {'from_expression': s, 'from_output_name': so, 'to_expression': d, 'to_input_name': di})


COMMON = '''
float3 col = 0; float al = 0;
float3 INK = float3(0.10, 0.055, 0.03);
float3 CREAM = float3(1.0, 0.94, 0.80);
float3 CREAM2 = float3(0.95, 0.80, 0.58);
float3 TAN = float3(0.80, 0.68, 0.52);
float3 ORA = float3(1.0, 0.55, 0.06);
float3 RED = float3(0.92, 0.12, 0.06);
float3 GR1 = float3(0.40, 0.74, 0.25);
float3 GR2 = float3(0.33, 0.65, 0.20);
float PI = 3.14159265;
'''


def over(c, o):
    return '{ float oo = saturate(%s); col = col * (1.0 - oo) + (%s) * oo; al = al + oo * (1.0 - al); }\n' % (o, c)


# the Image tint stays white; dividing it out keeps the colours exact if someone tints the widget later
END = 'return float4(col / max(al, 1e-4) / max(VC, 0.02), al / max(VA, 0.02));'

# v6 "Pixar" radar: mown-lawn disc (stripes turn with the map), cream bezel with an ink outline, gloss, ink tick
# dots and a red N badge on the bezel, soft drop shadow
RADAR = COMMON + '''
float2 q = (UV - 0.5) * 336.0;
float aa = max(length(fwidth(q)) * 0.7071, 1e-3);
float r = length(q);
float2 nd = float2(cos(North), sin(North));
float2 qs = q - float2(0.0, 5.0);
float rs = length(qs);
float a = atan2(q.y, q.x) - North;
a = a - 2.0 * PI * floor(a / (2.0 * PI));
float k = round(a / (PI / 6.0));
float2 tp = 153.5 * float2(cos(k * PI / 6.0 + North), sin(k * PI / 6.0 + North));
float dot12 = length(q - tp);
bool isN = fmod(k + 12.0, 12.0) < 0.5;
float2 nq = q - nd * 153.5;
float s = dot(q, nd) / 26.0;
float stripe = saturate((abs(frac(s) - 0.5) - 0.25) / (aa / 26.0) + 0.5);
float3 lawn = lerp(GR2, GR1, stripe);
lawn *= lerp(1.0, 0.72, smoothstep(118.0, 147.0, r));
lawn = lerp(lawn, lawn * 1.15 + 0.03, saturate(-q.y / 147.0) * 0.5);
float gloss = saturate(-q.y / 160.0);
''' + over('INK', '0.32 * (1.0 - smoothstep(158.0, 168.0, rs))') + \
    over('INK', 'saturate((162.5 - r) / aa + 0.5)') + \
    over('lerp(CREAM2, CREAM, gloss) + 0.08 * gloss', 'saturate((160.0 - r) / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.45 * saturate(1.0 - abs(r - 157.5) / (aa + 0.9)) * smoothstep(0.1, 0.8, gloss)') + \
    over('INK', 'saturate((149.5 - r) / aa + 0.5)') + \
    over('lawn', 'saturate((147.0 - r) / aa + 0.5)') + \
    over('INK', '0.22 * saturate((147.0 - r) / aa + 0.5) * (1.0 - smoothstep(138.0, 147.0, r))') + \
    over('INK', '(isN ? 0.0 : 0.85) * saturate((2.2 - dot12) / aa + 0.5)') + \
    over('INK', 'saturate((11.5 - length(nq)) / aa + 0.5)') + \
    over('RED', 'saturate((9.2 - length(nq)) / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.35 * saturate((5.0 - length(nq - float2(-2.5, -3.5))) / aa + 0.5)') + END

# v6 "Pixar" speedometer: cream toy dashboard with a thick ink outline and drop shadow, chunky orange->red speed
# segments with a red pointer, an inner RPM arc, a red gear roundel, TURBO pill and ACCEL / BOOST bars
SPEEDO = COMMON + '''
float2 q = UV * float2(460.0, 292.0);
float aa = max(length(fwidth(q)) * 0.7071, 1e-3);
float2 d = q - float2(230.0, 236.0);
float r = length(d);
float ang = atan2(-d.y, d.x);
float t = 1.0 - ang / PI;
float Lr = PI * r;
float mArc = (t <= 1.0) ? saturate(min(t, 1.0 - t) * Lr / aa + 0.5) : 0.0;
float SP = saturate(Speed), RP = saturate(Rpm), TH = saturate(Throttle), BO = saturate(Boost), PO = saturate(Pop);
float sdDisc = max(r - 220.0, d.y);
float2 bq = abs(q - float2(230.0, 260.0)) - float2(180.0, 26.0) + 14.0;
float sdBar = length(max(bq, 0.0)) + min(max(bq.x, bq.y), 0.0) - 14.0;
float sd = min(sdDisc, sdBar);
float2 d2 = d - float2(0.0, 6.0);
float sdS = min(max(length(d2) - 220.0, d2.y), length(max(abs(q - float2(230.0, 266.0)) - float2(166.0, 12.0), 0.0)) - 14.0);
float gl = saturate((236.0 - q.y) / 236.0);
// speed arc: chunky segments over an ink channel
float chan = saturate((14.5 - abs(r - 193.0)) / aa + 0.5) * mArc;
float bandS = saturate((11.5 - abs(r - 193.0)) / aa + 0.5) * mArc;
float fs = frac(t * 30.0);
float gapS = saturate((min(fs, 1.0 - fs) * Lr / 30.0 - 1.6) / aa + 0.5);
float litS = saturate((SP - t) * Lr / aa + 0.5);
float3 rampS = (t < 0.55) ? lerp(float3(1.0, 0.72, 0.15), ORA, t / 0.55) : lerp(ORA, RED, saturate((t - 0.55) / 0.45));
rampS = lerp(rampS, float3(1, 1, 1), 0.3 * saturate((r - 193.0) / 11.0));
// ticks
float kk = round(t * 12.0); float dl = abs(t - kk / 12.0) * Lr;
bool maj = fmod(kk, 2.0) < 0.5;
float tick = saturate(((maj ? 1.8 : 1.1) - dl) / aa + 0.5) * saturate(((maj ? 217.0 : 213.0) - r) / aa + 0.5) * saturate((r - 208.5) / aa + 0.5) * step(-0.002, t) * step(t, 1.002);
// rpm arc
float chanR = saturate((7.5 - abs(r - 145.0)) / aa + 0.5) * mArc;
float bandR = saturate((5.0 - abs(r - 145.0)) / aa + 0.5) * mArc;
float fr = frac(t * 24.0);
float gapR = saturate((min(fr, 1.0 - fr) * Lr / 24.0 - 1.2) / aa + 0.5);
float litR = saturate((RP - t) * Lr / aa + 0.5);
float red = step(0.85, t);
float flash = (RP > 0.88) ? (0.6 + 0.4 * sin(Time * 30.0)) : 1.0;
float3 rampR = lerp(lerp(float3(1.0, 0.72, 0.15), ORA, t), RED * flash + (1.0 - flash) * float3(1, 1, 1), red);
// pointer
float th = PI * (1.0 - SP);
float2 ax = float2(cos(th), -sin(th));
float2 pr = float2(dot(d, ax), dot(d, float2(-ax.y, ax.x)));
float h = saturate((pr.x - 150.0) / 66.0);
float wdt = lerp(6.5, 2.0, h);
float sdN = max(abs(pr.y) - wdt, max(150.0 - pr.x, pr.x - 216.0));
// inner face, turbo pill, bars, gear roundel
float inI = saturate((131.0 - r) / aa + 0.5) * saturate(-d.y / aa + 0.5);
float2 pq = abs(q - float2(230.0, 116.0)) - float2(33.0, 10.0) + 10.0;
float sdT = length(max(pq, 0.0)) + min(max(pq.x, pq.y), 0.0) - 10.0;
float bon = saturate((BO - 0.6) * 4.0);
float2 aq = abs(q - float2(132.0, 268.0)) - float2(60.0, 5.0) + 5.0;
float sdA = length(max(aq, 0.0)) + min(max(aq.x, aq.y), 0.0) - 5.0;
float2 oq = abs(q - float2(330.0, 268.0)) - float2(60.0, 5.0) + 5.0;
float sdO = length(max(oq, 0.0)) + min(max(oq.x, oq.y), 0.0) - 5.0;
float fillA = saturate((72.0 + 120.0 * TH - q.x) / aa + 0.5);
float fillO = saturate((270.0 + 120.0 * BO - q.x) / aa + 0.5);
float bp = (BO > 0.85) ? (0.8 + 0.2 * sin(Time * 12.0)) : 1.0;
float rg = length(q - float2(230.0, 262.0));
float rgo = 22.0 + 2.5 * PO;
''' + over('INK', '0.35 * (1.0 - smoothstep(-2.0, 9.0, sdS))') + \
    over('INK', 'saturate(-sd / aa + 0.5)') + \
    over('lerp(CREAM2, CREAM, gl)', 'saturate((-sd - 3.5) / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.35 * saturate(1.0 - length((q - float2(230.0, 70.0)) / float2(170.0, 42.0))) * saturate((-sd - 3.5) / aa + 0.5)') + \
    over('lerp(CREAM2 * 0.92, CREAM * 0.97, gl)', 'inI') + \
    over('INK', '0.55 * saturate(1.0 - abs(r - 131.0) / (aa + 0.8)) * saturate(-d.y / aa + 0.5)') + \
    over('INK', 'chan') + \
    over('TAN', 'bandS * gapS') + \
    over('rampS', 'bandS * gapS * litS') + \
    over('INK', 'tick') + \
    over('INK', 'chanR') + \
    over('lerp(TAN, float3(0.95, 0.62, 0.55), red)', 'bandR * gapR') + \
    over('rampR', 'bandR * gapR * litR') + \
    over('INK', '0.3 * (1.0 - smoothstep(-1.0, 5.0, sdN - 0.0)) * step(0.002, SP + 0.002)') + \
    over('INK', 'saturate((2.2 - sdN) / aa + 0.5)') + \
    over('lerp(RED, float3(1.0, 0.45, 0.35), saturate(-pr.y / max(wdt, 0.1)) * 0.6)', 'saturate(-sdN / aa + 0.5)') + \
    over('ORA', '0.5 * bon * (1.0 - smoothstep(0.0, 8.0, sdT)) * step(0.0, sdT)') + \
    over('INK', 'saturate((2.2 - sdT) / aa + 0.5)') + \
    over('lerp(TAN, ORA, bon)', 'saturate(-sdT / aa + 0.5)') + \
    over('INK', 'saturate((2.0 - sdA) / aa + 0.5)') + \
    over('TAN', 'saturate(-sdA / aa + 0.5)') + \
    over('lerp(ORA, RED, saturate((q.x - 72.0) / 120.0))', 'saturate(-sdA / aa + 0.5) * fillA') + \
    over('float3(1, 1, 1)', '0.35 * saturate(-sdA / aa + 0.5) * fillA * saturate((265.0 - q.y) / 3.0)') + \
    over('INK', 'saturate((2.0 - sdO) / aa + 0.5)') + \
    over('TAN', 'saturate(-sdO / aa + 0.5)') + \
    over('lerp(RED, float3(1.0, 0.3, 0.55), saturate((q.x - 270.0) / 120.0)) * bp', 'saturate(-sdO / aa + 0.5) * fillO') + \
    over('float3(1, 1, 1)', '0.35 * saturate(-sdO / aa + 0.5) * fillO * saturate((265.0 - q.y) / 3.0)') + \
    over('INK', 'saturate((rgo + 2.6 - rg) / aa + 0.5)') + \
    over('lerp(RED, float3(1.0, 0.4, 0.2), PO)', 'saturate((rgo - rg) / aa + 0.5)') + \
    over('float3(1, 1, 1)', '0.3 * saturate((rgo - 4.0 - length(q - float2(224.0, 254.0))) / aa + 0.5) * saturate((254.0 - q.y) / 4.0)') + END

SPECS = [
    ('M_RG_HUD_Radar', RADAR, [('North', 0.0)]),
    ('M_RG_HUD_Speedo', SPEEDO, [('Speed', 0.0), ('Rpm', 0.0), ('Throttle', 0.0), ('Boost', 0.0), ('Pop', 0.0)]),
]


def build(name, code, scalars):
    path = FOLD + '/' + name
    if t(AT + 'exists', {'path': path}):
        t(AT + 'delete', {'path': path})
    mat = t(M + 'create_material', {'folder_path': FOLD, 'asset_name': name})
    sp(mat, {'MaterialDomain': 'MD_UI', 'BlendMode': 'BLEND_Translucent'})
    ins = ['UV', 'VC', 'VA', 'Time'] + [s[0] for s in scalars]
    cu = expr(mat, 'Custom', 0, 0, {'code': code, 'outputType': 'CMOT_Float4'})
    for k, nm in enumerate(ins):
        cur = json.loads(t(O + 'get_properties', {'instance': cu, 'properties': ['Inputs']}))['Inputs']
        if k == 0:
            cur[0]['inputName'] = nm
        else:
            cur.append(dict(cur[0], inputName=nm))
        sp(cu, {'Inputs': cur})
    uv = expr(mat, 'TextureCoordinate', -500, -200)
    vc = expr(mat, 'VertexColor', -500, 0)
    tm = expr(mat, 'Time', -500, 200)
    link(mat, uv, '', cu, 'UV')
    link(mat, vc, '', cu, 'VC')
    link(mat, vc, 'A', cu, 'VA')
    link(mat, tm, '', cu, 'Time')
    for i, (pn, val) in enumerate(scalars):
        s = expr(mat, 'ScalarParameter', -500, 400 + 150 * i, {'parameterName': pn, 'defaultValue': val})
        link(mat, s, '', cu, pn)
    rgb = expr(mat, 'ComponentMask', 300, -100, {'r': True, 'g': True, 'b': True, 'a': False})
    alpha = expr(mat, 'ComponentMask', 300, 100, {'r': False, 'g': False, 'b': False, 'a': True})
    link(mat, cu, '', rgb, '')
    link(mat, cu, '', alpha, '')
    t(M + 'connect_to_output', {'expression': rgb, 'output_name': '', 'material_property': 'MP_EmissiveColor'})
    t(M + 'connect_to_output', {'expression': alpha, 'output_name': '', 'material_property': 'MP_Opacity'})
    t(M + 'recompile', {'material_or_function': mat})
    t(AT + 'save_assets', {'asset_paths': [path]})
    return path


def run():
    return {'built': [build(n, c, s) for n, c, s in SPECS]}
