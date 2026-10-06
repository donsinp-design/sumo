# SODA CAN stage, fully modelled: two sumos fight on the lid of a giant, ice-cold "KUMITE COLA" can standing on a
# wooden diner counter (glass of cola with ice and a striped straw on a napkin, a crown cap, a condensation puddle
# ring and stray drops), lit by a big daylight window plus a warm key. Built entirely by script (Blender 4.2 headless).
#   python tools/blender/stage_can.py [out_dir] [shot=game|low|tab|can ...] [fast] [noexport] [norender]
# Writes <out_dir>/can.glb (stage only: Z up, metres, origin at the lid centre, textures packed <= 1024 px) and
# <out_dir>/ex_<shot>.png with the game's masked sumos + gyoji imported from scratchpad/stage.
#
# Game contract (public/js/config.js RING_R = 4.6, stages.js can()): lid radius ~5.3, top at Z=0 and flat inside the
# fighting area. The lid panel is flat (Z=0) out to r 4.8 with only pressed relief (<= 2 cm): a raised bead at r 4.6
# marks the fighting circle, a debossed panel ring at 4.25, the scored opening, embossed lettering. The countersink,
# the double seam (rim lip, top at +0.27) and the neck are outside 4.8. The stay-on tab lies inside the circle, < 6 cm.
# Scale: real lid radius 2.65 cm -> 5.3 m, i.e. x200; the can is 21 m tall, the counter top is at Z = -21.
import bpy, bmesh, math, sys, os, time
import numpy as np
from mathutils import Vector, Matrix

SCR = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
CHAR_DIR = SCR + '/stage'
FLAGW = {'fast', 'noexport', 'norender', 'nochars'}
ARGS = [a for a in sys.argv[sys.argv.index('--') + 1 if '--' in sys.argv else 1:] if '=' not in a and a not in FLAGW and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else SCR + '/can'
os.makedirs(OUT, exist_ok=True)
SHOTS = [a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')] or ['game', 'low', 'tab', 'can']
FAST = 'fast' in sys.argv
T0 = time.time()
def log(*a): print('[can %5.1fs]' % (time.time() - T0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RING = 4.6
TZ = -21.0          # counter top
RB = 6.2            # can body radius
STAGE = bpy.data.collections.new('stage'); scn.collection.children.link(STAGE)
ROOM = bpy.data.collections.new('room'); scn.collection.children.link(ROOM)
RNG = np.random.default_rng(7)
F32 = np.float32
FONT_B = '/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf'
FONT_R = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FONT_J = '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'
TEX = 1 if FAST else 2   # texture resolution multiplier for the render (export is always downscaled to 1024)


# ================================================================ numpy helpers
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], F32)
def lin(h): return tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in hx(h)) + (1.0,)
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
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
    """h in metres, top-down rows (row 0 = +V). Tangent-space normal map (OpenGL, +Y = up in the image)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px_m)
    dy = -(np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px_m)    # row increases downwards = -V
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


# ================================================================ text rasteriser (Blender font -> outline -> even-odd)
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
    """E: (n,2,2) in crop pixel coords (x right, y down). Even-odd coverage (Hc, Wc) with SxS supersampling."""
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

def text_mask(shape, s, font, cx, cy, h_px, spacing=1.0, maxw=None, shear=0.0, S=4):
    """Full-size coverage mask with the text's bbox centred at (cx, cy) px and bbox height h_px."""
    E = text_edges(s, font, spacing)
    E[..., 0] += shear * E[..., 1]
    lo, hi_ = E.reshape(-1, 2).min(0), E.reshape(-1, 2).max(0)
    k = h_px / (hi_[1] - lo[1])
    if maxw and (hi_[0] - lo[0]) * k > maxw: k = maxw / (hi_[0] - lo[0])
    P = (E - (lo + hi_) / 2) * k; P[..., 1] *= -1
    w, h = (hi_ - lo) * k
    X0, Y0 = int(cx - w / 2) - 4, int(cy - h / 2) - 4
    Wc, Hc = int(w) + 9, int(h) + 9
    P[..., 0] += cx - X0; P[..., 1] += cy - Y0
    crop = fill_edges(P, Hc, Wc, S)
    full = np.zeros(shape, F32)
    ys, xs = slice(max(0, Y0), min(shape[0], Y0 + Hc)), slice(max(0, X0), min(shape[1], X0 + Wc))
    full[ys, xs] = crop[ys.start - Y0:ys.stop - Y0, xs.start - X0:xs.stop - X0]
    return full


# ================================================================ geometry helpers
def mesh_obj(name, verts, faces, uvs=None, coll=STAGE, mat=None, smooth=True, sharp=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', np.asarray(uvs, F32).ravel())
    me.validate(); me.update()
    if smooth: me.shade_smooth()
    if sharp: me.set_sharp_from_angle(angle=math.radians(sharp))
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    if mat: me.materials.append(mat)
    return ob

def revolve(name, prof, seg, uvmode=None, coll=STAGE, mat=None, rmod=None, sharp=None, centre=(0, 0, 0)):
    """Lathe a (r, z) profile. Faces point outward when the profile runs top-centre -> out -> down -> in.
    uvmode: ('planar', half_extent) | ('cyl', z_top, z_bot, theta0) | ('prof',) (u around, v = profile index)."""
    verts, idx = [], []
    for i, (r, z) in enumerate(prof):
        if r == 0:
            verts.append((centre[0], centre[1], centre[2] + z)); idx.append([len(verts) - 1] * seg); continue
        row = []
        for j in range(seg):
            t = j / seg * TAU; rr = rmod(r, z, t, i) if rmod else r
            verts.append((centre[0] + rr * math.cos(t), centre[1] + rr * math.sin(t), centre[2] + z)); row.append(len(verts) - 1)
        idx.append(row)
    V = np.array(verts, F32)
    faces, uvs = [], []
    def uv(i, jj, vi):
        x, y, z = V[vi] - np.array(centre, F32)
        if uvmode is None: return (jj / seg, i / (len(prof) - 1))
        if uvmode[0] == 'planar': e = uvmode[1]; return (x / (2 * e) + 0.5, y / (2 * e) + 0.5)
        if uvmode[0] == 'cyl':
            zt, zb, t0 = uvmode[1:]
            return (((jj / seg) - t0) % 1.0 if jj < seg else ((1.0 - t0) % 1.0 or 1.0), (z - zb) / (zt - zb))
        return (jj / seg, 1 - i / (len(prof) - 1))
    for i in range(len(prof) - 1):
        for j in range(seg):
            j2 = j + 1
            a, b, c, d = idx[i][j], idx[i][j2 % seg], idx[i + 1][j2 % seg], idx[i + 1][j]
            loop = [(a, i, j), (d, i + 1, j), (c, i + 1, j2), (b, i, j2)]
            if a == b: loop = [(a, i, j), (d, i + 1, j), (c, i + 1, j2)]
            elif c == d: loop = [(a, i, j), (d, i + 1, j), (b, i, j2)]
            faces.append([l[0] for l in loop])
            if uvmode and uvmode[0] == 'cyl':
                # keep the seam continuous: u of column j2 == seg is 1.0 after the theta0 shift handled by wrap
                us = [(((jj / seg) - uvmode[3]) % 1.0) for (_, _, jj) in loop]
                if max(us) - min(us) > 0.5: us = [u + 1.0 if u < 0.5 else u for u in us]
                for (vi, ii, jj), u in zip(loop, us): uvs.append((u, (V[vi][2] - centre[2] - uvmode[2]) / (uvmode[1] - uvmode[2])))
            else:
                for (vi, ii, jj) in loop: uvs.append(uv(ii, jj, vi))
    return mesh_obj(name, verts, faces, uvs, coll, mat, True, sharp)

def link(ob, coll): coll.objects.link(ob)


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

def hook_maps(nt, bs, col=None, rough=None, nrm=None, metal=None, nstr=1.0, mapping=None):
    uvn = None
    if mapping:
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = mapping; nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); uvn = mp.outputs['Vector']
    if col: nt.links.new(tex_node(nt, col, uvn).outputs['Color'], bs.inputs['Base Color'])
    if rough:
        t = tex_node(nt, rough, uvn); sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bs.inputs['Roughness'])
        if metal: nt.links.new(sep.outputs['Blue'], bs.inputs['Metallic'])   # glTF ORM packing: G rough, B metal
    if nrm:
        t = tex_node(nt, nrm, uvn); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])

def aniso(nt, bs, amount, axis='Z', rot=0.0):
    tg = nt.nodes.new('ShaderNodeTangent'); tg.direction_type = 'RADIAL'; tg.axis = axis
    nt.links.new(tg.outputs['Tangent'], bs.inputs['Tangent'])
    bs.inputs['Anisotropic'].default_value = amount; bs.inputs['Anisotropic Rotation'].default_value = rot

def water_mat(name='mWater', rough=0.02):
    m, nt, bs = principled(name, (1, 1, 1, 1), 0, rough, **{'Transmission Weight': 1.0, 'IOR': 1.333})
    return m


# ================================================================ LID: maps
log('lid maps')
LE = 5.4                                 # planar half extent of the lid UVs
LN = 1024 * TEX
lpx = 2 * LE / LN
gx = (np.arange(LN, dtype=F32) + 0.5) * lpx - LE
X, Y = np.meshgrid(gx, -gx)              # top-down: row 0 = +Y
R = np.sqrt(X * X + Y * Y)

RIV = np.array([0.0, -1.0], F32)         # rivet (between centre and the opening)
OPC1, OPR1 = np.array([0.0, -1.78], F32), 0.30     # opening: narrow end near the rivet
OPC2, OPR2 = np.array([0.0, -3.12], F32), 0.95     # wide end toward the rim

def sd_uneven_capsule(px, py, c1, r1, c2, r2):
    """Signed distance to the hull of two circles along the -Y axis (iq's uneven capsule)."""
    h = float(np.linalg.norm(c2 - c1)); qx = np.abs(px - c1[0]); qy = -(py - c1[1])   # axis pointing -Y
    b = (r1 - r2) / h; a = math.sqrt(1 - b * b); k = -b * qx + a * qy
    d1 = np.sqrt(qx * qx + qy * qy) - r1; d2 = np.sqrt(qx * qx + (qy - h) ** 2) - r2; d3 = qx * a + qy * b - r1
    return np.where(k < 0, d1, np.where(k > a * h, d2, d3))

def lid_maps():
    # spun / turned micro rings: a random radial profile, sampled per pixel
    nr = 16384; rr = np.linspace(0, LE * 1.5, nr)
    prof = np.zeros(nr, F32)
    for sig, amp in ((1.0, 1.0), (3.0, 0.7), (12.0, 0.5), (60, 0.6)):
        n = RNG.standard_normal(nr).astype(F32); k = np.fft.rfftfreq(nr)
        n = np.fft.irfft(np.fft.rfft(n) * np.exp(-2 * math.pi ** 2 * (sig * k) ** 2), n=nr).astype(F32); prof += amp * n / n.std()
    spun = np.interp(R, rr, prof).astype(F32)
    h = spun * 0.0006
    # opening: score line, anti-fracture score, debossed panel, raised bead
    d = sd_uneven_capsule(X, Y, OPC1, OPR1, OPC2, OPR2)
    h += -0.007 * np.exp(-(d / 0.009) ** 2) - 0.003 * np.exp(-((d + 0.07) / 0.008) ** 2)
    h += -0.006 * ss(0.0, -0.15, d) + 0.014 * np.exp(-((d - 0.15) / 0.05) ** 2)
    # rivet button: a raised bubble ring around the rivet (mostly under the tab)
    dr = np.sqrt((X - RIV[0]) ** 2 + (Y - RIV[1]) ** 2)
    h += 0.008 * ss(0.62, 0.45, dr)
    # embossed lettering behind the tab (fine, ~5 mm)
    def px_of(x, y): return (x + LE) / lpx, (LE - y) / lpx
    cx, cy = px_of(0, 3.25)
    t1 = text_mask(R.shape, 'KUMITE COLA', FONT_R, cx, cy, 0.30 / lpx, spacing=1.15)
    cx, cy = px_of(0, 3.68)
    t2 = text_mask(R.shape, 'CHILL  ·  FIGHT  ·  RECYCLE', FONT_R, cx, cy, 0.13 / lpx, spacing=1.2)
    tt = t1 + t2
    tb = np.fft.irfft2(np.fft.rfft2(tt) * np.exp(-2 * math.pi ** 2 * (1.2 * np.fft.rfftfreq(LN)[None, :]) ** 2
                                                   - 2 * math.pi ** 2 * (1.2 * np.fft.fftfreq(LN)[:, None]) ** 2), s=tt.shape).astype(F32)
    h += 0.005 * tb
    nrm = normal_from_height(h, lpx, 1.0)
    # colour: aluminium, slightly darker grime in the score and at the text, faint water spots
    base = 0.80 + 0.015 * gn(R.shape, 40 * TEX, 3)
    base -= 0.35 * np.exp(-(d / 0.012) ** 2) + 0.05 * tb
    spots = np.clip(gn(R.shape, 3 * TEX, 4) - 2.6, 0, 1)
    col = np.stack([base * 0.985, base * 0.99, base * 1.0], -1)
    ink = ss(0.075, 0.06, np.abs(R - RING)) * (1 - 0.15 * ss(0.5, 2.5, gn(R.shape, 4 * TEX, 7)))   # printed ring, slightly worn
    col = lerp(col, hx('d0142c') * 0.9, ink)
    rough = 0.30 + 0.03 * gn(R.shape, 25 * TEX, 5) + 0.05 * np.clip(gn(R.shape, (60 * TEX, 8 * TEX), 6), 0, 3) + 0.25 * spots
    rough += 0.08 * np.exp(-(d / 0.012) ** 2) - 0.12 * ink
    orm = np.stack([np.ones_like(rough), np.clip(rough, 0.05, 1), np.ones_like(rough)], -1)
    return img('lid_col', col), img('lid_orm', orm, True), img('lid_nrm', nrm, True)

LID_COL, LID_ORM, LID_NRM = lid_maps()
del X, Y, R

mLid, nt, bs = principled('mLidAlu', (0.8, 0.8, 0.8, 1), 1.0, 0.18)
hook_maps(nt, bs, LID_COL, LID_ORM, LID_NRM, metal=True)
aniso(nt, bs, 0.8, 'Z')
mAlu, nt, bs = principled('mCanAlu', lin('d6d9dd'), 1.0, 0.16); aniso(nt, bs, 0.6, 'Z')
mTab, nt, bs = principled('mTabAlu', lin('eceef1'), 1.0, 0.3); aniso(nt, bs, 0.6, 'X')

# ================================================================ LID: geometry
log('lid geometry')
P = [(0, 0)]
for r in np.arange(0.2, 4.2, 0.2): P.append((float(r), 0.0))
P += [(4.18, 0), (4.22, -0.008), (4.25, -0.012), (4.28, -0.008), (4.32, 0), (4.45, 0),
      (4.53, 0), (4.565, 0.008), (4.6, 0.015), (4.635, 0.008), (4.67, 0), (4.74, 0), (4.79, -0.005),
      (4.84, -0.03), (4.885, -0.10), (4.915, -0.20), (4.935, -0.27), (4.96, -0.31), (4.99, -0.315), (5.015, -0.29),
      (5.035, -0.21), (5.05, -0.10), (5.065, 0.02), (5.085, 0.12), (5.11, 0.195), (5.15, 0.245), (5.2, 0.268),
      (5.25, 0.265), (5.295, 0.24), (5.33, 0.19), (5.352, 0.10), (5.36, -0.02), (5.362, -0.2), (5.36, -0.36)]
LID = revolve('lid', P, 192, ('planar', LE), mat=mLid)
NECK = [(5.36, -0.36), (5.35, -0.46), (5.34, -0.52), (5.35, -0.58), (5.40, -0.72), (5.50, -0.92), (5.66, -1.22),
        (5.84, -1.58)]
SHOULDER = [(5.84, -1.58), (6.0, -1.95), (6.11, -2.3), (6.17, -2.58), (6.195, -2.78), (6.2, -2.95)]   # printed
revolve('neck', NECK, 160, None, mat=mAlu)

# ================================================================ PULL TAB (stay-on tab, real geometry)
log('tab')
def resample(P, step):
    P = np.asarray(P, F32); Q = np.vstack([P, P[:1]])
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    n = max(8, int(L[-1] / step)); s = np.linspace(0, L[-1], n, endpoint=False)
    return np.stack([np.interp(s, L, Q[:, 0]), np.interp(s, L, Q[:, 1])], -1)

def offset(P, d):
    """Offset a closed CCW polygon outward by d (vertex normals)."""
    nx = np.roll(P, -1, 0) - np.roll(P, 1, 0); n = np.stack([nx[:, 1], -nx[:, 0]], -1)
    n /= np.linalg.norm(n, axis=1, keepdims=True); return P + n * d

def arc(c, r, a0, a1, n, rx=None):
    t = np.linspace(a0, a1, n); return [(c[0] + (rx or r) * math.cos(a), c[1] + r * math.sin(a)) for a in t]

YN, HN, RC = -2.08, 1.02, 0.36     # nose end y, nose half width, nose corner radius
YT0, HT = 0.72, 1.6                # tail circle centre y, tail half width (tail end at 2.32 -> 4.4 m long, 3.2 wide)
def tab_outline():
    P = arc((HN - RC, YN + RC), RC, -math.pi / 2, 0, 10)
    for y in np.linspace(YN + RC, YT0, 30)[1:]:
        t = float(ss(YN + RC, YT0 + 0.15, y)); P.append((HN + (HT - HN) * t, y))
    P += arc((0, YT0), HT, 0, math.pi, 60)[1:]
    for y in np.linspace(YT0, YN + RC, 30)[1:]:
        t = float(ss(YN + RC, YT0 + 0.15, y)); P.append((-(HN + (HT - HN) * t), y))
    P += arc((-(HN - RC), YN + RC), RC, math.pi, 1.5 * math.pi, 10)[1:-1]
    return resample(P, 0.05)
HY0, HW, HRC, HY1 = 0.02, 0.88, 0.28, 1.05     # finger hole: flat edge y, half width (55%), corner r, end centre
def hole_outline():
    P = arc((HW - HRC, HY0 + HRC), HRC, -math.pi / 2, 0, 8)
    P += [(HW, y) for y in np.linspace(HY0 + HRC, HY1, 6)[1:]]
    P += arc((0, HY1), 0.85, 0, math.pi, 40, rx=HW)[1:]
    P += [(-HW, y) for y in np.linspace(HY1, HY0 + HRC, 6)[1:]]
    P += arc((-(HW - HRC), HY0 + HRC), HRC, math.pi, 1.5 * math.pi, 8)[1:-1]
    return resample(P, 0.04)
def slot_outline():
    # U-shaped slot around the rivet on the nose side; the tongue holding the rivet joins the tab toward the hole
    a0, a1, rc, hw = math.radians(160), math.radians(380), 0.47, 0.045
    P = arc(RIV, rc + hw, a0, a1, 50)
    e = (RIV[0] + rc * math.cos(a1), RIV[1] + rc * math.sin(a1)); P += arc(e, hw, a1, a1 + math.pi, 8)[1:-1]
    P += arc(RIV, rc - hw, a1, a0, 50)
    s = (RIV[0] + rc * math.cos(a0), RIV[1] + rc * math.sin(a0)); P += arc(s, hw, a0 + math.pi, a0 + TAU, 8)[1:-1]
    return np.array(P, F32)

def ccw(P):
    P = np.asarray(P, F32); a = np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    return P if a > 0 else P[::-1]

def curve_from(name, polys, z, extrude=0.0, bevel=0.0, fill='BOTH', dims='2D', res=2, cyclic=True):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = dims
    if dims == '2D': cu.fill_mode = fill
    cu.extrude = extrude; cu.bevel_depth = bevel; cu.bevel_resolution = res
    for P in polys:
        sp = cu.splines.new('POLY'); sp.points.add(len(P) - 1)
        for k, (x, y) in enumerate(P): sp.points[k].co = (float(x), float(y), 0, 1)
        sp.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu); STAGE.objects.link(ob); ob.location.z = z
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); bpy.ops.object.convert(target='MESH'); ob = bpy.context.view_layer.objects.active
    return ob

def bend(ob):
    """Tab lies almost flat: finger end lifted ~1.2 cm, nose pressed ~0.6 cm down onto the score."""
    me = ob.data
    for v in me.vertices:
        w = ob.matrix_world @ v.co
        if w.y > 0.9: v.co.z += 0.012 * ((w.y - 0.9) / 1.45) ** 2
        if w.y < -1.65: v.co.z -= 0.006 * min(1.0, (-1.65 - w.y) / 0.45)
    me.update()

OUTL, HOLE, SLOT = ccw(tab_outline()), ccw(hole_outline()), ccw(slot_outline())
TZC, TEXT_, TBEV = 0.030, 0.003, 0.02          # tab mid-plane z, half extrude, rounded (hemmed) edge radius
tab = curve_from('tab', [OUTL, HOLE, SLOT], TZC, TEXT_, TBEV, res=2)
# embossed ribs: around the finger hole and a hem step inside the outline
rib1 = curve_from('tab_rib_hole', [offset(HOLE, 0.22)], TZC + TEXT_ + TBEV - 0.004, 0, 0.022, dims='3D', res=3)
rib2 = curve_from('tab_rib_hem', [offset(OUTL, -0.16)], TZC + TEXT_ + TBEV - 0.006, 0, 0.018, dims='3D', res=3)
# flatten the rib tubes (stamped ribs are low and broad), then bend everything the same way
for o in (rib1, rib2):
    for v in o.data.vertices: v.co.z *= 0.45
for o in (tab, rib1, rib2):
    o.data.materials.clear(); o.data.materials.append(mTab); bend(o)
    for p in o.data.polygons: p.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(50))
def hull(P):
    P = sorted(map(tuple, P))
    def half(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0: h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1]); return np.array(lo[:-1] + up[:-1], F32)
OPEN = ccw(hull(arc(OPC1, OPR1, 0, TAU, 60)[:-1] + arc(OPC2, OPR2, 0, TAU, 120)[:-1]))
bead = curve_from('lid_open_bead', [resample(offset(resample(OPEN, 0.05), 0.15), 0.05)], 0.0, 0, 0.05, dims='3D', res=3)
for v in bead.data.vertices: v.co.z = max(v.co.z, -0.02) * 0.3
bead.data.materials.append(mAlu)
for p in bead.data.polygons: p.use_smooth = True
# rivet head: a low dome through the tongue, and the lid's rivet button showing through the slot
bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=14, radius=0.2, location=(RIV[0], RIV[1], TZC + TEXT_ + TBEV - 0.004))
riv = bpy.context.object; riv.scale = (1, 1, 0.075); bpy.ops.object.transform_apply(scale=True); bpy.ops.object.shade_smooth()
riv.name = 'tab_rivet'; riv.data.materials.append(mAlu)
for c in riv.users_collection: c.objects.unlink(riv)
STAGE.objects.link(riv)
bpy.ops.mesh.primitive_torus_add(major_radius=0.26, minor_radius=0.02, major_segments=48, minor_segments=8, location=(RIV[0], RIV[1], TZC + TEXT_ + TBEV - 0.012))
rr_ = bpy.context.object; rr_.scale = (1, 1, 0.5); bpy.ops.object.transform_apply(scale=True); bpy.ops.object.shade_smooth()
rr_.name = 'tab_rivet_ring'; rr_.data.materials.append(mTab)
for c in rr_.users_collection: c.objects.unlink(rr_)
STAGE.objects.link(rr_)


# ================================================================ CAN BODY + LABEL
log('label')
LW, LH = 2048 * TEX, 1024 * TEX
ZT, ZB = -1.58, -19.15                  # label span: printed shoulder + straight body
ZS = -2.95                              # top of the straight body
VS = (ZT - ZS) / (ZT - ZB)              # label v where the straight body starts
TH0 = math.radians(-58) - 0.25 * TAU    # theta at u = 0: face centres (u = .25, .75) at -58 deg and 122 deg
def label_maps():
    shape = (LH, LW)
    v0 = ((np.arange(LH, dtype=F32) + 0.5) / LH)[:, None] * np.ones((1, LW), F32)
    v = (v0 - VS) / (1 - VS)                 # design coordinate: 0 at the top of the straight body
    def VY(c): return (VS + c * (1 - VS)) * LH
    def VH(c): return c * (1 - VS) * LH
    u = ((np.arange(LW, dtype=F32) + 0.5) / LW)[None, :] * np.ones((LH, 1), F32)
    RED, RED2, WHT, CRM, SIL = hx('c8102e'), hx('8e0a1f'), hx('f7f4ee'), hx('f2e3bf'), hx('c9ccd0')
    col = lerp(RED, RED2, ss(0.35, 1.05, v) * 0.6 + 0.12 * ss(0.5, 2.5, gn(shape, 120 * TEX, 11)))
    white = np.zeros(shape, F32); metal = np.zeros(shape, F32); cream = np.zeros(shape, F32); redtxt = np.zeros(shape, F32)
    shade = np.zeros(shape, F32)
    # top / bottom: unprinted metal edge, then white pinstripe
    metal = np.maximum(metal, ss(0.010, 0.006, v0)); white = np.maximum(white, ss(0.012, 0.014, v) * ss(0.026, 0.023, v))
    metal = np.maximum(metal, ss(0.988, 0.992, v)); white = np.maximum(white, ss(0.972, 0.975, v) * ss(0.988, 0.985, v))
    for half in (0, 1):
        cx = (0.25 + 0.5 * half) * LW
        # wordmark: bold italic KUMITE with a deep drop shadow, COLA reversed out of a cream swoosh
        km = text_mask(shape, 'KUMITE', FONT_B, cx, VY(0.165), VH(0.17), spacing=1.02, maxw=0.25 * LW)
        sh = np.roll(np.roll(km, int(0.010 * LH), 0), int(0.004 * LW), 1)
        shade = np.maximum(shade, sh * 0.65); white = np.maximum(white, km)
        uu = (u - (0.25 + 0.5 * half)) * 2       # -0.5..0.5 across the face
        top_ = 0.305 + 0.025 * np.sin(uu * TAU * 0.9 + 0.6); bot_ = 0.43 + 0.03 * np.sin(uu * TAU * 0.9 + 0.2)
        band = ss(top_, top_ + 0.004, v) * ss(bot_ + 0.004, bot_, v) * (np.abs(uu) < 0.5)
        cream = np.maximum(cream, band)
        white = np.maximum(white, ss(top_ - 0.016, top_ - 0.012, v) * ss(top_ - 0.006, top_ - 0.010, v) * (np.abs(uu) < 0.5))
        redtxt = np.maximum(redtxt, text_mask(shape, 'C O L A', FONT_B, cx, VY(0.368), VH(0.075), spacing=1.0))
        white = np.maximum(white, text_mask(shape, '組手コーラ', FONT_J, cx, VY(0.475), VH(0.040), spacing=1.3))
        white = np.maximum(white, text_mask(shape, 'ICE COLD  ·  ORIGINAL TASTE  ·  350 ml', FONT_R, cx, VY(0.952), VH(0.020), spacing=1.1))
    # fizz bubbles: rising streams, growing as they rise
    bub = np.zeros(shape, F32)
    for s in range(14):
        u0 = RNG.uniform(0, 1); drift = RNG.uniform(-0.03, 0.03)
        for k in range(RNG.integers(7, 13)):
            t = RNG.uniform(0, 1) ** 0.8; vv = VS + (0.93 - t * 0.42) * (1 - VS); uu0 = (u0 + drift * t + 0.012 * math.sin(t * 9 + s)) % 1
            r = (4 + 26 * t ** 1.3 + RNG.uniform(0, 6)) * TEX
            cxp, cyp = uu0 * LW, vv * LH
            x0, x1, y0, y1 = int(cxp - r - 3), int(cxp + r + 4), int(cyp - r - 3), int(cyp + r + 4)
            if x0 < 0 or x1 >= LW: continue
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(F32); d = np.sqrt((xx - cxp) ** 2 + (yy - cyp) ** 2)
            ring = np.clip(1.6 * TEX - np.abs(d - r) , 0, 1) if RNG.uniform() < 0.6 else np.clip(r - d, 0, 1) * 0.92
            hl = np.clip(r * 0.28 - np.sqrt((xx - cxp + r * 0.35) ** 2 + (yy - cyp + r * 0.35) ** 2), 0, 1)
            bub[y0:y1, x0:x1] = np.maximum(bub[y0:y1, x0:x1], np.maximum(ring, hl))
    white = np.maximum(white, bub * (1 - cream))
    col = lerp(col, RED2 * 0.55, shade * (1 - white))
    col = lerp(col, CRM, cream); col = lerp(col, RED, redtxt * cream)
    col = lerp(col, WHT, white * (1 - redtxt)); col = lerp(col, SIL, metal)
    # condensation: fog (micro droplets, rougher) with clear trails where drops ran down
    fog = ss(-1.2, 0.6, gn(shape, 40 * TEX, 12)) * ss(0.0, 0.05, v0)
    trails = []
    clear = np.zeros(shape, F32)
    for k in range(70):
        tu = RNG.uniform(0.01, 0.99); tv0 = RNG.uniform(VS + 0.01, 0.7); tv1 = min(0.985, tv0 + RNG.uniform(0.06, 0.35))
        w = RNG.uniform(2.5, 6) * TEX
        y0, y1 = int(tv0 * LH), int(tv1 * LH)
        yy = np.arange(y0, y1)
        xc = tu * LW + 3 * TEX * np.sin(yy / (37.0 * TEX) + k)
        x0 = int(tu * LW - w - 8 * TEX); x1 = int(tu * LW + w + 8 * TEX)
        if x0 < 0 or x1 >= LW: continue
        xx = np.arange(x0, x1)[None, :]
        m = np.clip(w - np.abs(xx - xc[:, None]), 0, 1) * ss(y0, y0 + 30 * TEX, yy)[:, None]
        clear[y0:y1, x0:x1] = np.maximum(clear[y0:y1, x0:x1], m); trails.append((tu, tv1, w / LW))
    fog *= 1 - clear
    # micro droplets in the fog -> bumps
    hgt = np.zeros(shape, F32)
    n_md = 9000 * TEX * TEX // 2
    cu_ = RNG.uniform(0.01, 0.99, n_md); cv_ = RNG.uniform(0.03, 0.97, n_md); cr_ = RNG.uniform(1.2, 4.5, n_md) * TEX
    for a, b, r in zip(cu_, cv_, cr_):
        if fog[int(b * LH), int(a * LW)] < 0.3: continue
        cx_, cy_ = a * LW, b * LH; ri = int(r) + 2
        x0, y0 = int(cx_) - ri, int(cy_) - ri
        yy, xx = np.mgrid[y0:y0 + 2 * ri + 1, x0:x0 + 2 * ri + 1].astype(F32)
        dd = r * r - (xx - cx_) ** 2 - (yy - cy_) ** 2
        hgt[y0:y0 + 2 * ri + 1, x0:x0 + 2 * ri + 1] = np.maximum(hgt[y0:y0 + 2 * ri + 1, x0:x0 + 2 * ri + 1], np.sqrt(np.clip(dd, 0, None)) * 0.6)
    px_m = (TAU * RB) / LW
    nrm = normal_from_height(hgt * px_m, px_m, 1.0)
    rough = 0.09 + 0.26 * fog + 0.04 * metal + 0.02 * gn(shape, 6 * TEX, 13)
    rough = np.where(hgt > 0, 0.05, rough)
    met = 0.3 * (1 - white) * (1 - cream) + metal * 0.7
    orm = np.stack([np.ones(shape, F32), np.clip(rough, 0.04, 1), np.clip(met, 0, 1)], -1)
    return img('label_col', col), img('label_orm', orm, True), img('label_nrm', nrm, True), trails

LB_COL, LB_ORM, LB_NRM, TRAILS = label_maps()
mLabel, nt, bs = principled('mLabel', (0.8, 0.1, 0.1, 1), 0.3, 0.1, **{'Coat Weight': 0.0})
hook_maps(nt, bs, LB_COL, LB_ORM, LB_NRM, metal=True)
log('can body')
BODY = SHOULDER + [(RB, float(z)) for z in np.linspace(ZS, ZB, 9)[1:]]
revolve('can_body', BODY, 160, ('cyl', ZT, ZB, TH0 / TAU % 1.0), mat=mLabel)
BOT = [(6.2, -19.15), (6.17, -19.5), (6.05, -19.9), (5.8, -20.3), (5.45, -20.65), (5.15, -20.9), (4.98, -20.99),
       (4.85, -21.0), (4.72, -20.96), (4.62, -20.82), (4.5, -20.55), (4.0, -20.2), (3.0, -19.95), (1.5, -19.82), (0, -19.8)]
revolve('can_bottom', BOT, 128, None, mat=mAlu)

# ================================================================ condensation droplets on the wall
log('droplets')
mWater = water_mat()
def dome_template(seg=8, rings=2):
    V = [(0, 0, 1)]; F = []
    for k in range(1, rings + 1):
        a = k / rings * math.pi / 2
        for j in range(seg):
            t = j / seg * TAU; V.append((math.sin(a) * math.cos(t), math.sin(a) * math.sin(t), math.cos(a)))
    for j in range(seg): F.append((0, 1 + j, 1 + (j + 1) % seg))
    for k in range(rings - 1):
        b0, b1 = 1 + k * seg, 1 + (k + 1) * seg
        for j in range(seg): F.append((b0 + j, b1 + j, b1 + (j + 1) % seg, b0 + (j + 1) % seg))
    return np.array(V, F32), F
DV, DF = dome_template()
def drops_mesh(name, items, mat, tmpl=(DV, DF)):
    """items: (centre, normal, tangent, r, height, elong) -> one mesh of domes."""
    TV, TF = tmpl; verts, faces = [], []
    for c, n, t, r, h, el in items:
        c, n, t = Vector(c), Vector(n).normalized(), Vector(t).normalized(); b = n.cross(t)
        base = len(verts)
        for x, y, z in TV:
            yy = y * el - (el - 1) * 0.35 * (1 - z) if el > 1 else y
            verts.append(c + t * (x * r) + b * (yy * r) + n * (z * h - 0.15 * h))
        faces += [tuple(base + i for i in f) for f in TF]
    return mesh_obj(name, verts, faces, None, STAGE, mat, True)

acc = []    # (theta*RB, z, r)
def try_place(th, z, r):
    if acc:
        A = np.array(acc, F32); dx = (A[:, 0] - th * RB + math.pi * RB) % (TAU * RB) - math.pi * RB
        if np.any(np.sqrt(dx ** 2 + (A[:, 1] - z) ** 2) < (A[:, 2] + r) * 1.1): return False
    acc.append((th * RB, z, r)); return True
items = []
# drops at the bottom of the clear trails (they slid down and left the trail)
for tu, tv, w in TRAILS:
    th = TH0 + tu * TAU; z = ZT + (ZB - ZT) * (1 - (1 - tv))
    z = ZT - tv * (ZT - ZB); r = max(0.16, w * TAU * RB * 1.6)
    if z < ZS - 0.3 and try_place(th, z, r):
        items.append(((RB * math.cos(th), RB * math.sin(th), z), (math.cos(th), math.sin(th), 0), (-math.sin(th), math.cos(th), 0), r, r * 0.75, 1.5))
NDROP = 700 if FAST else 1500
tries = 0
while len(items) < NDROP and tries < NDROP * 8:
    tries += 1
    th = RNG.uniform(0, TAU); z = RNG.uniform(ZB + 0.2, ZS - 0.1)
    r = float(np.clip(RNG.lognormal(math.log(0.075), 0.55), 0.03, 0.32))
    if not try_place(th, z, r): continue
    el = 1.0 if r < 0.17 else RNG.uniform(1.0, 1.35)
    items.append(((RB * math.cos(th), RB * math.sin(th), z), (math.cos(th), math.sin(th), 0), (-math.sin(th), math.cos(th), 0), r, r * RNG.uniform(0.55, 0.8), el))
# a few on the neck
for k in range(120):
    NS = NECK + SHOULDER[1:]; i = RNG.integers(3, len(NS) - 1); f = RNG.uniform(); (r0, z0), (r1, z1) = NS[i], NS[i + 1]
    rr, zz = r0 + (r1 - r0) * f, z0 + (z1 - z0) * f; th = RNG.uniform(0, TAU)
    nr_ = Vector((zz - z1 if False else (z0 - z1), 0, (r1 - r0))).normalized()  # profile normal in (r, z)
    n = Vector((nr_.x * math.cos(th), nr_.x * math.sin(th), nr_.z)); t = Vector((-math.sin(th), math.cos(th), 0))
    r = float(np.clip(RNG.lognormal(math.log(0.06), 0.5), 0.03, 0.16))
    items.append(((rr * math.cos(th), rr * math.sin(th), zz), tuple(n), tuple(t), r, r * 0.65, 1.0))
drops_mesh('condensation', items, mWater)
log('droplets', len(items))


# ================================================================ COUNTER (wood butcher block) + room shell
log('counter')
def wood_maps():
    N = 1024 * TEX; shape = (N, N); rows = np.arange(N)[:, None] * np.ones((1, N))
    nst = 2; sw = N // nst; st = (rows // sw).astype(int); yl = (rows % sw) / sw
    rng = np.random.default_rng(21); tone = rng.uniform(-1, 1, nst)[st]; hue = rng.uniform(-1, 1, nst)[st]
    grain = gn(shape, (1.2 * TEX, 140 * TEX), 22); grain2 = gn(shape, (6 * TEX, 300 * TEX), 23)
    warp = gn(shape, (40 * TEX, 300 * TEX), 24)
    rings = np.sin((yl * 14 + 1.6 * warp + st * 1.7) * TAU * 0.5) ** 4
    t = 0.45 + 0.17 * tone + 0.10 * grain2 + 0.07 * grain + 0.2 * rings
    LIGHT, DARK = hx('c99363'), hx('7a4a26')
    col = lerp(DARK, LIGHT, np.clip(t, 0, 1)); col = lerp(col, hx('a8683a'), 0.25 * (hue > 0.3))
    seam = np.exp(-((yl * sw) / 1.2) ** 2) + np.exp(-(((1 - yl) * sw) / 1.2) ** 2)
    # butt joints, staggered
    jx = np.zeros(shape, F32)
    for s in range(nst):
        for x in rng.uniform(0, N, 2):
            cols = np.arange(N)[None, :]; m = np.exp(-((cols - x) / 1.0) ** 2); jx[s * sw:(s + 1) * sw] = np.maximum(jx[s * sw:(s + 1) * sw], m)
    dark = np.clip(seam + jx, 0, 1)
    col = lerp(col, hx('3e2614'), dark * 0.8)
    rough = 0.32 + 0.08 * grain + 0.10 * ss(0.5, 2.5, gn(shape, 60 * TEX, 25)) + 0.2 * dark
    h = (0.002 * grain + 0.004 * rings - 0.01 * dark) * 1.0
    nrm = normal_from_height(h, 64.0 / N, 1.0)
    orm = np.stack([np.ones(shape, F32), np.clip(rough, 0.05, 1), np.zeros(shape, F32)], -1)
    return img('wood_col', col), img('wood_orm', orm, True), img('wood_nrm', nrm, True)
W_COL, W_ORM, W_NRM = wood_maps()
mWood, nt, bs = principled('mWood', lin('a0703f'), 0, 0.35)
hook_maps(nt, bs, W_COL, W_ORM, W_NRM, mapping=(1, 1, 1))

def box(name, lo, hi, mat, coll, uvscale=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[(a + b) / 2 for a, b in zip(lo, hi)])
    o = bpy.context.object; o.name = name; o.scale = [b - a for a, b in zip(lo, hi)]
    bpy.ops.object.transform_apply(scale=True)
    for c in o.users_collection: c.objects.unlink(o)
    coll.objects.link(o); o.data.materials.append(mat)
    if uvscale:
        uvl = o.data.uv_layers.active.data
        for p in o.data.polygons:
            n = p.normal
            for li in p.loop_indices:
                v = o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
                a, b = (v.x, v.y) if abs(n.z) > 0.5 else ((v.x, v.z) if abs(n.y) > 0.5 else (v.y, v.z))
                uvl[li].uv = (a / uvscale, b / uvscale)
    if bevel:
        m = o.modifiers.new('b', 'BEVEL'); m.width = bevel; m.segments = 3
    return o

CX0, CX1, CY0, CY1 = -170, 170, -120, 70
box('counter', (CX0, CY0, TZ - 8), (CX1, CY1, TZ), mWood, STAGE, uvscale=64.0, bevel=1.6)

HDRI_ROT = 150
HDRI = SCR + '/ph/small_empty_house_2k.hdr'   # CC0, Poly Haven (render-only lighting/reflections)

# ================================================================ puddle ring + stray drops on the counter
log('puddle')
def puddle(name, cx, cy, r_in, r_out_fn, h, seg=160, rings=7):
    verts, faces = [], []
    for i in range(rings + 1):
        f = i / rings
        for j in range(seg):
            t = j / seg * TAU; ro = r_out_fn(t); r = r_in + (ro - r_in) * f
            edge = (1 - f)
            z = TZ + 0.004 + h * (1 - ss(0.55, 1.0, f) ** 1.5) if i < rings else TZ - 0.01
            verts.append((cx + r * math.cos(t), cy + r * math.sin(t), z))
    for i in range(rings):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    o = mesh_obj(name, verts, faces, None, STAGE, mWater, True)
    return o
ph = RNG.uniform(0, TAU, 6)
puddle('puddle_ring', 0, 0, 4.7, lambda t: 6.75 + 0.35 * math.sin(3 * t + ph[0]) + 0.22 * math.sin(7 * t + ph[1]) + 0.5 * max(0, math.sin(t + 0.6)) ** 6 * 2.2, 0.14)
DT = dome_template(20, 5)
cdrops = []
for (x, y, r) in ((8.6, -3.0, 0.9), (9.4, 1.5, 0.55), (7.4, 5.5, 0.7), (-8.4, 2.2, 0.6), (-7.8, -4.4, 1.1), (11.5, -1.0, 0.35),
                  (-10.5, -1.2, 0.4), (3.0, 8.4, 0.8), (-3.5, 8.0, 0.45), (15.5, 7.0, 1.3), (12.0, 10.5, 0.5)):
    cdrops.append(((x, y, TZ), (0, 0, 1), (1, 0, 0), r, min(0.22, r * 0.25), 1.0 + RNG.uniform(0, 0.3)))
drops_mesh('counter_drops', cdrops, mWater, DT)

# ================================================================ PROPS: glass of cola with ice + straw, napkin, crown cap
log('props')
GX, GY = -19.0, 11.0
NAPZ = TZ + 0.12
# napkin: soft folded paper under the glass, embossed border
def napkin_maps():
    N = 512; yy, xx = np.mgrid[0:N, 0:N].astype(F32) / N
    e = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
    quilt = (np.abs(np.sin((xx + yy) * 40 * math.pi)) * np.abs(np.sin((xx - yy) * 40 * math.pi)))
    border = ss(0.07, 0.065, e) * ss(0.045, 0.05, e)
    h = 0.02 * gn((N, N), 1.5, 51) + 0.04 * quilt * ss(0.08, 0.1, e) + 0.06 * border
    col = np.ones((N, N, 3), F32) * 0.94 - 0.03 * border[..., None]
    col[..., 2] -= 0.01
    return img('napkin_col', col), img('napkin_nrm', normal_from_height(h, 1.0 / N * 2, 1.0), True)
NP_COL, NP_NRM = napkin_maps()
mNap, nt, bs = principled('mNapkin', (0.94, 0.94, 0.93, 1), 0, 0.85, **{'Subsurface Weight': 0.15, 'Subsurface Radius': (0.5, 0.5, 0.5)})
hook_maps(nt, bs, NP_COL, None, NP_NRM)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=32, y_subdivisions=32, size=30, location=(GX + 1.5, GY - 1.0, NAPZ))
nap = bpy.context.object; nap.name = 'napkin'; nap.rotation_euler.z = math.radians(23)
gnp = gn((64, 64), 4, 52)
for v in nap.data.vertices:
    x, y = v.co.x / 15, v.co.y / 15
    z = 0.10 * gnp[int((y + 1) * 31.5), int((x + 1) * 31.5)]
    z += 0.35 * math.exp(-((x - y * 0.1) / 0.05) ** 2) * 0.5          # fold crease ridge
    z += 1.6 * max(0.0, (x + y - 1.45)) ** 2 * 3                      # one curled corner
    v.co.z = max(z, 0.0) * float(ss(7.0, 9.5, math.hypot(v.co.x + 1.0, v.co.y - 1.5)))   # flat under the glass
nap.data.shade_smooth()
for c in nap.users_collection: c.objects.unlink(nap)
STAGE.objects.link(nap); nap.data.materials.append(mNap)
sol = nap.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.12; sol.offset = -1

mGlass, nt, bs = principled('mGlass', (1, 1, 1, 1), 0, 0.0, **{'Transmission Weight': 1.0, 'IOR': 1.5})
GT = NAPZ + 0.12
GLASS = [(0, GT + 2.1), (5.6, GT + 2.15), (6.05, GT + 2.3), (6.2, GT + 2.7), (6.24, GT + 6), (6.3, GT + 20), (6.38, GT + 29.6),
         (6.44, GT + 29.85), (6.52, GT + 29.9), (6.62, GT + 29.82), (6.7, GT + 29.6), (6.62, GT + 20), (6.56, GT + 6),
         (6.55, GT + 1.2), (6.45, GT + 0.35), (6.2, GT + 0.05), (5.8, GT), (0, GT)]
revolve('glass', GLASS, 96, None, mat=mGlass, centre=(GX, GY, 0))   # inner floor -> inner wall up -> rim -> outer wall -> base
# cola: absorbing liquid, meniscus top, slightly bigger than the cavity (merges into the glass wall)
mCola = bpy.data.materials.new('mCola'); mCola.use_nodes = True; nt = mCola.node_tree; bs = nt.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value = (1, 1, 1, 1); bs.inputs['Transmission Weight'].default_value = 1; bs.inputs['IOR'].default_value = 1.34; bs.inputs['Roughness'].default_value = 0.0
va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.62, 0.22, 0.06, 1); va.inputs['Density'].default_value = 0.55
nt.links.new(va.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
LQT = GT + 19.0
COLA = [(0, LQT - 0.05), (5.0, LQT - 0.02), (6.0, LQT + 0.06), (6.28, LQT + 0.2), (6.29, LQT), (6.27, GT + 6), (6.24, GT + 2.7), (6.08, GT + 2.32), (5.6, GT + 2.17), (0, GT + 2.12)]
revolve('cola', COLA, 96, None, mat=mCola, centre=(GX, GY, 0))
mIce, nt, bs = principled('mIce', (1, 1, 1, 1), 0, 0.06, **{'Transmission Weight': 1.0, 'IOR': 1.31})
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; bm_ = nt.nodes.new('ShaderNodeBump'); bm_.inputs['Strength'].default_value = 0.15
nt.links.new(nz.outputs['Fac'], bm_.inputs['Height']); nt.links.new(bm_.outputs['Normal'], bs.inputs['Normal'])
for k, (dx, dy, dz, rx, ry, rz) in enumerate(((-1.6, 1.4, 0.9, 0.3, 0.2, 0.5), (2.0, 0.6, 0.6, -0.2, 0.4, 1.2), (0.3, -2.2, 0.4, 0.5, -0.3, 2.1),
                                               (-0.4, 0.2, -3.6, 0.9, 0.6, 0.3))):
    bpy.ops.mesh.primitive_cube_add(size=4.0, location=(GX + dx, GY + dy, LQT + dz))
    ic = bpy.context.object; ic.name = 'ice'; ic.rotation_euler = (rx, ry, rz); ic.scale = (1, 0.92, 0.85)
    bv = ic.modifiers.new('b', 'BEVEL'); bv.width = 0.55; bv.segments = 4
    bpy.ops.object.modifier_apply(modifier='b'); bpy.ops.object.shade_smooth()
    for c in ic.users_collection: c.objects.unlink(ic)
    STAGE.objects.link(ic); ic.data.materials.append(mIce)
# fizz bubbles clinging to the inside of the glass
bub_items = []
for k in range(70):
    t = RNG.uniform(0, TAU); z = RNG.uniform(GT + 2.6, LQT - 0.6); r = RNG.uniform(0.05, 0.16)
    rr = 6.24 - r * 0.6
    bub_items.append(((GX + rr * math.cos(t), GY + rr * math.sin(t), z), (-math.cos(t), -math.sin(t), 0), (-math.sin(t), math.cos(t), 0), r, r * 1.3, 1.0))
mBub, *_ = principled('mBubble', (1, 1, 1, 1), 0, 0.0, **{'Transmission Weight': 1.0, 'IOR': 0.75})
drops_mesh('glass_bubbles', bub_items, mBub)
# straw: striped paper straw, leaning toward the can
def straw_map():
    N = 256; yy, xx = np.mgrid[0:N, 0:N].astype(F32) / N
    s = ((xx + yy * 6) * 4) % 1.0; m = ss(0.46, 0.5, s) * ss(0.96, 0.92, s)
    col = lerp(np.array([0.96, 0.95, 0.92], F32) * np.ones((N, N, 1), F32), hx('d21f2b'), m)
    return img('straw_col', col)
mStraw, nt, bs = principled('mStraw', (1, 1, 1, 1), 0, 0.55); hook_maps(nt, bs, straw_map())
SL = 38.0
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.62, depth=SL, end_fill_type='NOTHING', location=(0, 0, 0))
stw = bpy.context.object; stw.name = 'straw'
uvl = stw.data.uv_layers.active.data
for p in stw.data.polygons:
    vs = [stw.data.vertices[stw.data.loops[li].vertex_index].co for li in p.loop_indices]
    us = [(math.atan2(v.y, v.x) / TAU) % 1.0 for v in vs]
    if max(us) - min(us) > 0.5: us = [u + 1 if u < 0.5 else u for u in us]
    for li, v, u in zip(p.loop_indices, vs, us): uvl[li].uv = (u, (v.z / SL + 0.5) * 7)
sol = stw.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.05
bpy.ops.object.shade_smooth()
stw.rotation_euler = (math.radians(-10), math.radians(13), 0)
_ax = stw.rotation_euler.to_matrix() @ Vector((0, 0, SL / 2))
stw.location = Vector((GX - 2.4, GY + 2.0, GT + 2.9)) + _ax          # bottom end rests on the glass floor
for c in stw.users_collection: c.objects.unlink(stw)
STAGE.objects.link(stw); stw.data.materials.append(mStraw)

# crown cap: red lacquer, 21 crimps, white KC roundel
def cap_map():
    N = 512 * TEX; yy, xx = np.mgrid[0:N, 0:N].astype(F32); c = N / 2; d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / c
    col = lerp(hx('b80d22') * np.ones((N, N, 1), F32), hx('d61a30'), ss(0.9, 0.2, d))
    ring = ss(0.66, 0.64, d) * ss(0.58, 0.60, d)
    kc = text_mask((N, N), 'KC', FONT_B, c, c, 0.36 * N, spacing=1.0)
    w = np.maximum(ring, kc)
    col = lerp(col, hx('f7f4ee'), w)
    return img('cap_col', col)
mCap, nt, bs = principled('mCap', lin('c0102a'), 0.55, 0.28, **{'Coat Weight': 0.6, 'Coat Roughness': 0.08})
hook_maps(nt, bs, cap_map())
CAPR = 3.05
CAP = [(0, 1.24), (1.5, 1.25), (2.55, 1.21), (2.8, 1.14), (2.95, 1.0), (3.02, 0.8), (3.08, 0.5), (3.16, 0.2), (3.24, 0.06), (3.27, 0.0),
       (3.2, -0.02), (3.1, 0.0)]
def cap_rmod(r, z, t, i):
    if i < 4: return r
    amp = 0.13 * ss(1.1, 0.4, z) * (1 if i < len(CAP) - 2 else 0.8)
    return r + amp * (abs(math.cos(t * 21 / 2)) ** 0.7 * 2 - 1.0)
cap = revolve('crown_cap', CAP, 168, ('planar', 3.3), mat=mCap, rmod=cap_rmod)
cap.location = (13.5, 3.5, TZ + 0.02); cap.rotation_euler = (math.radians(3), math.radians(-2), math.radians(30))


# ================================================================ triangle count (stage only)
def tri_count(coll):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in coll.all_objects:
        if o.type != 'MESH': continue
        ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles(); n += len(me.loop_triangles); ev.to_mesh_clear()
    return n
TRIS = tri_count(STAGE)
if 'norender' in sys.argv:
    dg = bpy.context.evaluated_depsgraph_get(); per = []
    for o in STAGE.all_objects:
        if o.type != 'MESH': continue
        ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles(); per.append((len(me.loop_triangles), o.name)); ev.to_mesh_clear()
    log(sorted(per, reverse=True)[:12])
log('stage triangles', TRIS)


# ================================================================ characters + masks (as stage_render.py)
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHAR_DIR, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots
CHARS = []
def add_characters():
    stance = None; RIGS = []
    def sumo(f, pos, face, scale=1.65):
        nonlocal stance
        new, roots = load(f); CHARS.extend(new)
        rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
        if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
        elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
        for r in roots:
            r.location = (pos[0], pos[1], 0.0); r.scale = (scale,) * 3
            r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))
    A, B = (-1.0, -0.15), (1.0, 0.15)
    sumo('sumo2_stance.glb', A, B); sumo('sumo2_red.glb', B, A)
    new, gr = load('gyoji.glb'); CHARS.extend(new)
    GP = (0.4, 4.68)
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
            o.matrix_world = Bm @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world; CHARS.append(o)
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


# ================================================================ lights, world, cameras, render
def setup_lights():
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world; nt = world.node_tree
    bg = nt.nodes['Background']; env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(HDRI_ROT))
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
    sun.data.energy = 5.0; sun.data.angle = math.radians(2.5); sun.data.color = (1.0, 0.985, 0.96)
    d = Vector((0.33, -0.78, -0.53)).normalized(); sun.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    key = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'AREA')); scn.collection.objects.link(key)
    key.data.shape = 'DISK'; key.data.size = 30; key.data.energy = 2.4e4; key.data.color = (1.0, 0.76, 0.52)
    key.location = (42, -40, 38); key.rotation_euler = (Vector((0, 0, 0)) - key.location).to_track_quat('-Z', 'Y').to_euler()

def cam_setup(shot):
    cam = bpy.data.objects.get('Cam')
    if not cam:
        cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.dof.use_dof = False; cam.data.clip_end = 2000; cam.data.type = 'PERSP'
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
        aim((10.0, -9.5, 3.4), (0, 0.6, -0.4), 31, 4.0, (0, 0, 1.2))
    elif shot == 'tab':
        aim((-2.6, -5.6, 2.6), (0.05, -0.75, 0.0), 36, 4.0, (0, -1.2, 0.03))
    elif shot == 'top':      # debug: orthographic top view of the tab
        aim((0, 0.1, 6), (0, 0.1, 0), 30); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 6.0
        cam.rotation_euler = (0, 0, 0)
    elif shot == 'can':
        aim((40, -44, -3.0), (-3.0, 2.0, -8.5), 42, 8.0, (0, -6.2, -10))

def render(shot):
    cam_setup(shot)
    scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'
    scn.cycles.samples = 16 if FAST else 48; scn.cycles.use_denoising = True; scn.cycles.use_adaptive_sampling = True
    scn.cycles.max_bounces = 10; scn.cycles.glossy_bounces = 5; scn.cycles.transmission_bounces = 10; scn.cycles.transparent_max_bounces = 8
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

# ================================================================ export (stage only, textures <= 1024)
if 'noexport' not in sys.argv:
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in STAGE.all_objects: o.select_set(True)
    for im in IMGS:
        w, h = im.size
        if max(w, h) > 1024:
            k = 1024 / max(w, h); im.scale(max(1, int(w * k)), max(1, int(h * k)))
        im.file_format = 'PNG'; im.pack()
    glb = os.path.join(OUT, 'can.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_image_format='AUTO')
    log('exported', glb, '%.1f MB' % (os.path.getsize(glb) / 1e6), 'tris', TRIS)
