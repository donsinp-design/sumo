const L=require('../lib.js');
(async()=>{const p=await L.open(480,270);await L.boot(p,2);
const r=await p.evaluate(()=>{const c=window.F.c,root=c.kit;root.updateMatrixWorld(true);const out={};const v=[0,0,0].map(()=>new THREE.Vector3());
 root.traverse((o)=>{if(!o.isMesh)return;const g=o.geometry,pa=g.attributes.position,ix=g.index;const n=ix?ix.count/3:pa.count/3;
  for(let t=0;t<n;t++){for(let k=0;k<3;k++)v[k].fromBufferAttribute(pa,ix?ix.getX(t*3+k):t*3+k).applyMatrix4(o.matrixWorld);
   const cx=(v[0].x+v[1].x+v[2].x)/3,cz=(v[0].z+v[1].z+v[2].z)/3,cy=(v[0].y+v[1].y+v[2].y)/3;
   if(cx>-12.7&&cx<-11.8&&cz>-26&&cz<3){const flat=Math.abs(v[0].y-v[1].y)<1e-3&&Math.abs(v[0].y-v[2].y)<1e-3;if(!flat)continue;const key=(o.name||'?')+' y'+cy.toFixed(3);out[key]=(out[key]||0)+1;}}});return out;});
console.log(JSON.stringify(r,null,1));process.exit(0);})();
