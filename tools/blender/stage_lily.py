# "LILY PAD" stage, fully modelled: two sumos fight on a giant water-lily pad floating on a clear golden-hour pond.
# Built entirely by script (Blender 4.2, run headless).
#   python tools/blender/stage_lily.py [out_dir] [chars_dir] [shot=game shot=low shot=splash] [samples=64] [pct=100]
#                                      [noren] [nochars] [noexp]
# Writes <out_dir>/lily.glb (the stage only: Z up, metres, origin at the pad centre, top of the pad at Z=0, the water
# surface 0.16 below it, front facing -Y) and renders <out_dir>/ex_game.png (the game camera), ex_low.png (low
# three-quarter) and ex_splash.png (one sumo thrown off the pad into the water, the other standing) with the game's
# characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in their masks.
# Layout (top view, camera on -Y): the big pad is centred on the origin with its V notch at the back-left (outside the
# fighting circle, which shows as a pale bloom ring at RING_R); neighbouring pads all round (some overlapping, some
# with drops), a pink-white water lily in bloom back-right with buds, a frog on a pad on the left, a dragonfly over
# the front-right, reeds and cattails in the back corners, floating petals, stones and weeds on the muddy bottom.
# The glb carries only image textures (numpy-painted or CC0 Poly Haven, <=1024 px, JPEG); the renders add Cycles-only
# touches (procedural ripples, water volume absorption, petal translucency, iridescence, an HDRI sky, dappled light).
# CC0 assets from Poly Haven (polyhaven.com): lakeside_sunrise HDRI, brown_mud_rocks_01 and mossy_rock textures.
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
FLAGS = ('noren', 'nochars', 'noexp')
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in FLAGS and not a.endswith('.py') and not a.startswith('-')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'lily')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
PH = os.path.join(SP, 'lily_ph')            # downloaded Poly Haven files (see the header)
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SHOTS = [a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')] or ['game', 'low']
SAMPLES = int(OPT.get('samples', 64)); PCT = int(OPT.get('pct', 100))
NOREN = 'noren' in sys.argv; NOCHARS = 'nochars' in sys.argv; NOEXP = 'noexp' in sys.argv
SPLASH = 'splash' in SHOTS

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RNG = np.random.default_rng(7)


def ring_r():
    try:
        txt = open(os.path.join(HERE, '..', '..', 'public', 'js', 'config.js')).read()
        return float(re.search(r'S\.RING_R\s*=\s*([\d.]+)', txt).group(1))
    except Exception:
        return 4.6


R = ring_r()            # fighting circle
RD = R + 0.7            # pad radius
WZ = -0.16              # water surface
FLAT = R + 0.25         # the pad is flat out to here, then its rim curls up
NOTCH_A = math.radians(132)   # the notch points back-left
NOTCH_RN = R + 0.1      # notch apex (outside the fighting circle)
NOTCH_TH = math.radians(55)   # half-angle of the V
SPL_A = math.radians(-140); SPL_R = RD + 1.75   # the splash shot: where the thrown sumo hits the water (front-left)
SPL_C = Vector((SPL_R * math.cos(SPL_A), SPL_R * math.sin(SPL_A), WZ))


# ================================================================ helpers
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def fsstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


STAGE = []
def obj(name, me, mats=(), stage=True, loc=None, rot=None, scale=None):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    for m in mats: me.materials.append(m)
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = rot
    if scale is not None: o.scale = scale if hasattr(scale, '__len__') else (scale,) * 3
    if stage: STAGE.append(o)
    return o
def bm_obj(name, bm, mats=(), smooth=40, **kw):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    return obj(name, me, mats, **kw)
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0


def planar_uv(me, S, cx=0.0, cy=0.0):
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    li = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', li)
    u = (co[li, 0] - cx) / (2 * S) + 0.5; v = (co[li, 1] - cy) / (2 * S) + 0.5
    uv.data.foreach_set('uv', np.stack([u, v], 1).ravel())
def box_uv(o, tile=1.0):
    me = o.data; uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u, v = (co.x, co.y) if ax == 2 else (co.y, co.z) if ax == 0 else (co.x, co.z)
            uv.data[li].uv = (u / tile, v / tile)


def curve_mesh(name, pts, radius, mat, res=8, bres=2, stage=True, taper=None, radii=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = radius; cu.bevel_resolution = bres
    cu.resolution_u = res; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for k, (bp, p) in enumerate(zip(sp.bezier_points, pts)):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        if radii: bp.radius = radii[k]
    tmp = bpy.data.objects.new(name + '_c', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    me.materials.clear(); me.shade_smooth()
    return obj(name, me, [mat], stage=stage)


def lathe(name, prof, mats, segs=24, loc=(0, 0, 0), rot=None, stage=True, smooth=60, vuv=True):
    """Profile [(r, z)] from bottom to top; r == 0 is a pole. UV: u around, v along the profile."""
    bm = bmesh.new(); rings = []
    uvl = bm.loops.layers.uv.new('UVMap')
    L = [0.0]
    for a, b in zip(prof[:-1], prof[1:]): L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    for (r, z) in prof:
        if r < 1e-6: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(TAU * i / segs), r * math.sin(TAU * i / segs), z)) for i in range(segs)])
    for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1: vs = (A[0], B[j], B[i]); us = ((i + .5) / segs, (j if j else segs) / segs, i / segs); ks = (k, k + 1, k + 1)
            elif len(B) == 1: vs = (A[i], A[j], B[0]); us = (i / segs, (j if j else segs) / segs, (i + .5) / segs); ks = (k, k, k + 1)
            else: vs = (A[i], A[j], B[j], B[i]); us = (i / segs, (j if j else segs) / segs, (j if j else segs) / segs, i / segs); ks = (k, k, k + 1, k + 1)
            f = bm.faces.new(vs)
            for lp, u, kk in zip(f.loops, us, ks): lp[uvl].uv = (u, L[kk] / L[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    return obj(name, me, mats, stage=stage, loc=loc, rot=rot)


def ellipsoid(name, size, mat, segs=16, rings=10, loc=(0, 0, 0), rot=(0, 0, 0), stage=True):
    prof = [(math.sin(math.pi * k / rings) * size[0], -math.cos(math.pi * k / rings) * size[2]) for k in range(rings + 1)]
    prof[0] = (0, prof[0][1]); prof[-1] = (0, prof[-1][1])
    o = lathe(name, prof, [mat], segs=segs, stage=stage)
    for v in o.data.vertices: v.co.y *= size[1] / size[0]
    o.location = loc; o.rotation_euler = rot
    return o


# ---------------------------------------------------------------- images, noise, materials
def image(name, arr, data=False, alpha=None):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    h, w = arr.shape[:2]; rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    if data: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.file_format = 'PNG'; im.pack(); return im
def load_img(fname, data=False):
    im = bpy.data.images.load(os.path.join(PH, fname)); im.pack()
    if data: im.colorspace_settings.name = 'Non-Color'
    return im
def normal_from_h(h, strength):
    gy, gx = np.gradient(h); n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True); return n * 0.5 + 0.5


def vnoise(n, cells, seed, m=None):
    """Tileable smooth value noise, n x m pixels with cells x cells lattice cells."""
    m = m or n
    g = np.random.default_rng(seed).random((cells, cells))
    y = np.arange(n) * cells / n; x = np.arange(m) * cells / m
    y0 = np.floor(y).astype(int); x0 = np.floor(x).astype(int); fy = y - y0; fx = x - x0
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % cells; x1 = (x0 + 1) % cells; y0 %= cells; x0 %= cells
    a = g[np.ix_(y0, x0)]; b = g[np.ix_(y0, x1)]; c = g[np.ix_(y1, x0)]; d = g[np.ix_(y1, x1)]
    fx = fx[None, :]; fy = fy[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
def fbm(n, cells, octaves, seed, gain=0.5, m=None):
    t = 0; amp = 1; s = 0
    for k in range(octaves):
        t = t + amp * vnoise(n, cells * 2 ** k, seed + k, m); s += amp; amp *= gain
    return t / s
def voronoi(n, cells, seed):
    """F1, F2 distances (in cell units) of a jittered grid, tileable."""
    pts = np.random.default_rng(seed).random((cells, cells, 2))
    cs = n / cells; p = (np.arange(n) + 0.5) / cs
    Y, X = np.meshgrid(p, p, indexing='ij'); ci = np.floor(Y).astype(int); cj = np.floor(X).astype(int)
    ds = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            a = ci + dy; b = cj + dx; q = pts[a % cells, b % cells]
            ds.append(np.hypot(a + q[..., 0] - Y, b + q[..., 1] - X))
    ds = np.sort(np.stack(ds), 0); return ds[0], ds[1]


BSDF = {}
MATS = {}
def mat(name, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tcol=None, trough=None, tnrm=None, nstr=1.0, emit=None, estr=0.0,
        coat=0.0, coat_r=0.05, spec=0.5, trans=0.0, ior=1.45, sss=0.0, sss_r=(1, 0.5, 0.2), sss_s=0.05, uvmap=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']; BSDF[name] = bs
    MATS[name] = m
    bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal; bs.inputs['Specular IOR Level'].default_value = spec
    bs.inputs['IOR'].default_value = ior
    if trans: bs.inputs['Transmission Weight'].default_value = trans
    if coat: bs.inputs['Coat Weight'].default_value = coat; bs.inputs['Coat Roughness'].default_value = coat_r
    if sss:
        bs.inputs['Subsurface Weight'].default_value = sss; bs.inputs['Subsurface Radius'].default_value = sss_r
        bs.inputs['Subsurface Scale'].default_value = sss_s
    def tex(im):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = im; return n
    if tcol: nt.links.new(tex(tcol).outputs['Color'], bs.inputs['Base Color'])
    if trough:
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tex(trough).outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bs.inputs['Roughness'])
    if tnrm:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(tex(tnrm).outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    if emit: bs.inputs['Emission Color'].default_value = (*emit, 1); bs.inputs['Emission Strength'].default_value = estr
    return m


def rough_img(name, arr):
    """A glTF-style metallic-roughness image (roughness in G, metal 0 in B)."""
    a = np.zeros(arr.shape + (3,), np.float32); a[..., 0] = 1; a[..., 1] = np.clip(arr, 0, 1); return image(name, a, data=True)


N = 1024
# ================================================================ textures
TS = RD + 0.15          # half-size of the main pad's planar texture square (metres)


def pad_veins(n, Rpx, cx, cy, nprim, seed, w0=3.0, w1=1.0):
    """Radiating, forking veins: returns intensity 0..1 (n x n)."""
    rng = np.random.default_rng(seed)
    V = np.zeros((n, n), np.float32)
    def stamp(px, py, w, st=1.0):
        k = int(math.ceil(2.6 * w)) + 1
        x0, x1 = max(0, int(px) - k), min(n, int(px) + k + 1); y0, y1 = max(0, int(py) - k), min(n, int(py) + k + 1)
        if x0 >= x1 or y0 >= y1: return
        xs = np.arange(x0, x1) + 0.5 - px; ys = np.arange(y0, y1) + 0.5 - py
        g = st * np.exp(-(ys[:, None] ** 2 + xs[None, :] ** 2) / (w * w))
        np.maximum(V[y0:y1, x0:x1], g, out=V[y0:y1, x0:x1])
    forks = (0.3, 0.58, 0.82)
    for i in range(nprim):
        a0 = TAU * (i + rng.uniform(-0.25, 0.25)) / nprim
        branches = [(a0, 0.0, 1)]            # base angle, fork offset accumulator sign tree
        spread = TAU / nprim
        ph = rng.uniform(0, TAU); wob = rng.uniform(0.02, 0.05); vs = rng.uniform(0.55, 1.0)
        fr = [f * Rpx * rng.uniform(0.9, 1.1) for f in forks]
        paths = [[]]
        # walk outwards; at each fork radius every branch splits in two that drift apart smoothly
        def ang(rho, code):
            a = a0 + wob * math.sin(rho * 0.012 + ph) + 0.06 * math.sin(rho * 0.03 + ph * 2) * (rho / Rpx)
            for lvl, bit in enumerate(code):
                d = spread * 0.25 / (2 ** lvl) * (1.0 if bit else -1.0)
                a += d * fsstep(fr[lvl], fr[lvl] + 70, rho)
            return a
        codes = [()]
        rho = 6.0
        while rho < Rpx * 1.02:
            lvl = sum(1 for f in fr if rho >= f)
            while len(codes[0]) < lvl: codes = [c + (b,) for c in codes for b in (0, 1)]
            w = w0 + (w1 - w0) * (rho / Rpx) ** 0.7
            w = w / (1 + 0.25 * len(codes[0]))
            for c in codes:
                a = ang(rho, c); stamp(cx + rho * math.cos(a), cy + rho * math.sin(a), max(0.7, w), vs * (0.75 ** len(c)) * (0.8 + 0.2 * math.sin(rho * 0.05 + ph)))
            rho += 0.8
    return V


def notch_dist(X, Y, A, rn, th):
    """Signed-ish distance (m) from points to the notch's V edges (positive outside the cut)."""
    ax = np.array([math.cos(A), math.sin(A)]); P0 = rn * ax
    best = np.full(X.shape, 1e9)
    for s in (-1, 1):
        d = np.array([math.cos(A + s * th), math.sin(A + s * th)])
        px = X - P0[0]; py = Y - P0[1]; t = np.maximum(px * d[0] + py * d[1], 0)
        best = np.minimum(best, np.hypot(px - t * d[0], py - t * d[1]))
    return best


def tex_pad(n, S, padR, ring=None, seed=1, notch=None, old=0.0):
    """Top of a lily pad: colour, roughness, normal. Planar over [-S, S]^2 metres."""
    p = (np.arange(n) + 0.5) / n * 2 * S - S
    Y, X = np.meshgrid(p, p, indexing='ij'); rho = np.hypot(X, Y); phi = np.arctan2(Y, X)
    px_m = n / (2 * S)
    Rpx = padR * px_m
    V = pad_veins(n, Rpx, n / 2, n / 2, 22 if padR > 3 else 16, seed, w0=5.0 if padR > 3 else 3.0, w1=1.8)
    F1, F2 = voronoi(n, 72 if padR > 3 else 48, seed + 3)
    reti = np.exp(-((F2 - F1) / 0.06) ** 2)                    # fine reticulate veinlets
    mott = fbm(n, 6, 5, seed + 5); mott2 = fbm(n, 24, 3, seed + 9)
    t = rho / padR
    dark, mid, light = np.array(lin('2f6a1e')), np.array(lin('55982f')), np.array(lin('86b844'))
    c = dark + (mid - dark) * np.clip(0.55 + 1.3 * (mott - 0.5) + 0.25 * (1 - t), 0, 1)[..., None]
    c = c + (light - c) * (0.3 * sstep(0.6, 0.85, fbm(n, 4, 4, seed + 7)))[..., None]
    c = c * (0.88 + 0.24 * mott2[..., None])
    # warmer, yellower towards the rim; a red-brown margin
    rimy = sstep(0.86, 0.99, t)
    c = c + (np.array(lin('8a9a3a')) - c) * (0.35 * rimy)[..., None]
    marg = sstep(padR - 0.07 * (padR / RD) ** 0.5, padR - 0.01, rho)
    if notch is not None:
        nd = notch_dist(X, Y, *notch); marg = np.maximum(marg, np.exp(-nd / 0.03) * sstep(notch[1] - 0.05, notch[1] + 0.1, rho))
    c = c + (np.array(lin('7a2c22')) - c) * (0.8 * marg)[..., None]
    # veins: pale yellow-green, thinner and fainter towards the rim
    vcol = np.array(lin('8fb85a'))
    vi = np.clip(V * 0.42, 0, 1) * (1 - 0.35 * t)
    c = c + (vcol - c) * vi[..., None]
    c = c + (np.array(lin('6a9a3a')) - c) * (0.22 * reti)[..., None]
    # sparse brown freckles and a few sun-scorched patches near the rim
    fr = vnoise(n, 160, seed + 11); fr = sstep(0.86, 0.93, fr) * sstep(0.35, 0.9, t)
    c = c + (np.array(lin('5a4a1c')) - c) * (0.55 * fr)[..., None]
    if old:
        sc = sstep(0.55, 0.8, fbm(n, 5, 4, seed + 13)) * sstep(0.5, 1.0, t)
        c = c + (np.array(lin('a08a34')) - c) * (old * sc)[..., None]
    # petiole spot in the centre
    c = c + (np.array(lin('9ab85a')) - c) * (0.6 * np.exp(-(rho / (0.06 * padR)) ** 2))[..., None]
    rough = 0.38 + 0.12 * mott2 + 0.08 * vi + 0.25 * fr + 0.3 * marg + 0.1 * sstep(0.6, 0.8, fbm(n, 8, 3, seed + 17))
    if ring is not None:   # the fighting circle: a pale waxy bloom band with a marginal vein in it
        dr = rho - ring
        band = np.exp(-(dr / 0.035) ** 2); halo = np.exp(-(dr / 0.16) ** 2) * (0.85 + 0.3 * (mott2 - 0.5))
        c = c + (np.array(lin('bcd68c')) - c) * np.clip(0.5 * band + 0.2 * halo, 0, 1)[..., None]
        rough = rough + 0.12 * halo
        V = np.maximum(V, band * 0.9)
    # height: veins sunk into the blade, blistered between them, fine cell domes
    h = -1.4 * V - 0.1 * reti + 0.05 * (1 - F1) + 0.8 * mott2 * 0.3
    nrm = normal_from_h(h, 1.6 * (n / 1024))
    c = np.where((rho > padR + 0.01)[..., None], np.array(lin('7a2c22')), c)
    return c, np.clip(rough, 0.05, 1), nrm


def tex_under(n, S, padR, seed=2):
    """Underside / curled rim: reddish purple with radial ribs, greener on the lip."""
    p = (np.arange(n) + 0.5) / n * 2 * S - S
    Y, X = np.meshgrid(p, p, indexing='ij'); rho = np.hypot(X, Y); phi = np.arctan2(Y, X)
    nz = fbm(n, 8, 4, seed); nz2 = fbm(n, 40, 2, seed + 1)
    ribs = 0.5 + 0.5 * np.cos(phi * 120 + 3.0 * (nz - 0.5))
    ribs = ribs ** 4
    base = np.array(lin('702238')); hi = np.array(lin('9a4a5a')); lip = np.array(lin('6a5a2a'))
    c = base * (0.75 + 0.5 * nz[..., None]) * (0.85 + 0.3 * nz2[..., None]) + (hi - base) * (0.3 * ribs)[..., None]
    c = c + (lip - c) * sstep(padR - 0.005, padR + 0.03, rho)[..., None]
    rough = 0.35 + 0.15 * nz2 - 0.1 * ribs
    h = ribs * 0.6 + 0.3 * nz2
    return c, rough, normal_from_h(h, 1.2)


print('painting textures...')
c, r_, n_ = tex_pad(N, TS, RD, ring=R, seed=1, notch=(NOTCH_A, NOTCH_RN, NOTCH_TH))
IM_PAD = (image('pad_col', c), rough_img('pad_rgh', r_), image('pad_nrm', n_, data=True))
c, r_, n_ = tex_under(512, TS, RD)
IM_UNDER = (image('under_col', c), rough_img('under_rgh', r_), image('under_nrm', n_, data=True))
c, r_, n_ = tex_pad(512, 1.06, 1.0, seed=21, notch=(0.0, 0.0, NOTCH_TH))
IM_SPAD = (image('spad_col', c), rough_img('spad_rgh', r_), image('spad_nrm', n_, data=True))
c, r_, n_ = tex_pad(512, 1.06, 1.0, seed=33, notch=(0.0, 0.0, NOTCH_TH), old=0.9)
IM_OPAD = (image('opad_col', c), rough_img('opad_rgh', r_), image('opad_nrm', n_, data=True))


def tex_petal(n=256, m=512):
    v = (np.arange(m) + 0.5) / m; u = (np.arange(n) + 0.5) / n
    V_, U_ = np.meshgrid(v, u, indexing='ij'); ue = np.abs(U_ - 0.5) * 2
    white, pink, deep = np.array(lin('fbf3ee')), np.array(lin('f4a6c4')), np.array(lin('e0608f'))
    t = np.clip(V_ ** 1.6 * 1.2 + 0.25 * ue * V_, 0, 1)
    c = white + (pink - white) * t[..., None]
    c = c + (deep - c) * (sstep(0.75, 1.0, V_) * 0.5)[..., None]
    c = c + (np.array(lin('f2dc7a')) - c) * (sstep(0.12, 0.0, V_) * 0.7)[..., None]    # yellowish base
    veins = (0.5 + 0.5 * np.cos(U_ * 70 + 2 * np.sin(V_ * 6))) ** 8 * sstep(0.05, 0.4, V_)
    c = c * (1 - 0.06 * veins[..., None])
    return c
IM_PETAL = image('petal_col', tex_petal())


def tex_frog(n=512):
    m = n // 2
    nz = fbm(m, 6, 4, 41, m=n); sp = vnoise(m, 22, 42, m=n); sp2 = vnoise(m, 40, 43, m=n)
    v = (np.arange(m) + 0.5) / m
    top = np.array(lin('6f9e34')); top2 = np.array(lin('4f7f26')); belly = np.array(lin('e6dca0'))
    c = top + (top2 - top) * nz[..., None]
    spots = np.maximum(sstep(0.7, 0.76, sp), sstep(0.78, 0.83, sp2))
    c = c + (np.array(lin('2a3a14')) - c) * (0.85 * spots)[..., None]
    c = c + (belly - c) * sstep(0.42, 0.3, v)[:, None, None]
    return c
IM_FROG = image('frog_col', tex_frog())


def tex_wing(n=512, m=128):
    u = (np.arange(n) + 0.5) / n; v = (np.arange(m) + 0.5) / m
    V_, U_ = np.meshgrid(v, u, indexing='ij')
    long = (0.5 + 0.5 * np.cos(V_ * TAU * 9 + 0.6 * np.sin(U_ * 7))) ** 30
    F1, F2 = voronoi(n, 28, 51); F1 = F1[:m]; F2 = F2[:m]
    cross = np.exp(-((F2 - F1) / 0.035) ** 2)
    vein = np.clip(0.8 * long + 0.35 * cross + np.exp(-((V_ - 0.92) / 0.03) ** 2), 0, 1)
    c = np.array(lin('f6fafa')) + (np.array(lin('3a2a1a')) - np.array(lin('f6fafa'))) * vein[..., None]
    c = c + (np.array(lin('d8a040')) - c) * (sstep(0.18, 0.0, U_) * 0.6)[..., None]                 # amber base
    stig = np.exp(-(((U_ - 0.86) / 0.04) ** 2 + ((V_ - 0.85) / 0.08) ** 2))
    c = c + (np.array(lin('2a1a0e')) - c) * np.clip(stig * 1.5, 0, 1)[..., None]                   # pterostigma
    return c
IM_WING = image('wing_col', tex_wing())

# water ripple normal map for the glb (the render uses procedural ripples instead): planar over [-WS, WS]
WS = 40.0
def tex_water(n=1024):
    p = (np.arange(n) + 0.5) / n * 2 * WS - WS
    Y, X = np.meshgrid(p, p, indexing='ij'); rho = np.hypot(X, Y)
    h = 0.6 * np.sin(TAU * (rho - RD) / 0.95) * np.exp(-np.maximum(rho - RD, 0) / 5.0) * (rho > RD - 0.3)
    h = h + 0.8 * (fbm(n, 24, 4, 61) - 0.5)
    return normal_from_h(h, 1.2)
IM_WATER_N = image('water_nrm', tex_water(), data=True)


# ================================================================ materials
M_PAD = mat('PadTop', rough=0.36, tcol=IM_PAD[0], trough=IM_PAD[1], tnrm=IM_PAD[2], nstr=0.45, coat=0.35, coat_r=0.12,
            sss=0.08, sss_r=(0.3, 1.0, 0.2), sss_s=0.04)
M_UNDER = mat('PadUnder', rough=0.4, tcol=IM_UNDER[0], trough=IM_UNDER[1], tnrm=IM_UNDER[2], nstr=0.8, coat=0.2, coat_r=0.2,
               sss=0.2, sss_r=(1.0, 0.3, 0.3), sss_s=0.05)
M_SPAD = mat('PadSmall', rough=0.3, tcol=IM_SPAD[0], trough=IM_SPAD[1], tnrm=IM_SPAD[2], nstr=0.6, coat=0.35, coat_r=0.12)
M_OPAD = mat('PadOld', rough=0.35, tcol=IM_OPAD[0], trough=IM_OPAD[1], tnrm=IM_OPAD[2], nstr=0.6, coat=0.25, coat_r=0.15)
M_DROP = mat('Droplet', (1, 1, 1), 0.0, trans=1.0, ior=1.33, spec=0.5)
M_WATER = mat('Water', lin('dcefe6'), 0.04, trans=1.0, ior=1.333, tnrm=IM_WATER_N, nstr=0.25)
M_MUD = mat('PondBed', tcol=load_img('brown_mud_rocks_01_diff_1k.jpg'), trough=None,
            tnrm=load_img('brown_mud_rocks_01_nor_gl_1k.jpg', True), nstr=1.0, rough=0.8)
M_ROCK = mat('Stone', tcol=load_img('mossy_rock_diff_1k.jpg'), tnrm=load_img('mossy_rock_nor_gl_1k.jpg', True), nstr=1.0, rough=0.7)
M_STEM = mat('Stem', lin('4a5a22'), 0.45, sss=0.1, sss_r=(0.4, 1.0, 0.2))
M_STEMR = mat('StemRed', lin('5a3a22'), 0.45)
M_WEED = mat('Weed', lin('5a7a22'), 0.6, sss=0.15, sss_r=(0.4, 1.0, 0.2))
M_PETAL = mat('Petal', rough=0.38, tcol=IM_PETAL, sss=0.25, sss_r=(1.0, 0.6, 0.6), sss_s=0.03, spec=0.4)
M_SEPAL = mat('Sepal', lin('6a4a3a'), 0.4, coat=0.2)
M_STAMEN = mat('Stamen', lin('f2b80e'), 0.45, sss=0.2, sss_r=(1.0, 0.7, 0.2))
M_STIGMA = mat('Stigma', lin('e6c020'), 0.5)
M_BUD = mat('Bud', lin('7a8a3a'), 0.35, coat=0.3, sss=0.1)
M_BUDTIP = mat('BudTip', lin('f0a0be'), 0.4, sss=0.2, sss_r=(1, .6, .6))
M_REED = mat('Reed', lin('6f8a32'), 0.55, sss=0.1, sss_r=(0.5, 1.0, 0.2))
M_REEDY = mat('ReedDry', lin('a8924a'), 0.6)
M_CATTAIL = mat('Cattail', lin('4a2c16'), 0.9)
M_DFLY = mat('DragonBody', lin('1f4f5a'), 0.3, metal=0.35, coat=0.6, coat_r=0.05)
M_DEYE = mat('DragonEye', lin('1a3a6a'), 0.12, coat=1.0, coat_r=0.02)
M_DLEG = mat('DragonLeg', lin('141414'), 0.4)
M_WING = mat('Wing', rough=0.05, tcol=IM_WING, trans=1.0, ior=1.3, spec=0.5)
M_FROG = mat('Frog', rough=0.32, tcol=IM_FROG, coat=0.6, coat_r=0.08, sss=0.15, sss_r=(0.5, 1.0, 0.3), sss_s=0.04)
M_FEYE = mat('FrogEye', lin('b0782a'), 0.1, coat=1.0, coat_r=0.01)
M_PUPIL = mat('FrogPupil', lin('050505'), 0.05, coat=1.0, coat_r=0.01)


# ================================================================ the lily pad builder
def notch_gap(r, rn, th):
    """Half-angle (rad) of the notch's gap at radius r for a V with apex at rn and half-angle th."""
    if r <= rn + 1e-6: return 0.0
    c = math.cos(th); s = -rn * c + math.sqrt(max(0.0, rn * rn * c * c - rn * rn + r * r))
    return math.atan2(s * math.sin(th), rn + s * c)


def build_pad(name, padR, mats, segs, top_rings, rim_rings, ztop, under, notch_a, rn, th, uvS, flat_frac=0.92,
              loc=(0, 0, 0), rot=0.0, stage=True):
    """A notched lily pad as a closed solid. ztop(r, a) gives the top surface height; `under` is a list of
    (r, z-or-None, dz) points for the lip, outer face and bottom (z None -> ztop at the rim plus dz), outermost first."""
    flat = padR * flat_frac
    rs = [padR * (k / top_rings) ** 0.8 * flat_frac for k in range(top_rings + 1)]
    rs += [flat + (padR - flat) * (k / rim_rings) for k in range(1, rim_rings + 1)]
    if rn < padR and rn not in rs:
        rs = sorted(set(rs + [rn]))
    prof = [(r, 'top', 0.0) for r in rs] + [(r, z, dz) for (r, z, dz) in under]
    # make sure the bottom also has a ring at the notch apex
    bot_rs = [p[0] for p in under if p[1] is not None]
    if rn < padR and rn not in bot_rs:
        # insert into the bottom part (descending radii)
        zb = [p for p in under if p[1] is not None]
        for k in range(len(zb) - 1):
            if zb[k][0] > rn > zb[k + 1][0]:
                f = (zb[k][0] - rn) / (zb[k][0] - zb[k + 1][0]); zz = zb[k][1] + (zb[k + 1][1] - zb[k][1]) * f
                i = prof.index(zb[k + 1]); prof.insert(i, (rn, zz, 0.0)); break
    bm = bmesh.new(); rings = []; kinds = []
    for (r, z, dz) in prof:
        if r < 1e-6:
            zz = ztop(0.0, 0.0) if z == 'top' else z
            rings.append([bm.verts.new((0, 0, zz))]); kinds.append(z == 'top'); continue
        g = notch_gap(r, rn, th)
        ring = []
        for j in range(segs + 1):
            a = notch_a + g + (TAU - 2 * g) * j / segs
            if z == 'top': zz = ztop(r, a)
            elif z is None: zz = ztop(padR, a) + dz
            else: zz = z
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), zz)))
        rings.append(ring); kinds.append(z == 'top')
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        mi = 0 if kinds[k] else 1     # (rounding over the lip is still the top skin)
        for j in range(segs):
            if len(A) == 1: f = bm.faces.new((A[0], B[j], B[j + 1]))
            elif len(B) == 1: f = bm.faces.new((A[j], B[0], A[j + 1]))
            else: f = bm.faces.new((A[j], B[j], B[j + 1], A[j + 1]))
            f.material_index = mi
    # notch caps: the open rings' end vertices, in profile order, closed through the apex
    if rn < padR:
        open_idx = [k for k, (r, z, dz) in enumerate(prof) if r >= rn - 1e-6]
        for side in (0, segs):
            vs = [rings[k][side] for k in open_idx]
            try:
                f = bm.faces.new(vs if side else vs[::-1]); f.material_index = 1
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(70))
    planar_uv(me, uvS)
    return obj(name, me, mats, stage=stage, loc=loc, rot=(0, 0, rot))


# ---------------------------------------------------------------- the big pad
RIM_UP = 0.2
WAVES = [(0.07, 5, 0.7), (0.04, 8, 2.1), (0.025, 13, 4.0), (0.012, 21, 1.3)]
def ztop_main(r, a):
    t = max(0.0, (r - FLAT) / (RD - FLAT))
    z = RIM_UP * t ** 2.0 + t * t * sum(A * math.sin(k * a + p) for A, k, p in WAVES)
    # gentle relief inside (<= ~1 cm): broad swells between the veins
    z += 0.006 * math.sin(3 * a + 1.0 + r * 0.9) * math.sin(r * 1.7) * min(1.0, r / 1.5)
    # the notch edges lift a little, like a real pad's
    ca = math.cos(a - NOTCH_A)
    if r > NOTCH_RN - 0.2 and ca > 0.7:
        g = notch_gap(max(r, NOTCH_RN), NOTCH_RN, NOTCH_TH); da = abs(math.atan2(math.sin(a - NOTCH_A), ca))
        d = max(0.0, (da - g)) * r
        z += 0.1 * math.exp(-d / 0.35) * fsstep(NOTCH_RN - 0.05, NOTCH_RN + 0.4, r)
    return z


print('building the pad...')
UNDER_MAIN = [(RD + 0.025, None, -0.02), (RD + 0.03, None, -0.055), (RD + 0.005, None, -0.09), (RD - 0.07, -0.03, 0),
              (RD - 0.16, -0.13, 0), (RD - 0.26, -0.22, 0), (RD - 0.42, -0.3, 0), (RD - 0.75, -0.35, 0), (2.5, -0.36, 0),
              (0.0, -0.36, 0)]
PAD = build_pad('LilyPad', RD, [M_PAD, M_UNDER], 256, 18, 9, ztop_main, UNDER_MAIN, NOTCH_A, NOTCH_RN, NOTCH_TH, TS,
                flat_frac=FLAT / RD)


# ---------------------------------------------------------------- the neighbouring pads
def small_pad(name, x, y, r, rot, m, z=WZ + 0.015, up=0.06, tilt=(0, 0), segs=None, seed=0, notch_th=None):
    rr = np.random.default_rng(seed)
    wv = [(rr.uniform(0.3, 0.7) * up, k, rr.uniform(0, TAU)) for k in (3, 5, 9)]
    th = notch_th or math.radians(rr.uniform(14, 26))
    rn = 0.0
    def zt(rad, a):
        t = rad / r; u = max(0.0, (t - 0.8) / 0.2)
        return up * u * u * (1 + sum(A * math.sin(k * a + p) for A, k, p in wv) / max(up, 1e-3)) + 0.004 * r * math.sin(2 * a + t * 3)
    th_ = 0.03 * min(1.0, r / 2)
    under = [(r * 1.004, None, -th_ * 0.3), (r * 0.995, None, -th_), (r * 0.9, -th_ - 0.02, 0), (0.0, -th_ - 0.03, 0)]
    segs = segs or int(np.clip(40 + r * 14, 40, 96))
    o = build_pad(name, r, [m, M_UNDER], segs, 5, 3, zt, under, 0.0, rn + 0.001, th, r * 1.06, flat_frac=0.8)
    # retarget the under material's UV-independent look: the small pads' undersides reuse the same image
    o.location = (x, y, z); o.rotation_euler = (tilt[0], tilt[1], rot)
    return o


PADS = []
PAD_SPECS = [  # x, y, radius, rotation, old?, z-lift (overlaps), tilt
    (-9.2, 4.2, 2.6, 0.4, False, 0.0, (0, 0)),       # the frog's pad (left)
    (-11.6, 7.6, 1.5, 2.2, True, 0.04, (0.04, -0.03)),  # overlapping the frog's pad
    (9.6, -3.4, 2.2, 3.6, False, 0.0, (0, 0)),       # front-right
    (11.4, -1.4, 1.2, 1.0, False, 0.035, (0.03, 0.05)),  # overlapping it
    (-8.6, -4.6, 2.0, 5.0, True, 0.0, (0, 0)),       # front-left
    (-6.8, -7.4, 1.0, 0.6, False, 0.0, (0, 0)),
    (2.6, 10.6, 2.9, 1.9, False, 0.0, (0, 0)),       # behind
    (6.4, 8.6, 1.4, 4.2, True, 0.0, (0, 0)),
    (-3.6, 9.4, 1.6, 2.8, False, 0.03, (0.0, 0.04)),
    (12.6, 6.4, 2.4, 0.2, False, 0.0, (0, 0)),       # under the flower
    (15.4, 2.6, 1.3, 2.4, True, 0.0, (0, 0)),
    (-14.6, 1.2, 2.2, 3.3, False, 0.0, (0, 0)),
    (-16.4, -4.0, 1.4, 1.2, True, 0.0, (0, 0)),
    (17.0, -6.4, 2.0, 5.5, False, 0.0, (0, 0)),
    (5.6, -9.4, 1.5, 0.9, True, 0.0, (0, 0)),
    (-1.6, -9.8, 1.1, 4.4, False, 0.0, (0, 0)),
]
print('building the small pads...')
for k, (x, y, r, rt, old, dz, tl) in enumerate(PAD_SPECS):
    PADS.append(small_pad('Pad%02d' % k, x, y, r, rt, M_OPAD if old else M_SPAD, z=WZ + 0.015 + dz, up=0.05 + 0.03 * r,
                          tilt=tl, seed=100 + k))


# ---------------------------------------------------------------- droplets on the waxy surfaces
DROP_ME = None
def drop_mesh():
    """A bead of water: a sessile drop (flattened sphere cut a little below its equator)."""
    global DROP_ME
    if DROP_ME: return DROP_ME
    prof = [(0.0, 0.0), (0.9, 0.0), (1.0, 0.22), (0.9, 0.5), (0.6, 0.76), (0.0, 0.88)]
    o = lathe('drop_tmp', prof, [M_DROP], segs=10, stage=False, smooth=80)
    DROP_ME = o.data; bpy.data.objects.remove(o); return DROP_ME


def drops_on(target_xy_z, n, rmin, rmax, seed, name, zfun, xform=None, avoid=None):
    rr = np.random.default_rng(seed); me = drop_mesh()
    bm = bmesh.new(); out = []
    for k in range(n):
        x, y = target_xy_z(rr)
        if avoid and avoid(x, y): continue
        s = rmin * (rmax / rmin) ** (rr.random() ** 1.8)
        out.append((x, y, s))
    tm = bmesh.new(); tm.from_mesh(me)
    for (x, y, s) in out:
        z = zfun(x, y)
        sx = s * rr.uniform(0.85, 1.25)
        M = Matrix.Translation((x, y, z + 0.003)) @ Matrix.Rotation(rr.uniform(0, TAU), 4, 'Z') @ Matrix.Diagonal((sx, s, s * rr.uniform(0.45, 0.7), 1))
        if xform: M = xform @ M
        tmp = tm.copy(); bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts)
        me2 = bpy.data.meshes.new('t'); tmp.to_mesh(me2); tmp.free(); bm.from_mesh(me2); bpy.data.meshes.remove(me2)
    tm.free()
    o = bm_obj(name, bm, [M_DROP], smooth=80)
    return o


def main_z(x, y):
    return ztop_main(math.hypot(x, y), math.atan2(y, x))


def main_drop_xy(rr):
    while True:
        if rr.random() < 0.7: r = RD * math.sqrt(rr.uniform(0.62, 0.985))
        else: r = RD * math.sqrt(rr.uniform(0.0, 0.62))
        a = rr.uniform(0, TAU)
        if abs(math.atan2(math.sin(a - NOTCH_A), math.cos(a - NOTCH_A))) < notch_gap(r, NOTCH_RN, NOTCH_TH) + 0.05: continue
        return r * math.cos(a), r * math.sin(a)


def avoid_feet(x, y):   # keep the sumos' footprint and the gyoji's spot dry
    return (math.hypot(x + 1.0, y + 0.15) < 1.3 or math.hypot(x - 1.0, y - 0.15) < 1.3 or math.hypot(x - 0.4, y - 5.0) < 0.6)


print('drops...')
DROPS = drops_on(main_drop_xy, 135, 0.025, 0.11, 5, 'Drops', main_z, avoid=avoid_feet)
# a few bigger beads pooled in the curl of the rim
def rim_xy(rr):
    while True:
        a = rr.uniform(0, TAU)
        if abs(math.atan2(math.sin(a - NOTCH_A), math.cos(a - NOTCH_A))) < NOTCH_TH + 0.25: continue
        r = rr.uniform(FLAT + 0.05, RD - 0.12); return r * math.cos(a), r * math.sin(a)
DROPS2 = drops_on(rim_xy, 22, 0.06, 0.14, 9, 'DropsRim', main_z)
for k, o in enumerate(PADS[:12:2]):   # some on the neighbouring pads
    sp = PAD_SPECS[k * 2]; r = sp[2]
    def xy(rr, r=r):
        a = rr.uniform(0.35, TAU - 0.35); rad = r * math.sqrt(rr.uniform(0.05, 0.85)); return rad * math.cos(a), rad * math.sin(a)
    d = drops_on(xy, int(6 + r * 5), 0.02, 0.08, 300 + k, 'DropsP%d' % k, lambda x, y: 0.0, xform=o.matrix_basis.copy())


# ================================================================ water, bed, stones, weeds, stems
print('water & pond bed...')
def water_surface():
    bm = bmesh.new()
    radii = [RD - 0.6 + 0.15 * k for k in range(30)]
    while radii[-1] < 130: radii.append(radii[-1] * 1.13)
    segs = 128; rings = []
    for r in radii:
        ring = []
        for j in range(segs):
            a = TAU * j / segs
            z = WZ + 0.012 * math.sin(TAU * (r - RD) / 1.1 + 0.3 * math.sin(3 * a)) * math.exp(-max(r - RD, 0) / 4) \
                + 0.01 * math.sin(0.35 * r * math.cos(a) + 1.0) * math.sin(0.27 * r * math.sin(a) + 2.0) * min(1, r / 8)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for A, B in zip(rings[:-1], rings[1:]):
        for j in range(segs):
            k = (j + 1) % segs; bm.faces.new((A[j], A[k], B[k], B[j]))
    centre = bm.faces.new([v for v in rings[0]])
    bmesh.ops.triangulate(bm, faces=[centre])
    bm.normal_update()
    down = [f for f in bm.faces if f.normal.z < 0]
    if down: bmesh.ops.reverse_faces(bm, faces=down)
    me = bpy.data.meshes.new('Water'); bm.to_mesh(me); bm.free(); me.shade_smooth()
    planar_uv(me, WS)
    return obj('Water', me, [M_WATER])
WATER = water_surface()


def bed_z(x, y):
    r = math.hypot(x, y)
    z = -2.3 + 0.35 * math.sin(x * 0.21 + 1) * math.cos(y * 0.17) + 0.15 * math.sin(x * 0.7 + y * 0.5)
    # shallower towards the reedy corners and far away
    for (cx, cy, rr) in ((-15.5, 11.5, 7), (16, 11, 7), (-14, -9, 6)):
        z += 1.4 * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (rr * rr))
    z += 0.9 * fsstep(22, 45, r)
    return z


def pond_bed():
    n = 72; L = 46.0
    bm = bmesh.new(); vs = []
    for i in range(n + 1):
        row = []
        for j in range(n + 1):
            x = -L + 2 * L * j / n; y = -L + 2 * L * i / n
            row.append(bm.verts.new((x, y, bed_z(x, y))))
        vs.append(row)
    for i in range(n):
        for j in range(n): bm.faces.new((vs[i][j], vs[i][j + 1], vs[i + 1][j + 1], vs[i + 1][j]))
    me = bpy.data.meshes.new('PondBed'); bm.to_mesh(me); bm.free(); me.shade_smooth()
    o = obj('PondBed', me, [M_MUD]); box_uv(o, 3.2); return o
BED = pond_bed()


def stone(name, x, y, s, seed, sink=0.4, sq=0.6):
    rr = np.random.default_rng(seed)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    ph = rr.uniform(0, TAU, 6)
    for v in bm.verts:
        p = v.co; d = 1 + 0.18 * math.sin(3 * p.x + ph[0]) * math.cos(2 * p.y + ph[1]) + 0.1 * math.sin(5 * p.z + ph[2]) \
            + 0.06 * math.sin(7 * p.x + 5 * p.y + ph[3])
        v.co = Vector((p.x * d * rr.uniform(0.98, 1.02), p.y * d * 0.85, p.z * d * sq))
    o = bm_obj(name, bm, [M_ROCK], smooth=70)
    o.scale = (s * rr.uniform(0.8, 1.3), s * rr.uniform(0.8, 1.2), s)
    o.rotation_euler = (rr.uniform(-0.2, 0.2), rr.uniform(-0.2, 0.2), rr.uniform(0, TAU))
    o.location = (x, y, bed_z(x, y) + s * sq * (1 - 2 * sink)); box_uv(o, 1.2)
    return o


rr = np.random.default_rng(17)
STONES = []
for k in range(26):
    while True:
        x, y = rr.uniform(-20, 20), rr.uniform(-12, 14)
        if math.hypot(x, y) > RD + 0.5: break
    STONES.append(stone('Stone%02d' % k, x, y, rr.uniform(0.25, 0.8), 400 + k))
for k, (x, y, s) in enumerate(((-13.2, 9.2, 1.1), (-12.0, 10.4, 0.6), (14.3, 8.6, 0.9), (-12.5, -7.6, 0.8))):   # breaking the surface
    o = stone('StoneBig%d' % k, x, y, s, 500 + k, sink=0.0, sq=0.75); o.location.z = WZ - 0.45 * s; STONES.append(o)


def ribbon(name, base, dirv, L, w0, bend, mat, segs=7, twist=0.0, sway=(0, 0), wexp=0.8, stage=True, uvv=True):
    """A tapering blade (reed leaf / weed strand) from base, rising along dirv, bending towards `bend`."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    d = Vector(dirv).normalized(); b = Vector(bend)
    side = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized()
    if b.length > 1e-6: side = d.cross(b).normalized() if d.cross(b).length > 1e-6 else side
    rows = []
    for k in range(segs + 1):
        t = k / segs
        c = Vector(base) + d * (L * t) + b * (t * t) + Vector((sway[0], sway[1], 0)) * math.sin(t * 3.0) * t
        w = w0 * (1 - t) ** wexp + 0.002
        tw = twist * t; sd = side * math.cos(tw) + d.cross(side) * math.sin(tw)
        rows.append((bm.verts.new(c - sd * w / 2), bm.verts.new(c + sd * w / 2), t))
    for (a0, a1, t0), (b0, b1, t1) in zip(rows[:-1], rows[1:]):
        f = bm.faces.new((a0, a1, b1, b0))
        for lp, uv in zip(f.loops, ((0, t0), (1, t0), (1, t1), (0, t1))): lp[uvl].uv = uv
    return bm_obj(name, bm, [mat], smooth=80, stage=stage)


def merge(name, objs, mats=None):
    """Join a list of mesh objects into one (keeps their materials)."""
    if not objs: return None
    for x in objs[1:]:
        if x in STAGE: STAGE.remove(x)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join(); o = bpy.context.view_layer.objects.active; o.name = name
    return o


# underwater weeds (pondweed strands) and the pads' long stems
weeds = []
for k in range(110):
    while True:
        x, y = rr.uniform(-18, 18), rr.uniform(-10, 14)
        if math.hypot(x, y) > RD - 1.5: break
    zb = bed_z(x, y); hi = min(2.0, (WZ - 0.25) - zb + 0.2)
    if hi < 0.7: continue
    L = rr.uniform(0.6, hi)
    for s in range(3):
        weeds.append(ribbon('weed', (x + rr.uniform(-.2, .2), y + rr.uniform(-.2, .2), zb - 0.05), (rr.uniform(-.3, .3), rr.uniform(-.3, .3), 1),
                            L * rr.uniform(0.6, 1.0), rr.uniform(0.12, 0.24), (rr.uniform(-.4, .4), rr.uniform(-.4, .4), 0), M_WEED,
                            segs=6, twist=rr.uniform(-2, 2), sway=(rr.uniform(-.15, .15), rr.uniform(-.15, .15))))
WEEDS = merge('Weeds', weeds)

stems = [curve_mesh('MainStem', [(0, 0, -0.3), (0.2, 0.4, -0.9), (-0.4, 1.4, -1.6), (-1.2, 2.4, bed_z(-1.2, 2.4) + 0.05)], 0.14, M_STEMR, res=6, bres=1)]
for k, (x, y, r, *_rest) in enumerate(PAD_SPECS):
    zb = bed_z(x, y); ex, ey = x + rr.uniform(-1.5, 1.5), y + rr.uniform(-1.5, 1.5)
    stems.append(curve_mesh('stem', [(x, y, WZ - 0.03), (x + (ex - x) * 0.3, y + (ey - y) * 0.2, (WZ + zb) / 2), (ex, ey, bed_z(ex, ey) + 0.03)],
                            0.035 + 0.012 * r, M_STEMR, res=5, bres=1))
STEMS = merge('Stems', stems)


# ================================================================ the water lily, buds, floating petals
def petal_mesh(L, W, cup, curl, nu=7, nv=5, mat_=None, name='petal', stage=False):
    """A pointed, cupped petal in local space: base at origin, length along +X, width along Y, cup up (+Z)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = []
    for i in range(nu + 1):
        u = i / nu; row = []
        w = W * (math.sin(math.pi * min(1.0, u ** 0.75 * 1.0)) ** 0.8) * (1 - 0.15 * u) + 0.004
        if i == nu: w = 0.004
        for j in range(nv + 1):
            v = j / nv * 2 - 1
            x = L * u; y = v * w / 2
            z = cup * (v * v) * w + curl * L * u * u
            row.append(bm.verts.new((x - 0.0 * u, y, z)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            for lp, (a, b) in zip(f.loops, ((j / nv, i / nu), (j / nv, (i + 1) / nu), ((j + 1) / nv, (i + 1) / nu), ((j + 1) / nv, i / nu))):
                lp[uvl].uv = (a, b)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.shade_smooth()
    return me


def add_me(bm, me, M):
    t = bmesh.new(); t.from_mesh(me); bmesh.ops.transform(t, matrix=M, verts=t.verts)
    m2 = bpy.data.meshes.new('t'); t.to_mesh(m2); t.free(); bm.from_mesh(m2); bpy.data.meshes.remove(m2)


def lily_flower(name, loc, size, openness=1.0, seed=0, rot=0.0):
    """Nymphaea bloom: green-purple sepals, 4 whorls of pink-white petals, a yellow heart of stamens."""
    rr = np.random.default_rng(seed); parts = []
    bm = bmesh.new()
    whorls = [(4, 1.0, 0.10, 8), (9, 0.95, 0.28, 0), (9, 0.85, 0.55, 20), (8, 0.68, 0.85, 10), (7, 0.5, 1.12, 0)]
    for wi, (cnt, Ls, elev, off) in enumerate(whorls):
        for k in range(cnt):
            a = TAU * k / cnt + math.radians(off) + rr.uniform(-0.08, 0.08)
            L = size * Ls * rr.uniform(0.92, 1.05); W = L * (0.38 if wi else 0.36)
            el = elev * (0.55 + 0.45 * openness) if wi else 0.05
            me = petal_mesh(L, W, 0.35, 0.10 - 0.05 * wi)
            M = Matrix.Translation((0, 0, 0.02 * wi * size)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((size * 0.08, 0, 0)) \
                @ Matrix.Rotation(-el + rr.uniform(-0.06, 0.06), 4, 'Y') @ Matrix.Rotation(rr.uniform(-0.08, 0.08), 4, 'X')
            add_me(bm if wi else BM_SEPAL, me, M); bpy.data.meshes.remove(me)
    o = bm_obj(name + '_petals', bm, [M_PETAL], smooth=80)
    o2 = bm_obj(name + '_sepals', BM_SEPAL.copy(), [M_SEPAL], smooth=80); BM_SEPAL.clear()
    # heart: a stigma disc and a crown of incurved stamens
    hb = bmesh.new()
    st = lathe('tmp', [(0, size * 0.1), (size * 0.12, size * 0.1), (size * 0.14, size * 0.16), (size * 0.08, size * 0.2), (0, size * 0.19)], [M_STIGMA], segs=16, stage=False)
    add_me(hb, st.data, Matrix()); bpy.data.objects.remove(st)
    for k in range(48):
        a = TAU * k / 48 + rr.uniform(-0.05, 0.05); r0 = size * rr.uniform(0.13, 0.19)
        h = size * rr.uniform(0.18, 0.3); lean = rr.uniform(0.15, 0.45)
        base = Vector((r0 * math.cos(a), r0 * math.sin(a), size * 0.1))
        tip = base + Vector((math.cos(a) * h * lean * 0.6, math.sin(a) * h * lean * 0.6, h))
        mid = (base + tip) / 2 + Vector((math.cos(a), math.sin(a), 0)) * h * 0.12
        s_ = ribbon('stm', base, (tip - base), (tip - base).length, size * 0.035, mid - (base + tip) / 2, M_STAMEN, segs=3, stage=False)
        add_me(hb, s_.data, Matrix()); bpy.data.objects.remove(s_)
    o3 = bm_obj(name + '_heart', hb, [M_STAMEN], smooth=80)
    for x in (o, o2, o3):
        x.location = loc; x.rotation_euler = (0, 0, rot)
    return [o, o2, o3]


BM_SEPAL = bmesh.new()
print('flowers...')
FLOWER = lily_flower('Lily', (11.4, 5.5, WZ + 0.05), 1.15, 1.0, seed=3, rot=0.3)
FLOWER2 = lily_flower('Lily2', (-12.3, 8.3, WZ + 0.06), 0.75, 0.55, seed=4, rot=1.2)
for o in FLOWER2: o.location.z += 0.04


def bud(name, base, top, size, seed):
    """A closed bud on its stem rising out of the water."""
    rr = np.random.default_rng(seed)
    base = Vector(base); top = Vector(top)
    mid = (base + top) / 2 + Vector((rr.uniform(-.3, .3), rr.uniform(-.3, .3), 0))
    stem_ = curve_mesh(name + '_stem', [base, mid, top], 0.045 * size / 0.5, M_STEM, res=6, bres=1)
    prof = [(0, -0.05), (0.18, 0.0), (0.26, 0.15), (0.27, 0.32), (0.2, 0.55), (0.1, 0.78), (0.0, 0.92)]
    prof = [(r * size, z * size * 1.3) for r, z in prof]
    b = lathe(name, prof, [M_BUD, M_BUDTIP], segs=16)
    # pink petal tip showing where the sepals part: upper faces get the tip material
    for p in b.data.polygons:
        c_ = p.center
        a = math.atan2(c_.y, c_.x)
        if c_.z > size * 1.3 * (0.42 + 0.25 * abs(math.sin(2 * a))): p.material_index = 1
    d = (top - mid).normalized()
    b.location = top; b.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return [stem_, b]


BUDS = bud('Bud1', (9.3, 7.6, WZ - 0.1), (9.0, 7.9, 1.0), 0.42, 1) + bud('Bud2', (13.8, 3.0, WZ - 0.1), (14.4, 3.2, 0.7), 0.36, 2) \
    + bud('Bud3', (-10.6, 1.0, WZ - 0.1), (-10.9, 0.6, 0.85), 0.38, 3)

# floating petals
fp = bmesh.new()
for k, (x, y, a) in enumerate(((7.2, -1.4, 0.3), (7.9, -0.8, 2.0), (6.6, 2.3, 4.0), (-6.9, 1.6, 1.0), (-7.4, -1.6, 5.2),
                                (3.4, -6.4, 2.6), (8.6, 3.4, 0.8), (-2.2, 7.4, 3.6), (9.9, 1.2, 1.7))):
    me = petal_mesh(0.7, 0.27, 0.3, 0.08 + 0.04 * (k % 3))
    add_me(fp, me, Matrix.Translation((x, y, WZ + 0.005)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(-0.05, 4, 'Y'))
    bpy.data.meshes.remove(me)
FLOATP = bm_obj('FloatingPetals', fp, [M_PETAL], smooth=80)


# ================================================================ reeds & cattails
print('reeds...')
def reed_clump(name, cx, cy, n, seed, h=(4.5, 8.0)):
    rr = np.random.default_rng(seed); bl = []; tails = []
    for k in range(n):
        x, y = cx + rr.normal(0, 1.2), cy + rr.normal(0, 1.0)
        L = rr.uniform(*h); lean = Vector((rr.normal(0, 0.12), rr.normal(0, 0.12), 1))
        bend = Vector((rr.normal(0, 1), rr.normal(0, 1), -0.2)) * rr.uniform(0.3, 1.6)
        m = M_REEDY if rr.random() < 0.18 else M_REED
        bl.append(ribbon('blade', (x, y, WZ - 0.3), lean, L, rr.uniform(0.09, 0.16), bend, m, segs=7, twist=rr.uniform(-1.5, 1.5), wexp=0.6))
    for k in range(max(3, n // 9)):
        x, y = cx + rr.normal(0, 1.0), cy + rr.normal(0, 0.8)
        L = rr.uniform(h[0] * 0.9, h[1] * 0.95); lean = Vector((rr.normal(0, .06), rr.normal(0, .06), 1)).normalized()
        top = Vector((x, y, WZ)) + lean * L
        tails.append(curve_mesh('ctstalk', [(x, y, WZ - 0.3), Vector((x, y, WZ)) + lean * L * 0.5 + Vector((rr.normal(0, .15), rr.normal(0, .15), 0)), top], 0.045, M_REED, res=4, bres=1))
        hl = rr.uniform(0.6, 0.85)
        hd = lathe('cthead', [(0, 0), (0.1, 0.02), (0.13, 0.12), (0.135, hl * 0.5), (0.13, hl - 0.1), (0.1, hl - 0.02), (0.02, hl), (0.02, hl + 0.35), (0, hl + 0.4)], [M_CATTAIL], segs=10)
        hd.location = top - lean * (hl + 0.1); hd.rotation_euler = lean.to_track_quat('Z', 'Y').to_euler(); tails.append(hd)
    a = merge(name + '_blades', bl); b = merge(name + '_tails', tails)
    return [a, b]


REEDS = reed_clump('ReedsL', -16.0, 11.8, 46, 1) + reed_clump('ReedsR', 16.8, 10.8, 40, 2) + reed_clump('ReedsF', -15.2, -9.0, 26, 3, h=(3.5, 6.0))


# ================================================================ dragonfly
print('dragonfly & frog...')
def dragonfly(loc, yaw, s=1.0):
    parts = []
    prof = [(0, 0), (0.035, 0.02)]
    for k in range(10):
        z = 0.05 + k * 0.06; r = 0.035 - 0.0018 * k
        prof += [(r * 1.08, z), (r * 0.92, z + 0.05)]
    prof += [(0.02, 0.66), (0, 0.68)]
    ab = lathe('DF_abdomen', [(r * s, z * s) for r, z in prof], [M_DFLY, M_DLEG], segs=10)
    for p in ab.data.polygons:   # dark rings between the segments
        zz = p.center.z / s
        if zz > 0.05 and ((zz - 0.05) % 0.06) > 0.045: p.material_index = 1
    ab.rotation_euler = (-math.pi / 2 - 0.06, 0, 0)
    th = ellipsoid('DF_thorax', (0.07 * s, 0.11 * s, 0.075 * s), M_DFLY, 14, 8, loc=(0, -0.03 * s, 0.01 * s))
    hd = ellipsoid('DF_head', (0.05 * s, 0.04 * s, 0.045 * s), M_DFLY, 12, 8, loc=(0, -0.155 * s, 0.015 * s))
    e1 = ellipsoid('DF_eyeL', (0.034 * s, 0.036 * s, 0.034 * s), M_DEYE, 14, 8, loc=(0.03 * s, -0.17 * s, 0.03 * s))
    e2 = ellipsoid('DF_eyeR', (0.034 * s, 0.036 * s, 0.034 * s), M_DEYE, 14, 8, loc=(-0.03 * s, -0.17 * s, 0.03 * s))
    parts += [ab, th, hd, e1, e2]
    # wings: thin veined membranes
    for sd in (-1, 1):
        for fw, (y0, ln, wd, sw) in enumerate(((-0.06, 0.42, 0.1, -0.12), (0.03, 0.4, 0.12, 0.1))):
            bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); top_, bot = [], []
            nseg = 10
            for i in range(nseg + 1):
                u = i / nseg; x = u * ln
                w = wd * (math.sin(math.pi * min(1, 0.15 + u * 0.92)) ** 0.6) * (0.75 + 0.35 * (1 - u))
                top_.append(bm.verts.new((sd * x * s, (y0 - w * 0.25) * s, 0))); bot.append(bm.verts.new((sd * x * s, (y0 + w * 0.75) * s, 0)))
            for i in range(nseg):
                f = bm.faces.new((top_[i], top_[i + 1], bot[i + 1], bot[i]) if sd > 0 else (top_[i], bot[i], bot[i + 1], top_[i + 1]))
                uvs = ((i / nseg, 0), ((i + 1) / nseg, 0), ((i + 1) / nseg, 1), (i / nseg, 1)) if sd > 0 else ((i / nseg, 0), (i / nseg, 1), ((i + 1) / nseg, 1), ((i + 1) / nseg, 0))
                for lp, uv in zip(f.loops, uvs): lp[uvl].uv = uv
            w_ = bm_obj('DF_wing', bm, [M_WING], smooth=0)
            w_.location = (sd * 0.03 * s, y0 * 0.3 * s, 0.05 * s); w_.rotation_euler = (0, sd * -0.12, sd * sw)
            parts.append(w_)
    for sd in (-1, 1):   # legs tucked under the thorax
        for k in range(3):
            y = (-0.08 + k * 0.04) * s
            parts.append(curve_mesh('DF_leg', [(sd * 0.02 * s, y, -0.03 * s), (sd * 0.07 * s, y - 0.02 * s, -0.07 * s), (sd * 0.05 * s, y - 0.05 * s, -0.11 * s)], 0.006 * s, M_DLEG, res=3, bres=0))
    root = bpy.data.objects.new('Dragonfly', None); scn.collection.objects.link(root); STAGE.append(root)
    for p in parts: p.parent = root
    root.location = loc; root.rotation_euler = (0.12, -0.08, yaw)
    return root, parts


DFLY, DFLY_PARTS = dragonfly((-6.2, 6.4, 1.9), math.radians(-120), s=1.8)


# ================================================================ frog
def frog(loc, yaw, s=1.0):
    """A sitting frog (facing -Y) from blended metaball ellipsoids given by their half-extents in metres."""
    mb = bpy.data.metaballs.new('FrogMB'); mb.resolution = 0.018 * s; mb.render_resolution = 0.018 * s; mb.threshold = 0.6
    def el(co, half, rot=None):
        e = mb.elements.new(); e.type = 'ELLIPSOID'; e.co = Vector(co) * s
        m_ = max(half); e.radius = m_ * s / 0.574 * 0.92
        e.size_x, e.size_y, e.size_z = [h / m_ for h in half]
        if rot: e.rotation = Euler(rot).to_quaternion()
    el((0, 0.08, 0.2), (0.22, 0.3, 0.15), (-0.25, 0, 0))      # body, sloping down to the rump
    el((0, -0.19, 0.26), (0.19, 0.16, 0.11), (0.1, 0, 0))     # head
    el((0, -0.32, 0.23), (0.12, 0.09, 0.065))                  # snout
    for sd in (-1, 1):
        el((sd * 0.11, -0.22, 0.34), (0.06, 0.06, 0.06))           # eye bumps
        el((sd * 0.2, 0.2, 0.12), (0.08, 0.2, 0.08), (0, 0, sd * 0.4))     # thigh
        el((sd * 0.26, 0.0, 0.07), (0.06, 0.19, 0.05), (0, 0, -sd * 0.3))  # shin folded forward
        el((sd * 0.31, -0.13, 0.02), (0.1, 0.14, 0.02), (0, 0, sd * 0.3))  # webbed hind foot
        el((sd * 0.15, -0.28, 0.1), (0.045, 0.045, 0.1), (0.25, -sd * 0.2, 0))   # front arm
        el((sd * 0.17, -0.36, 0.02), (0.07, 0.07, 0.02))           # hand
    tmp = bpy.data.objects.new('FrogMBo', mb); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    o = obj('Frog', me, [M_FROG])
    dec = o.modifiers.new('d', 'DECIMATE'); dec.ratio = float(OPT.get('frogdec', 0.3))
    dg = bpy.context.evaluated_depsgraph_get(); me2 = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
    o.modifiers.clear(); o.data = me2; me2.shade_smooth()
    # UV: spherical about the body centre (top = green and spotted, belly = cream)
    uv = me2.uv_layers.new(name='UVMap'); cc = Vector((0, -0.05, 0.2)) * s
    for l in me2.loops:
        p = me2.vertices[l.vertex_index].co - cc
        uv.data[l.index].uv = (math.atan2(p.y, p.x) / TAU + 0.5, math.atan2(p.z, math.hypot(p.x, p.y)) / math.pi + 0.5)
    eyes = []
    for sd in (-1, 1):
        ec = Vector((sd * 0.118, -0.235, 0.375)) * s; dv = Vector((sd * 0.65, -0.65, 0.35)).normalized()
        e = ellipsoid('FrogEye', (0.058 * s, 0.058 * s, 0.055 * s), M_FEYE, 16, 10, loc=ec); eyes.append(e)
        p = ellipsoid('FrogPupil', (0.03 * s, 0.006 * s, 0.017 * s), M_PUPIL, 10, 6, loc=ec + dv * 0.054 * s,
                      rot=dv.to_track_quat('-Y', 'Z').to_euler()); eyes.append(p)
    root = bpy.data.objects.new('FrogRoot', None); scn.collection.objects.link(root); STAGE.append(root)
    for x in [o] + eyes: x.parent = root
    root.location = loc; root.rotation_euler = (0, 0, yaw)
    return root


FROG = frog((-8.9, 3.9, WZ + 0.02), math.radians(62), s=1.9)


# ================================================================ export the stage
total = sum(tris(o) for o in STAGE)
print('TOTAL triangles:', total, ' objects:', len(STAGE))
top = sorted(((tris(o), o.name) for o in STAGE), reverse=True)[:14]; print('heaviest', top)
if not NOEXP:
    bpy.ops.object.select_all(action='DESELECT')
    for o in STAGE: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'lily.glb'), export_format='GLB', use_selection=True,
                              export_apply=True, export_image_format='JPEG', export_jpeg_quality=90)
    print('exported', os.path.join(OUT, 'lily.glb'), os.path.getsize(os.path.join(OUT, 'lily.glb')) // 1024, 'KB')
if NOREN: sys.exit(0)


# ================================================================ render-only touches
def nodes(m): return m.node_tree.nodes, m.node_tree.links


# water: procedural ripples (concentric rings round the pad, wind ripples), clear volume tinted green with depth
def water_render(splash_c=None):
    nt, lk = nodes(M_WATER); bs = BSDF['Water']
    for n in list(nt):
        if n.type in ('NORMAL_MAP', 'TEX_IMAGE'): nt.remove(n)
    geo = nt.new('ShaderNodeNewGeometry')
    sep = nt.new('ShaderNodeSeparateXYZ'); lk.new(geo.outputs['Position'], sep.inputs[0])
    def math_(op, a, b=None, v=None):
        m = nt.new('ShaderNodeMath'); m.operation = op
        for i, x in enumerate((a, b)):
            if x is None: continue
            if isinstance(x, (int, float)): m.inputs[i].default_value = x
            else: lk.new(x, m.inputs[i])
        return m.outputs[0]
    def ring_src(cx, cy, r0, lam, amp, dec):
        dx = math_('SUBTRACT', sep.outputs[0], cx); dy = math_('SUBTRACT', sep.outputs[1], cy)
        rr_ = math_('SQRT', math_('ADD', math_('MULTIPLY', dx, dx), math_('MULTIPLY', dy, dy)))
        d = math_('MAXIMUM', math_('SUBTRACT', rr_, r0), 0.0)
        s = math_('SINE', math_('MULTIPLY', d, TAU / lam))
        e = math_('EXPONENT', math_('MULTIPLY', d, -1.0 / dec))
        return math_('MULTIPLY', math_('MULTIPLY', s, e), amp)
    h = ring_src(0, 0, RD, 0.95, 0.022, 4.5)
    for (x, y, r, *_r) in PAD_SPECS[:8]:
        h = math_('ADD', h, ring_src(x, y, r, 0.6, 0.008, 1.6))
    if splash_c is not None:
        h = math_('ADD', h, ring_src(splash_c[0], splash_c[1], 2.4, 0.7, 0.05, 3.0))
    nz = nt.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.4; nz.inputs['Detail'].default_value = 6
    nz.inputs['Roughness'].default_value = 0.55
    lk.new(geo.outputs['Position'], nz.inputs['Vector'])
    h = math_('ADD', h, math_('MULTIPLY', nz.outputs['Fac'], 0.025))
    bump = nt.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 1.0; bump.inputs['Distance'].default_value = 1.0
    lk.new(h, bump.inputs['Height']); lk.new(bump.outputs['Normal'], bs.inputs['Normal'])
    bs.inputs['Base Color'].default_value = (1, 1, 1, 1); bs.inputs['Roughness'].default_value = 0.02
    bs.inputs['Base Color'].default_value = (*lin('cde8d2'), 1)       # a faint green cast on what is seen through it
    if 'nowater' in OPT: WATER.hide_render = True
    if 'nobump' in OPT: lk.remove(bump.outputs['Normal'].links[0])
    # no volume: shadow rays would never leave it (the water is invisible to them so the sun reaches the bed).
    # Depth absorption is faked on the underwater materials instead (depth_tint below).
    WATER.visible_shadow = False


water_render(SPL_C if SPLASH else None)


def depth_tint(mname, k=None, col=None):
    """Fade an underwater material towards murky pond green with depth below the surface."""
    k = float(OPT.get('absorb', 0.9)) if k is None else k
    nt, lk = nodes(MATS[mname]); bs = BSDF[mname]
    src = bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].links else None
    geo = nt.new('ShaderNodeNewGeometry'); sep = nt.new('ShaderNodeSeparateXYZ'); lk.new(geo.outputs['Position'], sep.inputs[0])
    d = nt.new('ShaderNodeMath'); d.operation = 'SUBTRACT'; d.inputs[0].default_value = WZ; lk.new(sep.outputs['Z'], d.inputs[1])
    d2 = nt.new('ShaderNodeMath'); d2.operation = 'MAXIMUM'; d2.inputs[1].default_value = 0.0; lk.new(d.outputs[0], d2.inputs[0])
    e = nt.new('ShaderNodeMath'); e.operation = 'MULTIPLY'; e.inputs[1].default_value = -k; lk.new(d2.outputs[0], e.inputs[0])
    ex = nt.new('ShaderNodeMath'); ex.operation = 'EXPONENT'; lk.new(e.outputs[0], ex.inputs[0])
    f = nt.new('ShaderNodeMath'); f.operation = 'SUBTRACT'; f.inputs[0].default_value = 1.0; lk.new(ex.outputs[0], f.inputs[1])
    mx = nt.new('ShaderNodeMix'); mx.data_type = 'RGBA'; lk.new(f.outputs[0], mx.inputs['Factor'])
    if src: lk.new(src, mx.inputs['A'])
    else: mx.inputs['A'].default_value = bs.inputs['Base Color'].default_value
    mx.inputs['B'].default_value = (*lin(col or '22351c'), 1)
    lk.new(mx.outputs['Result'], bs.inputs['Base Color'])


# the pad: waxy sheen micro-bumps, a little translucency under the sun
for mname in ('PadTop', 'PadSmall', 'PadOld'):
    nt, lk = nodes(MATS[mname]); bs = BSDF[mname]
    bs.inputs['Coat Weight'].default_value = 0.15 if mname == 'PadTop' else 0.06; bs.inputs['Coat Roughness'].default_value = 0.2 if mname == 'PadTop' else 0.3
    bs.inputs['Specular IOR Level'].default_value = 0.32 if mname == 'PadTop' else 0.22
    nm = [n for n in nt if n.type == 'NORMAL_MAP'][0]
    nz = nt.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 3
    bp = nt.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08; bp.inputs['Distance'].default_value = 0.01
    lk.new(nz.outputs['Fac'], bp.inputs['Height']); lk.new(nm.outputs['Normal'], bp.inputs['Normal'])
    lk.new(bp.outputs['Normal'], bs.inputs['Coat Normal'])
# petals: translucent
for mname in ('Petal', 'BudTip'):
    nt, lk = nodes(MATS[mname]); bs = BSDF[mname]
    tr = nt.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (*lin('ffd8e4'), 1)
    mx = nt.new('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = 0.3
    out = nt['Material Output']
    lk.new(bs.outputs[0], mx.inputs[1]); lk.new(tr.outputs[0], mx.inputs[2]); lk.new(mx.outputs[0], out.inputs['Surface'])
# iridescence on the dragonfly
BSDF['DragonBody'].inputs['Thin Film Thickness'].default_value = 380; BSDF['DragonBody'].inputs['Thin Film IOR'].default_value = 1.6
BSDF['Wing'].inputs['Thin Film Thickness'].default_value = 520; BSDF['Wing'].inputs['Thin Film IOR'].default_value = 1.45
BSDF['DragonEye'].inputs['Thin Film Thickness'].default_value = 300
# frog: wet sheen bumps
nt, lk = nodes(M_FROG)
nz = nt.new('ShaderNodeTexVoronoi'); nz.inputs['Scale'].default_value = 40
bp = nt.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25; bp.inputs['Distance'].default_value = 0.02
lk.new(nz.outputs['Distance'], bp.inputs['Height']); lk.new(bp.outputs['Normal'], BSDF['Frog'].inputs['Normal'])
# cattails: velvet
BSDF['Cattail'].inputs['Sheen Weight'].default_value = 0.6; BSDF['Cattail'].inputs['Sheen Tint'].default_value = (*lin('c89a6a'), 1)
# pond bed: algae tint
nt, lk = nodes(M_MUD); bs = BSDF['PondBed']
img = [n for n in nt if n.type == 'TEX_IMAGE' and n.image.name.startswith('brown_mud_rocks_01_diff')][0]
mix = nt.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.55
mix.inputs['B'].default_value = (*lin('8aa860'), 1)
lk.new(img.outputs['Color'], mix.inputs['A']); lk.new(mix.outputs['Result'], bs.inputs['Base Color'])
# algae patches and sunlight caustics on the bed (render-only)
nz = nt.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.25; nz.inputs['Detail'].default_value = 6
rp = nt.new('ShaderNodeMapRange'); rp.inputs['From Min'].default_value = 0.45; rp.inputs['From Max'].default_value = 0.65
lk.new(nz.outputs['Fac'], rp.inputs['Value'])
al = nt.new('ShaderNodeMix'); al.data_type = 'RGBA'; al.blend_type = 'MIX'; lk.new(rp.outputs['Result'], al.inputs['Factor'])
lk.new(mix.outputs['Result'], al.inputs['A']); al.inputs['B'].default_value = (*lin('3a4a1a'), 1)
lk.new(al.outputs['Result'], bs.inputs['Base Color'])


def caustics(mname, strength=1.6):
    nt, lk = nodes(MATS[mname]); bs = BSDF[mname]
    src = bs.inputs['Base Color'].links[0].from_socket
    geo = nt.new('ShaderNodeNewGeometry')
    wn_ = nt.new('ShaderNodeTexNoise'); wn_.inputs['Scale'].default_value = 0.6; wn_.inputs['Detail'].default_value = 2
    lk.new(geo.outputs['Position'], wn_.inputs['Vector'])
    dv = nt.new('ShaderNodeVectorMath'); dv.operation = 'MULTIPLY_ADD'; dv.inputs[1].default_value = (0.5, 0.5, 0.5)
    lk.new(wn_.outputs['Color'], dv.inputs[0]); lk.new(geo.outputs['Position'], dv.inputs[2])
    vo_ = nt.new('ShaderNodeTexVoronoi'); vo_.feature = 'DISTANCE_TO_EDGE'; vo_.inputs['Scale'].default_value = 1.3
    lk.new(dv.outputs['Vector'], vo_.inputs['Vector'])
    mr = nt.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.07
    mr.inputs['To Min'].default_value = 1.0 + strength; mr.inputs['To Max'].default_value = 0.85
    lk.new(vo_.outputs['Distance'], mr.inputs['Value'])
    ml = nt.new('ShaderNodeMix'); ml.data_type = 'RGBA'; ml.blend_type = 'MULTIPLY'; ml.inputs['Factor'].default_value = 1.0
    lk.new(src, ml.inputs['A']); lk.new(mr.outputs['Result'], ml.inputs['B'])
    lk.new(ml.outputs['Result'], bs.inputs['Base Color'])


caustics('PondBed'); caustics('Stone', 1.0)
for mname in ('PondBed', 'Stone', 'Weed', 'StemRed'):
    depth_tint(mname)

# ---------------------------------------------------------------- sky & sun
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
wn, wl = world.node_tree.nodes, world.node_tree.links
env = wn.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(PH, 'lakeside_sunrise_4k.hdr'))
SUN_DIR = Vector((-0.86, 0.5, 0.0)).normalized()       # horizontal direction towards the sun (back-left)
SUN_EL = math.radians(float(OPT.get('sunel', 25)))
# the HDRI's own sun sits at u = 0.600 (found by scanning the image): rotate the sky so it lines up with ours
u_h = 0.6002; phi = (u_h - 0.5) * TAU; d_h = Vector((-math.cos(phi), math.sin(phi), 0))
rotz = math.atan2(d_h.y, d_h.x) - math.atan2(SUN_DIR.y, SUN_DIR.x)
tc = wn.new('ShaderNodeTexCoord'); mp = wn.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, rotz)
wl.new(tc.outputs['Generated'], mp.inputs['Vector']); wl.new(mp.outputs['Vector'], env.inputs['Vector'])
clamp = wn.new('ShaderNodeMix'); clamp.data_type = 'RGBA'; clamp.blend_type = 'DARKEN'; clamp.inputs['Factor'].default_value = 1.0
clamp.inputs['B'].default_value = (6, 6, 6, 1)
wl.new(env.outputs['Color'], clamp.inputs['A'])
bg = wn['Background']; bg.inputs['Strength'].default_value = float(OPT.get('sky', 1.1))
wl.new(clamp.outputs['Result'], bg.inputs['Color'])

sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sdir = Vector((SUN_DIR.x * math.cos(SUN_EL), SUN_DIR.y * math.cos(SUN_EL), math.sin(SUN_EL)))
sun.rotation_euler = (-sdir).to_track_quat('-Z', 'Y').to_euler()
sun.data.energy = float(OPT.get('sun', 6.5)); sun.data.color = (1.0, 0.78, 0.52); sun.data.angle = math.radians(float(OPT.get('sunang', 4.0)))

# dappled light: an unseen patch of leafy canopy between the sun and the pond's left side (the left of the pad
# catches broken light; the fighting area stays in full sun)
bpy.ops.mesh.primitive_plane_add(size=1); gobo = bpy.context.object; gobo.name = 'Canopy'
GOBO_C = Vector(eval(OPT.get('gobo', '(-8.0, 3.0, 0.0)'))); GOBO_S = float(OPT.get('gobos', 16))
gobo.scale = (GOBO_S, GOBO_S, 1); gobo.location = GOBO_C + sdir * float(OPT.get('gobod', 8))
gobo.rotation_euler = sdir.to_track_quat('Z', 'Y').to_euler()
gm = bpy.data.materials.new('Canopy'); gm.use_nodes = True; gnt = gm.node_tree; gn, gl_ = gnt.nodes, gnt.links
gn.remove(gn['Principled BSDF'])
tco = gn.new('ShaderNodeTexCoord')
vo = gn.new('ShaderNodeTexNoise'); vo.inputs['Scale'].default_value = float(OPT.get('gobon', 14)); vo.inputs['Detail'].default_value = 10
vo.inputs['Roughness'].default_value = 0.72
gl_.new(tco.outputs['Object'], vo.inputs['Vector'])
ln_ = gn.new('ShaderNodeVectorMath'); ln_.operation = 'LENGTH'; gl_.new(tco.outputs['Object'], ln_.inputs[0])
sc_ = gn.new('ShaderNodeMath'); sc_.operation = 'MULTIPLY_ADD'; sc_.inputs[1].default_value = 1.3; sc_.inputs[2].default_value = -0.3
gl_.new(ln_.outputs['Value'], sc_.inputs[0])
ad_ = gn.new('ShaderNodeMath'); ad_.operation = 'ADD'; gl_.new(vo.outputs['Fac'], ad_.inputs[0]); gl_.new(sc_.outputs[0], ad_.inputs[1])
ramp = gn.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[1].position = 0.53
gl_.new(ad_.outputs[0], ramp.inputs['Fac'])
tr_ = gn.new('ShaderNodeBsdfTransparent'); df = gn.new('ShaderNodeBsdfDiffuse'); df.inputs['Color'].default_value = (0, 0, 0, 1)
ms = gn.new('ShaderNodeMixShader'); gl_.new(ramp.outputs['Color'], ms.inputs['Fac'])
gl_.new(df.outputs[0], ms.inputs[1]); gl_.new(tr_.outputs[0], ms.inputs[2]); gl_.new(ms.outputs[0], gn['Material Output'].inputs['Surface'])
gobo.data.materials.append(gm)
gobo.visible_camera = gobo.visible_glossy = gobo.visible_diffuse = gobo.visible_transmission = False
if 'nogobo' in OPT: gobo.hide_render = True

# warm bounce from the low sun off the water onto the undersides
if float(OPT.get('bounce', 0)) > 0:
    fill = bpy.data.objects.new('Bounce', bpy.data.lights.new('Bounce', 'AREA')); scn.collection.objects.link(fill)
    fill.data.energy = float(OPT.get('bounce', 150)); fill.data.color = (1.0, 0.85, 0.65); fill.data.size = 30; fill.data.shape = 'DISK'
    fill.location = (0, 0, -0.5); fill.rotation_euler = (math.pi, 0, 0); fill.visible_glossy = False   # facing up off the water


# ================================================================ characters (as stage_render.py)
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHARS, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots


stance = None
RIGS = []
def sumo(f, pos, face, scale=1.65, keep_action=True):
    global stance
    new, roots = load(f)
    rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
    if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
    elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
    if not keep_action and rig and rig.animation_data: rig.animation_data.action = None
    for r in roots:
        r.location = (pos[0], pos[1], main_z(pos[0], pos[1])); r.scale = (scale,) * 3
        r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))
    return rig, roots


def mmat(name, hexc, rough=0.35):
    m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*lin(hexc), 1); bs.inputs['Roughness'].default_value = rough; return m
def mask(kind, centre, fwd, up, k):
    fwd = (fwd - up * fwd.dot(up)).normalized(); right = fwd.cross(up).normalized()
    B = Matrix((right, fwd, up)).transposed().to_4x4(); B.translation = centre
    parts = []
    def put(o, loc, mat_):
        o.data.materials.append(mat_); bpy.ops.object.shade_smooth()
        o.matrix_world = B @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world; parts.append(o)
    def ell(loc, sc, mat_, half=False):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16); o = bpy.context.object
        if half:
            bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.05], context='VERTS'); bm.to_mesh(o.data); bm.free()
            sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.06
        o.scale = Vector(sc) * k; bpy.ops.object.transform_apply(scale=True); put(o, loc, mat_); return o
    def cone_(loc, r, h, rot, mat_):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r * k, depth=h * k); o = bpy.context.object
        o.rotation_euler = rot; bpy.ops.object.transform_apply(rotation=True); put(o, loc, mat_)
    def strap(mat_):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.25 * k, minor_radius=0.03 * k); o = bpy.context.object
        o.rotation_euler = (0.25, 0, 0); bpy.ops.object.transform_apply(rotation=True); put(o, (0, -0.02, 0.02), mat_)
    if kind == 'oni':
        R_ = mmat('mOni', 'c8231d'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), R_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
            cone_((sd * 0.11, 0.08, 0.2), 0.04, 0.18, (0, sd * 0.45, 0), mmat('mHorn', 'f2e6c8', 0.4))
        strap(R_)
    elif kind == 'hannya':
        W_ = mmat('mHannya', 'eae2c8'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
            cone_((sd * 0.11, 0.06, 0.22), 0.04, 0.22, (0, sd * 0.5, 0), mmat('mHornH', 'd8c890', 0.4))
        ell((0, 0.25, -0.12), (0.07, 0.02, 0.018), mmat('mMouth', '7a1414'))
        strap(W_)
    elif kind == 'kitsune':
        W_ = mmat('mKitsune', 'f6f2ea'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.03), (0.045, 0.015, 0.012), mmat('mRed', 'd8262e'))
            cone_((sd * 0.1, 0.06, 0.2), 0.055, 0.14, (0, sd * 0.3, 0), W_)
        cone_((0, 0.3, -0.06), 0.06, 0.14, (-math.pi / 2, 0, 0), W_)
        strap(mmat('mRedS', 'd8262e'))
    return parts


def head_frame(rig, roots):
    pb = rig.pose.bones['head']; M = rig.matrix_world @ pb.matrix
    up = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    fwd = (roots[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    return M.translation + up * 0.11 * roots[0].scale[0], fwd, up




def build_splash(c):
    """A crown of water thrown up round the impact, finger jets with beads at their tips, a spray of drops, foam."""
    rr = np.random.default_rng(91); out = []
    toward_pad = math.atan2(-c.y, -c.x)
    segs = 96; rows = 9; H = 2.3; r0 = 2.0
    nf = 17; fph = rr.uniform(0, TAU, nf); famp = rr.uniform(0.5, 1.0, nf)
    def hmax(a):
        da = abs(math.atan2(math.sin(a - toward_pad), math.cos(a - toward_pad)))
        side = 0.55 + 0.45 * fsstep(0.4, 1.6, da)
        lobes = 0.78 + 0.22 * math.cos(nf * a) ** 2
        return H * side * lobes * (0.9 + 0.2 * math.sin(3 * a + 1))
    bm = bmesh.new(); grid = []
    for i in range(rows + 1):
        t = i / rows; row = []
        for j in range(segs):
            a = TAU * j / segs; h = hmax(a)
            # fingers: the top rows pinch together towards the jets
            jet = math.cos(nf * a / 2) ** 2
            tt = t * (0.65 + 0.35 * jet) if t > 0.6 else t
            z = WZ - 0.1 + tt * h
            r = r0 + 0.9 * tt ** 1.6 + 0.05 * math.sin(7 * a + 3 * t)
            row.append(bm.verts.new((c.x + r * math.cos(a), c.y + r * math.sin(a), z)))
        grid.append(row)
    for i in range(rows):
        for j in range(segs):
            k = (j + 1) % segs; bm.faces.new((grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]))
    crown = bm_obj('SplashCrown', bm, [M_SPLASH], smooth=80, stage=False)
    so = crown.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.05
    sub = crown.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    disp_t = bpy.data.textures.new('spl', 'CLOUDS'); disp_t.noise_scale = 0.35
    dsp = crown.modifiers.new('d', 'DISPLACE'); dsp.texture = disp_t; dsp.strength = 0.06
    sub2 = crown.modifiers.new('sub2', 'SUBSURF'); sub2.levels = 1; sub2.render_levels = 1
    out.append(crown)
    # beads at the jets' tips and a spray thrown outwards
    bm = bmesh.new()
    def bead(p, rad, stretch, dirv):
        t = bmesh.new(); bmesh.ops.create_uvsphere(t, u_segments=10, v_segments=6, radius=1.0)
        M = Matrix.Translation(p) @ dirv.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Diagonal((rad, rad, rad * stretch, 1))
        bmesh.ops.transform(t, matrix=M, verts=t.verts)
        me = bpy.data.meshes.new('b'); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    for j in range(nf * 2):
        a = TAU * (j + 0.5) / (nf * 2) * 1.0
        a = (j * TAU / nf) / 2 * 2 / 2 + (TAU / nf) * (j // 2) if False else TAU * j / (2 * nf)
        if math.cos(nf * a / 2) ** 2 < 0.5: continue
        h = hmax(a) * (0.65 + 0.35)
        r = r0 + 0.9
        p = Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), WZ - 0.1 + h + 0.12))
        d = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 1)).normalized()
        bead(p, rr.uniform(0.04, 0.07), 1.8, d)
    for k in range(420):
        a = rr.uniform(0, TAU)
        da = abs(math.atan2(math.sin(a - toward_pad), math.cos(a - toward_pad)))
        hm = hmax(a)
        tt = rr.uniform(0.0, 1.0)
        r = r0 + 0.6 + tt * rr.uniform(0.5, 3.0)
        z = WZ + hm * (0.5 + 0.9 * rr.random()) * math.sin(math.pi * min(1, 0.25 + tt * 0.8)) + 0.1
        p = Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), z))
        d = Vector((math.cos(a), math.sin(a), 1.4 - 2.2 * tt)).normalized()
        rad = 0.012 + 0.05 * rr.random() ** 3
        bead(p, rad, 1.0 + 2.5 * rr.random(), d)
    # a few drops raining onto the pad's edge
    for k in range(40):
        a = toward_pad + rr.normal(0, 0.35); r = rr.uniform(0.6, 2.6)
        p = Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), WZ + rr.uniform(0.6, 2.6)))
        bead(p, 0.02 + 0.05 * rr.random() ** 2, 1.5 + 2 * rr.random(), Vector((rr.normal(0, .3), rr.normal(0, .3), 1)))
    spray = bm_obj('SplashSpray', bm, [M_SPLASH], smooth=80, stage=False); out.append(spray)
    # churned white water round the base and a skirt sheet rising from it
    foam_bm = bmesh.new(); fr = []
    for i, (rad, z) in enumerate(((0.0, WZ + 0.12), (1.2, WZ + 0.18), (2.0, WZ + 0.14), (2.6, WZ + 0.03), (3.4, WZ - 0.02))):
        row = []
        for j in range(64):
            a = TAU * j / 64; rj = rad * (1 + 0.08 * math.sin(5 * a + i) + 0.05 * rr.normal())
            row.append(foam_bm.verts.new((c.x + rj * math.cos(a), c.y + rj * math.sin(a), z + 0.05 * rr.normal())))
        fr.append(row)
    for A, B in zip(fr[:-1], fr[1:]):
        for j in range(64):
            k = (j + 1) % 64; foam_bm.faces.new((A[j], A[k], B[k], B[j]))
    foam = bm_obj('SplashFoam', foam_bm, [M_FOAM], smooth=80, stage=False); out.append(foam)
    return out


M_SPLASH = mat('SplashWater', (0.95, 1.0, 0.98), 0.06, trans=1.0, ior=1.333)
M_FOAM = mat('Foam', (0.92, 0.95, 0.93), 0.5, sss=0.4, sss_r=(1, 1, 1), sss_s=0.1)
if SPLASH:   # aerated, frothy water: mix white scatter into the clear splash where a noise says so
    nt, lk = nodes(M_SPLASH); bs = BSDF['SplashWater']
    nz = nt.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.5; nz.inputs['Detail'].default_value = 5
    rp = nt.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = 0.38; rp.color_ramp.elements[1].position = 0.62
    lk.new(nz.outputs['Fac'], rp.inputs['Fac'])
    wh = nt.new('ShaderNodeBsdfPrincipled'); wh.inputs['Base Color'].default_value = (0.95, 0.97, 0.96, 1); wh.inputs['Roughness'].default_value = 0.35
    wh.inputs['Subsurface Weight'].default_value = 0.5
    mx = nt.new('ShaderNodeMixShader'); lk.new(rp.outputs['Color'], mx.inputs['Fac'])
    lk.new(bs.outputs[0], mx.inputs[1]); lk.new(wh.outputs[0], mx.inputs[2]); lk.new(mx.outputs[0], nt['Material Output'].inputs['Surface'])
    # foam patches fade out into clear water
    nt, lk = nodes(M_FOAM); bs = BSDF['Foam']
    nz = nt.new('ShaderNodeTexVoronoi'); nz.inputs['Scale'].default_value = 3.0
    rp = nt.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = 0.15; rp.color_ramp.elements[1].position = 0.45
    lk.new(nz.outputs['Distance'], rp.inputs['Fac'])
    tr = nt.new('ShaderNodeBsdfTransparent')
    mx = nt.new('ShaderNodeMixShader'); lk.new(rp.outputs['Color'], mx.inputs['Fac'])
    lk.new(bs.outputs[0], mx.inputs[1]); lk.new(tr.outputs[0], mx.inputs[2]); lk.new(mx.outputs[0], nt['Material Output'].inputs['Surface'])


def set_bone(rig, name, euler):
    pb = rig.pose.bones[name]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = euler


if not NOCHARS:
    if not SPLASH:
        A, Bp = (-1.0, -0.15), (1.0, 0.15)
        sumo('sumo2_stance.glb', A, Bp)
        sumo('sumo2_red.glb', Bp, A)
        GX, GY = 0.4, 5.0
        _, gr = load('gyoji.glb')
        for r in gr: r.location = (GX, GY, main_z(GX, GY)); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
        scn.frame_set(1)
        for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
            if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
        gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
        mask('kitsune', Vector((GX, GY, main_z(GX, GY) + 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)
    else:
        # the winner stands at the edge in his stance, having just pushed; the loser flies backwards into the pond
        W = (SPL_C.x * 0.42, SPL_C.y * 0.42)
        sumo('sumo2_stance.glb', W, (SPL_C.x, SPL_C.y))
        rig, roots = sumo('sumo2_red.glb', (SPL_C.x, SPL_C.y), (0, 0), keep_action=False)
        yaw = roots[0].rotation_euler.z
        tilt = float(OPT.get('tilt', 0.75))
        for r in roots: r.rotation_euler = (tilt, 0.15, yaw)
        # arms flung up and out, legs kicking
        for sd, s in (('L', 1), ('R', float(OPT.get('rsign', 1)))):
            set_bone(rig, 'upper_arm.' + sd, (0.0, 0.0, s * 1.9))
            set_bone(rig, 'forearm.' + sd, (0.0, 0.0, s * 0.5))
            set_bone(rig, 'shoulder.' + sd, (0.0, 0.0, s * 0.25))
        set_bone(rig, 'thigh.L', (-0.9, 0, 0)); set_bone(rig, 'shin.L', (1.0, 0, 0))
        set_bone(rig, 'thigh.R', (-0.35, 0, 0)); set_bone(rig, 'shin.R', (0.5, 0, 0))
        set_bone(rig, 'head', (-0.35, 0, 0))
        scn.frame_set(1); bpy.context.view_layer.update()
        hip = rig.matrix_world @ rig.pose.bones['hips'].head
        want = Vector((SPL_C.x, SPL_C.y, float(OPT.get('hipz', 0.4))))
        for r in roots: r.location += want - hip
        bpy.context.view_layer.update()
        GX, GY = 0.4, 5.0
        _, gr = load('gyoji.glb')
        for r in gr: r.location = (GX, GY, main_z(GX, GY)); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi + 0.5)
        scn.frame_set(1)
        for (rig_, roots_), kind in zip(RIGS, ('oni', 'hannya')):
            if rig_: c, f, u = head_frame(rig_, roots_); mask(kind, c + f * 0.03, f, u, roots_[0].scale[0] * 0.95)
        gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
        mask('kitsune', Vector((GX, GY, main_z(GX, GY) + 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)
if SPLASH and 'nosplash' not in OPT:
    SPL = build_splash(SPL_C)


# ================================================================ cameras & render
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 400
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
scn.cycles.max_bounces = 10; scn.cycles.glossy_bounces = 4; scn.cycles.transmission_bounces = 10; scn.cycles.volume_bounces = 0
scn.cycles.transparent_max_bounces = 8; scn.cycles.diffuse_bounces = 3
scn.cycles.caustics_reflective = False; scn.cycles.caustics_refractive = False
scn.cycles.sample_clamp_indirect = 6.0
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.use_nodes = True; cnt = scn.node_tree
rl = cnt.nodes['Render Layers']; comp = cnt.nodes['Composite']
gl = cnt.nodes.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 1.5; gl.mix = -0.85; gl.size = 8
cnt.links.new(rl.outputs['Image'], gl.inputs['Image']); cnt.links.new(gl.outputs['Image'], comp.inputs['Image'])

VIEWS = {'flower': ((8.6, 2.0, 2.0), (11.4, 5.5, 0.2), 30), 'frog': ((-6.6, 1.2, 1.6), (-8.9, 3.9, 0.35), 30),
         'dfly': ((-4.2, 3.6, 2.4), (-6.2, 6.4, 1.9), 30), 'notch': ((0.2, 1.0, 2.2), (-2.6, 4.7, 0.0), 40),
         'rim': ((4.5, -7.5, 0.6), (3.0, -4.0, 0.0), 35), 'reeds': ((-8, 2, 3.0), (-15.5, 11.0, 2.0), 45)}
for shot in SHOTS:
    if shot == 'game':   # the game camera, 'wide' framing of stage_render.py
        el = math.radians(50); dist = 21
        cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
        cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'low':  # the low three-quarter view from the front-right
        cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
        cam.rotation_euler = (Vector((0, 0.8, 0.4)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot in VIEWS:   # close-ups for look-dev
        c_, t_, fv = VIEWS[shot]
        cam.location = c_; cam.data.angle_y = math.radians(fv)
        cam.rotation_euler = (Vector(t_) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'cam':
        cam.location = Vector(eval(OPT['cam'])); cam.data.angle_y = math.radians(float(OPT.get('fov', 30)))
        cam.rotation_euler = (Vector(eval(OPT['tgt'])) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'splash':
        cam.location = Vector(eval(OPT.get('scam', '(2.0, -15.5, 2.9)'))); cam.data.angle_y = math.radians(float(OPT.get('sfov', 34)))
        cam.rotation_euler = (Vector(eval(OPT.get('stgt', '(-3.9, -3.3, 1.05)'))) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = os.path.join(OUT, OPT.get('prefix', 'ex_') + shot + '.png')
    bpy.ops.render.render(write_still=True)
    print('wrote', scn.render.filepath)
