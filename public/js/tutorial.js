'use strict';
// Interactive tutorial: short lessons against a scripted practice partner.
(function () {
  // Practice partner: an input source with a few simple behaviours.
  class Dummy {
    constructor() { this.mode = 'idle'; this.t = 0; this.me = null; this.home = [1.5, 0]; }
    set(mode, home) { this.mode = mode; this.t = 0; if (home) this.home = home; }
    sample() {
      const r = { mx: 0, mz: 0, push: false, grab: false, dash: false };
      const me = this.me; if (!me) return r;
      const o = me.opp;
      this.t += S.DT;
      const dir = (x, z) => { const l = Math.hypot(x, z); if (l > 1e-3) { r.mx = x / l; r.mz = z / l; } };
      if (me.clinch && this.mode !== 'lifter') {
        if (this.mode === 'drive') dir(o.x - me.x, o.z - me.z);
        return r;
      }
      if (this.mode === 'lifter') { // grabs you, then lifts you
        if (me.clinch) { if (!me.clinch.lift && me.clinch.t > 0.4 && this.t % 1 < 0.05) r.grab = true; if (me.clinch.lift) { const d = Math.hypot(me.x, me.z) || 1; r.mx = -me.x / d * 0.3; r.mz = -me.z / d * 0.3; } return r; }
        dir(o.x - me.x, o.z - me.z);
        if (Math.hypot(o.x - me.x, o.z - me.z) - me.r - o.r < 0.4 && this.t % 1.2 < 0.05) r.grab = true;
        return r;
      }
      if (this.mode === 'grab') { // strolls up slowly, stops, then reaches for you: easy to read
        dir(o.x - me.x, o.z - me.z);
        const gap = Math.hypot(o.x - me.x, o.z - me.z) - me.r - o.r;
        if (gap > 0.4) { r.mx *= 0.35; r.mz *= 0.35; this.wait = 0; }
        else { r.mx *= 0.05; r.mz *= 0.05; this.wait = (this.wait || 0) + S.DT; if (this.wait > 0.9) { r.grab = true; this.wait = -0.6; } }
        return r;
      }
      if (this.mode === 'palm') { // walks up and slaps at you
        dir(o.x - me.x, o.z - me.z);
        const gap = Math.hypot(o.x - me.x, o.z - me.z) - me.r - o.r;
        if (gap < 0.45) { r.mx *= 0.2; r.mz *= 0.2; if (this.t % 1.1 < 0.04 && me.spd < 1.5) r.push = true; }
        return r;
      }
      if (this.mode === 'charge') {
        const ph = this.t % 3.4;
        if (ph < 1.3) { const hx = this.home[0] - me.x, hz = this.home[1] - me.z; if (Math.hypot(hx, hz) > 0.3) dir(hx * 0.4, hz * 0.4); }
        else if (ph < 2.1) { dir(o.x - me.x, o.z - me.z); if (ph > 1.72 && ph < 1.76) r.push = true; }
        return r;
      }
      // idle / drive: wander back home if knocked away
      const hx = this.home[0] - me.x, hz = this.home[1] - me.z;
      if (Math.hypot(hx, hz) > 1.2 && me.st === 'free') { dir(hx, hz); r.mx *= 0.4; r.mz *= 0.4; }
      return r;
    }
  }
  S.Dummy = Dummy;

  const L = (title, text, opts) => Object.assign({ title, text, need: 1 }, opts);
  const LESSONS = [
    L('HOW TO WIN', 'You win a bout when they step out of the ring, or when anything but the soles of their feet touches the clay: a hand, a knee, their back. First to win 2 bouts wins the match. Press J or Enter to start.', { check: 'info' }),
    L('MOVE', 'Walk into the glowing circle with W A S D.', { setup: 'marker', check: 'marker' }),
    L('DASH', 'Hold a direction and tap L to dash. You can dash almost any time, even mid-slap. Dash 3 times.', { need: 3, ev: (e, p) => e.type === 'dash' && e.w === p }),
    L('PUSH', 'Walk up close and tap J to push. Land 3 pushes.', { need: 3, ev: (e, p) => (e.type === 'hit' && e.w === p) || (e.type === 'impact' && e.a === p && e.agg) }),
    L('FLURRY', 'Tap J again and again, fast, to rain open-hand slaps (tsuppari). Land 5 in a row. A long flurry tires you out, and slapping at air leaves you open.', { need: 5, ev: (e, p) => e.type === 'hit' && e.w === p && e.kind === 'palm' }),
    L('HEAVY SHOVE', 'Stand still and hold J to wind up. Keep holding while you walk up to them, then let go for a big shove. (Pressing J while running is a charge instead.)', { ev: (e, p) => e.type === 'hit' && e.kind === 'heavy' && e.w === p }),
    L('THROAT PUSH', 'Get up close, hold L to plant your feet, then tap J: your hand goes up to their throat and stands them up, so they cannot push back for a moment.', { ev: (e, p) => e.type === 'hit' && e.w === p && e.special === 'nodowa' }),
    L('CHARGE', 'Run at them and press J just before you reach them. Speed is power.', { pos: [[-2.6, 0], [2.0, 0]], ev: (e, p) => e.type === 'impact' && e.a === p && e.agg }),
    L('RING OUT', 'Push them out of the ring. Watch their feet near the straw.', { pos: [[-0.4, 0], [3.0, 0]], win: true }),
    L('GRAB', 'Get close and tap K to grab their belt. You are now locked together.', { ev: (e, p) => e.type === 'clinch' && e.w === p }),
    L('GRAB BREAK', 'They will grab you. Tap K the instant they grab (or grab at the same moment) to break free. You both bounce apart.', { dummy: 'grab', ev: (e, p) => e.type === 'grabTech' }),
    L('DRIVE', 'Grab them with K, then just hold toward them. You walk them backwards and out.', { pos: [[0.4, 0], [2.6, 0]], win: true }),
    L('THROW', 'Grab with K and KEEP HOLDING it. Point sideways: they swing round you. The longer you swing, the harder the throw, but the more time they have to escape. Let go of K to throw them.', { dummy: 'drive', ev: (e, p) => (e.type === 'throw' && e.w === p && e.name !== 'hikiotoshi' && !/gake/.test(e.name)) || (e.type === 'decided' && e.winner === p && /nage|katasukashi/.test(e.km)) }),
    L('SPIN', 'They lean into you. Grab and keep holding K, then point behind you: they swing all the way round. Let go to send them flying.', { dummy: 'drive', ev: (e, p) => (e.type === 'throw' && e.w === p && (e.name === 'katasukashi' || e.swept > 2.2)) || (e.type === 'decided' && e.winner === p && e.km === 'katasukashi') }),
    L('LEG TRIP', 'Grab and keep holding K. Point straight at them, then let go of K to hook their leg.', { dummy: 'drive', ev: (e, p) => (e.type === 'throw' && e.w === p && /gake/.test(e.name)) || (e.type === 'decided' && e.winner === p && /gake/.test(e.km)) }),
    L('LIFT', 'Grab them, then tap K without aiming anywhere to lift them off their feet. Walk them out of the ring!', { pos: [[0.6, 0], [2.0, 0]], ev: (e, p) => (e.type === 'decided' && e.winner === p && e.km.indexOf('tsuri') === 0) }),
    L('SLAM', 'Grab them, tap K to lift them, then tap K again to slam them down. You let go and they are left dizzy.', { pos: [[0.6, 0], [2.0, 0]], ev: (e, p) => e.type === 'slam' && e.o && e.w === p }),
    L('WRIGGLE FREE', 'Now they lift YOU. Mash any button as fast as you can to wriggle free before they carry you out.', { dummy: 'lifter', pos: [[-0.4, 0], [1.0, 0]], ev: (e, p) => e.type === 'liftEnd' && e.o === p }),
    L('SHOVE OFF', 'Grab them, then tap J to shove yourself free and send them backwards. This also gets you out when THEY grab you.', { dummy: 'drive', ev: (e, p) => e.type === 'clinchEnd' && e.reason === 'break' }),
    L('LET GO', 'Grab them, then tap L to let go and step back. If they were pushing, they stumble forward. When they grab you and THROW COMING shows, tap L to slip out.', { dummy: 'drive', ev: (e, p) => e.type === 'disengage' && e.w === p }),
    L('EDGE SAVE', 'You are being driven out! Hold K and point behind you to swing them round and over the edge before your heels leave the straw.', { clinch: true, dummy: 'drive', pos: [[3.75, 0], [2.45, 0]], face: [Math.PI, 0], ev: (e, p) => (e.type === 'throw' && e.w === p && e.name === 'utchari') || (e.type === 'decided' && e.winner === p && e.km === 'utchari') }),
    L('STOP SHORT', 'Run at them and press J to charge, then tap L mid-charge to stop dead. Great when you think they will sidestep.', { pos: [[-2.6, 0], [2.0, 0]], ev: (e, p) => e.type === 'chargeCancel' && e.w === p }),
    L('SIDESTEP', 'They will charge at you. Hold a direction to the side and tap L to dodge.', { dummy: 'charge', pos: [[-1.2, 0], [2.6, 0]], ev: (e, p) => (e.type === 'perfectDodge' && e.w === p) || (e.type === 'whiff' && e.w !== p && !e.grab) }),
    L('FROM BEHIND', 'Dodge their charge, then chase them and hit their side or back with J. Pushes from behind are much stronger.', { dummy: 'charge', pos: [[-1.2, 0], [2.6, 0]], ev: (e, p) => (e.type === 'hit' && e.w === p && e.zone !== 'front') || (e.type === 'impact' && e.a === p && e.zone !== 'front') }),
    L('SLAP DOWN', 'As they charge in, hold away from them and tap J. You step back and slap them down with their own speed. It also works on someone flurrying at you. Miss and you are left open.', { dummy: 'charge', pos: [[-1.2, 0], [2.6, 0]], ev: (e, p) => e.type === 'hit' && e.w === p && e.kind === 'slap' }),
    L('BRACE', 'They will charge again. Hold L (no direction) to brace and take the hit. Time it just before impact for a perfect STOP.', { dummy: 'charge', pos: [[-1.2, 0], [2.6, 0]], ev: (e, p) => (e.type === 'braceCounter' && e.w === p) || (e.type === 'impact' && e.t === p && e.braced) }),
    L('PARRY', 'They will slap at you. Tap L (no direction) right as their hand arrives to knock it aside. They are left wide open.', { dummy: 'palm', ev: (e, p) => e.type === 'parry' && e.w === p }),
    L('CATCH', 'One more charge. Tap K right as they crash into you to catch them and spin them away.', { dummy: 'charge', pos: [[-1.2, 0], [2.6, 0]], ev: (e, p) => e.type === 'catch' && e.w === p }),
    L('FACE-OFF', 'Show off first: J clap, K stomp (W A S D more taunts). Then hold L to crouch and KEEP holding. When PRESS J! appears, press J to charge.', { setup: 'faceoff', check: 'faceoff' }),
    L('FACE SLAP', 'Charge at the start (J when PRESS J! appears), then tap J again as you hit: an open-hand slap to the face (harite) dazes them.', { setup: 'quickstart', check: 'quickstart', ev: (e, p) => e.type === 'hit' && e.w === p && e.special === 'harite' }),
    L('GACHA MODE', 'Two ways to play: PURE (just sumo) or GACHA, picked with Tab on character select. In Gacha, both of you draw a random one-shot skill at the start of every round. Use it or lose it. Try some: Space uses it, G draws another. Press Enter when you are done.', { setup: 'gacha', check: 'gacha' }),
  ];

  class Tutorial {
    constructor(game) {
      this.g = game; this.i = 0; this.count = 0; this.done = false; this.wait = 0;
      this.el = document.getElementById('tutPanel');
    }
    get p() { return this.g.match.w[0]; }
    lesson() { return LESSONS[this.i]; }
    begin(i, keep) {
      const g = this.g, m = g.match;
      if (!(keep && i === this.i)) this.count = 0;
      this.i = i; this.done = false; this.wait = 0; this.flags = {};
      if (i >= LESSONS.length) { this.finish(); return; }
      g.ui.hideGacha(); g.ui.hideBanner();
      const Ls = LESSONS[i];
      const pos = Ls.pos || [[-1.5, 0], [1.5, 0]];
      m.round = i; m.result = null; m.clinch = null; m.deadT = 0;
      const face = Ls.face || [0, Math.PI];
      m.w[0].reset(pos[0][0], pos[0][1], face[0]);
      m.w[1].reset(pos[1][0], pos[1][1], face[1]);
      if (Ls.setup === 'faceoff') { m.phase = 'shikiri'; m.phaseT = 0; m.goAt = 1e9; }
      else if (Ls.setup === 'quickstart') { m.phase = 'shikiri'; m.phaseT = 0; m.goAt = 1.6 + Math.random() * 0.6; }
      else { m.phase = 'fight'; m.sinceGo = 5; for (const w of m.w) w.set('free'); }
      m.time = 0; m.events = [];
      if (Ls.clinch) m.clinch = new S.Clinch(m, m.w[0], m.w[1], {});
      this.g.dummy.set(Ls.dummy || 'idle', pos[1]);
      this.g.match.techWin = Ls.dummy === 'grab' ? 0.5 : 0; // more time to break the hold while learning it
      g.R.fx.clearDecals();
      if (Ls.setup === 'gacha') { m.skills = [null, null]; if (!keep) this.skI = undefined; this.drawSkill(keep && this.skI !== undefined); } else m.skills = [null, null];
      if (Ls.setup === 'marker') { this.mk = [1.2, 1.6]; g.R.setMarker(this.mk[0], this.mk[1]); } else g.R.setMarker(null);
      g.ui.hideKimarite();
      this.render();
    }
    render() {
      const Ls = LESSONS[this.i];
      if (!Ls) return;
      let ticks = '';
      for (let k = 0; k < LESSONS.length; k++) ticks += '<i class="' + (k < this.i ? 'on' : k === this.i ? 'cur' : '') + '"></i>';
      const prog = Ls.need > 1 ? ' <b>' + Math.min(this.count, Ls.need) + ' / ' + Ls.need + '</b>' : '';
      this.el.innerHTML = '<div class="tp-head"><span>LESSON ' + (this.i + 1) + ' / ' + LESSONS.length + '</span>' + Ls.title + prog + '</div>' +
        '<div class="tp-text">' + Ls.text + '</div><div class="tp-ticks">' + ticks + '</div>' +
        (this.done ? '<div class="tp-ok">NICE!</div>' : '') + '<div class="tp-skip">Q previous · R replay · E skip · Esc pause</div>';
      this.el.classList.add('on');
    }
    complete() {
      if (this.done) return;
      this.done = true; this.wait = 1.3;
      this.g.audio.blip(true); this.g.audio.swell(0.5, 1);
      this.render();
    }
    onEvent(e) {
      if (e.type === 'skillUse' && LESSONS[this.i] && LESSONS[this.i].check === 'gacha') this.refillT = 1.6;
      if (this.done) return;
      const Ls = LESSONS[this.i], p = this.p;
      if (Ls.ev && Ls.ev(e, p)) { this.count++; this.render(); if (this.count >= Ls.need) this.complete(); }
      if (Ls.check === 'faceoff') {
        if (e.type === 'clap' && e.w === p) this.flags.clap = true;
        if (e.type === 'stomp' && e.w === p) this.flags.stomp = true;
        if (e.type === 'charge' && e.w === p && e.tachiai && this.flags.go) this.complete();
        if (e.type === 'go' && this.flags.go) this.flags.went = true;
      }
      if (e.type === 'decided') {
        if (Ls.win && e.winner === p && !e.draw) this.complete();
        else if (!this.done) this.wait = -1.2; // reset the lesson after a moment
      }
    }
    update(dt) {
      const Ls = LESSONS[this.i]; if (!Ls) return;
      const p = this.p, m = this.g.match;
      if (Ls.check === 'marker' && !this.done && Math.hypot(p.x - this.mk[0], p.z - this.mk[1]) < 0.6) this.complete();
      if (Ls.check === 'faceoff' && this.flags.clap && this.flags.stomp && (p.crouchT || 0) > 0.4 && !this.flags.go) {
        this.flags.go = true; m.goAt = m.phaseT + 0.8 + Math.random() * 0.8;
      }
      if (Ls.check === 'faceoff' && this.flags.went && !this.done && m.sinceGo > 2.5) this.begin(this.i); // missed the start: try again
      if (Ls.check === 'quickstart' && m.phase === 'fight' && !this.done && m.sinceGo > 3) this.begin(this.i, true);
      if (this.refillT > 0) { this.refillT -= dt; if (this.refillT <= 0 && LESSONS[this.i] && LESSONS[this.i].check === 'gacha' && !this.g.match.skills[0]) this.drawSkill(true); }
      if (this.wait > 0) { this.wait -= dt; if (this.wait <= 0) this.begin(this.i + 1); }
      else if (this.wait < 0) { this.wait += dt; if (this.wait >= 0) this.begin(this.i, true); }
      // keep lessons going after a stray ring-out / fall
      if (m.phase === 'over' && !this.wait && !this.done) this.wait = -1.2;
    }
    skip() { this.begin(this.i + 1); }
    drawSkill(same) {
      const L = S.Skills.LIST;
      if (!same) this.skI = ((this.skI === undefined ? -1 : this.skI) + 1) % L.length;
      const id = L[this.skI].id; this.g.match.skills[0] = id;
      this.g.ui.gacha(0, id, false, 'Space', true, (this.skI + 1) + ' / ' + L.length + ' &nbsp;·&nbsp; <kbd>G</kbd> next skill · <kbd>Enter</kbd> finish');
      this.g.audio.blip(true);
    }
    prev() { this.begin(Math.max(0, this.i - 1)); }
    replay() { this.begin(this.i); }
    finish() {
      this.el.classList.remove('on'); this.g.ui.hideGacha();
      this.g.R.setMarker(null);
      this.g.tut = null;
      this.g.seenTut = true; this.g.save();
      this.g.ui.show('tutdone');
    }
    hide() { this.el.classList.remove('on'); this.g.R.setMarker(null); this.g.ui.hideGacha(); }
  }
  S.Tutorial = Tutorial;
})();
