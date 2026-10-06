# KKBC art-direction study, STEP 0: rebuild the ORIGINAL in-game test segment (scratchpad/kitslice.js + public/js/kit-style.js)
# in Blender, so the art pass (kkbc_pass.py) can start from it.
#   <bl python> tools/blender/kkbc_segment.py [norender]
# Writes <OUT>/segment_original.blend and <OUT>/original_gamecam.png (1280x720, EEVEE Next, from the exact game camera).
# Mapping: game (Y up, street along -Z) -> Blender (Z up): (x, y, z)_bl = (x, -z, y)_game ; game rotation.y = Blender rotation about Z.
import bpy, bmesh, math, os, sys
from mathutils import Vector

SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
OUT = SP + '/kkbc'
CORNER_GLB = SP + '/corner/corner.glb'
SUMO_GLB = SP + '/sumo_soft/sumo_soft_poses.glb'
FONT_PATH = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
NORENDER = 'norender' in sys.argv
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
ROOT = scn.collection

def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in ROOT.children: ROOT.children.link(c)
    return c
C_ROAD, C_CORNER, C_PROPS, C_BLD, C_CHAR, C_LIGHT, C_CAM = (coll(n) for n in
    ('ORIG_ROAD', 'ORIG_CORNERS', 'ORIG_PROPS', 'ORIG_BACKDROP', 'ORIG_CHARACTER', 'ORIG_LIGHTING', 'ORIG_CAMERA'))

def G(x, z, y=0.0): return Vector((x, -z, y))          # game -> blender position

def lin(h):
    h = h if isinstance(h, int) else int(h, 16)
    c = [((h >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)

MATS = {}
def kmat(h, alpha=1.0):
    """kit-style MeshLambertMaterial stand-in: matte, no specular."""
    key = (h, alpha)
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new('kit_%06x' % h + ('_a' if alpha < 1 else ''))
    m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(h), 1); b.inputs['Roughness'].default_value = 1.0
    b.inputs['Specular IOR Level'].default_value = 0.0
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'; m.surface_render_method = 'BLENDED'
    m.diffuse_color = (*lin(h), alpha); MATS[key] = m; return m

def link(ob, c):
    c.objects.link(ob); return ob

def mesh_obj(name, bm, mat, c):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), c)

def rbox(name, w, h, d, col, pos, c, round_=None, rotz=0.0, alpha=1.0):
    """K.box: w (x) x h (up) x d (z, game), bottom at pos.z (blender). Rounded with a bevel modifier."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * w, v.co.y * d, v.co.z * h + h / 2))
    ob = mesh_obj(name, bm, kmat(col, alpha), c); ob.location = pos; ob.rotation_euler.z = rotz
    r = round_ if round_ is not None else min(0.08, min(w, h, d) * 0.18)
    r = min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001)
    if r > 0.002:
        bv = ob.modifiers.new('round', 'BEVEL'); bv.width = r; bv.segments = 3; bv.limit_method = 'NONE'
    for p in ob.data.polygons: p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(40))
    return ob

def cyl(name, rt, rb, h, col, pos, c, seg=20, rot=None):
    """K.cyl centred on pos (like three.js CylinderGeometry)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=rb, radius2=rt, depth=h)
    ob = mesh_obj(name, bm, kmat(col), c); ob.location = pos
    if rot: ob.rotation_euler = rot
    for p in ob.data.polygons: p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(40))
    return ob

def sph(name, col, pos, s, c, seg=16):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=1.0)
    ob = mesh_obj(name, bm, kmat(col), c); ob.location = pos; ob.scale = s
    for p in ob.data.polygons: p.use_smooth = True
    return ob

def empty(name, pos, c, rotz=0.0):
    e = link(bpy.data.objects.new(name, None), c); e.location = pos; e.rotation_euler.z = rotz; return e

def parent(ch, par):
    ch.parent = par; return ch

# kit palette (kit-style.js K.P)
P = dict(asphalt=0x8e8992, walk=0xcfc6ba, kerb=0xe9e4dc, line=0xf2efe8, wood=0xc99a68, woodDk=0xa97c52, white=0xf6f3ee,
         red=0xd9604f, redDk=0xb84a3e, teal=0x5aa8a0, yellow=0xeac25a, orange=0xe4a978, leaf=0x7fae6a, dark=0x3d3a44)

# ================================================================ ground (kitslice.js lines 21-30)
rbox('Road', 14.4, 0.0005, 24, 0xa79d97, G(0, -21, -0.0005), C_ROAD, 0)
rbox('Road_CentreBand', 3.2, 0.0005, 24, 0xbab0a6, G(0, -21, 0.0025), C_ROAD, 0)
z = -10.0; i = 0
while z > -24:
    rbox('Road_BandJoint_%02d' % i, 3.2, 0.006, 0.05, 0xa99f96, G(0, z, 0.003), C_ROAD, 0.002); z -= 1.6; i += 1
for sd, nm in ((-1, 'L'), (1, 'R')):
    rbox('Pavement_' + nm, 2.6, 0.08, 24, P['walk'], G(sd * 5.9, -21), C_ROAD, 0.02)
    rbox('Kerb_' + nm, 0.2, 0.1, 24, P['kerb'], G(sd * 4.55, -21), C_ROAD, 0.03)
    rbox('EdgeLine_' + nm, 0.12, 0.012, 24, P['line'], G(sd * 3.6, -21), C_ROAD, 0.004)
for i, z in enumerate((-14.5, -20.5, -26.5)):
    rbox('Grate_%d' % i, 0.7, 0.02, 0.45, 0x6f6a74, G(0, z), C_ROAD, 0.04)
rbox('StopLine', 4.4, 0.012, 0.45, P['line'], G(-2.2, -23.2), C_ROAD, 0.01)
cyl('Manhole', 0.42, 0.42, 0.02, 0x77727c, G(1.6, -12.2, 0.015), C_ROAD, 24)
# 止まれ: painted text on the road, top of the glyphs toward the far end (reads from the game camera)
cu = bpy.data.curves.new('Tomare', 'FONT'); cu.body = '止まれ'; cu.size = 1.15; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
if os.path.exists(FONT_PATH): cu.font = bpy.data.fonts.load(FONT_PATH)
t = link(bpy.data.objects.new('Tomare', cu), C_ROAD); t.location = G(-2.2, -21.6, 0.012); t.data.materials.append(kmat(0xf2efe8))

# ================================================================ backdrop building blocks (kitslice.js lines 55-59)
def jsmod(a, b): return math.fmod(a, b)
bcols = [0xdfe6ea, 0xe9dcc6, 0xc9d8cf, 0xe6cfc0, 0xd4dbe6]; bk = [0]
def blk(x, z, w, d, h):
    c = bcols[bk[0] % len(bcols)]; n = bk[0]; bk[0] += 1
    rbox('Block_%02d' % n, w, h, d, c, G(x, z), C_BLD, 0.1)
    rbox('Block_%02d_Roof' % n, w + 0.2, 0.3, d + 0.2, 0x8f8a96, G(x, z, h), C_BLD, 0.08)
    for f in range(int(math.floor((h - 2.5) / 2))):
        for i in range(max(1, int(math.floor(w / 2.2)))):
            wx = x - w / 2 + 1.1 + i * 2.2
            rbox('Block_%02d_Win_%d_%d' % (n, f, i), 1.1, 1.0, 0.12, 0x8fa6bd, G(wx, z + d / 2, 2.6 + f * 2), C_BLD, 0.04)
for z in (-4, -12, -20, -28): blk(-12.5, z, 5, 8, 9 + jsmod(jsmod(z * 7, 4) + 4, 4))
for z in (-6, -14, -22, -30): blk(12.5, z, 5, 8, 10 + jsmod(jsmod(z * 3, 5) + 5, 5))
for x in (-8, -1, 6): blk(x, -36, 7, 6, 11 + jsmod(jsmod(x * 5, 3) + 3, 3))

# ================================================================ props (kitslice.js lines 37-45, built like K.prop.*)
seed = [7]
def rnd():
    seed[0] = (seed[0] * 9301 + 49297) % 233280; return seed[0] / 233280
CNT = {}
def pname(k):
    CNT[k] = CNT.get(k, 0) + 1; return 'Orig_%s_%02d' % (k, CNT[k])
def p_crate(x, z, ry):
    e = empty(pname('Crate'), G(x, z), C_PROPS, ry)
    parent(rbox(e.name + '_body', 0.62, 0.42, 0.46, P['wood'], (0, 0, 0), C_PROPS, 0.04), e)
    for y in (0.13, 0.29): parent(rbox(e.name + '_band', 0.64, 0.035, 0.48, P['woodDk'], (0, 0, y), C_PROPS, 0.012), e)
def p_bin(x, z, ry=0):
    e = empty(pname('Bin'), G(x, z), C_PROPS)
    parent(cyl(e.name + '_body', 0.3, 0.26, 0.78, P['teal'], (0, 0, 0.39), C_PROPS, 22), e)
    parent(cyl(e.name + '_lid', 0.33, 0.33, 0.07, 0x4b8e88, (0, 0, 0.8), C_PROPS, 22), e)
    parent(rbox(e.name + '_handle', 0.18, 0.06, 0.06, 0x4b8e88, (0, 0, 0.83), C_PROPS, 0.02), e)
def p_bucket(x, z, ry=0):
    e = empty(pname('Bucket'), G(x, z), C_PROPS)
    parent(cyl(e.name + '_body', 0.2, 0.16, 0.34, P['yellow'], (0, 0, 0.17), C_PROPS, 18), e)
def p_bottle(x, z):
    e = empty(pname('Bottle'), G(x, z), C_PROPS)
    parent(cyl(e.name + '_body', 0.055, 0.055, 0.2, 0x6fae7e, (0, 0, 0.1), C_PROPS, 10), e)
    parent(cyl(e.name + '_neck', 0.022, 0.04, 0.09, 0x6fae7e, (0, 0, 0.245), C_PROPS, 8), e)
def p_chair(x, z):
    e = empty(pname('Chair'), G(x, z), C_PROPS)
    parent(cyl(e.name + '_seat', 0.2, 0.2, 0.07, P['red'], (0, 0, 0.46), C_PROPS, 18), e)
    for dx, dz in ((0.12, 0.12), (-0.12, 0.12), (0.12, -0.12), (-0.12, -0.12)):
        # three.js leg rotation (dz*0.6, 0, -dx*0.6) about game X / Z -> Blender X (= game X) and Y (= -game Z)
        parent(cyl(e.name + '_leg', 0.025, 0.03, 0.44, P['redDk'], (dx, -dz, 0.22), C_PROPS, 6, rot=(dz * 0.6, dx * 0.6, 0)), e)
def p_cone(x, z):
    e = empty(pname('Cone'), G(x, z), C_PROPS)
    parent(rbox(e.name + '_base', 0.42, 0.06, 0.42, P['orange'], (0, 0, 0), C_PROPS, 0.02), e)
    parent(cyl(e.name + '_body', 0.05, 0.17, 0.62, P['orange'], (0, 0, 0.37), C_PROPS, 18), e)
    parent(cyl(e.name + '_band', 0.1, 0.13, 0.12, P['white'], (0, 0, 0.42), C_PROPS, 18), e)
def p_plant(x, z, s):
    e = empty(pname('Plant'), G(x, z), C_PROPS); e.scale = (s, s, s)
    parent(cyl(e.name + '_pot', 0.28, 0.22, 0.5, 0xd28c6a, (0, 0, 0.25), C_PROPS, 18), e)
    for dx, y, dz, r in ((0, 0.82, 0, 0.36), (0.17, 0.7, 0.1, 0.25), (-0.16, 0.72, -0.06, 0.26)):
        parent(sph(e.name + '_leaf', P['leaf'], (dx, -dz, y), (r, r, r * 0.9), C_PROPS, 14), e)
def p_table(x, z):
    e = empty(pname('Table'), G(x, z), C_PROPS)
    parent(cyl(e.name + '_top', 0.55, 0.55, 0.07, P['wood'], (0, 0, 0.76), C_PROPS, 26), e)
    parent(cyl(e.name + '_leg', 0.06, 0.06, 0.72, P['dark'], (0, 0, 0.37), C_PROPS, 10), e)
    parent(cyl(e.name + '_foot', 0.26, 0.3, 0.05, P['dark'], (0, 0, 0.025), C_PROPS, 18), e)

p_table(3.3, -21)
for x, z in ((2.4, -20.6), (4.1, -21.5), (3.0, -22.0)): p_chair(x, z)
for t_, x, z in (('crate', 3.9, -12.4), ('crate', 3.8, -13.1), ('bucket', 4.1, -13.8), ('bin', -4.2, -19.6), ('crate', -4.3, -14.2),
                 ('crate', -4.4, -15.0), ('bin', -9.5, -23.2), ('bin', -9.8, -25.8), ('crate', -10.0, -24.4), ('crate', -8.6, -26.0),
                 ('bucket', -8.4, -23.0), ('crate', 4.4, -27.0)):
    ry = rnd() * 0.4 - 0.2
    {'crate': p_crate, 'bin': p_bin, 'bucket': p_bucket}[t_](x, z, ry)
for x, z in ((3.2, -20.9), (3.45, -21.15), (-4.3, -20.4), (-4.3, -21.2), (-4.4, -21.9)): p_bottle(x, z)
p_cone(-2.9, -22.6); p_cone(-2.4, -23.1)
p_plant(-6.9, -17.9, 1.1); p_plant(6.9, -24.6, 1.2); p_plant(-8.3, -26.2, 0.9)

# puddles (K.puddle): organic outline from three sine lobes, flat calm pale blue
def puddle(x, z, rx, rz, sd, n):
    bm = bmesh.new(); vs = []
    for i in range(64):
        a = i / 64 * math.pi * 2
        r = 1 + 0.16 * math.sin(a * 2 + sd) + 0.09 * math.sin(a * 3 + sd * 2.3) + 0.05 * math.sin(a * 5 + sd * 4.1)
        # three.js shape in XY then rotateX(-90): shape y -> -game z -> +blender y
        vs.append(bm.verts.new((math.cos(a) * r * rx, math.sin(a) * r * rz, 0)))
    bm.faces.new(vs)
    ob = mesh_obj('Puddle_%d' % n, bm, kmat(0x96bee6, 0.85), C_ROAD); ob.location = G(x, z, 0.009)
for n, (x, z, rx, rz, sd) in enumerate(((1.6, -19.2, 2.2, 1.4, 1.3), (2.2, -26.5, 1.4, 1.1, 2.7), (-9.2, -24.8, 0.9, 0.8, 4.1))):
    puddle(x, z, rx, rz, sd, n)

# ================================================================ the detailed market corner GLB, placed 5 times (kitslice.js lines 50-53)
bpy.ops.import_scene.gltf(filepath=CORNER_GLB)
src = [o for o in bpy.context.selected_objects]
corner = bpy.data.objects['Corner']
for o in src:
    for c in o.users_collection: c.objects.unlink(o)
    C_CORNER.objects.link(o)
PLACES = [('Corner_End', 0.6, -27.6, -math.pi / 2), ('Corner_L1', -5.4, -8.0, 0.0), ('Corner_L2', -5.4, -17.2, 0.0),
          ('Corner_R1', 5.4, -9.4, math.pi), ('Corner_R2', 5.4, -18.6, math.pi)]
for k, (nm, x, z, ry) in enumerate(PLACES):
    if k == 0:
        root = corner; root.name = nm
    else:
        root = corner.copy(); root.name = nm; C_CORNER.objects.link(root)
        for ch in [o for o in src if o.parent == corner]:
            d = ch.copy(); C_CORNER.objects.link(d); d.parent = root          # linked duplicate (shared mesh)
            d.name = nm + '_' + ch.name.split('.')[0]
    root.rotation_mode = 'XYZ'; root.location = G(x, z); root.rotation_euler = (0, 0, ry)
for ch in [o for o in src if o.parent == corner]: ch.name = 'Corner_End_' + ch.name.split('.')[0]

# ================================================================ the player sumo
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.import_scene.gltf(filepath=SUMO_GLB)
imp = list(bpy.context.selected_objects)
for o in imp:
    for c in o.users_collection: c.objects.unlink(o)
    C_CHAR.objects.link(o)
for o in imp:   # a stray 80-tri helper sphere without material (not visible in the game)
    if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
rig = next(o for o in C_CHAR.objects if o.type == 'ARMATURE')
f = -math.pi / 2 + 1.1
hero = empty('SUMO_Player', G(0, -17.5), C_CHAR, -f + math.pi / 2); hero.scale = (1.12,) * 3
for o in list(C_CHAR.objects):
    if o.parent is None and o != hero: o.parent = hero
act = bpy.data.actions.get('stance_SumoRig') or next(a for a in bpy.data.actions if a.name.startswith('stance'))
rig.animation_data_create(); rig.animation_data.action = act
scn.frame_start = scn.frame_end = scn.frame_current = int(act.frame_range[0])

# ================================================================ light (K.light): sun at player + (-9, 16, +7) aimed at the player, hemisphere 0.5
PL = G(0, -17.5)
sd = bpy.data.lights.new('Sun', 'SUN'); sd.color = lin(0xfff3e4); sd.energy = 0.72 * math.pi; sd.angle = math.radians(2.0)
sun = link(bpy.data.objects.new('Sun', sd), C_LIGHT)
sun.location = PL + G(-9, 7, 16)
sun.rotation_euler = (PL - sun.location).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new('World_Game'); scn.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); mr = nt.nodes.new('ShaderNodeMapRange')
mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
mix.inputs['A'].default_value = (*lin(0xc4b8aa), 1); mix.inputs['B'].default_value = (*lin(0xe6eef8), 1)
hemi = nt.nodes.new('ShaderNodeBackground'); hemi.inputs['Strength'].default_value = 0.5
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Color'].default_value = (*lin(0xcfe0ee), 1); bg.inputs['Strength'].default_value = 1.0
lp = nt.nodes.new('ShaderNodeLightPath'); ms = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes.new('ShaderNodeOutputWorld')
L = nt.links.new
L(tc.outputs['Generated'], sep.inputs[0]); L(sep.outputs['Z'], mr.inputs['Value']); L(mr.outputs['Result'], mix.inputs['Factor'])
L(mix.outputs['Result'], hemi.inputs['Color']); L(hemi.outputs[0], ms.inputs[1]); L(bg.outputs[0], ms.inputs[2])
L(lp.outputs['Is Camera Ray'], ms.inputs['Fac']); L(ms.outputs[0], out.inputs['Surface'])

# ================================================================ the game camera (campaign.js: dist 15, camT = player + (0.65x, 0, -2.6), lookAt camT.y 0.6)
dist = 15.0; px, pz = 0.0, -17.5
camT = (px * 0.65, pz - 2.6)
cd = bpy.data.cameras.new('GameCam'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(38); cd.clip_start = 0.1; cd.clip_end = 220
cam = link(bpy.data.objects.new('CAM_Game_Original', cd), C_CAM)
cam.location = G(camT[0], camT[1] + dist * 0.77, dist * 0.64)
tgt = G(camT[0], camT[1], 0.6)
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.camera = cam

# ================================================================ render settings: game-like (no tone mapping, Lambert-ish)
r = scn.render; r.engine = 'BLENDER_EEVEE_NEXT'; r.resolution_x, r.resolution_y = 1280, 720; r.resolution_percentage = 100
scn.view_settings.view_transform = 'Standard'; scn.view_settings.look = 'None'
scn.eevee.taa_render_samples = 32; scn.eevee.use_shadows = True; scn.eevee.shadow_resolution_scale = 1.0
r.film_transparent = False
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/segment_original.blend')
print('saved', OUT + '/segment_original.blend')
if not NORENDER:
    r.filepath = OUT + '/original_gamecam.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', r.filepath)
