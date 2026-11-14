#include "engine.hpp"
#include "parking.hpp"
#include "swarm_types.hpp"
// A common direct-shooting alternative with six control knots per channel; no terminal repair.
int main(int argc,char**argv){try{
    if(argc!=7)throw std::runtime_error("family task method seed budget output");
    std::string kind=argv[1];bool parking=kind=="parking";
    if(!parking && kind!="arm" && kind!="uav")throw std::invalid_argument("Use the docking adapter");std::unique_ptr<Model> m;std::unique_ptr<parking::Scene> car;
    int n=81,nx=5,nu=2;V start,goal,lo,hi;
    if(parking){car=std::make_unique<parking::Scene>(argv[2]);start.resize(5);goal.resize(5);
        start<<car->start.x,car->start.y,car->start.a,0,0;goal<<car->goal.x,car->goal.y,car->goal.a,0,0;
        lo.resize(7);lo<<-1e5,-1e5,-1e5,-2.5,-.7,-1,-.5;hi=-lo;
    }else{m=std::make_unique<Model>(argv[2]);n=m->N;nx=m->nx;nu=m->nu;start=m->lo.segment(1,nx);goal=m->lo.segment(m->ix(n-1,0),nx);
        lo=m->lo.segment(m->ix(1,0),m->b);hi=m->hi.segment(m->ix(1,0),m->b);}
    auto eval=[&](const V& x){double T=.5+99.5*x[0],h=T/(n-1),loss=0.;V state=start,z=V::Zero(1+n*(nx+nu));z[0]=T;
        for(int k=0;k<n;k++){
            int i=1+k*(nx+nu);z.segment(i,nx)=state;
            loss=std::max({loss,(lo.head(nx)-state).maxCoeff(),(state-hi.head(nx)).maxCoeff()});
            if(parking)loss=std::max(loss,.01-car->gap({state[0],state[1],state[2]}));
            else{auto pts=m->centres(state);for(int a=0;a<m->ns;a++)for(auto& o:m->obs)loss=std::max(loss,m->radii[a]+.03-Model::distance(pts[a],o));
                if(kind=="trailer")loss=std::max(loss,std::abs(state[2]-state[5])-1.2);}
            if(k==n-1)break;
            double phase=5.*k/(n-2);int j=std::min(4,int(phase));double t=phase-j;
            V u(nu);for(int l=0;l<nu;l++)u[l]=hi[nx+l]*(2*((1-t)*x[1+j*nu+l]+t*x[1+(j+1)*nu+l])-1);
            z.segment(i+nx,nu)=u;
            if(!parking){state=m->step(state,u,h);}
            else{
                auto flow=[&](const V& y){V r(5);r<<y[3]*std::cos(y[2]),y[3]*std::sin(y[2]),y[3]*std::tan(y[4])/2.8,u[0],u[1];return r;};
                V a=flow(state),b=flow(state+.5*h*a),c=flow(state+.5*h*b),d=flow(state+h*c);state+=(h/6)*(a+2*b+2*c+d);}
        }
        V error=state-goal;if(parking)error[2]=parking::wrap(error[2]);
        loss+=std::max(0.,error.lpNorm<Eigen::Infinity>()-.001);
        return Candidate{x,z,loss,parking?T:m->cost(z)};};
    std::ofstream log(std::string(argv[6])+".csv");log<<"eval,region,violation,cost,best_violation,best_cost\n"<<std::setprecision(17);
    Search search(std::stoul(argv[4]),1+6*nu,std::stoi(argv[5]),1,.5,argv[3],eval,log);search.run();
    std::ofstream out(argv[6]);out<<std::setprecision(17)<<"{\"evaluations\":"<<search.count<<",\"first\":"<<search.first<<",\"loss\":"<<search.winner.loss<<",\"J\":"<<search.winner.J<<",\"z\":";
    emit(out,search.winner.z);out<<"}";return out&&log?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

