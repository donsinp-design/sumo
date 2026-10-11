const L=require('../lib.js');
(async()=>{const p=await L.open(640,360);await L.boot(p,2);await p.evaluate(require('./takes.js').HELP);
const r=await p.evaluate(()=>{const c=window.F.c;return {w:c.walls.filter(w=>w.z1>-62&&w.z0<-41.5&&w.x1>-14&&w.x0<14).map(w=>[w.x0,w.x1,w.z0,w.z1,w.tall?1:0].map(v=>+v.toFixed(1))),n:c.npcs.map((n,i)=>i+' '+n.a.kind+' '+n.room+' '+n.a.x.toFixed(1)+','+n.a.z.toFixed(1)+' r'+n.range),carts:c.carts.map(q=>q.x.toFixed(1)+','+q.z.toFixed(1))};});
console.log(JSON.stringify(r));process.exit(0);})();
