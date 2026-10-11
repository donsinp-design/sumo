const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const c=window.F.c,root=c.kit;root.updateMatrixWorld(true);const out=[];
 root.traverse((o)=>{if(!o.isMesh)return;const b=new THREE.Box3().setFromObject(o);if(b.max.z>-86.4&&b.min.z<-85.6&&b.min.y>2.5&&b.max.x>-4.5&&b.min.x<9.5&&b.min.y<4.5)out.push(o.name+' <'+(o.parent&&o.parent.name)+'> ['+b.min.toArray().map(v=>v.toFixed(2))+'] ['+b.max.toArray().map(v=>v.toFixed(2))+'] v'+o.geometry.attributes.position.count);});return out;});
console.log(r.join('\n'));process.exit(0);})();
