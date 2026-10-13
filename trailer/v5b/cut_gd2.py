# cut_gd2.py [OUT.mp4] [--dry] : cut_gd.py (Go Down) kept whole, plus the campaign gachas from the stealth level:
# the machine pull and vanish in the sneaking section, the trap door and the sleep dart in the action, time drag, smoke
# and rewind in the breakdown, and on the beat-160 drop a gacha rampage (phantom dash, torpedo, daruma, giant, stomp,
# thousand hands, consume and spit, bomb, belly flop); the face-off collides on the beat-204 break.
# (was cut_pop.py) the action trailer, cut to DaBaby - Pop Dat Thang (DJ Sliink Jersey club remix),
# 137.6 BPM (beat 0.436 s from the 14.38 s drop). The song starts at 11.30 s: the Look Twice logo over "hey Sliink";
# on the drop the booty on the mound: left stomp, right stomp (two beats apart, on the beat), then the squat. Then short
# cuts, one action each, every action and every cut on the beat: asleep and the startle, the bucket thrown, the slip,
# the stool thrown to distract, the charge, knock, hide (laundry flies), the box pushed, the pop, the slap, the cart
# dive, the bucket KO, the slap, the bucket smashed, the slip, the vending machine (thumps on the beat, the crash),
# the can smashed and the slip; then the gacha and the fights through the breakdown; the face-off collides on the
# 54.91 hit: BIGGER IS BETTER, COMING SOON, and the booty squats once more.
import sys, os, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); TR = os.path.dirname(HERE); V5C = os.path.join(TR, 'v5c')
args_ = [a for a in sys.argv[1:] if not a.startswith('--')]
out = args_[0] if args_ else os.path.join(V5C, 'trailer_godown_gacha.mp4')
MUSIC = '/Users/don/Soulseek Downloads/003. Go Down (Big Freedia, SOPHIE).mp3'
FPS = 30; OFF = 0.0; BT = 0.47730; DROP = 0.310 + 4 * BT; COLLIDE = 0.310 + 204 * BT   # Go Down: beat 0.310 + k*0.4773 (125.7 BPM), downbeats k%4==0; the face-off collides on the 97.68 break (beat 204)
def bafter(s): return DROP + math.ceil((s - DROP) / BT - 1e-6) * BT          # song time -> next beat at or after
def frames(d): return len([f for f in os.listdir(os.path.join(V5C, d)) if f.startswith('f_')])
def logl(n): return [l.split() for l in open(os.path.join(V5C, n + '.log')) if l.strip()]
def first(n, pred): return next(int(l[0]) for l in logl(n) if pred(l))
def gev(n, key, idx=0):
    p = os.path.join(V5C, 'g5_' + n + '.log'); p = p if os.path.exists(p) else os.path.join(V5C, n + '.log')
    return [int(l.split()[0]) for l in open(p) if key in l][idx]
def gk(n, pred, off=0): return next(int(l[0]) for l in logl(n) if pred(l)) + off
def downs(l): return int(l[2][1:])
def knock(n, k=1): return gk(n, lambda l: downs(l) >= k)          # the k-th one down
def press(sec): return round((sec - 0.367) * FPS)                    # a press at script time sec (see v3/takes.js: t-=0.6)
E = []
def put(d, st, n, note=''):
    st, n = int(st), int(n); assert st >= 0 and n > 0 and st + n <= frames(d), f'{d}: {st}+{n} > {frames(d)}'
    E.append(dict(d=d, st=st, n=n, note=note))

# ---- the open (song time S; video time = S - OFF)
BL = [int(l[0]) for l in logl('booty_lrs2') if l[1] == 'stomp' and l[2] == '0']     # the two landings (left, right)
L1 = DROP + 2 * BT                                                                    # left lands two beats after the drop
bst = BL[0] - round((L1 - DROP) * FPS); bend = DROP + 8 * BT
put('booty_lrs2', bst, round((bend - DROP) * FPS), 'the booty: left stomp, right stomp, squat')
S = bend

# ---- the action, in sections of the song: each group fills its section, every event and cut on a beat
W = logl('wake7'); WT = [int(l[0]) for l in W if l[2] == 'throw' and l[3] == 'busy']
def bt(n): return DROP + n * BT
def W1(key): return first('wake7', key)
SHV = lambda f: first('shove4', f)
G1 = [('wake7', W1(lambda l: l[3] == 'gasp'), 0.9, 0.5, 0.8, 'asleep in the bath; the startle'),
      ('wake7', WT[0], 0.6, 0.5, 0.5, 'the bucket thrown: a puddle'),
      ('wake7', W1(lambda l: l[3] == 'slip'), 0.6, 0.5, 0.5, 'dashes and slips'),
      ('wake7', WT[-1], 0.5, 0.8, 0.4, 'the stool thrown to distract'),
      ('chargeko2', first('chargeko2', lambda l: '2KO' in l), 0.8, 0.5, 0.7, 'one charge, two down')]
CS = lambda f: first('cartko', f); CM = [int(l[0]) for l in logl('chasemaw') if l[1] == 'st2' and l[2] == 'busy'][0]; CM3 = [int(l[0]) for l in logl('chasemaw') if '3down' in ' '.join(l)][0]
SH2 = SHV(lambda l: l[1] == 'st2'); SHK = SHV(lambda l: any(w.endswith('KO') for w in l))
# one continuous shot for each scene (no jump cuts inside a scene): the anchor is its last big moment; the min lead keeps its first one in
G2 = [('gpull', gk('gpull', lambda l: 'used' in l), 1.4, 1.0, 1.2, 'he walks up to the hopping gacha machine and pulls it'),
      ('follow9', 236, 1.6, 1.4, 1.5, 'in the box: the cone sweeps over him'),
      ('gvanish', press(0.85) + 30, 1.0, 1.2, 0.9, 'vanish: he walks right through the cone'),
      ('knock8', first('knock8', lambda l: 'H1' in l), 1.0, 1.8, 0.9, 'knock knock, into the cart; they come and search'),
      ('shove4', SHK, 0.5, 0.6, (SHK - SH2) / FPS + 1.4, 'the attendant strains at the box; SURPRISE; the slap (one shot)'),
      ('gsleepdart', knock('gsleepdart'), 0.9, 1.0, 0.8, 'sleep dart: out like a light')]
G3 = [('cartdive', first('cartdive', lambda l: 'H1' in l), 0.9, 0.7, 0.8, 'pushes the cart and dives in, laundry flies'),
      ('cartko', CS(lambda l: '11KO' in l), 0.5, 0.6, (CS(lambda l: '11KO' in l) - CS(lambda l: '12KO' in l)) / FPS + 0.7, 'bucket to the head, then the slap (one shot)'),
      ('chasemaw', CM3, 0.3, 1.0, (CM3 - CM) / FPS + 0.6, 'the water bucket smashed, they slip (one shot)'),
      ('vend23', first('vend23', lambda l: 'brk1' in l), 1.8, 1.6, 1.7, 'thump, thump, KRRASH: cans spin and spray'),
      ('vend21', [int(l[0]) for l in logl('vend21') if '1down' in ' '.join(l)][0], 0.9, 1.2, 0.8, 'a can smashed at his feet: the attendant slips')]
G4 = [('gsmoke', gk('gsmoke', lambda l: True, 40), 1.2, 1.8, 1.0, 'smoke bomb as they close in: they run in blind, coughing'),
      ('gtimedrag', gk('gtimedrag', lambda l: l[1] == 'timedrag'), 0.8, 2.6, 0.6, 'time drag: he slips past them in slow motion and away'),
      ('grewind', gk('grewind', lambda l: 'rew' in l), 1.0, 1.6, 0.9, 'charges, slips on the puddle: REWIND, and round it')]
G5 = [('gtrapdoor', knock('gtrapdoor'), 1.2, 0.6, 1.0, 'trap door: the one chasing him drops through'),
      ('gphantom', knock('gphantom'), 0.8, 0.6, 0.7, 'phantom dash through the three of them'),
      ('gtorpedo', knock('gtorpedo'), 0.9, 0.6, 0.8, 'torpedo down the aisle'),
      ('gdaruma', knock('gdaruma', 2), 1.0, 0.8, 0.8, 'daruma roll'),
      ('ggiant', knock('ggiant'), 1.4, 0.8, 1.2, 'giant: they bounce off him'),
      ('gstomp', knock('gstomp'), 1.2, 0.8, 1.0, 'stomp as they close in from both sides'),
      ('ghands', knock('ghands'), 0.7, 1.0, 0.6, 'thousand hands'),
      ('gbomb', knock('gbomb'), 2.0, 0.9, 1.8, 'bomb: dropped, and they run into it')]
G6 = [('fb1', gev('fb1', 'perfectDodge'), 0.9, 2.8, 0.8, 'a perfect dodge (held after it, so you see him come round)'),
      ('fb4', gev('fb4', 'throw 1'), 0.9, 0.6, 0.6, 'the boss throws him'),
      ('g5_c_smokespin', gev('c_smokespin', 'skillUse 1'), 0.4, 1.4, 0.2, 'smoke on a spinning ring'),
      ('g5_unplug', gev('unplug', 'skillUse'), 0.2, 1.2, 0.1, 'controller disconnected'),
      ('g5_train', gev('train', 'trainHit'), 0.8, 0.5, 0.6, 'shinkansen'),
      ('g5_c_tripball', gev('c_tripball', 'ballHit'), 0.8, 0.6, 0.6, 'triplets vs daruma'),
      ('g5_c_shockcyc', gev('c_shockcyc', 'bigStomp'), 0.5, 1.2, 0.4, 'stomp vs cyclone'),
      ('g5_banana', gev('banana', ' slip '), 0.6, 0.4, 0.5, 'banana'),
      ('g5_c_giantchick', gev('c_giantchick', 'skillUse 0'), 0.8, 1.0, 0.6, 'giant, then chicken'),
      ('g5_claw', gev('claw', 'clawDrop'), 1.6, 0.4, 1.4, 'the claw'),
      ('g5_potato3', gev('potato3', 'boom 1'), 1.0, 0.5, 5.0, 'hot potato: passed back and forth, then BOOM'),
      ('fb8', gev('fb8', 'throw 0'), 0.9, 0.6, 0.6, 'he catches the charge and throws the boss'),
      ('g5_c_torprew', gev('c_torprew', 'rewind 0'), 0.8, 0.7, 0.6, 'torpedo, rewind')]
VS = lambda d: d.startswith('g5_') or d.startswith('fb') or d == 'fin'   # the sumo fights: zoomed in on the ring (see ZOOM)
ZOOM = 1.4
FL = open(os.path.join(V5C, 'fin.log')).read().split('\n'); CONTACT = next(int(l.split()[1]) for l in FL if l.startswith('CONTACT'))
fin_start = bafter(COLLIDE - (CONTACT - 96) / FPS) - BT
def lay(A, S0, k, commit, endt):
    s = S0
    for i, (d, h, lead, tail, ml, note) in enumerate(A):
        hb = bafter(s + max(lead * k, ml)); st = h - round((hb - s) * FPS); end = bafter(hb + tail * k)
        if commit:
            if i == len(A) - 1: end = endt
            n = min(round((end - s) * FPS), frames(d) - max(0, st)); put(d, max(0, st), n, note); s += n / FPS
        else: s = end
    return s
KS = []
for A, endt in [(G1, bt(24)), (G2, bt(60)), (G3, bt(88)), (G4, bt(108)), (G5, bt(140)), (G6, fin_start)]:
    lo, hi = 0.2, 4.0
    for _ in range(40):
        k = (lo + hi) / 2
        if lay(A, S, k, False, endt) > endt: hi = k
        else: lo = k
    KS.append(round(lo, 2)); S = lay(A, S, lo, True, endt)
    if abs(S - endt) > 0.02: E[-1]['n'] += round((endt - S) * FPS); S = endt
k = KS
fst = CONTACT - round((COLLIDE - S) * FPS)   # (ends on the frame before the game's one-frame impact flash)
put('fin', fst, round((COLLIDE - S) * FPS), 'salt, clap, the boss stomps, both charge: cut as they collide'); S = COLLIDE

# ---- the end: BIGGER IS BETTER on the 54.91 hit, COMING SOON 4 beats later, then the booty squats once more
C1 = round((bafter(COLLIDE + 1.6) - COLLIDE) * FPS); SOON = COLLIDE + C1 / FPS
C2 = round((bafter(SOON + 1.6) - SOON) * FPS); BUT = SOON + C2 / FPS
EL = 100   # booty_bow: arms wide (36), belt slap (56), the bow (78), the mawashi drops and the censor pops up (100)
land = bafter(BUT + (EL - 30) / FPS); b2st = EL - round((land - BUT) * FPS); b2n = round((bafter(land + 1.3) - BUT) * FPS)
total = BUT + b2n / FPS - OFF; LOGO_S = DROP - OFF

args = ['-loop', '1', '-framerate', str(FPS), '-t', f'{LOGO_S + 0.1:.3f}', '-i', os.path.join(TR, 'cards/logo2_sharp.png')]
fl = [f'[0:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={round(LOGO_S * FPS)},setpts=PTS-STARTPTS[v0]']
segs = E + [dict(d='booty_bow', st=b2st, n=b2n, note='button')]
for i, s in enumerate(segs, 1):
    args += ['-framerate', str(FPS), '-start_number', str(s['st']), '-i', os.path.join(V5C, s['d'], 'f_%04d.jpg')]
    zc = f"crop=iw/{ZOOM}:ih/{ZOOM}:(iw-ow)/2:ih*0.585-oh/2," if VS(s['d']) else ''
    fl.append(f"[{i}:v]trim=end_frame={s['n']},setpts=PTS-STARTPTS,{zc}scale=1280:720:flags=lanczos,setsar=1,format=yuv420p[v{i}]")
n = len(segs) + 1
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C1 / FPS + 0.1), '-i', os.path.join(V5C, 'bigger.png')]
fl.append(f'[{n}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C1},setpts=PTS-STARTPTS[vc]')
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C2 / FPS + 0.1), '-i', os.path.join(V5C, 'soon.png')]
fl.append(f'[{n + 1}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C2},setpts=PTS-STARTPTS[vd]')
fl.append('[v0]' + ''.join(f'[v{i}]' for i in range(1, n - 1)) + f'[vc][vd][v{n - 1}]concat=n={n + 2}:v=1:a=0[cat]')
ov_in = LOGO_S; ov_out = bend - OFF - 0.45
args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', os.path.join(HERE, 'title_booty1280.png')]
fl.append(f'[{n + 2}:v]format=rgba,fade=t=in:st={ov_in:.3f}:d=0.25:alpha=1,fade=t=out:st={ov_out:.3f}:d=0.35:alpha=1[title]')
fl.append(f"[cat][title]overlay=0:0:format=auto:enable='between(t,{ov_in:.3f},{ov_out + 0.4:.3f})',format=yuv420p[o]")
args += ['-i', MUSIC]
fl.append(f'[{n + 3}:a]atrim=end={total:.3f},afade=t=out:st={total - 0.7:.3f}:d=0.7[a]')
t = 0; print(f'{t:6.2f} (song {OFF:.2f})  Look Twice logo')
t = LOGO_S
for s in E: print(f"{t:6.2f} (song {t + OFF:6.2f})  {s['d']:<16} {s['st']:>5}+{s['n']:<4} {s['note']}"); t += s['n'] / FPS
print(f'{COLLIDE - OFF:6.2f}  BIGGER IS BETTER   {SOON - OFF:.2f} COMING SOON   {BUT - OFF:.2f} booty bow, mawashi drops   end {total:.2f}   (stretch {k})')
if '--dry' in sys.argv: sys.exit()
subprocess.run(['ffmpeg', '-y', '-v', 'error'] + args + ['-filter_complex', ';'.join(fl), '-map', '[o]', '-map', '[a]', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip(), out)
