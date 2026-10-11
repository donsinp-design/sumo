const L=require('../lib.js');
(async()=>{const p=await L.open(320,180);await L.boot(p,8);
const r=await p.evaluate(()=>{const c=F.c,P=c.P;c.outOfBath=true;c.asleep=false;const out=[];
 const dirs={away:[0,-1],along:[1,0],into:[0,1],diagIn:[0.7,0.7],diagOut:[0.7,-0.7]};
 for(const [nm,[mx,mz]] of Object.entries(dirs)){
  F.at(-8,-42.0,Math.PI/2,0);c.npcs.forEach(n=>{n.hold=1e6;n.a.x=-60;n.a.z=-100;});
  for(let i=0;i<30;i++){F.pad({mz:0.5});c.ctrl.update(1/60);c.step(1/60);} // walk up to the wall
  const x0=P.x,z0=P.z;let sts=new Set(),k=0;
  for(let i=0;i<90;i++){F.pad({mx,mz,dash:i<40});c.ctrl.update(1/60);c.step(1/60);sts.add(P.st);}
  out.push(nm+' start '+x0.toFixed(2)+','+z0.toFixed(2)+' moved '+Math.hypot(P.x-x0,P.z-z0).toFixed(2)+' states '+[...sts].join('/')+' room '+c.runRoom(x0,z0,Math.atan2(mz,mx),2).toFixed(2));}
 return out.join('\n');});
console.log(r);process.exit(0);})();
