'use strict';
// Phones as controllers. The game opens a small relay room (code PDxxxx) on the game server and shows a
// QR code; each phone that scans it opens pad.html, joins the room and sends its stick and buttons.
// First phone = Player 1, second = Player 2. A phone counts as that player's gamepad (see readPad in
// input.js), so it works in fights and menus with no other changes.
(function () {
  const FRESH = 1500; // ms: a phone that has gone quiet this long stops counting as held buttons

  class Phones {
    constructor() { this.ws = null; this.code = null; this.slots = [null, null]; this.conns = [null, null]; this.state = [null, null]; this.err = ''; this.onChange = null; }

    get on() { return !!this.ws && this.opened; }
    get connecting() { return !!this.ws && !this.opened; }
    start(again) {
      if (this.ws) return;
      // the same code every time on this computer, so a phone's home-screen icon reconnects without scanning again
      if (!this.code) {
        try { this.code = localStorage.getItem('kumitePhoneCode'); } catch (e) { /* storage blocked */ }
        if (!/^PD[A-Z0-9]{6}$/.test(this.code || '')) {
          this.code = 'PD' + Math.random().toString(36).slice(2, 8).toUpperCase().padEnd(6, 'X');
          try { localStorage.setItem('kumitePhoneCode', this.code); } catch (e) { /* storage blocked */ }
        }
      }
      if (!again) { this.slots = [null, null]; this.conns = [null, null]; this.state = [null, null]; }
      this.err = ''; this.opened = false;
      const u = S.wsUrl('ws'); u.search = '?room=' + this.code;
      let ws; try { ws = this.ws = new WebSocket(u.toString()); } catch (e) { this.ws = null; this.err = 'Could not reach the game server.'; this.changed(); return; }
      ws.onopen = () => { this.opened = true; this.tries = 0; this.changed(); };
      ws.onmessage = (e) => { if (e.data === 'pong') return; let m; try { m = JSON.parse(e.data); } catch (er) { return; } this.onMsg(m); };
      ws.onclose = () => {
        if (this.ws !== ws) return;
        this.ws = null;
        if (!this.opened && !again) { // never connected: this copy of the game has no server (for example the preview link)
          this.code = null; this.slots = [null, null]; this.conns = [null, null]; this.state = [null, null];
          this.err = 'Phone controllers need the online version of the game, at looktwicestudio.com/kumite. This copy cannot connect phones.';
          this.changed(); return;
        }
        // dropped after working: reconnect with the same code; the phones keep their seats
        this.tries = (this.tries || 0) + 1;
        if (this.tries > 10) { this.code = null; this.slots = [null, null]; this.conns = [null, null]; this.state = [null, null]; this.err = 'Lost the connection to the game server.'; this.changed(); return; }
        this.err = 'Reconnecting…'; this.changed();
        clearTimeout(this.retryT); this.retryT = setTimeout(() => this.start(true), 1500);
      };
      ws.onerror = () => {};
      clearInterval(this.keep); this.keep = setInterval(() => { if (this.ws && this.ws.readyState === 1) this.ws.send('ping'); }, 20000);
      this.changed();
    }
    stop() {
      clearInterval(this.keep); clearTimeout(this.retryT); this.tries = 0;
      if (this.ws) { const w = this.ws; this.ws = null; try { w.close(); } catch (e) { /* ignore */ } }
      this.slots = [null, null]; this.conns = [null, null]; this.state = [null, null]; this.code = null; this.changed();
    }
    send(m) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(m)); }
    // Each phone sends a key it keeps for the life of its tab, so a phone that reconnects (screen lock, Wi-Fi
    // blip, the camera app handing over to Safari) gets its old seat back instead of taking the other one.
    onMsg(m) {
      if (m.t === 'hi') this.assign(m.from, m.pk || m.from);
      else if (m.t === 'pleave') {
        const i = this.conns.indexOf(m.id); if (i < 0) return;
        this.slots[i] = null; this.conns[i] = null; this.state[i] = null;
        if (!this.slots[0] && this.slots[1]) { // only phone left is Player 2: make it Player 1
          this.slots = [this.slots[1], null]; this.conns = [this.conns[1], null]; this.state = [this.state[1], null];
          this.send({ t: 'slot', to: this.conns[0], slot: 0 });
        }
        this.changed();
      } else if (m.t === 'st') {
        const i = this.conns.indexOf(m.from);
        if (i < 0) { if (m.pk) this.assign(m.from, m.pk); return; } // a phone we lost track of (after a reconnect)
        const b = m.b || [];
        this.state[i] = { mx: +m.mx || 0, mz: +m.mz || 0, push: !!b[0], grab: !!b[1], dash: !!b[2], skill: !!b[3], start: !!b[4], at: performance.now() };
      }
    }
    assign(id, pk) {
      if (!id) return;
      let slot = this.slots.indexOf(pk);          // the same phone coming back
      if (slot < 0) slot = this.slots.indexOf(null);
      // both taken: a seat whose phone has gone quiet (a closed tab, a phone that went to sleep) can be taken over
      if (slot < 0) slot = [0, 1].find((k) => !this.slots[k] || !this.state[k] || performance.now() - this.state[k].at > 3000) ?? -1;
      if (slot < 0) { this.send({ t: 'slot', to: id, slot: -1 }); return; } // both seats taken
      this.slots[slot] = pk; this.conns[slot] = id;
      this.state[slot] = { mx: 0, mz: 0, push: false, grab: false, dash: false, skill: false, start: false, at: performance.now() }; // counts as live from now
      this.send({ t: 'slot', to: id, slot });
      this.changed();
    }
    // the phone for player i, if it is connected and talking
    get(i) { const s = this.state[i]; return s && performance.now() - s.at < FRESH ? s : null; }
    connected(i) { return !!this.slots[i]; }
    padUrl() { return S.webUrl('pad.html?c=' + this.code); } // phones always open the controller on the website
    qrSvg() {
      if (!this.code || typeof qrcode !== 'function') return '';
      const q = qrcode(0, 'M'); q.addData(this.padUrl()); q.make();
      return q.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
    }
    changed() { if (this.onChange) this.onChange(); }
  }
  S.phones = new Phones();
})();
