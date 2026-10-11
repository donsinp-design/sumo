# mcflick.py DIR A B : camera-motion-compensated flicker finder (pixels that blink after aligning frames)
import sys,warnings;warnings.filterwarnings('ignore')
from PIL import Image
d,a0,a1=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]);W,H=320,180
F=[list(Image.open(f'{d}/f_{i:04d}.jpg').convert('L').resize((W,H)).getdata()) for i in range(a0,a1)]
def off(A,B):
    best=None
    for dy in range(-6,7):
        for dx in range(-6,7):
            s=0;n=0
            for y in range(20,H-20,4):
                for x in range(20,W-20,4):
                    s+=abs(A[y*W+x]-B[(y+dy)*W+x+dx]);n+=1
            if best is None or s<best[0]:best=(s,dx,dy)
    return best[1],best[2]
offs=[off(F[i],F[i+1]) for i in range(len(F)-1)]
cnt={}
for i in range(1,len(F)-1):
    (ax,ay),(bx,by)=offs[i-1],offs[i]
    P,C,N=F[i-1],F[i],F[i+1]
    for y in range(8,H-8):
        for x in range(8,W-8):
            c=C[y*W+x];p=P[(y-ay)*W+x-ax];n=N[(y+by)*W+x+bx]
            if abs(c-p)>30 and abs(c-n)>30 and (c-p)*(c-n)>0: cnt[(x,y)]=cnt.get((x,y),[])+[a0+i]
import os
if os.environ.get("XMAX"):cnt={k:v for k,v in cnt.items() if k[0]<int(os.environ["XMAX"])}
print("total",sum(len(v) for v in cnt.values()))
hot=sorted(cnt.items(),key=lambda kv:-len(kv[1]))[:12]
for (x,y),fr in hot: print(x,y,len(fr),fr[:10])
print('offsets sample',offs[:5])
