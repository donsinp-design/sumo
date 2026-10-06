# Sumo referee (gyoji): a stylised static prop, built entirely by script (Blender 4.2, run headless).
#   python tools/blender/gyoji.py  [out.glb] [preview_prefix] [shot=front shot=vs ...]
# Same recipe as sumo.py / worker.py: the body (head, neck, torso, arms, mitten hands) is overlapping ellipsoids and
# tapered capsules fused into ONE skin with a voxel remesh, smoothed and decimated, the robe painted onto it by region.
# The costume pieces are built the same way or lofted and fitted to that skin: wide hitatare sleeves (fused volumes,
# cut clean at the cuff, a cord along the edge), flared pleated hakama, a waist tie, kikutoji tassels, a tall black
# lacquered eboshi with a chin cord, white tabi toes, and a lacquered gunbai held forward in the right hand.
# Purple silk with a subtle gold hanabishi lattice (a 512 px texture generated here and packed into the glb).
# Blender is Z-up with the front facing -Y (his right hand is at -X); the glTF export converts to Y-up. About 1.65 m
# to the top of the head, ~1.85 m to the top of the hat.
import bpy, bmesh, math, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARGS = [a for a in sys.argv if not a.startswith('shot=')]
out = ARGS[-2] if len(ARGS) > 2 and ARGS[-2].endswith('.glb') else '/tmp/gyoji.glb'
prev = ARGS[-1] if len(ARGS) > 2 else '/tmp/gyoji_prev'
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

# ---------------------------------------------------------------- the silk: purple with a faint gold hanabishi lattice
TEX_N, TEX_M = 512, 0.26            # texture size in px, metres of cloth one texture tile covers
def silk_image():
    n = TEX_N; cells = 8
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    u, v = (x * cells) % 1.0, (y * cells) % 1.0
    def ss(e0, e1, t): t = np.clip((t - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
    d = np.abs(u - 0.5) + np.abs(v - 0.5)                                 # diamond lattice through the cell edges
    line = 1 - ss(0.008, 0.022, np.abs(d - 0.5))
    fl = np.zeros_like(u)                                                  # four-petal flower in each diamond
    for cx, cy in ((0.5, 0.41), (0.5, 0.59), (0.41, 0.5), (0.59, 0.5)):
        fl = np.maximum(fl, 1 - ss(0.045, 0.065, np.hypot(u - cx, v - cy)))
    fl = np.maximum(fl, 1 - ss(0.02, 0.035, np.hypot(u - 0.5, v - 0.5)) * 0.0)
    dot = 1 - ss(0.018, 0.03, np.minimum(np.hypot(u, v), np.minimum(np.hypot(1 - u, v), np.minimum(np.hypot(u, 1 - v), np.hypot(1 - u, 1 - v)))))
    gold_a = np.clip(line * 0.35 + fl * 0.7 + dot * 0.5, 0, 1) * 0.42
    weave = 1 + 0.035 * np.sin(y * n * math.pi * 0.5) * np.sin(x * n * math.pi * 0.25) + 0.02 * np.sin(y * n * 0.09 + np.sin(x * 9) * 2)
    base = np.array([0x48, 0x1a, 0x6e], np.float32) / 255
    gold = np.array([0xd6, 0xb0, 0x5c], np.float32) / 255
    rgb = base[None, None, :] * weave[..., None] * (1 - gold_a[..., None]) + gold[None, None, :] * gold_a[..., None]
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((n, n, 1), np.float32)], axis=2)
    img = bpy.data.images.new('SilkPattern', n, n, alpha=False)
    img.pixels.foreach_set(rgba.ravel()); img.update(); img.pack()
    return img
SILK_IMG = silk_image()
def silk_mat(name):
    m = mat(name, (1, 1, 1), 0.42); nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = SILK_IMG
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Sheen Weight'].default_value = 0.2; b.inputs['Sheen Tint'].default_value = (*srgb('b890d8'), 1)
    return m

SKIN = mat('Skin', srgb('d9a07a'), 0.6)
HAIR = mat('Hair', srgb('2a2729'), 0.5)
ROBE = silk_mat('Silk')
TRIM = mat('SilkDark', srgb('2e1442'), 0.5)        # collar, waist tie
LINING = mat('Lining', srgb('24102f'), 0.8)        # inside the cuffs
UNDER = mat('Juban', srgb('f1ece2'), 0.6)          # white under-kimono at the neck
CORD = mat('Cord', srgb('efe6d6'), 0.65)           # sleeve cords, kikutoji, hat cord
TABI = mat('Tabi', srgb('f4f1ea'), 0.6)
LACQ = mat('Lacquer', srgb('121012'), 0.22)        # eboshi, gunbai
GOLD = mat('Gold', srgb('c9a04a'), 0.3); GOLD.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.85
RED = mat('Vermilion', srgb('b0281e'), 0.35)
FUSA = mat('Fusa', srgb('7a3aa8'), 0.7)           # gunbai tassel: purple (the senior referee's colour)
INK = mat('Ink', srgb('1a1216'), 0.5)
WHITE = mat('White', srgb('f6f0e6'), 0.5)

# ---------------------------------------------------------------- helpers: volumes, fusing
PARTS = []
def ell(x, y, z, rx, ry, rz, rot=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=18, location=(x, y, z)); o = bpy.context.object; o.scale = (rx, ry, rz)
    if rot is not None: o.rotation_euler = rot.to_euler()
    PARTS.append(o); return o
def limb(a, b, ra, rb):  # a tapered capsule from a to b
    a, b = Vector(a), Vector(b); d = b - a; L = d.length
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=ra, radius2=rb, depth=L, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); PARTS.append(o)
    ell(*a, ra, ra, ra); ell(*b, rb, rb, rb)
def tris_of(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
def fuse(name, voxel, target, weight=None, smooth=(10, 6)):
    for o in scn.objects: o.select_set(False)
    for o in PARTS: o.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.join(); PARTS.clear()
    ob = bpy.context.object; ob.name = name
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    r = ob.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = voxel; bpy.ops.object.modifier_apply(modifier='rm')
    m = ob.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); m.factor = 0.8; m.iterations = smooth[0]; m.smooth_type = 'LENGTH_WEIGHTED'
    bpy.ops.object.modifier_apply(modifier='sm')
    m = ob.modifiers.new('sm2', 'SMOOTH'); m.factor = 0.5; m.iterations = smooth[1]; bpy.ops.object.modifier_apply(modifier='sm2')
    if weight:
        vg = ob.vertex_groups.new(name='dec')
        for v in ob.data.vertices: vg.add([v.index], weight(v.co), 'REPLACE')
    for _ in range(3):
        n = tris_of(ob)
        if n <= target * 1.05: break
        d = ob.modifiers.new('dec', 'DECIMATE'); d.ratio = target / n
        if weight: d.vertex_group = 'dec'; d.vertex_group_factor = 1.0
        bpy.ops.object.modifier_apply(modifier='dec')
    ob.vertex_groups.clear()
    return ob

# ---------------------------------------------------------------- the body: one skin (head, neck, slim torso, arms, hands)
HZ = 1.53
ell(0, 0.015, 0.88, 0.155, 0.11, 0.11)          # pelvis
ell(0, -0.012, 1.0, 0.158, 0.118, 0.14)         # waist / belly: slim, a little middle-aged softness
ell(0, 0.0, 1.165, 0.182, 0.112, 0.148)         # chest
ell(0, 0.035, 1.23, 0.155, 0.088, 0.095)        # upper back
limb((0, 0.015, 1.31), (0, 0.0, 1.45), 0.058, 0.052)   # neck
ell(0, 0.012, HZ + 0.02, 0.089, 0.104, 0.098)   # cranium
ell(0, -0.036, HZ - 0.015, 0.079, 0.07, 0.084)  # face
ell(0, -0.03, HZ - 0.088, 0.071, 0.066, 0.048)  # jaw: narrower than the fishmonger's
ell(0, -0.079, HZ - 0.117, 0.032, 0.028, 0.027) # chin
ell(0, -0.079, HZ + 0.035, 0.067, 0.024, 0.021) # brow ridge
ell(0, -0.1, HZ - 0.012, 0.014, 0.021, 0.029)   # nose bridge
ell(0, -0.11, HZ - 0.034, 0.017, 0.015, 0.014)  # nose tip
for s in (-1, 1):
    ell(s * 0.044, -0.069, HZ - 0.027, 0.028, 0.025, 0.024)   # cheekbones
    ell(s * 0.088, 0.03, HZ + 0.002, 0.011, 0.017, 0.025)      # ears
ARM = {}
for s in (-1, 1):
    limb((s * 0.05, 0.025, 1.37), (s * 0.195, 0.02, 1.30), 0.052, 0.047)   # trapezius slope
    ell(s * 0.2, 0.01, 1.285, 0.072, 0.075, 0.072)                        # deltoid
    J = Vector((s * 0.205, 0.01, 1.285))
    if s < 0:   # his right arm: elbow at the side, forearm forward and a little up, holding the gunbai at chest height
        E = J + Vector((-0.03, -0.05, -0.245))
        d2 = Vector((0.07, -0.96, 0.25)).normalized()
    else:       # left arm: relaxed, hanging a little out and forward
        E = J + Vector((0.035, 0.01, -0.245))
        d2 = Vector((0.03, -0.12, -1.0)).normalized()
    W = E + d2 * 0.235
    limb(J, E, 0.056, 0.05); ell(*E, 0.05, 0.05, 0.05); limb(E, W, 0.05, 0.038)
    limb(W - d2 * 0.02, W + d2 * 0.035, 0.033, 0.035)                         # wrist
    if s < 0:   # a fist round the gunbai handle
        HD = Vector((-0.12, -0.62, 0.78)).normalized()                         # handle axis: up and forward
        f = (d2 - HD * d2.dot(HD)).normalized(); c = HD.cross(f)
        R = Matrix((f, HD, c)).transposed()
        H0 = W + d2 * 0.058
        ell(*H0, 0.05, 0.046, 0.042, R)                                        # fist
        ell(*(H0 + f * 0.022 - c * 0.006), 0.034, 0.05, 0.036, R)              # curled fingers / knuckles
        ell(*(H0 + HD * 0.036 + f * 0.012 + c * 0.02), 0.026, 0.016, 0.018, R) # thumb over the top
        GRIP = H0 + f * 0.01
    else:       # relaxed mitten hand (as worker.py), palm in, thumb forward
        xh = d2; yh = (Vector((0, -1, 0)) - d2 * d2.y).normalized(); zz = xh.cross(yh)
        up = -s * zz; R = Matrix((xh, yh, zz)).transposed()
        H0 = W + d2 * 0.03
        ell(*(H0 + xh * 0.05), 0.056, 0.046, 0.027, R)
        ell(*(H0 + xh * 0.11 - up * 0.008), 0.046, 0.044, 0.024, R)
        ell(*(H0 + xh * 0.142 - up * 0.024), 0.028, 0.04, 0.02, R)
        limb(H0 + xh * 0.03 + yh * 0.032 - up * 0.007, H0 + xh * 0.088 + yh * 0.072 - up * 0.022, 0.021, 0.017)
    ARM[s] = (J, E, W, d2)
def body_w(c):
    if c.z > HZ - 0.16 and abs(c.x) < 0.12: return 0.22 if c.y < 0.0 else 0.5   # the face keeps the most
    if any((c - ARM[s][2]).length < 0.16 for s in (-1, 1)): return 0.4             # hands
    if c.z > 1.25 and abs(c.x) < 0.13: return 0.45                                 # neck / collar
    return 1.0
body = fuse('Body', 0.009, 4100, body_w)
print('body triangles', tris_of(body))

# ---------------------------------------------------------------- paint the robe onto the skin
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(body, dg)
def path_on_skin(ctrl, n=40, tree=None):
    tree = tree or bvh
    ctrl = [Vector(c) for c in ctrl]; out_ = []
    for i in range(n):
        t = i / (n - 1) * (len(ctrl) - 1); k = min(int(t), len(ctrl) - 2); f = t - k
        p0, p1, p2, p3 = ctrl[max(k - 1, 0)], ctrl[k], ctrl[k + 1], ctrl[min(k + 2, len(ctrl) - 1)]
        q = 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)
        loc, nor, _, _ = tree.find_nearest(q); out_.append(loc)
    for _ in range(4):
        out_ = [out_[0]] + [(out_[i - 1] + 2 * out_[i] + out_[i + 1]) / 4 for i in range(1, n - 1)] + [out_[-1]]
    res = []
    for p in out_:
        loc, nor, _, _ = tree.find_nearest(p); res.append((loc, nor))
    return res
half = [(0.0, -0.108, 1.215), (0.034, -0.099, 1.28), (0.058, -0.078, 1.335), (0.071, -0.043, 1.372), (0.072, 0.005, 1.39), (0.051, 0.047, 1.396)]
COLLAR_PATH = path_on_skin(half + [(0, 0.064, 1.394)] + [(-x, y, z) for x, y, z in half[::-1]], 56)
CP = [(p, n, (COLLAR_PATH[min(i + 1, 55)][0] - COLLAR_PATH[max(i - 1, 0)][0]).normalized()) for i, (p, n) in enumerate(COLLAR_PATH)]
def inside_collar(c):
    if not (abs(c.x) < 0.2 and c.z > 1.2): return False
    if c.z > 1.45: return True
    p, n, t = min(CP, key=lambda q: (q[0] - c).length_squared)
    return (c - p).dot(n.cross(t)) > 0
bm = bmesh.new(); bm.from_mesh(body.data)
def cut(co, no, keep):
    vs = [v for v in bm.verts if keep(v.co)]; vset = set(vs)
    es = [e for e in bm.edges if e.verts[0] in vset and e.verts[1] in vset]
    fs = [f for f in bm.faces if all(v in vset for v in f.verts)]
    bmesh.ops.bisect_plane(bm, geom=vs + es + fs, plane_co=co, plane_no=no)
for s in (-1, 1):
    J, E, W, d2 = ARM[s]; cut(W, d2, lambda c, W=W: (c - W).length < 0.14)
for mm in (ROBE, SKIN, UNDER): body.data.materials.append(mm)
for f in bm.faces:
    c = f.calc_center_median(); hand = False
    for s in (-1, 1):
        J, E, W, d2 = ARM[s]
        if (c - W).length < 0.2 and (c - W).dot(d2) > 0: hand = True
    if hand: f.material_index = 1
    elif inside_collar(c): f.material_index = 2 if (c.y < -0.03 and c.z < 1.355) else 1
    else: f.material_index = 0
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
def hit(origin, direction, tree=None):
    loc, nor, _, _ = (tree or bvh).ray_cast(Vector(origin), Vector(direction).normalized(), 2.0); return loc, nor
def loop_around(center, axis, reach, n=48, tree=None):
    center, axis = Vector(center), Vector(axis).normalized()
    u = axis.orthogonal().normalized(); v = axis.cross(u); pts = []
    for k in range(n):
        a = 2 * math.pi * k / n; dr = u * math.cos(a) + v * math.sin(a)
        loc, nor = hit(center + dr * reach, -dr, tree)
        if loc is not None: pts.append((loc, nor))
    return pts
def band(name, pts, hw, ht, off, m_, closed=True, K=10, twist=None, ends=True):
    """a strip (superellipse cross-section, hw wide along the skin, ht thick off it) along surface points"""
    N = len(pts)
    for _ in range(3):
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
def kiku(name, loc, r, m_, nrm=None):
    """kikutoji: a small chrysanthemum pompom of tufts"""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=7, radius=r, location=(0, 0, 0)); o = bpy.context.object; o.name = name
    for v in o.data.vertices:
        d = v.co.normalized(); th = math.atan2(d.y, d.x); ph = math.acos(max(-1, min(1, d.z)))
        v.co = v.co * (1 + 0.22 * abs(math.sin(2.5 * th + 3 * ph)) - 0.08 + 0.08 * math.sin(5 * ph + th))
    if nrm is not None: o.scale = Vector((1, 1, 1)) - Vector([abs(x) for x in nrm]) * 0.25   # a little flatter against the cloth
    o.location = loc; bpy.ops.object.transform_apply(scale=True); return add(o, m_)
def tassel(name, top, length, r, m_):
    """a hanging fusa: knot + fluted bell of threads"""
    top = Vector(top)
    sphere(name + 'Knot', top, (r * 0.75, r * 0.75, r * 0.75), m_, 8, 5)
    bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=r * 1.15, radius2=r * 0.55, depth=length, location=top - Vector((0, 0, length / 2 + r * 0.4)))
    o = bpy.context.object; o.name = name
    for v in o.data.vertices:
        if v.co.length > 1e-4:
            a = math.atan2(v.co.y, v.co.x); k = 1 + 0.12 * math.cos(7 * a); v.co.x *= k; v.co.y *= k
    return add(o, m_)
def boundary_loop(me_bm, edges):
    """order a set of boundary edges into one loop of vertex coordinates"""
    adj = {}
    for e in edges:
        a, b = e.verts; adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    start = next(iter(adj)); loop = [start]; prev_ = None; cur = start
    while True:
        nxt = [v for v in adj[cur] if v is not prev_]
        if not nxt or nxt[0] is start: break
        prev_, cur = cur, nxt[0]; loop.append(cur)
        if len(loop) > len(adj): break
    return [v.co.copy() for v in loop]

# ---------------------------------------------------------------- collar: dark silk bands crossing on the chest, a white juban edge
band('Collar', COLLAR_PATH[:28], 0.024, 0.006, 0.003, TRIM, closed=False, K=5)
band('Collar', COLLAR_PATH[27:], 0.024, 0.006, 0.0075, TRIM, closed=False, K=5)
band('JubanNeck', [p for p in loop_around((0, 0.0, 1.352), (0, 0, 1), 0.3, 40) if p[0].y < -0.03 and abs(p[0].x) < 0.065], 0.007, 0.004, 0.0, UNDER, closed=False, K=4)

# ---------------------------------------------------------------- wide sleeves: fused volumes hanging from the arms, cut clean at the cuff
def cut_cap(ob, co, no):
    """slice the volume with a plane (dropping the side `no` points to), cap the cut; return the rim loop"""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
    edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
    rim = boundary_loop(bm, edges)
    cap = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges, normal=Vector(no))
    for f in cap['geom']:
        if isinstance(f, bmesh.types.BMFace): f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data); bm.free(); return rim
def bore(ob, centre, axis, r, depth):
    """bore a hole for the wrist into the cuff (lined in dark silk)"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r, depth=depth, location=centre)
    cyl = bpy.context.object; cyl.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler(); cyl.data.materials.append(LINING)
    md = ob.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = cyl; md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cyl, do_unlink=True)
def rim_cord(name, rim, plane_no, r=0.0075):
    step = max(1, len(rim) // 44); rim = rim[::step]
    ctr = sum(rim, Vector()) / len(rim); N = len(rim)
    for _ in range(3): rim = [(rim[i - 1] + 2 * rim[i] + rim[(i + 1) % N]) / 4 for i in range(N)]
    pts = []
    for p in rim:
        radial = (p - ctr); radial -= plane_no * radial.dot(plane_no)
        pts.append((p, (radial.normalized() * 0.6 + plane_no * 0.8).normalized()))
    return band(name, pts, r, r, -r * 0.9, CORD, K=5)
SLEEVE = {}
for s in (-1, 1):
    J, E, W, d2 = ARM[s]
    ell(*(J + Vector((s * 0.012, 0, -0.022))), 0.078, 0.085, 0.066)            # shoulder: sloped, not puffed
    limb(J + Vector((s * 0.01, 0, -0.02)), E, 0.08, 0.084)
    limb(E, W, 0.084, 0.076)
    if s < 0:   # forearm forward: the sleeve hangs as a deep curtain under it, and behind the upper arm
        for i in range(10):
            t = i / 9; P = E + (W - E) * t
            limb(P + Vector((0, 0, -0.02)), Vector((P.x + s * 0.03, P.y + 0.01, 0.775 - 0.035 * t)), 0.06, 0.058)
        for t in (0.3, 0.5, 0.7, 0.9):
            P = J + (E - J) * t; limb(P, Vector((P.x + s * 0.02, P.y + 0.06, 0.8)), 0.06, 0.058)
    else:       # arm hanging: the sleeve is a tall panel beside it, widening towards the back at the bottom
        L1, L2 = (E - J).length, (W - E).length
        for i in range(12):
            t = 0.12 + 1.0 * i / 11; dd = t * (L1 + L2)
            P = J + (E - J).normalized() * dd if dd < L1 else E + d2 * (dd - L1)
            limb(P + Vector((0, -0.03, 0)), P + Vector((s * 0.02 * t, 0.05 + 0.17 * t ** 1.2, 0)), 0.06, 0.06)
    sl = fuse('Sleeve', 0.014, 1000)
    sl.data.materials.append(ROBE); sl.data.materials.append(LINING)
    if s < 0:
        nh = Vector((d2.x, d2.y, 0)).normalized()
        rim = cut_cap(sl, W + d2 * 0.004, nh)
        bore(sl, W, d2, 0.043, 0.13)
        rim_cord('SleeveCord', rim, nh)
        low = min(rim, key=lambda p: p.z - 0.3 * (-p.y))          # the bottom front corner: the cord's end hangs there
    else:
        Q = W + d2 * ((0.782 - W.z) / d2.z)
        rim = cut_cap(sl, Vector((0, 0, 0.782)), Vector((0, 0, -1)))
        bore(sl, Q, d2, 0.045, 0.12)
        rim_cord('SleeveCord', rim, Vector((0, 0, -1)))
        low = min(rim, key=lambda p: p.y)
    bpy.context.view_layer.objects.active = sl; sl.select_set(True); bpy.ops.object.shade_smooth()
    SLEEVE[s] = sl
    # the cord's tail with its tassel, hanging from the sleeve's lower front corner
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.005, depth=0.06, location=low + Vector((0, -0.004, -0.03))); add(bpy.context.object, CORD)
    tassel('SleeveTassel', low + Vector((0, -0.004, -0.065)), 0.07, 0.016, CORD)
    print('sleeve', s, tris_of(sl))

# ---------------------------------------------------------------- hakama: wide pleated trousers flaring to the floor
ZT, NA, NZ = 0.935, 48, 12
top = []
for k in range(NA):
    th = 2 * math.pi * k / NA; dr = Vector((math.sin(th), -math.cos(th), 0))
    loc, _ = hit(Vector((0, 0.015, ZT)) + dr * 0.5, -dr)
    top.append((Vector((loc.x, loc.y - 0.015, 0)).length + 0.012))
def tri(x): x = x % 1.0; return 1 - 2 * abs(x - 0.5)        # 0..1..0 triangle wave
hv, hf = [], []
for i in range(NZ + 1):
    t = i / NZ; z = ZT + (0.012 - ZT) * t
    rx, ry = 0.168 + 0.2 * t ** 1.45, 0.128 + 0.155 * t ** 1.45
    b = min(t / 0.3, 1); b = b * b * (3 - 2 * b)
    for k in range(NA):
        th = 2 * math.pi * k / NA; sn, cs = math.sin(th), math.cos(th)
        re = 1 / math.sqrt((sn / rx) ** 2 + (cs / ry) ** 2)
        r = (1 - b) * top[k] + b * re
        r *= 1 + 0.07 * t ** 0.8 * (tri(th / (2 * math.pi) * 16 + 0.25) - 0.5)     # knife pleats
        for c0 in (0.0, math.pi):                                                  # the split between the legs, front and back
            dth = math.atan2(math.sin(th - c0), math.cos(th - c0))
            r *= 1 - (0.06 * max(t - 0.2, 0) + 0.2 * max(t - 0.55, 0) ** 1.5) * math.exp(-(dth / (0.1 + 0.25 * t ** 2)) ** 2)
        hv.append(Vector((sn * r, 0.015 - cs * r, z)))
for i in range(NZ):
    for k in range(NA):
        k2 = (k + 1) % NA; hf.append((i * NA + k, i * NA + k2, (i + 1) * NA + k2, (i + 1) * NA + k))
hak = mesh_obj('Hakama', hv, hf, ROBE)
bm = bmesh.new(); bm.from_mesh(hak.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(hak.data); bm.free()
hem = [(hv[NZ * NA + k] + Vector((0, 0, 0.004)), Vector((hv[NZ * NA + k].x, hv[NZ * NA + k].y - 0.015, 0)).normalized()) for k in range(NA)]
band('HakamaHem', hem, 0.009, 0.007, -0.004, TRIM, K=4)
# waist tie (himo) over the join of robe and hakama, a knot at the front
tie = [(hv[k] + Vector((0, 0, 0.012)), Vector((hv[k].x, hv[k].y - 0.015, 0)).normalized()) for k in range(NA)]
band('Himo', tie, 0.022, 0.008, 0.002, TRIM, K=5)
fz = hv[0] + Vector((0, -0.02, 0.012))
sphere('HimoKnot', fz, (0.032, 0.014, 0.02), TRIM, 12, 8)
for s in (-1, 1):
    sphere('HimoTail', fz + Vector((s * 0.016, 0.0, -0.06)), (0.016, 0.009, 0.05), TRIM, 10, 6, (0, s * 0.18, 0))
# koshi-ita: the stiff back plate of the hakama
kv = []
for zz in (ZT + 0.005, ZT + 0.085):
    for x in (-0.11, -0.04, 0.04, 0.11):
        w_ = x * (1 - 0.15 * (zz - ZT) / 0.085)
        l, _ = hit((w_, 1, zz), (0, -1, 0)); kv.append(Vector((w_, l.y + 0.016, zz)))
kp = mesh_obj('KoshiIta', kv, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6)], ROBE)
sol = kp.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.012; sol.offset = 0; bpy.ops.object.modifier_apply(modifier='sol')
bv_ = kp.modifiers.new('bev', 'BEVEL'); bv_.width = 0.004; bv_.segments = 2; bpy.ops.object.modifier_apply(modifier='bev')

# ---------------------------------------------------------------- white tabi toes peeking out under the hem
for s in (-1, 1):
    sphere('Tabi', (s * 0.112, -0.19, 0.03), (0.046, 0.115, 0.031), TABI, 14, 8)
    sphere('TabiToe', (s * 0.074, -0.278, 0.026), (0.019, 0.03, 0.022), TABI, 10, 6)

# ---------------------------------------------------------------- kikutoji on the chest, the sleeves and the back
for s in (-1, 1):
    l, n = hit((s * 0.085, -1, 1.175), (0, 1, 0)); kiku('Kiku', l + n * 0.016, 0.026, CORD, n)
l, n = hit((0, 1, 1.13), (0, -1, 0)); kiku('Kiku', l + n * 0.016, 0.026, CORD, n)
for s in (-1, 1):
    J, E, W, d2 = ARM[s]
    st = BVHTree.FromObject(SLEEVE[s], bpy.context.evaluated_depsgraph_get())
    for zz, yy in ((1.15, -0.02), (1.15, 0.06)):
        l, n = hit((s * 1, yy, zz), (-s, 0, 0), st)
        if l is not None: kiku('Kiku', l + n * 0.012, 0.02, CORD, n)

# ---------------------------------------------------------------- face: small dark eyes with glints, level brows, nose, a calm mouth
def on_face(x, z, off=0.0):
    loc, nor = hit((x, -1, z), (0, 1, 0)); return loc + nor * off, nor
for s in (-1, 1):
    p, n = on_face(s * 0.036, HZ + 0.006)
    sphere('Eye', p + Vector((0, 0.002, 0)), (0.012, 0.008, 0.0135), INK, 10, 7, (0, 0, s * 0.22))
    sphere('EyeHi', p + Vector((-s * 0.004, -0.007, 0.005)), (0.0038, 0.003, 0.0042), WHITE, 6, 5)
    p, n = on_face(s * 0.041, HZ + 0.036)
    bpy.ops.mesh.primitive_cube_add(location=p + Vector((0, -0.004, 0))); b = bpy.context.object; b.name = 'Brow'
    b.scale = (0.027, 0.0075, 0.0058); b.rotation_euler = (0, s * 0.06, s * 0.28)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    bv_ = b.modifiers.new('bev', 'BEVEL'); bv_.width = 0.005; bv_.segments = 2; bpy.ops.object.modifier_apply(modifier='bev'); add(b, HAIR)
mp = []                                                          # a short, nearly straight line: composed, a hint of a smile
for i in range(9):
    u_ = -1 + 2 * i / 8; p, n = on_face(u_ * 0.021, HZ - 0.069 + 0.0035 * u_ * u_); mp.append((p, n))
band('Mouth', mp, 0.0026, 0.0024, 0.0, INK, closed=False, K=5)

# hair: short, neat, covering the sides and back of the head down to the nape (the hat covers the crown)
HC = Vector((0, 0.012, HZ + 0.02))
def hairline(a):
    y = -0.11 * math.cos(a)
    if y < -0.06: return 0.03 + 0.02 * min((-y - 0.02) / 0.05, 1)
    if y < 0.02:
        t = (y + 0.06) / 0.08; return 0.045 + (-0.05 - 0.045) * (0.5 - 0.5 * math.cos(math.pi * t))
    yb = max(0, min(1, (y - 0.02) / 0.09))
    return -0.05 - 0.045 * (0.5 - 0.5 * math.cos(math.pi * yb))
NHA, NHE = 30, 5
hv2, hf2 = [], []
for k in range(NHA):
    a = 2 * math.pi * k / NHA; dh = Vector((math.sin(a), -math.cos(a), 0))
    e0 = math.atan2(hairline(a), 0.1)
    for r_ in range(NHE):
        e = e0 + (math.radians(70) - e0) * (r_ / (NHE - 1)) ** 0.85
        dr = dh * math.cos(e) + Vector((0, 0, 1)) * math.sin(e)
        l, nrm = hit(HC + dr * 0.3, -dr); hv2.append(l + nrm * 0.003)
for k in range(NHA):
    k2 = (k + 1) % NHA
    for r_ in range(NHE - 1): hf2.append((k * NHE + r_, k2 * NHE + r_, k2 * NHE + r_ + 1, k * NHE + r_ + 1))
cap = mesh_obj('Hair', hv2, hf2, HAIR)
sol = cap.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.008; sol.offset = 1; bpy.ops.object.modifier_apply(modifier='sol')

# ---------------------------------------------------------------- eboshi: tall black lacquered hat, flattened at the sides, crest folded forward
NE_A, NE_H, H_H = 28, 12, 0.21
base = []
for k in range(NE_A):
    th = 2 * math.pi * k / NE_A; dh = Vector((math.sin(th), -math.cos(th), 0))
    zb = HZ + 0.052 + 0.016 * math.cos(th)                 # sits higher over the brow, lower at the back
    l, n = hit(Vector((HC.x, HC.y, zb)) + dh * 0.3, -dh)
    base.append(Vector((l.x, l.y, zb)) + dh * 0.013)
BC = sum(base, Vector()) / NE_A
def sst(e0, e1, x): x = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return x * x * (3 - 2 * x)
ev = []
for i in range(NE_H + 1):
    h = (i / NE_H) ** 0.85
    ctr = BC + Vector((0, 0.045 * h ** 1.6, H_H * h))                 # leaning back
    sx = 1 - 0.5 * h ** 1.3; sy = 1 - 0.08 * h                        # pinched at the sides into a front-to-back crest
    if h > 0.8: k_ = math.sqrt(max(0.0, 1 - ((h - 0.8) / 0.2) ** 2)); sx *= 0.4 + 0.6 * k_; sy *= k_
    for k in range(NE_A):
        th = 2 * math.pi * k / NE_A; q = base[k] - BC
        dth = math.atan2(math.sin(th), math.cos(th))
        dh = Vector((math.sin(th), -math.cos(th), 0))
        crease = -0.006 * math.exp(-(dth / 0.18) ** 2) * sst(0.1, 0.4, h)                      # a soft vertical crease down the front
        fold = 0.022 * math.exp(-(dth / 0.5) ** 2) * sst(0.55, 0.9, h)                         # the crest folded forward at the top
        crinkle = 1 + 0.01 * math.sin(h * 24 + th * 2)                                         # lacquer wrinkles (sabi)
        ev.append(ctr + Vector((q.x * sx, q.y * sy, q.z * (1 - h))) * crinkle + dh * (crease + fold))
ev.append(BC + Vector((0, 0.045 - 0.02, H_H + 0.004)))
ef = []
for i in range(NE_H):
    for k in range(NE_A):
        k2 = (k + 1) % NE_A; ef.append((i * NE_A + k, i * NE_A + k2, (i + 1) * NE_A + k2, (i + 1) * NE_A + k))
for k in range(NE_A): ef.append((NE_H * NE_A + k, NE_H * NE_A + (k + 1) % NE_A, len(ev) - 1))
hat = mesh_obj('Eboshi', ev, ef, LACQ)
bm = bmesh.new(); bm.from_mesh(hat.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(hat.data); bm.free()
band('EboshiRim', [(base[k], (base[k] - BC - Vector((0, 0, (base[k] - BC).z))).normalized()) for k in range(NE_A)], 0.006, 0.004, -0.004, LACQ, K=4)
# chin cord: from the hat down in front of the ears, tied under the chin
for s in (-1, 1):
    pth = path_on_skin([(s * 0.092, 0.0, HZ + 0.05), (s * 0.09, -0.012, HZ - 0.01), (s * 0.078, -0.022, HZ - 0.075),
                        (s * 0.045, -0.045, HZ - 0.125), (s * 0.008, -0.07, HZ - 0.142)], 16)
    band('ChinCord', pth, 0.0042, 0.0042, 0.002, CORD, closed=False, K=4)
kn = path_on_skin([(0, -0.07, HZ - 0.143)], 2)[0][0]
sphere('ChinKnot', kn + Vector((0, -0.006, -0.006)), (0.012, 0.01, 0.01), CORD, 10, 6)
for s in (-1, 1):
    sphere('ChinTail', kn + Vector((s * 0.008, -0.01, -0.035)), (0.0045, 0.0045, 0.03), CORD, 8, 5, (0, s * 0.15, 0))

# ---------------------------------------------------------------- the gunbai in his right hand
a = HD; wv = (Vector((1, 0, 0)) - a * a.x).normalized(); fn = a.cross(wv)
G = GRIP
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.0115, depth=0.17, location=G + a * 0.012)
o = bpy.context.object; o.rotation_euler = a.to_track_quat('Z', 'Y').to_euler(); bpy.ops.object.transform_apply(rotation=True); add(o, LACQ); o.name = 'GunbaiHandle'
sphere('GunbaiButt', G - a * 0.075, (0.016, 0.016, 0.016), GOLD, 8, 6)
sphere('GunbaiCollar', G + a * 0.095, (0.017, 0.017, 0.017), GOLD, 8, 6)
V0, V1 = 0.1, 0.43
def gw(v):  # half-width of the paddle along its length: narrow neck, round gourd blade
    e = (v - 0.275) / 0.155; blade = 0.125 * math.sqrt(max(0.0, 1 - e * e)) ** 0.85
    neck = 0.02 + 0.25 * max(0.0, v - V0) ** 1.4
    return max(blade, neck) if v < 0.42 else blade
NV = 22; prof = []
for i in range(NV + 1):
    v = V0 + (V1 - V0) * (1 - math.cos(math.pi * i / NV)) / 2; prof.append((v, gw(v)))
outline = [(w_, v) for v, w_ in prof] + [(-w_, v) for v, w_ in prof[::-1][1:-1]]
outline = [p for i, p in enumerate(outline) if i == 0 or (Vector(p) - Vector(outline[i - 1])).length > 1e-4]
TH = 0.0065; gv = []
for side in (1, -1):
    for u_, v_ in outline: gv.append(G + a * v_ + wv * u_ + fn * TH * side)
NO = len(outline)
gf = [tuple(range(NO)), tuple(range(2 * NO - 1, NO - 1, -1))] + [(k, (k + 1) % NO, NO + (k + 1) % NO, NO + k) for k in range(NO)]
pad = mesh_obj('GunbaiBlade', gv, gf, LACQ)
bm = bmesh.new(); bm.from_mesh(pad.data); bmesh.ops.triangulate(bm, faces=bm.faces[:], ngon_method='BEAUTY'); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(pad.data); bm.free()
rim = [(G + a * v_ + wv * u_, None) for u_, v_ in outline]
cen = G + a * 0.27
rim = [(p, (p - cen - fn * (p - cen).dot(fn)).normalized()) for p, _ in rim]
band('GunbaiRim', rim, 0.0095, 0.0045, -0.0035, GOLD, K=5)
for side in (1, -1):   # a gold ring with a vermilion sun on both faces
    for r0, r1, m_, dz in ((0.058, 0.072, GOLD, 0.0012), (0.0, 0.045, RED, 0.0010)):
        vs, fs = [], []
        for k in range(32):
            ang = 2 * math.pi * k / 32; dd = wv * math.cos(ang) + a * math.sin(ang)
            for rr in (r0, r1): vs.append(cen + dd * rr + fn * side * (TH + dz))
        for k in range(32):
            k2 = (k + 1) % 32; fs.append((2 * k, 2 * k2, 2 * k2 + 1, 2 * k + 1) if side > 0 else (2 * k, 2 * k + 1, 2 * k2 + 1, 2 * k2))
        mesh_obj('GunbaiSun', vs, fs, m_)
butt = G - a * 0.088
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.004, depth=0.07, location=butt + Vector((0, 0, -0.035))); add(bpy.context.object, FUSA)
tassel('GunbaiFusa', butt + Vector((0, 0, -0.072)), 0.09, 0.02, FUSA)

# ---------------------------------------------------------------- UVs: box projection of the silk (one tile = TEX_M metres)
for o in scn.objects:
    if o.type != 'MESH': continue
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    uv = me.uv_layers[0]; uv.name = 'UVMap'
    mw = o.matrix_world
    for p in me.polygons:
        nn = (mw.to_3x3() @ p.normal); ax = max(range(3), key=lambda i: abs(nn[i]))
        for li in p.loop_indices:
            c = mw @ me.vertices[me.loops[li].vertex_index].co
            u_, v_ = ((c.x, c.z) if ax == 1 else (c.y, c.z) if ax == 0 else (c.x, c.y))
            uv.data[li].uv = (u_ / TEX_M, v_ / TEX_M)

# ---------------------------------------------------------------- one object, origin at the feet, export
from collections import Counter
cnt = Counter()
for o in scn.objects:
    if o.type == 'MESH': cnt[o.name.split('.')[0]] += tris_of(o)
print('parts', dict(cnt))
for o in scn.objects: o.select_set(o.type == 'MESH')
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
hero = bpy.context.object; hero.name = 'Gyoji'
scn.cursor.location = (0, 0, 0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
tris = tris_of(hero)
print('triangles', tris, 'height', max((hero.matrix_world @ v.co).z for v in hero.data.vertices))
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True)

# ---------------------------------------------------------------- preview renders (Cycles, CPU): soft sky + a warm sun
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (*srgb('b8c8dc'), 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 3.2; sun.data.color = srgb('ffe8c8'); sun.data.angle = 0.25; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
bpy.ops.mesh.primitive_plane_add(size=30); gnd = bpy.context.object; gnd.data.materials.append(mat('Ground', srgb('d8c8a8'), 0.9))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam; cam.data.lens = 50
scn.render.engine = 'CYCLES'; scn.cycles.samples = 48; scn.cycles.device = 'CPU'; scn.cycles.use_denoising = True
scn.render.resolution_x = scn.render.resolution_y = 640; scn.view_settings.view_transform = 'Standard'
ONLY = set(a.split('=')[1] for a in sys.argv if a.startswith('shot=')) or None
def shoot(name, pos, look=(0, 0, 0.95), lens=50):
    if ONLY and name not in ONLY: return
    cam.data.lens = lens
    cam.location = pos; cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = prev + '_' + name + '.png'; bpy.ops.render.render(write_still=True)
shoot('front', (1.25, -3.4, 1.45), (0, 0, 0.92))
shoot('front2', (-1.6, -3.1, 1.35), (0, 0, 0.92))
shoot('back', (-1.15, 3.4, 1.55), (0, 0, 0.92))
shoot('side', (3.5, -0.3, 1.2), (0, 0, 0.92))
shoot('face', (0.32, -0.95, HZ + 0.08), (0, 0, HZ - 0.0))
el = math.radians(50)
if not ONLY or ONLY & {'top', 'vs'}:
    before = set(scn.objects)
    bpy.ops.import_scene.gltf(filepath=VS)
    for o in set(scn.objects) - before:
        if o.parent is None: o.rotation_mode = 'XYZ'; o.scale = (1.15, 1.15, 1.15); o.location = (2.5, 0, 0)
    tgt = (1.25, 0, 0.8)
    camp = lambda az: (tgt[0] + 12 * math.cos(el) * math.sin(az), -12 * math.cos(el) * math.cos(az), 12 * math.sin(el))
    shoot('top', camp(0.35), tgt, 50)        # the game camera
    shoot('vs', camp(0.2), tgt, 95)          # same angle, tighter
