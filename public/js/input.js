'use strict';
// Input layer. Every player is driven by a Controller that reads a "source".
// Sources: keyboard (+ optional gamepad), AI. Touch can be added as another source later.
(function () {
  const GAME_KEYS = new Set([
    'KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyJ', 'KeyK', 'KeyL', 'KeyZ', 'KeyX', 'KeyC', 'Space',
    'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Numpad1', 'Numpad2', 'Numpad3',
    'Comma', 'Period', 'Slash', 'Backquote', 'F3', 'Numpad0', 'ShiftRight', 'Tab',
  ]);

  class Keyboard {
    constructor() {
      this.down = new Set();
      this.tap = new Set();      // latched presses so sub-frame taps are never lost
      this.listeners = [];
      addEventListener('keydown', (e) => {
        if (e.target && e.target.tagName === 'INPUT') return; // typing a name
        if (GAME_KEYS.has(e.code)) e.preventDefault();
        if (e.repeat) return;
        this.down.add(e.code);
        this.tap.add(e.code);
        for (const l of this.listeners) l(e);
      });
      addEventListener('keyup', (e) => this.down.delete(e.code));
      addEventListener('blur', () => this.down.clear());
    }
    has(codes) {
      for (const c of codes) if (this.down.has(c) || this.tap.has(c)) return true;
      return false;
    }
    flush() { this.tap.clear(); }
    on(fn) { this.listeners.push(fn); }
  }
  S.kb = new Keyboard();

  S.MAPS = {
    solo: { up: ['KeyW', 'ArrowUp'], down: ['KeyS', 'ArrowDown'], left: ['KeyA', 'ArrowLeft'], right: ['KeyD', 'ArrowRight'],
      push: ['KeyJ', 'KeyZ'], grab: ['KeyK', 'KeyX'], dash: ['KeyL', 'KeyC'], skill: ['Space'], taunts: true },
    p1: { up: ['KeyW'], down: ['KeyS'], left: ['KeyA'], right: ['KeyD'], push: ['KeyJ'], grab: ['KeyK'], dash: ['KeyL'], skill: ['Space'] },
    p2: { up: ['ArrowUp'], down: ['ArrowDown'], left: ['ArrowLeft'], right: ['ArrowRight'],
      push: ['Numpad1', 'Comma'], grab: ['Numpad2', 'Period'], dash: ['Numpad3', 'Slash'], skill: ['Numpad0', 'ShiftRight'] },
  };

  // KEY BINDINGS: the player picks one main key per action; the spare defaults stay unless taken
  S.BIND_ACTIONS = [['up', 'MOVE UP'], ['down', 'MOVE DOWN'], ['left', 'MOVE LEFT'], ['right', 'MOVE RIGHT'], ['push', 'PUSH'], ['grab', 'GRAB'], ['dash', 'DEFEND'], ['skill', 'GACHA SKILL']];
  const DEF_SOLO = JSON.parse(JSON.stringify(S.MAPS.solo));
  S.applyBinds = (b) => {
    b = b || {};
    for (const [a] of S.BIND_ACTIONS) {
      const k = b[a], taken = new Set(Object.keys(b).filter((x) => x !== a).map((x) => b[x]));
      const rest = DEF_SOLO[a].filter((c) => !taken.has(c) && c !== k);
      S.MAPS.solo[a] = k ? [k].concat(rest) : rest;
      if (k) GAME_KEYS.add(k);
    }
  };
  S.keyName = (c) => {
    if (!c) return '—';
    const n = { Space: 'SPACE', ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', ShiftLeft: 'L-SHIFT', ShiftRight: 'R-SHIFT', ControlLeft: 'L-CTRL', ControlRight: 'R-CTRL', AltLeft: 'L-ALT', AltRight: 'R-ALT', Enter: 'ENTER', Comma: ',', Period: '.', Slash: '/', Semicolon: ';', Quote: "'", BracketLeft: '[', BracketRight: ']', Backslash: '\\', Minus: '-', Equal: '=' }[c];
    return n || c.replace(/^Key/, '').replace(/^Digit/, '').replace(/^Numpad/, 'NUM ').toUpperCase();
  };
  S.mainKey = (a) => (S.MAPS.solo[a] || [])[0];
  if (S.profile) S.applyBinds(S.profile.binds);

  // a controller for player i: a gamepad (PS5, Xbox, ...) and/or a phone paired as a controller
  function readPad(i) {
    const g = readGamepad(i), ph = i != null && S.phones ? S.phones.get(i) : null;
    if (!ph) return g;
    if (!g) return { mx: ph.mx, mz: ph.mz, push: ph.push, grab: ph.grab, dash: ph.dash, skill: ph.skill, start: ph.start };
    const useG = Math.hypot(g.mx, g.mz) > 0.2;
    return { mx: useG ? g.mx : ph.mx, mz: useG ? g.mz : ph.mz, push: g.push || ph.push, grab: g.grab || ph.grab, dash: g.dash || ph.dash, skill: g.skill || ph.skill, start: g.start || ph.start };
  }
  function readGamepad(i) {
    if (i == null || !navigator.getGamepads) return null;
    const gp = navigator.getGamepads()[i];
    if (!gp || !gp.connected) return null;
    const b = (n) => !!(gp.buttons[n] && gp.buttons[n].pressed);
    let mx = gp.axes[0] || 0, mz = gp.axes[1] || 0;
    if (Math.hypot(mx, mz) < 0.22) { mx = 0; mz = 0; }
    if (b(14)) mx = -1; if (b(15)) mx = 1; if (b(12)) mz = -1; if (b(13)) mz = 1;
    // A = push, B = grab, X / RB = dash-brace (matches the design brief layout)
    return { mx, mz, push: b(0), grab: b(1), dash: b(2) || b(5), skill: b(3), start: b(9) };
  }
  S.readPad = readPad;

  class KeySource {
    constructor(map, pad) { this.map = map; this.pad = pad; }
    sample() {
      const k = S.kb, m = this.map;
      let mx = (k.has(m.right) ? 1 : 0) - (k.has(m.left) ? 1 : 0);
      let mz = (k.has(m.down) ? 1 : 0) - (k.has(m.up) ? 1 : 0);
      let push = k.has(m.push), grab = k.has(m.grab), dash = k.has(m.dash), skill = m.skill ? k.has(m.skill) : false;
      // WASD alone (face-off taunts) and arrows alone (extra taunts) when one player uses both
      const wd = m.taunts ? { mx: (k.has(['KeyD']) ? 1 : 0) - (k.has(['KeyA']) ? 1 : 0), mz: (k.has(['KeyS']) ? 1 : 0) - (k.has(['KeyW']) ? 1 : 0) } : null;
      const ar = m.taunts ? { up: k.has(['ArrowUp']), down: k.has(['ArrowDown']), left: k.has(['ArrowLeft']), right: k.has(['ArrowRight']) } : null;
      const p = readPad(this.pad);
      if (p) {
        if (p.mx || p.mz) { mx = p.mx; mz = p.mz; if (wd) { wd.mx = p.mx; wd.mz = p.mz; } }
        push = push || p.push; grab = grab || p.grab; dash = dash || p.dash; skill = skill || p.skill;
      }
      const T = S.touch; // phone / tablet controls feed player 1
      if (T && T.on && this.pad === 0) {
        if (T.mx || T.mz) { mx = T.mx; mz = T.mz; if (wd) { wd.mx = Math.abs(T.mx) > 0.5 ? Math.sign(T.mx) : 0; wd.mz = Math.abs(T.mz) > 0.5 ? Math.sign(T.mz) : 0; } }
        push = push || T.push; grab = grab || T.grab; dash = dash || T.dash; skill = skill || T.skill;
      }
      const l = Math.hypot(mx, mz);
      if (l > 1) { mx /= l; mz /= l; }
      return { mx, mz, push, grab, dash, skill, wd, ar };
    }
  }

  class Btn {
    constructor() { this.held = false; this.pressed = false; this.released = false; this.t = 0; }
    update(v, dt) {
      this.pressed = v && !this.held;
      this.released = !v && this.held;
      this.held = v;
      this.t = v ? (this.pressed ? 0 : this.t + dt) : 0;
    }
  }

  class Controller {
    constructor(src) { this.src = src; this.mx = 0; this.mz = 0; this.push = new Btn(); this.grab = new Btn(); this.dash = new Btn(); this.skill = new Btn(); this.wd = null; this.ar = null; }
    update(dt) {
      const r = this.src.sample();
      this.mx = r.mx; this.mz = r.mz; this.wd = r.wd || null; this.ar = r.ar || null;
      this.push.update(r.push, dt); this.grab.update(r.grab, dt); this.dash.update(r.dash, dt); this.skill.update(!!r.skill, dt);
    }
  }

  S.KeySource = KeySource;
  S.Controller = Controller;
  S.Btn = Btn;
  S.NULL_IN = { mx: 0, mz: 0, push: new Btn(), grab: new Btn(), dash: new Btn(), skill: new Btn() };
})();
