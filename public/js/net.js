'use strict';
// Online play: room connection + lockstep input exchange.
// Both players (and any spectators) run the same deterministic fight from the same inputs.
// Inputs are sent in "net frames" of 4 sim steps (30 per second) with a small delay to hide lag.
(function () {
  const BITS = { push: 1, grab: 2, dash: 4, skill: 8 };

  // compact input: [mx, mz, buttons, wasd-x, wasd-z, arrows]
  function pack(r) {
    let b = 0; for (const k in BITS) if (r[k]) b |= BITS[k];
    const ar = r.ar ? (r.ar.up ? 1 : 0) | (r.ar.right ? 2 : 0) | (r.ar.down ? 4 : 0) | (r.ar.left ? 8 : 0) : 0;
    return [Math.round(r.mx * 100), Math.round(r.mz * 100), b, r.wd ? r.wd.mx : 0, r.wd ? r.wd.mz : 0, ar];
  }
  function unpack(p) {
    if (!p) return { mx: 0, mz: 0, push: false, grab: false, dash: false, skill: false, wd: null, ar: null };
    return {
      mx: p[0] / 100, mz: p[1] / 100, push: !!(p[2] & 1), grab: !!(p[2] & 2), dash: !!(p[2] & 4), skill: !!(p[2] & 8),
      wd: { mx: p[3], mz: p[4] }, ar: { up: !!(p[5] & 1), right: !!(p[5] & 2), down: !!(p[5] & 4), left: !!(p[5] & 8) },
    };
  }
  S.netPack = pack; S.netUnpack = unpack;
  S.NET_KEEP = 5; // unchanged inputs are confirmed every 5 net frames (about 1/6 s)

  // input source for a wrestler driven by the network
  class NetSource {
    constructor(game, slot) { this.g = game; this.slot = slot; }
    sample() { return unpack(this.g.netCur && this.g.netCur[this.slot]); }
  }
  S.NetSource = NetSource;

  class Net {
    constructor(game) {
      this.g = game; this.ws = null; this.room = null; this.id = null; this.code = null;
      this.rtts = []; this.rtt = 0;
      // plain-text ping: the server answers it without waking the room
      setInterval(() => { const now = performance.now(); if (this.open && (!this.pingWait || now - this.pingAt > 3000)) { this.pingAt = now; this.pingWait = true; this.ws.send('ping'); } }, 1000);
    }
    // a safe input delay (in net frames of 33 ms) for this connection: covers the trip plus its wobble
    delayFrames() {
      if (!this.rtts.length) return 4;
      const worst = Math.max(...this.rtts.slice(-8));
      return Math.max(2, Math.min(9, Math.ceil((worst + 15) / 33.3)));
    }
    available() { return location.protocol === 'http:' || location.protocol === 'https:'; }
    // works at the site root or under a subpage like /kumite/
    url() { const u = new URL('ws', location.href); u.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'; u.search = ''; u.hash = ''; return u.toString(); }
    connect(code) {
      this.close();
      this.code = code;
      let ws;
      try { ws = this.ws = new WebSocket(this.url() + '?room=' + encodeURIComponent(code)); }
      catch (e) { this.g.onNetClosed('Could not reach the game server.'); return; }
      const g = this.g;
      ws.onopen = () => this.send({ t: 'hello', name: S.profile.names[0], arch: g.sel.c1 || 0, lo: S.profile.loadout() });
      ws.onmessage = (e) => {
        if (e.data === 'pong') { if (!this.pingWait) return; this.pingWait = false; this.rtts.push(performance.now() - this.pingAt); if (this.rtts.length > 12) this.rtts.shift(); this.rtt = this.rtts[this.rtts.length - 1]; return; }
        let m; try { m = JSON.parse(e.data); } catch (er) { return; } this.onMsg(m);
      };
      ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.room = null; g.onNetClosed('Disconnected from the room.'); } };
      ws.onerror = () => {};
    }
    close() { if (this.ws) { const w = this.ws; this.ws = null; try { w.close(); } catch (e) { /* ignore */ } } this.room = null; }
    get open() { return !!this.ws && this.ws.readyState === 1; }
    send(m) { if (this.open) this.ws.send(JSON.stringify(m)); }
    onMsg(m) {
      const g = this.g;
      switch (m.t) {
        case 'pong': this.rtts.push(performance.now() - m.id); if (this.rtts.length > 12) this.rtts.shift(); this.rtt = this.rtts[this.rtts.length - 1]; break;
        case 'room': this.room = m; this.id = m.you; g.onRoom(m); break;
        case 'start': g.onNetStart(m); break;
        case 'in': g.onNetInput(m); break;
        case 'ir': g.onNetRuns(m); break;
        case 'hash': g.onNetHash(m); break;
        case 'need': g.onNetNeed(m); break;
        case 'snap': g.onNetSnap(m); break;
        case 'abort': g.onNetAbort(m); break;
        case 'full': g.onQuickFull(); break;
      }
    }
  }
  S.Net = Net;

  // ---- state snapshot used to repair the rare desync
  const WF = ['x', 'z', 'vx', 'vz', 'f', 'fw', 'y', 'bal', 'tx', 'tz', 'stam', 'st', 't', 'dur', 'hitDone', 'hand', 'windPow', 'cspd', 'chargeHit',
    'tachiai', 'braceT', 'dashCD', 'ddx', 'ddz', 'dpow', 'sdx', 'sdz', 'fallX', 'fallZ', 'down', 'out', 'slideT', 'pressT', 'ghostT', 'charges',
    'pre', 'preT', 'crouchT', 'tachiPow', 'ignoreDash', 'uprightT', 'parryAt', 'teeter', 'szCur', 'boomT', 'swallowed', 'gulpI', 'sk', 'trail', 'trailT', 'rwTrail', 'gulpT', 'qT', 'hyN', 'hyHits', 'dq', 'carried', 'inShop', 'chkBy', 'ballCD', 'ballHitT', 'ballRoll', 'chkA', 'chkT', 'throatT', 'thrHand', 'throat', 'throatCD', 'flurry', 'lastPalmAt', 'gripCD', 'hariteUsed', 'dashAt', 'lean', 'teeterEnd', 'matta', 'mattaPen'];
  const MF = ['phase', 'phaseT', 'goAt', 'sinceGo', 'time', 'overT', 'round', 'deadT', 'lastContactT', 'stage', 'stageA'];
  S.netSnapshot = (m) => ({
    w: m.w.map((w) => { const o = {}; for (const k of WF) o[k] = w[k]; o.fxs = Object.assign({}, w.fxs); return o; }),
    m: Object.fromEntries(MF.map((k) => [k, m[k]])), wins: m.wins.slice(), hist: (m.history || []).slice(),
    cl: m.clinch ? { a: m.clinch.a.idx, ang: m.clinch.ang, cx: m.clinch.cx, cz: m.clinch.cz, d: m.clinch.d, v: m.clinch.v, vl: m.clinch.vl, w: m.clinch.w,
      grip: m.clinch.grip.slice(), type: m.clinch.type.slice(), t: m.clinch.t } : null,
    res: m.result ? { l: m.result.loser.idx, cause: m.result.cause, km: m.result.km, draw: !!m.result.draw } : null,
  });
  S.netApply = (m, d) => {
    d.w.forEach((o, i) => { const w = m.w[i]; for (const k of WF) w[k] = o[k]; w.fxs = Object.assign({}, o.fxs); });
    for (const k of MF) m[k] = d.m[k];
    m.wins = d.wins.slice(); m.history = (d.hist || []).slice();
    if (m.clinch) { m.clinch.done = true; for (const w of m.w) w.clinch = null; m.clinch = null; }
    if (d.cl) {
      const a = m.w[d.cl.a], b = a.opp;
      const c = new S.Clinch(m, a, b, {});
      Object.assign(c, { ang: d.cl.ang, cx: d.cl.cx, cz: d.cl.cz, d: d.cl.d, dT: d.cl.d, v: d.cl.v, vl: d.cl.vl, w: d.cl.w, grip: d.cl.grip, type: d.cl.type, t: d.cl.t });
      m.clinch = c; for (let i = 0; i < 2; i++) { m.w[i].st = d.w[i].st; m.w[i].t = d.w[i].t; }
    }
    m.result = d.res ? { loser: m.w[d.res.l], winner: m.w[d.res.l].opp, cause: d.res.cause, km: d.res.km, draw: d.res.draw } : null;
    m.events = [];
  };
  // full copy of a fight (keeps object links and classes), used to rewind for rollback
  const SKIP = { input: 1, ctrl: 1, _px: 1, events: 1 };
  S.cloneMatch = (m) => {
    const shared = new Set(S.ARCH), seen = new Map();
    const c = (v) => {
      if (v === null || typeof v !== 'object') return v;
      if (shared.has(v)) return v;
      const hit = seen.get(v); if (hit) return hit;
      if (Array.isArray(v)) { const a = new Array(v.length); seen.set(v, a); for (let i = 0; i < v.length; i++) a[i] = c(v[i]); return a; }
      const o = Object.create(Object.getPrototypeOf(v)); seen.set(v, o);
      for (const k of Object.keys(v)) if (!SKIP[k]) o[k] = c(v[k]);
      return o;
    };
    const out = c(m); out.events = [];
    return out;
  };
  S.netHash = (m) => {
    let h = 0;
    const add = (v) => { h = (Math.imul(h, 31) + (Math.round(v * 1000) | 0)) | 0; };
    for (const w of m.w) { add(w.x); add(w.z); add(w.vx); add(w.vz); add(w.bal); add(w.f); }
    add(m.round); add(m.wins[0]); add(m.wins[1]);
    return h;
  };
})();
