# "HELIPAD" stage, fully modelled: two sumos fight on an elevated rooftop helipad on top of a skyscraper at dusk.
# Built entirely by script (Blender 4.2, run headless).
#   python tools/blender/stage_heli.py [out_dir] [chars_dir] [shot=game shot=low] [samples=48] [pct=100] [noren] [nochars]
# Writes <out_dir>/heli.glb (the stage only: Z up, metres, origin at the pad centre, top of the pad at Z=0, front
# facing -Y) and renders <out_dir>/ex_game.png (game camera) and <out_dir>/ex_low.png (low three-quarter) with the game's
# characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in masks.
# Layout (top view, camera on -Y): a round concrete touchdown pad (r 5.3) on a steel frame 3 m above the roof of a
# tower, a safety net round its rim, an access stair down to the roof on the right; a light helicopter parked on the
# roof back-left, the windsock and the condensers back-right, the stair hut front-left, four floodlight masts; the
# city far below. CC0 Poly Haven assets (rooftop_night HDRI, concrete/gravel/metal textures) live in <scratchpad>/heli_ph.
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in ('noren', 'nochars') and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'heli')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
PH = os.path.join(SP, 'heli_ph')
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SHOTS = set(a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')) or {'game', 'low'}
SAMPLES = int(OPT.get('samples', 48)); PCT = int(OPT.get('pct', 100))
NOREN = 'noren' in sys.argv; NOCHARS = 'nochars' in sys.argv

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


R = ring_r()          # fighting circle = outer edge of the yellow touchdown ring
RD = R + 0.7          # pad radius
ROOF = -3.0           # roof slab top
NET_IN, NET_OUT = RD + 0.06, RD + 1.55
STAIR_A = math.radians(-8)     # the access stair leaves the pad to the right


# ================================================================ helpers
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def srgb(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


STAGE = []
def obj(name, me, mats=(), stage=True, loc=None, rot=None, scale=None):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    for m in mats: me.materials.append(m)
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = rot
    if scale is not None: o.scale = scale
    if stage: STAGE.append(o)
    return o
def bm_obj(name, bm, mats=(), smooth=35, **kw):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    return obj(name, me, mats, **kw)
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0


def planar_uv(me, S, cx=0.0, cy=0.0):
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for l in me.loops:
        co = me.vertices[l.vertex_index].co; uv.data[l.index].uv = ((co.x - cx) / (2 * S) + 0.5, (co.y - cy) / (2 * S) + 0.5)
def box_uv(o, tile=6.0, world=True, off=(0.0, 0.0)):
    me = o.data; uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    W = o.matrix_world if world else Matrix.Identity(4)
    R3 = W.to_3x3()
    for p in me.polygons:
        n = R3 @ p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = W @ me.vertices[me.loops[li].vertex_index].co
            u, v = (co.x, co.y) if ax == 2 else (co.y, co.z) if ax == 0 else (co.x, co.z)
            uv.data[li].uv = (u / tile + off[0], v / tile + off[1])


def lathe(name, prof, mats, segs=128, loc=(0, 0, 0), mi=None, uvS=None, smooth=40, stage=True, a0=0.0, a1=None):
    """Profile [(r, z)] top-inside -> outside -> down -> bottom-inside (normals face out); r == 0 is a pole."""
    full = a1 is None
    bm = bmesh.new(); rings = []
    n = segs if full else segs + 1
    for (r, z) in prof:
        if r < 1e-6: rings.append([bm.verts.new((0, 0, z))]); continue
        ring = []
        for i in range(n):
            a = (TAU * i / segs) if full else (a0 + (a1 - a0) * i / segs)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
        if len(A) == 1 and len(B) == 1: continue
        for i in range(segs):
            j = (i + 1) % n
            if len(A) == 1: f = bm.faces.new((A[0], B[i], B[j]))
            elif len(B) == 1: f = bm.faces.new((A[i], B[0], A[j]))
            else: f = bm.faces.new((A[i], B[i], B[j], A[j]))
            if mi: f.material_index = mi[k]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    planar_uv(me, uvS or max(r for r, _ in prof))
    return obj(name, me, mats, stage=stage, loc=loc)


def newfaces(ret):
    return {f for v in ret['verts'] for f in v.link_faces}
def look_mat(p0, p1, up=Vector((0, 0, 1))):
    d = (Vector(p1) - Vector(p0)); L = d.length; d.normalize()
    q = d.to_track_quat('Z', 'Y')
    return q.to_matrix().to_4x4(), L
def add_tube(bm, p0, p1, r, segs=10, mi=0, r1=None):
    M, L = look_mat(p0, p1); M.translation = (Vector(p0) + Vector(p1)) / 2
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r1 is None else r1, depth=L, matrix=M)
    for f in newfaces(ret): f.material_index = mi
    return ret
def add_box(bm, c, size, mi=0, rot=None, M=None):
    Mx = Matrix.Translation(Vector(c)) @ (rot.to_matrix().to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1))
    if M is not None: Mx = M @ Mx
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=Mx)
    for f in newfaces(ret): f.material_index = mi
    return ret
def add_sphere(bm, c, rad, seg=16, ring=8, mi=0, scale=(1, 1, 1)):
    M = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*scale, 1))
    ret = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=rad, matrix=M)
    for f in newfaces(ret): f.material_index = mi
    return ret
def add_cyl(bm, c, r, h, segs=24, mi=0, axis='Z', r1=None):
    c = Vector(c); d = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}[axis] * h / 2
    return add_tube(bm, c - d, c + d, r, segs, mi, r1)


def frames(pts, up=Vector((0, 0, 1))):
    P = [Vector(p) for p in pts]; n = len(P); T = []
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]); T.append(t.normalized())
    out = []
    prevN = None
    for i in range(n):
        if prevN is None:
            u = up if abs(T[i].dot(up)) < 0.95 else Vector((1, 0, 0))
            Nn = (u - T[i] * u.dot(T[i])).normalized()
        else:
            Nn = (prevN - T[i] * prevN.dot(T[i])).normalized()
        B = T[i].cross(Nn); out.append((P[i], T[i], Nn, B)); prevN = Nn
    return out
def sweep(bm, pts, r, n=8, mi=0, closed=False, caps=True, shape=None):
    """Tube along a polyline. r: scalar or per-point list. shape(k, i) -> (dx, dy) multiplies the circle (optional)."""
    F = frames(pts); rings = []
    for k, (p, t, nn, b) in enumerate(F):
        rr = r[k] if isinstance(r, (list, tuple, np.ndarray)) else r
        ring = []
        for i in range(n):
            a = TAU * i / n; ca, sa = math.cos(a), math.sin(a)
            if shape: ca, sa = shape(k, i, ca, sa)
            ring.append(bm.verts.new(p + (nn * ca + b * sa) * rr))
        rings.append(ring)
    m = len(rings)
    faces = []
    for k in range(m if closed else m - 1):
        A, B = rings[k], rings[(k + 1) % m]
        for i in range(n):
            j = (i + 1) % n; f = bm.faces.new((A[i], A[j], B[j], B[i])); f.material_index = mi; faces.append(f)
    if caps and not closed:
        f = bm.faces.new(rings[0][::-1]); f.material_index = mi
        f = bm.faces.new(rings[-1]); f.material_index = mi
    return rings
def extrude_poly(bm, poly, t, plane='XZ', off=0.0, mi=0):
    """Closed 2D polygon extruded by thickness t across the third axis (centred on off)."""
    def P(a, b, c):
        return (a, c, b) if plane == 'XZ' else (a, b, c) if plane == 'XY' else (c, a, b)
    A = [bm.verts.new(P(x, y, off - t / 2)) for x, y in poly]; B = [bm.verts.new(P(x, y, off + t / 2)) for x, y in poly]
    fs = [bm.faces.new(A), bm.faces.new(B[::-1])]
    for i in range(len(A)):
        j = (i + 1) % len(A); fs.append(bm.faces.new((A[i], A[j], B[j], B[i])))
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    for f in fs: f.material_index = mi
    return fs


def text_tris(body, font, size, align='CENTER'):
    """Triangles (T, 3, 2) of a text outline in its local plane, centred."""
    cu = bpy.data.curves.new('tt', 'FONT'); cu.body = body; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
    cu.font = font; cu.resolution_u = 4
    tmp = bpy.data.objects.new('tt', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:])
    T = np.array([[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces], np.float32); bm.free()
    return T
def raster(T, N, x0, x1, y0, y1, ss=3):
    """Coverage mask (N x N rows = y) of 2D triangles over [x0,x1]x[y0,y1], supersampled."""
    M = N * ss; m = np.zeros((M, M), np.float32)
    px = (x1 - x0) / M; py = (y1 - y0) / M
    for tri in T:
        (ax, ay), (bx, by), (cx, cy) = tri
        i0 = max(int((min(ax, bx, cx) - x0) / px) - 1, 0); i1 = min(int((max(ax, bx, cx) - x0) / px) + 2, M)
        j0 = max(int((min(ay, by, cy) - y0) / py) - 1, 0); j1 = min(int((max(ay, by, cy) - y0) / py) + 2, M)
        if i1 <= i0 or j1 <= j0: continue
        X, Y = np.meshgrid(x0 + (np.arange(i0, i1) + 0.5) * px, y0 + (np.arange(j0, j1) + 0.5) * py)
        d1 = (X - bx) * (ay - by) - (ax - bx) * (Y - by)
        d2 = (X - cx) * (by - cy) - (bx - cx) * (Y - cy)
        d3 = (X - ax) * (cy - ay) - (cx - ax) * (Y - ay)
        neg = (d1 < 0) | (d2 < 0) | (d3 < 0); pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        m[j0:j1, i0:i1] = np.maximum(m[j0:j1, i0:i1], (~(neg & pos)).astype(np.float32))
    return m.reshape(N, ss, N, ss).mean((1, 3))


# ---------------------------------------------------------------- images & materials
def image(name, arr, data=False, alpha=None):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    h, w = arr.shape[:2]; rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    if alpha is not None: rgba[..., 3] = np.clip(alpha, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    if data: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.file_format = 'PNG'; im.pack(); return im
def load_np(path, data=False):
    im = bpy.data.images.load(path)
    if data: im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a)
    return im, a.reshape(h, w, 4)[..., :3]
def normal_from_h(h, strength):
    gy, gx = np.gradient(h); n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True); return n * 0.5 + 0.5
def noise(N, px, seed, M=None):
    """Periodic smooth noise (N x N, or N x M), feature size ~px pixels, std 1."""
    M = M or N
    rng = np.random.default_rng(seed); a = rng.standard_normal((N, M))
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.rfftfreq(M)[None, :]
    k = np.exp(-(fx ** 2 + fy ** 2) * (px ** 2) * 2.0)
    b = np.fft.irfft2(np.fft.rfft2(a) * k, s=(N, M)); return ((b - b.mean()) / (b.std() + 1e-9)).astype(np.float32)
def fbm(N, px, seed, octaves=4, M=None):
    s = np.zeros((N, M or N), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        s += amp * noise(N, px / 2 ** o, seed + o, M); tot += amp; amp *= 0.5
    return s / tot
def blur(a, px):
    N, M = a.shape[:2]
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.rfftfreq(M)[None, :]
    k = np.exp(-(fx ** 2 + fy ** 2) * (px ** 2) * 2.0 * math.pi ** 2 / 2)
    if a.ndim == 2: return np.fft.irfft2(np.fft.rfft2(a) * k, s=(N, M)).astype(np.float32)
    return np.dstack([np.fft.irfft2(np.fft.rfft2(a[..., c]) * k, s=(N, M)) for c in range(a.shape[2])]).astype(np.float32)


BSDF = {}
def mat(name, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tcol=None, trough=None, tnrm=None, nstr=1.0, emit=None, estr=0.0,
        coat=0.0, coat_r=0.05, spec=0.5, temit=None, talpha=False, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']; BSDF[name] = bs
    bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal; bs.inputs['Specular IOR Level'].default_value = spec
    if coat: bs.inputs['Coat Weight'].default_value = coat; bs.inputs['Coat Roughness'].default_value = coat_r
    if sheen: bs.inputs['Sheen Weight'].default_value = sheen
    def tex(im):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = im; return n
    if tcol:
        t = tex(tcol); nt.links.new(t.outputs['Color'], bs.inputs['Base Color'])
        if talpha:
            nt.links.new(t.outputs['Alpha'], bs.inputs['Alpha']); m.blend_method = 'HASHED'
    if trough:
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tex(trough).outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bs.inputs['Roughness'])
    if tnrm:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(tex(tnrm).outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    if emit: bs.inputs['Emission Color'].default_value = (*emit, 1); bs.inputs['Emission Strength'].default_value = estr
    if temit:
        nt.links.new(tex(temit).outputs['Color'], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = estr
    return m


N = 1024
FONT_B = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
FONT_C = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf') \
    if os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf') else FONT_B


# ================================================================ textures
def ph(name, kind, data=False):
    p = os.path.join(PH, '%s_%s.jpg' % (name, kind))
    return load_np(p, data)


def tile_to(a, reps, n=N):
    """Downsample a (n x n x c) texture so `reps` copies fill an n x n image."""
    k = a.shape[0] // (n // reps) if a.shape[0] >= n // reps else 1
    if k > 1: a = a.reshape(a.shape[0] // k, k, a.shape[1] // k, k, -1).mean((1, 3))
    return np.tile(a, (reps, reps, 1))[:n, :n]


def tex_pad():
    """The touchdown pad: worn concrete, the yellow touchdown ring (outer edge = fighting circle), the white H, the
    white perimeter line, weight marking, paint wear, skid and tyre marks, oil stains, saw-cut joints."""
    S = RD; xs = (np.arange(N) + 0.5) / N * 2 * S - S
    X, Y = np.meshgrid(xs, xs); r = np.hypot(X, Y); pw = 2 * S / N
    _, cd = ph('concrete_floor_worn_001', 'Diffuse'); _, cr = ph('concrete_floor_worn_001', 'Rough', True)
    _, cn = ph('concrete_floor_worn_001', 'nor_gl', True)
    reps = 4
    A = tile_to(cd, reps); A2 = np.rot90(tile_to(cd[::-1], reps), 1)
    mix = sstep(-0.4, 0.4, noise(N, 60, 3))[..., None]
    conc = A * (1 - mix) + A2 * mix
    rough = tile_to(cr, reps)[..., 1] * (1 - mix[..., 0]) + np.rot90(tile_to(cr[::-1], reps), 1)[..., 1] * mix[..., 0]
    nrm = tile_to(cn, reps) * (1 - mix) + np.rot90(tile_to(cn[::-1], reps), 1) * mix
    # flip the rotated normal's xy accordingly (rot90 swaps the axes)
    lum = conc.mean(2); conc = conc / (lum.mean() + 1e-6)[..., None] if False else conc
    # large-scale weathering: damp patches, grime towards the rim, sun-bleached middle
    big = fbm(N, 120, 11); mid = fbm(N, 25, 12)
    tone = 0.40 * (1 + 0.10 * big + 0.05 * mid) * (1 - 0.12 * sstep(3.5, 5.3, r))
    conc = conc / conc.mean((0, 1)) * tone[..., None] * np.array([1.0, 0.99, 0.965])
    # saw-cut joints (2.65 m grid) with dark sealant
    joint = np.zeros_like(r)
    for v in (-2.65, 0.0, 2.65):
        joint = np.maximum(joint, 1 - sstep(0.004, 0.012, np.abs(X - v)))
        joint = np.maximum(joint, 1 - sstep(0.004, 0.012, np.abs(Y - v)))
    joint *= (r < RD - 0.05)
    # ---------------------------------------------------------------- paint masks
    aa = pw * 0.7
    ring = sstep(R - 0.30 - aa, R - 0.30 + aa, r) * (1 - sstep(R - aa, R + aa, r))
    edge = sstep(4.86 - aa, 4.86 + aa, r) * (1 - sstep(5.02 - aa, 5.02 + aa, r))
    hw, hh, bw = 1.25, 1.85, 0.56
    def band(v, a, b): return sstep(a - aa, a + aa, v) * (1 - sstep(b - aa, b + aa, v))
    Hm = np.maximum(np.maximum(band(X, -hw, -hw + bw), band(X, hw - bw, hw)) * band(Y, -hh, hh), band(X, -hw, hw) * band(Y, -bw / 2, bw / 2))
    # weight marking in front of the H (reads from the camera): "6.4t" in a white box outline
    T = text_tris('6.4', FONT_C, 0.62); T[..., 0] -= 0.12; T[..., 1] += -3.18
    T2 = text_tris('t', FONT_C, 0.36); T2[..., 0] += 0.44; T2[..., 1] += -3.26
    txt = raster(np.concatenate([T, T2]), N, -S, S, -S, S)
    box = (band(X, -0.78, 0.78) * band(Y, -3.62, -2.74)) * (1 - band(X, -0.70, 0.70) * band(Y, -3.54, -2.82))
    white = np.clip(Hm + edge + txt + box, 0, 1)
    yellow = ring
    # ---------------------------------------------------------------- wear
    fine = fbm(N, 3, 21, 3); coarse = fbm(N, 30, 22)
    traffic = np.exp(-(r / 3.2) ** 2)
    clum = conc.mean(2); pits = sstep(0.0, -0.10, (clum - blur(clum, 4)) / (clum.mean() + 1e-6))
    chips = sstep(0.95, 1.35, fine * 0.55 + coarse * 0.55 + 0.75 * traffic + 0.9 * pits)
    thin = 0.80 + 0.12 * sstep(-1, 1, coarse) - 0.18 * traffic * sstep(-0.5, 1.2, fine)
    a_y = yellow * (1 - chips) * thin; a_w = white * (1 - chips) * thin
    a_y *= (1 - joint); a_w *= (1 - joint)
    # ---------------------------------------------------------------- skid / tyre marks, oil
    skid = np.zeros_like(r)
    def stroke(p0, ang, L, w, curv, inten, dash=False):
        nonlocal skid
        n = int(L / (pw * 1.5)) + 2
        for k in range(n):
            t = k / (n - 1); a = ang + curv * (t - 0.5)
            px = p0[0] + math.cos(ang) * L * (t - 0.5) - math.sin(ang) * curv * L * 0.5 * (t - 0.5) ** 2
            py = p0[1] + math.sin(ang) * L * (t - 0.5) + math.cos(ang) * curv * L * 0.5 * (t - 0.5) ** 2
            fade = math.sin(math.pi * t) ** 0.4 * inten
            if dash and (k // 9) % 3 == 0: fade *= 0.4
            i = int((px + S) / pw); j = int((py + S) / pw); rad = int(w / pw) + 2
            if not (rad <= i < N - rad and rad <= j < N - rad): continue
            sub = np.hypot(X[j - rad:j + rad, i - rad:i + rad] - px, Y[j - rad:j + rad, i - rad:i + rad] - py)
            skid[j - rad:j + rad, i - rad:i + rad] = np.maximum(skid[j - rad:j + rad, i - rad:i + rad], (1 - sstep(w * 0.4, w, sub)) * fade)
    rng = np.random.default_rng(5)
    for _ in range(9):      # paired skid-shoe marks, 2.3 m apart, from landings
        c = rng.uniform(-1.6, 1.6, 2); ang = rng.uniform(0, math.pi); L = rng.uniform(0.8, 2.2)
        nx, ny = -math.sin(ang), math.cos(ang)
        for sd in (-1, 1):
            stroke((c[0] + nx * 1.15 * sd, c[1] + ny * 1.15 * sd), ang, L, rng.uniform(0.05, 0.08), rng.uniform(-0.15, 0.15), rng.uniform(0.35, 0.7))
    for _ in range(5):      # dolly tyre arcs
        c = rng.uniform(-2.8, 2.8, 2); stroke(c, rng.uniform(0, TAU), rng.uniform(2.5, 4.5), 0.09, rng.uniform(-1.5, 1.5), rng.uniform(0.3, 0.55), True)
    skid *= (0.75 + 0.25 * sstep(-1, 1, fine))
    oil = np.zeros_like(r)
    for _ in range(4):
        c = rng.uniform(-2.2, 2.2, 2); rad = rng.uniform(0.18, 0.5)
        d = np.hypot(X - c[0], Y - c[1]) * (1 + 0.35 * noise(N, 14, int(rng.integers(1000))))
        oil = np.maximum(oil, (1 - sstep(rad * 0.3, rad, d)) * rng.uniform(0.35, 0.7))
    # ---------------------------------------------------------------- compose (sRGB)
    YEL = srgb('e3b322'); WHT = srgb('d9d9d2')
    detail = (clum / (blur(clum, 6) + 1e-4))[..., None]
    col = conc.copy()
    col = col * (1 - a_y[..., None]) + YEL * np.clip(detail, 0.7, 1.2) * a_y[..., None]
    col = col * (1 - a_w[..., None]) + WHT * np.clip(detail, 0.75, 1.15) * a_w[..., None]
    col *= (1 - 0.55 * skid)[..., None]; col *= (1 - 0.45 * oil)[..., None] * np.array([1, 0.98, 0.96])
    col *= (1 - 0.6 * joint)[..., None]
    rgh = np.clip(rough * 0.9 + 0.05, 0.5, 1.0)
    paint = np.clip(a_y + a_w, 0, 1)
    rgh = rgh * (1 - paint) + (0.48 + 0.1 * fine) * paint
    rgh = rgh * (1 - 0.3 * skid) - 0.4 * oil
    h = -joint * 0.6 + paint * 0.25
    nrm2 = normal_from_h(blur(h, 0.7), 2.0)
    nrm = (nrm - 0.5) * (1 - 0.6 * paint[..., None]) + (nrm2 - 0.5)
    nrm[..., 2] = np.abs(nrm[..., 2]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-6
    return np.clip(col, 0, 1), np.clip(rgh, 0.05, 1), nrm * 0.5 + 0.5


def tex_net():
    """Rope netting with knots, tiled every 0.5 m (alpha cut-out)."""
    n = 256; xs = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(xs, xs); cells = 5      # 10 cm mesh
    u = (X + Y) * cells; v = (X - Y) * cells    # diamond mesh
    du = np.abs(u - np.round(u)); dv = np.abs(v - np.round(v))
    rope = np.maximum(1 - sstep(0.035, 0.07, du), 1 - sstep(0.035, 0.07, dv))
    knot = (1 - sstep(0.06, 0.11, np.hypot(du, dv)))
    a = np.clip(rope + knot, 0, 1)
    col = np.dstack([np.full_like(a, 0.10), np.full_like(a, 0.10), np.full_like(a, 0.09)]) * (0.8 + 0.4 * a[..., None])
    return col, a


def tex_windows(seed, kind='glass'):
    """Facade: 8 floors x 8 bays per tile (tile = 24 m x 28.8 m). Returns base colour (sRGB) and emission (sRGB)."""
    n = 512; c = n // 8; rng = np.random.default_rng(seed)
    base = np.zeros((n, n, 3), np.float32); em = np.zeros((n, n, 3), np.float32)
    yy, xx = np.mgrid[0:c, 0:c]
    for fy in range(8):
        floor_on = rng.uniform(0.15, 0.7)
        for bx in range(8):
            if kind == 'glass':
                win = (xx >= 3) & (xx < c - 3) & (yy >= 9) & (yy < c - 4)
                bcol = srgb('1b222c'); wcol = srgb('0d141e') * rng.uniform(0.8, 1.3)
            else:
                win = (xx >= 12) & (xx < c - 12) & (yy >= 16) & (yy < c - 12)
                bcol = srgb('4a4844') * rng.uniform(0.85, 1.1); wcol = srgb('10141a')
            cell = np.where(win[..., None], wcol, bcol)
            e = np.zeros((c, c, 3), np.float32)
            if rng.random() < floor_on:
                tint = srgb(rng.choice(['ffc98a', 'ffd9a0', 'fff1d8', 'd8e8ff', 'ffb070']))
                I = rng.uniform(0.35, 1.0)
                grad = 0.75 + 0.25 * (yy / c)          # ceiling light falls off downwards
                blind = rng.random() < 0.3
                if blind: grad = grad * (0.4 + 0.6 * ((yy // 3) % 2))
                e = np.where(win[..., None], tint * I * grad[..., None], 0)
            base[fy * c:(fy + 1) * c, bx * c:(bx + 1) * c] = cell
            em[fy * c:(fy + 1) * c, bx * c:(bx + 1) * c] = e
    return base, em


def tex_streets():
    """Street grid far below: dark blocks, sodium-lit roads, car lights. Covers 1200 m, roads every 30 m."""
    n = 1024; S = 600.0; xs = (np.arange(n) + 0.5) / n * 2 * S - S
    X, Y = np.meshgrid(xs, xs)
    dx = np.abs(((X + 15) % 30) - 15); dy = np.abs(((Y + 15) % 30) - 15)
    road = np.maximum(1 - sstep(4, 5.5, dx), 1 - sstep(4, 5.5, dy))
    avenue = np.maximum(1 - sstep(6, 8, np.abs(((X + 60) % 120) - 60)), 1 - sstep(6, 8, np.abs(((Y + 60) % 120) - 60)))
    rng = np.random.default_rng(3)
    cars = (rng.random((n, n)) < 0.012).astype(np.float32) * np.maximum(road, avenue)
    cars = blur(cars, 0.8) * 6
    em = np.dstack([road * 0.55 + avenue * 0.9, road * 0.33 + avenue * 0.55, road * 0.10 + avenue * 0.2]) * (0.6 + 0.4 * sstep(-1, 1, noise(n, 30, 4)))[..., None]
    em += cars[..., None] * np.array([1.0, 0.9, 0.8])
    base = np.full((n, n, 3), 0.03, np.float32)
    return base, np.clip(em, 0, 1)


def tex_louvre(n=256, slats=12):
    ys = (np.arange(n) + 0.5) / n; Y = np.repeat(ys[:, None], n, 1)
    f = (Y * slats) % 1.0
    h = np.where(f < 0.8, f / 0.8, (1 - f) / 0.2)
    return normal_from_h(h * 0.12, 3.0)


def tex_sock():
    """Windsock fabric: 5 bands orange/white along u, weave, dirt."""
    n = 256; u = (np.arange(n * 2) + 0.5) / (n * 2)
    U, V = np.meshgrid(u, (np.arange(n) + 0.5) / n)
    band = (np.floor(U * 5) % 2 == 0)
    ORA = srgb('ec5a14'); WH = srgb('e8e4dc')
    col = np.where(band[..., None], ORA, WH) * (0.88 + 0.12 * sstep(-1, 1, noise(n, 10, 9, n * 2)))[..., None]
    weave = 0.5 + 0.5 * np.sin(U * n * 2 * 1.5 * math.pi) * np.sin(V * n * 1.5 * math.pi)
    return np.clip(col, 0, 1), normal_from_h(weave * 0.3, 1.0)


# ================================================================ materials
print('textures...')
pc, pr, pn = tex_pad()
M_PAD = mat('PadConcrete', tcol=image('pad_col', pc), trough=image('pad_rough', np.dstack([pr, pr, pr]), True),
            tnrm=image('pad_nrm', pn, True), nstr=1.0)
im_cd, _ = ph('concrete_floor_worn_001', 'Diffuse'); im_cr, _ = ph('concrete_floor_worn_001', 'Rough', True)
im_cn, _ = ph('concrete_floor_worn_001', 'nor_gl', True)
M_CONC = mat('Concrete', tcol=im_cd, trough=im_cr, tnrm=im_cn)
im_gd, _ = ph('tarred_gravel', 'Diffuse'); im_gr, _ = ph('tarred_gravel', 'Rough', True); im_gn, _ = ph('tarred_gravel', 'nor_gl', True)
M_ROOF = mat('RoofGravel', tcol=im_gd, trough=im_gr, tnrm=im_gn)
im_md, _ = ph('metal_plate', 'Diffuse'); im_mr, _ = ph('metal_plate', 'Rough', True); im_mn, _ = ph('metal_plate', 'nor_gl', True)
M_PLATE = mat('TreadPlate', tcol=im_md, trough=im_mr, tnrm=im_mn, metal=0.8)
M_STEEL = mat('SteelGrey', lin('5d6166'), 0.55, 0.3)
M_STEELD = mat('SteelDark', lin('2b2e32'), 0.5, 0.4)
M_GALV = mat('Galvanised', lin('9a9fa3'), 0.42, 0.9)
M_ALU = mat('Aluminium', lin('b8bcc0'), 0.32, 1.0)
M_YELLOWSTEEL = mat('SafetyYellow', lin('d9a91a'), 0.45, 0.0, coat=0.3, coat_r=0.3)
M_RUBBER = mat('Rubber', lin('151515'), 0.75)
M_LENS_G = mat('LensGreen', lin('3bff6a'), 0.1, emit=lin('3bff6a'), estr=14.0)
M_LENS_W = mat('LensWhite', lin('fff6e8'), 0.1, emit=lin('fff6e8'), estr=10.0)
M_LENS_R = mat('LensRed', lin('ff2a14'), 0.15, emit=lin('ff2a14'), estr=18.0)
M_LAMP = mat('LampLens', lin('fff0d8'), 0.1, emit=lin('fff0d8'), estr=40.0)
M_HUTLAMP = mat('HutLamp', lin('ffd9a0'), 0.2, emit=lin('ffd9a0'), estr=12.0)
M_EXIT = mat('ExitSign', lin('18c060'), 0.3, emit=lin('20ff7a'), estr=4.0)
nc, na = tex_net()
M_NET = mat('Net', tcol=image('net_col', nc, alpha=na), rough=0.8, talpha=True)
M_STUCCO = mat('HutRender', tcol=im_cd, trough=im_cr, tnrm=im_cn)
M_DOOR = mat('DoorSteel', lin('3e4a52'), 0.45, 0.5)
M_UNIT = mat('UnitPaint', lin('c9cbc8'), 0.42, 0.1, tnrm=image('louvre_n', tex_louvre(), True), nstr=0.8)
M_FAN = mat('FanDark', lin('1a1c1e'), 0.5, 0.2)
M_COPING = mat('Coping', lin('7d8287'), 0.35, 0.8)
sc, sn = tex_sock()
M_SOCK = mat('Windsock', tcol=image('sock_col', sc), tnrm=image('sock_n', sn, True), rough=0.75, sheen=0.4)
gb, ge = tex_windows(1, 'glass'); cb, ce = tex_windows(2, 'concrete')
M_CITY_G = mat('CityGlass', tcol=image('cityg_col', gb), temit=image('cityg_em', ge), estr=3.0, rough=0.25, spec=0.6)
M_CITY_C = mat('CityConc', tcol=image('cityc_col', cb), temit=image('cityc_em', ce), estr=3.0, rough=0.7)
sb, se = tex_streets()
M_STREET = mat('Streets', tcol=image('street_col', sb), temit=image('street_em', se), estr=4.0, rough=0.9)
tb, te = tex_windows(17, 'glass')
M_TOWER = mat('TowerFacade', tcol=image('tower_col', tb), temit=image('tower_em', te), estr=2.0, rough=0.2, spec=0.7)
M_LOUVRE = mat('CrownLouvre', lin('2e3236'), 0.45, 0.6, tnrm=image('louvre_n2', tex_louvre(256, 20), True))
# helicopter
M_HPAINT = mat('HeliWhite', lin('e6e8ea'), 0.28, 0.0, coat=0.8, coat_r=0.06)
M_HNAVY = mat('HeliNavy', lin('101c3c'), 0.3, 0.0, coat=0.8, coat_r=0.06)
M_HRED = mat('HeliRed', lin('b0141a'), 0.3, 0.0, coat=0.8, coat_r=0.06)
M_HGLASS = mat('HeliGlass', lin('0b0f13'), 0.03, 0.0, spec=1.0)
M_HBLADE = mat('RotorBlade', lin('26292c'), 0.45, 0.3)
M_HTIP = mat('BladeTip', lin('e8c21c'), 0.4)
M_HMETAL = mat('HeliMetal', lin('3a3d40'), 0.4, 0.8)


# ================================================================ the pad
print('modelling...')
prof = [(0, 0), (1.5, 0), (3.0, 0), (4.2, 0), (4.6, 0), (5.0, 0), (RD - 0.06, 0), (RD - 0.015, -0.015), (RD, -0.05),
        (RD, -0.34), (RD - 0.05, -0.40), (4.3, -0.40), (0, -0.40)]
mi = [0] * 8 + [1] * 4
pad = lathe('Pad', prof, [M_PAD, M_CONC], segs=192, mi=mi, uvS=RD)
# give the side a proper concrete UV (cylindrical)
uv = pad.data.uv_layers[0]
for p in pad.data.polygons:
    if p.material_index == 1:
        for li in p.loop_indices:
            co = pad.data.vertices[pad.data.loops[li].vertex_index].co
            uv.data[li].uv = (math.atan2(co.y, co.x) * RD / 2.6, co.z / 2.6 + math.hypot(co.x, co.y) / 2.6)
# steel perimeter gutter / edge angle
lathe('PadGutter', [(RD + 0.001, -0.045), (RD + 0.07, -0.045), (RD + 0.07, -0.37), (RD + 0.001, -0.37)], [M_GALV], segs=192, smooth=30)

# edge lights: 24 recessed-housing pucks, alternating green/white (the game's)
bm = bmesh.new()
NL = 24
for k in range(NL):
    a = TAU * (k + 0.5) / NL; c = Vector((math.cos(a) * (RD - 0.17), math.sin(a) * (RD - 0.17), 0))
    add_cyl(bm, c + Vector((0, 0, 0.008)), 0.105, 0.016, 24, 0)
    add_cyl(bm, c + Vector((0, 0, 0.018)), 0.085, 0.006, 24, 0)
    r_ = add_sphere(bm, c + Vector((0, 0, 0.018)), 0.07, 16, 6, 1 + (k % 2), scale=(1, 1, 0.42))
    bmesh.ops.delete(bm, geom=[v for v in r_['verts'] if v.co.z < 0.0175], context='VERTS')
pucks = bm_obj('EdgeLights', bm, [M_GALV, M_LENS_G, M_LENS_W], smooth=40)

# ---------------------------------------------------------------- safety net round the rim (gap at the stair)
GAP = math.radians(7.5)
def in_gap(a): return abs(((a - STAIR_A + math.pi) % TAU) - math.pi) < GAP
bm = bmesh.new()
ZI, ZO = -0.30, -0.06
NA = 36
for k in range(NA):
    a = TAU * k / NA
    if in_gap(a) and abs(((a - STAIR_A + math.pi) % TAU) - math.pi) < GAP - 0.01: continue
    ca, sa = math.cos(a), math.sin(a)
    p0 = Vector((ca * (RD + 0.07), sa * (RD + 0.07), ZI - 0.04)); p1 = Vector((ca * NET_OUT, sa * NET_OUT, ZO))
    pitch = math.atan2(p1.z - p0.z, (p1 - p0).xy.length)
    add_box(bm, (0, 0, 0), ((p1 - p0).length, 0.05, 0.07), 0,
            M=Matrix.Translation((p0 + p1) / 2) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(-pitch, 4, 'Y'))
    # diagonal strut down to the pad edge beam
    add_tube(bm, (ca * (RD + 0.07), sa * (RD + 0.07), -0.36), (ca * (RD + 0.9), sa * (RD + 0.9), ZI + 0.14 * 0.9 / 1.5 - 0.03), 0.022, 6, 0)
arc_a0 = STAIR_A + GAP; arc_a1 = STAIR_A + TAU - GAP
pts_o = [(math.cos(arc_a0 + (arc_a1 - arc_a0) * t / 160) * NET_OUT, math.sin(arc_a0 + (arc_a1 - arc_a0) * t / 160) * NET_OUT, ZO) for t in range(161)]
sweep(bm, pts_o, 0.03, 8, 0)
netframe = bm_obj('NetFrame', bm, [M_GALV], smooth=40)
# the net itself: an annulus strip with tiled rope texture
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
SEG = 160; rows = [[], [], []]
for t in range(SEG + 1):
    a = arc_a0 + (arc_a1 - arc_a0) * t / SEG
    for j, f in enumerate((0.0, 0.5, 1.0)):
        rr = (RD + 0.07) + (NET_OUT - RD - 0.07) * f; z = ZI + (ZO - ZI) * f - 0.05 * math.sin(math.pi * f)   # a little sag
        rows[j].append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
for t in range(SEG):
    a = arc_a0 + (arc_a1 - arc_a0) * t / SEG; da = (arc_a1 - arc_a0) / SEG
    for j in range(2):
        f = bm.faces.new((rows[j][t], rows[j][t + 1], rows[j + 1][t + 1], rows[j + 1][t]))
        for l, (uu, vv) in zip(f.loops, ((t, j), (t + 1, j), (t + 1, j + 1), (t, j + 1))):
            l[uvl].uv = (uu * da * (RD + 0.8) / 0.5, vv * 0.75 / 0.5)
net = bm_obj('SafetyNet', bm, [M_NET], smooth=0)

# ---------------------------------------------------------------- steel frame under the deck, down to the roof
bm = bmesh.new()
for k in range(8):
    a = TAU * (k + 0.5) / 8; ca, sa = math.cos(a), math.sin(a)
    for rr in (2.0, 4.4):
        c = (ca * rr, sa * rr)
        add_box(bm, (c[0], c[1], (ROOF - 0.42) / 2), (0.30, 0.30, -ROOF - 0.42), 0, rot=Matrix.Rotation(a, 3, 'Z').to_euler())
        add_box(bm, (c[0], c[1], ROOF + 0.02), (0.55, 0.55, 0.04), 0, rot=Matrix.Rotation(a, 3, 'Z').to_euler())   # base plate
    # radial I-beam under the slab
    add_box(bm, (ca * 2.6, sa * 2.6, -0.62), (5.2, 0.16, 0.40), 0, rot=Matrix.Rotation(a, 3, 'Z').to_euler())
    # diagonal bracing between the inner and outer columns
    add_tube(bm, (ca * 2.0, sa * 2.0, ROOF + 0.3), (ca * 4.4, sa * 4.4, -0.9), 0.05, 6, 0)
for rr in (2.0, 4.4):     # ring girders
    pts = [(math.cos(TAU * t / 64) * rr, math.sin(TAU * t / 64) * rr, -0.62) for t in range(64)]
    sweep(bm, pts, 0.2, 4, 0, closed=True, caps=False, shape=lambda k, i, c, s: (c * 0.6, s * 1.0))
frame = bm_obj('PadFrame', bm, [M_STEEL], smooth=30)

# ---------------------------------------------------------------- access stair from the pad edge down to the roof
bm = bmesh.new()
ca, sa = math.cos(STAIR_A), math.sin(STAIR_A); tdir = Vector((ca, sa, 0)); side = Vector((-sa, ca, 0))
SW = 1.1; nst = 14; run = 0.28; rise = (0 - ROOF) / (nst + 1)
start = Vector((ca * (RD + 0.08), sa * (RD + 0.08), 0))
# landing (tread plate) bridging the net gap
L0 = start + tdir * 0.45 + Vector((0, 0, -0.03))
add_box(bm, L0, (0.9, SW + 0.1, 0.05), 1, rot=Matrix.Rotation(STAIR_A, 3, 'Z').to_euler())
for i in range(nst):
    c = start + tdir * (0.9 + run * (i + 0.5)) + Vector((0, 0, -rise * (i + 1)))
    add_box(bm, c, (run + 0.02, SW, 0.04), 1, rot=Matrix.Rotation(STAIR_A, 3, 'Z').to_euler())
end = start + tdir * (0.9 + run * nst)
for sd in (-1, 1):   # stringers + handrails + posts
    o = side * (SW / 2 + 0.04) * sd
    p0 = start + tdir * 0.9 + o + Vector((0, 0, -0.1)); p1 = end + o + Vector((0, 0, ROOF + 0.15))
    add_tube(bm, p0, p1, 0.11, 4, 0)
    h0 = start + tdir * 0.0 + o + Vector((0, 0, 1.0)); h1 = start + tdir * 0.9 + o + Vector((0, 0, 1.0))
    h2 = end + o + Vector((0, 0, ROOF + 1.05)); h3 = end + tdir * 0.6 + o + Vector((0, 0, ROOF + 1.05))
    sweep(bm, [h0, h1, h2, h3], 0.022, 8, 2)
    for q in (0.0, 0.9, 0.9 + run * nst * 0.5, 0.9 + run * nst):
        base = start + tdir * q + o + Vector((0, 0, -0.02 if q <= 0.9 else -rise * (q - 0.9) / run))
        if q == 0.9 + run * nst: base = end + o + Vector((0, 0, ROOF))
        add_tube(bm, base, base + Vector((0, 0, 1.03)), 0.02, 8, 2)
    mid = [start + tdir * 0.9 + o + Vector((0, 0, 0.5)), end + o + Vector((0, 0, ROOF + 0.55))]
    sweep(bm, mid, 0.015, 6, 2)
stair = bm_obj('AccessStair', bm, [M_YELLOWSTEEL, M_PLATE, M_GALV], smooth=30)
for p in stair.data.polygons: pass
box_uv(stair, 1.2)

# ================================================================ roof, parapet, tower
X0, X1, Y0, Y1 = -17.0, 14.0, -11.0, 15.0
bm = bmesh.new(); add_box(bm, ((X0 + X1) / 2, (Y0 + Y1) / 2, ROOF - 0.25), (X1 - X0, Y1 - Y0, 0.5), 0)
roof = bm_obj('RoofSlab', bm, [M_ROOF], smooth=0); box_uv(roof, 3.0)
PH_ = 1.1; PT = 0.35
bm = bmesh.new()
for (cx, cy, sx, sy) in (((X0 + X1) / 2, Y0 + PT / 2, X1 - X0, PT), ((X0 + X1) / 2, Y1 - PT / 2, X1 - X0, PT),
                         (X0 + PT / 2, (Y0 + Y1) / 2, PT, Y1 - Y0 - 2 * PT), (X1 - PT / 2, (Y0 + Y1) / 2, PT, Y1 - Y0 - 2 * PT)):
    add_box(bm, (cx, cy, ROOF + PH_ / 2), (sx, sy, PH_), 0)
    add_box(bm, (cx, cy, ROOF + PH_ + 0.02), (sx + 0.08 * (sx < 1), sy + 0.08 * (sy < 1), 0.04), 1)
parapet = bm_obj('Parapet', bm, [M_CONC, M_COPING], smooth=0); box_uv(parapet, 2.5)
# guard rail on the parapet
bm = bmesh.new()
inset = PT / 2
loop = [(X0 + inset, Y0 + inset), (X1 - inset, Y0 + inset), (X1 - inset, Y1 - inset), (X0 + inset, Y1 - inset)]
for k in range(4):
    a = Vector((*loop[k], 0)); b = Vector((*loop[(k + 1) % 4], 0)); L = (b - a).length; n = max(2, int(L / 1.6))
    for z in (ROOF + PH_ + 1.0, ROOF + PH_ + 0.5):
        add_tube(bm, a + Vector((0, 0, z)), b + Vector((0, 0, z)), 0.025, 8, 0)
    for i in range(n + 1):
        p = a + (b - a) * i / n
        add_tube(bm, p + Vector((0, 0, ROOF + PH_ + 0.04)), p + Vector((0, 0, ROOF + PH_ + 1.0)), 0.02, 6, 0)
rail = bm_obj('GuardRail', bm, [M_GALV], smooth=40)
# tower body: crown louvre band then curtain wall down to the street
bm = bmesh.new(); add_box(bm, ((X0 + X1) / 2, (Y0 + Y1) / 2, ROOF - 3.5), (X1 - X0 + 0.3, Y1 - Y0 + 0.3, 6.0), 0)
crown = bm_obj('TowerCrown', bm, [M_LOUVRE], smooth=0); box_uv(crown, 3.0)
bm = bmesh.new(); add_box(bm, ((X0 + X1) / 2, (Y0 + Y1) / 2, (ROOF - 6.5 - 150) / 2), (X1 - X0, Y1 - Y0, 150 + ROOF + 6.5 + 0.01 + 3), 0)
tower = bm_obj('TowerFacade', bm, [M_TOWER], smooth=0)
me = tower.data; uvt = me.uv_layers.new(name='UVMap')
for p in me.polygons:
    n = p.normal
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        u = co.x if abs(n.y) > 0.5 else co.y
        uvt.data[li].uv = (u / 24.0, co.z / 28.8)

# ---------------------------------------------------------------- stair hut (front-left), with door, lamp, exit sign
HX, HY = -13.2, -6.6; HW, HD, HH = 4.2, 3.6, 3.0
bm = bmesh.new()
add_box(bm, (HX, HY, ROOF + HH / 2), (HW, HD, HH), 0)
add_box(bm, (HX, HY, ROOF + HH + 0.12), (HW + 0.3, HD + 0.3, 0.24), 0)
hut = bm_obj('StairHut', bm, [M_STUCCO], smooth=0); box_uv(hut, 2.0)
bm = bmesh.new()
DX = HX + HW / 2 + 0.03     # door on the east face (towards the pad)
add_box(bm, (DX, HY + 0.5, ROOF + 1.08), (0.06, 1.05, 2.16), 0)            # leaf
add_box(bm, (DX + 0.01, HY + 0.5, ROOF + 2.2), (0.08, 1.25, 0.08), 1)       # frame head
for s_ in (-1, 1): add_box(bm, (DX + 0.01, HY + 0.5 + s_ * 0.58, ROOF + 1.1), (0.08, 0.08, 2.2), 1)
add_box(bm, (DX + 0.07, HY + 0.14, ROOF + 1.05), (0.05, 0.16, 0.03), 1)     # handle
add_box(bm, (DX + 0.04, HY + 0.5, ROOF + 0.15), (0.03, 1.0, 0.25), 1)        # kick plate
add_box(bm, (DX + 0.05, HY + 0.5, ROOF + 2.45), (0.06, 0.42, 0.16), 2)       # exit sign
add_box(bm, (DX + 0.08, HY - 0.45, ROOF + 2.4), (0.12, 0.22, 0.16), 3)       # bulkhead lamp
add_box(bm, (DX + 0.03, HY - 0.45, ROOF + 2.4), (0.04, 0.3, 0.24), 1)
door = bm_obj('HutDoor', bm, [M_DOOR, M_STEELD, M_EXIT, M_HUTLAMP], smooth=0)
# obstruction light on the hut roof
bm = bmesh.new(); add_cyl(bm, (HX + 1.4, HY + 1.2, ROOF + HH + 0.5), 0.04, 0.55, 8, 0)
add_sphere(bm, (HX + 1.4, HY + 1.2, ROOF + HH + 0.85), 0.11, 12, 8, 1)
obl = bm_obj('ObstructionLight', bm, [M_GALV, M_LENS_R])

# ---------------------------------------------------------------- condensers (back-right) and vents, pipes
def condenser(cx, cy, rot):
    bm = bmesh.new(); W_, D_, H_ = 2.6, 1.3, 1.5
    add_box(bm, (0, 0, H_ / 2 + 0.12), (W_, D_, H_), 0)
    for sx in (-1, 1):                       # base rails
        add_box(bm, (sx * (W_ / 2 - 0.15), 0, 0.06), (0.12, D_ + 0.2, 0.12), 2)
    for fx in (-0.65, 0.65):                 # fan shrouds, fans, wire guards
        ret = add_cyl(bm, (fx, 0, H_ + 0.12 + 0.06), 0.55, 0.12, 32, 2)
        add_cyl(bm, (fx, 0, H_ + 0.12 + 0.02), 0.5, 0.02, 32, 1)
        add_cyl(bm, (fx, 0, H_ + 0.12 + 0.07), 0.08, 0.1, 12, 2)
        for b in range(5):
            a = TAU * b / 5
            add_box(bm, (fx + math.cos(a) * 0.27, math.sin(a) * 0.27, H_ + 0.12 + 0.07), (0.42, 0.13, 0.012), 1,
                    rot=(Matrix.Rotation(a, 3, 'Z') @ Matrix.Rotation(0.35, 3, 'X')).to_euler())
        for rr in (0.18, 0.3, 0.42, 0.53):
            pts = [(fx + math.cos(TAU * t / 32) * rr, math.sin(TAU * t / 32) * rr, H_ + 0.12 + 0.135) for t in range(32)]
            sweep(bm, pts, 0.006, 4, 3, closed=True, caps=False)
        for a in (0.0, math.pi / 2):
            add_tube(bm, (fx - math.cos(a) * 0.55, -math.sin(a) * 0.55, H_ + 0.26), (fx + math.cos(a) * 0.55, math.sin(a) * 0.55, H_ + 0.26), 0.007, 4, 3)
    o = bm_obj('Condenser', bm, [M_UNIT, M_FAN, M_STEELD, M_GALV], smooth=30, loc=(cx, cy, ROOF), rot=(0, 0, rot))
    box_uv(o, 2.0, world=False)
    return o
for (cx, cy, rot) in ((8.6, 11.2, 0.0), (11.6, 7.0, math.pi / 2), (11.6, 3.6, math.pi / 2)):
    condenser(cx, cy, rot)
bm = bmesh.new()   # refrigerant pipes on sleepers from the condensers to the hut
pipe_path = [(11.6, 1.7, ROOF + 0.25), (11.6, -4.0, ROOF + 0.25), (6.0, -9.6, ROOF + 0.25), (-10.8, -9.6, ROOF + 0.25), (-10.8, -6.2, ROOF + 0.25)]
for dz in (0.0, 0.0):
    pass
for off in (-0.09, 0.09):
    pts = []
    for i in range(len(pipe_path) - 1):
        a = Vector(pipe_path[i]); b = Vector(pipe_path[i + 1]); d = (b - a).normalized(); s_ = Vector((-d.y, d.x, 0)) * off
        for t in np.linspace(0, 1, 6)[:-1] if i < len(pipe_path) - 2 else np.linspace(0, 1, 6):
            pts.append(a + (b - a) * t + s_)
    sweep(bm, pts, 0.035, 8, 0)
for i in range(len(pipe_path) - 1):
    a = Vector(pipe_path[i]); b = Vector(pipe_path[i + 1]); n = int((b - a).length / 1.8)
    for k in range(n + 1):
        p = a + (b - a) * k / max(n, 1); d = (b - a).normalized()
        add_box(bm, (p.x, p.y, ROOF + 0.09), (0.25 + 0.25 * abs(d.y), 0.25 + 0.25 * abs(d.x), 0.18), 1)
pipes = bm_obj('Pipes', bm, [M_RUBBER, M_STEELD], smooth=40)
# mushroom vents / soil stacks
bm = bmesh.new()
for (vx, vy, s_) in ((-6.0, 12.2, 1.0), (-2.5, 12.6, 0.8), (3.5, 12.4, 1.1), (-15.2, 2.0, 0.9), (-15.0, -1.4, 0.7), (12.4, -7.5, 1.0)):
    add_cyl(bm, (vx, vy, ROOF + 0.45 * s_), 0.16 * s_, 0.9 * s_, 20, 0)
    add_cyl(bm, (vx, vy, ROOF + 0.93 * s_), 0.34 * s_, 0.06 * s_, 24, 0)
    add_cyl(bm, (vx, vy, ROOF + 1.0 * s_), 0.30 * s_, 0.10 * s_, 24, 0, r1=0.05)
    add_cyl(bm, (vx, vy, ROOF + 0.03), 0.3 * s_, 0.06, 20, 1)
vents = bm_obj('Vents', bm, [M_GALV, M_RUBBER], smooth=40)

# ---------------------------------------------------------------- windsock (back-right corner)
WX, WY = 12.2, 13.0
bm = bmesh.new()
add_cyl(bm, (WX, WY, ROOF + 0.15), 0.25, 0.3, 16, 1)
add_tube(bm, (WX, WY, ROOF + 0.2), (WX, WY, 3.2), 0.065, 12, 0, r1=0.045)
for z in (0.6, -1.4):     # aviation-orange bands on the mast
    add_cyl(bm, (WX, WY, z), 0.062, 0.5, 12, 2)
SOCK_A = math.radians(205)    # blowing towards back-left
sd_ = Vector((math.cos(SOCK_A), math.sin(SOCK_A), 0))
top = Vector((WX, WY, 3.0))
# swivel frame: hoop + arm
hoop_c = top + sd_ * 0.35
pts = [hoop_c + (Vector((0, 0, 1)) * math.cos(TAU * t / 24) + sd_.cross(Vector((0, 0, 1))) * math.sin(TAU * t / 24)) * 0.42 for t in range(24)]
sweep(bm, pts, 0.018, 6, 0, closed=True, caps=False)
add_tube(bm, top + Vector((0, 0, -0.42)), hoop_c + Vector((0, 0, -0.42)), 0.02, 6, 0)
add_tube(bm, top + Vector((0, 0, 0.42)), hoop_c + Vector((0, 0, 0.42)), 0.02, 6, 0)
add_cyl(bm, top + Vector((0, 0, 0.0)), 0.05, 0.9, 10, 0)
add_sphere(bm, top + Vector((0, 0, 0.52)), 0.08, 10, 6, 3)   # red top light
wmast = bm_obj('WindsockMast', bm, [M_GALV, M_STEELD, mat('MastOrange', lin('d8541a'), 0.5), M_LENS_R], smooth=40)
# the sock: a tapering, gently drooping, rippled cone
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
L = 3.0; NS_ = 24; NR = 20
rings = []
side_v = sd_.cross(Vector((0, 0, 1)))
for i in range(NS_ + 1):
    t = i / NS_
    p = hoop_c + sd_ * (L * t) + Vector((0, 0, -0.55 * t ** 1.8)) + side_v * 0.12 * math.sin(t * 2.2)
    rr = 0.42 * (1 - 0.55 * t) * (1 + 0.04 * math.sin(t * 19))
    rings.append((p, rr, t))
F = frames([q[0] for q in rings])
vr = []
for (p, rr, t), (_, T_, Nn, B_) in zip(rings, F):
    ring = []
    for j in range(NR):
        a = TAU * j / NR; flat = 1 - 0.18 * t * max(0, math.sin(a))   # tail collapses a little on top
        ring.append(bm.verts.new(p + (Nn * math.cos(a) + B_ * math.sin(a) * flat) * rr * (1 + 0.03 * math.sin(a * 3 + t * 9))))
    vr.append(ring)
for i in range(NS_):
    for j in range(NR):
        jj = (j + 1) % NR
        f = bm.faces.new((vr[i][j], vr[i][jj], vr[i + 1][jj], vr[i + 1][j]))
        for l, (uu, vv) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
            l[uvl].uv = (uu / NS_, vv / NR)
sock = bm_obj('Windsock', bm, [M_SOCK], smooth=60)
sock.modifiers.new('sol', 'SOLIDIFY').thickness = 0.01
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.meshes.new_from_object(sock.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg); sock.modifiers.clear(); sock.data = me

# ---------------------------------------------------------------- floodlight masts aimed at the pad
FLOODS = [(-9.6, -8.6), (9.4, -8.8), (-4.5, 13.6), (6.5, 13.8)]
FLOOD_HEADS = []
bm = bmesh.new()
for (fx, fy) in FLOODS:
    top_z = 4.2
    add_cyl(bm, (fx, fy, ROOF + 0.05), 0.28, 0.1, 16, 0)
    add_tube(bm, (fx, fy, ROOF + 0.1), (fx, fy, top_z), 0.09, 12, 0, r1=0.07)
    to = Vector((-fx, -fy, 0)).normalized(); sdv = Vector((-to.y, to.x, 0))
    add_tube(bm, Vector((fx, fy, top_z)) - sdv * 0.75, Vector((fx, fy, top_z)) + sdv * 0.75, 0.04, 8, 0)
    for s_ in (-1, 1):
        hc = Vector((fx, fy, top_z)) + sdv * 0.55 * s_ + to * 0.15 + Vector((0, 0, -0.05))
        aim = Vector((0, 0, 0)) + sdv * 1.5 * s_
        d = (aim - hc).normalized()
        q = d.to_track_quat('Z', 'Y')
        M4 = Matrix.Translation(hc) @ q.to_matrix().to_4x4()
        add_box(bm, (0, 0, -0.06), (0.62, 0.48, 0.16), 1, M=M4)        # housing
        add_box(bm, (0, 0, 0.025), (0.56, 0.42, 0.012), 2, M=M4)        # lens
        for k in range(6): add_box(bm, (0, -0.18 + k * 0.072, -0.16), (0.58, 0.02, 0.05), 1, M=M4)   # cooling fins
        FLOOD_HEADS.append((hc + d * 0.05, d))
floods = bm_obj('FloodMasts', bm, [M_GALV, M_STEELD, M_LAMP], smooth=30)


# ================================================================ the helicopter (light single-engine, 3-blade)
def smooth_interp(xs, ctrl_x, ctrl_y):
    """Catmull-Rom through the control points."""
    cx = np.asarray(ctrl_x, float); cy = np.asarray(ctrl_y, float); out = []
    for x in xs:
        i = int(np.clip(np.searchsorted(cx, x) - 1, 0, len(cx) - 2))
        t = (x - cx[i]) / (cx[i + 1] - cx[i])
        p0 = cy[max(i - 1, 0)]; p1 = cy[i]; p2 = cy[i + 1]; p3 = cy[min(i + 2, len(cy) - 1)]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def build_heli(loc, heading, s=1.3):
    HM = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(heading, 4, 'Z') @ Matrix.Diagonal((s, s, s, 1))
    parts = []
    def put(name, bm, mats, smooth=35):
        o = bm_obj(name, bm, mats, smooth=smooth); o.matrix_world = HM; parts.append(o); return o
    # ---------------- cabin pod: lofted superellipse sections
    CX = [-2.55, -2.2, -1.6, -0.8, 0.2, 1.0, 1.6, 2.05, 2.38, 2.52]
    CW = [0.26, 0.42, 0.60, 0.68, 0.68, 0.65, 0.56, 0.42, 0.22, 0.04]
    CT = [1.62, 1.82, 2.08, 2.18, 2.16, 2.04, 1.78, 1.45, 1.15, 0.98]
    CB = [1.18, 0.86, 0.60, 0.52, 0.52, 0.54, 0.60, 0.70, 0.82, 0.94]
    NSx, NAr = 56, 48
    xs = np.linspace(CX[0], CX[-1], NSx)
    xs = CX[0] + (CX[-1] - CX[0]) * (0.5 - 0.5 * np.cos(np.linspace(0, math.pi, NSx)))   # denser at the ends
    W_ = np.maximum(smooth_interp(xs, CX, CW), 0.02); T_ = smooth_interp(xs, CX, CT); B_ = smooth_interp(xs, CX, CB)
    bm = bmesh.new(); rings = []
    nexp = 2.7
    for x, w, zt, zb in zip(xs, W_, T_, B_):
        zc = (zt + zb) / 2; h = (zt - zb) / 2; ring = []
        for j in range(NAr):
            a = TAU * j / NAr; ca, sa = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(ca) ** (2 / nexp), ca) * (1 - 0.16 * max(0.0, sa) ** 2)
            z = zc + h * math.copysign(abs(sa) ** (2 / nexp), sa)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    tip = bm.verts.new((CX[-1] + 0.03, 0, 0.97)); tail = bm.verts.new((CX[0] - 0.02, 0, 1.40))
    fl = []
    for i in range(NSx - 1):
        for j in range(NAr):
            jj = (j + 1) % NAr; fl.append(bm.faces.new((rings[i][j], rings[i][jj], rings[i + 1][jj], rings[i + 1][j])))
    for j in range(NAr):
        jj = (j + 1) % NAr
        fl.append(bm.faces.new((rings[-1][j], rings[-1][jj], tip))); fl.append(bm.faces.new((rings[0][jj], rings[0][j], tail)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    def prof_at(x):
        return float(np.interp(x, xs, T_)), float(np.interp(x, xs, B_)), float(np.interp(x, xs, W_))
    for f in bm.faces:
        c = f.calc_center_median(); x, y, z = c; zt, zb, w = prof_at(x); zc = (zt + zb) / 2; hh = (zt - zb) / 2
        rel = (z - zb) / max(zt - zb, 1e-3)
        m_ = 0
        # windscreen / chin bubble: everything forward of the door post above the belly line
        if x > 1.02 and rel > 0.30 and abs(y) > 0.025 and not (x > 2.3): m_ = 3
        if x > 1.02 and 0.27 < rel <= 0.33: m_ = 0
        # cabin door windows
        if -1.45 < x < 0.92 and abs(y) > 0.3 and zc + 0.02 < z < zt - 0.10:
            if not (-0.30 < x < -0.20) and not (0.84 < x < 0.92): m_ = 3
        # navy belly stripe and red pinstripe
        if m_ == 0 and abs(y) > 0.2 and zc - 0.40 < z < zc - 0.18 and x < 1.9: m_ = 1
        if m_ == 0 and abs(y) > 0.2 and zc - 0.15 < z < zc - 0.11 and x < 2.0: m_ = 2
        if m_ == 0 and rel < 0.12: m_ = 1
        f.material_index = m_
    put('HeliCabin', bm, [M_HPAINT, M_HNAVY, M_HRED, M_HGLASS], smooth=50)
    # ---------------- engine cowling + exhaust + intakes
    bm = bmesh.new()
    cx_ = [-2.35, -2.05, -1.2, -0.2, 0.35]; cw_ = [0.16, 0.34, 0.40, 0.38, 0.05]; ct_ = [2.30, 2.52, 2.60, 2.58, 2.16]
    xs2 = np.linspace(cx_[0], cx_[-1], 20); w2 = np.maximum(smooth_interp(xs2, cx_, cw_), 0.04); t2 = smooth_interp(xs2, cx_, ct_)
    rings = []
    for x, w, zt in zip(xs2, w2, t2):
        zb = 1.98; zc = (zt + zb) / 2; h = (zt - zb) / 2; ring = []
        for j in range(24):
            a = TAU * j / 24; ca, sa = math.cos(a), math.sin(a)
            ring.append(bm.verts.new((x, w * math.copysign(abs(ca) ** (2 / 3.0), ca), zc + h * math.copysign(abs(sa) ** (2 / 3.0), sa))))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(24):
            jj = (j + 1) % 24; bm.faces.new((rings[i][j], rings[i][jj], rings[i + 1][jj], rings[i + 1][j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for sd in (-1, 1):
        add_box(bm, (-0.6, sd * 0.395, 2.36), (0.55, 0.03, 0.16), 1)          # intake grilles
        add_tube(bm, (-1.9, sd * 0.2, 2.45), (-2.45, sd * 0.32, 2.62), 0.09, 12, 2)   # exhausts
    add_sphere(bm, (-1.1, 0, 2.62), 0.07, 10, 6, 3, scale=(1.4, 1, 0.8))   # anti-collision beacon
    # mast + hub fairing
    add_cyl(bm, (-0.45, 0, 2.75), 0.07, 0.35, 12, 2)
    add_sphere(bm, (-0.45, 0, 2.94), 0.24, 20, 10, 2, scale=(1, 1, 0.45))
    add_cyl(bm, (-0.45, 0, 3.04), 0.06, 0.14, 12, 2)
    put('HeliCowling', bm, [M_HPAINT, M_FAN, M_HMETAL, M_LENS_R], smooth=40)
    # ---------------- main rotor: 3 blades, slight coning/droop
    bm = bmesh.new()
    for b in range(3):
        a = math.radians(25) + TAU * b / 3
        Rz = Matrix.Rotation(a, 4, 'Z'); hub = Vector((-0.45, 0, 2.96))
        segs_ = 8
        for k in range(segs_):
            r0 = 0.25 + (5.0 - 0.25) * k / segs_; r1 = 0.25 + (5.0 - 0.25) * (k + 1) / segs_
            rm = (r0 + r1) / 2; droop = -0.006 * rm ** 2
            add_box(bm, (rm, 0, droop), (r1 - r0 + 0.01, 0.27 if k else 0.2, 0.04), 0,
                    M=Matrix.Translation(hub) @ Rz @ Matrix.Rotation(-0.012 * rm, 4, 'Y'))
        add_box(bm, (5.12, 0, -0.006 * 5.12 ** 2), (0.25, 0.27, 0.042), 1, M=Matrix.Translation(hub) @ Rz @ Matrix.Rotation(-0.06, 4, 'Y'))
        add_box(bm, (0.2, 0, 0), (0.35, 0.12, 0.09), 2, M=Matrix.Translation(hub) @ Rz)     # blade grip
    put('HeliRotor', bm, [M_HBLADE, M_HTIP, M_HMETAL], smooth=20)
    # ---------------- tail boom, fins, tail rotor
    bm = bmesh.new()
    pts = [(-2.3 - 5.0 * t, 0, 1.42 + 0.18 * t) for t in np.linspace(0, 1, 12)]
    rr = [0.30 - 0.17 * t for t in np.linspace(0, 1, 12)]
    sweep(bm, pts, rr, 20, 0)
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z < 1.42 + 0.18 * (-(c.x + 2.3) / 5.0) - 0.05: f.material_index = 1
    # vertical fin (swept) + ventral fin with tail skid
    extrude_poly(bm, [(-6.75, 1.62), (-7.35, 2.75), (-7.72, 2.78), (-7.55, 1.55)], 0.07, 'XZ', 0.0, 0)
    extrude_poly(bm, [(-6.9, 1.5), (-7.5, 1.48), (-7.62, 0.95), (-7.38, 0.97)], 0.06, 'XZ', 0.0, 1)
    add_tube(bm, (-7.5, 0, 0.99), (-7.0, 0, 1.25), 0.025, 6, 2)
    # horizontal stabiliser with end plates
    extrude_poly(bm, [(-5.15, -1.05), (-5.62, -1.05), (-5.62, 1.05), (-5.15, 1.05)], 0.06, 'XY', 1.55, 0)
    for sd in (-1, 1):
        extrude_poly(bm, [(-5.1, 1.4), (-5.62, 1.38), (-5.7, 1.9), (-5.4, 1.92)], 0.04, 'XZ', sd * 1.07, 1)
        add_sphere(bm, (-5.35, sd * 1.1, 1.58), 0.04, 8, 6, 3 if sd > 0 else 4)
    # tail rotor gearbox + 2 blades on the left side
    add_sphere(bm, (-7.15, -0.12, 1.92), 0.13, 12, 8, 2, scale=(1.3, 1, 1))
    add_cyl(bm, (-7.15, -0.25, 1.92), 0.04, 0.25, 8, 2, axis='Y')
    for b in range(2):
        a = math.radians(70) + math.pi * b
        c = Vector((-7.15, -0.36, 1.92)) + Vector((math.cos(a), 0, math.sin(a))) * 0.42
        add_box(bm, (0, 0, 0), (0.8, 0.02, 0.12), 5, M=Matrix.Translation(c) @ Matrix.Rotation(-a, 4, 'Y'))
    add_sphere(bm, (-7.62, 0, 2.72), 0.035, 8, 6, 6)       # white tail light
    put('HeliTail', bm, [M_HPAINT, M_HNAVY, M_HMETAL, mat('NavGreen', lin('20ff40'), 0.2, emit=lin('20ff40'), estr=8),
                         mat('NavRed', lin('ff2020'), 0.2, emit=lin('ff2020'), estr=8), M_HBLADE, M_LENS_W], smooth=40)
    # ---------------- skids and cross tubes, steps
    bm = bmesh.new()
    for sd in (-1, 1):
        pts = [(-1.65, sd * 1.08, 0.07), (-0.5, sd * 1.08, 0.07), (0.8, sd * 1.08, 0.07), (1.45, sd * 1.08, 0.08), (1.68, sd * 1.08, 0.17), (1.80, sd * 1.08, 0.34)]
        sweep(bm, pts, 0.045, 12, 0)
        add_box(bm, (0.1, sd * 0.98, 0.28), (0.36, 0.14, 0.02), 1)       # step
        add_tube(bm, (0.1, sd * 1.05, 0.08), (0.1, sd * 0.98, 0.27), 0.015, 6, 1)
        add_box(bm, (-1.0, sd * 1.08, 0.025), (0.5, 0.06, 0.03), 2)      # wear shoes
        add_box(bm, (0.9, sd * 1.08, 0.025), (0.5, 0.06, 0.03), 2)
    for xc in (-0.95, 0.85):
        pts = [(xc, -1.08, 0.07), (xc, -0.98, 0.42), (xc, -0.72, 0.60), (xc, 0, 0.62), (xc, 0.72, 0.60), (xc, 0.98, 0.42), (xc, 1.08, 0.07)]
        sweep(bm, pts, 0.042, 12, 0)
    put('HeliSkids', bm, [M_ALU, M_HMETAL, M_RUBBER], smooth=40)
    # registration on the fin (both sides)
    for sd in (-1, 1):
        t = text_mesh('HeliReg', 'JA6K16', 0.12, M_HNAVY)
        t.matrix_world = HM @ Matrix.Translation((-7.3, sd * 0.038, 2.08)) @ \
            (Matrix.Rotation(math.pi, 4, 'Z') if sd > 0 else Matrix.Identity(4)) @ Matrix.Rotation(math.pi / 2, 4, 'X')
        parts.append(t)
    return parts


def text_mesh(name, body, size, mat_, extrude=0.003):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.font = FONT_B; cu.resolution_u = 2
    tmp = bpy.data.objects.new(name + '_t', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    me.materials.clear()
    return obj(name, me, [mat_])


HELI_POS = (-10.2, 8.2, ROOF); HELI_HEAD = math.radians(-28)
heli = build_heli(HELI_POS, HELI_HEAD, 1.25)
# its parking box on the roof: a painted steel deck plate with a yellow box and an aiming T
bm = bmesh.new()
pcx, pcy = HELI_POS[0], HELI_POS[1]
Rh = Matrix.Rotation(HELI_HEAD, 4, 'Z'); Mh = Matrix.Translation((pcx, pcy, ROOF)) @ Rh
add_box(bm, (0, 0, 0.04), (12.0, 6.4, 0.08), 0, M=Mh)
for (cx, cy, sx, sy) in ((0, 3.0, 11.6, 0.15), (0, -3.0, 11.6, 0.15), (5.8, 0, 0.15, 6.15), (-5.8, 0, 0.15, 6.15), (3.4, 0, 1.6, 0.25), (4.2, 0, 0.25, 1.4)):
    add_box(bm, (cx, cy, 0.082), (sx, sy, 0.006), 1, M=Mh)
park = bm_obj('ParkingDeck', bm, [M_CONC, M_YELLOWSTEEL], smooth=0); box_uv(park, 2.6)

# ================================================================ the city below
print('city...')
bm = bmesh.new(); bmc = bmesh.new()
rng = np.random.default_rng(42)
GROUND = -150.0
REDS = []
for gx in range(-12, 13):
    for gy in range(-8, 14):
        cx = gx * 30.0; cy = gy * 30.0
        if abs(cx) < 40 and abs(cy) < 40: continue
        d = math.hypot(cx, cy)
        if d > 380: continue
        if rng.random() < 0.12: continue       # parks / plazas
        sx = rng.uniform(13, 22); sy = rng.uniform(13, 22)
        hmax = 60 + 120 * math.exp(-((d - 140) / 120) ** 2)
        h = rng.uniform(25, hmax) * (1.35 if rng.random() < 0.08 else 1.0)
        target = bm if rng.random() < 0.55 else bmc
        top = GROUND + h
        ret = add_box(target, (cx + rng.uniform(-3, 3), cy + rng.uniform(-3, 3), GROUND + h / 2), (sx, sy, h), 0)
        if rng.random() < 0.4:   # setback tier
            h2 = rng.uniform(8, 30); top = GROUND + h + h2
            add_box(target, (cx, cy, GROUND + h + h2 / 2), (sx * 0.65, sy * 0.65, h2), 0)
        if rng.random() < 0.5:   # roof plant box
            add_box(target, (cx + rng.uniform(-3, 3), cy + rng.uniform(-3, 3), top + 1.5), (sx * 0.3, sy * 0.3, 3), 1)
        if top > -40: REDS.append((cx, cy, top + 3.2))
city_g = bm_obj('CityGlass', bm, [M_CITY_G, M_STEELD], smooth=0)
city_c = bm_obj('CityConcrete', bmc, [M_CITY_C, M_STEELD], smooth=0)
for o, sd in ((city_g, 1), (city_c, 2)):
    me = o.data; uvc = me.uv_layers.new(name='UVMap'); r2 = np.random.default_rng(sd)
    for p in me.polygons:
        n = p.normal; off = (int(r2.integers(8)) / 8, int(r2.integers(8)) / 8)
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) > 0.5: u, v = 0.01, 0.01
            else: u, v = ((co.x if abs(n.y) > 0.5 else co.y) / 24.0 + off[0], (co.z - GROUND) / 28.8 + off[1])
            uvc.data[li].uv = (u, v)
bm = bmesh.new()
for (cx, cy, z) in REDS: add_sphere(bm, (cx, cy, z), 0.9, 6, 4, 0)
reds = bm_obj('CityBeacons', bm, [M_LENS_R], smooth=0)
bm = bmesh.new(); add_box(bm, (0, 0, GROUND), (1200, 1200, 0.2), 0)
streets = bm_obj('Streets', bm, [M_STREET], smooth=0); planar_uv(streets.data, 600)

for o in STAGE:
    if o.type == 'MESH' and not o.data.uv_layers: box_uv(o, 2.0)

# ================================================================ export the stage
total = sum(tris(o) for o in STAGE)
print('TOTAL triangles:', total, ' objects:', len(STAGE))
print('heaviest', sorted(((tris(o), o.name) for o in STAGE), reverse=True)[:12])
bpy.ops.object.select_all(action='DESELECT')
for o in STAGE: o.select_set(True)
GLB = os.path.join(OUT, 'heli.glb')
bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='JPEG', export_jpeg_quality=90)
print('exported', GLB, os.path.getsize(GLB) // 1024, 'KB')
if NOREN: sys.exit(0)


# ================================================================ render-only touches
def view_haze(mname, col, dist, amount=1.0):
    """Fade a distant material into the dusk haze (aerial perspective), by camera distance."""
    m = bpy.data.materials[mname]; nt = m.node_tree; out = nt.nodes['Material Output']; bs = BSDF[mname]
    cd = nt.nodes.new('ShaderNodeCameraData')
    mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'DIVIDE'; mth.inputs[1].default_value = -dist
    nt.links.new(cd.outputs['View Distance'], mth.inputs[0])
    ex = nt.nodes.new('ShaderNodeMath'); ex.operation = 'EXPONENT'; nt.links.new(mth.outputs[0], ex.inputs[0])
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(ex.outputs[0], inv.inputs[1])
    sc_ = nt.nodes.new('ShaderNodeMath'); sc_.operation = 'MULTIPLY'; sc_.inputs[1].default_value = amount; nt.links.new(inv.outputs[0], sc_.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = 1.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(sc_.outputs[0], mix.inputs[0]); nt.links.new(bs.outputs['BSDF'], mix.inputs[1]); nt.links.new(em.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])


HAZE = (0.055, 0.045, 0.075)
for mn in ('CityGlass', 'CityConc', 'Streets'): view_haze(mn, HAZE, float(OPT.get('hazed', 420)), 0.92)
view_haze('TowerFacade', HAZE, 260, 0.9)
BSDF['LensGreen'].inputs['Emission Strength'].default_value = 30
BSDF['LensWhite'].inputs['Emission Strength'].default_value = 24

# fine detail on the pad: a second, finer concrete normal on top of the composite (breaks the 1024 px softness)
nt = M_PAD.node_tree; bs = BSDF['PadConcrete']
tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (14, 14, 1)
nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
fn = nt.nodes.new('ShaderNodeTexImage'); fn.image = im_cn; nt.links.new(mp.outputs['Vector'], fn.inputs['Vector'])
bump_n = [n for n in nt.nodes if n.type == 'NORMAL_MAP'][0]
nm2 = nt.nodes.new('ShaderNodeNormalMap'); nm2.inputs['Strength'].default_value = 0.6
nt.links.new(fn.outputs['Color'], nm2.inputs['Color'])
# combine: use the fine normal as the base normal for the composite normal map (approximate)
mixn = nt.nodes.new('ShaderNodeMix'); mixn.data_type = 'VECTOR'; mixn.inputs['Factor'].default_value = 0.5
nt.links.new(bump_n.outputs['Normal'], mixn.inputs['A']); nt.links.new(nm2.outputs['Normal'], mixn.inputs['B'])
vn = nt.nodes.new('ShaderNodeVectorMath'); vn.operation = 'NORMALIZE'; nt.links.new(mixn.outputs['Result'], vn.inputs[0])
nt.links.new(vn.outputs[0], bs.inputs['Normal'])

# world: the CC0 dusk HDRI for the sky; below the horizon a dark city-glow gradient (the HDRI's car park is not seen)
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world; nt = world.node_tree
bg = nt.nodes['Background']
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(PH, 'rooftop_night.hdr'))
tco = nt.nodes.new('ShaderNodeTexCoord'); mpw = nt.nodes.new('ShaderNodeMapping')
mpw.inputs['Rotation'].default_value = (0, 0, math.radians(float(OPT.get('hrot', 90))))
nt.links.new(tco.outputs['Generated'], mpw.inputs['Vector']); nt.links.new(mpw.outputs['Vector'], env.inputs['Vector'])
sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tco.outputs['Generated'], sep.inputs['Vector'])
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.02; mr.inputs['From Max'].default_value = 0.06
nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
mixw = nt.nodes.new('ShaderNodeMix'); mixw.data_type = 'RGBA'; mixw.inputs['B'].default_value = (0, 0, 0, 1)
mixw.inputs['A'].default_value = (*[c * 0.9 for c in HAZE], 1)
nt.links.new(mr.outputs['Result'], mixw.inputs['Factor']); nt.links.new(env.outputs['Color'], mixw.inputs['B'])
nt.links.new(mixw.outputs['Result'], bg.inputs['Color']); bg.inputs['Strength'].default_value = float(OPT.get('sky', 0.8))


def light(name, kind, loc, look, energy, color, size=None, spot=None, blend=0.5, soft=0.5, glossy=True):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(L)
    L.location = loc; L.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    L.data.energy = energy; L.data.color = color
    if kind == 'AREA': L.data.shape = 'RECTANGLE'; L.data.size, L.data.size_y = size
    if kind == 'SPOT': L.data.spot_size = math.radians(spot); L.data.spot_blend = blend
    if kind in ('SPOT', 'POINT'): L.data.shadow_soft_size = soft
    L.visible_glossy = glossy
    return L


FE = float(OPT.get('flood', 2600))
for k, (hc, d) in enumerate(FLOOD_HEADS):
    light('Flood%d' % k, 'SPOT', hc + d * 0.12, hc + d * 10, FE, (1.0, 0.9, 0.78), spot=60, blend=0.7, soft=0.25)
light('HutLamp', 'POINT', (DX + 0.35, HY - 0.45, ROOF + 2.3), (0, 0, 0), 60, (1.0, 0.75, 0.45), soft=0.1)
light('SockLamp', 'SPOT', (WX - 0.6, WY - 0.6, ROOF + 0.6), (WX - 1.5, WY - 1.0, 3.0), 400, (1.0, 0.9, 0.75), spot=40, soft=0.1)
light('HeliLamp', 'SPOT', (-3.0, 3.5, 4.0), (HELI_POS[0], HELI_POS[1], ROOF + 1.5), 2500, (0.95, 0.9, 0.85), spot=45, blend=0.8, soft=0.4)
light('CityBounce', 'AREA', (0, 0, -40), (0, 0, 0), float(OPT.get('bounce', 5000)), (1.0, 0.6, 0.35), size=(60, 60))


# ================================================================ characters (as stage_render.py)
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHARS, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots


stance = None
RIGS = []
def sumo(f, pos, face, scale=1.65):
    global stance
    new, roots = load(f)
    rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
    if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
    elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
    for r in roots:
        r.location = (pos[0], pos[1], 0); r.scale = (scale,) * 3
        r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))


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


if not NOCHARS:
    A, Bp = (-1.0, -0.15), (1.0, 0.15)
    sumo('sumo2_stance.glb', A, Bp)
    sumo('sumo2_red.glb', Bp, A)
    GX, GY = 0.4, 5.0
    _, gr = load('gyoji.glb')
    for r in gr: r.location = (GX, GY, 0); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
    scn.frame_set(1)
    for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
        if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
    gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    mask('kitsune', Vector((GX, GY, 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)


# ================================================================ cameras & render
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 2000
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
scn.cycles.max_bounces = 6; scn.cycles.glossy_bounces = 3; scn.cycles.transparent_max_bounces = 8
scn.cycles.sample_clamp_indirect = 6.0; scn.cycles.caustics_reflective = scn.cycles.caustics_refractive = False
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.view_settings.exposure = float(OPT.get('exp', 0.0))
scn.use_nodes = True; cnt = scn.node_tree
rl = cnt.nodes['Render Layers']; comp = cnt.nodes['Composite']
gl = cnt.nodes.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 1.5; gl.mix = -0.75; gl.size = 7
cnt.links.new(rl.outputs['Image'], gl.inputs['Image']); cnt.links.new(gl.outputs['Image'], comp.inputs['Image'])

for shot in ('game', 'low', 'top'):
    if shot not in SHOTS: continue
    if shot == 'game':
        el = math.radians(50); dist = 21
        cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
        cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif shot == 'low':
        cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
        cam.rotation_euler = (Vector((0, 0.8, 0.4)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.location = (-2, -2, 40); cam.data.angle_y = math.radians(50)
        cam.rotation_euler = (Vector((-2, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = os.path.join(OUT, 'ex_%s.png' % shot)
    bpy.ops.render.render(write_still=True)
    print('wrote', scn.render.filepath)
