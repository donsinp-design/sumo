# cut_thick.py [OUT.mp4] [--dry] : the action trailer (no showcase), cut to DJ Chose & Beatking - THICK
# (96.5 BPM, beat 0.622 s). Look Twice logo; the booty stomping on the mound (BIG BOY SUMO fades in on the first
# stomp, the third lands on the 6.8 s hit); asleep in the bath, the startle on the 8.88 hit, out at a charge; then the
# action: slips, charges, throws, hiding, surprises, slaps, the gacha chaos and the fights, every hit and every cut on
# the beat; the face-off collides on the 59.05 hit: BIGGER IS BETTER, COMING SOON, and the booty stomps once more.
import sys, os, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); TR = os.path.dirname(HERE); V5C = os.path.join(TR, 'v5c')
args_ = [a for a in sys.argv[1:] if not a.startswith('--')]
out = args_[0] if args_ else os.path.join(V5C, 'trailer_thick.mp4')
MUSIC = '/Users/don/Soulseek Downloads/DJ Chose & Beatking - THICK (Dirty).mp3'
FPS = 30; B0 = 0.145; BT = 0.622
STOMP3 = 6.80; STARTLE = 8.88; OUT_CUT = 12.19; COLLIDE = 59.05
def bafter(t): return B0 + math.ceil((t - B0) / BT - 1e-6) * BT
def frames(d): return len([f for f in os.listdir(os.path.join(V5C, d)) if f.startswith('f_')])
def logl(n): return [l.split() for l in open(os.path.join(V5C, n + '.log')) if l.strip()]
def first(n, pred): return next(int(l[0]) for l in logl(n) if pred(l))
def gev(n, key, idx=0):
    p = os.path.join(V5C, 'g5_' + n + '.log'); p = p if os.path.exists(p) else os.path.join(V5C, n + '.log')
    return [int(l.split()[0]) for l in open(p) if key in l][idx]

E = []
def put(d, st, n, note=''):
    st, n = int(st), int(n); assert st >= 0 and n > 0 and st + n <= frames(d), f'{d}: {st}+{n} > {frames(d)}'
    E.append(dict(d=d, st=st, n=n, note=note))

# ---- the open
BS = [int(l[0]) for l in logl('booty_stomp') if l[1] == 'stomp']          # landing frames of the three stomps
LOGO_S = STOMP3 - (BS[2] - 0) / FPS                                        # booty clip from frame 0, third stomp on 6.8
b_end = 7.3
put('booty_stomp', 0, round((b_end - LOGO_S) * FPS), 'the booty on the mound: stomp, stomp, STOMP on the 6.8 hit')
t = LOGO_S + E[-1]['n'] / FPS
GASP = first('wake7', lambda l: l[3] == 'gasp')
wst = GASP - round((STARTLE - t) * FPS)
put('wake7', wst, round((OUT_CUT - t) * FPS), 'asleep; ええっ!? on the 8.88 hit; out of the bath'); t = OUT_CUT

# ---- the action: each clip's big moment on a beat at least `lead` s in, the cut on a beat at least `tail` s after
W = logl('wake7')
SLIP = first('wake7', lambda l: l[3] == 'slip'); STOOL = [int(l[0]) for l in W if l[2] == 'throw' and l[3] == 'busy'][-1]
A = [('wake7', SLIP, 0.8, 0.7, 'dashes at the puddle and slips'),
     ('chargeko2', first('chargeko2', lambda l: '2KO' in l), 0.9, 0.5, 'one charge, two attendants down'),
     ('wake7', STOOL, 0.7, 0.6, 'the stool thrown up the room'),
     ('knock8', first('knock8', lambda l: 'H1' in l), 1.2, 0.8, 'knock knock: into the cart, laundry flies'),
     ('shove4', first('shove4', lambda l: any(w.endswith('KO') for w in l)), 2.6, 0.4, 'the box shoved, he stands up, they jump: slap', 2.4),
     ('cartdive', first('cartdive', lambda l: 'H1' in l), 1.2, 0.8, 'dives into the rolling cart'),
     ('cartko', first('cartko', lambda l: '11KO' in l), 2.6, 0.4, 'bucket to the head, then the slap', 2.4),
     ('chasemaw', [int(l[0]) for l in logl('chasemaw') if '3down' in ' '.join(l)][0], 2.0, 1.0, 'bucket smashed, two slip'),
     ('vend21', first('vend21', lambda l: '1down' in l and l[1] in ('st4', 'st5')), 3.4, 0.5, 'thump thump KRRASH, can smashed, slip', 3.7),
     ('g5_train', gev('train', 'trainHit'), 1.0, 0.5, 'shinkansen'),
     ('g5_c_tripball', gev('c_tripball', 'ballHit'), 1.0, 0.8, 'triplets vs daruma'),
     ('fb1', gev('fb1', 'perfectDodge'), 1.0, 0.6, 'a perfect dodge'),
     ('g5_c_giantchick', gev('c_giantchick', 'skillUse 0'), 1.0, 1.2, 'giant, then chicken'),
     ('g5_c_shockcyc', gev('c_shockcyc', 'bigStomp'), 0.6, 1.8, 'stomp vs cyclone'),
     ('g5_banana', gev('banana', ' slip '), 0.8, 0.4, 'banana'),
     ('fb4', gev('fb4', 'throw 1'), 1.4, 0.5, 'the boss throws him'),
     ('g5_c_bumpflop3', gev('c_bumpflop3', ' bump '), 1.4, 0.5, 'belly flop, bumper bounce'),
     ('g5_claw', gev('claw', 'clawDrop'), 2.2, 0.3, 'the claw', 2.5),
     ('g5_potato3', gev('potato3', 'boom 1'), 2.0, 0.4, 'hot potato'),
     ('g5_c_torprew', gev('c_torprew', 'rewind 0'), 1.0, 0.8, 'torpedo, rewind'),
     ('g5_c_smokespin', gev('c_smokespin', 'skillUse 1'), 0.4, 1.2, 'smoke on a spinning ring'),
     ('fb8', gev('fb8', 'throw 0'), 1.2, 0.5, 'he catches the charge and throws the boss'),
     ('g5_unplug', gev('unplug', 'skillUse'), 0.2, 1.2, 'controller disconnected')]
FL = open(os.path.join(V5C, 'fin.log')).read().split('\n'); CONTACT = next(int(l.split()[1]) for l in FL if l.startswith('CONTACT'))
fin_start = bafter(COLLIDE - (CONTACT + 1 - 92) / FPS) - BT
lo, hi = 0.3, 3.0
for _ in range(40):
    k = (lo + hi) / 2; tt = t
    for d, h, lead, tail, note, *ml in A: hb = bafter(tt + max(lead * k, ml[0] if ml else 0)); tt = bafter(hb + tail * k)
    if tt > fin_start: hi = k
    else: lo = k
k = lo
for i, (d, h, lead, tail, note, *ml) in enumerate(A):
    hb = bafter(t + max(lead * k, ml[0] if ml else 0)); st = max(0, h - round((hb - t) * FPS)); end = bafter(hb + tail * k)
    if i == len(A) - 1: end = fin_start
    n = min(round((end - t) * FPS), frames(d) - st); put(d, st, n, note); t += n / FPS
if abs(t - fin_start) > 0.02: E[-1]['n'] += round((fin_start - t) * FPS); t = fin_start
fst = CONTACT + 1 - round((COLLIDE - t) * FPS)
put('fin', fst, round((COLLIDE - t) * FPS), 'salt, clap, the boss stomps, both charge: cut as they collide'); t = COLLIDE

# ---- the end: BIGGER IS BETTER on 59.05, COMING SOON on the next bar, the booty stomps once more on the beat
C1 = round((bafter(COLLIDE + 2.2) - COLLIDE) * FPS); SOON_T = COLLIDE + C1 / FPS
C2 = round((bafter(SOON_T + 2.0) - SOON_T) * FPS); BUT_T = SOON_T + C2 / FPS
bland = bafter(BUT_T + (BS[1] - 60) / FPS); bst = BS[1] - round((bland - BUT_T) * FPS); bn = round((bafter(bland + 0.7) - BUT_T) * FPS)
total = BUT_T + bn / FPS

args = ['-loop', '1', '-framerate', str(FPS), '-t', f'{LOGO_S + 0.1:.3f}', '-i', os.path.join(TR, 'cards/logo2_sharp.png')]
fl = [f'[0:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={round(LOGO_S * FPS)},setpts=PTS-STARTPTS[v0]']
segs = E + [dict(d='booty_stomp', st=bst, n=bn, note='button')]
for i, s in enumerate(segs, 1):
    args += ['-framerate', str(FPS), '-start_number', str(s['st']), '-i', os.path.join(V5C, s['d'], 'f_%04d.jpg')]
    fl.append(f"[{i}:v]trim=end_frame={s['n']},setpts=PTS-STARTPTS,scale=1280:720:flags=lanczos,setsar=1,format=yuv420p[v{i}]")
n = len(segs) + 1
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C1 / FPS + 0.1), '-i', os.path.join(V5C, 'bigger.png')]
fl.append(f'[{n}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C1},setpts=PTS-STARTPTS[vc]')
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C2 / FPS + 0.1), '-i', os.path.join(V5C, 'soon.png')]
fl.append(f'[{n + 1}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C2},setpts=PTS-STARTPTS[vd]')
order = '[v0]' + ''.join(f'[v{i}]' for i in range(1, n - 1)) + '[vc][vd]' + f'[v{n - 1}]'
fl.append(f'{order}concat=n={n + 2}:v=1:a=0[cat]')
ov_in = LOGO_S + BS[0] / FPS; ov_out = b_end - 0.5
args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', os.path.join(HERE, 'title1280.png')]
fl.append(f'[{n + 2}:v]format=rgba,fade=t=in:st={ov_in:.3f}:d=0.3:alpha=1,fade=t=out:st={ov_out:.3f}:d=0.4:alpha=1[title]')
fl.append(f"[cat][title]overlay=0:0:format=auto:enable='between(t,{ov_in:.3f},{ov_out + 0.5:.3f})',format=yuv420p[o]")
args += ['-i', MUSIC]
fl.append(f'[{n + 3}:a]atrim=end={total:.3f},afade=t=out:st={total - 0.8:.3f}:d=0.8[a]')
tt = 0; print(f'{0:7.2f}  Look Twice logo')
tt = LOGO_S
for s in E: print(f"{tt:7.2f}  {s['d']:<16} {s['st']:>5}+{s['n']:<4} {s['note']}"); tt += s['n'] / FPS
print(f'{COLLIDE:7.2f}  BIGGER IS BETTER   {SOON_T:.2f} COMING SOON   {BUT_T:.2f} booty button (stomp {bland:.2f})   end {total:.2f}   (stretch x{k:.2f})')
if '--dry' in sys.argv: sys.exit()
subprocess.run(['ffmpeg', '-y', '-v', 'error'] + args + ['-filter_complex', ';'.join(fl), '-map', '[o]', '-map', '[a]', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip(), out)
