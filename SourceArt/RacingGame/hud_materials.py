# HUD v4 (2026-10-30): UI materials for the Garden Grand Prix HUD skin. Body for the unreal-mcp
# ProgrammaticToolset (paste inline; the sandbox has no exec). Each material is a single Custom HLSL
# node in UI space: shapes are signed distances anti-aliased with fwidth, so they stay crisp at any size.
# Animated values come in through the Image tint (vertex colour), so no dynamic material instances:
#   M_RG_HUD_Gauge  tint.r = 0.5 + 0.5 * speed fill, tint.g = 0.5 + 0.5 * redline pulse, tint.b = tint.a = 1
#   M_RG_HUD_Badge  tint.rgb = gear colour, tint.a = 0.5 + 0.5 * pop (alpha 0 would cull the draw)
#   M_RG_HUD_Panel  rounded glass plate with drop shadow, rim light, racing stripes and accent bar
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
float3 ACC = float3(1.0, 0.05, 0.35);
float3 HOT = float3(1.0, 0.12, 0.02);
float3 GLASS_A = float3(0.07, 0.075, 0.10);
float3 GLASS_B = float3(0.012, 0.014, 0.024);
'''
# "over" compositing, written out per layer: col/al are premultiplied, unpremultiplied at the end
def over(c, o):
    return '{ float oo = saturate(%s); col = col * (1.0 - oo) + (%s) * oo; al = al + oo * (1.0 - al); }\n' % (o, c)


# Slate multiplies a UI material's output by the Image tint (vertex colour); divide it back out so the tint only carries data
END = 'return float4(col / max(al, 1e-4) / max(VC, 0.02), al / max(VA, 0.02));'

GAUGE = COMMON + '''
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
float aa = max(fwidth(r), 1e-4);
float a = degrees(atan2(p.y, p.x)); if (a < 0) a += 360.0;
float t = a - 150.0; if (t < 0) t += 360.0; t /= 240.0;
float P = saturate(VC.r * 2.0 - 1.0);
float L = 4.18879 * r;
float te = (t <= 1.0) ? min(t, 1.0 - t) : -min(t - 1.0, 1.5 - t);
float mArc = saturate(te * L / aa + 0.5);
float band = saturate((0.05 - abs(r - 0.82)) / aa + 0.5);
float lit = saturate((P - t) * L / aa + 0.5) * mArc;
float3 lc = (t < 0.55) ? lerp(float3(1, 1, 1), ACC, t / 0.55) : lerp(ACC, HOT, (t - 0.55) / 0.45);
float pulse = 1.0 + saturate(VC.g * 2.0 - 1.0) * 0.35 * sin(Time * 14.0);
lc = saturate(lc * pulse);
''' + over('float3(0,0,0)', '0.38 * (1.0 - smoothstep(0.66, 0.99, r))') + \
    over('lerp(GLASS_A, GLASS_B, saturate(r / 0.75)) + 0.06 * saturate(-p.y) * (1.0 - r)', '0.52 * saturate((0.75 - r) / aa + 0.5)') + \
    over('float3(1,1,1)', '0.13 * saturate(1.0 - abs(r - 0.75) / (aa * 1.3))') + \
    over('float3(1,1,1)', '0.24 * band * mArc * step(t, 0.85)') + \
    over('HOT', '0.55 * band * mArc * step(0.85, t)') + \
    over('lc', '0.30 * exp(-pow((r - 0.82) / 0.085, 2.0)) * lit') + \
    over('lc', 'band * lit') + '''
float th = radians(150.0 + 240.0 * P);
float2 h = 0.82 * float2(cos(th), sin(th));
float2 dh = p - h;
''' + over('lerp(float3(1,1,1), lc, 0.35)', '0.85 * exp(-dot(dh, dh) / 0.0045) * step(0.004, P)') + '''
float k = round(t * 10.0);
float ti = k / 10.0;
float dl = abs(t - ti) * L;
bool major = fmod(k, 2.0) < 0.5;
float rmax = major ? 0.975 : 0.945;
float tick = saturate((0.009 - dl) / aa + 0.5) * saturate((rmax - r) / aa + 0.5) * saturate((r - 0.905) / aa + 0.5) * step(t, 1.001);
float tl = step(ti, P + 0.001);
''' + over('lerp(float3(1,1,1), lerp(float3(1,1,1), lc, 0.4), tl)', 'tick * (major ? 0.8 : 0.42) * (0.75 + 0.25 * tl)') + END

BADGE = COMMON + '''
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
float aa = max(fwidth(r), 1e-4);
float pop = saturate(VA * 2.0 - 1.0);
float3 gc = VC;
float sh = 0.8 + 0.35 * (0.5 + 0.5 * cos(atan2(p.y, p.x) - Time * 1.6));
float rw = 0.055 + 0.03 * pop;
''' + over('float3(0,0,0)', '0.38 * (1.0 - smoothstep(0.62, 0.98, r))') + \
    over('gc', '(0.22 + 0.5 * pop) * exp(-pow((r - 0.80) / (0.09 + 0.06 * pop), 2.0))') + \
    over('lerp(GLASS_A, GLASS_B, saturate(r / 0.72)) + 0.07 * saturate(-p.y) * (1.0 - r)', '0.58 * saturate((0.72 - r) / aa + 0.5)') + \
    over('float3(1,1,1)', '0.14 * saturate(1.0 - abs(r - 0.72) / (aa * 1.3))') + \
    over('saturate(gc * sh + 0.25 * pop)', 'saturate((rw - abs(r - 0.80)) / aa + 0.5)') + END

PANEL = COMMON + '''
float2 fw = max(fwidth(UV), 1e-5);
float2 S = 1.0 / fw;
float2 q = UV * S;
float m = Inset * S.y;
float rad = Radius * S.y;
float2 c = S * 0.5;
float2 hs = c - m;
float2 d0 = abs(q - c) - hs + rad;
float sd = length(max(d0, 0.0)) + min(max(d0.x, d0.y), 0.0) - rad;
float2 d1 = abs(q - c - float2(0, m * 0.35)) - hs + rad;
float sds = length(max(d1, 0.0)) + min(max(d1.x, d1.y), 0.0) - rad;
float inM = saturate(0.5 - sd);
float v = saturate((q.y - (c.y - hs.y)) / (2.0 * hs.y));
float u = saturate((q.x - (c.x - hs.x)) / (2.0 * hs.x));
float stripe = step(0.5, frac((q.x + q.y) / (S.y * 0.045))) * saturate((u - 0.62) / 0.38) * saturate(1.0 - v / 0.45);
float bar = saturate(1.6 - abs(q.y - (c.y + hs.y - 5.0))) * saturate(min(q.x - (c.x - hs.x + rad), (c.x + hs.x - rad) - q.x) / (hs.x * 0.3));
float sw = exp(-pow(u - (frac(Time * 0.11) * 1.6 - 0.3), 2.0) / 0.006);
''' + over('float3(0,0,0)', '0.36 * (1.0 - smoothstep(-rad * 0.3, m * 0.95, sds))') + \
    over('lerp(GLASS_A, GLASS_B, v) + 0.035 * stripe', 'inM * lerp(0.50, 0.68, v)') + \
    over('float3(1,1,1)', 'saturate(1.0 - abs(sd + 0.75)) * (0.07 + 0.16 * (1.0 - v))') + \
    over('saturate(ACC * (0.85 + 0.7 * sw))', 'bar * inM') + END

SPECS = [
    ('M_RG_HUD_Gauge', GAUGE, [], []),
    ('M_RG_HUD_Badge', BADGE, [], []),
    ('M_RG_HUD_Panel', PANEL, [('Inset', 0.0515), ('Radius', 0.085)], []),
]


def build(name, code, scalars):
    path = FOLD + '/' + name
    if t(AT + 'exists', {'path': path}):
        t(AT + 'delete', {'path': path})
    mat = t(M + 'create_material', {'folder_path': FOLD, 'asset_name': name})
    sp(mat, {'MaterialDomain': 'MD_UI', 'BlendMode': 'BLEND_Translucent'})
    ins = ['UV', 'VC', 'VA', 'Time'] + [s[0] for s in scalars]
    cu = expr(mat, 'Custom', 0, 0, {'code': code, 'outputType': 'CMOT_Float4'})
    # inputs must grow one at a time, re-sending the stored elements unchanged (ArrayAdd is ambiguous otherwise)
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
    return {'built': [build(n, c, s) for n, c, s, _ in SPECS]}
