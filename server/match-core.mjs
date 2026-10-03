// Quick Match matchmaking, shared by the local server (local.mjs) and the Cloudflare Worker (worker.mjs).
// Every player has a rating (Elo, starts at 1000) plus wins, losses and games played, stored on the server
// under an anonymous player id kept in the browser. People waiting are paired with the closest rating
// within a range that is wide for new players, grows the longer they wait, and opens to anyone after 30s.
// A pair is sent a fresh one-on-one room code; the room reports the result back here.

const START = 1000;
const clean = (pid) => String(pid || '').replace(/[^A-Za-z0-9_-]/g, '').slice(0, 40);

export class MatchCore {
  // store: { get(key) -> Promise<value|undefined>, put(key, value) -> Promise }
  constructor(store) { this.store = store; this.q = new Map(); }

  async stats(pid) { return (await this.store.get('p:' + pid)) || { r: START, w: 0, l: 0, g: 0 }; }

  // the same shape as a room, so the local server can treat it like one
  join(conn) { return conn; }
  leave(conn) { this.q.delete(conn); }
  async message(conn, raw) {
    if (raw === 'ping') { this.send(conn, 'pong'); return; }
    let m; try { m = JSON.parse(raw); } catch (e) { return; }
    if (m.t === 'find') {
      const pid = clean(m.pid); if (!pid) return;
      for (const [c, e] of this.q) if (e.pid === pid && c !== conn) this.q.delete(c); // one queue spot per player
      const s = await this.stats(pid);
      this.send(conn, { t: 'you', r: Math.round(s.r), w: s.w, l: s.l, g: s.g });
      this.q.set(conn, { pid, r: s.r, g: s.g, since: Date.now() });
      if (this.onQueue) this.onQueue(conn, this.q.get(conn));
      this.tryMatch();
    } else if (m.t === 'cancel') this.q.delete(conn);
  }

  // how far apart two ratings may be for this player right now
  range(e, now) {
    const wait = (now - e.since) / 1000;
    if (wait >= 30) return Infinity;            // nobody waits forever
    return (e.g < 10 ? 250 : 120) + wait * 25;  // new players are placed loosely until their rating settles
  }

  // pair the closest acceptable ratings first; returns how many are still waiting
  tryMatch() {
    const now = Date.now();
    let L = [...this.q.entries()];
    for (;;) {
      let best = null;
      for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) {
        const a = L[i][1], b = L[j][1];
        if (a.pid === b.pid) continue;
        const d = Math.abs(a.r - b.r);
        if (d > Math.min(this.range(a, now), this.range(b, now))) continue;
        if (!best || d < best.d) best = { i, j, d };
      }
      if (!best) break;
      const code = 'QM' + Math.random().toString(36).slice(2, 6).toUpperCase().padEnd(4, '0');
      for (const k of [best.i, best.j]) { this.send(L[k][0], { t: 'match', code }); this.q.delete(L[k][0]); }
      L = [...this.q.entries()];
    }
    return this.q.size;
  }

  // a quick-match bout finished: move both ratings (bigger steps for the first 10 games)
  async result(wpid, lpid) {
    wpid = clean(wpid); lpid = clean(lpid);
    if (!wpid || !lpid || wpid === lpid) return;
    const W = await this.stats(wpid), Lo = await this.stats(lpid);
    const ew = 1 / (1 + Math.pow(10, (Lo.r - W.r) / 400));
    const kw = W.g < 10 ? 40 : 24, kl = Lo.g < 10 ? 40 : 24;
    W.r = Math.max(100, W.r + kw * (1 - ew)); Lo.r = Math.max(100, Lo.r - kl * (1 - ew));
    W.w++; W.g++; Lo.l++; Lo.g++;
    await this.store.put('p:' + wpid, W); await this.store.put('p:' + lpid, Lo);
  }

  send(conn, msg) { try { conn.send(typeof msg === 'string' ? msg : JSON.stringify(msg)); } catch (e) { /* closed */ } }
}
