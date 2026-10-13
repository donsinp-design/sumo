# The gacha machine as its own small glb, built with the bathhouse kit's palette, master material and module builder
# (the top of bathhouse_kit.py, up to the floors), so it matches the kit exactly.  <bl python> tools/blender/gacha_kit.py
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
src = open(os.path.join(HERE, 'bathhouse_kit.py')).read()
head = src[:src.index('def build_floors():')]
os.environ.setdefault('KIT_SP', os.environ.get('TMPDIR', '/tmp').rstrip('/') + '/gachakit_sp')
g = {'__file__': os.path.join(HERE, 'bathhouse_kit.py'), '__name__': 'kit'}
exec(compile(head, 'bathhouse_kit_head', 'exec'), g)
GB, obj_from, bpy = g['GB'], g['obj_from'], g['bpy']
if 'ENV_PROTO' not in g['CN']: g['CN']['ENV_PROTO'] = g['coll']('ENV_PROTO')
m = GB()
# a single Japanese capsule-toy machine (gachapon): white, on a flared stand; a rounded clear window bulging out
# over a printed card and a pile of capsules; below it the turn dial, the coin slot and the dark window the
# capsule drops into. (Front is +z.)
m.gbox(-0.37, 0.37, -0.3, 0.38, 0.0, 0.07, 'snow', bev=0.03)                  # the stand's foot
m.gbox(-0.32, 0.32, -0.27, 0.3, 0.07, 0.2, 'snow', bev=0.04)
m.gbox(-0.3, 0.3, -0.26, 0.26, 0.2, 0.46, 'snow', bev=0.04)
m.gbox(-0.31, 0.31, -0.27, 0.25, 0.46, 0.98, 'snow', bev=0.035)               # the lower cabinet
m.gcyl(-0.13, 0.25, 0.7, 0.115, 0.016, 'offwhite', seg=24, bev=0.005, axis='Y')    # dial plate
m.gcyl(-0.13, 0.265, 0.7, 0.07, 0.03, 'snow', seg=20, bev=0.01, axis='Y')          # the dial
m.gbox(-0.215, -0.045, 0.27, 0.31, 0.68, 0.72, 'snow', bev=0.015)             # its handle
m.gbox(-0.07, -0.02, 0.25, 0.262, 0.77, 0.82, 'red', bev=0.004)               # (the turn arrow)
m.gbox(-0.17, -0.09, 0.25, 0.26, 0.86, 0.9, 'dark', bev=0.004)                # coin slot
m.gcyl(-0.13, 0.252, 0.55, 0.022, 0.01, 'dark', seg=12, axis='Y')             # (the return button)
m.gbox(0.04, 0.24, 0.245, 0.262, 0.55, 0.8, 'dark', bev=0.03)                  # the capsule window
m.gbox(0.07, 0.21, 0.262, 0.266, 0.69, 0.76, 'yellow', bev=0.004)              # (its sticker)
m.gbox(0.06, 0.2, 0.25, 0.26, 0.86, 0.91, 'yellow', bev=0.004)                 # price label
m.gbox(-0.31, 0.31, -0.27, -0.08, 0.98, 1.44, 'snow', bev=0.03)                # behind the window
m.gbox(-0.26, 0.26, -0.09, -0.075, 1.0, 1.42, 'blue', bev=0.005)               # the printed card
m.gbox(-0.24, 0.24, -0.077, -0.072, 1.36, 1.41, 'snow')                        # (its title strip)
for k, (cx, cy) in enumerate([(-0.17, 1.27), (-0.07, 1.27), (0.03, 1.27), (-0.17, 1.17), (-0.07, 1.17)]):
    m.gbox(cx - 0.035, cx + 0.035, -0.074, -0.068, cy - 0.03, cy + 0.03, 'snow')   # little toy pictures
m.gbox(0.06, 0.2, -0.074, -0.066, 1.05, 1.22, 'pink', bev=0.01)                 # the big one
CAPS = ['pink', 'yellow', 'green', 'blue', 'orange', 'snow', 'red']
for k in range(14):                                                             # capsules piled up, mostly at the right
    px = 0.26 - 0.075 * (k % 5) - (0.04 if k >= 5 else 0); pz = -0.02 + 0.07 * ((k * 3) % 4); py = 1.04 + 0.075 * (k // 5) + 0.02 * ((k * 7) % 3)
    if k >= 10: px = 0.24 - 0.07 * (k - 10); py = 1.22
    m.gico(px, pz, py, 0.05, CAPS[k % len(CAPS)], sub=2)
for sd in (-1, 1): m.gcyl(sd * 0.295, -0.02, 1.21, 0.235, 0.03, 'snow', seg=28, bev=0.008, axis='X')   # the window's white side rims
m.gbox(-0.32, 0.32, -0.28, 0.17, 1.42, 1.54, 'snow', bev=0.05)                  # the rounded top
m.gcyl(0, 0.17, 1.48, 0.022, 0.012, 'chrome', seg=12, axis='Y')                 # (keyhole)
# the clear window goes last: a bulge (half a drum) that comes out as the see-through part
m.gcyl(0, -0.02, 1.21, 0.225, 0.56, 'glass_lt', seg=28, axis='X')
o = obj_from(m, 'ITEM_GACHA', 'ENV_PROTO')
for x in bpy.context.scene.objects: x.select_set(x.name == 'ITEM_GACHA')
out = os.path.join(HERE, '..', '..', 'public', 'assets', 'models', 'gacha_kit.glb')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True, export_yup=True)
print('WROTE', out)
