# Giant lily pad on a pond (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py.
#   <bl python> tools/blender/stage_lily_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vslily): lily_kit.blend, lily_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         lily_palette.png, lily_gamecam.exr (light passes) -> lily_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the other kits: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); M_GLASS_WATER (same palette, 'water'/'water_lt'
# swatches) for the pond surface and its flat ripple rings / streaks, over an opaque pale pond floor (as the campaign
# puddles sit over the road). The palette is the sushi kit's with the sushi-only swatches repurposed for pad greens,
# the ring line, lotus pink, reeds, cattails, the frog and the pond floor.
# Fighting surface (pad top) at z = 0, ring line at r = 4.6, pad r = 5.4 with its V notch outside the ring, pond at
# game y = -0.16. The small pads, the lotus flowers and the frog are separate root empties FLOAT_* (children = meshes),
# origin at the water level, so the game can bob them.
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vslily'
SUMO_GLB = '/home/user/sumo/public/assets/models/sumo_game.glb'
COMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kkbc_flat_comp.py')
NORENDER = 'norender' in sys.argv; LOWRES = 'lowres' in sys.argv
RNG = random.Random(7)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene; ROOT = scn.collection

def T(x, y, z): return Matrix.Translation((x, y, z))
def Rx(d): return Matrix.Rotation(math.radians(d), 4, 'X')
def Ry(d): return Matrix.Rotation(math.radians(d), 4, 'Y')
def Rz(d): return Matrix.Rotation(math.radians(d), 4, 'Z')
def Sc(x, y, z): return Matrix.Diagonal((x, y, z, 1))
I4 = Matrix.Identity(4)

def coll(name):
    c = bpy.data.collections.new(name); ROOT.children.link(c); return c
CN = {n: coll(n) for n in ('ENV_POND', 'ENV_PAD', 'ENV_FLOAT', 'ENV_PROPS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

# =====================================================================================================================
# palette + master material (sushi kit PAL; sushi-only slots repurposed for the pond)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('yellow_lt', 'f6dc8e'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('pad', '8cc66e'), ('pad_lt', 'aad98a'), ('pad_dk', '64a35c'), ('pad_alt', '9ccc72'), ('pad_line', 'e8f3c8'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('lotus_lt', 'f7c3d3'), ('reed', '7db863'), ('cattail', 'b98a68'), ('pond_bed', '8dbbe2'), ('stone', 'e9e1d1'), ('frog', 'a4d26e'), ('purple', '8c6aa8'),
]
SW = {n: i for i, (n, h) in enumerate(PAL)}
GLASSY = {'glass', 'glass_lt', 'water', 'water_lt'}
def swuv(n):
    i = SW[n]; return ((i % 8 + 0.5) / 8, (i // 8 + 0.5) / 8)
img = bpy.data.images.new('KKBC_Palette', 32, 32, alpha=False)
px = [0.0] * (32 * 32 * 4)
for i, (n, h) in enumerate(PAL):
    c = [int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]
    for yy in range((i // 8) * 4, (i // 8) * 4 + 4):
        for xx in range((i % 8) * 4, (i % 8) * 4 + 4):
            j = (yy * 32 + xx) * 4; px[j:j + 4] = [c[0], c[1], c[2], 1.0]
img.pixels = px
img.filepath_raw = OUT + '/lily_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

def master(name, rough, alpha=1.0, spec=0.25):
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; Lk = m.node_tree.links.new
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = 0.0
    b.inputs['Specular IOR Level'].default_value = spec
    tx = N.new('ShaderNodeTexImage'); tx.image = img; tx.interpolation = 'Closest'; tx.extension = 'EXTEND'; tx.name = 'Palette'
    uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'PAL'; Lk(uvn.outputs['UV'], tx.inputs['Vector'])
    oi = N.new('ShaderNodeObjectInfo'); cr = N.new('ShaderNodeValToRGB'); cr.name = 'Vary'
    cr.color_ramp.elements[0].color = (0.95, 0.95, 0.95, 1); cr.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0; mx.name = 'VaryMix'
    Lk(oi.outputs['Random'], cr.inputs['Fac']); Lk(tx.outputs['Color'], mx.inputs['A']); Lk(cr.outputs['Color'], mx.inputs['B'])
    Lk(mx.outputs['Result'], b.inputs['Base Color'])
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'; m.surface_render_method = 'BLENDED'; m.use_backface_culling = False
    m.diffuse_color = (0.8, 0.78, 0.74, alpha); return m
M_KIT = master('M_KIT', 0.85); M_KIT.use_backface_culling = True
M_GW = master('M_GLASS_WATER', 0.32, alpha=0.86, spec=0.5)

# =====================================================================================================================
# module builder (as the dohyo kit): bmesh primitives painted onto palette swatches
# =====================================================================================================================
MODS = {}
class MB:
    def __init__(s):
        s.bm = bmesh.new(); s.uv = s.bm.loops.layers.uv.new('PAL')
    def _begin(s): return set(s.bm.faces), set(s.bm.edges)
    def _end(s, before, col, bev=0.0, seg=2, ang=None, M=None, smooth=True):
        fb, eb = before; bm = s.bm
        new_e = [e for e in bm.edges if e not in eb]
        nf_ = [f for f in bm.faces if f not in fb]
        if nf_: bmesh.ops.recalc_face_normals(bm, faces=nf_)
        if bev > 0:
            es = new_e if ang is None else [e for e in new_e if e.is_manifold and e.calc_face_angle(0) > math.radians(ang)]
            if es: bmesh.ops.bevel(bm, geom=es, offset=bev, offset_type='OFFSET', segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
        u = swuv(col); mi = 1 if col in GLASSY else 0
        for f in bm.faces:
            if f not in fb:
                f.material_index = mi; f.smooth = smooth
                for l in f.loops: l[s.uv].uv = u
    def box(s, x0, x1, y0, y1, z0, z1, col, bev=0.0, seg=2, M=None):
        b = s._begin(); r = bmesh.ops.create_cube(s.bm, size=1.0)
        Mx = (M or I4) @ T((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) @ Sc(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
        bmesh.ops.transform(s.bm, matrix=Mx, verts=r['verts'])
        s._end(b, col, min(bev, abs(x1 - x0) / 2.05, abs(y1 - y0) / 2.05, abs(z1 - z0) / 2.05) if bev else 0, seg)
    def cyl(s, x, y, z, r, h, col, seg=12, r2=None, bev=0.0, bseg=2, M=None, axis='Z'):
        b = s._begin()
        res = bmesh.ops.create_cone(s.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
        A = {'Z': I4, 'X': Ry(90), 'Y': Rx(-90)}[axis]
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ A, verts=res['verts'])
        s._end(b, col, bev, bseg, ang=30 if bev else None)
    def ico(s, x, y, z, r, col, sub=2, sq=(1, 1, 1), M=None, jit=0.0):
        b = s._begin(); res = bmesh.ops.create_icosphere(s.bm, subdivisions=sub, radius=r)
        for v in res['verts']:
            if jit: v.co *= 1 + RNG.uniform(-jit, jit)
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ Sc(*sq), verts=res['verts'])
        s._end(b, col)
    def lathe(s, prof, col, seg=12, M=None, bev=0.0, ang=30):
        b = s._begin(); bm = s.bm; rings = []
        for r, z in prof:
            if r <= 1e-6: rings.append([bm.verts.new((0, 0, z))])
            else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
        for a, c in zip(rings, rings[1:]):
            for i in range(seg):
                i1 = (i + 1) % seg
                if len(a) == 1: bm.faces.new((a[0], c[i], c[i1]))
                elif len(c) == 1: bm.faces.new((a[i], a[i1], c[0]))
                else: bm.faces.new((a[i], a[i1], c[i1], c[i]))
        if len(rings[0]) > 1: bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1: bm.faces.new(rings[-1])
        bmesh.ops.transform(bm, matrix=(M or I4), verts=[v for rg in rings for v in rg]); s._end(b, col, bev, 2, ang=ang if bev else None)
    def prism(s, pts, z0, z1, col, M=None, bev=0.0, bseg=2):
        b = s._begin(); bm = s.bm
        lo = [bm.verts.new((x, y, z0)) for x, y in pts]; hi = [bm.verts.new((x, y, z1)) for x, y in pts]
        bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
        n = len(pts)
        for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
        bmesh.ops.transform(bm, matrix=(M or I4), verts=lo + hi); s._end(b, col, bev, bseg, ang=30 if bev else None)
    def finish(s, name, sharp=35):
        me = bpy.data.meshes.new(name); s.bm.normal_update(); s.bm.to_mesh(me); s.bm.free()
        me.materials.append(M_KIT); me.materials.append(M_GW)
        try: me.set_sharp_from_angle(angle=math.radians(sharp))
        except Exception: pass
        me['kkbc_module'] = 1; MODS[name] = me; return me

def place(mod, name, loc=(0, 0, 0), rz=0.0, s=1.0, c='ENV_PROPS', rx=0.0, ry=0.0):
    ob = bpy.data.objects.new(name, MODS[mod]); CN[c].objects.link(ob)
    ob.location = loc; ob.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    ob.scale = s if isinstance(s, (tuple, list)) else (s, s, s); return ob
NAMECNT = {}
def nm(p):
    NAMECNT[p] = NAMECNT.get(p, 0) + 1; return '%s_%02d' % (p, NAMECNT[p])
def paint_up(me, col, nz=0.75, zmin=-99.0):
    """recolour faces that face up (and sit above zmin) to another swatch."""
    uvl = me.uv_layers['PAL']; u = swuv(col)
    for p in me.polygons:
        if p.normal.z > nz and p.center.z > zmin:
            for li in p.loop_indices: uvl.data[li].uv = u
def blob(R, r, n=16, amp=0.14, k=None):
    """soft irregular closed outline (a melted cheese patch, a sauce splash)."""
    ph = [R.uniform(0, 6.28) for _ in range(3)]
    return [(r * (1 + amp * (0.6 * math.sin(2 * a + ph[0]) + 0.4 * math.sin(3 * a + ph[1]) + 0.25 * math.sin(5 * a + ph[2]))) * math.cos(a),
             r * (1 + amp * (0.6 * math.sin(2 * a + ph[0]) + 0.4 * math.sin(3 * a + ph[1]) + 0.25 * math.sin(5 * a + ph[2]))) * math.sin(a))
            for a in (2 * math.pi * i / n for i in range(n))]


# =====================================================================================================================
# dimensions (game stages.js 'lily': pad RD = RING_R + 0.7, pond surface H = 0.16 below the fighting surface)
# =====================================================================================================================
RING_R = 4.6               # playable radius
RD = 5.4                   # giant pad radius (slightly over RD 5.3 so the notch stays outside the ring line)
WZ = -0.16                 # pond surface
LIP = 0.2                  # width of the soft raised rim
NOTCH_DIR = -24.0          # notch direction (deg, blender, from +x) -> right, a touch towards the camera
LINE_IN, LINE_OUT = 4.53, 4.67   # the pale ring line

def notch_rmax(R, depth, half):
    """outline radius per angle (local, notch along +x): a straight-sided V from the tip (R - depth) to the edge."""
    tip = Vector((R - depth, 0.0)); phi = math.asin(half / R) if half else 0.0
    def f(t):
        if not depth or abs(t) >= phi: return R
        E = Vector((R * math.cos(phi), math.copysign(R * math.sin(phi), t)))
        d = Vector((math.cos(t), math.sin(t))); e = E - tip
        den = d.x * e.y - d.y * e.x
        s = (tip.x * e.y - tip.y * e.x) / den
        return s
    return f, phi

def mod_pad(name, R, depth=0.0, half=0.0, lip=LIP, zl=0.09, th=0.24, top='pad', side='pad_dk', vein='pad_lt', nv=9, ring=False, seg=144, z0=0.0):
    """a lily pad: flat top at z0, a soft raised lip, rolled edge, a V notch along local +x; chunky flat lighter veins."""
    m = MB(); bm = m.bm; b = m._begin()
    f, phi = notch_rmax(R, depth, half)
    angs = sorted(set([2 * math.pi * i / seg - math.pi for i in range(seg)] + ([0.0, phi - 1e-4, -phi + 1e-4, phi + 0.02, -phi - 0.02] if depth else [])))
    cols = []
    for t in angs:
        Rm = f(t); ri = Rm - lip; c, s_ = math.cos(t), math.sin(t)
        prof = [(ri * k, 0.0) for k in (0.18, 0.4, 0.62, 0.82, 0.94, 1.0)]
        prof += [(Rm - lip * 0.55, zl * 0.55), (Rm - lip * 0.22, zl), (Rm - lip * 0.04, zl * 0.8), (Rm + 0.02, zl * 0.1),
                 (Rm + 0.01, -th * 0.55), (Rm - 0.08, -th * 0.95), (Rm - 0.22, -th), (ri * 0.55, -th)]
        cols.append([bm.verts.new((r * c, r * s_, z0 + z)) for r, z in prof])
    ct = bm.verts.new((0, 0, z0)); cb = bm.verts.new((0, 0, z0 - th))
    n = len(angs); P = len(cols[0])
    for i in range(n):
        A, B_ = cols[i], cols[(i + 1) % n]
        bm.faces.new((ct, A[0], B_[0]))
        for k in range(P - 1): bm.faces.new((A[k], A[k + 1], B_[k + 1], B_[k]))
        bm.faces.new((cb, B_[-1], A[-1]))
    m._end(b, top)
    # veins: tapered flat strips from the centre to just inside the lip (none inside the notch)
    if nv:
        b = m._begin()
        for k in range(nv):
            t = math.pi + 2 * math.pi * (k + 0.5) / nv
            t = math.atan2(math.sin(t), math.cos(t))
            if depth and abs(t) < phi + 0.25: continue
            r0, r1 = R * 0.1, f(t) - lip - 0.28 * R / RD
            w0, w1 = 0.3 * R / RD + 0.03, 0.12 * R / RD + 0.02
            c, s_ = math.cos(t), math.sin(t); px, py = -s_, c
            pts = [((r0 + (r1 - r0) * u) * c + px * (w0 + (w1 - w0) * u), (r0 + (r1 - r0) * u) * s_ + py * (w0 + (w1 - w0) * u)) for u in (0.0, 0.5, 0.92)]
            pts += [((r1 + 0.07 * R / RD) * c + px * w1 * 0.5, (r1 + 0.07 * R / RD) * s_ + py * w1 * 0.5), ((r1 + 0.1 * R / RD) * c, (r1 + 0.1 * R / RD) * s_), ((r1 + 0.07 * R / RD) * c - px * w1 * 0.5, (r1 + 0.07 * R / RD) * s_ - py * w1 * 0.5)]
            pts += [((r0 + (r1 - r0) * u) * c - px * (w0 + (w1 - w0) * u), (r0 + (r1 - r0) * u) * s_ - py * (w0 + (w1 - w0) * u)) for u in (0.92, 0.5, 0.0)]
            m.prism(pts, z0 + 0.0, z0 + 0.008, vein)
        nn = 24; m.prism([(R * 0.13 * math.cos(2 * math.pi * i / nn), R * 0.11 * math.sin(2 * math.pi * i / nn)) for i in range(nn)], z0, z0 + 0.012, vein)
    if ring:                                                  # the ring line: a soft pale band at r = 4.6
        b = m._begin(); nr = 192; rings = []
        for r in (LINE_IN, LINE_OUT):
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / nr), r * math.sin(2 * math.pi * i / nr), z0 + 0.016)) for i in range(nr)])
        for i in range(nr):
            i1 = (i + 1) % nr; bm.faces.new((rings[0][i], rings[1][i], rings[1][i1], rings[0][i1]))
        m._end(b, 'pad_line', smooth=False)
    me = m.finish(name, sharp=70)
    uvl = me.uv_layers['PAL']; u = swuv(side)
    for p in me.polygons:                                     # rolled edge + underside a deeper green
        if p.normal.z < 0.35 and p.center.z < z0 + zl * 0.3:
            for li in p.loop_indices: uvl.data[li].uv = u
    return me

# ---- pond -------------------------------------------------------------------------------------------------------------
def annulus(m, cx, cy, r0, r1, z, col, a0=0.0, a1=2 * math.pi, n=96, h=0.006):
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    k = n if full else max(6, int(n * (a1 - a0) / (2 * math.pi)))
    if full:
        bm = m.bm; b = m._begin(); rings = []
        for r, zz in ((r0, z), (r1, z), (r1, z + h), (r0, z + h)):
            rings.append([bm.verts.new((cx + r * math.cos(a0 + 2 * math.pi * i / k), cy + r * math.sin(a0 + 2 * math.pi * i / k), zz)) for i in range(k)])
        for i in range(k):
            i1 = (i + 1) % k
            bm.faces.new((rings[3][i], rings[2][i], rings[2][i1], rings[3][i1]))       # top only + edges
            bm.faces.new((rings[2][i], rings[1][i], rings[1][i1], rings[2][i1]))
            bm.faces.new((rings[0][i], rings[3][i], rings[3][i1], rings[0][i1]))
        m._end(b, col, smooth=False)
    else:                                                     # an arc with soft rounded ends
        rm, hw = (r0 + r1) / 2, (r1 - r0) / 2
        pts = [(cx + (rm + hw) * math.cos(a0 + (a1 - a0) * i / k), cy + (rm + hw) * math.sin(a0 + (a1 - a0) * i / k)) for i in range(k + 1)]
        for j in range(1, 6):
            q = math.pi * j / 6; ex = cx + (rm + hw * math.cos(q)) * math.cos(a1); ey = cy + (rm + hw * math.cos(q)) * math.sin(a1)
            tx, ty = -math.sin(a1), math.cos(a1); pts.append((ex + tx * hw * math.sin(q), ey + ty * hw * math.sin(q)))
        pts += [(cx + (rm - hw) * math.cos(a1 - (a1 - a0) * i / k), cy + (rm - hw) * math.sin(a1 - (a1 - a0) * i / k)) for i in range(k + 1)]
        for j in range(1, 6):
            q = math.pi * j / 6; ex = cx + (rm - hw * math.cos(q)) * math.cos(a0); ey = cy + (rm - hw * math.cos(q)) * math.sin(a0)
            tx, ty = math.sin(a0), -math.cos(a0); pts.append((ex + tx * hw * math.sin(q), ey + ty * hw * math.sin(q)))
        m.prism(pts, z, z + h, col)
def stadium(m, cx, cy, L, w, ang, z, col, h=0.006):
    pts = []; ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for i in range(10):
        q = -math.pi / 2 + math.pi * i / 9; pts.append((L / 2 + w / 2 * math.cos(q), w / 2 * math.sin(q)))
    for i in range(10):
        q = math.pi / 2 + math.pi * i / 9; pts.append((-L / 2 + w / 2 * math.cos(q), w / 2 * math.sin(q)))
    m.prism([(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts], z, z + h, col)

def mod_pond():
    m = MB(); S = 80
    m.box(-S, S, -S, S, WZ - 0.06, WZ, 'water')                                            # the water surface (M_GLASS_WATER)
    return m.finish('MOD_PondWater', sharp=30)
def mod_bed():
    m = MB(); S = 80
    m.box(-S, S, -S, S, WZ - 0.9, WZ - 0.7, 'pond_bed')                                    # opaque pale pond floor under it
    return m.finish('MOD_PondBed', sharp=30)
STREAKS = ((-4.6, -5.6, 1.8, 0.28, 8), (6.8, -4.6, 1.5, 0.26, -6), (-11.0, 6.6, 2.6, 0.3, 4), (-10.0, 6.0, 1.2, 0.24, 4),
           (4.6, 11.4, 2.4, 0.28, -3), (13.6, 1.6, 1.8, 0.26, 6))
def mod_ripples():
    # separate pieces so the game can move them: the rings spread out and fade, the streaks drift and shimmer
    z = WZ + 0.003
    m = MB(); annulus(m, 0, 0, 6.1, 6.36, z, 'water_lt', n=160); m.finish('MOD_RippleA', sharp=30)
    m = MB(); annulus(m, 0, 0, 7.7, 7.9, z, 'water_lt', math.radians(-25), math.radians(120), n=160)
    annulus(m, 0, 0, 7.7, 7.9, z, 'water_lt', math.radians(160), math.radians(240), n=160); m.finish('MOD_RippleB', sharp=30)
    for i, (cx, cy, L, w, a) in enumerate(STREAKS):
        m = MB(); stadium(m, 0, 0, L, w, a, z, 'water_lt'); m.finish('MOD_Streak%d' % i, sharp=30)
def mod_ring_small(name, r):
    m = MB(); annulus(m, 0, 0, r, r + 0.13, WZ + 0.003, 'water_lt', n=96); return m.finish(name, sharp=30)

# ---- lotus, frog, reeds, stones ---------------------------------------------------------------------------------------
def petal(m, col, L, Wd, tilt, az, z, rr):
    """a chunky pointed petal: lathe teardrop, flattened, tilted out, set on a ring."""
    prof = [(0.0, 0.0), (0.22, 0.08), (0.36, 0.3), (0.4, 0.55), (0.33, 0.8), (0.17, 0.98), (0.0, 1.06)]
    M = T(rr * math.cos(math.radians(az)), rr * math.sin(math.radians(az)), z) @ Rz(az - 90) @ Rx(-tilt) @ Sc(Wd / 0.8, Wd * 0.42 / 0.8, L / 1.06)
    m.lathe(prof, col, 12, M=M)
def mod_lotus(name, s=1.0):
    m = MB()
    for k in range(8): petal(m, 'pink_acc', 1.25 * s, 0.78 * s, 62, k * 45 + 10, 0.08 * s, 0.22 * s)
    for k in range(7): petal(m, 'lotus_lt', 1.2 * s, 0.7 * s, 38, k * 51.4 + 30, 0.14 * s, 0.14 * s)
    for k in range(5): petal(m, 'foam', 1.0 * s, 0.6 * s, 16, k * 72 + 5, 0.2 * s, 0.07 * s)
    m.cyl(0, 0, 0.62 * s, 0.24 * s, 0.22 * s, 'acc_yellow', 16, r2=0.3 * s, bev=0.05 * s)
    return m.finish(name, sharp=60)
def mod_bud(name, s=1.0):
    m = MB(); m.cyl(0, 0, -0.4 * s, 0.07 * s, 1.4 * s, 'reed', 8)
    for k in range(4): petal(m, 'pink_acc', 1.0 * s, 0.62 * s, 8, k * 90, 0.25 * s, 0.05 * s)
    return m.finish(name, sharp=60)
def mod_frog():
    m = MB()
    m.ico(0, 0, 0.36, 0.5, 'frog', 2, (1.0, 1.1, 0.72))                                    # body
    m.ico(0, -0.32, 0.3, 0.32, 'yellow_lt', 2, (1.05, 0.6, 0.62))                          # pale chin/belly
    for sx in (-1, 1):
        m.ico(sx * 0.3, -0.12, 0.72, 0.19, 'frog', 2)                                        # eye bumps
        m.ico(sx * 0.32, -0.22, 0.76, 0.12, 'offwhite', 2)
        m.ico(sx * 0.33, -0.31, 0.77, 0.06, 'ink', 1)
        m.ico(sx * 0.48, 0.18, 0.16, 0.24, 'frog', 2, (0.8, 1.5, 0.6))                      # back legs
        m.ico(sx * 0.34, -0.42, 0.08, 0.13, 'frog', 2, (1.2, 1.0, 0.6))                     # front feet
    return m.finish('MOD_Frog', sharp=60)
def mod_reeds(name, seed, n_blade=7, n_tail=3, h=3.4):
    R = random.Random(seed); m = MB()
    for k in range(n_blade):
        a = R.uniform(0, 6.28); r = R.uniform(0, 0.55); hh = h * R.uniform(0.6, 1.0)
        lean_ax, lean = R.uniform(0, 360), R.uniform(6, 20)
        M = T(r * math.cos(a), r * math.sin(a), WZ - 0.1) @ Rz(lean_ax) @ Rx(lean) @ Sc(1, 0.4, 1)
        m.cyl(0, 0, hh / 2, 0.2, hh, R.choice(('reed', 'leaf', 'reed')), 6, r2=0.02, M=M)
    for k in range(n_tail):
        a = 2.1 * k + R.uniform(-0.4, 0.4); r = R.uniform(0.15, 0.45); hh = h * R.uniform(0.95, 1.2)
        M = T(r * math.cos(a), r * math.sin(a), WZ - 0.1) @ Rz(R.uniform(0, 360)) @ Rx(R.uniform(3, 9))
        m.cyl(0, 0, hh / 2, 0.055, hh, 'reed', 8, M=M)
        m.cyl(0, 0, hh * 0.78, 0.17, hh * 0.22, 'cattail', 12, M=M, bev=0.08, bseg=3)       # soft brown head
        m.cyl(0, 0, hh * 0.93, 0.03, hh * 0.1, 'reed', 6, r2=0.012, M=M)
    return m.finish(name, sharp=60)
def mod_stone(name, seed, r):
    R0 = RNG.getstate(); RNG.seed(seed); m = MB()
    m.ico(0, 0, 0, r, 'shutter', 2, (1.0, 0.86, 0.3), jit=0.05)
    RNG.setstate(R0); return m.finish(name, sharp=60)

mod_pad('MOD_GiantPad', RD, depth=0.56, half=0.95, ring=True, nv=9)
mod_pond(); mod_bed(); mod_ripples()
mod_pad('MOD_Pad_A', 2.2, depth=0.6, half=0.5, zl=0.05, th=0.13, lip=0.12, nv=7, seg=64)
mod_pad('MOD_Pad_B', 2.7, depth=0.75, half=0.6, zl=0.05, th=0.13, lip=0.13, nv=8, seg=72, top='pad_alt')
mod_pad('MOD_Pad_C', 1.6, zl=0.04, th=0.11, lip=0.1, nv=6, seg=56, top='pad_alt')
mod_pad('MOD_Pad_D', 1.7, depth=0.5, half=0.42, zl=0.04, th=0.11, lip=0.1, nv=6, seg=56)
mod_pad('MOD_Pad_E', 1.25, depth=0.38, half=0.3, zl=0.04, th=0.1, lip=0.09, nv=5, seg=48, top='pad_alt')
mod_ring_small('MOD_RingS', 3.25); mod_ring_small('MOD_RingXS', 2.15)
mod_lotus('MOD_Lotus', 1.0); mod_bud('MOD_LotusBud', 1.0); mod_frog()
mod_reeds('MOD_Reeds_A', 3, 11, 3, 3.8); mod_reeds('MOD_Reeds_B', 11, 10, 3, 3.6); mod_reeds('MOD_Reeds_C', 5, 8, 2, 3.0)
mod_stone('MOD_Stone_A', 1, 1.1); mod_stone('MOD_Stone_B', 2, 0.85)

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_PondBed', 'POND_Bed', c='ENV_POND')
place('MOD_PondWater', 'POND_Water', c='ENV_POND')
place('MOD_RippleA', 'RIPPLE_A', c='ENV_POND'); place('MOD_RippleB', 'RIPPLE_B', c='ENV_POND')
for i, (cx, cy, L, w, a) in enumerate(STREAKS): place('MOD_Streak%d' % i, 'STREAK_%d' % i, (cx, cy, 0), c='ENV_POND')
place('MOD_GiantPad', 'PAD_Giant', rz=NOTCH_DIR, c='ENV_PAD')

PZ = WZ + 0.05              # small pads: top 5 cm above the water
def float_root(name, x, y, rz=0.0):
    r = bpy.data.objects.new(name, None); CN['ENV_FLOAT'].objects.link(r)
    r.empty_display_type = 'CIRCLE'; r.empty_display_size = 1.5; r.location = (x, y, 0); r.rotation_euler.z = math.radians(rz); return r
def child(root, mod, name, loc=(0, 0, 0), rz=0.0, s=1.0):
    o = place(mod, name, loc, rz, s, c='ENV_FLOAT'); o.parent = root; return o
fp = float_root('FLOAT_Pad_0', -9.6, 2.6, 150); child(fp, 'MOD_Pad_A', 'FLOAT_Pad_0_Pad', (0, 0, PZ))
fp = float_root('FLOAT_Pad_1', -11.8, -2.6, 20); child(fp, 'MOD_Pad_C', 'FLOAT_Pad_1_Pad', (0, 0, PZ))
fp = float_root('FLOAT_Pad_2', -7.4, 10.4, 250); child(fp, 'MOD_Pad_D', 'FLOAT_Pad_2_Pad', (0, 0, PZ))
fp = float_root('FLOAT_Pad_3', 4.8, 8.6, 100); child(fp, 'MOD_Pad_E', 'FLOAT_Pad_3_Pad', (0, 0, PZ))
fl = float_root('FLOAT_Lotus_0', 10.6, 6.4, 205); child(fl, 'MOD_Pad_B', 'FLOAT_Lotus_0_Pad', (0, 0, PZ))
child(fl, 'MOD_Lotus', 'FLOAT_Lotus_0_Flower', (0.5, 0.3, PZ), 0, 1.15)
child(fl, 'MOD_RingS', 'FLOAT_Lotus_0_Ripple', (0, 0, 0))
fb = float_root('FLOAT_Lotus_1', -7.0, -2.3, 0); child(fb, 'MOD_Lotus', 'FLOAT_Lotus_1_Flower', (0, 0, WZ - 0.08), 30, 0.75)
child(fb, 'MOD_RingXS', 'FLOAT_Lotus_1_Ripple', (0, 0, 0), 0, 0.55)
ff = float_root('FLOAT_Frog', 8.4, -2.4, 300); child(ff, 'MOD_Pad_C', 'FLOAT_Frog_Pad', (0, 0, PZ), 0, 0.9)
child(ff, 'MOD_Frog', 'FLOAT_Frog_Frog', (0.1, 0.1, PZ + 0.04), 50, 0.95)

place('MOD_LotusBud', 'PROP_LotusBud', (12.6, 3.6, WZ + 0.3), rz=10, s=0.8, c='ENV_PROPS')
place('MOD_Reeds_A', 'PROP_Reeds_TL', (-12.0, 9.0, 0), rz=0, c='ENV_PROPS')
place('MOD_Reeds_B', 'PROP_Reeds_TR', (12.8, 8.8, 0), rz=40, c='ENV_PROPS')
place('MOD_Reeds_C', 'PROP_Reeds_BL', (-7.7, -5.0, 0), rz=80, c='ENV_PROPS')
place('MOD_Reeds_C', 'PROP_Reeds_BR', (8.3, -5.0, 0), rz=200, s=(0.9, 0.9, 0.85), c='ENV_PROPS')
place('MOD_Stone_A', 'PROP_Stone_0', (-3.6, 8.6, WZ + 0.1), rz=10, c='ENV_PROPS')
place('MOD_Stone_B', 'PROP_Stone_1', (-1.6, 10.0, WZ + 0.08), rz=70, c='ENV_PROPS')

# =====================================================================================================================
# characters: two soft sumos (sumo_game.glb, 'stance' frame 1), game x = -1.5 / +1.5, facing each other
# =====================================================================================================================
SUMO_SCALE = float(dict(a.split('=') for a in sys.argv if a.startswith('ss=')).get('ss', 1.5))   # 1.15 (game arch scale) read too small next to the in-game screenshot; 1.5 matches its sumo-to-ring ratio (~2.2 m tall)
def import_sumo(tag, x, face_deg, mawashi_hex):
    before = set(bpy.data.objects); mats_before = set(bpy.data.materials)
    bpy.ops.import_scene.gltf(filepath=SUMO_GLB)
    imp = [o for o in bpy.data.objects if o not in before]
    for o in imp:
        for c in list(o.users_collection): c.objects.unlink(o)
        CN['CHARACTERS'].objects.link(o)
    for o in list(imp):
        if o.type == 'MESH' and o.name.startswith('Icosphere'): imp.remove(o); bpy.data.objects.remove(o)
    rig = next(o for o in imp if o.type == 'ARMATURE'); rig.name = 'CHR_Rig_' + tag
    body = next(o for o in imp if o.type == 'MESH'); body.name = 'CHR_Sumo_' + tag
    root = bpy.data.objects.new('CHR_' + tag, None); CN['CHARACTERS'].objects.link(root)
    for o in imp:
        if o.parent is None: o.parent = root
    root.location = (x, 0, 0); root.rotation_euler.z = math.radians(face_deg); root.scale = (SUMO_SCALE,) * 3
    act = next(a for a in bpy.data.actions if a.name.startswith('stance'))
    rig.animation_data_create(); rig.animation_data.action = act
    # own copies of the materials so each sumo can carry its own mawashi
    for i, m in enumerate(body.data.materials):
        if m is None: continue
        mm = m.copy(); mm.name = m.name.split('.')[0] + '_' + tag; body.data.materials[i] = mm
        b = mm.node_tree.nodes.get('Principled BSDF')
        if not b: continue
        # kkbc_pass PASS 7 material treatment
        if mm.name.startswith('Skin'):
            b.inputs['Roughness'].default_value = 0.78; b.inputs['Specular IOR Level'].default_value = 0.2
            b.inputs['Coat Weight'].default_value = 0.0; b.inputs['Sheen Weight'].default_value = 0.0
            lk = b.inputs['Base Color'].links
            if lk:
                src = lk[0].from_socket; N = mm.node_tree.nodes
                mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
                mx.inputs['B'].default_value = (1.0, 0.9, 0.8, 1); mm.node_tree.links.new(src, mx.inputs['A']); mm.node_tree.links.new(mx.outputs['Result'], b.inputs['Base Color'])
            else: b.inputs['Base Color'].default_value = (*hexlin('f2b48e'), 1)
        elif mm.name.startswith('Mawashi'):
            b.inputs['Base Color'].default_value = (*hexlin(mawashi_hex), 1); b.inputs['Roughness'].default_value = 0.9
            b.inputs['Specular IOR Level'].default_value = 0.15
        elif mm.name.startswith(('Hair', 'Ink')):
            b.inputs['Roughness'].default_value = 0.6; b.inputs['Base Color'].default_value = (*hexlin('262230'), 1)
    # kkbc_flat_render softening: weld, smooth, corrective smooth
    bm = bmesh.new(); bm.from_mesh(body.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005); bm.to_mesh(body.data); bm.free()
    body.data.shade_smooth()
    cs = body.modifiers.new('soften', 'CORRECTIVE_SMOOTH'); cs.iterations = 30; cs.factor = 1.0; cs.rest_source = 'ORCO'; cs.smooth_type = 'LENGTH_WEIGHTED'
    sm = body.modifiers.new('round', 'SMOOTH'); sm.factor = 0.5; sm.iterations = 6
    return root
FACE = float(dict(a.split('=') for a in sys.argv if a.startswith('face=')).get('face', 90)) if any(a.startswith('face=') for a in sys.argv) else 90.0
import_sumo('Red', -1.5, FACE, 'c8392f')
import_sumo('Navy', 1.5, FACE + 180, '1f3a8a')
scn.frame_start = scn.frame_end = scn.frame_current = 1

# =====================================================================================================================
# light + world (option-2 pipeline: kkbc_segment world, kkbc_pass PASS 1 values, kkbc_flat_render sun angle)
# =====================================================================================================================
TGT = Vector((0, 0.15, 0.2))
sd = bpy.data.lights.new('Sun', 'SUN'); sd.energy = 4.4; sd.color = hexlin('ffe6c8'); sd.angle = math.radians(5)
sun = bpy.data.objects.new('LGT_Sun', sd); CN['LIGHTING'].objects.link(sun)
SUN_DIR = Vector((-7, -9, 17)).normalized()                     # game (-7, 17, 9) from the target
sun.location = TGT + SUN_DIR * 20; sun.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new('World_Game'); scn.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); mr = nt.nodes.new('ShaderNodeMapRange')
mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
mix.inputs['A'].default_value = (*hexlin('d9c2a4'), 1); mix.inputs['B'].default_value = (*hexlin('a9caf0'), 1)
hemi = nt.nodes.new('ShaderNodeBackground'); hemi.inputs['Strength'].default_value = 0.75; hemi.name = 'Hemi'
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Color'].default_value = (*hexlin('a9d6f5'), 1); bg.inputs['Strength'].default_value = 1.0; bg.name = 'SkyBG'
lp = nt.nodes.new('ShaderNodeLightPath'); ms = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes.new('ShaderNodeOutputWorld')
L = nt.links.new
L(tc.outputs['Generated'], sep.inputs[0]); L(sep.outputs['Z'], mr.inputs['Value']); L(mr.outputs['Result'], mix.inputs['Factor'])
L(mix.outputs['Result'], hemi.inputs['Color']); L(hemi.outputs[0], ms.inputs[1]); L(bg.outputs[0], ms.inputs[2])
L(lp.outputs['Is Camera Ray'], ms.inputs['Fac']); L(ms.outputs[0], out.inputs['Surface'])

# ---- versus game camera: game pos (0, 14.35, 13.93) -> lookAt (0, 0.2, -0.15), vfov 34, 16:9
cd = bpy.data.cameras.new('VersusCam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(34); cd.clip_start = 0.1; cd.clip_end = 200
cam = bpy.data.objects.new('CAM_Versus', cd); CN['CAMERAS'].objects.link(cam)
cam.location = (0, -13.93, 14.35); cam.rotation_euler = (TGT - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.camera = cam
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = 50 if LOWRES else 100

scn.render.engine = 'CYCLES'; cy = scn.cycles
cy.device = 'CPU'; cy.samples = 32 if LOWRES else 96; cy.use_adaptive_sampling = True; cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 4; cy.diffuse_bounces = 1; cy.glossy_bounces = 1; cy.transmission_bounces = 2; cy.transparent_max_bounces = 8
vl = scn.view_layers[0]
for p in ('use_pass_diffuse_direct', 'use_pass_diffuse_indirect', 'use_pass_diffuse_color', 'use_pass_glossy_direct', 'use_pass_glossy_indirect',
          'use_pass_glossy_color', 'use_pass_transmission_direct', 'use_pass_transmission_indirect', 'use_pass_transmission_color',
          'use_pass_emit', 'use_pass_environment', 'use_pass_ambient_occlusion', 'use_pass_normal'):
    setattr(vl, p, True)
scn.render.film_transparent = False
scn.view_settings.view_transform = 'Standard'; scn.view_settings.look = 'None'; scn.view_settings.exposure = 0
scn.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'; scn.render.image_settings.color_depth = '32'

# =====================================================================================================================
# export (stage only) + save + render
# =====================================================================================================================
def tris(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type == 'MESH':
            e = o.evaluated_get(dg); m = e.to_mesh(); m.calc_loop_triangles(); n += len(m.loop_triangles); e.to_mesh_clear()
    return n
env = [o for c in CN.values() if c.name.startswith('ENV_') for o in c.objects]
for m in (M_KIT, M_GW):   # glTF can't follow the per-object variation node: link the palette straight to Base Color
    N = m.node_tree.nodes; m.node_tree.links.new(N['Palette'].outputs['Color'], N['Principled BSDF'].inputs['Base Color'])
bpy.ops.object.select_all(action='DESELECT')
for o in env: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT + '/lily_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
for o in bpy.data.objects:            # water lets the light through (flat look): no shadows from the surface / ripples
    if o.name.startswith(('POND_Water', 'RIPPLE_', 'STREAK_')) or o.name.endswith('_Ripple'): o.visible_shadow = False
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/lily_kit.blend')
if not NORENDER:
    exr = OUT + '/lily_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/lily_gamecam.png'] + comp, check=True)
print('DONE')
