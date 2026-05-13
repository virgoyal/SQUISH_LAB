% improvedParticleID.m
% Script to create consolidated particle_positions.txt with correct frame
% numbers LOOOVVVEE


% Path to the particle tracking results
trackingResultsFile = 'particle_tracking_results.mat';

% Check if tracking results exist
if ~exist(trackingResultsFile, 'file')
    error('Cannot find tracking results file: %s', trackingResultsFile);
end

% Load the tracking results
disp('Loading tracking results...');
trackingData = load(trackingResultsFile);

% Prepare new positions data with correct frame numbers
disp('Creating particle_positions.txt with proper frame numbers...');
positions_data = [];

% For each image
for i = 1:length(trackingData.results.image_data)
    imgResult = trackingData.results.image_data{i};
    
    % Skip if the image has no data
    if isempty(imgResult)
        disp(['  Skipping image ' num2str(i) ' - no data']);
        continue;
    end
    
    % Get frame, particle IDs, and centers for this image
    frame = i;  % Frame is just the image index
    particleIds = imgResult.particle_ids;
    centers = imgResult.local_centers;
    
    % For each particle in this image
    for j = 1:length(particleIds)
        % Get the particle data
        if size(centers, 1) >= j
            % Get coordinates and radius
            x = centers(j, 1);
            y = centers(j, 2);
            
            if size(centers, 2) >= 3
                r = centers(j, 3);
            else
                r = 20; % Default radius if not available
            end
            
            % Get edge flag if available, otherwise use 0
            if size(centers, 2) >= 4
                edge = centers(j, 4);
            else
                edge = 0;
            end
            
            % Get the global unique ID
            particleId = particleIds(j);
            
            % Add to positions data: [frame, particleId, x, y, r, edge]
            positions_data = [positions_data; frame, particleId, x, y, r, edge];
        end
    end
end

% Save the consolidated file
base_dir = '.'; % Adjust if needed
output_file = fullfile(base_dir, 'particle_positions.txt');

% Back up any existing file
if exist(output_file, 'file')
    backup_file = [output_file '.backup'];
    copyfile(output_file, backup_file);
    disp(['Backed up existing file to: ' backup_file]);
end

% Write the new file
writematrix(positions_data, output_file, 'Delimiter', ',');

% Display statistics
disp(['Created particle_positions.txt with ' num2str(size(positions_data, 1)) ' particles']);
disp('Frame distribution:');
for i = 1:max(positions_data(:,1))
    count = sum(positions_data(:,1) == i);
    disp(['  Frame ' num2str(i) ': ' num2str(count) ' particles']);
end

% Display a preview of the data
disp('Preview of the first few rows:');
disp('Format: [frame, particleId, x, y, r, edge]');
disp(array2table(positions_data(1:min(10, size(positions_data, 1)), :), ...
    'VariableNames', {'Frame', 'ParticleID', 'X', 'Y', 'Radius', 'Edge'}));

% Display usage instructions
disp('To use this file with contactDetect:');
disp('1. Make sure particle_positions.txt is in your topDir');
disp('2. Run runCD2.m with the updated frame assignments');

disp('Done! Now try running runCD2.m for contact detection.');