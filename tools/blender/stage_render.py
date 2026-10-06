# Look-development render of the whole boss stage in full 3D: the modelled dohyo, two rigged sumo v2 in their
# stance, the gyoji, one warm spotlight in a black void, seen from the game camera. Not game data.
#   python tools/blender/stage_render.py <dir with dohyo.glb, sumo2_stance.glb, sumo2_red.glb, gyoji.glb> <out.png> [wide]
import bpy, math, sys, os
from mathutils import Vector
ARGS = [a for a in sys.argv if a not in ('wide', 'low')]; D, out = ARGS[-2], ARGS[-1]
WIDE = 'wide' in sys.argv; LOW = 'low' in sys.argv
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
RIGS = []
def sumo(f, pos, face, scale=1.65):
    global stance
    new, roots = load(f)
    rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
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

# ---------------------------------------------------------------- masks (the same designs as the game's)
from mathutils import Matrix
def mmat(name, hexc, rough=0.35):
    m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes['Principled BSDF']
    c = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]; c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    bs.inputs['Base Color'].default_value = (*c, 1); bs.inputs['Roughness'].default_value = rough; return m
def mask(kind, centre, fwd, up, k):
    fwd = (fwd - up * fwd.dot(up)).normalized(); right = fwd.cross(up).normalized()
    B = Matrix((right, fwd, up)).transposed().to_4x4(); B.translation = centre
    parts = []
    def put(o, loc, mat_):
        o.data.materials.append(mat_); bpy.ops.object.shade_smooth()
        o.matrix_world = B @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world; parts.append(o)
    def ell(loc, sc, mat_, half=False):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16); o = bpy.context.object
        if half:   # keep the front half: a shell that sits on the face
            import bmesh
            bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.05], context='VERTS'); bm.to_mesh(o.data); bm.free()
            sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.06
        o.scale = Vector(sc) * k; bpy.ops.object.transform_apply(scale=True); put(o, loc, mat_); return o
    def cone(loc, r, h, rot, mat_):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r * k, depth=h * k); o = bpy.context.object
        o.rotation_euler = rot; bpy.ops.object.transform_apply(rotation=True); put(o, loc, mat_)
    def strap(mat_):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.25 * k, minor_radius=0.03 * k); o = bpy.context.object
        o.rotation_euler = (0.25, 0, 0); bpy.ops.object.transform_apply(rotation=True); put(o, (0, -0.02, 0.02), mat_)
    INK = mmat('mInk', '141414', 0.5)
    if kind == 'oni':
        R_ = mmat('mOni', 'c8231d'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), R_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
            cone((sd * 0.11, 0.08, 0.2), 0.04, 0.18, (0, sd * 0.45, 0), mmat('mHorn', 'f2e6c8', 0.4))
        strap(R_)
    elif kind == 'hannya':
        W_ = mmat('mHannya', 'eae2c8'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
            cone((sd * 0.11, 0.06, 0.22), 0.04, 0.22, (0, sd * 0.5, 0), mmat('mHornH', 'd8c890', 0.4))
        ell((0, 0.25, -0.12), (0.07, 0.02, 0.018), mmat('mMouth', '7a1414'))
        strap(W_)
    elif kind == 'kitsune':
        W_ = mmat('mKitsune', 'f6f2ea'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.03), (0.045, 0.015, 0.012), mmat('mRed', 'd8262e'))
            cone((sd * 0.1, 0.06, 0.2), 0.055, 0.14, (0, sd * 0.3, 0), W_)
        cone((0, 0.3, -0.06), 0.06, 0.14, (-math.pi / 2, 0, 0), W_)
        strap(mmat('mRedS', 'd8262e'))
    return parts

def head_frame(rig, roots):
    pb = rig.pose.bones['head']; M = rig.matrix_world @ pb.matrix
    up = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    fwd = (roots[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    return M.translation + up * 0.11 * roots[0].scale[0], fwd, up
for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
    if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
mask('kitsune', Vector((0.4, 5.0, 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)

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
if LOW:   # a low three-quarter view from the front-right: faces, masks and the mound's height
    cam.location = (9.5, -8.5, 4.2); cam.data.angle_y = math.radians(30)
    cam.rotation_euler = (Vector((0, 0.8, 0.4)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = 48; scn.cycles.use_denoising = True
scn.render.resolution_x, scn.render.resolution_y = 1280, 720
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.render.filepath = out; bpy.ops.render.render(write_still=True)
