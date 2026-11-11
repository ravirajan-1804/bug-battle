import sys, importlib
from meshlib import v_sub, v_dot
mod = importlib.import_module(sys.argv[1])
for name in sys.argv[2:]:
    fn = getattr(mod, name)
    m = fn()
    m.compute_normals()
    c = [sum(p[i] for p in m.p)/len(m.p) for i in range(3)]
    good = sum(1 for p,n in zip(m.p,m.n) if v_dot(n, v_sub(p,c))>0)
    up = sum(1 for n in m.n if n[2]>0)
    print(name, len(m.p), 'outward %.2f'%(good/len(m.p)), 'up %.2f'%(up/len(m.p)))
