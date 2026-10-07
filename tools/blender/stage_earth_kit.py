# FLAT EARTH (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py / stage_lily_kit.py / stage_cake_kit.py / stage_vinyl_kit.py /
# stage_vacuum_kit.py / stage_heli_kit.py / stage_clock_kit.py.
#   <bl python> tools/blender/stage_earth_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vsearth): earth_kit.blend, earth_kit.glb (stage only, Y-up, palette embedded, M_KIT; no glass faces),
#         earth_palette.png, earth_gamecam.exr (light passes) -> earth_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the clock kit's, with the clock-only swatches
# repurposed for the ocean, ring line, ice, land, sand and the rock strata (and three unused city slots for stars/moon).
# Roots in the glb:
#   SPIN_Earth     ONE mesh, origin at the ring centre: pastel ocean (top at z = 0, r 5.12, runs on under the ice wall),
#                  chunky flat continents (stages.js LAND through P(lat, lon): azimuthal map from the north pole, prime
#                  meridian towards the camera), raised <= 0.03 with soft rounded edges, sandy desert patches, a
#                  north-pole ice cap and the soft pale ring line at r = 4.6 (latitude -60). The game may spin it.
#   DISC_IceWall   static chunky icy crest all round the edge (inner foot r 4.97, crest <= 0.3), rolling down into the
#                  pale icy top band of the side
#   DISC_Crust     static soft pastel rock / earth strata under the map, tapering to a rounded underside (~1.6 m + belly)
#   SPACE_*        static backdrop for the versus camera: floating rocks, soft clouds under the disc edge, chunky stars,
#                  a little sun and a crescent moon (flat shapes turned to the versus camera)
# Render only (not in the glb): the soft indigo-violet night sky (camera-only emissive dome; game: use the SKY_* colours).
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, map top at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vsearth'
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
CN = {n: coll(n) for n in ('ENV_SPIN', 'ENV_DISC', 'ENV_SPACE', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# =====================================================================================================================
# palette + master material (dohyo kit PAL; stage-only slots repurposed for the ocean, ring line, ice, land, sand and rock strata)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('star', 'f7e5a2'), ('star_lt', 'fbf5df'), ('moon', 'f3e8c6'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('stand', 'c4dbea'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('ocean', '93c3e6'), ('ring_line', 'f6f2e2'), ('ice', 'dcecf4'), ('ice_lt', 'f0f6f7'), ('ice_dk', 'bed7e8'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('land', '9fce7e'), ('land_dk', '82b56c'), ('sand', 'e9d5a0'), ('rock1', 'dcbb98'), ('rock2', 'c9a283'), ('rock3', 'b48f78'), ('rock4', 'a3826f'),
]
SW = {n: i for i, (n, h) in enumerate(PAL)}
SW['sun'] = SW['mustard']; SW['sun_lt'] = SW['star']
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
img.filepath_raw = OUT + '/earth_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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

def fillet(pts, r, n=3):
    """round every corner of a closed outline with a soft arc of radius ~r."""
    out = []; N = len(pts)
    for i in range(N):
        P = Vector(pts[i]); A = Vector(pts[i - 1]); B = Vector(pts[(i + 1) % N])
        u = (A - P).normalized(); v = (B - P).normalized()
        d = min(r, (A - P).length * 0.45, (B - P).length * 0.45)
        p0, p1 = P + u * d, P + v * d
        for k in range(n + 1):
            t = k / n; q = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * P + t * t * p1
            out.append((q.x, q.y))
    return out
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
def circle(r, n=16, cx=0.0, cy=0.0): return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in U(n)]

# =====================================================================================================================
# dimensions
# =====================================================================================================================
RING_R = 4.6               # playable radius (soft pale ring line on the ocean = latitude -60)
RD = 5.3                   # disc radius (map top at z = 0)
OC_R = 5.12                # the spinning map runs on under the ice wall up to here
ICE_IN = 4.97              # ice wall inner foot
ICE_TOP = 0.3              # ice wall crest (<= 0.35)
DISC_H = 1.6               # crust thickness under the map
LAND_H = 0.024             # continents: flat raised shapes, rounded edges (walkable)

def P(lat, lon):
    """stages.js P(): azimuthal map seen from above the north pole, radius = (90 - lat) / 150 * ring radius,
    prime meridian towards the camera (game +z = blender -y), lon +90 to game +x."""
    r = (90 - lat) / 150 * RING_R; a = math.radians(lon)
    return (math.sin(a) * r, -math.cos(a) * r)

# stages.js LAND (lat, lon) outlines
LAND = [
    [[70, -160], [72, -120], [75, -85], [62, -62], [50, -56], [45, -66], [30, -81], [25, -80], [18, -96], [15, -88], [8, -78], [20, -105], [32, -117], [40, -124], [50, -128], [58, -136], [60, -147], [64, -166]],
    [[83, -35], [80, -20], [70, -22], [60, -43], [65, -53], [77, -70]],
    [[12, -72], [10, -62], [5, -52], [-5, -35], [-10, -37], [-23, -42], [-35, -56], [-42, -63], [-55, -68], [-52, -75], [-40, -74], [-18, -71], [-5, -81], [2, -79], [9, -78]],
    [[71, 25], [70, 40], [60, 30], [55, 20], [54, 10], [51, 2], [48, -5], [43, -9], [36, -6], [37, 0], [43, 6], [44, 13], [40, 18], [38, 24], [41, 29], [45, 30], [46, 40], [55, 40], [65, 40]],
    [[37, 10], [32, 32], [12, 43], [11, 51], [-1, 42], [-10, 40], [-26, 33], [-34, 26], [-34, 18], [-28, 15], [-17, 12], [-5, 12], [4, 8], [5, -5], [10, -15], [21, -17], [28, -13], [35, -6]],
    [[77, 105], [73, 140], [70, 180], [64, 178], [60, 163], [52, 158], [53, 141], [43, 135], [38, 128], [35, 129], [30, 122], [22, 113], [10, 106], [1, 104], [8, 98], [16, 95], [22, 90], [20, 73], [25, 66], [25, 57], [13, 44], [30, 48], [37, 36], [42, 42], [45, 52], [55, 60], [68, 68], [72, 80]],
    [[-11, 131], [-12, 142], [-25, 153], [-37, 150], [-38, 141], [-32, 133], [-35, 117], [-22, 114], [-14, 127]],
    [[58, -5], [55, -1], [51, 1], [50, -5], [54, -4]], [[45, 142], [40, 141], [35, 140], [33, 131], [35, 133], [41, 140]],
    [[-1, 110], [-4, 120], [-8, 115], [-6, 105]], [[-35, 173], [-41, 176], [-46, 168], [-40, 172]],
]
LAND_COL = ['land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land', 'land']
# soft sandy patches (deserts) sitting a hair above the green: Sahara, central Australia
SAND = [
    [[30, -8], [32, 10], [30, 25], [27, 32], [18, 32], [15, 20], [16, 2], [18, -12], [24, -14]],
    [[-20, 120], [-19, 132], [-24, 140], [-30, 137], [-29, 124], [-25, 119]],
]

def simple_closed(pts, it=2):
    q = chaikin([tuple(p) for p in pts], it)
    # drop near-duplicate points
    out = []
    for p in q:
        if not out or (Vector(p) - Vector(out[-1])).length > 0.02: out.append(p)
    if (Vector(out[0]) - Vector(out[-1])).length < 0.02: out.pop()
    return out

def flat_shape(m, pts, z0, z1, col, bev):
    """a flat raised shape: ngon prism with a soft rounded top edge (bevel on the top rim only)."""
    b = m._begin(); bm = m.bm
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]; hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    fl = bm.faces.new(list(reversed(lo))); fh = bm.faces.new(hi)
    for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f not in b[0]])
    rim = [e for e in fh.edges]
    bmesh.ops.bevel(bm, geom=rim, offset=bev, offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    u = swuv(col)
    for f in bm.faces:
        if f not in b[0]:
            f.material_index = 0; f.smooth = True
            for l in f.loops: l[m.uv].uv = u

# ---- SPIN_Earth: ocean disc + continents + ring line (+ a little north-pole ice cap), ONE mesh, origin at the centre --
def mod_earth():
    m = MB()
    # ocean: thin flat slab, top at z = 0, running on under the ice wall
    m.lathe([(0.0, -0.06), (OC_R, -0.06), (OC_R, 0.0), (RING_R + 0.25, 0.0), (RING_R - 0.25, 0.0), (2.6, 0.0), (0.0, 0.0)], 'ocean', 128)
    # continents
    for poly, col in zip(LAND, LAND_COL):
        pts = simple_closed([P(la, lo) for la, lo in poly], 2)
        flat_shape(m, pts, -0.01, LAND_H, col, 0.014)
    for poly in SAND:
        pts = simple_closed([P(la, lo) for la, lo in poly], 3)
        flat_shape(m, pts, LAND_H - 0.006, LAND_H + 0.005, 'sand', 0.006)
    # north-pole sea-ice cap (flat, between the two sumos' feet)
    flat_shape(m, simple_closed(blob(random.Random(3), 0.3, 10, 0.18), 2), -0.01, 0.012, 'ice', 0.008)
    # the ring line: soft pale band at r = 4.6 (latitude -60)
    m.sweep(lambda a: [(RING_R - 0.075, -0.01), (RING_R + 0.075, -0.01), (RING_R + 0.075, 0.012), (RING_R + 0.06, 0.018),
                       (RING_R - 0.06, 0.018), (RING_R - 0.075, 0.012)], U(160), 'ring_line', closed=True)
    me = m.finish('MOD_Earth', sharp=60)
    # land sides a touch deeper green
    paint(me, 'land_dk', lambda p: p.normal.z < 0.5 and p.center.z > -0.012 and p.center.z < LAND_H - 0.004 and Vector((p.center.x, p.center.y)).length < RING_R)
    return me

# ---- the ice wall (static): chunky soft icy crest all round the edge, rolling down into the pale icy top band of the side
NBLK = 36
BLK = [RNG.uniform(0.0, 1.0) for _ in range(NBLK)]
def ice_h(a):
    t = (a / (2 * math.pi)) * NBLK; i = int(t) % NBLK; f = t - int(t)
    j = (i + 1) % NBLK
    s = f * f * (3 - 2 * f); s = s ** 2 * (3 - 2 * s)                   # soft steps between chunky blocks
    v = BLK[i] * (1 - s) + BLK[j] * s
    return 0.18 + 0.12 * v
def mod_icewall():
    m = MB()
    def prof(a):
        h = ice_h(a); wob = 0.025 * math.sin(7 * a) + 0.015 * math.sin(13 * a + 1)
        ri = ICE_IN + 0.5 * wob; ro = RD + 0.06 + wob
        return [(ri, -0.04), (ri + 0.005, 0.05), (ri + 0.04, h - 0.06), (ri + 0.1, h - 0.01), (ri + 0.18, h),
                (ro - 0.16, h - 0.005), (ro - 0.06, h - 0.04), (ro - 0.01, h - 0.11), (ro, 0.05), (ro - 0.005, -0.12),
                (ro - 0.03, -0.24), (ro - 0.08, -0.29), (ro - 0.16, -0.3), (ri + 0.02, -0.3), (ri, -0.2)]
    m.sweep(prof, U(176), 'ice', closed=True)
    me = m.finish('MOD_IceWall', sharp=55)
    paint(me, 'ice_lt', lambda p: p.normal.z > 0.55 and p.center.z > 0.1)
    return me

# ---- the crust: soft pastel rock / earth layers, slightly lumpy, tapering under the disc ------------------------------
STRATA = [(-0.26, -0.62, 'rock1'), (-0.62, -0.98, 'rock2'), (-0.98, -1.32, 'rock3'), (-1.32, -9.0, 'rock4')]
def mod_crust():
    m = MB()
    def prof(a):
        w = lambda k: 0.035 * math.sin(5 * a + k * 1.7) + 0.025 * math.sin(11 * a + k * 2.9) + 0.015 * math.sin(17 * a + k)
        r1 = RD + 0.01 + w(0); r2 = RD - 0.01 + w(1); r3 = RD - 0.05 + w(2); r4 = RD - 0.1 + w(3)   # near-vertical: the camera looks down ~59 deg
        return [(0.0, -1.95),
                (r4 * 0.5, -1.98), (r4 * 0.8, -1.9), (r4 * 0.95, -1.76), (r4, -1.6), (r4 * 1.005, -1.38), (r4 - 0.04, -1.33),
                (r3 - 0.05, -1.32), (r3, -1.28), (r3 + 0.02, -1.14), (r3, -1.01), (r3 - 0.05, -0.98),
                (r2 - 0.05, -0.97), (r2, -0.93), (r2 + 0.02, -0.79), (r2, -0.65), (r2 - 0.04, -0.62),
                (r1 - 0.04, -0.62), (r1, -0.58), (r1 + 0.02, -0.44), (r1, -0.3), (r1 - 0.05, -0.27), (RD - 0.3, -0.24),
                (0.0, -0.24)]
    m.sweep(prof, U(112), 'rock1')
    me = m.finish('MOD_Crust', sharp=50)
    def col(p):
        z = p.center.z
        for z0, z1, c in STRATA:
            if z1 <= z < z0: return c
        return None
    uvl = me.uv_layers['PAL']
    for p in me.polygons:
        c = col(p)
        if c:
            # the ledge tops (upward faces) of each band take the paler tone of the band above
            if p.normal.z > 0.6 and p.center.z < -0.3:
                c = {'rock2': 'rock1', 'rock3': 'rock2', 'rock4': 'rock3'}.get(c, c)
            u = swuv(c)
            for li in p.loop_indices: uvl.data[li].uv = u
    return me

# ---- a few chunky floating rocks under the disc --------------------------------------------------------------------
def mod_rock(k, r):
    m = MB(); R = random.Random(20 + k)
    m.ico(0, 0, 0, r, 'rock2', 2, sq=(1.0, 0.9, 0.72), jit=0.12)
    me = m.finish('MOD_Rock%d' % k, sharp=50)
    paint(me, 'rock1', lambda p: p.normal.z > 0.45)
    paint(me, 'rock3', lambda p: p.normal.z < -0.45)
    return me

# ---- soft clouds (pale, lilac undersides) ----------------------------------------------------------------------------
def mod_cloud(k, w):
    m = MB(); R = random.Random(40 + k); n = 5
    for i in range(n):
        t = (i / (n - 1) - 0.5) * 2
        r = w * (0.34 - 0.14 * abs(t)) * R.uniform(0.9, 1.1)
        m.ico(t * w * 0.42, R.uniform(-0.15, 0.15) * w * 0.3, r * 0.25, r, 'foam', 3, sq=(1.1, 0.85, 0.82))
    m.ico(0.0, 0.0, w * 0.12, w * 0.3, 'foam', 3, sq=(1.15, 0.85, 0.85))
    me = m.finish('MOD_Cloud%d' % k, sharp=70)
    paint(me, 'lilac', lambda p: p.normal.z < -0.35)
    return me

# ---- backdrop: chunky soft stars, a little cartoon sun and a crescent moon (flat shapes turned to the camera) ----------
def star_pts(r, k=5, inner=0.5):
    pts = []
    for i in range(2 * k):
        a = math.pi / 2 + math.pi * i / k; rr = r if i % 2 == 0 else r * inner
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return chaikin(pts, 1)
def mod_star(k, r, col):
    m = MB(); m.prism(fillet(star_pts(r, 5, 0.5), 0.08 * r, 2), -0.06 * r, 0.06 * r, col, bev=0.07 * r, bseg=1)
    return m.finish('MOD_Star%d' % k, sharp=70)
def mod_dot(k, r, col):
    m = MB(); m.prism(circle(r, 12), -0.08 * r, 0.08 * r, col, bev=0.1 * r, bseg=1)
    return m.finish('MOD_Dot%d' % k, sharp=70)
def mod_sun():
    m = MB(); R0 = 1.25
    m.prism(circle(R0, 40), -0.1, 0.1, 'sun', bev=0.08, bseg=2)
    m.prism(circle(R0 * 0.74, 36), 0.1, 0.14, 'sun_lt', bev=0.03, bseg=1)
    for i in range(10):
        a = 2 * math.pi * i / 10 + 0.15
        tri = [(R0 + 0.22, -0.26), (R0 + 0.82, 0.0), (R0 + 0.22, 0.26)]
        tri = chaikin(tri, 2)
        m.prism(tri, -0.07, 0.07, 'sun', M=Rz(math.degrees(a)), bev=0.04, bseg=1)
    return m.finish('MOD_Sun', sharp=70)
def mod_moon():
    m = MB(); R0 = 1.15; cb = Vector((-0.5, 0.28)); rb = 0.98
    # crescent = moon disc minus an offset disc
    def inB(p): return (Vector(p) - cb).length < rb
    N = 720; A = [(R0 * math.cos(2 * math.pi * i / N), R0 * math.sin(2 * math.pi * i / N)) for i in range(N)]
    s = next(i for i in range(N) if inB(A[i]) and not inB(A[i - 1]))      # A leaves the bite here (going ccw: enters B)
    e = next(i for i in range(N) if not inB(A[i]) and inB(A[i - 1]))
    outer = []; i = e
    while i != s: outer.append(A[i]); i = (i + 1) % N
    ta = math.atan2(A[s][1] - cb.y, A[s][0] - cb.x); tb = math.atan2(A[e][1] - cb.y, A[e][0] - cb.x)
    while tb > ta: tb -= 2 * math.pi
    inner = [(cb.x + rb * math.cos(ta + (tb - ta) * k / 16), cb.y + rb * math.sin(ta + (tb - ta) * k / 16)) for k in range(17)]
    pts = outer[::24] + inner[1:-1]
    pts = fillet(pts, 0.08, 2)
    m.prism(pts, -0.09, 0.09, 'moon', bev=0.06, bseg=2)
    return m.finish('MOD_Moon', sharp=70)

for f in (mod_earth, mod_icewall, mod_crust, mod_sun, mod_moon): f()
for k, r in enumerate((0.55, 0.42, 0.36)): mod_rock(k, r)
for k, w in enumerate((3.2, 2.4, 2.8, 2.0)): mod_cloud(k, w)
for k, (r, c) in enumerate(((0.62, 'star'), (0.45, 'star'), (0.34, 'star_lt'), (0.5, 'star_lt'))): mod_star(k, r, c)
for k, (r, c) in enumerate(((0.16, 'star'), (0.12, 'star_lt'), (0.2, 'star_lt'))): mod_dot(k, r, c)

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Earth', 'SPIN_Earth', c='ENV_SPIN')                       # the game may spin this about its origin
place('MOD_IceWall', 'DISC_IceWall', c='ENV_DISC')
place('MOD_Crust', 'DISC_Crust', c='ENV_DISC')
for k, (x, y, z, rz) in enumerate(((-4.6, -2.6, -2.75, 20), (5.2, -1.2, -2.5, -35), (3.8, -4.4, -3.3, 60))):
    place('MOD_Rock%d' % k, nm('SPACE_Rock'), (x, y, z), rz=rz, c='ENV_SPACE')
for k, (x, y, z, rz, s) in enumerate(((-7.0, -2.2, -1.7, 15, 1.0), (7.1, -1.0, -1.5, -20, 1.0), (-6.1, 3.6, -1.9, -10, 1.0), (6.4, 4.4, -2.1, 25, 1.0))):
    place('MOD_Cloud%d' % k, nm('SPACE_Cloud'), (x, y, z), rz=rz, s=s, c='ENV_SPACE')

# backdrop shapes placed in screen space (u, v from the bottom-left of the frame) at a depth along the camera ray,
# turned flat to the camera
TGT = Vector((0, 0.15, 0.2)); CAM_LOC = Vector((0, -13.93, 14.35))
CAM_Q = (TGT - CAM_LOC).to_track_quat('-Z', 'Y')
def screen_pt(u, v, d):
    th = math.tan(math.radians(17)); tw = th * 16 / 9
    return CAM_LOC + CAM_Q @ Vector(((u - 0.5) * 2 * tw * d, (v - 0.5) * 2 * th * d, -d))
def billboard(mod, name, u, v, d, s=1.0, roll=0.0):
    ob = place(mod, name, tuple(screen_pt(u, v, d)), s=s, c='ENV_SPACE')
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = CAM_Q @ Matrix.Rotation(math.radians(roll), 4, 'Z').to_quaternion()
    return ob
billboard('MOD_Sun', 'SPACE_Sun', 0.905, 0.80, 34, 1.0, -8)
billboard('MOD_Moon', 'SPACE_Moon', 0.095, 0.78, 34, 1.0, 18)
STARS = [  # (u, v, mod, roll)
    (0.06, 0.45, 'MOD_Star0', 8), (0.17, 0.92, 'MOD_Star1', -12), (0.2, 0.62, 'MOD_Star2', 20), (0.13, 0.2, 'MOD_Star3', -5),
    (0.27, 0.08, 'MOD_Star1', 14), (0.79, 0.93, 'MOD_Star3', 10), (0.95, 0.5, 'MOD_Star1', -18), (0.83, 0.62, 'MOD_Star2', 4),
    (0.88, 0.16, 'MOD_Star0', -10), (0.72, 0.06, 'MOD_Star2', 22), (0.36, 0.95, 'MOD_Star2', -8), (0.62, 0.96, 'MOD_Star1', 6),
]
for u, v, mod, rl in STARS: billboard(mod, nm('SPACE_Star'), u, v, 34, 1.0, rl)
DOTS = [(0.04, 0.88), (0.1, 0.62), (0.24, 0.8), (0.03, 0.3), (0.2, 0.36), (0.08, 0.06), (0.22, 0.2), (0.3, 0.86), (0.45, 0.97),
        (0.55, 0.93), (0.7, 0.87), (0.97, 0.94), (0.8, 0.78), (0.97, 0.7), (0.78, 0.4), (0.96, 0.32), (0.82, 0.28), (0.92, 0.05), (0.78, 0.12),
        (0.68, 0.98), (0.15, 0.5), (0.86, 0.48)]
for i, (u, v) in enumerate(DOTS): billboard('MOD_Dot%d' % (i % 3), nm('SPACE_Twinkle'), u, v, 34, 1.0)

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

# ---- render-only night sky: a camera-only emissive dome (soft indigo-violet, lighter round the disc, never black).
#      It hides the world from the camera only, so the world light (same as every kit) is untouched.
SKY_IN, SKY_OUT, SKY_TOP = '7d72b4', '4f4c8c', '5d5698'    # glow round the disc, frame corners, top of frame (sRGB)
ms_ = bpy.data.materials.new('M_SKY'); ms_.use_nodes = True; N = ms_.node_tree.nodes; N.clear(); Lk = ms_.node_tree.links.new
tc2 = N.new('ShaderNodeTexCoord'); sp2 = N.new('ShaderNodeSeparateXYZ'); Lk(tc2.outputs['Window'], sp2.inputs[0])
# aspect-corrected distance from a point a bit below the frame centre
dx = N.new('ShaderNodeMath'); dx.operation = 'SUBTRACT'; dx.inputs[1].default_value = 0.5; Lk(sp2.outputs['X'], dx.inputs[0])
dxs = N.new('ShaderNodeMath'); dxs.operation = 'MULTIPLY'; dxs.inputs[1].default_value = 16 / 9; Lk(dx.outputs[0], dxs.inputs[0])
dy = N.new('ShaderNodeMath'); dy.operation = 'SUBTRACT'; dy.inputs[1].default_value = 0.42; Lk(sp2.outputs['Y'], dy.inputs[0])
cmb = N.new('ShaderNodeCombineXYZ'); Lk(dxs.outputs[0], cmb.inputs['X']); Lk(dy.outputs[0], cmb.inputs['Y'])
ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; Lk(cmb.outputs[0], ln.inputs[0])
cr2 = N.new('ShaderNodeValToRGB'); Lk(ln.outputs['Value'], cr2.inputs['Fac'])
cr2.color_ramp.elements[0].position = 0.45; cr2.color_ramp.elements[0].color = (*hexlin(SKY_IN), 1)
cr2.color_ramp.elements[1].position = 1.0; cr2.color_ramp.elements[1].color = (*hexlin(SKY_OUT), 1)
# a gentle cooler tint towards the top of the frame
vt = N.new('ShaderNodeMapRange'); vt.inputs['From Min'].default_value = 0.6; vt.inputs['From Max'].default_value = 1.0
vt.inputs['To Max'].default_value = 0.55; Lk(sp2.outputs['Y'], vt.inputs['Value'])
mx2 = N.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; mx2.inputs['B'].default_value = (*hexlin(SKY_TOP), 1)
Lk(vt.outputs['Result'], mx2.inputs['Factor']); Lk(cr2.outputs['Color'], mx2.inputs['A'])
sc2 = N.new('ShaderNodeVectorMath'); sc2.operation = 'SCALE'; sc2.inputs['Scale'].default_value = 1 / 1.2; Lk(mx2.outputs['Result'], sc2.inputs[0])
em2 = N.new('ShaderNodeEmission'); Lk(sc2.outputs[0], em2.inputs['Color']); em2.inputs['Strength'].default_value = 1.0
o2 = N.new('ShaderNodeOutputMaterial'); Lk(em2.outputs[0], o2.inputs['Surface'])
bmd = bmesh.new(); bmesh.ops.create_uvsphere(bmd, u_segments=32, v_segments=16, radius=120)
bmesh.ops.reverse_faces(bmd, faces=bmd.faces)                      # faces the camera inside it
dme = bpy.data.meshes.new('SkyDome'); bmd.to_mesh(dme); bmd.free(); dme.materials.append(ms_)
dome = bpy.data.objects.new('SKY_Dome', dme); CN['LIGHTING'].objects.link(dome); dome.location = (0, -13.93, 14.35)
for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'): setattr(dome, a, False)
bg.inputs['Color'].default_value = (*hexlin(SKY_OUT), 1)

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
bpy.ops.export_scene.gltf(filepath=OUT + '/earth_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/earth_kit.blend')
if not NORENDER:
    exr = OUT + '/earth_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/earth_gamecam.png'] + comp, check=True)
print('DONE')
