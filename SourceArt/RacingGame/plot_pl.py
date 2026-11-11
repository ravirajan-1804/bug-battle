import json
from trackdef import Track, Shortcut, plot, SC_HALF_W
d = json.load(open('placements.json'))
T = Track(); S = Shortcut(T)
cols = {'Flower':(230,180,0),'PassageFlower':(255,120,0),'Mushroom':(200,0,0),'GiantMushroom':(150,0,0),'Pebble':(120,120,120),'FlagBanner':(0,150,255),'Lantern':(255,200,0),'BgGrass':(0,140,0),'InfieldGrass':(0,180,0),'InfieldFlower':(255,0,200)}
def extra(cv, tr):
    for i in range(len(S.xy)):
        c, f, r, u = S.frame(i)
        for side in (-1, 1):
            cv.dot(*tr(c[:2] + side * SC_HALF_W * r[:2]), (200, 120, 0), 1)
    for p in d['placements']:
        cv.dot(*tr(p['loc']), cols.get(p['label'], (150,0,200)), 2)
    for s in d['grid_slots']:
        cv.dot(*tr(s['loc']), (0,0,0), 2)
plot(T, 'placements.png', extra)
