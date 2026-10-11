// live boss bout at the game's camera: record every frame from the start; report who won round 1 and when
const L=require('../lib.js'),fs=require('fs');
const [,,name,sd,pai]=process.argv;
(async()=>{const p=await L.open(1280,720);await L.boot(p,5);
await p.evaluate(fs.readFileSync(__dirname+'/bosscap.js','utf8').match(/const SETUP=`([\s\S]*?)`;/)[1]);
const dir='../frames/'+name;fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
await p.evaluate(({sd,pai})=>{window.PAI=pai||'normal';window.STUB=0;const m=bossStart(sd);window.DEC=-1;window.WIN=-1;window.FR=0;const em=m.emit.bind(m);m.emit=(t,d)=>{if(t==='decided'&&DEC<0){DEC=FR;WIN=d&&d.winner?d.winner.idx:-1;}return em(t,d);};},{sd:+sd,pai});
let i=0;for(;i<520;i++){const st=await p.evaluate(()=>{S.game.frame(S.game.last+33.333);FR++;return [DEC,WIN];});
 await p.screenshot({path:`${dir}/f_${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:90});
 if(st[0]>=0&&st[1]!==1){console.log(name,'player won at',st[0],'- discard');process.exit(0);} if(st[0]>=0&&i>st[0]+75)break;}
console.log(name,'done',i,'decided',await p.evaluate(()=>DEC),'winner',await p.evaluate(()=>WIN));process.exit(0);})();
