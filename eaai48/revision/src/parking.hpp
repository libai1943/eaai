#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace parking {
constexpr double pi=3.14159265358979323846, wheelbase=2.8, margin=.01;
struct Point {double x,y;};
struct Pose {double x,y,a;};
struct Stroke {double k,s;}; // signed curvature and signed distance
using Path=std::vector<Stroke>;
double wrap(double a){return std::remainder(a,2*pi);}
Pose step(Pose p,Stroke t){
    double a=p.a+t.k*t.s;
    if(std::abs(t.k)<1e-12)return {p.x+t.s*std::cos(p.a),p.y+t.s*std::sin(p.a),p.a};
    return {p.x+(std::sin(a)-std::sin(p.a))/t.k,p.y+(std::cos(p.a)-std::cos(a))/t.k,a};
}
double travel(double s){double d=std::abs(s);return d<6.25?2*std::sqrt(d):d/2.5+2.5;}
double duration(const Path& path){
    double T=0,phi=0;
    for(auto a:path){if(std::abs(a.s)<1e-9)continue;
        double next=std::atan(wheelbase*a.k);T+=travel(a.s)+2*std::abs(next-phi);phi=next;}
    return T+2*std::abs(phi);
}
struct Axis {double x,y,lo,hi;};
struct Obstacle {
    std::array<Point,4> pts;std::array<Axis,4> axes;
    explicit Obstacle(std::istream& f){
        for(auto& q:pts)if(!(f>>q.x>>q.y))throw std::runtime_error("Missing polygon vertex");
        for(int i=0;i<4;i++){
            auto u=pts[i],v=pts[(i+1)%4];double l=std::hypot(v.x-u.x,v.y-u.y);
            if(l==0)throw std::runtime_error("Repeated polygon vertex");
            auto& a=axes[i];a={(u.y-v.y)/l,(v.x-u.x)/l,1e10,-1e10};
            for(auto q:pts){double z=q.x*a.x+q.y*a.y;a.lo=std::min(a.lo,z);a.hi=std::max(a.hi,z);}
        }
    }
    double gap(Pose p,double c,double s)const{
        double x=p.x+1.4155*c,y=p.y+1.4155*s,best=-1e10;
        for(auto a:axes){double h=2.3445*std::abs(c*a.x+s*a.y)+.971*std::abs(-s*a.x+c*a.y);
            double z=a.x*x+a.y*y;best=std::max({best,z-h-a.hi,a.lo-z-h});}
        for(int i=0;i<2;i++){double dx=i?-s:c,dy=i?c:s,lo=1e10,hi=-1e10;
            for(auto q:pts){double z=(q.x-x)*dx+(q.y-y)*dy;lo=std::min(lo,z);hi=std::max(hi,z);}
            double h=i?.971:2.3445;best=std::max({best,lo-h,-hi-h});}
        return best;
    }
#ifdef EAAI_SWEEP
    // Lower bound for a fixed obstacle normal or a continuously rotating car normal.
    // The interpolation error for a twice differentiable scalar projection is M*s*s/8.
    double sweptBound(Pose p,Pose q,Stroke t)const{
        double c[2]={std::cos(p.a),std::cos(q.a)},s[2]={std::sin(p.a),std::sin(q.a)};
        Pose end[2]={p,q};double k=std::abs(t.k),len=std::abs(t.s),result=-1e20;
        for(auto axis:axes){
            double lo[2],hi[2];
            for(int i=0;i<2;i++){
                double u=c[i]*axis.x+s[i]*axis.y,v=-s[i]*axis.x+c[i]*axis.y;
                double h=2.3445*std::abs(u)+.971*std::abs(v);
                double center=end[i].x*axis.x+end[i].y*axis.y+1.4155*u;
                lo[i]=center-h-axis.hi;hi[i]=axis.lo-center-h;
            }
            result=std::max(result,std::max(std::min(lo[0],lo[1]),std::min(hi[0],hi[1]))-(k+3.89*k*k)*len*len/8);
        }
        for(int a=0;a<2;a++){
            double low=1e20,high=1e20;
            for(auto v:pts){
                double f[2];
                for(int i=0;i<2;i++)f[i]=(v.x-end[i].x)*(a?-s[i]:c[i])+(v.y-end[i].y)*(a?c[i]:s[i]);
                double dist=std::hypot(v.x-p.x,v.y-p.y)+len;
                double rem=(3*k+dist*k*k)*len*len/8;
                low=std::min(low,std::min(f[0],f[1])-(a?.971:3.760)-rem);
                high=std::min(high,(a?-.971:-.929)-std::max(f[0],f[1])-rem);
            }
            result=std::max({result,low,high});
        }
        return result;
    }
#endif
};
struct Result {Path path;double loss=1e8,cost=1e8;};
class Scene {
public:
    Pose start,goal;std::vector<Obstacle> obs;
    explicit Scene(const std::string& file){std::ifstream f(file);int n;
        if(!(f>>start.x>>start.y>>start.a>>goal.x>>goal.y>>goal.a>>n)||n<1)throw std::runtime_error("Bad scene");
        while(n--)obs.emplace_back(f);}
    double gap(Pose p)const{double g=1e8,c=std::cos(p.a),s=std::sin(p.a);
        for(const auto& o:obs)g=std::min(g,o.gap(p,c,s));return g;}
    bool certify(Pose p,Stroke st,int level=0)const{
        Pose mid=step(p,{st.k,st.s/2});double g=gap(mid);
        if(g<margin)return false;
        if(g-margin>=.5*std::abs(st.s)*(1+3.89*std::abs(st.k))+1e-10)return true;
#ifdef EAAI_SWEEP
        if((st.k==0||std::abs(st.k)>1e-4)&&level<19){
            Pose q=step(p,st);double leaf=std::ldexp(.5*std::abs(st.s)*(1+3.89*std::abs(st.k)),level-20);
            bool proved=true;for(const auto& o:obs)if(o.sweptBound(p,q,st)<margin+leaf+1e-7){proved=false;break;}
            if(proved)return true;
        }
#endif
        return level<20 && certify(p,{st.k,st.s/2},level+1)&&certify(mid,{st.k,st.s/2},level+1);
    }
    Result score(Pose p,Path path)const{
        Result out;out.path=path;out.cost=duration(path);out.loss=0;double sum=0;int total=0;
        for(auto t:path){int n=std::max(1,int(std::ceil(std::abs(t.s)/.24)));
            for(int i=0;i<=n;i++){double v=std::max(0.,margin-gap(step(p,{t.k,t.s*i/n})));
                sum+=v;out.loss=std::max(out.loss,v);++total;}
            p=step(p,t);}
        out.loss+=sum/std::max(total,1);return out;
    }
    Result connect(Pose p,Pose q,double R)const{
        Result best;
        auto test=[&](Path path){
            Pose end=p;for(auto t:path)end=step(end,t);
            if(std::hypot(end.x-q.x,end.y-q.y)>1e-7||std::abs(wrap(end.a-q.a))>1e-8)return;
            if(best.loss==0 && duration(path)>=best.cost)return;
            auto w=score(p,path);
            if(w.loss<best.loss||(w.loss==best.loss&&w.cost<best.cost))best=w;
        };
        for(int l:{-1,1})for(int r:{-1,1}){
            double r1=l*R,r2=r*R;
            Point c1={p.x-r1*std::sin(p.a),p.y+r1*std::cos(p.a)};
            Point c2={q.x-r2*std::sin(q.a),q.y+r2*std::cos(q.a)};
            double dx=c2.x-c1.x,dy=c2.y-c1.y,D=std::hypot(dx,dy);
            if(D<1e-10)continue;double angle=std::atan2(dy,dx),offset=(r2-r1)/D;
            if(std::abs(offset)<=1)for(double h:{angle-std::asin(offset),angle-pi+std::asin(offset)}){
                test({{1/r1,r1*wrap(h-p.a)},{0,dx*std::cos(h)+dy*std::sin(h)},{1/r2,r2*wrap(q.a-h)}});
            }
            if(l!=r||D>4*R)continue;
            for(int side:{-1,1}){
                double off=side*std::sqrt(std::max(0.,4*R*R-D*D/4));
                Point mid={(c1.x+c2.x)/2-off*dy/D,(c1.y+c2.y)/2+off*dx/D};
                double h=std::atan2(l*(mid.x-c1.x),-l*(mid.y-c1.y));
                double b=std::atan2(l*(mid.x-c2.x),-l*(mid.y-c2.y));
                test({{1/r1,r1*wrap(h-p.a)},{-1/r1,-r1*wrap(b-h)},{1/r1,r1*wrap(q.a-b)}});
            }
        }return best;
    }
    template<class Vector> Result decode(const Vector& u)const{
        auto offset=[](double v){return v<.20?0.:7.*(2*(v-.2)/.8-1);};
        auto curvature=[](double q){return q<.3?0.:std::tan(.7)/wheelbase*(2*(q-.3)/.7-1);};
        Stroke pre{curvature(u[7]),offset(u[0])},post{curvature(u[8]),offset(u[1])};
        Pose a=step(start,pre),b=step(goal,{post.k,-post.s});Path path={pre};
        double R=wheelbase/std::tan(.7)*(1+1.5*u[2]*u[2]);
        if(u[3]<.35){auto part=connect(a,b,R);if(part.path.empty())return {};path.insert(path.end(),part.path.begin(),part.path.end());}
        else{
            double t=1.8*u[4]-.4,side=12*(u[5]-.5),heading=std::atan2(b.y-a.y,b.x-a.x);
            Pose mid={a.x+t*(b.x-a.x)-side*std::sin(heading),a.y+t*(b.y-a.y)+side*std::cos(heading),a.a+(2*u[6]-1)*pi};
            for(auto pair:{std::make_pair(a,mid),std::make_pair(mid,b)}){
                auto part=connect(pair.first,pair.second,R);if(part.path.empty())return {};
                path.insert(path.end(),part.path.begin(),part.path.end());}
        }
        path.push_back(post);auto out=score(start,path);
        if(out.loss==0){Pose p=start;for(auto t:path){if(!certify(p,t)){out.loss=1e-4;break;}p=step(p,t);}}
        return out;
    }
};
}

