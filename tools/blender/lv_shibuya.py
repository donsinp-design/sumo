# SHIBUYA at night (ZZZ / Orbitals look): the scramble crossing, a konbini, a game centre, a karaoke box, an office, the back alley.
#   blender -b -P tools/blender/lv_shibuya.py
# Plan (game coordinates, the camera looks from +z):
#   z  6 .. -4    the station plaza: Hachiko (west), the station front, where you start
#   z -4 .. -26   the SCRAMBLE CROSSING (x -12..12); the KONBINI west of it (x -32..-14), the GAME CENTRE east (x 14..32)
#   z -26 .. -28  the north pavement
#   z -28 .. -50  KARAOKE (x -32..-8), CENTER GAI (the shopping street, x -8..8), the OFFICE (x 8..32)
#   z -50 .. -60  the BACK ALLEY (dumpsters, AC units, vending machines) and the subway stairs (the exit)
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from levelkit import *

LV = Level('shibuya', 'SHIBUYA', '渋谷', 'The scramble at night: a konbini, a game centre, karaoke, an office, the back alley')
L = LV.L; B = LV.base; UPm = LV.upper
LV.bounds(-32.5, 32.5, -60.5, 6.5)
L['style'] = dict(sky='#161a28', lit=[1.0, 0.93, 0.83], shade=[0.40, 0.44, 0.66], lo=0.30, hi=0.33, form=0.05, lift=0.03)
L['ceil'] = 1
WH = 4.2    # storey height inside
T_ = 0.3    # wall thickness

# ---------------------------------------------------------------------------------------------------------------- the ground
B.gbox(-32.5, 32.5, -60.5, 6.5, -0.2, 0.0, 'asphalt')
def pave(x0, x1, z0, z1, col='concrete'):
    B.gbox(x0, x1, z0, z1, 0.0, 0.03, col)
    # paving joints every 1.2 m (darker lines)
    for k in range(1, int((x1 - x0) / 1.2)): B.gbox(x0 + k * 1.2 - 0.015, x0 + k * 1.2 + 0.015, z0, z1, 0.03, 0.034, 'asphalt_lt')
pave(-32.5, 32.5, -4, 6.5)                 # the station plaza
pave(-32.5, 32.5, -28, -26)                # the north pavement
pave(-12, -8, -26, -4); pave(8, 12, -26, -4)   # (narrow pavements beside the crossing)
pave(-8, 8, -50, -28, 'concrete_lt')       # Center Gai
B.gbox(-32.5, 32.5, -60.5, -50, 0.0, 0.02, 'asphalt_lt')   # the back alley
# the scramble: zebra stripes on four sides and the two diagonals
def zebra(cx, cz, ang, L_, n):
    for k in range(n):
        o = (k - (n - 1) / 2) * 0.9
        B.gboxr(cx + math.cos(math.radians(ang + 90)) * o, cz - math.sin(math.radians(ang + 90)) * o, L_, 0.5, 0.0, 0.035, ang, 'paint')
zebra(0, -6.5, 0, 3.2, 18); zebra(0, -23.5, 0, 3.2, 18); zebra(-9.5, -15, 90, 3.2, 14); zebra(9.5, -15, 90, 3.2, 14)
zebra(0, -15, 37, 2.6, 9); zebra(0, -15, -37, 2.6, 9)
for x in (-8, 8):
    for z in (-26, -4): B.gbox(x - 0.1, x + 0.1, z - 0.1, z + 0.1, 0.0, 0.04, 'paint')

L['rooms'] = []
LV.room('konbini', 'the konbini', -32, -14, -24, -6)
LV.room('arcade', 'the game centre', 14, 32, -24, -6)
LV.room('karaoke', 'karaoke', -32, -8, -50, -28)
LV.room('office', 'the office', 8, 32, -50, -28)
LV.room('alley', 'the back alley', -32.5, 32.5, -60.5, -50)
LV.room('cross', 'the crossing', -12, 12, -26, -4)

# ---------------------------------------------------------------------------------------------------------------- shared props
def walls(x0, x1, z0, z1, gaps, col='concrete', glass=(), h=WH, upper=12.0, sign=None):
    """a building's four walls with door gaps: gaps = {'n': [(a, b)], 's': ..., 'e': ..., 'w': ...} (along x for n/s, along z for e/w).
    glass sides: shop fronts (a low sill, glass to the ceiling: you see in, not through... the game counts glass as not blocking sight)."""
    def run(side, a0, a1, fixed):
        cuts = sorted(gaps.get(side, []))
        segs = []; p = a0
        for a, b in cuts: segs.append((p, a)); p = b
        segs.append((p, a1))
        for a, b in segs:
            if b - a < 0.05: continue
            if side in 'ns': X0, X1, Z0, Z1 = a, b, fixed - T_ / 2, fixed + T_ / 2
            else: X0, X1, Z0, Z1 = fixed - T_ / 2, fixed + T_ / 2, a, b
            if side in glass:
                LV.solid('glasswall', X0, X1, Z0, Z1, h, tall=False, draw=False)
                B.gbox(X0, X1, Z0, Z1, 0, 0.45, 'slate_dk'); B.gbox(X0 + 0.08, X1 - 0.08, Z0 + 0.08, Z1 - 0.08, 0.45, CUT, 'glass_lt')
                B.gbox(X0 - 0.02, X1 + 0.02, Z0 - 0.02, Z1 + 0.02, CUT - 0.02, CUT + 0.04, 'steel')
                UPm.gbox(X0 + 0.08, X1 - 0.08, Z0 + 0.08, Z1 - 0.08, CUT + 0.04, h - 0.5, 'glass_lt'); UPm.gbox(X0, X1, Z0, Z1, h - 0.5, h, 'slate_dk')
                L_ = (b - a); n = max(1, int(L_ / 2.0))
                for i in range(n + 1):
                    q = a + L_ * i / n
                    if side in 'ns': B.gbox(q - 0.05, q + 0.05, Z0, Z1, 0, CUT, 'steel'); UPm.gbox(q - 0.05, q + 0.05, Z0, Z1, CUT, h, 'steel')
                    else: B.gbox(X0, X1, q - 0.05, q + 0.05, 0, CUT, 'steel'); UPm.gbox(X0, X1, q - 0.05, q + 0.05, CUT, h, 'steel')
            else:
                LV.wall(X0, X1, Z0, Z1, h=h, col=col, trim='slate_dk', base='charcoal')
        # door headers over the gaps (third person)
        for a, b in cuts:
            if side in 'ns': UPm.gbox(a, b, fixed - T_ / 2, fixed + T_ / 2, 2.6, h, col)
            else: UPm.gbox(fixed - T_ / 2, fixed + T_ / 2, a, b, 2.6, h, col)
    run('s', x0, x1, z1); run('n', x0, x1, z0); run('w', z0, z1, x0); run('e', z0, z1, x1)
    # the ceiling, and the building going up above it (third person: the storeys, their windows)
    UPm.gbox(x0, x1, z0, z1, h, h + 0.25, 'charcoal')
    if upper > h:
        UPm.gbox(x0, x1, z0, z1, h + 0.25, upper, col)
        for side in 'nsew':
            L_ = (x1 - x0) if side in 'ns' else (z1 - z0)
            for fl in range(int((upper - h - 0.6) / 3.2)):
                y = h + 1.2 + fl * 3.2
                for k in range(int(L_ / 2.2)):
                    a = (x0 if side in 'ns' else z0) + 0.8 + k * 2.2
                    if a + 1.4 > (x1 if side in 'ns' else z1) - 0.4: break
                    lit = RNG.random() < 0.55
                    c = 'lamp' if lit and RNG.random() < 0.5 else 'screen' if lit and RNG.random() < 0.3 else 'glass'
                    if side == 's': UPm.sign(a + 0.7, y + 0.8, z1 + 0.01, 1.4, 1.6, c, '+z')
                    elif side == 'n': UPm.sign(a + 0.7, y + 0.8, z0 - 0.01, 1.4, 1.6, c, '-z')
                    elif side == 'e': UPm.sign(x1 + 0.01, y + 0.8, a + 0.7, 1.4, 1.6, c, '+x')
                    else: UPm.sign(x0 - 0.01, y + 0.8, a + 0.7, 1.4, 1.6, c, '-x')
    # the inside floor
    B.gbox(x0 + T_ / 2, x1 - T_ / 2, z0 + T_ / 2, z1 - T_ / 2, 0.0, 0.04, 'slate_lt' if col != 'brick' else 'wood')

def shelf(m, x0, x1, z0, z1, h, cols=('red', 'yellow', 'blue', 'green', 'orange', 'pink', 'paper', 'teal')):
    """a konbini gondola: a white unit, shelves both sides stocked with little coloured packets."""
    m.gbox(x0, x1, z0, z1, 0, 0.12, 'charcoal'); m.gbox(x0 + 0.04, x1 - 0.04, z0 + 0.04, z1 - 0.04, 0.12, h, 'offwhite', bev=0.02)
    along_x = (x1 - x0) >= (z1 - z0)
    for lv in range(4):
        y = 0.22 + lv * (h - 0.3) / 4
        L_ = (x1 - x0) if along_x else (z1 - z0); n = int(L_ / 0.22)
        for side in (0, 1):
            m.gbox(x0 - 0.03 if not along_x and side == 0 else x0, x1 + 0.03 if not along_x and side == 1 else x1, z0 - 0.03 if along_x and side == 0 else z0, z1 + 0.03 if along_x and side == 1 else z1, y - 0.02, y, 'steel')
            for k in range(n):
                if RNG.random() < 0.15: continue
                c = cols[(k * 3 + lv + side * 5) % len(cols)]; hh = 0.12 + 0.12 * RNG.random()
                a = (x0 if along_x else z0) + 0.06 + k * 0.22
                if along_x:
                    zz = (z0 - 0.02, z0 + 0.14) if side == 0 else (z1 - 0.14, z1 + 0.02)
                    m.gbox(a, a + 0.17, zz[0], zz[1], y, y + hh, c)
                else:
                    xx = (x0 - 0.02, x0 + 0.14) if side == 0 else (x1 - 0.14, x1 + 0.02)
                    m.gbox(xx[0], xx[1], a, a + 0.17, y, y + hh, c)

def claw(m, x, z, f=0):
    """a UFO catcher: a coloured base, a glass case of plush toys, a lit top with the claw."""
    col = ['pink', 'blue_lt', 'yellow', 'teal_lt'][int(abs(x * 3 + z)) % 4]
    m.gbox(x - 0.6, x + 0.6, z - 0.6, z + 0.6, 0, 0.8, col, bev=0.04)
    m.gbox(x - 0.55, x + 0.55, z - 0.55, z + 0.55, 0.8, 1.9, 'glass_lt')
    for k in range(7):
        m.gico(x - 0.35 + (k % 3) * 0.33, z - 0.3 + (k // 3) * 0.28, 0.92, 0.14, ['yellow', 'pink', 'snow', 'orange', 'blue_lt'][k % 5], sub=1, sq=(1, 1, 0.8))
    m.gbox(x - 0.62, x + 0.62, z - 0.62, z + 0.62, 1.9, 2.15, col, bev=0.03); m.gbox(x - 0.5, x + 0.5, z + 0.6, z + 0.63, 1.94, 2.1, 'neon_pink' if col != 'pink' else 'neon_cyan')
    m.gcyl(x + 0.1, z, 1.55, 0.03, 0.35, 'steel', seg=6); m.gico(x + 0.1, z, 1.52, 0.09, 'gold', sub=1)
    m.gbox(x - 0.4, x + 0.4, z + 0.6, z + 0.75, 0.7, 0.8, 'charcoal'); m.gcyl(x - 0.2, z + 0.68, 0.8, 0.03, 0.12, 'red', seg=8)

def booth(m, x0, x1, z0, z1, curtain='neon_pink', face='w'):
    """a purikura photo booth: a big printed box, a curtain over the way in, a lit panel."""
    m.gbox(x0, x1, z0, z1, 0, 2.3, 'offwhite', bev=0.05)
    m.gbox(x0 - 0.02, x1 + 0.02, z0 - 0.02, z1 + 0.02, 2.3, 2.45, 'pink', bev=0.03)
    if face == 'w':
        m.gbox(x0 - 0.04, x0, z0 + 0.25, z1 - 0.25, 0.25, 2.1, 'pink')
        m.sign(x0 - 0.05, 2.2, (z0 + z1) / 2, z1 - z0 - 0.3, 0.16, curtain, '-x')
        for k in range(5): m.gbox(x0 - 0.06, x0 - 0.04, z0 + 0.35 + k * (z1 - z0 - 0.7) / 4 - 0.02, z0 + 0.35 + k * (z1 - z0 - 0.7) / 4 + 0.02, 0.3, 2.05, 'purple')
    else:
        m.gbox(x0 + 0.25, x1 - 0.25, z1, z1 + 0.04, 0.25, 2.1, 'pink'); m.sign((x0 + x1) / 2, 2.2, z1 + 0.05, x1 - x0 - 0.3, 0.16, curtain, '+z')

def rhythm(m, x, z):
    """a taiko rhythm game: a big drum on a stand in front of a screen cabinet."""
    m.gbox(x - 0.7, x + 0.7, z - 1.1, z - 0.4, 0, 2.2, 'red_dk', bev=0.04); m.sign(x, 1.55, z - 0.39, 1.1, 0.8, 'screen', '+z')
    m.gbox(x - 0.75, x + 0.75, z - 1.12, z - 0.38, 2.2, 2.45, 'yellow', bev=0.03); m.sign(x, 2.32, z - 0.37, 1.2, 0.16, 'neon_yellow', '+z')
    m.gbox(x - 0.55, x + 0.55, z - 0.4, z + 0.3, 0, 0.55, 'charcoal', bev=0.03)
    for dx in (-0.28, 0.28): m.gcyl(x + dx, z - 0.05, 0.75, 0.24, 0.32, 'wood_lt', seg=16, axis='Y'); m.gcyl(x + dx, z - 0.05, 0.75, 0.25, 0.26, 'paper', seg=16, axis='Y')

def sofa_u(m, x0, x1, z0, z1, col='purple'):
    """the karaoke booth's U-shaped bench along three walls (open towards +z or towards the door side)."""
    m.gbox(x0, x0 + 0.7, z0, z1, 0, 0.45, col, bev=0.06); m.gbox(x0, x0 + 0.18, z0, z1, 0.45, 0.95, col, bev=0.05)
    m.gbox(x0, x1, z0, z0 + 0.7, 0, 0.45, col, bev=0.06); m.gbox(x0, x1, z0, z0 + 0.18, 0.45, 0.95, col, bev=0.05)

def desk(m, x0, x1, z0, z1, h=0.75):
    m.gbox(x0, x1, z0, z1, h - 0.05, h, 'tan', bev=0.015)
    for x in (x0 + 0.05, x1 - 0.1):
        m.gbox(x, x + 0.05, z0 + 0.05, z1 - 0.05, 0, h - 0.05, 'steel')
    m.gbox((x0 + x1) / 2 - 0.25, (x0 + x1) / 2 + 0.25, z0 + 0.05, z0 + 0.12, h, h + 0.38, 'charcoal'); m.sign((x0 + x1) / 2, h + 0.2, z0 + 0.12, 0.42, 0.28, 'screen', '+z')
    m.gbox((x0 + x1) / 2 - 0.22, (x0 + x1) / 2 + 0.22, z0 + 0.25, z0 + 0.4, h, h + 0.02, 'charcoal')
    for k in range(RNG.randint(1, 4)): m.gbox(x0 + 0.1 + k * 0.08, x0 + 0.32 + k * 0.08, z1 - 0.35, z1 - 0.1, h + k * 0.012, h + 0.012 + k * 0.012, 'paper')

def chair(m, x, z, col='charcoal'):
    m.gcyl(x, z, 0, 0.25, 0.05, 'steel', seg=10); m.gcyl(x, z, 0.05, 0.03, 0.4, 'steel', seg=6); m.gbox(x - 0.24, x + 0.24, z - 0.24, z + 0.24, 0.45, 0.53, col, bev=0.04)
    m.gbox(x - 0.22, x + 0.22, z + 0.2, z + 0.27, 0.53, 0.95, col, bev=0.03)

def vending(m, x0, x1, z0, z1, face='+z', col='red'):
    m.gbox(x0, x1, z0, z1, 0, 1.85, col, bev=0.03)
    if face == '+z':
        m.sign((x0 + x1) / 2, 1.25, z1, x1 - x0 - 0.2, 0.9, 'neon_white', '+z')
        for k in range(6): m.gbox(x0 + 0.12 + k * (x1 - x0 - 0.24) / 6, x0 + 0.12 + (k + 0.6) * (x1 - x0 - 0.24) / 6, z1, z1 + 0.02, 1.0, 1.15, ['blue', 'orange', 'green', 'red', 'yellow', 'paper'][k])
        m.gbox(x0 + 0.15, x1 - 0.15, z1, z1 + 0.06, 0.15, 0.4, 'charcoal')
    else:
        m.sign(x0, 1.25, (z0 + z1) / 2, z1 - z0 - 0.2, 0.9, 'neon_white', '-x'); m.gbox(x0 - 0.06, x0, z0 + 0.15, z1 - 0.15, 0.15, 0.4, 'charcoal')

def dumpster(m, x0, x1, z0, z1):
    m.gbox(x0, x1, z0, z1, 0.12, 1.2, 'green_dk', bev=0.04); m.gbox(x0 - 0.04, x1 + 0.04, z0 - 0.04, z1 + 0.04, 1.2, 1.3, 'green', bev=0.03)
    for x in (x0 + 0.2, x1 - 0.2):
        for z in (z0 + 0.2, z1 - 0.2): m.gcyl(x, z, 0, 0.08, 0.12, 'charcoal', seg=8)

def acunit(m, x0, x1, z0, z1):
    m.gbox(x0, x1, z0, z1, 0, 0.75, 'offwhite', bev=0.03); m.gcyl((x0 + x1) / 2 + 0.15, z1, 0.38, 0.26, 0.04, 'charcoal', seg=16, axis='Y')

def lamp(m, x, z, h=5.0):
    m.gcyl(x, z, 0, 0.09, h, 'slate_dk', seg=8); m.gbox(x - 0.1, x + 0.9, z - 0.1, z + 0.1, h - 0.1, h, 'slate_dk'); m.gbox(x + 0.5, x + 0.9, z - 0.15, z + 0.15, h - 0.22, h - 0.1, 'lamp')

def signal(m, x, z, f='+z'):
    m.gcyl(x, z, 0, 0.07, 2.8, 'slate_dk', seg=8); m.gbox(x - 0.2, x + 0.2, z - 0.12, z + 0.12, 2.2, 2.75, 'charcoal')
    m.sign(x, 2.6, z + (0.12 if f == '+z' else -0.12), 0.24, 0.18, 'neon_red', f); m.sign(x, 2.36, z + (0.12 if f == '+z' else -0.12), 0.24, 0.18, 'charcoal', f)

def standsign(m, x, z, col, f='+z'):
    """a lit A-board on the pavement (a shop's sign at street level)."""
    m.gbox(x - 0.32, x + 0.32, z - 0.2, z + 0.2, 0, 1.1, 'charcoal', bev=0.03); m.sign(x, 0.65, z + (0.2 if f == '+z' else -0.2), 0.5, 0.75, col, f)

# ---------------------------------------------------------------------------------------------------------------- the station plaza (start)
LV.solid('hachiko', -22.6, -21.2, 1.0, 2.6, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 1.0, 'rock', bev=0.06), m.gico(-21.9, 1.8, 1.45, 0.42, 'green_dk', sq=(1.3, 0.7, 0.9)), m.gico(-21.4, 1.8, 1.75, 0.2, 'green_dk'), m.gico(-21.3, 1.8, 2.0, 0.08, 'green_dk', sq=(0.6, 0.6, 1.4))))
for x, z in [(-26, 4), (-17, 4), (26, 4), (17, 4)]:
    LV.blocker(x, z, 1.0); B.gcyl(x, z, 0, 0.9, 0.5, 'concrete_lt', seg=14); B.gico(x, z, 1.2, 0.95, 'pine', sq=(1, 1, 1.1)); B.gico(x + 0.3, z - 0.2, 1.7, 0.6, 'green_dk')
# the station front along the south edge: a long low wall with the gates (just the look: you can't go in)
LV.solid('station', -32.5, 32.5, 5.8, 6.5, 3.0, draw=lambda m, x0, x1, z0, z1, h: m.gbox(x0, x1, z0, z1, 0, 3.0, 'slate', bev=0.03))
for k in range(9): B.sign(-24 + k * 6, 2.3, 5.79, 3.6, 0.5, 'neon_white' if k % 3 else 'neon_green', '-z')
for x in (-29, -12.5, 12.5, 29): lamp(B, x, -3.2)
for x, z in [(-12.4, -3.6), (12.4, -3.6), (-12.4, -26.4), (12.4, -26.4)]: LV.blocker(x, z, 0.3); signal(B, x, z, '+z' if z > -10 else '-z')
# the big screens over the crossing (third person: up on the buildings round it)
UPm.gbox(-14, -8, -26.6, -26.3, 6, 9.5, 'charcoal'); UPm.sign(-11, 7.75, -26.29, 5.6, 3.2, 'screen', '+z')
UPm.gbox(8, 14, -26.6, -26.3, 5, 8, 'charcoal'); UPm.sign(11, 6.5, -26.29, 5.6, 2.6, 'neon_pink', '+z')

# ---------------------------------------------------------------------------------------------------------------- the KONBINI (x -32..-14, z -24..-6)
walls(-32, -14, -24, -6, {'e': [(-16.4, -12.6)]}, col='offwhite', glass=('e', 's'), upper=10.0)
UPm.gbox(-14.3, -13.7, -24, -6, 3.0, 3.6, 'offwhite'); UPm.sign(-13.69, 3.3, -15, 16, 0.18, 'neon_green', '+x'); UPm.sign(-13.69, 3.08, -15, 16, 0.18, 'neon_cyan', '+x')
for z in (-9.5, -13.0, -16.5, -20.0):
    LV.solid('gondola', -27.5, -19.0, z - 0.45, z + 0.45, 1.55, tall=True, draw=lambda m, x0, x1, z0, z1, h: shelf(m, x0, x1, z0, z1, h))
LV.solid('fridges', -32 + T_ / 2, -30.9, -22.6, -7.0, 2.2, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'steel', bev=0.02), m.gbox(x1 - 0.02, x1 + 0.01, z0 + 0.1, z1 - 0.1, 0.15, h - 0.25, 'glass_lt'), m.sign(x1 + 0.02, h - 0.12, (z0 + z1) / 2, z1 - z0 - 0.2, 0.12, 'neon_white', '+x'),
    [m.gbox(x1 - 0.5, x1 - 0.05, z0 + 0.2 + k * 0.32, z0 + 0.44 + k * 0.32, 0.25 + 0.42 * (k % 4), 0.5 + 0.42 * (k % 4), ['blue', 'orange', 'green', 'paper', 'red', 'yellow'][k % 6]) for k in range(int((z1 - z0 - 0.4) / 0.32))]))
LV.solid('counter', -30.5, -21.0, -23.8 + T_ / 2, -22.4, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'offwhite', bev=0.03), m.gbox(x0 - 0.04, x1 + 0.04, z0 - 0.04, z1 + 0.06, h, h + 0.05, 'slate_dk'), m.gbox(-27.5, -26.9, -23.2, -22.7, h + 0.05, h + 0.35, 'charcoal'), m.sign(-27.2, h + 0.25, -22.69, 0.5, 0.2, 'screen', '+z'),
    m.gbox(-24.5, -23.2, -23.4, -22.6, h + 0.05, h + 0.6, 'glass_lt'), [m.gico(-24.2 + k * 0.3, -23.0, h + 0.15, 0.1, 'orange', sub=1) for k in range(4)]))
B.gbox(-30, -21, -24 + T_ / 2, -23.85, 1.3, 2.5, 'offwhite'); B.sign(-25.5, 2.2, -23.84, 8, 0.25, 'neon_green', '+z')   # (the cigarette wall behind the till)
LV.solid('atm', -15.2, -14.2 + -T_ / 2 + 0.15, -23.4, -22.4, 1.7, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'slate_lt', bev=0.03), m.sign(x0 - 0.0, 1.2, (z0 + z1) / 2, 0.6, 0.4, 'screen', '-x')))
LV.solid('magazines', -15.0, -14.2 + -T_ / 2 + 0.15, -10.5, -6.6, 1.2, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'offwhite', bev=0.02), [m.gbox(x0 - 0.02, x0, z0 + 0.1 + k * 0.38, z0 + 0.4 + k * 0.38, 0.5 + 0.3 * (k % 2), 0.85 + 0.3 * (k % 2), ['pink', 'yellow', 'blue_lt', 'red', 'teal_lt'][k % 5]) for k in range(10)]))
LV.solid('icecream', -19.6, -17.6, -7.6, -6.4 + -T_ / 2 + 0.0, 0.85, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'offwhite', bev=0.04), m.gbox(x0 + 0.08, x1 - 0.08, z0 + 0.08, z1 - 0.08, h, h + 0.02, 'glass_lt'), [m.gbox(x0 + 0.15 + k * 0.3, x0 + 0.38 + k * 0.3, z0 + 0.2, z0 + 0.5, h - 0.15, h - 0.02, ['pink', 'paper', 'yellow', 'blue_lt', 'orange', 'green'][k]) for k in range(6)]))
LV.hide('freezer', -18.6, -7.9, (-18.6, -9.0), by=0.95, label='the ice cream freezer')   # (inside the ice-cream chest, booty up through the glass)
LV.solid('oden', -21.0, -19.8, -23.6, -22.4, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'steel', bev=0.03), m.gbox(x0 + 0.08, x1 - 0.08, z0 + 0.08, z1 - 0.08, h, h + 0.02, 'tan'), [m.gico(x0 + 0.25 + (k % 3) * 0.35, z0 + 0.3 + (k // 3) * 0.4, h + 0.04, 0.09, ['offwhite', 'tan', 'ochre'][k % 3], sub=1) for k in range(6)]))
# the stock room door at the back (staff only: a hide behind it)
for x, z in [(-12.8, -9.0), (-12.8, -19.5)]: standsign(B, x, z, 'neon_green', '+z')
B.gbox(-13.8, -13.6, -16.4, -12.6, 2.4, 2.6, 'steel'); B.gbox(-14.0, -13.4, -16.4, -16.2, 0, 2.6, 'steel'); B.gbox(-14.0, -13.4, -12.8, -12.6, 0, 2.6, 'steel')   # (the automatic doors' frame)

# ---------------------------------------------------------------------------------------------------------------- the GAME CENTRE (x 14..32, z -24..-6)
walls(14, 32, -24, -6, {'w': [(-17.2, -12.4)]}, col='charcoal', glass=('s',), upper=13.0)
UPm.gbox(13.7, 14.3, -24, -6, 3.0, 3.8, 'charcoal'); UPm.sign(13.69, 3.4, -15, 16, 0.4, 'neon_pink', '-x'); UPm.sign(13.69, 3.0, -15, 16, 0.15, 'neon_cyan', '-x')
B.gbox(14.15, 32, -24, -6, 0.04, 0.05, 'purple')   # (a dark carpet)
for z in (-8.5, -10.1, -11.7):
    for x in (17.2, 18.8):
        LV.solid('claw', x - 0.6, x + 0.6, z - 0.6, z + 0.6, 2.15, draw=lambda m, x0, x1, z0, z1, h: claw(m, (x0 + x1) / 2, (z0 + z1) / 2))
for z in (-17.8, -19.4, -21.0):
    for x in (17.2, 18.8):
        LV.solid('claw', x - 0.6, x + 0.6, z - 0.6, z + 0.6, 2.15, draw=lambda m, x0, x1, z0, z1, h: claw(m, (x0 + x1) / 2, (z0 + z1) / 2))
for x in (23.0, 26.0):
    LV.solid('taiko', x - 0.75, x + 0.75, -23.7, -22.6, 2.45, draw=lambda m, x0, x1, z0, z1, h: rhythm(m, (x0 + x1) / 2, (z0 + z1) / 2 + 0.75))
LV.solid('medal', 22.0, 27.0, -15.6, -12.6, 1.6, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 1.0, 'gold', bev=0.06), m.gbox(x0 + 0.2, x1 - 0.2, z0 + 0.2, z1 - 0.2, 1.0, 1.6, 'glass_lt'), m.gbox(x0 + 0.5, x1 - 0.5, z0 + 0.5, z1 - 0.5, 1.0, 1.25, 'mustard'), [m.gcyl(x0 + 0.7 + k * 0.45, z0 + 0.8 + (k % 3) * 0.6, 1.25, 0.1, 0.03, 'gold', seg=10) for k in range(9)], m.gbox(x0 + 1.5, x1 - 1.5, z0 + 1.2, z1 - 1.2, 1.6, 2.4, 'red'), m.sign((x0 + x1) / 2, 2.1, z1 - 1.19, 1.8, 0.5, 'neon_yellow', '+z')))
for k, z in enumerate((-8.6, -11.4, -20.6)):
    LV.solid('purikura', 30.0, 31.85, z - 1.1, z + 1.1, 2.45, draw=lambda m, x0, x1, z0, z1, h, k=k: booth(m, x0, x1, z0, z1, ['neon_pink', 'neon_cyan', 'neon_yellow'][k], 'w'))
    LV.hide('booth', 30.9, z, (28.9, z), by=None, label='a photo booth')
LV.solid('prize', 28.6, 31.85, -17.4, -15.2, 1.1, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'offwhite', bev=0.03), m.gbox(x0, x1, z0, z1, h, h + 0.04, 'slate_dk'), [m.gico(x0 + 0.4 + k * 0.5, (z0 + z1) / 2, h + 0.22, 0.2, ['pink', 'yellow', 'blue_lt', 'snow', 'orange', 'teal_lt'][k], sq=(1, 1, 1.1)) for k in range(6)]))
for x in (20.5, 22.5): LV.cart(x, -20.5, 0.0)   # (prize trolleys: push them, hide in them)

# ---------------------------------------------------------------------------------------------------------------- CENTER GAI (x -8..8, z -28..-50): the shopping street
for z in (-31, -37, -43, -48):
    for x in (-7.2, 7.2): lamp(B, x, z, 4.4)
# banner arch over the street (third person)
UPm.gbox(-7.8, -7.4, -28.4, -28.0, 0, 6.5, 'slate_dk'); UPm.gbox(7.4, 7.8, -28.4, -28.0, 0, 6.5, 'slate_dk'); UPm.gbox(-7.8, 7.8, -28.4, -28.0, 5.6, 6.5, 'charcoal'); UPm.sign(0, 6.05, -27.99, 12, 0.6, 'neon_yellow', '+z')
LV.blocker(-7.6, -28.2, 0.3); LV.blocker(7.6, -28.2, 0.3)
for z, col in [(-33, 'neon_pink'), (-40, 'neon_cyan'), (-46, 'neon_yellow')]:
    standsign(B, -6.6, z, col, '+z'); standsign(B, 6.6, z + 2, col, '+z')
LV.solid('stall', -3.0, -1.0, -41.0, -38.0, 1.4, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 0.9, 'wood', bev=0.03), m.gbox(x0 - 0.2, x1 + 0.2, z0 - 0.2, z1 + 0.2, 2.2, 2.35, 'red'), [m.gcyl(xx, zz, 0, 0.05, 2.2, 'wood_dk', seg=6) for xx in (x0, x1) for zz in (z0, z1)], [m.gico(x0 + 0.3 + k * 0.35, (z0 + z1) / 2, 0.98, 0.12, 'ochre', sub=1) for k in range(5)], m.sign((x0 + x1) / 2, 2.0, z1 + 0.21, 1.8, 0.25, 'lamp', '+z')))   # a takoyaki stand
LV.cart(3.0, -35.0, 1.5708)   # a delivery trolley left on the street
LV.solid('bins', 1.5, 3.3, -46.6, -45.8, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: [m.gbox(x0 + k * 0.62, x0 + k * 0.62 + 0.55, z0, z1, 0, h, ['blue', 'green', 'yellow'][k], bev=0.04) for k in range(3)])

# ---------------------------------------------------------------------------------------------------------------- KARAOKE (x -32..-8, z -50..-28)
walls(-32, -8, -50, -28, {'e': [(-33.6, -30.4)], 'n': [(-14.4, -12.6)]}, col='brick', glass=(), upper=14.0)
UPm.gbox(-8.2, -7.6, -50, -28, 2.9, 3.8, 'brick'); UPm.sign(-7.59, 3.35, -36, 12, 0.6, 'neon_pink', '+x')
for k in range(5): UPm.sign(-7.59, 5.5 + k * 1.4, -31.5, 1.1, 1.0, ['neon_pink', 'neon_cyan', 'neon_yellow', 'neon_pink', 'neon_cyan'][k], '+x')   # (the vertical sign up the building)
# lobby (x -16..-8, z -36..-28): the front desk, a drinks bar; the corridor runs west at z -33 .. -35
LV.solid('kdesk', -13.0, -10.0, -32.6, -31.6, 1.05, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'purple', bev=0.03), m.gbox(x0 - 0.05, x1 + 0.05, z0 - 0.05, z1 + 0.05, h, h + 0.05, 'charcoal'), m.sign((x0 + x1) / 2, 0.55, z1 + 0.0, 2.6, 0.12, 'neon_pink', '+z'), m.gbox(-12.0, -11.4, -32.4, -32.0, h + 0.05, h + 0.4, 'charcoal'), m.sign(-11.7, h + 0.25, -31.99, 0.5, 0.25, 'screen', '+z')))
LV.solid('drinkbar', -15.8, -14.6, -35.6, -29.0, 1.1, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'charcoal', bev=0.03), [m.gbox(x0 + 0.2, x0 + 0.5, z0 + 0.3 + k * 0.8, z0 + 0.6 + k * 0.8, h, h + 0.5, ['red', 'orange', 'green', 'blue', 'yellow', 'paper', 'pink', 'teal'][k % 8], bev=0.03) for k in range(8)]))
# rooms: two rows off a corridor (z -38 .. -40 runs the width), booths 5 wide
CORZ0, CORZ1 = -40.2, -37.8
for k, x0 in enumerate((-32, -27, -22)):
    x1 = x0 + 5
    for row, (z0, z1, dz) in enumerate(((-50, CORZ0, CORZ0), (CORZ1, -28, CORZ1))):
        if row == 1 and x0 == -22: continue   # (the lobby end)
        dx0, dx1 = x0 + 1.4, x0 + 3.0
        # the booth's walls (the corridor side has the door)
        LV.wall(x1 - T_ / 2, x1 + T_ / 2, z0, z1, h=WH, col='brick', base='charcoal') if x1 < -16.9 or row == 0 else None
        LV.wall(x0 + T_ / 2 if x0 == -32 else x0 - T_ / 2, x0 + T_ / 2, z0, z1, h=WH, col='brick', base='charcoal') if x0 != -32 else None
        if row == 0:
            LV.wall(x0, dx0, dz - T_ / 2, dz + T_ / 2, h=WH, col='brick', base='charcoal'); LV.wall(dx1, x1, dz - T_ / 2, dz + T_ / 2, h=WH, col='brick', base='charcoal'); UPm.gbox(dx0, dx1, dz - T_ / 2, dz + T_ / 2, 2.4, WH, 'brick')
            zin0, zin1, back = z0 + 0.2, dz - 0.2, z0
        else:
            LV.wall(x0, dx0, dz - T_ / 2, dz + T_ / 2, h=WH, col='brick', base='charcoal'); LV.wall(dx1, x1, dz - T_ / 2, dz + T_ / 2, h=WH, col='brick', base='charcoal'); UPm.gbox(dx0, dx1, dz - T_ / 2, dz + T_ / 2, 2.4, WH, 'brick')
            zin0, zin1, back = dz + 0.2, z1 - 0.2, z1
        col = ['purple', 'teal', 'red_dk', 'navy', 'purple'][(k + row) % 5]
        B.gbox(x0 + 0.15, x1 - 0.15, min(zin0, zin1), max(zin0, zin1), 0.04, 0.06, ['navy', 'purple', 'charcoal'][(k + row) % 3])   # carpet
        # the sofa along the back and the side, a low table, the screen on the side wall
        if row == 0:
            LV.solid('ksofa', x0 + 0.2, x1 - 0.2, z0 + 0.2, z0 + 1.0, 0.95, tall=False, draw=lambda m, a0, a1, b0, b1, h, col=col: (m.gbox(a0, a1, b0, b1, 0, 0.45, col, bev=0.07), m.gbox(a0, a1, b0, b0 + 0.22, 0.45, h, col, bev=0.06)))
            LV.solid('ktable', x0 + 1.2, x1 - 1.2, z0 + 1.6, z0 + 2.6, 0.5, tall=False, draw=lambda m, a0, a1, b0, b1, h: (m.gbox(a0, a1, b0, b1, 0.42, 0.5, 'charcoal', bev=0.02), m.gbox(a0 + 0.1, a1 - 0.1, b0 + 0.1, b1 - 0.1, 0, 0.42, 'slate_dk'), m.gcyl(a0 + 0.4, b0 + 0.5, 0.5, 0.05, 0.2, 'mustard', seg=8), m.gcyl(a1 - 0.5, b0 + 0.4, 0.5, 0.05, 0.16, 'orange', seg=8), m.gbox(a0 + 0.9, a0 + 1.3, b0 + 0.3, b0 + 0.6, 0.5, 0.55, 'charcoal')))
            B.gbox(x1 - 0.32, x1 - 0.15, z0 + 1.0, z0 + 3.4, 1.0, 2.2, 'charcoal'); B.vquad([(x1 - 0.33, 1.1, z0 + 3.3), (x1 - 0.33, 1.1, z0 + 1.1), (x1 - 0.33, 2.1, z0 + 1.1), (x1 - 0.33, 2.1, z0 + 3.3)], 'screen')
            LV.hide('booth', x0 + 0.8, z0 + 0.6, ((dx0 + dx1) / 2, dz - 1.0), by=0.62, label='behind the karaoke sofa')
        else:
            LV.solid('ksofa', x0 + 0.2, x1 - 0.2, z1 - 1.0, z1 - 0.2, 0.95, tall=False, draw=lambda m, a0, a1, b0, b1, h, col=col: (m.gbox(a0, a1, b0, b1, 0, 0.45, col, bev=0.07), m.gbox(a0, a1, b1 - 0.22, b1, 0.45, h, col, bev=0.06)))
            LV.solid('ktable', x0 + 1.2, x1 - 1.2, z1 - 2.6, z1 - 1.6, 0.5, tall=False, draw=lambda m, a0, a1, b0, b1, h: (m.gbox(a0, a1, b0, b1, 0.42, 0.5, 'charcoal', bev=0.02), m.gbox(a0 + 0.1, a1 - 0.1, b0 + 0.1, b1 - 0.1, 0, 0.42, 'slate_dk'), m.gcyl(a0 + 0.5, b0 + 0.4, 0.5, 0.05, 0.2, 'pink', seg=8)))
            B.vquad([(x1 - 0.33, 1.1, z1 - 3.3), (x1 - 0.33, 1.1, z1 - 1.1), (x1 - 0.33, 2.1, z1 - 1.1), (x1 - 0.33, 2.1, z1 - 3.3)], 'screen'); B.gbox(x1 - 0.32, x1 - 0.15, z1 - 3.4, z1 - 1.0, 1.0, 2.2, 'charcoal')
            LV.hide('booth', x0 + 0.8, z1 - 0.6, ((dx0 + dx1) / 2, dz + 1.0), by=0.62, label='behind the karaoke sofa')
        # a mirror ball (third person: hangs from the ceiling) and the room's coloured light strip along the ceiling
        UPm.gico((x0 + x1) / 2, (zin0 + zin1) / 2, WH - 0.5, 0.25, 'steel', sub=2); UPm.gbox(x0 + 0.2, x1 - 0.2, back - 0.05 if row else back + 0.05, back + 0.05 if not row else back - 0.05, WH - 0.35, WH - 0.25, ['neon_pink', 'neon_cyan', 'neon_yellow'][(k + row) % 3])
B.gbox(-32, -16, CORZ0, CORZ1, 0.04, 0.06, 'charcoal')   # corridor carpet
for x in (-30, -25, -20): B.sign(x, 0.06, (CORZ0 + CORZ1) / 2, 1.6, 0.08, 'neon_pink', 'up')

# ---------------------------------------------------------------------------------------------------------------- the OFFICE (x 8..32, z -50..-28)
walls(8, 32, -50, -28, {'w': [(-33.6, -30.4)], 'n': [(16.4, 18.2)]}, col='slate', glass=('s',), upper=18.0)
UPm.gbox(7.7, 8.3, -50, -28, 3.0, 3.6, 'slate'); UPm.sign(7.69, 3.3, -39, 10, 0.3, 'neon_white', '-x')
B.gbox(8.15, 32, -50, -28, 0.04, 0.05, 'slate_lt')
LV.solid('reception', 9.6, 12.0, -36.0, -33.0, 1.1, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'offwhite', bev=0.04), m.gbox(x0 - 0.05, x1 + 0.05, z0 - 0.05, z1 + 0.05, h, h + 0.05, 'wood')))
# the cubicle farm: four pods of four desks with low partitions
for px, pz in [(15.0, -33.5), (21.0, -33.5), (15.0, -40.5), (21.0, -40.5)]:
    LV.solid('partition', px - 2.4, px + 2.4, pz - 0.06, pz + 0.06, 1.25, tall=False, draw=lambda m, x0, x1, z0, z1, h: m.gbox(x0, x1, z0, z1, 0, h, 'khaki', bev=0.02))
    LV.solid('partition', px - 0.06, px + 0.06, pz - 2.2, pz + 2.2, 1.25, tall=False, draw=lambda m, x0, x1, z0, z1, h: m.gbox(x0, x1, z0, z1, 0, h, 'khaki', bev=0.02))
    for sx in (-1, 1):
        for sz in (-1, 1):
            x0, x1 = (px - 2.3, px - 0.1) if sx < 0 else (px + 0.1, px + 2.3)
            z0, z1 = (pz - 0.85, pz - 0.1) if sz < 0 else (pz + 0.1, pz + 0.85)
            LV.solid('desk', x0, x1, z0, z1, 0.75, tall=False, draw=lambda m, a0, a1, b0, b1, h, sz=sz: desk(m, a0, a1, b0, b1, h) if sz > 0 else desk(m, a0, a1, b0, b1, h))
            chair(B, (x0 + x1) / 2, z1 + 0.55 if sz > 0 else z0 - 0.55)
LV.hide('desk', 13.6, -32.9, (13.6, -31.6), by=None, label='under a desk')
LV.hide('desk', 22.4, -41.1, (22.4, -42.4), by=None, label='under a desk')
LV.solid('copier', 26.6, 28.2, -31.0, -29.6, 1.15, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 0.95, 'offwhite', bev=0.05), m.gbox(x0 + 0.1, x1 - 0.1, z0 + 0.1, z1 - 0.1, 0.95, 1.05, 'slate_dk'), m.gbox(x0 + 0.15, x1 - 0.15, z0 + 0.15, z1 - 0.15, 1.05, 1.07, 'screen'), m.gbox(x1, x1 + 0.4, z0 + 0.3, z1 - 0.3, 0.6, 0.66, 'steel')))
LV.hide('copier', 27.4, -30.3, (27.4, -32.0), by=1.18, label='on the photocopier')   # (sat on the glass: his booty up on top)
LV.solid('cooler', 30.9, 31.8, -31.2, -30.2, 1.4, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 1.0, 'offwhite', bev=0.04), m.gcyl((x0 + x1) / 2, (z0 + z1) / 2, 1.0, 0.24, 0.45, 'water_lt', seg=14)))
# the meeting room (glass, x 26 .. 32, z -50 .. -42) and the boss's office (x 8 .. 14, z -50 .. -44)
LV.solid('glasswall', 25.8, 26.1, -50, -46.4, WH, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 0.1, 'steel'), m.gbox(x0, x1, z0, z1, 0.1, CUT, 'glass_lt'))); UPm.gbox(25.8, 26.1, -50, -46.4, CUT, WH, 'glass_lt')
LV.solid('glasswall', 25.8, 32, -42.15, -41.85, WH, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, 0.1, 'steel'), m.gbox(x0, x1, z0, z1, 0.1, CUT, 'glass_lt'))); UPm.gbox(25.8, 32, -42.15, -41.85, CUT, WH, 'glass_lt')
LV.solid('mtable', 27.6, 30.6, -48.4, -45.0, 0.75, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, h - 0.06, h, 'wood_lt', bev=0.03), m.gbox(x0 + 0.6, x1 - 0.6, z0 + 0.6, z1 - 0.6, 0, h - 0.06, 'slate_dk'), [m.gbox(x0 + 0.3 + k * 0.6, x0 + 0.5 + k * 0.6, z0 + 0.2, z0 + 0.45, h, h + 0.01, 'paper') for k in range(4)]))
for x in (28.0, 29.2, 30.4):
    for z in (-49.0, -44.4): chair(B, x, z, 'navy')
B.vquad([(31.83, 1.0, -44.0), (31.83, 1.0, -48.6), (31.83, 2.4, -48.6), (31.83, 2.4, -44.0)], 'screen')
LV.wall(8, 11.6, -44.15, -43.85, h=WH, col='wood_lt', trim='wood_dk', base='wood_dk'); LV.wall(13.4, 14.3, -44.15, -43.85, h=WH, col='wood_lt', trim='wood_dk', base='wood_dk'); LV.wall(14.0, 14.3, -50, -43.85, h=WH, col='wood_lt', trim='wood_dk', base='wood_dk')
UPm.gbox(11.6, 13.4, -44.15, -43.85, 2.4, WH, 'wood_lt')
LV.solid('bossdesk', 9.0, 12.6, -48.0, -46.8, 0.8, tall=False, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'wood_dk', bev=0.04), m.gbox(x0 - 0.04, x1 + 0.04, z0 - 0.04, z1 + 0.04, h, h + 0.05, 'wood'), m.gbox(10.4, 11.2, -47.9, -47.6, h + 0.05, h + 0.5, 'charcoal'), m.gcyl(9.4, -47.2, h + 0.05, 0.12, 0.25, 'green', seg=10), m.gico(9.4, -47.2, h + 0.4, 0.2, 'grass', sub=1)))
B.gbox(9.5, 12.0, -49.85, -49.6, 0.5, 2.3, 'wood'); [B.gbox(9.6 + k * 0.25, 9.8 + k * 0.25, -49.6, -49.4, 0.55 + (k % 3) * 0.55, 0.85 + (k % 3) * 0.55, ['red', 'navy', 'gold', 'green_dk'][k % 4]) for k in range(9)]
LV.hide('cupboard', 31.2, -36.8, (30.0, -36.8), by=None, label='the supply cupboard')
LV.solid('cupboard', 31.0, 31.85, -38.0, -35.6, 2.2, draw=lambda m, x0, x1, z0, z1, h: (m.gbox(x0, x1, z0, z1, 0, h, 'steel', bev=0.03), m.gbox(x0 - 0.02, x0, z0 + 0.1, (z0 + z1) / 2 - 0.02, 0.1, h - 0.1, 'slate_lt'), m.gbox(x0 - 0.02, x0, (z0 + z1) / 2 + 0.02, z1 - 0.1, 0.1, h - 0.1, 'slate_lt')))
for x, z in [(9.0, -29.0), (25.2, -42.8)]: LV.blocker(x, z, 0.5); B.gcyl(x, z, 0, 0.3, 0.5, 'wood_dk', seg=10); B.gico(x, z, 1.0, 0.45, 'grass', sq=(1, 1, 1.3))

# ---------------------------------------------------------------------------------------------------------------- the BACK ALLEY (z -50 .. -60) and the subway stairs
LV.wall(-32.5, 32.5, -60.6, -60.3, h=8.0, col='brick', base='charcoal')
for x in (-26.5, -12.0, 13.0, 25.0):
    LV.solid('dumpster', x - 1.0, x + 1.0, -59.9, -58.6, 1.3, tall=False, draw=lambda m, x0, x1, z0, z1, h: dumpster(m, x0, x1, z0, z1))
LV.hide('dumpster', -26.5, -59.2, (-26.5, -57.6), by=1.25, label='a dumpster')
LV.hide('dumpster', 25.0, -59.2, (25.0, -57.6), by=1.25, label='a dumpster')
for x0 in (-22.0, -18.5, 18.0, 21.5):
    LV.solid('ac', x0, x0 + 1.2, -50.9 + -T_ / 2, -50.2 + -T_ / 2, 0.75, tall=False, draw=lambda m, a0, a1, b0, b1, h: acunit(m, a0, a1, b0, b1))
LV.solid('vending', -9.4, -8.2, -59.9, -59.1, 1.85, draw=lambda m, x0, x1, z0, z1, h: vending(m, x0, x1, z0, z1, '+z', 'blue'))
LV.solid('vending', -7.9, -6.7, -59.9, -59.1, 1.85, draw=lambda m, x0, x1, z0, z1, h: vending(m, x0, x1, z0, z1, '+z', 'red'))
LV.solid('vending', 6.7, 7.9, -59.9, -59.1, 1.85, draw=lambda m, x0, x1, z0, z1, h: vending(m, x0, x1, z0, z1, '+z', 'offwhite'))
for x, z in [(-16, -55), (-4, -52.5), (16, -55.5)]:
    LV.blocker(x, z, 0.45); B.gcyl(x, z, 0, 0.38, 0.9, 'steel', seg=12); B.gcyl(x, z, 0.9, 0.42, 0.06, 'slate', seg=12)   # bins
# the subway stairs: a railed opening going down, the green sign (the EXIT)
LV.solid('rail', -2.2, -2.0, -59.6, -56.2, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: m.gbox(x0, x1, z0, z1, 0, h, 'green_dk'))
LV.solid('rail', 2.0, 2.2, -59.6, -56.2, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: m.gbox(x0, x1, z0, z1, 0, h, 'green_dk'))
LV.solid('rail', -2.2, 2.2, -59.8, -59.6, 1.0, tall=False, draw=lambda m, x0, x1, z0, z1, h: m.gbox(x0, x1, z0, z1, 0, h, 'green_dk'))
for k in range(8): B.gbox(-2.0, 2.0, -59.6 + k * 0.42, -59.18 + k * 0.42, -0.08 - k * 0.0, 0.0, 'charcoal' if k % 2 else 'slate_dk')
B.gbox(-2.6, -2.2, -56.4, -56.0, 0, 2.6, 'green_dk'); B.gbox(-2.8, -1.0, -56.3, -56.1, 2.2, 2.7, 'green'); B.sign(-1.9, 2.45, -56.09, 1.6, 0.36, 'neon_green', '+z')

# ---------------------------------------------------------------------------------------------------------------- the party spots and the moving parts
L['start'] = [[-19.0, 2.0], [-16.5, 2.0]]
L['maw'] = [[-22.8, -15.0], [24.4, -18.6], [-29.4, -46.6], [29.0, -47.5], [-20.0, -54.5], [20.0, -54.5], [0.6, -43.6], [-28.0, 2.6]]
L['exit'] = dict(x=0.0, z=-55.0, name='the subway stairs (back alley)')
L['pants'] = [0.0, -15.0]; L['hider'] = [-3.0, 2.0]; L['seeker'] = [3.0, 2.0]
L['staffZone'] = dict(x0=-32, x1=32, z0=-60, z1=-6)
L['seekerName'] = 'store manager'; L['hideList'] = 'the ice-cream freezer, a photo booth, behind a karaoke sofa, under a desk, on the photocopier, a dumpster, the crowd'
# the crowd crossing the scramble (stand among them: hidden), and drifting up and down Center Gai
L['crowd'] = [dict(path=[[-11, -5], [11, -25], [11, -5], [-11, -25]], n=10, v=1.2, w=2.6), dict(path=[[-10, -15], [10, -15]], n=5, v=1.1, w=3.0),
              dict(path=[[-4.5, -29], [-4.5, -49], [4.5, -49], [4.5, -29]], n=8, v=1.0, w=1.6)]
# a delivery truck crossing on the green: across, a wait while the people cross, back
L['movers'] = [dict(k='truck', path=[[-31.0, -2.4], [31.0, -2.4]], v=5.0, r=1.3, w=4.4, d=2.0, stops=[0, 1], stopT=6.0, hit='HIT BY A TRUCK!')]
L['ring'] = dict(x=0.0, z=-15.0)
L['lights'] = [dict(x=x, z=z, r=3.2, col='#ffb860', a=0.3) for x in (-29, -12.5, 12.5, 29) for z in (-3.2,)] + \
              [dict(x=x + 0.7, z=z, r=2.6, col='#ffc070', a=0.28) for z in (-31, -37, -43, -48) for x in (-7.2, 6.2)] + \
              [dict(x=-13.0, z=-14.5, r=3.0, col='#7dffa8', a=0.22), dict(x=13.0, z=-14.8, r=3.4, col='#ff6fb0', a=0.25), dict(x=-7.0, z=-31.5, r=2.8, col='#ff6fb0', a=0.22),
               dict(x=0.0, z=-56.5, r=2.4, col='#7dffa8', a=0.25), dict(x=-11, z=-26.8, r=4.0, col='#8ac8ff', a=0.2), dict(x=11, z=-26.8, r=4.0, col='#ff6fb0', a=0.2)]
def line(who, jp, en): return dict(who=who, jp=jp, en=en)
L['story'] = dict(
    start=[-29.4, -46.2, 1.57],
    intro=[line('', 'ん…ここは…カラオケ?', '...Mm. Where... karaoke?'),
           line('', '誰だ、「マイ・ウェイ」を十一回も歌ったのは。', 'Who sang "My Way" eleven times?'),
           line('', '…まわしが、ない。', '...My MAWASHI is gone.')],
    steps=[
        dict(obj='Sneak out of the booth to the karaoke FRONT DESK', at=[-11.5, -30.8], r=1.4, do='use', verb='read the note',
             think='The staff are on the corridor. Stay out of their sight.',
             say=[line('', 'メモがある。「忘れ物:とても長いベルト → 向かいのコンビニへ」', 'A note: "Lost property: one VERY long belt. Taken to the konbini."')]),
        dict(obj='Get to the KONBINI and check the lost property (by the till)', at=[-26.0, -21.6], r=1.5, do='use', verb='check the lost property',
             think='Across the crossing. Two people round me and nobody notices a thing.',
             say=[line('店員のメモ', '「ゲーセンの人が持っていきました。クレーンゲームの景品にするって」', 'Clerk\'s note: "The game centre guy took it. He wants it as a CLAW MACHINE prize."'),
                  line('', '…俺のまわしが、景品。', '...My mawashi. A prize.')]),
        dict(obj='In the GAME CENTRE: booty-slam the claw machine open', at=[18.0, -9.3], r=1.8, do='slam',
             think='Hold J for a booty slam. That glass won\'t know what hit it.',
             say=[line('', '…ぬいぐるみだけだ。景品の札がある。', '...Only plushies. There\'s a prize tag.'),
                  line('景品の札', '「特賞:チャンピオンベルト → 部長が会社に持ち帰り」', 'Tag: "GRAND PRIZE: champion\'s belt. Taken back to the office by the BOSS."')]),
        dict(obj='Into the OFFICE: find out where the boss is (the photocopier)', at=[27.4, -31.6], r=1.5, do='use', verb='look at the copier',
             think='An office at night. Somebody\'s still working. Somebody\'s always still working.',
             say=[line('コピー機', '(ガガガ…)「今夜:チーム懇親会。スクランブル交差点で相撲。ベルト持参。— 部長」', '(whirr...) "TONIGHT: team bonding. SUMO on the scramble crossing. Bring the belt. — The Boss."'),
                  line('', '…会社の懇親会で、俺のまわしを締める気か。', '...He\'s going to wear MY mawashi to his office party.')]),
    ],
    boss=dict(name='BUCHOYAMA', jp='部長山', at=[0.0, -19.5], belt='#2c3550', seen='The boss. Necktie on. MY mawashi over his suit trousers.',
              intro=[line('部長山', 'おや、残業か?', 'Oh? Working late?'),
                     line('部長山', 'このベルトか。いい締め心地だ。欲しければ…', 'This belt? Very comfortable. If you want it...'),
                     line('部長山', '交差点で、一番勝負だ。信号が変わる前にな。', '...one bout. On the crossing. Before the lights change.')],
              lost=[line('部長山', '甘いな。もう一番!', 'Too soft. Again!')],
              won=[line('部長山', '…見事だ。君、うちの会社に来ないか?', '...Splendid. Have you thought about a career in sales?'),
                   line('', '…まわしを返してくれ。', '...Just give me the mawashi.'),
                   line('部長山', 'ほら。…ところで、背中の「半額豆腐」は何だね?', 'Here. ...By the way, what\'s the "HALF-PRICE TOFU" on your back?')]),
    exit=[0.0, -55.0],
)

# ---------------------------------------------------------------------------------------------------------------- prototypes the game clones
m = LV.proto('ITEM_CART')   # a konbini delivery trolley (1.3 x 0.9): a wire cage on wheels with a few crates
m.gbox(-0.62, 0.62, -0.42, 0.42, 0.12, 0.18, 'steel'); m.gbox(-0.62, 0.62, -0.42, -0.38, 0.18, 1.05, 'steel'); m.gbox(-0.62, 0.62, 0.38, 0.42, 0.18, 1.05, 'steel'); m.gbox(-0.62, -0.58, -0.42, 0.42, 0.18, 1.05, 'steel')
m.gbox(-0.55, 0.1, -0.35, 0.35, 0.18, 0.55, 'blue', bev=0.03); m.gbox(-0.5, 0.05, -0.32, 0.32, 0.55, 0.85, 'yellow', bev=0.03)
for x in (-0.5, 0.5):
    for z in (-0.32, 0.32): m.gcyl(x, z, 0.0, 0.07, 0.12, 'charcoal', seg=8)
m.gbox(0.6, 0.66, -0.4, 0.4, 0.95, 1.0, 'charcoal')
m = LV.proto('MOVER_TRUCK')   # a small delivery truck (length along x)
m.gbox(-2.2, 0.9, -1.0, 1.0, 0.45, 2.6, 'offwhite', bev=0.06); m.gbox(0.9, 2.2, -0.95, 0.95, 0.45, 1.9, 'blue', bev=0.08)
m.gbox(1.6, 2.21, -0.8, 0.8, 1.15, 1.75, 'glass'); m.sign(-0.65, 1.7, 1.01, 2.6, 0.5, 'green', '+z'); m.sign(-0.65, 1.7, -1.01, 2.6, 0.5, 'green', '-z')
for x in (-1.5, 1.4):
    for z in (-0.95, 0.95): m.gcyl(x, z, 0.38, 0.38, 0.3, 'black', seg=14, axis='Y')
m.gbox(2.18, 2.22, -0.7, -0.45, 0.7, 0.9, 'lamp'); m.gbox(2.18, 2.22, 0.45, 0.7, 0.7, 0.9, 'lamp')

LV.export()
