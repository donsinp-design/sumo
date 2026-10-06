# Kumite campaign hero, v2: a premium stylised rikishi, built and rigged entirely by script (Blender 4.2, headless).
#   python tools/blender/sumo2.py  OUT_DIR  [shots=rest,back,front,game,toon,zoom,...] [samples=48] [res=720]
# Writes OUT_DIR/sumo2.glb (skinned, navy mawashi) + OUT_DIR/sumo2_red.glb (dark red mawashi) + preview PNGs.
#
# Recipe
#   body   overlapping volumes (real rikishi masses: traps, delts, scapulae, love handles, belly, buttocks, calves, toes)
#          fused into ONE skin by a voxel remesh, smoothed, then "sculpted" with analytic displacements (spine groove,
#          neck / wrist / knee / pec folds, navel, a cinch under the belt so the fat rolls over it), decimated.
#   skin   smart-project UVs; per-vertex colour (flush at knees, elbows, knuckles, cheeks, ears, shoulders, nape;
#          lighter belly; ray-traced crease occlusion; a little top light) + procedural mottling baked to a 1024 texture,
#          so it still reads under a flat toon shader that only uses base colour.
#   hair   an oiled cap shot onto the skull with combed ridges + a painted gloss band, a bulging tabo at the back, and an
#          oicho-mage: the topknot tied with a white cord and spread forward into a ginkgo-leaf fan.
#   belt   three layered silk wraps (each tilted differently so they cross at the back), a stacked folded knot, the
#          vertical strip between the buttocks and up the front, stiff sagari; a painted sheen texture (light top lip,
#          dark lower edge per wrap). A red texture is swapped in for the opponent export.
#   rig    a simple humanoid armature in an A-pose; bone-heat weights on the skin (envelope fallback), the clothes and
#          hair get the skin's weights (nearest-vertex blend) or a rigid anchor (knot, sagari, face, topknot).
# Blender is Z-up with the front facing -Y; the glTF export converts to Y-up. Real scale: about 1.85 m, origin at the feet.
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ARGS = [a for a in sys.argv[1:] if not a.endswith('.py')]
OPT = dict(a.split('=', 1) for a in ARGS if '=' in a)
POS = [a for a in ARGS if '=' not in a and not a.startswith('-')]
OUT = POS[0] if POS else '/tmp/sumo2'
os.makedirs(OUT, exist_ok=True)
SHOTS = set(OPT['shots'].split(',')) if 'shots' in OPT else None
SAMPLES, RES = int(OPT.get('samples', 48)), int(OPT.get('res', 720))

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def hexf(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])      # sRGB-encoded floats, for pixels
def sstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def gau(v, s): return np.exp(-(v / s) ** 2)
def mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    return m
def tex_mat(name, img, rough, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t.name = 'Tex'
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = spec
    return m
def np_image(name, arr):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(px.ravel()); img.update(); img.pack(); return img

# ---------------------------------------------------------------- painted textures: mawashi silk, oiled hair
def silk_img(name, base, hi, lo, seed):
    rng = np.random.default_rng(seed); H, W = 256, 512
    V, U = np.meshgrid((np.arange(H) + 0.5) / H, (np.arange(W) + 0.5) / W, indexing='ij')
    # across each wrap (v: 0 = lower edge, 1 = top lip): dark tucked underside, mid body, a bright rolled top lip
    m = np.interp(V, [0, 0.12, 0.3, 0.55, 0.78, 0.88, 0.95, 1], [-1, -0.75, -0.3, 0.0, 0.25, 0.75, 1.0, 0.85])
    fib = np.convolve(rng.normal(0, 1, H), np.ones(3) / 3, 'same')[:, None] * 0.035     # fibres along the wrap
    sheen = 0.06 * np.sin(2 * np.pi * (2 * U + 0.15 * np.sin(2 * np.pi * 3 * U + 6 * V))) + 0.03 * np.sin(2 * np.pi * 7 * U + 1.3)
    col = base + (hi - base) * np.maximum(m, 0)[..., None] + (lo - base) * np.maximum(-m, 0)[..., None]
    return np_image(name, col * (1 + fib + sheen)[..., None])
SILK_N = silk_img('SilkNavy', hexf('1b2a5e'), hexf('5c78c0'), hexf('0a0f26'), 1)
SILK_R = silk_img('SilkRed', hexf('8c2228'), hexf('cf5a55'), hexf('3c0a0e'), 1)

def hair_img():
    rng = np.random.default_rng(3); H, W = 256, 512
    V, U = np.meshgrid((np.arange(H) + 0.5) / H, (np.arange(W) + 0.5) / W, indexing='ij')
    jit = np.interp(U[0], np.linspace(0, 1, 97), rng.normal(0, 1, 97))[None, :]
    comb = 0.5 + 0.5 * np.cos(2 * np.pi * (40 * U + 0.25 * np.sin(2 * np.pi * V * 1.5)))             # combed ridges
    strand = 0.5 + 0.5 * np.cos(2 * np.pi * (157 * U + 0.6 * jit))
    lum = 0.78 + 0.22 * comb ** 2 + 0.1 * strand
    base = hexf('16141c') * lum[..., None]
    band = np.exp(-((V - 0.42 - 0.04 * jit) / 0.07) ** 2) * (0.35 + 0.65 * comb ** 3) * (0.7 + 0.3 * strand)   # oiled gloss band
    band2 = 0.5 * np.exp(-((V - 0.78) / 0.05) ** 2) * comb ** 4
    return np_image('HairTex', base + (hexf('8692b4') - base) * np.clip(band + band2, 0, 1)[..., None] * 0.85)
HAIR_IMG = hair_img()

MAW = tex_mat('Mawashi', SILK_N, 0.38, 0.6)
HAIR = tex_mat('Hair', HAIR_IMG, 0.22, 0.7)
INK = mat('Ink', srgb('1a1216'), 0.4)
WHITE = mat('White', srgb('f6f2ea'), 0.5)

# ---------------------------------------------------------------- skeleton landmarks (rest A-pose)
S2 = (-1, 1)
R40 = math.radians(40)
J = {s: Vector((s * 0.43, 0.01, 1.385)) for s in S2}                       # shoulder joint
D1 = {s: Vector((s * math.cos(R40), 0.0, -math.sin(R40))) for s in S2}     # upper arm, 40 degrees down
E = {s: J[s] + D1[s] * 0.30 for s in S2}                                   # elbow
D2 = {s: Vector((s * 0.6, -0.12, -0.79)).normalized() for s in S2}         # forearm
W = {s: E[s] + D2[s] * 0.27 for s in S2}                                   # wrist
HIP = {s: Vector((s * 0.20, 0.04, 0.80)) for s in S2}
KNEE = {s: Vector((s * 0.27, -0.02, 0.46)) for s in S2}
ANK = {s: Vector((s * 0.29, 0.03, 0.11)) for s in S2}
TOE = {s: Vector((s * 0.30, -0.19, 0.03)) for s in S2}
HC = Vector((0, 0.015, 1.705))                                             # skull centre
def hand_frame(s):
    xh = D2[s]; nin = Vector((-s, 0, 0)); nin = (nin - xh * xh.dot(nin)).normalized()   # palm normal: toward the thigh
    yh = xh.cross(nin).normalized()
    if yh.y > 0: yh = -yh                                                               # thumb side: forward
    return xh, yh, nin

# ---------------------------------------------------------------- body: volumes fused into one skin
parts = []
def ell(c, r, rot=None, seg=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=tuple(c)); o = bpy.context.object; o.scale = r
    if rot is not None: o.rotation_euler = rot.to_euler()
    parts.append(o); return o
def ell_ax(c, axes, r):                                                   # oriented ellipsoid, radii along a, b, a x b
    a, b = Vector(axes[0]).normalized(), Vector(axes[1]).normalized(); return ell(c, r, Matrix((a, b, a.cross(b))).transposed())
def limb(a, b, ra, rb, caps=True):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=ra, radius2=rb, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); parts.append(o)
    if caps: ell(a, (ra, ra, ra)); ell(b, (rb, rb, rb))

# torso
ell((0, 0.04, 0.84), (0.34, 0.22, 0.20))            # pelvis
for s in S2:
    ell((s * 0.145, 0.17, 0.765), (0.185, 0.165, 0.19))     # buttocks (the cleft stays between them)
ell((0, -0.08, 1.02), (0.40, 0.37, 0.34))           # the belly: big and round
ell((0, -0.19, 0.88), (0.31, 0.25, 0.16))           # lower belly, hanging toward the belt
ell((0, -0.02, 1.27), (0.37, 0.27, 0.22))           # chest
for s in S2:
    ell((s * 0.16, -0.165, 1.225), (0.155, 0.10, 0.125))   # heavy pecs
ell((0, 0.06, 1.25), (0.355, 0.22, 0.24))           # upper back
for s in S2:
    ell((s * 0.165, 0.19, 1.30), (0.15, 0.11, 0.16))       # shoulder-blade masses
ell((0, 0.07, 1.04), (0.355, 0.21, 0.20))           # lower back
ell((0, 0.075, 1.14), (0.36, 0.215, 0.17))          # mid back: one broad slab from the shoulder blades to the belt
for s in S2:
    limb((s * 0.065, 0.2, 1.0), (s * 0.06, 0.22, 1.3), 0.075, 0.06)   # erector columns either side of the spine
ell((0, 0.05, 0.945), (0.425, 0.285, 0.105))       # the roll of fat above the belt (love handles round the back)
for s in S2:
    ell((s * 0.27, 0.10, 0.955), (0.15, 0.17, 0.10))       # ...fuller over the hips
# shoulders, traps, neck
ell((0, 0.10, 1.46), (0.21, 0.13, 0.11))            # trapezius hump behind the neck
for s in S2:
    limb((s * 0.05, 0.07, 1.53), (s * 0.31, 0.04, 1.45), 0.105, 0.10)   # trapezius slope
    ell((s * 0.40, 0.01, 1.39), (0.165, 0.175, 0.16))      # deltoid
limb((0, 0.03, 1.40), (0, 0.0, 1.61), 0.14, 0.125, caps=False)   # thick neck
# head: cranium, face, a strong jaw, double chin, brow ridge, nose, cheeks, ears
ell(HC, (0.142, 0.155, 0.152))
ell((0, -0.045, 1.66), (0.136, 0.12, 0.12))
ell((0, -0.05, 1.592), (0.136, 0.112, 0.075))       # jaw / jowls
ell((0, -0.13, 1.566), (0.052, 0.04, 0.036))        # chin
ell((0, -0.075, 1.54), (0.105, 0.085, 0.05))        # double chin
ell((0, -0.122, 1.727), (0.105, 0.04, 0.03))        # brow ridge
ell((0, -0.165, 1.685), (0.018, 0.022, 0.036))      # nose bridge
ell((0, -0.172, 1.655), (0.028, 0.025, 0.023))      # nose tip
for s in S2:
    ell((s * 0.021, -0.162, 1.65), (0.016, 0.018, 0.014))  # nostrils
    ell((s * 0.078, -0.122, 1.636), (0.045, 0.035, 0.036))  # cheeks
    ell((s * 0.14, 0.012, 1.68), (0.022, 0.042, 0.052))     # ears
    ell((s * 0.152, 0.02, 1.685), (0.012, 0.03, 0.04))      # ear rim
# arms: big delts, thick upper arm, chunky forearm, open mitten hands with fingers indicated
for s in S2:
    limb(J[s], E[s], 0.142, 0.104)
    up = D1[s].cross(Vector((0, 1, 0))).normalized()
    if up.z < 0: up = -up
    ell_ax(J[s] + D1[s] * 0.13 + Vector((0, -0.03, 0)), (D1[s], Vector((0, 1, 0)), up), (0.12, 0.11, 0.115))   # biceps / triceps
    ell(E[s] + Vector((0, 0.02, 0)), (0.098, 0.1, 0.098))                                                      # elbow
    limb(E[s], W[s], 0.1, 0.066, caps=False)
    a2 = D2[s]; b2 = Vector((0, 1, 0)); b2 = (b2 - a2 * a2.dot(b2)).normalized(); c2 = a2.cross(b2)
    ell_ax(E[s] + D2[s] * 0.075, (a2, b2, c2), (0.12, 0.103, 0.1))                                             # forearm muscle
    ell(W[s], (0.067, 0.067, 0.067))
    xh, yh, nin = hand_frame(s); H0 = W[s] + xh * 0.02
    ell_ax(H0 + xh * 0.055, (xh, yh, nin), (0.07, 0.058, 0.034))                                               # palm
    for k, (off, L) in enumerate(((0.037, 0.078), (0.013, 0.088), (-0.012, 0.083), (-0.036, 0.068))):          # fingers
        a = H0 + xh * 0.105 + yh * off; b = a + xh * L + nin * 0.01
        limb(a, b, 0.0138, 0.0122)
    limb(H0 + xh * 0.03 + yh * 0.045 + nin * 0.006, H0 + xh * 0.095 + yh * 0.078 + nin * 0.024, 0.02, 0.015)   # thumb
# legs: massive thighs, knees, shapely calves, flat broad feet with toes
for s in S2:
    limb(HIP[s] + Vector((0, 0, -0.02)), KNEE[s], 0.245, 0.16)
    ell((s * 0.24, -0.03, 0.66), (0.215, 0.215, 0.2))                    # inner / front thigh mass
    ell((s * 0.27, 0.06, 0.62), (0.2, 0.18, 0.17))                       # hamstring mass under the buttock
    ell(KNEE[s] + Vector((0, -0.04, 0.0)), (0.14, 0.13, 0.12))          # knee
    limb(KNEE[s], ANK[s], 0.145, 0.092)
    ell((s * 0.29, 0.065, 0.31), (0.125, 0.115, 0.135))                # calf
    ell((s * 0.275, 0.04, 0.27), (0.12, 0.1, 0.11))                     # inner calf
    ell((s * 0.30, -0.06, 0.04), (0.105, 0.165, 0.06))                  # foot
    ell((s * 0.30, 0.07, 0.05), (0.08, 0.07, 0.065))                    # heel
    for k, (dx, r, dy) in enumerate(((-0.055, 0.03, 0.0), (-0.02, 0.023, 0.006), (0.008, 0.022, 0.012), (0.033, 0.02, 0.02), (0.056, 0.018, 0.03))):
        ell((s * (0.30 + dx), -0.205 + dy, 0.024), (r, r * 1.25, r))     # toes, big toe on the inside
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = 'Body'
bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
r = body.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.0075
bpy.ops.object.modifier_apply(modifier='rm')
m = body.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); m.factor = 0.8; m.iterations = 10; m.smooth_type = 'LENGTH_WEIGHTED'
bpy.ops.object.modifier_apply(modifier='sm')
m = body.modifiers.new('sm2', 'SMOOTH'); m.factor = 0.5; m.iterations = 6
bpy.ops.object.modifier_apply(modifier='sm2')

# ---------------------------------------------------------------- sculpt pass: analytic folds, grooves and a belt cinch
def belt_zc(th): return 0.80 - 0.045 * np.cos(th)          # the belt sits low under the belly, high on the sacrum
BELT_H = 0.085
def sculpt(me):
    n = len(me.vertices)
    co = np.empty(n * 3, np.float64); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    nr = np.empty(n * 3, np.float64); me.vertex_normals.foreach_get('vector', nr); nr = nr.reshape(-1, 3)
    x, y, z = co.T; nx, ny, nz = nr.T
    d = np.zeros(n)
    back = sstep(0.15, 0.5, ny)
    d -= 0.02 * gau(x, 0.03) * back * sstep(1.02, 1.12, z) * (1 - sstep(1.36, 1.46, z))           # spine groove (stops above the roll)
    for z0, a in ((1.06, 0.012), (1.15, 0.008)):                                                   # flank folds above the roll
        d -= a * gau(z - z0 - 0.15 * (np.abs(x) - 0.3), 0.009) * sstep(0.18, 0.3, np.abs(x)) * sstep(-0.05, 0.1, y) * sstep(0.2, 0.5, np.hypot(nx, ny))
    d -= 0.006 * gau(x, 0.06) * back * sstep(1.02, 1.12, z) * (1 - sstep(1.3, 1.44, z))           # ...with soft walls
    for z0, a in ((1.465, 0.011), (1.505, 0.009), (1.54, 0.005)):                                  # folds at the back of the neck
        d -= a * gau(z - (z0 + 0.9 * x ** 2), 0.0075) * np.exp(-(x / 0.12) ** 4) * sstep(0.1, 0.5, ny)
    for s in S2:
        e = np.array(E[s]); w_ = np.array(W[s]); d2 = np.array(D2[s]); kn = np.array(KNEE[s])
        t = (co - w_) @ d2; rad = np.linalg.norm((co - w_) - t[:, None] * d2, axis=1)
        arm = (rad < 0.1) & (s * x > 0.55)
        d -= arm * (0.009 * gau(t + 0.004, 0.006) + 0.005 * gau(t + 0.035, 0.006))               # wrist folds
        t = (co - e) @ np.array(D1[s]); rad = np.linalg.norm((co - e) - t[:, None] * np.array(D1[s]), axis=1)
        d -= ((rad < 0.13) & (s * x > 0.5)) * 0.01 * gau(t + 0.01, 0.012) * sstep(0.2, 0.6, -ny)      # inside of the elbow
        legx = np.exp(-((x - kn[0]) / 0.11) ** 4)
        d -= 0.014 * gau(z - 0.47, 0.01) * legx * sstep(0.2, 0.6, ny)                                 # behind the knee
        d -= 0.006 * gau(z - 0.43, 0.008) * legx * sstep(0.2, 0.6, ny)
        d -= 0.006 * gau(z - 0.125, 0.012) * np.exp(-((x - s * 0.29) / 0.09) ** 4) * sstep(0.2, 0.6, -ny) * (z < 0.2)  # ankle crease
    ax = np.abs(x)
    d -= 0.013 * gau(z - (1.13 + 1.3 * (ax - 0.16) ** 2), 0.011) * np.exp(-((ax - 0.16) / 0.14) ** 4) * sstep(0.3, 0.6, -ny)  # under the pecs
    d -= 0.02 * gau(np.hypot(x, z - 0.99), 0.012) * sstep(0.5, 0.8, -ny) * (y < -0.3)              # navel
    d -= 0.008 * gau(z - (1.548 + 0.6 * x ** 2), 0.008) * np.exp(-(x / 0.1) ** 4) * sstep(0.3, 0.6, -ny) * (y < -0.05)  # under the chin
    # cinch: the skin under the belt is pressed in, so the belly and love handles roll over the top edge
    th = np.arctan2(x, -(y + 0.03)); zc = belt_zc(th)
    torso = (np.abs(x) < 0.56) & (z > 0.58) & (z < 1.02)
    band = sstep(BELT_H + 0.02, BELT_H - 0.01, np.abs(z - zc))
    hz = np.hypot(nx, ny)
    d -= torso * band * 0.022 * sstep(0.3, 0.7, hz)
    co += nr * d[:, None]
    co[:, 2] = np.maximum(co[:, 2], 0.0)                                                            # flat soles
    me.vertices.foreach_set('co', co.ravel()); me.update()
sculpt(body.data)
m = body.modifiers.new('sm3', 'SMOOTH'); m.factor = 0.4; m.iterations = 2
bpy.ops.object.modifier_apply(modifier='sm3')

# decimate: the face, hands and toes keep their density
vg = body.vertex_groups.new(name='dec')
for v in body.data.vertices:
    c = v.co; w = 1.0
    if c.z > 1.52 and c.y < -0.02: w = 0.0
    elif abs(c.x) > 0.78: w = 0.05
    elif c.z < 0.08 and c.y < -0.12: w = 0.1
    elif c.z > 1.55: w = 0.4
    vg.add([v.index], w, 'REPLACE')
BODY_TRIS = int(OPT.get('bodytris', 19000))
for _ in range(4):
    n = sum(len(p.vertices) - 2 for p in body.data.polygons)
    if n <= BODY_TRIS * 1.04: break
    d = body.modifiers.new('dec', 'DECIMATE'); d.ratio = BODY_TRIS / n; d.use_symmetry = True; d.symmetry_axis = 'X'
    d.vertex_group = 'dec'; d.vertex_group_factor = 0.6
    bpy.ops.object.modifier_apply(modifier='dec')
body.vertex_groups.clear()
bpy.ops.object.shade_smooth()
print('body triangles', sum(len(p.vertices) - 2 for p in body.data.polygons))

dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(body, dg)
def hit(o, d, dist=3.0):
    loc, nor, _, _ = bvh.ray_cast(Vector(o), Vector(d).normalized(), dist); return loc, nor

# ---------------------------------------------------------------- mesh builders
def link_obj(name, me):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o); return o
def grid_obj(name, P, UV, m_, close_i=False, close_k=False, cap_i=False):
    """P[i][k] -> quads. Seams are real duplicate columns so UVs stay clean; close_* wraps topologically instead."""
    ni, nk = len(P), len(P[0])
    verts = [tuple(p) for row in P for p in row]
    faces = []
    for i in range(ni if close_i else ni - 1):
        i2 = (i + 1) % ni
        for k in range(nk if close_k else nk - 1):
            k2 = (k + 1) % nk
            faces.append((i * nk + k, i2 * nk + k, i2 * nk + k2, i * nk + k2))
    if cap_i:
        faces.append(tuple(range(nk))[::-1]); faces.append(tuple((ni - 1) * nk + k for k in range(nk)))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.validate(); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    flat = [uv for row in UV for uv in row]
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = flat[me.loops[li].vertex_index]
    o = link_obj(name, me); me.materials.append(m_)
    for p in me.polygons: p.use_smooth = True
    return o
def prim_obj(name, m_):
    o = bpy.context.object; o.name = name
    bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
    if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
    else: o.data.uv_layers[0].name = 'UVMap'
    o.data.materials.append(m_)
    for p in o.data.polygons: p.use_smooth = True
    return o
def sphere(name, loc, scale, m_, seg=16, rings=10, rot=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=tuple(loc)); o = bpy.context.object; o.scale = scale
    if rot is not None: o.rotation_euler = rot.to_euler() if hasattr(rot, 'to_euler') else rot
    return prim_obj(name, m_)
def push_out(obj, min_off, iters=3):
    """no vertex of obj closer than min_off to the skin, or inside it"""
    for v in obj.data.vertices:
        p = v.co.copy()
        for _ in range(iters):
            l, nrm, _, _ = bvh.find_nearest(p)
            if l is None: break
            dd = (p - l).dot(nrm)
            if dd < min_off: p = p + nrm * (min_off - dd)
            else: break
        v.co = p
    obj.data.update()
def sgp(v, e): return math.copysign(abs(v) ** e, v)

# ---------------------------------------------------------------- mawashi
CY = -0.03                                    # belt axis (y) — the waist is centred a little forward
def skin_r(th, z, r0=0.64):
    d = Vector((math.sin(th), -math.cos(th), 0)); o = Vector((0, CY, z))
    loc, _ = hit(o + d * r0, -d, r0)
    return (loc - o).length if loc else 0.3
NT = 72
THS = [math.pi * 2 * i / NT for i in range(NT)]
WRAPS = []                                     # (zfun, h, outer radius per theta) of the cloth laid so far
def lerp_th(arr, th):
    return float(np.interp(th % (2 * math.pi), THS + [2 * math.pi], list(arr) + [arr[0]]))
def cloth_base(th, z):
    """radius the next layer of cloth has to clear at (theta, z): the skin, or any wrap already there"""
    r = skin_r(th, z)
    for zf, h, Ro in WRAPS:
        if abs(z - zf(th)) <= h + 0.006: r = max(r, lerp_th(Ro, th))
    return r
def bridge(R):                                 # cloth spans concavities (spine groove, cleft): max filter, then smooth
    for _ in range(2): R = np.maximum(R, np.maximum(np.roll(R, 1), np.roll(R, -1)))
    for _ in range(4): R = (np.roll(R, 1) + 2 * R + np.roll(R, -1)) / 4
    return R
def wrap(name, zfun, h, off, t, K=10):
    prof = []
    for k in range(K + 1):
        g = math.pi + 2 * math.pi * k / K                             # seam on the inner face
        cx, cy = math.cos(g), math.sin(g); prof.append((h * sgp(cy, 0.28), t * (sgp(cx, 0.28) + 1) / 2))
    dzs = sorted(set(round(dz, 6) for dz, _ in prof))
    B = {dz: bridge(np.array([cloth_base(th, zfun(th) + dz) for th in THS])) for dz in dzs}
    P, UV = [], []
    for i in range(NT + 1):
        ii = i % NT; th = THS[ii] if i < NT else 2 * math.pi
        zc = zfun(th); row, uvr = [], []
        for dz, dr in prof:
            rr = B[round(dz, 6)][ii] + off + dr
            row.append(Vector((rr * math.sin(th), CY - rr * math.cos(th), zc + dz)))
            uvr.append((i / NT * 4.0, 0.5 + 0.5 * dz / h))
        P.append(row); UV.append(uvr)
    o = grid_obj(name, P, UV, MAW)
    WRAPS.append((zfun, h, np.max(np.array([B[d] for d in dzs]), axis=0) + off + t)); return o
# th = 0 at the front (-Y), pi at the back. Three wraps laid one over the other, each tilted differently so the
# edges step and cross (the camera mostly sees the back and the top lips of the wraps).
# Inner wraps ride higher, outer ones lower: from above and behind the top lips read as stepped terraces.
w1 = wrap('Wrap1', lambda th: float(belt_zc(th)) + 0.012, 0.07, 0.003, 0.018)
w2 = wrap('Wrap2', lambda th: float(belt_zc(th)) - 0.008 + 0.016 * math.sin(th) * (1 - math.cos(th)) / 2, 0.065, 0.001, 0.019)
w3 = wrap('Wrap3', lambda th: float(belt_zc(th)) - 0.035 - 0.018 * math.sin(th) * (1 - math.cos(th)) / 2, 0.06, 0.001, 0.019)
ZB = float(belt_zc(math.pi))                   # belt centre height at the back

def pad(name, thc, half_w, zc, h, off, t, tilt=0.0, bulge=0.25, NI=16, K=10, zbend=0.0, taper=0.0):
    """a folded slab of belt cloth lying flat over whatever is under it (a rounded rectangle, pillowed)"""
    P, UV = [], []
    for i in range(NI + 1):
        a = -1 + 2 * i / NI
        sz = (1 - abs(a) ** 6) ** 0.16                                  # rounded-rect outline
        th = thc + a * half_w / 0.42
        rr0 = max(cloth_base(th, zc + tilt * a + dz) for dz in np.linspace(-h, h, 7)) + off
        row, uvr = [], []
        for k in range(K + 1):
            g = math.pi + 2 * math.pi * k / K; cx, cy = math.cos(g), math.sin(g)
            dz = h * sz ** 0.5 * sgp(cy, 0.26)
            tt = t * sz * (1 + bulge * (1 - a * a) * (1 - abs(cy)))
            dr = tt * (sgp(cx, 0.26) + 1) / 2
            rr = rr0 + dr
            thk = thc + a * half_w * (1 - taper * (0.5 - 0.5 * dz / h)) / 0.42
            row.append(Vector((rr * math.sin(thk), CY - rr * math.cos(thk), zc + dz + tilt * a + zbend * a * a)))
            uvr.append((0.25 + (a + 1) * half_w * 2, 0.5 + 0.5 * dz / h))
        P.append(row); UV.append(uvr)
    o = grid_obj(name, P, UV, MAW)
    Ro = np.array([cloth_base(th, zc) for th in THS]) * 0                      # register it as cloth for the next layer
    for ii, th in enumerate(THS):
        dth = (th - thc + math.pi) % (2 * math.pi) - math.pi
        if abs(dth) < half_w / 0.42: Ro[ii] = max(cloth_base(th, zc + dz) for dz in (-h, 0, h)) + off + t * (1 + bulge * 0.5)
    WRAPS.append((lambda th, zc=zc: zc, h, Ro))
    return o
def path_strip(name, pts, side, hw, t, m_=None, K=8):
    P, UV = [], []; L = 0.0
    for i, p in enumerate(pts):
        tng = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized(); nn = side.cross(tng).normalized()
        if i: L += (pts[i] - pts[i - 1]).length
        row, uvr = [], []
        for k in range(K + 1):
            g = math.pi + 2 * math.pi * k / K; cx, cy = math.cos(g), math.sin(g)
            row.append(p + nn * t * 0.5 * sgp(cx, 0.4) + side * hw * sgp(cy, 0.4)); uvr.append((L * 3, 0.5 + 0.45 * sgp(cy, 0.4)))
        P.append(row); UV.append(uvr)
    return grid_obj(name, P, UV, m_ or MAW, cap_i=True)
# the back knot: three pleats stacked like roof tiles (each lip catches the light from above), a narrow vertical
# fold of the strip running up over them, and the tucked end standing up proud of the top edge
KNOT = [pad('KnotPleat', math.pi, 0.125 - 0.012 * k, ZB - 0.07 + 0.06 * k, 0.042, 0.002, 0.02, tilt=0.008 * (k - 1), bulge=0.35)
        for k in range(3)]
KNOT.append(pad('KnotFold', math.pi, 0.048, ZB - 0.035, 0.135, 0.003, 0.024, bulge=0.3, taper=-0.25))
yb = CY + lerp_th(WRAPS[-1][2], math.pi)       # outer face of the knot at the back centre
KNOT.append(pad('KnotEnd', math.pi, 0.05, ZB + 0.118, 0.034, -0.042, 0.022, bulge=0.5, zbend=-0.016))

# the tate-mitsu: one strip up the front over the groin, under the crotch, up between the buttocks into the knot
def mid_skin(phi, c=Vector((0, 0.03, 0.80))):
    d = Vector((0, -math.cos(phi), -math.sin(phi)))
    loc, nor = hit(c + d * 0.9, -d, 0.9)
    return loc, nor
zf, zb = float(belt_zc(0)) - 0.05, ZB - 0.06
phis = np.linspace(math.radians(8), math.radians(176), 40)
path = []
for ph in phis:
    loc, nor = mid_skin(ph)
    if loc is not None: path.append(loc)
# keep the run between the bottom of the belt at the front and at the back
path = [p for p in path if not (p.y < -0.1 and p.z > zf + 0.02) and not (p.y > 0.1 and p.z > zb + 0.04)]
for _ in range(3):                                                               # taut cloth: relax the path
    path = [path[0]] + [(path[i - 1] + 2 * path[i] + path[i + 1]) / 4 for i in range(1, len(path) - 1)] + [path[-1]]
NP = len(path)
P, UV = [], []
L_acc = 0.0
for i, p in enumerate(path):
    a = path[min(i + 1, NP - 1)] - path[max(i - 1, 0)]; tng = a.normalized()
    l, nrm, _, _ = bvh.find_nearest(p)
    side = Vector((1, 0, 0)); nn = side.cross(tng).normalized()
    if nn.dot(nrm) < 0: nn = -nn
    f = i / (NP - 1)
    hw = 0.065 * (1 - f) ** 2 + 0.03 + 0.055 * f ** 3                         # wide at the front panel and up into the knot
    if i > 0:
        L_acc += (path[i] - path[i - 1]).length
    row, uvr = [], []
    K = 8
    for k in range(K + 1):
        g = math.pi + 2 * math.pi * k / K; cx, cy = math.cos(g), math.sin(g)
        row.append(p + nn * (0.012 + 0.009 * (sgp(cx, 0.4) + 1)) + side * hw * sgp(cy, 0.4))
        uvr.append((L_acc * 3, 0.15 + 0.6 * (0.5 + 0.5 * sgp(cy, 0.4))))
    P.append(row); UV.append(uvr)
strip = grid_obj('TateMitsu', P, UV, MAW)
push_out(strip, 0.01)
# sagari: stiff cords tucked under the front of the belt
SAG = []
NS = 17
for j in range(NS):
    a = -0.98 + 1.96 * j / (NS - 1)
    th = a
    z0 = float(belt_zc(th)) - 0.05
    rr = lerp_th(WRAPS[0][2], th) + 0.004
    top = Vector((rr * math.sin(th), CY - rr * math.cos(th), z0))
    L = 0.215 - 0.04 * abs(a) ** 2 + 0.012 * math.sin(j * 2.3)
    out = Vector((math.sin(th), -math.cos(th), 0))
    P, UV = [], []
    for i in range(6):
        f = i / 5
        c = top + Vector((0, 0, -L * f)) + out * (0.012 * f)
        rad = 0.0105 - 0.003 * f
        row, uvr = [], []
        for k in range(7):
            g = 2 * math.pi * k / 6
            sd = Vector((math.cos(th), math.sin(th), 0))
            row.append(c + sd * math.cos(g) * rad + out * math.sin(g) * rad)
            uvr.append((k / 6 * 0.05 + j * 0.07, 0.3 + 0.5 * f))
        P.append(row); UV.append(uvr)
    o = grid_obj('Sagari', P, UV, MAW, cap_i=True)
    push_out(o, 0.012)
    SAG.append((o, top))

# ---------------------------------------------------------------- hair: an oiled cap, combed toward the topknot
POLE = Vector((0, 0.32, 1)).normalized()
PU = Vector((1, 0, 0)); PV = POLE.cross(PU).normalized()
def hairline(phi):            # elevation (radians, from the skull centre) of the hairline at azimuth phi (0 = front)
    pts = [(0.0, 0.62), (0.6, 0.56), (1.05, 0.36), (1.35, 0.17), (1.6, 0.22), (1.95, 0.12), (2.4, -0.38), (2.8, -0.62), (math.pi, -0.68)]
    return float(np.interp(abs(phi), [p[0] for p in pts], [p[1] for p in pts]))
def is_hair(dr):
    phi = math.atan2(dr.x, -dr.y); el = math.asin(max(-1, min(1, dr.z)))
    return el > hairline(phi)
def pdir(beta, a): return (POLE * math.cos(beta) + (PU * math.cos(a) + PV * math.sin(a)) * math.sin(beta)).normalized()
def skull(dr):
    l, nrm = hit(HC + dr * 0.45, -dr, 0.45); return l, nrm
NA, NE = 72, 14
B0 = 0.07
P, UV = [], []
for kk in range(NA + 1):
    a = 2 * math.pi * kk / NA
    bmax = B0
    while bmax < 2.6 and is_hair(pdir(bmax + 0.01, a)): bmax += 0.01
    row, uvr = [], []
    for j in range(NE + 1):
        beta = B0 + (bmax - B0) * (j / NE) ** 0.9
        dr = pdir(beta, a); l, nrm = skull(dr)
        phi = math.atan2(dr.x, -dr.y); el = math.asin(dr.z)
        tabo = 0.03 * math.exp(-((abs(phi) - math.pi) / 0.85) ** 2) * math.exp(-((el + 0.18) / 0.3) ** 2)   # the bulging tabo
        edge = min(1.0, (NE - j) / 3.0)                                          # thin out to nothing at the hairline
        groove = 0.0025 * (0.5 + 0.5 * math.cos(a * 40)) * edge
        row.append(l + nrm * (-0.0012 + 0.0095 * edge ** 0.6 + tabo * edge + groove))
        uvr.append((kk / NA, 0.05 + 0.9 * j / NE))
    P.append(row); UV.append(uvr)
cap = grid_obj('HairCap', P, UV, HAIR)
# the crown: the cap's pole hole is closed by the root of the topknot
T, Tn = skull(POLE)
T = T + Tn * 0.012
TF = (Vector((0, -1, 0)) - POLE * POLE.dot(Vector((0, -1, 0)))).normalized()    # forward along the scalp at the crown
TS = TF.cross(POLE).normalized()
o = sphere('TopknotRoot', (0, 0, 0), (1, 1, 1), HAIR, 20, 12)
for v in o.data.vertices:      # an ellipsoid along the crown frame
    c_ = v.co.copy(); v.co = T + TF * 0.005 + POLE * 0.01 + TS * c_.x * 0.034 + TF * c_.y * 0.05 + POLE * c_.z * 0.03
o.data.update()
o = sphere('TopknotTail', (0, 0, 0), (1, 1, 1), HAIR, 16, 10)
for v in o.data.vertices:      # the gathered hair behind the tie, flattened onto the crown
    c_ = v.co.copy(); v.co = T - TF * 0.022 + TS * c_.x * 0.03 + TF * c_.y * 0.034 + POLE * (c_.z * 0.02 - 0.004)
o.data.update()
for k, dz in enumerate((-0.006, 0.01)):          # the white motoyui cord, two turns round the root
    bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.0058, major_segments=20, minor_segments=6,
                                     location=tuple(T + TF * dz + POLE * 0.01), rotation=TF.to_track_quat('Z', 'Y').to_euler())
    tor = bpy.context.object; tor.scale = (1.2, 0.95, 1.0)
    prim_obj('Motoyui', WHITE)
# the ginkgo-leaf fan: the topknot folded forward and spread over the crown, its rim curling up
FP = T + TF * 0.018 + Vector((0, 0, 0.012))
FF = Vector((TF.x, TF.y, 0)).normalized()
NFA, NFR = 25, 9
P, UV = [], []
for i in range(NFA):
    ph = -1.0 + 2.0 * i / (NFA - 1)
    Rm = 0.115 * (1 - 0.2 * math.exp(-(ph / 0.12) ** 2)) * (0.82 + 0.18 * math.cos(ph))     # notched ginkgo rim
    row, uvr = [], []
    for j in range(NFR + 1):
        f = j / NFR; rho = 0.01 + (Rm - 0.01) * f
        q = FP + (FF * math.cos(ph) + TS * math.sin(ph) * 1.2) * rho
        dr = (q - HC).normalized(); l, nrm = skull(dr)
        rest = (l - HC).length + 0.026                                    # never closer to the skull than this
        q = q + Vector((0, 0, 0.012 * f + 0.026 * f ** 2.5 + 0.0018 * math.cos(ph * 20) * f ** 0.5))
        if (q - HC).length < rest: q = HC + (q - HC).normalized() * rest
        row.append(q)
        uvr.append(((ph + 1.0) / 2.0, 0.08 + 0.85 * f))
    P.append(row); UV.append(uvr)
fan = grid_obj('Ginkgo', P, UV, HAIR)
sol = fan.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.02; sol.offset = -1; sol.use_rim = True
bpy.context.view_layer.objects.active = fan; bpy.ops.object.modifier_apply(modifier='sol')
# a neck of gathered hair from the tie into the fan
P, UV = [], []
for i in range(6):
    f = i / 5; c = T + TF * (0.012 + 0.035 * f) + POLE * (0.016 + 0.02 * math.sin(f * math.pi * 0.8))
    row, uvr = [], []
    for k in range(13):
        g = 2 * math.pi * k / 12; rw = 0.026 + 0.03 * f; rh = 0.022 - 0.004 * f
        row.append(c + TS * math.cos(g) * rw + POLE * math.sin(g) * rh); uvr.append((k / 12, 0.2 + 0.2 * f))
    P.append(row); UV.append(uvr)
grid_obj('TopknotNeck', P, UV, HAIR)

# ---------------------------------------------------------------- face: small dark eyes with glints, strong brows, a small mouth
def on_face(x, z):
    l, n = hit((x, -1, z), (0, 1, 0)); return l, n
def strip_on_skin(name, ctrl, hw0, hw1, ht, off, m_, n=10):
    pts = []
    for i in range(n):
        t = i / (n - 1) * (len(ctrl) - 1); k = min(int(t), len(ctrl) - 2); f = t - k
        p = Vector(ctrl[k]).lerp(Vector(ctrl[k + 1]), f)
        l, nrm = on_face(p.x, p.z); pts.append((l, nrm))
    P, UV = [], []
    for i, (p, nrm) in enumerate(pts):
        tng = (pts[min(i + 1, n - 1)][0] - pts[max(i - 1, 0)][0]).normalized()
        side = nrm.cross(tng).normalized(); f = i / (n - 1); hw = hw0 + (hw1 - hw0) * f
        tap = (1 - abs(2 * f - 1) ** 4) ** 0.3
        row = []
        for k in range(7):
            g = 2 * math.pi * k / 6
            row.append(p + nrm * (off + ht * tap * (1 + math.sin(g)) / 2) + side * hw * tap * math.cos(g))
        P.append(row); UV.append([(0.5, 0.5)] * 7)
    return grid_obj(name, P, UV, m_, cap_i=True)
for s in S2:
    l, n_ = on_face(s * 0.05, 1.692)
    sphere('Eye', l + Vector((0, 0.003, 0)), (0.0135, 0.008, 0.017), INK, 12, 8, (0, 0, s * 0.3))
    sphere('EyeHi', l + Vector((-s * 0.004, -0.0075, 0.006)), (0.0042, 0.003, 0.0048), WHITE, 8, 6)
    strip_on_skin('Brow', [(s * 0.02, -0.2, 1.733), (s * 0.055, -0.2, 1.745), (s * 0.09, -0.2, 1.745)], 0.0105, 0.007, 0.007, 0.001, INK)
strip_on_skin('Mouth', [(-0.028, -0.2, 1.606), (-0.01, -0.2, 1.6), (0.01, -0.2, 1.6), (0.028, -0.2, 1.606)], 0.0042, 0.0042, 0.003, 0.0, INK, 12)

# ---------------------------------------------------------------- skin colour: per-vertex paint + crease occlusion, baked to a texture
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(78), island_margin=0.005, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
body.data.uv_layers[0].name = 'UVMap'

def all_bvh():
    vs, ps = [], []
    for o in scn.objects:
        if o.type != 'MESH': continue
        b = len(vs); vs += [o.matrix_world @ v.co for v in o.data.vertices]; ps += [[b + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(vs, ps)
def paint_skin():
    me = body.data; N = len(me.vertices)
    co = np.array([v.co for v in me.vertices]); nr = np.array([v.normal for v in me.vertices])
    x, y, z = co.T; nz = nr[:, 2]
    def blob(c, r): return np.exp(-np.sum((co - np.array(tuple(c))) ** 2, axis=1) / r ** 2)
    fl = np.zeros(N)
    def add(v, k=1.0):
        nonlocal fl; fl = np.maximum(fl, v * k)
    for s in S2:
        add(blob(KNEE[s] + Vector((0, -0.13, 0.01)), 0.1))
        add(blob(E[s] + Vector((0, 0.09, 0.01)), 0.075))
        xh, yh, nin = hand_frame(s)
        add(blob(W[s] + xh * 0.12 - nin * 0.03, 0.05))                    # knuckles (back of the hand)
        add(blob(W[s] + xh * 0.19, 0.04), 0.8)                            # fingertips
        add(blob((s * 0.08, -0.15, 1.636), 0.04))                         # cheeks
        add(blob((s * 0.145, 0.012, 1.68), 0.05))                         # ears
        add(blob((s * 0.42, 0.03, 1.50), 0.17), 0.75)                     # tops of the shoulders
        add(blob((s * 0.30, -0.24, 0.03), 0.08), 0.8)                     # toes
        add(blob((s * 0.30, 0.10, 0.04), 0.07), 0.7)                      # heels
        add(blob((s * 0.15, 0.30, 0.66), 0.12), 0.35)                     # under the buttocks
    add(np.clip(sstep(0.0, 0.1, y) * gau(z - 1.53, 0.08) * np.exp(-(x / 0.17) ** 4), 0, 1), 0.85)   # back of the neck
    add(blob((0, -0.19, 1.655), 0.035), 0.7)                              # nose tip
    light = np.clip(sstep(-0.2, -0.42, y) * gau(z - 1.0, 0.18) * gau(x, 0.3), 0, 1)
    base = np.array(srgb('efb48d')); belly = np.array(srgb('f6c7a5')); flush = np.array(srgb('e07467'))
    crease = np.array(srgb('a8584c')); areola = np.array(srgb('c97c68'))
    col = base[None] * (1 - light[:, None]) + belly[None] * light[:, None]
    col = col * (1 - 0.8 * fl[:, None]) + flush[None] * 0.8 * fl[:, None]
    for s in S2:
        l, _ = hit((s * 0.17, -1, 1.205), (0, 1, 0))
        ar = blob(l, 0.024) ** 2 * 0.8; col = col * (1 - ar[:, None]) + areola[None] * ar[:, None]
    nv = blob(hit((0, -1, 0.99), (0, 1, 0))[0], 0.016) * 0.6; col = col * (1 - nv[:, None]) + crease[None] * nv[:, None]
    # crease occlusion, ray traced against the skin, belt and hair
    B = all_bvh()
    gold = math.pi * (3 - math.sqrt(5)); NR = 20
    hemi = [Vector((math.cos(gold * i) * math.sqrt((i + 0.5) / NR), math.sin(gold * i) * math.sqrt((i + 0.5) / NR), math.sqrt(1 - (i + 0.5) / NR))) for i in range(NR)]   # cosine-weighted
    occ = np.zeros(N)
    for vi, v in enumerate(me.vertices):
        n_ = v.normal; t1 = n_.orthogonal().normalized(); t2 = n_.cross(t1)
        p = v.co + n_ * 0.003; h_ = 0
        for d in hemi:
            dw = t1 * d.x + t2 * d.y + n_ * d.z
            loc, _, _, dist = B.ray_cast(p, dw, 0.22)
            if loc is not None: h_ += 1.0 - 0.6 * dist / 0.22
        occ[vi] = h_ / NR
    occ = np.clip((occ - 0.08) / 0.6, 0, 1) ** 1.2
    col = col * (1 - 0.55 * occ[:, None]) + crease[None] * 0.55 * occ[:, None]
    col *= (0.95 + 0.06 * nz)[:, None]                                   # a touch of top light for the toon read
    ca = me.color_attributes.new('Paint', 'FLOAT_COLOR', 'POINT')
    rgba = np.ones((N, 4)); rgba[:, :3] = np.clip(col, 0, 1)
    ca.data.foreach_set('color', rgba.ravel())
paint_skin()

SKIN_IMG = bpy.data.images.new('SkinTex', 1024, 1024, alpha=False)
SKIN_IMG.generated_color = (*srgb('e9ab86'), 1)
SKIN = bpy.data.materials.new('Skin'); SKIN.use_nodes = True; nt = SKIN.node_tree; nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Paint'
tc = nt.nodes.new('ShaderNodeTexCoord')
def noise(scale, detail):
    nn = nt.nodes.new('ShaderNodeTexNoise'); nn.inputs['Scale'].default_value = scale; nn.inputs['Detail'].default_value = detail
    nt.links.new(tc.outputs['Object'], nn.inputs['Vector']); return nn
n1, n2 = noise(9, 4), noise(45, 2)
r1 = nt.nodes.new('ShaderNodeValToRGB'); r1.color_ramp.elements[0].position = 0.3; r1.color_ramp.elements[1].position = 0.7
r1.color_ramp.elements[0].color = (0.93, 0.89, 0.9, 1); r1.color_ramp.elements[1].color = (1.04, 1.03, 1.02, 1)
r2 = nt.nodes.new('ShaderNodeValToRGB'); r2.color_ramp.elements[0].position = 0.35; r2.color_ramp.elements[1].position = 0.65
r2.color_ramp.elements[0].color = (0.96, 0.95, 0.95, 1); r2.color_ramp.elements[1].color = (1.02, 1.02, 1.02, 1)
nt.links.new(n1.outputs['Fac'], r1.inputs['Fac']); nt.links.new(n2.outputs['Fac'], r2.inputs['Fac'])
m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs['Factor'].default_value = 1
m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs['Factor'].default_value = 1
nt.links.new(ca.outputs['Color'], m1.inputs[6]); nt.links.new(r1.outputs['Color'], m1.inputs[7])
nt.links.new(m1.outputs[2], m2.inputs[6]); nt.links.new(r2.outputs['Color'], m2.inputs[7])
nt.links.new(m2.outputs[2], em.inputs['Color']); nt.links.new(em.outputs['Emission'], outn.inputs['Surface'])
imn = nt.nodes.new('ShaderNodeTexImage'); imn.image = SKIN_IMG; nt.nodes.active = imn
body.data.materials.append(SKIN)
scn.cycles.samples = 8
for o in scn.objects: o.select_set(o == body)
bpy.context.view_layer.objects.active = body
bpy.ops.object.bake(type='EMIT', margin=16, use_clear=False)
SKIN_IMG.pack()
if 'savetex' in OPT:
    for im in (SKIN_IMG, SILK_N, HAIR_IMG): im.save_render(os.path.join(OUT, 'tex_' + im.name + '.png'))
# the final skin material: the baked texture into a principled BSDF
nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
imn = nt.nodes.new('ShaderNodeTexImage'); imn.image = SKIN_IMG; imn.name = 'Tex'
nt.links.new(imn.outputs['Color'], bs.inputs['Base Color']); nt.links.new(bs.outputs['BSDF'], outn.inputs['Surface'])
bs.inputs['Roughness'].default_value = 0.5; bs.inputs['Specular IOR Level'].default_value = 0.4
bs.inputs['Subsurface Weight'].default_value = 0.08; bs.inputs['Subsurface Radius'].default_value = (0.3, 0.12, 0.08)
bs.inputs['Subsurface Scale'].default_value = 0.05
body.data.color_attributes.remove(body.data.color_attributes['Paint'])

# ---------------------------------------------------------------- armature (A-pose rest)
rig_data = bpy.data.armatures.new('SumoRig'); rig = bpy.data.objects.new('SumoRig', rig_data); scn.collection.objects.link(rig)
for o in scn.objects: o.select_set(False)
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
FWD, UP = Vector((0, -1, 0)), Vector((0, 0, 1))
BONES = {}
def bone(name, head, tail, parent=None, roll_to=FWD):
    b = rig_data.edit_bones.new(name); b.head = Vector(head); b.tail = Vector(tail); b.use_connect = False
    if parent: b.parent = rig_data.edit_bones[parent]
    b.align_roll(roll_to); BONES[name] = parent; return b
bone('hips', (0, 0.05, 0.80), (0, 0.05, 0.98))
bone('spine', (0, 0.05, 0.98), (0, 0.04, 1.18), 'hips')
bone('belly', (0, -0.22, 0.97), (0, -0.44, 0.97), 'spine', UP)
bone('chest', (0, 0.04, 1.18), (0, 0.03, 1.42), 'spine')
bone('neck', (0, 0.03, 1.42), (0, 0.0, 1.60), 'chest')
bone('head', (0, 0.0, 1.60), (0, 0.0, 1.86), 'neck')
for s in S2:
    sd = '.L' if s > 0 else '.R'                      # +X is the character's left (front faces -Y)
    xh = D2[s]
    bone('shoulder' + sd, (s * 0.07, 0.05, 1.43), J[s], 'chest')
    bone('upper_arm' + sd, J[s], E[s], 'shoulder' + sd)
    bone('forearm' + sd, E[s], W[s], 'upper_arm' + sd)
    bone('hand' + sd, W[s], W[s] + xh * 0.18, 'forearm' + sd)
    bone('thigh' + sd, HIP[s], KNEE[s], 'hips')
    bone('shin' + sd, KNEE[s], ANK[s], 'thigh' + sd)
    bone('foot' + sd, ANK[s], TOE[s], 'shin' + sd, UP)
bpy.ops.object.mode_set(mode='OBJECT')
ORDER = []
def _ord(n):
    if n in ORDER: return
    if BONES[n]: _ord(BONES[n])
    ORDER.append(n)
for n in BONES: _ord(n)

# ---------------------------------------------------------------- weights: bone heat on the skin
for o in scn.objects: o.select_set(o in (body, rig))
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
def unweighted(o):
    return [v.index for v in o.data.vertices if sum(g.weight for g in v.groups) < 1e-3]
uw = unweighted(body)
print('bone heat: unweighted verts', len(uw), 'of', len(body.data.vertices))
WEIGHT_MODE = 'heat'
if len(uw) > 0.05 * len(body.data.vertices):
    WEIGHT_MODE = 'envelope'
    body.parent = None; body.modifiers.clear(); body.vertex_groups.clear()
    for b in rig_data.bones: b.envelope_distance = 0.25; b.head_radius = b.tail_radius = 0.12
    for o in scn.objects: o.select_set(o in (body, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
    uw = unweighted(body)
if uw:   # fill any stragglers from their nearest weighted neighbours
    kd = KDTree(len(body.data.vertices)); uws = set(uw)
    for v in body.data.vertices:
        if v.index not in uws: kd.insert(v.co, v.index)
    kd.balance()
    for i in uw:
        _, j, _ = kd.find(body.data.vertices[i].co)
        for g in body.data.vertices[j].groups: body.vertex_groups[g.group].add([i], g.weight, 'REPLACE')
print('weights:', WEIGHT_MODE, 'filled', len(uw))
bpy.ops.object.select_all(action='DESELECT')
# a little relaxation of the weights over the skin (smoother folds at the hips / shoulders)
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
try:
    bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=3)
except Exception as ex: print('smooth weights skipped', ex)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# under the belt the skin is bound to the hips (cloth and skin then move as one; the legs still bend below it)
hg = body.vertex_groups['hips']
for v in body.data.vertices:
    c = v.co
    if abs(c.x) > 0.56 or not (0.5 < c.z < 1.1): continue
    th = math.atan2(c.x, -(c.y + 0.03)); dz = abs(c.z - float(belt_zc(th)))
    k = 0.85 * float(sstep(0.15, 0.07, dz))
    if k <= 0: continue
    for g in v.groups:
        if body.vertex_groups[g.group].name != 'hips': g.weight *= (1 - k)
    cur = next((g.weight for g in v.groups if g.group == hg.index), 0.0)
    hg.add([v.index], cur * (1 - k) + k, 'REPLACE')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

# the rest of the character: weights from the skin (nearest-vertex blend) or a rigid anchor
GN = [g.name for g in body.vertex_groups]
bco = [v.co.copy() for v in body.data.vertices]
bw = [{body.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-4} for v in body.data.vertices]
KD = KDTree(len(bco))
for i, c in enumerate(bco): KD.insert(c, i)
KD.balance()
def skin_weights(p, k=6):
    acc = {}
    tot = 0
    for c, i, d in KD.find_n(p, k):
        w = 1 / (d + 0.004) ** 2; tot += w
        for g, x in bw[i].items(): acc[g] = acc.get(g, 0) + x * w
    s_ = sum(acc.values()) or 1
    return {g: x / s_ for g, x in acc.items() if x / s_ > 0.01}
def set_weights(o, fn):
    for g in GN:
        if g not in o.vertex_groups: o.vertex_groups.new(name=g)
    for v in o.data.vertices:
        for g, x in fn(v.co).items(): o.vertex_groups[g].add([v.index], x, 'REPLACE')
head_only = lambda p: {'head': 1.0}
knot_anchor = skin_weights(Vector((0, yb - 0.06, ZB)))
for o in list(scn.objects):
    if o.type != 'MESH' or o == body: continue
    nm = o.name.split('.')[0]
    if nm in ('Eye', 'EyeHi', 'Brow', 'Mouth', 'TopknotRoot', 'TopknotTail', 'Motoyui', 'Ginkgo', 'TopknotNeck'): set_weights(o, head_only)
    elif nm.startswith('Knot'): set_weights(o, lambda p: knot_anchor)
    elif nm == 'Sagari':
        top = [t for (so, t) in SAG if so == o][0]; aw = skin_weights(top)
        aw = {g: x for g, x in aw.items() if not g.startswith(('thigh', 'shin'))} or {'hips': 1.0}
        set_weights(o, lambda p, aw=aw: aw)
    else: set_weights(o, skin_weights)

# ---------------------------------------------------------------- one skinned mesh
meshes = [o for o in scn.objects if o.type == 'MESH']
for o in scn.objects: o.select_set(o in meshes)
bpy.context.view_layer.objects.active = body
body.parent = None
for mm in list(body.modifiers): body.modifiers.remove(mm)
bpy.ops.object.join()
hero = bpy.context.object; hero.name = 'Sumo'; hero.data.name = 'Sumo'
hero.data.validate(verbose=False)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)     # glTF skins carry 4 influences
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
for g in list(hero.vertex_groups):
    if g.name not in BONES: hero.vertex_groups.remove(g)
hero.parent = rig
am = hero.modifiers.new('Armature', 'ARMATURE'); am.object = rig
tris = sum(len(p.vertices) - 2 for p in hero.data.polygons)
uw = unweighted(hero)
print('TRIANGLES', tris, 'verts', len(hero.data.vertices), 'unweighted', len(uw))
print('BONES', ORDER)
print('MATERIALS', [m_.name for m_ in hero.data.materials])

# ---------------------------------------------------------------- export (rest pose), plus the red-mawashi variant
def export(path):
    rig_data.pose_position = 'REST'
    for o in scn.objects: o.select_set(o in (hero, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_skins=True, export_animations=False,
                              export_apply=False, export_rest_position_armature=True, export_yup=True)
    rig_data.pose_position = 'POSE'
MAW_TEX = MAW.node_tree.nodes['Tex']
export(os.path.join(OUT, 'sumo2.glb'))
MAW_TEX.image = SILK_R; export(os.path.join(OUT, 'sumo2_red.glb')); MAW_TEX.image = SILK_N
MAW_RED = MAW.copy(); MAW_RED.name = 'MawashiRed'; MAW_RED.node_tree.nodes['Tex'].image = SILK_R

# ---------------------------------------------------------------- posing (via the armature)
def two_bone(a, c, l1, l2, pole):
    d = c - a; L = min(d.length, l1 + l2 - 1e-4); dn = d.normalized()
    x = (l1 * l1 - l2 * l2 + L * L) / (2 * L); h = math.sqrt(max(l1 * l1 - x * x, 0))
    pn = (pole - dn * pole.dot(dn)).normalized()
    return a + dn * x + pn * h
def apply_pose(rg, spec, hips_off=Vector()):
    posed = {}
    for pb in rg.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for name in ORDER:
        b = rg.data.bones[name]; R = b.matrix_local
        inh = posed[b.parent.name] @ b.parent.matrix_local.inverted() @ R if b.parent else Matrix.Translation(hips_off) @ R
        head = inh.translation.copy(); rot = inh.to_3x3()
        if name in spec:
            dd, zz = spec[name](head) if callable(spec[name]) else spec[name]
            dd = Vector(dd).normalized()
            if zz is None:
                rot = rot.col[1].rotation_difference(dd).to_matrix() @ rot
            else:
                zz = Vector(zz); zz = (zz - dd * zz.dot(dd)).normalized(); xx = dd.cross(zz)
                rot = Matrix((xx, dd, zz)).transposed()
        M = Matrix.Translation(head) @ rot.to_4x4(); posed[name] = M
        rg.pose.bones[name].matrix = M
        bpy.context.view_layer.update()
def lean(deg):
    a = math.radians(deg); return ((0, -math.sin(a), math.cos(a)), (0, -math.cos(a), -math.sin(a)))
def stance_spec():
    sp = {'hips': lean(4), 'spine': lean(9), 'chest': lean(13), 'neck': lean(24), 'head': lean(2)}
    for s in S2:
        sd = '.L' if s > 0 else '.R'
        lt = (rig_data.bones['thigh' + sd].length, rig_data.bones['shin' + sd].length)
        ank = Vector((s * 0.52, 0.0, 0.11)); pole = Vector((s * 0.8, -0.6, 0.0))
        sp['thigh' + sd] = (lambda h, ank=ank, pole=pole, lt=lt: (two_bone(h, ank, lt[0], lt[1], pole) - h, pole))
        sp['shin' + sd] = (lambda h, ank=ank, pole=pole: (ank - h, pole))
        sp['foot' + sd] = ((s * 0.42, -0.86, -0.28), (0, 0, 1))
        sp['shoulder' + sd] = ((s * 0.93, -0.3, 0.05), None)
        sp['upper_arm' + sd] = ((s * 0.5, -0.72, -0.48), None)
        sp['forearm' + sd] = ((s * 0.16, -0.98, -0.02), None)
        sp['hand' + sd] = ((s * 0.06, -0.78, 0.6), (-s, 0, 0))
    return sp
STANCE_OFF = Vector((0, 0.03, -0.2))

# ---------------------------------------------------------------- previews
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('c9d3e0'), 1); bg.inputs['Strength'].default_value = 0.75
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 3.6; sun.data.color = srgb('ffe2bc'); sun.data.angle = 0.12
sun.rotation_euler = (math.radians(48), 0, math.radians(-145))       # warm key from above, behind-right of the hero
bpy.ops.mesh.primitive_plane_add(size=40); gnd = bpy.context.object; gnd.name = 'Ground'
GM = bpy.data.materials.new('Sand'); GM.use_nodes = True; gt = GM.node_tree; gb = gt.nodes['Principled BSDF']
gn = gt.nodes.new('ShaderNodeTexNoise'); gn.inputs['Scale'].default_value = 3.0; gn.inputs['Detail'].default_value = 6
gr = gt.nodes.new('ShaderNodeValToRGB'); gr.color_ramp.elements[0].color = (*srgb('caa577'), 1); gr.color_ramp.elements[1].color = (*srgb('e2c595'), 1)
gt.links.new(gn.outputs['Fac'], gr.inputs['Fac']); gt.links.new(gr.outputs['Color'], gb.inputs['Base Color']); gb.inputs['Roughness'].default_value = 0.95
gnd.data.materials.append(GM)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
scn.render.resolution_x = scn.render.resolution_y = RES
scn.view_settings.view_transform = 'Standard'
DEBUG = {'head', 'belt', 'face', 'stance_top', 'rest_back', 'stance_side', 'headtop'}
def shoot(name, pos, look, lens=50, w=None, h=None):
    if (SHOTS and name not in SHOTS) or (not SHOTS and name in DEBUG): return
    scn.render.resolution_x = w or RES; scn.render.resolution_y = h or RES
    cam.data.lens = lens; cam.location = pos
    cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = os.path.join(OUT, 'prev_' + name + '.png'); bpy.ops.render.render(write_still=True)
    print('rendered', name)

shoot('rest', (0.9, -5.2, 1.35), (0, 0, 0.95), 50)
shoot('rest_back', (-1.0, 5.0, 1.8), (0, 0, 0.95), 50)
shoot('head', (-0.5, 0.75, 2.35), (0, 0.0, 1.75), 50)
shoot('face', (0.35, -0.95, 1.75), (0, 0, 1.66), 50)
shoot('belt', (-0.6, 1.55, 1.25), (0, 0.15, 0.82), 50)
shoot('headtop', (0.0, 0.5, 2.9), (0, 0.02, 1.8), 70)
apply_pose(rig, stance_spec(), STANCE_OFF)
shoot('stance_back', (-1.5, 3.3, 2.8), (0, -0.1, 0.8), 50)
shoot('stance_front', (1.5, -3.4, 1.6), (0, -0.2, 0.8), 50)
shoot('stance_top', (0.0, 2.2, 4.0), (0, -0.1, 0.8), 50)
# the stance as a one-frame clip ("stance") for the game to pose the skinned model with
act = bpy.data.actions.new('stance'); rig.animation_data_create(); rig.animation_data.action = act
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    for f in (1, 2): pb.keyframe_insert('location', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f)
for o in scn.objects: o.select_set(o in (hero, rig))
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'sumo2_stance.glb'), export_format='GLB', use_selection=True, export_skins=True,
                          export_animations=True, export_apply=False, export_rest_position_armature=True, export_yup=True)
rig.animation_data.action = None
# the game camera: two of them squaring up, 1.6 m apart, the hero with its back to the camera
if not SHOTS or SHOTS & {'game', 'zoom', 'toon'}:
    rig2 = rig.copy(); scn.collection.objects.link(rig2)
    hero2 = hero.copy(); hero2.data = hero.data.copy(); scn.collection.objects.link(hero2)
    hero2.parent = rig2; hero2.modifiers['Armature'].object = rig2
    for i, m_ in enumerate(hero2.data.materials):
        if m_ == MAW: hero2.data.materials[i] = MAW_RED
    apply_pose(rig2, stance_spec(), STANCE_OFF)
    rig.location = (0, -0.8, 0); rig.rotation_euler = (0, 0, math.pi)     # hero: faces +Y, back to the camera
    rig2.location = (0, 0.8, 0)
    el, az = math.radians(50), 0.35
    gc = (12 * math.cos(el) * math.sin(az), -12 * math.cos(el) * math.cos(az), 12 * math.sin(el))
    sun.rotation_euler = (math.radians(45), 0, math.radians(-30))
    shoot('game', gc, (0, 0, 0.7), 50, 800, 600)
    shoot('zoom', gc, (0, 0, 0.7), 150, 800, 600)
    if not SHOTS or 'toon' in SHOTS:       # flat toon check: base colour / texture, a two-tone N.L step, no specular
        Ld = (sun.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
        for mm in bpy.data.materials:
            if not mm.use_nodes or mm == GM: continue
            t = mm.node_tree; b = t.nodes.get('Principled BSDF')
            if b is None: continue
            src = b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].links else None
            col = t.nodes.new('ShaderNodeRGB'); col.outputs[0].default_value = b.inputs['Base Color'].default_value
            geo = t.nodes.new('ShaderNodeNewGeometry'); dot = t.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
            dot.inputs[1].default_value = Ld; t.links.new(geo.outputs['Normal'], dot.inputs[0])
            st = t.nodes.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = 0.05
            t.links.new(dot.outputs['Value'], st.inputs[0])
            sh = t.nodes.new('ShaderNodeMix'); sh.data_type = 'RGBA'; sh.blend_type = 'MULTIPLY'; sh.inputs['Factor'].default_value = 1
            t.links.new(src if src else col.outputs[0], sh.inputs[6]); sh.inputs[7].default_value = (0.62, 0.58, 0.7, 1)
            fin = t.nodes.new('ShaderNodeMix'); fin.data_type = 'RGBA'
            t.links.new(st.outputs['Value'], fin.inputs[0]); t.links.new(sh.outputs[2], fin.inputs[6])
            t.links.new(src if src else col.outputs[0], fin.inputs[7])
            emn = t.nodes.new('ShaderNodeEmission'); t.links.new(fin.outputs[2], emn.inputs['Color'])
            t.links.new(emn.outputs['Emission'], t.nodes['Material Output'].inputs['Surface'])
        shoot('toon', gc, (0, 0, 0.7), 150, 800, 600)
print('done')
