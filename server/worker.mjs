// Cloudflare Worker: serves the game (static assets) and runs each room in a Durable Object.
// Rooms use WebSocket hibernation: when nobody is sending anything, the room sleeps and costs nothing,
// and the people in it stay connected. Who is in the room (and in what order) is saved on each
// connection, so the room can rebuild itself when the next message wakes it.
import { RoomCore } from './room-core.mjs';
import { MatchCore } from './match-core.mjs';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    // the game can live under a subpage, e.g. looktwicestudio.com/kumite/
    const base = (env.BASE_PATH || '').replace(/\/$/, '');
    if (base && url.pathname.startsWith(base)) {
      if (url.pathname === base) return Response.redirect(url.origin + base + '/' + url.search, 301);
      url.pathname = url.pathname.slice(base.length) || '/';
      request = new Request(url.toString(), request);
    }
    if (url.pathname === '/mm') { // Quick Match queue: one matchmaker for everyone
      if (request.headers.get('Upgrade') !== 'websocket') return new Response('Expected a websocket', { status: 400 });
      return env.MM.get(env.MM.idFromName('global')).fetch(request);
    }
    if (url.pathname === '/ws') {
      const code = (url.searchParams.get('room') || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
      if (!code || request.headers.get('Upgrade') !== 'websocket') return new Response('Expected a websocket', { status: 400 });
      const stub = env.ROOMS.get(env.ROOMS.idFromName(code));
      return stub.fetch(request);
    }
    const res = await env.ASSETS.fetch(request);
    // Cloudflare tidies addresses (pad.html -> pad) with a redirect to a root path; keep the game's subpage in it
    if (base && res.status >= 300 && res.status < 400) {
      const loc = res.headers.get('Location');
      if (loc && loc.startsWith('/') && !loc.startsWith(base + '/')) {
        const h = new Headers(res.headers); h.set('Location', base + loc);
        return new Response(res.body, { status: res.status, headers: h });
      }
    }
    return res;
  },
};

export class Room {
  constructor(state, env) {
    this.state = state; this.env = env; this.core = null; this.conns = new Map();
    // pings are answered by Cloudflare itself: they never wake the room and are not billed as room work
    try { state.setWebSocketAutoResponse(new WebSocketRequestResponsePair('ping', 'pong')); } catch (e) { /* older runtime */ }
  }
  connFor(ws) {
    let c = this.conns.get(ws);
    if (!c) { c = { ws, send: (s) => { try { ws.send(s); } catch (e) { /* closed */ } } }; this.conns.set(ws, c); }
    return c;
  }
  // make sure the room logic exists; after a sleep, rebuild it from what each connection remembers
  ensure(code) {
    if (this.core) return;
    const socks = this.state.getWebSockets();
    const saved = socks.map((ws) => ({ ws, a: ws.deserializeAttachment() || null })).filter((x) => x.a && x.a.id);
    this.core = new RoomCore(code || (saved[0] && saved[0].a.code) || '');
    this.core.onChange = () => this.persist();
    // quick-match results go to the matchmaker, which keeps everyone's rating
    this.core.onResult = (w, l) => {
      if (!this.env.MM) return;
      const p = this.env.MM.get(this.env.MM.idFromName('global')).fetch('https://mm/result', { method: 'POST', body: JSON.stringify({ w, l }) }).catch(() => {});
      (this.pending || (this.pending = [])).push(p);
    };
    if (saved.length) this.core.restore(saved.map((x) => Object.assign({ conn: this.connFor(x.ws) }, x.a)));
  }
  persist() {
    const c = this.core; if (!c) return;
    for (const [id, x] of c.members) {
      const ws = x.conn.ws; if (!ws) continue;
      let lo = x.lo; try { if (JSON.stringify(lo || null).length > 1200) lo = null; } catch (e) { lo = null; }
      try { ws.serializeAttachment({ id, code: c.code, name: x.name, arch: x.arch, lo, pid: x.pid || '', pos: c.order.indexOf(id), host: c.host === id }); } catch (e) { /* too big or closed */ }
    }
  }
  async fetch(request) {
    const url = new URL(request.url);
    this.ensure((url.searchParams.get('room') || '').toUpperCase());
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.state.acceptWebSocket(server);
    if (this.core.join(this.connFor(server)) === null) { this.conns.delete(server); try { server.close(1000, 'full'); } catch (e) { /* ignore */ } }
    return new Response(null, { status: 101, webSocket: client });
  }
  async webSocketMessage(ws, msg) {
    this.ensure();
    this.core.message(this.connFor(ws), typeof msg === 'string' ? msg : '');
    await this.flush();
  }
  async webSocketClose(ws) { await this.bye(ws); }
  async webSocketError(ws) { await this.bye(ws); }
  async bye(ws) {
    this.ensure();
    this.core.leave(this.connFor(ws));
    this.conns.delete(ws);
    try { ws.close(1000, 'bye'); } catch (e) { /* already closed */ }
    await this.flush();
  }
  async flush() { if (this.pending && this.pending.length) { const p = this.pending; this.pending = []; await Promise.all(p); } }
}

// The Quick Match queue and everyone's rating. Waiting players are remembered on their connections,
// so it can sleep between messages; an alarm re-checks the queue every 2s while anyone is waiting
// (the allowed rating gap grows with the wait).
export class Matchmaker {
  constructor(state, env) {
    this.state = state; this.conns = new Map();
    try { state.setWebSocketAutoResponse(new WebSocketRequestResponsePair('ping', 'pong')); } catch (e) { /* older runtime */ }
    this.core = new MatchCore({ get: (k) => state.storage.get(k), put: (k, v) => state.storage.put(k, v) });
    this.core.onQueue = (conn, e) => { try { conn.ws.serializeAttachment(e); } catch (er) { /* closed */ } };
    for (const ws of state.getWebSockets()) { const a = ws.deserializeAttachment(); if (a && a.pid) this.core.q.set(this.connFor(ws), a); }
  }
  connFor(ws) {
    let c = this.conns.get(ws);
    if (!c) { c = { ws, send: (s) => { try { ws.send(s); } catch (e) { /* closed */ } } }; this.conns.set(ws, c); }
    return c;
  }
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === '/result' && request.method === 'POST') {
      try { const { w, l } = await request.json(); await this.core.result(w, l); } catch (e) { /* bad report */ }
      return new Response('ok');
    }
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.state.acceptWebSocket(server);
    return new Response(null, { status: 101, webSocket: client });
  }
  async webSocketMessage(ws, msg) {
    await this.core.message(this.connFor(ws), typeof msg === 'string' ? msg : '');
    if (this.core.q.size && !(await this.state.storage.getAlarm())) await this.state.storage.setAlarm(Date.now() + 2000);
  }
  async webSocketClose(ws) { this.core.leave(this.connFor(ws)); this.conns.delete(ws); try { ws.close(1000, 'bye'); } catch (e) { /* closed */ } }
  async webSocketError(ws) { await this.webSocketClose(ws); }
  async alarm() { if (this.core.tryMatch()) await this.state.storage.setAlarm(Date.now() + 2000); }
}
