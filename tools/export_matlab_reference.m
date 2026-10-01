function export_matlab_reference(config_path)
% Execute original formulas and serialize actual graphics data for comparison.
config = jsondecode(fileread(config_path));
cd(config.root);
addpath(config.output);
app = A2RLReferenceApp;
cleanup = onCleanup(@() delete(app));
app.A2RL_UIFigure_.Visible = 'off';
app.A2RL_UIFigure_.Position = [50 50 1536 864];
[folder, name, ext] = fileparts(config.csv);
app.csv_data_filepath = [folder filesep];
app.csv_data_filename = [name ext];
app.read_data_file();
assert(app.is_valid_file_read);
app.init_index_value();
app.init_index_limit();
app.enable_components();
results = {};
fields = properties(app);
for c = 1:numel(config.cases)
    params = config.cases(c);
    app.current_index = params.index;
    app.Curr_Idx_Selector_.Value = params.index;
    app.Curr_Idx_Slider_.Value = params.index;
    app.Max_Cmd_Point_Selector_.Value = params.horizon;
    app.pit_show_flag = params.pit;
    app.plot_size = params.plot_size;
    app.Lap_Selector_.Value = app.lap_count(params.index) + 1;
    app.isFirstUpdate = true;
    app.Planning_isFirstUpdate = true;
    for t = 1:numel(config.tabs)
        tab = config.tabs{t};
        app.Tab_Group_.SelectedTab = app.(tab);
        app.tab_index = app.(tab).Title;
        sample = struct('tab', tab, 'params', params, 'error', '', ...
                        'axes', struct, 'info', struct);
        try
            feval(config.methods{t}, app);
            axes_names = config.axes.(tab);
            for a = 1:numel(axes_names)
                key = axes_names{a};
                ax = app.(key);
                items = flipud(ax.Children);
                series = {};
                for p = 1:numel(items)
                    item = items(p);
                    if ~isprop(item, 'XData') || ~isprop(item, 'YData')
                        continue;
                    end
                    entry = struct('x', item.XData, 'y', item.YData, 'type', item.Type);
                    names = {'Color','LineStyle','Marker','LineWidth','MarkerSize', ...
                             'DisplayName','UData','VData','AutoScaleFactor','ScaleFactor'};
                    for k = 1:numel(names)
                        if isprop(item, names{k})
                            entry.(names{k}) = item.(names{k});
                        end
                    end
                    series{end+1} = entry; %#ok<AGROW>
                end
                sample.axes.(key) = struct('series', {series}, 'xlim', ax.XLim, ...
                    'ylim', ax.YLim, 'title', ax.Title.String, ...
                    'xlabel', ax.XLabel.String, 'ylabel', ax.YLabel.String);
            end
            for k = 1:numel(fields)
                key = fields{k};
                if startsWith(key, 'Text_') && isprop(app.(key), 'Value')
                    sample.info.(key) = app.(key).Value;
                end
            end
            sample.info.Label_Time_stamp = app.Label_Time_stamp.Text;
            if strcmp(tab, 'Tab_Each_Lap')
                sample.info.Label_lap_time = app.Label_lap_time.Text;
            end
        catch err
            sample.error = getReport(err, 'extended', 'hyperlinks', 'off');
            fprintf('REFERENCE ERROR %s index=%d: %s\n', tab, params.index, err.message);
        end
        results{end+1} = sample; %#ok<AGROW>
        fprintf('REFERENCE %d/%d %s index=%d\n', c, numel(config.cases), tab, params.index);
    end
    save(fullfile(config.output, 'matlab_reference.mat'), 'results', '-v7');
end
app.current_index = config.cases(2).index;
app.Max_Cmd_Point_Selector_.Value = 30;
app.pit_show_flag = true;
app.isFirstUpdate = true;
app.Tab_Group_.SelectedTab = app.Tab_Main;
app.update_plot_main();
drawnow;
try
    exportapp(app.A2RL_UIFigure_, fullfile(config.output, 'matlab_main.png'));
catch err
    fprintf('SCREENSHOT: %s\n', err.message);
end
fprintf('A2RL_REFERENCE_COMPLETE: %d page snapshots\n', numel(results));
end
