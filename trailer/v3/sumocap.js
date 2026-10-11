// replay a scanned AI-vs-AI match to a frame window and record it (default game camera)
const L=require('../lib.js'),fs=require('fs');
const [,, name, seed, startF, nF, mode, arena]=process.argv;
(async()=>{
  const preview=mode==='preview'; const big=mode==='big'||mode==='bigprev'; const W=preview?640:1280,H=preview?360:720;
  const dir=(preview||mode==='bigprev'?'../prev/':'../frames/')+name; fs.mkdirSync(dir,{recursive:true});
  const p=await L.open(W,H,1);
  await p.evaluate(({seed,startF,arena})=>{
    const g=S.game; window.requestAnimationFrame=()=>0; g.camp=null; S.profile.rules='pure'; S.profile.stage=arena||'bath';
    const bn=document.getElementById('bnr'); if(bn) bn.style.display='none';
    const st=document.createElement('style'); st.textContent='#fx2d,#gacha,#callouts,#banner,#kimarite,#hint,#clinchHint,#blindOv,#hud,#bnr,.slash{display:none!important}'; document.head.appendChild(st);
    const R=g.R; R.render=()=>{}; R.update=()=>{};
    const nArch=S.ARCH.length; const sd=+seed; S.setSeed(sd*7919); const a=sd%nArch; let b=(sd*3+1)%nArch; if(b===a) b=(a+1)%nArch;
    g.sel={mode:'cpu',c1:a,c2:b,lock1:false,lock2:false}; g.mode='game'; g.paused=false; g.ui.hide(); g.ui.showHud(false);
    g.setupMatch(a,b,'attract'); g.last=performance.now();
    const lead=Math.max(0,+startF-22); for(let f=0;f<lead;f++) g.frame(g.last+33.333);
    delete R.render; delete R.update; window.G_LEFT=+startF-lead;
  },{seed,startF:+startF,arena});
  // render-only lead-in so the camera settles, then the window
  const lead=await p.evaluate(()=>window.G_LEFT);
  for(let i=0;i<lead;i++) await p.evaluate(()=>S.game.frame(S.game.last+33.333));
  for(let i=0;i<+nF;i++){
    await p.evaluate(()=>S.game.frame(S.game.last+33.333));
    if(!preview||i%2===0||big) await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:preview?70:90});
  }
  console.log(name,'done'); await p.close(); process.exit(0);
})();
