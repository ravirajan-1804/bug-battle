# Body for the unreal-mcp ProgrammaticToolset: realistic-food material instances (M_BB_Food children)
# and their assignment to the picnic food meshes. The old cartoon MI_* stay untouched.
MI = 'editor_toolset.toolsets.material_instance.MaterialInstanceTools.'
SM = 'editor_toolset.toolsets.static_mesh.StaticMeshTools.'
AT = 'editor_toolset.toolsets.asset.AssetTools.'
FOOD = '/Game/BugBattle/Materials/M_BB_Food.M_BB_Food'
FOLDER = '/Game/BugBattle/Materials/Instances/Food'
PIC = '/Game/BugBattle/Meshes/Picnic/'


def t(n, a):
    return execute_tool(n, json.dumps(a))['returnValue']


def col(c):
    return {'r': c[0], 'g': c[1], 'b': c[2], 'a': 1.0}


def fd(a, b, sss=(0.8, 0.4, 0.2), **k):
    # Subsurface washes colours out quickly in this bright lighting, so it is only kept (small) for the
    # translucent foods in SSS_KEEP; base colours are also deepened by 20 %.
    vec = {'ColorA': [c * 0.8 for c in a], 'ColorB': [c * 0.8 for c in b], 'SSSColor': [c * 0.45 for c in sss]}
    k['SSS'] = 0.0
    if 'speck' in k:
        vec['SpeckColor'] = k.pop('speck')
    return vec, k


# name: (ColorA, ColorB, SSS colour, scalar overrides) - frequencies are per real-life cm
MATS = {
    'MI_RF_Bread': fd((0.70, 0.52, 0.28), (0.86, 0.72, 0.48), (0.9, 0.65, 0.35), ColFreq=1.4, ColContrast=1.1,
                      BumpFreq=3.5, BumpAmt=0.04, PoreFreq=5.0, PoreAmt=0.025, PoreDark=0.22, Rough=0.85, RoughVar=0.1,
                      Specular=0.35, SSS=0.35),
    'MI_RF_Toast': fd((0.525, 0.30, 0.10), (0.825, 0.55, 0.225), (0, 0, 0), ColFreq=0.5, ColContrast=1.6,
                      BumpFreq=3.5, BumpAmt=0.04, PoreFreq=5.0, PoreAmt=0.025, PoreDark=0.22, Rough=0.8, RoughVar=0.15,
                      Specular=0.35),
    'MI_RF_Crust': fd((0.30, 0.13, 0.04), (0.55, 0.30, 0.10), (0.6, 0.3, 0.1), ColFreq=0.9, ColContrast=1.3,
                      BumpFreq=1.6, BumpAmt=0.06, PoreFreq=4.0, PoreAmt=0.02, PoreDark=0.3, Rough=0.65, RoughVar=0.2,
                      Specular=0.4, SSS=0.1),
    'MI_RF_Sugar': fd((0.80, 0.79, 0.74), (0.95, 0.94, 0.90), (0.9, 0.9, 0.85), ColFreq=6.0, ColContrast=1.5,
                      BumpFreq=9.0, BumpAmt=0.02, PoreFreq=7.0, PoreAmt=0.015, PoreDark=0.2, Rough=0.3, RoughVar=0.3,
                      Specular=0.8, SSS=0.5),
    'MI_RF_Cheese': fd((0.82, 0.56, 0.14), (0.93, 0.70, 0.26), (0.95, 0.6, 0.15), ColFreq=0.5, ColContrast=0.6,
                       BumpFreq=1.5, BumpAmt=0.012, PoreFreq=3.5, PoreAmt=0.006, PoreDark=0.1, Rough=0.42,
                       RoughVar=0.15, Specular=0.5, SSS=0.65),
    'MI_RF_CheeseHole': fd((0.78, 0.52, 0.12), (0.88, 0.64, 0.2), (0.95, 0.6, 0.15), ColFreq=0.7, ColContrast=0.6,
                           BumpFreq=1.2, BumpAmt=0.01, Rough=0.28, RoughVar=0.1, Specular=0.55, SSS=0.65),
    'MI_RF_CheeseRind': fd((0.62, 0.38, 0.08), (0.78, 0.52, 0.14), (0.8, 0.5, 0.1), ColFreq=1.2, ColContrast=1.0,
                           BumpFreq=2.0, BumpAmt=0.03, Rough=0.6, RoughVar=0.2, Specular=0.4, SSS=0.3),
    'MI_RF_Cookie': fd((0.42, 0.22, 0.08), (0.70, 0.46, 0.20), (0.7, 0.4, 0.15), ColFreq=0.7, ColContrast=1.3,
                       BumpFreq=1.0, BumpAmt=0.12, PoreFreq=2.2, PoreAmt=0.05, PoreDark=0.35, SpeckFreq=5.0,
                       SpeckSize=0.12, speck=(0.85, 0.80, 0.70), Rough=0.8, RoughVar=0.15, Specular=0.35, SSS=0.15),
    'MI_RF_ChocChip': fd((0.06, 0.025, 0.012), (0.12, 0.06, 0.03), (0.2, 0.08, 0.03), ColFreq=1.0, BumpFreq=2.5,
                         BumpAmt=0.03, Rough=0.38, RoughVar=0.2, Specular=0.5, SSS=0.05),
    'MI_RF_Croissant': fd((0.40, 0.16, 0.03), (0.78, 0.46, 0.12), (0.8, 0.4, 0.1), ColFreq=0.45, ColContrast=1.4,
                          BumpFreq=1.4, BumpAmt=0.05, PoreFreq=5.0, PoreAmt=0.01, PoreDark=0.2, Rough=0.32,
                          RoughVar=0.25, Specular=0.55, SSS=0.25),
    'MI_RF_DonutDough': fd((0.48, 0.24, 0.07), (0.72, 0.46, 0.18), (0.8, 0.45, 0.2), ColFreq=0.6, ColContrast=1.2,
                           BumpFreq=2.0, BumpAmt=0.03, PoreFreq=4.0, PoreAmt=0.02, PoreDark=0.3, Rough=0.6,
                           RoughVar=0.2, Specular=0.45, SSS=0.25),
    'MI_RF_Icing': fd((0.80, 0.36, 0.46), (0.90, 0.48, 0.56), (0.95, 0.5, 0.6), ColFreq=0.5, ColContrast=0.4,
                      BumpFreq=0.8, BumpAmt=0.02, Rough=0.16, RoughVar=0.12, Specular=0.6, SSS=0.5),
    'MI_RF_SprinkleA': fd((0.85, 0.75, 0.05), (0.95, 0.85, 0.12), (0.9, 0.8, 0.1), Rough=0.35, BumpAmt=0.0, SSS=0.2),
    'MI_RF_SprinkleB': fd((0.08, 0.35, 0.80), (0.12, 0.45, 0.9), (0.2, 0.5, 0.9), Rough=0.35, BumpAmt=0.0, SSS=0.2),
    'MI_RF_SprinkleC': fd((0.90, 0.92, 0.95), (0.95, 0.96, 0.98), (0.9, 0.9, 0.9), Rough=0.35, BumpAmt=0.0, SSS=0.2),
    'MI_RF_FriedSkin': fd((0.1125, 0.0375, 0.00875), (0.375, 0.15, 0.03125), (0.7, 0.3, 0.08), ColFreq=0.9,
                          ColContrast=1.7, BumpFreq=1.6, BumpAmt=0.14, PoreFreq=5.5, PoreAmt=0.025, PoreDark=0.3,
                          SpeckFreq=4.0, SpeckSize=0.1, speck=(0.05, 0.03, 0.02), NormalStr=2.0, Rough=0.35,
                          RoughVar=0.3, Specular=0.6, SSS=0.15),
    'MI_RF_Bone': fd((0.78, 0.72, 0.60), (0.90, 0.86, 0.76), (0.9, 0.8, 0.7), ColFreq=1.0, ColContrast=0.8,
                     BumpFreq=2.0, BumpAmt=0.02, Rough=0.55, RoughVar=0.15, SSS=0.3),
    'MI_RF_EggWhite': fd((0.88, 0.88, 0.84), (0.95, 0.95, 0.92), (0.95, 0.92, 0.85), ColFreq=0.5, ColContrast=0.3,
                         BumpFreq=1.0, BumpAmt=0.01, Rough=0.3, RoughVar=0.15, Specular=0.5, SSS=0.85),
    'MI_RF_EggYolk': fd((0.88, 0.50, 0.04), (0.98, 0.66, 0.10), (1.0, 0.6, 0.1), ColFreq=1.2, ColContrast=0.8,
                        BumpFreq=4.0, BumpAmt=0.02, PoreFreq=6.0, PoreAmt=0.01, PoreDark=0.15, Rough=0.7, RoughVar=0.15,
                        Specular=0.35, SSS=0.5),
    'MI_RF_Grape': fd((0.07, 0.015, 0.05), (0.16, 0.05, 0.12), (0.45, 0.04, 0.18), ColFreq=0.8, ColContrast=1.0,
                      BumpFreq=1.5, BumpAmt=0.008, Rough=0.55, RoughVar=0.3, Specular=0.4, SSS=0.6),
    'MI_RF_Stem': fd((0.16, 0.20, 0.06), (0.30, 0.32, 0.12), (0.3, 0.4, 0.1), ColFreq=2.0, BumpFreq=3.0,
                     BumpAmt=0.03, Rough=0.75, SSS=0.2),
    'MI_RF_MelonRindDark': fd((0.025, 0.09, 0.02), (0.05, 0.16, 0.035), (0.1, 0.3, 0.05), ColFreq=0.8,
                              ColContrast=1.1, BumpFreq=1.5, BumpAmt=0.015, SpeckFreq=1.8, SpeckSize=0.08,
                              speck=(0.15, 0.25, 0.08), Rough=0.3, RoughVar=0.2, Specular=0.5, SSS=0.15),
    'MI_RF_MelonRindLight': fd((0.16, 0.32, 0.08), (0.26, 0.44, 0.14), (0.3, 0.5, 0.15), ColFreq=0.8,
                               ColContrast=1.1, BumpFreq=1.5, BumpAmt=0.015, Rough=0.32, RoughVar=0.2,
                               Specular=0.5, SSS=0.15),
    'MI_RF_MelonFlesh': fd((0.72, 0.05, 0.06), (0.92, 0.18, 0.16), (1.0, 0.2, 0.15), ColFreq=0.7, ColContrast=1.0,
                           BumpFreq=2.5, BumpAmt=0.03, PoreFreq=3.0, PoreAmt=0.015, PoreDark=-0.25, Rough=0.22,
                           RoughVar=0.25, Specular=0.55, SSS=0.8),
    'MI_RF_MelonWhite': fd((0.70, 0.78, 0.50), (0.85, 0.88, 0.66), (0.8, 0.9, 0.6), ColFreq=1.0, BumpAmt=0.01,
                           Rough=0.35, SSS=0.6),
    'MI_RF_MelonSeed': fd((0.02, 0.014, 0.01), (0.05, 0.035, 0.02), (0.1, 0.05, 0.02), Rough=0.15, BumpAmt=0.0,
                          Specular=0.6, SSS=0.05),
    'MI_RF_Ham': fd((0.72, 0.30, 0.28), (0.88, 0.48, 0.44), (0.95, 0.4, 0.35), ColFreq=0.9, ColContrast=1.0,
                    BumpFreq=2.0, BumpAmt=0.015, PoreFreq=2.0, PoreAmt=0.01, PoreDark=-0.3, Rough=0.38,
                    RoughVar=0.2, Specular=0.5, SSS=0.6),
    'MI_RF_Lettuce': fd((0.25, 0.48, 0.06), (0.55, 0.75, 0.22), (0.5, 0.8, 0.2), ColFreq=0.6, ColContrast=1.4,
                        BumpFreq=1.2, BumpAmt=0.05, Rough=0.4, RoughVar=0.2, Specular=0.5, SSS=0.7),
    'MI_RF_TomatoSkin': fd((0.55, 0.025, 0.012), (0.75, 0.07, 0.025), (0.9, 0.1, 0.05), ColFreq=0.6,
                           ColContrast=0.9, BumpFreq=1.5, BumpAmt=0.006, Rough=0.12, RoughVar=0.1, Specular=0.6,
                           SSS=0.6),
    'MI_RF_TomatoFlesh': fd((0.78, 0.10, 0.05), (0.92, 0.28, 0.12), (1.0, 0.25, 0.1), ColFreq=1.0, BumpFreq=2.0,
                            BumpAmt=0.02, Rough=0.18, RoughVar=0.2, Specular=0.6, SSS=0.8),
    'MI_RF_Strawberry': fd((0.45, 0.012, 0.02), (0.72, 0.05, 0.05), (0.9, 0.05, 0.05), ColFreq=0.7, ColContrast=1.0,
                           BumpFreq=1.2, BumpAmt=0.012, Rough=0.22, RoughVar=0.2, Specular=0.6, SSS=0.65),
    'MI_RF_StrawberrySeed': fd((0.62, 0.48, 0.12), (0.78, 0.62, 0.2), (0.7, 0.5, 0.1), Rough=0.35, BumpAmt=0.0,
                               SSS=0.2),
    'MI_RF_Calyx': fd((0.06, 0.20, 0.03), (0.14, 0.34, 0.06), (0.2, 0.5, 0.1), ColFreq=1.5, BumpFreq=3.0,
                      BumpAmt=0.03, Rough=0.55, SSS=0.4),
    'MI_RF_Carrot': fd((0.78, 0.22, 0.02), (0.95, 0.40, 0.05), (1.0, 0.4, 0.05), ColFreq=0.9, ColContrast=1.0,
                       BumpFreq=1.0, BumpAmt=0.03, PoreFreq=1.6, PoreAmt=0.02, PoreDark=0.25, Rough=0.45,
                       RoughVar=0.2, Specular=0.5, SSS=0.55),
    'MI_RF_Breadstick': fd((0.50, 0.28, 0.09), (0.78, 0.54, 0.24), (0.8, 0.5, 0.2), ColFreq=0.8, ColContrast=1.3,
                           BumpFreq=1.6, BumpAmt=0.05, PoreFreq=3.5, PoreAmt=0.02, PoreDark=0.3, Rough=0.6,
                           RoughVar=0.2, Specular=0.45, SSS=0.2),
    'MI_RF_Sesame': fd((0.82, 0.72, 0.48), (0.92, 0.84, 0.62), (0.9, 0.8, 0.6), ColFreq=2.0, BumpAmt=0.0,
                       Rough=0.4, SSS=0.3),
}

SSS_KEEP = {'MI_RF_Grape': 0.1, 'MI_RF_Strawberry': 0.1, 'MI_RF_TomatoSkin': 0.08, 'MI_RF_TomatoFlesh': 0.12,
            'MI_RF_MelonFlesh': 0.12, 'MI_RF_EggWhite': 0.12, 'MI_RF_Cheese': 0.08, 'MI_RF_CheeseHole': 0.08,
            'MI_RF_Ham': 0.08, 'MI_RF_Lettuce': 0.1}
for _n, _k in SSS_KEEP.items():
    MATS[_n][1]['SSS'] = _k

# mesh: {slot: MI}
ASSIGN = {
    'SM_BreadstickBridge': {'BreadstickMat': 'MI_RF_Breadstick', 'SesameMat': 'MI_RF_Sesame'},
    'SM_CarrotSticks': {'CarrotMat': 'MI_RF_Carrot'},
    'SM_CheeseWedge': {'CheeseMat': 'MI_RF_Cheese', 'CheeseHoleMat': 'MI_RF_CheeseHole', 'CheeseRindMat': 'MI_RF_CheeseRind'},
    'SM_Cookie_A': {'ChocMat': 'MI_RF_ChocChip', 'CookieMat': 'MI_RF_Cookie'},
    'SM_Cookie_B': {'ChocMat': 'MI_RF_ChocChip', 'CookieMat': 'MI_RF_Cookie'},
    'SM_Croissant': {'CroissantMat': 'MI_RF_Croissant'},
    'SM_Donut': {'DoughMat': 'MI_RF_DonutDough', 'IcingMat': 'MI_RF_Icing', 'SprinkleAMat': 'MI_RF_SprinkleA',
                 'SprinkleBMat': 'MI_RF_SprinkleB', 'SprinkleCMat': 'MI_RF_SprinkleC'},
    'SM_Drumstick': {'BoneMat': 'MI_RF_Bone', 'FriedSkinMat': 'MI_RF_FriedSkin'},
    'SM_EggHalf': {'EggWhiteMat': 'MI_RF_EggWhite', 'EggYolkMat': 'MI_RF_EggYolk'},
    'SM_GrapeBunch': {'GrapeMat': 'MI_RF_Grape', 'StemMat': 'MI_RF_Stem'},
    'SM_MelonDome': {'MelonFleshMat': 'MI_RF_MelonFlesh', 'MelonWhiteMat': 'MI_RF_MelonWhite',
                     'RindDarkMat': 'MI_RF_MelonRindDark', 'RindLightMat': 'MI_RF_MelonRindLight'},
    'SM_MelonSlice': {'MelonFleshMat': 'MI_RF_MelonFlesh', 'MelonSeedMat': 'MI_RF_MelonSeed',
                      'MelonWhiteMat': 'MI_RF_MelonWhite', 'RindDarkMat': 'MI_RF_MelonRindDark'},
    'SM_Sandwich': {'BreadMat': 'MI_RF_Bread', 'CheeseMat': 'MI_RF_Cheese', 'CrustMat': 'MI_RF_Crust',
                    'HamMat': 'MI_RF_Ham', 'LettuceMat': 'MI_RF_Lettuce', 'TomatoFleshMat': 'MI_RF_TomatoFlesh',
                    'TomatoRedMat': 'MI_RF_TomatoSkin'},
    'SM_Strawberry': {'CalyxMat': 'MI_RF_Calyx', 'SeedMat': 'MI_RF_StrawberrySeed', 'StrawberryMat': 'MI_RF_Strawberry'},
    'SM_ToastRamp': {'BreadMat': 'MI_RF_Toast', 'CrustMat': 'MI_RF_Crust', 'SugarMat': 'MI_RF_Sugar'},
}


def mk(name, vec, sca):
    path = FOLDER + '/' + name
    if t(AT + 'exists', {'path': path}):
        inst = {'refPath': path + '.' + name}
    else:
        inst = t(MI + 'create', {'folder_path': FOLDER, 'asset_name': name, 'parent': {'refPath': FOOD}})
    for k, v in vec.items():
        t(MI + 'set_vector_parameter', {'instance': inst, 'name': k, 'value': col(v)})
    for k, v in sca.items():
        t(MI + 'set_scalar_parameter', {'instance': inst, 'name': k, 'value': v})
    return path


def run():
    t(AT + 'create_folder', {'path': FOLDER})
    made = [mk(n, v, s) for n, (v, s) in MATS.items()]
    meshes = []
    for mesh, slots in ASSIGN.items():
        m = {'refPath': PIC + mesh + '.' + mesh}
        for slot, mi in slots.items():
            t(SM + 'set_material', {'mesh': m, 'slot_name': slot, 'material': {'refPath': FOLDER + '/' + mi + '.' + mi}})
        meshes.append(PIC + mesh)
    # the cherry tomato lives in the Garden set (also used by Lvl_GardenArena)
    tom = '/Game/BugBattle/Meshes/Garden/SM_CherryTomato'
    for slot, mi in (('TomatoRedMat', 'MI_RF_TomatoSkin'), ('StemMat', 'MI_RF_Calyx')):
        t(SM + 'set_material', {'mesh': {'refPath': tom + '.SM_CherryTomato'}, 'slot_name': slot,
                                'material': {'refPath': FOLDER + '/' + mi + '.' + mi}})
    meshes.append(tom)
    t(AT + 'save_assets', {'asset_paths': made + meshes})
    return {'instances': len(made), 'meshes': len(meshes)}
