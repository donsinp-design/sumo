# The boss's stage: the big bath, drained, with a dohyo standing on its tiled bottom. Built with the bathhouse kit's
# palette, master material and module builder (the top of bathhouse_kit.py, up to the floors), so it matches the level.
#   <bl python> tools/blender/stage_bathpit_kit.py
# Output: public/assets/models/bathpit_kit.glb. Ring centre at the origin, fighting surface at y = 0 (game coords).
# Roots the game animates: WATER (the bath water, lowered as it drains) and WHIRL (the whirlpool over the drain).
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
src = open(os.path.join(HERE, 'bathhouse_kit.py')).read()
head = src[:src.index('def build_floors():')]
os.environ.setdefault('KIT_SP', os.environ.get('TMPDIR', '/tmp').rstrip('/') + '/bathpit_sp')
g = {'__file__': os.path.join(HERE, 'bathhouse_kit.py'), '__name__': 'kit'}
exec(compile(head, 'bathhouse_kit_head', 'exec'), g)
GB, MB, obj_from, place, bpy, swuv, U, Rz = g['GB'], g['MB'], g['obj_from'], g['place'], g['bpy'], g['swuv'], g['U'], g['Rz']
for c in ('ENV_PIT', 'ENV_PROPS'):
    if c not in g['CN']: g['CN'][c] = g['coll'](c)

RING_R = 4.6
Y0 = -0.55                 # the bath's bottom (the mound's foot); the fighting surface is y = 0
RIM = 1.6                  # the bathhouse floor round the bath
PX, PZ0, PZ1 = 12.0, -9.0, 9.0   # the bath's inside: x -PX..PX, z PZ0..PZ1
TOP, BOT = 6.1, 6.6        # the mound: half-size at the top, at the foot

# ---- the bath: tiled bottom, tiled walls, a hinoki rim -------------------------------------------------------------
m = GB()
m.gbox(-PX, PX, PZ0, PZ1, Y0 - 0.3, Y0, 'tile_blue')
for k in range(1, int(2 * PX)):                                        # the grout grid on the bottom
    x = -PX + k; m.gbox(x - 0.015, x + 0.015, PZ0, PZ1, Y0, Y0 + 0.004, 'tile_dk')
for k in range(1, int(PZ1 - PZ0)):
    z = PZ0 + k; m.gbox(-PX, PX, z - 0.015, z + 0.015, Y0, Y0 + 0.004, 'tile_dk')
W = 0.6
for x0, x1, z0, z1 in [(-PX - W, PX + W, PZ0 - W, PZ0), (-PX - W, PX + W, PZ1, PZ1 + W), (-PX - W, -PX, PZ0, PZ1), (PX, PX + W, PZ0, PZ1)]:
    m.gbox(x0, x1, z0, z1, Y0 - 0.3, RIM - 0.02, 'tile_blue')
# a navy band of tiles just under the rim, on the inside faces
for x0, x1, z0, z1 in [(-PX, PX, PZ0, PZ0 + 0.012), (-PX, PX, PZ1 - 0.012, PZ1), (-PX, -PX + 0.012, PZ0, PZ1), (PX - 0.012, PX, PZ0, PZ1)]:
    m.gbox(x0, x1, z0, z1, RIM - 0.55, RIM - 0.3, 'tile_navy')
for x0, x1, z0, z1 in [(-PX - W - 0.1, PX + W + 0.1, PZ0 - W - 0.1, PZ0 + 0.05), (-PX - W - 0.1, PX + W + 0.1, PZ1 - 0.05, PZ1 + W + 0.1),
                       (-PX - W - 0.1, -PX + 0.05, PZ0, PZ1), (PX - 0.05, PX + W + 0.1, PZ0, PZ1)]:
    m.gbox(x0, x1, z0, z1, RIM - 0.02, RIM + 0.22, 'hinoki', bev=0.06, seg=3)
# stone steps down into the bath, back left corner
for k in range(4):
    m.gbox(-PX + 0.05, -PX + 2.2, PZ0 + 0.05 + k * 0.55, PZ0 + 0.6 + k * 0.55, Y0, RIM - 0.25 - k * 0.5, 'stone', bev=0.04)
m.gcyl(9.2, 6.2, Y0, 0.42, 0.012, 'chrome_dk', seg=20)               # the drain
m.gcyl(9.2, 6.2, Y0, 0.3, 0.02, 'dark', seg=20)
for k, (x, z, r) in enumerate([(-8.5, 5.5, 0.9), (8.0, -6.5, 0.7), (-9.6, -2.0, 0.6), (10.4, 3.0, 0.5), (-4.0, 7.6, 0.55)]):   # puddles left behind
    m.gico(x, z, Y0 + 0.002, r, 'water_lt', sub=2, sq=(1.4, 1.0, 0.01))
obj_from(m, 'PIT_Bath', c='ENV_PIT')

# ---- the dohyo on the bath's bottom: a square clay mound, the straw ring, the start lines --------------------------
mm = MB()
rb, rt = BOT * math.sqrt(2), TOP * math.sqrt(2)
mm.lathe([(rb, Y0 - 0.02), (rt + 0.12, -0.06), (rt, 0.0)], 'cardboard_dk', seg=4, M=Rz(45), bev=0.12, ang=20)
me = mm.finish('MOD_PitMound', sharp=50)
uvl = me.uv_layers['PAL']; u = swuv('cardboard')
for p in me.polygons:
    if p.normal.z > 0.97 and p.center.z > -0.05:
        for li in p.loop_indices: uvl.data[li].uv = u
place('MOD_PitMound', 'PIT_Mound', c='ENV_PIT')
NB = 20; RB = RING_R + 0.17; da = 2 * math.pi / NB; L = 2 * RB * math.sin(da / 2) - 0.07
b = MB(); b.box(-L / 2, L / 2, RB - 0.13, RB + 0.13, 0.0, 0.17, 'tatami', bev=0.07, seg=3); b.finish('MOD_PitBale')
for i in range(NB):
    a = math.degrees(i * da); out = 0.3 if i % (NB // 4) == 0 else 0.0
    place('MOD_PitBale', 'PIT_Bale_%d' % i, (out * -math.sin(math.radians(a)), out * math.cos(math.radians(a)), 0.0), rz=a, c='ENV_PIT')
s = GB()
for x in (-0.7, 0.7): s.gbox(x - 0.045, x + 0.045, -0.45, 0.45, 0.0, 0.006, 'offwhite')
obj_from(s, 'PIT_Lines', c='ENV_PIT')

# ---- the bathhouse round it: tiled floor, the Fuji mural wall, side walls, wash stools and buckets ------------------
f = GB()
FX, FZ0, FZ1 = 30.0, -22.0, 18.0
for x0, x1, z0, z1 in [(-FX, FX, FZ0, PZ0 - W), (-FX, FX, PZ1 + W, FZ1), (-FX, -PX - W, PZ0 - W, PZ1 + W), (PX + W, FX, PZ0 - W, PZ1 + W)]:
    f.gbox(x0, x1, z0, z1, RIM - 0.4, RIM - 0.02, 'tile')
    xs = int(x0) + 1
    for x in range(xs, int(x1)):
        if x % 2 == 0: f.gbox(x - 0.012, x + 0.012, z0, z1, RIM - 0.02, RIM - 0.016, 'grout')
    for z in range(int(z0) + 1, int(z1)):
        if z % 2 == 0: f.gbox(x0, x1, z - 0.012, z + 0.012, RIM - 0.02, RIM - 0.016, 'grout')
for x in (-FX, FX):                                                    # tiled side walls with a wooden rail
    f.gbox(x - 0.6 * (1 if x > 0 else -1) * 0 - 0.6, x + 0.6, FZ0, FZ1, RIM - 0.02, RIM + 4.5, 'tile2')
    f.gbox(x - 0.75, x + 0.75, FZ0, FZ1, RIM + 2.4, RIM + 2.6, 'wood', bev=0.05)
f.gbox(-FX, FX, FZ0 - 1.0, FZ0, RIM - 0.02, RIM + 11.0, 'tile2')      # the back wall
MX0, MX1, MY0, MY1, MZ = -22.0, 22.0, RIM + 0.8, RIM + 10.2, FZ0 + 0.01
def face(pts, col, d=0.0): f.vquad([(x, y, MZ + d) for x, y in pts], col)
face([(MX0, MY0), (MX1, MY0), (MX1, MY1), (MX0, MY1)], 'sky')
face([(-15.0, MY0), (15.5, MY0), (1.6, MY0 + 7.0), (-1.2, MY0 + 7.0)], 'fuji', 0.01)
face([(-4.4, MY0 + 5.4), (-1.2, MY0 + 7.0), (1.6, MY0 + 7.0), (4.8, MY0 + 5.4), (2.7, MY0 + 5.8), (1.4, MY0 + 5.3), (0.0, MY0 + 5.9), (-1.6, MY0 + 5.3), (-2.8, MY0 + 5.8)], 'snow', 0.02)
for cx, cy, r in [(-17.0, MY0 + 7.6, 1.0), (-15.4, MY0 + 7.9, 1.3), (-13.8, MY0 + 7.5, 0.9), (13.0, MY0 + 7.9, 1.0), (14.6, MY0 + 8.1, 1.25), (16.2, MY0 + 7.8, 0.9)]:
    face([(cx + r * math.cos(a), cy + r * 0.7 * math.sin(a)) for a in U(14)], 'snow', 0.015)
x = MX0 + 0.3
while x < MX1 - 1.8:
    hh = 1.4 + 0.5 * math.sin(x * 0.7)
    face([(x, MY0), (x + 1.9, MY0), (x + 0.95, MY0 + hh)], 'pine' if int(x) % 2 else 'leaf', 0.03); x += 1.6
face([(MX0, MY0 - 0.6), (MX1, MY0 - 0.6), (MX1, MY0), (MX0, MY0)], 'tile_navy', 0.01)
for k in range(1, int((MX1 - MX0) / 2.4)):                             # the tile grid over the painting
    xx = MX0 + k * 2.4; face([(xx - 0.03, MY0 - 0.6), (xx + 0.03, MY0 - 0.6), (xx + 0.03, MY1), (xx - 0.03, MY1)], 'grout', 0.04)
for yy in (MY0 + 3.0, MY0 + 6.0):
    face([(MX0, yy - 0.03), (MX1, yy - 0.03), (MX1, yy + 0.03), (MX0, yy + 0.03)], 'grout', 0.04)
f.gbox(MX0 - 0.3, MX1 + 0.3, FZ0, FZ0 + 0.35, MY1, MY1 + 0.35, 'tile_dk', bev=0.05)
for sd in (-1, 1):                                                      # wash stations along both sides: stools, buckets
    for k in range(5):
        z = -6.5 + k * 3.2; xs = sd * 24.5
        f.gcyl(xs, z, RIM - 0.02, 0.42, 0.45, 'mustard', seg=16, bev=0.03)
        f.gcyl(xs - sd * 1.3, z + 1.0, RIM - 0.02, 0.36, 0.34, 'hinoki' if k % 2 else 'teal', seg=16, r2=0.3, bev=0.03)
        f.gbox(sd * FX - sd * 0.62 - 0.05, sd * FX - sd * 0.62 + 0.05, z - 1.0, z + 1.0, RIM + 0.9, RIM + 2.3, 'mirror')
for x, z in [(-16, 12), (17, 13), (-18, -14), (16, -15)]:              # stacked buckets, towel piles
    for j in range(3): f.gcyl(x + j * 0.1, z, RIM - 0.02 + j * 0.3, 0.36, 0.3, 'hinoki', seg=16, r2=0.32, bev=0.03)
    f.gbox(x + 1.4, x + 2.6, z - 0.5, z + 0.5, RIM - 0.02, RIM + 0.5, 'towel', bev=0.12)
obj_from(f, 'PIT_House', c='ENV_PIT')

# ---- the water (lowered by the game as it drains) and the whirlpool over the drain ---------------------------------
wtr = GB(); wtr.gbox(-PX, PX, PZ0, PZ1, RIM - 0.45, RIM - 0.3, 'water'); obj_from(wtr, 'WATER', c='ENV_PIT')
st = MB()
for k, (r0, r1, a0) in enumerate([(0.25, 1.5, 0), (0.4, 1.9, 90), (0.3, 1.3, 180), (0.45, 1.7, 270)]):
    pts = []
    for j in range(9):   # a curved streak swirling in to the middle
        t = j / 8; r = r1 + (r0 - r1) * t; a = math.radians(a0 + t * 140)
        pts.append((r * math.cos(a), r * math.sin(a)))
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        nx, ny = -(yb - ya), (xb - xa); l = math.hypot(nx, ny) or 1; w = 0.07 * (1 - 0.5 * (pts.index((xa, ya)) / 8)); nx, ny = nx / l * w, ny / l * w
        bmv = st.bm; bb = st._begin()
        vs = [bmv.verts.new((xa - nx, ya - ny, 0)), bmv.verts.new((xb - nx, yb - ny, 0)), bmv.verts.new((xb + nx, yb + ny, 0)), bmv.verts.new((xa + nx, ya + ny, 0))]
        bmv.faces.new(vs); st._end(bb, 'water_lt', smooth=False)
st.finish('MOD_Whirl'); place('MOD_Whirl', 'WHIRL', (9.2, -6.2, RIM - 0.29), c='ENV_PIT')

for ob in bpy.context.scene.objects: ob.select_set(ob.users_collection and ob.users_collection[0].name == 'ENV_PIT')
out = os.path.join(HERE, '..', '..', 'public', 'assets', 'models', 'bathpit_kit.glb')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True, export_yup=True)
print('WROTE', out)
