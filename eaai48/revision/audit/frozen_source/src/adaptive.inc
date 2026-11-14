// One covariance distribution per motion family. Residuals and accepted costs use the same rank.
void adaptRegions(){
    const bool global=mode=="cma_matched";
    const bool pure=mode=="region_plain"||mode.rfind("cma_",0)==0;
    const bool simple=mode=="rc_simple";
    const bool balanced=mode=="rc_balanced_first"||simple;
    struct Distribution {V mean,ps,pc;M C;double scale=.23;int updates=0;};
    std::array<Distribution,2> model;
    auto encode=[&](V x,int b){if(!global)x[axis]=b?(x[axis]-cut)/(1-cut):x[axis]/cut;return x;};
    auto decode=[&](V x,int b){for(double& v:x)v=reflect(v);if(!global)x[axis]=b?cut+(1-cut)*x[axis]:cut*std::min(x[axis],1.-1e-12);return x;};
    for(int b=0;b<2;b++){auto& m=model[b];m.mean=V::Constant(dim,.5);m.ps=V::Zero(dim);m.pc=m.ps;m.C=M::Identity(dim,dim);
        std::vector<Candidate> residents;for(auto& c:pop)if(global||label(c.x)==b)residents.push_back(c);
        std::sort(residents.begin(),residents.end(),better);if(!residents.empty()){
            m.mean.setZero();int n=std::min(4,int(residents.size()));for(int j=0;j<n;j++)m.mean+=encode(residents[j].x,b)/n;}}
    constexpr int batch=12,mu=6;V weights(mu);for(int j=0;j<mu;j++)weights[j]=std::log(mu+.5)-std::log(j+1.);
    weights/=weights.sum();double me=1/weights.squaredNorm(),d=dim;
    double cc=(4+me/d)/(d+4+2*me/d),cs=(me+2)/(d+me+5),c1=2/(std::pow(d+1.3,2)+me);
    double cm=std::min(1-c1,2*(me-2+1/me)/(std::pow(d+2,2)+me));
    double damp=1+2*std::max(0.,std::sqrt((me-1)/(d+1))-1)+cs,expected=std::sqrt(d)*(1-1/(4*d)+1/(21*d*d));
    for(int epoch=0;count<budget;epoch++){
        // Phase reversal preserves a reserved refresh in each region over eight
        // batches, while allocating exactly half the batches to each region.
        int b=mode=="region_equal"?((epoch%2)^((epoch/4)%2)):(epoch%4==0?(epoch/4)%2:label(winner.x));
        if(mode=="cma_regions_equal" || (balanced && first==0))b=epoch%2;
        if(global)b=0;
        Distribution& m=model[b];++m.updates;Eigen::SelfAdjointEigenSolver<M> eig(m.C);V di=eig.eigenvalues().cwiseMax(1e-14).cwiseSqrt();
        M A=eig.eigenvectors()*di.asDiagonal(),W=eig.eigenvectors()*di.cwiseInverse().asDiagonal()*eig.eigenvectors().transpose();
        std::vector<Candidate> sample;
        for(int j=0;j<batch&&count<budget;j++){
            V x(dim);if(j==0&&!pure)x=m.mean;
            else if(j==1&&!pure&&mode!="rc_no_poll"&&!simple&&archive[b].x.size()){
                x=encode(archive[b].x,b);int a=index(dim);x[a]+=(.005+.4*m.scale)*gaussian();}
            else if(j==2&&epoch%4==0&&!pure&&mode!="rc_no_refresh")x=fresh();
            else{V z(dim);for(double& a:z)a=gaussian();
                x=(j<=4&&!pure&&archive[b].x.size()?encode(archive[b].x,b):m.mean)+m.scale*A*z;}
            sample.push_back(eval(decode(x,b)));
        }
        if(int(sample.size())<mu)break;std::sort(sample.begin(),sample.end(),better);
        V next=V::Zero(dim);M rank=M::Zero(dim,dim);
        for(int j=0;j<mu;j++){V x=encode(sample[j].x,b);next+=weights[j]*x;V y=(x-m.mean)/m.scale;rank+=weights[j]*y*y.transpose();}
        V diff=(next-m.mean)/m.scale;m.ps=(1-cs)*m.ps+std::sqrt(cs*(2-cs)*me)*W*diff;
        bool h=m.ps.norm()/std::sqrt(1-std::pow(1-cs,2*m.updates))<(1.4+2/(d+1))*expected;
        m.pc=(1-cc)*m.pc+h*std::sqrt(cc*(2-cc)*me)*diff;
        m.C=(1-c1-cm+(!h)*c1*cc*(2-cc))*m.C+c1*m.pc*m.pc.transpose()+cm*rank;
        if(mode=="rc_diagonal"||simple)m.C=m.C.diagonal().asDiagonal().toDenseMatrix();
        m.scale=std::clamp(m.scale*std::exp(cs/damp*(m.ps.norm()/expected-1)),.006,.9);m.mean=next;
    }
}

