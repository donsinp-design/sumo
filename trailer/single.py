# single.py OUT.mp4 FRAMES dir:start  (one skill/move full screen, same ring crop as the grids)
import sys,subprocess
out,L,x=sys.argv[1],int(sys.argv[2]),sys.argv[3];d,s=x.split(':')
subprocess.run(['ffmpeg','-y','-v','error','-framerate','30','-start_number',s,'-i',f'{d}/f_%04d.jpg','-vf',f'trim=end_frame={L},setpts=PTS-STARTPTS,crop=720:405:280:128,scale=1280:720,setsar=1,tpad=stop_mode=clone:stop_duration=8,trim=end_frame={L},format=yuv420p','-c:v','libx264','-crf','17','-r','30',out],check=True)
