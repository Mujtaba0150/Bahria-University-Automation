#!/usr/bin/env python3
"""
Bahria University Automation Project - Interactive Setup Wizard
Provides a multi-page GUI for configuring the automation scripts.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import sys
from pathlib import Path
import platform

class SetupWizard:
    # Institution mapping (in order from form, including "Select" at index 0)
    # "Select" is not displayed, but index 0 is reserved for it
    INSTITUTIONS = [
        "Select",  # Index 0 (not displayed)
        "Bahria University College of Nursing",  # Index 1
        "Finishing School",  # Index 2
        "Health Sciences Campus (Islamabad)",  # Index 3
        "Health Sciences Campus (Karachi)",  # Index 4
        "IPP (Karachi)",  # Index 5
        "Islamabad E-8 Campus",  # Index 6 (DEFAULT)
        "Islamabad H-11 Campus",  # Index 7
        "Karachi Campus",  # Index 8
        "Lahore Campus",  # Index 9
        "NATIONAL SCHOOL OF HYDROGRAPHY",  # Index 10
        "NCMPR",  # Index 11
        "ODL",  # Index 12
        "PN Nursing College",  # Index 13
        "PN School Of Logistics",  # Index 14
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Bahria University Automation - Setup Wizard")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        # Configure colors
        self.bg_color = "#f5f5f5"
        self.fg_color = "#1a1a1a"
        self.accent_color = "#2c3e50"
        self.button_color = "#1a2635"
        self.button_hover_color = "#0f1620"

        self.root.configure(bg=self.bg_color)

        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')

        # Configure Combobox style - remove hover effects
        style.configure('TCombobox',
                       fieldbackground="#ffffff",
                       background="#ffffff",
                       foreground=self.fg_color,
                       padding=5,
                       relief='flat',
                       borderwidth=0)
        style.map('TCombobox',
                 fieldbackground=[('readonly', '#ffffff')],
                 background=[('readonly', '#ffffff')],
                 foreground=[('readonly', self.fg_color)])

        # Configure button style
        style.configure('TButton',
                       padding=10,
                       font=('Arial', 10),
                       relief='flat',
                       borderwidth=0)
        style.map('TButton',
                 background=[('active', self.button_color), ('pressed', self.accent_color)])
        
        # Configure Scrollbar style - minimal like Instagram
        style.configure('TScrollbar',
                       width=2,
                       troughcolor="#2c2c2c",
                       borderwidth=0,
                       darkcolor="#9f9f9f",
                       lightcolor="#9f9f9f")
        style.map('TScrollbar',
                 background=[('pressed', '#9f9f9f'), ('active', '#9f9f9f')])

        # Determine platform
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"

        # Default paths
        if self.is_windows:
            self.default_data_dir = os.path.join(os.environ.get("APPDATA"), "ms-playwright")
            self.default_download_dir = os.path.join(os.environ.get("USERPROFILE"), "Documents", "Assignments")
        else:
            home = os.path.expanduser("~")
            self.default_data_dir = os.path.join(home, ".local", "share", "ms-playwright")
            self.default_download_dir = os.path.join(home, "Documents", "Assignments")

        # Default values
        self.default_values = {
            'institution': '6',  # Islamabad E-8 Campus at index 6
            'disabled': 0,
            'gender': 0,
            'age': 0,
            'on_campus': 1,
            'notification_level': 0,
            'notify_extended': 1,
            'check_updates': 1,
            'create_aliases': True,
            'check_assignments_alias': 'assign',
            'check_attendance_alias': 'attend',
            'fill_surveys_alias': 'survey',
        }

        # Store values and load from .env if exists
        self.values = self.load_env_values()
        # If create_aliases is False (meaning "don't create aliases" was checked before), skip the aliases page
        self.skip_aliases_page = not self.values.get('create_aliases', True)
        # If enrollment_number or password are not set, we can skip the credentials page
        self.skip_credentials_page = not self.values.get('enrollment_number') or not self.values.get('password')
        self.current_page = 0
        self.pages = [
            self.page_credentials,
            self.page_directories,
            self.page_survey_vars,
            self.page_aliases,
            self.page_summary
        ]

        # Create main frame
        self.main_frame = tk.Frame(root, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create content frame (will be replaced by pages)
        self.content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Create navigation frame
        self.nav_frame = tk.Frame(self.main_frame, bg=self.accent_color, height=60)
        self.nav_frame.pack(fill=tk.X, padx=0, pady=0)

        self.prev_button = tk.Button(self.nav_frame, text="◀ Back", command=self.prev_page,
                                     bg=self.button_color, fg="white",
                                     font=("Arial", 10, "bold"), relief=tk.FLAT, borderwidth=0,
                                     highlightthickness=0, activebackground=self.button_hover_color, activeforeground="white", padx=20, pady=10)
        self.prev_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.page_label = tk.Label(self.nav_frame, text="", bg=self.accent_color,
                                  fg="white", font=("Arial", 9))
        self.page_label.pack(side=tk.LEFT, expand=True, padx=10, pady=10)

        self.next_button = tk.Button(self.nav_frame, text="Next ▶", command=self.next_page,
                                    bg=self.button_color, fg="white",
                                    font=("Arial", 10, "bold"), relief=tk.FLAT, borderwidth=0,
                                    highlightthickness=0, activebackground=self.button_hover_color, activeforeground="white", padx=20, pady=10)
        self.next_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.cancel_button = tk.Button(self.nav_frame, text="✕ Cancel", command=self.cancel,
                                      bg="#c0392b", fg="white",
                                      font=("Arial", 10, "bold"), relief=tk.FLAT, borderwidth=0,
                                      highlightthickness=0, activebackground="#922b21", activeforeground="white", padx=20, pady=10)
        self.cancel_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.show_page()

    def load_env_values(self):
        """Load existing values from .env file if it exists"""
        values = {}
        env_file = Path(".") / ".env"

        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()

                            # Map env keys to values dict
                            if key == 'ENROLLMENT_NUMBER':
                                # Strip quotes if present
                                values['enrollment_number'] = value.strip('"\'')
                            elif key == 'PASSWORD':
                                # Strip quotes if present
                                values['password'] = value.strip('"\'')
                            elif key == 'USER_DATA_DIR':
                                values['user_data_dir'] = value.strip('"\'')
                            elif key == 'DOWNLOAD_DIR':
                                values['download_dir'] = value.strip('"\'')
                            elif key == 'INSTITUTION':
                                values['institution'] = value.strip('"\'')
                            elif key == 'DISABLED':
                                values['disabled'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 0
                            elif key == 'GENDER':
                                values['gender'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 0
                            elif key == 'AGE':
                                values['age'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 0
                            elif key == 'ON_CAMPUS':
                                values['on_campus'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 1
                            elif key == 'NOTIFICATION_LEVEL':
                                values['notification_level'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 0
                            elif key == 'NOTIFY_EXTENDED':
                                values['notify_extended'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 1
                            elif key == 'CHECK_UPDATES':
                                values['check_updates'] = int(value.strip('"\'')) if value.strip('"\'').isdigit() else 1

            except Exception as e:
                print(f"Warning: Could not read .env file: {e}")

        # Fill in missing values with defaults
        for key, default in self.default_values.items():
            if key not in values:
                values[key] = default

        return values

    def clear_content(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_page(self):
        """Show current page"""
        self.clear_content()
        self.pages[self.current_page]()
        self.update_nav_buttons()

    def update_nav_buttons(self):
        """Update navigation buttons"""
        self.page_label.config(text=f"Page {self.current_page + 1} of {len(self.pages)}")
        self.prev_button.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)

        if self.current_page == len(self.pages) - 1:
            self.next_button.config(text="Finish")
        else:
            self.next_button.config(text="Next")

    def next_page(self):
        """Go to next page"""
        if self.current_page == len(self.pages) - 1:
            self.finish()
        else:
            self.current_page += 1
            # Skip credentials page if user chose to skip sign in
            if self.current_page == 0 and self.skip_credentials_page:
                self.current_page += 1
            # Skip aliases page if user checked "Don't create aliases"
            if self.current_page == 3 and self.skip_aliases_page:
                self.current_page += 1
            self.show_page()

    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            prev_page_num = self.current_page
            self.current_page -= 1
            # Skip credentials page when going backwards if it should be skipped
            if self.current_page == 0 and self.skip_credentials_page:
                # Can't go before page 0, so stay at page 1 (directories)
                self.current_page = 1
            # When going back FROM page 3 (aliases), reset skip_aliases_page
            # to allow user to reconsider their choice
            if prev_page_num == 3:
                self.skip_aliases_page = False

            self.show_page()

    def cancel(self):
        """Cancel setup"""
        if messagebox.askyesno("Cancel", "Are you sure you want to cancel setup?"):
            self.root.destroy()
            sys.exit(0)

    def enable_canvas_scrolling(self, canvas):
        """Enable trackpad/mouse wheel scrolling for a canvas"""
        def scroll_canvas(event):
            # Windows and macOS use MouseWheel, Linux uses Button-4/Button-5
            if event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5 or event.delta < 0:
                canvas.yview_scroll(3, "units")

        # Bind Windows/macOS mouse wheel
        canvas.bind("<MouseWheel>", scroll_canvas)
        # Bind Linux mouse wheel (Button-4 and Button-5)
        canvas.bind("<Button-4>", scroll_canvas)
        canvas.bind("<Button-5>", scroll_canvas)

    def finish(self):
        """Finish setup and write .env file"""
        try:
            env_file = Path(".") / ".env"

            env_content = f"""# Bahria University Automation - Configuration
# Generated by setup wizard

# Login credentials
ENROLLMENT_NUMBER="{self.values.get('enrollment_number', '')}"
PASSWORD="{self.values.get('password', '')}"

# Paths
USER_DATA_DIR={self.values.get('user_data_dir', self.default_data_dir)}
DOWNLOAD_DIR={self.values.get('download_dir', self.default_download_dir)}

# Survey variables
INSTITUTION={self.values.get('institution', 6)}
DISABLED={self.values.get('disabled', 0)}
GENDER={self.values.get('gender', 0)}
AGE={self.values.get('age', 0)}
ON_CAMPUS={self.values.get('on_campus', 1)}

# Notifications
NOTIFICATION_LEVEL={self.values.get('notification_level', 0)}
NOTIFY_EXTENDED={self.values.get('notify_extended', 1)}
CHECK_UPDATES={self.values.get('check_updates', 1)}
"""

            with open(env_file, 'w') as f:
                f.write(env_content)

            # Handle aliases/launchers
            if self.values.get('create_aliases', False):
                self.create_launchers()

            messagebox.showinfo("Success", "Setup completed successfully!\n\nYour .env file has been created.")
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete setup: {str(e)}")

    def create_launchers(self):
        """Create command aliases or shortcuts"""
        try:
            scripts = [
                ('checkAssignments.py', self.values.get('check_assignments_alias', 'check-assignments')),
                ('checkAttendance.py', self.values.get('check_attendance_alias', 'check-attendance')),
                ('fillSurveys.py', self.values.get('fill_surveys_alias', 'fill-surveys')),
            ]

            if self.is_windows:
                # Create batch files in the script directory
                script_dir = Path.cwd()
                for script, alias in scripts:
                    batch_file = script_dir / f"{alias}.cmd"
                    batch_content = f"@echo off\npython \"{script}\" %*"
                    with open(batch_file, 'w') as f:
                        f.write(batch_content)

                # Add script directory to PATH
                self._add_windows_path(script_dir)
            else:
                # Create symlinks or shell scripts in ~/.local/bin
                bin_dir = Path.home() / ".local" / "bin"
                bin_dir.mkdir(parents=True, exist_ok=True)

                script_dir = Path.cwd()
                for script, alias in scripts:
                    sh_file = bin_dir / alias
                    sh_content = f"""#!/bin/bash
python3 "{script_dir / script}" "$@"
"""
                    with open(sh_file, 'w') as f:
                        f.write(sh_content)
                    os.chmod(sh_file, 0o755)

        except Exception as e:
            messagebox.showwarning("Warning", f"Could not create launchers: {str(e)}")

    def _add_windows_path(self, script_dir):
        """Add script directory to Windows PATH environment variable"""
        try:
            # Create PowerShell script for user scope
            ps_file = Path(script_dir) / "update_path.ps1"
            ps_content = f"""$dir = '{script_dir}'
$path = [Environment]::GetEnvironmentVariable('Path','User')
if ($path -notlike "*$dir*") {{
  [Environment]::SetEnvironmentVariable('Path', "$path;$dir", 'User')
}}
Remove-Item -LiteralPath "$PSScriptRoot\\update_path.ps1" -Force
"""
            with open(ps_file, 'w') as f:
                f.write(ps_content)

            import subprocess
            subprocess.run([
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(ps_file)
            ], check=False)

            messagebox.showinfo("PATH Updated", "Script directory added to USER PATH.\nRestart terminal for changes to take effect.")

        except Exception as e:
            messagebox.showwarning("Warning", f"Could not update PATH: {str(e)}")

    # ==================== PAGE 1: CREDENTIALS ====================
    def page_credentials(self):
        """Page 1: Login credentials and institution selection"""
        title = tk.Label(self.content_frame, text="Step 1: Login Credentials",
                         font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.accent_color)
        title.pack(pady=(0, 5))

        desc = tk.Label(self.content_frame, text="Enter your Bahria University credentials and select your institution",
                        font=("Arial", 10), bg=self.bg_color, fg=self.fg_color)
        desc.pack(pady=(0, 15))

        # Create frame for form elements with grid layout for responsive resizing
        form_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        form_frame.columnconfigure(1, weight=1)

        # Enrollment number
        tk.Label(form_frame, text="Enrollment Number:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, sticky=tk.W, pady=12)
        enrollment_entry = tk.Entry(form_frame, font=("Arial", 11), width=50,
                                   relief=tk.FLAT, borderwidth=0, bg="#ffffff")
        enrollment_entry.grid(row=0, column=1, sticky=tk.EW, padx=10)
        enrollment_entry.insert(0, self.values.get('enrollment_number', ''))

        # Password
        tk.Label(form_frame, text="Password:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, sticky=tk.W, pady=12)
        password_entry = tk.Entry(form_frame, show="*", font=("Arial", 11), width=50,
                                 relief=tk.FLAT, borderwidth=0, bg="#ffffff")
        password_entry.grid(row=1, column=1, sticky=tk.EW, padx=10)
        password_entry.insert(0, self.values.get('password', ''))

        # Institution dropdown
        tk.Label(form_frame, text="Institution:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.accent_color).grid(row=2, column=0, sticky=tk.W, pady=(20, 12))

        # Create list of institution names (excluding "Select" at index 0)
        institution_names = self.INSTITUTIONS[1:]  # Skip "Select"

        # Find the current institution index
        current_index = int(self.values.get('institution', '6'))
        # Display index is current_index - 1 (since we're not showing "Select")
        display_index = current_index - 1

        institution_combo = ttk.Combobox(form_frame, values=institution_names,
                                        font=("Arial", 11), state="readonly", width=47)
        institution_combo.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=(20, 0))
        institution_combo.current(max(0, display_index))  # Ensure index is valid

        # "Don't sign in" checkbox
        skip_signin_var = tk.BooleanVar(value=self.skip_credentials_page)
        skip_check = tk.Checkbutton(self.content_frame,
                       text="Skip sign-in (use empty credentials)",
                       variable=skip_signin_var, font=("Arial", 11),
                       bg=self.bg_color, fg=self.fg_color,
                       selectcolor="#ffffff", activebackground=self.bg_color,
                       relief=tk.FLAT, highlightthickness=0,
                       command=lambda: toggle_fields())
        skip_check.pack(anchor=tk.W, pady=10)

        # Disclaimer about credentials - at the bottom
        disclaimer_text = (
            "⚠ Security Notice:\n"
            "• Skipping sign-in is SAFER (credentials not stored), but requires manual login occasionally\n"
            "• Adding credentials is more CONVENIENT, but stores them in plain text in .env file"
        )
        disclaimer = tk.Label(self.content_frame, text=disclaimer_text,
                             font=("Arial", 9), bg="#fff3cd", fg="#856404",
                             justify=tk.LEFT, wraplength=600, relief=tk.FLAT, padx=10, pady=10)
        disclaimer.pack(pady=(10, 0), fill=tk.X, padx=5)

        def toggle_fields():
            # If "Skip sign-in" is checked, disable only enrollment/password; institution always enabled
            state = tk.DISABLED if skip_signin_var.get() else tk.NORMAL
            enrollment_entry.config(state=state)
            password_entry.config(state=state)
            institution_combo.config(state="readonly")  # Always enabled

        # Initial state
        toggle_fields()

        def save_values():
            skip_signin = skip_signin_var.get()
            self.skip_credentials_page = skip_signin
            
            if skip_signin:
                # If skipping, set empty credentials
                self.values['enrollment_number'] = ''
                self.values['password'] = ''
                self.values['institution'] = '6'  # Default institution
                return True
            
            enrollment = enrollment_entry.get()
            password = password_entry.get()
            selected_index = institution_combo.current()
            # Store the actual list index (add 1 because we're skipping "Select" at index 0)
            institution_index = str(selected_index + 1) if selected_index >= 0 else '6'

            self.values['enrollment_number'] = enrollment
            self.values['password'] = password
            self.values['institution'] = institution_index

            if not enrollment or not password:
                messagebox.showwarning("Validation", "Please enter both enrollment number and password")
                return False
            if selected_index < 0:
                messagebox.showwarning("Validation", "Please select an institution")
                return False
            return True

        # Override next_page for validation
        original_next = self.next_page
        def next_with_validation():
            if save_values():
                original_next()

        self.next_button.config(command=next_with_validation)

    # ==================== PAGE 2: DIRECTORIES ====================
    def page_directories(self):
        """Page 2: Directory selection"""
        title = tk.Label(self.content_frame, text="Step 2: Select Directories",
                         font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.accent_color)
        title.pack(pady=(0, 5))

        desc = tk.Label(self.content_frame, text="Select where browser data and downloads will be stored",
                        font=("Arial", 10), bg=self.bg_color, fg=self.fg_color)
        desc.pack(pady=(0, 15))

        # Create frame for form elements with grid layout for responsive resizing
        form_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        form_frame.columnconfigure(1, weight=1)

        # User data directory
        tk.Label(form_frame, text="Browser Data Directory:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, sticky=tk.W, pady=12)

        data_frame = tk.Frame(form_frame, bg=self.bg_color)
        data_frame.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=12)
        data_frame.columnconfigure(0, weight=1)

        data_var = tk.StringVar(value=self.values.get('user_data_dir', self.default_data_dir))
        data_entry = tk.Entry(data_frame, textvariable=data_var, font=("Arial", 10),
                             relief=tk.FLAT, borderwidth=0, bg="#ffffff")
        data_entry.grid(row=0, column=0, sticky=tk.EW)

        def browse_data_dir():
            folder = filedialog.askdirectory(title="Select Browser Data Directory")
            if folder:
                data_var.set(folder)

        browse_btn = tk.Button(data_frame, text="Browse", command=browse_data_dir,
                              bg=self.button_color, fg="white", font=("Arial", 10),
                              relief=tk.FLAT, borderwidth=0, highlightthickness=0, activebackground=self.accent_color, activeforeground="white")
        browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Download directory
        tk.Label(form_frame, text="Download Directory:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, sticky=tk.W, pady=12)

        download_frame = tk.Frame(form_frame, bg=self.bg_color)
        download_frame.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=12)
        download_frame.columnconfigure(0, weight=1)

        download_var = tk.StringVar(value=self.values.get('download_dir', self.default_download_dir))
        download_entry = tk.Entry(download_frame, textvariable=download_var, font=("Arial", 10),
                                 relief=tk.FLAT, borderwidth=0, bg="#ffffff")
        download_entry.grid(row=0, column=0, sticky=tk.EW)

        def browse_download_dir():
            folder = filedialog.askdirectory(title="Select Download Directory")
            if folder:
                download_var.set(folder)

        browse_btn2 = tk.Button(download_frame, text="Browse", command=browse_download_dir,
                               bg=self.button_color, fg="white", font=("Arial", 10),
                               relief=tk.FLAT, borderwidth=0, highlightthickness=0, activebackground=self.accent_color, activeforeground="white")
        browse_btn2.grid(row=0, column=1, padx=(5, 0))

        def save_values():
            self.values['user_data_dir'] = data_var.get()
            self.values['download_dir'] = download_var.get()

            if not self.values['user_data_dir'] or not self.values['download_dir']:
                messagebox.showwarning("Validation", "Please select both directories")
                return False
            return True

        original_next = self.next_page
        def next_with_validation():
            if save_values():
                original_next()

        self.next_button.config(command=next_with_validation)

    # ==================== PAGE 3: SURVEY VARIABLES ====================
    def page_survey_vars(self):
        """Page 3: Survey environment variables for fillSurveys.py"""
        title = tk.Label(self.content_frame, text="Step 3: Survey Configuration",
                         font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.accent_color)
        title.pack(pady=(0, 5))

        desc = tk.Label(self.content_frame, text="Configure survey response variables",
                        font=("Arial", 10), bg=self.bg_color, fg=self.fg_color)
        desc.pack(pady=(0, 15))

        # Create a scrollable frame
        canvas = tk.Canvas(self.content_frame, highlightthickness=0, bg=self.bg_color)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview, style='TScrollbar')
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set, bg=self.bg_color)

        # Enable trackpad/mouse wheel scrolling
        self.enable_canvas_scrolling(canvas)

        # Disability status
        tk.Label(scrollable_frame, text="Disability Status:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, pady=(5, 8))
        disabled_var = tk.StringVar(value=str(self.values.get('disabled', 0)))
        tk.Radiobutton(scrollable_frame, text="Non-disabled", variable=disabled_var, value="0",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)
        tk.Radiobutton(scrollable_frame, text="Disabled", variable=disabled_var, value="1",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W, pady=(0, 12))

        # Gender
        tk.Label(scrollable_frame, text="Gender:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, pady=(12, 8))
        gender_var = tk.StringVar(value=str(self.values.get('gender', 0)))
        tk.Radiobutton(scrollable_frame, text="Male", variable=gender_var, value="0",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)
        tk.Radiobutton(scrollable_frame, text="Female", variable=gender_var, value="1",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W, pady=(0, 12))

        # Age
        tk.Label(scrollable_frame, text="Age Group:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, pady=(12, 8))
        age_var = tk.StringVar(value=str(self.values.get('age', 0)))
        tk.Radiobutton(scrollable_frame, text="< 22", variable=age_var, value="0",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)
        tk.Radiobutton(scrollable_frame, text="22-29", variable=age_var, value="1",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)
        tk.Radiobutton(scrollable_frame, text="> 29", variable=age_var, value="2",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W, pady=(0, 12))

        # Campus status
        tk.Label(scrollable_frame, text="Campus Status:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, pady=(12, 8))
        campus_var = tk.StringVar(value=str(self.values.get('on_campus', 1)))
        tk.Radiobutton(scrollable_frame, text="On Campus", variable=campus_var, value="1",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)
        tk.Radiobutton(scrollable_frame, text="Off Campus", variable=campus_var, value="0",
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W, pady=(0, 12))

        # Notification level
        tk.Label(scrollable_frame, text="Notification Level:", font=("Arial", 11, "bold"),
                bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, pady=(12, 8))
        notification_var = tk.StringVar(value=str(self.values.get('notification_level', 0)))
        options = [("Due Today", "0"), ("Next 4 days", "1"), ("7 days", "2"), ("14 days", "3"), ("All", "4")]
        for text, val in options:
            tk.Radiobutton(scrollable_frame, text=text, variable=notification_var, value=val,
                          bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                          selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)

        # Notify extended
        notify_var = tk.BooleanVar(value=bool(self.values.get('notify_extended', True)))
        tk.Checkbutton(scrollable_frame, text="Notify for submitted assignments", variable=notify_var,
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W, pady=(12, 5))

        # Check updates
        check_var = tk.BooleanVar(value=bool(self.values.get('check_updates', True)))
        tk.Checkbutton(scrollable_frame, text="Check for updates", variable=check_var,
                      bg=self.bg_color, fg=self.fg_color, font=("Arial", 10),
                      selectcolor="#ffffff", activebackground=self.bg_color, relief=tk.FLAT, highlightthickness=0).pack(anchor=tk.W)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def save_values():
            self.values['disabled'] = int(disabled_var.get())
            self.values['gender'] = int(gender_var.get())
            self.values['age'] = int(age_var.get())
            self.values['on_campus'] = int(campus_var.get())
            self.values['notification_level'] = int(notification_var.get())
            self.values['notify_extended'] = 1 if notify_var.get() else 0
            self.values['check_updates'] = 1 if check_var.get() else 0
            return True

        original_next = self.next_page
        def next_with_validation():
            if save_values():
                original_next()

        self.next_button.config(command=next_with_validation)

    # ==================== PAGE 4: ALIASES ====================
    def page_aliases(self):
        """Page 4: Create command aliases"""
        title = tk.Label(self.content_frame, text="Step 4: Create Aliases",
                         font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.accent_color)
        title.pack(pady=(0, 5))

        desc = tk.Label(self.content_frame, text="Create command aliases for quick script execution",
                        font=("Arial", 10), bg=self.bg_color, fg=self.fg_color)
        desc.pack(pady=(0, 15))

        # Create frame for alias inputs
        alias_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        alias_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        alias_frame.columnconfigure(1, weight=1)

        scripts_info = [
            ("checkAssignments.py", "check_assignments_alias"),
            ("checkAttendance.py", "check_attendance_alias"),
            ("fillSurveys.py", "fill_surveys_alias"),
        ]

        entries = {}

        for idx, (script, key) in enumerate(scripts_info):
            tk.Label(alias_frame, text=f"{script}:", font=("Arial", 11, "bold"),
                    bg=self.bg_color, fg=self.fg_color).grid(row=idx, column=0, sticky=tk.W, pady=8)
            entry = tk.Entry(alias_frame, font=("Arial", 10), relief=tk.FLAT, borderwidth=0, bg="#ffffff")
            entry.grid(row=idx, column=1, sticky=tk.EW, padx=10, pady=8)
            default_alias = self.values.get(key, script.replace('.py', '').replace('Surveys', 'survey').replace('Assignments', 'assign').replace('Attendance', 'attend'))
            entry.insert(0, default_alias)
            entries[key] = entry

        info = tk.Label(self.content_frame,
                       text="Windows: Creates .bat files in Scripts directory\nLinux/macOS: Creates shell scripts in ~/.local/bin",
                       font=("Arial", 9), bg=self.bg_color, fg=self.fg_color, justify=tk.LEFT)
        info.pack(anchor=tk.W, pady=10)

        # "Don't create aliases" checkbox at the bottom (disabled by default = False)
        aliases_var = tk.BooleanVar(value=self.values.get('create_aliases', True) == False)
        create_check = tk.Checkbutton(self.content_frame,
                       text="Don't create aliases",
                       variable=aliases_var, font=("Arial", 11),
                       bg=self.bg_color, fg=self.fg_color,
                       selectcolor="#ffffff", activebackground=self.bg_color,
                       relief=tk.FLAT, highlightthickness=0,
                       command=lambda: toggle_fields())
        create_check.pack(anchor=tk.W, pady=10)

        def toggle_fields():
            # If "Don't create aliases" is checked, disable fields; otherwise enable them
            state = tk.DISABLED if aliases_var.get() else tk.NORMAL
            for entry in entries.values():
                entry.config(state=state)

        # Initial state
        toggle_fields()

        def save_values():
            # If "Don't create aliases" is checked, skip creating them
            dont_create = aliases_var.get()
            self.skip_aliases_page = dont_create
            self.values['create_aliases'] = not dont_create

            if not dont_create:  # If we ARE creating aliases, validate the names
                for key, entry in entries.items():
                    alias_name = entry.get().strip()
                    if not alias_name:
                        messagebox.showwarning("Validation", f"Please enter an alias name or check 'Don't create aliases'")
                        return False
                    self.values[key] = alias_name
            return True

        original_next = self.next_page
        def next_with_validation():
            if save_values():
                original_next()

        self.next_button.config(command=next_with_validation)

    # ==================== PAGE 6: SUMMARY ====================
    def page_summary(self):
        """Page 6: Summary before finishing"""
        title = tk.Label(self.content_frame, text="Setup Summary",
                         font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.accent_color)
        title.pack(pady=(0, 5))

        # Create frame for summary (no scrolling needed)
        summary_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Display summary
        summary_items = [
            ("Enrollment Number", self.values.get('enrollment_number', 'N/A')),
            ("Institution", self.INSTITUTIONS[int(self.values.get('institution', '6'))] if int(self.values.get('institution', '6')) < len(self.INSTITUTIONS) else 'N/A'),
            ("Browser Data Dir", self.values.get('user_data_dir', 'N/A')),
            ("Download Dir", self.values.get('download_dir', 'N/A')),
            ("Disabled", "Yes" if self.values.get('disabled', 0) else "No"),
            ("Gender", "Female" if self.values.get('gender', 0) else "Male"),
            ("Age Group", ["< 22", "22-29", "> 29"][self.values.get('age', 0)]),
            ("Campus", "On Campus" if self.values.get('on_campus', 1) else "Off Campus"),
            ("Notification Level", ["Today", "4 days", "7 days", "14 days", "All"][self.values.get('notification_level', 0)]),
            ("Create Aliases", "Yes" if self.values.get('create_aliases', False) else "No"),
        ]

        # Add aliases if creating them
        if self.values.get('create_aliases', False):
            summary_items.extend([
                ("  - checkAssignments.py", self.values.get('check_assignments_alias', 'check-assignments')),
                ("  - checkAttendance.py", self.values.get('check_attendance_alias', 'check-attendance')),
                ("  - fillSurveys.py", self.values.get('fill_surveys_alias', 'fill-surveys')),
            ])



        for key, value in summary_items:
            frame = tk.Frame(summary_frame, bg=self.bg_color, relief=tk.FLAT)
            frame.pack(anchor=tk.W, pady=5, fill=tk.X, padx=5)

            tk.Label(frame, text=f"{key}:", font=("Arial", 10, "bold"),
                    width=22, anchor=tk.W, bg=self.bg_color, fg=self.accent_color).pack(side=tk.LEFT)
            tk.Label(frame, text=str(value), font=("Arial", 10),
                    bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Override navigation
        self.prev_button.config(state=tk.NORMAL)
        self.next_button.config(text="Finish")


def main():
    root = tk.Tk()
    wizard = SetupWizard(root)

    # Center window on screen after initialization
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()
