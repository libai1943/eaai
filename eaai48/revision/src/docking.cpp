// The search engine is shared with the other robot families. This adapter accepts only the new docking format.
#include "engine.hpp"
#include "parking.hpp"
namespace dock {
constexpr int N=96;
constexpr double pi=parking::pi;
struct Box {double x,y,h,lo,hi,w;};
struct Pose {double x,y,h,p;};
struct Leg {double s,A,k,T;int sign;}; // s is positive length; k is the articulation shape skew.
double separation(const Box& a,const Box& b){
    double ca=std::cos(a.h),sa=std::sin(a.h),cb=std::cos(b.h),sb=std::sin(b.h);
    double dx=b.x+.5*(b.lo+b.hi)*cb-a.x-.5*(a.lo+a.hi)*ca;
    double dy=b.y+.5*(b.lo+b.hi)*sb-a.y-.5*(a.lo+a.hi)*sa;
    double ax=.5*(a.hi-a.lo),bx=.5*(b.hi-b.lo),c=std::abs(ca*cb+sa*sb),s=std::abs(sa*cb-ca*sb);
    return std::max({std::abs(dx*ca+dy*sa)-ax-bx*c-b.w*s,std::abs(-dx*sa+dy*ca)-a.w-bx*s-b.w*c,
        std::abs(dx*cb+dy*sb)-bx-ax*c-a.w*s,std::abs(-dx*sb+dy*cb)-b.w-ax*s-a.w*c});
}
struct Shape { double alpha, curvature, steeringSlope; };
Shape shape(double u,double A,double skew,double length){
    double t=2*pi*u,si=std::sin(t),co=std::cos(t);
    double g=.5*(1-co),dg=pi*si,ddg=2*pi*pi*co;
    double f=1+skew*si,df=2*pi*skew*co,ddf=-4*pi*pi*skew*si;
    double a=A*g*f,as=A*(dg*f+g*df)/length,ass=A*(ddg*f+2*dg*df+g*ddf)/(length*length);
    double b=1+.5*std::cos(a),q=(as+std::sin(a)/3)/b;
    double qs=(ass+std::cos(a)*as/3+.5*q*std::sin(a)*as)/b;
    return {a,q,1.5*qs/(1+2.25*q*q)};
}
struct Stroke {
    Leg leg;std::array<Pose,N+1> q;double excess=0;
    Stroke(Pose start,double delta,double amp,double skew,double length=0){
        if(delta!=0){
            double f=0;for(int i=0;i<=N;i++){double a=shape(double(i)/N,amp,skew,1).alpha;
                f+=(i==0||i==N?1:(i%2?4:2))*std::sin(a)/(3*(1+.5*std::cos(a)));}
            length=delta/(f/(3*N));
        }else amp=skew=0;
        length=std::max(length,1e-8);q[0]=start;double ds=length/N,rate=0;
        if(amp==0){
            for(int i=1;i<=N;i++)q[i]={start.x+i*ds*std::cos(start.h),start.y+i*ds*std::sin(start.h),start.h,start.p};
            leg={length,0,0,1.01*std::max(pi*length/3.,pi*std::sqrt(length/.5)),1};return;
        }
        for(int i=0;i<N;i++){
            auto a=shape(double(i)/N,amp,skew,length),b=shape((i+.5)/N,amp,skew,length),c=shape(double(i+1)/N,amp,skew,length);
            auto p=q[i];double h0=p.h,h1=h0+.5*ds*a.curvature,h2=h0+.5*ds*b.curvature,h3=h0+ds*b.curvature;
            double h=h0+ds*(a.curvature+4*b.curvature+c.curvature)/6;
            q[i+1]={p.x+ds*(std::cos(h0)+2*std::cos(h1)+2*std::cos(h2)+std::cos(h3))/6,
                p.y+ds*(std::sin(h0)+2*std::sin(h1)+2*std::sin(h2)+std::sin(h3))/6,h,h-c.alpha};
            for(auto v:{a,b,c}){rate=std::max(rate,std::abs(v.steeringSlope));
                excess=std::max({excess,std::abs(std::atan(1.5*v.curvature))-.7,std::abs(v.alpha)-1.2});}
        }
        double T=std::max({pi*length/3.,pi*std::sqrt(length/.5),pi*length*rate}); // limits v=1.5, a=.25, steering rate=.5
        leg={length,amp,skew,T*1.01,1};
    }
    void translate(double x,double y){for(auto& p:q){p.x+=x;p.y+=y;}}
};
struct Scene {
    Pose start,goal;std::vector<Box> boxes;bool withdrawal=false;
    explicit Scene(const char* file){std::ifstream f(file);int n;
        if(!(f>>start.x>>start.y>>start.h>>goal.x>>goal.y>>goal.h>>n))throw std::runtime_error("bad docking scene");
        start.p=start.h;goal.p=goal.h;while(n--){double x,y,h,l,w;f>>x>>y>>h>>l>>w;boxes.push_back({x,y,h,-l/2,l/2,w/2});}
        int flag=0;if(f>>flag)withdrawal=flag!=0;}
    double gap(Pose p)const{
        Box tractor{p.x,p.y,p.h,-.25,1.8,.90};
        Box trailer{p.x-1.5*std::cos(p.h)-3*std::cos(p.p),p.y-1.5*std::sin(p.h)-3*std::sin(p.p),p.p,-1.2,2.25,.95};
        double g=1e9;for(auto& b:boxes)g=std::min({g,separation(tractor,b),separation(trailer,b)});return g;
    }
    Candidate evaluate(const V& u)const{
        double turn=(u[0]<.5?-1.:1.)*(.02+.31*u[1]);double h=start.h+turn;
        double withdraw=withdrawal?4.5+6.5*u[7]:0.;
        Pose exitStart=start;exitStart.x-=withdraw*std::cos(start.h);exitStart.y-=withdraw*std::sin(start.h);
        Stroke pullback(exitStart,0,0,0,withdraw);
        Stroke approach(exitStart,turn,turn*(1.25+1.05*u[2]),.32*(2*u[3]-1));
        double delta=parking::wrap(h-goal.h);
        Stroke exit(goal,delta,std::copysign(.59+.43*u[4],delta),.32*(2*u[5]-1));
        auto a=approach.q.back(),b=exit.q.back();double c=std::cos(h),s=std::sin(h),cg=std::cos(goal.h),sg=std::sin(goal.h);
        double tail=(-(a.x-b.x)*s+(a.y-b.y)*c)/std::sin(goal.h-h);
        double extra=.15+3.5*u[6],run=(b.x+tail*cg-a.x)*c+(b.y+tail*sg-a.y)*s+extra;
        double loss=std::max(0.,-tail)+std::max(0.,-run);tail=std::max(tail,0.);run=std::max(run,0.);
        exit.translate(tail*cg,tail*sg);
        Stroke dockStraight(goal,0,0,0,tail), aisle(a,0,0,0,run), extension(exit.q.back(),0,0,0,extra);
        std::vector<std::pair<Stroke*,int>> parts={{&approach,1},{&aisle,1},{&extension,-1},{&exit,-1},{&dockStraight,-1}};
        if(withdrawal)parts.insert(parts.begin(),{&pullback,-1});
        double T=0,penetration=0;int k=0;V z(5*parts.size());
        for(auto [st,sign]:parts){
            loss+=std::max(0.,st->excess);for(auto pose:st->q)penetration=std::max(penetration,.06-gap(pose));
            const auto& l=st->leg;z.segment<5>(5*k)<<l.s,l.A,l.k,l.T,sign;
            ++k;T+=l.T;
        }
        return {u,z,loss+std::max(0.,penetration),T};
    }
};
}
#ifndef REGION_DOCK_NO_CLI
int main(int argc,char** argv){try{
    if(argc!=6)throw std::runtime_error("scene mode seed budget output");
    dock::Scene p(argv[1]);std::ofstream log(std::string(argv[5])+".csv");
    log<<"eval,region,violation,cost,best_violation,best_cost\n"<<std::setprecision(17);
    Search solver(std::stoul(argv[3]),p.withdrawal?8:7,std::stoi(argv[4]),0,.5,argv[2],[&](const V& x){return p.evaluate(x);},log);solver.run();
    std::ofstream out(argv[5]);out<<std::setprecision(17)<<"{\"method\":\""<<argv[2]<<"\",\"evaluations\":"<<solver.count<<",\"first\":"<<solver.first<<",\"loss\":"<<solver.winner.loss<<",\"J\":"<<solver.winner.J<<",\"z\":";
    emit(out,solver.winner.z);out<<",\"x\":";emit(out,solver.winner.x);out<<"}";return out&&log?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
#endif

