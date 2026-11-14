function attribution_plot()
% Paired costs and the held-out scene-bootstrap interval from the audit.
root = fileparts(fileparts(mfilename('fullpath')));
stats = readtable(fullfile(root,'audit','comparisons.csv'),'TextType','string');
globalRow = stats(stats.split=="matched" & stats.method=="cma_matched",:);
regionalRow = stats(stats.split=="holdout" & stats.method=="cma_regions_adaptive",:);
assert(height(globalRow)==1 && height(regionalRow)==1);
values = [globalRow.parking globalRow.uav globalRow.arm globalRow.trailer];

fig = figure('Visible','off','Color','w','Units','inches','Position',[.5 .5 3.59 1.70]);
cleanup = onCleanup(@()close(fig)); %#ok<NASGU>
blue = [.02 .29 .51];
left = axes(fig,'Position',[.185 .28 .315 .50]);
right = axes(fig,'Position',[.648 .28 .315 .50]);
for ax = [left right]
    hold(ax,'on');
    set(ax,'FontName','Times New Roman','FontSize',7.2,'Box','off',...
        'TickDir','out','LineWidth',.55,'YColor',[.24 .24 .24]);
    xline(ax,0,':','Color',[.38 .38 .38],'LineWidth',.75);
    xlabel(ax,'Cost change (%)','FontSize',7.5);
end
set(left,'YLim',[.45 4.55],'YTick',1:4,'YTickLabel',{'Trailer','Arm','Flight','Parking'},...
    'XLim',[-33 4],'XTick',[-30 -15 0]);
for k=1:numel(values)
    y=5-k;
    plot(left,values(k),y,'o','Color',blue,'MarkerFaceColor',blue,'MarkerSize',3.5);
    if values(k)<-10, offset=1.8; align='left'; else, offset=-1.7; align='right'; end
    if k==1, label=sprintf('%+.4f',values(k)); else, label=sprintf('%+.2f',values(k)); end
    text(left,values(k)+offset,y,label,'FontName','Times New Roman','FontSize',7,...
        'HorizontalAlignment',align,'VerticalAlignment','middle');
end
set(right,'XLim',[-.125 .035],'XTick',[-.10 -.05 0],'YLim',[0 1],'YTick',[],'YColor','none');
lo=regionalRow.ci_low; hi=regionalRow.ci_high; mid=regionalRow.median;
plot(right,[lo hi],[.66 .66],'-','Color',blue,'LineWidth',1.25);
for endpoint=[lo hi]
    plot(right,[endpoint endpoint],[.60 .72],'-','Color',blue,'LineWidth',.9);
end
plot(right,mid,.66,'o','Color',blue,'MarkerFaceColor',blue,'MarkerSize',4);
text(right,mid,.85,sprintf('%+.3f%%',mid),'FontName','Times New Roman','FontSize',7.5,...
    'HorizontalAlignment','center','BackgroundColor','white','Margin',.1);
text(right,.5,.32,sprintf('95%% interval\n[%+.3f, %+.3f]%%',lo,hi),'Units','normalized',...
    'FontName','Times New Roman','FontSize',7,'HorizontalAlignment','center','BackgroundColor','white');
title(left,{'(a) Matched global CMA','Original cases'},'FontName','Times New Roman','FontSize',7.5,'FontWeight','normal');
title(right,{'(b) Adaptive regional CMA','Held-out cases'},'FontName','Times New Roman','FontSize',7.5,'FontWeight','normal');
annotation(fig,'rectangle',[.001 .001 .998 .998],'Color','white','LineWidth',.1);
exportgraphics(fig,fullfile(root,'figures','attribution.pdf'),'ContentType','vector','BackgroundColor','white');
end
