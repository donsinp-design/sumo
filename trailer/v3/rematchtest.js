// rematch boss vs a normal AI player: count edge saves vs falls, techs, parries, slap-downs over several bouts (sim only)
const L=require('../lib.js'),fs=require('fs');
(async()=>{const p=await L.open(320,180);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const r=await p.evaluate((rm)=>{const g=S.game;window.STUB=1;window.PAI='normal';F.c.bossWon1=rm;const tot={};let wins=[0,0];
 for(let sd=1;sd<=12;sd++){const m=bossStart(sd);const ai=g.ais.find(a=>a.me===m.w[1]);const em=m.emit.bind(m);
  m.emit=(t,d)=>{if(d&&d.w===m.w[1]&&/^(teeterSave|teeterFall|tech|techEscape|parry|slapGo|catch|disengage|grabTech|clinch)$/.test(t))tot[t]=(tot[t]||0)+1;if(t==='decided'&&d&&d.winner)wins[d.winner.idx]++;return em(t,d);};
  for(let f=0;f<1500;f++){g.frame(g.last+33.333);if(g.match!==m||m.phase==='over')break;}}
 return JSON.stringify({level:g.ais.find(a=>a.me===g.match.w[1])?'':'',wins,tot});},!!+process.argv[2]);
console.log(r);process.exit(0);})();
