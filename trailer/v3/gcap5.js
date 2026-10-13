// v5 (gcap5): gcap2 + the boss's inputs can be scripted too (bin), extra CSS (CSS env), the unplug pop-up shown, potato tag chase, stomp from a distance
// gacha skill used the way a player would, boss stage (bare), game camera, no HUD, event log.  node gcap2.js SKILL N
const L=require('../lib.js'),fs=require('fs');
const [,,sk,nn]=process.argv;const N=+nn||150;
const PLAY={
 dizzySlap:`if(!st.f){go();if(gap<0.4&&i>4){in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;else if(i-st.f>30&&gap<0.5&&i%10<2)in_.push=true;else if(i-st.f>30)go();`,
 smoke:`if(i>=4&&i<7)in_.skill=true;else if(i>20){go();if(gap<0.4&&i%12<2)in_.push=true;}`,
 dashThru:`if(!st.f){go();if(gap<1.6&&i>4){in_.mx=ux;in_.mz=uz;in_.skill=true;st.f=i;}}else if(i-st.f<3){in_.mx=ux;in_.mz=uz;in_.skill=true;}else if(i-st.f>20){go();if(gap<0.4&&i%10<2)in_.push=true;}`,
 invis:`if(i>=4&&i<7)in_.skill=true;else if(i>14){go();if(gap<0.4&&i%10<2)in_.push=true;}`,
 gale:`if(!st.f){if(gap>2.2)go();else if(i>4){in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;else if(i-st.f<50){in_.mx=ux;in_.mz=uz;}`,
 dart:`if(!st.f){if(gap>2.5)go();else if(i>4){me.f=Math.atan2(uz,ux);in_.mx=ux*0.2;in_.mz=uz*0.2;in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;else if(i-st.f>18){go();if(gap<0.4&&i%10<2)in_.push=true;}`,
 spin:`if(i>=4&&i<7)in_.skill=true;`,
 blur:`if(i>=4&&i<7)in_.skill=true;else if(i>14){if(i%40<20){in_.mx=-uz;in_.mz=ux;}else{go();if(gap<0.4&&i%10<2)in_.push=true;}}`,
 storm:`if(i>=4&&i<7)in_.skill=true;`,
 molotov:`if(m.skills&&m.skills[0]){in_.mx=ux*0.2;in_.mz=uz*0.2;in_.skill=i%6<2;}else{const l=Math.hypot(me.x,me.z)||1;if(gap<1.1){in_.dash=true;}else if(l>1){in_.mx=-me.x/l;in_.mz=-me.z/l;}}`,
 cyclone:`if(i>=4&&i<7)in_.skill=true;else if(i>8)go();`,
 hundred:`if(!st.f){go();if(gap<0.4&&i>4){in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;else{go(0.4);in_.push=true;}`,
 giant:`if(i>=4&&i<7)in_.skill=true;else if(i>10){go();if(gap<0.4&&i%10<2)in_.push=true;}`,
 train:`const tr=m.objs.find((q)=>q.type==='train'&&!q.go);if(!st.f){if(i>=6&&i<9)in_.skill=true;else if(gap>1.2)go();if(tr)st.f=i;}else if(tr){const px=-Math.sin(tr.a),pz=Math.cos(tr.a),vo=o.x*px+o.z*pz-tr.off,sg=Math.sign(vo)||1;const tx=o.x+px*sg*(o.r+me.r+0.15),tz=o.z+pz*sg*(o.r+me.r+0.15),qx=tx-me.x,qz=tz-me.z,ql=Math.hypot(qx,qz);const vm=me.x*px+me.z*pz-tr.off;if(tr.t>1.5){if(Math.abs(vo)<1.6&&Math.abs(vm)>Math.abs(vo)){in_.mx=-px*sg;in_.mz=-pz*sg;in_.push=i%6<2;}else{in_.mx=px*Math.sign(vm||1);in_.mz=pz*Math.sign(vm||1);}}else if(ql>0.3){in_.mx=qx/ql;in_.mz=qz/ql;}}else if(st.f){const l=Math.hypot(me.x,me.z)||1;if(l>2.5){in_.mx=-me.x/l;in_.mz=-me.z/l;}}`,
 rewind:`if(!st.f){const r=Math.hypot(me.x,me.z);if(r>S.RING_R-0.25&&i>8){in_.skill=true;st.f=i;}else if(gap>0.6&&i<12)go();}else if(i-st.f<3)in_.skill=true;`,
 bumper:`if(i>=4&&i<7)in_.skill=true;else if(i>10){const l=Math.hypot(me.x,me.z)||1;in_.mx=me.x/l;in_.mz=me.z/l;}`,
 torpedo:`if(!st.f){if(gap<3.2&&i<55){let ax=-ux-me.x*0.3,az=-uz-me.z*0.3;const al=Math.hypot(ax,az)||1;in_.mx=ax/al;in_.mz=az/al;in_.dash=i===4;}else{in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;`,
 triplets:`if(i>=6&&i<9)in_.skill=true;else if(gap>1)go();`,
 shock:`if(i>=2&&i<5)in_.skill=true;`,
 bellyFlop:`if(i>=2&&i<5)in_.skill=true;else if(me.st==='air'){in_.mx=0;in_.mz=0;}else go();`,
 chicken:`if(i>=4&&i<7)in_.skill=true;else if(i>20)go();`,
 inhale:`if(!st.f){go();if(gap<0.45&&i>4){in_.skill=true;st.f=i;}}else if(i-st.f<4)in_.skill=true;else if(!st.sp){const l=Math.hypot(me.x,me.z)||1;if(l<2.9){in_.mx=me.x/l;in_.mz=me.z/l;}else{me.f=Math.atan2(me.z,me.x);in_.skill=true;st.sp=i;}}else if(i-st.sp<3){in_.skill=true;}`,
 banana:`if(!st.f){if(gap<2.3&&i<40){let ax=-ux-me.x*0.3,az=-uz-me.z*0.3;const al=Math.hypot(ax,az)||1;in_.mx=ax/al;in_.mz=az/al;}else{in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;else if(i-st.f<22){let ax=-ux-me.x*0.35,az=-uz-me.z*0.35;const al=Math.hypot(ax,az)||1;in_.mx=ax/al;in_.mz=az/al;in_.dash=i-st.f===5;}`,
 ball:`if(i>=4&&i<7)in_.skill=true;else{go();if(i>20&&gap<2.2&&i%20<2)in_.dash=true;}`,
 potato:`if(m.skills&&m.skills[0]){go();in_.skill=i%6<2&&i>=2;}else{const l=Math.hypot(me.x,me.z)||1;if(gap<1.1){in_.dash=true;}else if(l>1){in_.mx=-me.x/l;in_.mz=-me.z/l;}}`,
 bomb:`const b=m.objs.find((q)=>q.type==='bomb'&&!q.gone);if(!st.f){if(i>=2&&i<5)in_.skill=true;if(b)st.f=i;}else if(b){const ex=b.x-o.x,ez=b.z-o.z,el=Math.hypot(ex,ez)||1,tx=b.x+ex/el*1.05,tz=b.z+ez/el*1.05,qx=tx-me.x,qz=tz-me.z,ql=Math.hypot(qx,qz);if(st.sl&&i-st.sl>3||b.t>4.2){const rx=me.x-b.x,rz=me.z-b.z,rl=Math.hypot(rx,rz)||1;let ax=rx/rl-me.x*0.25,az=rz/rl-me.z*0.25;const al=Math.hypot(ax,az)||1;in_.mx=ax/al;in_.mz=az/al;}else if(ql>0.3){in_.mx=qx/ql;in_.mz=qz/ql;}else{me.f=Math.atan2(-ez,-ex);if(b.t>3.2&&!st.sl){in_.push=true;st.sl=i;}}}`,
 unplug:`if(i>=4&&i<7)in_.skill=true;else if(i>10){go();if(gap<0.4&&i%10<2)in_.push=true;}`,
 potato2:`st.bo=true;const pot=m.objs.find((q)=>q.type==='potato');const RR=S.RING_R-1.1;
   const flee=(a,b,sp)=>{let dx=a.x-b.x,dz=a.z-b.z,l=Math.hypot(dx,dz)||1;dx/=l;dz/=l;const r=Math.hypot(a.x,a.z)||1;if(r>RR){const tx=-a.z/r,tz=a.x/r,s=Math.sign(tx*dx+tz*dz)||1;dx=tx*s-a.x/r*0.7;dz=tz*s-a.z/r*0.7;const q=Math.hypot(dx,dz)||1;dx/=q;dz/=q;}return [dx*sp,dz*sp];};
   if(!pot){if(i>=4&&i<7)in_.skill=true;}
   else{const late=pot.t>pot.dur-1.6,ready=pot.cd<-0.35;
     if(pot.holder===0){if(ready){in_.mx=ux;in_.mz=uz;}const f=flee(o,me,late?1:0.8);bin.mx=f[0];bin.mz=f[1];}
     else{const f=flee(me,o,late?1:0.8);in_.mx=f[0];in_.mz=f[1];if(ready&&!late){bin.mx=-ux;bin.mz=-uz;}else if(late){bin.mx=-ux*0.7;bin.mz=-uz*0.7;}}}`,
 shock2:`st.bo=i<75;if(!st.f){if(gap<2.3){in_.mx=-ux;in_.mz=-uz;}else if(i>3){in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;if(st.bo){if(st.f&&i-st.f>4){bin.mx=-ux*0.45;bin.mz=-uz*0.45;}}`,
 unplug2:`if(i>=4&&i<7)in_.skill=true;else if(i>10){go();if(gap<0.4&&i%10<2)in_.push=true;}`,
 torpedo2:`st.bo=!st.f||i-st.f<30;if(!st.f){if(gap<3.0&&i<60){let ax=-ux-me.x*0.3,az=-uz-me.z*0.3;const al=Math.hypot(ax,az)||1;in_.mx=ax/al;in_.mz=az/al;}else if(i>4){me.f=Math.atan2(uz,ux);in_.skill=true;st.f=i;}}else if(i-st.f<3){me.f=Math.atan2(uz,ux);in_.skill=true;}`,
 c_tripball:`st.bo=true;if(i>=6&&i<9)in_.skill=true;else if(i>12&&gap>1)go(0.6);
   if(i>=20&&i<23)bin.skill=true;else if(i>24){bin.mx=-ux;bin.mz=-uz;bin.dash=i%18===0&&gap<2.6;}`,
 c_shockcyc:`st.bo=true;if(!st.f){if(gap<2.3){in_.mx=-ux;in_.mz=-uz;}else if(i>3){in_.skill=true;st.f=i;}}else if(i-st.f<3)in_.skill=true;
   if(st.f&&i-st.f>=34&&i-st.f<37)bin.skill=true;else if(st.f&&i-st.f>=37){bin.mx=-ux;bin.mz=-uz;}`,
 c_giantchick:`st.bo=true;if(i>=4&&i<7)bin.skill=true;else if(i>8&&!st.c){bin.mx=-ux*0.45;bin.mz=-uz*0.45;}
   if(!st.c&&i>=34){in_.skill=true;st.c=i;}else if(st.c&&i-st.c<3)in_.skill=true;
   else if(!st.c&&i>8){const l=Math.hypot(me.x,me.z)||1;let ax=-ux,az=-uz;if(l>S.RING_R-1.3){ax=-me.z/l;az=me.x/l;}in_.mx=ax*0.6;in_.mz=az*0.6;}
   else if(st.c){const r=Math.hypot(o.x,o.z)||1;let ax=-o.z/r,az=o.x/r;ax-=o.x/r*0.25;az-=o.z/r*0.25;bin.mx=ax;bin.mz=az;go(0.8);}`,
 c_bumpflop:`st.bo=true;if(i>=4&&i<7)in_.skill=true;else if(i>8){const l=Math.hypot(me.x,me.z)||1;if(!st.b){in_.mx=me.x/l*0.8;in_.mz=me.z/l*0.8;if(l>S.RING_R-0.6)st.b=i;}}
   if(i>=16&&i<19)bin.skill=true;else if(i>19){bin.mx=-ux;bin.mz=-uz;}`,
 c_smokespin:`st.bo=true;if(i>=4&&i<7)in_.skill=true;else if(i>20){go();if(gap<0.4&&i%10<2)in_.push=true;}
   if(i>=12&&i<15)bin.skill=true;`,
 c_torprew:`st.bo=true;const l=Math.hypot(me.x,me.z)||1;
   if(!st.e){in_.mx=-ux;in_.mz=-uz;if(l>S.RING_R-1.4)st.e=i;}
   if(st.e&&!st.t&&i-st.e>8){o.f=Math.atan2(-uz,-ux);bin.skill=true;st.t=i;}else if(st.t&&i-st.t<3){o.f=Math.atan2(-uz,-ux);bin.skill=true;}`,
 c_bumpflop2:`st.bo=true;if(i>=4&&i<7)in_.skill=true;else if(i>8&&!st.l){const l=Math.hypot(me.x,me.z);if(l>0.5){in_.mx=-me.x/l*0.5;in_.mz=-me.z/l*0.5;}}
   if(i>=10&&i<13)bin.skill=true;else if(i>13&&o.st==='air'){bin.mx=-ux;bin.mz=-uz;}if(o.st==='recover')st.l=1;`,
 c_bumpflop3:`st.bo=true;const R0=+(window.BR||2.4);if(i>=4&&i<7)in_.skill=true;else if(i>8&&!st.l){const l=Math.hypot(me.x,me.z)||1,e=l-R0;if(Math.abs(e)>0.15){in_.mx=-me.x/l*Math.sign(e)*0.5;in_.mz=-me.z/l*Math.sign(e)*0.5;}}
   if(i>=10&&i<13)bin.skill=true;else if(i>13&&o.st==='air'){const l=Math.hypot(me.x,me.z)||1;const tx=me.x-me.x/l*0.7,tz=me.z-me.z/l*0.7,dx=tx-o.x,dz=tz-o.z,dl=Math.hypot(dx,dz)||1;bin.mx=dx/dl;bin.mz=dz/dl;}if(o.st==='recover')st.l=1;`,
 potato3:`st.bo=true;const pot=m.objs.find((q)=>q.type==='potato');const RR=S.RING_R-1.1;
   if(!pot){if(i>=4&&i<7)in_.skill=true;}
   else{const hm=pot.holder===0,Hw=hm?me:o,Rw=hm?o:me,hin=hm?in_:bin,rin=hm?bin:in_;let vx=Rw.x-Hw.x,vz=Rw.z-Hw.z;const vl=Math.hypot(vx,vz)||1;vx/=vl;vz/=vl;
     const ph=LOG.filter((l)=>l.indexOf('potatoPass')>0).length;st.dg=st.dg||{};
     if(Hw.st==='free'&&!(st.cw>i-28)&&pot.cd<-0.25){if(gap<2.7){hin.mx=vx;hin.mz=vz;hin.dash=true;st.cw=i;}else{hin.mx=vx*0.8;hin.mz=vz*0.8;}}
     if((Hw.st==='charge'||Hw.st==='wind'||Hw.st==='dash')&&gap<2.4&&!st.dg[ph]&&Rw.st==='free'){let px=-vz,pz=vx;if(px*Rw.x+pz*Rw.z>0){px=-px;pz=-pz;}rin.mx=px;rin.mz=pz;rin.dash=true;st.dg[ph]=i;}
     else if(Rw.st==='free'&&!(Hw.st==='charge'||Hw.st==='dash')){const r=Math.hypot(Rw.x,Rw.z)||1;let ax=vx,az=vz;if(r>RR){const tx=-Rw.z/r,tz=Rw.x/r,sg=Math.sign(tx*ax+tz*az)||1;ax=tx*sg-Rw.x/r*0.7;az=tz*sg-Rw.z/r*0.7;const q=Math.hypot(ax,az)||1;ax/=q;az/=q;}rin.mx=ax*0.55;rin.mz=az*0.55;}}`,
 claw:`if(m.skills&&m.skills[0]){in_.skill=i%6<2&&i>=2;}else{const l=Math.hypot(me.x,me.z)||1;if(gap<1.1){in_.dash=true;}else if(l>1){in_.mx=-me.x/l;in_.mz=-me.z/l;}}`,
};
(async()=>{const SS=+process.env.SS||1;const p=await L.open(1280,720,SS);if(SS>1)await p.evaluate((SS)=>{const R=S.game.R;R.prMax=SS;R.pr=SS;R.prFail=1e9;R.r.setPixelRatio(SS);R.resize&&R.resize();},SS);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const NAME=process.env.NAME||sk;await p.evaluate(({css,up})=>{const h=document.getElementById('hidevs');if(up&&h)h.textContent=h.textContent.replace('#unplug,','');window.SHOWUP=up;if(css){const e=document.createElement('style');e.id='x5css';e.textContent=css;document.head.appendChild(e);}},{css:process.env.CSS||'',up:!!process.env.SHOWUP});
const dir=(process.env.OUT||'../frames5/')+'g5_'+NAME;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sk,BO0,SK2,VIEW})=>{const g=S.game;window.STUB=1;window.ST={bo:BO0};window.PAI='normal';const m=bossStart(7);if(window.SHOWUP){const h=document.getElementById('hidevs');h.textContent=h.textContent.replace('#unplug,','');}g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;
  window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};window.BIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};const ai1=g.ctrls[1].src;g.ctrls[1].src={sample:(...a)=>{const r=ai1.sample(...a);return (window.ST&&ST.bo)?BIN:r;}};
  let k=0;while(m.phase!=='fight'&&k<2000){g.frame(g.last+33.333);k++;}for(let i=0;i<6;i++)g.frame(g.last+33.333);
  m.skills=[sk,SK2||null];if(VIEW)g.viewerIdx=+VIEW;g.awaitGacha=false;g.refreshSkills&&g.refreshSkills();window.STUB=0;window.M=m;window.ST={bo:BO0};window.FR=0;window.LOG=[];
  const em=m.emit.bind(m);m.emit=(t,d)=>{if(!/^(step|tick|sfx|palm|hit|brace|impact)$/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:'')+(t==='decided'&&d?' W'+(d.winner&&d.winner.idx):''));return em(t,d);};},{sk,BO0:!!process.env.BO0,SK2:process.env.SK2||'',VIEW:process.env.VIEW||''});
for(let i=0;i<8;i++)await p.evaluate(()=>{S.game.frame(S.game.last+33.333);});
const play=PLAY[process.env.PLAY||sk];await p.evaluate((br)=>{window.BR=br;},process.env.BR||'');const SK2=process.env.SK2||'';
for(let i=0;i<N;i++){await p.evaluate(({i,play,sk,SK2})=>{const g=S.game,m=M,me=m.w[0],o=m.w[1],st=ST,in_=VIN;Object.assign(in_,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});
   if(m.skills&&!m.skills[0]&&i<4&&!LOG.some((l)=>l.indexOf(" skillUse 0")>0))m.skills[0]=sk;if(SK2&&m.skills&&!m.skills[1]&&i<4&&!LOG.some((l)=>l.indexOf(" skillUse 1")>0))m.skills[1]=SK2;
   const bin=BIN;Object.assign(bin,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});const dx=o.x-me.x,dz=o.z-me.z,dl=Math.hypot(dx,dz)||1,ux=dx/dl,uz=dz/dl,gap=dl-me.r-o.r;const go=(s)=>{if(gap>0.3){in_.mx=ux*(s||1);in_.mz=uz*(s||1);}};
   (new Function('i','g','m','me','o','st','in_','ux','uz','gap','go','bin',play))(i,g,m,me,o,st,in_,ux,uz,gap,go,bin);
   g.frame(g.last+33.333);FR++;if(window.SHOWUP){const ue=document.getElementById('unplug'),on=!!(o.fxs&&o.fxs.unplug>0);ue.classList.toggle('on',on);if(on){ue.querySelector('.up-s').textContent='Your controller lost connection. Reconnecting…';ue.querySelector('.up-bar i').style.width=(100*(1-o.fxs.unplug/1.5))+'%';}}},{i,play,sk,SK2:process.env.SK2||''});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});}
fs.writeFileSync(dir+'.log',(await p.evaluate(()=>LOG)).join('\n'));console.log(sk,'done');process.exit(0);})();
