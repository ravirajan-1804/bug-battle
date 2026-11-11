# Run through unreal-mcp ProgrammaticToolset.execute_tool_script (paste the file contents as `script`).
# Builds the Spider Car power materials from the SpiderCar_Abilities.blend shader values.
# Custom primitive data: [0] Fade (the .blend 'fade' property) / spark age in frames, [1] Grow (bevel_factor_end) / spark
# speed, [2] film fade / spark duration. Always write every index a material reads: an unset index reads 0, not the default.
import json
M = 'editor_toolset.toolsets.material.MaterialTools.'
O = 'editor_toolset.toolsets.object.ObjectTools.'
AT = 'editor_toolset.toolsets.asset.AssetTools.'
MI = 'editor_toolset.toolsets.material_instance.MaterialInstanceTools.'
F = '/Game/SpiderCar/Abilities/Materials'


def t(n, a):
    return execute_tool(n, json.dumps(a))['returnValue']


def sp(obj, vals):
    return t(O + 'set_properties', {'instance': obj, 'values': json.dumps(vals)})


class G:
    def __init__(self, mat):
        self.mat, self.n, self.x, self.y = mat, {}, -1600, 0

    def node(self, name, cls, props=None):
        e = t(M + 'add_expression', {'material_or_function': self.mat,
                                    'expression_class': {'refPath': '/Script/Engine.MaterialExpression' + cls},
                                    'x': self.x, 'y': self.y})
        self.y += 160
        if props:
            sp(e, props)
        self.n[name] = e
        return e

    def custom(self, name, code, inputs, otype='CMOT_Float1'):
        # the node starts with one unnamed input: rename it first, then grow the array (one change per call)
        e = self.node(name, 'Custom', {'Code': code, 'OutputType': otype, 'Inputs': [{'InputName': inputs[0]}]})
        cur = json.loads(t(O + 'get_properties', {'instance': e, 'properties': ['Inputs']}))['Inputs']
        for i in inputs[1:]:
            el = json.loads(json.dumps(cur[0]))
            el['inputName'] = i
            cur = cur + [el]
            sp(e, {'Inputs': cur})
        return e

    def s(self, name, pname, val, cpd=None):
        p = {'ParameterName': pname, 'DefaultValue': val}
        if cpd is not None:
            p.update({'bUseCustomPrimitiveData': True, 'PrimitiveDataIndex': cpd})
        return self.node(name, 'ScalarParameter', p)

    def v(self, name, pname, rgb):
        return self.node(name, 'VectorParameter', {'ParameterName': pname,
                                                   'DefaultValue': {'r': rgb[0], 'g': rgb[1], 'b': rgb[2], 'a': 1}})

    def link(self, src, dst, din, sout=''):
        t(M + 'connect_expressions', {'from_expression': self.n[src], 'from_output_name': sout,
                                      'to_expression': self.n[dst], 'to_input_name': din})

    def out(self, src, prop, sout=''):
        t(M + 'connect_to_output', {'expression': self.n[src], 'output_name': sout, 'material_property': prop})

    def mul(self, name, a, b):
        self.node(name, 'Multiply')
        self.link(a, name, 'A')
        self.link(b, name, 'B')

    def done(self):
        t(M + 'layout_expressions', {'material_or_function': self.mat})
        t(M + 'recompile', {'material_or_function': self.mat})


def new_material(name, props):
    path = F + '/' + name
    if t(AT + 'exists', {'path': path}):
        t(AT + 'delete', {'path': path})
    mat = t(M + 'create_material', {'folder_path': F, 'asset_name': name})
    sp(mat, props)
    return G(mat)


def new_mi(name, parent, scalars=None, vectors=None):
    path = F + '/' + name
    if t(AT + 'exists', {'path': path}):
        t(AT + 'delete', {'path': path})
    mi = t(MI + 'create', {'folder_path': F, 'asset_name': name, 'parent': {'refPath': parent}})
    for k, v in (scalars or {}).items():
        t(MI + 'set_scalar_parameter', {'instance': mi, 'name': k, 'value': v})
    for k, v in (vectors or {}).items():
        t(MI + 'set_vector_parameter', {'instance': mi, 'name': k, 'value': {'r': v[0], 'g': v[1], 'b': v[2], 'a': 1}})
    return mi


def silk():
    """WEB_SILK: principled, alpha = fade (dithered), emission (0.8,0.88,1) x 0.9 x fade; strands grow along UV0.x."""
    g = new_material('M_SpiderCar_Silk', {'BlendMode': 'BLEND_Masked', 'TwoSided': True, 'DitherOpacityMask': True,
                                          'OpacityMaskClipValue': 0.5})
    g.s('fade', 'Fade', 1.0, 0)
    g.s('grow', 'Grow', 1.0, 1)
    g.node('uv', 'TextureCoordinate', {'CoordinateIndex': 0})
    g.custom('mask', 'return (UV.x <= Grow + 0.0005) ? saturate(Fade) : 0.0;', ['UV', 'Grow', 'Fade'])
    g.link('uv', 'mask', 'UV')
    g.link('grow', 'mask', 'Grow')
    g.link('fade', 'mask', 'Fade')
    g.v('base', 'BaseColor', (0.93, 0.94, 0.97))
    g.s('rough', 'Roughness', 0.38)
    g.v('ecol', 'EmissionColor', (0.80, 0.88, 1.0))
    g.s('ek', 'EmissionStrength', 0.9)
    g.mul('e1', 'ecol', 'ek')
    g.mul('e2', 'e1', 'fade')
    g.out('base', 'MP_BaseColor')
    g.out('rough', 'MP_Roughness')
    g.out('e2', 'MP_EmissiveColor')
    g.out('mask', 'MP_OpacityMask')
    g.done()


def film():
    """WEB_SILK_FILM / WEB_COCOON_FILM: translucent silk sheet, alpha = alpha_k x fade x film fade.
    CPD[2] (FilmFade) lets the cocoon film fade on its own keys while the strands share the mesh."""
    g = new_material('M_SpiderCar_SilkFilm', {'BlendMode': 'BLEND_Translucent', 'TwoSided': True,
                                              'TranslucencyLightingMode': 'TLM_SurfacePerPixelLighting'})
    g.s('fade0', 'Fade', 1.0, 0)
    g.s('ff', 'FilmFade', 1.0, 2)
    g.mul('fade', 'fade0', 'ff')
    g.v('base', 'BaseColor', (0.95, 0.96, 1.0))
    g.s('rough', 'Roughness', 0.5)
    g.v('ecol', 'EmissionColor', (0.85, 0.9, 1.0))
    g.s('ek', 'EmissionStrength', 0.25)
    g.s('ak', 'AlphaK', 0.22)
    g.mul('e1', 'ecol', 'ek')
    g.mul('e2', 'e1', 'fade')
    g.mul('op', 'ak', 'fade')
    g.out('base', 'MP_BaseColor')
    g.out('rough', 'MP_Roughness')
    g.out('e2', 'MP_EmissiveColor')
    g.out('op', 'MP_Opacity')
    g.done()


def emission():
    """fx_emission: mix(transparent, emission(color, strength x fade), fade)."""
    g = new_material('M_SpiderCar_Emission', {'BlendMode': 'BLEND_Translucent', 'ShadingModel': 'MSM_Unlit', 'TwoSided': True})
    g.s('fade', 'Fade', 1.0, 0)
    g.v('col', 'Color', (0.85, 0.92, 1.0))
    g.s('str', 'Strength', 6.0)
    g.mul('e1', 'col', 'str')
    g.mul('e2', 'e1', 'fade')
    g.node('op', 'Saturate')
    g.link('fade', 'op', '')
    g.out('e2', 'MP_EmissiveColor')
    g.out('op', 'MP_Opacity')
    g.done()


def sparks():
    """FX_SPARKS emission (1,0.62,0.18) x 8; each spark flies d*speed*frame with gravity, fade 1 -> 0 over dur."""
    g = new_material('M_SpiderCar_Sparks', {'BlendMode': 'BLEND_Translucent', 'ShadingModel': 'MSM_Unlit', 'TwoSided': True})
    g.s('age', 'AgeFrames', 0.0, 0)
    g.s('spd', 'Speed', 0.25, 1)
    g.s('dur', 'Duration', 12.0, 2)
    g.node('uv1', 'TextureCoordinate', {'CoordinateIndex': 1})
    g.node('uv2', 'TextureCoordinate', {'CoordinateIndex': 2})
    # same path as the .blend keys: d * speed * frame, minus 4.9 t^2 gravity (metres -> cm)
    g.custom('off', 'float f = clamp(Age, 0.0, Dur); float s = f / 24.0;\n'
                    'float3 d = float3(A.x, A.y, B.x);\n'
                    'return (d * Speed * f - float3(0, 0, 4.9 * s * s)) * 100.0;', ['A', 'B', 'Age', 'Speed', 'Dur'], 'CMOT_Float3')
    for a, b in (('uv1', 'A'), ('uv2', 'B'), ('age', 'Age'), ('spd', 'Speed'), ('dur', 'Dur')):
        g.link(a, 'off', b)
    g.node('xf', 'Transform', {'TransformSourceType': 'TRANSFORMSOURCE_Local', 'TransformType': 'TRANSFORM_World'})
    g.link('off', 'xf', '')
    g.custom('fd', 'return (Age >= 0.0 && Age <= Dur) ? saturate(1.0 - Age / Dur) : 0.0;', ['Age', 'Dur'])
    g.link('age', 'fd', 'Age')
    g.link('dur', 'fd', 'Dur')
    g.v('col', 'Color', (1.0, 0.62, 0.18))
    g.s('str', 'Strength', 8.0)
    g.mul('e1', 'col', 'str')
    g.mul('e2', 'e1', 'fd')
    g.out('e2', 'MP_EmissiveColor')
    g.out('fd', 'MP_Opacity')
    g.out('xf', 'MP_WorldPositionOffset')
    g.done()


def smoke():
    """FX_SMOKE: dark principled, alpha 0.85 x fade."""
    g = new_material('M_SpiderCar_Smoke', {'BlendMode': 'BLEND_Translucent', 'TwoSided': True,
                                           'TranslucencyLightingMode': 'TLM_SurfacePerPixelLighting'})
    g.s('fade', 'Fade', 1.0, 0)
    g.v('base', 'BaseColor', (0.035, 0.035, 0.04))
    g.s('rough', 'Roughness', 1.0)
    g.s('ak', 'AlphaK', 0.85)
    g.mul('op', 'ak', 'fade')
    g.out('base', 'MP_BaseColor')
    g.out('rough', 'MP_Roughness')
    g.out('op', 'MP_Opacity')
    g.done()


VORONOI = r'''
float3 Bite = float3(BX, BY, BZ);
float3 p = P * Scale;
float3 c = floor(p);
float3 f = p - c;
float3 mr = 0; float3 mg = 0; float md = 8.0;
for (int k = -1; k <= 1; k++) for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
  float3 g = float3(i, j, k);
  float3 h = c + g;
  float3 o = frac(sin(float3(dot(h, float3(127.1, 311.7, 74.7)), dot(h, float3(269.5, 183.3, 246.1)), dot(h, float3(113.5, 271.9, 124.6)))) * 43758.5453);
  float3 r = g + o - f;
  float d = dot(r, r);
  if (d < md) { md = d; mr = r; mg = g; }
}
float e = 8.0;
for (int k2 = -2; k2 <= 2; k2++) for (int j2 = -2; j2 <= 2; j2++) for (int i2 = -2; i2 <= 2; i2++) {
  float3 g = mg + float3(i2, j2, k2);
  float3 h = c + g;
  float3 o = frac(sin(float3(dot(h, float3(127.1, 311.7, 74.7)), dot(h, float3(269.5, 183.3, 246.1)), dot(h, float3(113.5, 271.9, 124.6)))) * 43758.5453);
  float3 r = g + o - f;
  float3 dr = r - mr;
  if (dot(dr, dr) > 0.00001) e = min(e, dot(0.5 * (mr + r), normalize(dr)));
}
float veins = 1.0 - saturate(e / 0.022);
float inside = (distance(P, Bite) < Venom * 5.5) ? 1.0 : 0.0;
return veins * inside;
'''


def veins():
    """ENEMY_PAINT venom: green emissive Voronoi veins spreading from the bite (radius venom x 5.5 m) + green tint (0.65 x venom).
    Used as an overlay material on the bitten car, one dynamic instance per mesh component (BP_SpiderCar_VenomFX sets
    Venom, BiteX/Y/Z and LocalToMetres each tick); P is the component-space position in metres."""
    g = new_material('M_SpiderCar_VenomVeins', {'BlendMode': 'BLEND_Translucent', 'TwoSided': False,
                                                'TranslucencyLightingMode': 'TLM_SurfacePerPixelLighting'})
    g.s('venom', 'Venom', 0.0)
    g.s('bx', 'BiteX', -2.1)
    g.s('by', 'BiteY', 0.0)
    g.s('bz', 'BiteZ', 0.55)
    g.s('ls', 'LocalToMetres', 0.01)
    g.node('wp', 'WorldPosition')
    g.node('lp', 'TransformPosition', {'TransformSourceType': 'TRANSFORMPOSSOURCE_World', 'TransformType': 'TRANSFORMPOSSOURCE_Local'})
    g.link('wp', 'lp', '')
    g.mul('pm', 'lp', 'ls')
    g.s('vs', 'VeinScale', 3.5)
    g.custom('mask', VORONOI, ['P', 'Scale', 'BX', 'BY', 'BZ', 'Venom'])
    g.link('pm', 'mask', 'P')
    g.link('vs', 'mask', 'Scale')
    for a, b in (('bx', 'BX'), ('by', 'BY'), ('bz', 'BZ'), ('venom', 'Venom')):
        g.link(a, 'mask', b)
    g.v('tint', 'TintColor', (0.03, 0.22, 0.015))
    g.v('ecol', 'VeinColor', (0.22, 1.0, 0.04))
    g.s('ek', 'VeinStrength', 3.2)
    g.mul('e1', 'ecol', 'ek')
    g.mul('e2', 'e1', 'mask')
    g.s('tk', 'TintAmount', 0.65)
    g.mul('tv', 'tk', 'venom')
    g.node('op', 'Max')
    g.link('tv', 'op', 'A')
    g.link('mask', 'op', 'B')
    g.s('rough', 'Roughness', 0.28)
    g.s('metal', 'Metallic', 0.6)
    g.out('tint', 'MP_BaseColor')
    g.out('rough', 'MP_Roughness')
    g.out('metal', 'MP_Metallic')
    g.out('e2', 'MP_EmissiveColor')
    g.out('op', 'MP_Opacity')
    g.done()


def run():
    silk()
    film()
    emission()
    sparks()
    smoke()
    veins()
    P = F + '/'
    new_mi('MI_SpiderCar_WebFilm', P + 'M_SpiderCar_SilkFilm.M_SpiderCar_SilkFilm')
    new_mi('MI_SpiderCar_CocoonFilm', P + 'M_SpiderCar_SilkFilm.M_SpiderCar_SilkFilm',
           {'Roughness': 0.45, 'EmissionStrength': 0.35, 'AlphaK': 0.13},
           {'BaseColor': (0.95, 0.95, 0.98), 'EmissionColor': (0.9, 0.92, 1.0)})
    E = P + 'M_SpiderCar_Emission.M_SpiderCar_Emission'
    new_mi('MI_SpiderCar_SilkFlash', E, {'Strength': 6.0}, {'Color': (0.85, 0.92, 1.0)})
    new_mi('MI_SpiderCar_VenomGreen', E, {'Strength': 7.0}, {'Color': (0.35, 1.0, 0.10)})
    new_mi('MI_SpiderCar_DashStreak', E, {'Strength': 7.0}, {'Color': (1.0, 0.07, 0.03)})
    S = '/Game/BugBattle/Materials/M_BB_Surface.M_BB_Surface'
    for nm, base, metal, rough, emis in (('Crimson', (0.46, 0.002, 0.006), 0.35, 0.22, (0, 0, 0)),
                                         ('BlackMetallic', (0.016, 0.016, 0.018), 0.7, 0.24, (0, 0, 0)),
                                         ('Gunmetal', (0.065, 0.068, 0.075), 1.0, 0.5, (0, 0, 0)),
                                         ('VenomGreen', (0.02, 0.02, 0.02), 0.0, 0.3, (1.2, 4.0, 0.32))):
        new_mi('MI_SpiderCar_Fang_' + nm, S, {'Metallic': metal, 'Roughness': rough, 'NoiseMix': 0.0},
               {'BaseColor': base, 'TintColor': tuple(c * 0.85 for c in base), 'EmissiveColor': emis})
    return {'ok': True}
