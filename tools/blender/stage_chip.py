# "POKER CHIP" stage, fully modelled: two sumos fight on top of a giant clay casino chip lying on a green felt poker
# table, shot like a macro tabletop photograph. Built entirely by script (Blender 4.2, run headless).
#   python tools/blender/stage_chip.py [out_dir] [chars_dir] [shot=game shot=low] [samples=48] [pct=100] [noren] [nochars]
# Writes <out_dir>/chip.glb (the stage only: Z up, metres, origin at the chip centre, top of the chip at Z=0, front
# facing -Y) and renders <out_dir>/ex_game.png (game camera) and <out_dir>/ex_low.png (low three-quarter) with the
# game's characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in masks.
# Scale: the hero chip (39 mm real) is 10.6 m across, so the world is ~272x life size; everything on the table keeps
# its real proportions (cards 17 x 24 m, chip stacks 0.85 m per chip, a rocks glass 22 m wide) except the padded rail,
# which is pulled in to ~30 m so it reads in the low view. Layout (camera on -Y): the chip at the origin, a fanned
# A-spade / K-heart on the left, the dealer button front-right, chip stacks back-right and back-left, a whiskey on
# the rocks back-left, the betting line arcing behind the chip, the padded leather rail beyond; a green-shaded lamp
# hangs high overhead; dark casino with out-of-focus lights. CC0 Poly Haven: leather, wood, warm_bar HDRI (reflections
# only) in <scratchpad>/chip_ph.
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in ('noren', 'nochars') and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'chip')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
PH = os.path.join(SP, 'chip_ph')
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SHOTS = set(a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')) or {'game', 'low'}
SAMPLES = int(OPT.get('samples', 48)); PCT = int(OPT.get('pct', 100))
NOREN = 'noren' in sys.argv; NOCHARS = 'nochars' in sys.argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi


def ring_r():
    try:
        txt = open(os.path.join(HERE, '..', '..', 'public', 'js', 'config.js')).read()
        return float(re.search(r'S\.RING_R\s*=\s*([\d.]+)', txt).group(1))
    except Exception:
        return 4.6


R = ring_r()          # fighting circle = the inlaid ring line
RD = R + 0.7          # chip radius
TH = 0.85             # chip thickness (3.3 mm at 272x)
FELT = -TH            # felt surface
INLAY = 3.3           # printed centre label radius
SPOTS = [math.radians(22.5 + 45 * k) for k in range(8)]


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


def planar_uv(me, S, cx=0.0, cy=0.0, mi=None):
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        if mi is not None and p.material_index != mi: continue
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = ((co.x - cx) / (2 * S) + 0.5, (co.y - cy) / (2 * S) + 0.5)
def cyl_uv(me, mi, z0, z1):
    uv = me.uv_layers[0]
    for p in me.polygons:
        if p.material_index != mi: continue
        us = []
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co; us.append(((math.atan2(co.y, co.x) / TAU) % 1.0, (co.z - z0) / (z1 - z0)))
        if max(u for u, _ in us) - min(u for u, _ in us) > 0.5: us = [((u + 1) if u < 0.5 else u, v) for u, v in us]
        for li, uvv in zip(p.loop_indices, us): uv.data[li].uv = uvv
def box_uv(o, tile=6.0, world=True):
    me = o.data; uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    W = o.matrix_world if world else Matrix.Identity(4); R3 = W.to_3x3()
    for p in me.polygons:
        n = R3 @ p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = W @ me.vertices[me.loops[li].vertex_index].co
            u, v = (co.x, co.y) if ax == 2 else (co.y, co.z) if ax == 0 else (co.x, co.z)
            uv.data[li].uv = (u / tile, v / tile)


def lathe_bm(bm, prof, segs, mi=None, cx=0.0, cy=0.0, z0=0.0):
    rings = []
    for (r, z) in prof:
        if r < 1e-6: rings.append([bm.verts.new((cx, cy, z + z0))]); continue
        rings.append([bm.verts.new((cx + r * math.cos(TAU * i / segs), cy + r * math.sin(TAU * i / segs), z + z0)) for i in range(segs)])
    for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
        if len(A) == 1 and len(B) == 1: continue
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1: f = bm.faces.new((A[0], B[i], B[j]))
            elif len(B) == 1: f = bm.faces.new((A[i], B[0], A[j]))
            else: f = bm.faces.new((A[i], B[i], B[j], A[j]))
            if mi: f.material_index = mi[k]
def newfaces(ret): return {f for v in ret['verts'] for f in v.link_faces}
def add_box(bm, c, size, mi=0, M=None):
    Mx = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*size, 1))
    if M is not None: Mx = M @ Mx
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=Mx)
    for f in newfaces(ret): f.material_index = mi
    return ret
def frames(pts, up=Vector((0, 0, 1))):
    P = [Vector(p) for p in pts]; n = len(P); out = []; prevN = None
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        if prevN is None:
            u = up if abs(t.dot(up)) < 0.95 else Vector((1, 0, 0)); Nn = (u - t * u.dot(t)).normalized()
        else: Nn = (prevN - t * prevN.dot(t)).normalized()
        out.append((P[i], t, Nn, t.cross(Nn))); prevN = Nn
    return out
def sweep_profile(bm, pts, prof, mi=None, closed=True):
    """Sweep a 2D profile [(across, up)] along a path (closed loop); profile is open, faces outward."""
    F = frames(pts); rings = []
    for (p, t, nn, b) in F:
        rings.append([bm.verts.new(p + b * a + nn * u) for a, u in prof])
    m = len(rings)
    for k in range(m if closed else m - 1):
        A, B = rings[k], rings[(k + 1) % m]
        for i in range(len(prof) - 1):
            f = bm.faces.new((A[i], A[i + 1], B[i + 1], B[i]))
            if mi: f.material_index = mi[i]
    return rings
def sweep(bm, pts, r, n=8, mi=0, closed=False):
    F = frames(pts); rings = []
    for (p, t, nn, b) in F:
        rings.append([bm.verts.new(p + (nn * math.cos(TAU * i / n) + b * math.sin(TAU * i / n)) * r) for i in range(n)])
    m = len(rings)
    for k in range(m if closed else m - 1):
        A, B = rings[k], rings[(k + 1) % m]
        for i in range(n):
            j = (i + 1) % n; f = bm.faces.new((A[i], A[j], B[j], B[i])); f.material_index = mi


FONT_SB = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf')
FONT_S = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
FONT_B = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
FONT_N = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
_TT = {}
def text_tris(body, font, size, align='CENTER'):
    key = (body, font.name, size, align)
    if key in _TT: return _TT[key].copy()
    cu = bpy.data.curves.new('tt', 'FONT'); cu.body = body; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
    cu.font = font; cu.resolution_u = 5
    tmp = bpy.data.objects.new('tt', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:])
    T = np.array([[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces], np.float32).reshape(-1, 3, 2); bm.free()
    _TT[key] = T; return T.copy()
def xform(T, s=1.0, rot=0.0, tx=0.0, ty=0.0):
    c, sn = math.cos(rot), math.sin(rot); X = T[..., 0] * s; Y = T[..., 1] * s
    out = np.empty_like(T); out[..., 0] = X * c - Y * sn + tx; out[..., 1] = X * sn + Y * c + ty; return out
def raster(T, W, H, x0, x1, y0, y1, ss=3):
    """Coverage (H rows x W cols) of 2D triangles over [x0,x1]x[y0,y1], supersampled."""
    MW, MH = W * ss, H * ss; m = np.zeros((MH, MW), np.float32)
    px = (x1 - x0) / MW; py = (y1 - y0) / MH
    for tri in T:
        (ax, ay), (bx, by), (cx, cy) = tri
        i0 = max(int((min(ax, bx, cx) - x0) / px) - 1, 0); i1 = min(int((max(ax, bx, cx) - x0) / px) + 2, MW)
        j0 = max(int((min(ay, by, cy) - y0) / py) - 1, 0); j1 = min(int((max(ay, by, cy) - y0) / py) + 2, MH)
        if i1 <= i0 or j1 <= j0: continue
        X, Y = np.meshgrid(x0 + (np.arange(i0, i1) + 0.5) * px, y0 + (np.arange(j0, j1) + 0.5) * py)
        d1 = (X - bx) * (ay - by) - (ax - bx) * (Y - by)
        d2 = (X - cx) * (by - cy) - (bx - cx) * (Y - cy)
        d3 = (X - ax) * (cy - ay) - (cx - ax) * (Y - ay)
        neg = (d1 < 0) | (d2 < 0) | (d3 < 0); pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        m[j0:j1, i0:i1] = np.maximum(m[j0:j1, i0:i1], (~(neg & pos)).astype(np.float32))
    return m.reshape(H, ss, W, ss).mean((1, 3))
def poly_tris(pts):
    """Fan/ear triangulation of a simple polygon via bmesh."""
    bm = bmesh.new(); vs = [bm.verts.new((x, y, 0)) for x, y in pts]; f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    T = np.array([[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces], np.float32); bm.free(); return T
def ellipse_pts(cx, cy, rx, ry, n=48, a0=0.0, a1=TAU):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + (0 if a1 - a0 >= TAU - 1e-6 else 1))]
def arc_text(body, font, size, r, centre, top=True, track=0.06):
    """Triangles of text set along a circle: on the top arc reading left-to-right with letters standing outward."""
    glyphs = []
    for ch in body:
        if ch == ' ': glyphs.append((None, size * 0.35)); continue
        T = text_tris(ch, font, size); w = T[..., 0].max() - T[..., 0].min(); glyphs.append((T, w))
    total = sum(w for _, w in glyphs) + track * size * (len(glyphs) - 1)
    out = []; pos = 0.0
    for T, w in glyphs:
        mid = pos + w / 2; pos += w + track * size
        if T is None: continue
        if top:
            a = centre + (total / 2 - mid) / r; out.append(xform(T, 1, a - math.pi / 2, r * math.cos(a), r * math.sin(a)))
        else:
            a = centre - (total / 2 - mid) / r; out.append(xform(T, 1, a + math.pi / 2, r * math.cos(a), r * math.sin(a)))
    return np.concatenate(out)


# ---------------------------------------------------------------- images & materials
def image(name, arr, data=False, alpha=None):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    h, w = arr.shape[:2]; rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    if alpha is not None: rgba[..., 3] = np.clip(alpha, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    if data: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.file_format = 'PNG'; im.pack(); return im
def load_im(path, data=False):
    im = bpy.data.images.load(path)
    if data: im.colorspace_settings.name = 'Non-Color'
    return im
def normal_from_h(h, strength):
    gy, gx = np.gradient(h); n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True); return n * 0.5 + 0.5
def noise(N, px, seed, M=None):
    M = M or N; rng = np.random.default_rng(seed); a = rng.standard_normal((N, M))
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.rfftfreq(M)[None, :]
    k = np.exp(-(fx ** 2 + fy ** 2) * (px ** 2) * 2.0)
    b = np.fft.irfft2(np.fft.rfft2(a) * k, s=(N, M)); return ((b - b.mean()) / (b.std() + 1e-9)).astype(np.float32)
def fbm(N, px, seed, octaves=4, M=None):
    s = np.zeros((N, M or N), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        s += amp * noise(N, px / 2 ** o, seed + o, M); tot += amp; amp *= 0.5
    return s / tot
def blur(a, px):
    N, M = a.shape[:2]; fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.rfftfreq(M)[None, :]
    k = np.exp(-(fx ** 2 + fy ** 2) * (px ** 2) * 2.0 * math.pi ** 2 / 2)
    if a.ndim == 2: return np.fft.irfft2(np.fft.rfft2(a) * k, s=(N, M)).astype(np.float32)
    return np.dstack([np.fft.irfft2(np.fft.rfft2(a[..., c]) * k, s=(N, M)) for c in range(a.shape[2])]).astype(np.float32)
def aniso_noise(N, along, across, ang, seed):
    """Streaky noise: long along direction `ang` (fibres)."""
    rng = np.random.default_rng(seed); a = rng.standard_normal((N, N))
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.fftfreq(N)[None, :]
    ca, sa = math.cos(ang), math.sin(ang); u = fx * ca + fy * sa; v = -fx * sa + fy * ca
    k = np.exp(-(u ** 2) * along ** 2 * 2 - (v ** 2) * across ** 2 * 2)
    b = np.real(np.fft.ifft2(np.fft.fft2(a) * k)); return ((b - b.mean()) / (b.std() + 1e-9)).astype(np.float32)


BSDF = {}
def mat(name, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tcol=None, trough=None, tnrm=None, nstr=1.0, emit=None, estr=0.0,
        coat=0.0, coat_r=0.05, spec=0.5, sheen=0.0, sheen_r=0.5, trans=0.0, ior=1.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']; BSDF[name] = bs
    bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal; bs.inputs['Specular IOR Level'].default_value = spec
    bs.inputs['IOR'].default_value = ior
    if coat: bs.inputs['Coat Weight'].default_value = coat; bs.inputs['Coat Roughness'].default_value = coat_r
    if sheen: bs.inputs['Sheen Weight'].default_value = sheen; bs.inputs['Sheen Roughness'].default_value = sheen_r
    if trans: bs.inputs['Transmission Weight'].default_value = trans
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


# ================================================================ textures
def tex_chip_top(n, body, spot, accent, ink, value, seed, hero=False):
    """Top face of a clay chip (planar UV over [-RD, RD]): clay body with mottling and flecks, 8 edge spots with
    accent hash inserts, the inlaid ring line at R, an embossed suit ring (normal only), the laminated centre inlay
    printed with KUMITE / value / suits, grime and scuffs. Returns colour (sRGB), roughness, normal."""
    S = RD; xs = (np.arange(n) + 0.5) / n * 2 * S - S
    X, Y = np.meshgrid(xs, xs); r = np.hypot(X, Y); th = np.arctan2(Y, X); pw = 2 * S / n; aa = pw * 0.75
    rng = np.random.default_rng(seed)
    BODY, SPOT, ACC, INK = srgb(body), srgb(spot), srgb(accent), srgb(ink)
    # clay: soft mottling + fine grain + a few flecks
    mott = fbm(n, n / 40, seed + 1); grain = noise(n, 1.0, seed + 2)
    clay = BODY * (1 + 0.05 * mott + 0.025 * grain)[..., None]
    fl = (np.random.default_rng(seed + 3).random((n, n)) < 0.0015).astype(np.float32); fl = blur(fl, 0.6) * 4
    clay = clay * (1 - 0.35 * np.clip(fl, 0, 1))[..., None] + SPOT * 0.3 * np.clip(fl, 0, 1)[..., None]
    col = clay.copy()
    # spots (rectangular inserts reaching the rim) + accent hashes between them
    spot_m = np.zeros_like(r); hash_m = np.zeros_like(r)
    for a in SPOTS:
        d = th - a; along = r * np.cos(d); perp = np.abs(r * np.sin(d))
        spot_m = np.maximum(spot_m, sstep(4.74 - aa, 4.74 + aa, along) * (1 - sstep(0.62 - aa, 0.62 + aa, perp)))
        d2 = th - (a + math.pi / 8); along2 = r * np.cos(d2); perp2 = r * np.sin(d2)
        for off in (-0.2, 0.2):
            hash_m = np.maximum(hash_m, sstep(4.86 - aa, 4.86 + aa, along2) * (1 - sstep(0.055 - aa, 0.055 + aa, np.abs(perp2 - off))))
    ring = 1 - sstep(0.045 - aa, 0.045 + aa, np.abs(r - R))
    col = col * (1 - spot_m[..., None]) + SPOT * (1 + 0.03 * mott)[..., None] * spot_m[..., None]
    col = col * (1 - hash_m[..., None]) + ACC * hash_m[..., None]
    col = col * (1 - ring[..., None]) + SPOT * ring[..., None]
    # embossed mould: thin grooves at 3.42 / 4.5 and a ring of 12 suits at r=3.96 (same colour, relief only)
    groove = (1 - sstep(0.012, 0.03, np.abs(r - 3.45))) + (1 - sstep(0.012, 0.03, np.abs(r - 4.48)))
    suits = '♠♥♦♣'
    Ts = [xform(text_tris(suits[k % 4], FONT_N, 0.52), 1, a - math.pi / 2, 3.96 * math.cos(a), 3.96 * math.sin(a))
          for k, a in enumerate(np.linspace(0, TAU, 12, endpoint=False) + math.pi / 12)]
    emb = raster(np.concatenate(Ts), n, n, -S, S, -S, S, ss=2)
    # centre inlay
    inl = 1 - sstep(INLAY - aa, INLAY + aa, r)
    LAB = srgb('f1ebdc') * (1 + 0.015 * grain)[..., None]
    lab = np.broadcast_to(LAB, (n, n, 3)).copy()
    def paint(mask, c):
        nonlocal lab
        lab = lab * (1 - mask[..., None]) + np.asarray(c) * mask[..., None]
    paint((1 - sstep(INLAY - 0.22 - aa, INLAY - 0.22 + aa, r)) * sstep(INLAY - 0.34 - aa, INLAY - 0.34 + aa, r), BODY)
    paint(1 - sstep(0.012, 0.012 + aa, np.abs(r - (INLAY - 0.46))), srgb('b8913c'))
    paint((1 - sstep(0.012, 0.012 + aa, np.abs(r - 1.95))) * (np.abs(Y) > 0.95), srgb('b8913c'))
    kum = raster(arc_text('KUMITE', FONT_SB, 0.62, 2.28, math.pi / 2, True, 0.12), n, n, -S, S, -S, S)
    paint(kum, INK)
    low = raster(arc_text('HIGH  STAKES', FONT_S, 0.34, 2.42, -math.pi / 2, False, 0.15), n, n, -S, S, -S, S)
    paint(low, INK * 0.6 + LAB.mean((0, 1)) * 0.4)
    val = raster(xform(text_tris(value, FONT_SB, 1.15 if len(value) > 3 else 1.4), 1, 0, 0, 0.1), n, n, -S, S, -S, S)
    paint(val, BODY * 0.85)
    for k, (sch, red) in enumerate((('♠', False), ('♥', True), ('♦', True), ('♣', False))):
        m_ = raster(xform(text_tris(sch, FONT_N, 0.5), 1, 0, -0.84 + 0.56 * k, -1.18), n, n, -S, S, -S, S)
        paint(m_, srgb('b81c22') if red else srgb('151515'))
    for sx in (-1, 1):   # little star ornaments either side of the value
        m_ = raster(xform(text_tris('★', FONT_N, 0.34), 1, 0, sx * 1.9, 0.1), n, n, -S, S, -S, S)
        paint(m_, srgb('b8913c'))
    col = col * (1 - inl[..., None]) + lab * inl[..., None]
    # wear: grime in the grooves / round the inlay edge / rim, scuffs, faint fingerprints of use
    h = groove * -0.6 + emb * 0.8 + inl * -0.5
    hb = blur(h, 2.5); cav = np.clip(hb - h, 0, 1)
    col *= (1 - 0.25 * cav)[..., None]
    rim = sstep(5.0, 5.3, r)
    scuffs = np.clip(sum(aniso_noise(n, 30, 0.8, rng.uniform(0, math.pi), seed + 10 + k) for k in range(3)) / 3, 0, None)
    sc_m = sstep(1.4, 2.6, scuffs) * (0.3 + 0.7 * rim)
    col = col * (1 - 0.18 * sc_m[..., None]) + 0.06 * sc_m[..., None]
    dirt = sstep(0.4, 1.6, fbm(n, n / 25, seed + 20)) * (0.4 + 0.6 * rim)
    col *= (1 - 0.12 * dirt)[..., None]
    rough = 0.52 + 0.06 * mott + 0.08 * dirt - 0.05 * spot_m
    rough = rough * (1 - inl) + (0.2 + 0.18 * sc_m + 0.04 * noise(n, 6, seed + 30)) * inl
    hh = h * 0.25 + 0.012 * grain + 0.05 * sc_m
    nrm = normal_from_h(blur(hh, 0.8), 3.0)
    return np.clip(col, 0, 1), np.clip(rough, 0.05, 1), nrm


def tex_chip_side(W, H, body, spot, accent, seed):
    """Edge band of a chip (u = angle / 2pi from +X, v = bottom -> top): the spot inserts run over the full height."""
    u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H; U, V = np.meshgrid(u, v)
    circ = TAU * RD; BODY, SPOT, ACC = srgb(body), srgb(spot), srgb(accent)
    col = np.broadcast_to(BODY, (H, W, 3)).copy() * (1 + 0.04 * noise(H, 3, seed, W))[..., None]
    for a in SPOTS:
        d = ((U - a / TAU + 0.5) % 1.0 - 0.5) * circ
        m = 1 - sstep(0.60, 0.65, np.abs(d)); col = col * (1 - m[..., None]) + SPOT * m[..., None]
        d2 = ((U - (a + math.pi / 8) / TAU + 0.5) % 1.0 - 0.5) * circ
        for off in (-0.2, 0.2):
            m2 = 1 - sstep(0.04, 0.07, np.abs(d2 - off)); col = col * (1 - m2[..., None]) + ACC * m2[..., None]
    # wear on the edge: scuffed and grimy toward the rims, horizontal rub marks
    rub = sstep(1.0, 2.5, np.abs(aniso_noise(max(W, H), 40, 0.6, 0.0, seed + 5)[:H, :W]))
    edge = np.maximum(1 - sstep(0.0, 0.25, V), sstep(0.75, 1.0, V))
    col = col * (1 - 0.15 * edge[..., None]) * (1 - 0.15 * rub[..., None]) + 0.04 * rub[..., None]
    rough = 0.55 + 0.1 * edge - 0.08 * rub
    hgt = 0.3 * rub + 0.04 * noise(H, 1.5, seed + 6, W)
    return np.clip(col, 0, 1), np.clip(rough, 0, 1), normal_from_h(hgt, 1.5)


def tex_felt(n=1024):
    """Poker 'speed cloth': fine plain weave (tile 6 m = ~22 mm real), fuzzy fibres, colour drift."""
    xs = np.arange(n); X, Y = np.meshgrid(xs, xs); p = 16.0
    wx = np.sin(X / p * math.pi) ** 2; wy = np.sin(Y / p * math.pi) ** 2
    over = ((np.floor(X / p) + np.floor(Y / p)) % 2).astype(np.float32)
    weave = over * wx * 0.6 + (1 - over) * wy * 0.6 + 0.4 * (wx * wy)
    fib = np.zeros((n, n), np.float32)
    rng = np.random.default_rng(4)
    for k in range(5): fib += np.clip(aniso_noise(n, 9, 0.7, rng.uniform(0, math.pi), 40 + k), 0, None) ** 2
    fib = fib / fib.max()
    drift = fbm(n, 90, 5)
    base = srgb('1c5c34')
    col = base * (0.9 + 0.06 * drift + 0.12 * weave - 0.08)[..., None] + np.array([0.04, 0.10, 0.06]) * fib[..., None]
    rough = 0.9 - 0.05 * fib
    h = weave * 0.5 + fib * 0.6 + 0.15 * noise(n, 1.2, 7)
    return np.clip(col, 0, 1), np.clip(rough, 0, 1), normal_from_h(h, 2.0)


def tex_card(rank, suit, red, W=736, H=1024):
    """A playing card face (63 x 88 mm), pixel coordinates (y up)."""
    rng = np.random.default_rng(hash((rank, suit)) % 1000)
    paper = srgb('f6f3ea') * (1 + 0.012 * noise(H, 1.5, 3, W) + 0.02 * noise(H, 40, 4, W))[..., None]
    col = paper.copy(); INK = srgb('b5121b') if red else srgb('121212')
    def paint(mask, c):
        nonlocal col
        col = col * (1 - mask[..., None]) + np.asarray(c) * mask[..., None]
    def glyph(ch, font, size, x, y, rot=0.0):
        return raster(xform(text_tris(ch, font, size), 1, rot, x, y), W, H, 0, W, 0, H, ss=2)
    # corner indices, top-left and bottom-right (rotated)
    for (x, y, rot) in ((70, H - 92, 0.0), (W - 70, 92, math.pi)):
        dy = -1 if rot == 0 else 1
        paint(glyph(rank, FONT_SB, 120, x, y, rot), INK)
        paint(glyph(suit, FONT_N, 92, x, y + dy * 115, rot), INK)
    if rank == 'A':
        big = 700 if suit == '♠' else 480
        paint(glyph(suit, FONT_N, big, W / 2, H / 2 + (10 if suit == '♠' else 0)), INK)
        if suit == '♠':   # the ornamental ace of spades: a fine frame ring and a scroll under the pip
            yy, xx = np.mgrid[0:H, 0:W]; rr = np.hypot(xx - W / 2, (yy - H / 2) * 1.0)
            paint(1 - sstep(2.0, 3.5, np.abs(rr - 300)), INK)
            paint(glyph('KUMITE', FONT_SB, 34, W / 2, H / 2 - 230), INK)
    else:   # court card: framed, two mirrored halves of a stylised king
        x0, x1, y0, y1 = 120, W - 120, 120, H - 120
        yy, xx = np.mgrid[0:H, 0:W]
        frame = ((xx > x0) & (xx < x1) & (yy > y0) & (yy < y1)).astype(np.float32)
        paint(frame, srgb('fbf7ee'))
        inner = ((xx > x0 + 4) & (xx < x1 - 4) & (yy > y0 + 4) & (yy < y1 - 4)).astype(np.float32)
        paint(frame - inner, srgb('2a3d8f'))
        Hc = H / 2; cx = W / 2
        GOLD, RED, BLUE, SKIN, BLK = srgb('e0b33a'), srgb('c4222a'), srgb('2a3d8f'), srgb('f2d3b0'), srgb('151515')
        def half(flip):
            def P(pts): return [((cx + (x - cx) * (-1 if flip else 1)), (Hc + (y - Hc) * (-1 if flip else 1))) for x, y in pts]
            def fill(pts, c, outline=True):
                T = poly_tris(P(pts)); m = raster(T, W, H, 0, W, 0, H, ss=2)
                if outline:
                    paint(np.clip(blur(m, 1.6) * 1.0 - m * 0.0, 0, 1) * (1 - m) * 1.6, BLK)
                paint(m, c)
            # robe / shoulders
            fill([(x0 + 6, Hc + 2), (x1 - 6, Hc + 2), (x1 - 6, Hc + 150), (cx + 120, Hc + 215), (cx - 120, Hc + 215), (x0 + 6, Hc + 150)], RED)
            fill([(cx - 60, Hc + 2), (cx + 60, Hc + 2), (cx + 46, Hc + 205), (cx - 46, Hc + 205)], GOLD)
            for k in range(5):
                fill(ellipse_pts(cx, Hc + 30 + k * 36, 10, 10, 12), BLUE, False)
            fill([(x0 + 6, Hc + 2), (cx - 150, Hc + 2), (cx - 150, Hc + 120), (x0 + 6, Hc + 150)], BLUE)
            fill([(x1 - 6, Hc + 2), (cx + 150, Hc + 2), (cx + 150, Hc + 120), (x1 - 6, Hc + 150)], BLUE)
            # collar, head, beard, crown
            fill([(cx - 125, Hc + 205), (cx + 125, Hc + 205), (cx + 95, Hc + 240), (cx - 95, Hc + 240)], GOLD)
            fill(ellipse_pts(cx, Hc + 300, 68, 82), SKIN)
            fill([(cx - 66, Hc + 300), (cx + 66, Hc + 300), (cx + 52, Hc + 232), (cx, Hc + 212), (cx - 52, Hc + 232)], srgb('8a5a2a'))
            fill([(cx - 30, Hc + 268), (cx + 30, Hc + 268), (cx + 22, Hc + 258), (cx - 22, Hc + 258)], srgb('6a3a1a'), False)
            for sx in (-1, 1): fill(ellipse_pts(cx + sx * 25, Hc + 318, 8, 5, 10), BLK, False)
            crown = [(cx - 78, Hc + 360), (cx + 78, Hc + 360), (cx + 84, Hc + 430), (cx + 52, Hc + 398), (cx + 26, Hc + 440),
                     (cx, Hc + 402), (cx - 26, Hc + 440), (cx - 52, Hc + 398), (cx - 84, Hc + 430)]
            fill(crown, GOLD)
            fill([(cx - 78, Hc + 360), (cx + 78, Hc + 360), (cx + 78, Hc + 376), (cx - 78, Hc + 376)], RED, False)
            # sword behind the head (the "suicide king")
            fill([(cx + 96, Hc + 230), (cx + 108, Hc + 236), (cx + 70, Hc + 450), (cx + 60, Hc + 446)], srgb('c8ccd2'))
            # suit pip in the corner of the frame
            paint(glyph(suit, FONT_N, 80, x0 + 50 if not flip else x1 - 50, Hc + 380 if not flip else Hc - 380, math.pi if flip else 0), INK)
        half(False); half(True)
        paint((1 - sstep(1.0, 2.5, np.abs(yy - Hc))) * inner, srgb('2a3d8f'))
    # card edge: rounded-corner border shadow line (very faint)
    return np.clip(col, 0, 1)


def tex_button(n=512):
    S = 6.0; xs = (np.arange(n) + 0.5) / n * 2 * S - S; X, Y = np.meshgrid(xs, xs); r = np.hypot(X, Y)
    col = np.broadcast_to(srgb('f4f1e8'), (n, n, 3)).copy() * (1 + 0.01 * noise(n, 2, 8))[..., None]
    def paint(mask, c):
        nonlocal col
        col = col * (1 - mask[..., None]) + np.asarray(c) * mask[..., None]
    paint(1 - sstep(0.06, 0.09, np.abs(r - 5.3)), srgb('141414'))
    paint(1 - sstep(0.02, 0.04, np.abs(r - 5.05)), srgb('141414'))
    paint(raster(arc_text('DEALER', FONT_SB, 1.35, 3.0, math.pi / 2, True, 0.1), n, n, -S, S, -S, S), srgb('141414'))
    paint(raster(arc_text('DEALER', FONT_SB, 1.35, 3.0, -math.pi / 2, False, 0.1), n, n, -S, S, -S, S), srgb('141414'))
    paint(raster(xform(text_tris('♠', FONT_N, 1.6), 1, 0, 0, 0), n, n, -S, S, -S, S), srgb('141414'))
    sc = sstep(1.6, 2.6, np.abs(aniso_noise(n, 20, 0.7, 0.4, 9)))
    col *= (1 - 0.06 * sc)[..., None]
    rough = 0.18 + 0.15 * sc
    return np.clip(col, 0, 1), rough


# ================================================================ materials
print('textures...')
CHIPS = {   # name: body, spot, accent, ink, value
    'red': ('b3171f', 'f2ebdc', '1f4fa8', '8e1218', '1000'),
    'black': ('17171a', 'efe9dc', 'c8262a', '17171a', '100'),
    'green': ('1d6b3c', 'f2ebdc', 'e0b33a', '134a29', '25'),
    'blue': ('1c3f8c', 'f2ebdc', 'e0b33a', '15306b', '50'),
    'purple': ('5a2a7a', 'f0e6c8', 'e0b33a', '441d5e', '500'),
}
CHIP_MATS = {}
for k, (b, s_, a_, i_, v_) in CHIPS.items():
    hero = k == 'red'; n = 1024 if hero else 512
    c, r_, nn = tex_chip_top(n, b, s_, a_, i_, v_, 11 + len(k), hero)
    cs, rs, ns = tex_chip_side(1024 if hero else 512, 64 if hero else 32, b, s_, a_, 3 + len(k))
    CHIP_MATS[k] = (mat('ChipTop_' + k, tcol=image('chip_%s_col' % k, c), trough=image('chip_%s_r' % k, np.dstack([r_] * 3), True),
                        tnrm=image('chip_%s_n' % k, nn, True), nstr=1.0, sheen=0.15, sheen_r=0.4),
                    mat('ChipEdge_' + k, tcol=image('chipe_%s_col' % k, cs), trough=image('chipe_%s_r' % k, np.dstack([rs] * 3), True),
                        tnrm=image('chipe_%s_n' % k, ns, True), sheen=0.15, sheen_r=0.4))
fc, fr, fn = tex_felt()
M_FELT = mat('Felt', tcol=image('felt_col', fc), trough=image('felt_r', np.dstack([fr] * 3), True), tnrm=image('felt_n', fn, True),
             nstr=1.0, sheen=1.0, sheen_r=0.35, spec=0.3)
M_LINE = mat('FeltPrint', lin('e3cf8e'), 0.85, tnrm=M_FELT.node_tree.nodes['Normal Map'].inputs['Color'].links[0].from_node.image, sheen=0.6, spec=0.3)
M_LEATHER = mat('Leather', tcol=load_im(os.path.join(PH, 'fabric_leather_02_Diffuse.jpg')),
                trough=load_im(os.path.join(PH, 'fabric_leather_02_Rough.jpg'), True),
                tnrm=load_im(os.path.join(PH, 'fabric_leather_02_nor_gl.jpg'), True), nstr=1.2, coat=0.15, coat_r=0.3)
M_PIPING = mat('Piping', lin('120c0a'), 0.4, coat=0.3, coat_r=0.2)
M_WOOD = mat('RailWood', tcol=load_im(os.path.join(PH, 'wood_table_001_Diffuse.jpg')),
             trough=load_im(os.path.join(PH, 'wood_table_001_Rough.jpg'), True),
             tnrm=load_im(os.path.join(PH, 'wood_table_001_nor_gl.jpg'), True), coat=1.0, coat_r=0.04)
CARD_MATS = {}
for rk, su, red in (('A', '♠', False), ('K', '♥', True), ('A', '♥', True)):
    CARD_MATS[rk + su] = mat('Card_' + rk + ('S' if su == '♠' else 'H'), tcol=image('card_%s%s' % (rk, 'S' if su == '♠' else 'H'), tex_card(rk, su, red)),
                             rough=0.32, coat=0.4, coat_r=0.12)
M_CARDEDGE = mat('CardEdge', lin('ece8de'), 0.6)
M_CARDBACK = mat('CardBack', lin('8e1a22'), 0.35, coat=0.4, coat_r=0.12)
bc, br_ = tex_button()
M_BUTTON = mat('DealerButton', tcol=image('button_col', bc), trough=image('button_r', np.dstack([br_] * 3), True), coat=0.5, coat_r=0.05)
M_BUTTONSIDE = mat('ButtonSide', lin('ece8de'), 0.25, coat=0.5, coat_r=0.05)
M_GLASS = mat('Glass', lin('ffffff'), 0.02, trans=1.0, ior=1.5, spec=0.5)
M_WHISKY = mat('Whisky', lin('c06a1a'), 0.02, trans=1.0, ior=1.33)
M_ICE = mat('Ice', lin('f4f8fb'), 0.12, trans=1.0, ior=1.31)
M_SHADE = mat('LampShadeGreen', lin('0f4a2a'), 0.12, coat=1.0, coat_r=0.03)
M_SHADEIN = mat('LampShadeInside', lin('f4efe2'), 0.5, emit=lin('ffd9a0'), estr=2.0)
M_BRASS = mat('Brass', lin('b8893a'), 0.28, 1.0)
M_BULB = mat('Bulb', lin('fff2d8'), 0.2, emit=lin('ffdcae'), estr=60)


# ================================================================ the hero chip
print('modelling...')
def chip_profile(rd=RD, th=TH, rr=0.11, inlay=INLAY, recess=0.015):
    p = [(0, -recess), (inlay - 0.05, -recess), (inlay, 0.0), (R - 0.3, 0), (rd - rr, 0)]
    for k in range(1, 5):
        a = math.pi / 2 * k / 4; p.append((rd - rr + rr * math.sin(a), -rr + rr * math.cos(a)))
    p += [(rd, -th + rr)]
    for k in range(1, 5):
        a = math.pi / 2 * k / 4; p.append((rd - rr + rr * math.cos(a), -th + rr - rr * math.sin(a)))
    p += [(rd * 0.8, -th), (0, -th)]
    return p
def build_chip(name, kind, loc=(0, 0, 0), rotz=0.0, segs=192, hero=False, tilt=None):
    prof = chip_profile() if hero else chip_profile(recess=0.0)
    top_n = 4 + 4      # segments on the top face incl. the upper round
    nseg = len(prof) - 1
    mi = [0] * (top_n - (0 if hero else 0)) + [1] * (nseg - top_n)
    bm = bmesh.new(); lathe_bm(bm, prof, segs, mi)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(50))
    planar_uv(me, RD)
    cyl_uv(me, 1, -TH, 0.0)
    o = obj(name, me, list(CHIP_MATS[kind]), loc=loc, rot=(0, 0, rotz))
    if tilt: o.rotation_euler = tilt
    return o


hero = build_chip('HeroChip', 'red', hero=True, segs=192)

# ================================================================ the table: felt, printed line, rail
bm = bmesh.new(); add_box(bm, (0, 0, FELT - 1.0), (420, 420, 2.0), 0)
felt = bm_obj('Felt', bm, [M_FELT], smooth=0); box_uv(felt, 6.0)
# printed betting line: an arc behind the chip, curving away at the sides
LC, LR = Vector((0, -32.0)), 42.5
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
segs = 160; a0, a1 = math.radians(20), math.radians(160)
rows = []
for i in range(segs + 1):
    a = a0 + (a1 - a0) * i / segs
    rows.append([bm.verts.new((LC.x + math.cos(a) * rr, LC.y + math.sin(a) * rr, FELT + 0.004)) for rr in (LR - 0.16, LR + 0.16)])
for i in range(segs):
    f = bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
    for l in f.loops: l[uvl].uv = (l.vert.co.x / 6.0, l.vert.co.y / 6.0)
line = bm_obj('BettingLine', bm, [M_LINE], smooth=0)
# padded leather rail on a varnished wooden racetrack, round the table edge
RC, RR_ = Vector((0, -18.0)), 50.0
bm = bmesh.new()
rail_pts = [(RC.x + math.cos(TAU * i / 160) * RR_, RC.y + math.sin(TAU * i / 160) * RR_, FELT) for i in range(160)]
# profile in (across = outward, up): racetrack wood, then the padded armrest
wood = [(-6.0, 0.0), (-6.0, 0.12), (-5.8, 0.25), (-1.4, 0.25), (-1.2, 0.2), (-1.2, 0.05)]
pad_ = [(-1.2, 0.05)]
for k in range(17):
    a = math.pi * k / 16          # rounded bolster: from the inner foot over the top to the outside
    pad_.append((-1.2 + 6.0 * (1 - math.cos(a)) / 2 + 0.6 * math.sin(a) * (k < 8), 0.05 + 3.4 * math.sin(a) ** 0.8))
pad_ += [(4.8, -1.5)]
F = frames(rail_pts)
def ring_verts(prof):
    out = []
    for (p, t, nn, b) in F:
        out.append([bm.verts.new(p - b * a + nn * u) for a, u in prof])
    return out
def bridge(rings, mi):
    m = len(rings)
    for k in range(m):
        A, B = rings[k], rings[(k + 1) % m]
        for i in range(len(A) - 1):
            f = bm.faces.new((A[i], B[i], B[i + 1], A[i + 1])); f.material_index = mi
bridge(ring_verts(wood), 0); bridge(ring_verts(pad_), 1)
rail = bm_obj('Rail', bm, [M_WOOD, M_LEATHER], smooth=45)
bmesh.ops.recalc_face_normals if False else None
me = rail.data; me.flip_normals() if False else None
box_uv(rail, 5.0)
# a piping seam along the top of the armrest
bm = bmesh.new()
for (p, t, nn, b) in [F[i] for i in range(len(F))]:
    pass
seam_pts = [p - b * (-1.2 + 0.4) + nn * 2.7 for (p, t, nn, b) in F]
sweep(bm, seam_pts, 0.12, 6, 0, closed=True)
seam2 = [p - b * 1.8 + nn * 3.38 for (p, t, nn, b) in F]
sweep(bm, seam2, 0.1, 6, 0, closed=True)
piping = bm_obj('RailPiping', bm, [M_PIPING], smooth=40)


# ================================================================ cards
def card(name, key, cx, cy, rotz, z=FELT, tilt=0.0):
    W, H, rc, t = 17.1, 23.9, 0.9, 0.08
    pts = []
    for (qx, qy, a0) in ((W / 2 - rc, -H / 2 + rc, -90), (W / 2 - rc, H / 2 - rc, 0), (-W / 2 + rc, H / 2 - rc, 90), (-W / 2 + rc, -H / 2 + rc, 180)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6); pts.append((qx + rc * math.cos(a), qy + rc * math.sin(a)))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    T = [bm.verts.new((x, y, t)) for x, y in pts]; B = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    ft = bm.faces.new(T); ft.material_index = 0
    fb = bm.faces.new(B[::-1]); fb.material_index = 2
    for i in range(len(pts)):
        j = (i + 1) % len(pts); f = bm.faces.new((B[i], B[j], T[j], T[i])); f.material_index = 1
    for f in bm.faces:
        for l in f.loops: l[uvl].uv = (l.vert.co.x / W + 0.5, l.vert.co.y / H + 0.5)
    o = bm_obj(name, bm, [CARD_MATS[key], M_CARDEDGE, M_CARDBACK], smooth=0)
    o.location = (cx, cy, z); o.rotation_euler = (0, tilt, rotz)
    return o


card('CardAceSpades', 'A♠', -21.5, 8.0, math.radians(194))
card('CardKingHearts', 'K♥', -17.2, 3.0, math.radians(171), z=FELT + 0.02, tilt=math.radians(0.4))
card('CardAceHearts', 'A♥', 7.0, 19.5, math.radians(62))

# ================================================================ chip stacks, a stray chip, the dealer button
STACK_SEGS = 64
rng = np.random.default_rng(9)
stack_meshes = {}
def stack(kind, cx, cy, n, lean=0.0):
    if kind not in stack_meshes:
        o = build_chip('Chip_' + kind, kind, segs=STACK_SEGS); stack_meshes[kind] = o.data; STAGE.remove(o); bpy.data.objects.remove(o)
    for i in range(n):
        o = obj('Stack_%s' % kind, stack_meshes[kind], (), loc=(cx + rng.normal(0, 0.06) + lean * i, cy + rng.normal(0, 0.06), FELT + TH * (i + 1)),
                rot=(0, 0, rng.uniform(0, TAU)))
stack('black', 14.5, 12.5, 8)
stack('green', 21.5, 6.0, 5)
stack('purple', 9.0, 22.0, 10)
stack('red', 21.0, 17.5, 3)
stack('blue', -12.5, 15.5, 6, lean=0.02)
stack('black', -19.0, 22.0, 4)
o = obj('StrayChip', stack_meshes['green'], (), loc=(-5.8, 15.5, FELT + TH + 0.0), rot=(0, 0, 0.7))
# dealer button front-right
bm = bmesh.new()
prof = [(0, 0)]
BR_, BH = 6.0, 2.2
for k in range(5):
    a = math.pi / 2 * k / 4; prof.append((BR_ - 0.3 + 0.3 * math.sin(a), -0.3 + 0.3 * math.cos(a)))
prof += [(BR_, -BH + 0.3)]
for k in range(1, 5):
    a = math.pi / 2 * k / 4; prof.append((BR_ - 0.3 + 0.3 * math.cos(a), -BH + 0.3 - 0.3 * math.sin(a)))
prof += [(0, -BH)]
lathe_bm(bm, prof, 128, [0] * 5 + [1] * (len(prof) - 6))
me = bpy.data.meshes.new('DealerButton'); bm.to_mesh(me); bm.free(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(50))
planar_uv(me, BR_)
button = obj('DealerButton', me, [M_BUTTON, M_BUTTONSIDE], loc=(17.0, -6.5, FELT + BH), rot=(0, 0, math.radians(-18)))

# ================================================================ whiskey on the rocks (back-left)
GX_, GY_ = -26.0, 33.0; GR, GH, GW, GB = 11.0, 24.0, 0.8, 3.2
bm = bmesh.new()
gprof = [(GR - GW, GB + 0.8), (GR - GW - 0.05, GH - 0.15), (GR - GW + 0.1, GH), (GR - 0.1, GH), (GR, GH - 0.2), (GR, 0.4), (GR - 0.4, 0.0),
         (GR - 1.6, 0.0), (GR - 1.8, 0.25), (0, 0.6)]
# inner bottom (thick base) back to the start: written as a closed lathe from the inside of the base
gprof = [(0, GB), (GR - GW - 0.8, GB)] + gprof
lathe_bm(bm, gprof, 96)
me = bpy.data.meshes.new('Glass'); bm.to_mesh(me); bm.free(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(60))
glass = obj('Glass', me, [M_GLASS], loc=(GX_, GY_, FELT))
for p in me.polygons: p.use_smooth = True
bm = bmesh.new(); LV = 9.5
lathe_bm(bm, [(0, LV - 0.05), (GR - GW - 0.6, LV), (GR - GW - 0.02, LV + 0.25), (GR - GW - 0.02, GB + 0.8), (GR - GW - 0.8, GB + 0.01), (0, GB + 0.01)], 96)
me = bpy.data.meshes.new('Whisky'); bm.to_mesh(me); bm.free(); me.shade_smooth()
whisky = obj('Whisky', me, [M_WHISKY], loc=(GX_, GY_, FELT))
ice_objs = []
for (dx, dy, z, s_, rx, ry, rz) in ((-2.5, 1.5, 9.0, 6.0, 0.3, 0.15, 0.4), (3.0, -1.0, 8.2, 5.4, -0.2, 0.35, 1.1), (0.5, 3.8, 12.0, 4.8, 0.6, -0.3, 2.0)):
    bpy.ops.mesh.primitive_cube_add(size=s_, location=(GX_ + dx, GY_ + dy, FELT + z)); c = bpy.context.object
    bv = c.modifiers.new('b', 'BEVEL'); bv.width = s_ * 0.12; bv.segments = 3
    c.rotation_euler = (rx, ry, rz)
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(c.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(c)
    bm = bmesh.new(); bm.from_mesh(me)
    for v in bm.verts: v.co += Vector(np.random.default_rng(len(ice_objs)).normal(0, 0.06, 3).tolist())
    bm.to_mesh(me); bm.free(); me.shade_smooth()
    ice_objs.append(obj('Ice', me, [M_ICE], loc=(GX_ + dx, GY_ + dy, FELT + z), rot=(rx, ry, rz)))

# ================================================================ the green-shaded lamp overhead (out of frame, lights the table)
LX, LY, LZ = 0.0, 8.0, 80.0
bm = bmesh.new()
sh = [(1.2, 14.0), (4.0, 13.6), (9.0, 10.5), (15.0, 4.5), (18.5, 0.6), (19.0, 0.0)]
sh_in = [(18.6, 0.0), (18.1, 0.6), (14.6, 4.3), (8.7, 10.1), (3.8, 13.2), (1.2, 13.6)]
lathe_bm(bm, sh, 64, [0] * (len(sh) - 1))
lathe_bm(bm, sh_in, 64, [1] * (len(sh_in) - 1))
me = bpy.data.meshes.new('LampShade'); bm.to_mesh(me); bm.free(); me.shade_smooth()
lamp = obj('LampShade', me, [M_SHADE, M_SHADEIN], loc=(LX, LY, LZ))
bm = bmesh.new(); sweep(bm, [(0, 0, 13.8), (0, 0, 120)], 0.5, 12, 0)
lathe_bm(bm, [(0, 9.0), (2.0, 8.6), (2.6, 6.0), (1.8, 4.2), (0, 3.6)], 24, [1] * 4)
me = bpy.data.meshes.new('LampRod'); bm.to_mesh(me); bm.free(); me.shade_smooth()
obj('LampRod', me, [M_BRASS, M_BULB], loc=(LX, LY, LZ))

# ================================================================ export the stage
total = sum(tris(o) for o in STAGE)
print('TOTAL triangles:', total, ' objects:', len(STAGE))
print('heaviest', sorted(((tris(o), o.name) for o in STAGE), reverse=True)[:10])
bpy.ops.object.select_all(action='DESELECT')
for o in STAGE: o.select_set(True)
GLB = os.path.join(OUT, 'chip.glb')
bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='JPEG', export_jpeg_quality=90)
print('exported', GLB, os.path.getsize(GLB) // 1024, 'KB')
if NOREN: sys.exit(0)


# ================================================================ render-only: world, lights, bokeh
nt = M_WHISKY.node_tree
va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (*lin('c8781e'), 1); va.inputs['Density'].default_value = 0.12
nt.links.new(va.outputs[0], nt.nodes['Material Output'].inputs['Volume'])

world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world; nt = world.node_tree
bg = nt.nodes['Background']
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(PH, 'warm_bar.hdr'))
lp = nt.nodes.new('ShaderNodeLightPath')
mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
mx.inputs['A'].default_value = (0.0, 0.0, 0.0, 1)
mxv = nt.nodes.new('ShaderNodeMath'); mxv.operation = 'MAXIMUM'
nt.links.new(lp.outputs['Is Glossy Ray'], mxv.inputs[0]); nt.links.new(lp.outputs['Is Transmission Ray'], mxv.inputs[1])
nt.links.new(mxv.outputs[0], mx.inputs['Factor']); nt.links.new(env.outputs['Color'], mx.inputs['B'])
nt.links.new(mx.outputs['Result'], bg.inputs['Color']); bg.inputs['Strength'].default_value = float(OPT.get('refl', 0.25))


def light(name, kind, loc, look, energy, color, size=None, spot=None, blend=0.5, soft=0.5, glossy=True):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(L)
    L.location = loc; L.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    L.data.energy = energy; L.data.color = color
    if kind == 'AREA': L.data.shape = 'DISK'; L.data.size = size
    if kind == 'SPOT': L.data.spot_size = math.radians(spot); L.data.spot_blend = blend
    if kind in ('SPOT', 'POINT'): L.data.shadow_soft_size = soft
    L.visible_glossy = glossy
    return L


KEY = float(OPT.get('key', 260000))
light('LampKey', 'SPOT', (LX, LY, LZ + 3.0), (0, 2, FELT), KEY, (1.0, 0.8, 0.56), spot=float(OPT.get('cone', 44)), blend=0.95, soft=7.0)
light('Rim', 'AREA', (6, 70, 22), (0, 0, 2), float(OPT.get('rim', 25000)), (1.0, 0.7, 0.45), size=30, glossy=True)
light('Fill', 'AREA', (-30, -60, 30), (0, 0, 0), float(OPT.get('fill', 1200)), (0.55, 0.65, 1.0), size=40, glossy=False)

# out-of-focus casino lights behind the table (slot banks, chandeliers)
rngb = np.random.default_rng(21)
BOK = {}
bm = bmesh.new()
for k in range(220):
    a = rngb.uniform(math.radians(25), math.radians(175)); d = rngb.uniform(90, 260)
    x, y = math.cos(a) * d, math.sin(a) * d - 10; z = rngb.uniform(-6, 40) * (d / 200)
    ci = int(rngb.choice([0, 0, 0, 1, 1, 2, 3], 1)[0])
    ret = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=rngb.uniform(0.6, 1.6), matrix=Matrix.Translation((x, y, z)))
    for f in newfaces(ret): f.material_index = ci
bok = bm_obj('Bokeh', bm, [mat('BokWarm', (0, 0, 0), 1, emit=lin('ffbe6a'), estr=40), mat('BokGold', (0, 0, 0), 1, emit=lin('ffd890'), estr=25),
                           mat('BokRed', (0, 0, 0), 1, emit=lin('ff3a2a'), estr=30), mat('BokBlue', (0, 0, 0), 1, emit=lin('5aa0ff'), estr=25)], stage=False)
bok.visible_shadow = False; bok.visible_diffuse = False


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
scn.cycles.max_bounces = 8; scn.cycles.glossy_bounces = 4; scn.cycles.transmission_bounces = 8; scn.cycles.transparent_max_bounces = 8
scn.cycles.sample_clamp_indirect = 6.0; scn.cycles.caustics_reflective = scn.cycles.caustics_refractive = False
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.view_settings.exposure = float(OPT.get('exp', 0.0))
scn.use_nodes = True; cnt = scn.node_tree
rl = cnt.nodes['Render Layers']; comp = cnt.nodes['Composite']
gl = cnt.nodes.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 1.5; gl.mix = -0.8; gl.size = 7
cnt.links.new(rl.outputs['Image'], gl.inputs['Image']); cnt.links.new(gl.outputs['Image'], comp.inputs['Image'])

cam.data.dof.use_dof = True
for shot in ('game', 'low', 'top', 'cards'):
    if shot not in SHOTS: continue
    if shot == 'game':
        el = math.radians(50); dist = 21
        cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
        tgt = Vector((0, 0.6, 0)); cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.dof.focus_distance = (tgt - cam.location).length; cam.data.dof.aperture_fstop = float(OPT.get('fgame', 0.5))
    elif shot == 'low':
        cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
        cam.rotation_euler = (Vector((0, 0.8, 0.4)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.dof.focus_distance = (Vector((0, 0.5, 1.5)) - cam.location).length; cam.data.dof.aperture_fstop = float(OPT.get('flow', 0.22))
    elif shot == 'cards':
        cam.data.dof.use_dof = False
        cam.location = (-19, 4, 45); cam.data.angle_y = math.radians(45)
        cam.rotation_euler = (Vector((-19, 4.5, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.data.dof.use_dof = False
        cam.location = (0, -5, 120); cam.data.angle_y = math.radians(40)
        cam.rotation_euler = (Vector((0, 5, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = os.path.join(OUT, 'ex_%s.png' % shot)
    bpy.ops.render.render(write_still=True)
    print('wrote', scn.render.filepath)
