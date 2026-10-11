const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const F=window.F,c=F.c;c.outOfBath=true;F.at(9,-61.8,-Math.PI/2,3);c.grace=0;c.noGuard=false;const P=c.P;
 c.spill(9,-57.6,0);const q=c.puddles[c.puddles.length-1];const n=c.npcs[4];n.a.x=9;n.a.z=-53.8;n.a.y=0;c.startChase(n);
 const out=['puddle y '+q.y.toFixed(2)+' floorY '+c.constructor.name];
 for(let k=0;k<180;k++){c.ctrl.update(1/60);c.step(1/60);if(k%10===0)out.push(k+' n '+n.a.x.toFixed(1)+','+n.a.z.toFixed(1)+' y'+n.a.y.toFixed(2)+' v'+Math.hypot(n.a.vx,n.a.vz).toFixed(1)+' '+n.a.st+' '+n.mode);}
 return out;});
console.log(r.join('\n'));process.exit(0);})();
