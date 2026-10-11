// scan bare boss bouts (render stubbed): node boutscan.js FROM TO PAI out.json
const L=require('../lib.js'),fs=require('fs');const a=process.argv.slice(2);
(async()=>{const p=await L.open(480,270);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const res=await p.evaluate(({from,to,pai})=>{const g=S.game;window.STUB=1;window.PAI=pai;const out={};
 for(let sd=from;sd<=to;sd++){const m=bossStart(sd);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;const log=[];let fr=0;const em=m.emit.bind(m);
  m.emit=(t,d)=>{if(!/^(step|tick|sfx)$/.test(t))log.push(fr+' '+t+' '+(d&&d.w?d.w.idx:d&&d.winner?'W'+d.winner.idx:''));return em(t,d);};
  for(fr=0;fr<1500;fr++){g.frame(g.last+33.333);if(g.match!==m||m.phase==='over')break;}
  out[sd]={frames:fr,log};}
 return out;},{from:+a[0],to:+a[1],pai:a[2]});
fs.writeFileSync(a[3],JSON.stringify(res));console.log('scanned');process.exit(0);})();
