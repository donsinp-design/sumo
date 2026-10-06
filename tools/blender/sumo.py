# Kumite campaign hero: a stylised sumo, built entirely by script (Blender 4.2, run headless).
#   python tools/blender/sumo.py  [out.glb] [preview_prefix]
# Chunky, soft, readable shapes in the spirit of modern stylised top-down games: a metaball body
# (one smooth skin over belly, chest, limbs), a simple friendly face, slicked hair with a topknot,
# a dark blue mawashi with sagari. Blender is Z-up with the front facing -Y; the glTF export
# converts to Y-up. Real scale: about 1.85 m.
import bpy, bmesh, math, sys
from mathutils import Vector

out = sys.argv[-2] if len(sys.argv) > 2 and sys.argv[-2].endswith('.glb') else '/tmp/sumo.glb'
prev = sys.argv[-1] if len(sys.argv) > 2 else '/tmp/sumo_prev'

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

def mat(name, rgb, rough=0.7):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    return m
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

SKIN, SKIN_D = mat('Skin', srgb('f0b48c'), 0.55), None
HAIR = mat('Hair', srgb('1c1a22'), 0.4)
BELT = mat('Mawashi', srgb('22336e'), 0.65)
INK = mat('Ink', srgb('1a1216'), 0.5)
WHITE = mat('White', srgb('f6f0e6'), 0.5)
CHEEK = mat('Cheek', srgb('e88f84'), 0.6)

# ---------------------------------------------------------------- body: overlapping volumes fused into one skin (voxel remesh)
parts = []
def ell(x, y, z, rx, ry, rz):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=18, location=(x, y, z)); o = bpy.context.object; o.scale = (rx, ry, rz); parts.append(o); return o
def limb(a, b, ra, rb):  # a tapered capsule from a to b
    a, b = Vector(a), Vector(b); d = b - a; L = d.length
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=ra, radius2=rb, depth=L, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); parts.append(o)
    ell(*a, ra, ra, ra); ell(*b, rb, rb, rb)
ell(0, -0.08, 0.97, 0.43, 0.42, 0.40)     # the belly: big and round, sitting forward
ell(0, -0.01, 1.28, 0.40, 0.31, 0.27)     # chest
ell(0, 0.08, 0.85, 0.37, 0.31, 0.26)      # seat
ell(0, 0.0, 1.47, 0.17, 0.16, 0.14)       # thick neck
for s_ in (-1, 1):
    ell(s_ * 0.36, 0.0, 1.38, 0.18, 0.17, 0.16)                                       # shoulders
    limb((s_ * 0.42, 0.0, 1.36), (s_ * 0.58, -0.03, 1.05), 0.135, 0.11)               # upper arm, a little out from the body
    limb((s_ * 0.58, -0.03, 1.05), (s_ * 0.62, -0.08, 0.80), 0.105, 0.085)            # forearm
    ell(s_ * 0.625, -0.09, 0.72, 0.075, 0.06, 0.085)                                  # hand
    limb((s_ * 0.22, 0.02, 0.82), (s_ * 0.28, 0.0, 0.42), 0.25, 0.18)                  # thigh
    limb((s_ * 0.28, 0.0, 0.42), (s_ * 0.29, 0.0, 0.12), 0.17, 0.12)                   # calf
    ell(s_ * 0.29, -0.06, 0.05, 0.1, 0.16, 0.06)                                    # foot
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = 'Body'
bpy.ops.object.transform_apply(scale=True, rotation=True)
r = body.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.014
bpy.ops.object.modifier_apply(modifier='rm')
m = body.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); m.factor = 0.8; m.iterations = 12; m.smooth_type = 'LENGTH_WEIGHTED'
bpy.ops.object.modifier_apply(modifier='sm')
m = body.modifiers.new('sm2', 'SMOOTH'); m.factor = 0.5; m.iterations = 8
bpy.ops.object.modifier_apply(modifier='sm2')
d = body.modifiers.new('dec', 'DECIMATE'); d.ratio = 0.12
bpy.ops.object.modifier_apply(modifier='dec')
body.data.materials.append(SKIN)
bpy.ops.object.shade_smooth()

def add(obj, m_):
    obj.data.materials.append(m_); bpy.ops.object.shade_smooth(); return obj
def sphere(name, loc, scale, m_, seg=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc); o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True); return add(o, m_)

# ---------------------------------------------------------------- head and face
HZ = 1.70
head = sphere('Head', (0, -0.02, HZ), (0.175, 0.17, 0.185), SKIN, 32, 20)
sphere('Jowls', (0, -0.07, HZ - 0.08), (0.15, 0.11, 0.08), SKIN)                # a full lower face
for s in (-1, 1):
    sphere('Ear', (s * 0.172, 0.0, HZ - 0.01), (0.03, 0.045, 0.055), SKIN, 12, 8)
    sphere('Eye', (s * 0.062, -0.165, HZ + 0.015), (0.022, 0.012, 0.03), INK, 12, 8)                 # small calm eyes
    sphere('EyeHi', (s * 0.056, -0.176, HZ + 0.025), (0.007, 0.004, 0.008), WHITE, 8, 6)             # a glint
    bpy.ops.mesh.primitive_cube_add(location=(s * 0.066, -0.162, HZ + 0.07)); b = bpy.context.object; b.name = 'Brow'
    b.scale = (0.045, 0.012, 0.013); b.rotation_euler = (0, s * 0.18, 0); bpy.ops.object.transform_apply(scale=True, rotation=True); add(b, HAIR)
    sphere('Cheek', (s * 0.098, -0.152, HZ - 0.035), (0.032, 0.008, 0.02), CHEEK, 12, 8)
sphere('Nose', (0, -0.182, HZ - 0.01), (0.026, 0.02, 0.024), SKIN, 12, 8)
bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.006, location=(0, -0.168, HZ - 0.065), rotation=(math.pi / 2, 0, 0))
mouth = bpy.context.object; mouth.name = 'Mouth'; mouth.scale = (1, 0.5, 1)
bm = bmesh.new(); bm.from_mesh(mouth.data)                       # keep the lower half: a small smile
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.0], context='VERTS'); bm.to_mesh(mouth.data); bm.free()
bpy.ops.object.transform_apply(scale=True, rotation=True); add(mouth, INK)

# hair: slicked back close to the scalp, a folded topknot (chonmage) lying forward along the crown
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=18, location=(0, 0.01, HZ + 0.015)); cap = bpy.context.object; cap.name = 'Hair'
cap.scale = (0.183, 0.18, 0.18); bpy.ops.object.transform_apply(scale=True)
bm = bmesh.new(); bm.from_mesh(cap.data)                          # hairline: off the forehead, down at the back
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < (0.055 if v.co.y < -0.05 else -0.06 if v.co.y > 0.05 else 0.0)], context='VERTS')
bm.to_mesh(cap.data); bm.free(); add(cap, HAIR)
sphere('Knot', (0, -0.02, HZ + 0.205), (0.045, 0.11, 0.04), HAIR, 16, 10)       # the topknot
sphere('KnotBase', (0, 0.07, HZ + 0.185), (0.05, 0.05, 0.04), HAIR, 12, 8)
bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.01, location=(0, 0.035, HZ + 0.198), rotation=(math.pi / 2, 0, 0))
add(bpy.context.object, WHITE); bpy.context.object.name = 'KnotTie'

# ---------------------------------------------------------------- mawashi: measured off the body at the waist
def ring_at(z):  # widest extent of the body around height z
    pts = [body.matrix_world @ v.co for v in body.data.vertices if abs(v.co.z - z) < 0.03 and abs(v.co.x) < 0.45]  # the torso only, not the hands
    return max(abs(p.x) for p in pts), max(p.y for p in pts), min(p.y for p in pts)
rx, ry_back, ry_front = ring_at(0.82)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.17, location=(0, (ry_back + ry_front) / 2, 0.83))
belt = bpy.context.object; belt.name = 'Mawashi'
belt.scale = (rx + 0.02, (ry_back - ry_front) / 2 + 0.02, 1); bpy.ops.object.transform_apply(scale=True)
bm = bmesh.new(); bm.from_mesh(belt.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9], context='FACES_ONLY'); bm.to_mesh(belt.data); bm.free()
# hug the body: subdivide the band, pull every point onto the skin, then stand it just proud of it
bpy.context.view_layer.objects.active = belt
sub = belt.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.subdivision_type = 'SIMPLE'; bpy.ops.object.modifier_apply(modifier='sub')
sw = belt.modifiers.new('sw', 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.012; bpy.ops.object.modifier_apply(modifier='sw')
sol = belt.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.035; sol.offset = 1
bev = belt.modifiers.new('bev', 'BEVEL'); bev.width = 0.012; bev.segments = 3
bpy.context.view_layer.objects.active = belt; bpy.ops.object.modifier_apply(modifier='sol'); bpy.ops.object.modifier_apply(modifier='bev'); add(belt, BELT)
# the front: a folded panel down over the groin, and the sagari (stiff cords) hanging off the belt
bpy.ops.mesh.primitive_cube_add(location=(0, ry_front - 0.03, 0.68)); fp = bpy.context.object; fp.name = 'MawashiFront'
fp.scale = (0.11, 0.025, 0.12); bpy.ops.object.transform_apply(scale=True)
b2 = fp.modifiers.new('bev', 'BEVEL'); b2.width = 0.02; b2.segments = 3; bpy.context.view_layer.objects.active = fp; bpy.ops.object.modifier_apply(modifier='bev'); add(fp, BELT)
for i in range(11):
    a = -0.75 + i * 0.15
    x, y = math.sin(a) * (rx + 0.03), ry_front - 0.02 + (1 - math.cos(a)) * 0.25
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.009, depth=0.2, location=(x, y, 0.66)); add(bpy.context.object, BELT); bpy.context.object.name = 'Sagari'
# the back knot
sphere('MawashiKnot', (0, ry_back + 0.02, 0.86), (0.08, 0.05, 0.07), BELT, 16, 10)

# ---------------------------------------------------------------- one object, origin at the feet, export
for o in scn.objects: o.select_set(o.type == 'MESH')
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
hero = bpy.context.object; hero.name = 'Sumo'
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
tris = sum(len(p.vertices) - 2 for p in hero.data.polygons)
print('triangles', tris)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True)

# ---------------------------------------------------------------- preview renders (Cycles, CPU): soft sky + a warm sun
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (*srgb('b8c8dc'), 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 3.2; sun.data.color = srgb('ffe8c8'); sun.data.angle = 0.25; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
bpy.ops.mesh.primitive_plane_add(size=8); gnd = bpy.context.object; gnd.data.materials.append(mat('Ground', srgb('d8c8a8'), 0.9))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam; cam.data.lens = 50
scn.render.engine = 'CYCLES'; scn.cycles.samples = 48; scn.cycles.device = 'CPU'
scn.render.resolution_x = scn.render.resolution_y = 640; scn.view_settings.view_transform = 'Standard'
def shoot(name, pos, look=(0, 0, 1.0)):
    cam.location = pos; cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = prev + '_' + name + '.png'; bpy.ops.render.render(write_still=True)
shoot('front', (1.6, -4.2, 1.6))
shoot('back', (-1.4, 4.2, 1.7))
shoot('face', (0.5, -1.6, 1.75), (0, 0, 1.62))
shoot('top', (2.5, -6.5, 7.5), (0, 0, 0.8))
