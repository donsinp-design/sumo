// Copies the game (../public) into www/ so it ships inside the iPhone / iPad / Mac app.
const fs = require('fs'), path = require('path');
const src = path.join(__dirname, '..', 'public'), dst = path.join(__dirname, 'www');
fs.rmSync(dst, { recursive: true, force: true });
fs.cpSync(src, dst, { recursive: true, filter: (f) => !/\.DS_Store$/.test(f) });
console.log('game copied to', dst);
