// gacha skill on the boss stage (box already burst), game camera, no HUD. node gcap.js SKILL SEED [N] [FIRE]
const L=require('../lib.js'),fs=require('fs');
const [,,sk,sd,nn,fire]=process.argv;const N=+nn||96,FIRE=+fire||8;
(async()=>{const p=await L.open(1280,720);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const dir='../frames/g2_'+sk;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sk,sd})=>{const g=S.game;window.STUB=1;window.PAI='normal';
  const m=bossStart(+sd);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;
  window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};
  let k=0;while(m.phase!=='fight'&&k<2000){g.frame(g.last+33.333);k++;}
  for(let i=0;i<20;i++)g.frame(g.last+33.333);
  m.skills=[sk,null];g.awaitGacha=false;g.refreshSkills&&g.refreshSkills();window.STUB=0;window.M=m;},{sk,sd});
for(let i=0;i<10;i++)await p.evaluate(()=>S.game.frame(S.game.last+33.333));
for(let i=0;i<N;i++){await p.evaluate(({i,FIRE,sk})=>{const m=M,w=m.w;Object.assign(VIN,{mx:0,mz:0,push:false,skill:false});
   if(m.skills&&!m.skills[0]&&i<FIRE)m.skills[0]=sk;
   const dx=w[1].x-w[0].x,dz=w[1].z-w[0].z,d=Math.hypot(dx,dz)||1;if(d>1.3){VIN.mx=dx/d;VIN.mz=dz/d;}
   if(i>=FIRE&&i<FIRE+3)VIN.skill=true;else if(i%20>12)VIN.push=true;
   S.game.frame(S.game.last+33.333);},{i,FIRE,sk});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});}
console.log(sk,'done');process.exit(0);})();
