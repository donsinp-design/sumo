'use strict';
// CAMPAIGN: a single-player brawler through the fish market (camp-map.js), ending in a sumo boss fight.
// Its own little engine, drawn with the same cel look as the main game (toon shading, ink outlines, the anime
// pass) and the same wrestler model for you, the sumo enemies and the boss.
//
// Controls (same buttons as the main game):
//   J  slap string (3 hits)            K  grab an enemy or a prop / throw what you hold
//   L  tap alone: PARRY (hold: block)  L + direction, tap: dodge · hold: CHARGE (breaks light and medium things)
//   SPACE  your skill (from a drink machine; recharges)     Esc  pause
(function () {
  const STEP = 1 / 120;
  const TAU = Math.PI * 2;
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const ang = (a) => { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; };
  const rnd = (a, b) => a + Math.random() * (b - a);

  // ---------------------------------------------------------------- props
  // weight: light (thrown far, breaks easily), medium (charge breaks it), heavy (stops a charge), tuna (heavy weapon)
  const PROPS = {
    crate:   { r: 0.36, h: 0.5,  hp: 2, pick: true,  wt: 'medium', dmg: 18, breaks: true,  col: 0xb07a44, shade: 0x5a3a1a },
    crate2:  { r: 0.42, h: 1.0,  hp: 3, pick: false, wt: 'medium', dmg: 0,  breaks: true,  col: 0xa87040, shade: 0x553418, into: 'crate' },
    foam:    { r: 0.34, h: 0.34, hp: 1, pick: true,  wt: 'light',  dmg: 9,  breaks: true,  col: 0xf6f6f0, shade: 0xa8b0b8 },
    bottle:  { r: 0.14, h: 0.32, hp: 1, pick: true,  wt: 'light',  dmg: 12, breaks: true,  col: 0x3a9a5a, shade: 0x1a4a2a },
    can:     { r: 0.1,  h: 0.13, hp: 1, pick: true,  wt: 'light',  dmg: 9,  breaks: true,  col: 0xe2322b, shade: 0x6e1018 },
    chair:   { r: 0.3,  h: 0.8,  hp: 1, pick: true,  wt: 'light',  dmg: 14, breaks: true,  col: 0xd84a3a, shade: 0x6a1a14 },
    bin:     { r: 0.34, h: 0.75, hp: 3, pick: true,  wt: 'medium', dmg: 20, breaks: false, col: 0x3a7ad0, shade: 0x1a3a6a },
    bucket:  { r: 0.24, h: 0.35, hp: 1, pick: true,  wt: 'light',  dmg: 7,  breaks: true,  col: 0xf2c14e, shade: 0x8a6a1a, splash: true },
    pallet:  { r: 0.55, h: 0.15, hp: 2, pick: false, wt: 'medium', dmg: 0,  breaks: true,  col: 0xc8a070, shade: 0x6a4a2a },
    cart:    { r: 0.6,  h: 0.9,  hp: 99, pick: false, wt: 'heavy', dmg: 0,  breaks: false, col: 0x8a96a2, shade: 0x3a4652, roll: true },
    barrier: { r: 0.55, h: 0.9,  hp: 99, pick: false, wt: 'heavy', dmg: 0,  breaks: false, col: 0xf2c14e, shade: 0x1a1a1a },
    tuna:    { r: 0.5,  h: 0.45, hp: 99, pick: true,  wt: 'tuna',  dmg: 30, breaks: false, col: 0x4a5a78, shade: 0x1a2236 },
    knife:   { r: 0.16, h: 0.06, hp: 99, pick: true, wt: 'light', dmg: 20, breaks: false, col: 0xd8dde4, shade: 0x6a7280, blade: true },
    onigiri: { r: 0.22, h: 0.25, hp: 1, pick: false, wt: 'light',  dmg: 0,  breaks: false, col: 0xf6f2ea, shade: 0xb8b0a0, heal: true },
  };

  // ---------------------------------------------------------------- enemies (the roster from the design brief)
  const KINDS = {
    fighter:   { hp: 45,  spd: 3.1, r: 0.42, mass: 1,   name: 'FIGHTER',   shirt: 0x2f6fd0, apron: 0xf6f6f0, band: 0xf6f6f0 },
    rusher:    { hp: 38,  spd: 4.3, r: 0.4,  mass: 0.9, name: 'RUSHER',    shirt: 0xe2322b, apron: 0x2a2a30, band: 0xe2322b },
    technical: { hp: 50,  spd: 3.3, r: 0.42, mass: 1,   name: 'TECHNICAL', shirt: 0x1a2a5a, apron: 0x1a2a5a, band: 0x101010, glasses: true },
    grappler:  { hp: 65,  spd: 2.6, r: 0.48, mass: 1.6, name: 'GRAPPLER',  shirt: 0x2e9e6a, apron: 0x3a2a20, band: 0xf2c14e },
    thrower:   { hp: 32,  spd: 3.4, r: 0.4,  mass: 0.9, name: 'THROWER',   shirt: 0xf2c14e, apron: 0x4a4a52, band: 0x2a2a30, cap: true },
    staff:     { hp: 50,  spd: 2.9, r: 0.42, mass: 1.1, name: 'STAFF',     shirt: 0x7a4ab0, apron: 0x2a2a30, band: 0xf6f6f0, pole: true },
    commander: { hp: 70,  spd: 2.7, r: 0.45, mass: 1.3, name: 'COMMANDER', shirt: 0xc8231d, apron: 0xf2c14e, band: 0xf2c14e, coat: true },
    sumo:      { hp: 110, spd: 2.5, r: 0.85, mass: 6,   name: 'SUMO',      wrestler: 1, size: 1.25 },
    boss:      { hp: 420, spd: 2.4, r: 1.05, mass: 12,  name: 'ŌZEKI MAGURO-YAMA', wrestler: 1, size: 1.6 },
  };

  // skills (sold by the drink machines) and masks: camp-skills.js
  const POOL = S.CampSkills.POOL;

  class Campaign {
    constructor(game) { this.g = game; }

    // ============================================================== setup / teardown
    start() {
      const g = this.g;
      this.R = g.R; this.t = 0; this.acc = 0; this.paused = false; this.over = null; this.slow = 0; this.hitstop = 0;
      this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0xa9cad1);
      this.cam = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 220);
      this.fx = new S.FX(this.scene); this.fx.scene = this.scene; this.fx.noMarks = true; // no footprints piling up over a whole level
      const nFx = this.scene.children.length;
      this.map = S.CampMap.build(this.scene);
      if (S.CampFlat) S.CampFlat.setup(this); // the flat look: soft sun, pastel master material, the rebuilt first street
      { // the market never moves: work out its transforms once instead of for thousands of objects every frame
        const swing = new Set(this.map.decor.filter((d) => d.kind === 'lantern' || d.kind === 'arrow').map((d) => d.m)); // these move
        this.scene.updateMatrixWorld(true);
        for (const o of this.scene.children.slice(nFx)) o.traverse((q) => { if (!swing.has(q)) q.matrixAutoUpdate = false; });
      }
      this.brk = new S.CampBreak(this); // stalls, tables and drink machines come apart; floors and walls crack
      this.sk = new S.CampSkills(this); // skills and masks
      this.ctrl = new S.Controller(new S.KeySource(S.MAPS.solo, 0));
      this.actors = []; this.props = []; this.shots = []; this.zones = this.map.zones.map((z) => Object.assign({ state: 'wait', ens: [] }, z));
      this.zi = 0; this.gate = this.zones[0].z1; this.ability = null; this.abCd = 0; this.fires = [];
      for (const p of this.map.props) this.addProp(p.type, p.x, p.z, p.ry);
      const arch = S.ARCH[g.sel && g.sel.c1 !== undefined ? g.sel.c1 : 0];
      this.P = this.addActor('player', this.map.start.x, this.map.start.z, { arch, lo: S.profile.loadout() });
      this.P.f = -Math.PI / 2; this.arch = arch; this.score = 0; this.scoreCp = 0;
      this.camT = new THREE.Vector3(this.P.x, 0, this.P.z - 2.5);
      // everyone is already in place when the market opens: fixed spots (learnable for speedruns), asleep until you walk in
      this.zones.forEach((Z, i) => this.populate(Z, i));
      this.runT = 0; this.hits = 0; this.usedSkill = false; this.mult = 1; this.chain = 0; this.chainT = 0; this.beat = 0;
      try { this.R.r.compile(this.scene, this.cam); } catch (e) { /* warm the shaders up front: no hitch when an area wakes */ }
      this.buildHud();
      this.resize = () => { this.cam.aspect = innerWidth / innerHeight; this.cam.updateProjectionMatrix(); this.fx.pmat.uniforms.uScale.value = innerHeight * this.R.r.getPixelRatio() / (2 * Math.tan(this.cam.fov * Math.PI / 360)); };
      addEventListener('resize', this.resize); this.resize();
      this.say('UOGASHI MARKET', 'Fight your way to the tuna auction', 3.5);
      this.prompt('Get a skill from the drink machine (walk up, press K)');
      g.audio.swell(0.4, 1.5);
      this.openMasks();
    }
    stop() {
      removeEventListener('resize', this.resize);
      if (this.flat) { this.R.r.shadowMap.enabled = false; this.R.r.localClippingEnabled = false; const vg = document.getElementById('vignette'); if (vg) vg.style.display = ''; }
      if (this.hud) this.hud.remove();
      this.scene = null;
    }

    // ============================================================== actors
    addActor(kind, x, z, o) {
      o = o || {};
      const K = kind === 'player' ? { hp: 100, spd: 4.3, r: 0.55, mass: 2.2 } : KINDS[kind];
      const big = kind === 'sumo' || kind === 'boss', fat = o.fat && !big;
      const a = { kind, x, z, y: 0, vx: 0, vz: 0, vy: 0, f: Math.PI / 2, r: K.r, mass: K.mass * (fat ? 1.6 : 1), hp: K.hp * (fat ? 1.35 : 1),
        spd: K.spd * (o.fat ? 0.82 : 1), fat: !!o.fat, st: 'free', t: 0, dur: 0, team: kind === 'player' ? 0 : 1, cd: rnd(0.6, 1.6), iframe: 0,
        hitLog: [], stun: 0, slow: 0, buff: 0, zone: o.zone, dead: false, held: null, holder: null, combo: 0, lastStrike: -9, frozen: 0, blind: 0, burn: 0 };
      a.maxHp = a.hp;
      if (kind === 'boss') { a.phase = 1; a.st = 'intro'; a.t = 0; }
      if (K.wrestler || kind === 'player') {
        const arch = o.arch || S.ARCH[1];
        a.view = new S.WrestlerView(this.scene, arch, this.fx, o.lo || (kind === 'player' ? S.DEF_EQ : S.profile.randomLoadout()));
        a.view.viewer = 0; a.view.match = null;
        if (this.flat && S.SoftSumo) S.SoftSumo.attach(a.view, { noBlob: true }); // the soft, rounded sumo
        if (a.view.mats) for (const m of a.view.mats) {
          if (m.uniforms && m.uniforms.uRimAmt) m.uniforms.uRimAmt.value = 0; // no rim glow in the market: it read as a halo
          if (m.fragmentShader) { m.fragmentShader = m.fragmentShader.replace('sh *= mix(vec3(1.0), vec3(0.8, 0.76, 1.1), uAnime);', 'sh *= mix(vec3(1.0), vec3(0.9, 0.86, 0.9), uAnime);'); m.needsUpdate = true; } // a warm skin shadow, not a violet one (that read as a pink sash)
        }
        a.w = { x, z, y: 0, f: a.f, fx: 0, fz: 1, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, fxs: {}, a: arch, idx: kind === 'player' ? 0 : 1, szCur: K.size || 1,
          squash: 0, bal: 1, tx: 0, tz: 0, power: 0, pre: null, preT: 0, hand: 0, windPow: 0, charges: 0, uprightT: 0, throatT: 0, lifted: false, down: false,
          fallX: 0, fallZ: 1, clinch: null, slideT: 0, spd: 0, crouchT: 0, lean: 0, gulpI: -1, contact: false, fwdIn: 0, ddx: 0, ddz: 0, boomT: 0 };
        a.size = K.size || 1;
      } else { a.view = new WorkerView(this.scene, kind, a.fat, o.pick); a.view.walls = this.map.walls; }
      this.actors.push(a);
      return a;
    }
    addProp(type, x, z, ry) {
      const D = PROPS[type];
      const p = { type, D, x, z, y: 0, vx: 0, vz: 0, vy: 0, r: D.r, hp: D.hp, held: null, thrown: null, ry: ry || 0, spin: 0, dead: false };
      p.mesh = propMesh(type); p.mesh.position.set(x, 0, z); p.mesh.rotation.y = p.ry;
      // Slightly oversized props stay readable at gameplay distance and share
      // the chunky environment scale without changing collision/navigation.
      if (!['tuna', 'onigiri', 'knife'].includes(type)) p.mesh.scale.setScalar(type === 'bottle' ? 1.22 : 1.14);
      this.scene.add(p.mesh);
      if (this.flat && S.CampFlat) S.CampFlat.swapProp(this, p); // the kit's chunky props (already at their own scale)
      this.props.push(p);
      return p;
    }

    // ============================================================== HUD
    buildHud() {
      { const tp = document.getElementById('tutPanel'); if (tp) tp.classList.remove('on'); }
      const h = this.hud = document.createElement('div'); h.id = 'campHud';
      const name = (this.arch && this.arch.name) || 'TAKAKAZE';
      h.innerHTML = '<div class="ch-me"><div class="ch-score">0000000</div><span class="ch-bar"><i></i></span><span class="ch-stam"><i></i></span><b class="ch-name">' + name + '</b></div>' +
        '<div class="ch-time">0:00</div><div class="ch-hurt"></div>' +
        '<div class="ch-yen"><span class="jp">円</span><b>0</b><span>YEN</span></div>' +
        '<div class="ch-sifu"><div class="ch-mul"><b>x1</b><small>Multiplier</small></div><i></i><div class="ch-sc"><b>0</b><small>Level Score</small></div></div>' +
        '<div class="ch-ab"><em>NO SKILL</em><kbd>SPACE</kbd><span class="ch-cd"><i></i></span></div>' +
        '<div class="ch-zone"></div><div class="ch-say"><b></b><span></span></div><div class="ch-prompt"></div>' +
        '<div class="ch-boss"><div class="ch-score">BOSS</div><span class="ch-bar"><i></i></span><b class="ch-name"></b></div><div class="ch-bars"></div>' +
        '<div class="ch-card"><div class="ch-cap"></div><b></b><span></span><em>' + (S.touch && S.touch.on ? 'GRAB or SKILL' : 'K or SPACE') + ' to keep it</em></div>' +
        '<div class="ch-pause"><h2 data-jp="一時停止">PAUSED</h2><button data-c="resume">RESUME</button><button data-c="retry">RESTART AREA</button><button data-c="quit">QUIT TO TITLE</button><p>J slap ×3 · K grab / throw · L parry (tap it when the ! turns gold) · L+dir dodge, hold to CHARGE · SPACE skill</p></div>' +
        '<div class="ch-shop"></div><div class="ch-mask"></div>' +
        '<div class="ch-over"><h2 data-jp=""></h2><p></p><button data-c="retry">TRY AGAIN <kbd>J</kbd></button><button data-c="quit">QUIT TO TITLE <kbd>Esc</kbd></button></div>';
      document.body.appendChild(h);
      h.addEventListener('click', (e) => {
        const b = e.target.closest('[data-c]'); if (b) this.command(b.dataset.c);
        const sb = e.target.closest('[data-shop]'); if (sb) this.sk.pick(sb.dataset.shop === 'x' ? 'x' : +sb.dataset.shop);
        const mb = e.target.closest('[data-mask]'); if (mb) this.pickMask(+mb.dataset.mask);
      });
      h.addEventListener('mousemove', (e) => { // only a real mouse move picks a row (redrawing under a still cursor must not steal the keyboard's choice)
        if (!this.maskOpen || (e.movementX === 0 && e.movementY === 0)) return; const mb = e.target.closest('[data-mask]'); if (mb && +mb.dataset.mask !== this.maskI) { this.maskI = +mb.dataset.mask; this.markMask(); }
      });
      this.el = (s) => h.querySelector(s);
      this.barEls = [];
    }
    addScore(n, raw) { if (this.over) return; const g = Math.round(n * (raw ? 1 : this.mult || 1) * (this.sk && this.sk.mask.id === 'hannya' ? 2 : 1)); this.score = (this.score || 0) + g; this.scoreBump = 1; }
    chainHit() { this.chain = (this.chain || 0) + 1; this.chainT = 0; const m = Math.min(8, 1 + Math.floor(this.chain / 4)); if (m > (this.mult || 1)) { this.mult = m; this.mulBump = 1; } }
    chainBreak() { if ((this.mult || 1) > 1) this.mulBump = 1; this.chain = 0; this.mult = 1; }
    say(big, small, dur) { const e = this.el('.ch-say'); e.querySelector('b').textContent = big; e.querySelector('span').textContent = small || ''; e.classList.add('on'); clearTimeout(this.sayT); this.sayT = setTimeout(() => e.classList.remove('on'), (dur || 2.5) * 1000); }
    prompt(t) {
      if (t && S.touch && S.touch.on) t = t.replace(/\b([Pp])ress (J|K|L|SPACE)\b|\b(J|K|L|SPACE)\b/g, (m, P, k1, k2) => { const k = k1 || k2, n = { J: 'PUSH', K: 'GRAB', L: 'DEFEND', SPACE: 'SKILL' }[k]; return P ? (P === 'P' ? 'Tap ' : 'tap ') + n : n; });
      const e = this.el('.ch-prompt'); e.textContent = t || ''; e.classList.toggle('on', !!t); }
    command(c) {
      if (c === 'resume') this.setPause(false);
      else if (c === 'retry') { this.setPause(false); this.retry(); }
      else if (c === 'quit') { this.g.endCampaign(); }
    }
    setPause(on) { this.paused = on; this.el('.ch-pause').classList.toggle('on', on); }
    onKey(e) {
      if (this.maskOpen) { if (e.repeat) return true; if (e.code === 'ArrowUp' || e.code === 'KeyW') this.maskMove(-1); else if (e.code === 'ArrowDown' || e.code === 'KeyS') this.maskMove(1); else if (e.code === 'Enter' || e.code === 'NumpadEnter') this.pickMask(this.maskI); return true; } // keys move one step per press; Enter wears it
      if (this.shopping) { if (e.code === 'Escape') this.sk.pick('x'); return true; }
      if (e.code === 'Escape' || e.code === 'KeyP') { if (this.over) return; this.setPause(!this.paused); return true; }
      if (this.paused) { if (e.code === 'KeyR') this.command('retry'); else if (e.code === 'KeyQ') this.command('quit'); else if (e.code === 'Enter' || e.code === 'KeyJ') this.command('resume'); return true; }
      if (this.over) { if (!this.el('.ch-over').classList.contains('on')) return true; if (e.code === 'Enter' || e.code === 'KeyJ' || e.code === 'KeyR' || e.code === 'Space') this.command(this.over === 'win' ? 'quit' : 'retry'); else if (e.code === 'KeyQ' || e.code === 'Escape') this.command('quit'); /* K (grab) never quits: mashing it must not throw the run away */ return true; }
      return false;
    }

    // ============================================================== main frame
    frame(dt) {
      if (!this.scene) return;
      const g = this.g;
      if (!this.paused && !this.cardOpen && !this.maskOpen) {
        if (this.hitstop > 0) this.hitstop -= dt;
        else {
          const ts = this.slow > 0 ? 0.35 : 1; if (this.slow > 0) this.slow -= dt;
          this.acc += dt * ts; let n = 0;
          while (this.acc >= STEP && n < 12) { this.ctrl.update(STEP);
            if (this.overT > 0.4 && this.ctrl.push.pressed) { this.acc = 0; this.command(this.over === 'win' ? 'quit' : 'retry'); return; }
            this.step(STEP); S.kb.flush && 0; this.acc -= STEP; n++; }
          if (n >= 12) this.acc = 0;
        }
      } else if (this.maskOpen) { this.ctrl.update(dt); this.maskInput(); }
      else if (this.shopping) { this.ctrl.update(dt); const k = this.ctrl; if (k.push.pressed) this.sk.pick(0); else if (k.grab.pressed) this.sk.pick(1); else if (k.dash.pressed) this.sk.pick(2); }
      else if (this.cardOpen) { this.ctrl.update(dt); if (this.ctrl.grab.pressed || this.ctrl.skill.pressed || this.ctrl.push.pressed) this.closeCard(); }
      // the result screen answers the slap button however it's mapped (keys, pad, phone): J = try again / continue, K = quit
      if (this.over && this.el('.ch-over').classList.contains('on')) {
        this.overT = (this.overT || 0) + dt;
      } else this.overT = 0;
      S.kb.flush();
      this.draw(dt);
      void g;
    }

    // ============================================================== simulation
    step(dt) {
      if (!this.over) this.runT = (this.runT || 0) + dt; // the speedrun clock (shown on the result, not on screen)
      // SECOND WIND: in the red (under 30%), stay out of trouble for 4s and you catch your breath, back up to 40%
      { const P0 = this.P; if (!P0.dead && !this.over && P0.hp < P0.maxHp * 0.4 && (P0.redT || P0.hp < P0.maxHp * 0.3)) {
          if (P0.hp < P0.maxHp * 0.3) P0.redT = true;
          if (this.t - (P0.lastHit || -99) > 4) { P0.hp = Math.min(P0.maxHp * 0.4, P0.hp + P0.maxHp * 0.08 * dt); if (P0.hp >= P0.maxHp * 0.4 - 1e-6) P0.redT = false; }
        } else if (P0.hp >= P0.maxHp * 0.4) P0.redT = false; }
      this.chainT = (this.chainT || 0) + dt; if (this.chainT > 6 && this.mult > 1) { this.mult--; this.chain = (this.mult - 1) * 4; this.chainT = 3; this.mulBump = 1; }
      this.t += dt;
      const P = this.P;
      this.flow(dt);
      this.playerStep(P, dt);
      for (const a of this.actors) if (a !== P) this.enemyStep(a, dt * this.sk.tscale(a));
      for (const a of this.actors) this.physics(a, dt * this.sk.tscale(a));
      this.separate();
      this.propStep(dt);
      this.shotStep(dt);
      this.fireStep(dt); this.sk.step(dt);
      if (this.abCd > 0) this.abCd -= dt;
      // tidy up the knocked-out
      for (const a of this.actors) if (a !== this.P && a.dead && a.t > 2.2 && !a.gone) { this.dropCarry(a); a.gone = true; a.view.dispose ? a.view.dispose(this.scene) : 0; }
      this.actors = this.actors.filter((a) => !a.gone);
    }

    // zones: wake enemies when you walk in, open the way on when the zone is clear
    // one open market: no gates or areas. Each sleeper notices you on its own (close enough, or a neighbour already fighting);
    // the boss wakes when you step onto the auction floor; beating him wins.
    flow(dt) {
      const P = this.P;
      const here = this.zones.findIndex((z) => P.z <= z.z0 && P.z > z.z1); if (here > (this.cp || 0)) { this.cp = here; this.scoreCp = this.score; } // checkpoint: the furthest area you've reached
      for (const Z of this.zones) {
        for (const e of Z.ens) {
          if (!e.sleep || e.dead) continue;
          const d = Math.hypot(P.x - e.x, P.z - e.z), near = Z.boss ? P.z < Z.z0 - 1 : d < 9.5 || Z.ens.some((o) => !o.sleep && !o.dead && Math.hypot(o.x - e.x, o.z - e.z) < 6 && Math.hypot(P.x - o.x, P.z - o.z) < 9);
          if (near) { e.sleep = false; if (Z.state === 'wait') { Z.state = 'fight'; this.wakeZone(Z); } }
        }
        if (Z.state === 'fight' && Z.boss && Z.ens.every((e) => e.dead) && !this.over) { Z.state = 'clear'; this.win(); }
      }
    }
    // put a zone's people in their fixed places, asleep
    populate(Z, zi) {
      Z.ens = [];
      if (Z.boss) { const B = this.addActor('boss', Z.boss.x, Z.boss.z - 6, { zone: Z }); B.f = Math.PI / 2; B.sleep = true; this.B = B; Z.ens.push(B); return; }
      Z.spawns.forEach(([kind, x, z, fat], si) => { const e = this.addActor(kind, x, z, { fat: fat === 'fat', zone: Z, pick: (zi * 3 + si * 2) % 5 }); e.f = Math.PI / 2; e.sleep = true; e.cd = 0.8 + si * 0.25; Z.ens.push(e); });
    }
    // you walked in: they notice you
    wakeZone(Z) {
      if (Z.boss) {
        this.B = Z.ens[0]; this.B.st = 'intro'; this.B.t = 0;
        this.el('.ch-boss').classList.add('on'); this.el('.ch-boss b').textContent = KINDS.boss.name;
        this.say(KINDS.boss.name, 'Champion of the tuna auction', 3); this.g.audio.roar(); this.g.audio.taiko();
        return;
      }
      if (Z.spawns.some((sp) => sp[0] === 'sumo') && !this.sumoTip) { // first sumo: say how to beat him
        this.sumoTip = true;
        this.prompt('SUMO: too heavy to push. Make him crash into a cart or wall, parry him (tap L), or throw crates at him, then grab (K)');
        clearTimeout(this.tipT); this.tipT = setTimeout(() => this.prompt(''), 9000);
      }
    }
    retry() {
      const zi = this.cp || 0, Z = this.zones[zi]; this.zi = zi;
      this.over = null; this.el('.ch-over').classList.remove('on');
      this.actors = this.actors.filter((a) => { if (a !== this.P && a.zone === Z) { this.dropCarry(a); if (a.bang) this.scene.remove(a.bang); if (a.view.dispose) a.view.dispose(this.scene); return false; } return true; });
      Z.state = 'wait'; Z.bossDone = false; this.B = null; this.el('.ch-boss').classList.remove('on');
      this.populate(Z, this.zi);
      const P = this.P; P.hp = P.maxHp; P.stam = 1; P.dead = false; this.score = this.scoreCp || 0; P.st = 'free'; P.t = 0; P.held = null; P.holder = null;
      P.x = 0; P.z = Z.z0 - 1; P.vx = P.vz = 0; this.shots = [];
    }
    win() {
      this.over = 'win'; this.slow = 1.2;
      setTimeout(() => {
        const o = this.el('.ch-over'); o.querySelector('h2').textContent = 'VICTORY'; o.querySelector('h2').dataset.jp = '勝利';
        const t = this.runT || 0, PAR = 360, noHit = !this.hits, noSkill = !this.usedSkill, fast = t < PAR;
        let best = 0; try { best = +localStorage.getItem('kumite.campBest') || 0; if (!best || t < best) localStorage.setItem('kumite.campBest', String(t)); } catch (e) { /* private mode */ }
        const yen = 200000 + (noHit ? 100000 : 0) + (noSkill ? 50000 : 0) + (fast ? 50000 : 0);
        const badge = (on, txt) => '<span class="ch-badge' + (on ? ' on' : '') + '">' + txt + '</span>';
        const bonus = (noHit ? 50000 : 0) + (noSkill ? 20000 : 0) + (fast ? 20000 : 0); this.addScore(bonus, true);
        o.querySelector('p').innerHTML = '<div class="ch-total">' + String(this.score).padStart(7, '0') + '</div>' +
          'Time ' + fmtT(t) + (best && t >= best ? ' · best ' + fmtT(best) : best ? ' · new best' : '') + ' · hits taken ' + (this.hits || 0) + '<br>' +
          badge(noHit, 'NO HIT') + badge(noSkill, 'NO SKILL') + badge(fast, 'UNDER ' + fmtT(PAR).slice(0, -2)) + '<br>+' + yen.toLocaleString() + ' yen';
        o.querySelector('[data-c="retry"]').style.display = 'none'; o.classList.add('on');
        S.profile.yen += yen; S.profile.save && S.profile.save(); this.g.ui.setYen && this.g.ui.setYen();
      }, 1600);
      this.g.audio.roar(); this.g.audio.taiko();
    }
    lose() {
      if (this.over) return; this.over = 'lose';
      setTimeout(() => { const o = this.el('.ch-over'); o.querySelector('h2').textContent = 'DEFEATED'; o.querySelector('h2').dataset.jp = '敗北'; o.querySelector('p').textContent = 'Try this area again'; o.querySelector('[data-c="retry"]').style.display = ''; o.classList.add('on'); }, 1200);
    }

    // ============================================================== the player
    playerStep(P, dt) {
      const c = this.ctrl;
      P.t += dt; if (P.iframe > 0) P.iframe -= dt; if (P.giant > 0) P.giant -= dt; if (P.iron > 0) P.iron -= dt;
      if (P.dead) { P.vx *= 0.9; P.vz *= 0.9; return; }
      let mx = c.mx, mz = c.mz; const mag = Math.hypot(mx, mz);
      if (mag > 1) { mx /= mag; mz /= mag; }
      const dirA = mag > 0.3 ? Math.atan2(mz, mx) : P.f;
      const heavy = (P.poison > 0 ? 0.6 : 1) * (this.sk.mask.id === 'fish' ? 0.85 : 1);
      const wantMove = (sp, turn) => { sp *= heavy; P.tvx = mx * sp; P.tvz = mz * sp; if (mag > 0.3) P.f += ang(dirA - P.f) * Math.min(1, dt * (turn || 14)); };
      P.tvx = 0; P.tvz = 0;
      const giant = P.giant > 0 ? 1.35 : 1;
      // STAMINA (as in versus): dodges, charges, slaps and throws spend it; it comes back when you ease off. Run dry and you're slow and weak
      if (P.stam === undefined) P.stam = 1;
      if (P.stamT > 0) P.stamT -= dt; else P.stam = Math.min(1, P.stam + dt * (P.st === 'free' ? 0.34 : 0.2));
      if (this.sk.player(P, dt, mx, mz)) { if (c.skill.pressed && this.ability && this.abCd <= 0 && !this.sk.gulp && !P.sk) this.useAbility(); return; } // a skill is driving (cyclone, daruma, torpedo...)
      // the ability (space)
      if (c.skill.pressed && this.ability && this.abCd <= 0 && !this.sk.gulp && ['free', 'hold', 'strike'].includes(P.st)) this.useAbility();
      // drink machines sell skills: one each (a new one replaces the one you have)
      let vm = null; for (const b of this.map.breakables) if (b.kind === 'vend' && !b.broken && !b.used && Math.hypot(P.x - (b.x + b.fx * 0.7), P.z - (b.z + b.fz * 0.7)) < 1.5) vm = b;
      const nearG = !!vm, atStart = P.z > -11 && !this.ability;
      if (nearG !== this.nearSkill || atStart !== this.atStart) { this.nearSkill = nearG; this.atStart = atStart; this.prompt(nearG ? (this.ability ? 'K: swap your skill' : 'K: get a skill') : atStart ? 'Get a skill from the drink machine (walk up, press K)' : ''); }
      switch (P.st) {
        case 'free': {
          wantMove(4.3 * giant);
          if (c.push.pressed) this.strike(P);
          else if (c.grab.pressed) { if (vm) this.getSkill(vm); else { this.aim(P, 1.8); this.set(P, 'grab', 0.22); this.spend(P, 0.04); } }
          else if (c.dash.pressed) { if (mag > 0.3) { this.set(P, 'lprep', 0.14); P.ldir = dirA; } else { this.set(P, 'parry', 0.42); this.g.audio.whoosh(0.08); } }
          break;
        }
        case 'strike': {
          wantMove(1.2, 6);
          const act = P.combo === 3 ? 0.14 : 0.08;
          if (!P.hitDone && P.t >= act) { P.hitDone = true; this.meleeHit(P, P.combo === 3 ? 1.45 : 1.25, 1.1, P.combo === 3 ? 16 : 8, P.combo === 3 ? 7 : 2.6, P.combo === 3); }
          if (P.t > P.dur * 0.6 && c.push.pressed) { P.queue = true; }
          if (P.t >= P.dur) { P.lastStrike = this.t; if (P.queue && P.combo < 3) { P.queue = false; this.strike(P); } else this.set(P, 'free'); }
          break;
        }
        case 'grab': {
          wantMove(0.8, 10);
          if (!P.hitDone && P.t >= 0.07) { P.hitDone = true; if (!this.tryGrab(P)) P.dur = 0.36; }
          if (P.t >= P.dur && P.st === 'grab') this.set(P, 'free');
          break;
        }
        case 'slam': {
          P.tvx = 0; P.tvz = 0;
          if (P.t >= 0.24 && !P.slamDone) { P.slamDone = true; if (P.held && !P.held.D && !P.held.dead) this.slamHit(P, P.held); }
          if (P.t >= P.dur) this.set(P, 'recover', 0.22);
          break;
        }
        case 'hold': {
          wantMove(3.0, 12);
          const H = P.held;
          if (!H || H.dead || (H.st && H.st !== 'held' && !H.D)) { P.held = null; this.set(P, 'free'); break; }
          if (!H.D) { // holding an enemy: J knees them, K throws; they break free after a while
            if (c.push.pressed && (P.knees || 0) < 3) { P.knees = (P.knees || 0) + 1; this.damage(H, 7, P, 0, 0, false); this.g.audio.thump(3); this.R && this.hitFx(H.x, H.z, 0.6); }
            if (c.grab.pressed) { if (Math.hypot(c.mx, c.mz) > 0.3) P.f = Math.atan2(c.mz, c.mx); this.slam(P); } // K slams them down (aimed where you push)
            else if (c.push.pressed && P.knees >= 3) this.throwHeld(P);
            else if (P.t > 2.6) { this.release(P, true); }
          } else if (c.grab.pressed || c.push.pressed) this.throwHeld(P);
          break;
        }
        case 'throw': wantMove(0.6); if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'btoss': { // belly toss: lift (0-0.3s), heave over in an arc (0.3-0.62s), impact
          const B = P.tossT, fx = Math.cos(P.f), fz = Math.sin(P.f), t = P.t;
          P.vx = P.vz = 0; // planted: the heave comes from the legs
          if (B && !B.dead && B.st === 'tossed') {
            const d0 = P.r + B.r * 0.7;
            if (t < 0.3) { const k = t / 0.3, e = k * k * (3 - 2 * k); B.x = P.x + fx * d0; B.z = P.z + fz * d0; B.y = 0.75 * e; if (t > 0.05 && !P.tossUp) { P.tossUp = true; this.g.audio.whoosh(0.3); } }
            else { const k = Math.min(1, (t - 0.3) / 0.32), d = d0 + 2.3 * k; B.x = P.x + fx * d; B.z = P.z + fz * d; B.y = 0.75 * (1 - k) + 1.5 * Math.sin(Math.PI * k); }
            B.f = P.f + Math.PI; B.vx = B.vz = 0;
            if (t >= 0.62 && !P.tossDone) this.tossLand(P, B);
          } else if (B && B.st === 'tossed' && !P.tossDone) this.tossLand(P, B);
          if (t >= P.dur) { P.tossT = null; P.tossUp = false; this.set(P, 'free'); }
          break;
        }
        case 'lprep': {
          wantMove(0.5);
          if (!c.dash.held) { const v = (this.tired(P) ? 6.5 : 11) * (this.sk.mask.id === 'kitsune' ? 1.9 : 1); this.spend(P, 0.16); this.set(P, 'dodge', 0.24); P.iframe = this.tired(P) ? 0.12 : this.sk.mask.id === 'kitsune' ? 0.42 : 0.26; const d = mag > 0.3 ? dirA : P.ldir; P.vx = Math.cos(d) * v; P.vz = Math.sin(d) * v; P.f = d; this.g.audio.whoosh(0.15); }
          else if (P.t >= P.dur || this.sk.mask.id === 'tengu') { if (P.stam < 0.12) { this.set(P, 'free'); this.popAt(P, 'TIRED!'); break; } this.spend(P, 0.08); this.set(P, 'charge', 1.5); P.cdir = mag > 0.3 ? dirA : P.ldir; P.f = P.cdir; P.chargeHits = new Set(); this.g.audio.whoosh(0.35); }
          break;
        }
        case 'dodge': P.tvx = P.vx * 0.9; P.tvz = P.vz * 0.9; if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'charge': {
          if (mag > 0.3) P.cdir += clamp(ang(dirA - P.cdir), -dt * 2.2, dt * 2.2);
          const sp = Math.min(9.5 * giant, 4 + P.t * 22);
          P.f = P.cdir; P.tvx = Math.cos(P.cdir) * sp; P.tvz = Math.sin(P.cdir) * sp; P.vx = P.tvx; P.vz = P.tvz;
          this.chargeHits(P, sp);
          if (P.t > 0.05 && Math.random() < 0.5) this.fx.dust(P.x - Math.cos(P.f) * 0.5, 0.05, P.z - Math.sin(P.f) * 0.5, 1, 0.2, 0.3, 0.3);
          this.spend(P, dt * 0.38);
          if (!c.dash.held || P.t >= P.dur || P.stam <= 0) this.set(P, 'recover', P.stam <= 0 ? 0.45 : 0.22); // out of breath: the charge dies
          break;
        }
        case 'parry': {
          if (P.t >= P.dur) { if (c.dash.held) this.set(P, 'block'); else this.set(P, 'free'); }
          break;
        }
        case 'block': if (!c.dash.held) this.set(P, 'free'); break;
        case 'recover': case 'bonk': wantMove(1); if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'hurt': if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'down': if (P.t >= P.dur) { this.set(P, 'getup', 0.35); P.iframe = 0.6; } break;
        case 'getup': if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'grabbed': {
          // break out: tap K right as they grab, or mash any button
          const any = c.push.pressed || c.grab.pressed || c.dash.pressed;
          if (c.grab.pressed && P.t < 0.32) P.esc = 1;
          if (any) P.esc = (P.esc || 0) + 0.2;
          const E = P.holder;
          if (!E || E.dead || E.st !== 'hold') { P.holder = null; this.set(P, 'free'); break; }
          if (P.esc >= 1) { this.escape(P, E); break; }
          P.x = E.x + Math.cos(E.f) * (E.r + P.r * 0.7); P.z = E.z + Math.sin(E.f) * (E.r + P.r * 0.7); P.vx = P.vz = 0;
          break;
        }
      }
      // giant: no grabs stick, bigger
      if (P.w) P.w.szCur += ((P.giant > 0 ? 1.45 : 1) - P.w.szCur) * Math.min(1, dt * 6);
      P.r = 0.55 * (P.w ? P.w.szCur : 1);
    }
    set(a, st, dur) { a.st = st; a.t = 0; a.dur = dur || 0; a.hitDone = false; }
    // soft auto-aim: slaps, grabs and throws turn toward the nearest enemy roughly in front of you
    aim(P, range) {
      let best = null, bd = range;
      for (const T of this.actors) {
        if (T.team === P.team || T.dead || T.st === 'held') continue;
        const dx = T.x - P.x, dz = T.z - P.z, d = Math.hypot(dx, dz) - T.r;
        if (d < bd && Math.abs(ang(Math.atan2(dz, dx) - P.f)) < 1.75) { bd = d; best = T; }
      }
      if (best) P.f = Math.atan2(best.z - P.z, best.x - P.x);
    }
    spend(P, k) { if (P !== this.P) return; P.stam = Math.max(0, (P.stam === undefined ? 1 : P.stam) - k); P.stamT = 0.55; if (P.stam <= 0 && !P.tiredPop) { P.tiredPop = true; this.popAt(P, 'TIRED!'); } if (P.stam > 0.3) P.tiredPop = false; }
    tired(P) { return P === this.P && P.stam !== undefined && P.stam < 0.15; }
    strike(P) {
      this.aim(P, 2.2); this.spend(P, 0.06);
      P.combo = this.t - P.lastStrike < 0.38 && P.combo < 3 ? P.combo + 1 : 1;
      this.set(P, 'strike', P.combo === 3 ? 0.42 : 0.26); P.queue = false; P.hand = (P.hand || 0) ^ 1;
      this.g.audio.whoosh(0.06);
    }
    // a hit in front of an attacker: everyone in the cone takes it
    meleeHit(A, reach, cone, dmg, knock, heavy) {
      let any = false;
      for (const T of this.actors) {
        if (T === A || T.team === A.team || T.dead || T.st === 'held') continue;
        const dx = T.x - A.x, dz = T.z - A.z, d = Math.hypot(dx, dz) - T.r;
        if (d > reach) continue;
        if (Math.abs(ang(Math.atan2(dz, dx) - A.f)) > cone) continue;
        // TECHNICAL: predictable spam gets parried
        if (A === this.P && T.kind === 'technical' && !['wind', 'act', 'down', 'getup'].includes(T.st)) {
          T.hitLog = T.hitLog.filter((h) => this.t - h < 1.3);
          if (T.hitLog.length >= 1) { this.parried(A, T); T.hitLog = []; continue; }
          T.hitLog.push(this.t);
        }
        const mul = (A.giant > 0 ? 1.6 : 1) * (T.stun > 0 || T.st === 'dazed' ? 1.5 : 1);
        this.damage(T, dmg * mul, A, Math.cos(A.f) * knock, Math.sin(A.f) * knock, heavy);
        any = true;
      }
      if (any) { this.g.audio.slap(heavy ? 6 : 3); this.hitstop = heavy ? 0.06 : 0.025; }
      return any;
    }
    tryGrab(P) {
      // an enemy within reach (sumo and the boss only when stunned or dazed)
      let best = null, bd = 1.25;
      for (const T of this.actors) {
        if (T === P || T.dead || T.team === P.team || ['thrown', 'held'].includes(T.st)) continue;
        if ((T.kind === 'sumo' || T.kind === 'boss') && !(T.stun > 0 || T.st === 'dazed')) continue;
        const dx = T.x - P.x, dz = T.z - P.z, d = Math.hypot(dx, dz) - T.r;
        if (d < bd && Math.abs(ang(Math.atan2(dz, dx) - P.f)) < 1.1) { bd = d; best = T; }
      }
      if (best) {
        if (best.kind === 'boss' || best.kind === 'sumo') { // a belly-toss on a dazed giant
          // hoist him onto your belly, heave him over, and drive him into the floor (btoss state below)
          P.f = Math.atan2(best.z - P.z, best.x - P.x); P.tossT = best; P.tossDone = false; this.spend(P, 0.2); P.iframe = Math.max(P.iframe || 0, 0.8);
          this.set(best, 'tossed', 0.75); best.holder = P; this.set(P, 'btoss', 0.78); this.g.audio.grab();
          this.say('BELLY TOSS!', '', 1); return true;
        }
        if (best.holdP) this.escapeFrom(best);
        this.dropCarry(best); best.st = 'held'; best.t = 0; best.holder = P; P.held = best; P.knees = 0; this.set(P, 'hold'); this.g.audio.grab();
        return true;
      }
      // or a prop
      let bp = null; bd = 1.1;
      for (const p of this.props) {
        if (p.dead || p.held || p.thrown || !p.D.pick) continue;
        const dx = p.x - P.x, dz = p.z - P.z, d = Math.hypot(dx, dz) - p.r;
        if (d < bd && (d < 0.35 || Math.abs(ang(Math.atan2(dz, dx) - P.f)) < 1.2)) { bd = d; bp = p; }
      }
      if (bp) { bp.held = P; P.held = bp; this.set(P, 'hold'); this.g.audio.grab(); return true; }
      return false;
    }
    // the slam: hoist them overhead and drive them straight down into the floor
    slam(P) { this.spend(P, 0.14); this.set(P, 'slam', 0.55); P.slamDone = false; this.g.audio.whoosh(0.35); }
    tossLand(P, B) {
      this.addScore(800); if (this.sk.mask.id === 'oni') { P.hp = Math.min(P.maxHp, P.hp + 15); this.popAt(P, '+15'); }
      P.tossDone = true; B.holder = null; B.y = 0; B.st = 'free';
      const fx = Math.cos(P.f), fz = Math.sin(P.f);
      this.damage(B, B.kind === 'boss' ? 40 : 30, P, fx * 2, fz * 2, true);
      if (!B.dead) { this.set(B, 'down', B.kind === 'boss' ? 1.3 : 1.5); B.fallX = fx; B.fallZ = fz; }
      this.shake = 0.8; this.hitstop = 0.12; this.g.audio.thump(12); this.g.audio.taiko && this.g.audio.taiko();
      this.fx.dust(B.x, 0.05, B.z, 20, 1.1, 0.8, 0.6); this.hitFx(B.x, B.z, 1.5); this.brk.crater(B.x, B.z);
      for (const T of this.actors) if (T !== B && T.team === 1 && !T.dead && Math.hypot(T.x - B.x, T.z - B.z) < 2.6) { const a = Math.atan2(T.z - B.z, T.x - B.x); this.damage(T, 8, P, Math.cos(a) * 4, Math.sin(a) * 4, true); }
    }
    slamHit(P, H) {
      this.addScore(500); if (this.sk.mask.id === 'oni') { P.hp = Math.min(P.maxHp, P.hp + 15); this.popAt(P, '+15'); }
      P.held = null; H.holder = null;
      const fx = Math.cos(P.f), fz = Math.sin(P.f);
      H.x = P.x + fx * 0.95; H.z = P.z + fz * 0.95; H.y = 0; H.vx = fx * 0.8; H.vz = fz * 0.8; H.slammed = true; H.st = 'free';
      this.damage(H, H.kind === 'sumo' ? 34 : 30, P, fx * 0.8, fz * 0.8, true); if (!H.dead) this.set(H, 'down', 1.4);
      this.shake = 0.75; this.hitstop = 0.1; this.g.audio.thump(10); this.g.audio.taiko && this.g.audio.taiko();
      this.fx.dust(H.x, 0.05, H.z, 16, 0.9, 0.7, 0.5); this.hitFx(H.x, H.z, 1.2); this.brk.crater(H.x, H.z); // the floor gives
      this.fx.ring(H.x, H.z, 2.4, 0.4); // a small shockwave: anyone close is hurt and staggered
      for (const T of this.actors) if (T !== H && T.team === 1 && !T.dead && Math.hypot(T.x - H.x, T.z - H.z) < 2.4) { const a = Math.atan2(T.z - H.z, T.x - H.x); this.damage(T, 10, P, Math.cos(a) * 5, Math.sin(a) * 5, false); }
    }
    throwHeld(P) {
      const H = P.held; P.held = null; this.set(P, 'throw', 0.28); this.spend(P, 0.1);
      if (Math.hypot(this.ctrl.mx, this.ctrl.mz) < 0.3) this.aim(P, 12); // no direction held: throw at the nearest enemy ahead
      const dir = P.f, sp = H.D ? (H.D.wt === 'tuna' ? 9 : 14) : 10;
      if (H.D) { H.held = null; H.thrown = { by: P, t: 0 }; H.vx = Math.cos(dir) * sp; H.vz = Math.sin(dir) * sp; H.vy = 2.2; H.y = 1.2; H.x = P.x + Math.cos(dir) * 0.8; H.z = P.z + Math.sin(dir) * 0.8; }
      else { H.holder = null; H.st = 'thrown'; H.t = 0; H.thrownBy = P; H.vx = Math.cos(dir) * sp; H.vz = Math.sin(dir) * sp; H.vy = 3.4; H.y = 0.8; }
      this.g.audio.whoosh(0.3);
    }
    release(P, pushed) {
      const H = P.held; P.held = null; this.set(P, 'free');
      if (H && !H.D) { H.holder = null; this.set(H, 'free'); if (pushed) { H.vx = Math.cos(P.f) * 4; H.vz = Math.sin(P.f) * 4; } }
      else if (H) H.held = null;
    }
    chargeHits(P, sp) {
      const fx = Math.cos(P.f), fz = Math.sin(P.f);
      for (const T of this.actors) {
        if (T === P || T.dead || T.team === P.team || P.chargeHits.has(T)) continue;
        const d = Math.hypot(T.x - P.x, T.z - P.z);
        if (d > P.r + T.r + 0.25) continue;
        if ((T.x - P.x) * fx + (T.z - P.z) * fz < 0) continue;
        P.chargeHits.add(T);
        if (T.kind === 'boss' || (T.kind === 'sumo' && !(T.stun > 0))) {
          const dz = T.stun > 0 || T.st === 'dazed';
          this.damage(T, dz ? 30 : 6, P, fx * (dz ? 4 : 0), fz * (dz ? 4 : 0), dz);
          this.set(P, 'bonk', 0.4); P.vx = -fx * 4; P.vz = -fz * 4; this.shake = 0.35; this.g.audio.thump(8); return;
        }
        this.damage(T, 15 * (P.giant > 0 ? 1.6 : 1), P, fx * 8, fz * 8, true);
        this.g.audio.thump(6); this.shake = 0.25; this.hitstop = 0.05;
      }
      // break through light and medium things; heavy things stop you
      for (const p of this.props) {
        if (p.dead || p.held) continue;
        const d = Math.hypot(p.x - P.x, p.z - P.z);
        if (d > P.r + p.r + 0.15 || (p.x - P.x) * fx + (p.z - P.z) * fz < 0) continue;
        if (p.D.wt === 'heavy' || p.D.wt === 'tuna') {
          if (p.D.roll) { p.vx = fx * sp * 0.9; p.vz = fz * sp * 0.9; p.rolling = { by: P, t: 0 }; this.set(P, 'recover', 0.25); P.vx *= 0.3; P.vz *= 0.3; this.g.audio.thump(5); return; }
          this.set(P, 'bonk', 0.4); P.vx = -fx * 3; P.vz = -fz * 3; this.shake = 0.3; this.g.audio.thump(7); return;
        }
        this.smash(p, fx * sp * 0.6, fz * sp * 0.6, P);
      }
    }
    parried(attacker, defender) {
      // defender turned the attack aside: the attacker reels
      const big = attacker.kind === 'boss' ? 1.6 : attacker.kind === 'sumo' ? 1.3 : 1.0;
      if (attacker === this.P) { this.set(attacker, 'hurt', 0.75); this.say('COUNTERED', 'Mix up your attacks', 1.2); this.popAt(attacker, 'COUNTERED!'); defender.cd = 0; }
      else { this.set(attacker, 'dazed', big); attacker.stun = big; this.popAt(attacker, 'PARRY!'); this.slow = 0.35; }
      this.g.audio.hyoshigi(); this.g.audio.slap(7); this.hitFx((attacker.x + defender.x) / 2, (attacker.z + defender.z) / 2, 1.2, true);
    }
    // incoming damage, with the player's parry and block
    damage(T, dmg, A, kx, kz, heavy) {
      if (A === this.P && T.team === 1 && dmg > 0 && !T.dead) { this.chainHit(); this.addScore(dmg * 10); }
      if (A && this.tired(A)) { dmg *= 0.6; kx = (kx || 0) * 0.6; kz = (kz || 0) * 0.6; } // swinging on empty
      if (T.dead) return;
      { const km = this.sk.dmgMul(T, A, dmg); if (km === 0) return; dmg *= km; }
      if (T.sleep) T.sleep = false;
      if (T === this.P) {
        if (T.iframe > 0 || T.st === 'dodge' || T.iron > 0) { if (T.iron > 0) this.popAt(T, 'IRON BODY'); return; }
        if (T.st === 'parry' && T.t < (this.sk.mask.id === 'tengu' ? 0.12 : 0.38) && A && A !== T) { this.parried(A, T); return; }
        if (T.st === 'block') { dmg *= 0.35; kx *= 0.3; kz *= 0.3; heavy = false; this.g.audio.thump(2); }
        if (T.giant > 0) { heavy = false; kx *= 0.3; kz *= 0.3; }
      }
      const slick = this.onPuddle(T);
      // market workers go down in two real hits (the first staggers them); the sumo and the boss use health
      if (T.team === 1 && T.kind !== 'sumo' && T.kind !== 'boss' && dmg > 0) {
        T.hits = (T.hits || 0) + (dmg >= 5 ? 1 : dmg / 12);
        dmg = T.hits >= 2 ? T.hp + 1 : Math.min(dmg, T.hp * 0.5);
      }
      if (T === this.P && dmg > 0) { this.hits = (this.hits || 0) + 1; this.chainBreak(); }
      T.hp -= dmg; T.lastHit = this.t;
      if (T.carry && (heavy || T.hp <= 0)) this.dropCarry(T);
      if (A && A !== T) { T.hitX = T.x - A.x; T.hitZ = T.z - A.z; } else { T.hitX = kx; T.hitZ = kz; }
      if (A && T.st === 'held' && A !== T.holder) { /* hit while held */ }
      const resist = clamp(1.6 / (T.mass || 1), 0.12, 1.2) * (slick ? 1.5 : 1);
      if (T.kind === 'boss' && !(T.st === 'dazed')) { kx *= 0.05; kz *= 0.05; heavy = false; }
      T.vx += kx * resist; T.vz += kz * resist;
      this.hitFx(T.x, T.z, heavy ? 1 : 0.6);
      if (T.hp <= 0) { this.ko(T, kx, kz); return; }
      if (T.st === 'held') return;
      if (T === this.P && this.P.held) this.release(this.P);
      const canDown = T.kind !== 'boss' && !(T.kind === 'sumo' && !(T.stun > 0));
      if ((heavy || (slick && dmg >= 8)) && canDown && !(T.fat && !heavy)) { this.set(T, 'down', T === this.P ? 0.85 : 1.15); T.fallX = kx || T.hitX; T.fallZ = kz || T.hitZ; if (T.holdP) this.escapeFrom(T); }
      else if (T.kind !== 'boss' && T.kind !== 'sumo') { if (T.holdP) this.escapeFrom(T); if (T.st !== 'act' || heavy) this.set(T, 'hurt', T === this.P ? 0.32 : 0.38); }
      else if (T.kind === 'sumo' && T.st !== 'dazed' && A === this.P) { // too heavy to stagger with one hit, but a full 3-hit string rocks him
        T.hitRun = (T.hitRun || []).filter((h) => this.t - h < 2.5); T.hitRun.push(this.t);
        if (T.hitRun.length >= 3 && T.st !== 'act') { T.hitRun = []; this.set(T, 'dazed', 1.0); T.stun = 1.0; }
      }
      this.sk.afterHit(T, A);
    }
    ko(T, kx, kz) {
      if (T === this.P && this.sk.saveFromDeath()) return; // REWIND fires by itself
      if (T !== this.P && T.team === 1 && this.sk.mask.id === 'okame' && Math.random() < 0.45) this.addProp('onigiri', T.x, T.z);
      T.hp = 0;
      if (T === this.P) { T.dead = true; this.set(T, 'down', 99); this.lose(); return; }
      this.addScore(T.kind === 'boss' ? 10000 : T.kind === 'sumo' ? 3000 : 1000);
      T.dead = true; this.set(T, 'down', 99); T.fallX = kx || T.hitX || 0; T.fallZ = kz || T.hitZ || 1;
      if (T.holdP) this.escapeFrom(T);
      if (T.holder) { T.holder.held = null; this.set(T.holder, 'free'); T.holder = null; }
      this.g.audio.thump(7);
      if (T.kind === 'boss') { T.zone.bossDone = true; this.slow = 2; this.say('KACHI-KOSHI!', 'The ōzeki falls', 3); }
      else if (Math.random() < 0.18) this.addProp('onigiri', T.x, T.z);
    }
    escape(P, E) {
      E.holdP = null; P.holder = null; this.set(P, 'free'); P.esc = 0; this.set(E, 'hurt', 0.6);
      E.vx = Math.cos(E.f) * -3; E.vz = Math.sin(E.f) * -3; this.popAt(P, 'BREAK!'); this.g.audio.slap(4);
    }
    escapeFrom(E) { const P = E.holdP; E.holdP = null; if (P) { P.holder = null; this.set(P, 'free'); } }
    onIce(a) { for (const p of this.map.puddles) if (p.ice && Math.hypot((a.x - p.x) / p.sx, a.z - p.z) < p.r) return true; return false; }
    onPuddle(a) { for (const p of this.map.puddles) if (Math.hypot((a.x - p.x) / p.sx, a.z - p.z) < p.r) return true; return false; }

    // ============================================================== enemies
    enemyStep(E, dt) {
      E.t += dt; if (E.stun > 0) E.stun -= dt; if (E.cd > 0) E.cd -= dt * (this.buffed(E) ? 1.7 : 1);
      if (E.frozen > 0) { E.frozen -= dt; E.vx = E.vz = 0; return; }
      if (E.blind > 0) E.blind -= dt;
      if (E.dead) { E.vx *= 0.9; E.vz *= 0.9; return; }
      if (E.sleep) { E.tvx = 0; E.tvz = 0; return; }
      if (this.sk.drive(E, dt)) return;
      if (E.st === 'tossed') { E.tvx = 0; E.tvz = 0; if (E.t > 1.2) { E.y = 0; this.set(E, 'free'); } return; } // carried by a belly toss
      if (E.kind === 'boss') { this.bossStep(E, dt); return; }
      const P = this.P, dx = P.x - E.x, dz = P.z - E.z, d = Math.hypot(dx, dz), toP = Math.atan2(dz, dx);
      const K = KINDS[E.kind], sp = E.spd * (this.buffed(E) ? 1.18 : 1);
      E.tvx = 0; E.tvz = 0;
      const face = (a, k) => { E.f += ang(a - E.f) * Math.min(1, dt * (k || 8)); };
      const go = (tx, tz, s) => { const w = this.route(E, tx, tz); const ex = w[0] - E.x, ez = w[1] - E.z, l = Math.hypot(ex, ez); if (l > 0.15) { E.tvx = ex / l * s; E.tvz = ez / l * s; } };
      if (E.blind > 0 && ['free', 'approach'].includes(E.st)) { E.st = 'free'; face(E.f + 3, 1); return; }
      switch (E.st) {
        case 'free': case 'approach': {
          face(toP);
          const token = this.hasToken(E);
          const want = E.kind === 'thrower' && !E.carry ? 1.0 : { fighter: 1.0, rusher: 1.0, technical: 1.0, grappler: 0.9, thrower: 6, staff: 1.9, commander: 2.6, sumo: 1.4 }[E.kind];
          // items: throwers run to a bottle (or knife) on the market and pick it up; brawlers grab a knife lying close by
          if (!E.carry && E.view && E.view.body && E.view.body.attach) {
            const want = E.kind === 'thrower' ? ['bottle', 'can', 'knife'] : ['fighter', 'technical', 'rusher'].includes(E.kind) ? ['knife'] : null;
            if (want) {
              let best = null, bd = E.kind === 'thrower' ? 16 : 4.5;
              for (const p of this.props) { if (p.dead || p.held || p.thrown || p.hop || !want.includes(p.type) || (p.claim && p.claim !== E && !p.claim.dead && !p.claim.carry)) continue; const dd = Math.hypot(p.x - E.x, p.z - E.z); if (dd < bd) { bd = dd; best = p; } }
              if (best) { best.claim = E; if (bd < E.r + best.D.r + 0.45) this.pickUp(E, best); else { go(best.x, best.z, sp); face(Math.atan2(best.z - E.z, best.x - E.x), 10); break; } }
            }
          }
          if (E.kind === 'thrower' && E.carry) { // keep the distance, step away when you get close
            if (d < 4) go(E.x - dx, E.z - dz, sp); else if (d > 8) go(P.x, P.z, sp); else this.strafe(E, toP, sp * 0.5);
            if (E.cd <= 0 && d < 11 && token) this.begin(E, 'bottle', 0.55);
            break;
          }
          if (E.carry && E.carry.type === 'knife' && d > 5 && d < 10 && E.cd <= 0 && token && Math.random() < 0.3) { this.begin(E, 'bottle', 0.5); break; } // sometimes the knife gets thrown
          if (E.kind === 'commander' && E.cd <= 0 && (E.shout || 0) < this.t - 7) { E.shout = this.t; this.begin(E, 'shout', 0.6); break; }
          if (!token) { // wait their turn in a ring around you (readable fights)
            const slot = (E.slot === undefined ? (E.slot = Math.random() * TAU) : E.slot) + this.t * 0.15;
            const R = 3.4 + (E.kind === 'staff' ? 0.6 : 0);
            go(P.x + Math.cos(slot) * R, P.z + Math.sin(slot) * R, sp * 0.7);
            break;
          }
          if (d > want + 0.2) go(P.x, P.z, sp);
          if (E.cd <= 0 && d < want + 0.8) {
            const roll = Math.random();
            if (E.kind === 'rusher') { this.begin(E, 'jab', 0.3); E.flurry = 1; }
            else if (E.kind === 'grappler') this.begin(E, roll < 0.7 ? 'grab' : 'jab', roll < 0.7 ? 0.48 : 0.4);
            else if (E.kind === 'staff') this.begin(E, 'sweep', 0.7);
            else if (E.kind === 'sumo') this.begin(E, d > 3 ? 'charge' : 'slap', d > 3 ? 0.75 : 0.5);
            else if (E.kind === 'fighter') this.begin(E, roll < 0.2 ? 'grab' : 'jab', roll < 0.2 ? 0.45 : 0.36);
            else this.begin(E, 'jab', 0.34);
          } else if (E.kind === 'sumo' && E.cd <= 0 && d > 3 && d < 9) this.begin(E, 'charge', 0.75);
          break;
        }
        case 'wind': {
          face(E.atk === 'rush' || E.atk === 'charge' ? toP : toP, E.atk === 'sweep' ? 3 : 6);
          if (E.t >= E.dur) { this.set(E, 'act', { jab: 0.22, grab: 0.2, rush: 0.6, sweep: 0.3, bottle: 0.25, shout: 0.4, slap: 0.3, charge: 1.1 }[E.atk]); E.adir = E.f; }
          break;
        }
        case 'act': this.enemyAct(E, dt, d, toP); break;
        case 'recover': if (E.t >= E.dur) this.set(E, 'free'); break;
        case 'hurt': if (E.t >= E.dur) this.set(E, 'free'); break;
        case 'dazed': if (E.t >= E.dur) this.set(E, 'free'); break;
        case 'down': if (E.t >= Math.max(0.75, E.dur - 0.5)) this.set(E, 'getup', 1.5); break; // a real getup takes a moment (the take is played about 2x)
        case 'getup': if (E.t >= E.dur) this.set(E, 'free'); break;
        case 'hold': { // a grappler holding you: throw after a beat
          face(toP, 4);
          if (!E.holdP) { this.set(E, 'free'); break; }
          if (E.t > 1.35) { const Pp = E.holdP; this.escapeFrom(E); this.damage(Pp, 17, null, Math.cos(E.f) * 7, Math.sin(E.f) * 7, true); this.set(E, 'recover', 0.6); this.g.audio.thump(8); this.shake = 0.3; }
          break;
        }
        case 'held': { const H = E.holder; if (!H) { this.set(E, 'free'); break; } const L = H.st === 'slam' ? Math.min(1, H.t / 0.2) : 0, R0 = (H.r + E.r * 0.6) * (1 - 0.55 * L); E.x = H.x + Math.cos(H.f) * R0; E.z = H.z + Math.sin(H.f) * R0; E.y = 0.5 + L * 1.1; E.vx = E.vz = 0; E.f = H.f + Math.PI; break; }
        case 'thrown': break; // flies (physics)
      }
      void K;
    }
    // steering: if a table or stall is between us and the target, head for its nearest corner instead
    route(E, tx, tz) {
      const m = E.r + 0.25;
      let hit = null, best = 1e9;
      for (const w of this.map.walls) {
        const t = segBox(E.x, E.z, tx, tz, w.x0 - m, w.z0 - m, w.x1 + m, w.z1 + m);
        if (t !== null && t < best) { best = t; hit = w; }
      }
      if (!hit) return [tx, tz];
      const c = [[hit.x0 - m - 0.1, hit.z0 - m - 0.1], [hit.x1 + m + 0.1, hit.z0 - m - 0.1], [hit.x0 - m - 0.1, hit.z1 + m + 0.1], [hit.x1 + m + 0.1, hit.z1 + m + 0.1]];
      let pick = c[0], bd = 1e9;
      for (const q of c) {
        const blocked = segBox(E.x, E.z, q[0], q[1], hit.x0 - m + 0.05, hit.z0 - m + 0.05, hit.x1 + m - 0.05, hit.z1 + m - 0.05) !== null;
        const dd = Math.hypot(q[0] - E.x, q[1] - E.z) + Math.hypot(tx - q[0], tz - q[1]) + (blocked ? 50 : 0);
        if (dd < bd) { bd = dd; pick = q; }
      }
      return pick;
    }
    begin(E, atk, wind) { E.atk = atk; this.set(E, 'wind', wind * (this.buffed(E) ? 0.85 : 1)); E.cd = rnd(1.2, 2.2); }
    strafe(E, toP, s) { const a = toP + Math.PI / 2 * (E.slot > Math.PI ? 1 : -1); E.tvx = Math.cos(a) * s; E.tvz = Math.sin(a) * s; }
    buffed(E) { return E.team === 1 && this.actors.some((c) => c.kind === 'commander' && !c.dead && c !== E && (this.t - (c.shout || -99) < 5 || Math.hypot(c.x - E.x, c.z - E.z) < 7)); }
    hasToken(E) {
      // the closest few enemies may attack; the rest wait (2 at a time, 3 when a commander is alive)
      if (E.kind === 'sumo') return true;
      const P = this.P, live = this.actors.filter((a) => a.team === 1 && !a.dead && a.kind !== 'thrower' && a.kind !== 'boss' && ['free', 'approach', 'wind', 'act', 'recover'].includes(a.st));
      live.sort((a, b) => Math.hypot(a.x - P.x, a.z - P.z) - Math.hypot(b.x - P.x, b.z - P.z));
      const n = this.actors.some((c) => c.kind === 'commander' && !c.dead) ? 3 : 2;
      return E.kind === 'thrower' ? this.actors.filter((a) => a.kind === 'thrower' && !a.dead && a.st === 'wind').length < 1 : live.indexOf(E) < n;
    }
    enemyAct(E, dt, d, toP) {
      const P = this.P;
      switch (E.atk) {
        case 'jab': if (!E.hitDone && E.t > 0.05) { E.hitDone = true; const kn = E.carry && E.carry.type === 'knife'; this.meleeHit(E, kn ? 1.3 : 1.15, 0.9, (E.fat ? 11 : 8) * (kn ? 1.6 : 1), 2.5, false); } break; // a knife cuts deeper
        case 'slap': if (!E.hitDone && E.t > 0.06) { E.hitDone = true; this.meleeHit(E, 1.7, 0.9, 14, 6, true); } break;
        case 'grab':
          if (!E.hitDone && E.t > 0.05) {
            E.hitDone = true;
            if (d < E.r + P.r + 0.75 && Math.abs(ang(toP - E.f)) < 0.9 && !['down', 'dodge', 'grabbed', 'getup'].includes(P.st) && P.iframe <= 0 && !(P.giant > 0) && !(P.sk && (P.sk.kind === 'ball' || P.sk.kind === 'cyc')) && !(P.invuln > 0)) {
              if (P.st === 'parry' && P.t < 0.22) { this.parried(E, P); break; }
              if (P.held) this.release(P);
              this.set(P, 'grabbed'); P.holder = E; P.esc = 0; E.holdP = P; this.set(E, 'hold'); this.g.audio.grab();
              this.popAt(P, 'GRABBED! mash buttons'); return;
            }
          }
          break;
        case 'rush': case 'charge': {
          const big = E.atk === 'charge', s = big ? 8.5 : 9;
          E.tvx = Math.cos(E.adir) * s; E.tvz = Math.sin(E.adir) * s; E.vx = E.tvx; E.vz = E.tvz; E.f = E.adir;
          if (!E.hitDone && d < E.r + P.r + 0.2) { E.hitDone = true; this.damage(P, big ? 18 : 12, E, Math.cos(E.adir) * 8, Math.sin(E.adir) * 8, true); }
          if (big) for (const p of this.props) if (!p.dead && !p.held && Math.hypot(p.x - E.x, p.z - E.z) < E.r + p.r + 0.1) { if (p.D.wt === 'heavy') { this.set(E, 'dazed', 1.3); E.stun = 1.3; this.shake = 0.4; this.g.audio.thump(9); return; } this.smash(p, E.tvx * 0.6, E.tvz * 0.6, E); }
          if (E.bumped) { E.bumped = false; if (big) { this.set(E, 'dazed', 1.3); E.stun = 1.3; this.shake = 0.4; this.g.audio.thump(9); return; } }
          break;
        }
        case 'sweep':
          if (!E.hitDone && E.t > 0.1) { E.hitDone = true; this.meleeHit(E, 2.3, 1.9, 14, 6, true); this.g.audio.whoosh(0.4); }
          break;
        case 'bottle': // throw whatever is in the hand (a bottle or a knife picked up off the market)
          if (!E.hitDone) {
            E.hitDone = true; const it = E.carry; if (!it) break;
            const lead = 0.5, tx = P.x + P.vx * lead, tz = P.z + P.vz * lead; const a = Math.atan2(tz - E.z, tx - E.x), l = Math.hypot(tx - E.x, tz - E.z), T = l / 10;
            let hp = E.view.body && E.view.body.handPos('R', new THREE.Vector3()); if (!hp || Math.hypot(hp.x - E.x, hp.z - E.z) > 1.5) hp = new THREE.Vector3(E.x, 1.5, E.z); // (not drawn this frame: from the body)
            const kind = it.type === 'knife' ? 'knife' : 'bottle';
            this.dropCarry(E, true);
            this.shots.push({ kind, dmg: kind === 'knife' ? 16 : 10, x: hp.x, z: hp.z, y: hp.y, vx: Math.cos(a) * 10, vz: Math.sin(a) * 10, vy: (1.0 - hp.y) / Math.max(0.15, T) + 9 * Math.max(0.15, T), by: E, mesh: shotMesh(this.scene, kind), t: 0 });
            this.g.audio.whoosh(0.2);
          }
          break;
        case 'shout':
          if (!E.hitDone) { E.hitDone = true; this.popAt(E, 'GET HIM!'); this.g.audio.clap(); for (const a of this.actors) if (a.team === 1 && !a.dead && a !== E) a.cd = Math.min(a.cd, 0.2); }
          break;
      }
      if (E.st === 'act' && E.t >= E.dur && E.flurry > 0 && E.atk === 'jab' && !E.dead) { E.flurry--; this.begin(E, 'jab', 0.16); return; }
      if (E.st === 'act' && E.t >= E.dur) this.set(E, 'recover', E.atk === 'rush' ? 0.85 : E.atk === 'charge' ? 0.9 : E.atk === 'sweep' ? 0.6 : 0.35);
    }

    // ============================================================== the boss
    bossStep(B, dt) {
      const P = this.P, dx = P.x - B.x, dz = P.z - B.z, d = Math.hypot(dx, dz), toP = Math.atan2(dz, dx);
      const k = B.phase === 2 ? 0.82 : 1, face = (s) => { B.f += ang(toP - B.f) * Math.min(1, dt * s); };
      B.tvx = 0; B.tvz = 0;
      if (B.phase === 1 && B.hp < B.maxHp * 0.5) { B.phase = 2; this.set(B, 'roar', 1.4); this.say('HE\'S ANGRY', 'Faster now', 1.8); this.g.audio.roar(); this.shake = 0.5;
        for (const sx of [-1, 1]) { const e = this.addActor('fighter', sx * 9, B.z - 2, { zone: B.zone }); B.zone.ens.push(e); } }
      switch (B.st) {
        case 'intro': B.tvz = 2.2; B.f = Math.PI / 2; if (B.t > 2.6) this.set(B, 'free'); break;
        case 'roar': if (B.t >= B.dur) this.set(B, 'free'); break;
        case 'free': {
          face(3);
          if (d > 2.2) { B.tvx = dx / d * B.spd / k; B.tvz = dz / d * B.spd / k; }
          if (B.cd <= 0) {
            if (d > 4.5) this.bossBegin(B, 'charge', 0.85 * k);
            else if (d < 2.9 && Math.random() < 0.55) this.bossBegin(B, 'slap', 0.55 * k);
            else this.bossBegin(B, 'stomp', 1.45 * (B.phase === 2 ? 0.88 : 1)); // a long, readable wind-up: time to back out of range
          }
          B.cd -= dt;
          break;
        }
        case 'wind': {
          if (B.atk !== 'charge' || B.t < B.dur * 0.7) face(B.atk === 'charge' ? 5 : 3);
          if (B.t >= B.dur) { this.set(B, 'act', { charge: 1.7, stomp: 0.25, slap: 0.3 }[B.atk]); B.adir = B.f; if (B.atk === 'stomp') this.bossStomp(B); }
          break;
        }
        case 'act': {
          if (B.atk === 'charge') {
            B.tvx = Math.cos(B.adir) * 11.5; B.tvz = Math.sin(B.adir) * 11.5; B.vx = B.tvx; B.vz = B.tvz; B.f = B.adir;
            if (!B.hitDone && d < B.r + P.r + 0.2 && P.st !== 'dodge' && P.iframe <= 0) { B.hitDone = true; this.damage(P, 22, B, Math.cos(B.adir) * 10, Math.sin(B.adir) * 10, true); this.shake = 0.5; }
            for (const p of this.props) if (!p.dead && !p.held && Math.hypot(p.x - B.x, p.z - B.z) < B.r + p.r) this.smash(p, B.tvx * 0.7, B.tvz * 0.7, B, true);
            if (B.bumped || B.t >= B.dur) { const wall = B.bumped; B.bumped = false; if (wall) { this.set(B, 'dazed', 1.9); B.stun = 1.9; this.shake = 0.7; this.g.audio.thump(10); this.popAt(B, 'CRASH!'); this.fx.burst(B.x, B.z, 1.2); } else this.set(B, 'recover', 0.7); }
          } else if (B.atk === 'slap') {
            if (!B.hitDone && B.t > 0.06) { B.hitDone = true; this.meleeHit(B, 2.0, 0.85, 18, 7, true); }
            if (B.t >= B.dur) this.set(B, 'recover', 0.45);
          } else if (B.t >= B.dur) {
            if (B.phase === 2 && !B.double) { B.double = true; this.bossBegin(B, 'stomp', 1.0); } else { B.double = false; this.set(B, 'recover', 1.0); }
          }
          break;
        }
        case 'recover': if (B.t >= B.dur) this.set(B, 'free'); break;
        case 'dazed': if (B.t >= B.dur) this.set(B, 'free'); break;
        case 'down': if (B.t >= B.dur) this.set(B, 'getup', 0.6); break;
        case 'getup': if (B.t >= B.dur) this.set(B, 'free'); break;
        case 'hurt': this.set(B, 'free'); break;
      }
    }
    bossBegin(B, atk, wind) { B.atk = atk; this.set(B, 'wind', wind); B.cd = rnd(0.9, 1.6) * (B.phase === 2 ? 0.7 : 1); if (atk === 'stomp') this.g.audio.taiko(); }
    bossStomp(B) {
      const P = this.P, R = 3.7, d = Math.hypot(P.x - B.x, P.z - B.z);
      this.fx.ring(B.x, B.z, R, 0.5); this.fx.burst(B.x, B.z, 1.4); this.shake = 0.6; this.g.audio.thump(12); this.brk.crack(B.x, B.z, 3.4);
      for (let i = 0; i < 14; i++) { const a = i / 14 * TAU; this.fx.dust(B.x + Math.cos(a) * R * 0.7, 0.05, B.z + Math.sin(a) * R * 0.7, 2, 0.3, 0.6, 0.4, Math.cos(a) * 3, Math.sin(a) * 3); }
      if (d < R + P.r) this.damage(P, 16, B, (P.x - B.x) / (d || 1) * 7, (P.z - B.z) / (d || 1) * 7, true);
      for (const p of this.props) if (!p.dead && Math.hypot(p.x - B.x, p.z - B.z) < R && p.D.wt !== 'heavy') { p.vy = 3; p.y = 0.05; p.vx += (p.x - B.x) * 1.2; p.vz += (p.z - B.z) * 1.2; p.hop = true; }
    }

    // ============================================================== skills (from the drink machines)
    getSkill(vm) {
      this.usedSkill = true;
      if (vm) { vm.used = true; if (vm.glow) { vm.glow.material.color.set(0x5a6070); vm.glow.userData.dim = true; } if (vm.arrow) vm.arrow.visible = false; this.g.audio.thump(4); } // sold out: its light goes dim, the arrow goes
      const L = POOL.filter((a) => a !== this.ability), A = L[Math.floor(Math.random() * L.length)];
      this.ability = A; this.abCd = 0; this.cardOpen = true; this.nearSkill = false; this.prompt('');
      const c = this.el('.ch-card'); c.querySelector('b').textContent = A.name; c.querySelector('span').textContent = A.desc; c.classList.add('on');
      this.el('.ch-ab em').textContent = A.name; this.g.audio.clack(); this.g.audio.swell(0.5, 1.2);
    }
    // ============================================================== the mask picker (before the market opens)
    openMasks() { this.maskOpen = true; this.maskI = 0; this.maskHold = 0; this.drawMasks(); this.el('.ch-mask').classList.add('on'); }
    drawMasks() {
      const M = S.CampSkills.MASKS, touch = S.touch && S.touch.on;
      this.el('.ch-mask').innerHTML = '<h2 data-jp="面">CHOOSE A MASK</h2>' + M.map((m, i) => '<button data-mask="' + i + '" class="' + (i === this.maskI ? 'sel' : '') + '"><span class="jp">' + m.jp + '</span>' + m.name + '<small>' + m.desc + '</small></button>').join('') +
        '<p>' + (touch ? 'Tap a mask' : 'W / S to choose · Enter to wear it') + '</p>';
    }
    maskMove(d) { const n = S.CampSkills.MASKS.length; this.maskI = (this.maskI + d + n) % n; this.markMask(); this.g.audio.tick && this.g.audio.tick(); }
    markMask() { this.el('.ch-mask').querySelectorAll('[data-mask]').forEach((b) => b.classList.toggle('sel', +b.dataset.mask === this.maskI)); }
    maskInput() { // the phone stick (keys: onKey; a gamepad: game.pollPad; each one step per press)
      const pad = S.touch && S.touch.on ? S.touch.mz : 0;
      if (Math.abs(pad) > 0.5) { if (!(this.maskHold > 0)) { this.maskMove(pad > 0 ? 1 : -1); this.maskHold = 0.25; } else this.maskHold -= 1 / 60; } else this.maskHold = 0;
    }
    pickMask(i) {
      const M = S.CampSkills.MASKS[i]; if (!M || !this.maskOpen) return;
      this.maskOpen = false; this.el('.ch-mask').classList.remove('on'); this.sk.mask = M; this.g.audio.clack();
      const mesh = S.CampSkills.maskMesh(M.id); if (mesh && this.P.view.head) { const s = this.P.view.s || 1; mesh.scale.setScalar(s); this.P.view.head.add(mesh); }
      if (M.id !== 'none') this.say(M.name, M.desc, 2.4);
      if (M.id === 'okame') for (const b of this.map.breakables) if (b.kind === 'vend') { b.used = true; if (b.glow) b.glow.visible = false; if (b.arrow) b.arrow.visible = false; }
      if (M.id === 'okame') this.prompt('');
      if (M.id === 'fish') { const t = this.addProp('tuna', this.P.x, this.P.z); t.held = this.P; this.P.held = t; this.set(this.P, 'hold'); }
    }
    closeCard() { this.cardOpen = false; this.el('.ch-card').classList.remove('on'); this.prompt('Use it with SPACE. It recharges.'); setTimeout(() => this.prompt(''), 3500); }
    useAbility() {
      const A = this.ability, P = this.P, fx = Math.cos(P.f), fz = Math.sin(P.f);
      this.abCd = A.cd; this.popAt(P, A.name); this.g.audio.swell(0.4, 0.8);
      if (this.sk.use(A)) return;
      const near = (r, cone) => this.actors.filter((e) => e.team === 1 && !e.dead && Math.hypot(e.x - P.x, e.z - P.z) < r && (!cone || Math.abs(ang(Math.atan2(e.z - P.z, e.x - P.x) - P.f)) < cone));
      switch (A.id) {
        case 'molotov': { // lob it onto the nearest enemy ahead (or 4m in front)
          this.aim(P, 9); const T = near(9, 1.2).sort((a, b) => Math.hypot(a.x - P.x, a.z - P.z) - Math.hypot(b.x - P.x, b.z - P.z))[0];
          const tx = T ? T.x + T.vx * 0.4 : P.x + Math.cos(P.f) * 4, tz = T ? T.z + T.vz * 0.4 : P.z + Math.sin(P.f) * 4;
          const vy = 4, ft = (vy + Math.sqrt(vy * vy + 2 * 18 * 1.4)) / 18, dx = tx - P.x, dz = tz - P.z;
          this.shots.push({ kind: 'molotov', x: P.x, z: P.z, y: 1.4, vx: dx / ft, vz: dz / ft, vy, by: P, mesh: shotMesh(this.scene, 'molotov'), t: 0 }); break;
        }
        case 'hundred': this.set(P, 'strike', 1.1); P.combo = 0; P.hundred = 1.1; this.hundredT = 0; break;
        case 'giant': P.giant = 8; break;
        case 'gale': for (const e of near(9, 0.7)) this.damage(e, 8, P, fx * 14, fz * 14, true); this.fx.ring(P.x + fx * 2, P.z + fz * 2, 3, 0.4); this.g.audio.whoosh(0.8); break;
        case 'shock': for (const e of near(5)) this.damage(e, 14, P, (e.x - P.x) * 2, (e.z - P.z) * 2, true); this.fx.ring(P.x, P.z, 5, 0.5); this.fx.burst(P.x, P.z, 1.3); this.shake = 0.5; this.g.audio.thump(12); break;
        case 'absorb': P.iron = 6; break;
        case 'claw': {
          const T = near(12).sort((a, b) => b.hp - a.hp)[0]; if (!T) break;
          this.set(T, 'clawed', 9); T.vx = T.vz = 0; this.g.audio.whoosh(0.5);
          const R = this.R, sc0 = R.scene; R.scene = this.scene; const me = R.makeObj({ type: 'claw' }); R.scene = sc0; // the arcade claw from versus
          me.userData.tgt.visible = false; (this.claws || (this.claws = [])).push({ me, e: T, t: 0, top: T.w ? 2.3 * (T.size || 1) : 1.85 }); break;
        }
        case 'blind': for (const e of near(9, 0.9)) { e.blind = 3; this.set(e, 'dazed', e.kind === 'boss' ? 1.4 : 3); e.stun = e.kind === 'boss' ? 1.4 : 3; } this.flash = 1; this.g.audio.clack(); break;
        case 'freeze': for (const e of near(6).slice(0, 4)) { e.frozen = e.kind === 'boss' ? 1.6 : 3; } this.g.audio.tick(); break;
        case 'storm': for (const e of near(14).sort((a, b) => Math.hypot(a.x - P.x, a.z - P.z) - Math.hypot(b.x - P.x, b.z - P.z)).slice(0, 3)) { this.damage(e, e.kind === 'boss' ? 30 : 34, P, 0, 0, true); this.fx.spark(e.x, 1.2, e.z, 1.6); this.bolts = (this.bolts || []).concat([{ x: e.x, z: e.z, t: 0.25 }]); } this.g.audio.thump(10); break;
      }
    }
    fireStep(dt) {
      // THOUSAND HANDS: rapid slaps while it lasts
      const P = this.P;
      if (P.hundred > 0) { P.hundred -= dt; P.st = 'strike'; P.t = 0.02; this.hundredT += dt; if (this.hundredT > 0.09) { this.hundredT = 0; P.hand ^= 1; this.meleeHit(P, 1.5, 0.8, 4, 3.5, false); } if (P.hundred <= 0) this.set(P, 'free'); }
      for (const F of this.fires) {
        F.t += dt; if (Math.random() < 0.6) this.fx.dust(F.x + rnd(-1.5, 1.5), 0.1, F.z + rnd(-1.5, 1.5), 1, 0.2, 1.2, 0.5);
        for (const e of this.actors) if (e.team === 1 && !e.dead && Math.hypot(e.x - F.x, e.z - F.z) < 2) { e.hp -= 12 * dt; if (e.hp <= 0) this.ko(e, 0, 0); else if (Math.random() < dt * 2 && e.kind !== 'boss') this.set(e, 'hurt', 0.4); }
      }
      this.fires = this.fires.filter((F) => { if (F.t > 4.5) { this.scene.remove(F.mesh); return false; } return true; });
      // CLAW MACHINE: the claw drops on them (0-0.5s), grips (to 0.65), hauls them up (to 1.25), lets go; they crash down
      for (const C of this.claws || []) {
        C.t += dt; const e = C.e, U = C.me.userData, t = C.t, LIFT = 2.4;
        if (!C.dropped && (e.dead || e.st !== 'clawed')) C.dropped = true;
        let hy;
        if (t < 0.5) { const k = t / 0.5; hy = 9 + (C.top + 0.75 - 9) * (1 - (1 - k) * (1 - k)); }
        else if (t < 0.65) hy = C.top + 0.75;
        else if (t < 1.25 && !C.dropped) { const k = (t - 0.65) / 0.6, ez = k * k * (3 - 2 * k); e.y = LIFT * ez; hy = C.top + 0.75 + e.y; if (!C.up) { C.up = true; this.g.audio.whoosh(0.3); } }
        else { if (!C.dropped) { C.dropped = true; this.g.audio.clack(); } if (!C.rel) { C.rel = t; C.vy = 0; } hy = C.top + 0.75 + LIFT + Math.max(0, t - (C.rel || t)) * 9; }
        if (!C.dropped || C.rel) { C.x = e.x; C.z = e.z; }
        if (C.dropped && C.rel && !C.landed && e.st === 'clawed') { // free fall
          C.vy -= 30 * dt; e.y = Math.max(0, e.y + C.vy * dt);
          if (e.y <= 0) { C.landed = true; e.y = 0; this.set(e, 'free'); this.damage(e, e.kind === 'boss' ? 40 : 45, P, 0, 0, true); if (!e.dead) this.set(e, 'down', 1.3);
            this.shake = 0.55; this.hitstop = 0.08; this.g.audio.thump(11); this.fx.burst(e.x, e.z, 1); this.brk.crater(e.x, e.z); }
        }
        if (e.st === 'clawed') { e.vx = e.vz = 0; }
        C.me.position.set(C.x, 0, C.z);
        U.head.position.y = hy; U.head.rotation.y += dt * 0.6; U.cable.position.y = (14 + hy) / 2; U.cable.scale.y = Math.max(0.01, 14 - hy);
        const open = t < 0.5 || C.dropped ? 0.55 : -0.05;
        for (const pr of U.prongs) pr.rotation.z += ((pr.children[0].position.x > 0 ? -open : open) - pr.rotation.z) * Math.min(1, dt * 12);
        U.lamp.material.color.setHex(Math.sin(this.t * 14) > 0 ? 0xffd23a : 0xff4fa3);
        if (hy > 14) { this.scene.remove(C.me); C.gone = true; }
      }
      if (this.claws) this.claws = this.claws.filter((C) => !C.gone);
    }

    // ============================================================== physics
    physics(a, dt) {
      const slick = this.onPuddle(a);
      if (a.crackT > 0) a.crackT -= dt;
      // smashed ice on the floor: running workers can lose their feet (you slide too, but a sumo doesn't fall over)
      if (slick && a.team === 1 && a.kind !== 'boss' && a.kind !== 'sumo' && !a.dead && !a.sleep && ['free', 'approach', 'recover'].includes(a.st) && Math.hypot(a.vx, a.vz) > 2.2 && this.onIce(a) && Math.random() < dt * 2.5) {
        const s = Math.hypot(a.vx, a.vz); this.set(a, 'down', 1.3); a.slipFall = true; a.fallX = -a.vx / s; a.fallZ = -a.vz / s; this.popAt(a, 'SLIP!'); this.dropCarry(a);
      }
      const fr = a.st === 'thrown' ? 0 : slick ? 2.2 : 11;
      if (a.tvx !== undefined && !['hurt', 'down', 'thrown', 'held', 'dazed', 'getup', 'grabbed', 'clawed'].includes(a.st) && !a.dead) {
        const k = 1 - Math.exp(-dt * (slick ? 3 : 14));
        a.vx += (a.tvx - a.vx) * k; a.vz += (a.tvz - a.vz) * k;
      } else { const k = Math.exp(-dt * fr); a.vx *= k; a.vz *= k; }
      if (a.st === 'thrown') {
        a.vy -= 18 * dt; a.y += a.vy * dt;
        for (const T of this.actors) if (T !== a && T !== a.thrownBy && !T.dead && T.team === a.team && Math.hypot(T.x - a.x, T.z - a.z) < T.r + a.r && a.y < 1.4) { this.damage(T, 15, a.thrownBy, a.vx * 0.6, a.vz * 0.6, true); }
        if (a.y <= 0) { a.y = 0; this.brk.crack(a.x, a.z, 1.5); this.damage(a, 20, a.thrownBy, a.vx * 0.4, a.vz * 0.4, true); if (!a.dead) this.set(a, 'down', 1.1); this.shake = 0.3; this.g.audio.thump(8); this.fx.dust(a.x, 0.05, a.z, 8, 0.4, 0.5, 0.4); }
      } else if (a.st !== 'held' && a.st !== 'clawed' && a.st !== 'tossed' && !(a === this.P && a.sk && a.sk.kind === 'flop')) a.y = 0;
      if (a.st === 'held' || a.st === 'grabbed' || a.st === 'tossed' || a.st === 'swallowed') return;
      a.x += a.vx * dt; a.z += a.vz * dt;
      // walls (axis-aligned boxes) and the zone gates
      for (const w of this.map.walls) this.pushOut(a, w);
      if (a.team === 0 || a.st === 'thrown') {
      }
      // dust when moving fast, slide streaks on wet floor
      const sp = Math.hypot(a.vx, a.vz);
      if (slick && sp > 4 && Math.random() < 0.3) this.fx.dust(a.x, 0.04, a.z, 1, 0.15, 0.2, 0.25);
      // water underfoot: a splash every stride, a big one when a body lands in it
      a.strideD = (a.strideD || 0) + sp * dt;
      const wet = slick && !this.onIce(a) && a.y < 0.05;
      if (wet && a.strideD > 0.75 && sp > 0.8) { a.strideD = 0; this.fx.water(a.x + a.vx * 0.04, a.z + a.vz * 0.04, sp > 4 ? 1.6 : 1); }
      const lying = a.st === 'down' || a.dead;
      if (wet && lying && !a.wasLying) this.fx.water(a.x, a.z, 3);
      a.wasLying = lying;
    }
    pushOut(a, w) {
      const cx = clamp(a.x, w.x0, w.x1), cz = clamp(a.z, w.z0, w.z1), dx = a.x - cx, dz = a.z - cz, d = Math.hypot(dx, dz);
      if (d >= a.r) return false;
      const sp0 = Math.hypot(a.vx, a.vz);
      if (w.brk && !w.brk.broken && this.brk) { // a charge, a thrown body or a charging sumo goes straight through a stall
        const ram = (a === this.P && a.st === 'charge' && sp0 > 6) || (a === this.P && a.sk && (a.sk.kind === 'torp' || (a.sk.kind === 'ball' && sp0 > 6))) || (a.st === 'thrown' && sp0 > 3) || ((a.kind === 'boss' || a.kind === 'sumo') && a.st === 'act' && a.atk === 'charge');
        if (ram && this.brk.smash(w.brk, a.st === 'thrown' && a.thrownBy ? a.thrownBy : a, a.vx, a.vz)) return false;
      } else if (!w.brk && d > 1e-5 && sp0 > 5 && (a.st === 'thrown' || (a === this.P && a.st === 'charge')) && !(a.crackT > 0) && this.brk) { a.crackT = 0.5; this.brk.wallCrack(cx, cz, dx / d, dz / d, a.st === 'thrown' ? 1.0 + (a.y || 0) : 0.9); this.shake = Math.max(this.shake, 0.3); }
      if (d < 1e-5) { // centre inside the box: push out the shortest way
        const opts = [[w.x0 - a.r - a.x, 0], [w.x1 + a.r - a.x, 0], [0, w.z0 - a.r - a.z], [0, w.z1 + a.r - a.z]].sort((p, q) => Math.abs(p[0] + p[1]) - Math.abs(q[0] + q[1]));
        a.x += opts[0][0]; a.z += opts[0][1];
      } else { const k = (a.r - d) / d; a.x += dx * k; a.z += dz * k; const vn = (a.vx * dx + a.vz * dz) / d; if (vn < 0) { a.vx -= vn * dx / d; a.vz -= vn * dz / d; } }
      if (Math.hypot(a.vx, a.vz) > 6 || a.st === 'act') a.bumped = true;
      return true;
    }
    separate() {
      const L = this.actors.filter((a) => !a.dead && !['held', 'grabbed', 'thrown', 'clawed', 'tossed', 'swallowed'].includes(a.st) && !(a.sk && a.sk.kind === 'flop'));
      for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) {
        const A = L[i], B = L[j], dx = B.x - A.x, dz = B.z - A.z, d = Math.hypot(dx, dz), m = A.r + B.r;
        if (d >= m || d < 1e-5) continue;
        const pen = m - d, ia = 1 / A.mass, ib = 1 / B.mass, s = pen / (ia + ib) / d;
        A.x -= dx * s * ia; A.z -= dz * s * ia; B.x += dx * s * ib; B.z += dz * s * ib;
      }
      // actors push light props and roll carts; props sit against walls
      for (const a of L) for (const p of this.props) {
        if (p.dead || p.held || p.thrown) continue;
        const dx = p.x - a.x, dz = p.z - a.z, d = Math.hypot(dx, dz), m = a.r + p.r;
        if (d >= m || d < 1e-5) continue;
        const heavy = p.D.wt === 'heavy' || p.D.wt === 'tuna' || !p.D.pick && p.D.wt === 'medium';
        const pen = m - d;
        if (heavy) { a.x -= dx / d * pen; a.z -= dz / d * pen; } else { p.x += dx / d * pen; p.z += dz / d * pen; }
      }
    }
    propStep(dt) {
      for (const p of this.props) {
        if (p.dead) continue;
        if (p.held) {
          const H = p.held; if (p.attached) continue; // in an enemy's hand (parented to the bone)
          const sz = H.w ? H.w.szCur : 1, small = p.D.r < 0.2;
          if (small && H.view && H.view.arms && H.view.arms[1] && H.view.arms[1].hand) { const v = H.view.arms[1].hand.getWorldPosition(new THREE.Vector3()); p.x = v.x; p.y = v.y - 0.08; p.z = v.z; }
          else { p.x = H.x + Math.cos(H.f) * 0.78 * sz; p.z = H.z + Math.sin(H.f) * 0.78 * sz; p.y = 0.95 * sz; } // hugged against the chest
          p.ry = -H.f; continue;
        }
        if (p.thrown || p.hop) {
          p.vy -= 18 * dt; p.y += p.vy * dt; p.x += p.vx * dt; p.z += p.vz * dt; p.spin += dt * 12;
          if (p.thrown) {
            for (const T of this.actors) {
              if (T.dead || T.team === p.thrown.by.team || T.st === 'held') continue;
              if (Math.hypot(T.x - p.x, T.z - p.z) < T.r + p.r + 0.1 && p.y < 2) {
                const heavy = p.D.wt === 'tuna' || p.D.wt === 'medium';
                this.damage(T, p.D.dmg * (T.stun > 0 ? 1.4 : 1), p.thrown.by, p.vx * 0.5, p.vz * 0.5, heavy);
                if (T.kind === 'sumo' && heavy) { T.stun = 1.2; this.set(T, 'dazed', 1.2); }
                this.g.audio.thump(heavy ? 7 : 4); this.landProp(p, true); break;
              }
            }
          }
          let hitWall = false;
          for (const w of this.map.walls) if (this.pushOut(p, w)) hitWall = true;
          if (!p.dead && (p.y <= 0 || hitWall)) { if (p.thrown && (hitWall || p.y <= 0)) this.landProp(p, hitWall); else { p.y = 0; p.vy = 0; p.hop = false; } }
        } else {
          const k = Math.exp(-dt * (p.rolling ? 1.2 : 8)); p.vx *= k; p.vz *= k; p.x += p.vx * dt; p.z += p.vz * dt;
          for (const w of this.map.walls) if (this.pushOut(p, w) && p.rolling) { p.vx *= -0.3; p.vz *= -0.3; }
          if (p.rolling) { // a rolling cart flattens whoever it meets
            p.rolling.t += dt; const sp = Math.hypot(p.vx, p.vz);
            for (const T of this.actors) if (T.team === 1 && !T.dead && sp > 3 && Math.hypot(T.x - p.x, T.z - p.z) < T.r + p.r) { this.damage(T, 22, this.P, p.vx * 0.6, p.vz * 0.6, true); p.vx *= 0.6; p.vz *= 0.6; }
            if (sp < 0.5) p.rolling = null;
          }
        }
        // onigiri: walk over it to eat
        if (p.D.heal && Math.hypot(this.P.x - p.x, this.P.z - p.z) < this.P.r + p.r) { this.P.hp = Math.min(this.P.maxHp, this.P.hp + 25); this.popAt(this.P, '+25'); this.g.audio.blip(true); this.killProp(p); }
      }
      this.props = this.props.filter((p) => !p.dead || p.mesh.parent);
    }
    landProp(p, wall) {
      p.thrown = null; p.y = 0; p.vy = 0;
      if (p.D.breaks) this.smash(p, p.vx * 0.3, p.vz * 0.3);
      else { p.vx *= wall ? -0.3 : 0.3; p.vz *= wall ? -0.3 : 0.3; }
    }
    smash(p, vx, vz, by, strong) {
      if (p.dead) return;
      if (!p.D.breaks && !(strong && p.D.wt !== 'tuna')) { p.vx += vx * 0.4; p.vz += vz * 0.4; return; }
      this.fx.dust(p.x, 0.3, p.z, 8, 0.35, 0.8, 0.35, vx * 0.3, vz * 0.3); this.fx.spark(p.x, 0.5, p.z, 0.8);
      this.g.audio.slap(5); this.g.audio.scuff();
      if (p.D.splash) this.map.puddles.push({ x: p.x, z: p.z, r: 0.9, sx: 1.2 }), this.addPuddleMesh(p.x, p.z);
      if (p.D.into) { for (let i = 0; i < 2; i++) { const q = this.addProp(p.D.into, p.x + rnd(-0.4, 0.4), p.z + rnd(-0.4, 0.4)); q.vx = vx * 0.5 + rnd(-1, 1); q.vz = vz * 0.5 + rnd(-1, 1); } }
      else if (p.type === 'crate' && Math.random() < 0.2) this.addProp('onigiri', p.x, p.z);
      this.killProp(p);
    }
    pickUp(E, p) {
      p.held = E; p.claim = null; E.carry = p;
      if (p.mesh.userData.k) p.mesh.userData.k.rotation.set(0, 0, 0); // a knife comes off the counter into the grip
      p.attached = !!(E.view.body && E.view.body.attach(p.mesh, 'R'));
      this.g.audio.blip(false);
    }
    // let go of a carried item (thrown: it's gone into a shot; otherwise it drops to the floor)
    dropCarry(E, used) {
      const p = E.carry; if (!p) return; E.carry = null; p.held = null; p.claim = null;
      if (p.attached) { this.scene.attach(p.mesh); p.attached = false; }
      if (used) { this.killProp(p); return; }
      p.mesh.scale.setScalar(1); if (p.mesh.userData.k) p.mesh.userData.k.rotation.set(0, 0, Math.PI / 2);
      p.x = E.x + rnd(-0.3, 0.3); p.z = E.z + rnd(-0.3, 0.3); p.y = 0.6; p.vy = 2; p.vx = rnd(-1, 1); p.vz = rnd(-1, 1); p.hop = true;
    }
    killProp(p) { p.dead = true; if (p.mesh.parent) p.mesh.parent.remove(p.mesh); }
    addPuddleMesh(x, z) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.8).rotateX(-Math.PI / 2), this.map.decor.find((d) => d.kind === 'puddle').m.material);
      m.position.set(x, 0.013, z); m.renderOrder = 1; S.Water.animate(m); this.scene.add(m);
    }
    shotStep(dt) {
      for (const s of this.shots) {
        s.t += dt; s.vy -= 18 * dt; s.x += s.vx * dt; s.z += s.vz * dt; s.y += s.vy * dt;
        s.mesh.position.set(s.x, s.y, s.z); s.mesh.rotation.x += dt * 14;
        const P = this.P;
        if ((s.kind === 'bottle' || s.kind === 'knife') && !s.done && s.by !== P && Math.hypot(P.x - s.x, P.z - s.z) < P.r + 0.35 && s.y < 1.9) {
          if (P.st === 'parry' && P.t < 0.26) { // PARRY: swat it back at whoever threw it
            const T = s.by && !s.by.dead ? s.by : null, a = T ? Math.atan2(T.z - s.z, T.x - s.x) : P.f + Math.PI, l = T ? Math.hypot(T.x - s.x, T.z - s.z) : 6, ft = Math.max(0.2, l / 14);
            s.by = P; s.vx = Math.cos(a) * 14; s.vz = Math.sin(a) * 14; s.vy = (1.0 - s.y) / ft + 9 * ft; s.back = true;
            this.popAt(P, 'PARRY!'); this.g.audio.hyoshigi(); this.g.audio.slap(6); this.hitFx(s.x, s.z, 0.9, true);
          } else if (P.st === 'block') { s.done = true; this.g.audio.thump(2); }
          else if (P.st !== 'dodge' && P.iframe <= 0) { s.done = true; this.damage(P, s.dmg || 10, s.by, s.vx * 0.3, s.vz * 0.3, false); this.g.audio.slap(4); }
        }
        if (s.back && !s.done) for (const T of this.actors) if (T.team === 1 && !T.dead && Math.hypot(T.x - s.x, T.z - s.z) < T.r + 0.3 && s.y < 2) { s.done = true; this.damage(T, 18, P, s.vx * 0.4, s.vz * 0.4, true); this.g.audio.slap(6); break; }
        let wall = false; for (const w of this.map.walls) if (s.x > w.x0 && s.x < w.x1 && s.z > w.z0 && s.z < w.z1) wall = true;
        if (s.y <= 0 || wall || s.done) {
          s.done = true; this.scene.remove(s.mesh); this.fx.spark(s.x, 0.2, s.z, 0.6);
          if (s.kind === 'molotov') { const m = new THREE.Mesh(new THREE.CircleGeometry(2, 28).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff7a1a, transparent: true, opacity: 0.45, depthWrite: false })); m.position.set(s.x, 0.02, s.z); this.scene.add(m); this.fires.push({ x: s.x, z: s.z, t: 0, mesh: m }); this.g.audio.thump(6); }
        }
      }
      this.shots = this.shots.filter((s) => !s.done);
    }
    hitFx(x, z, s, gold) { this.fx.spark(x, 1.0, z, s); if (gold) this.fx.ring(x, z, 1.4, 0.3); }
    popAt(a, txt) { const p = this.project(a.x, 2.4 * (a.size || 1), a.z); this.g.ui.callout(txt, p.x, p.y, /PARRY|CRASH|BELLY/.test(txt) ? 'big' : 'gold'); }
    project(x, y, z) { const v = new THREE.Vector3(x, y, z).project(this.cam); return { x: (v.x * 0.5 + 0.5) * innerWidth, y: (-v.y * 0.5 + 0.5) * innerHeight }; }

    // ============================================================== drawing
    draw(dt) {
      const R = this.R, T = this.t;
      for (const a of this.actors) {
        const cz = this.camT ? this.camT.z : this.P.z, far = a !== this.P && (a.z - cz > 11 || cz - a.z > 23 || a.st === 'swallowed'); // off the screen (behind the camera or far up the street): don't draw or animate it
        if (far) { a.view.root.visible = false; if (a.view.body && a.view.body.wrap) a.view.body.wrap.visible = false; if (a.view.shadow) a.view.shadow.visible = false; continue; }
        this.drawActor(a, dt, T);
      }
      for (const p of this.props) if (!p.dead) {
        if (p.attached) continue;
        p.mesh.position.set(p.x, p.y, p.z);
        p.mesh.rotation.set(p.thrown || p.hop ? p.spin : 0, p.held || p.thrown ? -p.ry : p.ry, 0);
      }
      for (const F of this.fires) F.mesh.material.opacity = 0.35 + Math.sin(T * 20 + F.x) * 0.1;
      this.map.update(T);
      this.fx.update(dt); this.fx.updateSalt(dt); this.fx.updateWater(dt); this.brk.update(dt); this.sk.draw(dt, T);
      this.telegraphs(T);
      // camera: high angle, follows you, frames the space ahead
      const P = this.P, Z = this.zones[this.zi], boss = Z && Z.boss && Z.state === 'fight';
      const hw = this.map.halfWidth(P.z), tx = clamp(P.x * 0.65, -Math.max(0, hw - 6), Math.max(0, hw - 6));
      const want = new THREE.Vector3(boss ? clamp((P.x + (this.B ? this.B.x : 0)) / 2, -4, 4) : tx, 0, boss ? (P.z + (this.B ? this.B.z : P.z)) / 2 : P.z - 2.6);
      this.camT.lerp(want, 1 - Math.exp(-dt * 4));
      // a lower, closer three-quarter view (about 40 degrees): you see the shopfronts and the people, not a board game
      const dist = boss ? 19 : 15, sh = this.shake > 0 ? this.shake : 0; this.shake = Math.max(0, (this.shake || 0) - dt * 1.6);
      this.cam.position.set(this.camT.x + (Math.random() - 0.5) * sh * 0.5, dist * 0.64 + (Math.random() - 0.5) * sh * 0.5, this.camT.z + dist * 0.77);
      this.cam.lookAt(this.camT.x, 0.6, this.camT.z);
      this.cam.updateMatrixWorld();
      S.R3.setLight(this.cam, R.anime);
      if (this.flat) { S.CampFlat.frame(this); R.r.render(this.scene, this.cam); } else if (R.anime && R.post) { const u = R.post.comp.uniforms; u.uCine.value = 1; R.post.render(this.scene, this.cam, T); u.uCine.value = 0; } else R.r.render(this.scene, this.cam);
      this.drawHud();
    }
    drawActor(a, dt, T) {
      if (a.gone) return;
      if (a.w) { // the wrestler model: translate our state into its poses
        const w = a.w, st = a.st;
        w.x = a.x; w.z = a.z; w.y = a.y; w.f = a.f; w.fx = Math.cos(a.f); w.fz = Math.sin(a.f); w.vx = a.vx; w.vz = a.vz; w.spd = Math.hypot(a.vx, a.vz);
        const map = { free: 'free', strike: 'palm', grab: 'grab', hold: 'grab', throw: 'heavy', lprep: 'brace', dodge: 'dash', charge: 'charge', parry: 'brace', block: 'brace',
          recover: 'recover', slam: 'heavy', btoss: a.t < 0.3 ? 'grab' : 'heavy', tossed: 'stun', bonk: 'stun', hurt: 'stun', down: 'fall', getup: 'recover', grabbed: 'stun', intro: 'free', roar: 'win', wind: a.atk === 'stomp' ? 'bigstomp' : a.atk === 'charge' ? 'wind' : 'wind',
          act: a.atk === 'stomp' ? 'bigstomp' : a.atk === 'charge' ? 'charge' : 'slap', dazed: 'stun', held: 'stun', thrown: 'fall', clawed: 'stun' };
        const nst = map[st] || 'free';
        if (w.st !== nst) { w.st = nst; w.t = 0; } else w.t = st === 'hold' || (st === 'btoss' && a.t < 0.3) ? 0.12 : st === 'btoss' ? a.t - 0.3 : a.t;
        if (st === 'wind' && a.atk === 'stomp') w.t = a.t * (0.45 / Math.max(0.01, a.dur)); // lift the leg over the wind-up
        if (st === 'act' && a.atk === 'stomp') w.t = 0.46 + a.t;
        w.dur = a.dur || 1; w.hand = a.hand || 0; w.down = st === 'down' && a.t > 0.25; w.fallX = a.fallX || 0; w.fallZ = a.fallZ || 1; w.ddx = Math.cos(a.f); w.ddz = Math.sin(a.f);
        w.fxs = { dizzy: a.stun > 0 || st === 'dazed' ? 1 : 0, frozen: a.frozen > 0 ? 1 : 0, invuln: a.iron > 0 ? 1 : 0 };
        if (a === this.P) {
          const hpr = a.dead ? 0 : a.hp / a.maxHp, st0 = a.stam === undefined ? 1 : a.stam;
          w.bruise = clamp((0.85 - hpr) / 0.65, 0, 1); w.hunch = st === 'free' ? clamp((0.45 - hpr) / 0.35, 0, 1) : 0;
          w.breath = clamp((0.7 - st0) / 0.55, 0, 1); w.sweat = Math.max(clamp((0.45 - st0) / 0.35, 0, 1), clamp((0.3 - hpr) / 0.3, 0, 0.6));
          w.relaxed = !this.actors.some((E) => E.team === 1 && !E.dead && !E.sleep && Math.hypot(E.x - a.x, E.z - a.z) < 4.5); // guard up only with someone close
          Object.assign(w.fxs, this.sk.fxs()); w.ballRoll = a.sk && a.sk.roll; w.torpedo = !!(a.sk && a.sk.kind === 'torp'); a.view.viewer = -1; }
        if (a.clone) { w.fxs.invuln = 0; }
        w.lifted = st === 'held' || st === 'clawed' || st === 'tossed';
        a.view.update(w, Math.max(dt, 1e-4), T);
        a.view.root.visible = !(a.iframe > 0 && st === 'getup' && Math.sin(T * 40) > 0) && !(w.fxs.ball > 0); // a daruma replaces the body
      } else { if (a.team === 1) a.engage = !a.dead && Math.hypot(this.P.x - a.x, this.P.z - a.z) < 5.5; a.view.update(a, dt, T); }
    }
    telegraphs(T) {
      // warnings: a "!" over anyone winding up; a gold ring under a dazed heavy
      if (!this.tg) { this.tg = []; this.tgi = 0; }
      for (const m of this.tg) m.visible = false; this.tgi = 0;
      const get = (shape) => {
        let m = this.tg[this.tgi];
        if (!m) { m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff2a2a, transparent: true, opacity: 0.35, depthWrite: false })); m.renderOrder = 2; this.scene.add(m); this.tg.push(m); }
        if (m.userData.shape !== shape) {
          m.geometry.dispose();
          m.geometry = shape === 'ring' ? new THREE.RingGeometry(0.82, 1, 40).rotateX(-Math.PI / 2) : shape === 'disc' ? new THREE.CircleGeometry(1, 40).rotateX(-Math.PI / 2)
            : shape === 'cone' ? new THREE.CircleGeometry(1, 24, -0.9, 1.8).rotateX(-Math.PI / 2) : shape === 'wide' ? new THREE.CircleGeometry(1, 30, -1.9, 3.8).rotateX(-Math.PI / 2) : new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2).translate(0.5, 0, 0);
          m.userData.shape = shape;
        }
        this.tgi++; m.visible = true; return m;
      };
      // (no floor shapes for attacks: the "!" over the head and the wind-up itself are the warning)
      // a heavy one (sumo, boss) is open: gold ring under him, call it out once
      for (const a of this.actors) {
        if (a.kind !== 'sumo' && a.kind !== 'boss') continue;
        const open = !a.dead && (a.st === 'dazed' || a.stun > 0);
        if (open && !a.wasOpen) this.popAt(a, a.kind === 'boss' ? 'DAZED! PUNISH HIM' : 'DAZED! GRAB HIM (K)');
        a.wasOpen = open;
        if (open) { const m = get('ring'); const R = a.r + 0.5; m.scale.set(R, 1, R); m.position.set(a.x, 0.035, a.z); m.material.opacity = 0.55 + 0.3 * Math.sin(T * 14); m.material.color.set(0xffd23a); }
      }
      // a red "!" over anyone winding up an attack (orange for a grab)
      if (!this.bangTex) this.bangTex = S.R3.canvasTex(64, 64, (c) => { c.fillStyle = '#fff8ec'; c.beginPath(); c.arc(32, 32, 30, 0, 7); c.fill(); c.fillStyle = '#e2322b'; c.beginPath(); c.arc(32, 32, 25, 0, 7); c.fill(); c.fillStyle = '#fff8ec'; c.font = '900 44px "Dela Gothic One", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('!', 32, 34); });
      for (const a of this.actors) {
        const on = a.st === 'wind' && !a.dead;
        if (on && !a.bang) { a.bang = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.bangTex, depthTest: false, transparent: true })); a.bang.renderOrder = 9; this.scene.add(a.bang); }
        if (a.bang) {
          a.bang.visible = on;
          if (on) { const h = (a.w ? 2.5 * (a.size || 1) : 2.3) + Math.sin(T * 14) * 0.06; a.bang.position.set(a.x, h, a.z); const now = a.dur - a.t < 0.32; // the last moment before it lands: the "!" turns gold and swells = PARRY NOW
            a.bang.scale.setScalar((a.kind === 'boss' ? 1.1 : 0.7) * (now ? 1.3 : 1)); a.bang.material.color.set(now ? 0xffd23a : a.atk === 'grab' ? 0xffb050 : 0xffffff);
            if (!this.parryTip && !this.over && !this.maskOpen) { this.parryTip = true; this.prompt(S.touch && S.touch.on ? '! = an attack is coming. When it turns gold, tap DEFEND (no direction) to PARRY' : '! = an attack is coming. When it turns gold, tap L (no direction) to PARRY'); setTimeout(() => this.prompt(''), 6000); } }
          if (a.gone) { this.scene.remove(a.bang); a.bang = null; }
        }
      }
    }
    drawHud() {
      const P = this.P;
      this.el('.ch-me .ch-bar i').style.width = Math.max(0, P.hp / P.maxHp * 100) + '%';
      const tm = this.el('.ch-time'); if (tm) tm.textContent = fmtT(this.runT || 0).replace(/\.\d$/, '');
      this.el('.ch-me .ch-score').textContent = String(this.score || 0).padStart(7, '0');
      { const yb = this.el('.ch-yen b'), y = Math.round(S.profile.yen || 0); if (yb.dataset.v !== String(y)) { yb.dataset.v = String(y); yb.textContent = y.toLocaleString('en-US'); } }
      { const sc = this.el('.ch-sc b'), mu = this.el('.ch-mul b'); sc.textContent = (this.score || 0).toLocaleString('en-US'); mu.textContent = 'x' + (this.mult || 1);
        const sb = this.scoreBump || 0, mb = this.mulBump || 0; sc.style.transform = 'scale(' + (1 + sb * 0.12) + ')'; mu.style.transform = 'scale(' + (1 + mb * 0.25) + ')';
        this.scoreBump = Math.max(0, sb - 0.08); this.mulBump = Math.max(0, mb - 0.05); this.el('.ch-mul').classList.toggle('hot', (this.mult || 1) > 1); }
      // LOW HEALTH: no bar. Under 30% the screen edges go red and pulse with a heartbeat you can hear
      { const hp = P.dead ? 0 : P.hp / P.maxHp, k = clamp((0.3 - hp) / 0.3, 0, 1), el = this.el('.ch-hurt');
        if (k > 0 && !P.dead && !this.over) {
          const bpm = 78 + 70 * k, per = 60 / bpm, now = performance.now() / 1000; this.beat = (this.beat || 0) + Math.min(0.1, now - (this.beatNow || now)); this.beatNow = now;
          const ph = (this.beat % per) / per; if (ph < (this.lastPh || 0)) { this.g.audio.thump(1.2 + k * 1.5); setTimeout(() => this.g.audio.thump(0.8 + k), 160); } this.lastPh = ph; // lub-dub
          const pulse = Math.exp(-ph * 10) + 0.6 * Math.exp(-Math.max(0, ph - 0.16) * 12) * (ph > 0.16 ? 1 : 0);
          el.style.opacity = (0.35 + 0.35 * k + 0.3 * k * Math.min(1, pulse)).toFixed(3);
        } else { el.style.opacity = '0'; this.beat = 0; } }
      this.el('.ch-me .ch-bar').classList.toggle('low', P.hp < 30);
      const sb = this.el('.ch-stam'); sb.firstChild.style.width = Math.round((P.stam === undefined ? 1 : P.stam) * 100) + '%'; sb.classList.toggle('tired', this.tired(P));
      const A = this.ability; this.el('.ch-ab').classList.toggle('ready', !!A && this.abCd <= 0);
      this.el('.ch-cd i').style.width = A ? (100 * (1 - Math.max(0, this.abCd) / A.cd)) + '%' : '0%';
      if (this.B) this.el('.ch-boss .ch-bar i').style.width = Math.max(0, this.B.hp / this.B.maxHp * 100) + '%';
      // no floating health bars over enemies (workers go down in two hits; the boss has his bar up top)
      let i = 0;
      for (; i < this.barEls.length; i++) this.barEls[i].style.display = 'none';
      if (this.flash > 0) { this.flash -= 0.05; document.body.style.setProperty('--campFlash', this.flash); }
    }
  }

  // ---------------------------------------------------------------- props: simple readable shapes
  function propMesh(type) {
    if (S.CampArt) return S.CampArt.prop(type);
    const D = PROPS[type], g = new THREE.Group(), M = (c, s) => S.toon(c, { shade: s, rimAmt: 0.35 }), B = S.CampMap.box, C = S.CampMap.cyl;
    switch (type) {
      case 'crate': B(g, 0.66, 0.5, 0.66, D.col, D.shade, 0, 0.25, 0, 0.022); B(g, 0.7, 0.06, 0.7, 0x8a5a2a, 0x4a2a10, 0, 0.5, 0, 0.0); break;
      case 'crate2': B(g, 0.78, 0.5, 0.78, D.col, D.shade, 0, 0.25, 0, 0.022); B(g, 0.74, 0.5, 0.74, 0xb88050, D.shade, 0.04, 0.75, 0.02, 0.022); break;
      case 'foam': B(g, 0.62, 0.34, 0.5, D.col, D.shade, 0, 0.17, 0, 0.02); B(g, 0.5, 0.04, 0.4, 0x3fb0e0, 0x1a5a8a, 0, 0.35, 0, 0.0); break;
      case 'bottle': C(g, 0.06, 0.08, 0.26, D.col, D.shade, 0, 0.13, 0, 8, 0.012); C(g, 0.025, 0.04, 0.1, D.col, D.shade, 0, 0.3, 0, 6, 0.01); break;
      case 'can': { const k = [0xe2322b, 0x2f6fd0, 0x2e9e6a, 0xf2c14e][(Math.random() * 4) | 0]; C(g, 0.045, 0.045, 0.13, k, new THREE.Color(k).multiplyScalar(0.45).getHex(), 0, 0.065, 0, 10, 0.01); C(g, 0.04, 0.045, 0.012, 0xc8ccd0, 0x6a7078, 0, 0.136, 0, 10, 0); break; }
      case 'chair': B(g, 0.46, 0.06, 0.46, D.col, D.shade, 0, 0.45, 0, 0.015); B(g, 0.46, 0.45, 0.06, D.col, D.shade, 0, 0.7, -0.2, 0.015); for (const [x, z] of [[-0.18, -0.18], [0.18, -0.18], [-0.18, 0.18], [0.18, 0.18]]) B(g, 0.05, 0.45, 0.05, 0x3a3a40, 0x101014, x, 0.22, z, 0.0); break;
      case 'bin': C(g, 0.3, 0.26, 0.72, D.col, D.shade, 0, 0.36, 0, 14, 0.02); C(g, 0.32, 0.32, 0.06, 0x2a5aa0, 0x10203a, 0, 0.74, 0, 14, 0.01); break;
      case 'bucket': C(g, 0.22, 0.17, 0.32, D.col, D.shade, 0, 0.16, 0, 12, 0.015); C(g, 0.19, 0.19, 0.02, 0x7ac8f0, 0x3a7aa0, 0, 0.29, 0, 12, 0.0); break;
      case 'pallet': B(g, 1.1, 0.12, 0.9, D.col, D.shade, 0, 0.06, 0, 0.018); break;
      case 'cart': B(g, 1.1, 0.12, 0.7, D.col, D.shade, 0, 0.55, 0, 0.02); B(g, 0.05, 0.6, 0.7, 0x5a6672, 0x202830, -0.55, 0.85, 0, 0.012); for (const [x, z] of [[-0.45, -0.3], [0.45, -0.3], [-0.45, 0.3], [0.45, 0.3]]) C(g, 0.1, 0.1, 0.06, 0x1a1a1a, 0x050505, x, 0.1, z, 10, 0.0).rotation.x = Math.PI / 2; B(g, 0.9, 0.3, 0.55, 0xf6f6f0, 0xa8b0b8, 0.05, 0.76, 0, 0.012); break;
      case 'barrier': { B(g, 1.1, 0.12, 0.12, 0xf2c14e, 0x8a6a1a, 0, 0.75, 0, 0.015); B(g, 1.1, 0.12, 0.12, 0x1a1a1a, 0x050505, 0, 0.55, 0, 0.015); for (const x of [-0.5, 0.5]) B(g, 0.08, 0.85, 0.3, 0xf2c14e, 0x8a6a1a, x, 0.42, 0, 0.012); break; }
      case 'tuna': { const b = S.R3.mesh(S.R3.GEO.sphere, M(D.col, D.shade), 0.025); b.scale.set(0.32, 0.26, 0.9); b.position.y = 0.26; g.add(b);
        const belly = S.R3.mesh(S.R3.GEO.sphere, M(0xdfe6ee, 0x8a96a8), 0); belly.scale.set(0.26, 0.15, 0.78); belly.position.y = 0.16; g.add(belly);
        const tail = S.R3.mesh(new THREE.ConeGeometry(0.22, 0.4, 4), M(D.col, D.shade), 0.015); tail.rotation.x = Math.PI / 2; tail.position.set(0, 0.28, -0.95); g.add(tail);
        const tag = B(g, 0.12, 0.02, 0.16, 0xe2322b, 0x7a1418, 0.12, 0.52, 0.2, 0.0); void tag; break; }
      case 'onigiri': { const o = S.R3.mesh(new THREE.ConeGeometry(0.2, 0.26, 3), M(D.col, D.shade), 0.015); o.position.y = 0.16; g.add(o); B(g, 0.2, 0.12, 0.06, 0x1a2a1a, 0x050a05, 0, 0.1, 0.09, 0.0); break; }
    }
    return g;
  }
  function shotMesh(scene, kind) {
    const g = new THREE.Group();
    if (kind === 'knife') { const k = S.CampArt.prop('knife'); k.userData.k.rotation.set(0, 0, 0); k.userData.k.position.y = -0.1; scene.add(k); return k; }
    S.CampMap.cyl(g, 0.05, 0.07, 0.24, kind === 'molotov' ? 0xc84a1a : 0x3a9a5a, 0x2a1a10, 0, 0, 0, 8, 0.012);
    if (kind === 'molotov') { const f = new THREE.Sprite(new THREE.SpriteMaterial({ map: S.CampMap.glowTex(), color: 0xff8a2a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })); f.scale.setScalar(0.5); f.position.y = 0.2; g.add(f); }
    scene.add(g); return g;
  }

  // ---------------------------------------------------------------- market workers (non-sumo enemies)
  class WorkerView {
    constructor(scene, kind, fat, pick) {
      // rounded, chunky shapes with ink outlines, the same family as the sumo wrestlers (no boxes)
      const K = KINDS[kind], M = (c, s, o) => S.toon(c, Object.assign({ shade: s, rimAmt: 0.6 }, o || {}));
      const skin = M(0xe9b894, 0xa06a5a, { rim: 0xfff0d8 }), shirt = M(K.shirt, mul(K.shirt, 0.45)), apron = M(K.apron, mul(K.apron, 0.55)), pants = M(0x2a2a3a, 0x0c0c16),
        boot = M(0x22242c, 0x08080c, { spec: 0.35 }), band = M(K.band, mul(K.band, 0.5)), hair = M(0x2a1e2c, 0x0e0a14, { spec: 0.2, rim: 0x8fa6e8 }), ink = S.toon(0x1a1014, { shade: 0x0b0608, rimAmt: 0 }), white = M(0xfff8ec, 0xb8b0a0);
      const mesh = S.R3.mesh, SG = S.R3.GEO.sphere, fw = fat ? 1.45 : 1, th = 0.026;
      this.kind = kind; this.fat = fat; this.scene = scene;
      this.root = new THREE.Group(); scene.add(this.root);
      this.hips = new THREE.Group(); this.hips.position.y = 0.9; this.root.add(this.hips);
      const add = (p, geo, mat, x, y, z, sx, sy, sz, t) => { const m = mesh(geo, mat, t === undefined ? th : t); m.position.set(x, y, z); m.scale.set(sx, sy, sz); p.add(m); return m; };
      const cap = (r, l) => new THREE.CapsuleGeometry(r, l, 4, 12);
      // torso: chest + belly (a real round belly on the big ones), apron hugging the front
      this.torso = new THREE.Group(); this.hips.add(this.torso);
      add(this.torso, SG, shirt, 0, 0.56, 0, 0.34 * fw, 0.34, 0.25 * (fat ? 1.25 : 1));
      add(this.torso, SG, shirt, 0, 0.24, fat ? 0.06 : 0, 0.31 * fw, 0.3 * (fat ? 1.15 : 1), (fat ? 0.36 : 0.23));
      if (K.coat) add(this.torso, SG, M(0xc8231d, 0x6e1018), 0, 0.5, -0.01, 0.37 * fw, 0.38, 0.28 * (fat ? 1.25 : 1)); // happi coat
      if (!K.coat) add(this.torso, SG, apron, 0, 0.28, (fat ? 0.27 : 0.17), 0.27 * fw, 0.36, 0.08, 0.016);
      add(this.torso, new THREE.TorusGeometry(0.3 * fw, 0.022, 6, 24), apron, 0, 0.36, 0.0, 1, 1, fat ? 1.2 : 0.8, 0.01).rotation.x = Math.PI / 2;
      for (const sd of [-1, 1]) add(this.torso, SG, shirt, sd * 0.33 * fw, 0.74, 0, 0.13 * (fat ? 1.25 : 1), 0.12, 0.13);
      // head: big and readable, anime hair tufts, headband with a knot and tails
      this.head = new THREE.Group(); this.head.position.set(0, 1.02, 0.02); this.torso.add(this.head);
      add(this.head, SG, skin, 0, 0, 0, 0.23, 0.25, 0.23);
      add(this.head, SG, skin, 0, -0.1, 0.05, 0.16, 0.1, 0.15, 0.0);                     // jaw
      add(this.head, SG, hair, 0, 0.1, -0.035, 0.235, 0.19, 0.235, 0.02);
      for (let i = 0; i < 5; i++) { const t = add(this.head, new THREE.ConeGeometry(0.07, 0.2, 5), hair, -0.14 + i * 0.07, 0.24, -0.03 + Math.abs(i - 2) * -0.02, 1, 1, 1, 0.012); t.rotation.set(-0.5, 0, (i - 2) * 0.35); }
      add(this.head, new THREE.TorusGeometry(0.228, 0.035, 6, 22), band, 0, 0.1, 0, 1, 1, 1, 0.012).rotation.x = Math.PI / 2 - 0.12;
      add(this.head, SG, band, 0, 0.1, -0.24, 0.06, 0.05, 0.05, 0.01);
      for (const sd of [-1, 1]) { const tl = add(this.head, cap(0.025, 0.12), band, sd * 0.05, 0.02, -0.27, 1, 1, 1, 0.008); tl.rotation.set(0.6, 0, sd * 0.4); }
      for (const sd of [-1, 1]) {
        add(this.head, SG, white, sd * 0.085, 0.0, 0.2, 0.05, 0.055, 0.03, 0.0);           // eye white
        add(this.head, SG, ink, sd * 0.08, -0.005, 0.222, 0.032, 0.042, 0.02, 0.0);       // pupil
        const br = add(this.head, cap(0.016, 0.07), ink, sd * 0.09, 0.075, 0.205, 1, 1, 1, 0); br.rotation.z = Math.PI / 2 + sd * 0.35; // angry brows
        add(this.head, SG, skin, sd * 0.225, -0.01, 0, 0.04, 0.06, 0.035, 0.012);          // ears
      }
      add(this.head, cap(0.012, 0.06), ink, 0, -0.1, 0.205, 1, 1, 1, 0).rotation.z = Math.PI / 2;
      if (K.glasses) { for (const sd of [-1, 1]) add(this.head, new THREE.TorusGeometry(0.055, 0.012, 5, 14), ink, sd * 0.085, 0.0, 0.225, 1, 1, 1, 0); }
      if (K.cap) { add(this.head, SG, M(0x2a5a9a, 0x10284a), 0, 0.15, -0.01, 0.245, 0.15, 0.245, 0.016); add(this.head, SG, M(0x2a5a9a, 0x10284a), 0, 0.12, 0.2, 0.17, 0.03, 0.12, 0.01); }
      // arms: shirt sleeve, rolled up, bare forearm, round fist
      this.arms = [-1, 1].map((sd) => {
        const sh = new THREE.Group(); sh.position.set(sd * 0.36 * fw, 0.74, 0); this.torso.add(sh);
        add(sh, cap(0.095 * (fat ? 1.3 : 1), 0.24), shirt, 0, -0.17, 0, 1, 1, 1, 0.022);
        add(sh, new THREE.TorusGeometry(0.1 * (fat ? 1.3 : 1), 0.03, 6, 14), shirt, 0, -0.33, 0, 1, 1, 1, 0.01).rotation.x = Math.PI / 2;
        const el = new THREE.Group(); el.position.y = -0.36; sh.add(el);
        add(el, cap(0.082 * (fat ? 1.2 : 1), 0.22), skin, 0, -0.15, 0, 1, 1, 1, 0.022);
        add(el, SG, skin, 0, -0.33, 0.01, 0.105, 0.1, 0.105, 0.02);
        return { sh, el, sd };
      });
      if (K.pole) { const p = add(this.arms[1].el, new THREE.CylinderGeometry(0.035, 0.035, 2.4, 8), M(0xc8a070, 0x6a4a2a), 0, -1.05, 0.04, 1, 1, 1, 0.012); add(p, SG, M(0x3a3a40, 0x101014), 0.06, -1.15, 0, 0.16, 0.08, 0.06, 0.01); p.userData.acc = true; }
      if (kind === 'thrower') { const bt = this.bottle = add(this.arms[1].el, new THREE.CylinderGeometry(0.045, 0.055, 0.24, 10), M(0x3a9a5a, 0x1a4a2a, { spec: 0.5 }), 0, -0.56, 0.02, 1, 1, 1, 0.01); bt.userData.acc = true; add(bt, new THREE.CylinderGeometry(0.018, 0.026, 0.1, 8), M(0x3a9a5a, 0x1a4a2a), 0, 0.15, 0, 1, 1, 1, 0.008); } // held by the neck, clear of the fist
      // legs: work trousers and round rubber boots, a real knee so they can bend and fold
      this.legs = [-1, 1].map((sd) => {
        const hp = new THREE.Group(); hp.position.set(sd * 0.15 * fw, 0, 0); this.hips.add(hp);
        add(hp, cap(0.115 * (fat ? 1.3 : 1), 0.28), pants, 0, -0.24, 0, 1, 1, 1, 0.022);
        const kn = new THREE.Group(); kn.position.y = -0.45; hp.add(kn);
        add(kn, cap(0.105, 0.2), boot, 0, -0.17, 0, 1, 1, 1, 0.022);
        add(kn, SG, boot, 0, -0.38, 0.06, 0.12, 0.08, 0.19, 0.02);
        const ft = new THREE.Object3D(); ft.position.set(0, -0.4, 0.02); kn.add(ft);
        return { hp, kn, ft, sd };
      });
      // ragdoll: joint markers and the bones it turns
      const mk = (p, x, y, z) => { const o = new THREE.Object3D(); o.position.set(x, y, z); p.add(o); return o; };
      this.neck = mk(this.torso, 0, 0.8, 0);
      for (const A of this.arms) A.ha = mk(A.el, 0, -0.33, 0);
      const [L, R] = this.legs, [aL, aR] = this.arms;
      this.rd = new S.Ragdoll(
        { pelvis: this.hips, neck: this.neck, head: this.head, shL: aL.sh, elL: aL.el, haL: aL.ha, shR: aR.sh, elR: aR.el, haR: aR.ha,
          hipL: L.hp, knL: L.kn, ftL: L.ft, hipR: R.hp, knR: R.kn, ftR: R.ft },
        [{ obj: this.hips, frame: ['pelvis', 'neck', 'hipL', 'hipR'] }, { obj: this.torso, frame: ['pelvis', 'neck', 'shL', 'shR'] }, { obj: this.head, aim: ['neck', 'head'] },
          { obj: aL.sh, aim: ['shL', 'elL'] }, { obj: aL.el, aim: ['elL', 'haL'] }, { obj: aR.sh, aim: ['shR', 'elR'] }, { obj: aR.el, aim: ['elR', 'haR'] },
          { obj: L.hp, aim: ['hipL', 'knL'] }, { obj: L.kn, aim: ['knL', 'ftL'] }, { obj: R.hp, aim: ['hipR', 'knR'] }, { obj: R.kn, aim: ['knR', 'ftR'] }]);
      this.rdBones = this.rd.bones.map((b) => b.obj);
      // a real skinned body (when loaded): the shapes above become an invisible rig that drives it
      if (S.Chars && S.Chars.ready) {
        this.body = new S.Chars.Body(scene, kind, K, fat, pick === undefined ? Math.floor(Math.random() * 5) : pick);
        this.root.traverse((o) => { if (o.isMesh) o.visible = false; });
        if (kind === 'staff') { // a market hook-pole, 1.5 m, gripped a third of the way up in the striking hand
          const pole = new THREE.Group(), shaft = S.R3.mesh(new THREE.CylinderGeometry(0.028, 0.032, 1.5, 8), S.toon(0xc8a070, { shade: 0x6a4a2a }), 0.01); shaft.position.y = 0.45; pole.add(shaft);
          const hook = S.R3.mesh(new THREE.TorusGeometry(0.07, 0.014, 6, 12, Math.PI * 1.2), S.toon(0x4a4e56, { shade: 0x16181c, spec: 0.5 }), 0.008); hook.position.y = 1.22; hook.rotation.z = Math.PI / 2; pole.add(hook);
          this.body.attach(pole, 'R');
        }
        this.J = {}; for (const k in this.rd.joints) this.J[k] = new THREE.Vector3();
      }
      // ground shadow
      // a soft contact shadow (light enough that the comic halftone pass doesn't print its dot grid over it)
      WorkerView.shTex = WorkerView.shTex || S.R3.canvasTex(128, 128, (c) => { const gr = c.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, 'rgba(42,54,70,0.38)'); gr.addColorStop(0.55, 'rgba(42,54,70,0.2)'); gr.addColorStop(1, 'rgba(42,54,70,0)'); c.fillStyle = gr; c.fillRect(0, 0, 128, 128); });
      this.shadow = new THREE.Mesh(new THREE.PlaneGeometry(1.15 * fw, 0.95 * fw).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: WorkerView.shTex, transparent: true, opacity: 0.42, depthWrite: false }));
      this.shadow.renderOrder = 1; scene.add(this.shadow);
      this.walk = 0; this.mats = [skin, shirt, apron, pants];
      this.flashT = 0; this.lastHp = null;
    }
    // a full-body pose for this moment: keyframes with anticipation, a fast strike with overshoot, and follow-through
    // ANIMATION. Built the way action games animate fighters (Souls-likes in particular):
    //  - a bladed combat stance when engaged: lead (left) foot forward, guard up, never both arms mirrored
    //  - every strike is driven from the hips: hips turn first, then the shoulder, elbow, hand (the kinetic chain)
    //  - anticipation is slow and readable, the strike is fast, the end pose holds a beat, recovery is weighted
    //  - one hand works while the other guards or counterbalances; steps and lunges carry the weight forward
    //  - joints are springs with different stiffness (core stiff, arms looser, head slowest), so distal parts lag
    //    and overshoot: follow-through and overlapping action come out of the physics, not hand-tuned frames
    //  - hits push the body (velocity impulses), they don't snap it to a pose
    pose(a, T) {
      const st = a.st, sp = Math.hypot(a.vx, a.vz), mv = Math.min(1, sp / 2.4), k = a.dur ? clamp(a.t / a.dur, 0, 1) : 0;
      const ez = (x) => x * x * (3 - 2 * x), out = (x) => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
      const cyc = this.walk, sw = Math.sin(cyc), cw = Math.cos(cyc);
      this.eng = (this.eng || 0) + (((a.engage && st !== 'recover') || st === 'wind' || st === 'act' ? 1 : 0) - (this.eng || 0)) * 0.08;
      const e = this.eng, breathe = Math.sin(T * 2.1 + this.ph);
      // relaxed: arms hang with a soft elbow, weight settles from foot to foot
      const P = { y: 0.89 + breathe * 0.008, lean: 0.03, roll: Math.sin(T * 0.7 + this.ph) * 0.025, hy: 0, tw: 0, hx: 0.05, hz: 0,
        aR: [0.04, 0, -0.1], eR: -0.35, aL: [0.06, 0, 0.1], eL: -0.3, lL: 0.02, kL: 0.12, lR: -0.02, kR: 0.14 };
      // engaged: bladed stance, lead hand out at chin height, rear fist by the cheek, a little bounce
      if (e > 0.01) {
        const G = { y: 0.84 + Math.sin(T * 4.2 + this.ph) * 0.012, lean: 0.12, roll: Math.sin(T * 2.1 + this.ph) * 0.03, hy: -0.38, tw: 0.16, hx: 0.12, hz: 0,
          aL: [-0.95, 0.15, 0.32], eL: -1.45, aR: [-0.45, -0.1, -0.42], eR: -2.15, lL: -0.32, kL: 0.32, lR: 0.22, kR: 0.4 };
        if (a.kind === 'staff') { G.aR = [-0.75, 0, -0.25]; G.eR = -0.9; G.aL = [-0.9, 0, 0.45]; G.eL = -1.2; }
        if (a.kind === 'thrower') { G.aR = [-0.2, 0, -0.25]; G.eR = -1.0; }
        for (const key in G) P[key] = Array.isArray(G[key]) ? P[key].map((v, i) => v + (G[key][i] - v) * e) : P[key] + (G[key] - P[key]) * e;
      }
      // walking: pelvis dips over the planted foot and swings, the chest counter-rotates, arms swing opposite the legs
      if (mv > 0.01) {
        P.y -= Math.abs(cw) * 0.035 * mv; P.roll += sw * 0.06 * mv; P.hy += sw * 0.12 * mv; P.tw -= sw * 0.2 * mv; P.lean += 0.06 * mv;
        P.lL += sw * 0.7 * mv; P.lR -= sw * 0.7 * mv;
        P.kL += Math.max(0, Math.sin(cyc + 1.7)) * 0.95 * mv; P.kR += Math.max(0, Math.sin(cyc + 1.7 + Math.PI)) * 0.95 * mv;
        const arm = mv * (1 - e * 0.7);
        P.aR[0] -= sw * 0.42 * arm; P.aL[0] += sw * 0.42 * arm; P.eR -= (0.2 + Math.max(0, -sw) * 0.35) * arm; P.eL -= (0.2 + Math.max(0, sw) * 0.35) * arm;
      }
      const set = (o) => { for (const key in o) P[key] = o[key]; };
      // strikes: [load, hit]. Lead = left, power hand = right.
      const W = {
        jab: [ // rear-hand palm strike: coil the hips back, then drive through with a lunge; the lead hand pulls back to guard
          { hy: -0.75, tw: -0.45, lean: -0.05, y: 0.82, aR: [0.3, -0.2, -0.55], eR: -1.95, aL: [-1.25, 0.1, 0.12], eL: -0.55, lL: -0.24, kL: 0.25, lR: 0.2, kR: 0.55, hx: 0.15 },
          { hy: 0.42, tw: 0.5, lean: 0.34, y: 0.76, aR: [-1.58, 0.05, 0.16], eR: -0.12, aL: [-0.55, 0.2, 0.55], eL: -2.0, lL: -0.43, kL: 0.62, lR: 0.38, kR: 0.12, hx: 0.2 }],
        grab: [ // collar grab: drop the weight, reach with the lead hand first, the rear hand follows
          { hy: -0.3, tw: -0.15, lean: 0.25, y: 0.76, aL: [-0.75, 0.1, 0.38], eL: -0.85, aR: [-0.35, 0, -0.45], eR: -1.5, lL: -0.26, kL: 0.5, lR: 0.22, kR: 0.55, hx: 0.2 },
          { hy: 0.12, tw: 0.2, lean: 0.52, y: 0.71, aL: [-1.52, 0.05, -0.08], eL: -0.1, aR: [-1.2, 0, 0.18], eR: -0.55, lL: -0.51, kL: 0.75, lR: 0.38, kR: 0.08, hx: 0.25 }],
        sweep: [ // two-handed pole swing: wound far round, the hips lead and the pole trails, a wide braced stance
          { hy: 0.95, tw: 0.75, lean: 0.02, y: 0.8, aR: [-1.05, 0, -1.15], eR: -0.55, aL: [-1.15, 0, 0.42], eL: -1.2, lL: -0.28, kL: 0.5, lR: 0.3, kR: 0.5, hx: 0 },
          { hy: -0.95, tw: -0.85, lean: 0.28, y: 0.74, aR: [-1.35, 0, 0.35], eR: -0.15, aL: [-1.0, 0, 0.95], eL: -0.55, lL: -0.34, kL: 0.62, lR: 0.34, kR: 0.4, hx: 0.1 }],
        bottle: [ // overhand throw: step in with the lead foot, point with the lead hand, bottle cocked behind the head
          { hy: -0.75, tw: -0.55, lean: -0.22, y: 0.85, aR: [-2.45, 0.2, -0.6], eR: -1.7, aL: [-1.45, 0, 0.28], eL: -0.18, lL: -0.26, kL: 0.28, lR: 0.19, kR: 0.5, hx: -0.1 },
          { hy: 0.55, tw: 0.6, lean: 0.45, y: 0.78, aR: [-0.95, 0, 0.32], eR: -0.1, aL: [-0.35, 0, 0.62], eL: -1.85, lL: -0.4, kL: 0.6, lR: 0.38, kR: 0.12, hx: 0.25 }],
        shout: [ // the commander: fist up, other hand on the hip, chest out
          { hy: 0, tw: 0.1, lean: -0.15, y: 0.9, hx: -0.35, aR: [-2.75, 0, -0.25], eR: -0.45, aL: [0.25, 0, 0.62], eL: -1.7, lL: -0.14, kL: 0.15, lR: 0.14, kR: 0.18 },
          { hy: 0, tw: 0.15, lean: -0.25, y: 0.92, hx: -0.5, aR: [-2.95, 0, -0.15], eR: -0.2, aL: [0.25, 0, 0.62], eL: -1.7, lL: -0.14, kL: 0.15, lR: 0.14, kR: 0.18 }],
      };
      W.slap = W.jab; W.rush = W.grab; W.charge = W.grab;
      let stiff = 1;
      if (st === 'wind' || st === 'act') {
        const K = W[a.atk] || W.jab;
        if (st === 'wind') { // ease into the load over the first part of the wind-up, then creep further back (tension)
          const w = ez(Math.min(1, a.t / 0.28)), creep = 1 + 0.12 * k;
          for (const key in K[0]) { const v = K[0][key]; P[key] = Array.isArray(v) ? P[key].map((p0, i) => p0 + (v[i] * (i === 0 ? creep : 1) - p0) * w) : P[key] + (v * (key === 'hy' || key === 'tw' ? creep : 1) - P[key]) * w; }
          stiff = 0.8;
        } else { // the strike: a fast drive to the hit pose (springs supply the lag and whip), hold it, then let go
          set(JSON.parse(JSON.stringify(K[1])));
          if (a.atk === 'sweep') { const s2 = out(a.t / Math.max(0.05, a.dur * 0.7)); P.hy = 0.95 + (-0.95 - 0.95) * s2; P.tw = 0.75 + (-0.85 - 0.75) * s2; }
          stiff = 3.2;
        }
      } else if (st === 'recover') { // weight still forward from the strike, settling back into the stance
        const K = W[a.atk] || W.jab, h = K[1], w = 1 - ez(k);
        for (const key of ['lean', 'y', 'lL', 'kL', 'lR', 'kR', 'hy']) if (h[key] !== undefined) P[key] = P[key] + (h[key] - P[key]) * w * 0.7;
        stiff = 0.55;
      } else if (st === 'hold') { set({ aR: [-1.3, 0, 0.32], aL: [-1.25, 0, -0.3], eR: -0.45, eL: -0.6, lean: -0.12, y: 0.82, lL: -0.35, kL: 0.45, lR: 0.32, kR: 0.4, hy: 0, tw: 0 }); }
      else if (st === 'dazed' || a.blind > 0) {
        set({ lean: 0.12 + Math.sin(T * 4.6) * 0.1, roll: Math.sin(T * 3.1) * 0.13, hz: Math.sin(T * 3.7) * 0.32, hx: 0.25, y: 0.83, hy: Math.sin(T * 1.9) * 0.2,
          aR: [0.12, 0, -0.22], aL: [0.18, 0, 0.26], eR: -0.25, eL: -0.4, kL: 0.35 + Math.sin(T * 4.6) * 0.14, kR: 0.35 - Math.sin(T * 4.6) * 0.14 });
        stiff = 0.6;
      } else if (st === 'hurt') { set({ lean: -0.18, hx: -0.25, y: 0.84, aR: [-0.2, 0, -0.5], eR: -1.3, aL: [-0.3, 0, 0.55], eL: -1.4 }); stiff = 0.9; }
      if (a.frozen > 0) stiff = 99;
      return { P, stiff };
    }
    // spring stiffness per joint (rad/s^2 per rad): the core leads, limbs lag behind it, the head lags most
    static get K() { return { y: 300, lean: 210, roll: 200, hy: 230, tw: 170, hx: 85, hz: 85, aR: 150, aL: 150, eR: 100, eL: 100, lL: 340, lR: 340, kL: 340, kR: 340 }; }
    springTo(P, stiff, dt) {
      if (!this.cur) { this.cur = JSON.parse(JSON.stringify(P)); this.vel = {}; for (const key in P) this.vel[key] = Array.isArray(P[key]) ? P[key].map(() => 0) : 0; }
      const KK = WorkerView.K, n = Math.max(1, Math.ceil(dt * 240)), h = dt / n;
      for (const key in P) {
        if (this.cur[key] === undefined) { this.cur[key] = JSON.parse(JSON.stringify(P[key])); this.vel[key] = Array.isArray(P[key]) ? P[key].map(() => 0) : 0; }
        const kk = Math.min(4000, (KK[key] || 150) * stiff), c = 2 * Math.sqrt(kk) * 0.78; // slightly under-damped: a touch of overshoot
        for (let s = 0; s < n; s++) {
          if (Array.isArray(P[key])) for (let i = 0; i < P[key].length; i++) { this.vel[key][i] += (kk * (P[key][i] - this.cur[key][i]) - c * this.vel[key][i]) * h; this.cur[key][i] += this.vel[key][i] * h; }
          else { this.vel[key] += (kk * (P[key] - this.cur[key]) - c * this.vel[key]) * h; this.cur[key] += this.vel[key] * h; }
        }
      }
    }
    // a hit: knock the joints (velocity), away from the blow
    impulse(f, sd, big) {
      if (!this.vel) return; const v = this.vel, m = big ? 1.5 : 1;
      v.lean += -7 * f * m; v.hx += -11 * f * m; v.hz += 7 * sd * m; v.roll += 5 * sd * m; v.tw += 6 * sd * m; v.y -= 0.8 * m;
      v.aR[0] += 7 * m; v.aL[0] += 7 * m; v.aR[2] -= 5 * m; v.aL[2] += 5 * m; v.eR += 6 * m; v.eL += 6 * m;
    }
    setPose(P) {
      this.hips.position.set(0, P.y, 0); this.hips.rotation.set(P.lean, P.hy || 0, P.roll);
      this.torso.rotation.set(0, P.tw, 0); this.head.rotation.set(P.hx, -P.tw * 0.5, P.hz);
      const [L, R] = this.arms;
      R.sh.rotation.set(P.aR[0], P.aR[1], P.aR[2]); R.el.rotation.set(P.eR, 0, 0);
      L.sh.rotation.set(P.aL[0], P.aL[1], P.aL[2]); L.el.rotation.set(P.eL, 0, 0);
      this.legs[0].hp.rotation.set(P.lL - P.lean, 0, 0); this.legs[0].kn.rotation.set(P.kL, 0, 0);
      this.legs[1].hp.rotation.set(P.lR - P.lean, 0, 0); this.legs[1].kn.rotation.set(P.kR, 0, 0);
    }
    update(a, dt, T) {
      const sp = Math.hypot(a.vx, a.vz), st = a.st, rd = this.rd;
      if (this.ph === undefined) { this.ph = Math.random() * 6; this.cur = null; this.vel = null; this.hitK = 0; }
      this.root.position.set(a.x, a.y || 0, a.z); this.root.rotation.set(0, Math.PI / 2 - a.f, 0);
      this.walk += dt * sp * 3.4;
      // a new hit: remember which way it shoved us (in our own frame)
      if (this.lastHp !== null && a.hp < this.lastHp) {
        this.flashT = 1; this.hitK = 1;
        const hx = a.hitX || -Math.cos(a.f), hz = a.hitZ || -Math.sin(a.f), hl = Math.hypot(hx, hz) || 1;
        this.hitF = -((hx * Math.cos(a.f) + hz * Math.sin(a.f)) / hl) >= -0.2 ? 1 : -1; this.hitS = (-hx * Math.sin(a.f) + hz * Math.cos(a.f)) / hl > 0 ? -1 : 1;
        this.impulse(this.hitF, this.hitS, this.lastHp - a.hp > 12);
      }
      this.hitK = Math.max(0, this.hitK - dt * 3.2);
      // ----- ragdoll: thrown, knocked down, dead, or dangling in someone's grip
      const lifted = st === 'held' || st === 'clawed', rag = st === 'thrown' && !(S.Anim && S.Anim.ready && this.mo && this.mo.fall); // hits, knockouts and slams are authored falls (see mocap); physics only for a full throw
      if (rag && !rd.on) {
        this.root.updateMatrixWorld(true);
        // launch speeds are capped and the body stays tensed: a person falls, a doll flies
        const cap = (vx, vz, m) => { const l = Math.hypot(vx, vz), k = l > m ? m / l : 1; return [vx * k, vz * k]; };
        if (a.slammed) { a.slammed = false; rd.start(new THREE.Vector3(a.vx, -7, a.vz), { push: new THREE.Vector3(Math.cos(a.f + Math.PI), 0, Math.sin(a.f + Math.PI)), tone0: 0.32, toneEnd: 0.07, relax: 1.4 }); }
        else if (st === 'thrown') { const [vx, vz] = cap(a.vx, a.vz, 5.5); rd.start(new THREE.Vector3(vx, Math.min(a.vy || 2, 2.6), vz), { spin: 0.55, ax: vx / (Math.hypot(vx, vz) || 1), az: vz / (Math.hypot(vx, vz) || 1), tone0: 0.34, toneEnd: 0.07, relax: 1.2 }); }
        else { const fx = a.fallX || -Math.cos(a.f), fz = a.fallZ || -Math.sin(a.f), fl = Math.hypot(fx, fz) || 1, [vx, vz] = cap(a.vx * 0.7, a.vz * 0.7, 3.2); rd.start(new THREE.Vector3(vx, 0.5, vz), { push: new THREE.Vector3(fx / fl * 1.9, 0, fz / fl * 1.9), limp: a.dead, tone0: a.dead ? 0.2 : 0.3, toneEnd: a.dead ? 0.02 : 0.06, relax: 1.6 }); }
        this.snap = null;
      }
      this.wasLifted = lifted;
      if (rd.on && !rag) { // back to our feet: blend out of wherever the body ended up
        const pel = rd.P('pelvis').x; if (!lifted && this.walls) { a.x = pel.x; a.z = pel.z; this.root.position.set(a.x, a.y || 0, a.z); } // get up where the body lies
        this.snap = { q: this.rdBones.map((o) => o.quaternion.clone()), hp: this.hips.position.clone(), face: rd.facing(), side: Math.random() < 0.5 ? 1 : -1, t: 0, dur: st === 'getup' ? a.dur : 0.3, getup: st === 'getup' };
        rd.stop();
      }
      if (rd.on) {
        rd.step(dt, this.walls ? (p, r) => this.collide(p, r) : null, { x: a.x, z: a.z });
        rd.apply(this.hips, this.root);
        const pel = rd.P('pelvis').x; this.shadow.position.set(pel.x, 0.014, pel.z);
      } else {
        if (S.Anim && S.Anim.ready) this.mocap(a, dt, T);
        else { const { P, stiff } = this.pose(a, T); this.springTo(P, stiff, Math.min(dt, 1 / 20)); this.setPose(this.cur); }
        // blending out of the ragdoll: through a kneel (getting up) or straight back (released)
        if (this.snap) {
          const S0 = this.snap; S0.t += dt;
          const kk = clamp(S0.t / S0.dur, 0, 1), ez = (x) => x * x * (3 - 2 * x);
          const stand = this.rdBones.map((o) => o.quaternion.clone()), standHp = this.hips.position.clone();
          let from = S0.q, fromHp = S0.hp, to = stand, toHp = standHp, w2 = ez(kk);
          if (S0.getup) {
            const mid = 0.55;
            this.setPose(this.kneel(S0.face, S0.side));
            const kneel = this.rdBones.map((o) => o.quaternion.clone()), kneelHp = this.hips.position.clone();
            if (kk < mid) { to = kneel; toHp = kneelHp; w2 = ez(kk / mid); } else { from = kneel; fromHp = kneelHp; w2 = ez((kk - mid) / (1 - mid)); }
          }
          this.rdBones.forEach((o, i) => o.quaternion.slerpQuaternions(from[i], to[i], w2));
          this.hips.position.lerpVectors(fromHp, toHp, w2);
          if (kk >= 1) { this.snap = null; this.cur = null; this.vel = null; }
        }
        this.shadow.position.set(a.x, 0.014, a.z);
      }
      this.shadow.visible = !a.gone;
      // hit flash and ice tint
      this.lastHp = a.hp; this.flashT = Math.max(0, this.flashT - dt * 7);
      for (const m of this.mats) { const fr = a.frozen > 0; m.uniforms.uFlashCol.value.set(fr ? 0x9fe6ff : a.burn ? 0xff7a1a : 0xffffff); m.uniforms.uFlash.value = fr ? 0.55 : this.flashT * 0.7; }
      const fade = a.dead && a.t > 1.6;
      this.root.visible = !fade || Math.sin(a.t * 30) > 0;
      if (this.body) {
        this.root.updateMatrixWorld(true);
        for (const k in this.J) this.rd.joints[k].getWorldPosition(this.J[k]);
        this.body.drive(this.J, this.root, this.root.visible && !a.gone, !rd.on && !this.snap && st !== 'thrown' && !lifted && st !== 'down' && st !== 'getup' && !a.dead && !(this.mo && this.mo.fall));
        const fr = a.frozen > 0; this.body.flash(fr ? 0x9fe6ff : a.burn ? 0xff7a1a : 0xffffff, fr ? 0.55 : this.flashT * 0.7);
        if (this.body.setFace) this.body.setFace(a.dead || st === 'down' || st === 'thrown' ? 2 : this.hitK > 0.35 || st === 'held' || st === 'dazed' ? 1 : 0);
      }
    }
    // MOTION CAPTURE: real recorded movement (CMU mocap, see anim.js) drives the rig. Locomotion blends idle /
    // fighting stance / walk / run by the actor's actual speed, played at the rate that keeps the feet planted;
    // attacks play a recorded strike timed to the game's wind-up and hit; hits add a flinch on top.
    mocap(a, dt, T) {
      const A = S.Anim, st = a.st, sp = Math.hypot(a.vx, a.vz), rd = this.rd;
      if (!rd.calibrated) { this.root.updateMatrixWorld(true); rd.calibrate(); }
      const N = 15, mk = () => Array.from({ length: N }, () => new THREE.Vector3());
      const M = this.mo || (this.mo = { out: mk(), tmp: mk(), ph: Math.random(), idleT: Math.random() * 3, atkW: 0, atkT: 0, atk: null, mv: 0, run: 0 });
      const frozen = a.frozen > 0, tdt = frozen ? 0 : dt;
      const big = (S.Chars && S.Chars.BIG) || 1, eng = a.engage || st === 'wind' || st === 'act' || st === 'recover' || st === 'hold';
      // locomotion weights, smoothed so starts and stops ease
      M.mv += (clamp((sp - 0.25) / 0.6, 0, 1) - M.mv) * Math.min(1, dt * 8);
      M.run += (clamp((sp - 1.8) / 0.9, 0, 1) - M.run) * Math.min(1, dt * 6);
      M.eng = (M.eng || 0) + ((eng ? 1 : 0) - (M.eng || 0)) * Math.min(1, dt * 4);
      const walkN = a.fat ? 'heavy' : 'walk', cW = A.clip(walkN), cR = A.clip('run');
      const rW = clamp(sp / (cW.speed * big), 0.55, 1.7), rR = clamp(sp / (cR.speed * big), 0.7, 1.5);
      // which way are we actually going? Sidestepping or circling: turn the body toward the travel direction.
      // Backing away from the player: keep facing them and play the gait in reverse (a backpedal). Attacks face the target.
      const busy = st === 'wind' || st === 'act' || st === 'recover' || st === 'hold' || st === 'hurt' || st === 'dazed';
      let dYaw = 0, back = false;
      if (sp > 0.35 && !busy) { const d = Math.atan2(Math.sin(Math.atan2(a.vz, a.vx) - a.f), Math.cos(Math.atan2(a.vz, a.vx) - a.f)); if (Math.abs(d) > 2.2) back = true; else dYaw = d; }
      M.yaw = (M.yaw || 0) + (dYaw - (M.yaw || 0)) * Math.min(1, dt * 7);
      M.back = (M.back || 0) + ((back ? 1 : 0) - (M.back || 0)) * Math.min(1, dt * 8);
      // one shared gait phase, so walk and run stay in step while they blend
      M.ph += tdt * ((1 - M.run) * rW / cW.dur + M.run * rR / cR.dur) * (M.mv > 0.02 ? 1 : 0) * (M.back > 0.5 ? -0.8 : 1);
      M.idleT += tdt * (st === 'dazed' ? 0.6 : 1);
      const out = M.out, tmp = M.tmp, add = (w) => { if (w > 0.001) for (let i = 0; i < N; i++) out[i].addScaledVector(tmp[i], w); };
      for (const v of out) v.set(0, 0, 0);
      const wIdle = 1 - M.mv;
      if (wIdle > 0.001) {
        A.sample('idle', M.idleT, tmp); add(wIdle * (1 - M.eng));
        A.sample('stance', M.idleT, tmp); add(wIdle * M.eng);
      }
      if (M.mv > 0.001) {
        A.sample(walkN, M.ph * cW.dur, tmp); add(M.mv * (1 - M.run));
        A.sample('run', M.ph * cR.dur, tmp); add(M.mv * M.run);
      }
      // attack layer
      const ATK = { jab: 'jab', slap: 'jab', grab: 'grab', bottle: 'throw', sweep: 'sweep', shout: 'shout', rush: 'run', charge: 'run' };
      let aw = 0;
      if (st === 'wind' || st === 'act' || st === 'hold') {
        const name = ATK[a.atk] || 'jab', c = A.clip(name), hit = c.peak || c.dur * 0.5, lead = Math.min(0.22, hit * 0.4);
        M.atk = name;
        if (st === 'wind') M.atkT = (Math.min(1, a.t / Math.max(0.05, a.dur)) ** 1.4) * (hit - lead); // the wind-up stretches to fill the telegraph
        else if (st === 'act') M.atkT = hit - lead + a.t;                                              // the strike plays at real speed
        else M.atkT = hit + 0.1;
        aw = 1;
      } else if (st === 'recover' && M.atk) { M.atkT += tdt; aw = 1 - clamp(a.t / Math.max(0.1, a.dur), 0, 1); }
      else M.atk = aw > 0 ? M.atk : null;
      M.atkW += (aw - M.atkW) * Math.min(1, dt * (aw > M.atkW ? 14 : 6));
      if (M.atk && M.atkW > 0.001) { A.sample(M.atk, M.atkT, tmp); for (let i = 0; i < N; i++) out[i].lerp(tmp[i], M.atkW); }
      // holding someone: arms forward, braced
      // held up by the collar: hanging upright, legs kicking, hands clawing at the holder's wrists
      if (st === 'held' || st === 'clawed') {
        A.sample('stance', 0.3, out);
        const nk = out[1], hip = [out[9], out[12]];
        for (const [i, sg] of [[5, -1], [8, 1]]) out[i].set(nk.x + sg * 0.1, nk.y + 0.08, nk.z + 0.26);          // hands at the collar
        for (const [i, sg] of [[4, -1], [7, 1]]) out[i].set(nk.x + sg * 0.3, nk.y - 0.12, nk.z + 0.16);         // elbows out
        [[10, 11, 0], [13, 14, 1]].forEach(([kn, ft, side]) => {
          const s1 = Math.sin(T * 9 + side * 2.6), h = hip[side];
          out[kn].set(h.x, h.y - 0.42, h.z + 0.12 + s1 * 0.16); out[ft].set(h.x, h.y - 0.82, h.z - 0.05 + s1 * 0.3);
        });
        for (const v of out) v.y -= 0.18; // the root already sits off the ground; let the feet hang just clear of it
      }
      // KNOCKDOWN: motion-captured falls and getups (CMU: a rug-pull fall onto the back, a banana-peel slip on ice, a real
      // person getting up off the floor), turned so the body falls away from the blow. No rag doll.
      const falling = st === 'down' || a.dead, rot = (v, c, s) => { const x = v.x; v.x = x * c + v.z * s; v.z = -x * s + v.z * c; };
      const flat = (r) => Math.atan2(r[2].x - r[0].x, r[2].z - r[0].z); // which way the head lies from the pelvis
      if (falling && !M.fall && A.clip('fallBack')) {
        const name = a.slipFall ? 'fallSlip' : 'fallBack', c = A.clip(name); a.slipFall = false;
        const wd = new THREE.Vector3(a.fallX || -Math.cos(a.f), 0, a.fallZ || -Math.sin(a.f)); if (wd.lengthSq() < 1e-6) wd.set(-Math.cos(a.f), 0, -Math.sin(a.f));
        wd.normalize().applyQuaternion(this.root.quaternion.clone().invert());
        A.sample(name, c.dur, tmp); const th = Math.atan2(wd.x, wd.z) - flat(tmp); // the head lands on the far side from the hit
        const fromThrow = M.prevSt === 'thrown';
        M.fall = { t: 0, name, c: Math.cos(th), s: Math.sin(th), from: out.map((v) => v.clone()), sp: a.slammed ? 1.7 : 1, t0: fromThrow ? c.dur : a.slammed ? 0.3 : 0 };
        a.slammed = false;
      }
      if (M.fall && (falling || st === 'getup')) {
        const F = M.fall; F.t += tdt;
        if (falling) {
          A.sample(F.name, F.t0 + F.t * F.sp, tmp);
          const wb = Math.min(1, F.t / 0.14);
          for (let i = 0; i < N; i++) { rot(tmp[i], F.c, F.s); out[i].copy(F.from[i]).lerp(tmp[i], wb); }
          F.lay = out.map((v) => v.clone());
        } else { // up off the floor: the getup take, turned and shifted so it starts exactly where the body lies
          const G = A.clip('getupBack'), L0 = F.lay || out.map((v) => v.clone());
          if (!F.g) { A.sample('getupBack', 0, tmp); const th = flat(L0) - flat(tmp), c = Math.cos(th), s = Math.sin(th); const p0 = tmp[0].clone(); rot(p0, c, s); F.g = { c, s, ox: L0[0].x - p0.x, oz: L0[0].z - p0.z }; }
          const g = clamp(a.t / Math.max(0.1, a.dur), 0, 1), sh = 1 - g * g * (3 - 2 * g);
          A.sample('getupBack', g * G.dur, tmp);
          const wIn = Math.min(1, a.t / 0.18), wOut = clamp((g - 0.72) / 0.28, 0, 1);
          for (let i = 0; i < N; i++) {
            rot(tmp[i], F.g.c, F.g.s); tmp[i].x += F.g.ox * sh; tmp[i].z += F.g.oz * sh;
            const v = L0[i].clone().lerp(tmp[i], wIn); out[i].copy(v.lerp(out[i], wOut * wOut * (3 - 2 * wOut)));
          }
        }
      } else if (M.fall && !falling && st !== 'getup') M.fall = null;
      M.prevSt = st;
      // hit flinch and daze sway: tip the upper body about the pelvis
      const pel = out[0], upper = [1, 2, 3, 4, 5, 6, 7, 8];
      let tipX = 0, tipZ = 0, headX = 0;
      if (this.hitK > 0 && !M.fall) { tipX = -0.45 * this.hitK * this.hitF; tipZ = 0.3 * this.hitK * this.hitS; headX = -0.35 * this.hitK * this.hitF; }
      if (st === 'dazed' || a.blind > 0) { tipX += 0.12 + Math.sin(T * 4.3) * 0.1; tipZ += Math.sin(T * 3.1) * 0.12; }
      if (tipX || tipZ) {
        const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(tipX, 0, tipZ));
        for (const i of upper) out[i].sub(pel).applyQuaternion(q).add(pel);
        if (headX) { const qh = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), headX); out[2].sub(out[1]).applyQuaternion(qh).add(out[1]); }
      }
      // turn toward the travel direction (about the pelvis)
      if (Math.abs(M.yaw) > 0.01) { const qy = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -M.yaw), c0 = pel.clone(); for (let i = 0; i < N; i++) out[i].sub(c0).applyQuaternion(qy).add(c0); }
      // into the world and onto the rig
      this.root.updateMatrixWorld(true);
      const W = M.world || (M.world = mk());
      for (let i = 0; i < N; i++) W[i].copy(out[i]).applyMatrix4(this.root.matrixWorld);
      rd.setPoints(W); rd.apply(this.hips, this.root, true);
    }
    // halfway up: on one knee (from lying on the back: sat up; from the front: pushed up on the hands)
    kneel(face, side) {
      const up = face > 0, L = side > 0;
      return { y: 0.55, lean: up ? 0.15 : 0.55, roll: 0, tw: 0.15 * side, hx: up ? 0.2 : -0.3, hz: 0,
        aR: up ? [-0.9, 0, 0.1] : [-1.25, 0, -0.1], eR: up ? -0.8 : -0.15, aL: up ? [-0.5, 0, 0.3] : [-1.25, 0, 0.1], eL: up ? -1.2 : -0.15,
        lL: L ? -1.45 : 0.05, kL: L ? 1.5 : 1.55, lR: L ? 0.05 : -1.45, kR: L ? 1.55 : 1.5 };
    }
    collide(p, r) {
      for (const w of this.walls) {
        const cx = clamp(p.x, w.x0, w.x1), cz = clamp(p.z, w.z0, w.z1), dx = p.x - cx, dz = p.z - cz, d = Math.hypot(dx, dz);
        if (d < r && d > 1e-6) { p.x = cx + (dx / d) * r; p.z = cz + (dz / d) * r; }
      }
    }
    dispose(scene) { scene.remove(this.root); scene.remove(this.shadow); if (this.body) this.body.dispose(); }
  }
  // where a segment first enters a box (0..1), or null
  function segBox(x0, z0, x1, z1, bx0, bz0, bx1, bz1) {
    let t0 = 0, t1 = 1; const dx = x1 - x0, dz = z1 - z0;
    for (const [p, q] of [[-dx, x0 - bx0], [dx, bx1 - x0], [-dz, z0 - bz0], [dz, bz1 - z0]]) {
      if (Math.abs(p) < 1e-9) { if (q < 0) return null; continue; }
      const r = q / p; if (p < 0) { if (r > t1) return null; if (r > t0) t0 = r; } else { if (r < t0) return null; if (r < t1) t1 = r; }
    }
    return x0 >= bx0 && x0 <= bx1 && z0 >= bz0 && z0 <= bz1 ? null : t0; // already inside the margin: don't fight it
  }
  const mul = (c, k) => { const C = new THREE.Color(c); C.multiplyScalar(k); return C.getHex(); };
  const fmtT = (t) => Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0') + '.' + Math.floor((t * 10) % 10);

  S.Campaign = Campaign;
  S.CAMP = { PROPS, KINDS, POOL };
})();
