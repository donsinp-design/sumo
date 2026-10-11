const L=require('../lib.js');const T=require('./takes.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);await p.evaluate(T.HELP);
const r=await p.evaluate(()=>{const F=window.F,c=F.c;c.outOfBath=true;F.at(2.5,-30.3,Math.PI/2,0);const out=[];for(let k=0;k<600;k++){c.ctrl.update(1/60);c.step(1/60);if(k%60===0){const d=H.danger(c,0.5);out.push(k+' '+(d?c.npcs.indexOf(d)+' '+d.a.x.toFixed(1)+','+d.a.z.toFixed(1)+' f'+d.a.f.toFixed(2):'-'));}}return out;});
console.log(r.join('\n'));process.exit(0);})();
