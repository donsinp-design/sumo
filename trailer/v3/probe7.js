const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const c=window.F.c,root=c.kit;root.updateMatrixWorld(true);const out=[];const v=new THREE.Vector3();
 root.traverse((o)=>{if(!o.isMesh)return;const pa=o.geometry.attributes.position;let n=0,xs=new Set();for(let i=0;i<pa.count;i++){v.fromBufferAttribute(pa,i).applyMatrix4(o.matrixWorld);if(Math.abs(v.z+86.2)<0.02||Math.abs(v.z+85.8)<0.02){if(v.x>-4.1&&v.x<9.1&&v.y>2.9){n++;xs.add(v.x.toFixed(2));}}}
  if(n)out.push(o.name+' <'+(o.parent&&o.parent.name)+'> n'+n+' xs '+[...xs].slice(0,12).join(','));});return out;});
console.log(r.join('\n'));process.exit(0);})();
