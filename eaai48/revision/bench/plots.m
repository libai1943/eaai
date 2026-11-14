function plots()
R=fileparts(fileparts(mfilename('fullpath')));F=fullfile(R,'figures');
D=jsondecode(fileread(fullfile(F,'data.json')));
set(groot,'defaultAxesFontName','Times New Roman','defaultTextFontName','Times New Roman','defaultAxesFontSize',7);
blue=[.02 .29 .51];sand=[.72 .35 .16];gray=[.53 .58 .61];
for kinds={'parking','uav','arm','trailer'}
 kind=kinds{1};fig=figure('Visible','off','Color','w','Units','inches','Position',[0 0 7.3 9.45]);
 planar=any(strcmp(kind,{'parking','trailer'}));span=[];centers=zeros(12,2);
 if planar
  for j=1:12
    c=D(strcmp({D.name},sprintf('%s_%02d',kind,j)));p=c.scene;xy=[];
    if strcmp(kind,'parking'),xy=reshape(p.polygons,[],2);e=reshape(p.endpoints,3,[])';xy=[xy;e(:,1:2)];
    else,for b=p.rectangles',xy=[xy;corners(b(1:3)',-b(4)/2,b(4)/2,b(5)/2)];end,end
    for k=1:numel(c.tracks)
        t=pick(c.tracks,k);x=t.poses;
        for q=unique(round(linspace(1,size(x,1),100)))
            if strcmp(kind,'parking'),xy=[xy;corners(x(q,1:3),-.929,3.760,.971)];
            else,[A,B]=rig(x(q,:));xy=[xy;A;B];end
        end
    end
    centers(j,:)=(max(xy)+min(xy))/2;span(j)=max(max(xy)-min(xy));
  end
  fullSpan=ceil(max(span)*1.06);
 end
 for j=1:12
    col=mod(j-1,3);row=floor((j-1)/3);
    ax=axes(fig,'Units','inches','Position',[.48+2.40*col,7.43-2.21*row,1.86,1.86]);hold(ax,'on');box(ax,'on');
    c=D(strcmp({D.name},sprintf('%s_%02d',kind,j)));p=c.scene;
    if strcmp(kind,'parking')
      for k=1:size(p.polygons,1),poly(ax,squeeze(p.polygons(k,:,:)));end
    elseif strcmp(kind,'trailer')
      for b=p.rectangles',poly(ax,corners(b(1:3)',-b(4)/2,b(4)/2,b(5)/2));end
    else
      for b=p.obstacles',cube(ax,b,kind);end
    end
    for k=numel(c.tracks):-1:1
      t=pick(c.tracks,k);x=t.poses;main=strcmp(t.method,'adaptive');clr=sand;sty=':';
      if main,clr=blue;sty='-';end
      if planar
        if main&&strcmp(kind,'trailer')
          rev=t.speed(:)<-1e-7;z=x;z(rev,:)=nan;plot(ax,z(:,1),z(:,2),'-','Color',blue,'LineWidth',1.4);
          z=x;z(~rev,:)=nan;plot(ax,z(:,1),z(:,2),'--','Color',blue,'LineWidth',1.4);
        else,plot(ax,x(:,1),x(:,2),sty,'Color',clr,'LineWidth',1.35);end
        if main
          s=[0;cumsum(vecnorm(diff(x(:,1:2)),2,2))];[~,idx]=min(abs(s-linspace(0,s(end),8)),[],1);
          for n=2:7,drawbody(ax,x(idx(n),:),kind,'--',.80*gray,.60);end
          drawbody(ax,x(1,:),kind,'-',[.19 .22 .24],.82);drawbody(ax,x(end,:),kind,'-',blue,.96);
          if ~isempty(t.switches),plot(ax,t.switches(:,1),t.switches(:,2),'d','MarkerSize',3.3,'Color',blue);end
          plot(ax,x(1,1),x(1,2),'^','MarkerSize',3,'Color',[.12 .12 .12]);plot(ax,x(end,1),x(end,2),'s','MarkerSize',3,'Color',blue,'MarkerFaceColor',blue);
        end
      else
        plot3(ax,x(:,1),x(:,2),x(:,3),sty,'Color',clr,'LineWidth',1.2);
        if main
           plot3(ax,x(1,1),x(1,2),x(1,3),'^k','MarkerSize',3);plot3(ax,x(end,1),x(end,2),x(end,3),'s','MarkerSize',3,'Color',blue);
           if strcmp(kind,'arm'),for ii=unique(round(linspace(1,size(x,1),5))),q=[0 0 1;t.elbow(ii,:);x(ii,:)];plot3(ax,q(:,1),q(:,2),q(:,3),'--','Color',gray,'LineWidth',.55);end,end
        end
      end
    end
    if planar
       axis(ax,'equal');xlim(ax,centers(j,1)+[-.5 .5]*fullSpan);ylim(ax,centers(j,2)+[-.5 .5]*fullSpan);
    else
       if strcmp(kind,'uav'),xlim(ax,[-.5 15.8]);ylim(ax,[-3.4 3.4]);zlim(ax,[0 3.9]);
       else,xlim(ax,[-.12 1.78]);ylim(ax,[-1.6 1.6]);zlim(ax,[.2 2.75]);end
       pbaspect(ax,[1.25 1 .9]);view(ax,[24 23]);zlabel(ax,'z (m)');
    end
    if row==3,xlabel(ax,'x (m)');end
    if col==0,ylabel(ax,'y (m)');end
    title(ax,sprintf('%s%02d',upper(kind(1)),j),'FontWeight','normal');
 end
 keyAx=axes(fig,'Position',[.015 .003 .97 .050],'Visible','off'); hold(keyAx,'on');
 if strcmp(kind,'trailer')
    names={'Forward','Reverse','CMA-ES','Gear change'};
    h=[plot(keyAx,nan,nan,'-','Color',blue),plot(keyAx,nan,nan,'--','Color',blue),...
       plot(keyAx,nan,nan,':','Color',sand),plot(keyAx,nan,nan,'d','Color',blue,'MarkerSize',3)];
 else
    names={'RegionCovOpt','CMA-ES'};
    h=[plot(keyAx,nan,nan,'-','Color',blue),plot(keyAx,nan,nan,':','Color',sand)];
 end
 key=legend(keyAx,h,names,'Orientation','vertical','NumColumns',1,'Box','on',...
    'FontSize',6.3,'FontName','Times New Roman');
 key.ItemTokenSize=[13 6]; key.Units='inches'; pos=key.Position;
 key.Position=[6.98-pos(3) .03 pos(3) pos(4)];
 annotation(fig,'rectangle',[.001 .001 .998 .998],'Color','white','LineWidth',.1);
 exportgraphics(fig,fullfile(F,[kind '.pdf']),'ContentType','vector','BackgroundColor','white');
 rasterCommand=sprintf('pdftoppm -png -singlefile -r 190 "%s" "%s"',fullfile(F,[kind '.pdf']),fullfile(F,kind));
 [status,detail]=system(rasterCommand); if status~=0, error('%s',detail); end
 close(fig)
end
end
function v=pick(t,k)
if iscell(t),v=t{k};else,v=t(k);end
end
function poly(ax,x)
patch(ax,x(:,1),x(:,2),[.84 .85 .85],'EdgeColor',[.43 .45 .46],'LineWidth',.45);
end
function q=corners(p,lo,hi,w)
q=[lo -w;hi -w;hi w;lo w;lo -w]*[cos(p(3)) sin(p(3));-sin(p(3)) cos(p(3))]+p(1:2);
end
function [A,B]=rig(x)
a=x(1:2)-1.5*[cos(x(3)) sin(x(3))]-3*[cos(x(4)) sin(x(4))];
A=corners(x(1:3),-.25,1.8,.9);B=corners([a x(4)],-1.2,2.25,.95);
end
function drawbody(ax,x,kind,sty,clr,w)
if strcmp(kind,'parking'),q=corners(x(1:3),-.929,3.76,.971);plot(ax,q(:,1),q(:,2),sty,'Color',clr,'LineWidth',w);
else,[A,B]=rig(x);plot(ax,A(:,1),A(:,2),sty,'Color',clr,'LineWidth',w);plot(ax,B(:,1),B(:,2),sty,'Color',clr,'LineWidth',w);
 d=[cos(x(3)) sin(x(3))];e=[cos(x(4)) sin(x(4))];h=x(1:2)-1.5*d;link=[x(1:2)-.25*d;h;h-.75*e];plot(ax,link(:,1),link(:,2),sty,'Color',clr,'LineWidth',w);end
end
function cube(ax,b,kind)
if strcmp(kind,'uav'),b(2)=max(-3.3,b(2));b(5)=min(3.3,b(5));b(3)=max(0,b(3));b(6)=min(3.8,b(6));end
v=[b([1 2 3])';b([4 2 3])';b([4 5 3])';b([1 5 3])';b([1 2 6])';b([4 2 6])';b([4 5 6])';b([1 5 6])'];
patch(ax,'Vertices',v,'Faces',[1 2 3 4;5 6 7 8;1 2 6 5;2 3 7 6;3 4 8 7;4 1 5 8],'FaceColor',[.82 .83 .84],'FaceAlpha',.22,'EdgeColor',[.58 .60 .62],'LineWidth',.4);
end

