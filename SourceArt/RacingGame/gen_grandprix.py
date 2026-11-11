"""Generates the Garden Grand Prix circuit meshes + a placement list.

v5 (2026-10-17): the layout follows the Losail circuit (see trackdef.py). The shortcut, two-way
split and tunnels of v3/v4 are gone; their generator code is in Saved/RG_backup_v4.

Outputs (SourceArt/RacingGame/obj):
  SM_RG_Road_00..NN      main loop chunks: asphalt, kerbs, edge lines, barriers (complex collision)
  SM_RG_GridMarkings     start line, checkered finish band, 7 grid boxes, lane dashes
  SM_RG_Ground_rc        terrain tiles that hug the track and roll into mounds
  SM_RG_Verge_k          giant grass blades lining the circuit (chunked)
  SM_RG_* structures     finish arch + start-light gantry, bunting, flag banners, lanterns,
                         root arch, chevron boards, fallen leaves, seed pods, glow fungus
and placements.json (actor transforms for the level build script).
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "BugBattle"))
from meshlib import Mesh, ellipsoid, tube_along, catmull, lathe_x, Rng, v_add, v_norm, v_sub, v_mul, v_cross  # noqa: E402
from trackdef import Track, HALF_W, L, LAYOUT_SCALE, ENV_SCALE  # noqa: E402

OUT = os.path.join(HERE, "obj")
os.makedirs(OUT, exist_ok=True)

T = Track()
BRANCHES = ()            # v5 has no shortcut / alternate route
N = len(T.xy)
I_START = T.index_at(*L(40, 67))
# start/finish straight (south side, driven east): sample range used for dashes, flags and lanterns
STRAIGHT = range(T.index_at(*L(24.5, 67)), T.index_at(*L(81, 67)))


def near_start(i, k):
    return abs(((i - I_START + N // 2) % N) - N // 2) < k


def tunnel_dims(half_w):
    """Inner radius, outer radius, axis height: the 236 deg arc meets the ground just outside the barrier."""
    r_in = (half_w + 140.0) / math.sin(math.radians(118))
    return r_in, r_in + 200.0, -r_in * math.cos(math.radians(118))


# Tunnels (2026-10-17, user request "two tunnels at two corners"): hollow-log tunnels over the
# big north-east corner and the long sweeping west corner, the two wide corners with the most
# room around them. (mesh name, path, first sample, last sample)
TUNNELS = [("SM_RG_Tunnel_A", T, int(0.325 * N), int(0.386 * N)),
           ("SM_RG_Tunnel_B", T, int(0.745 * N), int(0.822 * N))]
TUN_R_OUT = tunnel_dims(HALF_W)[1]


def in_tunnel(path, i, pad=4):
    return any(p is path and a - pad <= i <= b + pad for (_, p, a, b) in TUNNELS)


def clear_of_tunnels(p, margin):
    """Props must stay outside the tunnel shells (outer radius from the road centre)."""
    for (_, path, a, b) in TUNNELS:
        if np.linalg.norm(path.xy[a - 6:b + 7] - np.asarray(p)[None, :2], axis=1).min() < TUN_R_OUT + margin:
            return False
    return True


BAR_IN, BAR_OUT = 0.0, 50.0           # barrier sits outside the road edge
BARRIER = [(0, 0), (0, 72), (-6, 90), (-44, 90), (-50, 72), (-50, -70)]   # (outward, up) from road edge
BAR_MATS = ["Barrier", "Barrier", "Rail", "Rail", "Barrier"]


def P(c, r, u, l, h):
    return tuple(c + r * l + u * h)


def dist_to(path_xy, pts):
    """min distance of each pt (k,2) to polyline samples (m,2)."""
    pts = np.atleast_2d(pts)
    d = np.sqrt(((pts[:, None, :] - path_xy[None, :, :]) ** 2).sum(-1))
    return d.min(1)


# ---------------------------------------------------------------- road builder
def build_road(path, idx, half_w, kerb_w, kerb_mats, kerb_len, skip_barrier, surf_dz=0.0, closed=True,
               lane_paint=True, surf="Asphalt"):
    """Ribbon road over sample indices idx (consecutive). Returns Mesh."""
    m = Mesh()
    frames = [path.frame(i) for i in idx]
    s_vals = [i * path.step for i in idx]
    rows = []
    # lateral profile of the driving surface (l, h, material of the span to the next point)
    prof = [(-half_w, 2.0, "K"), (-half_w + kerb_w * 0.4, 5.0, "K"), (-half_w + kerb_w, 0.0, "L" if lane_paint else "A"),
            (-half_w + kerb_w + 20, 0.0, "A"), (0.0, 0.0, "A"), (half_w - kerb_w - 20, 0.0, "L" if lane_paint else "A"),
            (half_w - kerb_w, 0.0, "K"), (half_w - kerb_w * 0.4, 5.0, "K"), (half_w, 2.0, None)]
    for k, (c, f, r, u) in enumerate(frames):
        row = []
        for (l, h, _) in prof:
            row.append(m.vert(P(c, r, u, l, h + surf_dz), (l / 200.0, s_vals[k] / 200.0)))
        rows.append(row)
    for k in range(len(frames) - 1):
        band = int(s_vals[k] // kerb_len) % 2
        for j, (_, _, mk) in enumerate(prof[:-1]):
            mat = {"K": kerb_mats[band], "L": "Paint", "A": surf}[mk]
            a, b, cc, d = rows[k][j], rows[k][j + 1], rows[k + 1][j + 1], rows[k + 1][j]
            m.quad(mat, a, d, cc, b)       # winding fixed by normals in writer
    # explicit up normals for the surface (flat shading across the ribbon)
    for k, (c, f, r, u) in enumerate(frames):
        for vi in rows[k]:
            m.n[vi] = tuple(u)
    # barriers
    for side in (-1, 1):
        live = [not skip_barrier(frames[k][0], frames[k][2], side) for k in range(len(frames))]
        brow = []
        for k, (c, f, r, u) in enumerate(frames):
            ring = []
            for (o, h) in BARRIER:
                l = side * (half_w + o * -1)   # o<=0 moves outward
                ring.append(P(c, r, u, l, h + surf_dz))
            brow.append(ring)
        # each profile edge gets its own verts for hard edges
        for k in range(len(frames) - 1):
            if not (live[k] and live[k + 1]):
                continue
            band = int(s_vals[k] // 600.0) % 2
            for e in range(len(BARRIER) - 1):
                mat = BAR_MATS[e]
                if mat == "Barrier":
                    mat = "BarrierRed" if band else "BarrierWhite"
                p0, p1 = brow[k][e], brow[k][e + 1]
                q0, q1 = brow[k + 1][e], brow[k + 1][e + 1]
                # profile is clockwise in (outward, up); outward normal = edge rotated +90deg
                eo = -(BARRIER[e + 1][0] - BARRIER[e][0])
                eu = BARRIER[e + 1][1] - BARRIER[e][1]
                no, nu = -eu, eo
                nrm = frames[k][2] * side * no + frames[k][3] * nu
                nrm = tuple(nrm / (np.linalg.norm(nrm) + 1e-9))
                v = s_vals[k] / 200.0
                ids = [m.vert(p0, (e * 0.3, v), nrm), m.vert(p1, (e * 0.3 + 0.3, v), nrm),
                       m.vert(q1, (e * 0.3 + 0.3, v + path.step / 200.0), nrm), m.vert(q0, (e * 0.3, v + path.step / 200.0), nrm)]
                m.quad(mat, *ids)
        # end caps where a barrier run starts/stops
        for k in range(len(frames)):
            prev_live = live[k - 1] if k > 0 else (live[-1] if closed else False)
            nxt_live = live[k + 1] if k + 1 < len(frames) else (live[0] if closed else False)
            if live[k] and (not prev_live or not nxt_live):
                nrm = tuple(frames[k][1] * (-1 if not prev_live else 1))
                ring = brow[k]
                ids = [m.vert(p, (0, 0), nrm) for p in ring]
                for t in range(1, len(ids) - 1):
                    m.tri("BarrierRed", ids[0], ids[t], ids[t + 1])
    return m


def main_skip(c, r, side):
    """No main barrier where a branch road leaves/joins (the opening)."""
    p = c[:2] + r[:2] * side * (HALF_W + 25)
    return any(dist_to(Q.xy, p)[0] < Q.half_w + 60 for Q in BRANCHES)


def branch_skip(Q):
    def skip(c, r, side):
        p = c[:2] + r[:2] * side * (Q.half_w + 25)
        return dist_to(T.xy, p)[0] < HALF_W + 60
    return skip



def main_plane_z(x, y):
    """Height of the (banked) main road plane at xy, plus lateral distance from the main centreline."""
    j, _ = T.nearest((x, y))
    c, f, r, u = T.frame(j)
    rxy = r[:2]
    lat = float(np.dot(np.array([x, y]) - c[:2], rxy) / np.dot(rxy, rxy))
    lat_c = max(-HALF_W, min(HALF_W, lat))
    return c[2] + r[2] * lat_c, abs(lat)


def blend_to_main(m, surf_ref, below=10.0, ramp=700.0):
    """Per-vertex: snap shortcut vertices on/near the main road onto the main plane (just below it),
    easing back to their own height within `ramp` cm outside the main road edge."""
    for i, p in enumerate(m.p):
        zm, al = main_plane_z(p[0], p[1])
        t = (al - HALF_W - 30.0) / ramp
        if t >= 1.0:
            continue
        t = max(0.0, t)
        w = t * t * (3 - 2 * t)
        # keep each vertex's offset relative to the surface (kerb lip / barrier height)
        m.p[i] = (p[0], p[1], p[2] * w + (zm - below + (p[2] - surf_ref[i])) * (1 - w))


def gen_roads():
    out = {}
    nchunk = 10
    bounds = np.linspace(0, N, nchunk + 1).astype(int)
    for k in range(nchunk):
        idx = list(range(bounds[k], bounds[k + 1] + 1))     # overlap one sample so chunks join
        idx = [i % N for i in idx]
        m = build_road(T, idx, HALF_W, 120.0, ("KerbRed", "KerbWhite"), 300.0, main_skip)
        # fix: frames use index modulo but s for UV should keep increasing
        out["SM_RG_Road_%02d" % k] = m
    return out


def build_branch(Q, kerb_w, kerb_mats, kerb_len, surf, lane_paint):
    m = build_road(Q, list(range(len(Q.xy))), Q.half_w, kerb_w, kerb_mats, kerb_len, branch_skip(Q),
                   surf_dz=0.0, closed=False, surf=surf, lane_paint=lane_paint)
    # reference surface height under each vertex (centre-plane of its cross-section)
    surf_ref = {}
    for i, p in enumerate(m.p):
        k, _ = nearest_on(Q, p)
        c, f, r, u = Q.frame(k)
        lat = float(np.dot(np.array(p) - c, r))
        surf_ref[i] = c[2] + r[2] * lat
    blend_to_main(m, surf_ref)
    return m


def nearest_on(Q, p):
    d = np.linalg.norm(Q.xy - np.asarray(p)[None, :2], axis=1)
    k = int(np.argmin(d))
    return k, d[k]


# ---------------------------------------------------------------- start/finish markings
def box(m, mat, c, f, r, u, l0, l1, s0, s1, h=1.5, t=0.0):
    """flat quad on the road plane between lateral l0..l1 and along s0..s1 (cm, relative to c)."""
    pts = [c + r * l0 + f * s0 + u * h, c + r * l1 + f * s0 + u * h, c + r * l1 + f * s1 + u * h, c + r * l0 + f * s1 + u * h]
    ids = [m.vert(tuple(p), ((p @ r) / 100.0, (p @ f) / 100.0), tuple(u)) for p in pts]
    m.quad(mat, ids[0], ids[3], ids[2], ids[1])


GRID_SLOTS = []


def gen_markings():
    m = Mesh()
    c, f, r, u = T.frame(I_START)
    # true position of the start line along X (the straight is flat & axis aligned)
    sq = 100.0
    inner = HALF_W - 120
    ncol = int(2 * inner // sq)
    for row in range(2):
        for col in range(ncol):
            mat = "PaintBlack" if (row + col) % 2 else "Paint"
            l0 = -inner + col * (2 * inner / ncol)
            box(m, mat, c, f, r, u, l0, l0 + 2 * inner / ncol, -row * sq, -row * sq + sq * 0.999 - (0 if row else 0) + 0.0)
    box(m, "Paint", c, f, r, u, -inner, inner, 100.0, 125.0)              # solid borders of the band
    box(m, "Paint", c, f, r, u, -inner, inner, -125.0, -100.0)
    # 7 staggered grid boxes behind the line: pole on the left (inside of Turn 1 is left)
    for k in range(7):
        side = -1 if k % 2 == 0 else 1
        back = 450.0 + k * 520.0
        lat = side * 560.0
        i = I_START - int(round(back / T.step))
        cc, ff, rr, uu = T.frame(i)
        GRID_SLOTS.append((cc + rr * lat - ff * 0.0 + uu * 60.0, math.degrees(T.heading[i])))
        # bracket: front bar + two side legs (car 470 x 230)
        box(m, "Paint", cc, ff, rr, uu, lat - 170, lat + 170, 260, 285)
        box(m, "Paint", cc, ff, rr, uu, lat - 170, lat - 150, 140, 285)
        box(m, "Paint", cc, ff, rr, uu, lat + 150, lat + 170, 140, 285)
        # slot number as tally bars in front of the box
        for t in range(k + 1):
            o = lat - 150 + t * 22
            box(m, "PaintYellow", cc, ff, rr, uu, o, o + 12, 300, 340)
    # centre lane dashes on the start/finish straight: 3 m dash / 4 m gap at exact arc-length
    # spacing (the old per-sample test drifted, merging or skipping dashes), kept out of the
    # starting grid and clear of the checkered band
    DASH, PERIOD = 300.0, 700.0
    s_start = I_START * T.step
    grid_back = 450.0 + 6 * 520.0 + 600.0          # behind the last grid box
    s_a, s_b = STRAIGHT.start * T.step, (STRAIGHT.stop - 1) * T.step - DASH
    k0 = math.ceil((s_a - (s_start + 400.0)) / PERIOD)
    for k in range(k0, int((s_b - s_start) // PERIOD) + 1):
        s0 = s_start + 400.0 + k * PERIOD          # dashes are phased from just past the line
        if s_start - grid_back - DASH < s0 < s_start + 300.0:
            continue
        i = int(round(s0 / T.step))
        cc, ff, rr, uu = T.frame(i)
        d = s0 - i * T.step
        box(m, "Paint", cc, ff, rr, uu, -12, 12, d, d + DASH, h=1.0)
    return m


# ---------------------------------------------------------------- terrain
def edge_heights():
    """z of left/right road edges per sample (for ground fitting)."""
    zl, zr = np.zeros(N), np.zeros(N)
    for i in range(N):
        c, f, r, u = T.frame(i)
        zl[i] = (c - r * (HALF_W + 50))[2]
        zr[i] = (c + r * (HALF_W + 50))[2]
    return zl, zr


def ground_height(X, Y, zl, zr):
    pts = np.stack([X.ravel(), Y.ravel()], 1)
    H = np.zeros(len(pts))
    best = np.full(len(pts), 1e12)
    side = np.zeros(len(pts))
    bi = np.zeros(len(pts), dtype=int)
    for i0 in range(0, N, 50):
        seg = T.xy[i0:i0 + 50]
        d = np.sqrt(((pts[:, None, :] - seg[None, :, :]) ** 2).sum(-1))
        j = d.argmin(1)
        dm = d[np.arange(len(pts)), j]
        upd = dm < best
        best[upd] = dm[upd]
        bi[upd] = i0 + j[upd]
    hd = T.heading[bi]
    rx, ry = -np.sin(hd), np.cos(hd)
    side = np.sign((pts[:, 0] - T.xy[bi, 0]) * rx + (pts[:, 1] - T.xy[bi, 1]) * ry)
    ze = np.where(side > 0, zr[bi], zl[bi])
    zin = np.minimum(zl[bi], zr[bi])
    # rolling mounds away from the track (garden beds)
    X0, Y0 = pts[:, 0], pts[:, 1]
    mound = (np.sin(X0 / 2300.0 + 1.3) * np.cos(Y0 / 2900.0 - 0.4) * 0.5 + 0.5) * 420 \
        + (np.sin(X0 / 900.0 + Y0 / 1300.0) * 0.5 + 0.5) * 90 + np.cos(X0 / 5100.0 - Y0 / 4300.0) * 160
    rr = np.sqrt(X0 ** 2 + Y0 ** 2)
    mound += np.clip((rr - 15000 * ENV_SCALE) / (3000.0 * ENV_SCALE), 0, 1) * 700        # rises toward the fence for a horizon
    def blend(d, d0, d1):
        t = np.clip((d - d0) / (d1 - d0), 0, 1)
        return t * t * (3 - 2 * t)
    near = np.where(best < HALF_W, zin - 60, ze - 12)
    w = blend(best, HALF_W + 250, HALF_W + 3500)
    H = near * (1 - w) + (np.maximum(ze, 0) * 0.6 + mound - 120) * w
    # branch road corridors (shortcut, alternate route)
    for Q in BRANCHES:
        dq = np.sqrt(((pts[:, None, :] - Q.xy[None, :, :]) ** 2).sum(-1))
        jq = dq.argmin(1)
        dq = dq[np.arange(len(pts)), jq]
        zq = Q.z[jq]
        near_q = np.where(dq < Q.half_w, zq - 60, zq - 12)
        w2 = blend(dq, Q.half_w + 250, Q.half_w + 2500)
        H = np.where(dq < best, near_q * (1 - w2) + H * w2, H)
        best = np.minimum(best, dq)
    return H.reshape(X.shape)


def gen_ground():
    zl, zr = edge_heights()
    out = {}
    tiles = 4
    ext = 19000.0 * ENV_SCALE
    res = 96
    edges = np.linspace(-ext, ext, tiles + 1)
    for ty in range(tiles):
        for tx in range(tiles):
            xs = np.linspace(edges[tx], edges[tx + 1], res + 1)
            ys = np.linspace(edges[ty], edges[ty + 1], res + 1)
            X, Y = np.meshgrid(xs, ys)
            Hh = ground_height(X, Y, zl, zr)
            m = Mesh()
            ids = [[m.vert((X[j, i], Y[j, i], Hh[j, i]), (X[j, i] / 1000.0, Y[j, i] / 1000.0)) for i in range(res + 1)]
                   for j in range(res + 1)]
            for j in range(res):
                for i in range(res):
                    a, b, c, d = ids[j][i], ids[j][i + 1], ids[j + 1][i + 1], ids[j + 1][i]
                    # upward facing: in UE (X fwd, Y right) a->d->c is CCW seen from +Z? normals fixed in writer
                    m.quad("Ground", a, d, c, b)
            m.compute_normals()
            for i, n in enumerate(m.n):
                if n[2] < 0:
                    m.n[i] = (-n[0], -n[1], -n[2])
            out["SM_RG_Ground_%d%d" % (ty, tx)] = m
    return out


# ---------------------------------------------------------------- grass verges
def blade(m, mat, base, H, wid, ang, lean, bend, twist=0.0):
    ca, sa = math.cos(ang), math.sin(ang)

    def fn(u, v):
        w = wid * (1 - v) ** 0.7 * (1 if v < 0.98 else 0.2)
        off = (u - 0.5) * w
        lx = lean * v * v * H
        z = H * v - bend * H * v ** 3 * 0.25
        # blade plane oriented by ang; lean outward along its normal
        x = base[0] + off * ca + lx * -sa
        y = base[1] + off * sa + lx * ca
        cup = abs(u - 0.5) * w * 0.25
        return (x - cup * sa, y + cup * ca, base[2] + z)
    m.grid(mat, 2, 6, fn)


def gen_verges():
    rng = Rng(4711)
    out = {}
    nchunk = 10
    bounds = np.linspace(0, N, nchunk + 1).astype(int)
    zl, zr = edge_heights()
    for k in range(nchunk):
        m = Mesh()
        for i in range(bounds[k], bounds[k + 1]):
            c, f, r, u = T.frame(i)
            h = T.heading[i]
            r0 = np.array([-math.sin(h), math.cos(h)])
            for side in (-1, 1):
                for _ in range(5):
                    off = HALF_W + 260 + rng.r(0, 1) ** 1.6 * 1700
                    p = T.xy[i] + r0 * side * off + np.array([math.cos(h), math.sin(h)]) * rng.r(-50, 50)
                    if any(dist_to(Q.xy, p)[0] < Q.half_w + 350 for Q in BRANCHES):
                        continue
                    if in_tunnel(T, i) and off < TUN_R_OUT + 250:
                        continue
                    # whole-loop test: Losail's hairpin legs run side by side, so a blade
                    # must stay clear of every part of the road, not just its own leg
                    if dist_to(T.xy, p)[0] < HALF_W + 220:
                        continue
                    # keep the start/finish & grid sight-lines open (arch pillars, gantry, banners)
                    if abs(((i - I_START + N // 2) % N) - N // 2) < 6 and off < HALF_W + 900:
                        continue
                    zb = (zr[i] if side > 0 else zl[i]) - 25
                    tall = (off - HALF_W) / 1960.0
                    H = rng.r(250, 520) + tall * rng.r(300, 1300)
                    ang = h + rng.r(-0.8, 0.8)
                    lean_dir = side * rng.r(0.05, 0.35)
                    mat = "Grass" if rng.f() < 0.55 else ("GrassB" if rng.f() < 0.75 else "GrassDry")
                    blade(m, mat, (p[0], p[1], zb), H, rng.r(40, 85), ang, lean_dir, rng.r(0.3, 1.0))
        out["SM_RG_Verge_%02d" % k] = m
    return out


# ---------------------------------------------------------------- hollow log tube (unused in v5, kept for reuse)
def gen_tube(S, i0, i1, R_in, R_out, cz, seed=77):
    """Hollow-log tube over `S` (a Track or Branch) between samples i0..i1."""
    m = Mesh()
    a0, a1 = math.radians(-118), math.radians(118)
    segs = 40
    rings_in, rings_out = [], []
    rng = Rng(seed)
    bumps = [rng.r(0, 6.28) for _ in range(6)]
    for k, i in enumerate(range(i0, i1 + 1)):
        c, f, r, u = S.frame(i)
        axis_c = c + u * cz
        ri, ro = [], []
        for sgi in range(segs + 1):
            a = a0 + (a1 - a0) * sgi / segs
            d = u * math.cos(a) + r * math.sin(a)
            wob = 1 + 0.03 * math.sin(a * 7 + bumps[0] + k * 0.2) + 0.02 * math.sin(a * 17 + bumps[1])
            ri.append(m.vert(tuple(axis_c + d * R_in * (2 - wob)), (sgi / segs * 4, k * S.step / 300.0), tuple(-d)))
            ro.append(m.vert(tuple(axis_c + d * R_out * wob), (sgi / segs * 6, k * S.step / 300.0), tuple(d)))
        rings_in.append(ri)
        rings_out.append(ro)
    for k in range(len(rings_in) - 1):
        for sgi in range(segs):
            m.quad("LogInner", rings_in[k][sgi], rings_in[k][sgi + 1], rings_in[k + 1][sgi + 1], rings_in[k + 1][sgi])
            m.quad("Bark", rings_out[k][sgi], rings_out[k + 1][sgi], rings_out[k + 1][sgi + 1], rings_out[k][sgi + 1])
    # cut ends: annulus between inner and outer
    for k, sgn in ((0, -1), (len(rings_in) - 1, 1)):
        i = i0 + k
        c, f, r, u = S.frame(i)
        nrm = tuple(f * sgn)
        ids_i = [m.vert(m.p[v], (0.5, 0.5), nrm) for v in rings_in[k]]
        ids_o = [m.vert(m.p[v], (0.5, 0.5), nrm) for v in rings_out[k]]
        for sgi in range(segs):
            m.quad("WoodEnd", ids_i[sgi], ids_o[sgi], ids_o[sgi + 1], ids_i[sgi + 1])
        # rim lips down to ground
        for side_list in (ids_i, ids_o):
            pass
    # glowing fungus shelves inside, high on the walls (clear of the road)
    nf = max(10, int((i1 - i0) * S.step / 900))
    for k in range(nf):
        i = i0 + int((i1 - i0) * (0.08 + 0.84 * k / (nf - 1)))
        c, f, r, u = S.frame(i)
        side = -1 if k % 2 else 1
        a = side * math.radians(rng.r(55, 80))
        d = u * math.cos(a) + r * math.sin(a)
        base = c + u * cz + d * (R_in * 0.98)
        for j in range(3):
            rr = rng.r(70, 130)
            cen = base - d * rr * 0.5 + f * rng.r(-120, 120) + u * (j * 60 - 60)
            ellipsoid(m, "FungusGlow", tuple(cen), (rr, rr, rr * 0.35), 14, 8)
    return m


# ---------------------------------------------------------------- finish arch + start lights
def gen_arch():
    """Two giant curving grass-stem pillars with a checkered banner beam and a 5-light start gantry.
    Authored around the start line: X along the track, Y across, Z up, origin on the road centre."""
    m = Mesh()
    span = HALF_W + 650
    top = 2300.0     # raised from 1250 so the start-light gantry clears the high chase camera
    for side in (-1, 1):
        pts = [(0, side * span, -40), (30, side * span * 1.0, 400), (0, side * span * 0.98, 900), (-20, side * span * 0.93, top)]
        pts = catmull(pts, 6)
        tube_along(m, "Rail", pts, [90 - 20 * k / (len(pts) - 1) for k in range(len(pts))], segs=16)   # steel posts (were green stems)
        # leafy collar at the base
        for j in range(5):
            a = j * 2 * math.pi / 5 + 0.3
            L = 520

            def leaf(u, v, a=a, side=side):
                w = 170 * math.sin(math.pi * min(1.0, v * 1.05)) * (u - 0.5) * 2
                rr = 60 + v * L
                z = 30 + 260 * math.sin(v * 1.7) - 180 * v * v
                return (rr * math.cos(a) - w * math.sin(a), side * span + rr * math.sin(a) + w * math.cos(a), z)
            m.grid("KerbRed", 4, 10, leaf)   # red base fins
    # cross beam: rounded bar
    beam = [(0, -span, top - 30), (0, span, top - 30)]
    tube_along(m, "Rail", catmull(beam, 8), [55] * 9, segs=14)
    # checkered banner hanging below the beam (thin double-sided slab), 2 rows of squares
    sq = 120.0
    ncol = int(2 * (span - 120) // sq)
    w = 2 * (span - 120) / ncol
    for row in range(2):
        for col in range(ncol):
            mat = "PaintBlack" if (row + col) % 2 else "Paint"
            y0 = -(span - 120) + col * w
            z1 = top - 90 - row * sq
            for xo, nx in ((8, 1), (-8, -1)):
                ids = [m.vert((xo, y0, z1), (0, 0), (nx, 0, 0)), m.vert((xo, y0 + w, z1), (1, 0), (nx, 0, 0)),
                       m.vert((xo, y0 + w, z1 - sq), (1, 1), (nx, 0, 0)), m.vert((xo, y0, z1 - sq), (0, 1), (nx, 0, 0))]
                m.quad(mat, *ids)
    # start-light gantry hanging under the banner, facing the grid (-X)
    gz = top - 90 - 2 * sq - 40
    for side in (-1, 1):
        tube_along(m, "Rail", [(0, side * 520, top - 90 - 2 * sq), (0, side * 520, gz - 40)], [10, 10], segs=8)
    hb = [(-40, -620, gz - 190), (40, 620, gz)]
    _boxm(m, "Housing", hb)
    for k in range(5):
        y = -480 + k * 240
        for zz in (gz - 50, gz - 140):
            ellipsoid(m, "LampRed", (-44, y, zz), (14, 38, 38), 16, 10)
    return m


def _boxm(m, mat, b):
    (x0, y0, z0), (x1, y1, z1) = b
    faces = [((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
             ((-1, 0, 0), [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)]),
             ((0, 1, 0), [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)]),
             ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
             ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
             ((0, 0, -1), [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)])]
    for n, q in faces:
        ids = [m.vert(p, ((p[0] + p[1]) / 100.0, p[2] / 100.0), n) for p in q]
        m.quad(mat, *ids)


# ---------------------------------------------------------------- banners, bunting, lanterns
BANNER_COLS = ["BannerYellow", "BannerTeal", "BannerMagenta", "BannerOrange", "BannerPurple"]


def gen_flag():
    """Tall feather flag on a bendy pole (origin at pole base). Fabric is a thin slab."""
    m = Mesh()
    H = 1100.0
    tube_along(m, "Rail", [(0, 0, -30), (0, 0, H)], [9, 7], segs=8)
    ellipsoid(m, "Rail", (0, 0, H + 8), (14, 14, 14), 10, 6)
    for mat_i, (z0, z1) in enumerate([(380, 1080)]):
        def fab(u, v, sgn=1):
            x = 18 + u * 230 * (1 - 0.35 * v * v)          # feather shape curving back
            z = z1 - v * (z1 - z0) + (u * 60 if v > 0.9 else 0)
            y = 10 * math.sin(u * 3.0 + v * 2.0)
            return (x, y, z)
        m.grid("Fabric", 6, 10, fab)
        m.grid("Fabric", 6, 10, lambda u, v: (lambda p: (p[0], p[1] - 4, p[2]))(fab(u, v)), flip=True)
    return m


def gen_bunting(length=1800.0, sag=180.0, n=14):
    """String of pennants between two posts (origin at first post base, string along +X)."""
    m = Mesh()
    H = 700.0
    for x in (0.0, length):
        tube_along(m, "Rail", [(x, 0, -30), (x, 0, H + 30)], [12, 10], segs=8)
    pts = []
    for k in range(17):
        t = k / 16
        pts.append((t * length, 0, H - sag * 4 * t * (1 - t)))
    tube_along(m, "Rail", pts, [3] * len(pts), segs=5, cap=False)
    for k in range(n):
        t = (k + 0.5) / n
        x = t * length
        z = H - sag * 4 * t * (1 - t)
        w = length / n * 0.42
        mat = "Pennant%d" % (k % 5)
        for yo, ny in ((2.5, 1), (-2.5, -1)):
            a = m.vert((x - w, yo, z), (0, 0), (0, ny, 0))
            b = m.vert((x + w, yo, z), (1, 0), (0, ny, 0))
            c = m.vert((x, yo, z - w * 2.6), (0.5, 1), (0, ny, 0))
            m.tri(mat, a, b, c)
    return m


def gen_lantern():
    """Garden lantern post: curved stem, leaf cap, glowing bulb (origin at base)."""
    m = Mesh()
    pts = catmull([(0, 0, -30), (0, 0, 400), (40, 0, 760), (150, 0, 880)], 6)
    tube_along(m, "Stem", pts, [22 - 8 * k / (len(pts) - 1) for k in range(len(pts))], segs=10)
    ellipsoid(m, "LampWarm", (190, 0, 800), (52, 52, 70), 18, 12)
    ellipsoid(m, "Leaf", (190, 0, 870), (110, 110, 30), 18, 8)
    return m


def gen_chevron():
    """Yellow/black chevron board on two legs (faces -X, origin at base centre)."""
    m = Mesh()
    W, Hb, z0 = 520.0, 220.0, 130.0
    for y in (-W / 2 + 40, W / 2 - 40):
        tube_along(m, "Rail", [(0, y, -30), (0, y, z0 + Hb)], [10, 10], segs=8)
    _boxm(m, "ChevronBlack", [(-6, -W / 2, z0), (6, W / 2, z0 + Hb)])
    # chevrons (pointing +Y) as raised geometry on the -X face
    for k in range(3):
        y0 = -W / 2 + 70 + k * 140
        pts = [(y0, z0 + 25), (y0 + 70, z0 + Hb / 2), (y0, z0 + Hb - 25), (y0 + 40, z0 + Hb - 25), (y0 + 110, z0 + Hb / 2),
               (y0 + 40, z0 + 25)]
        ids = [m.vert((-8, p[0], p[1]), (0, 0), (-1, 0, 0)) for p in pts]
        m.tri("ChevronYellow", ids[0], ids[1], ids[5])
        m.tri("ChevronYellow", ids[1], ids[4], ids[5])
        m.tri("ChevronYellow", ids[1], ids[2], ids[4])
        m.tri("ChevronYellow", ids[2], ids[3], ids[4])
    return m


# ---------------------------------------------------------------- garden props
def gen_root_arch(seed=5, span=3800.0 * HALF_W / 800.0, height=2600.0 * HALF_W / 950.0):
    """Gnarled root arching over the road (origin centre, arch spans along Y)."""
    rng = Rng(seed)
    m = Mesh()
    pts = []
    for k in range(11):
        t = k / 10
        y = (t - 0.5) * span
        z = height * math.sin(math.pi * t) ** 0.8 - 120
        x = 160 * math.sin(t * 5 + 1) + rng.r(-40, 40)
        pts.append((x, y, z))
    pts = catmull(pts, 4)
    rad = [230 * (1.15 - 0.45 * math.sin(math.pi * k / (len(pts) - 1))) for k in range(len(pts))]
    tube_along(m, "Bark", pts, rad, segs=18)
    # side rootlets spreading into the ground at both feet
    for side in (-1, 1):
        for j in range(4):
            a = rng.r(-1.2, 1.2)
            foot = (0, side * span * 0.5, -60)
            q = [foot, (300 * math.sin(a), side * (span * 0.5 + 300 * math.cos(a)), 60),
                 (700 * math.sin(a), side * (span * 0.5 + 700 * math.cos(a)), -40)]
            tube_along(m, "Bark", catmull(q, 4), [110 - 9 * i for i in range(9)], segs=10)
    return m


def gen_ground_root(seed, L=4200.0):
    rng = Rng(seed)
    m = Mesh()
    pts = []
    for k in range(9):
        t = k / 8
        pts.append((t * L, 260 * math.sin(t * 4 + seed), 90 * math.sin(t * math.pi) - 40 + rng.r(-30, 30)))
    pts = catmull(pts, 4)
    tube_along(m, "Bark", pts, [160 * (1 - 0.7 * k / (len(pts) - 1)) + 20 for k in range(len(pts))], segs=14)
    return m


def gen_leaf(seed, L=2600.0, W=1100.0, curl=0.35, mat="LeafA"):
    """Fallen leaf with a raised midrib, curled edges (lies on ground, origin at stem)."""
    rng = Rng(seed)
    m = Mesh()

    def fn(u, v):
        x = v * L
        half = W * 0.5 * math.sin(math.pi * min(1.0, v ** 0.8)) * (1 - 0.15 * v)
        y = (u - 0.5) * 2 * half
        e = abs(u - 0.5) * 2
        z = 25 + curl * half * e * e + 120 * math.sin(v * math.pi) * 0.6 + 40 * math.sin(v * 9 + u * 3)
        return (x, y, z)
    m.grid(mat, 12, 24, fn)
    m.grid(mat, 12, 24, lambda u, v: (lambda p: (p[0], p[1], p[2] - 6))(fn(u, v)), flip=True)
    tube_along(m, "Stem", [(-160, 0, 10), (0, 0, 30), (L * 0.9, 0, 30 + 120 * math.sin(0.9 * math.pi) * 0.6)], [30, 26, 8], segs=8)
    return m


def gen_seedpod(seed, H=520.0):
    rng = Rng(seed)
    m = Mesh()
    ribs = 7

    def deform(p, d):
        ph = math.atan2(d[1], d[0])
        k = 1 + 0.08 * math.cos(ribs * ph)
        z = p[2]
        taper = 1 - 0.35 * max(0.0, d[2])
        return (p[0] * k * taper, p[1] * k * taper, z)
    ellipsoid(m, "Pod", (0, 0, H * 0.5), (H * 0.33, H * 0.33, H * 0.5), 36, 18, deform=deform)
    tube_along(m, "Stem", [(0, 0, H * 0.95), (20, 0, H * 1.12), (70, 0, H * 1.2)], [26, 18, 10], segs=8)
    return m


def gen_glow_mushrooms(seed):
    """Cluster of small glowing toadstools (origin at cluster centre)."""
    rng = Rng(seed)
    m = Mesh()
    for k in range(5):
        a = rng.r(0, 6.28)
        d = rng.r(0, 180)
        x, y = d * math.cos(a), d * math.sin(a)
        H = rng.r(120, 320)
        R = H * rng.r(0.45, 0.65)
        tube_along(m, "MushStem", [(x, y, -10), (x + rng.r(-20, 20), y, H)], [R * 0.22, R * 0.18], segs=10)
        ellipsoid(m, "FungusGlow", (x, y, H), (R, R, R * 0.45),
                  20, 10, deform=lambda p, dd: (p[0], p[1], p[2] if dd[2] > 0 else p[2] * 0.3))
    return m


# ---------------------------------------------------------------- placements
def yaw_deg(i):
    return math.degrees(T.heading[i % N])


def track_pt(i, lat, path=T):
    c, f, r, u = path.frame(i)
    return c + r * lat


def clear_of_roads(p, margin):
    p = np.asarray(p)
    return clear_of_tunnels(p, margin) and dist_to(T.xy, p[:2])[0] > HALF_W + margin and all(dist_to(Q.xy, p[:2])[0] > Q.half_w + margin for Q in BRANCHES)


# Unscaled XY footprint (min x, min y, max x, max y) of the scatter meshes, read from the UE assets.
# Giant flowers/clumps spread far wider than their trunk, so placement tests the whole footprint.
FOOT = {"SM_TomatoPlant_A": (-2169, -1874, 1710, 1592), "SM_TomatoPlant_B": (-1927, -1357, 1937, 2312),
        "SM_Sunflower": (-1505, -1475, 1246, 1379), "SM_Daisy": (-1321, -857, 842, 1287),
        "SM_GrassClump_B": (-1186, -1135, 1998, 1109), "SM_Allium": (-757, -1444, 1103, 1420),
        "SM_GrassClump_A": (-1423, -1130, 1213, 1244), "SM_RG_GroundRoot": (-104, -393, 4240, 237),
        "SM_RainPuddle": (-1095, -739, 997, 877), "SM_RG_FallenLeaf_A": (-178, -516, 2600, 516),
        "SM_Twig": (-848, -48, 842, 399), "SM_RG_GlowMushrooms": (-274, -265, 213, 340),
        "SM_PetalDebris": (-231, -96, 231, 96), "SM_Acorn_A": (-98, -98, 98, 98),
        "SM_RG_FallenLeaf_B": (-178, -609, 2000, 609), "SM_Acorn_B": (-98, -98, 98, 98),
        "SM_Clover_B": (-165, -202, 254, 176), "SM_Pebble_A": (-224, -248, 224, 202),
        "SM_Pebble_C": (-314, -258, 289, 220), "SM_RG_SeedPod": (-171, -182, 185, 182),
        "SM_Clover_A": (-144, -208, 230, 168), "SM_Pebble_B": (-166, -157, 163, 146),
        "SM_Mushroom_A": (-308, -319, 318, 301), "SM_Mushroom_B": (-296, -267, 232, 265),
        "SM_Dandelion": (-955, -1163, 1389, 1133), "SM_PinkFlower": (-1096, -1388, 1034, 659),
        "SM_Poppy": (-598, -666, 1281, 1151), "SM_TulipYellow": (-1473, -1739, 979, 1356),
        "SM_TulipRed": (-1670, -526, 706, 1870), "SM_Bluebell": (-1711, -1446, 1254, 1559),
        "SM_Lavender": (-522, -502, 480, 586)}


def footprint_clear(mesh, p, yaw_deg_, scale, margin=None):
    """True when the mesh's rotated, scaled XY footprint stays `margin` clear of every road
    (450 cm for big plants, 330 cm for small ground props; both keep outside barriers and tunnel shells)."""
    fx0, fy0, fx1, fy1 = FOOT[mesh.split("/")[-1]]
    if margin is None:
        margin = 330.0 if max(abs(fx0), abs(fy0), fx1, fy1) * scale < 400.0 else 450.0
    a = math.radians(yaw_deg_)
    ca, sa = math.cos(a), math.sin(a)
    for u in (0.0, 0.5, 1.0):
        for v in (0.0, 0.5, 1.0):
            lx = (fx0 + (fx1 - fx0) * u) * scale
            ly = (fy0 + (fy1 - fy0) * v) * scale
            q = (p[0] + lx * ca - ly * sa, p[1] + lx * sa + ly * ca)
            if not clear_of_roads(q, margin):
                return False
    return True


def placements():
    P_ = []
    add = lambda mesh, loc, rot=(0, 0, 0), scale=1.0, folder="Props", coll=False, label=None: P_.append(
        {"mesh": mesh, "loc": [float(loc[0]), float(loc[1]), float(loc[2])], "rot": [float(x) for x in rot],
         "scale": [float(scale)] * 3 if not isinstance(scale, (list, tuple)) else [float(x) for x in scale],
         "folder": folder, "collision": coll, "label": label})
    NEW = "/Game/RacingGame/Meshes/"
    BB = "/Game/BugBattle/Meshes/"
    # finish arch at start line
    c, f, r, u = T.frame(I_START)
    add(NEW + "SM_RG_FinishArch", (c[0] + 5, c[1], T.z[I_START]), (0, yaw_deg(I_START), 0), folder="Track/StartFinish",
        label="FinishArch_StartLights")
    # flags & bunting on straights B and H (both sides, outside verges)
    rng = Rng(99)
    for i in [i for i in STRAIGHT if not near_start(i, 22)][::17]:
        for side in (-1, 1):
            p = track_pt(i, side * (HALF_W + 330))
            add(NEW + "SM_RG_FlagBanner", (p[0], p[1], T.z[i % N] - 20), (0, yaw_deg(i) + (180 if side < 0 else 0) + rng.r(-15, 15), 0),
                scale=rng.r(0.9, 1.15), folder="Track/Banners", label="FlagBanner")
    for i in [i for i in STRAIGHT if i > I_START + 14][::22]:
        for side in (-1, 1):
            p = track_pt(i, side * (HALF_W + 220))
            add(NEW + "SM_RG_Bunting", (p[0], p[1], T.z[i] - 20), (0, yaw_deg(i), 0), folder="Track/Banners", label="Bunting")
    # lanterns along the grid (trackside lighting)
    for i in range(STRAIGHT[0], I_START + 30, 9):
        for side in (-1, 1):
            p = track_pt(i, side * (HALF_W + 140))
            add(NEW + "SM_RG_Lantern", (p[0], p[1], T.z[i % N] - 20), (0, yaw_deg(i) + (90 if side < 0 else -90), 0),
                folder="Track/Lighting", label="Lantern")
    # outside chevrons on the heavy-braking corners: Turn 1, the two hairpins, the chicane
    for apex in (L(88, 62.5), L(38, 12.5), L(30, 37.6), L(31.1, 53.1)):
        i_tight = T.index_at(*apex)
        for k in (-14, -7, 0):
            i = (i_tight + k) % N
            side = -1 if T.curv[i] > 0 else 1
            p = track_pt(i, side * (HALF_W + 200))
            if dist_to(T.xy, p[:2])[0] < HALF_W + 150:      # would sit on a neighbouring leg
                continue
            add(NEW + "SM_RG_ChevronBoard", (p[0], p[1], T.z[i] - 15), (0, yaw_deg(i) + 180, 0), folder="Track/Signs",
                label="CornerChevron")
    # root arches over the north-east straight and the long right-hand sweep
    for pt, label, sc in ((L(79.5, 46), "RootArch", 1.0), (L(63.5, 31), "RootArch_North", [1.0, 1.05, 1.15])):
        i_root = T.index_at(*pt)
        c, f, r, u = T.frame(i_root)
        add(NEW + "SM_RG_RootArch", (c[0], c[1], T.z[i_root]), (0, yaw_deg(i_root), 0), scale=sc, folder="Environment/Roots",
            label=label)

    # ---------------- scatter (existing BugBattle meshes + new garden props), kept off the roads
    rng = Rng(2024)
    flowers = [BB + "Arena/SM_Sunflower", BB + "Arena/SM_Daisy", BB + "Arena/SM_PinkFlower",
               BB + "Wildflowers/SM_TulipRed", BB + "Wildflowers/SM_TulipYellow", BB + "Wildflowers/SM_Allium",
               BB + "Wildflowers/SM_Poppy", BB + "Wildflowers/SM_Lavender", BB + "Wildflowers/SM_Dandelion",
               BB + "Wildflowers/SM_Bluebell"]
    placed = []

    def try_place(mesh, p, rad, margin, scale, folder, label, z_off=0.0, rot=None):
        if not clear_of_roads(p, margin + rad):
            return False
        rot = rot or (0, rng.r(0, 360), 0)
        if not footprint_clear(mesh, p, rot[1], scale if not isinstance(scale, (list, tuple)) else max(scale)):
            return False
        for (q, qr) in placed:
            if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < (qr + rad) ** 2 * 0.55:
                return False
        if abs(p[0]) > 17000 * ENV_SCALE or abs(p[1]) > 17000 * ENV_SCALE or (p[0] ** 2 + p[1] ** 2) > (17200 * ENV_SCALE) ** 2:
            return False
        placed.append((p, rad))
        i, _ = T.nearest(p[:2])
        z = ground_at(p)
        add(mesh, (p[0], p[1], z + z_off), rot, scale, folder, False, label)
        return True

    # Section D garden passage + trackside giant flowers (middle ground): along the whole loop, both sides
    for i in range(0, N, 3):
        h = T.heading[i]
        r0 = np.array([-math.sin(h), math.cos(h)])
        for side in (-1, 1):
            if rng.f() < 0.35:
                continue
            off = HALF_W + rng.r(1700, 4200)
            p = T.xy[i] + r0 * side * off
            fm = flowers[int(rng.r(0, len(flowers)))]
            sc = rng.r(0.75, 1.25)
            try_place(fm, p, 650 * sc, 300, sc, "Environment/Flowers", "Flower")
    # denser giant flower canopy in the garden passage (D) - closer to the road
    for i in range(T.index_at(*L(86, 58)), T.index_at(*L(85, 19)), 3):
        h = T.heading[i]
        r0 = np.array([-math.sin(h), math.cos(h)])
        for side in (-1, 1):
            off = HALF_W + rng.r(1450, 2400)
            p = T.xy[i] + r0 * side * off
            fm = flowers[int(rng.r(0, len(flowers)))]
            sc = rng.r(0.8, 1.2)
            try_place(fm, p, 700 * sc, 250, sc, "Environment/Flowers", "PassageFlower")
    # mushrooms clusters (300-800 tall) near the track, small rocks, clover
    for i in list(range(0, N, 2)) * 2:
        h = T.heading[i]
        r0 = np.array([-math.sin(h), math.cos(h)])
        side = 1 if rng.f() < 0.5 else -1
        roll = rng.f()
        if roll < 0.18:
            p = T.xy[i] + r0 * side * (HALF_W + rng.r(520, 1200))
            ms = BB + ("Arena/SM_Mushroom_A" if rng.f() < 0.5 else "Arena/SM_Mushroom_B")
            sc = rng.r(0.6, 1.25)
            try_place(ms, p, 330 * sc, 200, sc, "Environment/Mushrooms", "Mushroom")
        elif roll < 0.30:
            p = T.xy[i] + r0 * side * (HALF_W + rng.r(300, 900))
            pb = BB + "Arena/SM_Pebble_" + "ABC"[int(rng.r(0, 3))]
            sc = rng.r(0.6, 2.2)
            try_place(pb, p, 230 * sc, 150, sc, "Environment/Rocks", "Pebble", rot=(rng.r(-8, 8), rng.r(0, 360), rng.r(-8, 8)))
        elif roll < 0.38:
            p = T.xy[i] + r0 * side * (HALF_W + rng.r(380, 900))
            cl = BB + "Garden/SM_Clover_" + "AB"[int(rng.r(0, 2))]
            sc = rng.r(1.5, 3.0)
            try_place(cl, p, 200 * sc, 150, sc, "Environment/Vegetation", "Clover")
        elif roll < 0.43:
            p = T.xy[i] + r0 * side * (HALF_W + rng.r(700, 1800))
            try_place(NEW + "SM_RG_SeedPod", p, 260, 200, rng.r(0.7, 1.4), "Environment/Vegetation", "SeedPod",
                      rot=(rng.r(-12, 12), rng.r(0, 360), rng.r(-12, 12)))
        elif roll < 0.47:
            p = T.xy[i] + r0 * side * (HALF_W + rng.r(500, 1100))
            try_place(NEW + "SM_RG_GlowMushrooms", p, 260, 180, rng.r(0.8, 1.4), "Environment/Mushrooms", "GlowMushrooms")
    # giant mushrooms as landmarks (scaled 2-3.5x) further out
    for k in range(90):
        a = rng.r(0, 6.28)
        rr = rng.r(2000, 16000) * ENV_SCALE
        p = np.array([rr * math.cos(a), rr * math.sin(a)])
        ms = BB + ("Arena/SM_Mushroom_A" if k % 2 else "Arena/SM_Mushroom_B")
        sc = rng.r(1.8, 3.6)
        try_place(ms, p, 330 * sc, 900, sc, "Environment/Mushrooms", "GiantMushroom")
    # fallen leaves, roots, puddles, acorns, twigs on the ground (foreground/middle)
    for k in range(420):
        a = rng.r(0, 6.28)
        rr = rng.r(1000, 16000) * ENV_SCALE
        p = np.array([rr * math.cos(a), rr * math.sin(a)])
        roll = rng.f()
        if roll < 0.28:
            try_place(NEW + "SM_RG_FallenLeaf_" + "AB"[k % 2], p, 1300, 350, rng.r(0.7, 1.3), "Environment/Leaves", "FallenLeaf")
        elif roll < 0.45:
            try_place(NEW + "SM_RG_GroundRoot", p, 2100, 400, rng.r(0.7, 1.2), "Environment/Roots", "GroundRoot")
        elif roll < 0.58:
            try_place(BB + "Garden/SM_RainPuddle", p, 1000, 300, rng.r(0.8, 1.6), "Environment/Puddles", "Puddle", z_off=8)
        elif roll < 0.72:
            try_place(BB + "Garden/SM_Acorn_" + "AB"[k % 2], p, 150, 250, rng.r(2.0, 3.5), "Environment/Vegetation", "Acorn",
                      rot=(rng.r(-70, 70), rng.r(0, 360), rng.r(-30, 30)), z_off=60)
        elif roll < 0.84:
            try_place(BB + "Arena/SM_Twig", p, 850, 300, rng.r(1.5, 3.0), "Environment/Vegetation", "Twig")
        else:
            try_place(BB + "Arena/SM_PetalDebris", p, 230, 200, rng.r(2, 4), "Environment/Vegetation", "Petals")
    # big grass clumps + tomato plants + flowers as dense background ring (in front of the fence)
    for k in range(340):
        a = 2 * math.pi * k / 340 + rng.r(-0.01, 0.01)
        rr = rng.r(14800, 16900) * ENV_SCALE
        p = np.array([rr * math.cos(a), rr * math.sin(a)])
        roll = rng.f()
        if roll < 0.45:
            mesh = BB + "Arena/SM_GrassClump_" + "AB"[k % 2]
            sc = rng.r(1.0, 1.8)
            try_place(mesh, p, 1100 * sc * 0.6, 500, sc, "Environment/Background", "BgGrass")
        elif roll < 0.62:
            mesh = BB + "Garden/SM_TomatoPlant_" + "AB"[k % 2]
            try_place(mesh, p, 1500, 500, rng.r(0.9, 1.3), "Environment/Background", "BgTomato")
        else:
            fm = flowers[int(rng.r(0, len(flowers)))]
            sc = rng.r(1.2, 1.9)
            try_place(fm, p, 900 * sc * 0.6, 500, sc, "Environment/Background", "BgFlower")
    # infield: grass clumps & flowers mid-ground
    for k in range(650):
        p = np.array([rng.r(-36, 36), rng.r(-27, 27)]) * LAYOUT_SCALE
        roll = rng.f()
        if roll < 0.35:
            sc = rng.r(0.7, 1.2)
            try_place(BB + "Arena/SM_GrassClump_" + "AB"[k % 2], p, 1100 * sc * 0.6, 600, sc, "Environment/Infield", "InfieldGrass")
        elif roll < 0.8:
            fm = flowers[int(rng.r(0, len(flowers)))]
            sc = rng.r(0.9, 1.4)
            try_place(fm, p, 900 * sc * 0.7, 600, sc, "Environment/Infield", "InfieldFlower")
        else:
            try_place(BB + "Garden/SM_TomatoPlant_" + "AB"[k % 2], p, 1500, 900, rng.r(0.7, 1.0), "Environment/Infield", "InfieldTomato")
    # make sure the rarer props always appear (random scatter can skip them entirely)
    for mesh, rad, folder, label, rr0, rr1, want in ((NEW + "SM_RG_GroundRoot", 1200, "Environment/Roots", "GroundRoot", 3000 * ENV_SCALE, 15000 * ENV_SCALE, 3),
                                                      (BB + "Garden/SM_TomatoPlant_A", 800, "Environment/Background", "BgTomato", 14800 * ENV_SCALE, 16900 * ENV_SCALE, 3)):
        got = sum(1 for q in P_ if q["mesh"] == mesh)
        for _ in range(2000):
            if got >= want:
                break
            a = rng.r(0, 6.28)
            rr = rng.r(rr0, rr1)
            got += try_place(mesh, np.array([rr * math.cos(a), rr * math.sin(a)]), rad, 400, rng.r(0.8, 1.2), folder, label)
    # backyard fence ring (existing) as horizon
    add(BB + "Garden/SM_BackyardFence", (0, 0, 380), (0, 0, 0), [ENV_SCALE, ENV_SCALE, 1.0], "Environment/Background", False, "BackyardFence")
    return P_


ZL = ZR = None


def ground_at(p):
    X = np.array([[p[0]]])
    Y = np.array([[p[1]]])
    return float(ground_height(X, Y, ZL, ZR)[0, 0])


def main():
    global ZL, ZR
    only = sys.argv[1:]
    ZL, ZR = edge_heights()
    gens = {}
    if not only or "roads" in only:
        gens.update(gen_roads())
    if not only or "marks" in only:
        gens["SM_RG_GridMarkings"] = gen_markings()
    if not only or "ground" in only:
        gens.update(gen_ground())
    if not only or "verge" in only:
        gens.update(gen_verges())
    if not only or "props" in only:
        for (name, path, a, b) in TUNNELS:
            ri, ro, cz = tunnel_dims(HALF_W)
            gens[name] = gen_tube(path, a, b, ri, ro, cz, seed=len(name) + a)
        gens["SM_RG_FinishArch"] = gen_arch()
        gens["SM_RG_FlagBanner"] = gen_flag()
        gens["SM_RG_Bunting"] = gen_bunting()
        gens["SM_RG_Lantern"] = gen_lantern()
        gens["SM_RG_ChevronBoard"] = gen_chevron()
        gens["SM_RG_RootArch"] = gen_root_arch()
        gens["SM_RG_GroundRoot"] = gen_ground_root(3)
        gens["SM_RG_FallenLeaf_A"] = gen_leaf(1)
        gens["SM_RG_FallenLeaf_B"] = gen_leaf(2, L=2000, W=1300, curl=0.6, mat="LeafB")
        gens["SM_RG_SeedPod"] = gen_seedpod(4)
        gens["SM_RG_GlowMushrooms"] = gen_glow_mushrooms(6)
    for name, m in gens.items():
        print(name, m.write_obj(os.path.join(OUT, name + ".obj")))
    if not GRID_SLOTS:
        gen_markings()
    pl = placements()
    meta = {
        "grid_slots": [{"loc": [float(x) for x in p], "yaw": float(y)} for p, y in GRID_SLOTS],
        "start_index": I_START, "lap_length_cm": float(T.length),
        "start_line": [float(x) for x in T.frame(I_START)[0]],
        "placements": pl,
    }
    json.dump(meta, open(os.path.join(HERE, "placements.json"), "w"), indent=1)
    print("placements", len(pl))


if __name__ == "__main__":
    main()
