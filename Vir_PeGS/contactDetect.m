% updated for first release of PeGS2 by Carmen lee 29/9/2024
% update Lori S McCabe 08/2024 for PEGS 2.0 wrapper compatibility
% original version Carmen Lee modular and converted as basis for PEGS 2.0
% 
% #contactDetect.m
% 
% The main function of this module is to take the particles found in the previous steps and to see if they have contacts between either the other particles or the wall. It begins by calculating the global intensity gradient squared for each particle. It then finds neighbour particles within tolerance (dtol) and assigns a contact based on the local g2 value. After going through the possible neighbours, it then considers edge particles based on the edge assignment.
% 
% **I**: 
% N images that are located in topDir/imgDir/ path
% 
% 
% N files *_centers.txt from the particleDetect step that are located in topDir/particlesDir/ 
% centers.txt needs to be in the format of [x, y, r, edge], where x, y, r are values in pixels, edge is a flag to indicate if the particle is near an edge
% 
% **OR** particle\_positions.txt located in topDir from the particleTrack module, which needs to be in the format of [frame, particleid, x, y, r, edge], where x, y, r are values in pixels, edge is a flag to indicate if the particle is near an edge
% 
% **O**: *_contacts.mat which consists of a data structure called particle, saved in directory topDir/contactsDir/
% particle = {'id','x','y','r','rm','color','fsigma','z','forcescale','g2','forces', fitError,'betas','alphas','neighbours','contactG2s','forceImage', 'edge'}
% Which will be partially populated from this step and the disksolve module, 
% 
% Change from pegs 1. Include an edge flag that designates the direction of the edge. 
% For a rectangular box, edge = 0 means not at an edge, the ascii art shows an example. Can be modified based on the applicable geometry
% <pre>
%         2
%     _________
%    |        |
%  -1|        |1
%    |        |
%     _________
%       -2
% </pre>
%   
%   
% **Parameters**
% -`p.metersperpixel`: the conversion from pixels to meter m/pixel
% 
% -`p.fsigma`: the photoelastic stress coefficient
% 
% -`p.g2cal`: calibration from g2 to force (can be computed by joG2cal.m from PeGS 1.0)
% 
% -`p.dtol`: how far away can the outlines of 2 particles be to still be considered Neighbors (pixels)
% 
% -`p.contactG2Threshold`: the threshold that determines if the potential contact is valid, if the sum of g2 in local contact area is above this value it will be valid. Note that this is sensitive to CR and imadjust_limits settings.
% 
% -`p.CR`: contact radius over which contact gradient is calculated (larger = larger area considered)
% 
% -`p.imadjust_limits`: adjusts contrast in the green channel, decreasing the upper bound generally increases signal.
% 
% -`p.rednormal`: fractional amount to subtract the red channel from the green channel (Rimg/rednormal) because sometimes the red channel leaks into the force channel
% 
% -`p.figverbose`: do you want to see the figures as you go?
% 



function out = contactDetect(fileParams, cdParams, verbose)
%fileParams passed in from wrapper
%requires input/output directories, image names

%cdParams are parameters specific for contact detection
%this includes all thresholding limits (listed below)


%% directory business and importing files

if ~exist(fullfile(fileParams.topDir, fileParams.contactDir) , 'dir')
   mkdir(fullfile(fileParams.topDir, fileParams.contactDir))
end



files = dir(fullfile(fileParams.topDir, fileParams.imgDir,fileParams.imgReg)); %images
if exist(fullfile(fileParams.topDir, 'particle_positions.txt'), 'file')
    centersfile = readmatrix(fullfile(fileParams.topDir, 'particle_positions.txt')); %tracked
else
    centersfile = dir(fullfile(fileParams.topDir, fileParams.particleDir, '*_centers.txt')); %not tracked
end


cdParams = setupParams(cdParams)

%% setting up mask
mask = abs(-cdParams.CR:cdParams.CR);
mask = mask.^2 + mask.^2';
maskCR = double(sqrt(mask) <= cdParams.CR-1);



%% image manipulation
for imgnumb = 1:size(files,1)

    clear particle %reinitialize the particle structure

    %read in image
    Img = imread(fullfile(files(imgnumb).folder, files(imgnumb).name));
    Rimg = Img(:,:,1);
    Gimg = Img(:,:,2); %force image


    %adjust green image contrast by subtracting red channel and adjusting
    %contrast levels as set by imadjust_limits. This will need to be
    %tweaked for different lighting and transmission or reflection
    %photoelasticimetry
    
    Gimg = Gimg-Rimg./cdParams.rednormal;
    Gimg= im2double(Gimg);
   
    Gimg = Gimg.*(Gimg > 0);
    Gimg = imadjust(Gimg,cdParams.imadjust_limits);
   
    if cdParams.figverbose
        figure(1); %makes a lot of figures, override onto 1
        
        imshow(Gimg)
        title('Gimg')

    end
    

    


    %% initialize data structure
    if exist(fullfile(fileParams.topDir, 'particle_positions.txt'), 'file') 
        if isfield(fileParams, 'frameIdInd')
           frame = str2double(files(imgnumb).name(fileParams.frameIdInd:fileParams.frameIdInd+3));
        else
           frame = imgnumb;
        end
        pData = centersfile(centersfile(:,1)==frame,3:6);
        id = centersfile(centersfile(:,1) == frame, 2);
        
    else
        pData = readmatrix(fullfile(fileParams.topDir, fileParams.particleDir, centersfile(imgnumb).name));%,"NumHeaderLines", 1); %Read Position data from centers file
        id = 1:size(pData,1);
    end
   
    if ~isempty(pData)

        N = size(pData,1);

        particle(1:N) = struct('id',0,'x',0,'y',0,'r',0,'rm',0,'color','','fsigma',0,'z',0,'forcescale',0,'g2',0,'forces',[],'fitError', [],'betas',[],'alphas',[],'neighbours',[],'contactG2s',[],'forceImage',[],  'edge', 0);
        
        for n = 1:N %Bookkeeping from centers-tracked
            particle(n).id= id(n);
            particle(n).x = pData(n,1);
            particle(n).y = pData(n,2);
            particle(n).r = round(pData(n,3));
            particle(n).edge = pData(n, 4);
            particle(n).rm = particle(n).r*cdParams.metersperpixel;
            particle(n).fsigma = cdParams.fsigma;
        end

        if cdParams.figverbose
            viscircles([pData(:,1),pData(:,2)],pData(:,3));
            hold on;
        end

        for n=1:N %loop over particles

            %create a circular mask

            r = particle(n).r;
            if round(particle(n).y+r)<size(Gimg, 1)&&round(particle(n).x+r)<size(Gimg,2)&&round(particle(n).y-r)>1&&round(particle(n).x-r)>1 %double check to make sure the bounds are within the image

                mask = abs(-r:r);
                mask = mask.^2 + mask.^2';
                mask1 = (sqrt(mask) <= r);

                %This crops out a particlstructuree
                cropXstart = round(particle(n).x-r);
                cropXstop = round(particle(n).x-r)+ size(mask1,1)-1;
                cropYstart = round(particle(n).y-r);
                cropYstop = round(particle(n).y-r)+ size(mask1,2)-1;


                particleImg= Gimg(cropYstart:cropYstop, cropXstart:cropXstop).*mask1;
                particle(n).forceImage=particleImg; %save this so we can fit to this image later in diskSolve


                %create a circular mask with a radius that is one pixel smaller
                %for cropping out the relevant gradient

                mask2 = double(sqrt(mask) <= r-1);

                %Compute G^2 for each particle
                [gx,gy] = gradient(particleImg);
                g2 = (gx.^2 + gy.^2).*mask2;
                particle(n).g2 = sum(sum(g2));
                particle(n).forcescale = particle(n).g2/cdParams.g2cal; %saving some particle scale features
            else
                error('badimage!! Particles partially cut off')

            end
        end
        %% look at neighbours

        xmat = pData(:,1);
        ymat = pData(:,2);
        rmat = pData(:,3);

        rmats = rmat; %Saves our radius matrix for later

        dmat = pdist2([xmat,ymat],[xmat,ymat]); %Creates a distance matrix for particle center locations
        rmat = rmat + rmat'; %Makes a combination of radii for each particle

        friendmat = dmat < (rmat + cdParams.dtol) & dmat~=0; %Logical "friend" matrix

        friendmat = triu(friendmat); %Only examine the upper triangle portion (no repeats)
        [f1, f2] = find(friendmat == 1); %Creates an index of particles that are considered touching
        %%
        xpairs = [xmat(f1),xmat(f2)]; %set up an array of pairs of x, y and r for easy manipulation later
        ypairs = [ymat(f1),ymat(f2)];
        rpairs = [rmats(f1),rmats(f2)];

        %% loop over friends

        for l = 1:length(f1)

            x = xpairs(l,:);
            y = ypairs(l,:);
            r = rpairs(l,:);

                        
            if cdParams.figverbose
            plot(x, y, 'LineWidth', 2)
            title('neighbour candidates')
            end
            
            [contactG2p, contactIp] = contactspot(x,y,r, cdParams.CR, Gimg, maskCR);

            if(contactG2p(1) > cdParams.contactG2Threshold && contactG2p(2) > cdParams.contactG2Threshold)

                %this is a valid contact, remember it
                particle(f1(l)).z= particle(f1(l)).z +1; %increase coordination number
                particle(f1(l)).contactG2s(particle(f1(l)).z)=contactG2p(1); %remember the g2 value of the current contact area
                particle(f1(l)).contactIs(particle(f1(l)).z)=contactIp(1); %changes to color
                particle(f1(l)).color(particle(f1(l)).z)='r'; %changes to color
                particle(f1(l)).neighbours(particle(f1(l)).z) = particle(f2(l)).id; %particle m is now noted as a neigbour in the particle l datastructure
                particle(f1(l)).betas(particle(f1(l)).z) = atan2(y(2)-y(1),x(2)-x(1)); %the contact angle to particle m is now noted in the particle l datastructure
                particle(f2(l)).z= particle(f2(l)).z+1; %increase coordination number
                particle(f2(l)).contactG2s(particle(f2(l)).z)=contactG2p(2); %remember the g2 value of the current contact area
                particle(f2(l)).contactIs(particle(f2(l)).z)=contactIp(2);
                particle(f2(l)).color(particle(f2(l)).z)='r'; %changes to color
                particle(f2(l)).neighbours(particle(f2(l)).z) = particle(f1(l)).id; %particle m is now noted as a neigbour in the particle l datastructure
                particle(f2(l)).betas(particle(f2(l)).z) = atan2(y(1)-y(2),x(1)-x(2));


            end




        end
        %%

        %Check if any of the walls is a neighbour as well

        circs = [[particle.y]', [particle.x]', [particle.r]', [particle.edge]']; %Makes a circs matrix from old matrices

        
        for disk = 1:length(particle)
            if circs(disk,4) == 1
                contacts = 0;
            elseif circs(disk,4) == -1
                contacts = pi;
            elseif circs(disk,4) == 2
                contacts = pi/2;
            elseif circs(disk,4) == -2
                contacts = -pi/2;
            end
            if particle(disk).edge ~=0
                x = particle(disk).x;
                y = particle(disk).y;
                r = particle(disk).r;
                for c =1:length(contacts) %technically doesn't need to be a loop but we will keep it for alternate scenarios
                    [contactG2p, contactIp]= contactspotwall(x, y, r, cdParams.CR, contacts(c),Gimg, maskCR);
                    if(contactG2p > cdParams.contactG2Threshold)
                        particle(disk).z= particle(disk).z +1; %increase coordination number
                        particle(disk).contactG2s(particle(disk).z)=contactG2p;
                        particle(disk).contactIs(particle(disk).z)=contactIp;
                        particle(disk).neighbours(particle(disk).z) = -1; %the wall is now noted as a neigbour in the particle l datastructure
                        particle(disk).betas(particle(disk).z) = contacts(c); %the contact angle to the wall is now noted in the particle l datastructure
                        particle(disk).color(particle(disk).z)='g';
                        %     else
                    end
                end
            end
        end


    end




if cdParams.figverbose 
    h3 = figure(20);
    hAx1 = subplot(1,1,1,'Parent', h3);
    imshow(Gimg, 'Parent', hAx1);
    hold (hAx1, 'on');
    for n = 1:length(particle)
        particle(n).id;
        
        z = particle(n).z; %get particle coordination number
        if (z>0) %if the particle does have contacts
            for m = 1:z %for each contact
                %draw contact lines
                lineX(1)=particle(n).x;
                lineY(1)=particle(n).y;
                lineX(2) = lineX(1) + particle(n).r * cos(particle(n).betas(m));
                lineY(2) = lineY(1) + particle(n).r * sin(particle(n).betas(m));
                viscircles([lineX(1), lineY(1)], particle(n).r, 'color', 'blue');
                viscircles([lineX(1) + (particle(n).r-cdParams.CR) * cos(particle(n).betas(m)) lineY(1) + (particle(n).r-cdParams.CR) * sin(particle(n).betas(m))], cdParams.CR, 'color', 'white');
                plot(hAx1, lineX, lineY,particle(n).color(m),'LineWidth',2);
            end
        end
        text(hAx1, particle(n).x, particle(n).y, num2str(particle(n).id), 'Color', 'y')
    end
    drawnow;
    hold off;
    if verbose
    saveas(h3,fullfile(fileParams.topDir, fileParams.contactDir,['Contacts_' files(imgnumb).name(1:end-4)]),'jpg') %save fig(20) 
    end
end %PEGS wrapper verbose

if verbose
disp([num2str(sum([particle.z])), ' contacts detected'])
end

%save updated particle contact info
savename = strrep(files(imgnumb).name, fileParams.imgReg(2:end), '_contacts.mat');
save(fullfile(fileParams.topDir, fileParams.contactDir, savename),'particle')

end %loop imgnumb

%% save parameters 

fields = fieldnames(cdParams);
for i = 1:length(fields)
    fileParams.(fields{i}) = cdParams.(fields{i});
end


fileParams.time = datetime("now");
fields = fieldnames(fileParams);
C=struct2cell(fileParams);
cdParams = [fields C];

writecell(cdParams,fullfile(fileParams.topDir, fileParams.contactDir,'contactDetect_params.txt'),'Delimiter','tab')
if verbose 
        disp('done with contactDetect()');
end

out = true; %if function ran completely, return true to PEGS wrapper
end %function contact detect





%% other called functions used in the contact detect algorithm 
function contactG2 = gradientcalculator(imgchunk)
[gx,gy] = gradient(imgchunk);
g2 = (gx.^2 + gy.^2);
contactG2 = sum(sum(g2));

end

function [contactG2p, contactIp]=contactspot(x, y, r, CR, Gimgd, maskCR)
contactangle = [atan2(y(2)-y(1),x(2)-x(1)), atan2(y(1)-y(2), x(1)-x(2))];
contactXp = round(x + (r -  1 - CR).* cos(contactangle));
contactYp = round(y + (r - 1 - CR).* sin(contactangle));

contactImg = im2double(imcrop(Gimgd,[contactXp(1)-CR contactYp(1)-CR CR*2 CR*2]));
contactImg = contactImg.*maskCR;

contactG2p = [gradientcalculator(contactImg)];
contactIp = [sum(sum(contactImg))];

contactImg = im2double(imcrop(Gimgd,[contactXp(2)-CR contactYp(2)-CR CR*2 CR*2]));
contactImg = contactImg.*maskCR;
contactG2p(2,:)= gradientcalculator(contactImg);
contactIp(2,:) = sum(sum(contactImg));
%contactG2p = [G1 G2]
end

function [contactG2p, contactIp]=contactspotwall(x, y, r, CR, angle,Gimgd, maskCR)

contactX = round(x + (r -  1 - CR).* cos(angle));
contactY = round(y + (r -1- CR).* sin(angle));


contactImg = im2double(imcrop(Gimgd,[contactX-CR contactY-CR CR*2 CR*2]));
contactImg = contactImg.*maskCR;

contactG2p = gradientcalculator(contactImg);

contactIp = sum(sum(contactImg));

end

%% end of other functions block

function params = setupParams(params)
%% thresholding limits (setting defaults if none listed in wrapper)

if ~isfield(params,'metersperpixel') 
    params.metersperpixel = .007/160;
end

if ~isfield(params,'fsigma') %photoelastic stress coefficient
    params.fsigma = 140;
end

if ~isfield(params,'g2cal') %calibration Value for the g^2 method, can be computed by joG2cal.m (PEGS 1.0 version)
    params.g2cal = 100;
end

if ~isfield(params,'dtol') %how far away can the outlines of 2 particles be to still be considered Neighbors
    params.dtol = 10;
end

if ~isfield(params,'contactG2Threshold') %sum of g2 in a contact area larger than this determines a valid contact
    params.contactG2Threshold = 0.5; 
end

if ~isfield(params,'CR') %contact radius over which contact gradient is calculated
    params.CR = 10;
end

if ~isfield(params,'imadjust_limits') %adjust contrast in green channel
    params.imadjust_limits = [0,.65];
end

if ~isfield(params,'rednormal') %fractional amount to subtract the red channel from the green channel (Rimg/rednormal)
    params.rednormal = 2;
end


if ~isfield(params,'figverbose') %show all the figures as you go
    params.figverbose = true;
end
end



