#pragma once
#include "swarm_types.hpp"
#include <array>

// A nodal velocity diagram represents a piecewise-constant acceleration exactly.
// Its endpoint velocities fix the zeroth acceleration moment. Its trapezoidal
// area fixes displacement, equivalently the first weighted acceleration moment.
struct DoubleIntegratorDecoder {
    explicit DoubleIntegratorDecoder(const Model& model) : p(model), basis(model.N, 3) {
        if ((p.kind != "arm" && p.kind != "uav") || p.nx != 6 || p.nu != 3)
            throw std::invalid_argument("DoubleIntegratorDecoder needs three double integrators");
        const double pi = std::acos(-1.);
        const std::array<int,3> harmonics{0, 1, 4};
        for (int k = 0; k < p.N; ++k) {
            double t = double(k)/(p.N-1), envelope = std::pow(std::sin(pi*t),2);
            for (int j=0; j<3; ++j) {
                double w = harmonics[j]*pi;
                basis(k,j) = pi*std::sin(2*pi*t)*std::cos(w*t) - w*envelope*std::sin(w*t);
            }
        }
        basis.row(0).setZero();
        basis.row(p.N-1).setZero();
        basisArea = basis.colwise().sum() / double(p.N-1);
        for (int j = 0; j < 3; ++j) {
            double range = p.hi[p.ix(1,j)]-p.lo[p.ix(1,j)];
            bendScale[j] = .19*range;
        }
    }

    int dimension() const { return 12; } // time slack, two ramp lengths, three bends per coordinate

    V decode(const V& unit) const {
        if (unit.size()!=dimension()) throw std::invalid_argument("Incorrect double-integrator particle dimension");
        const int m = p.N-1;
        P start = p.lo.segment<3>(p.ix(0,0)), goal = p.lo.segment<3>(p.ix(m,0));
        P v0 = p.lo.segment<3>(p.ix(0,3)), vf = p.lo.segment<3>(p.ix(m,3));
        double left = .09+.40*unit[1], right = .09+.40*unit[2];
        V profile(p.N);
        for (int k=0; k<=m; ++k) {
            double t = double(k)/m;
            profile[k] = std::min({t/left,1.,(1.-t)/right});
        }
        profile *= m/profile.sum(); // area is one; both endpoints are exactly zero
        Eigen::Matrix3d coeff;
        for (int axis=0; axis<3; ++axis) {
            for (int j=0; j<3; ++j) {
                // A smooth bias toward modest bends while preserving both signs.
                double s = 2.*unit[3+3*axis+j]-1.;
                double amplitude = (j==1 ? .85 : 1.)*bendScale[axis];
                coeff(j,axis) = amplitude*s*std::abs(s);
            }
        }
        // Subtract the sampled area of every perturbation. Displacements stay
        // exact on any mesh, including when a ramp breakpoint lies inside a cell.
        const Eigen::RowVector3d direction = (goal-start).transpose()-basisArea*coeff;
        M shape = basis*coeff;
        shape.noalias() += profile*direction;
        M drift(p.N,3);
        const P average = .5*(v0+vf);
        for (int k=0; k<=m; ++k) {
            double t = double(k)/m;
            drift.row(k) = ((1.-t)*v0+t*vf-profile[k]*average).transpose();
        }
        // Physical velocity is drift + shape/T. With the rest endpoints of
        // the experiments, the least admissible time follows componentwise
        // from max |shape| and sqrt(max |discrete acceleration|).
        double tmin = p.lo[0], tmax = p.hi[0];
        for (int axis=0; axis<3; ++axis) {
            const double vlow=p.lo[p.ix(1,3+axis)], vhigh=p.hi[p.ix(1,3+axis)];
            const double alow=p.lo[p.ix(1,6+axis)], ahigh=p.hi[p.ix(1,6+axis)];
            if (!(vlow<0. && vhigh>0. && alow<0. && ahigh>0.))
                throw std::invalid_argument("Velocity and acceleration ranges must bracket zero");
            for (int k=0; k<=m; ++k) {
                limitLinear(shape(k,axis), vhigh-drift(k,axis), tmin,tmax);
                limitLinear(-shape(k,axis), drift(k,axis)-vlow, tmin,tmax);
                if (k==m) break;
                const double apath=m*(shape(k+1,axis)-shape(k,axis));
                const double adrift=m*(drift(k+1,axis)-drift(k,axis));
                tmin=std::max({tmin,positiveRoot(ahigh,adrift,apath),positiveRoot(-alow,-adrift,-apath)});
            }
        }
        // Infeasible shapes still decode to finite physical candidates and are
        // scored by the common bound/obstacle checks. No state is clipped.
        const double slack=unit[0]*unit[0]*unit[0];
        double tlimit=std::clamp(tmax,p.lo[0],p.hi[0]);
        double T=std::clamp(tmin*(1.+.6*slack),p.lo[0],tlimit);
        M velocity=drift+shape/T;
        V z=V::Zero(p.n);
        z[0]=T;
        P pos=start;
        for (int k=0; k<=m; ++k) {
            z.segment<3>(p.ix(k,0))=pos;
            z.segment<3>(p.ix(k,3))=velocity.row(k).transpose();
            if (k<m) {
                z.segment<3>(p.ix(k,6))=(m/T)*(velocity.row(k+1)-velocity.row(k)).transpose();
                pos+=(.5*T/m)*(velocity.row(k)+velocity.row(k+1)).transpose();
            }
        }
        return z;
    }

private:
    const Model& p;
    M basis;
    Eigen::RowVector3d basisArea;
    P bendScale;
    // Intersect v <= c*T with the duration interval.
    static void limitLinear(double v,double c,double& lower,double& upper) {
        if (c>0.) lower=std::max(lower,v/c);
        else if (c<0.) upper=std::min(upper,v/c);
    }
    // Smallest nonnegative threshold above which cap*T^2 >= b*T+c.
    static double positiveRoot(double cap,double b,double c) {
        double disc=b*b+4.*cap*c;
        if (disc<=0.) return 0.;
        double s=std::sqrt(disc);
        if (b>=0.) return (b+s)/(2.*cap);
        return c>0. ? 2.*c/(s-b) : 0.;
    }
};
