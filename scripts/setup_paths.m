function setup_paths()
%SETUP_PATHS Add MATPOWER, MOST, and PGLib-OPF to the MATLAB path.
%
%   Run from any directory after bootstrap_deps.sh:
%       run('/absolute/path/to/mat-py/scripts/setup_paths.m')
%   or, if already in mat-py/scripts:
%       setup_paths

    here = fileparts(mfilename('fullpath'));
    root = fileparts(here);
    mp   = fullfile(root, 'matlab', 'matpower');
    most = fullfile(root, 'matlab', 'most');
    pglib = fullfile(root, 'matlab', 'pglib-opf');

    assert(exist(mp, 'dir') == 7, ...
        'MATPOWER not found at %s — run scripts/bootstrap_deps.sh', mp);

    % Prefer MATPOWER installer when available
    install_m = fullfile(mp, 'install_matpower.m');
    if exist(install_m, 'file')
        addpath(mp);
        % Non-interactive path add when possible; else user runs install_matpower
        if exist('install_matpower', 'file')
            try
                install_matpower(1, 0, 0);  % quiet-ish; depends on MATPOWER version
            catch
                addpath(genpath(fullfile(mp, 'lib')));
                addpath(fullfile(mp, 'data'));
            end
        end
    else
        addpath(genpath(fullfile(mp, 'lib')));
        addpath(fullfile(mp, 'data'));
    end

    if exist(most, 'dir') == 7
        addpath(fullfile(most, 'lib'));
        addpath(fullfile(most, 'examples'));
    else
        warning('MOST not found at %s', most);
    end

    if exist(pglib, 'dir') == 7
        addpath(pglib);
        api = fullfile(pglib, 'api');
        if exist(api, 'dir') == 7
            addpath(api);
        end
    else
        warning('PGLib-OPF not found at %s', pglib);
    end

    fprintf('setup_paths: mat-py root = %s\n', root);
end
