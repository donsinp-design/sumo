// trailer capture harness: drives the real game frame by frame and screenshots each frame
const {chromium}=require(process.env.PW||'playwright');
const fs=require('fs');
exports.open=async function(w=1280,h=720,dsf=1){
  const b=await chromium.launch({args:process.env.SWGL?['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']:['--enable-webgl','--ignore-gpu-blocklist','--enable-gpu']});
  const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:dsf});
  p.on('pageerror',e=>console.log('PAGEERR',e.message));
  await p.goto('http://127.0.0.1:8896/dist-kumitegame/index.html');
  await p.waitForFunction(()=>window.S&&S.Chars&&S.Chars.ready&&S.SoftSumo&&S.SoftSumo.loaded&&S.loadBathKit,null,{timeout:90000});
  await p.evaluate(async()=>{ await S.loadBathKit(); });
  await p.evaluate(()=>{
    // seeded randomness, so a take can be repeated exactly
    window.seed=(s)=>{let a=s>>>0;Math.random=()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};};
    const g=S.game; g.settings.hudGuide=false; g.settings.hudTips=false; g.settings.hudCtx=false; g.settings.hudGoal=false;
    window.F={UP:3,g,inp:{mx:0,mz:0,push:false,grab:false,dash:false,skill:false},
      boot(sd){ seed(sd||1); g.camp=new S.Stealth(g); F.c=g.camp; F.c.start(); F.c.ctrl=new S.Controller({sample:()=>F.inp}); window.requestAnimationFrame=()=>0; document.getElementById('vignette')&&(document.getElementById('vignette').style.display='none'); F.c.hud.querySelector('.st-help')&&(F.c.hud.querySelector('.st-help').style.display='none'); return F.c; },
      tick(dt){ F.c.frame(dt||1/30); },
      at(x,z,f,y){ const c=F.c,P=c.P; P.x=x;P.z=z;P.y=y||0;P.f=f===undefined?0:f;P.vx=P.vz=0;P.st='free';P.t=0;P.dur=0;c.noGuard=true;c.grace=99;c.camT.set(Math.max(-18,Math.min(18,x*0.8)),P.y,z-2.6); },
      npcAt(n,x,z,f){ const a=n.a; a.x=x;a.z=z;a.f=f;a.y=z<-61?3:0; n.mode='route'; n.route=[[x,z,999,f]]; n.i=0; n.wait=999; n.path=null; n.hold=0; n.alarm=0; },
      park(keep){ // every other staff member: out of the way, standing still
        F.c.npcs.forEach((n,i)=>{ if(keep.includes(n)) return; n.hold=1e6; n.a.x=-60-i*3; n.a.z=-100; n.mode='route'; n.alarm=0; }); },
      cam(x,z,y,dist,h,flip){ F.c.camFocus={x,z,y:y||0,dist:dist||11,h:h||0.62,flip:!!flip}; },
      quiet(){ const c=F.c; c.think=()=>{}; const e=c.el('.st-think'); if(e)e.style.display='none'; },
      item(i,x,z,y){ const b=F.c.buckets[i]; b.state='floor'; b.m.position.set(x,y||0,z); b.m.rotation.set(0,0,0); b.x0=x;b.z0=z;b.base=y||0;b.y=y||0; b.m.visible=true; return b; },
      box(){ const c=F.c; c.outOfBath=true; c.wearing=true; c.pantsBox.visible=false; c.wearBox(); },
      pad(o){ Object.assign(F.inp,{mx:0,mz:0,push:false,grab:false,dash:false,skill:false},o||{}); },
      cap(t,s){ let e=document.getElementById('cap'); if(!e){ e=document.createElement('div'); e.id='cap'; e.style.cssText='position:fixed;left:3.4vw;bottom:9vh;z-index:99;font:400 4vw "Dela Gothic One",sans-serif;color:#fffaf0;background:#14101a;padding:.3vw 1.6vw .6vw;transform:rotate(-2deg);letter-spacing:.03em;display:none'; document.body.appendChild(e);} if(!t){e.style.display='none';return;} e.textContent=t; e.style.display='block'; },
      card(html,bg){ let e=document.getElementById('card'); if(!e){ e=document.createElement('div'); e.id='card'; e.style.cssText='position:fixed;inset:0;z-index:98;display:none;align-items:center;justify-content:center;flex-direction:column;text-align:center;color:#fffaf0;font:400 7vw "Dela Gothic One",sans-serif;letter-spacing:.04em'; document.body.appendChild(e);} if(html===null){e.style.display='none';return;} e.innerHTML=html; e.style.background=bg||'#000'; e.style.display='flex'; },
      fade(a){ let e=document.getElementById('fade'); if(!e){ e=document.createElement('div'); e.id='fade'; e.style.cssText='position:fixed;inset:0;z-index:97;background:#fff;opacity:0;pointer-events:none'; document.body.appendChild(e);} e.style.opacity=a; }
    };
  });
  return p;
};
let frameNo=0;
exports.shot=async function(p,dir,name,n,fn,opts={}){
  fs.mkdirSync(dir,{recursive:true});
  for(let i=0;i<n;i++){
    await p.evaluate(({i,n,fn})=>{ (new Function('i','n','F','return ('+fn+')(i,n,F)'))(i,n,F); },{i,n,fn:fn.toString()});
    await p.screenshot({path:`${dir}/${name}_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:88});
  }
};

exports.boot=async function(p,sd){
  await p.evaluate((sd)=>{F.boot(sd);const b=document.getElementById('bnr');if(b)b.style.display='none'; F.g.ui.hide&&F.g.ui.hide(); document.body.classList.remove('wmm-title'); document.querySelectorAll('.wmm-wrap,.menu,.pause-wrap').forEach(e=>e.style.display='none'); const st=document.createElement('style'); st.textContent='#overlay,.wmm-wrap,.wmm-logo,#menu{display:none!important} #stealthHud .st-map,#stealthHud .st-bonus,#stealthHud .st-obj,#stealthHud .st-help,#stealthHud .st-hp,#stealthHud .st-stam,#stealthHud .st-ctx,#stealthHud .st-tip,#stealthHud .st-maparrow,#stealthHud .st-safe,#stealthHud .st-oni,#stealthHud .st-wake,#stealthHud .st-think,#stealthHud .st-ko{display:none!important}'; document.head.appendChild(st);},sd);
  await p.waitForFunction(()=>F.c.breakables&&F.c.breakables.length>0,null,{timeout:60000});
};
