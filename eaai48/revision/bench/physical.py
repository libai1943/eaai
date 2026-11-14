"""Independent dense replay and tables. No planner code is imported."""
from pathlib import Path
import argparse, csv, json, math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def car(case,z):
    z=np.asarray(z,dtype=float)
    if z.ndim!=1 or not z.size or z.size%2 or not np.isfinite(z).all():raise ValueError("Malformed parking strokes")
    pose=np.array(case["endpoints"][:3]);target=np.array(case["endpoints"][3:])
    rows=[];T=0;phi=0;gear=[];switches=[];length=0
    for k,s in np.array(z).reshape(-1,2):
        if abs(s)<1e-9:continue
        if abs(k)>math.tan(.7)/2.8+1e-10:raise ValueError("curvature limit")
        samples=np.linspace(0,s,max(2,math.ceil(abs(s)/.014)+1));angle=pose[2]+k*samples
        seg=np.c_[pose[0]+samples*np.sinc(k*samples/(2*np.pi))*np.cos((angle+pose[2])/2),
                  pose[1]+samples*np.sinc(k*samples/(2*np.pi))*np.sin((angle+pose[2])/2),angle]
        if gear and np.sign(s)!=gear[-1]:switches.append(pose[:2].tolist())
        gear.append(np.sign(s));rows.append(seg);pose=seg[-1].copy();length+=abs(s)
        angle=math.atan(2.8*k);d=abs(s);peak=min(2.5,math.sqrt(d));T+=2*abs(angle-phi)+2*peak+(d-peak**2)/peak;phi=angle
    if not rows:return dict(ok=False,J=None,error=None,gap=None),{}
    T+=2*abs(phi);poses=np.vstack(rows);angle=poses[:,2]
    c,s=np.cos(angle),np.sin(angle)
    body=np.stack([poses[:,:2]+np.c_[c*dx-s*dy,s*dx+c*dy] for dx,dy in [(-.929,-.971),(3.76,-.971),(3.76,.971),(-.929,.971)]],axis=1)
    gap=1e10
    for poly in case["polygons"]:
        poly=np.asarray(poly);edges=np.roll(poly,-1,axis=0)-poly;axes=np.c_[edges[:,1],-edges[:,0]]/np.linalg.norm(edges,axis=1)[:,None]
        separations=[]
        for axis in axes:
            proj=body@axis;other=poly@axis
            separations.append(np.maximum(proj.min(1)-other.max(),other.min()-proj.max(1)))
        for axis in (np.c_[c,s],np.c_[-s,c]):
            proj=(body*axis[:,None,:]).sum(2);other=axis@poly.T
            separations.append(np.maximum(proj.min(1)-other.max(1),other.min(1)-proj.max(1)))
        gap=min(gap,float(np.max(separations,axis=0).min()))
    diff=pose-target;diff[2]=math.remainder(diff[2],2*math.pi);error=float(np.max(np.abs(diff)))
    idx=np.unique(np.linspace(0,len(poses)-1,min(450,len(poses)),dtype=int))
    return dict(ok=gap>=.01-1e-8 and error<1e-5,J=T,error=error,gap=gap,gears=len(switches)),dict(poses=poses[idx].tolist(),switches=switches)
def body(x,kind):
    if kind=="uav":return x[...,None,:3],np.array([.22])
    if kind=="arm":
        a,b,c=x[...,0],x[...,1],x[...,2];base=np.zeros(x.shape[:-1]+(1,3));base[...,0,2]=1
        def link(l,t):return l*np.stack((np.cos(a)*np.cos(t),np.sin(a)*np.cos(t),np.sin(t)),axis=-1)[...,None,:]
        t=(np.arange(4)+.5)[:,None]/4;v=link(.9,b);w=link(.8,b+c)
        return np.concatenate((base+v*t,base+v+w*t),axis=-2),np.full(8,.13)
    raise ValueError("Expected arm or aerial model")
def allgap(x,case):
    centers,radii=body(x,case["kind"]);g=np.full(x.shape[:-1],1.e8)
    for box in case["obstacles"]:
        delta=np.maximum(np.asarray(box[:3])-centers,centers-box[3:])
        dist=np.where(delta.max(-1)>0,np.linalg.norm(np.maximum(delta,0),axis=-1),delta.max(-1))
        g=np.minimum(g,(dist-radii).min(-1))
    return g
def spatial_many(case,items):
    # Integrate all runs of a scene simultaneously, never reset to its saved state nodes.
    n=case["N"];kind=case["kind"];nx=case["nx"];nu=case["nu"];sub=32
    if kind not in ("uav","arm") or n<5 or nx!=6 or nu!=3:raise ValueError("Invalid spatial model structure")
    if not items:return []
    try:Z=np.asarray([r["z"] for r in items],dtype=float)
    except (ValueError,TypeError,KeyError) as e:raise ValueError("Malformed trajectory") from e
    if Z.shape!=(len(items),1+n*(nx+nu)) or not np.isfinite(Z).all():raise ValueError("Nonfinite or malformed trajectory")
    T=Z[:,0]
    if np.any((T<.5-1e-9)|(T>100.+1e-9)):raise ValueError("Duration outside [0.5,100]")
    X=Z[:,1:].reshape(len(items),n,nx+nu)
    U=X[:,:-1,nx:];x=np.broadcast_to(case["start"],(len(items),nx)).copy()
    h=T[:,None]/((n-1)*sub)
    nodegap=allgap(X[:,:,:nx],case).min(1);g=nodegap.copy();limits=np.zeros(len(items))
    lower=np.array(case["lower"]);upper=np.array(case["upper"])
    node_error=np.max(np.abs(X[:,0,:nx]-x),axis=1)
    for k in range(n-1):
        u=U[:,k];sp=[]
        for j in range(sub):
            x[:,:3]+=h*x[:,3:]+.5*h*h*u;x[:,3:]+=h*u
            sp.append(x.copy())
        node_error=np.maximum(node_error,np.max(np.abs(x-X[:,k+1,:nx]),axis=1))
        points=np.stack(sp,axis=1)
        g=np.minimum(g,allgap(points,case).min(1))
        limits=np.maximum(limits,np.maximum(lower[:nx]-points,points-upper[:nx]).max(axis=(1,2)))
    error=np.max(np.abs(x-np.asarray(case["goal"])),axis=1)
    limits=np.maximum(limits,np.maximum(lower-X,X-upper).max(axis=(1,2)))
    J=T+.01*np.sum(U*U,axis=(1,2))/(n-1)+.002*np.sum(np.diff(U,axis=1)**2,axis=(1,2))
    ok=(g>=-1e-8)&(nodegap>=.03-1e-6)&(error<1e-3)&(limits<=1e-5)&(T>=.5-1e-9)&(T<=100.000001)&(node_error<1e-5)&(np.max(np.abs(X[:,-1,nx:]),axis=1)<1e-10)
    return [dict(ok=bool(ok[i]),J=J[i],error=error[i],gap=g[i]) for i in range(len(items))]
