# Flat "KKBC" composite: flat albedo, sun only decides lit vs. shadow (soft edge), lilac shadow tint, light AO.
import OpenEXR, numpy as np, sys
from PIL import Image
src,out=sys.argv[1],sys.argv[2]
P=dict(a.split('=') for a in sys.argv[3:]); g=lambda k,d: float(P.get(k,d))
ch=OpenEXR.File(src).parts[0].channels
def get(n):
    c=ch['ViewLayer.'+n].pixels
    return c[...,:3].astype(np.float32) if c.ndim==3 else c.astype(np.float32)[...,None]
col=get('DiffCol'); dd=get('DiffDir'); di=get('DiffInd'); ao=get('AO')[...,:1] if ch['ViewLayer.AO'].pixels.ndim==3 else get('AO')
env=get('Env'); emit=get('Emit')
gd,gi,gc=get('GlossDir'),get('GlossInd'),get('GlossCol'); td,ti,tc=get('TransDir'),get('TransInd'),get('TransCol')
lum=lambda x:(x*[0.2126,0.7152,0.0722]).sum(-1,keepdims=True)
s=lum(dd)/np.percentile(lum(dd)[lum(col)>0.02],97)
from scipy.ndimage import gaussian_filter
s=gaussian_filter(s[...,0],g('blur',1.6))[...,None]; ao=gaussian_filter(ao[...,0],2.0)[...,None]
sm=lambda a,b,x:np.clip((x-a)/(b-a),0,1)**2*(3-2*np.clip((x-a)/(b-a),0,1))
L=sm(g('lo',0.06),g('hi',0.30),s)
L=L*(1-g('form',0.12))+g('form',0.12)*np.clip(s,0,1)          # a little form, mostly flat
lit=np.array([1.0,0.975,0.93])*g('litk',1.0)
shd=np.array([0.66,0.68,0.86])*g('shdk',1.0)
AO=1-g('ao',0.25)*(1-ao[...,:1])
dif=col*(shd+(lit-shd)*L)*AO
other=(gd+gi)*gc*g('gloss',0.25)+(td+ti)*tc+emit
img=dif+other
bg=(lum(col)<1e-4)&(lum(tc)<1e-4)&(lum(emit)<1e-4)
img=np.where(bg,env,img)
img=np.clip(img*g('exp',1.0),0,1)
srgb=np.where(img<=0.0031308,img*12.92,1.055*img**(1/2.4)-0.055)
srgb=g('lift',0.03)+(1-g('lift',0.03)-0.01)*srgb               # no pure black / white
Image.fromarray((np.clip(srgb,0,1)*255+0.5).astype(np.uint8)).save(out)
print('ok',float(np.percentile(lum(dd),97)))
