// Cloudflare Worker: serves the game (static assets) and runs each room in a Durable Object.
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
  constructor(state, env) { this.state = state; this.core = null; }
  async fetch(request) {
    const url = new URL(request.url);
    const code = (url.searchParams.get('room') || '').toUpperCase();
    if (!this.core) this.core = new RoomCore(code);
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    server.accept();
    const conn = { send: (s) => server.send(s) };
    this.core.join(conn);
    server.addEventListener('message', (ev) => this.core.message(conn, typeof ev.data === 'string' ? ev.data : ''));
    const bye = () => this.core.leave(conn);
    server.addEventListener('close', bye);
    server.addEventListener('error', bye);
    return new Response(null, { status: 101, webSocket: client });
  }
}
