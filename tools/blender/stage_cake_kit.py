# Giant birthday cake (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py / stage_lily_kit.py.
#   <bl python> tools/blender/stage_cake_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vscake): cake_kit.blend, cake_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         cake_palette.png, cake_gamecam.exr (light passes) -> cake_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the dohyo kit's, with the dohyo-only swatches
# repurposed for frosting, sponge, jam, strawberries, candle flames, the cake stand and the tablecloth.
# The candle flames are separate root objects FLAME_01..FLAME_08 (origin at the flame's foot) so the game can flicker them.
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, frosting top at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vscake'
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
CN = {n: coll(n) for n in ('ENV_GROUND', 'ENV_CAKE', 'ENV_TOPPINGS', 'ENV_PROPS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# =====================================================================================================================
# palette + master material (dohyo kit PAL; dohyo-only slots repurposed for the cake)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('stand', 'c4dbea'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('frost', 'f8eee3'), ('frost_pink', 'f3b9c7'), ('sponge', 'f2d59b'), ('berry', 'e2636b'), ('cloth', 'cfe6d8'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('ring_line', 'ec93ab'), ('flame', 'f9dd84'), ('cloth_dot', 'e2f1e7'), ('mint', 'a8dcc6'), ('stone', 'e9e1d1'), ('jam', 'eda0b0'), ('purple', '8c6aa8'),
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
img.filepath_raw = OUT + '/cake_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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

def sweep(s, prof, angs, col, M=None, smooth=True, closed=False):
    """lathe whose profile may change with the angle: prof(a) -> [(r, z), ...] from the bottom centre round to the top
    centre (same number of points for every angle; r = 0 at either end makes a pole, otherwise that end is capped)."""
    b = s._begin(); bm = s.bm; rings = []
    P = [prof(a) for a in angs]; npf = len(P[0]); na = len(angs)
    poles = {}
    for q in range(npf):
        if all(P[i][q][0] < 1e-6 for i in range(na)):
            poles[q] = bm.verts.new((0, 0, P[0][q][1]))
    for i, a in enumerate(angs):
        ca, sa = math.cos(a), math.sin(a)
        rings.append([poles[q] if q in poles else bm.verts.new((r * ca, r * sa, z)) for q, (r, z) in enumerate(P[i])])
    for i in range(na):
        A, B = rings[i], rings[(i + 1) % na]
        for q in range(npf if closed else npf - 1):
            q1 = (q + 1) % npf
            vs = [A[q], B[q], B[q1], A[q1]]
            u = []
            for v in vs:
                if v not in u: u.append(v)
            if len(u) >= 3: bm.faces.new(u)
    if not closed and 0 not in poles: bm.faces.new([rings[i][0] for i in range(na)])
    if not closed and npf - 1 not in poles: bm.faces.new([rings[i][npf - 1] for i in range(na)])
    allv = list(poles.values()) + [v for rg in rings for v in rg if v not in poles.values()]
    if M is not None: bmesh.ops.transform(bm, matrix=M, verts=list(set(allv)))
    s._end(b, col, smooth=smooth)
MB.sweep = sweep
def U(n): return [2 * math.pi * i / n for i in range(n)]
def paint(me, col, fn):
    uvl = me.uv_layers['PAL']; u = swuv(col)
    for p in me.polygons:
        if fn(p):
            for li in p.loop_indices: uvl.data[li].uv = u

# =====================================================================================================================
# dimensions
# =====================================================================================================================
RING_R = 4.6               # playable radius
RD = 5.3                   # cake radius (frosting top at z = 0)
CK_H = 2.0                 # cake height: top -> stand plate
RC = 0.32                  # soft rounded top edge
PLATE_Z = -CK_H            # top of the cake-stand plate
PL_R = 6.35                # stand plate radius (scalloped rim)
TBL = -3.05                # tablecloth surface

# ---- cake -----------------------------------------------------------------------------------------------------------
# side bands, top -> bottom (the frosting collar with pink drips covers the top ~0.3-0.9 m)
BANDS = [(0.0, -0.95, 'sponge'), (-0.95, -1.15, 'frost'), (-1.15, -1.52, 'sponge'), (-1.52, -1.68, 'jam'), (-1.68, -2.0, 'sponge')]
def mod_cake():
    m = MB(); prof = [(0.0, PLATE_Z), (RD, PLATE_Z)]
    for z in (-1.84, -1.68, -1.52, -1.33, -1.15, -0.95, -0.6): prof.append((RD, z))
    for k in range(5):
        t = math.pi / 2 * k / 4; prof.append((RD - RC + RC * math.cos(t), -RC + RC * math.sin(t)))
    prof.append((RD - RC - 0.6, 0.0))
    prof.append((0.0, 0.0))
    m.lathe(prof, 'frost', 96)
    me = m.finish('MOD_Cake', sharp=50)
    for z0, z1, c in BANDS:
        paint(me, c, lambda p, z0=z0, z1=z1: p.normal.z < 0.5 and z1 < p.center.z < z0 and p.center.z < -RC)
    paint(me, 'frost', lambda p: p.center.z < PLATE_Z + 0.01 and p.normal.z < -0.5)
    return me
def mod_filling():
    """the cream and jam layers bulge a little out of the sponge: soft piped bands."""
    m = MB()
    for z0, z1, c in BANDS:
        if c == 'sponge': continue
        h = z0 - z1; zc = (z0 + z1) / 2
        prof = [(RD - 0.1, z1 + 0.005)] + [(RD + 0.055 * math.sin(math.pi * k / 4) + 0.005, z1 + 0.005 + (h - 0.01) * k / 4) for k in range(5)] + [(RD - 0.1, z0 - 0.005)]
        m.sweep(lambda a, prof=prof: prof, U(96), c, closed=True)
    return m.finish('MOD_Filling', sharp=70)
# pink frosting collar: covers the soft top edge and runs down the side in fat rounded drips
R_D = random.Random(21)
DRIPS = []
a = 0.0
while a < 2 * math.pi - 0.12:
    w = R_D.uniform(0.032, 0.05); L = R_D.uniform(0.28, 0.62)
    DRIPS.append((a + w, w, L)); a += 2 * w + R_D.uniform(0.035, 0.12)
def drip_len(a):
    d = 0.0
    for c, w, L in DRIPS:
        x = (a - c + math.pi) % (2 * math.pi) - math.pi
        if abs(x) < w: d = max(d, L * math.sqrt(1 - (x / w) ** 2))
    return d
def mod_collar():
    m = MB()
    angs = sorted(set([round(x, 5) for x in U(120)] + [round((c + w * t) % (2 * math.pi), 5) for c, w, L in DRIPS for t in (-1.0, -0.93, -0.62, 0.0, 0.62, 0.93, 1.0)]))
    ZD = -0.42           # collar bottom between drips
    TO, TI = 0.06, 0.03  # outer / inner offset from the cake surface
    def edge(k, off):    # point on the rounded top edge, k in [0, 1] from the top (start) to the side
        t = math.pi / 2 * (1 - k) * 0.82; rr = RC + off
        return (RD - RC + rr * math.cos(t), -RC + rr * math.sin(t))
    def prof(a):
        zb = ZD - drip_len(a)
        outer = [edge(k / 3, TO) for k in range(4)] + [(RD + TO, (-RC + zb + 0.06) / 2), (RD + TO, zb + 0.06), (RD + TO * 0.55, zb + 0.005), (RD + 0.01, zb - 0.01)]
        inner = [(RD - TI, zb + 0.04)] + [edge(k / 2, -TI) for k in range(2, -1, -1)]
        # closed loop: inner (bottom -> top) then outer (top -> bottom); start the sweep profile at the inner bottom
        return inner + outer
    m.sweep(prof, angs, 'frost_pink', closed=True)
    return m.finish('MOD_Collar', sharp=70)
def mod_ringline():
    m = MB(); m.sweep(lambda a: [(RING_R - 0.07, -0.01), (RING_R + 0.07, -0.01), (RING_R + 0.07, 0.018), (RING_R - 0.07, 0.018)], U(128), 'ring_line', closed=True)
    return m.finish('MOD_RingLine', sharp=60)
def kiss(m, x, y, z, r, h, col, ridges=7, seg=28, tw=0.0):
    """a piped frosting dollop: soft ridged dome rising to a little curled tip."""
    prof = [(0.0, 0.0), (r * 0.96, 0.0), (r, h * 0.12), (r * 0.92, h * 0.3), (r * 0.72, h * 0.5), (r * 0.45, h * 0.7), (r * 0.2, h * 0.88), (0.0, h)]
    def p(a):
        return [(rr * (1 + 0.07 * math.cos(ridges * a + tw * zz / h)) if 0 < k < len(prof) - 1 else rr, zz) for k, (rr, zz) in enumerate(prof)]
    m.sweep(p, U(seg), col, M=T(x, y, z))
def mod_dollop(col):
    m = MB(); kiss(m, 0, 0, 0, 0.3, 0.42, col, seg=16, tw=3.0)
    return m.finish('MOD_Dollop_' + col, sharp=60)
def mod_border():
    """little piped beads round the foot of the cake."""
    m = MB(); n = 64
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        m.lathe([(0.0, -0.2), (0.17, -0.15), (0.25, 0.0), (0.18, 0.14), (0.0, 0.2)], 'frost', 8, M=T((RD + 0.05) * math.cos(a), (RD + 0.05) * math.sin(a), PLATE_Z + 0.12))
    return m.finish('MOD_Border', sharp=80)
def mod_strawberry():
    """chunky strawberry lying on its side: a heart-shaped cone (pointed tip, wide shoulders), yellow seeds, a leafy
    cap at the wide end. Lying down so the cone reads from the high game camera (upright it read as a tomato)."""
    m = MB()
    R = Matrix.Rotation(math.radians(84), 4, 'X')          # the tip points along -y (out from the cake), the cap faces +y
    M = T(0, 0, 0.2) @ R
    prof = [(0.0, -0.36), (0.07, -0.3), (0.15, -0.18), (0.21, -0.04), (0.235, 0.08), (0.22, 0.17), (0.15, 0.23), (0.0, 0.25)]
    m.lathe(prof, 'berry', 16, M=M)
    for i in range(18):                                     # seeds dotted over the visible upper side
        zz = -0.28 + 0.48 * ((i * 0.61) % 1.0); ang = math.radians(-70 + 140 * ((i * 0.37) % 1.0)) + math.pi / 2
        rr = max(0.04, float(__import__('numpy').interp(zz, [p_[1] for p_ in prof], [p_[0] for p_ in prof]))) + 0.004
        m.ico(rr * math.cos(ang), rr * math.sin(ang), zz, 0.022, 'acc_yellow', sub=1, sq=(1, 1, 1.4), M=M)
    n = 10; pts = [((0.21 if i % 2 == 0 else 0.08) * math.cos(2 * math.pi * i / n), (0.21 if i % 2 == 0 else 0.08) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    m.prism(pts, 0.22, 0.27, 'leaf', bev=0.015, M=M)
    m.cyl(0, 0, 0.27, 0.03, 0.1, 'leaf_dk', 8, M=M)
    return m.finish('MOD_Strawberry', sharp=60)
def mod_candle(col):
    m = MB()
    m.cyl(0, 0, 0.45, 0.15, 0.9, col, 20, bev=0.04, bseg=2)
    m.cyl(0, 0, 0.95, 0.025, 0.1, 'wood_dk', 8)                                     # wick
    return m.finish('MOD_Candle_' + col, sharp=50)
def mod_flame():
    """soft teardrop flame; origin at its foot so the game can flicker it by scaling y."""
    m = MB()
    m.lathe([(0.0, 0.0), (0.1, 0.03), (0.16, 0.13), (0.165, 0.22), (0.125, 0.35), (0.065, 0.47), (0.0, 0.56)], 'flame', 16)
    me = m.finish('MOD_Flame', sharp=80)
    paint(me, 'orange', lambda p: p.center.z < 0.1)
    return me
def mod_sprinkles():
    m = MB(); R = random.Random(9); pts = []
    cols = ['pink_acc', 'dusty_blue', 'mint', 'flame', 'lilac']
    while len(pts) < 30:
        a = R.uniform(0, 2 * math.pi); r = 4.25 * math.sqrt(R.uniform(0.02, 1))
        x, y = r * math.cos(a), r * math.sin(a)
        if min(math.hypot(x - 1.5, y), math.hypot(x + 1.5, y)) < 1.1 or any(math.hypot(x - u, y - v) < 1.0 for u, v in pts): continue
        pts.append((x, y))
    for k, (x, y) in enumerate(pts):
        m.cyl(x, y, 0.012, 0.095, 0.024, cols[k % len(cols)], 10)
    return m.finish('MOD_Sprinkles', sharp=60)
# ---- stand + table + props ------------------------------------------------------------------------------------------
def mod_stand():
    """pale ceramic cake stand: a plate with a scalloped rim on a short soft foot."""
    m = MB(); n = 18
    def plate(a):
        sc = 1 + 0.025 * abs(math.cos(n * a / 2)) ** 0.6
        R = PL_R * sc
        return [(0.0, PLATE_Z - 0.26), (R - 0.4, PLATE_Z - 0.26), (R - 0.05, PLATE_Z - 0.16), (R, PLATE_Z - 0.04), (R - 0.04, PLATE_Z + 0.08),
                (R - 0.18, PLATE_Z + 0.06), (R - 0.45, PLATE_Z), (0.0, PLATE_Z)]
    m.sweep(plate, U(n * 8), 'stand')
    m.lathe([(0.0, TBL), (2.7, TBL), (2.75, TBL + 0.08), (2.5, TBL + 0.2), (1.25, TBL + 0.42), (1.0, TBL + 0.6), (1.05, PLATE_Z - 0.25), (0.0, PLATE_Z - 0.25)], 'stand', 64)
    return m.finish('MOD_Stand', sharp=50)
def mod_cloth():
    """plain pastel tablecloth with a few big soft dots (flat colour, no texture)."""
    m = MB(); m.box(-30, 30, -16, 30, TBL - 0.2, TBL, 'cloth')
    R = random.Random(3); k = 0
    for j in range(-6, 12):
        for i in range(-10, 11):
            x = i * 3.4 + (1.7 if j % 2 else 0) + R.uniform(-0.3, 0.3); y = j * 2.9 + R.uniform(-0.3, 0.3)
            if math.hypot(x, y) < PL_R + 0.7 or y < -7.5 or abs(x) > 13.3 + 0.3 * (y + 4): continue   # only where the camera sees
            b = m._begin(); vs = [m.bm.verts.new((x + 0.45 * math.cos(t), y + 0.45 * math.sin(t), TBL + 0.004)) for t in U(14)]
            m.bm.faces.new(vs); m._end(b, 'cloth_dot', smooth=False)                              # one flat disc
    for f in m.bm.faces:                       # a lone disc has no inside: make sure it faces up
        if f.calc_center_median().z > TBL and f.normal.z < 0: f.normal_flip()
    return m.finish('MOD_Cloth', sharp=30)
def mod_present():
    """wrapped present: soft box, ribbon cross, a fat two-loop bow."""
    m = MB(); W, H = 1.25, 1.7
    m.box(-W, W, -W, W, 0, H, 'pink_acc', 0.12, 3)
    m.box(-0.24, 0.24, -W - 0.03, W + 0.03, -0.0, H + 0.03, 'mint', 0.05, 2)
    m.box(-W - 0.03, W + 0.03, -0.24, 0.24, -0.0, H + 0.03, 'mint', 0.05, 2)
    m.ico(0.42, 0, H + 0.24, 0.42, 'mint', 2, (1.15, 0.55, 0.62), M=Rz(20))
    m.ico(-0.42, 0, H + 0.24, 0.42, 'mint', 2, (1.15, 0.55, 0.62), M=Rz(20))
    m.ico(0, 0, H + 0.17, 0.2, 'mint', 2, (1, 1, 0.8), M=Rz(20))
    return m.finish('MOD_Present', sharp=50)
def mod_hat():
    """party hat: fat cone in pastel bands with a pompom on top."""
    m = MB(); Rb, Hh = 1.0, 2.3
    m.lathe([(0.0, 0.0), (Rb, 0.0), (Rb * 0.98, 0.05)] + [(Rb * (1 - k / 8) * 0.98, Hh * k / 8) for k in range(1, 8)] + [(0.0, Hh)], 'lilac', 32)
    m.ico(0, 0, Hh + 0.1, 0.3, 'flame', 2)
    me = m.finish('MOD_Hat', sharp=60)
    paint(me, 'frost', lambda p: p.normal.z > -0.5 and (0.62 < p.center.z < 0.9 or 1.45 < p.center.z < 1.7) and p.center.z < Hh)
    return me
def mod_balloon(col):
    m = MB()
    prof = []
    for k in range(15):                         # soft egg, a touch narrower at the knot
        t = math.pi * k / 14; z = -math.cos(t); r = 0.9 * math.sin(t) * (1 - 0.12 * (1 - z) / 2)
        prof.append((0.0 if k in (0, 14) else r, z))
    m.lathe(prof, col, 28)
    m.cyl(0, 0, -1.04, 0.12, 0.12, col, 10, r2=0.05)                                 # knot
    return m.finish('MOD_Balloon_' + col, sharp=70)
def mod_string(h):
    m = MB(); m.cyl(0, 0, h / 2, 0.03, h, 'frost', 6)
    return m.finish('MOD_String_%d' % int(h * 10), sharp=80)
def mod_dessert():
    """small dessert plate with a chunky fork."""
    m = MB()
    m.lathe([(0.0, 0.0), (1.1, 0.0), (1.45, 0.1), (1.6, 0.22), (1.48, 0.26), (1.2, 0.14), (0.0, 0.14)], 'stand', 40)
    fk = Rz(-30)
    m.box(-1.55, 0.4, -0.17, 0.17, 0.14, 0.3, 'pink_acc', 0.07, 2, M=fk)                     # handle
    m.box(0.3, 0.78, -0.36, 0.36, 0.14, 0.28, 'pink_acc', 0.06, 2, M=fk)                     # head
    for yy in (-0.27, -0.09, 0.09, 0.27):
        m.box(0.7, 1.3, yy - 0.07, yy + 0.07, 0.14, 0.27, 'pink_acc', 0.05, 2, M=fk)       # tines
    return m.finish('MOD_Dessert', sharp=50)

for f in (mod_cake, mod_filling, mod_collar, mod_ringline, mod_border, mod_strawberry, mod_flame, mod_sprinkles, mod_stand, mod_cloth,
          mod_present, mod_hat, mod_dessert): f()
for c in ('frost', 'frost_pink'): mod_dollop(c)
CANDLE_COLS = ('lilac', 'dusty_blue', 'mint', 'pink_acc', 'flame', 'lilac', 'mint', 'dusty_blue')
for c in set(CANDLE_COLS): mod_candle(c)
for c in ('pink_acc', 'dusty_blue', 'flame', 'mint'): mod_balloon(c)

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Cloth', 'TABLE_Cloth', c='ENV_GROUND')
place('MOD_Stand', 'TABLE_Stand', c='ENV_CAKE')
place('MOD_Cake', 'CAKE_Body', c='ENV_CAKE')
place('MOD_Filling', 'CAKE_Filling', c='ENV_CAKE')
place('MOD_Collar', 'CAKE_Collar', c='ENV_CAKE')
place('MOD_Border', 'CAKE_Border', c='ENV_CAKE')
place('MOD_RingLine', 'CAKE_RingLine', c='ENV_CAKE')
place('MOD_Sprinkles', 'CAKE_Sprinkles', c='ENV_TOPPINGS')
ND = 36; DR = RD - 0.33; ci = 0
for k in range(ND):
    a = 2 * math.pi * (k + 0.5) / ND; x, y = DR * math.cos(a), DR * math.sin(a)
    if k % 9 in (2, 6):                       # candles (8)
        col = CANDLE_COLS[ci]; ci += 1
        place('MOD_Candle_' + col, nm('CAKE_Candle'), (x, y, 0.0), c='ENV_TOPPINGS')
        place('MOD_Flame', nm('FLAME'), (x, y, 1.0), rz=math.degrees(a), c='ENV_TOPPINGS')
        place('MOD_Dollop_frost', nm('CAKE_Dollop'), (x, y, 0.0), s=(1.0, 1.0, 0.45), rz=k * 37, c='ENV_TOPPINGS')
        continue
    place('MOD_Dollop_' + ('frost_pink' if k % 2 else 'frost'), nm('CAKE_Dollop'), (x, y, 0.0), rz=k * 37, s=RNG.uniform(0.95, 1.05), c='ENV_TOPPINGS')
    if k % 9 == 4 or k % 9 == 8:              # strawberries on top of a few dollops
        place('MOD_Strawberry', nm('CAKE_Strawberry'), (x, y, 0.3), rz=math.degrees(math.atan2(y, x)) - 90 + RNG.uniform(-25, 25), c='ENV_TOPPINGS')   # tip pointing out from the cake
# table props (only where the camera sees them)
place('MOD_Present', 'TABLE_Present', (-10.6, 2.2, TBL), rz=18, c='ENV_PROPS')
place('MOD_Hat', 'TABLE_PartyHat', (10.2, 4.6, TBL), c='ENV_PROPS')
place('MOD_Dessert', 'TABLE_DessertPlate', (9.2, -0.6, TBL), rz=10, c='ENV_PROPS')
for k, (x, y, h, col) in enumerate(((-12.3, 8.0, 2.0, 'pink_acc'), (-10.7, 9.4, 2.6, 'dusty_blue'), (-13.6, 10.4, 2.4, 'flame'),
                                     (12.9, 10.2, 2.3, 'mint'), (14.4, 8.6, 1.9, 'pink_acc'))):
    place('MOD_Balloon_' + col, nm('TABLE_Balloon'), (x, y, TBL + h + 1.1), rz=k * 40, rx=(1 if x > 0 else -1) * (k % 2 * 2 - 1) * 5, c='ENV_PROPS')
    place(mod_string(h).name, nm('TABLE_BalloonString'), (x, y, TBL), c='ENV_PROPS')

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
bpy.ops.export_scene.gltf(filepath=OUT + '/cake_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
for o in bpy.data.objects:            # the flames are light: they cast no shadow
    if o.name.startswith('FLAME'): o.visible_shadow = False
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/cake_kit.blend')
if not NORENDER:
    exr = OUT + '/cake_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/cake_gamecam.png'] + comp, check=True)
print('DONE')
