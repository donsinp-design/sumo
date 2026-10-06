# "FLAT EARTH" stage, fully modelled: two sumos fight on a flat-earth disc floating in space. Built entirely by script
# (Blender 4.2, run headless).
#   python tools/blender/stage_earth.py [out_dir] [chars_dir] [samples=32] [pct=100] [noren] [nochars] [earth=<dir>]
# Writes <out_dir>/earth.glb (the disc only: Z up, metres, origin at the north pole, map surface at Z=0, the prime meridian
# pointing to -Y, i.e. towards the game camera) and renders <out_dir>/ex_game.png from the game camera ('wide' of
# stage_render.py) with the game's characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in masks.
# The map: NASA Blue Marble Next Generation (topography + bathymetry, Dec 2004, public domain, 5400x2700) and the NASA
# Blue Marble cloud layer, reprojected to an azimuthal equidistant ("flat earth") map, north pole at the centre, latitude
# -75 at the disc edge (RD = RING_R + 0.7). Images come from <earth>/bathy.jpg and <earth>/clouds.jpg; if absent a
# procedural ocean/continent map is painted instead. Land is raised <= 3 cm (and a normal map), the oceans are glossy;
# the fighting circle is a faint latitude line (with a faint graticule painted on the map). The rim is a craggy ice wall,
# under it a rock crust with strata, thin waterfalls spill off the edge. Stars, the small sun and the moon are render-only.
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
ARGS = [a for a in sys.argv[sys.argv.index('--') + 1 if '--' in sys.argv else 1:]
        if '=' not in a and a not in ('noren', 'nochars') and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'earth')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SAMPLES = int(OPT.get('samples', 32)); PCT = int(OPT.get('pct', 100))
NOREN = 'noren' in sys.argv; NOCHARS = 'nochars' in sys.argv
EARTH = OPT.get('earth', os.path.join(SP, 'dl_bm'))

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi


def ring_r():
    try:
        txt = open(os.path.join(HERE, '..', '..', 'public', 'js', 'config.js')).read()
        return float(re.search(r'S\.RING_R\s*=\s*([\d.]+)', txt).group(1))
    except Exception:
        return 4.6


R = ring_r()            # fighting circle
RD = R + 0.7            # map radius; the ice wall starts here
LAT_EDGE = -85.0        # latitude at RD (Antarctica is the white band just inside the ice wall)
HMAX = 0.03             # land relief
def lat_of(r): return 90.0 - r / RD * (90.0 - LAT_EDGE)


# ================================================================ helpers
def srgb(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)   # for painted images
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


STAGE = []
def obj(name, me, mats=(), stage=True, loc=None, rot=None):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    for m in mats: me.materials.append(m)
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = rot
    if stage: STAGE.append(o)
    return o
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0


def image(name, arr, data=False):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    h, w = arr.shape[:2]; rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    if data: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.file_format = 'PNG'; im.pack(); return im
def normal_from_h(h, strength):
    gy, gx = np.gradient(h); n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True); return n * 0.5 + 0.5
def blur(a, k):
    n0, n1 = a.shape; fy = np.fft.fftfreq(n0)[:, None]; fx = np.fft.fftfreq(n1)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-(fx ** 2 + fy ** 2) * (k ** 2) * 20)))
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


BSDF = {}
def mat(name, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tcol=None, trough=None, tnrm=None, nstr=1.0, emit=None,
        estr=0.0, coat=0.0, coat_r=0.05, spec=0.5, alpha=1.0):
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
    if alpha < 1: bs.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'
    return m


# ================================================================ the map (azimuthal equidistant, 1024 px over the disc)
N = 1024
rng = np.random.default_rng(5)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
X = ((xx + 0.5) / N * 2 - 1) * RD; Y = ((yy + 0.5) / N * 2 - 1) * RD       # row 0 = -Y (Blender images are bottom-up)
RR = np.sqrt(X * X + Y * Y)
LAT = np.clip(lat_of(RR), -90, 90)
LON = np.degrees(np.arctan2(X, -Y))                                         # prime meridian towards -Y, east clockwise...


def load_equirect(path):
    im = bpy.data.images.load(path); w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(h, w, 4)[..., :3]   # bottom-up, linear
    bpy.data.images.remove(im); return a
def sample(eq, lat, lon):
    h, w = eq.shape[:2]
    fx = (lon + 180.0) / 360.0 * w - 0.5; fy = (lat + 90.0) / 180.0 * h - 0.5
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); tx = (fx - x0)[..., None]; ty = (fy - y0)[..., None]
    x0w, x1w = x0 % w, (x0 + 1) % w; y0c, y1c = np.clip(y0, 0, h - 1), np.clip(y0 + 1, 0, h - 1)
    return ((eq[y0c, x0w] * (1 - tx) + eq[y0c, x1w] * tx) * (1 - ty) + (eq[y1c, x0w] * (1 - tx) + eq[y1c, x1w] * tx) * ty)


# Viewed from above the north pole east runs anticlockwise: with the prime meridian at -Y, 90E lies at +X.
# arctan2(X, -Y) gives +90 at +X, so LON is already east-positive.
BATHY = os.path.join(EARTH, 'bathy.jpg'); CLOUDS = os.path.join(EARTH, 'clouds.jpg')
if os.path.exists(BATHY):
    eq = load_equirect(BATHY)
    # supersample 2x2 (the map is minified near the pole, magnified near the rim)
    d = (RD * 2 / N) / 2
    col = np.zeros((N, N, 3), np.float32)
    for ox in (-0.5, 0.5):
        for oy in (-0.5, 0.5):
            Xs, Ys = X + ox * d, Y + oy * d; Rs = np.sqrt(Xs * Xs + Ys * Ys)
            col += sample(eq, np.clip(lat_of(Rs), -90, 90), np.degrees(np.arctan2(Xs, -Ys)))
    col /= 4; del eq
    ocean = sstep(0.025, 0.07, col[..., 2] - col[..., 0])               # blue-dominant = sea (ice and deserts are not)
    ocean = np.clip(blur(ocean, 0.6), 0, 1)
    SOURCE = 'NASA Blue Marble NG (topo+bathy)'
else:   # procedural fallback: fbm continents
    n1 = blur(rng.standard_normal((N, N)).astype(np.float32), 40); n2 = blur(rng.standard_normal((N, N)).astype(np.float32), 9)
    f = n1 / n1.std() + 0.35 * n2 / n2.std()
    ocean = 1 - sstep(0.55, 0.7, f); ocean = np.where(LAT < -66, 0, ocean)
    deep = srgb('0b2a5a'); shelf = srgb('2f7fa8'); green = srgb('4d6b2e'); dry = srgb('a48a5e')
    sea = shelf + (deep - shelf) * sstep(0.0, 0.5, 0.55 - f)[..., None]
    land = green + (dry - green) * sstep(-0.3, 0.6, n2 / n2.std())[..., None]
    land = np.where((LAT < -66)[..., None], np.array([0.85, 0.88, 0.92]), land)
    col = sea * ocean[..., None] + land * (1 - ocean[..., None])
    SOURCE = 'procedural'
land = 1 - ocean

# land relief: local shading contrast of the shaded-relief map ~ mountains
L = col @ np.array([0.3, 0.59, 0.11], np.float32)
relief = np.abs(L - blur(L, 3.0)); relief = blur(relief, 1.2); relief /= np.percentile(relief[land > 0.5], 97) + 1e-6
H = land * (0.35 + 0.65 * np.clip(relief, 0, 1))
H = np.clip(blur(H, 0.7), 0, 1)
HEIGHT = H * HMAX                                                            # metres, <= 3 cm

# the sea: richer blues, shallow shelves a touch more turquoise; light clouds very faint
sea_t = col * np.array([0.92, 1.02, 1.1], np.float32) * 1.08
col = col * land[..., None] + sea_t * ocean[..., None]
if os.path.exists(CLOUDS):
    eqc = load_equirect(CLOUDS); cl = sample(eqc, LAT, LON)[..., 0]; del eqc
    col = col + (np.array([0.95, 0.96, 1.0]) - col) * (np.clip(cl, 0, 1) ** 1.5 * 0.09)[..., None]
# faint graticule (every 30 deg of longitude, every 30 deg of latitude), Gleason-map style
px = RD * 2 / N
g = np.zeros((N, N), np.float32)
for la in (60, 30, 0, -30):
    rl = (90 - la) / (90 - LAT_EDGE) * RD; g = np.maximum(g, np.exp(-((RR - rl) / (0.9 * px)) ** 2))
for lo in range(0, 360, 30):
    a = math.radians(lo); dist = np.abs(X * math.cos(a) + Y * math.sin(a))     # line through the pole
    along = X * -math.sin(a) + Y * math.cos(a)
    g = np.maximum(g, np.exp(-(dist / (0.8 * px)) ** 2) * sstep(0.4, 0.9, RR) * (along > -1e9))
col = col + (np.array([0.85, 0.9, 1.0]) - col) * (g * 0.16)[..., None]
col[RR > RD] = np.array([0.82, 0.86, 0.92])
TCOL = image('EarthMap', col)
rough = 0.12 * ocean + 0.72 * land; rough = np.where(LAT < -66, 0.45, rough)
TROUGH = image('EarthRough', np.dstack([rough * 0, rough, rough * 0]), True)
TNRM = image('EarthNormal', normal_from_h(H, 6.0), True)
print('map source:', SOURCE)


def height_at(x, y):
    i = int(np.clip((y / RD + 1) / 2 * N, 0, N - 1)); j = int(np.clip((x / RD + 1) / 2 * N, 0, N - 1))
    return float(HEIGHT[i, j])


# ================================================================ materials
EARTH_M = mat('EarthMap', (0.2, 0.3, 0.5), 0.4, tcol=TCOL, trough=TROUGH, tnrm=TNRM, nstr=1.0)
LINE = mat('LatitudeLine', (0.5, 0.58, 0.68), 0.4, emit=(0.7, 0.85, 1.0), estr=0.03)
# crust strata (cylindrical u = angle, v = depth)
NS = 1024
sv = np.linspace(0, 1, 256)[:, None]; su = np.linspace(0, 1, NS)[None, :]
wob = blur(rng.standard_normal((256, NS)).astype(np.float32), 10); wob /= wob.std()
bands = np.sin((sv * 26 + 0.25 * wob) * TAU * 0.5) * 0.5 + 0.5
fine = blur(rng.standard_normal((256, NS)).astype(np.float32), 1.5); fine /= fine.std()
c1 = srgb('5b4634'); c2 = srgb('8a6f52'); c3 = srgb('3a3029')
strata = c1 + (c2 - c1) * bands[..., None] + (c3 - c1) * sstep(0.6, 1.0, sv)[..., None] * 0.8
strata *= (1 + 0.12 * fine)[..., None]
strata[sv[:, 0] > 0.93] = strata[sv[:, 0] > 0.93] * 0.5 + srgb('3c5a2a') * 0.5      # a soil/grass lip at the top
TSTRATA = image('Strata', strata)
CRUST = mat('Crust', (0.3, 0.25, 0.2), 0.85, tcol=TSTRATA)
ICE = mat('IceWall', lin('e8f2fb'), 0.32, coat=0.4, coat_r=0.15)
WATER = mat('Waterfall', lin('cfe6f5'), 0.08, alpha=0.65)

# ================================================================ map surface (concentric rings, land raised)
NR, SEG = 110, 256
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
radii = [RD * (k / NR) ** 0.9 for k in range(1, NR + 1)]
pole = bm.verts.new((0, 0, height_at(0, 0)))
rings = []
for r in radii:
    ring = []
    for i in range(SEG):
        a = TAU * i / SEG; x, y = r * math.cos(a), r * math.sin(a)
        ring.append(bm.verts.new((x, y, height_at(x, y) if r < RD - 0.02 else 0.0)))
    rings.append(ring)
for i in range(SEG):
    bm.faces.new((pole, rings[0][i], rings[0][(i + 1) % SEG]))
for A, B in zip(rings[:-1], rings[1:]):
    for i in range(SEG):
        j = (i + 1) % SEG; bm.faces.new((A[i], B[i], B[j], A[j]))
for f in bm.faces:
    if f.normal.z < 0: f.normal_flip()
    for l in f.loops: l[uvl].uv = (l.vert.co.x / (2 * RD) + 0.5, l.vert.co.y / (2 * RD) + 0.5)
me = bpy.data.meshes.new('EarthTop'); bm.to_mesh(me); bm.free(); me.shade_smooth()
obj('EarthTop', me, [EARTH_M])

# the fighting circle: a faint latitude line riding on the map
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); S2 = 256; w = 0.016
inner = []; outer = []
for i in range(S2):
    a = TAU * i / S2; c, s = math.cos(a), math.sin(a)
    z = max(height_at(R * c, R * s), height_at((R + 0.04) * c, (R + 0.04) * s), height_at((R - 0.04) * c, (R - 0.04) * s)) + 0.003
    inner.append(bm.verts.new(((R - w) * c, (R - w) * s, z))); outer.append(bm.verts.new(((R + w) * c, (R + w) * s, z)))
for i in range(S2):
    j = (i + 1) % S2; f = bm.faces.new((inner[i], outer[i], outer[j], inner[j]))
    if f.normal.z < 0: f.normal_flip()
    for l in f.loops: l[uvl].uv = (i / S2, 0.5)
me = bpy.data.meshes.new('FightLine'); bm.to_mesh(me); bm.free()
obj('FightLine', me, [LINE])


# ================================================================ ice wall (craggy, irregular) and crust
def noise1(n, k, seed):
    r = np.random.default_rng(seed).standard_normal(n); F = np.fft.rfft(r); f = np.fft.rfftfreq(n)
    out = np.fft.irfft(F * np.exp(-(f * k) ** 2), n); return out / (out.std() + 1e-9)
SW = 384
blk = np.repeat(np.random.default_rng(4).random(SW // 4 + 1), 4)[:SW] - 0.5      # serac blocks: stepped heights
hn = noise1(SW, 40, 1) * 0.35 + noise1(SW, 6, 2) * 0.25 + blk * 1.1
crag = noise1(SW, 1.2, 3)
#            r offset, z,  jitter-scale     (inner foot -> crest -> outer foot)
wall = [(-0.03, -0.004, 0.0), (0.0, 0.04, 0.2), (0.02, 0.17, 0.6), (0.05, 0.27, 1.0), (0.13, 0.31, 1.0),
        (0.24, 0.30, 1.0), (0.32, 0.24, 0.8), (0.37, 0.12, 0.6), (0.40, 0.02, 0.3), (0.42, -0.06, 0.0)]
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); rings = []
for k, (dr, z, js) in enumerate(wall):
    ring = []
    for i in range(SW):
        a = TAU * i / SW; hh = max(0.45, 1 + 0.3 * hn[i])
        r = RD + dr + js * 0.03 * crag[(i + k * 7) % SW]
        ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z * hh if z > 0 else z)))
    rings.append(ring)
for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
    for i in range(SW):
        j = (i + 1) % SW; f = bm.faces.new((A[i], B[i], B[j], A[j]))
        for l, uv in zip(f.loops, ((i / SW, k / 9), (i / SW, (k + 1) / 9), ((i + 1) / SW, (k + 1) / 9), ((i + 1) / SW, k / 9))):
            l[uvl].uv = (uv[0] * 8, uv[1])
me = bpy.data.meshes.new('IceWall'); bm.to_mesh(me); bm.free()
me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(50))
icewall = obj('IceWall', me, [ICE])
# outward normals check (the first face of the outer slope should face +r)
RC = RD + 0.42
crust = [(RC, -0.06), (RC + 0.02, -0.4), (RC - 0.02, -0.9), (RC - 0.12, -1.3), (RC - 0.5, -1.75), (RC - 1.3, -2.25),
         (RC - 2.6, -2.75), (RC - 4.2, -3.15), (0, -3.4)]
SC = 192
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); rings = []
cn = noise1(SC, 6, 7)
for k, (r, z) in enumerate(crust):
    if r < 1e-6: rings.append([bm.verts.new((0, 0, z))]); continue
    ring = []
    for i in range(SC):
        a = TAU * i / SC; rr = r * (1 + (0.0 if k < 2 else 0.035 * cn[(i * 3 + k * 11) % SC]))
        ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z + (0 if k < 2 else 0.08 * cn[(i * 5 + k) % SC]))))
    rings.append(ring)
vz = [0.0] + list(np.cumsum([math.dist(crust[k], crust[k + 1]) for k in range(len(crust) - 1)]))
vz = [v / vz[-1] for v in vz]
for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
    for i in range(SC):
        j = (i + 1) % SC
        if len(B) == 1:
            f = bm.faces.new((A[i], B[0], A[j])); uvs = ((i / SC, 1 - vz[k]), (i / SC, 1 - vz[k + 1]), ((i + 1) / SC, 1 - vz[k]))
        else:
            f = bm.faces.new((A[i], B[i], B[j], A[j]))
            uvs = ((i / SC, 1 - vz[k]), (i / SC, 1 - vz[k + 1]), ((i + 1) / SC, 1 - vz[k + 1]), ((i + 1) / SC, 1 - vz[k]))
        for l, uv in zip(f.loops, uvs): l[uvl].uv = (uv[0] * 3, uv[1])
me = bpy.data.meshes.new('Crust'); bm.to_mesh(me); bm.free(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(40))
obj('Crust', me, [CRUST])
# a thin plate under the wall/map so nothing sees through between the map and the crust
bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=128, radius=RC + 0.01)
for v in bm.verts: v.co.z = -0.05
for f in bm.faces:
    if f.normal.z < 0: f.normal_flip()
me = bpy.data.meshes.new('Floor'); bm.to_mesh(me); bm.free(); obj('CrustTop', me, [CRUST])

# ================================================================ waterfalls spilling off the edge
FALLS = [(math.radians(a), wdt) for a, wdt in ((171, 0.06), (187, 0.035), (-6, 0.05), (9, 0.03))]
for n, (a0, hw) in enumerate(FALLS):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); NU, NV = 6, 26; grid = []
    jit = np.random.default_rng(20 + n)
    for vi in range(NV + 1):
        t = vi / NV; row = []
        r = RC + 0.03 + 1.5 * t ** 1.4; z = -0.05 - 5.5 * t ** 1.15
        spread = hw * (1 + 0.6 * t)
        for ui in range(NU + 1):
            s = ui / NU * 2 - 1; a = a0 + s * spread + 0.01 * jit.standard_normal() * t
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        grid.append(row)
    for vi in range(NV):
        for ui in range(NU):
            f = bm.faces.new((grid[vi][ui], grid[vi][ui + 1], grid[vi + 1][ui + 1], grid[vi + 1][ui]))
            for l, (uu, vv) in zip(f.loops, ((ui, vi), (ui + 1, vi), (ui + 1, vi + 1), (ui, vi + 1))):
                l[uvl].uv = (uu / NU, 1 - vv / NV)
    for f in bm.faces:   # face outwards
        c = f.calc_center_median(); rad = Vector((c.x, c.y, 0)).normalized()
        if f.normal.dot(rad) < 0: f.normal_flip()
    me = bpy.data.meshes.new('Waterfall%d' % n); bm.to_mesh(me); bm.free(); me.shade_smooth()
    obj('Waterfall%d' % n, me, [WATER])

# ================================================================ export the stage
total = sum(tris(o) for o in STAGE)
print('TOTAL triangles:', total, ' objects:', len(STAGE))
print('heaviest', sorted(((tris(o), o.name) for o in STAGE), reverse=True)[:8])
bpy.ops.object.select_all(action='DESELECT')
for o in STAGE: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'earth.glb'), export_format='GLB', use_selection=True,
                          export_apply=True, export_image_format='JPEG', export_jpeg_quality=92)
print('exported', os.path.join(OUT, 'earth.glb'), os.path.getsize(os.path.join(OUT, 'earth.glb')) // 1024, 'KB')
if NOREN: sys.exit(0)


# ================================================================ render-only: ice & water shading, space, sun, moon
nt = ICE.node_tree; bs = BSDF['IceWall']
bs.inputs['Subsurface Weight'].default_value = 0.35; bs.inputs['Subsurface Radius'].default_value = (0.3, 0.6, 1.0)
bs.inputs['Subsurface Scale'].default_value = 0.08
tc = nt.nodes.new('ShaderNodeTexCoord')
vn = nt.nodes.new('ShaderNodeTexVoronoi'); vn.inputs['Scale'].default_value = 7; nt.links.new(tc.outputs['Object'], vn.inputs['Vector'])
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 6
nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'ADD'
nt.links.new(vn.outputs['Distance'], mx.inputs[0]); nt.links.new(nz.outputs['Fac'], mx.inputs[1])
bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.9; bp.inputs['Distance'].default_value = 0.05
nt.links.new(mx.outputs[0], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], bs.inputs['Normal'])
ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*lin('8fb6d4'), 1)
ramp.color_ramp.elements[1].color = (*lin('f4f9fd'), 1); ramp.color_ramp.elements[0].position = 0.35
nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bs.inputs['Base Color'])

# map: tiny ripples on the sea for a broken sheen
nt = EARTH_M.node_tree; bs = BSDF['EarthMap']
nmap = next(n for n in nt.nodes if n.type == 'NORMAL_MAP')
rip = nt.nodes.new('ShaderNodeTexNoise'); rip.inputs['Scale'].default_value = 60; rip.inputs['Detail'].default_value = 3
bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08; bp.inputs['Distance'].default_value = 0.01
nt.links.new(rip.outputs['Fac'], bp.inputs['Height']); nt.links.new(nmap.outputs['Normal'], bp.inputs['Normal'])
nt.links.new(bp.outputs['Normal'], bs.inputs['Normal'])

# waterfall: transparency fading downwards, streaks along the fall
nt = WATER.node_tree; bs = BSDF['Waterfall']
uvn = nt.nodes.new('ShaderNodeUVMap')
sepx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uvn.outputs['UV'], sepx.inputs['Vector'])
mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (14, 1.2, 1)
nt.links.new(uvn.outputs['UV'], mp.inputs['Vector'])
st = nt.nodes.new('ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 3; st.inputs['Detail'].default_value = 5
nt.links.new(mp.outputs['Vector'], st.inputs['Vector'])
fade = nt.nodes.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = 0.0; fade.inputs['From Max'].default_value = 1.0
fade.inputs['To Min'].default_value = 0.0; fade.inputs['To Max'].default_value = 1.0
nt.links.new(sepx.outputs['Y'], fade.inputs['Value'])
pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.8; nt.links.new(fade.outputs['Result'], pw.inputs[0])
edge = nt.nodes.new('ShaderNodeMath'); edge.operation = 'PINGPONG'; edge.inputs[1].default_value = 0.5
nt.links.new(sepx.outputs['X'], edge.inputs[0])
es = nt.nodes.new('ShaderNodeMapRange'); es.inputs['From Min'].default_value = 0.0; es.inputs['From Max'].default_value = 0.25
nt.links.new(edge.outputs[0], es.inputs['Value'])
m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(pw.outputs[0], m1.inputs[0]); nt.links.new(es.outputs['Result'], m1.inputs[1])
sr = nt.nodes.new('ShaderNodeMapRange'); sr.inputs['From Min'].default_value = 0.35; sr.inputs['From Max'].default_value = 0.65
nt.links.new(st.outputs['Fac'], sr.inputs['Value'])
m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(sr.outputs['Result'], m2.inputs[1])
m3 = nt.nodes.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'; m3.inputs[1].default_value = 0.9
nt.links.new(m2.outputs[0], m3.inputs[0]); nt.links.new(m3.outputs[0], bs.inputs['Alpha'])
bs.inputs['Emission Color'].default_value = (0.6, 0.8, 1.0, 1); bs.inputs['Emission Strength'].default_value = 0.6

# space: black with stars (two layers), the faintest blue haze
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world; wt = world.node_tree
bg = wt.nodes['Background']; wtc = wt.nodes.new('ShaderNodeTexCoord')
acc = None
for scale, thr, amp in ((420, 0.93, 6.0), (120, 0.975, 30.0)):
    vor = wt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = scale
    wt.links.new(wtc.outputs['Generated'], vor.inputs['Vector'])
    dr = wt.nodes.new('ShaderNodeMapRange'); dr.inputs['From Min'].default_value = 0.0; dr.inputs['From Max'].default_value = 0.12
    dr.inputs['To Min'].default_value = 1.0; dr.inputs['To Max'].default_value = 0.0; wt.links.new(vor.outputs['Distance'], dr.inputs['Value'])
    sc = wt.nodes.new('ShaderNodeSeparateColor'); wt.links.new(vor.outputs['Color'], sc.inputs['Color'])
    gate = wt.nodes.new('ShaderNodeMapRange'); gate.inputs['From Min'].default_value = thr; gate.inputs['From Max'].default_value = 1.0
    gate.inputs['To Min'].default_value = 0.0; gate.inputs['To Max'].default_value = amp; wt.links.new(sc.outputs['Red'], gate.inputs['Value'])
    mm = wt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'
    wt.links.new(dr.outputs['Result'], mm.inputs[0]); wt.links.new(gate.outputs['Result'], mm.inputs[1])
    if acc is None: acc = mm
    else:
        ad = wt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'; wt.links.new(acc.outputs[0], ad.inputs[0]); wt.links.new(mm.outputs[0], ad.inputs[1]); acc = ad
starc = wt.nodes.new('ShaderNodeMixRGB'); starc.blend_type = 'MULTIPLY'; starc.inputs['Fac'].default_value = 1.0
starc.inputs['Color2'].default_value = (0.9, 0.95, 1.0, 1)
cmb = wt.nodes.new('ShaderNodeCombineColor')
for ch in ('Red', 'Green', 'Blue'): wt.links.new(acc.outputs[0], cmb.inputs[ch])
wt.links.new(cmb.outputs['Color'], starc.inputs['Color1'])
haze = wt.nodes.new('ShaderNodeTexNoise'); haze.inputs['Scale'].default_value = 1.6; haze.inputs['Detail'].default_value = 6
wt.links.new(wtc.outputs['Generated'], haze.inputs['Vector'])
hz = wt.nodes.new('ShaderNodeMixRGB'); hz.blend_type = 'MULTIPLY'; hz.inputs['Fac'].default_value = 1.0
hz.inputs['Color2'].default_value = (0.0012, 0.0016, 0.004, 1); wt.links.new(haze.outputs['Fac'], hz.inputs['Color1'])
add = wt.nodes.new('ShaderNodeMixRGB'); add.blend_type = 'ADD'; add.inputs['Fac'].default_value = 1.0
wt.links.new(starc.outputs['Color'], add.inputs['Color1']); wt.links.new(hz.outputs['Color'], add.inputs['Color2'])
lp = wt.nodes.new('ShaderNodeLightPath')
mixc = wt.nodes.new('ShaderNodeMixRGB'); mixc.inputs['Color1'].default_value = (0.0, 0.0, 0.0, 1)   # stars only to the camera
wt.links.new(lp.outputs['Is Camera Ray'], mixc.inputs['Fac']); wt.links.new(add.outputs['Color'], mixc.inputs['Color2'])
wt.links.new(mixc.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0


def light(name, kind, loc, look, energy, color, size=None, spot=None, blend=0.5, soft=0.5, glossy=True, angle=None):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(L)
    L.location = loc; L.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    L.data.energy = energy; L.data.color = color
    if kind == 'AREA': L.data.shape = 'RECTANGLE'; L.data.size, L.data.size_y = size
    if kind == 'SPOT': L.data.spot_size = math.radians(spot); L.data.spot_blend = blend
    if kind in ('SPOT', 'POINT'): L.data.shadow_soft_size = soft
    if kind == 'SUN': L.data.angle = math.radians(angle or 2)
    L.visible_glossy = glossy
    return L


def panel(name, loc, look, size, strength, color):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    o.location = loc; o.scale = (size[0], size[1], 1)
    o.rotation_euler = (Vector(loc) - Vector(look)).to_track_quat('Z', 'Y').to_euler()
    m = mat(name, (0, 0, 0), 1.0, emit=color, estr=strength, spec=0.0); me.materials.append(m)
    o.visible_camera = o.visible_diffuse = o.visible_shadow = o.visible_transmission = o.visible_volume_scatter = False
    return o


cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 400
el = math.radians(50); dist = 21
cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
bpy.context.view_layer.update()

# the small sun (upper right of the frame) and the moon (upper left), hovering in space beyond the rim
SUN_P = Vector((float(OPT.get('sx', 11.5)), float(OPT.get('sy', 9.0)), float(OPT.get('sz', -1.5))))
MOON_P = Vector((float(OPT.get('mx', -12.0)), float(OPT.get('my', 8.0)), float(OPT.get('mz', -2.5))))
for nm, p in (('sun', SUN_P), ('moon', MOON_P)):
    print(nm, 'in frame at', tuple(round(c, 3) for c in world_to_camera_view(scn, cam, p)))
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.55, location=SUN_P); sun = bpy.context.object
sun.data.materials.append(mat('SunOrb', (0, 0, 0), 1.0, emit=(1.0, 0.78, 0.45), estr=40.0)); bpy.ops.object.shade_smooth()
sun.visible_shadow = False
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.55, location=MOON_P); moon = bpy.context.object
mm = mat('Moon', (0.5, 0.5, 0.5), 0.9); bpy.ops.object.shade_smooth(); moon.data.materials.append(mm)
nt = mm.node_tree; bs = BSDF['Moon']
mv = nt.nodes.new('ShaderNodeTexNoise'); mv.inputs['Scale'].default_value = 3.5; mv.inputs['Detail'].default_value = 8
cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.16, 0.16, 0.17, 1); cr.color_ramp.elements[1].color = (0.62, 0.61, 0.59, 1)
cr.color_ramp.elements[0].position = 0.4; cr.color_ramp.elements[1].position = 0.62
nt.links.new(mv.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
cv = nt.nodes.new('ShaderNodeTexVoronoi'); cv.inputs['Scale'].default_value = 9
bpm = nt.nodes.new('ShaderNodeBump'); bpm.inputs['Strength'].default_value = 0.5
nt.links.new(cv.outputs['Distance'], bpm.inputs['Height']); nt.links.new(bpm.outputs['Normal'], bs.inputs['Normal'])
light('SunGlow', 'POINT', tuple(SUN_P), (0, 0, 0), 2500, (1.0, 0.8, 0.55), soft=0.55, glossy=False)

# key: the sun's warmth from high up its side; cool moon fill; a rim from behind; a softbox for the sea's sheen
light('Key', 'SUN', (10, 6, 14), (0, 0, 0), 4.2, (1.0, 0.9, 0.78), angle=4.0)
light('MoonFill', 'AREA', (-14, -4, 10), (0, 0, 0), 1800, (0.6, 0.72, 1.0), size=(8, 8), glossy=False)
light('Rim', 'AREA', (0, 16, 4), (0, 0, 0), 1500, (0.7, 0.8, 1.0), size=(16, 4), glossy=False)
panel('SeaSheen', (6, 22, 17), (0, 2, 0), (34, 12), 1.1, (1.0, 0.92, 0.8))

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


# ================================================================ render (game camera only)
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
scn.cycles.max_bounces = 6; scn.cycles.glossy_bounces = 3; scn.cycles.transparent_max_bounces = 8
scn.cycles.sample_clamp_indirect = 6.0
scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.use_nodes = True; cnt = scn.node_tree
rl = cnt.nodes['Render Layers']; comp = cnt.nodes['Composite']
gl = cnt.nodes.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 2.0; gl.mix = -0.7; gl.size = 8
cnt.links.new(rl.outputs['Image'], gl.inputs['Image']); cnt.links.new(gl.outputs['Image'], comp.inputs['Image'])
scn.render.filepath = os.path.join(OUT, 'ex_game.png')
bpy.ops.render.render(write_still=True)
print('wrote', scn.render.filepath)
