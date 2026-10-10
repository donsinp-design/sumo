'use strict';
// Simulation: wrestlers, collisions, balance, attacks, clinch, win detection.
// Everything is 2D on the ring floor (x, z). Rendering reads this state.
(function () {
  const RR = S.RING_R;
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const wrap = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
  S.clamp = clamp; S.wrap = wrap;
  // seeded random for anything that changes the fight (online play needs both sides to roll the same numbers)
  let seed = (Math.random() * 2 ** 31) | 0;
  S.seedRand = (n) => { seed = (n >>> 0) || 1; };
  S.getSeed = () => seed; S.setSeed = (n) => { seed = n; };
  S.rand = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  S.PRE_DUR = { clap: 0.3, stomp: 0.8, salt: 0.9, spread: 0.8, faceSlap: 0.35, beltSlap: 0.35,
    x_flex: 0.9, x_point: 0.6, x_drum: 0.8, x_hype: 0.9, x_bow: 0.8, x_neck: 0.6, x_cry: 0.9, x_shimmy: 1.0 };

  // technique tag -> kimarite, depending on how the round ended
  const OUT = {
    palm: 'tsukidashi', heavy: 'oshidashi', charge: 'oshidashi', side: 'oshidashi', rear: 'okuridashi',
    slap: 'hatakikomi', pull: 'hikiotoshi', hikiotoshi: 'hikiotoshi', drive: 'yorikiri', burst: 'yorikiri',
    rearDrive: 'okuridashi', break: 'oshidashi', lift: 'tsuridashi', utchari: 'utchari', tottari: 'tottari', katasukashi: 'katasukashi', swing: 'uwatenage',
    uwatenage: 'uwatenage', shitatenage: 'shitatenage', kotenage: 'kotenage', uchigake: 'uchigake', sotogake: 'sotogake',
  };
  const DOWN = Object.assign({}, OUT, {
    palm: 'tsukitaoshi', heavy: 'oshitaoshi', charge: 'oshitaoshi', side: 'tsukiotoshi', rear: 'okuritaoshi',
    drive: 'yoritaoshi', burst: 'yoritaoshi', rearDrive: 'okuritaoshi', break: 'oshitaoshi', lift: 'tsuriotoshi',
  });

  // ---------------------------------------------------------------- Wrestler
  class Wrestler {
    constructor(idx, arch) {
      this.idx = idx; this.a = arch; this.m = arch.mass;
      this.r = this.r0 = 0.7 * Math.pow(arch.scale, 0.85); this.m0 = arch.mass;
      this.input = S.NULL_IN; this.opp = null;
      this.reset(0, 0, 0);
    }
    reset(x, z, f) {
      this.x = x; this.z = z; this.vx = 0; this.vz = 0; this.f = f; this.fw = 0; this.y = 0;
      this.bal = 1; this.tx = 0; this.tz = 0; this.stam = 1;
      this.st = 'ready'; this.t = 0; this.dur = 0; this.hitDone = false;
      this.hand = 0; this.windPow = 0; this.cspd = 0; this.chargeHit = false; this.tachiai = false; this.dodged = false;
      this.braceT = 9; this.dashCD = 0; this.ddx = 0; this.ddz = 0; this.dpow = 1;
      this.sdx = 0; this.sdz = 0; this.fallX = 0; this.fallZ = 0;
      this.down = false; this.out = false; this.clinch = null; this.lifted = false;
      this.squash = 0; this.slideT = 0; this.pressT = 0; this.ghostT = 0;
      this.parryAt = -9; this.matta = 0; this.mattaPen = false; this.dashAt = -9; this.lean = 0; this.teeterEnd = -9; this.gripCD = 0; this.hariteUsed = false; this.hariteQ = false; this.flurry = 0; this.lastPalmAt = -9; this.teeter = false; this.crouchT = 0; this.feint = 0; this.feintAt = -9; this.feintBtn = null; this.buf = null;
      this.pre = null; this.preT = 9; this.stomped = false; this.power = 0; this.tachiPow = 0;
      this.lastTech = null; this.lastBy = null; this.lastT = -99;
      this.fxs = {}; this.str = 1; this.szCur = 1; this.charges = 0; this.torpedo = false; this.trapped = false;
      this.boomT = 0; this.swallowed = false; this.gulpI = -1; this.trail = []; this.trailT = 0; this.rwTrail = []; this.gulpT = 0; this.qT = 0; this.hyN = 0; this.hyHits = 0; this.dq = []; this.carried = false; this.inShop = false; this.chkBy = -1; this.ballCD = 0; this.ballHitT = 0; this.ballRoll = 0; this.chkA = 0; this.chkT = 0;
      if (this.r0) { this.r = this.r0; this.m = this.m0; }
      this.fwdIn = 0; this.inMag = 0; this.contact = false;
    }
    get fx() { return Math.cos(this.f); }
    get fz() { return Math.sin(this.f); }
    get spd() { return Math.hypot(this.vx, this.vz); }
    set(st, dur) { this.st = st; this.t = 0; this.dur = dur || 0; this.hitDone = false; if (st !== 'charge') this.holdCharge = false; }
  }
  S.Wrestler = Wrestler;

  // ------------------------------------------------------------------- Match
  class Match {
    constructor(archs) {
      this.w = [new Wrestler(0, archs[0]), new Wrestler(1, archs[1])];
      this.w[0].opp = this.w[1]; this.w[1].opp = this.w[0];
      this.wins = [0, 0]; this.round = 0; this.events = []; this.clinch = null;
      this.time = 0; this.phase = 'idle'; this.phaseT = 0; this.sinceGo = -1;
      this.deadT = 0; this.result = null; this.overT = 0; this.lastContactT = 0;
      this.skills = [null, null]; this.objs = []; this.fakeName = [null, null]; this.third = null; this.stage = 'dohyo'; this.stageA = 0; // a third wrestler, once someone calls one in
      this.history = []; // who won each round, in order (for the round circles)
    }
    emit(type, d) { d = d || {}; d.type = type; this.events.push(d); }

    newRound() {
      this.round++; this.clinch = null; this.time = 0; this.sinceGo = -1; this.result = null;
      this.deadT = 0; this.overT = 0; this.lastContactT = 0; this.objs = [];
      this.w[0].reset(-1.3, 0, 0);
      this.w[1].reset(1.3, 0, Math.PI);
      this.phase = 'shikiri'; this.phaseT = 0;
      if (this.third && S.Skills) S.Skills.spawnThird(this);
      this.goAt = 1.6 + S.rand() * 1.1;     // unpredictable start = tension
      this.emit('round', { round: this.round });
    }

    // what the wrestler's body actually receives this frame (status effects bend the controls)
    xform(w) {
      let c = w.ctrl; const f = w.fxs, P = w._px || (w._px = {});
      // SAKE: everything they press arrives 0.4s late, with the directions reversed
      if (f.drunk > 0) {
        const sn = (b) => ({ held: b.held, pressed: b.pressed, released: b.released, t: b.t });
        (w.dq || (w.dq = [])).push({ mx: c.mx, mz: c.mz, push: sn(c.push), grab: sn(c.grab), dash: sn(c.dash), skill: sn(c.skill), wd: null, ar: null });
        c = w.dq.length > 48 ? w.dq.shift() : { mx: 0, mz: 0, push: S.NULL_IN.push, grab: S.NULL_IN.grab, dash: S.NULL_IN.dash, skill: S.NULL_IN.skill };
      } else if (w.dq && w.dq.length) w.dq = [];
      let mx = c.mx, mz = c.mz;
      if (f.drunk > 0) { mx = -mx; mz = -mz; } // ...and the stick is backwards: left is right, up is down
      // POSSESSION: the body runs for the nearest edge, whatever they press
      if (f.possessed > 0) {
        let px = w.x, pz = w.z, l = Math.hypot(px, pz);
        if (l < 0.3) { px = w.x - w.opp.x; pz = w.z - w.opp.z; l = Math.hypot(px, pz) || 1; }
        mx = px / l; mz = pz / l; c = { mx, mz, push: S.NULL_IN.push, grab: S.NULL_IN.grab, dash: S.NULL_IN.dash, skill: S.NULL_IN.skill };
      }
      // CONTROLLER DISCONNECTED or stage fright under the spotlight: nothing gets through
      if (f.unplug > 0 || f.stagefright > 0) { mx = 0; mz = 0; c = { mx: 0, mz: 0, push: S.NULL_IN.push, grab: S.NULL_IN.grab, dash: S.NULL_IN.dash, skill: S.NULL_IN.skill }; }
      // CHICKEN: no hands to push or grab with
      if (f.chicken > 0) c = { mx, mz, push: S.NULL_IN.push, grab: S.NULL_IN.grab, dash: S.NULL_IN.dash, skill: S.NULL_IN.skill };
      if (f.dizzy > 0) {
        const an = this.time * 2.6 + w.idx * 2;
        mx = mx * 0.6 + Math.cos(an) * 0.7; mz = mz * 0.6 + Math.sin(an) * 0.7;
        const l = Math.hypot(mx, mz); if (l > 1) { mx /= l; mz /= l; }
      }
      const lock = f.frozen > 0 || f.grabbed > 0 || f.blind > 0 && false;
      const armless = f.noarms > 0; // NO ARMS: nothing to push or grab with
      const N = S.NULL_IN;
      P.mx = lock ? 0 : mx; P.mz = lock ? 0 : mz;
      P.push = lock || armless ? N.push : c.push; P.grab = lock || armless ? N.grab : c.grab; P.dash = lock ? N.dash : c.dash;
      P.skill = c.skill || N.skill; P.wd = c.wd || null; P.ar = c.ar || null;
      return P;
    }

    step(dt) {
      this.time += dt; this.phaseT += dt; this.deadT -= dt;
      const A = this.w[0], B = this.w[1];
      for (const w of this.w) { if (w.input !== w._px) w.ctrl = w.input; w.input = this.xform(w); }
      if (this.phase === 'shikiri') {
        // face-off: clap (push), stomp taunt (grab), hold dash to gather power for the charge
        for (const w of this.w) {
          const I = w.input;
          w.feint -= dt; w.preT += dt;
          for (const b of ['push', 'grab', 'dash']) if (I[b].pressed) { w.feintAt = this.phaseT; w.feintBtn = b; }
          // MATTA: jumping the gun (charging forward just before the call) restarts the face-off
          const odx = w.opp.x - w.x, odz = w.opp.z - w.z, odl = Math.hypot(odx, odz) || 1;
          if (I.push.pressed && (I.mx * odx + I.mz * odz) / odl > 0.5 && this.phaseT > Math.max(1.0, this.goAt - 0.6) && this.phaseT < this.goAt - 0.13 && !w.mattaPen) { // after two, no more restarts: you just go late
            w.matta = (w.matta || 0) + 1; if (w.matta >= 2) w.mattaPen = true;
            this.phaseT = 0.6; this.goAt = 1.6 + S.rand() * 1.1;
            for (const v of this.w) { v.pre = null; v.crouchT = 0; v.feintAt = -9; }
            this.emit('matta', { w, n: w.matta });
            return;
          }
          w.crouchT = I.dash.held ? (w.crouchT || 0) + dt : 0;
          // direction taps: W salt, A arms spread, S face slap, D belt slap
          const src = I.wd || { mx: I.mx, mz: I.mz };
          const dirs = { up: src.mz < -0.5, left: src.mx < -0.5, down: src.mz > 0.5, right: src.mx > 0.5 };
          const tapped = (k) => dirs[k] && !(w.pdir && w.pdir[k]);
          const ar = I.ar || {};
          const arT = (k) => ar[k] && !(w.par && w.par[k]);
          const busy = (w.pre && w.preT < (S.PRE_DUR[w.pre] || 0.3)) || w.crouchT > 0;
          if (!busy && this.phaseT > 0.85) {
            let pre = null;
            if (I.push.pressed) pre = 'clap';
            else if (I.grab.pressed) pre = 'stomp';
            else if (tapped('up')) pre = 'salt';
            else if (tapped('left')) pre = 'spread';
            else if (tapped('down')) pre = 'faceSlap';
            else if (tapped('right')) pre = 'beltSlap';
            else if (w.extraTaunts) {
              const slots = ['up', 'right', 'down', 'left'];
              for (let k = 0; k < 4; k++) if (arT(slots[k]) && w.extraTaunts[k]) { pre = 'x_' + w.extraTaunts[k]; break; }
            }
            if (pre) { w.pre = pre; w.preT = 0; w.stomped = false; this.emit(pre === 'stomp' ? 'stompUp' : pre === 'clap' ? 'clap' : 'taunt', { w, kind: pre }); }
          }
          w.pdir = dirs; w.par = Object.assign({}, ar);
          const hitAt = { stomp: 0.5, salt: 0.45, faceSlap: 0.12, beltSlap: 0.12, spread: 0.45, clap: 0.1 }[w.pre];
          if (w.pre && w.pre !== 'clap' && !w.stomped && w.preT > hitAt) { w.stomped = true; this.emit(w.pre === 'stomp' ? 'stomp' : 'tauntHit', { w, kind: w.pre }); }
        }
        if (this.phaseT >= this.goAt) {
          this.phase = 'fight'; this.sinceGo = 0;
          for (const w of this.w) {
            w.set('free');
            const set = (w.crouchT || 0) > 0.3; // fists down when the call comes: quicker start
            w.tachiPow = set ? 1 : 0;
            w.ignoreDash = set;
            w.crouchT = 0;
            // a press right before the call still counts (buffer)
            w.buf = this.phaseT - w.feintAt < 0.13 ? w.feintBtn : null;
            // caught mid-stomp: you start late. That's the price of showing off.
            const pd = S.PRE_DUR[w.pre] || 0;
            if (pd >= 0.7 && w.preT < pd) { w.set('recover', pd - w.preT); w.buf = null; }
            if (w.mattaPen) { w.mattaPen = false; w.set('recover', 0.35); w.buf = null; w.tachiPow = 0; } // second false start: you go late
          }
          this.emit('go');
        }
        return;
      }
      if (this.phase === 'fight') this.sinceGo += dt; else this.overT += dt;
      // statuses, size, skill use
      for (const w of this.w) {
        for (const k in w.fxs) if (w.fxs[k] > 0) w.fxs[k] -= dt;
        const f = w.fxs, tgt = f.giant > 0 ? 1.8 : f.chicken > 0 ? 0.45 : f.shrink > 0 ? 0.6 : 1;
        w.szCur += (tgt - w.szCur) * Math.min(1, dt * 7);
        w.r = w.r0 * w.szCur; w.m = w.m0 * (f.giant > 0 ? 2 : f.chicken > 0 ? 0.35 : f.shrink > 0 ? 0.5 : 1); w.str = f.giant > 0 ? 2 : f.shrink > 0 ? 0.5 : 1;
        // holding someone you consumed: Space spits them out the way you face
        if (this.phase === 'fight' && S.Skills && w.gulpI >= 0 && w.st !== 'spit' && w.input.skill.pressed && !w.down) S.Skills.spit(this, w);
        else if (this.phase === 'fight' && S.Skills && w.input.skill.pressed && this.skills[w.idx] && !w.down && w.st !== 'fall' && !w.lifted && !(this.skills[w.idx] === 'copycat' && (!this.skills[w.opp.idx] || this.skills[w.opp.idx] === 'fake')) && !(this.skills[w.idx] === 'favourite') && !(this.skills[w.idx] === 'reset' && !this.wins[0] && !this.wins[1] && !(this.third && this.third.wins)) && !(this.skills[w.idx] === 'third' && this.third)) {
          const id = this.skills[w.idx]; this.skills[w.idx] = null;
          S.Skills.use(this, w, id);
        }
      }
      if (S.Skills) S.Skills.update(this, dt);
      // DJ VINYL: the record turns all bout long and carries everyone round with it
      if (this.stage === 'vinyl' && this.phase === 'fight') {
        const da = 0.32 * dt, c = Math.cos(da), s = Math.sin(da);
        this.stageA += da;
        for (const w of this.w) { if (w.st === 'air' || w.carried || w.swallowed) continue; const x = w.x, z = w.z; w.x = x * c - z * s; w.z = x * s + z * c; w.f = S.wrap(w.f + da); }
        for (const q of this.objs) if (['banana', 'trap', 'beartrap', 'hole', 'pickup'].includes(q.type)) { const x = q.x, z = q.z; q.x = x * c - z * s; q.z = x * s + z * c; }
      }

      for (const w of this.w) this.control(w, dt);
      if (this.clinch) this.clinch.update(dt);
      for (const w of this.w) {
        if (!w.clinch) { w.x += w.vx * dt; w.z += w.vz * dt; }
        const lim = 5.85;
        if (Math.abs(w.x) > lim) { w.x = clamp(w.x, -lim, lim); w.vx = 0; }
        if (Math.abs(w.z) > lim) { w.z = clamp(w.z, -lim, lim); w.vz = 0; }
      }
      this.collide(A, B);
      if (A.contact) this.lastContactT = this.time;
      this.checkRing();
      if (this.phase === 'over') this.postRound();
    }

    // ---------------------------------------------------------- per wrestler
    control(w, dt) {
      const o = w.opp, a = w.a;
      const I = this.phase === 'fight' ? w.input : S.NULL_IN;
      const buf = w.buf; w.buf = null;
      const pr = (b) => I[b].pressed || buf === b;
      const slowK = (w.fxs.slow > 0 ? 0.45 : 1) * (w.gulpI >= 0 ? 0.8 : 1) * (w.fxs.haste > 0 ? 1.4 : 1) * (w.fxs.poison > 0 ? 0.75 : 1); // a belly full of wrestler slows you down dt *= slowK; // time drag: their whole body runs slow
      w.t += dt; w.dashCD -= dt; w.gripCD = (w.gripCD || 0) - dt; w.braceT += dt; w.ghostT -= dt; w.slideT -= dt; w.uprightT = (w.uprightT || 0) - dt;
      w.squash = Math.max(0, w.squash - dt * 5);
      w.throatT = (w.throatT || 0) - dt; w.thrHand = (w.thrHand || 0) - dt; w.throatCD = (w.throatCD || 0) - dt;
      if (w.st === 'fall' && w.t > 0.22 && !w.down) { w.down = true; w.squash = 1; this.emit('slam', { w, x: w.x, z: w.z }); } // hits the clay

      if (!w.clinch && w.y > 0 && w.st !== 'air') w.y = Math.max(0, w.y - dt * 2.5);
      if (w.torpedo && w.st !== 'charge') w.torpedo = false;
      if (!w.clinch && S.Skills && S.Skills.control(this, w, dt, I)) return;
      if (w.clinch) {
        w.fwdIn = 0;
        return; // clinch drives position, balance, stamina
      }

      const dx = o.x - w.x, dz = o.z - w.z;
      const dist = Math.hypot(dx, dz) || 1e-4, nx = dx / dist, nz = dz / dist;
      const mag = Math.min(1, Math.hypot(I.mx, I.mz));
      const ix = mag > 0.05 ? I.mx / Math.max(mag, 1e-4) * mag : 0, iz = mag > 0.05 ? I.mz / Math.max(mag, 1e-4) * mag : 0;
      w.fwdIn = mag > 0.2 ? (ix * nx + iz * nz) / mag : 0;
      w.inMag = mag;

      // ---------------- state transitions
      if (w.ignoreDash && !I.dash.held) w.ignoreDash = false;
      switch (w.st) {
        case 'free':
          if (w.ignoreDash) { if (pr('push')) this.startPush(w); else if (pr('grab')) w.set('grab'); }
          else if (pr('dash') && w.dashCD <= 0) { if (mag > 0.35) this.startDash(w, ix / mag, iz / mag); else this.startBrace(w); }
          else if (I.dash.held && I.dash.t > 0.1 && mag < 0.35) this.startBrace(w);
          else if (pr('push')) this.startPush(w);
          else if (pr('grab')) w.set('grab');
          break;
        case 'brace':
          if (!I.dash.held) w.set('free');
          else if (pr('push') && !(w.throatCD > 0) && Math.hypot(w.opp.x - w.x, w.opp.z - w.z) - w.r - w.opp.r < 0.5) { // feet planted, up close: hand to the throat
            w.throat = true; w.throatCD = 2; w.windPow = 0.3; w.set('heavy', 0.5); w.stam = Math.max(0, w.stam - 0.08);
            this.emit('heavyGo', { w, throat: true });
          }
          else if (pr('push')) this.startPush(w);
          else if (pr('grab')) w.set('grab');
          break;
        case 'palm':
          if (w.t >= 0.05 && w.t < 0.12) this.hitCheck(w, 'palm', 0.42);
          if (w.t >= 0.11 && pr('push')) { const hit = w.hitDone; w.hand ^= 1; w.set('palm'); this.palmCost(w, hit); this.emit('palm', { w }); }
          else if (w.t >= 0.11 && pr('grab')) w.set('grab');
          else if (pr('dash') && w.dashCD <= 0 && mag > 0.35) this.startDash(w, ix / mag, iz / mag);
          else if (w.t >= 0.2) {
            if (!w.hitDone && (w.flurry || 0) >= 4) { w.set('recover', 0.12 + 0.03 * Math.min(6, w.flurry)); this.hurt(w, 0.03, w.fx, w.fz, true); this.emit('whiff', { w, palm: true }); } // swinging at air: overreach
            else if (I.push.held && I.push.t > 0.17) { w.set('wind'); this.emit('wind', { w }); } else w.set('free');
          }
          break;
        case 'wind':
          w.windPow = clamp(w.t / 0.45, 0, 1);
          if (!I.push.held || w.t > 2) { w.throat = false; w.set('heavy', 0.5); w.stam = Math.max(0, w.stam - 0.08); this.emit('heavyGo', { w }); }
          else if (pr('dash') && w.dashCD <= 0 && mag > 0.35) this.startDash(w, ix / mag, iz / mag);
          break;
        case 'heavy':
          if (w.t >= 0.05 && w.t < 0.17 && this.hitCheck(w, 'heavy', w.throat ? 0.75 : 0.55)) w.dur = 0.34;
          if (w.t >= w.dur) { w.throat = false; w.set('free'); }
          else if (w.t >= 0.17 && pr('dash') && w.dashCD <= 0 && mag > 0.35) { w.throat = false; this.startDash(w, ix / mag, iz / mag); }
          break;
        case 'charge':
          if (w.holdCharge) { // a held charge: keeps going while L is held and there is breath, steers a little
            if (I.dash.held && w.stam > 0.02 && !w.chargeHit && w.t < 1.6) { w.dur = Math.max(w.dur, w.t + 0.08); w.stam = Math.max(0, w.stam - dt * 0.32); }
            if (!I.dash.held) w.dur = Math.min(w.dur, w.t + 0.05);
          }
          if (pr('push') && !w.chargeHit && !w.hariteUsed) w.hariteQ = true; // J again mid-charge: slap the face as you hit
          if (pr('dash') && w.t > 0.08 && !w.chargeHit) { // pull up short: counter to an expected sidestep
            w.set('brace'); w.braceT = 0.3; w.vx *= 0.35; w.vz *= 0.35;
            this.hurt(w, 0.08, w.fx, w.fz, true);
            this.emit('chargeCancel', { w });
          } else if (w.chargeHit) w.set('recover', 0.14);
          else if (w.t >= w.dur) {
            const dodged = w.dodged; w.dodged = false;
            w.set('overrun', dodged ? 0.75 : 0.38);
            this.hurt(w, dodged ? 0.14 : 0.08, w.fx, w.fz, true);
            this.emit('whiff', { w });
          }
          break;
        case 'slap':
          if (w.t >= 0.06 && w.t < 0.24 && !w.hitDone) this.slapCheck(w);
          if (w.t >= w.dur) { if (!w.hitDone) { w.set('recover', 0.32); this.emit('whiff', { w, slap: true }); } else w.set('free'); } // slapped at nothing: caught leaning
          break;
        case 'grab':
          if (w.t >= 0.06 && w.t < 0.17 && this.tryClinch(w)) return;
          if (w.t >= 0.17) { w.set('recover', 0.3); this.emit('whiff', { w, grab: true }); }
          break;
        case 'dash':
          if (w.t >= w.dur) {
            // dashing straight at them commits you; sidesteps and retreats recover quickly
            const dx0 = w.opp.x - w.x, dz0 = w.opp.z - w.z, dl0 = Math.hypot(dx0, dz0) || 1, fwd = (w.ddx * dx0 + w.ddz * dz0) / dl0;
            if (I.dash.held && fwd < 0.5) { w.set('brace'); w.braceT = 0.3; } else w.set('recover', fwd > 0.5 ? 0.2 : 0.06);
          }
          break;
        case 'recover': case 'stun': case 'overrun':
          if (w.t >= w.dur) w.set('free');
          else if (w.st === 'recover' && pr('dash') && w.dashCD <= 0 && mag > 0.35) this.startDash(w, ix / mag, iz / mag);
          break;
        case 'stumble':
          if (w.t > 0.3 && w.bal > 0.45) w.set('free');
          break;
      }

      // ---------------- locomotion (feet push the body toward a desired velocity)
      const ms = a.maxSpeed;
      let vdx = 0, vdz = 0, F = a.moveForce, turnK = 1, face = true, rec = 0.6;
      const mv = (k) => {
        if (mag < 0.05) return;
        const along = (ix * w.fx + iz * w.fz) / mag;
        const fac = along >= 0 ? 1 : 1 + along * 0.38; // backing up is slower
        vdx = ix * ms * k * fac; vdz = iz * ms * k * fac;
      };
      switch (w.st) {
        case 'free': mv(1); if (w.contact && w.fwdIn > 0.4) F = a.pushForce * (this.deadT > 0 ? 1.15 : 1) * (w.uprightT > 0 ? 0.55 : 1); break;
        case 'brace': mv(0.2); F = a.pushForce * 1.6 * (0.45 + 0.55 * w.stam); turnK = 0.6; rec = 0.6; break;
        case 'palm': if (w.t < 0.11) { vdx = w.fx * 1.4; vdz = w.fz * 1.4; } else mv(0.5); rec = 0.3; break;
        case 'wind': mv(0.78); turnK = 0.8; rec = 0.3; break;
        case 'heavy':
          if (w.t >= 0.05 && w.t < 0.17) { vdx = w.fx * 3.8; vdz = w.fz * 3.8; F = a.pushForce * 1.4; }
          else if (w.t >= 0.17) mv(0.15);
          turnK = 0.15; rec = 0.1; break;
        case 'charge': vdx = w.fx * w.cspd; vdz = w.fz * w.cspd; F = a.moveForce * 2.6; turnK = 0.12; rec = 0.05; break;
        case 'overrun': { const sp = w.spd; vdx = w.vx * 0.75; vdz = w.vz * 0.75; if (sp < 0.1) { vdx = vdz = 0; } F = a.moveForce * 0.28; turnK = 0.15; rec = 0.05; break; }
        case 'slap':
          if (w.t < 0.13) { vdx = -w.fx * 3.0; vdz = -w.fz * 3.0; F = a.moveForce * 1.5; } else mv(0.2);
          turnK = 0.5; rec = 0.2; break;
        case 'grab': vdx = w.fx * 2.0; vdz = w.fz * 2.0; rec = 0.25; break;
        case 'dash': { const k2 = w.t < w.dur * 0.7 ? 1 : 0.45; vdx = w.ddx * a.dashSpeed * w.dpow * k2; vdz = w.ddz * a.dashSpeed * w.dpow * k2; F = w.m * 95; rec = 0.3; break; }
        case 'recover': mv(0.4); F *= 0.7; rec = 0.3; break;
        case 'stun': F *= 0.25; rec = 0; break;
        case 'stumble': vdx = w.sdx * 1.3 + ix * ms * 0.25; vdz = w.sdz * 1.3 + iz * ms * 0.25; F *= 0.45; turnK = 0.3; rec = 0.4; break;
        case 'fall': // tipping over carries you along; once you hit the clay you skid to a stop
          if (w.down) { vdx = 0; vdz = 0; F = a.moveForce * 0.9; } else { vdx = w.fallX * 0.8; vdz = w.fallZ * 0.8; F *= 0.4; }
          face = false; rec = 0; break;
        case 'win': case 'lose': F *= 0.8; face = false; rec = 1; break;
      }
      if (w.slideT > 0) F *= 0.33;
      F *= w.str * slowK; vdx *= slowK; vdz *= slowK;
      if (w.fxs.turnLock > 0) face = false;
      // dig heels into the straw bales when being forced out
      const dc = Math.hypot(w.x, w.z);
      if (dc > RR - 0.45 && w.st !== 'fall') {
        const ox = w.x / dc, oz = w.z / dc;
        const outV = w.vx * ox + w.vz * oz;
        if (outV > 0 && vdx * ox + vdz * oz < 0.5) F *= 1.7;
        // sent stumbling at the straw: dig in and teeter, slow ones survive
        if ((w.st === 'overrun' || w.st === 'stumble') && outV > 0 && !w.clinch && this.time - w.teeterEnd > 0.8) {
          // heels on the straw, arms windmilling: hold toward the middle to win your balance back
          w.vx -= ox * outV * 0.85; w.vz -= oz * outV * 0.85;
          w.lean = Math.min(0.85, 0.4 + outV * 0.07 + (1 - w.bal) * 0.25);
          w.set('teeter', 1.2); w.teeter = true;
          this.emit('teeter', { w });
        }
      }
      if (w.st === 'teeter') {
        const tx = w.x / (dc || 1), tz = w.z / (dc || 1);
        vdx = 0; vdz = 0; F = a.moveForce * 3; face = false;
        const inward = mag > 0.2 ? -(ix * tx + iz * tz) / mag : 0; // pushing toward the middle (+) or out (-)
        w.lean += dt * (1.0 - 2.1 * Math.max(0, inward) + 1.2 * Math.max(0, -inward) + (w.contact ? 1.0 : 0)) / (0.8 + 0.2 * a.stability);
        if (w.lean <= 0) { w.set('recover', 0.15); w.vx = -tx * 1.6; w.vz = -tz * 1.6; w.bal = Math.max(w.bal, 0.5); this.emit('teeterSave', { w }); w.teeterEnd = this.time; }
        else if (w.lean >= 1 || w.t >= w.dur) { w.set('stumble'); w.sdx = tx; w.sdz = tz; w.vx = tx * 2.2; w.vz = tz * 2.2; this.emit('teeterFall', { w }); w.teeterEnd = this.time; }
      }
      let ax = (vdx - w.vx) * 16, az = (vdz - w.vz) * 16;
      const amax = F / w.m, al = Math.hypot(ax, az);
      if (al > amax) { ax *= amax / al; az *= amax / al; }
      const sp = w.spd;
      // sharp reversal at speed costs balance
      if (w.st === 'free' && sp > ms * 0.62 && mag > 0.5) {
        const c = (w.vx * ix + w.vz * iz) / (sp * mag);
        if (c < -0.2) this.hurt(w, dt * 0.55 * (sp / ms) * -c, w.vx / sp, w.vz / sp, true);
      }
      w.vx += ax * dt; w.vz += az * dt;
      if (w.down) { const k = Math.exp(-dt * 7); w.vx *= k; w.vz *= k; if (Math.hypot(w.vx, w.vz) < 0.15) w.vx = w.vz = 0; } // down means down: a short skid, then still

      // facing: always tries to square up to the opponent, but turning has inertia
      if (w.gulpI >= 0) { // carrying someone in your belly: face where you walk, so you can aim the spit
        const mag2 = Math.hypot(I.mx, I.mz);
        if (mag2 > 0.25) w.f += clamp(wrap(Math.atan2(I.mz, I.mx) - w.f), -8 * dt, 8 * dt);
      } else if (face) {
        const tgt = Math.atan2(nz, nx);
        const rate = a.turnRate * turnK / (1 + sp * 0.16);
        w.f += clamp(wrap(tgt - w.f), -rate * dt, rate * dt);
      }
      w.f = wrap(w.f + w.fw * dt); w.fw *= Math.exp(-5 * dt);

      // stamina
      w.stam = clamp(w.stam + dt * (w.st === 'brace' ? -0.16 : 0.3), 0, 1);

      // overcommit: leaning into someone who suddenly isn't there
      if (w.st === 'free' && this.phase === 'fight') {
        if (w.contact && w.fwdIn > 0.5) w.pressT = Math.min(0.6, w.pressT + dt);
        else {
          if (!w.contact && w.pressT > 0.2 && w.fwdIn > 0.5 &&
              (o.st === 'dash' || o.st === 'slap' || o.fwdIn < -0.4)) {
            this.tag(w, o, 'pull');
            this.hurt(w, 0.12 + 0.35 * w.pressT, w.fx, w.fz);
            w.vx += w.fx * 1.6; w.vz += w.fz * 1.6;
            if (w.st === 'free') { w.set('stumble'); w.sdx = w.fx; w.sdz = w.fz; }
            w.pressT = 0;
            this.emit('overcommit', { w });
          }
          w.pressT = Math.max(0, w.pressT - dt * 3);
        }
      } else w.pressT = Math.max(0, w.pressT - dt * 3);

      this.recover(w, dt, rec);
    }

    recover(w, dt, rate) {
      if (w.st === 'fall' || w.down) return;
      w.bal = Math.min(1, w.bal + rate * w.a.recovery * dt);
      const k = Math.exp(-dt * 2.5); w.tx *= k; w.tz *= k;
    }

    // --------------------------------------------------------------- actions
    startBrace(w) { w.set('brace'); w.braceT = 0; w.parryAt = this.time; this.emit('brace', { w }); }

    startDash(w, dx, dz) { w.dashAt = this.time;
      w.ddx = dx; w.ddz = dz;
      w.dpow = w.stam > 0.15 ? 1 : 0.6;
      w.set('dash', w.a.dashTime);
      w.dashCD = 0.42; w.stam = Math.max(0, w.stam - 0.1);
      this.emit('dash', { w });
      // perfect sidestep vs an incoming charge
      const o = w.opp;
      if (o.st === 'charge' || (o.st === 'heavy' && o.t < 0.17)) {
        const ov = o.spd; if (ov < 1) return;
        const rx = w.x - o.x, rz = w.z - o.z, d = Math.hypot(rx, rz);
        const closing = (o.vx * rx + o.vz * rz) / d;
        const t2i = (d - w.r - o.r) / Math.max(closing, 0.1);
        const lateral = Math.abs(dx * o.vx / ov + dz * o.vz / ov) < 0.6;
        if (closing > 2 && t2i < 0.3 && lateral) {
          w.ghostT = 0.3; o.dodged = true;
          this.tag(o, w, 'dodge');
          this.hurt(o, 0.16, o.vx / ov, o.vz / ov, false);
          if (o.st === 'charge') o.dur = Math.max(o.dur, o.t + 0.12);
          this.emit('perfectDodge', { w, o, henka: this.sinceGo < 0.7 });
        }
      }
    }

    startPush(w) {
      const ms = w.a.maxSpeed;
      const vf = w.vx * w.fx + w.vz * w.fz;
      w.chargeHit = false; w.dodged = false;
      if (w.fwdIn < -0.55 && w.inMag > 0.5) { w.set('slap', 0.45); this.emit('slapGo', { w }); return; }
      if (this.sinceGo < 0.85 && !w.tachiai && w.fwdIn > -0.5) { // the opening charge: generous window after the call
        w.tachiai = true; w.cspd = ms * 1.45 * (1 + 0.15 * w.tachiPow); w.set('charge', 0.36);
        w.stam = Math.max(0, w.stam - 0.12);
        this.emit('charge', { w, tachiai: true }); return;
      }
      const gapNow = Math.hypot(w.opp.x - w.x, w.opp.z - w.z) - w.r - w.opp.r;
      if (vf > ms * 0.45 && w.fwdIn > 0.5 && gapNow > 0.7) { // needs a real run-up; up close it's a hand // running at them from a distance: charge (up close it's a slap)
        w.cspd = Math.max(vf, ms) * 1.2; w.set('charge', 0.4);
        w.stam = Math.max(0, w.stam - 0.12);
        this.emit('charge', { w }); return;
      }
      w.set('palm'); w.hand ^= 1; this.palmCost(w, true);
      this.emit('palm', { w });
    }

    // every palm in a quick string costs more stamina; a long flurry wears you out
    palmCost(w, lastHit) {
      w.flurry = this.time - w.lastPalmAt < 0.5 && this.time >= w.lastPalmAt ? (w.flurry || 0) + 1 : 1;
      w.lastPalmAt = this.time;
      w.stam = Math.max(0, w.stam - (0.04 + 0.018 * Math.min(6, Math.max(0, w.flurry - 2)) + (lastHit ? 0 : 0.02)));
    }

    hitCheck(w, kind, extra) {
      if (w.hitDone) return false;
      const o = w.opp;
      if (o.st === 'fall' || o.down) return false;
      const dx = o.x - w.x, dz = o.z - w.z, d = Math.hypot(dx, dz) || 1e-4;
      if (d > w.r + o.r + extra) return false;
      const nx = dx / d, nz = dz / d;
      if (nx * w.fx + nz * w.fz < 0.5) return false;
      w.hitDone = true;
      this.applyHit(w, o, kind, nx, nz);
      return true;
    }

    zoneOf(T, nx, nz) { // n = direction attacker -> T
      const fr = -(T.fx * nx + T.fz * nz);
      return fr > 0.45 ? 'front' : fr > -0.35 ? 'side' : 'rear';
    }

    applyHit(w, o, kind, nx, nz) {
      const zone = this.zoneOf(o, nx, nz);
      // parry: a brace tapped just as the hand arrives knocks it aside
      if (zone === 'front' && (o.st === 'brace' || o.st === 'free') && this.time - (o.parryAt === undefined ? -9 : o.parryAt) < 0.17 && (kind === 'palm' || kind === 'heavy')) {
        w.set('stun', kind === 'heavy' ? 0.45 : 0.32);
        this.hurt(w, kind === 'heavy' ? 0.16 : 0.1, -nx, -nz, true);
        w.vx -= nx * 2; w.vz -= nz * 2;
        this.emit('parry', { w: o, o: w, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2 });
        return;
      }
      if (w.fxs.thiefT > 0 && S.Skills) S.Skills.knockSkill(this, w, o, nx, nz);
      const P = w.a.power * (w.str || 1);
      let imp, bal, tag;
      if (kind === 'palm') { const k = 0.65 + 0.35 * w.stam; imp = 2.3 * P * k; bal = 0.04 * k; tag = 'palm'; }
      else { imp = (3.2 + 3.4 * w.windPow) * P; bal = 0.08 + 0.16 * w.windPow; tag = 'heavy'; }
      const braced = o.st === 'brace' && zone === 'front' && o.stam > 0.05;
      if (zone === 'side') { imp *= 1.2; bal *= 1.8; tag = 'side'; }
      if (zone === 'rear') { imp *= 1.45; bal *= 2.4; tag = 'rear'; }
      let recoil = 0.15;
      if (braced) { imp *= 0.35; bal *= 0.3; recoil = 0.6; }
      const armored = o.st === 'charge' || (o.st === 'heavy' && o.t > 0.05 && o.t < 0.17);
      if (armored && kind === 'palm') { imp *= 0.3; bal *= 0.3; recoil = 0.5; }
      if (o.st === 'wind' || (o.st === 'grab' && o.t < 0.17)) { o.set('stun', 0.22); this.emit('interrupt', { w: o }); }
      if (o.bal < 0.35 && zone !== 'rear') bal += kind === 'heavy' ? 0.22 : 0.06;
      if (o.st === 'stumble' || o.st === 'teeter') { bal += 0.08; imp *= 1.3; } // already reeling: finish them
      let special = null;
      // harite: an open-hand slap to the face right off the start dazes them
      // (works on someone charging at you too: a slap in the face stops the charge dead)
      if (kind === 'palm' && zone === 'front' && this.sinceGo < 1.2 && !w.hariteUsed && !braced) { w.hariteUsed = true; special = 'harite'; o.set('stun', 0.4); bal += 0.06; if (armored) { imp /= 0.3; bal /= 0.3; recoil = 0.15; } }
      // nodowa: a heavy shove to the throat stands them up; they can't drive for a moment
      if (kind === 'heavy' && w.throat && zone !== 'rear' && !braced) { w.throat = false; special = 'nodowa'; o.uprightT = 0.7; o.set('stun', 0.15); o.throatT = 0.45; w.thrHand = 0.45; imp *= 0.8; }
      if (w.charges > 0) { const bst = 1 + w.charges * 1.1; imp *= bst; bal *= bst; this.emit('boost', { w, n: w.charges }); w.charges = 0; }
      if (o.fxs.invuln > 0) { imp *= 0.05; }
      if (o.fxs.absorb > 0) { imp *= 0.3; }
      const om = o.m * (braced ? 1.6 : 1);
      o.vx += nx * imp / om; o.vz += nz * imp / om;
      w.vx -= nx * imp * recoil / w.m; w.vz -= nz * imp * recoil / w.m;
      o.slideT = Math.max(o.slideT, kind === 'heavy' ? 0.32 : 0.14);
      o.squash = Math.min(1, imp / 5);
      const cr = o.fx * nz - o.fz * nx;
      o.fw += cr * (zone === 'front' ? 0.6 : 2.6) * (kind === 'heavy' ? 1.6 : 1);
      this.tag(o, w, tag);
      this.hurt(o, bal, nx, nz);
      this.emit('hit', { kind, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, nx, nz, power: imp, zone, braced, w, o, special });
    }

    slapCheck(w) {
      const o = w.opp;
      const dx = o.x - w.x, dz = o.z - w.z, d = Math.hypot(dx, dz) || 1e-4;
      if (d > w.r + o.r + 0.75) return;
      const nx = dx / d, nz = dz / d;
      if (nx * w.fx + nz * w.fz < 0.4) return;
      w.hitDone = true;
      const oIn = -(o.vx * nx + o.vz * nz); // opponent's speed toward me
      const ov = o.spd || 1;
      if (oIn > Math.max(2.0, o.a.maxSpeed * 1.05) || o.st === 'charge' || o.pressT > 0.15 || o.st === 'heavy' || ((o.st === 'palm' || o.st === 'recover') && (o.flurry || 0) >= 3 && this.time - o.lastPalmAt < 0.6)) {
        // Hatakikomi: their own momentum slams them down
        const dmg = 0.32 + 0.11 * Math.max(0, oIn) + (o.st === 'charge' ? 0.25 : 0) + ((o.flurry || 0) >= 3 && this.time - o.lastPalmAt < 0.6 ? 0.3 : 0); // flurrying = leaning in
        this.tag(o, w, 'slap');
        const fx = o.spd > 0.5 ? o.vx / ov : -nx, fz = o.spd > 0.5 ? o.vz / ov : -nz;
        o.vx += fx * 1.2; o.vz += fz * 1.2;
        if (o.st === 'charge') o.chargeHit = true;
        this.hurt(o, dmg, fx, fz);
        w.dur = 0.3; w.ghostT = 0.2;
        this.emit('hit', { kind: 'slap', x: o.x, z: o.z, nx: fx, nz: fz, power: 5 + oIn, zone: 'front', w, o, big: true });
      } else {
        this.hurt(o, 0.04, nx, nz);
        o.vx += nx * 0.6; o.vz += nz * 0.6;
        this.emit('hit', { kind: 'slapWeak', x: o.x, z: o.z, nx, nz, power: 1, zone: 'front', w, o });
      }
    }

    tryClinch(w) {
      const o = w.opp;
      if (w.gripCD > 0) return false; // hands still shaken loose from the last grip
      if (o.clinch || o.down || o.st === 'fall' || o.st === 'charge' || o.st === 'dash' || o.st === 'air' || o.fxs.thru > 0 || o.swallowed || w.swallowed || w.gulpI >= 0 || o.fxs.ball > 0 || w.fxs.ball > 0 || o.fxs.cyclone > 0 || w.fxs.cyclone > 0 || o.fxs.chicken > 0 || w.fxs.chicken > 0 || o.carried || w.carried || o.inShop || w.inShop || o.st === 'rewinding' || w.st === 'rewinding') return false; // (a wrestler winding back on the tape can't be grabbed)
      const dx = o.x - w.x, dz = o.z - w.z, d = Math.hypot(dx, dz) || 1e-4;
      if (d > w.r + o.r + 0.45) return false;
      const nx = dx / d, nz = dz / d;
      if (nx * w.fx + nz * w.fz < 0.4) return false;
      const fr = -(o.fx * nx + o.fz * nz);
      if (o.st === 'grab' && o.t < 0.09 && fr > 0) { this.grabTech(w, o); return true; } // both grabbed at once
      this.clinch = new Clinch(this, w, o, { rear: fr < -0.3, braced: o.st === 'brace', mutual: o.st === 'grab' });
      this.emit('clinch', { w, o, rear: fr < -0.3, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2 });
      return true;
    }

    // grab break: bounce apart, nobody gets the hold
    grabTech(a, b) {
      if (a.clinch) a.clinch.end('tech');
      const dx = b.x - a.x, dz = b.z - a.z, d = Math.hypot(dx, dz) || 1, nx = dx / d, nz = dz / d;
      a.vx = -nx * 3.2; a.vz = -nz * 3.2; b.vx = nx * 3.2; b.vz = nz * 3.2;
      a.set('recover', 0.22); b.set('recover', 0.22); a.ghostT = b.ghostT = 0.15; a.gripCD = 0.7;
      for (const w of [a, b]) { // a break never pushes anyone out of the ring
        const dc = Math.hypot(w.x, w.z);
        if (dc > RR - 1.4 && (w.vx * w.x + w.vz * w.z) > 0) { const sx = -w.z / dc, sz = w.x / dc, sg = (w.vx * sx + w.vz * sz) >= 0 ? 1 : -1; w.vx = sx * sg * 2.4 - w.x / dc * 0.8; w.vz = sz * sg * 2.4 - w.z / dc * 0.8; }
        w.lastTech = null; w.lastBy = null;
      }
      this.emit('grabTech', { w: b, o: a, x: (a.x + b.x) / 2, z: (a.z + b.z) / 2 });
    }

    tag(victim, by, tech) { victim.lastTech = tech; victim.lastBy = by; victim.lastT = this.time; }

    hurt(w, amt, dx, dz, self) {
      if (w.st === 'fall' || w.down || (this.phase !== 'fight' && this.phase !== 'over')) return;
      if (w.fxs.invuln > 0 && !self) return;
      if (w.fxs.absorb > 0 && !self) { amt *= 0.25; if (amt > 0.02 && w.charges < 3) { w.charges++; this.emit('absorbCharge', { w, n: w.charges }); } }
      const k = amt / w.a.stability;
      w.bal -= k;
      const l = Math.hypot(dx, dz) || 1;
      w.tx += dx / l * k * 1.5; w.tz += dz / l * k * 1.5;
      const tl = Math.hypot(w.tx, w.tz); if (tl > 1) { w.tx /= tl; w.tz /= tl; }
      if (w.bal <= 0) this.knockDown(w, dx, dz);
      else if (w.bal < 0.22 && !w.clinch && ['free', 'recover', 'palm', 'brace', 'dash', 'wind', 'grab', 'overrun'].includes(w.st)) {
        w.set('stumble'); w.sdx = dx / l; w.sdz = dz / l;
        this.emit('stumble', { w });
      }
    }

    knockDown(w, dx, dz) {
      if (w.clinch) w.clinch.end('fall');
      const l = Math.hypot(dx, dz) || 1;
      w.fallX = dx / l; w.fallZ = dz / l; w.bal = 0;
      w.set('fall', 0.3);
      this.emit('fall', { w });
    }

    // -------------------------------------------------------------- collision
    effMass(w, nx, nz) { // n points from w toward the other body
      let m = w.m;
      const front = w.fx * nx + w.fz * nz;
      if (w.st === 'brace' && front > 0.5) m *= 1 + 0.9 * (0.4 + 0.6 * w.stam);
      if (w.st === 'charge') m *= w.torpedo ? 2.2 : 1.35;
      if (w.fxs.invuln > 0) m *= 6;
      if (w.fxs.absorb > 0) m *= 3;
      if (w.fxs.frozen > 0) m *= 0.8;
      if (w.st === 'stumble' || w.st === 'fall') m *= 0.8;
      const dc = Math.hypot(w.x, w.z);
      if (dc > RR - 0.45 && (-nx * w.x - nz * w.z) / dc > 0.3) m *= 1.25;
      return m;
    }

    collide(A, B) {
      A.contact = B.contact = false;
      if (this.clinch) { A.contact = B.contact = true; return; }
      if (A.down && B.down) return;
      const dx = B.x - A.x, dz = B.z - A.z;
      let d = Math.hypot(dx, dz);
      const min = A.r + B.r;
      if (d >= min + 0.06) return;
      A.contact = B.contact = true;
      if (d >= min) return;
      if (A.ghostT > 0 || B.ghostT > 0 || A.st === 'air' || B.st === 'air' || A.fxs.thru > 0 || B.fxs.thru > 0) return;
      if (d < 1e-4) d = 1e-4;
      const nx = dx / d, nz = dz / d;
      const ma = this.effMass(A, nx, nz), mb = this.effMass(B, -nx, -nz);
      // someone lying on the clay is a dead weight: the other one is pushed off them, never the other way round
      const ia = A.down && !B.down ? 0 : 1 / ma, ib = B.down && !A.down ? 0 : 1 / mb, pen = min - d;
      A.x -= nx * pen * ia / (ia + ib); A.z -= nz * pen * ia / (ia + ib);
      B.x += nx * pen * ib / (ia + ib); B.z += nz * pen * ib / (ia + ib);
      // a dash into someone's chest carries no more weight than walking into them
      for (const [D, T, sx, sz] of [[A, B, nx, nz], [B, A, -nx, -nz]]) {
        if (!(D.st === 'dash' || (D.st === 'recover' && this.time - D.dashAt < 0.45))) continue;
        if (this.zoneOf(T, sx, sz) !== 'front' || (D.ddx * sx + D.ddz * sz) < 0.5) continue;
        const vin = D.vx * sx + D.vz * sz; if (vin > 2) { D.vx -= sx * (vin - 2); D.vz -= sz * (vin - 2); }
      }
      const rv = (B.vx - A.vx) * nx + (B.vz - A.vz) * nz;
      if (rv >= 0) return;
      const closing = -rv;
      const aIn = A.vx * nx + A.vz * nz, bIn = -(B.vx * nx + B.vz * nz);
      const aAgg = A.st === 'charge' || (A.st === 'heavy' && A.t > 0.04 && A.t < 0.18);
      const bAgg = B.st === 'charge' || (B.st === 'heavy' && B.t > 0.04 && B.t < 0.18);
      if (A.torpedo && S.Skills.parry(this, B, A, nx, nz)) { A.torpedo = false; return; }
      if (B.torpedo && S.Skills.parry(this, A, B, -nx, -nz)) { B.torpedo = false; return; }
      if (this.catchCheck(B, A, nx, nz) || this.catchCheck(A, B, -nx, -nz)) return;
      const ctr = this.braceCounter(B, A, nx, nz, aAgg) || this.braceCounter(A, B, -nx, -nz, bAgg);
      const e = ctr ? 0.55 : 0.06;
      const j = -(1 + e) * rv / (ia + ib);
      A.vx -= j * ia * nx; A.vz -= j * ia * nz;
      B.vx += j * ib * nx; B.vz += j * ib * nz;
      if (closing < 1.0) return;
      if (A.st === 'charge') A.chargeHit = true;
      if (B.st === 'charge') B.chargeHit = true;
      if (ctr) return;
      if (aAgg && bAgg && aIn > 1.6 && bIn > 1.6) { this.deadlock(A, B, nx, nz, closing); return; }
      if (aIn >= bIn) this.bodyHit(A, B, nx, nz, closing, aAgg);
      else this.bodyHit(B, A, -nx, -nz, closing, bAgg);
      // a dash is footwork, not a battering ram: running one into someone's chest stops you dead, and leaves you open
      for (const [D, T, sx, sz] of [[A, B, nx, nz], [B, A, -nx, -nz]]) {
        if (!(D.st === 'dash' || (D.st === 'recover' && this.time - D.dashAt < 0.45)) || this.zoneOf(T, sx, sz) !== 'front' || (D.ddx * sx + D.ddz * sz) < 0.5) continue;
        D.vx *= 0.15; D.vz *= 0.15; D.set('recover', 0.28);
        this.emit('dashBump', { w: D, o: T, x: (D.x + T.x) / 2, z: (D.z + T.z) / 2 });
      }
    }

    // Grab timed against an incoming charge: catch them and spin them round with their own momentum.
    catchCheck(T, At, nx, nz) { // n from At to T
      if (At.st !== 'charge' || T.st !== 'grab' || T.t > 0.19 || T.clinch || At.clinch || T.swallowed || At.swallowed) return false;
      if (-(T.fx * nx + T.fz * nz) < 0.5) return false;
      if (At.m > T.m * 1.3) return false; // too heavy to catch: you get bowled over
      const sp = At.spd;
      const c = this.clinch = new Clinch(this, T, At, {});
      const I = T.input, px = -nz, pz = nx;
      const li = I.mx * px + I.mz * pz;
      const side = Math.abs(li) > 0.3 ? -Math.sign(li) : (At.vx * px + At.vz * pz) >= 0 ? -1 : 1;
      const r0 = Math.hypot(At.x - T.x, At.z - T.z);
      c.tech = {
        kind: 'throw', w: T, o: At, t: 0, ok: true, name: 'tottari', side, dur: 0.42,
        sc: 0.75 + Math.min(0.35, sp * 0.04), px: T.x, pz: T.z, ox: At.x, oz: At.z,
        a0: Math.atan2(At.z - T.z, At.x - T.x), r0, fling: 1 + Math.min(1, sp / 8),
      };
      this.tag(At, T, 'tottari');
      this.emit('catch', { w: T, o: At, x: (T.x + At.x) / 2, z: (T.z + At.z) / 2 });
      return true;
    }

    braceCounter(T, At, nx, nz, agg) { // T braces, At attacks, n from At to T
      if (T.st !== 'brace' || !agg || At.st !== 'charge') return false;
      if (-(T.fx * nx + T.fz * nz) < 0.5) return false;
      if (T.braceT > 0.24 || T.stam < 0.1) return false;
      At.set('stun', 0.42);
      this.tag(At, T, 'heavy');
      this.hurt(At, 0.3, -nx, -nz, false);
      T.stam = Math.min(1, T.stam + 0.2);
      At.squash = 1; T.squash = 0.6;
      this.emit('braceCounter', { x: (T.x + At.x) / 2, z: (T.z + At.z) / 2, w: T, o: At, nx, nz });
      return true;
    }

    deadlock(A, B, nx, nz, closing) {
      for (const w of [A, B]) {
        if (w.st === 'charge' || w.st === 'heavy') w.set('free');
        w.slideT = 0.25; w.squash = 1;
      }
      this.hurt(A, 0.05, -nx, -nz, true);
      this.hurt(B, 0.05, nx, nz, true);
      this.deadT = 1.1;
      this.emit('deadlock', { x: (A.x + B.x) / 2, z: (A.z + B.z) / 2, nx, nz, power: closing * Math.sqrt(A.m * B.m) });
    }

    bodyHit(At, T, nx, nz, closing, agg) {
      const zone = this.zoneOf(T, nx, nz);
      const zm = zone === 'front' ? 1 : zone === 'side' ? 1.7 : 2.4;
      const braced = T.st === 'brace' && zone === 'front';
      let dmg = 0.032 * closing * Math.sqrt(At.m / T.m) * zm * (braced ? 0.35 : 1) * (agg ? 1.15 : At.st === 'free' ? 0.6 : 0.8) * ((At.st === 'dash' || this.time - (At.dashAt === undefined ? -9 : At.dashAt) < 0.45) && zone === 'front' ? 0.35 : 1);
      if (T.bal < 0.4 && zone !== 'rear') dmg *= 1.3;
      if (closing > 1.5) this.tag(T, At, zone === 'rear' ? 'rear' : zone === 'side' ? 'side' : At.st === 'charge' ? 'charge' : 'heavy');
      // harite: a face slap queued during the charge lands with the hit and dazes them
      if (At.st === 'charge' && At.hariteQ && zone === 'front' && !At.hariteUsed && T.st !== 'brace') {
        At.hariteQ = false; At.hariteUsed = true; T.set('stun', 0.4); dmg += 0.06;
        this.emit('hit', { kind: 'palm', x: T.x, z: T.z, nx, nz, power: 4, zone, w: At, o: T, special: 'harite' });
      }
      this.hurt(T, dmg, nx, nz);
      // a badly angled charge leaves the attacker off balance
      const af = At.fx * nx + At.fz * nz;
      if (af < 0.65 && closing > 2) this.hurt(At, 0.035 * closing * (1 - af), At.fx, At.fz, true);
      const cr = T.fx * nz - T.fz * nx;
      T.fw += -cr * closing * (zone === 'front' ? 0.4 : 1.2);
      T.slideT = Math.max(T.slideT, 0.08 + closing * 0.03);
      T.squash = Math.min(1, closing / 5); At.squash = Math.min(1, closing / 7);
      if (T.st === 'grab' && closing > 2.2) T.set('stun', 0.18);
      if (T.st === 'wind' && closing > 2.5) T.set('stun', 0.2);
      this.emit('impact', {
        x: (At.x + T.x) / 2, z: (At.z + T.z) / 2, nx, nz, power: closing * Math.sqrt(At.m * T.m),
        closing, zone, braced, a: At, t: T, agg,
      });
    }

    // ------------------------------------------------------------ win checks
    checkRing() {
      if (this.phase !== 'fight') return;
      let lo = null, ld = 0, cause = '';
      for (const w of this.w) {
        if (w.st === 'rewinding' || w.swallowed || w.carried || w.inShop) continue; // mid-rewind, or inside the other wrestler
        const d = Math.hypot(w.x, w.z);
        if (d > RR && d - RR > ld) { lo = w; ld = d - RR; cause = 'out'; }
      }
      if (!lo) for (const w of this.w) if (w.down && w.st !== 'rewinding') { lo = w; cause = 'down'; break; }
      if (lo) this.lose(lo, cause);
    }

    lose(L, cause) {
      // pushed out by the third wrestler: the round is theirs
      const thirdWin = this.third && this.time - (L.thirdT === undefined ? -9 : L.thirdT) < 2 && !(L.lastBy === L.opp && L.lastT > L.thirdT);
      // holding REWIND saves you: it fires by itself instead of losing
      if (this.skills[L.idx] === 'favourite' && S.Skills && !L.swallowed) { this.skills[L.idx] = null; this.emit('skillUse', { w: L, id: 'favourite', x: L.x, z: L.z, auto: true }); S.Skills.crowdSave(this, L, cause); return; }
      if (this.skills[L.idx] === 'rewind' && S.Skills && !L.swallowed) { this.skills[L.idx] = null; this.emit('skillUse', { w: L, id: 'rewind', x: L.x, z: L.z, auto: true }); S.Skills.rewind(this, L); return; }
      if (thirdWin) {
        this.result = { loser: L, winner: L.opp, cause, km: 'sk_third', third: true };
        this.phase = 'over'; this.overT = 0; this.third.wins++; this.history.push(2);
        L.out = cause === 'out'; if (this.clinch) this.clinch.end('decided');
        this.emit('decided', this.result); return;
      }
      const W = L.opp;
      const km = this.kimarite(L, cause);
      this.result = { loser: L, winner: W, cause, km };
      this.phase = 'over'; this.overT = 0;
      this.wins[W.idx]++; this.history.push(W.idx);
      L.out = cause === 'out';
      if (this.clinch) this.clinch.end('decided');
      this.emit('decided', this.result);
    }

    // nobody wins (a kamikaze that catches both): the round is fought again
    draw(km) {
      this.result = { draw: true, winner: this.w[0], loser: this.w[1], cause: 'draw', km };
      this.phase = 'over'; this.overT = 0;
      if (this.clinch) this.clinch.end('decided');
      this.emit('decided', this.result);
    }

    kimarite(L, cause) {
      const W = L.opp;
      const recent = L.lastBy === W && this.time - L.lastT < 2.5 ? L.lastTech : null;
      if (recent && recent.indexOf('sk_') === 0) return recent;
      if (recent && recent !== 'dodge') return (cause === 'out' ? OUT : DOWN)[recent] || (cause === 'out' ? 'oshidashi' : 'oshitaoshi');
      if (cause === 'out') {
        const sp = L.spd;
        const fwd = sp > 0.5 && (L.vx * L.fx + L.vz * L.fz) / sp > 0.3;
        return fwd ? 'isamiashi' : 'fumidashi';
      }
      return 'koshikudake';
    }

    postRound() {
      const r = this.result; if (!r || r.draw) return;
      const W = r.winner, L = r.loser;
      if (this.overT > 0.55 && !['win', 'fall'].includes(W.st) && !W.down) W.set('win');
      if (this.overT > 0.55 && !['lose', 'fall'].includes(L.st) && !L.down) L.set('lose');
    }
  }
  S.Match = Match;

  // ------------------------------------------------------------------ Clinch
  // A temporary positional battle. The pair moves as one body; each wrestler
  // pushes along the axis (drive / pull), sideways (rotate) or resists (brace).
  class Clinch {
    constructor(m, a, b, opt) {
      this.m = m; this.a = a; this.b = b; this.t = 0; this.done = false;
      this.grip = [0, 0]; this.type = ['inside', 'inside']; this.won = [false, false];
      this.grip[a.idx] = 1.3 + (a.a.grip - 1) * 1.2 + (opt.braced ? 0.55 : 0) - (opt.mutual ? 0.2 : 0);
      this.grip[b.idx] = 1.0 + (b.a.grip - 1) * 1.2 - (opt.braced ? 0.2 : 0);
      const aIn = a.a.key === 'tech' || a.r <= b.r + 0.02;
      this.type[a.idx] = aIn ? 'inside' : 'outside';
      this.type[b.idx] = aIn ? 'outside' : 'inside';
      this.rear = opt.rear ? a : null; this.turnT = 0;
      if (this.rear) { this.grip[a.idx] = 3; this.grip[b.idx] = 0; }
      this.M = a.m + b.m;
      this.ang = Math.atan2(b.z - a.z, b.x - a.x);
      this.cx = (a.x * a.m + b.x * b.m) / this.M; this.cz = (a.z * a.m + b.z * b.m) / this.M;
      const nx = Math.cos(this.ang), nz = Math.sin(this.ang);
      const px = a.vx * a.m + b.vx * b.m, pz = a.vz * a.m + b.vz * b.m;
      this.v = (px * nx + pz * nz) / this.M;
      this.vl = (-px * nz + pz * nx) / this.M;
      this.w = 0;
      this.d = Math.hypot(b.x - a.x, b.z - a.z);
      this.dT = (a.r + b.r) * 0.8;
      this.tech = null; this.lift = null;
      this.vul = [0, 0]; this.burst = [0, 0]; this.tow = [0, 0];
      a.clinch = b.clinch = this;
      a.kArm = !!(a.input && a.input.grab && a.input.grab.held); b.kArm = false; // keep holding the grab button, aim, release
      a.kAimAt = b.kAimAt = undefined;
      a.set('clinch'); b.set('clinch');
    }
    other(w) { return w === this.a ? this.b : this.a; }
    sg(w) { return w === this.a ? 1 : -1; }
    axis() { return [Math.cos(this.ang), Math.sin(this.ang)]; }
    rr() { return [this.d * this.b.m / this.M, this.d * this.a.m / this.M]; }

    update(dt) {
      if (this.done) return;
      const m = this.m, A = this.a, B = this.b;
      this.t += dt;
      this.d += (this.dT - this.d) * Math.min(1, dt * 10);
      for (const w of [A, B]) { this.burst[w.idx] -= dt; this.vul[w.idx] -= dt; }
      // a throw that has only just started can still be slipped (L) or shoved off (J)
      if (this.tech && this.tech.t < 0.25 && this.tech.kind !== 'utchari' && m.phase === 'fight') {
        const v = this.tech.o, atk = this.tech.w, I = v.input;
        if (I && (I.dash.pressed || I.push.pressed)) {
          this.tech = null;
          if (I.dash.pressed) this.tryDisengage(v); else this.tryBreak(v);
          atk.set('recover', 0.3); atk.gripCD = 0.7;
          m.emit('techEscape', { w: v, o: atk, x: (v.x + atk.x) / 2, z: (v.z + atk.z) / 2 });
          return;
        }
      }
      if (this.tech) { this.updateTech(dt); return; }
      const live = m.phase === 'fight';
      let [nx, nz] = this.axis();
      const px = -nz, pz = nx;

      // ---------- discrete actions
      let swung = false;
      if (live) {
        for (const w of [A, B]) {
          const I = w.input, s = this.sg(w);
          let tw = (I.mx * nx + I.mz * nz) * s;
          let sd = (I.mx * px + I.mz * pz) * s;
          if (this.lift) {
            if (this.lift.o === w) {
              if (I.push.pressed || I.grab.pressed || I.dash.pressed) { this.lift.w.stam -= 0.08; m.emit('struggle', { w }); }
            } else if (I.grab.pressed && this.lift.t > 0.6) { w.kArm = false; this.setDown(true); if (this.done) return; } // a slam needs a proper heave first: time to wriggle
            continue;
          }
          if (this.rear && this.rear !== w) { // facing away: can only turn around
            if (Math.abs(sd) > 0.4 || Math.abs(tw) > 0.4) {
              this.turnT += dt * 1.4 * (w.a.turnRate / 4.4);
              if (this.turnT >= 1) this.unRear();
            }
            continue;
          }
          if (this.rear === w && I.push.pressed) { this.rearShove(w); return; }
          if (I.grab.pressed && w === this.b && this.t < (m.techWin || 0.38) && !this.rear) { m.grabTech(this.a, this.b); return; }
          // one rule: while K is held you are in MOVE mode (swing, throw, trip, spin, lift); with K up the stick pushes and drags.
          if (I.grab.pressed) { w.kArm = true; w.kPressT = this.t; }
          else if (I.grab.held && !w.kArm) { w.kArm = true; w.kPressT = -9; } // still holding from the grab: move mode, not a tap
          // SWING: keep K held and point somewhere: they swing round you to that side
          if (w.kArm && I.grab.held && Math.hypot(I.mx, I.mz) > 0.4) {
            const o = this.other(w);
            const ta = Math.atan2(I.mz, I.mx), cur = Math.atan2(o.z - w.z, o.x - w.x);
            if ((this.swing && this.swing.w === w) || Math.abs(S.wrap(ta - cur)) > 0.6) { this.swingStep(w, ta, dt); swung = true; continue; }
          }
          // remember the aim while K is held, so letting go of the direction a hair early still counts
          if (I.grab.held && (Math.abs(tw) > 0.35 || Math.abs(sd) > 0.35)) { w.kAimTw = tw; w.kAimSd = sd; w.kAimAt = this.t; }
          if (I.grab.released && w.kArm) {
            w.kArm = false;
            if (this.swing && this.swing.w === w) { if (this.releaseSwing()) return; }
            if (Math.abs(tw) <= 0.35 && Math.abs(sd) <= 0.35 && w.kAimAt !== undefined && this.t - w.kAimAt < 0.2) { tw = w.kAimTw; sd = w.kAimSd; }
            // a quick tap that only grabbed should not fire a move by itself
            // every move is: hold K a moment, aim (or not, for a lift), let go. A quick press does nothing, so a
            // stray K (grabbing again, or pressing as they grab you) never lifts or trips by accident.
            const aimed = Math.abs(tw) > 0.35 || Math.abs(sd) > 0.35;
            const heldFor = w.kPressT >= 0 ? this.t - w.kPressT : this.t; // pressed while locked, or held since the grab
            const fresh = w.kPressT >= 0; // K pressed again after locking up; the grab's own K can aim a move but never lifts
            if (fresh ? heldFor >= 0.15 : (aimed && this.t >= 0.35)) { this.attempt(w, aimed ? tw : 0, aimed ? sd : 0); if (this.done || this.tech) return; }
          }
          else if (I.push.pressed) { this.tryBreak(w); if (this.done) return; }
          else if (I.dash.pressed) { this.tryDisengage(w); if (this.done) return; }
        }
      }

      if (swung) return; // the swing placed both bodies this frame
      if (this.swing && !(this.swing.w.input.grab.held)) this.swing = null;

      // ---------- continuous forces
      const intent = [0, 0], res = [0, 0], lat = [0, 0], rres = [0, 0], tow = [0, 0];
      for (const w of [A, B]) {
        const i = w.idx, s = this.sg(w), I = live ? w.input : S.NULL_IN;
        const o = this.other(w);
        const tw = (I.mx * nx + I.mz * nz) * s, lw = I.mx * px + I.mz * pz;
        tow[i] = tw;
        if (this.lift && this.lift.o === w) continue;
        const brace = false;
        const victim = this.rear && this.rear !== w, atk = this.rear === w;
        const P = w.a.pushForce * (w.str || 1) * (w.fxs.slow > 0 ? 0.5 : 1);
        let drive = P * (0.7 + 0.17 * this.grip[i]) * (0.45 + 0.55 * w.bal) * (0.45 + 0.55 * w.stam);
        if (atk) drive *= 1.7;
        if (victim) drive *= 0.15;
        if (this.burst[i] > 0) drive *= 2.3;
        if (this.vul[i] > 0) drive *= 0.3;
        if (brace) res[i] = P * 1.5 * (0.4 + 0.6 * w.stam) * (1.15 - 0.12 * this.grip[o.idx]) * (victim ? 0.3 : 1);
        else if (tw > 0.3) intent[i] = s * drive * Math.min(1, tw * 1.2);
        else if (tw < -0.3) intent[i] = -s * drive * 0.7 * Math.min(1, -tw * 1.2);
        else res[i] = P * 0.55 * (victim ? 0.3 : 1);
        if (Math.abs(lw) > 0.3 && !brace && !victim) lat[i] = lw * P * (0.5 + 0.18 * this.grip[i]) * w.a.tech;
        else rres[i] = P * (brace ? 1.1 : 0.45) * (victim ? 0.3 : 1);
        if (this.vul[i] > 0) { res[i] *= 0.4; rres[i] *= 0.4; }
        const working = intent[i] !== 0 || lat[i] !== 0;
        w.stam = clamp(w.stam - dt * (brace ? 0.14 : working ? 0.09 : -0.1), 0, 1);
      }
      this.tow = tow;

      if (this.lift) {
        const L = this.lift; L.t += dt;
        const I = live ? L.w.input : S.NULL_IN;
        const sp = 1.5 * Math.sqrt(L.w.a.pushForce / 24);
        const tv = (I.mx * nx + I.mz * nz) * sp, tl = (I.mx * px + I.mz * pz) * sp;
        this.v += (tv - this.v) * Math.min(1, dt * 6);
        this.vl += (tl - this.vl) * Math.min(1, dt * 6);
        this.w *= Math.exp(-dt * 6);
        L.w.stam -= dt * 0.4 * (L.o.m / L.w.m);
        if (L.w.stam <= 0 || L.t > 2.4 || L.w.bal < 0.3) this.setDown(false);
      } else {
        // axial push battle
        const net = intent[0] + intent[1];
        const dir = Math.sign(net);
        let Rs = 0;
        for (const w of [A, B]) {
          const i = w.idx;
          if (intent[i] === 0 || Math.sign(intent[i]) !== dir) Rs += res[i];
          const dc = Math.hypot(w.x, w.z);
          if (dir !== 0 && dc > RR - 0.45 && (w.x * nx + w.z * nz) / dc * dir > 0.3 && intent[i] * dir <= 0) {
            const fighting = intent[i] * dir < 0 || (live && w.input.dash.held);
            Rs += w.a.pushForce * (fighting ? 0.55 : 0.12); // heels on the straw only help if you fight it
          }
        }
        const eff = dir * Math.max(0, Math.abs(net) - Rs);
        this.v += eff / this.M * dt;
        this.v *= Math.exp(-dt * (eff === 0 ? 7 : 1.8));
        // rotation
        const [ra, rb] = this.rr();
        const tau = rb * lat[B.idx] - ra * lat[A.idx];
        const Rr = (rres[0] + rres[1]) * this.d * 0.5;
        const te = Math.sign(tau) * Math.max(0, Math.abs(tau) - Rr);
        const J = A.m * ra * ra + B.m * rb * rb;
        this.w += te / J * dt * 1.4;
        this.w *= Math.exp(-dt * (te === 0 ? 8 : 2.6));
        this.w = clamp(this.w, -3, 3);
        this.vl += (lat[0] + lat[1]) / this.M * dt * 0.35;
        this.vl *= Math.exp(-dt * 4);

        // balance consequences
        for (const w of [A, B]) {
          const i = w.idx, s = this.sg(w), o = this.other(w), j = o.idx;
          if (live && tow[i] > 0.3 && tow[j] < -0.3) { // pulled while driving
            m.tag(w, o, 'pull');
            m.hurt(w, dt * 0.3 * (1 + Math.abs(this.v) * 0.4), s * nx, s * nz);
          }
          const back = -s * this.v;
          // elbows tight (no stick input, not being driven): their grip stops growing and yours creeps back
          const oI = live ? o.input : S.NULL_IN, oTight = Math.hypot(oI.mx, oI.mz) < 0.2 && this.tow[j] > -0.3;
          const myI = live ? w.input : S.NULL_IN;
          // the grip battle: drive them back to work your hands deeper; get driven back and your hands slip
          if (live && Math.hypot(myI.mx, myI.mz) < 0.2 && back < 0.35) this.grip[i] = Math.min(1.6, this.grip[i] + dt * 0.2);
          if (live && -back > 0.35 && tow[i] > 0.3) this.grip[i] = Math.min(3, this.grip[i] + dt * (oTight ? 0.25 : 0.5));
          // won the grip battle (clearly ahead): a better hold, and an inside grip if you didn't have one
          if (live && !this.won[i] && this.grip[i] - this.grip[j] > 0.6 && !this.rear) {
            this.won[i] = true; this.won[j] = false;
            if (this.type[i] === 'outside') { this.type[i] = 'inside'; this.type[j] = 'outside'; }
            m.emit('gripWin', { w, o });
          }
          if (back > 0.35 && tow[i] > -0.3) {
            m.tag(w, o, this.rear === o ? 'rearDrive' : 'drive');
            m.hurt(w, dt * 0.04 * back, -s * nx, -s * nz);
            if (live) this.grip[i] = Math.max(0, this.grip[i] - dt * 0.3);
          }
          const mine = w === A ? -lat[i] : lat[i];
          if (Math.abs(this.w) > 0.9 && Math.sign(mine) !== Math.sign(this.w)) {
            m.hurt(w, dt * 0.16 * (Math.abs(this.w) - 0.7), px * Math.sign(this.w), pz * Math.sign(this.w));
          }
          if (this.done) return;
          m.recover(w, dt, 0.2);
        }
      }

      this.ang = wrap(this.ang + this.w * dt);
      [nx, nz] = this.axis();
      this.cx += (nx * this.v - nz * this.vl) * dt;
      this.cz += (nz * this.v + nx * this.vl) * dt;
      this.place(dt);

      // referee breaks up a stalled clinch (no infinite clinches)
      const busy = !this.lift && (intent[0] !== 0 || intent[1] !== 0 || lat[0] !== 0 || lat[1] !== 0);
      this.idleT = busy || Math.abs(this.v) > 0.3 ? 0 : (this.idleT || 0) + dt;
      // a dead-even shoving match with nothing moving also gets broken up
      this.stallT = Math.abs(this.v) < 0.25 && Math.abs(this.w) < 0.35 ? (this.stallT || 0) + dt : 0;
      if (this.stallT > 3.5) { this.separate(); return; }
      if (this.idleT > 2.0 || (this.t > 3 && A.stam < 0.1 && B.stam < 0.1 && Math.abs(this.v) < 0.3) || this.t > 15) this.separate();
    }

    place(dt) {
      const A = this.a, B = this.b;
      const [nx, nz] = this.axis();
      const [ra, rb] = this.rr();
      const ax = this.cx - nx * ra, az = this.cz - nz * ra, bx = this.cx + nx * rb, bz = this.cz + nz * rb;
      const cap = (v) => clamp(v, -9, 9);
      A.vx = cap((ax - A.x) / dt); A.vz = cap((az - A.z) / dt);
      B.vx = cap((bx - B.x) / dt); B.vz = cap((bz - B.z) / dt);
      A.x = ax; A.z = az; B.x = bx; B.z = bz;
      const turn = (w, tgt) => { w.f += clamp(wrap(tgt - w.f), -10 * dt, 10 * dt); };
      if (this.rear) {
        const atk = this.rear, vic = this.other(atk);
        const fa = atk === A ? this.ang : wrap(this.ang + Math.PI);
        turn(atk, fa);
        turn(vic, wrap(fa + Math.PI * this.turnT));
      } else {
        turn(A, this.ang); turn(B, wrap(this.ang + Math.PI));
      }
      for (const w of [A, B]) {
        const tgt = this.lift && this.lift.o === w ? 0.42 : 0;
        w.y += (tgt - w.y) * Math.min(1, dt * 9);
      }
    }

    resync() {
      const A = this.a, B = this.b;
      this.ang = Math.atan2(B.z - A.z, B.x - A.x);
      this.d = Math.hypot(B.x - A.x, B.z - A.z);
      this.cx = (A.x * A.m + B.x * B.m) / this.M; this.cz = (A.z * A.m + B.z * B.m) / this.M;
      this.v = 0; this.vl = 0; this.w = 0;
    }

    unRear() {
      this.rear = null; this.turnT = 0;
      this.grip = [1, 1];
      this.m.emit('turnaround', {});
    }

    // ---------- technique resolution
    utchariOk(w) {
      const o = this.other(w), s = this.sg(w);
      const [nx, nz] = this.axis();
      const dc = Math.hypot(w.x, w.z);
      if (dc < RR - 0.55) return false; // heels on the bales
      const ux = w.x / dc, uz = w.z / dc;
      if (-(s * nx) * ux - (s * nz) * uz < 0.5) return false; // opponent must be pushing me outward
      const back = -s * this.v;
      return back > 0.6 && this.tow[o.idx] > 0.3; // ...and committing hard
    }

    evalTech(w, kind) {
      const o = this.other(w), i = w.idx, j = o.idx, s = this.sg(w);
      const gd = this.grip[i] - this.grip[j], bd = w.bal - o.bal;
      const oDrive = this.tow[j] > 0.3 ? 1 : 0;
      const toward = -s * this.v; // pair moving toward me = opponent's momentum is mine to use
      const mom = clamp(Math.max(oDrive * 0.6, toward * 0.5), 0, 1);
      const oBrace = o.input.dash.held && o.stam > 0.05;
      const massR = w.m / o.m, tech = w.a.tech;
      let sc = 0, name = kind, ok = false;
      switch (kind) {
        case 'throw':
          sc = 0.45 + gd * 0.1 + bd * 0.3 + mom * 0.42 + (tech - 1) * 0.45 + (massR - 1) * 0.3 - (oBrace ? 0.18 : 0);
          name = this.grip[i] < 1.1 ? 'kotenage' : this.type[i] === 'inside' ? 'shitatenage' : 'uwatenage';
          ok = sc > 0.3; break;
        case 'trip':
          sc = 0.05 + gd * 0.15 + bd * 0.45 + Math.max(oDrive, clamp(Math.abs(toward), 0, 1)) * 0.36 + (Math.abs(this.w) > 0.6 ? 0.15 : 0) + (tech - 1) * 0.6 - (oBrace ? 0.32 : 0) + (massR - 1) * 0.1;
          name = this.type[i] === 'inside' ? 'uchigake' : 'sotogake';
          ok = sc > 0.3; break;
        case 'spin':
          sc = 0.3 + bd * 0.25 + mom * 0.6 + gd * 0.06 + (tech - 1) * 0.3 - Math.max(0, o.m / w.m - 1) * 0.3;
          name = 'katasukashi'; ok = o.m < w.m * 1.7 && w.bal > 0.2; break;
        case 'pull':
          sc = 0.04 + bd * 0.4 + gd * 0.08 + (oDrive ? 0.42 : -0.2) + mom * 0.15 + (tech - 1) * 0.2;
          name = 'hikiotoshi'; ok = sc > 0.3; break;
        case 'utchari': {
          if (!this.utchariOk(w)) return { ok: false, sc: -1, name: 'utchari' };
          sc = -0.2 + gd * 0.12 + (w.bal - 0.55) * 0.7 + clamp(toward - 0.6, 0, 1) * 0.45 + (tech - 1) * 0.35 - (o.m / w.m - 1) * 0.6;
          name = 'utchari'; ok = sc > 0.25; break;
        }
        case 'lift': {
          const can = w.stam > 0.25 && w.bal > 0.4 && w.m * 1.6 >= o.m;
          sc = (can ? 0.4 : 0) + gd * 0.1 - (oBrace ? 0.25 : 0);
          name = 'lift'; ok = can && sc > 0.3; break;
        }
        case 'burst':
          sc = 0.3 + gd * 0.1 + bd * 0.3; name = 'burst'; ok = w.stam > 0.15; break;
      }
      return { ok, sc, name };
    }

    // rotate the opponent around you toward the angle you point at
    swingStep(w, ta, dt) {
      const o = this.other(w), m = this.m;
      if (!this.swing || this.swing.w !== w) this.swing = { w, swept: 0, om: 0, side: 1, t: 0 };
      const Sw = this.swing; Sw.t += dt;
      let cur = Math.atan2(o.z - w.z, o.x - w.x);
      const d = S.wrap(ta - cur);
      let omax = 4.6 * Math.sqrt((w.m * (w.str || 1)) / o.m) * (0.75 + 0.12 * this.grip[w.idx]);
      if (this.tow[o.idx] > 0.3) omax *= 0.6;
      omax *= Math.min(1, 0.3 + Sw.t * 2.0); // the swing builds up: a quick flick is a weak throw, a big one takes time (and can be escaped)
      if (o.fxs.invuln > 0) omax *= 0.2;
      const stp = clamp(d, -omax * dt, omax * dt);
      cur += stp; Sw.swept += Math.abs(stp); Sw.om = stp / dt; if (Math.abs(stp) > 1e-4) Sw.side = Math.sign(stp);
      const r = Math.max(0.9, Math.hypot(o.x - w.x, o.z - w.z));
      const ox = o.x, oz = o.z;
      o.x = w.x + Math.cos(cur) * r; o.z = w.z + Math.sin(cur) * r;
      o.vx = (o.x - ox) / dt; o.vz = (o.z - oz) / dt; w.vx *= 0.5; w.vz *= 0.5;
      w.f = cur; o.f = S.wrap(cur + Math.PI);
      if (Math.abs(stp) > 1e-4) m.hurt(o, dt * 0.05 * Math.abs(Sw.om), -Math.sin(cur) * Sw.side, Math.cos(cur) * Sw.side);
      const edge = Math.hypot(w.x, w.z) > RR - 0.8;
      m.tag(o, w, edge ? 'utchari' : 'swing');
      this.resync();
    }
    releaseSwing() {
      const Sw = this.swing; this.swing = null;
      if (!Sw || Sw.swept < 0.35) return false; // barely moved: treat as a normal release
      const m = this.m, w = Sw.w, o = this.other(w);
      const d = Math.hypot(o.x - w.x, o.z - w.z) || 1, ux = (o.x - w.x) / d, uz = (o.z - w.z) / d;
      const tx = -uz * Sw.side, tz = ux * Sw.side;
      const om = Math.min(6, Math.abs(Sw.om)), sw = Math.min(3.4, Sw.swept);
      const edge = Math.hypot(w.x, w.z) > RR - 0.8;
      const name = edge ? 'utchari' : sw > 2.4 ? 'katasukashi' : this.grip[w.idx] < 1.1 ? 'kotenage' : this.type[w.idx] === 'inside' ? 'shitatenage' : 'uwatenage';
      this.end('throw');
      const bst = 1 + (w.charges || 0) * 0.5; if (w.charges) { m.emit('boost', { w, n: w.charges }); w.charges = 0; }
      const sp = (1.4 + om * 0.9 + sw * 0.6) * bst;
      o.vx = tx * sp + ux * 1.2; o.vz = tz * sp + uz * 1.2;
      m.tag(o, w, name);
      m.hurt(o, (0.12 + sw * 0.17 + om * 0.05) * bst, tx, tz);
      w.set('recover', 0.2);
      if (o.st !== 'fall') { o.set('stumble'); o.sdx = tx; o.sdz = tz; }
      m.emit('throw', { w, o, name, x: o.x, z: o.z, swept: sw });
      return true;
    }
    kindFor(w, tw, sd) {
      const at = Math.abs(sd), ut = this.utchariOk(w);
      if (Math.abs(tw) < 0.35 && at < 0.35) return 'lift';
      if (tw >= 0.35 && at < 0.75) return 'trip';
      if (tw <= -0.35 && at < 0.75) return ut ? 'utchari' : 'spin';
      return ut ? 'utchari' : 'throw';
    }
    inputDir(w) {
      const I = w.input, s = this.sg(w), [nx, nz] = this.axis();
      return [(I.mx * nx + I.mz * nz) * s, (I.mx * -nz + I.mz * nx) * s];
    }
    attempt(w, tw, sd) {
      const at = Math.abs(sd);
      const ut = this.utchariOk(w);
      let kind;
      if (Math.abs(tw) < 0.35 && at < 0.35) kind = 'lift';            // K alone
      else if (tw >= 0.35 && at < 0.75) kind = 'trip';                // toward + K: hook the leg
      else if (tw <= -0.35 && at < 0.75) kind = ut ? 'utchari' : 'spin'; // away + K: spin them past you
      else kind = ut ? 'utchari' : 'throw';                           // sideways + K
      const m = this.m, o = this.other(w), i = w.idx, j = o.idx, s = this.sg(w);
      const [nx, nz] = this.axis();
      const ev = this.evalTech(w, kind);
      if (kind === 'lift') {
        if (ev.ok) {
          this.lift = { w, o, t: 0 }; o.lifted = true;
          m.tag(o, w, 'lift'); w.stam -= 0.1;
          m.emit('lift', { w, o });
        } else {
          const g = 0.42 * w.a.grip * (o.input.dash.held ? 0.6 : 1);
          this.vul[i] = 0.25; void g;
          m.emit('liftFail', { w, heavy: w.m * 1.35 < o.m, x: o.x, z: o.z });
        }
        return;
      }
      if (kind === 'burst') {
        if (w.stam < 0.15) return;
        this.burst[i] = 0.35; w.stam -= 0.2;
        const dmg = 0.1 + (o.bal < 0.38 ? 0.6 : 0) + Math.max(0, this.grip[i] - this.grip[j]) * 0.04;
        m.tag(o, w, 'burst');
        m.hurt(o, dmg, s * nx, s * nz);
        m.emit('burst', { w, o, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2 });
        return;
      }
      const T = this.tech = {
        kind, w, o, t: 0, ok: ev.ok, name: ev.name, side: Math.sign(sd) || 1, sc: ev.sc,
        dur: { throw: 0.42, trip: 0.3, pull: 0.3, utchari: 0.62, spin: 0.5 }[kind],
      };
      T.px = w.x; T.pz = w.z; T.ox = o.x; T.oz = o.z;
      T.a0 = Math.atan2(o.z - w.z, o.x - w.x); T.r0 = Math.hypot(o.x - w.x, o.z - w.z);
      if (ev.ok && kind === 'utchari') m.tag(o, w, 'utchari');
      w.stam = Math.max(0, w.stam - 0.12);
      m.emit('tech', { kind, ok: ev.ok, name: ev.name, w, o, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2 });
    }

    updateTech(dt) {
      const T = this.tech, w = T.w, o = T.o;
      T.t += dt;
      const k = clamp(T.t / T.dur, 0, 1);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const p = [w.x, w.z, o.x, o.z];
      if (T.kind === 'spin') {
        const ang = T.a0 + T.side * Math.PI * e;
        w.x = T.px; w.z = T.pz;
        o.x = w.x + Math.cos(ang) * T.r0; o.z = w.z + Math.sin(ang) * T.r0;
        w.f = ang; o.f = S.wrap(ang + Math.PI);
      } else if (T.kind === 'throw' || T.kind === 'utchari') {
        let ang;
        if (T.ok) ang = T.a0 + T.side * (T.kind === 'utchari' ? Math.PI : 2.5) * e;
        else ang = T.a0 + T.side * 0.5 * Math.sin(Math.PI * k);
        const rr = T.r0 * (T.kind === 'utchari' && T.ok ? 1 + 0.25 * Math.sin(Math.PI * k) : 1);
        w.x = T.px; w.z = T.pz;
        o.x = w.x + Math.cos(ang) * rr; o.z = w.z + Math.sin(ang) * rr;
        w.f = ang; o.f = wrap(ang + Math.PI);
        o.y = T.kind === 'utchari' && T.ok ? 0.55 * Math.sin(Math.PI * k) : T.ok ? 0.18 * Math.sin(Math.PI * k) : 0;
      } else if (T.kind === 'pull') {
        const ux = (T.px - T.ox) / T.r0, uz = (T.pz - T.oz) / T.r0; // o -> w
        w.x = T.px + ux * 0.7 * e; w.z = T.pz + uz * 0.7 * e;
        const oe = (T.ok ? 1.0 : 0.55) * e;
        o.x = T.ox + ux * oe; o.z = T.oz + uz * oe;
      } else { // trip: hold position, hook
        w.x = T.px; w.z = T.pz; o.x = T.ox; o.z = T.oz;
      }
      w.vx = (w.x - p[0]) / dt; w.vz = (w.z - p[1]) / dt;
      o.vx = (o.x - p[2]) / dt; o.vz = (o.z - p[3]) / dt;
      if (k >= 1) this.finishTech();
    }

    finishTech() {
      const T = this.tech, m = this.m, w = T.w, o = T.o, i = w.idx, j = o.idx;
      const d = Math.hypot(o.x - w.x, o.z - w.z) || 1;
      const ux = (o.x - w.x) / d, uz = (o.z - w.z) / d;   // w -> o
      const tx = -uz * T.side, tz = ux * T.side;          // swing tangent
      this.tech = null;
      o.y = 0;
      const fail = () => {
        this.grip[j] = Math.min(3, this.grip[j] + 0.35);
        this.vul[i] = 0.42;
        this.resync();
        m.emit('techFail', { w, o, kind: T.kind });
      };
      switch (T.kind) {
        case 'spin':
          if (T.ok) { // they were leaning on you: they fly past and go down
            this.end('spin');
            const fl = 2.4 + Math.max(0, T.sc) * 2.2;
            o.vx = tx * fl - ux * 0.5; o.vz = tz * fl - uz * 0.5;
            m.tag(o, w, 'katasukashi');
            m.hurt(o, 0.3 + Math.max(0, T.sc) * 0.6, tx, tz);
            w.set('recover', 0.2);
            if (o.st !== 'fall') { o.set('stumble'); o.sdx = tx; o.sdz = tz; }
            m.emit('throw', { w, o, name: 'katasukashi', x: o.x, z: o.z });
          } else { // too heavy, or you were falling yourself: you just swap places
            this.resync(); this.vul[i] = 0.25;
            m.emit('swap', { w, o, x: (w.x + o.x) / 2, z: (w.z + o.z) / 2 });
          }
          break;
        case 'throw':
          if (T.ok) {
            this.end('throw');
            const fl = (T.fling || 1) * (1 + (w.charges || 0) * 0.5); if (w.charges) { m.emit('boost', { w, n: w.charges }); w.charges = 0; }
            o.vx = (tx * 3.6 + ux * 1.6) * fl; o.vz = (tz * 3.6 + uz * 1.6) * fl;
            m.tag(o, w, T.name);
            m.hurt(o, 0.35 + T.sc * 0.6, tx, tz);
            w.set('recover', 0.25);
            if (o.st !== 'fall') { o.set('stumble'); o.sdx = tx; o.sdz = tz; }
            m.emit('throw', { w, o, name: T.name, x: o.x, z: o.z });
          } else { m.hurt(w, 0.22, -ux, -uz, true); fail(); }
          break;
        case 'trip':
          if (T.ok) {
            this.end('trip');
            o.vx = ux * 1.4; o.vz = uz * 1.4;
            m.tag(o, w, T.name);
            m.hurt(o, 0.45 + T.sc * 0.5, ux, uz);
            w.set('recover', 0.2);
            m.emit('throw', { w, o, name: T.name, x: o.x, z: o.z });
          } else { m.hurt(w, 0.28, ux, uz, true); fail(); }
          break;
        case 'pull':
          if (T.ok) {
            this.end('pull');
            o.vx = -ux * 3.2; o.vz = -uz * 3.2;
            w.vx = tx * 3; w.vz = tz * 3; w.ghostT = 0.35;
            m.tag(o, w, 'hikiotoshi');
            m.hurt(o, 0.3 + T.sc * 0.5, -ux, -uz);
            w.set('recover', 0.2);
            m.emit('throw', { w, o, name: 'hikiotoshi', x: o.x, z: o.z });
          } else fail();
          break;
        case 'utchari':
          if (T.ok) {
            this.end('utchari');
            const od = Math.hypot(o.x, o.z) || 1;
            o.vx = o.x / od * 2.5; o.vz = o.z / od * 2.5;
            m.hurt(o, 0.3, o.vx, o.vz);
            w.set('recover', 0.3);
            m.emit('throw', { w, o, name: 'utchari', x: o.x, z: o.z });
          } else {
            this.end('utchariFail');
            w.vx = -ux * 3; w.vz = -uz * 3;
            m.tag(w, o, 'drive');
            m.hurt(w, 0.55, -ux, -uz);
            if (o.st === 'recover') o.dur = 0.2;
          }
          break;
      }
    }

    setDown(slam) {
      const L = this.lift; this.lift = null;
      L.o.lifted = false;
      const s = this.sg(L.w);
      const [nx, nz] = this.axis();
      if (slam) {
        this.m.tag(L.o, L.w, 'lift');
        this.m.hurt(L.o, (0.35 + (1 - L.o.bal) * 0.5) * (0.45 + 0.55 * Math.max(0, Math.min(1, L.w.stam))), s * nx, s * nz); // a tired lifter slams softly
        this.m.emit('slam', { w: L.w, o: L.o, x: L.o.x, z: L.o.z });
        // slammed down: you let go, they bounce off you dazed
        this.end('slam');
        const dx = L.o.x - L.w.x, dz = L.o.z - L.w.z, d = Math.hypot(dx, dz) || 1;
        L.o.vx += dx / d * 2.2; L.o.vz += dz / d * 2.2;
        if (L.o.st !== 'fall') L.o.set('stun', 0.5);
        L.o.fxs.dizzy = Math.max(L.o.fxs.dizzy || 0, 0.5);
        L.w.set('recover', 0.2);
        return;
      } else this.m.hurt(L.o, 0.12, s * nx, s * nz);
      L.w.stam = Math.max(0, L.w.stam - 0.1);
      if (!slam) this.m.emit('liftEnd', { w: L.w, o: L.o });
    }

    rearShove(w) {
      const o = this.other(w), s = this.sg(w);
      const [nx, nz] = this.axis();
      this.end('rearShove');
      const imp = 6.5 * w.a.power;
      o.vx += s * nx * imp / o.m; o.vz += s * nz * imp / o.m;
      o.slideT = 0.35;
      this.m.tag(o, w, 'rear');
      this.m.hurt(o, 0.3, s * nx, s * nz);
      w.set('recover', 0.2);
      this.m.emit('hit', { kind: 'heavy', x: o.x, z: o.z, nx: s * nx, nz: s * nz, power: imp, zone: 'rear', w, o, big: true });
    }

    tryBreak(w) {
      const o = this.other(w), i = w.idx, j = o.idx, s = this.sg(w);
      if (o === this.a) o.gripCD = 0.5; // shoved out of their grip: they can't just grab straight back
      const [nx, nz] = this.axis();
      {
        this.end('break');
        const esc = o === this.a; // shoving out of THEIR grip: it frees you, it is not an attack
        const imp = 4.6 * w.a.power * (this.grip[i] >= this.grip[j] - 0.35 || o.bal < 0.45 ? 1 : 0.65) * (esc ? 0.55 : 1);
        if (esc) w.stam = Math.max(0, w.stam - 0.12);
        o.vx += s * nx * imp / o.m; o.vz += s * nz * imp / o.m;
        w.vx -= s * nx * imp * 0.25 / w.m; w.vz -= s * nz * imp * 0.25 / w.m;
        o.slideT = 0.2;
        this.m.tag(o, w, 'break');
        this.m.hurt(o, esc ? 0.03 : 0.1, s * nx, s * nz);
        w.set('recover', esc ? 0.2 : 0.16); o.set('recover', esc ? 0.14 : 0.2);
        this.m.emit('hit', { kind: 'palm', x: (w.x + o.x) / 2, z: (w.z + o.z) / 2, nx: s * nx, nz: s * nz, power: imp, zone: 'front', w, o });
      }
      void i; void j;
    }

    tryDisengage(w) {
      const o = this.other(w), i = w.idx, j = o.idx, s = this.sg(w);
      if (o === this.a) o.gripCD = 0.5;
      const [nx, nz] = this.axis();
      {
        const oWasDriving = this.tow[j] > 0.3;
        this.end('disengage');
        w.vx = -s * nx * 5; w.vz = -s * nz * 5;
        w.set('recover', 0.15);
        if (oWasDriving) {
          this.m.tag(o, w, 'pull');
          this.m.hurt(o, 0.3, -s * nx, -s * nz);
          o.vx += -s * nx * 2.2; o.vz += -s * nz * 2.2;
          if (o.st !== 'fall') { o.set('stumble'); o.sdx = -s * nx; o.sdz = -s * nz; }
        }
        this.m.emit('disengage', { w });
      }
      void i;
    }

    separate() {
      const A = this.a, B = this.b;
      const [nx, nz] = this.axis();
      this.end('separate');
      A.vx = -nx * 2.2; A.vz = -nz * 2.2; B.vx = nx * 2.2; B.vz = nz * 2.2;
      for (const w of [A, B]) { // never shove anyone out of the ring when breaking up
        const dc = Math.hypot(w.x, w.z);
        if (dc > RR - 1.4 && (w.vx * w.x + w.vz * w.z) > 0) { w.vx = -w.x / dc * 1.5; w.vz = -w.z / dc * 1.5; }
        w.tag = null; w.lastTech = null; w.lastBy = null;
      }
      this.m.emit('separate', {});
    }

    end(reason) {
      if (this.done) return;
      this.done = true; this.swing = null;
      for (const w of [this.a, this.b]) {
        w.clinch = null; w.lifted = false;
        if (w.st === 'clinch') w.set('recover', 0.12);
      }
      if (this.m.clinch === this) this.m.clinch = null;
      this.m.emit('clinchEnd', { reason });
    }
  }
  S.Clinch = Clinch;
})();
