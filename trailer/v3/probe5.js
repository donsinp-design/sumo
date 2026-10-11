const L=require('../lib.js');const I=+process.argv[2];
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate((I)=>{const c=window.F.c,root=c.kit;root.updateMatrixWorld(true);const out=[];
 root.traverse((o)=>{if(o.name&&o.name.startsWith('SOLID_'+I+'_')){const b=new THREE.Box3().setFromObject(o);out.push(o.name+' '+o.type+' mat:'+(o.material&&o.material.name)+' ['+b.min.toArray().map(v=>v.toFixed(2))+'] ['+b.max.toArray().map(v=>v.toFixed(2))+'] pos '+o.position.toArray().map(v=>v.toFixed(2))+' parent '+(o.parent&&o.parent.name));}});return out;},I);
console.log(r.join('\n'));process.exit(0);})();
