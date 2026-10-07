# The soft sumo made game-ready for the flat look: split vertices welded, the skin Taubin-smoothed (rounder, simpler
# shapes without shrinking), and everything sitting on the skin (mawashi, hair, eyes) carried along with it so the
# belt keeps hugging the body. Clips (stance, push, charge) are kept.
#   python tools/blender/sumo_game.py <sumo_soft_poses.glb> <out.glb> [preview.png]
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
args = [a for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else sys.argv[1:]
SRC, OUT = args[0], args[1]; PREV = args[2] if len(args) > 2 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
scn = bpy.context.scene
hero = bpy.data.objects['Sumo']; rig = next(o for o in scn.objects if o.type == 'ARMATURE')
me = hero.data

# ---- weld the glTF seam splits (the mesh comes apart if smoothed otherwise)
bm = bmesh.new(); bm.from_mesh(me)
n0 = len(bm.verts); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005); bm.to_mesh(me); bm.free()
print('welded', n0, '->', len(me.vertices))

# ---- which vertices are skin
SKIN = [i for i, m in enumerate(me.materials) if m and m.name.startswith('Skin')][0]
nv = len(me.vertices)
is_skin = np.zeros(nv, bool)
for p in me.polygons:
    if p.material_index == SKIN: is_skin[list(p.vertices)] = True
for p in me.polygons:                         # a vertex shared with cloth/hair stays put (keeps the seams closed)
    if p.material_index != SKIN: is_skin[list(p.vertices)] = False
co = np.empty(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
nb = [[] for _ in range(nv)]
for e in me.edges:
    a, b = e.vertices
    nb[a].append(b); nb[b].append(a)
idx = np.where(is_skin)[0]

# ---- Taubin smoothing of the skin: removes lumps and creases, keeps the volume
def lap(P):
    L = np.zeros_like(P)
    for i in idx:
        n = nb[i]
        if n: L[i] = P[n].mean(0) - P[i]
    return L
P = co.copy()
for _ in range(int(os.environ.get('SMOOTH_IT', '14'))):
    P[idx] += 0.5 * lap(P)[idx]
    P[idx] += -0.53 * lap(P)[idx]
disp = P - co
print('skin moved: mean %.4f max %.4f' % (np.linalg.norm(disp[idx], axis=1).mean(), np.linalg.norm(disp[idx], axis=1).max()))

# ---- everything else follows the nearest skin, so the belt, hair and eyes stay on the body
kd = KDTree(len(idx))
for k, i in enumerate(idx): kd.insert(Vector(co[i]), int(i))
kd.balance()
for i in np.where(~is_skin)[0]:
    acc, ws = np.zeros(3), 0.0
    for _, j, d in kd.find_n(Vector(co[i]), 6):
        w = 1.0 / (d + 0.01) ** 2; acc += disp[j] * w; ws += w
    P[i] = co[i] + acc / ws
me.vertices.foreach_set('co', P.ravel()); me.update()

# ---- close any gap left between the belt and the skin: pull cloth inside-faces onto the skin surface
from mathutils.bvhtree import BVHTree
skin_bm = bmesh.new(); skin_bm.from_mesh(me)
skin_bm.faces.ensure_lookup_table()
bmesh.ops.delete(skin_bm, geom=[f for f in skin_bm.faces if f.material_index != SKIN], context='FACES_ONLY')
bvh = BVHTree.FromBMesh(skin_bm)
MAW = [i for i, m in enumerate(me.materials) if m and m.name.startswith('Mawashi')]
cloth = set()
for p in me.polygons:
    if p.material_index in MAW: cloth.update(p.vertices)
moved = 0
for i in cloth:
    v = me.vertices[i]; loc, nrm, _, d = bvh.find_nearest(v.co)
    if loc is None: continue
    off = (v.co - loc).dot(nrm)
    if 0.0 < off < 0.06 and (v.co - loc).length < 0.08:    # just outside the skin: snug it down (keep a hair of clearance)
        v.co = loc + nrm * min(off, 0.008); moved += 1
me.update(); print('cloth verts snugged', moved)
skin_bm.free()
for p in me.polygons: p.use_smooth = True
if hasattr(me, 'set_sharp_from_angle'): me.set_sharp_from_angle(angle=math.radians(180))

# ---- export with every clip
for o in scn.objects: o.select_set(o in (hero, rig))
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_skins=True, export_animations=True,
                          export_animation_mode='ACTIONS', export_apply=False, export_rest_position_armature=True, export_yup=True)
print('exported', OUT)

if PREV:   # quick check render: stance, flat-ish light, high three-quarter view
    act = next(a for a in bpy.data.actions if a.name.startswith('stance')); print('actions', [a.name for a in bpy.data.actions])
    rig.animation_data.action = act; scn.frame_set(1)
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.86, 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.2
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
    sun.data.energy = 2.5; sun.data.angle = math.radians(6); sun.rotation_euler = (math.radians(35), 0, math.radians(-30))
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    for nm, az in (('back', 200), ('front', 20)):
        a = math.radians(az); el = math.radians(48); dist = 4.6; tgt = Vector((0, 0, 0.8))
        cam.location = tgt + Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))) * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 50
        scn.render.engine = 'CYCLES'; scn.cycles.samples = 32; scn.cycles.use_denoising = True
        scn.render.resolution_x, scn.render.resolution_y = 700, 700; scn.view_settings.view_transform = 'Standard'
        scn.render.filepath = PREV.replace('.png', '_' + nm + '.png'); bpy.ops.render.render(write_still=True)
