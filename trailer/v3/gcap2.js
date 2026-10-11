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
 claw:`if(m.skills&&m.skills[0]){in_.skill=i%6<2&&i>=2;}else{const l=Math.hypot(me.x,me.z)||1;if(gap<1.1){in_.dash=true;}else if(l>1){in_.mx=-me.x/l;in_.mz=-me.z/l;}}`,
};
(async()=>{const SS=+process.env.SS||1;const p=await L.open(1280,720,SS);if(SS>1)await p.evaluate((SS)=>{const R=S.game.R;R.prMax=SS;R.pr=SS;R.prFail=1e9;R.r.setPixelRatio(SS);R.resize&&R.resize();},SS);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const dir=(process.env.OUT||'../frames5/')+'g5_'+sk;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sk})=>{const g=S.game;window.STUB=1;window.PAI='normal';const m=bossStart(7);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;
  window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};
  let k=0;while(m.phase!=='fight'&&k<2000){g.frame(g.last+33.333);k++;}for(let i=0;i<6;i++)g.frame(g.last+33.333);
  m.skills=[sk,null];g.awaitGacha=false;g.refreshSkills&&g.refreshSkills();window.STUB=0;window.M=m;window.ST={};window.FR=0;window.LOG=[];
  const em=m.emit.bind(m);m.emit=(t,d)=>{if(!/^(step|tick|sfx|palm|hit|brace|impact)$/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:'')+(t==='decided'&&d?' W'+(d.winner&&d.winner.idx):''));return em(t,d);};},{sk});
for(let i=0;i<8;i++)await p.evaluate(()=>{S.game.frame(S.game.last+33.333);});
const play=PLAY[sk];
for(let i=0;i<N;i++){await p.evaluate(({i,play,sk})=>{const g=S.game,m=M,me=m.w[0],o=m.w[1],st=ST,in_=VIN;Object.assign(in_,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});
   if(m.skills&&!m.skills[0]&&i<4&&!LOG.some((l)=>l.indexOf(" skillUse 0")>0))m.skills[0]=sk;
   const dx=o.x-me.x,dz=o.z-me.z,dl=Math.hypot(dx,dz)||1,ux=dx/dl,uz=dz/dl,gap=dl-me.r-o.r;const go=(s)=>{if(gap>0.3){in_.mx=ux*(s||1);in_.mz=uz*(s||1);}};
   (new Function('i','g','m','me','o','st','in_','ux','uz','gap','go',play))(i,g,m,me,o,st,in_,ux,uz,gap,go);
   g.frame(g.last+33.333);FR++;},{i,play,sk});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});}
fs.writeFileSync(dir+'.log',(await p.evaluate(()=>LOG)).join('\n'));console.log(sk,'done');process.exit(0);})();
