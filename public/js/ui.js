'use strict';
// DOM UI: HUD, banners, result card, callouts, menus, clinch hints, 2D overlay (speed lines, debug).
(function () {
  const $ = (id) => document.getElementById(id);

  class UI {
    constructor(game) {
      this.g = game;
      this.cv = $('fx2d'); this.cx = this.cv.getContext('2d');
      this.lines = null;
      this.screen = $('screen'); this.focus = 0; this.items = [];
      this.hintEl = $('clinchHint');
      this.resize(); addEventListener('resize', () => this.resize());
      this.screen.addEventListener('click', (e) => {
        const b = e.target.closest('[data-i]');
        if (b) { this.focus = +b.dataset.i; this.highlight(); this.activate(); }
      });
      this.screen.addEventListener('mousemove', (e) => {
        const b = e.target.closest('[data-i]');
        if (b && +b.dataset.i !== this.focus) { this.focus = +b.dataset.i; this.highlight(); if (this.name === 'locker') this.g.lockerPreview(); }
      });
    }
    resize() {
      const d = Math.min(2, devicePixelRatio || 1);
      this.cv.width = innerWidth * d; this.cv.height = innerHeight * d;
      this.cx.setTransform(d, 0, 0, d, 0, 0);
    }

    // ------------------------------------------------------------- HUD
    showHud(on) { $('hud').classList.toggle('hidden', !on); }
    setFighters(archs, labels) {
      for (let i = 0; i < 2; i++) {
        $('n' + (i + 1)).innerHTML = archs[i].name + '<span>' + labels[i] + '</span>';
        document.querySelector('.plate.p' + (i + 1)).style.setProperty('--acc', archs[i].accent);
      }
    }
    // one circle per possible round, filled in the winner's colour as rounds are won
    setWins(w, need) {
      const m = this.g.match, hist = (m && m.history) || [], n = need * 2 - 1;
      if (this.g.endless && this.g.endless()) { // non-stop: a running tally instead of round circles
        const g = this.g;
        $('rounds').innerHTML = '<span class="tally">' + w[0] + ' – ' + w[1] + '</span>' + (g.nsStreak > 1 ? '<span class="streak">' + g.nsStreak + ' IN A ROW</span>' : '');
        this.histN = hist.length; return;
      }
      let h = '';
      for (let k = 0; k < n; k++) {
        const wi = hist[k];
        const fresh = k === hist.length - 1 && hist.length > (this.histN || 0);
        h += wi === undefined ? '<i></i>' : '<i class="on' + (fresh ? ' new' : '') + '" style="--c:' + (wi === 2 ? S.ARCH[m.third ? m.third.arch : 0].accent : wi === 1 && m.w[0].a === m.w[1].a ? '#f6eddc' : m.w[wi].a.accent) + '"></i>';
      }
      this.histN = hist.length;
      $('rounds').innerHTML = h;
    }
    setRound(n) { $('roundLbl').textContent = 'ROUND ' + n; }
    setRecord(t) { $('record').textContent = t || ''; }
    setYen() { $('yen').textContent = S.fmtYen(S.profile.yen); }
    // skill slots: holders see their own skill; a CPU's stays secret
    setSkills(skills, secret, keys) {
      for (let i = 0; i < 2; i++) {
        const el = $('sk' + (i + 1)), id = skills[i];
        if (!id) { el.className = 'skslot'; el.innerHTML = ''; continue; }
        const g = this.g.match, sk = S.Skills.BY[id === 'fake' ? g && g.fakeName[i] : id] || { name: '???' };
        el.className = 'skslot on';
        el.innerHTML = secret[i] ? 'SECRET SKILL' : sk.name + '<kbd>' + keys[i] + '</kbd>';
      }
    }
    hideGacha() { const el = $('gacha'); clearTimeout(this.gt); if (el.className.indexOf('show') >= 0) el.className = el.className.replace('show', 'hide'); }
    gacha(side, id, secret, key, hold, cont) {
      const el = $('gacha'), sk = S.Skills.BY[id];
      el.className = ''; void el.offsetWidth;
      el.innerHTML = secret ? '<div class="gcard"><div class="gn">SECRET SKILL</div><div class="gd">The CPU drew something...</div></div>'
        : '<div class="gcard"><div class="gl">NEW SKILL</div><div class="gn">' + sk.name + '</div><div class="gd">' + sk.desc + '</div><div class="gk">Press <kbd>' + key + '</kbd> during a bout to use it</div>' +
          (hold ? '<div class="gc">' + (cont.indexOf('·') >= 0 ? cont : 'Press <kbd>' + cont + '</kbd> to continue') + '</div>' : '') + '</div>';
      el.className = 'show ' + (side ? 'right' : 'left');
      clearTimeout(this.gt);
      if (!hold) this.gt = setTimeout(() => { el.className = 'hide ' + (side ? 'right' : 'left'); }, 2600);
    }
    // PEEK: show what the other player holds, and your new draw
    peek(side, theirs, mine, key, fakeOf) {
      const el = $('gacha'), n = S.Skills.BY[mine];
      const t = theirs === 'fake' ? { name: 'FAKE ' + ((S.Skills.BY[fakeOf] || {}).name || ''), desc: 'A copy that does nothing.' } : theirs ? S.Skills.BY[theirs] : null;
      el.className = ''; void el.offsetWidth;
      el.innerHTML = '<div class="gcard"><div class="gl">THEY HAVE</div><div class="gn">' + (t ? t.name : 'NOTHING') + '</div>' +
        (t ? '<div class="gd">' + t.desc + '</div>' : '') + '<div class="gk">Your new skill: <b>' + n.name + '</b> · <kbd>' + key + '</kbd></div></div>';
      el.className = 'show ' + (side ? 'right' : 'left');
      clearTimeout(this.gt); this.gt = setTimeout(() => { el.className = 'hide ' + (side ? 'right' : 'left'); }, 3200);
    }
    stageRow() {
      const st = S.STAGES.find((s) => s.id === S.profile.stage) || S.STAGES[0];
      return '<div class="bet stage" data-stage="1"><span>STAGE</span><i>‹ ' + st.name + ' ›</i><b>Q / E to change</b></div>';
    }
    betRow() {
      const P = S.profile, b = P.betNow(), odds = S.BET_ODDS[this.g.settings.difficulty] || 1;
      return '<div class="bet" data-bet="1"><span>BET</span><i>' + (b ? (b === P.yen ? 'ALL IN ' : '') + S.fmtYen(b) : 'NO BET') + '</i>' +
        '<em>' + (b ? 'Win +' + S.fmtYen(b * odds) + ' · Lose −' + S.fmtYen(b) : 'Bet yen on yourself. ' + this.g.settings.difficulty.toUpperCase() + ' CPU pays ' + odds + ' to 1.') + '</em><b>↑ ↓ to change</b></div>';
    }
    // rewind: an old VCR on fast-reverse
    // thousand hands: a running hit counter
    combo(text, big) {
      const el = $('combo'); clearTimeout(this.cbT);
      if (!text) { el.className = ''; return; }
      el.textContent = text; el.className = 'on' + (big ? ' big' : '');
      this.cbT = setTimeout(() => { el.className = ''; }, big ? 2200 : 900);
    }
    vhs(on) { $('vhs').classList.toggle('on', !!on); }
    training(html) { const el = $('trainPanel'); if (!html) { el.classList.remove('on'); return; } el.innerHTML = html; el.classList.add('on'); }
    blind(on, txt) { $('blindOv').classList.toggle('on', !!on); const t = $('blindTxt'); if (t.classList.contains('on') !== !!txt) t.classList.toggle('on', !!txt); }
    hint(t) { $('hint').innerHTML = t || ''; }

    banner(text, cls, dur) {
      const b = $('banner');
      b.className = ''; void b.offsetWidth;
      b.querySelector('.jp').textContent = text;
      if (this.g.tut) cls = (cls || '') + ' low';
      b.className = 'show ' + (cls || '');
      clearTimeout(this.bt);
      if (dur) this.bt = setTimeout(() => { b.className = 'hide ' + (cls || ''); }, dur * 1000);
    }
    hideBanner() { $('banner').className = 'hide'; }

    kimarite(key, winnerArch, side, label) {
      const k = S.KIMARITE[key] || S.KIMARITE.oshidashi;
      const el = $('kimarite');
      el.querySelector('.kj').textContent = k[1];
      el.querySelector('.ro').textContent = k[2];
      el.querySelector('.who').innerHTML = '<b style="color:' + winnerArch.accent + '">' + (label || winnerArch.name + ' WINS') + '</b>';
      el.className = ''; void el.offsetWidth; el.className = 'show ' + (side ? 'right' : 'left');
    }
    hideKimarite() { $('kimarite').className = 'hide'; }

    callout(text, x, y, cls) {
      const d = document.createElement('div');
      d.className = 'callout ' + (cls || '');
      d.textContent = text;
      d.style.left = x + 'px'; d.style.top = y + 'px';
      $('callouts').appendChild(d);
      setTimeout(() => d.remove(), 1100);
    }

    // in-clinch hint next to a human wrestler
    clinchHint(show, x, y, html) {
      const el = this.hintEl;
      if (!show) { el.classList.remove('on'); return; }
      if (html !== this.hintHtml) { this.hintHtml = html; el.innerHTML = html; }
      el.style.left = x + 'px'; el.style.top = y + 'px';
      el.classList.add('on');
    }

    // ------------------------------------------------------------- 2D FX
    speedLines(x, y, power, dur, dark) { if (this.g.kind === 'attract') return; this.lines = { x, y, p: power, t: 0, dur: dur || 0.22, dark: !!dark }; }
    impactFrame(ms) {
      if (this.g.kind === 'attract') return;
      const gl = $('gl');
      gl.classList.add('impact');
      clearTimeout(this.it);
      this.it = setTimeout(() => gl.classList.remove('impact'), ms || 70);
    }
    flash(color, dur) {
      if (this.g.kind === 'attract') return;
      const f = $('flash');
      f.style.transition = 'none'; f.style.background = color || '#fff'; f.style.opacity = 0.7;
      void f.offsetWidth;
      f.style.transition = 'opacity ' + (dur || 0.25) + 's ease-out'; f.style.opacity = 0;
    }

    draw(dt) {
      const c = this.cx, W = innerWidth, H = innerHeight;
      const mm = this.g.match;
      if (mm) for (let i = 0; i < 2; i++) {
        const el = this.stEl || (this.stEl = [$('st1'), $('st2')]), v = Math.max(0, Math.min(1, mm.w[i].stam));
        if (el[i]) { el[i].firstChild.style.width = Math.round(v * 100) + '%'; el[i].classList.toggle('low', v < 0.25); }
      }
      c.clearRect(0, 0, W, H);
      const L = this.lines;
      if (L) {
        L.t += dt;
        if (L.t > L.dur) this.lines = null;
        else {
          const k = 1 - L.t / L.dur;
          const n = 90, R0 = Math.max(W, H);
          const inner = Math.min(W, H) * (0.16 + 0.12 * (1 - k)) / Math.min(1.4, L.p);
          c.fillStyle = L.dark ? 'rgba(15,6,10,' + (0.85 * k) + ')' : 'rgba(255,250,240,' + (0.75 * k) + ')';
          for (let i = 0; i < n; i++) {
            const a = Math.random() * Math.PI * 2, w2 = 0.004 + Math.random() * 0.012;
            const r1 = inner * (1 + Math.random() * 0.9);
            c.beginPath();
            c.moveTo(L.x + Math.cos(a) * r1, L.y + Math.sin(a) * r1);
            c.lineTo(L.x + Math.cos(a - w2) * R0, L.y + Math.sin(a - w2) * R0);
            c.lineTo(L.x + Math.cos(a + w2) * R0, L.y + Math.sin(a + w2) * R0);
            c.fill();
          }
        }
      }
      if (this.g.settings.debug && this.g.match) this.drawDebug(c);
    }

    drawDebug(c) {
      const g = this.g, m = g.match, Rn = g.R;
      const arrow = (x, z, dx, dz, col, y) => {
        const a = Rn.project(x, y || 0.05, z), b = Rn.project(x + dx, y || 0.05, z + dz);
        c.strokeStyle = col; c.fillStyle = col; c.lineWidth = 2.5; c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y); c.stroke();
        const an = Math.atan2(b.y - a.y, b.x - a.x);
        c.beginPath(); c.moveTo(b.x, b.y); c.lineTo(b.x - Math.cos(an - 0.4) * 9, b.y - Math.sin(an - 0.4) * 9); c.lineTo(b.x - Math.cos(an + 0.4) * 9, b.y - Math.sin(an + 0.4) * 9); c.fill();
      };
      const lines = [];
      for (const w of m.w) {
        arrow(w.x, w.z, w.vx * 0.35, w.vz * 0.35, '#4cf');
        arrow(w.x, w.z, w.fx * 1.0, w.fz * 1.0, '#fd4', 0.1);
        arrow(w.x, w.z, w.tx * 1.5, w.tz * 1.5, '#f55', 0.15);
        const p = Rn.project(w.x, 2.6 * w.a.scale, w.z);
        c.fillStyle = 'rgba(0,0,0,0.6)'; c.fillRect(p.x - 40, p.y - 22, 80, 16);
        c.fillStyle = w.bal > 0.5 ? '#6f6' : w.bal > 0.25 ? '#fc4' : '#f44'; c.fillRect(p.x - 38, p.y - 20, 76 * Math.max(0, w.bal), 6);
        c.fillStyle = '#7cf'; c.fillRect(p.x - 38, p.y - 12, 76 * w.stam, 4);
        const ai = g.ais.find((a) => a.me === w);
        let grip = '';
        if (w.clinch) { const cl = w.clinch; grip = ' grip ' + cl.grip[w.idx].toFixed(2) + ' (' + cl.type[w.idx] + ')' + (cl.rear === w ? ' REAR' : ''); }
        lines.push('<b style="color:' + w.a.accent + '">' + w.a.name + '</b> ' + w.st + ' ' + w.t.toFixed(2) +
          ' | bal ' + w.bal.toFixed(2) + ' stam ' + w.stam.toFixed(2) + ' | v ' + w.spd.toFixed(2) + ' | p ' + (w.spd * w.m).toFixed(2) +
          ' | m ' + w.m + grip + (w.lastTech ? ' | tag ' + w.lastTech : '') + (ai ? ' | AI: ' + ai.state : ''));
      }
      if (m.clinch) {
        const cl = m.clinch;
        lines.push('CLINCH v ' + cl.v.toFixed(2) + ' w ' + cl.w.toFixed(2) + ' t ' + cl.t.toFixed(1) + (cl.tech ? ' TECH ' + cl.tech.kind + (cl.tech.ok ? ' ok' : ' fail') : '') + (cl.lift ? ' LIFT' : ''));
      }
      lines.push('phase ' + m.phase + ' | time ' + m.time.toFixed(1) + ' | deadlock ' + Math.max(0, m.deadT).toFixed(2) + ' | timescale ' + g.ts.toFixed(2));
      $('debug').innerHTML = lines.join('<br>');
    }

    // ------------------------------------------------------------- screens
    // every change of screen goes through the banner wipe (except pause and the result card)
    show(name, data) {
      const bn = S.Banners;
      const wipe = bn && name !== this.name && name !== 'result' && name !== 'pause' && this.name !== 'pause';
      if (wipe) {
        if (this.pending) { this.pending = { name, data }; return; }
        if (!bn.busy) {
          this.pending = { name, data };
          bn.flood({ hold: 0.06, speed: 1.6, onCovered: () => { const p = this.pending; this.pending = null; if (p) this.showNow(p.name, p.data); } });
          return;
        }
      }
      this.showNow(name, data);
    }
    showNow(name, data) {
      this.name = name; this.data = data || {}; this.focus = 0;
      this.render();
      const yen = $('yen'); this.setYen();
      yen.style.display = ['title', 'select', 'result', 'tutdone'].includes(name) ? 'block' : 'none';
    }
    hide() { this.pending = null; this.name = null; this.screen.className = ''; this.screen.innerHTML = ''; $('yen').style.display = 'none'; }

    render() {
      const g = this.g, n = this.name, d = this.data, st = g.settings;
      if (!n) { this.hide(); return; }
      let h = '';
      this.items = [];
      const btn = (label, act, value, tag) => {
        const i = this.items.length; this.items.push(act);
        return '<button data-i="' + i + '" class="' + (i === this.focus ? 'on' : '') + (value ? ' opt' : '') + '">' + label +
          (value ? '<em>‹ ' + value + ' ›</em>' : '') + (tag ? '<i class="tagsoon">' + tag + '</i>' : '') + '</button>';
      };
      const P = S.profile;
      const foot = (t) => '<div class="foot">' + t + '</div>';
      if (n === 'title') {
        h = '<div class="title-wrap"><img class="logo-img" src="assets/logo.webp?v=2" alt="Kumite"><div class="menu">' +
          btn('PLAY', 'play') + btn('MULTIPLAYER', 'online') + btn('SETTINGS', 'settings') + (S.APP === 'desktop' ? btn('QUIT', 'quit') : '') +
          '</div></div>';
      } else if (n === 'play') {
        const phs = () => { const P = S.phones, k = P.slots.filter(Boolean).length; return P.on ? (k ? k + ' CONNECTED' : 'ON') : 'OFF'; };
        this.phs = phs;
        h = '<div class="pause-wrap"><div class="ptitle">PLAY</div><div class="menu">' +
          btn('PLAY VS CPU', 'cpu') + btn('LEARN TO PLAY', 'learn') + btn('TRAINING', 'training') + btn('LOCKER', 'locker') + btn('PHONE CONTROLLERS', 'phones', phs()) + btn('BACK', 'back') +
          '</div>' + foot('Esc back') + '</div>';
      } else if (n === 'binds') {
        h = '<div class="pause-wrap"><div class="ptitle">KEY BINDINGS</div><div class="menu">';
        for (const [a, label] of S.BIND_ACTIONS) h += btn(label, 'bind:' + a, d && d.waiting === a ? 'PRESS A KEY…' : S.keyName(S.mainKey(a)));
        h += btn('RESET TO DEFAULT', 'bindReset') + btn('BACK', 'back') + '</div>' + foot('Enter, then press the new key &nbsp;·&nbsp; Esc cancels') + '</div>';
      } else if (n === 'settings') {
        h = '<div class="pause-wrap"><div class="ptitle">SETTINGS</div><div class="menu">' +
          btn('CPU DIFFICULTY', 'diff', st.difficulty.toUpperCase()) +
          btn('VS CPU MATCH', 'endless', st.endless ? 'NON-STOP' : 'BEST OF 3') +
          btn('STAGE', 'pstage', (S.STAGES.find((x) => x.id === S.profile.stage) || S.STAGES[0]).name) +
          btn('COUNTER TIPS', 'hints', st.hints ? 'ON' : 'OFF') +
          btn('SOUND', 'sound', st.sound ? 'ON' : 'OFF') +
          (S.APP === 'desktop' ? btn('DISPLAY', 'fullscreen', window.kumiteDesktop && window.kumiteDesktop.isFullScreen() ? 'FULLSCREEN' : 'WINDOWED') : '') +
          btn('DEBUG VIEW', 'debug', st.debug ? 'ON' : 'OFF') + btn('CONTROLS', 'controls') + btn('PHONE CONTROLLERS', 'phones', (S.phones.on ? (S.phones.slots.filter(Boolean).length + ' CONNECTED') : 'OFF')) +
          btn('YOUR NAME', 'name1', P.names[0]) +
          btn('BACK', 'back') + '</div>' + foot('← → change &nbsp;·&nbsp; Enter on a name to type it &nbsp;·&nbsp; Esc back') + '</div>';
      } else if (n === 'select') {
        const gacha = P.rules === 'gacha';
        h = '<div class="sel-wrap"><div class="sel-title">CHOOSE YOUR WRESTLER</div>' +
          '<div class="rules" data-rules="1"><span class="' + (gacha ? '' : 'on') + '">PURE</span><span class="' + (gacha ? 'on' : '') + '">GACHA</span>' +
          '<em>' + (gacha ? 'Both players draw a random one-shot skill every round. Use it with Space.' : 'Just sumo. No skills, no tricks.') + '</em><b>Tab to switch</b></div>' + (d.mode === 'cpu' ? this.betRow() : '') + this.stageRow() + '<div class="cards">';
        S.ARCH.forEach((a, i) => {
          const tags = [];
          if (d.c1 === i) tags.push('<i class="t1">' + (d.lock1 ? 'P1 ✓' : 'P1') + '</i>');
          if (d.mode === 'pvp' && d.c2 === i) tags.push('<i class="t2">' + (d.lock2 ? 'P2 ✓' : 'P2') + '</i>');
          h += '<div class="card ' + (d.c1 === i ? 'on1 ' : '') + (d.mode === 'pvp' && d.c2 === i ? 'on2' : '') + '" data-card="' + i + '" style="--acc:' + a.accent + '">' +
            '<div class="tags">' + tags.join('') + '</div><div class="ct">' + a.title + '</div><div class="cn">' + a.name + '</div>' +
            '<div class="cb">' + a.blurb + '</div><div class="tr">' + a.traits.join('<br>') + '</div></div>';
        });
        h += '</div>' + foot(d.mode === 'pvp' ? 'P1: A D + Space &nbsp;·&nbsp; P2: ← → + Enter &nbsp;·&nbsp; Esc back' : 'Esc back') + '</div>';
      } else if (n === 'tutorial' || n === 'controls') {
        const pv = d.mode === 'pvp';
        const k = (a, b) => pv ? '<kbd>' + a + '</kbd><em>P2</em><kbd>' + b + '</kbd>' : '<kbd>' + a + '</kbd>';
        h = '<div class="tut-wrap"><div class="tut-cards">' +
          '<div class="tc"><div class="tk">' + k('W A S D', '← ↑ ↓ →') + '</div><div class="tl">MOVE</div></div>' +
          '<div class="tc"><div class="tk">' + k('J', '1') + '</div><div class="tl">PUSH</div></div>' +
          '<div class="tc"><div class="tk">' + k('K', '2') + '</div><div class="tl">GRAB</div></div>' +
          '<div class="tc"><div class="tk">' + k('L', '3') + '</div><div class="tl">DASH / BRACE</div></div>' +
          '</div><div class="tut-sub">Push them out of the ring, or make them touch the clay.' +
          (n === 'tutorial' ? '<br><span>New here? Choose PLAY → LEARN TO PLAY.</span>' : '') +
          (n === 'controls' ? '<br><span>Locked together: K up = stick pushes / drags · hold K a moment + aim, let go = side throw, away spin, toward trip, no aim lift<br>Before the start: J clap · K stomp · W salt · A arms · S face slap · D belt slap · hold L crouch<br>Gamepad: A push · B grab · X dash · Y skill &nbsp;·&nbsp; Space: gacha skill &nbsp;·&nbsp; Esc pause</span>' : '') +
          '</div><div class="menu">' + (n === 'controls' ? btn('KEY BINDINGS', 'binds') + btn('MOVE LIST', 'moves') : '') + btn(n === 'tutorial' ? 'START' : 'BACK', n === 'tutorial' ? 'begin' : 'back') + '</div></div>';
      } else if (n === 'pause') {
        h = '<div class="pause-wrap"><div class="ptitle">PAUSED</div><div class="menu">' +
          btn('RESUME', 'resume') + (g.kind === 'training' ? btn('STAGE', 'pstage', (S.STAGES.find((x) => x.id === S.profile.stage) || S.STAGES[0]).name) : '') + btn(d.tut ? 'RESTART TUTORIAL' : 'RESTART MATCH', 'restart') + btn('PHONE CONTROLLERS', 'phones', (S.phones.on ? (S.phones.slots.filter(Boolean).length + ' CONNECTED') : 'OFF')) + btn('SETTINGS', 'settings') + btn('QUIT TO TITLE', 'quit') + '</div></div>';
      } else if (n === 'trainsel') {
        h = '<div class="sel-wrap"><div class="sel-title">TRAINING · PICK YOUR WRESTLER</div>' + this.stageRow() + '<div class="cards">';
        S.ARCH.forEach((a, i) => {
          h += '<div class="card ' + (d.c1 === i ? 'on1' : '') + '" data-card="' + i + '" style="--acc:' + a.accent + '"><div class="tags">' + (d.c1 === i ? '<i class="t1">YOU</i>' : '') + '</div><div class="ct">' + a.title + '</div><div class="cn">' + a.name + '</div><div class="cb">' + a.blurb + '</div><div class="tr">' + a.traits.join('<br>') + '</div></div>';
        });
        h += '</div>' + foot('Enter to start &nbsp;·&nbsp; Esc back') + '</div>';
      } else if (n === 'moves') {
        const L = S.profile.landed, got = S.HOWTO.filter((r) => L[r[0]]).length;
        h = '<div class="moves-wrap"><div class="ptitle">MOVE LIST</div><div class="mv-sub">Win with a move to tick it off · ' + got + ' / ' + S.HOWTO.length + ' landed</div><div class="mv-grid">';
        for (const [k, how] of S.HOWTO) {
          const km = S.KIMARITE[k], n2 = L[k] || 0;
          h += '<div class="mv ' + (n2 ? 'got' : '') + '"><div class="mvn">' + (n2 ? '✓ ' : '') + km[1] + '<span>' + km[2] + '</span></div><div class="mvh">' + how + (n2 ? ' <b>×' + n2 + '</b>' : '') + '</div></div>';
        }
        h += '</div><div class="menu">' + btn('BACK', 'back') + '</div></div>';
      } else if (n === 'online') {
        h = '<div class="pause-wrap"><div class="ptitle">MULTIPLAYER</div><div class="soonbox"><div>Quick Match finds an opponent at your level.</div>Or create a room and share its code: two fight, everyone else watches, winner stays on. Phone controllers let two people play on this screen with their phones.</div>' +
          (d.err ? '<div class="neterr">' + d.err + '</div>' : '') +
          '<div class="menu">' + btn('QUICK MATCH', 'quickMatch') + btn('CREATE ROOM', 'createRoom') + btn('JOIN ROOM', 'joinRoom') + btn('PHONE CONTROLLERS', 'phones') + btn('BACK', 'back') + '</div>' + foot('Online uses Pure rules · Esc back') + '</div>';
      } else if (n === 'phones') {
        const P = S.phones, row = (i) => '<div class="ph-row"><b>PLAYER ' + (i + 1) + '</b><span class="' + (P.connected(i) ? 'ok' : '') + '">' + (P.connected(i) ? 'PHONE CONNECTED' : 'waiting for a phone…') + '</span></div>';
        h = '<div class="pause-wrap"><div class="ptitle">PHONE CONTROLLERS</div>' +
          (P.err ? '<div class="neterr">' + P.err + '</div>' : '') +
          (P.connecting ? '<div class="lb-wait">Connecting to the game server…</div>' : '') +
          (P.on ? '<div class="ph-box"><div class="ph-qr">' + P.qrSvg() + '</div><div class="ph-info">' +
            '<p>Scan with your phone camera. The first phone is Player 1, the second Player 2.</p>' +
            '<p class="ph-code">or open <span>' + P.padUrl().replace(/^https?:\/\//, '') + '</span></p>' + row(0) + row(1) +
            '<p class="ph-small">Phones work in the menus too: J is OK, K is back, ❚❚ pauses. PS5 and Xbox controllers work as well: just connect them to this computer.</p></div></div>' : '') +
          '<div class="menu">' + (P.on ? (g.phonesBack && g.phonesBack !== 'online' && g.phonesBack !== 'title' ? btn('DONE', 'back') : btn('PLAY', 'play')) + btn('DISCONNECT PHONES', 'phonesOff') : P.connecting ? '' : btn('TRY AGAIN', 'phonesOn')) + btn('BACK', 'back') + '</div>' + foot('Pick PLAY, then Versus for two phones, or vs CPU for one · Esc back') + '</div>';
      } else if (n === 'lobby') {
        const r = d.room, me = r ? r.you : null;
        if (d.searching) { // Quick Match queue
          const s = d.me;
          h = '<div class="lobby"><div class="lb-code"><span>ONLINE</span>QUICK MATCH</div>' +
            '<div class="lb-wait">Looking for an opponent at your level…</div>' +
            (s ? '<div class="lb-q">Rating <b>' + s.r + '</b> · ' + s.w + ' wins · ' + s.l + ' losses · ' + s.g + ' games' + (s.g < 10 ? ' · still placing you (first 10 games)' : '') + '</div>' : '') +
            '<div class="lb-q">If nobody close to your rating is around, the search widens. After 30 seconds you face whoever is waiting.</div>' +
            '<div class="menu">' + btn('LEAVE', 'leaveRoom') + '</div></div>';
          this.screen.className = 'show ' + n; this.screen.innerHTML = h; return;
        }
        h = '<div class="lobby">' + (/^QM[A-Z0-9]+$/.test(d.code || '') ? '<div class="lb-code"><span>ONLINE</span>QUICK MATCH</div>' : '<div class="lb-code"><span>ROOM CODE</span>' + (d.code || '…') + '</div>');
        if (!r) h += '<div class="lb-wait">Connecting…</div>';
        else {
          const nm = (x) => x ? x.name + (x.id === me ? ' (YOU)' : '') + (x.id === r.host ? ' ★' : '') : '<em>waiting…</em>';
          const ar = (x) => x ? '<b style="color:' + S.ARCH[x.arch].accent + '">' + S.ARCH[x.arch].name + '</b>' : '';
          h += '<div class="lb-ring"><div class="lb-p">' + nm(r.order[0]) + ar(r.order[0]) + '</div><div class="lb-vs">VS</div><div class="lb-p">' + nm(r.order[1]) + ar(r.order[1]) + '</div></div>';
          const q = r.order.slice(2);
          h += '<div class="lb-q">' + (q.length ? 'NEXT UP: ' + q.map((x) => x.name + (x.id === me ? ' (YOU)' : '')).join(' → ') : (r.auto ? 'One on one. Rematches start by themselves.' : 'Share the code: more people can join and watch.')) + '</div>';
          const mine = r.order.find((x) => x.id === me);
          if (mine) h += '<div class="lb-pick">Your wrestler: <b>‹ ' + S.ARCH[mine.arch].name + ' ›</b></div>';
          const host = me === r.host;
          h += '<div class="lb-wait">' + (r.playing ? 'A bout is on: you will watch it start…' : r.order.length < 2 ? (r.auto ? 'Looking for an opponent… the next person to press Quick Match is matched with you.' : 'Waiting for a second player to join…') : r.auto ? 'Next bout starts in a few seconds…' : host ? 'Press <kbd>Enter</kbd> to start the bout' : 'Waiting for the host to start') + '</div>';
          h += '<div class="menu">' + (!r.auto && host && !r.playing && r.order.length >= 2 ? btn('START BOUT', 'startBout') : '') + btn('LEAVE', 'leaveRoom') + '</div>';
        }
        h += foot('← → change wrestler · Esc leave') + '</div>';
      } else if (n === 'soon') {
        h = '<div class="pause-wrap soon"><div class="ptitle">' + d.title + '</div><div class="soonbox">' + d.lines.map((l) => '<div>' + l + '</div>').join('') +
          '</div><div class="menu">' + btn('BACK', 'back') + '</div></div>';
      } else if (n === 'locker') {
        const cat = S.CAT[d.cat], eq = P.eq;
        h = '<div class="locker"><div class="lk-head">LOCKER <span class="wallet">' + S.fmtYen(P.yen) + '</span></div><div class="lk-tabs">';
        S.CAT.forEach((c, i) => { h += '<span data-cat="' + i + '" class="' + (i === d.cat ? 'on' : '') + '">' + c.label + '</span>'; });
        h += '</div>' + (cat.note ? '<div class="lk-note">' + cat.note + '</div>' : '');
        if (cat.key === 'taunt') {
          const arrows = ['↑', '→', '↓', '←'];
          h += '<div class="lk-slots">' + eq.taunts.map((id, k) => '<span>' + arrows[k] + ' ' + (id ? S.item(id).name : '—') + '</span>').join('') + '</div>';
        }
        h += '<div class="menu lk-list">';
        for (const it of cat.items) {
          const own = P.has(it.id);
          const on = cat.key === 'taunt' ? eq.taunts.includes(it.id) : eq[cat.key] === it.id;
          const tag = on ? 'EQUIPPED' : own ? 'OWNED' : S.fmtYen(it.price) + ' · ' + it.wins + ' WINS';
          const i = this.items.length; this.items.push('item:' + it.id);
          const sw = it.c1 ? '<i class="sw" style="background:' + it.c1 + ';border-color:' + it.c2 + '"></i>' : '';
          h += '<button data-i="' + i + '" class="lk-item ' + (i === this.focus ? 'on ' : '') + (on ? 'eq ' : '') + (!own && P.yen < it.price ? 'poor' : '') + '">' + sw + it.name + '<em>' + tag + '</em></button>';
        }
        h += '</div>' + foot('← → category &nbsp;·&nbsp; Enter buy / equip &nbsp;·&nbsp; Esc back') + '</div>';
      } else if (n === 'tutdone') {
        h = '<div class="res-wrap" style="--acc:#f0c35a"><div class="rk">DONE!</div><div class="rn">YOU KNOW THE BASICS</div>' +
          '<div class="rs small">There is more to find in the ring: trips, lifts, last-second turnarounds on the edge.</div>' +
          '<div class="menu">' + btn('PLAY VS CPU', 'cpu') + btn('TITLE', 'quit') + '</div></div>';
      } else if (n === 'result') {
        const a = d.arch;
        h = '<div class="res-wrap" style="--acc:' + a.accent + '"><div class="rk">' + d.head + '</div><div class="rn">' + d.who + '</div><div class="rs">' + d.score + '</div>' +
          '<div class="rec">' + d.record + '</div>' + (d.yen ? '<div class="yenwin">+' + S.fmtYen(d.yen) + '</div>' : '') + (d.lost ? '<div class="yenwin lost">−' + S.fmtYen(d.lost) + ' bet lost</div>' : '') +
          (d.streak !== null && d.streak !== undefined ? '<div class="streak">' + (d.streak > 0 ? 'WIN STREAK ' + d.streak : 'STREAK BROKEN') + '<span>BEST ' + d.best + '</span></div>' : '') +
          (d.online ? '<div class="lb-wait">Back to the lobby in a moment…</div></div>' : '<div class="menu">' + btn('REMATCH <span id="rmc"></span>', 'rematch') + btn('CHANGE WRESTLERS', 'select') + btn('TITLE', 'quit') + '</div></div>');
      }
      this.screen.className = 'show ' + n;
      this.screen.innerHTML = h;
    }
    highlight() {
      this.screen.querySelectorAll('[data-i]').forEach((b) => b.classList.toggle('on', +b.dataset.i === this.focus));
    }
    nav(dir) {
      if (!this.items.length) return;
      this.focus = (this.focus + dir + this.items.length) % this.items.length;
      this.highlight(); this.g.audio.blip(false);
      if (this.name === 'locker') this.g.lockerPreview();
    }
    current() { return this.items[this.focus]; }
    activate(dir) {
      const act = this.items[this.focus];
      if (act) { this.g.audio.blip(true); this.g.menuAction(act, dir || 1); }
    }
  }
  S.UI = UI;
})();
