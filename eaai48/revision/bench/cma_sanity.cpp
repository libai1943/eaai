// Functional cross-check objective; uses the exact production Search::covariance path.
#include "../src/engine.hpp"
#include <sstream>
int main(int argc,char** argv){
    int n=std::stoi(argv[1]),seed=std::stoi(argv[2]),budget=std::stoi(argv[3]);
    auto f=[&](const V& x){V delta=x-V::Constant(n,.37);double sum=delta.sum(),J=0;
        for(int i=0;i<n;i++){double a=delta[i]-2*sum/n;J+=std::pow(1000.,double(i)/(n-1))*a*a;}
        return Candidate{x,V(),0,J};};
    std::ostringstream log;Search opt(seed,n,budget,0,.5,"cma",f,log);opt.run();
    std::cout<<std::setprecision(17)<<opt.winner.J<<'\n';
}
