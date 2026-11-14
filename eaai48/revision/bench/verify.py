"""Reintegrate articulated open-loop controls from the prescribed start; do not reset at gear changes."""
import csv,json,math,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1]
from physical import car,spatial_many
from importlib.util import spec_from_file_location,module_from_spec
def sat(x,y,h,lo,hi,w,rects):
    c,s=np.cos(h),np.sin(h);x=x+.5*(lo+hi)*c;y=y+.5*(lo+hi)*s
    rx=(hi-lo)/2;best=np.full(x.shape,1e3)
    for bx,by,bh,l,width in rects:
        C,S=math.cos(bh),math.sin(bh);dx=bx-x;dy=by-y
        dot=np.abs(c*C+s*S);cross=np.abs(s*C-c*S);bxr=l/2;byr=width/2
        gap=np.maximum.reduce([np.abs(dx*c+dy*s)-rx-bxr*dot-byr*cross,
            np.abs(-dx*s+dy*c)-w-bxr*cross-byr*dot,
            np.abs(dx*C+dy*S)-bxr-rx*dot-w*cross,np.abs(-dx*S+dy*C)-byr-rx*cross-w*dot])
        best=np.minimum(best,gap)
    return best
def control(t,z):
    L,A,k,T,d=z.T;w=np.pi*t;u=(1-np.cos(w))/2;u=np.where(d>0,u,1-u);v=d*L*np.pi/(2*T)*np.sin(w)
    q=2*np.pi*u;si=np.sin(q);co=np.cos(q);g=.5*(1-co);g1=np.pi*si;g2=2*np.pi**2*co
    f=1+k*si;f1=2*np.pi*k*co;f2=-4*np.pi**2*k*si
    a=A*g*f;as1=A*(g1*f+g*f1)/L;as2=A*(g2*f+2*g1*f1+g*f2)/L**2
    div=1+.5*np.cos(a);K=(as1+np.sin(a)/3)/div
    K1=(as2+np.cos(a)*as1/3+.5*K*np.sin(a)*as1)/div
    return v,K,np.arctan(1.5*K),1.5*K1*v/(1+2.25*K*K),d*L*np.pi**2/(2*T*T)*np.cos(w)
def dock_many(cfg,rec,steps=400):
    n=len(rec);raw=np.asarray([r["z"] for r in rec],dtype=float)
    if raw.ndim!=2 or raw.shape[1]==0 or raw.shape[1]%5 or not np.isfinite(raw).all():raise ValueError("Malformed docking strokes")
    z=raw.reshape(n,-1,5)
    if np.any(z[:,:,0]<=0) or np.any(z[:,:,3]<=0) or not np.isin(z[:,:,4],[-1,1]).all():raise ValueError("Invalid stroke length, duration or gear")
    x=np.tile([*cfg["start"],cfg["start"][2]],(n,1))
    seq=[x.copy()];speed=[np.zeros(n)];limit=np.zeros(n); minv=np.zeros(n);maxv=np.zeros(n);switch=[]
    def rhs(x,v,K):
        delta=x[:,2]-x[:,3];hd=v*K
        return np.stack([v*np.cos(x[:,2]),v*np.sin(x[:,2]),hd,(v*np.sin(delta)-1.5*hd*np.cos(delta))/3],axis=1)
    for j in range(z.shape[1]):
        zz=z[:,j];dt=zz[:,3:4]/steps
        for k in range(steps):
            v0,K0,phi0,o0,a0=control(k/steps,zz);v1,K1,phi1,o1,a1=control((k+.5)/steps,zz);v2,K2,phi2,o2,a2=control((k+1)/steps,zz)
            f=rhs(x,v0,K0);b=rhs(x+dt*f/2,v1,K1);c=rhs(x+dt*b/2,v1,K1);e=rhs(x+dt*c,v2,K2);x=x+dt*(f+2*b+2*c+e)/6
            for v,phi,o,a in [(v0,phi0,o0,a0),(v1,phi1,o1,a1),(v2,phi2,o2,a2)]:
                limit=np.maximum.reduce([limit,np.abs(phi)-.7,np.abs(o)-.5,np.abs(a)-.25,np.abs(v)-1.5])
            seq.append(x.copy());speed.append(v2);minv=np.minimum(minv,v1);maxv=np.maximum(maxv,v1)
        if j+1<z.shape[1] and z[0,j,4]!=z[0,j+1,4]:switch.append(x.copy())
    X=np.stack(seq,axis=1);speed=np.stack(speed,axis=1);heading=X[:,:,2];tr=X[:,:,3]
    tx=X[:,:,0]-1.5*np.cos(heading)-3*np.cos(tr);ty=X[:,:,1]-1.5*np.sin(heading)-3*np.sin(tr)
    gap=np.minimum(sat(X[:,:,0],X[:,:,1],heading,*cfg["tractor"],cfg["rectangles"]),sat(tx,ty,tr,*cfg["trailer"],cfg["rectangles"])).min(1)
    end=np.max(np.abs(x-np.array([*cfg["goal"],cfg["goal"][2]])),axis=1);limit=np.maximum(limit,np.max(np.abs(heading-tr),axis=1)-1.2)
    ok=(gap>=.03)&(end<.001)&(limit<1e-5)&(minv<-.05)&(maxv>.05)
    for i,vs in enumerate(speed):
        signs=np.sign(vs[np.abs(vs)>.05]);sequence=signs[np.r_[True,np.diff(signs)!=0]] if len(signs) else signs
        ok[i]&=list(sequence)==([-1,1,-1] if cfg["withdrawal"] else [1,-1])
    return [dict(ok=bool(ok[i]),J=float(z[i,:,3].sum()),error=float(end[i]),gap=float(gap[i]),vmin=float(minv[i]),vmax=float(maxv[i]),limits=float(limit[i])) for i in range(n)],X,speed,np.stack(switch,axis=1)
def main():
    rows=[];gallery=[];base=R.parent;raw=R/"runs"
    for kind in ["parking","uav","arm","trailer"]:
      for j in range(1,13):
        name=f"{kind}_{j:02}";cfg=json.loads(((R if kind=="trailer" else base)/"data"/(name+".json")).read_text())
        files=sorted(raw.glob(name+"_*.json"));assert len(files)==42,(name,len(files))
        items=[json.loads(f.read_text()) for f in files];idx=[i for i,r in enumerate(items) if r["loss"]==0]
        accepted={};traces={}
        if idx and kind=="trailer":
            result,X,speed,switch=dock_many(cfg,[items[i] for i in idx])
            for k,i in enumerate(idx):
                accepted[i]=result[k];traces[i]=dict(poses=X[k,::5].tolist(),speed=speed[k,::5].tolist(),switches=switch[k,:,:2].tolist())
        elif kind=="parking":
            for i in idx:accepted[i],traces[i]=car(cfg,items[i]["z"])
        elif idx:accepted=dict(zip(idx,spatial_many(cfg,[items[i] for i in idx])))
        starts={};galleryrow=dict(name=name,kind=kind,scene=cfg,tracks=[])
        for i,(p,r) in enumerate(zip(files,items)):
            m=r["method"];seed=int(p.stem.split("_")[-1]);a=accepted.get(i,{})
            lines=Path(str(p)+".csv").read_bytes().splitlines()
            if len(lines)!=r["evaluations"]+1 or starts.setdefault(seed,lines[1:25])!=lines[1:25]:raise ValueError(f"Unmatched budget/initialization {p}")
            if a and abs(a["J"]-r["J"])>1e-6:raise ValueError(f"Cost mismatch {p}")
            rows.append(dict(case=name,family=kind,seed=seed,method=m,budget=r["evaluations"],first=r["first"],accepted=int(bool(a)),valid=int(bool(a.get("ok"))),cost=a.get("J") if a.get("ok") else None,terminal=a.get("error"),clearance=a.get("gap"),vmin=a.get("vmin"),vmax=a.get("vmax")))
            if seed!=4201 or m not in ("adaptive","cma") or not a.get("ok"):continue
            if kind in ("parking","trailer"):trace=traces[i]
            else:
                x=np.asarray(r["z"][1:]).reshape(cfg["N"],-1)[:,:cfg["nx"]]
                if kind=="arm":
                    a0,b,c=x[:,:3].T;elbow=np.tile([0.,0.,1.],(len(x),1))+.9*np.c_[np.cos(a0)*np.cos(b),np.sin(a0)*np.cos(b),np.sin(b)]
                    tip=elbow+.8*np.c_[np.cos(a0)*np.cos(b+c),np.sin(a0)*np.cos(b+c),np.sin(b+c)]
                    trace=dict(poses=tip.tolist(),elbow=elbow.tolist())
                else:trace=dict(poses=x.tolist())
            galleryrow["tracks"].append(dict(**trace,method=m))
        gallery.append(galleryrow)
    assert len(rows)==2016
    with (R/"output/verified.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,rows[0]);w.writeheader();w.writerows(rows)
    (R/"figures/data.json").write_text(json.dumps(gallery))
    print(len(rows),"verified",sum(x['accepted'] and not x['valid'] for x in rows),"disagreements")
if __name__=="__main__":main()

