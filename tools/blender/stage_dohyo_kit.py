# Neighbourhood-shrine dohyo (versus stage) in the approved option-2 "soft city" look (KKBC kit language).
#   <bl python> tools/blender/stage_dohyo_kit.py [norender] [lowres] [ss=1.5] [exp=1.2 shdk=1.1 ...comp args]
# Output (scratchpad/vsdohyo): dohyo_kit.blend, dohyo_kit.glb (stage only, Y-up, palette embedded, M_KIT + M_GLASS_WATER),
#         dohyo_palette.png, dohyo_gamecam.exr (light passes) -> dohyo_gamecam.png (flat composite via kkbc_flat_comp.py)
# Same delivery rules as kkbc_pass.py: ONE master material whose colour comes from a 32x32 nearest-filtered palette
# (8x8 swatches of 4x4 px, every face UV'd to its swatch centre); a second material only for water. The palette is the
# kkbc_pass PAL with the option-2 recolours (kkbc_flat_render.py) baked in, and a few street-only swatches
# (fish / daikon / produce) repurposed for clay, straw, gravel, torii vermilion, lantern stone and the tassel colours.
# Game (Y up) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game. Ring centre at the origin, fighting surface at z = 0.
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/vsdohyo'
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
CN = {n: coll(n) for n in ('ENV_GROUND', 'ENV_DOHYO', 'ENV_ROOF', 'ENV_PROPS', 'ENV_VEGETATION', 'CHARACTERS', 'LIGHTING', 'CAMERAS')}

def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

# =====================================================================================================================
# palette + master material (kkbc_pass.py PAL, option-2 recolours, repurposed street-only slots)
# =====================================================================================================================
PAL = [
    ('dark', '4d4756'), ('ink', '524b5a'), ('road', 'b3aba2'), ('road_band', 'bdb5ab'), ('road_dk', 'a0978e'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'cbbfb1'), ('concrete_dk', 'b3a698'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('tassel_bl', '7fa3d4'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('clay', 'dcb084'), ('clay_dk', 'c89b6e'), ('straw', 'e8d49c'), ('orange_fr', 'f2a23a'), ('gravel', 'dccdb4'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('torii', 'e2684b'), ('straw_dk', 'd4bb80'), ('tassel_bk', '645d6e'), ('sky_sign', '7fc4e8'), ('stone', 'e9e1d1'), ('skin_ref', 'f0c4a2'), ('purple', '8c6aa8'),
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
img.filepath_raw = OUT + '/dohyo_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

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
# module builder (as kkbc_pass.MB): bmesh primitives painted onto palette swatches
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
    def cbox(s, cx, cy, cz, sx, sy, sz, col, bev=0.0, seg=2, M=None):
        s.box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2, col, bev, seg, M)
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
    def prism(s, pts, z0, z1, col, M=None, bev=0.0):
        b = s._begin(); bm = s.bm
        lo = [bm.verts.new((x, y, z0)) for x, y in pts]; hi = [bm.verts.new((x, y, z1)) for x, y in pts]
        bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
        n = len(pts)
        for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
        bmesh.ops.transform(bm, matrix=(M or I4), verts=lo + hi); s._end(b, col, bev, 2, ang=30 if bev else None)
    def tube(s, path, r, col, rseg=10, M=None, caps=True):
        """fat rounded tube (a straw bale, a rope) along a polyline path; ends close in a rounded dome."""
        b = s._begin(); bm = s.bm; rings = []
        P = [Vector(p) for p in path]
        def frame(i):
            t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
            up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n1 = t.cross(up).normalized(); n2 = n1.cross(t).normalized(); return t, n1, n2
        prof = []
        if caps:
            for k in (0.35, 0.75, 0.95): prof.append((0, k))
        for i in range(len(P)): prof.append((i, 1.0))
        if caps:
            for k in (0.95, 0.75, 0.35): prof.append((len(P) - 1, k))
        for j, (i, k) in enumerate(prof):
            t, n1, n2 = frame(i)
            off = 0.0
            if caps and j < 3: off = -r * math.sqrt(max(0, 1 - k * k))
            if caps and j >= len(prof) - 3: off = r * math.sqrt(max(0, 1 - k * k))
            c = P[i] + t * off
            rings.append([bm.verts.new(c + (n1 * math.cos(2 * math.pi * q / rseg) + n2 * math.sin(2 * math.pi * q / rseg)) * r * k) for q in range(rseg)])
        for a, c in zip(rings, rings[1:]):
            for q in range(rseg):
                q1 = (q + 1) % rseg; bm.faces.new((a[q], a[q1], c[q1], c[q]))
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
        bmesh.ops.transform(bm, matrix=(M or I4), verts=[v for rg in rings for v in rg]); s._end(b, col)
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

# =====================================================================================================================
# dimensions
# =====================================================================================================================
RING_R = 4.6               # playable radius (inner edge of the ring bales)
H = 0.55                   # mound height; fighting surface at z = 0, yard at z = -H
TOP = 6.35                 # half-size of the mound top (12.7 m)
BOT = 6.95                 # half-size of the mound foot (13.9 m)
G0 = -H
POST = 7.05                # frame posts on the yard, just outside the mound-foot corners

# ---- yard -----------------------------------------------------------------------------------------------------------
def mod_ground():
    m = MB(); m.box(-30, 30, -14, 34, G0 - 0.3, G0, 'gravel'); return m.finish('MOD_Ground')
def mod_slab(w, d, col='stone'):
    m = MB(); m.box(-w / 2, w / 2, -d / 2, d / 2, G0 - 0.05, G0 + 0.05, col, 0.04, 2); return m.finish('MOD_Slab_%s_%d' % (col, int(w * 100)))
# ---- dohyo ----------------------------------------------------------------------------------------------------------
def mod_mound():
    m = MB()
    rb, rt = BOT * math.sqrt(2), TOP * math.sqrt(2)
    m.lathe([(rb, G0 - 0.02), (rt + 0.12, -0.06), (rt, 0.0)], 'clay_dk', seg=4, M=Rz(45), bev=0.12, ang=20)
    # top face recoloured to the lighter clay: paint faces whose normal points up
    me = m.finish('MOD_Mound', sharp=50)
    uvl = me.uv_layers['PAL']; u = swuv('clay')
    for p in me.polygons:
        if p.normal.z > 0.97 and p.center.z > -0.05:
            for li in p.loop_indices: uvl.data[li].uv = u
    return me
def mod_steps():
    """clay steps cut into the middle of a mound side (pivot: mound foot at the side midpoint, steps go towards -Y)."""
    m = MB()
    m.box(-0.85, 0.85, -0.55, 0.05, G0, G0 + 0.2, 'clay_dk', 0.07)
    m.box(-0.85, 0.85, -0.25, 0.25, G0 + 0.2, G0 + 0.38, 'clay_dk', 0.07)
    m.tube([(-0.8, -0.5, G0 + 0.21), (0.8, -0.5, G0 + 0.21)], 0.1, 'straw_dk', 8)   # a step bale
    return m.finish('MOD_Steps')
def mod_bale_arc(R, a0, a1, r=0.17, name='MOD_Bale'):
    m = MB(); n = 7
    pts = [(R * math.cos(a0 + (a1 - a0) * i / (n - 1)), R * math.sin(a0 + (a1 - a0) * i / (n - 1)), 0.0) for i in range(n)]
    m.tube(pts, r, 'straw', 10)
    # two fat rope bands
    for f in (0.3, 0.7):
        a = a0 + (a1 - a0) * f; c = Vector((R * math.cos(a), R * math.sin(a), 0))
        b = m._begin(); res = bmesh.ops.create_cone(m.bm, cap_ends=True, cap_tris=False, segments=10, radius1=r * 1.06, radius2=r * 1.06, depth=0.08)
        bmesh.ops.transform(m.bm, matrix=T(*c) @ Rz(math.degrees(a)) @ Rx(90), verts=res['verts']); m._end(b, 'straw_dk')
    return m.finish(name)
def mod_bale_line(L, r=0.17, name='MOD_BaleLine'):
    m = MB(); m.tube([(-L / 2 + i * L / 4, 0, 0) for i in range(5)], r, 'straw', 10)
    for f in (-0.25, 0.25):
        m.cyl(f * L, 0, 0, r * 1.06, 0.08, 'straw_dk', 10, axis='X')
    return m.finish(name)
def mod_line():
    m = MB(); m.box(-0.07, 0.07, -0.45, 0.45, -0.01, 0.018, 'offwhite', 0.012); return m.finish('MOD_ShikiriSen')
def mod_bucket():
    m = MB()
    m.lathe([(0.34, 0), (0.38, 0.5)], 'wood_lt', 14, bev=0.035)
    for z in (0.12, 0.4): m.cyl(0, 0, z, 0.37 + 0.03 * z, 0.07, 'wood_dk', 14)
    m.cyl(0, 0, 0.47, 0.33, 0.04, 'water', 14)
    m.box(-0.05, 0.05, -0.38, 0.38, 0.52, 0.62, 'wood_dk', 0.035)                # one chunky handle bar across the rim
    m.cbox(0.28, 0.25, 0.56, 0.08, 0.5, 0.06, 'wood', 0.025, M=Rz(18))            # ladle, resting on the rim
    return m.finish('MOD_Bucket')
def mod_saltbox():
    m = MB()
    m.box(-0.32, 0.32, -0.24, 0.24, 0, 0.42, 'wood', 0.05)
    m.box(-0.25, 0.25, -0.17, 0.17, 0.3, 0.46, 'foam', 0.06)            # heaped salt
    m.ico(0, 0, 0.44, 0.17, 'foam', 2, (1.35, 0.9, 0.45))
    return m.finish('MOD_SaltBox')
def mod_post(col):
    """frame post in its corner colour (NE blue, SE red, SW white, NW black - muted), fat tassel hanging on the ring side."""
    m = MB(); Hp = 4.3
    m.box(-0.2, 0.2, -0.2, 0.2, G0, Hp, 'wood', 0.06, 2)
    m.box(-0.27, 0.27, -0.27, 0.27, G0, G0 + 0.3, 'stone', 0.07)                  # stone footing
    m.box(-0.235, 0.235, -0.235, 0.235, 0.7, 3.4, col, 0.08, 2)                   # cloth wrap in the post's colour
    m.box(-0.25, 0.25, -0.25, 0.25, 3.15, 3.3, 'straw_dk', 0.06)                 # tie
    m.box(-0.06, 0.06, -0.42, -0.2, 3.1, 3.3, 'straw_dk', 0.03)                 # cord to the tassel
    m.ico(0.0, -0.46, 3.0, 0.2, col, 2)                                           # knot
    m.lathe([(0.0, 2.05), (0.3, 2.12), (0.24, 2.62), (0.12, 2.82), (0.0, 2.86)], col, 12, M=T(0, -0.46, 0))
    m.cyl(0, -0.46, 2.78, 0.15, 0.12, 'straw_dk', 10)
    m.box(-0.26, 0.26, -0.26, 0.26, Hp - 0.02, Hp + 0.14, 'wood_dk', 0.06)      # cap
    return m.finish('MOD_Post_' + col)
# ---- shrine yard props ----------------------------------------------------------------------------------------------
def mod_lantern():
    m = MB()
    m.box(-0.5, 0.5, -0.5, 0.5, 0, 0.3, 'concrete', 0.07)
    m.lathe([(0.24, 0.3), (0.2, 1.1), (0.3, 1.2)], 'concrete', 10, bev=0.03)
    m.box(-0.42, 0.42, -0.42, 0.42, 1.18, 1.36, 'concrete', 0.06)
    m.box(-0.33, 0.33, -0.33, 0.33, 1.36, 1.86, 'concrete', 0.05)
    m.box(-0.2, 0.2, -0.335, 0.335, 1.48, 1.74, 'cream', 0.03); m.box(-0.335, 0.335, -0.2, 0.2, 1.48, 1.74, 'cream', 0.03)   # light box windows
    m.lathe([(0.0, 1.86), (0.66, 1.86), (0.62, 1.98), (0.2, 2.28), (0.0, 2.32)], 'concrete', 6, M=Rz(30), bev=0.04)
    m.ico(0, 0, 2.36, 0.12, 'concrete', 1)
    return m.finish('MOD_Lantern')
def mod_torii():
    m = MB(); Hh = 3.5; S = 1.35
    for sd in (-1, 1):
        m.lathe([(0.2, 0.0), (0.17, Hh)], 'torii', 12, M=T(sd * S, 0, 0))
        m.cyl(sd * S, 0, 0.14, 0.25, 0.28, 'tassel_bk', 12, bev=0.04)
    m.box(-S - 0.45, S + 0.45, -0.15, 0.15, Hh - 0.75, Hh - 0.5, 'torii', 0.06)          # nuki
    m.box(-0.12, 0.12, -0.13, 0.13, Hh - 0.5, Hh, 'torii', 0.04)                          # gakuzuka
    m.box(-S - 0.7, S + 0.7, -0.24, 0.24, Hh, Hh + 0.26, 'torii', 0.07)                  # shimaki
    b = m._begin(); r = bmesh.ops.create_cube(m.bm, size=1.0)
    bmesh.ops.transform(m.bm, matrix=T(0, 0, Hh + 0.42) @ Sc(2 * S + 1.9, 0.6, 0.26), verts=r['verts'])
    for v in r['verts']:
        if abs(v.co.x) > S + 0.8: v.co.z += 0.16                                          # upturned kasagi ends
    m._end(b, 'tassel_bk', 0.08)
    return m.finish('MOD_Torii')
def mod_nobori(col, col2):
    m = MB()
    m.cyl(0, 0, 1.9, 0.06, 3.8, 'wood_lt', 8, bev=0.02)
    m.box(-0.05, 0.05, 0.08, 0.78, 0.9, 3.6, col, 0.03)                                 # banner (thick)
    m.box(-0.065, 0.065, 0.08, 0.78, 3.15, 3.45, col2, 0.02)
    m.box(-0.065, 0.065, 0.28, 0.58, 1.3, 2.9, col2, 0.02)                               # one fat stripe instead of lettering
    m.box(-0.05, 0.05, 0.0, 0.9, 3.6, 3.7, 'wood_lt', 0.02)
    m.cyl(0, 0, 0.12, 0.2, 0.24, 'stone', 10, bev=0.04)
    return m.finish('MOD_Nobori_' + col)
def mod_fence(L):
    m = MB(); n = max(2, int(L / 1.6) + 1)
    for i in range(n):
        x = -L / 2 + L * i / (n - 1); m.box(x - 0.09, x + 0.09, -0.09, 0.09, 0, 0.95, 'wood_dk', 0.04)
    for z in (0.35, 0.75): m.box(-L / 2 - 0.1, L / 2 + 0.1, -0.06, 0.06, z - 0.08, z + 0.08, 'wood', 0.035)
    return m.finish('MOD_Fence_%d' % int(L * 10))
def mod_shrub(k):
    m = MB(); cols = [('leaf', 'leaf_lt'), ('leaf_dk', 'leaf'), ('sage', 'leaf_lt')][k % 3]
    m.ico(0, 0, 0.42, 0.62, cols[0], 2, (1.1, 1.0, 0.75), jit=0.05)
    m.ico(0.38, -0.2, 0.36, 0.42, cols[1], 2, (1, 1, 0.8), jit=0.05)
    m.ico(-0.36, 0.25, 0.32, 0.4, cols[0], 2, (1, 1, 0.8), jit=0.05)
    return m.finish('MOD_Shrub_%d' % k)
def mod_patch(k):
    """flat, soft-edged moss / grass patch on the gravel."""
    m = MB(); n = 14; R = random.Random(30 + k)
    pts = [((1.0 + R.uniform(-0.12, 0.12)) * math.cos(2 * math.pi * i / n) * 1.6, (1.0 + R.uniform(-0.12, 0.12)) * math.sin(2 * math.pi * i / n), ) for i in range(n)]
    m.prism(pts, G0 - 0.02, G0 + 0.04, 'sage', bev=0.03)
    return m.finish('MOD_Patch_%d' % k)
def mod_tree():
    m = MB()
    m.lathe([(0.24, 0), (0.17, 2.3)], 'wood_dk', 8)
    m.ico(0, 0, 2.7, 1.45, 'leaf', 2, (1, 1, 0.82), jit=0.04)
    m.ico(0.9, -0.5, 2.25, 0.95, 'leaf_lt', 2, (1, 1, 0.85), jit=0.04)
    m.ico(-0.85, 0.4, 3.25, 0.9, 'leaf_dk', 2, (1, 1, 0.85), jit=0.04)
    return m.finish('MOD_Tree')
def mod_hokora():
    """little roadside shrine on a stone base (back of the yard)."""
    m = MB()
    m.box(-0.75, 0.75, -0.6, 0.6, 0, 0.5, 'stone', 0.07)
    m.box(-0.5, 0.5, -0.4, 0.4, 0.5, 1.35, 'wood_lt', 0.05)
    m.box(-0.36, 0.36, -0.42, -0.36, 0.62, 1.2, 'wood_dk', 0.03)
    for sd in (-1, 1): m.box(-0.8, 0.8, -0.32, 0.32, -0.08, 0.08, 'roof', 0.05, M=T(0, 0, 1.52) @ Rx(-sd * 28) @ T(0, sd * 0.3, 0))
    m.box(-0.18, 0.18, -0.43, -0.39, 1.0, 1.12, 'torii', 0.02)
    m.box(-0.35, 0.35, -0.7, -0.45, 0.5, 0.75, 'wood', 0.04)                             # offering box
    return m.finish('MOD_Hokora')
def mod_rope():
    """shimenawa: fat straw rope sagging between the torii pillars with two white shide blocks."""
    m = MB(); S = 1.35; pts = [(-S + 2 * S * i / 6, 0, 2.55 - 0.18 * math.sin(math.pi * i / 6)) for i in range(7)]
    m.tube(pts, 0.1, 'straw', 8)
    for x in (-0.5, 0.5): m.box(x - 0.12, x + 0.12, -0.03, 0.03, 2.0, 2.4, 'offwhite', 0.02)
    return m.finish('MOD_Shimenawa')

for f in (mod_ground, mod_mound, mod_steps, mod_line, mod_bucket, mod_saltbox, mod_lantern, mod_torii, mod_tree, mod_hokora, mod_rope): f()
mod_slab(1.3, 0.9); mod_slab(1.0, 0.8, 'concrete')
for k in range(3): mod_shrub(k); mod_patch(k)
POSTS = [('tassel_bl', (POST, POST)), ('red', (POST, -POST)), ('offwhite', (-POST, -POST)), ('tassel_bk', (-POST, POST))]   # NE blue, SE red, SW white, NW black
for col, _ in POSTS: mod_post(col)
mod_nobori('coral', 'offwhite'); mod_nobori('dusty_blue', 'offwhite'); mod_nobori('mustard', 'offwhite')
mod_fence(8.0); mod_fence(5.0)

# ---- the ring: 20 bales, 16 on the circle, the four tokudawara (N/S/E/W) set a bale-width outward
NB = 20; RB = RING_R + 0.17; da = 2 * math.pi / NB; gap = 0.035
mod_bale_arc(RB, -da / 2 + gap, da / 2 - gap, name='MOD_Bale')
mod_bale_line(2 * (TOP - 0.45) / 5 - 0.08, name='MOD_BaleSq')
mod_bale_line(1.0, 0.15, name='MOD_BaleCorner')

# =====================================================================================================================
# assemble
# =====================================================================================================================
place('MOD_Ground', 'YARD_Ground', c='ENV_GROUND')
place('MOD_Mound', 'DOHYO_Mound', c='ENV_DOHYO')
for k, a in enumerate((0, 90, 180, 270)):
    d = Vector((math.cos(math.radians(a - 90)), math.sin(math.radians(a - 90)), 0))
    place('MOD_Steps', nm('DOHYO_Steps'), tuple(d * (BOT - 0.05)), rz=a, c='ENV_DOHYO')
for i in range(NB):
    a = i * da
    if i % (NB // 4) == 0:   # tokudawara: the bale on each axis sits ~a bale width further out
        place('MOD_Bale', nm('DOHYO_Tokudawara'), (0.32 * math.cos(a), 0.32 * math.sin(a), 0.0), rz=math.degrees(a), c='ENV_DOHYO')
    else:
        place('MOD_Bale', nm('DOHYO_Bale'), (0, 0, 0.0), rz=math.degrees(a) + RNG.uniform(-0.4, 0.4), c='ENV_DOHYO')
# square outer bales along the mound-top edge (5 per side, between the posts)
SQ = TOP - 0.42; LB = 2 * (TOP - 0.45) / 5
for side in range(4):
    for j in range(5):
        t = -SQ + LB * (j + 0.5) + (TOP - 0.45 - SQ)
        rot = side * 90
        p = (Rz(rot) @ Vector((t, -SQ, 0.02, 1))).xyz
        if j in (0, 4): continue                                                   # leave the corners free for the posts / buckets
        place('MOD_BaleSq', nm('DOHYO_SquareBale'), tuple(p), rz=rot + RNG.uniform(-0.6, 0.6), c='ENV_DOHYO')
for x in (-0.7, 0.7): place('MOD_ShikiriSen', nm('DOHYO_ShikiriSen'), (x, 0, 0), c='ENV_DOHYO')

# roof frame: four posts at the mound-top corners, side beams; the gable roof only at the back edge of the frame
for col, (x, y) in POSTS:
    p = place('MOD_Post_' + col, nm('ROOF_Post'), (x, y, 0), c='ENV_ROOF')
    p.rotation_euler.z = math.atan2(-y, -x) - math.atan2(-1, 0)                    # tassels hang on the ring side
# open frame only (no roof, no beams): a tsuriyane would hide the ring from the high versus camera

# buckets + salt at the corners (on the mound top, inside the posts)
place('MOD_Bucket', 'PROP_Bucket_A', (-TOP + 0.55, -TOP + 0.55, 0), rz=12, c='ENV_DOHYO')
place('MOD_Bucket', 'PROP_Bucket_B', (TOP - 0.55, -TOP + 0.55, 0), rz=-8, c='ENV_DOHYO')
place('MOD_SaltBox', 'PROP_Salt_A', (-TOP + 0.5, TOP - 0.5, 0), rz=90, c='ENV_DOHYO')
place('MOD_SaltBox', 'PROP_Salt_B', (TOP - 0.5, TOP - 0.5, 0), rz=90, c='ENV_DOHYO')

# yard: stepping-stone path from the torii (back right) to the east steps, lanterns, banners, fence, greenery, hokora
TOR = Vector((10.2, 5.6, G0)); place('MOD_Torii', 'YARD_Torii', tuple(TOR), rz=-62, c='ENV_PROPS')
place('MOD_Shimenawa', 'YARD_Shimenawa', tuple(TOR), rz=-62, c='ENV_PROPS')
a, b = Vector((9.3, 4.4)), Vector((BOT + 0.9, 0.0))
for i in range(5):
    p = a.lerp(b, i / 4.0); place('MOD_Slab_stone_130', nm('YARD_Slab'), (p.x + RNG.uniform(-0.1, 0.1), p.y, 0.0), rz=-62 + 90 + RNG.uniform(-8, 8), c='ENV_GROUND')
for x, y, r in ((-9.0, -2.6, 8), (-9.2, 3.0, -6), (8.9, -3.4, 4)):
    place('MOD_Lantern', nm('YARD_Lantern'), (x, y, G0), rz=r, c='ENV_PROPS')
for (mod, x, y) in (('MOD_Nobori_coral', -8.6, 7.4), ('MOD_Nobori_dusty_blue', -7.2, 8.4), ('MOD_Nobori_mustard', -5.8, 9.2)):
    place(mod, nm('YARD_Nobori'), (x, y, G0), rz=-30 + RNG.uniform(-5, 5), c='ENV_PROPS')
place('MOD_Fence_80', 'YARD_Fence_Back', (1.0, 11.6, G0), c='ENV_PROPS')
place('MOD_Fence_50', 'YARD_Fence_Left', (-11.6, 4.5, G0), rz=90, c='ENV_PROPS')
place('MOD_Hokora', 'YARD_Hokora', (-2.2, 10.2, G0), rz=0, c='ENV_PROPS')
for i, (x, y) in enumerate(((-2.2 + 0.0, 8.7), (-2.2, 7.8))): place('MOD_Slab_concrete_100', nm('YARD_Slab'), (x, y, 0.0), rz=RNG.uniform(-6, 6), c='ENV_GROUND')
SHR = [(-9.0, -5.8, 0, 1.15), (-10.6, 0.2, 1, 1.0), (8.8, -6.2, 2, 1.1), (10.4, 0.2, 0, 0.95), (5.2, 10.6, 1, 1.0), (-6.4, 11.2, 2, 0.9), (2.6, 11.0, 0, 0.8), (12.2, 8.6, 1, 1.0)]
for x, y, k, s in SHR: place('MOD_Shrub_%d' % k, nm('YARD_Shrub'), (x, y, G0), rz=RNG.uniform(0, 360), s=s, c='ENV_VEGETATION')
for k, (x, y, r, sc) in enumerate(((-10.2, -1.2, 20, 1.5), (9.6, -1.6, -15, 1.3), (-4.6, 9.4, 5, 1.6), (11.4, 8.4, 40, 1.4))):
    place('MOD_Patch_%d' % (k % 3), nm('YARD_Moss'), (x, y, 0), rz=r, s=(sc, sc, 1), c='ENV_GROUND')
for x, y in ((-12.2, 9.8), (8.0, 12.6), (-13.5, -3.0)): place('MOD_Tree', nm('YARD_Tree'), (x, y, G0), rz=RNG.uniform(0, 360), s=RNG.uniform(0.95, 1.1), c='ENV_VEGETATION')
for o in CN['ENV_GROUND'].objects: pass

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
bpy.ops.export_scene.gltf(filepath=OUT + '/dohyo_kit.glb', export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
for m in (M_KIT, M_GW):
    N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
print('STAGE_TRIS', tris(env), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/dohyo_kit.blend')
if not NORENDER:
    exr = OUT + '/dohyo_gamecam.exr'; scn.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    comp = [a for a in sys.argv if a.startswith(('exp=', 'shdk=', 'lift=', 'ao=', 'lo=', 'hi=', 'form=', 'litk=', 'blur='))]
    if not any(a.startswith('exp=') for a in comp): comp.append('exp=1.2')
    if not any(a.startswith('shdk=') for a in comp): comp.append('shdk=1.1')
    subprocess.run([sys.executable, COMP, exr, OUT + '/dohyo_gamecam.png'] + comp, check=True)
print('DONE')
