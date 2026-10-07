# TAIKO DRUM (versus stage) in the approved option-2 "soft city" look (KKBC kit language), same method as
# stage_dohyo_kit.py / stage_pizza_kit.py / stage_sushi_kit.py / stage_lily_kit.py / stage_cake_kit.py / stage_vinyl_kit.py /
# stage_vacuum_kit.py / stage_heli_kit.py / stage_clock_kit.py / stage_earth_kit.py.
#   <bl python> tools/blender/stage_taiko_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vstaiko): taiko_kit.blend, taiko_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         taiko_palette.png, taiko_gamecam.exr (light passes) -> taiko_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as the dohyo kit: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for glass/water (unused here,
# kept so the glb carries the same two materials). The palette is the dohyo kit's, with the dohyo-only (and city
# interior/shutter) swatches repurposed for the drum skin, ring line, mitsudomoe red, brass tacks, barrel wood, the
# stage boards, the red/white curtain and the lantern pastels.
# Roots in the glb:
#   DRUM               ONE giant taiko: skin top at z = 0 (radius 5.3, flat to r 5.12), soft ring line at r = 4.6,
#                      a band of 36 brass tacks at r 4.93, rolled rim, bulging barrel down to the boards (z = -2.4)
#                      with a skin flap + tack row at top and bottom (front half only)
#   DRUM_Tomoe         the mitsudomoe: three separate commas, 120 deg apart, raised 0.022 (walkable)
#   FLOOR, CURTAIN     pale stage boards (top z = -2.4) and the kohaku maku along the back (y = 10.2)
#   LANTERN_01..04     hanging chochin, separate roots with the ORIGIN AT THE HANGING POINT (z = 6, off screen) so the
#                      game can sway them (rotate about the origin's x / z)
#   PROP_*             a standing lantern (front left) and two bachi resting on a little stand (front right)
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, drumhead top at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vstaiko'
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
CN = {n: coll(n) for n in ('ENV_STAGE', 'ENV_PROPS', 'ENV_DRUM', 'ENV_LANTERNS', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


# =====================================================================================================================
# palette + master material (dohyo kit PAL; stage-only slots repurposed for the drum, the boards, curtain and lanterns)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('skin', 'f4e8cc'), ('skin_edge', 'ead8b2'), ('ring_line', 'c99772'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('brass_dk', 'd2a650'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('tomoe', 'dc6450'), ('barrel', 'd0935f'), ('barrel_dk', 'b97f55'), ('brass', 'e8be62'), ('board', 'efdfc2'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('board2', 'e8d5b4'), ('board_gap', 'cdb48f'), ('maku_red', 'e26a5a'), ('maku_white', 'f5eee2'), ('lan_pink', 'f2b4a8'), ('lan_cream', 'f6e3b4'), ('lan_mint', 'b9e0cc'),
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
img.filepath_raw = OUT + '/taiko_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
RING_R = 4.6               # playable radius (soft ring line on the drumhead)
RD = 5.3                   # drumhead radius (skin top at z = 0)
FLOOR_Z = -2.4             # festival stage boards (game y = -2.4)
TOP_FLAT = 5.12            # flat skin out to here, then it rolls over the rim
TACK_R = 4.93              # band of brass tacks just outside the ring line
CURT_Y = 10.2              # kohaku maku along the back

# ---- the giant taiko: skin + rolled rim + bulging barrel with a skin flap and a tack row at top and bottom -----------
HEAD_BANDS = [(0.0, RING_R - 0.07, 'skin'), (RING_R - 0.07, RING_R + 0.07, 'ring_line'), (RING_R + 0.07, TOP_FLAT, 'skin_edge')]
def barrel_r(z):
    """bulging wood between the two skin flaps (z -1.98 .. -0.42)."""
    t = (z + 1.98) / 1.56
    return 5.33 + 0.36 * math.sin(math.pi * max(0.0, min(1.0, t)))
def mod_drum():
    m = MB()
    prof = [(0.0, FLOOR_Z), (5.30, FLOOR_Z), (5.36, FLOOR_Z + 0.04), (5.385, FLOOR_Z + 0.12), (5.39, -2.02), (5.36, -1.985), (5.33, -1.98)]
    for k in range(1, 12):
        z = -1.98 + 1.56 * k / 12; prof.append((barrel_r(z), z))
    prof += [(5.33, -0.42), (5.36, -0.415), (5.385, -0.38), (5.385, -0.17), (5.37, -0.1), (5.33, -0.045), (5.27, -0.012), (5.20, 0.0)]
    for r0, r1, c in reversed(HEAD_BANDS):
        prof.append((r1, 0.0))
    prof.append((0.0, 0.0))
    m.lathe(prof, 'barrel', 112)
    # brass tacks: the band on the skin just outside the ring line, and one row on each skin flap (front half only)
    tack = [(0.0, -0.03), (0.17, -0.03), (0.17, 0.02), (0.15, 0.07), (0.09, 0.105), (0.0, 0.115)]
    NT = 36
    for k in range(NT):
        a = 2 * math.pi * (k + 0.5) / NT
        m.lathe(tack, 'brass', 10, M=T(TACK_R * math.cos(a), TACK_R * math.sin(a), 0.0))
    small = [(0.0, -0.04), (0.14, -0.04), (0.14, 0.02), (0.12, 0.06), (0.07, 0.09), (0.0, 0.1)]
    for z, R in ((-0.275, 5.385), (FLOOR_Z + 0.27, 5.39)):
        for k in range(NT):
            a = 2 * math.pi * (k + 0.5) / NT
            if math.sin(a) > 0.25: continue          # the far side is never seen
            m.lathe(small, 'brass', 10, M=T(R * math.cos(a), R * math.sin(a), z) @ Rz(math.degrees(a)) @ Ry(90))
    # chunky brass carrying rings (kan) on both sides of the barrel
    for sgn in (-1, 1):
        x = sgn * (barrel_r(-1.2) - 0.02)
        m.lathe([(0.0, -0.02), (0.2, -0.02), (0.2, 0.05), (0.15, 0.12), (0.0, 0.14)], 'brass_dk', 12, M=T(x, 0, -0.95) @ Ry(sgn * 90))
        m.sweep(lambda a: [(0.38 + 0.085 * math.cos(b), 0.085 * math.sin(b)) for b in U(8)], U(20), 'brass', M=T(x + sgn * 0.1, 0, -1.33) @ Ry(90), closed=True)
    me = m.finish('MOD_Drum', sharp=40)
    uvl = me.uv_layers['PAL']; ub = Vector(swuv('barrel'))
    for p in me.polygons:
        if (Vector(uvl.data[p.loop_indices[0]].uv) - ub).length > 1e-4: continue      # tacks + rings keep their brass
        r = Vector((p.center.x, p.center.y)).length; z = p.center.z; c = None
        if p.normal.z > 0.9 and abs(z) < 0.003 and r < TOP_FLAT:
            for r0, r1, cc in HEAD_BANDS:
                if r0 <= r < r1: c = cc
        elif -0.43 < z <= 0.0: c = 'skin_edge'          # rolled rim + top flap
        elif z < -1.97: c = 'skin_edge'                  # bottom flap
        if c:
            u = swuv(c)
            for li in p.loop_indices: uvl.data[li].uv = u
    return me

# ---- mitsudomoe: three separate commas (fat round head tangent to the emblem circle, a tail running along that circle
# and tapering to a point; all curl counter-clockwise seen from above), 120 deg apart with clear skin gaps between them --
TOM_RE, TOM_HR, TOM_TW, TOM_SPAN = 2.8, 1.04, 1.36, 94.0
def tomoe_outline(a0):
    d = TOM_RE - TOM_HR; span = math.radians(TOM_SPAN)
    c = Vector((d * math.cos(a0), d * math.sin(a0))); u = Vector((math.cos(a0), math.sin(a0))); v = Vector((-math.sin(a0), math.cos(a0)))
    def P(r, a): return Vector((r * math.cos(a), r * math.sin(a)))
    def ri(t): return TOM_RE - TOM_TW * (1 - t) ** 1.15
    # where the tail's inner edge leaves the head circle
    lo, hi = 0.0, 0.6
    for _ in range(40):
        mid = (lo + hi) / 2
        if (P(ri(mid), a0 + span * mid) - c).length < TOM_HR: lo = mid
        else: hi = mid
    ts_ = hi; n = 34
    outer = [P(TOM_RE, a0 + span * k / n) for k in range(n + 1)]                       # T -> tip along the emblem circle
    inner = [P(ri(t), a0 + span * t) for t in (ts_ + (1 - ts_) * k / n for k in range(n - 1, -1, -1))]   # tip -> neck
    q = inner[-1] - c; ps0 = math.atan2(q.dot(v), q.dot(u)) % (2 * math.pi)
    head = [c + TOM_HR * (math.cos(ps) * u + math.sin(ps) * v) for ps in (ps0 + (2 * math.pi - ps0) * k / 30 for k in range(1, 30))]
    return [(p.x, p.y) for p in outer + inner + head]
def mod_tomoe():
    m = MB()
    for k in range(3):
        a0 = math.radians(90 + 120 * k)
        m.prism(tomoe_outline(a0), -0.01, 0.022, 'tomoe', bev=0.01, bseg=1)
    me = m.finish('MOD_Tomoe', sharp=40)
    return me

# ---- festival stage: pale boards, kohaku maku along the back ----------------------------------------------------------
def mod_floor():
    m = MB()
    m.box(-40, 40, -20, 30, FLOOR_Z - 0.6, FLOOR_Z - 0.03, 'board_gap')
    y = -20.0; k = 0; R = random.Random(3)
    while y < CURT_Y + 1.0:
        w = 1.35; col = ('board', 'board2')[k % 2]
        # boards are staggered: two lengths with a butt joint at a random x
        xj = R.uniform(-14, 14)
        for xa, xb in ((-40, xj - 0.03), (xj + 0.03, 40)):
            m.box(xa, xb, y + 0.03, y + w - 0.03, FLOOR_Z - 0.12, FLOOR_Z, col, 0.035, 2)
        y += w; k += 1
    return m.finish('MOD_Floor', sharp=40)
def mod_curtain():
    m = MB(); SW_ = 1.3; X0 = -26; n = 40; Z0, Z1 = FLOOR_Z, 7.0
    def yy(x): return CURT_Y + 0.22 * math.sin(2 * math.pi * x / (2 * SW_))
    for s in range(n):
        xa = X0 + s * SW_; col = ('maku_red', 'maku_white')[s % 2]
        xs = [xa + SW_ * i / 5 for i in range(6)]
        b = m._begin(); bm = m.bm
        F = [bm.verts.new((x, yy(x), Z0)) for x in xs]; Ft = [bm.verts.new((x, yy(x), Z1)) for x in xs]
        B = [bm.verts.new((x, yy(x) + 0.08, Z0)) for x in xs]; Bt = [bm.verts.new((x, yy(x) + 0.08, Z1)) for x in xs]
        for i in range(5):
            bm.faces.new((F[i], F[i + 1], Ft[i + 1], Ft[i])); bm.faces.new((B[i + 1], B[i], Bt[i], Bt[i + 1]))
            bm.faces.new((F[i + 1], F[i], B[i], B[i + 1])); bm.faces.new((Ft[i], Ft[i + 1], Bt[i + 1], Bt[i]))
        bm.faces.new((F[0], Ft[0], Bt[0], B[0])); bm.faces.new((F[5], B[5], Bt[5], Ft[5]))
        m._end(b, col)
    # a soft rolled hem along the bottom
    m.box(X0, X0 + n * SW_, CURT_Y - 0.4, CURT_Y + 0.4, Z0, Z0 + 0.12, 'maku_white', 0.05, 2)
    return m.finish('MOD_Curtain', sharp=40)

# ---- chochin: round paper lantern, origin at the hanging point (the game sways it about the origin) --------------------
LAN_RH, LAN_H = 0.66, 1.5
def lantern_body(m, z, col, band, M=None):
    M = M or I4; prof = []
    n = 14
    for i in range(n + 1):
        t = i / n; zz = -LAN_H / 2 + LAN_H * t
        r = LAN_RH * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2)) ** 0.8
        r = max(r, 0.34) * (1 + 0.035 * math.cos(2 * math.pi * t * 5))
        prof.append((r, zz))
    m.lathe([(0.0, -LAN_H / 2)] + prof + [(0.0, LAN_H / 2)], col, 20, M=M @ T(0, 0, z))
    for s in (-1, 1):
        m.lathe([(0.0, -0.08), (0.37, -0.08), (0.39, -0.05), (0.39, 0.05), (0.37, 0.08), (0.0, 0.08)], 'wood_dk', 16, M=M @ T(0, 0, z + s * (LAN_H / 2 + 0.02)))
    if band:
        m.lathe([(LAN_RH * 0.985, -0.17), (LAN_RH * 1.03, -0.15), (LAN_RH * 1.03, 0.15), (LAN_RH * 0.985, 0.17)], band, 20, M=M @ T(0, 0, z))
def mod_lantern(name, col, band, drop):
    """origin = hanging point; the lantern centre hangs `drop` below it on a cord."""
    m = MB()
    m.cyl(0, 0, -(drop - LAN_H / 2 - 0.1) / 2, 0.035, drop - LAN_H / 2 - 0.1, 'wood_dk', 6)
    m.lathe([(0.0, 0.0), (0.12, 0.0), (0.12, 0.1), (0.0, 0.12)], 'wood_dk', 8, M=T(0, 0, -drop + LAN_H / 2 + 0.08))
    lantern_body(m, -drop, col, band)
    return m.finish(name, sharp=40)
def mod_stand_lantern():
    m = MB()
    m.box(-0.55, 0.55, -0.55, 0.55, 0.0, 0.22, 'wood', 0.06, 2)
    m.box(-0.11, 0.11, -0.11, 0.11, 0.2, 2.95, 'wood', 0.04, 1)
    m.box(-0.11, 0.11, -0.11, 0.8, 2.85, 3.05, 'wood', 0.04, 1)               # little arm
    m.cyl(0, 0.68, 2.72, 0.03, 0.26, 'wood_dk', 6)
    lantern_body(m, 2.72 - 0.85, 'lan_cream', 'maku_red', M=T(0, 0.68, 0))
    return m.finish('MOD_StandLantern', sharp=40)

# ---- bachi resting on a little stand ----------------------------------------------------------------------------------
def mod_bachi_stand():
    """a low dark-wood cradle; two chunky pale bachi (with a coral grip) rest across it."""
    m = MB(); H = 0.5
    m.box(-1.25, 1.25, -0.6, 0.6, 0.0, 0.16, 'wood_dk', 0.06, 2)
    for x in (-0.8, 0.8):
        m.box(x - 0.14, x + 0.14, -0.5, 0.5, 0.1, H, 'wood_dk', 0.06, 2)
        for y0, y1 in ((-0.5, -0.33), (-0.06, 0.06), (0.33, 0.5)):                  # cradle prongs
            m.box(x - 0.14, x + 0.14, y0, y1, H - 0.05, H + 0.24, 'wood_dk', 0.05, 2)
    L = 3.1
    for y in (-0.2, 0.2):
        prof = [(0.0, -L / 2), (0.1, -L / 2 + 0.015), (0.15, -L / 2 + 0.07), (0.16, -L / 2 + 0.16), (0.19, L / 2 - 0.22), (0.19, L / 2 - 0.1),
                (0.15, L / 2 - 0.02), (0.0, L / 2)]
        M = T(0.0, y, H + 0.2) @ Ry(90)
        m.lathe(prof, 'canvas', 12, M=M)
        m.lathe([(0.175, -L / 2 + 0.3), (0.2, -L / 2 + 0.32), (0.2, -L / 2 + 0.9), (0.175, -L / 2 + 0.92)], 'maku_red', 12, M=M)   # grip wrap
    return m.finish('MOD_BachiStand', sharp=40)

for f in (mod_drum, mod_tomoe, mod_floor, mod_curtain, mod_stand_lantern, mod_bachi_stand): f()
LANTERNS = [  # (name, body, band, hang point, drop)
    ('LANTERN_01', 'lan_pink', None, (-9.6, 4.8, 6.0), 6.1),
    ('LANTERN_02', 'lan_cream', 'maku_red', (-4.9, 8.4, 6.0), 6.2),
    ('LANTERN_03', 'lan_mint', None, (4.9, 8.4, 6.0), 6.2),
    ('LANTERN_04', 'lan_cream', 'maku_red', (9.6, 4.8, 6.0), 6.1),
]
for nm_, col, band, hp, drop in LANTERNS: mod_lantern('MOD_' + nm_, col, band, drop)

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Floor', 'FLOOR', c='ENV_STAGE')
place('MOD_Curtain', 'CURTAIN', c='ENV_STAGE')
place('MOD_Drum', 'DRUM', c='ENV_DRUM')
place('MOD_Tomoe', 'DRUM_Tomoe', c='ENV_DRUM')
for nm_, col, band, hp, drop in LANTERNS:
    place('MOD_' + nm_, nm_, hp, c='ENV_LANTERNS')
place('MOD_StandLantern', 'PROP_StandLantern', (-9.4, -1.2, FLOOR_Z), rz=-90, c='ENV_PROPS')
place('MOD_BachiStand', 'PROP_Bachi', (8.9, -1.6, FLOOR_Z), rz=-18, c='ENV_PROPS')

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
bpy.ops.export_scene.gltf(filepath=OUT + '/taiko_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/taiko_kit.blend')
if not NORENDER:
    exr = OUT + '/taiko_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/taiko_gamecam.png'] + comp, check=True)
print('DONE')
