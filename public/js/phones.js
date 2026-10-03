'use strict';
// Phones as controllers. The game opens a small relay room (code PDxxxx) on the game server and shows a
// QR code; each phone that scans it opens pad.html, joins the room and sends its stick and buttons.
// First phone = Player 1, second = Player 2. A phone counts as that player's gamepad (see readPad in
// input.js), so it works in fights and menus with no other changes.
(function () {
  const FRESH = 1500; // ms: a phone that has gone quiet this long stops counting as held buttons

  class Phones {
    constructor() { this.ws = null; this.code = null; this.slots = [null, null]; this.state = [null, null]; this.err = ''; this.onChange = null; }

    get on() { return !!this.ws; }
    start() {
      if (this.ws) return;
      if (!(location.protocol === 'http:' || location.protocol === 'https:')) { this.err = 'Phone controllers need the online version of the game.'; this.changed(); return; }
      this.code = 'PD' + Math.random().toString(36).slice(2, 6).toUpperCase().padEnd(4, 'X');
      this.slots = [null, null]; this.state = [null, null]; this.err = '';
      const u = new URL('ws', location.href); u.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'; u.search = '?room=' + this.code; u.hash = '';
      let ws; try { ws = this.ws = new WebSocket(u.toString()); } catch (e) { this.ws = null; this.err = 'Could not reach the game server.'; this.changed(); return; }
      ws.onmessage = (e) => { if (e.data === 'pong') return; let m; try { m = JSON.parse(e.data); } catch (er) { return; } this.onMsg(m); };
      ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.slots = [null, null]; this.state = [null, null]; this.err = 'Lost the connection to the game server.'; this.changed(); } };
      ws.onerror = () => {};
      clearInterval(this.keep); this.keep = setInterval(() => { if (this.ws && this.ws.readyState === 1) this.ws.send('ping'); }, 20000);
      this.changed();
    }
    stop() {
      clearInterval(this.keep);
      if (this.ws) { const w = this.ws; this.ws = null; try { w.close(); } catch (e) { /* ignore */ } }
      this.slots = [null, null]; this.state = [null, null]; this.code = null; this.changed();
    }
    send(m) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(m)); }
    onMsg(m) {
      if (m.t === 'pjoin' || (m.t === 'hi' && this.slots.indexOf(m.from || m.id) < 0)) this.assign(m.from || m.id);
      else if (m.t === 'hi') this.send({ t: 'slot', to: m.from, slot: this.slots.indexOf(m.from) });
      else if (m.t === 'pleave') { const i = this.slots.indexOf(m.id); if (i >= 0) { this.slots[i] = null; this.state[i] = null; this.changed(); } }
      else if (m.t === 'st') {
        const i = this.slots.indexOf(m.from); if (i < 0) return;
        const b = m.b || [];
        this.state[i] = { mx: +m.mx || 0, mz: +m.mz || 0, push: !!b[0], grab: !!b[1], dash: !!b[2], skill: !!b[3], start: !!b[4], at: performance.now() };
      }
    }
    assign(id) {
      if (!id) return;
      const slot = this.slots.indexOf(null);
      if (slot < 0) { this.send({ t: 'slot', to: id, slot: -1 }); return; } // both seats taken
      this.slots[slot] = id; this.send({ t: 'slot', to: id, slot });
      this.changed();
    }
    // the phone for player i, if it is connected and talking
    get(i) { const s = this.state[i]; return s && performance.now() - s.at < FRESH ? s : null; }
    connected(i) { return !!this.slots[i]; }
    padUrl() { return new URL('pad.html?c=' + this.code, location.href).toString(); }
    qrSvg() {
      if (!this.code || typeof qrcode !== 'function') return '';
      const q = qrcode(0, 'M'); q.addData(this.padUrl()); q.make();
      return q.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
    }
    changed() { if (this.onChange) this.onChange(); }
  }
  S.phones = new Phones();
})();
