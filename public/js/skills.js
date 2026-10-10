'use strict';
// Gacha-mode skills: one-shot specials dealt to both players every round, used with Space.
// Pure simulation (no rendering) so it runs in headless tests too.
(function () {
  const RR = S.RING_R;
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const dirTo = (a, b) => { const dx = b.x - a.x, dz = b.z - a.z, d = Math.hypot(dx, dz) || 1e-4; return [dx / d, dz / d, d]; };

  const LIST = [
    { id: 'dizzySlap', name: 'DIZZY SLAP', desc: 'A slap that leaves them seeing stars.', kind: 'atk' },
    { id: 'turnSlap', name: 'SPIN SLAP', desc: 'A slap that spins them round to face the wrong way.', kind: 'atk' },
    { id: 'smoke', name: 'SMOKE BOMB', desc: 'A huge, thick cloud over half the ring for 5 seconds. They cannot see through it, you can.', kind: 'any' },
    { id: 'absorb', name: 'IRON BODY', desc: 'For 3s hits barely move you. Each hit charges your next attack.', kind: 'atk' },
    { id: 'slow', name: 'TIME DRAG', desc: 'They move in slow motion for 5 seconds.', kind: 'any' },
    { id: 'swap', name: 'SWITCH', desc: 'Swap places with them instantly.', kind: 'def' },
    { id: 'barrage', name: 'CROWD BARRAGE', desc: 'The crowd pelts them with cushions for 5 seconds.', kind: 'any' },
    { id: 'dashThru', name: 'PHANTOM DASH', desc: 'Dash straight through them and end up behind.', kind: 'atk' },
    { id: 'invuln', name: 'INVINCIBLE', desc: 'Nothing can hurt or move you for 3 seconds.', kind: 'atk' },
    { id: 'blind', name: 'BLINDING FLASH', desc: 'They are blinded for 2 seconds.', kind: 'any' },
    { id: 'drunk', name: 'SAKE', desc: 'For 5 seconds they are drunk: everything they press happens 0.4s late, and the stick is backwards.', kind: 'any' },
    { id: 'shrink', name: 'SHRINK', desc: 'They shrink to half their power for 5 seconds.', kind: 'any' },
    { id: 'quake', name: 'EARTHQUAKE', desc: 'The ground heaves under them only for 3 seconds, throwing them around the ring.', kind: 'any' },
    { id: 'freeze', name: 'FREEZE', desc: 'They are frozen solid for 3 seconds. Slide them out!', kind: 'atk' },
    { id: 'invis', name: 'VANISH', desc: 'You turn invisible to them for 3 seconds.', kind: 'atk' },
    { id: 'giant', name: 'GIANT', desc: 'Double size and double strength for 3 seconds.', kind: 'atk' },
    { id: 'banana', name: 'BANANA PEEL', desc: 'Drop a peel. Whoever steps on it goes flat on their back and loses.', kind: 'trap' },
    { id: 'trap', name: 'TRAPDOOR', desc: 'A hidden trapdoor where you stand. Lure them onto it and they drop through.', kind: 'trap' },
    { id: 'fanGrab', name: 'SUPERFAN', desc: 'A fan grabs them from the crowd and holds them for 3 seconds.', kind: 'atk' },
    { id: 'referee', name: 'REFEREE BREAK', desc: 'The referee runs in between you and shoves you both apart.', kind: 'def' },
    { id: 'hundred', name: 'THOUSAND HANDS', desc: 'A blur of slaps for 3 seconds. Land every single one for a thousand-hit combo.', kind: 'atk' },
    { id: 'torpedo', name: 'TORPEDO', desc: 'Launch yourself head-first across the ring.', kind: 'atk' },
    { id: 'dart', name: 'SLEEP DART', desc: 'Fire a dart straight ahead. If it hits, they fall asleep on their feet for 2.5s. They can dodge it.', kind: 'any' },
    { id: 'inhale', name: 'CONSUME', desc: 'Inhale hard and swallow them whole. Walk them anywhere you like, then press Space to spit them out the way you face.', kind: 'atk' },
    { id: 'beartrap', name: 'BEAR TRAP', desc: 'Drop a bear trap at your feet. Whoever steps in it is stuck fast for 3s. They cannot be shoved out, but you can grab them and lift them out.', kind: 'trap' },
    { id: 'gale', name: 'GIANT FAN', desc: 'Pull out a massive fan and blast them with wind for 1.5s. Steer the gust with the stick. Bracing halves it.', kind: 'atk' },
    { id: 'rewind', name: 'REWIND', desc: 'Jump back to where you were 3 seconds ago. If you are about to lose while holding it, it fires by itself.', kind: 'def' },
    { id: 'bumper', name: 'BUMPER RING', desc: 'For 6s the edge of the ring bounces you back in hard instead of letting you out.', kind: 'def' },
    { id: 'ball', name: 'DARUMA ROLL', desc: 'Turn into a daruma doll for 5s. Roll around fast and press dash (L) to smash forward. Nobody can grab a daruma.', kind: 'atk' },
    { id: 'hole', name: 'BLACK HOLE', desc: 'Drop a tiny gravity point where you stand. For 3s it drags both of you toward it.', kind: 'trap' },
    { id: 'favourite', name: 'AUDIENCE FAVOURITE', desc: 'A second life. The first time you would lose, the crowd shoves you back into the ring. Works by itself.', kind: 'def' },
    { id: 'triplets', name: 'TRIPLETS', desc: 'Poof: you and two clones appear around them. The clones move on their own. Only you can see your armband. A clone vanishes when touched; only the real you can lose.', kind: 'atk' },
    { id: 'possess', name: 'POSSESSION', desc: 'For 1.2s their body runs for the nearest edge, whatever they press.', kind: 'any' },
    { id: 'fish', name: 'LIVE FISH', desc: 'Throw a giant tuna into the ring. It flops around wildly for 7s and knocks over anyone it hits.', kind: 'any' },
    { id: 'bomb', name: 'BOMB', desc: 'A bomb lands in the middle and blows in 5s. Shove it toward them. Hit it too often and it goes off early.', kind: 'any' },
    { id: 'chicken', name: 'CHICKEN', desc: 'Turn them into a tiny, very fast chicken for 3s. They can only run, no pushing, grabbing or skills. Catch them, or let them tire themselves out.', kind: 'any' },
    { id: 'shock', name: 'SHOCKWAVE STOMP', desc: 'A huge stomp (half-second wind-up) sends a shockwave rolling across the ring. They can parry it or dash through it.', kind: 'atk' },
    { id: 'potato', name: 'HOT POTATO', desc: 'Stick a flashing bomb on them. It blows in 6s and floors whoever holds it. Touch the other wrestler to pass it on.', kind: 'any' },
    { id: 'claw', name: 'CLAW MACHINE', desc: 'A crane claw hunts overhead for 7s. Whoever it catches gets carried somewhere random and dropped, maybe outside the ring.', kind: 'any' },
    { id: 'doors', name: 'MYSTERY DOOR', desc: 'Two doors appear at opposite ends of the ring for 9s. Walk into one and you come out of either.', kind: 'def' },
    { id: 'copycat', name: 'COPYCAT', desc: 'Take the skill they are holding. They are left with a fake that does nothing.', kind: 'any' },
    { id: 'thief', name: 'SKILL THIEF', desc: 'Your next slap within 4s knocks their skill out onto the floor. Whoever gets to it first keeps it.', kind: 'atk' },
    { id: 'spin', name: 'ROTATING RING', desc: 'The whole dohyo starts spinning for 6s, carrying everyone round and flinging them outward.', kind: 'any' },
    { id: 'train', name: 'TRAIN CROSSING', desc: 'Warning bells ring, then something huge blasts straight across the ring. Get out of the lane.', kind: 'any' },
    { id: 'blur', name: 'CENSORED', desc: 'For 5s you are a blur of pixels to them. They can barely tell where you are.', kind: 'any' },
    { id: 'unplug', name: 'CONTROLLER DISCONNECTED', desc: 'Their controller "disconnects". They cannot move or act for 1.5s.', kind: 'any' },
    { id: 'spot', name: 'SPOTLIGHT', desc: 'Blackout: only the spotlight can be seen. It pins them for 2s with stage fright, then follows you for 3s.', kind: 'any' },
    { id: 'konbini', name: 'CONVENIENCE STORE', desc: 'A tiny konbini appears. Walk in, browse every gacha skill on the shelves and buy one with your yen, or leave. They can attack the shop (1000 health); when it breaks you are thrown out.', kind: 'def' },
    { id: 'takeaway', name: 'TAKEAWAY BAG', desc: 'A mystery food bag lands in the middle. Whoever eats it gets giant strength or food poisoning.', kind: 'any' },
    { id: 'third', name: 'SURPRISE CHALLENGER', desc: 'A third wrestler joins the match and fights whoever is closest. It scores rounds too: if all three end on one point, the match is a draw.', kind: 'any' },
    { id: 'noarms', name: 'NO ARMS', desc: 'Their arms vanish for 5s. No pushing, no grabbing.', kind: 'any' },
    { id: 'reset', name: 'SCORE RESET', desc: 'Wipe the score back to nothing for everyone.', kind: 'any' },
    { id: 'storm', name: 'LIGHTNING', desc: 'Three lightning bolts strike them from above. Each one is marked on the floor first: move off the mark or be stunned.', kind: 'any' },
    { id: 'molotov', name: 'MOLOTOV COCKTAIL', desc: 'Throw a flaming bottle at where they stand. It bursts into a patch of fire for 4s: anyone in it burns, staggers and loses balance.', kind: 'any' },
    { id: 'peek', name: 'PEEK', desc: 'See the skill they are holding, then draw a new one for yourself.', kind: 'any' },
    { id: 'boom', name: 'KAMIKAZE', desc: 'Light a 1.5s fuse, then explode. If they are within about 3.5 metres, you both go down and the round is fought again. If they got away, only you go down.', kind: 'def' },
    { id: 'cyclone', name: 'CYCLONE', desc: 'Spin like a top for 5s. Steer with the stick: anyone you touch is flung away, and nobody can grab you.', kind: 'atk' },
    { id: 'bellyFlop', name: 'BELLY FLOP', desc: 'Leap off screen, steer your shadow, and crash down on them.', kind: 'any' },
  ];
  const BY = {}; for (const s of LIST) BY[s.id] = s;
  // skill finishes show up as the winning technique
  S.KIMARITE.sk_trap = ['', 'OTOSHIANA', 'Dropped through a trapdoor'];
  S.KIMARITE.sk_banana = ['', 'BANANA', 'Slipped on a peel'];
  S.KIMARITE.sk_bellyFlop = ['', 'BELLY FLOP', 'Crushed from the sky'];
  S.KIMARITE.sk_barrage = ['', 'CROWD BARRAGE', 'Pelted by the fans'];
  S.KIMARITE.sk_freeze = ['', 'ICE SLIDE', 'Slid out frozen solid'];
  S.KIMARITE.sk_inhale = ['', 'SPAT OUT', 'Swallowed whole and spat out'];
  S.KIMARITE.sk_gale = ['', 'BLOWN AWAY', 'Blown out by a giant fan'];
  S.KIMARITE.sk_ball = ['', 'BOWLED OVER', 'Flattened by a rolling ball'];
  S.KIMARITE.sk_cyclone = ['', 'CYCLONE', 'Flung out by a spinning top'];
  S.KIMARITE.sk_hole = ['', 'BLACK HOLE', 'Dragged out by gravity'];
  S.KIMARITE.sk_fish = ['', 'TUNA SLAP', 'Knocked out by a flopping tuna'];
  S.KIMARITE.sk_bomb = ['', 'BLOWN UP', 'Caught in the bomb blast'];
  S.KIMARITE.sk_wave = ['', 'SHOCKWAVE', 'Knocked out by a stomp shockwave'];
  S.KIMARITE.sk_possess = ['', 'POSSESSED', 'Walked out against their will'];
  S.KIMARITE.sk_potato = ['', 'HOT POTATO', 'Holding the bomb when it blew'];
  S.KIMARITE.sk_claw = ['', 'CLAW MACHINE', 'Dropped out by the claw'];
  S.KIMARITE.sk_spin = ['', 'SPUN OUT', 'Flung off the spinning ring'];
  S.KIMARITE.sk_train = ['', 'TRAIN', 'Hit by the sumo express'];
  S.KIMARITE.sk_third = ['', 'INTRUDER', 'Pushed out by the third wrestler'];
  S.KIMARITE.sk_molotov = ['', 'BURNT OUT', 'Set alight by a molotov'];
  S.KIMARITE.sk_bolt = ['', 'LIGHTNING', 'Struck by lightning'];
  S.KIMARITE.sk_boom = ['', 'KAMIKAZE', 'Blew themselves up'];
  S.KIMARITE.sk_boomDraw = ['', 'DOUBLE KO', 'Nobody wins. The round is fought again'];
  S.KIMARITE.sk_fanGrab = ['', 'SUPERFAN', 'Held by a fan'];

  const Skills = {
    LIST, BY,
    random() { return LIST[(S.rand() * LIST.length) | 0].id; },

    use(m, w, id) {
      const o = w.opp, f = w.fxs, of = o.fxs;
      const [nx, nz, d] = dirTo(w, o);
      m.emit('skillUse', { w, id, x: w.x, z: w.z });
      if (w.clinch && ['dizzySlap', 'turnSlap', 'dashThru', 'hundred', 'torpedo', 'bellyFlop', 'swap', 'fanGrab', 'freeze', 'gale', 'inhale'].includes(id)) w.clinch.end('skill');
      switch (id) {
        case 'dizzySlap': case 'turnSlap': w.set('sslap', 0.38); w.sk = id; break;
        case 'smoke': m.objs.push({ type: 'smoke', x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, t: 0, dur: 5, owner: w }); break;
        case 'absorb': f.absorb = 3; w.charges = 0; break;
        case 'slow': of.slow = 5; break;
        case 'swap': {
          const tx = w.x, tz = w.z; w.x = o.x; w.z = o.z; o.x = tx; o.z = tz;
          w.ghostT = o.ghostT = 0.25; m.emit('poof', { x: w.x, z: w.z }); m.emit('poof', { x: o.x, z: o.z }); break;
        }
        case 'barrage': m.objs.push({ type: 'barrage', target: o, owner: w, t: 0, dur: 5, next: 0 }); break;
        case 'dashThru':
          w.ddx = nx; w.ddz = nz; w.set('dash', 0.32); w.dpow = (d + 1.5) / (w.a.dashSpeed * 0.32 * 0.85); w.dashCD = 0.6;
          f.thru = 0.45; w.ghostT = 0.45; break;
        case 'invuln': f.invuln = 3; break;
        case 'blind': of.blind = 2; break;
        case 'drunk': of.drunk = 5; break;
        case 'shrink': of.shrink = 5; break;
        case 'quake': of.quake = 3; break;
        case 'freeze': of.frozen = 3; if (o.clinch) o.clinch.end('skill'); m.tag(o, w, 'sk_freeze'); break;
        case 'invis': f.invis = 3; break;
        case 'giant': f.giant = 3; break;
        case 'beartrap': m.objs.push({ type: 'beartrap', x: w.x, z: w.z, t: 0, dur: 14, owner: w, armed: false }); break;
        case 'banana': m.objs.push({ type: 'banana', x: w.x + nx * 1.1, z: w.z + nz * 1.1, t: 0, dur: 12, owner: w }); break;
        case 'trap': m.objs.push({ type: 'trap', x: w.x, z: w.z, t: 0, dur: 9, owner: w, armed: false }); break;
        case 'fanGrab': {
          const od = Math.hypot(o.x, o.z) || 1, ax = o.x / od * (RR + 1.1), az = o.z / od * (RR + 1.1);
          of.grabbed = 3; o.gx = o.x; o.gz = o.z;
          if (o.clinch) o.clinch.end('skill');
          m.objs.push({ type: 'fan', target: o, owner: w, ax, az, t: 0, dur: 3 });
          m.tag(o, w, 'sk_fanGrab'); break;
        }
        case 'referee': m.objs.push({ type: 'ref', x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, t: 0, dur: 1.5, pushed: false }); break;
        case 'hundred': w.set('hyaku', 3); w.hitT = 0; w.hyN = 0; w.hyHits = 0; break;
        case 'torpedo':
          w.f = Math.atan2(nz, nx); w.cspd = 11; w.chargeHit = false; w.dodged = false; w.set('charge', 0.62); w.torpedo = true; break;
        case 'peek': {
          (m.peek || (m.peek = [false, false]))[w.idx] = true;
          let nid = 'peek'; while (nid === 'peek') nid = LIST[(S.rand() * LIST.length) | 0].id;
          m.skills[w.idx] = nid;
          m.emit('peek', { w, theirs: m.skills[o.idx], fakeOf: m.fakeName[o.idx], mine: nid }); break;
        }
        case 'boom': w.boomT = 1.5; break;
        case 'rewind': Skills.rewind(m, w); break;
        case 'bumper': f.bumper = 6; break;
        case 'ball': f.ball = 5; w.ballCD = 0; if (w.clinch) w.clinch.end('skill'); break;
        case 'cyclone': f.cyclone = 5; w.cycAng = w.cycAng || 0; w.cycHitT = 0; if (w.clinch) w.clinch.end('skill'); m.emit('cyclone', { w, x: w.x, z: w.z }); break;
        case 'hole': m.objs.push({ type: 'hole', x: w.x, z: w.z, t: 0, dur: 3, owner: w }); break;
        case 'favourite': break; // only ever fires by itself
        case 'blur': f.blur = 5; break;
        case 'storm': m.objs.push({ type: 'storm', owner: w, t: 0, dur: 3.6, x: o.x, z: o.z, n: 0, next: 0.2, strikeAt: -1, flash: 0 }); break;
        case 'molotov': {
          // thrown at where they are now: they can step away while it flies
          m.objs.push({ type: 'molotov', owner: w, t: 0, dur: 5.1, sx: w.x, sz: w.z, tx: o.x, tz: o.z, x: w.x, z: w.z, y: 1.6, landed: false, R: 1.4 });
          break;
        }
        case 'third':
          if (!m.third) { let a = (S.rand() * S.ARCH.length) | 0; m.third = { arch: a, wins: 0 }; Skills.spawnThird(m, true); m.emit('thirdIn', {}); }
          break;
        case 'noarms': of.noarms = 5; if (o.clinch) o.clinch.end('skill'); break;
        case 'reset': m.wins = [0, 0]; m.history = []; if (m.third) m.third.wins = 0; m.emit('scoreReset', {}); break;
        case 'unplug': of.unplug = 1.5; if (o.clinch) o.clinch.end('skill'); m.emit('unplug', { w: o }); break;
        case 'spot': of.stagefright = 2; of.dark = 5; m.objs.push({ type: 'spot', owner: w, t: 0, dur: 5 }); break;
        case 'konbini': {
          // the shop opens up across the ring from them
          let ax = w.x - o.x, az = w.z - o.z; const al = Math.hypot(ax, az) || 1;
          let x = w.x + ax / al * 1.5, z = w.z + az / al * 1.5; const l = Math.hypot(x, z); if (l > RR - 1) { x *= (RR - 1) / l; z *= (RR - 1) / l; }
          m.objs.push({ type: 'konbini', x, z, t: 0, dur: 12, hp: 1000, cd: [0, 0], it: 0, owner: w, shake: 0, leave: false, bought: null }); break;
        }
        case 'takeaway': m.objs.push({ type: 'bag', x: 0, z: 0, t: 0, dur: 12 }); break;
        case 'fake': m.emit('fakeUse', { w, x: w.x, z: w.z }); m.fakeName[w.idx] = null; break;
        case 'potato': m.objs.push({ type: 'potato', holder: o.idx, t: 0, dur: 6, cd: 0.6, owner: w }); m.emit('potatoOn', { w: o }); break;
        case 'claw': m.objs.push({ type: 'claw', x: w.x * 0.3, z: w.z * 0.3, h: 3.4, t: 0, dur: 9, mode: 'hunt', mt: 0, huntFor: 1.4 + S.rand() * 0.8, victim: -1, dx: 0, dz: 0, owner: w }); break;
        case 'doors': { const a = S.rand() * Math.PI * 2; m.objs.push({ type: 'doors', a, t: 0, dur: 9, cd: [0, 0] }); break; }
        case 'copycat': {
          const theirs = m.skills[o.idx];
          m.skills[w.idx] = theirs; m.fakeName[w.idx] = theirs === 'fake' ? m.fakeName[o.idx] : null;
          m.fakeName[o.idx] = theirs; m.skills[o.idx] = 'fake';
          m.emit('copycat', { w, o, id: theirs }); break;
        }
        case 'thief': f.thiefT = 4; break;
        case 'spin': m.objs.push({ type: 'spin', t: 0, dur: 6, a: 0 }); break;
        case 'train': {
          const a = S.rand() * Math.PI * 2, off = (S.rand() - 0.5) * 2.6;
          // the lane runs through where they stand, give or take
          const px = -Math.sin(a), pz = Math.cos(a), lo = o.x * px + o.z * pz + off * 0.5;
          m.objs.push({ type: 'train', a, off: lo, t: 0, dur: 3.7, warn: 2.1, hit: [false, false], go: false, owner: w });
          m.emit('trainWarn', {}); break;
        }
        case 'possess': of.possessed = 1.2; if (o.clinch) o.clinch.end('skill'); m.tag(o, w, 'sk_possess'); break;
        case 'fish': {
          const a = S.rand() * Math.PI * 2;
          m.objs.push({ type: 'fish', x: o.x + Math.cos(a) * 1.4, z: o.z + Math.sin(a) * 1.4, vx: 0, vz: 0, t: 0, dur: 7, hopT: 0.2, spin: 0, cd: [0, 0], owner: w });
          break;
        }
        case 'bomb': m.objs.push({ type: 'bomb', x: 0, z: 0, vx: 0, vz: 0, t: 0, dur: 5, hits: 0, cd: [0, 0], owner: w }); break;
        case 'chicken': of.chicken = 3; if (o.clinch) o.clinch.end('skill'); o.chkA = S.rand() * 6.28; o.chkT = 0; o.chkBy = -1; break;
        case 'shock': w.set('bigstomp', 0.5); break;
        case 'triplets': {
          // poof: you and two clones appear around them; which one is real is random
          const a0 = S.rand() * Math.PI * 2, real = (S.rand() * 3) | 0, pos = [];
          for (let k = 0; k < 3; k++) {
            let px = o.x + Math.cos(a0 + k * 2.094) * 1.8, pz = o.z + Math.sin(a0 + k * 2.094) * 1.8;
            const l = Math.hypot(px, pz); if (l > RR - 0.7) { px *= (RR - 0.7) / l; pz *= (RR - 0.7) / l; }
            pos.push([px, pz]);
          }
          m.emit('poof', { x: w.x, z: w.z });
          w.x = pos[real][0]; w.z = pos[real][1]; w.vx = w.vz = 0; w.ghostT = 0.3; w.f = Math.atan2(o.z - w.z, o.x - w.x);
          const clones = pos.filter((_, k) => k !== real).map(([x, z]) => ({ x, z, vx: 0, vz: 0, alive: true, ang: Math.atan2(z - o.z, x - o.x), dir: S.rand() < 0.5 ? -1 : 1, lunge: 0, think: 0 }));
          for (const p of pos) m.emit('poof', { x: p[0], z: p[1] });
          m.objs.push({ type: 'clones', owner: w, t: 0, dur: 8, c: clones });
          break;
        }
        case 'gale': { const [nx, nz] = dirTo(w, o); w.f = Math.atan2(nz, nx); w.set('gale', 1.5); break; }
        case 'dart': { // fired the way you face, so it can be dodged
          const fx = Math.cos(w.f), fz = Math.sin(w.f);
          m.objs.push({ type: 'dart', x: w.x + fx * (w.r + 0.1), z: w.z + fz * (w.r + 0.1), vx: fx * 13, vz: fz * 13, t: 0, dur: 1.2, owner: w });
          break;
        }
        case 'inhale': w.set('inhale', 1.1); w.gulpI = -1; break;
        case 'bellyFlop':
          w.set('air', 1.65); w.ax2 = o.x; w.az2 = o.z; w.sx0 = w.x; w.sz0 = w.z; break;
      }
    },

    // per-wrestler special states and status effects; return true when this took over control
    control(m, w, dt, I) {
      const f = w.fxs, o = w.opp, a = w.a;
      if (w.carried) { w.vx = w.vz = 0; w.ghostT = 0.2; return true; } // dangling from the claw
      if (w.inShop) { w.vx = w.vz = 0; w.ghostT = 0.2; return true; } // browsing the shelves
      if (w.swallowed) { // inside the other wrestler: ride along until spat out
        const g = m.w[1 - w.idx]; w.x = g.x; w.z = g.z; w.vx = w.vz = 0; w.ghostT = 0.2; return true;
      }
      if (f.zapped > 0) { const k = Math.exp(-dt * 3); w.vx *= k; w.vz *= k; return true; } // frazzled by lightning
      if (f.sleep > 0) { // asleep on their feet: no control, but they can still be shoved
        const k = Math.exp(-dt * 2.5); w.vx *= k; w.vz *= k; return true;
      }
      if (f.snared > 0) { // jaws shut on the ankle: rooted to the spot, but can still be grabbed and lifted out
        w.vx *= Math.exp(-dt * 12); w.vz *= Math.exp(-dt * 12);
        w.vx += (w.gx - w.x) * 30 * dt; w.vz += (w.gz - w.z) * 30 * dt; return true;
      }
      if (f.frozen > 0 || f.grabbed > 0) {
        const k = Math.exp(-dt * (f.frozen > 0 ? 0.8 : 8)); // ice slides, a grip holds
        w.vx *= k; w.vz *= k;
        if (f.grabbed > 0 && w.gx !== undefined) { w.vx += (w.gx - w.x) * 6 * dt; w.vz += (w.gz - w.z) * 6 * dt; }
        return true;
      }
      if (w.st === 'sslap') {
        const [nx, nz, d] = dirTo(w, o);
        w.vx += (nx * 3.2 - w.vx) * Math.min(1, dt * 12); w.vz += (nz * 3.2 - w.vz) * Math.min(1, dt * 12);
        w.f = Math.atan2(nz, nx);
        if (!w.hitDone && w.t > 0.08 && w.t < 0.28 && d < w.r + o.r + 0.8 && o.st !== 'air') {
          w.hitDone = true;
          if (Skills.parry(m, o, w, nx, nz)) { /* knocked aside */ }
          else if (o.fxs.invuln > 0) { m.emit('hit', { kind: 'palm', x: o.x, z: o.z, nx, nz, power: 1, zone: 'front', w, o }); }
          else {
            if (w.sk === 'dizzySlap') { o.fxs.dizzy = 2.5; }
            else { o.f = S.wrap(o.f + Math.PI); o.fxs.turnLock = 0.9; }
            if (o.clinch) o.clinch.end('skill');
            o.set('stun', 0.3); o.vx += nx * 1.5; o.vz += nz * 1.5;
            m.tag(o, w, 'palm');
            m.emit('hit', { kind: 'heavy', x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, nx, nz, power: 6, zone: 'front', w, o, big: true, special: w.sk });
          }
        }
        if (w.t >= w.dur) w.set('recover', 0.15);
        return true;
      }
      if (w.st === 'inhale') {
        const [nx, nz, d] = dirTo(w, o);
        w.f = Math.atan2(nz, nx); w.vx *= Math.exp(-dt * 8); w.vz *= Math.exp(-dt * 8);
        if (d < 3.8 && o.st !== 'air' && !o.lifted && !(o.fxs.invuln > 0) && !o.down) {
          if (o.clinch) o.clinch.end('skill');
          const pull = 26 * (1 - d / 4.2);
          o.vx -= nx * pull * dt; o.vz -= nz * pull * dt; o.slideT = Math.max(o.slideT, 0.15);
          if (o.st !== 'stun') o.set('stun', 0.25);
          if (d < w.r + o.r + 0.25) { // gulp
            o.swallowed = true; o.x = w.x; o.z = w.z; o.vx = o.vz = 0; w.gulpI = o.idx; w.ghostT = o.ghostT = 0.2;
            w.gulpT = 0; w.set('recover', 0.2); m.emit('gulp', { w, x: w.x, z: w.z });
          }
        }
        if (w.st === 'inhale' && w.t >= w.dur) w.set('recover', 0.3);
        return true;
      }
      if (f.chicken > 0) {
        // a tiny chicken: frantic and fast. The chicken's own player (or CPU) steers it with their own stick,
        // with a bit of chicken panic mixed in. It cannot attack, only run.
        w.chkT -= dt; if (w.chkT <= 0) { w.chkT = 0.12 + S.rand() * 0.2; w.chkA += (S.rand() - 0.5) * 3.2; }
        const C = I || S.NULL_IN, cm = Math.hypot(C.mx || 0, C.mz || 0);
        const ax = (C.mx || 0) + Math.cos(w.chkA) * 0.25 * (cm > 0.1 ? 1 : 2), az = (C.mz || 0) + Math.sin(w.chkA) * 0.25 * (cm > 0.1 ? 1 : 2);
        w.vx += ax * 34 * dt; w.vz += az * 34 * dt;
        const k = Math.exp(-dt * 2.2); w.vx *= k; w.vz *= k;
        const sp = Math.hypot(w.vx, w.vz); if (sp > 7.5) { w.vx *= 7.5 / sp; w.vz *= 7.5 / sp; }
        if (sp > 0.3) w.f = Math.atan2(w.vz, w.vx);
        if (w.st !== 'free') w.set('free');
        return true;
      }
      if (f.cyclone > 0) {
        // CYCLONE: a spinning top, arms out. Slow-ish, steerable, and it drifts
        w.vx += I.mx * 18 * dt; w.vz += I.mz * 18 * dt;
        const k = Math.exp(-dt * 1.6); w.vx *= k; w.vz *= k;
        const sp = Math.hypot(w.vx, w.vz); if (sp > 5.2) { w.vx *= 5.2 / sp; w.vz *= 5.2 / sp; }
        const spin = 26 * Math.min(1, f.cyclone / 0.6, (5 - f.cyclone) / 0.4 + 0.3); // winds up, winds down
        w.cycAng = (w.cycAng || 0) + spin * dt; w.f = w.cycAng;
        if (w.st !== 'free') w.set('free');
        return true;
      }
      if (f.ball > 0) {
        // rolling ball: build speed with the stick, dash to smash forward
        w.ballCD -= dt;
        w.vx += I.mx * 15 * dt; w.vz += I.mz * 15 * dt;
        const k = Math.exp(-dt * 0.7); w.vx *= k; w.vz *= k;
        let sp = Math.hypot(w.vx, w.vz);
        if (I.dash.pressed && w.ballCD <= 0) {
          let dx = I.mx, dz = I.mz, dl = Math.hypot(dx, dz);
          if (dl < 0.2) { dx = sp > 0.3 ? w.vx : Math.cos(w.f); dz = sp > 0.3 ? w.vz : Math.sin(w.f); dl = Math.hypot(dx, dz) || 1; }
          w.vx += dx / dl * 7; w.vz += dz / dl * 7; w.ballCD = 0.7; m.emit('ballDash', { w, x: w.x, z: w.z });
          sp = Math.hypot(w.vx, w.vz);
        }
        const cap = w.ballCD > 0.35 ? 11 : 7.5; if (sp > cap) { w.vx *= cap / sp; w.vz *= cap / sp; }
        if (sp > 0.3) w.f = Math.atan2(w.vz, w.vx);
        w.ballRoll += sp * dt / 0.7;
        if (w.st !== 'free') w.set('free');
        return true;
      }
      if (w.st === 'bigstomp') {
        w.vx *= Math.exp(-dt * 10); w.vz *= Math.exp(-dt * 10);
        const [nx, nz] = dirTo(w, o); w.f = Math.atan2(nz, nx);
        if (w.t >= w.dur) {
          m.objs.push({ type: 'wave', x: w.x, z: w.z, r: w.r, t: 0, dur: 1.1, owner: w, done: false });
          m.emit('bigStomp', { w, x: w.x, z: w.z });
          w.set('recover', 0.2);
        }
        return true;
      }
      if (w.st === 'rewinding') {
        const T = w.rwTrail, n = T.length, k = Math.min(1, w.t / w.dur);
        const fi = (1 - k) * (n - 1), i = Math.floor(fi), a = T[i], b = T[Math.min(n - 1, i + 1)], u = fi - i;
        w.x = a[0] + (b[0] - a[0]) * u; w.z = a[1] + (b[1] - a[1]) * u; w.f = a[2];
        w.vx = w.vz = 0; w.ghostT = 0.2;
        if (w.t >= w.dur) { w.rwTrail = []; w.set('recover', 0.25); m.emit('rewindEnd', { w, x: w.x, z: w.z }); }
        return true;
      }
      if (w.st === 'gale') {
        // plant your feet and fan: a cone of wind in front, strongest up close
        if (I.mx || I.mz) { const ta = Math.atan2(I.mz, I.mx), da = S.wrap(ta - w.f); w.f += clamp(da, -dt * 2.2, dt * 2.2); }
        w.vx *= Math.exp(-dt * 10); w.vz *= Math.exp(-dt * 10);
        const fx = Math.cos(w.f), fz = Math.sin(w.f), dx = o.x - w.x, dz = o.z - w.z, d = Math.hypot(dx, dz) || 1e-4;
        const along = (dx * fx + dz * fz) / d;
        if (w.t > 0.15 && d < 6 && along > 0.72 && o.st !== 'air' && !o.swallowed && !o.lifted && !(o.fxs.invuln > 0)) {
          if (o.clinch) o.clinch.end('skill');
          const F = 46 * (1 - d / 7) * (o.st === 'brace' ? 0.5 : 1) * (0.75 + 0.25 * Math.sin(w.t * 14));
          o.vx += fx * F * dt / Math.max(0.6, o.m); o.vz += fz * F * dt / Math.max(0.6, o.m);
          o.slideT = Math.max(o.slideT, 0.12);
          m.tag(o, w, 'sk_gale'); m.hurt(o, dt * 0.25, fx, fz);
        }
        if (w.t >= w.dur) w.set('recover', 0.25);
        return true;
      }
      if (w.st === 'spit') {
        // a quick wind-up, then out they come
        w.vx *= Math.exp(-dt * 8); w.vz *= Math.exp(-dt * 8); w.ghostT = 0.2;
        if (w.t >= w.dur) {
          const fx = Math.cos(w.f), fz = Math.sin(w.f);
          o.swallowed = false; w.gulpI = -1;
          o.x = w.x + fx * (w.r + o.r + 0.1); o.z = w.z + fz * (w.r + o.r + 0.1);
          o.vx = fx * 10.5 / Math.max(0.7, o.m); o.vz = fz * 10.5 / Math.max(0.7, o.m); o.slideT = 0.7; o.ghostT = 0.25;
          o.f = Math.atan2(-fz, -fx);
          m.tag(o, w, 'sk_inhale'); m.hurt(o, 0.6, fx, fz);
          if (o.st !== 'fall') { o.set('stumble'); o.sdx = fx; o.sdz = fz; }
          w.set('recover', 0.35);
          m.emit('spit', { w, o, x: o.x, z: o.z, nx: fx, nz: fz });
        }
        return true;
      }
      if (w.st === 'hyaku') {
        const [nx, nz, d] = dirTo(w, o);
        w.f = Math.atan2(nz, nx);
        w.vx += (nx * 1.4 - w.vx) * Math.min(1, dt * 8); w.vz += (nz * 1.4 - w.vz) * Math.min(1, dt * 8);
        w.hitT -= dt;
        if (w.hitT <= 0) {
          w.hitT = 0.075; w.hand ^= 1; w.hyN++;
          if (d < w.r + o.r + 0.45 && o.st !== 'air' && Skills.parry(m, o, w, nx, nz)) { w.set('stun', 0.4); m.emit('hyakuEnd', { w, hits: w.hyHits, n: w.hyN, parried: true }); return true; }
          if (d < w.r + o.r + 0.45 && o.st !== 'air' && !(o.fxs.invuln > 0) && !o.swallowed) {
            w.hyHits++; Skills.knockSkill(m, w, o, nx, nz);
            const k = o.fxs.absorb > 0 ? 0.3 : 1;
            o.vx += nx * 1.25 * k / o.m; o.vz += nz * 1.25 * k / o.m; o.slideT = Math.max(o.slideT, 0.1);
            if (o.clinch) o.clinch.end('skill');
            m.tag(o, w, 'palm'); m.hurt(o, 0.022, nx, nz);
            m.emit('hit', { kind: 'palm', x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, nx, nz, power: 1.6, zone: 'front', w, o, rapid: true, hits: w.hyHits });
          }
        }
        if (w.t >= w.dur) { w.set('recover', 0.2); m.emit('hyakuEnd', { w, hits: w.hyHits, n: w.hyN }); }
        return true;
      }
      if (w.st === 'air') {
        const t = w.t;
        if (t < 0.45) { w.y = 9 * Math.pow(t / 0.45, 1.5); w.x = w.sx0; w.z = w.sz0; }
        else if (t < 1.35) {
          // steer the landing spot: drifts toward them, your stick nudges it
          const tx = o.x + I.mx * 1.6, tz = o.z + I.mz * 1.6;
          w.ax2 += clamp(tx - w.ax2, -3.5 * dt, 3.5 * dt); w.az2 += clamp(tz - w.az2, -3.5 * dt, 3.5 * dt);
          const ad = Math.hypot(w.ax2, w.az2); if (ad > RR - 0.4) { w.ax2 *= (RR - 0.4) / ad; w.az2 *= (RR - 0.4) / ad; }
          w.x = w.ax2; w.z = w.az2; w.y = 9;
        } else { w.x = w.ax2; w.z = w.az2; w.y = 9 * Math.max(0, 1 - (t - 1.35) / 0.3); }
        w.vx = w.vz = 0;
        if (t >= w.dur) {
          w.y = 0; w.set('recover', 0.45); w.squash = 1;
          const [nx, nz, d] = dirTo(w, o);
          if (d < 1.45 && o.st !== 'air' && Skills.parry(m, o, w, nx, nz, true)) { w.set('stun', 0.6); }
          else if (d < 1.45 && o.st !== 'air' && !(o.fxs.invuln > 0)) {
            if (o.clinch) o.clinch.end('skill');
            o.vx += nx * 6 / Math.max(0.6, o.m); o.vz += nz * 6 / Math.max(0.6, o.m); o.slideT = 0.4;
            m.tag(o, w, 'sk_bellyFlop'); m.hurt(o, 0.62 * (1.45 - d) / 1.45 + 0.25, nx, nz);
          }
          m.emit('impact', { x: w.x, z: w.z, nx: 0, nz: 1, power: 13, closing: 9, zone: 'front', a: w, t: o, agg: true, flop: true });
        }
        return true;
      }
      return false;
    },

    // world objects + continuous effects
    update(m, dt) {
      for (const w of m.w) {
        const f = w.fxs;
        if (f.quake > 0 && !w.down && m.phase === 'fight') {
          w.vx += (S.rand() - 0.5) * 30 * dt; w.vz += (S.rand() - 0.5) * 30 * dt;
          // the ground heaves: every so often it throws them a step in a random direction
          w.qT -= dt;
          if (w.qT <= 0 && !w.clinch) {
            w.qT = 0.28 + S.rand() * 0.18;
            const a = S.rand() * Math.PI * 2; w.vx += Math.cos(a) * 2.8; w.vz += Math.sin(a) * 2.8; w.slideT = Math.max(w.slideT, 0.22);
            m.hurt(w, 0.05, Math.cos(a), Math.sin(a)); m.emit('quakeDust', { x: w.x, z: w.z });
          }
          m.hurt(w, dt * 0.16, S.rand() - 0.5, S.rand() - 0.5);
          if (S.rand() < dt * 10) m.emit('quakeDust', { x: w.x, z: w.z });
        }
        if (f.burning > 0 && m.phase === 'fight' && !w.swallowed) {
          m.hurt(w, dt * 0.9, S.rand() - 0.5, S.rand() - 0.5);
          if (S.rand() < dt * 5) { const a = S.rand() * Math.PI * 2; w.vx += Math.cos(a) * 1.4; w.vz += Math.sin(a) * 1.4; }
          if (w.st === 'brace') w.set('free');
        }
        if (f.poison > 0) { f.dizzy = Math.max(f.dizzy || 0, 0.05); if (S.rand() < dt * 1.2 && !w.clinch && w.st === 'free') { w.set('stumble'); w.sdx = Math.cos(w.f); w.sdz = Math.sin(w.f); m.hurt(w, 0.08, w.sdx, w.sdz); } }
        if (f.dizzy > 0) { w.tx += Math.sin(m.time * 9) * dt * 0.6; w.tz += Math.cos(m.time * 7) * dt * 0.6; }
        if (f.turnLock > 0 && !w.clinch) w.fw = 0;
        // BUMPER RING: the straw throws you back in
        if (f.bumper > 0 && m.phase === 'fight' && !w.swallowed && !(f.bumpCD > 0)) {
          const d = Math.hypot(w.x, w.z);
          if (d > RR - 0.28) {
            const nx = w.x / d, nz = w.z / d, out = w.vx * nx + w.vz * nz;
            if (w.clinch) w.clinch.end('skill');
            w.vx -= nx * (Math.max(0, out) * 2 + 4.5); w.vz -= nz * (Math.max(0, out) * 2 + 4.5);
            w.x = nx * (RR - 0.32); w.z = nz * (RR - 0.32); f.bumpCD = 0.25;
            if (w.st === 'fall' || w.st === 'stumble') w.set('recover', 0.2);
            m.emit('bump', { w, x: nx * RR, z: nz * RR });
          }
        }
        // ROLLING BALL: hit them at speed and they fly
        if (f.ball > 0 && m.phase === 'fight' && w.ballHitT <= 0) {
          const o = w.opp, dx = o.x - w.x, dz = o.z - w.z, d = Math.hypot(dx, dz) || 1e-4, nx = dx / d, nz = dz / d;
          const closing = (w.vx - o.vx) * nx + (w.vz - o.vz) * nz;
          if (d < w.r + o.r + 0.1 && closing > 2.2 && o.st !== 'air' && !o.swallowed) {
            w.ballHitT = 0.45;
            if (Skills.parry(m, o, null, nx, nz)) { w.vx = -nx * 4; w.vz = -nz * 4; }
            else if (!(o.fxs.invuln > 0)) {
              if (o.clinch) o.clinch.end('skill');
              const pw = (closing * 1.05 + 2) / Math.max(0.6, o.m);
              o.vx += nx * pw; o.vz += nz * pw; o.slideT = 0.5;
              m.tag(o, w, 'sk_ball'); m.hurt(o, 0.08 * closing, nx, nz);
              if (o.st !== 'fall') { o.set('stumble'); o.sdx = nx; o.sdz = nz; }
              w.vx *= 0.3; w.vz *= 0.3;
              m.emit('ballHit', { w, o, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, power: closing });
            }
          }
        }
        if (w.ballHitT > 0) w.ballHitT -= dt;
        // CYCLONE: touch the top and you're thrown off it, sideways and out
        if (f.cyclone > 0 && m.phase === 'fight' && !(w.cycHitT > 0)) {
          const o = w.opp, dx = o.x - w.x, dz = o.z - w.z, d = Math.hypot(dx, dz) || 1e-4, nx = dx / d, nz = dz / d;
          if (d < w.r + o.r + 0.2 && o.st !== 'air' && !o.swallowed && !(o.fxs.invuln > 0)) {
            w.cycHitT = 0.5;
            if (Skills.parry(m, o, null, nx, nz)) { w.vx = -nx * 3; w.vz = -nz * 3; }
            else {
              if (o.clinch) o.clinch.end('skill');
              const tx = -nz, tz = nx, pw = 7.5 / Math.max(0.6, o.m); // out, plus a sideways whip from the spin
              o.vx += (nx * 0.8 + tx * 0.6) * pw; o.vz += (nz * 0.8 + tz * 0.6) * pw; o.slideT = 0.5;
              m.tag(o, w, 'sk_cyclone'); m.hurt(o, 0.1, nx, nz);
              if (o.st !== 'fall') { o.set('stumble'); o.sdx = nx; o.sdz = nz; }
              m.emit('cycloneHit', { w, o, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2 });
            }
          }
        }
        if (w.cycHitT > 0) w.cycHitT -= dt;
        if (w.gulpI >= 0 && m.phase === 'fight' && w.st !== 'spit') { w.gulpT += dt; if (w.gulpT > 5) Skills.spit(m, w); } // can't hold them forever
        if (m.phase === 'fight' && !w.swallowed && !w.down) {
          w.trailT += dt;
          if (w.trailT >= 0.1) { w.trailT -= 0.1; w.trail.push([w.x, w.z, w.f]); if (w.trail.length > 30) w.trail.shift(); }
        }
        if (w.swallowed && m.phase !== 'fight') { w.swallowed = false; const g = m.w[1 - w.idx]; g.gulpI = -1; w.x = g.x + Math.cos(g.f) * (g.r + w.r); w.z = g.z + Math.sin(g.f) * (g.r + w.r); }
        if (w.boomT > 0) {
          if (m.phase !== 'fight') { w.boomT = 0; continue; }
          w.boomT -= dt;
          if (w.boomT <= 0) Skills.explode(m, w);
        }
      }
      for (let i = m.objs.length - 1; i >= 0; i--) {
        const ob = m.objs[i];
        ob.t += dt;
        if (ob.type === 'banana') {
          for (const w of m.w) {
            if (w === ob.owner && ob.t < 1.0) continue;
            if (w.st === 'air' || w.lifted || w.down) continue;
            if (Math.hypot(w.x - ob.x, w.z - ob.z) < w.r * 0.55 + 0.2) {
              const sp = w.spd || 1, dx = w.spd > 0.3 ? w.vx / sp : w.fx, dz = w.spd > 0.3 ? w.vz / sp : w.fz;
              if (w.clinch) w.clinch.end('slip');
              if (w !== ob.owner) m.tag(w, ob.owner, 'sk_banana');
              w.vx += dx * 3; w.vz += dz * 3;
              // feet fly out: flat on their back, and that loses the bout
              if (w.st !== 'fall') { w.set('fall', 0.3); w.fallX = -dx; w.fallZ = -dz; }
              m.emit('slip', { w, x: ob.x, z: ob.z });
              ob.t = ob.dur;
            }
          }
        } else if (ob.type === 'trap') {
          const own = ob.owner, vic = own.opp;
          if (!ob.armed && Math.hypot(own.x - ob.x, own.z - ob.z) > 0.9) ob.armed = true;
          if (ob.armed && m.phase === 'fight' && vic.st !== 'air' && !vic.lifted && Math.hypot(vic.x - ob.x, vic.z - ob.z) < 0.5) {
            if (vic.clinch) vic.clinch.end('trap');
            vic.x = ob.x; vic.z = ob.z; vic.vx = vic.vz = 0; vic.trapped = true;
            m.tag(vic, own, 'sk_trap');
            m.emit('trapdoor', { w: vic, x: ob.x, z: ob.z });
            vic.set('fall', 0.3); vic.fallX = 0; vic.fallZ = 1; vic.down = true;
            ob.sprung = true; ob.dur = ob.t + 2.5;
          }
        } else if (ob.type === 'barrage') {
          ob.next -= dt;
          if (ob.next <= 0 && ob.t < ob.dur) {
            ob.next = 0.32;
            const T = ob.target, a = S.rand() * Math.PI * 2;
            const sx = T.x + Math.cos(a) * 9, sz = T.z + Math.sin(a) * 9;
            const ft = 0.75, tx = T.x + T.vx * 0.4, tz = T.z + T.vz * 0.4;
            m.objs.push({ type: 'proj', x: sx, y: 3, z: sz, vx: (tx - sx) / ft, vz: (tz - sz) / ft, vy: (1.2 - 3 + 0.5 * 9 * ft * ft) / ft, t: 0, dur: 8, target: T, owner: ob.owner, kind: (S.rand() * 3) | 0, live: true });
          }
        } else if (ob.type === 'proj') {
          if (ob.live) {
            ob.vy -= 9 * dt; ob.x += ob.vx * dt; ob.y += ob.vy * dt; ob.z += ob.vz * dt;
            const T = ob.target;
            const vl = Math.hypot(ob.vx, ob.vz) || 1;
            if (ob.y < 2 && Math.hypot(T.x - ob.x, T.z - ob.z) < T.r + 0.15 && Skills.parry(m, T, null, ob.vx / vl, ob.vz / vl)) { ob.vx = -ob.vx * 0.6; ob.vz = -ob.vz * 0.6; ob.vy = 3; ob.target = T.opp; }
            else if (ob.y < 2 && Math.hypot(T.x - ob.x, T.z - ob.z) < T.r + 0.15 && !(T.fxs.invuln > 0)) {
              ob.live = false; ob.y = 0.06;
              if (T.st !== 'fall' && !T.down) { if (T.clinch) T.clinch.end('barrage'); if (!['air'].includes(T.st)) T.set('stun', 0.2); }
              T.vx += ob.vx * 0.08; T.vz += ob.vz * 0.08;
              m.tag(T, ob.owner, 'sk_barrage'); m.hurt(T, 0.05, ob.vx, ob.vz);
              m.emit('projHit', { x: ob.x, z: ob.z, w: T });
            } else if (ob.y <= 0.06) { ob.live = false; ob.y = 0.06; }
          }
        } else if (ob.type === 'beartrap') {
          const own = ob.owner, vic = own.opp;
          if (!ob.armed && Math.hypot(own.x - ob.x, own.z - ob.z) > 0.9) ob.armed = true;
          if (ob.armed && !ob.sprung && m.phase === 'fight' && vic.st !== 'air' && !vic.lifted && !vic.swallowed && Math.hypot(vic.x - ob.x, vic.z - ob.z) < 0.5) {
            ob.sprung = true; ob.dur = ob.t + 3.3; ob.victim = vic;
            if (vic.clinch) vic.clinch.end('trap');
            vic.fxs.snared = 3; vic.gx = ob.x; vic.gz = ob.z; vic.set('stun', 0.1);
            m.emit('snap', { w: vic, x: ob.x, z: ob.z });
          }
          // grabbed or lifted: they come out of the trap with whoever is holding them
          if (ob.sprung && ob.victim && ob.victim.fxs.snared > 0 && (ob.victim.clinch || ob.victim.lifted)) { ob.victim.fxs.snared = 0; ob.dur = Math.min(ob.dur, ob.t + 0.4); }
        } else if (ob.type === 'hole') {
          // a tiny point of gravity: pulls everything in, harder the closer it is
          for (const p of m.w) {
            if (p.st === 'air' || p.swallowed || p.clinch || m.phase !== 'fight') continue;
            const dx = ob.x - p.x, dz = ob.z - p.z, d = Math.hypot(dx, dz);
            if (d < 0.15) { p.vx *= Math.exp(-dt * 6); p.vz *= Math.exp(-dt * 6); continue; }
            const a = Math.min(13, 9 / (d + 0.35));
            p.vx += dx / d * a * dt; p.vz += dz / d * a * dt; p.slideT = Math.max(p.slideT, 0.1);
            if (p !== ob.owner) m.tag(p, ob.owner, 'sk_hole');
          }
          for (const q of m.objs) if (q.type === 'bomb' || q.type === 'fish') { const dx = ob.x - q.x, dz = ob.z - q.z, d = Math.hypot(dx, dz) || 1; q.vx += dx / d * 6 * dt; q.vz += dz / d * 6 * dt; }
        } else if (ob.type === 'fish') {
          // a live tuna: random flops, bounces off the straw, knocks people over
          ob.hopT -= dt;
          if (ob.hopT <= 0) { ob.hopT = 0.3 + S.rand() * 0.45; const a = S.rand() * Math.PI * 2, sp = 3 + S.rand() * 3.5; ob.vx = Math.cos(a) * sp; ob.vz = Math.sin(a) * sp; ob.spin = (S.rand() - 0.5) * 18; }
          const k = Math.exp(-dt * 1.6); ob.vx *= k; ob.vz *= k;
          ob.x += ob.vx * dt; ob.z += ob.vz * dt;
          const d0 = Math.hypot(ob.x, ob.z);
          if (d0 > RR - 0.35) { const nx = ob.x / d0, nz = ob.z / d0, vn = ob.vx * nx + ob.vz * nz; if (vn > 0) { ob.vx -= 2 * vn * nx; ob.vz -= 2 * vn * nz; } ob.x = nx * (RR - 0.35); ob.z = nz * (RR - 0.35); }
          for (const p of m.w) {
            ob.cd[p.idx] -= dt;
            if (ob.cd[p.idx] > 0 || p.st === 'air' || p.swallowed || m.phase !== 'fight') continue;
            const dx = p.x - ob.x, dz = p.z - ob.z, d = Math.hypot(dx, dz) || 1e-4;
            if (d > p.r + 0.5 || Math.hypot(ob.vx, ob.vz) < 0.8) continue;
            ob.cd[p.idx] = 0.6;
            const nx = dx / d, nz = dz / d;
            if (Skills.parry(m, p, null, nx, nz)) { ob.vx = -nx * 6; ob.vz = -nz * 6; continue; }
            if (p.fxs.invuln > 0) continue;
            if (p.clinch) p.clinch.end('skill');
            p.vx += nx * 3.8 / Math.max(0.6, p.m); p.vz += nz * 3.8 / Math.max(0.6, p.m); p.slideT = 0.35;
            m.hurt(p, 0.16, nx, nz); m.tag(p, p.opp, 'sk_fish');
            if (p.st !== 'fall') p.set('stun', 0.25);
            ob.vx = -nx * 2.5; ob.vz = -nz * 2.5;
            m.emit('fishHit', { w: p, x: ob.x, z: ob.z });
          }
        } else if (ob.type === 'bomb') {
          // shove it, slap it, but don't slap it too often
          const k = Math.exp(-dt * 2.2); ob.vx *= k; ob.vz *= k; ob.x += ob.vx * dt; ob.z += ob.vz * dt;
          for (const p of m.w) {
            ob.cd[p.idx] -= dt;
            const dx = ob.x - p.x, dz = ob.z - p.z, d = Math.hypot(dx, dz) || 1e-4, nx = dx / d, nz = dz / d;
            const reach = p.r + 0.32;
            if (d < reach && !p.swallowed && p.st !== 'air') {
              ob.x = p.x + nx * reach; ob.z = p.z + nz * reach;
              const vin = p.vx * nx + p.vz * nz; if (vin > 0) { ob.vx += nx * vin * 1.3; ob.vz += nz * vin * 1.3; }
            }
            const striking = ['palm', 'heavy', 'charge', 'sslap', 'hyaku', 'dash'].includes(p.st) || p.fxs.ball > 0;
            if (striking && ob.cd[p.idx] <= 0 && d < p.r + 0.75 && (p.fx * nx + p.fz * nz > 0.3 || p.fxs.ball > 0)) {
              ob.cd[p.idx] = 0.35; ob.hits++; ob.vx += nx * 5.5; ob.vz += nz * 5.5;
              m.emit('bombHit', { x: ob.x, z: ob.z, hits: ob.hits });
            }
          }
          if (!ob.gone && (ob.t >= 5 || ob.hits >= 4 || Math.hypot(ob.x, ob.z) > RR + 1.5)) {
            ob.gone = true; ob.dur = ob.t;
            for (const p of m.w) {
              if (p.swallowed || p.st === 'air') continue;
              const dx = p.x - ob.x, dz = p.z - ob.z, d = Math.hypot(dx, dz) || 1e-4;
              if (d > 2.6 || p.fxs.invuln > 0 || m.phase !== 'fight') continue;
              const kk = 1 - d / 2.6, nx = dx / d, nz = dz / d;
              if (p.clinch) p.clinch.end('skill');
              p.vx += nx * (4 + 8 * kk) / Math.max(0.6, p.m); p.vz += nz * (4 + 8 * kk) / Math.max(0.6, p.m); p.slideT = 0.6;
              m.hurt(p, 0.3 + 0.5 * kk, nx, nz); m.tag(p, p.opp, 'sk_bomb');
              if (kk > 0.55 && p.st !== 'fall') { p.set('fall', 0.3); p.fallX = nx; p.fallZ = nz; }
              else if (p.st !== 'fall') { p.set('stumble'); p.sdx = nx; p.sdz = nz; }
            }
            m.emit('boom', { w: ob.owner, x: ob.x, z: ob.z, k: 0.9 });
          }
        } else if (ob.type === 'wave') {
          // the shockwave rolls outward; parry it or dash through it
          ob.r = ob.owner.r + ob.t * 5.2;
          const T = ob.owner.opp;
          if (!ob.done && m.phase === 'fight' && !T.swallowed && T.st !== 'air') {
            const dx = T.x - ob.x, dz = T.z - ob.z, d = Math.hypot(dx, dz) || 1e-4;
            if (Math.abs(d - ob.r) < 0.32) {
              const nx = dx / d, nz = dz / d;
              if (T.st === 'dash' || T.fxs.thru > 0) { /* dashed through it */ }
              else {
                ob.done = true;
                if (Skills.parry(m, T, null, nx, nz)) { /* broke it */ }
                else if (!(T.fxs.invuln > 0)) {
                  if (T.clinch) T.clinch.end('skill');
                  T.vx += nx * 5.5 / Math.max(0.6, T.m); T.vz += nz * 5.5 / Math.max(0.6, T.m); T.slideT = 0.5;
                  m.hurt(T, 0.35, nx, nz); m.tag(T, ob.owner, 'sk_wave');
                  if (T.st !== 'fall') { T.set('stumble'); T.sdx = nx; T.sdz = nz; }
                  m.emit('waveHit', { w: T, x: T.x, z: T.z });
                }
              }
            }
          }
        } else if (ob.type === 'clones') {
          // the clones copy your every step; touch one and it's gone
          const own = ob.owner, T = own.opp;
          for (const c of ob.c) {
            if (!c.alive) continue;
            // each clone stalks them on its own: circling, feinting in and out, switching direction
            c.think -= dt;
            if (c.think <= 0) { c.think = 0.4 + S.rand() * 0.8; if (S.rand() < 0.35) c.dir = -c.dir; if (S.rand() < 0.3) c.lunge = 0.45; }
            c.lunge -= dt; c.ang += c.dir * 0.9 * dt;
            const rad = c.lunge > 0 ? own.r + T.r + 0.5 : own.r + T.r + 0.9 + Math.sin(ob.t * 2 + c.ang) * 0.25;
            let tx = T.x + Math.cos(c.ang) * rad, tz = T.z + Math.sin(c.ang) * rad; const tl = Math.hypot(tx, tz); if (tl > RR - 0.5) { tx *= (RR - 0.5) / tl; tz *= (RR - 0.5) / tl; }
            const dx = tx - c.x, dz = tz - c.z, dl = Math.hypot(dx, dz) || 1, want = Math.min(3.4, dl * 4);
            c.vx += (dx / dl * want - c.vx) * Math.min(1, dt * 8); c.vz += (dz / dl * want - c.vz) * Math.min(1, dt * 8);
            c.x += c.vx * dt; c.z += c.vz * dt;
            const dc = Math.hypot(c.x, c.z);
            const reach = own.r + T.r + (['palm', 'heavy', 'charge'].includes(T.st) ? 0.35 : 0.02);
            if (dc > RR || Math.hypot(T.x - c.x, T.z - c.z) < reach || m.phase !== 'fight') { c.alive = false; m.emit('poof', { x: c.x, z: c.z }); }
          }
          if (!ob.c.some((c) => c.alive)) ob.dur = ob.t;
          else if (ob.t >= ob.dur - dt) for (const c of ob.c) if (c.alive) { c.alive = false; m.emit('poof', { x: c.x, z: c.z }); }
        } else if (ob.type === 'potato') {
          // stuck to the holder; touching the other wrestler passes it on
          const H = m.w[ob.holder], O = H.opp;
          ob.cd -= dt;
          if (ob.cd <= 0 && !O.swallowed && !H.swallowed && Math.hypot(H.x - O.x, H.z - O.z) < H.r + O.r + 0.15) {
            ob.holder = O.idx; ob.cd = 0.6; m.emit('potatoPass', { w: O, x: O.x, z: O.z });
          }
          if (m.phase !== 'fight') ob.dur = ob.t;
          else if (ob.t >= ob.dur - dt) {
            const V = m.w[ob.holder];
            if (!(V.fxs.invuln > 0) && !V.swallowed) {
              if (V.clinch) V.clinch.end('skill');
              const a = S.rand() * Math.PI * 2;
              V.vx += Math.cos(a) * 3; V.vz += Math.sin(a) * 3;
              m.tag(V, V.opp, 'sk_potato'); m.hurt(V, 1, Math.cos(a), Math.sin(a));
              if (V.st !== 'fall') { V.set('fall', 0.3); V.fallX = Math.cos(a); V.fallZ = Math.sin(a); }
              const Q = V.opp, dq = Math.hypot(Q.x - V.x, Q.z - V.z);
              if (dq < 2 && !(Q.fxs.invuln > 0) && !Q.swallowed) { const nx = (Q.x - V.x) / (dq || 1), nz = (Q.z - V.z) / (dq || 1); Q.vx += nx * 3.5; Q.vz += nz * 3.5; if (Q.st !== 'fall') { Q.set('stumble'); Q.sdx = nx; Q.sdz = nz; } }
            }
            m.emit('boom', { w: V, x: V.x, z: V.z, k: 0.7 });
          }
        } else if (ob.type === 'claw') {
          // the crane: hunt, drop, grab, carry, release
          ob.mt += dt;
          if (ob.mode === 'hunt') {
            const T = ob.owner.opp, dx = T.x - ob.x, dz = T.z - ob.z, d = Math.hypot(dx, dz) || 1;
            const sp = Math.min(2.6, d * 3); ob.x += dx / d * sp * dt + (S.rand() - 0.5) * 0.04; ob.z += dz / d * sp * dt + (S.rand() - 0.5) * 0.04;
            ob.h = 3.4;
            if (ob.mt > ob.huntFor) { ob.mode = 'drop'; ob.mt = 0; }
          } else if (ob.mode === 'drop') {
            ob.h = 3.4 - 1.9 * Math.min(1, ob.mt / 0.4);
            if (ob.mt >= 0.4) {
              let best = null, bd = 0.85;
              for (const p of m.w) { const d = Math.hypot(p.x - ob.x, p.z - ob.z); if (d < bd && p.st !== 'air' && !p.swallowed && !(p.fxs.invuln > 0)) { best = p; bd = d; } }
              if (best && m.phase === 'fight') {
                if (best.clinch) best.clinch.end('skill');
                best.carried = true; ob.victim = best.idx; ob.mode = 'carry'; ob.mt = 0;
                const a = S.rand() * Math.PI * 2, r = S.rand() * (RR + 1.4);
                ob.dx = Math.cos(a) * r; ob.dz = Math.sin(a) * r;
                m.emit('clawGrab', { w: best, x: ob.x, z: ob.z });
              } else { ob.mode = 'rise'; ob.mt = 0; }
            }
          } else if (ob.mode === 'rise') {
            ob.h = 1.5 + 1.9 * Math.min(1, ob.mt / 0.4);
            if (ob.mt >= 0.4) { ob.mode = 'hunt'; ob.mt = 0; ob.huntFor = 1.0 + S.rand() * 0.8; }
          } else if (ob.mode === 'carry') {
            const V = m.w[ob.victim];
            ob.h = Math.min(3.6, 1.5 + ob.mt * 4);
            if (ob.mt > 0.4) { const dx = ob.dx - ob.x, dz = ob.dz - ob.z, d = Math.hypot(dx, dz); if (d > 0.05) { const sp = Math.min(3.2, d * 4); ob.x += dx / d * sp * dt; ob.z += dz / d * sp * dt; } else { ob.mode = 'release'; ob.mt = 0; } }
            V.x = ob.x; V.z = ob.z; V.y = Math.max(0, ob.h - 1.75); V.vx = V.vz = 0;
            if (m.phase !== 'fight') { ob.mode = 'release'; ob.mt = 0; }
          } else if (ob.mode === 'release') {
            const V = m.w[ob.victim];
            if (V && V.carried) {
              V.carried = false; V.ghostT = 0.2; if (V.st !== 'fall') V.set('stun', 0.3);
              if (Math.hypot(V.x, V.z) > RR) m.tag(V, ob.owner.idx === V.idx ? V.opp : ob.owner, 'sk_claw');
              m.emit('clawDrop', { w: V, x: V.x, z: V.z });
            }
            ob.h += dt * 4; if (ob.mt > 0.8) ob.dur = ob.t;
          }
          if (ob.t >= ob.dur - dt && ob.victim >= 0 && m.w[ob.victim].carried) m.w[ob.victim].carried = false;
        } else if (ob.type === 'doors') {
          // walk into a door, come out of either one
          const D = [[Math.cos(ob.a) * (RR - 0.9), Math.sin(ob.a) * (RR - 0.9)], [-Math.cos(ob.a) * (RR - 0.9), -Math.sin(ob.a) * (RR - 0.9)]];
          for (const p of m.w) {
            ob.cd[p.idx] -= dt;
            if (ob.cd[p.idx] > 0 || p.st === 'air' || p.swallowed || p.carried || p.clinch || m.phase !== 'fight') continue;
            for (let k = 0; k < 2; k++) {
              if (Math.hypot(p.x - D[k][0], p.z - D[k][1]) > 0.75) continue;
              const out = S.rand() < 0.5 ? k : 1 - k, ex = D[out][0], ez = D[out][1], l = Math.hypot(ex, ez) || 1;
              m.emit('poof', { x: p.x, z: p.z });
              p.x = ex - ex / l * 0.55; p.z = ez - ez / l * 0.55; p.vx = -ex / l * 2.5; p.vz = -ez / l * 2.5; p.ghostT = 0.3;
              ob.cd[p.idx] = 1.2; m.emit('door', { w: p, x: p.x, z: p.z, same: out === k });
              break;
            }
          }
        } else if (ob.type === 'pickup') {
          // a skill lying on the floor: first empty-handed wrestler to reach it keeps it
          for (const p of m.w) {
            if (m.skills[p.idx] || p.st === 'air' || p.swallowed || p.carried || p.down) continue;
            if (Math.hypot(p.x - ob.x, p.z - ob.z) < p.r + 0.2) {
              m.skills[p.idx] = ob.id; m.fakeName[p.idx] = ob.fakeOf || null; ob.dur = ob.t;
              m.emit('pickup', { w: p, id: ob.id, x: ob.x, z: ob.z }); break;
            }
          }
        } else if (ob.type === 'spin') {
          // the dohyo turns: everyone standing on it goes round, and gets flung outward
          const wv = 1.15 * Math.min(1, ob.t / 0.8) * Math.min(1, (ob.dur - ob.t) / 0.6), da = wv * dt;
          ob.a += da;
          const c = Math.cos(da), s = Math.sin(da);
          for (const p of m.w) {
            if (p.st === 'air' || p.carried || p.swallowed) continue;
            const x = p.x, z = p.z; p.x = x * c - z * s; p.z = x * s + z * c; p.f = S.wrap(p.f + da);
            const r = Math.hypot(p.x, p.z);
            if (r > 0.2) { const k = wv * wv * r * 0.55 * dt; p.vx += p.x / r * k; p.vz += p.z / r * k; m.tag(p, p.opp, 'sk_spin'); }
          }
          for (const q of m.objs) if (['banana', 'trap', 'beartrap', 'hole', 'pickup'].includes(q.type)) { const x = q.x, z = q.z; q.x = x * c - z * s; q.z = x * s + z * c; }
        } else if (ob.type === 'train') {
          // bells, then the express: anyone in the lane gets flattened
          const dx = Math.cos(ob.a), dz = Math.sin(ob.a), px = -dz, pz = dx;
          if (ob.t >= ob.warn) {
            if (!ob.go) { ob.go = true; m.emit('trainGo', {}); }
            ob.front = -14 + (ob.t - ob.warn) * 52;   // (a long shinkansen: 38 long)
            for (const p of m.w) {
              if (ob.hit[p.idx] || p.st === 'air' || p.swallowed || p.carried || m.phase !== 'fight') continue;
              const u = p.x * dx + p.z * dz, v = p.x * px + p.z * pz - ob.off;
              if (Math.abs(v) < 1.05 + p.r * 0.5 && ob.front >= u && ob.front - 38 <= u) {
                ob.hit[p.idx] = true;
                if (p.fxs.invuln > 0) continue;
                if (p.clinch) p.clinch.end('skill');
                const sd = v >= 0 ? 1 : -1;
                p.vx += dx * 13 + px * sd * 3; p.vz += dz * 13 + pz * sd * 3; p.slideT = 0.8;
                m.tag(p, p === ob.owner ? p.opp : ob.owner, 'sk_train'); m.hurt(p, 1, dx, dz);
                if (p.st !== 'fall') { p.set('fall', 0.3); p.fallX = dx; p.fallZ = dz; }
                m.emit('trainHit', { w: p, x: p.x, z: p.z });
              }
            }
          }
        } else if (ob.type === 'konbini') {
          // a little shop: the owner walks in for a random boost; the other wrestler can wreck it
          const own = ob.owner, T = own.opp;
          ob.shake = Math.max(0, ob.shake - dt * 4);
          for (const p of m.w) {
            ob.cd[p.idx] -= dt;
            if (p.swallowed || p.carried || p.st === 'air' || p.inShop) continue;
            const dx = p.x - ob.x, dz = p.z - ob.z, d = Math.hypot(dx, dz) || 1e-4, reach = p.r + 0.7;
            if (p === own && !ob.used && d < reach + 0.05 && m.phase === 'fight') {
              if (p.clinch) p.clinch.end('skill');
              p.inShop = true; p.x = ob.x; p.z = ob.z; ob.used = true; ob.it = 0; m.emit('shopIn', { w: p, x: ob.x, z: ob.z }); continue;
            }
            if (d < reach) { p.x = ob.x + dx / d * reach; p.z = ob.z + dz / d * reach; const vin = -(p.vx * dx + p.vz * dz) / d; if (vin > 0) { p.vx += dx / d * vin; p.vz += dz / d * vin; } }
            const striking = ['palm', 'heavy', 'charge', 'sslap', 'hyaku'].includes(p.st) || p.fxs.ball > 0;
            if (p === T && striking && ob.cd[p.idx] <= 0 && d < reach + 0.5 && (p.fx * -dx + p.fz * -dz) / d > 0.3) {
              ob.cd[p.idx] = 0.35; const dmg = 50 + ((S.rand() * 51) | 0); ob.hp = Math.max(0, ob.hp - dmg); ob.shake = 1; m.emit('shopHit', { x: ob.x, z: ob.z, hp: ob.hp, dmg });
              if (ob.hp <= 0) {
                ob.dur = ob.t;
                if (own.inShop) { own.inShop = false; own.x = ob.x + dx / d * -0.9; own.z = ob.z + dz / d * -0.9; own.set('stun', 0.6); own.ghostT = 0.3; }
                m.emit('shopBreak', { x: ob.x, z: ob.z });
              }
            }
          }
          if (own.inShop && ob.used && ob.dur > ob.t) {
            ob.it += dt;
            // leave when you've bought something, chosen to leave, or browsed too long
            if (ob.bought || ob.leave || ob.it >= 15 || m.phase !== 'fight') {
              own.inShop = false; own.ghostT = 0.3;
              const a = Math.atan2(-ob.z, -ob.x); own.x = ob.x + Math.cos(a) * 1.0; own.z = ob.z + Math.sin(a) * 1.0; own.f = a;
              if (ob.bought && m.phase === 'fight') { m.skills[own.idx] = ob.bought; m.fakeName[own.idx] = null; m.emit('shopBuy', { w: own, id: ob.bought, x: own.x, z: own.z }); }
              m.emit('shopOut', { w: own });
              ob.dur = ob.t + 0.4;
            }
          }
          if (ob.t >= ob.dur - dt && own.inShop) { own.inShop = false; }
        } else if (ob.type === 'bag') {
          // whoever reaches it first eats it: 50/50
          for (const p of m.w) {
            if (p.swallowed || p.carried || p.inShop || p.st === 'air' || p.down || m.phase !== 'fight') continue;
            if (Math.hypot(p.x - ob.x, p.z - ob.z) < p.r + 0.3) {
              const good = S.rand() < 0.5;
              if (good) p.fxs.giant = 4; else { p.fxs.poison = 4; }
              ob.dur = ob.t; m.emit('eat', { w: p, good, x: ob.x, z: ob.z }); break;
            }
          }
        } else if (ob.type === 'spot') {
          if (m.phase !== 'fight') ob.dur = ob.t;
        } else if (ob.type === 'third') {
          // the third wrestler: picks on whoever is closest, slaps them toward the edge, can be shoved out itself
          ob.stT -= dt; if (ob.stT <= 0 && ob.st !== 'free') ob.st = 'free';
          ob.cd -= dt;
          if (m.phase !== 'fight') { ob.vx *= 0.8; ob.vz *= 0.8; }
          else {
            let T = null, td = 1e9;
            for (const p of m.w) { if (p.down || p.swallowed || p.carried || p.inShop || p.st === 'air') continue; const d = Math.hypot(p.x - ob.x, p.z - ob.z); if (d < td) { td = d; T = p; } }
            if (T && ob.st !== 'stun') {
              const nx = (T.x - ob.x) / (td || 1), nz = (T.z - ob.z) / (td || 1);
              ob.f += S.wrap(Math.atan2(nz, nx) - ob.f) * Math.min(1, dt * 6);
              const want = td > ob.r + T.r + 0.1 ? 2.6 : 0.6;
              ob.vx += (nx * want - ob.vx) * Math.min(1, dt * 5); ob.vz += (nz * want - ob.vz) * Math.min(1, dt * 5);
              if (td < ob.r + T.r + 0.35 && ob.cd <= 0) {
                ob.cd = 0.55 + S.rand() * 0.35; ob.st = 'palm'; ob.stT = 0.25; ob.hand ^= 1;
                if (Skills.parry(m, T, null, nx, nz)) { ob.vx -= nx * 3; ob.vz -= nz * 3; ob.st = 'stun'; ob.stT = 0.5; }
                else if (!(T.fxs.invuln > 0)) {
                  if (T.clinch) T.clinch.end('skill');
                  T.vx += nx * 3.2 / Math.max(0.6, T.m); T.vz += nz * 3.2 / Math.max(0.6, T.m); T.slideT = Math.max(T.slideT, 0.25);
                  T.thirdT = m.time; m.hurt(T, 0.1, nx, nz);
                  m.emit('thirdHit', { x: (T.x + ob.x) / 2, z: (T.z + ob.z) / 2 });
                }
              }
            }
            // bodies bump; strikes from the wrestlers knock it back
            for (const p of m.w) {
              if (p.swallowed || p.carried || p.inShop || p.st === 'air') continue;
              const dx = ob.x - p.x, dz = ob.z - p.z, d = Math.hypot(dx, dz) || 1e-4, min = ob.r + p.r;
              if (d < min) {
                const nx = dx / d, nz = dz / d, pen = min - d;
                ob.x += nx * pen * 0.55; ob.z += nz * pen * 0.55; p.x -= nx * pen * 0.45; p.z -= nz * pen * 0.45;
                const striking = ['palm', 'heavy', 'charge', 'sslap', 'hyaku'].includes(p.st) || p.fxs.ball > 0;
                const pin = p.vx * nx + p.vz * nz;
                if (pin > 0) { ob.vx += nx * pin * (striking ? 1.6 : 0.8); ob.vz += nz * pin * (striking ? 1.6 : 0.8); }
                if (striking && ob.st !== 'stun') { ob.vx += nx * 2.5; ob.vz += nz * 2.5; ob.st = 'stun'; ob.stT = 0.35; }
              }
            }
          }
          ob.x += ob.vx * dt; ob.z += ob.vz * dt; ob.vx *= Math.exp(-dt * 1.5); ob.vz *= Math.exp(-dt * 1.5);
          if (Math.hypot(ob.x, ob.z) > RR && m.phase === 'fight') { ob.dur = ob.t; m.emit('thirdOut', { x: ob.x, z: ob.z }); } // out for this round
        } else if (ob.type === 'storm') {
          // three bolts: the mark follows them, then locks, then the sky strikes
          const T = ob.owner.opp;
          ob.flash = Math.max(0, ob.flash - dt * 6);
          if (ob.strikeAt < 0) {
            ob.next -= dt;
            if (ob.next <= 0 && ob.n < 3) { ob.strikeAt = ob.t + 0.75; ob.x = T.x; ob.z = T.z; m.emit('boltWarn', { x: ob.x, z: ob.z }); }
          } else {
            if (ob.t < ob.strikeAt - 0.3) { ob.x += (T.x - ob.x) * Math.min(1, dt * 4); ob.z += (T.z - ob.z) * Math.min(1, dt * 4); } // tracks, then locks
            if (ob.t >= ob.strikeAt) {
              ob.n++; ob.strikeAt = -1; ob.next = 0.25; ob.flash = 1; ob.bx = ob.x; ob.bz = ob.z;
              const hit = m.phase === 'fight' && T.st !== 'air' && !T.swallowed && !(T.fxs.invuln > 0) && Math.hypot(T.x - ob.x, T.z - ob.z) < T.r + 0.35;
              if (hit) { if (T.clinch) T.clinch.end('skill'); T.fxs.zapped = 1.3; T.vx *= 0.2; T.vz *= 0.2; m.hurt(T, 0.25, 0, 0, true); m.tag(T, ob.owner, 'sk_bolt'); }
              m.emit('bolt', { x: ob.x, z: ob.z, hit, w: T });
              if (ob.n >= 3) ob.dur = ob.t + 0.4;
            }
          }
        } else if (ob.type === 'molotov') {
          // flight: a lobbed bottle; landing: a burning patch that sets anyone in it on fire
          const FT = 0.8;
          if (!ob.landed) {
            const k = Math.min(1, ob.t / FT); ob.x = ob.sx + (ob.tx - ob.sx) * k; ob.z = ob.sz + (ob.tz - ob.sz) * k; ob.y = 1.6 + 3 * k * (1 - k) - 1.5 * k;
            if (k >= 1) {
              ob.landed = true; ob.y = 0; m.emit('molotovBurst', { x: ob.x, z: ob.z });
              for (const p of m.w) { if (Math.hypot(p.x - ob.x, p.z - ob.z) < ob.R + p.r * 0.5 && p.st !== 'air' && !p.swallowed && !(p.fxs.invuln > 0)) { if (p.clinch) p.clinch.end('skill'); p.fxs.burning = 2.2; p.set('stun', 0.35); m.hurt(p, 0.2, 0, 0, true); m.tag(p, p === ob.owner ? p.opp : ob.owner, 'sk_molotov'); } }
            }
          } else if (m.phase === 'fight') {
            for (const p of m.w) if (Math.hypot(p.x - ob.x, p.z - ob.z) < ob.R + p.r * 0.4 && p.st !== 'air' && !p.swallowed && !p.carried && !(p.fxs.invuln > 0)) { p.fxs.burning = Math.max(p.fxs.burning || 0, 0.9); m.tag(p, p === ob.owner ? p.opp : ob.owner, 'sk_molotov'); }
          }
                } else if (ob.type === 'ref') {
          if (!ob.pushed && ob.t >= 0.32) {
            ob.pushed = true;
            if (m.clinch) m.clinch.end('referee');
            for (const p of m.w) {
              if (p.swallowed) continue;
              let dx = p.x - ob.x, dz = p.z - ob.z, dl = Math.hypot(dx, dz);
              if (dl < 1e-3) { dx = p === m.w[0] ? -1 : 1; dz = 0; dl = 1; }
              p.vx = dx / dl * 4; p.vz = dz / dl * 4; if (p.st !== 'fall') p.set('recover', 0.35);
            }
            m.emit('refBreak', { x: ob.x, z: ob.z });
          }
        } else if (ob.type === 'dart') {
          ob.x += ob.vx * dt; ob.z += ob.vz * dt;
          const T = ob.owner.opp;
          if (!ob.hit && T.st !== 'air' && !T.swallowed && Math.hypot(T.x - ob.x, T.z - ob.z) < T.r + 0.08) {
            ob.hit = true; ob.dur = ob.t;
            const dl = Math.hypot(ob.vx, ob.vz) || 1;
            if (Skills.parry(m, T, null, ob.vx / dl, ob.vz / dl)) { /* swatted away */ }
            else if (!(T.fxs.invuln > 0)) {
              if (T.clinch) T.clinch.end('skill');
              T.fxs.sleep = 2.5; T.set('stun', 0.1);
              m.emit('sleep', { w: T, x: T.x, z: T.z });
            }
          }
          if (Math.hypot(ob.x, ob.z) > RR + 3) ob.dur = ob.t;
        } else if (ob.type === 'fan') {
          const T = ob.target;
          if (T.fxs.grabbed > 0 && T.gx !== undefined) { // dragged slowly toward the crowd
            const dx = ob.ax - T.gx, dz = ob.az - T.gz, d = Math.hypot(dx, dz) || 1;
            T.gx += dx / d * 0.35 * dt; T.gz += dz / d * 0.35 * dt;
          }
        }
        if (ob.t >= ob.dur) m.objs.splice(i, 1);
      }
    },

    spit(m, w) { if (w.clinch) w.clinch.end('skill'); w.set('spit', 0.22); },

    // anything that hits can be parried: DEFEND tapped just before it lands, facing it, knocks it aside.
    // n points from the attack toward T. A (the attacker, if close) is stunned by the deflection.
    parry(m, T, A, nx, nz, anyDir) {
      if (!T || T.down || T.swallowed || T.clinch || !(T.st === 'brace' || T.st === 'free')) return false;
      if (m.time - (T.parryAt === undefined ? -9 : T.parryAt) >= 0.17) return false;
      if (!anyDir && -(T.fx * nx + T.fz * nz) < 0.45) return false;
      if (A && A !== T && Math.hypot(A.x - T.x, A.z - T.z) < 2.5) {
        if (A.st !== 'fall' && A.st !== 'air') A.set('stun', 0.4);
        A.vx -= nx * 2.5; A.vz -= nz * 2.5; m.hurt(A, 0.12, -nx, -nz, true);
      }
      T.parryAt = -9; // one parry per tap
      m.emit('parry', { w: T, o: A || T, x: T.x - nx * 0.6, z: T.z - nz * 0.6 });
      return true;
    },

    // SURPRISE CHALLENGER: the third wrestler steps up at the side of the ring
    spawnThird(m, now) {
      const A = m.w[0], B = m.w[1];
      let px = -(B.z - A.z), pz = B.x - A.x; const l = Math.hypot(px, pz) || 1; px /= l; pz /= l;
      const sd = S.rand() < 0.5 ? 1 : -1;
      m.objs.push({ type: 'third', x: px * sd * (RR - 1.1), z: pz * sd * (RR - 1.1), vx: 0, vz: 0, f: Math.atan2(-pz * sd, -px * sd), t: 0, dur: 1e9, st: 'free', stT: 0, r: 0.78, m: 1.1, cd: 0.8, arch: m.third.arch, hand: 0 });
      if (now) m.emit('poof', { x: px * sd * (RR - 1.1), z: pz * sd * (RR - 1.1) });
    },

    // SKILL THIEF: the slap knocks their skill out onto the floor
    knockSkill(m, w, o, nx, nz) {
      if (!(w.fxs.thiefT > 0) || !m.skills[o.idx]) return;
      let px = o.x + nx * 1.1, pz = o.z + nz * 1.1; const l = Math.hypot(px, pz); if (l > RR - 0.5) { px *= (RR - 0.5) / l; pz *= (RR - 0.5) / l; }
      m.objs.push({ type: 'pickup', id: m.skills[o.idx], fakeOf: m.fakeName[o.idx], x: px, z: pz, t: 0, dur: 8 });
      m.skills[o.idx] = null; m.fakeName[o.idx] = null; w.fxs.thiefT = 0;
      m.emit('knockSkill', { w, o, x: px, z: pz });
    },

    // AUDIENCE FAVOURITE: the crowd shoves them back in (or picks them up), once
    crowdSave(m, w, cause) {
      if (w.clinch) w.clinch.end('skill');
      const d = Math.hypot(w.x, w.z);
      if (cause === 'out' || d > RR - 0.6) {
        const nx = d > 0.01 ? w.x / d : Math.cos(w.f), nz = d > 0.01 ? w.z / d : Math.sin(w.f);
        w.x = nx * (RR - 0.85); w.z = nz * (RR - 0.85); w.vx = -nx * 3; w.vz = -nz * 3;
      } else { w.vx = w.vz = 0; }
      w.down = false; w.out = false; w.lifted = false; w.trapped = false; w.y = 0; w.bal = 1; w.tx = w.tz = 0; w.ghostT = 0.4;
      for (const k of ['sleep', 'frozen', 'grabbed', 'snared', 'possessed', 'chicken', 'ash', 'zapped', 'burning']) w.fxs[k] = 0;
      w.set('recover', 0.5);
      m.emit('crowdSave', { w, x: w.x, z: w.z });
    },

    // back to where you stood 3 seconds ago, on your feet and steady
    rewind(m, w) {
      const fx = w.x, fz = w.z;
      if (w.clinch) w.clinch.end('skill');
      if (w.gulpI >= 0) { const v = m.w[w.gulpI]; v.swallowed = false; v.x = w.x; v.z = w.z; w.gulpI = -1; }
      // play the last 3 seconds backwards, like a tape: they visibly backtrack along their path
      w.rwTrail = w.trail.concat([[w.x, w.z, w.f]]); w.vx = w.vz = 0; w.y = 0;
      w.down = false; w.out = false; w.lifted = false; w.trapped = false; w.torpedo = false;
      w.bal = 1; w.tx = w.tz = 0; w.ghostT = 0.4; w.boomT = 0;
      for (const k of ['sleep', 'frozen', 'grabbed', 'dizzy', 'drunk', 'blind', 'quake', 'ash', 'zapped', 'burning']) w.fxs[k] = 0;
      w.set('rewinding', 0.75); w.trail = [];
      m.emit('rewind', { w, x0: fx, z0: fz, x: w.x, z: w.z });
    },

    // kamikaze: the bomber always goes down; if they're still in the blast, so do they and nobody wins
    explode(m, w) {
      const o = w.opp, [nx, nz, d] = dirTo(w, o), R = 3.6;
      if (m.clinch) m.clinch.end('skill');
      const down = (p, sx, sz) => { p.vx = sx * 2.5; p.vz = sz * 2.5; p.set('fall', 0.3); p.fallX = sx; p.fallZ = sz; p.down = true; };
      const caught = d < R && !(o.fxs.invuln > 0) && o.st !== 'air';
      down(w, -nx, -nz);
      if (caught) { down(o, nx, nz); m.emit('boom', { w, x: w.x, z: w.z, k: 1 }); m.draw('sk_boomDraw'); }
      else { m.tag(w, o, 'sk_boom'); m.emit('boom', { w, x: w.x, z: w.z, k: 0.6 }); }
    },

    // CPU decides when to use what it holds
    aiWant(m, w) {
      if (w.gulpI >= 0) { const fx = Math.cos(w.f), fz = Math.sin(w.f); return w.st !== 'spit' && (w.gulpT > 3 || (w.gulpT > 0.6 && w.x * fx + w.z * fz > 1.2)); } // spit toward the edge
      const id = m.skills[w.idx]; if (!id) return false;
      const o = w.opp, d = Math.hypot(o.x - w.x, o.z - w.z);
      const myEdge = RR - Math.hypot(w.x, w.z);
      const k = (BY[id] || { kind: 'any' }).kind;
      if (m.sinceGo < 0.8) return false;
      if (id === 'favourite') return false; // fires by itself
      if (id === 'fake') return Math.random() < 0.01;
      if (id === 'copycat') return m.skills[o.idx] && m.skills[o.idx] !== 'fake' && Math.random() < 0.05;
      if (id === 'thief') return m.skills[o.idx] && d < 2.2 && Math.random() < 0.05;
      if (id === 'konbini') return false; // the CPU never goes shopping
      if (id === 'reset') return m.wins[o.idx] > m.wins[w.idx] && Math.random() < 0.05;
      if (id === 'noarms') return d < 3 && Math.random() < 0.04;
      if (id === 'molotov') return d > 1.5 && Math.random() < 0.04;
      if (id === 'doors') return Math.random() < 0.006;
      if (id === 'bumper') return myEdge < 1.2 && (w.clinch || o.contact) && Math.random() < 0.1;
      if (id === 'ball') return d > 1.5 && d < 4 && Math.random() < 0.03;
      if (id === 'cyclone') return d < 3 && Math.random() < 0.04;
      if (id === 'hole') return myEdge > 2 && RR - Math.hypot(o.x, o.z) > 1 && d > 1.5 && Math.random() < 0.02;
      if (id === 'possess') return RR - Math.hypot(o.x, o.z) < 2 && Math.random() < 0.05;
      if (id === 'shock') return d > 1.4 && d < 4 && RR - Math.hypot(o.x, o.z) < 2.5 && Math.random() < 0.05;
      if (id === 'gale') return d < 3.5 && RR - Math.hypot(o.x, o.z) < 2.6 && Math.random() < 0.06;
      if (id === 'rewind') return false; // it saves itself for the moment they would lose
      if (id === 'dart') return d > 1.4 && d < 6 && Math.abs(S.wrap(Math.atan2(o.z - w.z, o.x - w.x) - w.f)) < 0.2 && Math.random() < 0.1;
      if (id === 'inhale') return d < 3.2 && myEdge > 1.2 && Math.random() < 0.05;
      if (id === 'boom') return d < 1.6 && myEdge < 1.0 && (w.clinch || o.contact) && Math.random() < 0.06; // about to lose: take them with you
      if (k === 'def') return myEdge < 1.0 && (w.clinch || o.contact);
      if (k === 'trap') return d > 1.8 && myEdge > 1.5 && Math.random() < 0.02;
      if (k === 'atk') return d < 2.4 && Math.random() < 0.05;
      return Math.random() < 0.012;
    },
  };
  S.Skills = Skills;
})();
