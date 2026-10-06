# Kumite hero, soft variant: a simplified rikishi in a soft, chunky, matte-pastel style (think "Little Kitty, Big City"
# humans: clean rounded forms, a readable silhouette, almost no surface detail). Built and rigged by script (Blender 4.2).
#   python tools/blender/sumo_soft.py  OUT_DIR  [samples=32] [res=800] [render=0]
# Writes OUT_DIR/sumo_soft.glb (navy mawashi), OUT_DIR/sumo_soft_red.glb (dark red mawashi), OUT_DIR/sumo_soft_stance.glb
# (with a one-frame 'stance' action) and one preview, OUT_DIR/prev_stance.png (two of them squaring up).
#
# Derived from sumo2.py, same skeleton (20 bones, same names, A-pose rest) and export layout, but
#   body   a handful of big overlapping volumes (belly, chest, back, hips, shoulders, limbs, mitten hands, simple feet)
#          fused by a coarse voxel remesh and smoothed hard: no sculpted folds, grooves, navel or muscle definition.
#   skin   one flat warm colour with a very soft blush on the cheeks (baked to a small texture), matte.
#   face   two small dark dot eyes; no nose, mouth or brows.
#   hair   a smooth black cap and one simple chonmage lying forward on the crown.
#   belt   one clean thick band, a single knot block at the back, the front strip, a few chunky sagari strips.
# Blender is Z-up with the front facing -Y; the glTF export converts to Y-up. Real scale: about 1.85 m, origin at the feet.
import bpy, math, sys, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ARGS = [a for a in sys.argv[1:] if not a.endswith('.py')]
OPT = dict(a.split('=', 1) for a in ARGS if '=' in a)
POS = [a for a in ARGS if '=' not in a and not a.startswith('-')]
OUT = POS[0] if POS else '/tmp/sumo_soft'
os.makedirs(OUT, exist_ok=True)
SAMPLES, RES = int(OPT.get('samples', 32)), int(OPT.get('res', 800))
RENDER = OPT.get('render', '1') != '0'

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def sstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def mat(name, rgb, rough=0.85, spec=0.25):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = spec
    return m

NAVY, RED = srgb('2b3a72'), srgb('8a2a32')
MAW = mat('Mawashi', NAVY, 0.8, 0.25)
HAIR = mat('Hair', srgb('211e27'), 0.7, 0.3)
INK = mat('Ink', srgb('1d1619'), 0.6, 0.3)
SKIN_RGB, BLUSH_RGB = srgb('f3c4a2'), srgb('f19a8e')

# ---------------------------------------------------------------- skeleton landmarks (rest A-pose), as sumo2
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

# ---------------------------------------------------------------- body: a few big soft volumes fused into one skin
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

# torso: one big round belly, a broad chest/back, a full seat (no cleft)
# fat and firm: one solid round mochi of a trunk (no sag, nothing hanging), full round back and sides, wide hips
ell((0, 0.03, 0.86), (0.42, 0.29, 0.26))            # wide hips and a full seat
ell((0, -0.03, 1.06), (0.44, 0.40, 0.42))           # the core: round all the way round
ell((0, -0.11, 1.02), (0.38, 0.36, 0.34))           # the belly: high, full, tight
ell((0, 0.01, 1.27), (0.41, 0.31, 0.27))            # chest and a full rounded back
# broad soft shoulders and a short thick neck
for s in S2:
    limb((s * 0.06, 0.05, 1.50), (s * 0.32, 0.03, 1.43), 0.12, 0.11)    # shoulder slope
    ell((s * 0.39, 0.01, 1.38), (0.17, 0.17, 0.165))                   # shoulder ball
limb((0, 0.03, 1.40), (0, 0.01, 1.62), 0.165, 0.145, caps=False)   # short, thick neck
# head: a round skull and full cheeks, small ear nubs
ell(HC, (0.148, 0.158, 0.158))
ell((0, -0.03, 1.635), (0.142, 0.13, 0.11))
for s in S2:
    ell((s * 0.142, 0.015, 1.68), (0.024, 0.036, 0.045))
# arms: thick, smooth, ending in mitten hands (one mitt + a thumb)
for s in S2:
    limb(J[s], E[s], 0.142, 0.106)
    up = D1[s].cross(Vector((0, 1, 0))).normalized()
    if up.z < 0: up = -up
    ell_ax(J[s] + D1[s] * 0.14 + Vector((0, -0.01, 0)), (D1[s], Vector((0, 1, 0)), up), (0.13, 0.115, 0.115))
    limb(E[s], W[s], 0.104, 0.09)                                                       # no pinched wrist
    xh, yh, nin = hand_frame(s); H0 = W[s] + xh * 0.02
    # chunky toy mitt: a thick rounded paddle as wide as the forearm, a soft finger block, a separate rounded thumb
    limb(W[s] - xh * 0.02, H0 + xh * 0.05, 0.088, 0.08, caps=False)                    # wrist, as thick as the forearm
    ell_ax(H0 + xh * 0.085, (xh, yh, nin), (0.105, 0.095, 0.062))                      # palm paddle
    ell_ax(H0 + xh * 0.15, (xh, yh, nin), (0.075, 0.092, 0.058))                        # finger block, rounded tip
    limb(H0 + xh * 0.03 + yh * 0.06 + nin * 0.01, H0 + xh * 0.10 + yh * 0.125 + nin * 0.03, 0.042, 0.038)   # thumb
# legs: massive smooth thighs, thick calves, simple rounded feet
for s in S2:
    limb(HIP[s] + Vector((0, 0, -0.02)), KNEE[s], 0.285, 0.18)
    limb(KNEE[s], ANK[s], 0.172, 0.108)
    ell((s * 0.285, 0.03, 0.31), (0.14, 0.14, 0.17))                   # calf, centred on the shin
    ell((s * 0.30, -0.055, 0.05), (0.115, 0.18, 0.07))                 # foot
    ell((s * 0.30, 0.05, 0.06), (0.09, 0.08, 0.07))                    # heel
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = 'Body'
bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
r = body.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.009
bpy.ops.object.modifier_apply(modifier='rm')
m = body.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); m.factor = 0.9; m.iterations = 40; m.smooth_type = 'LENGTH_WEIGHTED'
bpy.ops.object.modifier_apply(modifier='sm')
m = body.modifiers.new('sm2', 'SMOOTH'); m.factor = 0.6; m.iterations = 20
bpy.ops.object.modifier_apply(modifier='sm2')
co = np.empty(len(body.data.vertices) * 3); body.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
co[:, 2] = np.maximum(co[:, 2], 0.0)                                       # flat soles
body.data.vertices.foreach_set('co', co.ravel()); body.data.update()

BODY_TRIS = int(OPT.get('bodytris', 9300))
for _ in range(4):
    n = sum(len(p.vertices) - 2 for p in body.data.polygons)
    if n <= BODY_TRIS * 1.04: break
    d = body.modifiers.new('dec', 'DECIMATE'); d.ratio = BODY_TRIS / n; d.use_symmetry = True; d.symmetry_axis = 'X'
    bpy.ops.object.modifier_apply(modifier='dec')
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

# ---------------------------------------------------------------- mawashi: one clean thick band
def belt_zc(th): return 0.80 - 0.045 * np.cos(th)          # the belt sits low under the belly, high on the sacrum
CY = -0.03
def skin_r(th, z, r0=0.64):
    d = Vector((math.sin(th), -math.cos(th), 0)); o = Vector((0, CY, z))
    loc, _ = hit(o + d * r0, -d, r0)
    return (loc - o).length if loc else 0.3
NT = 72
THS = [math.pi * 2 * i / NT for i in range(NT)]
WRAPS = []
def lerp_th(arr, th):
    return float(np.interp(th % (2 * math.pi), THS + [2 * math.pi], list(arr) + [arr[0]]))
def cloth_base(th, z):
    r = skin_r(th, z)
    for zf, h, Ro in WRAPS:
        if abs(z - zf(th)) <= h + 0.006: r = max(r, lerp_th(Ro, th))
    return r
def bridge(R):                                 # taut cloth: spans concavities, then smooth
    for _ in range(3): R = np.maximum(R, np.maximum(np.roll(R, 1), np.roll(R, -1)))
    for _ in range(8): R = (np.roll(R, 1) + 2 * R + np.roll(R, -1)) / 4
    return R
def wrap(name, zfun, h, off, t, K=12):
    prof = []
    for k in range(K + 1):
        g = math.pi + 2 * math.pi * k / K
        cx, cy = math.cos(g), math.sin(g); prof.append((h * sgp(cy, 0.45), t * (sgp(cx, 0.45) + 1) / 2))
    dzs = sorted(set(round(dz, 6) for dz, _ in prof))
    Rall = bridge(np.max(np.array([[cloth_base(th, zfun(th) + dz) for th in THS] for dz in dzs]), axis=0))   # one smooth radius
    P, UV = [], []
    for i in range(NT + 1):
        ii = i % NT; th = THS[ii] if i < NT else 2 * math.pi
        zc = zfun(th); row, uvr = [], []
        for dz, dr in prof:
            rr = Rall[ii] + off + dr
            row.append(Vector((rr * math.sin(th), CY - rr * math.cos(th), zc + dz)))
            uvr.append((i / NT * 4.0, 0.5 + 0.5 * dz / h))
        P.append(row); UV.append(uvr)
    o = grid_obj(name, P, UV, MAW)
    WRAPS.append((zfun, h, Rall + off + t)); return o
BAND_H = 0.085
band = wrap('Band', lambda th: float(belt_zc(th)) - 0.01, BAND_H, 0.008, 0.032)
ZB = float(belt_zc(math.pi)) - 0.01

def pad(name, thc, half_w, zc, h, off, t, bulge=0.25, NI=12, K=12):
    """a rounded, pillowed block lying over the band"""
    P, UV = [], []
    for i in range(NI + 1):
        a = -1 + 2 * i / NI
        sz = (1 - abs(a) ** 4) ** 0.25
        th = thc + a * half_w / 0.42
        rr0 = max(cloth_base(th, zc + dz) for dz in np.linspace(-h, h, 5)) + off
        row, uvr = [], []
        for k in range(K + 1):
            g = math.pi + 2 * math.pi * k / K; cx, cy = math.cos(g), math.sin(g)
            dz = h * sz ** 0.5 * sgp(cy, 0.4)
            tt = t * sz * (1 + bulge * (1 - a * a) * (1 - abs(cy)))
            rr = rr0 + tt * (sgp(cx, 0.4) + 1) / 2
            row.append(Vector((rr * math.sin(th), CY - rr * math.cos(th), zc + dz)))
            uvr.append((0.25 + (a + 1) * half_w * 2, 0.5 + 0.5 * dz / h))
        P.append(row); UV.append(uvr)
    return grid_obj(name, P, UV, MAW)
knot = pad('Knot', math.pi, 0.1, ZB + 0.01, 0.105, -0.004, 0.045, bulge=0.3)
yb = CY + lerp_th(WRAPS[-1][2], math.pi)

# the tate-mitsu: one plain strip up the front, under the crotch, up between the buttocks into the knot
def mid_skin(phi, c=Vector((0, 0.03, 0.80))):
    d = Vector((0, -math.cos(phi), -math.sin(phi)))
    return hit(c + d * 0.9, -d, 0.9)
zf, zb = float(belt_zc(0)) - 0.07, ZB - 0.07
path = []
for ph in np.linspace(math.radians(8), math.radians(176), 32):
    loc, nor = mid_skin(ph)
    if loc is not None: path.append(loc)
path = [p for p in path if not (p.y < -0.1 and p.z > zf + 0.02) and not (p.y > 0.1 and p.z > zb + 0.04)]
for _ in range(5):
    path = [path[0]] + [(path[i - 1] + 2 * path[i] + path[i + 1]) / 4 for i in range(1, len(path) - 1)] + [path[-1]]
NP = len(path); P, UV = [], []; L_acc = 0.0
for i, p in enumerate(path):
    tng = (path[min(i + 1, NP - 1)] - path[max(i - 1, 0)]).normalized()
    l, nrm, _, _ = bvh.find_nearest(p)
    side = Vector((1, 0, 0)); nn = side.cross(tng).normalized()
    if nn.dot(nrm) < 0: nn = -nn
    f = i / (NP - 1); hw = 0.075 * (1 - f) ** 2 + 0.035 + 0.04 * f ** 3
    if i > 0: L_acc += (path[i] - path[i - 1]).length
    row, uvr = [], []
    for k in range(9):
        g = math.pi + 2 * math.pi * k / 8; cx, cy = math.cos(g), math.sin(g)
        row.append(p + nn * (0.012 + 0.01 * (sgp(cx, 0.5) + 1)) + side * hw * sgp(cy, 0.5))
        uvr.append((L_acc * 3, 0.5 + 0.4 * sgp(cy, 0.5)))
    P.append(row); UV.append(uvr)
strip = grid_obj('TateMitsu', P, UV, MAW)
push_out(strip, 0.012)
# sagari: a few chunky flat strips hanging from the front of the band
SAG = []
for j in range(7):
    th = -0.72 + 1.44 * j / 6
    rr = lerp_th(WRAPS[0][2], th) + 0.004
    top = Vector((rr * math.sin(th), CY - rr * math.cos(th), float(belt_zc(th)) - 0.04))
    out = Vector((math.sin(th), -math.cos(th), 0)); sd = Vector((math.cos(th), math.sin(th), 0))
    L = 0.2 - 0.03 * abs(th)
    P, UV = [], []
    for i in range(5):
        f = i / 4
        c = top + Vector((0, 0, -L * f)) + out * (0.015 * f)
        row, uvr = [], []
        for k in range(9):
            g = math.pi + 2 * math.pi * k / 8; cx, cy = math.cos(g), math.sin(g)
            row.append(c + out * 0.008 * sgp(cx, 0.5) + sd * 0.022 * sgp(cy, 0.5)); uvr.append((k / 8, f))
        P.append(row); UV.append(uvr)
    o = grid_obj('Sagari', P, UV, MAW, cap_i=True)
    push_out(o, 0.012)
    SAG.append((o, top))

# ---------------------------------------------------------------- hair: a smooth cap and a simple chonmage
POLE = Vector((0, 0.32, 1)).normalized()
PU = Vector((1, 0, 0)); PV = POLE.cross(PU).normalized()
def hairline(phi):
    pts = [(0.0, 0.62), (0.6, 0.56), (1.05, 0.38), (1.35, 0.22), (1.6, 0.22), (1.95, 0.12), (2.4, -0.36), (2.8, -0.58), (math.pi, -0.62)]
    return float(np.interp(abs(phi), [p[0] for p in pts], [p[1] for p in pts]))
def is_hair(dr):
    phi = math.atan2(dr.x, -dr.y); el = math.asin(max(-1, min(1, dr.z)))
    return el > hairline(phi)
def pdir(beta, a): return (POLE * math.cos(beta) + (PU * math.cos(a) + PV * math.sin(a)) * math.sin(beta)).normalized()
def skull(dr):
    l, nrm = hit(HC + dr * 0.45, -dr, 0.45); return l, nrm
NA, NE = 40, 10
B0 = 0.07
P, UV = [], []
bm = []
for kk in range(NA):
    a = 2 * math.pi * kk / NA; bmax = B0
    while bmax < 2.6 and is_hair(pdir(bmax + 0.01, a)): bmax += 0.01
    bm.append(bmax)
bm = np.array(bm)
for _ in range(3): bm = (np.roll(bm, 1) + 2 * bm + np.roll(bm, -1)) / 4    # a clean, smooth hairline
for kk in range(NA + 1):
    a = 2 * math.pi * kk / NA; bmax = bm[kk % NA]
    row, uvr = [], []
    for j in range(NE + 1):
        beta = B0 + (bmax - B0) * (j / NE) ** 0.9
        dr = pdir(beta, a); l, nrm = skull(dr)
        phi = math.atan2(dr.x, -dr.y); el = math.asin(dr.z)
        tabo = 0.022 * math.exp(-((abs(phi) - math.pi) / 0.9) ** 2) * math.exp(-((el + 0.15) / 0.32) ** 2)
        edge = min(1.0, (NE - j) / 3.0)
        edge = edge * edge * (3 - 2 * edge)
        row.append(l + nrm * (0.003 + 0.011 * edge + tabo * edge))
        uvr.append((kk / NA, 0.05 + 0.9 * j / NE))
    P.append(row); UV.append(uvr)
cap = grid_obj('HairCap', P, UV, HAIR)
T, Tn = skull(POLE)
T = T + Tn * 0.012
TF = (Vector((0, -1, 0)) - POLE * POLE.dot(Vector((0, -1, 0)))).normalized()
TS = TF.cross(POLE).normalized()
# the crown hole of the cap is covered by a soft root, and the chonmage lies forward over the crown: a bent capsule
o = sphere('TopknotRoot', (0, 0, 0), (1, 1, 1), HAIR, 20, 12)
for v in o.data.vertices:
    c_ = v.co.copy(); v.co = T - TF * 0.01 - POLE * 0.004 + TS * c_.x * 0.045 + TF * c_.y * 0.055 + POLE * c_.z * 0.02
o.data.update()
o = sphere('Chonmage', (0, 0, 0), (1, 1, 1), HAIR, 20, 14)
for v in o.data.vertices:
    c_ = v.co.copy(); u = c_.y
    v.co = T + TF * (0.03 + 0.085 * u) + POLE * (0.02 - 0.012 * u * u) + TS * c_.x * 0.036 + POLE * c_.z * 0.026
o.data.update()

# ---------------------------------------------------------------- face: two small dark dot eyes, nothing else
for s in S2:
    l, n_ = hit((s * 0.052, -1, 1.69), (0, 1, 0))
    sphere('Eye', l + Vector((0, 0.002, 0)), (0.012, 0.006, 0.0145), INK, 10, 6)

# ---------------------------------------------------------------- skin: one flat colour, a soft cheek blush, baked to a small texture
bpy.context.view_layer.objects.active = body
for o in scn.objects: o.select_set(o == body)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(78), island_margin=0.01, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
body.data.uv_layers[0].name = 'UVMap'
me = body.data; N = len(me.vertices)
bco = np.array([v.co for v in me.vertices])
blush = np.zeros(N)
for s in S2:
    l, _ = hit((s * 0.085, -1, 1.645), (0, 1, 0))
    blush = np.maximum(blush, np.exp(-np.sum((bco - np.array(tuple(l))) ** 2, axis=1) / 0.034 ** 2))
blush *= 0.35
col = np.array(SKIN_RGB)[None] * (1 - blush[:, None]) + np.array(BLUSH_RGB)[None] * blush[:, None]
ca = me.color_attributes.new('Paint', 'FLOAT_COLOR', 'POINT')
rgba = np.ones((N, 4)); rgba[:, :3] = col; ca.data.foreach_set('color', rgba.ravel())
SKIN_IMG = bpy.data.images.new('SkinTex', 512, 512, alpha=False)
SKIN_IMG.generated_color = (*SKIN_RGB, 1)
SKIN = bpy.data.materials.new('Skin'); SKIN.use_nodes = True; nt = SKIN.node_tree; nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Paint'
nt.links.new(vc.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs['Emission'], outn.inputs['Surface'])
imn = nt.nodes.new('ShaderNodeTexImage'); imn.image = SKIN_IMG; nt.nodes.active = imn
me.materials.append(SKIN)
scn.cycles.samples = 4
bpy.ops.object.bake(type='EMIT', margin=16, use_clear=False)
px = np.array(SKIN_IMG.pixels[:]).reshape(-1, 4)                      # any pixel the bake missed (or bled dark): plain skin
lum = px[:, :3] @ np.array([0.3, 0.5, 0.2]); lum0 = np.array(SKIN_RGB) @ np.array([0.3, 0.5, 0.2])
bad = lum < 0.8 * lum0
print('skin texture: fixed pixels', int(bad.sum()))
px[bad, :3] = SKIN_RGB; px[:, 3] = 1
SKIN_IMG.pixels.foreach_set(px.ravel().astype(np.float32)); SKIN_IMG.update()
SKIN_IMG.pack()
nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
imn = nt.nodes.new('ShaderNodeTexImage'); imn.image = SKIN_IMG; imn.name = 'Tex'
nt.links.new(imn.outputs['Color'], bs.inputs['Base Color']); nt.links.new(bs.outputs['BSDF'], outn.inputs['Surface'])
bs.inputs['Roughness'].default_value = 0.85; bs.inputs['Specular IOR Level'].default_value = 0.2
me.color_attributes.remove(me.color_attributes['Paint'])

# ---------------------------------------------------------------- armature (A-pose rest), as sumo2
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
    sd = '.L' if s > 0 else '.R'
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
if uw:
    kd = KDTree(len(body.data.vertices)); uws = set(uw)
    for v in body.data.vertices:
        if v.index not in uws: kd.insert(v.co, v.index)
    kd.balance()
    for i in uw:
        _, j, _ = kd.find(body.data.vertices[i].co)
        for g in body.data.vertices[j].groups: body.vertex_groups[g.group].add([i], g.weight, 'REPLACE')
print('weights:', WEIGHT_MODE, 'filled', len(uw))
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
try:
    bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=8)
except Exception as ex: print('smooth weights skipped', ex)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# the trunk bends as one soft volume: whatever share of a vertex belongs to hips / spine / chest is redistributed by
# height over wide, overlapping bands (bone heat leaves sharp seams there, which crease the belly and back when posed)
TRUNK = ('hips', 'spine', 'chest')
# bone heat leaks the thighs up the round flanks: above the belt the legs have no say (their share goes to the trunk)
hg0 = body.vertex_groups['hips']
for v in body.data.vertices:
    c = v.co
    if abs(c.x) > 0.6 or c.z < 0.6: continue
    th = math.atan2(c.x, -(c.y + 0.03)); keep = float(sstep(float(belt_zc(th)) + 0.05, float(belt_zc(th)) - 0.06, c.z))
    if keep >= 1: continue
    moved = 0.0
    for g in v.groups:
        if body.vertex_groups[g.group].name.startswith(('thigh', 'shin', 'foot')): moved += g.weight * (1 - keep); g.weight *= keep
    if moved > 0:
        cur = next((g.weight for g in v.groups if g.group == hg0.index), 0.0); hg0.add([v.index], cur + moved, 'REPLACE')
for v in body.data.vertices:
    cur = {body.vertex_groups[g.group].name: g.weight for g in v.groups}
    tot = sum(cur.get(n, 0.0) for n in TRUNK)
    if tot <= 1e-4: continue
    z = v.co.z
    wh = 1 - float(sstep(0.80, 1.10, z)); wc = float(sstep(1.02, 1.40, z)); ws = max(0.0, 1 - wh - wc)
    for n, w_ in zip(TRUNK, (wh, ws, wc)):
        if w_ * tot > 1e-4: body.vertex_groups[n].add([v.index], w_ * tot, 'REPLACE')
        elif n in cur: body.vertex_groups[n].remove([v.index])
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# near the midline the trunk belongs to the chest, not the shoulders (arms coming forward would drag and fold it)
cg = body.vertex_groups['chest']
for v in body.data.vertices:
    lo = 0.2 + 0.14 * float(sstep(1.42, 1.2, v.co.z))                  # lower down, the round sides belong to the trunk too
    keep = float(sstep(lo, lo + 0.16, abs(v.co.x)))
    if keep >= 1: continue
    moved = 0.0
    for g in v.groups:
        if body.vertex_groups[g.group].name.startswith(('shoulder', 'upper_arm')): moved += g.weight * (1 - keep); g.weight *= keep
    if moved > 0:
        cur = next((g.weight for g in v.groups if g.group == cg.index), 0.0); cg.add([v.index], cur + moved, 'REPLACE')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# under the belt the skin is bound to the hips (cloth and skin move as one; the legs still bend below it)
hg = body.vertex_groups['hips']
for v in body.data.vertices:
    c = v.co
    if abs(c.x) > 0.56 or not (0.5 < c.z < 1.1): continue
    th = math.atan2(c.x, -(c.y + 0.03)); dz = abs(c.z - float(belt_zc(th)) + 0.01)
    k = float(sstep(0.17, 0.09, dz))
    if k <= 0: continue
    for g in v.groups:
        if body.vertex_groups[g.group].name != 'hips': g.weight *= (1 - k)
    cur = next((g.weight for g in v.groups if g.group == hg.index), 0.0)
    hg.add([v.index], cur * (1 - k) + k, 'REPLACE')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# relax once more and cap to 4 influences here, on the skin alone, so the glTF limit later drops nothing abrupt
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
for _ in range(2):
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.6, repeat=6)
bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.02)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

# the mitts belong to the hand bones (bone heat leaves part of them on the forearm, which bends the wrist into a stalk)
for s in S2:
    sd = '.L' if s > 0 else '.R'; xh = D2[s]
    gh, gf = body.vertex_groups['hand' + sd], body.vertex_groups['forearm' + sd]
    for v in body.data.vertices:
        if v.co.x * s < 0.5: continue
        rel = v.co - W[s]; t = rel.dot(xh)
        if t < -0.12 or (rel - xh * t).length > 0.2: continue
        wh = float(sstep(-0.10, 0.06, t))
        for g in list(v.groups):
            if g.group not in (gh.index, gf.index): body.vertex_groups[g.group].remove([v.index])
        gh.add([v.index], wh, 'REPLACE'); gf.add([v.index], 1 - wh, 'REPLACE')
GN = [g.name for g in body.vertex_groups]
bco_l = [v.co.copy() for v in body.data.vertices]
bw = [{body.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-4} for v in body.data.vertices]
KD = KDTree(len(bco_l))
for i, c in enumerate(bco_l): KD.insert(c, i)
KD.balance()
def skin_weights(p, k=6):
    acc = {}
    for c, i, d in KD.find_n(p, k):
        w = 1 / (d + 0.004) ** 2
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
    if nm in ('Eye', 'TopknotRoot', 'Chonmage'): set_weights(o, head_only)
    elif nm == 'Knot': set_weights(o, lambda p: knot_anchor)
    elif nm == 'Sagari':
        top = [t for (so, t) in SAG if so == o][0]; aw = skin_weights(top)
        aw = {g: x for g, x in aw.items() if not g.startswith(('thigh', 'shin'))} or {'hips': 1.0}
        set_weights(o, lambda p, aw=aw: aw)
    elif nm in ('Band', 'TateMitsu'):                     # cloth rides the hips, never the thighs
        def cloth_w(p):
            w_ = {g: x for g, x in skin_weights(p).items() if not g.startswith(('thigh', 'shin'))} or {'hips': 1.0}
            t_ = sum(w_.values()); return {g: x / t_ for g, x in w_.items()}
        set_weights(o, skin_weights if nm == 'TateMitsu' else cloth_w)
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
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
for g in list(hero.vertex_groups):
    if g.name not in BONES: hero.vertex_groups.remove(g)
hero.parent = rig
am = hero.modifiers.new('Armature', 'ARMATURE'); am.object = rig
tris = sum(len(p.vertices) - 2 for p in hero.data.polygons)
uw = unweighted(hero)
print('TRIANGLES', tris, 'verts', len(hero.data.vertices), 'unweighted', len(uw))
print('BONES', len(ORDER), ORDER)
print('MATERIALS', [m_.name for m_ in hero.data.materials])

# ---------------------------------------------------------------- export (rest pose), plus the red-mawashi variant
def export(path):
    rig_data.pose_position = 'REST'
    for o in scn.objects: o.select_set(o in (hero, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_skins=True, export_animations=False,
                              export_apply=False, export_rest_position_armature=True, export_yup=True)
    rig_data.pose_position = 'POSE'
MAW_BSDF = MAW.node_tree.nodes['Principled BSDF']
export(os.path.join(OUT, 'sumo_soft.glb'))
MAW_BSDF.inputs['Base Color'].default_value = (*RED, 1); export(os.path.join(OUT, 'sumo_soft_red.glb'))
MAW_BSDF.inputs['Base Color'].default_value = (*NAVY, 1)
MAW_RED = MAW.copy(); MAW_RED.name = 'MawashiRed'; MAW_RED.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*RED, 1)

# ---------------------------------------------------------------- posing (via the armature), as sumo2
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
def leg(sp, s, ank, pole, foot, foot_up=(0, 0, 1)):
    sd = '.L' if s > 0 else '.R'; ank, pole = Vector(ank), Vector(pole)
    lt = (rig_data.bones['thigh' + sd].length, rig_data.bones['shin' + sd].length)
    sp['thigh' + sd] = (lambda h, ank=ank, pole=pole, lt=lt: (two_bone(h, ank, lt[0], lt[1], pole) - h, pole))
    sp['shin' + sd] = (lambda h, ank=ank, pole=pole: (ank - h, pole))
    sp['foot' + sd] = (foot, foot_up)
def arm(sp, s, sh, ua, fa, hd, hz):
    sd = '.L' if s > 0 else '.R'
    sp['shoulder' + sd] = (sh, None); sp['upper_arm' + sd] = (ua, None); sp['forearm' + sd] = (fa, hz); sp['hand' + sd] = (hd, hz)
# each pose: (spec builder taking a ground offset dz, hips offset); the offset is solved so the lowest skin point sits on the floor
def stance_spec(dz=0.0):
    # shiko-dachi-like ready stance: feet wide and turned out, knees over the toes, hips low, back nearly upright,
    # arms relaxed forward and out, open hands palm-down at belly height, head up looking ahead
    sp = {'hips': lean(5), 'spine': lean(7), 'chest': lean(9), 'neck': lean(4), 'head': lean(-4)}
    for s in S2:
        out = math.radians(38)
        leg(sp, s, (s * 0.56, 0.02, 0.11 + dz), (s * math.sin(out), -math.cos(out), 0.05),
            (s * 0.55 * math.sin(out) / 0.6, -0.55 * math.cos(out) / 0.6, -0.3))
        arm(sp, s, (s * 0.95, -0.28, -0.08), (s * 0.42, -0.42, -0.80), (s * 0.12, -0.95, -0.28),
            (s * 0.06, -0.86, -0.5), (-s, 0, 0.5))
    return sp
STANCE_OFF = Vector((0, 0.03, -0.22))
def push_spec(dz=0.0):
    # oshi: driving forward. Torso ~35 degrees forward, left foot planted ahead with the knee bent over it, right leg
    # long and nearly straight behind on the ball of the foot, both arms out at chest height, palms forward, head up
    sp = {'hips': lean(36), 'spine': lean(42), 'chest': lean(45), 'neck': lean(20), 'head': lean(-4)}
    leg(sp, 1, (0.30, -0.36, 0.11 + dz), (0.25, -0.95, 0.1), (0.18, -0.93, -0.32))
    leg(sp, -1, (-0.27, 0.55, 0.17 + dz), (-0.15, -0.6, -0.8), (-0.05, -0.5, -0.86), (0, -1, 0.3))
    for s in S2:
        arm(sp, s, (s * 0.9, -0.42, -0.04), (s * 0.30, -0.92, -0.22), (s * 0.02, -0.88, 0.47),
            (-s * 0.04, -0.50, 0.86), (-s, 0, 0))
    return sp
PUSH_OFF = Vector((0, -0.16, -0.15))
def charge_spec(dz=0.0):
    # tachiai / run: ~45 degrees forward and falling into the step. Left thigh driven up and forward, right leg long
    # behind pushing off the toes; arms bent and pumping low (right forward, left back), head slightly down
    sp = {'hips': lean(50), 'spine': lean(55), 'chest': lean(58), 'neck': lean(36), 'head': lean(18)}
    leg(sp, 1, (0.29, -0.52, 0.32 + dz), (0.15, -0.7, 0.7), (0.12, -0.75, -0.65))
    leg(sp, -1, (-0.25, 0.55, 0.20 + dz), (-0.1, -0.6, -0.8), (-0.03, -0.35, -0.94), (0, -1, 0.3))
    arm(sp, -1, (-0.88, -0.45, -0.1), (-0.2, -0.45, -0.87), (0.15, -0.80, 0.58), (0.1, -0.97, 0.1), (1, 0, 0))
    arm(sp, 1, (0.92, -0.2, -0.1), (0.35, 0.75, -0.55), (0.10, -0.35, -0.93), (0.05, -0.5, -0.86), (-1, 0, 0))
    return sp
CHARGE_OFF = Vector((0, -0.2, -0.1))

def floor_z():
    bpy.context.view_layer.update()
    ev = hero.evaluated_get(bpy.context.evaluated_depsgraph_get()); me_ = ev.to_mesh()
    z = np.empty(len(me_.vertices) * 3); me_.vertices.foreach_get('co', z); ev.to_mesh_clear()
    return float(z.reshape(-1, 3)[:, 2].min())
def pose_grounded(rg, fn, off):
    dz = 0.0
    for _ in range(3):
        apply_pose(rg, fn(dz), off + Vector((0, 0, dz)))
        if rg != rig: break
        dz -= floor_z()
    return dz
POSES = [('stance', stance_spec, STANCE_OFF), ('push', push_spec, PUSH_OFF), ('charge', charge_spec, CHARGE_OFF)]
POSE_DZ = {}
def bake_action(name, fn, off):
    POSE_DZ[name] = pose_grounded(rig, fn, off)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        for f in (1, 2): pb.keyframe_insert('location', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f)
    rig.animation_data.action = None
    print('pose', name, 'ground dz %.3f' % POSE_DZ[name])
    return act
def export_anim(path):                                     # every action baked so far goes out as its own clip
    for o in scn.objects: o.select_set(o in (hero, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_skins=True,
                              export_animations=True, export_animation_mode='ACTIONS', export_apply=False,
                              export_rest_position_armature=True, export_yup=True)

# the stance as a one-frame clip ("stance") for the game to pose the skinned model with
ACTS = {'stance': bake_action(*POSES[0])}
rig.animation_data.action = ACTS['stance']
export_anim(os.path.join(OUT, 'sumo_soft_stance.glb'))
# then all three clips (stance, push, charge) in one file
rig.animation_data.action = None
for p_ in POSES[1:]: ACTS[p_[0]] = bake_action(*p_)
rig.animation_data.action = ACTS['stance']
export_anim(os.path.join(OUT, 'sumo_soft_poses.glb'))
rig.animation_data.action = None
apply_pose(rig, stance_spec(POSE_DZ['stance']), STANCE_OFF + Vector((0, 0, POSE_DZ['stance'])))

# ---------------------------------------------------------------- preview: two of them squaring up, soft pastel light
if RENDER:
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('ece4f6'), 1); bg.inputs['Strength'].default_value = 1.1
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
    sun.data.energy = 2.2; sun.data.color = srgb('ffe4c8'); sun.data.angle = math.radians(25)
    sun.rotation_euler = (math.radians(42), 0, math.radians(-35))
    bpy.ops.mesh.primitive_plane_add(size=40); gnd = bpy.context.object; gnd.name = 'Ground'
    gnd.data.materials.append(mat('Floor', srgb('f2ece6'), 0.95, 0.1))
    rig2 = rig.copy(); scn.collection.objects.link(rig2)
    hero2 = hero.copy(); hero2.data = hero.data.copy(); scn.collection.objects.link(hero2)
    hero2.parent = rig2; hero2.modifiers['Armature'].object = rig2
    for i, m_ in enumerate(hero2.data.materials):
        if m_ == MAW: hero2.data.materials[i] = MAW_RED
    apply_pose(rig2, stance_spec(POSE_DZ['stance']), STANCE_OFF + Vector((0, 0, POSE_DZ['stance'])))
    rig.location = (0, -0.8, 0); rig.rotation_euler = (0, 0, math.pi)     # hero: faces +Y, back to the camera
    rig2.location = (0, 0.8, 0)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    el, az, dist = math.radians(42), 0.62, 7.2
    cam.location = (dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el))
    cam.data.lens = 62
    cam.rotation_euler = (Vector((0, 0, 0.75)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
    scn.render.resolution_x = scn.render.resolution_y = RES
    scn.view_settings.view_transform = 'Standard'
    scn.render.filepath = os.path.join(OUT, 'prev_stance.png'); bpy.ops.render.render(write_still=True)
    # the three clips side by side, seen 3/4 from front-right and above
    for o in (hero2, rig2): bpy.data.objects.remove(o)
    rig.location = (0, 0, 0); rig.rotation_euler = (0, 0, 0)
    el, az, dist = math.radians(28), math.radians(55), 10.5
    right = Vector((math.cos(az), math.sin(az), 0)); tgt = Vector((0, 0, 0.72))
    cam.location = tgt + Vector((dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el)))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 50
    for i, (nm, fn, off) in enumerate(POSES):
        if i == 0: rg, hr = rig, hero
        else:
            rg = rig.copy(); scn.collection.objects.link(rg)
            hr = hero.copy(); hr.data = hero.data.copy(); scn.collection.objects.link(hr); hr.parent = rg; hr.modifiers['Armature'].object = rg
        rg.animation_data_create(); rg.animation_data.action = ACTS[nm]
        if nm == 'push': RG_PUSH = rg
        rg.location = right * (2.05 * (i - 1)); rg.rotation_euler = (0, 0, math.radians(20 if i == 0 else -15))   # stance more frontal, the drives more in profile
    scn.frame_set(1)
    scn.render.resolution_x, scn.render.resolution_y = 1200, 500
    scn.render.filepath = os.path.join(OUT, 'prev_poses.png'); bpy.ops.render.render(write_still=True)
    # close-up of the pushing hands, 3/4 from above
    bpy.context.view_layer.update()
    for o in scn.objects:
        if o.type in ('MESH', 'ARMATURE') and o not in (RG_PUSH, gnd) and o.parent != RG_PUSH: o.hide_render = True
    hc = sum((RG_PUSH.matrix_world @ RG_PUSH.pose.bones['hand' + sd].head for sd in ('.L', '.R')), Vector()) / 2
    fwd = (RG_PUSH.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized(); side = Vector((-fwd.y, fwd.x, 0))
    cam.location = hc + (fwd * 1.1 + side * 0.75 + Vector((0, 0, 0.95))) * 1.75
    cam.rotation_euler = (hc + fwd * 0.1 - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 50
    scn.render.resolution_x, scn.render.resolution_y = 800, 500
    scn.render.filepath = os.path.join(OUT, 'prev_hands.png'); bpy.ops.render.render(write_still=True)
print('done')
