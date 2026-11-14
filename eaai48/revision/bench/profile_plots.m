function profile_plots()
% Time is in seconds on every panel. Duplicate switch times preserve control jumps.
base = fileparts(fileparts(mfilename('fullpath')));
figures = fullfile(base, 'figures');
data = fullfile(figures, 'profiles');
pages = fullfile(base, 'tmp', 'profile_pages');
if ~isfolder(pages), mkdir(pages); end
idx = jsondecode(fileread(fullfile(data, 'index.json')));
names = regexprep({idx.source}, '_adaptive_.*', '');
draw_pair(data, idx, names, {'parking_02','trailer_04'}, fullfile(figures,'profile_ground.pdf'));
draw_pair(data, idx, names, {'uav_04','arm_04'}, fullfile(figures,'profile_spatial.pdf'));
for k = 1:2:numel(idx)
    draw_pair(data, idx, names, names(k:k+1), fullfile(pages,sprintf('profiles_%02d.pdf',(k+1)/2)));
end
end

function draw_pair(data, idx, names, selected, filename)
isVehicle = startsWith(selected{1},{'parking','trailer'});
heightInches = 4.50 + 1.65 * isVehicle;
fig = figure('Visible','off','Color','w','Units','inches','Position',[.3 .3 7.3 heightInches]);
finish = onCleanup(@()close(fig)); %#ok<NASGU>
palette = [.05 .28 .46; .76 .32 .13; .19 .46 .35];
styles = {'-','--','-.'};
for col = 1:2
    meta = idx(strcmp(names,selected{col})); family = meta.family;
    tableData = readtable(fullfile(data,[selected{col} '.csv']));
    [fields, labels, units, titles] = channel_groups(family);
    n = numel(fields); left = .115 + .495*(col-1); bottom = .080; top = .934;
    code = [upper(selected{col}(1)),selected{col}(end-1:end)];
    heading = sprintf('%s   |   %s',code,titles);
    annotation(fig,'textbox',[left-.045 .957 .439 .033],'String',heading,'FontName','Times New Roman',...
        'FontWeight','bold','FontSize',10,'HorizontalAlignment','center','EdgeColor','none');
    annotation(fig,'textbox',[left-.045 .920 .439 .032],'String',...
        sprintf('Seed %d     T = %.2f s     J = %.3f',meta.seed,meta.T,meta.cost),...
        'FontName','Times New Roman','FontSize',8,'HorizontalAlignment','center','EdgeColor','none');
    height = (top-bottom)/n;
    for r = 1:n
        rect = [left,bottom+(n-r)*height+.008,.365,height-.028];
        ax = axes(fig,'Position',rect,...
            'FontName','Times New Roman','FontSize',7.4,'Box','on','Layer','top');
        hold(ax,'on');
        lines = gobjects(1,numel(fields{r}));
        for j = 1:numel(fields{r})
            lines(j) = plot(ax,tableData.time,tableData.(fields{r}{j}),styles{j},'Color',palette(j,:),...
                'LineWidth',1.05);
        end
        xlim(ax,[0 meta.T]);
        for t = reshape(meta.switches,1,[])
            xline(ax,t,':','Color',[.43 .43 .43],'LineWidth',.70,'HandleVisibility','off');
        end
        values = tableData{:,fields{r}};
        lo = min(values(:)); hi = max(values(:));
        pad = max(.09*(hi-lo),1.e-3);
        ylim(ax,[lo-pad,hi+pad]);
        ylabel(ax,units{r},'FontSize',8);
        if r==n, xlabel(ax,'Time (s)','FontSize',8); else, ax.XTickLabel = {}; end
        if numel(lines) > 1
            loc = 'best';
            if strcmp(family,'uav') && r==1, loc = 'northwest'; end
            key = legend(ax,lines,labels{r},'Orientation','vertical','Location',loc,...
                'Box','on','FontSize',7,'NumColumns',1);
            key.ItemTokenSize = [12 7];
            key.Color = 'white'; key.EdgeColor = [.48 .48 .48];
            ax.Position = rect;
            if ~strcmp(loc,'northwest')
                place_legend(ax,key,tableData.time,values,meta.T);
            end
        end
        ax.Position = rect;
    end
end
annotation(fig,'rectangle',[.001 .001 .998 .998],'Color','white','LineWidth',.1);
exportgraphics(fig,filename,'ContentType','vector','BackgroundColor','white');
end

function place_legend(ax,key,t,values,T)
% Choose an in-panel box with minimal overlap with the curves, including held-control jumps.
key.Units='normalized'; d=key.Position; r=ax.Position;
w=d(3)/r(3); h=d(4)/r(4); margin=.018;
if w>=1-2*margin || h>=1-2*margin, return; end
x=t/T; y=(values-ax.YLim(1))/diff(ax.YLim);
score=inf; best=[margin,1-h-margin];
for bottom=linspace(1-h-margin,margin,7)
    for left=linspace(margin,1-w-margin,7)
        withinX = max(x(1:end-1),x(2:end))>=left & min(x(1:end-1),x(2:end))<=left+w;
        withinY = max(y(1:end-1,:),y(2:end,:))>=bottom & min(y(1:end-1,:),y(2:end,:))<=bottom+h;
        overlap=nnz(withinY & withinX);
        if overlap<score, score=overlap; best=[left,bottom]; end
        if score==0, break; end
    end
    if score==0, break; end
end
key.Position=[r(1)+best(1)*r(3),r(2)+best(2)*r(4),d(3),d(4)];
end

function [fields, labels, units, titleText] = channel_groups(family)
switch family
    case {'parking','trailer'}
        fields = {{'x','y'},{'theta','phi'},{'v'},{'a'},{'omega'}};
        labels = {{'x','y'},{'\theta','\phi'},{'v'},{'a'},{'\omega'}};
        if strcmp(family,'trailer')
            fields{2} = {'theta','psi','phi'}; labels{2} = {'\theta','\psi','\phi'};
            titleText = 'Articulated docking';
        else
            titleText = 'Car parking';
        end
        units = {'Position (m)','Angle (rad)','Speed (m/s)','Accel. (m/s^2)','Steer rate (rad/s)'};
    case 'uav'
        fields = {{'x','y','z'},{'vx','vy','vz'},{'ax','ay','az'}};
        labels = {{'x','y','z'},{'v_x','v_y','v_z'},{'a_x','a_y','a_z'}};
        units = {'Position (m)','Velocity (m/s)','Accel. (m/s^2)'}; titleText = 'Aerial flight';
    case 'arm'
        fields = {{'q1','q2','q3'},{'dq1','dq2','dq3'},{'ddq1','ddq2','ddq3'}};
        labels = {{'q_1','q_2','q_3'},{'dq_1/dt','dq_2/dt','dq_3/dt'},{'a_1','a_2','a_3'}};
        units = {'Joint angle (rad)','Joint rate (rad/s)','Joint accel. (rad/s^2)'}; titleText = 'Manipulator';
end
end
