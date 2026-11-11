# Body for the unreal-mcp ProgrammaticToolset (run via mk.py): creates the RacingGame material instances.
MI = 'editor_toolset.toolsets.material_instance.MaterialInstanceTools.'
AT = 'editor_toolset.toolsets.asset.AssetTools.'
SURF = '/Game/BugBattle/Materials/M_BB_Surface.M_BB_Surface'
FOL = '/Game/BugBattle/Materials/M_BB_Foliage.M_BB_Foliage'
FOLDER = '/Game/RacingGame/Materials'

def col(c):
    return {'r': c[0], 'g': c[1], 'b': c[2], 'a': 1.0}

def mk(name, parent, vec, sca):
    path = FOLDER + '/' + name
    if t(AT + 'exists', {'path': path}):
        inst = {'refPath': path + '.' + name}
    else:
        inst = t(MI + 'create', {'folder_path': FOLDER, 'asset_name': name, 'parent': {'refPath': parent}})
    for k, v in vec.items():
        t(MI + 'set_vector_parameter', {'instance': inst, 'name': k, 'value': col(v)})
    for k, v in sca.items():
        t(MI + 'set_scalar_parameter', {'instance': inst, 'name': k, 'value': v})
    return path

def paint(base, tint=None, rough=0.5, spec=0.5, metal=0.0, noise=0.12, ns=0.01, emis=(0, 0, 0), nstr=0.25, fuzz=0.0):
    return ({'BaseColor': base, 'TintColor': tint or [x * 0.8 for x in base], 'EmissiveColor': emis, 'FuzzColor': [1, 1, 1]},
            {'Roughness': rough, 'Specular': spec, 'Metallic': metal, 'NoiseMix': noise, 'NoiseScale': ns,
             'NormalStrength': nstr, 'NormalTiling': 4.0, 'RoughnessVariation': 0.15, 'FuzzAmount': fuzz})

MATS = {
    'MI_RG_Asphalt': paint([0.085, 0.085, 0.09], [0.035, 0.035, 0.04], rough=0.8, spec=0.4, noise=0.55, ns=0.02, nstr=0.6),
    'MI_RG_ShortcutClay': paint([0.36, 0.17, 0.08], [0.22, 0.1, 0.05], rough=0.85, spec=0.35, noise=0.5, ns=0.012, nstr=0.6),
    'MI_RG_Paint': paint([0.86, 0.86, 0.83], [0.72, 0.72, 0.7], rough=0.55, noise=0.1),
    'MI_RG_PaintBlack': paint([0.018, 0.018, 0.02], rough=0.5, noise=0.05),
    'MI_RG_PaintYellow': paint([0.95, 0.68, 0.04], rough=0.5, noise=0.08),
    'MI_RG_KerbRed': paint([0.72, 0.035, 0.03], rough=0.4, spec=0.55, noise=0.1),
    'MI_RG_KerbWhite': paint([0.88, 0.88, 0.86], rough=0.4, spec=0.55, noise=0.1),
    'MI_RG_ChevronYellow': paint([0.98, 0.62, 0.02], rough=0.45, noise=0.05),
    'MI_RG_Housing': paint([0.03, 0.03, 0.035], rough=0.35, spec=0.6, metal=0.7, noise=0.05),
    'MI_RG_LampRed': paint([0.6, 0.02, 0.02], rough=0.2, emis=(25.0, 0.6, 0.25), noise=0.0),
    'MI_RG_LampWarm': paint([1.0, 0.85, 0.55], rough=0.3, emis=(14.0, 8.0, 2.6), noise=0.0),
    'MI_RG_FungusGlow': paint([0.25, 0.95, 0.85], rough=0.4, emis=(0.4, 4.0, 3.2), noise=0.2, fuzz=0.3),
    'MI_RG_LogInner': paint([0.42, 0.27, 0.14], [0.3, 0.18, 0.09], rough=0.8, spec=0.3, noise=0.45, ns=0.004, nstr=0.8),
    'MI_RG_BannerYellow': paint([0.96, 0.76, 0.06], rough=0.75, noise=0.15, fuzz=0.2),
    'MI_RG_BannerTeal': paint([0.02, 0.55, 0.58], rough=0.75, noise=0.15, fuzz=0.2),
    'MI_RG_BannerMagenta': paint([0.78, 0.04, 0.42], rough=0.75, noise=0.15, fuzz=0.2),
    'MI_RG_BannerOrange': paint([0.96, 0.32, 0.02], rough=0.75, noise=0.15, fuzz=0.2),
    'MI_RG_BannerPurple': paint([0.33, 0.07, 0.68], rough=0.75, noise=0.15, fuzz=0.2),
}

def run():
    made = []
    for name, (vec, sca) in MATS.items():
        made.append(mk(name, SURF, vec, sca))
    made.append(mk('MI_RG_LeafAutumn', FOL, {'BaseColor': [0.42, 0.16, 0.02], 'TintColor': [0.62, 0.36, 0.04],
                                             'SSSColor': [0.7, 0.35, 0.03], 'FuzzColor': [0.6, 0.45, 0.2], 'EmissiveColor': [0, 0, 0]},
                    {'Roughness': 0.55, 'NoiseMix': 0.35, 'NoiseScale': 0.002, 'RootShade': 0.5, 'TipShade': 1.1,
                     'FuzzAmount': 0.1, 'Specular': 0.4, 'Metallic': 0.0}))
    t(AT + 'save_assets', {'asset_paths': made})
    return {'made': made}
