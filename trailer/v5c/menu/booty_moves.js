const L=require('./lib.js');
(async()=>{const OUT=process.argv[2];const p=await L.open(1920,1080,2);
await p.evaluate(()=>{const R=S.game.R;R.prMax=2;R.pr=2;R.prFail=1e9;R.r.setPixelRatio(2);R.resize&&R.resize();});
await p.evaluate(()=>{const g=S.game;window.requestAnimationFrame=()=>0;
  const st=document.createElement('style');st.textContent='#hud,#overlay,.wmm-wrap,#bnr,#hint,#callouts,#banner,#gacha,#rounds,#roundLbl,#kimarite,#stealthHud,#fx2d,#combo,#yen,#record{display:none!important}';document.head.appendChild(st);
  g.ui.hide&&g.ui.hide();g.setupMatch(0,1,'cpu');g.mode='game';g.R.setStage('dohyo');g.match.stage='dohyo';g.last=performance.now();
  for(let i=0;i<20;i++)g.frame(g.last+33.333);});
const info=await p.evaluate(()=>{const m=S.game.match;return m.w.map(w=>[w.x.toFixed(2),w.z.toFixed(2),w.f.toFixed(2),m.phase]);});
console.log(JSON.stringify(info));
const N=+process.env.N||110,BGC=process.env.BG==='white'?0xf7f5f0:0x0b0a0d;const fs=require('fs');fs.mkdirSync(OUT,{recursive:true});
await p.evaluate(()=>{const g=S.game,m=g.match;window.VIN={mx:0,mz:0,push:false,grab:false,dash:false,skill:false};g.ctrls[0].src={sample:()=>VIN};g.ais=g.ais.filter(a=>a.me!==m.w[0]);window.LOG=[];window.FR=0;const em=m.emit.bind(m);m.emit=(t,d)=>{if(/stomp|clap|taunt/.test(t))LOG.push(FR+' '+t+' '+(d&&d.w?d.w.idx:''));return em(t,d);};if(m.goAt<20)m.goAt=30;});
for(let i=0;i<N;i++){
 await p.evaluate(({i,bg})=>{window.CD=2.5;window.CH=0.62;window.CL=0.5;VIN.grab=false;VIN.push=(i===30||i===31);VIN.mx=(i===60||i===61)?1:(i===90||i===91)?-1:0;VIN.mz=(i===120||i===121)?1:0;
const g=S.game,R=g.R,m=g.match,w=m.w[0];
  R.views[1]&&(R.views[1].root.visible=false);R.scene.background.set(bg);
  // behind wrestler 0, low, looking at the seat and legs
  const fx=Math.cos(w.f),fz=Math.sin(w.f),D=+(window.CD||3.0),bx=w.x-fx*D,bz=w.z-fz*D;
  if(!window.CAMF){window.CAMF={p:[bx,+(window.CH||0.75),bz],l:[w.x,+(window.CL||0.6),w.z]};}R.camOverride=CAMF;
  g.frame(g.last+33.333);FR++;
  // after the game's own update: hide everything but the ring mound (clay + straw) and him, then draw the frame
  const keep=new Set([R.dohyoG,R.views[0].root]);
  for(const o of R.scene.children){if(keep.has(o)){o.visible=true;continue;}if(o.isLight||o.isCamera)continue;o.visible=false;}
  R.dohyoG.traverse((o)=>{o.visible=true;});
  // plain clay top: the ring texture's painted lines (ring circle, start lines) painted over in its own clay colour
  if(!window.CLAYED&&R.ringTex&&R.ringTex.image){const cv=R.ringTex.image,cx=cv.getContext('2d'),Wd=cv.width,px=cx.getImageData(Math.round(Wd*0.5),Math.round(Wd*0.62),1,1).data;
    const img=cx.getImageData(0,0,Wd,Wd),d=img.data;for(let q=0;q<d.length;q+=4){const lum=d[q]+d[q+1]+d[q+2];if(lum>3*215||Math.abs(d[q]-px[0])+Math.abs(d[q+1]-px[1])+Math.abs(d[q+2]-px[2])>60){d[q]=px[0];d[q+1]=px[1];d[q+2]=px[2];}}
    cx.putImageData(img,0,0);R.ringTex.needsUpdate=true;window.CLAYED=1;}
  // no lines on the mound: the ring's straw circle stays, the painted ring line and the two start lines go
  R.dohyoG.traverse((o)=>{if(!o.isMesh)return;const bb=new THREE.Box3().setFromObject(o),h=bb.max.y-bb.min.y,wx=bb.max.x-bb.min.x,wz=bb.max.z-bb.min.z;
    if(h<0.03&&bb.min.y>0.004)o.visible=false;            // painted ring line (sits just above the clay)
    if(h<0.05&&Math.min(wx,wz)<0.2&&Math.max(wx,wz)<1.5)o.visible=false;});   // the shikiri start lines
  R.cam.updateMatrixWorld();
  if(R.anime&&R.post)R.post.render(R.scene,R.cam,R.time);else R.r.render(R.scene,R.cam);},{i,bg:BGC});
 await p.screenshot({path:OUT+'/f_'+String(i).padStart(4,'0')+'.jpg',type:'jpeg',quality:92});}
fs.writeFileSync(OUT+'.log',(await p.evaluate(()=>LOG)).join('\n'));console.log('clip done');process.exit(0);})();
