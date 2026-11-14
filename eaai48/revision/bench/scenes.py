from pathlib import Path
import math,json
D=Path(__file__).resolve().parents[1]/"data"
names=["diagonal loading pocket","paired diagonal docks","perpendicular loading bay","side-wall berth","offset gate","mirrored gate","short terminal apron","long terminal apron","oblique service berth","staggered bollards","adjacent occupied berth","terminal wall and posts"]
def main():
 for i,name in enumerate(names):
    sign=1 if i%2==0 else -1;ang=math.radians([48,54,82,69,62,76,58,88,44,72,65,80][i])*sign
    sx=-4-(i%3); gx=.8*(i%4)-1;gy=-sign*(10.5+.7*(i%5)+.065*(abs(math.degrees(ang))-45))
    c,s=math.cos(ang),math.sin(ang);rect=[]
    def dock(x,y,l,w,tilt=0):
        rect.append([gx+x*c-y*s,gy+x*s+y*c,ang+math.radians(tilt),l,w])
    clearance=1.52+.14*(i%4)
    dock(-2.8,clearance+.25,7.0+.3*(i%3),.5);dock(-2.9,-clearance-.3,7.1+.25*(i%4),.6)
    dock(-6.6-.08*(i%3),0,.52,2*clearance+.9)
    if i%3!=0:dock(1.3,clearance+.5,.65,.7,12)
    if i%3!=1:dock(.9,-clearance-.9,.70,.65,-15)
    if i>=6:dock(-2.8,clearance+2.0,5.8,1.65,3)
    rect.append([6+.45*(i%4),sign*(3.7+.28*(i%3)),0,2.6+.4*(i%3),1.0])
    if i%2:rect.append([13.5,sign*4.15,-.15,1.,1.35])
    if i in (2,5,8):rect.append([-.2, -sign*2.65,math.radians(sign*12),2.4,1.05])
    if i in (3,7,10):rect.append([8.8,-sign*3.0,-.09*sign,3.8,1.3])
    if i in (4,9,11):rect.extend([[3.2,sign*2.8,.14*sign,1.8,1.1],[10.5,-sign*3.25,0,2.1,1.]])
    yaw=math.radians([0,8,-9,12,-7,6,10,-10,7,-12,11,-8][i])
    withdraw=i in (3,7,10)
    if withdraw:
        # A bollard ahead of the initial tractor nose restricts a direct departure.
        rect.append([sx+3.05*math.cos(yaw),3.05*math.sin(yaw),yaw,.8,.8])
    start=[sx,0,yaw];goal=[gx,gy,ang];p=dict(name=name,start=start,goal=goal,rectangles=rect,withdrawal=withdraw,
        tractor=[-.25,1.8,.90],trailer=[-1.2,2.25,.95],tractor_wheelbase=1.5,hitch_offset=1.5,trailer_drawbar=3.,node_margin=.06)
    out=D/f"trailer_{i+1:02}";out.with_suffix(".json").write_text(json.dumps(p,indent=2));out.with_suffix(".task").write_text(" ".join(map(str,start+goal+[len(rect)]))+"\n"+"\n".join(" ".join(map(str,b)) for b in rect)+"\n"+str(int(withdraw))+"\n")
if __name__=="__main__":main()

