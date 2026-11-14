#pragma once
struct SpatialChart {
    const Model& p; DoubleIntegratorDecoder normal;
    explicit SpatialChart(const Model& p):p(p),normal(p){}
    V decode(const V& u)const{
        if(u[12]<.45)return normal.decode(u.head(12));
        std::vector<P> knots={p.lo.segment<3>(1)};
        if(p.kind=="uav"){
            for(int g=0;g<int(p.portals.size());g++){
                const auto& portal=p.portals[g];
                auto span=[](double a,double b,double q){return (a+b)/2+.8*(q-.5)*(b-a);};
                knots.push_back(P(portal.x,span(portal.ylo,portal.yhi,u[2*g]),span(portal.zlo,portal.zhi,u[2*g+1])));
            }
        }else if(u[7]>.45){
            P a=knots.front(),b=p.lo.segment<3>(p.ix(p.N-1,0));
            double shoulder=-.85+2.2*u[1],elbow=-1.4+2.85*u[2];
            knots.push_back(P(a[0]+.22*u[0]*(b[0]-a[0]),shoulder,elbow));
#ifdef EAAI_ARM_OVERTRAVEL
            if(u[9]>.35){
                double direction=b[0]>a[0]?1.:-1.;
                double turn=std::clamp(b[0]+direction*(.04+.85*u[3]),p.lo[p.ix(1,0)],p.hi[p.ix(1,0)]);
                knots.push_back(P(turn,shoulder,elbow));
                knots.push_back(P(turn,b[1],b[2]));
            }else
#endif
            knots.push_back(P(b[0]-.22*u[3]*(b[0]-a[0]),shoulder,elbow));
        }else{
            auto end=p.lo.segment<3>(p.ix(p.N-1,0));P m=.5*(knots[0]+end);
            m+=P(.65*(u[0]-.5),1.5*(u[1]-.5),1.8*(u[2]-.5));knots.push_back(m);
            if(u[3]>.5){P q=.45*m+.55*end;q+=P(.5*(u[4]-.5),1.1*(u[5]-.5),1.2*(u[6]-.5));knots.push_back(q);}
        }
        knots.push_back(p.lo.segment<3>(p.ix(p.N-1,0)));
        int n=p.N-1;M velocities=M::Zero(p.N,3);int pieces=int(knots.size())-1;
        for(int j=0;j<pieces;j++){
            int l=j*n/pieces,r=(j+1)*n/pieces;double sum=0;
            for(int k=l+1;k<r;k++)sum+=std::min(k-l,r-k);
            for(int k=l+1;k<r;k++)velocities.row(k)=std::min(k-l,r-k)/sum*(knots[j+1]-knots[j]).transpose();
        }
        double h=.5/n;
        for(int k=0;k<n;k++)for(int j=0;j<3;j++)
            h=std::max({h,std::abs(velocities(k,j))/p.hi[p.ix(1,3+j)],std::sqrt(std::abs(velocities(k+1,j)-velocities(k,j))/p.hi[p.ix(1,6+j)])});
        h*=1.000000001;V z=V::Zero(p.n),state=p.lo.segment(1,6);z[0]=n*h;
        for(int k=0;k<n;k++){V a=(velocities.row(k+1)-velocities.row(k)).transpose()/(h*h);
            z.segment(p.ix(k,0),6)=state;z.segment(p.ix(k,6),3)=a;state=p.step(state,a,h);}
        z.segment(p.ix(n,0),6)=state;return z;
    }
};

