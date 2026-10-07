# TAIKO DRUM stage, fully modelled: two sumos fight on the cowhide head of a giant nagado-daiko standing upright on its
# wooden stand (dai) on a polished plank stage: rolled-over hide nailed with two rows of iron byou, a lacquered keyaki
# barrel with brass kan rings, a painted mitsudomoe in the middle; bachi, a hachimaki, a nobori banner and a string of
# glowing paper lanterns around, under one warm stage spot in a dark hall. Built by script (Blender 4.2).
#   python tools/blender/stage_taiko.py [out_dir] [shot=game|low ...] [fast] [noexport] [norender] [nochars]
# Writes <out_dir>/taiko.glb (stage only: Z up, metres, origin at the head centre, textures packed <= 1024 px, JPEG)
# and <out_dir>/ex_<shot>.png with the game's masked sumos + gyoji imported from scratchpad/stage.
#
# Game contract (public/js/config.js RING_R = 4.6, stages.js taiko()): the drum head has radius 5.3, top at Z = 0 and
# perfectly flat out to r 4.95 where the hide rolls over the bearing edge (relief only in the maps). The fighting circle
# is a thin painted line at r 4.6, where the shaved playing area meets the thicker un-shaved rim of the hide.
# Only what the game camera sees is built (no bottom head); only ex_game.png is rendered by default.
# Scale: a 2-shaku drum (head 60 cm) x17.7; the barrel is 9 m long and the floor is at Z = -11.4.
import bpy, bmesh, math, sys, os, time
import numpy as np
from mathutils import Vector, Matrix

SCR = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
CHAR_DIR = SCR + '/stage'
PH = SCR + '/taiko_ph'        # CC0 Poly Haven: dark_wooden_planks (stage floor, stand), rosewood_veneer1 (barrel)
FLAGW = {'fast', 'noexport', 'norender', 'nochars'}
ARGS = [a for a in sys.argv[sys.argv.index('--') + 1 if '--' in sys.argv else 1:] if '=' not in a and a not in FLAGW and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else SCR + '/taiko'
os.makedirs(OUT, exist_ok=True)
SHOTS = [a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')] or ['game']
FAST = 'fast' in sys.argv
T0 = time.time()
def log(*a): print('[taiko %5.1fs]' % (time.time() - T0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RING = 4.6           # fighting circle
RT = 5.3             # head radius
FLAT = 4.95          # flat playing surface; the hide rolls over the bearing edge beyond
ROLL = RT - FLAT
LB = 9.0             # barrel length (top head at 0, bottom head at -LB)
BULGE = 0.72
STAND_H = 2.4
FZ = -LB - STAND_H   # floor
STAGE = bpy.data.collections.new('stage'); scn.collection.children.link(STAGE)
RIG = bpy.data.collections.new('rig'); scn.collection.children.link(RIG)
RNG = np.random.default_rng(23)
F32 = np.float32
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FONT_J = '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'
TEXN = 1024 if FAST else 2048


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



# ================================================================ taiko helpers
def poly_mask(shape, polys_px, S=3):
    """Even-odd coverage of closed polygons given in pixel coords (x right, y down)."""
    E = np.concatenate([np.stack([P, np.roll(P, -1, 0)], 1) for P in polys_px], 0).astype(F32)
    lo, hi = E.reshape(-1, 2).min(0), E.reshape(-1, 2).max(0)
    X0, Y0 = max(0, int(lo[0]) - 2), max(0, int(lo[1]) - 2)
    X1, Y1 = min(shape[1], int(hi[0]) + 3), min(shape[0], int(hi[1]) + 3)
    full = np.zeros(shape, F32)
    if X1 <= X0 or Y1 <= Y0: return full
    full[Y0:Y1, X0:X1] = fill_edges(E - np.array([X0, Y0], F32), Y1 - Y0, X1 - X0, S)
    return full

def blur(a, sig):
    H, W = a.shape; ky = np.fft.fftfreq(H)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    g = np.exp(-2 * math.pi ** 2 * sig ** 2 * (kx ** 2 + ky ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(H, W)).astype(F32)

def tomoe_polys(cx, cy, RE, to_px, rot=0.0):
    """Mitsudomoe: three commas (head disc + tail hugging the outer circle), as polygons in pixel coords.
    Same construction as the game's canvas version (stages.js), scaled to an outer radius RE."""
    k = RE / 172.0; polys = []
    for c in range(3):
        a = rot + c / 3 * TAU; pts = []
        for s in range(41):
            f = s / 40; ang = a + f * 2.3; rad = (80 + f * 90) * k; w2 = 70 * (1 - f) * k
            pts.append((cx + math.cos(ang) * (rad + w2), cy + math.sin(ang) * (rad + w2)))
        for s in range(40, -1, -1):
            f = s / 40; ang = a + f * 2.3; rad = (80 + f * 90) * k; w2 = 70 * (1 - f) * k
            pts.append((cx + math.cos(ang) * (rad - w2 * 0.3), cy + math.sin(ang) * (rad - w2 * 0.3)))
        P = np.array(pts, F32); polys.append(np.stack(to_px(P[:, 0], P[:, 1]), 1))
        hc = (cx + math.cos(a) * 95 * k, cy + math.sin(a) * 95 * k); hr = 62 * k
        t = np.linspace(0, TAU, 72, endpoint=False)
        Hc = np.stack([hc[0] + hr * np.cos(t), hc[1] + hr * np.sin(t)], 1).astype(F32)
        polys.append(np.stack(to_px(Hc[:, 0], Hc[:, 1]), 1))
    return polys

def tomoe_mask(X, Y, cx, cy, RE, rot, w, n=3):
    """Mitsudomoe coverage (anti-aliased over w metres): three commas, each a head disc whose tail sweeps round
    against the outer circle and tapers to a point just short of the next comma."""
    x, y = X - cx, Y - cy; rho = np.hypot(x, y); phi = np.arctan2(y, x)
    d, hr, DL = 0.5 * RE, 0.29 * RE, 2.3
    m = np.zeros(X.shape, F32)
    for c in range(n):
        a = rot + c / n * TAU
        head = 1 - ss(hr - w, hr + w, np.hypot(x - d * math.cos(a), y - d * math.sin(a)))
        dl = np.mod(a - phi, TAU)                        # the tail runs clockwise behind the head
        inner = (d - hr) + (RE - (d - hr)) * np.clip(dl / DL, 0, 1) ** 0.7
        outer = np.minimum(RE, d + hr + (RE - d - hr) * np.sqrt(np.clip(dl / 0.7, 0, 1)))
        tail = ss(inner - w, inner + w, rho) * (1 - ss(outer - w, outer + w, rho)) * (1 - ss(DL - 0.01, DL, dl))
        m = np.maximum(m, np.maximum(head, tail))
    return m

def union_mask(shape, polys):
    m = np.zeros(shape, F32)
    for P in polys: m = np.maximum(m, poly_mask(shape, [P]))
    return m

def rb(z):
    """Barrel radius at height z (0 .. -LB): bearing edges RT at the heads, a belly of +BULGE in the middle."""
    t = np.clip((-np.asarray(z, F32) - ROLL) / (LB - 2 * ROLL), 0, 1)
    return RT + BULGE * np.sin(math.pi * t) ** 0.85
def drb(z, e=1e-3): return (rb(z + e) - rb(z - e)) / (2 * e)

def frame_at(th, z, lift=0.0):
    """Point on the barrel surface + basis (tangent around, down-the-surface, outward normal)."""
    r = float(rb(z)) + lift; n = np.array([math.cos(th), math.sin(th), -float(drb(z))], F32); n /= np.linalg.norm(n)
    t = np.array([-math.sin(th), math.cos(th), 0], F32); d = np.cross(n, t)      # d points up the barrel
    return np.array([r * math.cos(th), r * math.sin(th), z], F32), t, -d, n

def lathe_template(prof, seg, rmod=None):
    """(r, h) profile from the top centre outwards -> verts (axis +Z), faces."""
    V, F, rows = [], [], []
    for i, (r, h) in enumerate(prof):
        if r == 0: V.append((0, 0, h)); rows.append([len(V) - 1] * seg); continue
        row = []
        for j in range(seg):
            a = j / seg * TAU; rr_ = r * (rmod(a) if rmod else 1)
            V.append((rr_ * math.cos(a), rr_ * math.sin(a), h)); row.append(len(V) - 1)
        rows.append(row)
    for i in range(len(prof) - 1):
        for j in range(seg):
            a, b, c, d = rows[i][j], rows[i][(j + 1) % seg], rows[i + 1][(j + 1) % seg], rows[i + 1][j]
            if a == b: F.append([a, d, c])
            elif c == d: F.append([a, d, b])
            else: F.append([a, d, c, b])
    return np.array(V, F32), F

def torus_template(R, r, sR=40, sr=10):
    V, F = [], []
    for i in range(sR):
        a = i / sR * TAU
        for j in range(sr):
            b = j / sr * TAU
            V.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    for i in range(sR):
        for j in range(sr):
            i2, j2 = (i + 1) % sR, (j + 1) % sr
            F.append([i * sr + j, i2 * sr + j, i2 * sr + j2, i * sr + j2])
    return np.array(V, F32), F

def place(builder, V, F, origin, X, Y, Z, uv=None):
    M = np.stack([X, Y, Z], 1).astype(F32)
    builder.add(V @ M.T + origin, F, uv if uv is not None else [(0, 0)] * len(V))

def xform(objs, k, at):
    T = Matrix.Translation(at) @ Matrix.Diagonal((k, k, k, 1))
    for o in objs: o.data.transform(T)

def mirrored(ob, name):
    """Copy of ob mirrored to the bottom head (z -> -LB - z), normals fixed."""
    me = ob.data.copy(); me.transform(Matrix.Translation((0, 0, -LB)) @ Matrix.Diagonal((1, 1, -1, 1)))
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o2 = bpy.data.objects.new(name, me); STAGE.objects.link(o2); return o2


# ================================================================ DRUMHEAD maps (planar +-LE_S)
LE_S = 5.45
def skin_maps(tag, crest=True, n=TEXN, seed=0):
    log('skin maps', tag)
    lp = 2 * LE_S / n
    g_ = (np.arange(n, dtype=F32) + 0.5) * lp - LE_S
    X, Y = np.meshgrid(g_, -g_); R = np.hypot(X, Y); A = np.arctan2(Y, X)
    def to_px(x, y): return (x + LE_S) / lp, (LE_S - y) / lp
    w = lp * 0.8
    sh = R.shape
    # rawhide: cream, fibrous, with faint veins and translucent / denser patches
    f1, f2, f3 = gn(sh, 2.0 * n / 2048, 101 + seed), gn(sh, 9 * n / 2048, 102 + seed), gn(sh, 60 * n / 2048, 103 + seed)
    fib = gn(sh, (1.0 * n / 2048, 7 * n / 2048), 104 + seed)
    vein = np.exp(-(gn(sh, 26 * n / 2048, 105 + seed) / 0.07) ** 2) * (0.5 + 0.5 * gn(sh, 80 * n / 2048, 106 + seed))
    col = hx('e6d2a6') * (1 + 0.035 * f1 + 0.06 * f2 + 0.09 * f3 + 0.03 * fib)[..., None]
    col = lerp(col, hx('bf9a66'), np.clip(vein, 0, 1) * 0.55)
    col = lerp(col, hx('f3e6c6'), np.clip(0.5 * f3 - 0.3, 0, 1) * 0.5)          # thinner, more translucent patches
    # worn centre: greyer and darker where the bachi land, strike marks
    wear = np.exp(-(R / 2.7) ** 2) * np.clip(0.75 + 0.35 * f2, 0, 1.2)
    col = lerp(col, hx('a9906c'), wear * 0.42)
    rng = np.random.default_rng(7 + seed); marks = np.zeros(sh, F32)
    for _ in range(140):
        rr_ = abs(rng.normal(0, 1.4)); aa = rng.uniform(0, TAU); px_, py_ = to_px(rr_ * math.cos(aa), rr_ * math.sin(aa))
        s_ = rng.uniform(0.05, 0.16) / lp; y0, x0 = int(py_), int(px_); rad = int(s_ * 3) + 1
        ys, xs = slice(max(0, y0 - rad), min(n, y0 + rad)), slice(max(0, x0 - rad), min(n, x0 + rad))
        yy, xx = np.mgrid[ys, xs]; marks[ys, xs] += np.exp(-((xx - px_) ** 2 + (yy - py_) ** 2) / (2 * s_ * s_)) * rng.uniform(0.2, 0.6)
    col = lerp(col, hx('8f7656'), np.clip(marks, 0, 1) * 0.5)
    rough = 0.42 + 0.06 * f2 + 0.12 * wear
    H = 0.00035 * f1 + 0.0002 * fib + 0.0006 * f2
    # the un-shaved rim of the hide outside the fighting circle: denser, amber, with stretch wrinkles at the roll
    rimz = ss(4.62, 4.78, R)
    col = lerp(col, hx('cfa76b') * (1 + 0.05 * f2[..., None]), rimz)
    col = lerp(col, hx('a77a43'), ss(5.0, 5.3, R) * 0.7)
    wr = np.sin(A * 110 + 2.5 * f2) * ss(4.75, 5.15, R)
    H += 0.003 * wr; col *= (1 - 0.06 * wr * ss(4.8, 5.2, R))[..., None]
    # the painted fighting line at r 4.6
    line = band(R, 4.565, 4.635, w)
    paint_noise = ss(0.45, 0.75, 0.5 + 0.5 * gn(sh, 3 * n / 2048, 108 + seed))
    col = lerp(col, hx('2a1a12'), line * (0.92 - 0.25 * paint_noise))
    rough = rough * (1 - line) + 0.35 * line
    if crest:
        RE = 2.2
        tm = tomoe_mask(X, Y, 0.0, 0.0, RE, math.radians(80), w)
        outline = np.clip(blur(tm, 3.0 * n / 2048) * 3.0, 0, 1) * (1 - tm)
        ringm = band(R, RE + 0.12, RE + 0.27, w)
        worn = 1 - 0.55 * ss(0.55, 0.85, 0.5 + 0.5 * gn(sh, 2.5 * n / 2048, 109 + seed)) * np.exp(-(R / 1.6) ** 2)
        red = hx('b0241b') * (0.92 + 0.08 * f2[..., None])
        col = lerp(col, red, tm * worn)
        col = lerp(col, hx('17100c'), np.clip(outline * 0.9 + ringm, 0, 1) * worn)
        p_ = np.clip(tm + outline + ringm, 0, 1) * worn
        rough = rough * (1 - p_) + 0.3 * p_; H += 0.0004 * p_
    col = np.clip(col, 0, 1)
    return img('skin_col_' + tag, col), img('skin_orm_' + tag, orm(np.clip(rough, 0.05, 1)), True), img('skin_nrm_' + tag, normal_from_height(H, lp), True)

def skin_material(tag, maps):
    m, nt, bs = principled('mHide_' + tag, lin('ead8b0'), 0.0, 0.45, **{'Subsurface Weight': 0.3, 'Subsurface Radius': (0.08, 0.05, 0.025), 'Subsurface Scale': 1.0, 'Sheen Weight': 0.15})
    hook_maps(nt, bs, *maps); return m

def flap_maps():
    NU, NV = TEXN, 128
    u = (np.arange(NU) + 0.5) / NU; v = (np.arange(NV) + 0.5) / NV
    U, Vv = np.meshgrid(u, v[::-1]); sh = U.shape
    f2 = gn(sh, (6, 18), 201); f1 = gn(sh, 1.5, 202)
    f3 = gn(sh, (20, 60), 203)
    col = hx('a8773e') * (1 + 0.1 * f2 + 0.04 * f1 + 0.08 * f3)[..., None]
    col = lerp(col, hx('6e4a22'), ss(0.45, 1.0, Vv) * 0.7)
    # stretch folds between the tacks (64 per row, 6 texture repeats around -> 64/6 per tile is not integral: use sin)
    H = 0.004 * np.sin(U * TAU * 64 / 6 + 1.5 * f2) * ss(0.1, 0.6, Vv) + 0.0005 * f1
    return img('flap_col', np.clip(col, 0, 1)), img('flap_orm', orm(np.clip(0.5 + 0.05 * f2, 0, 1)), True), img('flap_nrm', normal_from_height(H, 0.02), True)


# ================================================================ materials
log('materials')
SKIN_A = skin_maps('crest', True)
mHide = skin_material('crest', SKIN_A)
mFlap, nt, bs = principled('mHideFlap', lin('a8773e'), 0.0, 0.42, **{'Subsurface Weight': 0.35, 'Subsurface Radius': (0.08, 0.04, 0.015)})
hook_maps(nt, bs, *flap_maps(), mapping=(6, 1, 1))
RW = PH + '/rosewood_veneer1/'
mBarrel, nt, bs = principled('mKeyakiLacquer', lin('6a2a14'), 0.0, 0.25, **{'Coat Weight': 1.0, 'Coat Roughness': 0.045, 'Coat IOR': 1.52})
hook_maps(nt, bs, load_img(RW + 'rosewood_veneer1_diff_2k.jpg'), None, load_img(RW + 'rosewood_veneer1_nor_gl_2k.jpg', True), nstr=0.35, mapping=(1.0, 0.24, 1))
rtn = tex_node(nt, load_img(RW + 'rosewood_veneer1_rough_2k.jpg', True), nt.nodes['Mapping'].outputs['Vector'])
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.18; mr.inputs['To Max'].default_value = 0.4
nt.links.new(rtn.outputs['Color'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], bs.inputs['Roughness'])
mIron, nt, bs = principled('mByouIron', lin('5e554c'), 0.65, 0.34); micro_bump(nt, bs, 40, 0.3, 0.01)
mBrass, nt, bs = principled('mKanBrass', lin('a88445'), 1.0, 0.3); micro_bump(nt, bs, 25, 0.2, 0.01)
DW = PH + '/dark_wooden_planks/'
def plank_mat(name, rmin, rmax, tint=None):
    m, nt, bs = principled(name, lin('4a3426'), 0.0, 0.3)
    hook_maps(nt, bs, load_img(DW + 'dark_wooden_planks_diff_2k.jpg'), None, load_img(DW + 'dark_wooden_planks_nor_gl_2k.jpg', True), nstr=0.7)
    rt_ = tex_node(nt, load_img(DW + 'dark_wooden_planks_rough_2k.jpg', True))
    mr_ = nt.nodes.new('ShaderNodeMapRange'); mr_.inputs['To Min'].default_value = rmin; mr_.inputs['To Max'].default_value = rmax
    nt.links.new(rt_.outputs['Color'], mr_.inputs['Value']); nt.links.new(mr_.outputs['Result'], bs.inputs['Roughness'])
    return m
mFloor = plank_mat('mStageFloor', 0.12, 0.42)
mStand = plank_mat('mStandWood', 0.25, 0.5)
mBlackIron, nt, bs = principled('mBlackIron', lin('151413'), 0.8, 0.45)


# ================================================================ DRUM builder
def drum(tag, k, at, crest=True, kan_angles=(math.radians(-42), math.radians(138)), ntack=64, q=1.0, bottom_tacks=True, bottom=True):
    log('drum', tag)
    objs = []
    hide = mHide
    # head: flat playing surface, the hide rolling over the bearing edge
    rings = [1.6, 3.4, 4.6, FLAT]
    arc = [(FLAT + ROLL * math.sin(a), -ROLL + ROLL * math.cos(a)) for a in np.linspace(0, math.pi / 2, 7)[1:]]
    hseg = int(224 * q) // 8 * 8
    head = revolve('head_' + tag, [(0, 0.0)] + [(r, 0.0) for r in rings] + arc, hseg, mat=hide, uv_planar=LE_S)
    objs.append(head)
    # the hide flap nailed down the barrel, ragged lower edge
    seg, rows = int(224 * q) // 8 * 8, 7
    rag = gn1(seg, 2.0, 61) * 0.05 + 0.05 * np.abs(np.sin(np.arange(seg) / seg * TAU * ntack / 2)) + 0.03 * gn1(seg, 12, 62)
    V, F, U = [], [], []
    for j in range(seg + 1):
        th = j / seg * TAU; ze = -1.78 + rag[j % seg]
        for i in range(rows + 1):
            s = i / rows; z = -ROLL + (ze + ROLL) * s
            lift = 0.035 * ss(0.0, 0.12, s)
            r = float(rb(z)) + lift; V.append((r * math.cos(th), r * math.sin(th), z)); U.append((j / seg, 1 - s))
        r = float(rb(ze)) + 0.003; V.append((r * math.cos(th), r * math.sin(th), ze - 0.004)); U.append((j / seg, 0.0))
    nr = rows + 2
    for j in range(seg):
        for i in range(nr - 1):
            F.append([j * nr + i, j * nr + i + 1, (j + 1) * nr + i + 1, (j + 1) * nr + i])
    UL = []
    for f in F: UL.extend([U[q] for q in f])
    flap = mesh_obj('flap_' + tag, V, F, UL, STAGE, mFlap, True, None, fix=True); objs.append(flap)
    # barrel
    zs = np.linspace(-ROLL - 0.25, -LB + ROLL + 0.25, int(24 * q) + 2)
    barrel = revolve('barrel_' + tag, [(float(rb(z)), float(z)) for z in zs], int(128 * q) // 8 * 8, mat=mBarrel); objs.append(barrel)
    # bottom head (mirrored)
    if bottom:
        hb_ = revolve('head_bottom_' + tag, [(0, -LB)] + [(FLAT, -LB)] + [(r, -LB - z) for r, z in arc], 64, mat=hide, uv_planar=LE_S)
        bm = bmesh.new(); bm.from_mesh(hb_.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(hb_.data); bm.free()
        objs.append(hb_); objs.append(mirrored(flap, 'flap_bottom_' + tag))
    # byou: two staggered rows of dome-headed iron tacks top and bottom
    tb = Builder()
    TV, TF = lathe_template([(0, 0.078), (0.12, 0.07), (0.19, 0.046), (0.232, 0.014), (0.225, -0.01)], 10)
    rngt = np.random.default_rng(71)
    for zrow, ph in ((-0.8, 0.0), (-1.3, 0.5)):
        for q in range(ntack):
            th = (q + ph + rngt.normal(0, 0.03)) / ntack * TAU
            for z in ((zrow, -LB - zrow) if bottom_tacks else (zrow,)):
                p, t, d, n = frame_at(th, z, 0.03)
                sc = 1 + rngt.normal(0, 0.03)
                place(tb, TV * sc, TF, p, t, d, n)
    objs.append(tb.build('byou_' + tag, mIron, sharp=None))
    # kan: brass rosette plate, staple and a ring hanging flat against the belly
    kb = Builder()
    RV, RF = lathe_template([(0, 0.2), (0.22, 0.19), (0.45, 0.14), (0.68, 0.08), (0.84, 0.03), (0.86, 0.0)], 48, rmod=lambda a: 1 + 0.05 * math.cos(16 * a))
    BV, BF = lathe_template([(0, 0.34), (0.1, 0.33), (0.16, 0.28), (0.17, 0.18), (0.14, 0.17), (0.0, 0.17)], 16)
    SV, SF = torus_template(0.17, 0.055, 20, 8)
    KV, KF = torus_template(0.92, 0.12, 48, 10)
    for th in kan_angles:
        p, t, d, n = frame_at(th, -LB * 0.37, 0.0)
        place(kb, RV, RF, p, t, d, n); place(kb, BV, BF, p, t, d, n)
        place(kb, SV, SF, p + n * 0.36, n, d, t)
        place(kb, KV, KF, p + n * 0.42 + d * 0.86, t, d, n)
    objs.append(kb.build('kan_' + tag, mBrass))
    # stand (dai): a square frame on four short legs, two bearers under the drum, iron corner caps
    st = []
    zt = -LB
    st.append(rbox('dai_beam', (-7.3, -6.75, zt - 1.05), (7.3, -5.75, zt), mStand, bevel=0.06, seg=2, uvscale=35))
    st.append(rbox('dai_beam', (-7.3, 5.75, zt - 1.05), (7.3, 6.75, zt), mStand, bevel=0.06, seg=2, uvscale=35))
    st.append(rbox('dai_beam', (-7.3, -5.75, zt - 1.05), (-6.3, 5.75, zt), mStand, bevel=0.06, seg=2, uvscale=35))
    st.append(rbox('dai_beam', (6.3, -5.75, zt - 1.05), (7.3, 5.75, zt), mStand, bevel=0.06, seg=2, uvscale=35))
    for sx in (-3.0, 3.0):
        st.append(rbox('dai_bearer', (sx - 0.5, -5.75, zt - 0.95), (sx + 0.5, 5.75, zt), mStand, bevel=0.06, seg=2, uvscale=35))
    for sx in (-6.8, 6.8):
        for sy in (-6.25, 6.25):
            st.append(rbox('dai_leg', (sx - 0.62, sy - 0.62, zt - STAND_H), (sx + 0.62, sy + 0.62, zt - 1.05), mStand, bevel=0.06, seg=2, uvscale=35))
            st.append(rbox('dai_cap', (sx - 0.62 - 0.03, sy - 0.62 - 0.03, zt - 0.5), (sx + 0.62 + 0.03, sy + 0.62 + 0.03, zt + 0.03), mBlackIron, bevel=0.03, seg=2))
    objs += st
    xform(objs, k, at)
    return objs

DRUM = drum('main', 1.0, (0, 0, 0), bottom_tacks=False, bottom=False)


# ================================================================ FLOOR (polished stage planks)
log('floor')
PT = 2.0 * 17.7
V = [(-90, -70, FZ), (90, -70, FZ), (90, 90, FZ), (-90, 90, FZ)]
mesh_obj('floor', V, [[0, 1, 2, 3]], [((x / PT) + 0.13, (y / PT) + 0.4) for x, y, _ in V], STAGE, mFloor, False)


# ================================================================ BACHI and HACHIMAKI (front right)
log('bachi + hachimaki')
mBachi, nt, bs = principled('mBachiWood', lin('cfae7e'), 0.0, 0.45); micro_bump(nt, bs, 6, 0.12, 0.02)
def bachi(x, y, ang, roll=0.0):
    prof = [(0, 7.1), (0.11, 7.08), (0.19, 7.02), (0.235, 6.86), (0.24, 6.2), (0.222, 1.2), (0.205, 0.16), (0.15, 0.02), (0, 0)]
    o = revolve('bachi', prof, 18, mat=mBachi)
    o.data.transform(Matrix.Translation((x, y, FZ + 0.236)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'Y') @ Matrix.Translation((0, 0, -3.55)))
    return o
bachi(11.2, 1.0, math.radians(18)); bachi(11.6, 2.2, math.radians(-14))

def hachimaki():
    ctrl = [(9.0, 5.8), (11.2, 6.6), (13.6, 6.0), (15.0, 4.2), (16.4, 3.0), (18.6, 3.6), (20.2, 5.4)]
    C = catmull([(x, y, 0) for x, y in ctrl], 14)
    T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True); S = np.stack([-T[:, 1], T[:, 0], np.zeros(len(T))], 1)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]); Ls = L[-1]
    W = 0.9; V, Uv = [], []
    for i in range(len(C)):
        z = FZ + 0.015 + 0.07 * (0.5 + 0.5 * math.sin(L[i] * 1.3)) + 0.03 * (0.5 + 0.5 * math.sin(L[i] * 3.7))
        for sgn in (-1, 1):
            tilt = 0.07 * math.sin(L[i] * 1.9) * sgn
            p = C[i] + S[i] * (W / 2) * sgn; V.append((p[0], p[1], z + tilt)); Uv.append((L[i] / Ls, (sgn + 1) / 2))
    F = [[2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2] for i in range(len(C) - 1)]
    UL = []
    for f in F: UL.extend([Uv[q] for q in f])
    # texture: white cotton, red hinomaru in the middle, 必勝 either side
    NU, NV = 2048, 112
    lpu, lpv = Ls / NU, W / NV
    def to_px(x, y): return x / lpu, (W / 2 - y) / lpv
    uu, vv = np.meshgrid((np.arange(NU) + 0.5) * lpu, W / 2 - (np.arange(NV) + 0.5) * lpv)
    weave = gn(uu.shape, 0.8, 301); col = hx('f2efe8') * (0.96 + 0.025 * weave + 0.02 * gn(uu.shape, (6, 30), 302))[..., None]
    disc = 1 - ss(0.27, 0.29, np.hypot(uu - Ls / 2, vv))
    col = lerp(col, hx('c4231d'), disc)
    t1 = text_mask_m(uu.shape, '必勝', FONT_J, (Ls / 2 - 1.15, 0.0), 0.5, (0, 1), to_px, 1.0)
    t2 = text_mask_m(uu.shape, '必勝', FONT_J, (Ls / 2 + 1.15, 0.0), 0.5, (0, 1), to_px, 1.0)
    col = lerp(col, hx('16120f'), np.clip(t1 + t2, 0, 1) * 0.95)
    hm, nt, bs = principled('mHachimaki', lin('f2efe8'), 0.0, 0.85, **{'Sheen Weight': 0.5})
    hook_maps(nt, bs, img('hachimaki_col', np.clip(col, 0, 1)))
    return mesh_obj('hachimaki', V, F, UL, STAGE, hm, True)
hachimaki()


# ================================================================ NOBORI banner (back left)
log('banner')
mLacq, nt, bs = principled('mBlackLacquer', lin('0d0b0a'), 0.0, 0.12, **{'Coat Weight': 0.6, 'Coat Roughness': 0.05})
BX, BY = -17.5, 12.5
BT, BB, BWd = 7.2, -8.6, 5.6
def banner_tex():
    NU, NV = 512, 1440
    lp = BWd / NU
    def to_px(x, y): return x / lp, (BT - y) / lp
    xx, yy = np.meshgrid((np.arange(NU) + 0.5) * lp, BT - (np.arange(NV) + 0.5) * lp)
    sh = xx.shape
    dye = gn(sh, (40, 8), 401); weave = gn(sh, 0.7, 402)
    col = hx('1c2a4c') * (1 + 0.08 * dye + 0.03 * weave)[..., None]
    white = hx('eeeae0')
    border = (xx < 0.5) | (yy > BT - 0.45)
    loops = (xx < 0.5) & (np.sin((yy - BT) / 2.4 * math.pi) > 0.82)
    col = lerp(col, white * (0.97 + 0.03 * weave[..., None]), border.astype(F32))
    col = lerp(col, hx('7a1c16'), loops.astype(F32) * 0.0)
    crest = tomoe_mask(xx, yy, BWd / 2 + 0.25, BT - 2.0, 1.25, 0.4, lp)
    cring = band(np.hypot(xx - BWd / 2 - 0.25, yy - BT + 2.0), 1.4, 1.58, lp)
    tx1 = text_mask_m(sh, '太', FONT_J, (BWd / 2 + 0.25, BT - 6.0), 3.2, (0, 1), to_px)
    tx2 = text_mask_m(sh, '鼓', FONT_J, (BWd / 2 + 0.25, BT - 10.4), 3.2, (0, 1), to_px)
    ink = np.clip(crest + cring + tx1 + tx2, 0, 1)
    bleed = np.clip(blur(ink, 1.5) * 1.2, 0, 1)
    col = lerp(col, white * (0.94 + 0.05 * dye[..., None]), bleed)
    return img('banner_col', np.clip(col, 0, 1)), img('banner_nrm', normal_from_height(0.002 * weave, lp), True)
bcol, bnrm = banner_tex()
mBanner, nt, bs = principled('mBannerCloth', lin('1c2a4c'), 0.0, 0.85, **{'Sheen Weight': 0.6})
hook_maps(nt, bs, bcol, None, bnrm, nstr=0.5)
NXb, NZb = 14, 40
V, Uv, F = [], [], []
for j in range(NZb + 1):
    z = BT - (BT - BB) * j / NZb
    for i in range(NXb + 1):
        x = BWd * i / NXb
        wv = 0.32 * math.sin(x * 1.1 + z * 0.22 + 0.6) * (x / BWd) + 0.12 * math.sin(z * 0.5) + 0.15 * (x / BWd) ** 2
        V.append((BX + 0.25 + x, BY + wv, z)); Uv.append((x / BWd, (z - BB) / (BT - BB)))
for j in range(NZb):
    for i in range(NXb):
        a = j * (NXb + 1) + i; F.append([a, a + NXb + 1, a + NXb + 2, a + 1])
UL = []
for f in F: UL.extend([Uv[q] for q in f])
mesh_obj('banner', V, F, UL, STAGE, mBanner, True)
pb = Builder()
for P, r in (([(BX, BY, FZ), (BX, BY, BT + 1.2)], 0.2), ([(BX, BY, BT + 0.15), (BX + BWd + 0.5, BY, BT + 0.15)], 0.11)):
    Vt, Ft, Ut = tube(P, r, 16); pb.add(Vt, Ft, Ut)
pb.build('banner_pole', mLacq)
fin = revolve('banner_finial', [(0, 0.9), (0.18, 0.82), (0.3, 0.55), (0.32, 0.3), (0.22, 0.05), (0, 0.0)], 20, mat=mBrass, centre=(BX, BY, BT + 1.2))
base = rbox('banner_base', (BX - 1.2, BY - 1.2, FZ), (BX + 1.2, BY + 1.2, FZ + 0.6), mLacq, bevel=0.12, seg=3)


# ================================================================ LANTERNS on a sagging rope (back)
log('lanterns')
def lantern_tex():
    NU, NV = 1024, 512
    uu, vv = np.meshgrid((np.arange(NU) + 0.5) / NU, ((np.arange(NV) + 0.5) / NV)[::-1])
    sh = uu.shape
    fib = gn(sh, 1.2, 501); blot = gn(sh, 25, 502)
    col = hx('d0381e') * (1 + 0.05 * fib + 0.06 * blot)[..., None]
    bandm = band(vv, -1, 0.11, 0.004) + band(vv, 0.89, 2, 0.004)
    col = lerp(col, hx('1a1210'), bandm * 0.9)
    # 祭 front and back: write on a flat (u * circumference, v * height) chart
    Cc, Hh = 2 * math.pi * 1.3, 3.8
    def to_px(x, y): return x / Cc * NU, (Hh - y) / Hh * NV
    tm = text_mask_m(sh, '祭', FONT_J, (0.25 * Cc, Hh * 0.5), 1.8, (0, 1), to_px) + text_mask_m(sh, '祭', FONT_J, (0.75 * Cc, Hh * 0.5), 1.8, (0, 1), to_px)
    col = lerp(col, hx('140c0a'), np.clip(tm, 0, 1) * 0.95)
    emis = col * (1 - 0.85 * np.clip(bandm + tm, 0, 1))[..., None] * (0.85 + 0.15 * fib[..., None])
    return img('lantern_col', np.clip(col, 0, 1)), img('lantern_emis', np.clip(emis * 1.15, 0, 1))
lcol, lemis = lantern_tex()
mPaper, nt, bs = principled('mLanternPaper', lin('d0381e'), 0.0, 0.6, **{'Subsurface Weight': 0.2})
hook_maps(nt, bs, lcol, emis=lemis, estr=3.0)
mRope, nt, bs = principled('mRope', lin('3a2c20'), 0.0, 0.8)
LY = 15.0
def rope_z(x): return 2.4 - 3.0 * (1 - (x / 34.0) ** 2)
LXS = [-21.0, -10.5, 0.0, 10.5, 21.0]
lb, cb_, rb_ = Builder(), Builder(), Builder()
HH, RR_ = 1.9, 1.32
prof = []
for zz in np.linspace(HH, -HH, 49):
    base_r = max(0.66, RR_ * max(0.0, 1 - (zz / HH) ** 2) ** 0.55)
    rib = 1 - 0.022 * (0.5 + 0.5 * math.cos(TAU * zz / 0.19))
    prof.append((base_r * rib, zz))
PV, PF = lathe_template(prof, 24)
# per-loop uv for the paper: u around, v height
def lathe_uv(Vv):
    a = (np.arctan2(Vv[:, 1], Vv[:, 0]) / TAU) % 1.0; return list(zip(a, (Vv[:, 2] + HH) / (2 * HH)))
CV, CF = lathe_template([(0, 0.2), (0.68, 0.2), (0.74, 0.14), (0.74, -0.14), (0.68, -0.2), (0, -0.2)], 24)
LANTERNS = []
for x in LXS:
    zc = rope_z(x) - 0.7 - HH - 0.25
    c = np.array([x, LY, zc], F32)
    I3 = (np.array([1, 0, 0], F32), np.array([0, 1, 0], F32), np.array([0, 0, 1], F32))
    Vp = PV + c; uvp = lathe_uv(PV)
    # fix the u seam per face when building: add faces with per-loop uvs
    n0 = lb.n; lb.V.extend(map(tuple, Vp));
    for f in PF:
        us = [uvp[q] for q in f]
        if max(u for u, _ in us) - min(u for u, _ in us) > 0.5: us = [(u + 1.0 if u < 0.5 else u, v) for u, v in us]
        lb.F.append([q + n0 for q in f]); lb.U.extend(us)
    lb.n += len(Vp)
    for sz in (HH + 0.05, -HH - 0.05): place(cb_, CV, CF, c + np.array([0, 0, sz], F32), *I3)
    Vt, Ft, Ut = tube([(x, LY, rope_z(x)), (x, LY, zc + HH + 0.2)], 0.035, 6); rb_.add(Vt, Ft, Ut)
    LANTERNS.append(c)
lan = lb.build('lantern_paper', mPaper); lan.visible_shadow = False
cb_.build('lantern_caps', mLacq)
rp = catmull([(x, LY, rope_z(x)) for x in np.linspace(-40, 40, 17)], 6)
Vt, Ft, Ut = tube(rp, 0.08, 8); rb_.add(Vt, Ft, Ut)
rb_.build('lantern_rope', mRope)

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
GP = (0.4, 4.68)
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


# ================================================================ lights (warm stage spot in a dark hall), cameras, render
def setup_lights():
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0035, 0.003, 0.0028, 1)
    def L(name, kind, loc, tgt, energy, color, **kw):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); RIG.objects.link(o)
        o.data.energy = energy; o.data.color = color; o.location = loc
        if tgt is not None: o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        for k_, v in kw.items(): setattr(o.data, k_, v)
        return o
    L('Key', 'SPOT', (2.0, -5.0, 27.0), (0, 0.4, -2.0), 2.6e4, (1.0, 0.8, 0.58), spot_size=math.radians(46), spot_blend=0.85, shadow_soft_size=1.8)
    L('Rim', 'AREA', (-6.0, 24.0, 9.0), (0, 0, -3.0), 4.5e3, (0.62, 0.72, 1.0), size=12.0, shape='DISK')
    for c in LANTERNS:
        L('LanternLight', 'POINT', tuple(c), None, 700, (1.0, 0.55, 0.26), shadow_soft_size=0.9)

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
        aim((12.6, -12.1, 3.1), (0, 0.5, -2.1), 32, 8.0, (0, 0, 1.0))
    elif shot == 'drum':
        aim((24, -30, -2), (0, 0, -5.5), 40, 11.0)

def render(shot):
    cam_setup(shot)
    scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'
    scn.cycles.samples = 16 if FAST else 32; scn.cycles.use_denoising = True; scn.cycles.use_adaptive_sampling = True
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
    glb = os.path.join(OUT, 'taiko.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=90)
    log('exported', glb, '%.1f MB' % (os.path.getsize(glb) / 1e6), 'tris', TRIS)
