// Builds KUMITEGAME, the fork at looktwicestudio.com/kumitegame/: the game with the anime look switched on.
//   node tools/build-fork.js   -> dist-kumitegame/
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..'), src = path.join(root, 'public'), out = path.join(root, 'dist-kumitegame');
fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(src, out, { recursive: true, filter: (f) => !/\.DS_Store$/.test(f) });
const ix = path.join(out, 'index.html');
let h = fs.readFileSync(ix, 'utf8');
h = h.replace('<script src="js/platform.js"></script>', `<script>window.KUMITE_STYLE = 'anime'; window.KUMITE_FORK = 'kumitegame';</script>\n<script src="js/platform.js"></script>`);
fs.writeFileSync(ix, h);
console.log('built', out);
