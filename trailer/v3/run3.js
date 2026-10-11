// natural takes: warm up (no render) so the take starts mid-action, then record at the game's own camera
const L=require('../lib.js'),fs=require('fs');
const [,, name, mode]=process.argv; const T=require('./takes.js'); const tk=T[name];
if(!tk){ console.log('no take',name); process.exit(1); }
(async()=>{
  const preview=mode==='preview'; const W=preview?640:1280,H=preview?360:720;
  const dir=(process.env.DIR?process.env.DIR:preview?'../prev/':'../frames/')+name; fs.mkdirSync(dir,{recursive:true});
  const SS=+process.env.SS||1;const p=await L.open(W,H,SS);if(SS>1)await p.evaluate((SS)=>{const R=S.game.R;R.prMax=SS;R.pr=SS;R.prFail=1e9;R.r.setPixelRatio(SS);R.resize&&R.resize();},SS); await L.boot(p,tk.seed); await p.evaluate(T.HELP);
  await p.evaluate(`(()=>{const F=window.F;F.c.asleep=false;F.take={};(${tk.setup.toString()})(F);F.c.G.traverse((o)=>{if(o.userData&&o.userData.ring&&o.userData.ar)Object.defineProperty(o,'visible',{get:()=>false,set:()=>{},configurable:true});});})()`);
  await p.evaluate(`(()=>{const F=window.F,c=F.c,sc=${tk.script.toString()};const pre=${tk.pre};let k=0;for(;k<pre*60;k++){sc(k/60,F);c.ctrl.update(1/60);c.step(1/60);if(F.take.stopWarm)break;}F.t0=k/60;const P=c.P;c.camT.set(Math.max(-18,Math.min(18,P.x*0.8)),Math.max(0,P.y),P.z-2.6);})()`);
  const LOG=process.env.LOG||'""';const step=`(()=>{const F=window.F,c=F.c;F.t0+=1/30;(${tk.script.toString()})(F.t0,F);c.frame(1/30);const gt=F.t0*1000;for(const an of document.getAnimations()){if(an._g0===undefined){an._g0=gt;an.pause();}an.currentTime=gt-an._g0;}const P=c.P;return (${LOG});})()`;const logs=[];
  for(let i=0;i<10;i++) await p.evaluate(step);
  let k=0;
  const NN=+process.env.N||tk.n;for(let i=0;i<NN;i++){
    logs.push(i+' '+await p.evaluate(step));
    if(!preview||i%3===0){ await p.screenshot({path:`${dir}/f_${String(k++).padStart(4,'0')}.jpg`,type:'jpeg',quality:preview?70:90}); }
  }
  if(process.env.LOG)fs.writeFileSync(dir+'.log',logs.join('\n'));console.log(name,'done',k); await p.close(); process.exit(0);
})();
