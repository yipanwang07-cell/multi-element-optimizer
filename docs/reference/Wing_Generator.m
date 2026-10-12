%% Multi-Element Wing Generator

% Copyright (c) 2017, Nick Morse
% See license agreement

% To add an airfoil add add its name and coordinates to airfoildatabase.mat

% Airfoil coordinate files must be given in (x,y) coordinates and the
% coordinate points must start from the trailing edge, move forward to the
% leading edge, and continue back to the trailing edge

function varargout = Wing_Generator(varargin)
% WING_GENERATOR MATLAB code for Wing_Generator.fig
%      WING_GENERATOR, by itself, creates a new WING_GENERATOR or raises the existing
%      singleton*.
%
%      H = WING_GENERATOR returns the handle to a new WING_GENERATOR or the handle to
%      the existing singleton*.
%
%      WING_GENERATOR('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in WING_GENERATOR.M with the given input arguments.
%
%      WING_GENERATOR('Property','Value',...) creates a new WING_GENERATOR or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before Wing_Generator_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to Wing_Generator_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help Wing_Generator

% Last Modified by GUIDE v2.5 26-Jul-2022 09:18:17

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @Wing_Generator_OpeningFcn, ...
                   'gui_OutputFcn',  @Wing_Generator_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
    
    
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before Wing_Generator is made visible.
function Wing_Generator_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to Wing_Generator (see VARARGIN)

% Load airfoil database
load airfoildatabase.mat
handles.airfoil = airfoil;

% Set drop down menu items
set(handles.popupmenu1,'string',{airfoil(:).name})
set(handles.popupmenu2,'string',{airfoil(:).name})
set(handles.popupmenu3,'string',{airfoil(:).name})

% Choose default command line output for Wing_Generator
handles.output = hObject;

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes Wing_Generator wait for user response (see UIRESUME)
% uiwait(handles.figure1);


% --- Outputs from this function are returned to the command line.
function varargout = Wing_Generator_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;


% --- Executes on button press in generate.
function generate_Callback(hObject, eventdata, handles)
% hObject    handle to generate (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
generate(hObject, eventdata, handles)


function generate(hObject, eventdata, handles)

% Load airfoils
airfoil = handles.airfoil;

%% Retrieve User Inputs

index1= get(handles.popupmenu1,'Value');
index3= get(handles.popupmenu3,'Value');

base=str2double(get(handles.edit16,'String'));
if isnan(base) % No input
    msgbox({'ERROR: Enter box width'}, 'Error','error')
    error('Box width not specified')
end

height=str2double(get(handles.edit17,'String'));
if isnan(height) % No input
    msgbox({'ERROR: Enter box height'}, 'Error','error')
    error('Box height not specified')
end
hyp=sqrt(base^2+height^2); %corner-to-corner distance

chord1= str2double(get(handles.mechord,'String'));
if isnan(chord1) % No input
    msgbox({'ERROR: Enter main element chord'}, 'Error','error')
    error('Main element chord not specified')
end

AoA1= str2double(get(handles.meAoA,'String'));
if isnan(AoA1) % No input
    msgbox({'ERROR: Enter main element angle'}, 'Error','error')
    error('Main element angle not specified')
end

gap1x= str2double(get(handles.edit11,'String'));
if isnan(gap1x) % No input
    gap1x=0.02*hyp;
    %set(handles.edit11,'String',num2str(gap1x));
end
gap1y= str2double(get(handles.edit12,'String'));
if isnan(gap1y) % No input
    gap1y=0.02*hyp;
    %set(handles.edit12,'String',num2str(gap1y));
end

q=get(handles.radiobutton1,'Value'); % 1 flap or 2 flaps

if q==1 % 2 flaps
    index2= get(handles.popupmenu2,'Value');
    
    chord2= str2double(get(handles.f2chord,'String'));
    if isnan(chord2) % No input
        msgbox({'ERROR: Enter flap 2 chord'}, 'Error','error')
        error('Flap 2 chord not specified')
    end
    
    AoA2= str2double(get(handles.f2AoA,'String'));
    if isnan(AoA2) % No input
        msgbox({'ERROR: Enter flap 2 angle'}, 'Error','error')
        error('Flap 2 angle not specified')
    end
    
    gap2x= str2double(get(handles.edit14,'String'));
    if isnan(gap2x) % No input
        gap2x=0.02*hyp;
        %set(handles.edit14,'String',num2str(gap2x));
    end
    gap2y= str2double(get(handles.edit15,'String'));
    if isnan(gap2y) % No input
        gap2y=0.02*hyp;
        %set(handles.edit15,'String',num2str(gap2y));
    end
end


%% Main Element

% Use airfoil database to retrieve airfoil name/coordinates
filename1 = airfoil(index1).name;
Ain1 = airfoil(index1).coord;
handles.airfoil1 = filename1;

% Shift leading edge to origin
[M, ind]=min(Ain1(:,1));
Ain1(:,2)=Ain1(:,2)-Ain1(ind,2);
Ain1(:,1)=Ain1(:,1)-M;

% Calculate number of coordinates
lengthAin1=size(Ain1,1);

% Delete repeated x-coordinate point to allow for input into ANSYS
if Ain1(1)==Ain1(lengthAin1)
    Ain1=Ain1(1:lengthAin1-1, :);
    lengthAin1=lengthAin1-1;
end

% Add z-coordinates (zeros)
Ain1=[Ain1 zeros(1,lengthAin1)']';
handles.lengthAin1=lengthAin1;

% Rotate airfoil to x-axis
ang1=-asind(Ain1(2,1)/Ain1(1,1));
R1=[cosd(ang1), -sind(ang1), 0;
    sind(ang1), cosd(ang1), 0;
    0, 0, 1];
Ain1=R1*Ain1;

% Renormalize airfoil
Ain1=Ain1'/Ain1(1,1);

% Scale airfoil
Ain1=chord1*Ain1;
filename1=strcat(filename1, '_chord', num2str(chord1));

% Invert airfoil if necessary
mn1=min(Ain1);
mx1=max(Ain1);

if abs(mn1(2))<abs(mx1(2))
    Ain1(:,2)=-Ain1(:,2);
end

% Rotate airfoil
Ain1=Ain1';
R3=[cosd(AoA1), -sind(AoA1), 0;
    sind(AoA1), cosd(AoA1), 0;
    0, 0, 1];
Ain1=R3*Ain1;
handles.filename1=strcat(filename1, '_angle', num2str(AoA1));

Ain1=Ain1';

mn1=min(Ain1);

% Shift airfoil vertically so bottom is at y=0
Ain1(:,2)=Ain1(:,2)-mn1(2);
% Shift airfoil horizontally so front is at x=0
Ain1(:,1)=Ain1(:,1)-mn1(1);

%% Flap 2

if q==1 % 2 flaps
    % Use airfoil database to retrieve airfoil name/coordinates
    filename2 = airfoil(index2).name;
    Ain2 = airfoil(index2).coord;  
    handles.airfoil2 = filename2;
    
    % Shift leading edge to origin
    [M, ind]=min(Ain2(:,1));
    Ain2(:,2)=Ain2(:,2)-Ain2(ind,2);
    Ain1(:,1)=Ain1(:,1)-M;

    % Calculate number of coordinates
    lengthAin2=size(Ain2,1);
    
    % Delete repeated x-coordinate point to allow for input into ANSYS
    if Ain2(1)==Ain2(lengthAin2)
        Ain2=Ain2(1:lengthAin2-1, :);
        lengthAin2=lengthAin2-1;
    end

    % Add z-coordinates (zeros)
    Ain2=[Ain2 zeros(1,lengthAin2)']';

    handles.lengthAin2=lengthAin2;

    % Rotate airfoil to x-axis
    ang2=-asind(Ain2(2,1)/Ain2(1,1));
    R2=[cosd(ang2), -sind(ang2), 0;
        sind(ang2), cosd(ang2), 0;
        0, 0, 1];
    Ain2=R2*Ain2;

    % Renormalize airfoil
    Ain2=Ain2'/Ain2(1,1);

    % Scale airfoil
    Ain2=chord2*Ain2;
    filename2=strcat(filename2,'_chord', num2str(chord2));

    % Invert airfoil if necessary
    mn2=min(Ain2);
    mx2=max(Ain2);

    if abs(mn2(2))<abs(mx2(2))
        Ain2(:,2)=-Ain2(:,2);
    end

    % Rotate airfoil
    Ain2=Ain2';
    R3=[cosd(AoA2), -sind(AoA2), 0;
        sind(AoA2), cosd(AoA2), 0;
        0, 0, 1];
    Ain2=R3*Ain2;
    handles.filename2=strcat(filename2, '_angle', num2str(AoA2));

    Ain2=Ain2';
    mx2=max(Ain2);

    % Shift airfoil vertically so top is at top of box
    Ain2(:,2)=Ain2(:,2)+height-mx2(2);
    
    % Shift airfoil horizontally so back is at back of box
    Ain2(:,1)=Ain2(:,1)+base-mx2(1);

    mn2=min(Ain2);
end

%% Flap 1

% Use airfoil database to retrieve airfoil name/coordinates
filename3 = airfoil(index3).name;
Ain3 = airfoil(index3).coord;
handles.airfoil3 = filename3;

% Shift leading edge to origin
[M, ind]=min(Ain3(:,1));
Ain3(:,2)=Ain3(:,2)-Ain3(ind,2);
Ain1(:,1)=Ain1(:,1)-M;

% Calculate number of coordinates
lengthAin3=size(Ain3,1);

% Delete repeated x-coordinate point to allow for input into ANSYS
if Ain3(1)==Ain3(lengthAin3)
    Ain3=Ain3(1:lengthAin3-1, :);
    lengthAin3=lengthAin3-1;
end

% Add z-coordinates (zeros)
Ain3=[Ain3 zeros(1,lengthAin3)']';

handles.lengthAin3=lengthAin3;

% Rotate airfoil to x-axis
ang3=-asind(Ain3(2,1)/Ain3(1,1));
R3=[cosd(ang3), -sind(ang3), 0;
    sind(ang3), cosd(ang3), 0;
    0, 0, 1];
Ain3=R3*Ain3;
% Renormalize airfoil
Ain3=Ain3'/Ain3(1,1);

% Invert airfoil if necessary
mn3=min(Ain3);
mx3=max(Ain3);
if abs(mn3(2))<abs(mx3(2))
    Ain3(:,2)=-Ain3(:,2);
end

% Flap 1 bounding box
if q==1 % 2 flaps
    base1=(mn2(1)+gap2x)-(Ain1(1,1)-gap1x);
    height1=(mn2(2)-gap2y)-(Ain1(1,2)+gap1y);
else % 1 flap
    base1=base-(Ain1(1,1)-gap1x);
    height1=height-(Ain1(1,2)+gap1y);
end

% Need to fit flap 1 within bounding box
% (1) Find flap 1 angle

% Shift trailing edge of flap to origin
Ain3(:,1)=Ain3(:,1)-Ain3(1,1);
Ain3(:,2)=Ain3(:,2)-Ain3(1,2);

% Find angle using bisection method
n=1;%iteration count
Ntot=100; %max iterations
relerr=1; %initialize
tol=1e-6; %tolerance
a=0; %deg
b=90; %deg
cb=0; %initial angle (deg)

while relerr>tol
    c=(a+b)/2;
    
    % Rotate airfoil
    Ain3=Ain3';
    Rc=[cosd(c-cb), -sind(c-cb), 0;
        sind(c-cb), cosd(c-cb), 0;
        0, 0, 1];
    Ain3=Rc*Ain3;
    Ain3=Ain3';
    
    % Find minimum
    mn3=min(Ain3);
    
    % Scaling ratios
    xrat=base1/abs(mn3(1));
    yrat=height1/abs(mn3(2));
    
    cb=c; %old value of c
    
    if xrat<yrat
        a=c;
    else
        b=c;
    end
    
    relerr=abs(xrat-yrat);
    if n>=Ntot
        msgbox({'ERROR: Flap 1 could not be placed'}, 'Error','error')
        error('Flap 1 could not be placed')
    end
    
    n=n+1;
end

% (2) Scale airfoil
Ain3=xrat*Ain3;

% Find minimums
mn3=min(Ain3);

% Shift airfoil horizontally so front is at x=0
Ain3(:,1)=Ain3(:,1)-mn3(1);
% Shift airfoil vertically so bottom is at y=0
Ain3(:,2)=Ain3(:,2)-mn3(2);

% Shift airfoil horizontally into final position
Ain3(:,1)=Ain3(:,1)+Ain1(1,1)-gap1x;
% Shift airfoil vertically into final position
Ain3(:,2)=Ain3(:,2)+Ain1(1,2)+gap1y;

handles.filename3=strcat(filename3,'_', num2str(xrat),'_',num2str(c),'deg');


%% Plot

axes(handles.axes1)
cla
rectangle('Position', [0 0 base height], 'EdgeColor', 'k', 'LineWidth', 1)
hold on
if(license('test', 'curve_fitting_toolbox'))
    fnplt(cscvn(Ain1(:,1:2)'), 'b') % Main Element
    plot(Ain1(:,1),Ain1(:,2),'.b', 'MarkerSize', 13)

    fnplt(cscvn(Ain3(:,1:2)'), 'b') % Flap 1
    plot(Ain3(:,1),Ain3(:,2),'.b', 'MarkerSize', 13)

    if q==1 % 2 flaps
        fnplt(cscvn(Ain2(:,1:2)'), 'b') % Flap 2
        plot(Ain2(:,1),Ain2(:,2),'.b', 'MarkerSize', 13)
    end
else
    plot(Ain1(:,1),Ain1(:,2),'.-b', 'MarkerSize', 13)
    plot(Ain3(:,1),Ain3(:,2),'.-b', 'MarkerSize', 13)

    if q==1 % 2 flaps
        plot(Ain2(:,1),Ain2(:,2),'.-b', 'MarkerSize', 13)
    end
end

axis equal
frame=0.05*base;
xlim([0-frame base+frame])
ylim([0-frame height+frame])


%% Prepare data to save

handles.q=q;
handles.base=base;
handles.height=height;
handles.gap1x=gap1x;
handles.gap1y=gap1y;
handles.Ain1=Ain1;
handles.chord1=chord1;
handles.AoA1=AoA1;
handles.index1=index1;
if q==1 % 2 flaps
    handles.Ain2=Ain2;
    handles.gap2x=gap2x;
    handles.gap2y=gap2y;
    handles.chord2=chord2;
    handles.AoA2=AoA2;
    handles.index2=index2;
end
chord3=xrat;
AoA3=c;
handles.chord3=chord3;
handles.AoA3=AoA3;
handles.Ain3=Ain3;
handles.index3=index3;


guidata(hObject,handles)


% --- Executes on button press in save.
function save_Callback(hObject, eventdata, handles)
% hObject    handle to save (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

generate(hObject, eventdata, handles)
handles = guidata(hObject);


saven = get(handles.savename,'String');
type = get(handles.pushbutton3,'String');

if ~isempty(saven)
    saven=strcat(saven, '_');
end

q=handles.q;

saven=strcat(saven, 'box', num2str(handles.base), 'x', num2str(handles.height), '_');

filename1=strcat('ME_',handles.filename1, '_slot1_x', num2str(handles.gap1x), '_y', num2str(handles.gap1y), '_');
if q==1 % 2 flaps
    filename3=strcat('F1_',handles.filename3, '_slot2_x', num2str(handles.gap2x), '_y', num2str(handles.gap2y), '_');
    if strcmp(type, 'ANSYS') % ANSYS
        filename2=strcat('F2_',handles.filename2, '_ANSYS.txt');
        outfile=strcat(saven,filename1,filename3,filename2);
    else % Solidworks
        filename2=strcat('F2_',handles.filename2);
        outfile1=strcat(saven,filename1, 'SolidWorks.txt');
        outfile3=strcat(saven,filename3, 'SolidWorks.txt');
        outfile2=strcat(saven,filename2, '_SolidWorks.txt');
    end
else % 1 flap
    if strcmp(type, 'ANSYS') % ANSYS
        filename3=strcat('F1_',handles.filename3, '_ANSYS.txt');
        outfile=strcat(saven,filename1,filename3);
    else % Solidworks
        filename3=strcat('F1_',handles.filename3);
        outfile1=strcat(saven,filename1, 'SolidWorks.txt');
        outfile3=strcat(saven,filename3, '_SolidWorks.txt');
    end
end

if strcmp(type, 'ANSYS') % ANSYS
    % Add a group column and point list (numbered list)
    Ain1=[ones(1,handles.lengthAin1)' (1:handles.lengthAin1)' handles.Ain1];
    if q==1 % 2 flaps
        Ain2=[ones(1,handles.lengthAin2)'*3 (1:handles.lengthAin2)' handles.Ain2];
    end
    Ain3=[ones(1,handles.lengthAin3)'*2 (1:handles.lengthAin3)' handles.Ain3];

    % Write output file with #Group heading (for input into ANSYS)
    fileID=fopen(outfile,'w');
    fprintf(fileID, '%0s\n', '#Group 1');
    fprintf(fileID, '%0.0f %4.0f %12.8f %12.8f %12.8f\r\n', Ain1');
    fprintf(fileID, '%0s\n', '#Group 2');
    fprintf(fileID, '%0.0f %4.0f %12.8f %12.8f %12.8f\r\n', Ain3');
    if q==1 % 2 flaps
        fprintf(fileID, '%0s\n', '#Group 3');
        fprintf(fileID, '%0.0f %4.0f %12.8f %12.8f %12.8f\r\n', Ain2');
    end
    fclose(fileID);
    
else % SolidWorks
    % Write output file with #Group heading (for input into ANSYS)
    fileID=fopen(outfile1,'w');
    fprintf(fileID, '%12.8f %12.8f %12.8f\r\n', handles.Ain1');
    fclose(fileID);

    fileID=fopen(outfile3,'w');
    fprintf(fileID, '%12.8f %12.8f %12.8f\r\n', handles.Ain3');
    fclose(fileID);
    
    if q==1 % 2 flaps
        fileID=fopen(outfile2,'w');
        fprintf(fileID, '%12.8f %12.8f %12.8f\r\n', handles.Ain2');
        fclose(fileID);
    end
end

%% Text file with parameters

saventext = get(handles.savename,'String');
if ~isempty(saventext)
    saventextb=strcat(saventext, '_');
end
outfiletext = strcat(saventext, '_wing_parameters.txt');

fileIDtext=fopen(outfiletext, 'w');

fprintf(fileIDtext,'WING PARAMETER FILE\r\n');
fprintf(fileIDtext,'Produced by Multi-Element Wing Generator\r\n\r\n');

fprintf(fileIDtext,'Wing Summary:\r\n');
fprintf(fileIDtext, ['  Wing name: ',saventext,'\r\n']);
strdate = date;
fprintf(fileIDtext, ['  Created: ',strdate,'\r\n']);

fprintf(fileIDtext, '\r\nBox Size:\r\n');
fprintf(fileIDtext, '  Length: %g\r\n', handles.base);
fprintf(fileIDtext, '  Height: %g\r\n', handles.height);

fprintf(fileIDtext, '\r\nMain Element:\r\n');
fprintf(fileIDtext, ['  Airfoil: ', handles.airfoil1, '\r\n']);
fprintf(fileIDtext, '  Chord length: %g\r\n', handles.chord1);
fprintf(fileIDtext, '  Angle: %g deg\r\n', handles.AoA1);

fprintf(fileIDtext, '\r\nSlot Gap 1:\r\n');
fprintf(fileIDtext, '  Horizontal: %g\r\n', handles.gap1x);
fprintf(fileIDtext, '  Vertical: %g\r\n', handles.gap1y);

fprintf(fileIDtext, '\r\nFlap 1:\r\n');
fprintf(fileIDtext, ['  Airfoil: ', handles.airfoil3, '\r\n']);
fprintf(fileIDtext, '  Chord length: %g\r\n', handles.chord3);
fprintf(fileIDtext, '  Angle: %g deg\r\n', handles.AoA3);


if q==1 % 2 flaps
    fprintf(fileIDtext, '\r\nSlot Gap 2:\r\n');
    fprintf(fileIDtext, '  Horizontal: %g\r\n', handles.gap2x);
    fprintf(fileIDtext, '  Vertical: %g\r\n', handles.gap2y);

    fprintf(fileIDtext, '\r\nFlap 2:\r\n');
    fprintf(fileIDtext, ['  Airfoil: ', handles.airfoil2, '\r\n']);
    fprintf(fileIDtext, '  Chord length: %g\r\n', handles.chord2);
    fprintf(fileIDtext, '  Angle: %g deg\r\n', handles.AoA2);
end
fclose(fileIDtext);



%% Display messages
if strcmp(type, 'ANSYS') % ANSYS
    confirm=sprintf('File created: %s', outfile);
    disp(confirm)
    
    msgbox({'Parameter file created:' outfiletext '' 'ANSYS file created:' outfile}, 'Success')
    
else % SolidWorks
    disp('Files created:')
    disp(outfile1)
    disp(outfile3)
    if q==1 % 2 flaps
        disp(outfile2)  
        msgbox({'Parameter file created:' outfiletext '' 'SolidWorks files created:' outfile1 outfile3 outfile2}, 'Success')
    else % 1 flap
        msgbox({'Parameter file created:' outfiletext '' 'SolidWorks files created:' outfile1 outfile3}, 'Success')
    end
    
end

confirmtext=sprintf('Parameter file created: %s', outfiletext);
disp(confirmtext)


function savename_Callback(hObject, eventdata, handles)
% hObject    handle to savename (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of savename as text
%        str2double(get(hObject,'String')) returns contents of savename as a double


% --- Executes during object creation, after setting all properties.
function savename_CreateFcn(hObject, eventdata, handles)
% hObject    handle to savename (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function f2chord_Callback(hObject, eventdata, handles)
% hObject    handle to f2chord (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of f2chord as text
%        str2double(get(hObject,'String')) returns contents of f2chord as a double


% --- Executes during object creation, after setting all properties.
function f2chord_CreateFcn(hObject, eventdata, handles)
% hObject    handle to f2chord (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


function f2AoA_Callback(hObject, eventdata, handles)
% hObject    handle to f2AoA (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of f2AoA as text
%        str2double(get(hObject,'String')) returns contents of f2AoA as a double


% --- Executes during object creation, after setting all properties.
function f2AoA_CreateFcn(hObject, eventdata, handles)
% hObject    handle to f2AoA (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


function mechord_Callback(hObject, eventdata, handles)
% hObject    handle to mechord (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of mechord as text
%        str2double(get(hObject,'String')) returns contents of mechord as a double


% --- Executes during object creation, after setting all properties.
function mechord_CreateFcn(hObject, eventdata, handles)
% hObject    handle to mechord (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function meAoA_Callback(hObject, eventdata, handles)
% hObject    handle to meAoA (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of meAoA as text
%        str2double(get(hObject,'String')) returns contents of meAoA as a double


% --- Executes during object creation, after setting all properties.
function meAoA_CreateFcn(hObject, eventdata, handles)
% hObject    handle to meAoA (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function edit16_Callback(hObject, eventdata, handles)
% hObject    handle to edit16 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit16 as text
%        str2double(get(hObject,'String')) returns contents of edit16 as a double


% --- Executes during object creation, after setting all properties.
function edit16_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit16 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function edit17_Callback(hObject, eventdata, handles)
% hObject    handle to edit17 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit17 as text
%        str2double(get(hObject,'String')) returns contents of edit17 as a double


% --- Executes during object creation, after setting all properties.
function edit17_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit17 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function edit14_Callback(hObject, eventdata, handles)
% hObject    handle to edit14 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit14 as text
%        str2double(get(hObject,'String')) returns contents of edit14 as a double


% --- Executes during object creation, after setting all properties.
function edit14_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit14 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function edit15_Callback(hObject, eventdata, handles)
% hObject    handle to edit15 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit15 as text
%        str2double(get(hObject,'String')) returns contents of edit15 as a double


% --- Executes during object creation, after setting all properties.
function edit15_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit15 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function edit11_Callback(hObject, eventdata, handles)
% hObject    handle to edit11 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit11 as text
%        str2double(get(hObject,'String')) returns contents of edit11 as a double


% --- Executes during object creation, after setting all properties.
function edit11_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit11 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function edit12_Callback(hObject, eventdata, handles)
% hObject    handle to edit12 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit12 as text
%        str2double(get(hObject,'String')) returns contents of edit12 as a double


% --- Executes during object creation, after setting all properties.
function edit12_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit12 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in radiobutton1.
function radiobutton1_Callback(hObject, eventdata, handles)
% hObject    handle to radiobutton1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of radiobutton1


% --- Executes on selection change in popupmenu1.
function popupmenu1_Callback(hObject, eventdata, handles)
% hObject    handle to popupmenu1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns popupmenu1 contents as cell array
%        contents{get(hObject,'Value')} returns selected item from popupmenu1


% --- Executes during object creation, after setting all properties.
function popupmenu1_CreateFcn(hObject, eventdata, handles)
% hObject    handle to popupmenu1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

% --- Executes on selection change in popupmenu2.
function popupmenu2_Callback(hObject, eventdata, handles)
% hObject    handle to popupmenu2 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns popupmenu2 contents as cell array
%        contents{get(hObject,'Value')} returns selected item from popupmenu2


% --- Executes during object creation, after setting all properties.
function popupmenu2_CreateFcn(hObject, eventdata, handles)
% hObject    handle to popupmenu2 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on selection change in popupmenu3.
function popupmenu3_Callback(hObject, eventdata, handles)
% hObject    handle to popupmenu3 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns popupmenu3 contents as cell array
%        contents{get(hObject,'Value')} returns selected item from popupmenu3


% --- Executes during object creation, after setting all properties.
function popupmenu3_CreateFcn(hObject, eventdata, handles)
% hObject    handle to popupmenu3 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in pushbutton3.
function pushbutton3_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton3 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% this toggles pushbutton3 between 0 and 1 and its label between 'ANSYS'
% and 'SolidWorks'
type = get(handles.pushbutton3,'String');

if strcmp(type, 'ANSYS')
    set(handles.pushbutton3,'String','SolidWorks')
else
    set(handles.pushbutton3,'String','ANSYS')
end
