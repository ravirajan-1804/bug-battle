"""Writes Saved/ClaudeScripts/plan.json: Garden 2 material instances + slot assignments.
Run the plan with Saved/ClaudeScripts/runner_inline.py through the unreal-mcp ProgrammaticToolset."""
import json, os

MAT = '/Game/BugBattle/Materials/'
FOLD = '/Game/BugBattle/Garden2/Materials'
MESH = '/Game/BugBattle/Garden2/Meshes/'
PLAN = os.path.join(os.path.dirname(__file__), '..', '..', 'Saved', 'ClaudeScripts', 'plan.json')


def food(a, b, **k):
    d = dict(Scale=240.0, ColFreq=0.8, ColContrast=1.0, BumpFreq=2.0, BumpAmt=0.05, PoreFreq=2.0, PoreAmt=0.0,
             PoreDark=0.3, SpeckFreq=3.0, SpeckSize=0.0, NormalStr=1.0, Rough=0.8, RoughVar=0.15, Specular=0.35, SSS=0.0)
    vec = {'ColorA': a, 'ColorB': b, 'SpeckColor': k.pop('speck', (0.05, 0.04, 0.03)), 'SSSColor': k.pop('sss', (0.5, 0.4, 0.3))}
    d.update(k)
    return ('M_BB_Food', vec, d)


def surf(base, tint=None, **k):
    d = dict(NoiseMix=0.1, NoiseScale=0.01, FuzzAmount=0.0, Roughness=0.4, Specular=0.5, Metallic=0.0,
             RoughnessVariation=0.1, NormalTiling=4.0, NormalStrength=0.15)
    d.update(k)
    return ('M_BB_Surface', {'BaseColor': base, 'TintColor': tint or base, 'FuzzColor': (1, 1, 1), 'EmissiveColor': (0, 0, 0)}, d)


def leaf(base, tint, sss, root=0.45, tip=1.15, **k):
    d = dict(NoiseMix=0.5, NoiseScale=0.0006, FuzzAmount=0.12, Roughness=0.5, Specular=0.45, Metallic=0.0,
             RoughnessVariation=0.15, NormalTiling=2.0, NormalStrength=0.2, RootShade=root, TipShade=tip)
    d.update(k)
    return ('M_BB_Foliage', {'BaseColor': base, 'TintColor': tint, 'SSSColor': sss, 'FuzzColor': (0.6, 0.8, 0.3),
                             'EmissiveColor': (0, 0, 0)}, d)


MIS = {
    # ground: light sandy track dirt with grit and tiny pebbles, darker loam off the racing line
    'MI_G2_TrackDirt': food((0.24, 0.15, 0.08), (0.43, 0.30, 0.18), ColFreq=0.5, ColContrast=1.2, BumpFreq=3.0, BumpAmt=0.06,
                            PoreFreq=5.0, PoreAmt=0.03, PoreDark=0.18, SpeckFreq=8.0, SpeckSize=0.1, speck=(0.09, 0.06, 0.035),
                            NormalStr=1.5, Rough=0.92, RoughVar=0.06, Specular=0.3),
    'MI_G2_Soil': food((0.10, 0.06, 0.03), (0.23, 0.15, 0.08), ColFreq=0.6, ColContrast=1.3, BumpFreq=3.0, BumpAmt=0.07,
                       PoreFreq=5.0, PoreAmt=0.03, PoreDark=0.25, SpeckFreq=7.0, SpeckSize=0.1, speck=(0.10, 0.13, 0.04),
                       NormalStr=1.5, Rough=0.95, RoughVar=0.05, Specular=0.3),
    'MI_G2_Bark': food((0.06, 0.045, 0.03), (0.25, 0.19, 0.13), ColFreq=1.2, ColContrast=1.4, BumpFreq=2.5, BumpAmt=0.12,
                       PoreFreq=4.0, PoreAmt=0.05, PoreDark=0.3, SpeckFreq=5.0, SpeckSize=0.08, speck=(0.22, 0.26, 0.12),
                       NormalStr=2.0, Rough=0.9),
    'MI_G2_WoodInner': food((0.30, 0.20, 0.10), (0.56, 0.41, 0.25), ColFreq=2.0, ColContrast=1.1, BumpFreq=4.0, BumpAmt=0.08,
                            PoreFreq=6.0, PoreAmt=0.02, PoreDark=0.25, NormalStr=1.6, Rough=0.85),
    'MI_G2_Moss': food((0.05, 0.12, 0.01), (0.19, 0.33, 0.03), ColFreq=3.0, ColContrast=1.3, BumpFreq=8.0, BumpAmt=0.08,
                       PoreFreq=10.0, PoreAmt=0.04, PoreDark=0.35, SpeckFreq=12.0, SpeckSize=0.12, speck=(0.36, 0.44, 0.05),
                       NormalStr=2.0, Rough=0.95, Specular=0.25, SSS=0.3, sss=(0.2, 0.4, 0.05)),
    'MI_G2_MushCap': food((0.19, 0.085, 0.035), (0.46, 0.27, 0.13), ColFreq=0.9, ColContrast=1.2, BumpFreq=3.0, BumpAmt=0.02,
                          PoreFreq=3.0, PoreAmt=0.01, PoreDark=0.2, Rough=0.55, RoughVar=0.2, Specular=0.45, SSS=0.15,
                          sss=(0.6, 0.35, 0.15)),
    'MI_G2_MushGill': food((0.40, 0.30, 0.20), (0.56, 0.45, 0.33), ColFreq=1.5, BumpFreq=4.0, BumpAmt=0.02, Rough=0.8),
    'MI_G2_MushStem': food((0.56, 0.48, 0.36), (0.76, 0.69, 0.56), ColFreq=1.2, ColContrast=0.8, BumpFreq=3.0, BumpAmt=0.02,
                           Rough=0.7, SSS=0.2, sss=(0.8, 0.7, 0.5)),
    'MI_G2_Stone': food((0.16, 0.15, 0.13), (0.35, 0.32, 0.28), ColFreq=2.0, ColContrast=1.1, BumpFreq=5.0, BumpAmt=0.02,
                        PoreFreq=7.0, PoreAmt=0.006, SpeckFreq=10.0, SpeckSize=0.1, speck=(0.1, 0.09, 0.08), Rough=0.6, RoughVar=0.2,
                        Specular=0.45),
    'MI_G2_StoneDark': food((0.07, 0.07, 0.065), (0.17, 0.16, 0.15), ColFreq=2.0, BumpFreq=5.0, BumpAmt=0.02, Rough=0.55, Specular=0.45),
    'MI_G2_StoneWarm': food((0.25, 0.17, 0.10), (0.43, 0.33, 0.23), ColFreq=2.0, BumpFreq=5.0, BumpAmt=0.02, Rough=0.65),
    'MI_G2_CapLiner': food((0.45, 0.35, 0.22), (0.62, 0.52, 0.36), ColFreq=4.0, BumpFreq=8.0, BumpAmt=0.02, PoreFreq=9.0,
                           PoreAmt=0.01, Rough=0.85),
    'MI_G2_TreeBark': food((0.05, 0.04, 0.03), (0.16, 0.13, 0.10), ColFreq=0.3, BumpFreq=0.6, BumpAmt=0.1, NormalStr=1.5, Rough=0.9),
    # painted / bare metal
    'MI_G2_CanRed': surf((0.55, 0.012, 0.01), (0.35, 0.01, 0.01), Metallic=0.55, Roughness=0.28, Specular=0.6),
    'MI_G2_CanWhite': surf((0.85, 0.85, 0.83), Metallic=0.2, Roughness=0.3),
    'MI_G2_CanMetal': surf((0.75, 0.75, 0.76), Metallic=1.0, Roughness=0.22),
    'MI_G2_CanInside': surf((0.35, 0.35, 0.36), Metallic=1.0, Roughness=0.45),
    'MI_G2_CapRed': surf((0.60, 0.02, 0.015), Metallic=0.35, Roughness=0.3),
    'MI_G2_CapBlue': surf((0.02, 0.10, 0.55), Metallic=0.35, Roughness=0.3),
    'MI_G2_CapGreen': surf((0.03, 0.30, 0.05), Metallic=0.35, Roughness=0.3),
    'MI_G2_CapYellow': surf((0.85, 0.55, 0.02), Metallic=0.35, Roughness=0.3),
    'MI_G2_CapWhite': surf((0.85, 0.85, 0.82), Metallic=0.3, Roughness=0.3),
    'MI_G2_CapMetal': surf((0.70, 0.70, 0.70), Metallic=1.0, Roughness=0.3),
    'MI_G2_Rubber': surf((0.02, 0.02, 0.02), Roughness=0.85, Specular=0.3),
    'MI_G2_Hub': surf((0.60, 0.60, 0.60), Metallic=0.8, Roughness=0.35),
    'MI_G2_Siding': surf((0.42, 0.45, 0.47), Roughness=0.8),
    'MI_G2_Roof': surf((0.06, 0.05, 0.05), Roughness=0.9),
    'MI_G2_Trim': surf((0.80, 0.80, 0.78), Roughness=0.6),
    'MI_G2_Window': surf((0.03, 0.05, 0.08), Roughness=0.08, Specular=1.0),
    'MI_G2_Door': surf((0.20, 0.06, 0.04), Roughness=0.6),
    # foliage
    'MI_G2_GrassA': leaf((0.16, 0.42, 0.03), (0.40, 0.60, 0.06), (0.45, 0.65, 0.08)),
    'MI_G2_GrassB': leaf((0.05, 0.20, 0.02), (0.14, 0.36, 0.03), (0.25, 0.50, 0.05)),
    'MI_G2_GrassDry': leaf((0.30, 0.36, 0.08), (0.50, 0.48, 0.14), (0.60, 0.55, 0.15)),
    'MI_G2_Leaf': leaf((0.08, 0.25, 0.03), (0.20, 0.42, 0.05), (0.30, 0.55, 0.06)),
    'MI_G2_Stem': leaf((0.12, 0.30, 0.04), (0.30, 0.45, 0.08), (0.35, 0.55, 0.10), root=0.8, tip=1.0),
    'MI_G2_Clover': leaf((0.04, 0.20, 0.02), (0.10, 0.32, 0.03), (0.20, 0.50, 0.05), root=0.8, tip=1.05),
    'MI_G2_CloverMark': leaf((0.30, 0.45, 0.20), (0.40, 0.55, 0.28), (0.40, 0.60, 0.25), root=1.0, tip=1.0),
    'MI_G2_CloverStem': leaf((0.20, 0.35, 0.10), (0.30, 0.45, 0.18), (0.35, 0.55, 0.15), root=0.9, tip=1.0),
    'MI_G2_Fluff': leaf((0.92, 0.92, 0.88), (0.95, 0.93, 0.86), (1.0, 0.92, 0.75), root=0.85, tip=1.1, Roughness=0.7,
                        FuzzAmount=0.0, NoiseMix=0.1),
    'MI_G2_FluffCore': leaf((0.72, 0.71, 0.66), (0.78, 0.76, 0.70), (1.0, 0.90, 0.70), root=1.0, tip=1.0, Roughness=0.8,
                            FuzzAmount=0.0, NoiseMix=0.1),
    'MI_G2_Pod': leaf((0.30, 0.24, 0.12), (0.40, 0.32, 0.16), (0.5, 0.4, 0.2), root=1.0, tip=1.0),
    'MI_G2_Canopy': leaf((0.06, 0.18, 0.03), (0.12, 0.30, 0.04), (0.25, 0.45, 0.05), root=1.0, tip=1.0, NoiseScale=0.0002, NoiseMix=0.6),
}

SLOT = {'TrackDirtMat': 'MI_G2_TrackDirt', 'SoilMat': 'MI_G2_Soil', 'CanDirtMat': 'MI_G2_TrackDirt', 'BarkMat': 'MI_G2_Bark',
        'WoodInnerMat': 'MI_G2_WoodInner', 'MossMat': 'MI_G2_Moss', 'MushCapMat': 'MI_G2_MushCap', 'MushGillMat': 'MI_G2_MushGill',
        'MushStemMat': 'MI_G2_MushStem', 'StoneMat': 'MI_G2_Stone', 'StoneDarkMat': 'MI_G2_StoneDark',
        'StoneWarmMat': 'MI_G2_StoneWarm', 'CapLinerMat': 'MI_G2_CapLiner', 'CapMetalMat': 'MI_G2_CapMetal',
        'TreeBarkMat': 'MI_G2_TreeBark', 'CanRedMat': 'MI_G2_CanRed', 'CanWhiteMat': 'MI_G2_CanWhite',
        'CanMetalMat': 'MI_G2_CanMetal', 'CanInsideMat': 'MI_G2_CanInside', 'RubberMat': 'MI_G2_Rubber', 'HubMat': 'MI_G2_Hub',
        'SidingMat': 'MI_G2_Siding', 'RoofMat': 'MI_G2_Roof', 'TrimMat': 'MI_G2_Trim', 'WindowMat': 'MI_G2_Window',
        'DoorMat': 'MI_G2_Door', 'GrassAMat': 'MI_G2_GrassA', 'GrassBMat': 'MI_G2_GrassB', 'GrassDryMat': 'MI_G2_GrassDry',
        'LeafMat': 'MI_G2_Leaf', 'StemMat': 'MI_G2_Stem', 'CloverMat': 'MI_G2_Clover', 'CloverMarkMat': 'MI_G2_CloverMark',
        'CloverStemMat': 'MI_G2_CloverStem', 'FluffMat': 'MI_G2_Fluff', 'FluffCoreMat': 'MI_G2_FluffCore', 'PodMat': 'MI_G2_Pod',
        'CanopyMat': 'MI_G2_Canopy'}

MESH_SLOTS = {
    'SM_G2_Ground': ['SoilMat', 'TrackDirtMat'], 'SM_G2_SodaCan': ['CanDirtMat', 'CanInsideMat', 'CanMetalMat', 'CanRedMat', 'CanWhiteMat'],
    'SM_G2_Mushroom_A': ['MushCapMat', 'MushGillMat', 'MushStemMat'], 'SM_G2_Mushroom_B': ['MushCapMat', 'MushGillMat', 'MushStemMat'],
    'SM_G2_MushCluster': ['MushCapMat', 'MushGillMat', 'MushStemMat'],
    'SM_G2_Dandelion_A': ['FluffMat', 'FluffCoreMat', 'LeafMat', 'PodMat', 'StemMat'],
    'SM_G2_Dandelion_B': ['FluffMat', 'FluffCoreMat', 'LeafMat', 'PodMat', 'StemMat'],
    'SM_G2_Clover': ['CloverMat', 'CloverMarkMat', 'CloverStemMat'], 'SM_G2_BigLog': ['BarkMat', 'MossMat', 'WoodInnerMat'],
    'SM_G2_SplitRamp': ['BarkMat', 'WoodInnerMat'], 'SM_G2_Branch_A': ['BarkMat'], 'SM_G2_Branch_B': ['BarkMat'],
    'SM_G2_Branch_C': ['BarkMat'], 'SM_G2_Boulder_A': ['StoneMat'], 'SM_G2_Boulder_B': ['StoneMat'], 'SM_G2_Boulder_C': ['StoneMat'],
    'SM_G2_House': ['DoorMat', 'RoofMat', 'SidingMat', 'TrimMat', 'WindowMat'], 'SM_G2_BgTree_A': ['CanopyMat', 'TreeBarkMat'],
    'SM_G2_BgTree_B': ['CanopyMat', 'TreeBarkMat'], 'SM_G2_Moss': ['MossMat'], 'SM_G2_Tire': ['HubMat', 'RubberMat'],
    'SM_G2_Pebbles': ['StoneMat', 'StoneDarkMat', 'StoneWarmMat'], 'SM_G2_Tufts': ['GrassAMat', 'GrassBMat', 'GrassDryMat'],
}
for k in range(12):
    MESH_SLOTS['SM_G2_Grass_%02d' % k] = ['GrassAMat', 'GrassBMat', 'GrassDryMat']


def col(c):
    return {'r': c[0], 'g': c[1], 'b': c[2], 'a': 1.0}


def main():
    plan = []
    for name, (parent, vec, sca) in MIS.items():
        plan.append({'t': 'AS.delete', 'a': {'path': FOLD + '/' + name}, 'opt': True})
        plan.append({'t': 'MI.create', 'a': {'folder_path': FOLD, 'asset_name': name,
                                             'parent': {'refPath': MAT + parent + '.' + parent}}, 'n': name})
        for p, v in vec.items():
            plan.append({'t': 'MI.set_vector_parameter', 'a': {'instance': {'refPath': FOLD + '/' + name + '.' + name}, 'name': p, 'value': col(v)}})
        for p, v in sca.items():
            plan.append({'t': 'MI.set_scalar_parameter', 'a': {'instance': {'refPath': FOLD + '/' + name + '.' + name}, 'name': p, 'value': v}})
    for mesh, slots in MESH_SLOTS.items():
        for s in slots:
            mi = SLOT[s]
            plan.append({'t': 'SM.set_material', 'a': {'mesh': {'refPath': MESH + mesh + '.' + mesh}, 'slot_name': s,
                                                       'material': {'refPath': FOLD + '/' + mi + '.' + mi}}})
    for c in ('Red', 'Blue', 'Green', 'Yellow', 'White'):
        mesh = 'SM_G2_Cap_' + c
        for s, mi in (('CapPaintMat', 'MI_G2_Cap' + c), ('CapMetalMat', 'MI_G2_CapMetal'), ('CapLinerMat', 'MI_G2_CapLiner')):
            plan.append({'t': 'SM.set_material', 'a': {'mesh': {'refPath': MESH + mesh + '.' + mesh}, 'slot_name': s,
                                                       'material': {'refPath': FOLD + '/' + mi + '.' + mi}}})
    write_chunks(plan)


def write_chunks(plan, size=260):
    base = os.path.dirname(PLAN)
    n = 0
    for i in range(0, len(plan), size):
        with open(os.path.join(base, 'plan_%d.json' % n), 'w') as f:
            json.dump(plan[i:i + size], f, separators=(',', ':'))
        n += 1
    print(len(plan), 'steps in', n, 'chunks')


if __name__ == '__main__':
    main()
