# KKBC art-direction pass ("Little Kitty, Big City" visual language) on the test street segment.
#   <bl python> tools/blender/kkbc_pass.py [renders=1,3,final] [lowres]
# Input : <OUT>/segment_original.blend   (built by kkbc_segment.py)
# Output: <OUT>/segment_kkbc.blend, <OUT>/segment_kkbc.glb (environment, no sumo), <OUT>/kit.glb (one object per module at the origin),
#         <OUT>/kkbc_palette.png, <OUT>/pass1_gamecam.png, <OUT>/pass3_gamecam.png, <OUT>/kkbc_gamecam.png, <OUT>/revised_gamecam.png
# Delivery rules: ONE master material (M_KIT) whose colour comes from a 32x32 nearest-filtered palette texture (8x8 swatches of 4x4 px);
# every face is UV'd onto the centre of its swatch. A second material (M_GLASS_WATER, same palette) only for window glass and puddles.
# The environment is a kit of named modules (mesh datablocks MOD_*) placed as linked duplicates.
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/kkbc'
FONT_PATH = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
ARGS = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
RENDERS = ARGS.get('renders', '1,3,final').split(',')
LOWRES = 'lowres' in sys.argv
RNG = random.Random(5)

bpy.ops.wm.open_mainfile(filepath=OUT + '/segment_original.blend')
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/segment_kkbc.blend')
scn = bpy.context.scene; ROOT = scn.collection
FONT = bpy.data.fonts.load(FONT_PATH)

def T(x, y, z): return Matrix.Translation((x, y, z))
def Rx(d): return Matrix.Rotation(math.radians(d), 4, 'X')
def Ry(d): return Matrix.Rotation(math.radians(d), 4, 'Y')
def Rz(d): return Matrix.Rotation(math.radians(d), 4, 'Z')
def Sc(x, y, z): return Matrix.Diagonal((x, y, z, 1))
FPX = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # text plane -> faces +X, reads along +Y
I4 = Matrix.Identity(4)

def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent or ROOT
    if c.name not in [ch.name for ch in par.children]: par.children.link(c)
    return c
CN = {n: coll(n) for n in ('ENV_BUILDINGS', 'ENV_ROAD', 'ENV_STALLS', 'ENV_PROPS', 'ENV_SIGNS', 'ENV_UTILITY', 'ENV_VEGETATION',
                           'CHARACTERS', 'LIGHTING', 'CAMERAS', 'KIT_MODULES')}

def delete(objs):
    for o in list(objs):
        if o and o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)

RENDER_PY = '''
import bpy, sys
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); s = bpy.context.scene
s.camera = bpy.data.objects[a[1]]; s.render.resolution_percentage = int(a[2]); s.render.filepath = a[3]
bpy.ops.render.render(write_still=True)
'''
def render(path, cam=None):
    """EEVEE Next dropped object shadows when rendering inside this long-running build process (fresh loads are fine),
    so every checkpoint is saved as a copy and rendered by a fresh Blender python process."""
    import subprocess, tempfile
    tmpb = OUT + '/_render_tmp.blend'; scr = OUT + '/_render_tmp.py'
    open(scr, 'w').write(RENDER_PY)
    bpy.ops.wm.save_as_mainfile(filepath=tmpb, copy=True)
    subprocess.run([sys.executable, scr, '--', tmpb, (cam or scn.camera).name, '50' if LOWRES else '100', path],
                   cwd='/tmp', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print('RENDER', path, flush=True)

def tris(objs):
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type in ('MESH', 'CURVE', 'FONT') and o.visible_get():
            e = o.evaluated_get(dg)
            try:
                m = e.to_mesh(); m.calc_loop_triangles(); n += len(m.loop_triangles); e.to_mesh_clear()
            except RuntimeError: pass
    return n

ORIG_CAM = bpy.data.objects['CAM_Game_Original']
CORNERS = {k: bpy.data.objects['Corner_' + k] for k in ('L1', 'L2', 'R1', 'R2', 'End')}
KN = {'L1': 'Fish', 'R1': 'Veg', 'L2': 'Pickle', 'R2': 'Drinks', 'End': 'Market'}   # corner -> stall archetype name
PLAYER = Vector((0, 17.5, 0))

# =====================================================================================================================
# PASS 1 - lighting + colour management
# =====================================================================================================================
def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexlin(h): return tuple(srgb2lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

vs = scn.view_settings; vs.view_transform = 'AgX'; vs.look = 'AgX - Medium High Contrast'; vs.exposure = 0.72; vs.gamma = 1.0
ee = scn.eevee
ee.taa_render_samples = 32   # >32 samples dropped object shadows on this software-GL (llvmpipe) EEVEE Next
ee.use_shadows = True; ee.shadow_ray_count = 3; ee.shadow_step_count = 10; ee.use_soft_shadows = True
ee.shadow_resolution_scale = 0.75; ee.shadow_pool_size = '1024'; ee.use_bloom = False; ee.use_ssr = False   # a bigger pool: at 1280x720 the default one overflowed and dropped object shadows
ee.use_gtao = True; ee.gtao_distance = 0.6; ee.gtao_factor = 0.6              # subtle AO / contact darkening
ee.use_raytracing = False; ee.fast_gi_method = 'GLOBAL_ILLUMINATION'
# Evaluation renders use CYCLES (low samples + OIDN): EEVEE Next renders headless here only through software GL (llvmpipe) and
# randomly drops all object shadows there. Light paths are kept short (1 diffuse bounce) so it stays close to sun + hemisphere.
scn.render.engine = 'CYCLES'; cy = scn.cycles
cy.device = 'CPU'; cy.samples = 24; cy.use_adaptive_sampling = True; cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 4; cy.diffuse_bounces = 1; cy.glossy_bounces = 1; cy.transmission_bounces = 2; cy.transparent_max_bounces = 8
sun = bpy.data.objects['Sun']; sun.name = 'LGT_Sun'; sd = sun.data
sd.energy = 4.4; sd.color = hexlin('ffe6c8'); sd.angle = math.radians(15); sd.use_shadow_jitter = False   # jittered soft shadows vanish in this software-GL final render; EEVEE Next's
# shadow tracing still softens the edges from the 20 deg disc
sd.shadow_filter_radius = 3.0
# same sun direction as the game (from player + (-9,16,+7) game), so the three.js rig can match it
w = scn.world; nt = w.node_tree
mix = next(n for n in nt.nodes if n.type == 'MIX')
mix.inputs['A'].default_value = (*hexlin('d9c2a4'), 1)       # warm ground bounce
mix.inputs['B'].default_value = (*hexlin('a9caf0'), 1)       # soft blue sky (keeps the shade colourful)
hemi = next(n for n in nt.nodes if n.type == 'BACKGROUND' and n.inputs['Strength'].default_value == 0.5)
hemi.inputs['Strength'].default_value = 0.75; hemi.name = 'Hemi'
bgc = next(n for n in nt.nodes if n.type == 'BACKGROUND' and n != hemi)
bgc.inputs['Color'].default_value = (*hexlin('a9d6f5'), 1); bgc.inputs['Strength'].default_value = 1.0; bgc.name = 'SkyBG'
for o in [sun]: [c.objects.unlink(o) for c in o.users_collection]; CN['LIGHTING'].objects.link(o)
if '1' in RENDERS: render(OUT + '/pass1_gamecam.png', ORIG_CAM)

# =====================================================================================================================
# PASS 2 - materials: one stylised palette + master material
# =====================================================================================================================
PAL = [  # name, sRGB hex.  ~55% warm neutrals, ~25% muted colour, ~12% accents, ~5% darks (by screen area, see report)
    ('dark', '2a2630'), ('ink', '332e38'), ('road', '7b736e'), ('road_band', '8a817a'), ('road_dk', '625b57'), ('pave', 'd3c7b5'), ('kerb', 'e1d9cb'), ('line', 'e9dfc8'),
    ('concrete', 'bcae9f'), ('concrete_dk', '9b8f84'), ('offwhite', 'e6e0d5'), ('cream', 'eadbbf'), ('cream2', 'e3cfae'), ('plaster', 'd2c8ba'), ('roof', '6f6872'), ('roof2', '8c8079'),
    ('dusty_blue', '9db5cb'), ('teal_muted', '84b5ad'), ('sage', 'adc39d'), ('coral', 'e59d86'), ('mustard', 'e2b85e'), ('pink', 'e9bdb0'), ('lilac', 'bdb3d3'), ('terracotta', 'cf7a5a'),
    ('glass', '7f9db8'), ('glass_lt', 'a9c6dc'), ('water', '9cc6e8'), ('water_lt', 'cfe6f5'), ('frame', 'e3ddd1'), ('interior', '6f5b4e'), ('shutter', 'b9b6b0'), ('shutter_dk', '948f8b'),
    ('wood', 'bb8b5e'), ('wood_lt', 'd3ab7a'), ('wood_dk', '8c6648'), ('canvas', 'dcc59e'), ('metal', '8f9ba8'), ('metal_lt', 'b6c0c8'), ('ice', 'd8ecf1'), ('foam', 'ece9e0'),
    ('leaf', '6aa55a'), ('leaf_lt', 'a2c866'), ('leaf_dk', '4f8a4c'), ('fish_blue', '6b90b0'), ('fish_pink', 'ef9f88'), ('fish_silver', 'c7d2d8'), ('orange_fr', 'f2a23a'), ('daikon', 'eee8d8'),
    ('red', 'dd5a42'), ('red_dk', 'b9493c'), ('orange', 'ef9a4c'), ('acc_yellow', 'efc24c'), ('teal', '3f9d97'), ('blue', '3f7fc2'), ('navy', '2f4b7c'), ('green', '4fa56b'),
    ('pink_acc', 'ef9ab2'), ('apple', 'd9473b'), ('banana', 'f1d052'), ('cabbage', 'b2d67a'), ('sky_sign', '7fc4e8'), ('yolk', 'f6d55e'), ('skin_ref', 'f0c4a2'), ('purple', '8c6aa8'),
]
SW = {n: i for i, (n, h) in enumerate(PAL)}
GLASSY = {'glass', 'glass_lt', 'water', 'water_lt'}
def swuv(n):
    i = SW[n]; return ((i % 8 + 0.5) / 8, (i // 8 + 0.5) / 8)            # swatch 0 at UV (0,0): un-UV'd geometry reads as 'dark'
img = bpy.data.images.new('KKBC_Palette', 32, 32, alpha=False)
px = [0.0] * (32 * 32 * 4)
for i, (n, h) in enumerate(PAL):
    c = [int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]
    cx, cy = i % 8, i // 8
    for yy in range(cy * 4, cy * 4 + 4):
        for xx in range(cx * 4, cx * 4 + 4):
            j = (yy * 32 + xx) * 4; px[j:j + 4] = [c[0], c[1], c[2], 1.0]
img.pixels = px
img.filepath_raw = OUT + '/kkbc_palette.png'; img.file_format = 'PNG'; img.save(); img.pack()

def master(name, rough, alpha=1.0, spec=0.25):
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; Lk = m.node_tree.links.new
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = 0.0
    b.inputs['Specular IOR Level'].default_value = spec
    tx = N.new('ShaderNodeTexImage'); tx.image = img; tx.interpolation = 'Closest'; tx.extension = 'EXTEND'; tx.name = 'Palette'
    uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'PAL'; Lk(uvn.outputs['UV'], tx.inputs['Vector'])
    oi = N.new('ShaderNodeObjectInfo'); cr = N.new('ShaderNodeValToRGB'); cr.name = 'Vary'
    cr.color_ramp.elements[0].color = (0.94, 0.94, 0.94, 1); cr.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0; mx.name = 'VaryMix'
    Lk(oi.outputs['Random'], cr.inputs['Fac']); Lk(tx.outputs['Color'], mx.inputs['A']); Lk(cr.outputs['Color'], mx.inputs['B'])
    Lk(mx.outputs['Result'], b.inputs['Base Color'])
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'; m.surface_render_method = 'BLENDED'; m.use_backface_culling = False
    m.diffuse_color = (0.8, 0.78, 0.74, alpha); return m
M_KIT = master('M_KIT', 0.85)
M_KIT.use_backface_culling = True                     # every kit mesh is closed or outward-facing: export single-sided
M_GW = master('M_GLASS_WATER', 0.32, alpha=0.86, spec=0.5)

def nearest_sw(rgb_lin):
    def to_s(v): return v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    s = [to_s(max(0, v)) for v in rgb_lin[:3]]; best = None
    for n, h in PAL:
        if n in ('skin_ref',): continue
        c = [int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]
        d = 2 * (s[0] - c[0]) ** 2 + 4 * (s[1] - c[1]) ** 2 + 3 * (s[2] - c[2]) ** 2
        if best is None or d < best[0]: best = (d, n)
    return best[1]
NAME_SW = {'Road': 'road', 'Road_CentreBand': 'road_band', 'Pavement_L': 'pave', 'Pavement_R': 'pave', 'Kerb_L': 'kerb', 'Kerb_R': 'kerb',
           'EdgeLine_L': 'line', 'EdgeLine_R': 'line', 'StopLine': 'line', 'Tomare': 'line', 'Manhole': 'road_dk'}
def palettize(ob, force=None):
    """Remap a mesh object's materials onto palette swatches (nearest colour) and switch it to M_KIT / M_GLASS_WATER."""
    me = ob.data
    if me.users > 1 and me.get('pal_done'): return
    uvl = me.uv_layers.get('PAL') or me.uv_layers.new(name='PAL')
    for l_ in list(me.uv_layers):
        if l_.name != 'PAL': me.uv_layers.remove(l_)
    slot_sw = []
    for m in me.materials:
        nm = force
        if not nm and m:
            if m.name.startswith(('glass', 'glare')): nm = 'glass'
            else:
                b = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
                nm = nearest_sw(b.inputs['Base Color'].default_value if b else m.diffuse_color)
        slot_sw.append(nm or 'concrete')
    if not slot_sw: slot_sw = [force or 'concrete']
    for p in me.polygons:
        n = slot_sw[min(p.material_index, len(slot_sw) - 1)]; u = swuv(n)
        for li in p.loop_indices: uvl.data[li].uv = u
        p.material_index = 1 if n in GLASSY else 0
    me.materials.clear(); me.materials.append(M_KIT); me.materials.append(M_GW); me['pal_done'] = 1

for o in list(bpy.data.objects):
    if o.type == 'FONT':   # 止まれ: convert the text to a mesh first
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        n = bpy.data.objects.new(o.name, me); n.matrix_world = o.matrix_world; [c.objects.link(n) for c in o.users_collection]
        delete([o]); n.name = 'Tomare'; me.materials.append(M_KIT)
for o in list(bpy.data.objects):
    if o.type != 'MESH' or o.name.startswith(('Sumo',)) or any(c.name == 'ORIG_CHARACTER' for c in o.users_collection): continue
    if o.name.startswith('Puddle'): palettize(o, 'water'); continue
    palettize(o, NAME_SW.get(o.name))
# orphan the original 140 GLB / kit materials
for m in list(bpy.data.materials):
    if m.users == 0: bpy.data.materials.remove(m)

# =====================================================================================================================
# module builder: bmesh primitives painted onto palette swatches
# =====================================================================================================================
MODS = {}
class MB:
    def __init__(s):
        s.bm = bmesh.new(); s.uv = s.bm.loops.layers.uv.new('PAL')
    def _begin(s): return set(s.bm.faces), set(s.bm.edges)
    def _end(s, before, col, bev=0.0, seg=2, ang=None, M=None, verts=None, smooth=True, recalc=True):
        fb, eb = before; bm = s.bm
        new_e = [e for e in bm.edges if e not in eb]
        if M is not None:
            nv = list({v for e in new_e for v in e.verts} | set(verts or []))
            bmesh.ops.transform(bm, matrix=M, verts=nv)
        nf_ = [f for f in bm.faces if f not in fb]
        if recalc and nf_: bmesh.ops.recalc_face_normals(bm, faces=nf_)
        if bev > 0:
            es = new_e if ang is None else [e for e in new_e if e.is_manifold and e.calc_face_angle(0) > math.radians(ang)]
            if es: bmesh.ops.bevel(bm, geom=es, offset=bev, offset_type='OFFSET', segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
        u = swuv(col); mi = 1 if col in GLASSY else 0
        for f in bm.faces:
            if f not in fb:
                f.material_index = mi; f.smooth = smooth
                for l in f.loops: l[s.uv].uv = u
    def box(s, x0, x1, y0, y1, z0, z1, col, bev=0.0, seg=2, M=None, ang=None):
        b = s._begin(); r = bmesh.ops.create_cube(s.bm, size=1.0)
        Mx = (M or I4) @ T((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) @ Sc(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
        bmesh.ops.transform(s.bm, matrix=Mx, verts=r['verts'])
        s._end(b, col, min(bev, abs(x1 - x0) / 2.05, abs(y1 - y0) / 2.05, abs(z1 - z0) / 2.05) if bev else 0, seg, ang)
    def cbox(s, cx, cy, cz, sx, sy, sz, col, bev=0.0, seg=2, M=None):
        s.box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2, col, bev, seg, M)
    def cyl(s, x, y, z, r, h, col, seg=12, r2=None, bev=0.0, bseg=2, M=None, axis='Z'):
        """centred cylinder / cone (r bottom, r2 top)."""
        b = s._begin()
        res = bmesh.ops.create_cone(s.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
        A = {'Z': I4, 'X': Ry(90), 'Y': Rx(-90)}[axis]
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ A, verts=res['verts'])
        s._end(b, col, bev, bseg, ang=30 if bev else None)
    def ico(s, x, y, z, r, col, sub=1, sq=(1, 1, 1), M=None, jit=0.0, smooth=True):
        b = s._begin(); res = bmesh.ops.create_icosphere(s.bm, subdivisions=sub, radius=r)
        for v in res['verts']:
            if jit: v.co *= 1 + RNG.uniform(-jit, jit)
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ Sc(*sq), verts=res['verts'])
        s._end(b, col, smooth=smooth)
    def uvs(s, x, y, z, r, col, seg=10, rings=6, sq=(1, 1, 1), M=None):
        b = s._begin(); res = bmesh.ops.create_uvsphere(s.bm, u_segments=seg, v_segments=rings, radius=r)
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ Sc(*sq), verts=res['verts'])
        s._end(b, col)
    def lathe(s, prof, col, seg=12, M=None):
        """prof: [(r, z)...] bottom->top; r==0 ends collapse to a pole."""
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
        vs_ = [v for rg in rings for v in rg]
        bmesh.ops.transform(bm, matrix=(M or I4), verts=vs_); s._end(b, col)
    def prism(s, pts, z0, z1, col, M=None, bev=0.0):
        """extrude a 2D polygon (x,y) between z0 and z1."""
        b = s._begin(); bm = s.bm
        lo = [bm.verts.new((x, y, z0)) for x, y in pts]; hi = [bm.verts.new((x, y, z1)) for x, y in pts]
        bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
        n = len(pts)
        for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
        bmesh.ops.transform(bm, matrix=(M or I4), verts=lo + hi); s._end(b, col, bev, 2, ang=30 if bev else None)
    def sheet(s, rows, colfn, M=None):
        b = s._begin(); bm = s.bm
        V = [[bm.verts.new(p) for p in row] for row in rows]
        for i in range(len(V) - 1):
            for j in range(len(V[0]) - 1):
                f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
        if M is not None: bmesh.ops.transform(bm, matrix=M, verts=[v for r in V for v in r])
        fb = b[0]
        # paint per face by its (i,j) cell
        newf = [f for f in bm.faces if f not in fb]
        k = 0
        for i in range(len(V) - 1):
            for j in range(len(V[0]) - 1):
                f = newf[k]; k += 1; c = colfn(i, j); u = swuv(c)
                f.material_index = 1 if c in GLASSY else 0; f.smooth = True
                for l in f.loops: l[s.uv].uv = u
    def text(s, txt, M, size, col, extrude=0.02, spacing=1.0, lines=1.0):
        cu = bpy.data.curves.new('tx', 'FONT'); cu.body = txt; cu.font = FONT; cu.size = size; cu.extrude = extrude
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_character = spacing; cu.space_line = lines; cu.resolution_u = 2
        ob = bpy.data.objects.new('tx', cu); ROOT.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
        tb = bmesh.new(); tb.from_mesh(me); bpy.data.meshes.remove(me); tb.normal_update()
        bmesh.ops.delete(tb, geom=[f for f in tb.faces if f.normal.z < -0.5], context='FACES')
        bmesh.ops.transform(tb, matrix=M, verts=tb.verts)
        if M.to_3x3().determinant() < 0: bmesh.ops.reverse_faces(tb, faces=tb.faces[:])
        b = s._begin(); tb.verts.index_update(); vs_ = [s.bm.verts.new(v.co) for v in tb.verts]
        for f in tb.faces:
            try: s.bm.faces.new([vs_[v.index] for v in f.verts])
            except ValueError: pass
        tb.free(); s._end(b, col, smooth=False, recalc=False)
    def finish(s, name, sharp=35):
        me = bpy.data.meshes.new(name); s.bm.normal_update(); s.bm.to_mesh(me); s.bm.free()
        me.materials.append(M_KIT); me.materials.append(M_GW)
        try: me.set_sharp_from_angle(angle=math.radians(sharp))
        except Exception: pass
        me['kkbc_module'] = 1; MODS[name] = me; return me

def place(mod, name, parent=None, loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0, s=(1, 1, 1), c='ENV_PROPS'):
    me = MODS[mod]; ob = bpy.data.objects.new(name, me); CN[c].objects.link(ob)
    if parent: ob.parent = parent
    ob.location = loc; ob.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    ob.scale = s if isinstance(s, (tuple, list)) else (s, s, s)
    return ob

NAMECNT = {}
def nm(prefix):
    NAMECNT[prefix] = NAMECNT.get(prefix, 0) + 1; return '%s_%s' % (prefix, chr(64 + NAMECNT[prefix]) if NAMECNT[prefix] <= 26 else NAMECNT[prefix])

# =====================================================================================================================
# PASS 3 - architecture: big wall planes, big windows with chunky frames, big doors/shutters, big signs
# =====================================================================================================================
WX = -2.6                     # facade plane in the corner frame (faces +X = the street)
def mod_shell(name, col_gf, col_up, H, col_base='concrete'):
    """corner-shop building, pivot at the facade foot (x=0), y centred on the 8.05 m frontage, shop opening 4.4 m wide."""
    m = MB(); Y0, Y1 = -4.025, 4.025; O0, O1 = -3.525, 0.875; GF = 3.6; B = 0.05
    m.box(-1.2, 0, Y0, O0, 0, GF, col_gf, B)                          # left pier
    m.box(-1.2, 0, O1, Y1, 0, GF, col_gf, B)                          # right ground-floor wall
    m.box(-1.2, 0, O0 - 0.02, O1 + 0.02, 2.6, GF, col_gf, B)          # header over the opening
    m.box(-1.2, -0.95, O0, O1, 0, 2.6, 'interior', 0)                  # shop interior back wall
    m.box(-1.0, -0.02, O0, O1, 2.52, 2.62, 'ink', 0)                   # interior ceiling shadow line
    m.box(-0.06, 0.06, O1, Y1, 0, 0.55, col_base, 0.03)                # chunky plinth
    m.box(-1.24, 0.12, Y0 - 0.06, Y1, GF, GF + 0.2, 'roof2', 0.05)     # belt course (one big band)
    m.box(-1.2, 0, Y0, Y1, GF + 0.2, H, col_up, B)                    # upper storey: one big wall plane
    m.box(-1.3, 0.16, Y0 - 0.12, Y1 + 0.04, H, H + 0.28, 'roof', 0.06)  # parapet cap
    return m.finish(name)
def mod_interior(name):
    m = MB()   # shelves with product masses (no tiny items), pivot at the shelf foot
    m.box(-0.3, 0.0, -0.8, 0.8, 0, 1.9, 'wood_dk', 0.03)
    cols = ['orange', 'blue', 'acc_yellow', 'green', 'red', 'foam']
    for r in range(3):
        z = 0.25 + r * 0.55
        m.box(-0.3, 0.06, -0.8, 0.8, z - 0.05, z, 'wood_lt', 0.015)
        for k in range(3): m.box(-0.26, 0.0, -0.74 + k * 0.5, -0.32 + k * 0.5, z, z + 0.32 + 0.06 * ((k + r) % 2), cols[(k + r * 2) % 6], 0.04)
    return m.finish(name)
def mod_shutter(name):
    m = MB()   # roll shutter: big housing + a half-drawn shutter with two broad grooves; pivot at housing centre bottom on the facade
    m.box(-0.05, 0.26, -2.25, 2.25, 0.25, 0.6, 'shutter_dk', 0.07, 3)
    m.box(-0.06, 0.02, -2.2, 2.2, -0.45, 0.25, 'shutter', 0.025)
    for z in (-0.12, 0.08): m.box(0.0, 0.035, -2.2, 2.2, z, z + 0.05, 'shutter_dk', 0.015)
    m.box(-0.07, 0.05, -2.2, 2.2, -0.55, -0.45, 'shutter_dk', 0.03)
    return m.finish(name)
def mod_window(name, kind='A'):
    """big window with a chunky frame, facing +X, pivot at its centre on the wall plane. A plain, B curtain + flower box, C backdrop."""
    m = MB(); W, Hh = (1.5, 1.3) if kind != 'C' else (1.6, 1.35); F = 0.13
    m.box(0.0, 0.12, -W / 2, W / 2, -Hh / 2, Hh / 2, 'frame', 0.035)
    m.box(0.07, 0.125, -W / 2 + F, W / 2 - F, -Hh / 2 + F, Hh / 2 - F, 'glass' if kind != 'C' else 'glass_lt', 0)
    m.box(0.1, 0.15, -0.045, 0.045, -Hh / 2 + F, Hh / 2 - F, 'frame', 0.02)            # one fat mullion
    m.box(0.0, 0.24, -W / 2 - 0.1, W / 2 + 0.1, -Hh / 2 - 0.13, -Hh / 2 + 0.0, 'frame', 0.04)  # deep sill
    if kind == 'B':
        m.box(0.08, 0.135, -W / 2 + F, -0.05, -Hh / 2 + F + 0.1, Hh / 2 - F, 'cream', 0.02)
        m.box(0.24, 0.5, -W / 2 + 0.05, W / 2 - 0.05, -Hh / 2 - 0.35, -Hh / 2 - 0.13, 'terracotta', 0.05)
        for k, yy in enumerate((-0.45, 0.0, 0.45)):
            m.ico(0.37, yy, -Hh / 2 - 0.08, 0.2, ['leaf', 'leaf_lt', 'leaf'][k], 1, (1, 1.2, 0.8), jit=0.08)
        m.ico(0.45, -0.22, -Hh / 2 + 0.02, 0.07, 'pink_acc', 1); m.ico(0.45, 0.25, -Hh / 2 + 0.02, 0.07, 'acc_yellow', 1)
    return m.finish(name)
def mod_ac(name):
    m = MB()
    for by in (-0.3, 0.3): m.box(0.0, 0.45, by - 0.035, by + 0.035, -0.06, 0.0, 'metal', 0.015)
    m.box(0.05, 0.45, -0.46, 0.46, 0.0, 0.64, 'offwhite', 0.06, 3)
    m.cyl(0.455, -0.12, 0.32, 0.22, 0.03, 'metal_lt', 16, axis='X')
    m.cyl(0.47, -0.12, 0.32, 0.07, 0.03, 'metal', 10, axis='X')
    return m.finish(name)
def mod_pipe(name):
    m = MB(); m.cyl(0, 0, 0.5, 0.075, 1.0, 'plaster', 10); return m.finish(name)       # unit-height drainpipe, scaled in Z
def mod_signboard(name, col_border, col_face='offwhite', L=4.4, Hs=0.8):
    m = MB(); m.box(0.0, 0.16, -L / 2, L / 2, -Hs / 2, Hs / 2, col_border, 0.05, 3)
    m.box(0.1, 0.19, -L / 2 + 0.12, L / 2 - 0.12, -Hs / 2 + 0.1, Hs / 2 - 0.1, col_face, 0.03)
    return m.finish(name)
def mod_text(name, txt, col, size, vertical=False, extrude=0.025):
    m = MB()
    if vertical: m.text('\n'.join(txt), T(0, 0, 0) @ Rx(90), size, col, extrude, lines=0.82)       # faces -Y, reads down
    else: m.text(txt, FPX, size, col, extrude)                                                       # faces +X, reads along +Y
    return m.finish(name)
def mod_vsign(name, col):
    """vertical projecting sign (tate-kanban): thick board on two big brackets; pivot at the wall foot of the bracket."""
    m = MB()
    for z in (-0.65, 0.75): m.box(0.0, 0.32, -0.05, 0.05, z - 0.05, z + 0.05, 'ink', 0.02)
    m.box(0.22, 0.9, -0.1, 0.1, -1.05, 1.05, col, 0.06, 3)
    m.box(0.29, 0.83, -0.115, 0.115, -0.95, 0.95, 'offwhite', 0.03)
    m.cyl(0.56, 0, 1.16, 0.09, 0.14, 'acc_yellow', 10, bev=0.02)
    return m.finish(name)
def mod_poster(name, col, col2):
    m = MB(); m.box(0.0, 0.03, -0.27, 0.27, -0.36, 0.36, col, 0.015); m.box(0.02, 0.04, -0.18, 0.18, -0.05, 0.22, col2, 0.01)
    m.box(0.02, 0.04, -0.18, 0.18, -0.26, -0.14, col2, 0.01); return m.finish(name)
def mod_fan(name):
    m = MB()   # big wall fan like the reference: bracket, chunky cage ring, three fat blades
    m.box(0.0, 0.2, -0.06, 0.06, -0.06, 0.06, 'offwhite', 0.02)
    m.cyl(0.32, 0, 0, 0.12, 0.26, 'offwhite', 12, axis='X', bev=0.03)
    b = m._begin(); r = bmesh.ops.create_cone(m.bm, cap_ends=False, segments=16, radius1=0.4, radius2=0.4, depth=0.16)
    bmesh.ops.transform(m.bm, matrix=T(0.4, 0, 0) @ Ry(90), verts=r['verts']); m._end(b, 'offwhite')
    for k in range(3):
        a = k * 120 + 20
        m.cbox(0.44, 0, 0, 0.03, 0.18, 0.3, 'sky_sign', 0.02, M=T(0, 0, 0) @ Rx(a) @ T(0, 0, 0.17))
    m.cyl(0.47, 0, 0, 0.08, 0.06, 'offwhite', 10, axis='X')
    return m.finish(name)
def mod_balcony(name, W):
    m = MB(); m.box(0.0, 0.9, -W / 2, W / 2, -0.12, 0.0, 'concrete', 0.04)
    m.box(0.78, 0.9, -W / 2, W / 2, 0.0, 0.85, 'frame', 0.04); m.box(0.0, 0.9, -W / 2, -W / 2 + 0.1, 0.0, 0.85, 'frame', 0.04)
    m.box(0.0, 0.9, W / 2 - 0.1, W / 2, 0.0, 0.85, 'frame', 0.04)
    return m.finish(name)

# ---- remove the corners' old building geometry (fine tiles, siding slats, grout, tiny lamps) and the old backdrop boxes
for o in list(bpy.data.objects):
    if o.name.endswith('_Building') or o.name.startswith('Block_'): delete([o])
for o in list(bpy.data.objects):
    if o.name.startswith('Road_BandJoint'): delete([o])          # 5 cm paving joints: below the detail floor at gameplay distance

ARCH = {  # per corner: ground-floor colour, upper colour, parapet height, sign word / colour, vertical sign word, windows
    'L1': dict(gf='cream', up='dusty_blue', H=6.3, word='鮮魚', sc='navy', vw='魚', wins=[(-1.3, 'B'), (1.3, 'A'), (3.7, 'A')]),
    'R1': dict(gf='offwhite', up='sage', H=6.9, word='八百屋', sc='green', vw='野菜', wins=[(-1.6, 'A'), (0.9, 'B'), (3.6, 'A')]),
    'L2': dict(gf='cream2', up='coral', H=6.0, word='漬物', sc='red', vw='漬', wins=[(-1.0, 'A'), (2.0, 'A')]),
    'R2': dict(gf='plaster', up='mustard', H=7.1, word='酒', sc='teal', vw='酒', wins=[(-1.4, 'B'), (1.2, 'A'), (3.8, 'B')]),
    'End': dict(gf='cream', up='teal_muted', H=6.6, word='市場', sc='orange', vw='果物', wins=[(-1.2, 'A'), (1.3, 'B'), (3.7, 'A')]),
}
for k, a in ARCH.items():
    mn = 'MOD_Shell_%s_%s' % (a['gf'].capitalize(), a['up'].capitalize())
    if mn not in MODS: mod_shell(mn, a['gf'], a['up'], a['H'])
mod_interior('MOD_ShopShelf'); mod_shutter('MOD_Door_Shutter'); mod_window('MOD_Window_A', 'A'); mod_window('MOD_Window_B', 'B')
mod_window('MOD_Window_C', 'C'); mod_ac('MOD_AC'); mod_pipe('MOD_Pipe'); mod_vsign('MOD_Sign_V_Red', 'red'); mod_vsign('MOD_Sign_V_Navy', 'navy')
mod_fan('MOD_Fan'); mod_balcony('MOD_Balcony', 2.6)
for c1, c2 in (('acc_yellow', 'red'), ('sky_sign', 'offwhite'), ('pink_acc', 'navy'), ('green', 'acc_yellow')):
    mod_poster('MOD_Poster_%s' % c1.split('_')[-1].capitalize(), c1, c2)

for k, a in ARCH.items():
    cr = CORNERS[k]; cr.name = 'CORNER_' + KN[k]
    for c_ in cr.users_collection: c_.objects.unlink(cr)
    CN['ENV_BUILDINGS'].objects.link(cr)
    mn = 'MOD_Shell_%s_%s' % (a['gf'].capitalize(), a['up'].capitalize())
    place(mn, 'BLD_Shop_%s' % KN[k], cr, (WX, 1.525, 0), c='ENV_BUILDINGS')
    place('MOD_ShopShelf', 'BLD_ShopShelf_%s' % KN[k], cr, (WX - 0.65, -1.0, 0), c='ENV_BUILDINGS')
    place('MOD_Door_Shutter', 'BLD_Shutter_%s' % KN[k], cr, (WX, 0.2, 2.35), c='ENV_BUILDINGS')
    for y, kind in a['wins']: place('MOD_Window_' + kind, nm('BLD_Window'), cr, (WX, y, 4.75 + (0.15 if a['H'] > 6.5 else 0)), c='ENV_BUILDINGS')
    if k in ('L1', 'R2', 'R1'): place('MOD_AC', nm('BLD_AC'), cr, (WX, 4.6, 2.72), c='ENV_BUILDINGS')
    pp = place('MOD_Pipe', nm('BLD_Pipe'), cr, (WX + 0.12, 5.43, 0), s=(1, 1, a['H']), c='ENV_BUILDINGS')
    # big horizontal sign (one big word), slightly tilted on two corners
    mb = 'MOD_SignBoard_H_' + a['sc'].capitalize()
    if mb not in MODS: mod_signboard(mb, a['sc'])
    tilt = {'L2': 2.0, 'R1': -1.5}.get(k, 0.0)
    sb = place(mb, 'SIGN_%s_Band' % KN[k], cr, (WX + 0.02, 0.2, 3.3), rx=tilt, c='ENV_SIGNS')
    tn = 'MOD_Text_' + a['word']
    if tn not in MODS: mod_text(tn, a['word'], a['sc'] if a['sc'] != 'acc_yellow' else 'ink', 0.56 if len(a['word']) < 3 else 0.5)
    place(tn, 'SIGN_%s_Word' % KN[k], sb, (0.19, 0, 0), c='ENV_SIGNS')
    # vertical projecting sign at the corner pillar, 1.3x the old one, slight tilt
    vn = 'MOD_Sign_V_' + ('Red' if k in ('L1', 'L2', 'End') else 'Navy')
    vt = 'MOD_TextV_' + a['vw']
    if vt not in MODS: mod_text(vt, a['vw'], 'red_dk' if 'Red' in vn else 'navy', 0.46 if len(a['vw']) == 1 else 0.4, vertical=True)
    vs_ = place(vn, 'SIGN_%s_Vertical' % KN[k], cr, (WX, -2.32, 4.85), rx={'L1': 2.5, 'R2': -3.0}.get(k, 0.0), c='ENV_SIGNS')
    for side, rz in ((-1, 0), (1, 180)):
        place(vt, 'SIGN_%s_VWord_%s' % (KN[k], 'a' if side < 0 else 'b'), vs_, (0.56, side * 0.125, 0.0), rz=rz, c='ENV_SIGNS')
    if k == 'End':
        place('MOD_Fan', 'BLD_Fan_Market', cr, (WX, 3.0, 2.5), rz=0, c='ENV_BUILDINGS')
        for pn, y, z in (('Yellow', 2.75, 1.5), ('Sign', 3.75, 2.4), ('Acc', 4.45, 2.4), ('Green', 5.15, 2.4)):
            place('MOD_Poster_' + pn, nm('BLD_Poster'), cr, (WX + 0.02, y, z), rz=RNG.uniform(-3, 3), c='ENV_BUILDINGS')
    if k in ('R2', 'L1'):
        place('MOD_Balcony', nm('BLD_Balcony'), cr, (WX, 1.3, 4.0 + (0.15 if a['H'] > 6.5 else 0)), c='ENV_BUILDINGS')

# backdrop blocks: big simple volumes, roof cap, big windows on the faces the camera sees
BLK = []
def jsmod(a, b): return math.fmod(a, b)
for z in (-4, -12, -20, -28): BLK.append((-12.5, z, 5, 8, 9 + jsmod(jsmod(z * 7, 4) + 4, 4), +1))
for z in (-6, -14, -22, -30): BLK.append((12.5, z, 5, 8, 10 + jsmod(jsmod(z * 3, 5) + 5, 5), -1))
for x in (-8, -1, 6): BLK.append((x, -36, 7, 6, 11 + jsmod(jsmod(x * 5, 3) + 3, 3), 0))
BCOL = ['cream', 'dusty_blue', 'sage', 'pink', 'cream2', 'teal_muted', 'lilac', 'mustard', 'plaster', 'coral', 'cream']
for i, (x, z, w_, d_, h_, side) in enumerate(BLK):
    m = MB(); jw = RNG.uniform(-0.15, 0.15)
    m.box(-w_ / 2, w_ / 2, -d_ / 2, d_ / 2, 0, h_, BCOL[i], 0.12)
    m.box(-w_ / 2 - 0.15, w_ / 2 + 0.15 + jw, -d_ / 2 - 0.15, d_ / 2 + 0.15, h_, h_ + 0.35, 'roof' if i % 2 else 'roof2', 0.08)
    m.box(-w_ / 2 - 0.05, w_ / 2 + 0.05, -d_ / 2 - 0.05, d_ / 2 + 0.05, 0, 0.6, 'concrete_dk' if i % 3 else 'concrete', 0.04)
    mn = 'MOD_Block_%02d' % i; m.finish(mn)
    bo = place(mn, 'BLD_Backdrop_%02d' % i, None, (x, -z, 0), c='ENV_BUILDINGS')
    nf = int((h_ - 2.5) // 2.2)
    for f in range(nf):
        zz = 3.2 + f * 2.2
        nwin = max(1, int(w_ // 2.6))
        for j in range(nwin):   # face toward the camera (blender -Y)
            wx = -w_ / 2 + w_ / (nwin) * (j + 0.5)
            place('MOD_Window_C', nm('BLD_BackWin'), bo, (wx, -d_ / 2, zz), rz=-90, c='ENV_BUILDINGS')
        if side:
            for j in range(3):  # street-facing side
                yy = -d_ / 2 + d_ / 3 * (j + 0.5)
                place('MOD_Window_C', nm('BLD_BackWin'), bo, (side * w_ / 2, yy, zz), rz=0 if side > 0 else 180, c='ENV_BUILDINGS')

ORIG_CAM.name = 'CAM_Game_Original'
if '3' in RENDERS: render(OUT + '/pass3_gamecam.png', ORIG_CAM)

# =====================================================================================================================
# PASS 4 - market stalls: 5 archetypes from one kit
# =====================================================================================================================
AWN = {'Blue': ('blue', 'offwhite'), 'Red': ('red', 'offwhite'), 'Green': ('green', 'cream'), 'Yellow': ('acc_yellow', 'offwhite'),
       'Plain': ('canvas', 'terracotta')}
def mod_awning(name, c1, c2, D=2.55, Wd=4.6, drop=0.38, n=12, plain=False):
    """thick soft awning: pivot at the back-top edge centre, slopes down toward +X, stripes run front-back, sags between the rafters.
    Thickness and soft edges come from Solidify + Bevel modifiers on the placed objects."""
    m = MB(); NU, NV = 8, n * 2
    rows = []
    for i in range(NU + 1):
        u = i / NU; x = u * D; row = []
        for j in range(NV + 1):
            v = j / NV; y = -Wd / 2 + v * Wd
            sag = 0.09 * math.sin(math.pi * v) ** 1.5 * math.sin(math.pi * min(1, u * 1.15)) ** 0.7 + 0.025 * math.sin(math.pi * ((v * 3) % 1))
            row.append((x, y, -drop * u - sag))
        rows.append(row)
    m.sheet(rows, lambda i, j: (c1 if (j // 2) % 2 == 0 else c2) if not plain else c1)
    # scalloped valance: one fat tongue per stripe along the front and the two sides
    def tongue(p0, ax, w, col, out):
        pts = []
        for k in range(7):
            t = k / 6; pts.append((t * w, 0))
        for k in range(7):
            t = 1 - k / 6; pts.append((t * w, -0.2 - 0.1 * math.sin(math.pi * t)))
        Mx = T(*p0) @ Matrix(((ax[0], out[0], 0, 0), (ax[1], out[1], 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))) @ Rx(90)
        m.prism(pts, -0.012, 0.012, col, Mx)
    fz = -drop - 0.0
    sw = Wd / n
    for k in range(n):
        col = (c1 if k % 2 == 0 else c2) if not plain else c2
        tongue((D + 0.01, -Wd / 2 + k * sw, fz), (0, 1), sw, col, (1, 0))
    for sgn in (-1, 1):
        ns = 5; ss = D / ns
        for k in range(ns):
            col = (c1 if k % 2 == 0 else c2) if not plain else c2
            zz = -drop * (k * ss) / D
            Mx_y = sgn * (Wd / 2 + 0.01)
            pts = [(t / 6 * ss, 0) for t in range(7)] + [((1 - t / 6) * ss, -0.17 - 0.08 * math.sin(math.pi * (1 - t / 6))) for t in range(7)]
            Mx = T(k * ss, Mx_y, zz) @ Ry(math.degrees(math.atan2(drop, D))) @ Rx(90)
            m.prism(pts, -0.012, 0.012, col, Mx)
    m.cyl(D + 0.02, 0, fz + 0.01, 0.05, Wd + 0.1, 'offwhite' if not plain else 'terracotta', 10, axis='Y')   # fat front bar
    return m.finish(name, sharp=50)
def mod_post(name):
    m = MB(); m.box(-0.055, 0.055, -0.055, 0.055, 0, 1.0, 'frame', 0.02); return m.finish(name)
def mod_counter(name, col_body, col_top, h=0.78, D=1.95, Wd=4.1):
    m = MB()   # pivot: front face foot centre; body goes back toward -X
    m.box(-D, 0.0, -Wd / 2, Wd / 2, 0.0, 0.12, 'dark' if col_body != 'teal' else 'ink', 0.03)
    m.box(-D + 0.02, -0.04, -Wd / 2 + 0.04, Wd / 2 - 0.04, 0.1, h - 0.06, col_body, 0.04)
    for yy in (-Wd / 6, Wd / 6): m.box(-0.06, -0.01, yy - 0.04, yy + 0.04, 0.16, h - 0.1, col_top, 0.015)   # two broad panel grooves
    m.box(-D - 0.04, 0.06, -Wd / 2 - 0.05, Wd / 2 + 0.05, h - 0.08, h, col_top, 0.035)
    return m.finish(name)
def mod_tier(name, col, h=0.28, D=0.75, Wd=4.0):
    m = MB(); m.box(-D / 2, D / 2, -Wd / 2, Wd / 2, 0, h, col, 0.04); m.box(D / 2 - 0.04, D / 2 + 0.02, -Wd / 2, Wd / 2, h - 0.2, h, 'teal', 0.02)
    return m.finish(name)
def mod_ice(name):
    m = MB(); m.box(-0.4, 0.4, -1.95, 1.95, 0, 0.1, 'metal_lt', 0.03)
    m.box(-0.36, 0.36, -1.9, 1.9, 0.06, 0.14, 'ice', 0.04); return m.finish(name)
def mod_fishrow(name, col, col2, n=6, L=0.62):
    """a row of big chunky fish lying across the ice (6 fish instead of ~40 small ones)."""
    m = MB()
    for k in range(n):
        y = -1.6 + 3.2 * k / (n - 1); a = RNG.uniform(-6, 6)
        M = T(0, y, 0.06) @ Rz(a)
        m.uvs(0, 0, 0, 1, col, 10, 6, (L / 2, 0.13, 0.08), M)
        m.uvs(0.02, 0, -0.03, 1, col2, 10, 6, (L / 2.3, 0.11, 0.05), M)
        m.prism([(0, 0), (0.17, -0.11), (0.17, 0.11)], -0.025, 0.025, col, M @ T(-L / 2 + 0.03, 0, 0) @ Rz(180))
    return m.finish(name)
def mod_foambox(name):
    m = MB(); m.box(-0.36, 0.36, -0.24, 0.24, 0, 0.34, 'foam', 0.05); m.box(-0.37, 0.37, -0.25, 0.25, 0.3, 0.38, 'blue', 0.03)
    m.box(0.36, 0.38, -0.12, 0.12, 0.1, 0.24, 'blue', 0.01); return m.finish(name)
def mod_cooler(name):
    m = MB(); m.box(-0.4, 0.4, -0.27, 0.27, 0, 0.46, 'blue', 0.07); m.box(-0.42, 0.42, -0.29, 0.29, 0.44, 0.56, 'offwhite', 0.05)
    m.box(-0.2, 0.2, -0.05, 0.05, 0.56, 0.62, 'offwhite', 0.025); return m.finish(name)
def mod_crate(name, col, col2=None, L=0.74, Wd=0.55, H=0.5):
    m = MB(); m.box(-L / 2, L / 2, -Wd / 2, Wd / 2, 0, H, col, 0.05)
    m.box(-L / 2 - 0.015, L / 2 + 0.015, -Wd / 2 - 0.015, Wd / 2 + 0.015, H * 0.55, H * 0.55 + 0.07, col2 or col, 0.02)
    m.box(-L / 2 + 0.07, L / 2 - 0.07, -Wd / 2 + 0.07, Wd / 2 - 0.07, H - 0.03, H + 0.005, 'ink' if col != 'wood' else 'wood_dk', 0.01)
    return m.finish(name)
def mod_basket(name, col='green'):
    m = MB(); m.box(-0.33, 0.33, -0.26, 0.26, 0, 0.24, col, 0.05); m.box(-0.36, 0.36, -0.29, 0.29, 0.2, 0.27, col, 0.03)
    return m.finish(name)
def mod_produce(name, col, col2, r=0.11, n=7, sq=(1, 1, 1), sub=1):
    """a produce MASS sitting in a basket (a few big lumps, no tiny items)."""
    m = MB()
    for k in range(n):
        a = k * 2.4; rr = 0.12 * (k % 3)
        m.ico(math.cos(a) * rr * 1.4, math.sin(a) * rr, 0.24 + 0.05 * (k % 2), r * RNG.uniform(0.9, 1.1), col if k % 3 else col2, sub, sq, jit=0.06)
    return m.finish(name)
def mod_fridge(name):
    m = MB(); m.box(-0.45, 0.45, -0.55, 0.55, 0, 1.95, 'offwhite', 0.07, 3)
    m.box(-0.45, 0.47, -0.55, 0.55, 1.62, 1.95, 'red', 0.05)
    m.box(0.4, 0.47, -0.45, 0.45, 0.25, 1.55, 'glass_lt', 0.02)
    for r in range(3):
        z = 0.35 + r * 0.42
        for k in range(3): m.box(0.1, 0.38, -0.4 + k * 0.28, -0.18 + k * 0.28, z, z + 0.3, ['green', 'orange', 'blue', 'acc_yellow', 'red', 'sky_sign'][(k + r) % 6], 0.04)
    m.box(0.45, 0.5, 0.35, 0.42, 0.7, 1.1, 'metal', 0.02)
    return m.finish(name)
def mod_tub(name, col_in):
    m = MB(); m.cyl(0, 0, 0.27, 0.33, 0.54, 'wood', 14, r2=0.36, bev=0.03)
    for z in (0.12, 0.42): m.cyl(0, 0, z, 0.355, 0.07, 'wood_dk', 14)
    m.cyl(0, 0, 0.52, 0.31, 0.05, col_in, 14); return m.finish(name)
def mod_banner(name, word, col, fg='offwhite'):
    """hanging cloth banner / noren panel with ONE big word, faces +X; pivot at the top centre."""
    m = MB(); m.cyl(0.0, 0, 0.0, 0.035, 1.0, 'wood_dk', 8, axis='Y')
    m.box(-0.02, 0.02, -0.4, 0.4, -1.15, -0.03, col, 0.015)
    m.text(word, T(0.025, 0, -0.55) @ FPX, 0.55 if len(word) == 1 else 0.36, fg, 0.012)
    return m.finish(name)
def mod_lantern(name):
    m = MB(); m.lathe([(0, -0.3), (0.12, -0.3), (0.22, -0.18), (0.25, 0.0), (0.22, 0.18), (0.12, 0.3), (0, 0.3)], 'red', 12)
    m.cyl(0, 0, -0.3, 0.13, 0.07, 'ink', 12); m.cyl(0, 0, 0.3, 0.13, 0.07, 'ink', 12)
    m.box(-0.012, 0.012, -0.012, 0.012, 0.33, 0.55, 'ink'); return m.finish(name)
def mod_bunting(name, L=4.6, n=8, sagv=0.35):
    m = MB(); cols = ['red', 'acc_yellow', 'blue', 'green', 'offwhite', 'pink_acc', 'orange', 'teal']
    pts = [(0, -L / 2 + L * k / 12, -sagv * math.sin(math.pi * k / 12)) for k in range(13)]
    for a, b in zip(pts, pts[1:]):
        mid = Vector(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)); d = Vector(b) - Vector(a)
        m.cyl(0, 0, 0, 0.018, d.length + 0.01, 'canvas', 6, M=T(*mid) @ Rx(-math.degrees(math.atan2(d.z, d.y))), axis='Y')
    for k in range(n):
        t = (k + 0.5) / n; y = -L / 2 + L * t; z = -sagv * math.sin(math.pi * t)
        m.prism([(-0.17, 0), (0.17, 0), (0, -0.36)], -0.012, 0.012, cols[k % len(cols)], T(0, y, z) @ FPX)
    return m.finish(name)
def mod_aboard(name, col='green'):
    m = MB()
    for s_ in (-1, 1): m.box(-0.06 + s_ * 0.14, 0.06 + s_ * 0.14, -0.36, 0.36, 0, 1.0, 'wood', 0.03, M=T(0, 0, 0) @ Ry(s_ * 10))
    m.box(0.21, 0.24, -0.29, 0.29, 0.3, 0.9, col if col != 'green' else 'leaf_dk', 0.02, M=Ry(10))
    m.box(0.24, 0.25, -0.2, 0.2, 0.62, 0.74, 'offwhite', 0.01, M=Ry(10))
    return m.finish(name)
def mod_plaque(name, col, word):
    m = MB(); m.box(-0.05, 0.05, -0.45, 0.45, -0.32, 0.0, col, 0.03); m.text(word, T(0.055, 0, -0.16) @ FPX, 0.22, 'offwhite', 0.01)
    for yy in (-0.35, 0.35): m.box(-0.01, 0.01, yy - 0.01, yy + 0.01, 0.0, 0.25, 'ink')
    return m.finish(name)

for k_, (c1, c2) in AWN.items(): mod_awning('MOD_Awning_' + k_, c1, c2, plain=(k_ == 'Plain'))
mod_post('MOD_StallPost'); mod_counter('MOD_Counter_Wood', 'wood', 'wood_dk'); mod_counter('MOD_Counter_Teal', 'teal', 'offwhite', h=0.82)
mod_counter('MOD_Counter_Low', 'wood_dk', 'wood_lt', h=0.6); mod_tier('MOD_CounterTier', 'wood_lt'); mod_ice('MOD_IceBed')
mod_fishrow('MOD_FishRow_Blue', 'fish_blue', 'fish_silver'); mod_fishrow('MOD_FishRow_Pink', 'fish_pink', 'offwhite')
mod_foambox('MOD_FoamBox'); mod_cooler('MOD_Cooler'); mod_crate('MOD_Crate_Wood', 'wood', 'wood_dk'); mod_crate('MOD_Crate_Blue', 'blue', 'navy')
mod_crate('MOD_Crate_Green', 'green', 'leaf_dk'); mod_basket('MOD_Basket_Green', 'green'); mod_basket('MOD_Basket_Blue', 'blue')
mod_produce('MOD_Produce_Orange', 'orange_fr', 'orange', 0.12); mod_produce('MOD_Produce_Cabbage', 'cabbage', 'leaf_lt', 0.16, 5)
mod_produce('MOD_Produce_Apple', 'apple', 'red_dk', 0.11); mod_produce('MOD_Produce_Banana', 'banana', 'acc_yellow', 0.13, 5, (1.8, 0.7, 0.6))
mod_produce('MOD_Produce_Daikon', 'daikon', 'offwhite', 0.11, 5, (2.4, 0.6, 0.6)); mod_produce('MOD_Produce_Egg', 'yolk', 'acc_yellow', 0.13, 5, (1.3, 1, 0.5))
mod_fridge('MOD_Fridge'); mod_tub('MOD_Tub_Pickle', 'leaf_lt'); mod_tub('MOD_Tub_Plum', 'red_dk'); mod_lantern('MOD_Lantern')
mod_bunting('MOD_Bunting'); mod_aboard('MOD_ABoard')
mod_banner('MOD_Banner_Tsuke', '漬', 'navy'); mod_banner('MOD_Banner_Sake', '酒', 'red'); mod_banner('MOD_Banner_Yasai', '安', 'green')
mod_plaque('MOD_Plaque_Sale', 'red', '特売')

for o in list(bpy.data.objects):
    if any(o.name.endswith(s_) for s_ in ('_Stall_Boxes', '_Stall_Canopy', '_Stall_Cards', '_Stall_Counter', '_Stall_Fish', '_Stall_Frame',
                                         '_Stall_Ice', '_Stall_Lights', '_Stall_Props', '_Bunting')): delete([o])

def awning(cr, k, var, back_z, sy=1.0, sx=1.0):
    a = place('MOD_Awning_' + var, 'STALL_%s_Awning' % k, cr, (-2.07, 0, back_z), s=(sx, sy, 1.0), c='ENV_STALLS')
    so = a.modifiers.new('Solidify', 'SOLIDIFY'); so.thickness = 0.025; so.offset = 1.0; so.use_even_offset = True
    bv = a.modifiers.new('Bevel', 'BEVEL'); bv.width = 0.015; bv.segments = 2; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(40)
    for px_ in (-2.02, -2.02 + 2.55 * sx - 0.5):
        for py in (-2.2 * sy, 2.2 * sy):
            zt = back_z - 0.38 * (px_ + 2.07) / (2.55 * sx) - 0.05
            place('MOD_StallPost', nm('STALL_%s_Post' % k), cr, (px_, py, 0), s=(1, 1, zt), c='ENV_STALLS')
    return a

S = {}
# A - FISH (left, near): blue/white awning, wood counter, ice + big fish, foam boxes + cooler, lanterns
cr = CORNERS['L1']
awning(cr, 'Fish_A', 'Blue', 2.8)
place('MOD_Counter_Wood', 'STALL_Fish_A_Counter', cr, (0.03, 0, 0), c='ENV_STALLS')
place('MOD_IceBed', 'STALL_Fish_A_Ice', cr, (-0.4, 0, 0.78), c='ENV_STALLS')
place('MOD_FishRow_Blue', 'STALL_Fish_A_FishRow', cr, (-0.4, 0, 0.86), c='ENV_STALLS')
place('MOD_CounterTier', 'STALL_Fish_A_Tier', cr, (-1.25, 0, 0.78), c='ENV_STALLS')
for i, (x, y, z, r) in enumerate(((-1.25, -1.3, 1.06, 2), (-1.25, 0.1, 1.06, -3), (-1.25, 1.4, 1.06, 4))):
    place('MOD_FoamBox', nm('PROP_FoamBox'), cr, (x, y, z), rz=r, c='ENV_PROPS')
place('MOD_Cooler', nm('PROP_Cooler'), cr, (0.55, -2.55, 0), rz=8, c='ENV_PROPS')
place('MOD_FoamBox', nm('PROP_FoamBox'), cr, (-0.2, -2.6, 0), rz=-4, c='ENV_PROPS')
place('MOD_FoamBox', nm('PROP_FoamBox'), cr, (-0.2, -2.6, 0.38), rz=5, s=0.95, c='ENV_PROPS')
for y in (-2.0, 2.0): place('MOD_Lantern', nm('STALL_Lantern'), cr, (0.35, y, 1.95), c='ENV_STALLS')
place('MOD_ABoard', nm('PROP_ABoard'), cr, (0.85, 1.5, 0), rz=-25, c='ENV_PROPS')
place('MOD_Bunting', nm('STALL_Bunting'), cr, (WX + 0.35, 0.2, 3.9), c='ENV_STALLS')

# B - GREENGROCER (right, near): green/cream awning set higher, teal counter, baskets of produce masses, crates on the ground
cr = CORNERS['R1']
awning(cr, 'Veg_B', 'Green', 3.0, sy=1.02)
place('MOD_Counter_Teal', 'STALL_Veg_B_Counter', cr, (0.03, 0, 0), c='ENV_STALLS')
place('MOD_CounterTier', 'STALL_Veg_B_Tier', cr, (-1.3, 0, 0.82), s=(1, 1, 1.4), c='ENV_STALLS')
prods = ['Orange', 'Cabbage', 'Apple', 'Banana', 'Daikon', 'Orange']
for i in range(6):
    row, col_ = divmod(i, 3); x = -0.45 - row * 0.85; y = -1.35 + col_ * 1.35; z = 0.82 + row * 0.39
    place('MOD_Basket_Green' if i % 2 == 0 else 'MOD_Basket_Blue', nm('STALL_Veg_B_Basket'), cr, (x, y, z), rz=RNG.uniform(-5, 5), s=(1.4, 1.6, 1.0), c='ENV_STALLS')
    place('MOD_Produce_' + prods[i], nm('PROP_Produce'), cr, (x, y, z), rz=RNG.uniform(0, 360), s=(1.35, 1.5, 1.15), c='ENV_PROPS')
place('MOD_Crate_Wood', nm('PROP_Crate'), cr, (0.55, -2.5, 0), rz=4, c='ENV_PROPS')
place('MOD_Crate_Wood', nm('PROP_Crate'), cr, (0.55, -2.5, 0.5), rz=-3, s=(0.95, 0.95, 1.0), c='ENV_PROPS')
place('MOD_Produce_Cabbage', nm('PROP_Produce'), cr, (0.55, -2.5, 0.78), s=1.3, c='ENV_PROPS')
place('MOD_Banner_Yasai', 'STALL_Veg_B_Banner', cr, (0.45, 1.3, 2.6), c='ENV_STALLS')

# C - PICKLES (left, far): red/white awning, lower & shallower, low counter with big tubs, noren at the doorway, bucket
cr = CORNERS['L2']
awning(cr, 'Pickle_C', 'Red', 2.55, sx=0.88)
place('MOD_Counter_Low', 'STALL_Pickle_C_Counter', cr, (-0.15, 0, 0), s=(0.92, 1, 1), c='ENV_STALLS')
for i, y in enumerate((-1.35, 0.0, 1.35)):
    place('MOD_Tub_Pickle' if i != 1 else 'MOD_Tub_Plum', nm('PROP_Tub'), cr, (-0.85, y, 0.6), rz=RNG.uniform(0, 360), s=(1.25, 1.25, 1.1), c='ENV_PROPS')
for y in (-0.45, 0.45): place('MOD_Banner_Tsuke', nm('STALL_Pickle_C_Noren'), cr, (WX + 0.12, y + 0.2, 2.55), c='ENV_STALLS')
place('MOD_Crate_Blue', nm('PROP_Crate'), cr, (0.45, -2.5, 0), rz=-6, c='ENV_PROPS')
for y in (-1.95, 1.95): place('MOD_Lantern', nm('STALL_Lantern'), cr, (0.3, y, 1.75), c='ENV_STALLS')
place('MOD_Plaque_Sale', 'STALL_Pickle_C_Plaque', cr, (0.15, 0.0, 2.05), c='ENV_STALLS')

# D - DRINKS (right, far): yellow/white awning wider and taller, big refrigerated block, crates of bottles, vertical banner
cr = CORNERS['R2']
awning(cr, 'Drinks_D', 'Yellow', 3.1, sy=1.05, sx=1.06)
place('MOD_Fridge', 'STALL_Drinks_D_Fridge', cr, (-1.35, -1.05, 0), c='ENV_STALLS')
place('MOD_Fridge', 'STALL_Drinks_D_Fridge2', cr, (-1.35, 0.15, 0), s=(1, 1, 0.92), c='ENV_STALLS')
place('MOD_Counter_Low', 'STALL_Drinks_D_Counter', cr, (0.0, 1.45, 0), s=(0.6, 0.3, 1.0), c='ENV_STALLS')
for i, (x, y, z) in enumerate(((-0.35, 1.2, 0.6), (-0.35, 1.85, 0.6), (-0.85, 1.5, 0.6))):
    place('MOD_Crate_Blue' if i != 1 else 'MOD_Crate_Green', nm('PROP_Crate'), cr, (x, y, z), rz=RNG.uniform(-6, 6), s=(0.85, 0.85, 0.8), c='ENV_PROPS')
place('MOD_Banner_Sake', 'STALL_Drinks_D_Banner', cr, (0.5, -1.9, 2.55), c='ENV_STALLS')
place('MOD_Crate_Blue', nm('PROP_Crate'), cr, (0.5, -2.55, 0), rz=5, c='ENV_PROPS')
place('MOD_Crate_Blue', nm('PROP_Crate'), cr, (0.5, -2.55, 0.5), rz=-4, c='ENV_PROPS')

# E - MARKET CORNER (end of the street, facing the camera): plain canvas awning, produce in baskets, bunting, fan, posters
cr = CORNERS['End']
awning(cr, 'Market_E', 'Plain', 2.85)
place('MOD_Counter_Wood', 'STALL_Market_E_Counter', cr, (0.03, 0, 0), s=(1, 1, 0.95), c='ENV_STALLS')
place('MOD_CounterTier', 'STALL_Market_E_Tier', cr, (-1.3, 0, 0.74), s=(1, 1, 1.2), c='ENV_STALLS')
prods = ['Apple', 'Banana', 'Cabbage', 'Orange', 'Egg', 'Daikon']
for i in range(6):
    row, col_ = divmod(i, 3); x = -0.45 - row * 0.85; y = -1.35 + col_ * 1.35; z = 0.74 + row * 0.34
    place('MOD_Basket_Green' if (i + 1) % 2 else 'MOD_Basket_Blue', nm('STALL_Market_E_Basket'), cr, (x, y, z), rz=RNG.uniform(-5, 5), s=(1.4, 1.6, 1.0), c='ENV_STALLS')
    place('MOD_Produce_' + prods[i], nm('PROP_Produce'), cr, (x, y, z), rz=RNG.uniform(0, 360), s=(1.35, 1.5, 1.15), c='ENV_PROPS')
place('MOD_Bunting', nm('STALL_Bunting'), cr, (0.4, 0, 2.35), c='ENV_STALLS')
place('MOD_Bunting', nm('STALL_Bunting'), cr, (WX + 0.4, 0.2, 3.95), rz=180, c='ENV_STALLS')
for i, (x, y, z, r) in enumerate(((0.6, -2.55, 0, 3), (0.62, -2.5, 0.5, -5))):
    place('MOD_Crate_Wood', nm('PROP_Crate'), cr, (x, y, z), rz=r, c='ENV_PROPS')
place('MOD_Produce_Orange', nm('PROP_Produce'), cr, (0.62, -2.5, 0.78), s=1.3, c='ENV_PROPS')
place('MOD_ABoard', nm('PROP_ABoard'), cr, (0.9, 1.55, 0), rz=15, c='ENV_PROPS')

# =====================================================================================================================
# PASS 5 - utility poles / signage: thicker poles, fewer parts, chunky transformer, few thick sagging wires
# =====================================================================================================================
def mod_pole(name):
    m = MB(); m.cyl(0, 0, 4.1, 0.205, 8.2, 'concrete', 10, r2=0.155)          # +20% radius, 10 sides
    m.box(-0.3, 0.3, -0.3, 0.3, 0, 0.08, 'concrete_dk', 0.03)
    for k in range(3):                                                    # guard sleeve: 3 broad yellow/dark bands
        z0 = 0.15 + k * 0.6; m.cyl(0, 0, z0 + 0.15, 0.245, 0.3, 'acc_yellow', 10); m.cyl(0, 0, z0 + 0.45, 0.245, 0.3, 'ink', 10)
    m.box(-0.85, 0.85, -0.09, 0.09, 7.5, 7.68, 'metal', 0.04)            # one fat cross arm
    for x in (-0.6, 0.6): m.cyl(x, 0, 7.78, 0.08, 0.2, 'foam', 8, r2=0.05)
    return m.finish(name)
def mod_transformer(name):
    m = MB(); m.box(-0.38, -0.1, -0.12, 0.12, 0.05, 0.75, 'metal', 0.04)     # big bracket
    m.cyl(0.0, 0, 0.45, 0.33, 0.95, 'metal_lt', 12, bev=0.05); m.cyl(0, 0, 0.98, 0.3, 0.14, 'metal', 12, r2=0.18, bev=0.03)
    m.box(0.3, 0.36, -0.1, 0.1, 0.4, 0.6, 'acc_yellow', 0.02); return m.finish(name)
def mod_lamp(name):
    m = MB(); m.lathe([(0, 0.0), (0.06, 0.0), (0.06, 0.4), (0.0, 0.4)], 'metal', 8, M=T(0.0, 0, 0) @ Ry(0))
    pts = [(0.0, 0.0), (0.5, 0.35), (1.1, 0.42)]
    for a, b in zip(pts, pts[1:]):
        d = Vector((b[0] - a[0], 0, b[1] - a[1])); mid = Vector(((a[0] + b[0]) / 2, 0, (a[1] + b[1]) / 2))
        m.cyl(0, 0, 0, 0.05, d.length + 0.06, 'metal', 8, M=T(*mid) @ Ry(math.degrees(math.atan2(d.x, d.z))))
    m.lathe([(0, 0.0), (0.19, 0.0), (0.16, 0.09), (0.0, 0.12)], 'metal_lt', 10, M=T(1.15, 0, 0.3))
    return m.finish(name)
def mod_plate(name):
    m = MB(); m.box(0.0, 0.05, -0.17, 0.17, -0.35, 0.35, 'offwhite', 0.03); m.box(0.03, 0.06, -0.17, 0.17, 0.15, 0.35, 'blue', 0.02)
    m.text('12', T(0.065, 0, -0.1) @ FPX, 0.22, 'ink', 0.01); return m.finish(name)
def mod_stopsign(name):
    m = MB(); s_ = 0.62   # Japanese stop sign: an inverted red triangle with a white rim and 止まれ
    tri = [(-s_ * 0.866, s_ * 0.5), (s_ * 0.866, s_ * 0.5), (0, -s_)]
    m.prism([(y, z) for y, z in tri], 0.0, 0.07, 'offwhite', Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))), bev=0.0)
    tri2 = [(y * 0.8, z * 0.8) for y, z in tri]
    m.prism(tri2, 0.06, 0.09, 'red', Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    m.text('止まれ', T(0.095, 0, 0.12) @ FPX, 0.2, 'offwhite', 0.01)
    m.box(-0.25, 0.0, -0.06, 0.06, -0.06, 0.06, 'metal', 0.02)
    return m.finish(name)
mod_pole('MOD_Pole'); mod_transformer('MOD_Transformer'); mod_lamp('MOD_StreetLamp'); mod_plate('MOD_PolePlate'); mod_stopsign('MOD_Sign_Tomare')
for o in list(bpy.data.objects):
    if o.name.endswith('_UtilityPole'): delete([o])
POLE_L = Vector((0.75, -3.3, 0))
POLES = {}
for k, cr in CORNERS.items():
    p = place('MOD_Pole', 'UTIL_Pole_%s' % KN[k], cr, POLE_L, rz={'L1': 0, 'L2': 4, 'R1': -3, 'R2': 2, 'End': 0}[k], c='ENV_UTILITY')
    POLES[k] = p
    if k in ('L1', 'R2', 'End'): place('MOD_Transformer', 'UTIL_Transformer_%s' % KN[k], p, (0.5, 0, 5.0), rz=0, c='ENV_UTILITY')
    if k in ('L2', 'R1', 'End'): place('MOD_StreetLamp', 'UTIL_StreetLamp_%s' % KN[k], p, (0.18, 0, 4.5), rz=0, c='ENV_UTILITY')
    place('MOD_PolePlate', 'SIGN_PolePlate_%s' % KN[k], p, (0.2, 0, 2.6), rz=0, ry=0, c='ENV_SIGNS')
# the 止まれ sign on the pole nearest the stop line (left far pole), tilted 3 degrees
place('MOD_Sign_Tomare', 'SIGN_Tomare_A', POLES['L2'], (0.0, -0.22, 3.0), rz=-90, rx=3, c='ENV_SIGNS')
bpy.context.view_layer.update()
WIRES = [('L1', 'L2', 7.45, 0.55), ('L2', 'End', 7.45, 0.6), ('R1', 'R2', 7.45, 0.55), ('R2', 'End', 7.3, 0.7), ('L2', 'R2', 7.0, 0.7), ('R1', None, 6.6, 0.45)]
for i, (a, b, z, sagv) in enumerate(WIRES):
    pa = POLES[a].matrix_world @ Vector((0.6 if a.startswith('L') else -0.6, 0, z))
    if b: pb = POLES[b].matrix_world @ Vector((-0.6 if b.startswith('R') else 0.6, 0, z - 0.1))
    else: pb = CORNERS[a].matrix_world @ Vector((WX + 0.1, -1.4, 5.6))
    cu = bpy.data.curves.new('WIRE_%d' % i, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.028; cu.bevel_resolution = 1; cu.resolution_u = 6
    sp = cu.splines.new('POLY'); N = 10; sp.points.add(N)
    for j in range(N + 1):
        t = j / N; p = pa.lerp(pb, t); p.z -= sagv * math.sin(math.pi * t); sp.points[j].co = (*p, 1)
    cu.materials.append(M_KIT)
    wo = bpy.data.objects.new('UTIL_Wire_%s' % chr(65 + i), cu); CN['ENV_UTILITY'].objects.link(wo)

# =====================================================================================================================
# PASS 6 - props: chunkier, fewer, bigger; controlled imperfection
# =====================================================================================================================
def mod_bin(name):
    m = MB(); m.cyl(0, 0, 0.4, 0.29, 0.8, 'teal', 14, r2=0.33, bev=0.03); m.cyl(0, 0, 0.84, 0.36, 0.1, 'green', 14, bev=0.03)
    m.box(-0.13, 0.13, -0.05, 0.05, 0.88, 0.95, 'green', 0.025); return m.finish(name)
def mod_bucket(name):
    m = MB(); m.cyl(0, 0, 0.18, 0.17, 0.36, 'acc_yellow', 12, r2=0.22, bev=0.025); m.cyl(0, 0, 0.35, 0.225, 0.04, 'orange', 12)
    return m.finish(name)
def mod_cone(name):
    m = MB(); m.box(-0.22, 0.22, -0.22, 0.22, 0, 0.07, 'orange', 0.03)
    m.cyl(0, 0, 0.4, 0.19, 0.66, 'orange', 12, r2=0.06); m.cyl(0, 0, 0.45, 0.145, 0.15, 'offwhite', 12, r2=0.115)
    return m.finish(name)
def mod_chair(name):
    m = MB(); m.cyl(0, 0, 0.46, 0.22, 0.09, 'red', 12, bev=0.03)
    for dx, dy in ((0.13, 0.13), (-0.13, 0.13), (0.13, -0.13), (-0.13, -0.13)):
        m.cyl(0, 0, 0, 0.04, 0.46, 'red_dk', 8, M=T(dx, dy, 0.22) @ Rx(-dy * 50) @ Ry(dx * 50))
    return m.finish(name)
def mod_table(name):
    m = MB(); m.cyl(0, 0, 0.76, 0.58, 0.09, 'wood', 16, bev=0.03); m.cyl(0, 0, 0.37, 0.08, 0.72, 'ink', 10)
    m.cyl(0, 0, 0.03, 0.32, 0.06, 'ink', 12, bev=0.02); return m.finish(name)
def mod_bottle(name):
    m = MB(); m.cyl(0, 0, 0.16, 0.09, 0.32, 'green', 10, bev=0.02); m.cyl(0, 0, 0.38, 0.04, 0.14, 'green', 8, r2=0.035)
    m.cyl(0, 0, 0.46, 0.045, 0.04, 'red', 8); return m.finish(name)
def mod_bottlecrate(name):
    m = MB(); m.box(-0.3, 0.3, -0.22, 0.22, 0, 0.3, 'acc_yellow', 0.04)
    for i in range(3):
        for j in range(2): m.cyl(-0.18 + i * 0.18, -0.09 + j * 0.18, 0.38, 0.07, 0.2, 'green' if (i + j) % 2 else 'leaf_dk', 8, bev=0.015)
    return m.finish(name)
def mod_plant(name, pot='terracotta', leaf=('leaf', 'leaf_lt', 'leaf_dk')):
    m = MB(); m.cyl(0, 0, 0.26, 0.22, 0.52, pot, 12, r2=0.29, bev=0.03); m.cyl(0, 0, 0.5, 0.31, 0.06, pot, 12)
    for (dx, dy, z, r), c in zip(((0, 0, 0.86, 0.36), (0.2, 0.1, 0.72, 0.26), (-0.18, -0.08, 0.74, 0.27)), leaf):
        m.ico(dx, dy, z, r, c, 1, (1, 1, 0.9), jit=0.07)
    return m.finish(name)
def mod_vending(name, body, acc, panel):
    """chunky Japanese vending machine: pivot at the back foot, front faces +X."""
    m = MB(); m.box(0.0, 0.8, -0.48, 0.48, 0, 1.9, body, 0.06, 3)
    m.box(0.0, 0.84, -0.48, 0.48, 1.62, 1.9, acc, 0.05)
    m.box(0.76, 0.83, -0.42, 0.2, 0.95, 1.56, 'glass_lt', 0.02)
    for r in range(2):
        for k in range(3):
            z = 1.02 + r * 0.28
            m.box(0.62, 0.78, -0.37 + k * 0.19, -0.25 + k * 0.19, z, z + 0.22, ['red', 'blue', 'green', 'acc_yellow', 'orange', 'sky_sign'][(k + r * 3) % 6], 0.03)
    m.box(0.8, 0.86, 0.25, 0.44, 0.9, 1.5, panel, 0.03)
    m.box(0.8, 0.86, -0.36, 0.14, 0.12, 0.36, 'ink', 0.04)
    m.box(0.8, 0.84, -0.42, 0.2, 0.45, 0.86, acc, 0.02)
    return m.finish(name)
def mod_recycle(name):
    m = MB(); m.box(-0.22, 0.22, -0.25, 0.25, 0, 0.82, 'offwhite', 0.05); m.box(-0.24, 0.24, -0.27, 0.27, 0.8, 0.9, 'blue', 0.04)
    for hy in (-0.11, 0.11): m.cyl(0, hy, 0.905, 0.075, 0.02, 'ink', 10)
    m.box(0.22, 0.24, -0.17, 0.17, 0.45, 0.7, 'blue', 0.015); return m.finish(name)
def mod_puddle(name, rx, ry, sd):
    m = MB(); bm = m.bm
    def outline(sc_, N=28):
        pts = []
        for i in range(N):
            a = i / N * math.pi * 2
            r = 1 + 0.16 * math.sin(a * 2 + sd) + 0.09 * math.sin(a * 3 + sd * 2.3) + 0.05 * math.sin(a * 5 + sd * 4.1)
            pts.append((math.cos(a) * r * rx * sc_, math.sin(a) * r * ry * sc_))
        return pts
    m.prism(outline(1.0), 0.0, 0.006, 'water_lt'); m.prism(outline(0.86), 0.0, 0.012, 'water')
    return m.finish(name)
mod_bin('MOD_Bin'); mod_bucket('MOD_Bucket'); mod_cone('MOD_Cone'); mod_chair('MOD_Chair'); mod_table('MOD_Table'); mod_bottle('MOD_Bottle_Big')
mod_bottlecrate('MOD_BottleCrate'); mod_plant('MOD_Plant_A'); mod_plant('MOD_Plant_B', 'blue', ('leaf_lt', 'leaf', 'leaf_lt'))
mod_vending('MOD_Vending_Red', 'red', 'red_dk', 'offwhite'); mod_vending('MOD_Vending_White', 'offwhite', 'blue', 'sky_sign'); mod_recycle('MOD_Bin_Recycle')
PUD = [(1.6, -19.2, 2.2, 1.4, 1.3), (2.2, -26.5, 1.4, 1.1, 2.7), (-9.2, -24.8, 0.9, 0.8, 4.1)]
for i, (x, z, rx, rz, sd_) in enumerate(PUD): mod_puddle('MOD_Puddle_%s' % 'ABC'[i], rx, rz, sd_)

for o in list(bpy.data.objects):
    if o.name.endswith(('_VendingMachine_Red', '_VendingMachine_White', '_RecycleBin', '_Plants')) or o.name.startswith('Puddle_'): delete([o])
# corner street furniture
for k, cr in CORNERS.items():
    place('MOD_Vending_Red' if k != 'R1' else 'MOD_Vending_White', nm('PROP_Vending'), cr, (-2.58, 3.83, 0), rz=RNG.uniform(-2, 2), c='ENV_PROPS')
    if k not in ('L2',): place('MOD_Vending_White' if k != 'R1' else 'MOD_Vending_Red', nm('PROP_Vending'), cr, (-2.58, 4.85, 0), rz=RNG.uniform(-2, 2), c='ENV_PROPS')
    place('MOD_Bin_Recycle', nm('PROP_BinRecycle'), cr, (-2.1, 3.0, 0), rz=RNG.uniform(-5, 5), c='ENV_PROPS')
    place('MOD_Plant_A', nm('VEG_Plant'), cr, (-2.25, -2.45, 0), rz=RNG.uniform(0, 360), s=RNG.uniform(0.95, 1.1), c='ENV_VEGETATION')
    if k in ('L1', 'End', 'R2'): place('MOD_Plant_B', nm('VEG_Plant'), cr, (-2.2, 2.55, 0), rz=RNG.uniform(0, 360), s=0.85, c='ENV_VEGETATION')
# kitslice street props, rebuilt chunkier at the same spots (positions unchanged = same collision footprint)
orig = {o.name: o for o in bpy.data.objects if o.name.startswith('Orig_') and o.parent is None}
def gpos(o): return o.location.copy()
REPL = {'Crate': ('MOD_Crate_Wood', 1.0, 'PROP_Crate'), 'Bin': ('MOD_Bin', 1.15, 'PROP_Bin'), 'Bucket': ('MOD_Bucket', 1.2, 'PROP_Bucket'),
        'Cone': ('MOD_Cone', 1.2, 'PROP_Cone'), 'Chair': ('MOD_Chair', 1.12, 'PROP_Chair'), 'Table': ('MOD_Table', 1.05, 'PROP_Table'),
        'Plant': ('MOD_Plant_A', 1.0, 'VEG_Plant')}
bottles = []
for n_, o in sorted(orig.items()):
    kind = n_.split('_')[1]
    if kind == 'Bottle': bottles.append(gpos(o)); continue
    mod, s_, pre = REPL[kind]
    s0 = o.scale.x * s_ * RNG.uniform(0.93, 1.07)
    place(mod, nm(pre), None, gpos(o), rz=math.degrees(o.rotation_euler.z) + RNG.uniform(-5, 5), rx=RNG.uniform(-2, 2), s=s0,
          c='ENV_VEGETATION' if kind == 'Plant' else 'ENV_PROPS')
# 5 tiny bottles -> one big bottle on the table + one bottle crate by the left kerb
place('MOD_Bottle_Big', nm('PROP_Bottle'), None, (3.3, 21.0, 0.8), rz=20, s=1.0, c='ENV_PROPS')
place('MOD_BottleCrate', nm('PROP_BottleCrate'), None, (-4.25, 21.1, 0), rz=-8, c='ENV_PROPS')
for o in list(bpy.data.objects):
    if o.name.startswith('Orig_'): delete([o])
for i, (x, z, rx, rz, sd_) in enumerate(PUD): place('MOD_Puddle_%s' % 'ABC'[i], 'ROAD_Puddle_%s' % 'ABC'[i], None, (x, -z, 0.004), c='ENV_ROAD')

# road: chunkier kerbs (same footprint), keep painted marks; rebuild as palette modules
def mod_road(name):
    m = MB(); m.box(-7.2, 7.2, 9, 33, -0.02, 0.0, 'road'); m.box(-1.6, 1.6, 9, 33, 0.0, 0.004, 'road_band'); return m.finish(name)
def mod_pavement(name):
    m = MB(); m.box(-1.3, 1.3, -12, 12, 0, 0.1, 'pave', 0.03); return m.finish(name)
def mod_kerb(name):
    m = MB(); m.box(-0.12, 0.12, -12, 12, 0, 0.14, 'kerb', 0.05, 3); return m.finish(name)
def mod_line(name, L, Wd):
    m = MB(); m.box(-Wd / 2, Wd / 2, -L / 2, L / 2, 0, 0.012, 'line', 0.004); return m.finish(name)
def mod_manhole(name):
    m = MB(); m.cyl(0, 0, 0.01, 0.46, 0.02, 'road_dk', 16, bev=0.008); m.cyl(0, 0, 0.022, 0.34, 0.01, 'concrete_dk', 16); return m.finish(name)
def mod_grate(name):
    m = MB(); m.box(-0.38, 0.38, -0.25, 0.25, 0, 0.02, 'road_dk', 0.02)
    for k in range(3): m.box(-0.3 + k * 0.22, -0.2 + k * 0.22, -0.18, 0.18, 0.015, 0.025, 'concrete_dk', 0.008)
    return m.finish(name)
def mod_tomare(name):
    m = MB(); m.text('止まれ', Matrix.Identity(4), 1.25, 'line', 0.004, spacing=1.05); return m.finish(name)
for n_ in ('Road', 'Road_CentreBand', 'Pavement_L', 'Pavement_R', 'Kerb_L', 'Kerb_R', 'EdgeLine_L', 'EdgeLine_R', 'StopLine', 'Tomare', 'Manhole', 'Grate_0', 'Grate_1', 'Grate_2'):
    delete([bpy.data.objects.get(n_)])
mod_road('MOD_Road'); mod_pavement('MOD_Pavement'); mod_kerb('MOD_Kerb'); mod_line('MOD_Line_Edge', 24, 0.14); mod_line('MOD_Line_Stop', 0.5, 4.4)
mod_manhole('MOD_Manhole'); mod_grate('MOD_Grate'); mod_tomare('MOD_Road_Tomare')
place('MOD_Road', 'ROAD_Asphalt', None, (0, 0, 0), c='ENV_ROAD')
gm = MB(); gm.box(-18, 18, -2, 42, -0.08, -0.03, 'concrete'); gm.finish('MOD_Ground')
place('MOD_Ground', 'ROAD_Ground', None, (0, 0, 0), c='ENV_ROAD')
for sd_, k in ((-1, 'L'), (1, 'R')):
    place('MOD_Pavement', 'ROAD_Pavement_' + k, None, (sd_ * 5.9, 21, 0), c='ENV_ROAD')
    place('MOD_Kerb', 'ROAD_Kerb_' + k, None, (sd_ * 4.55, 21, 0), c='ENV_ROAD')
    place('MOD_Line_Edge', 'ROAD_EdgeLine_' + k, None, (sd_ * 3.6, 21, 0.004), c='ENV_ROAD')
place('MOD_Line_Stop', 'ROAD_StopLine', None, (-2.2, 23.2, 0.004), c='ENV_ROAD')
place('MOD_Road_Tomare', 'ROAD_Tomare', None, (-2.2, 21.6, 0.006), c='ENV_ROAD')
place('MOD_Manhole', 'ROAD_Manhole', None, (1.6, 12.2, 0), c='ENV_ROAD')
for i, z in enumerate((14.5, 20.5, 26.5)): place('MOD_Grate', nm('ROAD_Grate'), None, (0, z, 0.004), rz=RNG.uniform(-3, 3), c='ENV_ROAD')

# =====================================================================================================================
# PASS 7 - character: material only (rig, mesh, animation untouched)
# =====================================================================================================================
for m in bpy.data.materials:
    if not m.use_nodes: continue
    b = m.node_tree.nodes.get('Principled BSDF')
    if not b: continue
    if m.name.startswith('Skin'):
        b.inputs['Roughness'].default_value = 0.78; b.inputs['Specular IOR Level'].default_value = 0.2
        b.inputs['Coat Weight'].default_value = 0.0; b.inputs['Sheen Weight'].default_value = 0.0
        lk = b.inputs['Base Color'].links
        if lk:   # warm the skin texture a touch (multiply by a warm tint), keep its painted detail
            src = lk[0].from_socket; N = m.node_tree.nodes
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            mx.inputs['B'].default_value = (1.0, 0.9, 0.8, 1); m.node_tree.links.new(src, mx.inputs['A']); m.node_tree.links.new(mx.outputs['Result'], b.inputs['Base Color'])
        else:
            b.inputs['Base Color'].default_value = (*hexlin('f2b48e'), 1)
    elif m.name.startswith('Mawashi'):
        b.inputs['Base Color'].default_value = (*hexlin('1f3a8a'), 1); b.inputs['Roughness'].default_value = 0.9
        b.inputs['Specular IOR Level'].default_value = 0.15
    elif m.name.startswith(('Hair', 'Ink')):
        b.inputs['Roughness'].default_value = 0.6; b.inputs['Base Color'].default_value = (*hexlin('262230'), 1)
for o in list(bpy.data.objects):
    if any(c.name == 'ORIG_CHARACTER' for c in o.users_collection):
        for c in list(o.users_collection): c.objects.unlink(o)
        CN['CHARACTERS'].objects.link(o)
SUMO = bpy.data.objects['SUMO_Player']; SUMO.name = 'CHR_Sumo_Player'

# =====================================================================================================================
# PASS 8 - cameras
# =====================================================================================================================
for c in list(ORIG_CAM.users_collection): c.objects.unlink(ORIG_CAM)
CN['CAMERAS'].objects.link(ORIG_CAM)
cd = bpy.data.cameras.new('RevisedCam'); cd.lens = 40; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'; cd.clip_start = 0.1; cd.clip_end = 220
cd.dof.use_dof = False
REV = bpy.data.objects.new('CAM_Game_Revised', cd); CN['CAMERAS'].objects.link(REV)
REV_POS = Vector((1.6, 10.0, 8.3)); PITCH = 40.0      # 35 mm, 42 deg down, slightly lower than the game cam, 3/4 on the sumo's front
cd.lens = 35
yaw = math.atan2(PLAYER.x + 0.2 - REV_POS.x, PLAYER.y + 2.4 - REV_POS.y)    # aim a little past the sumo: the street ahead stays in view
REV_AIM = REV_POS + Vector((math.sin(yaw) * math.cos(math.radians(PITCH)), math.cos(yaw) * math.cos(math.radians(PITCH)), -math.sin(math.radians(PITCH))))
REV.location = REV_POS; REV.rotation_euler = (REV_AIM - REV_POS).to_track_quat('-Z', 'Y').to_euler()
# foreground framing: a festival lantern string across the street between the L2 and R1 facades; the near lanterns
# dip into the top of the revised frame (and read as an overhead string, above the player, in the original frame)
from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
def cam_point(cam_, u, v, depth):
    """world point that projects to normalised frame coords (u, v) at 'depth' metres in front of cam_."""
    d = cam_.data; aspect = scn.render.resolution_x / scn.render.resolution_y
    hw = d.sensor_width / 2 / d.lens if d.sensor_fit != 'VERTICAL' else math.tan(d.angle_y / 2) * aspect
    hh = hw / aspect
    return cam_.matrix_world @ (Vector(((u - 0.5) * 2 * hw, (v - 0.5) * 2 * hh, -1.0)) * depth)
LAN_S = 1.1
def wire_for(top):
    pa = Vector((-7.75, top.y + 0.4, top.z + 0.9)); pb = Vector((7.75, top.y - 0.4, top.z + 0.9))
    t0 = (top.x - pa.x) / (pb.x - pa.x); sg = (pa.lerp(pb, t0).z - top.z) / max(0.05, math.sin(math.pi * t0))
    return pa, pb, sg
def wire_clear(pa, pb, sg):
    """the wire must stay out of the player's band of the gameplay frame (v 0.12..0.62)."""
    for j in range(21):
        t = j / 20; p = pa.lerp(pb, t); p.z -= sg * math.sin(math.pi * t); v = world_to_camera_view(scn, ORIG_CAM, p)
        if v.z > 0 and 0 < v.x < 1 and 0.12 < v.y < 0.62: return False
    return True
best = None                                           # lantern centre just above the revised frame's top edge (its lower part enters);
for dep in [1.8 + 0.2 * i for i in range(14)]:        # keep the wire clear of the player in the gameplay frame, lantern as far out as possible
    for u in (0.06, 0.1, 0.14, 0.86, 0.9, 0.94):
        c_ = cam_point(REV, u, 1.07, dep); v_ = world_to_camera_view(scn, ORIG_CAM, c_)
        ok = wire_clear(*wire_for(c_ + Vector((0, 0, 0.55 * LAN_S))))
        score = abs(v_.x - 0.5) + (0.5 if v_.y > 1.0 or v_.z < 0 else 0) + (10 if ok else 0)
        if best is None or score > best[0]: best = (score, c_, u, dep, tuple(round(q, 2) for q in v_), ok)
print('LANTERN anchor', best)
anchor = best[1]
top = anchor + Vector((0, 0, 0.55 * LAN_S))           # where its cord meets the wire
pa, pb, sagv = wire_for(top)
cu = bpy.data.curves.new('WIRE_lanterns', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.022; cu.bevel_resolution = 1; cu.resolution_u = 6
sp = cu.splines.new('POLY'); sp.points.add(16)
for j in range(17):
    t = j / 16; p = pa.lerp(pb, t); p.z -= sagv * math.sin(math.pi * t); sp.points[j].co = (*p, 1)
cu.materials.append(M_KIT); CN['ENV_UTILITY'].objects.link(bpy.data.objects.new('UTIL_Wire_Lanterns', cu))
for x in (top.x, -top.x * 0.6 - 1.5 if top.x > 0 else 3.4):
    t = (x - pa.x) / (pb.x - pa.x); wp = pa.lerp(pb, t); wp.z -= sagv * math.sin(math.pi * t)
    place('MOD_Lantern', nm('STALL_Lantern_Street'), None, (wp.x, wp.y, wp.z - 0.55 * LAN_S), rz=RNG.uniform(-8, 8), s=LAN_S, c='ENV_STALLS')
bpy.context.view_layer.update()
for cam_ in (ORIG_CAM, REV):
    for o in [o for o in CN['ENV_STALLS'].objects if o.name.startswith('STALL_Lantern_Street')] + [SUMO]:
        v = world_to_camera_view(scn, cam_, o.matrix_world.translation + Vector((0, 0, 0.9 if o == SUMO else 0)))
        print('PROJ', cam_.name, o.name, round(v.x, 2), round(v.y, 2))

# =====================================================================================================================
# PASS 9 - cleanup: collections, names, kit
# =====================================================================================================================
for n_ in ('ORIG_ROAD', 'ORIG_CORNERS', 'ORIG_PROPS', 'ORIG_BACKDROP', 'ORIG_CHARACTER', 'ORIG_LIGHTING', 'ORIG_CAMERA'):
    c = bpy.data.collections.get(n_)
    if c:
        for o in list(c.objects):
            if o.users_collection == (c,) or len(o.users_collection) == 1: CN['ENV_PROPS'].objects.link(o)
            c.objects.unlink(o)
        bpy.data.collections.remove(c)
# leftover corner children / empties from the original GLB (none should remain except the 5 CORNER_ roots)
left = [o for o in bpy.data.objects if o.parent and o.parent.name.startswith('CORNER_') and o.data is not None and not o.data.get('kkbc_module') and o.type == 'MESH']
print('LEFTOVER corner meshes', [o.name for o in left]); delete(left)
for o in list(bpy.data.objects):
    if o.type == 'EMPTY' and o.name.startswith('Orig_'): delete([o])
# kit collection: each module once at the origin (excluded from the view layer so it does not render)
for n_, me in MODS.items():
    ob = bpy.data.objects.new(n_, me); CN['KIT_MODULES'].objects.link(ob)
for me in list(bpy.data.meshes):
    if me.users == 0: bpy.data.meshes.remove(me)
for m in list(bpy.data.materials):
    if m.users == 0: bpy.data.materials.remove(m)
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == 'KIT_MODULES': lc.exclude = True

# =====================================================================================================================
# PASS 10 - final balance (values tuned against the reference across iterations; see report)
# =====================================================================================================================
env = [o for c in CN.values() if c.name.startswith('ENV_') for o in c.objects]
print('TRIS env', tris(env), 'chars', tris(list(CN['CHARACTERS'].objects)), 'modules', len(MODS), 'objects', len(env))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/segment_kkbc.blend')
if 'dbg' in RENDERS:
    dc = bpy.data.cameras.new('dbg'); dc.lens = 24; dbg = bpy.data.objects.new('CAM_Debug', dc); CN['CAMERAS'].objects.link(dbg)
    dbg.location = (0, 1.0, 13.0); dbg.rotation_euler = (Vector((0, 20, 0)) - dbg.location).to_track_quat('-Z', 'Y').to_euler()
    render(OUT + '/dbg_overview.png', dbg)
    dbg.location = (9.5, 33.0, 6.0); dbg.rotation_euler = (Vector((-2, 22, 2.5)) - dbg.location).to_track_quat('-Z', 'Y').to_euler()
    render(OUT + '/dbg_reverse.png', dbg)
    bpy.data.objects.remove(dbg)
scn.camera = ORIG_CAM

# =====================================================================================================================
# exports: assembled environment (no sumo) + kit (one object per module at the origin)
# =====================================================================================================================
def export(objs, path):
    # glTF can't follow the per-object variation node: link the palette straight to Base Color for the export
    saved = []
    for m in (M_KIT, M_GW):
        N = m.node_tree.nodes; b = N['Principled BSDF']; m.node_tree.links.new(N['Palette'].outputs['Color'], b.inputs['Base Color'])
    bpy.ops.object.select_all(action='DESELECT')
    tmp = []
    for o in objs:
        if o.type == 'CURVE':   # wires -> meshes painted on the 'ink' swatch
            dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            uvl = me.uv_layers.get('PAL') or me.uv_layers.new(name='PAL')
            for l_ in list(me.uv_layers):
                if l_.name != 'PAL': me.uv_layers.remove(l_)
            uvl = me.uv_layers['PAL']
            for d in uvl.data: d.uv = swuv('ink')
            me.materials.clear(); me.materials.append(M_KIT)
            t = bpy.data.objects.new(o.name + '_mesh', me); t.matrix_world = o.matrix_world; ROOT.objects.link(t); tmp.append(t); t.select_set(True)
            o.hide_set(True)
        else:
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
    for t in tmp: bpy.data.objects.remove(t)
    for o in objs:
        if o.type == 'CURVE': o.hide_set(False)
    for m in (M_KIT, M_GW):
        N = m.node_tree.nodes; m.node_tree.links.new(N['VaryMix'].outputs['Result'], N['Principled BSDF'].inputs['Base Color'])
    print('EXPORT', path)
env = [o for c in CN.values() if c.name.startswith('ENV_') for o in c.objects]
export(env, OUT + '/segment_kkbc.glb')
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == 'KIT_MODULES': lc.exclude = False
export(list(CN['KIT_MODULES'].objects), OUT + '/kit.glb')
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == 'KIT_MODULES': lc.exclude = True
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/segment_kkbc.blend')
if 'final' in RENDERS:
    render(OUT + '/kkbc_gamecam.png', ORIG_CAM)
    render(OUT + '/revised_gamecam.png', REV)
print('DONE')
