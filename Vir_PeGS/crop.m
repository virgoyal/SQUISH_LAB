% Center crop a batch of images to a region close to 2169x2169 
% but preserving the original aspect ratio (9504:6336 ~ 1.5:1)

input_folder = 'jpegs'; % Folder with your images
output_folder = 'cropped_images'; % Folder to save cropped images

% Create output folder if it doesn't exist
if ~exist(output_folder, 'dir')
    mkdir(output_folder);
end

% Target center crop size (roughly)
target_size = 2169; % You want around 2169x2169

% Load all JPEG files
image_files = dir(fullfile(input_folder, '*.jpeg'));
if isempty(image_files)
    error('No JPEG images found in the input folder: %s', input_folder);
end

% Aspect ratio of original images
aspect_ratio = 9504 / 6336; % ≈ 1.5

% Adjust target dimensions to maintain original aspect ratio
% Let's find width and height that are close to target_size but preserve 1.5 ratio
if aspect_ratio >= 1
    crop_width = round(target_size * aspect_ratio);
    crop_height = target_size;
else
    crop_width = target_size;
    crop_height = round(target_size / aspect_ratio);
end

fprintf('Cropping to size: %d x %d (W x H)\n', crop_width, crop_height);

% Process each image
for i = 1:length(image_files)
    img_path = fullfile(input_folder, image_files(i).name);
    img = imread(img_path);

    [img_height, img_width, ~] = size(img);

    % Find center
    center_x = img_width / 2;
    center_y = img_height / 2;

    % Define cropping rectangle
    x1 = round(center_x - crop_width/2);
    y1 = round(center_y - crop_height/2);
    
    % Make sure the rectangle stays within bounds
    x1 = max(1, x1);
    y1 = max(1, y1);
    x2 = min(img_width, x1 + crop_width - 1);
    y2 = min(img_height, y1 + crop_height - 1);

    % Adjust width and height if needed
    crop_width_actual = x2 - x1 + 1;
    crop_height_actual = y2 - y1 + 1;

    % Crop the image
    cropped_img = imcrop(img, [x1, y1, crop_width_actual-1, crop_height_actual-1]);

    % Save the cropped image
    output_path = fullfile(output_folder, image_files(i).name);
    imwrite(cropped_img, output_path);

    fprintf('Processed %s\n', image_files(i).name);
    fprintf('Saved cropped image to: %s\n', output_path);

end

disp('Cropping complete!');
