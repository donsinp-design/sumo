# The "final boss" dohyo: a raised clay ring alone in a black void under one warm spotlight, built entirely by script
# (Blender 4.2, run headless).
#   python tools/blender/dohyo.py  [out_dir]  [shot=spot shot=close shot=top ...]  [noprev]
# Writes <out_dir>/dohyo.glb with four top-level objects, origin at the ring centre, Z up, top surface at Z=0,
# front facing -Y, real metres matching the game (S.RING_R is read from public/js/config.js):
#   Mound   the clay mound: flat top (radius RING_R + 1.6) and sloped trapezoid sides 0.6 m down, one mesh.
#   Tawara  the 20 half-buried straw bales round the ring (4 tokudawara on the cardinal points set out by a bale width),
#           each a lumpy, slowly twisted straw bundle with three rope bands.
#   Shikiri the two white start lines, painted and slightly raised.
#   Sand    loose sand grains and clumps kicked up against the bales, the rim and the start lines.
# The recipe: the mound is a dense polar mesh displaced by one height function (macro undulation, a raised rim, clay
# packed up against the bales) and then decimated; the fine relief (broom sweeps, the janome band, toe scuffs, grain)
# is painted with numpy into the textures, with the cavities baked into Base Color so a flat toon shader under a
# light from straight above still reads them. Preview renders <out_dir>/prev_*.png (Cycles, CPU).
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
DEF_OUT = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad/dohyo'
ARGS = [a for a in sys.argv[1:] if '=' not in a and a != 'noprev' and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else DEF_OUT
os.makedirs(OUT, exist_ok=True)
SHOTS = set(a.split('=', 1)[1] for a in sys.argv if a.startswith('shot='))
NOPREV = 'noprev' in sys.argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi


def ring_r():  # the game's ring radius: the inside edge of the straw circle
    try:
        txt = open(os.path.join(HERE, '..', '..', 'public', 'js', 'config.js')).read()
        return float(re.search(r'S\.RING_R\s*=\s*([\d.]+)', txt).group(1))
    except Exception:
        return 4.6


R = ring_r()
RT = R + 1.6           # radius of the mound's flat top (the old boss-stage disc)
DROP = 0.6             # height of the sloped sides
RB = RT + 0.36         # radius at the foot: a trapezoid, a little wider at the bottom
EXT = RT + 0.12        # half-size of the square the top texture covers
NB = 20                # bales in the ring
BA, BRY, BZC = 0.16, 0.15, -0.03   # bale half-width, half-height, axis height (axis below ground: half-buried)
BGW = 0.15             # bale half-width where it meets the clay
SHIKIRI_X, SHIKIRI_W, SHIKIRI_L = 0.62, 0.07, 0.9
RNG = np.random.default_rng(7)


# ================================================================ helpers
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t


def fnoise(h, w, sy, sx, seed):
    """Tileable gaussian-filtered noise (sigma in px along rows / columns), zero mean, unit deviation."""
    r = np.random.default_rng(seed).standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    k = np.exp(-2 * np.pi ** 2 * ((fy * sy) ** 2 + (fx * sx) ** 2))
    n = np.fft.ifft2(np.fft.fft2(r) * k).real
    return ((n - n.mean()) / (n.std() + 1e-12)).astype(np.float32)


def sample(img, u, v):
    """Bilinear, wrapping lookup; u, v in [0,1) across the columns / rows."""
    n, m = img.shape
    u = u * m - 0.5; v = v * n - 0.5
    i0 = np.floor(u).astype(int); j0 = np.floor(v).astype(int); fu = u - i0; fv = v - j0
    i0 %= m; j0 %= n; i1 = (i0 + 1) % m; j1 = (j0 + 1) % n
    return (img[j0, i0] * (1 - fu) * (1 - fv) + img[j0, i1] * fu * (1 - fv) +
            img[j1, i0] * (1 - fu) * fv + img[j1, i1] * fu * fv)


def normal_from_height(hm, px, py=None):
    py = py or px
    gx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) / (2 * px)
    gy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) / (2 * py)
    n = np.stack([-gx, -gy, np.ones_like(hm)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def image(name, arr, data=False):
    """arr: (h, w, 3) floats, row 0 at the bottom (v = 0); sRGB-encoded for colour, raw for data."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    if data: img.colorspace_settings.name = 'Non-Color'
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(px.ravel()); img.file_format = 'PNG'; img.pack()
    return img


def mat(name, base_img=None, nrm_img=None, rough=0.8, nrm_strength=1.0, spec=0.35, color=(1, 1, 1)):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Base Color'].default_value = (*color, 1)
    if base_img:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = base_img; t.interpolation = 'Linear'
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if nrm_img:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = nrm_img
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nrm_strength
        nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def make_obj(name, verts, faces, uvs=None, mats=(), mat_idx=None, smooth=True):
    """uvs: per-loop (flattened in face order) array (n_loops, 2)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        uv = me.uv_layers.new(name='UVMap'); uv.data.foreach_set('uv', np.asarray(uvs, np.float32).ravel())
    for m_ in mats: me.materials.append(m_)
    if mat_idx is not None: me.polygons.foreach_set('material_index', np.asarray(mat_idx, np.int32))
    if smooth is True: me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
    elif smooth is not False: me.polygons.foreach_set('use_smooth', np.asarray(smooth, bool))
    me.validate(); me.update()
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    return o


def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)


# ================================================================ layout of the bales
class Bale: pass


BALES = []
SLOT = TAU / NB
BL = SLOT * (R + BA) - 0.07          # bale length along its arc: a small gap between neighbours
for k in range(NB):
    b = Bale()
    b.toku = k % 5 == 0                    # k = 0, 5, 10, 15 sit on the cardinal points (+X, +Y, -X, -Y)
    b.rc = R + BA + (2 * BA if b.toku else 0) + RNG.uniform(-0.008, 0.008)
    b.ph = k * SLOT + RNG.uniform(-0.004, 0.004)
    b.L = BL * RNG.uniform(0.985, 1.0)
    b.ha = b.L / 2 / b.rc
    b.zc = BZC + RNG.uniform(-0.012, 0.006)
    b.size = RNG.uniform(0.97, 1.03)
    b.seed = 100 + k
    b.bands = [-0.31 * b.L, 0.0, 0.31 * b.L]
    BALES.append(b)


def end_profile(s, L):  # 1 along the bale, rounding down to 0 at its blunt ends
    e = np.clip((L / 2 - np.abs(s)) / 0.15, 0, 1)
    return np.sqrt(1 - (1 - e) ** 2)


def bale_dist(x, y):
    """Signed horizontal distance from (x, y) to the nearest bale's footprint edge (negative under a bale)."""
    ph = np.arctan2(y, x)
    best = np.full(np.shape(x), 9.0, np.float32)
    for b in BALES:
        dph = (ph - b.ph + np.pi) % TAU - np.pi
        c = np.clip(dph, -b.ha, b.ha)
        d = np.hypot(x - b.rc * np.cos(b.ph + c), y - b.rc * np.sin(b.ph + c))
        best = np.minimum(best, d - BGW * b.size * end_profile(c * b.rc, b.L))
    return best


# ================================================================ the surface height (geometry scale)
MAC1 = fnoise(256, 256, 12, 12, 1)    # ~0.6 m undulation
MAC2 = fnoise(256, 256, 4, 4, 2)      # ~0.2 m
MEXT = 6.8


def H(x, y, bd=None):
    r = np.hypot(x, y)
    u, v = (x + MEXT) / (2 * MEXT), (y + MEXT) / (2 * MEXT)
    h = 0.005 * sample(MAC1, u, v) + 0.0015 * sample(MAC2, u, v)
    h = h - 0.004 * np.exp(-(r / 2.0) ** 2)                 # the centre trodden down a little
    h = h + 0.024 * sstep(RT - 0.55, RT - 0.08, r)          # a slightly raised rim
    if bd is None: bd = bale_dist(x, y)
    h = h + 0.03 * np.exp(-np.maximum(bd, 0) / 0.05)        # clay packed up against the bales
    return h


# ================================================================ textures
def tex_top(N=1024):
    """Base colour + normal for the top: broom-swept clay with grain, the janome band, compacted centre and
    start-line areas, toe scuffs, darkening where the clay meets the straw."""
    px = 2 * EXT / N
    c = (np.arange(N) + 0.5) * px - EXT
    X, Y = np.meshgrid(c, c)                      # rows = y (row 0 at the bottom), cols = x
    r = np.hypot(X, Y)
    bd = bale_dist(X, Y)
    warp = fnoise(N, N, 14, 14, 11)
    # --- broom sweeps: arcs of bristle striations, laid one over the other (newer overwrites older)
    S = (0.5 + 0.5 * np.cos(r / 0.05 * TAU + 2 * warp)) ** 3 * 0.4
    RIDGE = np.zeros((N, N), np.float32)
    rng = np.random.default_rng(5)
    for i in range(260):
        rr = 6.15 * math.sqrt(rng.uniform()); aa = rng.uniform(0, TAU)
        pcx, pcy = rr * math.cos(aa), rr * math.sin(aa)
        D = rng.uniform(0.7, 1.4); dirn = rng.uniform(0, TAU)
        cx, cy = pcx - D * math.cos(dirn), pcy - D * math.sin(dirn)
        wb = rng.uniform(0.16, 0.3); span = rng.uniform(0.35, 0.8)
        lam = rng.uniform(0.04, 0.06)
        ext_ = D + wb + 0.1
        i0 = max(0, int((cx - ext_ + EXT) / px)); i1 = min(N, int((cx + ext_ + EXT) / px) + 1)
        j0 = max(0, int((cy - ext_ + EXT) / px)); j1 = min(N, int((cy + ext_ + EXT) / px) + 1)
        if i1 <= i0 or j1 <= j0: continue
        x = X[j0:j1, i0:i1] - cx; y = Y[j0:j1, i0:i1] - cy
        d = np.hypot(x, y); a = (np.arctan2(y, x) - dirn + np.pi) % TAU - np.pi
        w = warp[j0:j1, i0:i1]
        m = sstep(wb, wb - 0.07, np.abs(d - D)) * sstep(span, span - 0.25, np.abs(a))
        stripes = (0.5 + 0.5 * np.cos(d / lam * TAU + 1.5 * w)) ** 2.5
        S[j0:j1, i0:i1] = S[j0:j1, i0:i1] * (1 - m) + stripes * m
        # the broom pushes a little loose sand into a soft ridge at the end of each stroke
        endd = np.abs(np.abs(a) - span + 0.08) * D
        RIDGE[j0:j1, i0:i1] += 0.6 * np.exp(-(endd / 0.03) ** 2) * sstep(wb, wb - 0.07, np.abs(d - D)) * (a > 0)
    breakup = 0.55 + 0.45 * sstep(-1.2, 1.0, fnoise(N, N, 3, 3, 12))
    S *= breakup
    # --- janome: a band of fine, evenly brushed sand just outside the straw
    J = sstep(R + 0.25, R + 0.4, r) * sstep(R + 0.95, R + 0.8, r)
    jstr = (0.5 + 0.5 * np.cos(r / 0.045 * TAU + 0.6 * warp)) ** 2
    S = S * (1 - J) + jstr * J * 0.6
    # --- compacted: the centre and where the two men crouch at their lines
    Cc = 0.75 * np.exp(-(r / 1.9) ** 2)
    for sx in (-1, 1):
        Cc = Cc + 0.8 * np.exp(-((X - sx * 1.05) / 0.62) ** 2 - (Y / 0.7) ** 2)
    Cc = np.clip(Cc, 0, 1)
    # --- toe scuffs and short slide marks behind each line
    SC = np.zeros((N, N), np.float32)
    for sx in (-1, 1):
        for i in range(9):
            ex = sx * rng.uniform(0.78, 1.5); ey = rng.uniform(-0.55, 0.55)
            l = rng.uniform(0.05, 0.11); wd = rng.uniform(0.03, 0.05); ang = rng.uniform(-0.4, 0.4)
            dx, dy = X - ex, Y - ey
            u_ = dx * math.cos(ang) + dy * math.sin(ang); v_ = -dx * math.sin(ang) + dy * math.cos(ang)
            SC += np.exp(-(u_ / l) ** 2 - (v_ / wd) ** 2)
        for i in range(2):
            ex = sx * rng.uniform(0.9, 1.3); ey = rng.uniform(-0.4, 0.4)
            dx, dy = X - ex, Y - ey
            SC += 0.5 * np.exp(-(dx / 0.3) ** 2 - (dy / 0.035) ** 2)
    SC = np.clip(SC, 0, 1.2)
    # --- height for the normal map (metres)
    g1 = fnoise(N, N, 0.7, 0.7, 13); g2 = fnoise(N, N, 2.0, 2.0, 14); meso = fnoise(N, N, 6, 6, 15)
    rough = 1 - 0.65 * Cc
    hm = (0.0007 * g1 + 0.0006 * g2) * rough + 0.0012 * meso + 0.0016 * S * (1 - 0.7 * Cc) \
        + 0.0012 * np.clip(RIDGE, 0, 1) - 0.004 * SC
    nrm = normal_from_height(hm, px)
    # --- colour (sRGB)
    n1 = fnoise(N, N, 60, 60, 21); n2 = fnoise(N, N, 25, 25, 22); n3 = fnoise(N, N, 8, 8, 23)
    col = np.broadcast_to(hx('c4946a'), (N, N, 3)).copy()
    col = lerp(col, hx('cf9a56'), (0.4 * sstep(-1, 1.5, n1))[..., None])       # ochre
    col = lerp(col, hx('b88672'), (0.35 * sstep(-0.5, 1.5, n2))[..., None])    # rosy
    val = 1 + 0.045 * n3 + 0.04 * g2 * rough + 0.05 * g1 * rough
    col = lerp(col, hx('9a6844'), (0.5 * Cc)[..., None])                        # compacted: darker, damper
    col = lerp(col, hx('d8b48a'), (0.45 * J)[..., None])                        # janome: paler, finer
    val = val * (1 - 0.13 * S * (1 - 0.6 * Cc)) + 0.08 * np.clip(RIDGE, 0, 1)    # stripes darken their grooves
    val = val * (1 - 0.22 * SC)
    val = val * (1 - 0.45 * np.exp(-np.maximum(bd, 0) / 0.035)) * (1 - 0.15 * np.exp(-np.maximum(bd, 0) / 0.15))
    rim = sstep(RT - 0.25, RT - 0.02, r)
    col = lerp(col, hx('cfa680'), (0.4 * rim)[..., None])                       # the dry, crumbly rim
    col = col * val[..., None]
    sp = rng.uniform(size=(N, N))
    col[sp > 0.996] = hx('ecd8b8'); col[sp < 0.0035] = hx('5a3c28')
    return col, nrm


def tex_side(W=512, Hh=256):
    """Side clay: darker and smoother, with overlapping trowel strokes. Covers 2.4 m x 1.2 m; tiles around."""
    px = 2.4 / W
    xs = (np.arange(W) + 0.5) * px; ys = (np.arange(Hh) + 0.5) * px
    X, Y = np.meshgrid(xs, ys)
    hm = np.zeros((Hh, W), np.float32); shade = np.zeros((Hh, W), np.float32)
    rng = np.random.default_rng(31)
    for i in range(90):
        cx, cy = rng.uniform(0, 2.4), rng.uniform(0, 1.2)
        a, b = rng.uniform(0.18, 0.4), rng.uniform(0.05, 0.11); ang = rng.uniform(-0.35, 0.35)
        dx = (X - cx + 1.2) % 2.4 - 1.2; dy = Y - cy
        u = dx * math.cos(ang) + dy * math.sin(ang); v = -dx * math.sin(ang) + dy * math.cos(ang)
        e = (u / a) ** 2 + (v / b) ** 2
        m = sstep(1.0, 0.8, e)
        plane = 0.0015 * (v / b) + rng.uniform(-0.001, 0.001)
        ridge = 0.0018 * np.exp(-((e - 0.95) / 0.08) ** 2) * (v > 0)     # clay pushed out at one edge of the stroke
        hm = hm * (1 - m) + plane * m + ridge
        shade = shade * (1 - m) + rng.uniform(-1, 1) * m
    g = fnoise(Hh, W, 0.8, 0.8, 32); scratch = fnoise(Hh, W, 0.6, 30, 33)
    hm = hm + 0.0004 * g + 0.0004 * scratch
    nrm = normal_from_height(hm, px)
    n1 = fnoise(Hh, W, 30, 60, 34)
    col = np.broadcast_to(hx('9a6a4a'), (Hh, W, 3)).copy()
    col = lerp(col, hx('8a5a44'), (0.4 * sstep(-1, 1.5, n1))[..., None])
    val = 1 + 0.035 * shade + 0.035 * g - 0.04 * np.clip(scratch, 0, 3) + 25 * hm
    v01 = Y / 1.2
    val = val * (1 + 0.12 * sstep(0.1, 0.0, v01))          # top band (v near 0): dusty and lighter
    col = col * val[..., None]
    return col, nrm


def tex_straw(N=512):
    """Rice straw along u (bale length, 0.71 m per tile), around v (0..1 across the visible arc)."""
    f = 0.55 * fnoise(N, N, 0.9, 26, 41) + 0.35 * fnoise(N, N, 2.2, 70, 42) + 0.25 * fnoise(N, N, 0.6, 7, 43)
    clump = fnoise(N, N, 9, 90, 44)
    t = 1 / (1 + np.exp(-(1.3 * f + 0.5 * clump)))
    col = lerp(hx('6e5328')[None, None], hx('c9ad6c')[None, None], t[..., None] ** 0.9)
    col = lerp(col, hx('e6d29a')[None, None], (sstep(0.75, 0.95, t))[..., None])
    weather = sstep(0.3, 1.6, fnoise(N, N, 40, 80, 45))
    grey = col.mean(-1, keepdims=True) * np.array([1.0, 0.98, 0.9])
    col = lerp(col, grey, 0.45 * weather[..., None])
    odd = fnoise(N, N, 0.7, 40, 46) > 2.3                   # the odd darker brown straw
    col[odd] *= np.array([0.7, 0.6, 0.5])
    v = (np.arange(N)[:, None] + 0.5) / N
    edge = np.minimum(v, 1 - v) + 0.03 * fnoise(N, N, 3, 3, 47)
    dirt = sstep(0.14, 0.02, edge)[..., None]                 # soiled where it meets the clay
    col = lerp(col, hx('8a6448')[None, None] * 0.9, 0.75 * dirt)
    hm = 0.0012 * f + 0.0008 * clump
    nrm = normal_from_height(hm, 0.71 / N, 0.55 / N)
    return col, nrm


def tex_rope(W=256, Hh=64):
    """Twisted straw rope: u along the rope (0.4 m per tile), v once round the rope."""
    x = np.arange(W)[None, :] + 0.5; y = np.arange(Hh)[:, None] + 0.5
    ph = TAU * (x / 25.6 + 2 * y / Hh)
    strand = np.abs(np.sin(ph / 2)) ** 0.6
    fib = fnoise(Hh, W, 0.7, 6, 51)
    t = np.clip(0.75 * strand + 0.12 * fib, 0, 1)
    col = lerp(hx('5a4220')[None, None], hx('b49456')[None, None], t[..., None])
    hm = 0.003 * strand + 0.0003 * fib
    nrm = normal_from_height(hm, 0.4 / W, 0.126 / Hh)
    return col, nrm


def tex_paint(W=64, Hh=512):
    """White start-line paint, worn at the edges and scuffed through in spots."""
    u = (np.arange(W)[None, :] + 0.5) / W; v = (np.arange(Hh)[:, None] + 0.5) / Hh
    edge = np.minimum(np.minimum(u, 1 - u) * 0.074, np.minimum(v, 1 - v) * 0.9)
    n = fnoise(Hh, W, 3, 3, 61); n2 = fnoise(Hh, W, 12, 4, 62)
    wear = np.clip(sstep(0.012, 0.0, edge + 0.004 * n) + sstep(1.6, 2.4, n2 + 0.4 * n), 0, 1)
    col = lerp(hx('f4efe4')[None, None], hx('c09670')[None, None], 0.85 * wear[..., None])
    col *= (1 + 0.03 * fnoise(Hh, W, 1, 1, 63))[..., None]
    return col


def tex_loose(N=128):
    n = fnoise(N, N, 2, 2, 71); n2 = fnoise(N, N, 0.6, 0.6, 72)
    col = lerp(hx('b88458')[None, None], hx('e2c098')[None, None], sstep(-1.5, 1.5, n)[..., None])
    return col * (1 + 0.08 * n2)[..., None]


# ================================================================ Mound
def build_mound():
    NA = 720
    rs_top = np.concatenate([np.linspace(0.06, 4.2, 42), np.linspace(4.22, 5.6, 70), np.linspace(5.64, RT - 0.08, 12)])
    top_r = RT - 0.08
    # rounded edge (quadratic Bezier) into the slope, then the slope down to the foot
    P0 = np.array([top_r, 0.0]); C = np.array([RT + 0.02, 0.0])
    slope = np.array([RB - RT, -DROP]); slope /= np.linalg.norm(slope)
    P1 = C + slope * 0.11
    corner = [(1 - t) ** 2 * P0 + 2 * (1 - t) * t * C + t * t * P1 for t in np.linspace(0, 1, 8)[1:]]
    bottom = np.array([RB, -DROP])
    side = [P1 + (bottom - P1) * t for t in np.linspace(0, 1, 15)[1:]]
    side = [p + np.array([0.015 * math.sin(math.pi * t), 0]) for p, t in zip(side, np.linspace(0, 1, 15)[1:])]
    prof = [(r_, 0.0, 1.0) for r_ in rs_top]
    prof += [(p[0], p[1], 1 - i / (len(corner))) for i, p in enumerate(corner, 1)]
    prof += [(p[0], p[1], 0.0) for p in side]
    prof = np.array(prof)                           # columns: r, z (base profile), weight of the top's relief
    ang = np.arange(NA) / NA * TAU
    rr, A = np.meshgrid(prof[:, 0], ang, indexing='ij')
    X, Y = rr * np.cos(A), rr * np.sin(A)
    Z = np.broadcast_to(prof[:, 1:2], rr.shape).copy()
    wt = np.broadcast_to(prof[:, 2:3], rr.shape)
    # relief of the top; the edge takes the relief of the top's last ring so the two join
    hx_, hy_ = np.minimum(rr, top_r) * np.cos(A), np.minimum(rr, top_r) * np.sin(A)
    Z += H(hx_, hy_) * np.where(rr <= top_r, 1.0, wt)
    # the slope: hand-dressed waviness, pushed out along the horizontal
    sn = fnoise(64, 1024, 2.5, 18, 7)
    on_side = rr > top_r + 0.005
    zz = np.clip((Z + 0.7) / 0.8, 0, 1)
    dr = 0.012 * sample(sn, A / TAU, zz) * on_side * sstep(0.0, 0.08, -Z)
    X += dr * np.cos(A); Y += dr * np.sin(A)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    nr = len(prof)
    idx = lambda i, j: i * NA + (j % NA)
    faces = []
    for i in range(nr - 1):
        for j in range(NA):
            faces.append((idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)))
    ci = len(verts)
    verts = np.vstack([verts, [[0, 0, H(np.array([0.0]), np.array([0.0]))[0]]]])
    for j in range(NA): faces.append((ci, idx(0, j + 1), idx(0, j)))
    o = make_obj('Mound', verts, faces)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    full = tris(o)
    d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = 26000 / full; d.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='dec')
    # materials and UVs: planar for the top, wrapped round for the sides
    me = o.data
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    lv = np.zeros(len(me.loops), int); me.loops.foreach_get('vertex_index', lv)
    ls = np.zeros(len(me.polygons), int); me.polygons.foreach_get('loop_start', ls)
    lt = np.zeros(len(me.polygons), int); me.polygons.foreach_get('loop_total', lt)
    pc = np.zeros(len(me.polygons) * 3); me.polygons.foreach_get('center', pc); pc = pc.reshape(-1, 3)
    pr = np.hypot(pc[:, 0], pc[:, 1])
    is_side = pr > RT - 0.01
    lp = co[lv]
    u_top = (lp[:, 0] + EXT) / (2 * EXT); v_top = (lp[:, 1] + EXT) / (2 * EXT)
    reps = round(TAU * (RT + 0.15) / 2.4)
    u_side = (np.arctan2(lp[:, 1], lp[:, 0]) / TAU) % 1.0 * reps
    v_side = (0.03 - lp[:, 2]) / 1.2 + 0.0
    face_of_loop = np.repeat(np.arange(len(me.polygons)), lt)
    side_loop = is_side[face_of_loop]
    # fix the wrap seam: within a face, bring every u near the face's first u
    first = u_side[ls][face_of_loop]
    u_side = np.where(u_side - first > reps / 2, u_side - reps, np.where(first - u_side > reps / 2, u_side + reps, u_side))
    uv = np.where(side_loop[:, None], np.stack([u_side, v_side], -1), np.stack([u_top, v_top], -1))
    me.uv_layers.new(name='UVMap').data.foreach_set('uv', uv.astype(np.float32).ravel())
    me.polygons.foreach_set('material_index', is_side.astype(np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
    me.update()
    print('mound: built', full, 'tris, decimated to', tris(o))
    return o


# ================================================================ Tawara
def bale_surface(b, s, th, ridges=True):
    """Points on bale b at arc position s (m from its middle) and angle th round its cross-section."""
    rng = np.random.default_rng(b.seed)
    p1, p2, p3 = rng.uniform(0, TAU, 3)
    f = end_profile(s, b.L) * b.size
    pinch = sum(np.exp(-((s - sb) / 0.03) ** 2) for sb in b.bands)
    f = f * (1 - 0.11 * pinch)
    f = f * (1 + 0.035 * np.sin(s / b.L * TAU * 1.5 + p1) + 0.02 * np.sin(s / b.L * TAU * 3.7 + p2))  # lumps
    if ridges:   # a slow twist of straw strands
        f = f * (1 + 0.028 * np.sin(8 * th + s / b.L * TAU * 1.1 + p3) + 0.012 * np.sin(19 * th - s / b.L * TAU * 2 + p2))
    ph = b.ph + s / b.rc
    a = BA * f * np.cos(th)
    zf = BRY * f * np.sin(th) * (1 - 0.1 * np.clip(np.sin(th), 0, 1) ** 6)    # a little flattened on top
    x = (b.rc + a) * np.cos(ph); y = (b.rc + a) * np.sin(ph)
    return np.stack([x, y, b.zc + zf], -1)


def build_tawara():
    verts, faces, uvs, mi = [], [], [], []
    TH = np.linspace(-0.3, math.pi + 0.3, 21)
    for b in BALES:
        ss = list(np.linspace(-b.L / 2, b.L / 2, 25))
        for sb in b.bands: ss += [sb - 0.035, sb - 0.012, sb + 0.012, sb + 0.035]
        ss = np.unique(np.round(ss, 4))
        S_, T_ = np.meshgrid(ss, TH, indexing='ij')
        P = bale_surface(b, S_, T_).reshape(-1, 3)
        base = len(verts); verts.extend(P)
        ns, nt = len(ss), len(TH)
        u = (S_ + b.L / 2) / (b.L / 2)
        v = (T_ - TH[0]) / (TH[-1] - TH[0]) + 0.22 * S_ / b.L
        rr = np.random.default_rng(b.seed + 1)
        u = u + rr.uniform(0, 1)
        for i in range(ns - 1):
            for j in range(nt - 1):
                faces.append((base + i * nt + j, base + (i + 1) * nt + j, base + (i + 1) * nt + j + 1, base + i * nt + j + 1))
                uvs.extend([(u[i, j], v[i, j]), (u[i + 1, j], v[i + 1, j]), (u[i + 1, j + 1], v[i + 1, j + 1]), (u[i, j + 1], v[i, j + 1])])
                mi.append(0)
        # rope bands: a flattened tube round the pinched waist of the bundle
        NP, NS = 16, 5
        for sb in b.bands:
            th = np.linspace(-0.22, math.pi + 0.22, NP)
            c0 = bale_surface(b, np.full(NP, sb), th, ridges=False)
            cin = bale_surface(b, np.full(NP, sb), th * 0 + math.pi / 2, ridges=False)[0]
            ph = b.ph + sb / b.rc
            T = np.array([-math.sin(ph), math.cos(ph), 0.0])              # along the bale
            axis = np.array([b.rc * math.cos(ph), b.rc * math.sin(ph), b.zc])
            Nn = c0 - axis; Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
            Cc = c0 + Nn * 0.012
            plen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Cc, axis=0), axis=1))])
            bb = len(verts)
            for k in range(NP):
                for q in range(NS):
                    psi = q / NS * TAU
                    verts.append(Cc[k] + Nn[k] * math.cos(psi) * 0.018 + T * math.sin(psi) * 0.024)
            for k in range(NP - 1):
                for q in range(NS):
                    q1 = (q + 1) % NS
                    faces.append((bb + k * NS + q, bb + k * NS + q1, bb + (k + 1) * NS + q1, bb + (k + 1) * NS + q))
                    uvs.extend([(plen[k] / 0.4, q / NS), (plen[k] / 0.4, (q + 1) / NS), (plen[k + 1] / 0.4, (q + 1) / NS), (plen[k + 1] / 0.4, q / NS)])
                    mi.append(1)
    o = make_obj('Tawara', np.array(verts), faces, np.array(uvs), (STRAW, ROPE), mi)
    print('tawara:', tris(o), 'tris')
    return o


# ================================================================ Shikiri
def build_shikiri():
    verts, faces, uvs = [], [], []
    xo = np.array([-0.5, -0.46, -0.36, 0, 0.36, 0.46, 0.5]) * (SHIKIRI_W + 0.004)
    fx = np.array([0, 0.6, 1, 1, 1, 0.6, 0])
    yl = SHIKIRI_L / 2
    yo = np.concatenate([[-yl - 0.002, -yl + 0.002, -yl + 0.01], np.linspace(-yl + 0.025, yl - 0.025, 20), [yl - 0.01, yl - 0.002, yl + 0.002]])
    fy = np.concatenate([[0, 0.6, 1], np.ones(20), [1, 0.6, 0]])
    for sx in (-1, 1):
        X, Yg = np.meshgrid(sx * SHIKIRI_X + xo, yo, indexing='ij')
        F = np.minimum(fx[:, None], fy[None, :])
        rng = np.random.default_rng(80 + sx)
        Z = H(X, Yg) + 0.0065 * F - 0.002 * (1 - F) + 0.0006 * rng.standard_normal(X.shape) * F
        base = len(verts); verts.extend(np.stack([X, Yg, Z], -1).reshape(-1, 3))
        nx, ny = X.shape
        U = (xo[:, None] / (SHIKIRI_W + 0.004) + 0.5) * np.ones((1, ny)); V = (yo[None, :] + yl) / SHIKIRI_L * np.ones((nx, 1))
        if sx < 0: U = 1 - U
        for i in range(nx - 1):
            for j in range(ny - 1):
                faces.append((base + i * ny + j, base + (i + 1) * ny + j, base + (i + 1) * ny + j + 1, base + i * ny + j + 1))
                uvs.extend([(U[i, j], V[i, j]), (U[i + 1, j], V[i + 1, j]), (U[i + 1, j + 1], V[i + 1, j + 1]), (U[i, j + 1], V[i, j + 1])])
    o = make_obj('Shikiri', np.array(verts), faces, np.array(uvs), (PAINT,))
    print('shikiri:', tris(o), 'tris')
    return o


# ================================================================ Sand
def blob(kind, rng):
    """A small irregular grain: an octahedron (tiny grains) or a 12-vertex icosahedron (clumps), jittered."""
    if kind == 0:
        v = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
        f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    else:
        t = (1 + 5 ** 0.5) / 2
        v = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                      [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
        v /= np.linalg.norm(v[0])
        f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = v * rng.uniform(0.7, 1.25, (len(v), 1))
    return v, f


def build_sand():
    rng = np.random.default_rng(91)
    # candidates over the top, kept in proportion to where loose sand gathers
    M = 60000
    rr = (RT - 0.04) * np.sqrt(rng.uniform(size=M)); aa = rng.uniform(0, TAU, M)
    x, y = rr * np.cos(aa), rr * np.sin(aa)
    bd = bale_dist(x, y)
    dens = 1.0 * np.exp(-np.maximum(bd, 0) / 0.06) * (bd > 0.0) * np.where(np.hypot(x, y) > (R + BA), 1.0, 0.55)
    dens += 0.5 * sstep(RT - 0.35, RT - 0.08, rr)
    for sx in (-1, 1):
        dens += 0.25 * np.exp(-((x - sx * 1.05) / 0.45) ** 2 - (y / 0.6) ** 2)
    dens += 0.015
    onl = (np.abs(np.abs(x) - SHIKIRI_X) < SHIKIRI_W) & (np.abs(y) < SHIKIRI_L / 2 + 0.03)
    dens[onl] = 0
    keep = rng.uniform(size=M) < dens / dens.max() * 0.06
    x, y, bdk = x[keep], y[keep], bd[keep]
    z = H(x, y, bdk)
    verts, faces, uvs, sm = [], [], [], []
    for i in range(len(x)):
        big = rng.uniform() < 0.12
        kind = 1 if big else 0
        s = rng.uniform(0.028, 0.05) if big else rng.lognormal(math.log(0.012), 0.35)
        v, f = blob(kind, rng)
        a = rng.uniform(0, TAU); ca, sa = math.cos(a), math.sin(a)
        v = v * np.array([s * rng.uniform(0.8, 1.3), s, s * rng.uniform(0.35, 0.6)])
        v = v @ np.array([[ca, sa, 0], [-sa, ca, 0], [0, 0, 1]])
        v += np.array([x[i], y[i], z[i] + s * 0.12])
        base = len(verts); verts.extend(v)
        cu, cv = rng.uniform(size=2)
        for t in f:
            faces.append(tuple(base + k for k in t)); uvs.extend([(cu, cv)] * 3); sm.append(big)
    o = make_obj('Sand', np.array(verts), faces, np.array(uvs), (LOOSE,), smooth=sm)
    print('sand:', len(x), 'grains,', tris(o), 'tris')
    return o


# ================================================================ build everything
col, nrm = tex_top(); TOP = mat('ClayTop', image('clay_top', col), image('clay_top_n', nrm, True), rough=0.9, nrm_strength=1.0, spec=0.3)
col, nrm = tex_side(); SIDE = mat('ClaySide', image('clay_side', col), image('clay_side_n', nrm, True), rough=0.75, spec=0.35)
col, nrm = tex_straw(); STRAW = mat('Straw', image('straw', col), image('straw_n', nrm, True), rough=0.8, spec=0.4)
col, nrm = tex_rope(); ROPE = mat('Rope', image('rope', col), image('rope_n', nrm, True), rough=0.85, spec=0.35)
PAINT = mat('Paint', image('paint', tex_paint()), rough=0.5, spec=0.45)
LOOSE = mat('LooseSand', image('loose_sand', tex_loose()), rough=0.95, spec=0.3)

mound = build_mound(); mound.data.materials.append(TOP); mound.data.materials.append(SIDE)
tawara = build_tawara()
shikiri = build_shikiri()
sand = build_sand()
objs = [mound, tawara, shikiri, sand]
total = sum(tris(o) for o in objs)
print('TOTAL triangles', total, {o.name: tris(o) for o in objs}, 'RING_R', R)

bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'dohyo.glb'), export_format='GLB', use_selection=True,
                          export_apply=True, export_image_format='JPEG', export_jpeg_quality=90)

# ================================================================ previews: a black void and one warm spotlight from straight above
if not NOPREV:
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    spot = bpy.data.objects.new('Spot', bpy.data.lights.new('Spot', 'SPOT')); scn.collection.objects.link(spot)
    spot.location = (0, 0, 15); spot.data.energy = 9000; spot.data.color = (1.0, 0.8, 0.58)
    spot.data.spot_size = math.radians(56); spot.data.spot_blend = 0.55; spot.data.shadow_soft_size = 0.8
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    scn.render.engine = 'CYCLES'; scn.cycles.samples = 48; scn.cycles.device = 'CPU'; scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 4
    scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'

    def shoot(name, pos, look, w=960, h=540, vfov=None, lens=None, ortho=None):
        if SHOTS and name not in SHOTS: return
        scn.render.resolution_x, scn.render.resolution_y = w, h
        cam.data.type = 'ORTHO' if ortho else 'PERSP'
        if ortho: cam.data.ortho_scale = ortho
        if vfov: cam.data.sensor_fit = 'VERTICAL'; cam.data.angle_y = math.radians(vfov)
        if lens: cam.data.sensor_fit = 'AUTO'; cam.data.lens = lens
        cam.location = pos; cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
        scn.render.filepath = os.path.join(OUT, 'prev_' + name + '.png'); bpy.ops.render.render(write_still=True)

    # the game camera: vertical fov 34 deg, framed to the stage like render.js does (about 20 m out), 50 deg down
    pitch, dist = math.radians(50), 20.0
    shoot('spot', (0, -dist * math.cos(pitch), dist * math.sin(pitch)), (0, 0, 0.2), vfov=34)
    shoot('close', (1.1, -3.0, 0.42), (0.55, -4.9, 0.02), lens=40)
    shoot('top', (0, 0, 30), (0, 0, 0), 900, 900, ortho=2 * RB + 0.4)
