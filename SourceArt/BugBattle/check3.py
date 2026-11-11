import gen_garden as g
from meshlib import v_sub, v_cross, v_dot, v_norm
def stat(name, m, fn):
    good=tot=0
    for mat,ts in m.tris.items():
        for a,b,c in ts:
            n=v_cross(v_sub(m.p[b],m.p[a]), v_sub(m.p[c],m.p[a]))
            p=m.p[a]; tot+=1; good+= fn(mat,p,n)
    print(name, '%.2f'%(good/tot))
import math
# log panel: bark faces away from the log axis; woodend faces up
def logf(mat,p,n):
    if mat=='WoodEnd': return n[2]>0
    return True
stat('logs-top-up', g.log_panel(3), logf)
stat('stump-up', g.tree_stump(), lambda mat,p,n: n[2]>0 if mat=='WoodEnd' else True)
stat('stump-side-out', g.tree_stump(), lambda mat,p,n: (n[0]*p[0]+n[1]*p[1])>0 if mat=='Bark' and p[2]>0 else True)
stat('stone-up', g.stepping_stone(4), lambda mat,p,n: n[2]>0)
stat('pot-side-out', g.flower_pot(), lambda mat,p,n: (n[0]*p[0]+n[1]*p[1])>=-1e-6 if mat=='Terracotta' else n[2]>0)
