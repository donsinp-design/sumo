// Room logic shared by the local server (local.mjs) and the Cloudflare Worker (worker.mjs).
// A room is a queue of people: the first two are in the ring, everyone else watches.
// Winner stays on, loser goes to the back of the queue.
// The server never runs the fight: it relays each player's button presses to everyone.

export class RoomCore {
  constructor(code) {
    this.code = code;
    this.members = new Map(); // id -> { conn, name, arch, lo }
    this.order = [];          // queue of ids; [0] and [1] are in the ring
    this.host = null;
    this.playing = false;
    this.match = null;        // { p: [id, id] }
    this.nextId = 1;
    this.auto = code === 'PUBLIC'; // quick match: bouts start by themselves
    this.autoTimer = null;
  }

  join(conn) {
    const id = 'm' + this.nextId++;
    conn.id = id;
    this.members.set(id, { conn, name: 'PLAYER', arch: 0, lo: null });
    this.order.push(id);
    if (!this.host) this.host = id;
    this.broadcastRoom();
    this.maybeAuto();
    return id;
  }

  leave(conn) {
    const id = conn.id;
    if (!this.members.has(id)) return;
    this.members.delete(id);
    this.order = this.order.filter((x) => x !== id);
    if (this.host === id) this.host = this.order[0] || null;
    if (this.autoTimer && this.order.length < 2) { clearTimeout(this.autoTimer); this.autoTimer = null; }
    if (this.playing && this.match && this.match.p.includes(id)) {
      this.playing = false; this.match = null;
      this.broadcast({ t: 'abort', reason: 'A player left the ring.' });
    }
    this.broadcastRoom();
    this.maybeAuto();
  }

  message(conn, raw) {
    let m;
    try { m = JSON.parse(raw); } catch (e) { return; }
    const id = conn.id, me = this.members.get(id);
    if (!me) return;
    switch (m.t) {
      case 'hello':
        me.name = String(m.name || 'PLAYER').slice(0, 12).toUpperCase();
        me.arch = (m.arch | 0) % 4; me.lo = m.lo || null;
        this.broadcastRoom(); break;
      case 'ping': this.send(conn, { t: 'pong', id: m.id }); break;
      case 'arch':
        me.arch = (m.arch | 0) % 4; this.broadcastRoom(); break;
      case 'start':
        if (this.auto || id !== this.host || this.playing || this.order.length < 2) return;
        this.startMatch(); break;
      case 'in': case 'hash': case 'snap': case 'need':
        // only the two fighters' inputs matter; relay to everyone else in the room
        if (!this.playing) return;
        if (m.t === 'in' && !this.match.p.includes(id)) return;
        this.broadcast(m, id); break;
      case 'end': {
        // reported by the first fighter; winner stays on, loser to the back of the queue
        if (!this.playing || id !== this.match.p[0]) return;
        const loser = this.match.p[m.winner === 0 ? 1 : 0];
        this.order = this.order.filter((x) => x !== loser); this.order.push(loser);
        const winner = this.match.p[m.winner === 0 ? 0 : 1];
        this.order = [winner].concat(this.order.filter((x) => x !== winner));
        this.playing = false; this.match = null;
        this.broadcastRoom(); this.maybeAuto(); break;
      }
    }
  }

  startMatch() {
    if (this.playing || this.order.length < 2) return;
    this.playing = true;
    this.match = { p: [this.order[0], this.order[1]] };
    this.broadcast({
      t: 'start', seed: (Math.random() * 2 ** 31) | 0, p: this.match.p,
      names: this.match.p.map((x) => this.members.get(x).name),
      archs: this.match.p.map((x) => this.members.get(x).arch),
      los: this.match.p.map((x) => this.members.get(x).lo),
    });
    this.broadcastRoom();
  }
  // quick match: start a bout a few seconds after two people are free
  maybeAuto() {
    if (!this.auto || this.playing || this.order.length < 2 || this.autoTimer) return;
    this.autoAt = Date.now() + 5000;
    this.broadcastRoom();
    this.autoTimer = setTimeout(() => { this.autoTimer = null; this.startMatch(); }, 5000);
  }

  roomState(forId) {
    return {
      t: 'room', code: this.code, you: forId, host: this.host, playing: this.playing, auto: this.auto, startsIn: this.autoTimer ? Math.max(0, this.autoAt - Date.now()) : 0,
      order: this.order.map((id) => { const x = this.members.get(id); return { id, name: x.name, arch: x.arch }; }),
    };
  }
  broadcastRoom() { for (const [id, x] of this.members) this.send(x.conn, this.roomState(id)); }
  broadcast(msg, exceptId) {
    const s = JSON.stringify(msg);
    for (const [id, x] of this.members) if (id !== exceptId) this.send(x.conn, s);
  }
  send(conn, msg) { try { conn.send(typeof msg === 'string' ? msg : JSON.stringify(msg)); } catch (e) { /* closed */ } }
}
