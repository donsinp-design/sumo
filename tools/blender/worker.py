# Fish-market worker enemy: a stylised Tsukiji fishmonger, built entirely by script (Blender 4.2, run headless).
#   python tools/blender/worker.py  [out.glb] [preview_prefix]
# Same recipe as sumo.py: overlapping volumes (head, neck, torso, sleeves, mitten hands, trousers, boots) fused
# into ONE skin with a voxel remesh, then smoothed and decimated. Clothing is painted onto that skin by region
# (clean cuts made with bisect planes) and the region borders are hidden under real cloth pieces fitted to the
# surface: a collar band, cuffs, jacket hem, boot rims. On top: a hanging rubber apron, short hair, a twisted
# hachimaki, a simple tough face. Blender is Z-up with the front facing -Y; the glTF export converts to Y-up.
# Real scale: about 1.72 m. Also writes <out>_red.glb and <out>_green.glb (jacket colour variants).
import bpy, bmesh, math, sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARGS = [a for a in sys.argv if not a.startswith('shot=')]            # optional shot=front shot=vs ... renders only those
out = ARGS[-2] if len(ARGS) > 2 and ARGS[-2].endswith('.glb') else '/tmp/worker.glb'
prev = ARGS[-1] if len(ARGS) > 2 else '/tmp/worker_prev'
VS = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad/sumo_hero.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

def mat(name, rgb, rough=0.7):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    return m
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

SKIN = mat('Skin', srgb('c98a62'), 0.6)          # tanned, warmer and darker than the sumo
STUB = mat('Stubble', srgb('a8806a'), 0.8)
HAIR = mat('Hair', srgb('1d1a1c'), 0.5)
JACKET = mat('Jacket', srgb('233257'), 0.8)      # indigo work jacket
COLLAR = mat('Collar', srgb('141a2c'), 0.75)
SHIRT = mat('Undershirt', srgb('ece8de'), 0.7)
PANTS = mat('Trousers', srgb('34353b'), 0.8)
BOOT = mat('Boots', srgb('17171a'), 0.32)
SOLE = mat('Sole', srgb('2c2a28'), 0.7)
APRON = mat('Apron', srgb('e6e2d6'), 0.38)       # pale rubber
INK = mat('Ink', srgb('1a1216'), 0.5)
WHITE = mat('White', srgb('f6f0e6'), 0.5)
BAND = mat('Hachimaki', srgb('f3efe6'), 0.6)

# ---------------------------------------------------------------- body: overlapping volumes fused into one skin (voxel remesh)
parts = []
def ell(x, y, z, rx, ry, rz, rot=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=18, location=(x, y, z)); o = bpy.context.object; o.scale = (rx, ry, rz)
    if rot is not None: o.rotation_euler = rot.to_euler()
    parts.append(o); return o
def limb(a, b, ra, rb):  # a tapered capsule from a to b
    a, b = Vector(a), Vector(b); d = b - a; L = d.length
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=ra, radius2=rb, depth=L, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); parts.append(o)
    ell(*a, ra, ra, ra); ell(*b, rb, rb, rb)

# torso: pelvis, a slight paunch, a broad chest, sloping trapezius
ell(0, 0.015, 0.93, 0.175, 0.12, 0.115)          # pelvis
ell(0, -0.035, 1.07, 0.178, 0.152, 0.15)         # belly: a solid paunch
ell(0, 0.0, 1.235, 0.2, 0.125, 0.155)            # chest
ell(0, 0.04, 1.30, 0.17, 0.095, 0.10)            # upper back
limb((0, 0.015, 1.38), (0, 0.0, 1.52), 0.066, 0.059)   # thick neck
# head: cranium, face mass, square jaw, chin, brow ridge, cheekbones, nose, ears
HZ = 1.60
ell(0, 0.012, HZ + 0.02, 0.093, 0.108, 0.10)     # cranium (top at 1.72)
ell(0, -0.038, HZ - 0.015, 0.083, 0.072, 0.085)  # face
ell(0, -0.032, HZ - 0.09, 0.077, 0.07, 0.05)     # jaw
ell(0, -0.083, HZ - 0.12, 0.036, 0.03, 0.029)    # chin
ell(0, -0.083, HZ + 0.035, 0.07, 0.025, 0.022)   # brow ridge
ell(0, -0.104, HZ - 0.012, 0.015, 0.022, 0.03)   # nose bridge
ell(0, -0.116, HZ - 0.033, 0.02, 0.017, 0.016)   # nose tip
for s in (-1, 1):
    ell(s * 0.045, -0.072, HZ - 0.025, 0.03, 0.026, 0.025)    # cheekbones
    ell(s * 0.096, 0.016, HZ - 0.008, 0.02, 0.029, 0.04)       # ears
ARM = {}
for s in (-1, 1):
    limb((s * 0.05, 0.025, 1.44), (s * 0.21, 0.02, 1.37), 0.058, 0.052)   # trapezius slope
    ell(s * 0.215, 0.01, 1.35, 0.085, 0.085, 0.08)                         # deltoid
    J = Vector((s * 0.22, 0.01, 1.355))
    d1 = Vector((s * math.cos(math.radians(35)), 0, -math.sin(math.radians(35))))
    E = J + d1 * 0.265
    d2 = Vector((s * 0.68, -0.16, -0.72)).normalized()
    W = E + d2 * 0.235
    limb(J, E, 0.08, 0.068)                     # upper sleeve
    ell(*(E + Vector((0, 0.012, 0.004))), 0.07, 0.07, 0.066)                 # elbow fold
    limb(E, W, 0.068, 0.056)                     # forearm sleeve, slightly loose
    limb(W - d2 * 0.02, W + d2 * 0.045, 0.037, 0.039)                       # wrist
    # mitten hand: palm, fingers as one curled block, a separate thumb
    xh = d2; yh = (Vector((0, -1, 0)) - d2 * d2.y).normalized(); zz = xh.cross(yh)
    up = -s * zz                                 # back of the hand: up and out
    R = Matrix((xh, yh, zz)).transposed()
    H0 = W + d2 * 0.03
    ell(*(H0 + xh * 0.055), 0.062, 0.05, 0.03, R)                            # palm
    ell(*(H0 + xh * 0.12 - up * 0.01), 0.05, 0.048, 0.026, R)                # fingers
    ell(*(H0 + xh * 0.155 - up * 0.028), 0.03, 0.044, 0.022, R)              # curled finger tips
    limb(H0 + xh * 0.03 + yh * 0.035 - up * 0.008, H0 + xh * 0.095 + yh * 0.08 - up * 0.026, 0.023, 0.019)   # thumb
    ARM[s] = (W, d2)
    # legs: baggy trousers, a little blousing over the boot tops, tall wide boots
    limb((s * 0.1, 0.01, 0.9), (s * 0.118, -0.008, 0.54), 0.11, 0.078)   # thigh, tapering to the knee
    ell(s * 0.085, 0.05, 0.885, 0.088, 0.078, 0.088)                          # seat
    limb((s * 0.115, -0.005, 0.54), (s * 0.12, 0.005, 0.445), 0.079, 0.095)  # knee, trousers bunching into the boot
    limb((s * 0.12, 0.008, 0.42), (s * 0.12, 0.015, 0.14), 0.088, 0.078)    # wide boot shaft
    ell(s * 0.12, -0.045, 0.095, 0.08, 0.155, 0.07)                          # boot foot
    ell(s * 0.12, 0.045, 0.1, 0.076, 0.078, 0.08)                            # heel
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = 'Body'
bpy.ops.object.transform_apply(scale=True, rotation=True)
r = body.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.009
bpy.ops.object.modifier_apply(modifier='rm')
m = body.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); m.factor = 0.8; m.iterations = 10; m.smooth_type = 'LENGTH_WEIGHTED'
bpy.ops.object.modifier_apply(modifier='sm')
m = body.modifiers.new('sm2', 'SMOOTH'); m.factor = 0.5; m.iterations = 6
bpy.ops.object.modifier_apply(modifier='sm2')
vg = body.vertex_groups.new(name='dec')
for v in body.data.vertices:
    c = v.co; w = 1.0
    if c.z > 1.47 and abs(c.x) < 0.13: w = 0.25 if c.y < 0.0 else 0.5         # the face keeps the most
    elif c.z > 1.25 and abs(c.x) < 0.14 and (c.y < -0.02 or c.z > 1.4): w = 0.4  # neck and collar line
    elif c.z > 0.85 and abs(c.x) > 0.58: w = 0.45                              # hands
    vg.add([v.index], w, 'REPLACE')
BODY_TRIS = 7000
for _ in range(3):
    n = sum(len(p.vertices) - 2 for p in body.data.polygons)
    if n <= BODY_TRIS * 1.05: break
    d = body.modifiers.new('dec', 'DECIMATE'); d.ratio = BODY_TRIS / n; d.use_symmetry = True; d.symmetry_axis = 'X'
    d.vertex_group = 'dec'; d.vertex_group_factor = 1.0
    bpy.ops.object.modifier_apply(modifier='dec')
body.vertex_groups.clear()
print('body triangles', sum(len(p.vertices) - 2 for p in body.data.polygons))

# ---------------------------------------------------------------- paint the clothes onto the skin: clean bisect cuts, then regions
WAIST, BOOTZ = 0.885, 0.405
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(body, dg)
def path_on_skin(ctrl, n=40):
    """a smooth path through rough control points, each sample pulled onto the skin"""
    ctrl = [Vector(c) for c in ctrl]; out_ = []
    for i in range(n):
        t = i / (n - 1) * (len(ctrl) - 1); k = min(int(t), len(ctrl) - 2); f = t - k
        p0, p1, p2, p3 = ctrl[max(k - 1, 0)], ctrl[k], ctrl[k + 1], ctrl[min(k + 2, len(ctrl) - 1)]
        q = 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)
        loc, nor, _, _ = bvh.find_nearest(q); out_.append(loc)
    for _ in range(4):   # relax the projected points along the path, then settle them back onto the skin
        out_ = [out_[0]] + [(out_[i - 1] + 2 * out_[i] + out_[i + 1]) / 4 for i in range(1, n - 1)] + [out_[-1]]
    res = []
    for p in out_:
        loc, nor, _, _ = bvh.find_nearest(p); res.append((loc, nor))
    return res
# the jacket's collar line: a V crossing low on the chest, up round the back of the neck
half = [(0.0, -0.115, 1.30), (0.036, -0.105, 1.36), (0.062, -0.082, 1.41), (0.077, -0.045, 1.445), (0.078, 0.005, 1.462), (0.056, 0.05, 1.468)]
COLLAR_PATH = path_on_skin(half + [(0, 0.068, 1.466)] + [(-x, y, z) for x, y, z in half[::-1]], 56)
CP = [(p, n, (COLLAR_PATH[min(i + 1, 55)][0] - COLLAR_PATH[max(i - 1, 0)][0]).normalized()) for i, (p, n) in enumerate(COLLAR_PATH)]
def inside_collar(c):
    if not (abs(c.x) < 0.2 and c.z > 1.29): return False
    if c.z > 1.52: return True
    p, n, t = min(CP, key=lambda q: (q[0] - c).length_squared)
    return (c - p).dot(n.cross(t)) > 0
bm = bmesh.new(); bm.from_mesh(body.data)
def cut(co, no, keep):
    vs = [v for v in bm.verts if keep(v.co)]; vset = set(vs)
    es = [e for e in bm.edges if e.verts[0] in vset and e.verts[1] in vset]
    fs = [f for f in bm.faces if all(v in vset for v in f.verts)]
    bmesh.ops.bisect_plane(bm, geom=vs + es + fs, plane_co=co, plane_no=no)
cut((0, 0, BOOTZ), (0, 0, 1), lambda c: c.z < 0.6)
cut((0, 0, WAIST), (0, 0, 1), lambda c: abs(c.x) < 0.33 and c.z < 1.0)
for s in (-1, 1):
    W, d2 = ARM[s]; cut(W, d2, lambda c, s=s: s * c.x > 0.42)
mats = [SKIN, JACKET, SHIRT, PANTS, BOOT]
for mm in mats: body.data.materials.append(mm)
for f in bm.faces:
    c = f.calc_center_median()
    if c.z < BOOTZ: f.material_index = 4
    elif c.z < WAIST and abs(c.x) < 0.33: f.material_index = 3
    elif abs(c.x) > 0.42 and (c - ARM[1 if c.x > 0 else -1][0]).dot(ARM[1 if c.x > 0 else -1][1]) > 0: f.material_index = 0
    elif inside_collar(c): f.material_index = 2 if (c.y < -0.03 and c.z < 1.425) else 0
    else: f.material_index = 1
bm.to_mesh(body.data); bm.free()
bpy.ops.object.shade_smooth()

def add(obj, m_):
    obj.data.materials.append(m_); bpy.context.view_layer.objects.active = obj; obj.select_set(True); bpy.ops.object.shade_smooth(); return obj
def sphere(name, loc, scale, m_, seg=24, rings=16, rot=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc); o = bpy.context.object; o.name = name; o.scale = scale
    if rot is not None: o.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True); return add(o, m_)
def mesh_obj(name, verts, faces, m_):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.validate(); me.update()
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    for x in scn.objects: x.select_set(False)
    return add(o, m_)

# ---------------------------------------------------------------- cloth pieces that follow the skin
def hit(origin, direction):
    loc, nor, _, _ = bvh.ray_cast(Vector(origin), Vector(direction).normalized(), 2.0); return loc, nor
def loop_around(center, axis, reach, n=48, zfun=None):
    """points where rays fired in at `center` (perpendicular to `axis`) meet the skin"""
    center, axis = Vector(center), Vector(axis).normalized()
    u = axis.orthogonal().normalized(); v = axis.cross(u)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n; dr = u * math.cos(a) + v * math.sin(a); c = center.copy()
        for _ in range(6 if zfun else 1):
            loc, nor = hit(c + dr * reach, -dr)
            if zfun is None or loc is None: break
            c.z = zfun(loc)
        if loc is not None: pts.append((loc, nor))
    return pts
def band(name, pts, hw, ht, off, m_, closed=True, K=10, twist=None, ends=True):
    """a strip (superellipse cross-section, hw wide along the skin, ht thick off it) along surface points"""
    N = len(pts)
    for _ in range(3):   # calm the normals of the decimated skin so the strip doesn't wobble
        pts = [(p, (pts[(i - 1) % N][1] + 2 * n + pts[(i + 1) % N][1]).normalized() if (closed or 0 < i < N - 1) else n) for i, (p, n) in enumerate(pts)]
    verts, faces = [], []
    for i, (p, n) in enumerate(pts):
        a = pts[(i + 1) % N][0] if (closed or i < N - 1) else p; b = pts[i - 1][0] if (closed or i > 0) else p
        t = (a - b).normalized(); side = n.cross(t).normalized(); nn = t.cross(side).normalized()
        if nn.dot(n) < 0: nn = -nn
        ctr = p + n * (off + ht)
        if twist: ctr = ctr + twist(i, side, nn)
        for k in range(K):
            g = 2 * math.pi * (k + 0.5) / K; cx, cy = math.cos(g), math.sin(g)
            verts.append(ctr + side * (math.copysign(abs(cx) ** 0.6, cx) * hw) + nn * (math.copysign(abs(cy) ** 0.6, cy) * ht))
    for i in range(N if closed else N - 1):
        j = (i + 1) % N
        for k in range(K): faces.append((i * K + k, i * K + (k + 1) % K, j * K + (k + 1) % K, j * K + k))
    if not closed and ends:
        faces.append(tuple(range(K))[::-1]); faces.append(tuple((N - 1) * K + k for k in range(K)))
    return mesh_obj(name, verts, faces, m_)
# collar band: a wide dark band crossing over at the chest, hiding the jacket / skin border
band('Collar', COLLAR_PATH[:28], 0.022, 0.006, 0.003, COLLAR, closed=False, K=6)
band('Collar', COLLAR_PATH[27:], 0.022, 0.006, 0.0075, COLLAR, closed=False, K=6)   # the left panel laps over the right
band('ShirtNeck', [p for p in loop_around((0, 0.0, 1.425), (0, 0, 1), 0.3, 40) if p[0].y < -0.03 and abs(p[0].x) < 0.07], 0.007, 0.004, 0.0, SHIRT, closed=False, K=4)
# cuffs, jacket hem, boot rims
for s in (-1, 1):
    W, d2 = ARM[s]
    band('Cuff', loop_around(W - d2 * 0.012, d2, 0.15, 20), 0.02, 0.007, 0.002, JACKET, K=5)
    band('BootRim', loop_around((s * 0.12, 0.01, BOOTZ + 0.008), (0, 0, 1), 0.16, 24), 0.02, 0.009, 0.0, BOOT, K=5)
band('Hem', loop_around((0, 0.02, WAIST + 0.012), (0, 0, 1), 0.4, 40), 0.03, 0.009, 0.003, JACKET, K=5)
# chunky soles
for s in (-1, 1):
    vs, fs, NS = [], [], 24
    for z, ins in ((0.0, 0.01), (0.007, 0.0), (0.036, 0.0), (0.042, 0.012)):
        for k in range(NS):
            a = 2 * math.pi * k / NS; ca, sa = math.cos(a), math.sin(a)
            rx_, ry_ = 0.09 - ins, (0.172 if sa < 0 else 0.162) - ins                   # a touch longer at the toe
            vs.append(Vector((s * 0.12 + math.copysign(abs(ca) ** 0.75, ca) * rx_, -0.04 + math.copysign(abs(sa) ** 0.75, sa) * ry_, z)))
    for r_ in range(3):
        for k in range(NS): fs.append((r_ * NS + k, r_ * NS + (k + 1) % NS, (r_ + 1) * NS + (k + 1) % NS, (r_ + 1) * NS + k))
    fs.append(tuple(range(NS))[::-1]); fs.append(tuple(3 * NS + k for k in range(NS)))
    mesh_obj('Sole', vs, fs, SOLE)

# ---------------------------------------------------------------- the apron: hangs straight from the chest and belly, flares a little at the hem
AT, AB, NX, NZ = 1.27, 0.43, 10, 22
av, af = [], []
cols = [[None] * (NX + 1) for _ in range(NZ + 1)]
for i in range(NZ + 1):
    t = i / NZ; z = AT + (AB - AT) * t
    half = 0.14 + 0.07 * min(t / 0.3, 1) ** 0.7 + 0.015 * max(t - 0.75, 0) / 0.25    # bib, widening at the waist, flared hem
    for j in range(NX + 1):
        u = -1 + 2 * j / NX; x = u * half
        loc, _ = hit((x, -1, z), (0, 1, 0))
        ys = loc.y - 0.02 if loc is not None else None
        yv = ys if ys is not None else 0.0
        if i > 0:
            above = cols[i - 1][j]
            yv = min(above, ys) if ys is not None else above                    # cloth can't swing back in under the belly
        cols[i][j] = yv
# smooth sideways a little, wrap the edges round the sides, flare the hem out
for it in range(3):
    for i in range(NZ + 1):
        row = cols[i][:]
        for j in range(1, NX): cols[i][j] = 0.25 * row[j - 1] + 0.5 * row[j] + 0.25 * row[j + 1]
for i in range(NZ + 1):
    t = i / NZ; z = AT + (AB - AT) * t
    half = 0.14 + 0.07 * min(t / 0.3, 1) ** 0.7 + 0.015 * max(t - 0.75, 0) / 0.25
    for j in range(NX + 1):
        u = -1 + 2 * j / NX; x = u * half
        y = cols[i][j] - 0.035 * max(t - 0.7, 0) / 0.3 * (0.6 + 0.4 * abs(u))  # flare at the hem
        y += 0.05 * abs(u) ** 3 * min(t / 0.2, 1)                                # edges curl back round the body
        loc, _ = hit((x, -1, z), (0, 1, 0))
        y += 0.006 * math.sin(u * math.pi * 2.5) * max(t - 0.3, 0)              # a couple of stiff folds in the rubber
        if loc is not None: y = min(y, loc.y - 0.016)
        v = Vector((x, y, z))
        for _ in range(2):
            l, nrm, _, _ = bvh.find_nearest(v)
            if (v - l).dot(nrm) < 0.02: v = l + nrm * 0.02                        # never inside or touching the jacket
        av.append(v)
for i in range(NZ):
    for j in range(NX): af.append((i * (NX + 1) + j, i * (NX + 1) + j + 1, (i + 1) * (NX + 1) + j + 1, (i + 1) * (NX + 1) + j))
apron = mesh_obj('Apron', av, af, APRON)
sol = apron.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.008; sol.offset = 0
bpy.ops.object.modifier_apply(modifier='sol')
# straps: up over the shoulders round the back of the neck, ties round the waist to a bow at the back
for s in (-1, 1):
    band('Strap', path_on_skin([(s * 0.125, -0.13, AT + 0.005), (s * 0.135, -0.07, 1.39), (s * 0.125, -0.0, 1.45), (s * 0.075, 0.06, 1.475), (0, 0.082, 1.47)], 16),
         0.011, 0.0035, 0.018, APRON, closed=False, K=5)
ties = loop_around((0, 0.02, 1.02), (0, 0, 1), 0.4, 48)
ties = [p for p in ties if p[0].y > -0.08]
ties.sort(key=lambda p: math.atan2(p[0].x, p[0].y))
band('Tie', ties, 0.012, 0.004, 0.003, APRON, closed=False, K=5)
bk = [p for p in ties if abs(p[0].x) < 0.02][0][0]
for s in (-1, 1):
    sphere('Bow', bk + Vector((s * 0.035, 0.018, 0.005)), (0.035, 0.012, 0.02), APRON, 10, 6, (0, s * 0.3, 0))
    sphere('BowTail', bk + Vector((s * 0.02, 0.016, -0.065)), (0.012, 0.006, 0.06), APRON, 8, 6, (0, s * 0.25, 0))
sphere('BowKnot', bk + Vector((0, 0.02, 0)), (0.016, 0.012, 0.016), APRON, 8, 6)

# ---------------------------------------------------------------- a crest on the back of the jacket: a ring with a bar (maru ni ichi)
loc, nor = hit((0, 1, 1.24), (0, -1, 0))

def disc_ring(name, r0, r1, z, m_, seg=40):
    vs, fs = [], []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        for rr in (r0, r1):
            x, zz = rr * math.cos(a), z + rr * math.sin(a); l, _ = hit((x, 1, zz), (0, -1, 0)); vs.append(Vector((x, l.y + 0.003, zz)))
    for k in range(seg):
        k2 = (k + 1) % seg; fs.append((2 * k, 2 * k2, 2 * k2 + 1, 2 * k + 1))
    return mesh_obj(name, vs, fs, m_)
crest = disc_ring('Crest', 0.058, 0.074, 1.24, WHITE)
bv = []
for x in (-0.045, -0.015, 0.015, 0.045):
    for zz in (1.229, 1.251):
        l, _ = hit((x, 1, zz), (0, -1, 0)); bv.append(Vector((x, l.y + 0.003, zz)))
mesh_obj('CrestBar', bv, [(0, 2, 3, 1), (2, 4, 5, 3), (4, 6, 7, 5)], WHITE)

# ---------------------------------------------------------------- face: small dark eyes with glints, scowling brows, nose, a flat mouth
def on_face(x, z, off=0.0):
    loc, nor = hit((x, -1, z), (0, 1, 0)); return loc + nor * off, nor
for s in (-1, 1):
    p, n = on_face(s * 0.037, HZ + 0.008, 0.0)
    sphere('Eye', p + Vector((0, 0.002, 0)), (0.0125, 0.008, 0.0165), INK, 10, 7, (0, 0, s * 0.25))
    sphere('EyeHi', p + Vector((-s * 0.004, -0.007, 0.006)), (0.004, 0.003, 0.0045), WHITE, 6, 5)
    p, n = on_face(s * 0.042, HZ + 0.038, 0.0)
    bpy.ops.mesh.primitive_cube_add(location=p + Vector((0, -0.004, 0))); b = bpy.context.object; b.name = 'Brow'
    b.scale = (0.03, 0.009, 0.0085); b.rotation_euler = (0, -s * 0.38, s * 0.3)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    bv_ = b.modifiers.new('bev', 'BEVEL'); bv_.width = 0.006; bv_.segments = 2; bpy.ops.object.modifier_apply(modifier='bev'); add(b, HAIR)
p, n = on_face(0, HZ - 0.072, 0.0)
bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.005, major_segments=24, minor_segments=6, location=p + Vector((0, -0.004, -0.022)), rotation=(math.pi / 2, 0, 0))
mouth = bpy.context.object; mouth.name = 'Mouth'; mouth.scale = (1, 0.6, 1)
bm = bmesh.new(); bm.from_mesh(mouth.data)                       # keep the upper arc: a hard, downturned mouth
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < 0.019], context='VERTS'); bm.to_mesh(mouth.data); bm.free()
bpy.ops.object.transform_apply(scale=True, rotation=True); add(mouth, INK)

# stubble: a thin shell over the jaw and upper lip
sv, sf, NT, NZS = [], [], 16, 8
for a in range(NT + 1):
    th = math.radians(-100 + 200 * a / NT); dr = Vector((math.sin(th), -math.cos(th), 0))
    side = min(abs(th) / math.radians(80), 1)
    z0 = HZ - 0.13 + 0.015 * side                          # along the jaw line
    z1 = HZ - 0.068 + 0.04 * side ** 2                     # under the mouth, rising to the sideburns
    for b in range(NZS + 1):
        z = z0 + (z1 - z0) * b / NZS
        org = Vector((0, -0.02, z))
        l, nrm = hit(org + dr * 0.25, -dr)
        while (l - org).length < 0.076 and z < z1:          # that ray found the neck, not the jaw: move up to the jaw line
            z += 0.004; org = Vector((0, -0.02, z)); l, nrm = hit(org + dr * 0.25, -dr)
        sv.append(l + nrm * 0.003)
for a in range(NT):
    for b in range(NZS): sf.append((a * (NZS + 1) + b, (a + 1) * (NZS + 1) + b, (a + 1) * (NZS + 1) + b + 1, a * (NZS + 1) + b + 1))
mesh_obj('Stubble', sv, sf, STUB)

# hair: short, cropped close to the scalp. Built as a grid from the hairline up to the crown, every point shot onto the
# skull, so the hairline is one clean curve (forehead high, over the ears, down to the nape) rather than a stair-step.
HC = Vector((0, 0.012, HZ + 0.02))
def hairline(a):   # height above HC of the hairline at azimuth a (0 = front, pi = back)
    y = -0.11 * math.cos(a)
    if y < -0.02: return 0.02 + 0.025 * min((-y - 0.02) / 0.05, 1)        # forehead
    yb = max(0, min(1, (y - 0.035) / 0.075))
    return 0.02 - 0.1 * (0.5 - 0.5 * math.cos(math.pi * yb))               # over the ears, down the back of the head
NA, NE = 30, 7
hv, hf = [], []
for k in range(NA):
    a = 2 * math.pi * k / NA; dh = Vector((math.sin(a), -math.cos(a), 0))
    e0 = math.atan2(hairline(a), 0.1)
    for r_ in range(NE):
        e = e0 + (math.radians(84) - e0) * (r_ / (NE - 1)) ** 0.85
        dr = dh * math.cos(e) + Vector((0, 0, 1)) * math.sin(e)
        l, nrm = hit(HC + dr * 0.3, -dr); hv.append(l + nrm * 0.003)
l, nrm = hit(HC + Vector((0, 0, 0.3)), (0, 0, -1)); hv.append(l + nrm * 0.003); top = len(hv) - 1
for k in range(NA):
    k2 = (k + 1) % NA
    for r_ in range(NE - 1): hf.append((k * NE + r_, k2 * NE + r_, k2 * NE + r_ + 1, k * NE + r_ + 1))
    hf.append((k * NE + NE - 1, k2 * NE + NE - 1, top))
cap = mesh_obj('Hair', hv, hf, HAIR)
sol = cap.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.007; sol.offset = 1; bpy.ops.object.modifier_apply(modifier='sol')

# hachimaki: two twisted strands round the forehead, a knot and two short tails at the back
def head_z(p): return HZ + 0.05 + 0.012 * max(p.y, 0) / 0.1
ring = loop_around((0, 0.012, HZ + 0.05), (0, 0, 1), 0.3, 42, head_z)
TW = 6
for k in range(2):
    band('Hachimaki', ring, 0.0115, 0.009, 0.012, BAND, K=5,
         twist=lambda i, side, nn, k=k: (side * math.cos(2 * math.pi * TW * i / 42 + k * math.pi) * 0.0065 +
                                        nn * math.sin(2 * math.pi * TW * i / 42 + k * math.pi) * 0.004))
bk = max(ring, key=lambda p: p[0].y)[0]
sphere('HachiKnot', bk + Vector((0, 0.02, 0.002)), (0.022, 0.016, 0.019), BAND, 8, 6)
for s in (-1, 1):
    sphere('HachiTail', bk + Vector((s * 0.012, 0.022, -0.036)), (0.011, 0.005, 0.034), BAND, 8, 6, (0.15, s * 0.18, 0))

# ---------------------------------------------------------------- one object, origin at the feet, export (+ jacket colour variants)
from collections import Counter
cnt = Counter()
for o in scn.objects:
    if o.type == 'MESH': cnt[o.name.split('.')[0]] += sum(len(p.vertices) - 2 for p in o.data.polygons)
print('parts', dict(cnt))
for o in scn.objects: o.select_set(o.type == 'MESH')
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
hero = bpy.context.object; hero.name = 'Worker'
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
tris = sum(len(p.vertices) - 2 for p in hero.data.polygons)
print('triangles', tris)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True)
jb = JACKET.node_tree.nodes['Principled BSDF'].inputs['Base Color']
base = tuple(jb.default_value)
for tag, hx in (('red', '8a2b25'), ('green', '2f553b')):
    jb.default_value = (*srgb(hx), 1)
    bpy.ops.export_scene.gltf(filepath=out[:-4] + '_' + tag + '.glb', export_format='GLB', use_selection=True, export_apply=True)
jb.default_value = base

# ---------------------------------------------------------------- preview renders (Cycles, CPU): soft sky + a warm sun
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (*srgb('b8c8dc'), 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 3.2; sun.data.color = srgb('ffe8c8'); sun.data.angle = 0.25; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
bpy.ops.mesh.primitive_plane_add(size=30); gnd = bpy.context.object; gnd.data.materials.append(mat('Ground', srgb('d8c8a8'), 0.9))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam; cam.data.lens = 50
scn.render.engine = 'CYCLES'; scn.cycles.samples = 48; scn.cycles.device = 'CPU'
scn.render.resolution_x = scn.render.resolution_y = 640; scn.view_settings.view_transform = 'Standard'
ONLY = set(a for a in sys.argv if a.startswith('shot=')) and set(a.split('=')[1] for a in sys.argv if a.startswith('shot=')) or None
def shoot(name, pos, look=(0, 0, 0.95), lens=50):
    if ONLY and name not in ONLY: return
    cam.data.lens = lens
    cam.location = pos; cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = prev + '_' + name + '.png'; bpy.ops.render.render(write_still=True)
shoot('front', (1.25, -3.3, 1.45), (0, 0, 0.9))
shoot('back', (-1.15, 3.3, 1.55), (0, 0, 0.9))
if ONLY and 'side' in ONLY: shoot('side', (0.9, 0.05, 1.62), (0, 0, 1.6))
if ONLY and 'hand' in ONLY: shoot('hand', (1.2, -0.9, 1.3), (0.62, -0.05, 1.0))
shoot('face', (0.38, -0.95, 1.66), (0, 0, 1.56))
el = math.radians(50)
shoot('top', (12 * math.cos(el) * math.sin(0.35), -12 * math.cos(el) * math.cos(0.35), 12 * math.sin(el)), (0, 0, 0.8), 50)        # the game camera
shoot('topzoom', (12 * math.cos(el) * math.sin(0.35), -12 * math.cos(el) * math.cos(0.35), 12 * math.sin(el)), (0, 0, 0.85), 160)  # same angle, tight
# the hero and the worker squaring up, seen from the game camera
if (not ONLY or 'vs' in ONLY) and VS:
    hero.location = (1.0, 0, 0); hero.rotation_euler = (0, 0, -math.pi / 2)
    before = set(scn.objects)
    bpy.ops.import_scene.gltf(filepath=VS)
    for o in set(scn.objects) - before:
        if o.parent is None: o.rotation_mode = 'XYZ'; o.scale = (1.15, 1.15, 1.15); o.location = (-1.0, 0, 0); o.rotation_euler = (0, 0, math.pi / 2)
    shoot('vs', (12 * math.cos(el) * math.sin(0.25), -12 * math.cos(el) * math.cos(0.25), 12 * math.sin(el)), (0, 0, 0.9), 85)   # game angle, tighter lens so both read at 640 px
