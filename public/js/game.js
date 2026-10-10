'use strict';
// Game: main loop, match flow, event -> feedback (fx, audio, camera, time), menus, tutorial.
(function () {
  if (!window.THREE) { document.getElementById('nolib').classList.remove('hidden'); return; }
  const RR = S.RING_R;
  S.OPAQUE_SCREENS = ['title', 'select', 'settings', 'controls', 'binds', 'soon', 'trainsel', 'tutorial', 'tutdone', 'moves', 'online', 'lobby', 'play'];

  class Game {
    constructor() {
      this.settings = { difficulty: 'normal', debug: false, hints: true, sound: true, endless: false };
      this.seenTut = false;
      try {
        const sv = JSON.parse(localStorage.getItem('hakkeyoi') || '{}');
        Object.assign(this.settings, sv.settings || {}); this.seenTut = !!sv.seenTut;
      } catch (e) { /* storage blocked */ }
      this.settings.debug = false;
      this.R = new S.Renderer(document.getElementById('gl'));
      // ART STYLE: the fork (KUMITEGAME) keeps its own choice and starts in ANIME; the main game starts CLASSIC
      this.styleKey = window.KUMITE_FORK ? 'styleFork' : 'style';
      if (!this.settings[this.styleKey]) this.settings[this.styleKey] = window.KUMITE_STYLE === 'anime' ? 'anime' : 'classic';
      this.R.setAnime(this.settings[this.styleKey] === 'anime');
      this.audio = new S.Audio();
      this.audio.muted = !this.settings.sound;
      this.ui = new S.UI(this);
      this.net = new S.Net(this);
      this.match = null; this.ctrls = []; this.ais = []; this.mode = 'title'; this.paused = false;
      this.acc = 0; this.ts = 1; this.slowT = 0; this.slowScale = 1; this.hitstop = 0; this.excite = 0;
      this.overT = 0; this.kmShown = false; this.need = 2; this.palmChain = [0, 0]; this.nokottaT = 0;
      this.sel = { mode: 'cpu', c1: 0, c2: 1, lock1: false, lock2: false };
      this.padPrev = {}; this.tut = null; this.uiBack = 'title';
      S.kb.on((e) => this.onKey(e));
      addEventListener('pointerdown', () => this.audio.init());
      document.getElementById('shopUi').addEventListener('pointerdown', (e) => { const b = e.target.closest('[data-shop]'); if (b) { e.preventDefault(); this.shopAction(b.dataset.shop); } });
      document.getElementById('trainPanel').addEventListener('click', (e) => {
        const b = e.target.closest('[data-train]'); if (!b || this.kind !== 'training') return;
        ({ gacha: () => this.trainGacha(), back: () => this.trainSkill(-1), next: () => this.trainSkill(1), partner: () => this.cycleTrain(), reset: () => this.trainReset(), rec: () => this.trainRec(), stage: () => this.trainStage(1) })[b.dataset.train]();
      });
      document.getElementById('screen').addEventListener('click', (e) => {
        const tab = e.target.closest('[data-cat]');
        if (tab && this.ui.name === 'locker') { this.lockerCat = +tab.dataset.cat; this.showLocker(0); return; }
        if (e.target.closest('[data-rules]') && this.ui.name === 'select') { this.toggleRules(); return; }
        if (e.target.closest('[data-bet]') && this.ui.name === 'select') { this.changeBet(1); return; }
        if (e.target.closest('[data-stage]') && (this.ui.name === 'select' || this.ui.name === 'trainsel')) { this.changeStage(1); return; }
        const c = e.target.closest('[data-card]');
        if (c && this.ui.name === 'trainsel') { const i = +c.dataset.card; if (this.sel.c1 === i) this.startTraining(); else { this.sel.c1 = i; this.ui.show('trainsel', { c1: i }); } return; }
        if (c && this.ui.name === 'select') {
          const i = +c.dataset.card;
          if (this.sel.c1 === i && !this.sel.lock1) this.lockSel(1);
          else if (!this.sel.lock1) { this.sel.c1 = i; this.audio.blip(false); this.ui.show('select', this.sel); }
        }
      });
      this.startAttract();
      // open with one banner wipe straight onto the menu (the page starts behind a black cover): wait for the banner art first
      // ...and for the logo, decoded, so the title never appears without it
      const logo = new Image(); logo.src = 'assets/logo.webp?v=2';
      const logoReady = new Promise((res) => { (logo.decode ? logo.decode() : Promise.reject()).then(res, () => { logo.onload = res; logo.onerror = res; if (logo.complete) res(); }); setTimeout(res, 3000); });
      const showTitle = () => logoReady.then(() => this.ui.show('title'));
      if (S.WMM) S.WMM.splash(() => { if (!this.camp) this.ui.showNow('title'); }); // straight onto the white title (no banner wipe: it flashed the versus arena)
      else if (S.Banners && S.Banners.whenReady) S.Banners.whenReady(showTitle, 3000); else showTitle();
      // background ticker: browsers pause hidden windows, which would freeze an online opponent
      try {
        const tk = new Worker(URL.createObjectURL(new Blob(['setInterval(() => postMessage(0), 16)'], { type: 'text/javascript' })));
        tk.onmessage = () => { if (document.hidden && this.kind === 'online') { const t = performance.now(); this.lastBg = t; this.frame(t, true); } };
      } catch (e) { /* no workers: fine */ }
      // photo mode for screenshots: ?demo=1,2&snap=impact&after=3
      const q = new URLSearchParams(location.search);
      if (q.get('demo')) {
        const [a, b] = q.get('demo').split(',').map(Number);
        this.ui.hide(); this.spectate(a, b);
        this.snap = q.get('snap'); this.snapAfter = +(q.get('after') || 0); this.snapPow = +(q.get('pow') || 0);
        if (q.get('debug')) { this.settings.debug = true; document.getElementById('debug').classList.add('on'); }
      }
      this.last = performance.now();
      requestAnimationFrame((t) => this.frame(t));
    }
    save() { try { localStorage.setItem('hakkeyoi', JSON.stringify({ settings: this.settings, seenTut: this.seenTut })); } catch (e) { /* ignore */ } }

    // ------------------------------------------------------------ setup
    setupMatch(i1, i2, kind) {
      this.awaitGacha = false; if (this.ui) { this.ui.hideGacha(); this.ui.vhs(false); }
      let archs = [S.ARCH[i1], S.ARCH[i2]];
      if (kind === 'boss') { const A = S.ARCH[0]; i2 = 0; archs = [Object.assign({}, S.ARCH[i1], { name: 'YOU', kanji: 'あなた' }),   // the bathhouse owner: regular size, grey topknot, his own dark mawashi, a gentler build
        Object.assign({}, A, { name: 'YUNOFUJI', kanji: '湯乃富士', belt: 0x3b3346, hair: 0xc9c6c0, accent: '#8a7aa8', moveForce: A.moveForce * 0.82, pushForce: A.pushForce * 0.72, power: A.power * 0.75, dashSpeed: A.dashSpeed * 0.82, grip: A.grip * 0.9, stability: A.stability * 0.92 })]; }
      this.kind = kind; this.archIdx = [i1, i2];
      const m = this.match = new S.Match(archs);
      this.ais = []; this.ctrls = []; this.dummy = null;
      for (let k = 0; k < 2; k++) {
        let src;
        if (kind === 'online') { src = new S.NetSource(this, k); }
        else if (kind === 'attract' || ((kind === 'cpu' || kind === 'boss') && k === 1)) {
          const ai = new S.AI(m.w[k], m, kind === 'attract' ? 'normal' : kind === 'boss' ? 'boss' : this.settings.difficulty, { noLearn: kind === 'attract' || kind === 'boss' }); if (kind === 'boss') { ai.L = Object.assign({}, S.AI_LEVELS.boss); this.bossSoft = 0; }
          this.ais.push(ai); src = ai;
        } else if (kind === 'training' && k === 1) {
          this.dummy = new S.Dummy(); this.dummy.me = m.w[1];
          const ai = new S.AI(m.w[1], m, this.settings.difficulty, { noLearn: true }); this.ais.push(ai);
          this.trainAI = ai;
          const g = this; src = { sample: () => g.trainSample(ai) };
        } else if (kind === 'tutorial' && k === 1) {
          src = this.dummy = new S.Dummy(); this.dummy.me = m.w[1];
        } else src = new S.KeySource(kind === 'pvp' ? (k === 0 ? S.MAPS.p1 : S.MAPS.p2) : S.MAPS.solo, k);
        const c = new S.Controller(src);
        this.ctrls.push(c); m.w[k].input = c;
      }
      const P = S.profile;
      const human = (k) => kind === 'pvp' || ((kind === 'cpu' || kind === 'boss' || kind === 'tutorial' || kind === 'showcase' || kind === 'training') && k === 0);
      this.loadouts = kind === 'online' ? [0, 1].map((k) => (this.netMatch.los[k] || JSON.parse(JSON.stringify(S.DEF_EQ)))) : [0, 1].map((k) => (k === 0 && human(0) ? P.loadout() : kind === 'pvp' ? JSON.parse(JSON.stringify(S.DEF_EQ)) : P.randomLoadout()));
      this.names = [kind === 'boss' ? 'YOU' : human(0) ? P.names[0] : 'CPU', kind === 'pvp' ? P.names[1] : kind === 'boss' ? 'YUNOFUJI' : kind === 'tutorial' || kind === 'training' ? 'PARTNER' : 'CPU'];
      this.viewerIdx = kind === 'pvp' ? -1 : kind === 'attract' ? -1 : 0;
      for (let k = 0; k < 2; k++) m.w[k].extraTaunts = this.loadouts[k].taunts.map((id) => (id ? S.item(id).pose : null));
      this.R.noMasks = kind === 'boss'; this.R.setWrestlers(archs, this.loadouts, this.names); this.R.bossGear(kind === 'boss', kind === 'boss' && this.bossBox, this.bossBoxMaker || null);
      for (const v of this.R.views) v.onDerobe = (w) => { this.audio.whoosh(0.4); this.R.fx.dust(w.x, 0.05, w.z, 6, 0.3, 0.5, 0.3); this.audio.cheer(0.4, 0.8); };
      this.ui.setFighters(archs, kind === 'cpu' ? [this.names[0], 'CPU · ' + this.settings.difficulty.toUpperCase()] : kind === 'boss' ? ['', '湯乃富士'] : kind === 'pvp' ? this.names : kind === 'tutorial' ? ['YOU', 'PARTNER'] : ['CPU', 'CPU']);
      this.ui.setSkills([null, null], [false, false], ['', '']);
      this.ui.setRecord(kind === 'cpu' || kind === 'pvp' ? this.recordText() : '');
      this.ui.setWins([0, 0], this.need);
      this.ui.hideKimarite();
      this.matchOver = false; this.acc = 0; this.slowT = 0; this.hitstop = 0;
      this.bnrGo = false; this.bnrKey = null;
      if (this.bannerKind()) S.Banners.wall({ hold: 0.15, speed: 0.95 });
      // stage: your pick (or a random one) for CPU, local versus and training; the classic dohyo everywhere else
      const stage = kind === 'boss' ? 'bath' : ['cpu', 'pvp', 'training'].includes(kind) ? S.stageFor(S.profile.stage) : 'dohyo';
      this.R.setStage(stage); m.stage = stage;
      if (kind !== 'tutorial') { m.newRound(); this.handleEvents(); this.dealSkills(); }
    }
    // gacha rules: every round, both players draw a fresh random skill (unused ones are lost)
    dealSkills() {
      const m = this.match;
      if (S.profile.rules !== 'gacha' || (this.kind !== 'cpu' && this.kind !== 'pvp')) return;
      m.skills = [S.Skills.random(), S.Skills.random()]; m.peek = [false, false];
      this.refreshSkills();
      this.awaitGacha = true; this.gachaReadyAt = performance.now() + 1200;
      setTimeout(() => { if (this.match === m) { this.ui.gacha(0, m.skills[0], false, this.skillKey(0), true, this.contKey(0)); this.audio.blip(true); } }, 500);
    }
    // ---- the boss, from the bathhouse: a sumo bout against him (best of three), a training session; then back to the bathhouse
    dealBossGacha() {   // "ハンデだ": you lost a round, so he flicks you a capsule: one skill, yours for the next
      const m = this.match; if (!m) return;
      m.skills = [S.Skills.random(), null]; m.peek = [false, false]; this.refreshSkills();
      this.awaitGacha = true; this.gachaReadyAt = performance.now() + 1200;
      this.ui.gacha(0, m.skills[0], false, this.skillKey(0), true, this.contKey(0)); this.audio.blip(true);
    }
    enterBoss(camp) {
      if (camp && camp.makeBox) this.bossBoxMaker = () => camp.makeBox();   // park the bathhouse (it stays exactly as it is) and take over the screen
      this.campSaved = camp; this.camp = null; this.leavingBoss = false;
      if (camp.hud) camp.hud.style.display = 'none';
      document.body.classList.remove('campaign'); document.body.classList.add('playing');
    }
    startBossBout(camp) {
      this.enterBoss(camp);
      const c1 = this.sel.c1 || 0, c2 = c1 === 1 ? 0 : 1;
      this.sel = { mode: 'cpu', c1, c2, lock1: false, lock2: false };
      this.nsStreak = 0; this.mode = 'game'; this.paused = false; this.endTutorial(); this.ui.training(null); this.ui.hide(); this.ui.showHud(true); this.ui.hint('Esc pause'); this.stake = 0;
      this.setupMatch(c1, c2, 'boss');
    }
    startBossTraining(camp) { this.enterBoss(camp); this.startTutorial(); }
    leaveBoss(res) {
      if (this.leavingBoss || !this.campSaved) return; this.leavingBoss = true;
      const done = () => {
        const camp = this.campSaved; this.campSaved = null; this.leavingBoss = false; this.paused = false;
        this.startAttract(); this.ui.hide(); this.ui.showHud(false); this.ui.hint(''); this.ui.training(null);
        this.mode = 'campaign'; document.body.classList.add('playing', 'campaign'); this.camp = camp; this.R.resize();
        if (camp.hud) camp.hud.style.display = '';
        camp.resumeFromBoss(res);
      };
      const bn = S.Banners; if (bn && !bn.busy) bn.flood({ hold: 0.06, speed: 1.6, onCovered: done }); else done();
    }
    startAttract() {
      if (!this.ui.pending) S.Banners.stop(); // a menu wipe may be on its way: let it finish
      this.bnrGo = false; this.ui.vhs(false);
      this.mode = 'title'; this.endTutorial(); this.R.camOverride = null; this.ui.training(null);
      // no live demo behind the menus: empty the ring
      this.match = null; this.kind = 'title'; this.ais = []; this.ctrls = []; this.awaitGacha = false;
      this.R.setWrestlers([], null, ['', '']); this.R.clearObjs();
      this.ui.hideKimarite(); this.ui.hideBanner();
      this.ui.showHud(false); this.ui.hint('');
    }
    startGame() {
      this.nsStreak = 0;
      this.mode = 'game'; this.paused = false; this.endTutorial(); this.ui.training(null);
      this.ui.hide(); this.ui.showHud(true);
      this.ui.hint(this.sel.mode === 'cpu' && this.settings.endless ? 'Non-stop · Esc pause to stop' : 'Esc pause');
      this.stake = 0;
      if (this.sel.mode === 'cpu' && !this.settings.endless) { this.stake = S.profile.betNow(); if (this.stake) { S.profile.earn(-this.stake); this.ui.setYen(); } }
      this.setupMatch(this.sel.c1, this.sel.c2, this.sel.mode);
    }
    startTutorial() {
      if (!S.Banners.busy) S.Banners.wall({ hold: 0.12, speed: 1.1 });
      this.mode = 'game'; this.paused = false; this.ui.training(null);
      this.ui.hide(); this.ui.showHud(false); this.ui.hint('');
      this.setupMatch(0, 2, 'tutorial');
      this.tut = new S.Tutorial(this);
      this.tut.begin(0);
    }
    endTutorial() { if (this.tut) { this.tut.hide(); this.tut = null; } }
    // test helper: watch two CPUs from the in-game camera
    spectate(i1, i2, lvl) {
      this.sel = { mode: 'cpu', c1: i1, c2: i2, lock1: true, lock2: true };
      this.startGame();
      const m = this.match, ai = new S.AI(m.w[0], m, lvl || 'hard', { noLearn: true });
      this.ais.unshift(ai); this.ctrls[0].src = ai;
    }
    // test helper: render the current frame at a fixed size and send it to the dev server
    async capture(name, w, h) {
      w = w || 1600; h = h || 900;
      const R = this.R;
      R.r.setPixelRatio(1); R.r.setSize(w, h, false);
      R.cam.aspect = w / h; R.cam.updateProjectionMatrix();
      R.fx.pmat.uniforms.uScale.value = h / (2 * Math.tan(R.cam.fov * Math.PI / 360));
      R.update(this, 1e-4, 1e-4); R.render();
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const g = c.getContext('2d');
      const gl = R.r.getContext(), px = new Uint8Array(w * h * 4);
      gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px); // works even when the page is hidden
      const img = g.createImageData(w, h);
      for (let y = 0; y < h; y++) img.data.set(px.subarray((h - 1 - y) * w * 4, (h - y) * w * 4), y * w * 4);
      g.putImageData(img, 0, 0);
      g.drawImage(this.ui.cv, 0, 0, w, h);
      const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.9));
      R.r.setPixelRatio(R.pr); R.resize();
      await fetch('/__shot?name=' + name, { method: 'POST', body: blob });
      return name;
    }

    // ------------------------------------------------------------ loop
    frame(now, bg) {
      if (!bg) requestAnimationFrame((t) => this.frame(t));
      if (!bg && this.lastBg && now - this.lastBg < 50) { this.last = now; }
      // online keeps real time even when the browser ticks slowly, so the two players don't drift apart
      const dt = Math.min(this.kind === 'online' ? 0.25 : 0.05, (now - this.last) / 1000); if (!bg && !document.hidden) this.R.perf((now - this.last) / 1000); this.last = now;
      if (this.camp) { this.pollPad(); this.camp.frame(dt); this.ui.draw(dt); return; } // CAMPAIGN: its own engine and scene
      const wmmTitle = S.WMM && (this.ui.name === 'title' || S.WMM.busy); if (S.WMM) document.body.classList.toggle('wmm-title', !!wmmTitle);
      if (wmmTitle) { this.pollPad(); S.WMM.frame(dt, this.R); this.ui.draw(dt); return; } // WHERE'S MY MAWASHI: the ninja title
      this.pollPad();
      let animDt = 0;
      if (this.frozen) { this.R.update(this, 1e-4, 1e-4); this.R.render(); this.ui.draw(0); return; }
      if (this.kind === 'showcase' && this.match) {
        for (const w of this.match.w) { w.t += dt; w.preT += dt; }
        const w0 = this.match.w[0];
        if (w0.pre && w0.preT > (S.PRE_DUR[w0.pre] || 1) + 0.6) w0.preT = 0;
        if (w0.st === 'win' && w0.t > 3) w0.t = 0;
        w0.f = Math.PI / 2 + Math.sin(performance.now() / 1400) * 0.5;
      } else if (this.match && !this.paused) {
        if (this.hitstop > 0) { this.hitstop -= dt; }
        else if (this.kind === 'online') { animDt = this.slot >= 0 ? this.onlineStepRB(dt) : this.onlineStep(dt); }
        else if (this.awaitGacha && this.match.phase !== 'over') { /* reading the gacha card */ }
        else {
          let ts = 1;
          if (this.slowT > 0) { this.slowT -= dt; ts = this.slowScale; }
          this.ts = ts;
          this.acc += dt * ts;
          let n = 0;
          while (this.acc >= S.DT && n < 10) { this.simStep(); this.acc -= S.DT; n++; }
          if (n >= 10) this.acc = 0;
          animDt = dt * ts;
        }
        if (this.tut) this.tut.update(dt); else if (this.kind === 'training') this.trainFlow(dt); else if (this.kind === 'online') this.onlineFlow(dt); else this.flow(dt);
      }
      this.excite *= Math.exp(-dt * 0.9);
      // a drawing glitch must never freeze the match: log it once and keep playing
      try { this.R.update(this, animDt, dt); } catch (err) { if (!this.drawErr) { this.drawErr = true; console.error(err); } }
      let slide = 0; for (const v of this.R.views) slide += v.slideAmt || 0;
      this.audio.slide(this.paused ? 0 : slide * 0.4);
      this.updateHints();
      if (S.touchState) {
        const playing = this.mode === 'game' && !this.ui.name && !!this.match && this.kind !== 'showcase';
        const meIdx = this.kind === 'online' ? this.slot : 0;
        S.touchState(playing, playing && this.match.skills && meIdx >= 0 && !!this.match.skills[meIdx]);
      }
      const m = this.match;
      if (m && this.kind !== 'showcase') {
        const me = this.viewerIdx >= 0 ? m.w[this.viewerIdx] : null;
        const bl = me && me.fxs.blind > 0;
        this.ui.blind(bl && Math.random() > 0.08, bl);
        if (m.w.some((w) => w.fxs.quake > 0)) this.R.shake(0.1);
        this.screenFx(m, me);
      } else { this.ui.blind(false); this.screenFx(null, null); }
      if (this.rematchT > 0 && this.ui.name === 'result') {
        this.rematchT -= dt;
        const el = document.getElementById('rmc'); if (el) el.textContent = '(' + Math.ceil(this.rematchT) + ')';
        if (this.rematchT <= 0) this.menuAction('rematch');
      }
      if (!bg && !(this.ui.name && S.OPAQUE_SCREENS.includes(this.ui.name))) this.R.render();
      this.ui.draw(dt);
    }

    simStep() {
      for (const ai of this.ais) ai.step(S.DT);
      for (const c of this.ctrls) c.update(S.DT);
      S.kb.flush();
      this.match.step(S.DT);
      this.handleEvents();
      if (this.kind === 'online') this.onlineRounds();
    }

    // clinch hint next to a human player who is locked up
    updateHints() {
      const m = this.match;
      let show = false, x = 0, y = 0, html = '';
      const hi = this.kind === 'pvp' || this.kind === 'attract' || this.kind === 'showcase' ? -1 : this.kind === 'online' ? this.slot : 0;
      const human = m && hi >= 0 ? m.w[hi] : null;
      if (human && this.settings.hints && this.mode === 'game' && !this.paused && m.phase === 'fight') {
        if (m.clinch && human.clinch && !m.clinch.tech) {
          // tug-of-war: the marker sits in the middle when the grips are even and slides your way as you win
          const c = m.clinch, gi = c.grip[human.idx], go = c.grip[human.opp.idx], pct = Math.round(Math.max(4, Math.min(96, 50 + 38 * (gi - go))));
          const ready = (k) => { const e = c.evalTech(human, k); return e.ok && e.sc > 0.34; };
          html = '<span class="gripm"><em>YOU</em><span class="gbar' + (gi - go > 0.6 ? ' win' : gi - go < -0.6 ? ' lose' : '') + '"><i style="width:' + pct + '%"></i><u></u></span><em>THEM</em>' +
            (c.type[human.idx] === 'inside' ? '<b>INSIDE</b>' : '') + '</span><span class="ready"><s' + (ready('trip') ? ' class="on"' : '') + '>TRIP</s><s' + (ready('throw') ? ' class="on"' : '') + '>THROW</s></span>' + this.clinchTip(c, human);
        }
        else if (!m.clinch) {
          // outside the grapple: a counter tip for what they are doing right now, held a moment so it can be read
          const t = this.counterTip(m, human);
          if (t) { this.ctTip = t; this.ctUntil = m.time + 0.8; }
          if (this.ctTip && m.time < this.ctUntil) html = this.ctTip; else this.ctTip = null;
        }
        if (html) { const p = this.R.project(human.x, 0, human.z); show = true; x = p.x; y = p.y + 40; }
      } else this.ctTip = null;
      this.ui.clinchHint(show, x, y, html);
    }

    // what to press against what they are doing (outside the grapple)
    counterTip(m, me) {
      const o = me.opp, J = '<kbd>J</kbd>', K = '<kbd>K</kbd>', Lk = '<kbd>L</kbd>';
      if (me.st === 'teeter') return '<b>TEETERING!</b> Hold toward the <b>middle</b> of the ring to stay in';
      if (o.st === 'teeter') return '<b>THEY ARE TEETERING!</b> Give them a push ' + J + ' before they recover';
      const dx = o.x - me.x, dz = o.z - me.z, d = Math.hypot(dx, dz) || 1, gap = d - me.r - o.r;
      const toMe = -(o.vx * dx + o.vz * dz) / d;
      if (o.fxs && (o.fxs.chicken > 0 || o.fxs.ball > 0)) return null;
      if ((o.st === 'charge' || (o.st === 'dash' && toMe > 3)) && gap < 3) return '<b>CHARGE!</b> Hold away + ' + J + ' slap down &nbsp;·&nbsp; side + ' + Lk + ' dodge';
      if (o.st === 'palm' && (o.flurry || 0) >= 3 && gap < 1) return '<b>FLURRY!</b> ' + Lk + ' (no direction) parry &nbsp;·&nbsp; away + ' + J + ' slap down';
      if (o.st === 'wind' && gap < 1.2) return '<b>WIND-UP!</b> ' + J + ' now to interrupt';
      if (['recover', 'overrun', 'stun', 'stumble'].includes(o.st) && gap < 1.4) return '<b>OPEN!</b> ' + J + ' push &nbsp;·&nbsp; ' + K + ' grab';
      const edge = S.RING_R - Math.hypot(me.x, me.z);
      if (edge < 1.0 && o.contact && o.fwdIn > 0.5) return '<b>ON THE EDGE!</b> Side + ' + Lk + ' to slip out';
      return null;
    }

    // one tip at a time, picked for the situation
    clinchTip(c, me) {
      const o = me.opp, s = c.sg(me), K = '<kbd>K</kbd>', J = '<kbd>J</kbd>', Lk = '<kbd>L</kbd>';
      if (me.kArm && me.input.grab.held && !c.lift) {
        if (c.swing && c.swing.w === me) return 'Swinging! Let go of ' + K + ' to <b>THROW</b>' + (c.swing.swept > 2.4 ? ' — full spin!' : '');
        const [tw, sd] = c.inputDir(me);
        if (Math.abs(tw) > 0.35 || Math.abs(sd) > 0.35) return tw > 0.35 ? 'Let go of ' + K + ' to <b>TRIP</b> their leg' : 'Point where you want them to swing';
        return '<b>Point anywhere</b> to swing them round you · let go of ' + K + ' to throw';
      }
      if (c.lift) { const left = Math.max(0, c.lift.w.stam); const bar = '<span class="wbar"><i style="width:' + Math.round(left * 100) + '%"></i></span>'; return c.lift.w === me ? 'Walk them out of the ring · ' + K + ' slam them down ' + bar : '<b>WRIGGLE!</b> Mash any button to break free ' + bar; }
      if (c.rear === me) return 'You are behind them! ' + J + ' shove them out';
      if (c.rear) return 'They are behind you! Hold any direction to turn around';
      // being grabbed: how to get out, first
      // only when they are really aiming a move (K held and pointing) or already swinging you
      const oI = o.input, oAim = o.kArm && oI && oI.grab && oI.grab.held ? c.inputDir(o) : null;
      const swinging = c.swing && c.swing.w === o && c.swing.swept > 0.15;
      if (swinging || (oAim && (Math.abs(oAim[0]) > 0.35 || Math.abs(oAim[1]) > 0.35))) {
        const what = swinging || !oAim || Math.abs(oAim[1]) > 0.35 || oAim[0] < -0.35 ? 'THROW' : 'LEG TRIP';
        return '<b>' + what + ' COMING!</b> ' + Lk + ' slip out &nbsp;·&nbsp; ' + J + ' shove off';
      }
      if (c.b === me && c.t < (this.match.techWin || 0.38)) return '<b>GRABBED!</b> Tap ' + K + ' now to break the grip';
      const myEdge = S.RING_R - Math.hypot(me.x, me.z), oEdge = S.RING_R - Math.hypot(o.x, o.z);
      const pushedBack = -s * c.v > 0.3;
      if (pushedBack && myEdge < 1.3) return 'Near the edge! Hold ' + K + ' and <b>point behind you</b> to swing them out';
      if (pushedBack || c.tow[o.idx] > 0.3) return 'They are pushing: hold ' + K + ' and <b>point behind you</b> to swing them past';
      const tr = c.evalTech(me, 'trip');
      if (tr.ok && tr.sc > 0.34) return '<b>TRIP READY!</b> Hold ' + K + ', point at them, let go';
      if (oEdge < 1.6) return '<b>Hold toward them</b> to drive them out';
      const tips = ['K up: <b>hold toward them</b> to drive them back and win the grip', '<b>Hold ' + K + '</b> = move mode (throw, spin, trip) · K up = push and drag', 'Let go of the stick to keep your elbows tight: their grip stops growing', 'Hold ' + K + ' and <b>point</b>: they swing round you · let go to throw', 'Hold ' + K + ', point <b>at them</b>, let go: leg trip', 'Hold ' + K + ' a moment, no aim, let go: lift',
        'Want out? ' + J + ' shove off &nbsp;·&nbsp; ' + Lk + ' slip back',
        (c.b === me ? 'They grabbed you, but you can fight back: ' : '') + 'hold ' + K + ' with no aim to lift, or hold ' + K + ' and point to throw'];
      return tips[Math.floor(c.t / 2.5) % tips.length];
    }

    recordText() {
      const r = S.profile.record(this.names[0], this.names[1]);
      return r[0] + '  –  ' + r[1]; // just the score: names next to numbers read as "PLAYER 1 1"
    }
    contKey(i) { return this.kind === 'pvp' && i === 1 ? '1 or Enter' : 'J or Enter'; }
    confirmGacha() {
      if (!this.awaitGacha || performance.now() < this.gachaReadyAt) return false;
      this.awaitGacha = false; S.kb.flush(); this.ui.hideGacha(); this.audio.blip(true); return true;
    }
    skillKey(i) { return this.kind === 'pvp' ? (i === 0 ? 'Space' : 'Num 0') : 'Space'; }
    refreshSkills() {
      const m = this.match; if (!m) return;
      this.ui.setSkills(m.skills, [false, this.kind === 'cpu' && !(m.peek && m.peek[0])], [this.skillKey(0), this.skillKey(1)]);
    }
    onSkill(e) {
      const sk = S.Skills.BY[e.id], w = e.w, R = this.R, ui = this.ui, A = this.audio;
      this.refreshSkills(); if (this.kind === 'training') this.trainPanel();
      if (!sk) return; // a fake (from COPYCAT) has its own effect
      const p = this.scr(w.x, w.z, 2.6);
      if (this.kind !== 'attract') ui.callout(sk.name, p.x, p.y - 40, 'skill');
      A.whoosh(0.5); A.cheer(0.6, 1.0); this.excite = 1.2;
      R.fx.dust(w.x, 0.05, w.z, 10, 0.4, 0.9, 0.4);
      if (e.id === 'blind') { ui.flash('#ffffff', 0.5); }
      if (e.id === 'slow' || e.id === 'freeze' || e.id === 'trap') this.slowmo(0.5, 0.25);
      if (e.id === 'giant' || e.id === 'invuln' || e.id === 'torpedo') { R.shake(0.25); R.kick(0.06); }
      if (e.id === 'smoke') A.whoosh(0.8);
      if (e.id === 'gale') { A.whoosh(1.4); R.shake(0.15); }
    }
    // full-screen skill effects: security camera, spotlight, controller disconnected
    screenFx(m, me) {
      const live = m && this.kind !== 'attract' && this.kind !== 'showcase';
      // SPOTLIGHT: total blackout except the one pool of light
      const sp = live && m.objs.find((o) => o.type === 'spot');
      const cv = document.getElementById('spot');
      if (sp) {
        if (cv.width !== innerWidth || cv.height !== innerHeight) { cv.width = innerWidth; cv.height = innerHeight; }
        cv.classList.add('on');
        const g = cv.getContext('2d'), lit = sp.t < 2 ? sp.owner.opp : sp.owner, victim = sp.owner.opp;
        const p = this.R.project(lit.x, 1.0, lit.z), q = this.R.project(lit.x + 1.4, 1.0, lit.z), rad = Math.max(60, Math.abs(q.x - p.x)) * 1.1;
        const k = Math.min(1, sp.t / 0.2) * Math.min(1, (sp.dur - sp.t) / 0.3);
        g.globalCompositeOperation = 'source-over'; g.clearRect(0, 0, cv.width, cv.height);
        g.fillStyle = 'rgba(0,0,0,' + k + ')'; g.fillRect(0, 0, cv.width, cv.height);
        g.globalCompositeOperation = 'destination-out';
        const gr = g.createRadialGradient(p.x, p.y, rad * 0.55, p.x, p.y, rad); gr.addColorStop(0, 'rgba(0,0,0,1)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = gr; g.beginPath(); g.arc(p.x, p.y, rad, 0, 7); g.fill();
        g.globalCompositeOperation = 'source-over';
        if (!this.spotOn) { this.spotOn = true; this.audio.thump(10); }
      } else if (cv && cv.classList.contains('on')) { cv.classList.remove('on'); this.spotOn = false; }
      // CONVENIENCE STORE: the shop menu while you're inside, and the shop's health over the building
      const shop = live && m.objs.find((o) => o.type === 'konbini');
      const su = document.getElementById('shopUi'), sh = document.getElementById('shopHp');
      const inside = shop && me && shop.owner === me && me.inShop;
      su.classList.toggle('on', !!inside);
      if (inside) {
        su.querySelector('.sh-hp i').style.width = (shop.hp / 10) + '%';
        su.querySelector('.sh-wallet').textContent = 'Wallet ' + S.fmtYen(S.profile.yen);
        su.querySelector('[data-shop="buy"]').classList.toggle('poor', S.profile.yen < this.SHOP_PRICE);
        const L = this.shopList(), it = L[((this.shopI || 0) % L.length + L.length) % L.length];
        su.querySelector('.sh-n').textContent = it.name; su.querySelector('.sh-d').textContent = it.desc;
        su.querySelector('.sh-c').textContent = (((this.shopI || 0) % L.length + L.length) % L.length + 1) + ' / ' + L.length + '  ·  ‹ › to browse';
        su.querySelector('.k-buy').textContent = S.keyName(S.mainKey('push')); su.querySelector('.k-leave').textContent = S.keyName(S.mainKey('grab'));
      }
      if (shop && shop.t < shop.dur - 0.05) {
        const p = this.R.project(shop.x, 1.9, shop.z);
        sh.classList.add('on'); sh.style.left = p.x + 'px'; sh.style.top = p.y + 'px'; sh.querySelector('i').style.width = (shop.hp / 10) + '%';
      } else sh.classList.remove('on');
      this.shopObj = inside ? shop : null;
      // CONTROLLER DISCONNECTED: the full-screen fake error only for the person it hit (when they are watching
      // this screen); everyone else just sees a tag over the frozen wrestler
      const un = live && m.w.find((w) => w.fxs.unplug > 0);
      const ue = document.getElementById('unplug');
      const mine = !!un && this.kind !== 'pvp' && un.idx === this.viewerIdx;
      ue.classList.toggle('on', mine);
      if (mine) {
        ue.querySelector('.up-s').textContent = 'Your controller lost connection. Reconnecting…';
        ue.querySelector('.up-bar i').style.width = (100 * (1 - un.fxs.unplug / 1.5)) + '%';
      }
      if (un && !mine && this.unplugTag !== un) { const p = this.scr(un.x, un.z, 2.6); this.ui.callout('CONTROLLER DISCONNECTED', p.x, p.y, 'small'); }
      this.unplugTag = un && !mine ? un : null;
    }
    get SHOP_PRICE() { return 50000; }
    shopList() { return S.Skills.LIST.filter((s) => s.id !== 'konbini'); } // every skill on the shelves
    shopAction(a) {
      const shop = this.shopObj; if (!shop || shop.bought || shop.leave) return;
      if (a === 'buy') {
        if (S.profile.yen < this.SHOP_PRICE) { this.audio.blip(false); const p = this.scr(shop.x, shop.z, 2.2); this.ui.callout('NOT ENOUGH YEN', p.x, p.y, 'gold'); return; }
        S.profile.earn(-this.SHOP_PRICE); this.ui.setYen();
        const L = this.shopList(); shop.bought = L[((this.shopI || 0) % L.length + L.length) % L.length].id; this.audio.blip(true);
      } else if (a === 'prev' || a === 'next') { this.shopI = (this.shopI || 0) + (a === 'next' ? 1 : -1); this.audio.blip(false); }
      else { shop.leave = true; this.audio.blip(false); }
    }
    slowmo(scale, dur) { if (this.slowT <= 0 || scale <= this.slowScale) { this.slowScale = scale; this.slowT = dur; } }
    stop(sec) { this.hitstop = Math.max(this.hitstop, sec); }
    scr(x, z, y) { return this.R.project(x, y === undefined ? 1.2 : y, z); }

    flow(dt) {
      const m = this.match;
      if (m.phase === 'fight') {
        // the referee calls "nokotta!" (still in!) while someone survives on the straw
        this.nokottaT -= dt;
        for (const w of m.w) {
          if (RR - Math.hypot(w.x, w.z) < 0.7 && w.contact && this.nokottaT <= 0) {
            this.nokottaT = 1.0;
            const p = this.scr(this.R.ref.x, this.R.ref.z, 2.2);
            if (this.kind !== 'attract') this.ui.callout('NOKOTTA!', p.x, p.y, 'ref');
            this.excite = Math.min(1.2, this.excite + 0.3);
            this.audio.cheer(0.35, 0.7);
          }
        }
      }
      if (m.phase !== 'over') return;
      this.overT += dt;
      const r = m.result;
      if (!this.kmShown && this.overT > 0.4) {
        this.kmShown = true;
        if (this.kind !== 'attract') this.showKm(r, this.winLabel(r.winner.idx));
        this.ui.setWins(m.wins, this.need);
      }
      if (this.overT > 1.0) this.R.cs.focusW *= Math.exp(-dt * 2);
      if (this.awaitGacha && this.overT > 2.4) this.ui.hideKimarite();
      if (m.overT > 2.6 && this.overT > 2.0 && !this.matchOver && !this.awaitGacha && !this.bnrGo) { // game-clock time, so slow-motion never cuts the bow short
        const end = !!this.matchEnd(m);
        if (this.bannerKind() && !end) { // the result card appears straight away; banners only between rounds
          // banners flood in; the next round is set up underneath once the screen is covered
          this.bnrGo = true;
          S.Banners.flood(end ? { hold: 0.2, speed: 0.95, onCovered: () => { this.bnrGo = false; if (this.match === m) this.advanceRound(); } }
            : { hold: 0.1, speed: 1.1, onCovered: () => { this.bnrGo = false; if (this.match === m) this.advanceRound(); } });
        } else this.advanceRound();
      }
    }
    // match over? with a third wrestler, three single points (three rounds) is a draw
    endless() { return this.kind === 'cpu' && this.settings.endless; }
    matchEnd(m) {
      if (this.endless()) return null; // non-stop: bouts keep coming until you quit
      const t3 = m.third ? m.third.wins : 0;
      if (m.wins[0] >= this.need) return { wi: 0 };
      if (m.wins[1] >= this.need) return { wi: 1 };
      if (t3 >= this.need) return { third: true };
      if (m.third && m.wins[0] + m.wins[1] + t3 >= this.need * 2 - 1) return { draw: true };
      return null;
    }
    bannerKind() { return this.kind === 'cpu' || this.kind === 'boss' || this.kind === 'pvp' || this.kind === 'online'; }
    advanceRound() {
      const m = this.match, r = m.result;
      {
        this.ui.hideKimarite();
        this.R.focus(0, 0, 0);
        const best = Math.max(m.wins[0], m.wins[1]), fin = this.matchEnd(m);
        if (fin && this.kind === 'boss' && fin.wi !== undefined) { this.matchOver = true; this.ui.hideBanner(); this.leaveBoss(fin.wi === 0 ? 'won' : 'lost'); return; }
        if (fin && (fin.third || fin.draw) && this.kind !== 'attract') {
          // the challenger took it, or everyone has one point: nobody wins; a draw hands back the bet
          this.matchOver = true;
          const stake = this.kind === 'cpu' ? this.stake || 0 : 0; this.stake = 0;
          if (fin.draw && stake) S.profile.earn(stake);
          this.ui.setYen();
          const ta = S.ARCH[m.third.arch];
          this.ui.show('result', { arch: fin.draw ? { accent: '#f0c35a' } : ta, head: fin.draw ? 'DRAW' : this.kind === 'cpu' ? 'YOU LOSE' : 'CHALLENGER WINS', who: fin.draw ? '' : ta.name, score: m.wins[0] + ' – ' + m.wins[1] + ' – ' + m.third.wins, record: this.recordText(), yen: 0, lost: fin.draw ? 0 : stake });
          this.rematchT = 5; this.ui.hideBanner(); this.audio.roar();
        } else if (fin && this.kind !== 'attract') {
          this.matchOver = true;
          const wi = fin.wi;
          const humanWon = this.kind === 'pvp' || wi === 0;
          const stake = this.kind === 'cpu' ? this.stake || 0 : 0; this.stake = 0;
          const odds = S.BET_ODDS[this.settings.difficulty] || 1;
          const yen = humanWon && this.kind !== 'tutorial' ? 100000 + stake * odds : 0;
          if (yen) S.profile.earn(yen + (humanWon ? stake : 0));
          const rec = S.profile.record(this.names[0], this.names[1]); rec[wi]++;
          // win streak against the CPU
          if (this.kind === 'cpu') { const P = S.profile; P.streak = wi === 0 ? P.streak + 1 : 0; P.bestStreak = Math.max(P.bestStreak, P.streak); P.save(); }
          this.ui.setRecord(this.recordText()); this.ui.setYen();
          this.ui.show('result', { arch: m.w[wi].a, head: this.kind === 'cpu' ? (wi === 0 ? 'YOU WIN' : 'YOU LOSE') : 'WINNER', who: this.kind === 'cpu' ? '' : this.names[wi], score: m.wins[0] + ' – ' + m.wins[1], record: this.recordText(), yen, lost: humanWon ? 0 : stake, streak: this.kind === 'cpu' ? S.profile.streak : null, best: S.profile.bestStreak });
          this.rematchT = 5;
          this.ui.hideBanner();
          this.audio.roar();
        } else {
          if (this.endless()) {
            // non-stop: every bout you win pays out, and the streak runs on
            if (!r.draw && !r.third && r.winner.idx === 0) { S.profile.earn(50000); this.ui.setYen(); this.nsStreak = (this.nsStreak || 0) + 1; this.nsBest = Math.max(this.nsBest || 0, this.nsStreak); }
            else if (!r.draw) this.nsStreak = 0;
            this.ui.setWins(m.wins, this.need);
          } else if (best >= this.need) { m.wins = [0, 0]; m.history = []; m.third = null; this.ui.setWins(m.wins, this.need); }
          if (r.draw) m.round--; // fought again
          m.newRound();
          this.handleEvents();
        }
      }
    }

    // ------------------------------------------------------------ events -> feedback
    handleEvents() {
      const m = this.match, fx = this.R.fx, A = this.audio, ui = this.ui, R = this.R;
      const evs = m.events; m.events = [];
      const quiet = this.kind === 'attract' || this.kind === 'showcase';
      const tut = this.kind === 'tutorial';
      for (const e of evs) {
        if (this.snap && !this.snapAt && e.type === this.snap && m.time > this.snapAfter && (!this.snapPow || (e.power || 0) >= this.snapPow)) {
          this.snapAt = performance.now();
          setTimeout(() => { this.frozen = true; document.title = 'SNAP'; }, +(new URLSearchParams(location.search).get('delay') || 60));
        }
        if (this.tut) this.tut.onEvent(e);
        this.trackCombo(e, quiet);
        switch (e.type) {
          case 'round':
            if (e.round === 1) for (const v of R.views) v.resetJacket();
            R.clearThrown();
            this.overT = 0; this.kmShown = false; this.palmChain = [0, 0];
            fx.clearDecals();
            R.ref.set('ready');
            if (!quiet) { ui.setRound(e.round); if (!S.Banners.busy) ui.banner('READY', 'ready'); }
            break;
          case 'clap': {
            const w = e.w; A.clap(); R.views[w.idx] && (R.views[w.idx].clapT = 0);
            fx.spark(w.x + w.fx * 0.5, 1.3 * w.a.scale, w.z + w.fz * 0.5, 0.5);
            break;
          }
          case 'stompUp': A.whoosh(0.3); break;
          case 'taunt': if (e.kind === 'salt') A.whoosh(0.4); else if (e.kind && e.kind.indexOf('x_') === 0) { A.cheer(0.45, 0.9); if (e.kind === 'x_cry') A.thump(4); if (e.kind === 'x_drum') A.slap(3); this.excite = Math.max(this.excite, 0.7); } break;
          case 'skillUse': this.onSkill(e); break;
          case 'peek': this.refreshSkills(); if (this.kind !== 'attract' && (e.w.idx === 0 || this.kind === 'pvp')) this.ui.peek(e.w.idx, e.theirs, e.mine, this.skillKey(e.w.idx), e.fakeOf); break;
          case 'rewind': {
            A.whoosh(0.9); if (this.kind !== 'attract') ui.vhs(true); break;
          }
          case 'unplug': A.blip(false); A.blip(false); break;
          case 'confused': { const p = this.scr(e.w.x, e.w.z, 2.7); if (!quiet) ui.callout('?', p.x, p.y, 'big'); break; }
          case 'shopIn': { const p = this.scr(e.x, e.z, 1.8); if (!quiet) ui.callout('WELCOME!', p.x, p.y, 'gold'); A.blip(true); break; }
          case 'shopHit': { A.slap(6); this.R.fx.dust(e.x, 0.6, e.z, 6, 0.4, 0.6, 0.3); const p = this.scr(e.x, e.z, 1.7); if (!quiet) ui.callout('-' + e.dmg, p.x + (Math.random() - 0.5) * 60, p.y, 'small'); break; }
          case 'shopBreak': { fx.burst(e.x, e.z, 14); A.thump(12); R.shake(0.4); const p = this.scr(e.x, e.z, 1.6); if (!quiet) ui.callout('SHOP SMASHED!', p.x, p.y, 'big'); this.R.shake(0.3); break; }
          case 'shopBuy': { this.refreshSkills(); const p = this.scr(e.x, e.z, 2.4); if (!quiet) ui.callout((S.Skills.BY[e.id] || {}).name + '!', p.x, p.y, 'skill'); A.cheer(0.6, 1); break; }
          case 'shopBuff': { const nm = { giant: 'GIANT!', invuln: 'INVINCIBLE!', absorb: 'IRON BODY!', haste: 'ENERGY DRINK!' }[e.buff]; const p = this.scr(e.x, e.z, 2.4); if (!quiet) ui.callout(nm, p.x, p.y, 'skill'); A.blip(true); A.cheer(0.6, 1); break; }
          case 'eat': { const p = this.scr(e.x, e.z, 2.4); if (!quiet) ui.callout(e.good ? 'GIANT STRENGTH!' : 'FOOD POISONING!', p.x, p.y, e.good ? 'skill' : 'big'); A.whoosh(0.3); if (e.good) R.shake(0.2); break; }
          case 'boltWarn': A.blip(false); break;
          case 'bolt': { ui.flash('#e8f6ff', e.hit ? 0.55 : 0.3); A.thump(16); A.clack(); R.shake(e.hit ? 0.6 : 0.3); fx.burst(e.x, e.z, 12); fx.spark(e.x, 0.6, e.z, 2.4); if (e.hit) { const p = this.scr(e.x, e.z, 2.2); if (!quiet) ui.callout('ZAPPED!', p.x, p.y, 'big'); } break; }
          case 'molotovBurst': { fx.burst(e.x, e.z, 14); fx.spark(e.x, 0.5, e.z, 2.2); A.clack(); A.whoosh(1.0); A.thump(8); R.shake(0.3); const p = this.scr(e.x, e.z, 1.2); if (!quiet) ui.callout('FIRE!', p.x, p.y, 'big'); break; }
          case 'thirdIn': { const p = this.scr(0, 0, 1); if (!quiet) ui.callout('A CHALLENGER APPEARS!', p.x, p.y - 60, 'big'); A.roar(); A.taiko && A.taiko(); this.ui.setWins(m.wins, this.need); break; }
          case 'thirdHit': A.slap(4); fx.spark(e.x, 1.3, e.z, 0.9); break;
          case 'thirdOut': { const p = this.scr(e.x, e.z, 1.6); if (!quiet) ui.callout('CHALLENGER OUT!', p.x, p.y, 'gold'); A.cheer(0.8, 1); break; }
          case 'scoreReset': { ui.setWins(m.wins, this.need); const p = this.scr(0, 0, 1); if (!quiet) ui.callout('SCORE RESET!', p.x, p.y - 60, 'big'); A.whoosh(0.6); A.cheer(0.8, 1.2); break; }
          case 'potatoOn': { const p = this.scr(e.w.x, e.w.z, 2.6); if (!quiet) ui.callout('HOT POTATO!', p.x, p.y, 'big'); A.clack(); break; }
          case 'potatoPass': { const p = this.scr(e.x, e.z, 2.4); if (!quiet) ui.callout('PASS!', p.x, p.y, 'gold'); A.slap(4); A.cheer(0.5, 0.8); break; }
          case 'clawGrab': { const p = this.scr(e.x, e.z, 2.6); if (!quiet) ui.callout('GOT YOU!', p.x, p.y, 'big'); A.clack(); A.cheer(0.7, 1); break; }
          case 'clawDrop': { A.thump(6); fx.dust(e.x, 0.05, e.z, 10, 0.4, 0.8, 0.4); break; }
          case 'door': { fx.dust(e.x, 0.05, e.z, 10, 0.4, 0.8, 0.4); A.whoosh(0.3); A.clack(); break; }
          case 'copycat': { this.refreshSkills(); const p = this.scr(e.w.x, e.w.z, 2.6); if (!quiet) ui.callout('COPIED!', p.x, p.y, 'skill'); A.blip(true); break; }
          case 'fakeUse': { this.refreshSkills(); const p = this.scr(e.x, e.z, 2.4); if (!quiet) ui.callout('FAKE!', p.x, p.y, 'big'); fx.dust(e.x, 0.05, e.z, 8, 0.3, 0.5, 0.3); A.whoosh(0.2); break; }
          case 'knockSkill': { this.refreshSkills(); const p = this.scr(e.x, e.z, 1.6); if (!quiet) ui.callout('SKILL KNOCKED LOOSE!', p.x, p.y, 'big'); A.slap(8); break; }
          case 'pickup': { this.refreshSkills(); const p = this.scr(e.x, e.z, 1.8); if (!quiet) ui.callout((S.Skills.BY[e.id] || { name: 'FAKE' }).name + '!', p.x, p.y, 'skill'); A.blip(true); break; }
          case 'trainWarn': {
            if (quiet) break;
            clearInterval(this.bellT); let n = 0;
            this.bellT = setInterval(() => { A.blip(n % 2 === 0); if (++n >= 9) clearInterval(this.bellT); }, 230);
            const p = this.scr(0, 0, 1); ui.callout('TRAIN COMING!', p.x, p.y - 60, 'big'); break;
          }
          case 'trainGo': A.whoosh(1.4); A.thump(12); R.shake(0.6); break;
          case 'trainHit': { A.thump(16); R.shake(0.8); this.stop(0.08); const p = this.scr(e.x, e.z, 1.6); if (!quiet) ui.callout('TRAIN!', p.x, p.y, 'big'); break; }
          case 'crowdSave': { const p = this.scr(e.x, e.z, 2.2); if (!quiet) ui.callout('THE CROWD SAVES YOU!', p.x, p.y, 'big'); A.roar(); this.excite = 2; fx.dust(e.x, 0.05, e.z, 18, 0.8, 1.2, 0.5); R.shake(0.3); break; }
          case 'bump': { fx.ring(e.x, e.z, 1.6, 0.35); fx.spark(e.x, 0.8, e.z, 1.6); A.thump(6); A.clack(); R.shake(0.15); break; }
          case 'cyclone': A.whoosh(0.9); fx.dust(e.x, 0.05, e.z, 14, 0.4, 0.8, 0.45); break;
          case 'cycloneHit': { fx.burst(e.x, e.z, 10); A.thump(9); R.shake(0.25); this.stop(0.05); const p = this.scr(e.x, e.z, 1.6); if (!quiet) ui.callout('WHIRLED!', p.x, p.y, 'skill'); break; }
          case 'ballDash': A.whoosh(0.5); fx.dust(e.x, 0.05, e.z, 8, 0.3, 0.6, 0.35); break;
          case 'ballHit': { fx.burst(e.x, e.z, 12); A.thump(10); R.shake(0.3); this.stop(0.06); const p = this.scr(e.x, e.z, 1.6); if (!quiet) ui.callout('STRIKE!', p.x, p.y, 'skill'); break; }
          case 'fishHit': { A.slap(6); fx.dust(e.x, 0.05, e.z, 6, 0.3, 0.6, 0.3); const p = this.scr(e.x, e.z, 1.4); if (!quiet) ui.callout('SLAP!', p.x, p.y, 'gold'); break; }
          case 'bombHit': { A.clack(); fx.spark(e.x, 0.6, e.z, 1.1); break; }
          case 'slam': { fx.burst(e.x, e.z, 16); fx.ring(e.x, e.z, 2.4, 0.35); fx.dust(e.x, 0.05, e.z, 14, 0.7, 1.2, 0.5); A.thump(14); R.shake(0.5); R.kick(0.12); if (!quiet) this.stop(0.08); break; }
          case 'bigStomp': { A.thump(14); R.shake(0.45); R.kick(0.1); fx.dust(e.x, 0.05, e.z, 20, 0.6, 1.4, 0.5); break; }
          case 'waveHit': { A.thump(8); fx.burst(e.x, e.z, 10); break; }
          case 'snap': { const p = this.scr(e.x, e.z, 1.6); if (this.kind !== 'attract') ui.callout('SNAP!', p.x, p.y, 'skill'); A.clack(); A.thump(8); R.shake(0.2); fx.dust(e.x, 0.05, e.z, 8, 0.3, 0.6, 0.3); break; }
          case 'hyakuEnd': {
            if (this.kind === 'attract' || !e.n) break;
            if (e.hits >= e.n) { ui.combo('1000 HIT COMBO!', true); A.roar(); this.excite = 2; R.shake(0.3); }
            else ui.combo(e.hits * 25 + ' HITS', false);
            break;
          }
          case 'rewindEnd': { fx.ring(e.x, e.z, 3, 0.5); fx.spark(e.x, 1.0, e.z, 2.2); A.clack(); ui.vhs(false); break; }
          case 'sleep': { const p = this.scr(e.x, e.z, 2.4); if (this.kind !== 'attract') ui.callout('Zzz…', p.x, p.y, 'skill'); A.whoosh(0.2); break; }
          case 'gulp': { const p = this.scr(e.x, e.z, 2.2); if (this.kind !== 'attract') ui.callout('GULP!', p.x, p.y, 'skill'); A.thump(6); R.kick(0.05); break; }
          case 'spit': {
            fx.burst(e.x, e.z, 16); fx.dust(e.x, 0.05, e.z, 14, 0.6, 1.4, 0.5); R.shake(0.35); A.thump(12); A.whoosh(0.4); this.slowmo(0.35, 0.4);
            const p = this.scr(e.x, e.z, 1.8); if (this.kind !== 'attract') ui.callout('PTOOEY!', p.x, p.y, 'skill'); break;
          }
          case 'boom': {
            fx.burst(e.x, e.z, 30); fx.ring(e.x, e.z, 5, 0.6); fx.spark(e.x, 1.0, e.z, 4); fx.dust(e.x, 0.05, e.z, 24, 1.2, 2.2, 0.8);
            R.shake(0.9 * e.k + 0.2); R.kick(0.2); ui.flash('#ffb040', 0.55); ui.impactFrame(120);
            A.thump(16); A.roar(); this.stop(0.12); this.slowmo(0.3, 0.7); this.excite = 2;
            const p = this.scr(e.x, e.z, 1.5); if (this.kind !== 'attract') ui.callout('BOOM!', p.x, p.y, 'skill');
            break;
          }
          case 'grabTech': {
            this.stop(0.05); this.slowmo(0.4, 0.2); A.slap(5); A.whoosh(0.3); fx.dust(e.x, 0.05, e.z, 8, 0.4, 0.6, 0.35); fx.spark(e.x, 1.4, e.z, 1.2);
            const p = this.scr(e.x, e.z); if (!quiet) ui.callout('TECH!', p.x, p.y - 80, 'teal'); break;
          }
          case 'techEscape': {
            this.slowmo(0.3, 0.25); A.whoosh(0.3); fx.dust(e.x, 0.05, e.z, 8, 0.4, 0.6, 0.35);
            const p = this.scr(e.x, e.z); if (!quiet) ui.callout('ESCAPED!', p.x, p.y - 80, 'teal'); break;
          }
          case 'parry': {
            this.stop(0.06); this.slowmo(0.3, 0.3); R.fx.spark(e.x, 1.4, e.z, 1.5); A.slap(6); A.thump(4);
            const p = this.scr(e.x, e.z); if (!quiet) ui.callout('PARRY!', p.x, p.y - 80, 'teal'); this.excite = 1; break;
          }
          case 'boost': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout('POWER ×' + (e.n + 1) + '!', p.x, p.y - 90, 'big'); this.slowmo(0.3, 0.3); R.shake(0.4); break; }
          case 'absorbCharge': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout('CHARGE ' + e.n, p.x, p.y - 70, 'small'); A.thump(3); break; }
          case 'slip': { const p = this.scr(e.x, e.z); if (!quiet) ui.callout('SLIP!', p.x, p.y - 60, 'gold'); A.whoosh(0.3); A.cheer(0.7, 1); fx.dust(e.x, 0.05, e.z, 6, 0.3, 0.5, 0.3); break; }
          case 'projHit': A.thump(2); fx.dust(e.x, 0.05, e.z, 3, 0.2, 0.3, 0.25); break;
          case 'poof': fx.dust(e.x, 0.05, e.z, 14, 0.5, 1.2, 0.5); A.whoosh(0.3); break;
          case 'refBreak': R.ref.set('go'); fx.dust(e.x, 0.05, e.z, 10, 0.5, 0.8, 0.4); A.clack(); break;
          case 'trapdoor': { this.slowmo(0.3, 0.6); R.shake(0.3); A.thump(10); const p = this.scr(e.x, e.z); if (!quiet) ui.callout('TRAPDOOR!', p.x, p.y - 60, 'big'); break; }
          case 'quakeDust': fx.dust(e.x + (Math.random() - 0.5), 0.05, e.z + (Math.random() - 0.5), 2, 0.3, 0.6, 0.3); break;
          case 'tauntHit': {
            const w = e.w, s2 = w.a.scale;
            if (e.kind === 'salt') { fx.salt(w.x + w.fx * 0.4, 1.7 * s2, w.z + w.fz * 0.4, w.fx, w.fz); A.cheer(0.5, 1); }
            else if (e.kind === 'faceSlap') { A.slap(4); fx.spark(w.x + w.fx * 0.25, 2.0 * s2, w.z + w.fz * 0.25, 0.5); }
            else if (e.kind === 'beltSlap') { A.slap(3); A.thump(2); }
            else if (e.kind === 'spread') A.cheer(0.3, 0.6);
            this.excite = Math.max(this.excite, 0.5);
            break;
          }
          case 'stomp': {
            const w = e.w; A.thump(6); R.shake(0.12);
            fx.burst(w.x, w.z, 5); fx.ring(w.x, w.z, 1.4, 0.3);
            this.excite = Math.max(this.excite, 0.6); A.cheer(0.4, 0.8);
            break;
          }
          case 'go':
            R.ref.set('go');
            if (!quiet) { ui.banner(tut ? 'PRESS J!' : 'HAKKEYOI!', 'go', tut ? 1.2 : 0.75); }
            if (!quiet) { A.hyoshigi(); setTimeout(() => A.taiko(), 90); } // the clappers mark the exact moment to go
            this.excite = 0.6;
            for (const w of m.w) if (w.tachiPow > 0.5) fx.dust(w.x, 0.05, w.z, 8, 0.4, 0.6, 0.35);
            break;
          case 'charge': {
            const w = e.w;
            fx.dust(w.x - w.fx * 0.4, 0.05, w.z - w.fz * 0.4, e.tachiai ? 14 : 8, 0.3, 0.9, 0.4, -w.fx * 2, -w.fz * 2);
            A.whoosh(0.3);
            break;
          }
          case 'palm': A.whoosh(0.1); break;
          case 'heavyGo': A.whoosh(0.2); break;
          case 'slapGo': A.whoosh(0.15); break;
          case 'dash': fx.dust(e.w.x, 0.05, e.w.z, 5, 0.3, 0.6, 0.3, -e.w.ddx * 2, -e.w.ddz * 2); A.scuff(); break;
          case 'brace': fx.dust(e.w.x, 0.05, e.w.z, 4, 0.5, 0.3, 0.3); A.scuff(); break;
          case 'hit': this.onHit(e); if (e.rapid && e.hits && this.kind !== 'attract') ui.combo(e.hits * 25 + ' HITS', false); break;
          case 'impact': this.onImpact(e); break;
          case 'deadlock': {
            this.stop(0.11); R.shake(0.45); R.kick(0.1);
            fx.burst(e.x, e.z, 14); fx.ring(e.x, e.z, 2.6, 0.4); fx.spark(e.x, 1.4, e.z, 2.2);
            const p = this.scr(e.x, e.z);
            ui.speedLines(p.x, p.y, 1.3, 0.3); ui.impactFrame(80);
            if (!quiet) ui.callout('CLASH!', p.x, p.y - 70, 'big');
            A.thump(12); A.cheer(0.8, 1.2); this.excite = 1.2;
            break;
          }
          case 'braceCounter': {
            this.stop(0.08); this.slowmo(0.3, 0.35); R.shake(0.3);
            fx.burst(e.x, e.z, 10); fx.spark(e.x, 1.3, e.z, 1.8);
            const p = this.scr(e.x, e.z);
            ui.speedLines(p.x, p.y, 1.1, 0.25); ui.impactFrame(60);
            if (!quiet) ui.callout('STOPPED!', p.x, p.y - 70, 'gold');
            A.thump(9); this.excite = 1;
            break;
          }
          case 'catch': {
            this.stop(0.07); this.slowmo(0.3, 0.55); R.shake(0.25); R.kick(0.1); R.focus(e.x, e.z, 0.8);
            fx.burst(e.x, e.z, 8); fx.spark(e.x, 1.3, e.z, 2);
            const p = this.scr(e.x, e.z);
            ui.speedLines(p.x, p.y, 1.3, 0.4, true);
            if (!quiet) ui.callout('CAUGHT!', p.x, p.y - 80, 'big');
            A.grab(); A.whoosh(0.5); A.cheer(0.9, 1.4); this.excite = 1.3;
            break;
          }
          case 'perfectDodge': {
            this.slowmo(0.28, 0.42); A.whoosh(0.4);
            const p = this.scr(e.w.x, e.w.z);
            if (!quiet) ui.callout(e.henka ? 'HENKA!' : 'DODGE!', p.x, p.y - 80, 'teal');
            fx.dust(e.w.x, 0.05, e.w.z, 8, 0.3, 0.8, 0.35);
            A.cheer(0.5, 0.8); this.excite = 0.9;
            break;
          }
          case 'whiff': if (!e.grab) { fx.dust(e.w.x, 0.05, e.w.z, 6, 0.4, 0.5, 0.35); A.scuff(); } break;
          case 'overcommit': {
            fx.dust(e.w.x, 0.05, e.w.z, 6, 0.3, 0.5, 0.3);
            const p = this.scr(e.w.x, e.w.z);
            if (!quiet) ui.callout('PULLED!', p.x, p.y - 70, '');
            A.scuff(); break;
          }
          case 'stumble': A.scuff(); break;
          case 'interrupt': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout('INTERRUPTED', p.x, p.y - 70, 'small'); break; }
          case 'clinch': {
            A.grab(); R.shake(0.08);
            fx.dust(e.x, 0.05, e.z, 8, 0.4, 0.5, 0.35);
            const p = this.scr(e.x, e.z);
            if (!quiet) ui.callout(e.rear ? 'FROM BEHIND!' : 'LOCKED!', p.x, p.y - 80, e.rear ? 'gold' : 'small');
            this.excite = Math.max(this.excite, 0.5);
            break;
          }
          case 'regrip': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout(e.level >= 2.25 ? 'STRONG GRIP' : 'GRIP +', p.x, p.y - 70, e.level >= 2.25 ? 'gold' : 'small'); A.grab(); break; }
          case 'burst': R.shake(0.15); fx.burst(e.x, e.z, 6); A.thump(5); break;
          case 'teeter': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout('TEETERING!', p.x, p.y - 80, 'gold'); A.scuff(); A.cheer(0.6, 1); this.excite = 1; break; }
          case 'gripWin': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout('GRIP WON!', p.x, p.y - 80, 'teal'); A.thump && A.thump(2); break; }
          case 'matta': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout(e.n >= 2 ? 'MATTA! You start late' : 'MATTA! False start', p.x, p.y - 80, 'gold'); A.whoosh(0.3); break; }
          case 'teeterSave': { const p = this.scr(e.w.x, e.w.z); if (!quiet) ui.callout('SAVED!', p.x, p.y - 80, 'teal'); A.cheer(0.9, 1.3); fx.dust(e.w.x, 0.05, e.w.z, 8, 0.4, 0.6, 0.35); break; }
          case 'chargeCancel': fx.dust(e.w.x, 0.05, e.w.z, 6, 0.3, 0.5, 0.3); A.scuff(); break;
          case 'swap': A.whoosh(0.3); fx.dust(e.x, 0.05, e.z, 6, 0.4, 0.5, 0.3); break;
          case 'liftFail': { const p = this.scr(e.x, e.z); if (!quiet) ui.callout(e.heavy ? 'TOO HEAVY!' : 'NO GRIP YET', p.x, p.y - 90, 'small'); A.scuff(); break; }
          case 'tech': {
            const p = this.scr(e.x, e.z);
            if (e.kind === 'utchari' && e.ok) {
              this.slowmo(0.22, 0.9); R.kick(0.18); R.focus(e.x, e.z, 1);
              ui.speedLines(p.x, p.y, 1.5, 0.5, true); A.whoosh(0.6); this.excite = 1.4;
            } else if (e.ok) { this.slowmo(0.45, 0.3); A.whoosh(0.35); R.kick(0.06); }
            else { A.scuff(); if (!quiet) ui.callout('FAILED', p.x, p.y - 70, 'small'); }
            break;
          }
          case 'techFail': break;
          case 'throw': if (this.R.stageId === 'taiko') A.taiko(); {
            const p = this.scr(e.x, e.z);
            fx.burst(e.x, e.z, 9); R.shake(0.22);
            const k = S.KIMARITE[e.name];
            if (k && !quiet) ui.callout(k[1] + '!', p.x, p.y - 90, 'big');
            A.thump(8); A.cheer(0.7, 1.2); this.excite = 1.1;
            break;
          }
          case 'lift': {
            this.slowmo(0.45, 0.35);
            const p = this.scr(e.o.x, e.o.z);
            if (!quiet) ui.callout('LIFTED!', p.x, p.y - 100, 'gold');
            A.grab(); A.cheer(0.6, 1.2); this.excite = 1;
            break;
          }
          case 'slam': fx.burst(e.x, e.z, 12); R.shake(0.3); A.thump(10); break;
          case 'struggle': case 'turnaround': A.scuff(); break;
          case 'disengage': fx.dust(e.w.x, 0.05, e.w.z, 5, 0.3, 0.5, 0.3); A.whoosh(0.15); break;
          case 'decided': this.onDecided(e); break;
        }
      }
    }

    // emergent combos: successful actions chained before the opponent lands anything
    trackCombo(e, quiet) {
      let who = null;
      if (e.type === 'hit' && e.kind !== 'slapWeak') who = e.w;
      else if (e.type === 'impact' && e.agg && e.power > 3) who = e.a;
      else if (['throw', 'catch', 'perfectDodge', 'braceCounter', 'lift', 'overcommit'].includes(e.type)) who = e.type === 'overcommit' ? e.w.opp : e.w;
      else if (e.type === 'clinch' && e.rear) who = e.w;
      else if (e.type === 'round') this.combo = [{ n: 0, t: -9 }, { n: 0, t: -9 }];
      if (!who || !this.match) return;
      if (!this.combo) this.combo = [{ n: 0, t: -9 }, { n: 0, t: -9 }];
      const t = this.match.time, c = this.combo[who.idx];
      c.n = t - c.t < 1.4 ? c.n + 1 : 1; c.t = t;
      this.combo[1 - who.idx].n = 0;
      if (c.n >= 2 && !quiet) {
        const p = this.scr(who.x, who.z, 2.6 * who.a.scale);
        this.ui.callout(c.n + ' HIT COMBO', p.x, p.y - 20, 'combo');
      }
    }

    onHit(e) {
      const fx = this.R.fx, A = this.audio, ui = this.ui, quiet = this.kind === 'attract';
      const y = 1.2 * (e.o ? e.o.a.scale : 1);
      if (e.kind === 'palm') {
        fx.spark(e.x, y, e.z, e.braced ? 0.6 : 0.9);
        fx.dust(e.o.x, 0.05, e.o.z, 3, 0.3, 0.4, 0.28);
        A.slap(e.power);
        this.stop(e.braced ? 0.02 : 0.035);
        this.R.shake(0.05);
        const i = e.w.idx; this.palmChain[i]++; this.palmChain[1 - i] = 0;
        if (this.palmChain[i] === 4 && !quiet) { const p = this.scr(e.x, e.z); ui.callout('TSUPPARI!', p.x, p.y - 80, ''); }
        if (e.special === 'harite' && !quiet) { const p = this.scr(e.x, e.z); ui.callout('FACE SLAP!', p.x, p.y - 70, 'big'); this.stop(0.09); A.slap(9); this.R.shake(0.25); fx.spark(e.x, 1.6, e.z, 1.8); }
      } else if (e.kind === 'heavy' || e.kind === 'slap') {
        const big = e.power > 4.5 || e.big;
        fx.spark(e.x, y, e.z, big ? 1.8 : 1.2); fx.burst(e.o.x, e.o.z, e.power);
        if (big) fx.ring(e.o.x, e.o.z, 2, 0.3);
        A.thump(e.power * 1.3); A.slap(e.power);
        if (e.special === 'nodowa' && !quiet) { const p = this.scr(e.x, e.z); ui.callout('THROAT PUSH!', p.x, p.y - 100, 'big'); this.stop(0.1); this.slowmo(0.35, 0.35); A.thump(12); A.slap(7); this.R.shake(0.4); fx.spark(e.x, 1.7, e.z, 2.4); fx.ring(e.x, e.z, 2.2, 0.35); }
        this.stop(big ? 0.075 : 0.045); this.R.shake(big ? 0.3 : 0.14); this.R.kick(big ? 0.05 : 0.02);
        if (big) this.slowmo(0.35, 0.25);
        if (e.special === 'dizzySlap' || e.special === 'turnSlap') { const p = this.scr(e.x, e.z); if (!quiet) ui.callout(e.special === 'dizzySlap' ? 'DIZZY!' : 'TURNED AROUND!', p.x, p.y - 90, 'gold'); }
        if (big) {
          const p = this.scr(e.x, e.z);
          ui.speedLines(p.x, p.y, 1, 0.2); if (e.kind === 'slap') ui.impactFrame(60);
          if (e.kind === 'slap' && !quiet) ui.callout('SLAPPED DOWN!', p.x, p.y - 80, 'big');
        }
        this.excite = Math.max(this.excite, big ? 0.9 : 0.5);
      } else if (e.kind === 'slapWeak') { A.slap(1); fx.spark(e.x, y, e.z, 0.5); }
      if (e.zone === 'rear' && !quiet && e.kind !== 'slapWeak') { const p = this.scr(e.x, e.z); ui.callout('FROM BEHIND!', p.x, p.y - 60, 'gold'); }
    }

    onImpact(e) {
      const fx = this.R.fx, A = this.audio, ui = this.ui;
      const p = e.power;
      if (p < 1.5) return;
      fx.burst(e.x, e.z, p);
      if (p > 3) fx.spark(e.x, 1.3, e.z, Math.min(2.2, 0.6 + p * 0.18));
      if (p > 5) fx.ring(e.x, e.z, 1.2 + p * 0.15, 0.32);
      this.R.shake(Math.min(0.5, p * 0.045));
      this.stop(Math.min(0.085, p * 0.009));
      A.thump(p);
      if (p > 6.5) {
        const s = this.scr(e.x, e.z);
        ui.speedLines(s.x, s.y, Math.min(1.5, p / 7), 0.24); ui.impactFrame(55); this.R.kick(0.06);
        this.excite = Math.max(this.excite, 0.9);
      }
    }

    onDecided(r) {
      this.ui.vhs(false);
      if (this.R.stageId === 'taiko') { this.audio.taiko(); setTimeout(() => this.audio.taiko(), 160); } // the drum booms as they land
      const ui = this.ui, A = this.audio, R = this.R, L = r.loser, W = r.winner;
      if (r.draw || r.third) {
        this.overT = 0; this.kmShown = false; this.excite = 1.6;
        R.focus((L.x + W.x) / 2, (L.z + W.z) / 2, 1); R.ref.set('go'); A.roar();
        const m = this.match;
        if (S.profile.rules === 'gacha' && (this.kind === 'cpu' || this.kind === 'pvp') && !this.matchEnd(m)) {
          m.skills = [null, null]; this.refreshSkills(); this.awaitGacha = true; this.gachaReadyAt = performance.now() + 1500;
          setTimeout(() => { if (this.match === m && this.awaitGacha) this.dealSkills(); }, 900);
        }
        ui.hideBanner(); return;
      }
      if (['cpu', 'pvp', 'training', 'online'].includes(this.kind) && (this.kind === 'pvp' || W.idx === (this.kind === 'online' ? this.slot : 0))) S.profile.land(r.km);
      this.overT = 0; this.kmShown = false;
      this.stop(0.14);
      this.slowmo(0.25, 0.85);
      R.shake(0.45); R.kick(0.12);
      R.focus((L.x + W.x) / 2, (L.z + W.z) / 2, 1);
      R.fx.burst(L.x, L.z, 14); R.fx.ring(L.x, L.z, 3, 0.45); R.fx.spark(L.x, 1.0, L.z, 2.4);
      const p = this.scr(L.x, L.z);
      ui.speedLines(p.x, p.y, 1.4, 0.45); ui.impactFrame(90); ui.flash('#fff6e6', 0.35);
      A.thump(14); A.roar();
      R.ref.set('point', W);
      this.excite = 1.6;
      const lo = this.loadouts && this.loadouts[W.idx];
      if (lo && this.kind !== 'attract') setTimeout(() => { if (this.match && this.match.result === r) R.crowdThrow((S.item(lo.throw) || {}).kind || 'zabuton', W.x, W.z); }, 500);
      const m = this.match;
      const matchGoesOn = m && !this.matchEnd(m);
      if (matchGoesOn && this.kind === 'boss' && W.idx === 1) {
        if (this.bossBox) { this.bossBox = false; if (this.R.bossG) this.R.bossG.box = false; }   // (the box bursts; from here on he's bare)
        const L = this.ais[0] && this.ais[0].L; if (L) { this.bossSoft = (this.bossSoft || 0) + 1; const k = this.bossSoft; L.react += 0.1; L.think += 0.06; L.aggr = Math.max(0.15, L.aggr - 0.06 * k); L.skill = Math.max(0.04, L.skill * 0.6); L.escP = Math.max(0.15, L.escP * 0.75); L.parryP = Math.max(0.15, L.parryP * 0.75); L.dodge = Math.max(0.02, L.dodge * 0.6); }   // (a lost round: he goes easier still)
        m.skills = [null, null]; this.refreshSkills(); this.awaitGacha = true; this.gachaReadyAt = performance.now() + 1500;
        setTimeout(() => { if (this.match === m && this.awaitGacha) this.dealBossGacha(); }, 900);
      }
      if (matchGoesOn && S.profile.rules === 'gacha' && (this.kind === 'cpu' || this.kind === 'pvp')) {
        m.skills = [null, null]; this.refreshSkills();
        this.awaitGacha = true; this.gachaReadyAt = performance.now() + 1500; // next round's draw is shown before it starts
        setTimeout(() => { if (this.match === m && this.awaitGacha) this.dealSkills(); }, 900);
      }
      ui.hideBanner();
    }

    // ------------------------------------------------------------ menus
    onKey(e) {
      this.audio.init();
      if (this.camp && !this.ui.name && this.camp.onKey(e)) return;
      const c = e.code, ui = this.ui;
      if (this.bindWait) { // KEY BINDINGS: this key becomes the new main key for that action
        const a = this.bindWait, f = ui.focus; this.bindWait = null;
        if (c !== 'Escape') { const b = S.profile.binds; for (const x in b) if (b[x] === c) delete b[x]; b[a] = c; S.profile.save(); S.applyBinds(b); this.audio.blip(true); }
        ui.show('binds'); ui.focus = f; ui.highlight(); return;
      }
      if (c === 'F3' || c === 'Backquote') { this.toggleDebug(); return; }
      if (document.activeElement && document.activeElement.tagName === 'INPUT') return;
      if (ui.name === 'select') { if (c === 'Tab') { this.toggleRules(); return; } this.selectKey(c); return; }
      if (ui.name === 'lobby') {
        if (['KeyA', 'ArrowLeft'].includes(c)) { this.sel.c1 = ((this.sel.c1 || 0) + 3) % 4; this.net.send({ t: 'arch', arch: this.sel.c1 }); this.audio.blip(false); return; }
        if (['KeyD', 'ArrowRight'].includes(c)) { this.sel.c1 = ((this.sel.c1 || 0) + 1) % 4; this.net.send({ t: 'arch', arch: this.sel.c1 }); this.audio.blip(false); return; }
        if (['Enter', 'NumpadEnter', 'Space', 'KeyJ'].includes(c)) { this.net.send({ t: 'start' }); return; }
        if (c === 'Escape' || c === 'Backspace') { this.leaveRoom(); return; }
        return;
      }
      if (ui.name === 'trainsel') {
        if (['KeyA', 'KeyW', 'ArrowLeft', 'ArrowUp'].includes(c)) { this.sel.c1 = (this.sel.c1 + 3) % 4; ui.show('trainsel', { c1: this.sel.c1 }); this.audio.blip(false); }
        else if (['KeyD', 'KeyS', 'ArrowRight', 'ArrowDown'].includes(c)) { this.sel.c1 = (this.sel.c1 + 1) % 4; ui.show('trainsel', { c1: this.sel.c1 }); this.audio.blip(false); }
        else if (c === 'KeyQ' || c === 'KeyE') this.changeStage(c === 'KeyE' ? 1 : -1);
        else if (['Enter', 'Space', 'KeyJ', 'NumpadEnter'].includes(c)) this.startTraining();
        else if (c === 'Escape' || c === 'Backspace') ui.show('play');
        return;
      }
      if (this.kind === 'training' && !ui.name && !this.paused) {
        if (c === 'Tab') { this.cycleTrain(); return; }
        if (c === 'KeyR') { this.trainReset(); return; }
        if (c === 'KeyT') { this.trainRec(); return; }
        if (c === 'KeyG') { this.trainSkill(1); return; }
        if (c === 'KeyB') { this.trainSkill(-1); return; }
        if (c === 'KeyO') { this.trainGacha(); return; }
        if (c === 'KeyM') { this.trainStage(1); return; }
        if (c === 'KeyN') { this.trainStage(-1); return; }
      }
      if (ui.name === 'result' && c !== 'Enter' && c !== 'Space' && c !== 'KeyJ') this.rematchT = 0; // any other key stops the auto-rematch
      if (ui.name === 'locker') {
        if (c === 'KeyA' || c === 'ArrowLeft') { this.lockerCat = (this.lockerCat + S.CAT.length - 1) % S.CAT.length; this.showLocker(0); return; }
        if (c === 'KeyD' || c === 'ArrowRight') { this.lockerCat = (this.lockerCat + 1) % S.CAT.length; this.showLocker(0); return; }
      }
      if (ui.name) {
        if (c === 'KeyW' || c === 'ArrowUp') ui.nav(-1);
        else if (c === 'KeyS' || c === 'ArrowDown') ui.nav(1);
        else if (c === 'KeyA' || c === 'ArrowLeft') { if (this.isOption(ui.current())) ui.activate(-1); }
        else if (c === 'KeyD' || c === 'ArrowRight') { if (this.isOption(ui.current())) ui.activate(1); }
        else if (c === 'Enter' || c === 'Space' || c === 'KeyJ' || c === 'NumpadEnter') ui.activate(1);
        else if (c === 'Escape' || c === 'Backspace') this.back();
        return;
      }
      if (this.awaitGacha && (['Enter', 'NumpadEnter', 'KeyJ', 'Space', 'Numpad1', 'Comma'].includes(c) || S.MAPS.solo.push.includes(c))) { this.confirmGacha(); return; }
      if (this.shopObj && !this.paused) { const K = S.MAPS.solo; if (['Enter', 'NumpadEnter', 'Space'].includes(c) || K.push.includes(c)) { this.shopAction('buy'); return; } if (['Backspace'].includes(c) || K.grab.includes(c) || K.dash.includes(c)) { this.shopAction('leave'); return; } if (K.left.includes(c) || K.up.includes(c)) { this.shopAction('prev'); return; } if (K.right.includes(c) || K.down.includes(c)) { this.shopAction('next'); return; } }
      if (this.kind === 'online' && this.mode === 'game' && !ui.name) {
        if (c === 'Escape') { if (this.leaveArm > performance.now()) this.leaveRoom(); else { this.leaveArm = performance.now() + 2000; this.ui.hint('Press Esc again to leave the room'); } }
        return; // no pausing an online bout
      }
      if (c === 'Escape' && this.mode === 'game') this.pause(true);
      if (this.tut && !this.paused) {
        const gl = this.tut.lesson && this.tut.lesson();
        if (gl && gl.check === 'info' && ['Enter', 'NumpadEnter', 'KeyJ', 'Space'].includes(c)) { this.tut.complete(); return; }
        if (gl && gl.check === 'gacha') { if (c === 'KeyG') { this.tut.drawSkill(); return; } if (c === 'Enter' || c === 'NumpadEnter') { this.tut.complete(); return; } }
        if (c === 'KeyQ') this.tut.prev();
        else if (c === 'KeyR') this.tut.replay();
        else if (c === 'KeyE') this.tut.skip();
      }
    }
    // ---- training: endless practice ring
    // CAMPAIGN: the fish market brawler (campaign.js); the ring and its views are left alone underneath
    startCampaign() {
      this.startAttract(); this.ui.hide(); this.ui.showHud(false); this.ui.hint('');
      this.mode = 'campaign'; document.body.classList.add('playing', 'campaign');
      this.camp = new S.Campaign(this); this.camp.start();
    }
    // TEST level: the bathhouse stealth level (stealth.js), run through the same hooks as the campaign
    startStealth(intro) {
      this.startAttract(); this.ui.hide(); this.ui.showHud(false); this.ui.hint('');
      this.mode = 'campaign'; document.body.classList.add('playing', 'campaign');
      this.camp = new S.Stealth(this); this.camp.start(intro);
    }
    endCampaign() {
      // cover the screen first, tear down underneath, then reveal the title: never a glimpse of the versus stage
      const done = () => {
        if (this.camp) { this.camp.stop(); this.camp = null; }
        document.body.classList.remove('playing', 'campaign');
        this.R.resize(); this.startAttract(); this.ui.showNow('title');
      };
      const bn = S.Banners;
      if (bn && !bn.busy && this.camp) { if (this.camp.hud) this.camp.hud.style.display = 'none'; bn.flood({ hold: 0.06, speed: 1.6, onCovered: done }); }
      else done();
    }
    startTraining() {
      if (this.rec) { this.rec = null; if (this.recKeys) this.ctrls[0].src = this.recKeys; }
      if (!S.Banners.busy) S.Banners.wall({ hold: 0.12, speed: 1.1 });
      this.mode = 'game'; this.paused = false; this.endTutorial();
      this.ui.hide(); this.ui.showHud(false); this.ui.hint('');
      const c1 = this.sel.c1 || 0;
      this.trainMode = this.trainMode || 'idle'; if (this.trainSkillI === undefined) this.trainSkillI = -1; this.trainRefill = 0;
      this.setupMatch(c1, c1 === 0 ? 1 : 0, 'training');
      this.trainReset();
    }
    trainReset() {
      const m = this.match; if (!m) return;
      m.round = 1; m.result = null; m.clinch = null; m.deadT = 0; m.objs = [];
      const keep = m.skills[0];
      m.w[0].reset(-1.5, 0, 0); m.w[1].reset(1.5, 0, Math.PI);
      m.phase = 'fight'; m.sinceGo = 5; m.time = 0; m.events = [];
      for (const w of m.w) w.set('free');
      m.skills = [this.trainOn ? keep || (this.trainSkillI >= 0 ? S.Skills.LIST[this.trainSkillI].id : null) : null, null];
      this.dummy.set(this.trainMode === 'cpu' || this.trainMode === 'replay' ? 'idle' : this.trainMode, [1.5, 0]);
      this.repI = 0; // a recording replays from the top on every reset
      this.R.fx.clearDecals(); this.R.clearThrown(); this.ui.hideKimarite(); this.ui.hideBanner(); this.ui.vhs(false); this.overT = 0; this.kmShown = false;
      this.trainPanel();
    }
    cycleTrain() {
      if (this.rec) this.trainRec(); // switching partner ends a recording
      const order = ['idle', 'charge', 'palm', 'drive', 'cpu'].concat(this.recFrames ? ['replay'] : []);
      this.trainMode = order[(order.indexOf(this.trainMode) + 1) % order.length];
      this.dummy.set(this.trainMode === 'cpu' || this.trainMode === 'replay' ? 'idle' : this.trainMode, [1.5, 0]);
      this.repI = 0;
      this.audio.blip(true); this.trainPanel();
    }
    // the training partner's input: a live recording, a replay, the CPU, or a scripted dummy
    trainSample(ai) {
      const N0 = { mx: 0, mz: 0, push: false, grab: false, dash: false, skill: false };
      if (this.rec) {
        const r = this.recKeys.sample();
        const f = { mx: r.mx, mz: r.mz, push: r.push, grab: r.grab, dash: r.dash, skill: false };
        this.rec.frames.push(f);
        if (this.rec.frames.length >= this.rec.max) setTimeout(() => { if (this.rec) this.trainRec(); }, 0);
        return f;
      }
      if (this.trainMode === 'replay' && this.recFrames) return this.recFrames[this.repI++] || N0;
      return this.trainMode === 'cpu' ? ai.sample() : this.dummy.sample();
    }
    // T: record the partner. Your keys drive them while recording; T again (or 10s) stops and they replay it on every reset.
    trainRec() {
      const m = this.match; if (!m || this.kind !== 'training') return;
      if (!this.rec) {
        this.recKeys = this.ctrls[0].src;
        this.ctrls[0].src = { sample: () => ({ mx: 0, mz: 0, push: false, grab: false, dash: false, skill: false }) };
        this.trainReset();
        this.rec = { frames: [], max: Math.round(10 / S.DT) };
        this.audio.blip(true); this.trainPanel();
      } else {
        const fr = this.rec.frames; this.rec = null;
        this.ctrls[0].src = this.recKeys;
        if (fr.length > 10) { this.recFrames = fr; this.trainMode = 'replay'; }
        this.audio.blip(true); this.trainReset();
      }
    }

    // gacha practice: step forward or back through every skill; a used skill comes back so it can be tried again
    trainSkill(d) {
      const L = S.Skills.LIST, n = L.length;
      this.trainOn = true;
      this.trainSkillI = this.trainSkillI < 0 ? (d > 0 ? 0 : n - 1) : (this.trainSkillI + d + n) % n;
      this.match.skills[0] = L[this.trainSkillI].id; this.trainRefill = 0;
      this.refreshSkills(); this.ui.showHud(false);
      this.audio.blip(true); this.trainPanel();
    }
    trainGacha() {
      this.trainOn = !this.trainOn; this.trainRefill = 0;
      if (this.trainOn) { if (this.trainSkillI < 0) this.trainSkillI = 0; this.match.skills[0] = S.Skills.LIST[this.trainSkillI].id; }
      else this.match.skills[0] = null;
      this.refreshSkills(); this.ui.showHud(false); this.audio.blip(true); this.trainPanel();
    }
    // swap the stage on the spot, without leaving the ring ('random' is skipped here: you want to see what you pick)
    trainStage(d) {
      const L = S.STAGES.filter((s) => s.id !== 'random');
      const i = Math.max(0, L.findIndex((s) => s.id === (this.match && this.match.stage)));
      const id = L[(i + d + L.length) % L.length].id;
      S.profile.stage = id; S.profile.save();
      this.R.setStage(id); this.match.stage = id; this.match.stageA = 0;
      this.R.fx.clearDecals(); this.audio.blip(true); this.trainPanel();
    }
    trainPanel() {
      const names = { idle: 'STANDS STILL', charge: 'CHARGES AT YOU', palm: 'SLAPS AT YOU', drive: 'PUSHES BACK WHEN GRABBED', cpu: 'FIGHTS (CPU ' + this.settings.difficulty.toUpperCase() + ')',
        replay: 'REPLAYS YOUR RECORDING (' + (this.recFrames ? (this.recFrames.length * S.DT).toFixed(1) : 0) + 's)' };
      const L = S.Skills.LIST, cur = this.trainOn && this.trainSkillI >= 0 ? L[this.trainSkillI] : null;
      const ready = this.match && this.match.skills[0];
      const touch = S.touch && S.touch.on;
      const k = (key, act, label) => '<span class="tp-btn" data-train="' + act + '">' + (touch ? '' : '<kbd>' + key + '</kbd> ') + label + '</span>';
      if (this.rec) {
        this.ui.training('<div class="tp-head"><span class="tp-rec">● REC</span>You are the partner</div>' +
          '<div class="tp-text">Your keys move the partner now. Do the move you want to practise against. Up to 10s.</div>' +
          '<div class="tp-skip">' + k('T', 'rec', 'stop recording') + '</div>');
        return;
      }
      this.ui.training('<div class="tp-head"><span>TRAINING</span>Partner ' + names[this.trainMode] + '</div>' +
        '<div class="tp-text">Stage <b>' + ((S.STAGES.find((s) => s.id === (this.match && this.match.stage)) || {}).name || 'DOHYO') + '</b> · ' + (cur ? 'Gacha ON · <b>' + cur.name + '</b> (' + (this.trainSkillI + 1) + '/' + L.length + ') · ' + (ready ? (touch ? 'tap SKILL' : 'Space') + ' to use' : 'coming back…') : 'Gacha OFF · pure sumo') + '</div>' +
        (cur ? '<div class="tp-desc">' + cur.desc + '</div>' : '') +
        '<div class="tp-skip">' + k('O', 'gacha', this.trainOn ? 'gacha off' : 'gacha on') + k('B', 'back', 'back') + k('G', 'next', 'next skill') + k('Tab', 'partner', 'partner') + k('T', 'rec', 'record partner') + k('M', 'stage', 'stage') + k('R', 'reset', 'reset') + (touch ? '' : ' · Esc menu') + '</div>');
    }
    trainFlow(dt) {
      const m = this.match;
      // the skill you just used comes back, so you can try it again
      if (this.trainOn && this.trainSkillI >= 0 && !m.skills[0]) {
        if (this.trainRefill <= 0) this.trainRefill = 1.2;
        else if ((this.trainRefill -= dt) <= 0) { m.skills[0] = S.Skills.LIST[this.trainSkillI].id; this.refreshSkills(); this.ui.showHud(false); this.trainPanel(); }
      }
      if (m.phase !== 'over') return;
      this.overT += dt;
      if (!this.kmShown && this.overT > 0.4) { this.kmShown = true; const r = m.result; this.showKm(r, this.winLabel(r.winner.idx)); }
      if (this.overT > 1.8) { this.R.focus(0, 0, 0); this.trainReset(); }
    }
    showKm(r, label) {
      if (r.third) { const ta = S.ARCH[this.match.third.arch]; this.ui.kimarite(r.km, ta, 1, 'CHALLENGER WINS'); return; }
      if (r.draw) this.ui.kimarite(r.km, { accent: '#f0c35a' }, 0, 'NO WINNER');
      else this.ui.kimarite(r.km, r.winner.a, r.winner.idx, label);
    }
    winLabel(i) {
      if (this.kind === 'cpu' || this.kind === 'training' || this.kind === 'tutorial') return i === 0 ? 'YOU WIN' : 'YOU LOSE';
      if (this.kind === 'pvp') return this.names[i] + ' WINS';
      return '';
    }
    // ---- online
    // Quick Match: queue for a similar-rated opponent, then meet them in a fresh one-on-one room
    startFind() { this.net.close(); this.qmCode = null; this.ui.show('lobby', { searching: true, me: this.net.me || null }); this.net.findMatch(); }
    onQueueStats(m) { if (this.ui.name === 'lobby' && !this.qmCode) this.ui.show('lobby', { searching: true, me: m }); }
    onMatchFound(code) {
      this.qmCode = code; this.enterRoom(code);
      // if the other player never shows up, go back in the queue
      clearTimeout(this.qmT); this.qmT = setTimeout(() => this.qmCheck(), 12000);
    }
    qmCheck() {
      const r = this.net.room;
      if (!this.qmCode || this.net.code !== this.qmCode || this.kind === 'online') return;
      if (!r || r.order.length < 2) this.startFind();
    }
    onQuickFull() { this.startFind(); }
    enterRoom(code) {
      this.net.connect(code);
      this.ui.show('lobby', { room: null, code });
    }
    askRoomCode() {
      const btn = this.ui.screen.querySelector('[data-i="' + this.ui.focus + '"]');
      if (!btn) return;
      const inp = document.createElement('input');
      inp.className = 'nameinp'; inp.maxLength = 6; inp.placeholder = 'CODE';
      btn.appendChild(inp); inp.focus();
      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); const v = inp.value.toUpperCase().replace(/[^A-Z0-9]/g, ''); if (v.length >= 3) this.enterRoom(v); }
        if (e.key === 'Escape') { e.preventDefault(); inp.blur(); }
      });
      inp.addEventListener('blur', () => { if (this.ui.name === 'online') this.ui.render(); }, { once: true });
    }
    leaveRoom() {
      this.net.stopFind(); clearTimeout(this.qmT); this.qmCode = null;
      this.net.close(); this.kind = 'title';
      this.ui.hint(''); this.ui.showHud(false); this.ui.hideKimarite();
      this.ui.show('title'); this.startAttract();
    }
    onRoom(m) {
      this.roomState = m;
      // quick match: opponent gone after a bout? go back in the queue
      if (this.qmCode && m.code === this.qmCode) {
        if (m.order.length >= 2) this.qmHad2 = true;
        else if (this.qmHad2) { this.qmHad2 = false; clearTimeout(this.qmT); this.qmT = setTimeout(() => { const r = this.net.room; if (this.net.code === this.qmCode && r && r.order.length < 2) this.startFind(); }, 3000); }
      }
      if (this.kind === 'online' && this.match && !this.matchOver && m.playing) return; // mid-bout: keep fighting
      if (this.kind === 'online' && this.resultUntil > performance.now()) return; // let the result show first
      if (this.ui.name === 'lobby' || this.kind === 'online' || this.ui.name === 'online') {
        if (this.kind === 'online') { this.kind = 'title'; this.match = null; this.R.setWrestlers([], null, ['', '']); this.ui.showHud(false); this.ui.hint(''); this.ui.hideKimarite(); }
        const f = this.ui.focus; this.ui.show('lobby', { room: m, code: m.code }); this.ui.focus = Math.min(f, this.ui.items.length - 1); this.ui.highlight();
      }
    }
    onNetClosed(msg) {
      if (this.kind === 'online' || this.ui.name === 'lobby') {
        this.kind = 'title'; this.match = null; this.R.setWrestlers([], null, ['', '']);
        this.ui.showHud(false); this.ui.hint(''); this.ui.hideKimarite();
        this.ui.show('online', { err: msg + (location.protocol === 'file:' ? '' : ' Is the game server running?') });
      }
    }
    onNetAbort(m) { if (this.kind === 'online') { this.matchOver = true; this.resultUntil = 0; this.ui.callout(m.reason || 'Bout cancelled', innerWidth / 2, innerHeight / 2, 'big'); setTimeout(() => this.roomState && this.onRoom(this.roomState), 1200); } }
    onNetStart(m) {
      this.netMatch = m;
      this.slot = m.p.indexOf(this.net.id);
      this.mode = 'game'; this.paused = false;
      this.ui.hide(); this.ui.showHud(true);
      S.seedRand(m.seed);
      this.setupMatch(m.archs[0], m.archs[1], 'online');
      this.names = m.names.slice();
      this.ui.setFighters([S.ARCH[m.archs[0]], S.ARCH[m.archs[1]]], [this.slot === 0 ? 'YOU' : 'P1', this.slot === 1 ? 'YOU' : 'P2']);
      this.viewerIdx = this.slot >= 0 ? this.slot : -1;
      this.ui.hint((this.slot < 0 ? 'Watching · ' : '') + 'Room ' + this.net.code + ' · Esc twice to leave');
      this.ui.setRecord('');
      this.nf = 0; this.ND = this.slot >= 0 ? 1 : this.net.delayFrames() + S.NET_KEEP; this.outQ = null; this.remoteNf = 0; this.remoteNfAt = performance.now(); this.inBuf = [{}, {}]; this.sentF = this.ND - 1; this.netCur = [null, null];
      this.snaps = {}; this.pred = {}; this.rbFrom = null; this.confirmed = [-1, -1]; this.nextHash = 30; this.awaitSnap = false; this.rollbacks = 0;
      if (this.slot >= 0) { for (let f = 0; f < this.ND; f++) { const z = [0, 0, 0, 0, 0, 0]; this.inBuf[this.slot][f] = z; this.queueInput(f, z); } this.flushInputs(); }
      this.localSrc = new S.KeySource(S.MAPS.solo, 0);
      this.hashes = {}; this.rHashes = {}; this.desyncs = 0; this.waitT = 0; this.acc = 0; this.resultUntil = 0;
    }
    // inputs go out only when they change, plus a short 'still the same' note every few frames (far fewer messages)
    queueInput(k, pk) {
      const q = this.outQ || (this.outQ = { runs: [], sent: null });
      const L = q.runs[q.runs.length - 1], key = pk.join();
      if (L && L[1] === k - 1 && L[3] === key) L[1] = k; else q.runs.push([k, k, pk, key]);
      if ((q.sent !== key) || k - q.runs[0][0] + 1 >= S.NET_KEEP) this.flushInputs();
    }
    flushInputs() {
      const q = this.outQ; if (!q || !q.runs.length) return;
      this.net.send({ t: 'ir', s: this.slot, n: this.nf, r: q.runs.map((x) => [x[0], x[1], x[2]]) });
      q.sent = q.runs[q.runs.length - 1][3]; q.runs = [];
    }
    onNetRuns(m) {
      if (!this.inBuf || (m.s !== 0 && m.s !== 1) || !Array.isArray(m.r)) return;
      if (m.s !== this.slot) { this.remoteNf = m.n; this.remoteNfAt = performance.now(); }
      for (const [f0, f1, b] of m.r) for (let f = f0; f <= f1 && f - f0 < 400; f++) this.onNetInput({ s: m.s, f, b });
    }
    onNetInput(m) {
      if (!this.inBuf || (m.s !== 0 && m.s !== 1)) return;
      this.inBuf[m.s][m.f] = m.b;
      while (this.inBuf[m.s][this.confirmed[m.s] + 1] !== undefined) this.confirmed[m.s]++;
      // rollback: we already played this frame with a guess; if the guess was wrong, rewind to it
      if (this.slot >= 0 && m.s !== this.slot && m.f < this.nf && this.pred[m.f] && this.pred[m.f].join() !== m.b.join()) {
        this.rbFrom = this.rbFrom === null ? m.f : Math.min(this.rbFrom, m.f);
      }
      if (this.pred) delete this.pred[m.f];
    }
    onNetHash(m) { if (!this.rHashes) return; this.rHashes[m.f] = m.h; this.checkHash(m.f); }
    checkHash(f) {
      if (this.hashes[f] === undefined || this.rHashes[f] === undefined) return;
      if (this.hashes[f] !== this.rHashes[f]) { this.desyncs++; if (this.slot === 1) { this.awaitSnap = true; this.net.send({ t: 'need' }); } }
      delete this.hashes[f]; delete this.rHashes[f];
    }
    onNetNeed() { if (this.slot === 0 && this.match) this.net.send({ t: 'snap', f: this.nf, d: S.netSnapshot(this.match) }); }
    onNetSnap(m) {
      if (this.slot === 0 || !this.match || (this.slot === 1 && !this.awaitSnap)) return;
      this.awaitSnap = false; S.netApply(this.match, m.d);
      if (this.slot === 1) { this.nf = m.f; this.snaps = {}; this.pred = {}; this.rbFrom = null; this.sentF = Math.max(this.sentF, this.nf); }
    }
    // lockstep: advance only when both players' inputs for the next net frame have arrived
    onlineStep(dt) {
      const m = this.match;
      if (this.hitstop > 0) { this.hitstop -= dt; return 0; }
      let ts = 1; if (this.slowT > 0) { this.slowT -= dt; ts = this.slowScale; } this.ts = ts;
      this.acc += dt * ts;
      const NDT = 4 * S.DT; let n = 0, ran = 0;
      while (this.acc >= NDT && n < 6) {
        const f = this.nf;
        if (this.slot >= 0 && this.sentF < f + this.ND) {
          const pk = S.netPack(this.localSrc.sample()); S.kb.flush();
          for (let k = this.sentF + 1; k <= f + this.ND; k++) { this.inBuf[this.slot][k] = pk; this.queueInput(k, pk); }
          this.sentF = f + this.ND;
        }
        const a = this.inBuf[0][f], b = this.inBuf[1][f];
        if (a === undefined || b === undefined) { this.waitT += dt; break; }
        this.waitT = 0; this.netCur = [a, b];
        for (let k = 0; k < 4; k++) this.simStep();
        delete this.inBuf[0][f - 90]; delete this.inBuf[1][f - 90];
        this.nf++; this.acc -= NDT; n++; ran++;
        if (this.nf > 1 && (this.nf - 1) % 30 === 0 && m === this.match) { // state after frame nf-1, same frame the players report
          this.hashes[this.nf - 1] = S.netHash(this.match); this.checkHash(this.nf - 1);
        }
      }
      if (this.acc > NDT * 6) this.acc = NDT * 6;
      this.hintT = (this.hintT || 0) - dt;
      if (this.waitT > 1.2) this.ui.hint('Waiting for the other player…');
      else if (this.hintT <= 0) { this.hintT = 0.5; this.ui.hint((this.slot < 0 ? 'Watching · ' : '') + 'Ping ' + Math.round(this.net.rtt) + ' ms · delay ' + Math.round(this.ND * 33) + ' ms · Esc twice to leave'); }
      this.lastWait = this.waitT;
      return ran ? dt * ts : 0;
    }
    // ---- rollback: play ahead on a guess of the opponent's input, rewind if the guess was wrong
    saveFrame() {
      return { m: S.cloneMatch(this.match), seed: S.getSeed(), btns: this.ctrls.map((c) => ['push', 'grab', 'dash', 'skill'].map((b) => [c[b].held, c[b].t])) };
    }
    remoteFor(f) {
      const op = 1 - this.slot, B = this.inBuf[op];
      if (B[f] !== undefined) return { b: B[f], guessed: false };
      for (let k = Math.min(f, this.confirmed[op]); k >= 0 && k > f - 120; k--) if (B[k] !== undefined) return { b: B[k], guessed: true };
      return { b: [0, 0, 0, 0, 0, 0], guessed: true };
    }
    simFrame(f, silent) {
      const me = this.slot, r = this.remoteFor(f);
      if (r.guessed) this.pred[f] = r.b; else delete this.pred[f];
      const mine = this.inBuf[me][f] || [0, 0, 0, 0, 0, 0];
      this.netCur = me === 0 ? [mine, r.b] : [r.b, mine];
      for (let k = 0; k < 4; k++) {
        if (silent) { for (const c of this.ctrls) c.update(S.DT); this.match.step(S.DT); this.match.events.length = 0; this.onlineRounds(true); }
        else this.simStep();
      }
    }
    rollback(k) {
      const sn = this.snaps[k];
      if (!sn) return; // too old to rewind: keep going
      this.match = S.cloneMatch(sn.m); S.setSeed(sn.seed);
      sn.btns.forEach((bs, i) => ['push', 'grab', 'dash', 'skill'].forEach((b, j) => { const B = this.ctrls[i][b]; B.held = bs[j][0]; B.t = bs[j][1]; B.pressed = B.released = false; }));
      this.match.w[0].input = this.ctrls[0]; this.match.w[1].input = this.ctrls[1];
      for (let j = k; j < this.nf; j++) {
        this.snaps[j] = this.saveFrame();
        this.simFrame(j, true);
      }
      this.rollbacks++;
    }
    onlineStepRB(dt) {
      // no hit-pause or slow-mo here: each side would pause at slightly different moments and drift apart
      this.hitstop = 0; this.slowT = 0; const ts = 1; this.ts = 1;
      // time sync: if we're running ahead of the other player, ease off a little so neither side has to stall
      const remoteNow = this.remoteNf + (performance.now() - this.remoteNfAt) / 33.3 + (this.net.rtt || 0) / 33.3; // where they are now: last report, aged, plus the trip
      this.ahead = this.nf - remoteNow;
      this.acc += dt * ts * (this.ahead > 1.5 ? 0.85 : this.ahead < -2 ? 1.15 : 1);
      if (this.rbFrom !== null) { const k = this.rbFrom; this.rbFrom = null; if (k < this.nf) this.rollback(k); }
      const NDT = 4 * S.DT, MAXROLL = 12 + S.NET_KEEP, op = 1 - this.slot;
      let n = 0, ran = 0;
      while (this.acc >= NDT && n < 8) {
        const f = this.nf;
        if (f - this.confirmed[op] > MAXROLL) { this.waitT += dt; this.stallT = (this.stallT || 0) + dt; break; } // too far ahead of what we know: wait
        if (this.sentF < f + this.ND) {
          const pk = S.netPack(this.localSrc.sample()); S.kb.flush();
          for (let k = this.sentF + 1; k <= f + this.ND; k++) { this.inBuf[this.slot][k] = pk; this.queueInput(k, pk); }
          this.sentF = f + this.ND;
        }
        this.snaps[f] = this.saveFrame();
        this.simFrame(f, false);
        delete this.snaps[f - 45]; delete this.inBuf[0][f - 150]; delete this.inBuf[1][f - 150];
        this.waitT = 0; this.nf++; this.acc -= NDT; n++; ran++;
      }
      if (this.acc > NDT * 8) this.acc = NDT * 8;
      // sync check on frames both sides have fully confirmed
      const h = this.nextHash;
      if (this.confirmed[op] >= h && this.nf > h + 1 && this.snaps[h + 1] && this.rbFrom === null) {
        const val = S.netHash(this.snaps[h + 1].m);
        if (this.slot === 0) this.net.send({ t: 'hash', f: h, h: val });
        else { this.hashes[h] = val; this.checkHash(h); }
        this.nextHash += 30;
      } else if (this.nf > h + 40) this.nextHash += 30; // skipped (rewound past it)
      this.hintT = (this.hintT || 0) - dt;
      if (this.waitT > 1.2) this.ui.hint('Waiting for the other player…');
      else if (this.hintT <= 0) { this.hintT = 0.5; this.ui.hint('Ping ' + Math.round(this.net.rtt) + ' ms · Esc twice to leave'); }
      return ran ? dt * ts : 0;
    }

    // round changes happen inside the sim step so every client switches on the same frame
    onlineRounds(silent) {
      const m = this.match;
      if (!m || m.phase !== 'over' || this.matchOver || m.overT < 2.6) return;
      if (Math.max(m.wins[0], m.wins[1]) >= this.need) {
        if (silent) return; // decided for real on the next normal frame
        this.matchOver = true;
        const wi = m.wins[0] > m.wins[1] ? 0 : 1;
        const mine = this.slot === wi;
        if (mine) { S.profile.earn(100000); this.ui.setYen(); }
        if (this.slot === 0) this.net.send({ t: 'end', winner: wi });
        this.ui.hideKimarite();
        this.ui.show('result', { arch: m.w[wi].a, head: this.slot < 0 ? 'WINNER' : mine ? 'YOU WIN' : 'YOU LOSE', who: this.slot < 0 || !mine ? this.names[wi] : '', score: m.wins[0] + ' – ' + m.wins[1], record: 'Winner stays on', yen: mine ? 100000 : 0, online: true });
        this.resultUntil = performance.now() + 4000;
        setTimeout(() => { if (this.roomState) { this.resultUntil = 0; this.onRoom(this.roomState); } }, 4100);
      } else { if (m.result && m.result.draw) m.round--; m.newRound(); if (silent) m.events.length = 0; else this.handleEvents(); }
    }
    onlineFlow(dt) {
      const m = this.match; if (!m || m.phase !== 'over') { this.overT = 0; this.bnrKey = null; return; }
      this.overT += dt;
      if (!this.kmShown && this.overT > 0.4) { this.kmShown = true; const r = m.result; this.showKm(r, this.slot < 0 ? this.names[r.winner.idx] + ' WINS' : r.winner.idx === this.slot ? 'YOU WIN' : 'YOU LOSE'); this.ui.setWins(m.wins, this.need); }
      if (this.overT > 1.0) this.R.cs.focusW *= Math.exp(-dt * 2);
      if (this.overT > 2.2) this.ui.hideKimarite();
      if (m.overT >= 1.85 && !this.bnrKey && Math.max(m.wins[0], m.wins[1]) < this.need) { // covered by ~2.5s; the sim resets the round at 2.6s
        this.bnrKey = true;
        const end = Math.max(m.wins[0], m.wins[1]) >= this.need;
        S.Banners.flood({ hold: end ? 0.35 : 0.3, speed: 1.15 });
      }
    }

    isOption(a) { return a === 'diff' || a === 'endless' || a === 'hints' || a === 'sound' || a === 'debug' || a === 'pstage' || /^hud[A-Z]/.test(a); }
    toggleRules() {
      const P = S.profile; P.rules = P.rules === 'gacha' ? 'pure' : 'gacha'; P.save();
      this.audio.blip(true); this.ui.show('select', this.sel);
    }
    // ---- locker / shop with a live try-on preview
    openLocker() {
      this.lockerCat = this.lockerCat || 0;
      this.mode = 'locker'; this.endTutorial(); this.ui.hideBanner();
      const c1 = this.sel.c1 || 0;
      this.setupMatch(c1, (c1 + 1) % 4, 'showcase');
      this.ui.showHud(false); this.ui.hint('');
      this.showLocker(0);
    }
    showLocker(focus) {
      this.ui.show('locker', { cat: this.lockerCat });
      this.ui.focus = Math.min(focus || 0, this.ui.items.length - 1); this.ui.highlight();
      this.lockerPreview();
    }
    lockerPreview() {
      if (this.kind !== 'showcase') return;
      const act = this.ui.current() || '';
      const id = act.indexOf('item:') === 0 ? act.slice(5) : null;
      const cat = S.CAT[this.lockerCat];
      const lo = S.profile.loadout();
      if (id && cat.key !== 'taunt') lo[cat.key] = id;
      const m = this.match, archs = [m.w[0].a, m.w[1].a];
      this.loadouts = [lo, S.DEF_EQ];
      this.R.setWrestlers(archs, this.loadouts, [S.profile.names[0], '']);
      const v1 = this.R.views[1]; v1.root.visible = false; v1.shadow.visible = false;
      const w0 = m.w[0];
      w0.reset(0, 0, Math.PI / 2); m.w[1].reset(0, 5.8, -Math.PI / 2);
      m.phase = 'shikiri'; m.round = 1; m.phaseT = 0;
      if (cat.key === 'victory') { this.R.views[0].victory = (S.item(id) || {}).pose || this.R.views[0].victory; w0.set('win'); }
      else if (cat.key === 'taunt' && id) { w0.pre = 'x_' + S.item(id).pose; w0.preT = 0; }
      this.R.camOverride = { p: [-0.4, 2.2, 6.0], l: [-1.7, 1.0, 0] };
      if (cat.key === 'throw' && id) this.R.crowdThrow(S.item(id).kind, 0, 0); else this.R.clearThrown();
      if (cat.key === 'banner') this.R.camOverride = { p: [-4.5, 2.6, 2.5], l: [-6.9, 1.6, -5.5] };
    }
    lockerBuy(id) {
      const P = S.profile, it = S.item(id), cat = S.CAT[this.lockerCat];
      if (!P.has(id)) {
        if (P.yen < it.price) { this.audio.scuff(); const el = document.querySelector('.wallet'); if (el) { el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake'); } return; }
        P.buy(id); this.audio.cheer(0.5, 0.8);
      }
      P.equip(cat.key, id); this.audio.blip(true);
      this.showLocker(this.ui.focus);
    }
    editName(i) {
      const btn = this.ui.screen.querySelector('[data-i="' + this.ui.focus + '"] em');
      if (!btn) return;
      const inp = document.createElement('input');
      inp.value = S.profile.names[i]; inp.maxLength = 12; inp.className = 'nameinp';
      btn.replaceWith(inp); inp.focus(); inp.select();
      const done = () => { const v = inp.value.trim().toUpperCase().slice(0, 12); if (v) { S.profile.names[i] = v; S.profile.save(); } const f = this.ui.focus; this.ui.render(); this.ui.focus = f; this.ui.highlight(); };
      inp.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === 'Escape') { e.preventDefault(); inp.blur(); } });
      inp.addEventListener('blur', done, { once: true });
    }
    toggleDebug() {
      this.settings.debug = !this.settings.debug;
      document.getElementById('debug').classList.toggle('on', this.settings.debug);
      if (this.ui.name === 'settings') { const f = this.ui.focus; this.ui.render(); this.ui.focus = f; this.ui.highlight(); }
    }
    pause(on) {
      this.paused = on; S.kb.flush();
      if (on) this.ui.show('pause', { tut: !!this.tut }); else this.ui.hide();
    }
    back() {
      const n = this.ui.name;
      if (n === 'pause') this.pause(false);
      else if (n === 'settings') { if (this.uiBack === 'stealth' && this.camp) { this.ui.hide(); this.camp.hudApply(); this.camp.setPause(true); } else if (this.uiBack === 'pause') this.ui.show('pause', { tut: !!this.tut }); else this.ui.show('title'); }
      else if (n === 'play') this.ui.show('title');
      else if (n === 'controls') { const f = this.uiBack; this.ui.show('settings'); this.uiBack = f; }
      else if (n === 'online') this.ui.show('title');
      else if (n === 'phones') { const b = this.phonesBack || 'online'; this.phonesBack = null; if (b === 'pause') this.ui.show('pause', { tut: !!this.tut }); else this.ui.show(b, {}); }
      else if (n === 'lobby') this.leaveRoom();
      else if (n === 'moves' || n === 'binds') this.ui.show('controls');
      else if (n === 'select' || n === 'trainsel') this.ui.show('play');
      else if (n === 'tutorial' || n === 'soon') this.ui.show('title');
      else if (n === 'locker') { this.R.camOverride = null; this.R.clearThrown(); this.ui.show('play'); this.startAttract(); }
    }
    selectKey(c) {
      const s = this.sel;
      const mv = (k, d) => { if (s['lock' + k]) return; s['c' + k] = (s['c' + k] + d + 4) % 4; this.audio.blip(false); this.ui.show('select', s); };
      const pvp = s.mode === 'pvp';
      if (s.mode === 'cpu' && !s.lock1 && ['KeyW', 'ArrowUp', 'KeyS', 'ArrowDown'].includes(c)) { this.changeBet(c === 'KeyW' || c === 'ArrowUp' ? 1 : -1); return; }
      if (!s.lock1 && (c === 'KeyQ' || c === 'KeyE')) { this.changeStage(c === 'KeyE' ? 1 : -1); return; }
      if (c === 'KeyA' || c === 'KeyW' || (!pvp && (c === 'ArrowLeft' || c === 'ArrowUp'))) mv(1, -1);
      else if (c === 'KeyD' || c === 'KeyS' || (!pvp && (c === 'ArrowRight' || c === 'ArrowDown'))) mv(1, 1);
      else if (pvp && c === 'ArrowUp') mv(2, -1);
      else if (pvp && c === 'ArrowDown') mv(2, 1);
      else if (pvp && c === 'ArrowLeft') mv(2, -1);
      else if (pvp && c === 'ArrowRight') mv(2, 1);
      else if (c === 'Space' || c === 'KeyJ' || (!pvp && (c === 'Enter' || c === 'NumpadEnter'))) this.lockSel(1);
      else if (pvp && (c === 'Enter' || c === 'NumpadEnter' || c === 'Numpad1' || c === 'Comma')) this.lockSel(2);
      else if (c === 'Escape' || c === 'Backspace') { if (s.lock1 || s.lock2) { s.lock1 = s.lock2 = false; this.ui.show('select', s); } else this.ui.show('play'); }
    }
    // bet steps, plus ALL IN; never more than you have
    changeStage(d) {
      const L = S.STAGES, i = Math.max(0, L.findIndex((s) => s.id === S.profile.stage));
      S.profile.stage = L[(i + d + L.length) % L.length].id; S.profile.save(); this.audio.blip(false);
      if (this.ui.name === 'trainsel') this.ui.show('trainsel', { c1: this.sel.c1 }); else this.ui.show('select', this.sel);
    }
    changeBet(d) {
      const P = S.profile, steps = S.BETS.filter((v) => v < P.yen).concat([P.yen]);
      let i = steps.indexOf(P.betNow()); if (i < 0) i = steps.findIndex((v) => v > P.betNow()) - (d > 0 ? 1 : 0);
      i = (i + d + steps.length) % steps.length;
      P.bet = steps[i]; P.save(); this.audio.blip(false); this.ui.show('select', this.sel);
    }
    lockSel(k) {
      const s = this.sel;
      s['lock' + k] = true; this.audio.blip(true);
      if (s.mode === 'cpu' && k === 1) { let c2 = (Math.random() * 4) | 0; if (c2 === s.c1) c2 = (c2 + 1 + ((Math.random() * 3) | 0)) % 4; s.c2 = c2; s.lock2 = true; }
      this.ui.show('select', s);
      if (s.lock1 && s.lock2) {
        setTimeout(() => {
          if (this.ui.name !== 'select') return;
          if (!this.seenTut) this.ui.show('tutorial', { mode: s.mode }); else this.startGame();
        }, 450);
      }
    }
    menuAction(act, dir) {
      const ui = this.ui, st = this.settings;
      if (act && act.indexOf('bind:') === 0) { // wait for the next key
        const a = act.slice(5), f = ui.focus; this.bindWait = a; ui.show('binds', { waiting: a }); ui.focus = f; ui.highlight(); this.audio.blip(true); return;
      }
      const refresh = () => { const f = ui.focus; ui.render(); ui.focus = f; ui.highlight(); };
      switch (act) {
        case 'cpu': case 'pvp':
          this.sel = { mode: act, c1: this.sel.c1 || 0, c2: act === 'pvp' ? 1 : this.sel.c2, lock1: false, lock2: false };
          ui.show('select', this.sel); break;
        case 'learn': this.startTutorial(); break;
        case 'campaign': this.startCampaign(); break;
        case 'test': this.startStealth(); break;
        case 'wmmPlay': this.ui.hide(); S.WMM.play(() => this.startStealth(true)); break;
        case 'training': this.sel.c1 = this.sel.c1 || 0; ui.show('trainsel', { c1: this.sel.c1 }); break;
        case 'play': ui.show('play'); break;
        case 'locker': this.openLocker(); break;
        case 'moves': this.movesBack = ui.name; ui.show('moves'); break;
        case 'phones': this.phonesBack = ui.name; this.watchPhones(); S.phones.start(); ui.show('phones'); break;
        case 'phonesOn': this.watchPhones(); S.phones.start(); break;
        case 'phonesOff': S.phones.stop(); break;
        case 'online': ui.show('online', { err: this.net.available() ? '' : 'Online needs the game server. Start it with: node server/local.mjs' }); break;
        case 'createRoom': { const L = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; let c = ''; for (let i = 0; i < 4; i++) c += L[(Math.random() * L.length) | 0]; this.enterRoom(c); break; }
        case 'joinRoom': this.askRoomCode(); break;
        case 'quickMatch': this.startFind(); break;
        case 'leaveRoom': this.leaveRoom(); break;
        case 'startBout': this.net.send({ t: 'start' }); break;
        case 'soonRanked': ui.show('soon', { title: 'RANKED', lines: ['Coming soon.', 'Online matches against players of your level.', 'Climb the banzuke: from Jonokuchi to Yokozuna.', 'Pure rules only.'] }); break;
        case 'name1': this.editName(0); break;
        case 'name2': this.editName(1); break;
        case 'settings': this.uiBack = ui.name === 'pause' ? 'pause' : 'title'; ui.show('settings'); break;
        case 'diff': {
          const i = S.DIFFS.indexOf(st.difficulty);
          st.difficulty = S.DIFFS[(i + dir + 3) % 3]; this.save(); refresh();
          if (this.kind === 'cpu') for (const ai of this.ais) ai.L = S.AI_LEVELS[st.difficulty];
          break;
        }
        case 'hints': st.hints = !st.hints; this.save(); refresh(); break;
        case 'hudGuide': st.hudGuide = st.hudGuide !== true; this.save(); refresh(); break;   // (the guide starts hidden)
        case 'hudMap': case 'hudBonus': case 'hudGoal': case 'hudMeter': case 'hudTips': case 'hudCtx': st[a] = st[a] === false; this.save(); refresh(); break;   // (stealth level HUD pieces)
        case 'style': st[this.styleKey] = st[this.styleKey] === 'anime' ? 'classic' : 'anime'; this.R.setAnime(st[this.styleKey] === 'anime'); this.save(); refresh(); break;
        case 'endless': st.endless = !st.endless; this.save(); refresh(); break;
        case 'sound': st.sound = !st.sound; this.audio.muted = !st.sound; this.save(); refresh(); break;
        case 'debug': this.toggleDebug(); break;
        case 'fullscreen': if (window.kumiteDesktop) { window.kumiteDesktop.toggleFullScreen(); setTimeout(refresh, 150); } break;
        case 'quitApp': if (window.kumiteDesktop) window.kumiteDesktop.quit(); break;
        case 'controls': ui.show('controls'); break;
        case 'binds': ui.show('binds'); break;
        case 'pstage': { // pick the stage from the menus; in Training it changes there and then
          const L = S.STAGES, i = Math.max(0, L.findIndex((x) => x.id === S.profile.stage));
          S.profile.stage = L[(i + (dir || 1) + L.length) % L.length].id; S.profile.save();
          if (this.kind === 'training' && this.match) { const id = S.stageFor(S.profile.stage); this.R.setStage(id); this.match.stage = id; }
          this.audio.blip(false); refresh(); break;
        }
        case 'bindReset': S.profile.binds = {}; S.profile.save(); S.applyBinds({}); refresh(); this.audio.blip(true); break;
        case 'back': this.back(); break;
        case 'begin': this.seenTut = true; this.save(); this.startGame(); break;
        case 'resume': this.pause(false); break;
        case 'skip': this.paused = false; ui.hide(); if (this.tut) this.tut.skip(); break;
        case 'prevLesson': this.paused = false; ui.hide(); if (this.tut) this.tut.prev(); break;
        case 'replayLesson': this.paused = false; ui.hide(); if (this.tut) this.tut.replay(); break;
        case 'restart': this.paused = false; if (this.tut) this.startTutorial(); else if (this.kind === 'training') this.startTraining(); else if (this.kind === 'boss') this.setupMatch(this.sel.c1 || 0, 0, 'boss'); else this.startGame(); break;
        case 'quit': if (this.campSaved) { this.paused = false; this.rematchT = 0; this.leaveBoss('quit'); break; } this.ui.training(null); this.paused = false; this.rematchT = 0; this.R.camOverride = null; ui.show('title'); this.startAttract(); break;
        case 'rematch': this.rematchT = 0; this.startGame(); break;
        case 'select': this.rematchT = 0; this.sel.lock1 = this.sel.lock2 = false; ui.show('select', this.sel); break;
        default: if (act.indexOf('item:') === 0) this.lockerBuy(act.slice(5));
      }
    }
    // keep the phone screen up to date as phones come and go
    watchPhones() {
      S.phones.onChange = () => {
        if (this.ui.name !== 'phones') { if (S.phones.slots.some(Boolean)) this.audio.blip(true); return; }
        const f = this.ui.focus; this.ui.show('phones'); this.ui.focus = Math.min(f, this.ui.items.length - 1); this.ui.highlight(); this.audio.blip(true);
      };
    }
    pollPad() {
      const p = S.readPad(0);
      if (!p) return;
      const prev = this.padPrev, ui = this.ui;
      const edge = (k, v) => { const r = v && !prev[k]; prev[k] = v; return r; };
      const up = edge('up', p.mz < -0.5), dn = edge('dn', p.mz > 0.5), lf = edge('lf', p.mx < -0.5), rt = edge('rt', p.mx > 0.5);
      const a = edge('a', p.push), b = edge('b', p.grab), st = edge('st', p.start);
      if (st || a || b || up || dn) this.audio.init();
      if (this.camp && this.camp.maskOpen) { if (up) this.camp.maskMove(-1); if (dn) this.camp.maskMove(1); if (a || st) this.camp.pickMask(this.camp.maskI); return; } // the mask picker: one step per push
      if (ui.name === 'select') {
        if (lf || up) this.selectKey('KeyA'); if (rt || dn) this.selectKey('KeyD'); if (a) this.lockSel(1); if (b) this.selectKey('Escape');
      } else if (ui.name) {
        if (up) ui.nav(-1); if (dn) ui.nav(1);
        if ((lf || rt) && this.isOption(ui.current())) ui.activate(lf ? -1 : 1);
        if (a) ui.activate(1); if (b) this.back();
      } else if (this.awaitGacha && a) this.confirmGacha();
      else if (st && this.mode === 'game') this.pause(true);
      else if (st && this.camp) this.camp.onKey({ code: 'Escape' });
    }
  }

  window.addEventListener('load', () => { S.game = new Game(); });
})();
