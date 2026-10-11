# cut.py OUT.mp4 "dir:start:count" ... -> concatenates image-sequence ranges (30fps, 1280x720) with hard cuts
import sys,subprocess
out=sys.argv[1];segs=sys.argv[2:];args=[];fl=[]
for i,s in enumerate(segs):
    p=s.split(':');d,st,n=p[0],int(p[1]),int(p[2]);fi=int(p[3]) if len(p)>3 else 0;fo=int(p[4]) if len(p)>4 else 0;fc=p[5] if len(p)>5 else 'white'
    fd=(f',fade=t=in:s=0:n={fi}:color={fc}' if fi else '')+(f',fade=t=out:s={n-fo}:n={fo}:color={fc}' if fo else '')
    if d.startswith('card='):
        args+=['-loop','1','-framerate','30','-t',str(n/30),'-i',d[5:]]
        fl.append(f'[{i}:v]scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={n}{fd}[v{i}]')
    else:
        args+=['-framerate','30','-start_number',str(st),'-i',f'{d}/f_%04d.jpg']
        fl.append(f'[{i}:v]trim=end_frame={n},setpts=PTS-STARTPTS,scale=1280:720,setsar=1,format=yuv420p{fd}[v{i}]')
fc=';'.join(fl)+';'+''.join(f'[v{i}]' for i in range(len(segs)))+f'concat=n={len(segs)}:v=1:a=0[o]'
subprocess.run(['ffmpeg','-y','-v','error']+args+['-filter_complex',fc,'-map','[o]','-c:v','libx264','-crf','17','-pix_fmt','yuv420p','-r','30',out],check=True)
print(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',out],capture_output=True,text=True).stdout.strip())
