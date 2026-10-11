const L=require('../lib.js');
(async()=>{const p=await L.open(640,360);await L.boot(p,5);
await p.evaluate(require('fs').readFileSync('bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const r=await p.evaluate(()=>{const g=S.game,R=g.R;const m=bossStart(10);let dec=-1;const em=m.emit.bind(m);let fr=0;m.emit=(t,d)=>{if(t==='decided'&&dec<0)dec=fr;return em(t,d);};
 const o=[];for(fr=0;fr<90;fr++){g.frame(g.last+33.333);if(fr%40==0){const v1=R.views[1];o.push('w1 '+m.w[1].x.toFixed(2)+','+m.w[1].z.toFixed(2)+' v1root '+(v1&&v1.root?v1.root.position.toArray().map(x=>x.toFixed(1))+' sc '+v1.root.scale.x.toFixed(2)+' par '+!!v1.root.parent:'none')+' keys '+(v1?Object.keys(v1).slice(0,12).join('|'):''));const v=R.views||[];o.push(fr+' phase '+m.phase+' w0 '+m.w[0].x.toFixed(2)+','+m.w[0].z.toFixed(2)+' views '+v.length+' vis '+v.map(x=>x&&x.root&&x.root.visible).join(',')+' cam '+R.cam.position.toArray().map(x=>x.toFixed(1)).join(','));}}
 return o.join('\n')+'\ndecided '+dec+' mode '+g.mode+' camp '+!!g.camp;});
console.log(r);await p.screenshot({path:'../out/bdbg.jpg'});process.exit(0);})();
