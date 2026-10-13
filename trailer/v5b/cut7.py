# cut7.py [OUT.mp4] : showcase v5, third pass (no ring zoom, no boss highlights: the gacha run straight into the finale).
# was cut6.py: Built from the owner's description of v4 plus the v5 notes.
# Frames: trailer/v5/<take> (first pass) and trailer/v5b/<take> (re-recorded). All frames are 2560x1440 (SS=2).
#  - room scenes are scaled down whole; ring scenes (gacha, boss, finale) use the old ring crop (single.py's, at 2x)
#  - every cut is snapped to a strong hit in music/modena.ogg (onsets.json); the COMING SOON card lands on the
#    2:08.9 hit just before the phrase ends (last chord 2:09.5), and the music is let ring out and faded after it
#  - food rain dissolves into the bath; the title fades in on the 7.9 s hit (his startle) and out as he climbs out
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); TR = os.path.dirname(HERE); V5 = os.path.join(TR, 'v5')
out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(HERE, 'showcase_v5.mp4')
FPS = 30; CARD_T = 128.89; CARD_LEN = 3.0; DISS = 0.5
ON = json.load(open(os.path.join(HERE, 'onsets.json')))
RING = None   # (no zoom: the game's own camera)
def src(d): return os.path.join(HERE, d) if os.path.isdir(os.path.join(HERE, d)) else os.path.join(V5, d)

# (dir, first frame, seconds wanted, speed, ring crop?, note). Seconds are snapped to a hit; None = exact frames given in 'n'
S = []
def seg(d, st, sec, speed=1, ring=False, note='', snap=True): S.append(dict(d=d, st=st, sec=sec, sp=speed, ring=ring, note=note, snap=snap))
seg('food', 0, 3.1, note='food rain (dissolves into the bath)', snap=False)
seg('wake4', 15, 1389 / 30, note='ONE take: asleep, startle on the 7.9 s hit, bucket, puddle, slip, locker room, stool, tiptoe, locked locker')
seg('knock8', 40, 5.3, note='knocks on the wall (コンコン), hides in the cart; the attendant comes, searches, leaves; nobody slips')
seg('shove2', 12, 2.6, note='the box gets shoved; he pops up; cut on the attendant\'s shock')
seg('follow9', 140, 4.6, note='the box follows; the cone passes over it once')
seg('cartrun', 8, 2.9, note='cart run (the game already pushes carts at double speed); cut as he arrives')
seg('cartko', 20, 4.3, note='out of the cart, bucket to the back of the head, then a slap KO')
seg('chasemaw', 40, 5.5, note='chased with the bucket: smashes it, two of them slip')
seg('vend12', 20, 8.3, note='thump thump KRRASH; slams a can down where the attendant runs in; he slips; drinks another can; burps')
# gacha singles (stretched together to fill up to the finale)
GACHA0 = len(S)
seg('g5_ball', 0, 1.3, ring=True)
seg('g5_banana', 8, 1.6, ring=True)
seg('g5_train', 60, 1.6, ring=True)
seg('g5_giant', 0, 1.3, ring=True)
seg('g5_chicken', 2, 1.3, ring=True)
seg('g5_claw', 62, 2.5, ring=True, note='the claw comes down, grabs him, lifts him off and drops him out')
seg('g5_inhale', 6, 1.6, ring=True)
seg('g5_potato', 56, 4.4, ring=True, note='hot potato tag: whoever has the bomb chases, the other runs; it blows on the boss')
seg('g5_torpedo', 8, 1.9, ring=True, note='backs off and launches flat across the ring')
seg('g5_bellyFlop', 2, 1.9, ring=True)
seg('g5_cyclone', 4, 2.0, ring=True)
seg('g5_bumper', 30, 1.4, ring=True)
seg('g5_triplets', 4, 1.3, ring=True)
seg('g5_shock', 8, 1.7, ring=True, note='stomp from a distance; the wave rolls into the boss')
seg('g5_rewind', 194, 1.6, ring=True, note='thrown out... rewind (no date on the VHS screen)')
seg('g5_smoke', 0, 1.3, ring=True)
seg('g5_unplug', 2, 1.7, ring=True, note='the CONTROLLER DISCONNECTED pop-up, bar filling')
seg('g5_spin', 20, 1.5, ring=True)
BOSS0 = GACHA0
FIN = dict(d='fin', st=None, contact=208, sec=4.3, ring=True, note='finale: salt, clap, the boss stomps, both charge; card just before they meet')

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
    s = S[i]; end = t + s['sec']
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
for it in range(30):   # stretch the gacha run until the finale starts after the boss's cage is off the ring (frame 76)
    for s, b in zip(S[BOSS0:], base): s['sec'] = b * k
    t = t0
    for i in range(BOSS0, len(S)): t = lay(i, t)
    fin_n = int(round((CARD_T - t) * FPS))
    if FIN['contact'] - fin_n >= 76 or it == 29: break
    k *= 1 + (76 - (FIN['contact'] - fin_n)) / FPS / sum(b * k for b in base) + 0.002
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
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(CARD_LEN + 0.1), '-i', os.path.join(TR, 'cards/soon_sharp.png')]
CI = nin; fl.append(f'[{CI}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={int(CARD_LEN * FPS)},setpts=PTS-STARTPTS[vc]')
# food -> wake dissolve
fl.append(f"[v1][v2]xfade=transition=fade:duration={DISS}:offset={S[0]['n'] / FPS - DISS:.3f}[vfw]")
chain = '[v0][vfw]' + ''.join(f'[v{i}]' for i in range(3, nin)) + '[vc]'
fl.append(f'{chain}concat=n={nin}:v=1:a=0[cat]')
total = CARD_T + CARD_LEN
# title: in on the startle hit, out as he climbs out of the bath (wake4 frame ~262)
w = S[1]; ov_in = w['t'] + (187 - w['st']) / FPS; ov_out = w['t'] + (280 - w['st']) / FPS - 0.6
TI = CI + 1; args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', os.path.join(HERE, 'title1280.png')]
fl.append(f'[{TI}:v]format=rgba,fade=t=in:st={ov_in:.3f}:d=0.6:alpha=1,fade=t=out:st={ov_out:.3f}:d=0.8:alpha=1[title]')
fl.append(f"[cat][title]overlay=0:0:format=auto:enable='between(t,{ov_in:.3f},{ov_out + 0.9:.3f})',format=yuv420p[o]")
# music: from the start; after the card's hit the last chord rings, then a gentle fade into silence
AI = TI + 1; args += ['-i', os.path.join(TR, 'music/modena.ogg')]
fl.append(f'[{AI}:a]atrim=end={total:.3f},afade=t=out:st={CARD_T + 0.75:.3f}:d={CARD_LEN - 0.95:.3f}[a]')
cmd = ['ffmpeg', '-y', '-v', 'error'] + args + ['-filter_complex', ';'.join(fl), '-map', '[o]', '-map', '[a]', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', out]
print(f"{0:7.2f}  logo")
for s in ALL: print(f"{s['t']:7.2f}  {s['d']:<13} from {s['st']:>5}  {s['n']:4d}f x{s.get('sp', 1)}  {s.get('note', '')}")
print(f'{CARD_T:7.2f}  COMING SOON   title {ov_in:.2f}-{ov_out:.2f}   total {total:.2f}')
if '--dry' in sys.argv: sys.exit()
subprocess.run(cmd, check=True)
print(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip(), out)
