// Local game server: serves the game and runs online rooms. No dependencies.
// Run:  node server/local.mjs 8732      then open http://localhost:8732
import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { RoomCore } from './room-core.mjs';
import { MatchCore } from './match-core.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'public');
const PORT = +(process.argv[2] || process.env.PORT || 8732);
const SHOTS = path.resolve(ROOT, '..', '..', 'shots');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.webp': 'image/webp',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };

const rooms = new Map();
// Quick Match queue and ratings (kept in memory here; on Cloudflare they are stored for good)
const ratings = new Map();
const mm = new MatchCore({ get: async (k) => ratings.get(k), put: async (k, v) => { ratings.set(k, v); } });
setInterval(() => mm.tryMatch(), 2000); // the allowed rating gap grows while people wait
const roomFor = (code) => {
  if (!rooms.has(code)) { const r = new RoomCore(code); r.onResult = (w, l) => mm.result(w, l); rooms.set(code, r); }
  return rooms.get(code);
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (req.method === 'POST' && url.pathname === '/__shot') { // dev screenshots
    const name = (url.searchParams.get('name') || 'shot').replace(/[^\w-]/g, '');
    const chunks = []; req.on('data', (c) => chunks.push(c));
    req.on('end', () => { fs.mkdirSync(SHOTS, { recursive: true }); fs.writeFileSync(path.join(SHOTS, name + '.jpg'), Buffer.concat(chunks)); res.end('ok'); });
    return;
  }
  let p = decodeURIComponent(url.pathname);
  if (p.endsWith('/')) p += 'index.html';
  const file = path.resolve(ROOT, '.' + p);
  if (!file.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(data);
  });
});

// ---- minimal WebSocket (RFC 6455): text frames, ping/pong, close
server.on('upgrade', (req, sock) => {
  const url = new URL(req.url, 'http://x');
  const isMM = url.pathname.endsWith('/mm');
  if (!url.pathname.endsWith('/ws') && !isMM) { sock.destroy(); return; }
  const code = isMM ? '' : (url.searchParams.get('room') || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
  if (!code && !isMM) { sock.destroy(); return; }
  const accept = crypto.createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
  sock.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + '\r\n\r\n');
  sock.setNoDelay(true);
  const room = isMM ? mm : roomFor(code);
  const LAG = +(process.env.LAG || 0);
  const conn = {
    send(str) { if (LAG) { setTimeout(() => conn.sendNow(str), LAG + Math.random() * LAG * 0.3); return; } conn.sendNow(str); },
    sendNow(str) {
      const body = Buffer.from(str);
      let head;
      if (body.length < 126) head = Buffer.from([0x81, body.length]);
      else if (body.length < 65536) { head = Buffer.alloc(4); head[0] = 0x81; head[1] = 126; head.writeUInt16BE(body.length, 2); }
      else { head = Buffer.alloc(10); head[0] = 0x81; head[1] = 127; head.writeBigUInt64BE(BigInt(body.length), 2); }
      sock.write(Buffer.concat([head, body]));
    },
  };
  room.join(conn);
  let buf = Buffer.alloc(0), closed = false;
  const close = () => { if (closed) return; closed = true; room.leave(conn); if (room.members && !room.members.size) rooms.delete(code); sock.destroy(); };
  sock.on('data', (d) => {
    buf = Buffer.concat([buf, d]);
    while (buf.length >= 2) {
      const op = buf[0] & 0x0f, masked = buf[1] & 0x80;
      let len = buf[1] & 0x7f, off = 2;
      if (len === 126) { if (buf.length < 4) return; len = buf.readUInt16BE(2); off = 4; }
      else if (len === 127) { if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); off = 10; }
      const need = off + (masked ? 4 : 0) + len;
      if (buf.length < need) return;
      let payload = buf.subarray(off + (masked ? 4 : 0), need);
      if (masked) { const mk = buf.subarray(off, off + 4); payload = Buffer.from(payload); for (let i = 0; i < payload.length; i++) payload[i] ^= mk[i & 3]; }
      buf = buf.subarray(need);
      if (op === 1) { const txt = payload.toString('utf8'); if (LAG) setTimeout(() => room.message(conn, txt), LAG); else room.message(conn, txt); }
      else if (op === 8) { close(); return; }
      else if (op === 9) sock.write(Buffer.concat([Buffer.from([0x8a, payload.length]), payload]));
    }
  });
  sock.on('close', close); sock.on('error', close);
});

server.listen(PORT, () => console.log('Kumite running at http://localhost:' + PORT));
