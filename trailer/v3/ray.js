const L=require('../lib.js');const pts=JSON.parse(process.argv[2]);
(async()=>{const p=await L.open(320,180);await L.boot(p,8);
const r=await p.evaluate((pts)=>{const c=F.c,out=[];const rc=new THREE.Raycaster();rc.camera=c.cam;const ms=[];c.scene.traverse(o=>{if(o.isMesh&&!o.isSkinnedMesh)ms.push(o);});
 for(const [x,z] of pts){rc.set(new THREE.Vector3(x,20,z),new THREE.Vector3(0,-1,0));const hs=rc.intersectObjects(ms,false).filter(h=>h.object.visible&&h.object.isMesh).slice(0,5);
  out.push(x+','+z+': '+hs.map(h=>{const m=Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material;return (m.name||'mat')+'#'+h.face.materialIndex+' c'+(m.color?m.color.getHexString():'')+' y'+h.point.y.toFixed(4);}).join(' | ')+' :: '+hs.map(h=>(h.object.name||'')+'<'+(h.object.parent&&h.object.parent.name||'')+'>'+' y'+h.point.y.toFixed(3)).join(' | '));}
 return out.join('\n');},pts);
console.log(r);process.exit(0);})();
