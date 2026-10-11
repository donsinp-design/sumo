// a real boss bout: the boss's own AI vs a player bot that answers with the moves we want shown (dodge / catch / brace / parry / tech / save / slam / lift / spin / trip)
// node botrec.js NAME SEED PLAN [NMAX]   (PLAN: comma list, e.g. dodge,parry,slam)
const L=require('../lib.js'),fs=require('fs');const [,,name,sd,plan,nmax]=process.argv;
(async()=>{const SS=+process.env.SS||1;const p=await L.open(1280,720,SS);if(SS>1)await p.evaluate((SS)=>{const R=S.game.R;R.prMax=SS;R.pr=SS;R.prFail=1e9;R.r.setPixelRatio(SS);R.resize&&R.resize();},SS);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const dir=(process.env.OUT||"../frames3/")+name;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sd,plan})=>{const g=S.game;window.STUB=0;window.PAI='normal';const m=bossStart(+sd);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;
 g.ais=g.ais.filter((a)=>a.me!==m.w[0]);window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};
 window.ST={plan:plan.split(',')};window.FR=0;window.LOG=[];window.M=m;const em=m.emit.bind(m);m.emit=(t,d)=>{if(!/^(step|tick|sfx)$/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:'')+(t==='decided'&&d?' W'+(d.winner&&d.winner.idx):'')+(t==='throw'&&d?' '+d.name:''));return em(t,d);};},{sd,plan});
const N=+nmax||700;let i=0;
for(;i<N;i++){await p.evaluate(()=>{const g=S.game,m=g.match,me=m.w[0],o=m.w[1],c=m.clinch,st=ST,in_=VIN;Object.assign(in_,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});
  (()=>{const dx=o.x-me.x,dz=o.z-me.z,dl=Math.hypot(dx,dz)||1,ux=dx/dl,uz=dz/dl,gap=dl-me.r-o.r,has=(k)=>st.plan.includes(k),l=Math.hypot(me.x,me.z)||1;
  const go=(s)=>{if(gap>0.3){in_.mx=ux*(s||1);in_.mz=uz*(s||1);}};
  for(const k of ['cd','pc','tc'])if(st[k]>0)st[k]--;
  if(m.phase!=='fight'){st.ch=0;return;}
  if(me.st==='teeter'){st.saved=1;in_.grab=true;in_.mx=-me.x/l;in_.mz=-me.z/l;st.ch=0;return;}
  if(o.st==='charge'&&gap<1.4&&!st.cd&&!c){st.cd=40;if(has('dodge')&&!st.didDodge){st.didDodge=1;in_.mx=-uz;in_.mz=ux;in_.dash=true;}else if(has('catch')&&!st.didCatch){st.didCatch=1;in_.grab=true;}else if(has('brace'))in_.dash=true;return;}
  if(has('parry')&&!st.pc&&(o.st==='palm'||o.st==='heavy')&&gap<1.0){st.pc=25;in_.dash=true;return;}
  if(c){st.ch=(st.ch||0)+1;const h=st.ch;if(h<3&&has('tech')){in_.grab=true;return;}
    const mv=st.plan.find((k)=>['slam','lift','spin','trip','drive'].includes(k)&&!st['did_'+k])||'drive';
    if(mv==='slam'){if(h<16)in_.grab=true;else if(h>42&&h<45){in_.grab=true;}if(h>50)st.did_slam=1;}
    else if(mv==='lift'){if(h<16)in_.grab=true;else if(h>22){in_.mx=ux;in_.mz=uz;}if(h>140)st.did_lift=1;}
    else if(mv==='spin'){in_.grab=h<48;if(h<48){in_.mx=-ux;in_.mz=-uz;}if(h>60)st.did_spin=1;}
    else if(mv==='trip'){const tr=c.evalTech&&c.evalTech(me,'trip');in_.mx=ux;in_.mz=uz;in_.grab=!(h>8&&tr&&tr.ok&&tr.sc>0.34)&&!st.rel;if(!in_.grab){st.rel=1;st.did_trip=1;}}
    else{in_.grab=h<40;in_.mx=ux;in_.mz=uz;}
    return;}
  st.ch=0;st.rel=0;st.h=(st.h||0)+1;
  if(has('wait')&&st.h<75&&!st.didDodge){in_.mx=-ux*0.15;in_.mz=-uz*0.15;return;}
  if(has('save')&&!st.saved){if(me.st==='teeter')st.saved=1;in_.mx=-ux*0.3;in_.mz=-uz*0.3;return;}
  if(gap>0.45)go();else{if(has('grab')||st.plan.some((k)=>['slam','lift','spin','trip'].includes(k)&&!st['did_'+k]))in_.grab=st.h%10<3;else in_.push=st.h%12<2;in_.mx=ux;in_.mz=uz;}})();
  g.frame(g.last+33.333);FR++;});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});
 if(await p.evaluate(()=>S.game.match!==M||M.phase==='over'))break;}
fs.writeFileSync(dir+'.log',(await p.evaluate(()=>LOG)).join('\n'));console.log(name,'done',i);process.exit(0);})();
