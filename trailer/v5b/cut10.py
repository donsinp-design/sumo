# cut10.py [OUT.mp4] : showcase v5, sixth pass (wake6, chargeko2, cartdive, potato3, no inhale, cut on the collision)
# was cut9.py: fifth pass (shove4: real 2 s strain; vend20: prints seen first; chargeko back; bumper bounce)
# was cut8.py: fourth pass (v5c frames: the owner's cloud flicker fixes, combined gacha, two end cards)
# was cut7.py: third pass (no ring zoom, no boss highlights: the gacha run straight into the finale).
# was cut6.py: Built from the owner's description of v4 plus the v5 notes.
# Frames: trailer/v5/<take> (first pass) and trailer/v5b/<take> (re-recorded). All frames are 2560x1440 (SS=2).
#  - room scenes are scaled down whole; ring scenes (gacha, boss, finale) use the old ring crop (single.py's, at 2x)
#  - every cut is snapped to a strong hit in music/modena.ogg (onsets.json); the COMING SOON card lands on the
#    2:08.9 hit just before the phrase ends (last chord 2:09.5), and the music is let ring out and faded after it
#  - food rain dissolves into the bath; the title fades in on the 7.9 s hit (his startle) and out as he climbs out
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); TR = os.path.dirname(HERE); V5 = os.path.join(TR, 'v5'); V5C = os.path.join(TR, 'v5c')
out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(V5C, 'showcase_v5.mp4')
FPS = 30; CARD_T = 128.89; CARD_LEN = 3.0; DISS = 0.5
ON = json.load(open(os.path.join(HERE, 'onsets.json')))
CARD2_T = 130.64   # the next strong hit: COMING SOON
RING = None   # (no zoom: the game's own camera)
def src(d): return os.path.join(V5C, d)   # (everything re-recorded on the new build)


def logl(name): return [l.split() for l in open(os.path.join(V5C, name + '.log')) if l.strip()]
WAKE_N = next(int(l[0]) for l in logl('wake6') if len(l) > 1 and l[2] == 'end') + 12 - 15
SH = logl('shove4'); KO = next(int(l[0]) for l in SH if any(w.endswith('KO') for w in l)); SHOVE_ST = max(0, next(int(l[0]) for l in SH if 'PUSH' in ' '.join(l)) - 14); SHOVE_N = KO + 10 - SHOVE_ST
CR = logl('cartdive'); stop = next((int(CR[k][0]) for k in range(20, len(CR) - 4) if all(CR[k][3] == CR[k + j][3] for j in range(1, 5))), 150); CART_N = stop + 6 - 8
FL = [l for l in open(os.path.join(V5C, 'fin.log'))]; FIN_END = next(int(l.split()[1]) for l in FL if l.startswith('CONTACT')) + 1   # (cut on the frame they collide)
WL = logl('wake6'); GASP = next(int(l[0]) for l in WL if len(l) > 3 and l[3] == 'gasp'); OUTB = next(int(l[0]) for l in WL if l[1] == 'i2')
print('wake', WAKE_N, 'shove', SHOVE_ST, SHOVE_N, 'cart', CART_N, 'fin end', FIN_END)
# (dir, first frame, seconds wanted, speed, ring crop?, note). Seconds are snapped to a hit; None = exact frames given in 'n'
S = []
def seg(d, st, sec, speed=1, ring=False, note='', snap=True, nf=None): S.append(dict(d=d, st=st, sec=sec, sp=speed, ring=ring, note=note, snap=snap, nf=nf))
seg('food', 0, 3.1, note='food rain (dissolves into him asleep in the bath)', snap=False)
seg('wake6', 15, WAKE_N / 30, note='ONE take, steered like a person: asleep, startle, bucket, puddle, slip, locker room, stool, tiptoe, locked locker')
seg('chargeko2', 2, 2.2, note='down the locker aisle at a charge: one charge bowls over both attendants')
seg('knock8', 40, 5.3, note='knocks on the wall, hides in the cart; the attendant comes and searches')
seg('shove4', SHOVE_ST, SHOVE_N / 30, note='the attendant strains and sweats pushing the box for 2 s; he jumps out, they jump; slap: out cold', snap=False)
seg('follow9', 140, 4.6, note='the box follows; the cone passes over it once')
seg('cartdive', 8, 2.8, note='pushes the cart into the laundry and dives in on the move: it rolls on, towels fly out', nf=84)
seg('cartko', 20, 4.3, note='out of the cart, bucket to the back of the head, then a slap KO')
seg('chasemaw', 40, 5.5, note='chased with the bucket: smashes it, two of them slip')
seg('vend20', 40, 9.9, note='tiptoes through a puddle (footprints); the attendant sees the prints and follows; thump thump KRRASH, cans roll, one sprays; he runs in; can smashed: he slips')
# gacha: singles and pairs (one skill each side)
GACHA0 = len(S)
seg('g5_banana', 8, 1.6, ring=True)
seg('g5_c_tripball', 4, 2.4, ring=True, note='triplets vs daruma')
seg('g5_train', 60, 1.6, ring=True)
seg('g5_c_giantchick', 2, 3.3, ring=True, note='the boss goes giant; he turns him into a chicken')
seg('g5_claw', 76, 2.1, ring=True, nf=74, note='the claw grabs him, lifts him off and drops him out')
seg('g5_c_shockcyc', 6, 3.0, ring=True, note='his stomp vs the boss\'s cyclone')
seg('g5_c_bumpflop3', 22, 2.5, ring=True, note='belly flop (already in the air) throws him into the straw; the bumper ring throws him back in')
seg('g5_potato3', 24, 4.6, ring=True, note='hot potato tag: whoever has the bomb charges, the other dodges; it blows on the boss')
seg('g5_c_smokespin', 2, 3.0, ring=True, note='smoke bomb (the boss\'s view: a solid wall) on a spinning ring')
seg('g5_unplug', 2, 1.7, ring=True)
seg('g5_c_torprew', 22, 2.4, ring=True, note='the boss torpedoes him out; rewind fires by itself')
BOSS0 = GACHA0
FIN = dict(d='fin', st=None, contact=FIN_END, sec=(FIN_END - 92) / 30, ring=True, note='finale: salt, clap, the boss stomps; cut as they charge')

def snap(t, lo=0.4):
    best = None
    for tt, s in ON:
        if abs(tt - t) <= lo and s >= 30:
            sc = abs(tt - t) - s / 400
            if best is None or sc < best[0]: best = (sc, tt)
    return best[1] if best else t

# lay out: logo 2.2 s, food, (dissolve) wake ... ; the boss clips stretch/shrink so the finale ends on CARD_T
LOGO = 66
t = LOGO / FPS
fin_start = snap(CARD_T - FIN['sec'])
def lay(i, t):
    s = S[i]
    if s.get('nf'): s['n'] = s['nf']; s['t'] = t; return t + s['nf'] / FPS
    end = t + s['sec']
    if s['snap'] and i != len(S) - 1: end = snap(end)
    have = len([f for f in os.listdir(src(s['d'])) if f.startswith('f_')])
    n = int(round((end - t) * FPS)); n = min(n, (have - s['st']) // s.get('sp', 1))
    if i < len(S) - 1 and n < int(round((end - t) * FPS)):   # out of footage: stop on the last hit before it runs out
        e2 = t + n / FPS; cand = [tt for tt, st in ON if st >= 30 and t + 0.8 < tt <= e2]; n = int((cand[-1] - t) * FPS) if cand else n
    s['n'] = n; s['t'] = t; return t + n / FPS
for i in range(BOSS0):
    if i == 1: t -= DISS   # the wake starts under the food's last half second
    t = lay(i, t)
t0 = t; base = [s['sec'] for s in S[BOSS0:]]; k = (fin_start - t0) / sum(base)
for it in range(60):   # stretch/shrink the gacha run so the finale starts just before the salt (frame ~92 of fin)
    for s_, b in zip(S[BOSS0:], base): s_['sec'] = b * k
    t = t0
    for i in range(BOSS0, len(S)): t = lay(i, t)
    fst = FIN['contact'] - int(round((CARD_T - t) * FPS))
    if 86 <= fst <= 95: break
    k *= 0.996 if fst > 95 else 1.004
print(f'gacha clips scaled x{k:.2f}')
FIN['n'] = int(round((CARD_T - t) * FPS)); FIN['t'] = t; FIN['st'] = FIN['contact'] - FIN['n']
ALL = S + [FIN]

for s in ALL:
    have = len([f for f in os.listdir(src(s['d'])) if f.startswith('f_')])
    need = s['st'] + s['n'] * s.get('sp', 1)
    assert need <= have, f"{s['d']} needs frames up to {need}, has {have}"
args = ['-loop', '1', '-framerate', str(FPS), '-t', str(LOGO / FPS + 0.1), '-i', os.path.join(TR, 'cards/logo2_sharp.png')]
fl = [f'[0:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={LOGO},setpts=PTS-STARTPTS[v0]']
for i, s in enumerate(ALL, 1):
    n, sp = s['n'], s.get('sp', 1)
    args += ['-framerate', str(FPS), '-start_number', str(s['st']), '-i', f"{src(s['d'])}/f_%04d.jpg"]
    crop = ''
    speed = f',setpts=PTS/{sp}' if sp != 1 else ''
    fi = ',fade=t=in:s=0:n=12:color=white' if s['d'] == 'food' else ''
    fl.append(f"[{i}:v]trim=end_frame={n * sp},setpts=PTS-STARTPTS{speed},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,{crop}scale=1280:720:flags=lanczos,setsar=1,format=yuv420p{fi}[v{i}]")
nin = len(ALL) + 1
C1 = int(round((CARD2_T - CARD_T) * FPS)); C2 = int(round(CARD_LEN * FPS))
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C1 / FPS + 0.1), '-i', os.path.join(V5C, 'bigger.png')]
CI = nin; fl.append(f'[{CI}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C1},setpts=PTS-STARTPTS[vc]')
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C2 / FPS + 0.1), '-i', os.path.join(V5C, 'soon.png')]
CI += 1; fl.append(f'[{CI}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C2},setpts=PTS-STARTPTS[vd]')
# food -> wake dissolve
fl.append(f"[v1][v2]xfade=transition=fade:duration={DISS}:offset={S[0]['n'] / FPS - DISS:.3f}[vfw]")
chain = '[v0][vfw]' + ''.join(f'[v{i}]' for i in range(3, nin)) + '[vc][vd]'
fl.append(f'{chain}concat=n={nin + 1}:v=1:a=0[cat]')
total = CARD2_T + CARD_LEN
# title: in on the startle hit, out as he climbs out of the bath (wake4 frame ~262)
w = S[1]; ov_in = w['t'] + (GASP - w['st']) / FPS; ov_out = w['t'] + (OUTB - w['st']) / FPS - 0.6
TI = CI + 1; args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', os.path.join(HERE, 'title1280.png')]
fl.append(f'[{TI}:v]format=rgba,fade=t=in:st={ov_in:.3f}:d=0.6:alpha=1,fade=t=out:st={ov_out:.3f}:d=0.8:alpha=1[title]')
fl.append(f"[cat][title]overlay=0:0:format=auto:enable='between(t,{ov_in:.3f},{ov_out + 0.9:.3f})',format=yuv420p[o]")
# music: from the start; after the card's hit the last chord rings, then a gentle fade into silence
AI = TI + 1; args += ['-i', os.path.join(TR, 'music/modena.ogg')]
fl.append(f'[{AI}:a]atrim=end={total:.3f},afade=t=out:st={CARD2_T + 0.5:.3f}:d={CARD_LEN - 0.6:.3f}[a]')
cmd = ['ffmpeg', '-y', '-v', 'error'] + args + ['-filter_complex', ';'.join(fl), '-map', '[o]', '-map', '[a]', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', out]
print(f"{0:7.2f}  logo")
for s in ALL: print(f"{s['t']:7.2f}  {s['d']:<13} from {s['st']:>5}  {s['n']:4d}f x{s.get('sp', 1)}  {s.get('note', '')}")
print(f'{CARD_T:7.2f}  BIGGER IS BETTER, {CARD2_T:.2f} COMING SOON   title {ov_in:.2f}-{ov_out:.2f}   total {total:.2f}')
if '--dry' in sys.argv: sys.exit()
subprocess.run(cmd, check=True)
print(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip(), out)
