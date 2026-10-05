'use strict';
// CAMPAIGN SKILLS + MASKS. The drink machines sell skills (Space to use, recharges); before a run you pick a mask
// that bends one rule. Most skills are the versus gacha skills rebuilt for a street brawl against a crowd; the art
// comes from the versus renderer (makeObj), drawn into the campaign scene.
//
//   const K = new S.CampSkills(camp)
//   K.use(skill) -> true if handled        K.player(P, dt, mx, mz) -> true while a skill drives you
//   K.drive(E, dt) -> true while a skill drives an enemy (asleep, trapped, swallowed, panicking, a clone)
//   K.step(dt)  K.draw(dt, T)  K.tscale(a)  K.dmgMul(T, A, dmg)  K.afterHit(T, A)  K.saveFromDeath()  K.fxs()
(function () {
  const rnd = (a, b) => a + Math.random() * (b - a), TAU = Math.PI * 2;
  const ang = (a) => { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; };
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

  const POOL = [
    { id: 'molotov', name: 'MOLOTOV COCKTAIL', desc: 'Throw a fire bottle ahead: a burning patch that hurts anyone in it.', cd: 18 },
    { id: 'hundred', name: 'THOUSAND HANDS', desc: 'A blur of slaps in front of you: big damage, pushes everyone back.', cd: 16 },
    { id: 'giant', name: 'GIANT', desc: 'Grow huge for 8s: more damage, no knockdowns, grabs cannot hold you.', cd: 26 },
    { id: 'gale', name: 'GIANT FAN', desc: 'A gale in front of you blows enemies off their feet.', cd: 16 },
    { id: 'shock', name: 'SHOCKWAVE STOMP', desc: 'Stomp: everyone around you is knocked down.', cd: 18 },
    { id: 'absorb', name: 'IRON BODY', desc: '6s: hits do nothing to you.', cd: 24 },
    { id: 'claw', name: 'CLAW MACHINE', desc: 'A claw drops on the toughest nearby enemy, lifts them and drops them.', cd: 22 },
    { id: 'freeze', name: 'FREEZE', desc: 'Freezes the nearest enemies solid for 3s.', cd: 20 },
    { id: 'storm', name: 'LIGHTNING', desc: 'Lightning strikes the three nearest enemies.', cd: 20 },
    { id: 'cyclone', name: 'CYCLONE', desc: 'Spin like a top for 5s. Steer it: everyone you touch is flung away. Nobody can grab you.', cd: 22 },
    { id: 'ball', name: 'DARUMA ROLL', desc: 'Become a daruma for 6s. Roll into them to bowl them over; L to smash forward.', cd: 22 },
    { id: 'triplets', name: 'TRIPLETS', desc: 'Two clones of you appear and fight for 8s. A clone vanishes when it is hit.', cd: 26 },
    { id: 'dizzySlap', name: 'DIZZY SLAPS', desc: 'Your next 4 slaps leave them seeing stars: dazed and open.', cd: 14 },
    { id: 'turnSlap', name: 'SPIN SLAPS', desc: 'Your next 4 slaps spin them round, hard: they stagger with their back to you.', cd: 14 },
    { id: 'smoke', name: 'SMOKE BOMB', desc: 'A thick cloud for 6s. Inside it, they cannot find you.', cd: 20 },
    { id: 'slow', name: 'TIME DRAG', desc: 'Everyone else moves in slow motion for 6 seconds.', cd: 22 },
    { id: 'dashThru', name: 'PHANTOM DASH', desc: 'Dash straight through everyone in front of you. All of them go down.', cd: 12 },
    { id: 'invuln', name: 'INVINCIBLE', desc: '5s: nothing hurts or moves you, and anyone who touches you bounces off.', cd: 24 },
    { id: 'shrink', name: 'SHRINK', desc: 'Everyone near you shrinks for 7s: weak hits, and they fly when you hit them.', cd: 22 },
    { id: 'quake', name: 'EARTHQUAKE', desc: 'The market heaves for 3s: everyone is thrown off their feet and everything near you breaks.', cd: 26 },
    { id: 'invis', name: 'VANISH', desc: 'Invisible for 6s: they lose you. Your first hit out of nowhere does double.', cd: 20 },
    { id: 'banana', name: 'BANANA PEEL', desc: 'Drop a peel. The next one to step on it goes flat on their back.', cd: 10 },
    { id: 'trap', name: 'TRAPDOOR', desc: 'A hidden trapdoor where you stand. Walk off it, lure them on, and they drop through.', cd: 20 },
    { id: 'torpedo', name: 'TORPEDO', desc: 'Launch yourself head-first: through everyone, through the stalls.', cd: 14 },
    { id: 'dart', name: 'SLEEP DART', desc: 'Fire a dart straight ahead. Whoever it hits falls asleep on their feet for 5s.', cd: 12 },
    { id: 'inhale', name: 'CONSUME', desc: 'Swallow the one in front of you whole. Press Space again to spit them out like a cannonball.', cd: 18 },
    { id: 'beartrap', name: 'BEAR TRAP', desc: 'Drop a bear trap. Whoever steps in it is stuck fast for 4s.', cd: 14 },
    { id: 'rewind', name: 'REWIND', desc: 'Jump back to where you were 3s ago. If you would be knocked out holding it, it fires by itself with half your health back.', cd: 30 },
    { id: 'bomb', name: 'BOMB', desc: 'Drop a bomb that blows in 3s. Slap or charge it to send it at them.', cd: 18 },
    { id: 'potato', name: 'HOT POTATO', desc: 'Stick a bomb on the nearest one. They panic and run to their friends. Touch them and it\'s yours!', cd: 18 },
    { id: 'train', name: 'TRAIN CROSSING', desc: 'Bells ring, then a train blasts across the street ahead. Stay out of the lane.', cd: 26 },
    { id: 'konbini', name: 'CONVENIENCE STORE', desc: 'A tiny konbini pops up. Walk in and pick one of three skills off the shelf.', cd: 30 },
    { id: 'takeaway', name: 'TAKEAWAY BAG', desc: 'A mystery food bag lands ahead. Eat it: giant strength... or food poisoning.', cd: 20 },
    { id: 'bellyFlop', name: 'BELLY FLOP', desc: 'Leap off the screen, steer your shadow, and crash down on them.', cd: 20 },
  ];
  const BY = {}; for (const s of POOL) BY[s.id] = s;

  // masks: one per run, picked before the market opens. Each bends one rule, for better and worse.
  const MASKS = [
    { id: 'none', name: 'SHIROKAO', jp: '素顔', desc: 'Your bare face. Standard rules: the pure leaderboard.' },
    { id: 'oni', name: 'ONI', jp: '鬼', desc: 'Slams and belly tosses heal you. You take 25% more damage.' },
    { id: 'tengu', name: 'TENGU', jp: '天狗', desc: 'Charges come out instantly and smash anything. Your parry window is tiny.' },
    { id: 'kitsune', name: 'KITSUNE', jp: '狐', desc: 'Dodges go twice as far and are untouchable. Your slaps are weaker.' },
    { id: 'hannya', name: 'HANNYA', jp: '般若', desc: 'One hit kills you. One hit kills them. Double score.' },
    { id: 'okame', name: 'OKAME', jp: 'おかめ', desc: 'Knocked-out enemies often drop onigiri. The skill machines are empty.' },
    { id: 'fish', name: 'FISHMONGER', jp: '魚屋', desc: 'Start holding a tuna; smashed stalls drop extra weapons. You move 15% slower.' },
  ];

  class CampSkills {
    constructor(c) {
      this.c = c; this.objs = []; this.hist = []; this.histT = 0; this.slowT = 0; this.quake = null; this.gulp = null;
      this.mask = MASKS[0];
    }
    // ------------------------------------------------------------------ helpers
    // versus art, drawn into the campaign scene
    art(type, extra) {
      const R = this.c.R, sc0 = R.scene, v0 = R.viewer; R.scene = this.c.scene; R.viewer = -1;
      const me = R.makeObj(Object.assign({ type, owner: { idx: 0 }, c: [], t: 0 }, extra || {}));
      R.scene = sc0; R.viewer = v0; return me;
    }
    add(o) { this.objs.push(o); return o; }
    kill(o) { o.dead = true; if (o.me && o.me.parent) o.me.parent.remove(o.me); if (o.ring && o.ring.parent) o.ring.parent.remove(o.ring); }
    foes(r, x, z) { const c = this.c; x = x === undefined ? c.P.x : x; z = z === undefined ? c.P.z : z; return c.actors.filter((e) => e.team === 1 && !e.dead && !e.sleep && e.st !== 'swallowed' && Math.hypot(e.x - x, e.z - z) < r); }
    blast(x, z, r, dmg, by, opt) { // a bomb going off: everything in range, players included if close
      const c = this.c; opt = opt || {};
      for (const e of c.actors) {
        if (e.dead || e.clone || e.st === 'swallowed') continue; const d = Math.hypot(e.x - x, e.z - z); if (d > r) continue;
        const a = Math.atan2(e.z - z, e.x - x), k = 1 - d / r * 0.5;
        if (e === c.P) { if (!opt.spareMe) c.damage(e, dmg * 0.4 * k, null, Math.cos(a) * 7, Math.sin(a) * 7, true); }
        else { e.sleep = false; c.damage(e, dmg * k, by, Math.cos(a) * 9, Math.sin(a) * 9, true); }
      }
      for (const b of c.map.breakables) if (!b.broken && Math.hypot(b.x - x, b.z - z) < r) { c.brk.smash(b, by || c.P, b.x - x, b.z - z); if (b.kind === 'vend' && !b.broken) c.brk.smash(b, by || c.P, b.x - x, b.z - z); }
      for (const p of c.props) if (!p.dead && Math.hypot(p.x - x, p.z - z) < r) c.smash(p, (p.x - x) * 3, (p.z - z) * 3, by || c.P, true);
      c.brk.crater(x, z); c.fx.burst(x, z, 1.6); c.fx.dust(x, 0.2, z, 22, 1.2, 1.0, 0.7); c.fx.spark(x, 0.8, z, 2.2);
      c.shake = Math.max(c.shake, 0.8); c.hitstop = Math.max(c.hitstop, 0.08); c.g.audio.thump(13); c.g.audio.roar && 0;
    }
    groundRing(col, r) { const m = new THREE.Mesh(new THREE.RingGeometry(r * 0.8, r, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.7, depthWrite: false })); m.renderOrder = 2; this.c.scene.add(m); return m; }

    // ------------------------------------------------------------------ using a skill
    use(A) {
      const c = this.c, P = c.P, fx = Math.cos(P.f), fz = Math.sin(P.f), au = c.g.audio;
      switch (A.id) {
        case 'cyclone': P.sk = { kind: 'cyc', t: 0, dur: 5, hit: new Map() }; au.whoosh(0.9); c.fx.dust(P.x, 0.05, P.z, 14, 0.5, 0.8, 0.5); return true;
        case 'ball': P.sk = { kind: 'ball', t: 0, dur: 6, cd: 0, roll: 0 }; c.release && P.held && c.release(P); au.clack(); c.fx.burst(P.x, P.z, 0.8); return true;
        case 'triplets': {
          for (const sd of [-1, 1]) {
            const x = P.x + Math.cos(P.f + sd * 1.6) * 1.4, z = P.z + Math.sin(P.f + sd * 1.6) * 1.4;
            const k = c.addActor('player', x, z, { arch: c.arch, lo: S.profile.loadout() }); k.clone = true; k.cloneT = 8; k.f = P.f; k.hp = k.maxHp = 1; k.cd = rnd(0, 0.4);
            c.fx.burst(x, z, 0.9); c.fx.dust(x, 0.3, z, 10, 0.6, 0.7, 0.5);
          }
          au.clack(); return true;
        }
        case 'dizzySlap': P.slapFx = { kind: 'dizzy', n: 4, t: 8 }; return true;
        case 'turnSlap': P.slapFx = { kind: 'spin', n: 4, t: 8 }; return true;
        case 'smoke': {
          const me = this.art('smoke'); me.position.set(P.x, 0, P.z); me.scale.setScalar(1.15);
          this.add({ type: 'smoke', me, x: P.x, z: P.z, r: 3.9, t: 0, dur: 6 }); au.whoosh(0.6); c.fx.dust(P.x, 0.4, P.z, 20, 1.2, 1.2, 0.8); return true;
        }
        case 'slow': this.slowT = 6; au.swell(0.5, 1.6); c.flash = 0.6; return true;
        case 'dashThru': P.sk = { kind: 'pdash', t: 0, dur: 0.22, f: P.f, hit: new Set() }; P.iframe = Math.max(P.iframe, 0.35); au.whoosh(0.7); return true;
        case 'invuln': P.invuln = 5; au.swell(0.6, 1.0); return true;
        case 'shrink': for (const e of this.foes(12)) { e.shrinkT = 7; c.fx.spark(e.x, 1.2, e.z, 0.8); } au.blip(true); return true;
        case 'quake': this.quake = { t: 0, n: 0 }; au.thump(14); c.shake = 1; return true;
        case 'invis': P.invis = 6; au.whoosh(0.4); c.fx.dust(P.x, 0.5, P.z, 12, 0.6, 0.7, 0.5); return true;
        case 'banana': { const me = this.art('banana'); const x = P.x - fx * 0.6, z = P.z - fz * 0.6; me.position.set(x, 0.05, z); this.add({ type: 'banana', me, x, z, t: 0 }); au.blip(false); return true; }
        case 'trap': { const me = this.art('trap'); me.position.set(P.x, 0.02, P.z); me.scale.setScalar(1.6); this.add({ type: 'trap', me, x: P.x, z: P.z, t: 0, dur: 14, armed: false, ate: 0 }); au.clack(); return true; }
        case 'torpedo': P.sk = { kind: 'torp', t: 0, dur: 0.9, f: P.f, hit: new Set() }; P.iframe = Math.max(P.iframe, 0.9); au.whoosh(0.9); return true;
        case 'dart': { const me = this.art('dart'); me.position.set(P.x + fx * 0.8, 1.1, P.z + fz * 0.8); me.rotation.y = -P.f; this.add({ type: 'dart', me, x: P.x + fx * 0.8, z: P.z + fz * 0.8, vx: fx * 17, vz: fz * 17, t: 0 }); au.whoosh(0.2); return true; }
        case 'inhale': {
          const T = this.foes(3).filter((e) => e.kind !== 'boss' && e.kind !== 'sumo' && Math.abs(ang(Math.atan2(e.z - P.z, e.x - P.x) - P.f)) < 1.0).sort((a, b) => Math.hypot(a.x - P.x, a.z - P.z) - Math.hypot(b.x - P.x, b.z - P.z))[0];
          if (!T) { c.popAt(P, 'NOTHING TO EAT'); c.abCd = 1; return true; }
          c.dropCarry(T); if (T.holdP) c.escapeFrom(T); T.st = 'swallowed'; T.t = 0; this.gulp = { e: T, t: 0 }; c.abCd = 0.4; // Space again spits
          au.whoosh(0.5); c.popAt(P, 'GULP!'); return true;
        }
        case 'beartrap': { const me = this.art('beartrap'); const x = P.x - fx * 0.7, z = P.z - fz * 0.7; me.position.set(x, 0, z); me.scale.setScalar(1.3); this.add({ type: 'beartrap', me, x, z, t: 0, shut: false }); au.clack(); return true; }
        case 'rewind': this.rewind(false); return true;
        case 'bomb': { const me = this.art('bomb'); const x = P.x + fx * 1.2, z = P.z + fz * 1.2; me.position.set(x, 0, z); this.add({ type: 'bomb', me, x, z, vx: 0, vz: 0, t: 0, dur: 3, kickT: 0 }); au.clack(); return true; }
        case 'potato': {
          const T = this.foes(9).sort((a, b) => Math.hypot(a.x - P.x, a.z - P.z) - Math.hypot(b.x - P.x, b.z - P.z))[0];
          if (!T) { c.popAt(P, 'NO ONE NEAR'); c.abCd = 1; return true; }
          const me = this.art('potato'); this.add({ type: 'potato', me, holder: T, t: 0, dur: 5, passT: 0 }); c.popAt(T, 'HOT POTATO!'); au.clack(); return true;
        }
        case 'train': {
          const me = this.art('train'); const lz = P.z - 3.6; me.position.set(0, 0, lz); me.userData.loco.visible = false;
          this.add({ type: 'train', me, z: lz, t: 0, warn: 1.5, front: -26, hit: new Set() }); au.tick(); return true;
        }
        case 'konbini': {
          const me = this.art('konbini'); const x = P.x + fx * 2.4, z = P.z + fz * 2.4; me.position.set(x, 0, z); me.rotation.y = -P.f + Math.PI / 2;
          this.add({ type: 'konbini', me, x, z, t: 0, dur: 14 }); c.fx.dust(x, 0.2, z, 14, 0.8, 0.8, 0.5); au.blip(true); return true;
        }
        case 'takeaway': { const me = this.art('bag'); const x = P.x + fx * 2.2, z = P.z + fz * 2.2; this.add({ type: 'bag', me, x, z, t: 0, dur: 15 }); au.whoosh(0.3); return true; }
        case 'bellyFlop': P.sk = { kind: 'flop', t: 0, dur: 1.6, tx: P.x, tz: P.z }; P.iframe = Math.max(P.iframe, 1.7); au.whoosh(0.8); return true;
      }
      return false;
    }
    // REWIND: back to where you were 3s ago (saving: half your health back)
    rewind(saving) {
      const c = this.c, P = c.P, h = this.hist[0] || { x: P.x, z: P.z };
      c.fx.dust(P.x, 0.5, P.z, 14, 0.8, 0.8, 0.5); c.fx.burst(P.x, P.z, 0.8);
      P.x = h.x; P.z = h.z; P.vx = P.vz = 0; P.y = 0; P.sk = null; P.held && c.release(P); P.holder = null;
      if (saving) { P.hp = Math.max(P.hp, P.maxHp * 0.5); P.dead = false; c.set(P, 'free'); P.iframe = 1.5; c.say('REWIND!', 'Half your health back', 1.6); }
      else { c.set(P, 'free'); P.iframe = 0.6; c.popAt(P, 'REWIND'); }
      c.fx.burst(P.x, P.z, 1.0); c.g.audio.swell(0.6, 0.8); this.hist = [];
    }
    saveFromDeath() {
      const c = this.c;
      if (c.ability && c.ability.id === 'rewind' && c.abCd <= 0) { c.abCd = c.ability.cd; this.rewind(true); return true; }
      return false;
    }

    // ------------------------------------------------------------------ while a skill drives you
    player(P, dt, mx, mz) {
      const c = this.c, K = P.sk; if (!K) return false;
      K.t += dt; const au = c.g.audio;
      if (K.kind === 'cyc') {
        P.st = 'free'; P.tvx = mx * 5.2; P.tvz = mz * 5.2; P.f += dt * 26 * Math.min(1, (K.dur - K.t) / 0.4 + 0.3);
        for (const e of c.actors) {
          if (e.team !== 1 || e.dead || e.st === 'swallowed' || Math.hypot(e.x - P.x, e.z - P.z) > P.r + e.r + 0.35) continue;
          if ((K.hit.get(e) || -9) > K.t - 0.6) continue; K.hit.set(e, K.t);
          const a = Math.atan2(e.z - P.z, e.x - P.x), tx = -Math.sin(a), tz = Math.cos(a);
          c.damage(e, 14, P, (Math.cos(a) * 0.8 + tx * 0.6) * 11, (Math.sin(a) * 0.8 + tz * 0.6) * 11, true); au.thump(7); c.popAt(e, 'WHIRLED!');
        }
        for (const p of c.props) if (!p.dead && !p.held && Math.hypot(p.x - P.x, p.z - P.z) < P.r + p.r + 0.3) c.smash(p, (p.x - P.x) * 6, (p.z - P.z) * 6, P);
        if (K.t >= K.dur) P.sk = null;
        return true;
      }
      if (K.kind === 'ball') {
        K.cd -= dt; P.st = 'free';
        P.vx += mx * 16 * dt; P.vz += mz * 16 * dt; const k = Math.exp(-dt * 0.8); P.vx *= k; P.vz *= k;
        if (c.ctrl.dash.pressed && K.cd <= 0) { const l = Math.hypot(mx, mz), dx = l > 0.2 ? mx / l : Math.cos(P.f), dz = l > 0.2 ? mz / l : Math.sin(P.f); P.vx += dx * 7; P.vz += dz * 7; K.cd = 0.7; au.whoosh(0.5); }
        let sp = Math.hypot(P.vx, P.vz); const cap = K.cd > 0.35 ? 11 : 7.5; if (sp > cap) { P.vx *= cap / sp; P.vz *= cap / sp; sp = cap; }
        P.tvx = P.vx; P.tvz = P.vz; if (sp > 0.3) P.f = Math.atan2(P.vz, P.vx); K.roll += sp * dt / 0.7;
        if (sp > 3) for (const e of c.actors) {
          if (e.team !== 1 || e.dead || e.st === 'swallowed' || e.st === 'down' || Math.hypot(e.x - P.x, e.z - P.z) > P.r + e.r + 0.15) continue;
          c.damage(e, 8 + sp * 1.6, P, P.vx * 1.1, P.vz * 1.1, true); P.vx *= 0.55; P.vz *= 0.55; au.thump(9); c.fx.burst(e.x, e.z, 0.8); c.popAt(e, 'STRIKE!');
        }
        if (K.t >= K.dur) { P.sk = null; c.fx.burst(P.x, P.z, 0.8); }
        return true;
      }
      if (K.kind === 'pdash' || K.kind === 'torp') {
        const s = K.kind === 'torp' ? 15 : 30; P.st = K.kind === 'torp' ? 'charge' : 'dodge'; P.f = K.f;
        P.vx = P.tvx = Math.cos(K.f) * s; P.vz = P.tvz = Math.sin(K.f) * s;
        for (const e of c.actors) {
          if (e.team !== 1 || e.dead || K.hit.has(e) || e.st === 'swallowed' || Math.hypot(e.x - P.x, e.z - P.z) > P.r + e.r + 0.4) continue;
          K.hit.add(e); c.damage(e, K.kind === 'torp' ? 24 : 18, P, -Math.sin(K.f) * (Math.random() < 0.5 ? 6 : -6) + Math.cos(K.f) * 3, Math.cos(K.f) * 3, true); au.thump(8); c.fx.spark(e.x, 1, e.z, 1);
        }
        for (const p of c.props) if (!p.dead && !p.held && Math.hypot(p.x - P.x, p.z - P.z) < P.r + p.r + 0.2) c.smash(p, P.vx * 0.5, P.vz * 0.5, P, true);
        if (K.kind === 'torp' && Math.random() < 0.6) c.fx.dust(P.x, 0.3, P.z, 1, 0.3, 0.4, 0.3);
        if (K.t >= K.dur || (K.kind === 'torp' && P.bumped)) { P.bumped = false; P.sk = null; P.vx *= 0.25; P.vz *= 0.25; c.set(P, 'recover', 0.3); if (K.kind === 'torp') { c.shake = Math.max(c.shake, 0.4); c.brk.crack(P.x, P.z, 1.4); } }
        return true;
      }
      if (K.kind === 'flop') {
        // up off the screen (0-0.45s), steer the shadow, then down like a meteor (last 0.25s)
        const up = 0.45, fall = 0.25;
        if (!K.ring) { K.ring = this.groundRing(0xff3b3b, 1.6); }
        P.st = 'free'; P.tvx = 0; P.tvz = 0; P.vx = P.vz = 0;
        if (K.t < up) { P.y = 14 * (K.t / up) ** 2; K.tx = P.x; K.tz = P.z; }
        else if (K.t < K.dur - fall) { K.tx += mx * 7 * dt; K.tz += mz * 7 * dt; P.x = K.tx; P.z = K.tz; P.y = 14; }
        else { const k = (K.t - (K.dur - fall)) / fall; P.x = K.tx; P.z = K.tz; P.y = 14 * (1 - k * k); }
        K.ring.position.set(K.tx, 0.04, K.tz); const pul = 1 + 0.1 * Math.sin(K.t * 20); K.ring.scale.set(pul, 1, pul);
        if (K.t >= K.dur) {
          P.y = 0; c.scene.remove(K.ring); P.sk = null;
          this.blast(P.x, P.z, 3.2, 38, P, { spareMe: true }); c.set(P, 'recover', 0.35); c.popAt(P, 'BELLY FLOP!');
        }
        return true;
      }
      return false;
    }

    // ------------------------------------------------------------------ skills driving enemies (true: skip the usual AI)
    drive(E, dt) {
      const c = this.c;
      if (E.clone) return this.cloneStep(E, dt);
      if (E.st === 'swallowed') { E.x = c.P.x; E.z = c.P.z; E.vx = E.vz = E.tvx = E.tvz = 0; return true; }
      if (E.sleepT > 0) { E.sleepT -= dt; E.tvx = E.tvz = 0; E.vx *= 0.8; E.vz *= 0.8; if (!['down', 'getup', 'held', 'thrown'].includes(E.st)) { E.st = 'dazed'; E.t = 0; E.dur = 1; } if (Math.random() < dt * 1.5) c.popAt(E, 'Zzz'); if (E.sleepT <= 0) c.set(E, 'free'); return true; }
      if (E.trapT > 0) { E.trapT -= dt; E.vx = E.vz = E.tvx = E.tvz = 0; if (E.trapT <= 0) c.set(E, 'free'); return true; }
      if (E.shrinkT > 0) E.shrinkT -= dt;
      // hot potato: run to the nearest friend to pass it on
      const pot = this.objs.find((o) => o.type === 'potato' && !o.dead && o.holder === E);
      if (pot && ['free', 'approach', 'recover'].includes(E.st)) {
        const fr = c.actors.filter((o) => o !== E && o.team === 1 && !o.dead && o.st !== 'swallowed').sort((a, b) => Math.hypot(a.x - E.x, a.z - E.z) - Math.hypot(b.x - E.x, b.z - E.z))[0];
        const tx = fr ? fr.x : E.x + (E.x - c.P.x), tz = fr ? fr.z : E.z + (E.z - c.P.z), l = Math.hypot(tx - E.x, tz - E.z) || 1;
        E.tvx = (tx - E.x) / l * E.spd * 1.5; E.tvz = (tz - E.z) / l * E.spd * 1.5; E.f = Math.atan2(E.tvz, E.tvx); E.st = 'free'; return true;
      }
      // smoke or vanish: they've lost you
      if ((c.P.invis > 0 || this.inSmoke(c.P) || this.inSmoke(E)) && Math.hypot(E.x - c.P.x, E.z - c.P.z) > 1.3) E.blind = Math.max(E.blind || 0, 0.15);
      return false;
    }
    inSmoke(a) { return this.objs.some((o) => o.type === 'smoke' && !o.dead && Math.hypot(a.x - o.x, a.z - o.z) < o.r); }
    cloneStep(K, dt) { // a clone: walk at the nearest enemy and slap
      const c = this.c; K.cloneT -= dt; K.t += dt; if (K.cd > 0) K.cd -= dt;
      if (K.cloneT <= 0) { this.poof(K); return true; }
      const T = c.actors.filter((e) => e.team === 1 && !e.dead && !e.sleep && e.st !== 'swallowed').sort((a, b) => Math.hypot(a.x - K.x, a.z - K.z) - Math.hypot(b.x - K.x, b.z - K.z))[0];
      K.tvx = K.tvz = 0;
      if (K.st === 'strike') { if (K.t >= K.dur) c.set(K, 'free'); return true; }
      if (!T) { const dx = c.P.x - K.x, dz = c.P.z - K.z, d = Math.hypot(dx, dz); if (d > 2) { K.tvx = dx / d * 4; K.tvz = dz / d * 4; } return true; }
      const dx = T.x - K.x, dz = T.z - K.z, d = Math.hypot(dx, dz); K.f = Math.atan2(dz, dx);
      if (d > K.r + T.r + 0.5) { K.tvx = dx / d * 4.4; K.tvz = dz / d * 4.4; }
      else if (K.cd <= 0) { c.set(K, 'strike', 0.26); K.hand = (K.hand || 0) ^ 1; c.meleeHit(K, 1.3, 0.9, 10, 3, false); K.cd = 0.45; }
      return true;
    }
    poof(K) { const c = this.c; c.fx.burst(K.x, K.z, 0.9); c.fx.dust(K.x, 0.4, K.z, 12, 0.7, 0.7, 0.5); c.g.audio.blip(false); K.dead = true; K.gone = true; K.view.dispose && K.view.dispose(c.scene); }

    // ------------------------------------------------------------------ damage hooks
    dmgMul(T, A, dmg) {
      const c = this.c, P = c.P, m = this.mask.id;
      if (T.clone) { this.poof(T); return 0; }
      if (T === P && P.invuln > 0) { if (A && A !== P) { const a = Math.atan2(A.z - P.z, A.x - P.x); A.vx += Math.cos(a) * 6; A.vz += Math.sin(a) * 6; } return 0; }
      if (T === P && P.sk && (P.sk.kind === 'flop' || P.sk.kind === 'torp' || P.sk.kind === 'pdash')) return 0;
      let k = 1;
      if (A && A.shrinkT > 0) k *= 0.35;
      if (T.shrinkT > 0) k *= 1.5;
      if (T.trapT > 0 || T.sleepT > 0) k *= 1.3;
      if (A === P && P.invis > 0) { k *= 2; P.invis = 0; c.popAt(T, 'FROM NOWHERE!'); }
      if (T === P && m === 'oni') k *= 1.25;
      if (A === P && m === 'kitsune' && P.st === 'strike') k *= 0.7;
      if (m === 'hannya') { if (T === P && dmg > 0) return 999; if (A === P && T.team === 1) k *= T.kind === 'boss' || T.kind === 'sumo' ? 3 : 99; }
      return k;
    }
    afterHit(T, A) {
      const c = this.c, P = c.P;
      if (A === P && P.slapFx && P.st === 'strike' && T.team === 1 && !T.dead) {
        const F = P.slapFx;
        if (F.kind === 'dizzy') { c.set(T, 'dazed', T.kind === 'boss' ? 1.2 : 2.5); T.stun = T.kind === 'boss' ? 1.2 : 2.5; c.popAt(T, 'DIZZY!'); }
        else { T.f += Math.PI; if (T.kind !== 'boss') { c.set(T, 'hurt', 1.0); T.vx += Math.cos(P.f) * 4; T.vz += Math.sin(P.f) * 4; } c.popAt(T, 'SPUN!'); }
        if (--F.n <= 0) P.slapFx = null;
      }
      if (T.shrinkT > 0 && A === P && T.st !== 'down' && T.kind !== 'boss' && !T.dead) { c.set(T, 'down', 1.0); T.fallX = Math.cos(P.f); T.fallZ = Math.sin(P.f); T.vx += Math.cos(P.f) * 6; T.vz += Math.sin(P.f) * 6; }
    }
    tscale(a) { return a !== this.c.P && !a.clone && this.slowT > 0 ? 0.3 : 1; }
    fxs() {
      const P = this.c.P, K = P.sk;
      return { invis: P.invis > 0 ? 1 : 0, ball: K && K.kind === 'ball' ? 1 : 0, cyclone: K && K.kind === 'cyc' ? Math.max(0.01, K.dur - K.t) : 0, invuln: P.invuln > 0 || P.iron > 0 ? 1 : 0, giant: P.giant > 0 ? 1 : 0 };
    }

    // ------------------------------------------------------------------ the world: traps, bombs, trains, shops...
    step(dt) {
      const c = this.c, P = c.P, au = c.g.audio;
      if (this.slowT > 0) this.slowT -= dt;
      if (P.invuln > 0) P.invuln -= dt; if (P.invis > 0) P.invis -= dt;
      if (P.slapFx && (P.slapFx.t -= dt) <= 0) P.slapFx = null;
      if (P.poison > 0) P.poison -= dt;
      // rewind memory: where you were, every tenth of a second, 3s back
      this.histT += dt; if (this.histT >= 0.1) { this.histT = 0; if (!P.dead && P.st !== 'grabbed') this.hist.push({ x: P.x, z: P.z }); if (this.hist.length > 30) this.hist.shift(); }
      // CONSUME: they ride in your belly until you spit (Space) or 5s pass
      if (this.gulp) {
        const G = this.gulp; G.t += dt;
        if (G.e.dead || G.e.gone) this.gulp = null;
        else if (G.t > 5 || (G.t > 0.3 && c.ctrl.skill.pressed)) this.spit();
      }
      // EARTHQUAKE: three heaves; everything near you breaks
      if (this.quake) {
        const Q = this.quake; Q.t += dt; c.shake = Math.max(c.shake, 0.5);
        if (Math.random() < dt * 10) c.brk.crack(P.x + rnd(-9, 9), P.z + rnd(-9, 9), rnd(1.2, 2.6));
        if (Q.t >= Q.n * 1.0) {
          Q.n++; au.thump(12);
          for (const e of this.foes(13)) { e.sleep = false; c.damage(e, 10, P, rnd(-4, 4), rnd(-4, 4), true); }
          if (Q.n === 1) for (const b of c.map.breakables) if (!b.broken && Math.hypot(b.x - P.x, b.z - P.z) < 10) { c.brk.smash(b, P, b.x - P.x, b.z - P.z); if (b.kind === 'vend') c.brk.smash(b, P, b.x - P.x, b.z - P.z); }
          if (Q.n === 1) for (const p of c.props) if (!p.dead && Math.hypot(p.x - P.x, p.z - P.z) < 10) c.smash(p, rnd(-3, 3), rnd(-3, 3), P, true);
        }
        if (Q.t > 3) this.quake = null;
      }
      for (const o of this.objs) {
        if (o.dead) continue; o.t += dt;
        switch (o.type) {
          case 'smoke': if (o.t > o.dur) this.kill(o); break;
          case 'banana': for (const e of c.actors) if (e.team === 1 && !e.dead && !e.sleep && e.kind !== 'boss' && Math.hypot(e.x - o.x, e.z - o.z) < e.r + 0.3 && !['down', 'getup', 'held', 'thrown', 'swallowed'].includes(e.st)) {
            const s = Math.hypot(e.vx, e.vz) || 1; c.set(e, 'down', 1.5); e.slipFall = true; e.fallX = -(e.vx || Math.cos(e.f)) / s; e.fallZ = -(e.vz || Math.sin(e.f)) / s; e.vx *= 1.6; e.vz *= 1.6;
            c.damage(e, 12, P, 0, 0, false); c.popAt(e, 'SLIP!'); au.slap(4); this.kill(o); break;
          } break;
          case 'trap': {
            if (!o.armed && Math.hypot(P.x - o.x, P.z - o.z) > 1.2) o.armed = true;
            for (const e of c.actors) if (o.armed && e.team === 1 && !e.dead && !e.sleep && Math.hypot(e.x - o.x, e.z - o.z) < 0.85 && !['held', 'thrown', 'swallowed'].includes(e.st)) {
              o.me.userData.hole.visible = true; o.holeT = 0.6; au.thump(6);
              if (e.kind === 'boss' || e.kind === 'sumo') { c.damage(e, 35, P, 0, 0, false); e.trapT = 1.5; c.popAt(e, 'STUCK IN THE HOLE!'); }
              else { c.popAt(e, 'OTOSHIANA!'); c.addScore(1000); e.dead = true; e.hp = 0; e.gone = true; c.dropCarry(e); e.view.dispose ? e.view.dispose(c.scene) : 0; }
              if (++o.ate >= 2) o.t = o.dur; break;
            }
            if (o.holeT > 0 && (o.holeT -= dt) <= 0) o.me.userData.hole.visible = false;
            if (o.t > o.dur) this.kill(o);
            break;
          }
          case 'dart': {
            o.x += o.vx * dt; o.z += o.vz * dt; o.me.position.set(o.x, 1.1, o.z);
            const hit = c.actors.find((e) => e.team === 1 && !e.dead && e.st !== 'swallowed' && Math.hypot(e.x - o.x, e.z - o.z) < e.r + 0.15);
            if (hit) { hit.sleep = false; hit.sleepT = hit.kind === 'boss' ? 2 : 5; c.popAt(hit, 'SLEEP!'); au.blip(true); this.kill(o); }
            else if (o.t > 0.9 || c.map.walls.some((w) => o.x > w.x0 && o.x < w.x1 && o.z > w.z0 && o.z < w.z1)) this.kill(o);
            break;
          }
          case 'beartrap': {
            if (!o.shut) for (const e of c.actors) if (e.team === 1 && !e.dead && !e.sleep && Math.hypot(e.x - o.x, e.z - o.z) < e.r + 0.3 && !['held', 'thrown', 'swallowed'].includes(e.st)) {
              o.shut = true; o.victim = e; e.trapT = e.kind === 'boss' ? 1.8 : 4; e.x = o.x; e.z = o.z; c.damage(e, 8, P, 0, 0, false); c.popAt(e, 'SNAP!'); au.clack(); break;
            }
            if (o.shut) { for (const j of o.me.userData.jaws) j.rotation.x += (j.userData.sd * -1.35 - j.rotation.x) * Math.min(1, dt * 22); if (!(o.victim && o.victim.trapT > 0)) o.done = (o.done || 0) + dt; if (o.done > 0.8) this.kill(o); }
            if (o.t > 20) this.kill(o);
            break;
          }
          case 'bomb': {
            // slap it or charge it and it skids away from you
            if (o.kickT > 0) o.kickT -= dt;
            const d = Math.hypot(P.x - o.x, P.z - o.z);
            if (o.kickT <= 0 && d < P.r + 0.6 && ['strike', 'charge', 'dodge'].includes(P.st)) { const a = Math.atan2(o.z - P.z, o.x - P.x), s = P.st === 'charge' ? 13 : 9; o.vx = Math.cos(a) * s; o.vz = Math.sin(a) * s; o.kickT = 0.3; au.slap(4); }
            o.x += o.vx * dt; o.z += o.vz * dt; const k = Math.exp(-dt * 1.4); o.vx *= k; o.vz *= k;
            for (const w of c.map.walls) if (o.x > w.x0 - 0.3 && o.x < w.x1 + 0.3 && o.z > w.z0 - 0.3 && o.z < w.z1 + 0.3) { o.vx *= -0.5; o.vz *= -0.5; o.x += o.vx * dt * 2; o.z += o.vz * dt * 2; }
            if (Math.hypot(o.vx, o.vz) > 4 && c.actors.some((e) => e.team === 1 && !e.dead && Math.hypot(e.x - o.x, e.z - o.z) < e.r + 0.35)) o.t = o.dur; // it hits someone: boom
            o.me.position.set(o.x, 0, o.z); const fl = o.dur - o.t < 1 ? Math.sin(o.t * 40) > 0 : Math.sin(o.t * 12) > 0;
            const u = o.me.userData.body.material.uniforms; if (u && u.uFlash) { u.uFlash.value = fl ? 0.6 : 0; u.uFlashCol && u.uFlashCol.value.set(0xff2a1a); }
            if (o.t >= o.dur) { this.kill(o); this.blast(o.x, o.z, 3.6, 40, P); }
            break;
          }
          case 'potato': {
            const H = o.holder; if (o.passT > 0) o.passT -= dt;
            if (!H || H.dead || H.gone) { const n = this.foes(9, o.lx, o.lz)[0]; if (n) o.holder = n; else { this.kill(o); break; } }
            o.lx = o.holder.x; o.lz = o.holder.z;
            // touch passes it on: friend to friend, or from them to you (and you back to them)
            if (o.passT <= 0) for (const e of c.actors) {
              if (e === o.holder || e.dead || e.clone || e.st === 'swallowed' || (e.team === 1 && e.sleep)) continue;
              if (Math.hypot(e.x - o.holder.x, e.z - o.holder.z) < e.r + o.holder.r + 0.15) { o.holder = e; o.passT = 0.6; c.popAt(e, e === P ? 'YOU HAVE IT!' : 'PASSED!'); au.blip(false); break; }
            }
            const hs = o.holder.w ? 2.6 * (o.holder.size || 1) : 2.2; o.me.position.set(o.holder.x, hs, o.holder.z);
            const fl = Math.sin(o.t * (8 + o.t * 6)) > 0, u = o.me.userData.body.material.uniforms; if (u && u.uFlash) { u.uFlash.value = fl ? 0.6 : 0; u.uFlashCol && u.uFlashCol.value.set(0xff2a1a); }
            if (o.t >= o.dur) { const h = o.holder; this.kill(o); this.blast(h.x, h.z, 3.0, 42, P, { spareMe: h !== P }); if (h === P) c.damage(P, 25, null, 0, 0, true); }
            break;
          }
          case 'train': {
            const U = o.me.userData;
            U.lane.visible = o.t < o.warn + 0.5 && Math.sin(o.t * 18) > -0.3;
            if (o.t < o.warn && Math.floor(o.t * 4) !== Math.floor((o.t - dt) * 4)) au.tick();
            if (o.t >= o.warn) {
              U.loco.visible = true; o.front += dt * 36; U.loco.position.x = o.front;
              if (!o.honk) { o.honk = true; au.roar && au.whoosh(1); c.shake = Math.max(c.shake, 0.6); }
              for (const e of c.actors) {
                if (e.dead || o.hit.has(e) || Math.abs(e.z - o.z) > 1.25 || e.x > o.front || e.x < o.front - 7) continue;
                o.hit.add(e); if (e === P) { c.damage(P, 22, null, 6, 0, true); continue; }
                if (e.clone) { this.poof(e); continue; } e.sleep = false; c.damage(e, 60, P, 16, rnd(-3, 3), true);
              }
              for (const b of c.map.breakables) if (!b.broken && Math.abs(b.z - o.z) < 1.4 + (b.len || 0) / 2 && b.x < o.front && b.x > o.front - 7) { c.brk.smash(b, P, 12, 0); if (b.kind === 'vend') c.brk.smash(b, P, 12, 0); }
              if (o.front > 30) this.kill(o);
            }
            break;
          }
          case 'konbini':
            if (Math.hypot(P.x - o.x, P.z - o.z) < 1.3 && !this.shop) this.openShop(o);
            if (o.t > o.dur) this.kill(o);
            break;
          case 'bag': {
            const h = Math.max(0, 6 - o.t * 14); o.me.position.set(o.x, h, o.z); o.me.rotation.y = o.t * 0.5;
            if (h <= 0 && !o.landed) { o.landed = true; c.fx.dust(o.x, 0.1, o.z, 8, 0.4, 0.6, 0.3); au.thump(4); }
            if (o.landed && Math.hypot(P.x - o.x, P.z - o.z) < P.r + 0.45) {
              this.kill(o);
              if (Math.random() < 0.65) { P.giant = 7; P.hp = Math.min(P.maxHp, P.hp + 30); c.say('DELICIOUS!', 'Giant strength', 1.6); au.swell(0.6, 1); }
              else { P.poison = 5; c.damage(P, 10, null, 0, 0, false); c.say('FOOD POISONING!', 'Slow and sick for 5s', 1.6); }
            }
            if (o.t > o.dur) this.kill(o);
            break;
          }
        }
      }
      this.objs = this.objs.filter((o) => !o.dead);
    }
    spit() {
      const c = this.c, P = c.P, E = this.gulp.e, fx = Math.cos(P.f), fz = Math.sin(P.f); this.gulp = null;
      E.x = P.x + fx * (P.r + E.r + 0.2); E.z = P.z + fz * (P.r + E.r + 0.2); E.y = 1.0; E.vy = 2.5; E.vx = fx * 16; E.vz = fz * 16; E.thrownBy = P; E.st = 'thrown'; E.t = 0;
      c.abCd = c.ability ? c.ability.cd : 18; c.g.audio.whoosh(0.8); c.popAt(P, 'PTOO!'); c.fx.dust(E.x, 1, E.z, 10, 0.4, 0.5, 0.3);
    }
    // CONVENIENCE STORE: three skills on the shelf, pick one (or walk away)
    openShop(o) {
      const c = this.c, have = c.ability && c.ability.id;
      const L = POOL.filter((s) => s.id !== have && s.id !== 'konbini').sort(() => Math.random() - 0.5).slice(0, 3);
      this.shop = { o, L };
      const el = c.el('.ch-shop'); el.innerHTML = '<h2 data-jp="コンビニ">CONVENIENCE STORE</h2>' + L.map((s, i) => '<button data-shop="' + i + '"><kbd>' + 'JKL'[i] + '</kbd> ' + s.name + '<small>' + s.desc + '</small></button>').join('') + '<button data-shop="x"><kbd>Esc</kbd> WALK OUT</button>';
      el.classList.add('on'); c.cardOpen = true; c.shopping = true; c.g.audio.blip(true);
    }
    pick(i) {
      const c = this.c, S0 = this.shop; if (!S0) return;
      c.el('.ch-shop').classList.remove('on'); this.shop = null; c.cardOpen = false; c.shopping = false; this.kill(S0.o);
      if (i === 'x' || !S0.L[i]) return;
      const A = S0.L[i]; c.ability = A; c.abCd = 0; c.el('.ch-ab em').textContent = A.name; c.say(A.name, 'Bought', 1.4); c.g.audio.clack();
    }

    // ------------------------------------------------------------------ per-frame art (positions, scale, the whirlwind)
    draw(dt, T) {
      const c = this.c, P = c.P;
      for (const o of this.objs) if (o.type === 'smoke' && o.me) { for (const sp of o.me.children) { const s = sp.userData.s * (o.t < 0.4 ? o.t / 0.4 : o.t > o.dur - 1 ? Math.max(0.01, o.dur - o.t) : 1); sp.scale.setScalar(s); } }
      // shrunk enemies
      for (const e of c.actors) {
        if (e.w || !e.view || !e.view.root) continue;
        const want = e.shrinkT > 0 ? 0.55 : 1; e.shrinkS = (e.shrinkS || 1) + (want - (e.shrinkS || 1)) * Math.min(1, dt * 8);
        if (Math.abs(e.shrinkS - 1) < 0.002 && !e.shrinkBase) continue;
        const R = e.view.root; if (!e.shrinkBase) e.shrinkBase = R.scale.clone();
        R.scale.copy(e.shrinkBase).multiplyScalar(e.shrinkS); if (e.view.body && e.view.body.wrap) e.view.body.wrap.scale.setScalar(e.shrinkS);
        if (Math.abs(e.shrinkS - 1) < 0.002) { R.scale.copy(e.shrinkBase); if (e.view.body && e.view.body.wrap) e.view.body.wrap.scale.setScalar(1); e.shrinkBase = null; }
      }
      // the player's cyclone whirlwind
      const K = P.sk;
      if (K && K.kind === 'cyc') { if (!this.cyc) { this.cyc = S.R3.cyclone(); c.scene.add(this.cyc); } const k = Math.min(1, K.t / 0.3, (K.dur - K.t) / 0.3); S.R3.cycloneUpdate(this.cyc, P.x, P.z, 1.25, k, dt); if (Math.random() < dt * 30) { const a = Math.random() * TAU; c.fx.dust(P.x + Math.cos(a), 0.05, P.z + Math.sin(a), 1, 0.25, 0.5, 0.35, -Math.sin(a) * 4, Math.cos(a) * 4); } }
      else if (this.cyc) this.cyc.visible = false;
      // time drag: a faint purple wash
      c.R.post && 0;
    }
  }
  // ------------------------------------------------------------------ mask art: a face plate on the sumo's head
  function maskMesh(id) {
    if (id === 'none') return null;
    const W = S.R3, g = new THREE.Group(), T = (c, sh, o) => S.toon(c, Object.assign({ shade: sh }, o || {}));
    const plate = (col, sh) => { const m = W.mesh(new THREE.SphereGeometry(1, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), T(col, sh), 0.012); m.rotation.x = Math.PI / 2; m.scale.set(0.2, 0.09, 0.24); m.position.set(0, 0.05, 0.16); g.add(m); return m; };
    const eyes = (col) => { for (const sd of [-1, 1]) { const e = W.mesh(W.GEO.sphere, T(col, col), 0); e.scale.set(0.035, 0.02, 0.01); e.position.set(sd * 0.075, 0.09, 0.245); g.add(e); } };
    const horn = (col, sh, sd, len) => { const h = W.mesh(new THREE.ConeGeometry(0.035, len, 8), T(col, sh), 0.008); h.position.set(sd * 0.11, 0.26, 0.12); h.rotation.z = -sd * 0.45; g.add(h); };
    if (id === 'oni') { plate(0xc8231d, 0x6e1018); eyes(0xffd23a); horn(0xf2e6c8, 0x9a8a68, -1, 0.16); horn(0xf2e6c8, 0x9a8a68, 1, 0.16); const fang = W.mesh(new THREE.ConeGeometry(0.02, 0.06, 6), T(0xffffff, 0xb8b0a0), 0); fang.position.set(0.04, -0.03, 0.25); fang.rotation.x = Math.PI; g.add(fang); }
    else if (id === 'tengu') { plate(0xd8262e, 0x7a1414); eyes(0x141414); const nose = W.mesh(new THREE.ConeGeometry(0.035, 0.24, 10), T(0xd8262e, 0x7a1414), 0.01); nose.rotation.x = Math.PI / 2; nose.position.set(0, 0.04, 0.36); g.add(nose); for (const sd of [-1, 1]) { const b = W.mesh(W.GEO.box, T(0xf6f2ea, 0xb8b0a0), 0); b.scale.set(0.07, 0.015, 0.01); b.position.set(sd * 0.07, 0.14, 0.24); b.rotation.z = sd * 0.35; g.add(b); } }
    else if (id === 'kitsune') { plate(0xf6f2ea, 0xb8b0a0); for (const sd of [-1, 1]) { const e = W.mesh(W.GEO.box, T(0xd8262e, 0x7a1414), 0); e.scale.set(0.06, 0.014, 0.01); e.position.set(sd * 0.075, 0.09, 0.245); e.rotation.z = sd * 0.4; g.add(e); const ear = W.mesh(new THREE.ConeGeometry(0.05, 0.12, 4), T(0xf6f2ea, 0xb8b0a0), 0.008); ear.position.set(sd * 0.1, 0.24, 0.12); ear.rotation.z = -sd * 0.3; g.add(ear); } const sn = W.mesh(new THREE.ConeGeometry(0.06, 0.12, 8), T(0xf6f2ea, 0xb8b0a0), 0.008); sn.rotation.x = Math.PI / 2; sn.position.set(0, 0.02, 0.29); g.add(sn); }
    else if (id === 'hannya') { plate(0xeae2c8, 0xa89a78); eyes(0xffd23a); horn(0xd8c890, 0x8a7a48, -1, 0.2); horn(0xd8c890, 0x8a7a48, 1, 0.2); const m = W.mesh(W.GEO.box, T(0x7a1414, 0x3a0808), 0); m.scale.set(0.12, 0.025, 0.01); m.position.set(0, -0.02, 0.25); g.add(m); }
    else if (id === 'okame') { const p = plate(0xfbf6ee, 0xc8bca8); p.scale.set(0.22, 0.1, 0.25); for (const sd of [-1, 1]) { const ch = W.mesh(W.GEO.sphere, T(0xf08a8a, 0xc06060), 0); ch.scale.set(0.035, 0.03, 0.01); ch.position.set(sd * 0.11, 0.0, 0.235); g.add(ch); const e = W.mesh(W.GEO.box, T(0x141414, 0x141414), 0); e.scale.set(0.04, 0.008, 0.01); e.position.set(sd * 0.07, 0.09, 0.25); g.add(e); } }
    else if (id === 'fish') { const cap = W.mesh(new THREE.SphereGeometry(1, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), T(0x2f6fd0, 0x163a78), 0.012); cap.scale.set(0.26, 0.15, 0.26); cap.position.set(0, 0.17, 0.0); g.add(cap); const brim = W.mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.02, 16, 1, false, -Math.PI / 2, Math.PI), T(0x2f6fd0, 0x163a78), 0.008); brim.position.set(0, 0.18, 0.18); g.add(brim); const band = W.mesh(new THREE.TorusGeometry(0.255, 0.018, 6, 24), T(0xf6f2ea, 0xb8b0a0), 0); band.rotation.x = Math.PI / 2; band.position.y = 0.18; g.add(band); }
    return g;
  }
  CampSkills.POOL = POOL; CampSkills.BY = BY; CampSkills.MASKS = MASKS; CampSkills.maskMesh = maskMesh;
  S.CampSkills = CampSkills;
})();
