'use strict';
// CPU opponent. Acts as an input source (presses the same three buttons as a human).
// It perceives the opponent with a reaction delay and decides on a fixed think rhythm.
(function () {
  const RR = S.RING_R;
  const clamp = S.clamp;
  const LEVELS = {
    easy:   { react: 0.30, think: 0.16, skill: 0.45, dodge: 0.25, tricky: 0.08, aggr: 0.45 },
    normal: { react: 0.19, think: 0.10, skill: 0.72, dodge: 0.45, tricky: 0.18, aggr: 0.6 },
    hard:   { react: 0.12, think: 0.06, skill: 0.94, dodge: 0.6, tricky: 0.28, aggr: 0.72 },
    boss:   { react: 0.5, think: 0.26, skill: 0.225, escP: 0.5, parryP: 0.5, dodge: 0.08, tricky: 0, aggr: 0.36 },   // the bathhouse owner: a patient old champion, for casual players (and he goes easier after each round you lose)
  };
  // remembers how the human opens, across rounds and matches
  const MEM = { charge: 1, brace: 0.6, henka: 0.4, wait: 0.6 };
  // remembers what the human leans on mid-bout, so it can stop falling for it
  const HAB = { flurry: 0.3, slap: 0.3, grab: 0.3, dodge: 0.3, charge: 0.3, poke: 0.3 };

  class AI {
    constructor(me, match, level, opts) {
      this.me = me; this.m = match; this.L = LEVELS[level] || LEVELS.normal;
      this.learn = !(opts && opts.noLearn);
      this.mx = 0; this.mz = 0;
      this.btn = { push: { until: 0, next: 0 }, grab: { until: 0, next: 0 }, dash: { until: 0, next: 0 }, skill: { until: 0, next: 0 } };
      this.time = 0; this.thinkT = 0; this.hist = []; this.state = 'idle';
      this.open = null; this.mode = null; this.modeT = 0; this.recorded = false; this.clT = 0;
      this.round = -1;
    }
    sample() {
      const T = this.time, b = this.btn;
      // I am the chicken: no attacking, just run. Keep away from them and stay off the edge.
      const me = this.me, o = me.opp;
      if (me.fxs.chicken > 0 && o) {
        let ax = me.x - o.x, az = me.z - o.z; const al = Math.hypot(ax, az) || 1; ax /= al; az /= al;
        const rl = Math.hypot(me.x, me.z), edge = Math.max(0, (rl - 2.2) / 2.4); // 0 in the middle, 1 at the rim
        let mx = ax * (1 - edge) - (me.x / (rl || 1)) * edge * 1.4 + Math.cos(T * 2.1) * 0.35 * (1 - edge);
        let mz = az * (1 - edge) - (me.z / (rl || 1)) * edge * 1.4 + Math.sin(T * 2.1) * 0.35 * (1 - edge);
        const ml = Math.hypot(mx, mz) || 1;
        return { mx: mx / ml, mz: mz / ml, push: false, grab: false, dash: false, skill: false };
      }
      const k = this.slow || 1;
      return { mx: this.mx * k, mz: this.mz * k, push: T < b.push.until, grab: T < b.grab.until, dash: T < b.dash.until, skill: T < b.skill.until };
    }
    tap(n, dur) {
      const b = this.btn[n];
      if (this.time < b.next) return false;
      b.until = this.time + (dur || 0.05); b.next = b.until + 0.04;
      return true;
    }
    hold(n, dur) {
      const b = this.btn[n];
      if (this.time < b.until) { b.until = Math.max(b.until, this.time + dur); b.next = b.until + 0.04; return true; }
      return this.tap(n, dur);
    }
    holding(n) { return this.time < this.btn[n].until; }
    release(n) { const b = this.btn[n]; if (this.time < b.until) { b.until = this.time; b.next = this.time + 0.04; } }
    dir(x, z) { const l = Math.hypot(x, z); if (l < 1e-4) { this.mx = this.mz = 0; return; } this.mx = x / l; this.mz = z / l; }
    rnd() { return Math.random(); }

    step(dt) {
      this.time += dt;
      const o = this.me.opp, m = this.m;
      if (m.round !== this.round) {
        this.round = m.round; this.open = null; this.mode = null; this.recorded = false; this.dir(0, 0); this.aimHold = null; this.fakeStop = null;
        if (this.learn) for (const k in HAB) HAB[k] = Math.min(4, HAB[k] * 0.85);
      }
      if (this.learn && m.phase === 'fight') this.watch(o, m);
      if (!(o.fxs && o.fxs.invis > 0) || !this.hist.length) this.hist.push({ st: o.st, t: o.t, x: o.x, z: o.z, vx: o.vx, vz: o.vz, bal: o.bal, fwd: o.fwdIn, contact: o.contact, braceT: o.braceT, pressT: o.pressT, flurry: o.flurry || 0 });
      if (this.hist.length > 90) this.hist.shift();
      // the other one has vanished: he can't see where they went, so he stands there looking about (a question mark now and then), nothing else
      if (o.fxs && o.fxs.invis > 0 && m.phase === 'fight' && !this.me.clinch) {
        this.confT = (this.confT || 0) + dt; if (this.confT > 0.9 || this.lostO !== true) { this.confT = 0; this.m.emit('confused', { w: this.me }); }
        this.lostO = true; this.dir(Math.cos(this.time * 1.9) * 0.4, Math.sin(this.time * 1.4) * 0.4); this.state = 'confused'; return;
      } else this.lostO = false;
      // learn the human's opening habit
      if (this.learn && m.phase === 'fight' && !this.recorded && m.sinceGo > 0.6) {
        this.recorded = true;
        const k = o.tachiai ? 'charge' : (o.st === 'brace' || o.braceT < 0.7) ? 'brace' : (o.dashCD > -0.2) ? 'henka' : 'wait';
        for (const key in MEM) MEM[key] *= 0.85;
        MEM[k] += 1;
      }
      this.modeT += dt;
      this.thinkT -= dt;
      if (m.phase === 'fight' && S.Skills && S.Skills.aiWant(m, this.me)) this.tap('skill', 0.05);
      if (this.thinkT <= 0) {
        this.thinkT = this.L.think * (0.75 + this.rnd() * 0.5);
        const fogged = this.me.fxs && this.me.fxs.dark > 0 && this.rnd() < 0.45; // can't see properly: guesses
        if (this.me.fxs && (this.me.fxs.blind > 0 || fogged) && m.phase === 'fight') { this.dir(this.rnd() - 0.5, this.rnd() - 0.5); this.state = 'blind'; }
        else this.decide();
      }
    }
    // notice the human's habits as they happen
    watch(o, m) {
      const prev = this.lastOSt; this.lastOSt = o.st;
      if (o.st === prev) return;
      const me = this.me;
      if (o.st === 'slap') HAB.slap += 0.5;
      else if (o.st === 'dash' && (me.st === 'charge' || me.spd > me.a.maxSpeed * 0.6)) HAB.dodge += 0.5;
      else if (o.st === 'charge') HAB.charge += 0.3;
      else if (o.st === 'palm' && (o.flurry || 0) === 4) HAB.flurry += 0.6;
      else if (o.st === 'palm' && (o.flurry || 0) === 1) HAB.poke += 0.15;
      else if (o.st === 'clinch' && m.clinch && m.clinch.a === o) HAB.grab += 0.5;
    }
    perceive() {
      const k = Math.min(this.hist.length - 1, Math.round(this.L.react / S.DT));
      return this.hist[this.hist.length - 1 - k];
    }

    // ----------------------------------------------------------------- decide
    decide() {
      const m = this.m, me = this.me;
      if (m.phase === 'shikiri') {
        this.dir(0, 0);
        if (!this.open) this.planOpening();
        const Op = this.open, t = m.phaseT;
        if (Op.kind === 'charge' && t > 1.55) this.hold('dash', 0.25); // fists down
        if (!Op.taunt && t > 0.9 && t < 1.2) { Op.taunt = true; if (this.rnd() < 0.45) { const d = [[0, -1], [-1, 0], [0, 1], [1, 0]][(this.rnd() * 4) | 0]; this.dir(d[0], d[1]); } }
        if (!Op.pre && t > 1.25 && t < 1.5) { Op.pre = true; if (t < 1.35 && this.rnd() < 0.35) this.tap('grab', 0.05); else if (this.rnd() < 0.5) this.tap('push', 0.05); }
        this.state = 'shikiri:' + Op.kind; return;
      }
      if (m.phase !== 'fight') { this.dir(0, 0); this.state = 'idle'; return; }
      if (me.clinch) { if (this.clT === 0) { this.techTried = false; } if (this.clT === 0) this.nextTech = 0.5 + this.rnd() * 1.2; this.clT += this.L.think; this.decideClinch(); return; }
      this.clT = 0; this.aimHold = null; this.armT = 0;
      if (this.open && !this.open.done && this.execOpening()) return;
      this.decideFree();
    }

    planOpening() {
      const L = this.L, tot = MEM.charge + MEM.brace + MEM.henka + MEM.wait;
      const pc = MEM.charge / tot, ph = MEM.henka / tot, pb = MEM.brace / tot, pw = MEM.wait / tot;
      const w = { charge: 0.45, brace: 0.15, henka: 0.1, delay: 0.15, walk: 0.15 };
      if (pc > 0.45) { w.brace += 0.3 * L.skill; w.henka += 0.15 * L.skill; w.charge -= 0.15; }
      if (ph > 0.25) { w.delay += 0.3; w.walk += 0.2; w.henka = 0.02; }
      if (pb > 0.35) { w.walk += 0.35; w.charge -= 0.15; }
      if (pw > 0.35) w.charge += 0.3;
      // hard: sometimes jump at the call and stop dead, to draw out a sidestep or a slap
      w.fake = L.tricky > 0.25 ? 0.12 + 0.3 * ph + 0.1 * Math.min(2, HAB.slap + HAB.dodge) : 0;
      let r = this.rnd() * Object.values(w).reduce((a, b) => a + Math.max(0, b), 0), kind = 'charge';
      for (const k in w) { r -= Math.max(0, w[k]); if (r <= 0) { kind = k; break; } }
      this.open = { kind, done: false, side: this.rnd() < 0.5 ? 1 : -1, delay: 0.1 + this.rnd() * 0.12, power: this.rnd() < 0.5 };
    }

    execOpening() {
      const m = this.m, me = this.me, o = me.opp, t = m.sinceGo, Op = this.open;
      if (t < this.L.react * 0.7) { this.dir(0, 0); return true; }
      const nx = o.x - me.x, nz = o.z - me.z;
      this.state = 'open:' + Op.kind;
      switch (Op.kind) {
        case 'charge': this.dir(nx, nz); this.tap('push'); Op.done = true; return true;
        case 'brace': this.dir(0, 0); this.hold('dash', 0.4); Op.done = true; return true;
        case 'henka': this.dir(-nz * Op.side + -nx * 0.2, nx * Op.side - nz * 0.2); this.tap('dash'); Op.done = true; return true;
        case 'delay':
          if (t < this.L.react * 0.7 + Op.delay) { this.dir(0, 0); return true; }
          this.dir(nx, nz); this.tap('push'); Op.done = true; return true;
        case 'walk':
          if (t > 1.0 || me.contact) { Op.done = true; return false; }
          this.dir(nx, nz); return true;
        case 'fake':
          if (t < this.L.react * 0.7 + 0.2) { this.dir(nx, nz); return true; }
          Op.done = true; this.mode = 'fake'; this.modeT = 0; this.fakeStop = this.time; this.fakeOpen = true; return false;
      }
      Op.done = true; return false;
    }

    // steer: toward the opponent while working my way to the centre side
    steer(nx, nz, fwdW, tanW) {
      const me = this.me;
      const tx = -nz, tz = nx;
      const cx = -me.x, cz = -me.z, cl = Math.hypot(cx, cz) || 1;
      const sign = (tx * cx + tz * cz) >= 0 ? 1 : -1;
      const myEdge = RR - Math.hypot(me.x, me.z);
      const inW = clamp((1.6 - myEdge) / 1.6, 0, 1) * 1.2;
      this.dir(nx * fwdW + tx * sign * tanW + cx / cl * inW, nz * fwdW + tz * sign * tanW + cz / cl * inW);
    }

    decideFree() {
      const m = this.m, me = this.me, o = me.opp, L = this.L, P = this.perceive();
      if (!P) return;
      const dx = P.x - me.x, dz = P.z - me.z, dist = Math.hypot(dx, dz) || 1e-3;
      const nx = dx / dist, nz = dz / dist;
      const gap = dist - me.r - o.r;
      const myEdge = RR - Math.hypot(me.x, me.z), oEdge = RR - Math.hypot(P.x, P.z);
      const oSpeedToMe = -(P.vx * nx + P.vz * nz);
      const canAct = ['free', 'brace', 'recover', 'palm'].includes(me.st);
      const mySp = me.spd, ms = me.a.maxSpeed;
      this.slow = 1;
      // they are on the rim: no lunging, creep in so a sidestep can't send me flying out
      const rimCareful = oEdge < 1.7 && myEdge > oEdge && L.skill * (0.6 + 0.3 * Math.min(2, HAB.dodge)) > 0.45;
      // they keep grabbing: running into them just hands them a catch
      const grabWary = L.skill * Math.min(2, HAB.grab) > 0.7;

      if (me.st === 'teeter') { // win the balance back: lean in toward the middle (the weaker ones flail)
        if (this.rnd() < 0.45 + 0.55 * L.skill) this.dir(-me.x, -me.z); else this.dir(this.rnd() - 0.5, this.rnd() - 0.5);
        this.state = 'teeter'; return;
      }
      if (me.st === 'stumble' || me.st === 'overrun' || (me.st === 'recover' && RR - Math.hypot(me.x, me.z) < 1.2)) { this.steer(nx, nz, 0, 0); this.state = 'recovering'; return; }

      // 1. threats: incoming charge / heavy
      const oCharging = P.st === 'charge' || (P.st === 'heavy' && P.t < 0.17) || (oSpeedToMe > 3.4 && P.st !== 'dash');
      if (oCharging && gap < Math.max(0.45, oSpeedToMe * 0.32) && canAct) {
        if (gap < 0.9 && canAct && this.rnd() < L.skill * 0.3) { this.dir(nx, nz); this.tap('grab', 0.05); this.state = 'catch'; return; }
        // the classic answer to a charge: step back and slap them down with their own speed
        if (P.st === 'charge' && gap < 1.1 && myEdge > 1.4 && this.rnd() < L.tricky * (0.8 + 0.5 * Math.min(2, HAB.charge))) { this.dir(-nx, -nz); this.tap('push'); this.state = 'slapdown-charge'; return; }
        const preferDodge = myEdge < 1.8 || this.rnd() < L.dodge;
        if (preferDodge && me.dashCD <= 0) {
          let lx = -P.vz, lz = P.vx; const ll = Math.hypot(lx, lz) || 1; lx /= ll; lz /= ll;
          if (lx * -me.x + lz * -me.z < 0) { lx = -lx; lz = -lz; }
          this.release('dash'); this.dir(lx, lz); this.tap('dash', 0.05); this.state = 'dodge'; return;
        }
        this.dir(0, 0); this.hold('dash', 0.35); this.state = 'brace'; return;
      }
      if (me.st === 'brace' && this.holding('dash')) { this.dir(0, 0); this.state = 'bracing'; return; }

      // a dash straight at me is not a charge: stand my ground (they bump and stall), then punish
      if (P.st === 'dash' && oSpeedToMe > 2 && gap < 1.4 && canAct && myEdge > 1.5) { this.dir(0, 0); this.state = 'hold-ground'; return; }
      // 2. punish an opponent who is stuck in recovery / off balance
      const oVuln = ['recover', 'stun', 'overrun', 'stumble'].includes(P.st) || (P.st === 'heavy' && P.t > 0.2) || (P.st === 'grab' && P.t > 0.12) || (P.st === 'slap' && P.t > 0.24);
      if (oVuln && gap < 1.4 && canAct) {
        const behind = (o.fx * -nx + o.fz * -nz) < -0.2;
        this.dir(nx, nz);
        if (gap < 0.45) {
          // a long opening is worth more than a single hand: take the belt (unless they love grabbing)
          const longOpen = (o.st === 'recover' || o.st === 'stun' || o.st === 'overrun') && o.dur - o.t > 0.22; // only grab into a long opening; a hand beats a grab otherwise
          if (behind || P.bal < 0.3) this.tap('push');
          else if (longOpen && !(o.gripCD > 0) && this.rnd() < 0.65 - 0.15 * Math.min(2, HAB.grab)) this.tap('grab');
          else if (P.bal < 0.45 || this.rnd() < 0.5) this.tap('push'); else this.tap('grab');
        }
        this.state = 'punish'; return;
      }
      // interrupt a heavy windup
      if (P.st === 'wind' && gap < 0.7 && canAct) { this.dir(nx, nz); this.tap('push'); this.state = 'interrupt'; return; }

      // a planted fake charge: hold still, braced, and see what they do
      if (this.mode === 'fake' && this.fakeStop) {
        const held = this.time - this.fakeStop;
        if (held < 0.4) { this.dir(0, 0); this.hold('dash', 0.08); this.state = 'fake-plant'; return; }
        this.release('dash'); this.mode = null; this.fakeStop = null;
        // nothing happened and the opening charge is still live: now really go
        if (this.fakeOpen && m.sinceGo < 0.8 && this.rnd() < 0.6) { this.fakeOpen = false; this.dir(nx, nz); this.tap('push'); this.state = 'stutter-charge'; return; }
        this.fakeOpen = false;
      }

      // 3. close range
      if (gap < 0.6 && P.st === 'palm' && P.flurry >= 2 && canAct) {
        // they are flurrying: parry it, slap them down with their own lean, or step off the line
        const r = this.rnd(), ad = L.skill * Math.min(1, 0.45 + 0.2 * HAB.flurry);
        if (L.parryP !== undefined) {   // (a set share of flurries get parried: one roll per flurry, not one per tick)
          if (this.time - (this.parryT === undefined ? -9 : this.parryT) > 1.2) this.parryGo = this.rnd() < L.parryP;
          this.parryT = this.time; if (this.parryGo) { this.dir(0, 0); this.tap('dash', 0.04); this.state = 'parry'; return; }
        } else if (r < ad * 0.3) { this.dir(0, 0); this.tap('dash', 0.04); this.state = 'parry'; return; }
        if (r < ad * 0.65 && myEdge > 1.3) { this.dir(-nx, -nz); this.tap('push'); this.state = 'slapdown-flurry'; return; }
        if (r < ad && me.dashCD <= 0) { let lx = -nz, lz = nx; if (lx * -me.x + lz * -me.z < 0) { lx = -lx; lz = -lz; } this.dir(lx, lz); this.tap('dash'); this.state = 'sidestep-flurry'; return; }
      }
      // poke range (a hand reaches a bit further than a grab): don't walk into their hand, use yours
      if (this.mode === 'bait') {
        if (this.modeT < 0.25) { this.dir(-nx, -nz); this.state = 'bait-step'; return; }
        this.mode = null;
        if ((P.st === 'palm' && P.t > 0.1) || P.st === 'recover') { this.dir(nx, nz); this.tap(gap < 0.45 ? 'grab' : 'push'); this.state = 'whiff-punish'; return; }
      }
      if (gap >= 0.45 && gap < 0.62 && canAct && L.tricky > 0.25 && myEdge > 2 && HAB.poke > HAB.flurry + 0.5 && this.time > (this.baitCD || 0) && this.rnd() < L.tricky) {
        this.baitCD = this.time + 2.5; this.mode = 'bait'; this.modeT = 0; this.dir(-nx, -nz); this.state = 'bait-step'; return; // step out of their reach to make them whiff
      }
      if (gap >= 0.45 && gap < 0.62 && canAct && P.st !== 'brace' && this.rnd() < 0.35 + 0.5 * L.aggr) {
        this.dir(nx, nz); this.tap('push'); this.state = 'poke'; return;
      }
      if (gap < 0.45) {
        if (!canAct) { this.dir(nx, nz); return; }
        if (P.st === 'brace' && P.braceT > 0.05) { this.dir(nx, nz); this.tap('grab'); this.state = 'grab-vs-brace'; return; }
        if (P.bal < 0.42) { this.dir(nx, nz); this.hold('push', 0.42); this.state = 'heavy'; return; }
        if (myEdge < 1.0 && P.fwd > 0.4 && me.dashCD <= 0) { // escape the edge sideways
          let lx = -nz, lz = nx; if (lx * -me.x + lz * -me.z < 0) { lx = -lx; lz = -lz; }
          this.dir(lx, lz); this.tap('dash'); this.state = 'edge-escape'; return;
        }
        if (P.contact && P.fwd > 0.5 && P.pressT > 0.15 && myEdge > 1.6 && this.rnd() < L.tricky * (1 + 0.4 * Math.min(2, HAB.charge + HAB.flurry))) {
          this.dir(-nx, -nz); this.tap('push'); this.state = 'slapdown'; return;
        }
        if ((rimCareful || grabWary) && mySp > ms * 0.4) { this.dir(nx, nz); this.slow = 0.2; this.state = 'brake'; return; }
        const a = me.a;
        const wGrab = a.grip * a.tech * 0.55 + (oEdge < 1.5 ? 0.25 + 0.3 * L.skill * Math.min(2, HAB.dodge) : 0) + (a.key === 'heavy' ? 0.25 : 0);
        const wPalm = a.power * 0.6 + (a.key === 'fast' ? 0.25 : 0) + 0.3 * L.skill * Math.min(2, HAB.grab); // they love the belt: keep them off it
        this.dir(nx, nz);
        if (this.rnd() < wGrab / (wGrab + wPalm)) { this.tap('grab'); this.state = 'grab'; }
        else { this.tap('push'); this.state = 'tsuppari'; }
        return;
      }

      // 4a. fake run-up: sprint in, plant before they can slap
      if (this.mode === 'fake' && !this.fakeStop) {
        if (this.modeT > 1.2) this.mode = null;
        else { this.dir(nx, nz); if (gap < 1.5) { this.fakeStop = this.time; this.dir(0, 0); this.hold('dash', 0.1); } this.state = 'fake-run'; return; }
      }
      // 4. charge run-up in progress
      if (this.mode === 'charge') {
        if (this.modeT > 1.2 || gap > 3.4 || rimCareful || grabWary) this.mode = null;
        else {
          this.dir(nx, nz);
          const vf = me.vx * me.fx + me.vz * me.fz;
          if (vf > ms * 0.58 && gap < 1.6 && canAct) { this.tap('push'); this.mode = null; }
          this.state = 'charging'; return;
        }
      }

      // hard: back on the rope, stand and invite the lunge (the threat branch pivots away when it comes)
      if (L.tricky > 0.25 && myEdge < 1.3 && gap > 0.62 && gap < 2.2 && oSpeedToMe > 0.8 && HAB.charge + HAB.dodge > 1.2 && this.rnd() < 0.55) { this.dir(0, 0); this.state = 'rim-bait'; return; }
      // 5. mid range
      const quiet = m.time - m.lastContactT;
      if (gap < 2.6) {
        const aligned = (me.fx * nx + me.fz * nz) > 0.85;
        // charging at someone on the bales is how you get sidestepped out: only the reckless do it
        const lineOut = oEdge < 1.25 + 0.35 * L.skill * Math.min(2, HAB.dodge) && this.rnd() > (1 - L.skill) * 0.5;
        const wantCharge = !lineOut && ((oEdge < 1.8 && myEdge > oEdge + 0.4) || quiet > 2.2 || this.rnd() < L.aggr * 0.15);
        if (wantCharge && aligned && gap > 0.8 && myEdge > 1.2 && P.st !== 'brace' && !(grabWary && this.rnd() < 0.8)) {
          // hard: against someone who slaps down or sidesteps charges, run in and stop dead instead
          const fakeP = L.tricky > 0.25 ? L.tricky * (0.5 + 0.5 * Math.min(3, HAB.slap + HAB.dodge)) : 0;
          if (gap > 1.6 && this.rnd() < fakeP) { this.mode = 'fake'; this.modeT = 0; this.fakeStop = null; this.fakeOpen = false; this.dir(nx, nz); this.state = 'fake-run'; return; }
          // a known slap-downer gets fewer straight charges
          if (this.rnd() < L.skill * 0.25 * Math.min(2, HAB.slap)) { this.steer(nx, nz, 0.5, 0.5); this.state = 'wary'; return; }
          this.mode = 'charge'; this.modeT = 0; this.dir(nx, nz); this.state = 'start-charge'; return;
        }
        this.steer(nx, nz, 0.75 / (1 + 0.25 * L.skill * Math.min(3, HAB.slap)), 0.45);
        if (rimCareful && gap < 1.8) { this.slow = 0.45; this.state = 'creep'; return; }
        this.state = 'approach'; return;
      }
      this.steer(nx, nz, 1, 0.25); this.state = 'close-in';
      void mySp;
    }

    // relative direction inside a clinch: tw toward opponent, sd lateral in my frame
    rel(c, tw, sd) {
      const me = this.me, s = c.sg(me);
      const [nx, nz] = c.axis();
      const px = -nz, pz = nx;
      this.dir(s * nx * tw + s * px * sd, s * nz * tw + s * pz * sd);
    }

    decideClinch() {
      const c = this.m.clinch, me = this.me, o = me.opp, L = this.L;
      if (!c) return;
      this.release('dash'); this.slow = 1;
      const i = me.idx, j = o.idx, s = c.sg(me);
      const [nx, nz] = c.axis();
      // winding up my own throw: keep K held and keep pointing until it goes
      if (this.aimHold && !c.tech && !c.lift) {
        const A = this.aimHold;
        if (A.alt && this.time > A.switchAt) { A.mx = A.alt[0]; A.mz = A.alt[1]; A.alt = null; this.state = 'windup-switch'; }
        if (this.time < A.until) { this.mx = A.mx; this.mz = A.mz; if (this.state !== 'windup-switch') this.state = 'windup'; return; }
        this.aimHold = null;
      }
      // just been grabbed: counter-grab
      if (c.b === me && c.t < 0.3 && !c.rear && !this.techTried) { this.techTried = true; if (this.rnd() < L.skill * (0.35 + 0.1 * Math.min(2, HAB.grab))) { this.tap('grab', 0.04); this.state = 'grab-break'; return; } }
      if (c.tech) {
        // their throw has only just started: slip it
        if (c.tech.o === me && c.tech.t < 0.2 && this.escFor !== c.tech) { this.escFor = c.tech; if (this.rnd() < (L.escP !== undefined ? L.escP : L.skill * 0.35)) { this.escape(c); return; } }
        this.dir(0, 0); this.state = 'tech'; return;
      }
      // they are winding up (K held and aiming) or already swinging me: get out
      const oArmed = (o.kArm && o.input && o.input.grab && o.input.grab.held) || (c.swing && c.swing.w === o);
      this.armT = oArmed ? (this.armT || 0) + this.L.think : 0;
      const danger = RR - Math.hypot(me.x, me.z) < 1.6 ? 0.1 : 0;
      if (oArmed && this.armT > L.react && this.rnd() < L.skill * (0.11 + danger + 0.05 * Math.min(2, HAB.grab))) { this.escape(c); return; }
      if (c.lift) {
        if (c.lift.w === me) { const ol = Math.hypot(o.x, o.z) || 1; this.dir(o.x / ol, o.z / ol); this.state = 'carry'; }
        else {
          // lifted: wriggle like a human mashing. Better players mash harder.
          this.dir(this.rnd() - 0.5, this.rnd() - 0.5);
          this.wrig = ((this.wrig || 0) + 1) % 3;
          if (this.rnd() < 0.35 + 0.6 * L.skill) this.tap(['push', 'grab', 'dash'][this.wrig], 0.03);
          this.state = 'struggle';
        }
        return;
      }
      const myD = Math.hypot(me.x, me.z) || 1, oD = Math.hypot(o.x, o.z) || 1;
      const myEdge = RR - myD, oEdge = RR - oD;
      const myBack = (me.x / myD) * -s * nx + (me.z / myD) * -s * nz;
      const oBack = (o.x / oD) * s * nx + (o.z / oD) * s * nz;
      if (c.rear === me) { this.rel(c, 1, 0); if (oEdge < 1.6 || this.rnd() < 0.25) this.tap('push'); this.state = 'rear'; return; }
      if (c.rear === o) { this.rel(c, 0, 1); this.state = 'turning'; return; }

      // being driven back toward my edge: use their drive against them, or get off the line
      const drivenBack = c.tow[j] > 0.3 || -s * c.v > 0.3;
      if (drivenBack && myEdge < 1.6 && myBack > 0.2 && !c.utchariOk(me) && this.rnd() < 0.2 + 0.35 * L.skill) {
        const sp = c.evalTech(me, 'spin'), th = c.evalTech(me, 'throw');
        const best = sp.ok && sp.sc > 0.55 && sp.sc >= th.sc ? 'spin' : th.ok && th.sc > 0.55 ? 'throw' : null;
        if (best) {
          const side = this.bestSide(c);
          if (best === 'spin') this.rel(c, -1, 0); else this.rel(c, 0, side);
          const wind = 0.12 + 0.1 * (1 - L.skill); // no time for a long wind-up with your heels on the straw
          this.hold('grab', wind); this.aimHold = { until: this.time + wind, mx: this.mx, mz: this.mz };
          this.state = 'edge-' + best; return;
        }
        if (myEdge < 1.2) { this.dir(0, 0); this.tap('push'); this.state = 'edge-shove'; return; }
        this.rel(c, 1, 0); this.state = 'edge-pushback'; return;
      }
      // fighting for survival on the bales
      if (c.utchariOk(me)) {
        const ev = c.evalTech(me, 'utchari');
        if (ev.ok && this.clT > this.nextTech && this.rnd() < L.skill * 0.35) { this.rel(c, -0.7, this.rnd() < 0.5 ? 0.7 : -0.7); this.hold('grab', 0.2); this.state = 'UTCHARI'; return; }
        if (ev.ok) this.nextTech = this.clT + 0.3;
        if (this.rnd() < 0.55) { this.rel(c, 0.2, this.bestSide(c)); this.state = 'edge-rotate'; }
        else { this.rel(c, 1, 0); this.state = 'edge-pushback'; }
        return;
      }

      const thresh = 0.3 + (1 - L.skill) * 0.18;
      const cands = [];
      for (const k of ['throw', 'trip', 'spin', 'lift']) {
        const ev = c.evalTech(me, k);
        if (ev.ok && ev.sc > thresh) cands.push([k, ev.sc]);
      }
      cands.sort((a, b) => b[1] - a[1]);
      const patience = this.clT > 2.2;
      if (cands.length && this.clT > this.nextTech && (cands[0][1] > 0.5 || patience)) {
        this.nextTech = this.clT + 0.6 + this.rnd() * 1.4;
        const k = cands[0][0], side = this.bestSide(c);
        if (k === 'throw') this.rel(c, 0, side);
        else if (k === 'trip') this.rel(c, 1, 0);
        else if (k === 'spin') this.rel(c, -1, 0);
        else this.dir(0, 0);
        // hold K and point for a moment before letting go, like a human does: it can be read and escaped
        const wind = k === 'lift' ? 0.25 : 0.5 - 0.22 * L.skill + this.rnd() * 0.15;
        this.hold('grab', wind); this.aimHold = { until: this.time + wind, mx: this.mx, mz: this.mz };
        // hard: show one throw, then switch to another halfway through the wind-up
        if (L.tricky > 0.25 && (k === 'throw' || k === 'trip') && this.rnd() < L.tricky * 0.8) {
          const mx0 = this.mx, mz0 = this.mz;
          if (k === 'throw') this.rel(c, 1, 0); else this.rel(c, 0, this.bestSide(c));
          this.aimHold.alt = [this.mx, this.mz]; this.aimHold.switchAt = this.time + wind * 0.5; this.aimHold.until += 0.1; this.hold('grab', wind + 0.1);
          this.mx = mx0; this.mz = mz0;
        }
        this.state = k; return;
      }
      if (me.stam < 0.18 && c.tow[j] < 0.3 && this.rnd() < 0.5) { this.dir(0, 0); this.state = 'rest'; return; }
      if (oEdge < 2.0 && oBack > 0.2) {
        this.rel(c, 1, 0);
        this.state = 'drive'; return;
      }
      if (myEdge < 1.6 && myBack > 0.3) { this.rel(c, 0.3, this.bestSide(c)); this.state = 'swap'; return; }
      if (patience && this.rnd() < 0.15) { this.tap(this.rnd() < 0.5 ? 'push' : 'dash'); this.state = 'break'; return; }
      this.rel(c, 1, oBack < 0.2 ? this.bestSide(c) * 0.5 : 0); this.state = 'drive';
    }

    // break out of a hold: shove off if my back is to the edge, otherwise mostly slip back
    escape(c) {
      const me = this.me, s = c.sg(me), [nx, nz] = c.axis();
      const d = Math.hypot(me.x, me.z) || 1, back = (me.x / d) * -s * nx + (me.z / d) * -s * nz;
      this.release('grab'); this.dir(0, 0); this.aimHold = null;
      this.tap((RR - d < 1.6 && back > 0.2) || this.rnd() < 0.4 ? 'push' : 'dash', 0.04);
      this.state = 'escape';
    }

    // which rotation sends the opponent toward the edge
    bestSide(c) {
      const me = this.me, o = me.opp;
      const a0 = Math.atan2(o.z - me.z, o.x - me.x), r = Math.hypot(o.x - me.x, o.z - me.z);
      const pos = (sg) => { const a = a0 + sg * 0.8; return Math.hypot(me.x + Math.cos(a) * r, me.z + Math.sin(a) * r); };
      return pos(1) > pos(-1) ? 1 : -1;
    }
  }
  S.AI = AI;
  S.AI_MEM = MEM; S.AI_HAB = HAB;
  S.AI_LEVELS = LEVELS;
})();
