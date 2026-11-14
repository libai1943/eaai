#pragma once
#include "swarm_types.hpp"
struct SpatialScore {double violation,objective;};
inline SpatialScore evaluateNodes(const Model& m,const V& z){
    if(z.size()!=m.n||!z.allFinite()||z[0]<=0)return {1e20,1e20};
    const double dt=z[0]/(m.N-1);
    const double bounds=std::max({0.,(m.lo-z).maxCoeff(),(z-m.hi).maxCoeff()});
    double dynamics=0,geometry=0,sum=0;
    for(int k=0;k<m.N;k++){
        V x=z.segment(m.ix(k,0),m.nx);
        auto points=m.centres(x);double deficit=0;
        for(int j=0;j<m.ns;j++)for(const auto& box:m.obs){
            double clearance=Model::distance(points[j],box)-m.radii[j];
            deficit=std::max(deficit,m.clearance-clearance);
        }
        geometry=std::max(geometry,deficit);sum+=deficit*deficit;
        if(k+1<m.N){V next=m.step(x,z.segment(m.ix(k,m.nx),m.nu),dt);dynamics=std::max(dynamics,(next-z.segment(m.ix(k+1,0),m.nx)).lpNorm<Eigen::Infinity>());}
    }
    bool feasible=bounds<1e-7 && dynamics<1e-6 && geometry<1e-6;
    return {feasible?0.:bounds+dynamics+geometry+std::sqrt(sum/m.N),m.cost(z)};
}
inline bool replayAccepted(const Model& m,const V& z){
    V x=m.lo.segment(1,m.nx);double h=z[0]/(20*(m.N-1));
    for(int k=0;k<m.N-1;k++)for(int j=0;j<20;j++){
        x=m.step(x,z.segment(m.ix(k,m.nx),m.nu),h);
        if(!x.allFinite()||(m.lo.segment(m.ix(1,0),m.nx)-x).maxCoeff()>=1e-5||(x-m.hi.segment(m.ix(1,0),m.nx)).maxCoeff()>=1e-5)return false;
        auto points=m.centres(x);
        for(int i=0;i<m.ns;i++)for(const auto& box:m.obs)if(Model::distance(points[i],box)<m.radii[i])return false;
    }
    return (x-m.lo.segment(m.ix(m.N-1,0),m.nx)).lpNorm<Eigen::Infinity>()<.001;
}

