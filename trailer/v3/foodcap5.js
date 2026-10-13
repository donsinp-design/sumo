// the title screen's food rain, no menu/logo: S.WMM.frame driven at 30 fps (v5: local playwright, GPU, out dir via OUT)
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch({args:process.env.SWGL?['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']:['--enable-webgl','--ignore-gpu-blocklist','--enable-gpu']});
const SS=+process.env.SS||1;const p=await b.newPage({viewport:{width:1280,height:720},deviceScaleFactor:SS});
await p.goto('http://127.0.0.1:8896/dist-kumitegame/index.html');await p.waitForFunction(()=>window.S&&S.WMM&&S.game&&S.game.R,null,{timeout:90000});
await p.waitForTimeout(4000);
await p.evaluate(()=>{window.requestAnimationFrame=()=>0;const st=document.createElement('style');st.textContent='.wmm-wrap,.menu,.wmm-logo,#bnr,#hint,#overlay>*:not(canvas),.pause-wrap,.foot,.wmm-foot{display:none!important}';document.head.appendChild(st);S.game.ui.name='title';});
const dir=(process.env.OUT||'../v5/')+'food';fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
for(let i=0;i<60;i++)await p.evaluate(()=>S.WMM.frame(1/30,S.game.R));
const N=+process.env.N||150;
for(let i=0;i<N;i++){await p.evaluate(()=>S.WMM.frame(1/30,S.game.R));await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});}
console.log('food done',N);await b.close();})();
