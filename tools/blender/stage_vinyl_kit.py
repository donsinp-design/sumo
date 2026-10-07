# DJ vinyl turntable (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py / stage_lily_kit.py / stage_cake_kit.py.
#   <bl python> tools/blender/stage_vinyl_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vsvinyl): vinyl_kit.blend, vinyl_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         vinyl_palette.png, vinyl_gamecam.exr (light passes) -> vinyl_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the cake kit's, with the cake-only swatches
# repurposed for the record (soft indigo-charcoal + groove band), label, pale "silver", deck, fader slots and the booth table.
# Everything that turns with the record (disc, groove bands, ring line, label + text, spindle) is ONE mesh object
# SPIN_Record with its origin at the ring centre: the game rotates it about the vertical axis. Everything else is static.
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, record top at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vsvinyl'
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
CN = {n: coll(n) for n in ('ENV_GROUND', 'ENV_SPIN', 'ENV_DECK', 'ENV_PROPS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# =====================================================================================================================
# palette + master material (dohyo kit PAL; stage-only slots repurposed for the turntable booth)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('stand', 'c4dbea'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('deck_top', 'dfd6ee'), ('deck_side', 'c6bbdf'), ('label', 'ec8a66'), ('label_lt', 'f7d592'), ('table', 'a9d8cd'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('ring_line', 'eee4f1'), ('vinyl_band', '524d6d'), ('silver', 'dcdde5'), ('mint', 'a8dcc6'), ('silver_dk', 'b9bbcb'), ('vinyl', '423d59'), ('slot', '7a7396'),
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
img.filepath_raw = OUT + '/vinyl_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
RD = 5.3                   # record radius (record top at z = 0)
REC_H = 0.16               # record thickness
PLAT_R = 5.6               # platter radius
PLAT_Z = -REC_H            # platter top (the record lies on it)
DECK_Z = -0.55             # deck top
TBL = -1.45                # booth table top
DECK_X0, DECK_X1, DECK_Y = -6.6, 8.3, 7.5                     # main deck footprint
MIX_X0, MIX_X1, MIX_Y0, MIX_Y1, MIX_Z = 8.75, 13.95, -4.6, 4.6, -0.35
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# ---- the record (everything here turns) ------------------------------------------------------------------------------
# flat tone bands on the top, centre -> edge: (r0, r1, colour)
REC_BANDS = [(1.45, 1.75, 'vinyl'), (1.75, 2.3, 'vinyl_band'), (2.3, 2.95, 'vinyl'), (2.95, 3.55, 'vinyl_band'), (3.55, 4.1, 'vinyl'),
             (4.1, 4.42, 'vinyl_band'), (4.42, RING_R - 0.09, 'vinyl'), (RING_R - 0.09, RING_R + 0.09, 'ring_line'),
             (RING_R + 0.09, 5.0, 'vinyl'), (5.0, RD, 'vinyl')]
def text_mesh(m, body, size, x, y, z, col, rz=0.0):
    fnt = bpy.data.fonts.load(FONT, check_existing=True)
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = body; cu.font = fnt; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    cu.fill_mode = 'BOTH'; cu.resolution_u = 3; cu.extrude = 0.012
    ob = bpy.data.objects.new('tmp_txt', cu); ROOT.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); me0 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    b = m._begin(); bm2 = bmesh.new(); bm2.from_mesh(me0); bpy.data.meshes.remove(me0)
    bmesh.ops.remove_doubles(bm2, verts=bm2.verts, dist=0.0005)
    bmesh.ops.transform(bm2, matrix=T(x, y, z) @ Rz(rz), verts=bm2.verts)
    tmp = bpy.data.meshes.new('tmp'); bm2.to_mesh(tmp); bm2.free(); m.bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    m._end(b, col, smooth=False)
def mod_record():
    m = MB()
    # disc: flat bottom, soft rounded rim, top split at every band edge
    prof = [(0.0, -REC_H), (RD - 0.06, -REC_H), (RD - 0.01, -REC_H + 0.025), (RD, -REC_H / 2), (RD - 0.01, -0.025), (RD - 0.06, 0.0)]
    for r0, r1, c in reversed(REC_BANDS):
        prof.append((r0, 0.0))
    prof.append((0.0, 0.0))
    m.lathe(prof, 'vinyl', 128)
    # centre label: a thin raised disc with a soft edge, a pale inner ring, chunky text
    LZ = 0.022; LR = 1.42
    m.lathe([(0.0, -0.01), (LR, -0.01), (LR, LZ - 0.01), (LR - 0.012, LZ - 0.002), (LR - 0.03, LZ), (0.62, LZ), (0.5, LZ), (0.0, LZ)], 'label', 96)
    m.lathe([(0.36, LZ - 0.005), (0.5, LZ - 0.005), (0.5, LZ + 0.006), (0.36, LZ + 0.006)], 'label_lt', 64)   # pale ring round the spindle
    text_mesh(m, 'KUMITE', 0.46, 0, 0.88, LZ - 0.004, 'label_lt')
    text_mesh(m, '33', 0.36, 0, -0.9, LZ - 0.004, 'label_lt')
    # spindle (pale soft grey, rounded top)
    m.lathe([(0.0, LZ - 0.01), (0.16, LZ - 0.01), (0.16, LZ + 0.03), (0.11, LZ + 0.05), (0.11, 0.3), (0.095, 0.36), (0.055, 0.395), (0.0, 0.405)], 'silver', 24)
    me = m.finish('MOD_Record', sharp=40)
    uvl = me.uv_layers['PAL']
    for p in me.polygons:                            # paint the groove bands / ring line onto the record top by radius
        if p.normal.z > 0.9 and abs(p.center.z) < 0.003:
            r = Vector((p.center.x, p.center.y)).length
            for r0, r1, c in REC_BANDS:
                if r0 <= r < r1 and r > 1.43:
                    u = swuv(c)
                    for li in p.loop_indices: uvl.data[li].uv = u
    return me
# ---- turntable -------------------------------------------------------------------------------------------------------
def mod_platter(name='MOD_Platter'):
    """pale soft-grey platter under the record: a chunky disc with a rounded top edge."""
    m = MB()
    m.lathe([(0.0, DECK_Z - 0.01), (PLAT_R - 0.15, DECK_Z - 0.01), (PLAT_R - 0.05, DECK_Z + 0.06), (PLAT_R, DECK_Z + 0.16), (PLAT_R, PLAT_Z - 0.09),
             (PLAT_R - 0.03, PLAT_Z - 0.03), (PLAT_R - 0.1, PLAT_Z), (0.0, PLAT_Z)], 'silver', 128)
    me = m.finish(name, sharp=40)
    paint(me, 'silver_dk', lambda p: p.normal.z < 0.5 and p.center.z < DECK_Z + 0.08)   # a darker foot band
    return me
def mod_deck(x0, x1, y0, y1, name):
    """chunky rounded deck body: pale lavender top, lilac sides."""
    m = MB()
    m.box(x0, x1, y0, y1, TBL, DECK_Z, 'deck_side', 0.32, 4)
    me = m.finish(name, sharp=40)
    paint_up(me, 'deck_top', nz=0.5, zmin=DECK_Z - 0.2)
    return me
def mod_tonearm():
    """clean simple tonearm, resting beside the record (not over it): pedestal, straight tube, headshell, counterweight.
    origin at the pivot on the deck top; the arm runs towards -y."""
    m = MB()
    m.lathe([(0.0, 0.0), (0.78, 0.0), (0.8, 0.08), (0.72, 0.2), (0.5, 0.26), (0.0, 0.26)], 'silver_dk', 40)          # round plinth
    m.lathe([(0.0, 0.2), (0.3, 0.2), (0.3, 0.62), (0.26, 0.7), (0.0, 0.72)], 'silver', 24)                        # pivot post
    m.ico(0, 0, 0.72, 0.24, 'silver', 2)                                                                       # pivot ball
    L = 4.4
    m.cyl(0, -L / 2 + 0.1, 0.72, 0.1, L, 'silver', 14, axis='Y')                                               # tube
    m.box(-0.3, 0.3, -L - 0.75, -L + 0.05, 0.56, 0.78, 'coral', 0.09, 3)                                       # headshell
    m.cyl(0, 0.78, 0.72, 0.3, 0.6, 'silver_dk', 24, bev=0.08, bseg=3, axis='Y')                                # counterweight
    m.cyl(0, 0.33, 0.72, 0.07, 0.4, 'silver', 10, axis='Y')
    return m.finish('MOD_Tonearm', sharp=45)
def mod_mixer():
    """mixer: rounded dusty-blue box, chunky knobs in three rows at the back, two channel faders at the front (nothing else)."""
    m = MB()
    m.box(MIX_X0, MIX_X1, MIX_Y0, MIX_Y1, TBL, MIX_Z, 'dusty_blue', 0.32, 4)
    me_cols = ('coral', 'mustard', 'mint')
    for j, y in enumerate((3.5, 2.2, 0.9)):
        for i, x in enumerate((9.7, 10.95, 12.2, 13.3)):
            m.cyl(x, y, MIX_Z + 0.14, 0.36, 0.28, me_cols[j], 24, bev=0.09, bseg=3)
            m.cyl(x, y, MIX_Z + 0.3, 0.16, 0.06, 'offwhite', 16, bev=0.02)
    for x in (9.75, 11.05):                                                                                    # channel faders
        m.box(x - 0.11, x + 0.11, -2.9, -0.5, MIX_Z - 0.02, MIX_Z + 0.012, 'slot', 0.04, 2)
        yc = -1.3 if x < 10 else -2.2
        m.box(x - 0.32, x + 0.32, yc - 0.24, yc + 0.24, MIX_Z, MIX_Z + 0.3, 'offwhite', 0.1, 3)
    me = m.finish('MOD_Mixer', sharp=40)
    return me
def mod_record2():
    """the static record on the second deck (pale-mint label)."""
    m = MB()
    prof = [(0.0, -REC_H), (RD - 0.06, -REC_H), (RD, -REC_H / 2), (RD - 0.06, 0.0), (3.6, 0.0), (3.0, 0.0), (2.3, 0.0), (1.45, 0.0), (0.0, 0.0)]
    m.lathe(prof, 'vinyl', 96)
    m.lathe([(0.0, -0.01), (1.42, -0.01), (1.42, 0.012), (1.39, 0.022), (0.0, 0.022)], 'mint', 64)
    m.lathe([(0.0, 0.0), (0.16, 0.0), (0.11, 0.05), (0.11, 0.3), (0.06, 0.39), (0.0, 0.4)], 'silver', 16)
    me = m.finish('MOD_Record2', sharp=40)
    paint(me, 'vinyl_band', lambda p: p.normal.z > 0.9 and abs(p.center.z) < 0.003 and (2.3 < Vector((p.center.x, p.center.y)).length < 3.0 or 3.6 < Vector((p.center.x, p.center.y)).length < 4.4))
    return me
def mod_speaker():
    """chunky pastel speaker box with two soft cones facing the booth."""
    m = MB(); W, D, H = 5.0, 4.0, 7.5
    m.box(-W / 2, W / 2, -D / 2, D / 2, 0, H, 'pink', 0.4, 4)
    for zc, R in ((H * 0.72, 1.45), (H * 0.3, 1.75)):
        Mf = T(0, -D / 2, zc) @ Rx(90)
        m.lathe([(0.0, -0.05), (R + 0.12, -0.05), (R + 0.12, 0.06), (R, 0.1), (R * 0.82, 0.04), (R * 0.4, -0.12), (R * 0.36, -0.1), (0.0, -0.1)], 'lilac', 40, M=Mf)
        m.lathe([(0.0, -0.12), (R * 0.36, -0.12), (R * 0.3, 0.02), (R * 0.15, 0.1), (0.0, 0.12)], 'offwhite', 24, M=Mf)
    return m.finish('MOD_Speaker', sharp=45)
def mod_table():
    """the booth table: one plain pastel teal slab (flat colour)."""
    m = MB(); m.box(-40, 40, -20, 40, TBL - 0.4, TBL, 'table')
    return m.finish('MOD_Table', sharp=30)

for f in (mod_record, mod_platter, mod_tonearm, mod_mixer, mod_record2, mod_speaker, mod_table): f()
mod_deck(DECK_X0, DECK_X1, -DECK_Y, DECK_Y, 'MOD_Deck')
mod_deck(-23.0, -7.4, -DECK_Y, DECK_Y, 'MOD_Deck2')

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Table', 'BOOTH_Table', c='ENV_GROUND')
place('MOD_Record', 'SPIN_Record', c='ENV_SPIN')                       # the game spins this about its origin
place('MOD_Platter', 'DECK_Platter', c='ENV_DECK')
place('MOD_Deck', 'DECK_Body', c='ENV_DECK')
place('MOD_Tonearm', 'DECK_Tonearm', (6.95, 3.1, DECK_Z), rz=-3, c='ENV_DECK')
place('MOD_Deck2', 'DECK2_Body', c='ENV_PROPS')
place('MOD_Platter', 'DECK2_Platter', (-15.2, 0, 0), c='ENV_PROPS')
place('MOD_Record2', 'DECK2_Record', (-15.2, 0, 0), rz=40, c='ENV_PROPS')
place('MOD_Mixer', 'BOOTH_Mixer', c='ENV_PROPS')
place('MOD_Speaker', 'BOOTH_Speaker_L', (-12.2, 10.6, TBL), rz=14, c='ENV_PROPS')
place('MOD_Speaker', 'BOOTH_Speaker_R', (13.6, 10.9, TBL), rz=-14, c='ENV_PROPS')
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
bpy.ops.export_scene.gltf(filepath=OUT + '/vinyl_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/vinyl_kit.blend')
if not NORENDER:
    exr = OUT + '/vinyl_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/vinyl_gamecam.png'] + comp, check=True)
print('DONE')
