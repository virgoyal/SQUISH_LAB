function runCD2_final()

% 1. File‑system parameters

fileParams.topDir      = pwd;           % project root (current folder)
fileParams.imgDir      = 'result1';     % folder with piece_*.png
fileParams.imgReg      = 'piece_*.png'; % glob for images
fileParams.particleDir = 'output';      % centres from dialin
fileParams.contactDir  = 'contacts';    % where contact files go


% 2. Load particle_positions.txt produced by preseservePaticleID.m

particleFile = fullfile(fileParams.topDir,'particle_positions.txt');
if ~exist(particleFile,'file')
    error('particle_positions.txt not found – run preseservePaticleID.m first');
end
particles = readmatrix(particleFile);
fprintf('Loaded %d particle rows from particle_positions.txt\n',size(particles,1));

% 3. Smart edge cleaner: drop any particle that contactDetect cannot crop

CR = 10;          % *must* match cdParams.CR below
fprintf('Running edge cleaner (margin = radius + %d px) …\n',CR);

imgFiles = dir(fullfile(fileParams.topDir,fileParams.imgDir,fileParams.imgReg));
if isempty(imgFiles)
    error('No image files found in %s',fileParams.imgDir);
end

% Cache per‑image sizes [H W]
imgSize = zeros(numel(imgFiles),2);
for k = 1:numel(imgFiles)
    I = imread(fullfile(imgFiles(k).folder,imgFiles(k).name));
    imgSize(k,:) = size(I,[1 2]);     % [rows cols]
end

frames = particles(:,1);   % frame index assigned earlier
x      = particles(:,3);
y      = particles(:,4);
r      = particles(:,5);

keep = true(size(particles,1),1);
for i = 1:size(particles,1)
    f = frames(i);
    if f<1 || f>numel(imgFiles)
        warning('Frame %d outside image list – dropping particle',f);
        keep(i) = false; continue; end
    H = imgSize(f,1); W = imgSize(f,2);
    % replicate the exact inequalities in contactDetect (rounded) and add ±CR
    if  round(y(i)+r(i)) > H-1 || round(x(i)+r(i)) > W-1 || ...
        round(y(i)-r(i)) < 2   || round(x(i)-r(i)) < 2   || ...
        (y(i)+r(i)+CR)   > H   || (x(i)+r(i)+CR) > W     || ...
        (y(i)-r(i)-CR)   < 1   || (x(i)-r(i)-CR) < 1
        keep(i) = false;
    end
end

cleanedParticles = particles(keep,:);
fprintf('Edge cleaner: kept %d / %d particles (%.1f%%)\n',sum(keep),numel(keep),100*sum(keep)/numel(keep));

% Backup original and overwrite with cleaned list
backupFile = [particleFile '.backup_' datestr(now,'yyyymmdd_HHMMSS')];
copyfile(particleFile,backupFile);
writematrix(cleanedParticles,particleFile);
fprintf('Wrote cleaned particle list; backup saved to\n   %s\n',backupFile);


% 4. Parameters for contactDetect

cdParams = struct();
cdParams.metersperpixel       = 0.007/160;  % your calibration
cdParams.fsigma               = 140;        % PE stress coefficient
cdParams.g2cal                = 100;        % g²→force calibration
cdParams.dtol                 = 10;         % neighbour distance tol (px)
cdParams.contactG2Threshold   = 0.5;        % minimal g² in contact area
cdParams.CR                   = CR;         % *** keep equal to CR above ***
cdParams.imadjust_limits      = [0 0.65];   % contrast stretch for green ch.
cdParams.rednormal            = 2;          % red‑leak subtraction factor
cdParams.figverbose           = true;       % show figures & save JPGs


% 5. Launch contactDetect (unchanged)

fprintf('Calling contactDetect …\n');
try
    contactDetect(fileParams,cdParams,true);   % true = verbose wrapper
    fprintf('contactDetect finished successfully.\n');
catch ME
    fprintf(2,'contactDetect crashed: %s\n',ME.message);
    rethrow(ME);
end

end  % function runCD2_final

%MAKE SURE TO CHANGE THE EXTENSION OF THE .png s to . mat s before you run master

