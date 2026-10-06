# ROBOT VACUUM stage, fully modelled: two sumos fight on the lid of a giant round robot vacuum (lidar type) parked on a
# light-oak living-room floor next to a flat-woven rug with a fringe; a sock, a phone cable, crumbs and dust bunnies on
# the floor, the charging dock against the skirting board, a sofa and a potted plant around, daylight from a window.
# Built entirely by script (Blender 4.2 headless).
#   python tools/blender/stage_vacuum.py [out_dir] [shot=game|low ...] [fast] [noexport] [norender] [nochars]
# Writes <out_dir>/vacuum.glb (stage only: Z up, metres, origin at the lid centre, textures packed <= 1024 px, JPEG)
# and <out_dir>/ex_<shot>.png with the game's masked sumos + gyoji imported from scratchpad/stage.
#
# Game contract (public/js/config.js RING_R = 4.6, stages.js vacuum()): the robot's top cover has radius 5.3, top at
# Z = 0 and flat out to r 5.08 (relief only in the maps: seams, button domes <= 1.5 cm). The fighting circle is a cyan
# light ring inlaid in a seam at r 4.6. The lidar turret sits on a rear lobe of the body, entirely beyond r 4.75.
# Scale: a real robot (radius 17 cm, 9 cm tall) x31; the floor is at Z = -2.9.
import bpy, bmesh, math, sys, os, time
import numpy as np
from mathutils import Vector, Matrix

SCR = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
CHAR_DIR = SCR + '/stage'
PH = SCR + '/vac_ph'          # CC0 Poly Haven: laminate_floor_02, potted_plant_04, lythwood_lounge HDRI
FLAGW = {'fast', 'noexport', 'norender', 'nochars'}
ARGS = [a for a in sys.argv[sys.argv.index('--') + 1 if '--' in sys.argv else 1:] if '=' not in a and a not in FLAGW and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else SCR + '/vacuum'
os.makedirs(OUT, exist_ok=True)
SHOTS = [a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')] or ['game', 'low']
FAST = 'fast' in sys.argv
T0 = time.time()
def log(*a): print('[vac %5.1fs]' % (time.time() - T0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RING = 4.6           # fighting circle
RT = 5.3             # top cover radius
FZ = -2.9            # floor
STAGE = bpy.data.collections.new('stage'); scn.collection.children.link(STAGE)
RIG = bpy.data.collections.new('rig'); scn.collection.children.link(RIG)
RNG = np.random.default_rng(11)
F32 = np.float32
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
TEXN = 1024 if FAST else 2048

PHI_F = math.radians(-100)                      # the robot's heading (front), seen from above
FWD = np.array([math.cos(PHI_F), math.sin(PHI_F)], F32)
RIGHT = np.array([math.sin(PHI_F), -math.cos(PHI_F)], F32)
TA = PHI_F + math.pi                           # rear: the lidar lobe
TC = 5.62 * np.array([math.cos(TA), math.sin(TA)], F32); TR = 0.86; LOBE = 1.1


# ================================================================ numpy helpers
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], F32)
def lin(h): return tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in hx(h)) + (1.0,)
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def band(x, a, b, w):
    return ss(a - w, a + w, x) * (1 - ss(b - w, b + w, x))
def lerp(a, b, t): return a + (b - a) * np.asarray(t, F32)[..., None]

def gn(shape, sig, seed):
    """Periodic gaussian-filtered white noise, std 1. sig in px, scalar or (sy, sx)."""
    H, W = shape
    n = np.random.default_rng(seed).standard_normal((H, W)).astype(F32)
    ky = np.fft.fftfreq(H)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    sy, sx = (sig, sig) if np.isscalar(sig) else sig
    g = np.exp(-2 * math.pi ** 2 * ((sx * kx) ** 2 + (sy * ky) ** 2))
    o = np.fft.irfft2(np.fft.rfft2(n) * g, s=(H, W)).astype(F32)
    return o / (o.std() + 1e-8)

def gn1(n, sig, seed):
    x = np.random.default_rng(seed).standard_normal(n).astype(F32)
    k = np.fft.rfftfreq(n); o = np.fft.irfft(np.fft.rfft(x) * np.exp(-2 * math.pi ** 2 * (sig * k) ** 2), n).astype(F32)
    return o / (o.std() + 1e-8)

IMGS = []
def img(name, arr, noncolor=False):
    """arr: (H, W, 3|1) top-down rows, sRGB values for colour maps."""
    arr = np.asarray(arr, F32)
    if arr.ndim == 2: arr = arr[..., None]
    H, W, C = arr.shape
    px = np.ones((H, W, 4), F32); px[..., :3] = arr[..., :3] if C >= 3 else arr[..., :1]
    px = np.ascontiguousarray(px[::-1])
    im = bpy.data.images.new(name, W, H, alpha=False)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.clip(px, 0, 1).ravel()); im.update(); IMGS.append(im); return im

def normal_from_height(h, px_m, strength=1.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px_m)
    dy = -(np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px_m)
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5

def orm(rough, metal=None):
    o = np.ones(rough.shape + (3,), F32); o[..., 1] = rough; o[..., 2] = 0 if metal is None else metal; return o

def text_edges(s, font, spacing=1.0):
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.space_character = spacing; cu.align_x = 'CENTER'
    ob = bpy.data.objects.new('txt', cu); scn.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me)
    E = np.array([[tuple(e.verts[0].co.xy), tuple(e.verts[1].co.xy)] for e in bm.edges if e.is_boundary], F32)
    bm.free(); ev.to_mesh_clear(); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    return E

def fill_edges(E, Hc, Wc, S=4):
    hi = np.zeros((Hc * S, Wc * S), bool)
    x0, y0, x1, y1 = E[:, 0, 0] * S, E[:, 0, 1] * S, E[:, 1, 0] * S, E[:, 1, 1] * S
    for r in range(Hc * S):
        y = r + 0.5
        m = (y0 <= y) != (y1 <= y)
        if not m.any(): continue
        xs = np.sort(x0[m] + (y - y0[m]) * (x1[m] - x0[m]) / (y1[m] - y0[m]))
        for a, b in zip(xs[0::2], xs[1::2]):
            ia, ib = max(0, int(math.ceil(a - 0.5))), min(Wc * S, int(math.floor(b - 0.5)) + 1)
            if ib > ia: hi[r, ia:ib] ^= True
    return hi.reshape(Hc, S, Wc, S).mean((1, 3)).astype(F32)

def text_mask_m(shape, s, font, centre, h_m, up, to_px, spacing=1.0):
    """Coverage of text s (cap height h_m metres) centred at centre (m), its 'up' along unit vector up.
    to_px maps metres (x, y) -> pixel (col, row)."""
    E = text_edges(s, font, spacing)
    lo, hi_ = E.reshape(-1, 2).min(0), E.reshape(-1, 2).max(0)
    k = h_m / (hi_[1] - lo[1]); P = (E - (lo + hi_) / 2) * k
    upv = np.array(up, F32); rt = np.array([upv[1], -upv[0]], F32)
    W = P[..., 0:1] * rt + P[..., 1:2] * upv + np.array(centre, F32)
    Q = np.stack(to_px(W[..., 0], W[..., 1]), -1)
    lo2, hi2 = Q.reshape(-1, 2).min(0), Q.reshape(-1, 2).max(0)
    X0, Y0 = int(lo2[0]) - 3, int(lo2[1]) - 3; Wc, Hc = int(hi2[0] - X0) + 4, int(hi2[1] - Y0) + 4
    Q = Q - np.array([X0, Y0], F32)
    crop = fill_edges(Q, Hc, Wc, 3)
    full = np.zeros(shape, F32)
    ys, xs = slice(max(0, Y0), min(shape[0], Y0 + Hc)), slice(max(0, X0), min(shape[1], X0 + Wc))
    full[ys, xs] = crop[ys.start - Y0:ys.stop - Y0, xs.start - X0:xs.stop - X0]
    return full


# ================================================================ geometry helpers
def mesh_obj(name, verts, faces, uvs=None, coll=STAGE, mat=None, smooth=True, sharp=None, fix=False):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', np.asarray(uvs, F32).ravel())
    me.validate(); me.update()
    if fix:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth()
    if sharp: me.set_sharp_from_angle(angle=math.radians(sharp))
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    if mat: me.materials.append(mat)
    return ob

class Builder:
    """Accumulates (verts, faces, per-loop uvs) pieces into one mesh."""
    def __init__(self): self.V, self.F, self.U = [], [], []; self.n = 0
    def add(self, V, F, U=None):
        V = np.asarray(V, F32)
        for f in F:
            self.F.append([i + self.n for i in f])
            self.U.extend([U[i] for i in f] if U is not None else [(0, 0)] * len(f))
        self.V.extend(map(tuple, V)); self.n += len(V)
    def build(self, name, mat, coll=STAGE, smooth=True, sharp=None):
        return mesh_obj(name, self.V, self.F, self.U, coll, mat, smooth, sharp)

def revolve(name, prof, seg, coll=STAGE, mat=None, centre=(0, 0, 0), sharp=None, uv_planar=None):
    """Lathe an (r, z) profile running top-centre -> out -> down -> in. UV: u around, v along the profile
    (or planar x/y over +-uv_planar)."""
    verts, idx = [], []
    for i, (r, z) in enumerate(prof):
        if r == 0:
            verts.append((centre[0], centre[1], centre[2] + z)); idx.append([len(verts) - 1] * (seg + 1)); continue
        row = []
        for j in range(seg + 1):
            t = j / seg * TAU
            verts.append((centre[0] + r * math.cos(t), centre[1] + r * math.sin(t), centre[2] + z)); row.append(len(verts) - 1)
        idx.append(row)
    faces, uvs = [], []
    for i in range(len(prof) - 1):
        for j in range(seg):
            a, b, c, d = idx[i][j], idx[i][j + 1], idx[i + 1][j + 1], idx[i + 1][j]
            loop = [(a, i, j), (d, i + 1, j), (c, i + 1, j + 1), (b, i, j + 1)]
            if a == b: loop = [(a, i, j), (d, i + 1, j), (c, i + 1, j + 1)]
            elif c == d: loop = [(a, i, j), (d, i + 1, j), (b, i, j + 1)]
            faces.append([l[0] for l in loop])
            for (vi, ii, jj) in loop:
                if uv_planar:
                    x, y = verts[vi][0] - centre[0], verts[vi][1] - centre[1]
                    uvs.append((x / (2 * uv_planar) + 0.5, y / (2 * uv_planar) + 0.5))
                else: uvs.append((jj / seg, 1 - ii / (len(prof) - 1)))
    ob = mesh_obj(name, verts, faces, uvs, coll, mat, True, sharp)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(ob.data); bm.free()
    ob.data.shade_smooth()
    if sharp: ob.data.set_sharp_from_angle(angle=math.radians(sharp))
    return ob

def frames(P):
    P = np.asarray(P, F32); T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    a = np.array([0, 0, 1], F32) if abs(T[0][2]) < 0.9 else np.array([1, 0, 0], F32)
    N = np.cross(T[0], a); N /= np.linalg.norm(N); Ns, Bs = [], []
    for t in T:
        N = N - t * np.dot(N, t); N /= np.linalg.norm(N) + 1e-9; Ns.append(N); Bs.append(np.cross(t, N))
    return T, np.array(Ns), np.array(Bs)

def tube(P, rad, sides=6, cap=True, twist=0.0):
    """Tube along polyline P with radii rad. Returns verts, faces, uvs (per vertex)."""
    P = np.asarray(P, F32); n = len(P); rad = np.broadcast_to(np.asarray(rad, F32), (n,))
    T, N, B = frames(P)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    V, U = [], []
    for i in range(n):
        for k in range(sides):
            a = k / sides * TAU + twist * L[i]
            V.append(P[i] + rad[i] * (math.cos(a) * N[i] + math.sin(a) * B[i])); U.append((k / sides, L[i]))
    F = []
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            F.append([i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k])
    if cap:
        V.append(P[0]); U.append((0.5, 0)); c0 = len(V) - 1
        V.append(P[-1]); U.append((0.5, L[-1])); c1 = len(V) - 1
        for k in range(sides):
            k2 = (k + 1) % sides
            F.append([c0, k2, k]); F.append([c1, (n - 1) * sides + k, (n - 1) * sides + k2])
    return np.array(V, F32), F, U

def catmull(C, per=8):
    C = np.asarray(C, F32); C = np.vstack([2 * C[0] - C[1], C, 2 * C[-1] - C[-2]]); out = []
    for i in range(1, len(C) - 2):
        p0, p1, p2, p3 = C[i - 1], C[i], C[i + 1], C[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(C[-2]); return np.array(out, F32)

def rbox(name, lo, hi, mat, coll=STAGE, bevel=0.0, seg=3, uvscale=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[(a + b) / 2 for a, b in zip(lo, hi)])
    o = bpy.context.object; o.name = name; o.scale = [b - a for a, b in zip(lo, hi)]
    bpy.ops.object.transform_apply(location=True, scale=True)
    for c in o.users_collection: c.objects.unlink(o)
    coll.objects.link(o); o.data.materials.append(mat)
    if uvscale:
        uvl = o.data.uv_layers.active.data
        for p in o.data.polygons:
            nn = p.normal
            for li in p.loop_indices:
                v = o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
                a, b = (v.x, v.y) if abs(nn.z) > 0.5 else ((v.x, v.z) if abs(nn.y) > 0.5 else (v.y, v.z))
                uvl[li].uv = (a / uvscale, b / uvscale)
    if bevel:
        m = o.modifiers.new('b', 'BEVEL'); m.width = bevel; m.segments = seg; m.limit_method = 'ANGLE'
        o.modifiers.new('wn', 'WEIGHTED_NORMAL').keep_sharp = True
    o.data.shade_smooth()
    return o


# ================================================================ materials
def principled(name, col=(0.8, 0.8, 0.8, 1), metal=0.0, rough=0.5, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = col if len(col) == 4 else (*col, 1)
    bs.inputs['Metallic'].default_value = metal; bs.inputs['Roughness'].default_value = rough
    for k, v in kw.items(): bs.inputs[k].default_value = v
    return m, nt, bs

def tex_node(nt, im, uv=None, interp='Linear'):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; t.interpolation = interp
    if uv is not None: nt.links.new(uv, t.inputs['Vector'])
    return t

def hook_maps(nt, bs, col=None, ormi=None, nrm=None, metal=False, nstr=1.0, mapping=None, emis=None, estr=1.0):
    uvn = None
    if mapping:
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = mapping; nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); uvn = mp.outputs['Vector']
    if col: nt.links.new(tex_node(nt, col, uvn).outputs['Color'], bs.inputs['Base Color'])
    if ormi:
        t = tex_node(nt, ormi, uvn); sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bs.inputs['Roughness'])
        if metal: nt.links.new(sep.outputs['Blue'], bs.inputs['Metallic'])
    if nrm:
        t = tex_node(nt, nrm, uvn); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    if emis:
        nt.links.new(tex_node(nt, emis, uvn).outputs['Color'], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = estr

def aniso(nt, bs, amount, axis='Z'):
    tg = nt.nodes.new('ShaderNodeTangent'); tg.direction_type = 'RADIAL'; tg.axis = axis
    nt.links.new(tg.outputs['Tangent'], bs.inputs['Tangent']); bs.inputs['Anisotropic'].default_value = amount

def micro_bump(nt, bs, scale, strength, dist=0.01):
    """Render-only procedural grain (not exported)."""
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 8
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength; bp.inputs['Distance'].default_value = dist
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    if bs.inputs['Normal'].is_linked:
        nt.links.new(bs.inputs['Normal'].links[0].from_socket, bp.inputs['Normal'])
    nt.links.new(bp.outputs['Normal'], bs.inputs['Normal'])

def load_img(path, noncolor=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    IMGS.append(im); return im


# ================================================================ body outline (circle + smooth rear lobe for the lidar)
log('outline')
def sdf(px, py):
    d1 = np.hypot(px, py) - RT; d2 = np.hypot(px - TC[0], py - TC[1]) - LOBE; k = 0.7
    h = np.clip(0.5 + 0.5 * (d2 - d1) / k, 0, 1); return d2 * (1 - h) + d1 * h - k * h * (1 - h)
NO = 4096
THS = np.arange(NO, dtype=F32) / NO * TAU
rr = np.linspace(8.0, 0.0, 3201, dtype=F32)
D = sdf(np.cos(THS)[:, None] * rr[None], np.sin(THS)[:, None] * rr[None])
first = np.argmax(D < 0, axis=1)
d0, d1_ = D[np.arange(NO), first - 1], D[np.arange(NO), first]
ROUT = rr[first - 1] + (rr[first] - rr[first - 1]) * d0 / (d0 - d1_)
OP = np.stack([ROUT * np.cos(THS), ROUT * np.sin(THS)], 1)
TG = np.roll(OP, -1, 0) - np.roll(OP, 1, 0); NRM = np.stack([TG[:, 1], -TG[:, 0]], 1); NRM /= np.linalg.norm(NRM, axis=1, keepdims=True)

def off(th, d):
    """Point on the body outline at polar angle th, moved inward by d (negative: outward)."""
    th = np.mod(th, TAU); r = np.interp(th, THS, ROUT, period=TAU)
    nx = np.interp(th, THS, NRM[:, 0], period=TAU); ny = np.interp(th, THS, NRM[:, 1], period=TAU)
    l = np.hypot(nx, ny); return np.stack([r * np.cos(th) - nx / l * d, r * np.sin(th) - ny / l * d], -1)

def sweep(name, prof, th0, th1, n, mat, closed_prof=False, full=False, cap=False, coll=STAGE, sharp=None):
    """Sweep a (d, z) profile along the body outline between polar angles th0..th1."""
    cols = n if full else n + 1
    ths = th0 + (th1 - th0) * np.arange(cols) / n
    V, F, U = [], [], []
    np_ = len(prof)
    for (d, z) in prof:
        P = off(ths, d)
        for p in P: V.append((p[0], p[1], z))
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(off(ths, 0), axis=0), axis=1))]) / 10.0
    rows = np_ if closed_prof else np_ - 1
    for i in range(rows):
        i2 = (i + 1) % np_
        for j in range(n):
            j2 = (j + 1) % cols
            f = [i * cols + j, i2 * cols + j, i2 * cols + j2, i * cols + j2]
            F.append(f); uj2 = arc[j] + (arc[1] - arc[0]) if (full and j2 == 0) else arc[j2]
            U.extend([(arc[j], 1 - i / (np_ - 1)), (arc[j], 1 - i2 / (np_ - 1)), (uj2, 1 - i2 / (np_ - 1)), (uj2, 1 - i / (np_ - 1))])
    if cap:
        for j in (0, cols - 1):
            f = [i * cols + j for i in range(np_)]
            F.append(f if j else f[::-1]); U.extend([(0.5, 0.5)] * np_)
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', np.asarray(U, F32).ravel())
    me.validate(); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    me.shade_smooth()
    if sharp: me.set_sharp_from_angle(angle=math.radians(sharp))
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob); me.materials.append(mat); return ob


# ================================================================ TOP COVER maps (planar, +-LE)
log('top maps')
LE = 6.9
lpx = 2 * LE / TEXN
g = (np.arange(TEXN, dtype=F32) + 0.5) * lpx - LE
X, Y = np.meshgrid(g, -g)
R = np.hypot(X, Y)
LX = X * RIGHT[0] + Y * RIGHT[1]; LY = X * FWD[0] + Y * FWD[1]
def to_px_top(x, y): return (x + LE) / lpx, (LE - y) / lpx
w = lpx * 0.8

def top_maps():
    H = np.zeros(R.shape, F32)
    # concentric brushing: random radial profile + a little angular wobble
    nr = 65536; rgrid = np.linspace(0, LE * 1.5, nr, dtype=F32)
    prof = gn1(nr, 1.2, 3) * 0.6 + gn1(nr, 6.0, 4) * 0.4
    A = np.arctan2(Y, X)
    brush = np.interp(R + 0.004 * np.sin(A * 3 + 1.0), rgrid, prof)
    panel = 1 - ss(4.44, 4.46, R)
    H += brush * 0.00035 * panel
    col = np.zeros(R.shape + (3,), F32) + hx('a3a8b0')
    tone = 0.92 + 0.08 * gn(R.shape, 60, 5)
    col *= (tone * (1 - 0.06 * ss(0, 4.4, R)))[..., None]
    col = col * (1 + 0.05 * brush[..., None] * panel[..., None])
    rough = np.full(R.shape, 0.3, F32) + 0.03 * brush; metal = np.full(R.shape, 0.6, F32)
    emis = np.zeros(R.shape + (3,), F32)
    CY = hx('00b4ff')
    # fighting-circle light ring: a seam, a frosted diffuser strip, a seam
    seam_i = band(R, 4.45, 4.51, w); strip = band(R, 4.51, 4.69, w); seam_o = band(R, 4.69, 4.74, w); outer = ss(4.74 - w, 4.74 + w, R)
    H += -0.012 * (seam_i + seam_o) - 0.004 * strip
    col = lerp(col, hx('0a0b0c'), seam_i + seam_o); rough = rough * (1 - seam_i - seam_o) + 0.6 * (seam_i + seam_o); metal *= 1 - seam_i - seam_o
    glow = 0.82 + 0.18 * np.cos(np.arctan2(LX, LY) * 1.0)          # a little brighter toward the front
    col = lerp(col, hx('5cc6f2'), strip); rough = rough * (1 - strip) + 0.35 * strip; metal *= 1 - strip
    emis += (strip * glow * (1 - 0.25 * (np.abs(R - 4.6) / 0.09) ** 2))[..., None] * CY
    # outer band: piano black, with a faint satin edge
    col = lerp(col, hx('060708'), outer); rough = rough * (1 - outer) + 0.06 * outer; metal *= 1 - outer
    # ---- centre: CLEAN button, status ring, bezel
    btn = 1 - ss(0.50 - w, 0.50 + w, R); ring = band(R, 0.555, 0.665, w); bez = band(R, 0.68, 0.82, w); gap = band(R, 0.50, 0.555, w) + band(R, 0.665, 0.68, w) + band(R, 0.82, 0.84, w)
    H += 0.012 * btn * (1 - (R / 0.5) ** 2) + 0.004 * bez - 0.008 * gap
    col = lerp(col, hx('0b0c0e'), btn + gap); rough = rough * (1 - btn - gap) + 0.12 * btn + 0.5 * gap; metal *= 1 - btn - gap
    col = lerp(col, hx('8fdcff'), ring); rough = rough * (1 - ring) + 0.3 * ring; metal *= 1 - ring
    emis += (ring * 1.15)[..., None] * CY
    col = lerp(col, hx('c9ccd1'), bez); rough = rough * (1 - bez) + 0.2 * bez       # polished, metal
    # power icon (white print) on the button: ring with a gap toward the front + a bar
    ang = np.degrees(np.arctan2(LX, LY))
    pring = band(np.hypot(LX, LY), 0.17, 0.225, w) * ss(36, 42, np.abs(ang)); pbar = band(LX, -0.027, 0.027, w) * band(LY, 0.04, 0.27, w)
    icon = np.clip(pring + pbar, 0, 1) * btn
    # home + spot buttons in front of the big one
    def small_button(cx, cy):
        rr_ = np.hypot(LX - cx, LY - cy)
        b = 1 - ss(0.2 - w, 0.2 + w, rr_); bz = band(rr_, 0.2, 0.25, w)
        return rr_, b, bz
    nonlocal_icons = []
    for cx, kind in ((-0.46, 'home'), (0.46, 'spot')):
        cy = 1.02
        rr_, b, bz = small_button(cx, cy)
        H += 0.006 * b * (1 - (rr_ / 0.2) ** 2) + 0.003 * bz
        col = lerp(col, hx('0b0c0e'), b); rough = rough * (1 - b) + 0.14 * b; metal *= 1 - b
        col = lerp(col, hx('aeb2b8'), bz); rough = rough * (1 - bz) + 0.22 * bz
        u, v = LX - cx, LY - cy
        if kind == 'home':   # house outline: roof chevron + walls + door
            roof = band(np.abs(u) * 0.95 + (v - 0.105), -0.022, 0.022, w) * band(v, -0.01, 0.11, w)
            walls = (band(np.abs(u), 0.075, 0.105, w) * band(v, -0.1, 0.04, w)) + band(v, -0.1, -0.075, w) * band(np.abs(u), 0, 0.105, w)
            door = band(np.abs(u), 0.0, 0.025, w) * band(v, -0.09, -0.02, w)
            ic = np.clip(roof + walls + door, 0, 1)
        else:                # spot: dot + ring + dashed ring
            rq = np.hypot(u, v); aq = np.arctan2(u, v)
            ic = np.clip((1 - ss(0.03, 0.04, rq)) + band(rq, 0.07, 0.095, w) + band(rq, 0.125, 0.148, w) * (np.cos(aq * 8) > 0), 0, 1)
        icon = np.clip(icon + ic * b, 0, 1)
    col = lerp(col, hx('eef1f4'), icon * 0.95); rough = rough * (1 - icon) + 0.35 * icon
    # brand print toward the rear of the panel
    tm = text_mask_m(R.shape, 'KUMITE', FONT, -FWD * 3.25, 0.30, FWD, to_px_top, 1.25)
    tm2 = text_mask_m(R.shape, 'LIDAR  NAV  PRO', FONT, -FWD * 2.82, 0.12, FWD, to_px_top, 1.4)
    t_all = np.clip(tm + tm2 * 0.85, 0, 1)
    col = lerp(col, hx('b6bbc2'), t_all * 0.9); rough = rough * (1 - t_all) + 0.45 * t_all; metal *= 1 - 0.7 * t_all
    H -= 0.001 * t_all
    # turret collar footprint (geometry covers it) and a fine satin chamfer at the cover edge
    edge = ss(5.0, 5.08, R) * (1 - ss(6.9, 7.0, R))
    rough = rough + 0.03 * edge
    col = np.clip(col, 0, 1)
    return img('top_col', col), img('top_orm', orm(np.clip(rough, 0.03, 1), metal), True), img('top_nrm', normal_from_height(H, lpx), True), img('top_emis', np.clip(emis, 0, 1))

TOP_COL, TOP_ORM, TOP_NRM, TOP_EMIS = top_maps()
mTop, nt, bs = principled('mTopCover', lin('4a4e55'), 1.0, 0.3)
hook_maps(nt, bs, TOP_COL, TOP_ORM, TOP_NRM, metal=True, emis=TOP_EMIS, estr=3.2)
aniso(nt, bs, 0.65)
bs.inputs['Coat Weight'].default_value = 0.0

# ================================================================ BODY
log('body')
EDGE = 0.22
def polar_cap(name, radii_fn, nseg, z, mat, rings=(0.0, 0.08, 0.2, 0.38, 0.58, 0.78, 0.92, 1.0), inner=None):
    """Flat cap: rings scaled between an inner circle (or the centre) and an outer boundary fn(theta)->(n,2)."""
    ths = np.arange(nseg, dtype=F32) / nseg * TAU
    Pout = radii_fn(ths); V, F, U = [], [], []
    if inner is None: V.append((0, 0, z)); start = 1
    else: start = 0
    Pin = np.zeros_like(Pout) if inner is None else np.stack([inner * np.cos(ths), inner * np.sin(ths)], 1)
    rs = [f for f in rings if not (inner is None and f == 0)]
    for f in rs:
        P = Pin + (Pout - Pin) * f
        for p in P: V.append((p[0], p[1], z))
    def vi(k, j): return start + k * nseg + (j % nseg)
    if inner is None:
        for j in range(nseg): F.append([0, vi(0, j), vi(0, j + 1)])
    for k in range(len(rs) - 1):
        for j in range(nseg): F.append([vi(k, j), vi(k + 1, j), vi(k + 1, j + 1), vi(k, j + 1)])
    for f in F:
        for i in f: U.append((V[i][0] / (2 * LE) + 0.5, V[i][1] / (2 * LE) + 0.5))
    return mesh_obj(name, V, F, U, STAGE, mat, True)

# inner panel disc (exact circle, so the radial-tangent brushing is concentric) + outer part out to the edge round
polar_cap('top_panel', lambda t: np.stack([4.48 * np.cos(t), 4.48 * np.sin(t)], 1), 384, 0.0, mTop, rings=(0, 0.06, 0.15, 0.3, 0.5, 0.7, 0.88, 1.0))
polar_cap('top_outer', lambda t: off(t, EDGE), 768, 0.0, mTop, rings=(0.0, 0.25, 0.5, 0.75, 1.0), inner=4.48)

mPiano, nt, bs = principled('mPianoBlack', lin('060708'), 0.0, 0.07, **{'Coat Weight': 0.6, 'Coat Roughness': 0.03})
mTrim, nt, bs = principled('mTrim', lin('c4c7cc'), 1.0, 0.24); aniso(nt, bs, 0.6)
mShell, nt, bs = principled('mShell', lin('1c1d20'), 0.0, 0.48); micro_bump(nt, bs, 400, 0.08)
mBumper, nt, bs = principled('mBumper', lin('121314'), 0.0, 0.4); micro_bump(nt, bs, 600, 0.12)
mIR, nt, bs = principled('mIRWindow', lin('140608'), 0.0, 0.04, **{'Coat Weight': 1.0, 'Coat Roughness': 0.02})
mUnder, nt, bs = principled('mUnder', lin('0e0e10'), 0.0, 0.7)
mTire, nt, bs = principled('mTire', lin('151515'), 0.0, 0.85); micro_bump(nt, bs, 120, 0.3)

arc_ = [(EDGE - EDGE * math.sin(a), -EDGE + EDGE * math.cos(a)) for a in np.linspace(0, math.pi / 2, 9)]
sweep('top_rim', arc_ + [(0, -0.44), (0.02, -0.47), (0.07, -0.48)], 0, TAU, 576, mPiano, full=True)
sweep('trim', [(0.07, -0.48), (0.005, -0.5), (0, -0.53), (0, -0.585), (0.06, -0.6)], 0, TAU, 576, mTrim, full=True)
sweep('shell', [(0.06, -0.6), (0.0, -0.64), (0.0, -2.28), (0.05, -2.42), (0.2, -2.53), (0.5, -2.58)], 0, TAU, 384, mShell, full=True)
polar_cap('underside', lambda t: off(t, 0.5), 256, -2.58, mUnder, rings=(0.0, 0.5, 1.0))
# front bumper: half the perimeter, proud of the shell, with end gaps (the seam)
BA = math.radians(96)
bump = [(0.12, -0.63), (-0.02, -0.63), (-0.07, -0.68), (-0.1, -0.85), (-0.115, -1.2), (-0.11, -1.6), (-0.085, -1.95), (-0.03, -2.15), (0.08, -2.3), (0.2, -2.34)]
sweep('bumper', bump, PHI_F - BA, PHI_F + BA, 420, mBumper, closed_prof=True, cap=True)
sweep('ir_window', [(-0.112, -1.1), (-0.122, -1.13), (-0.122, -1.37), (-0.112, -1.4)], PHI_F - math.radians(20), PHI_F + math.radians(20), 120, mIR, cap=False)
# drive wheels in their wells, the caster at the front
for sd in (-1, 1):
    c = np.array(off(PHI_F + sd * math.pi / 2, 1.5), F32)
    wob = revolve('wheel', [(0, 0.26), (0.5, 0.26), (0.62, 0.2), (0.64, 0.0), (0.62, -0.2), (0.5, -0.26), (0, -0.26)], 40, mat=mTire)
    wob.rotation_euler = (math.pi / 2, 0, PHI_F); wob.location = (c[0], c[1], FZ + 0.64)
cst = revolve('caster', [(0, 0.2), (0.3, 0.2), (0.36, 0), (0.3, -0.2), (0, -0.2)], 24, mat=mTire)
cf = FWD * 3.8; cst.rotation_euler = (math.pi / 2, 0, PHI_F + math.pi / 2); cst.location = (cf[0], cf[1], FZ + 0.36)

# ---- lidar turret on the rear lobe (beyond r 4.75)
log('turret')
mSmoke, nt, bs = principled('mSmokeGlass', lin('07090b'), 0.0, 0.03, **{'Coat Weight': 1.0, 'Coat Roughness': 0.0})
mCap, nt, bs = principled('mCapAlu', lin('5a5d63'), 1.0, 0.26); aniso(nt, bs, 0.7)
cx, cy = float(TC[0]), float(TC[1])
revolve('lidar_collar', [(0, 0.03), (0.9, 0.03), (0.97, 0.015), (0.99, 0.0), (0.99, -0.01)], 96, mat=mTrim, centre=(cx, cy, 0))
revolve('lidar_body', [(0, 0.76), (0.6, 0.76), (0.74, 0.745), (0.82, 0.7), (0.86, 0.62), (0.86, 0.56), (0.83, 0.545), (0.83, 0.2), (0.86, 0.185), (0.86, 0.03), (0.86, 0.0)], 96, mat=mPiano, centre=(cx, cy, 0))
revolve('lidar_window', [(0.842, 0.54), (0.848, 0.52), (0.848, 0.21), (0.842, 0.2)], 96, mat=mSmoke, centre=(cx, cy, 0))
revolve('lidar_cap', [(0, 0.768), (0.5, 0.768), (0.56, 0.762), (0.6, 0.755)], 64, mat=mCap, centre=(cx, cy, 0))

# ---- side brush at the front-right corner: hub, 3 arms of bristle tufts poking out past the bumper
log('side brush')
mHub, nt, bs = principled('mBrushHub', lin('2b2d31'), 0.0, 0.35)
mBristle, nt, bs = principled('mBristle', lin('3a3d42'), 0.0, 0.45, **{'Sheen Weight': 0.3})
SB = off(PHI_F - math.radians(44), 1.05); SBz = FZ + 0.27
hub = revolve('brush_hub', [(0, 0.06), (0.22, 0.06), (0.3, 0.03), (0.32, -0.04), (0.28, -0.07), (0, -0.07)], 40, mat=mHub, centre=(SB[0], SB[1], SBz))
bb = Builder(); hb = Builder()
a0 = PHI_F - math.radians(30)
rng = np.random.default_rng(5)
for k in range(3):
    a = a0 + k * TAU / 3
    d = np.array([math.cos(a), math.sin(a), 0], F32); sdv = np.array([-d[1], d[0], 0], F32)
    # plastic arm stub
    P = np.array([SB[0], SB[1], SBz - 0.02], F32)
    Vt, Ft, Ut = tube([P + d * 0.15, P + d * 0.42 + np.array([0, 0, -0.04], F32)], [0.07, 0.055], 8)
    hb.add(Vt, Ft, Ut)
    base = P + d * 0.4 + np.array([0, 0, -0.05], F32)
    for b in range(34):
        fan = rng.normal(0, 0.09); L = 2.05 + rng.normal(0, 0.06)
        dd = d * math.cos(fan) + sdv * math.sin(fan)
        pts = []
        for t in np.linspace(0, 1, 7):
            sweepback = -sdv * (0.18 * t * t)                 # bristles trail against the spin
            z = (SBz - 0.07) + (FZ + 0.025 + rng.uniform(0, 0.03) - (SBz - 0.07)) * (1 - (1 - t) ** 1.6)
            q = base + dd * (L * t) + sweepback + rng.normal(0, 0.006, 3).astype(F32) * t
            q[2] = max(z, FZ + 0.02); pts.append(q)
        Vt, Ft, Ut = tube(pts, np.linspace(0.016, 0.009, 7), 4, cap=False)
        bb.add(Vt, Ft, Ut)
hb.build('brush_arms', mHub)
bb.build('brush_bristles', mBristle)


# ================================================================ FLOOR, WALL, SKIRTING
log('room')
FT = PH + '/laminate/'
mFloor, nt, bs = principled('mOakFloor', lin('b08a62'), 0.0, 0.45)
FLOOR_TILE = 1.7 * 31       # Poly Haven laminate_floor_02 is 1.7 m square
hook_maps(nt, bs, load_img(FT + 'laminate_floor_02_diff_2k.jpg'), None, load_img(FT + 'laminate_floor_02_nor_gl_2k.jpg', True), nstr=0.6)
rt = tex_node(nt, load_img(FT + 'laminate_floor_02_rough_2k.jpg', True))
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.22; mr.inputs['To Max'].default_value = 0.55
nt.links.new(rt.outputs['Color'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], bs.inputs['Roughness'])
WALLY = 17.0
fx0, fx1, fy0, fy1 = -80, 60, -60, WALLY
V = [(fx0, fy0, FZ), (fx1, fy0, FZ), (fx1, fy1, FZ), (fx0, fy1, FZ)]
off_u, off_v = 0.37, 0.21
UV = [((x / FLOOR_TILE) + off_u, (y / FLOOR_TILE) + off_v) for x, y, _ in V]
fl = mesh_obj('floor', V, [[0, 1, 2, 3]], UV, STAGE, mFloor, False)
bpy.context.view_layer.objects.active = fl
sub = fl.modifiers.new('sub', 'SUBSURF'); sub.subdivision_type = 'SIMPLE'; sub.levels = sub.render_levels = 3

mWall, nt, bs = principled('mWall', lin('e9e4da'), 0.0, 0.85); micro_bump(nt, bs, 6, 0.08, 0.05)
mesh_obj('wall', [(fx0, WALLY, FZ), (fx1, WALLY, FZ), (fx1, WALLY, FZ + 80), (fx0, WALLY, FZ + 80)], [[0, 3, 2, 1]], None, STAGE, mWall, False)
mSkirt, nt, bs = principled('mSkirting', lin('f1eee8'), 0.0, 0.32); micro_bump(nt, bs, 30, 0.04, 0.02)
SK = [(0, 0), (0.48, 0), (0.48, 1.9), (0.44, 2.1), (0.34, 2.22), (0.3, 2.3), (0.18, 2.36), (0.12, 2.5), (0.0, 2.6)]   # (depth, height)
V, F = [], []
for x in (fx0, fx1):
    for dpt, h in SK: V.append((x, WALLY - dpt, FZ + h))
n_ = len(SK)
for i in range(n_ - 1): F.append([i, i + 1, n_ + i + 1, n_ + i])
mesh_obj('skirting', V, F, None, STAGE, mSkirt, True, 40)


# ================================================================ RUG with fringe (left of the robot)
log('rug')
RUG_X1, RUG_X0, RUG_Y0, RUG_Y1 = -8.4, -60.0, -13.5, 12.5
RUG_ROT = math.radians(4); RUG_C = np.array([-8.4, -0.5], F32); RH = 0.26
def rug_maps():
    NU, NV = TEXN, TEXN // 2                    # u along x (first 26 m from the fringe end), v across
    LU, LV = 26.0, RUG_Y1 - RUG_Y0
    u = (np.arange(NU, dtype=F32) + 0.5) / NU * LU; v = (np.arange(NV, dtype=F32) + 0.5) / NV * LV
    U, Vv = np.meshgrid(u, v[::-1])
    pu, pv = LU / NU, LV / NV
    # flat weave: weft rows across, warp bumps
    rowp = 0.13; colp = 0.11
    rowi = np.floor(U / rowp); fu = U / rowp - rowi; fv = Vv / colp + 0.5 * (rowi % 2)
    h = (np.sin(math.pi * fu) ** 0.6) * (0.55 + 0.45 * np.cos(TAU * fv) ** 2) * 0.03
    h += 0.006 * gn(U.shape, 1.2, 21)
    # pattern: ivory field, charcoal lattice of diamonds, borders
    jit = 0.12 * gn(U.shape, 30, 22)
    P = 5.6
    du = np.abs(((U - 2.6 + jit) / P + 0.5) % 1.0 - 0.5) * P; dv = np.abs(((Vv - LV / 2) / P + 0.5) % 1.0 - 0.5) * P
    lat = band(np.abs(du + dv - P / 2), -1, 0.22, 0.05) * (1 - 0)
    diam_c = band(du + dv, -1, 0.55, 0.05)                  # small solid diamond at the lattice centres
    edge_d = np.minimum(Vv, LV - Vv); end_d = U
    border = band(edge_d, 0.9, 1.25, 0.05) + band(edge_d, 1.55, 1.75, 0.05) + band(end_d, 0.9, 1.25, 0.05) + band(end_d, 1.55, 1.75, 0.05)
    field = (edge_d > 2.1) & (end_d > 2.1)
    ink = np.clip(lat * field + diam_c * field + border, 0, 1)
    rust = band(edge_d, 1.28, 1.52, 0.05) * (end_d > 1.25) + band(end_d, 1.28, 1.52, 0.05) * (edge_d > 1.25)
    base = hx('e6dfcf') * (0.93 + 0.05 * gn(U.shape, (2, 90), 23)[..., None])     # abrash: row-wise tone drift
    col = lerp(base, hx('34322f') * (0.9 + 0.1 * gn(U.shape, 3, 24)[..., None]), ink)
    col = lerp(col, hx('a65a3c'), np.clip(rust, 0, 1) * 0.9)
    col *= (0.86 + 0.14 * (h / 0.03))[..., None]
    rough = np.full(U.shape, 0.92, F32)
    return img('rug_col', np.clip(col, 0, 1)), img('rug_orm', orm(rough), True), img('rug_nrm', normal_from_height(h, (pu + pv) / 2, 1.0), True)
RUG_COL, RUG_ORM, RUG_NRM = rug_maps()
mRug, nt, bs = principled('mRug', lin('e6dfcf'), 0.0, 0.9, **{'Sheen Weight': 0.6, 'Sheen Roughness': 0.5})
hook_maps(nt, bs, RUG_COL, RUG_ORM, RUG_NRM, nstr=1.0)
# rug slab: top grid with a slight relief, rounded bound edges
NXr, NYr = 60, 50
LU = 26.0
V, F, Uv = [], [], []
xs = np.linspace(RUG_X1, RUG_X0, NXr + 1); ys = np.linspace(RUG_Y0, RUG_Y1, NYr + 1)
rz = gn((NYr + 1, NXr + 1), 4, 31) * 0.02
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        ed = min(y - RUG_Y0, RUG_Y1 - y, RUG_X1 - x)
        z = FZ + RH * (0.6 + 0.4 * min(1, ed / 0.3) ** 0.5) + rz[j, i] * min(1, ed / 1.0)
        V.append((x, y, z)); Uv.append(((RUG_X1 - x) / LU, (y - RUG_Y0) / (RUG_Y1 - RUG_Y0)))
for j in range(NYr):
    for i in range(NXr):
        a = j * (NXr + 1) + i; F.append([a, a + NXr + 1, a + NXr + 2, a + 1])
# skirt down to the floor around the visible edges
nb = len(V)
def addskirt(idx_list):
    s0 = len(V)
    for k in idx_list:
        x, y, z = V[k]; V.append((x, y, FZ + 0.005)); Uv.append(Uv[k])
    for t in range(len(idx_list) - 1):
        F.append([idx_list[t], s0 + t, s0 + t + 1, idx_list[t + 1]])
addskirt([j * (NXr + 1) for j in range(NYr + 1)][::-1])                       # fringe end (x = RUG_X1)
addskirt([i for i in range(NXr + 1)])                                          # front edge
addskirt([NYr * (NXr + 1) + i for i in range(NXr + 1)][::-1])                  # back edge
UVL = []
for f in F: UVL.extend([Uv[i] for i in f])
rug = mesh_obj('rug', V, F, UVL, STAGE, mRug, True, None, fix=True)
rug.data.uv_layers[0].data.foreach_set('uv', np.asarray(UVL, F32).ravel())
for o in (rug,):
    o.location = (0, 0, 0)
# fringe: cotton tassels along the end
mFringe, nt, bs = principled('mFringe', lin('e3dac8'), 0.0, 0.85, **{'Sheen Weight': 0.8, 'Sheen Roughness': 0.4})
fb = Builder(); rng = np.random.default_rng(8)
for y in np.arange(RUG_Y0 + 0.25, RUG_Y1 - 0.2, 0.2):
    L = 1.55 + rng.normal(0, 0.12); sway = rng.normal(0, 0.18); bend = rng.normal(0, 0.12)
    pts = []
    for t in np.linspace(0, 1, 8):
        x = RUG_X1 - 0.05 + L * t
        yy = y + sway * t * t + bend * math.sin(t * 3.0)
        z = FZ + 0.14 * (1 - min(1, t * 3)) + 0.045 + 0.01 * math.sin(t * 9 + y)
        pts.append((x, yy, z))
    rad = np.array([0.055, 0.075, 0.05, 0.048, 0.046, 0.045, 0.042, 0.03], F32)   # knot near the edge
    Vt, Ft, Ut = tube(pts, rad, 5, twist=6.0); fb.add(Vt, Ft, Ut)
fringe = fb.build('rug_fringe', mFringe)
# rotate the rug about its fringe-end centre
for o in (rug, fringe):
    o.data.transform(Matrix.Translation((RUG_C[0], RUG_C[1], 0)) @ Matrix.Rotation(RUG_ROT, 4, 'Z') @ Matrix.Translation((-RUG_C[0], -RUG_C[1], 0)))


# ================================================================ DOCK against the skirting, its cord
log('dock')
mDockG, nt, bs = principled('mDockGloss', lin('0b0c0d'), 0.0, 0.08, **{'Coat Weight': 0.5, 'Coat Roughness': 0.03})
mDockM, nt, bs = principled('mDockMatte', lin('17181b'), 0.0, 0.5); micro_bump(nt, bs, 500, 0.1)
mContact, nt, bs = principled('mContact', lin('d8d2c4'), 1.0, 0.18)
mLed, nt, bs = principled('mLed', lin('ffffff'), 0.0, 0.3, **{'Emission Color': (0.95, 1.0, 1.0, 1), 'Emission Strength': 6.0})
DX = -6.8; DB = WALLY - 0.48
rbox('dock_tower', (DX - 2.4, DB - 1.55, FZ), (DX + 2.4, DB, FZ + 3.1), mDockM, bevel=0.35, seg=4)
rbox('dock_face', (DX - 2.25, DB - 1.62, FZ + 0.5), (DX + 2.25, DB - 1.3, FZ + 2.95), mDockG, bevel=0.14, seg=3)
rbox('dock_ramp', (DX - 2.3, DB - 3.6, FZ), (DX + 2.3, DB - 1.3, FZ + 0.16), mDockM, bevel=0.07, seg=2)
for sd in (-1, 1):
    rbox('dock_contact', (DX + sd * 1.0 - 0.32, DB - 3.1, FZ + 0.15), (DX + sd * 1.0 + 0.32, DB - 1.9, FZ + 0.2), mContact, bevel=0.03, seg=2)
rbox('dock_led', (DX - 0.16, DB - 1.64, FZ + 2.55), (DX + 0.16, DB - 1.6, FZ + 2.63), mLed)
mCord, nt, bs = principled('mCordBlack', lin('121212'), 0.0, 0.38)
cord = catmull([(DX + 2.2, DB - 0.6, FZ + 0.5), (DX + 2.9, DB - 0.35, FZ + 0.14), (DX + 5.5, DB - 0.25, FZ + 0.13), (DX + 9.0, DB - 0.55, FZ + 0.13),
                (DX + 12.5, DB - 0.3, FZ + 0.13), (DX + 18, DB - 0.2, FZ + 0.13), (DX + 30, DB - 0.2, FZ + 0.13)], 10)
Vt, Ft, Ut = tube(cord, 0.12, 10); b_ = Builder(); b_.add(Vt, Ft, Ut); b_.build('dock_cord', mCord)


# ================================================================ PHONE CABLE (white USB-C, loose on the floor, right)
log('cable')
mCable, nt, bs = principled('mCableWhite', lin('eeeeec'), 0.0, 0.32, **{'Subsurface Weight': 0.15})
mPlug, nt, bs = principled('mPlugMetal', lin('cfd1d4'), 1.0, 0.2)
CR = 0.1
ctrl = [(30, 1.0), (19, 0.6), (14.5, 2.8), (12.6, 6.4), (10.2, 8.0), (8.4, 6.6), (9.6, 4.3), (11.8, 4.0)]
cp = catmull([(x, y, FZ + CR) for x, y in ctrl], 14)
Vt, Ft, Ut = tube(cp, CR, 10); b_ = Builder(); b_.add(Vt, Ft, Ut); b_.build('phone_cable', mCable)
end = cp[-1]; dirv = (cp[-1] - cp[-3]); dirv[2] = 0; dirv /= np.linalg.norm(dirv); ang = math.atan2(dirv[1], dirv[0])
pl = rbox('plug_boot', (-0.15, -0.21, -0.14), (0.95, 0.21, 0.14), mCable, bevel=0.08, seg=3)
pl.data.transform(Matrix.Translation((end[0], end[1], FZ + 0.14)) @ Matrix.Rotation(ang, 4, 'Z'))
tip = rbox('plug_tip', (0.95, -0.15, -0.065), (1.42, 0.15, 0.065), mPlug, bevel=0.05, seg=2)
tip.data.transform(Matrix.Translation((end[0], end[1], FZ + 0.14)) @ Matrix.Rotation(ang, 4, 'Z'))


# ================================================================ SOCK (front right): a flattened knitted tube, L-shaped
log('sock')
def sock():
    # centreline: cuff -> leg -> heel bend -> foot -> toe
    segs = []
    leg = 2.5; heel_r = 0.95; heel_a = math.radians(105); foot = 2.2
    s_list = np.linspace(0, 1, 90)
    Ltot = leg + heel_r * heel_a + foot
    C, Tn = [], []
    for s in s_list * Ltot:
        if s <= leg: p = np.array([0, s]); t = np.array([0, 1.0])
        elif s <= leg + heel_r * heel_a:
            a = (s - leg) / heel_r; p = np.array([heel_r - heel_r * math.cos(a), leg + heel_r * math.sin(a)]); t = np.array([math.sin(a), math.cos(a)])
        else:
            a = heel_a; p0 = np.array([heel_r - heel_r * math.cos(a), leg + heel_r * math.sin(a)]); t = np.array([math.sin(a), math.cos(a)])
            p = p0 + t * (s - leg - heel_r * heel_a)
        C.append(p); Tn.append(t)
    C = np.array(C, F32); Tn = np.array(Tn, F32); Nn = np.stack([Tn[:, 1], -Tn[:, 0]], 1)    # N points to the heel side
    NA = 40
    V, F, U = [], [], []
    rng = np.random.default_rng(3)
    wob = gn((len(s_list), NA), (3, 4), 41)
    for i, s in enumerate(s_list):
        sl = s * Ltot
        wdt = 1.12 + 0.04 * math.sin(s * 9)
        if sl > Ltot - 0.9: k = (Ltot - sl) / 0.9; wdt *= math.sqrt(max(0, 1 - (1 - k) ** 2)) * 0.98 + 0.02
        hgt = 0.13 + 0.03 * math.sin(s * 5 + 1)
        if sl < 0.15: hgt *= 0.4 + 4 * sl
        if sl > Ltot - 0.9: hgt *= max(0.05, (Ltot - sl) / 0.9) ** 0.5
        for j in range(NA):
            a = j / NA * TAU
            ca, sa = math.cos(a), math.sin(a)
            z = (hgt * sa if sa > 0 else hgt * sa * 0.25) + hgt * 0.25 + 0.012 * wob[i, j] + 0.012
            p = C[i] + Nn[i] * (wdt * ca * (1 + 0.02 * wob[i, j]))
            V.append((p[0], p[1], z)); U.append((s, j / NA))
    for i in range(len(s_list) - 1):
        for j in range(NA):
            j2 = (j + 1) % NA
            F.append([i * NA + j, i * NA + j2, (i + 1) * NA + j2, (i + 1) * NA + j])
    Uloop = []
    for f in F:
        uu = [U[k] for k in f]
        if f[1] % NA == 0: uu[1] = (uu[1][0], 1.0); uu[2] = (uu[2][0], 1.0)
        Uloop.extend(uu)
    # close the cuff opening as a flat dark slit and the toe tip
    c0 = len(V); V.append((C[0][0], C[0][1], 0.05));
    for j in range(NA): F.append([c0, (j + 1) % NA, j]); Uloop.extend([(0, 0.5), (0, (j + 1) / NA), (0, j / NA)])
    i = len(s_list) - 1; c1 = len(V); V.append((C[-1][0], C[-1][1], 0.04))
    for j in range(NA): F.append([c1, i * NA + j, i * NA + (j + 1) % NA]); Uloop.extend([(1, 0.5), (1, j / NA), (1, (j + 1) / NA)])
    ob = mesh_obj('sock', V, F, Uloop, STAGE, None, True, None)
    # knit maps: u along the sock (Ltot), v around (circumference ~ 4.6)
    NU, NV = 1024, 512
    uu, vv = np.meshgrid((np.arange(NU) + 0.5) / NU, ((np.arange(NV) + 0.5) / NV)[::-1])
    sm = uu * Ltot
    rows = Ltot / 0.115; cols = 48
    cu, cv = uu * rows, vv * cols
    fu, fv = cu % 1.0, cv % 1.0
    x, y = fv - 0.5, fu - 0.5
    def leg_(x0, rot):
        xr = (x - x0) * math.cos(rot) - y * math.sin(rot); yr = (x - x0) * math.sin(rot) + y * math.cos(rot)
        return np.clip(1 - (xr / 0.22) ** 2 - (yr / 0.62) ** 2, 0, 1) ** 0.5
    knit = np.maximum(leg_(-0.22, 0.45), leg_(0.22, -0.45))
    rib = 0.5 + 0.5 * np.cos(TAU * cv / 2)
    cuff = sm < 0.85
    h = np.where(cuff, 0.6 * rib + 0.4 * knit * rib, knit) * 0.03 + 0.004 * gn(uu.shape, 1.5, 42)
    heather = 0.92 + 0.08 * gn(uu.shape, 0.8, 43)
    col = hx('c3c0bb') * heather[..., None]
    # cuff stripes, heel and toe in charcoal
    stripe = (band(sm, 0.22, 0.34, 0.01) + band(sm, 0.46, 0.58, 0.01))
    col = lerp(col, hx('f1efe9') * heather[..., None], cuff.astype(F32))
    col = lerp(col, hx('243451'), stripe)
    sidev = np.cos(vv * TAU)
    heel = band(sm, 2.25, 2.25 + 0.95 * math.radians(105) + 0.45, 0.06) * ss(0.15, 0.35, sidev)
    toe = ss(Ltot - 0.95, Ltot - 0.85, sm)
    col = lerp(col, hx('55585e') * heather[..., None], np.clip(toe, 0, 1))
    col *= (0.8 + 0.2 * (h / 0.03))[..., None]
    sc, so, sn = img('sock_col', np.clip(col, 0, 1)), img('sock_orm', orm(np.full(uu.shape, 0.9, F32)), True), img('sock_nrm', normal_from_height(h, Ltot / NU, 1.0), True)
    m, nt, bs = principled('mSock', lin('c3c0bb'), 0.0, 0.9, **{'Sheen Weight': 0.7, 'Sheen Roughness': 0.45})
    hook_maps(nt, bs, sc, so, sn)
    ob.data.materials.append(m)
    ob.data.transform(Matrix.Translation((8.4, -5.2, FZ)) @ Matrix.Rotation(math.radians(-28), 4, 'Z'))
    return ob
sock()


# ================================================================ CRUMBS and DUST BUNNIES
log('crumbs + dust')
def ico(sub=1):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    V = np.array([v.co[:] for v in bm.verts], F32); F = [[v.index for v in f.verts] for f in bm.faces]; bm.free(); return V, F
IV, IF = ico(1)
mCrumb, nt, bs = principled('mCrumb', lin('c89a58'), 0.0, 0.75, **{'Subsurface Weight': 0.2, 'Subsurface Radius': (0.05, 0.03, 0.02)})
mCrust, nt, bs = principled('mCrust', lin('7a4520'), 0.0, 0.6)
cb, cb2 = Builder(), Builder(); rng = np.random.default_rng(17)
def crumbs(cx, cy, n, spread, smax):
    for _ in range(n):
        s = smax * (0.35 + 0.65 * rng.random() ** 2)
        p = np.array([cx + rng.normal(0, spread), cy + rng.normal(0, spread * 0.7), 0], F32)
        if np.hypot(p[0], p[1]) < 6.4: continue
        sc = np.array([s * rng.uniform(0.8, 1.3), s * rng.uniform(0.7, 1.1), s * rng.uniform(0.45, 0.7)], F32)
        Vv = IV * (1 + 0.28 * rng.normal(0, 1, (len(IV), 1))).astype(F32) * sc
        a = rng.uniform(0, TAU); Rm = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]], F32)
        Vv = Vv @ Rm.T; Vv[:, 2] -= Vv[:, 2].min(); Vv += p + np.array([0, 0, FZ - 0.01], F32)
        (cb2 if rng.random() < 0.35 else cb).add(Vv, IF, [(0, 0)] * len(Vv))
crumbs(-6.6, -6.4, 14, 1.0, 0.28); crumbs(4.6, -7.0, 7, 1.0, 0.22); crumbs(6.6, 8.6, 6, 1.4, 0.14); crumbs(-1.5, 9.8, 5, 2.0, 0.12)
cb.build('crumbs', mCrumb); cb2.build('crumbs_crust', mCrust)

mDust, nt, bs = principled('mDust', lin('8e8a84'), 0.0, 1.0, **{'Sheen Weight': 1.0, 'Sheen Roughness': 0.3, 'Subsurface Weight': 0.3, 'Subsurface Radius': (0.1, 0.1, 0.1)})
mFluff, nt, bs = principled('mFluff', lin('a8a49d'), 0.0, 0.9, **{'Sheen Weight': 1.0})
db, dc = Builder(), Builder()
def bunny(cx, cy, s, n=70):
    Vc = IV * np.array([s, s * 0.85, s * 0.42], F32) * (1 + 0.2 * rng.normal(0, 1, (len(IV), 1))).astype(F32)
    Vc[:, 2] -= Vc[:, 2].min() + 0.02 * s; Vc += np.array([cx, cy, FZ], F32); dc.add(Vc, IF, [(0, 0)] * len(Vc))
    for _ in range(n):
        u = rng.normal(0, 1, 3); u /= np.linalg.norm(u); p = np.array([cx, cy, FZ + s * 0.25], F32) + u * np.array([s, s * 0.85, s * 0.35], F32) * rng.uniform(0.3, 1.25)
        pts = [p.copy()]; dvec = rng.normal(0, 1, 3); dvec[2] *= 0.3
        for k in range(5):
            dvec = dvec + rng.normal(0, 0.9, 3); dvec[2] *= 0.4; dvec /= np.linalg.norm(dvec)
            p = p + dvec * s * 0.16; p[2] = max(p[2], FZ + 0.01); pts.append(p.copy())
        Vt, Ft, Ut = tube(pts, 0.006 + 0.006 * rng.random(), 3, cap=False); db.add(Vt, Ft, Ut)
bunny(-1.2, WALLY - 1.6, 0.55); bunny(12.0, 9.6, 0.4, 50); bunny(-13.0, -5.0, 0.45, 60); bunny(-17.8, 13.0, 0.6)
dc.build('dust_core', mDust); db.build('dust_fibres', mFluff)


# ================================================================ SOFA corner (left back) and a PLANT (right back)
log('sofa + plant')
mSofa, nt, bs = principled('mSofaFabric', lin('5d6a70'), 0.0, 0.92, **{'Sheen Weight': 0.8, 'Sheen Roughness': 0.5}); micro_bump(nt, bs, 25, 0.35, 0.05)
mWalnut, nt, bs = principled('mWalnut', lin('4a2e1c'), 0.0, 0.35); micro_bump(nt, bs, 3, 0.15, 0.02)
mBrass, nt, bs = principled('mBrass', lin('c99a52'), 1.0, 0.28)
SOX = -21.5
rbox('sofa_base', (SOX - 40, -40, FZ + 3.6), (SOX, WALLY - 0.8, FZ + 9.0), mSofa, bevel=0.9, seg=5)
rbox('sofa_seat', (SOX - 40, -40.5, FZ + 8.6), (SOX + 0.3, WALLY - 0.8, FZ + 16.0), mSofa, bevel=1.6, seg=5)
for ly in (WALLY - 3.0, -8.0):
    revolve('sofa_leg', [(0, 3.62), (0.55, 3.62), (0.52, 1.0), (0.44, 0.5), (0.44, 0.45), (0.38, 0.45), (0.36, 0.02), (0.33, 0.0), (0, 0.0)], 32, mat=mWalnut, centre=(SOX - 1.4, ly, FZ), sharp=50)
    revolve('sofa_ferrule', [(0, 0.5), (0.45, 0.5), (0.45, 0.02), (0.42, 0.0), (0, 0.0)], 32, mat=mBrass, centre=(SOX - 1.4, ly, FZ + 0.001), sharp=50)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=PH + '/plant/potted_plant_04_1k.gltf')
new = [o for o in bpy.data.objects if o not in before]
for o in new:
    for c in list(o.users_collection): c.objects.unlink(o)
    STAGE.objects.link(o)
roots = [o for o in STAGE.all_objects if o in new and (o.parent is None)]
for r in roots:
    r.scale = (31,) * 3; r.location = (12.6, 9.8, FZ); r.rotation_euler = (0, 0, math.radians(30))
for im in bpy.data.images:
    if 'potted_plant' in im.name and im not in IMGS: IMGS.append(im)


# ================================================================ triangle count (stage only)
def tri_count(coll):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0; per = []
    for o in coll.all_objects:
        if o.type != 'MESH': continue
        ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles(); k = len(me.loop_triangles); n += k; per.append((k, o.name)); ev.to_mesh_clear()
    return n, sorted(per, reverse=True)
TRIS, PER = tri_count(STAGE)
log('stage triangles', TRIS, PER[:10])


# ================================================================ characters + masks (as stage_render.py)
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHAR_DIR, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots
GP = (-0.85, 4.66)
def add_characters():
    stance = None; RIGS = []
    def sumo(f, pos, face, scale=1.65):
        nonlocal stance
        new, roots = load(f)
        rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
        if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
        elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
        for r in roots:
            r.location = (pos[0], pos[1], 0.0); r.scale = (scale,) * 3
            r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))
    A, B = (-1.0, -0.15), (1.0, 0.15)
    sumo('sumo2_stance.glb', A, B); sumo('sumo2_red.glb', B, A)
    new, gr = load('gyoji.glb')
    for r in gr: r.location = (GP[0], GP[1], 0); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
    scn.frame_set(1)
    def mmat(name, hexc, rough=0.35):
        m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = lin(hexc); b.inputs['Roughness'].default_value = rough; return m
    def mask(kind, centre, fwd, up, k):
        fwd = (fwd - up * fwd.dot(up)).normalized(); right = fwd.cross(up).normalized()
        Bm = Matrix((right, fwd, up)).transposed().to_4x4(); Bm.translation = centre
        def put(o, loc, mat_):
            o.data.materials.append(mat_); bpy.ops.object.shade_smooth()
            o.matrix_world = Bm @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world
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
    def head_frame(rig, roots):
        pb = rig.pose.bones['head']; M = rig.matrix_world @ pb.matrix
        up = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
        fwd = (roots[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
        return M.translation + up * 0.11 * roots[0].scale[0], fwd, up
    for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
        if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
    gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    mask('kitsune', Vector((GP[0], GP[1], 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)


# ================================================================ lights (window daylight), cameras, render
HDRI = PH + '/lythwood_lounge_2k.hdr'
HDRI_ROT = 200
SUN_DIR = Vector((-0.6, 0.28, -0.75)).normalized()     # light travels toward -x: the window is on the right
def setup_lights():
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world; nt = world.node_tree
    bg = nt.nodes['Background']; env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(HDRI_ROT))
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.8
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); RIG.objects.link(sun)
    sun.data.energy = 5.0; sun.data.angle = math.radians(1.6); sun.data.color = (1.0, 0.97, 0.93)
    sun.rotation_euler = SUN_DIR.to_track_quat('-Z', 'Y').to_euler()
    # window frame in the right-hand wall: only casts the sun patch + mullion shadows (invisible otherwise)
    WX = 48.0
    def back(x, y):    # floor point -> point on the plane x = WX along -SUN_DIR
        t = (WX - x) / -SUN_DIR.x; return Vector((x, y, FZ)) - SUN_DIR * t
    c0, c1 = back(-15.0, -12.0), back(13.0, 18.0)
    y0, y1 = min(c0.y, c1.y), max(c0.y, c1.y); z0, z1 = min(c0.z, c1.z), max(c0.z, c1.z)
    bw = 1.4; parts = []
    big = 400
    parts += [((WX, y0 - big, z0 - big), (WX + 0.5, y0, z1 + big)), ((WX, y1, z0 - big), (WX + 0.5, y1 + big, z1 + big)),
              ((WX, y0, z0 - big), (WX + 0.5, y1, z0)), ((WX, y0, z1), (WX + 0.5, y1, z1 + big))]
    ym = (y0 + y1) / 2; zm = z0 + (z1 - z0) * 0.62
    parts += [((WX, ym - bw / 2, z0), (WX + 0.5, ym + bw / 2, z1)), ((WX, y0, zm - bw / 2), (WX + 0.5, y1, zm + bw / 2))]
    for lo, hi in parts:
        o = rbox('window_occluder', lo, hi, mWall, coll=RIG)
        o.visible_camera = False; o.visible_diffuse = False; o.visible_glossy = False; o.visible_transmission = False
    fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'AREA')); RIG.objects.link(fill)
    fill.data.shape = 'RECTANGLE'; fill.data.size = 40; fill.data.size_y = 30; fill.data.energy = 5e3; fill.data.color = (0.85, 0.92, 1.0)
    fill.location = (40, -10, 25); fill.rotation_euler = (Vector((0, 0, 0)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

def cam_setup(shot):
    cam = bpy.data.objects.get('Cam')
    if not cam:
        cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.dof.use_dof = False; cam.data.clip_end = 2000
    def aim(loc, tgt, fov, fstop=None, focus=None):
        cam.location = loc; cam.data.angle_y = math.radians(fov)
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        if fstop:
            cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
            cam.data.dof.focus_distance = (Vector(focus or tgt) - Vector(loc)).length
    if shot == 'game':
        el = math.radians(50); dist = 21
        aim((0, -dist * math.cos(el), dist * math.sin(el)), (0, 0.6, 0), 34)
    elif shot == 'low':
        aim((10.6, -10.2, 2.9), (0, 0.5, -1.0), 32, 8.0, (0, 0, 1.0))
    elif shot == 'brush':
        aim((2.5, -11.5, -0.6), (-0.6, -4.6, -2.3), 32, 8.0)

def render(shot):
    cam_setup(shot)
    scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'
    scn.cycles.samples = 16 if FAST else 48; scn.cycles.use_denoising = True; scn.cycles.use_adaptive_sampling = True
    scn.cycles.max_bounces = 8; scn.cycles.glossy_bounces = 4; scn.cycles.transmission_bounces = 4; scn.cycles.transparent_max_bounces = 8
    scn.cycles.diffuse_bounces = 3; scn.cycles.caustics_reflective = False; scn.cycles.caustics_refractive = False
    scn.cycles.blur_glossy = 1.0; scn.cycles.sample_clamp_indirect = 8.0
    scn.render.resolution_x, scn.render.resolution_y = (640, 360) if FAST else (1280, 720)
    scn.render.resolution_percentage = 100
    scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
    scn.render.filepath = os.path.join(OUT, 'ex_%s.png' % shot)
    log('render', shot); bpy.ops.render.render(write_still=True); log('done', scn.render.filepath)

if 'norender' not in sys.argv:
    if 'nochars' not in sys.argv: add_characters()
    setup_lights()
    for s in SHOTS: render(s)

# ================================================================ export (stage only, textures <= 1024, JPEG)
if 'noexport' not in sys.argv:
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in STAGE.all_objects: o.select_set(True)
    for im in IMGS:
        w_, h_ = im.size
        if max(w_, h_) > 1024:
            k = 1024 / max(w_, h_); im.scale(max(1, int(w_ * k)), max(1, int(h_ * k)))
        if im.packed_file is None and not im.filepath: im.file_format = 'PNG'; im.pack()
    glb = os.path.join(OUT, 'vacuum.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=90)
    log('exported', glb, '%.1f MB' % (os.path.getsize(glb) / 1e6), 'tris', TRIS)
