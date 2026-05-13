def set_zero_position(self):
        """Set the current position as the zero point (origin)"""
        if not self.connected:
            return
            
        try:

            self.gantry.GCommand('DP 0,0')
            

            self.status_var.set("Position zeroed - current position is now (0,0)")
            

            self.current_x = 0
            self.current_y = 0
            self.position_var.set("X: 0, Y: 0")
            
        except Exception as e:
            self.status_var.set(f"Zero position error: {e}")
"""
Integrated Gantry & Camera Control System

This script creates a graphical interface for controlling the gantry and camera with:
1. Manual positioning with arrow keys
2. Image grid configuration with overlap
3. Automatic image capture with snake pattern
4. Camera control integration with filter operation
5. Safety limits and confirmation checks
"""
import tkinter as tk
from tkinter import ttk, messagebox, IntVar, BooleanVar
import gclib
import time
import threading
import math
import serial
import os
from datetime import datetime

class IntegratedGantryCameraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Integrated Gantry & Camera Control")

    
        

        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')
        

        self.connected = False
        self.gantry = None
        self.ser = None
        self.camera_connected = False
        

        self.step_size = 5000  
        self.speed = 50000     

        self.current_x = 0
        self.current_y = 0
        

        self.start_x = None
        self.start_y = None
        self.x_dimension = 500000  
        self.y_dimension = 500000  
        self.overlap = 0.2         
        

        self.camera_width_px = 9504
        self.camera_height_px = 6336
        self.fov_width_mm = 268.29  # 10 9/16 inches in mm
        
        # Gantry calibration
        self.x_scale = 2500  # Encoder steps per mm (X)
        self.y_scale = 6250  # Encoder steps per mm (Y)
        
        # Safety limits (default values)
        self.x_limit = 1660768
        self.y_limit = 3084965
        
        # Imaging options
        self.auto_capture = BooleanVar(value=True)  
        
        # Imaging status
        self.is_imaging = False
        self.stop_imaging = False
        self.waiting_for_photo = False
        
        # Gantry connection parameters 
        self.gantry_port = tk.StringVar(value="COM4")
        self.gantry_baud = tk.StringVar(value="19200")
        
        # Camera connection parameters
        self.port_var = tk.StringVar(value="COM7")
        self.baud_var = tk.StringVar(value="115200")
        
        # Create Save directory
        self.setup_save_directory()
        
        # Create simplified status frame
        self.create_status_frame()
        
        # Set up keyboard bindings
        self.setup_keyboard_bindings()
        
        # Create notebook (tabs)
        self.create_notebook()

    def setup_save_directory(self):
        """Set up a directory for saving images"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_save_dir = os.path.join(current_dir, "captured_images")
        os.makedirs(self.base_save_dir, exist_ok=True)
        

        now = datetime.now()
        session_name = now.strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.base_save_dir, session_name)
        os.makedirs(self.session_dir, exist_ok=True)

    def create_status_frame(self):
        """Create the status frame with only connection status and position information"""
        # Status display
        status_frame = tk.Frame(self.root, bg='#f0f0f0')
        status_frame.pack(pady=5)
        
        tk.Label(status_frame, text="Gantry:", bg='#f0f0f0', font=('Arial', 12)).grid(row=0, column=0, padx=5)
        self.status_var = tk.StringVar()
        self.status_var.set("Disconnected")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                     bg='#ffcccb', width=25, font=('Arial', 12))
        self.status_label.grid(row=0, column=1, padx=5)
        
        tk.Label(status_frame, text="Camera:", bg='#f0f0f0', font=('Arial', 12)).grid(row=0, column=2, padx=5)
        self.camera_status_var = tk.StringVar()
        self.camera_status_var.set("Disconnected")
        self.camera_status_label = tk.Label(status_frame, textvariable=self.camera_status_var, 
                                          bg='#ffcccb', width=25, font=('Arial', 12))
        self.camera_status_label.grid(row=0, column=3, padx=5)
        
        # Position display
        position_frame = tk.Frame(self.root, bg='#f0f0f0')
        position_frame.pack(pady=5)
        
        tk.Label(position_frame, text="Current Position:", bg='#f0f0f0', font=('Arial', 12)).grid(row=0, column=0, padx=5)
        self.position_var = tk.StringVar()
        self.position_var.set("X: 0, Y: 0")
        self.position_label = tk.Label(position_frame, textvariable=self.position_var, 
                                      bg='white', width=25, font=('Arial', 12))
        self.position_label.grid(row=0, column=1, padx=5)
        

        self.set_start_button = tk.Button(position_frame, text="Set as Start Position", 
                                         command=self.set_start_position,
                                         bg='#FF9800', fg='white', width=15, height=1, state=tk.DISABLED)
        self.set_start_button.grid(row=0, column=2, padx=10)

    def create_notebook(self):
        """Create notebook with tabs for different functions"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        gantry_tab = ttk.Frame(self.notebook)
        self.notebook.add(gantry_tab, text='Gantry')
        
        imaging_tab = ttk.Frame(self.notebook)
        self.notebook.add(imaging_tab, text='Imaging Setup')
        
        camera_tab = ttk.Frame(self.notebook)
        self.notebook.add(camera_tab, text='Camera Control')
        
        safety_tab = ttk.Frame(self.notebook)
        self.notebook.add(safety_tab, text='Safety Settings')
        
        # Populate tabs
        self.create_gantry_tab(gantry_tab)
        self.create_imaging_tab(imaging_tab)
        self.create_camera_tab(camera_tab)
        self.create_safety_tab(safety_tab)

    def create_gantry_tab(self, parent):
        """Create gantry control tab"""
        # Create frames
        settings_frame = tk.LabelFrame(parent, text="Gantry Configuration", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        movement_frame = tk.LabelFrame(parent, text="Movement Controls", padx=10, pady=10)
        movement_frame.pack(fill="x", padx=10, pady=10)
        
        control_frame = tk.Frame(movement_frame)
        control_frame.pack(pady=10)
        
        position_control_frame = tk.Frame(movement_frame)
        position_control_frame.pack(pady=10)
        
        instructions_frame = tk.LabelFrame(parent, text="Instructions", padx=10, pady=10)
        instructions_frame.pack(fill="x", padx=10, pady=10)
        
        # Connection settings
        tk.Label(settings_frame, text="Serial Port:", width=15, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        port_entry = tk.Entry(settings_frame, textvariable=self.gantry_port, width=10)
        port_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.gantry_connect_button = tk.Button(settings_frame, text="Connect", command=self.connect_gantry,
                                        bg='#4CAF50', fg='white', width=15, height=1)
        self.gantry_connect_button.grid(row=0, column=2, padx=10, pady=5)
        
        tk.Label(settings_frame, text="Baud Rate:", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        baud_entry = tk.Entry(settings_frame, textvariable=self.gantry_baud, width=10)
        baud_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.gantry_disconnect_button = tk.Button(settings_frame, text="Disconnect", command=self.disconnect_gantry,
                                          bg='#f44336', fg='white', width=15, height=1, state=tk.DISABLED)
        self.gantry_disconnect_button.grid(row=1, column=2, padx=10, pady=5)
        

        self.apply_gantry_settings_button = tk.Button(settings_frame, text="Apply Settings", 
                                                    command=self.apply_gantry_settings,
                                                    bg='#2196F3', fg='white', width=15, height=1)
        self.apply_gantry_settings_button.grid(row=0, column=3, rowspan=2, padx=10, pady=5)

        tk.Label(movement_frame, text="Step Size:", font=('Arial', 12)).pack(anchor="w", padx=10, pady=(10,0))
        step_size_frame = tk.Frame(movement_frame)
        step_size_frame.pack(anchor="w", padx=10, pady=(0,10))
        
        self.step_size_var = tk.StringVar()
        self.step_size_var.set(str(self.step_size))
        step_size_entry = tk.Entry(step_size_frame, textvariable=self.step_size_var, width=10, font=('Arial', 12))
        step_size_entry.pack(side=tk.LEFT, padx=5)
        step_size_entry.bind('<Return>', self.update_step_size)
        
        update_step_button = tk.Button(step_size_frame, text="Update", command=self.update_step_size, 
                                    bg='#2196F3', fg='white', width=8, height=1)
        update_step_button.pack(side=tk.LEFT, padx=5)
        
        # Position control buttons
        zero_button = tk.Button(position_control_frame, text="Zero Position", width=12, height=2,
                               command=self.set_zero_position,
                               bg='#2196F3', fg='white')
        zero_button.pack(side=tk.LEFT, padx=10)
        
        # Return to Start Position button
        self.return_to_start_button = tk.Button(position_control_frame, text="Return to Start Position", width=18, height=2,
                                              command=self.return_to_start_position,
                                              bg='#FF9800', fg='white', state=tk.DISABLED)
        self.return_to_start_button.pack(side=tk.LEFT, padx=10)
        
        # Go Home button 
        home_button = tk.Button(control_frame, text="Home", width=5, height=2,
                               command=lambda: self.goto_home(None))
        home_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Control pad 
        up_button = tk.Button(control_frame, text="▲", width=5, height=2,
                             command=lambda: self.move_up(None))
        up_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Stop button
        stop_button = tk.Button(control_frame, text="STOP", width=5, height=2,
                               command=lambda: self.emergency_stop(None),
                               bg='red', fg='white')
        stop_button.grid(row=0, column=2, padx=5, pady=5)
        
        left_button = tk.Button(control_frame, text="◄", width=5, height=2,
                               command=lambda: self.move_left(None))
        left_button.grid(row=1, column=0, padx=5, pady=5)
        
        down_button = tk.Button(control_frame, text="▼", width=5, height=2,
                               command=lambda: self.move_down(None))
        down_button.grid(row=1, column=1, padx=5, pady=5)
        
        right_button = tk.Button(control_frame, text="►", width=5, height=2,
                                command=lambda: self.move_right(None))
        right_button.grid(row=1, column=2, padx=5, pady=5)
        

        instructions = """
        1. Use arrow keys to navigate to desired start position
        2. Click "Set as Start Position" to mark the current position as the start
        
        Emergency Stop = Esc
        """
        
        instr_label = tk.Label(instructions_frame, text=instructions, 
                              font=('Arial', 11), justify=tk.LEFT)
        instr_label.pack(pady=5, anchor='w')

    def create_camera_tab(self, parent):
        """Create camera control tab"""

        config_frame = tk.LabelFrame(parent, text="Camera Configuration", padx=10, pady=10)
        config_frame.pack(fill="x", padx=10, pady=10)
        
        control_frame = tk.LabelFrame(parent, text="Manual Camera Control", padx=10, pady=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # --- Configuration Frame ---
        # COM Port
        tk.Label(config_frame, text="Serial Port:", width=15, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        port_entry = tk.Entry(config_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.camera_connect_button = tk.Button(config_frame, text="Connect", command=self.connect_camera,
                                           bg='#4CAF50', fg='white', width=12, height=1)
        self.camera_connect_button.grid(row=0, column=2, padx=10, pady=5)
        
        # Baud Rate
        tk.Label(config_frame, text="Baud Rate:", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        baud_entry = tk.Entry(config_frame, textvariable=self.baud_var, width=10)
        baud_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.camera_disconnect_button = tk.Button(config_frame, text="Disconnect", command=self.disconnect_camera,
                                              bg='#f44336', fg='white', width=12, height=1, state=tk.DISABLED)
        self.camera_disconnect_button.grid(row=1, column=2, padx=10, pady=5)
        
        # Apply Settings Button
        apply_button = tk.Button(config_frame, text="Apply Settings", command=self.apply_camera_settings,
                                bg='#2196F3', fg='white', width=15, height=1)
        apply_button.grid(row=0, column=3, rowspan=2, padx=10, pady=5)
        

        # Take Photo Button
        self.take_photo_button = tk.Button(control_frame, text="Take Photo (No Filter)", 
                                         command=lambda: self.take_manual_photo(False),
                                         bg='#4CAF50', fg='white', width=20, height=2, state=tk.DISABLED)
        self.take_photo_button.grid(row=0, column=0, padx=10, pady=10)
        
        # Take Photo with Filter Button
        self.take_photo_filter_button = tk.Button(control_frame, text="Take Photo (With Filter)", 
                                                command=lambda: self.take_manual_photo(True),
                                                bg='#2196F3', fg='white', width=20, height=2, state=tk.DISABLED)
        self.take_photo_filter_button.grid(row=0, column=1, padx=10, pady=10)
        
        # Filter Control
        self.filter_frame = tk.Frame(control_frame)
        self.filter_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        
        # Filter On Button
        self.filter_on_button = tk.Button(self.filter_frame, text="Move Filter In", 
                                        command=lambda: self.control_filter(True),
                                        bg='#FFC107', fg='black', width=15, height=1, state=tk.DISABLED)
        self.filter_on_button.pack(side=tk.LEFT, padx=10)
        
        # Filter Off Button
        self.filter_off_button = tk.Button(self.filter_frame, text="Move Filter Out", 
                                         command=lambda: self.control_filter(False),
                                         bg='#FF9800', fg='black', width=15, height=1, state=tk.DISABLED)
        self.filter_off_button.pack(side=tk.LEFT, padx=10)
        
        # Take Both Photos Button
        self.take_both_button = tk.Button(control_frame, text="Take Both Photos (Normal + Filter)", 
                                        command=self.take_both_photos,
                                        bg='#673AB7', fg='white', width=30, height=2, state=tk.DISABLED)
        self.take_both_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        # Status Info
        self.camera_info_var = tk.StringVar(value="Camera not connected")
        camera_info_label = tk.Label(control_frame, textvariable=self.camera_info_var, 
                                   font=('Arial', 10), fg='#555555')
        camera_info_label.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def create_imaging_tab(self, parent):
        """Create imaging setup tab"""
        # Create frames
        param_frame = tk.LabelFrame(parent, text="Imaging Parameters", padx=10, pady=10)
        param_frame.pack(fill="x", padx=10, pady=10)
        
        start_frame = tk.LabelFrame(parent, text="Start Position", padx=10, pady=10)
        start_frame.pack(fill="x", padx=10, pady=10)
        
        camera_frame = tk.LabelFrame(parent, text="Camera Settings", padx=10, pady=10)
        camera_frame.pack(fill="x", padx=10, pady=10)
        
        capture_frame = tk.LabelFrame(parent, text="Capture Options", padx=10, pady=10)
        capture_frame.pack(fill="x", padx=10, pady=10)
        
        calc_frame = tk.LabelFrame(parent, text="Calculated Values", padx=10, pady=10)
        calc_frame.pack(fill="x", padx=10, pady=10)
        
        control_frame = tk.Frame(parent, padx=10, pady=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        

        # Overlap
        tk.Label(param_frame, text="Overlap (%):", width=15, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        self.overlap_var = tk.StringVar(value=str(self.overlap * 100))
        overlap_entry = tk.Entry(param_frame, textvariable=self.overlap_var, width=10)
        overlap_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # X Dimension (mm)
        tk.Label(param_frame, text="X Width (mm):", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        self.x_dim_var = tk.StringVar(value=str(self.x_dimension / self.x_scale))
        x_dim_entry = tk.Entry(param_frame, textvariable=self.x_dim_var, width=10)
        x_dim_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Y Dimension (mm)
        tk.Label(param_frame, text="Y Height (mm):", width=15, anchor='e').grid(row=2, column=0, padx=5, pady=5)
        self.y_dim_var = tk.StringVar(value=str(self.y_dimension / self.y_scale))
        y_dim_entry = tk.Entry(param_frame, textvariable=self.y_dim_var, width=10)
        y_dim_entry.grid(row=2, column=1, padx=5, pady=5)

        # Start X
        tk.Label(start_frame, text="Start X:", width=15, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        self.start_x_var = tk.StringVar(value="Not set")
        tk.Label(start_frame, textvariable=self.start_x_var, width=15, anchor='w').grid(row=0, column=1, padx=5, pady=5)
        
        # Start Y
        tk.Label(start_frame, text="Start Y:", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        self.start_y_var = tk.StringVar(value="Not set")
        tk.Label(start_frame, textvariable=self.start_y_var, width=15, anchor='w').grid(row=1, column=1, padx=5, pady=5)
        

        # Camera Resolution
        tk.Label(camera_frame, text="Resolution (px):", width=15, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        self.resolution_var = tk.StringVar(value=f"{self.camera_width_px} × {self.camera_height_px}")
        tk.Label(camera_frame, textvariable=self.resolution_var, width=20, anchor='w').grid(row=0, column=1, padx=5, pady=5)
        
        # FOV Width
        tk.Label(camera_frame, text="FOV Width (mm):", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        self.fov_width_var = tk.StringVar(value=str(self.fov_width_mm))
        fov_entry = tk.Entry(camera_frame, textvariable=self.fov_width_var, width=10)
        fov_entry.grid(row=1, column=1, padx=5, pady=5)
        

        # Auto vs Manual capture
        auto_capture_check = tk.Checkbutton(capture_frame, text="Automatic Capture (No user confirmation)",
                                           variable=self.auto_capture)
        auto_capture_check.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # Calculate Button
        calculate_button = tk.Button(calc_frame, text="Calculate Grid", command=self.calculate_grid)
        calculate_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        # Grid Size
        tk.Label(calc_frame, text="Grid Size:", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        self.grid_size_var = tk.StringVar(value="Not calculated")
        tk.Label(calc_frame, textvariable=self.grid_size_var, width=20, anchor='w').grid(row=1, column=1, padx=5, pady=5)
        
        # Step Size
        tk.Label(calc_frame, text="Step Size (mm):", width=15, anchor='e').grid(row=2, column=0, padx=5, pady=5)
        self.step_mm_var = tk.StringVar(value="Not calculated")
        tk.Label(calc_frame, textvariable=self.step_mm_var, width=20, anchor='w').grid(row=2, column=1, padx=5, pady=5)
        
        # Total Images
        tk.Label(calc_frame, text="Total Images:", width=15, anchor='e').grid(row=3, column=0, padx=5, pady=5)
        self.total_images_var = tk.StringVar(value="Not calculated")
        tk.Label(calc_frame, textvariable=self.total_images_var, width=20, anchor='w').grid(row=3, column=1, padx=5, pady=5)
        
 
        # Start Imaging Button
        self.start_imaging_button = tk.Button(control_frame, text="Start Imaging Sequence", 
                                             command=self.start_imaging_sequence,
                                             bg='#4CAF50', fg='white', width=20, height=2, state=tk.DISABLED)
        self.start_imaging_button.pack(side=tk.LEFT, padx=10)
        
        # Stop Imaging Button
        self.stop_imaging_button = tk.Button(control_frame, text="Stop Imaging", 
                                            command=self.stop_imaging_sequence,
                                            bg='#f44336', fg='white', width=15, height=2, state=tk.DISABLED)
        self.stop_imaging_button.pack(side=tk.LEFT, padx=10)

    def create_safety_tab(self, parent):
        """Create safety settings tab"""
        # Create frames
        limits_frame = tk.LabelFrame(parent, text="Safety Limits (Encoder Units)", padx=10, pady=10)
        limits_frame.pack(fill="x", padx=10, pady=10)

        # X Limit
        tk.Label(limits_frame, text="X Limit:", width=15, anchor='e').grid(row=0, column=0, padx=5, pady=5)
        self.x_limit_var = tk.StringVar(value=str(self.x_limit))
        self.x_limit_entry = tk.Entry(limits_frame, textvariable=self.x_limit_var, width=15, state=tk.DISABLED)
        self.x_limit_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Y Limit
        tk.Label(limits_frame, text="Y Limit:", width=15, anchor='e').grid(row=1, column=0, padx=5, pady=5)
        self.y_limit_var = tk.StringVar(value=str(self.y_limit))
        self.y_limit_entry = tk.Entry(limits_frame, textvariable=self.y_limit_var, width=15, state=tk.DISABLED)
        self.y_limit_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Override Checkbox
        self.override_var = BooleanVar(value=False)
        override_check = tk.Checkbutton(limits_frame, text="I promise I know what I am doing", 
                                      variable=self.override_var, command=self.toggle_limit_override)
        override_check.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        # Apply Limits Button
        self.apply_limits_button = tk.Button(limits_frame, text="Apply Safety Limits", 
                                           command=self.apply_safety_limits,
                                           bg='#FF5722', fg='white', width=15, height=1, state=tk.DISABLED)
        self.apply_limits_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10)
        
        # Warning Label
        warning_label = tk.Label(limits_frame, text="WARNING: Changing safety limits may cause damage to the gantry system.\n"
                                                  "Only override if you fully understand the consequences.",
                               font=('Arial', 11, 'bold'), fg='red')
        warning_label.grid(row=4, column=0, columnspan=2, padx=5, pady=10)
        
        # Current Limits Info
        limits_info = tk.Label(limits_frame, text=f"Default X Limit: 1660768\nDefault Y Limit: 3084965",
                             font=('Arial', 10), fg='#555555')
        limits_info.grid(row=5, column=0, columnspan=2, padx=5, pady=10, sticky='w')

    def setup_keyboard_bindings(self):
        """Set up keyboard shortcuts"""
        self.root.bind('<Up>', self.move_up)
        self.root.bind('<Down>', self.move_down)
        self.root.bind('<Left>', self.move_left)
        self.root.bind('<Right>', self.move_right)
        self.root.bind('<Home>', self.goto_home)
        self.root.bind('<Escape>', self.emergency_stop)
        
    def toggle_limit_override(self):
        """Enable/disable limit override"""
        if self.override_var.get():
            self.x_limit_entry.config(state=tk.NORMAL)
            self.y_limit_entry.config(state=tk.NORMAL)
            self.apply_limits_button.config(state=tk.NORMAL)
        else:
            self.x_limit_entry.config(state=tk.DISABLED)
            self.y_limit_entry.config(state=tk.DISABLED)
            self.apply_limits_button.config(state=tk.DISABLED)
            
    def apply_safety_limits(self):
        """Apply new safety limits"""
        try:
            new_x_limit = int(self.x_limit_var.get())
            new_y_limit = int(self.y_limit_var.get())
            
            if new_x_limit <= 0 or new_y_limit <= 0:
                messagebox.showerror("Invalid Limits", "Limits must be positive values")
                return

            if messagebox.askyesno("Confirm Safety Limits", 
                                  f"Are you sure you want to set the safety limits to:\nX: {new_x_limit}\nY: {new_y_limit}"):
                self.x_limit = new_x_limit
                self.y_limit = new_y_limit
                messagebox.showinfo("Limits Updated", "Safety limits have been updated")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for the limits")
    
    def update_step_size(self, event=None):
        """Update the step size for manual movement"""
        try:
            self.step_size = int(self.step_size_var.get())
            self.status_var.set(f"Step size updated: {self.step_size}")
        except ValueError:
            self.status_var.set("Invalid step size!")
            self.step_size_var.set(str(self.step_size))
    
    def connect_gantry(self):
        """Connect to the gantry"""
        if self.connected:
            return
            
        try:

            port = self.gantry_port.get()
            baud = self.gantry_baud.get()
            
            self.status_var.set(f"Connecting to {port} at {baud}...")
            self.root.update()
            
      
            threading.Thread(target=lambda: self._connect_thread(port, baud), daemon=True).start()
        except Exception as e:
            self.status_var.set(f"Connection error: {e}")
            
    def _connect_thread(self, port, baud):
        """Thread for connecting to gantry"""
        try:
            self.gantry = gclib.py()
            self.gantry.GOpen(f'-a {port} -b {baud}')
            self.gantry.GCommand('CN,-1')  # Set home position to bottom left
            
            self.connected = True
            

            self.root.after(0, self._update_ui_after_connect)
            

            threading.Thread(target=self._poll_position, daemon=True).start()
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.root.after(0, lambda: self.status_var.set(error_msg))
            
    def _update_ui_after_connect(self):
        """Update UI after successful gantry connection"""
        self.status_var.set("Connected")
        self.status_label.config(bg='#c8e6c9')
        self.set_start_button.config(state=tk.NORMAL)

        self.gantry_connect_button.config(state=tk.DISABLED)
        self.gantry_disconnect_button.config(state=tk.NORMAL)
        

        self.update_start_button_state()
            
    def _poll_position(self):
        """Continuously poll the gantry position"""
        while self.connected:
            try:
                pos = self.gantry.GCommand('RP')
                if pos and ',' in pos:
                    x, y = pos.split(',')
                    self.current_x = int(x.strip())
                    self.current_y = int(y.strip())
                    
             
                    self.root.after(0, lambda: self.position_var.set(f"X: {self.current_x}, Y: {self.current_y}"))
            except:
                pass
                
            time.sleep(0.2) 
            
    def disconnect_gantry(self):
        """Disconnect from the gantry"""
        if not self.connected:
            return
            
        try:
            self.status_var.set("Disconnecting...")
            self.root.update()
            

            self.gantry.GClose()
            self.gantry = None
            self.connected = False
            
            self.status_var.set("Disconnected")
            self.status_label.config(bg='#ffcccb')
            self.set_start_button.config(state=tk.DISABLED)
            self.start_imaging_button.config(state=tk.DISABLED)
            

            self.gantry_connect_button.config(state=tk.NORMAL)
            self.gantry_disconnect_button.config(state=tk.DISABLED)
            
        except Exception as e:
            self.status_var.set(f"Disconnect error: {e}")
            
    def apply_gantry_settings(self):
        """Apply gantry connection settings"""
        # If already connected, ask to disconnect first
        if self.connected:
            if messagebox.askyesno("Already Connected", 
                                 "Gantry is already connected. Disconnect to apply new settings?"):
                self.disconnect_gantry()
            else:
                return
                
        messagebox.showinfo("Settings Applied", 
                           f"Gantry settings updated:\nPort: {self.gantry_port.get()}\nBaud: {self.gantry_baud.get()}")
    
    def home_gantry(self):
        """Home the gantry"""
        if not self.connected:
            return
            
        try:
            self.status_var.set("Homing...")
            self.root.update()
            
  
            threading.Thread(target=self._home_thread, daemon=True).start()
        except Exception as e:
            self.status_var.set(f"Homing error: {e}")
            
    def _home_thread(self):
        """Thread for homing the gantry"""
        try:
            # IMPORTANT Set speed
            self.gantry.GCommand('SP 50000,100000')
            
            # Move a bit to avoid limit switches
            self.gantry.GCommand('PR 100000,200000;BG')
            self.gantry.GCommand('AM;HM;BG')  # Wait for motion to complete, then home
            
            # Wait for homing to complete
            is_done = False
            last_pos = ""
            while not is_done and self.connected:
                pos = self.gantry.GCommand('RP')
                if pos == last_pos:
                    is_done = True
                else:
                    time.sleep(0.25)
                    last_pos = pos
            
            # Set position to 0,0
            self.gantry.GCommand('AM;PT;DP 0,0')
            

            self.root.after(0, lambda: self.status_var.set("Homing complete"))
            
        except Exception as e:
            error_msg = f"Homing failed: {str(e)}"
            self.root.after(0, lambda: self.status_var.set(error_msg))
            
    def connect_camera(self):
        """Connect to the camera"""
        if self.camera_connected:
            return
        
        try:

            port = self.port_var.get()
            baud = int(self.baud_var.get())
            
            # Update status
            self.camera_status_var.set("Connecting...")
            self.root.update()
            

            threading.Thread(target=lambda: self._connect_camera_thread(port, baud), daemon=True).start()
            
        except Exception as e:
            self.camera_status_var.set(f"Error: {str(e)}")
            
    def _connect_camera_thread(self, port, baud):
        """Thread for connecting to camera"""
        try:
   
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # Allow time for connection to establish
            
            self.camera_connected = True
            
            # Update UI in main thread
            self.root.after(0, self._update_ui_after_camera_connect)
            
        except Exception as e:
            error_msg = f"Camera connection failed: {str(e)}"
            self.root.after(0, lambda: self.camera_status_var.set(error_msg))
            
    def _update_ui_after_camera_connect(self):
        """Update UI after successful camera connection"""
        self.camera_status_var.set("Connected")
        self.camera_status_label.config(bg='#c8e6c9')
        self.camera_connect_button.config(state=tk.DISABLED)
        self.camera_disconnect_button.config(state=tk.NORMAL)
        

        self.take_photo_button.config(state=tk.NORMAL)
        self.take_photo_filter_button.config(state=tk.NORMAL)
        self.filter_on_button.config(state=tk.NORMAL)
        self.filter_off_button.config(state=tk.NORMAL)
        self.take_both_button.config(state=tk.NORMAL)
        

        self.camera_info_var.set(f"Connected to {self.port_var.get()} at {self.baud_var.get()} baud")
        

        self.update_start_button_state()
        
    def disconnect_camera(self):
        """Disconnect from the camera"""
        if not self.camera_connected:
            return
            
        try:
            # Close connection
            if self.ser:
                self.ser.close()
                self.ser = None
                
            self.camera_connected = False
            

            self.camera_status_var.set("Disconnected")
            self.camera_status_label.config(bg='#ffcccb')
            self.camera_connect_button.config(state=tk.NORMAL)
            self.camera_disconnect_button.config(state=tk.DISABLED)
            

            self.take_photo_button.config(state=tk.DISABLED)
            self.take_photo_filter_button.config(state=tk.DISABLED)
            self.filter_on_button.config(state=tk.DISABLED)
            self.filter_off_button.config(state=tk.DISABLED)
            self.take_both_button.config(state=tk.DISABLED)
            
   
            self.camera_info_var.set("Camera not connected")
            

            self.update_start_button_state()
            
        except Exception as e:
            self.camera_status_var.set(f"Disconnect error: {e}")
            
    def apply_camera_settings(self):
        """Apply new camera settings and reconnect if already connected"""
        was_connected = self.camera_connected
        

        if was_connected:
            self.disconnect_camera()
            
 
        try:

            if was_connected:
                self.connect_camera()
                
            messagebox.showinfo("Settings Applied", "Camera settings have been updated")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid baud rate")
            
    def send_camera_command(self, cmd):
        """Send a command to the camera/filter controller"""
        if not self.camera_connected or not self.ser:
            self.camera_info_var.set("Camera not connected")
            return False
            
        try:

            self.ser.write((cmd + '\n').encode())
            time.sleep(0.5)
            

            if self.ser.in_waiting:
                response = self.ser.read(self.ser.in_waiting).decode().strip()
                self.camera_info_var.set(f"ESP32: {response}")
                
            return True
            
        except Exception as e:
            self.camera_info_var.set(f"Command error: {str(e)}")
            return False
            
    def take_manual_photo(self, with_filter=False):
        """Take a single photo, optionally with filter"""
        if not self.camera_connected:
            return
            
        try:

            manual_dir = os.path.join(self.session_dir, "manual")
            os.makedirs(manual_dir, exist_ok=True)

            if with_filter:
                self.control_filter(True)
                time.sleep(1) 
                

            success = self.send_camera_command("SHUTTER")
            
            if success:
                self.camera_info_var.set(f"Took photo {'with' if with_filter else 'without'} filter")
                
            # If with filter, move filter back out
            if with_filter:
                time.sleep(1)  # Wait after photo
                self.control_filter(False)
                
        except Exception as e:
            self.camera_info_var.set(f"Photo error: {str(e)}")
            
    def control_filter(self, filter_in=True):
        """Control filter position"""
        if not self.camera_connected:
            return
            
        cmd = "FILTER,ON" if filter_in else "FILTER,OFF"
        success = self.send_camera_command(cmd)
        
        if success:
            self.camera_info_var.set(f"Filter {'in position' if filter_in else 'moved away'}")
            
    def take_both_photos(self):
        """Take a pair of photos (with and without filter)"""
        if not self.camera_connected:
            return
            
        try:

            manual_dir = os.path.join(self.session_dir, "manual")
            os.makedirs(manual_dir, exist_ok=True)
            
            # Step 1: Take photo without filter
            success1 = self.send_camera_command("SHUTTER")
            time.sleep(1)
            
            # Step 2: Move filter in front
            success2 = self.send_camera_command("FILTER,ON")
            time.sleep(1)
            
            # Step 3: Take photo with filter
            success3 = self.send_camera_command("SHUTTER")
            time.sleep(1)
            
            # Step 4: Move filter away
            success4 = self.send_camera_command("FILTER,OFF")
            
            if success1 and success2 and success3 and success4:
                self.camera_info_var.set("Successfully captured both photos")
            else:
                self.camera_info_var.set("Error in capture sequence")
                
        except Exception as e:
            self.camera_info_var.set(f"Photo sequence error: {str(e)}")
            
    def move_gantry(self, x_change=0, y_change=0):
        """Move the gantry by the specified steps"""
        if not self.connected:
            return
            
        try:
            # Calculate new position
            new_x = self.current_x + x_change
            new_y = self.current_y + y_change
            
            # Check against safety limits
            if new_x > self.x_limit or new_y > self.y_limit:
                self.status_var.set("Movement blocked by safety limits")
                return
                
            # Send move command
            self.gantry.GCommand(f'PA {new_x}, {new_y};BG')
            self.status_var.set(f"Moving to X: {new_x}, Y: {new_y}")
            
        except Exception as e:
            self.status_var.set(f"Movement error: {e}")
    
    def move_up(self, event=None):
        """Move gantry up"""
        self.move_gantry(0, self.step_size)
        
    def move_down(self, event=None):
        """Move gantry down"""
        self.move_gantry(0, -self.step_size)
        
    def move_left(self, event=None):
        """Move gantry left"""
        self.move_gantry(-self.step_size, 0)
        
    def move_right(self, event=None):
        """Move gantry right"""
        self.move_gantry(self.step_size, 0)
        
    def goto_home(self, event=None):
        """Move gantry to home position"""
        if not self.connected:
            return
            
        try:
            self.gantry.GCommand('PA 0, 0;BG')
            self.status_var.set("Moving to home position")
        except Exception as e:
            self.status_var.set(f"Move to home error: {e}")
            
    def emergency_stop(self, event=None):
        """Emergency stop all motion"""
        if not self.connected:
            return
            
        try:
            self.gantry.GCommand('ST')  # Stop all motion
            self.status_var.set("EMERGENCY STOP")
            
            # If imaging, stop that too
            self.stop_imaging = True
        except Exception as e:
            self.status_var.set(f"Emergency stop error: {e}")
            
    def set_start_position(self):
        """Set current position as start position for imaging"""
        if not self.connected:
            return
            

        self.start_x = self.current_x
        self.start_y = self.current_y
        

        self.start_x_var.set(str(self.start_x))
        self.start_y_var.set(str(self.start_y))
        

        self.update_start_button_state()
        

        self.return_to_start_button.config(state=tk.NORMAL)
        
        self.status_var.set(f"Start position set: X={self.start_x}, Y={self.start_y}")

    def return_to_start_position(self):
        """Return to the previously set start position"""
        if not self.connected or self.start_x is None or self.start_y is None:
            return
            
        try:
            self.status_var.set(f"Returning to start position: X={self.start_x}, Y={self.start_y}")
            

            self.gantry.GCommand(f'PA {self.start_x}, {self.start_y};BG')
            

        except Exception as e:
            self.status_var.set(f"Return to start error: {e}")
            
    def calculate_grid(self):
        """Calculate imaging grid based on parameters"""
        try:
  
            self.overlap = float(self.overlap_var.get()) / 100  # Convert from percentage
            x_dimension_mm = float(self.x_dim_var.get())
            y_dimension_mm = float(self.y_dim_var.get())
            self.fov_width_mm = float(self.fov_width_var.get())
            
            # Convert to encoder steps
            self.x_dimension = int(x_dimension_mm * self.x_scale)
            self.y_dimension = int(y_dimension_mm * self.y_scale)
            
            # Check against safety limits
            if self.start_x is not None and self.start_y is not None:
                end_x = self.start_x + self.x_dimension
                end_y = self.start_y + self.y_dimension
                
                if end_x > self.x_limit or end_y > self.y_limit:
                    messagebox.showwarning("Safety Warning", 
                                         "The imaging area extends beyond safety limits.\n"
                                         "Please reduce dimensions or change start position.")
            
            # Calculate aspect ratio
            aspect_ratio = self.camera_height_px / self.camera_width_px
            fov_height_mm = self.fov_width_mm * aspect_ratio
            
            # Calculate step sizes
            x_step_mm = self.fov_width_mm * (1 - self.overlap)
            y_step_mm = fov_height_mm * (1 - self.overlap)
            
            # Calculate number of steps
            x_steps = math.ceil(x_dimension_mm / x_step_mm) + 1
            y_steps = math.ceil(y_dimension_mm / y_step_mm) + 1
            
            # Calculate encoder step size
            x_inc = int(x_step_mm * self.x_scale)
            y_inc = int(y_step_mm * self.y_scale)
            

            self.x_inc = x_inc
            self.y_inc = y_inc
            self.x_steps = x_steps
            self.y_steps = y_steps
            

            self.grid_size_var.set(f"{x_steps} × {y_steps}")
            self.step_mm_var.set(f"{x_step_mm:.2f} × {y_step_mm:.2f}")
            self.total_images_var.set(str(x_steps * y_steps))
            
            # Enable start imaging button if start position is set
            self.update_start_button_state()
            
            self.status_var.set("Grid calculation complete")
            
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numbers for all fields")
            
    def update_start_button_state(self):
        """Update the state of the start imaging button"""
        if self.start_x is not None and self.start_y is not None and hasattr(self, 'x_steps'):
            # Only enable if camera is connected
            if self.camera_connected and self.connected:
                self.start_imaging_button.config(state=tk.NORMAL)
            else:
                self.start_imaging_button.config(state=tk.DISABLED)
        
    def start_imaging_sequence(self):
        """Start the automated imaging sequence"""
        if not self.connected or self.is_imaging or not self.camera_connected:
            return
            
        if self.start_x is None or self.start_y is None:
            messagebox.showerror("Error", "Start position not set")
            return
            
        if not hasattr(self, 'x_steps') or not hasattr(self, 'y_steps'):
            messagebox.showerror("Error", "Grid not calculated")
            return
            
        # Confirm starting the sequence
        if not messagebox.askyesno("Confirm", 
                                 f"Start imaging sequence?\n\n{self.x_steps}×{self.y_steps} grid\n"
                                 f"Total images: {self.x_steps * self.y_steps}\n"
                                 f"Mode: {'Automatic' if self.auto_capture.get() else 'Manual'} capture"):
            return
            

        run_dir = os.path.join(self.session_dir, f"sequence_{len(os.listdir(self.session_dir))}")
        os.makedirs(run_dir, exist_ok=True)
        self.current_run_dir = run_dir
            

        self.stop_imaging = False
        self.is_imaging = True
        

        self.start_imaging_button.config(state=tk.DISABLED)
        self.stop_imaging_button.config(state=tk.NORMAL)
        

        threading.Thread(target=self._imaging_thread, daemon=True).start()
    
    def _show_photo_prompt(self, image_number, position):
        """Shows a photo prompt dialog and handles the response"""

        dialog = tk.Toplevel(self.root)
        dialog.title("Take Photo")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()  
        

        tk.Label(dialog, text=f"Position {position}", font=('Arial', 14)).pack(pady=5)
        tk.Label(dialog, text=f"Take photos #{image_number} (normal & filtered)", font=('Arial', 12)).pack(pady=5)
        tk.Label(dialog, text="Press Continue when done", font=('Arial', 10)).pack(pady=5)
        
        # Add buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_take_photos():
            self.take_both_photos()
            time.sleep(3)  # Give time for photos to complete
            
        def on_continue():
            self.waiting_for_photo = False
            dialog.destroy()
            
        tk.Button(button_frame, text="Take Photos", command=on_take_photos, 
                 bg='#4CAF50', fg='white', width=12, height=2).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Continue", command=on_continue, 
                 bg='#2196F3', fg='white', width=12, height=2).pack(side=tk.LEFT, padx=10)
            
    def _imaging_thread(self):
        """Thread for automated imaging sequence"""
        try:
            self.status_var.set("Moving to start position...")
            
            # Make sure filter is moved out before starting the sequence
            if self.camera_connected:
                self.control_filter(False)  # Move filter out
                time.sleep(0.5)  # Give it time to move
                
            # Move to start position
            self.gantry.GCommand(f'PA {self.start_x}, {self.start_y};BG')
            
            # Wait for move to complete
            is_done = False
            while not is_done and not self.stop_imaging:
                pos = self.gantry.GCommand('RP')
                if pos == f'{self.start_x}, {self.start_y}':
                    is_done = True
                else:
                    time.sleep(0.25)
        
        
            
            if self.stop_imaging:
                self.root.after(0, lambda: self.status_var.set("Imaging sequence stopped"))
                self.is_imaging = False
                self.root.after(0, lambda: self.start_imaging_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_imaging_button.config(state=tk.DISABLED))
                return
                

            self.root.after(0, lambda: self.status_var.set("Imaging sequence started"))
            
            image_count = 0
            
            for y in range(self.y_steps):
                # Set initial position for this row
                if y == 0:
                    aim_x = self.start_x
                    aim_y = self.start_y
                else:
                    aim_y += self.y_inc
                
                # Move across the row
                for x in range(self.x_steps):
                    if x != 0:
                        # Alternate direction based on row number
                        if y % 2 == 0:  # Even rows move right
                            aim_x += self.x_inc
                        else:  # Odd rows move left
                            aim_x -= self.x_inc
                
                    if self.stop_imaging:
                        break
                    
                    # Check against safety limits
                    if aim_x > self.x_limit or aim_y > self.y_limit:
                        error_msg = f"Position {x},{y} exceeds safety limits - stopping sequence"
                        self.root.after(0, lambda msg=error_msg: self.status_var.set(msg))
                        self.stop_imaging = True
                        break
                        
          
                    self.gantry.GCommand(f'PA {aim_x}, {aim_y};BG')
                    

                    pos_info = f"Moving to position {x},{y}"
                    self.root.after(0, lambda info=pos_info: self.status_var.set(info))
                    

                    is_done = False
                    while not is_done and not self.stop_imaging:
                        pos = self.gantry.GCommand('RP')
                        if pos == f'{aim_x}, {aim_y}':
                            is_done = True
                        else:
                            time.sleep(0.25)
                    
                    if self.stop_imaging:
                        break
                        

                    image_count += 1
                    

                    status_info = f"Position {x},{y}: Image #{image_count}"
                    self.root.after(0, lambda info=status_info: self.status_var.set(info))
                    
                    if self.auto_capture.get():
                        # Automatic capture mode

                        self.take_both_photos()
                        time.sleep(1)  # Brief pause between positions
                    else:
                        # Manual confirmation mode

                        self.waiting_for_photo = True
                        

                        pos_str = f"{x},{y}"
                        self.root.after(0, lambda cnt=image_count, p=pos_str: self._show_photo_prompt(cnt, p))
                        
                        # Wait for user confirmation
                        while self.waiting_for_photo and not self.stop_imaging:
                            time.sleep(0.1)
            
                if self.stop_imaging:
                    break
            
            # Complete sequence
            if not self.stop_imaging:
                self.root.after(0, lambda: self.status_var.set(f"Imaging sequence complete - {image_count} positions captured"))
            else:
                self.root.after(0, lambda: self.status_var.set("Imaging sequence stopped"))
            

            self.is_imaging = False
            self.root.after(0, lambda: self.start_imaging_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_imaging_button.config(state=tk.DISABLED))
            
        except Exception as e:
            error_msg = f"Imaging error: {str(e)}"
            self.root.after(0, lambda: self.status_var.set(error_msg))
            self.is_imaging = False
            self.root.after(0, lambda: self.start_imaging_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_imaging_button.config(state=tk.DISABLED))
            
    def stop_imaging_sequence(self):
        """Stop the automated imaging sequence"""
        if not self.is_imaging:
            return
            
        if messagebox.askyesno("Confirm", "Stop the imaging sequence?"):
            self.stop_imaging = True
            self.status_var.set("Stopping imaging sequence...")
            self.stop_imaging_button.config(state=tk.DISABLED)
    
    def set_zero_position(self):
        """Set the current position as the zero point (origin)"""
        if not self.connected:
            return
            
        try:
            # Set the current position as origin (0,0)
            self.gantry.GCommand('DP 0,0')
            

            self.status_var.set("Position zeroed - current position is now (0,0)")
            

            self.current_x = 0
            self.current_y = 0
            self.position_var.set("X: 0, Y: 0")
            
        except Exception as e:
            self.status_var.set(f"Zero position error: {e}")

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = IntegratedGantryCameraGUI(root)
    root.mainloop()
