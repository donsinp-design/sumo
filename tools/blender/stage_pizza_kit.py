# Giant pizza (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as stage_dohyo_kit.py.
#   <bl python> tools/blender/stage_pizza_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vspizza): pizza_kit.blend, pizza_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         pizza_palette.png, pizza_gamecam.exr (light passes) -> pizza_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the dohyo kit's, with the dohyo-only swatches
# (clay, straw, gravel, torii, tassels, ...) repurposed for crust, sauce, cheese, pepperoni and the gingham cloth.
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, fighting surface at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vspizza'
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
CN = {n: coll(n) for n in ('ENV_GROUND', 'ENV_PIZZA', 'ENV_TOPPINGS', 'ENV_PROPS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

# =====================================================================================================================
# palette + master material (dohyo kit PAL; dohyo-only slots repurposed for the pizza)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('cloth_red', 'e08a7e'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('crust', 'e3ad6c'), ('crust_dk', 'd09658'), ('cheese', 'f5d47e'), ('chilli', 'e0603e'), ('cloth', 'f3e8d4'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('sauce', 'e06a4c'), ('cheese_lt', 'f8dc94'), ('cloth_mid', 'efc0b2'), ('crust_lt', 'eec184'), ('stone', 'e9e1d1'), ('pepperoni', 'c24f42'), ('purple', '8c6aa8'),
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
img.filepath_raw = OUT + '/pizza_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
# dimensions
# =====================================================================================================================
RING_R = 4.6               # playable radius
SAUCE_R = 5.75             # sauce disc (runs under the crust)
CR_R = 6.0                 # crust tube centre radius
CR_W, CR_H = 0.72, 0.5     # crust half-width / half-height (inner edge ~5.3, top ~+0.55)
BASE_Z = -0.32             # underside of the pizza = top of the board
BOARD_R, BOARD_H = 7.35, 0.42
TBL = BASE_Z - BOARD_H     # tablecloth surface

# ---- pizza ----------------------------------------------------------------------------------------------------------
def mod_base():
    m = MB(); m.lathe([(SAUCE_R + 0.2, BASE_Z), (SAUCE_R + 0.2, -0.12), (SAUCE_R, -0.04), (0.0, -0.04)], 'sauce', 96)
    return m.finish('MOD_PizzaBase')
def mod_crust():
    """one chunky, puffy rim: an elliptic tube around the pizza whose width and height swell in soft lumps."""
    m = MB(); bm = m.bm; b = m._begin(); NA, NQ = 160, 18; rings = []
    R = random.Random(11); ph = [R.uniform(0, 6.28) for _ in range(4)]
    for i in range(NA):
        a = 2 * math.pi * i / NA
        lump = 0.55 * math.sin(7 * a + ph[0]) + 0.3 * math.sin(11 * a + ph[1]) + 0.25 * math.sin(17 * a + ph[2]) + 0.15 * math.sin(3 * a + ph[3])
        w = CR_W * (1 + 0.07 * lump); h = CR_H * (1 + 0.12 * lump); cz = BASE_Z + h * 0.92
        rg = []
        for q in range(NQ):
            t = 2 * math.pi * q / NQ
            dr, dz = math.cos(t), math.sin(t)
            if dz < 0: dz *= 0.92; dr *= 1.0
            # flatten the underside onto the board
            z = max(cz + h * dz, BASE_Z)
            r = CR_R + w * dr * (1.0 if dr > 0 else 0.95)
            rg.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(rg)
    for i in range(NA):
        A, B = rings[i], rings[(i + 1) % NA]
        for q in range(NQ):
            q1 = (q + 1) % NQ; bm.faces.new((A[q], B[q], B[q1], A[q1]))
    m._end(b, 'crust')
    me = m.finish('MOD_Crust', sharp=80)
    paint_up(me, 'crust_lt', nz=0.8, zmin=BASE_Z + 0.5)
    return me
def mod_cheese():
    """the melted cheese pool: one flat soft-edged shape that stops just inside the ring line, so a band of sauce marks the ring."""
    m = MB(); n = 120; R = random.Random(5); ph = [R.uniform(0, 6.28) for _ in range(4)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 4.3 + 0.16 * math.sin(6 * a + ph[0]) + 0.1 * math.sin(9 * a + ph[1]) + 0.07 * math.sin(14 * a + ph[2])
        pts.append((r * math.cos(a), r * math.sin(a)))
    m.prism(pts, -0.09, 0.0, 'cheese', bev=0.035)
    return m.finish('MOD_Cheese')
def mod_patch(k, col, r, z0, z1, amp=0.18, n=18):
    m = MB(); m.prism(blob(random.Random(40 + k), r, n, amp), z0, z1, col, bev=min(0.03, (z1 - z0) * 0.45))
    return m.finish('MOD_Patch_%s_%d' % (col, k))
def mod_pepperoni():
    """matte, flat, soft-edged slice."""
    m = MB(); m.cyl(0, 0, 0.0, 0.52, 0.09, 'pepperoni', 28, bev=0.035, bseg=3)
    return m.finish('MOD_Pepperoni')
def mod_basil(k):
    """one fat basil leaf: flat pointed ellipse, slightly domed, with a lighter half for the midrib fold."""
    m = MB(); n = 20; L, Wd = 0.72, 0.36; pts = []
    for i in range(n):
        t = 2 * math.pi * i / n; x = L * math.cos(t); y = Wd * math.sin(t) * (1 - 0.35 * (x / L)) * (0.55 + 0.45 * abs(math.sin(t)) ** 0.3)
        pts.append((x, y))
    m.prism(pts, 0.0, 0.06, 'leaf', bev=0.025)
    me = m.finish('MOD_Basil_%d' % k)
    uvl = me.uv_layers['PAL']; u = swuv('leaf_lt')
    for p in me.polygons:
        if p.center.y > 0.03 and p.normal.z > 0.5:
            for li in p.loop_indices: uvl.data[li].uv = u
    return me
# ---- board + table --------------------------------------------------------------------------------------------------
def mod_board():
    m = MB()
    m.lathe([(BOARD_R - 0.1, TBL), (BOARD_R, TBL + 0.1), (BOARD_R, BASE_Z - 0.1), (BOARD_R - 0.12, BASE_Z), (0.0, BASE_Z)], 'wood_dk', 96)
    # handle with a hanging hole, pointing to the back-left
    b = m._begin(); bm = m.bm; n = 28; pts = []
    for i in range(n):
        t = 2 * math.pi * i / n; pts.append((math.cos(t) * 1.25, math.sin(t) * 1.05))
    lo = [bm.verts.new((x + BOARD_R + 0.55, y, TBL)) for x, y in pts]
    hi = [bm.verts.new((x + BOARD_R + 0.55, y, BASE_Z)) for x, y in pts]
    bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
    for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    m._end(b, 'wood_dk', 0.08, 2, ang=30)
    m.box(BOARD_R - 1.0, BOARD_R + 0.4, -0.75, 0.75, TBL, BASE_Z, 'wood_dk', 0.0)                   # neck into the round
    m.cyl(BOARD_R + 0.95, 0, BASE_Z + 0.002, 0.36, 0.01, 'wood_dk', 20)                            # hole (just a darker disc)
    me = m.finish('MOD_Board', sharp=50)
    paint_up(me, 'wood', nz=0.97, zmin=BASE_Z - 0.05)
    uvl = me.uv_layers['PAL']; u = swuv('wood_dk')
    for p in me.polygons:
        if p.center.z > BASE_Z and (Vector((p.center.x, p.center.y)) - Vector((BOARD_R + 0.95, 0))).length < 0.37:
            for li in p.loop_indices: uvl.data[li].uv = u
    return me
CHK = 2.2                  # gingham cell
def mod_cloth():
    """gingham tablecloth as flat-coloured quads: cream / pink (one stripe) / soft red (both stripes)."""
    m = MB(); bm = m.bm; b = m._begin()
    X0, X1, Y0, Y1 = -13, 13, -6, 12        # in cells
    vs = {}
    for i in range(X0, X1 + 1):
        for j in range(Y0, Y1 + 1): vs[i, j] = bm.verts.new((i * CHK - CHK / 2, j * CHK - CHK / 2, TBL))
    cols = {}
    for i in range(X0, X1):
        for j in range(Y0, Y1):
            f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1])); cols[f] = ('cloth', 'cloth_mid', 'cloth_red')[(i % 2) + (j % 2)]
    m._end(b, 'cloth', smooth=False)
    for f, c in cols.items():
        u = swuv(c)
        for l in f.loops: l[m.uv].uv = u
    return m.finish('MOD_Cloth')
def mod_dish():
    """little ceramic dish of chilli flakes: a fat bowl with a soft heap."""
    m = MB()
    m.lathe([(0.0, 0.0), (0.95, 0.0), (1.35, 0.22), (1.55, 0.62), (1.42, 0.7), (1.2, 0.44), (0.0, 0.44)], 'dusty_blue', 28)
    m.ico(0, 0, 0.4, 1.12, 'chilli', 3, (1, 1, 0.62), jit=0.04)                       # a soft heap of flakes
    for k in range(7):                                                               # a few chunky flakes on top
        a = k * 0.9 + 0.4; rr = 0.35 + 0.25 * (k % 3); z = 0.4 + 0.66 * math.sqrt(max(0.0, 1 - (rr / 1.12) ** 2))
        m.ico(rr * math.cos(a), rr * math.sin(a), z, 0.2, ('red_dk', 'orange', 'red')[k % 3], 1, (1.5, 1, 0.45), M=Rz(k * 47))
    return m.finish('MOD_ChilliDish', sharp=60)
def mod_napkin():
    """folded napkin: two soft stacked layers and a turned-back corner."""
    m = MB()
    m.box(-2.0, 2.0, -1.45, 1.45, 0.0, 0.2, 'sage', 0.08, 3)
    m.box(-1.85, 1.85, -1.3, 1.3, 0.2, 0.38, 'sage', 0.08, 3)
    m.box(-1.85, 1.85, -0.22, 0.22, 0.38, 0.44, 'teal_muted', 0.03)                          # one soft stripe
    return m.finish('MOD_Napkin', sharp=60)

for f in (mod_base, mod_crust, mod_cheese, mod_pepperoni, mod_board, mod_cloth, mod_dish, mod_napkin): f()
for k in range(3): mod_basil(k)
for k in range(6): mod_patch(k, 'cheese_lt', 0.7 + 0.12 * k, -0.02, 0.012)
for k in range(4): mod_patch(10 + k, 'cheese', 0.42 + 0.06 * k, -0.06, -0.01)       # drips of cheese on the sauce band
for k in range(3): mod_patch(20 + k, 'sauce', 0.38 + 0.08 * k, -0.02, 0.008, 0.22)   # sauce peeking through the cheese

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Cloth', 'TABLE_Cloth', c='ENV_GROUND')
place('MOD_Board', 'TABLE_Board', rz=145, c='ENV_PIZZA')
place('MOD_PizzaBase', 'PIZZA_Base', c='ENV_PIZZA')
place('MOD_Crust', 'PIZZA_Crust', c='ENV_PIZZA')
place('MOD_Cheese', 'PIZZA_Cheese', c='ENV_PIZZA')
# lighter melted patches on the cheese, kept off the two start marks (x = +-1.5)
for k, (x, y, r) in enumerate(((-0.2, 2.6, 20), (2.9, 1.2, 70), (-3.0, -1.0, 140), (0.6, -2.7, 200), (-2.4, 2.4, 260), (3.0, -1.9, 320))):
    place('MOD_Patch_cheese_lt_%d' % k, nm('PIZZA_CheeseMelt'), (x, y, 0.0), rz=r, c='ENV_TOPPINGS')
for k, a in enumerate((35, 128, 214, 300)):
    rr = 4.65 + 0.05 * k; place('MOD_Patch_cheese_%d' % (10 + k), nm('PIZZA_CheeseDrip'), (rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a)), 0.0), rz=a * 2, c='ENV_TOPPINGS')
for k, (x, y) in enumerate(((1.4, 3.1), (-3.6, 0.8), (1.0, -3.6))):
    place('MOD_Patch_sauce_%d' % (20 + k), nm('PIZZA_SauceSpot'), (x, y, 0.0), rz=k * 70, c='ENV_TOPPINGS')
PEP = [(-2.75, 2.75), (2.85, 2.6), (-3.55, -1.45), (3.55, -0.75), (-1.55, -3.55), (1.95, -3.25), (-0.95, 3.75), (-3.85, 0.55), (3.8, 0.85)]
for x, y in PEP:
    place('MOD_Pepperoni', nm('PIZZA_Pepperoni'), (x, y, 0.035), rz=RNG.uniform(0, 360), s=RNG.uniform(0.93, 1.07), c='ENV_TOPPINGS')
for k, (x, y, r) in enumerate(((0.4, 2.75, 20), (-3.0, 1.55, -60), (-2.3, -2.6, 110), (2.6, -1.6, 160))):
    place('MOD_Basil_%d' % (k % 3), nm('PIZZA_Basil'), (x, y, 0.0), rz=r, c='ENV_TOPPINGS')
# table props (only where the camera sees them): chilli flakes front-right, napkin left
place('MOD_ChilliDish', 'TABLE_ChilliDish', (9.4, 2.6, TBL), c='ENV_PROPS')
place('MOD_Napkin', 'TABLE_Napkin', (-10.0, 1.4, TBL), rz=-14, c='ENV_PROPS')

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
bpy.ops.export_scene.gltf(filepath=OUT + '/pizza_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/pizza_kit.blend')
if not NORENDER:
    exr = OUT + '/pizza_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/pizza_gamecam.png'] + comp, check=True)
print('DONE')
