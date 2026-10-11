# strobe.py DIR [FROM TO]: per-pixel up-down flicker events (320x180), total + hottest pixels
import sys,warnings;warnings.filterwarnings('ignore')
from PIL import Image
d=sys.argv[1];a0=int(sys.argv[2]) if len(sys.argv)>2 else 0;a1=int(sys.argv[3]) if len(sys.argv)>3 else 120
W,H=320,180;fr=[list(Image.open(f'{d}/f_{i:04d}.jpg').convert('L').resize((W,H)).getdata()) for i in range(a0,a1)]
cnt=[0]*(W*H)
for i in range(1,len(fr)-1):
    a,b,c=fr[i-1],fr[i],fr[i+1]
    for p in range(W*H):
        if abs(b[p]-a[p])>28 and abs(b[p]-c[p])>28 and (b[p]-a[p])*(b[p]-c[p])>0: cnt[p]+=1
hot=sorted(range(W*H),key=lambda p:-cnt[p])[:3]
print(d,'total',sum(cnt),'max',max(cnt),'hot',[(p%W,p//W,cnt[p]) for p in hot])
