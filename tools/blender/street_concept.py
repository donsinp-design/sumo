# Look-development render: one market street in the target art style (soft, chunky, stylised, warm dawn sun,
# real soft shadows), with the new sumo. Not game data: a picture to agree the look before rebuilding the map.
#   python tools/blender/street_concept.py <sumo.glb> <out.png>
import bpy, math, sys, random
from mathutils import Vector
random.seed(7)
sumo_glb, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
MATS = {}
def mat(h, rough=0.75):
    if h in MATS: return MATS[h]
    m = bpy.data.materials.new(h); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(h), 1); b.inputs['Roughness'].default_value = rough; MATS[h] = m; return m
def stripes(a, b, n=10):  # awning canvas: soft-edged stripes
    m = bpy.data.materials.new('stripe' + a + b); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_profile = 'SIN'; wv.inputs['Scale'].default_value = n
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.48; ramp.color_ramp.elements[1].position = 0.52
    ramp.color_ramp.elements[0].color = (*srgb(a), 1); ramp.color_ramp.elements[1].color = (*srgb(b), 1)
    nt.links.new(tc.outputs['Generated'], wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.85; return m
def ground_mat(base, dark):  # a painted floor: broad soft tone variation, no tiling pattern
    m = bpy.data.materials.new('ground'); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.35; nz.inputs['Detail'].default_value = 3
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*srgb(dark), 1); ramp.color_ramp.elements[1].color = (*srgb(base), 1)
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.65
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.9; return m

def rbox(x, y, z, sx, sy, sz, m, bev=0.04, rz=0):  # a box with soft rounded edges
    bpy.ops.mesh.primitive_cube_add(location=(x, y, z)); o = bpy.context.object; o.scale = (sx / 2, sy / 2, sz / 2); o.rotation_euler.z = rz
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if bev: bv = o.modifiers.new('b', 'BEVEL'); bv.width = bev; bv.segments = 4; o.modifiers.new('w', 'WEIGHTED_NORMAL')
    o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o
def cyl(x, y, z, r, h, m, verts=24, bev=0.02):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=(x, y, z)); o = bpy.context.object
    if bev: bv = o.modifiers.new('b', 'BEVEL'); bv.width = bev; bv.segments = 3
    o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o
def blob(x, y, z, sx, sy, sz, m, rz=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=(x, y, z)); o = bpy.context.object; o.scale = (sx, sy, sz); o.rotation_euler.z = rz
    o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

# ---------------------------------------------------------------- the street
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); g = bpy.context.object; g.scale = (30, 40, 1); g.data.materials.append(ground_mat('c9b79a', 'b3a283'))
for s in (-1, 1):  # building fronts, chunky and softly bevelled, warm plaster and wood
    for i, (w, col, h) in enumerate([(4.2, 'e8d9bd', 4.6), (3.6, 'd99c7a', 5.4), (4.4, 'efe3cc', 4.2), (3.8, 'c9d4c2', 5.0), (4.0, 'e2c79c', 4.8)]):
        y = -9 + i * 4.3
        rbox(s * 8.6, y, h / 2, 2.6, w - 0.15, h, mat(col), 0.08)
        rbox(s * 7.28, y, 1.25, 0.08, w * 0.7, 2.2, mat('8a7a6a'), 0.02)                    # the shutter / doorway
        rbox(s * 7.25, y, 2.9, 0.12, w * 0.75, 0.55, mat(['c8342c', '2f5fa8', '2e8a5e', 'e0a43a', '6a4a8a'][i % 5]), 0.04)  # shop sign board
        rbox(s * 7.3, y, h + 0.05, 0.4, w - 0.1, 0.18, mat('7a5a48'), 0.03)                 # roof edge
# ---------------------------------------------------------------- stalls: counter, ice bed, fish, striped awning on poles
FISH = [mat('a9b8c8', 0.35), mat('d7826a', 0.4), mat('8fa0b4', 0.35)]
def stall(x, y, sd, a, b):
    rbox(x, y, 0.45, 1.7, 3.2, 0.9, mat('8a5a3a'), 0.05)                    # wooden counter
    rbox(x, y, 0.95, 1.6, 3.0, 0.14, mat('dff1f7', 0.3), 0.05)               # ice bed
    for i in range(9):
        for j in (-1, 0, 1):
            f = blob(x + j * 0.42, y - 1.25 + i * 0.31, 1.07, 0.17, 0.06, 0.05, FISH[(i + j) % 3], rz=math.pi / 2 + random.uniform(-0.2, 0.2))
    for i in (-1, 1): cyl(x - sd * 1.6, y + i * 1.55, 1.4, 0.04, 2.8, mat('5a5a62'), 8, 0)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x - sd * 0.8, y, 2.75)); aw = bpy.context.object; aw.scale = (1.7, 3.3, 1); aw.rotation_euler.y = -sd * 0.3
    bpy.ops.object.transform_apply(scale=True, rotation=True); so = aw.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.04; aw.data.materials.append(stripes(a, b, 9))
    bv = aw.modifiers.new('b', 'BEVEL'); bv.width = 0.02; bv.segments = 2
for (x, y, sd, a, b) in [(-5.4, -4.5, -1, 'd8423a', 'f4ead8'), (-5.4, 1.5, -1, 'e8b43a', '3a3a48'), (5.4, -2.0, 1, '3a6ac8', 'f4ead8'), (5.4, 4.0, 1, '3a9a6a', 'f4ead8')]:
    stall(x, y, sd, a, b)
# ---------------------------------------------------------------- props
for (x, y, r) in [(-3.2, -6.5, 0.2), (-2.7, -7.1, -0.3), (3.5, 6.5, 0.1), (-3.0, 4.6, 0.6)]:
    c = rbox(x, y, 0.27, 0.6, 0.45, 0.54, mat('c08a52'), 0.04, r); rbox(x, y, 0.55, 0.62, 0.47, 0.04, mat('a8743e'), 0.01, r)
for (x, y) in [(3.0, -6.0), (3.4, -5.4)]: cyl(x, y, 0.42, 0.28, 0.84, mat('2f6ad8', 0.5), 28, 0.04)
for (x, y) in [(2.2, 1.0), (3.2, 1.6), (2.6, 2.4)]: cyl(x, y, 0.22, 0.17, 0.44, mat('d83a3a', 0.5), 20, 0.03)
cyl(2.7, 1.7, 0.36, 0.55, 0.06, mat('8a5a3a'), 32, 0.02); cyl(2.7, 1.7, 0.18, 0.06, 0.36, mat('5a3a2a'), 10, 0)
for (x, y) in [(-1.6, 6.5), (1.0, -8.0)]: cyl(x, y, 0.2, 0.22, 0.4, mat('f0c43a', 0.5), 20, 0.03)
blob(-0.5, 3.6, 0.12, 0.65, 0.22, 0.14, mat('5a7090', 0.35), 0.4)                                # a big tuna on the ground
for (x, y, sx) in [(0.8, -3.0, 1.0), (-1.5, -0.5, 1.4)]: blob(x, y, 0.004, 0.6 * sx, 0.45 * sx, 0.004, mat('9a8a74', 0.15))   # wet patches
for (x, y) in [(-6.6, -8.6), (6.6, 8.2), (-6.6, 6.2), (6.6, -6.8)]:   # potted shrubs: the greens of the palette
    cyl(x, y, 0.3, 0.32, 0.6, mat('b8644a'), 20, 0.04)
    for k in range(5): blob(x + random.uniform(-0.2, 0.2), y + random.uniform(-0.2, 0.2), 0.85 + random.uniform(0, 0.4), 0.32, 0.32, 0.28, mat(random.choice(['5a9a4a', '4a8a42', '6aaa52'])))
# ---------------------------------------------------------------- people: market workers in the same chunky style (placeholder shapes)
def worker(x, y, coat, rz):
    blob(x, y, 0.95, 0.24, 0.2, 0.42, mat(coat), rz)                       # body
    blob(x, y - 0.0, 1.55, 0.16, 0.16, 0.17, mat('f0c09a', 0.6))             # head
    blob(x, y + 0.01, 1.63, 0.165, 0.165, 0.11, mat('2a2a30', 0.5))          # hair
    for s in (-1, 1): cyl(x + s * 0.11, y, 0.3, 0.085, 0.6, mat('2a2e3a'), 12, 0.02)   # legs, rubber boots
    rbox(x, y - 0.17, 0.95, 0.36, 0.06, 0.6, mat('f2efe8'), 0.03, rz)        # apron
for (x, y, c, r) in [(-1.2, -4.0, '3a62b8', 0.3), (1.6, -5.2, '3a62b8', -0.4), (0.5, 0.8, 'c8423a', 0.1), (-2.1, 2.0, '3a8a62', -0.2)]: worker(x, y, c, r)
# ---------------------------------------------------------------- the sumo
bpy.ops.import_scene.gltf(filepath=sumo_glb)
for o in bpy.context.selected_objects:
    if o.type == 'MESH': o.location = (0.3, -1.8, 0); o.scale = (1.15, 1.15, 1.15); o.rotation_euler.z = math.pi * 0.9
# ---------------------------------------------------------------- light: a warm low morning sun, a bright soft sky
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('a9c6e8'), 1); bg.inputs['Strength'].default_value = 1.1
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 4.2; sun.data.color = srgb('fff0d8'); sun.data.angle = math.radians(4); sun.rotation_euler = (math.radians(42), 0, math.radians(-38))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam; cam.data.lens = 32
cam.location = (0, -15.5, 15.5); cam.rotation_euler = (Vector((0, -1.0, 0.6)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.render.engine = 'CYCLES'; scn.cycles.samples = 40; scn.cycles.device = 'CPU'; scn.cycles.use_denoising = True
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Punchy'
scn.render.filepath = out; bpy.ops.render.render(write_still=True)
