# SUSHI TRAIN stage props: kaiten-zushi plates, nigiri, maki, gunkan and the table pieces, built entirely by script
# (Blender 4.2, run headless).
#   python tools/blender/sushi.py  [out_dir]  [shot=hero shot=close shot=lineup shot=flat ...]  [noprev]
# Writes <out_dir>/sushi_set.glb (one top-level object per prop, origin at its base centre, Z up, real metres) and
# preview renders <out_dir>/prev_*.png.
# The recipe: lathe (spin) profiles rounded with Chaikin for every ceramic piece; nigiri / maki rice built from a
# few hundred real grain shapes scattered over a core and fused with a voxel remesh, then decimated (lumpy, grainy
# silhouettes with sane triangle counts); fish slices are lofted 'pillows' (thick in the middle, feathered rounded
# edges, thinner at the ends) draped over the actual rice with ray casts; all fine detail (salmon fat lines, shrimp
# stripes, nori fibre, tamago layers, plate patterns, the kanji on the cup) is painted with numpy into small packed
# textures that feed Base Color directly, so a flat toon shader still reads them.
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

DEF_OUT = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad/sushi'
ARGS = [a for a in sys.argv[1:] if '=' not in a and a != 'noprev' and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else DEF_OUT
os.makedirs(OUT, exist_ok=True)
SHOTS = set(a.split('=', 1)[1] for a in sys.argv if a.startswith('shot='))
NOPREV = 'noprev' in sys.argv
KANJI_FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi


# ================================================================ helpers: colour, materials, textures
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def mat(name, base, rough=0.5, img=None, sss=0.0, sss_rad=(1.0, 0.45, 0.25), sss_scale=0.002, coat=0.0, trans=0.0,
        spec=0.5, sheen=0.0, ior=1.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(base), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = sss_rad
    b.inputs['Subsurface Scale'].default_value = sss_scale
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.08
    b.inputs['Transmission Weight'].default_value = trans
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['IOR'].default_value = ior
    if img is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t.interpolation = 'Linear'; t.location = (-400, 200)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m

def image(name, arr):
    """arr: (h, w, 3) sRGB floats, row 0 = v 0 (bottom). Packed into the .blend so the GLB embeds it."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(px.ravel()); img.file_format = 'PNG'; img.pack()
    return img

def vnoise(h, w, cy, cx, rng):
    """tileable value noise, cy x cx cells"""
    g = rng.random((cy, cx)).astype(np.float32)
    ys = np.arange(h) * cy / h; xs = np.arange(w) * cx / w
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    fy = ys - y0; fx = xs - x0; fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % cy; x1 = (x0 + 1) % cx; y0 %= cy; x0 %= cx
    a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
    fx = fx[None, :]; fy = fy[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
def fbm(h, w, cy, cx, octv, rng, gain=0.5):
    s = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for i in range(octv):
        s += amp * vnoise(h, w, cy * 2 ** i, cx * 2 ** i, rng); tot += amp; amp *= gain
    return s / tot
def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2: t = t[..., None]
    return a * (1 - t) + b * t
def blur(a, n=1):
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a
def grid(h, w):
    v, u = np.meshgrid((np.arange(h) + 0.5) / h, (np.arange(w) + 0.5) / w, indexing='ij'); return u, v


# ================================================================ helpers: meshes
def mk(name, verts, faces, m=None, uvs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(float(c) for c in v) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.validate(); me.update()
    if uvs is not None:
        uv = me.uv_layers.new(name='UVMap')
        vi = np.empty(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', vi)
        uv.data.foreach_set('uv', np.asarray(uvs, np.float32)[vi].ravel())
    if smooth: me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    if m is not None: me.materials.append(m)
    return o

def activate(o):
    for x in bpy.context.view_layer.objects: x.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
def apply_mod(o, md): activate(o); bpy.ops.object.modifier_apply(modifier=md.name)
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
def decimate(o, target):
    n = tris(o)
    if n > target:
        d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = target / n; apply_mod(o, d)
def smooth_all(o): o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
def join(objs, name):
    objs = [o for o in objs if o is not None]
    activate(objs[0])
    for o in objs[1:]: o.select_set(True)
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name; return o
def xf(o, M): o.data.transform(M); o.data.update(); return o
def fix_normals(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
def bvh_of(objs):
    V, P = [], []
    for o in objs:
        base = len(V); M = o.matrix_world
        V += [M @ v.co for v in o.data.vertices]; P += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(V, P)
def rot(axis, deg): return Matrix.Rotation(math.radians(deg), 4, axis)
def T(x, y, z): return Matrix.Translation((x, y, z))
def S(x, y, z): return Matrix.Diagonal((x, y, z, 1))

def superell(ax, ay, az, e1=1.0, e2=1.0, nu=32, nv=16):
    """superellipsoid (e<1 boxier, 1 = ellipsoid), returns verts, faces"""
    f = lambda c, e: math.copysign(abs(c) ** e, c)
    V = [(0, 0, -az)]
    for i in range(1, nv):
        ph = -math.pi / 2 + math.pi * i / nv
        for k in range(nu):
            th = TAU * k / nu
            V.append((ax * f(math.cos(ph), e1) * f(math.cos(th), e2), ay * f(math.cos(ph), e1) * f(math.sin(th), e2), az * f(math.sin(ph), e1)))
    V.append((0, 0, az)); N = len(V) - 1
    ring = lambda i, k: 1 + (i - 1) * nu + k % nu
    F = [(0, ring(1, k + 1), ring(1, k)) for k in range(nu)]
    for i in range(1, nv - 1):
        F += [(ring(i, k), ring(i, k + 1), ring(i + 1, k + 1), ring(i + 1, k)) for k in range(nu)]
    F += [(ring(nv - 1, k), ring(nv - 1, k + 1), N) for k in range(nu)]
    return np.array(V), F

def chaikin(pts, it=2):
    pts = [np.array(p, float) for p in pts]
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): out += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        out.append(pts[-1]); pts = out
    return pts
def simplify(pts, tol):
    pts = [np.array(p) for p in pts]
    def rec(a, b):
        if b <= a + 1: return [a]
        A, B = pts[a], pts[b]; d = B - A; L = np.linalg.norm(d) + 1e-12
        best, bi = -1, a
        for i in range(a + 1, b):
            dist = abs(d[0] * (pts[i] - A)[1] - d[1] * (pts[i] - A)[0]) / L
            if dist > best: best, bi = dist, i
        return rec(a, bi) + rec(bi, b) if best > tol else [a]
    return [tuple(pts[i]) for i in rec(0, len(pts) - 1)] + [tuple(pts[-1])]
def profile(ctrl, it=2, tol=0.00004): return simplify(chaikin(ctrl, it), tol)

def lathe(name, prof, seg, m, vfun=None, planar=None):
    """spin an (r, z) profile round Z. Profile runs counter-clockwise in the r-z plane (outside on the right as you walk).
    UVs: planar (top-down, `planar` = size in metres of the 0..1 square) or (angle, vfun(i, r, z))"""
    V, UV, idx = [], [], []
    for i, (r, z) in enumerate(prof):
        row = []
        for k in range(seg + 1):
            a = TAU * k / seg; row.append(len(V)); V.append((r * math.cos(a), r * math.sin(a), z))
            UV.append((0.5 + r * math.cos(a) / planar, 0.5 + r * math.sin(a) / planar) if planar else (k / seg, vfun(i, r, z)))
        idx.append(row)
    F = []
    for i in range(len(prof) - 1):
        for k in range(seg):
            a, b, c, d = idx[i][k], idx[i][k + 1], idx[i + 1][k + 1], idx[i + 1][k]
            if prof[i][0] < 1e-9: F.append((a, c, d))
            elif prof[i + 1][0] < 1e-9: F.append((a, b, c))
            else: F.append((a, b, c, d))
    return mk(name, V, F, m, UV)

def resample(pts, n):
    """closed polyline -> n points evenly spaced by arc length"""
    P = np.array(pts, float); Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])], 1)


# ================================================================ rice: real grains fused over a core, then crisp grains on top
_G = superell(1, 1, 1, 1, 1, 8, 5)
_GC = superell(1, 1, 1, 1, 1, 8, 4)          # 48 triangles: the crisp grains that sit on the surface
def _scatter(tri, n, keep, rng, mind=0.0):
    w = np.array([t[4] for t in tri]); w /= w.sum()
    out, tries = [], 0
    while len(out) < n and tries < n * 60:
        tries += 1
        a, b, c, nrm, _ = tri[rng.choice(len(tri), p=w)]
        u, v = rng.random(2)
        if u + v > 1: u, v = 1 - u, 1 - v
        p = a + (b - a) * u + (c - a) * v
        if not keep(p, nrm): continue
        if mind and any((p - q).length < mind for q, _ in out): continue
        out.append((p, nrm))
    return out
def _tris_of(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces); bm.normal_update()
    tri = [(f.verts[0].co.copy(), f.verts[1].co.copy(), f.verts[2].co.copy(), f.normal.copy(), f.calc_area()) for f in bm.faces]
    bm.free(); return tri
def _grains(samples, rng, G, gsize, sink, tilt=0.28):
    GV, GF = G; V, F = [], []
    for p, nrm in samples:
        nn = (nrm + Vector(rng.normal(0, tilt, 3))).normalized()                     # grains don't lie perfectly flat
        t = nn.orthogonal().normalized(); ang = rng.random() * TAU
        t = (t * math.cos(ang) + nn.cross(t) * math.sin(ang)).normalized(); bb = nn.cross(t)
        Rm = Matrix((t, bb, nn)).transposed()
        sz = np.array((0.0031, 0.00165, 0.00135)) * gsize * rng.uniform(0.85, 1.12)
        sz[2] *= rng.uniform(0.9, 1.15)
        ctr = p + nrm * rng.uniform(*sink)
        base = len(V)
        V += [ctr + Rm @ Vector(gv * sz) for gv in GV]
        F += [tuple(base + i for i in f) for f in GF]
    return V, F
def rice(name, core, n, keep, target, m, voxel=0.0005, seed=1, gsize=1.0, sink=(0.0002, 0.0007), crisp=0, ckeep=None, csink=(-0.0006, -0.0002), cgsize=None):
    """core + n grains fused (voxel remesh, decimated to `target`) for a lumpy body, then `crisp` separate low-poly grains
    scattered over that body where ckeep(p, n) allows, so the rice reads as grains, not as a lumpy blob"""
    rng = np.random.default_rng(seed)
    V, F = _grains(_scatter(_tris_of(core), n, keep, rng), rng, _G, gsize, sink)
    grains = mk(name + '_g', V, F)
    o = join([core, grains], name)
    r = o.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = voxel; r.adaptivity = 0; apply_mod(o, r)
    s = o.modifiers.new('sm', 'SMOOTH'); s.factor = 0.5; s.iterations = 2; apply_mod(o, s)
    decimate(o, target)
    o.data.materials.clear(); o.data.materials.append(m); smooth_all(o)
    if crisp:
        cg_ = cgsize or gsize * 1.02
        V, F = _grains(_scatter(_tris_of(o), crisp, ckeep or keep, rng, mind=0.0026 * cg_), rng, _GC, cg_, csink, 0.35)
        cg = mk(name + '_c', V, F, m)
        o = join([o, cg], name)
    return o


# ================================================================ fish slices: a lofted pillow draped over the rice
def slab(name, outline, Th, drape, m, nr=8, thick=None, rice_bvh=None, margin=0.0003, uvf=None, edge=4.0, pw=0.45):
    P = np.array(outline); nt = len(P); c = P.mean(0)
    rs = np.sin(np.pi / 2 * np.arange(nr + 1) / nr)
    X = c[None, None] + rs[:, None, None] * (P[None] - c[None, None])
    x, y = X[..., 0], X[..., 1]
    t = Th * np.clip(1 - rs ** edge, 0, 1)[:, None] ** pw * np.ones_like(x)
    if thick is not None: t = t * thick(x, y)
    t[-1] = 0
    mid = drape(x, y)
    if rice_bvh is not None:
        need = np.zeros_like(x)
        for i in range(nr + 1):
            for k in range(nt):
                loc, _, _, _ = rice_bvh.ray_cast(Vector((x[i, k], y[i, k], 0.2)), Vector((0, 0, -1)))
                if loc is not None: need[i, k] = max(0.0, loc.z + margin - (mid[i, k] - t[i, k] / 2))
        L = need.copy()
        for _ in range(10):   # spread the lift smoothly, never below what each point needs
            nb = (np.roll(L, 1, 1) + np.roll(L, -1, 1) + np.vstack([L[:1], L[:-1]]) + np.vstack([L[1:], L[-1:]]) + L) / 5
            L = np.maximum(need, nb)
        mid = mid + L
    top, bot = mid + t / 2, mid - t / 2
    V, UVs = [], []
    def add(px, py, pz):
        V.append((px, py, pz)); UVs.append(uvf(px, py) if uvf else (0, 0)); return len(V) - 1
    ct = add(x[0, 0], y[0, 0], top[0, 0])
    Tr = [[ct] * nt] + [[add(x[i, k], y[i, k], top[i, k]) for k in range(nt)] for i in range(1, nr + 1)]
    cb = add(x[0, 0], y[0, 0], bot[0, 0])
    Br = [[cb] * nt] + [[add(x[i, k], y[i, k], bot[i, k]) for k in range(nt)] for i in range(1, nr)] + [Tr[nr]]
    F = []
    for k in range(nt):
        k2 = (k + 1) % nt
        F.append((ct, Tr[1][k], Tr[1][k2])); F.append((cb, Br[1][k2], Br[1][k]))
        for i in range(1, nr):
            F.append((Tr[i][k], Tr[i + 1][k], Tr[i + 1][k2], Tr[i][k2]))
            F.append((Br[i][k2], Br[i + 1][k2], Br[i + 1][k], Br[i][k]))
    return mk(name, V, F, m, UVs)


# ================================================================ nori: a wrapped sheet, a spiral strip with an overlap seam
def nori_wrap(name, a, b, h, m, seg=64, seed=3, rows=4, flare=0.0004, z0=0.0):
    rng = np.random.default_rng(seed)
    over = 0.55                                          # radians of overlap where the sheet's end laps over its start
    fr = rng.integers(2, 9, 5); ph = rng.random(5) * TAU; am = rng.uniform(0.3, 1.0, 5)
    edge = lambda th: sum(am[i] * math.sin(fr[i] * th + ph[i]) for i in range(5)) / am.sum()
    wr = lambda th: math.sin(9 * th + 1.3) * 0.6 + math.sin(14 * th + 0.4) * 0.4
    n = int(seg * (1 + over / TAU)) + 1
    V, UV = [], []
    for j in range(n):
        th = (TAU + over) * j / (n - 1); grow = 0.00055 * th / TAU          # the outer layer sits on the inner one
        for r_ in range(rows):
            f = r_ / (rows - 1); z = z0 + h * f
            if r_ == rows - 1: z += 0.0006 * edge(th)                       # torn, uneven top edge
            d = grow + flare * f ** 2 + 0.00022 * wr(th) * (0.3 + f)        # flares open a touch at the top, soft wrinkles
            V.append(((a + d) * math.cos(th), (b + d) * math.sin(th), z))
            UV.append((th / TAU * 2.0, f))
    F = [(j * rows + r_, (j + 1) * rows + r_, (j + 1) * rows + r_ + 1, j * rows + r_ + 1) for j in range(n - 1) for r_ in range(rows - 1)]
    o = mk(name, V, F, m, UV)
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = 0.0005; s.offset = -1; apply_mod(o, s)
    return o


# ================================================================ textures
R = np.random.default_rng(11)

def tex_nori(w=256, h=256):
    u, v = grid(h, w)
    base = hx('1b2619')
    n1 = fbm(h, w, 6, 6, 4, R); fib = fbm(h, w, 64, 6, 2, R); sp = vnoise(h, w, 128, 128, R)
    c = mix(base, hx('33432a'), sstep(0.5, 0.85, n1) * 0.8)            # lighter green patches
    c = mix(c, hx('46563a'), sstep(0.62, 0.9, fib) * 0.5)               # fibres
    c = mix(c, hx('0d120c'), sstep(0.72, 0.9, sp) * 0.7)                # pin holes / dark specks
    c = mix(c, hx('2a3a2f'), sstep(0.55, 0.75, fbm(h, w, 3, 20, 2, R)) * 0.35)
    return image('nori', c)

def tex_salmon(L, W, w=512, h=256, seed=5):
    rng = np.random.default_rng(seed)
    u, v = grid(h, w); x = (u - 0.5) * L; y = (v - 0.5) * W
    warp = (fbm(h, w, 2, 4, 3, rng) - 0.5) * 0.0045
    s = x * math.cos(1.05) + y * math.sin(1.05) + 0.0075 * (y / (W / 2)) ** 2 + warp       # curved bands across the slice
    s = s + 0.0035 * (np.abs(y) / (W / 2)) ** 1.6
    ph = s / 0.0056 + (fbm(h, w, 1, 4, 2, rng) - 0.5) * 1.2
    f = ph - np.floor(ph); d = np.minimum(f, 1 - f)
    wid = 0.035 + 0.075 * fbm(h, w, 3, 10, 2, rng) * (0.5 + 0.5 * np.sin(np.floor(ph) * 2.7) ** 2)
    line = 1 - sstep(wid * 0.3, wid, d)
    ph2 = ph * 2 + 0.5; f2 = ph2 - np.floor(ph2); d2 = np.minimum(f2, 1 - f2)
    thin = (1 - sstep(0.012, 0.03, d2)) * sstep(0.45, 0.7, fbm(h, w, 2, 8, 2, rng))          # some faint secondary lines
    halo = 1 - sstep(wid, wid * 3.5, d)
    flesh = mix(hx('ee5a22'), hx('fb8443'), sstep(-0.7, 1.0, y / (W / 2)))                 # belly side paler
    flesh = mix(flesh, hx('e04a18'), sstep(0.55, 0.9, fbm(h, w, 3, 6, 3, rng)) * 0.45)
    flesh = mix(flesh, hx('ff9a62'), halo * 0.35)
    c = mix(flesh, hx('ffd9c2'), thin * 0.45)
    c = mix(c, hx('ffdcc6'), line * 0.88)
    c = mix(c, hx('ffb08a'), sstep(0.8, 1.0, np.abs(y) / (W / 2)) * 0.35)
    c = mix(c, hx('ffb48a'), sstep(0.92, 1.0, np.abs(y) / (W / 2)) * 0.5)
    return image('salmon', c)

def tex_tuna(L, W, w=256, h=128):
    u, v = grid(h, w); x = (u - 0.5) * L; y = (v - 0.5) * W
    n = fbm(h, w, 3, 6, 4, R)
    s = x * math.cos(1.2) + y * math.sin(1.2) + 0.006 * (y / (W / 2)) ** 2 + (fbm(h, w, 2, 4, 2, R) - 0.5) * 0.006
    ph = s / 0.0062; f = ph - np.floor(ph); d = np.minimum(f, 1 - f)
    line = 1 - sstep(0.015, 0.05, d)
    c = mix(hx('a3162a'), hx('b8243a'), n)
    c = mix(c, hx('861022'), sstep(0.6, 0.9, fbm(h, w, 5, 9, 3, R)) * 0.5)
    c = mix(c, hx('c9485a'), line * 0.35)                                                  # faint sinew lines
    return image('tuna', c)

def tex_ebi(L, W, xt, xh, wfun, w=512, h=256):
    u, v = grid(h, w); x = (u - 0.5) * L; y = (v - 0.5) * W
    ww = np.maximum(wfun(np.clip(x, xh, xt)), 0.004); ay = np.clip(np.abs(y) / ww, 0, 1.3)
    seg = (xt - xh) / 6.2
    ph = (x - xh) / seg + 0.35 * ay ** 2 + (fbm(h, w, 2, 6, 2, R) - 0.5) * 0.15            # stripes bow toward the head
    f = ph - np.floor(ph)
    band = sstep(0.12, 0.38, f) * (1 - sstep(0.62, 0.92, f))
    core = sstep(0.3, 0.5, f) * (1 - sstep(0.5, 0.75, f))
    red = np.clip(band * 0.9 + sstep(0.65, 1.0, ay) * 0.75, 0, 1)
    c = mix(hx('fdf3e8'), hx('f6643c'), red)
    c = mix(c, hx('e2361f'), core * 0.6 * red)
    c = mix(c, hx('f2d6c4'), (1 - sstep(0.0, 0.05, ay)) * 0.6)                               # the butterfly fold
    c = mix(c, hx('fff8f0'), sstep(0.55, 0.85, fbm(h, w, 6, 12, 2, R)) * 0.15 * (1 - red))
    return image('ebi', c)

def tex_ebi_tail(w=128, h=64):
    u, v = grid(h, w)
    c = mix(hx('f6905a'), hx('e8401f'), sstep(0.1, 0.5, u))
    c = mix(c, hx('a51d14'), sstep(0.7, 1.0, u))
    rays = 0.5 + 0.5 * np.sin((v - 0.5) * 40 + u * 2)
    c = mix(c, hx('c62a18'), rays * 0.15 * sstep(0.2, 0.6, u))
    return image('ebi_tail', c)

def tex_tamago(w=256, h=256):
    u, v = grid(h, w)
    c = np.zeros((h, w, 3), np.float32)
    top = v >= 0.5
    n = fbm(h, w, 6, 6, 4, R)
    ctop = mix(hx('f6c445'), hx('eaa62e'), sstep(0.55, 0.85, n) * 0.8)                     # lightly browned patches
    ctop = mix(ctop, hx('d78f2a'), sstep(0.75, 0.95, fbm(h, w, 10, 10, 2, R)) * 0.45)
    zz = (v % 0.5) / 0.5                                                                    # side regions: z 0..1
    lay = zz * 6.5 + (fbm(h, w, 2, 6, 2, R) - 0.5) * 0.6
    f = lay - np.floor(lay); d = np.minimum(f, 1 - f)
    cs = mix(hx('fbd35a'), hx('f4bc3e'), sstep(0.0, 0.5, f))
    cs = mix(cs, hx('dc9a2a'), (1 - sstep(0.02, 0.07, d)) * 0.7)                           # thin browned layer lines
    c = np.where(top[..., None], ctop, cs)
    return image('tamago', c)

def tex_plate(name, rim, w=512):
    u, v = grid(w, w); x = (u - 0.5) * 0.16; y = (v - 0.5) * 0.16
    r = np.hypot(x, y); th = np.arctan2(y, x)
    glaze = hx('f7f4ec'); col = hx(rim); tint = mix(col, hx('ffffff'), 0.55)
    c = np.ones((w, w, 3), np.float32) * glaze
    c = mix(c, hx('ece6d8'), sstep(0.3, 0.8, fbm(w, w, 5, 5, 3, R)) * 0.35)                 # glaze pooling
    sp = vnoise(w, w, 256, 256, R)
    c = mix(c, hx('8b7a68'), sstep(0.965, 0.995, sp) * 0.45)                                  # iron speckles
    # seigaiha (overlapping wave scales) in a lighter tint over the rim band
    r0, r1, Rw, ncell = 0.0652, 0.0765, 0.0032, 68
    s = (th / TAU) * ncell; tt = (r - r0) / Rw
    best = np.full(r.shape, 99.0); dbest = np.zeros_like(r)
    for j in range(int((r1 - r0) / Rw * 2) + 3):
        sh = 0.5 * (j % 2); tc = j * 0.5
        sc = np.floor(s - sh + 0.5) + sh
        d = np.hypot((s - sc) * 2, tt - tc)
        ok = (tt >= tc) & (d < 1.0) & (best > 98)
        dbest = np.where(ok, d, dbest); best = np.where(ok, j, best)
    arcs = np.zeros_like(r)
    for k in (1.0, 0.68, 0.36):
        arcs = np.maximum(arcs, 1 - sstep(0.035, 0.085, np.abs(dbest - k)))
    inband = sstep(r0 - 0.0003, r0 + 0.0003, r)
    bandc = mix(col, tint, arcs * (best < 98))
    c = mix(c, bandc, inband)
    c = mix(c, col, (1 - sstep(0.0003, 0.0007, np.abs(r - 0.0603))))                        # a fine line inside the band
    c = mix(c, mix(col, hx('000000'), 0.15), sstep(0.0745, 0.0758, r))                     # rim edge a touch deeper
    return image('plate_' + name, c)

def glyph_mask(ch, h, w, box):
    """rasterise a glyph (via a Blender text object -> triangles) into a (h, w) mask inside box=(x0, y0, x1, y1) px"""
    m = np.zeros((h, w), np.float32)
    if not os.path.exists(KANJI_FONT): return m
    cu = bpy.data.curves.new('glyph', 'FONT'); cu.body = ch; cu.font = bpy.data.fonts.load(KANJI_FONT)
    ob = bpy.data.objects.new('glyph', cu); scn.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces)
    tri = [[v.co.xy.copy() for v in f.verts] for f in bm.faces]; bm.free()
    ob.evaluated_get(dg).to_mesh_clear(); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    P = np.array([[p.x, p.y] for t in tri for p in t]); mn, mxp = P.min(0), P.max(0)
    x0, y0, x1, y1 = box
    def tp(p): return (x0 + (p.x - mn[0]) / (mxp[0] - mn[0]) * (x1 - x0), y0 + (p.y - mn[1]) / (mxp[1] - mn[1]) * (y1 - y0))
    for t in tri:
        (ax_, ay_), (bx_, by_), (cx_, cy_) = tp(t[0]), tp(t[1]), tp(t[2])
        xa, xb = int(max(min(ax_, bx_, cx_) - 1, 0)), int(min(max(ax_, bx_, cx_) + 2, w))
        ya, yb = int(max(min(ay_, by_, cy_) - 1, 0)), int(min(max(ay_, by_, cy_) + 2, h))
        if xb <= xa or yb <= ya: continue
        Y, X = np.mgrid[ya:yb, xa:xb] + 0.5
        d = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
        if abs(d) < 1e-12: continue
        l1 = ((by_ - cy_) * (X - cx_) + (cx_ - bx_) * (Y - cy_)) / d
        l2 = ((cy_ - ay_) * (X - cx_) + (ax_ - cx_) * (Y - cy_)) / d
        ins = (l1 >= 0) & (l2 >= 0) & (1 - l1 - l2 >= 0)
        m[ya:yb, xa:xb] = np.maximum(m[ya:yb, xa:xb], ins)
    return m

def tex_cup(w=512, h=512):
    u, v = grid(h, w)
    n = fbm(h, w, 8, 4, 3, R)
    body = mix(hx('e7dcc3'), hx('d9caa8'), sstep(0.35, 0.8, n))                           # oatmeal glaze
    body = mix(body, hx('6b4e33'), sstep(0.94, 0.99, vnoise(h, w, 200, 200, R)) * 0.7)       # speckle
    c = body.copy()
    # iron-brown dipped rim, with a drippy lower edge
    drip = 0.86 - 0.025 * fbm(h, w, 1, 14, 2, R) - 0.03 * sstep(0.75, 0.95, fbm(h, w, 1, 22, 1, R))
    c = mix(c, mix(hx('6e3b1e'), hx('8f5328'), n), sstep(drip, drip + 0.006, v) * (v < 0.93))
    c = mix(c, hx('6e3b1e'), sstep(0.982, 0.99, v))                                        # rim inside
    c = mix(c, hx('b98d63'), 1 - sstep(0.045, 0.055, v))                                    # unglazed foot
    # two brushed bands near the base
    for vb in (0.17, 0.2):
        c = mix(c, hx('34436a'), (1 - sstep(0.002, 0.005, np.abs(v - vb - 0.003 * np.sin(u * TAU * 3)))) * 0.85)
    # the kanji: on the cup's 0.21 m circumference this box is ~32 x 38 mm
    g = np.zeros((h, w), np.float32)
    for uc in (0.25, 0.75):
        g = np.maximum(g, glyph_mask('寿', h, w, (int((uc - 0.075) * w), int(0.33 * h), int((uc + 0.075) * w), int(0.73 * h))))
    g = blur(g, 3); g = sstep(0.18, 0.45, g + (fbm(h, w, 30, 30, 2, R) - 0.5) * 0.3)        # a slightly ragged brush edge
    c = mix(c, hx('2a3557'), g * 0.95 * (v > 0.06) * (v < 0.93))
    return image('teacup', c)

def tex_soydish(w=256, h=256):
    u, v = grid(h, w)
    c = mix(hx('f4efe4'), hx('e6dfcf'), fbm(h, w, 6, 6, 3, R) * 0.6)
    indigo = mix(hx('22346a'), hx('2f4a8a'), fbm(h, w, 8, 4, 3, R))
    c = np.where((v < 0.5)[..., None], indigo, c)                                          # outside: indigo
    c = mix(c, indigo, sstep(0.93, 0.95, v))                                               # rim: indigo
    c = mix(c, hx('2f4a8a'), (1 - sstep(0.004, 0.008, np.abs(v - 0.86))) * 0.9)              # a line inside the rim
    return image('soydish', c)

def tex_gari(w=128, h=128):
    u, v = grid(h, w); r = np.hypot(u - 0.5, v - 0.5) * 2
    c = mix(hx('fde3d8'), hx('f7aeb0'), sstep(0.25, 1.0, r))
    fib = fbm(h, w, 4, 40, 2, R)
    c = mix(c, hx('fff6ee'), sstep(0.55, 0.8, fib) * 0.35)
    c = mix(c, hx('f2a3a6'), sstep(0.88, 1.0, r) * 0.6)
    return image('gari', c)

def tex_wood_stick(w=256, h=32):
    u, v = grid(h, w)
    g = fbm(h, w, 4, 40, 3, R)
    wood = mix(hx('e2c08f'), hx('c49563'), sstep(0.45, 0.75, g))
    lac = mix(hx('7e1a1c'), hx('5a1114'), fbm(h, w, 2, 16, 2, R) * 0.6)
    c = mix(lac, wood, sstep(0.39, 0.41, u))                                               # lacquered handle, bare wood tips
    c = mix(c, hx('d9b25a'), (1 - sstep(0.004, 0.009, np.abs(u - 0.405))) * 0.9)            # a thin gold line
    return image('chopsticks', c)


# ================================================================ materials
IMG_NORI = tex_nori()
RICE = mat('Rice', 'ebe4d4', 0.42, sss=0.12, sss_rad=(1.0, 0.85, 0.6), sss_scale=0.0008, sheen=0.1)
NORI = mat('Nori', '1b2619', 0.62, IMG_NORI, spec=0.35)
IKURA = mat('Ikura', 'ff6a12', 0.04, sss=1.0, sss_rad=(1, 0.3, 0.08), sss_scale=0.004, coat=1.0, ior=1.38)
WASABI = mat('Wasabi', 'a9c34e', 0.6, sss=0.2, sss_rad=(0.5, 1.0, 0.3), sss_scale=0.0015)
SOY = mat('Soy', '3a1608', 0.12, spec=0.35)
TEA = mat('GreenTea', 'a3a63c', 0.03, coat=0.3, spec=0.6)
CUKE_SKIN = mat('CucumberSkin', '2d6a2a', 0.4)
CUKE = mat('Cucumber', 'cfe39a', 0.45, sss=0.3, sss_rad=(0.6, 1.0, 0.4), sss_scale=0.0015)
TUNA_CORE = mat('TunaFilling', 'a8192d', 0.3, sss=0.25, sss_scale=0.0015, coat=0.3)
REST = mat('RestCeramic', '6f9d8e', 0.18, coat=0.3)
ASSETS = {}
LAYOUT = {}

def finalize(name, objs, pos):
    o = join(objs, name)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges); bm.to_mesh(o.data); bm.free()
    o.data.validate()
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    base = Vector(((co[:, 0].min() + co[:, 0].max()) / 2, (co[:, 1].min() + co[:, 1].max()) / 2, co[:, 2].min()))
    o.data.transform(Matrix.Translation(-base)); o.data.update(); o.location = pos
    ASSETS[name] = o
    print('built %-16s %6d tris' % (name, tris(o)), flush=True)
    return o


# ================================================================ plates
PLATE_PROF = profile([(0, 0.0042), (0.040, 0.0042), (0.0425, 0.0006), (0.0438, 0.0), (0.0462, 0.0), (0.0475, 0.0006), (0.049, 0.0040),
                      (0.0712, 0.0142), (0.0752, 0.0176), (0.0759, 0.0196), (0.0750, 0.0213), (0.0731, 0.0214), (0.0702, 0.0192),
                      (0.0535, 0.0100), (0.0485, 0.0081), (0.025, 0.0076), (0, 0.0075)], it=3, tol=0.00012)
PLATE_FLOOR = 0.0075
for i, (nm, col) in enumerate((('red', 'cf3a3e'), ('yellow', 'f1b52c'), ('blue', '2d5fb2'), ('green', '3f9a5e'))):
    pm = mat('Plate_' + nm, 'f7f4ec', 0.12, tex_plate(nm, col), coat=0.5)
    finalize('plate_' + nm, [lathe('plate_' + nm, PLATE_PROF, 52, pm, planar=0.16)], (-0.27 + i * 0.18, 0.0, 0))


# ================================================================ nigiri
def nigiri_rice(seed, ax=0.0228, ay=0.0106, az=0.0097, n=150, target=1000, cover=0.78, crisp=40):
    V, F = superell(ax, ay, az, 0.75, 0.55, 32, 16)
    V[:, 2] += 0.0088; V[:, 2] = np.maximum(V[:, 2], 0.0006)
    core = mk('rice', V, F)
    return rice('rice', core, n, lambda p, nrm: p.z > 0.0028 and nrm.z < cover, target, RICE, seed=seed,
                crisp=crisp, ckeep=lambda p, nrm: p.z > 0.0022 and nrm.z < 0.55)

RICE_TOP = 0.0198
def outline_slice(a, b, p=3.2, shear=0.3, taper=0.1, n=44):
    pts = []
    for k in range(240):
        th = TAU * k / 240; c, s = math.cos(th), math.sin(th)
        x = a * math.copysign(abs(c) ** (2 / p), c); y = b * math.copysign(abs(s) ** (2 / p), s)
        y *= 1 - taper * x / a; x += shear * y
        pts.append((x, y))
    return resample(pts, n)

def neta_drape(top, kx=6.5, ky=16.0, end=0.018, kend=22.0, twist=0.0):
    def d(x, y):
        ex = np.maximum(np.abs(x) - end, 0)
        return top - kx * x * x - ky * y * y - kend * ex * ex + twist * x * y + 0.00035 * np.sin(x * 140 + 0.6) * np.cos(y * 90)
    return d

def make_nigiri(name, pos, neta_mat, L, W, Th, seed, kx=6.5, ky=16.0, extra=None):
    r = nigiri_rice(seed)
    bv = bvh_of([r])
    ol = outline_slice(L / 2, W / 2)
    sl = slab(name + '_neta', ol, Th, neta_drape(RICE_TOP + Th / 2, kx, ky, kend=34.0, twist=0.5), neta_mat, nr=8, rice_bvh=bv,
              edge=9.0, pw=0.32, thick=lambda x, y: 0.5 + 0.5 * np.clip(1 - (x / (L / 2)) ** 2, 0, 1),
              uvf=lambda x, y: (0.5 + x / 0.068, 0.5 + y / 0.032))
    return finalize(name, [r, sl] + (extra or []), pos)

SALMON = mat('Salmon', 'f47a3c', 0.36, tex_salmon(0.068, 0.032), sss=0.5, sss_rad=(1.0, 0.45, 0.25), sss_scale=0.003, coat=0.12)
TUNA = mat('Tuna', 'a51c2c', 0.3, tex_tuna(0.068, 0.032), sss=0.35, sss_rad=(1.0, 0.3, 0.25), sss_scale=0.002, coat=0.3)
make_nigiri('nigiri_salmon', (-0.27, 0.16, 0), SALMON, 0.064, 0.028, 0.0045, 21, kx=9.0, ky=26.0)
make_nigiri('nigiri_tuna', (-0.09, 0.16, 0), TUNA, 0.062, 0.027, 0.005, 22, kx=7.5, ky=24.0)

# ---- tamago: a stiff layered omelette block with a nori belt
TAMAGO = mat('Tamago', 'f9c22e', 0.55, tex_tamago(), sss=0.12, sss_rad=(1.0, 0.8, 0.3), sss_scale=0.0015)
def uv_box(o, sx, sy, sz):
    """per-face UV islands: top/bottom faces -> v 0.5..1 by (x, y); long sides -> v 0..0.5 by (x, z); ends by (y, z)"""
    me = o.data; uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        nx, ny, nz = p.normal
        for li in p.loop_indices:
            c = me.vertices[me.loops[li].vertex_index].co
            if abs(nz) > 0.6: uvv = (0.5 + c.x / sx, 0.5 + 0.5 * (0.5 + c.y / sy))
            elif abs(ny) >= abs(nx): uvv = (0.5 + c.x / sx, 0.5 * (c.z / sz))
            else: uvv = (0.5 + c.y / sx, 0.5 * (c.z / sz))
            uv.data[li].uv = uvv
def make_tamago(pos):
    r = nigiri_rice(23)
    V, F = superell(0.0292, 0.0126, 0.0066, 0.28, 0.24, 40, 14)
    V[:, 2] += 0.0066
    tz = V[:, 2].copy()
    V[:, 2] += RICE_TOP - 0.0006 - 3.2 * V[:, 0] ** 2 + 0.0006 * np.sin(V[:, 0] * 90)          # bows a little over the rice
    tm = mk('tamago', V, F, TAMAGO)
    co = tm.data.vertices
    uv_box(tm, 0.062, 0.027, 0.0124)
    for i, v in enumerate(co): pass
    # nori belt: a strip across the middle, shrink-wrapped over the tamago and down the rice to the plate
    bv = bvh_of([r, tm])
    NU, NA = 4, 34
    rows = []
    for j in range(NU):
        x = -0.0052 + 0.0104 * j / (NU - 1)
        ctr = Vector((x, 0, 0.012)); D, dirs = [], []
        for k in range(NA):
            a = math.radians(-122 + 244 * k / (NA - 1))
            dr = Vector((0, math.sin(a), math.cos(a))); dirs.append(dr)
            loc, nrm, _, _ = bv.ray_cast(ctr + dr * 0.06, -dr)
            D.append((loc - ctr).length if loc is not None else 0.0)
        D = np.array(D); E = D.copy()
        for _ in range(8):   # a smooth envelope over the rice lumps: the sheet bridges them, never dips inside
            E = np.maximum(D, (np.r_[E[:1], E[:-1]] + 2 * E + np.r_[E[1:], E[-1:]]) / 4)
        pts = [ctr + dirs[k] * (E[k] + 0.0006) for k in range(NA)]
        for p in pts: p.z = max(p.z, 0.0003)
        rows.append(pts)
    V2, UV2 = [], []
    for j in range(NU):
        for k in range(NA): V2.append(rows[j][k]); UV2.append((j / (NU - 1) * 0.3, k / (NA - 1) * 1.2))
    F2 = [(j * NA + k, j * NA + k + 1, (j + 1) * NA + k + 1, (j + 1) * NA + k) for j in range(NU - 1) for k in range(NA - 1)]
    belt = mk('belt', V2, F2, NORI, UV2)
    fix = belt.modifiers.new('sol', 'SOLIDIFY'); fix.thickness = 0.0005; fix.offset = 1; apply_mod(belt, fix)
    fix_normals(belt)
    return finalize('nigiri_tamago', [r, tm, belt], pos)
make_tamago((0.09, 0.16, 0))

# ---- ebi: a butterflied prawn, striped, with the tail fanned up
EBI_XT, EBI_XH = 0.023, -0.026
def ebi_w(x):
    s = np.clip((EBI_XT - x) / (EBI_XT - EBI_XH), 0, 1); return 0.0056 + 0.0088 * s ** 0.8
def ebi_outline(n=48):
    pts = [(x, float(ebi_w(x))) for x in np.linspace(EBI_XT, EBI_XH, 30)]
    Rl = float(ebi_w(EBI_XH)) / 2
    pts += [(EBI_XH + Rl * 0.9 * math.cos(a), Rl + Rl * math.sin(a)) for a in np.linspace(math.pi / 2, 1.5 * math.pi, 14)[1:]]
    pts += [(EBI_XH + 0.0026, 0.0)]
    pts += [(EBI_XH + Rl * 0.9 * math.cos(a), -Rl + Rl * math.sin(a)) for a in np.linspace(math.pi / 2, 1.5 * math.pi, 14)[:-1]]
    pts += [(x, -float(ebi_w(x))) for x in np.linspace(EBI_XH, EBI_XT, 30)]
    we = float(ebi_w(EBI_XT))
    pts += [(EBI_XT + we * 0.7 * math.cos(a), we * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, 9)[1:-1]]
    return resample(pts, n)
EBI = mat('Ebi', 'f6643c', 0.35, tex_ebi(0.068, 0.032, EBI_XT, EBI_XH, ebi_w), sss=0.4, sss_rad=(1.0, 0.6, 0.4), sss_scale=0.002, coat=0.3)
EBI_TAIL = mat('EbiTail', 'e8401f', 0.3, tex_ebi_tail(), sss=0.3, sss_scale=0.0015, coat=0.4, trans=0.1)
def make_ebi(pos):
    r = nigiri_rice(24)
    bv = bvh_of([r])
    segL = (EBI_XT - EBI_XH) / 6.2
    def ridge(x, y):   # each shell segment swells a little
        ph = (x - EBI_XH) / segL + 0.35 * (np.abs(y) / ebi_w(np.clip(x, EBI_XH, EBI_XT))) ** 2
        return 0.86 + 0.14 * np.sin(ph * TAU - 1.2) ** 2
    Th = 0.0034
    body = slab('ebi', ebi_outline(), Th, neta_drape(RICE_TOP + Th / 2, 6.0, 22.0, end=0.017, kend=30.0, twist=-0.4), EBI, nr=7, edge=8.0, pw=0.35,
                rice_bvh=bv, thick=ridge, uvf=lambda x, y: (0.5 + x / 0.068, 0.5 + y / 0.032))
    zt = max(v.co.z for v in body.data.vertices if v.co.x > EBI_XT - 0.002)
    parts = [r, body]
    for yaw, ln, wd in ((-38, 0.0115, 0.0046), (-13, 0.0135, 0.005), (13, 0.0135, 0.005), (38, 0.0115, 0.0046)):
        ol = outline_slice(ln / 2, wd / 2, p=2.3, shear=0.0, taper=-0.25, n=18)
        lobe = slab('tail', ol, 0.0012, lambda x, y: 0.0012 * (x / (ln / 2)) ** 2, EBI_TAIL, nr=3,
                    uvf=lambda x, y, ln=ln: (0.5 + x / ln, 0.5 + y / ln))
        xf(lobe, T(EBI_XT + 0.001, 0, zt - 0.0012) @ rot('Z', yaw) @ rot('Y', -30) @ T(ln / 2 - 0.0012, 0, 0))
        parts.append(lobe)
    return finalize('nigiri_ebi', parts, pos)
make_ebi((0.27, 0.16, 0))


# ================================================================ maki
def make_maki(name, pos, filling, seed):
    h = 0.0232
    core = lathe('core', [(0.0058, 0.0006), (0.0118, 0.0006), (0.0118, h - 0.0012), (0.0058, h - 0.0012), (0.0058, 0.0006)], 32, None, vfun=lambda *a: 0)
    rc = rice('rice', core, 60, lambda p, n: n.z > 0.5, 800, RICE, seed=seed, gsize=0.85, sink=(0.0001, 0.0004), crisp=44, cgsize=0.8,
               csink=(-0.00075, -0.0004),
               ckeep=lambda p, n: n.z > 0.6)
    nori = nori_wrap('nori', 0.0129, 0.0129, h + 0.0004, NORI, seg=60, seed=seed)
    return finalize(name, [rc, nori] + filling(h), pos)

def cucumber(h):
    out = []
    for cx, cy, ang in ((-0.0024, -0.0015, 20), (0.0026, -0.0012, -35), (0.0001, 0.0028, 75)):
        V, F = superell(0.0026, 0.0026, h / 2 - 0.0012, 0.3, 0.45, 16, 10)
        V[:, 2] += h / 2 - 0.0002
        o = mk('cuke', V, F, CUKE); o.data.materials.append(CUKE_SKIN)
        sd = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
        for p in o.data.polygons:
            if p.center.xy.dot(sd.xy) > 0.0015: p.material_index = 1          # the skin on the outer side of each baton
        xf(o, T(cx, cy, 0) @ rot('Z', ang - 0))
        out.append(o)
    return out
def tuna_core(h):
    V, F = superell(0.0048, 0.0042, h / 2 - 0.001, 0.25, 0.4, 20, 10)
    V[:, 2] += h / 2 - 0.0003
    V[:, 0] += 0.0003 * np.sin(V[:, 2] * 300); V[:, 1] += 0.0003 * np.cos(V[:, 0] * 900)
    return [xf(mk('tuna', V, F, TUNA_CORE), rot('Z', 12))]
make_maki('maki_cucumber', (-0.27, 0.30, 0), cucumber, 31)
make_maki('maki_tuna', (-0.15, 0.30, 0), tuna_core, 32)


# ================================================================ gunkan ikura
def make_gunkan(pos):
    a, b = 0.0178, 0.0124
    V, F = superell(a - 0.0032, b - 0.0032, 0.0085, 0.6, 0.45, 28, 12)
    V[:, 2] += 0.0085; V[:, 2] = np.maximum(V[:, 2], 0.0006)
    rc = rice('rice', mk('core', V, F), 30, lambda p, n: n.z > 0.5, 380, RICE, seed=41)
    nori = nori_wrap('nori', a + 0.0004, b + 0.0004, 0.0245, NORI, seg=56, seed=42, flare=0.0008, rows=3)
    rng = np.random.default_rng(43); rb = 0.0026
    beads = []
    ztop = lambda x, y: 0.0335 - 0.009 * ((x / a) ** 2 + (y / b) ** 2)
    floor = 0.0172
    def rest_z(x, y):
        z = floor + rb
        for bx, by, bz, br in beads:
            d2 = (x - bx) ** 2 + (y - by) ** 2; s = (rb + br) * 0.96
            if d2 < s * s: z = max(z, bz + math.sqrt(s * s - d2))
        return z
    for _ in range(42):
        best = None
        for _ in range(90):
            x, y = rng.uniform(-a, a), rng.uniform(-b, b)
            if (x / (a - rb * 0.95)) ** 2 + (y / (b - rb * 0.95)) ** 2 > 1: continue
            z = rest_z(x, y)
            if z <= ztop(x, y) and (best is None or z < best[2]): best = (x, y, z)
        if best: beads.append((*best, rb * rng.uniform(0.93, 1.05)))
    objs = []
    BV, BF = superell(1, 1, 1, 1, 1, 9, 6)
    V2, F2 = [], []
    for x, y, z, br in beads:
        base = len(V2); sq = rng.uniform(0.9, 1.0)
        V2 += [(x + v[0] * br, y + v[1] * br, z + v[2] * br * sq) for v in BV]
        F2 += [tuple(base + i for i in f) for f in BF]
    roe = mk('roe', V2, F2, IKURA)
    print('ikura beads', len(beads))
    return finalize('gunkan_ikura', [rc, nori, roe], pos)
make_gunkan((-0.03, 0.30, 0))


# ================================================================ soy dish
SOYDISH = mat('SoyDish', 'f4efe4', 0.12, tex_soydish(), coat=0.5)
def make_soy(pos):
    prof = profile([(0, 0.0032), (0.022, 0.0032), (0.0235, 0.0008), (0.0248, 0.0), (0.0272, 0.0), (0.0284, 0.0012), (0.0336, 0.0094),
                    (0.0369, 0.0146), (0.0374, 0.0162), (0.0364, 0.0173), (0.0349, 0.0166), (0.0311, 0.0112), (0.0252, 0.0069),
                    (0.018, 0.0059), (0, 0.0056)], it=3, tol=0.0001)
    apex = max(range(len(prof)), key=lambda i: prof[i][1])
    vf = lambda i, r, z: (0.05 + 0.45 * z / 0.0175) if i <= apex else (0.5 + 0.45 * (z - 0.0055) / 0.012)
    dish = lathe('dish', prof, 44, SOYDISH, vfun=vf)
    zs = 0.0098
    inner = [p for p in prof[apex:]]
    rw = float(np.interp(zs, [p[1] for p in inner[::-1]], [p[0] for p in inner[::-1]]))
    soy = lathe('soy', [(rw + 0.0002, zs + 0.0004), (rw - 0.0012, zs + 0.00008), (rw - 0.004, zs), (0, zs)], 44, SOY, vfun=lambda *a: 0.5)
    return finalize('soy_dish', [dish, soy], pos)
make_soy((0.09, 0.30, 0))


# ================================================================ wasabi: a little piped swirl
def make_wasabi(pos):
    NA, NT = 56, 26
    V, F = [], []
    for j in range(NT + 1):
        t = j / NT
        Rr = 0.0118 * (1 - t ** 1.7) ** 0.75 * (1 + 0.12 * math.sin(math.pi * min(t / 0.35, 1)))   # a soft bulge low down
        z = 0.021 * t ** 0.9
        tw = 2.6 * t + 0.4 * t * t                                                   # ridges twist as they rise
        lean = 0.0018 * t ** 2
        for k in range(NA):
            th = TAU * k / NA
            rr = Rr * (1 + 0.3 * (1 - t) ** 0.5 * (math.cos(7 * (th + tw)) * 0.5 + 0.5) ** 2)
            V.append((rr * math.cos(th) + lean, rr * math.sin(th), z))
    V.append((0.0021, 0, 0.0218)); top = len(V) - 1
    V.append((0, 0, 0)); bot = len(V) - 1
    for j in range(NT):
        F += [(j * NA + k, j * NA + (k + 1) % NA, (j + 1) * NA + (k + 1) % NA, (j + 1) * NA + k) for k in range(NA)]
    F += [(NT * NA + k, NT * NA + (k + 1) % NA, top) for k in range(NA)]
    F += [(k, bot, (k + 1) % NA) for k in range(NA)]
    o = mk('wasabi', V, F)
    fix_normals(o)
    tx = bpy.data.textures.new('grit', 'CLOUDS'); tx.noise_scale = 0.0009
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; apply_mod(o, sub)
    d = o.modifiers.new('grit', 'DISPLACE'); d.texture = tx; d.strength = 0.0003; d.mid_level = 0.5; apply_mod(o, d)
    decimate(o, 1800); o.data.materials.clear(); o.data.materials.append(WASABI); smooth_all(o)
    return finalize('wasabi', [o], pos)
make_wasabi((0.20, 0.30, 0))


# ================================================================ gari: pickled ginger petals in a fan
GARI = mat('Gari', 'f4b5ae', 0.3, tex_gari(), sss=0.35, sss_rad=(1.0, 0.6, 0.6), sss_scale=0.002, coat=0.25)
def make_gari(pos):
    rng = np.random.default_rng(51)
    parts = []
    for i in range(6):
        a, b = rng.uniform(0.021, 0.025), rng.uniform(0.014, 0.017)
        pts = []
        for k in range(160):
            th = TAU * k / 160; rr = 1 + 0.06 * math.sin(3 * th + i) + 0.04 * math.sin(5 * th + 2 * i)
            pts.append((a * rr * math.cos(th), b * rr * math.sin(th)))
        ol = resample(pts, 28)
        ph = rng.random() * TAU
        def drape(x, y, a=a, b=b, ph=ph):
            r2 = (x / a) ** 2 + (y / b) ** 2; th = np.arctan2(y / b, x / a)
            return 0.005 * r2 + 0.0016 * np.sin(4 * th + ph) * r2 ** 1.5 + 0.0008 * np.sin(7 * th + 2 * ph) * r2 ** 2 - 0.0016 * (x / a)
        p = slab('gari', ol, 0.0008, drape, GARI, nr=4, edge=3.0, uvf=lambda x, y, a=a, b=b: (0.5 + 0.5 * x / a, 0.5 + 0.5 * y / b))
        yaw = -70 + 140 * i / 5 + rng.uniform(-5, 5)
        xf(p, rot('Z', yaw) @ T(0.017, 0, 0.0012 + 0.0011 * i) @ rot('Y', -10 - 6 * rng.random()))
        parts.append(p)
    return finalize('gari', parts, pos)
make_gari((0.30, 0.30, 0))


# ================================================================ chopsticks on a rest
STICK = mat('Chopsticks', 'c99a64', 0.35, tex_wood_stick(), coat=0.4)
def make_chopsticks(pos):
    Lc = 0.215
    def stick():
        NS, NL = 10, 12; V, UV = [], []
        for i in range(NL + 1):
            s = i / NL; x = Lc * s; hw = 0.0034 * (1 - s) + 0.0016 * s
            if i == NL: hw *= 0.7
            for k in range(NS + 1):
                th = TAU * k / NS; c, sn = math.cos(th), math.sin(th)
                V.append((x, hw * math.copysign(abs(c) ** 0.55, c), hw * math.copysign(abs(sn) ** 0.55, sn))); UV.append((s, k / NS))
        F = [(i * (NS + 1) + k, (i + 1) * (NS + 1) + k, (i + 1) * (NS + 1) + k + 1, i * (NS + 1) + k + 1) for i in range(NL) for k in range(NS)]
        V += [(-0.0003, 0, 0), (Lc + 0.0004, 0, 0)]; UV += [(0, 0.5), (1, 0.5)]; c0, c1 = len(V) - 2, len(V) - 1
        F += [(c0, k + 1, k) for k in range(NS)] + [(c1, NL * (NS + 1) + k, NL * (NS + 1) + k + 1) for k in range(NS)]
        o = mk('stick', V, F, STICK, UV); fix_normals(o); return o
    # rest: a little pillow with a saddle dip
    V, F = superell(0.019, 0.0062, 0.0042, 0.55, 0.5, 28, 12)
    V[:, 2] += 0.0042
    dip = np.exp(-(V[:, 0] / 0.007) ** 2) * np.clip(V[:, 2] - 0.004, 0, None) / 0.0042
    V[:, 2] -= 0.0026 * dip
    rest = mk('rest', V, F, REST)
    xf(rest, T(0.165, 0, 0) @ rot('Z', 90))
    zr = 0.0084 - 0.0026 + 0.0001
    parts = [rest]
    for side, yaw in ((-1, 2.5), (1, -1.5)):
        st = stick()
        tilt = math.degrees(math.asin((zr - 0.0016) / 0.165))
        xf(st, T(0, side * 0.0062, 0.0034) @ rot('Z', yaw) @ rot('Y', -tilt))
        parts.append(st)
    return finalize('chopsticks', parts, pos)
make_chopsticks((0.0, 0.46, 0))


# ================================================================ teacup (yunomi)
CUP = mat('Teacup', 'e7dcc3', 0.22, tex_cup(), coat=0.35)
def make_cup(pos):
    prof = profile([(0, 0.0045), (0.021, 0.0045), (0.0225, 0.0015), (0.0240, 0.0), (0.0275, 0.0), (0.0290, 0.0020), (0.0298, 0.0060),
                    (0.0312, 0.020), (0.0328, 0.060), (0.0337, 0.078), (0.0339, 0.0835), (0.0329, 0.0853), (0.0313, 0.0849),
                    (0.0303, 0.082), (0.0294, 0.060), (0.0281, 0.020), (0.0262, 0.0115), (0.020, 0.0092), (0, 0.0090)], it=3, tol=0.00012)
    apex = max(range(len(prof)), key=lambda i: prof[i][1])
    def vf(i, r, z):
        if i <= apex: return 0.02 + 0.91 * z / 0.0853 if r > 0.0232 else 0.01
        return 0.94 + 0.055 * z / 0.0853
    cup = lathe('cup', prof, 48, CUP, vfun=vf)
    zt = 0.072
    inner = prof[apex:]
    rw = float(np.interp(zt, [p[1] for p in inner[::-1]], [p[0] for p in inner[::-1]]))
    tea = lathe('tea', [(rw + 0.0002, zt + 0.0005), (rw - 0.0015, zt + 0.0001), (0, zt)], 48, TEA, vfun=lambda *a: 0.5)
    return finalize('teacup', [cup, tea], pos)
make_cup((0.20, 0.46, 0))


# ================================================================ export
total = 0
print('\n%-16s %7s' % ('object', 'tris'))
for nm, o in ASSETS.items():
    total += tris(o); print('%-16s %7d' % (nm, tris(o)))
print('%-16s %7d\n' % ('TOTAL', total), flush=True)
for o in scn.objects: o.select_set(o.name in ASSETS)
glb = os.path.join(OUT, 'sushi_set.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_image_format='AUTO')
print('wrote', glb)
if NOPREV: sys.exit(0)


# ================================================================ previews (Cycles, CPU): warm soft daylight on a light wood counter
for o in ASSETS.values(): o.hide_render = True
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('dfe4ea'), 1); bg.inputs['Strength'].default_value = 0.9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 3.6; sun.data.color = srgb('ffe2bd'); sun.data.angle = math.radians(16)
sun.rotation_euler = (math.radians(42), 0, math.radians(-140))
fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'AREA')); scn.collection.objects.link(fill)
fill.data.energy = 0; fill.data.size = 1.2; fill.data.color = srgb('fff4e6'); fill.location = (0.6, -0.9, 0.9)
fill.rotation_euler = (Vector((0, 0, 0)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

def wood_mat():
    m = bpy.data.materials.new('Counter'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 4
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'; wv.wave_profile = 'SIN'
    wv.inputs['Scale'].default_value = 7.0; wv.inputs['Distortion'].default_value = 4.0; wv.inputs['Detail'].default_value = 4
    wv.inputs['Detail Scale'].default_value = 1.5
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.18, 1.0, 1.0)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], wv.inputs['Vector']); nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*srgb('e8cfa5'), 1); ramp.color_ramp.elements[1].color = (*srgb('dbbb8b'), 1)
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 1.0
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'FLOAT'; mx.inputs['Factor'].default_value = 0.35
    nt.links.new(wv.outputs['Fac'], mx.inputs['A']); nt.links.new(nz.outputs['Fac'], mx.inputs['B'])
    nt.links.new(mx.outputs['Result'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.6
    return m
bpy.ops.mesh.primitive_plane_add(size=4); counter = bpy.context.object; counter.name = 'Counter'; counter.data.materials.append(wood_mat())
# a stretch of conveyor behind the counter edge, for context
STEEL = mat('Steel', 'c9ccd0', 0.25); STEEL.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 1.0
BELT = mat('Belt', 'e9e3d6', 0.6)
INST = []
def place(name, loc, rz=0.0):
    src = ASSETS[name]; o = bpy.data.objects.new(name + '_i', src.data); scn.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rz)); INST.append(o); return o
def box(name, loc, size, m):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name; o.scale = [s / 2 for s in size]
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = 0.004; bv.segments = 3; o.data.materials.append(m); INST.append(o); return o

scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = 48
scn.cycles.use_denoising = True
try: scn.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
scn.view_settings.view_transform = 'AgX'
try: scn.view_settings.look = 'AgX - Punchy'
except Exception: pass
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
def shoot(name, pos, look, lens=50, res=(900, 600)):
    if SHOTS and name.split('_')[0] not in SHOTS and name not in SHOTS: return
    cam.data.lens = lens; cam.location = pos
    cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.filepath = os.path.join(OUT, 'prev_' + name + '.png'); bpy.ops.render.render(write_still=True)
    print('rendered', name, flush=True)
def cam_at(target, dist, el, az):
    el, az = math.radians(el), math.radians(az)
    return (target[0] + dist * math.cos(el) * math.sin(az), target[1] - dist * math.cos(el) * math.cos(az), target[2] + dist * math.sin(el))
def clear():
    for o in INST: bpy.data.objects.remove(o)
    INST.clear()

# (a) hero vignette: plates coming along the belt, the diner's things on the counter in front
FZ = PLATE_FLOOR
def lane():
    box('LaneBase', (0, 0.17, 0.018), (1.6, 0.21, 0.036), STEEL)
    box('LaneBelt', (0, 0.17, 0.0372), (1.6, 0.18, 0.003), BELT)
    box('LaneRail', (0, 0.06, 0.03), (1.6, 0.012, 0.06), STEEL)
LZ = 0.0387
def plate_with(col, x, y, z, rz, items):
    place('plate_' + col, (x, y, z), rz)
    for nm, dx, dy, r in items:
        a = math.radians(rz); px = x + dx * math.cos(a) - dy * math.sin(a); py = y + dx * math.sin(a) + dy * math.cos(a)
        place(nm, (px, py, z + FZ), rz + r)
lane()
plate_with('red', -0.25, 0.17, LZ, 8, [('nigiri_salmon', 0, 0.019, -4), ('nigiri_salmon', 0.003, -0.019, 6)])
plate_with('blue', -0.085, 0.17, LZ, -14, [('nigiri_tuna', 0, 0.019, 3), ('nigiri_tuna', -0.002, -0.019, -5)])
plate_with('yellow', 0.08, 0.17, LZ, 20, [('nigiri_tamago', 0, 0.02, 0), ('nigiri_ebi', 0, -0.02, 180)])
plate_with('green', 0.245, 0.17, LZ, -6, [('maki_cucumber', -0.017, 0.018, 0), ('maki_tuna', 0.017, -0.016, 40)])
plate_with('red', 0.41, 0.17, LZ, 4, [('gunkan_ikura', -0.022, 0.0, 90), ('nigiri_ebi', 0.022, 0.0, 95)])
plate_with('yellow', -0.415, 0.17, LZ, 4, [('gunkan_ikura', -0.022, 0.0, 80), ('maki_cucumber', 0.022, 0.0, 95)])
place('soy_dish', (-0.10, 0.0, 0))
place('wasabi', (-0.035, -0.035, 0)); place('gari', (0.035, -0.01, 0), 20)
place('chopsticks', (-0.02, -0.085, 0), 4)
place('teacup', (0.17, 0.0, 0))
shoot('hero', cam_at((0.0, 0.07, 0.0), 0.78, 50, 14), (0.0, 0.065, 0.01), 40)
clear()

# (b) close-ups: each nigiri on its plate
for nm, col in (('salmon', 'red'), ('tuna', 'blue'), ('tamago', 'yellow'), ('ebi', 'green')):
    place('plate_' + col, (0, 0, 0), 0)
    place('nigiri_' + nm, (0, 0, FZ), 15)
    shoot('close_' + nm, cam_at((0, 0, 0.012), 0.24, 42, 28), (0, 0, 0.012), 60, (800, 600))
    clear()
for nm in ('maki_cucumber', 'maki_tuna', 'gunkan_ikura'):
    place(nm, (0, 0, 0), 0)
    shoot('close_' + nm, cam_at((0, 0, 0.012), 0.18, 48, 28), (0, 0, 0.012), 60, (640, 480))
    clear()

# (c) the whole set as exported, from the game angle
for o in ASSETS.values(): o.hide_render = False
shoot('lineup', cam_at((0.0, 0.2, 0.0), 1.15, 50, 0), (0.0, 0.22, 0.0), 45)
# (d) base colours only (roughly how a flat toon shader sees it): every material becomes an emission of its base colour
for m in bpy.data.materials:
    if not m.use_nodes or 'Principled BSDF' not in m.node_tree.nodes: continue
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; out = nt.nodes['Material Output']
    em = nt.nodes.new('ShaderNodeEmission')
    if b.inputs['Base Color'].is_linked: nt.links.new(b.inputs['Base Color'].links[0].from_socket, em.inputs['Color'])
    else: em.inputs['Color'].default_value = b.inputs['Base Color'].default_value
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
bg.inputs['Color'].default_value = (*srgb('e8dcc8'), 1); bg.inputs['Strength'].default_value = 1.0
sun.data.energy = 0; counter.hide_render = True
scn.cycles.samples = 8; scn.view_settings.view_transform = 'Standard'
shoot('flat', cam_at((0.0, 0.2, 0.0), 1.15, 50, 0), (0.0, 0.22, 0.0), 45)
