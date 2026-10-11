// scan AI-vs-AI sumo matches for named moments: logs [frame, event, matchtime, wrestler] per seed
const L=require('../lib.js'),fs=require('fs');
const [,, from, to, outf]=process.argv;
(async()=>{
  const p=await L.open(480,270);
  const res=await p.evaluate(({from,to})=>{
    const g=S.game; window.requestAnimationFrame=()=>0; g.camp=null; S.profile.rules='pure'; S.profile.stage='bath';
    const R=g.R; R.render=()=>{}; R.update=()=>{};
    const out={}; const nArch=S.ARCH.length;
    for(let sd=from;sd<=to;sd++){
      S.setSeed(sd*7919); const a=sd%nArch; let b=(sd*3+1)%nArch; if(b===a) b=(a+1)%nArch;
      g.sel={mode:'cpu',c1:a,c2:b,lock1:false,lock2:false}; g.mode='game'; g.paused=false; g.ui.hide(); g.ui.showHud(false);
      g.setupMatch(a,b,'attract'); g.last=performance.now(); const m=g.match; const log=[]; const em=m.emit.bind(m);
      let fr=0; m.emit=(t,d)=>{ log.push([fr,t,+(m.time||0).toFixed(2),d&&d.w?d.w.idx:-1]); return em(t,d); };
      for(fr=0;fr<1500;fr++){ g.frame(g.last+33.333); if(g.match!==m||m.phase==='over') break; }
      out[sd]={a,b,frames:fr,log};
    }
    return out;
  },{from:+from,to:+to});
  fs.writeFileSync(outf,JSON.stringify(res));
  console.log('scanned',Object.keys(res).length);
  process.exit(0);
})();
