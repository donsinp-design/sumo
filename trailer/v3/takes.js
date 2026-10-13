// natural takes: the sumo is driven only by the game's own inputs (move, tiptoe, K, J, L), reacting to what the staff do
const T={};
T.HELP=`window.H={
 danger(c,extra){const P=c.P;for(const n of c.npcs){if(n.ko||n.a.st==='down')continue;if(Math.abs(n.a.y-P.y)>1.5)continue;const dx=P.x-n.a.x,dz=P.z-n.a.z,d=Math.hypot(dx,dz);const r=(n.range||6)*1.15+(extra||0);if(d>r)continue;let da=Math.atan2(dz,dx)-n.a.f;da=Math.atan2(Math.sin(da),Math.cos(da));if(Math.abs(da)<(n.half||0.62)+0.45)return n;}return null;},
 go(F,tx,tz,s){const P=F.c.P,dx=tx-P.x,dz=tz-P.z,d=Math.hypot(dx,dz)||1;F.inp.mx=dx/d*(s||1);F.inp.mz=dz/d*(s||1);return d;},
 stop(F){F.inp.mx=0;F.inp.mz=0;},
 pulse(F,t,period){return (Math.floor(t*30/(period||4))%2)===0;},
 sgo(F,tk,t,tx,tz,s){const P=F.c.P;if(tk.weave){const ex=tx-P.x,ez=tz-P.z,ed=Math.hypot(ex,ez)||1;if(ed>1.3){const w=(0.28*Math.sin(t*1.7+1)+0.12*Math.sin(t*3.9))*Math.min(1,(ed-1.3)/1.5);tx+=-ez/ed*w;tz+=ex/ed*w;}}const dx=tx-P.x,dz=tz-P.z,d=Math.hypot(dx,dz)||1,want=Math.atan2(dz,dx);const dt=Math.min(0.05,Math.max(0,t-(tk.lt===undefined?t:tk.lt)));tk.lt=t;
   if(tk.sa===undefined||tk.idle){const v=Math.hypot(P.vx,P.vz);tk.sa=v>0.3?Math.atan2(P.vz,P.vx):P.f;}tk.idle=false;
   const da=Math.atan2(Math.sin(want-tk.sa),Math.cos(want-tk.sa));tk.da=da;const mx=7.5*dt;tk.sa+=Math.max(-mx,Math.min(mx,da));
   const sp=(s||1)*(d<0.6?Math.max(0.35,d/0.6):1)*(Math.abs(da)>1.6&&d<1?0.4:1);F.inp.mx=Math.cos(tk.sa)*sp;F.inp.mz=Math.sin(tk.sa)*sp;return d;},
 sstop(F,tk){F.inp.mx=0;F.inp.mz=0;tk.idle=true;},
 gcam(F){const P=F.c.P,tk=F.take;F.cam(P.x,P.z-1.0,0,9.5,0.62);tk.camN=(tk.camN||0)+1;if(tk.camN<4){F.c.camT.set(P.x,0,P.z-1.0);}},   // (no pan in from the runner's default camera)
 gcap(F,t){const c=F.c,tk=F.take,N={smoke:'SMOKE BOMB!',vanish:'VANISH!',timedrag:'TIME DRAG!',sleepdart:'SLEEP DART!',trapdoor:'TRAP DOOR!',rewind:'REWIND!',phantom:'PHANTOM DASH!',torpedo:'TORPEDO!',daruma:'DARUMA ROLL!',giant:'GIANT!',stomp:'STOMP!',hands:'THOUSAND HANDS!',consume:'CONSUME!',bomb:'BOMB!',flop:'BELLY FLOP!'};
   if(c.gSkill&&c.gSkill!=='spit')tk.gid=c.gSkill;if(tk.gid&&!c.gSkill&&tk.capT===undefined)tk.capT=t;if(c.gSkill==='spit'&&tk.capT!==undefined&&!tk.sp0)tk.sp0=1;if(tk.sp0===1&&!c.gSkill){tk.sp0=2;tk.capT=t;tk.gid='spit';N.spit='SPIT!';}N.spit='SPIT!';
   if(c.gm&&c.gm.used&&tk.pullT===undefined&&!tk.gid)tk.pullT=t;if(tk.pullT!==undefined&&t-tk.pullT<1.4){F.cap('GACHA!');return;}
   F.cap(tk.capT!==undefined&&t-tk.capT<1.4?N[tk.gid]:'');}
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
// v5: knock2 with two seconds of lead before the knock, so the attendant's slip is clearly not the knock's doing
T.knock3={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=5.4;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: knock3 without the puddle by the attendant, so the knock lures him over and nobody slips
T.knock4={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=5.4;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: knock4 with the attendant further off, so he is round the corner before he can see the cart
T.knock5={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=9.0;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
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

T.knock6={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=7.0;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
T.knock7={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=6.2;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: knock4 with the attendant short-sighted / narrow-eyed, so he comes to look but does not spot him first
T.knock8={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=5.4;g.range=3.0;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: knock4 with the attendant further off, so he is round the corner before he can see the cart
T.knock5={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=9.0;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: knock4 with the attendant short-sighted / narrow-eyed, so he comes to look but does not spot him first
T.knock9={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=5.4;g.half=0.3;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: knock4 with the attendant further off, so he is round the corner before he can see the cart
T.knock5={seed:4,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.stage='key';F.at(-1.0,-46.35,-Math.PI/2,0);c.grace=1.5;const tk=F.take;tk.st=0;tk.ct=c.carts[0];
   const g=c.npcs[1];g.a.x=9.0;g.a.z=-44.4;g.i=1;g.wait=6;g.a.f=0;g.path=null;const th=c.npcs[3];th.a.x=-10.5;th.a.z=-30.5;th.i=0;th.wait=60;th.a.f=-Math.PI/2;th.path=null;c.puddles=c.puddles.filter((q)=>!(q.x>2&&q.z<-40&&q.z>-50));},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,ct=tk.ct;F.pad();
   if(tk.st===0){H.stop(F);P.f=-Math.PI/2;if(t>2.8){tk.st=1;tk.k=t;}}
   else if(tk.st===1){P.f=-Math.PI/2;F.inp.push=(t-tk.k)<0.07;if(t-tk.k>0.42)tk.st=2;}
   else if(tk.st===2){H.stop(F);P.f=Math.PI;tk.st=3;}
   else if(tk.st===3){H.stop(F);c.keys.KeyI=true;if(!tk.ip||(!P.hidden&&t-tk.ip>0.2)){c.iPress=true;tk.ip=t;}if(P.hidden)tk.st=4;}
   else{c.keys.KeyI=true;H.stop(F);}}};
// v5: vend3, but he drinks the second can too (J), and stays put for the burp
T.vend4={seed:8,pre:0.6,n:330,
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
   else if(tk.st===5){H.stop(F);if(!tk.t5)tk.t5=t;P.f=0;F.inp.push=t-tk.t5>0.3&&t-tk.t5<0.37;if(t-tk.t5>4.5)tk.st=6;}
   else{H.stop(F);}}};
// v5: the vending machine. Thump, thump, KRRASH; he grabs a can, and when the attendant comes for him he throws it so it
// bursts into a soda puddle beside him, steps round behind the puddle, the attendant runs at him and slips; then he drinks
// a can while they're down, and burps
T.vend5={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){H.stop(F);const g=guard();if(g&&g.d<7.5){   // pick a short throw (into a wall close by) roughly across the attendant's line
       const ga=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);let best=null;
       for(let a=-Math.PI;a<Math.PI;a+=Math.PI/24){const L=Math.max(1,c.reach(P.x,P.z,a,8)-0.6);if(L<1.0||L>2.6)continue;const lx=P.x+Math.cos(a)*L,lz=P.z+Math.sin(a)*L;
         const ux=lx-g.n.a.x,uz=lz-g.n.a.z,ul=Math.hypot(ux,uz)||1,tx=lx+ux/ul*1.4,tz=lz+uz/ul*1.4;if(c.inWall(tx,tz)||!c.clear(P.x,P.z,tx,tz))continue;
         let da=Math.abs(Math.atan2(Math.sin(a-ga),Math.cos(a-ga)));const sc=Math.abs(da-Math.PI/2)+Math.hypot(tx-P.x,tz-P.z)*0.15;if(!best||sc<best.sc)best={a,lx,lz,tx,tz,sc};}
       if(best){tk.th=best;P.f=best.a;tk.st=4;tk.t4=t;}}}
   else if(tk.st===4){H.stop(F);P.f=tk.th.a;F.inp.grab=t-tk.t4<0.07;if(!P.held&&t-tk.t4>0.45){tk.st=5;}}
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const d=H.go(F,tk.th.tx,tk.th.tz,1);if(d<0.25){tk.st=6;tk.t6=t;}}
   else if(tk.st===6){H.stop(F);const g=guard();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>4){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: vend5, but the can is thrown onto the route the attendant is about to run, so he hits the soda at speed
T.vend6={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){H.stop(F);const g=guard();if(g&&g.d<8&&g.n.path&&g.n.path.length){   // throw it onto the route the attendant is about to run
       const pts=[[g.n.a.x,g.n.a.z]].concat(g.n.path.slice(g.n.pi||0));let best=null;
       for(let a=-Math.PI;a<Math.PI;a+=Math.PI/36){const L=Math.max(1,c.reach(P.x,P.z,a,8)-0.6);if(L>5)continue;const lx=P.x+Math.cos(a)*L,lz=P.z+Math.sin(a)*L;
         let acc=0,bestD=1e9,along=0;for(let q=0;q<pts.length-1;q++){const ax=pts[q][0],az=pts[q][1],bx=pts[q+1][0],bz=pts[q+1][1],sx=bx-ax,sz=bz-az,sl=Math.hypot(sx,sz)||1e-4;let u=((lx-ax)*sx+(lz-az)*sz)/(sl*sl);u=Math.max(0,Math.min(1,u));const d=Math.hypot(ax+sx*u-lx,az+sz*u-lz);if(d<bestD){bestD=d;along=acc+u*sl;}acc+=sl;}
         if(bestD>0.4||along<1.6)continue;const fly=Math.hypot(g.n.a.x-(P.x+lx)/2,g.n.a.z-(P.z+lz)/2);if(fly<1.0)continue;const sc=bestD+Math.abs(along-2.6)*0.2;if(!best||sc<best.sc)best={a,lx,lz,tx:P.x,tz:P.z,sc};}
       if(best){tk.th=best;P.f=best.a;tk.st=4;tk.t4=t;}}}
   else if(tk.st===4){H.stop(F);P.f=tk.th.a;F.inp.grab=t-tk.t4<0.07;if(!P.held&&t-tk.t4>0.45){tk.st=5;}}
   else if(tk.st===5){H.stop(F);tk.st=6;tk.t6=t;}
   else if(tk.st===6){H.stop(F);const g=guard();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>4){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: vend6, and after the throw he steps behind the puddle so the attendant has to run through it to reach him
T.vend7={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){H.stop(F);tk.can=P.held;const g=guard();if(g&&g.d<8&&g.n.path&&g.n.path.length){   // throw it onto the route the attendant is about to run
       const pts=[[g.n.a.x,g.n.a.z]].concat(g.n.path.slice(g.n.pi||0));let best=null;
       for(let a=-Math.PI;a<Math.PI;a+=Math.PI/36){const L=Math.max(1,c.reach(P.x,P.z,a,8)-0.6);if(L>5)continue;const lx=P.x+Math.cos(a)*L,lz=P.z+Math.sin(a)*L;
         let acc=0,bestD=1e9,along=0;for(let q=0;q<pts.length-1;q++){const ax=pts[q][0],az=pts[q][1],bx=pts[q+1][0],bz=pts[q+1][1],sx=bx-ax,sz=bz-az,sl=Math.hypot(sx,sz)||1e-4;let u=((lx-ax)*sx+(lz-az)*sz)/(sl*sl);u=Math.max(0,Math.min(1,u));const d=Math.hypot(ax+sx*u-lx,az+sz*u-lz);if(d<bestD){bestD=d;along=acc+u*sl;}acc+=sl;}
         if(bestD>0.4||along<1.6)continue;const fly=Math.hypot(g.n.a.x-(P.x+lx)/2,g.n.a.z-(P.z+lz)/2);if(fly<1.0)continue;const sc=bestD+Math.abs(along-2.6)*0.2;if(!best||sc<best.sc)best={a,lx,lz,tx:P.x,tz:P.z,sc};}
       if(best){tk.th=best;P.f=best.a;tk.st=4;tk.t4=t;}}}
   else if(tk.st===4){H.stop(F);P.f=tk.th.a;if(tk.n0===undefined)tk.n0=c.puddles.length;F.inp.grab=t-tk.t4<0.07;if(!P.held&&t-tk.t4>0.45){tk.st=5;}}
   else if(tk.st===5){H.stop(F);const q=c.puddles.length>tk.n0?c.puddles[c.puddles.length-1]:null;if(q){tk.q=q;tk.st=5.5;}else if(t-tk.t4>1.5){tk.st=6;tk.t6=t;}}
   else if(tk.st===5.5){const g=guard(),q=tk.q;if(P.st!=='free'||!g){H.stop(F);if(!g){tk.st=6;tk.t6=t;}return;}const ux=q.x-g.n.a.x,uz=q.z-g.n.a.z,ul=Math.hypot(ux,uz)||1;let tx=q.x+ux/ul*0.85,tz=q.z+uz/ul*0.85;if(c.inWall(tx,tz)){tx=P.x;tz=P.z;}const d=H.go(F,tx,tz,1);if(d<0.2){H.stop(F);P.f=Math.atan2(-uz,-ux);}if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t4>6){tk.st=7;tk.k=0;}}
   else if(tk.st===6){H.stop(F);const g=guard();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>4){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: the vending machine. KRRASH; he grabs a can and throws it across the room; the landing brings the attendant running
// into the soda and he slips; meanwhile he picks up another can, drinks it, and burps
T.vend8={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){H.stop(F);const g=guard();if(g&&g.d<9){   // throw it across the room: the crash brings the attendant running, straight into the soda
       let best=null;for(let a=-Math.PI;a<Math.PI;a+=Math.PI/36){const L=Math.max(1,c.reach(P.x,P.z,a,8)-0.6);if(L<3.2)continue;const lx=P.x+Math.cos(a)*L,lz=P.z+Math.sin(a)*L;
         let ok=true;for(const n of c.npcs){if(n.ko)continue;const sx=lx-P.x,sz=lz-P.z,u=Math.max(0,Math.min(1,((n.a.x-P.x)*sx+(n.a.z-P.z)*sz)/(L*L)));if(Math.hypot(P.x+sx*u-n.a.x,P.z+sz*u-n.a.z)<1.3)ok=false;}if(!ok)continue;
         const gd=Math.hypot(lx-g.n.a.x,lz-g.n.a.z);if(gd<2.2)continue;const sc=Math.abs(gd-3.2);if(!best||sc<best.sc)best={a,lx,lz,sc};}
       if(best){tk.th=best;P.f=best.a;tk.st=4;tk.t4=t;}}}
   else if(tk.st===4){H.stop(F);P.f=tk.th.a;F.inp.grab=t-tk.t4<0.07;if(!P.held&&t-tk.t4>0.45){tk.st=6;tk.t6=t;}}
   else if(tk.st===6){H.stop(F);P.f=Math.atan2(tk.th.lz-P.z,tk.th.lx-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>5){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: the vending machine. KRRASH; he grabs a can, slams it down where the attendant is running to (the crash), steps back;
// the attendant runs into the soda and slips; meanwhile he picks up another can, drinks it, and burps
T.vend9={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){H.stop(F);const g=guard();if(g&&g.n.path&&g.n.path.length){   // where the attendant is running to (the crash), and from which way
       const p=g.n.path,e=p[p.length-1],q=p.length>1?p[p.length-2]:[g.n.a.x,g.n.a.z];let dx=e[0]-q[0],dz=e[1]-q[1];const l=Math.hypot(dx,dz)||1;dx/=l;dz/=l;
       tk.e={x:e[0],z:e[1],dx,dz};tk.st=3.5;}}
   else if(tk.st===3.5){const e=tk.e,sx=e.x+e.dx*1.0,sz=e.z+e.dz*1.0;const d=H.go(F,sx,sz,1);if(d<0.15){H.stop(F);P.f=Math.atan2(-e.dz,-e.dx);tk.st=4;tk.t4=t;}}
   else if(tk.st===4){H.stop(F);const e=tk.e;P.f=Math.atan2(-e.dz,-e.dx);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.6){tk.st=5;}}   // hold K: slammed down, soda everywhere
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const e=tk.e;const d=H.go(F,e.x+e.dx*2.1,e.z+e.dz*2.1,0.8);if(d<0.15){tk.st=6;tk.t6=t;}}
   else if(tk.st===6){H.stop(F);const e=tk.e;P.f=Math.atan2(-e.dz,-e.dx);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>5){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: the vending machine. KRRASH; he grabs a can, walks off a few steps and, when the attendant comes from the machine,
// throws it back at them: soda across their path, they slip; then he drinks another can and burps
T.vend10={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){const d=H.go(F,5.8,-40.2,1);if(d<0.2){H.stop(F);P.f=0;tk.st=3.5;}}
   else if(tk.st===3.5){H.stop(F);P.f=0;const g=guard();if(g&&g.n.a.x-P.x>2.0&&g.d<6.5){const L=Math.max(1,c.reach(P.x,P.z,0,8)-0.6);tk.L=L;if(g.d>L+0.6||g.d<2.6){tk.st=4;tk.t4=t;}}}
   else if(tk.st===4){H.stop(F);P.f=0;F.inp.grab=t-tk.t4<0.07;if(!P.held&&t-tk.t4>0.45){tk.st=6;tk.t6=t;}}
   else if(tk.st===6){H.stop(F);const g=guard();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>5){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: the vending machine. KRRASH; he grabs a can, slams it down in the gap the attendant runs through, steps back;
// the attendant hits the soda at a run and slips; meanwhile he picks up another can, drinks it, and burps
T.vend11={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){const d=H.go(F,9.6,-40.2,0.9);if(d<0.12){H.stop(F);tk.st=4;tk.t4=t;}}
   else if(tk.st===4){H.stop(F);P.f=-2.13;F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.6){tk.st=5;}}   // hold K: slammed down in the gap they come through
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const d=H.go(F,10.4,-39.0,0.8);if(d<0.15){tk.st=6;tk.t6=t;}}
   else if(tk.st===6){H.stop(F);const g=guard();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&n.a.slipFall)||t-tk.t6>5){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5: vend11, drinking the moment the attendant is down
T.vend12={seed:8,pre:0.6,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;F.take.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const guard=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st==='down'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode==='route'||n.mode==='return')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.8);if(d<0.15){tk.st=1;tk.t1=t;}}
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.0)tk.st=2;}
   else if(tk.st===2){if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;tk.k=0;}else pick();}
   else if(tk.st===3){const d=H.go(F,9.6,-40.2,0.9);if(d<0.12){H.stop(F);tk.st=4;tk.t4=t;}}
   else if(tk.st===4){H.stop(F);P.f=-2.13;F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.6){tk.st=5;}}   // hold K: slammed down in the gap they come through
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const d=H.go(F,10.4,-39.0,0.8);if(d<0.15){tk.st=6;tk.t6=t;}}
   else if(tk.st===6){H.stop(F);const g=guard();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(c.npcs.some((n)=>n.a.st==='down'&&!n.ko)||t-tk.t6>5){tk.st=7;tk.k=0;}}
   else if(tk.st===7){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=8;tk.t8=t;F.inp.grab=false;}else pick();}
   else if(tk.st===8){H.stop(F);F.inp.push=t-tk.t8>0.1&&t-tk.t8<0.17;if(t-tk.t8>4.5)tk.st=9;}
   else{H.stop(F);}}};
// v5c: wake4 steered like a person: the stick turns gradually (no 90 degree snaps), corners are cut, dashes start once he faces the way he means to go
T.wake5={seed:2,pre:2.0,n:1560,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';const tk=F.take;tk.st=0;tk.i=0;
   tk.q=[['go',1.0,-1.0,'w'],['go',1.2,0.9,'w'],['dash',-6.5,0.9,1.0],['go',-9.5,-3.2,'w'],['pick',-10.2,-2.5,'oke'],['go',-4.6,-2.6,'w'],['face',-Math.PI/2],['throw'],['wait',0.5],['pud'],['wait',0.3],['dashp',-4.6,-14.0,1.6],['wait',1.2],['go',-4.6,-12.6,'w'],['go',-4.6,-14.5,'w'],['go',0.6,-17.0,'w'],['dash',6.2,-24.6,1.4],['pick',7.6,-23.5,'stool'],['go',6.75,-28.0,'a'],['go',10.2,-28.6,'a'],['face',-Math.PI/2],['throw'],['wait',1.0],['go',1.5,-28.3,'a'],['go',-7.5,-28.3,'a'],['go',-10.6,-29.6,'a'],['go',-10.6,-38.0,'a'],['go',-10.4,-39.6,'a'],['use'],['end']];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>5.2){c.wake();tk.st=1;tk.t1=t;}return;}
   if(tk.st===1){if(t-tk.t1>1.2)tk.st=2;return;}
   const s=tk.q[tk.i];if(!s||s[0]==='end'){H.stop(F);c.keys.KeyI=false;return;}
   const nxt=()=>{tk.i++;tk.s0=undefined;tk.k=0;tk.dd=0;};if(tk.s0===undefined)tk.s0=t;const dt=t-tk.s0;
   if(P.st!=='free'&&s[0]!=='wait'){H.sstop(F,tk);return;}
   if(s[0]==='go'){let near=false;if(s[3]==='a')for(const n of c.npcs){if(n.ko||Math.abs(n.a.y-P.y)>1.5)continue;if(Math.hypot(n.a.x-P.x,n.a.z-P.z)<4.6)near=true;}
     c.keys.KeyI=near;if(near&&H.danger(c,-1.5)){H.sstop(F,tk);return;}{const q=tk.q[tk.i+1];if(H.sgo(F,tk,t,s[1],s[2],1)<((q&&q[0]==='go')?0.85:0.35))nxt();}}
   else if(s[0]==='dashp'){c.keys.KeyI=false;const q=tk.pud;const tx=q?q.x:s[1];H.sgo(F,tk,t,tx,s[2],1);if(!tk.dd&&Math.abs(tk.da)<0.3){F.inp.dash=true;tk.dd=t;}if(tk.dd&&t-tk.dd>s[3])nxt();}
   else if(s[0]==='dash'){c.keys.KeyI=false;const d=H.sgo(F,tk,t,s[1],s[2],1);if(!tk.dd&&Math.abs(tk.da)<0.3){F.inp.dash=true;tk.dd=t;}if((tk.dd&&t-tk.dd>s[3])||d<0.4)nxt();}
   else if(s[0]==='pud'){const q=c.puddles[c.puddles.length-1];tk.pud=q;if(q){const back=Math.min(-0.3,q.z+3.0);if(H.sgo(F,tk,t,q.x,back,0.8)<0.3){H.sstop(F,tk);nxt();}}else nxt();}
   else if(s[0]==='face'){H.sstop(F,tk);const da=Math.atan2(Math.sin(s[1]-P.f),Math.cos(s[1]-P.f));P.f+=Math.max(-0.33,Math.min(0.33,da));if(dt>0.2&&Math.abs(da)<0.05)nxt();}
   else if(s[0]==='wait'){H.sstop(F,tk);if(dt>s[1])nxt();}
   else if(s[0]==='throw'){H.sstop(F,tk);F.inp.grab=dt<0.07;if(dt>0.4)nxt();}
   else if(s[0]==='use'){H.sstop(F,tk);c.keys.KeyI=false;F.inp.grab=dt>0.3&&dt<0.37;if(dt>0.5)nxt();}
   else if(s[0]==='pick'){c.keys.KeyI=false;let b=null,bd=1e9;for(const q of c.buckets){if(q.state!=='floor'||(s[3]&&q.kind!==s[3]))continue;const d=Math.hypot(q.m.position.x-s[1],q.m.position.z-s[2]);if(d<bd){bd=d;b=q;}}
     if(P.held){nxt();return;}if(!b){nxt();return;}const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);
     if(d>0.75&&!s[3])H.sgo(F,tk,t,b.m.position.x,b.m.position.z,0.8);else if(d>0.95)H.sgo(F,tk,t,b.m.position.x,b.m.position.z,0.5);else{H.sstop(F,tk);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;}}}};
// v5c: shove2, but the attendant shoves the box for a full 2 s; he stands up, they jump back; he slaps them out cold
T.shove3={seed:5,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;F.box();c.P.st='free';c.P.dur=0;c.noDuck=0;c.P.boxHide=true;c.wasBoxHide=true;c.ballK=1;c.stage='exit';F.at(1.5,-77.4,Math.PI,3);c.grace=3.5;c.keys.KeyI=true;const tk=F.take;tk.st=1;const n=tk.n=c.npcs[9];n.a.x=-2.6;n.a.z=-77.4;n.a.f=0;n.i=1;n.wait=0;n.mode='route';n.path=null;c.goTo(n,9.6,-77.4);},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();
   if(tk.st===1){H.stop(F);c.keys.KeyI=true;const nd=Math.hypot(n.a.x-P.x,n.a.z-P.z);if((n.pushing2||n.clr)&&nd<1.7){tk.sh=tk.sh||t;if(t-tk.sh>2.0){tk.st=2;tk.up=t;}}}
   else if(tk.st===2){H.stop(F);c.keys.KeyI=false;if(t-tk.up>0.75){tk.st=3;tk.t3=t;}}
   else if(tk.st===3){c.keys.KeyI=false;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);P.f=Math.atan2(n.a.z-P.z,n.a.x-P.x);if(d>1.1&&!n.ko)H.go(F,n.a.x,n.a.z,0.8);else{H.stop(F);F.inp.push=!n.ko&&!(tk.sl&&t-tk.sl<0.5);if(F.inp.push)tk.sl=t;}}
   else{H.stop(F);}}};
// v5c: the vending machine, as the owner described it. He walks through a puddle to the machine, leaving big wet footprints;
// an attendant finds the trail and follows it; he thumps the machine (they hear it and hurry over); KRRASH, cans roll out,
// one splits and sprays; he grabs a can and smashes it on the floor in front of them as they come; they hit the soda and slip.
T.vend13={seed:8,pre:14,n:420,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.6,V.z+0.3,0,0);c.grace=0;
   c.spill(V.x0-5.4,V.z+0.3,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-11.8,V.z-0.6,Math.PI);n.alarm=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.stopWarm=true;tk.t0=t;tk.n.a.f=0;}}
   else if(tk.st===0.5){H.stop(F);P.f=0;if(t-tk.t0>2.2){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5c: vend13 with the walk through the puddle on camera (the footprints are drawn by the frame update, not the warm-up)
T.vend14={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.6,V.z+0.3,0,0);c.grace=0;
   c.spill(V.x0-5.4,V.z+0.3,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-10.6,V.z-0.6,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){H.stop(F);P.f=0;if(t-tk.t0>2.2){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5c: vend14 from the old start spot (the other one was against a bench)
T.vend15={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;
   c.spill(V.x0-3.3,V.z+0.4,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-8.2,V.z-0.6,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){H.stop(F);P.f=0;if(t-tk.t0>2.2){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5c: vend15 with the puddle on the line he actually walks
T.vend16={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-4.2,V.z+0.4,0,0);c.grace=0;
   c.spill(V.x0-2.7,V.z-0.55,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-8.2,V.z-0.6,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){H.stop(F);P.f=0;if(t-tk.t0>2.2){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5c: vend16 starting further back, so five footprints lead up to the machine
T.vend17={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-8.2,V.z-0.6,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){H.stop(F);P.f=0;if(t-tk.t0>2.2){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5c: vend17 with the attendant further off (back turned while he wades through), and no slip before the smash
T.vend18={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-10.2,V.z-0.6,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   if(tk.st<4&&tk.n)tk.n.slipCd=Math.max(tk.n.slipCd||0,0.2);   // (he keeps his feet until the can is smashed in front of him)
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){H.stop(F);P.f=0;if(t-tk.t0>2.2){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5d: shove3, but the 2 s count only runs while they actually have their shoulder to the box (sweating, ふんっ / 重っ)
T.shove4={seed:5,pre:0.4,n:420,
 setup:(F)=>{const c=F.c;F.box();c.P.st='free';c.P.dur=0;c.noDuck=0;c.P.boxHide=true;c.wasBoxHide=true;c.ballK=1;c.stage='exit';F.at(1.5,-77.4,Math.PI,3);c.grace=3.5;c.keys.KeyI=true;const tk=F.take;tk.st=1;const n=tk.n=c.npcs[9];n.a.x=-2.6;n.a.z=-77.4;n.a.f=0;n.i=1;n.wait=0;n.mode='route';n.path=null;c.goTo(n,9.6,-77.4);},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,n=tk.n;F.pad();
   if(tk.st===1){H.stop(F);c.keys.KeyI=true;const nd=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(n.pushing2&&nd<1.7){tk.pt=(tk.pt||0)+(tk.lt?t-tk.lt:0);}tk.lt=t;if(tk.pt>2.0||(tk.pt>0.8&&!n.clr)){tk.st=2;tk.up=t;}}
   else if(tk.st===2){H.stop(F);c.keys.KeyI=false;if(t-tk.up>0.75){tk.st=3;tk.t3=t;}}
   else if(tk.st===3){c.keys.KeyI=false;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);P.f=Math.atan2(n.a.z-P.z,n.a.x-P.x);if(d>1.1&&!n.ko)H.go(F,n.a.x,n.a.z,0.8);else{H.stop(F);F.inp.push=!n.ko&&!(tk.sl&&t-tk.sl<0.5);if(F.inp.push)tk.sl=t;}}
   else{H.stop(F);}}};
// v5d: vend18, but he only starts thumping once the attendant has seen the footprints and is following them
T.vend19={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-9.4,V.z-0.4,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   if(tk.st<4&&tk.n)tk.n.slipCd=Math.max(tk.n.slipCd||0,0.2);   // (he keeps his feet until the can is smashed in front of him)
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){H.stop(F);P.f=0;const n=tk.n;if(n.inv&&!tk.seen)tk.seen=t;if((tk.seen&&t-tk.seen>1.0)||t-tk.t0>9){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5d: through the locker room at a charge: two attendants walking away down the long aisle (they haven't seen him)
// get bowled over one after the other (a charge only flattens someone who hasn't made him out yet)
T.chargeko={seed:2,pre:0.3,n:200,
 setup:(F)=>{const c=F.c,tk=F.take;c.outOfBath=true;c.stage='key';F.at(9.6,-28.3,Math.PI,0);c.grace=6;tk.st=0;
   const A=tk.A=c.npcs[0],B=tk.B=c.npcs[2];
   for(const [n,x] of [[A,4.6],[B,0.6]]){n.a.x=x;n.a.z=-28.3;n.a.f=Math.PI;n.route=[[x,-28.3,0,Math.PI],[x-9,-28.3,0,Math.PI]];n.i=1;n.wait=0;n.mode='route';n.path=null;n.alarm=0;c.goTo(n,x-9,-28.3);n.mode='route';}
   F.park([A,B]);tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();c.grace=Math.max(c.grace,0.5);
   const tgt=[tk.A,tk.B].find((n)=>!n.ko&&n.a.st!=='down');
   const charge=(n)=>{const dx=n.a.x-P.x,dz=n.a.z-P.z,d=Math.hypot(dx,dz)||1;F.inp.mx=dx/d;F.inp.mz=dz/d;F.inp.dash=P.st==='free'&&P.cd<=0;};
   if(tk.st===0){H.go(F,P.x-1,-28.3,0.6);if(t>0.7)tk.st=1;}
   else if(tk.st===1){if(tgt)charge(tgt);else{tk.st=2;tk.t2=t;}}
   else{H.stop(F);}}};
// v5d: vend19, tiptoeing through the puddle (silent, still leaves prints) so the attendant finds the trail, not him
T.vend20={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-9.4,V.z-0.4,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   if(tk.st<4&&tk.n)tk.n.slipCd=Math.max(tk.n.slipCd||0,0.2);   // (he keeps his feet until the can is smashed in front of him)
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){c.keys.KeyI=true;const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){c.keys.KeyI=false;H.stop(F);P.f=0;const n=tk.n;if(n.inv&&!tk.seen)tk.seen=t;if((tk.seen&&t-tk.seen>1.0)||t-tk.t0>9){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.75);F.inp.push=((t-tk.t1)%0.75)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5e: wake5 without the walk back after the bucket (he throws it from where he is, towards the door), round the bath in a curve, a slight weave on the stick
T.wake6={seed:2,pre:2.0,n:1560,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';const tk=F.take;tk.st=0;tk.i=0;
   tk.weave=true;tk.q=[['go',1.0,-1.0,'w'],['go',0.6,0.9,'w'],['dash',-5.6,0.6,1.0],['go',-8.6,-2.4,'w'],['go',-9.6,-3.4,'w'],['aim',-10.2,-2.45],['grab'],['go',-7.6,-4.6,'w'],['aim',-4.8,-12.6],['throw'],['wait',0.5],['pud'],['wait',0.3],['dashp',-4.6,-14.0,1.6],['wait',1.2],['go',-4.6,-12.6,'w'],['go',-4.6,-14.5,'w'],['go',0.6,-17.0,'w'],['dash',6.2,-24.6,1.4],['pick',7.6,-23.5,'stool'],['go',6.75,-28.0,'a'],['go',10.2,-28.6,'a'],['face',-Math.PI/2],['throw'],['wait',1.0],['go',1.5,-28.3,'a'],['go',-7.5,-28.3,'a'],['go',-10.6,-29.6,'a'],['go',-10.6,-38.0,'a'],['go',-10.4,-39.6,'a'],['use'],['end']];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>5.2){c.wake();tk.st=1;tk.t1=t;}return;}
   if(tk.st===1){if(t-tk.t1>1.2)tk.st=2;return;}
   const s=tk.q[tk.i];if(!s||s[0]==='end'){H.stop(F);c.keys.KeyI=false;return;}
   const nxt=()=>{tk.i++;tk.s0=undefined;tk.k=0;tk.dd=0;};if(tk.s0===undefined)tk.s0=t;const dt=t-tk.s0;
   if(P.st!=='free'&&s[0]!=='wait'){H.sstop(F,tk);return;}
   if(s[0]==='go'){let near=false;if(s[3]==='a')for(const n of c.npcs){if(n.ko||Math.abs(n.a.y-P.y)>1.5)continue;if(Math.hypot(n.a.x-P.x,n.a.z-P.z)<4.6)near=true;}
     c.keys.KeyI=near;if(near&&H.danger(c,-1.5)){H.sstop(F,tk);return;}{const q=tk.q[tk.i+1];if(H.sgo(F,tk,t,s[1],s[2],1)<((q&&q[0]==='go')?0.85:0.35))nxt();}}
   else if(s[0]==='dashp'){c.keys.KeyI=false;const q=tk.pud;const tx=q?q.x:s[1];H.sgo(F,tk,t,tx,s[2],1);if(!tk.dd&&Math.abs(tk.da)<0.3){F.inp.dash=true;tk.dd=t;}if(tk.dd&&t-tk.dd>s[3])nxt();}
   else if(s[0]==='dash'){c.keys.KeyI=false;const d=H.sgo(F,tk,t,s[1],s[2],1);if(!tk.dd&&Math.abs(tk.da)<0.3){F.inp.dash=true;tk.dd=t;}if((tk.dd&&t-tk.dd>s[3])||d<0.4)nxt();}
   else if(s[0]==='pud'){const q=c.puddles[c.puddles.length-1];tk.pud=q;if(q){const back=Math.min(-0.3,q.z+3.0);if(H.sgo(F,tk,t,q.x,back,0.8)<0.3){H.sstop(F,tk);nxt();}}else nxt();}
   else if(s[0]==='grab'){H.sstop(F,tk);F.inp.grab=dt<0.07;if(P.held&&dt>0.2)nxt();else if(dt>1.0)nxt();}
   else if(s[0]==='aim'){H.sstop(F,tk);const want=Math.atan2(s[2]-P.z,s[1]-P.x),da=Math.atan2(Math.sin(want-P.f),Math.cos(want-P.f));P.f+=Math.max(-0.33,Math.min(0.33,da));if(dt>0.2&&Math.abs(da)<0.05)nxt();}
   else if(s[0]==='face'){H.sstop(F,tk);const da=Math.atan2(Math.sin(s[1]-P.f),Math.cos(s[1]-P.f));P.f+=Math.max(-0.33,Math.min(0.33,da));if(dt>0.2&&Math.abs(da)<0.05)nxt();}
   else if(s[0]==='wait'){H.sstop(F,tk);if(dt>s[1])nxt();}
   else if(s[0]==='throw'){H.sstop(F,tk);F.inp.grab=dt<0.07;if(dt>0.4)nxt();}
   else if(s[0]==='use'){H.sstop(F,tk);c.keys.KeyI=false;F.inp.grab=dt>0.3&&dt<0.37;if(dt>0.5)nxt();}
   else if(s[0]==='pick'){c.keys.KeyI=false;let b=null,bd=1e9;for(const q of c.buckets){if(q.state!=='floor'||(s[3]&&q.kind!==s[3]))continue;const d=Math.hypot(q.m.position.x-s[1],q.m.position.z-s[2]);if(d<bd){bd=d;b=q;}}
     if(P.held){if(s[3]&&P.held.kind!==s[3]){F.inp.grab=false;P.held.state='floor';}nxt();return;}if(!b){nxt();return;}const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);
     if(d>0.75&&!s[3])H.sgo(F,tk,t,b.m.position.x,b.m.position.z,0.8);else if(d>0.6)H.sgo(F,tk,t,b.m.position.x,b.m.position.z,0.45);else{H.sstop(F,tk);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;}}}};
// v5e: chargeko with the two attendants close together: one charge bowls over both
T.chargeko2={seed:2,pre:0.3,n:200,
 setup:(F)=>{const c=F.c,tk=F.take;c.outOfBath=true;c.stage='key';F.at(9.6,-28.3,Math.PI,0);c.grace=6;tk.st=0;
   const A=tk.A=c.npcs[0],B=tk.B=c.npcs[2];
   for(const [n,x] of [[A,6.0],[B,4.5]]){n.a.x=x;n.a.z=-28.3;n.a.f=Math.PI;n.route=[[x,-28.3,0,Math.PI],[x-9,-28.3,0,Math.PI]];n.i=1;n.wait=0;n.mode='route';n.path=null;n.alarm=0;c.goTo(n,x-9,-28.3);n.mode='route';}
   F.park([A,B]);tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();c.grace=Math.max(c.grace,0.5);
   const tgt=[tk.A,tk.B].find((n)=>!n.ko&&n.a.st!=='down');
   const charge=(n)=>{const dx=n.a.x-P.x,dz=n.a.z-P.z,d=Math.hypot(dx,dz)||1;F.inp.mx=dx/d;F.inp.mz=dz/d;F.inp.dash=P.st==='free'&&P.cd<=0;};
   if(tk.st===0){H.go(F,P.x-1,-28.3,0.6);if(t>0.7)tk.st=1;}
   else if(tk.st===1){if(tgt)charge(tgt);else{tk.st=2;tk.t2=t;}}
   else{H.stop(F);}}};
// v5e: pushes the laundry cart through into the laundry and dives into it on the move: it rolls on with him inside, towels fly out
T.cartdive={seed:4,pre:0.3,n:200,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const ct=c.carts[1];F.at(ct.x-1.0,ct.z,0,0);c.grace=1.5;const tk=F.take;tk.ct=ct;tk.st=0;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){H.stop(F);P.f=0;F.inp.grab=t>0.5&&t<0.57;if(P.cart){tk.st=1;}}
   else if(tk.st===1){const w=[[8.8,-49.6],[16,-49.6]][tk.w||0];if(H.go(F,w[0],w[1],1)<0.5)tk.w=(tk.w||0)+1;if(P.x>(+(globalThis.DIVEX||11.5))){tk.st=2;tk.t2=t;}}
   else if(tk.st===2){H.go(F,16,-49.6,1);c.keys.KeyI=true;if(t-tk.t2<0.05)c.iPress=true;if(P.hidden){tk.st=3;}}
   else{H.stop(F);c.keys.KeyI=true;}}};
// v5f (Lotus Eater): wake6 with its big moments held to the beat (sync steps wait until the song time; the startle is 12.85 s)
T.wake7={seed:2,pre:2.0,n:1560,
 setup:(F)=>{const c=F.c;c.asleep=true;c.el('.st-zzz').style.display='block';const tk=F.take;tk.st=0;tk.i=0;
   tk.weave=true;tk.q=[['go',1.0,-1.0,'w'],['go',0.6,0.9,'w'],['sync',16.26],['dash',-5.6,0.6,1.0],['go',-8.6,-2.4,'w'],['go',-9.6,-3.4,'w'],['aim',-10.2,-2.45],['grab'],['go',-7.6,-4.6,'w'],['aim',-4.8,-12.6],['sync',21.59],['throw'],['wait',0.5],['pud'],['wait',0.3],['sync',25.76],['dashp',-4.6,-14.0,1.6],['wait',1.2],['go',-4.6,-12.6,'w'],['go',-4.6,-14.5,'w'],['go',0.6,-17.0,'w'],['sync',31.93],['dash',6.2,-24.6,1.4],['pick',7.6,-23.5,'stool'],['go',6.75,-28.0,'a'],['go',10.2,-28.6,'a'],['face',-Math.PI/2],['sync',38.39],['throw'],['wait',1.0],['go',1.5,-28.3,'a'],['go',-7.5,-28.3,'a'],['go',-10.6,-29.6,'a'],['go',-10.6,-38.0,'a'],['go',-10.4,-39.6,'a'],['sync',54.31],['use'],['end']];},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take;F.pad();
   if(tk.st===0){if(t>5.2){c.wake();tk.st=1;tk.t1=t;}return;}
   if(tk.st===1){if(t-tk.t1>1.2)tk.st=2;return;}
   if(tk.tg===undefined&&P.st==='gasp')tk.tg=t;const s=tk.q[tk.i];if(!s||s[0]==='end'){H.stop(F);c.keys.KeyI=false;return;}
   const nxt=()=>{tk.i++;tk.s0=undefined;tk.k=0;tk.dd=0;};if(tk.s0===undefined)tk.s0=t;const dt=t-tk.s0;
   if(P.st!=='free'&&s[0]!=='wait'){H.sstop(F,tk);return;}
   if(s[0]==='go'){let near=false;if(s[3]==='a')for(const n of c.npcs){if(n.ko||Math.abs(n.a.y-P.y)>1.5)continue;if(Math.hypot(n.a.x-P.x,n.a.z-P.z)<4.6)near=true;}
     c.keys.KeyI=near;if(near&&H.danger(c,-1.5)){H.sstop(F,tk);return;}{const q=tk.q[tk.i+1];if(H.sgo(F,tk,t,s[1],s[2],1)<((q&&q[0]==='go')?0.85:0.35))nxt();}}
   else if(s[0]==='dashp'){c.keys.KeyI=false;const q=tk.pud;const tx=q?q.x:s[1];H.sgo(F,tk,t,tx,s[2],1);if(!tk.dd&&Math.abs(tk.da)<0.3){F.inp.dash=true;tk.dd=t;}if(tk.dd&&t-tk.dd>s[3])nxt();}
   else if(s[0]==='dash'){c.keys.KeyI=false;const d=H.sgo(F,tk,t,s[1],s[2],1);if(!tk.dd&&Math.abs(tk.da)<0.3){F.inp.dash=true;tk.dd=t;}if((tk.dd&&t-tk.dd>s[3])||d<0.4)nxt();}
   else if(s[0]==='pud'){const q=c.puddles[c.puddles.length-1];tk.pud=q;if(q){const back=Math.min(-0.3,q.z+3.0);if(H.sgo(F,tk,t,q.x,back,0.8)<0.3){H.sstop(F,tk);nxt();}}else nxt();}
   else if(s[0]==='sync'){H.sstop(F,tk);if(tk.tg!==undefined&&12.85+(t-tk.tg)>=s[1])nxt();}
   else if(s[0]==='grab'){H.sstop(F,tk);F.inp.grab=dt<0.07;if(P.held&&dt>0.2)nxt();else if(dt>1.0)nxt();}
   else if(s[0]==='aim'){H.sstop(F,tk);const want=Math.atan2(s[2]-P.z,s[1]-P.x),da=Math.atan2(Math.sin(want-P.f),Math.cos(want-P.f));P.f+=Math.max(-0.33,Math.min(0.33,da));if(dt>0.2&&Math.abs(da)<0.05)nxt();}
   else if(s[0]==='face'){H.sstop(F,tk);const da=Math.atan2(Math.sin(s[1]-P.f),Math.cos(s[1]-P.f));P.f+=Math.max(-0.33,Math.min(0.33,da));if(dt>0.2&&Math.abs(da)<0.05)nxt();}
   else if(s[0]==='wait'){H.sstop(F,tk);if(dt>s[1])nxt();}
   else if(s[0]==='throw'){H.sstop(F,tk);F.inp.grab=dt<0.07;if(dt>0.4)nxt();}
   else if(s[0]==='use'){H.sstop(F,tk);c.keys.KeyI=false;F.inp.grab=dt>0.3&&dt<0.37;if(dt>0.5)nxt();}
   else if(s[0]==='pick'){c.keys.KeyI=false;let b=null,bd=1e9;for(const q of c.buckets){if(q.state!=='floor'||(s[3]&&q.kind!==s[3]))continue;const d=Math.hypot(q.m.position.x-s[1],q.m.position.z-s[2]);if(d<bd){bd=d;b=q;}}
     if(P.held){if(s[3]&&P.held.kind!==s[3]){F.inp.grab=false;P.held.state='floor';}nxt();return;}if(!b){nxt();return;}const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);
     if(d>0.75&&!s[3])H.sgo(F,tk,t,b.m.position.x,b.m.position.z,0.8);else if(d>0.6)H.sgo(F,tk,t,b.m.position.x,b.m.position.z,0.45);else{H.sstop(F,tk);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8<3;}}}};
// v5f: vend20 thumping once a beat (0.622 s, Lotus Eater)
T.vend21={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-9.4,V.z-0.4,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   if(tk.st<4&&tk.n)tk.n.slipCd=Math.max(tk.n.slipCd||0,0.2);   // (he keeps his feet until the can is smashed in front of him)
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){c.keys.KeyI=true;const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){c.keys.KeyI=false;H.stop(F);P.f=0;const n=tk.n;if(n.inv&&!tk.seen)tk.seen=t;if((tk.seen&&t-tk.seen>1.0)||t-tk.t0>9){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.622);F.inp.push=((t-tk.t1)%0.622)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5g: vend21 thumping every two beats of Pop Dat Thang (0.872 s)
T.vend22={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-9.4,V.z-0.4,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.7)H.go(F,b.m.position.x,b.m.position.z,0.6);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%8===1;if(tk.k>40){b._skip=true;tk.k=0;}}};
   if(tk.st<4&&tk.n)tk.n.slipCd=Math.max(tk.n.slipCd||0,0.2);   // (he keeps his feet until the can is smashed in front of him)
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){c.keys.KeyI=true;const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){c.keys.KeyI=false;H.stop(F);P.f=0;const n=tk.n;if(n.inv&&!tk.seen)tk.seen=t;if((tk.seen&&t-tk.seen>1.0)||t-tk.t0>9){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.872);F.inp.push=((t-tk.t1)%0.872)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>0.6)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<3.6){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.45;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};
// v5h: vend22 with three spinning cans: he watches them go, then grabs a still can quickly
T.vend23={seed:8,pre:0.2,n:460,
 setup:(F)=>{const c=F.c;c.outOfBath=true;const V=c.vend,tk=F.take;tk.st=0;F.at(V.x0-6.0,V.z-0.6,0,0);c.grace=0;
   c.spill(V.x0-4.7,V.z-0.6,0);const n=tk.n=c.npcs[1];F.npcAt(n,V.x0-9.4,V.z-0.4,Math.PI);n.alarm=0;tk.stopWarm=true;},
 script:(t,F)=>{const c=F.c,P=c.P,tk=F.take,V=c.vend;F.pad();
   const nearCan=()=>{let best=null,bd=1e9;for(const b of c.buckets){if(b.kind!=='can'||b.state!=='floor'||b._skip||!b.soda)continue;const d=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(d<bd){bd=d;best=b;}}return best;};
   const pick=()=>{const b=nearCan();if(!b)return;const bd=Math.hypot(b.m.position.x-P.x,b.m.position.z-P.z);if(bd>0.55)H.go(F,b.m.position.x,b.m.position.z,0.9);else{H.stop(F);P.f=Math.atan2(b.m.position.z-P.z,b.m.position.x-P.x);tk.k=(tk.k||0)+1;F.inp.grab=tk.k%4===1;if(tk.k>24){b._skip=true;tk.k=0;}}};
   if(tk.st<4&&tk.n)tk.n.slipCd=Math.max(tk.n.slipCd||0,0.2);   // (he keeps his feet until the can is smashed in front of him)
   const coming=()=>{let g=null,gd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||Math.abs(n.a.y-P.y)>1.5)continue;if(n.mode!=='goto'&&n.mode!=='chase')continue;const d=Math.hypot(n.a.x-P.x,n.a.z-P.z);if(d<gd){gd=d;g=n;}}return g?{n:g,d:gd}:null;};
   if(tk.st===0){c.keys.KeyI=true;const d=H.go(F,V.x0-0.75,V.z,0.75);if(d<0.15){H.stop(F);tk.st=0.5;tk.t0=t;const n=tk.n;F.npcAt(n,n.a.x,n.a.z,0);}}
   else if(tk.st===0.5){c.keys.KeyI=false;H.stop(F);P.f=0;const n=tk.n;if(n.inv&&!tk.seen)tk.seen=t;if((tk.seen&&t-tk.seen>1.0)||t-tk.t0>9){tk.st=1;tk.t1=t;}}   // the attendant picks up the trail
   else if(tk.st===1){H.stop(F);P.f=0;const k=Math.floor((t-tk.t1)/0.872);F.inp.push=((t-tk.t1)%0.872)<0.07&&k<3;if(V.broke&&!tk.br)tk.br=t;if(tk.br&&t-tk.br>1.4)tk.st=2;}
   else if(tk.st===2){if(P.st!=='free'){H.stop(F);return;}if(P.held&&P.held.kind==='can'){tk.st=3;F.inp.grab=false;}else pick();}
   else if(tk.st===3){H.stop(F);const g=coming();if(g)P.f=Math.atan2(g.n.a.z-P.z,g.n.a.x-P.x);if(g&&g.d<7){tk.st=4;tk.t4=t;tk.g=g.n;}}
   else if(tk.st===4){H.stop(F);P.f=Math.atan2(tk.g.a.z-P.z,tk.g.a.x-P.x);F.inp.grab=t-tk.t4<0.37;if(!P.held&&t-tk.t4>0.5){tk.st=5;tk.t5=t;}}   // hold K: smashed on the floor
   else if(tk.st===5){if(P.st!=='free'){H.stop(F);return;}const g=tk.g,ux=P.x-g.a.x,uz=P.z-g.a.z,ul=Math.hypot(ux,uz)||1;if(!tk.bk){tk.bk=[P.x+ux/ul*0.9,P.z+uz/ul*0.9];if(c.inWall(tk.bk[0],tk.bk[1]))tk.bk=[P.x,P.z];}
     if(H.go(F,tk.bk[0],tk.bk[1],0.9)<0.15||t-tk.t5>1.2){H.stop(F);tk.st=6;}}
   else{H.stop(F);const g=tk.g;if(g)P.f=Math.atan2(g.a.z-P.z,g.a.x-P.x);}}};

// ---- campaign gachas (stealth level): the locker-room aisle (x 0..10, z -33.9); the staff come at him (a chase), nothing staged in a ring.
// The game's own camera; no gacha HUD badge (hidden, H.gcam); c.hitCd held up so a take isn't cut short by a KO.
T.G={};
H_G=`H.gcam=(F)=>{const b=F.c.el('.st-gbadge');if(b)b.style.visibility='hidden';};
 H.chase=(F,list)=>{const c=F.c;c.puddles=c.puddles.filter((q)=>!(Math.abs(q.x-9.8)<0.01&&Math.abs(q.z+33.6)<0.01));const N=list.map((q)=>c.npcs[q[0]]);N.forEach((n,k)=>F.npcAt(n,list[k][1],list[k][2],list[k][3]||0));F.park(N);N.forEach((n)=>c.startChase(n));return N;};
 H.near=(F)=>{const c=F.c,P=c.P;let bd=1e9;for(const n of c.npcs){if(n.ko||n.a.st!=='free'||n.a.x<-50)continue;bd=Math.min(bd,Math.hypot(n.a.x-P.x,n.a.z-P.z));}return bd;};`;
const G0=(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;};
T.gpull={seed:8,pre:0.1,n:190,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(5.4,-24.4,0,0);c.grace=99;F.park([]);F.take.stopWarm=true;},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;F.pad();if(!tk.st){const d=H.go(F,8.45,-26.0,0.8);if(d<0.12){tk.st=1;tk.t1=t;}}else{H.stop(F);P.f=0;F.inp.grab=t-tk.t1>0.5&&t-tk.t1<0.6;}}};
T.gvanish={seed:8,pre:0.1,n:200,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(0.6,-33.5,0,0);c.grace=0;const n=c.npcs[1];F.npcAt(n,5.4,-35.0,Math.PI/2+0.4);F.park([n]);c.gSkill='vanish';F.take.stopWarm=true;},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c;F.pad();F.inp.skill=t>0.25&&t<0.3;if(t>0.6)H.go(F,10.5,-33.4,0.85);}};
T.gsmoke={seed:8,pre:0.1,n:230,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(3.2,-33.9,0,0);c.grace=0;H.chase(F,[[1,-3.0,-33.6],[2,-3.8,-34.4]]);c.gSkill='smoke';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c;c.hitCd=9;F.pad();F.inp.skill=H.near(F)<3.4&&!F.take.u&&(F.take.u=1);if(!F.take.u)H.go(F,5,-33.9,0.6);else if(!F.take.t2){F.take.t2=t;}else if(t-F.take.t2<1.0)H.stop(F);else{c.keys.KeyI=true;H.go(F,10.5,-32.6,0.7);}}};
T.gtimedrag={seed:8,pre:0.1,n:230,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(8.4,-33.9,Math.PI,0);H.chase(F,[[1,1.2,-34.4,0],[2,0.4,-33.5,0]]);c.gSkill='timedrag';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();
   if(!tk.u){H.stop(F);P.f=Math.PI;if(H.near(F)<3.6){F.inp.skill=true;tk.u=t;}return;}
   if(t-tk.u<0.25){H.stop(F);return;}
   if(!tk.w){const d=H.go(F,4.4,-32.3,1);if(d<0.4)tk.w=1;}else if(tk.w===1){const d=H.go(F,0.5,-32.3,1);if(d<0.4)tk.w=2;}else H.go(F,-5,-33.6,1);}};
T.gsleepdart={seed:8,pre:0.1,n:180,
 setup:(F)=>{const c=F.c;c.outOfBath=true;F.at(2.0,-33.9,0,0);c.grace=0;const n=c.npcs[1];F.npcAt(n,6.6,-34.1,0);F.park([n]);c.gSkill='sleepdart';F.take.stopWarm=true;},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c;F.pad();F.inp.skill=t>0.5&&t<0.55;if(t>1.6){c.keys.KeyI=true;H.go(F,10.5,-32.7,0.8);}}};
T.gtrapdoor={seed:8,pre:0.1,n:210,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(3.0,-33.9,0,0);H.chase(F,[[1,-3.6,-33.9]]);c.gSkill='trapdoor';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P;c.hitCd=9;F.pad();F.inp.skill=t>0.15&&t<0.2;if(t<0.4)return;if(t<1.2)H.go(F,6.4,-33.9,1);else{H.stop(F);P.f=Math.PI;}}};
T.grewind={seed:8,pre:0.1,n:260,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(1.0,-33.9,0,0);c.spill(5.2,-33.9,0);H.chase(F,[[1,-4.0,-33.9]]);c.gSkill='rewind';c.hist=[];c.recT=0;},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();
   if(!tk.r){if(c.rew)tk.r=1;if(t>0.5&&!tk.ch){F.inp.mx=1;F.inp.dash=P.st==='free';if(P.st==='charge'||P.st==='slip')tk.ch=1;}return;}
   if(c.rew)return;const d=tk.a?0:H.go(F,4.2,-32.5,0.9);if(!tk.a&&d<0.4)tk.a=1;if(tk.a)H.go(F,10,-32.6,0.9);}};
T.gphantom={seed:8,pre:0.1,n:150,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(1.0,-33.9,0,0);H.chase(F,[[1,9.5,-33.6,Math.PI],[2,10.6,-34.3,Math.PI],[3,11.8,-33.8,Math.PI]]);c.gSkill='phantom';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();if(!tk.u){P.f=0;if(H.near(F)<3.2){F.inp.skill=true;tk.u=1;}}}};
T.gtorpedo={seed:8,pre:0.1,n:150,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(-0.5,-33.9,0,0);H.chase(F,[[1,9.0,-33.5,Math.PI],[2,10.2,-34.4,Math.PI],[3,11.5,-33.9,Math.PI]]);c.gSkill='torpedo';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();if(!tk.u){P.f=0;if(H.near(F)<5.5){F.inp.skill=true;tk.u=1;}}else H.go(F,10,-33.9,1);}};
T.gdaruma={seed:8,pre:0.1,n:200,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(3.4,-33.9,0,0);F.take.N=H.chase(F,[[1,10.2,-33.4,Math.PI],[2,11.0,-34.6,Math.PI],[3,-3.0,-33.5,0],[4,-3.8,-34.4,0]]);c.gSkill='daruma';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();if(!tk.u){P.f=0;if(H.near(F)<3.4){F.inp.skill=true;tk.u=1;}return;}const n=tk.N.filter((q)=>q.a.st==='free'&&!q.ko).sort((a,b)=>Math.hypot(a.a.x-P.x,a.a.z-P.z)-Math.hypot(b.a.x-P.x,b.a.z-P.z))[0];if(n)H.go(F,n.a.x,n.a.z,1);}};
T.ggiant={seed:8,pre:0.1,n:220,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(3.0,-33.9,0,0);F.take.N=H.chase(F,[[1,9.8,-33.5,Math.PI],[2,10.8,-34.4,Math.PI],[3,-3.4,-33.8,0]]);c.gSkill='giant';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();F.inp.skill=t>0.3&&t<0.35;if(t<1.2){H.stop(F);return;}const n=tk.N.filter((q)=>q.a.st==='free'&&!q.ko).sort((a,b)=>Math.hypot(a.a.x-P.x,a.a.z-P.z)-Math.hypot(b.a.x-P.x,b.a.z-P.z))[0];if(n)H.go(F,n.a.x,n.a.z,0.7);else H.stop(F);}};
T.gstomp={seed:8,pre:0.1,n:160,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(4.6,-33.9,Math.PI/2,0);H.chase(F,[[1,-1.2,-33.5,0],[2,-2.0,-34.4,0],[3,10.6,-33.4,Math.PI],[4,11.4,-34.5,Math.PI],[5,12.2,-33.9,Math.PI]]);c.gSkill='stomp';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,tk=F.take;c.hitCd=9;F.pad();if(!tk.u&&H.near(F)<2.4){F.inp.skill=true;tk.u=1;}}};
T.ghands={seed:8,pre:0.1,n:150,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(2.4,-33.9,0,0);H.chase(F,[[1,8.6,-33.5,Math.PI],[2,9.2,-34.3,Math.PI],[3,10.4,-33.9,Math.PI]]);c.gSkill='hands';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();P.f=0;if(!tk.u&&H.near(F)<2.2){F.inp.skill=true;tk.u=1;}}};
T.gbomb={seed:8,pre:0.1,n:210,
 setup:(F)=>{const c=F.c;c.outOfBath=true;c.grace=0;F.take.stopWarm=true;F.at(6.0,-33.9,Math.PI,0);H.chase(F,[[1,-3.4,-33.0,0],[2,-4.2,-34.8,0],[3,-5.0,-33.2,0]]);c.gSkill='bomb';},
 script:(t,F)=>{t-=0.6;H.gcam(F);const c=F.c,P=c.P,tk=F.take;c.hitCd=9;F.pad();if(!tk.u){H.stop(F);P.f=Math.PI;if(H.near(F)<9.3){F.inp.skill=true;tk.u=t;}return;}if(t-tk.u<0.4){H.stop(F);P.f=Math.PI;return;}const d=H.go(F,9.4,-33.2,1);if(d<0.3){H.stop(F);P.f=Math.PI;}}};
T.HELP=T.HELP+H_G;
module.exports=T;
