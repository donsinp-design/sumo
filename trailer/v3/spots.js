const L=require('../lib.js');const spots=JSON.parse(process.argv[2]);
(async()=>{const p=await L.open(640,360);await L.boot(p,8);
for(const [x,z,y] of spots){await p.evaluate(({x,z,y})=>{const c=F.c;c.outOfBath=true;c.asleep=false;F.at(x,z,0,y);for(let i=0;i<8;i++)c.frame(1/30);},{x,z,y});
 await p.screenshot({path:`../test/spot_${x}_${z}.jpg`});}
process.exit(0);})();
