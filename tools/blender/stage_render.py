# Look-development render of the whole boss stage in full 3D: the modelled dohyo, two rigged sumo v2 in their
# stance, the gyoji, one warm spotlight in a black void, seen from the game camera. Not game data.
#   python tools/blender/stage_render.py <dir with dohyo.glb, sumo2_stance.glb, sumo2_red.glb, gyoji.glb> <out.png> [wide]
import bpy, math, sys, os
from mathutils import Vector
ARGS = [a for a in sys.argv if a != 'wide']; D, out = ARGS[-2], ARGS[-1]
WIDE = 'wide' in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(D, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots

load('dohyo.glb')
stance = None
def sumo(f, pos, face, scale=1.65):
    global stance
    new, roots = load(f)
    rig = next((o for o in new if o.type == 'ARMATURE'), None)
    if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
    elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
    for r in roots:
        r.location = (pos[0], pos[1], 0); r.scale = (scale,) * 3
        r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))
# game ground is x/z; blender here x/y with the camera on -Y. Two sumos squaring up, hands about to lock.
A, B = (-1.0, -0.15), (1.0, 0.15)
sumo('sumo2_stance.glb', A, B)
sumo('sumo2_red.glb', B, A)
_, gr = load('gyoji.glb')
for r in gr: r.location = (0.4, 5.0, 0); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
scn.frame_set(1)

# light: one warm spot straight down, nearly nothing else
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
spot = bpy.data.objects.new('Spot', bpy.data.lights.new('Spot', 'SPOT')); scn.collection.objects.link(spot)
spot.data.energy = 9000; spot.data.color = (1.0, 0.86, 0.7); spot.data.spot_size = math.radians(70); spot.data.spot_blend = 0.6
spot.data.shadow_soft_size = 1.2; spot.location = (0.5, -1.0, 16); spot.rotation_euler = (math.radians(4), 0, 0)
rim = bpy.data.objects.new('Rim', bpy.data.lights.new('Rim', 'AREA')); scn.collection.objects.link(rim)
rim.data.energy = 600; rim.data.color = (0.6, 0.7, 1.0); rim.data.size = 6; rim.location = (0, 12, 6)
rim.rotation_euler = (Vector((0, 0, 0.5)) - rim.location).to_track_quat('-Z', 'Y').to_euler()

cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
el = math.radians(50); dist = 21 if WIDE else 17
cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34); cam.data.sensor_fit = 'VERTICAL'
cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = 48; scn.cycles.use_denoising = True
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.render.filepath = out; bpy.ops.render.render(write_still=True)
