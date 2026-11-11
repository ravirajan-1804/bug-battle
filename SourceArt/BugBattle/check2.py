import math
import gen_arena as g
from meshlib import v_sub, v_cross, v_dot, v_norm
# rim/content faces should face the arena centre (-radial)
m = g.hive_panel(11)
for mat, ts in m.tris.items():
    good=tot=0
    for a,b,c in ts:
        n = v_cross(v_sub(m.p[b],m.p[a]), v_sub(m.p[c],m.p[a]))
        p = m.p[a]; rad = v_norm((p[0],p[1],0))
        tot+=1; good += v_dot(v_norm(n), rad) < 0
    print('panel', mat, tot, 'facing centre %.2f'%(good/tot))
for name, fn in [('floor',g.arena_floor),('dais',g.hex_dais),('ramp',lambda: g.leaf(1500,760,166))]:
    m=fn(); up=tot=0
    for mat,ts in m.tris.items():
        for a,b,c in ts:
            n=v_cross(v_sub(m.p[b],m.p[a]), v_sub(m.p[c],m.p[a])); tot+=1; up+= n[2]>0
    print(name, tot, 'up %.2f'%(up/tot))
