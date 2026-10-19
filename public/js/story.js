'use strict';
// LEVEL STORY: a level's own run, from its layout's `story` (tools/blender/LEVELS.md), on the party engine with one player.
// He's lost his mawashi again: a chain of steps (go somewhere, use something, booty-slam something, hide somewhere) leads to
// whoever has it, the boss. The dohyo comes up out of the level, a sumo bout (the same one as the bathhouse's boss), then out.
// Staff patrol, chase, grab: held too long and he's back at the last step he reached.
(function () {
  if (!S.Party || !S.StealthLib) return;
  const { floorY } = S.StealthLib;
  const near = (p, x, z, r) => Math.hypot(p.x - x, p.z - z) < r;

  class LevelStory extends S.Party {
    start(id) {
      const g = this.g, keep = [g.partyLevel, g.partyCpu];
      g.partyLevel = id; g.partyCpu = true;   // (one player: the whole screen)
      super.start('story');
      [g.partyLevel, g.partyCpu] = keep;
    }
    title(name, how) { const c = this.hud.querySelector('.card'); c.innerHTML = '<b>' + name + '</b>' + how + '<br><span style="color:#9fb6d6">WASD move · SHIFT run · L belly slide · J push (hold: booty slam) · K use · I hide' + (this.fpv ? ' · the mouse turns the camera' : '') + '</span><br>ESC: menu';
      c.style.opacity = 1; clearTimeout(this.cardT); this.cardT = setTimeout(() => { if (this.hud) c.style.opacity = 0; }, 7000); }
    hudSide(p, txt) { const h = this.hint(p); if (h) txt += (txt ? '  ·  ' : '') + h; const e = this.hud.querySelector('.s0'); if (e.textContent !== txt) e.textContent = txt; e.style.display = txt ? '' : 'none'; e.style.borderLeft = '6px solid #f2cf4a'; }
    // ---- setup
    setupStory() {
      const St = this.St = this.lv.story || { start: [this.M.start[0][0], this.M.start[0][1], -Math.PI / 2], steps: [], exit: [this.M.exit[0], this.M.exit[1]] };
      const p = this.ps[0], o = this.ps[1]; o.gone = true; o.hidden = { gone: true }; o.x = o.z = 9999;   // (no second player: parked, never drawn)
      this.place(p, St.start[0], St.start[1], St.start[2] === undefined ? -Math.PI / 2 : St.start[2]);
      this.cp = [St.start[0], St.start[1], p.f];
      this.spawnStaff();
      this.mk = this.marker(); this.si = -1; this.cur = null; this.ph = 'play'; this.caughtN = 0; this.tStart = this.t;
      this.hud.querySelector('.s1').style.display = 'none'; this.hud.querySelector('.b1').style.display = 'none';
      this.buildSay();
      const nm = (S.LEVEL_NAMES[this.lvId] || [this.lv.name])[0];
      this.title(nm, this.lv.blurb || 'Find your mawashi');
      const it = St.intro || [];
      if (it.length) this.say(it, () => this.next()); else this.next();
    }
    marker() {   // a ring on the floor and an arrow bobbing over it: where to go next
      const g = new THREE.Group(); this.G.add(g); g.visible = false;
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.8, 1.0, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xf2cf4a, transparent: true, opacity: 0.85, depthWrite: false })); ring.position.y = 0.05; ring.renderOrder = 3; g.add(ring);
      const ar = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.arrowTex(), transparent: true, depthWrite: false, depthTest: false })); ar.scale.set(0.7, 0.7, 1); ar.position.y = 2.6; ar.renderOrder = 7; g.add(ar);
      g.userData = { ring, ar }; return g;
    }
    show(at) { const g = this.mk; if (!at) { g.visible = false; return; } g.visible = true; g.position.set(at[0], floorY(at[0], at[1]), at[1]); }
    dressLevel(k) {
      super.dressLevel(k);
      for (const s of (this.St && this.St.steps) || []) if (s.prop && !s.propM) { const o = k.getObjectByName(s.prop); if (!o) continue; const c = o.clone(); c.visible = true; c.position.set(s.at[0], floorY(s.at[0], s.at[1]), s.at[1]); c.rotation.set(0, 0, 0); this.G.add(c); s.propM = c; if (s.doneOnce) c.visible = false; }
    }
    // ---- the steps
    next() {
      this.si++; const St = this.St;
      if (this.si < St.steps.length) { const s = this.cur = St.steps[this.si]; this.show(s.at); if (s.think) this.thinkLine(s.think); return; }
      this.cur = null; if (St.boss) this.bossAppear(); else this.toExit();
    }
    stepDone() {
      const s = this.cur; if (!s || s.doneOnce) return; s.doneOnce = true; this.cur = null; this.show(null);
      if (s.propM) s.propM.visible = false;
      if (s.open !== undefined) for (const k of [].concat(s.open)) { const w = this.solidW && this.solidW[k]; if (w) { w.x0 = w.x1 = w.z0 = w.z1 = 1e4; } const o = this.kit && this.kit.getObjectByName('SOLID_' + k); if (o) o.visible = false; this.buildNav(); this.points = this.walkPoints(); }
      this.cp = [s.at[0], s.at[1], this.ps[0].f]; this.sfx('whoosh', 0.4);
      if (s.say && s.say.length) this.say(s.say, () => this.next()); else this.next();
    }
    use2(p) {
      const s = this.cur; if (s && s.do === 'use' && near(p, s.at[0], s.at[1], (s.r || 1.6) + 0.4)) { p.st = 'busy'; p.t = 0; this.stepDone(); return; }
      if (this.ph === 'boss' && this.bossM && near(p, this.bossM.x, this.bossM.z, 3.2)) { this.bossTalk(); return; }
      super.use2(p);
    }
    slamLand(p) { super.slamLand(p); const s = this.cur; if (s && s.do === 'slam' && near(p, s.at[0], s.at[1], (s.r || 1.6) + 0.8)) this.stepDone(); }
    frozen(p) { return !!this.saying || !!this.ringCut || this.ph === 'over' || this.ph === 'bout'; }
    caught(p, s) {   // held too long: back to the last step he reached
      s.mode = 'down'; s.t = 0; s.a.st = 'free'; p.grabbedBy = null; p.holdT = 0; this.caughtN++;
      for (const q of this.staff) if (q.mode === 'chase' || q.mode === 'hold') { q.mode = 'patrol'; q.path = null; q.target = null; }
      this.place(p, this.cp[0], this.cp[1], this.cp[2]); this.banner(p, 'CAUGHT! Back to where you were', '#dd5a42'); this.sfx('thump', 4);
    }
    stepStory(dt) {
      const p = this.ps[0];
      if (this.ph !== 'bout') for (const s of this.staff) if (!(this.saying || this.ringCut)) this.staffStep(s, dt);
      this.sayStep(dt); this.ringStep(dt);
      const m = this.mk; if (m.visible) { m.userData.ar.position.y = 2.6 + Math.sin(this.t * 3) * 0.15; m.userData.ring.material.opacity = 0.6 + 0.3 * Math.sin(this.t * 4); }
      const s = this.cur;
      if (s && !this.saying) {
        const r = s.r || 1.6;
        if (s.do === 'goto' || !s.do) { if (near(p, s.at[0], s.at[1], r)) this.stepDone(); }
        else if (s.do === 'hide') { if ((p.hidden || p.sub) && near(p, s.at[0], s.at[1], r + 1.5)) this.stepDone(); }
      }
      if (this.ph === 'boss' && this.bossM && !this.saying && near(p, this.bossM.x, this.bossM.z, 2.6)) this.bossTalk();
      if (this.ph === 'exit' && !this.saying && near(p, this.St.exit[0], this.St.exit[1], 1.8)) this.cleared();
      if (this.bossM) this.bossDraw(dt);
      const obj = this.saying ? '' : this.ph === 'exit' ? 'MAWASHI ✓ · get out: ' + ((this.lv.exit && this.lv.exit.name) || 'the exit') : this.ph === 'boss' ? 'Face ' + this.St.boss.name : this.cur ? this.cur.obj : '';
      this.hudSide(p, obj + (p.st === 'grabbed' ? ' · GRABBED: push, slam, wriggle! ' + Math.max(0, 3 - (p.holdT || 0)).toFixed(1) : ''));
    }
    hint(p) {
      const s = this.cur, K = { use: 'K', hide: 'I', push: 'J' };
      if (p.st === 'grabbed') return 'J: shove them off · hold J: booty slam';
      if (s && near(p, s.at[0], s.at[1], (s.r || 1.6) + 1.2)) { if (s.do === 'use') return K.use + ': ' + (s.verb || 'use'); if (s.do === 'slam') return 'hold J: booty slam it'; if (s.do === 'hide') return K.hide + ': hide here'; }
      if (this.ph === 'boss' && this.bossM && near(p, this.bossM.x, this.bossM.z, 3.2)) return K.use + ': talk';
      return super.hint(p);
    }
    // ---- the boss: he turns up with your mawashi, talks, the dohyo comes up, the bout
    bossAppear() {
      const B = this.St.boss, arch = Object.assign({}, S.ARCH[2 % S.ARCH.length], { belt: new THREE.Color(B.belt || '#3b3346').getHex() });
      const v = new S.WrestlerView(this.scene, arch, this.fx, S.DEF_EQ); v.viewer = 1; v.match = null;
      const w = Object.assign({}, this.ps[0].w, { a: arch, idx: 1, fxs: {}, carry: null, st: 'free', t: 0 });
      this.bossM = { v, w, x: B.at[0], z: B.at[1], f: Math.atan2(this.ps[0].z - B.at[1], this.ps[0].x - B.at[0]) };
      if (S.SoftSumo && S.SoftSumo.loaded) S.SoftSumo.attach(v, { noBlob: true });
      this.puff(B.at[0], 0.5, B.at[1], 10, 0.5); this.ph = 'boss'; this.show(B.at);
      this.thinkLine(B.seen || ('...that\'s ' + B.name + '. And that\'s MY mawashi.'));
    }
    bossDraw(dt) {
      const b = this.bossM, w = b.w, p = this.ps[0]; if (!this.ringCut && this.ph === 'boss') b.f = Math.atan2(p.z - b.z, p.x - b.x);
      w.x = b.x; w.z = b.z; w.y = 0; w.f = b.f; w.fx = Math.cos(b.f); w.fz = Math.sin(b.f); w.vx = w.vz = 0; w.spd = 0; w.st = 'free'; w.relaxed = true; w.fxs = {};
      b.v.update(w, Math.max(dt, 1e-4), this.t); b.v.root.position.y += floorY(b.x, b.z); b.v.root.visible = this.ph !== 'exit' || !this.bossGone;
    }
    bossTalk() {
      if (this.talking) return; this.talking = true; this.show(null);
      const B = this.St.boss; this.say(B.intro || [{ who: B.jp || B.name, jp: '返してほしければ、わしに勝て。', en: 'Want it back? Beat me.' }], () => this.ringRise(() => this.bout()));
    }
    ringRise(cb) {   // the dohyo comes up out of the floor where the level says; the camera re-centres on it (the usual height: never low)
      const R0 = this.lv.ring || { x: this.bossM.x, z: this.bossM.z };
      if (!this.dohyoM) { this.dohyoM = S.makeBathDohyo(); this.dohyoM.scale.setScalar(0.8); this.G.add(this.dohyoM); }
      this.dohyoM.position.set(R0.x, -1.2, R0.z); this.dohyoM.visible = true; this.ringCut = { t: 0, cb, R0 }; this.sfx('whoosh', 0.8);
      const H = 0.55, half = 3.9 * 0.8, f0 = this.rt.floorY;   // (once up, its top is floor: he stands on the mound)
      if (!this.rt.dohyo) { this.rt.dohyo = true; this.rt.floorY = (x, z) => (Math.abs(x - R0.x) < half && Math.abs(z - R0.z) < half ? H + f0(R0.x, R0.z) : f0(x, z)); }
    }
    ringStep(dt) {
      const R = this.ringCut; if (!R) return; R.t += dt; const t = R.t, e = (k) => k * k * (3 - 2 * k), c = (a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
      this.dohyoM.position.y = -1.2 + 1.75 * e(c(0.3, 2.4));
      if (t > 0.3 && t < 2.4 && Math.random() < dt * 10) this.puff(R.R0.x + (Math.random() - 0.5) * 6, 0.2, R.R0.z + (Math.random() - 0.5) * 6, 3, 0.3);
      this.camFocus = { x: R.R0.x, z: R.R0.z };
      if (t > 1.6) { const p = this.ps[0], b = this.bossM; b.x = R.R0.x + 1.2; b.z = R.R0.z; b.f = Math.PI; if (!R.placed) { R.placed = true; this.place(p, R.R0.x - 1.2, R.R0.z, 0); } }
      if (t > 3.6) { this.ringCut = null; this.camFocus = null; R.cb(); }
    }
    bout() {
      const g = this.g, B = this.St.boss; this.ph = 'bout';
      this.bossInfo = { name: B.name, kanji: B.jp || B.name, belt: new THREE.Color(B.belt || '#3b3346').getHex() }; this.bossStage = 'lvring'; g.bossLevel = this.lvId;
      const r = this.R.r; r.setScissorTest(false); r.setViewport(0, 0, innerWidth, innerHeight);
      g.startBossBout(this);
    }
    resumeFromBoss(res) {   // back from the bout (game.leaveBoss)
      this.keys = {}; this.paused = false; this.acc = 0; S.StealthLib.setLevel(this.rt); S.levelStyle(this.lv.style, this.scene);
      if (res === 'quit') { this.g.endCampaign(); return; }
      const B = this.St.boss;
      if (res === 'trained') { this.bout(); return; }
      if (res === 'lost') { this.ph = 'boss'; this.say(B.lost || [{ who: B.jp || B.name, jp: 'まだまだ!', en: 'Not even close. Again!' }], () => this.bout()); return; }
      this.ph = 'won';
      this.say(B.won || [{ who: B.jp || B.name, jp: '…見事だ。持っていけ。', en: '...Well fought. Take it.' }], () => {
        const p = this.ps[0]; p.maw = true; this.banner(p, 'MAWASHI ON!', '#3a9a5e'); this.sfx('whoosh', 0.5);
        this.puff(this.bossM.x, 0.5, this.bossM.z, 10, 0.5); this.bossGone = true; this.bossM.v.root.visible = false; this.toExit(); });
    }
    toExit() { this.ph = 'exit'; this.show(this.St.exit); for (const s of this.staff) if (s.mode === 'hold') { s.mode = 'patrol'; } }
    cleared() {
      this.ph = 'over'; this.show(null); const p = this.ps[0]; p.st = 'win'; p.t = 0;
      try { localStorage.setItem('lv_clear_' + this.lvId, '1'); } catch (e) {}
      const secs = Math.round(this.t - this.tStart);
      this.bigText('LEVEL CLEAR', (S.LEVEL_NAMES[this.lvId] || [''])[0] + ' · ' + Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0') + ' · caught ' + this.caughtN + ' · ENTER: again · ESC: menu');
    }
    // ---- talk: a line at a time at the bottom (K / J / ENTER: next)
    buildSay() {
      const e = this.sayE = document.createElement('div');
      e.style.cssText = 'position:absolute;left:50%;bottom:7vh;transform:translateX(-50%);width:min(760px,90vw);background:rgba(24,22,32,.9);color:#f4efe6;border-radius:14px;padding:14px 20px;display:none;font-family:"Barlow Condensed",sans-serif';
      this.hud.appendChild(e);
      const th = this.thinkE = document.createElement('div');
      th.style.cssText = 'position:absolute;left:50%;top:18vh;transform:translateX(-50%);max-width:80vw;background:rgba(255,250,240,.94);color:#3a3440;border-radius:18px;padding:8px 16px;font:700 20px "Barlow Condensed",sans-serif;opacity:0;transition:opacity .3s';
      this.hud.appendChild(th);
    }
    say(lines, cb) { this.saying = { lines: lines.slice(), i: -1, t: 0, cb }; this.sayNext(); }
    sayNext() {
      const S0 = this.saying; S0.i++; S0.t = 0;
      if (S0.i >= S0.lines.length) { this.saying = null; this.sayE.style.display = 'none'; S0.cb && S0.cb(); return; }
      const L0 = S0.lines[S0.i]; S0.dur = L0.t || Math.max(2.2, (L0.en || '').length * 0.055);
      this.sayE.innerHTML = (L0.who ? '<div style="color:#f2cf4a;font-weight:800;font-size:16px">' + L0.who + '</div>' : '<div style="color:#9fb6d6;font-weight:800;font-size:16px">YOU (thinking)</div>') +
        '<div style="font-size:22px;font-weight:700">' + (L0.jp || '') + '</div><div style="font-size:19px;opacity:.85">' + (L0.en || '') + '</div>';
      this.sayE.style.display = 'block';
    }
    sayStep(dt) {
      const S0 = this.saying; if (!S0) return; S0.t += dt;
      const k = this.keys, adv = k.Enter || k.KeyK || k.KeyJ || k.KeyE || k.Space;
      if (adv && !this.advHeld && S0.t > 0.35) { this.advHeld = true; this.sayNext(); return; }
      if (!adv) this.advHeld = false;
      if (S0.t > S0.dur + 1.2) this.sayNext();
    }
    thinkLine(t) { const e = this.thinkE; if (!e) return; e.textContent = t; e.style.opacity = 1; clearTimeout(this.thT); this.thT = setTimeout(() => { if (this.thinkE) e.style.opacity = 0; }, 3200); }
  }
  S.LevelStory = LevelStory;
})();
