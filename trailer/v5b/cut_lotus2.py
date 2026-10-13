# cut_lotus2.py [OUT.mp4] [--dry] : the second showcase, every cut and every big moment on the beat of
# Mura Masa - Lotus Eater (96.8 BPM: beat 0.622 s from 13.065 s).
#   intro (quiet)            logo, food rain, asleep in the bath
#   12.85  the beat arrives  he startles awake; the bath-to-locker take (wake7, its moments held to the beat by
#                            sync steps): charge out 16.8, bucket 21.8, slip on the 26.5 hit, charge 32.3, stool 38.6
#   54.74  the bridge        the locked locker rattles on the first downbeat; then the slow, sneaky scenes:
#                            knock & hide, the box following, the strain at the box, the pop and the slap
#   79.62  the drop          the vending machine smashes on it (vend21 thumps once a beat); then the action:
#                            can smash & slip, the charge, the cart dive, the cart KO, the bucket chase, the gacha
#   ~105   the outro         the rest of the gacha; the face-off; they collide on the 126.07 hit: BIGGER IS BETTER,
#                            COMING SOON on 128.81, and the song plays out
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); TR = os.path.dirname(HERE); V5C = os.path.join(TR, 'v5c')
args_ = [a for a in sys.argv[1:] if not a.startswith('--')]
out = args_[0] if args_ else os.path.join(V5C, 'showcase_lotus.mp4')
MUSIC = '/Users/don/Soulseek Downloads/04 Mura Masa - Lotus Eater.mp3'
FPS = 30; B0 = 13.065; BT = 0.622
STARTLE = 12.85; DROP = 79.62; COLLIDE = 126.07; SOON = 128.81; CARD_LEN = 3.7; LOGO_S = 3.0; DISS = 0.5
def beat_at_or_after(t): import math; return B0 + math.ceil((t - B0) / BT - 1e-6) * BT
def nearest_beat(t): return B0 + round((t - B0) / BT) * BT
def logl(n): return [l.split() for l in open(os.path.join(V5C, n + '.log')) if l.strip()]
def frames(d): return len([f for f in os.listdir(os.path.join(V5C, d)) if f.startswith('f_')])
def first(n, pred): return next(int(l[0]) for l in logl(n) if pred(l))

# ---- frames of the events, from the take logs
W = logl('wake7'); GASP = first('wake7', lambda l: l[3] == 'gasp'); WEND = first('wake7', lambda l: l[2] == 'end')
OUTB = first('wake7', lambda l: l[1] == 'i2')
KNOCK = first('knock8', lambda l: l[2] == 'busy'); HIDE = first('knock8', lambda l: 'H1' in l)
SH = logl('shove4'); PUSH = first('shove4', lambda l: 'PUSH' in ' '.join(l)); POP = first('shove4', lambda l: l[1] == 'st2'); SKO = first('shove4', lambda l: any(w.endswith('KO') for w in l))
VCRASH = first('vend21', lambda l: 'brk1' in l); VSLIP = first('vend21', lambda l: '1down' in l and l[1] in ('st4', 'st5'))
CKO = first('chargeko2', lambda l: '2KO' in l)
DIVE = first('cartdive', lambda l: 'H1' in l)
CARTKO = first('cartko', lambda l: '11KO' in l)
CMS = [int(l[0]) for l in logl('chasemaw') if '3down' in ' '.join(l)][0]
FL = [l for l in open(os.path.join(V5C, 'fin.log'))]; CONTACT = next(int(l.split()[1]) for l in FL if l.startswith('CONTACT'))
def gev(n, key, idx=0):
    ev = [int(l.split()[0]) for l in open(os.path.join(V5C, 'g5_' + n + '.log')) if key in l]; return ev[idx]

E = []   # (dir, start frame, frames, note)
def put(d, st, n, note=''):
    assert st >= 0 and st + n <= frames(d), f'{d}: {st}+{n} > {frames(d)}'
    E.append(dict(d=d, st=int(st), n=int(n), note=note))

# ---- intro + the one take
t_w = STARTLE - (GASP - 15) / FPS                       # wake7 shown from frame 15 so the startle is on 12.85
food_s = t_w + DISS - LOGO_S
put('food', 0, round(food_s * FPS), 'food rain, dissolving into him asleep')
w_end = beat_at_or_after(STARTLE + (WEND + 4 - GASP) / FPS)
put('wake7', 15, round((w_end - t_w) * FPS), 'the one take, its moments on the beat; the locked locker rattles on 54.74')
t = w_end

# ---- the bridge: knock & hide, follow, the box (ends where the vending machine take must start)
v_start = beat_at_or_after(DROP - (VCRASH - 0) / FPS)   # vend21 from as early as possible with the crash on the drop
VST = VCRASH - round((DROP - v_start) * FPS)
# knock: the knock on a beat, at least 0.8 s in; cut on a beat while they search
kb = beat_at_or_after(t + 0.8); kst = KNOCK - round((kb - t) * FPS); kend = beat_at_or_after(kb + (HIDE - KNOCK) / FPS + 2.4)
put('knock8', kst, round((kend - t) * FPS), 'knocks on the wall on a beat, hides in the cart (laundry flies); the attendant comes to look'); t = kend
# the box: the KO (slap) on the last beat before the vending take, after ~4.7 s of push / pop / shock
s_end = v_start; sko_b = nearest_beat(s_end - 0.6); sst = SKO - round((sko_b - (sko_b - (SKO - PUSH + 6) / FPS)) * FPS)
s_start = beat_at_or_after(sko_b - (SKO - (PUSH - 6)) / FPS) - BT; sst = SKO - round((sko_b - s_start) * FPS)
# follow fills the gap between the knock and the box
put('follow9', 140, round((s_start - t) * FPS), 'the box tiptoes after the attendant; the cone passes over it'); t = s_start
put('shove4', sst, round((s_end - t) * FPS), 'the attendant strains and sweats at the box; he stands up, they jump; the slap on the beat'); t = s_end

# ---- the drop: the vending machine crash on 79.62, then the action
v_end = beat_at_or_after(DROP + (VSLIP - VCRASH) / FPS + 0.5)
put('vend21', VST, round((v_end - t) * FPS), 'tiptoe through the puddle, the prints are found; thump thump thump on the beat, KRRASH on the drop; can smashed, he slips'); t = v_end
def hit(d, h, lead, tail, note):
    """the clip's big moment (frame h) on a beat at least `lead` s in; cut on a beat at least `tail` s after it"""
    global t
    hb = beat_at_or_after(t + lead); st = h - round((hb - t) * FPS); end = beat_at_or_after(hb + tail)
    put(d, st, round((end - t) * FPS), note); t = end
hit('chargeko2', CKO, 0.9, 0.6, 'a charge down the locker aisle bowls over both attendants')
hit('cartdive', DIVE, 1.2, 0.9, 'pushes the cart into the laundry, dives in on the beat; it rolls on, laundry flies out')
hit('cartko', CARTKO, 3.9, 0.5, 'out of the cart: the bucket KO, then the slap KO on the beat')
hit('chasemaw', CMS, 3.0, 1.2, 'chased with the bucket: he smashes it; two of them slip')
# ---- gacha: the loud ones while the section lasts, the rest in the outro; the finale starts on a beat
G = [('g5_c_tripball', gev('c_tripball', 'ballHit'), 1.0, 1.0, 'triplets vs daruma'),
     ('g5_train', gev('train', 'trainHit'), 1.0, 0.6, 'shinkansen'),
     ('g5_c_shockcyc', gev('c_shockcyc', 'bigStomp'), 0.6, 2.7, 'his stomp vs the boss\'s cyclone'),
     ('g5_banana', gev('banana', ' slip '), 0.8, 0.5, 'banana peel'),
     ('g5_c_giantchick', gev('c_giantchick', 'skillUse 0'), 1.0, 1.2, 'the boss goes giant; he turns him into a chicken'),
     ('g5_claw', gev('claw', 'clawDrop'), 2.6, 0.3, 'the claw lifts him off and drops him out'),
     ('g5_c_bumpflop3', gev('c_bumpflop3', ' bump '), 1.4, 0.6, 'belly flop into the straw; the bumper throws him back'),
     ('g5_potato3', gev('potato3', 'boom 1'), 2.6, 0.5, 'hot potato tag: charge and dodge; it blows on the boss'),
     ('g5_c_torprew', gev('c_torprew', 'rewind 0'), 1.0, 0.8, 'the boss torpedoes him out; rewind fires by itself'),
     ('g5_c_smokespin', gev('c_smokespin', 'skillUse 1'), 0.4, 2.0, 'smoke bomb (a wall to the boss) on a spinning ring'),
     ('g5_unplug', gev('unplug', 'skillUse'), 0.2, 1.6, 'controller disconnected')]
fin_start = beat_at_or_after(COLLIDE - (CONTACT + 1 - 86) / FPS)
# fit: share the time between the gacha clips by scaling their lead/tail
lo, hi = 0.3, 3.0
for it in range(40):
    k = (lo + hi) / 2; t0 = t; tt = t
    for d, h, lead, tail, note in G:
        hb = beat_at_or_after(tt + lead * k); tt = beat_at_or_after(hb + tail * k)
    if tt > fin_start: hi = k
    else: lo = k
k = lo
for d, h, lead, tail, note in G:
    hb = beat_at_or_after(t + lead * k); st = max(0, h - round((hb - t) * FPS)); end = beat_at_or_after(hb + tail * k)
    if G[-1][0] == d: end = fin_start
    n = min(round((end - t) * FPS), frames(d) - st); put(d, st, n, note); t = t + n / FPS
if abs(t - fin_start) > 0.02: E[-1]['n'] += round((fin_start - t) * FPS); t = fin_start
# ---- the finale: they collide on 126.07
fst = CONTACT + 1 - round((COLLIDE - t) * FPS)
put('fin', fst, round((COLLIDE - t) * FPS), 'salt, clap, the boss stomps, both charge; cut as they collide')

# ---- render
total = SOON + CARD_LEN
args = ['-loop', '1', '-framerate', str(FPS), '-t', str(LOGO_S + 0.1), '-i', os.path.join(TR, 'cards/logo2_sharp.png')]
fl = [f'[0:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={round(LOGO_S * FPS)},setpts=PTS-STARTPTS[v0]']
for i, s in enumerate(E, 1):
    args += ['-framerate', str(FPS), '-start_number', str(s['st']), '-i', os.path.join(V5C, s['d'], 'f_%04d.jpg')]
    fi = ',fade=t=in:s=0:n=12:color=white' if s['d'] == 'food' else ''
    fl.append(f"[{i}:v]trim=end_frame={s['n']},setpts=PTS-STARTPTS,scale=1280:720:flags=lanczos,setsar=1,format=yuv420p{fi}[v{i}]")
n = len(E) + 1
C1 = round((SOON - COLLIDE) * FPS); C2 = round(CARD_LEN * FPS)
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C1 / FPS + 0.1), '-i', os.path.join(V5C, 'bigger.png')]
fl.append(f'[{n}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C1},setpts=PTS-STARTPTS[vc]')
args += ['-loop', '1', '-framerate', str(FPS), '-t', str(C2 / FPS + 0.1), '-i', os.path.join(V5C, 'soon.png')]
fl.append(f'[{n + 1}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={C2},setpts=PTS-STARTPTS[vd]')
fl.append(f"[v1][v2]xfade=transition=fade:duration={DISS}:offset={E[0]['n'] / FPS - DISS:.3f}[vfw]")
fl.append('[v0][vfw]' + ''.join(f'[v{i}]' for i in range(3, n)) + f'[vc][vd]concat=n={n + 1}:v=1:a=0[cat]')
ov_in = STARTLE; ov_out = t_w + (OUTB - 15) / FPS - 0.6
args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', os.path.join(HERE, 'title1280.png')]
fl.append(f'[{n + 2}:v]format=rgba,fade=t=in:st={ov_in:.3f}:d=0.6:alpha=1,fade=t=out:st={ov_out:.3f}:d=0.8:alpha=1[title]')
fl.append(f"[cat][title]overlay=0:0:format=auto:enable='between(t,{ov_in:.3f},{ov_out + 0.9:.3f})',format=yuv420p[o]")
args += ['-i', MUSIC]
fl.append(f'[{n + 3}:a]atrim=end={total:.3f},afade=t=out:st={total - 0.6:.3f}:d=0.6[a]')
tt = 0; print(f'{0:7.2f}  logo')
tt = LOGO_S
for i, s in enumerate(E):
    if i == 1: tt -= DISS
    print(f"{tt:7.2f}  {s['d']:<16} {s['st']:>5}+{s['n']:<4} {s['note']}"); tt += s['n'] / FPS
print(f'{COLLIDE:7.2f}  BIGGER IS BETTER   {SOON:.2f} COMING SOON   end {total:.2f}   (gacha stretch x{k:.2f})')
if '--dry' in sys.argv: sys.exit()
subprocess.run(['ffmpeg', '-y', '-v', 'error'] + args + ['-filter_complex', ';'.join(fl), '-map', '[o]', '-map', '[a]', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip(), out)
