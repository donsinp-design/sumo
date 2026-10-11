// natural takes: the sumo is driven only by the game's own inputs (move, tiptoe, K, J, L), reacting to what the staff do
const T={};
T.HELP=`window.H={
 danger(c,extra){const P=c.P;for(const n of c.npcs){if(n.ko||n.a.st==='down')continue;if(Math.abs(n.a.y-P.y)>1.5)continue;const dx=P.x-n.a.x,dz=P.z-n.a.z,d=Math.hypot(dx,dz);const r=(n.range||6)*1.15+(extra||0);if(d>r)continue;let da=Math.atan2(dz,dx)-n.a.f;da=Math.atan2(Math.sin(da),Math.cos(da));if(Math.abs(da)<(n.half||0.62)+0.45)return n;}return null;},
 go(F,tx,tz,s){const P=F.c.P,dx=tx-P.x,dz=tz-P.z,d=Math.hypot(dx,dz)||1;F.inp.mx=dx/d*(s||1);F.inp.mz=dz/d*(s||1);return d;},
 stop(F){F.inp.mx=0;F.inp.mz=0;},
 pulse(F,t,period){return (Math.floor(t*30/(period||4))%2)===0;}
};`;
const UP=3;
// 1: the box sneaks across the lobby, freezing whenever a cone could find it
T.boxsneak={seed:3,pre:3.5,n:150,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(-8,-79.6,0,3);c.grace=0;},
 script:(t,F)=>{const c=F.c;F.pad();c.keys.KeyI=true;const d=H.danger(c);if(d)H.stop(F);else H.go(F,9.5,-79.6,0.9);}};
// 2: sitting still in the box on a guard's patrol line: they shove it aside
T.boxshove={seed:5,pre:2.5,n:170,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(-1,-79.3,0,3);c.grace=0;},
 script:(t,F)=>{const c=F.c;F.pad();c.keys.KeyI=true;const d=H.go(F,2.6,-77.4,0.9);if(d<0.4)H.stop(F);}};
// 3: creeping up behind a guard in the box, then standing up
T.boxsurprise={seed:6,pre:3.2,n:140,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(13.2,-50.3,0,0);c.grace=0;F.take.n=c.npcs[13];},
 script:(t,F)=>{const c=F.c,n=F.take.n,P=c.P;F.pad();const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);
   if(!F.take.arr&&d<1.7){F.take.arr=t;}
   if(F.take.arr){H.stop(F);c.keys.KeyI=(t-F.take.arr)<0.9;}
   else{c.keys.KeyI=true;const dd=H.danger(c);if(dd&&dd!==n)H.stop(F);else H.go(F,n.a.x-0.9,n.a.z-1.0,0.9);}}};
// 4: grab the bucket as the guards close in, slam it, run, and they slip
T.chasebucket={seed:8,pre:9,n:150,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(5.6,-76.8,Math.PI/2,3);c.grace=0;F.take.b=c.buckets.find((b)=>b.kind==='bucket'&&Math.abs(b.z0+70.4)<0.4);F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,b=F.take.b;F.pad();const ch=c.npcs.filter((n)=>n.mode==='chase'&&!n.ko);
   if(F.take.st===0){const d=H.go(F,b.x0,b.z0-1.0,1);if(d<2.6){F.take.st=1;F.take.stopWarm=true;}}
   else if(F.take.st===1){H.go(F,b.x0,b.z0-1.0,0.5);const dd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(P.held){F.take.st=2;}else if(dd<1.4){F.inp.grab=H.pulse(F,t,3);}}
   else if(F.take.st===2){const n=ch[0]||c.npcs[5];P.f=Math.atan2(n.a.z-P.z,n.a.x-P.x);F.inp.grab=true;if(!P.held)F.take.st=3;}
   else H.go(F,P.x,-84,1);}};
// 2b: hiding in the box on a patrol line: shoved, then stands up (they leap back), then he runs
T.shovesurp={seed:5,pre:6,n:200,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(5.2,-77.6,Math.PI,3);c.grace=0;F.take.st=1;},
 script:(t,F)=>{const c=F.c;F.pad();const tk=F.take;
   if(tk.st===0){}
   else if(tk.st===1){c.keys.KeyI=true;H.stop(F);if(c.npcs.some((n)=>n.pushing2)){tk.sh=tk.sh||t;tk.stopWarm=t-tk.sh>0.2;if(t-tk.sh>1.2){tk.st=2;tk.up=t;}}}
   else if(tk.st===2){c.keys.KeyI=false;H.stop(F);if(t-tk.up>0.7)tk.st=3;}
   else{c.keys.KeyI=false;H.go(F,-6,-81,1);}}};
// 5: corridor: carrying a bucket, spotted from down the corridor; he runs round the corner into the lockers, turns, slams it (puddle), runs on: they slip
T.chaseslip={seed:8,pre:8,n:240,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.item(34,6.6,-44.4);F.at(7.4,-44.4,Math.PI,0);c.grace=0;const tk=F.take;tk.b=c.buckets[34];tk.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,b=tk.b;F.pad();const ch=c.npcs.filter((n)=>n.mode==='chase'&&!n.ko&&n.a.st==='free');
   if(tk.st===0){P.f=Math.PI;tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;if(P.held){tk.st=1;F.inp.grab=false;}}
   else if(tk.st===1){H.stop(F);if(ch.length){tk.st=1.5;tk.t1=t;tk.stopWarm=true;}}
   else if(tk.st===1.5){if(P.x<9.6)H.go(F,10.2,-44.4,1);else H.go(F,10.2,-39.8,1);if(P.z>-40.6){tk.st=2;tk.t2=t;}}
   else if(tk.st===2){let n=null,bd=1e9;for(const q of ch){const d=Math.hypot(q.a.x-P.x,q.a.z-P.z);if(d<bd){bd=d;n=q;}}
     P.f=n?Math.atan2(n.a.z-P.z,n.a.x-P.x):-Math.PI/2;F.inp.grab=t-tk.t2>0.1;if(!P.held){tk.st=3;tk.t3=t;F.inp.grab=false;}}
   else{if(t-tk.t3>0.3)H.go(F,3.5,-40.2,1);}}};
// 6: locker room: spotted, he body-checks the one coming at him, then takes a run-up and charges straight through a bank of lockers
T.chargelock={seed:8,pre:10,n:240,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-0.6,-40.3,Math.PI/2,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();const ch=c.npcs.filter((n)=>n.mode==='chase'&&!n.ko&&n.a.st==='free'&&Math.abs(n.a.y-P.y)<1);
   const charge=(ax,az)=>{const d=Math.hypot(ax,az)||1;F.inp.mx=ax/d;F.inp.mz=az/d;F.inp.dash=P.st==='free'&&!tk.dl;if(P.st==='wind'||P.st==='charge')tk.dl=true;if(P.st==='free'&&tk.dl&&!F.inp.dash){tk.dl=false;}};
   if(tk.st===0){H.stop(F);P.f=lerp0(P.f);if(ch.length){const n=ch[0],d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<3.6){tk.st=1;tk.t1=t;tk.stopWarm=true;tk.n=n;}}}
   else if(tk.st===1){const n=tk.n;if(n.ko||t-tk.t1>1.6){tk.st=2;tk.t2=t;tk.dl=false;}else charge(n.a.x-P.x,n.a.z-P.z);}
   else if(tk.st===2){const d=H.go(F,-0.2,-40.3,0.8);if(d<0.25||t-tk.t2>1.5){tk.st=3;tk.t3=t;tk.dl=false;}}
   else if(tk.st===3){charge(0,1);if(t-tk.t3>1.4)tk.st=4;}
   else H.go(F,-0.2,-33,0.7);
   function lerp0(f){return f;}}};
// 1+2: one take: the box creeps along behind a guard; he turns round, it freezes; he comes back, shoves it; it stands up, he jumps; it runs
T.sneakshove={seed:5,pre:14,n:330,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';const n=c.npcs[9];F.take.n=n;F.at(n.a.x-2.2,-77.6,0,3);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();
   if(tk.st===0){c.keys.KeyI=true;const away=Math.cos(n.a.f)*(P.x-n.a.x)+Math.sin(n.a.f)*(P.z-n.a.z)<0;   // he's facing away from the box
     if(n.a.x>5.5)tk.stopWarm=true;
     if(n.mode==='route'&&n.wait>0&&!tk.went)H.stop(F);
     else if(away){tk.went=true;const tx=n.a.x-Math.cos(n.a.f)*1.9,tz=-78.0;H.go(F,tx,tz,0.9);}else{H.stop(F);if(tk.went)tk.st=1;}}
   else if(tk.st===1){c.keys.KeyI=true;H.stop(F);if(c.npcs.some((q)=>q.pushing2)){tk.sh=tk.sh||t;if(t-tk.sh>1.2){tk.st=2;tk.up=t;}}}
   else if(tk.st===2){c.keys.KeyI=false;H.stop(F);if(t-tk.up>0.7)tk.st=3;}
   else{c.keys.KeyI=false;H.go(F,-6,-81,1);}}};
// 1b: the box creeps down the staff corridor, freezing whenever a cone could find it
T.boxsneak2={seed:3,pre:2,n:180,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(-2.6,-45.8,0,0);c.grace=0;},
 script:(t,F)=>{const c=F.c;F.pad();c.keys.KeyI=true;const d=H.danger(c,-1.5);if(d)H.stop(F);else H.go(F,10.5,-45.6,0.9);}};
// 1+2 (one shot): while the guard looks the other way, the box creeps up into his path and freezes; he walks into it, shoves it; it stands up, he jumps; it runs
T.creepshove={seed:5,pre:0.1,n:260,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(6.4,-81.0,Math.PI/2,3);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){c.keys.KeyI=true;const dg=H.danger(c,-1);if(dg&&dg===c.npcs[9])H.stop(F);else{const d=H.go(F,5.2,-77.6,0.9);if(d<0.3){H.stop(F);tk.st=1;}}}
   else if(tk.st===1){c.keys.KeyI=true;H.stop(F);if(c.npcs.some((n)=>n.pushing2)){tk.sh=tk.sh||t;if(t-tk.sh>1.2){tk.st=2;tk.up=t;}}}
   else if(tk.st===2){c.keys.KeyI=false;H.stop(F);if(t-tk.up>0.7)tk.st=3;}
   else{c.keys.KeyI=false;H.go(F,-6,-81,1);}}};
// 5b: in the mawashi (the escape): carrying a bucket, spotted; round the corner into the narrow locker aisle, turn, slam it (the puddle fills the aisle), run on: they slip on it
T.chasemaw={seed:8,pre:8,n:260,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.gotMawashi=true;F.item(34,6.6,-44.4);F.at(7.4,-44.4,Math.PI,0);c.grace=0;const tk=F.take;tk.b=c.buckets[34];tk.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();const ch=c.npcs.filter((n)=>n.mode==='chase'&&!n.ko&&n.a.st==='free');
   let near=null,nd=1e9;for(const q of ch){const d=Math.hypot(q.a.x-P.x,q.a.z-P.z);if(d<nd){nd=d;near=q;}}
   if(tk.st===0){P.f=Math.PI;tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;if(P.held){tk.st=1;F.inp.grab=false;}}
   else if(tk.st===1){H.stop(F);if(ch.length){tk.st=1.5;tk.stopWarm=true;}}
   else if(tk.st===1.5){if(P.z<-41.2)H.go(F,10.3,-44.4+(P.x>9.6?6:0),1);else H.go(F,6.4,-40.2,1);if(P.z>-41.2&&P.x<6.9){tk.st=2;tk.t2=t;}}
   else if(tk.st===2){P.f=0;F.inp.grab=t-tk.t2>0.1;if(!P.held){tk.st=3;tk.t3=t;F.inp.grab=false;}}
   else{if(t-tk.t3>0.25){if(P.x>-2.5)H.go(F,-3.0,-40.2,1);else H.go(F,-2.6,-44.4,1);}}}};
// 7: hidden in a laundry cart behind the machine staff; out of the cart, grab the bucket, throw it at the nearest back: down he goes
T.cartko={seed:8,pre:2.5,n:320,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const ct=c.carts[3];F.at(ct.x,ct.z+0.95,-Math.PI/2,0);c.grace=0;const tk=F.take;tk.st=0;tk.ct=ct;tk.b=F.item(31,14.6,-53.4);tk.n=c.npcs[12];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n,b=tk.b;F.pad();const dx=n.a.x-P.x,dz=n.a.z-P.z,d=Math.hypot(dx,dz);
   if(tk.st===0){c.keys.KeyI=true;if(!tk.ip){c.iPress=true;tk.ip=1;}if(P.hidden){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){c.keys.KeyI=true;if(t-tk.t1>0.3)tk.stopWarm=true;const away=Math.cos(n.a.f)*dx+Math.sin(n.a.f)*dz>0;if(t-tk.t1>1.0&&away&&c.npcs.every((q)=>!H.danger(c)||true)){tk.st=2;tk.t2=t;tk.stopWarm=true;}}
   else if(tk.st===2){c.keys.KeyI=true;F.inp.mx=-0.3;F.inp.mz=1;if(!P.hidden&&t-tk.t2>0.3){tk.st=3;c.keys.KeyI=false;}}
   else if(tk.st===3){c.keys.KeyI=false;const bx=b.m.position.x,bz=b.m.position.z,bd=Math.hypot(bx-P.x,bz-P.z);if(bd>0.8&&!tk.at)H.go(F,bx,bz,0.6);else{tk.at=1;P.f=Math.atan2(bz-P.z,bx-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;}if(P.held){tk.st=4;F.inp.grab=false;tk.t4=t;}}
   else if(tk.st===4){if(!tk.spot){let best=null;for(let a=-0.6;a<=0.6;a+=0.1)for(let sd=3;sd<=6.5;sd+=0.25){const ang=Math.atan2(dz,dx)+a,x=n.a.x-Math.cos(ang)*sd,z=n.a.z-Math.sin(ang)*sd;if(c.inWall(x,z)||!c.clear(P.x,P.z,x,z))continue;const Lr=Math.max(1,c.reach(x,z,ang,8)-0.6),k=sd/Lr;if(k<0.8||k>0.97)continue;const sc=Math.abs(k-0.9)+Math.hypot(x-P.x,z-P.z)*0.05;if(!best||sc<best.sc)best={x,z,sc};}tk.spot=best||{x:P.x,z:P.z};}
     const sd=H.go(F,tk.spot.x,tk.spot.z,0.7);const away=Math.cos(n.a.f)*dx+Math.sin(n.a.f)*dz>0;if(sd<0.25){H.stop(F);P.f=Math.atan2(dz,dx);if(t-tk.t4>0.35&&away){F.inp.grab=true;tk.st=5;tk.t5=t;}}}
   else if(tk.st===5){P.f=Math.atan2(dz,dx);F.inp.grab=t-tk.t5<0.08;if(t-tk.t5>0.5)tk.st=6;}
   else{let q=null,qd=1e9;for(const m of c.npcs){if(m.ko||m.a.st==='down'||Math.abs(m.a.y-P.y)>1)continue;const e=Math.hypot(m.a.x-P.x,m.a.z-P.z);if(e<qd){qd=e;q=m;}}
     if(q&&qd<1.25&&!(tk.sl>0&&t-tk.sl<0.6)){P.f=Math.atan2(q.a.z-P.z,q.a.x-P.x);F.inp.push=true;tk.sl=t;}else if(q&&qd<4&&q.mode==='chase'){P.f=Math.atan2(q.a.z-P.z,q.a.x-P.x);H.stop(F);}else H.stop(F);}}};
// 8: the vending machine: thump, a can; thump, another; KRRRASH: glass, cans everywhere, one split and spraying
T.vend={seed:8,pre:0.6,n:200,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br){tk.br=t;}if(tk.br&&t-tk.br>1.4)tk.st=2;}
   else{H.go(F,V.x0-4,V.z-0.4,0.6);}}};
// 9: the escape, in the mawashi: a chef blocks the kitchen door, so he charges him flat, then runs the gauntlet past the mousetraps and out the back door
T.escape={seed:4,pre:3,n:330,
 setup:(F)=>{const c=F.c;c.jumpTo('escape');c.outOfBath=true;F.at(4.4,-49.6,-Math.PI/2,0);c.grace=0;const tk=F.take;tk.wp=[[4.4,-55.1],[1.6,-55.5],[-2.0,-56.15],[-6.4,-56.2],[-9.6,-57.6],[-11.6,-59.3],[-14,-59.3]];tk.i=0;tk.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=c.npcs[16];F.pad();if(c.over){H.stop(F);return;}
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(!n.ko&&Math.abs(n.a.x-4.4)<1.3&&n.a.z>-56&&n.a.z<-53.2){tk.st=1;tk.stopWarm=true;tk.t1=t;}}
   else if(tk.st===1){const dx=n.a.x-P.x,dz=n.a.z-P.z,d=Math.hypot(dx,dz)||1;F.inp.mx=dx/d;F.inp.mz=dz/d;F.inp.dash=t-tk.t1<0.1;if(n.ko||t-tk.t1>1.6)tk.st=2;}
   else{const w=tk.wp[tk.i];if(!w){H.stop(F);return;}const d=H.go(F,w[0],w[1],1);if(d<0.35)tk.i++;}}};
// 0: asleep in the bath (Zzz), wakes, wades to the steps and climbs out
T.wake={seed:2,pre:0.1,n:210,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>2.2){c.wake();tk.st=1;tk.t1=t;}}
   else if(tk.st===1){if(t-tk.t1>1.3){tk.st=2;}}
   else if(tk.st===2){const d=H.go(F,1.0,-1.0,1);if(d<0.4)tk.st=3;}
   else H.go(F,-6,2.5,1);}};
// 0b: one take: asleep in the bath (Zzz), wakes, climbs out, runs round the bath, dashes across the wash area, then tiptoes through the locker room to his locker
T.toLocker={seed:2,pre:0.1,n:600,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';const tk=F.take;tk.st=0;tk.i=0;
   tk.wp=[[1.0,-1.0,'w'],[1.2,0.9,'w'],[-4.6,0.9,'w'],[-4.6,-14.5,'w'],[0.6,-17.0,'w'],[1.2,-18.2,'d'],[6.75,-25.0,'w'],[6.75,-28.6,'t'],[2.5,-30.5,'t'],[2.5,-37.4,'t'],[-4.5,-38.2,'t'],[-10.3,-39.7,'t']];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>2.0){c.wake();tk.st=1;tk.t1=t;}return;}
   if(tk.st===1){if(t-tk.t1>1.2)tk.st=2;return;}
   const w=tk.wp[tk.i];if(!w){H.stop(F);c.keys.KeyI=false;return;}
   if(w[2]==='d'){if(!tk.dt){tk.dt=t;}const a=Math.atan2(-24.5-P.z,4.2-P.x);F.inp.mx=Math.cos(a);F.inp.mz=Math.sin(a);F.inp.dash=t-tk.dt<0.1;if(t-tk.dt>1.3){tk.i++;}return;}
   c.keys.KeyI=w[2]==='t';
   if(w[2]==='t'&&H.danger(c,0.5)){H.stop(F);return;}
   const d=H.go(F,w[0],w[1],1);if(d<0.35)tk.i++;}};
// 1c: the box creeps along behind a guard in the corridor; when he turns it freezes (his cone sweeps over it); he walks back into it, shoves it; it stands up, he jumps; it runs
T.boxfollow={seed:8,pre:12,n:420,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';c.outOfBath=true;F.at(0.6,-44.6,0,0);c.grace=1.5;c.keys.KeyI=true;const tk=F.take;tk.st=0;tk.n=c.npcs[1];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();const dx=P.x-n.a.x,dz=P.z-n.a.z,d=Math.hypot(dx,dz)||1,fa=(Math.cos(n.a.f)*dx+Math.sin(n.a.f)*dz)/d;
   const others=c.npcs.some((q)=>q!==n&&!q.ko&&Math.abs(q.a.y-P.y)<1.5&&(()=>{const ex=P.x-q.a.x,ez=P.z-q.a.z,ed=Math.hypot(ex,ez);if(ed>q.range*1.2)return false;let da=Math.atan2(ez,ex)-q.a.f;da=Math.atan2(Math.sin(da),Math.cos(da));return Math.abs(da)<q.half+0.5;})());
   if(tk.st===0){c.keys.KeyI=true;const going=n.mode==='route'&&!(n.wait>0)&&Math.cos(n.a.f)>0.7;if(going&&!tk.go&&n.a.x>2.4&&n.a.x<4)tk.go=1;tk.oth=others;
     if(tk.go&&fa<-0.45&&!others&&P.tip>0.9&&n.a.x<9.8){tk.stopWarm=true;H.go(F,n.a.x-2.1,-44.6,0.9);tk.moved=1;}else{H.stop(F);if(tk.moved&&n.a.x>9.5)tk.st=1;}}
   else if(tk.st===1){c.keys.KeyI=true;H.stop(F);if(n.pushing2){tk.sh=tk.sh||t;if(t-tk.sh>1.2){tk.st=2;tk.up=t;}}}
   else if(tk.st===2){c.keys.KeyI=false;H.stop(F);if(t-tk.up>0.7)tk.st=3;}
   else{c.keys.KeyI=false;H.go(F,-9,-45.6,1);}}};
// 1d (lobby): the box creeps along behind the guard; he turns at the end of his beat, it freezes, his cone sweeps over it; he walks back into it, shoves it; it stands up, he jumps; it runs
T.follow9={seed:5,pre:0.4,n:540,
 setup:(F)=>{const c=F.c;F.box();c.stage='exit';F.at(-0.7,-75.3,0,3);c.grace=1.2;c.keys.KeyI=true;c.P.boxHide=true;c.wasBoxHide=true;c.ballK=1;const tk=F.take;tk.st=1;const n=tk.n=c.npcs[9];n.a.x=3;n.a.z=-77.4;n.a.f=0;n.i=1;n.wait=0;n.mode='route';n.path=null;c.goTo(n,9.6,-77.4);},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();c.keys.KeyI=true;
   const dx=P.x-n.a.x,dz=P.z-n.a.z,d=Math.hypot(dx,dz)||1,fa=(Math.cos(n.a.f)*dx+Math.sin(n.a.f)*dz)/d;
   if(tk.st===0){H.stop(F);if(n.mode==='route'&&!(n.wait>0)&&Math.cos(n.a.f)>0.8&&n.a.x>0.5&&n.a.x<2){P.x=n.a.x-3.7;P.z=-75.3;P.vx=P.vz=0;c.camT.set(P.x*0.8,3,P.z-2.6);c.grace=1.2;tk.st=1;}}
   else{const sx=Math.cos(n.a.f)>0?1:-1;if(n.mode==='route'&&!(n.wait>0)&&fa<-0.55&&Math.abs(Math.cos(n.a.f))>0.8&&Math.abs(P.x-n.a.x)>3.7){H.go(F,n.a.x-3.6*sx,-75.3,0.9);}else H.stop(F);}}};
// 8b: the vending machine: thump, a can; thump, another; KRRRASH. He picks one up and drinks it; picks up another, and when someone comes to look, throws it at them
T.vend2={seed:8,pre:0.6,n:330,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();const cans=()=>c.buckets.filter((b)=>b.kind==='can'&&b.state==='floor'&&b.soda!==undefined);
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||b.soda===undefined)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;if(tk.k>20){b._skip=true;tk.k=0;}}};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.2)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=2.5;F.inp.grab=false;}else pick();}
   else if(tk.st===2.5){const d=H.go(F,5.6,-40.2,1);if(d<0.3){tk.st=3;tk.t3=t;}}
   else if(tk.st===3){H.stop(F);P.f=0;F.inp.push=t-tk.t3>0.15&&t-tk.t3<0.22;if(!P.held&&t-tk.t3>0.3){tk.st=4;tk.t4=t;tk.k=0;}}
   else if(tk.st===4){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=5;F.inp.grab=false;}else pick();}
   else if(tk.st===5){let n=null,nd=1e9;for(const q of c.npcs){if(q.ko||Math.abs(q.a.y-P.y)>1)continue;const d=Math.hypot(q.a.x-P.x,q.a.z-P.z);if(d<nd&&d<9){nd=d;n=q;}}
     if(n){const a=Math.atan2(n.a.z-P.z,n.a.x-P.x);P.f=a;const L=Math.max(1,c.reach(P.x,P.z,a,8)-0.6);if(nd>0.62*L&&nd<0.96*L&&nd>1.6){F.inp.grab=true;tk.st=6;tk.t6=t;}else if(nd<1.6){H.go(F,P.x-(n.a.x-P.x),P.z,1);}else H.stop(F);}else{H.stop(F);P.f=0;}}
   else{F.inp.grab=t-tk.t6<0.08;}}};

// v3 intro: a long sleep (Zzz), wakes, climbs out: "no mawashi!?", walks (dash across the wash area), tiptoes only when someone's close, tries his locker: locked
T.vend3={seed:8,pre:0.6,n:330,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();const cans=()=>c.buckets.filter((b)=>b.kind==='can'&&b.state==='floor'&&b.soda!==undefined);
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||b.soda===undefined)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;if(tk.k>20){b._skip=true;tk.k=0;}}};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.2)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=2.5;F.inp.grab=false;}else pick();}
   else if(tk.st===2.5){const d=H.go(F,5.6,-40.2,1);if(d<0.3){tk.st=3;tk.t3=t;}}
   else if(tk.st===3){H.stop(F);P.f=0;F.inp.push=t-tk.t3>0.15&&t-tk.t3<0.22;if(!P.held&&t-tk.t3>0.3){tk.st=4;tk.t4=t;tk.k=0;}}
   else if(tk.st===4){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=5;F.inp.grab=false;}else pick();}
   else if(tk.st===5){H.stop(F);if(!tk.t5)tk.t5=t;P.f=0.6;F.inp.push=t-tk.t5>0.3&&t-tk.t5<0.37;if(t-tk.t5>2.5)tk.st=6;}
   else{H.stop(F);}}};

T.wake3={seed:2,pre:0.1,n:1080,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';const tk=F.take;tk.st=0;tk.i=0;
   tk.wp=[[1.0,-1.0,'w'],[1.2,0.9,'w'],[-4.6,0.9,'w'],[-4.6,-14.5,'w'],[0.6,-17.0,'w'],[1.2,-18.2,'d'],[6.75,-25.0,'w'],[6.75,-28.4,'a'],[1.5,-28.3,'a'],[-7.5,-28.3,'a'],[-10.6,-29.6,'a'],[-10.6,-38.0,'a'],[-10.4,-39.6,'a'],['use']];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>5.2){c.wake();tk.st=1;tk.t1=t;}return;}
   if(tk.st===1){if(t-tk.t1>1.2)tk.st=2;return;}
   const w=tk.wp[tk.i];if(!w){H.stop(F);c.keys.KeyI=false;return;}
   if(w[0]==='use'){H.stop(F);c.keys.KeyI=false;if(!tk.u){tk.u=t;}F.inp.grab=t-tk.u>0.3&&t-tk.u<0.37;if(t-tk.u>0.5)tk.i++;return;}
   if(w[2]==='d'){if(!tk.dt){tk.dt=t;}const a=Math.atan2(-24.5-P.z,4.2-P.x);F.inp.mx=Math.cos(a);F.inp.mz=Math.sin(a);F.inp.dash=t-tk.dt<0.1;if(t-tk.dt>1.3){tk.i++;}return;}
   let near=false;if(w[2]==='a'){for(const n of c.npcs){if(n.ko||Math.abs(n.a.y-P.y)>1.5)continue;if(Math.hypot(n.a.x-P.x,n.a.z-P.z)<6.2)near=true;}}
   c.keys.KeyI=near;
   if(near&&H.danger(c,0.5)){H.stop(F);return;}
   const d=H.go(F,w[0],w[1],1);if(d<0.35)tk.i++;}};
// v3: sitting in the box right in a staff member's way: he shoves it aside... it stands up. He jumps out of his skin; the box runs
T.shove2={seed:5,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;F.box();c.P.st='free';c.P.dur=0;c.noDuck=0;c.P.boxHide=true;c.wasBoxHide=true;c.ballK=1;c.stage='exit';F.at(1.5,-77.4,Math.PI,3);c.grace=3.5;c.keys.KeyI=true;const tk=F.take;tk.st=1;const n=tk.n=c.npcs[9];n.a.x=-2.6;n.a.z=-77.4;n.a.f=0;n.i=1;n.wait=0;n.mode='route';n.path=null;c.goTo(n,9.6,-77.4);},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();
   if(tk.st===1){H.stop(F);c.keys.KeyI=true;const nd=Math.hypot(n.a.x-P.x,n.a.z-P.z);if((n.pushing2||n.clr)&&nd<1.7){tk.sh=tk.sh||t;if(t-tk.sh>0.9){tk.st=2;tk.up=t;}}}
   else if(tk.st===2){H.stop(F);c.keys.KeyI=false;if(t-tk.up>1.0)tk.st=3;}
   else{c.keys.KeyI=false;H.go(F,-7,-80.5,1);}}};
// v3: knocks on the lockers to lure the attendant behind them round to look, then slips off the other way
T.knock1={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-5,-32.45,-Math.PI/2,0);c.grace=1.0;const tk=F.take;tk.st=0;tk.n=c.npcs[2];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;c.keys.KeyI=true;if(t>1.0){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07||((t-tk.k)>0.45&&(t-tk.k)<0.52);if(t-tk.k>0.6){tk.st=2;tk.x0=n.a.x;}}
   else if(tk.st===2){H.stop(F);c.keys.KeyI=true;if(Math.abs(n.a.x-tk.x0)>0.25){tk.st=3;tk.dir=n.a.x<tk.x0?1:-1;tk.wp=tk.dir>0?[[0.5,-32.6],[0.5,-30],[-3.4,-29.6]]:[[-10.3,-32.6],[-10.3,-30],[-6.6,-29.6]];tk.i=0;}else if(t-tk.k>6){tk.st=4;}}
   else if(tk.st===3){const near=Math.hypot(n.a.x-P.x,n.a.z-P.z)<5;c.keys.KeyI=near;const w=tk.wp[tk.i];if(!w){H.stop(F);c.keys.KeyI=true;return;}if(H.go(F,w[0],w[1],1)<0.35)tk.i++;}
   else H.stop(F);}};
T.cartrun={seed:4,pre:0.3,n:240,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const ct=c.carts[1];F.at(ct.x-1.0,ct.z,0,0);c.grace=1.5;const tk=F.take;tk.ct=ct;tk.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){H.stop(F);P.f=0;F.inp.grab=t>0.5&&t<0.57;if(P.cart){tk.st=1;}}
   else{const w=[[8.8,-49.6],[16,-49.6]][tk.w||0];if(!w){H.stop(F);return;}if(H.go(F,w[0],w[1],1)<0.5)tk.w=(tk.w||0)+1;}}};

// v3: knocks on the wall to lure them over, then hops into the laundry cart and hides while they come and look
T.knock2={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=5.4;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>0.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};

T.washtest={seed:2,pre:0.3,n:120,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.6,-3,-Math.PI/2,0);c.grace=99;},
 script:(t,F)=>{F.pad();const d=H.go(F,-4.6,-14.5,1);}};

// v4 intro: sleep, wake, "no mawashi!?", dash to the first bucket on the left wall, throw it ahead (it splashes a puddle),
// dash, slip on his own puddle, walk over it, dash to the locker room door; grab a stool, go to the bottom right of the locker room,
// throw it up the room to send someone off to look, then tiptoe left behind the attendant by the puddle and on to his locker: locked
T.wake4={seed:2,pre:2.0,n:1560,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';const tk=F.take;tk.st=0;tk.i=0;
   tk.q=[['go',1.0,-1.0,'w'],['go',1.2,0.9,'w'],['dash',-6.5,0.9,1.0],['go',-9.5,-3.2,'w'],['pick',-10.2,-2.5,'oke'],['go',-4.6,-2.6,'w'],['face',-Math.PI/2],['throw'],['wait',0.5],['pud'],['wait',0.3],['dashp',-4.6,-14.0,1.6],['wait',1.2],['go',-4.6,-12.6,'w'],['go',-4.6,-14.5,'w'],['go',0.6,-17.0,'w'],['dash',6.2,-24.6,1.4],['pick',7.6,-23.5,'stool'],['go',6.75,-28.0,'a'],['go',10.2,-28.6,'a'],['face',-Math.PI/2],['throw'],['wait',1.0],['go',1.5,-28.3,'a'],['go',-7.5,-28.3,'a'],['go',-10.6,-29.6,'a'],['go',-10.6,-38.0,'a'],['go',-10.4,-39.6,'a'],['use'],['end']];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>5.2){c.wake();tk.st=1;tk.t1=t;}return;}
   if(tk.st===1){if(t-tk.t1>1.2)tk.st=2;return;}
   const s=tk.q[tk.i];if(!s||s[0]==='end'){H.stop(F);c.keys.KeyI=false;return;}
   const nxt=()=>{tk.i++;tk.s0=undefined;tk.k=0;};if(tk.s0===undefined)tk.s0=t;const dt=t-tk.s0;
   if(P.st!=='free'&&s[0]!=='wait'){H.stop(F);return;}
   if(s[0]==='go'){let near=false;if(s[3]==='a')for(const n of c.npcs){if(n.ko||Math.abs(n.a.y-P.y)>1.5)continue;if(Math.hypot(n.a.x-P.x,n.a.z-P.z)<4.6)near=true;}
     c.keys.KeyI=near;if(near&&H.danger(c,-1.5)){H.stop(F);return;}if(H.go(F,s[1],s[2],1)<0.35)nxt();}
   else if(s[0]==='dashp'){c.keys.KeyI=false;const q=tk.pud;const tx=q?q.x:s[1];H.go(F,tx,s[2],1);F.inp.dash=dt<0.08;if(dt>s[3])nxt();}
   else if(s[0]==='dash'){c.keys.KeyI=false;const d=H.go(F,s[1],s[2],1);F.inp.dash=dt<0.08;if(dt>s[3]||d<0.4)nxt();}
   else if(s[0]==='pud'){const q=c.puddles[c.puddles.length-1];tk.pud=q;if(q){const back=Math.min(-0.3,q.z+3.0);if(H.go(F,q.x,back,0.8)<0.3){H.stop(F);P.f=-Math.PI/2;nxt();}}else nxt();}
   else if(s[0]==='face'){H.stop(F);P.f=s[1];if(dt>0.15)nxt();}
   else if(s[0]==='wait'){H.stop(F);if(dt>s[1])nxt();}
   else if(s[0]==='throw'){H.stop(F);F.inp.grab=dt<0.07;if(dt>0.4)nxt();}
   else if(s[0]==='use'){H.stop(F);c.keys.KeyI=false;F.inp.grab=dt>0.3&&dt<0.37;if(dt>0.5)nxt();}
   else if(s[0]==='pick'){c.keys.KeyI=false;let b=null,bd=1e9;for(const q of c.buckets){if(q.state!=='floor'||(s[3]&&q.kind!==s[3]))continue;const d=Math.hypot(q.m.position.x-s[1],q.m.position.z-s[2]);if(d<bd){bd=d;b=q;}}
     if(P.held){nxt();return;}if(!b){nxt();return;}const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);
     if(d>0.75&&!s[3])H.go(F,b.m.position.x,b.m.position.z,0.8);else if(d>0.95)H.go(F,b.m.position.x,b.m.position.z,0.5);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;}}}};

T.washA={seed:2,pre:0.3,n:120,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.6,-3,-Math.PI/2,0);c.grace=99;const sh=c.flat.lights.sun.shadow;sh.mapSize.set(4096,4096);if(sh.map){sh.map.dispose();sh.map=null;}},
 script:(t,F)=>{F.pad();H.go(F,-4.6,-14.5,1);}};
T.washB={seed:2,pre:0.3,n:120,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.6,-3,-Math.PI/2,0);c.grace=99;const L=c.flat.lights,sun=L.sun;L.aim=(x,z)=>{sun.position.set(x-7,17,z+9);sun.target.position.set(x,0,z);sun.target.updateMatrixWorld();};},
 script:(t,F)=>{F.pad();H.go(F,-4.6,-14.5,1);}};
T.washC={seed:2,pre:0.3,n:120,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.6,-3,-Math.PI/2,0);c.grace=99;const sh=c.flat.lights.sun.shadow;sh.radius=1;sh.normalBias=0.06;},
 script:(t,F)=>{F.pad();H.go(F,-4.6,-14.5,1);}};

T.tvroom={seed:2,pre:0.3,n:3,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-2.4,-84.6,-Math.PI/2,3);c.grace=99;},
 script:(t,F)=>{F.pad();}};

T.wallt={seed:2,pre:0.3,n:70,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.5,-8.5,-Math.PI/2,0);c.grace=99;},
 script:(t,F)=>{F.pad();H.go(F,-4.5,-14.5,0.6);}};

T.wallt2={seed:2,pre:0.3,n:70,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.5,-8.5,-Math.PI/2,0);c.grace=99;const sh=c.flat.lights.sun.shadow;sh.bias=-0.003;sh.normalBias=0.09;},
 script:(t,F)=>{F.pad();H.go(F,-4.5,-14.5,0.6);}};
T.wallt3={seed:2,pre:0.3,n:70,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.5,-8.5,-Math.PI/2,0);c.grace=99;c.kit.traverse((o)=>{if(o.name==='MOD_BUILDING')o.castShadow=false;});},
 script:(t,F)=>{F.pad();H.go(F,-4.5,-14.5,0.6);}};

T.wallt4={seed:2,pre:0.3,n:70,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.5,-8.5,-Math.PI/2,0);c.grace=99;const sh=c.flat.lights.sun.shadow;sh.bias=-0.006;sh.normalBias=0.16;},
 script:(t,F)=>{F.pad();H.go(F,-4.5,-14.5,0.6);}};
T.wallt5={seed:2,pre:0.3,n:70,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(-4.5,-8.5,-Math.PI/2,0);c.grace=99;const sh=c.flat.lights.sun.shadow;sh.bias=-0.003;sh.normalBias=0.09;sh.mapSize.set(4096,4096);if(sh.map){sh.map.dispose();sh.map=null;}},
 script:(t,F)=>{F.pad();H.go(F,-4.5,-14.5,0.6);}};
module.exports=T;
