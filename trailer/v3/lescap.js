// a training lesson, but in the boss match (YOU vs YUNOFUJI, bath stage, bare): the lesson's partner drives the boss; the player's buttons are
// pressed the way a person would, on the game's own NOW cue. Game camera, no HUD.  node lescap.js NAME "LESSON TITLE" N [preview]
const L=require('../lib.js'),fs=require('fs');
const [,,name,title,nn,pv]=process.argv;const N=+nn||110;const preview=pv==='preview';
const PLAY={
 'DASH':`st.h=(st.h||0)+1;const k=Math.floor(st.h/22),ph=st.h%22;if(ph<3){const a=[1.57,-1.57,0,3.14][k%4];in_.mx=Math.cos(a);in_.mz=Math.sin(a);in_.dash=ph===0;}`,
 'PUSH':`if(gap>0.35)go();else{st.h=(st.h||0)+1;in_.push=st.h%14<2;}`,
 'FLURRY':`if(gap>0.35&&!st.h)go();else{st.h=(st.h||0)+1;in_.push=st.h%4<2;}`,
 'HEAVY SHOVE':`st.h=(st.h||0)+1;if(st.h<6){}else if(!st.rel){in_.push=true;if(st.h>18){if(gap>0.25)go(0.6);else st.rel=1;}}`,
 'CHARGE':`if(!st.c){go();if(gap<1.5){in_.push=true;st.c=1;}}`,
 'RING OUT':`go();st.h=(st.h||0)+1;in_.push=gap<0.4&&st.h%10<2;`,
 'DRIVE':`if(!c){go(0.5);if(gap<0.45&&!st.g){st.g=1;in_.grab=true;}}else{in_.mx=ux;in_.mz=uz;}`,
 'THROW':`if(!c){go(0.4);if(gap<0.45)st.k=1;in_.grab=!!st.k;}else{st.h=(st.h||0)+1;in_.grab=st.h<30;if(st.h<30){in_.mx=-uz;in_.mz=ux;}}`,
 'WRIGGLE FREE':`st.h=(st.h||0)+1;if(me.lifted||(c&&c.lift)){in_.push=st.h%3===0;in_.grab=st.h%3===1;in_.dash=st.h%3===2;}`,
 'SHOVE OFF':`if(!c){go(0.4);if(gap<0.45&&!st.g){st.g=1;in_.grab=true;}}else{st.h=(st.h||0)+1;in_.push=st.h>14&&st.h<17;}`,
 'LET GO':`if(!c){go(0.4);if(gap<0.45&&!st.g){st.g=1;in_.grab=true;}}else{st.h=(st.h||0)+1;in_.dash=st.h>18&&st.h<21;}`,
 'EDGE SAVE':`st.h=(st.h||0)+1;in_.grab=st.h<34;if(st.h<34){in_.mx=-ux;in_.mz=-uz;}`,
 'STOP SHORT':`if(!st.c){go();if(gap<1.7){in_.push=true;st.c=1;}}else{st.c++;in_.dash=st.c>5&&st.c<8;}`,
 'FROM BEHIND':`if(!st.d){if(o.st==='charge'&&gap<1.3){in_.mx=-uz;in_.mz=ux;in_.dash=true;st.d=1;}}else{st.d++;if(st.d>14){go();in_.push=gap<0.5&&st.d%8<2;}}`,
 'ESCAPE A THROW':`if(c){st.h=(st.h||0)+1;in_.dash=st.h>10&&st.h<13;}`,
 'SPIN':`if(!c){go(0.4);if(gap<0.45)st.k=1;in_.grab=!!st.k;}else{st.h=(st.h||0)+1;in_.grab=st.h<48;if(st.h<48){in_.mx=-ux;in_.mz=-uz;}}`,
 'SLAP DOWN':`if(now>=0&&now<3){in_.mx=-ux;in_.mz=-uz;in_.push=true;}`,
 'GRAB BREAK':`if(now>=0&&now<3)in_.grab=true;`,
 'PARRY':`if(now>=0&&now<3)in_.dash=true;`,
 'CATCH':`if(now>=0&&now<3)in_.grab=true;`,
 'SLAM':`if(!c&&!st.lift){go(0.4);if(gap<0.45&&!st.g){st.g=1;in_.grab=true;}}else{st.h=(st.h||0)+1;if(st.h<16)in_.grab=true;else if(st.h>42&&st.h<45)in_.grab=true;}`,
 'BRACE':`if(!st.b&&o.st==='charge'&&gap<1.5)st.b=1;if(st.b&&st.b<26){st.b++;in_.dash=true;}`,
 'LEG TRIP':`if(!c){go(0.4);if(gap<0.45)st.k=1;in_.grab=!!st.k;}else{const tr=c.evalTech(me,'trip');in_.mx=ux;in_.mz=uz;st.h=(st.h||0)+1;in_.grab=!(st.h>8&&tr&&tr.ok&&tr.sc>0.34)&&!st.rel;if(!in_.grab)st.rel=1;}`,
 'THROAT PUSH':`if(gap>0.35&&!st.h)go(0.4);else{st.h=(st.h||0)+1;in_.dash=st.h<20;in_.push=st.h>=8&&st.h<11;}`,
 'SIDESTEP':`if(now>=0&&now<3){in_.mx=-uz;in_.mz=ux;in_.dash=true;}`,
 'LIFT':`if(!c&&!st.l){go(0.4);if(gap<0.45&&!st.g){st.g=1;in_.grab=true;}}else{st.l=1;st.h=(st.h||0)+1;if(st.h<16)in_.grab=true;else if(st.h>22){in_.mx=ux;in_.mz=uz;}}`,
 'FACE-OFF':`st.h=(st.h||0)+1;const seq=[['push',20],['grab',50],['mz',-1,80],['mx',-1,110],['mz',1,140],['mx',1,170],['push',200],['grab',230]];for(const q of seq){const at=q[q.length-1];if(st.h>=at&&st.h<at+3){if(q.length===2)in_[q[0]]=true;else in_[q[0]]=q[1];}}`,
 'STAY IN':`st.h=(st.h||0)+1;if(st.h>3){const l=Math.hypot(me.x,me.z)||1;in_.mx=-me.x/l;in_.mz=-me.z/l;}`,
};
(async()=>{const p=await L.open(preview?640:1280,preview?360:720);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const dir=(preview?'../prev/':'../frames3/')+name;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
const ok=await p.evaluate(({title})=>{const g=S.game;window.STUB=0;const m=bossStart(7);g.bossBox=false;if(g.R.bossG)g.R.bossG.box=false;
  g.ais=[];g.dummy=new S.Dummy();g.dummy.me=m.w[1];g.ctrls[1].src=g.dummy;window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};
  g.tut=new S.Tutorial(g);let i=0;while(true){g.tut.i=i;const Ls=g.tut.lesson();if(!Ls)return 'no lesson';if(Ls.title===title)break;i++;}
  g.tut.begin(i);window.NOWF=-1;window.FR=0;const cal=g.ui.callout.bind(g.ui);g.ui.callout=(t,...a)=>{if(t==='NOW!')NOWF=FR;return cal(t,...a);};
  window.ST={};window.LOG=[];const em=m.emit.bind(m);m.emit=(t,d)=>{if(!/^(step|tick|sfx)$/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:'')+(t==='decided'&&d?' W'+(d.winner&&d.winner.idx)+' '+(d.km||'')+' '+(d.cause||''):'')+(t==='throw'&&d?' '+d.name:''));return em(t,d);};return 'ok';},{title});
if(ok!=='ok'){console.log(ok);process.exit(1);}
const play=PLAY[title];let k=0;
for(let i=0;i<N;i++){await p.evaluate((play)=>{const g=S.game,m=g.match,me=m.w[0],o=m.w[1],c=m.clinch,st=ST;const in_=VIN;Object.assign(in_,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false});
   const dx=o.x-me.x,dz=o.z-me.z,dl=Math.hypot(dx,dz)||1,ux=dx/dl,uz=dz/dl,gap=dl-me.r-o.r,now=NOWF>=0?FR-NOWF:-1;const go=(s)=>{if(gap>0.3){in_.mx=ux*(s||1);in_.mz=uz*(s||1);}};
   (new Function('g','m','me','o','c','st','in_','ux','uz','gap','now','go',play))(g,m,me,o,c,st,in_,ux,uz,gap,now,go);
   g.frame(g.last+33.333);FR++;},play);
 if(!preview||i%3===0)await p.screenshot({path:`${dir}/f_${String(k++).padStart(4,'0')}.jpg`,type:'jpeg',quality:preview?70:90});}
fs.writeFileSync(dir+'.log',(await p.evaluate(()=>LOG)).join('\n'));console.log(name,'done',k);process.exit(0);})();
