// Copies the game (../public) into app/ so it ships inside the desktop app. The online server is not needed.
const fs = require('fs'), path = require('path');
const src = path.join(__dirname, '..', 'public'), dst = path.join(__dirname, 'app');
fs.rmSync(dst, { recursive: true, force: true });
fs.cpSync(src, dst, { recursive: true, filter: (f) => !/\.DS_Store$/.test(f) });
console.log('game copied to', dst);
