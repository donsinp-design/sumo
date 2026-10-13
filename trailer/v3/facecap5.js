// v5 (facecap5): facecap without the box he wears into the boss bout (it burst across the ring during the salt)
// the boss bout's face-off as a finale: he throws salt, claps; the boss stomps; GO: both charge... stop just before they meet
// node facecap.js NAME SEED
const L=require('../lib.js'),fs=require('fs');const [,,name,sd]=process.argv;
(async()=>{const SS=+process.env.SS||1;const p=await L.open(1280,720,SS);if(SS>1)await p.evaluate((SS)=>{const R=S.game.R;R.prMax=SS;R.pr=SS;R.prFail=1e9;R.r.setPixelRatio(SS);R.resize&&R.resize();},SS);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1].replace('g.bossBox=true','g.bossBox=false'));
const dir=(process.env.OUT||'../frames8/')+name;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sd})=>{const g=S.game;window.STUB=0;const m=bossStart(+sd);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;
 g.ais=g.ais.filter((a)=>a.me!==m.w[0]);window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};
 const ai=g.ctrls[1].src;window.BIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[1].src={sample:(...a)=>{const r=ai.sample(...a);return m.phase==='shikiri'?BIN:r;}};
 window.M=m;window.FR=0;window.LOG=[];const em=m.emit.bind(m);m.emit=(t,d)=>{if(!/^(step|tick|sfx)$/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:'')+' '+m.phase+' '+m.phaseT.toFixed(2));return em(t,d);};},{sd});
let i=0,stop=-1;
for(;i<500;i++){const r=await p.evaluate(()=>{const g=S.game,m=g.match,me=m.w[0],o=m.w[1],I=VIN,B=BIN;Object.assign(I,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});Object.assign(B,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});
  if(m.phase==='shikiri'){if(m.goAt<6.6)m.goAt=6.8;const t=m.phaseT;
    if(t>3.35&&t<3.45)I.mz=-1;            // W: salt
    if(t>4.55&&t<4.6)I.push=true;          // clap
    if(t>5.15&&t<5.2)B.grab=true;          // the boss: stomp
    if(t>6.1)I.dash=true;                  // gathering for the charge
  } else if(m.phase==='fight'){const dx=o.x-me.x,dz=o.z-me.z,l=Math.hypot(dx,dz)||1;I.mx=dx/l;I.mz=dz/l;I.push=m.sinceGo<0.1;}
  g.frame(g.last+33.333);FR++;const gap=Math.hypot(o.x-me.x,o.z-me.z)-me.r-o.r;return {ph:m.phase,gap};});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:92});
 if(r.ph==='fight'&&r.gap<0.15&&stop<0)stop=i;if(stop>=0&&i>stop+8)break;}
fs.writeFileSync(dir+'.log',(await p.evaluate(()=>LOG)).join('\n')+'\nCONTACT '+stop);console.log(name,'done',i,'contact',stop);process.exit(0);})();
