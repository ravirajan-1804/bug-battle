# Body for the unreal-mcp ProgrammaticToolset (run via mk.py, which prepends hdr.py):
# builds M_BB_Food, a procedural "realistic food" master. All detail is generated from world
# position divided by Scale (240 = the bug-scale factor), so frequencies are per real-life cm.
FOLD = '/Game/BugBattle/Materials'

LIB = '''struct FN {
  float h(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
  float n(float3 x) {
    float3 i = floor(x); float3 f = frac(x); f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(h(i), h(i + float3(1, 0, 0)), f.x), lerp(h(i + float3(0, 1, 0)), h(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(h(i + float3(0, 0, 1)), h(i + float3(1, 0, 1)), f.x), lerp(h(i + float3(0, 1, 1)), h(i + float3(1, 1, 1)), f.x), f.y), f.z);
  }
  float fbm(float3 p) {
    float s = 0.0, a = 0.5;
    for (int k = 0; k < 5; k++) { s += a * n(p); p = p * 2.03 + float3(17.1, 9.2, 4.7); a *= 0.5; }
    return s / 0.97;
  }
  float cell(float3 p) {
    float3 i = floor(p); float3 f = frac(p); float d = 8.0;
    for (int z = -1; z <= 1; z++) for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
      float3 o = float3(x, y, z);
      float3 r = o + float3(h(i + o), h(i + o + 31.3), h(i + o + 71.7)) - f;
      d = min(d, dot(r, r));
    }
    return sqrt(d);
  }
  float height(float3 p, float bf, float ba, float pf, float pa) {
    float v = ba * fbm(p * bf);
    if (pa > 0.001) v -= pa * (1.0 - smoothstep(0.05, 0.42, cell(p * pf)));
    return v;
  }
};
FN F;
'''

NORMAL = LIB + '''float3 p = WP / Scale;
float e = 0.12 / max(max(BumpFreq, PoreFreq), 0.01);
float h0 = F.height(p, BumpFreq, BumpAmt, PoreFreq, PoreAmt);
float3 g = float3(F.height(p + float3(e, 0, 0), BumpFreq, BumpAmt, PoreFreq, PoreAmt) - h0,
                  F.height(p + float3(0, e, 0), BumpFreq, BumpAmt, PoreFreq, PoreAmt) - h0,
                  F.height(p + float3(0, 0, e), BumpFreq, BumpAmt, PoreFreq, PoreAmt) - h0) / e;
float3 nn = normalize(N);
float3 gt = g - dot(g, nn) * nn;
return normalize(nn - NormalStr * gt);'''

COLOR = LIB + '''float3 p = WP / Scale;
float v = saturate(0.5 + (F.fbm(p * ColFreq) - 0.5) * ColContrast * 2.0);
float3 c = lerp(ColorA.rgb, ColorB.rgb, v);
if (PoreAmt > 0.001) { float pm = 1.0 - smoothstep(0.05, 0.42, F.cell(p * PoreFreq)); c *= 1.0 - PoreDark * pm; }
if (SpeckSize > 0.001) { float s = F.cell(p * SpeckFreq + 13.7); c = lerp(c, SpeckColor.rgb, 1.0 - smoothstep(SpeckSize * 0.7, SpeckSize, s)); }
return c;'''

ROUGH = LIB + '''float3 p = WP / Scale;
return saturate(Rough + RoughVar * (F.fbm(p * ColFreq * 2.7 + 5.1) - 0.5) * 2.0);'''

SCALARS = [('Scale', 240.0), ('ColFreq', 0.8), ('ColContrast', 1.0), ('BumpFreq', 2.0), ('BumpAmt', 0.05),
           ('PoreFreq', 2.0), ('PoreAmt', 0.0), ('PoreDark', 0.3), ('SpeckFreq', 3.0), ('SpeckSize', 0.0),
           ('NormalStr', 1.0), ('Rough', 0.6), ('RoughVar', 0.2), ('Specular', 0.5), ('SSS', 0.3)]
VECTORS = [('ColorA', (0.6, 0.4, 0.2)), ('ColorB', (0.8, 0.6, 0.3)), ('SpeckColor', (0.1, 0.07, 0.04)),
           ('SSSColor', (0.8, 0.4, 0.2))]


def run():
    g = new_material(FOLD, 'M_BB_Food', {'ShadingModel': 'MSM_Subsurface', 'bTangentSpaceNormal': False})
    g.node('WP', 'WorldPosition')
    g.node('N', 'VertexNormalWS')
    for pn, v in SCALARS:
        g.sparam(pn, pn, v)
    for pn, c in VECTORS:
        g.vparam(pn, pn, c)
    specs = {
        'FoodNormal': (NORMAL, ['WP', 'N', 'Scale', 'BumpFreq', 'BumpAmt', 'PoreFreq', 'PoreAmt', 'NormalStr'], 'CMOT_Float3'),
        'FoodColor': (COLOR, ['WP', 'Scale', 'ColorA', 'ColorB', 'ColFreq', 'ColContrast', 'PoreFreq', 'PoreAmt',
                              'PoreDark', 'SpeckColor', 'SpeckFreq', 'SpeckSize'], 'CMOT_Float3'),
        'FoodRough': (ROUGH, ['WP', 'Scale', 'Rough', 'RoughVar', 'ColFreq'], 'CMOT_Float1'),
    }
    for name, (code, ins, ot) in specs.items():
        g.custom(name, code, ins, ot)
        for i in ins:
            g.link(i, name, i)
    g.out('FoodNormal', 'MP_Normal')
    g.out('FoodColor', 'MP_BaseColor')
    g.out('FoodRough', 'MP_Roughness')
    g.out('Specular', 'MP_Specular')
    g.out('SSSColor', 'MP_SubsurfaceColor')
    g.out('SSS', 'MP_Opacity')
    g.compile()
    t(AT + 'save_assets', {'asset_paths': [FOLD + '/M_BB_Food']})
    return {'ok': True}
