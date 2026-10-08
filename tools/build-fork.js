// Builds KUMITEGAME, the fork at looktwicestudio.com/kumitegame/: the game with the anime look switched on.
//   node tools/build-fork.js   -> dist-kumitegame/
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..'), src = path.join(root, 'public'), out = path.join(root, 'dist-kumitegame');
fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(src, out, { recursive: true, filter: (f) => !/\.DS_Store$/.test(f) });
const ix = path.join(out, 'index.html');
let h = fs.readFileSync(ix, 'utf8');
// a white boot cover that only the logo splash removes (the original's black cover times out at 5 s and showed the versus arena)
h = h.replace(/<div id="bootcover"[^>]*><\/div>\s*<script>setTimeout\(function\(\)\{var c=document.getElementById\("bootcover"\)[^<]*<\/script>/, '<div id="wmmBoot" style="position:fixed;inset:0;background:#fff;z-index:47"></div>');
h = h.replace('<title>Kumite</title>', "<title>Where's my Mawashi</title>");
h = h.replace('<script src="js/platform.js"></script>', `<script>window.KUMITE_STYLE = 'anime'; window.KUMITE_FORK = 'kumitegame';</script>\n<script src="js/platform.js"></script>`);
fs.writeFileSync(ix, h);
console.log('built', out);
