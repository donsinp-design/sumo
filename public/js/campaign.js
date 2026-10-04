'use strict';
// CAMPAIGN: a single-player brawler through the fish market (camp-map.js), ending in a sumo boss fight.
// Its own little engine, drawn with the same cel look as the main game (toon shading, ink outlines, the anime
// pass) and the same wrestler model for you, the sumo enemies and the boss.
//
// Controls (same buttons as the main game):
//   J  slap string (3 hits)            K  grab an enemy or a prop / throw what you hold
//   L  tap alone: PARRY (hold: block)  L + direction, tap: dodge · hold: CHARGE (breaks light and medium things)
//   SPACE  your gacha ability (recharges)     Esc  pause
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
    chair:   { r: 0.3,  h: 0.8,  hp: 1, pick: true,  wt: 'light',  dmg: 14, breaks: true,  col: 0xd84a3a, shade: 0x6a1a14 },
    bin:     { r: 0.34, h: 0.75, hp: 3, pick: true,  wt: 'medium', dmg: 20, breaks: false, col: 0x3a7ad0, shade: 0x1a3a6a },
    bucket:  { r: 0.24, h: 0.35, hp: 1, pick: true,  wt: 'light',  dmg: 7,  breaks: true,  col: 0xf2c14e, shade: 0x8a6a1a, splash: true },
    pallet:  { r: 0.55, h: 0.15, hp: 2, pick: false, wt: 'medium', dmg: 0,  breaks: true,  col: 0xc8a070, shade: 0x6a4a2a },
    cart:    { r: 0.6,  h: 0.9,  hp: 99, pick: false, wt: 'heavy', dmg: 0,  breaks: false, col: 0x8a96a2, shade: 0x3a4652, roll: true },
    barrier: { r: 0.55, h: 0.9,  hp: 99, pick: false, wt: 'heavy', dmg: 0,  breaks: false, col: 0xf2c14e, shade: 0x1a1a1a },
    tuna:    { r: 0.5,  h: 0.45, hp: 99, pick: true,  wt: 'tuna',  dmg: 30, breaks: false, col: 0x4a5a78, shade: 0x1a2236 },
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
    sumo:      { hp: 150, spd: 2.5, r: 0.85, mass: 6,   name: 'SUMO',      wrestler: 1, size: 1.25 },
    boss:      { hp: 650, spd: 2.4, r: 1.05, mass: 12,  name: 'ŌZEKI MAGURO-YAMA', wrestler: 1, size: 1.6 },
  };

  // ---------------------------------------------------------------- gacha: a curated, combat-useful pool only
  const POOL = [
    { id: 'molotov', name: 'MOLOTOV COCKTAIL', desc: 'Throw a fire bottle ahead: a burning patch that hurts anyone in it.', cd: 18 },
    { id: 'hundred', name: 'THOUSAND HANDS', desc: 'A blur of slaps in front of you: big damage, pushes everyone back.', cd: 16 },
    { id: 'giant', name: 'GIANT', desc: 'Grow huge for 8s: more damage, no knockdowns, grabs cannot hold you.', cd: 26 },
    { id: 'gale', name: 'GIANT FAN', desc: 'A gale in front of you blows enemies off their feet.', cd: 16 },
    { id: 'shock', name: 'SHOCKWAVE STOMP', desc: 'Stomp: everyone around you is knocked down.', cd: 18 },
    { id: 'absorb', name: 'IRON BODY', desc: '6s: hits do nothing to you.', cd: 24 },
    { id: 'claw', name: 'CLAW MACHINE', desc: 'A claw drops on the toughest nearby enemy, lifts them and slams them down.', cd: 22 },
    { id: 'blind', name: 'BLINDING FLASH', desc: 'Everyone in front of you is dazed for 3s: free hits.', cd: 18 },
    { id: 'freeze', name: 'FREEZE', desc: 'Freezes the nearest enemies solid for 3s.', cd: 20 },
    { id: 'storm', name: 'LIGHTNING', desc: 'Lightning strikes the three nearest enemies.', cd: 20 },
  ];

  class Campaign {
    constructor(game) { this.g = game; }

    // ============================================================== setup / teardown
    start() {
      const g = this.g;
      this.R = g.R; this.t = 0; this.acc = 0; this.paused = false; this.over = null; this.slow = 0; this.hitstop = 0;
      this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0x0d0a10);
      this.cam = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 220);
      this.fx = new S.FX(this.scene); this.fx.noMarks = true; // no footprints piling up over a whole level
      this.map = S.CampMap.build(this.scene);
      this.ctrl = new S.Controller(new S.KeySource(S.MAPS.solo, 0));
      this.actors = []; this.props = []; this.shots = []; this.zones = this.map.zones.map((z) => Object.assign({ state: 'wait', ens: [] }, z));
      this.zi = 0; this.gate = this.zones[0].z1; this.ability = null; this.abCd = 0; this.fires = [];
      for (const p of this.map.props) this.addProp(p.type, p.x, p.z, p.ry);
      const arch = S.ARCH[g.sel && g.sel.c1 !== undefined ? g.sel.c1 : 0];
      this.P = this.addActor('player', this.map.start.x, this.map.start.z, { arch, lo: S.profile.loadout() });
      this.P.f = -Math.PI / 2;
      this.camT = new THREE.Vector3(this.P.x, 0, this.P.z - 2.5);
      this.buildHud();
      this.resize = () => { this.cam.aspect = innerWidth / innerHeight; this.cam.updateProjectionMatrix(); this.fx.pmat.uniforms.uScale.value = innerHeight * this.R.r.getPixelRatio() / (2 * Math.tan(this.cam.fov * Math.PI / 360)); };
      addEventListener('resize', this.resize); this.resize();
      this.say('UOGASHI MARKET', 'Fight your way to the tuna auction', 3.5);
      this.prompt('Grab a free gacha from the red machine (walk up, press K)');
      g.audio.swell(0.4, 1.5);
    }
    stop() {
      removeEventListener('resize', this.resize);
      if (this.hud) this.hud.remove();
      this.scene = null;
    }

    // ============================================================== actors
    addActor(kind, x, z, o) {
      o = o || {};
      const K = kind === 'player' ? { hp: 100, spd: 4.3, r: 0.55, mass: 2.2 } : KINDS[kind];
      const a = { kind, x, z, y: 0, vx: 0, vz: 0, vy: 0, f: Math.PI / 2, r: K.r, mass: K.mass * (o.fat ? 1.6 : 1), hp: K.hp * (o.fat ? 1.35 : 1),
        spd: K.spd * (o.fat ? 0.82 : 1), fat: !!o.fat, st: 'free', t: 0, dur: 0, team: kind === 'player' ? 0 : 1, cd: rnd(0.6, 1.6), iframe: 0,
        hitLog: [], stun: 0, slow: 0, buff: 0, zone: o.zone, dead: false, held: null, holder: null, combo: 0, lastStrike: -9, frozen: 0, blind: 0, burn: 0 };
      a.maxHp = a.hp;
      if (kind === 'boss') { a.phase = 1; a.st = 'intro'; a.t = 0; }
      if (K.wrestler || kind === 'player') {
        const arch = o.arch || S.ARCH[1];
        a.view = new S.WrestlerView(this.scene, arch, this.fx, o.lo || (kind === 'player' ? S.DEF_EQ : S.profile.randomLoadout()));
        a.view.viewer = 0; a.view.match = null;
        a.w = { x, z, y: 0, f: a.f, fx: 0, fz: 1, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, fxs: {}, a: arch, idx: kind === 'player' ? 0 : 1, szCur: K.size || 1,
          squash: 0, bal: 1, tx: 0, tz: 0, power: 0, pre: null, preT: 0, hand: 0, windPow: 0, charges: 0, uprightT: 0, throatT: 0, lifted: false, down: false,
          fallX: 0, fallZ: 1, clinch: null, slideT: 0, spd: 0, crouchT: 0, lean: 0, gulpI: -1, contact: false, fwdIn: 0, ddx: 0, ddz: 0, boomT: 0 };
        a.size = K.size || 1;
      } else a.view = new WorkerView(this.scene, kind, a.fat);
      this.actors.push(a);
      return a;
    }
    addProp(type, x, z, ry) {
      const D = PROPS[type];
      const p = { type, D, x, z, y: 0, vx: 0, vz: 0, vy: 0, r: D.r, hp: D.hp, held: null, thrown: null, ry: ry || 0, spin: 0, dead: false };
      p.mesh = propMesh(type); p.mesh.position.set(x, 0, z); p.mesh.rotation.y = p.ry; this.scene.add(p.mesh);
      this.props.push(p);
      return p;
    }

    // ============================================================== HUD
    buildHud() {
      const h = this.hud = document.createElement('div'); h.id = 'campHud';
      h.innerHTML = '<div class="ch-me"><b>YOU</b><span class="ch-bar"><i></i></span><div class="ch-ab"><em>NO ABILITY</em><span class="ch-cd"><i></i></span><kbd>SPACE</kbd></div></div>' +
        '<div class="ch-zone"></div><div class="ch-go">GO ↑</div><div class="ch-say"><b></b><span></span></div><div class="ch-prompt"></div>' +
        '<div class="ch-boss"><b></b><span class="ch-bar"><i></i></span></div><div class="ch-bars"></div>' +
        '<div class="ch-card"><div class="ch-cap"></div><b></b><span></span><em>K or SPACE to keep it</em></div>' +
        '<div class="ch-pause"><h2>PAUSED</h2><button data-c="resume">RESUME</button><button data-c="retry">RESTART AREA</button><button data-c="quit">QUIT TO TITLE</button><p>J slap ×3 · K grab / throw · L parry · L+dir dodge, hold to CHARGE · SPACE ability</p></div>' +
        '<div class="ch-over"><h2></h2><p></p><button data-c="retry">TRY AGAIN</button><button data-c="quit">QUIT TO TITLE</button></div>';
      document.body.appendChild(h);
      h.addEventListener('click', (e) => { const b = e.target.closest('[data-c]'); if (b) this.command(b.dataset.c); });
      this.el = (s) => h.querySelector(s);
      this.barEls = [];
    }
    say(big, small, dur) { const e = this.el('.ch-say'); e.querySelector('b').textContent = big; e.querySelector('span').textContent = small || ''; e.classList.add('on'); clearTimeout(this.sayT); this.sayT = setTimeout(() => e.classList.remove('on'), (dur || 2.5) * 1000); }
    prompt(t) { const e = this.el('.ch-prompt'); e.textContent = t || ''; e.classList.toggle('on', !!t); }
    command(c) {
      if (c === 'resume') this.setPause(false);
      else if (c === 'retry') { this.setPause(false); this.retry(); }
      else if (c === 'quit') { this.g.endCampaign(); }
    }
    setPause(on) { this.paused = on; this.el('.ch-pause').classList.toggle('on', on); }
    onKey(e) {
      if (e.code === 'Escape' || e.code === 'KeyP') { if (this.over) return; this.setPause(!this.paused); return true; }
      if (this.paused) { if (e.code === 'KeyR') this.command('retry'); else if (e.code === 'KeyQ') this.command('quit'); else if (e.code === 'Enter' || e.code === 'KeyJ') this.command('resume'); return true; }
      if (this.over) { if (e.code === 'Enter' || e.code === 'KeyJ' || e.code === 'KeyR') this.command(this.over === 'win' ? 'quit' : 'retry'); else if (e.code === 'KeyQ' || e.code === 'Escape') this.command('quit'); return true; }
      return false;
    }

    // ============================================================== main frame
    frame(dt) {
      if (!this.scene) return;
      const g = this.g;
      if (!this.paused && !this.cardOpen) {
        if (this.hitstop > 0) this.hitstop -= dt;
        else {
          const ts = this.slow > 0 ? 0.35 : 1; if (this.slow > 0) this.slow -= dt;
          this.acc += dt * ts; let n = 0;
          while (this.acc >= STEP && n < 12) { this.ctrl.update(STEP); this.step(STEP); S.kb.flush && 0; this.acc -= STEP; n++; }
          if (n >= 12) this.acc = 0;
        }
      } else if (this.cardOpen) { this.ctrl.update(dt); if (this.ctrl.grab.pressed || this.ctrl.skill.pressed || this.ctrl.push.pressed) this.closeCard(); }
      S.kb.flush();
      this.draw(dt);
      void g;
    }

    // ============================================================== simulation
    step(dt) {
      this.t += dt;
      const P = this.P;
      this.flow(dt);
      this.playerStep(P, dt);
      for (const a of this.actors) if (a !== P) this.enemyStep(a, dt);
      for (const a of this.actors) this.physics(a, dt);
      this.separate();
      this.propStep(dt);
      this.shotStep(dt);
      this.fireStep(dt);
      if (this.abCd > 0) this.abCd -= dt;
      // tidy up the knocked-out
      for (const a of this.actors) if (a !== this.P && a.dead && a.t > 2.2 && !a.gone) { a.gone = true; a.view.dispose ? a.view.dispose(this.scene) : 0; }
      this.actors = this.actors.filter((a) => !a.gone);
    }

    // zones: wake enemies when you walk in, open the way on when the zone is clear
    flow(dt) {
      const P = this.P, Z = this.zones[this.zi];
      if (!Z) return;
      if (Z.state === 'wait' && P.z < Z.z0 + 1.5) {
        Z.state = 'fight'; this.spawnZone(Z);
        this.el('.ch-zone').textContent = Z.name; this.el('.ch-zone').classList.add('on'); this.el('.ch-go').classList.remove('on');
        setTimeout(() => this.el('.ch-zone') && this.el('.ch-zone').classList.remove('on'), 2200);
      }
      if (Z.state === 'fight') {
        const alive = Z.ens.filter((e) => !e.dead);
        if (!alive.length && (!Z.boss || Z.bossDone)) {
          Z.state = 'clear';
          if (Z.boss) { this.win(); return; }
          this.zi++; const N = this.zones[this.zi]; this.gate = N ? N.z1 : -999;
          P.hp = Math.min(P.maxHp, P.hp + 20);
          this.el('.ch-go').classList.add('on'); this.g.audio.blip(true); this.g.audio.swell(0.3, 0.8);
          this.say('CLEAR', N ? 'Head deeper: ' + N.name.toLowerCase() : '', 2);
        }
      }
    }
    spawnZone(Z) {
      if (Z.boss) {
        const B = this.addActor('boss', Z.boss.x, Z.boss.z - 6, { zone: Z }); B.f = Math.PI / 2; this.B = B; Z.ens.push(B);
        this.el('.ch-boss').classList.add('on'); this.el('.ch-boss b').textContent = KINDS.boss.name;
        this.say(KINDS.boss.name, 'Champion of the tuna auction', 3); this.g.audio.roar(); this.g.audio.taiko();
        this.backGate = Z.z0 + 1; // the curtains close behind you
        return;
      }
      for (const [kind, x, z, fat] of Z.spawns) { const e = this.addActor(kind, x, z, { fat: fat === 'fat', zone: Z }); e.f = Math.PI / 2; Z.ens.push(e); }
      this.backGate = Z.z0 + 1.2;
    }
    retry() {
      const Z = this.zones[this.zi];
      this.over = null; this.el('.ch-over').classList.remove('on');
      for (const e of Z.ens) { e.dead = true; e.t = 99; }
      this.actors = this.actors.filter((a) => { if (a !== this.P && a.zone === Z) { if (a.view.dispose) a.view.dispose(this.scene); return false; } return true; });
      Z.ens = []; Z.state = 'wait'; Z.bossDone = false; this.B = null; this.el('.ch-boss').classList.remove('on');
      const P = this.P; P.hp = P.maxHp; P.dead = false; P.st = 'free'; P.t = 0; P.held = null; P.holder = null;
      P.x = 0; P.z = Z.z0 + 3; P.vx = P.vz = 0; this.shots = [];
    }
    win() {
      this.over = 'win'; this.slow = 1.2;
      setTimeout(() => {
        const o = this.el('.ch-over'); o.querySelector('h2').textContent = 'VICTORY';
        o.querySelector('p').textContent = 'The tuna auction is yours. +200,000 yen'; o.querySelector('[data-c="retry"]').style.display = 'none'; o.classList.add('on');
        S.profile.yen += 200000; S.profile.save && S.profile.save(); this.g.ui.setYen && this.g.ui.setYen();
      }, 1600);
      this.g.audio.roar(); this.g.audio.taiko();
    }
    lose() {
      if (this.over) return; this.over = 'lose';
      setTimeout(() => { const o = this.el('.ch-over'); o.querySelector('h2').textContent = 'DEFEATED'; o.querySelector('p').textContent = 'Try this area again'; o.querySelector('[data-c="retry"]').style.display = ''; o.classList.add('on'); }, 1200);
    }

    // ============================================================== the player
    playerStep(P, dt) {
      const c = this.ctrl;
      P.t += dt; if (P.iframe > 0) P.iframe -= dt; if (P.giant > 0) P.giant -= dt; if (P.iron > 0) P.iron -= dt;
      if (P.dead) { P.vx *= 0.9; P.vz *= 0.9; return; }
      let mx = c.mx, mz = c.mz; const mag = Math.hypot(mx, mz);
      if (mag > 1) { mx /= mag; mz /= mag; }
      const dirA = mag > 0.3 ? Math.atan2(mz, mx) : P.f;
      const wantMove = (sp, turn) => { P.tvx = mx * sp; P.tvz = mz * sp; if (mag > 0.3) P.f += ang(dirA - P.f) * Math.min(1, dt * (turn || 14)); };
      P.tvx = 0; P.tvz = 0;
      const giant = P.giant > 0 ? 1.35 : 1;
      // the ability (space)
      if (c.skill.pressed && this.ability && this.abCd <= 0 && ['free', 'hold', 'strike'].includes(P.st)) this.useAbility();
      // interacting with the gacha machine
      const gm = this.map.gacha, nearG = !this.ability && Math.hypot(P.x - gm.x, P.z - gm.z) < 1.9;
      const atStart = P.z > -11 && !this.ability;
      if (nearG !== this.nearGacha || atStart !== this.atStart) { this.nearGacha = nearG; this.atStart = atStart; this.prompt(nearG ? 'K: spin the gacha' : atStart ? 'Grab a free gacha from the red machine (walk up, press K)' : ''); }
      switch (P.st) {
        case 'free': {
          wantMove(4.3 * giant);
          if (c.push.pressed) this.strike(P);
          else if (c.grab.pressed) { if (nearG) this.spinGacha(); else { this.aim(P, 1.8); this.set(P, 'grab', 0.22); } }
          else if (c.dash.pressed) { if (mag > 0.3) { this.set(P, 'lprep', 0.14); P.ldir = dirA; } else { this.set(P, 'parry', 0.26); this.g.audio.whoosh(0.08); } }
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
        case 'hold': {
          wantMove(3.0, 12);
          const H = P.held;
          if (!H || H.dead || (H.st && H.st !== 'held' && !H.D)) { P.held = null; this.set(P, 'free'); break; }
          if (!H.D) { // holding an enemy: J knees them, K throws; they break free after a while
            if (c.push.pressed && (P.knees || 0) < 3) { P.knees = (P.knees || 0) + 1; this.damage(H, 7, P, 0, 0, false); this.g.audio.thump(3); this.R && this.hitFx(H.x, H.z, 0.6); }
            if (c.grab.pressed || (c.push.pressed && P.knees >= 3)) this.throwHeld(P);
            else if (P.t > 2.6) { this.release(P, true); }
          } else if (c.grab.pressed || c.push.pressed) this.throwHeld(P);
          break;
        }
        case 'throw': wantMove(0.6); if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'lprep': {
          wantMove(0.5);
          if (!c.dash.held) { this.set(P, 'dodge', 0.24); P.iframe = 0.26; const d = mag > 0.3 ? dirA : P.ldir; P.vx = Math.cos(d) * 11; P.vz = Math.sin(d) * 11; P.f = d; this.g.audio.whoosh(0.15); }
          else if (P.t >= P.dur) { this.set(P, 'charge', 1.5); P.cdir = mag > 0.3 ? dirA : P.ldir; P.f = P.cdir; P.chargeHits = new Set(); this.g.audio.whoosh(0.35); }
          break;
        }
        case 'dodge': P.tvx = P.vx * 0.9; P.tvz = P.vz * 0.9; if (P.t >= P.dur) this.set(P, 'free'); break;
        case 'charge': {
          if (mag > 0.3) P.cdir += clamp(ang(dirA - P.cdir), -dt * 2.2, dt * 2.2);
          const sp = Math.min(9.5 * giant, 4 + P.t * 22);
          P.f = P.cdir; P.tvx = Math.cos(P.cdir) * sp; P.tvz = Math.sin(P.cdir) * sp; P.vx = P.tvx; P.vz = P.tvz;
          this.chargeHits(P, sp);
          if (P.t > 0.05 && Math.random() < 0.5) this.fx.dust(P.x - Math.cos(P.f) * 0.5, 0.05, P.z - Math.sin(P.f) * 0.5, 1, 0.2, 0.3, 0.3);
          if (!c.dash.held || P.t >= P.dur) this.set(P, 'recover', 0.22);
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
    strike(P) {
      this.aim(P, 2.2);
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
          if (T.hitLog.length >= 2) { this.parried(A, T); T.hitLog = []; continue; }
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
          this.damage(best, best.kind === 'boss' ? 40 : 30, P, Math.cos(P.f) * 3, Math.sin(P.f) * 3, true);
          this.set(P, 'throw', 0.4); this.g.audio.thump(10); this.R.shake && 0; this.shake = 0.5;
          this.say('BELLY TOSS!', '', 1); return true;
        }
        if (best.holdP) this.escapeFrom(best);
        best.st = 'held'; best.t = 0; best.holder = P; P.held = best; P.knees = 0; this.set(P, 'hold'); this.g.audio.grab();
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
    throwHeld(P) {
      const H = P.held; P.held = null; this.set(P, 'throw', 0.28);
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
      if (T.dead) return;
      if (T === this.P) {
        if (T.iframe > 0 || T.st === 'dodge' || T.iron > 0) { if (T.iron > 0) this.popAt(T, 'IRON BODY'); return; }
        if (T.st === 'parry' && T.t < 0.22 && A && A !== T) { this.parried(A, T); return; }
        if (T.st === 'block') { dmg *= 0.35; kx *= 0.3; kz *= 0.3; heavy = false; this.g.audio.thump(2); }
        if (T.giant > 0) { heavy = false; kx *= 0.3; kz *= 0.3; }
      }
      const slick = this.onPuddle(T);
      T.hp -= dmg; T.lastHit = this.t;
      if (A && T.st === 'held' && A !== T.holder) { /* hit while held */ }
      const resist = clamp(1.6 / (T.mass || 1), 0.12, 1.2) * (slick ? 1.5 : 1);
      if (T.kind === 'boss' && !(T.st === 'dazed')) { kx *= 0.05; kz *= 0.05; heavy = false; }
      T.vx += kx * resist; T.vz += kz * resist;
      this.hitFx(T.x, T.z, heavy ? 1 : 0.6);
      if (T.hp <= 0) { this.ko(T, kx, kz); return; }
      if (T.st === 'held') return;
      if (T === this.P && this.P.held) this.release(this.P);
      const canDown = T.kind !== 'boss' && !(T.kind === 'sumo' && !(T.stun > 0));
      if ((heavy || (slick && dmg >= 8)) && canDown && !(T.fat && !heavy)) { this.set(T, 'down', T === this.P ? 0.85 : 1.15); T.fallX = kx; T.fallZ = kz; if (T.holdP) this.escapeFrom(T); }
      else if (T.kind !== 'boss' && T.kind !== 'sumo') { if (T.holdP) this.escapeFrom(T); if (T.st !== 'act' || heavy) this.set(T, 'hurt', T === this.P ? 0.32 : 0.38); }
    }
    ko(T, kx, kz) {
      T.hp = 0;
      if (T === this.P) { T.dead = true; this.set(T, 'down', 99); this.lose(); return; }
      T.dead = true; this.set(T, 'down', 99); T.fallX = kx || 0; T.fallZ = kz || 1;
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
    onPuddle(a) { for (const p of this.map.puddles) if (Math.hypot((a.x - p.x) / p.sx, a.z - p.z) < p.r) return true; return false; }

    // ============================================================== enemies
    enemyStep(E, dt) {
      E.t += dt; if (E.stun > 0) E.stun -= dt; if (E.cd > 0) E.cd -= dt * (this.buffed(E) ? 1.7 : 1);
      if (E.frozen > 0) { E.frozen -= dt; E.vx = E.vz = 0; return; }
      if (E.blind > 0) E.blind -= dt;
      if (E.dead) { E.vx *= 0.9; E.vz *= 0.9; return; }
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
          const want = { fighter: 1.0, rusher: 4.5, technical: 1.0, grappler: 0.9, thrower: 6, staff: 1.9, commander: 2.6, sumo: 1.4 }[E.kind];
          if (E.kind === 'thrower') { // keep the distance, step away when you get close
            if (d < 4) go(E.x - dx, E.z - dz, sp); else if (d > 8) go(P.x, P.z, sp); else this.strafe(E, toP, sp * 0.5);
            if (E.cd <= 0 && d < 11 && token) this.begin(E, 'bottle', 0.55);
            break;
          }
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
            if (E.kind === 'rusher') this.begin(E, d > 2.5 ? 'rush' : 'jab', d > 2.5 ? 0.5 : 0.36);
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
        case 'down': if (E.t >= E.dur) this.set(E, 'getup', 0.45); break;
        case 'getup': if (E.t >= E.dur) this.set(E, 'free'); break;
        case 'hold': { // a grappler holding you: throw after a beat
          face(toP, 4);
          if (!E.holdP) { this.set(E, 'free'); break; }
          if (E.t > 1.35) { const Pp = E.holdP; this.escapeFrom(E); this.damage(Pp, 17, null, Math.cos(E.f) * 7, Math.sin(E.f) * 7, true); this.set(E, 'recover', 0.6); this.g.audio.thump(8); this.shake = 0.3; }
          break;
        }
        case 'held': { const H = E.holder; if (!H) { this.set(E, 'free'); break; } E.x = H.x + Math.cos(H.f) * (H.r + E.r * 0.6); E.z = H.z + Math.sin(H.f) * (H.r + E.r * 0.6); E.y = 0.5; E.vx = E.vz = 0; E.f = H.f + Math.PI; break; }
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
        case 'jab': if (!E.hitDone && E.t > 0.05) { E.hitDone = true; this.meleeHit(E, 1.15, 0.9, E.fat ? 11 : 8, 2.5, false); } break;
        case 'slap': if (!E.hitDone && E.t > 0.06) { E.hitDone = true; this.meleeHit(E, 1.7, 0.9, 14, 6, true); } break;
        case 'grab':
          if (!E.hitDone && E.t > 0.05) {
            E.hitDone = true;
            if (d < E.r + P.r + 0.75 && Math.abs(ang(toP - E.f)) < 0.9 && !['down', 'dodge', 'grabbed', 'getup'].includes(P.st) && P.iframe <= 0 && !(P.giant > 0)) {
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
          if (!E.hitDone && E.t > 0.1) { E.hitDone = true; this.meleeHit(E, 2.3, 1.9, 14, 6, true); this.fx.ring(E.x, E.z, 2.4, 0.3); this.g.audio.whoosh(0.4); }
          break;
        case 'bottle':
          if (!E.hitDone) { E.hitDone = true; const lead = 0.5, tx = P.x + P.vx * lead, tz = P.z + P.vz * lead; const a = Math.atan2(tz - E.z, tx - E.x), l = Math.hypot(tx - E.x, tz - E.z), T = l / 10;
            this.shots.push({ kind: 'bottle', x: E.x, z: E.z, y: 1.5, vx: Math.cos(a) * 10, vz: Math.sin(a) * 10, vy: (1.0 - 1.5) / Math.max(0.15, T) + 9 * Math.max(0.15, T), by: E, mesh: shotMesh(this.scene, 'bottle'), t: 0 });
            this.g.audio.whoosh(0.2); }
          break;
        case 'shout':
          if (!E.hitDone) { E.hitDone = true; this.popAt(E, 'GET HIM!'); this.fx.ring(E.x, E.z, 7, 0.6); this.g.audio.clap(); for (const a of this.actors) if (a.team === 1 && !a.dead && a !== E) a.cd = Math.min(a.cd, 0.2); }
          break;
      }
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
            else this.bossBegin(B, 'stomp', 1.0 * k);
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
            if (B.phase === 2 && !B.double) { B.double = true; this.bossBegin(B, 'stomp', 0.55); } else { B.double = false; this.set(B, 'recover', 0.75); }
          }
          break;
        }
        case 'recover': if (B.t >= B.dur) this.set(B, 'free'); break;
        case 'dazed': if (B.t >= B.dur) this.set(B, 'free'); break;
        case 'hurt': case 'down': case 'getup': this.set(B, 'free'); break;
      }
    }
    bossBegin(B, atk, wind) { B.atk = atk; this.set(B, 'wind', wind); B.cd = rnd(0.9, 1.6) * (B.phase === 2 ? 0.7 : 1); if (atk === 'stomp') this.g.audio.taiko(); }
    bossStomp(B) {
      const P = this.P, R = 3.7, d = Math.hypot(P.x - B.x, P.z - B.z);
      this.fx.ring(B.x, B.z, R, 0.5); this.fx.burst(B.x, B.z, 1.4); this.shake = 0.6; this.g.audio.thump(12);
      for (let i = 0; i < 14; i++) { const a = i / 14 * TAU; this.fx.dust(B.x + Math.cos(a) * R * 0.7, 0.05, B.z + Math.sin(a) * R * 0.7, 2, 0.3, 0.6, 0.4, Math.cos(a) * 3, Math.sin(a) * 3); }
      if (d < R + P.r) this.damage(P, 16, B, (P.x - B.x) / (d || 1) * 7, (P.z - B.z) / (d || 1) * 7, true);
      for (const p of this.props) if (!p.dead && Math.hypot(p.x - B.x, p.z - B.z) < R && p.D.wt !== 'heavy') { p.vy = 3; p.y = 0.05; p.vx += (p.x - B.x) * 1.2; p.vz += (p.z - B.z) * 1.2; p.hop = true; }
    }

    // ============================================================== abilities (the gacha)
    spinGacha() {
      const A = POOL[Math.floor(Math.random() * POOL.length)];
      this.ability = A; this.abCd = 0; this.cardOpen = true; this.nearGacha = false; this.prompt('');
      const c = this.el('.ch-card'); c.querySelector('b').textContent = A.name; c.querySelector('span').textContent = A.desc; c.classList.add('on');
      this.el('.ch-ab em').textContent = A.name; this.g.audio.clack(); this.g.audio.swell(0.5, 1.2);
    }
    closeCard() { this.cardOpen = false; this.el('.ch-card').classList.remove('on'); this.prompt('Use it with SPACE. It recharges.'); setTimeout(() => this.prompt(''), 3500); }
    useAbility() {
      const A = this.ability, P = this.P, fx = Math.cos(P.f), fz = Math.sin(P.f);
      this.abCd = A.cd; this.popAt(P, A.name); this.g.audio.swell(0.4, 0.8);
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
          T.clawT = 1.4; this.set(T, 'clawed', 1.4); this.g.audio.whoosh(0.5); break;
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
      for (const e of this.actors) if (e.st === 'clawed') {
        e.vx = e.vz = 0; e.y = e.t < 0.9 ? Math.min(2.6, e.t * 4) : Math.max(0, 2.6 - (e.t - 0.9) * 12);
        if (e.t >= e.dur) { e.y = 0; this.damage(e, e.kind === 'boss' ? 40 : 45, P, 0, 0, true); this.shake = 0.4; this.fx.burst(e.x, e.z, 1); if (!e.dead) this.set(e, 'down', 1.2); }
      }
    }

    // ============================================================== physics
    physics(a, dt) {
      const slick = this.onPuddle(a);
      const fr = a.st === 'thrown' ? 0 : slick ? 2.2 : 11;
      if (a.tvx !== undefined && !['hurt', 'down', 'thrown', 'held', 'dazed', 'getup', 'grabbed', 'clawed'].includes(a.st) && !a.dead) {
        const k = 1 - Math.exp(-dt * (slick ? 3 : 14));
        a.vx += (a.tvx - a.vx) * k; a.vz += (a.tvz - a.vz) * k;
      } else { const k = Math.exp(-dt * fr); a.vx *= k; a.vz *= k; }
      if (a.st === 'thrown') {
        a.vy -= 18 * dt; a.y += a.vy * dt;
        for (const T of this.actors) if (T !== a && T !== a.thrownBy && !T.dead && T.team === a.team && Math.hypot(T.x - a.x, T.z - a.z) < T.r + a.r && a.y < 1.4) { this.damage(T, 15, a.thrownBy, a.vx * 0.6, a.vz * 0.6, true); }
        if (a.y <= 0) { a.y = 0; this.damage(a, 20, a.thrownBy, a.vx * 0.4, a.vz * 0.4, true); if (!a.dead) this.set(a, 'down', 1.1); this.shake = 0.3; this.g.audio.thump(8); this.fx.dust(a.x, 0.05, a.z, 8, 0.4, 0.5, 0.4); }
      } else if (a.st !== 'held' && a.st !== 'clawed') a.y = 0;
      if (a.st === 'held' || a.st === 'grabbed') return;
      a.x += a.vx * dt; a.z += a.vz * dt;
      // walls (axis-aligned boxes) and the zone gates
      for (const w of this.map.walls) this.pushOut(a, w);
      if (a.team === 0 || a.st === 'thrown') {
        if (a.z < this.gate + a.r && this.zones[this.zi] && this.zones[this.zi].state !== 'clear') { a.z = this.gate + a.r; if (a.vz < 0) a.vz = 0; }
        if (this.backGate !== undefined && a.team === 0 && a.z > this.backGate - a.r && this.zones[this.zi] && this.zones[this.zi].state === 'fight') { a.z = this.backGate - a.r; if (a.vz > 0) a.vz = 0; }
      }
      // dust when moving fast, slide streaks on wet floor
      const sp = Math.hypot(a.vx, a.vz);
      if (slick && sp > 4 && Math.random() < 0.3) this.fx.dust(a.x, 0.04, a.z, 1, 0.15, 0.2, 0.25);
    }
    pushOut(a, w) {
      const cx = clamp(a.x, w.x0, w.x1), cz = clamp(a.z, w.z0, w.z1), dx = a.x - cx, dz = a.z - cz, d = Math.hypot(dx, dz);
      if (d >= a.r) return false;
      if (d < 1e-5) { // centre inside the box: push out the shortest way
        const opts = [[w.x0 - a.r - a.x, 0], [w.x1 + a.r - a.x, 0], [0, w.z0 - a.r - a.z], [0, w.z1 + a.r - a.z]].sort((p, q) => Math.abs(p[0] + p[1]) - Math.abs(q[0] + q[1]));
        a.x += opts[0][0]; a.z += opts[0][1];
      } else { const k = (a.r - d) / d; a.x += dx * k; a.z += dz * k; const vn = (a.vx * dx + a.vz * dz) / d; if (vn < 0) { a.vx -= vn * dx / d; a.vz -= vn * dz / d; } }
      if (Math.hypot(a.vx, a.vz) > 6 || a.st === 'act') a.bumped = true;
      return true;
    }
    separate() {
      const L = this.actors.filter((a) => !a.dead && !['held', 'grabbed', 'thrown', 'clawed'].includes(a.st));
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
        if (p.held) { const H = p.held; p.x = H.x + Math.cos(H.f) * 0.2; p.z = H.z + Math.sin(H.f) * 0.2; p.y = 1.55 * (H.w ? H.w.szCur : 1); p.ry = -H.f; continue; }
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
    killProp(p) { p.dead = true; if (p.mesh.parent) p.mesh.parent.remove(p.mesh); }
    addPuddleMesh(x, z) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.8).rotateX(-Math.PI / 2), this.map.decor.find((d) => d.kind === 'puddle').m.material);
      m.position.set(x, 0.013, z); m.renderOrder = 1; this.scene.add(m);
    }
    shotStep(dt) {
      for (const s of this.shots) {
        s.t += dt; s.vy -= 18 * dt; s.x += s.vx * dt; s.z += s.vz * dt; s.y += s.vy * dt;
        s.mesh.position.set(s.x, s.y, s.z); s.mesh.rotation.x += dt * 14;
        const P = this.P;
        if (s.kind === 'bottle' && !s.done && s.by !== P && Math.hypot(P.x - s.x, P.z - s.z) < P.r + 0.35 && s.y < 1.9) {
          if (P.st === 'parry' && P.t < 0.26) { // PARRY: swat it back at whoever threw it
            const T = s.by && !s.by.dead ? s.by : null, a = T ? Math.atan2(T.z - s.z, T.x - s.x) : P.f + Math.PI, l = T ? Math.hypot(T.x - s.x, T.z - s.z) : 6, ft = Math.max(0.2, l / 14);
            s.by = P; s.vx = Math.cos(a) * 14; s.vz = Math.sin(a) * 14; s.vy = (1.0 - s.y) / ft + 9 * ft; s.back = true;
            this.popAt(P, 'PARRY!'); this.g.audio.hyoshigi(); this.g.audio.slap(6); this.hitFx(s.x, s.z, 0.9, true);
          } else if (P.st === 'block') { s.done = true; this.g.audio.thump(2); }
          else if (P.st !== 'dodge' && P.iframe <= 0) { s.done = true; this.damage(P, 10, s.by, s.vx * 0.3, s.vz * 0.3, false); this.g.audio.slap(4); }
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
      for (const a of this.actors) this.drawActor(a, dt, T);
      for (const p of this.props) if (!p.dead) {
        p.mesh.position.set(p.x, p.y, p.z);
        p.mesh.rotation.set(p.thrown || p.hop ? p.spin : 0, p.held || p.thrown ? -p.ry : p.ry, 0);
      }
      for (const F of this.fires) F.mesh.material.opacity = 0.35 + Math.sin(T * 20 + F.x) * 0.1;
      this.map.update(T);
      this.fx.update(dt);
      this.telegraphs(T);
      // camera: high angle, follows you, frames the space ahead
      const P = this.P, Z = this.zones[this.zi], boss = Z && Z.boss && Z.state === 'fight';
      const hw = this.map.halfWidth(P.z), tx = clamp(P.x * 0.65, -Math.max(0, hw - 6), Math.max(0, hw - 6));
      const want = new THREE.Vector3(boss ? clamp((P.x + (this.B ? this.B.x : 0)) / 2, -4, 4) : tx, 0, boss ? (P.z + (this.B ? this.B.z : P.z)) / 2 : P.z - 2.6);
      this.camT.lerp(want, 1 - Math.exp(-dt * 4));
      const dist = boss ? 22 : 18.5, sh = this.shake > 0 ? this.shake : 0; this.shake = Math.max(0, (this.shake || 0) - dt * 1.6);
      this.cam.position.set(this.camT.x + (Math.random() - 0.5) * sh * 0.5, dist * 0.78 + (Math.random() - 0.5) * sh * 0.5, this.camT.z + dist * 0.62);
      this.cam.lookAt(this.camT.x, 0.6, this.camT.z);
      this.cam.updateMatrixWorld();
      S.R3.setLight(this.cam, R.anime);
      if (R.anime && R.post) R.post.render(this.scene, this.cam, T); else R.r.render(this.scene, this.cam);
      this.drawHud();
    }
    drawActor(a, dt, T) {
      if (a.gone) return;
      if (a.w) { // the wrestler model: translate our state into its poses
        const w = a.w, st = a.st;
        w.x = a.x; w.z = a.z; w.y = a.y; w.f = a.f; w.fx = Math.cos(a.f); w.fz = Math.sin(a.f); w.vx = a.vx; w.vz = a.vz; w.spd = Math.hypot(a.vx, a.vz);
        const map = { free: 'free', strike: 'palm', grab: 'grab', hold: 'grab', throw: 'heavy', lprep: 'brace', dodge: 'dash', charge: 'charge', parry: 'brace', block: 'brace',
          recover: 'recover', bonk: 'stun', hurt: 'stun', down: 'fall', getup: 'recover', grabbed: 'stun', intro: 'free', roar: 'win', wind: a.atk === 'stomp' ? 'bigstomp' : a.atk === 'charge' ? 'wind' : 'wind',
          act: a.atk === 'stomp' ? 'bigstomp' : a.atk === 'charge' ? 'charge' : 'slap', dazed: 'stun', held: 'stun', thrown: 'fall', clawed: 'stun' };
        const nst = map[st] || 'free';
        if (w.st !== nst) { w.st = nst; w.t = 0; } else w.t = st === 'hold' ? 0.12 : a.t;
        if (st === 'wind' && a.atk === 'stomp') w.t = a.t * (0.45 / Math.max(0.01, a.dur)); // lift the leg over the wind-up
        if (st === 'act' && a.atk === 'stomp') w.t = 0.46 + a.t;
        w.dur = a.dur || 1; w.hand = a.hand || 0; w.down = st === 'down' && a.t > 0.25; w.fallX = a.fallX || 0; w.fallZ = a.fallZ || 1; w.ddx = Math.cos(a.f); w.ddz = Math.sin(a.f);
        w.fxs = { dizzy: a.stun > 0 || st === 'dazed' ? 1 : 0, frozen: a.frozen > 0 ? 1 : 0, invuln: a.iron > 0 ? 1 : 0 };
        w.lifted = st === 'held' || st === 'clawed';
        a.view.update(w, Math.max(dt, 1e-4), T);
        a.view.root.visible = !(a.iframe > 0 && st === 'getup' && Math.sin(T * 40) > 0);
      } else a.view.update(a, dt, T);
    }
    telegraphs(T) {
      // red warnings under anyone winding up an attack, so every hit can be read and answered
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
      for (const a of this.actors) {
        if (a.st !== 'wind' || a.dead) continue;
        const k = clamp(a.t / Math.max(0.01, a.dur), 0, 1), pulse = 0.42 + 0.35 * k + 0.12 * Math.sin(T * 30);
        let m;
        if (a.atk === 'stomp') { m = get('disc'); m.scale.set(3.7 * k, 1, 3.7 * k); m.rotation.y = 0; }
        else if (a.atk === 'charge' || a.atk === 'rush') { m = get('line'); const L = a.kind === 'boss' ? 16 : 6; m.scale.set(L, 1, a.r * 2); m.rotation.y = -a.f; }
        else if (a.atk === 'sweep') { m = get('wide'); m.scale.set(2.4, 1, 2.4); m.rotation.y = -a.f; }
        else if (a.atk === 'bottle') { m = get('ring'); const P = this.P; m.scale.set(0.8, 1, 0.8); m.position.set(P.x, 0.03, P.z); m.material.opacity = pulse; continue; }
        else if (a.atk === 'shout') { m = get('ring'); m.scale.set(7, 1, 7); m.rotation.y = 0; }
        else { m = get('cone'); const r = a.kind === 'boss' ? 2.2 : a.kind === 'sumo' ? 1.9 : 1.4; m.scale.set(r + a.r, 1, r + a.r); m.rotation.y = -a.f; }
        m.position.set(a.x, 0.03, a.z); m.material.opacity = pulse;
        m.material.color.set(a.atk === 'grab' ? 0xff8a1a : 0xff2a2a); // orange = a grab (break it with K)
      }
      // a red "!" over anyone winding up an attack (orange for a grab)
      if (!this.bangTex) this.bangTex = S.R3.canvasTex(64, 64, (c) => { c.fillStyle = '#fff8ec'; c.beginPath(); c.arc(32, 32, 30, 0, 7); c.fill(); c.fillStyle = '#e2322b'; c.beginPath(); c.arc(32, 32, 25, 0, 7); c.fill(); c.fillStyle = '#fff8ec'; c.font = '900 44px "Dela Gothic One", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('!', 32, 34); });
      for (const a of this.actors) {
        const on = a.st === 'wind' && !a.dead;
        if (on && !a.bang) { a.bang = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.bangTex, depthTest: false, transparent: true })); a.bang.renderOrder = 9; this.scene.add(a.bang); }
        if (a.bang) {
          a.bang.visible = on;
          if (on) { const h = (a.w ? 2.5 * (a.size || 1) : 2.3) + Math.sin(T * 14) * 0.06; a.bang.position.set(a.x, h, a.z); a.bang.scale.setScalar(a.kind === 'boss' ? 1.1 : 0.7); a.bang.material.color.set(a.atk === 'grab' ? 0xffb050 : 0xffffff); }
          if (a.gone) { this.scene.remove(a.bang); a.bang = null; }
        }
      }
      // the gate ahead: a glowing strip on the floor when the way is open
      if (!this.goM) { this.goM = new THREE.Mesh(new THREE.PlaneGeometry(6, 0.6).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x3fe0a0, transparent: true, opacity: 0.5, depthWrite: false })); this.scene.add(this.goM); }
      const Z = this.zones[this.zi], open = this.zi > 0 && Z && Z.state === 'wait';
      this.goM.visible = !!open; if (open) { this.goM.position.set(0, 0.03, Z.z0 + 1); this.goM.material.opacity = 0.3 + 0.25 * Math.sin(T * 6); }
    }
    drawHud() {
      const P = this.P;
      this.el('.ch-me .ch-bar i').style.width = Math.max(0, P.hp / P.maxHp * 100) + '%';
      this.el('.ch-me .ch-bar').classList.toggle('low', P.hp < 30);
      const A = this.ability; this.el('.ch-ab').classList.toggle('ready', !!A && this.abCd <= 0);
      this.el('.ch-cd i').style.width = A ? (100 * (1 - Math.max(0, this.abCd) / A.cd)) + '%' : '0%';
      if (this.B) this.el('.ch-boss .ch-bar i').style.width = Math.max(0, this.B.hp / this.B.maxHp * 100) + '%';
      // small health bars over hurt enemies
      const bars = this.el('.ch-bars'); let i = 0;
      for (const a of this.actors) {
        if (a.team !== 1 || a.dead || a.kind === 'boss' || a.hp >= a.maxHp) continue;
        let b = this.barEls[i]; if (!b) { b = document.createElement('span'); b.innerHTML = '<i></i>'; bars.appendChild(b); this.barEls.push(b); }
        const p = this.project(a.x, 2.1 * (a.size || 1) * (a.fat ? 1.05 : 1), a.z);
        b.style.display = ''; b.style.left = p.x + 'px'; b.style.top = p.y + 'px'; b.firstChild.style.width = (a.hp / a.maxHp * 100) + '%'; i++;
      }
      for (; i < this.barEls.length; i++) this.barEls[i].style.display = 'none';
      if (this.flash > 0) { this.flash -= 0.05; document.body.style.setProperty('--campFlash', this.flash); }
    }
  }

  // ---------------------------------------------------------------- props: simple readable shapes
  function propMesh(type) {
    const D = PROPS[type], g = new THREE.Group(), M = (c, s) => S.toon(c, { shade: s, rimAmt: 0.35 }), B = S.CampMap.box, C = S.CampMap.cyl;
    switch (type) {
      case 'crate': B(g, 0.66, 0.5, 0.66, D.col, D.shade, 0, 0.25, 0, 0.022); B(g, 0.7, 0.06, 0.7, 0x8a5a2a, 0x4a2a10, 0, 0.5, 0, 0.0); break;
      case 'crate2': B(g, 0.78, 0.5, 0.78, D.col, D.shade, 0, 0.25, 0, 0.022); B(g, 0.74, 0.5, 0.74, 0xb88050, D.shade, 0.04, 0.75, 0.02, 0.022); break;
      case 'foam': B(g, 0.62, 0.34, 0.5, D.col, D.shade, 0, 0.17, 0, 0.02); B(g, 0.5, 0.04, 0.4, 0x3fb0e0, 0x1a5a8a, 0, 0.35, 0, 0.0); break;
      case 'bottle': C(g, 0.06, 0.08, 0.26, D.col, D.shade, 0, 0.13, 0, 8, 0.012); C(g, 0.025, 0.04, 0.1, D.col, D.shade, 0, 0.3, 0, 6, 0.01); break;
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
    S.CampMap.cyl(g, 0.05, 0.07, 0.24, kind === 'molotov' ? 0xc84a1a : 0x3a9a5a, 0x2a1a10, 0, 0, 0, 8, 0.012);
    if (kind === 'molotov') { const f = new THREE.Sprite(new THREE.SpriteMaterial({ map: S.CampMap.glowTex(), color: 0xff8a2a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })); f.scale.setScalar(0.5); f.position.y = 0.2; g.add(f); }
    scene.add(g); return g;
  }

  // ---------------------------------------------------------------- market workers (non-sumo enemies)
  class WorkerView {
    constructor(scene, kind, fat) {
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
      if (K.pole) { const p = add(this.arms[1].el, new THREE.CylinderGeometry(0.035, 0.035, 2.4, 8), M(0xc8a070, 0x6a4a2a), 0, -0.33, 0.6, 1, 1, 1, 0.012); p.rotation.x = Math.PI / 2; add(p, SG, M(0x3a3a40, 0x101014), 0, 1.15, 0, 0.16, 0.08, 0.06, 0.01); }
      if (kind === 'thrower') add(this.arms[1].el, new THREE.CylinderGeometry(0.05, 0.06, 0.22, 10), M(0x3a9a5a, 0x1a4a2a, { spec: 0.5 }), 0, -0.4, 0.06, 1, 1, 1, 0.01);
      if (K.coat) { const mg = add(this.arms[0].el, new THREE.ConeGeometry(0.11, 0.28, 12, 1, true), M(0xf6f2ea, 0x9a9080), 0, -0.45, 0.09, 1, 1, 1, 0.01); mg.rotation.x = -Math.PI / 2; }
      // legs: work trousers and round rubber boots
      this.legs = [-1, 1].map((sd) => {
        const hp = new THREE.Group(); hp.position.set(sd * 0.15 * fw, 0, 0); this.hips.add(hp);
        add(hp, cap(0.115 * (fat ? 1.3 : 1), 0.28), pants, 0, -0.26, 0, 1, 1, 1, 0.022);
        add(hp, cap(0.105, 0.2), boot, 0, -0.62, 0, 1, 1, 1, 0.022);
        add(hp, SG, boot, 0, -0.83, 0.06, 0.12, 0.08, 0.19, 0.02);
        return { hp, sd };
      });
      // ground shadow
      this.shadow = new THREE.Mesh(new THREE.CircleGeometry(0.45 * fw, 20).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x1a0a20, transparent: true, opacity: 0.4, depthWrite: false }));
      this.shadow.renderOrder = 1; scene.add(this.shadow);
      this.walk = 0; this.mats = [skin, shirt, apron, pants];
      this.flashT = 0; this.lastHp = null;
    }
    update(a, dt, T) {
      const sp = Math.hypot(a.vx, a.vz), st = a.st;
      this.root.position.set(a.x, a.y || 0, a.z); this.root.rotation.set(0, Math.PI / 2 - a.f, 0);
      this.shadow.position.set(a.x, 0.014, a.z); this.shadow.visible = !a.gone;
      this.walk += dt * sp * 3.2;
      let lean = 0, armR = [0, 0, 0], armL = [0, 0, 0], elR = 0, elL = 0, legA = Math.sin(this.walk) * Math.min(1, sp / 2) * 0.6, bob = Math.abs(Math.sin(this.walk)) * 0.05 * Math.min(1, sp / 2), down = 0, spin = 0;
      armR[0] = -legA * 0.8; armL[0] = legA * 0.8; elR = -0.4; elL = -0.4;
      const k = a.dur ? clamp(a.t / a.dur, 0, 1) : 0;
      if (st === 'wind') {
        if (a.atk === 'jab' || a.atk === 'slap') { armR = [0.9, 0, -0.3]; elR = -1.4; lean = -0.15; }
        else if (a.atk === 'grab') { armR = [-0.9, 0, -0.3]; armL = [-0.9, 0, 0.3]; lean = -0.1; elR = elL = -0.2; }
        else if (a.atk === 'rush' || a.atk === 'charge') { lean = 0.55; armR = [0.6, 0, -0.4]; armL = [0.6, 0, 0.4]; }
        else if (a.atk === 'sweep') { armR = [-1.2, 0, -1.2]; lean = -0.1; this.torso.rotation.y = 1.2 * k; }
        else if (a.atk === 'bottle') { armR = [-2.6, 0, -0.2]; elR = -0.8; lean = -0.2; }
        else if (a.atk === 'shout') { armL = [-2.6, 0, 0.3]; armR = [-2.4, 0, -0.3]; }
      } else if (st === 'act') {
        if (a.atk === 'jab' || a.atk === 'slap') { armR = [-1.55, 0, 0.05]; elR = 0; lean = 0.2; }
        else if (a.atk === 'grab') { armR = [-1.5, 0, 0.1]; armL = [-1.5, 0, -0.1]; elR = elL = 0; lean = 0.25; }
        else if (a.atk === 'rush' || a.atk === 'charge') { lean = 0.6; armR = [-0.5, 0, -0.6]; armL = [-0.5, 0, 0.6]; }
        else if (a.atk === 'sweep') { armR = [-1.4, 0, -0.2]; this.torso.rotation.y = 1.2 - 2.8 * k; }
        else if (a.atk === 'bottle') { armR = [-1.2, 0, 0]; elR = 0; lean = 0.2; }
      } else if (st === 'hold') { armR = [-1.4, 0, 0.3]; armL = [-1.4, 0, -0.3]; elR = elL = -0.3; }
      else if (st === 'recover') lean = 0.15;
      if (st !== 'wind' && st !== 'act') this.torso.rotation.y *= 0.8;
      if (st === 'hurt') { lean = -0.35 + Math.sin(a.t * 30) * 0.05; armR = [-0.4, 0, -0.8]; armL = [-0.4, 0, 0.8]; }
      if (st === 'dazed' || a.blind > 0) { lean = Math.sin(T * 5) * 0.12; this.head.rotation.z = Math.sin(T * 4) * 0.3; } else this.head.rotation.z *= 0.8;
      if (st === 'down' || a.dead) { down = Math.min(1, a.t / 0.25); }
      if (st === 'getup') down = 1 - k;
      if (st === 'held' || st === 'clawed') { legA = Math.sin(T * 18) * 0.5; armR = [-0.6 + Math.sin(T * 16) * 0.4, 0, -0.6]; armL = [-0.6 - Math.sin(T * 16) * 0.4, 0, 0.6]; }
      if (st === 'thrown') spin = a.t * 12;
      if (a.frozen > 0) { legA = 0; armR = [0.2, 0, -0.2]; armL = [0.2, 0, 0.2]; }
      this.hips.position.y = 0.9 + bob - down * 0.62;
      this.hips.rotation.x = lean - down * 1.45 + spin;
      const sa = (A, v, e) => { A.sh.rotation.set(v[0], v[1], v[2]); A.el.rotation.x = e; };
      sa(this.arms[1], armR, elR); sa(this.arms[0], armL, elL);
      this.legs[0].hp.rotation.x = legA * (1 - down); this.legs[1].hp.rotation.x = -legA * (1 - down);
      // hit flash and ice tint
      if (this.lastHp !== null && a.hp < this.lastHp) this.flashT = 1;
      this.lastHp = a.hp; this.flashT = Math.max(0, this.flashT - dt * 7);
      for (const m of this.mats) { const fr = a.frozen > 0; m.uniforms.uFlashCol.value.set(fr ? 0x9fe6ff : a.burn ? 0xff7a1a : 0xffffff); m.uniforms.uFlash.value = fr ? 0.55 : this.flashT * 0.7; }
      const fade = a.dead && a.t > 1.4;
      this.root.visible = !fade || Math.sin(a.t * 30) > 0;
    }
    dispose(scene) { scene.remove(this.root); scene.remove(this.shadow); }
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

  S.Campaign = Campaign;
  S.CAMP = { PROPS, KINDS, POOL };
})();
