% forceChainViewer.m

% Builds a GLOBAL force‑chain graph from *_contacts.mat files and lets you
% inspect whether two particles are connected across images.

% HOW TO USE:
%   1. Be in the project root that contains the /contacts folder.
%   2. Run   >> forceChainViewer
%       e.g.  [8 30]
%       Press Enter on a blank line to quit.



function forceChainViewer()
    %% Config
    topDir      = pwd;                 % run from project root
    contactsDir = fullfile(topDir,'contacts');
    files = dir(fullfile(contactsDir,'*.mat'));
    if isempty(files)
        error('No *_contacts.mat files found in %s. Run contactDetect first.',contactsDir);
    end

    %% Build edge list 
    fprintf('Building force‑chain graph from %d contact files...\n', numel(files));
    edges = [];        % [idA idB]
    ids   = [];        % collect all IDs

    for k = 1:numel(files)
        S = load(fullfile(files(k).folder, files(k).name), 'particle');
        P = S.particle;
        for n = 1:numel(P)
            idA   = P(n).id;
            if isempty(idA); continue; end
            nbrs  = P(n).neighbours;
            nbrs  = nbrs(~isnan(nbrs) & nbrs > 0);   % skip wall / NaN / negative
            if ~isempty(nbrs)
                edges = [edges; [repmat(idA, numel(nbrs),1) nbrs(:)]]; %#ok<AGROW>
            end
            ids = [ids; idA]; %#ok<AGROW>
        end
    end

    % make undirected unique edge list
    edges = sort(edges,2);
    edges = unique(edges,'rows');

    %% Construct graph 
    uniqueIDs = unique([ids; edges(:)]);
    nodeNames = strtrim(cellstr(num2str(uniqueIDs)));   % remove leading spaces

    % map ID -> index
    map = containers.Map(num2cell(uniqueIDs), num2cell(1:numel(uniqueIDs)));
    src = arrayfun(@(x) map(x), edges(:,1));
    dst = arrayfun(@(x) map(x), edges(:,2));

    G = graph(src, dst, [], nodeNames);
    fprintf('Graph has %d nodes and %d edges.\n', numnodes(G), numedges(G));

    %% Save 
    save('force_chain_graph.mat','G');
    assignin('base','G',G);   % make available to caller workspace
    fprintf('Saved graph to force_chain_graph.mat and exported variable G to workspace.\n');

    %% Viz
    figure('Name','Force‑chain connectivity','Color','w');
    comps = conncomp(G);
    plot(G,'MarkerSize',6,'NodeCData',comps,'EdgeAlpha',0.5,'NodeLabel',[]);
    colormap(lines(max(comps)));
    title('Force‑chain components across all images');
    axis equal off;

    %% Interactive query loop
    disp('Enter two particle IDs as a row vector like [8 30] to test connectivity.');
    disp('Press Enter on a blank line to quit.');
    while true
        idsIn = input('IDs: ');
        if isempty(idsIn)
            break;         % user pressed Enter
        end
        if numel(idsIn) ~= 2 || ~isnumeric(idsIn)
            disp(' Please enter exactly two numeric IDs, e.g. [13 1]');
            continue;
        end
        try
            [tf,pathIDs] = isConnected(G, idsIn(1), idsIn(2));
            if tf
                fprintf('✔ Connected. Shortest path: %s\n', mat2str(pathIDs));
            else
                fprintf('✘ Not connected.\n');
            end
        catch ME
            fprintf('Error: %s\n', ME.message);
        end
    end
end

%% ----------------------------------------------------------------------
function [tf, pathIDs] = isConnected(G, idA, idB)
%ISCONNECTED  True if a path exists between particle idA and idB.
%   [tf, pathIDs] = isConnected(G, 13, 8)

    nameA = strtrim(num2str(idA));
    nameB = strtrim(num2str(idB));

    allNames = strtrim(G.Nodes.Name);          % cell array cleaned
    if ~any(strcmp(allNames,nameA)) || ~any(strcmp(allNames,nameB))
        error('One or both IDs not present in the graph.');
    end

    idxA = find(strcmp(allNames,nameA),1);
    idxB = find(strcmp(allNames,nameB),1);

    [pathIdx, tf] = shortestpath(G, idxA, idxB);

    if tf
        % Convert char names back to numeric IDs safely
        pathIDs = cellfun(@str2double, allNames(pathIdx));
    else
        pathIDs = [];
    end
end
