#pragma once
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <vector>
#include <array>
#include <stdexcept>
using V=Eigen::VectorXd;using M=Eigen::MatrixXd;
struct Candidate { V x,z;double loss=1e10,J=1e10; };
bool better(const Candidate& a,const Candidate& b){return a.loss<b.loss||(a.loss==b.loss&&a.J<b.J);}
void emit(std::ostream& out,const V& x){out<<"[";for(int j=0;j<x.size();j++){if(j)out<<",";out<<x[j];}out<<"]";}
struct Search {
    std::mt19937_64 rng;int dim,budget,count=0,first=0,axis;double cut;std::string mode;
    std::function<Candidate(const V&)> oracle;Candidate winner,archive[2];std::ostream& log;
    std::vector<Candidate> pop;std::vector<V> pos,vel;
    Search(unsigned s,int d,int n,int axis_,double cut_,std::string m,std::function<Candidate(const V&)> fn,std::ostream& log_)
    :rng(s),dim(d),budget(n),axis(axis_),cut(cut_),mode(m),oracle(fn),log(log_){
        const std::vector<std::string> modes={"proposed","balanced","no_poll","no_diff","random","de","pso","cem","poll","bfgs","cma","adaptive","region_equal","region_plain","rc_no_poll","rc_no_refresh","rc_diagonal","cma_matched","cma_regions_equal","cma_regions_adaptive","rc_balanced_first","rc_simple"};
        if(std::find(modes.begin(),modes.end(),mode)==modes.end())throw std::invalid_argument("Unknown search method: "+mode);
        if(budget<24)throw std::invalid_argument("Evaluation budget must be at least 24");
        if(dim<1||axis<0||axis>=dim||!(cut>0&&cut<1))throw std::invalid_argument("Invalid search domain");
    }
    double uniform(){return std::generate_canonical<double,53>(rng);}
    int index(int n){return std::uniform_int_distribution<int>(0,n-1)(rng);}
    double gaussian(){return std::normal_distribution<double>()(rng);}
    double reflect(double x){double a=std::fmod(std::abs(x),2.);return a>1?2-a:a;}
    int label(const V& x){return x[axis]>=cut;}
    Candidate eval(const V& x){Candidate c=oracle(x);c.x=x;++count;
        if(!std::isfinite(c.loss)||!std::isfinite(c.J))throw std::runtime_error("Nonfinite score");
        if(better(c,winner))winner=c;
        int b=label(x);if(better(c,archive[b]))archive[b]=c;
        if(!first&&c.loss==0)first=count;
        log<<count<<','<<b<<','<<c.loss<<','<<c.J<<','<<winner.loss<<','<<winner.J<<'\n';return c;}
    V fresh(){V x(dim);for(double& v:x)v=uniform();return x;}
    void gradient(){
        int start=0;std::sort(pop.begin(),pop.end(),better);
        while(count<budget){
            Candidate c=pop[start++%pop.size()];M H=M::Identity(dim,dim);V previous,disp;
            for(int iter=0;iter<30&&count+dim+1<=budget;iter++){
                V g(dim);double f=c.J+1000*c.loss;
                for(int j=0;j<dim;j++){V x=c.x;double h=x[j]<.9999?1e-4:-1e-4;x[j]+=h;
                    auto y=eval(x);g[j]=(y.J+1000*y.loss-f)/h;}
                if(previous.size()){V y=g-previous;double sy=disp.dot(y);
                    if(sy>1e-10){M A=M::Identity(dim,dim)-disp*y.transpose()/sy;H=A*H*A.transpose()+disp*disp.transpose()/sy;}}
                V dir=-H*g;double scale=dir.lpNorm<Eigen::Infinity>();if(scale<1e-10)break;dir*=std::min(1.,.3/scale);
                bool moved=false;
                for(double s=1;s>=1./64&&count<budget;s*=.5){V x=(c.x+s*dir).cwiseMax(0.).cwiseMin(1.);
                    auto t=eval(x);if(t.J+1000*t.loss<f){previous=g;disp=x-c.x;c=t;moved=true;break;}}
                if(!moved)break;
            }
            if(count+dim+1>budget){while(count<budget)eval(fresh());break;}
        }}
    void covariance(){
        const int lambda=24,mu=12;V weights(mu);
        for(int j=0;j<mu;j++)weights[j]=std::log(mu+.5)-std::log(j+1.);
        weights/=weights.sum();double me=1/weights.squaredNorm(),d=dim;
        double cc=(4+me/d)/(d+4+2*me/d),cs=(me+2)/(d+me+5),c1=2/(std::pow(d+1.3,2)+me);
        double cm=std::min(1-c1,2*(me-2+1/me)/(std::pow(d+2,2)+me));
        double damp=1+2*std::max(0.,std::sqrt((me-1)/(d+1))-1)+cs;
        double expected=std::sqrt(d)*(1-1/(4*d)+1/(21*d*d)),sigma=.24;
        M C=M::Identity(dim,dim);V pc=V::Zero(dim),ps=pc,mean=pc;
        std::sort(pop.begin(),pop.end(),better);
        for(int j=0;j<mu;j++)mean+=weights[j]*pop[j].x;
        for(int gen=1;count<budget;gen++){
            Eigen::SelfAdjointEigenSolver<M> eig(C);V D=eig.eigenvalues().cwiseMax(1e-14).cwiseSqrt();
            M B=eig.eigenvectors(),A=B*D.asDiagonal(),inverse=B*D.cwiseInverse().asDiagonal()*B.transpose();
            std::vector<Candidate> batch;
            for(int j=0;j<lambda&&count<budget;j++){
                V noise(dim);for(double& n:noise)n=gaussian();V x=mean+sigma*A*noise;
                for(double& v:x)v=reflect(v);batch.push_back(eval(x));
            }
            if(int(batch.size())<mu)break;std::sort(batch.begin(),batch.end(),better);V next=V::Zero(dim);M rank=M::Zero(dim,dim);
            for(int j=0;j<mu;j++){next+=weights[j]*batch[j].x;V y=(batch[j].x-mean)/sigma;rank+=weights[j]*y*y.transpose();}
            V y=(next-mean)/sigma;ps=(1-cs)*ps+std::sqrt(cs*(2-cs)*me)*inverse*y;
            bool h=ps.norm()/std::sqrt(1-std::pow(1-cs,2*gen))<(1.4+2/(d+1))*expected;
            pc=(1-cc)*pc+double(h)*std::sqrt(cc*(2-cc)*me)*y;
            C=(1-c1-cm+(!h)*c1*cc*(2-cc))*C+c1*pc*pc.transpose()+cm*rank;
            sigma=std::clamp(sigma*std::exp(cs/damp*(ps.norm()/expected-1)),1e-6,2.);mean=next;
        }
    }
#include "adaptive.inc"
    void run(){
        const int n=24;std::vector<V> lhs(n,V(dim));std::vector<int> slots(n);std::iota(slots.begin(),slots.end(),0);
        for(int j=0;j<dim;j++){std::shuffle(slots.begin(),slots.end(),rng);for(int i=0;i<n;i++)lhs[i][j]=(slots[i]+uniform())/n;}
        for(auto x:lhs){pop.push_back(eval(x));pos.push_back(x);vel.push_back(V::Zero(dim));}
        if(mode=="bfgs"){gradient();return;}
        if(mode=="cma_matched"||mode.rfind("cma_regions_",0)==0||mode=="adaptive"||mode=="region_equal"||mode=="region_plain"||mode.rfind("rc_",0)==0){adaptRegions();return;}
        if(mode=="cma"){covariance();return;}
        int turn=0;double radii[2]={.18,.18};
        while(count<budget){
            std::vector<Candidate> ranked=pop;std::sort(ranked.begin(),ranked.end(),better);V mean=V::Zero(dim),sd=mean;
            if(mode=="cem"){for(int i=0;i<6;i++)mean+=ranked[i].x/6;for(int i=0;i<6;i++)sd+=(ranked[i].x-mean).cwiseAbs2()/6;sd=sd.cwiseSqrt().cwiseMax(.025);}
            auto old=pop;Candidate lead=winner;
            for(int i=0;i<n&&count<budget;i++,turn++){
                V x=pop[i].x;int target=i;
                if(mode=="random")x=fresh();
                else if(mode=="pso"){
                    for(int j=0;j<dim;j++){vel[i][j]=std::clamp(.72984*vel[i][j]+1.49618*uniform()*(old[i].x[j]-pos[i][j])+1.49618*uniform()*(lead.x[j]-pos[i][j]),-.35,.35);
                        pos[i][j]=reflect(pos[i][j]+vel[i][j]);}x=pos[i];
                }else if(mode=="de"){std::vector<int> ids;for(int k=0;k<n;k++)if(k!=i)ids.push_back(k);std::shuffle(ids.begin(),ids.end(),rng);
                    int mandatory=index(dim);for(int j=0;j<dim;j++)if(j==mandatory||uniform()<.9)x[j]=reflect(old[ids[0]].x[j]+.8*(old[ids[1]].x[j]-old[ids[2]].x[j]));}
                else if(mode=="cem"){for(int j=0;j<dim;j++)x[j]=reflect(mean[j]+sd[j]*gaussian());}
                else if(mode=="poll"){x=winner.x;int j=index(dim);x[j]=reflect(x[j]+(.2*std::pow(.08,double(count)/budget))*gaussian());}
                else{
                    int b=mode=="balanced"?turn%2:(turn/4)%2;
                    if(mode!="balanced" && turn%4!=0)b=label(winner.x);
                    std::vector<int> slots;for(int k=0;k<n;k++)if(label(pop[k].x)==b)slots.push_back(k);
                    if(slots.empty()){x=fresh();x[axis]=b?cut+(1-cut)*uniform():cut*uniform();}
                    else{
                        target=slots[index(int(slots.size()))];x=archive[b].x;
                        if(turn%12==0)x=fresh();
                        else if(turn%3!=0 && mode!="no_poll"){int j=index(dim);x[j]=reflect(x[j]+radii[b]*gaussian());}
                        else{int a=slots[index(int(slots.size()))],d=slots[index(int(slots.size()))];int must=index(dim);
                            for(int j=0;j<dim;j++)if(j==must||uniform()<.75)x[j]=reflect(x[j]+(mode=="no_diff"?0.:.6)*(pop[a].x[j]-pop[d].x[j])+.075*gaussian());}
                        if(label(x)!=b)x[axis]=b?cut+(1-cut)*uniform():cut*uniform();
                    }
                    auto prev=archive[b];auto t=eval(x);
                    radii[b]=std::clamp(radii[b]*(better(t,prev)?1.16:.976),.006,.3);
                    if(better(t,pop[target])||turn%12==0)pop[target]=t;
                    continue;
                }
                auto t=eval(x);if(mode=="cem"||better(t,pop[i]))pop[i]=t;
            }
        }
    }
};
