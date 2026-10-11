const L=require('../lib.js');
(async()=>{const p=await L.open(320,180);await L.boot(p,8);
const r=await p.evaluate(()=>F.c.walls.filter(w=>w.z1>-48&&w.z0<-36&&w.x1>-14&&w.x0<14).map(w=>'x '+w.x0.toFixed(1)+'..'+w.x1.toFixed(1)+' z '+w.z0.toFixed(1)+'..'+w.z1.toFixed(1)+(w.tall?' T':'')+(w.y0!==undefined?' y'+w.y0:'')).join('\n'));
console.log(r);process.exit(0);})();
