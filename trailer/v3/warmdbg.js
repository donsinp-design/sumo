const L=require('../lib.js');const T=require('./takes.js');const [,,name,expr,steps]=process.argv;const tk=T[name];
(async()=>{const p=await L.open(320,180);await L.boot(p,tk.seed);await p.evaluate(T.HELP);
await p.evaluate(`(()=>{const F=window.F;F.c.asleep=false;F.take={};(${tk.setup.toString()})(F);})()`);
const r=await p.evaluate(`(()=>{const F=window.F,c=F.c,sc=${tk.script.toString()};const o=[];for(let k=0;k<${steps};k++){sc(k/60,F);c.ctrl.update(1/60);c.step(1/60);const P=c.P;if(k%30==0)o.push(k+' '+(${expr}));}return o.join('\\n');})()`);
console.log(r);process.exit(0);})();
