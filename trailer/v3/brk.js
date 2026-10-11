const L=require('../lib.js');
(async()=>{const p=await L.open(320,180);await L.boot(p,8);
const r=await p.evaluate(()=>F.c.breakables.filter(B=>!B.s.f).map(B=>B.s.k+' x '+B.s.x0.toFixed(1)+'..'+B.s.x1.toFixed(1)+' z '+B.s.z0.toFixed(1)+'..'+B.s.z1.toFixed(1)).join('\n'));
console.log(r);process.exit(0);})();
