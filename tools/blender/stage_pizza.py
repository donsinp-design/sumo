# PIZZA stage, fully modelled: a giant Neapolitan-style pizza (the fighting surface) on a dark steel tray raised on a
# chrome stand, on a trattoria table with a red/white gingham cloth, plus table props (chianti-bottle candle, wine
# glass, parmesan + chili shakers, pizza cutter, napkins, crumbs). Built entirely by script (Blender 4.2, headless).
#   python tools/blender/stage_pizza.py [out_dir] [shot=game|low ...] [fast] [noexport] [norender]
# Writes <out_dir>/pizza.glb (stage only: Z up, metres, origin at pizza centre, top of cheese ~0, textures <=1024 px)
# and <out_dir>/ex_game.png / ex_low.png (with the game's masked sumos + gyoji imported from scratchpad/stage).
#
# Game contract (public/js/config.js, stages.js): ring radius 4.6, fighting surface flat inside r 5.3 (|z| <= 3 cm).
# So everything inside 5.3 is a heightfield with <= 3 cm of real relief; the food detail there (cheese folds and
# blisters, sauce peeks, cut grooves, cheese strings, oil) lives in 2048 px numpy-painted colour / roughness /
# normal maps, and only the cornicione (r 5.3..6.3), which is outside the fighting area, gets big real relief.
# The ring edge is a circular cutter groove at r 4.6 with the sauce showing through (same language as the 8 cuts).
import bpy, bmesh, math, sys, os, time
import numpy as np
from mathutils import Vector, Matrix

SCR = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
CHAR_DIR = SCR + '/stage'
FLAGW = {'fast', 'noexport', 'norender', 'tris', 'dump'}
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in FLAGW and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else SCR + '/pizza'
os.makedirs(OUT, exist_ok=True)
SHOTS = [a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')] or ['game', 'low']
FAST = 'fast' in sys.argv
T0 = time.time()
def log(*a): print('[pizza %5.1fs]' % (time.time() - T0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RING = 4.6          # fighting circle
RFLAT = 5.3         # flat (<= 3 cm) inside this
TZ = -3.25          # table (cloth) top
STAGE = bpy.data.collections.new('stage'); scn.collection.children.link(STAGE)
BG = bpy.data.collections.new('bg'); scn.collection.children.link(BG)


# ================================================================ helpers
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
def lin(h): return tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in hx(h))
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def mix(a, b, t):
    t = np.asarray(t, np.float32)
    iscol = (np.ndim(a) >= 1 and np.shape(a)[-1] == 3) or (np.ndim(b) >= 1 and np.shape(b)[-1] == 3)
    if iscol and t.ndim >= 1 and t.shape[-1] != 3: t = t[..., None]
    return a + (b - a) * t

def gn(shape, sig, seed, ang=None):
    """Isotropic (or anisotropic, sig=(along, across) at angle ang) gaussian-filtered white noise, periodic, std 1.
    sig in pixels; scalar or (sy, sx)."""
    H, W = shape
    n = np.random.default_rng(seed).standard_normal((H, W)).astype(np.float32)
    ky = np.fft.fftfreq(H)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    if ang is None:
        sy, sx = (sig, sig) if np.isscalar(sig) else sig
        g = np.exp(-2 * math.pi ** 2 * ((sx * kx) ** 2 + (sy * ky) ** 2))
    else:
        sa, sb = sig; c, s = math.cos(ang), math.sin(ang)
        ka = kx * c + ky * s; kb = -kx * s + ky * c
        g = np.exp(-2 * math.pi ** 2 * ((sa * ka) ** 2 + (sb * kb) ** 2))
    o = np.fft.irfft2(np.fft.rfft2(n) * g, s=(H, W)).astype(np.float32)
    return o / (o.std() + 1e-9)

def blur(a, sig):
    H, W = a.shape[:2]
    ky = np.fft.fftfreq(H)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    sy, sx = (sig, sig) if np.isscalar(sig) else sig
    g = np.exp(-2 * math.pi ** 2 * ((sx * kx) ** 2 + (sy * ky) ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(H, W)).astype(np.float32)

def h2n(Hm, dx, dy, k=1.0):
    gy, gx = np.gradient(Hm, dy, dx)
    n = np.stack([-k * gx, -k * gy, np.ones_like(Hm)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5

IMGS = []
def image(name, arr, noncolor=False):
    arr = np.clip(arr, 0, 1).astype(np.float32)
    H, W = arr.shape[:2]
    im = bpy.data.images.new(name, W, H, alpha=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    px = np.ones((H, W, 4), np.float32); px[..., :arr.shape[2]] = arr
    im.pixels.foreach_set(px.ravel()); im.update(); IMGS.append(im); return im

def orm(rough, metal=None, sssm=None):
    a = np.zeros(rough.shape + (3,), np.float32)
    a[..., 0] = 1 if sssm is None else sssm; a[..., 1] = rough; a[..., 2] = 0 if metal is None else metal
    return a

def pmat(name, color='ffffff', img=None, rough=0.5, ormimg=None, nimg=None, nstr=1.0, metal=0.0, sss=0.0,
         sss_r=(1.0, 0.5, 0.25), sss_s=0.02, sss_mask=False, trans=0.0, ior=1.45, coat=0.0, coat_r=0.05, sheen=0.0,
         sheen_r=0.5, emit=None, emit_s=0.0, alpha=False, spec=0.5, tint=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(color), 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['IOR'].default_value = ior; b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = sss_r
    b.inputs['Subsurface Scale'].default_value = sss_s
    b.inputs['Transmission Weight'].default_value = trans
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = coat_r
    b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = sheen_r
    if emit:
        b.inputs['Emission Color'].default_value = (*lin(emit), 1); b.inputs['Emission Strength'].default_value = emit_s
    if img:
        t = N.new('ShaderNodeTexImage'); t.image = img; t.location = (-600, 300)
        if tint:
            mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs['Factor'].default_value = 1
            L.new(t.outputs['Color'], mm.inputs[6]); mm.inputs[7].default_value = (*tint, 1); L.new(mm.outputs[2], b.inputs['Base Color'])
        else: L.new(t.outputs['Color'], b.inputs['Base Color'])
        if alpha:
            L.new(t.outputs['Alpha'], b.inputs['Alpha']); m.blend_method = 'CLIP'; m.alpha_threshold = 0.5
    if ormimg:
        t = N.new('ShaderNodeTexImage'); t.image = ormimg; t.location = (-600, 0)
        sp = N.new('ShaderNodeSeparateColor'); sp.location = (-300, 0); L.new(t.outputs['Color'], sp.inputs['Color'])
        L.new(sp.outputs['Green'], b.inputs['Roughness']); L.new(sp.outputs['Blue'], b.inputs['Metallic'])
        if sss_mask:
            mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = sss
            L.new(sp.outputs['Red'], mu.inputs[0]); L.new(mu.outputs[0], b.inputs['Subsurface Weight'])
    if nimg:
        t = N.new('ShaderNodeTexImage'); t.image = nimg; t.location = (-600, -300)
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr; nm.location = (-300, -300)
        L.new(t.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m

def mk(name, V, F, UV=None, mat=None, smooth=True, coll=None):
    V = np.asarray(V, np.float32)
    me = bpy.data.meshes.new(name); me.from_pydata(V.tolist(), [], [list(map(int, f)) for f in F]); me.update()
    if UV is not None:
        UV = np.asarray(UV, np.float32)
        uvl = me.uv_layers.new(name='UVMap'); li = np.zeros(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', li)
        uvl.data.foreach_set('uv', UV[li].ravel())
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    o = bpy.data.objects.new(name, me); (coll or STAGE).objects.link(o)
    if mat: me.materials.append(mat)
    return o

def grid_faces(nr, nc, wrap_c=False):
    F = []
    cc = nc if wrap_c else nc - 1
    for i in range(nr - 1):
        for j in range(cc):
            j2 = (j + 1) % nc
            F.append((i * nc + j, i * nc + j2, (i + 1) * nc + j2, (i + 1) * nc + j))
    return F

def lathe(prof, segs, name, mat, uvfn=None, coll=None, z0=0.0, xy=(0, 0)):
    prof = np.asarray(prof, np.float32); n = len(prof)
    a = np.linspace(0, TAU, segs + 1)
    V = []; UV = []
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))]; L /= L[-1]
    for i in range(n):
        for j in range(segs + 1):
            x = prof[i, 0] * math.cos(a[j]); y = prof[i, 0] * math.sin(a[j])
            V.append((x + xy[0], y + xy[1], prof[i, 1] + z0))
            UV.append(uvfn(x, y, j / segs, L[i]) if uvfn else (j / segs, L[i]))
    return mk(name, V, grid_faces(n, segs + 1), UV, mat, coll=coll)

def chaikin(P, it=3, closed=False):
    P = np.asarray(P, np.float64)
    for _ in range(it):
        Q = P if not closed else np.vstack([P, P[:1]])
        a = Q[:-1] * 0.75 + Q[1:] * 0.25; b = Q[:-1] * 0.25 + Q[1:] * 0.75
        R = np.empty((2 * len(a), P.shape[1])); R[0::2] = a; R[1::2] = b
        P = R if closed else np.vstack([P[:1], R, P[-1:]])
    return P

def resample(P, n, closed=False):
    Q = np.vstack([P, P[:1]]) if closed else P
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    s = np.linspace(0, L[-1], n + (1 if closed else 0))
    out = np.stack([np.interp(s, L, Q[:, k]) for k in range(Q.shape[1])], -1)
    return (out[:-1] if closed else out), L[-1]

def tube(pts, rad, sides=8, cap=True):
    """Sweep a circle along a polyline (parallel transport). Returns V, F."""
    pts = np.asarray(pts, np.float64); n = len(pts); rad = np.broadcast_to(np.asarray(rad, np.float64), (n,))
    T = np.gradient(pts, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    ref = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    Nn = np.cross(T[0], ref); Nn /= np.linalg.norm(Nn)
    V = []
    for i in range(n):
        if i:
            Nn = Nn - T[i] * Nn.dot(T[i]); Nn /= np.linalg.norm(Nn) + 1e-12
        Bn = np.cross(T[i], Nn)
        for k in range(sides):
            a = k / sides * TAU
            V.append(pts[i] + rad[i] * (math.cos(a) * Nn + math.sin(a) * Bn))
    F = grid_faces(n, sides, wrap_c=True)
    if cap:
        V.append(pts[0]); V.append(pts[-1]); c0, c1 = len(V) - 2, len(V) - 1
        for k in range(sides):
            F.append((c0, (k + 1) % sides, k)); F.append((c1, (n - 1) * sides + k, (n - 1) * sides + (k + 1) % sides))
    return np.array(V), F

def sample(arr, u, v):
    """bilinear sample arr (H,W[,C]) at uv in 0..1 (rows = v)."""
    H, W = arr.shape[:2]
    x = np.clip(u * W - 0.5, 0, W - 1.001); y = np.clip(v * H - 0.5, 0, H - 1.001)
    x0 = x.astype(int); y0 = y.astype(int); fx = x - x0; fy = y - y0
    if arr.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    return (arr[y0, x0] * (1 - fx) * (1 - fy) + arr[y0, x0 + 1] * fx * (1 - fy) + arr[y0 + 1, x0] * (1 - fx) * fy + arr[y0 + 1, x0 + 1] * fx * fy)

def stamp_iter(shape, cx, cy, rad):
    """yield (ys, xs, d2-grid offsets) of a patch around (cx, cy) px with half size rad px (clipped)."""
    H, W = shape
    x0 = max(int(cx - rad - 1), 0); x1 = min(int(cx + rad + 2), W); y0 = max(int(cy - rad - 1), 0); y1 = min(int(cy + rad + 2), H)
    if x1 <= x0 or y1 <= y0: return None
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    return slice(y0, y1), slice(x0, x1), xx + 0.5 - cx, yy + 0.5 - cy


# ================================================================ layout: cuts, pepperoni, basil
rng = np.random.default_rng(7)
CUTS = [math.radians(22.5 + 45 * k) for k in range(8)]
FIGHTERS = [(-1.0, -0.15), (1.0, 0.15)]
PEPS = []
for k in range(4):
    a = math.radians(45 + 90 * k + rng.uniform(-5, 5)); r = 2.05 + rng.uniform(-0.12, 0.12)
    PEPS.append((r * math.cos(a), r * math.sin(a), rng.uniform(0.56, 0.64)))
for k in range(8):
    a = math.radians(45 * k + rng.uniform(-6, 6)); r = 3.55 + rng.uniform(-0.18, 0.15)
    PEPS.append((r * math.cos(a), r * math.sin(a), rng.uniform(0.56, 0.67)))
def cutdist(x, y):
    r = math.hypot(x, y); th = math.atan2(y, x)
    return min(r * abs(math.sin(th - c)) if math.cos(th - c) > 0 else 99 for c in CUTS)
LEAVES = []
tries = 0
while len(LEAVES) < 6 and tries < 5000:
    tries += 1
    r = math.sqrt(rng.uniform(0.3, 1)) * 4.0; a = rng.uniform(0, TAU); x, y = r * math.cos(a), r * math.sin(a)
    L = rng.uniform(0.85, 1.15)
    if cutdist(x, y) < 0.5 or r > 3.95: continue
    if any(math.hypot(x - px, y - py) < pr + 0.6 for px, py, pr in PEPS): continue
    if any(math.hypot(x - fx, y - fy) < 0.9 for fx, fy in FIGHTERS): continue
    if any(math.hypot(x - lx, y - ly) < 1.3 for lx, ly, *_ in LEAVES): continue
    LEAVES.append((x, y, L, rng.uniform(0, TAU), len(LEAVES) == 2))


# ================================================================ the pizza top (cheese / sauce / cuts) maps
def worley(N, E, pts, warp=None):
    """F1, F2 distances (metres) on an N x N grid over [-E, E]^2 (computed at N/4 and upsampled)."""
    n = N // 4; px = 2 * E / n
    c = (np.arange(n, dtype=np.float32) + 0.5) * px - E
    X, Y = np.meshgrid(c, c); Q = np.stack([X.ravel(), Y.ravel()], -1)
    if warp is not None: Q = Q + warp.reshape(-1, 2)
    F1 = np.full(len(Q), 1e9, np.float32); F2 = np.full(len(Q), 1e9, np.float32)
    for i in range(0, len(Q), 16384):
        d = np.sqrt(((Q[i:i + 16384, None, :] - pts[None, :, :]) ** 2).sum(-1))
        p = np.partition(d, 1, axis=1)
        F1[i:i + 16384] = p[:, 0]; F2[i:i + 16384] = p[:, 1]
    up = lambda a: sample(a.reshape(n, n), *np.meshgrid((np.arange(N) + 0.5) / N, (np.arange(N) + 0.5) / N))
    return up(F1), up(F2)

def build_top():
    N = 1024 if FAST else 2048; E = 5.45; px = 2 * E / N
    c = (np.arange(N, dtype=np.float32) + 0.5) * px - E
    X, Y = np.meshgrid(c, c); R = np.hypot(X, Y); TH = np.arctan2(Y, X)
    m = lambda s: s / px     # metres -> px
    nb = gn((N, N), m(0.6), 1); nm = gn((N, N), m(0.16), 2); ns = gn((N, N), m(0.045), 3); nf = gn((N, N), m(0.012), 4)
    nmi = gn((N, N), m(0.004), 5); nb2 = gn((N, N), m(1.2), 6); nm2 = gn((N, N), m(0.25), 8); nl = gn((N, N), m(0.5), 10)
    # --- melted cheese pools: warped Worley cells (pieces of mozzarella that melted into each other)
    pts = []
    rp = np.random.default_rng(21)
    while len(pts) < 230:
        q = rp.uniform(-5.1, 5.1, 2)
        if np.hypot(*q) < 5.05 and all(np.hypot(*(q - p)) > 0.42 for p in pts): pts.append(q)
    pts = np.array(pts, np.float32)
    n4 = N // 4
    wv = np.stack([gn((n4, n4), n4 / 24, 201), gn((n4, n4), n4 / 24, 202)], -1) * 0.22
    F1, F2 = worley(N, E, pts, wv)
    e = blur((F2 - F1) * 0.5, m(0.02)) + 0.03 * nm + 0.012 * ns     # distance to the seam between two pools
    # --- cut grooves (8 slices, healing shut in places) + the continuous ring cut at 4.6 (the fighting circle)
    thw = TH + 0.0035 * nm
    dcut = np.full((N, N), 99, np.float32); cutang = np.zeros((N, N), np.float32)
    for ca in CUTS:
        dd = R * np.abs(np.sin(thw - ca)); dd = np.where(np.cos(thw - ca) > 0, dd, 99)
        cutang = np.where(dd < dcut, ca, cutang); dcut = np.minimum(dcut, dd)
    wc = (0.02 + 0.008 * ns + 0.006 * nl)
    dring = np.abs(R - (RING + 0.01 * nb)); wr = 0.062 + 0.01 * ns
    gcut = ss(wc + 0.02, wc - 0.004, dcut) * ss(0.25, 0.5, R) * (wc > 0.004)
    gring = ss(wr + 0.022, wr - 0.008, dring)
    G = np.maximum(gcut, gring)
    rim = np.maximum(np.exp(-((dcut - wc - 0.035) / 0.03) ** 2) * ss(0.25, 0.5, R) * ss(0.0, 0.01, wc), np.exp(-((dring - wr - 0.035) / 0.03) ** 2))
    # --- cheese strings bridging the grooves: thick where they leave the cheese, thin and sagging in the middle
    S = np.zeros((N, N), np.float32); SH = np.zeros((N, N), np.float32)
    segs = []
    for ca in CUTS:
        for _ in range(7):
            r = rng.uniform(0.8, 4.3); w = rng.uniform(0.008, 0.02); off = rng.uniform(-0.03, 0.03)
            t = np.array([math.cos(ca), math.sin(ca)]); nrm = np.array([-t[1], t[0]]); sk = rng.uniform(-0.05, 0.05)
            segs.append((t * r - nrm * 0.07 + t * off, t * r + nrm * 0.07 + t * (off + sk), w))
    for _ in range(34):
        a = rng.uniform(0, TAU); t = np.array([math.cos(a), math.sin(a)]); nrm = np.array([-t[1], t[0]])
        w = rng.uniform(0.008, 0.022); sk = rng.uniform(-0.06, 0.06)
        segs.append((t * (RING - 0.11), t * (RING + 0.11) + nrm * sk, w))
    for p0, p1, w in segs:
        cx, cy = (p0 + p1) / 2; half = np.linalg.norm(p1 - p0) / 2 + w * 3
        st = stamp_iter((N, N), (cx + E) / px, (cy + E) / px, m(half))
        if not st: continue
        sy, sx, dx, dy = st
        P = np.stack([dx * px + cx, dy * px + cy], -1); d = p1 - p0
        tt = np.clip(((P - p0) @ d) / (d @ d), 0, 1)
        dist = np.linalg.norm(P - (p0 + tt[..., None] * d), axis=-1)
        wt = w * (0.45 + 2.2 * (1 - np.sin(math.pi * tt)) ** 2)
        msk = ss(wt, wt * 0.3, dist) * 0.92
        S[sy, sx] = np.maximum(S[sy, sx], msk)
        SH[sy, sx] = np.maximum(SH[sy, sx], msk * (0.002 - 0.012 * np.sin(math.pi * tt)))
    S = S * ss(0.1, 0.6, G)
    Ge = G * (1 - S)
    # --- cheese coverage: pools separated by sauce channels where the seam gap is open, plus a few holes
    redge = 5.0 + 0.09 * nm + 0.05 * ns + 0.02 * nf
    C0 = ss(redge + 0.02, redge - 0.03, R)
    gap = 0.05 * (nm2 * 0.8 + 0.25 * ns - 1.05)
    pool = ss(gap, gap + 0.05, e)
    hole = ss(-1.5, -1.2, 0.75 * nm2 + 0.4 * nm + 0.15 * ns + 0.08 * nf)
    c = hole * C0 * (1 - G)
    cs = ss(0.1, 0.85, blur(c, m(0.04)))                 # rounded, thick melted edges
    dome = ss(0.0, 0.32, e) * cs                         # pools are pillowy: highest in the middle
    valley = (1 - ss(0.0, 0.16, e)) * c * (0.5 + 0.5 * ss(-1, 1, nl))   # merged seams: shallow oily valleys
    T = np.clip(0.55 + 0.25 * nb + 0.3 * dome + 0.1 * nm, 0.05, 1)
    # --- stringy folds: anisotropic noise layers following a flow field, pulled perpendicular to the cuts
    near_cut = np.exp(-(dcut / 0.3) ** 2) * ss(0.25, 0.6, R); near_ring = np.exp(-(dring / 0.3) ** 2)
    phi = np.where(near_cut > near_ring, cutang + math.pi / 2, TH)
    wdir = np.maximum(near_cut, near_ring)
    vx = (1 - wdir) * np.cos(2 * math.pi * nb2 * 0.7) + wdir * np.cos(2 * phi)
    vy = (1 - wdir) * np.sin(2 * math.pi * nb2 * 0.7) + wdir * np.sin(2 * phi)
    phi = 0.5 * np.arctan2(vy, vx)
    F = np.zeros((N, N), np.float32); wsum = np.zeros((N, N), np.float32)
    for k in range(6):
        a = k * math.pi / 6
        lay = gn((N, N), (m(0.25), m(0.02)), 20 + k, ang=a)
        w = np.maximum(np.cos(2 * (phi - a)), 0) ** 3
        F += w * lay; wsum += w
    F /= wsum + 1e-6
    ridge = (1 - np.clip(np.abs(F) / 1.6, 0, 1)) ** 4
    # --- blisters: clean browned domes on the pool tops, clustered (leopard)
    BLh = np.zeros((N, N), np.float32); BLb = np.zeros((N, N), np.float32); BLd = np.zeros((N, N), np.float32)
    clus = blur(nb + 0.7 * nm, m(0.1))
    bl = []
    while len(bl) < 900:
        r = math.sqrt(rng.uniform(0, 1)) * 5.0; a = rng.uniform(0, TAU); x, y = r * math.cos(a), r * math.sin(a)
        i, j = int((y + E) / px), int((x + E) / px)
        pr = (0.2 + 0.8 * (clus[i, j] > 0.0)) * (0.45 + 0.55 * ss(3.0, 4.9, r)) * float(c[i, j] > 0.6) * (0.3 + 0.7 * ss(0.04, 0.2, e[i, j]))
        if any(math.hypot(x - qx, y - qy) < qr * 1.05 for qx, qy, qr in PEPS): pr = 0
        if rng.uniform() < pr: bl.append((x, y))
    for x, y in bl:
        big = rng.uniform() < 0.28
        rad = rng.uniform(0.1, 0.3) if big else rng.uniform(0.03, 0.08)
        st = stamp_iter((N, N), (x + E) / px, (y + E) / px, m(rad * 1.5))
        if not st: continue
        sy, sx, dx, dy = st
        d = np.hypot(dx, dy) * px / (rad * (1 + 0.18 * ns[sy, sx] + 0.06 * nf[sy, sx]))
        dm = np.clip(1 - d * d, 0, 1)
        h = (0.004 + 0.007 * rng.uniform()) * (rad / 0.24) ** 0.4
        BLh[sy, sx] = np.maximum(BLh[sy, sx], h * dm ** 1.2)
        b = rng.uniform(0.45, 1.0) * (1.0 if big else rng.uniform(0.6, 1.0))
        BLb[sy, sx] = np.maximum(BLb[sy, sx], b * ss(0.0, 0.7, dm))
        if rng.uniform() < (0.12 if big else 0.06):
            BLd[sy, sx] = np.maximum(BLd[sy, sx], ss(0.35, 0.8, dm) * rng.uniform(0.5, 1.0))
    BLb *= c; BLd *= c
    # --- grease: a thin ring round each pepperoni that runs off along the valleys; an olive-oil drizzle
    OIL = np.zeros((N, N), np.float32); UNDER = np.zeros((N, N), np.float32); NEAR = np.zeros((N, N), np.float32)
    for x, y, pr in PEPS:
        d = np.hypot(X - x, Y - y)
        OIL = np.maximum(OIL, ss(pr * 1.16 + 0.03 * ns, pr * 1.0, d))
        NEAR = np.maximum(NEAR, ss(pr * 2.2, pr * 1.05, d))
        UNDER = np.maximum(UNDER, ss(pr * 1.02, pr * 0.9, d))
    OIL = np.maximum(OIL, valley * (0.35 + 0.65 * NEAR) * ss(-0.6, 0.6, nm))
    for k in range(3):
        a0 = rng.uniform(0, TAU); r0 = rng.uniform(1.0, 3.5)
        tt = np.linspace(0, 1, 160); aa = a0 + tt * rng.uniform(1.2, 2.4); rr = r0 + 0.8 * np.sin(tt * 5 + k) * tt
        P2 = np.stack([rr * np.cos(aa), rr * np.sin(aa)], -1)
        for (x, y), w in zip(P2, 0.025 + 0.025 * np.sin(tt * 17) ** 2):
            st = stamp_iter((N, N), (x + E) / px, (y + E) / px, m(w * 1.5))
            if not st: continue
            sy, sx, dx, dy = st
            OIL[sy, sx] = np.maximum(OIL[sy, sx], 0.7 * ss(w, w * 0.4, np.hypot(dx, dy) * px))
    drops = ss(2.2, 2.6, gn((N, N), m(0.018), 9)) * ss(-0.3, 0.6, nb)
    OIL = np.clip(np.maximum(OIL, drops * 0.9), 0, 1) * ss(5.25, 5.0, R)
    # --- colours (sRGB)
    sauce = mix(hx('b4321a'), hx('8a1e0e'), ss(-0.8, 1.6, nm2 * 0.6 + ns * 0.6))
    pulp = ss(1.3, 2.2, nf)
    sauce = mix(sauce, hx('d2522a'), 0.35 * pulp)
    sauce = mix(sauce, hx('6a1409'), 0.5 * ss(0.05, 0.6, blur(c, m(0.03))) * (1 - c))         # reduced at cheese edges
    sauce = mix(sauce, hx('4a0f07'), ss(5.1, 5.32, R) * (0.5 + 0.3 * nm))                      # caramelised at the crust
    sauce = mix(sauce, hx('5a1208'), 0.45 * ss(0.3, 0.9, G) * (1 - S))                          # shadowed groove floor
    ch = mix(hx('e2a244'), hx('f2d17e'), ss(0.1, 0.8, T) * cs)
    ch = mix(ch, hx('f7e0a0'), 0.4 * dome * ss(-0.5, 1.0, nm))
    ch = ch * (1 + 0.04 * ridge[..., None] - 0.03 * ss(-1, 1, ns)[..., None])
    ch = mix(ch, hx('e2a64a'), valley * 0.35)
    br = np.clip(0.25 + 0.35 * nb + 0.55 * ss(3.9, 5.0, R) + 0.25 * nm, 0, 1) * 0.6 + 0.35 * rim * c
    ch = mix(ch, hx('d8963e'), br * 0.65)
    ch = mix(ch, hx('e6a444'), ss(0.0, 0.35, BLb)); ch = mix(ch, hx('c86e26'), ss(0.25, 0.8, BLb)); ch = mix(ch, hx('8e4214'), ss(0.7, 1.0, BLb) * 0.8)
    ch = mix(ch, hx('5e2a0e'), BLd * 0.7)
    ch = mix(ch, hx('e88a28'), OIL * 0.45)
    ch = mix(ch, hx('c8642a'), UNDER * 0.5)
    col = mix(sauce, ch, c)
    col = mix(col, hx('f4e2b0'), S)
    col = mix(col, hx('d8b070'), ss(5.25, 5.4, R))
    herb = ss(3.1, 3.6, gn((N, N), m(0.006), 11)) * ss(-0.5, 0.8, nb2)
    col = mix(col, hx('3a4418'), herb * 0.85)
    chili = ss(3.5, 3.9, gn((N, N), m(0.01), 12))
    col = mix(col, hx('b8320e'), chili * 0.9)
    # --- height (metres, within the 3 cm budget)
    Hm = -0.02 + 0.0012 * ns + 0.0008 * pulp * (1 - c)
    Hm = Hm + c * (0.013 * cs + 0.007 * dome - 0.003 * valley + 0.0014 * ridge * cs + 0.003 * rim) + BLh * c
    Hm = Hm - 0.004 * Ge + SH * S
    Hm = Hm * (1 - UNDER) - 0.028 * UNDER
    Hm = np.clip(np.where(R > 5.35, -0.02, Hm), -0.029, 0.027)
    # --- roughness, sss
    rough = mix(np.full((N, N), 0.16, np.float32), 0.4 - 0.05 * ridge - 0.06 * dome, c)
    rough = mix(rough, 0.5, ss(0.3, 0.8, BLb)); rough = mix(rough, 0.66, BLd)
    rough = mix(rough, 0.06, OIL * 0.9)
    rough = rough + 0.04 * nf
    sssm = np.clip(0.25 + 0.75 * c, 0, 1) * (1 - 0.6 * ss(0.3, 0.9, BLb))
    micro = 0.0004 * nmi + 0.0003 * nf + 0.0003 * herb + 0.0004 * chili + 0.0005 * pulp * (1 - c)
    nrm = h2n(Hm + micro * (1 - OIL * 0.8), px, px, 3.5)
    TOP = dict(N=N, E=E, H=Hm)
    log('top maps built')
    return (image('top_col', col), image('top_orm', orm(np.clip(rough, 0.03, 1), None, sssm), True),
            image('top_nrm', nrm, True), TOP)


def build_pizza_top():
    col, ormi, nrm, TOP = build_top()
    M = pmat('m_pizza_top', img=col, ormimg=ormi, nimg=nrm, nstr=1.0, sss=0.3, sss_mask=True,
             sss_r=(1.0, 0.75, 0.35), sss_s=0.012, spec=0.55, coat=0.0)
    E = TOP['E']; Hs = blur(TOP['H'], 4)
    K, S = 44, 176
    rr = RFLAT + 0.06
    V = [(0, 0, 0)]; UV = [(0.5, 0.5)]
    rings = np.linspace(0, 1, K + 1)[1:] ** 0.85 * rr
    for r in rings:
        for j in range(S):
            a = j / S * TAU; V.append((r * math.cos(a), r * math.sin(a), 0))
    V = np.array(V, np.float32)
    U = (V[:, 0] + E) / (2 * E); W = (V[:, 1] + E) / (2 * E)
    V[:, 2] = sample(Hs, U, W)
    F = [(0, 1 + j, 1 + (j + 1) % S) for j in range(S)]
    for i in range(K - 1):
        for j in range(S):
            a0 = 1 + i * S; a1 = 1 + (i + 1) * S; j2 = (j + 1) % S
            F.append((a0 + j, a1 + j, a1 + j2, a0 + j2))
    o = mk('pizza_top', V, F, np.stack([U, W], -1), M)
    # underside disc
    bot = [(0, 0, -0.215)] + [(5.6 * math.cos(j / 64 * TAU), 5.6 * math.sin(j / 64 * TAU), -0.215) for j in range(64)]
    mk('pizza_bottom', bot, [(0, (j + 1) % 64 + 1, j + 1) for j in range(64)], [(0.5, 0.5)] * 65, M)
    return TOP


# ================================================================ crust (cornicione): 8 lumpy slices of a profile sweep
PROF_CTRL = [(5.26, -0.045), (5.31, -0.012), (5.37, 0.06), (5.45, 0.2), (5.56, 0.345), (5.71, 0.455), (5.88, 0.485),
             (6.04, 0.44), (6.18, 0.32), (6.28, 0.15), (6.31, 0.0), (6.27, -0.12), (6.14, -0.195), (5.86, -0.215),
             (5.5, -0.215), (5.3, -0.15)]
NT = 36
PROF, PLEN = resample(chaikin(PROF_CTRL, 3, closed=True), NT, closed=True)
# rotate so row 0 is the inner start (closest to the first control point)
i0 = int(np.argmin(np.linalg.norm(PROF - np.array(PROF_CTRL[0]), axis=1))); PROF = np.roll(PROF, -i0, axis=0)
PTAN = np.roll(PROF, -1, 0) - np.roll(PROF, 1, 0); PTAN /= np.linalg.norm(PTAN, axis=1, keepdims=True)
PNRM = np.stack([-PTAN[:, 1], PTAN[:, 0]], -1)       # outward for a clockwise loop
if PNRM[np.argmax(PROF[:, 1]), 1] < 0: PNRM = -PNRM
S_OF_T = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([PROF, PROF[:1]]), axis=0), axis=1))]
TT = S_OF_T / S_OF_T[-1]                             # t of each row (NT+1 values, closed)
CV = 0.875                                           # crust texture: v 0..CV = profile, above = crumb
bubbles = []
rb = np.random.default_rng(31)
for _ in range(46):
    th = rb.uniform(0, math.pi); tb = rb.uniform(0.12, 0.3)
    big = rb.uniform() < 0.3
    bubbles.append((th, tb * S_OF_T[-1], rb.uniform(0.12, 0.24) if big else rb.uniform(0.05, 0.11), rb.uniform(0.035, 0.08) if big else rb.uniform(0.015, 0.035), rb.uniform() < 0.75))

def zprof_t(t):
    return np.interp(t, TT, np.r_[PROF[:, 1], PROF[0, 1]])

def build_crust_tex():
    W, H = (2048, 512) if FAST else (4096, 1024)
    Hp = int(H * CV)
    du = math.pi * 5.8 / W; dv = S_OF_T[-1] / Hp
    u = (np.arange(W) + 0.5) / W; t = (np.arange(Hp) + 0.5) / Hp
    U, Tt = np.meshgrid(u, t)
    Z = zprof_t(Tt); top = np.clip(Z / 0.48, 0, 1)
    m = lambda s: (s / dv, s / du)
    n1 = gn((Hp, W), m(0.12), 41); n2 = gn((Hp, W), m(0.035), 42); n3 = gn((Hp, W), m(0.01), 43); n4 = gn((Hp, W), m(0.003), 44)
    # browning
    B = np.clip(0.38 + 0.6 * top ** 1.2 + 0.16 * n1 + 0.07 * n2, 0, 1)
    under = ss(-0.13, -0.19, Z)
    TTOP = TT[int(np.argmax(PROF[:, 1]))]
    outer = ss(TTOP, TTOP + 0.08, Tt) * ss(0.3, 0.1, Z)
    col = mix(hx('e4bc7c'), hx('d29242'), ss(0.1, 0.45, B))
    col = mix(col, hx('b26a28'), ss(0.45, 0.85, B)); col = mix(col, hx('804016'), ss(0.85, 1.0, B) * 0.7)
    # leopard spots + charred bubble tops
    SP = np.zeros((Hp, W), np.float32); HA = np.zeros((Hp, W), np.float32); BH = np.zeros((Hp, W), np.float32)
    rs = np.random.default_rng(55)
    spots = []
    for _ in range(2600 if not FAST else 1300):
        tt = rs.uniform(0.04, 0.52); pz = zprof_t(tt) / 0.48
        if rs.uniform() > 0.05 + 0.95 * max(pz, 0) ** 2: continue
        spots.append((rs.uniform(0, 1), tt, rs.uniform(0.01, 0.028) if rs.uniform() < 0.72 else rs.uniform(0.03, 0.075), rs.uniform(0.5, 1.0)))
    for th, sb, rbub, hb, ch in bubbles:
        spots.append((th / math.pi, sb / S_OF_T[-1], rbub * (0.45 if ch else 0.2), 1.0 if ch else 0.5))
        BHc = (th / math.pi, sb / S_OF_T[-1], rbub)
        for off in (-1, 0, 1):
            st = stamp_iter((Hp, W), (BHc[0] + off) * W, BHc[1] * Hp, max(rbub / du, rbub / dv) * 1.2)
            if not st: continue
            sy, sx, dx, dy = st
            d = np.hypot(dx * du, dy * dv) / rbub
            BH[sy, sx] = np.maximum(BH[sy, sx], np.clip(1 - d * d, 0, 1) ** 1.5 * hb)
    for su, st_, sr, si in spots:
        for off in (-1, 0, 1):
            st = stamp_iter((Hp, W), (su + off) * W, st_ * Hp, max(sr / du, sr / dv) * 2.6)
            if not st: continue
            sy, sx, dx, dy = st
            d = np.hypot(dx * du, dy * dv) / (sr * (1 + 0.35 * n3[sy, sx] + 0.2 * n4[sy, sx]))
            SP[sy, sx] = np.maximum(SP[sy, sx], si * ss(1.0, 0.35, d))
            HA[sy, sx] = np.maximum(HA[sy, sx], si * ss(2.6, 0.8, d))
    col = mix(col, hx('8a4a1c'), HA * 0.55)
    col = mix(col, hx('3a1c0c'), ss(0.1, 0.6, SP)); col = mix(col, hx('160d08'), ss(0.6, 1.0, SP) * 0.9)
    # flour / semolina dust on the outer, lower side
    fl = np.maximum(outer, under) * (0.5 + 0.5 * ss(-0.5, 1.0, n1))
    col = mix(col, hx('f1e6cf'), 0.35 * fl)
    sem = ss(2.6, 3.2, gn((Hp, W), m(0.004), 45)) * (0.3 + fl)
    col = mix(col, hx('f6eee0'), np.clip(sem, 0, 1) * 0.8)
    # underside: oven-floor spotting
    col = mix(col, hx('9a6a3a'), under * 0.5)
    col = mix(col, hx('2a180c'), under * ss(1.6, 2.2, n2))
    # sauce stain / cheese drips on the inner foot
    inner = ss(0.075, 0.03, Tt + 0.02 * n2)
    col = mix(col, hx('8c2210'), inner * 0.9)
    drip = ss(1.2, 1.6, gn((Hp, W), (m(0.06)[0], m(0.025)[1]), 46)) * ss(0.12, 0.05, Tt)
    col = mix(col, hx('ecc888'), drip)
    col = col * (0.94 + 0.06 * n3[..., None] * 0.5)
    rough = np.clip(0.74 + 0.06 * n2 + 0.12 * ss(0.3, 0.9, SP) - 0.35 * inner - 0.25 * drip - 0.12 * ss(1.0, 2.0, n1) * top, 0.2, 1)
    hgt = 0.0016 * n3 + 0.0009 * n4 + 0.0025 * n2 * top + 0.001 * sem - 0.0012 * SP + BH * 0.0
    cracks = ss(0.06, 0.0, np.abs(gn((Hp, W), m(0.02), 47))) * top * 0.6
    hgt -= 0.0012 * cracks
    col = mix(col, hx('6a3410'), cracks * 0.25)
    nrm = h2n(hgt, du, dv, 1.6)
    # crumb strip (cut faces)
    Hc = H - Hp
    n5 = gn((Hc, W), 3.0, 48); n6 = gn((Hc, W), 9.0, 49)
    holes = ss(0.9, 1.4, n5 + 0.4 * n6)
    ccol = mix(hx('f0dcaa'), hx('a07840'), holes); ccol = mix(ccol, hx('c48a40'), 0.3 * ss(0.5, 1.5, n6))
    crough = np.full((Hc, W), 0.85, np.float32)
    cn = h2n(-holes * 0.004 + 0.001 * n5, du, du, 1.0)
    COL = np.concatenate([col, ccol], 0); ROUGH = np.concatenate([rough, crough], 0); NRM = np.concatenate([nrm, cn], 0)
    log('crust maps built')
    return image('crust_col', COL), image('crust_orm', orm(ROUGH), True), image('crust_nrm', NRM, True)

def build_crust():
    col, ormi, nrm = build_crust_tex()
    M = pmat('m_crust', img=col, ormimg=ormi, nimg=nrm, nstr=1.0, sss=0.18, sss_r=(1.0, 0.7, 0.4), sss_s=0.03, sheen=0.25, sheen_r=0.6)
    rl = np.random.default_rng(77)
    LM = gn((128, 2048), (4.0, 6.0), 61)          # lumps over (s, theta) for the whole circle
    LM2 = gn((128, 2048), (1.6, 2.2), 62)
    n1 = gn((1, 2048), (1, 40), 63)[0]; n2 = gn((1, 2048), (1, 25), 64)[0]; n3 = gn((1, 2048), (1, 70), 65)[0]
    gap = 0.03
    NC = 36 if FAST else 72
    for k in range(8):
        a0 = CUTS[k]; a1 = CUTS[(k + 1) % 8] + (TAU if k == 7 else 0)
        ths = np.linspace(a0 + gap / 5.8, a1 - gap / 5.8, NC + 1)
        V = []; UV = []
        for th in ths:
            ti = int((th % TAU) / TAU * 2048) % 2048
            hs = 1 + 0.13 * n1[ti] + 0.05 * n3[ti]; rsft = 0.06 * n2[ti]
            e = min(abs(th - a0), abs(a1 - th)) * 5.8
            squash = 1 - 0.2 * math.exp(-(e / 0.3) ** 2)
            for i in range(NT + 1):
                ii = i % NT
                rho, z = PROF[ii]; nr, nz = PNRM[ii]; t = TT[i]
                if z > 0: z = z * hs * squash
                rho = rho + rsft * ss(5.45, 5.9, rho) * (1 if z > -0.15 else 0.5)
                w = ss(-0.06, 0.1, PROF[ii, 1]) * ss(5.33, 5.45, PROF[ii, 0])
                s = S_OF_T[i]
                lump = 0.026 * sample(LM, np.array([(th % TAU) / TAU]), np.array([s / S_OF_T[-1]]))[0] + 0.01 * sample(LM2, np.array([(th % TAU) / TAU]), np.array([s / S_OF_T[-1]]))[0]
                bb = 0.0
                for bth, bs, br, bh, _ in bubbles:
                    dth = ((th - bth + math.pi / 2) % math.pi) - math.pi / 2
                    d2 = (dth * rho) ** 2 + (s - bs) ** 2
                    if d2 < br * br: bb = max(bb, bh * (1 - d2 / (br * br)) ** 1.5)
                dd = w * (lump + bb)
                V.append((math.cos(th) * (rho + nr * dd), math.sin(th) * (rho + nr * dd), z + nz * dd))
                UV.append((th / math.pi, t * CV))
        nrow = NT + 1
        F = []
        for j in range(NC):
            for i in range(NT):
                F.append((j * nrow + i, j * nrow + i + 1, (j + 1) * nrow + i + 1, (j + 1) * nrow + i))
        V = np.array(V); UV = np.array(UV)
        # caps (cut faces): separate verts, fan from centroid, crumb UVs
        for end, jj in ((0, 0), (1, NC)):
            ring = V[jj * nrow: jj * nrow + NT]
            cen = ring.mean(0); base = len(V)
            capV = np.vstack([ring, cen[None]])
            rr_ = np.hypot(capV[:, 0], capV[:, 1])
            capUV = np.stack([0.05 + 0.4 * (rr_ - 5.2) / 1.2 + 0.5 * end, CV + 0.01 + 0.11 * (capV[:, 2] + 0.25) / 0.8], -1)
            V = np.vstack([V, capV]); UV = np.vstack([UV, capUV])
            for i in range(NT):
                f = (base + NT, base + i, base + (i + 1) % NT)
                F.append(f if end else f[::-1])
        o = mk('crust_%d' % k, V, F, UV, M)
        me = o.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    log('crust built')


# ================================================================ pepperoni cups
def build_pepperoni(TOP):
    N = 512 if FAST else 1024; e = 1.12; px = 2 * e / N
    c = (np.arange(N) + 0.5) * px - e; X, Y = np.meshgrid(c, c); R = np.hypot(X, Y); A = np.arctan2(Y, X)
    m = lambda s: s / px
    n1 = gn((N, N), m(0.12), 81); n2 = gn((N, N), m(0.035), 82); n3 = gn((N, N), m(0.01), 83)
    col = mix(hx('bc3a1c'), hx('8a2210'), ss(-1.2, 1.5, n1 * 0.5 + n2 * 0.4 + 0.4 * n3))
    FAT = np.zeros((N, N), np.float32)
    rp = np.random.default_rng(5)
    for _ in range(900):
        x, y = rp.uniform(-1, 1, 2)
        if x * x + y * y > 0.92: continue
        rad = rp.uniform(0.006, 0.022)
        st = stamp_iter((N, N), (x + e) / px, (y + e) / px, m(rad * 1.6))
        sy, sx, dx, dy = st
        d = np.hypot(dx, dy) * px / (rad * (1 + 0.3 * n3[sy, sx]))
        FAT[sy, sx] = np.maximum(FAT[sy, sx], ss(1.0, 0.6, d))
    col = mix(col, hx('c8644a'), FAT * 0.6)
    pep = ss(2.8, 3.3, gn((N, N), m(0.008), 84))
    col = mix(col, hx('2a0805'), pep)
    rimw = 0.74 + 0.06 * n2
    crisp = ss(rimw - 0.06, 0.97, R)
    col = mix(col, hx('3e0c06'), crisp * 0.9); col = mix(col, hx('1e0503'), ss(0.95, 1.0, R + 0.02 * n2))
    pool = ss(0.62 + 0.05 * n2, 0.42, R)
    col = mix(col, hx('c4401a'), pool * 0.3)
    col = mix(col, hx('5a1a0a'), ss(0.6, 1.4, n3) * crisp * 0.5)       # blistered charred bits on the rim
    rough = np.clip(0.42 + 0.05 * n2 - 0.35 * pool + 0.2 * crisp - 0.1 * FAT, 0.04, 1)
    wr = np.sin(A * 34 + 3 * n1) * ss(0.7, 0.98, R)                       # rim wrinkles
    cup = 0.13 * ss(0.25, 0.92, R + 0.03 * n2) ** 1.6 * ss(1.06, 0.93, R)            # the curled cup, faked in the normals
    hgt = cup + 0.0015 * n3 + 0.0012 * n2 + 0.002 * FAT + 0.004 * wr - 0.002 * pool * ss(-1, 1, n2)
    nrm = h2n(hgt, px * 0.62, px * 0.62, 1.6)
    M = pmat('m_pepperoni', img=image('pep_col', col), ormimg=image('pep_orm', orm(rough), True), nimg=image('pep_nrm', nrm, True),
             sss=0.25, sss_r=(1.0, 0.3, 0.15), sss_s=0.02, coat=0.35, coat_r=0.08)
    NR, NS = 9, 44
    for k, (px0, py0, pr) in enumerate(PEPS):
        rr_ = np.random.default_rng(100 + k)
        rot = rr_.uniform(0, TAU)
        rad_n = 1 + 0.035 * np.sin(np.arange(NS) / NS * TAU * 3 + rr_.uniform(0, 6)) + 0.02 * np.sin(np.arange(NS) / NS * TAU * 7 + rr_.uniform(0, 6))
        rim_h = 1 + 0.22 * np.sin(np.arange(NS) / NS * TAU * 2 + rr_.uniform(0, 6)) + 0.1 * np.sin(np.arange(NS) / NS * TAU * 5)
        V = [(0, 0, -0.026)]; UV = [(0.5, 0.5)]
        for i in range(1, NR + 1):
            q = i / NR
            for j in range(NS):
                a = j / NS * TAU; rq = q * rad_n[j]
                z = -0.026 + 0.04 * rim_h[j] * q ** 2.2
                V.append((rq * pr * math.cos(a), rq * pr * math.sin(a), z)); UV.append((0.5 + rq * math.cos(a) / (2 * e), 0.5 + rq * math.sin(a) / (2 * e)))
        for j in range(NS):         # rolled edge going down into the cheese
            a = j / NS * TAU; rq = 1.035 * rad_n[j]
            V.append((rq * pr * math.cos(a), rq * pr * math.sin(a), -0.002 + 0.016 * rim_h[j])); UV.append((0.5 + 1.03 * math.cos(a) / (2 * e), 0.5 + 1.03 * math.sin(a) / (2 * e)))
        for j in range(NS):
            a = j / NS * TAU; rq = 1.04 * rad_n[j]
            V.append((rq * pr * math.cos(a), rq * pr * math.sin(a), -0.02)); UV.append((0.5 + 1.05 * math.cos(a) / (2 * e), 0.5 + 1.05 * math.sin(a) / (2 * e)))
        F = [(0, 1 + j, 1 + (j + 1) % NS) for j in range(NS)]
        for i in range(NR + 1):
            for j in range(NS):
                a0 = 1 + i * NS; a1 = 1 + (i + 1) * NS; j2 = (j + 1) % NS
                F.append((a0 + j, a1 + j, a1 + j2, a0 + j2))
        V = np.array(V)
        cr, sr = math.cos(rot), math.sin(rot)
        V = np.stack([V[:, 0] * cr - V[:, 1] * sr + px0, V[:, 0] * sr + V[:, 1] * cr + py0, V[:, 2]], -1)
        mk('pepperoni_%02d' % k, V, F, UV, M)
    log('pepperoni built')


# ================================================================ basil
def build_basil():
    N = 512 if FAST else 1024
    W2 = N // 2
    u = (np.arange(W2) + 0.5) / W2; v = (np.arange(N) + 0.5) / N
    U, Vv = np.meshgrid(u, v)
    out_col = []; out_a = []; out_r = []; out_n = []
    for torn in (False, True):
        sd = 90 + torn
        n2 = gn((N, W2), 6, sd); n3 = gn((N, W2), 2, sd + 10); n1 = gn((N, W2), 30, sd + 20)
        half = 0.46 * np.sin(math.pi * np.clip(Vv, 0, 1) ** 0.78) ** 0.8
        half = half * (1 + 0.06 * n1 / 1.0 + 0.03 * n2 + 0.015 * n3)
        du_ = np.abs(U - 0.5)
        inside = ss(half + 0.004, half - 0.004, du_)
        if torn:
            tear = 0.62 + 0.03 * gn((1, W2), 3, 99)[0][None, :] + 0.015 * gn((1, W2), 1, 98)[0][None, :]
            inside = inside * ss(tear + 0.004, tear - 0.004, Vv)
        # veins: midrib + side veins sweeping toward the tip
        mid = ss(0.012 * (1.2 - Vv), 0.0, du_)
        sv = np.zeros_like(U)
        for k in range(9):
            v0 = 0.08 + k * 0.095
            vline = v0 + 0.55 * du_ ** 1.1
            sv = np.maximum(sv, ss(0.008, 0.0, np.abs(Vv - vline)) * ss(0.0, 0.02, du_) * ss(half * 0.95, half * 0.6, du_))
        col = mix(hx('2c4818'), hx('17300c'), ss(-1, 1.5, n1 * 0.6 + n2 * 0.4))
        col = mix(col, hx('3e6424'), np.maximum(mid, sv * 0.45))
        col = mix(col, hx('0f2008'), ss(0.4, 1.6, n1 + 0.6 * n2) * 0.85)           # oven-wilted, translucent patches
        edge = ss(half - 0.05, half, du_)
        edge = ss(half - 0.09, half, du_)
        col = mix(col, hx('3a3410'), edge * 0.75 * ss(-0.8, 0.8, n2))                # crisp, browned edges
        col = mix(col, hx('1a1408'), ss(2.0, 2.6, n3 + n2 * 0.5) * 0.8)              # tiny scorch dots
        rough = np.clip(0.42 + 0.05 * n2 + 0.2 * edge - 0.12 * ss(0.5, 1.5, n1), 0.12, 1)
        pucker = (np.sin(Vv * 37 + 2 * n2) * np.sin(du_ * 31 + n2) * 0.5) * 0.6 + 0.4 * n2 / 3
        hgt = 0.0012 * pucker - 0.0008 * np.maximum(mid, sv) + 0.0003 * n3
        out_col.append(col); out_a.append(inside); out_r.append(rough); out_n.append(h2n(hgt, 1.0 / W2, 1.0 / N, 1.5))
    col = np.concatenate(out_col, 1); a = np.concatenate(out_a, 1)
    ci = image('basil_col', np.concatenate([col, a[..., None]], -1))
    M = pmat('m_basil', img=ci, alpha=True, ormimg=image('basil_orm', orm(np.concatenate(out_r, 1)), True),
             nimg=image('basil_nrm', np.concatenate(out_n, 1), True), sss=0.2, sss_r=(0.4, 1.0, 0.3), sss_s=0.01, coat=0.08, coat_r=0.2)
    NU, NV = 9, 16
    for k, (x0, y0, L, rot, torn) in enumerate(LEAVES):
        Wd = L * 0.6
        V = []; UV = []
        for i in range(NV + 1):
            vv = i / NV
            for j in range(NU + 1):
                uu = j / NU; q = (uu - 0.5) * 2
                z = 0.005 + 0.02 * abs(q) ** 1.6 * math.sin(math.pi * min(vv, 1)) ** 0.5 + 0.004 * math.sin(math.pi * vv)
                V.append(((uu - 0.5) * Wd, (vv - 0.5) * L, z)); UV.append((uu * 0.5 + (0.5 if torn else 0), vv))
        V = np.array(V); cr, sr = math.cos(rot), math.sin(rot)
        V = np.stack([V[:, 0] * cr - V[:, 1] * sr + x0, V[:, 0] * sr + V[:, 1] * cr + y0, V[:, 2]], -1)
        mk('basil_%d' % k, V, grid_faces(NV + 1, NU + 1), UV, M)
    log('basil built')


# ================================================================ tray + stand
def build_tray():
    N = 1024; e = 7.0; px = 2 * e / N
    c = (np.arange(N) + 0.5) * px - e; X, Y = np.meshgrid(c, c); R = np.hypot(X, Y); A = np.arctan2(Y, X)
    n1 = gn((N, N), 40, 101); n2 = gn((N, N), 8, 102); n3 = gn((N, N), 1.5, 103)
    col = mix(hx('2c2a27'), hx('17130f'), ss(-0.5, 1.5, n1 * 0.7 + n2 * 0.3))
    rough = 0.42 + 0.1 * n1 * 0.5 + 0.05 * n2
    SC = np.zeros((N, N), np.float32)
    rt = np.random.default_rng(9)
    lines = []
    for _ in range(420):
        p = rt.uniform(-6.8, 6.8, 2); a = rt.uniform(0, TAU); L = rt.uniform(0.2, 2.0)
        lines.append((p, p + L * np.array([math.cos(a), math.sin(a)])))
    for ca in CUTS:                       # cutter marks run off the pizza onto the tray
        for _ in range(3):
            a = ca + rt.uniform(-0.02, 0.02); t = np.array([math.cos(a), math.sin(a)])
            lines.append((t * 6.0, t * rt.uniform(6.6, 6.9)))
    for p0, p1 in lines:
        cx, cy = (p0 + p1) / 2; half = np.linalg.norm(p1 - p0) / 2 + 0.02
        st = stamp_iter((N, N), (cx + e) / px, (cy + e) / px, half / px)
        if not st: continue
        sy, sx, dx, dy = st
        P = np.stack([dx * px + cx, dy * px + cy], -1); d = p1 - p0
        tt = np.clip(((P - p0) @ d) / (d @ d), 0, 1)
        dist = np.linalg.norm(P - (p0 + tt[..., None] * d), axis=-1)
        SC[sy, sx] = np.maximum(SC[sy, sx], ss(px * 0.9, 0, dist) * rt.uniform(0.3, 1.0))
    col = mix(col, hx('6a655c'), SC * 0.6); rough = rough - 0.15 * SC
    dust = ss(2.5, 3.0, gn((N, N), 1.2, 104)) * ss(6.0, 6.35, R) * ss(6.95, 6.6, R)
    crumbs = ss(2.9, 3.3, gn((N, N), 2.0, 105)) * ss(6.1, 6.4, R) * ss(6.9, 6.6, R)
    col = mix(col, hx('e8dcc0'), dust * 0.8); col = mix(col, hx('b07a3a'), crumbs)
    metal = 1 - np.maximum(dust, crumbs)
    rough = np.clip(np.maximum(rough, np.maximum(dust, crumbs) * 0.8), 0.15, 1)
    hgt = 0.0004 * n3 - 0.0006 * SC + 0.0015 * crumbs
    nrm = h2n(hgt, px, px, 1.0)
    M = pmat('m_tray', img=image('tray_col', col), ormimg=image('tray_orm', orm(rough, metal), True), nimg=image('tray_nrm', nrm, True), metal=1)
    prof = [(0, -0.218), (6.5, -0.218), (6.72, -0.205), (6.84, -0.15), (6.9, -0.08), (6.95, -0.06), (6.99, -0.075),
            (6.98, -0.12), (6.86, -0.24), (6.6, -0.262), (0, -0.262)]
    prof = chaikin(prof, 1)[::-1]
    lathe(prof, 96, 'tray', M, uvfn=lambda x, y, a, s: ((x + e) / (2 * e), (y + e) / (2 * e)))
    # chrome wire stand: ring under the tray + 3 legs splaying to feet on the cloth
    CH = pmat('m_chrome', '#d8d8d8'[1:], rough=0.12, metal=1)
    V = []; F = []
    def add(vv, ff):
        o = len(V); V.extend(list(vv)); F.extend([tuple(i + o for i in f) for f in ff])
    ringp = [(4.3 * math.cos(a), 4.3 * math.sin(a), -0.33) for a in np.linspace(0, TAU, 65)]
    add(*tube(ringp, 0.075, 8, cap=False))
    ringp2 = [(2.4 * math.cos(a), 2.4 * math.sin(a), -0.33) for a in np.linspace(0, TAU, 41)]
    add(*tube(ringp2, 0.06, 8, cap=False))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        d = np.array([math.cos(a), math.sin(a), 0])
        ctrl = [d * 2.4 + [0, 0, -0.33], d * 4.3 + [0, 0, -0.33], d * 5.0 + [0, 0, -0.6], d * 5.35 + [0, 0, -1.8],
                d * 5.7 + [0, 0, TZ + 0.5], d * 6.3 + [0, 0, TZ + 0.09], d * 6.9 + [0, 0, TZ + 0.09]]
        pts = chaikin(np.array(ctrl), 3)
        add(*tube(pts, 0.085, 8))
        foot = [d * 6.25 + [0, 0, TZ + 0.07], d * 7.1 + [0, 0, TZ + 0.07]]
        add(*tube(np.linspace(foot[0], foot[1], 6), 0.14, 10))
    mk('stand', V, F, None, CH)
    # rubber feet
    log('tray built')


# ================================================================ tablecloth (gingham with real draped folds)
HX, HY, DROP = 15.0, 13.0, 5.5
def build_cloth():
    T = 512 if FAST else 1024; th = 8 if not FAST else 4; tile = 1.5
    i = np.arange(T) // th; f = (np.arange(T) % th + 0.5) / th
    nth = T // th; chk = nth // 2
    red = ((i // chk) % 2 == 0)
    I, J = np.meshgrid(i, i); FX, FY = np.meshgrid(f, f)
    top = (I + J) % 2 == 0                       # warp (vertical thread) on top
    RED = hx('b3161b'); WHT = hx('f2ede3')
    rt = np.random.default_rng(3)
    slub_c = 1 + 0.05 * rt.standard_normal(nth); slub_r = 1 + 0.05 * rt.standard_normal(nth)
    warpcol = np.where(red[:, None], RED, WHT) * slub_c[i][:, None]
    weftcol = np.where(red[:, None], RED, WHT) * slub_r[i][:, None]
    col = np.where(top[..., None], warpcol[None, :, :], weftcol[:, None, :])
    hw = np.sin(math.pi * FX) ** 0.7 * (0.75 + 0.25 * np.sin(math.pi * FY))
    hf = np.sin(math.pi * FY) ** 0.7 * (0.75 + 0.25 * np.sin(math.pi * FX))
    h = np.where(top, hw, hf)
    fib = gn((T, T), 0.8, 111)
    col = col * (0.8 + 0.2 * h[..., None]) * (1 + 0.025 * fib[..., None])
    rough = np.clip(0.82 + 0.05 * fib, 0, 1)
    nrm = h2n(h * 0.0012 + 0.0001 * fib, tile / T, tile / T, 1.0)
    M = pmat('m_cloth', img=image('cloth_col', col), ormimg=image('cloth_orm', orm(rough), True), nimg=image('cloth_nrm', nrm, True),
             sheen=0.6, sheen_r=0.4, sss=0.08, sss_r=(1, 0.4, 0.3), sss_s=0.02)
    def axis(H):
        inner = np.linspace(-H + 1.6, H - 1.6, int((2 * H - 3.2) / 1.4) + 1)
        edge = np.linspace(H - 1.6, H + DROP, int((1.6 + DROP) / 0.24) + 1)[1:]
        return np.r_[-edge[::-1], inner, edge]
    xs, ys = axis(HX), axis(HY)
    A, B = np.meshgrid(xs, ys)
    qx = np.clip(A, -HX, HX); qy = np.clip(B, -HY, HY)
    ox, oy = A - qx, B - qy; d = np.hypot(ox, oy) + 1e-9; dx, dy = ox / d, oy / d
    # perimeter coordinate (continuous through corners)
    Rc = 1.2; a2 = np.arctan2(dy, dx) % TAU; hp = math.pi / 2
    ex, ey = np.abs(ox) > 1e-6, np.abs(oy) > 1e-6
    b1 = 2 * HY; b2 = b1 + Rc * hp + 2 * HX; b3 = b2 + Rc * hp + 2 * HY; b4 = b3 + Rc * hp + 2 * HX
    s = np.select([ex & ey & (ox > 0) & (oy > 0), ex & ey & (ox < 0) & (oy > 0), ex & ey & (ox < 0) & (oy < 0), ex & ey,
                   ex & (ox > 0), ey & (oy > 0), ex & (ox < 0), ey],
                  [b1 + Rc * a2, b2 + Rc * (a2 - hp), b3 + Rc * (a2 - 2 * hp), b4 + Rc * (a2 - 3 * hp),
                   qy + HY, b1 + Rc * hp + (HX - qx), b2 + Rc * hp + (HY - qy), b3 + Rc * hp + (qx + HX)], 0.0)
    Ptot = b4 + Rc * hp
    rr = 0.3
    phi = np.minimum(d / rr, math.pi / 2)
    hang = np.maximum(d - rr * math.pi / 2, 0)
    rc = np.random.default_rng(12)
    fold = sum(np.sin(s * TAU * round(Ptot / wl) / Ptot + rc.uniform(0, TAU)) * amp for wl, amp in ((2.6, 1.0), (1.55, 0.55), (0.9, 0.25)))
    corner = (np.abs(ox) > 0.2) & (np.abs(oy) > 0.2)
    amp = 0.32 * ss(0.0, 3.5, hang) * (1 + 0.8 * corner)
    out = rr * np.sin(phi) + amp * (1 + fold / 1.8) + 0.15 * ss(0, 4, hang)
    Xc = qx + dx * out; Yc = qy + dy * out
    Zc = TZ - rr * (1 - np.cos(phi)) - hang
    flat = d < 1e-6
    wr = 0.02 * gn((len(ys), len(xs)), 2.0, 13)
    crease = 0.012 * (np.exp(-(A / 0.08) ** 2) + np.exp(-(B / 0.08) ** 2) + np.exp(-((np.abs(A) - HX / 2) / 0.08) ** 2))
    Zc = np.where(flat, TZ + wr + crease - 0.02, Zc)
    Xc = np.where(flat, A, Xc); Yc = np.where(flat, B, Yc)
    V = np.stack([Xc, Yc, Zc], -1).reshape(-1, 3)
    UV = np.stack([A / tile, B / tile], -1).reshape(-1, 2)
    mk('tablecloth', V, grid_faces(len(ys), len(xs)), UV, M)
    log('cloth built')


# ================================================================ props
GLASSY = []
def glass_mat(name, tintc=(0.96, 1.0, 0.98), rough=0.02):
    m = pmat(name, rough=rough, trans=1.0, ior=1.5, spec=0.5)
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*tintc, 1)
    return m

def straw_tex():
    W, H = 512, 1024
    u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H; U, Vv = np.meshgrid(u, v)
    n1 = gn((H, W), (40, 1.2), 121); n2 = gn((H, W), 3, 122)
    strands = np.sin(U * TAU * 64 + 1.5 * n1) * 0.5 + 0.5
    bands = (np.floor(Vv * 22) % 2)
    weave = np.where(bands > 0, np.sin(U * TAU * 32) * 0.5 + 0.5, strands)
    col = mix(hx('c9a25a'), hx('8a6a2e'), ss(0.2, 1.0, 1 - weave) * 0.6 + 0.2 * ss(-1, 1, n2))
    col = mix(col, hx('e0c487'), ss(1.2, 2.0, n1) * 0.4)
    hgt = weave * 0.6 + 0.1 * n2
    return image('straw_col', col), image('straw_nrm', h2n(hgt, 1.0 / 128, 1.0 / 256, 1.0), True)

def grain_tex(name, palette, seed, size=512, flakes=False):
    N = size; rg = np.random.default_rng(seed)
    col = np.tile(hx(palette[0]), (N, N, 1)).astype(np.float32); hgt = np.zeros((N, N), np.float32)
    n = gn((N, N), 1.0, seed)
    for _ in range(2600 if flakes else 4000):
        x, y = rg.uniform(0, N, 2); r = rg.uniform(2.5, 7 if flakes else 4.5)
        cc = hx(palette[rg.integers(len(palette))]) * rg.uniform(0.85, 1.1)
        st = stamp_iter((N, N), x, y, r * (2.2 if flakes else 1.3))
        if not st: continue
        sy, sx, dx, dy = st
        if flakes:
            a = rg.uniform(0, math.pi); ca, sa = math.cos(a), math.sin(a)
            d = np.hypot((dx * ca + dy * sa) / 2.0, (-dx * sa + dy * ca) / 0.9) / r
        else: d = np.hypot(dx, dy) / r
        msk = ss(1.0, 0.7, d + 0.2 * n[sy, sx])
        col[sy, sx] = mix(col[sy, sx], cc, msk); hgt[sy, sx] = np.maximum(hgt[sy, sx], msk * (1 - d * 0.5))
    return image(name + '_col', col), image(name + '_nrm', h2n(hgt, 0.4, 0.4, 1.0), True)

def build_props():
    # ---- chianti fiasco candle (back left)
    bx, by = -7.6, 9.6; BS = 0.8
    before = set(bpy.data.objects)
    GL = glass_mat('m_bottle', (0.18, 0.42, 0.22), 0.04)
    prof = [(0, 0.02), (1.25, 0.02), (1.75, 0.18), (2.0, 0.7), (2.04, 1.3), (1.92, 2.1), (1.55, 2.85), (1.0, 3.45), (0.62, 3.95),
            (0.5, 4.5), (0.47, 5.9), (0.53, 6.05), (0.5, 6.25), (0.42, 6.3)]
    o = lathe(chaikin(prof, 1), 36, 'bottle', GL, z0=TZ, xy=(bx, by))
    so = o.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.06; so.offset = -1
    sc, sn = straw_tex()
    STR = pmat('m_straw', img=sc, nimg=sn, nstr=1.2, rough=0.75, sheen=0.4, sss=0.1, sss_s=0.01)
    sprof = [(0, -0.0), (1.3, 0.0), (1.82, 0.16), (2.08, 0.7), (2.12, 1.3), (2.0, 2.1), (1.72, 2.65)]
    o = lathe(chaikin(sprof, 1), 48, 'straw', STR, z0=TZ, xy=(bx, by))
    me = o.data; rs = np.random.default_rng(44)
    zs = np.array([v.co.z for v in me.vertices]); ztop = zs.max()
    for v in me.vertices:
        if v.co.z > ztop - 0.05:
            a = math.atan2(v.co.y - by, v.co.x - bx); v.co.z -= 0.12 * (1 + math.sin(a * 23)) * rs.uniform(0.4, 1.0)
    bandp = [(bx + 1.95 * math.cos(a), by + 1.95 * math.sin(a), TZ + 2.3) for a in np.linspace(0, TAU, 49)]
    V, F = tube(bandp, 0.09, 8, cap=False); mk('straw_band', V, F, None, STR)
    # candle + wax drips
    WAX = pmat('m_wax', 'f2e8d0', rough=0.35, sss=0.6, sss_r=(1.0, 0.8, 0.5), sss_s=0.15)
    WAXR = pmat('m_wax_red', 'a4161a', rough=0.35, sss=0.5, sss_r=(1.0, 0.3, 0.2), sss_s=0.12)
    WAXG = pmat('m_wax_green', '2e6a3a', rough=0.35, sss=0.5, sss_r=(0.4, 1.0, 0.4), sss_s=0.12)
    cprof = [(0, TZ + 7.35), (0.18, TZ + 7.38), (0.33, TZ + 7.5), (0.36, TZ + 7.45), (0.37, TZ + 6.1), (0, TZ + 6.1)]
    lathe(chaikin(cprof, 2)[::-1], 32, 'candle', WAX, xy=(bx, by))
    rd = np.random.default_rng(66)
    for k in range(16):
        a = rd.uniform(0, TAU); mat_ = [WAX, WAX, WAXR, WAXG][k % 4]
        L = rd.uniform(0.6, 3.6 if mat_ is not WAX else 2.2)
        z0 = TZ + (7.45 if mat_ is WAX else 6.25); zz = np.linspace(z0, z0 - L, 14)
        rad_neck = np.interp(zz - TZ, [3.95, 4.5, 5.9, 6.3, 7.5], [0.62, 0.5, 0.47, 0.5, 0.37])
        aa = a + 0.08 * np.sin(np.linspace(0, 3, 14) + k)
        thick = np.linspace(0.07, 0.11, 14) * rd.uniform(0.7, 1.3); thick[-1] *= 1.5
        pts = np.stack([bx + (rad_neck + thick * 0.5) * np.cos(aa), by + (rad_neck + thick * 0.5) * np.sin(aa), zz], -1)
        V, F = tube(pts, thick, 8); mk('drip_%d' % k, V, F, None, mat_)
    FL = pmat('m_flame', 'ffb040', emit='ffa030', emit_s=60.0)
    fprof = [(0, TZ + 7.52), (0.1, TZ + 7.6), (0.14, TZ + 7.75), (0.1, TZ + 7.95), (0.04, TZ + 8.15), (0, TZ + 8.25)]
    lathe(fprof, 16, 'flame', FL, xy=(bx, by), coll=BG)
    Mb = Matrix.Translation((bx, by, TZ)) @ Matrix.Scale(BS, 4) @ Matrix.Translation((-bx, -by, -TZ))
    for o in set(bpy.data.objects) - before: o.data.transform(Mb)
    CANDLE_POS = tuple(Mb @ Vector((bx, by, TZ + 7.85)))
    # ---- wine glass (back right)
    gx, gy = 8.8, 8.6
    GLS = glass_mat('m_glass')
    gp = [(0, 0.0), (1.15, 0.0), (1.2, 0.04), (0.6, 0.12), (0.16, 0.35), (0.11, 0.8), (0.11, 2.2), (0.3, 2.45), (0.9, 2.75),
          (1.22, 3.4), (1.28, 4.2), (1.15, 5.2), (1.02, 5.95)]
    o = lathe(chaikin(gp, 1), 36, 'wine_glass', GLS, z0=TZ, xy=(gx, gy))
    so = o.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.04; so.offset = -1
    WINE = pmat('m_wine', rough=0.0, trans=1.0, ior=1.34)
    WINE.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.012, 0.03, 1)
    wp = [(0, 2.53), (0.3, 2.53), (0.85, 2.8), (1.16, 3.4), (1.21, 3.75), (1.2, 3.78), (0, 3.78)]
    lathe(chaikin(wp, 1), 36, 'wine', WINE, z0=TZ, xy=(gx, gy))
    # ---- shakers (left side): glass jar + chrome perforated cap, parmesan / chili flakes
    def shaker(x, y, name, fill_col, fill_n, fill_h):
        GJ = glass_mat('m_jar_' + name)
        jp = [(0, 0.0), (0.88, 0.0), (0.92, 0.05), (0.92, 2.85), (0.84, 2.95), (0.84, 3.2)]
        o = lathe(chaikin(jp, 1), 32, 'jar_' + name, GJ, z0=TZ, xy=(x, y))
        so = o.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.07; so.offset = -1
        FM = pmat('m_fill_' + name, img=fill_col, nimg=fill_n, nstr=1.5, rough=0.8, sss=0.15 if name == 'parm' else 0.05, sss_s=0.01)
        fp = [(0, 0.28), (0.8, 0.28), (0.8, fill_h), (0.5, fill_h + 0.12), (0, fill_h + 0.2)]
        lathe(fp, 32, 'fill_' + name, FM, z0=TZ, xy=(x, y), uvfn=lambda xx, yy, a, s: (a * 4, s * 3))
        N = 512; u = (np.arange(N) + 0.5) / N; U, Vv = np.meshgrid(u, u)
        holes = np.zeros((N, N), np.float32)
        for rr_, cnt in ((0.0, 1), (0.12, 6), (0.24, 12), (0.36, 18)):
            for k in range(cnt):
                a = k / cnt * TAU
                holes = np.maximum(holes, ss(0.022, 0.014, np.hypot(U - 0.5 - rr_ * math.cos(a), Vv - 0.5 - rr_ * math.sin(a))))
        ccol = mix(np.tile(hx('d8d8d8'), (N, N, 1)), hx('101010'), holes)
        CAP = pmat('m_cap_' + name, img=image('cap_col_' + name, ccol), ormimg=image('cap_orm_' + name, orm(0.14 + 0.8 * holes, 1 - holes), True),
                   nimg=image('cap_nrm_' + name, h2n(-holes * 0.01, 1 / N, 1 / N, 1.0), True), metal=1)
        cp = [(0, 4.05), (0.4, 4.02), (0.75, 3.85), (0.93, 3.55), (0.96, 3.2), (0.93, 3.12), (0.86, 3.12)]
        lathe(chaikin(cp, 1)[::-1], 32, 'cap_' + name, CAP, z0=TZ, xy=(x, y), uvfn=lambda xx, yy, a, s: (0.5 + (xx) / 2.1, 0.5 + (yy) / 2.1))
    pc, pn = grain_tex('parm', ['eadbb0', 'f6ecc8', 'd2bc84', 'fbf3dc'], 131)
    shaker(-10.6, 1.4, 'parm', pc, pn, 2.1)
    cc, cn = grain_tex('chili', ['7a160a', 'a8260e', 'e0a83a', '5a1006', 'c03a12'], 132, flakes=True)
    shaker(-9.4, -2.2, 'chili', cc, cn, 1.7)
    # ---- pizza cutter (right, lying on the cloth)
    STEEL = pmat('m_steel', 'c8c8c6', rough=0.22, metal=1)
    N = 512; u = (np.arange(N) + 0.5) / N; U, Vv = np.meshgrid(u, u); Rw = np.hypot(U - 0.5, Vv - 0.5) * 2; Aw = np.arctan2(Vv - 0.5, U - 0.5)
    circ = np.sin(Rw * 900 + 3 * gn((N, N), 20, 142)) * 0.5 + 0.5
    smear = ss(0.3, 0.9, gn((N, N), 10, 143) * 0.6 + 0.8) * ss(0.78, 0.92, Rw) * ss(0.3, 0.7, np.cos(Aw - 0.8))
    smear = np.maximum(smear, ss(1.6, 2.2, gn((N, N), 4, 144)) * ss(0.6, 0.9, Rw))
    wcol = mix(np.tile(hx('c9c9c6'), (N, N, 1)) * (0.92 + 0.08 * circ[..., None]), hx('8a1e0c'), smear * 0.85)
    wrough = 0.18 + 0.08 * circ + 0.2 * smear
    WH = pmat('m_wheel', img=image('wheel_col', wcol), ormimg=image('wheel_orm', orm(wrough, 1 - smear), True), metal=1)
    HAND = pmat('m_handle', '1c1a19', rough=0.55, coat=0.2, coat_r=0.3)
    parts = []
    wp_ = [(0, 0.04), (1.35, 0.03), (1.5, 0.0), (1.35, -0.03), (0, -0.04)]
    w = lathe(wp_[::-1], 64, 'cutter_wheel', WH, uvfn=lambda xx, yy, a, s: (0.5 + xx / 3.0, 0.5 + yy / 3.0)); parts.append(w)
    hub = lathe([(0, 0.11), (0.28, 0.1), (0.3, 0.0), (0.28, -0.1), (0, -0.11)][::-1], 24, 'cutter_hub', STEEL); parts.append(hub)
    V, F = tube([(0, 0.13, 0.0), (-0.9, 0.16, 0.0), (-1.9, 0.12, 0.0), (-2.2, 0.0, 0.0)], 0.07, 8); parts.append(mk('cutter_fork', V, F, None, STEEL))
    V, F = tube([(0, -0.13, 0.0), (-0.9, -0.16, 0.0), (-1.9, -0.12, 0.0), (-2.2, 0.0, 0.0)], 0.07, 8); parts.append(mk('cutter_fork2', V, F, None, STEEL))
    hp = np.array([(-2.2, 0, 0), (-2.6, 0, 0), (-3.4, 0, 0), (-4.6, 0, 0), (-5.6, 0, 0), (-5.9, 0, 0)])
    V, F = tube(hp, [0.16, 0.24, 0.3, 0.33, 0.31, 0.2], 16); parts.append(mk('cutter_handle', V, F, None, HAND))
    for p in parts: p.data.transform(Matrix.Rotation(math.radians(6), 4, 'X'))
    for p in parts:
        p.data.transform(Matrix.Rotation(math.radians(115), 4, 'Z')); p.data.transform(Matrix.Translation((9.6, -1.6, TZ + 0.34)))
    # ---- napkins (right, folded linen)
    Tn = 256; f_ = (np.arange(Tn) % 4 + 0.5) / 4; I_ = np.arange(Tn) // 4
    FXn, FYn = np.meshgrid(f_, f_); In, Jn = np.meshgrid(I_, I_)
    hn = np.where((In + Jn) % 2 == 0, np.sin(math.pi * FXn), np.sin(math.pi * FYn)) + 0.3 * gn((Tn, Tn), 0.8, 151)
    NAP = pmat('m_napkin', 'ece5d6', rough=0.85, sheen=0.7, sss=0.12, sss_s=0.03, nimg=image('napkin_nrm', h2n(hn * 0.001, 0.25 / Tn, 0.25 / Tn, 1.0), True),
               img=image('napkin_col', np.tile(hx('ece5d6'), (Tn, Tn, 1)) * (0.93 + 0.07 * hn[..., None] / 1.3)))
    for k, (cx, cy, rot, z0) in enumerate(((10.6, 4.4, 0.35, 0.0), (10.45, 4.25, 0.12, 0.16))):
        n = 18; V = []
        for i in range(n + 1):
            for j in range(n + 1):
                x = (j / n - 0.5) * 4.4; y = (i / n - 0.5) * 4.4
                V.append((x, y, 0))
        V = np.array(V); rn = np.random.default_rng(150 + k)
        e_ = np.maximum(np.abs(V[:, 0]), np.abs(V[:, 1])) / 2.2
        V[:, 2] = 0.15 - 0.09 * ss(0.8, 1.0, e_) + 0.03 * np.sin(V[:, 0] * 2.1 + k) * np.sin(V[:, 1] * 1.7) + 0.05 * np.exp(-(V[:, 0] / 0.15) ** 2) - 0.03 * np.exp(-((V[:, 1] - 0.4) / 0.1) ** 2)
        Vb = V.copy(); Vb[:, 2] = 0.0
        nv = len(V); F = grid_faces(n + 1, n + 1)
        Fb = [tuple(i + nv for i in f[::-1]) for f in F]
        # side skirt
        ring = [i * (n + 1) for i in range(n + 1)] + [n * (n + 1) + j for j in range(1, n + 1)] + [i * (n + 1) + n for i in range(n - 1, -1, -1)] + [j for j in range(n - 1, 0, -1)]
        Fs = [(ring[q], ring[(q + 1) % len(ring)], ring[(q + 1) % len(ring)] + nv, ring[q] + nv) for q in range(len(ring))]
        VV = np.vstack([V, Vb]); cr, sr = math.cos(rot), math.sin(rot)
        VV = np.stack([VV[:, 0] * cr - VV[:, 1] * sr + cx, VV[:, 0] * sr + VV[:, 1] * cr + cy, VV[:, 2] + TZ + 0.02 + z0], -1)
        o = mk('napkin_%d' % k, VV, F + Fb + Fs, np.stack([VV[:, 0] / 0.25, VV[:, 1] / 0.25], -1), NAP)
        me = o.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    # ---- crumbs + spilled chili flakes on the cloth
    CR = bpy.data.materials['m_crust']
    rc = np.random.default_rng(160)
    V = []; F = []
    for k in range(40):
        a = rc.uniform(0, TAU); r = rc.uniform(7.2, 10.5); x, y = r * math.cos(a), r * math.sin(a)
        if y > 7: continue
        s = rc.uniform(0.06, 0.18)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s)
        for v in bm.verts: v.co = Vector((v.co.x * rc.uniform(0.7, 1.4), v.co.y * rc.uniform(0.7, 1.3), v.co.z * 0.6 + s * 0.45))
        o_ = len(V); V += [(v.co.x + x, v.co.y + y, v.co.z + TZ) for v in bm.verts]; F += [tuple(o_ + v.index for v in f.verts) for f in bm.faces]; bm.free()
    UVc = [(rc.uniform(0, 1), rc.uniform(0.2, 0.4)) for _ in V]
    mk('crumbs', V, F, UVc, CR)
    FLK = pmat('m_flake', 'a8260e', rough=0.6)
    V = []; F = []
    for k in range(45):
        x = -9.4 + rc.normal(0, 0.9) + 1.0; y = -2.2 + rc.normal(0, 1.0) - 0.6; a = rc.uniform(0, TAU); s = rc.uniform(0.05, 0.11)
        o_ = len(V); ca, sa = math.cos(a), math.sin(a)
        for px_, py_ in ((-s, -s * 0.5), (s, -s * 0.4), (s * 0.8, s * 0.5), (-s * 0.7, s * 0.6)):
            V.append((x + px_ * ca - py_ * sa, y + px_ * sa + py_ * ca, TZ + 0.012))
        F.append((o_, o_ + 1, o_ + 2, o_ + 3))
    mk('chili_flakes', V, F, None, FLK)
    log('props built')
    return CANDLE_POS


# ================================================================ background room (render only)
def build_room():
    FLR = bpy.data.materials.new('m_floor'); FLR.use_nodes = True
    b = FLR.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.05, 0.025, 0.012, 1); b.inputs['Roughness'].default_value = 0.4
    V = [(-200, -200, TZ - 23), (200, -200, TZ - 23), (200, 200, TZ - 23), (-200, 200, TZ - 23)]
    mk('floor', V, [(0, 1, 2, 3)], None, FLR, coll=BG)
    WAL = bpy.data.materials.new('m_wall'); WAL.use_nodes = True
    b = WAL.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.12, 0.05, 0.025, 1); b.inputs['Roughness'].default_value = 0.8
    V = [(-200, 75, TZ - 23), (200, 75, TZ - 23), (200, 75, 80), (-200, 75, 80)]
    mk('wall', V, [(0, 1, 2, 3)], None, WAL, coll=BG)
    # warm string lights / sconces -> bokeh
    LB = pmat('m_bulb', 'ffc070', emit='ffb060', emit_s=14.0)
    rb_ = np.random.default_rng(170)
    for k in range(36):
        x = -90 + k * 5.0 + rb_.uniform(-0.8, 0.8); z = -6 + 4 * math.cos(k * 0.35) + rb_.uniform(-0.5, 0.5)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.5, location=(x, 72, z))
        o = bpy.context.object; o.data.materials.append(LB)
        for c_ in o.users_collection: c_.objects.unlink(o)
        BG.objects.link(o)
    for x in (-40, -12, 22, 48):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.6, location=(x, 73, -12))
        o = bpy.context.object; o.data.materials.append(pmat('m_sconce', 'ffb060', emit='ff9a40', emit_s=12.0))
        pl = bpy.data.objects.new('wl', bpy.data.lights.new('wl', 'POINT')); BG.objects.link(pl); pl.location = (x, 70.5, -11); pl.data.energy = 9000; pl.data.color = (1, 0.6, 0.3)
        for c_ in o.users_collection: c_.objects.unlink(o)
        BG.objects.link(o)


# ================================================================ Poly Haven CC0 surroundings (render only, not exported)
PH = SCR + '/ph'
def ph_import(rel, loc, rotz, scale=31.0):
    f = os.path.join(PH, rel)
    if not os.path.exists(f): log('missing', f); return
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f)
    for o in set(bpy.data.objects) - before:
        for c_ in list(o.users_collection): c_.objects.unlink(o)
        BG.objects.link(o)
        if o.parent is None:
            o.location = loc; o.rotation_mode = 'XYZ'; o.rotation_euler = (0, 0, rotz); o.scale = (scale,) * 3

def build_surroundings():
    FLOOR = TZ - 23.0
    ph_import('dining_chair_02/dining_chair_02_1k.gltf', (-8.0, HY + 7.5, FLOOR), 0.15)
    ph_import('dining_chair_02/dining_chair_02_1k.gltf', (10.0, HY + 8.0, FLOOR), -0.2)
    ph_import('lemon/lemon_1k.gltf', (-11.8, 5.6, TZ + 1.6), 0.7)

# ================================================================ build
TOPD = build_pizza_top()
build_crust()
build_pepperoni(TOPD)
build_basil()
build_tray()
build_cloth()
CANDLE = build_props()
build_room()
build_surroundings()

def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); n += len(me.loop_triangles); o.evaluated_get(dg).to_mesh_clear()
    return n
STAGE_TRIS = tri_count(STAGE.objects)
if 'dump' in sys.argv:
    os.makedirs(os.path.join(OUT, 'tex'), exist_ok=True)
    for im in IMGS:
        im.filepath_raw = os.path.join(OUT, 'tex', im.name + '.png'); im.file_format = 'PNG'; im.save()
for o in STAGE.objects:
    if o.name.startswith(('bottle', 'wine', 'jar_')): o.visible_shadow = False
if 'tris' in sys.argv:
    import collections; agg = collections.Counter()
    for o in STAGE.objects: agg[o.name.split('_')[0]] += tri_count([o])
    log(sorted(agg.items(), key=lambda kv: -kv[1]))
log('stage triangles:', STAGE_TRIS)

# max relief inside the flat zone
zin = []
for o in STAGE.objects:
    if o.type != 'MESH': continue
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        if math.hypot(w.x, w.y) < RFLAT and w.z > -0.1 and not o.name.startswith('crust'): zin.append(w.z)
log('relief inside r<5.3: min %.3f max %.3f' % (min(zin), max(zin)))


# ================================================================ characters (from stage_render.py)
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHAR_DIR, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots

CHARS = []
def place_chars():
    global stance
    stance = None; RIGS = []
    def sumo(f, pos, face, scale=1.65):
        global stance
        new, roots = load(f); CHARS.extend(new)
        rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
        if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
        elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
        for r in roots:
            r.location = (pos[0], pos[1], 0); r.scale = (scale,) * 3
            r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))
    A, B = FIGHTERS
    sumo('sumo2_stance.glb', A, B)
    sumo('sumo2_red.glb', B, A)
    new, gr = load('gyoji.glb'); CHARS.extend(new)
    for r in gr: r.location = (0.4, 5.0, -0.02); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
    scn.frame_set(1)
    def mmat(name, hexc, rough=0.35):
        m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value = (*lin(hexc), 1); bs.inputs['Roughness'].default_value = rough; return m
    def mask(kind, centre, fwd, up, k):
        fwd = (fwd - up * fwd.dot(up)).normalized(); right = fwd.cross(up).normalized()
        Bm = Matrix((right, fwd, up)).transposed().to_4x4(); Bm.translation = centre
        parts = []
        def put(o, loc, mat_):
            o.data.materials.append(mat_); bpy.ops.object.shade_smooth()
            o.matrix_world = Bm @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world; parts.append(o)
        def ell(loc, sc, mat_, half=False):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16); o = bpy.context.object
            if half:
                bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.05], context='VERTS'); bm.to_mesh(o.data); bm.free()
                sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.06
            o.scale = Vector(sc) * k; bpy.ops.object.transform_apply(scale=True); put(o, loc, mat_); return o
        def cone(loc, r, h, rot, mat_):
            bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r * k, depth=h * k); o = bpy.context.object
            o.rotation_euler = rot; bpy.ops.object.transform_apply(rotation=True); put(o, loc, mat_)
        def strap(mat_):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.25 * k, minor_radius=0.03 * k); o = bpy.context.object
            o.rotation_euler = (0.25, 0, 0); bpy.ops.object.transform_apply(rotation=True); put(o, (0, -0.02, 0.02), mat_)
        if kind == 'oni':
            R_ = mmat('mOni', 'c8231d'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), R_, True)
            for sd in (-1, 1):
                ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
                cone((sd * 0.11, 0.08, 0.2), 0.04, 0.18, (0, sd * 0.45, 0), mmat('mHorn', 'f2e6c8', 0.4))
            strap(R_)
        elif kind == 'hannya':
            W_ = mmat('mHannya', 'eae2c8'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
            for sd in (-1, 1):
                ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
                cone((sd * 0.11, 0.06, 0.22), 0.04, 0.22, (0, sd * 0.5, 0), mmat('mHornH', 'd8c890', 0.4))
            ell((0, 0.25, -0.12), (0.07, 0.02, 0.018), mmat('mMouth', '7a1414'))
            strap(W_)
        elif kind == 'kitsune':
            W_ = mmat('mKitsune', 'f6f2ea'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
            for sd in (-1, 1):
                ell((sd * 0.075, 0.245, 0.03), (0.045, 0.015, 0.012), mmat('mRed', 'd8262e'))
                cone((sd * 0.1, 0.06, 0.2), 0.055, 0.14, (0, sd * 0.3, 0), W_)
            cone((0, 0.3, -0.06), 0.06, 0.14, (-math.pi / 2, 0, 0), W_)
            strap(mmat('mRedS', 'd8262e'))
        return parts
    def head_frame(rig, roots):
        pb = rig.pose.bones['head']; M = rig.matrix_world @ pb.matrix
        up = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
        fwd = (roots[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
        return M.translation + up * 0.11 * roots[0].scale[0], fwd, up
    for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
        if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
    gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    mask('kitsune', Vector((0.4, 5.0, 1.52 * 1.5 - 0.02)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)


# ================================================================ lights, camera, render
def setup_light():
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    bgn = world.node_tree.nodes['Background']; bgn.inputs['Color'].default_value = (0.03, 0.017, 0.009, 1); bgn.inputs['Strength'].default_value = 1.0
    def area(name, loc, target, energy, size, color, shape='DISK'):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA')); scn.collection.objects.link(l)
        l.data.energy = energy; l.data.size = size; l.data.shape = shape; l.data.color = color; l.location = loc
        l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return l
    k = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SPOT')); scn.collection.objects.link(k)
    k.data.energy = 40000; k.data.color = (1.0, 0.8, 0.58); k.data.spot_size = math.radians(75); k.data.spot_blend = 0.75
    k.data.shadow_soft_size = 3.0; k.location = (-6, 9, 24)
    k.rotation_euler = (Vector((0.5, -0.8, 0)) - k.location).to_track_quat('-Z', 'Y').to_euler()
    area('Top', (0, -4, 22), (0, 0, 0), 3000, 12, (1.0, 0.84, 0.66))
    area('Fill', (16, -18, 9), (0, 0, 0), 2500, 16, (1.0, 0.86, 0.72))
    area('Rim', (6, 24, 9), (0, 0, 0.5), 5000, 10, (1.0, 0.88, 0.75))
    area('Back', (-17, 16, 7), (0, 0, 0), 7000, 12, (1.0, 0.82, 0.62))
    c = bpy.data.objects.new('Candle', bpy.data.lights.new('Candle', 'POINT')); scn.collection.objects.link(c)
    c.data.energy = 3000; c.data.color = (1.0, 0.55, 0.22); c.data.shadow_soft_size = 0.25; c.location = CANDLE

def render(shot):
    cam = bpy.data.objects.get('Cam')
    if not cam:
        cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.dof.use_dof = False
    if shot == 'close':
        cam.location = (3.2, -3.6, 2.2); cam.data.angle_y = math.radians(28)
        cam.rotation_euler = (Vector((0.6, 1.2, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'crust':
        cam.location = (2.5, -8.2, 1.4); cam.data.angle_y = math.radians(26)
        cam.rotation_euler = (Vector((1.2, -4.8, 0.1)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'game':
        el = math.radians(50); dist = 21
        cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
        cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
        tgt = Vector((0, 0.8, 0.4))
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (Vector((0, 0, 1.6)) - cam.location).length; cam.data.dof.aperture_fstop = 2.0
    scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'
    scn.cycles.samples = 16 if FAST else 64; scn.cycles.use_denoising = True
    scn.cycles.caustics_reflective = False; scn.cycles.caustics_refractive = False
    scn.cycles.max_bounces = 8; scn.cycles.transmission_bounces = 8; scn.cycles.glossy_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = (640, 360) if FAST else (1280, 720)
    scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Punchy'
    scn.view_settings.exposure = -0.25
    scn.render.filepath = os.path.join(OUT, 'ex_%s.png' % shot)
    log('rendering', shot); bpy.ops.render.render(write_still=True); log('wrote', scn.render.filepath)

if 'noexport' not in sys.argv:
    # export first on a copy of the images scaled to <=1024 px, then restore? simpler: export at the end
    pass

if 'norender' not in sys.argv:
    place_chars(); setup_light()
    for s in SHOTS: render(s)

if 'noexport' not in sys.argv:
    for o in CHARS:
        try: bpy.data.objects.remove(o, do_unlink=True)
        except ReferenceError: pass
    for im in IMGS:
        w, h = im.size
        if max(w, h) > 1024:
            k = 1024 / max(w, h); im.scale(max(1, int(w * k)), max(1, int(h * k)))
        im.file_format = 'PNG'; im.pack()
    bpy.ops.object.select_all(action='DESELECT')
    for o in STAGE.objects: o.select_set(True)
    bpy.context.view_layer.objects.active = STAGE.objects[0]
    glb = os.path.join(OUT, 'pizza.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_image_format='AUTO')
    log('exported', glb, '%.1f MB' % (os.path.getsize(glb) / 1e6), 'tris', STAGE_TRIS)
