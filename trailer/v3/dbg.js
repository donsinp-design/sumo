const L=require('../lib.js');const T=require('./takes.js');const tk=T.shove2;
(async()=>{const p=await L.open(480,270);await L.boot(p,tk.seed);await p.evaluate(T.HELP);
await p.evaluate(`(()=>{const F=window.F;F.c.asleep=false;F.take={};(${tk.setup.toString()})(F);})()`);
const out=await p.evaluate(`(()=>{const F=window.F,c=F.c,sc=${tk.script.toString()};const r=["pre "+c.npcs[9].mode+" "+c.npcs.map((n,i)=>n.mode==="chase"?i:"").join("")];for(let k=0;k<40;k++){sc(k/60,F);c.ctrl.update(1/60);c.step(1/60);const P=c.P,n=c.npcs[9];r.push(k+' st'+P.st+' bh'+(P.boxHide?1:0)+' nd'+(c.noDuck||0).toFixed(2)+' I'+(c.keys.KeyI?1:0)+' w'+(c.wearing?1:0)+' n9 '+n.mode+' al'+n.alarm.toFixed(2)+' g'+c.grace.toFixed(2));}return r;})()`);
console.log(out.join('\n'));process.exit(0);})();
