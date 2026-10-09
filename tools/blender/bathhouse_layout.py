# THE BATHHOUSE (stealth test level): one floor plan shared by the Blender kit (bathhouse_kit.py builds the visuals)
# and the game (public/js/bath-layout.js: colliders, points of interest). Game coordinates: x right, z towards the
# camera (the level runs to -z), y up. Blender: (x, y, z)_bl = (x, -z, y)_game.
#   python3 tools/blender/bathhouse_layout.py      -> writes public/js/bath-layout.js
#
# A two-storey neighbourhood sento on a slope: the street entrance is upstairs, the baths are on the ground floor.
# GROUND (y 0)
#   bath hall    z  4.4 .. -16   the bath (hinoki rim, steps on the near side), wash stations along the west wall,
#                                the tiled Mt Fuji wall at the far end
#   wash area    z -16  .. -27   wash stations (taps, mirrors) down both walls and a back-to-back island
#   changing rm  z -27  .. -47   frosted-glass sliding doors from the wash area; wooden lockers, benches, basket
#                                shelves, a vanity, a scale, a fan
#   staff corr.  z -47  .. -53   the wood-fired boiler, firewood, towel shelves, washing machines; a dead end: at its
#                                east end a heap of delivery boxes, dumped there for now, blocks the back stairs
#   back stairs  x 6.6 .. 11.4, z -53 .. -61, up to y 3
#   courtyard    z -53.4 .. -61, x < 6.4: a small walled garden (not walkable), under the open sky
# UPPER (y 3)
#   lounge       z -61 .. -73    tatami corner, massage chairs, milk fridge, drinks machine, manga shelf, sofa;
#                                the fire exit in the west wall
#   front hall   z -73 .. -86    the front desk; the genkan (shoe lockers, stone floor) in the west
#   south row    z -86 .. -92    genkan entrance (x < -4), staff office (walled off, x -4 .. 4), storage (x 4 .. 12)
import json, os

UP = 3.0
S = []      # solids: colliders, and what the kit builds there
def solid(k, x0, x1, z0, z1, h, f=0, tall=True, **kw):
    S.append(dict(k=k, x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1), h=h, f=f, tall=tall, **kw))
def wall(x0, x1, z0, z1, f=0, col='plaster', h=1.15, **kw): solid('wall', x0, x1, z0, z1, h, f, True, col=col, **kw)
B = []      # round blockers (plants, pillars)
def blocker(k, x, z, r, f=0, **kw): B.append(dict(k=k, x=x, z=z, r=r, f=f, **kw))
DOORS = []  # doorways (posts both sides, a threshold)
def door(x0, x1, z, f=0, kind='frame'): DOORS.append(dict(x0=x0, x1=x1, z=z, f=f, kind=kind))
def zdoor(z0, z1, x, f=0): DOORS.append(dict(z0=z0, z1=z1, x=x, f=f, kind='zframe'))   # a doorway in a wall running along z

# ================================================================ GROUND
# outer shell
wall(-12.4, -12, -37.0, 4.4, col='tile'); wall(-12.4, -12, -53.4, -38.8, col='tile'); zdoor(-38.8, -37.0, -12.2);   # the door to the toilets
wall(-12.4, -12, -58.4, -53.4, col='tile'); wall(-12.4, -12, -61, -60.2, col='tile'); zdoor(-60.2, -58.4, -12.2);          # the kitchen's back door
wall(12, 12.4, -48.4, 4.4, col='tile'); wall(12, 12.4, -53.4, -50.6, col='tile'); zdoor(-50.6, -48.4, 12.2); wall(-12.4, 12.4, 4.4, 4.8, col='tile')
# ---- bath hall: the bath (rim pieces; the gap x 0..2 on the near side has the steps)
for x0, x1, z0, z1 in [(-3.2, 0, -2.3, -1.8), (2, 9.2, -2.3, -1.8), (-3.2, 9.2, -12.2, -11.7), (-3.2, -2.7, -11.7, -2.3), (8.7, 9.2, -11.7, -2.3)]:
    solid('rim', x0, x1, z0, z1, 0.55, tall=False)
POOL = dict(x0=-2.7, x1=8.7, z0=-11.7, z1=-2.3, water=0.42, steps=[0, 2])
# wash stations along the west wall of the bath hall
solid('washrow', -12, -11.1, -14.6, 3.6, 0.5, tall=False, side='w')
# the far wall: tiled, with Mt Fuji over the bath (x 2.2 .. 12, taller); the doorway to the wash area x -2.2 .. 2.2
wall(-12, -2.2, -16.2, -15.8, col='tile'); solid('mural', 2.2, 12, -16.2, -15.8, 2.0, col='tile'); door(-2.2, 2.2, -16)
# ---- wash area: stations down both walls and a back-to-back island
solid('washrow', -12, -11.1, -26.4, -17.0, 0.5, tall=False, side='w'); solid('washrow', 11.1, 12, -26.4, -17.0, 0.5, tall=False, side='e')
solid('washisland', -9, -3, -22.6, -20.6, 0.95, tall=False); solid('washisland', 3, 9, -22.6, -20.6, 0.95, tall=False)
# frosted-glass partition with the sliding doors (x 4 .. 7.6)
wall(-12, 4, -27.2, -26.8, col='glass'); wall(7.6, 12, -27.2, -26.8, col='glass'); door(4, 7.6, -27, kind='slide')
# ---- changing room
for x0, x1, z0, z1 in [(-9, -1, -31.7, -31), (2, 10, -31.7, -31), (-7, 1, -36.7, -36), (4, 12, -36.7, -36), (-12, -4, -41.7, -41), (-1, 8, -41.7, -41)]:
    solid('lockers', x0, x1, z0, z1, 1.75)
for x0, x1, z0, z1 in [(-6, -2, -34.2, -33.6), (5, 9, -39.4, -38.8), (-9, -5, -39.4, -38.8)]:
    solid('bench', x0, x1, z0, z1, 0.45, tall=False)
solid('vanity', 11.2, 12, -46.6, -42.4, 0.85, tall=False)          # mirrors and hair dryers on the east wall
solid('baskets', -12, -11.3, -35.5, -32.0, 1.4)                    # rattan basket shelves
solid('vending', 11.0, 12, -40.3, -38.7, 1.9)                     # a drinks machine on the east wall (no coins on him: thump it)
# his: number 8, top row, at the far end of the bank at z -41 (deep in the room: it takes three charges to burst open)
LOCKER = dict(x=-12 + 2.5 * 8 / 13, z=-40.25, face=-40.98, bank=4, bx0=-12, bz0=-41.7)
wall(-12, -11.6, -47.2, -46.8); wall(-8.4, 12, -47.2, -46.8); door(-11.6, -8.4, -47)   # the staff door
# ---- staff corridor
wall(-12, 3.4, -53.4, -53, col='plaster_dk'); wall(5.4, 6.4, -53.4, -53, col='plaster_dk'); door(3.4, 5.4, -53.2)   # into the kitchen
solid('boiler', -5.0, -0.6, -53, -51.9, 1.6)
solid('firewood', 0.2, 2.6, -53, -52.2, 0.9, tall=False)
solid('towels', -9.6, -6.8, -53, -52.3, 1.5)
solid('washer', -6.6, -3.4, -48.0, -47.2, 1.0)
solid('crates', -11.8, -10.6, -52.9, -51.7, 0.8, tall=False)
CRACK = dict(x0=6.6, x1=11.4, z0=-53.0, z1=-51.7, h=1.6, x=9.0, z=-52.35)   # the box heap in front of the stairs (charge through it)
# ---- LAUNDRY ROOM (east of the corridor, beside the back stairs): rows of big washers and dryers make a maze,
# carts, a folding table; the towel shelf at the far end
wall(12, 22.8, -44.0, -43.6, col='tile'); wall(22.4, 22.8, -61, -43.6, col='tile'); wall(12, 22.8, -61, -60.6, col='tile'); wall(12, 12.4, -60.6, -53.4, col='tile')
LAUNDRY = dict(x0=12.4, x1=22.4, z0=-60.6, z1=-44.0)
for x0, x1, z0, z1 in [(12.4, 19.4, -52.2, -51.2), (15.4, 22.4, -55.4, -54.4), (12.4, 19.4, -58.3, -57.3)]:
    solid('washer', x0, x1, z0, z1, 1.4, big=True)
solid('foldtable', 15.0, 18.2, -47.6, -46.6, 0.85, tall=False)
solid('towelshelf', 12.6, 16.2, -60.6, -59.9, 1.6)
TOWEL = dict(x=14.4, z=-59.2)
CARTS = [dict(x=-2.4, z=-45.9, r=0.2), dict(x=0.4, z=-48.4, r=0.0), dict(x=20.6, z=-47.4, r=1.3), dict(x=12.95, z=-56.0, r=1.5708)]
# ---- back stairs
wall(6.4, 6.6, -61, -53.0, col='plaster_dk', h=UP + 1.0); wall(11.4, 11.6, -61, -53.0, col='plaster_dk', h=UP + 1.0); wall(11.6, 12.4, -53.4, -53, col='plaster_dk')
STAIRS = dict(x0=6.6, x1=11.4, z0=-61, z1=-53, steps=16)
COURTYARD = dict(x0=-12.4, x1=6.4, z0=-61, z1=-53.4)   # (now the kitchen)
# ---- KITCHEN (behind the corridor, under the upper floor's edge): stove line and sinks along the back, the prep island,
# the pantry, and in the corner the onigiri counter. Rat holes in the walls. The back door to the alley in the west wall
KITCHEN = dict(x0=-12, x1=6.4, z0=-61, z1=-53.4)
wall(-12.4, 6.4, -61.4, -61, col='tile')
solid('stove', -7.0, 0.0, -61, -60.0, 0.95, tall=False)
solid('ksink', 1.0, 5.4, -61, -60.2, 0.9, tall=False)
solid('prep', -6.0, 1.0, -57.8, -56.6, 0.9, tall=False)
solid('pantry', 4.8, 6.4, -58.6, -54.4, 1.8)
solid('oncounter', -12, -8.6, -54.4, -53.4, 0.95, tall=False); solid('oncounter', -12, -11.0, -56.6, -54.4, 0.95, tall=False)
solid('kfridge', -12, -10.8, -58.2, -57.0, 1.9)
ONIGIRI = dict(x=-9.9, z=-53.9, y=0.95, need=10, chef=[-9.9, -55.3])     # the plate on the counter; where the chef stands to make them
RATHOLES = [dict(x=0.5, z=-60.95)]   # one mouse hole, in the back wall between the stoves and the sinks
RATPATH = [[0.5, -59.75], [-8.4, -59.75]]   # the rats' run: out along the back wall, behind the prep island, up to the counter
TRAPS = [dict(x=-3.0, z=-55.6), dict(x=-8.0, z=-58.9), dict(x=2.6, z=-58.9), dict(x=-0.6, z=-59.3), dict(x=-10.2, z=-59.6), dict(x=3.6, z=-55.2), dict(x=-7.2, z=-55.0)]
BACKDOOR = dict(x=-12.2, z0=-60.2, z1=-58.4)
KDOOR = dict(x=4.4, z=-53.2)
# ---- TOILETS (behind a door in the changing room's west wall): five stalls down the far wall, urinals, sinks
TOILETS = dict(x0=-20.4, x1=-12.4, z0=-45, z1=-31)
wall(-20.8, -12.4, -31, -30.6, col='tile'); wall(-20.8, -12.4, -45.4, -45, col='tile'); wall(-20.8, -20.4, -45.4, -30.6, col='tile')
STALL_Z = [-32.0, -34.4, -36.8, -39.2, -41.6, -44.0]
for z in STALL_Z: solid('stallwall', -20.4, -18.2, z - 0.05, z + 0.05, 1.6)
STALLS = [dict(x=-19.3, z=(a + b) / 2) for a, b in zip(STALL_Z, STALL_Z[1:])]
STALL_USE = 2
solid('urinals', -16.4, -13.0, -31.6, -31.0, 1.1, tall=False)
solid('tsinks', -18.0, -13.4, -45.0, -44.4, 0.9, tall=False)
blocker('trolley', -12.98, -35.1, 0.75)   # the cleaner's trolley against the east wall
TP = dict(x=10.0, z=-89.6)        # toilet paper, on the storage shelf

# ================================================================ UPPER
F = 1
wall(-12.4, -12, -70.6, -61, F); wall(-12.4, -12, -92.4, -72.4, F); wall(12, 12.4, -92.4, -61, F)
wall(-12.4, 6.4, -61.4, -61, F); wall(11.6, 12.4, -61.4, -61, F); wall(-12.4, 12.4, -92.4, -92, F)
EXIT = dict(x=-12.2, z0=-72.4, z1=-70.6)
for z in (-72.6, -70.4): solid('exitpost', -12.6, -12.0, z - 0.2, z + 0.2, 2.0, F)
wall(-15, -12.4, -73, -72.8, F, col='metal'); wall(-15, -12.4, -70.2, -70.0, F, col='metal'); wall(-15.2, -15, -73, -70, F, col='metal')   # the fire escape landing
# ---- lounge
TATAMI = dict(x0=-12, x1=-4, z0=-70, z1=-62, h=0.15)
for x, z in [(-9.6, -64.6), (-6.4, -67.6)]: solid('lowtable', x - 0.8, x + 0.8, z - 0.5, z + 0.5, 0.47, F, tall=False)
for x in (0.5, 2.7, 4.9): solid('massage', x - 0.8, x + 0.8, -62.6, -61.4, 1.2, F, tall=False)
solid('fridge', 10.8, 12, -66, -63.6, 1.9, F)
solid('vending', 10.8, 12, -68.6, -67.0, 1.9, F)
solid('manga', 4, 8, -72.9, -72.4, 1.6, F)
solid('sofa', -1, 4.6, -68.0, -67.2, 0.8, F, tall=False)
solid('sofa', 6.6, 10.0, -70.4, -69.6, 0.8, F, tall=False)
solid('lowtable', 0.6, 3.0, -66.5, -65.7, 0.4, F, tall=False, plain=True)
solid('bench', 1.6, 7.4, -74.0, -73.4, 0.45, F, tall=False)
wall(-12, -3, -73.2, -72.8, F, col='wood'); wall(1, 8, -73.2, -72.8, F, col='wood'); wall(11, 12, -73.2, -72.8, F, col='wood')
door(-3, 1, -73, F); door(8, 11, -73, F)
# ---- front hall: the desk, a tall cabinet (the way behind the desk is narrow), the wall behind with the storage door
solid('desk', -1, 9, -83.2, -82, 1.05, F, tall=False)
solid('cabinet', 11, 12, -86, -80, 1.9, F)
wall(-4, 9, -86.2, -85.8, F, col='wood'); wall(11, 12, -86.2, -85.8, F, col='wood'); door(9, 11, -86, F)
# ---- genkan: shoe lockers along the west wall and an island, the entrance doors (shut for the night) in the south wall
GENKAN = dict(x0=-12, x1=-4, z0=-92, z1=-76)
solid('shoes', -12, -11.3, -91.8, -76, 1.6, F); solid('shoes', -8.6, -7.9, -89.4, -80.6, 1.6, F)
ENTRANCE = dict(x0=-10.4, x1=-7.2, z=-92)
# ---- south row: staff office (walled off) and storage
wall(-4.4, -4, -92, -86.2, F, col='wood'); wall(3.6, 4, -92, -86.2, F, col='wood')
OFFICE = dict(x0=-4, x1=3.6, z0=-92, z1=-86.2)
solid('shelf', 4.4, 5.6, -91.6, -87.4, 1.8, F); solid('shelf', 10.8, 11.8, -91.6, -88.4, 1.8, F, tp=True)   # (the top row of this one: toilet paper only)
BOX = dict(x=8.2, z=-90.2, ry=0.4)

# round blockers
for x, z, s in [(10.6, 2.8, 1), (10.6, -14.6, 0.9), (-6.0, -46.0, 0.7)]: blocker('plant', x, z, 0.8 * s, s=s)
blocker('plant', 10.8, -75.0, 0.64, F, s=0.8); blocker('plant', -2.2, -62.3, 0.56, F, s=0.7); blocker('plant', 10.9, -71.8, 0.56, F, s=0.7)
blocker('pillar', -1.8, -82.6, 0.4, F)

# things to pick up and throw; puddles
ITEMS = []
for z in (-2, -5, -8, -11, -14): ITEMS += [dict(k='stool', x=-10.5, z=z + 0.2), dict(k='oke', x=-10.2, z=z - 0.45)]
for sd in (-1, 1):
    for z in (-18.6, -21.2, -23.8): ITEMS += [dict(k='stool', x=sd * 10.5, z=z), dict(k='oke', x=sd * 10.2, z=z - 0.65)]
for z in (-19.7, -23.5):
    for x in (-7.6, -4.4, 4.4, 7.6): ITEMS += [dict(k='stool', x=x, z=z)]
ITEMS += [dict(k='bucket', x=21.4, z=-58.8), dict(k='bucket', x=13.7, z=-49.5), dict(k='bucket', x=1.4, z=-54.2), dict(k='bucket', x=-13.6, z=-43.2), dict(k='bucket', x=-4.4, z=-45.4), dict(k='bucket', x=0.6, z=-38.6), dict(k='oke', x=-3.2, z=-64.2, f=F), dict(k='bucket', x=5.6, z=-70.4, f=F), dict(k='stool', x=-5.4, z=-84.4, f=F)]
WASHB = dict(x=3.6, z=-1.0)                                         # his yellow wash bucket by the steps
PUDDLES = [dict(x=3.0, z=-59.5, rx=0.9, rz=0.5), dict(x=-15.0, z=-39.0, rx=0.9, rz=0.55), dict(x=-1.2, z=-29.2, rx=1.0, rz=0.6), dict(x=6.2, z=-44.4, rx=1.2, rz=0.7), dict(x=-9.6, z=-44.4, rx=0.9, rz=0.55), dict(x=9.8, z=-33.6, rx=0.8, rz=0.55),
           dict(x=-5.6, z=-48.6, rx=0.9, rz=0.5), dict(x=9.4, z=-66.4, rx=0.7, rz=0.45, f=F, milk=True)]

# everything but the walls breaks under a charge; long pieces in segments of about 2.4 m (only the one you hit goes)
BREAKABLE = {'lockers', 'bench', 'washrow', 'washisland', 'vanity', 'baskets', 'boiler', 'firewood', 'towels', 'cart', 'washer', 'crates',
             'lowtable', 'massage', 'fridge', 'vending', 'manga', 'sofa', 'desk', 'cabinet', 'shoes', 'shelf', 'foldtable', 'prep', 'pantry', 'kfridge', 'tsinks'}
for s_ in S:
    if s_['k'] in BREAKABLE:
        ax = 'x' if s_['x1'] - s_['x0'] >= s_['z1'] - s_['z0'] else 'z'; L = (s_['x1'] - s_['x0']) if ax == 'x' else (s_['z1'] - s_['z0'])
        s_.update(brk=1, ax=ax, n=max(1, round(L / 2.4)))

LAYOUT = dict(UP=UP, solids=S, blockers=B, doors=DOORS, pool=POOL, locker=LOCKER, crack=CRACK, stairs=STAIRS, courtyard=COURTYARD, exit=EXIT, tatami=TATAMI,
              genkan=GENKAN, entrance=ENTRANCE, office=OFFICE, box=BOX, items=ITEMS, washb=WASHB, puddles=PUDDLES, laundry=LAUNDRY, towel=TOWEL, carts=CARTS,
              kitchen=KITCHEN, onigiri=ONIGIRI, ratholes=RATHOLES, ratpath=RATPATH, traps=TRAPS, backdoor=BACKDOOR, kdoor=KDOOR, toilets=TOILETS, stalls=STALLS, stall_use=STALL_USE, tp=TP)

if __name__ == '__main__':
    import hashlib
    glb = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../public/assets/models/bathhouse_kit.glb')
    if os.path.exists(glb): LAYOUT['v'] = hashlib.md5(open(glb, 'rb').read()).hexdigest()[:10]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../public/js/bath-layout.js')
    with open(out, 'w') as fh:
        fh.write("'use strict';\n// generated by tools/blender/bathhouse_layout.py (the bathhouse floor plan, shared with the Blender kit)\nS.BathLayout = " + json.dumps(LAYOUT, separators=(',', ':')) + ';\n')
    print('wrote', out, len(S), 'solids')
