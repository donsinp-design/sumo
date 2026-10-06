# BIRTHDAY CAKE stage, fully modelled: a giant buttercream layer cake (the fighting surface) with a glossy pink drip,
# piped star rosettes and a shell border, rainbow sprinkles, strawberries and cherries, lit twisted candles, and a
# wedge cut out of the rim showing the sponge / cream / jam layers; on a white porcelain cake stand on a party table
# (pink gingham cloth with draped folds, party plates with forks and the cut slice, a party hat, a gift box, confetti,
# balloons). Built entirely by script (Blender 4.2, headless).
#   python tools/blender/stage_cake.py [out_dir] [shot=game|low ...] [fast] [noexport] [norender]
# Writes <out_dir>/cake.glb (stage only: Z up, metres, origin at the cake top centre, textures <= 1024 px) and
# <out_dir>/ex_game.png / ex_low.png (with the game's masked sumos + gyoji imported from scratchpad/stage).
#
# Game contract (public/js/config.js, stages.js): ring radius 4.6, cake top radius ~5.3, top surface at Z=0 and flat
# inside the fighting area (relief <= 3 cm: the sprinkles there are half sunk, the piped ring line is 2.8 cm high).
# Everything tall (rosettes, candles, berries, the cut) lives outside r = 4.6. The buttercream detail on the top
# (turntable spatula arcs, palette-knife sweeps, pinholes) is in numpy-painted normal / roughness maps.
import bpy, bmesh, math, sys, os, time
import numpy as np
from mathutils import Vector, Matrix

SCR = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
CHAR_DIR = SCR + '/stage'
FLAGW = {'fast', 'noexport', 'norender', 'nochars', '--tris'}
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in FLAGW and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else SCR + '/cake'
os.makedirs(OUT, exist_ok=True)
SHOTS = [a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')] or ['game', 'low']
FAST = 'fast' in sys.argv
SAMPLES = int(next((a.split('=')[1] for a in sys.argv if a.startswith('samples=')), 16 if FAST else 64))
T0 = time.time()
def log(*a): print('[cake %5.1fs]' % (time.time() - T0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RING = 4.6          # fighting circle
RT = 5.3            # cake radius
RE = 0.16           # rounded top edge
RIN = RT - RE       # flat top ends here
H = 2.0             # cake height (top at 0, bottom at -H)
PZ = -H             # stand plate top
TZ = -3.7           # table (cloth) top
STAGE = bpy.data.collections.new('stage'); scn.collection.children.link(STAGE)
BG = bpy.data.collections.new('bg'); scn.collection.children.link(BG)
rng = np.random.default_rng(11)


# ================================================================ helpers
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
def lin(h): return tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in hx(h))
def ss(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def gn(shape, sig, seed, ang=None):
    """periodic gaussian-filtered white noise, std 1. sig px scalar or (sy, sx); with ang: (along, across)."""
    Hh, W = shape
    n = np.random.default_rng(seed).standard_normal((Hh, W)).astype(np.float32)
    ky = np.fft.fftfreq(Hh)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    if ang is None:
        sy, sx = (sig, sig) if np.isscalar(sig) else sig
        g = np.exp(-2 * math.pi ** 2 * ((sx * kx) ** 2 + (sy * ky) ** 2))
    else:
        sa, sb = sig; c, s = math.cos(ang), math.sin(ang)
        ka = kx * c + ky * s; kb = -kx * s + ky * c
        g = np.exp(-2 * math.pi ** 2 * ((sa * ka) ** 2 + (sb * kb) ** 2))
    o = np.fft.irfft2(np.fft.rfft2(n) * g, s=(Hh, W)).astype(np.float32)
    return o / (o.std() + 1e-9)

def blur(a, sig):
    Hh, W = a.shape[:2]
    ky = np.fft.fftfreq(Hh)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    sy, sx = (sig, sig) if np.isscalar(sig) else sig
    g = np.exp(-2 * math.pi ** 2 * ((sx * kx) ** 2 + (sy * ky) ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(Hh, W)).astype(np.float32)

def h2n(Hm, dx, dy, k=1.0):
    gy, gx = np.gradient(Hm, dy, dx)
    n = np.stack([-k * gx, -k * gy, np.ones_like(Hm)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5

IMGS = []
def image(name, arr, noncolor=False):
    arr = np.clip(arr, 0, 1).astype(np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, -1)
    Hh, W = arr.shape[:2]
    im = bpy.data.images.new(name, W, Hh, alpha=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    px = np.ones((Hh, W, 4), np.float32); px[..., :arr.shape[2]] = arr
    im.pixels.foreach_set(px.ravel()); im.update(); IMGS.append(im); return im

def orm(rough, metal=None):
    a = np.zeros(rough.shape + (3,), np.float32); a[..., 0] = 1; a[..., 1] = rough
    a[..., 2] = 0 if metal is None else metal; return a

def pmat(name, color='ffffff', img=None, rough=0.5, ormimg=None, nimg=None, nstr=1.0, metal=0.0, sss=0.0,
         sss_r=(1.0, 0.6, 0.4), sss_s=0.04, trans=0.0, ior=1.45, coat=0.0, coat_r=0.05, sheen=0.0, sheen_r=0.5,
         emit=None, emit_s=0.0, spec=0.5, bump=None):
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
        t = N.new('ShaderNodeTexImage'); t.image = img; t.location = (-600, 300); L.new(t.outputs['Color'], b.inputs['Base Color'])
    if ormimg:
        t = N.new('ShaderNodeTexImage'); t.image = ormimg; t.location = (-600, 0)
        sp = N.new('ShaderNodeSeparateColor'); sp.location = (-300, 0); L.new(t.outputs['Color'], sp.inputs['Color'])
        L.new(sp.outputs['Green'], b.inputs['Roughness']); L.new(sp.outputs['Blue'], b.inputs['Metallic'])
    if nimg:
        t = N.new('ShaderNodeTexImage'); t.image = nimg; t.location = (-600, -300)
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr; nm.location = (-300, -300)
        L.new(t.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    elif bump:   # render-only micro relief (procedural noise); the glb keeps the plain colour/roughness
        sc, st = bump
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = sc; nz.inputs['Detail'].default_value = 6
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = st; bp.inputs['Distance'].default_value = 0.02
        L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def mk(name, V, F, UV=None, mat=None, smooth=True, coll=None, fix=None):
    V = np.asarray(V, np.float64)
    me = bpy.data.meshes.new(name); me.from_pydata(V.tolist(), [], [list(map(int, f)) for f in F]); me.update()
    if UV is not None:
        UV = np.asarray(UV, np.float32)
        uvl = me.uv_layers.new(name='UVMap'); li = np.zeros(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', li)
        uvl.data.foreach_set('uv', UV[li].ravel())
    if fix is not None:   # flip faces whose normal disagrees with fix(centre) -> expected direction
        bm = bmesh.new(); bm.from_mesh(me)
        flip = [f for f in bm.faces if f.normal.dot(Vector(fix(np.array(f.calc_center_median())))) < 0]
        if flip: bmesh.ops.reverse_faces(bm, faces=flip)
        bm.to_mesh(me); bm.free()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    o = bpy.data.objects.new(name, me); (coll or STAGE).objects.link(o)
    if mat:
        for m_ in (mat if isinstance(mat, (list, tuple)) else [mat]): me.materials.append(m_)
    return o

def grid_faces(nr, nc, wrap_c=False):
    F = []; cc = nc if wrap_c else nc - 1
    for i in range(nr - 1):
        for j in range(cc):
            j2 = (j + 1) % nc; F.append((i * nc + j, i * nc + j2, (i + 1) * nc + j2, (i + 1) * nc + j))
    return F

def lathe(prof, segs, name, mat, coll=None, xy=(0, 0, 0), rfun=None, uvs=1.0, fix=None):
    """revolve (r, z) profile; rfun(r, z, a) -> (r, z) may perturb. UV u = angle*uvs, v = arclength."""
    prof = np.asarray(prof, np.float64); n = len(prof)
    Lc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))]; Lc /= max(Lc[-1], 1e-9)
    V = []; UV = []
    for i in range(n):
        for j in range(segs + 1):
            a = j / segs * TAU; r, z = prof[i]
            if rfun: r, z = rfun(r, z, a)
            V.append((xy[0] + r * math.cos(a), xy[1] + r * math.sin(a), xy[2] + z)); UV.append((j / segs * uvs, Lc[i]))
    o = mk(name, V, grid_faces(n, segs + 1), UV, mat, coll=coll, fix=fix)
    weld(o); return o

def weld(o, d=1e-5):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=d); bm.to_mesh(o.data); bm.free()

def tube(pts, rad, sides=8, cap=True, star=0.0, nstar=0, rz=None, arc=None):
    """sweep a (star) cross-section along a polyline with parallel transport. rad per point; rz squashes the
    cross-section along world z (flattened tubes). arc=(a0, a1) keeps only part of the circle (open strip)."""
    pts = np.asarray(pts, np.float64); n = len(pts); rad = np.broadcast_to(np.asarray(rad, np.float64), (n,))
    T = np.gradient(pts, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    ref = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    Nn = np.cross(T[0], ref); Nn /= np.linalg.norm(Nn)
    V = []
    ks = sides if arc is None else sides + 1
    for i in range(n):
        if i: Nn = Nn - T[i] * Nn.dot(T[i]); Nn /= np.linalg.norm(Nn) + 1e-12
        Bn = np.cross(T[i], Nn)
        for k in range(ks):
            a = k / sides * TAU if arc is None else arc[0] + (arc[1] - arc[0]) * k / sides
            f = 1 + star * math.cos(nstar * a) if nstar else 1
            off = rad[i] * f * (math.cos(a) * Nn + math.sin(a) * Bn)
            if rz is not None: off[2] *= rz
            V.append(pts[i] + off)
    F = grid_faces(n, ks, wrap_c=arc is None)
    if cap and arc is None:
        V.append(pts[0]); V.append(pts[-1]); c0, c1 = len(V) - 2, len(V) - 1
        for k in range(sides):
            F.append((c0, (k + 1) % sides, k)); F.append((c1, (n - 1) * sides + k, (n - 1) * sides + (k + 1) % sides))
    return np.array(V), F

class Merge:
    """accumulate V/F of many small parts into one mesh (one draw call; per-part transforms = instancing)."""
    def __init__(s): s.V = []; s.F = []; s.UV = []; s.n = 0
    def add(s, V, F, UV=None):
        V = np.asarray(V); s.V.append(V); s.F.extend([[i + s.n for i in f] for f in F])
        s.UV.append(np.zeros((len(V), 2)) if UV is None else np.asarray(UV)); s.n += len(V)
    def build(s, name, mat, coll=None, smooth=True, uv=False):
        if not s.V: return None
        return mk(name, np.vstack(s.V), s.F, np.vstack(s.UV) if uv else None, mat, smooth=smooth, coll=coll)

def frame(z_axis, x_hint=(1, 0, 0)):
    z = np.asarray(z_axis, np.float64); z /= np.linalg.norm(z)
    x = np.asarray(x_hint, np.float64); x = x - z * x.dot(z)
    if np.linalg.norm(x) < 1e-6: x = np.cross(z, [0, 1, 0])
    x /= np.linalg.norm(x); y = np.cross(z, x); return np.stack([x, y, z], 1)

def rotz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
def rotx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def roty(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def rprof(z):
    """cake outer radius at height z (rounded top edge)."""
    z = np.asarray(z, np.float64)
    return np.where(z > -RE, RIN + np.sqrt(np.clip(RE ** 2 - (z + RE) ** 2, 0, None)), RT)


# ================================================================ layout: the cut wedge, rosettes, candles
PHN = math.radians(-50)          # the cut faces the front-right (the low camera)
RTIP = 4.72                      # wedge tip, just outside the fighting circle
BETA = math.radians(52)          # each wall opens this much from the radial direction
P0 = np.array([RTIP * math.cos(PHN), RTIP * math.sin(PHN)])
U1 = np.array([math.cos(PHN + BETA), math.sin(PHN + BETA)])   # wall 1 (counter-clockwise side)
U2 = np.array([math.cos(PHN - BETA), math.sin(PHN - BETA)])
def s_hit(u, r): b = P0.dot(u); return -b + math.sqrt(b * b - P0.dot(P0) + r * r)
def wall_pt(u, s): return P0 + s * u
SMAX = s_hit(U1, RT)
def ang(p): return math.atan2(p[1], p[0])
def ray_wall(th, u):
    d = np.array([math.cos(th), math.sin(th)])
    A = np.array([[d[0], -u[0]], [d[1], -u[1]]])
    try: t, s = np.linalg.solve(A, P0)
    except np.linalg.LinAlgError: return 1e9
    return t if (s >= -1e-9 and t > 0) else 1e9
def rmax(th): return min(RIN, ray_wall(th, U1), ray_wall(th, U2))
def in_cut(th, r):
    """is the point (r, th) removed by the wedge?"""
    p = np.array([r * math.cos(th), r * math.sin(th)]) - P0
    n1 = np.array([-U1[1], U1[0]]); n2 = np.array([U2[1], -U2[0]])
    return p.dot(n1) < 0 and p.dot(n2) < 0 and p.dot([math.cos(PHN), math.sin(PHN)]) > 0
TH1 = ang(wall_pt(U1, s_hit(U1, RT))); TH2 = ang(wall_pt(U2, s_hit(U2, RT)))   # cut opening at the side
def wrapd(a): return (a + math.pi) % TAU - math.pi
def near_cut(th, margin): return wrapd(th - PHN) < wrapd(TH1 - PHN) + margin and wrapd(th - PHN) > wrapd(TH2 - PHN) - margin

NROS = 24; RROS = 5.0
ROS = [wrapd(math.radians(97) + k / NROS * TAU) for k in range(NROS)]
ROS = [a for a in ROS if not near_cut(a, 0.07)]
CANDLES = [wrapd(math.radians(97) + (k + 0.5) / NROS * TAU) for k in range(0, NROS, 3)]
CANDLES = [a for a in CANDLES if not near_cut(a, 0.12)]
FIGHTERS = [(-1.0, -0.15), (1.0, 0.15)]
HAT = (9.8, 1.2); GIFT = (-12.4, 3.0)
GYOJI = (0.35, 4.1)
log('rosettes', len(ROS), 'candles', len(CANDLES), 'cut opening %.1f..%.1f deg, wall %.2f m' % (math.degrees(TH2), math.degrees(TH1), SMAX))


# ================================================================ buttercream maps
TS = 1024 if FAST else 2048; TSPAN = 5.45
def build_top_maps():
    n = TS; dx = 2 * TSPAN / n
    c = (np.arange(n) + 0.5) * dx - TSPAN
    X, Y = np.meshgrid(c, c); R = np.hypot(X, Y); A = np.arctan2(Y, X)
    h = np.zeros((n, n), np.float32); rg = np.random.default_rng(21)
    # turntable smoothing: partial concentric arcs, each leaves a soft lip where the spatula edge lifted
    for k in range(70):
        rk = rg.uniform(0.2, 5.1); a0 = rg.uniform(-math.pi, math.pi); span = rg.uniform(0.5, 3.4)
        w = rg.uniform(0.012, 0.035); amp = rg.uniform(0.0008, 0.0026) * rg.choice([-1, 1])
        da = (A - a0 + math.pi) % TAU - math.pi
        fade = ss(-span / 2, -span / 2 + 0.4, da) * (1 - ss(span / 2 - 0.6, span / 2, da))
        dr = R - rk - 0.004 * np.sin(A * 3 + k)
        h += (amp * (np.exp(-(dr / w) ** 2) - 0.6 * np.exp(-((dr - 1.6 * w) / (2.2 * w)) ** 2)) * fade).astype(np.float32)
    # a few straight palette-knife sweeps (the blade lip on both sides of a slightly flattened band)
    for k in range(7):
        a = rg.uniform(0, math.pi); d = np.array([math.cos(a), math.sin(a)]); off = rg.uniform(-3.8, 3.8)
        bw = rg.uniform(0.35, 0.7); u = X * d[0] + Y * d[1]; v = -X * d[1] + Y * d[0] - off
        L0 = rg.uniform(-4, 0); L1 = L0 + rg.uniform(1.5, 4.5)
        along = ss(L0, L0 + 0.5, u) * (1 - ss(L1 - 0.8, L1, u))
        prof = 0.0016 * (np.exp(-((np.abs(v) - bw) / 0.02) ** 2)) - 0.0006 * ss(bw, bw * 0.5, np.abs(v))
        h += (prof * along).astype(np.float32)
    h += 0.0035 * gn((n, n), n / 26, 22) + 0.0006 * gn((n, n), 6, 23)
    # pinholes (air bubbles dragged open by the spatula)
    pits = np.zeros((n, n), np.float32)
    for k in range(1600 if not FAST else 500):
        px, py = rg.uniform(0, n, 2); rr = rg.uniform(0.8, 2.6) * n / 2048
        x0, x1 = int(max(px - 4 * rr - 1, 0)), int(min(px + 4 * rr + 2, n)); y0, y1 = int(max(py - 4 * rr - 1, 0)), int(min(py + 4 * rr + 2, n))
        yy, xx = np.mgrid[y0:y1, x0:x1]; d2 = ((xx + 0.5 - px) ** 2 + ((yy + 0.5 - py) * 0.7) ** 2) / rr ** 2
        pits[y0:y1, x0:x1] = np.maximum(pits[y0:y1, x0:x1], np.exp(-d2 * 1.5))
    h -= 0.0018 * pits
    nrm = h2n(h, dx, dx, 1.0)
    fine = gn((n, n), 1.5, 24)
    lip = np.clip(blur(np.abs(np.gradient(h, dx)[1]) + np.abs(np.gradient(h, dx)[0]), 2) * 18, 0, 1)
    rough = np.clip(0.26 - 0.08 * lip + 0.22 * pits + 0.03 * fine + 0.03 * gn((n, n), 60, 25), 0.15, 0.8)
    base = hx('f8e8d8'); tint = hx('f7d8dc')
    col = base + (tint - base) * np.clip(0.5 + 0.35 * gn((n, n), 140, 26), 0, 1)[..., None]
    col = col * (1 - 0.06 * pits[..., None]) * (1 + 0.012 * fine[..., None])
    col = col * (1 - 0.04 * ss(4.9, 5.3, R))[..., None]
    return col, rough, nrm

def build_side_maps():
    W, Hh = (512, 256) if FAST else (1024, 512)
    TW, TH = TAU * RT / 6, H + 0.4                     # one tile: 1/6 of the circumference
    h = 0.0012 * gn((Hh, W), (2.0, 90), 31) + 0.0015 * gn((Hh, W), (6, 220), 32) + 0.0004 * gn((Hh, W), 1.5, 33)
    rg = np.random.default_rng(34); yy = np.arange(Hh)[:, None]
    for k in range(18):   # scraper streaks: horizontal lips at the height of a nick in the scraper
        y = rg.uniform(0, Hh); w = rg.uniform(0.6, 1.8)
        h += (rg.uniform(0.0004, 0.0012) * np.exp(-((yy - y) / w) ** 2) * (0.6 + 0.4 * gn((1, W), (1, 40), 35 + k))).astype(np.float32)
    nrm = h2n(h, TW / W, TH / Hh)
    rough = np.clip(0.4 + 0.04 * gn((Hh, W), 3, 36), 0.2, 0.8)
    col = hx('fbf1ea') * (1 + 0.01 * gn((Hh, W), 2, 37))[..., None]
    return col, rough, nrm

def build_crumb_maps():
    """the cut faces: atlas, left half = wall 1, right half = wall 2. u across the wall (0 at the tip), v = height."""
    n = 512 if FAST else 1024
    zz = (np.arange(n) + 0.5) / n * H - H                   # row -> z (bottom row = -H)
    LAY = [  # (z_top, z_bottom, kind)  from the top down
        (0.0, -0.06, 'frost'), (-0.06, -0.6, 'sponge'), (-0.6, -0.71, 'cream'), (-0.71, -0.79, 'jam'),
        (-0.79, -1.3, 'sponge'), (-1.3, -1.41, 'cream'), (-1.41, -1.49, 'jam'), (-1.49, -2.0, 'sponge')]
    sponge = hx('f0c878'); crust = hx('9a5a26'); cream = hx('fff4e2'); jam = hx('b0122a'); frost = hx('fbf1ea')
    col = np.zeros((n, n, 3), np.float32); hgt = np.zeros((n, n), np.float32); rough = np.zeros((n, n), np.float32)
    wob = 0.012 * gn((1, n), (1, 30), 41)[0]                 # layer boundaries wobble along u
    Z = zz[:, None] + wob[None, :]
    pore1 = gn((n, n), (2.2, 1.6), 42); pore2 = gn((n, n), (5, 3.5), 43); pores = np.clip((pore1 * 0.75 + pore2 * 0.55 - 1.0) * 1.4, 0, 1)
    big = np.clip((gn((n, n), (7, 5), 44) - 1.9) * 2, 0, 1)
    hgt -= 0.01 * pores + 0.016 * big
    for (z0, z1, kind) in LAY:
        m = ((Z <= z0) & (Z > z1)).astype(np.float32)
        if kind == 'sponge':
            t = np.clip(np.minimum(z0 - Z, Z - z1) / 0.03, 0, 1)            # baked skin at the layer faces
            c = sponge[None, None] * (1 + 0.06 * gn((n, n), 20, 45)[..., None])
            c = c + (hx('9a6428') - c) * np.clip(0.75 * pores + 0.8 * big, 0, 1)[..., None]
            c = crust + (c - crust) * ss(0.0, 1.0, t)[..., None]
            r = 0.85 * np.ones((n, n))
        elif kind == 'cream':
            c = cream[None, None] * (1 + 0.015 * gn((n, n), 3, 46)[..., None]); r = 0.5 * np.ones((n, n))
            hgt += m * 0.003 * gn((n, n), 6, 47)
        elif kind == 'jam':
            seeds = np.clip((gn((n, n), 1.2, 48) - 2.6) * 3, 0, 1)
            fruit = np.clip(gn((n, n), (3, 10), 49) * 0.5 + 0.3, 0, 1)
            c = jam[None, None] * (1 + 0.25 * fruit[..., None]) + seeds[..., None] * (hx('e8b050') - jam)[None, None] * 0.7
            r = 0.16 + 0.1 * seeds
        else:
            c = frost[None, None] * np.ones((n, n, 1)); r = 0.38 * np.ones((n, n))
        col = col * (1 - m[..., None]) + c * m[..., None]; rough = rough * (1 - m) + r * m
    # the outer buttercream coat (and the pink drip skin) at the outside of each wall
    u = np.r_[np.linspace(0, 1, n // 2, endpoint=False), np.linspace(0, 1, n // 2, endpoint=False)] + 0.5 / (n // 2)
    souter = np.array([s_hit(U1, float(rprof(z))) for z in zz]) / SMAX
    coat = ss(-0.012, 0.0, u[None, :] - souter[:, None] + 0.07 / SMAX + 0.004 * gn((n, n), (8, 2), 50))
    col = col * (1 - coat[..., None]) + frost * coat[..., None]; rough = rough * (1 - coat) + 0.38 * coat
    hgt += 0.004 * coat
    col = col[::-1]; rough = rough[::-1]; hgt = hgt[::-1]          # image rows run bottom-up in Blender
    nrm = h2n(hgt[::-1], SMAX / (n // 2), H / n)[::-1]
    return col, rough, nrm


# ================================================================ the cake
def build_cake():
    tc, tr, tn = build_top_maps()
    M_TOP = pmat('m_top', img=image('top_col', tc), ormimg=image('top_orm', orm(tr), True), nimg=image('top_nrm', tn, True),
                 sss=0.15, sss_r=(1.0, 0.75, 0.6), sss_s=0.015, nstr=2.0)
    sc, sr, sn = build_side_maps()
    M_SIDE = pmat('m_side', img=image('side_col', sc), ormimg=image('side_orm', orm(sr), True), nimg=image('side_nrm', sn, True),
                  sss=0.35, sss_r=(1.0, 0.75, 0.6), sss_s=0.05)
    cc, cr, cn = build_crumb_maps()
    M_CUT = pmat('m_cut', img=image('cut_col', cc), ormimg=image('cut_orm', orm(cr), True), nimg=image('cut_nrm', cn, True),
                 sss=0.08, sss_r=(1.0, 0.6, 0.3), sss_s=0.015, nstr=1.5)
    log('cake maps')
    # --- top: polar grid, outer rows bend to follow the cut
    nseg = 160
    th = list(np.linspace(-math.pi, math.pi, nseg, endpoint=False))
    for extra in (PHN, ang(wall_pt(U1, s_hit(U1, RIN))), ang(wall_pt(U2, s_hit(U2, RIN)))):
        th = [t for t in th if abs(wrapd(t - extra)) > 0.008] + [extra]
    th = np.array(sorted(th)); ns = len(th)
    rin = np.r_[np.linspace(0.35, 4.3, 11), 4.45, 4.55, 4.6, 4.65, 4.7]
    V = [(0, 0, 0)]; UV = [(0.5, 0.5)]
    for t in th:
        rm = rmax(t)
        rr = np.r_[rin, np.linspace(4.7, rm, 6)[1:]] if rm > 4.71 else np.r_[rin[rin < rm - 0.01], rm]
        rr = np.interp(np.linspace(0, 1, len(rin) + 5), np.linspace(0, 1, len(rr)), rr)
        for r in rr: V.append((r * math.cos(t), r * math.sin(t), 0))
    nr = len(rin) + 5
    V = np.array(V); UV = (V[:, :2] + TSPAN) / (2 * TSPAN)
    F = []
    def vid(j, i): return 1 + (j % ns) * nr + i
    for j in range(ns):
        F.append((0, vid(j, 0), vid(j + 1, 0)))
        for i in range(nr - 1): F.append((vid(j, i), vid(j, i + 1), vid(j + 1, i + 1), vid(j + 1, i)))
    mk('cake_top', V, F, UV, M_TOP, fix=lambda c: (0, 0, 1))
    # --- side lathe (incl. the rounded top edge), open at the cut
    ra = np.linspace(0, math.pi / 2, 7)
    prof = [(RIN + RE * math.sin(a), -RE + RE * math.cos(a)) for a in ra] + [(RT, z) for z in np.linspace(-RE, -H, 13)[1:]]
    V = []; UV = []; ncol = 150
    for (r, z) in prof:
        a1 = ang(wall_pt(U1, s_hit(U1, r))); a2 = ang(wall_pt(U2, s_hit(U2, r)))
        a2u = a2 + TAU if a2 < a1 else a2
        for a in np.linspace(a1, a2u, ncol + 1):
            V.append((r * math.cos(a), r * math.sin(a), z)); UV.append(((a - a1) / TAU * 6, (z + H) / (H + 0.4)))
    mk('cake_side', V, grid_faces(len(prof), ncol + 1), UV, M_SIDE,
       fix=lambda c: (c[0], c[1], max(c[2] + RE, 0) * 3))
    # --- the two cut walls
    zs = np.r_[[-RE + RE * math.cos(a) for a in ra], np.linspace(-RE, -H, 24)[1:]]
    for wi, u in enumerate((U1, U2)):
        V = []; UV = []; nc = 10
        for z in zs:
            so = s_hit(u, float(rprof(z)))
            for s in np.linspace(0, so, nc + 1):
                p = wall_pt(u, s); V.append((p[0], p[1], z)); UV.append((0.5 * wi + 0.5 * s / SMAX, (z + H) / H))
        inner = P0 + 0.6 * np.array([math.cos(PHN), math.sin(PHN)])
        mk('cake_cut%d' % wi, V, grid_faces(len(zs), nc + 1), UV, M_CUT,
           fix=lambda c, inner=inner: (inner[0] - c[0], inner[1] - c[1], 0))
    log('cake body')
    return M_TOP, M_SIDE, M_CUT


# ================================================================ drip, piping, fruit, sprinkles
M_DRIP = pmat('m_drip', 'ec6f98', rough=0.12, coat=0.6, coat_r=0.04, sss=0.25, sss_r=(1, 0.3, 0.35), sss_s=0.03, spec=0.6)
def star_tip_nrm():
    """normal map for piped buttercream: u around the tube (8 star-tip ridges), v along it (tiny drag streaks)."""
    n = 128 if FAST else 256
    u = (np.arange(n) + 0.5) / n; U, Vv = np.meshgrid(u, u)
    hgt = np.abs(np.sin(math.pi * 8 * U)) ** 0.55 * 0.012 + 0.0015 * gn((n, n), (1.0, 6), 401)   # rows = v
    rough = np.clip(0.4 - 0.1 * (hgt / 0.012) + 0.03 * gn((n, n), 2, 402), 0.2, 0.7)
    return h2n(hgt, 0.63 / n, 1.5 / n), rough
_SN, _SR = star_tip_nrm(); _SNI = image('pipe_nrm', _SN, True); _SRI = image('pipe_orm', orm(_SR), True)
M_PINK = pmat('m_pipe_pink', 'f5aec4', rough=0.42, sss=0.12, sss_r=(1, 0.6, 0.55), sss_s=0.012, nimg=_SNI, ormimg=_SRI, nstr=1.0)
M_WHITE = pmat('m_pipe_white', 'fcf4ec', rough=0.42, sss=0.12, sss_r=(1, 0.75, 0.6), sss_s=0.012, nimg=_SNI, ormimg=_SRI, nstr=1.0)
M_LINE = pmat('m_line', 'e2557d', rough=0.45, sss=0.35, sss_r=(1, 0.35, 0.4), sss_s=0.03, bump=(14, 0.15))

def build_drip():
    # band: over the top rim, round the edge and a little way down the side, wavy lower edge
    s_top = RIN - 4.98; s_round = RE * math.pi / 2
    def surf(s):
        """arc length from r=4.98 on the top -> (r, z, nr, nz) on the cake surface."""
        if s <= s_top: return 4.98 + s, 0.0, 0.0, 1.0
        if s <= s_top + s_round:
            a = (s - s_top) / RE; return RIN + RE * math.sin(a), -RE + RE * math.cos(a), math.sin(a), math.cos(a)
        return RT, -RE - (s - s_top - s_round), 1.0, 0.0
    ncol = 200; band_len = 0.13
    a1 = ang(wall_pt(U1, s_hit(U1, RT))); a2 = ang(wall_pt(U2, s_hit(U2, RT))); a2u = a2 + TAU if a2 < a1 else a2
    cols = np.linspace(a1 + 0.004, a2u - 0.004, ncol + 1)
    wav = 0.05 * gn((1, ncol + 1), (1, 3), 61)[0]
    V = []; rows = 9
    for i in range(rows):
        for j, a in enumerate(cols):
            smax = s_top + s_round + band_len + wav[j]
            s = smax * i / (rows - 1)
            r, z, nr_, nz_ = surf(s)
            # top edge tucked under the rosettes (thin), full thickness on the shoulder, tapering at the lower edge
            tk = 0.034 * ss(0, 0.1, s) * (1 - ss(smax - 0.07, smax, s) * 0.92)
            V.append(((r + nr_ * tk) * math.cos(a), (r + nr_ * tk) * math.sin(a), z + nz_ * tk))
    mk('drip_band', V, grid_faces(rows, ncol + 1), None, M_DRIP, fix=lambda c: (c[0], c[1], max(c[2] + 0.1, 0) * 4))
    # individual drips: half capsules lying on the side, bulging into a bead at the end
    mg = Merge(); rg = np.random.default_rng(62)
    a = a1 + 0.05
    while a < a2u - 0.05:
        Ld = float(np.clip(rg.gamma(2.0, 0.22), 0.12, 1.25)); w = rg.uniform(0.055, 0.085)
        if rg.random() < 0.18: Ld *= 0.4
        nrm = np.array([math.cos(a), math.sin(a), 0]); tg = np.array([-math.sin(a), math.cos(a), 0])
        ys = np.r_[np.linspace(-0.04, Ld - w * 1.25, 5), Ld - w * 1.25 + w * 1.25 * np.sin(np.linspace(0.35, 1, 4) * math.pi / 2)]
        ks = 6; Vd = []
        for y in ys:
            wb = w * (1 + 0.22 * ss(Ld * 0.55, Ld - w, y))
            if y > Ld - w * 1.25:
                q = (y - (Ld - w * 1.25)) / (w * 1.25); wy = wb * math.sqrt(max(1 - q * q, 0))
            else: wy = wb
            thk = 0.036 * (1 + 0.45 * ss(Ld * 0.5, Ld - w, y)) * (wy / wb if wb else 0)
            for k in range(ks + 1):
                phi = -math.pi / 2 + math.pi * k / ks
                p = np.array([0, 0, -RE - 0.05 - y]) + nrm * (RT - 0.004 + thk * math.cos(phi)) + tg * wy * math.sin(phi)
                Vd.append(p)
        mg.add(Vd, grid_faces(len(ys), ks + 1))
        a += (rg.uniform(0.22, 0.52)) / RT
    o = mg.build('drips', M_DRIP)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, c.y, 0))) < 0: f.normal_flip()
    bm.to_mesh(o.data); bm.free()
    log('drip')

def rosette(c, a0, mat, mg, scale=1.0):
    """a star-tip swirl dollop: a lathe whose 8-ridged cross-section twists as it rises to a soft curled peak."""
    rows, cols = 13, 24; Hr = 0.42 * scale; R0 = 0.27 * scale
    V = []; UV = []
    for i in range(rows):
        t = i / (rows - 1)
        r = R0 * (0.82 + 0.18 * math.sin(math.pi * min(t / 0.25, 1) / 2)) * (1 - t) ** 0.75 if t < 1 else 0
        if i == 0: r = R0 * 0.8
        z = Hr * (t if i else 0.0) + (0.0 if i else -0.02)
        lean = 0.05 * scale * t ** 2
        for j in range(cols + 1):
            an = j / cols * TAU
            rr = r * (1 + (0.26 - 0.1 * t) * math.cos(8 * an + 3.6 * t + a0))
            V.append((c[0] + rr * math.cos(an) + lean * math.cos(a0), c[1] + rr * math.sin(an) + lean * math.sin(a0), c[2] + z))
            UV.append((j / cols, t))
    mg[mat].add(V, grid_faces(rows, cols + 1), UV)

def piped(P, rad, sides, nstar, star, rz=None):
    """star-tip tube as an open strip with a duplicated seam column so the ridge normal map tiles around it."""
    V, F = tube(P, rad, sides=sides, star=star, nstar=nstar, rz=rz, arc=(0, TAU))
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.asarray(P), axis=0), axis=1))]
    UV = [(k / sides, seg[i] / 1.5) for i in range(len(P)) for k in range(sides + 1)]
    return V, F, UV

def build_piping():
    mg = {M_PINK: Merge(), M_WHITE: Merge()}
    rg = np.random.default_rng(71)
    for k, a in enumerate(ROS):
        rosette((RROS * math.cos(a), RROS * math.sin(a), 0.01), rg.uniform(0, TAU), M_PINK if k % 2 else M_WHITE, mg, 1.25)
    # base shell border (white), open at the cut
    a1 = ang(wall_pt(U1, s_hit(U1, RT))); a2 = ang(wall_pt(U2, s_hit(U2, RT))); a2u = a2 + TAU if a2 < a1 else a2
    a1 += 0.03; a2u -= 0.03
    nsh = int((a2u - a1) * RT / 0.45); per = 5
    t = np.linspace(0, nsh, nsh * per + 1); f = t % 1.0
    bump = np.sin(math.pi * np.clip(f / 0.4, 0, 1) / 2) * (1 - ss(0.4, 1.0, f)) ** 0.8
    aa = a1 + (a2u - a1) * t / nsh
    rr = RT + 0.04 + 0.05 * bump; zz = -H + 0.07 + 0.04 * bump
    P = np.stack([rr * np.cos(aa), rr * np.sin(aa), zz], 1)
    V, F, UV = piped(P, 0.04 + 0.1 * bump, 6, 3, 0.2)
    mg[M_PINK].add(V, F, UV)
    mg[M_PINK].build('piping_pink', M_PINK, uv=True); mg[M_WHITE].build('piping_white', M_WHITE, uv=True)
    # the fighting circle: a piped line of pink icing, 2.8 cm high
    n = 300; a = np.linspace(0, TAU, n, endpoint=False)
    wv = 1 + 0.06 * gn((1, n), (1, 6), 72)[0]
    P = np.stack([RING * np.cos(a), RING * np.sin(a), np.full(n, 0.012)], 1)
    P = np.vstack([P, P[:1]]); wv = np.r_[wv, wv[:1]]
    V, F = tube(P, 0.05 * wv, sides=6, cap=False, rz=0.32)
    V[:, 2] = np.maximum(V[:, 2], -0.004)
    mk('ring_line', V, F, None, M_LINE)
    log('piping')

def straw_tex():
    n = 256 if FAST else 512
    u = (np.arange(n) + 0.5) / n; U, Vv = np.meshgrid(u, u)
    cols_, rows_ = 14, 9
    gy = Vv * rows_; gx = U * cols_ + 0.5 * (np.floor(gy) % 2)
    dx_ = (gx % 1) - 0.5; dy_ = (gy % 1) - 0.5
    d = np.hypot(dx_ * 1.0, dy_ * 1.5)
    pit = np.exp(-(d / 0.22) ** 2); seed = np.exp(-(d / 0.09) ** 2)
    base = hx('c8101c'); top = hx('e9e0b8')
    tipfade = ss(0.0, 0.25, Vv)[..., None]            # v=0 at the tip, 1 near the calyx (paler shoulders)
    col = base * (1 + 0.15 * gn((n, n), 12, 81)[..., None]) * (1 - 0.25 * pit[..., None])
    col = col + (top - col) * (1 - tipfade) * 0.0 + (hx('f2d060') - col) * seed[..., None] * 0.85
    col = col + (hx('f0e4c0') - col) * ss(0.9, 1.0, Vv)[..., None] * 0.7
    hgt = -0.6 * pit + 0.5 * seed
    rough = np.clip(0.22 + 0.25 * pit + 0.05 * gn((n, n), 4, 82), 0.1, 0.8)
    return col, rough, h2n(hgt, 1 / n * 20, 1 / n * 20)

def build_fruit():
    sc, sr, sn = straw_tex()
    M_STR = pmat('m_strawberry', img=image('straw_col', sc), ormimg=image('straw_orm', orm(sr), True), nimg=image('straw_nrm', sn, True),
                 sss=0.3, sss_r=(1, 0.2, 0.15), sss_s=0.05, coat=0.3, coat_r=0.1, nstr=0.8)
    M_LEAF = pmat('m_calyx', '3f8a2a', rough=0.45, sss=0.2, sss_r=(0.4, 1, 0.3), sss_s=0.02)
    M_CHERRY = pmat('m_cherry', '7a0812', rough=0.1, coat=0.8, coat_r=0.03, sss=0.25, sss_r=(1, 0.1, 0.1), sss_s=0.04)
    M_STEM = pmat('m_stem', '5a6a2a', rough=0.6)
    ms, ml, mc, mt = Merge(), Merge(), Merge(), Merge()
    rg = np.random.default_rng(83)
    Ls, Rs = 0.6, 0.25
    tprof = np.linspace(0, 1, 14)
    # strawberry: v from tip (0) to shoulder (1)
    def straw_shape(t): return Rs * (np.sin(np.clip(t, 0, 1) * math.pi * 0.62) ** 0.75) * (1 - 0.25 * ss(0.85, 1, t))
    for k, a in enumerate(ROS):
        c = np.array([RROS * math.cos(a), RROS * math.sin(a), 0.4])
        if k % 3 == 1:   # strawberry, lying tilted on the rosette, tip pointing out
            out = np.array([math.cos(a), math.sin(a), 0])
            axis = out * 0.55 + np.array([0, 0, 0.83]); Rm = frame(axis) @ rotz(rg.uniform(0, TAU))
            segs = 16; Vv = []; UVv = []
            for t in tprof:
                for j in range(segs + 1):
                    an = j / segs * TAU; r = straw_shape(t) * (1 + 0.04 * math.cos(3 * an + 1.7 * t))
                    p = np.array([r * math.cos(an), r * math.sin(an), (1 - t) * Ls]); Vv.append(c - axis / np.linalg.norm(axis) * 0.05 + Rm @ p * 1.0)
                    UVv.append((j / segs, t))
            F = grid_faces(len(tprof), segs + 1)
            ms.add(Vv, F, UVv)
            # calyx: 7 sepals flaring from the shoulder
            top_c = c - axis / np.linalg.norm(axis) * 0.05
            for s in range(7):
                aa = s / 7 * TAU + rg.uniform(-0.2, 0.2)
                d = Rm @ np.array([math.cos(aa), math.sin(aa), 0]); ax_ = Rm @ np.array([0, 0, -1.0])
                pts = [top_c + d * (0.03 + 0.2 * q) + ax_ * (0.04 * q - 0.02 + 0.06 * q * q) for q in np.linspace(0, 1, 5)]
                w = np.array([0.03, 0.045, 0.04, 0.025, 0.004])
                Vl = []; side = np.cross(d, ax_)
                for p, ww in zip(pts, w): Vl += [p - side * ww, p + side * ww]
                ml.add(Vl, [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(4)])
            st = [top_c + Rm @ np.array([0, 0, -1.0]) * q * 0.12 for q in np.linspace(0, 1, 4)]
            V2, F2 = tube(st, 0.018, sides=6); mt.add(V2, F2)
        elif k % 3 == 2 and k % 2 == 0:   # cherry with its stem
            cr = 0.17; cc_ = c + np.array([0, 0, 0.12])
            prof = [(0.0, -cr)] + [(cr * math.sin(q), -cr * math.cos(q)) for q in np.linspace(0.25, math.pi - 0.3, 10)] + [(0.035, cr * 0.82), (0.0, cr * 0.72)]
            Vv = []
            segs = 16
            for (r, z) in prof:
                for j in range(segs + 1):
                    an = j / segs * TAU; Vv.append(cc_ + np.array([r * math.cos(an), r * math.sin(an), z]))
            mc.add(Vv, grid_faces(len(prof), segs + 1))
            b0 = cc_ + np.array([0, 0, cr * 0.72]); dd = rg.uniform(0, TAU)
            st = [b0 + np.array([math.cos(dd) * 0.25 * q * q, math.sin(dd) * 0.25 * q * q, 0.42 * q]) for q in np.linspace(0, 1, 8)]
            V2, F2 = tube(st, np.linspace(0.016, 0.011, 8), sides=6); mt.add(V2, F2)
    for o in (ms.build('strawberries', M_STR, uv=True), ml.build('calyx', M_LEAF), mc.build('cherries', M_CHERRY), mt.build('stems', M_STEM)):
        if o: weld(o, 1e-4)
    log('fruit')

SPR_COLS = ['ff4f7b', '3cb4ff', 'ffd02e', '5fd36a', 'a874ff', 'ff8a3a', 'fffaf2']
def sprinkle(c, d, L=0.2, r=0.028, up=(0, 0, 1)):
    """a little rod with domed ends: 4 sides, 10 verts, 16 tris."""
    d = np.asarray(d, np.float64); d /= np.linalg.norm(d)
    n1 = np.cross(d, up); n1 = n1 / (np.linalg.norm(n1) + 1e-9) if np.linalg.norm(n1) > 1e-6 else np.cross(d, [1, 0, 0]); n1 /= np.linalg.norm(n1)
    n2 = np.cross(d, n1); V = []
    for e in (-1, 1):
        for k in range(4):
            a = (k + 0.5) / 4 * TAU; V.append(c + d * e * (L / 2 - r * 0.6) + r * (math.cos(a) * n1 + math.sin(a) * n2))
    V.append(c - d * L / 2); V.append(c + d * L / 2)
    F = [(k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k) for k in range(4)]
    F += [(8, (k + 1) % 4, k) for k in range(4)] + [(9, 4 + k, 4 + (k + 1) % 4) for k in range(4)]
    return V, F

def build_sprinkles():
    mats = [pmat('m_spr_%d' % i, c_, rough=0.3, sss=0.2, sss_r=(1, 0.8, 0.6), sss_s=0.02, coat=0.25) for i, c_ in enumerate(SPR_COLS)]
    mg = [Merge() for _ in mats]; rg = np.random.default_rng(91)
    def put(c, d, up=(0, 0, 1)):
        V, F = sprinkle(np.asarray(c), d, L=rg.uniform(0.15, 0.23), up=up); mg[rg.integers(len(mats))].add(V, F)
    n_top = 500 if FAST else 900; placed = 0
    while placed < n_top:   # on the top: half sunk into the buttercream (<= 3 cm proud)
        r = 4.95 * math.sqrt(rg.random()); a = rg.uniform(-math.pi, math.pi)
        if 4.52 < r < 4.68 or in_cut(a, r) or r > rmax(a) - 0.05: continue
        if r > 4.68 and min(abs(wrapd(a - b)) for b in ROS) * RROS < 0.3: continue
        if (r * math.cos(a) - GYOJI[0]) ** 2 + (r * math.sin(a) - GYOJI[1]) ** 2 < 0.1: continue
        c = (r * math.cos(a), r * math.sin(a), 0.002); da = rg.uniform(0, TAU)
        put(c, (math.cos(da), math.sin(da), rg.uniform(-0.03, 0.03))); placed += 1
    for _ in range(40 if FAST else 80):   # stuck on the sides
        a = rg.uniform(-math.pi, math.pi)
        if near_cut(a, 0.02): continue
        z = -rg.uniform(0.3, 1.9); nrm = np.array([math.cos(a), math.sin(a), 0])
        tg = np.array([-math.sin(a), math.cos(a), 0]); da = rg.uniform(0, TAU)
        put(nrm * (RT + 0.012) + np.array([0, 0, z]), tg * math.cos(da) + np.array([0, 0, math.sin(da)]), up=nrm)
    for _ in range(30 if FAST else 40):    # fallen onto the stand plate
        r = rg.uniform(RT + 0.25, 6.05); a = rg.uniform(-math.pi, math.pi); da = rg.uniform(0, TAU)
        put((r * math.cos(a), r * math.sin(a), PZ + 0.025), (math.cos(da), math.sin(da), 0))
    for _ in range(30 if FAST else 50):   # and onto the cloth
        r = 6.9 + rg.gamma(1.5, 1.4); a = rg.uniform(-math.pi, math.pi); da = rg.uniform(0, TAU)
        put((r * math.cos(a), r * math.sin(a), TZ + 0.025), (math.cos(da), math.sin(da), 0))
    for i, m in enumerate(mats): mg[i].build('sprinkles_%d' % i, m, smooth=True)
    log('sprinkles')


# ================================================================ candles
def candle_tex(colhex):
    n = 128 if FAST else 256
    u = (np.arange(n) + 0.5) / n; U, Vv = np.meshgrid(u, u)
    stripe = ss(0.04, 0.0, np.abs(((U * 2 + Vv * 1.6) % 1.0) - 0.25) - 0.13)
    col = hx(colhex) + (hx('fffaf2') - hx(colhex)) * stripe[..., None]
    return col * (1 + 0.02 * gn((n, n), 3, 101)[..., None])

FLAMES = []
def build_candles():
    M_WICK = pmat('m_wick', '1a1410', rough=0.9)
    M_EMBER = pmat('m_ember', '301008', emit='ff5a10', emit_s=12.0)
    M_FL = flame_mat()
    cols = ['8fd0ff', 'ff9ec0', 'ffe07a', '9ae6a8', 'c6a6ff']
    rg = np.random.default_rng(111)
    Hc, Rc = 1.3, 0.11
    for k, a in enumerate(CANDLES):
        ch = cols[k % len(cols)]
        M = pmat('m_candle_%d' % k, img=image('candle_%d' % k, candle_tex(ch)), rough=0.35, sss=0.6, sss_r=(1, 0.75, 0.5), sss_s=0.06, coat=0.15)
        base = np.array([RROS * math.cos(a), RROS * math.sin(a), -0.08])
        tw = rg.uniform(0, TAU)
        zs = np.r_[np.linspace(0, Hc - 0.03, 14), Hc - 0.01, Hc]
        segs = 18; V = []; UV = []
        for i, z in enumerate(zs):
            for j in range(segs + 1):
                an = j / segs * TAU
                rr = Rc * (1 + 0.09 * math.cos(6 * an + 7.0 * z + tw))
                if z >= Hc - 0.03: rr *= [1.0, 0.9, 0.55][min(i - (len(zs) - 3), 2)] if i >= len(zs) - 3 else 1
                zz = z + (0.0 if i < len(zs) - 1 else -0.02)
                V.append(base + np.array([rr * math.cos(an), rr * math.sin(an), zz])); UV.append((j / segs, z / Hc))
        V.append(base + np.array([0, 0, Hc - 0.025])); UV.append((0.5, 1.0)); c0 = len(V) - 1
        F = grid_faces(len(zs), segs + 1); lr = (len(zs) - 1) * (segs + 1)
        F += [(c0, lr + j, lr + j + 1) for j in range(segs)]
        # wax drips running down from the rim
        mg = Merge(); mg.add(V, F, UV)
        for d in range(rg.integers(2, 4)):
            an = rg.uniform(0, TAU); Ld = rg.uniform(0.1, 0.42)
            pts = []
            for q in np.linspace(0, 1, 9):
                z = Hc - 0.01 - Ld * q; a2 = an + 0.25 * q
                rr = Rc * (1 + 0.09 * math.cos(6 * a2 + 7.0 * z + tw)) + 0.006
                pts.append(base + np.array([rr * math.cos(a2), rr * math.sin(a2), z]))
            V2, F2 = tube(pts, np.r_[np.linspace(0.016, 0.02, 7), 0.017, 0.004], sides=6)
            mg.add(V2, F2, np.tile([[0.5, 0.98]], (len(V2), 1)))
        mg.build('candle_%d' % k, M, uv=True)
        top = base + np.array([0, 0, Hc - 0.02])
        bend = rg.uniform(0, TAU)
        wpts = [top + np.array([0.02 * q * q * math.cos(bend), 0.02 * q * q * math.sin(bend), 0.11 * q]) for q in np.linspace(0, 1, 5)]
        V2, F2 = tube(wpts, 0.011, sides=6); mk('wick_%d' % k, V2, F2, None, M_WICK)
        V2, F2 = tube([wpts[-1] - np.array([0, 0, 0.012]), wpts[-1] + np.array([0, 0, 0.006])], 0.012, sides=6); mk('ember_%d' % k, V2, F2, None, M_EMBER)
        # flame: teardrop, leaning a touch
        fb = wpts[-1] + np.array([0, 0, -0.035]); hf = 0.36; lean = np.array([rg.uniform(-0.02, 0.02), rg.uniform(-0.02, 0.02), 0])
        prof = [(0.0, 0.0)] + [(0.068 * math.sin(math.pi * min(t / 0.38, 1) / 2) ** 0.8 * (1 - ss(0.3, 1.0, t)) ** 0.9 + 0.001, hf * t) for t in np.linspace(0.04, 1, 14)] + [(0, hf)]
        Vf = []
        for (r, z) in prof:
            for j in range(17):
                an = j / 16 * TAU; Vf.append(fb + lean * (z / hf) ** 2 + np.array([r * math.cos(an), r * math.sin(an), z]))
        fo = mk('flame_%d' % k, Vf, grid_faces(len(prof), 17), None, M_FL); weld(fo, 1e-5)
        FLAMES.append(fb + np.array([0, 0, 0.13]))
    log('candles', len(FLAMES))

def flame_mat():
    m = bpy.data.materials.new('m_flame'); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); L.new(sep.outputs['Z'], ramp.inputs[0])
    el = ramp.color_ramp.elements
    el[0].position = 0.0; el[0].color = (0.15, 0.3, 1.0, 1); el[1].position = 1.0; el[1].color = (1.0, 0.35, 0.05, 1)
    e = el.new(0.16); e.color = (1.0, 0.75, 0.35, 1); e = el.new(0.4); e.color = (1.0, 0.92, 0.7, 1); e = el.new(0.75); e.color = (1.0, 0.6, 0.15, 1)
    em = N.new('ShaderNodeEmission'); L.new(ramp.outputs['Color'], em.inputs['Color'])
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.55
    mp = N.new('ShaderNodeMapRange'); mp.inputs['From Min'].default_value = 0.0; mp.inputs['From Max'].default_value = 0.9
    mp.inputs['To Min'].default_value = 40.0; mp.inputs['To Max'].default_value = 4.0
    L.new(lw.outputs['Facing'], mp.inputs['Value']); L.new(mp.outputs['Result'], em.inputs['Strength'])
    tr = N.new('ShaderNodeBsdfTransparent'); mix = N.new('ShaderNodeMixShader')
    L.new(lw.outputs['Facing'], mix.inputs['Fac']); L.new(em.outputs[0], mix.inputs[1]); L.new(tr.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])
    m.blend_method = 'BLEND'
    return m


# ================================================================ stand, cloth
def build_stand():
    M = pmat('m_porcelain', 'f7f4f2', rough=0.08, coat=0.5, coat_r=0.03, sss=0.15, sss_r=(1, 0.9, 0.8), sss_s=0.02)
    M_GOLD = pmat('m_gold', 'e2b65a', rough=0.22, metal=1.0)
    prof = [(0, PZ), (5.9, PZ), (6.1, PZ + 0.02), (6.22, PZ + 0.07), (6.3, PZ + 0.075), (6.34, PZ + 0.04), (6.3, PZ - 0.05),
            (6.0, PZ - 0.13), (4.0, PZ - 0.19), (1.3, PZ - 0.24), (0.85, PZ - 0.36), (0.62, PZ - 0.62), (0.56, PZ - 0.9),
            (0.62, PZ - 1.05), (0.82, PZ - 1.12), (0.66, PZ - 1.2), (0.7, PZ - 1.3), (1.2, PZ - 1.47), (2.1, PZ - 1.6),
            (2.6, TZ + 0.06), (2.66, TZ + 0.02), (2.6, TZ), (0, TZ)]
    p = np.array(prof, np.float64); P2 = [p[0]]
    for i in range(1, len(p) - 1):   # round the corners a little
        P2 += [p[i] * 0.75 + p[i - 1] * 0.25, p[i], p[i] * 0.75 + p[i + 1] * 0.25] if 0 < i < len(p) - 2 else [p[i]]
    P2.append(p[-1])
    o = lathe(P2, 48, 'cake_stand', M)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    # thin gold band on the rim
    a = np.linspace(0, TAU, 121)
    P = np.stack([6.33 * np.cos(a), 6.33 * np.sin(a), np.full_like(a, PZ + 0.015)], 1)
    V, F = tube(P, 0.03, sides=6, cap=False, rz=1.4); mk('stand_gold', V, F, None, M_GOLD)
    log('stand')

HX, HY, DROP = 19.0, 19.0, 6.5
def build_cloth():
    T = 512 if FAST else 1024; th = 8 if not FAST else 4; tile = 0.8
    i = np.arange(T) // th; f = (np.arange(T) % th + 0.5) / th
    nth = T // th; chk = nth // 2
    red = ((i // chk) % 2 == 0)
    I, J = np.meshgrid(i, i); FX, FY = np.meshgrid(f, f)
    top = (I + J) % 2 == 0
    PNK = hx('e9799f'); WHT = hx('fbf4ee')
    rt = np.random.default_rng(3)
    slub_c = 1 + 0.05 * rt.standard_normal(nth); slub_r = 1 + 0.05 * rt.standard_normal(nth)
    warp = np.where(red[:, None], PNK, WHT) * slub_c[i][:, None]
    weft = np.where(red[:, None], PNK, WHT) * slub_r[i][:, None]
    col = np.where(top[..., None], warp[None, :, :], weft[:, None, :])
    hw = np.sin(math.pi * FX) ** 0.7 * (0.75 + 0.25 * np.sin(math.pi * FY))
    hf = np.sin(math.pi * FY) ** 0.7 * (0.75 + 0.25 * np.sin(math.pi * FX))
    h = np.where(top, hw, hf); fib = gn((T, T), 0.8, 111)
    col = col * (0.82 + 0.18 * h[..., None]) * (1 + 0.025 * fib[..., None])
    rough = np.clip(0.85 + 0.05 * fib, 0, 1)
    nrm = h2n(h * 0.001 + 0.0001 * fib, tile / T, tile / T, 1.0)
    M = pmat('m_cloth', img=image('cloth_col', col), ormimg=image('cloth_orm', orm(rough), True), nimg=image('cloth_nrm', nrm, True),
             sheen=0.7, sheen_r=0.35, sss=0.08, sss_r=(1, 0.5, 0.5), sss_s=0.02)
    def axis(Hh):
        inner = np.linspace(-Hh + 1.6, Hh - 1.6, int((2 * Hh - 3.2) / 2.6) + 1)
        edge = np.linspace(Hh - 1.6, Hh + DROP, int((1.6 + DROP) / 0.4) + 1)[1:]
        return np.r_[-edge[::-1], inner, edge]
    xs, ys = axis(HX), axis(HY)
    A, B = np.meshgrid(xs, ys)
    qx = np.clip(A, -HX, HX); qy = np.clip(B, -HY, HY)
    ox, oy = A - qx, B - qy; d = np.hypot(ox, oy) + 1e-9; dx, dy = ox / d, oy / d
    angl = np.arctan2(dy, dx)
    s = np.where(np.abs(ox) > np.abs(oy), qy * np.sign(ox), -qx * np.sign(oy)) + angl * 1.2
    rr = 0.3; phi = np.minimum(d / rr, math.pi / 2); hang = np.maximum(d - rr * math.pi / 2, 0)
    rc = np.random.default_rng(12)
    fold = sum(np.sin(s * (TAU / wl) + rc.uniform(0, TAU)) * amp for wl, amp in ((2.8, 1.0), (1.6, 0.55), (0.95, 0.25)))
    corner = (np.abs(ox) > 0.2) & (np.abs(oy) > 0.2)
    amp = 0.34 * ss(0.0, 3.5, hang) * (1 + 0.8 * corner)
    out = rr * np.sin(phi) + amp * fold + 0.15 * ss(0, 4, hang)
    Xc = qx + dx * out; Yc = qy + dy * out; Zc = TZ - rr * (1 - np.cos(phi)) - hang
    flat = d < 1e-6
    wr = 0.025 * gn((len(ys), len(xs)), 2.0, 13)
    crease = 0.014 * (np.exp(-(A / 0.08) ** 2) + np.exp(-(B / 0.08) ** 2) + np.exp(-((np.abs(A) - HX / 2) / 0.08) ** 2))
    Zc = np.where(flat, TZ + wr + crease - 0.03, Zc)
    Xc = np.where(flat, A, Xc); Yc = np.where(flat, B, Yc)
    V = np.stack([Xc, Yc, Zc], -1).reshape(-1, 3); UV = np.stack([A / tile, B / tile], -1).reshape(-1, 2)
    mk('tablecloth', V, grid_faces(len(ys), len(xs)), UV, M, fix=lambda c: (c[0] * 0.01, c[1] * 0.01, 1) if c[2] > TZ - 0.2 else (c[0], c[1], 0))
    log('cloth')


# ================================================================ party props
def plate_tex():
    n = 512 if FAST else 1024
    c = (np.arange(n) + 0.5) / n * 2 - 1; X, Y = np.meshgrid(c, c); R = np.hypot(X, Y)
    col = np.ones((n, n, 3), np.float32) * hx('fffaf6')
    # pastel polka dots on the rim, gold band
    A_ = np.arctan2(Y, X); nd = 26
    dd = np.hypot((A_ % (TAU / nd) - TAU / nd / 2) * R, R - 0.86)
    col = np.where((dd < 0.035)[..., None], hx('7fcbf2'), col)
    dd2 = np.hypot(((A_ + TAU / nd / 2) % (TAU / nd) - TAU / nd / 2) * R, R - 0.74)
    col = np.where((dd2 < 0.022)[..., None], hx('f59ab8'), col)
    gold = (np.abs(R - 0.965) < 0.02) | (np.abs(R - 0.64) < 0.006)
    col = np.where(gold[..., None], hx('d9ab52'), col)
    met = gold.astype(np.float32); rough = np.where(gold, 0.25, 0.6)
    return col, rough, met

def build_props():
    pc, pr, pm = plate_tex()
    M_PLATE = pmat('m_plate', img=image('plate_col', pc), ormimg=image('plate_orm', orm(pr, pm), True), rough=0.6, sheen=0.2)
    M_FORK = pmat('m_fork', 'e6bf6a', rough=0.2, metal=1.0)
    rg = np.random.default_rng(141)
    PLATES = [(-9.4, -2.6, 0.3), (10.6, 5.6, -0.4), (-10.0, 8.6, 1.0)]
    for pi_, (x, y, rot) in enumerate(PLATES):
        Rp = 2.4; segs = 44; rows = np.r_[0, 0.3, 0.6, 0.9, 1.25, 1.55, 1.72, 1.85, 2.0, 2.15, 2.3, Rp]
        V = []; UV = []
        for r in rows:
            for j in range(segs + 1):
                a = j / segs * TAU
                rim = ss(1.6, Rp, r)
                z = 0.02 + 0.26 * rim ** 1.4 + 0.035 * rim * math.cos(36 * a) - 0.012 * ss(1.4, 1.6, r) * (1 - rim)
                rr = r * (1 + 0.01 * rim * math.cos(36 * a))
                V.append((x + rr * math.cos(a + rot), y + rr * math.sin(a + rot), TZ + z)); UV.append((0.5 + 0.5 * r / Rp * math.cos(a), 0.5 + 0.5 * r / Rp * math.sin(a)))
        o = mk('plate_%d' % pi_, V, grid_faces(len(rows), segs + 1), UV, M_PLATE, fix=lambda c: (0, 0, 1)); weld(o)
        sm = o.modifiers.new('thick', 'SOLIDIFY'); sm.thickness = 0.025; sm.offset = -1
    # forks: an outline extruded into a plate, bent a little
    def fork(pos, rot, tilt=0.0):
        L = 2.6
        outline = [(0, -0.1), (0.15, -0.12), (1.25, -0.08), (1.55, -0.055), (1.75, -0.07), (1.95, -0.17), (2.03, -0.18), (2.6, -0.17),
                   (2.6, -0.12), (2.07, -0.11), (2.07, -0.075), (2.6, -0.075), (2.6, -0.03), (2.07, -0.02), (2.07, 0.02), (2.6, 0.03), (2.6, 0.075),
                   (2.07, 0.075), (2.07, 0.11), (2.6, 0.12), (2.6, 0.17), (2.03, 0.18), (1.95, 0.17), (1.75, 0.07), (1.55, 0.055), (1.25, 0.08),
                   (0.15, 0.12), (0, 0.1), (-0.04, 0)]
        bm = bmesh.new(); vs = [bm.verts.new((x_, y_, 0)) for x_, y_ in outline]; f = bm.faces.new(vs)
        ex = bmesh.ops.extrude_face_region(bm, geom=[f]); top = [e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=top, vec=(0, 0, 0.045))
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        for v in bm.verts:
            x_ = v.co.x; v.co.z += 0.12 * ss(0.8, 1.9, x_) - 0.06 * ss(2.0, 2.6, x_) + 0.05 * ss(0.6, 0.0, x_)
        me = bpy.data.meshes.new('fork'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('fork', me); STAGE.objects.link(o); me.materials.append(M_FORK)
        o.location = pos; o.rotation_euler = (tilt, 0, rot)
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.015; bv.segments = 1; bv.limit_method = 'ANGLE'
        return o
    fork((-12.1, -1.4, TZ + 0.06), -0.9)
    fork((8.4, 4.0, TZ + 0.04), 2.6)
    fork((-11.9, 7.2, TZ + 0.3), 0.3, 0.0)
    log('plates/forks')
    return PLATES

def build_slice(M_TOP, M_SIDE, M_CUT, plate):
    """the wedge that was cut out, standing on the front-left plate (same geometry as the cut, inverted)."""
    objs = []
    ra = np.linspace(0, math.pi / 2, 7)
    zs = np.r_[[-RE + RE * math.cos(a) for a in ra], np.linspace(-RE, -H, 18)[1:]]
    inner = P0 + 0.6 * np.array([math.cos(PHN), math.sin(PHN)])
    for wi, u in enumerate((U1, U2)):
        V = []; UV = []; nc = 8
        for z in zs:
            so = s_hit(u, float(rprof(z)))
            for s in np.linspace(0, so, nc + 1):
                p = wall_pt(u, s); V.append((p[0], p[1], z)); UV.append((0.5 * wi + 0.5 * s / SMAX, (z + H) / H))
        objs.append(mk('slice_cut%d' % wi, V, grid_faces(len(zs), nc + 1), UV, M_CUT,
                       fix=lambda c, inner=inner: (c[0] - inner[0], c[1] - inner[1], 0) if True else 0))
    # outer side
    V = []; UV = []; nco = 14
    for z in zs:
        r = float(rprof(z)); b1 = ang(wall_pt(U1, s_hit(U1, r))); b2 = ang(wall_pt(U2, s_hit(U2, r)))
        for a in np.linspace(b2, b1, nco + 1): V.append((r * math.cos(a), r * math.sin(a), z)); UV.append(((a - b2) / TAU * 6, (z + H) / (H + 0.4)))
    objs.append(mk('slice_side', V, grid_faces(len(zs), nco + 1), UV, M_SIDE, fix=lambda c: (c[0], c[1], max(c[2] + RE, 0) * 3)))
    # top + bottom fans
    for zz, nm, mt in ((0.0, 'slice_top', M_TOP), (-H, 'slice_bot', M_CUT)):
        rr_ = RIN if zz == 0 else RT
        b1 = ang(wall_pt(U1, s_hit(U1, rr_))); b2 = ang(wall_pt(U2, s_hit(U2, rr_)))
        V = [(P0[0], P0[1], zz)] + [(rr_ * math.cos(a), rr_ * math.sin(a), zz) for a in np.linspace(b2, b1, nco + 1)]
        V = np.array(V); F = [(0, i, i + 1) for i in range(1, nco + 1)]
        objs.append(mk(nm, V, F, (V[:, :2] + TSPAN) / (2 * TSPAN), mt, fix=lambda c, zz=zz: (0, 0, 1 if zz == 0 else -1)))
    # a rosette and a strawberry-less cherry on its back edge
    mg = {M_PINK: Merge()}
    cpos = np.array([5.0 * math.cos(PHN), 5.0 * math.sin(PHN), 0.01]); rosette(cpos, 1.0, M_PINK, mg, 0.9)
    objs.append(mg[M_PINK].build('slice_rosette', M_PINK, uv=True))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); sl = bpy.context.object; sl.name = 'cake_slice'
    # move: centroid of the wedge to the plate, lying on its side so a cut face looks up
    cen = Vector((*(P0 + 0.45 * np.array([math.cos(PHN), math.sin(PHN)])), -H / 2))
    sl.data.transform(Matrix.Translation(-cen))
    x, y, rot = plate
    # stand it upright on the plate, wall 2 (its cut face) turned towards the game camera, a bit to the right
    n2 = np.array([U2[1], -U2[0]])                         # outward normal of wall 2 as seen from the slice
    want = math.atan2(-1.0, 0.45)
    zrot = want - math.atan2(n2[1], n2[0])
    x, y, rot = plate
    sl.location = (x, y, TZ + 0.045 + H / 2); sl.rotation_euler = (0, 0, zrot)
    log('slice')

def build_hat_gift_confetti_balloons():
    # --- party hat: foil-striped cone, tinsel pompom, elastic
    n = 512 if FAST else 1024
    u = (np.arange(n) + 0.5) / n; U, Vv = np.meshgrid(u, u)
    st = (((U * 8 + Vv * 2.5) % 1.0) < 0.5)
    dots = np.hypot(((U * 24) % 1) - 0.5, ((Vv * 12) % 1) - 0.5) < 0.18
    col = np.where(st[..., None], hx('b47cff'), hx('fff4fb')); col = np.where((dots & ~st)[..., None], hx('ffd23a'), col)
    met = (st * 0.0 + (dots & ~st) * 1.0).astype(np.float32); rough = np.where(st, 0.35, 0.45); rough = np.where(dots & ~st, 0.2, rough)
    M_HAT = pmat('m_hat', img=image('hat_col', col), ormimg=image('hat_orm', orm(rough, met), True), sheen=0.3)
    hx_, hy_ = HAT; hh, hr = 2.9, 1.05
    prof = [(hr * (1 - t), hh * t) for t in np.linspace(0, 1, 12)]
    o = lathe(prof, 48, 'party_hat', M_HAT, xy=(hx_, hy_, TZ + 0.01), rfun=lambda r, z, a: (r * (1 + 0.012 * math.sin(a * 3)), z))
    sm = o.modifiers.new('thick', 'SOLIDIFY'); sm.thickness = 0.02
    M_TIN = pmat('m_tinsel', 'f2c84a', rough=0.18, metal=1.0)
    mg = Merge(); rg = np.random.default_rng(151); tipc = np.array([hx_, hy_, TZ + hh + 0.12])
    for k in range(90 if not FAST else 60):
        d = rg.standard_normal(3); d /= np.linalg.norm(d)
        V, F = sprinkle(tipc + d * 0.2, d, L=0.42, r=0.012); mg.add(V, F)
    mg.build('hat_tinsel', M_TIN)
    M_EL = pmat('m_elastic', 'f2e8f0', rough=0.6)
    pts = [np.array([hx_ + hr * math.cos(a), hy_ + hr * math.sin(a), TZ + 0.02]) for a in (1.9, 4.4)]
    mid = (pts[0] + pts[1]) / 2 + np.array([-1.3, -0.6, 0])
    cur = [pts[0] * (1 - t) ** 2 + mid * 2 * t * (1 - t) + pts[1] * t * t for t in np.linspace(0, 1, 24)]
    V, F = tube(cur, 0.02, sides=5); mk('hat_elastic', V, F, None, M_EL)
    # --- gift box: wrapped box and lid, ribbon cross and a bow
    col = np.ones((n, n, 3), np.float32) * hx('7fd6c4')
    dd = np.hypot(((U * 8) % 1) - 0.5, ((Vv * 8) % 1) - 0.5) < 0.16
    dd2 = np.hypot(((U * 8 + 0.5) % 1) - 0.5, ((Vv * 8 + 0.5) % 1) - 0.5) < 0.1
    col = np.where(dd[..., None], hx('fff8f0'), col); col = np.where(dd2[..., None], hx('ffd23a'), col)
    M_GIFT = pmat('m_gift', img=image('gift_col', col), rough=0.4, sheen=0.3, coat=0.2)
    M_RIB = pmat('m_ribbon', 'e83a6a', rough=0.18, sheen=0.4, coat=0.5, coat_r=0.1)
    gx, gy = GIFT; grot = 0.35; W_, Hb = 2.6, 2.0
    def box(name, cx, cy, z0, sx, sy, sz, mat, bev=0.04):
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
        for c_ in o.users_collection: c_.objects.unlink(o)
        STAGE.objects.link(o)
        o.scale = (sx, sy, sz); bpy.ops.object.transform_apply(scale=True)
        o.location = (cx, cy, z0 + sz / 2); o.rotation_euler = (0, 0, grot); o.data.materials.append(mat)
        b = o.modifiers.new('bv', 'BEVEL'); b.width = bev; b.segments = 2
        uvl = o.data.uv_layers.new(name='UVMap')
        for loop in o.data.loops:
            v = o.data.vertices[loop.vertex_index].co; nn = o.data.polygons[0].normal
        for poly in o.data.polygons:   # box projection
            nn = poly.normal
            for li in poly.loop_indices:
                v = o.data.vertices[o.data.loops[li].vertex_index].co
                if abs(nn.z) > 0.5: uvl.data[li].uv = (v.x / 2.6 + 0.5, v.y / 2.6 + 0.5)
                elif abs(nn.x) > 0.5: uvl.data[li].uv = (v.y / 2.6 + 0.5, v.z / 2.6 + 0.5)
                else: uvl.data[li].uv = (v.x / 2.6 + 0.5, v.z / 2.6 + 0.5)
        bpy.ops.object.shade_smooth(); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
        return o
    box('gift_box', gx, gy, TZ, W_, W_, Hb, M_GIFT, 0.03)
    box('gift_lid', gx, gy, TZ + Hb - 0.3, W_ + 0.12, W_ + 0.12, 0.42, M_GIFT, 0.04)
    box('gift_rib1', gx, gy, TZ - 0.005, W_ + 0.16, 0.36, Hb + 0.13, M_RIB, 0.02)
    box('gift_rib2', gx, gy, TZ - 0.005, 0.36, W_ + 0.16, Hb + 0.13, M_RIB, 0.02)
    Rg = rotz(grot); top = np.array([gx, gy, TZ + Hb + 0.14]); mg = Merge()
    for sd in (-1, 1):   # bow loops
        pts = []
        for t in np.linspace(0, 1, 22):
            a = t * TAU
            loc = np.array([sd * (0.55 - 0.55 * math.cos(a)) * 1.0, 0.18 * math.sin(a) * 0.4, 0.42 * math.sin(a * 0.5) ** 1.2 * 1.0])
            pts.append(top + Rg @ loc)
        V, F = tube(pts, np.r_[0.12 * np.ones(22)], sides=10, rz=0.35); mg.add(V, F)
    for sd in (-1, 1):   # tails
        pts = [top + Rg @ np.array([sd * 0.2 * t, -0.4 - 0.9 * t, -0.05 - 0.25 * t * t]) for t in np.linspace(0, 1, 8)]
        V, F = tube(pts, 0.11, sides=8, rz=0.3); mg.add(V, F)
    V, F = tube([top + np.array([0, 0, -0.05]), top + np.array([0, 0, 0.15])], 0.16, sides=10); mg.add(V, F)
    mg.build('gift_bow', M_RIB)
    log('hat/gift')
    # --- confetti on the cloth (discs, strips, a few foil)
    ccols = ['ff5a7a', '5ac8ff', 'ffd23a', '7ae07a', 'b07aff', 'ff9a4a']
    mats = [pmat('m_conf_%d' % i, c_, rough=0.45, sheen=0.3) for i, c_ in enumerate(ccols)] + [pmat('m_conf_foil', 'e8c070', rough=0.18, metal=1.0)]
    mgs = [Merge() for _ in mats]; rg = np.random.default_rng(161)
    nconf = 140 if FAST else 420
    k = 0
    while k < nconf:
        x, y = rg.uniform(-HX + 0.6, HX - 0.6), rg.uniform(-HY + 0.6, HY - 0.6)
        if math.hypot(x, y) < 6.6: continue
        if abs(x - GIFT[0]) < 1.8 and abs(y - GIFT[1]) < 1.8: continue
        if math.hypot(x - HAT[0], y - HAT[1]) < 1.1: continue
        R3 = rotz(rg.uniform(0, TAU)) @ rotx(rg.uniform(-0.12, 0.12))
        if rg.random() < 0.6:
            r = rg.uniform(0.09, 0.13); Vc = [np.zeros(3)] + [np.array([r * math.cos(a), r * math.sin(a), 0]) for a in np.linspace(0, TAU, 9)[:-1]]
            Fc = [(0, i, i % 8 + 1) for i in range(1, 9)]
        else:
            l, w = rg.uniform(0.2, 0.32), rg.uniform(0.06, 0.09); bend = rg.uniform(-0.05, 0.05)
            Vc = [np.array([sx * l / 2, sy * w / 2, bend * (sx * 0.5) ** 2 * 4]) for sx in (-1, 0, 1) for sy in (-1, 1)]
            Fc = [(0, 1, 3, 2), (2, 3, 5, 4)]
        zc = TZ + 0.012 + abs(rg.normal(0, 0.006))
        Vc = [np.array([x, y, zc]) + R3 @ v for v in Vc]
        mi = rg.integers(len(mats)) if rg.random() > 0.1 else len(mats) - 1
        mgs[mi].add(Vc, Fc); k += 1
    for i, m in enumerate(mats): mgs[i].build('confetti_%d' % i, m, smooth=False)
    # --- balloons behind the cake, on ribbons tied down to the table
    bcols = ['ff4f7b', '3cb4ff', 'ffd02e', '5fd36a', 'b07aff', 'ff8a3a']
    BAL = [(-10.5, 11.5, 4.6), (-6.4, 14.5, 7.0), (-1.5, 15.5, 6.2), (5.6, 14.6, 7.2), (9.6, 11.2, 4.9), (14.6, 9.6, 6.6)]
    M_STR = pmat('m_ribbon_curl', 'f4f0f4', rough=0.25, metal=0.4)
    sm_ = Merge()
    for k, (x, y, z) in enumerate(BAL):
        M = pmat('m_balloon_%d' % k, bcols[k], rough=0.22, coat=0.6, coat_r=0.08, sss=0.3, sss_r=(1, 0.8, 0.8), sss_s=0.3, sheen=0.15)
        Rb = 1.35; prof = []
        for t in np.linspace(0, 1, 18):
            a = t * math.pi
            r = Rb * math.sin(a) * (1 - 0.12 * (1 - t) ** 2); zz = -Rb * math.cos(a) * 1.18 - 0.25 * (1 - t) ** 3
            prof.append((max(r, 0), zz))
        prof = [(0.0, prof[0][1] - 0.04)] + prof[1:-1] + [(0.0, prof[-1][1])]
        o = lathe(prof, 32, 'balloon_%d' % k, M, xy=(x, y, TZ + z))
        knot = np.array([x, y, TZ + z + prof[0][1]])
        V, F = tube([knot + np.array([0, 0, 0.03]), knot - np.array([0, 0, 0.12]), knot - np.array([0, 0, 0.16])], [0.09, 0.11, 0.04], sides=8)
        mk('balloon_knot_%d' % k, V, F, None, M)
        # curled ribbon down to the table
        end = np.array([x * 0.82, y - 2.0, TZ]); pts = []
        for t in np.linspace(0, 1, 70):
            p = knot * (1 - t) + end * t + np.array([0.18 * math.sin(t * 38 + k), 0.18 * math.cos(t * 38 + k), 0]) * ss(0.0, 0.1, t) * (1 - t * 0.5)
            p[2] += 0.6 * math.sin(math.pi * t) * 0.0
            pts.append(p)
        V, F = tube(pts[::2], 0.02, sides=4, rz=1.0); sm_.add(V, F)
    sm_.build('balloon_ribbons', M_STR)
    log('confetti/balloons')


# ================================================================ background room (render only)
def build_room():
    FLR = pmat('m_floor', '6a4028', rough=0.35)
    mk('floor', [(-200, -200, TZ - 9), (200, -200, TZ - 9), (200, 200, TZ - 9), (-200, 200, TZ - 9)], [(0, 1, 2, 3)], None, FLR, coll=BG)
    WAL = pmat('m_wall', 'f0c0b4', rough=0.8)
    mk('wall', [(-200, 48, TZ - 9), (200, 48, TZ - 9), (200, 48, 80), (-200, 48, 80)], [(0, 1, 2, 3)], None, WAL, coll=BG)
    LB = pmat('m_bulb', 'ffd090', emit='ffb870', emit_s=30.0)
    rb_ = np.random.default_rng(170)
    for row in range(3):
        for k in range(46):
            x = -70 + k * 3.1 + rb_.uniform(-0.6, 0.6); z = 6 + row * 7 + 4 * math.cos(k * 0.45 + row) + rb_.uniform(-0.4, 0.4)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=5, radius=0.35, location=(x, 46.5, z))
            o = bpy.context.object; o.data.materials.append(LB)
            for c_ in o.users_collection: c_.objects.unlink(o)
            BG.objects.link(o)
    # bunting flags strung across the back wall
    mg = Merge(); fc = ['ff5a7a', '5ac8ff', 'ffd23a', '7ae07a', 'b07aff']
    Mf = [pmat('m_flag_%d' % i, c_, rough=0.7, sheen=0.4) for i, c_ in enumerate(fc)]; mgs = [Merge() for _ in Mf]
    for k in range(30):
        x = -45 + k * 3.0; z = 30 - 5 * math.sin((k / 29) * math.pi)
        V = [(x - 1.2, 45, z), (x + 1.2, 45, z), (x, 45, z - 2.4)]; mgs[k % 5].add(V, [(0, 1, 2)])
    for i, m in enumerate(Mf): mgs[i].build('bunting_%d' % i, m, coll=BG, smooth=False)


# ================================================================ build
M_TOP, M_SIDE, M_CUT = build_cake()
build_drip()
build_piping()
build_fruit()
build_sprinkles()
build_candles()
build_stand()
build_cloth()
PLATES = build_props()
build_slice(M_TOP, M_SIDE, M_CUT, PLATES[0])
build_hat_gift_confetti_balloons()
build_room()

def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); n += len(me.loop_triangles); o.evaluated_get(dg).to_mesh_clear()
    return n
STAGE_TRIS = tri_count(STAGE.objects)
log('stage triangles:', STAGE_TRIS)
if '--tris' in sys.argv:
    for o in sorted(STAGE.objects, key=lambda o: -tri_count([o]))[:25]: log('   %-22s %6d' % (o.name, tri_count([o])))
zin = []
for o in STAGE.objects:
    if o.type != 'MESH': continue
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        if math.hypot(w.x, w.y) < RING and w.z > -0.5: zin.append(w.z)
log('relief inside the ring r<4.6: min %.3f max %.3f' % (min(zin), max(zin)))


# ================================================================ characters (same code as stage_render.py)
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
    for r in gr: r.location = (GYOJI[0], GYOJI[1], 0); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
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
            o.matrix_world = Bm @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world; parts.append(o); CHARS.append(o)
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
    mask('kitsune', Vector((GYOJI[0], GYOJI[1], 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)


# ================================================================ lights, camera, render
def setup_light():
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    bgn = world.node_tree.nodes['Background']; bgn.inputs['Strength'].default_value = 0.22
    hdr = os.path.join(SCR, 'ph_cake', 'lebombo_1k.hdr')   # Poly Haven (CC0) interior, for soft reflections only
    if os.path.exists(hdr):
        et = world.node_tree.nodes.new('ShaderNodeTexEnvironment'); et.image = bpy.data.images.load(hdr)
        world.node_tree.links.new(et.outputs['Color'], bgn.inputs['Color'])
    else: bgn.inputs['Color'].default_value = (0.05, 0.03, 0.025, 1)
    def area(name, loc, target, energy, size, color, shape='DISK'):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA')); scn.collection.objects.link(l)
        l.data.energy = energy; l.data.size = size; l.data.shape = shape; l.data.color = color; l.location = loc
        l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return l
    area('Key', (-8, -7, 22), (0.5, 0.5, 0), 7000, 8, (1.0, 0.82, 0.62))
    sp = bpy.data.objects.new('KeySpot', bpy.data.lights.new('KeySpot', 'SPOT')); scn.collection.objects.link(sp)
    sp.data.energy = 110000; sp.data.color = (1.0, 0.8, 0.58); sp.data.spot_size = math.radians(40); sp.data.spot_blend = 0.85
    sp.data.shadow_soft_size = 1.6; sp.location = (-6, -7, 25)
    sp.rotation_euler = (Vector((0.3, 0.6, -1.0)) - sp.location).to_track_quat('-Z', 'Y').to_euler()
    area('Fill', (17, -16, 8), (0, 0, -1), 1800, 18, (0.9, 0.9, 1.0))
    area('Rim', (1, 17, 18), (0, 0, 0), 26000, 12, (1.0, 0.9, 0.82))
    area('Bounce', (0, 0, TZ - 8), (0, 0, 0), 0, 1, (1, 1, 1))
    for i, p in enumerate(FLAMES):
        c = bpy.data.objects.new('CandleL%d' % i, bpy.data.lights.new('CandleL%d' % i, 'POINT')); scn.collection.objects.link(c)
        c.data.energy = 160; c.data.color = (1.0, 0.58, 0.26); c.data.shadow_soft_size = 0.06; c.location = Vector(p)
    # bloom around the flames
    scn.use_nodes = True; nt = scn.node_tree; nt.nodes.clear()
    rl = nt.nodes.new('CompositorNodeRLayers'); gl = nt.nodes.new('CompositorNodeGlare'); co = nt.nodes.new('CompositorNodeComposite')
    gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 4.0; gl.size = 7; gl.mix = -0.55
    nt.links.new(rl.outputs['Image'], gl.inputs['Image']); nt.links.new(gl.outputs['Image'], co.inputs['Image'])

def render(shot):
    cam = bpy.data.objects.get('Cam')
    if not cam:
        cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.dof.use_dof = False; cam.data.clip_end = 500
    if shot == 'game':
        el = math.radians(50); dist = 21
        cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
        cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'close':   # detail check: the cut, rosettes, drips, a candle
        cam.location = (7.6, -7.6, 1.2); cam.data.angle_y = math.radians(24)
        tgt = Vector((3.4, -4.2, -0.6)); cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'ros':
        cam.location = (2.6, -1.4, 1.0); cam.data.angle_y = math.radians(22)
        tgt = Vector((4.96, 0.6, 0.15)); cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
        tgt = Vector((0, 0.8, 0.4))
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (Vector((0, 0, 1.6)) - cam.location).length; cam.data.dof.aperture_fstop = 6.0
    scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'
    scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
    scn.cycles.caustics_reflective = False; scn.cycles.caustics_refractive = False
    scn.cycles.max_bounces = 8; scn.cycles.glossy_bounces = 4; scn.cycles.transparent_max_bounces = 16
    scn.render.resolution_x, scn.render.resolution_y = (640, 360) if FAST else (1280, 720)
    scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'; scn.view_settings.exposure = -0.35
    scn.render.filepath = os.path.join(OUT, 'ex_%s.png' % shot)
    log('rendering', shot); bpy.ops.render.render(write_still=True); log('wrote', scn.render.filepath)

if 'norender' not in sys.argv:
    if 'nochars' not in sys.argv: place_chars()
    setup_light()
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
    glb = os.path.join(OUT, 'cake.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_image_format='AUTO')
    log('exported', glb, '%.1f MB' % (os.path.getsize(glb) / 1e6), 'tris', STAGE_TRIS)
