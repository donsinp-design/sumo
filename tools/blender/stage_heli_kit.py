# HELIPAD (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py / stage_lily_kit.py / stage_cake_kit.py / stage_vinyl_kit.py /
# stage_vacuum_kit.py.
#   <bl python> tools/blender/stage_heli_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vsheli): heli_kit.blend, heli_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         heli_palette.png, heli_gamecam.exr (light passes) -> heli_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the vacuum kit's, with the vacuum-only swatches
# repurposed for the pad (pad, pad side, perimeter line, touchdown yellow, H white), the roof (2 slab tones, seam,
# parapet, cap) and the two edge-light colours.
# Roots in the glb:
#   PAD, PAD_H        the helipad (top at z = 0, radius 5.3, 0.25 thick on the roof; yellow touchdown circle centred on r = 4.6)
#   LIGHT_01..12      small soft edge lights round the rim (origin at each light's foot) so the game can blink them
#   ROOF, ROOF_*      roof slabs (top z = -0.25), parapet, tower body; AC units, water tank, planter, windsock, vents
#   CITY              the pastel city far below (street level z = -30), ONE mesh
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, pad top at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vsheli'
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
CN = {n: coll(n) for n in ('ENV_CITY', 'ENV_ROOF', 'ENV_PAD', 'ENV_LIGHTS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

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
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('pad', 'c4c1c9'), ('pad_side', 'aeabb6'), ('pad_line', 'efebe3'), ('yellow', 'f0cd62'), ('h_white', 'f8f5ee'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('roof_a', 'ddd5c9'), ('roof_b', 'd6cdc0'), ('roof_seam', 'bfb5a8'), ('parapet', 'e7e0d4'), ('cap', 'f1ece2'), ('light_w', 'fff0c2'), ('light_g', '9ddcab'),
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
img.filepath_raw = OUT + '/heli_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
RING_R = 4.6               # playable radius (the yellow touchdown circle is centred on it)
RD = 5.3                   # pad radius (pad top at z = 0)
ROOF_Z = -0.25             # roof surface (game y = -0.25)
PX, PY0, PY1 = 9.1, -17.0, 8.6     # roof outline (outer face of the parapet): x in [-PX, PX], y in [PY0, PY1]
PW, PH = 0.6, 0.95         # parapet thickness / height above the roof
GZ = -30.0                 # street level far below
SLAB = 3.0                 # roof slab size

# ---- the pad (static): flat tone zones on the top, centre -> edge: (r0, r1, colour) ----------------------------------
PAD_BANDS = [(0.0, RING_R - 0.22, 'pad'), (RING_R - 0.22, RING_R + 0.22, 'yellow'), (RING_R + 0.22, 4.98, 'pad'),
             (4.98, 5.2, 'pad_line')]
def mod_pad():
    m = MB()
    prof = [(5.2, ROOF_Z), (5.3, ROOF_Z + 0.015), (5.36, ROOF_Z + 0.06), (5.38, -0.15), (5.37, -0.08),     # soft foot + side
            (5.34, -0.035), (5.29, -0.008), (5.2, 0.0)]                                                     # rounded top edge
    for r0, r1, c in reversed(PAD_BANDS):
        if r0 > 0: prof.append((r0, 0.0))
    prof.append((0.0, 0.0))
    m.lathe(prof, 'pad', 128)
    me = m.finish('MOD_Pad', sharp=40)
    uvl = me.uv_layers['PAL']
    for p in me.polygons:
        r = Vector((p.center.x, p.center.y)).length
        c = 'pad_side'
        if p.normal.z > 0.9 and abs(p.center.z) < 0.003:
            for r0, r1, cc in PAD_BANDS:
                if r0 <= r < r1: c = cc
        u = swuv(c)
        for li in p.loop_indices: uvl.data[li].uv = u
    return me

def fillet(pts, r, n=3):
    """round every corner of a closed outline (convex or concave) with a soft arc of radius ~r."""
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
def mod_H():
    """the big soft white H (flat, a hair above the pad), legs along the depth axis."""
    m = MB(); W, Hh, b, c = 3.3, 4.1, 0.82, 0.8
    pts = [(-W / 2, -Hh / 2), (-W / 2 + b, -Hh / 2), (-W / 2 + b, -c / 2), (W / 2 - b, -c / 2), (W / 2 - b, -Hh / 2), (W / 2, -Hh / 2),
           (W / 2, Hh / 2), (W / 2 - b, Hh / 2), (W / 2 - b, c / 2), (-W / 2 + b, c / 2), (-W / 2 + b, Hh / 2), (-W / 2, Hh / 2)]
    m.prism(fillet(pts, 0.16, 3), -0.01, 0.018, 'h_white')
    return m.finish('MOD_H', sharp=40)

def mod_light(col):
    """small soft edge light: a squat base and a rounded dome, origin at its foot."""
    m = MB()
    m.lathe([(0.0, 0.0), (0.26, 0.0), (0.27, 0.03), (0.25, 0.07), (0.0, 0.07)], 'metal_lt', 16)
    m.lathe([(0.0, 0.065)] + [(0.19 * math.cos(math.radians(a)), 0.065 + 0.17 * math.sin(math.radians(a))) for a in (0, 25, 50, 72)] + [(0.0, 0.235)], col, 16)
    return m.finish('MOD_Light_' + col, sharp=60)

# ---- the roof: slabs, parapet, and a few calm rooftop things ---------------------------------------------------------
def slab(m, x0, x1, y0, y1, col, c=0.06, depth=0.15):
    b = m._begin(); bm = m.bm; z1 = ROOF_Z; z0 = ROOF_Z - depth
    top = [bm.verts.new(v) for v in ((x0 + c, y0 + c, z1), (x1 - c, y0 + c, z1), (x1 - c, y1 - c, z1), (x0 + c, y1 - c, z1))]
    mid = [bm.verts.new(v) for v in ((x0, y0, z1 - c), (x1, y0, z1 - c), (x1, y1, z1 - c), (x0, y1, z1 - c))]
    bot = [bm.verts.new(v) for v in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
    bm.faces.new(top)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((mid[i], mid[j], top[j], top[i])); bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
    m._end(b, col)
def mod_roof():
    m = MB(); ix = PX - PW; iy = PY1 - PW
    m.box(-PX, PX, PY0, PY1, ROOF_Z - 0.3, ROOF_Z - 0.1, 'roof_seam')            # seam colour under the slabs
    G = 0.05; xs = [-ix + k * SLAB for k in range(int(2 * ix / SLAB) + 2)]
    ys = [iy - k * SLAB for k in range(int((iy - PY0) / SLAB) + 2)]
    for a, (x0, x1) in enumerate(zip(xs, xs[1:])):
        for bb, (y1, y0) in enumerate(zip(ys, ys[1:])):
            x1c, y0c = min(x1, ix), max(y0, PY0)
            if x1c - x0 < 0.3 or y1 - y0c < 0.3: continue
            if max(abs(x0), abs(x1c)) < 3.5 and max(abs(y0c), abs(y1)) < 3.5: continue          # hidden under the pad
            slab(m, x0 + G, x1c - G, y0c + G, y1 - G, 'roof_a' if (a + bb) % 2 else 'roof_b')
    # parapet: chunky low wall + a lighter rounded cap (back + both sides; the front is behind the camera)
    for x0, x1, y0, y1 in ((-PX, PX, iy, PY1), (-PX, -ix, PY0, iy + 0.01), (ix, PX, PY0, iy + 0.01)):
        m.box(x0, x1, y0, y1, ROOF_Z - 0.2, ROOF_Z + PH, 'parapet', 0.1, 2)
    for x0, x1, y0, y1 in ((-PX - 0.08, PX + 0.08, iy - 0.08, PY1 + 0.08), (-PX - 0.08, -ix + 0.08, PY0, iy + 0.01), (ix - 0.08, PX + 0.08, PY0, iy + 0.01)):
        m.box(x0, x1, y0, y1, ROOF_Z + PH, ROOF_Z + PH + 0.16, 'cap', 0.07, 2)
    # the tower under the roof (catches the sun's shadow onto the street; its walls face away from the camera)
    m.box(-PX + 0.02, PX - 0.02, PY0, PY1 - 0.02, GZ, ROOF_Z - 0.3, 'plaster')
    return m.finish('MOD_Roof', sharp=40)

def mod_ac():
    """chunky air-con unit: soft box on two rails, round fan on top, three slats at the front."""
    m = MB(); w, d, h = 2.0, 1.5, 1.05
    for y in (-0.5, 0.5): m.box(-w / 2 + 0.1, w / 2 - 0.1, y - 0.1, y + 0.1, 0, 0.14, 'metal', 0.04, 1)
    m.box(-w / 2, w / 2, -d / 2, d / 2, 0.12, 0.12 + h, 'foam', 0.16, 3)
    m.cyl(0.0, 0.0, 0.12 + h, 0.56, 0.06, 'metal_lt', 24, bev=0.02, bseg=1)
    m.cyl(0.0, 0.0, 0.12 + h + 0.02, 0.44, 0.04, 'metal', 24)
    m.cyl(0.0, 0.0, 0.12 + h + 0.05, 0.13, 0.05, 'foam', 12)
    for k in range(3):
        z = 0.32 + k * 0.24; m.box(-w / 2 + 0.3, w / 2 - 0.3, -d / 2 - 0.04, -d / 2 + 0.05, z, z + 0.08, 'metal_lt', 0.03, 1)
    return m.finish('MOD_AC', sharp=40)
def mod_tank():
    """small water tank: soft drum with a domed lid and two bands, on a low stand."""
    m = MB(); R = 1.2
    m.box(-1.0, 1.0, -1.0, 1.0, 0.0, 0.25, 'metal', 0.06, 1)
    m.lathe([(0.0, 0.25), (R - 0.06, 0.25), (R, 0.32), (R, 2.0), (R - 0.05, 2.08), (0.9, 2.2), (0.5, 2.36), (0.0, 2.4)], 'dusty_blue', 28)
    for z in (0.8, 1.55): m.cyl(0, 0, z, R + 0.04, 0.14, 'frame', 28, bev=0.03, bseg=1)
    m.cyl(0, 0, 2.42, 0.22, 0.12, 'frame', 12, bev=0.03, bseg=1)
    return m.finish('MOD_Tank', sharp=45)
def mod_planter():
    """long wooden planter with round soft bushes and a few flowers."""
    m = MB(); L, Wd = 4.6, 1.2
    m.box(-Wd / 2, Wd / 2, -L / 2, L / 2, 0.0, 0.7, 'wood', 0.1, 2)
    m.box(-Wd / 2 + 0.12, Wd / 2 - 0.12, -L / 2 + 0.12, L / 2 - 0.12, 0.66, 0.72, 'wood_dk', 0.0)
    for k, (y, r, c) in enumerate(((-1.6, 0.62, 'leaf'), (-0.6, 0.55, 'leaf_lt'), (0.45, 0.68, 'leaf'), (1.55, 0.58, 'leaf_dk'))):
        m.ico(RNG.uniform(-0.06, 0.06), y, 0.82, r, c, 2, sq=(1, 1, 0.85), jit=0.03)
    for x, y, z, c in ((0.25, -1.1, 1.18, 'pink_acc'), (-0.2, 0.0, 1.0, 'acc_yellow'), (0.3, 0.95, 1.28, 'pink_acc'), (-0.25, 1.9, 1.1, 'offwhite')):
        m.ico(x, y, z, 0.13, c, 1)
    return m.finish('MOD_Planter', sharp=40)
def mod_windsock():
    """a windsock on a pole: soft striped cone blowing to +x."""
    m = MB(); H = 3.0
    m.cyl(0, 0, 0.1, 0.32, 0.2, 'concrete_dk', 16, bev=0.05, bseg=1)
    m.cyl(0, 0, H / 2 + 0.2, 0.06, H, 'metal_lt', 8)
    m.ico(0, 0, H + 0.22, 0.1, 'metal_lt', 1)
    M = T(0.0, 0.0, H - 0.05) @ Rz(0) @ Ry(96)          # sock axis along +x, drooping a touch
    segs = [(0.0, 0.3, 'orange'), (0.3, 0.6, 'offwhite'), (0.6, 0.9, 'orange'), (0.9, 1.2, 'offwhite'), (1.2, 1.5, 'orange')]
    for z0, z1, c in segs:
        r0 = 0.36 - 0.13 * z0 / 1.5; r1 = 0.36 - 0.13 * z1 / 1.5
        m.lathe([(r0 - 0.04, z0), (r0, z0), (r1, z1), (r1 - 0.04, z1)], c, 16, M=M @ T(0, 0, 0.12))
    m.cyl(0, 0, 0.06, 0.4, 0.12, 'metal', 16, M=M)
    return m.finish('MOD_Windsock', sharp=40)
def mod_vent():
    m = MB()
    m.cyl(0, 0, 0.35, 0.17, 0.7, 'metal_lt', 12)
    m.lathe([(0.0, 0.66), (0.34, 0.66), (0.36, 0.72), (0.25, 0.86), (0.0, 0.9)], 'foam', 16)
    return m.finish('MOD_Vent', sharp=50)

# ---- the city far below: pastel blocks, streets, soft trees (ONE mesh) ----------------------------------------------
FACADES = ['cream', 'pink', 'dusty_blue', 'sage', 'coral', 'mustard', 'lilac', 'cream2', 'teal_muted', 'plaster', 'pink', 'cream']
TOPS = ['concrete', 'offwhite', 'kerb', 'concrete', 'plaster']
CAM_P = Vector((0, -13.93, 14.35)); CAM_F = (Vector((0, 0.15, 0.2)) - CAM_P).normalized()
CAM_R = CAM_F.cross(Vector((0, 0, 1))).normalized(); CAM_U = CAM_R.cross(CAM_F)
def in_view(x0, x1, y0, y1, z0, z1, pad=0.04):
    """True when any corner of the box projects inside the versus camera frame (cheap culling of the far city)."""
    ty = math.tan(math.radians(17)); tx = ty * 16 / 9; xs = []; ys = []
    for x in (x0, x1):
        for y in (y0, y1):
            for z in (z0, z1):
                d = Vector((x, y, z)) - CAM_P; f = d.dot(CAM_F)
                if f <= 0.1: continue
                xs.append(d.dot(CAM_R) / f / tx); ys.append(d.dot(CAM_U) / f / ty)
    if not xs: return False
    return min(xs) < 1 + pad and max(xs) > -1 - pad and min(ys) < 1 + pad and max(ys) > -1 - pad
def tree(m, x, y, z, s=1.0):
    if not in_view(x - 1.4 * s, x + 1.4 * s, y - 1.4 * s, y + 1.4 * s, z, z + 3.5 * s): return
    m.cyl(x, y, z + 0.7 * s, 0.22 * s, 1.4 * s, 'wood_dk', 6)
    c = RNG.choice(('leaf', 'leaf', 'leaf_lt', 'leaf_dk'))
    m.ico(x, y, z + 2.2 * s, 1.35 * s, c, 1, sq=(1, 1, 0.92), jit=0.06)
def wins(a0, a1, w=1.3, gap=1.2):
    """evenly spread chunky windows along a facade from a0 to a1 (margin 0.8)."""
    L = a1 - a0 - 1.6; n = max(1, int((L + gap) / (w + gap))); g = (L - n * w) / max(n - 1, 1) if n > 1 else 0
    s = a0 + 0.8 + (0 if n > 1 else (L - w) / 2)
    return [(s + k * (w + g), s + k * (w + g) + w) for k in range(n)]
def building(m, x0, x1, y0, y1, top, col):
    """chunky pastel building: soft body, a lighter roof slab inset, window strips on the faces the camera sees,
    and sometimes a little roof box / tank."""
    if not in_view(x0, x1, y0, y1, GZ, top + 1.6): return
    m.box(x0, x1, y0, y1, GZ - 0.2, top, col, 0.35, 1)
    tc = RNG.choice(TOPS); i = 0.45
    m.box(x0 + i, x1 - i, y0 + i, y1 - i, top - 0.2, top + 0.06, tc, 0.08, 1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    nfl = int((top - GZ - 2.0) / 3.2)
    for f in range(nfl):
        z = GZ + 2.4 + f * 3.2
        if z + 1.3 > top - 0.6: break
        for a, b in wins(x0, x1): m.box(a, b, y0 - 0.08, y0 + 0.2, z, z + 1.4, 'stand', 0.06, 1)        # front (-y)
        fx = (x0 - 0.08, x0 + 0.2) if cx > 0 else (x1 - 0.2, x1 + 0.08)                              # side facing the centre
        for a, b in wins(y0, y1): m.box(fx[0], fx[1], a, b, z, z + 1.4, 'stand', 0.06, 1)
    r = RNG.random()
    if r < 0.35:
        w = min(x1 - x0, y1 - y0) * 0.28
        m.box(cx - w, cx + w * 0.6, cy - w * 0.6, cy + w, top + 0.06, top + 1.5, 'offwhite', 0.2, 2)
    elif r < 0.6:
        m.cyl(cx + RNG.uniform(-1, 1), cy + RNG.uniform(-1, 1), top + 0.9, 1.0, 1.7, RNG.choice(('wood_lt', 'dusty_blue', 'terracotta')), 14, bev=0.12, bseg=1)
def mod_city():
    m = MB()
    m.box(-90, 90, -40, 110, GZ - 0.6, GZ, 'road')                                   # streets everywhere first
    # road markings: centre dashes on the streets around our block
    XR = (13.0, 23.0); YR = (14.0, 24.0)
    for x in range(-86, 87, 6):
        m.box(x - 1.4, x + 1.4, (YR[0] + YR[1]) / 2 - 0.13, (YR[0] + YR[1]) / 2 + 0.13, GZ, GZ + 0.02, 'line')
    for s in (-1, 1):
        xc = s * (XR[0] + XR[1]) / 2
        for y in range(-38, 108, 6):
            if YR[0] - 1 < y < YR[1] + 1: continue
            m.box(xc - 0.13, xc + 0.13, y - 1.4, y + 1.4, GZ, GZ + 0.02, 'line')
        for k in range(6):                                                          # zebra crossing at the corner
            x0 = s * (XR[0] + 0.8 + k * 1.5)
            m.box(min(x0, x0 + s * 0.8), max(x0, x0 + s * 0.8), YR[0] + 0.6, YR[0] + 3.8, GZ, GZ + 0.02, 'line')
    # blocks: (x0, x1, y0, y1); ours is the centre-front one
    bx_ = [(-90, -XR[1]), (-XR[0], XR[0]), (XR[1], 90)]
    by_ = [(-40, YR[0]), (YR[1], 62.0), (70.0, 110)]
    for (x0, x1) in bx_:
        for (y0, y1) in by_:
            m.box(x0, x1, y0, y1, GZ - 0.4, GZ + 0.22, 'pave', 0.12, 1)              # pavement / kerb block
            ours = x0 == -XR[0] and y0 == -40
            park = x0 == -90 and y0 == YR[1]
            # street trees along the pavement edges that face our street
            for t in range(int(x0) + 4, int(x1) - 2, 8):
                if y0 == YR[1]: tree(m, t + 1.0, y0 + 1.4, GZ + 0.22, 0.95)
                if y1 == YR[0] and not (-PX - 2 < t < PX + 2): tree(m, t + 1.0, y1 - 1.4, GZ + 0.22, 0.95)
            if ours: continue
            if park:
                m.box(x0 + 3, x1 - 3, y0 + 3, y1 - 3, GZ + 0.22, GZ + 0.36, 'sage', 0.1, 1)
                for k in range(16):
                    tree(m, RNG.uniform(x0 + 6, x1 - 6), RNG.uniform(y0 + 6, y1 - 6), GZ + 0.36, RNG.uniform(1.0, 1.4))
                continue
            # lots along x, two rows deep
            xx = x0 + 2.0
            while xx < x1 - 6:
                w = RNG.uniform(8, 12); xe = min(xx + w, x1 - 2.0)
                yy = y0 + 2.0
                for row in range(3):
                    d = (y1 - y0 - 4.0) / 3; ye = yy + d
                    dist = math.hypot((xx + xe) / 2, (yy + ye) / 2)          # keep the next-door buildings well below our roof
                    top = GZ + (RNG.uniform(5, 11) if dist < 45 else RNG.uniform(7, 15))
                    building(m, xx + 0.5, xe - 0.5, yy + 0.5, ye - 0.5, top, RNG.choice(FACADES))
                    yy = ye
                xx = xe
    # a few chunky toy cars on the streets
    for x, y, rz, c in ((-30, 16.4, 0, 'coral'), (8, 21.6, 180, 'dusty_blue'), (40, 16.4, 0, 'mustard'), (-17.0, 34, 90, 'offwhite'),
                        (19.4, 40, -90, 'teal_muted'), (-19.4, 2, -90, 'pink'), (15.6, -6, 90, 'lilac')):
        if not in_view(x - 2.2, x + 2.2, y - 2.2, y + 2.2, GZ, GZ + 2): continue
        M = T(x, y, GZ) @ Rz(rz)
        m.box(-2.1, 2.1, -1.0, 1.0, 0.25, 1.15, c, 0.3, 2, M=M)
        m.box(-1.2, 0.9, -0.85, 0.85, 1.1, 1.85, 'stand', 0.25, 2, M=M)
        for wx in (-1.3, 1.3):
            for wy in (-1.0, 1.0): m.cyl(wx, wy, 0.42, 0.42, 0.3, 'dark', 10, axis='Y', M=M)
    return m.finish('MOD_City', sharp=40)

for f in (mod_pad, mod_H, mod_roof, mod_ac, mod_tank, mod_planter, mod_windsock, mod_vent, mod_city): f()
for c in ('light_w', 'light_g'): mod_light(c)

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_City', 'CITY', c='ENV_CITY')
place('MOD_Roof', 'ROOF', c='ENV_ROOF')
place('MOD_Pad', 'PAD', c='ENV_PAD')
place('MOD_H', 'PAD_H', c='ENV_PAD')
NL = 12
for k in range(NL):                                           # the game blinks these
    a = 2 * math.pi * (k + 0.5) / NL
    place('MOD_Light_' + ('light_g' if k % 2 else 'light_w'), 'LIGHT_%02d' % (k + 1), (5.09 * math.cos(a), 5.09 * math.sin(a), 0.0), c='ENV_LIGHTS')
place('MOD_AC', 'ROOF_AC_01', (-6.7, 6.5, ROOF_Z), rz=0, c='ENV_ROOF')
place('MOD_AC', 'ROOF_AC_02', (-7.3, 3.7, ROOF_Z), rz=90, c='ENV_ROOF')
place('MOD_Tank', 'ROOF_Tank', (6.9, 6.3, ROOF_Z), c='ENV_ROOF')
place('MOD_Planter', 'ROOF_Planter', (7.55, -1.2, ROOF_Z), c='ENV_ROOF')
place('MOD_Windsock', 'ROOF_Windsock', (-7.5, -1.8, ROOF_Z), rz=20, c='ENV_ROOF')
place('MOD_Vent', 'ROOF_Vent_01', (-1.6, 7.25, ROOF_Z), c='ENV_ROOF')
place('MOD_Vent', 'ROOF_Vent_02', (1.2, 7.3, ROOF_Z), s=0.85, c='ENV_ROOF')

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
bpy.ops.export_scene.gltf(filepath=OUT + '/heli_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
for o in bpy.data.objects:            # the edge lights are light: they cast no shadow
    if o.name.startswith('LIGHT_'): o.visible_shadow = False
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/heli_kit.blend')
if not NORENDER:
    exr = OUT + '/heli_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/heli_gamecam.png'] + comp, check=True)
print('DONE')
