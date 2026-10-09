// Builds KUMITEGAME, the fork at looktwicestudio.com/kumitegame/: the game with the anime look switched on.
//   node tools/build-fork.js   -> dist-kumitegame/
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..'), src = path.join(root, 'public'), out = path.join(root, 'dist-kumitegame');
fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(src, out, { recursive: true, filter: (f) => !/\.DS_Store$/.test(f) });
const ix = path.join(out, 'index.html');
let h = fs.readFileSync(ix, 'utf8');
// a white boot cover that only the logo splash removes (the original's black cover times out at 5 s and showed the versus arena)
h = h.replace(/<div id="bootcover"[^>]*><\/div>\s*<script>setTimeout\(function\(\)\{var c=document.getElementById\("bootcover"\)[^<]*<\/script>/, '<div id="wmmBoot" style="position:fixed;inset:0;background:#fff;z-index:29"></div>');
h = h.replace('<title>Kumite</title>', "<title>Where's my Mawashi</title>");
// the sumo as the icon (a head-and-shoulders render of him on a red disc); at /bigboysumo the tab says Big Boy Sumo
h = h.replace('href="assets/icon-180.png?v=2"', 'href="assets/wmm-icon-180.png"').replace('href="assets/icon-192.png?v=2"', 'href="assets/wmm-icon-192.png"').replace('href="assets/icon-512.png?v=2"', 'href="assets/wmm-icon-512.png"');
h = h.replace('<link rel="apple-touch-icon"', '<link rel="icon" type="image/png" sizes="32x32" href="assets/wmm-icon-32.png">\n<link rel="apple-touch-icon"');
h = h.replace("<title>Where's my Mawashi</title>", `<title>Where's my Mawashi</title>\n<script>if (/^\\/bigboysumo/.test(location.pathname)) document.title = 'Big Boy Sumo';</script>`);
h = h.replace('<script src="js/platform.js"></script>', `<script>window.KUMITE_STYLE = 'anime'; window.KUMITE_FORK = 'kumitegame';</script>\n<script src="js/platform.js"></script>`);
// cache-busting: every local script, stylesheet and the logo carry this build's hash, so a new deploy is never
// served from a browser's old copies (a mix of old and new files breaks the game)
const crypto = require('crypto'), hsh = crypto.createHash('md5');
const walk = (d) => { for (const f of fs.readdirSync(d).sort()) { const q = path.join(d, f); if (fs.statSync(q).isDirectory()) walk(q); else if (/\.(js|css|html|webp|glb)$/.test(f)) hsh.update(fs.readFileSync(q)); } };
walk(out); const V = hsh.digest('hex').slice(0, 10);
h = h.replace(/(<script src="(?:js|vendor)\/[^"?]+)"/g, `$1?v=${V}"`).replace(/(<link rel="stylesheet" href="css\/[^"?]+)"/g, `$1?v=${V}"`);
fs.writeFileSync(ix, h);
console.log('built', out, V);
