const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const c=window.F.c,root=c.kit;root.updateMatrixWorld(true);const out={};const v=new THREE.Vector3();
 root.traverse((o)=>{if(!o.isMesh)return;const pa=o.geometry.attributes.position;if(!pa)return;const hs={};let n=0;
  for(let i=0;i<pa.count;i++){v.fromBufferAttribute(pa,i).applyMatrix4(o.matrixWorld);if(v.x>-11.6&&v.x<-6&&v.z>-16&&v.z<0&&v.y>-0.05&&v.y<0.05){hs[v.y.toFixed(4)]=(hs[v.y.toFixed(4)]||0)+1;n++;}}
  if(n){let nm=o.name;let q=o.parent;while(q&&!nm){nm=q.name;q=q.parent;}out[(o.name||'?')+'<'+(o.parent&&o.parent.name)]=hs;}});return out;});
console.log(JSON.stringify(r,null,1));process.exit(0);})();
