// Builds the browser version for game portals (itch.io, Newgrounds, Game Jolt, CrazyGames):
// the game files with online play pointed at looktwicestudio.com, zipped as Kumite-web.zip.
//   node tools/build-web.js            -> dist-web/ and Kumite-web.zip
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
const root = path.join(__dirname, '..'), src = path.join(root, 'public'), out = path.join(root, 'dist-web');
const SERVER = 'https://looktwicestudio.com/kumite/';
fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(src, out, { recursive: true, filter: (f) => !/\.DS_Store$|manifest\.webmanifest$/.test(f) });
const ix = path.join(out, 'index.html');
let h = fs.readFileSync(ix, 'utf8');
h = h.replace('<script src="js/platform.js"></script>',
  `<script>window.KUMITE_SERVER = ${JSON.stringify(SERVER)}; window.KUMITE_PORTAL = 'portal';</script>\n<script src="js/platform.js"></script>`);
h = h.replace(/<link rel="manifest"[^>]*>\n?/, ''); // install-as-app belongs to the real website
fs.writeFileSync(ix, h);
fs.rmSync(path.join(root, 'Kumite-web.zip'), { force: true });
execSync('zip -qr ../Kumite-web.zip .', { cwd: out });
const n = execSync('find . -type f | wc -l', { cwd: out }).toString().trim();
console.log('Kumite-web.zip:', n, 'files,', (fs.statSync(path.join(root, 'Kumite-web.zip')).size / 1e6).toFixed(1), 'MB');
