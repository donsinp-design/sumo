# THE BATHHOUSE (stealth test level) as a Blender kit, in the approved option-2 "soft city" look, same method as the
# stage kits (stage_*_kit.py): one master material coloured from a 32x32 palette, bevelled soft shapes, nothing floating,
# no lettering but Japanese. The floor plan (and the game's colliders) come from bathhouse_layout.py.
#   <bl python> tools/blender/bathhouse_kit.py [norender] [lowres] [views=bath,wash,...]
# Output (scratchpad/bathkit): bathhouse_kit.glb, bathhouse_kit.blend, bh_<view>.png (game-camera approval renders)
# Roots in the glb: FLOORS, BUILDING, DETAILS (static); WATER; CRACK_WALL / CRACK_RUBBLE (before / after the charge);
#   LKDOOR_0..4 (his locker and the four round it, knocked off in the smash) and LKHOLES (dark hollows behind them);
#   prototypes the game clones: ITEM_STOOL, ITEM_OKE, ITEM_BUCKET, ITEM_WASHB, BOX, CLOTH_SHIRT, CLOTH_SHORTS
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/bathkit'
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
CN = {n: coll(n) for n in ('ENV_STAGE', 'ENV_PROPS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# =====================================================================================================================
# palette + master material (dohyo kit PAL; stage-only slots repurposed for the drum, the boards, curtain and lanterns)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('grout', 'c3d2d1'), ('tile', 'e6f0ee'), ('tile2', 'd9e8e6'), ('tile_dk', 'b5ccca'), ('tile_blue', '9fc4d6'), ('tile_navy', '5f87a8'), ('roof', '6f6872'),
    ('plaster', 'efe6d6'), ('plaster2', 'e2d6c2'), ('plaster_dk', 'c9bfb2'), ('offwhite', 'f2ede4'), ('stone', 'c4beb4'), ('stone2', 'aea89f'), ('roof2', '8c8079'), ('terracotta', 'cf7a5a'),
    ('hinoki', 'e8cb98'), ('hinoki_dk', 'd0a874'), ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('wood_dd', '6e4c38'), ('board', 'e6cfa4'), ('board2', 'd9be92'),
    ('tatami', 'd8d3a0'), ('tatami2', 'cdc792'), ('tatami_edge', '3f5a4a'), ('cushion', 'e59d86'), ('cushion2', '9db5cb'), ('rattan', 'd9b77e'), ('towel', 'f6f1e6'), ('towel_pk', 'f3c3c9'),
    ('glass', '7f9db8'), ('glass_lt', 'c4dde8'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('chrome', 'c3cbd2'), ('chrome_dk', '8f9ba8'), ('mirror', 'd4e7f0'), ('sky', 'a9d3ef'),
    ('fuji', '4f7fb8'), ('snow', 'faf8f2'), ('pine', '4f8f6a'), ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('metal', '9aa3ab'), ('brick', 'c98a6a'), ('orange', 'ef9a4c'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('mustard', 'e2b85e'), ('yellow', 'f2cf4a'), ('green', '3a9a5e'), ('green_dk', '2e7d4c'), ('navy', '2f4b7c'), ('blue', '5a8fd0'),
    ('pink', 'ef9ab2'), ('lilac', 'bdb3d3'), ('teal', '84b5ad'), ('sage', 'adc39d'), ('cardboard', 'd3a96e'), ('cardboard_dk', 'b98c52'), ('concrete', 'c9c0b4'), ('ink', '524b5a'),
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
img.filepath_raw = OUT + '/bath_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
# the floor plan (shared with the game)
# =====================================================================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bathhouse_layout as LY
UP = LY.UP
FONT = '/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf' if os.path.exists('/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf') else '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'

class GB(MB):
    """the module builder in GAME coordinates: x, z (towards the camera), y up."""
    def gbox(s, x0, x1, z0, z1, y0, y1, col, bev=0.0, seg=2):
        s.box(min(x0, x1), max(x0, x1), -max(z0, z1), -min(z0, z1), y0, y1, col, bev, seg)
    def gcyl(s, x, z, y, r, h, col, seg=14, r2=None, bev=0.0, axis='Z'):
        s.cyl(x, -z, y + (h / 2 if axis == 'Z' else 0), r, h, col, seg=seg, r2=r2, bev=bev, axis=axis)
    def gico(s, x, z, y, r, col, sub=2, sq=(1, 1, 1), jit=0.0):
        s.ico(x, -z, y, r, col, sub=sub, sq=sq, jit=jit)
    def gprism(s, pts, y0, y1, col, bev=0.0):
        s.prism([(x, -z) for x, z in pts], y0, y1, col, bev=bev)
    def quad(s, x0, x1, z0, z1, y, col):
        b = s._begin(); bm = s.bm
        vs = [bm.verts.new((x0, -z1, y)), bm.verts.new((x1, -z1, y)), bm.verts.new((x1, -z0, y)), bm.verts.new((x0, -z0, y))]
        bm.faces.new(vs); s._end(b, col, smooth=False)
    def vquad(s, pts, col):
        """a flat face from game points [(x, y, z), ...] (decals on walls)."""
        b = s._begin(); bm = s.bm; bm.faces.new([bm.verts.new((x, -z, y)) for x, y, z in pts]); s._end(b, col, smooth=False)
    def text(s, body, size, col, x, y, z, depth=0.02, face='z', align='CENTER'):
        """Japanese lettering as a thin solid, facing +z (towards the camera) or up ('y')."""
        cu = bpy.data.curves.new('txt', 'FONT'); cu.body = body; cu.size = size; cu.extrude = depth / 2; cu.align_x = align; cu.align_y = 'CENTER'
        try: cu.font = bpy.data.fonts.load(FONT, check_existing=True)
        except Exception: pass
        ob = bpy.data.objects.new('txt', cu); ROOT.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
        Mx = T(x, -z, y) @ (Rx(90) if face == 'z' else I4)
        b = s._begin(); vm = {}
        for v in me.vertices: vm[v.index] = s.bm.verts.new(Mx @ v.co)
        for p in me.polygons:
            try: s.bm.faces.new([vm[i] for i in p.vertices])
            except ValueError: pass
        s._end(b, col, smooth=False); bpy.data.meshes.remove(me)

def obj_from(mb, name, c='ENV_PROPS', loc=(0, 0, 0)):
    mb.finish('MOD_' + name); return place('MOD_' + name, name, loc, c=c)

def ylev(f): return UP if f else 0.0

# =====================================================================================================================
# floors and the outside
# =====================================================================================================================
def build_floors():
    m = GB()
    # the outside: a gravel lot and the street, round the whole building
    m.gbox(-40, 40, -110, 30, -0.3, -0.02, 'stone2')
    # ground floor
    def checker(x0, x1, z0, z1, y, c, a, b):
        nx = max(1, round((x1 - x0) / c)); nz = max(1, round((z1 - z0) / c)); dx = (x1 - x0) / nx; dz = (z1 - z0) / nz
        for i in range(nx):
            for j in range(nz): m.quad(x0 + i * dx, x0 + (i + 1) * dx, z0 + j * dz, z0 + (j + 1) * dz, y, a if (i + j) % 2 else b)
    checker(-12, 12, -16, 4.4, 0.0, 0.8, 'tile', 'tile2')                 # bath hall: pale tiles
    checker(-12, 12, -27, -16, 0.0, 0.8, 'tile', 'tile2')                 # wash area
    m.gbox(-12, 12, -47, -27, -0.06, 0.0, 'board')                        # changing room: wooden boards
    for k in range(40): m.gbox(-12, 12, -47 + k * 0.5 + 0.235, -47 + k * 0.5 + 0.265, 0.0, 0.004, 'board2')
    m.gbox(-12, 12, -53, -47, -0.06, 0.0, 'concrete')                     # staff corridor
    # bath: tub floor and walls (tiled, a blue band), the water is its own root
    P = LY.POOL
    m.gbox(P['x0'], P['x1'], P['z0'], P['z1'], -0.75, -0.7, 'tile_blue')
    for x0, x1, z0, z1 in [(P['x0'], P['x1'], P['z1'] - 0.02, P['z1']), (P['x0'], P['x1'], P['z0'], P['z0'] + 0.02), (P['x0'], P['x0'] + 0.02, P['z0'], P['z1']), (P['x1'] - 0.02, P['x1'], P['z0'], P['z1'])]:
        m.gbox(x0, x1, z0, z1, -0.7, 0.4, 'tile_navy')
    # the courtyard garden under the open sky (not walkable): gravel raked in lines, stepping stones, a pine, a stone lantern
    C = LY.COURTYARD
    m.gbox(C['x0'], C['x1'], C['z0'], C['z1'], -0.02, 0.04, 'offwhite')
    for k in range(14): m.gbox(C['x0'] + 0.3, C['x1'] - 0.3, C['z0'] + 0.3 + k * 0.5, C['z0'] + 0.34 + k * 0.5, 0.04, 0.05, 'stone')
    for i, (x, z) in enumerate([(-9, -55.5), (-7.4, -56.6), (-5.6, -57.2), (-3.8, -57.0), (-2.0, -56.2)]):
        m.gprism([(x + p[0], z + p[1]) for p in chaikin(blob(RNG, 0.55, 10, 0.2), 1)], 0.04, 0.14, 'stone2', bev=0.03)
    m.gcyl(2.6, -58.6, 0.05, 0.16, 1.4, 'wood_dk', seg=10, r2=0.12)
    for dx, dy, dz, r in [(0, 1.5, 0, 0.75), (0.7, 1.2, 0.3, 0.55), (-0.6, 1.25, -0.2, 0.55), (0.2, 1.95, 0.1, 0.5)]: m.gico(2.6 + dx, -58.6 + dz, dy, r, 'pine', sq=(1, 1, 0.55))
    m.gbox(-10.8, -10.2, -59.6, -59.0, 0.04, 0.55, 'stone', bev=0.04); m.gbox(-11.0, -10.0, -59.8, -58.8, 0.55, 0.75, 'stone', bev=0.06)
    m.gbox(-10.75, -10.25, -59.55, -59.05, 0.75, 1.05, 'stone2', bev=0.04); m.gbox(-11.1, -9.9, -59.9, -58.7, 1.05, 1.2, 'stone', bev=0.08)
    for x, z in [(-6.5, -59.6), (-1.5, -54.4), (4.8, -55.0)]: m.gico(x, z, 0.35, 0.5, 'leaf', sq=(1.2, 1, 0.7), jit=0.12)
    # bamboo fence round the courtyard (low)
    for x0, x1, z0, z1 in [(C['x0'], C['x1'], C['z1'] - 0.1, C['z1']), (C['x0'], C['x0'] + 0.1, C['z0'], C['z1']), (C['x1'] - 0.1, C['x1'], C['z0'], C['z1'])]:
        m.gbox(x0, x1, z0, z1, 0.0, 0.9, 'sage', bev=0.02)
    # the building mass under the upper floor: plaster with a wooden band (seen from the stairs and the garden)
    m.gbox(-12.4, 12.4, -92.4, -61, 0.0, UP - 0.06, 'plaster2')
    m.gbox(-12.45, 12.45, -61.05, -60.95, UP - 0.5, UP - 0.06, 'wood_dk')
    for x in range(-12, 7, 3): m.gbox(x - 0.08, x + 0.08, -61.04, -60.96, 0.0, UP - 0.5, 'wood')
    # stair foot walls are in the layout; the stairs themselves
    S_ = LY.STAIRS; n = S_['steps']
    for k in range(n):
        z1 = S_['z1'] - k * 0.5; y1 = UP * (k + 1) / n
        m.gbox(S_['x0'], S_['x1'], z1 - 0.5, z1, 0.0, y1 - 0.04, 'wood_lt'); m.gbox(S_['x0'], S_['x1'], z1 - 0.5, z1 - 0.02, y1 - 0.04, y1, 'wood', bev=0.015)
    for x in (S_['x0'] + 0.12, S_['x1'] - 0.12):   # handrails on brackets along both stair walls
        for k in range(0, n, 4):
            z = S_['z1'] - k * 0.5 - 0.25; m.gbox(x - 0.03, x + 0.03, z - 0.03, z + 0.03, UP * k / n, UP * k / n + 0.9, 'chrome_dk')
    Lr = math.hypot(S_['z1'] - S_['z0'], UP); ang = math.degrees(math.atan2(UP, S_['z1'] - S_['z0']))
    for x in (S_['x0'] + 0.12, S_['x1'] - 0.12):
        m.box(-0.045, 0.045, -Lr / 2, Lr / 2, -0.045, 0.045, 'wood_dk', bev=0.02, M=T(x, -(S_['z1'] + S_['z0']) / 2, 0.9 + UP / 2) @ Rx(ang))
    # upper floor: wooden boards; the genkan is stone, a step down; the staff office and storage plain boards
    m.gbox(-12, 12, -86, -61, UP - 0.06, UP, 'board')
    for k in range(50): m.gbox(-12, 12, -86 + k * 0.5 + 0.235, -86 + k * 0.5 + 0.265, UP, UP + 0.004, 'board2')
    G = LY.GENKAN
    m.gbox(-12, -4, -92, -86, UP - 0.06, UP - 0.02, 'stone'); m.gbox(G['x0'], G['x1'], G['z0'], -76, UP - 0.06, UP + 0.001, 'stone')
    for i in range(8):
        for j in range(8): m.quad(-12 + i, -11 + i, -92 + j * 2, -90 + j * 2, UP + 0.003, 'stone' if (i + j) % 2 else 'stone2') if -92 + j * 2 < -76 else None
    m.gbox(-4.12, -3.88, -92, -76, UP, UP + 0.1, 'wood_dk', bev=0.02)            # the step up from the genkan (agari-kamachi)
    m.gbox(-4, 12, -92, -86, UP - 0.06, UP, 'board2')
    # the upper floor seen from outside: tiled roof eaves round it, a step down
    for x0, x1, z0, z1 in [(-14.4, 14.4, -94.4, -92.4), (-14.4, -12.4, -92.4, -61), (12.4, 14.4, -92.4, -61)]:
        m.gbox(x0, x1, z0, z1, UP - 0.6, UP - 0.45, 'roof', bev=0.04)
    for k in range(-14, 15):
        m.gbox(k - 0.05, k + 0.05, -94.4, -92.4, UP - 0.45, UP - 0.4, 'roof2')
    # the neighbourhood: plaster houses with tiled pitched roofs all round (so past the walls there are rooftops, not a blank)
    R2 = random.Random(3)
    def house(x0, x1, z0, z1, hh, along_x):
        m.gbox(x0, x1, z0, z1, 0.0, hh, R2.choice(['plaster', 'plaster2', 'offwhite', 'board']), bev=0.04)
        ridge = hh + 1.1; c = R2.choice(['roof', 'roof2', 'tile_navy', 'red_dk'])
        if along_x:
            zm = (z0 + z1) / 2
            for a, b in ((z0 - 0.3, zm), (z1 + 0.3, zm)):
                bb = m._begin(); bm = m.bm
                v = [bm.verts.new((x0 - 0.3, -a, hh - 0.15)), bm.verts.new((x1 + 0.3, -a, hh - 0.15)), bm.verts.new((x1 + 0.3, -b, ridge)), bm.verts.new((x0 - 0.3, -b, ridge))]
                bm.faces.new(v); m._end(bb, c, smooth=False)
        else:
            xm = (x0 + x1) / 2
            for a, b in ((x0 - 0.3, xm), (x1 + 0.3, xm)):
                bb = m._begin(); bm = m.bm
                v = [bm.verts.new((a, -(z0 - 0.3), hh - 0.15)), bm.verts.new((a, -(z1 + 0.3), hh - 0.15)), bm.verts.new((b, -(z1 + 0.3), ridge)), bm.verts.new((b, -(z0 - 0.3), ridge))]
                bm.faces.new(v); m._end(bb, c, smooth=False)
    z = 6.0
    while z > -108:
        d = R2.uniform(5, 8)
        house(-24, -16.5, z - d + 0.6, z, R2.uniform(1.8, 2.5), False); house(16.5, 24, z - d + 0.6, z, R2.uniform(1.8, 2.5), False); z -= d
    x = -24.0
    while x < 24:
        w_ = R2.uniform(5, 8); house(x, x + w_ - 0.6, -104, -96.5, R2.uniform(1.6, 2.2), True); x += w_
    for x, z in [(-15, -20), (-15, -40), (15, -10), (15, -45), (-15, 0), (15, -80), (-15.5, -84)]:
        m.gico(x, z, 0.6, 0.9, 'leaf', sq=(1, 1, 0.8), jit=0.12); m.gico(x + 0.4, z - 0.3, 1.1, 0.6, 'leaf_lt', jit=0.1)
    return obj_from(m, 'FLOORS', 'ENV_STAGE')

def build_water():
    m = GB(); P = LY.POOL
    m.gbox(P['x0'], P['x1'], P['z0'], P['z1'], P['water'] - 0.02, P['water'], 'water')
    m.gbox(P['steps'][0], P['steps'][1], P['z1'], -1.8, P['water'] - 0.02, P['water'], 'water')
    return obj_from(m, 'WATER', 'ENV_STAGE')

# =====================================================================================================================
# solids from the floor plan
# =====================================================================================================================
WALLCOL = {'plaster': ('plaster', 'wood'), 'plaster_dk': ('plaster_dk', 'wood_dk'), 'tile': ('tile', 'tile_dk'), 'wood': ('wood_lt', 'wood_dk'), 'metal': ('metal', 'chrome_dk'), 'glass': ('glass_lt', 'wood')}
def w_wall(m, s, y):
    body, trim = WALLCOL.get(s.get('col', 'plaster'), ('plaster', 'wood'))
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    if s.get('col') == 'glass':      # frosted glass in wooden frames
        m.gbox(x0, x1, z0, z1, y, y + 0.12, 'wood', bev=0.02); m.gbox(x0, x1, z0, z1, y + h - 0.1, y + h, 'wood', bev=0.02)
        L = x1 - x0; n = max(1, round(L / 1.6))
        for i in range(n + 1): xx = x0 + L * i / n; m.gbox(max(x0, xx - 0.06), min(x1, xx + 0.06), z0, z1, y, y + h, 'wood', bev=0.02)
        m.gbox(x0, x1, z0 + 0.12, z1 - 0.12, y + 0.12, y + h - 0.1, 'glass_lt'); return
    m.gbox(x0, x1, z0, z1, y, y + h, body, bev=0.025)
    m.gbox(x0 - 0.03, x1 + 0.03, z0 - 0.03, z1 + 0.03, y + h - 0.02, y + h + 0.07, trim, bev=0.03)
    m.gbox(x0 - 0.015, x1 + 0.015, z0 - 0.015, z1 + 0.015, y, y + 0.12, trim)                           # skirting
    if s.get('col') == 'tile':
        hz = (z1 - z0) > (x1 - x0)
        L = (z1 - z0) if hz else (x1 - x0)
        for k in range(1, int(L / 0.6)):
            p = (z0 if hz else x0) + k * 0.6
            if hz: m.gbox(x0 - 0.008, x1 + 0.008, p - 0.012, p + 0.012, y + 0.12, y + h - 0.02, 'grout')
            else: m.gbox(x0 + k * 0.6 - 0.012, x0 + k * 0.6 + 0.012, z0 - 0.008, z1 + 0.008, y + 0.12, y + h - 0.02, 'grout')
        for yy in (0.5, 0.85): m.gbox(x0 - 0.008, x1 + 0.008, z0 - 0.008, z1 + 0.008, y + yy - 0.012, y + yy + 0.012, 'grout')

def w_mural(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h, 'tile', bev=0.025); m.gbox(x0 - 0.03, x1 + 0.03, z0 - 0.03, z1 + 0.03, y + h - 0.02, y + h + 0.07, 'tile_dk', bev=0.03)
    f = z1 + 0.004                                                       # the face towards the bath
    def face(pts, col, d=0.0):
        m.vquad([(x, yy, f + d) for x, yy in pts], col)
    face([(x0 + 0.05, 0.25), (x1 - 0.05, 0.25), (x1 - 0.05, h - 0.06), (x0 + 0.05, h - 0.06)], 'sky')
    cx = (x0 + x1) / 2
    face([(cx - 3.2, 0.25), (cx + 3.4, 0.25), (cx + 0.35, 1.72), (cx - 0.25, 1.72)], 'fuji', 0.003)
    face([(cx - 0.95, 1.38), (cx - 0.25, 1.72), (cx + 0.35, 1.72), (cx + 1.05, 1.38), (cx + 0.6, 1.46), (cx + 0.3, 1.36), (cx, 1.48), (cx - 0.35, 1.36), (cx - 0.6, 1.46)], 'snow', 0.006)
    for cxx, cy, r in [(x0 + 1.3, 1.55, 0.22), (x0 + 1.65, 1.6, 0.28), (x0 + 2.0, 1.53, 0.2), (x1 - 1.6, 1.62, 0.22), (x1 - 1.25, 1.66, 0.27), (x1 - 0.9, 1.6, 0.2)]:
        face([(cxx + r * math.cos(a), cy + r * 0.7 * math.sin(a)) for a in U(14)], 'snow', 0.005)
    xx = x0 + 0.1
    while xx < x1 - 0.4:
        hh = 0.32 + 0.12 * math.sin(xx * 3.1)
        face([(xx, 0.25), (xx + 0.42, 0.25), (xx + 0.21, 0.25 + hh)], 'pine' if int(xx * 2) % 2 else 'leaf', 0.008); xx += 0.36
    face([(x0 + 0.05, 0.12), (x1 - 0.05, 0.12), (x1 - 0.05, 0.27), (x0 + 0.05, 0.27)], 'tile_navy', 0.009)
    for k in range(1, int((x1 - x0) / 0.6)):                               # the tile grid over the painting
        xx = x0 + k * 0.6; face([(xx - 0.008, 0.12), (xx + 0.008, 0.12), (xx + 0.008, h - 0.06), (xx - 0.008, h - 0.06)], 'grout', 0.011)
    for yy in (0.72, 1.32):
        face([(x0 + 0.05, yy - 0.008), (x1 - 0.05, yy - 0.008), (x1 - 0.05, yy + 0.008), (x0 + 0.05, yy + 0.008)], 'grout', 0.011)

def w_rim(m, s, y):
    m.gbox(s['x0'], s['x1'], s['z0'], s['z1'], y, y + s['h'], 'hinoki', bev=0.06, seg=3)
    m.gbox(s['x0'] + 0.04, s['x1'] - 0.04, s['z0'] + 0.04, s['z1'] - 0.04, y + s['h'] - 0.01, y + s['h'] + 0.015, 'hinoki_dk', bev=0.02)

def w_washrow(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']; east = s.get('side') == 'e'
    m.gbox(x0, x1, z0, z1, y, y + 0.5, 'tile2', bev=0.03); m.gbox(x0 - 0.02, x1 + 0.02, z0 - 0.02, z1 + 0.02, y + 0.5, y + 0.56, 'tile_dk', bev=0.02)
    wx = x1 - 0.12 if east else x0 + 0.12          # backboard against the wall: mirrors
    bx0, bx1 = (x1 - 0.14, x1) if east else (x0, x0 + 0.14)
    n = max(1, int((z1 - z0) / 1.3))
    for i in range(n):
        zc = z0 + (i + 0.5) * (z1 - z0) / n
        m.gbox(bx0, bx1, zc - 0.42, zc + 0.42, y + 0.56, y + 1.1, 'tile_dk', bev=0.02)
        m.gbox(bx0 + (0 if east else 0.14), bx1 - (0.14 if east else 0) + (0.01 if east else 0.0), zc - 0.36, zc + 0.36, y + 0.62, y + 1.04, 'mirror') if False else None
        mxf = (bx0 - 0.01) if east else (bx1 + 0.01)
        m.vquad([(mxf, y + 0.64, zc - 0.34), (mxf, y + 0.64, zc + 0.34), (mxf, y + 1.04, zc + 0.34), (mxf, y + 1.04, zc - 0.34)] if east else
                [(mxf, y + 0.64, zc + 0.34), (mxf, y + 0.64, zc - 0.34), (mxf, y + 1.04, zc - 0.34), (mxf, y + 1.04, zc + 0.34)], 'mirror')
        tx = (x0 + 0.1) if east else (x1 - 0.1)    # two taps (hot red / cold blue) and a shower head on its hook
        for dz, col in ((-0.16, 'red'), (0.16, 'blue')):
            m.gcyl(tx, zc + dz, y + 0.56, 0.035, 0.1, 'chrome'); m.gcyl(tx, zc + dz, y + 0.66, 0.05, 0.035, col)
        m.gcyl((bx0 - 0.05) if east else (bx1 + 0.05), zc + 0.3, y + 0.56, 0.03, 0.5, 'chrome_dk', seg=8)
        m.gcyl((bx0 - 0.07) if east else (bx1 + 0.07), zc + 0.3, y + 1.06, 0.06, 0.06, 'chrome', seg=10)
        m.gcyl(tx + (0.05 if east else -0.05), zc - 0.38, y + 0.56, 0.05, 0.12, 'pink' if i % 2 else 'teal', seg=10, bev=0.01)   # a shampoo bottle

def w_washisland(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']; zc = (z0 + z1) / 2
    m.gbox(x0, x1, z0, z1, y, y + 0.5, 'tile2', bev=0.03); m.gbox(x0 - 0.02, x1 + 0.02, z0 - 0.02, z1 + 0.02, y + 0.5, y + 0.56, 'tile_dk', bev=0.02)
    m.gbox(x0 + 0.1, x1 - 0.1, zc - 0.08, zc + 0.08, y + 0.56, y + 0.95, 'tile_dk', bev=0.02)
    n = max(1, int((x1 - x0) / 1.3))
    for i in range(n):
        xc = x0 + (i + 0.5) * (x1 - x0) / n
        for sd in (-1, 1):
            f = zc + sd * 0.09
            pts = [(xc - 0.36, y + 0.6, f), (xc + 0.36, y + 0.6, f), (xc + 0.36, y + 0.92, f), (xc - 0.36, y + 0.92, f)]
            m.vquad(pts if sd > 0 else pts[::-1], 'mirror')
            for dx, col in ((-0.16, 'red'), (0.16, 'blue')):
                m.gcyl(xc + dx, zc + sd * 0.35, y + 0.56, 0.035, 0.1, 'chrome'); m.gcyl(xc + dx, zc + sd * 0.35, y + 0.66, 0.05, 0.035, col)

def door_panels(x0, x1, zf, y, rows, col, plate, sd):
    """a run of locker doors on the face at z = zf (sd: +1 faces +z)."""
    pass

LOCKER_DOORS = []   # (x, y0) of the five doors round his locker that burst open
def w_lockers(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h, 'wood', bev=0.03)
    m.gbox(x0 - 0.03, x1 + 0.03, z0 - 0.03, z1 + 0.03, y + h - 0.02, y + h + 0.06, 'wood_dk', bev=0.03)
    m.gbox(x0 + 0.03, x1 - 0.03, z0 - 0.01, z1 + 0.01, y, y + 0.08, 'wood_dd')
    n = round((x1 - x0) / 0.6); pitch = (x1 - x0) / n
    mine = LY.LOCKER; bank_is_mine = abs(s['x0'] - 4) < 1e-6 and abs(s['z0'] + 36.7) < 1e-6
    for sd, zf in ((1, z1), (-1, z0)):
        for i in range(n):
            xc = x0 + (i + 0.5) * pitch
            for r, (ya, yb) in enumerate(((0.12, 0.88), (0.94, 1.7))):
                special = bank_is_mine and sd == 1 and any(abs(xc - dx) < 0.05 and abs(ya - dy) < 0.05 for dx, dy in LOCKER_DOOR_SLOTS)
                if special: continue
                m.gbox(xc - pitch / 2 + 0.035, xc + pitch / 2 - 0.035, zf - 0.02 if sd > 0 else zf - 0.015, zf + 0.015 if sd > 0 else zf + 0.02, y + ya, y + yb, 'wood_lt', bev=0.012, seg=1)
                m.gbox(xc + pitch / 2 - 0.2, xc + pitch / 2 - 0.08, zf - 0.02 if sd > 0 else zf - 0.04, zf + 0.04 if sd > 0 else zf + 0.02, y + yb - 0.3, y + yb - 0.12, 'board')   # wooden key plate

def build_locker_doors():
    """his locker and its neighbours: separate roots (the game knocks them off), with dark hollows behind (hidden)."""
    out = []; fz = LY.LOCKER['face']
    for k, (x, ya) in enumerate(LOCKER_DOOR_SLOTS):
        m = GB(); yb = ya + 0.76
        m.gbox(-0.255, 0.255, -0.035, 0.0, -(yb - ya) / 2, (yb - ya) / 2, 'wood_lt', bev=0.012)
        m.gbox(0.12, 0.23, 0.0, 0.02, (yb - ya) / 2 - 0.3, (yb - ya) / 2 - 0.12, 'board', bev=0.01)
        if k == 0:   # his: number 8 on a little yellow tag
            m.gbox(-0.14, 0.06, 0.0, 0.012, 0.05, 0.25, 'yellow', bev=0.01); m.text('8', 0.16, 'dark', -0.04, 0.15, 0.016, depth=0.008)
        ob = obj_from(m, 'LKDOOR_%d' % k, 'ENV_DYN', (x, -(fz + 0.035), (ya + yb) / 2)); out.append(ob)
    h = GB()
    for x, ya in LOCKER_DOOR_SLOTS:
        h.gbox(x - 0.26, x + 0.26, fz - 0.02, fz - 0.005, ya, ya + 0.76, 'dark')
        h.gbox(x - 0.24, x + 0.24, fz - 0.03, fz - 0.015, ya + 0.02, ya + 0.04, 'wood_dk')
    obj_from(h, 'LKHOLES', 'ENV_DYN')
    return out

def w_bench(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    if s['f']: m.gbox(x0, x1, z1 - 0.08, z1 + 0.0, y + 0.42, y + 0.9, 'wood_lt', bev=0.03) if False else None
    for k in range(3):
        zz = z0 + (k + 0.5) * (z1 - z0) / 3; m.gbox(x0, x1, zz - 0.09, zz + 0.09, y + h - 0.07, y + h, 'wood_lt', bev=0.02)
    for xx in (x0 + 0.25, x1 - 0.25):
        m.gbox(xx - 0.06, xx + 0.06, z0 + 0.04, z1 - 0.04, y, y + h - 0.07, 'wood_dk', bev=0.015)
    m.gbox(x0 + 0.3, x1 - 0.3, (z0 + z1) / 2 - 0.03, (z0 + z1) / 2 + 0.03, y + 0.12, y + 0.18, 'wood_dk')

def w_vanity(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']
    m.gbox(x0, x1, z0, z1, y, y + 0.8, 'wood', bev=0.03); m.gbox(x0 - 0.03, x1, z0 - 0.03, z1 + 0.03, y + 0.8, y + 0.86, 'offwhite', bev=0.02)
    m.gbox(x1 - 0.1, x1, z0, z1, y + 0.86, y + 1.15, 'wood_dk', bev=0.02)
    for i in range(3):
        zc = z0 + (i + 0.5) * (z1 - z0) / 3
        m.vquad([(x1 - 0.105, y + 0.88, zc - 0.5), (x1 - 0.105, y + 0.88, zc + 0.5), (x1 - 0.105, y + 1.12, zc + 0.5), (x1 - 0.105, y + 1.12, zc - 0.5)][::-1], 'mirror')
        m.gcyl(x0 + 0.25, zc + 0.3, y + 0.86, 0.06, 0.16, 'lilac', seg=10, bev=0.02)        # a hair dryer standing on the counter
        m.gcyl(x0 - 0.45, zc, y, 0.2, 0.42, 'cushion2', seg=14, bev=0.04)                    # a round stool
    # a scale and a standing fan next to the vanity
    m.gbox(x0 - 1.2, x0 - 0.6, z0 - 0.9, z0 - 0.3, y, y + 0.12, 'offwhite', bev=0.03); m.gcyl(x0 - 0.9, z0 - 0.4, y + 0.12, 0.05, 0.75, 'chrome', seg=8)
    m.gcyl(x0 - 0.9, z0 - 0.4, y + 0.87, 0.22, 0.12, 'offwhite', seg=18, bev=0.03, axis='Z')
    m.gcyl(x0 - 0.9, z1 + 0.6, y, 0.22, 0.05, 'chrome_dk', seg=14); m.gcyl(x0 - 0.9, z1 + 0.6, y + 0.05, 0.03, 1.0, 'chrome', seg=8)
    m.gico(x0 - 0.9, z1 + 0.6, y + 1.15, 0.24, 'teal', sq=(1, 1, 0.45))

def w_baskets(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    for xx in (x0 + 0.04, x1 - 0.04):
        for zz in (z0 + 0.05, z1 - 0.05): m.gbox(xx - 0.04, xx + 0.04, zz - 0.04, zz + 0.04, y, y + h, 'wood_dk')
    for r in range(3):
        yy = y + 0.05 + r * 0.46; m.gbox(x0, x1, z0, z1, yy, yy + 0.04, 'wood', bev=0.01)
        n = int((z1 - z0) / 0.6)
        for i in range(n):
            zc = z0 + (i + 0.5) * (z1 - z0) / n
            m.gbox(x0 + 0.08, x1 - 0.04, zc - 0.25, zc + 0.25, yy + 0.04, yy + 0.3, 'rattan', bev=0.05)
            if (i + r) % 3 == 0: m.gbox(x0 + 0.15, x1 - 0.1, zc - 0.18, zc + 0.18, yy + 0.3, yy + 0.36, 'towel', bev=0.03)

def w_boiler(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']; xc = (x0 + x1) / 2; zc = (z0 + z1) / 2
    m.gbox(x0, x1, z0, z1, y, y + 0.35, 'brick', bev=0.03)                                   # brick plinth
    m.cyl(xc + 0.2, -zc, y + 0.95, 0.6, x1 - x0 - 0.7, 'metal', seg=20, axis='X', bev=0.05)   # the boiler drum, lying
    for dx in (-1.2, 0.0, 1.2): m.cyl(xc + 0.2 + dx, -zc, y + 0.95, 0.62, 0.08, 'chrome_dk', seg=20, axis='X')   # riveted bands
    m.gbox(x0 + 0.05, x0 + 0.55, z0 + 0.1, z1 - 0.05, y + 0.35, y + 1.25, 'brick', bev=0.03)    # the firebox at the end, its door shut
    m.gbox(x0 + 0.1, x0 + 0.5, z1 - 0.06, z1 + 0.0, y + 0.5, y + 0.95, 'dark', bev=0.02)
    m.gcyl(xc + 1.5, zc - 0.2, y + 1.4, 0.13, 0.25, 'chrome_dk', seg=12)                         # flue stub (cut away with the walls)
    for dx in (-0.6, 0.6): m.gcyl(xc + dx, zc - 0.3, y + 1.5, 0.05, 0.14, 'red', seg=10)        # valves on top
def w_firewood(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']
    for r in range(4):
        for i in range(int((x1 - x0) / 0.24) - (r % 2)):
            xx = x0 + 0.13 + i * 0.24 + (0.12 if r % 2 else 0)
            m.cyl(xx, -(z0 + z1) / 2, y + 0.12 + r * 0.21, 0.11, z1 - z0, 'hinoki_dk' if (i + r) % 3 else 'wood_lt', seg=7, axis='Y')

def w_towels(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z0 + 0.05, y, y + h, 'wood_dk')
    for r in range(3):
        yy = y + 0.1 + r * 0.48; m.gbox(x0, x1, z0, z1, yy, yy + 0.04, 'wood', bev=0.01)
        for i in range(int((x1 - x0) / 0.5)):
            xx = x0 + 0.08 + i * 0.5
            m.gbox(xx, xx + 0.4, z0 + 0.1, z1 - 0.06, yy + 0.04, yy + 0.33, ['towel', 'towel_pk', 'cushion2'][(i + r) % 3], bev=0.035)

def w_cart(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']
    for xx in (x0 + 0.1, x1 - 0.1):
        for zz in (z0 + 0.1, z1 - 0.1): m.gcyl(xx, zz, y, 0.07, 0.1, 'dark', seg=10)
    m.gbox(x0, x1, z0, z1, y + 0.12, y + 0.7, 'board', bev=0.05); m.gico((x0 + x1) / 2, (z0 + z1) / 2, y + 0.7, 0.45, 'towel', sq=(1.2, 0.8, 0.35))

def w_shelf(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    for xx in (x0 + 0.04, x1 - 0.04):
        for zz in (z0 + 0.04, z1 - 0.04): m.gbox(xx - 0.04, xx + 0.04, zz - 0.04, zz + 0.04, y, y + h, 'wood_dk')
    for r in range(4):
        yy = y + 0.05 + r * 0.45; m.gbox(x0, x1, z0, z1, yy, yy + 0.04, 'wood', bev=0.01)
        n = int((z1 - z0) / 0.7)
        for i in range(n):
            zc = z0 + (i + 0.5) * (z1 - z0) / n; c = ['cardboard', 'towel', 'cardboard_dk', 'towel_pk', 'teal'][(i * 3 + r) % 5]
            m.gbox(x0 + 0.1, x1 - 0.1, zc - 0.28, zc + 0.28, yy + 0.04, yy + 0.04 + (0.32 if c.startswith('card') else 0.2), c, bev=0.03)

def w_lowtable(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']; xc, zc = (x0 + x1) / 2, (z0 + z1) / 2; yt = y + LY.TATAMI['h']
    if s.get('plain'):   # a coffee table on a round rug
        m.gprism([(xc + 2.4 * math.cos(a), zc - 0.6 + 1.6 * math.sin(a)) for a in U(28)], y + 0.002, y + 0.014, 'cushion')
        m.gprism([(xc + 2.1 * math.cos(a), zc - 0.6 + 1.35 * math.sin(a)) for a in U(28)], y + 0.014, y + 0.018, 'pink')
        m.gbox(x0, x1, z0, z1, y + 0.32, y + 0.4, 'wood_dk', bev=0.03)
        for xx in (x0 + 0.1, x1 - 0.1):
            for zz in (z0 + 0.1, z1 - 0.1): m.gbox(xx - 0.04, xx + 0.04, zz - 0.04, zz + 0.04, y, y + 0.32, 'wood_dd')
        m.gcyl(xc - 0.4, zc, y + 0.4, 0.06, 0.12, 'offwhite', seg=12); m.gbox(xc + 0.1, xc + 0.6, zc - 0.2, zc + 0.15, y + 0.4, y + 0.43, 'mustard', bev=0.01)
        return
    m.gbox(x0, x1, z0, z1, yt + 0.28, yt + 0.34, 'wood_dd', bev=0.03)
    for xx in (x0 + 0.12, x1 - 0.12):
        for zz in (z0 + 0.12, z1 - 0.12): m.gbox(xx - 0.05, xx + 0.05, zz - 0.05, zz + 0.05, yt, yt + 0.28, 'wood_dd')
    m.gcyl(xc + 0.3, zc, yt + 0.34, 0.07, 0.08, 'offwhite', seg=12)                       # tea cups
    m.gcyl(xc - 0.25, zc + 0.1, yt + 0.34, 0.07, 0.08, 'offwhite', seg=12)
    for dx, dz in ((-1.15, 0), (1.15, 0), (0, 0.9)):
        m.gbox(xc + dx - 0.32, xc + dx + 0.32, zc + dz - 0.32, zc + dz + 0.32, yt, yt + 0.1, 'cushion', bev=0.05)

def w_massage(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']; xc = (x0 + x1) / 2
    m.gbox(x0 + 0.1, x1 - 0.1, z0, z1, y, y + 0.25, 'wood_dd', bev=0.05)
    m.gbox(x0 + 0.2, x1 - 0.2, z0 + 0.05, z1 - 0.3, y + 0.25, y + 0.5, 'cushion', bev=0.1)
    m.gbox(x0 + 0.2, x1 - 0.2, z1 - 0.38, z1 - 0.05, y + 0.45, y + 1.2, 'cushion', bev=0.12)
    for sd in (-1, 1): m.gbox(xc + sd * 0.62 - 0.12, xc + sd * 0.62 + 0.12, z0 + 0.05, z1 - 0.1, y + 0.25, y + 0.72, 'red_dk', bev=0.07)
    m.gbox(x0 + 0.3, x1 - 0.3, z0 - 0.45, z0 + 0.05, y, y + 0.32, 'red_dk', bev=0.07)             # footrest

def w_fridge(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h, 'offwhite', bev=0.04)
    m.gbox(x0 + 0.1, x1 - 0.1, z0 + 0.1, z1 - 0.1, y + 1.82, y + h + 0.02, 'navy', bev=0.02)
    # glass front (facing -x, into the lounge) with three shelves of bottled milk behind it
    fx = x0 - 0.005
    for r in range(4):
        yy = y + 0.25 + r * 0.38
        m.gbox(x0 + 0.06, x0 + 0.5, z0 + 0.12, z1 - 0.12, yy - 0.02, yy, 'chrome')
        for i in range(6):
            zz = z0 + 0.3 + i * (z1 - z0 - 0.6) / 5
            m.gcyl(x0 + 0.25, zz, yy, 0.075, 0.26, 'offwhite', seg=10, r2=0.06)
            m.gcyl(x0 + 0.25, zz, yy + 0.26, 0.065, 0.04, ['red', 'wood', 'orange', 'blue'][r], seg=10)
            m.gcyl(x0 + 0.25, zz, yy + 0.08, 0.077, 0.1, ['offwhite', 'wood_lt', 'orange', 'offwhite'][r], seg=10)
    m.gbox(fx - 0.01, fx, z0 + 0.08, z1 - 0.08, y + 0.15, y + 1.75, 'glass_lt')

def w_vending(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h, 'red', bev=0.04)
    m.gbox(x0 - 0.02, x0 + 0.02, z0 + 0.1, z1 - 0.1, y + 1.0, y + 1.75, 'offwhite', bev=0.01)
    for r in range(2):
        for i in range(5):
            zz = z0 + 0.25 + i * (z1 - z0 - 0.5) / 4
            m.gcyl(x0 - 0.02, zz, y + 1.08 + r * 0.33, 0.06, 0.22, ['blue', 'green', 'orange', 'mustard', 'teal'][(i + r) % 5], seg=10)
            m.gbox(x0 - 0.035, x0 - 0.02, zz - 0.04, zz + 0.04, y + 1.02 + r * 0.33, y + 1.05 + r * 0.33, 'yellow')
    m.gbox(x0 - 0.04, x0, z0 + 0.3, z1 - 0.3, y + 0.25, y + 0.45, 'dark', bev=0.02)

def w_manga(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z0 + 0.06, y, y + h, 'wood_dk')
    for xx in (x0 + 0.03, x1 - 0.03): m.gbox(xx - 0.03, xx + 0.03, z0, z1, y, y + h, 'wood_dk')
    for r in range(4):
        yy = y + 0.04 + r * 0.4; m.gbox(x0, x1, z0, z1, yy, yy + 0.03, 'wood', bev=0.01)
        xx = x0 + 0.08; i = 0
        while xx < x1 - 0.12:
            w = 0.05 + 0.02 * ((i * 7) % 3); hh = 0.26 + 0.05 * ((i * 5) % 3)
            m.gbox(xx, xx + w, z0 + 0.08, z1 - 0.04, yy + 0.03, yy + 0.03 + hh, ['red', 'navy', 'mustard', 'teal', 'pink', 'green', 'offwhite'][(i * 3 + r) % 7])
            xx += w + 0.008; i += 1

def w_sofa(m, s, y):
    x0, x1, z0, z1 = s['x0'], s['x1'], s['z0'], s['z1']
    m.gbox(x0, x1, z0, z1, y, y + 0.42, 'cushion2', bev=0.12, seg=3)
    m.gbox(x0, x1, z0, z0 + 0.25, y + 0.3, y + 0.8, 'cushion2', bev=0.11, seg=3)
    n = 3
    for i in range(n):
        xa = x0 + 0.1 + i * (x1 - x0 - 0.2) / n; m.gbox(xa + 0.03, xa + (x1 - x0 - 0.2) / n - 0.03, z0 + 0.22, z1 - 0.05, y + 0.42, y + 0.52, 'lilac', bev=0.05)

def w_desk(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h - 0.06, 'wood', bev=0.03)
    for k in range(int((x1 - x0) / 0.25)):                                            # vertical slats on the front
        xx = x0 + 0.12 + k * 0.25; m.gbox(xx - 0.035, xx + 0.035, z1 - 0.005, z1 + 0.02, y + 0.1, y + h - 0.12, 'wood_lt', bev=0.01)
    m.gbox(x0 - 0.06, x1 + 0.06, z0 - 0.06, z1 + 0.1, y + h - 0.06, y + h, 'wood_dk', bev=0.03)
    m.gbox(x0 + 0.04, x1 - 0.04, z1 - 0.01, z1 + 0.03, y, y + 0.1, 'wood_dd')
    # on the desk: a bell, the ticket box, a tray of soap and shampoo for sale, folded rental towels
    m.gcyl(7.6, -82.5, y + h, 0.09, 0.03, 'chrome_dk', seg=12); m.gico(7.6, -82.5, y + h + 0.05, 0.07, 'mustard', sq=(1, 1, 0.8))
    m.gbox(5.0, 5.6, -82.9, -82.4, y + h, y + h + 0.32, 'wood_dk', bev=0.03); m.gbox(5.08, 5.52, -82.42, -82.38, y + h + 0.16, y + h + 0.22, 'dark')
    m.gbox(1.0, 2.6, -82.8, -82.2, y + h, y + h + 0.05, 'wood_lt', bev=0.02)
    for i, c in enumerate(['pink', 'teal', 'offwhite', 'mustard', 'lilac']): m.gcyl(1.2 + i * 0.3, -82.5, y + h + 0.05, 0.07, 0.18, c, seg=10, bev=0.02)
    for i in range(3): m.gbox(-0.7, -0.1, -82.9, -82.3, y + h + i * 0.08, y + h + 0.08 + i * 0.08, ['towel', 'towel_pk', 'towel'][i], bev=0.03)
    # behind: a low back counter (shelves with towels and soap boxes) against the wall
    m.gbox(0.0, 8.6, -85.8, -85.2, y, y + 0.9, 'wood_dk', bev=0.03)
    for i in range(8): m.gbox(0.2 + i * 1.05, 1.0 + i * 1.05, -85.7, -85.3, y + 0.9, y + 1.08, ['cardboard', 'towel', 'teal', 'towel_pk'][i % 4], bev=0.03)
    m.gbox(7.4, 8.0, -84.4, -83.8, y, y + 0.45, 'cushion2', bev=0.08)                 # her stool

def w_cabinet(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h, 'wood_dk', bev=0.04)
    n = 4
    for i in range(n):
        zc = z0 + (i + 0.5) * (z1 - z0) / n
        for r in range(3): m.gbox(x0 - 0.02, x0 + 0.02, zc - 0.62, zc + 0.62, y + 0.1 + r * 0.6, y + 0.62 + r * 0.6, 'wood', bev=0.015)

def w_shoes(m, s, y):
    """getabako: wooden shoe lockers, each little door with a wooden key board."""
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + h, 'wood', bev=0.03); m.gbox(x0 - 0.03, x1 + 0.03, z0 - 0.03, z1 + 0.03, y + h - 0.02, y + h + 0.05, 'wood_dk', bev=0.02)
    rows = 5; n = int((z1 - z0) / 0.4)
    for face in ((x1,) if x0 < -11 else (x0, x1)):
        sd = 1 if face == x1 else -1
        for i in range(n):
            zc = z0 + (i + 0.5) * (z1 - z0) / n
            for r in range(rows):
                ya = y + 0.12 + r * (h - 0.2) / rows; yb = ya + (h - 0.2) / rows - 0.04
                m.gbox(face - 0.015 if sd > 0 else face - 0.02, face + 0.02 if sd > 0 else face + 0.015, zc - 0.17, zc + 0.17, ya, yb, 'wood_lt')
                m.gbox(face + (0.02 if sd > 0 else -0.04), face + (0.04 if sd > 0 else -0.02), zc - 0.05, zc + 0.05, yb - 0.17, yb - 0.04, 'board' if (i + r) % 4 else 'wood_dd')

def w_washer(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']; n = 2
    for i in range(n):
        xa = x0 + i * (x1 - x0) / n; xb = xa + (x1 - x0) / n - 0.06; xc = (xa + xb) / 2
        m.gbox(xa, xb, z0, z1, y, y + h, 'offwhite', bev=0.05)
        m.cyl(xc, -(z0 - 0.005), y + 0.5, 0.3, 0.04, 'chrome', seg=20, axis='Y'); m.cyl(xc, -(z0 - 0.02), y + 0.5, 0.22, 0.03, 'glass_lt', seg=20, axis='Y')
        m.gbox(xa + 0.1, xb - 0.1, z0 + 0.1, z1 - 0.05, y + h, y + h + 0.03, 'chrome_dk')
def w_crates(m, s, y):
    x0, x1, z0, z1, h = s['x0'], s['x1'], s['z0'], s['z1'], s['h']
    m.gbox(x0, x1, z0, z1, y, y + 0.4, 'wood_lt', bev=0.03); m.gbox(x0 + 0.1, x1 - 0.2, z0 + 0.1, z1 - 0.2, y + 0.4, y + 0.8, 'hinoki_dk', bev=0.03)
    for yy in (0.15, 0.3): m.gbox(x0 - 0.01, x1 + 0.01, z1 - 0.01, z1 + 0.01, y + yy - 0.02, y + yy + 0.02, 'wood_dk')
def w_exitpost(m, s, y):
    m.gbox(s['x0'], s['x1'], s['z0'], s['z1'], y, y + s['h'], 'green', bev=0.03)

# everything but the walls can be smashed by a charge: each of those is its own root, SOLID_<index in the layout>
BREAKABLE = {'lockers', 'bench', 'washrow', 'washisland', 'vanity', 'baskets', 'boiler', 'firewood', 'towels', 'cart', 'washer', 'crates',
             'lowtable', 'massage', 'fridge', 'vending', 'manga', 'sofa', 'desk', 'cabinet', 'shoes', 'shelf'}
def build_solids():
    m = GB()
    for i, s in enumerate(LY.S):
        y = ylev(s['f']); fn = globals().get('w_' + s['k']) or (lambda mm, s, y: mm.gbox(s['x0'], s['x1'], s['z0'], s['z1'], y, y + s['h'], 'plaster', bev=0.03))
        if s['k'] in BREAKABLE: mm = GB(); fn(mm, s, y); obj_from(mm, 'SOLID_%02d' % i, 'ENV_DYN')
        else: fn(m, s, y)
    return obj_from(m, 'BUILDING', 'ENV_STAGE')

# =====================================================================================================================
# doorways, the fire exit, the genkan entrance, tatami, plants, puddles, office, storage
# =====================================================================================================================
def build_details():
    m = GB()
    for d in LY.DOORS:
        y = ylev(d['f']); z = d['z']
        if d['kind'] == 'slide':     # frosted sliding doors, one slid open
            m.gbox(d['x0'], (d['x0'] + d['x1']) / 2 + 0.1, z - 0.24, z - 0.14, y, y + 1.15, 'wood', bev=0.02)
            m.gbox(d['x0'] + 0.08, (d['x0'] + d['x1']) / 2 + 0.02, z - 0.23, z - 0.15, y + 0.1, y + 1.05, 'glass_lt')
            m.gbox(d['x0'] - 0.05, d['x1'] + 0.05, z - 0.3, z + 0.3, y, y + 0.02, 'wood_dk')
            continue
        for x in (d['x0'] - 0.14, d['x1'] + 0.14): m.gbox(x - 0.15, x + 0.15, z - 0.28, z + 0.28, y, y + 1.4, 'wood_dk', bev=0.03)
        m.gbox(d['x0'], d['x1'], z - 0.3, z + 0.3, y, y + 0.025, 'wood_dk')
    # bath steps (two wooden steps up to the rim gap, one inside)
    P = LY.POOL; s0, s1 = P['steps']
    m.gbox(s0, s1, -1.55 - 0.25, -1.55 + 0.25, 0.0, 0.18, 'hinoki', bev=0.04); m.gbox(s0, s1, -2.05 - 0.25, -2.05 + 0.25, 0.0, 0.36, 'hinoki', bev=0.04)
    m.gbox(s0 + 0.05, s1 - 0.05, -2.9, -2.3, -0.75, 0.05, 'tile_navy', bev=0.03)
    # tatami corner
    t = LY.TATAMI; y = UP
    m.gbox(t['x0'], t['x1'], t['z0'], t['z1'], y, y + t['h'] - 0.02, 'wood_dk', bev=0.02)
    for i in range(int((t['x1'] - t['x0']) / 1.8)):
        for j in range(int((t['z1'] - t['z0']) / 0.9)):
            xa = t['x0'] + i * 1.8; za = t['z0'] + j * 0.9
            m.gbox(xa + 0.02, xa + 1.78, za + 0.02, za + 0.88, y + t['h'] - 0.02, y + t['h'], 'tatami' if (i + j) % 2 else 'tatami2', bev=0.01)
            m.gbox(xa + 0.02, xa + 1.78, za + 0.02, za + 0.09, y + t['h'] - 0.019, y + t['h'] + 0.002, 'tatami_edge'); m.gbox(xa + 0.02, xa + 1.78, za + 0.81, za + 0.88, y + t['h'] - 0.019, y + t['h'] + 0.002, 'tatami_edge')
    # the fire exit: green frame, a sign box on the lintel, the outside landing and the escape stairs going down
    E = LY.EXIT
    m.gbox(-12.6, -12.0, E['z0'] - 0.4, E['z1'] + 0.4, UP + 1.95, UP + 2.15, 'green', bev=0.03)
    m.gbox(-12.5, -12.1, -72.0, -71.0, UP + 2.15, UP + 2.55, 'green_dk', bev=0.03)
    sx = -12.1 + 0.005; zc = -71.5
    m.vquad([(sx + 0.002, UP + 2.2, zc - 0.45), (sx + 0.002, UP + 2.2, zc + 0.45), (sx + 0.002, UP + 2.5, zc + 0.45), (sx + 0.002, UP + 2.5, zc - 0.45)][::-1], 'green')
    # the running figure and a doorway on the sign (on its +z face and its lounge-side face), lettering 非常口 below
    for fz, up_ in ((-71.0 + 0.004, 1),):
        def fq(pts, col):
            m.vquad([(x, yy, fz) for x, yy in pts], col)
        fq([(-12.42, UP + 2.2), (-12.18, UP + 2.2), (-12.18, UP + 2.5), (-12.42, UP + 2.5)], 'green')
    m.text('非常口', 0.13, 'snow', -12.3, UP + 2.36, -70.98, depth=0.01)
    m.gbox(-15, -12.4, -72.8, -70.2, UP - 0.1, UP, 'metal')
    for k in range(10): m.gbox(-15 + k * 0.26, -14.9 + k * 0.26, -72.8, -70.2, UP, UP + 0.012, 'chrome_dk')
    for k in range(6): m.gbox(-15.0, -14.4, -70.0 + k * 0.5, -69.5 + k * 0.5, UP - 0.5 * (k + 1), UP - 0.5 * k - 0.45, 'metal')
    m.gbox(-15.05, -14.95, -72.8, -70.0, UP, UP + 1.0, 'chrome_dk')
    # the genkan entrance: lattice sliding doors (shut), a noren on its own frame, slippers lined up on the step
    En = LY.ENTRANCE; y = UP; z = En['z']
    for i in range(4):
        xa = En['x0'] + i * (En['x1'] - En['x0']) / 4
        m.gbox(xa + 0.02, xa + (En['x1'] - En['x0']) / 4 - 0.02, z + 0.02, z + 0.1, y, y + 1.15, 'wood', bev=0.02)
        m.gbox(xa + 0.1, xa + (En['x1'] - En['x0']) / 4 - 0.1, z + 0.09, z + 0.11, y + 0.15, y + 1.05, 'glass_lt')
        for k in range(1, 4): m.gbox(xa + 0.1, xa + (En['x1'] - En['x0']) / 4 - 0.1, z + 0.105, z + 0.12, y + 0.15 + k * 0.22, y + 0.17 + k * 0.22, 'wood')
    for x in (En['x0'] - 0.2, En['x1'] + 0.2): m.gbox(x - 0.1, x + 0.1, z + 0.02, z + 0.3, y, y + 2.1, 'wood_dk', bev=0.03)
    m.gbox(En['x0'] - 0.3, En['x1'] + 0.3, z + 0.08, z + 0.24, y + 2.05, y + 2.2, 'wood_dk', bev=0.03)        # the noren rod
    nz = z + 0.3
    for i in range(3):   # three panels of indigo cloth with ゆ across the middle one
        xa = En['x0'] + i * (En['x1'] - En['x0']) / 3
        m.vquad([(xa + 0.04, y + 1.45, nz), (xa + (En['x1'] - En['x0']) / 3 - 0.04, y + 1.45, nz), (xa + (En['x1'] - En['x0']) / 3 - 0.04, y + 2.12, nz), (xa + 0.04, y + 2.12, nz)], 'navy')
    m.text('ゆ', 0.5, 'snow', (En['x0'] + En['x1']) / 2, y + 1.78, nz + 0.012, depth=0.01)
    for k in range(8):
        xs = -4.45 - (k % 2) * 0.22; zs = -77.0 - (k // 2) * 1.5
        m.gbox(xs - 0.08, xs + 0.08, zs - 0.16, zs + 0.16, y, y + 0.05, 'cushion2' if k % 4 < 2 else 'pink', bev=0.03)
    m.gcyl(-5.4, -90.8, y, 0.2, 0.6, 'wood_dk', seg=14, r2=0.22)                                                  # umbrella stand
    for k in range(3): m.gcyl(-5.4 + (k - 1) * 0.06, -90.8, y + 0.4, 0.025, 0.55, ['navy', 'red', 'offwhite'][k], seg=6)
    # staff office (walled off): desk, chair, filing shelf, a kettle, a futon rolled up
    O = LY.OFFICE
    m.gbox(-3.4, -1.0, -91.6, -90.6, y, y + 0.75, 'wood', bev=0.03); m.gbox(-2.8, -2.0, -91.4, -91.0, y + 0.75, y + 1.1, 'dark', bev=0.02)
    m.gbox(-2.6, -1.8, -90.4, -89.8, y, y + 0.45, 'cushion2', bev=0.06)
    m.gbox(0.6, 3.4, -91.8, -91.2, y, y + 1.1, 'wood_dk', bev=0.03)
    for i in range(6): m.gbox(0.7 + i * 0.45, 1.05 + i * 0.45, -91.7, -91.25, y + 0.6, y + 1.0, ['cardboard', 'mustard', 'teal'][i % 3], bev=0.02)
    m.gbox(-0.4, 1.8, -88.4, -87.4, y, y + 0.35, 'towel', bev=0.15); m.gcyl(-3.0, -88.0, y, 0.18, 0.2, 'chrome', seg=12, bev=0.03)
    m.gbox(-3.6, -2.4, -87.2, -86.6, y, y + 0.08, 'tatami', bev=0.02)
    # storage: boxes stacked on the floor, a mop and a bucket
    for x, z, w, h, c in [(4.8, -86.9, 0.7, 0.5, 'cardboard'), (6.4, -91.4, 0.9, 0.6, 'cardboard_dk'), (6.4, -91.4, 0.7, 0.45, 'cardboard'), (11.0, -87.0, 0.8, 0.55, 'cardboard')]:
        y0 = y + (0.6 if c == 'cardboard' and z == -91.4 else 0.0)
        m.gbox(x - w / 2, x + w / 2, z - w / 2, z + w / 2, y0, y0 + h, c, bev=0.03)
    m.gcyl(11.4, -86.7, y, 0.025, 1.4, 'wood_lt', seg=6); m.gico(11.4, -86.7, y + 0.08, 0.16, 'towel', sq=(1, 1, 0.6))
    # plants (potted, on the floor), puddles
    for bi, b in enumerate(LY.B):
        if b['k'] == 'plant':
            y = ylev(b['f']); s = b['s']; m0 = m; m = GB()
            m.gcyl(b['x'], b['z'], y, 0.42 * s, 0.6 * s, 'terracotta', seg=14, r2=0.34 * s, bev=0.03)
            for dx, dz, dy, r in [(0, 0, 1.0, 0.55), (0.32, 0.18, 0.86, 0.38), (-0.3, -0.12, 0.9, 0.4), (0.05, -0.28, 1.25, 0.36)]:
                m.gico(b['x'] + dx * s, b['z'] + dz * s, y + dy * s, r * s, 'leaf' if dy < 1.1 else 'leaf_lt', sq=(1, 1, 0.9), jit=0.08)
            obj_from(m, 'PLANT_%02d' % bi, 'ENV_DYN'); m = m0
        elif b['k'] == 'pillar':
            y = ylev(b['f']); m.gcyl(b['x'], b['z'], y, 0.26, 2.0, 'hinoki', seg=16, bev=0.03); m.gcyl(b['x'], b['z'], y, 0.36, 0.1, 'stone', seg=16, bev=0.03)
            m.gcyl(b['x'], b['z'], y + 2.0, 0.34, 0.06, 'wood_dk', seg=16)
    for p in LY.PUDDLES:
        y = ylev(p.get('f', 0)); pts = [(p['x'] + q[0] * p['rx'], p['z'] + q[1] * p['rz']) for q in chaikin(blob(RNG, 1.0, 14, 0.18), 1)]
        m.gprism(pts, y + 0.002, y + 0.012, 'water_lt' if not p.get('milk') else 'snow')
        m.gbox(p['x'] - p['rx'] * 0.4, p['x'] + p['rx'] * 0.2, p['z'] - p['rz'] * 0.3, p['z'] - p['rz'] * 0.2, y + 0.012, y + 0.016, 'snow')
    # the yellow bottle of milk on its side by the spill
    m.cyl(9.9, 66.1, UP + 0.08, 0.08, 0.3, 'offwhite', seg=10, axis='X')
    return obj_from(m, 'DETAILS', 'ENV_PROPS')

# =====================================================================================================================
# the cracked wall (and the rubble after the charge), item prototypes, the box, tiny clothes
# =====================================================================================================================
def build_crack():
    """the cracked plaster wall at the end of the corridor, facing you; behind it the back stairs."""
    C = LY.CRACK; m = GB(); x0, x1, z0, z1, h = C['x0'], C['x1'], C['z0'], C['z1'], C['h']
    m.gbox(x0, x1, z0 + 0.1, z1 - 0.1, 0.0, h - 0.05, 'dark')                         # seen through the crack
    crack = [(x0 + 2.2, h + 0.1), (x0 + 2.6, 0.92), (x0 + 2.15, 0.66), (x0 + 2.85, 0.38), (x0 + 2.45, -0.05)]
    L = [(x0, 0.0), (x0, h)] + [(xx - 0.06, yy) for xx, yy in crack]
    R = [(xx + 0.06, yy) for xx, yy in reversed(crack)] + [(x1, h), (x1, 0.0)]
    for poly in (L, R):
        b = m._begin(); bm = m.bm; P = [(xx, max(0.0, min(h, yy))) for xx, yy in poly]
        fr = [bm.verts.new((xx, -z1, yy)) for xx, yy in P]; bk = [bm.verts.new((xx, -z0, yy)) for xx, yy in P]
        try:
            bm.faces.new(fr); bm.faces.new(list(reversed(bk)))
            for k in range(len(P)): bm.faces.new((fr[k], fr[(k + 1) % len(P)], bk[(k + 1) % len(P)], bk[k]))
        except ValueError: pass
        m._end(b, 'plaster')
    m.gbox(x0 - 0.03, x0 + 2.1, z0 - 0.03, z1 + 0.03, h - 0.02, h + 0.07, 'wood', bev=0.03); m.gbox(x0 + 2.9, x1 + 0.03, z0 - 0.03, z1 + 0.03, h - 0.02, h + 0.07, 'wood', bev=0.03)
    m.gbox(x0, x1, z1 - 0.015, z1 + 0.015, 0.0, 0.12, 'wood')
    f = z1 + 0.012
    def fq(pts, col): m.vquad([(xx, yy, f) for xx, yy in pts], col)
    for (ax, ay), (bx, by) in [((x0 + 2.6, 0.92), (x0 + 1.7, 1.05)), ((x0 + 2.15, 0.66), (x0 + 1.3, 0.5)), ((x0 + 2.85, 0.38), (x0 + 3.7, 0.22)), ((x0 + 2.85, 0.38), (x0 + 3.4, 0.8)), ((x0 + 1.7, 1.05), (x0 + 1.2, 1.12))]:
        d = Vector((bx - ax, by - ay)); n = Vector((-d.y, d.x)).normalized() * 0.018
        fq([(ax - n.x, ay - n.y), (bx - n.x, by - n.y), (bx + n.x, by + n.y), (ax + n.x, ay + n.y)], 'dark')
    for xx, yy, w, hh in [(x0 + 1.75, 0.62, 0.34, 0.2), (x0 + 3.2, 0.62, 0.3, 0.22), (x0 + 2.0, 0.22, 0.26, 0.18)]:
        m.gbox(xx - w / 2, xx + w / 2, z1 - 0.05, z1 + 0.02, yy - hh / 2, yy + hh / 2, 'brick', bev=0.02)
    for k in range(5): m.gico(x0 + 1.9 + k * 0.28, z1 + 0.25 + (k % 2) * 0.15, 0.04, 0.07 + (k % 3) * 0.03, 'plaster', sub=1, sq=(1, 1, 0.5), jit=0.2)
    obj_from(m, 'CRACK_WALL', 'ENV_DYN')
    r = GB()   # after the charge: the stumps either side and rubble spilling onto the corridor floor
    r.gbox(x0, x0 + 1.0, z0, z1, 0.0, h - 0.25, 'plaster', bev=0.03); r.gbox(x1 - 0.9, x1, z0, z1, 0.0, h - 0.15, 'plaster', bev=0.03)
    r.gbox(x0 - 0.03, x0 + 1.0, z0 - 0.03, z1 + 0.03, h - 0.27, h - 0.2, 'wood'); r.gbox(x1 - 0.9, x1 + 0.03, z0 - 0.03, z1 + 0.03, h - 0.17, h - 0.1, 'wood')
    for k in range(14):
        xx = x0 + 1.2 + (k * 0.37) % 2.6; zz = z1 + 0.3 + (k * 0.61) % 1.6
        r.gico(xx, zz, 0.06, 0.1 + (k % 3) * 0.05, ['plaster', 'brick', 'plaster_dk'][k % 3], sub=1, sq=(1.2, 1, 0.6), jit=0.2)
    obj_from(r, 'CRACK_RUBBLE', 'ENV_DYN')

def build_items():
    m = GB()   # a plastic bath stool
    m.gcyl(0, 0, 0.0, 0.22, 0.28, 'mustard', seg=16, r2=0.25); m.gcyl(0, 0, 0.28, 0.27, 0.06, 'mustard', seg=18, bev=0.025)
    m.gbox(-0.08, 0.08, -0.26, -0.2, 0.05, 0.2, 'dark') if False else None
    obj_from(m, 'ITEM_STOOL', 'ENV_PROTO')
    m = GB()   # the little wooden wash bucket (oke)
    m.lathe([(0.0, 0.0), (0.17, 0.0), (0.2, 0.02), (0.22, 0.22), (0.2, 0.22), (0.18, 0.04), (0.0, 0.04)], 'hinoki', seg=16)
    m.gcyl(0, 0, 0.14, 0.222, 0.03, 'wood_dk', seg=16)
    obj_from(m, 'ITEM_OKE', 'ENV_PROTO')
    m = GB()   # a cleaning bucket
    m.lathe([(0.0, 0.0), (0.22, 0.0), (0.24, 0.02), (0.3, 0.42), (0.27, 0.42), (0.21, 0.05), (0.0, 0.05)], 'teal', seg=16)
    m.gcyl(0, 0, 0.3, 0.29, 0.04, 'chrome', seg=16)
    obj_from(m, 'ITEM_BUCKET', 'ENV_PROTO')
    m = GB()   # his yellow plastic wash bucket, a towel folded over the rim
    m.lathe([(0.0, 0.0), (0.2, 0.0), (0.22, 0.02), (0.3, 0.34), (0.27, 0.34), (0.19, 0.05), (0.0, 0.05)], 'yellow', seg=18)
    m.gbox(-0.25, 0.25, -0.1, 0.1, 0.33, 0.38, 'towel', bev=0.02)
    obj_from(m, 'ITEM_WASHB', 'ENV_PROTO')
    m = GB()   # the cardboard box (open top, flaps out): 1.6 x 0.8 x 1.4
    W, H, D, t = 1.6, 0.8, 1.4, 0.04
    m.gbox(-W / 2, W / 2, -D / 2, -D / 2 + t, 0, H, 'cardboard', bev=0.01); m.gbox(-W / 2, W / 2, D / 2 - t, D / 2, 0, H, 'cardboard', bev=0.01)
    m.gbox(-W / 2, -W / 2 + t, -D / 2, D / 2, 0, H, 'cardboard_dk', bev=0.01); m.gbox(W / 2 - t, W / 2, -D / 2, D / 2, 0, H, 'cardboard_dk', bev=0.01)
    m.gbox(-W / 2, W / 2, -D / 2, D / 2, 0, t, 'cardboard_dk')
    m.gbox(-0.16, 0.16, D / 2, D / 2 + 0.01, 0.05, H - 0.02, 'board')
    for sd in (-1, 1):
        b = m._begin(); bm = m.bm; z = sd * D / 2
        vs = [bm.verts.new((x, -z, H)) for x in (-W / 2, W / 2)] + [bm.verts.new((x, -(z + sd * 0.34), H + 0.2)) for x in (W / 2, -W / 2)]
        bm.faces.new(vs if sd > 0 else vs[::-1]); m._end(b, 'cardboard', smooth=False)
    obj_from(m, 'BOX', 'ENV_PROTO')
    for nm_, col, shp in [('CLOTH_SHIRT', 'pink', 'shirt'), ('CLOTH_SHORTS', 'blue', 'shorts')]:
        m = GB()
        pts = [(-0.09, -0.13), (0.09, -0.13), (0.09, 0.05), (0.16, 0.02), (0.19, 0.08), (0.1, 0.14), (-0.1, 0.14), (-0.19, 0.08), (-0.16, 0.02), (-0.09, 0.05)] if shp == 'shirt' else \
              [(-0.11, 0.08), (0.11, 0.08), (0.12, -0.1), (0.02, -0.1), (0.0, -0.02), (-0.02, -0.1), (-0.12, -0.1)]
        m.gprism([(x, -y) for x, y in pts], 0.0, 0.025, col)
        obj_from(m, nm_, 'ENV_PROTO')

# =====================================================================================================================
# assemble
# =====================================================================================================================
for n in ('ENV_DYN', 'ENV_PROTO', 'RENDER_ONLY'): CN[n] = coll(n)
_lx = LY.LOCKER['x']
_p = 8 / 13; LOCKER_DOOR_SLOTS = [(_lx, 0.94), (_lx - _p, 0.94), (_lx + _p, 0.12), (_lx - 2 * _p, 0.12), (_lx + 2 * _p, 0.94)]
build_floors(); build_water(); build_solids(); build_details(); build_locker_doors(); build_crack(); build_items()
bpy.data.objects['LKHOLES'].hide_render = True; bpy.data.objects['CRACK_RUBBLE'].hide_render = True
# for the approval renders only: the items where the game puts them, the box in storage, his wash bucket
for it in LY.ITEMS:
    o = bpy.data.objects.new(nm('R_' + it['k']), bpy.data.objects['ITEM_' + it['k'].upper()].data); CN['RENDER_ONLY'].objects.link(o)
    o.location = (it['x'], -it['z'], ylev(it.get('f', 0))); o.rotation_euler.z = RNG.uniform(0, 6)
o = bpy.data.objects.new('R_washb', bpy.data.objects['ITEM_WASHB'].data); CN['RENDER_ONLY'].objects.link(o); o.location = (LY.WASHB['x'], -LY.WASHB['z'], 0)
o = bpy.data.objects.new('R_box', bpy.data.objects['BOX'].data); CN['RENDER_ONLY'].objects.link(o); o.location = (LY.BOX['x'], -LY.BOX['z'], UP); o.rotation_euler.z = LY.BOX['ry']
for o in CN['ENV_PROTO'].objects: o.hide_render = True

# =====================================================================================================================
# light + world (as the stage kits), the stealth game camera at several spots
# =====================================================================================================================
sd = bpy.data.lights.new('Sun', 'SUN'); sd.energy = 4.4; sd.color = hexlin('ffe6c8'); sd.angle = math.radians(5)
sun = bpy.data.objects.new('LGT_Sun', sd); CN['LIGHTING'].objects.link(sun)
SUN_DIR = Vector((-7, -9, 17)).normalized()
sun.location = SUN_DIR * 20; sun.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new('World_Game'); scn.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); mr = nt.nodes.new('ShaderNodeMapRange')
mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
mix.inputs['A'].default_value = (*hexlin('d9c2a4'), 1); mix.inputs['B'].default_value = (*hexlin('a9caf0'), 1)
hemi = nt.nodes.new('ShaderNodeBackground'); hemi.inputs['Strength'].default_value = 0.75
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Color'].default_value = (*hexlin('d9e6e9'), 1); bg.inputs['Strength'].default_value = 1.0
lp = nt.nodes.new('ShaderNodeLightPath'); ms = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes.new('ShaderNodeOutputWorld')
L = nt.links.new
L(tc.outputs['Generated'], sep.inputs[0]); L(sep.outputs['Z'], mr.inputs['Value']); L(mr.outputs['Result'], mix.inputs['Factor'])
L(mix.outputs['Result'], hemi.inputs['Color']); L(hemi.outputs[0], ms.inputs[1]); L(bg.outputs[0], ms.inputs[2])
L(lp.outputs['Is Camera Ray'], ms.inputs['Fac']); L(ms.outputs[0], out.inputs['Surface'])
cd = bpy.data.cameras.new('GameCam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(38); cd.clip_start = 0.1; cd.clip_end = 200
cam = bpy.data.objects.new('CAM_Game', cd); CN['CAMERAS'].objects.link(cam); scn.camera = cam
def game_cam(px, pz, py):
    cx = max(-10, min(10, px * 0.8)); cz = pz - 2.6
    pos = Vector((cx, -(cz + 11.55), py + 9.6)); tgt = Vector((cx, -cz, py + 0.6))
    cam.location = pos; cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
    sun.location = tgt + SUN_DIR * 20
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = 50 if LOWRES else 100
scn.render.engine = 'CYCLES'; cy = scn.cycles
cy.device = 'CPU'; cy.samples = 24 if LOWRES else 64; cy.use_adaptive_sampling = True; cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 4; cy.diffuse_bounces = 1; cy.glossy_bounces = 1; cy.transmission_bounces = 2; cy.transparent_max_bounces = 8
vl = scn.view_layers[0]
for p in ('use_pass_diffuse_direct', 'use_pass_diffuse_indirect', 'use_pass_diffuse_color', 'use_pass_glossy_direct', 'use_pass_glossy_indirect',
          'use_pass_glossy_color', 'use_pass_transmission_direct', 'use_pass_transmission_indirect', 'use_pass_transmission_color',
          'use_pass_emit', 'use_pass_environment', 'use_pass_ambient_occlusion', 'use_pass_normal'):
    setattr(vl, p, True)
scn.view_settings.view_transform = 'Standard'; scn.view_settings.look = 'None'; scn.view_settings.exposure = 0
scn.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'; scn.render.image_settings.color_depth = '32'

# =====================================================================================================================
# export + save + render
# =====================================================================================================================
env = [o for c in CN.values() if c.name.startswith('ENV_') for o in c.objects]
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['Palette'].outputs['Color'], N['Principled BSDF'].inputs['Base Color'])
bpy.ops.object.select_all(action='DESELECT')
for o in env: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT + '/bathhouse_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('OBJECTS', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/bathhouse_kit.blend')
VIEWS = {'bath': (1.2, -6.2, 0), 'wash': (0, -21, 0), 'changing': (5, -34, 0), 'corridor': (2, -50, 0), 'stairs': (9, -57, 1.5),
         'lounge': (1, -67, UP), 'hall': (3, -79, UP), 'south': (2, -88, UP)}
want = [a.split('=')[1].split(',') for a in sys.argv if a.startswith('views=')]
want = want[0] if want else list(VIEWS)
if not NORENDER:
    for v in want:
        game_cam(*VIEWS[v]); exr = OUT + '/bh_%s.exr' % v; scn.render.filepath = exr
        bpy.ops.render.render(write_still=True)
        subprocess.run([sys.executable, COMP, exr, OUT + '/bh_%s.png' % v, 'exp=1.2', 'shdk=1.1'], check=True)
print('DONE')
