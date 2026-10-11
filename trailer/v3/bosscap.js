// boss bout, AI on both sides, game's own camera, no HUD/callouts.
// scan mode: node bosscap.js scan FROM TO out.json   -> per seed: events + frame where the box bursts
// cap mode:  node bosscap.js cap NAME SEED START N [preview]
const L=require('../lib.js'),fs=require('fs');
const a=process.argv.slice(2);
const SETUP=`window.bossStart=(sd)=>{const g=S.game;window.requestAnimationFrame=()=>0;
  const st=document.getElementById('hidevs')||document.createElement('style');st.id='hidevs';st.textContent='#fx2d,#gacha,#callouts,#banner,#kimarite,#hint,#clinchHint,#blindOv,#hud,#bnr,.slash,#stealthHud,.callout,#vhs,#combo,#tutPanel,#trainPanel,#shopUi,#yen,#record,#debug,#unplug,#rounds,#roundLbl{display:none!important}';document.head.appendChild(st);
  const R=g.R;if(!R.__wrapped){R.__wrapped=1;let b=12345;const rr=()=>{b|=0;b=b+0x6D2B79F5|0;let t=Math.imul(b^b>>>15,1|b);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};
    for(const k of ['update','render']){const f=R[k].bind(R);R['__'+k]=f;R[k]=function(){if(window.STUB)return;const o=Math.random;Math.random=rr;try{return f.apply(null,arguments);}finally{Math.random=o;}};}}
  S.setSeed(sd*7919);seed(sd);g.bossBox=true;g.startBossBout(F.c);g.last=performance.now();const m=g.match;
  const ai=new S.AI(m.w[0],m,window.PAI||'normal',{noLearn:true});g.ais.push(ai);g.ctrls[0].src=ai;
  return m;};`;
(async()=>{
  const mode=a[0];
  if(mode==='scan'){
    const p=await L.open(480,270);await L.boot(p,5);await p.evaluate(SETUP);
    const res=await p.evaluate(({from,to})=>{const g=S.game;window.STUB=1;const out={};
      for(let sd=from;sd<=to;sd++){const m=bossStart(sd);const log=[];let fr=0;const em=m.emit.bind(m);
        m.emit=(t,d)=>{log.push([fr,t,d&&d.w?d.w.idx:d&&d.winner?'W'+d.winner.idx:-1]);return em(t,d);};
        let burst=-1,fight=-1;
        for(fr=0;fr<2400;fr++){g.frame(g.last+33.333);if(fight<0&&m.phase==='fight')fight=fr;if(burst<0&&!g.bossBox)burst=fr;if(g.match!==m)break;if(burst>=0&&fr>burst+90)break;}
        out[sd]={fight,burst,frames:fr,log:log.filter(e=>!['step','tick','sfx'].includes(e[1]))};}
      return out;},{from:+a[1],to:+a[2]});
    fs.writeFileSync(a[3],JSON.stringify(res));console.log('scanned');process.exit(0);
  }
  const [,name,sd,start,n,pv]=a;const preview=pv==='preview';
  const p=await L.open(preview?640:1280,preview?360:720);await L.boot(p,5);await p.evaluate(SETUP);
  const dir=(preview?'../prev/':'../frames/')+name;fs.mkdirSync(dir,{recursive:true});
  await p.evaluate(({sd,start})=>{const g=S.game;window.STUB=1;const m=bossStart(sd);window.DEC=-1;window.FR=0;const em=m.emit.bind(m);m.emit=(t,d)=>{if(t==='decided'&&DEC<0)DEC=FR;return em(t,d);};const lead=Math.max(0,start-20);for(let f=0;f<lead;f++){g.frame(g.last+33.333);FR++;}window.STUB=0;window.LEFT=start-lead;},{sd:+sd,start:+start});
  const left=await p.evaluate(()=>window.LEFT);for(let i=0;i<left;i++)await p.evaluate(()=>{S.game.frame(S.game.last+33.333);FR++;});
  let k=0;for(let i=0;i<+n;i++){await p.evaluate(()=>{S.game.frame(S.game.last+33.333);FR++;});if(!preview||i%3===0)await p.screenshot({path:`${dir}/f_${String(k++).padStart(4,'0')}.jpg`,type:'jpeg',quality:preview?70:90});}
  console.log(name,'done',k,'decided at',await p.evaluate(()=>DEC));process.exit(0);
})();
