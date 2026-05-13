%INTERAACTIVE PARTICLE DETECT!! LOVE

imagePath = 'result1/piece_0_0.png';
img = imread(imagePath);
if size(img, 3) == 3
    grayImg = img(:,:,2);
    redImg = img(:,:,1);
else
    grayImg = img;
    redImg = img;
end

% Parameters                %0_0    0_1     1_0     1_1
radius_min = 105;           % 105   100
radius_max = 290;           % 290   290
sensitivity = 0.9724;       % 0.9724 0.975
edgeThreshold = 0.05;       % 0.05  0.04
min_center_distance = 200;  % 200   200
interactive_selection = true; 

% Find circles
[centers, radii] = imfindcircles(grayImg, [radius_min radius_max], ...
    'Sensitivity', sensitivity, 'EdgeThreshold', edgeThreshold, 'Method', 'PhaseCode');

% Filter out circles whose centers are too close together
if ~isempty(centers)
    
    originalCount = size(centers, 1);
    
    
    keepCircles = true(size(centers, 1), 1);
    
    
    global userChoice;
    
    % Compare each pair of circles
    i = 1;
    while i <= size(centers, 1)
        if keepCircles(i)  % Skip if already marked for removal
            j = i + 1;
            while j <= size(centers, 1)
                if keepCircles(j)  
                    
                    dist = norm(centers(i,:) - centers(j,:));
                    
                    
                    if dist < min_center_distance
                        if interactive_selection
                            
                            h = figure('Name', 'Select Circle to Keep');
                            imshow(img);
                            hold on;
                            
                            % Draw circle i in red
                            viscircles(centers(i,:), radii(i), 'EdgeColor', 'r', 'LineWidth', 2);
                            text(centers(i,1), centers(i,2), ['1: r=' num2str(radii(i),3)], ...
                                'Color', 'red', 'FontSize', 12, 'HorizontalAlignment', 'center');
                            
                            % Draw circle j in green
                            viscircles(centers(j,:), radii(j), 'EdgeColor', 'g', 'LineWidth', 2);
                            text(centers(j,1), centers(j,2), ['2: r=' num2str(radii(j),3)], ...
                                'Color', 'green', 'FontSize', 12, 'HorizontalAlignment', 'center');
                            
                           
                            title({['Overlapping Circles: Distance = ' num2str(dist,3) ...
                                ' (min = ' num2str(min_center_distance) ')'], ...
                                'RED = Circle 1, GREEN = Circle 2'});
                            
                            
                            userChoice = 0;
                            
                            % Create buttons for user selection
                            btnRed = uicontrol('Style', 'pushbutton', 'String', 'Keep RED (1)', ...
                                'Position', [50, 20, 100, 30], ...
                                'Callback', @(src,event) selectCircle(1));
                            
                            btnGreen = uicontrol('Style', 'pushbutton', 'String', 'Keep GREEN (2)', ...
                                'Position', [200, 20, 100, 30], ...
                                'Callback', @(src,event) selectCircle(2));
                            
                            btnBoth = uicontrol('Style', 'pushbutton', 'String', 'Keep BOTH', ...
                                'Position', [350, 20, 100, 30], ...
                                'Callback', @(src,event) selectCircle(3));
                            
                            
                            uiwait(h);
                            
                            
                            disp(['User chose: ', num2str(userChoice)]);
                            
                            switch userChoice
                                case 1 % Keep circle i (RED)
                                    disp('Keeping RED circle, removing GREEN circle');
                                    keepCircles(j) = false;
                                case 2 % Keep circle j (GREEN)
                                    disp('Keeping GREEN circle, removing RED circle');
                                    keepCircles(i) = false;
                                    i = i - 1; 
                                    break; 
                                case 3 % Keep both
                                    disp('Keeping BOTH circles');
                                    
                                otherwise % Default: keep the larger one
                                    disp('No selection made, keeping the larger circle');
                                    if radii(i) >= radii(j)
                                        keepCircles(j) = false;
                                    else
                                        keepCircles(i) = false;
                                        i = i - 1; 
                                        break; 
                                    end
                            end
                        else
                            %  keep the circle with larger radius
                            if radii(i) >= radii(j)
                                keepCircles(j) = false;
                            else
                                keepCircles(i) = false;
                                i = i - 1; 
                                break; 
                            end
                        end
                    end
                end
                j = j + 1;
            end
        end
        i = i + 1;
    end
    
    % Filter circles
    centers = centers(keepCircles, :);
    radii = radii(keepCircles);
    

    numRemoved = originalCount - size(centers, 1);
    if numRemoved > 0
        disp(['Removed ' num2str(numRemoved) ' overlapping circles.']);
    end
end

% Display original image
figure;
subplot(1, 2, 1);
imshow(img);
title('Original Image');

% Display result
subplot(1, 2, 2);
imshow(img);
title(['Detected: ' num2str(size(centers, 1)) ' circles']);

if ~isempty(centers)
    viscircles(centers, radii, 'EdgeColor', 'b');
    
   
    
    
    disp('Detected circles:');
    for i = 1:min(10, size(centers, 1)) 
        disp(['Circle ' num2str(i) ': Center (' num2str(centers(i,1)) ',' num2str(centers(i,2)) '), Radius: ' num2str(radii(i))]);
    end
    
    % Determine edge particles (using rectangle boundary like in particleDetect)
    dtol = 10; % distance tolerance for edge detection
    
    % Find boundary positions
    lpos = min(centers(:,1)-radii);
    rpos = max(centers(:,1)+radii);
    upos = max(centers(:,2)+radii);
    bpos = min(centers(:,2)-radii);
    
    % Determine which particles are at edges
    lwi = centers(:,1)-radii <= lpos+dtol;
    rwi = centers(:,1)+radii >= rpos-dtol;
    uwi = centers(:,2)+radii >= upos-dtol;
    bwi = centers(:,2)-radii <= bpos+dtol;
    

    edges = zeros(length(radii), 1);
    edges(rwi) = 1; % right
    edges(lwi) = -1; % left
    edges(uwi) = 2; % upper
    edges(bwi) = -2; % bottom
    
    % Create matrix with [x, y, radius, edge]
    particleData = [centers(:,1), centers(:,2), radii, edges];
    

    [~, fileName, ~] = fileparts(imagePath);
    

    outDir = 'output';
    if ~exist(outDir, 'dir')
        mkdir(outDir);
    end
    

    centersFileName = fullfile(outDir, [fileName, '_centers.txt']);
    writematrix(particleData, centersFileName, 'Delimiter', ',');
    disp(['Centers data saved to: ' centersFileName]);
    

    paramsFileName = fullfile(outDir, 'particleDetect_params.txt');
    
    
    params = struct();
    params.radiusRange = [radius_min radius_max];
    params.sensitivity = sensitivity;
    params.edgeThreshold = edgeThreshold;
    params.min_center_distance = min_center_distance;
    params.interactive_selection = interactive_selection;
    params.dtol = dtol;
    params.boundaryType = 'rectangle';
    params.time = datestr(now);
    params.imgDir = 'result1';
    
 
    fields = fieldnames(params);
    C = struct2cell(params);
    paramsData = [fields C];
    

    writecell(paramsData, paramsFileName, 'Delimiter', 'tab');
    disp(['Parameters saved to: ' paramsFileName]);
else
    text(size(img,2)/2-100, size(img,1)/2, 'No circles detected', ...
        'Color', 'red', 'FontSize', 14, 'BackgroundColor', 'black');
end


disp('Parameters used:');
disp(['Radius Range: [' num2str(radius_min) ', ' num2str(radius_max) ']']);
disp(['Sensitivity: ' num2str(sensitivity)]);
disp(['Edge Threshold: ' num2str(edgeThreshold)]);
disp(['Minimum Center Distance: ' num2str(min_center_distance)]);
disp(['Interactive Selection: ' num2str(interactive_selection)]);


function selectCircle(choice)
    global userChoice;
    userChoice = choice;
    disp(['Selected choice: ', num2str(choice)]);
    close(gcf);
end