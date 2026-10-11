// a whole boss bout (bare: after the box burst), AI on both sides, game camera, no HUD; every frame + an event log
const L=require('../lib.js'),fs=require('fs');
const [,,name,sd,pai,nmax]=process.argv;
(async()=>{const p=await L.open(1280,720);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const dir='../frames3/'+name;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sd,pai})=>{window.PAI=pai||'normal';window.STUB=0;const g=S.game;const m=bossStart(+sd);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;window.LOG=[];window.FR=0;const em=m.emit.bind(m);
  m.emit=(t,d)=>{if(!/^(step|tick|sfx)$/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:d&&d.winner?'W'+d.winner.idx:''));return em(t,d);};window.M=m;},{sd:+sd,pai});
const N=+nmax||600;let i=0;for(;i<N;i++){await p.evaluate(()=>{S.game.frame(S.game.last+33.333);FR++;});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});
 if(await p.evaluate(()=>S.game.match!==M||M.phase==='over'))break;}
fs.writeFileSync(dir+'.log',(await p.evaluate(()=>LOG)).join('\n'));console.log(name,'done',i);process.exit(0);})();
