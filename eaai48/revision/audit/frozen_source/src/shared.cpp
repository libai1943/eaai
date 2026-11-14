#include "engine.hpp"
#include "parking.hpp"
#include "double_integrator.hpp"
#include "spatial_score.hpp"
#include "spatial.hpp"
#include <chrono>
int main(int argc,char** argv){try{
    if(argc!=7)throw std::runtime_error("family task mode seed budget output");std::string group=argv[1],mode=argv[3];
    auto start=std::chrono::steady_clock::now();std::function<Candidate(const V&)> fn;
    std::unique_ptr<parking::Scene> car;std::unique_ptr<Model> model;
    std::unique_ptr<SpatialChart> spatial;
    int dim,axis;double cut=.5;
    if(group=="parking"){car=std::make_unique<parking::Scene>(argv[2]);dim=9;axis=3;cut=.35;
        fn=[&](const V& x){auto w=car->decode(x);V z(2*w.path.size());int i=0;for(auto s:w.path){z[i++]=s.k;z[i++]=s.s;}
            return Candidate{x,z,w.loss,w.cost};};}
    else{if(group!="uav" && group!="arm")throw std::invalid_argument("Use the rectangular docking adapter for trailers"); model=std::make_unique<Model>(argv[2]);
        {spatial=std::make_unique<SpatialChart>(*model);dim=13;axis=12;cut=.45;}
        fn=[&](const V& x){V z=spatial->decode(x);
            auto s=evaluateNodes(*model,z);
            if(s.violation==0&&!replayAccepted(*model,z))s.violation=.0001;
            return Candidate{x,z,s.violation,s.objective};};}
    std::ofstream log(std::string(argv[6])+".csv");log<<"eval,region,violation,cost,best_violation,best_cost\n"<<std::setprecision(17);
    Search search(std::stoul(argv[4]),dim,std::stoi(argv[5]),axis,cut,mode,fn,log);search.run();
    std::ofstream out(argv[6]);out<<std::setprecision(17)<<"{\"method\":\""<<mode<<"\",\"evaluations\":"<<search.count<<",\"first\":"<<search.first<<",\"loss\":"<<search.winner.loss<<",\"J\":"<<search.winner.J<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"x\":";emit(out,search.winner.x);out<<",\"z\":";emit(out,search.winner.z);out<<"}";
    if(!out||!log)throw std::runtime_error("Cannot write results");
    return 0;}catch(std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

