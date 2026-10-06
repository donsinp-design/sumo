# "DJ VINYL" stage, fully modelled: two sumos fight on a spinning record on a giant direct-drive DJ turntable in a
# dark club. Built entirely by script (Blender 4.2, run headless).
#   python tools/blender/stage_vinyl.py [out_dir] [chars_dir] [shot=game shot=low] [samples=64] [pct=100] [noren] [nochars]
# Writes <out_dir>/vinyl.glb (the stage only: Z up in Blender, metres, origin at the record centre, top of the record at
# Z=0, front facing -Y) and renders <out_dir>/ex_game.png (the game camera) and <out_dir>/ex_low.png (low three-quarter)
# with the game's characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in masks.
# Layout (top view, camera on -Y): the deck's platter is centred on the origin; the tonearm stands back-right with its
# headshell resting on the record's front-right edge; pitch slider front-right, start/stop front-left, 45 adaptor
# back-left; the mixer to the right, a second deck to the left, speaker stacks behind the booth, a dark club around.
# The glb carries only image textures (numpy-painted, <=1024 px); the renders add Cycles-only touches on top (radial
# anisotropy on the vinyl and the platter, brushed anisotropy on the plinth, haze, lasers, bloom).
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in ('noren', 'nochars') and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'vinyl')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SHOTS = set(a.split('=', 1)[1] for a in sys.argv if a.startswith('shot=')) or {'game', 'low'}
SAMPLES = int(OPT.get('samples', 64)); PCT = int(OPT.get('pct', 100))
NOREN = 'noren' in sys.argv; NOCHARS = 'nochars' in sys.argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi
RNG = np.random.default_rng(11)


def ring_r():
    try:
        txt = open(os.path.join(HERE, '..', '..', 'public', 'js', 'config.js')).read()
        return float(re.search(r'S\.RING_R\s*=\s*([\d.]+)', txt).group(1))
    except Exception:
        return 4.6


R = ring_r()          # fighting circle (white line on the record)
RD = R + 0.7          # record radius
PL_TOP = -0.55        # plinth top
TABLE = -2.75         # booth table top


# ================================================================ helpers
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


STAGE = []
def obj(name, me, mats=(), stage=True, loc=None, rot=None):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    for m in mats: me.materials.append(m)
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = rot
    if stage: STAGE.append(o)
    return o
def bm_obj(name, bm, mats=(), smooth=40, **kw):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    return obj(name, me, mats, **kw)
def apply_mods(o, smooth=None):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    o.modifiers.clear(); o.data = me
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    return o
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0


def planar_uv(me, S, cx=0.0, cy=0.0):
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for l in me.loops:
        co = me.vertices[l.vertex_index].co; uv.data[l.index].uv = ((co.x - cx) / (2 * S) + 0.5, (co.y - cy) / (2 * S) + 0.5)
def box_uv(o, tile=6.0):
    me = o.data; uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    W = o.matrix_world
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = W @ me.vertices[me.loops[li].vertex_index].co
            u, v = (co.x, co.y) if ax == 2 else (co.y, co.z) if ax == 0 else (co.x, co.z)
            uv.data[li].uv = (u / tile, v / tile)


def lathe(name, prof, mats, segs=128, loc=(0, 0, 0), rot=None, mod=None, mi=None, uvS=None, smooth=40, stage=True):
    """Profile [(r, z)] traversed top-inside -> outside -> down -> bottom-inside (normals face out); r == 0 is a pole.
    mod(a, r, z) scales the radius (knurls); mi[k] is the material index of segment k."""
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        if r < 1e-6: rings.append([bm.verts.new((0, 0, z))]); continue
        ring = []
        for i in range(segs):
            a = TAU * i / segs; rr = r * (mod(a, r, z) if mod else 1.0)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
        if len(A) == 1 and len(B) == 1: continue
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1: f = bm.faces.new((A[0], B[i], B[j]))
            elif len(B) == 1: f = bm.faces.new((A[i], B[0], A[j]))
            else: f = bm.faces.new((A[i], B[i], B[j], A[j]))
            if mi: f.material_index = mi[k]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    planar_uv(me, uvS or max(r for r, _ in prof))
    return obj(name, me, mats, stage=stage, loc=loc, rot=rot)


def rrect(x0, x1, y0, y1, rc, cseg=6):
    rc = max(0.0, min(rc, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4))
    if rc <= 0: return [(x1, y1), (x0, y1), (x0, y0), (x1, y0)][::-1]
    pts = []
    for cx, cy, a0 in ((x1 - rc, y0 + rc, -90), (x1 - rc, y1 - rc, 0), (x0 + rc, y1 - rc, 90), (x0 + rc, y0 + rc, 180)):
        for k in range(cseg + 1):
            a = math.radians(a0 + 90 * k / cseg); pts.append((cx + rc * math.cos(a), cy + rc * math.sin(a)))
    return pts
def rbox(name, x0, x1, y0, y1, z0, z1, mat, rc=0.15, bev=0.04, bseg=3, cseg=6, loc=None, rot=None, uv=6.0, stage=True,
         taper=0.0, holes=()):
    """Rounded-corner slab with a crisp bevel round its top and bottom rims. taper shrinks the top outline inwards.
    holes: [(kind, x, y, r or (w,h), depth)] cut by boolean from the top or front face (kind 'cylz'/'cyly'/'boxy')."""
    bm = bmesh.new()
    pb = rrect(x0, x1, y0, y1, rc, cseg); pt = rrect(x0 + taper, x1 - taper, y0 + taper, y1 - taper, max(0, rc - taper), cseg)
    B = [bm.verts.new((x, y, z0)) for x, y in pb]; T = [bm.verts.new((x, y, z1)) for x, y in pt]
    bm.faces.new(T); bm.faces.new(B[::-1])
    for i in range(len(B)):
        j = (i + 1) % len(B); bm.faces.new((B[i], B[j], T[j], T[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = obj(name, me, [mat] if mat else [], stage=stage)
    if bev > 0:
        b = o.modifiers.new('bev', 'BEVEL'); b.width = bev; b.segments = bseg; b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(30); b.miter_outer = 'MITER_ARC'
    cutters = []
    for kind, hx, hy, hr, hd in holes:
        if kind == 'cyly':
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=hr, depth=hd * 2, location=(hx, y0, hy), rotation=(math.pi / 2, 0, 0))
        elif kind == 'boxy':
            bpy.ops.mesh.primitive_cube_add(size=1, location=(hx, y0, hy)); bpy.context.object.scale = (hr[0], hd * 2, hr[1])
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=hr, depth=hd * 2, location=(hx, hy, z1))
        c = bpy.context.object; c.hide_render = True; cutters.append(c)
        m = o.modifiers.new('cut', 'BOOLEAN'); m.object = c; m.operation = 'DIFFERENCE'; m.solver = 'EXACT'
    apply_mods(o, smooth=40)
    for c in cutters: bpy.data.objects.remove(c)
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = rot
    if uv: box_uv(o, uv)
    return o


def curve_mesh(name, pts, radius, mat, res=16, bres=4, stage=True, handles='AUTO', tilt=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = radius; cu.bevel_resolution = bres
    cu.resolution_u = res; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = handles
    tmp = bpy.data.objects.new(name + '_c', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    me.materials.clear(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(50))
    return obj(name, me, [mat], stage=stage)


def text_mesh(name, body, size, mat, loc, rot_z=0.0, extrude=0.002, align='CENTER', font=None, bold=0.0, stage=True):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = 'CENTER'; cu.offset = bold; cu.resolution_u = 4
    if font: cu.font = font
    tmp = bpy.data.objects.new(name + '_t', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    me.materials.clear()
    return obj(name, me, [mat], stage=stage, loc=(loc[0], loc[1], loc[2] + extrude), rot=(0, 0, rot_z))


# ---------------------------------------------------------------- images & materials
def image(name, arr, data=False):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    h, w = arr.shape[:2]; rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False); im.pixels.foreach_set(rgba.ravel())
    if data: im.colorspace_settings.name = 'Non-Color'
    im.file_format = 'PNG'; im.pack(); return im
def normal_from_h(h, strength):
    gy, gx = np.gradient(h); n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True); return n * 0.5 + 0.5


BSDF = {}
def mat(name, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tcol=None, trough=None, tnrm=None, nstr=1.0, emit=None, estr=0.0,
        coat=0.0, coat_r=0.05, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']; BSDF[name] = bs
    bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal; bs.inputs['Specular IOR Level'].default_value = spec
    if coat: bs.inputs['Coat Weight'].default_value = coat; bs.inputs['Coat Roughness'].default_value = coat_r
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


N = 1024
def tex_brushed(seed, base=0.27, amp=0.07):
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((N, N)).astype(np.float32)
    k = np.zeros(N, np.float32); k[:90] = 1; k = np.roll(k, -45); K = np.fft.rfft(k)
    a = np.fft.irfft(np.fft.rfft(a, axis=1) * K, n=N, axis=1)            # long streaks along u
    a = (a + np.roll(a, 1, 0) * 0.5 + np.roll(a, -1, 0) * 0.5) / 2
    a /= a.std() * 3
    for _ in range(60):   # a few longer, brighter scratches
        y = rng.integers(0, N); x0 = rng.integers(0, N); L = rng.integers(80, 400)
        a[y, np.arange(x0, x0 + L) % N] += rng.uniform(0.3, 0.8)
    rough = np.clip(base + amp * a, 0.05, 1)
    nrm = normal_from_h(a * 0.6, 1.0)
    return rough, nrm


def tex_vinyl():
    S = RD + 0.05; xs = (np.arange(N) + 0.5) / N * 2 * S - S
    X, Y = np.meshgrid(xs, xs); r = np.hypot(X, Y)
    rr = np.linspace(0, S, 6000)
    music = np.zeros_like(rr)
    for f, w in ((3, 0.5), (9, 0.3), (27, 0.25), (80, 0.18), (240, 0.12), (700, 0.08)):
        music += w * np.sin(rr * f + RNG.uniform(0, TAU)) * RNG.uniform(0.6, 1.0)
    music += np.convolve(RNG.standard_normal(rr.size), np.ones(9) / 9, 'same') * 0.35
    music = (music - music.min()) / (music.max() - music.min())
    m = np.interp(r, rr, music)
    groove = (r > 1.98) & (r < 5.1)
    gaps = np.zeros_like(r)
    for g in (4.16, 3.58, 3.05, 2.52):
        gaps = np.maximum(gaps, 1 - sstep(0.03, 0.045, np.abs(r - g)))
    gr = sstep(1.96, 2.0, r) * (1 - sstep(5.08, 5.12, r))      # 1 inside the grooved area
    line = 1 - sstep(0.035, 0.045, np.abs(r - R))
    # fine ring ripple (several px period, a moire-free stand-in for the groove pitch) modulated by the music
    ripple = 0.5 + 0.5 * np.sin(r * TAU / 0.022)
    col = 0.030 + 0.016 * m * gr * (1 - gaps) + 0.004 * ripple * gr
    col = col * (1 - line) + 0.86 * line
    rough = (0.34 + 0.08 * m) * gr * (1 - gaps) + 0.12 * (gaps * gr + (1 - gr))
    rough = rough * (1 - line) + 0.42 * line
    h = (ripple * 0.25 + m * 0.6) * gr * (1 - gaps) - 0.6 * gaps * gr + 0.6 * line
    return np.clip(col, 0, 1), rough, normal_from_h(h, 1.6)


def tex_label():
    S = 1.75; xs = (np.arange(N) + 0.5) / N * 2 * S - S
    X, Y = np.meshgrid(xs, xs); r = np.hypot(X, Y)
    base = np.array([0.80, 0.14, 0.11], np.float32)
    noise = RNG.standard_normal((N, N)).astype(np.float32) * 0.012
    col = base[None, None, :] * (1 - 0.06 * sstep(0.5, 1.75, r))[..., None] + noise[..., None]
    for rad, w, c in ((1.62, 0.010, (0.95, 0.92, 0.85)), (1.55, 0.004, (0.95, 0.92, 0.85)), (0.42, 0.006, (0.95, 0.92, 0.85))):
        k = (1 - sstep(w, w + 0.006, np.abs(r - rad)))[..., None]; col = col * (1 - k) + np.array(c) * k
    rough = 0.5 + noise * 4
    return np.clip(col, 0, 1), rough


# ---------------------------------------------------------------- materials
print('painting textures'); sys.stdout.flush()
br_r, br_n = tex_brushed(1)
ALU = mat('Aluminium', lin('c9cbcf'), 0.27, 1.0, trough=image('alu_rough', br_r, True), tnrm=image('alu_n', br_n, True), nstr=0.35)
ALU_RIM = mat('PlatterAlu', lin('d6d8dc'), 0.16, 1.0, trough=image('alu_rough', br_r, True), nstr=0.2)
CHROME = mat('Chrome', lin('e8e9ec'), 0.07, 1.0)
DARKMET = mat('DarkAnodised', lin('2a2b2f'), 0.33, 1.0, trough=image('dark_rough', np.clip(br_r + 0.06, 0, 1), True),
              tnrm=image('alu_n', br_n, True), nstr=0.3)
BLACK = mat('SatinBlack', lin('121214'), 0.42, 0.0, spec=0.5)
GLOSSBLACK = mat('GlossBlack', lin('0b0b0d'), 0.12, 0.0, coat=0.6, coat_r=0.04)
RUBBER = mat('Rubber', lin('101011'), 0.72, 0.0, spec=0.35)
KNOB = mat('KnobRubber', lin('17171a'), 0.55, 0.0)
INK = mat('WhiteInk', lin('ecebe6'), 0.45)
vc, vr, vn = tex_vinyl()
VINYL = mat('Vinyl', (0.02, 0.02, 0.02), 0.3, 0.0, tcol=image('vinyl_col', vc), trough=image('vinyl_rough', vr, True),
            tnrm=image('vinyl_n', vn, True), nstr=0.6, spec=0.55)
lc, lr = tex_label()
LABEL = mat('Label', lin('c8231d'), 0.5, tcol=image('label_col', lc), trough=image('label_rough', lr, True), coat=0.25, coat_r=0.25)
LABEL_INK = mat('LabelInk', lin('f4efe2'), 0.38)
ORANGE_LED = mat('LedOrange', lin('ff7a1a'), 0.3, emit=lin('ff6a10'), estr=18)
GREEN_LED = mat('LedGreen', lin('3aff6a'), 0.3, emit=lin('2aff5a'), estr=10)
WHITE_LAMP = mat('LampWhite', lin('ffffff'), 0.2, emit=lin('fff2dc'), estr=25)
RED_ACC = mat('RedAccent', lin('b81c1c'), 0.35, coat=0.5)
CONE = mat('ConePaper', lin('1a1a1c'), 0.78, spec=0.3)
DUSTCAP = mat('DustCap', lin('202024'), 0.3, coat=0.4)
LAMINATE = mat('BoothLaminate', lin('0e0e10'), 0.3, coat=0.3, coat_r=0.15)
FLOOR = mat('ClubFloor', lin('0a0a0c'), 0.22, spec=0.6)
PADS = [mat('Pad' + n, lin(c), 0.55, emit=lin(c), estr=6) for n, c in
        (('Magenta', 'ff2ab4'), ('Cyan', '1ad8ff'), ('Amber', 'ffb21a'), ('Violet', '8a4aff'))]
PAD_OFF = mat('PadOff', lin('2a2a30'), 0.6)
SCREEN = mat('Screen', lin('050608'), 0.05, coat=1.0, coat_r=0.02)
SCREEN_TXT = mat('ScreenText', lin('3ae0ff'), 0.3, emit=lin('3ae0ff'), estr=8)
VU = {c: mat('Vu' + c, lin(h), 0.3, emit=lin(h), estr=9) for c, h in (('G', '3aff5a'), ('Y', 'ffd21a'), ('R', 'ff2a1a'))}
VU_OFF = mat('VuOff', lin('1a1d1a'), 0.3)
CABLE = mat('Cable', lin('0d0d0f'), 0.45, coat=0.2, coat_r=0.3)
RCA_RED = mat('RcaRed', lin('c41a1a'), 0.35, coat=0.5)
RCA_WHITE = mat('RcaWhite', lin('d8d8d4'), 0.35, coat=0.5)
GOLD = mat('Gold', lin('e6b04a'), 0.2, 1.0)

FONT = None
for f in ('/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf', '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'):
    if os.path.exists(f): FONT = bpy.data.fonts.load(f); break
FONT_B = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf') if os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf') else FONT


# ================================================================ the deck
def knurl(n, depth):
    return lambda a, r, z: 1.0 + depth * (1 if math.cos(a * n) > 0 else -1) * 0.5


def build_deck(prefix, ox=0.0, ring_line=True):
    parts = []
    P = lambda o: (parts.append(o), o)[1]
    # plinth: aluminium top plate with a crisp bevel over a satin black body, on four big feet
    x0, x1, y0, y1 = -6.8, 9.0, -6.25, 6.25
    P(rbox(prefix + 'PlinthTop', x0, x1, y0, y1, PL_TOP - 0.32, PL_TOP, ALU, rc=0.35, bev=0.07, bseg=4))
    P(rbox(prefix + 'PlinthBody', x0 + 0.06, x1 - 0.06, y0 + 0.06, y1 - 0.06, TABLE + 0.32, PL_TOP - 0.32, BLACK, rc=0.3, bev=0.05))
    for fx, fy in ((x0 + 1.4, y0 + 1.4), (x1 - 1.4, y0 + 1.4), (x0 + 1.4, y1 - 1.4), (x1 - 1.4, y1 - 1.4)):
        P(lathe(prefix + 'Foot', [(0, TABLE + 0.32), (0.95, TABLE + 0.32), (1.0, TABLE + 0.28), (1.0, TABLE + 0.18), (1.06, TABLE + 0.12),
                                (1.06, TABLE + 0.02), (1.0, TABLE), (0, TABLE)], [RUBBER, ALU], 48, loc=(fx, fy, 0), mi=[0, 0, 1, 1, 0, 0, 0]))
    # platter: aluminium with the strobe dots on its side
    prof = [(0, -0.10), (5.5, -0.10), (5.56, -0.115), (5.60, -0.17), (5.66, -0.48), (5.62, -0.515), (5.3, -0.53), (0, -0.53)]
    P(lathe(prefix + 'Platter', prof, [ALU_RIM], 256))
    bm = bmesh.new()
    for row, (zc, cnt) in enumerate(((-0.215, 183), (-0.295, 180), (-0.375, 186), (-0.445, 177))):
        rr = 5.60 + (-(zc + 0.17)) / 0.31 * 0.06
        for k in range(cnt):
            a = TAU * (k + 0.5 * row) / cnt; c, s = math.cos(a), math.sin(a)
            hw, hh, d = 0.045, 0.026, 0.028
            vs = []
            for (t, zz, out) in ((-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0), (-hw, -hh, d), (hw, -hh, d), (hw, hh, d), (-hw, hh, d)):
                rad = rr - 0.01 + out
                vs.append(bm.verts.new((rad * c - t * s, rad * s + t * c, zc + zz)))
            for f in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
                bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    P(bm_obj(prefix + 'StrobeDots', bm, [ALU_RIM], smooth=0))
    # record: black vinyl with a beaded rim; label (red, KUMITE) and spindle
    P(lathe(prefix + 'Record', [(0.14, 0.0), (5.16, 0.0), (5.23, 0.014), (5.285, 0.01), (RD, -0.02), (5.29, -0.085), (5.24, -0.1),
                               (0.14, -0.1), (0.14, 0.0)], [VINYL], 384, uvS=RD + 0.05, smooth=50))
    P(lathe(prefix + 'Label', [(0, 0.004), (1.745, 0.004), (1.75, 0.0)], [LABEL], 160, uvS=1.75))
    P(text_mesh(prefix + 'LabelKumite', 'KUMITE', 0.62, LABEL_INK, (0, 0.62, 0.004), font=FONT, bold=0.012))
    P(text_mesh(prefix + 'LabelKanji', '組手', 0.36, LABEL_INK, (0, -0.62, 0.004), font=FONT, bold=0.006))
    P(text_mesh(prefix + 'LabelRpm', '33 1/3 RPM', 0.17, LABEL_INK, (0, -1.08, 0.004), font=FONT))
    P(text_mesh(prefix + 'LabelSide', 'SIDE A', 0.15, LABEL_INK, (-1.05, 0.0, 0.004), font=FONT))
    P(text_mesh(prefix + 'LabelBpm', '128 BPM', 0.15, LABEL_INK, (1.08, 0.0, 0.004), font=FONT))
    P(lathe(prefix + 'Spindle', [(0, 0.24), (0.06, 0.235), (0.1, 0.205), (0.115, 0.16), (0.115, -0.1)], [CHROME], 48))

    # ---------------- tonearm (pivot back-right, headshell resting on the record's front-right edge)
    Pv = Vector((6.6, 3.8, 0)); Nd = Vector((3.52, -3.69, 0))
    d = (Nd - Pv).normalized(); n = Vector((-d.y, d.x, 0))      # n: left of d (away from the spindle)
    ZA = 0.78                                                   # arm tube height
    P(lathe(prefix + 'ArmBase', [(0, PL_TOP + 0.08), (1.25, PL_TOP + 0.08), (1.3, PL_TOP + 0.04), (1.3, PL_TOP)], [ALU], 96, loc=Pv,
            mod=None))
    P(lathe(prefix + 'ArmHeightRing', [(0, -0.16), (0.95, -0.16), (1.0, -0.2), (1.0, -0.42), (0, -0.42)], [DARKMET], 120, loc=Pv,
            mod=lambda a, r, z: 1.0 + (0.025 if math.cos(a * 60) > 0 else 0.0) * (1 if -0.4 < z < -0.18 else 0)))
    P(lathe(prefix + 'ArmPillar', [(0, 0.42), (0.5, 0.42), (0.55, 0.38), (0.55, -0.17), (0, -0.17)], [ALU], 64, loc=Pv))
    P(lathe(prefix + 'ArmGimbalCap', [(0, 1.12), (0.25, 1.1), (0.42, 1.02), (0.46, 0.92), (0.46, 0.42), (0, 0.42)], [BLACK], 64, loc=Pv))
    # gimbal axle across the arm, the arm tube (rear stub + S-curve), the counterweight
    ang = math.atan2(d.y, d.x)
    P(lathe(prefix + 'GimbalAxle', [(0, 0.62), (0.16, 0.62), (0.2, 0.58), (0.2, -0.58), (0.16, -0.62), (0, -0.62)], [CHROME], 32,
            loc=(Pv.x, Pv.y, ZA), rot=(math.pi / 2, 0, ang)))
    hs_ang = math.radians(-22)                                  # headshell offset, turned toward the spindle
    h = Vector((d.x * math.cos(hs_ang) - d.y * math.sin(hs_ang), d.x * math.sin(hs_ang) + d.y * math.cos(hs_ang), 0))
    J = Nd - h * 1.25                                           # headshell collar
    L = (J - Pv).length
    dl = Vector((d.x * math.cos(0.16) - d.y * math.sin(0.16), d.x * math.sin(0.16) + d.y * math.cos(0.16), 0))
    tube = [Pv - d * 1.0, Pv + dl * L * 0.35, J - h * L * 0.28, J]
    P(curve_mesh(prefix + 'ArmTube', [Vector((p.x, p.y, ZA if i < 3 else ZA - 0.06)) for i, p in enumerate(tube)], 0.105, CHROME, res=24))
    cw = Pv - d * 1.05
    P(lathe(prefix + 'ArmStub', [(0, 1.15), (0.13, 1.15), (0.13, 0.0), (0, 0.0)], [CHROME], 24, loc=(cw.x, cw.y, ZA),
            rot=(Vector((-d.x, -d.y, 0)).to_track_quat('Z', 'Y').to_euler())))
    cwp = Pv - d * 1.35
    P(lathe(prefix + 'Counterweight', [(0, 1.0), (0.42, 1.0), (0.5, 0.95), (0.52, 0.85), (0.52, 0.35), (0.56, 0.32), (0.56, 0.06),
                                      (0.5, 0.0), (0.2, -0.02), (0, -0.02)], [ALU, DARKMET, BLACK], 96,
            loc=(cwp.x, cwp.y, ZA), rot=(Vector((-d.x, -d.y, 0)).to_track_quat('Z', 'Y').to_euler()),
            mod=lambda a, r, z: 1.0 + (0.03 if math.cos(a * 48) > 0 else 0.0) * (1 if 0.4 < z < 0.84 else 0),
            mi=[0, 0, 0, 0, 2, 2, 2, 0, 0]))
    # headshell: a slim shell with a finger lift, the collar, a cartridge with a red stripe, the stylus
    hrot = (0, 0, math.atan2(h.y, h.x))
    HC = Nd - h * 0.55
    P(rbox(prefix + 'Headshell', -0.8, 0.8, -0.34, 0.34, ZA - 0.2, ZA - 0.12, ALU, rc=0.14, bev=0.025, bseg=2, loc=(HC.x, HC.y, 0), rot=hrot))
    P(lathe(prefix + 'Collar', [(0, 0.34), (0.15, 0.34), (0.19, 0.3), (0.19, 0.03), (0.15, 0.0), (0, 0.0)], [DARKMET], 48,
            loc=(J.x - h.x * 0.17, J.y - h.y * 0.17, ZA - 0.06), rot=h.to_track_quat('Z', 'Y').to_euler(),
            mod=lambda a, r, z: 1.0 + (0.04 if math.cos(a * 24) > 0 else 0.0) * (1 if 0.04 < z < 0.3 else 0)))
    fl0 = HC + h * 0.55 + Vector((-h.y, h.x, 0)) * 0.3
    P(curve_mesh(prefix + 'FingerLift', [Vector((fl0.x, fl0.y, ZA - 0.16)), Vector((fl0.x - h.y * 0.45 + h.x * 0.15, fl0.y + h.x * 0.45 + h.y * 0.15, ZA - 0.12)),
                                         Vector((fl0.x - h.y * 0.75 + h.x * 0.05, fl0.y + h.x * 0.75 + h.y * 0.05, ZA + 0.02))], 0.04, ALU, res=12))
    CC = Nd - h * 0.36
    P(rbox(prefix + 'Cartridge', -0.42, 0.42, -0.27, 0.27, 0.13, ZA - 0.2, BLACK, rc=0.06, bev=0.03, bseg=2, taper=0.03,
           loc=(CC.x, CC.y, 0), rot=hrot))
    P(rbox(prefix + 'CartStripe', -0.43, 0.43, -0.12, 0.12, ZA - 0.32, ZA - 0.24, RED_ACC, rc=0.02, bev=0.01, bseg=1,
           loc=(CC.x, CC.y, 0), rot=hrot))
    P(curve_mesh(prefix + 'Cantilever', [Vector((Nd.x - h.x * 0.12, Nd.y - h.y * 0.12, 0.16)), Vector((Nd.x, Nd.y, 0.03))], 0.012, GOLD, res=2, handles='VECTOR'))
    # arm rest with its clip, cue lever, anti-skate dial
    P(lathe(prefix + 'ArmRest', [(0, 0.55), (0.2, 0.55), (0.2, 0.25), (0.13, 0.22), (0.13, PL_TOP), (0, PL_TOP)], [ALU, RUBBER], 32,
            loc=(8.25, -0.9, 0), mi=[1, 1, 1, 0, 0]))
    P(rbox(prefix + 'ArmRestCup', -0.25, 0.25, -0.12, 0.12, 0.55, 0.68, RUBBER, rc=0.05, bev=0.02, loc=(8.25, -0.9, 0), rot=(0, 0, 0.4)))
    P(rbox(prefix + 'CueBase', -0.3, 0.3, -0.45, 0.45, PL_TOP, PL_TOP + 0.25, BLACK, rc=0.1, bev=0.03, loc=(8.35, 1.3, 0)))
    P(curve_mesh(prefix + 'CueLever', [Vector((8.35, 1.3, PL_TOP + 0.2)), Vector((8.1, 0.95, PL_TOP + 0.6))], 0.05, CHROME, res=2, handles='VECTOR'))
    P(lathe(prefix + 'CueTip', [(0, 0.14), (0.1, 0.12), (0.14, 0.0), (0.1, -0.12), (0, -0.14)], [BLACK], 24, loc=(8.1, 0.95, PL_TOP + 0.64)))
    ask = Pv + Vector((1.15, -1.0, 0))
    P(lathe(prefix + 'AntiSkate', [(0, 0.12), (0.3, 0.12), (0.35, 0.08), (0.35, 0.0), (0, 0.0)], [DARKMET], 48,
            loc=(ask.x, ask.y, PL_TOP), mod=lambda a, r, z: 1.0 + (0.03 if math.cos(a * 30) > 0 else 0) * (1 if z < 0.09 else 0)))
    P(rbox(prefix + 'AntiSkateMark', -0.02, 0.02, 0.0, 0.3, PL_TOP + 0.12, PL_TOP + 0.13, INK, rc=0, bev=0, loc=(ask.x, ask.y, 0), rot=(0, 0, 0.7)))

    # ---------------- controls on the plinth
    P(rbox(prefix + 'StartStop', -6.35, -4.95, -5.75, -4.8, PL_TOP - 0.02, PL_TOP + 0.14, BLACK, rc=0.12, bev=0.035))
    P(text_mesh(prefix + 'StartTxt', 'START/STOP', 0.17, INK, (-5.65, -5.27, PL_TOP + 0.14), font=FONT_B, extrude=0.003))
    for i, (bx_, lbl) in enumerate(((-4.3, '33'), (-3.25, '45'))):
        P(rbox(prefix + 'Speed' + lbl, bx_ - 0.42, bx_ + 0.42, -5.9, -5.4, PL_TOP - 0.02, PL_TOP + 0.1, ALU, rc=0.08, bev=0.025))
        P(text_mesh(prefix + 'SpeedTxt' + lbl, lbl, 0.2, BLACK, (bx_, -5.65, PL_TOP + 0.1), font=FONT_B, extrude=0.003))
        P(lathe(prefix + 'SpeedLed' + lbl, [(0, 0.03), (0.05, 0.02), (0.06, 0.0)], [ORANGE_LED if i == 0 else BLACK], 16,
                loc=(bx_, -5.25, PL_TOP)))
    # power dial and the strobe lamp beside the platter
    P(lathe(prefix + 'PowerDial', [(0, 0.28), (0.38, 0.28), (0.44, 0.22), (0.46, 0.0), (0, 0.0)], [ALU], 64, loc=(-6.0, -3.6, PL_TOP),
            mod=lambda a, r, z: 1.0 + (0.025 if math.cos(a * 40) > 0 else 0) * (1 if z < 0.21 else 0)))
    P(rbox(prefix + 'PowerMark', -0.03, 0.03, 0.0, 0.32, PL_TOP + 0.28, PL_TOP + 0.29, ORANGE_LED, rc=0, bev=0, loc=(-6.0, -3.6, 0), rot=(0, 0, 0.6)))
    sl = Vector((-4.35, -4.3, 0)); sla = math.atan2(-sl.y, -sl.x)
    P(lathe(prefix + 'StrobeLamp', [(0, 0.5), (0.3, 0.5), (0.34, 0.45), (0.34, 0.0), (0, 0.0)], [ALU], 48, loc=(sl.x, sl.y, PL_TOP)))
    P(rbox(prefix + 'StrobeLens', -0.05, 0.05, -0.2, 0.2, PL_TOP + 0.1, PL_TOP + 0.36, ORANGE_LED, rc=0.03, bev=0.01,
           loc=(sl.x + math.cos(sla) * 0.31, sl.y + math.sin(sla) * 0.31, 0), rot=(0, 0, sla)))
    # pitch slider: a long slot, the fader cap, tick marks and the zero LED
    px = 8.0
    P(rbox(prefix + 'PitchSlot', px - 0.12, px + 0.12, -5.7, -1.7, PL_TOP - 0.04, PL_TOP + 0.005, GLOSSBLACK, rc=0.1, bev=0.0))
    P(rbox(prefix + 'PitchCap', px - 0.36, px + 0.36, -3.95, -3.35, PL_TOP, PL_TOP + 0.32, BLACK, rc=0.06, bev=0.04, taper=0.04))
    P(rbox(prefix + 'PitchCapLine', px - 0.34, px + 0.34, -3.67, -3.63, PL_TOP + 0.32, PL_TOP + 0.33, INK, rc=0, bev=0))
    bm = bmesh.new()
    for k in range(17):
        y = -5.5 + k * 3.6 / 16; w = 0.28 if k % 4 == 0 else 0.16
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((px - 0.32 - w / 2, y, PL_TOP + 0.003)) @ Matrix.Diagonal((w, 0.035, 0.006, 1)))
    P(bm_obj(prefix + 'PitchTicks', bm, [INK], smooth=0))
    P(lathe(prefix + 'PitchZeroLed', [(0, 0.04), (0.06, 0.03), (0.07, 0.0)], [GREEN_LED], 16, loc=(px + 0.4, -3.6, PL_TOP)))
    P(text_mesh(prefix + 'PitchTxt', 'PITCH', 0.16, INK, (px, -6.0, PL_TOP), font=FONT_B, extrude=0.002))
    # target light: a pop-up lamp aimed at the needle
    P(lathe(prefix + 'TargetPost', [(0, 0.55), (0.1, 0.55), (0.1, 0.0), (0, 0.0)], [CHROME], 16, loc=(5.6, -5.0, PL_TOP)))
    tla = math.atan2(Nd.y + 5.0, Nd.x - 5.6)
    P(lathe(prefix + 'TargetHead', [(0, 0.3), (0.13, 0.3), (0.15, 0.27), (0.15, 0.0), (0, 0.0)], [BLACK, WHITE_LAMP], 24,
            loc=(5.6, -5.0, PL_TOP + 0.62), rot=Vector((math.cos(tla), math.sin(tla), -0.6)).to_track_quat('-Z', 'Y').to_euler(), mi=[0, 0, 0, 1]))
    # 45 adaptor in its well at the back-left
    aw = Vector((-5.55, 5.05, 0))
    P(lathe(prefix + 'AdaptorWell', [(0, PL_TOP + 0.003), (0.92, PL_TOP + 0.003), (0.95, PL_TOP - 0.0)], [GLOSSBLACK], 64, loc=aw))
    P(lathe(prefix + 'Adaptor', [(0.62, 0.16), (0.82, 0.16), (0.86, 0.12), (0.86, 0.0), (0.6, 0.0), (0.6, 0.16)], [ALU], 96,
            loc=(aw.x, aw.y, PL_TOP + 0.003), smooth=50))
    P(lathe(prefix + 'AdaptorHub', [(0.12, 0.26), (0.24, 0.26), (0.27, 0.22), (0.27, 0.0), (0.12, 0.0), (0.12, 0.26)], [ALU], 48,
            loc=(aw.x, aw.y, PL_TOP + 0.003)))
    bm = bmesh.new()
    for k in range(3):
        a = TAU * k / 3 + 0.3
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((aw.x + math.cos(a) * 0.44, aw.y + math.sin(a) * 0.44, PL_TOP + 0.08))
                              @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Diagonal((0.36, 0.12, 0.12, 1)))
    P(bm_obj(prefix + 'AdaptorSpokes', bm, [ALU], smooth=0))
    P(text_mesh(prefix + 'Badge', 'QUARTZ DIRECT DRIVE', 0.16, BLACK, (-3.2, 5.75, PL_TOP), font=FONT_B, extrude=0.002))
    if ox:
        for o in parts: o.location.x += ox
    return parts, (Pv, Nd, sl)


deck, (PIV, NEEDLE, STROBE) = build_deck('Deck')
deck2, _ = build_deck('Deck2_', ox=-17.0)


# ================================================================ the mixer
def knob(name, x, y, z0, r, hgt, mark_a, cap=None):
    o = lathe(name, [(0, z0 + hgt), (r * 0.72, z0 + hgt), (r * 0.88, z0 + hgt - 0.03), (r, z0 + hgt - 0.1), (r, z0 + 0.06),
                     (r * 1.18, z0 + 0.04), (r * 1.18, z0)], [KNOB], 48, loc=(x, y, 0),
              mod=lambda a, rr, z: 1.0 + (0.035 if math.cos(a * 28) > 0 else 0) * (1 if z0 + 0.08 < z < z0 + hgt - 0.1 else 0))
    m = rbox(name + 'Mark', -0.02, 0.02, r * 0.15, r * 0.85, z0 + hgt, z0 + hgt + 0.01, INK, rc=0, bev=0, loc=(x, y, 0), rot=(0, 0, mark_a), uv=0)
    out = [o, m]
    if cap: out.append(lathe(name + 'Cap', [(0, z0 + hgt + 0.012), (r * 0.5, z0 + hgt + 0.012), (r * 0.55, z0 + hgt)], [cap], 32, loc=(x, y, 0)))
    return out


MX0, MX1 = 9.45, 15.85; MT = PL_TOP + 0.15
mixer = [rbox('MixerBody', MX0, MX1, -6.25, 6.25, TABLE, MT - 0.25, BLACK, rc=0.2, bev=0.05),
         rbox('MixerTop', MX0 + 0.04, MX1 - 0.04, -6.21, 6.21, MT - 0.25, MT, DARKMET, rc=0.18, bev=0.06, bseg=4)]
rng = np.random.default_rng(3)
for ci, cx in enumerate((10.95, 14.35)):
    for k, y in enumerate((5.35, 4.35, 3.4, 2.45)):
        mixer += knob('Knob%d_%d' % (ci, k), cx, y, MT, 0.34 if k else 0.3, 0.38, rng.uniform(-2.2, 2.2), cap=ALU if k == 0 else None)
    mixer += knob('Filter%d' % ci, cx, 1.35, MT, 0.42, 0.42, rng.uniform(-1.5, 1.5), cap=ALU)
    for k, (dx, dy) in enumerate(((-0.42, 0.45), (0.42, 0.45), (-0.42, -0.35), (0.42, -0.35))):
        pm = PADS[(k + ci * 2) % 4] if (k + ci) % 3 != 2 else PAD_OFF
        mixer.append(rbox('Pad%d_%d' % (ci, k), cx + dx - 0.34, cx + dx + 0.34, dy - 0.34, dy + 0.34, MT - 0.02, MT + 0.14, pm, rc=0.09, bev=0.04, bseg=3))
    mixer.append(rbox('Cue%d' % ci, cx - 0.32, cx + 0.32, -1.25, -0.95, MT - 0.02, MT + 0.1, ORANGE_LED if ci == 0 else BLACK, rc=0.06, bev=0.025))
    mixer.append(rbox('FaderSlot%d' % ci, cx - 0.09, cx + 0.09, -4.6, -1.6, MT - 0.03, MT + 0.004, GLOSSBLACK, rc=0.08, bev=0))
    fy = -2.2 if ci == 0 else -3.5
    mixer.append(rbox('Fader%d' % ci, cx - 0.32, cx + 0.32, fy - 0.38, fy + 0.38, MT, MT + 0.42, BLACK, rc=0.06, bev=0.04, taper=0.05))
    mixer.append(rbox('FaderLine%d' % ci, cx - 0.27, cx + 0.27, fy - 0.025, fy + 0.025, MT + 0.42, MT + 0.43, INK, rc=0, bev=0))
    bm = bmesh.new()
    for k in range(11):
        y = -4.45 + k * 0.28
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((cx - 0.3 if k % 5 else cx - 0.36, y, MT + 0.003)) @ Matrix.Diagonal((0.16 if k % 5 else 0.28, 0.03, 0.006, 1)))
    mixer.append(bm_obj('FaderTicks%d' % ci, bm, [INK], smooth=0))
# centre strip: display, master knobs, VU meters, crossfader
mixer.append(rbox('Display', 11.95, 13.35, 4.75, 5.85, MT - 0.01, MT + 0.03, SCREEN, rc=0.05, bev=0.01))
mixer.append(text_mesh('DisplayTxt', '128.0', 0.42, SCREEN_TXT, (12.65, 5.35, MT + 0.03), font=FONT_B, extrude=0.001))
mixer += knob('Master', 12.65, 3.75, MT, 0.36, 0.38, 1.2, cap=ALU)
mixer += knob('Booth', 12.65, 2.7, MT, 0.3, 0.36, -0.4)
lit = (12, 10)
for col_i, vx in enumerate((12.45, 12.85)):
    for k in range(15):
        y = -3.7 + k * 0.33; c = 'G' if k < 10 else 'Y' if k < 13 else 'R'
        on = k < lit[col_i]
        mixer.append(rbox('Vu%d_%d' % (col_i, k), vx - 0.12, vx + 0.12, y - 0.1, y + 0.1, MT - 0.01, MT + 0.03, VU[c] if on else VU_OFF, rc=0.02, bev=0.0, uv=0))
mixer.append(rbox('XfSlot', 11.4, 13.9, -5.38, -5.22, MT - 0.03, MT + 0.004, GLOSSBLACK, rc=0.07, bev=0))
mixer.append(rbox('Xfader', 12.25, 12.95, -5.62, -4.98, MT, MT + 0.4, BLACK, rc=0.06, bev=0.04, taper=0.05))
mixer.append(rbox('XfaderLine', 12.575, 12.625, -5.58, -5.02, MT + 0.4, MT + 0.41, INK, rc=0, bev=0))
mixer.append(text_mesh('MixerBrand', 'KUMITE  DJM-2', 0.2, INK, (12.65, -5.95, MT), font=FONT_B, extrude=0.002))


# ================================================================ booth, speakers, floor, cables
booth = [rbox('BoothTop', -34, 34, -10.5, 9.0, TABLE - 1.0, TABLE, LAMINATE, rc=0.4, bev=0.08, uv=10.0),
         rbox('BoothFront', -33.5, 33.5, -10.4, 8.9, -14.0, TABLE - 1.0, BLACK, rc=0.3, bev=0.0, uv=10.0)]
floor_me = bpy.data.meshes.new('Floor'); bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=80); bmesh.ops.translate(bm, vec=(0, 10, -14), verts=bm.verts)
bm.to_mesh(floor_me); bm.free(); floor = obj('Floor', floor_me, [FLOOR]); box_uv(floor, 20.0)


def cone(name, x, y, z, rad):
    prof = [(0, -0.17), (0.18, -0.19), (0.3, -0.3), (0.32, -0.42), (0.86, -0.06), (0.9, 0.02), (0.96, 0.04), (1.0, 0.0), (1.1, 0.0), (1.1, -0.06)]
    prof = [(r * rad, zz * rad) for r, zz in prof]
    return lathe(name, prof, [DUSTCAP, CONE, RUBBER, ALU], 64, loc=(x, y, z), rot=(math.pi / 2, 0, 0), mi=[0, 0, 0, 1, 2, 2, 2, 3, 3])


speakers = []
for sx in (-17.5, 19.5):
    sy = 13.0; fy = sy - 2.6
    speakers.append(rbox('SubCab', sx - 3.2, sx + 3.2, sy - 2.6, sy + 2.6, -14.0, -7.4, BLACK, rc=0.15, bev=0.08,
                         holes=[('cyly', sx, -10.7, 2.3, 0.5)]))
    speakers.append(cone('SubCone', sx, fy + 0.45, -10.7, 2.25))
    speakers.append(rbox('TopCab', sx - 2.6, sx + 2.6, sy - 2.3, sy + 2.3, -7.35, 1.2, BLACK, rc=0.15, bev=0.08,
                         holes=[('cyly', sx, -5.3, 1.75, 0.5), ('cyly', sx, -1.6, 1.75, 0.5)]))
    for zc in (-5.3, -1.6): speakers.append(cone('TopCone', sx, sy - 2.3 + 0.42, zc, 1.72))
    speakers.append(lathe('Horn', [(0.3, 0.0), (0.45, 0.22), (1.1, 0.42), (1.25, 0.42), (1.25, 0.36)], [GLOSSBLACK], 4,
                          loc=(sx, sy - 2.3 - 0.4, 0.4), rot=(-math.pi / 2, math.pi / 4, 0)))
    speakers.append(rbox('PowerLed', sx + 2.0, sx + 2.15, sy - 2.33, sy - 2.3, -7.0, -6.85, mat('LedBlue', lin('3a8aff'), 0.3, emit=lin('3a8aff'), estr=20), rc=0, bev=0, uv=0))

cables = []
cables.append(curve_mesh('CableAudio', [Vector((8.6, 6.25, PL_TOP - 1.2)), Vector((8.9, 7.4, TABLE + 0.08)), Vector((10.3, 7.9, TABLE + 0.08)),
                                        Vector((11.2, 6.25, MT - 1.0))], 0.08, CABLE))
cables.append(curve_mesh('CablePower', [Vector((-5.5, 6.25, PL_TOP - 1.4)), Vector((-5.0, 7.6, TABLE + 0.09)), Vector((-2.5, 8.6, TABLE + 0.09)),
                                        Vector((-1.0, 9.25, TABLE - 1.2)), Vector((-0.6, 9.4, -9.0))], 0.09, CABLE))
for k, (cm, dx) in enumerate(((RCA_RED, 0.0), (RCA_WHITE, 0.25))):
    cables.append(curve_mesh('Rca%d' % k, [Vector((-8.6, 5.6 - dx, PL_TOP - 1.0)), Vector((-8.4, 4.0 - dx, TABLE + 0.06)),
                                           Vector((-7.1, 7.2 + dx, TABLE + 0.06)), Vector((-6.2, 6.25, PL_TOP - 1.0))], 0.045, CABLE))

for o in deck + deck2 + mixer + booth + speakers + cables:
    if not o.data.uv_layers: box_uv(o)

# ================================================================ export the stage
total = sum(tris(o) for o in STAGE)
unique = {}
for o in STAGE: unique[o.data.name] = tris(o)
print('TOTAL triangles (rendered, incl. deck 2):', total, ' objects:', len(STAGE))
top = sorted(((tris(o), o.name) for o in STAGE), reverse=True)[:12]; print('heaviest', top)
bpy.ops.object.select_all(action='DESELECT')
for o in STAGE: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'vinyl.glb'), export_format='GLB', use_selection=True,
                          export_apply=True, export_image_format='JPEG', export_jpeg_quality=92)
print('exported', os.path.join(OUT, 'vinyl.glb'), os.path.getsize(os.path.join(OUT, 'vinyl.glb')) // 1024, 'KB')
if NOREN: sys.exit(0)


# ================================================================ render-only: Cycles touches the glb can't carry
def aniso(mname, amount, axis='Z', rot=0.0, uvtan=False):
    bs = BSDF[mname]; nt = bs.id_data
    t = nt.nodes.new('ShaderNodeTangent')
    if uvtan: t.direction_type = 'UV_MAP'
    else: t.direction_type = 'RADIAL'; t.axis = axis
    nt.links.new(t.outputs['Tangent'], bs.inputs['Tangent'])
    bs.inputs['Anisotropic'].default_value = amount; bs.inputs['Anisotropic Rotation'].default_value = rot
aniso('Vinyl', 0.85, 'Z', 0.0)
aniso('PlatterAlu', 0.6, 'Z', 0.0)
aniso('Aluminium', 0.55, uvtan=True)
aniso('DarkAnodised', 0.5, uvtan=True)
aniso('Chrome', 0.0)

world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0015, 0.0012, 0.003, 1)


def light(name, kind, loc, look, energy, color, size=None, spot=None, blend=0.5, soft=0.5, glossy=True, camera=False):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(L)
    L.location = loc; L.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    L.data.energy = energy; L.data.color = color
    if kind == 'AREA':
        L.data.shape = 'RECTANGLE'; L.data.size, L.data.size_y = size
    if kind == 'SPOT': L.data.spot_size = math.radians(spot); L.data.spot_blend = blend
    if kind in ('SPOT', 'POINT'): L.data.shadow_soft_size = soft
    L.visible_glossy = glossy
    return L


light('Key', 'SPOT', (1.0, -3.0, 17), (0, 0.3, 0), 11000, (1.0, 0.84, 0.66), spot=46, blend=0.55, soft=1.4)
light('SpotMagenta', 'SPOT', (-15, 11, 15), (-1, 0, 0), 26000, (1.0, 0.18, 0.62), spot=34, blend=0.45, soft=0.6)
light('SpotCyan', 'SPOT', (16, 10, 14), (2, 1, 0), 22000, (0.15, 0.7, 1.0), spot=36, blend=0.45, soft=0.6)
light('Softbox', 'AREA', (0, 20, 15), (0, 0, -1), 3500, (0.85, 0.9, 1.0), size=(30, 4))
light('SoftboxWarm', 'AREA', (-6, 16, 10), (0, 0, -1), 900, (1.0, 0.75, 0.55), size=(10, 1.5))
light('Fill', 'AREA', (4, -20, 10), (0, 0, 0), 900, (0.6, 0.7, 1.0), size=(14, 6), glossy=False)
light('StrobeGlow', 'POINT', (STROBE.x + 0.5, STROBE.y + 0.5, PL_TOP + 0.3), (0, 0, 0), 60, (1.0, 0.35, 0.08), soft=0.2)
light('MixerGlow', 'AREA', (12.65, 0.0, MT + 1.4), (12.65, 0, 0), 120, (0.8, 0.4, 1.0), size=(4, 10), glossy=False)
for sx, c in ((-17.5, (1.0, 0.2, 0.6)), (19.5, (0.2, 0.6, 1.0))):
    light('SpkRim', 'SPOT', (sx, 4, 9), (sx, 10.5, -4), 9000, c, spot=40, blend=0.6, soft=0.5)

# haze and lasers
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 8, 2)); hz = bpy.context.object; hz.name = 'Haze'; hz.scale = (90, 60, 34)
hm = bpy.data.materials.new('Haze'); hm.use_nodes = True; nt = hm.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
pv = nt.nodes.new('ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = float(OPT.get('haze', 0.0035))
pv.inputs['Anisotropy'].default_value = 0.45
nt.links.new(pv.outputs['Volume'], nt.nodes['Material Output'].inputs['Volume']); hz.data.materials.append(hm)
LASER = {c: mat('Laser' + c, (0, 0, 0), 1.0, emit=lin(h), estr=40) for c, h in (('C', '3ad8ff'), ('M', 'ff3ad8'), ('G', '6aff6a'))}
for k in range(6):
    src = Vector((-14 + k * 5.6, 26, 7)); tgt = Vector((-24 + k * 9.5, -6, 22 + (k % 3) * 3))
    dirv = (tgt - src); ln = dirv.length
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.035, depth=ln, location=(src + tgt) / 2)
    o = bpy.context.object; o.rotation_euler = dirv.to_track_quat('Z', 'Y').to_euler(); o.data.materials.append(LASER['CMG'[k % 3]])
    o.visible_shadow = False


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
cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 300
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
scn.cycles.max_bounces = 6; scn.cycles.glossy_bounces = 4; scn.cycles.volume_bounces = 0; scn.cycles.transparent_max_bounces = 4
scn.cycles.sample_clamp_indirect = 8.0; scn.cycles.volume_step_rate = 4.0; scn.cycles.volume_max_steps = 96
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.use_nodes = True; cnt = scn.node_tree
rl = cnt.nodes['Render Layers']; comp = cnt.nodes['Composite']
gl = cnt.nodes.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 1.2; gl.mix = -0.8; gl.size = 8
cnt.links.new(rl.outputs['Image'], gl.inputs['Image']); cnt.links.new(gl.outputs['Image'], comp.inputs['Image'])

for shot in ('game', 'low'):
    if shot not in SHOTS: continue
    if shot == 'game':   # the game camera, 'wide' framing of stage_render.py
        el = math.radians(50); dist = 21
        cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
        cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:                # the low three-quarter view from the front-right
        cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
        cam.rotation_euler = (Vector((0, 0.8, 0.4)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = os.path.join(OUT, 'ex_%s.png' % shot)
    bpy.ops.render.render(write_still=True)
    print('wrote', scn.render.filepath)
