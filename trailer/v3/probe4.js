const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const c=window.F.c,root=c.kit;root.updateMatrixWorld(true);const fl=root.getObjectByName('FLOORS');const out=[];
 fl.traverse((o)=>{if(!o.isMesh)return;const g=o.geometry,pa=g.attributes.position,ix=g.index;const v=[new THREE.Vector3(),new THREE.Vector3(),new THREE.Vector3()];const n=ix?ix.count/3:pa.count/3;
  const mats=Array.isArray(o.material)?o.material.length:1;const sizes={};
  for(let t=0;t<n;t++){for(let k=0;k<3;k++){const id=ix?ix.getX(t*3+k):t*3+k;v[k].fromBufferAttribute(pa,id).applyMatrix4(o.matrixWorld);}
   const cx=(v[0].x+v[1].x+v[2].x)/3,cz=(v[0].z+v[1].z+v[2].z)/3;if(cx>-11.6&&cx<-6&&cz>-16&&cz<0){const a=Math.abs((v[1].x-v[0].x)*(v[2].z-v[0].z)-(v[2].x-v[0].x)*(v[1].z-v[0].z))/2;const k=a.toFixed(2);sizes[k]=(sizes[k]||0)+1;}}
  out.push({name:o.name,indexed:!!ix,tris:n,mats,groups:g.groups.length,sizes});});return out;});
console.log(JSON.stringify(r));process.exit(0);})();
