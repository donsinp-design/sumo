# ROBOT VACUUM (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py / stage_lily_kit.py / stage_cake_kit.py / stage_vinyl_kit.py.
#   <bl python> tools/blender/stage_vacuum_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vsvacuum): vacuum_kit.blend, vacuum_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         vacuum_palette.png, vacuum_gamecam.exr (light passes) -> vacuum_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the vinyl kit's, with the vinyl-only swatches
# repurposed for the robot (lid, lid rim, bumper, skirt, aqua ring line, lid; the inner lid line uses 'frame') and the floor (3 board tones,
# seam, rug, rug band, rug centre).
# Roots in the glb:
#   ROBOT_Body  static robot (lid top at z = 0, radius 5.3, ring line at r = 4.6, underside clear of the floor)
#   BRUSH_L/_R  the two side brushes under the front (game -z), origin at each brush hub: the game spins them
#   FLOOR       boards + rug + small floor things, ONE mesh, 216 x 216 centred at the origin, top at z = -0.9;
#               its pattern repeats exactly every 72 m in x and y (the game slides it, offset wrapped modulo 72)
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, robot top at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vsvacuum'
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
CN = {n: coll(n) for n in ('ENV_GROUND', 'ENV_ROBOT', 'ENV_BRUSH', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# =====================================================================================================================
# palette + master material (dohyo kit PAL; stage-only slots repurposed for the robot vacuum + living-room floor)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('stand', 'c4dbea'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('lid', 'f1f0ec'), ('lid_rim', 'd9dfea'), ('bumper', 'a9b6dc'), ('skirt', '8f93b4'), ('board_a', 'e9cfa6'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('ring_line', '79cfd9'), ('board_b', 'e2c399'), ('board_c', 'eed8b4'), ('gap', 'c4a07a'), ('rug', 'f0c3bd'), ('rug_band', 'f8eedc'), ('rug_in', 'cfc3e6'),
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
img.filepath_raw = OUT + '/vacuum_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
RD = 5.3                   # robot radius (lid top at z = 0)
FLOOR_Z = -0.9             # living-room floor (game y = -0.9)
BOT_Z = -0.74              # robot underside (a little clearance so flat floor things slide under)
TILE = 72.0                # the floor pattern repeats every TILE m in x and y (the game wraps its offset modulo 72)
FLOOR_HALF = 108.0         # floor is 216 x 216, centred at the origin (3 x 3 tiles)
BW, BL, GAP = 3.0, 24.0, 0.06                                  # floorboard width / length / seam

# ---- the robot (static) ----------------------------------------------------------------------------------------------
# flat tone zones on the lid, centre -> edge: (r0, r1, colour)
LID_BANDS = [(0.0, 2.9, 'lid'), (2.9, 3.04, 'frame'), (3.04, RING_R - 0.1, 'lid'), (RING_R - 0.1, RING_R + 0.1, 'ring_line'),
             (RING_R + 0.1, 5.1, 'lid_rim')]
def mod_robot():
    m = MB()
    prof = [(0.0, BOT_Z), (4.7, BOT_Z), (5.0, BOT_Z + 0.03), (5.17, BOT_Z + 0.09), (5.24, -0.6),     # under-skirt, tucked in
            (5.31, -0.585), (5.36, -0.54), (5.37, -0.46), (5.37, -0.38), (5.35, -0.34), (5.31, -0.32),   # soft bumper band
            (5.3, -0.3), (5.3, -0.2), (5.28, -0.1), (5.24, -0.04), (5.18, -0.008), (5.1, 0.0)]                        # lid side, rounded top edge
    for r0, r1, c in reversed(LID_BANDS):
        if r0 > 0: prof.append((r0, 0.0))
    prof.append((0.0, 0.0))
    m.lathe(prof, 'lid', 128)
    # two wheels + a caster underneath (hidden mostly; they make the robot stand on the floor)
    for x in (-3.3, 3.3):
        m.cyl(x, 0, FLOOR_Z + 0.42, 0.42, 0.5, 'skirt', 20, bev=0.08, bseg=2, axis='X')
    m.ico(0, 3.6, FLOOR_Z + 0.2, 0.22, 'skirt', 2)
    me = m.finish('MOD_Robot', sharp=40)
    uvl = me.uv_layers['PAL']
    for p in me.polygons:
        r = Vector((p.center.x, p.center.y)).length
        c = None
        if p.normal.z > 0.9 and abs(p.center.z) < 0.003:
            for r0, r1, cc in LID_BANDS:
                if r0 <= r < r1: c = cc
        elif r > 5.0 and -0.6 < p.center.z < -0.31: c = 'skirt'
        elif r > 5.0 and p.center.z >= -0.31: c = 'bumper'
        elif p.center.z <= -0.6 and r > 3.0: c = 'skirt'
        if c:
            u = swuv(c)
            for li in p.loop_indices: uvl.data[li].uv = u
    return me
BR_Z = -0.8                # brush hub height (the game spins BRUSH_L / BRUSH_R about their own vertical axis)
BR_POS = [(-math.sin(0.5) * (RD - 0.35), math.cos(0.5) * (RD - 0.35)), (math.sin(0.5) * (RD - 0.35), math.cos(0.5) * (RD - 0.35))]
def mod_brush():
    """chunky toy side brush: soft hub + three tapered coral arms with rounded tips, origin at the hub."""
    m = MB()
    m.lathe([(0.0, -0.07), (0.36, -0.07), (0.42, -0.02), (0.42, 0.04), (0.36, 0.08), (0.2, 0.09), (0.2, BOT_Z - BR_Z + 0.04), (0.0, BOT_Z - BR_Z + 0.04)], 'skirt', 24)
    m.ico(0, 0, 0.09, 0.2, 'bumper', 2, sq=(1, 1, 0.45))
    L = 2.8
    for k in range(3):
        Ma = Rz(k * 120) @ Ry(2.0)
        m.prism(chaikin([(0.2, -0.16), (L * 0.55, -0.2), (L, -0.42), (L + 0.35, -0.3), (L + 0.42, 0.0), (L + 0.35, 0.3), (L, 0.42), (L * 0.55, 0.2), (0.2, 0.16)], 2),
                -0.07, 0.07, 'coral', M=Ma, bev=0.05, bseg=2)
    return m.finish('MOD_Brush', sharp=45)

# ---- the living-room floor: ONE mesh FLOOR (boards + rug + small things), 216 x 216, repeating every 72 m ------------
TONES = ('board_a', 'board_b', 'board_c')
ROWS = int(TILE / BW)                                    # 24 board rows per tile
ROW_OFF = [RNG.choice((0, 6, 12, 18)) for _ in range(ROWS)]   # joint offsets per row (joints repeat every BL = 24 | 72)
ROW_TONE = [[RNG.randrange(3) for _ in range(3)] for _ in range(ROWS)]
RUG_C, RUG_W, RUG_H, RUG_RC = (-11.5, 4.5), 21.0, 15.0, 3.0   # rug centre (tile-local), size, corner radius
def rrect(w, h, rc, n=6):
    pts = []
    for cx, cy, a0 in ((w / 2 - rc, h / 2 - rc, 0), (-w / 2 + rc, h / 2 - rc, 90), (-w / 2 + rc, -h / 2 + rc, 180), (w / 2 - rc, -h / 2 + rc, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + rc * math.cos(a), cy + rc * math.sin(a)))
    return pts
def chaikin(pts, it=2):
    for _ in range(it):
        q = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = q
    return pts
def board(m, x0, x1, y0, y1, col, c=0.07, depth=0.2):
    """floorboard: flat top with a soft chamfer round it (no bottom face): 18 triangles."""
    b = m._begin(); bm = m.bm; z1 = FLOOR_Z; z0 = FLOOR_Z - depth
    top = [bm.verts.new(v) for v in ((x0 + c, y0 + c, z1), (x1 - c, y0 + c, z1), (x1 - c, y1 - c, z1), (x0 + c, y1 - c, z1))]
    mid = [bm.verts.new(v) for v in ((x0, y0, z1 - c), (x1, y0, z1 - c), (x1, y1, z1 - c), (x0, y1, z1 - c))]
    bot = [bm.verts.new(v) for v in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
    bm.faces.new(top)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((mid[i], mid[j], top[j], top[i])); bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
    m._end(b, col)
def floor_items(m, ox, oy):
    """rug + a couple of small calm things lying on the floor of one tile (tile centre ox, oy)."""
    rx, ry = ox + RUG_C[0], oy + RUG_C[1]
    M = T(rx, ry, 0)
    m.prism(rrect(RUG_W, RUG_H, RUG_RC), FLOOR_Z, FLOOR_Z + 0.1, 'rug', M=M, bev=0.05, bseg=2)
    m.prism(rrect(RUG_W - 2.6, RUG_H - 2.6, RUG_RC - 1.3), FLOOR_Z + 0.1, FLOOR_Z + 0.112, 'rug_band', M=M)
    m.prism(rrect(RUG_W - 3.8, RUG_H - 3.8, RUG_RC - 1.9), FLOOR_Z + 0.112, FLOOR_Z + 0.118, 'rug', M=M)
    m.prism(rrect(RUG_W - 9.0, RUG_H - 8.0, 2.2), FLOOR_Z + 0.118, FLOOR_Z + 0.124, 'rug_in', M=M)
    # a dropped sock (soft mint L, coral cuff + stripe) on the boards, back right
    Ms = T(ox + 10.2, oy + 8.6, FLOOR_Z) @ Rz(-22)
    m.prism(chaikin([(-1.6, -0.55), (0.7, -0.6), (1.1, -0.3), (1.15, 0.6), (1.1, 1.6), (0.85, 1.9), (0.35, 1.9), (0.05, 1.6), (0.0, 0.55), (-1.6, 0.55)], 2),
            0.0, 0.22, 'teal_muted', M=Ms, bev=0.08, bseg=2)
    m.box(-1.75, -1.2, -0.62, 0.62, 0.0, 0.27, 'coral', 0.12, 2, M=Ms)
    m.box(-0.75, -0.45, -0.58, 0.58, 0.0, 0.235, 'coral', 0.08, 2, M=Ms)
    # a cookie on the rug, back left
    Mc = T(ox - 8.6, oy + 9.6, FLOOR_Z + 0.1)
    m.lathe([(0.0, 0.0), (0.95, 0.0), (1.02, 0.07), (0.97, 0.17), (0.85, 0.21), (0.0, 0.21)], 'wood_lt', 24, M=Mc)
    for a, d in ((20, 0.45), (140, 0.55), (250, 0.4), (320, 0.62)):
        m.ico(0.0, 0.0, 0.0, 0.14, 'wood_dk', 1, sq=(1, 1, 0.5), M=Mc @ T(d * math.cos(math.radians(a)), d * math.sin(math.radians(a)), 0.21))
    # a crayon on the boards, front right
    Mk = T(ox + 8.4, oy - 2.2, FLOOR_Z + 0.2) @ Rz(28)
    m.cyl(0, 0, 0, 0.2, 2.0, 'dusty_blue', 10, axis='X', M=Mk)
    m.cyl(-0.25, 0, 0, 0.215, 0.9, 'offwhite', 10, axis='X', M=Mk)
    m.cyl(1.25, 0, 0, 0.2, 0.5, 'dusty_blue', 10, r2=0.06, axis='X', M=Mk)
def mod_floor():
    m = MB()
    H = FLOOR_HALF
    m.box(-H, H, -H, H, FLOOR_Z - 0.3, FLOOR_Z - 0.12, 'gap')                  # seam colour under the boards
    nrows = int(2 * H / BW)
    for j in range(nrows):
        jj = j % ROWS; y0 = -H + j * BW
        off = ROW_OFF[jj]
        k0 = int(math.floor((-H - off) / BL)) - 1
        for k in range(k0, k0 + int(2 * H / BL) + 3):
            x0, x1 = off + k * BL, off + (k + 1) * BL
            if x1 <= -H or x0 >= H: continue
            tone = TONES[ROW_TONE[jj][k % 3]]
            ex0 = max(x0 + GAP, -H); ex1 = min(x1 - GAP, H)
            board(m, ex0, ex1, y0 + GAP, y0 + BW - GAP, tone)
    for tx in (-TILE, 0, TILE):
        for ty in (-TILE, 0, TILE):
            floor_items(m, tx, ty)
    return m.finish('MOD_Floor', sharp=40)

for f in (mod_robot, mod_brush, mod_floor): f()

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Floor', 'FLOOR', c='ENV_GROUND')                          # the game slides this (offset wrapped modulo 72)
place('MOD_Robot', 'ROBOT_Body', c='ENV_ROBOT')
place('MOD_Brush', 'BRUSH_L', (BR_POS[0][0], BR_POS[0][1], BR_Z), rz=10, c='ENV_BRUSH')    # the game spins these
place('MOD_Brush', 'BRUSH_R', (BR_POS[1][0], BR_POS[1][1], BR_Z), rz=-50, c='ENV_BRUSH')

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
bpy.ops.export_scene.gltf(filepath=OUT + '/vacuum_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/vacuum_kit.blend')
if not NORENDER:
    exr = OUT + '/vacuum_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/vacuum_gamecam.png'] + comp, check=True)
print('DONE')
