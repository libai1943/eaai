#pragma once
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

using V = Eigen::VectorXd;
using M = Eigen::MatrixXd;
using P = Eigen::Vector3d;
struct Box { P lo, hi; };
struct Portal { double x,ylo,yhi,zlo,zhi; };

// Read the original endpoint-only task directly. There is no trajectory input.
struct Model {
    std::string kind;
    int N, nx, nu, b, ns, n;
    double clearance = .03;
    V lo, hi;
    std::vector<double> radii;
    std::vector<Box> obs;
    std::vector<Portal> portals;

    explicit Model(const std::string& path) {
        std::ifstream input(path);
        double unusedNominalDuration;
        int obstacleCount;
        if (!(input >> kind >> N >> nx >> nu >> unusedNominalDuration >> obstacleCount)
                || N < 5 || obstacleCount < 1
                || !((kind == "uav" || kind == "arm") && nx == 6 && nu == 3))
            throw std::runtime_error("Invalid endpoint-only task header: " + path);
        obs.resize(obstacleCount);
        for (auto& box : obs) {
            for (double& v : box.lo) input >> v;
            for (double& v : box.hi) input >> v;
            if (!input || !box.lo.allFinite() || !box.hi.allFinite() || !(box.lo.array() < box.hi.array()).all()) throw std::runtime_error("Invalid obstacle bounds");
        }
        // Legacy task files explicitly encode each rectangular opening as L/R/B/T boxes.
        // Validate once and convert to a typed portal list before decoding any candidate.
        if(kind=="uav"){
            if(obs.size()%4 || obs.size()>24)throw std::runtime_error("Flight task requires 1--6 ordered L/R/B/T wall groups");
            for(size_t i=0;i<obs.size();i+=4){
                const auto &l=obs[i],&r=obs[i+1],&b=obs[i+2],&t=obs[i+3];
                auto same=[](double x,double y){return std::abs(x-y)<1e-9;};
                for(size_t j=i+1;j<i+4;j++)if(!same(l.lo[0],obs[j].lo[0])||!same(l.hi[0],obs[j].hi[0]))throw std::runtime_error("Wall group has inconsistent thickness");
                if(!(l.hi[1]<r.lo[1]&&b.hi[2]<t.lo[2])||!same(b.lo[1],l.hi[1])||!same(b.hi[1],r.lo[1])||!same(t.lo[1],l.hi[1])||!same(t.hi[1],r.lo[1]))throw std::runtime_error("Invalid rectangular portal geometry");
                portals.push_back({.5*(l.lo[0]+l.hi[0]),l.hi[1],r.lo[1],b.hi[2],t.lo[2]});
            }
            if(N-1<2*int(portals.size()+1))throw std::runtime_error("Insufficient control intervals for portals");
        }
        b = nx + nu;
        n = 1 + N*b;
        V lower(b), upper(b), start(nx), goal(nx);
        for (double& v : lower) input >> v;
        for (double& v : upper) input >> v;
        for (double& v : start) input >> v;
        for (double& v : goal) input >> v;
        if (!input || !lower.allFinite() || !upper.allFinite() || !start.allFinite() || !goal.allFinite())
            throw std::runtime_error("Invalid endpoint or bound");
        std::string extra;
        if (input >> extra) throw std::runtime_error("Unexpected data following endpoints");
        lo.resize(n); hi.resize(n); lo[0] = .5; hi[0] = 100.;
        for (int k=0; k<N; ++k) {
            lo.segment(ix(k,0),b)=lower; hi.segment(ix(k,0),b)=upper;
        }
        lo.segment(ix(0,0),nx)=hi.segment(ix(0,0),nx)=start;
        lo.segment(ix(N-1,0),nx)=hi.segment(ix(N-1,0),nx)=goal;
        lo.tail(nu).setZero(); hi.tail(nu).setZero();
        if (kind == "uav") radii = {.22};
        if (kind == "arm") radii = std::vector<double>(8,.13);
        ns = static_cast<int>(radii.size());
    }
    int ix(int k, int d) const { return 1+k*b+d; }
    V step(const V& x, const V& u, double h) const {
        V out(6); out.head(3)=x.head(3)+h*x.tail(3)+(.5*h*h)*u;
        out.tail(3)=x.tail(3)+h*u; return out;
    }
    std::vector<P> centres(const V& x) const {
        if (kind=="uav") return {x.head(3)};
        std::vector<P> c; c.reserve(ns);
        if (kind=="arm") {
            double a=x[0], b=x[1], e=b+x[2];
            P base(0,0,1), v(.9*cos(a)*cos(b),.9*sin(a)*cos(b),.9*sin(b));
            P w(.8*cos(a)*cos(e),.8*sin(a)*cos(e),.8*sin(e));
            for (int j=0;j<4;++j) c.push_back(base+((j+.5)/4)*v);
            for (int j=0;j<4;++j) c.push_back(base+v+((j+.5)/4)*w);
            return c;
        }
        throw std::logic_error("Unknown spatial model");
    }
    static double distance(const P& p,const Box& o) {
        const P outside=(o.lo-p).cwiseMax(p-o.hi).cwiseMax(P::Zero());
        if (outside.squaredNorm()>0.) return outside.norm();
        return -std::min((p-o.lo).minCoeff(),(o.hi-p).minCoeff());
    }
    double cost(const V& z) const {
        double effort=0., variation=0.;
        for (int k=0;k<N-1;++k) {
            const auto u=z.segment(ix(k,nx),nu); effort+=u.squaredNorm();
            if (k) variation+=(u-z.segment(ix(k-1,nx),nu)).squaredNorm();
        }
        return z[0]+.01*effort/(N-1)+.002*variation;
    }
};
