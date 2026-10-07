# Kaiten-zushi "sushi train" (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_sushi_kit.py.
#   <bl python> tools/blender/stage_sushi_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vssushi): sushi_kit.blend, sushi_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         sushi_palette.png, sushi_gamecam.exr (light passes) -> sushi_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo/pizza kits: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the dohyo kit's, with the dohyo-only swatches
# repurposed (as the pizza did) for rice, salmon, tuna, nori, hinoki, porcelain and the faint glaze motif.
# The four plates riding the belt are separate root empties RIDE_0..RIDE_3 (plate + sushi as children) at
# game x = -20.5, -10.6, 10.6, 20.5, z = 0, standing on the belt (game y = -0.62); the game slides them along x.
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, fighting surface at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vssushi'
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
CN = {n: coll(n) for n in ('ENV_GROUND', 'ENV_BELT', 'ENV_PLATE', 'ENV_RIDES', 'ENV_PROPS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

# =====================================================================================================================
# palette + master material (dohyo kit PAL; dohyo-only slots repurposed for the sushi bar, as the pizza did)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('yellow_lt', 'f6dc8e'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('rice', 'f6f1e6'), ('rice_dk', 'e6dccb'), ('salmon', 'f2976a'), ('salmon_lt', 'f9c9a6'), ('hinoki', 'e8d2a8'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('tuna', 'd95e57'), ('nori', '56665e'), ('hinoki_dk', 'cfb084'), ('porcelain', 'f4f0e8'), ('stone', 'e9e1d1'), ('motif', 'eeeae3'), ('purple', '8c6aa8'),
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
img.filepath_raw = OUT + '/sushi_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
# dimensions (game stages.js 'sushi': plate RD = RING_R + 0.7, plate 0.32 thick + 0.3 foot -> belt at -0.62)
# =====================================================================================================================
RING_R = 4.6               # playable radius
RD = RING_R + 0.7          # giant plate radius (5.3)
BY = -0.62                 # top of the belt slats (the giant plate's foot and the riding plates stand here)
BW = 12.4                  # belt width (game z / blender y)
SLAT = 1.7                 # slat pitch along x
CT = -0.3                  # counter top
CY = BW / 2 + 0.75         # counter edge (both sides of the belt)
RIDE_X = (-20.5, -10.6, 10.6, 20.5)

def mod_draped(name, L, Wd, H, col, drape=0.22, nx=14, stripe=None, stripe_every=3):
    """a slab of fish draped over the rice: rounded-rectangle section swept along x, ends tucked down."""
    m = MB(); bm = m.bm; b = m._begin(); rings = []
    sec = []
    nq = 16
    for q in range(nq):                                     # superellipse cross-section (soft pillow)
        t = 2 * math.pi * q / nq; c, s_ = math.cos(t), math.sin(t)
        sec.append((Wd / 2 * math.copysign(abs(c) ** 0.55, c), H / 2 * math.copysign(abs(s_) ** 0.7, s_)))
    for i in range(nx + 1):
        u = -1 + 2 * i / nx; x = u * L / 2
        dz = -drape * u * u                                  # drape down at both ends
        taper = 1 - 0.12 * u * u                             # ends a touch narrower
        rings.append([bm.verts.new((x, y * taper, z * (1 - 0.15 * u * u) + dz)) for y, z in sec])
    for i in range(nx):
        A, B_ = rings[i], rings[i + 1]
        for q in range(nq):
            q1 = (q + 1) % nq; bm.faces.new((A[q], B_[q], B_[q1], A[q1]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    m._end(b, col)
    me = m.finish(name, sharp=70)
    if stripe:                                               # soft fat-stripes across the top (salmon)
        uvl = me.uv_layers['PAL']; u_ = swuv(stripe); seg = L / nx
        for p in me.polygons:
            k = int((p.center.x + L / 2) / seg)
            if p.normal.z > 0.2 and k % stripe_every == 1 and 0 < k < nx - 1:
                for li in p.loop_indices: uvl.data[li].uv = u_
    return me

# ---- giant plate ----------------------------------------------------------------------------------------------------
def mod_plate():
    m = MB()
    prof = [(0.0, -0.42), (3.55, -0.42), (3.6, BY), (3.98, BY), (4.06, -0.42), (4.9, -0.27), (5.25, -0.12), (5.38, -0.02),
            (5.36, 0.05), (5.27, 0.085), (5.16, 0.075), (5.0, 0.055), (4.82, 0.03), (4.66, 0.006), (4.62, 0.0), (3.0, 0.0), (0.0, 0.0)]
    m.lathe(prof, 'porcelain', 128)
    me = m.finish('MOD_GiantPlate', sharp=40)
    uvl = me.uv_layers['PAL']; u = swuv('navy')
    for p in me.polygons:                                    # the chunky indigo rim band on top
        r = Vector((p.center.x, p.center.y)).length
        if p.normal.z > 0.3 and 4.6 < r < 5.2 and p.center.z > -0.01:
            for li in p.loop_indices: uvl.data[li].uv = u
    return me
def mod_kotobuki():
    """a big faint 寿 glazed into the well: one flat filled glyph, a shade off the porcelain."""
    fnt = bpy.data.fonts.load('/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
    cu = bpy.data.curves.new('kotobuki', 'FONT'); cu.body = '寿'; cu.font = fnt; cu.size = 6.4; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    cu.fill_mode = 'BOTH'; cu.resolution_u = 4
    ob = bpy.data.objects.new('tmp_kotobuki', cu); ROOT.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); me0 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    m = MB(); b = m._begin(); m.bm.from_mesh(me0); bpy.data.meshes.remove(me0)
    bmesh.ops.remove_doubles(m.bm, verts=m.bm.verts, dist=0.001)
    bmesh.ops.transform(m.bm, matrix=T(0, 0.25, 0.008), verts=m.bm.verts)
    for f in m.bm.faces:
        if f.normal.z < 0: f.normal_flip()
    m._end(b, 'motif', smooth=False)
    return m.finish('MOD_Kotobuki')

# ---- belt -----------------------------------------------------------------------------------------------------------
def mod_belt():
    m = MB()
    n = 50
    for k in range(n):
        x = (k - n / 2 + 0.5) * SLAT
        m.box(x - SLAT / 2 + 0.05, x + SLAT / 2 - 0.05, -BW / 2, BW / 2, BY - 0.16, BY, 'pave', 0.08, 2)
    m.box(-n * SLAT / 2, n * SLAT / 2, -BW / 2, BW / 2, BY - 0.4, BY - 0.17, 'concrete_dk', 0.0)          # channel floor (seen in the gaps)
    for sgn in (-1, 1):                                                                           # rails either side
        y0 = sgn * (BW / 2 + 0.02); y1 = sgn * (BW / 2 + 0.62)
        m.box(-n * SLAT / 2, n * SLAT / 2, min(y0, y1), max(y0, y1), BY - 0.45, CT + 0.14, 'offwhite', 0.12, 3)
    return m.finish('MOD_Belt', sharp=50)
def mod_counter():
    """pale hinoki counters both sides of the belt: long planks, a darker seam between them."""
    m = MB(); X = 45
    for sgn in (-1, 1):
        ya, yb = sgn * CY, sgn * (CY + 26)
        m.box(-X, X, min(ya, yb), max(ya, yb), CT - 1.4, CT - 0.04, 'hinoki_dk', 0.0)
        y0 = CY
        for k, (w, col) in enumerate(((2.6, 'hinoki'), (3.4, 'cream2'), (3.0, 'hinoki'), (4.0, 'cream2'), (14.0, 'hinoki'))):
            a, bb = sgn * (y0 + 0.04), sgn * (y0 + w - 0.04); y0 += w
            m.box(-X, X, min(a, bb), max(a, bb), CT - 0.3, CT, col, 0.05 if k else 0.12, 2)
    return m.finish('MOD_Counter', sharp=50)

# ---- riding plates + sushi -------------------------------------------------------------------------------------------
PR = 2.75                  # riding plate radius
PTOP = 0.36                # riding plate well height above the belt
def mod_ride_plate(rim, well):
    m = MB()
    m.lathe([(0.0, 0.1), (1.7, 0.1), (1.74, 0.0), (1.98, 0.0), (2.05, 0.12), (2.62, 0.3), (2.76, 0.4), (2.72, 0.46), (2.58, 0.47),
             (2.3, 0.4), (2.2, PTOP), (0.0, PTOP)], rim, 48)
    me = m.finish('MOD_RidePlate_' + rim, sharp=40)
    paint_up(me, well, nz=0.97, zmin=PTOP - 0.01)
    return me
def mod_rice(name, L=1.75, Wd=1.0, H=0.62):
    m = MB(); m.box(-L / 2, L / 2, -Wd / 2, Wd / 2, 0.0, H, 'rice', 0.3, 3)
    return m.finish(name, sharp=60)
def mod_tamago():
    m = MB()
    m.box(-1.0, 1.0, -0.56, 0.56, 0.0, 0.62, 'rice', 0.28, 3)
    m.box(-1.08, 1.08, -0.6, 0.6, 0.55, 1.0, 'acc_yellow', 0.12, 2)
    m.box(-0.24, 0.24, -0.64, 0.64, 0.25, 1.06, 'nori', 0.07, 2)           # nori belt
    return m.finish('MOD_Tamago', sharp=50)
def mod_gunkan():
    m = MB(); b = m._begin(); bm = m.bm; n = 24; pts = [(1.0 * math.cos(2 * math.pi * i / n), 0.68 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    m.prism(pts, 0.0, 0.82, 'nori', bev=0.06)
    m.prism([(x * 0.9, y * 0.86) for x, y in pts], 0.5, 0.74, 'rice', bev=0.03)
    R = random.Random(3)
    for k in range(13):                                                        # ikura pearls heaped on top
        a = k * 2.4; rr = 0.62 * math.sqrt((k + 0.5) / 13)
        m.ico(rr * math.cos(a) * 1.0, rr * math.sin(a) * 0.62, 0.86 + 0.08 * (1 - rr / 0.62), 0.2, 'orange', 1)
    return m.finish('MOD_Gunkan', sharp=60)
def mod_maki(fill):
    m = MB()
    m.cyl(0, 0, 0.42, 0.62, 0.84, 'nori', 24, bev=0.07, bseg=2)
    m.cyl(0, 0, 0.845, 0.5, 0.02, 'rice', 24)
    m.cyl(0, 0, 0.86, 0.19, 0.02, fill, 16)
    return m.finish('MOD_Maki_' + fill, sharp=50)

# ---- counter props ----------------------------------------------------------------------------------------------------
def mod_teacup():
    m = MB()
    m.lathe([(0.0, 0.0), (0.62, 0.0), (0.72, 0.08), (0.8, 1.5), (0.72, 1.55), (0.66, 1.3), (0.0, 1.3)], 'sage', 28, bev=0.04)
    m.lathe([(0.0, 0.55), (0.76, 0.55), (0.785, 0.6), (0.785, 0.83), (0.77, 0.88), (0.0, 0.88)], 'teal_muted', 28)   # one soft band
    m.cyl(0, 0, 1.31, 0.665, 0.02, 'leaf_lt', 28)                                                  # green tea
    return m.finish('MOD_Teacup', sharp=50)
def mod_soy():
    m = MB()
    m.lathe([(0.0, 0.0), (0.7, 0.0), (1.05, 0.14), (1.12, 0.26), (1.02, 0.3), (0.86, 0.16), (0.0, 0.16)], 'offwhite', 28)
    m.cyl(0, 0, 0.17, 0.82, 0.02, 'interior', 28)                                                  # soy (warm brown, never black)
    m.ico(0.62, 0.55, 0.3, 0.24, 'leaf_lt', 2, (1, 1, 0.75))                                      # dab of wasabi on the edge
    return m.finish('MOD_Soy', sharp=50)
def mod_gari():
    m = MB()
    m.lathe([(0.0, 0.0), (0.6, 0.0), (0.95, 0.12), (1.05, 0.3), (0.94, 0.33), (0.78, 0.16), (0.0, 0.16)], 'dusty_blue', 28)
    for k in range(7):                                                                             # a loose rosette of thin pink slices
        a = k * 0.9 + 0.3; rr = 0.1 + 0.42 * (k > 0)
        m.ico(rr * math.cos(a), rr * math.sin(a), 0.26 + 0.1 * (k == 0), 0.36, 'pink_acc' if k in (0, 3) else 'pink', 2, (1.15, 0.7, 0.24), M=Rz(math.degrees(a) + 90) if k else I4)
    return m.finish('MOD_Gari', sharp=60)
def mod_chopsticks():
    m = MB()
    m.box(-0.45, 0.45, -0.22, 0.22, 0.0, 0.28, 'coral', 0.1, 3)                                   # chunky rest
    for dy in (-0.11, 0.11):
        m.box(-1.0, 2.6, dy - 0.075, dy + 0.075, 0.24, 0.38, 'wood_lt', 0.05, 2, M=Ry(-4) @ Rz(-3 if dy < 0 else 3))
    return m.finish('MOD_Chopsticks', sharp=50)

mod_plate(); mod_kotobuki(); mod_belt(); mod_counter()
for rim, well in (('red', 'coral'), ('acc_yellow', 'yellow_lt'), ('blue', 'dusty_blue'), ('green', 'sage')): mod_ride_plate(rim, well)
mod_rice('MOD_Rice'); mod_tamago(); mod_gunkan(); mod_maki('leaf'); mod_maki('tuna')
mod_draped('MOD_FishSalmon', 2.15, 1.12, 0.24, 'salmon', stripe='salmon_lt')
mod_draped('MOD_FishTuna', 2.15, 1.12, 0.26, 'tuna')
mod_teacup(); mod_soy(); mod_gari(); mod_chopsticks()

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Counter', 'COUNTER', c='ENV_GROUND')
place('MOD_Belt', 'BELT', c='ENV_BELT')
place('MOD_GiantPlate', 'PLATE_Giant', c='ENV_PLATE')
place('MOD_Kotobuki', 'PLATE_Kotobuki', c='ENV_PLATE')

def nigiri(parent, fish, x, y, rz):
    M = Matrix.Translation((x, y, PTOP)) @ Rz(rz)
    o = place('MOD_Rice', nm(parent.name + '_Rice'), c='ENV_RIDES'); o.parent = parent; o.matrix_basis = M
    f = place(fish, nm(parent.name + '_Fish'), c='ENV_RIDES'); f.parent = parent; f.matrix_basis = M @ T(0, 0, 0.62 + 0.04)
def item(parent, mod, x, y, rz):
    o = place(mod, nm(parent.name + '_Item'), c='ENV_RIDES'); o.parent = parent; o.matrix_basis = Matrix.Translation((x, y, PTOP)) @ Rz(rz)
MENU = [('green', lambda p: (item(p, 'MOD_Tamago', -0.15, 0.85, 8), item(p, 'MOD_Gunkan', 0.1, -0.8, -6))),
        ('blue', lambda p: (nigiri(p, 'MOD_FishSalmon', 0, 0.68, 6), nigiri(p, 'MOD_FishSalmon', 0, -0.68, -5))),
        ('acc_yellow', lambda p: (nigiri(p, 'MOD_FishTuna', 0, 0.68, -4), nigiri(p, 'MOD_FishTuna', 0, -0.68, 5))),
        ('red', lambda p: (item(p, 'MOD_Maki_leaf', -0.75, 0.62, 0), item(p, 'MOD_Maki_tuna', 0.85, 0.45, 0), item(p, 'MOD_Maki_leaf', 0.0, -0.85, 0)))]
for k, (x, (rim, fill)) in enumerate(zip(RIDE_X, MENU)):
    root = bpy.data.objects.new('RIDE_%d' % k, None); CN['ENV_RIDES'].objects.link(root)
    root.empty_display_type = 'CIRCLE'; root.empty_display_size = PR; root.location = (x, 0, BY)
    pl = place('MOD_RidePlate_' + rim, 'RIDE_%d_Plate' % k, c='ENV_RIDES'); pl.parent = root
    fill(root)

# counter props: back counter only (the camera sees ~y 7..14 there), spaced out, nothing in front of the fight
CZ = CT
PS = 1.7                   # props at the same toy scale as the sushi (a nigiri is ~2.2 long)
place('MOD_Teacup', 'PROP_Teacup', (-10.2, 8.9, CZ), s=PS, c='ENV_PROPS')
place('MOD_Gari', 'PROP_Gari', (-6.4, 9.0, CZ), rz=20, s=PS, c='ENV_PROPS')
place('MOD_Chopsticks', 'PROP_Chopsticks', (5.0, 8.4, CZ), rz=8, s=PS, c='ENV_PROPS')
place('MOD_Soy', 'PROP_Soy', (10.6, 9.6, CZ), rz=-30, s=PS, c='ENV_PROPS')

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
bpy.ops.export_scene.gltf(filepath=OUT + '/sushi_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/sushi_kit.blend')
if not NORENDER:
    exr = OUT + '/sushi_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/sushi_gamecam.png'] + comp, check=True)
print('DONE')
