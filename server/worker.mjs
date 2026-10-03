// Cloudflare Worker: serves the game (static assets) and runs each room in a Durable Object.
// Rooms use WebSocket hibernation: when nobody is sending anything, the room sleeps and costs nothing,
// and the people in it stay connected. Who is in the room (and in what order) is saved on each
// connection, so the room can rebuild itself when the next message wakes it.
import { RoomCore } from './room-core.mjs';

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
    if (url.pathname === '/ws') {
      const code = (url.searchParams.get('room') || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
      if (!code || request.headers.get('Upgrade') !== 'websocket') return new Response('Expected a websocket', { status: 400 });
      const stub = env.ROOMS.get(env.ROOMS.idFromName(code));
      return stub.fetch(request);
    }
    return env.ASSETS.fetch(request);
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
    if (saved.length) this.core.restore(saved.map((x) => Object.assign({ conn: this.connFor(x.ws) }, x.a)));
  }
  persist() {
    const c = this.core; if (!c) return;
    for (const [id, x] of c.members) {
      const ws = x.conn.ws; if (!ws) continue;
      let lo = x.lo; try { if (JSON.stringify(lo || null).length > 1200) lo = null; } catch (e) { lo = null; }
      try { ws.serializeAttachment({ id, code: c.code, name: x.name, arch: x.arch, lo, pos: c.order.indexOf(id), host: c.host === id }); } catch (e) { /* too big or closed */ }
    }
  }
  async fetch(request) {
    const url = new URL(request.url);
    this.ensure((url.searchParams.get('room') || '').toUpperCase());
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.state.acceptWebSocket(server);
    this.core.join(this.connFor(server));
    return new Response(null, { status: 101, webSocket: client });
  }
  webSocketMessage(ws, msg) {
    this.ensure();
    this.core.message(this.connFor(ws), typeof msg === 'string' ? msg : '');
  }
  webSocketClose(ws) { this.bye(ws); }
  webSocketError(ws) { this.bye(ws); }
  bye(ws) {
    this.ensure();
    this.core.leave(this.connFor(ws));
    this.conns.delete(ws);
    try { ws.close(1000, 'bye'); } catch (e) { /* already closed */ }
  }
}
