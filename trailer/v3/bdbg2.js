const L=require('../lib.js');
(async()=>{const p=await L.open(640,360);await L.boot(p,5);
await p.evaluate(require('fs').readFileSync('bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
await p.evaluate(()=>{window.M=bossStart(10);});
for(let i=0;i<150;i++){await p.evaluate(()=>S.game.frame(S.game.last+33.333)); if(i==40||i==100||i==149) await p.screenshot({path:'../out/bdbg_'+i+'.jpg'});}
process.exit(0);})();
