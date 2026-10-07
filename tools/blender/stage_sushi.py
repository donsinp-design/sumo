# "SUSHI TRAIN" stage, fully modelled: two sumos fight on a giant glazed kaiten-zushi plate riding single file on a
# black crescent-chain conveyor between polished steel guides, one ~40x sushi plate in the slot either side, pale
# hinoki counters either side (soy dish, wasabi, gari, chopsticks, 寿 cup on the far one). Built entirely by script (Blender 4.2, run headless).
#   python tools/blender/stage_sushi.py [out_dir] [chars_dir] [sushi_glb] [samples=32] [pct=100] [noren] [nochars]
# Writes <out_dir>/sushi_stage.glb (the stage only: Z up in Blender, metres, origin at the plate centre, flat top of the
# plate at Z=0, camera side -Y) and renders <out_dir>/ex_game.png from the game camera ('wide' of stage_render.py)
# with the game's characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in masks.
# Only what the game camera sees is built: the belt runs along X through the plate centre.
# The sushi pieces / table props are instances of the meshes in sushi_set.glb (tools/blender/sushi.py) at 40x.
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
ARGS = [a for a in sys.argv[1:] if '=' not in a and a not in ('noren', 'nochars') and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'sushistage')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
SUSHI = ARGS[2] if len(ARGS) > 2 else os.path.join(SP, 'sushi', 'sushi_set.glb')
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SAMPLES = int(OPT.get('samples', 32)); PCT = int(OPT.get('pct', 100))
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
RING_R = ring_r()
PR = RING_R + 0.7            # giant plate radius (5.3)
K = 40.0                     # scale of the sushi-set props
BELT_Z = -0.6                # top of the belt slats = underside of the giant plate's foot
BELT_W = 3.35                # half width of the slats: a single-file lane, a little wider than a 40x plate (r 3.03)
COUNTER_Z = -1.45            # hinoki counter top, a step below the belt
COUNTER_Y = 4.05             # the counters start right at the belt's steel skirt, on both sides


# ================================================================ helpers
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def hx(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2: t = t[..., None]
    return a * (1 - t) + b * t
def grid(h, w):
    v, u = np.meshgrid((np.arange(h) + 0.5) / h, (np.arange(w) + 0.5) / w, indexing='ij'); return u, v
def vnoise(h, w, cy, cx, rng=RNG):
    g = rng.random((cy, cx)).astype(np.float32)
    ys = np.arange(h) * cy / h; xs = np.arange(w) * cx / w
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    fy = ys - y0; fx = xs - x0; fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % cy; x1 = (x0 + 1) % cx; y0 %= cy; x0 %= cx
    a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
    fx = fx[None, :]; fy = fy[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
def fbm(h, w, cy, cx, octv, gain=0.5):
    s = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for i in range(octv):
        s += amp * vnoise(h, w, cy * 2 ** i, cx * 2 ** i); tot += amp; amp *= gain
    return s / tot
def image(name, arr):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(px.ravel()); img.file_format = 'PNG'; img.pack()
    return img
def mat(name, base, rough=0.5, img=None, metal=0.0, coat=0.0, aniso=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(base), 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.06
    if aniso: b.inputs['Anisotropic'].default_value = aniso      # Cycles-only (the glb keeps metal/roughness)
    if img is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t.location = (-400, 200)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m
def mk(name, verts, faces, m=None, uvs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(float(c) for c in v) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.validate(); me.update()
    if uvs is not None:
        uv = me.uv_layers.new(name='UVMap')
        vi = np.empty(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', vi)
        uv.data.foreach_set('uv', np.asarray(uvs, np.float32)[vi].ravel())
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    if m is not None: me.materials.append(m)
    STAGE.append(o); return o
def activate(o):
    for x in bpy.context.view_layer.objects: x.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
def apply_mod(o, md): activate(o); bpy.ops.object.modifier_apply(modifier=md.name)
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0
def bevel(o, w, seg=2, angle=40):
    b = o.modifiers.new('bev', 'BEVEL'); b.width = w; b.segments = seg; b.limit_method = 'ANGLE'
    b.angle_limit = math.radians(angle); apply_mod(o, b)
def box(name, x0, x1, y0, y1, z0, z1, m, uvs_scale=None):
    V = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    uv = [(v[0] / uvs_scale, v[1] / uvs_scale) for v in V] if uvs_scale else None
    return mk(name, V, F, m, uv, smooth=False)
STAGE = []


# ================================================================ textures (numpy, <= 1024 px)
def tex_plate(n=1024):
    """top of the giant plate, planar: u,v = 0.5 + (x,y) / (2 PR)"""
    u, v = grid(n, n); x = (u - 0.5) * 2 * PR; y = (v - 0.5) * 2 * PR
    r = np.hypot(x, y); th = np.arctan2(y, x)
    c = np.ones((n, n, 3), np.float32) * hx('f8f6f1')
    c = mix(c, hx('ebe6dc'), sstep(0.35, 0.85, fbm(n, n, 6, 6, 4)) * 0.45)                    # glaze pooling
    c = mix(c, hx('fdfcf9'), sstep(0.55, 0.9, fbm(n, n, 3, 3, 3)) * 0.4)
    c = mix(c, hx('8a7c6c'), sstep(0.972, 0.996, vnoise(n, n, 400, 400)) * 0.35)              # iron speckles
    indigo = mix(hx('1d2f66'), hx('2b4588'), fbm(n, n, 24, 24, 3) * 0.8)
    # the ring line (RING_R): a brushed indigo line with a slightly uneven edge
    wob = (fbm(n, n, 40, 40, 2) - 0.5) * 0.02
    c = mix(c, indigo, 1 - sstep(0.035, 0.05, np.abs(r - RING_R + wob)))
    # seigaiha band (indigo ground, pale wave-scale arcs) from just outside the gold line to the edge
    r0, Rw = RING_R + 0.21, 0.2
    ncell = int(round(TAU * (r0 + 0.2) / (2 * Rw)))
    s = (th / TAU) * ncell; tt = (r - r0) / Rw
    best = np.full(r.shape, 99.0); dbest = np.zeros_like(r)
    for j in range(int((PR + 0.3 - r0) / Rw * 2) + 3):
        sh = 0.5 * (j % 2); tc = j * 0.5
        sc = np.floor(s - sh + 0.5) + sh
        d = np.hypot((s - sc) * 2, tt - tc)
        ok = (tt >= tc) & (d < 1.0) & (best > 98)
        dbest = np.where(ok, d, dbest); best = np.where(ok, j, best)
    arcs = np.zeros_like(r)
    for k in (0.88, 0.58, 0.28):
        arcs = np.maximum(arcs, 1 - sstep(0.035, 0.085, np.abs(dbest - k)))
    band = mix(indigo, hx('d4dcec'), arcs * (best < 98) * 0.8)
    c = mix(c, band, sstep(r0 - 0.012, r0 + 0.012, r))
    c = mix(c, hx('16244f'), sstep(PR - 0.06, PR - 0.02, r))                                # deeper at the very edge
    return image('giant_plate', c)

def tex_steel(n=1024):
    """brushed stainless along u (the direction of travel); 1 tile = 4 m"""
    st = vnoise(n, n, 600, 6) * 0.5 + vnoise(n, n, 260, 3) * 0.3 + vnoise(n, n, 90, 2) * 0.2
    c = mix(hx('aeb2b8'), hx('d6d9dd'), st)
    c = mix(c, hx('9a9ea4'), sstep(0.55, 0.85, fbm(n, n, 6, 6, 3)) * 0.25)                  # faint smudges
    return image('steel', c)

def tex_hinoki(n=1024):
    """pale hinoki, grain along u; 1 tile = 8 m"""
    u, v = grid(n, n)
    warp = fbm(n, n, 6, 2, 3)
    g = (v * 22 + warp * 3.0 + fbm(n, n, 30, 3, 2) * 0.6)
    rings = np.abs(np.mod(g, 1.0) - 0.5) * 2
    late = 1 - sstep(0.0, 0.18, rings)                                                       # thin late-wood lines
    c = mix(hx('efdfc0'), hx('e3cca3'), fbm(n, n, 12, 3, 3))
    c = mix(c, hx('cfb084'), late * 0.55)
    c = mix(c, hx('d8bd92'), sstep(0.6, 0.95, vnoise(n, n, 420, 10)) * 0.3)                  # pores / fine streaks
    # board joints every 1/2 tile along v
    c = mix(c, hx('a88a62'), 1 - sstep(0.0005, 0.002, np.abs(np.mod(v, 0.5) - 0.25)))
    return image('hinoki', c)

PORCELAIN = mat('GiantPlate', 'f8f6f1', 0.1, tex_plate(), coat=0.6)
SLAT = mat('CrescentSlat', '141517', 0.38, coat=0.25)                                      # matte black, slight sheen
RAIL = mat('RailSteel', 'cdd0d4', 0.12, tex_steel(512), metal=1.0, aniso=0.4)             # polished guides
SKIRT = mat('SkirtSteel', 'c4c8cd', 0.28, tex_steel(), metal=1.0, aniso=0.7)               # brushed skirt below
BED = mat('BeltBed', '0b0b0c', 0.7)

def tex_glaze(name, base, n=512):
    """a single bright glaze with faint brush strokes, in the sushi set's plate UVs (u,v = 0.5 + (x,y) / 0.16 m)"""
    u, v = grid(n, n); x = (u - 0.5) * 0.16; y = (v - 0.5) * 0.16
    r = np.hypot(x, y); th = np.arctan2(y, x)
    col = hx(base); lite = mix(col, hx('ffffff'), 0.35); deep = mix(col, hx('000000'), 0.18)
    c = mix(col, deep, sstep(0.3, 0.9, fbm(n, n, 5, 5, 3)) * 0.35)                          # glaze pooling
    swirl = 0.5 + 0.5 * np.sin(th * 2 + r * 900 + fbm(n, n, 8, 8, 3) * 9)                     # turned / brushed glaze
    c = mix(c, lite, sstep(0.75, 1.0, swirl) * 0.18)
    for r0, a0, a1, w in ((0.03, -0.6, 2.2, 0.006), (0.05, 2.6, 5.2, 0.007)):                 # two sweeping strokes
        ang = np.mod(th - a0, TAU); inarc = sstep(0.0, 0.5, ang) * (1 - sstep(a1 - a0 - 0.6, a1 - a0, ang))
        rag = (fbm(n, n, 40, 40, 2) - 0.5) * 0.004
        c = mix(c, lite, (1 - sstep(w * 0.4, w, np.abs(r - r0 + rag))) * inarc * 0.32)
    c = mix(c, hx('8a7c6c'), sstep(0.975, 0.996, vnoise(n, n, 300, 300)) * 0.3)             # speckles
    c = mix(c, deep, sstep(0.0735, 0.0756, r) * 0.6)                                          # rim edge a touch deeper
    return image('glaze_' + name, c)
GOLD = mat('Gold', 'e2b04a', 0.22, metal=1.0)
HINOKI = mat('Hinoki', 'ead8b4', 0.55, tex_hinoki(), coat=0.15)


# ================================================================ the giant plate (lathe)
def lathe(name, prof, seg, m, uvfun):
    rings = len(prof); V = []; UV = []
    for (r, z) in prof:
        for k in range(seg):
            a = TAU * k / seg; p = (r * math.cos(a), r * math.sin(a), z); V.append(p); UV.append(uvfun(p))
    F = []
    for i in range(rings - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            F.append((i * seg + k, i * seg + k2, (i + 1) * seg + k2, (i + 1) * seg + k))
    c0 = len(V); V.append((0, 0, prof[0][1])); UV.append(uvfun(V[-1]))
    c1 = len(V); V.append((0, 0, prof[-1][1])); UV.append(uvfun(V[-1]))
    for k in range(seg):
        k2 = (k + 1) % seg
        F.append((c0, k2, k)); F.append((c1, (rings - 1) * seg + k, (rings - 1) * seg + k2))
    o = mk(name, V, F, m, UV)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return o

# top (flat, Z=0) -> a low lip outside the fighting area -> rolled edge -> underside -> foot ring on the belt
PROF = [(0.6, 0.0), (2.0, 0.0), (3.4, 0.0), (4.4, 0.0), (4.85, 0.0), (4.97, 0.004), (5.06, 0.018), (5.14, 0.032),
        (5.21, 0.035), (5.26, 0.022), (5.292, -0.01), (5.302, -0.05), (5.29, -0.1), (5.25, -0.14), (5.17, -0.17),
        (4.8, -0.22), (4.3, -0.27), (3.8, -0.31), (3.4, -0.35), (3.2, -0.38), (3.12, -0.48), (3.08, -0.56),
        (3.05, BELT_Z), (2.9, BELT_Z), (2.87, -0.56), (2.83, -0.46), (2.6, -0.42), (1.5, -0.4), (0.6, -0.39)]
# (the underside clears the guide rails at r 3.4-3.8: the arena plate overhangs them)
def plate_uv(p):
    if p[2] < -0.16:     # underside: squeeze into the plain white middle of the texture
        return (0.5 + p[0] / (2 * PR) * 0.4, 0.5 + p[1] / (2 * PR) * 0.4)
    return (0.5 + p[0] / (2 * PR), 0.5 + p[1] / (2 * PR))
plate = lathe('GiantPlate', PROF, 192, PORCELAIN, plate_uv)
# the gold line just outside the ring line, a thin inlaid band (2 mm proud)
def annulus(name, r0, r1, z, seg, m):
    V = [(r * math.cos(TAU * k / seg), r * math.sin(TAU * k / seg), z) for r in (r0, r1) for k in range(seg)]
    F = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
    return mk(name, V, F, m, smooth=False)
annulus('GoldLine', RING_R + 0.1, RING_R + 0.16, 0.002, 192, GOLD)
annulus('GoldEdge', 5.215, 5.24, 0.0365, 192, GOLD)


# ================================================================ the kaiten belt: black crescent top chain, steel guides
X0, X1 = -17.5, 17.5
PITCH, GAP, RC, NY = 1.8, 0.05, 3.75, 31
def slat(name, x0):
    """one crescent link: convex leading arc, concave trailing arc of the same circle shifted one pitch back, so
    each link nests into the next"""
    V = []
    ys = np.linspace(-BELT_W, BELT_W, NY)
    for z in (BELT_Z - 0.1, BELT_Z):
        for y in ys:
            a = math.sqrt(RC * RC - y * y) - RC
            for x in (x0 - PITCH + GAP + a, x0 + a):
                V.append((x, y, z))
    n = NY * 2; F = []
    for i in range(NY - 1):
        a, b = 2 * i, 2 * i + 2
        F.append((n + a, n + a + 1, n + b + 1, n + b))           # top
        F.append((a, b, b + 1, a + 1))                           # bottom
        F.append((a, n + a, n + b, b))                           # trailing (concave) side
        F.append((a + 1, b + 1, n + b + 1, n + a + 1))           # leading (convex) side
    l = 2 * (NY - 1)
    F.append((0, 1, n + 1, n)); F.append((l, n + l, n + l + 1, l + 1))
    o = mk(name, V, F, SLAT, smooth=False)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return o
slats = [slat('Slat', x) for x in np.arange(X0, X1 + 3.0, PITCH)]
for o in slats: bevel(o, 0.03, 2, 30)
activate(slats[0])
for o in slats[1:]: o.select_set(True)
bpy.ops.object.join(); belt = bpy.context.object; belt.name = belt.data.name = 'BeltSlats'
for o in slats[1:]: STAGE.remove(o)
box('BeltBed', X0, X1, -BELT_W - 0.05, BELT_W + 0.05, BELT_Z - 0.4, BELT_Z - 0.12, BED)
for sd in (-1, 1):   # brushed steel skirt from the guide down to the counters
    box('Skirt', X0, X1, min(sd * 3.5, sd * 3.95), max(sd * 3.5, sd * 3.95), COUNTER_Z - 0.05, BELT_Z - 0.3, SKIRT, uvs_scale=4.0)

def rail(name, yc, side):
    """a stainless guard rail along X: rounded-rectangle section, inner face toward the belt"""
    w, z0, z1, rr = 0.42, BELT_Z - 0.35, BELT_Z + 0.17, 0.1
    pts = []
    for cx, cz, a0 in ((w / 2 - rr, z1 - rr, 0), (-w / 2 + rr, z1 - rr, 90)):
        for k in range(7):
            a = math.radians(a0 + 15 * k); pts.append((cx + rr * math.cos(a), cz + rr * math.sin(a)))
    pts = [(w / 2, z0)] + pts + [(-w / 2, z0)]
    V, UV = [], []
    for x in (X0, X1):
        for (py, pz) in pts:
            V.append((x, yc + py * side, pz)); UV.append((x / 4.0, (py + pz) / 4.0))
    n = len(pts); F = [(k, k + 1, n + k + 1, n + k) for k in range(n - 1)]
    o = mk(name, V, F, RAIL, UV)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return o
rail('RailFront', -BELT_W - 0.25, -1)
rail('RailBack', BELT_W + 0.25, 1)

# ================================================================ hinoki counters either side of the belt
for nm, y0, y1 in (('CounterBack', COUNTER_Y, 18), ('CounterFront', -11, -COUNTER_Y)):
    bevel(box(nm, -24, 24, y0, y1, COUNTER_Z - 0.6, COUNTER_Z, HINOKI, uvs_scale=8.0), 0.05, 3, 30)


# ================================================================ sushi-set props at 40x (instances of the set's meshes)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=SUSHI)
MESH = {}
for o in [o for o in bpy.data.objects if o not in before]:
    if o.type == 'MESH': MESH[o.name] = o.data
    bpy.data.objects.remove(o)
for me in MESH.values():   # the set's textures were PNG: keep them as they are (<=512 px), the glb re-encodes as JPEG
    pass
def place(name, loc, rz=0.0, k=K):
    o = bpy.data.objects.new(name, MESH[name]); scn.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rz)); o.scale = (k,) * 3; STAGE.append(o); return o
FZ = 0.0075 * K            # the set's plate floor height
def plate_with(col, x, y, rz, items):
    place('plate_' + col, (x, y, BELT_Z), rz)
    a = math.radians(rz)
    for nm, dx, dy, r in items:
        dx *= K; dy *= K
        place(nm, (x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a), BELT_Z + FZ), rz + r)
# single file along the belt: [salmon plate] gap [arena plate] gap [maki plate]; the next slots are out of frame
GLAZES = {}
def glazed(col, hexc):   # the set's plate mesh with a plain bright glaze instead of the white + seigaiha one
    me = MESH['plate_red'].copy(); me.materials.clear()
    me.materials.append(mat('Glaze_' + col, hexc, 0.12, tex_glaze(col, hexc), coat=0.6)); MESH['glazed_' + col] = me
glazed('skyblue', '5fb4e8'); glazed('yellow', 'f2c230')
def plate_with(col, x, y, rz, items):
    place('glazed_' + col, (x, y, BELT_Z), rz)
    a = math.radians(rz)
    for nm, dx, dy, r in items:
        dx *= K; dy *= K
        place(nm, (x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a), BELT_Z + FZ), rz + r)
SLOT = PR + 1.1 + 0.0757 * K           # arena edge + a clear 1.1 m gap + the small plate's radius
plate_with('skyblue', -SLOT, 0.0, 84, [('nigiri_salmon', 0, 0.019, -4), ('nigiri_salmon', 0.003, -0.019, 6)])
plate_with('yellow', SLOT, 0.0, -72, [('maki_cucumber', -0.017, 0.016, 0), ('maki_tuna', 0.017, -0.016, 40)])
# the diner's things on the far counter, clear of the arena plate and the gyoji
CZ = COUNTER_Z
place('soy_dish', (-8.4, 7.2, CZ))
place('wasabi', (-5.9, 6.2, CZ)); place('gari', (-3.4, 8.3, CZ), 25)
place('chopsticks', (-4.3, 10.9, CZ), 3)
place('teacup', (7.6, 7.4, CZ), -20)

# ================================================================ export the stage
for o in bpy.context.view_layer.objects: o.select_set(o in STAGE)
dg = bpy.context.evaluated_depsgraph_get()
TOTAL = sum(tris(o) for o in STAGE)
for o in STAGE: print('%-16s %7d' % (o.name, tris(o)))
print('STAGE TRIS', TOTAL, flush=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'sushi_stage.glb'), export_format='GLB', use_selection=True,
                          export_apply=True, export_image_format='JPEG', export_jpeg_quality=90)
print('wrote', os.path.join(OUT, 'sushi_stage.glb'), flush=True)
if NOREN: sys.exit(0)


# ================================================================ characters (as stage_render.py): two masked sumos, masked gyoji
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHARS, f))
    new = [o for o in bpy.data.objects if o not in before]
    return new, [o for o in new if o.parent is None or o.parent not in new]
def mmat(name, hexc, rough=0.35):
    m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*srgb(hexc), 1); bs.inputs['Roughness'].default_value = rough; return m
def mask(kind, centre, fwd, up, k):
    fwd = (fwd - up * fwd.dot(up)).normalized(); right = fwd.cross(up).normalized()
    B = Matrix((right, fwd, up)).transposed().to_4x4(); B.translation = centre
    def put(o, loc, mat_):
        o.data.materials.append(mat_); bpy.ops.object.shade_smooth()
        o.matrix_world = B @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world
    def ell(loc, sc, mat_, half=False):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16); o = bpy.context.object
        if half:
            bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.05], context='VERTS'); bm.to_mesh(o.data); bm.free()
            sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.06
        o.scale = Vector(sc) * k; bpy.ops.object.transform_apply(scale=True); put(o, loc, mat_)
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

if not NOCHARS:
    stance = None; RIGS = []
    def sumo(f, pos, face, scale=1.65):
        global stance
        new, roots = load(f)
        rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
        if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
        elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
        for r in roots:
            r.location = (pos[0], pos[1], 0); r.scale = (scale,) * 3
            r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))
    A, B = (-1.0, -0.15), (1.0, 0.15)
    sumo('sumo2_stance.glb', A, B)
    sumo('sumo2_red.glb', B, A)
    GY = (0.4, 5.0)
    _, gr = load('gyoji.glb')
    for r in gr: r.location = (GY[0], GY[1], 0); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
    scn.frame_set(1)
    for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
        if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
    gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    mask('kitsune', Vector((GY[0], GY[1], 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)


# ================================================================ light: warm, soft restaurant light from above
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('f0d9b8'), 1); bg.inputs['Strength'].default_value = 0.35
def light(name, loc, look, energy, color, size, shape='RECTANGLE'):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.color = color; L.shape = shape
    if shape in ('RECTANGLE', 'ELLIPSE'): L.size, L.size_y = size
    else: L.size = size[0]
    o = bpy.data.objects.new(name, L); scn.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
light('Ceiling', (0, 2, 14), (0, 2, 0), 2600, srgb('ffe3bf'), (28, 16))            # the big soft ceiling panel
light('Lamp', (-2.5, -1.5, 10), (0, 0.5, 0), 1800, srgb('ffd6a0'), (5, 5), 'DISK')   # a pendant over the plate
light('LampR', (6, 7, 9), (6, 9, -1.4), 700, srgb('ffd6a0'), (4, 4), 'DISK')         # one over the counter

# ================================================================ game camera ('wide') and render
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
el = math.radians(50); dist = 21
cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34); cam.data.sensor_fit = 'VERTICAL'
cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
try: scn.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.render.filepath = os.path.join(OUT, 'ex_game.png'); bpy.ops.render.render(write_still=True)
print('rendered', scn.render.filepath, flush=True)
