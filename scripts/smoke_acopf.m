function results = smoke_acopf()
%SMOKE_ACOPF Run a few AC-OPF cases and print objectives.
%
%   Requires MATLAB + MATPOWER (and optionally PGLib on path).
%   From mat-py/scripts:
%       setup_paths
%       smoke_acopf

    setup_paths;

    cases = { ...
        'case14', ...
        'pglib_opf_case14_ieee', ...
        'pglib_opf_case30_ieee' ...
    };

    results = struct('name', {}, 'success', {}, 'f', {}, 'et', {}, 'msg', {});

    for k = 1:numel(cases)
        name = cases{k};
        entry = struct('name', name, 'success', false, 'f', NaN, 'et', NaN, 'msg', '');
        try
            if exist(name, 'file') ~= 2 && exist([name '.m'], 'file') ~= 2
                entry.msg = 'case file not on path';
                results(k) = entry;
                fprintf('%-28s SKIP  (%s)\n', name, entry.msg);
                continue
            end
            t0 = tic;
            r = runopf(name, mpoption('verbose', 0, 'out.all', 0));
            entry.et = toc(t0);
            entry.success = isfield(r, 'success') && r.success;
            if isfield(r, 'f'), entry.f = r.f; end
            entry.msg = ternary(entry.success, 'ok', 'solver failed');
            fprintf('%-28s %s  f=%-12g  t=%.2fs\n', ...
                name, upper(string(entry.success)), entry.f, entry.et);
        catch ME
            entry.msg = ME.message;
            fprintf('%-28s ERR   %s\n', name, ME.message);
        end
        results(k) = entry;
    end
end

function out = ternary(cond, a, b)
    if cond, out = a; else, out = b; end
end
