# Fish-market street corner test area (Blender 4.2 headless, built by script).
#   <bl python> tools/blender/corner.py [noprev]
# Writes <OUT>/corner.glb (Y-up glTF, flat base-colour materials) and <OUT>/prev.png (Cycles preview).
# Blender Z up, metres. The fish stall is centred on the origin, 4.5 m long along Y, its counter front at x=0 facing +X
# (the street). Vending machines continue along +Y, the two-storey building front stands behind (wall plane x=-2.6),
# the utility pole at the street edge on the -Y side. Everything is parented to the empty "Corner".
# Style: simplified-but-rich toy-like modelling, soft bevels, matte flat colours, no image textures (only text meshes).
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix

OUT = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad/corner'
NOPREV = 'noprev' in sys.argv
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene; C = bpy.context
RND = random.Random(11)
FONT = None
for f in ('/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf', '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'):
    if os.path.exists(f): FONT = bpy.data.fonts.load(f); break

# ================================================================ materials: flat, matte, softened colours
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
MATS = {}
def mat(name, h, rough=0.72, metal=0.0, emit=0.0, alpha=1.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(h), 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Specular IOR Level'].default_value = 0.28
    if emit: b.inputs['Emission Color'].default_value = (*srgb(h), 1); b.inputs['Emission Strength'].default_value = emit
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'
    m.diffuse_color = (*srgb(h), alpha); MATS[name] = m; return m
PAL = {  # name: hex, roughness
    'wood': 'c99466', 'wood2': 'b8804f', 'wood_dk': '8a5a3a', 'wood_pale': 'dcb58a', 'paint_teal': '4f9a96', 'plinth': '4a3f3a',
    'frame': '5b8a86', 'frame_dk': '3f6461', 'stripe_a': '3f74b0', 'stripe_b': 'f4efe2', 'pipe_white': 'f1ede3',
    'steel': 'b9bfc4', 'tray': 'd3d8da', 'ice': 'dff0f5', 'ice2': 'c6e4ee', 'styro': 'f5f4ee', 'styro_lbl': '4f7fc0',
    'crate_blue': '3f86c8', 'crate_white': 'eef1ef', 'crate_green': '58a65a', 'tray_blk': '2b2a2e',
    'ink': '25222a', 'paper': 'f8f5ec', 'red': 'd84a3e', 'red_dk': 'b23a33', 'yellow': 'f2c94c', 'navy': '2a4372',
    'black': '26262b', 'dark': '3a3a40', 'grey': '8e959b', 'grey_lt': 'c7ccd0', 'white': 'f3f1ea', 'bulb': 'ffe7b0',
    'mack_back': '4f8fa8', 'mack_str': '2c5a72', 'mack_belly': 'e3e8ea', 'fin_grey': '9fb3bd', 'eye_w': 'f6f3ea',
    'snap_back': 'e8706a', 'snap_belly': 'f6c0b0', 'snap_fin': 'ee8f80', 'aji_back': '8fa39a', 'aji_belly': 'e6e9e4',
    'buri_back': '5d7895', 'buri_belly': 'eceeea', 'buri_line': 'e8c955', 'tuna': 'c23a45', 'tuna_fat': 'f2b5b0', 'tuna_skin': '3e4a5c',
    'squid': 'f6ebe4', 'squid_dk': 'cf7f70', 'octo': 'd9573f', 'octo_lt': 'f2ae8f', 'prawn': 'f08a5a', 'prawn_lt': 'f7b98f',
    'shell': 'eea078', 'shell_in': 'f6e8d8', 'scal_meat': 'fbf6ee', 'scal_roe': 'f0a35c', 'baran': '58b85a', 'lemon': 'f4d84a',
    'leaf': '5f9e4a', 'leaf2': '4b8a3c', 'leaf3': '78b25a', 'pot': 'c46f4f', 'pot_blue': '5b80aa', 'soil': '5a4232',
    'hose': '62b35c', 'boot': 'eceae2', 'boot_sole': '3a3836', 'bucket': '4d8fd1', 'bamboo': 'd8b06c',
    'chalk': '2f4a3f', 'chalk_w': 'f2efe4', 'chalk_y': 'f4d47c', 'chalk_p': 'f2a6aa', 'lantern': 'd8493b',
    'plaster': 'ecdcc0', 'siding': 'b9c9c4', 'siding2': 'aebfba', 'tile_a': 'a88972', 'tile_b': 'b5977f', 'tile_w': 'cfdcd6',
    'grout': '7e7a74', 'band': '8b6a52', 'alu': 'cfd3d3', 'glass': '7e9bb2', 'curtain': 'f1e0ae', 'shutter': 'b8bdc1',
    'shutter_dk': '8d949a', 'interior': '6c5648', 'sign': 'f7f2e4', 'ac': 'eceae3', 'drain': '8fa0a8',
    'vm_red': 'd9473e', 'vm_red_dk': 'b8382f', 'vm_white': 'eef0ee', 'vm_blue': '3a7ac2', 'vm_lblue': '8fc8ea', 'vm_panel': '4b5058',
    'vm_inner': 'eef4f6', 'vm_shelf': 'c9d0d4', 'vm_btn': '7fd0ff', 'vm_led': '7fe08a', 'bin': 'dde4dc',
    'pole': 'b8b5ad', 'guard_y': 'f1c232', 'guard_k': '2c2a28', 'transf': '9aa3a8', 'insul': '7a8f80',
    'bun_r': 'e2574c', 'bun_y': 'f3c84b', 'bun_b': '4a86c8', 'bun_g': '5cae6a', 'bun_w': 'f5f1e6', 'bun_p': 'ef9ab0',
    'drink_g': 'a9cf7c', 'drink_w': 'cfe6f1', 'drink_o': 'f2a640', 'drink_br': '86593c', 'drink_bl': '5ea3df', 'drink_rd': 'cf4a3f',
    'drink_cap': 'f5f3ee', 'drink_lbl': 'f8f6f0', 'rope': 'cdb48a',
}
ROUGH = {'steel': 0.5, 'tray': 0.55, 'ice': 0.45, 'ice2': 0.45, 'glass': 0.3, 'alu': 0.5, 'tuna': 0.6, 'squid': 0.6}
def M(n):
    if n in MATS: return MATS[n]
    return mat(n, PAL[n], ROUGH.get(n, 0.75))
EMIT = {'bulb': mat('bulb_lit', 'ffe7b0', 0.4, emit=5.0), 'vm_inner': mat('vm_inner_lit', 'eef4f6', 0.6, emit=0.45),
        'vm_btn': mat('vm_btn_lit', '86d4ff', 0.5, emit=1.2), 'vm_led': mat('vm_led_lit', '7fe08a', 0.5, emit=2.0),
        'interior_lt': mat('fridge_lit', 'f4f7f2', 0.6, emit=0.8)}
GLARE = mat('glass_glare', 'f4fbff', 0.2, alpha=0.32)

# ================================================================ transform stack, mesh groups
I4 = Matrix.Identity(4)
def T(x, y, z): return Matrix.Translation((x, y, z))
def Rx(d): return Matrix.Rotation(math.radians(d), 4, 'X')
def Ry(d): return Matrix.Rotation(math.radians(d), 4, 'Y')
def Rz(d): return Matrix.Rotation(math.radians(d), 4, 'Z')
def Sc(x, y, z): return Matrix.Diagonal((x, y, z, 1))
FPX = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # text/plate local XY plane -> faces +X (reads along +Y)
CUR = [I4]
class at:
    def __init__(s, m): s.m = m
    def __enter__(s): CUR.append(CUR[-1] @ s.m)
    def __exit__(s, *a): CUR.pop()

class Grp:
    def __init__(s, name): s.name, s.bm, s.mats = name, bmesh.new(), []
    def mi(s, m):
        if m not in s.mats: s.mats.append(m)
        return s.mats.index(m)
GROUPS = {}
G = None
def group(name):
    global G
    G = GROUPS.setdefault(name, Grp(name)); return G

def put(bm, mats, Mx=None, smooth=True):
    """Merge a temp bmesh into the current group. mats: one material/name or a list indexed by face.material_index."""
    if not isinstance(mats, (list, tuple)): mats = [mats]
    mats = [M(m) if isinstance(m, str) else m for m in mats]
    W = CUR[-1] @ (Mx if Mx is not None else I4)
    bmesh.ops.transform(bm, matrix=W, verts=bm.verts)
    if W.to_3x3().determinant() < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    idx = [G.mi(m) for m in mats]
    bm.verts.index_update()
    vs = [G.bm.verts.new(v.co) for v in bm.verts]
    for f in bm.faces:
        try: nf = G.bm.faces.new([vs[v.index] for v in f.verts])
        except ValueError: continue
        nf.material_index = idx[min(f.material_index, len(idx) - 1)]
        nf.smooth = f.smooth if smooth is None else smooth
    bm.free()

def bevel(bm, w, seg=2, ang=30):
    es = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(ang)]
    if es and w > 0:
        bmesh.ops.bevel(bm, geom=es, offset=w, offset_type='OFFSET', segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)

# ================================================================ primitives
def cube_bm(sx, sy, sz, bev=0.012, seg=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    t = min(sx, sy, sz)
    if bev and t >= 0.006: bevel(bm, min(bev, 0.42 * t), seg if t >= 0.05 else 1)
    return bm
def cbox(cx, cy, cz, sx, sy, sz, m, bev=0.012, seg=2, Mx=None):
    put(cube_bm(sx, sy, sz, bev, seg), m, T(cx, cy, cz) @ (Mx if Mx is not None else I4))
def box(x0, x1, y0, y1, z0, z1, m, bev=0.012, seg=2, Mx=None):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    cbox((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0, m, bev, seg, Mx)
AX = {'Z': I4, 'X': Ry(90), 'Y': Rx(-90)}
def cyl_bm(r, h, segs=12, r2=None, bev=0.0, bseg=1):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
    if bev: bevel(bm, bev, bseg, 40)
    return bm
def cyl(x, y, z, r, h, m, axis='Z', segs=12, r2=None, bev=0.0, bseg=1, Mx=None):
    put(cyl_bm(r, h, segs, r2, bev, bseg), m, T(x, y, z) @ (Mx if Mx is not None else I4) @ AX[axis])
def sphere(x, y, z, rx, ry, rz, m, u=12, v=8, Mx=None, smooth=True):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    put(bm, m, T(x, y, z) @ (Mx if Mx is not None else I4) @ Sc(rx, ry, rz), smooth)
def ico(x, y, z, r, m, sub=1, sq=(1, 1, 1), Mx=None, jitter=0.0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    if jitter:
        for v in bm.verts: v.co *= 1 + RND.uniform(-jitter, jitter)
    put(bm, m, T(x, y, z) @ (Mx if Mx is not None else I4) @ Sc(*sq), smooth=False)

def lathe_bm(prof, segs=12, mats=None, cap=True):
    """prof: [(r, z)...]; r=0 gives a pole vertex. mats: material index per band (len(prof)-1)."""
    bm = bmesh.new(); rings = []
    for r, z in prof:
        if r < 1e-6: rings.append([bm.verts.new((0, 0, z))])
        else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(segs):
            j = (i + 1) % segs
            try:
                if len(a) == 1 and len(b) == 1: continue
                if len(a) == 1: f = bm.faces.new((a[0], b[j], b[i]))
                elif len(b) == 1: f = bm.faces.new((a[i], a[j], b[0]))
                else: f = bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError: continue
            f.material_index = mats[k] if mats else 0
    if cap:
        up = prof[1][1] >= prof[0][1]
        if len(rings[0]) > 2:
            f = bm.faces.new(list(reversed(rings[0])) if up else rings[0]); f.material_index = mats[0] if mats else 0
        upl = prof[-1][1] >= prof[-2][1]
        if len(rings[-1]) > 2:
            f = bm.faces.new(rings[-1] if upl else list(reversed(rings[-1]))); f.material_index = mats[-1] if mats else 0
    return bm
def lathe(prof, m, Mx=None, segs=12, mats_idx=None, cap=True, smooth=True):
    put(lathe_bm(prof, segs, mats_idx, cap), m, Mx, smooth)

def tube_bm(pts, r, sides=6, radii=None, caps=True):
    pts = [Vector(p) for p in pts]; n = len(pts); bm = bmesh.new(); rings = []
    tan = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    up = Vector((0, 0, 1)) if abs(tan[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = tan[0].cross(up).normalized()
    for i in range(n):
        if i > 0:
            ax = tan[i - 1].cross(tan[i])
            if ax.length > 1e-6: nrm = Matrix.Rotation(tan[i - 1].angle(tan[i]), 3, ax.normalized()) @ nrm
        b = tan[i].cross(nrm); rr = radii[i] if radii else r
        rings.append([bm.verts.new(pts[i] + (nrm * math.cos(a) + b * math.sin(a)) * rr) for a in [2 * math.pi * k / sides for k in range(sides)]])
    for i in range(n - 1):
        for k in range(sides):
            k1 = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k]))
    if caps:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    return bm
def tube(pts, r, m, sides=6, radii=None, caps=True, Mx=None):
    put(tube_bm(pts, r, sides, radii, caps), m, Mx)

def spline(ctrl, per=6, closed=False):
    P = [Vector(p) for p in ctrl]; out = []
    n = len(P); rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if closed else P[max(i - 1, 0)]; p1 = P[i]; p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed else P[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed: out.append(P[-1])
    else: out.append(out[0].copy())
    return out
def sag(p0, p1, drop, n=12):
    p0, p1 = Vector(p0), Vector(p1)
    return [p0.lerp(p1, i / n) - Vector((0, 0, drop * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
def circle(r, n=24, z=0.0):
    return [Vector((r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z)) for i in range(n + 1)]

def sheet_bm(rows, thick=0.0):
    """rows: 2D list of points (grid). Quads between them; optional solidify."""
    bm = bmesh.new(); V = [[bm.verts.new(p) for p in row] for row in rows]
    for j in range(len(V) - 1):
        for i in range(len(V[0]) - 1):
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    if thick: bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
    return bm

def poly_bm(pts, thick=0.004):
    bm = bmesh.new(); f = bm.faces.new([bm.verts.new(p) for p in pts])
    if thick: bmesh.ops.solidify(bm, geom=[f], thickness=thick)
    return bm

def lattice_bm(w, h, nu, nv, frame=0.03, bar=0.025, t=0.012):
    """Panel in local XZ (x 0..w, z 0..h) with nu x nv real rectangular holes; thickness along Y."""
    hw = (w - 2 * frame - (nu - 1) * bar) / nu; hh = (h - 2 * frame - (nv - 1) * bar) / nv
    def edges(n, f, hole, b):
        e = [0, f]
        for i in range(n):
            e.append(e[-1] + hole)
            if i < n - 1: e.append(e[-1] + b)
        e.append(e[-1] + f); return e
    xs = edges(nu, frame, hw, bar); zs = edges(nv, frame, hh, bar)
    bm = bmesh.new(); V = [[bm.verts.new((x, 0, z)) for x in xs] for z in zs]
    for j in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            if i % 2 == 1 and j % 2 == 1: continue
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=t)
    return bm

def text(s, Mx, size, m, extrude=0.0, fitw=None, align='CENTER', spacing=1.0):
    """Text in local XY (reads +X, up +Y, faces +Z), placed by Mx in the current frame."""
    if FONT is None: return
    cu = bpy.data.curves.new('t', 'FONT'); cu.body = s; cu.font = FONT; cu.size = size; cu.extrude = extrude
    cu.resolution_u = 2; cu.align_x = align; cu.align_y = 'CENTER'; cu.space_character = spacing; cu.space_line = 1.05
    ob = bpy.data.objects.new('t', cu); scn.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(C.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me); bm.normal_update()
    if extrude:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.5], context='FACES')
        for v in bm.verts: v.co.z += extrude
    if fitw:
        xs = [v.co.x for v in bm.verts]
        if xs and max(xs) - min(xs) > fitw:
            k = fitw / (max(xs) - min(xs))
            for v in bm.verts: v.co.x *= k; v.co.y *= k
    put(bm, m, Mx, smooth=False)

# ================================================================ reusable props
def fish(L, H, W, kind, Mx):
    """Stylised fish lying on its side. Local: length +X (head), placed so it rests on z=0 plane."""
    P = {'mack': ('mack_back', 'mack_belly', 'fin_grey', 'mack_str'), 'snap': ('snap_back', 'snap_belly', 'snap_fin', None),
         'aji': ('aji_back', 'aji_belly', 'fin_grey', None), 'buri': ('buri_back', 'buri_belly', 'fin_grey', 'buri_line')}[kind]
    prof = [(0.0, 0.17, 0.3), (0.1, 0.3, 0.45), (0.25, 0.64, 0.75), (0.45, 0.95, 1.0), (0.62, 1.0, 1.0), (0.78, 0.86, 0.9),
            (0.9, 0.58, 0.66), (0.97, 0.28, 0.36), (1.0, 0.0, 0.0)]
    seg = 10; bm = bmesh.new(); rings = []
    for t, hf, wf in prof:
        x = t * L
        if hf == 0: rings.append([bm.verts.new((x, 0, 0))]); continue
        rings.append([bm.verts.new((x, W / 2 * wf * math.cos(2 * math.pi * i / seg), H / 2 * hf * math.sin(2 * math.pi * i / seg))) for i in range(seg)])
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            f = bm.faces.new((a[i], b[0], a[j])) if len(b) == 1 else bm.faces.new((a[i], b[i], b[j], a[j]))
    bm.faces.new(rings[0])
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median(); f.material_index = 1
        if c.z > 0.08 * H: f.material_index = 0
        if P[3] and kind == 'mack' and c.z > 0.16 * H and c.x < 0.82 * L and int(c.x / L * 15 + c.z / H * 5) % 2 == 0: f.material_index = 3
        if P[3] and kind == 'buri' and abs(c.z) < 0.09 * H and 0.1 * L < c.x < 0.85 * L: f.material_index = 3
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])        # loft winding is inward; flip once
    lie = Mx @ Rx(90)                            # lateral +Y becomes up: the fish lies on its side, eye side up
    with at(lie):
        put(bm, [P[0], P[1], P[2], P[3] or P[0]], T(0, 0, 0))
        put(poly_bm([(0.03 * L, 0, 0.1 * H), (-0.2 * L, 0, 0.5 * H), (-0.12 * L, 0, 0), (-0.2 * L, 0, -0.5 * H), (0.03 * L, 0, -0.1 * H)], 0.006), P[2], T(0, 0.003, 0), smooth=False)
        put(poly_bm([(0.36 * L, 0, 0.4 * H), (0.62 * L, 0, 0.42 * H), (0.42 * L, 0, 0.66 * H)], 0.005), P[2], T(0, 0.0025, 0), smooth=False)
        put(poly_bm([(0.74 * L, 0, -0.05 * H), (0.62 * L, 0, -0.2 * H), (0.6 * L, 0, -0.05 * H)], 0.004), P[2], T(0, 0.32 * W, 0), smooth=False)
        er = 0.085 * H
        for s in (1, -1):
            sphere(0.87 * L, s * 0.31 * W, 0.12 * H, er, er * 0.6, er, 'eye_w', 8, 5)
            sphere(0.875 * L, s * (0.31 * W + er * 0.45), 0.12 * H, er * 0.55, er * 0.4, er * 0.55, 'black', 6, 3)
        # gill line
        tube([(0.76 * L, 0.3 * W * 1.05, 0.25 * H), (0.735 * L, 0.36 * W, 0.0), (0.76 * L, 0.3 * W, -0.22 * H)], 0.004, P[0], 4)

def squid(L, Mx):
    """Squid lying flat: mantle along +X toward the tail fins at x=0, tentacles beyond L*0.62."""
    with at(Mx):
        R = 0.13 * L
        prof = [(0, 0), (0.25 * R, 0.04 * L), (0.6 * R, 0.14 * L), (0.95 * R, 0.32 * L), (R, 0.5 * L), (0.85 * R, 0.6 * L), (0.0, 0.6 * L)]
        bm = lathe_bm(prof, 10, cap=False)
        for f in bm.faces:
            c = f.calc_center_median(); f.material_index = 1 if c.x < -0.45 * R and c.z > 0.08 * L else 0
        put(bm, ['squid', 'squid_dk'], Ry(90) @ Sc(0.72, 1, 1))
        fin = [(0.0, 0, 0), (0.12 * L, 0.24 * L * 0.62, 0), (0.24 * L, 0, 0), (0.12 * L, -0.24 * L * 0.62, 0)]
        put(poly_bm(fin, 0.006), 'squid_dk', T(0.0, 0, 0.0), smooth=False)
        sphere(0.66 * L, 0, 0, 0.07 * L, 0.6 * R, 0.5 * R, 'squid', 10, 6)
        for s in (1, -1):
            sphere(0.67 * L, s * 0.55 * R, 0.12 * R, 0.03 * L, 0.022 * L, 0.03 * L, 'eye_w', 6, 4)
            sphere(0.675 * L, s * 0.62 * R, 0.14 * R, 0.018 * L, 0.014 * L, 0.018 * L, 'black', 6, 3)
        for k in range(8):
            a = (k - 3.5) / 3.5
            ln = 0.42 * L if k in (2, 5) else 0.3 * L
            pts = [(0.7 * L, a * 0.3 * R, 0), (0.7 * L + ln * 0.4, a * 0.55 * R, -0.01 * L), (0.7 * L + ln * 0.75, a * 0.9 * R + 0.03 * L * math.sin(k), -0.02 * L),
                   (0.7 * L + ln, a * 1.1 * R + 0.05 * L * math.cos(k * 1.7), -0.022 * L)]
            pts = spline(pts, 3)
            tube(pts, 0, 'squid' if k % 2 else 'squid_dk', 5, [0.03 * L * (1 - 0.75 * i / (len(pts) - 1)) for i in range(len(pts))])

def octopus(s, Mx):
    with at(Mx @ Sc(s, s, s)):
        sphere(-0.03, 0, 0.13, 0.11, 0.095, 0.12, 'octo', 14, 10, Ry(-25))
        sphere(0.05, 0, 0.05, 0.1, 0.1, 0.06, 'octo', 12, 6)
        for sd in (1, -1):
            sphere(0.085, sd * 0.045, 0.1, 0.022, 0.022, 0.026, 'octo_lt', 8, 6)
            box(0.104, 0.11, sd * 0.045 - 0.012, sd * 0.045 + 0.012, 0.096, 0.104, 'black', 0.002, 1)
        for k in range(8):
            a0 = math.radians(k * 45 + 10); pts = []
            for i in range(14):
                t = i / 13; r = 0.07 + 0.26 * t ** 0.9; a = a0 + 0.9 * t ** 2.2 * (1 if k % 2 else -1)
                if t > 0.75: r -= (t - 0.75) * 0.5
                pts.append((0.05 + r * math.cos(a), r * math.sin(a), 0.035 * (1 - t) + 0.012))
            rad = [0.034 * (1 - 0.82 * i / 13) for i in range(14)]
            tube(pts, 0, 'octo', 6, rad)
            for i in range(2, 12, 2):   # pale suckers along each arm
                p = Vector(pts[i]); sphere(p.x, p.y, p.z - rad[i] * 0.55, rad[i] * 0.45, rad[i] * 0.45, rad[i] * 0.3, 'octo_lt', 5, 3)

def prawn(Mx):
    with at(Mx):
        segs = 6
        for i in range(segs):
            a = math.radians(-80 + i * 30); r = 0.045
            x, z = r * math.cos(a), r * math.sin(a) + 0.045
            rr = 0.019 - i * 0.0018
            sphere(x, 0, z * 0.6 + 0.012, rr * 1.15, rr, rr * 0.95, 'prawn' if i % 2 == 0 else 'prawn_lt', 7, 5, Ry(-math.degrees(a)))
        sphere(0.05, 0, 0.015, 0.03, 0.017, 0.016, 'prawn', 8, 6, Ry(10))   # head
        for s in (1, -1):
            put(poly_bm([(0, 0, 0), (0.025, s * 0.012, 0), (0.02, s * 0.026, 0)], 0.003), 'prawn_lt', T(0.005, 0, 0.065), smooth=False)
            tube(spline([(0.075, s * 0.006, 0.018), (0.11, s * 0.02, 0.03), (0.15, s * 0.05, 0.02)], 3), 0.0016, 'prawn', 3)
            sphere(0.072, s * 0.01, 0.024, 0.004, 0.004, 0.004, 'black', 4, 3)

def scallop(Mx):
    with at(Mx):
        R = 0.085; na, nr = 14, 5; rows = []
        for j in range(nr + 1):
            r = R * j / nr; row = []
            for i in range(na + 1):
                a = math.radians(-75 + 150 * i / na)
                rib = 0.004 * math.cos(a * 22) * (j / nr)
                row.append((r * math.cos(a) * 1.0 - 0.03, r * math.sin(a), 0.035 * (j / nr) ** 2 + rib + 0.004))
            rows.append(row)
        bm = sheet_bm(rows, 0.005)
        put(bm, 'shell', None, smooth=True)
        box(-0.045, -0.025, -0.022, 0.022, 0.0, 0.006, 'shell', 0.002, 1)
        cyl(0.004, 0, 0.018, 0.026, 0.016, 'scal_meat', 'Z', 12, bev=0.005)
        sphere(0.022, 0.016, 0.017, 0.016, 0.011, 0.008, 'scal_roe', 8, 5, Rz(-40))

def ice_bed(x0, x1, y0, y1, z, amp=0.022, step=0.055):
    nx = max(2, int((x1 - x0) / step)); ny = max(2, int((y1 - y0) / step)); rows = []
    for j in range(ny + 1):
        rows.append([(x0 + (x1 - x0) * i / nx + RND.uniform(-0.25, 0.25) * step * (0 < i < nx),
                      y0 + (y1 - y0) * j / ny + RND.uniform(-0.25, 0.25) * step * (0 < j < ny),
                      z + RND.uniform(0, amp)) for i in range(nx + 1)])
    bm = sheet_bm(rows)
    for f in bm.faces: f.material_index = 1 if RND.random() < 0.28 else 0; f.smooth = False
    put(bm, ['ice', 'ice2'], None, smooth=False)
    for _ in range(int((x1 - x0) * (y1 - y0) * 22)):
        ico(RND.uniform(x0, x1), RND.uniform(y0, y1), z + amp * 0.8, RND.uniform(0.012, 0.022), 'ice', 1, (1, 1, 0.7), jitter=0.2)

def styro_box(cx, cy, z0, lx, ly, h, wall=0.028, label=True):
    with at(T(cx, cy, z0)):
        box(-lx / 2, lx / 2, -ly / 2, ly / 2, 0, 0.03, 'styro', 0.01)
        for s in (1, -1):
            box(s * (lx / 2 - wall), s * lx / 2, -ly / 2, ly / 2, 0, h, 'styro', 0.012)
            box(-lx / 2 + wall, lx / 2 - wall, s * (ly / 2 - wall), s * ly / 2, 0, h, 'styro', 0.012)
        if label:   # printed blue stamp on the street side
            box(lx / 2, lx / 2 + 0.003, -ly * 0.18, ly * 0.18, h * 0.3, h * 0.7, 'styro_lbl', 0.0)

def crate(cx, cy, z0, lx, ly, h, col, nl=6, ns=4, nv=2, Mx=None, floor=True):
    t = 0.014
    with at(T(cx, cy, z0) @ (Mx if Mx is not None else I4)):
        if floor: box(-lx / 2 + 0.01, lx / 2 - 0.01, -ly / 2 + 0.01, ly / 2 - 0.01, 0, 0.016, col, 0.005, 1)
        hb = h - 0.035
        for s in (1, -1):
            put(lattice_bm(ly - 0.04, hb, nl, nv, 0.028, 0.022, t), col, T(s * (lx / 2 - t / 2) + (t / 2), -ly / 2 + 0.02, 0.0) @ Rz(90), smooth=False)
            put(lattice_bm(lx - 0.04, hb, ns, nv, 0.028, 0.022, t), col, T(-lx / 2 + 0.02, s * (ly / 2 - t / 2) - t / 2, 0.0), smooth=False)
        for s in (1, -1):    # thick top rim and corner posts
            box(s * lx / 2 - s * 0.022, s * lx / 2, -ly / 2, ly / 2, hb - 0.004, h, col, 0.008, 1)
            box(-lx / 2, lx / 2, s * ly / 2 - s * 0.022, s * ly / 2, hb - 0.004, h, col, 0.008, 1)
            for s2 in (1, -1): box(s * lx / 2 - s * 0.03, s * lx / 2, s2 * ly / 2 - s2 * 0.03, s2 * ly / 2, 0, h, col, 0.008, 1)

def baran(x0, x1, y, z, n=8, h=0.05):
    """Green zig-zag 'baran' grass divider strip standing along X at y."""
    pts = []
    for i in range(2 * n + 1):
        pts.append((x0 + (x1 - x0) * i / (2 * n), y, z + (h if i % 2 else h * 0.35)))
    pts = [(x1, y, z), (x0, y, z)] + pts[0:]
    rows = [[(p[0], p[1], z) for p in pts[2:]], [p for p in pts[2:]]]
    put(sheet_bm(rows, 0.003), 'baran', None, smooth=False)

def leaf_flat(Mx, L, W):
    """A flat decorative leaf (haran) with a raised midrib, lying on the ice."""
    with at(Mx):
        n = 8; rows = []
        for i in range(n + 1):
            t = i / n; x = (t - 0.5) * L; w = W / 2 * math.sin(math.pi * t) ** 0.8
            rows.append([(x, -w, 0.004 * math.sin(math.pi * t)), (x, 0, 0.012 * math.sin(math.pi * t)), (x, w, 0.004 * math.sin(math.pi * t))])
        put(sheet_bm(list(map(list, zip(*rows))), 0.003), 'baran', None, smooth=True)

def price_card(x, y, z, name, price, h=0.2, tilt=-14, yaw=0, col='red'):
    with at(T(x, y, z) @ Rz(yaw)):
        cyl(0, 0, h / 2, 0.0035, h, 'wood_pale', 'Z', 5)
        with at(T(0.006, 0, h + 0.035) @ Ry(tilt)):
            box(-0.003, 0.003, -0.07, 0.07, -0.045, 0.045, 'paper', 0.003, 1)
            box(0.003, 0.0045, -0.07, 0.07, 0.026, 0.045, col, 0, 1)
            text(name, T(0.0048, 0, 0.003) @ FPX, 0.026, 'ink', fitw=0.12)
            text(price, T(0.0048, 0, -0.026) @ FPX, 0.032, col, fitw=0.125)

def fan(Mx, r=0.16, base='wall'):
    """Electric fan blowing along local +X with a wire cage."""
    with at(Mx):
        if base == 'wall':
            box(-0.16, -0.14, -0.06, 0.06, -0.08, 0.08, 'white', 0.01)
            tube([(-0.14, 0, 0), (-0.1, 0, -0.02), (-0.08, 0, 0)], 0.018, 'white', 8)
        lathe([(0, -0.1), (0.05, -0.095), (0.065, -0.06), (0.06, -0.02), (0.035, 0.0), (0, 0.005)], 'white', Ry(90), 12)
        cyl(0.02, 0, 0, 0.028, 0.03, 'grey_lt', 'X', 10)
        for k in range(3):
            put(cube_bm(0.008, r * 0.42, r * 0.85, 0.004, 1), mat('fan_blade', 'a9d3ea', 0.6), T(0.02, 0, 0) @ Rx(k * 120 + 15) @ T(0, 0, r * 0.47) @ Ry(18))
        for rx_, rr in ((0.06, r), (0.07, r * 0.66), (0.075, r * 0.33), (-0.03, r)):
            tube([(rx_, p.x, p.y) for p in circle(rr, 28)], 0.0035, 'white', 4, caps=False)
        for k in range(10):
            a = 2 * math.pi * k / 10; ca, sa = math.cos(a), math.sin(a)
            tube([(0.075, 0.03 * ca, 0.03 * sa), (0.065, r * 0.7 * ca, r * 0.7 * sa), (0.04, r * ca, r * sa), (-0.03, r * ca, r * sa), (-0.06, 0.05 * ca, 0.05 * sa)], 0.0025, 'white', 3, caps=False)
        cyl(0.08, 0, 0, 0.03, 0.01, 'stripe_a', 'X', 12, bev=0.003)

def bottle(kind, Mx):
    """PET bottle or can. Material bands: body / label / cap."""
    col = {'g': 'drink_g', 'w': 'drink_w', 'o': 'drink_o', 'br': 'drink_br', 'bl': 'drink_bl', 'rd': 'drink_rd'}[kind]
    if kind == 'br':  # coffee can
        prof = [(0, 0), (0.021, 0), (0.023, 0.006), (0.023, 0.08), (0.019, 0.088), (0, 0.088)]
        lathe(prof, [col, 'drink_lbl', 'steel'], Mx, 10, [0, 0, 1, 2, 2]); return
    prof = [(0, 0), (0.02, 0.0), (0.023, 0.006), (0.023, 0.03), (0.023, 0.068), (0.021, 0.085), (0.011, 0.105), (0.009, 0.108), (0.009, 0.122), (0, 0.122)]
    lathe(prof, [col, 'drink_lbl', 'drink_cap'], Mx, 10, [0, 0, 0, 1, 0, 0, 2, 2, 2])

def pot_plant(x, y, kind, s=1.0):
    with at(T(x, y, 0) @ Sc(s, s, s)):
        pc = 'pot' if kind == 'bush' else 'pot_blue'
        lathe([(0, 0), (0.12, 0), (0.15, 0.24), (0.175, 0.25), (0.178, 0.3), (0.16, 0.3), (0.15, 0.27), (0, 0.27)], pc, None, 16)
        cyl(0, 0, 0.275, 0.15, 0.01, 'soil', 'Z', 14)
        if kind == 'bush':
            for i in range(9):
                a = i * 2.4; rr = 0.08 + 0.05 * (i % 3)
                ico(rr * math.cos(a) * 0.9, rr * math.sin(a) * 0.9, 0.37 + 0.06 * (i % 4) + 0.02 * i / 9, 0.1 + 0.02 * (i % 2), ['leaf', 'leaf2', 'leaf3'][i % 3], 1, jitter=0.12)
            for i in range(5):
                a = i * 1.3; ico(0.11 * math.cos(a), 0.11 * math.sin(a), 0.5, 0.024, 'bun_p' if i % 2 else 'bun_w', 1)
        else:   # spiky leaves (snake plant style)
            for i in range(9):
                a = i * 2.39; lean = 0.05 + 0.05 * (i % 3); hgt = 0.45 + 0.12 * ((i * 7) % 4) / 3
                pts = [(0.03 * math.cos(a), 0.03 * math.sin(a), 0.27), (lean * math.cos(a), lean * math.sin(a), 0.27 + hgt * 0.5),
                       (lean * 1.6 * math.cos(a), lean * 1.6 * math.sin(a), 0.27 + hgt)]
                pts = spline(pts, 3); n = len(pts)
                rows = []
                for j, p in enumerate(pts):
                    w = 0.035 * (1 - j / (n - 1)) + 0.002
                    d = Vector((-math.sin(a), math.cos(a), 0)) * w
                    rows.append([Vector(p) - d, Vector(p) + Vector((math.cos(a), math.sin(a), 0)) * 0.012, Vector(p) + d])
                put(sheet_bm(rows, 0.004), ['leaf', 'leaf2', 'leaf3'][i % 3], None, smooth=False)

def lantern(x, y, ztop, txt='魚'):
    with at(T(x, y, ztop)):
        cyl(0, 0, -0.025, 0.07, 0.05, 'black', 'Z', 14, bev=0.008)
        prof = []
        n = 14
        for i in range(n + 1):
            th = math.radians(-74 + 148 * i / n)
            r = 0.155 * math.cos(th) * (1.0 if i % 2 == 0 else 0.955)
            prof.append((r, -0.25 + 0.2 * math.sin(th)))
        lathe(prof, 'lantern', None, 18, cap=False)
        cyl(0, 0, -0.455, 0.07, 0.05, 'black', 'Z', 14, bev=0.008)
        tube([(0, 0, 0.0), (0, 0, 0.08)], 0.004, 'black', 4)
        text(txt, T(0.158, 0, -0.25) @ FPX, 0.13, 'ink', 0.004)
        for k in range(5):
            tube([(0.0 + 0.012 * math.cos(k), 0.012 * math.sin(k), -0.48), (0.015 * math.cos(k), 0.015 * math.sin(k), -0.56)], 0.004, 'yellow', 3)

def bunting(pts, phase=0):
    P = [Vector(p) for p in pts]
    tube(P, 0.004, 'rope', 4, caps=False)
    cols = ['bun_r', 'bun_y', 'bun_b', 'bun_w', 'bun_g', 'bun_p']
    seglen = [(P[i + 1] - P[i]).length for i in range(len(P) - 1)]; tot = sum(seglen)
    def at_d(d):
        for i, l in enumerate(seglen):
            if d <= l: return P[i].lerp(P[i + 1], d / l)
            d -= l
        return P[-1]
    d = 0.08; k = phase
    while d + 0.16 < tot:
        a = at_d(d); b = at_d(d + 0.16); mid = (a + b) / 2 - Vector((0, 0, 0.19))
        put(poly_bm([a, mid, b], 0.003), cols[k % len(cols)], None, smooth=False)
        d += 0.24; k += 1

# ================================================================ the stall
CZ_B, CZ_F, CX_B, CX_F = 2.80, 2.44, -2.05, 0.45
SLOPE = math.degrees(math.atan2(CZ_B - CZ_F, CX_F - CX_B))
def zc(x): return CZ_B + (x - CX_B) * (CZ_F - CZ_B) / (CX_F - CX_B)
RAFT_Y = (-2.2, -0.733, 0.733, 2.2)

group('Stall_Frame')
for px in (-0.05, -2.02):
    for py in (-2.2, 2.2):
        top = zc(px) - 0.04
        box(px - 0.03, px + 0.03, py - 0.03, py + 0.03, 0, top, 'frame', 0.012)
        box(px - 0.06, px + 0.06, py - 0.06, py + 0.06, 0, 0.015, 'frame_dk', 0.005, 1)
for py in RAFT_Y:
    mx = (CX_B + CX_F) / 2
    cbox(mx, py, zc(mx) - 0.035, CX_F - CX_B + 0.04, 0.035, 0.045, 'frame', 0.01, 1, Ry(SLOPE))
for px in (-0.05, -2.02, CX_F - 0.02):
    box(px - 0.025, px + 0.025, -2.24, 2.24, zc(px) - 0.1, zc(px) - 0.05, 'frame', 0.01, 1)
for py in (-2.2, 2.2):   # side rails and knee braces
    box(-2.02, -0.05, py - 0.02, py + 0.02, 1.32, 1.36, 'frame', 0.008, 1)
    for px, sg in ((-0.05, -1), (-2.02, 1)):
        p0 = Vector((px, py, zc(px) - 0.45)); p1 = Vector((px + sg * 0.4, py, zc(px + sg * 0.4) - 0.07))
        tube([p0, p1], 0.014, 'frame', 6)
box(-0.87, -0.83, -2.2, 2.2, zc(-0.85) - 0.1, zc(-0.85) - 0.065, 'frame', 0.01, 1)   # hanging bar
for py in (-2.0, -1.0, 0.0, 1.0, 2.0):   # rope ties along the back
    tube([(-2.02, py, zc(-2.02) - 0.1), (-2.0, py, zc(-2.02) - 0.16)], 0.006, 'rope', 4)

group('Stall_Canopy')
NSTR = 12; SW = 4.5 / NSTR
for i in range(NSTR):
    ya = -2.25 + i * SW; rows = []
    for jx in range(11):
        x = CX_B - 0.02 + (CX_F + 0.04 - CX_B) * jx / 10; row = []
        for jy in range(5):
            y = ya + SW * jy / 4
            fr = ((y + 2.2) % 1.4665) / 1.4665
            sagv = 0.065 * math.sin(math.pi * fr) * (0.35 + 0.65 * math.sin(math.pi * jx / 10) ** 0.5)
            row.append((x, y, zc(x) + 0.01 - sagv + 0.012 * math.sin(math.pi * jy / 4)))
        rows.append(row)
    put(sheet_bm(rows, 0.014), 'stripe_a' if i % 2 == 0 else 'stripe_b', None)

def valance(p0, axis, length, ztop_fn, n, depth, out):
    """Pleated scalloped valance. p0: start point, axis: unit run direction, out: outward normal."""
    p0, axis, out = Vector(p0), Vector(axis), Vector(out); w = length / n
    for i in range(n):
        rows = []
        for r in range(4):
            v = r / 3; row = []
            for c in range(9):
                u = c / 8; s = i * w + u * w; p = p0 + axis * s
                d = depth * (0.5 + 0.5 * math.sin(math.pi * u) ** 0.6)     # rounded tongue per stripe
                bul = 0.035 * math.sin(math.pi * u) * (0.3 + 0.7 * v) + 0.008 * math.sin(4 * math.pi * u) * v
                row.append(p + out * bul + Vector((0, 0, ztop_fn(p) - v * d - p.z)))
            rows.append(row)
        put(sheet_bm(rows, 0.008), 'stripe_a' if i % 2 == 0 else 'stripe_b', None)
    q0 = p0 + out * 0.01; q1 = p0 + axis * length + out * 0.01
    tube([Vector((q.x, q.y, ztop_fn(q) + 0.005)) for q in (q0, q1)], 0.014, 'pipe_white', 8)
VD = 0.24
valance((CX_F + 0.02, -2.25, 0), (0, 1, 0), 4.5, lambda p: zc(CX_F), NSTR, VD, (1, 0, 0))
for sy in (-1, 1):
    valance((CX_B, sy * 2.26, 0), (1, 0, 0), CX_F + 0.02 - CX_B, lambda p: zc(p.x), 6, VD * 0.8, (0, sy, 0))

group('Stall_Lights')
RAIL_X, RAIL_Z = 0.22, zc(0.22) - 0.13
box(RAIL_X - 0.02, RAIL_X + 0.02, -2.0, 2.0, RAIL_Z - 0.02, RAIL_Z + 0.02, 'black', 0.008, 1)
for py in (-1.9, 0.0, 1.9): tube([(RAIL_X, py, RAIL_Z), (RAIL_X, py, zc(RAIL_X) - 0.03)], 0.007, 'black', 5)
for py in (-1.5, -0.5, 0.5, 1.5):
    pos = Vector((RAIL_X + 0.02, py, RAIL_Z - 0.22)); tgt = Vector((-0.7, py * 0.8, 0.95))
    tube([(RAIL_X, py, RAIL_Z), pos + Vector((0, 0, 0.05))], 0.008, 'black', 5)
    for s in (-1, 1): tube([pos + Vector((0, s * 0.055, 0.05)), pos + Vector((0, s * 0.055, -0.01))], 0.006, 'black', 4)
    tube([pos + Vector((0, -0.055, 0.05)), pos + Vector((0, 0.055, 0.05))], 0.006, 'black', 4)
    rot = (tgt - pos).to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    lathe([(0, 0.13), (0.022, 0.128), (0.04, 0.11), (0.046, 0.06), (0.052, 0.0), (0.047, 0.0), (0.04, 0.02), (0, 0.02)], 'white', T(*pos) @ rot @ T(0, 0, -0.06), 14)
    cyl(0, 0, 0, 0.041, 0.006, EMIT['bulb'], 'Z', 14, Mx=T(*pos) @ rot @ T(0, 0, -0.04))

group('Stall_Counter')
box(-1.92, -0.06, -1.95, 1.95, 0, 0.09, 'plinth', 0.01)
box(-1.95, -0.035, -1.98, 1.98, 0.09, 0.70, 'wood_dk', 0.0)
k = 0
y = -2.0
while y < 1.99:   # front planks with real gaps
    w = 0.155
    box(-0.04, 0.0, y + 0.006, min(y + w, 2.0) - 0.006, 0.07, 0.69, 'wood' if k % 3 else 'wood2', 0.008, 1); y += w; k += 1
for sy in (-1, 1):
    x = -1.95; k = 0
    while x < -0.04:
        box(x + 0.006, min(x + 0.16, -0.04) - 0.006, sy * 1.98, sy * 2.02, 0.07, 0.69, 'wood2' if k % 2 else 'wood', 0.008, 1); x += 0.16; k += 1
box(-0.07, 0.035, -2.04, 2.04, 0.68, 0.74, 'wood_dk', 0.016)
box(-1.97, -0.07, -2.04, -1.98, 0.68, 0.74, 'wood_dk', 0.012); box(-1.97, -0.07, 1.98, 2.04, 0.68, 0.74, 'wood_dk', 0.012)
# tier B and C steps
box(-1.27, -0.6, -2.0, 2.0, 0.74, 0.98, 'wood2', 0.015)
box(-0.62, -0.585, -2.0, 2.0, 0.76, 0.99, 'paint_teal', 0.008, 1)
box(-1.96, -1.25, -2.0, 2.0, 0.74, 1.20, 'wood', 0.015)
box(-1.27, -1.235, -2.0, 2.0, 0.98, 1.21, 'paint_teal', 0.008, 1)
for sy in (-1, 1):
    box(-1.96, -0.6, sy * 1.98, sy * 2.02, 0.74, 0.98, 'wood_dk', 0.01, 1)
    box(-1.96, -1.25, sy * 1.98, sy * 2.02, 0.98, 1.2, 'wood_dk', 0.01, 1)
# little paper posters on the fascia
for py, col, t1 in ((-1.0, 'yellow', '特価'), (0.0, 'paper', '朝獲れ'), (1.0, 'chalk_p', '活')):
    box(-0.585, -0.582, py - 0.09, py + 0.09, 0.85, 0.99, col, 0, 1)
    text(t1, T(-0.5815, py, 0.92) @ FPX, 0.07, 'red_dk', fitw=0.15)
# tier A slanted tray
TA = T(-0.3, 0, 0.80) @ Ry(6)
box(-0.6, -0.02, -1.96, 1.96, 0.70, 0.725, 'wood_dk', 0.008, 1)
with at(TA):
    box(-0.31, 0.31, -1.98, 1.98, -0.03, 0.0, 'tray', 0.006)
    for s in (1, -1):
        box(s * 0.31, s * 0.33, -1.98, 1.98, -0.03, 0.045, 'tray', 0.008, 1)
        box(-0.33, 0.33, s * 1.98, s * 2.0, -0.03, 0.045, 'tray', 0.008, 1)
    for py in (-0.66, 0.66): box(-0.31, 0.31, py - 0.01, py + 0.01, 0.0, 0.04, 'tray', 0.005, 1)

group('Stall_Ice')
with at(TA): ice_bed(-0.3, 0.3, -1.97, 1.97, 0.005)
BOXES_B = (-1.47, -0.5, 0.47, 1.44)
for cy in BOXES_B: ice_bed(-1.21, -0.69, cy - 0.4, cy + 0.4, 1.06, 0.018)

group('Stall_Boxes')
for cy in BOXES_B: styro_box(-0.95, cy, 0.98, 0.58, 0.86, 0.2)
crate(-1.6, -1.45, 1.2, 0.62, 0.9, 0.2, 'crate_blue')
crate(-1.6, -0.45, 1.2, 0.62, 0.9, 0.2, 'crate_white')
crate(-1.6, 0.55, 1.2, 0.62, 0.9, 0.2, 'crate_blue')
crate(-1.6, 1.3, 1.2, 0.32, 0.42, 0.14, 'crate_green', 4, 3, 1)
# prawn trays
for ty in (0.28, 0.66):
    with at(T(-0.95, ty, 1.085) @ Rx(0)):
        box(-0.23, 0.23, -0.17, 0.17, 0, 0.012, 'tray_blk', 0.004, 1)
        for s in (1, -1):
            box(-0.23, 0.23, s * 0.17 - s * 0.012, s * 0.17, 0, 0.03, 'tray_blk', 0.004, 1)
            box(s * 0.23 - s * 0.012, s * 0.23, -0.17, 0.17, 0, 0.03, 'tray_blk', 0.004, 1)
# ice in the tier C crates
ice_bed(-1.88, -1.32, -1.86, -1.04, 1.32, 0.015)
ice_bed(-1.88, -1.32, 0.14, 0.96, 1.32, 0.015)
ice_bed(-1.88, -1.32, -0.86, -0.04, 1.32, 0.015)
for cy in (-1.45, -0.45, 0.55): box(-1.89, -1.31, cy - 0.43, cy + 0.43, 1.215, 1.32, 'ice2', 0)

group('Stall_Fish')
with at(TA):   # tier A: mackerel row, snapper, squid
    for i in range(7):
        y = -1.86 + i * 0.165
        fish(0.32, 0.075, 0.05, 'mack', T(-0.16, y, 0.045) @ Rz(22 + RND.uniform(-4, 4)))
    for i, y in enumerate((-0.52, -0.12, 0.28)):
        fish(0.36, 0.15, 0.06, 'snap', T(-0.17, y, 0.05) @ Rz(16 + 6 * i))
    for i, y in enumerate((-0.45, -0.05, 0.35)):
        leaf_flat(T(-0.02, y, 0.03) @ Rz(16 + 6 * i + 8), 0.42, 0.14)
    for i in range(4):
        squid(0.4, T(0.25, 0.82 + i * 0.3, 0.045) @ Rz(180 + RND.uniform(-5, 5)))
# tier B: tuna, octopus, prawns, scallops
with at(T(-0.95, -1.47, 1.09)):
    sec = [(0, 0.04), (0.045, 0.03), (0.075, -0.02), (0.06, -0.05), (-0.06, -0.05), (-0.075, -0.02), (-0.045, 0.03)]
    rings = []
    bm = bmesh.new()
    for j in range(9):
        t = j / 8; sc = 0.35 + 0.65 * math.sin(math.pi * (0.1 + 0.85 * t)) ** 0.6
        rings.append([bm.verts.new((sx * sc * 1.4, -0.36 + 0.72 * t, (sz + 0.05) * sc * 1.3)) for sx, sz in sec])
    for j in range(8):
        for i in range(7):
            f = bm.faces.new((rings[j][i], rings[j][(i + 1) % 7], rings[j + 1][(i + 1) % 7], rings[j + 1][i]))
            f.material_index = 2 if i == 0 else 0
    for rg in (rings[0], rings[-1]):
        f = bm.faces.new(rg if rg is rings[-1] else list(reversed(rg))); f.material_index = 1
    put(bm, ['tuna', 'tuna_fat', 'tuna_skin'], T(-0.07, 0.04, 0.0) @ Rz(4))
    for k2 in range(3):   # saku blocks with fat lines
        with at(T(0.15, -0.22 + k2 * 0.2, 0.0) @ Rz(-8)):
            box(-0.045, 0.045, -0.075, 0.075, 0, 0.035, 'tuna' if k2 < 2 else 'tuna_fat', 0.008, 1)
            for ln in (-0.04, 0.0, 0.04): box(-0.046, 0.046, ln - 0.004, ln + 0.004, 0.03, 0.037, 'tuna_fat' if k2 < 2 else 'tuna', 0.002, 1)
    baran(0.08, 0.22, -0.33, 0.0, 4)
for i, oy in enumerate((-0.68, -0.32)):
    octopus(0.75, T(-0.97, oy, 1.08) @ Rz(30 + i * 140))
for ty in (0.28, 0.66):
    for r_ in range(2):
        for c_ in range(3):
            prawn(T(-1.08 + c_ * 0.12, ty - 0.08 + r_ * 0.16, 1.1) @ Rz(90 + RND.uniform(-6, 6)))
for r_ in range(2):
    for c_ in range(4):
        scallop(T(-1.08 + r_ * 0.24, 1.15 + c_ * 0.19, 1.085) @ Rz(RND.uniform(-30, 30) + (0 if r_ else 180)))
# tier C crates: aji row, two buri, mackerel
for i in range(5):
    fish(0.26, 0.07, 0.045, 'aji', T(-1.7, -1.8 + i * 0.16, 1.35) @ Rz(12))
for i in range(2):
    fish(0.62, 0.17, 0.11, 'buri', T(-1.86, -0.72 + i * 0.4, 1.38) @ Rz(18 - i * 30))
for i in range(5):
    fish(0.3, 0.072, 0.05, 'mack', T(-1.75, 0.2 + i * 0.16, 1.35 + 0.01 * (i % 2)) @ Rz(-10))
for i in range(9):   # lemons in the green basket
    sphere(-1.68 + 0.08 * (i % 3), 1.18 + 0.09 * (i // 3), 1.27 + 0.02 * (i % 2), 0.04, 0.03, 0.03, 'lemon', 8, 6, Rz(RND.uniform(0, 180)))

group('Stall_Cards')
price_card(-0.07, -1.3, 0.8, 'さば', '¥280', 0.17)
price_card(-0.07, -0.1, 0.8, '真鯛', '¥650', 0.17, col='red_dk')
price_card(-0.07, 1.3, 0.8, 'いか', '¥320', 0.17)
for cy, n, p in zip(BOXES_B, ('まぐろ', 'たこ', '有頭えび', 'ほたて'), ('¥980', '¥760', '¥450', '¥150')):
    price_card(-0.68, cy + 0.25, 1.1, n, p, 0.16)
price_card(-1.29, -0.45, 1.36, 'ぶり', '¥1200', 0.16, col='red_dk')
price_card(-1.29, 1.0, 1.36, 'あじ', '¥120', 0.14)

group('Stall_Props')
# hanging scale
SX, SY = -0.85, 1.05
tube([(SX, SY, zc(SX) - 0.05), (SX, SY, 1.98)], 0.005, 'steel', 4)
with at(T(SX, SY, 1.86)):
    cyl(0, 0, 0, 0.11, 0.07, 'red', 'X', 20, bev=0.015, bseg=2)
    cyl(0.036, 0, 0, 0.088, 0.004, 'paper', 'X', 20)
    for k2 in range(12):
        a = 2 * math.pi * k2 / 12
        cbox(0.04, 0.072 * math.cos(a), 0.072 * math.sin(a), 0.003, 0.004, 0.014, 'ink', 0, 1, Rx(math.degrees(a) - 90))
    cbox(0.042, 0.02, 0.025, 0.003, 0.006, 0.07, 'red_dk', 0, 1, Rx(-40))
    cyl(0.043, 0, 0, 0.008, 0.006, 'ink', 'X', 8)
    tube([(0, 0, 0.11), (0, 0, 0.14)], 0.01, 'steel', 6)
    tube(spline([(0, 0, -0.11), (0, 0, -0.16), (0, 0.02, -0.18)], 3), 0.005, 'steel', 4)
for k2 in range(3):
    a = 2 * math.pi * k2 / 3 + 0.4
    tube([(SX, SY + 0.02, 1.68), (SX + 0.14 * math.cos(a), SY + 0.14 * math.sin(a), 1.45)], 0.0025, 'steel', 3)
lathe([(0, 1.38), (0.1, 1.39), (0.15, 1.43), (0.16, 1.45), (0.15, 1.45), (0.14, 1.43), (0.095, 1.40), (0, 1.40)], 'steel', T(SX, SY, 0), 18)
# hanging zaru basket on a coiled spring (the cash basket)
ZX, ZY = -0.85, -1.0
pts = [(ZX + 0.025 * math.cos(t * 0.9), ZY + 0.025 * math.sin(t * 0.9), zc(ZX) - 0.05 - t * 0.012) for t in range(40)]
tube(pts, 0.003, 'grey', 3, caps=False)
tube([(ZX, ZY, pts[-1][2]), (ZX, ZY, 1.86)], 0.004, 'grey', 3)
for k2 in range(3):
    a = 2 * math.pi * k2 / 3; tube([(ZX, ZY, 1.86), (ZX + 0.13 * math.cos(a), ZY + 0.13 * math.sin(a), 1.72)], 0.002, 'grey', 3)
lathe([(0, 1.6), (0.07, 1.61), (0.12, 1.66), (0.135, 1.72), (0.125, 1.72), (0.11, 1.67), (0.065, 1.625), (0, 1.62)], 'bamboo', T(ZX, ZY, 0), 16)
tube([(ZX + p.x, ZY + p.y, 1.72) for p in circle(0.135, 24)], 0.007, 'wood_pale', 5, caps=False)
for k2 in range(8):
    a = 2 * math.pi * k2 / 8; tube([(ZX, ZY, 1.605), (ZX + 0.13 * math.cos(a), ZY + 0.13 * math.sin(a), 1.72)], 0.003, 'wood2', 3)
# cash box
with at(T(-1.62, 1.75, 1.2) @ Rz(-20)):
    box(-0.11, 0.11, -0.15, 0.15, 0, 0.09, 'crate_green', 0.012)
    box(-0.115, 0.115, -0.155, 0.155, 0.09, 0.125, mat('cashbox_lid', '4c9a50'), 0.012)
    tube(spline([(0.0, -0.05, 0.125), (0.0, -0.04, 0.16), (0.0, 0.04, 0.16), (0.0, 0.05, 0.125)], 3), 0.006, 'steel', 6)
    box(0.115, 0.12, -0.02, 0.02, 0.07, 0.1, 'steel', 0.003, 1)
    cyl(0.121, 0, 0.083, 0.004, 0.003, 'ink', 'X', 6)
# radio on the top step
with at(T(-1.85, 1.52, 1.2) @ Rz(-35)):
    box(-0.05, 0.05, -0.1, 0.1, 0, 0.11, 'red', 0.015)
    cyl(0.051, -0.04, 0.055, 0.035, 0.006, 'dark', 'X', 14)
    for k2 in range(4): box(0.05, 0.055, 0.02, 0.08, 0.025 + k2 * 0.022, 0.032 + k2 * 0.022, 'white', 0, 1)
    tube([(0, 0.08, 0.11), (0, 0.12, 0.33)], 0.003, 'steel', 4)
# wall fan on the back post
fan(T(-1.98, -2.15, 2.05) @ Rz(25) @ Ry(12), 0.15)
# lanterns at the two front corners on little arms
for sy in (-1, 1):
    tube([(CX_F - 0.02, sy * 2.24, zc(CX_F) - 0.07), (CX_F - 0.02, sy * 2.45, zc(CX_F) - 0.07)], 0.012, 'frame', 6)
    lantern(CX_F - 0.02, sy * 2.45, zc(CX_F) - 0.12, '魚' if sy < 0 else '鮮')
# hose coiled on the ground, ending in a nozzle
pts = []
for k2 in range(64):
    t = k2 / 63 * 3 * 2 * math.pi; r = 0.27 - 0.012 * t / (2 * math.pi)
    pts.append((0.55 + r * math.cos(t), 1.55 + r * math.sin(t), 0.022 + 0.01 * math.sin(t * 0.5) + 0.022 * (t / (6 * math.pi))))
lead = [(0.55 + 0.27, 1.55, 0.022), (0.75, 1.15, 0.02), (0.3, 0.9, 0.02), (0.03, 0.6, 0.02)]
tube(spline(list(reversed(lead[1:])), 4)[:-1] + [Vector(p) for p in pts], 0.02, 'hose', 8)
end = Vector(pts[-1])
cyl(end.x + 0.05, end.y, end.z + 0.02, 0.022, 0.12, 'yellow', 'X', 10, bev=0.006, Mx=Rz(-30))
# rubber boots
for bx, by, rot in ((0.28, 2.0, 15), (0.42, 2.17, -10)):
    with at(T(bx, by, 0) @ Rz(rot)):
        lathe([(0.0, 0.07), (0.07, 0.07), (0.068, 0.2), (0.072, 0.4), (0.078, 0.43), (0.074, 0.44), (0.064, 0.42), (0.0, 0.42)], 'boot', None, 14)
        cyl(0, 0, 0.435, 0.077, 0.02, 'stripe_a', 'Z', 14, bev=0.005)
        sphere(0.07, 0, 0.065, 0.13, 0.07, 0.065, 'boot', 12, 8)
        box(-0.07, 0.2, -0.065, 0.065, 0, 0.03, 'boot_sole', 0.012)
# blue bucket
with at(T(0.12, 2.5, 0)):
    lathe([(0, 0.0), (0.12, 0.0), (0.15, 0.28), (0.16, 0.29), (0.155, 0.3), (0.14, 0.29), (0.11, 0.02), (0, 0.02)], 'bucket', None, 16)
    tube(spline([(0, -0.15, 0.27), (0, -0.1, 0.38), (0, 0.1, 0.38), (0, 0.15, 0.27)], 4), 0.005, 'grey', 4)
    cyl(0, 0, 0.24, 0.13, 0.01, 'ice2', 'Z', 14)
# crate stack beside the stall (pole side)
crate(-1.2, -2.6, 0.0, 0.62, 0.9, 0.24, 'crate_blue', Mx=Rz(90))
crate(-1.2, -2.6, 0.24, 0.62, 0.9, 0.24, 'crate_white', Mx=Rz(87))
styro_box(-1.18, -2.6, 0.48, 0.58, 0.86, 0.2, label=True)
box(-1.18 - 0.31, -1.18 + 0.31, -2.6 - 0.45, -2.6 + 0.45, 0.68, 0.71, 'styro', 0.01, Mx=Rz(4))
text('鮮魚', T(-1.18, -2.6, 0.712) @ Rz(90), 0.16, 'styro_lbl')
crate(-0.45, -2.62, 0.0, 0.45, 0.62, 0.2, 'crate_green', 4, 3, 1, Mx=Rz(-12))
# hand-written A-frame menu board
with at(T(0.95, -2.35, 0) @ Rz(-38)):
    for s in (1, -1):
        with at(T(s * 0.2, 0, 0) @ Ry(-s * 11)):
            for sy2 in (-1, 1): box(-0.018, 0.018, sy2 * 0.29 - 0.02, sy2 * 0.29 + 0.02, 0.0, 0.95, 'wood', 0.008, 1)
            box(-0.018, 0.018, -0.29, 0.29, 0.92, 0.96, 'wood', 0.008, 1)
            box(-0.018, 0.018, -0.29, 0.29, 0.2, 0.24, 'wood', 0.008, 1)
            box(-0.01, 0.01, -0.27, 0.27, 0.24, 0.92, 'chalk', 0.004, 1)
    with at(T(0.2, 0, 0) @ Ry(-11) @ T(0.0105, 0, 0)):
        text('本日のおすすめ', T(0, 0, 0.85) @ FPX, 0.06, 'chalk_y', fitw=0.48)
        box(0, 0.002, -0.22, 0.22, 0.795, 0.802, 'chalk_w', 0, 1)
        for i, (a_, b_) in enumerate((('まぐろ', '980'), ('真鯛', '650'), ('さば', '280'), ('ほたて', '150'))):
            text(a_, T(0, -0.22, 0.74 - i * 0.085) @ FPX, 0.05, 'chalk_w', align='LEFT')
            text(b_, T(0, 0.12, 0.74 - i * 0.085) @ FPX, 0.05, 'chalk_p')
        put(poly_bm([(0, -0.12, 0.33), (0, 0.0, 0.29), (0, 0.08, 0.33), (0, 0.13, 0.29), (0, 0.13, 0.37), (0, 0.08, 0.33), (0, 0.0, 0.37)], 0.002), 'chalk_p', None, smooth=False)
        sphere(0.002, -0.06, 0.34, 0.002, 0.01, 0.01, 'chalk_w', 6, 4)

# tall wooden notice board on the left front post, bag roll on the right one
with at(T(0.0, -2.2, 0)):
    box(0.03, 0.06, -0.12, 0.12, 1.0, 2.0, 'wood_pale', 0.012)
    box(0.06, 0.065, -0.1, 0.1, 1.06, 1.94, 'paper', 0, 1)
    text('本\n日\n入\n荷', T(0.066, 0, 1.52) @ FPX, 0.17, 'ink', 0.004)
    cyl(0.068, 0, 1.86, 0.035, 0.004, 'red', 'X', 14)
    for zz in (1.15, 1.85): box(-0.035, 0.035, -0.035, 0.035, zz - 0.02, zz + 0.02, 'frame_dk', 0.006, 1)
with at(T(0.0, 2.2, 1.55)):
    tube([(0.03, 0, 0.12), (0.12, 0, 0.12), (0.12, 0, 0.0)], 0.006, 'steel', 5)
    cyl(0.12, 0, -0.06, 0.05, 0.18, 'white', 'Y', 14, bev=0.01)
    cyl(0.12, 0, -0.06, 0.015, 0.2, 'red', 'Y', 8)
    put(sheet_bm([[(0.12 + 0.05, -0.08, -0.06), (0.12 + 0.05, 0.08, -0.06)], [(0.12 + 0.055, -0.08, -0.25), (0.12 + 0.06, 0.08, -0.25)]]), 'white', None)
# a dip net and ladle standing in the blue bucket
tube([(0.12, 2.5, 0.05), (0.2, 2.42, 0.85)], 0.008, 'wood_pale', 5)
tube([(0.2 + 0.07 * math.cos(a), 2.42 + 0.07 * math.sin(a), 0.92) for a in [i * 2 * math.pi / 16 for i in range(17)]], 0.006, 'steel', 4, caps=False)
lathe([(0, 0.82), (0.05, 0.84), (0.068, 0.92), (0, 0.92)], mat('net', '6fa7c9', 0.8), T(0.2, 2.42, 0), 10, cap=False)

group('Bunting')
POLE = Vector((0.75, -3.3, 0))
bunting(sag((POLE.x - 0.15, POLE.y, 3.55), (-2.58, 4.6, 3.4), 0.4, 26), 0)
bunting(sag((POLE.x - 0.12, POLE.y + 0.05, 2.9), (CX_F + 0.04, -2.25, zc(CX_F) - 0.02), 0.08, 6), 2)

# ================================================================ vending machines + recycle bin
def vending(yc, kind):
    red = kind == 'red'
    body = 'vm_red' if red else 'vm_white'; acc = 'vm_red_dk' if red else 'vm_blue'
    adp = 'white' if red else 'vm_lblue'; cpan = 'grey_lt' if red else 'vm_panel'
    with at(T(-1.82, yc, 0)):
        box(-0.72, -0.05, -0.44, 0.44, 0, 0.07, 'dark', 0.01)
        box(-0.76, -0.12, -0.475, 0.475, 0.06, 1.84, body, 0.04, 3)
        # front door frame around the window
        box(-0.14, 0.0, -0.475, 0.475, 0.06, 0.92, body, 0.03, 2)
        box(-0.14, 0.0, -0.475, 0.475, 1.6, 1.84, body, 0.03, 2)
        box(-0.14, 0.0, -0.475, -0.41, 0.9, 1.62, body, 0.02, 2)
        box(-0.14, 0.0, 0.19, 0.475, 0.9, 1.62, body, 0.02, 2)
        box(0.0, 0.012, -0.47, 0.47, 1.66, 1.8, acc, 0.01, 1)          # header band
        text('つめた〜い', T(0.013, -0.18, 1.73) @ FPX, 0.06, 'white', fitw=0.4)
        cyl(0.012, 0.3, 1.73, 0.05, 0.006, 'white', 'X', 16)
        text('水', T(0.016, 0.3, 1.73) @ FPX, 0.06, acc)
        # window recess with lit back, shelves, bottles, buttons
        box(-0.13, -0.12, -0.41, 0.19, 0.92, 1.6, EMIT['vm_inner'], 0)
        kinds = (['g', 'w', 'o', 'rd', 'bl', 'br'] if red else ['w', 'bl', 'g', 'br', 'o', 'w'])
        for r_ in range(3):
            z = 0.95 + r_ * 0.215
            box(-0.12, -0.02, -0.41, 0.19, z - 0.012, z, 'vm_shelf', 0.003, 1)
            for c_ in range(6):
                yy = -0.355 + c_ * 0.1
                kk = kinds[(c_ + r_ * 2) % 6]
                bottle(kk, T(-0.07, yy, z) @ Sc(1.15, 1.15, 1.15))
                box(-0.03, -0.012, yy - 0.035, yy + 0.035, z - 0.045, z - 0.012, 'white', 0.003, 1)   # price strip
                box(-0.014, -0.004, yy - 0.018, yy + 0.018, z - 0.04, z - 0.026, EMIT['vm_btn'], 0.003, 1)
        for gy, gz in ((-0.25, 1.25), (0.02, 1.4)):
            cbox(-0.004, gy, gz, 0.003, 0.05, 0.42, GLARE, 0, 1, Rx(28))
        # coin / bill panel
        box(0.0, 0.02, 0.215, 0.445, 0.97, 1.52, cpan, 0.012)
        box(0.02, 0.026, 0.24, 0.42, 1.4, 1.48, 'black', 0.004, 1)
        text('120', T(0.0265, 0.33, 1.44) @ FPX, 0.045, EMIT['vm_led'])
        box(0.02, 0.028, 0.25, 0.31, 1.3, 1.36, 'dark', 0.004, 1); box(0.027, 0.03, 0.262, 0.298, 1.325, 1.333, 'black', 0, 1)
        box(0.02, 0.026, 0.27, 0.42, 1.19, 1.24, 'dark', 0.004, 1); box(0.026, 0.029, 0.29, 0.40, 1.21, 1.22, 'black', 0, 1)
        cyl(0.025, 0.38, 1.33, 0.025, 0.012, 'vm_blue' if red else 'vm_lblue', 'X', 16, bev=0.004)
        cyl(0.03, 0.31, 1.08, 0.022, 0.03, 'steel', 'X', 12, bev=0.006)
        box(0.02, 0.03, 0.37, 0.42, 1.05, 1.1, 'yellow', 0.005, 1)
        box(0.0, 0.03, 0.24, 0.42, 0.78, 0.9, 'dark', 0.012); box(0.028, 0.032, 0.26, 0.4, 0.8, 0.86, 'black', 0, 1)
        # advert panel
        box(0.0, 0.012, -0.41, 0.18, 0.4, 0.88, adp, 0.01, 1)
        cyl(0.014, -0.12, 0.66, 0.15, 0.006, acc, 'X', 24)
        bottle('g' if red else 'bl', T(0.03, -0.12, 0.55) @ Sc(2.6, 2.6, 2.6))
        for k2, sz in enumerate((0.42, 0.6, 0.78)):
            box(0.012, 0.016, 0.06, 0.16, sz - 0.012, sz + 0.012, acc if k2 != 1 else 'yellow', 0.004, 1)
        # pickup slot with flap
        box(0.0, 0.03, -0.37, 0.15, 0.1, 0.34, 'dark', 0.015)
        box(0.025, 0.035, -0.34, 0.12, 0.13, 0.31, 'black', 0.004, 1)
        cbox(0.04, -0.11, 0.22, 0.008, 0.44, 0.17, mat('flap', '4c5560', 0.4, alpha=0.85), 0.003, 1, Ry(-8))
        box(0.03, 0.045, -0.35, 0.13, 0.11, 0.13, 'steel', 0.004, 1)
        # side stripe and top cap
        for s in (1, -1):
            box(-0.7, -0.18, s * 0.475, s * 0.481, 1.3, 1.42, 'white' if red else 'vm_blue', 0, 1)
        box(-0.78, 0.02, -0.49, 0.49, 1.84, 1.87, acc, 0.012, 1)

group('VendingMachine_Red'); vending(3.83, 'red')
group('VendingMachine_White'); vending(4.82, 'white')
group('RecycleBin')
with at(T(-2.05, 3.0, 0)):
    box(-0.2, 0.2, -0.22, 0.22, 0.0, 0.8, 'bin', 0.03, 3)
    box(-0.21, 0.21, -0.23, 0.23, 0.8, 0.86, 'vm_blue', 0.02, 2)
    for hy in (-0.1, 0.1):
        cyl(0, hy, 0.862, 0.065, 0.006, 'black', 'Z', 18)
        tube([(p.x, hy + p.y, 0.864) for p in circle(0.07, 20)], 0.008, 'white', 5, caps=False)
    box(0.2, 0.206, -0.17, 0.17, 0.45, 0.72, 'vm_blue', 0.004, 1)
    text('あきかん', T(0.207, 0, 0.66) @ FPX, 0.05, 'white', fitw=0.3)
    text('ペットボトル', T(0.207, 0, 0.56) @ FPX, 0.05, 'white', fitw=0.3)
    put(poly_bm([(0, -0.04, 0.47), (0, 0.04, 0.47), (0, 0.0, 0.52)], 0.002), 'white', T(0.207, 0, 0), smooth=False)

# ================================================================ the building
WX = -2.6; Y0B, Y1B = -2.5, 5.55; GF, UF0, TOPB = 3.6, 3.7, 6.25
group('Building')
box(WX - 1.2, WX - 0.02, Y0B + 0.02, -2.0, 0, TOPB, 'plaster', 0)              # core block, open where the shop is
box(WX - 1.2, WX - 0.02, 2.4, Y1B, 0, TOPB, 'plaster', 0)
box(WX - 1.2, WX - 0.02, -2.0, 2.4, 2.6, TOPB, 'plaster', 0)
box(WX - 1.0, WX, -2.0, 2.4, -0.02, 0.005, 'grout', 0)
# shop opening recess (interior seen behind the stall)
box(WX - 1.0, WX - 0.95, -2.0, 2.4, 0, 2.6, 'interior', 0)
box(WX - 1.0, WX, -2.0, 2.4, 2.6, 2.65, 'dark', 0)
box(WX - 0.98, WX - 0.9, -1.6, -0.5, 0.0, 1.8, 'white', 0.02)
box(WX - 0.92, WX - 0.9, -1.55, -0.55, 0.2, 1.7, EMIT['interior_lt'], 0)
for zz in (0.25, 0.62, 0.99, 1.36):
    box(WX - 0.9, WX - 0.68, -1.56, -0.54, zz - 0.02, zz, 'steel', 0.004, 1)
    for i in range(7):
        c3 = ['drink_g', 'drink_o', 'drink_bl', 'drink_rd', 'drink_w', 'styro_lbl', 'yellow'][(i + int(zz * 10)) % 7]
        box(WX - 0.86, WX - 0.72, -1.52 + i * 0.135, -1.42 + i * 0.135, zz, zz + 0.12 + 0.08 * ((i * 3 + int(zz * 7)) % 3) / 2, c3, 0.01, 1)
for zz in (0.18, 1.75): box(WX - 0.7, WX - 0.62, -1.6, -0.5, zz - 0.03, zz + 0.03, 'white', 0.015)
for yy in (-1.6, -1.05, -0.5): box(WX - 0.7, WX - 0.62, yy - 0.03, yy + 0.03, 0.15, 1.78, 'white', 0.015)
for zz in (0.55, 0.95, 1.35): box(WX - 0.95, WX - 0.6, 0.2, 2.2, zz, zz + 0.03, 'wood', 0.008, 1)
for i in range(8): box(WX - 0.9, WX - 0.7, 0.3 + i * 0.24, 0.5 + i * 0.24, 0.98, 1.1 + 0.05 * (i % 3), 'styro' if i % 2 else 'crate_blue', 0.01, 1)
box(WX - 0.9, WX - 0.86, -1.95, 2.35, 2.5, 2.54, EMIT['interior_lt'], 0.0)
# roll shutter: housing, slats down to ~2 m, guide rails
box(WX - 0.04, WX + 0.2, -2.05, 2.45, 2.6, 2.9, 'shutter_dk', 0.06, 3)
for k2 in range(9):
    z1 = 2.6 - k2 * 0.068
    box(WX - 0.06, WX - 0.02, -2.0, 2.4, z1 - 0.066, z1, 'shutter', 0.014, 2)
box(WX - 0.07, WX - 0.0, -2.0, 2.4, 2.6 - 9 * 0.068 - 0.05, 2.6 - 9 * 0.068, 'shutter_dk', 0.012, 1)
for hy in (-1.2, 1.6): tube(spline([(WX, hy - 0.08, 1.96), (WX + 0.05, hy - 0.06, 1.94), (WX + 0.05, hy + 0.06, 1.94), (WX, hy + 0.08, 1.96)], 3), 0.008, 'steel', 6)
for sy in (-2.0, 2.4): box(WX - 0.08, WX + 0.02, sy - 0.04, sy + 0.04, 0, 2.6, 'shutter_dk', 0.01, 1)
# corner pillar and mid pillar: stacked tiles with real joints; side wall wraps round the corner
def tile_pillar(y0, y1, x0, x1, h, wrap=0.0):
    k3 = 0; z = 0.0
    while z < h - 0.01:
        th = min(0.15, h - z)
        box(x0, x1, y0, y1, z + 0.004, z + th - 0.004, 'tile_a' if k3 % 2 else 'tile_b', 0.006, 1)
        if wrap: box(x0 - wrap, x0, y0, y0 + 0.02, z + 0.004, z + th - 0.004, 'tile_a' if k3 % 2 else 'tile_b', 0.004, 1)
        z += th; k3 += 1
    box(x0 - 0.01, x1 + 0.02, y0 - 0.02, y1 + 0.02, 0, 0.12, 'grout', 0.01, 1)
box(WX - 1.2, WX + 0.17, Y0B - 0.005, -2.05, 0, GF, 'grout', 0)
tile_pillar(Y0B - 0.02, -2.05, WX - 0.02, WX + 0.18, GF, 1.15)
box(WX - 0.02, WX + 0.12, 2.42, 2.68, 0, GF, 'grout', 0)
tile_pillar(2.42, 2.68, WX - 0.02, WX + 0.14, GF)
# right wall section: tiled wainscot + plaster
box(WX - 0.01, WX + 0.005, 2.68, Y1B, 0, 1.02, 'grout', 0)
for r_ in range(7):
    for c_ in range(int((Y1B - 2.68) / 0.15)):
        y = 2.68 + c_ * 0.15
        box(WX, WX + 0.02, y + 0.004, y + 0.146, r_ * 0.145 + 0.004, r_ * 0.145 + 0.141, 'tile_w', 0)
box(WX - 0.01, WX + 0.05, 2.68, Y1B, 1.02, 1.06, 'band', 0.01, 1)
box(WX - 0.01, WX + 0.01, 2.68, Y1B, 1.06, GF, 'plaster', 0)
# electricity meter box
box(WX, WX + 0.1, 2.85, 3.15, 1.3, 1.62, 'grey_lt', 0.015)
cyl(WX + 0.1, 3.0, 1.5, 0.07, 0.02, 'glass', 'X', 16, bev=0.004)
box(WX + 0.1, WX + 0.105, 2.92, 3.08, 1.34, 1.4, 'dark', 0, 1)
tube([(WX + 0.03, 3.0, 1.62), (WX + 0.03, 3.0, GF)], 0.012, 'grey', 6)
# sign band: board with 鮮魚, red roundel, tagline, gooseneck lamps
box(WX, WX + 0.05, -2.05, 2.45, 2.9, GF - 0.02, 'band', 0.01)
box(WX + 0.03, WX + 0.12, -1.9, 2.3, 2.95, 3.55, 'navy', 0.02)
box(WX + 0.1, WX + 0.14, -1.84, 2.24, 3.0, 3.5, 'sign', 0.012)
text('鮮魚', T(WX + 0.14, 0.1, 3.25) @ FPX, 0.4, 'navy', 0.02, spacing=1.15)
cyl(WX + 0.142, -1.35, 3.25, 0.2, 0.012, 'red', 'X', 28, bev=0.004)
text('魚', T(WX + 0.15, -1.35, 3.25) @ FPX, 0.24, 'sign', 0.008)
text('産地直送', T(WX + 0.14, 1.65, 3.36) @ FPX, 0.1, 'red', 0.006, fitw=0.9)
text('新鮮・地物', T(WX + 0.14, 1.65, 3.16) @ FPX, 0.09, 'navy', 0.006, fitw=0.9)
for ly in (-1.0, 0.2, 1.4):
    tube(spline([(WX + 0.02, ly, 3.62), (WX + 0.22, ly, 3.72), (WX + 0.42, ly, 3.66)], 4), 0.01, 'frame_dk', 6)
    lathe([(0, 0.0), (0.012, 0.02), (0.075, -0.04), (0.08, -0.05), (0.07, -0.05), (0, -0.01)], 'frame_dk', T(WX + 0.44, ly, 3.64) @ Ry(25), 14)
    cyl(0, 0, 0, 0.065, 0.004, EMIT['bulb'], 'Z', 12, Mx=T(WX + 0.44, ly, 3.64) @ Ry(25) @ T(0, 0, -0.046))
# vertical projecting sign (tate kanban) on the corner pillar, read from the street
with at(T(WX + 0.2, Y0B + 0.18, 0)):
    for zz in (4.0, 5.6): box(0.0, 0.42, -0.02, 0.02, zz - 0.02, zz + 0.02, 'frame_dk', 0.006, 1)
    box(0.12, 0.6, -0.06, 0.06, 3.85, 5.75, 'red', 0.03, 2)
    box(0.15, 0.57, -0.065, 0.065, 3.9, 5.7, 'sign', 0.012, 1)
    for sd in (-1, 1):
        text('魚\nが\nし', T(0.36, sd * 0.066, 4.8) @ Rz(180 if sd < 0 else 0) @ Rx(90), 0.38, 'red_dk', 0.008)
    cyl(0.36, 0, 5.92, 0.06, 0.12, 'bulb', 'Z', 12, bev=0.01)
# belt course and lap siding on the upper floor (wrapping the corner)
box(WX - 0.02, WX + 0.08, Y0B - 0.08, Y1B, GF, UF0, 'band', 0.015)
box(WX - 1.2, WX + 0.08, Y0B - 0.08, Y0B + 0.02, GF, UF0, 'band', 0.012, 1)
z = UF0; k3 = 0
while z < TOPB - 0.18:
    box(WX - 0.01, WX + 0.035, Y0B - 0.03, Y1B, z, z + 0.185, 'siding' if k3 % 2 else 'siding2', 0.008, 1)
    box(WX + 0.035, WX + 0.045, Y0B - 0.03, Y1B, z, z + 0.012, 'grout', 0, 1)
    box(WX - 1.2, WX + 0.035, Y0B - 0.04, Y0B - 0.0, z, z + 0.185, 'siding' if k3 % 2 else 'siding2', 0.008, 1)
    z += 0.18; k3 += 1
# parapet coping
box(WX - 1.22, WX + 0.12, Y0B - 0.1, Y1B, TOPB - 0.02, TOPB + 0.1, 'band', 0.02)
box(WX - 1.22, WX + 0.14, Y0B - 0.12, Y1B, TOPB + 0.1, TOPB + 0.14, 'dark', 0.012, 1)
# windows
def window(y0, y1, z0, z1, curtain=False, guard=False, flowers=False):
    box(WX + 0.03, WX + 0.1, y0, y1, z0, z1, 'alu', 0.012)
    box(WX + 0.08, WX + 0.105, y0 + 0.05, y1 - 0.05, z0 + 0.05, z1 - 0.05, 'glass', 0)
    ym = (y0 + y1) / 2
    box(WX + 0.1, WX + 0.12, ym - 0.025, ym + 0.025, z0 + 0.04, z1 - 0.04, 'alu', 0.006, 1)
    for gy in (y0 + 0.2, ym + 0.15):
        cbox(WX + 0.106, gy, (z0 + z1) / 2, 0.003, 0.07, (z1 - z0) * 0.7, mat('glare_w', 'c8dcea', 0.3), 0, 1, Rx(25))
    if curtain:
        put(sheet_bm([[(WX + 0.075 + 0.015 * math.sin(i * 1.3), y0 + 0.05 + (ym - y0 - 0.05) * i / 10, z) for i in range(11)] for z in (z0 + 0.06, z1 - 0.06)]), 'curtain', None)
    box(WX + 0.08, WX + 0.18, y0 - 0.06, y1 + 0.06, z0 - 0.05, z0, 'alu', 0.012)
    if guard:
        for gz in (z0 + 0.12, z0 + 0.3, z0 + 0.48): tube([(WX + 0.18, y0 + 0.02, gz), (WX + 0.18, y1 - 0.02, gz)], 0.012, 'alu', 6)
        for gy in (y0 + 0.04, y1 - 0.04): tube([(WX + 0.1, gy, z0 + 0.05), (WX + 0.18, gy, z0 + 0.05), (WX + 0.18, gy, z0 + 0.55)], 0.012, 'alu', 6)
    if flowers:
        box(WX + 0.12, WX + 0.32, y0 + 0.1, y1 - 0.1, z0 - 0.2, z0 - 0.05, 'pot', 0.02)
        for i in range(10):
            yy = y0 + 0.16 + (y1 - y0 - 0.32) * i / 9
            ico(WX + 0.22, yy, z0 - 0.02 + 0.03 * (i % 2), 0.075, ['leaf', 'leaf2', 'leaf3'][i % 3], 1, jitter=0.15)
            if i % 2: ico(WX + 0.28, yy, z0 + 0.03, 0.025, 'bun_r' if i % 4 == 1 else 'bun_y', 1)
window(-1.5, -0.1, 4.25, 5.45, curtain=True, guard=True)
window(0.8, 2.2, 4.25, 5.45, flowers=True)
window(3.1, 3.9, 4.55, 5.45, curtain=True)
# AC outdoor unit on brackets with its pipe
with at(T(WX, 4.55, 4.05)):
    for by in (-0.28, 0.28):
        box(0.0, 0.42, by - 0.015, by + 0.015, -0.04, 0.0, 'grey', 0.005, 1)
        tube([(0.0, by, -0.3), (0.38, by, -0.03)], 0.012, 'grey', 4)
    box(0.06, 0.36, -0.4, 0.4, 0.0, 0.55, 'ac', 0.03, 3)
    cyl(0.36, -0.1, 0.27, 0.2, 0.01, 'dark', 'X', 24)
    for rr in (0.2, 0.15, 0.1, 0.05):
        tube([(0.372, -0.1 + p.x, 0.27 + p.y) for p in circle(rr, 24)], 0.006, 'ac', 4, caps=False)
    tube([(0.373, -0.3, 0.27), (0.373, 0.1, 0.27)], 0.006, 'ac', 4); tube([(0.373, -0.1, 0.07), (0.373, -0.1, 0.47)], 0.006, 'ac', 4)
    for k2 in range(3):
        put(cube_bm(0.008, 0.06, 0.15, 0.003, 1), 'grey', T(0.355, -0.1, 0.27) @ Rx(k2 * 120) @ T(0, 0, 0.09) @ Ry(20))
    for k2 in range(6): box(0.36, 0.37, 0.18, 0.34, 0.08 + k2 * 0.07, 0.1 + k2 * 0.07, 'grey_lt', 0.004, 1)
    tube(spline([(0.2, 0.4, 0.15), (0.2, 0.5, 0.12), (0.1, 0.55, 0.2), (0.02, 0.55, 0.5)], 4), 0.025, 'pipe_white', 8)
# round wall fan (ventilation) above the bin
fan(T(WX + 0.16, 3.0, 2.35) @ Rz(15), 0.18)
# drainpipe with brackets
DY = 5.42
tube(spline([(WX + 0.15, DY - 0.25, TOPB - 0.05), (WX + 0.15, DY - 0.1, TOPB - 0.25), (WX + 0.12, DY, TOPB - 0.45)], 3) +
     [Vector((WX + 0.12, DY, 0.25)), Vector((WX + 0.2, DY, 0.06)), Vector((WX + 0.3, DY, 0.04))], 0.045, 'drain', 10)
box(WX + 0.02, WX + 0.24, DY - 0.38, DY - 0.12, TOPB - 0.12, TOPB, 'drain', 0.02)
for zz in (1.0, 2.3, 3.4, 4.6, 5.6):
    tube([(WX + 0.12 + p.x * 1.0, DY + p.y, zz) for p in circle(0.055, 12)], 0.008, 'grey', 4, caps=False)
    box(WX, WX + 0.08, DY - 0.012, DY + 0.012, zz - 0.012, zz + 0.012, 'grey', 0.003, 1)

group('Plants')
pot_plant(-2.3, -2.42, 'bush', 1.0)
pot_plant(-2.32, 2.62, 'spiky', 0.9)
pot_plant(-2.05, 2.42, 'bush', 0.7)

# ================================================================ utility pole
group('UtilityPole')
with at(T(POLE.x, POLE.y, 0)):
    lathe([(0, 0), (0.17, 0), (0.12, 8.2), (0, 8.2)], 'pole', None, 16)
    box(-0.24, 0.24, -0.24, 0.24, 0, 0.05, 'pole', 0.02)
    # yellow/black guard sleeve with diagonal stripes
    rings = 16; segs = 24; bm = bmesh.new(); V = []
    for j in range(rings + 1):
        z = 0.12 + 1.8 * j / rings; r = 0.172 - 0.006 * z / 8.2 * 8 + 0.012
        V.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    for j in range(rings):
        for i in range(segs):
            i1 = (i + 1) % segs; f = bm.faces.new((V[j][i], V[j][i1], V[j + 1][i1], V[j + 1][i]))
            f.material_index = int((i / segs * 4 + j / rings * 1.8 * 2.2)) % 2
    put(bm, ['guard_y', 'guard_k'], None)
    for zz in (0.12, 1.92): tube([(p.x, p.y, zz) for p in circle(0.186, 24)], 0.01, 'guard_k', 4, caps=False)
    # number plate
    with at(T(0.0, -0.17, 2.3) @ Rz(-90)):
        box(-0.002, 0.012, -0.08, 0.08, -0.17, 0.17, 'white', 0.004, 1)
        box(0.012, 0.014, -0.08, 0.08, 0.12, 0.17, 'vm_blue', 0, 1)
        text('魚河岸', T(0.0145, 0, 0.03) @ FPX, 0.05, 'ink', fitw=0.13)
        text('12', T(0.0145, 0, -0.08) @ FPX, 0.07, 'ink')
    # step bolts
    for k2 in range(10):
        z = 2.4 + k2 * 0.42; a = math.pi * (k2 % 2) + 0.6; r = 0.17 - 0.05 * z / 8.2
        tube([(r * math.cos(a), r * math.sin(a), z), ((r + 0.18) * math.cos(a), (r + 0.18) * math.sin(a), z)], 0.012, 'grey', 5)
    # street lamp on a curved arm toward the street
    tube(spline([(0.1, 0, 4.4), (0.5, 0, 4.75), (1.1, 0, 4.85)], 4), 0.03, 'grey', 8)
    for zz in (4.35, 4.85): tube([(p.x * 1.0, p.y, zz) for p in circle(0.15, 16)], 0.012, 'grey', 4, caps=False)
    lathe([(0, 0.0), (0.05, 0.0), (0.16, -0.06), (0.17, -0.09), (0.0, -0.09)], 'grey_lt', T(1.15, 0, 4.86), 16)
    cyl(1.15, 0, 4.77, 0.13, 0.01, EMIT['bulb'], 'Z', 16)
    # cross arm with insulators
    box(-0.75, 0.75, -0.05, 0.05, 7.55, 7.65, 'grey', 0.015)
    for ix in (-0.6, -0.2, 0.25, 0.6):
        lathe([(0, 0), (0.04, 0.0), (0.06, 0.04), (0.035, 0.06), (0.055, 0.1), (0.03, 0.13), (0.0, 0.14)], 'insul', T(ix, 0, 7.65), 10)
    # transformer can on the street side
    with at(T(0.42, 0, 5.0)):
        for zz in (0.1, 0.55): box(-0.3, -0.1, -0.05, 0.05, zz - 0.03, zz + 0.03, 'grey', 0.01, 1)
        cyl(0, 0, 0.35, 0.24, 0.72, 'transf', 'Z', 20, bev=0.02, bseg=2)
        lathe([(0.25, 0.71), (0.25, 0.74), (0.18, 0.8), (0, 0.82)], 'transf', None, 20)
        for k2 in range(8):
            a = 2 * math.pi * k2 / 8 + 0.2
            cbox(0.25 * math.cos(a), 0.25 * math.sin(a), 0.33, 0.06, 0.012, 0.5, 'transf', 0.004, 1, Rz(math.degrees(a)))
        for ix in (-0.08, 0.08): lathe([(0, 0), (0.025, 0), (0.035, 0.03), (0.02, 0.05), (0.03, 0.08), (0, 0.1)], 'insul', T(ix, 0.0, 0.8), 8)
        box(0.235, 0.25, -0.06, 0.06, 0.38, 0.46, 'yellow', 0.003, 1)
    # drop cable to the building and wires to the cross arm
    tube(sag((0.42, 0.0, 5.85), (-0.6, 0.0, 7.6), 0.15, 8), 0.012, 'black', 5)
tube(sag((POLE.x - 0.1, POLE.y, 6.6), (WX + 0.05, -1.8, TOPB - 0.2), 0.35, 14), 0.012, 'black', 5)
tube(sag((POLE.x + 0.4, POLE.y, 5.3), (WX + 0.05, -1.5, 3.8), 0.25, 12), 0.01, 'black', 5)

# ================================================================ build objects, parent, export
corner = bpy.data.objects.new('Corner', None); scn.collection.objects.link(corner)
OBJS = []
for name, g in GROUPS.items():
    me = bpy.data.meshes.new(name); g.bm.normal_update(); g.bm.to_mesh(me); g.bm.free()
    for m in g.mats: me.materials.append(m)
    ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob); ob.parent = corner
    wn = ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.weight = 50
    OBJS.append(ob)
dg = C.evaluated_depsgraph_get(); tri = {}
for ob in OBJS:
    e = ob.evaluated_get(dg); m_ = e.to_mesh(); m_.calc_loop_triangles(); tri[ob.name] = len(m_.loop_triangles); e.to_mesh_clear()
print('TRIS total', sum(tri.values())); print(sorted(tri.items(), key=lambda kv: -kv[1]))
bpy.ops.object.select_all(action='DESELECT')
corner.select_set(True)
for ob in OBJS: ob.select_set(True)
C.view_layer.objects.active = corner
glb = os.path.join(OUT, 'corner.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_yup=True)
print('wrote', glb)
if NOPREV: sys.exit(0)

# ================================================================ preview: street ground, soft daylight, game-like camera
TMP = []
def gplane(x0, x1, y0, y1, z, h):
    box(x0, x1, y0, y1, z - 0.05, z, mat('pv_' + h, h, 0.9), 0)
group('PV_Ground')
gplane(-8, 1.05, -9, 10, 0.0, 'cfc6b5')
for y in range(-9, 10):
    box(-8, 1.05, y - 0.008, y + 0.008, -0.01, 0.002, mat('pv_joint', 'b3aa98', 0.9), 0)
gplane(1.05, 1.25, -9, 10, 0.06, 'b8b2a8')
gplane(1.25, 12, -9, 10, -0.04, '8d9097')
for y in range(-9, 10, 3): box(4.2, 4.35, y, y + 1.6, -0.04, -0.035, mat('pv_line', 'eeeae0', 0.9), 0)
pv = bpy.data.meshes.new('PV'); GROUPS['PV_Ground'].bm.to_mesh(pv)
for m in GROUPS['PV_Ground'].mats: pv.materials.append(m)
po = bpy.data.objects.new('PV_Ground', pv); scn.collection.objects.link(po)

world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('bcd6f0'), 1); bg.inputs['Strength'].default_value = 0.95
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 4.2; sun.data.color = srgb('fff2dc'); sun.data.angle = math.radians(9)
sun.rotation_euler = (math.radians(46), 0, math.radians(38))
for py in (-1.5, -0.5, 0.5, 1.5):   # warm glow from the stall spots
    L = bpy.data.objects.new('spot', bpy.data.lights.new('spot', 'POINT')); scn.collection.objects.link(L)
    L.location = (RAIL_X - 0.1, py, RAIL_Z - 0.3); L.data.energy = 18; L.data.color = srgb('ffd9a0'); L.data.shadow_soft_size = 0.2
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = 32; scn.cycles.use_denoising = True
scn.cycles.max_bounces = 5; scn.cycles.use_adaptive_sampling = True
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium Low Contrast'; scn.view_settings.exposure = 0.0
def shoot(fn, tgt, az, d, h, lens):
    tgt = Vector(tgt); az = math.radians(az)
    pos = tgt + Vector((d * math.cos(az), d * math.sin(az), 0)); pos.z = h
    cam.location = pos; cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
    scn.render.filepath = os.path.join(OUT, fn); bpy.ops.render.render(write_still=True); print('wrote', fn)
DBG = [a[5:] for a in sys.argv if a.startswith('shot=')]
if not DBG: shoot('prev.png', (-1.0, 0.7, 1.75), -33, 8.7, 3.5, 27)
if 'close' in DBG: shoot('dbg_close.png', (-0.7, 0.0, 1.0), -20, 3.2, 2.2, 32)
if 'vm' in DBG: shoot('dbg_vm.png', (-1.9, 4.3, 1.1), -15, 3.6, 1.7, 32)
if 'bld' in DBG: shoot('dbg_bld.png', (-2.6, 1.4, 3.6), -10, 9.0, 3.0, 28)
