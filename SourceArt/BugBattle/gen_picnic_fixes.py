"""Picnic Arena fixes (2026-10-17):
- SM_MelonDome_Real: same drivable half-watermelon dome as gen_picnic.melon_dome, but the rind is one
  smooth surface with UVs (u around the melon 0..1, v pole to pole 0..1) so M_BB_Watermelon can draw
  realistic stripes; the red / white cut edge at the plate is kept.
- SM_SodaCan_Collision: invisible, smooth collision shell for the soda-can tunnel. The visual can's
  faceted inside, necked ends and rolled lips made cars jolt; this replaces them with a fine smooth tube
  and gentle ramps over the lips. Place it on the same transform as the SodaCanTunnel actor.
Run: python gen_picnic_fixes.py
"""
import math, os
from meshlib import Mesh

OUT = os.path.join(os.path.dirname(__file__), "obj")
os.makedirs(OUT, exist_ok=True)


# ---------- watermelon ----------

def melon_dome_real(A=3000.0, B=2300.0, H=650.0):
    m = Mesh()
    nt, nphi = 120, 180
    ts = [-math.cos(math.pi * i / nt) for i in range(nt + 1)]      # denser near the poles
    span0, span1 = 0.11, math.pi - 0.11

    def surf(t, phi):
        c = math.cos(phi)
        x = A * t
        y = B * math.sqrt(max(0.0, 1 - t * t)) * c
        rho2 = t * t + (1 - t * t) * c * c
        return (x, y, H * max(0.0, 1 - rho2) ** 1.5 - 3.0)

    def band(p0, p1, steps, mat, uv):
        grid = []
        for t in ts:
            row = []
            for s in range(steps + 1):
                ph = p0 + (p1 - p0) * s / steps
                row.append(m.vert(surf(t, ph), uv(ph, t)))
            grid.append(row)
        for i in range(nt):
            for s in range(steps):
                a, b, c, d = grid[i][s], grid[i][s + 1], grid[i + 1][s + 1], grid[i + 1][s]
                m.quad(mat, a, b, c, d)

    edge_uv = lambda ph, t: (ph * 3, t * 4)
    band(0.0, 0.06, 1, "MelonFlesh", edge_uv)
    band(0.06, span0, 1, "MelonWhite", edge_uv)
    band(span0, span1, nphi, "Rind", lambda ph, t: ((ph - span0) / (span1 - span0), (t + 1) * 0.5))
    band(span1, math.pi - 0.06, 1, "MelonWhite", edge_uv)
    band(math.pi - 0.06, math.pi, 1, "MelonFlesh", edge_uv)
    return m


# ---------- soda can collision ----------

L, R, WALL, NECK = 2900.0, 820.0, 22.0, 230.0
CZ = R - 10.0
R_IN = R - WALL
X_MOUTH = L / 2 - 30.0              # end of the inner tube (just inside the rolled lip)


def inner_radius(ax):
    """Smooth inner radius along |x|: full inside, easing in to the necked mouth."""
    x0 = L / 2 - NECK
    if ax <= x0:
        return R_IN
    k = min(1.0, (ax - x0) / (X_MOUTH - x0))
    return R_IN - (R_IN - 735.0) * (0.5 - 0.5 * math.cos(math.pi * k))


# ramp centre-line profile (|x|, z): plate -> over the lip -> down onto the tube floor
RAMP = [(2300.0, -5.0), (1750.0, 75.0), (1480.0, 108.0), (1250.0, 70.0), (950.0, 14.0)]
RAMP_HALF_IN, RAMP_HALF_OUT = 520.0, 700.0


def ramp_z(ax):
    for (x0, z0), (x1, z1) in zip(RAMP, RAMP[1:]):
        if x1 <= ax <= x0:
            k = (x0 - ax) / (x0 - x1)
            k = k * k * (3 - 2 * k)
            return z0 + (z1 - z0) * k
    return RAMP[-1][1]


def soda_can_collision():
    m = Mesh()
    segs = 256
    nx = 60
    # inner tube (faces point inward)
    rings = []
    for j in range(nx + 1):
        x = -X_MOUTH + 2 * X_MOUTH * j / nx
        r = inner_radius(abs(x))
        rings.append([m.vert((x, r * math.sin(2 * math.pi * i / segs), CZ - r * math.cos(2 * math.pi * i / segs)))
                      for i in range(segs)])
    for j in range(nx):
        for i in range(segs):
            i2 = (i + 1) % segs
            m.quad("Collision", rings[j][i], rings[j + 1][i], rings[j + 1][i2], rings[j][i2])
    # outer shell + end annuli
    oseg = 160
    outer = []
    for x in (-L / 2, L / 2):
        outer.append([m.vert((x, R * math.sin(2 * math.pi * i / oseg), CZ - R * math.cos(2 * math.pi * i / oseg)))
                      for i in range(oseg)])
    for i in range(oseg):
        i2 = (i + 1) % oseg
        m.quad("Collision", outer[0][i], outer[0][i2], outer[1][i2], outer[1][i])
    for side, x in ((0, -L / 2), (1, L / 2)):
        r_in = inner_radius(X_MOUTH)
        inn = [m.vert((x, r_in * math.sin(2 * math.pi * i / oseg), CZ - r_in * math.cos(2 * math.pi * i / oseg)))
               for i in range(oseg)]
        for i in range(oseg):
            i2 = (i + 1) % oseg
            m.quad("Collision", outer[side][i], outer[side][i2], inn[i2], inn[i])
    # solid flanks under the belly (as in the visual can) so cars cannot wedge underneath
    phi = math.radians(70.0)
    yb, zt = R * math.sin(phi), CZ - R * math.cos(phi)
    for sy in (1, -1):
        a = m.vert((-L / 2, sy * yb, -5)); b = m.vert((L / 2, sy * yb, -5))
        c = m.vert((L / 2, sy * yb, zt + 5)); d = m.vert((-L / 2, sy * yb, zt + 5))
        m.quad("Collision", a, b, c, d)
    # ramps at both mouths: smooth wedges from the plate over the lip down to the tube floor. Inside the
    # can the cross-section follows the tube's curvature (lifted to clear the lip) so off-centre wheels
    # meet no step; outside on the plate it flattens out.
    n, ny = 48, 16
    for sx in (1, -1):
        rows = []
        for k in range(n + 1):
            ax = RAMP[0][0] + (RAMP[-1][0] - RAMP[0][0]) * k / n
            half = RAMP_HALF_OUT if ax > L / 2 else RAMP_HALF_IN + (RAMP_HALF_OUT - RAMP_HALF_IN) * max(0.0, (ax - 1250.0) / (L / 2 - 1250.0))
            r = inner_radius(min(ax, X_MOUTH))
            w = 1.0 if ax <= X_MOUTH else max(0.0, 1.0 - (ax - X_MOUTH) / 250.0)
            zc = ramp_z(ax)
            row = []
            for q in range(ny + 1):
                y = -half + 2 * half * q / ny
                lift = (math.sqrt(r * r) - math.sqrt(max(r * r - y * y, 0.0))) * w
                row.append(m.vert((sx * ax, y, zc + lift)))
            row += [m.vert((sx * ax, -half, -10.0)), m.vert((sx * ax, half, -10.0))]
            rows.append(row)
        for k in range(n):
            for q in range(ny):
                quad_up(m, rows[k][q], rows[k][q + 1], rows[k + 1][q + 1], rows[k + 1][q])
            # side skirts down to the plate
            m.quad("Collision", rows[k][ny + 1], rows[k][0], rows[k + 1][0], rows[k + 1][ny + 1])
            m.quad("Collision", rows[k][ny], rows[k][ny + 2], rows[k + 1][ny + 2], rows[k + 1][ny])
    return m


def quad_up(m, a, b, c, d):
    """Add a quad whose front face points up (+Z), whatever the vertex order."""
    pa, pb, pc = m.p[a], m.p[b], m.p[c]
    nz = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
    if nz >= 0:
        m.quad("Collision", a, b, c, d)
    else:
        m.quad("Collision", a, d, c, b)


def main():
    for name, fn in (("SM_MelonDome_Real", melon_dome_real), ("SM_SodaCan_Collision", soda_can_collision)):
        print(name, fn().write_obj(os.path.join(OUT, name + ".obj")))


if __name__ == "__main__":
    main()
