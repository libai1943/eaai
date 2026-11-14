#define REGION_DOCK_NO_CLI
#include "docking.cpp"
int main(int argc,char** argv){try{
    if(argc!=6)throw std::runtime_error("scene mode seed budget output");
    dock::Scene scene(argv[1]);std::ofstream log(std::string(argv[5])+".csv");
    log<<"eval,region,violation,cost,best_violation,best_cost\n"<<std::setprecision(17);
    auto oracle=[&](const V& u){
        double T=.5+99.5*u[0],h=T/120;using State=Eigen::Matrix<double,6,1>;
        State x;x<<scene.start.x,scene.start.y,scene.start.h,0.,0.,scene.start.p;
        double loss=0,vmin=0,vmax=0;std::vector<int> gears;
        for(int i=0;i<120;i++){double phase=5.*i/119;int j=std::min(4,int(phase));double f=phase-j;
            double a=.25*(2*((1-f)*u[1+2*j]+f*u[3+2*j])-1);
            double w=.5*(2*((1-f)*u[2+2*j]+f*u[4+2*j])-1);
            auto rhs=[&](State y){State r;double dh=y[3]*std::tan(y[4])/1.5,delta=y[2]-y[5];r<<y[3]*std::cos(y[2]),y[3]*std::sin(y[2]),dh,a,w,(y[3]*std::sin(delta)-1.5*dh*std::cos(delta))/3;return r;};
            State p=rhs(x),q=rhs(x+h*p/2),r=rhs(x+h*q/2),s=rhs(x+h*r);x+=h*(p+2*q+2*r+s)/6;
            loss=std::max({loss,.06-scene.gap({x[0],x[1],x[2],x[5]}),std::abs(x[3])-1.5,std::abs(x[4])-.7,std::abs(x[2]-x[5])-1.2});
            vmin=std::min(vmin,x[3]);vmax=std::max(vmax,x[3]);
            if(std::abs(x[3])>.05){int sign=x[3]>0?1:-1;if(gears.empty()||gears.back()!=sign)gears.push_back(sign);}
        }
        State g;g<<scene.goal.x,scene.goal.y,scene.goal.h,0,0,scene.goal.p;
        loss+=std::max(0.,(x-g).lpNorm<Eigen::Infinity>()-.001)+std::max(0.,vmin+.05)+std::max(0.,.05-vmax);
        if(gears!=(scene.withdrawal?std::vector<int>{-1,1,-1}:std::vector<int>{1,-1}))loss+=1.;
        return Candidate{u,u,loss,T};};
    Search st(std::stoul(argv[3]),13,std::stoi(argv[4]),1,.5,argv[2],oracle,log);st.run();
    std::ofstream out(argv[5]);out<<std::setprecision(17)<<"{\"first\":"<<st.first<<",\"loss\":"<<st.winner.loss<<",\"evaluations\":"<<st.count<<",\"x\":";emit(out,st.winner.x);out<<"}";
    return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}

