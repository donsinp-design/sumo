const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const c=window.F.c;return {b:c.buckets.filter(b=>b.state==='floor'&&b.m.position.z>-45&&b.m.position.z<3).map(b=>b.kind+'@'+b.m.position.x.toFixed(1)+','+b.m.position.z.toFixed(1)),p:c.puddles.map(q=>q.x.toFixed(1)+','+q.z.toFixed(1)+' r'+q.rx.toFixed(1))};});
console.log(JSON.stringify(r,null,0));process.exit(0);})();
