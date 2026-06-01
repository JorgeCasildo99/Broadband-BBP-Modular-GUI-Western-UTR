import customtkinter as ctk
import os
import sys

# --- PATH SETUP ---
# Ensures all subfolders are importable regardless of where the script is run from.
# BASE_DIR always points to the bbp_gui/ folder where main.py lives.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)                                      # root: bbp_gui/
sys.path.insert(0, os.path.join(BASE_DIR, "core"))               # bbp_gui/core/
sys.path.insert(0, os.path.join(BASE_DIR, "ui"))                 # bbp_gui/ui/
sys.path.insert(0, os.path.join(BASE_DIR, "ui", "GravesAndPitarka"))  # bbp_gui/ui/GravesAndPitarka/
sys.path.insert(0, os.path.join(BASE_DIR, "ui", "results"))        # bbp_gui/ui/results/

# --- CORE IMPORTS ---
# AppConfig and WSLBridge live in bbp_gui/core/
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge

# --- UI IMPORTS ---
# Resources.py lives in bbp_gui/core/
import core.Resources as res
from ui.Dashboard import DashboardPanel
from ui.GravesAndPitarka.GravesAndPitarkaPanel import GravesAndPitarkaPanel
from ui.SimulationPanel import SimulationPanel
from ui.results.ResultsPanel        import ResultsPanel
from ui.results.ResultsHistoryPanel import ResultsHistoryPanel
from ui.ConfigurationPanel          import ConfigurationPanel


class MainPanel(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- FORCE DARK THEME ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("BBP Modular Interface - Research System")
        self.geometry("1100x800")
        self.minsize(1000, 750)

        # Main background color
        self.configure(fg_color="#1a1a1a")

        # --- FIXED STATUS BAR ---
        self.status_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="#111111")
        self.status_bar.pack(side="top", fill="x")

        self.lbl_status_icon = ctk.CTkLabel(
            self.status_bar, text="●", text_color="yellow", font=("Arial", 16)
        )
        self.lbl_status_icon.pack(side="left", padx=(20, 5))

        self.lbl_status_text = ctk.CTkLabel(
            self.status_bar,
            text="INITIALIZING...",
            font=(res.FONT_LABEL[0], 12, "bold")
        )
        self.lbl_status_text.pack(side="left")

        # --- WSL STATUS INDICATOR (right side of status bar) ---
        # Shows WSL connection state persistently so researchers always
        # know if the Linux environment is reachable
        self.lbl_wsl_info = ctk.CTkLabel(
            self.status_bar,
            text="WSL: Checking...",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        )
        self.lbl_wsl_info.pack(side="right", padx=20)

        # --- DYNAMIC CONTENT CONTAINER ---
        self.container = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        self.run_startup_sequence()

    # ------------------------------------------------------------------
    # STARTUP SEQUENCE
    # ------------------------------------------------------------------

    def run_startup_sequence(self):
        """
        Clears the container and starts the animated step-by-step
        startup check sequence using self.after() to keep UI responsive.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        self.lbl_loading = ctk.CTkLabel(
            self.container,
            text="System Handshake...",
            font=(res.FONT_TITLE[0], 24, "bold")
        )
        self.lbl_loading.pack(pady=(150, 10))

        self.lbl_step = ctk.CTkLabel(
            self.container,
            text="Checking WSL availability...",
            font=(res.FONT_LABEL[0], 14)
        )
        self.lbl_step.pack(pady=5)

        self.prog_bar = ctk.CTkProgressBar(self.container, width=400)
        self.prog_bar.pack(pady=20)
        self.prog_bar.set(0)

        # Kick off the sequence — each step schedules the next
        self.after(800, self.step_0_check_wsl)

    def step_0_check_wsl(self):
        """
        STEP 0 — WSL Check (NEW)
        Verifies WSL is installed and reachable from Windows Python.
        This must pass before any BBP check since BBP lives inside WSL.
        Uses WSLBridge.check_wsl_available() instead of shutil.which()
        which only looks at Windows PATH.
        Progress: 0% -> 25%
        """
        wsl_ok, wsl_version = WSLBridge.check_wsl_available()

        if wsl_ok:
            self.prog_bar.set(0.25)
            self.lbl_wsl_info.configure(
                text=f"WSL: {wsl_version}",
                text_color=res.COLOR_SUCCESS
            )
            self.lbl_step.configure(text="WSL Found. Checking BBP Core...")
            self.after(800, self.step_1_check_bbp)
        else:
            self.lbl_wsl_info.configure(
                text="WSL: NOT FOUND",
                text_color=res.COLOR_ERROR
            )
            self.show_error(
                "WSL NOT DETECTED\n"
                "Please install WSL and ensure it is accessible.\n"
                "Run: wsl --install in PowerShell as Administrator."
            )

    def step_1_check_bbp(self):
        """
        STEP 1 — BBP Check (UPDATED)
        Uses WSLBridge.check_bbp_environment() to verify BBP inside WSL.
        Previously used shutil.which() and os.environ.get() which only
        see Windows paths and environment variables, not WSL ones.
        Progress: 25% -> 50%
        """
        bbp_status = WSLBridge.check_bbp_environment()

        if bbp_status["connected"]:
            self.prog_bar.set(0.5)
            self.lbl_step.configure(
                text=f"BBP Found ({bbp_status['version']}). Creating Project Workspace..."
            )
            self.after(800, self.step_2_create_folders)
        else:
            self.show_error(
                f"BBP PLATFORM NOT DETECTED INSIDE WSL\n"
                f"Details: {bbp_status['details']}\n"
                f"Ensure BBP_DIR and BBP_DATA_DIR are set in your WSL ~/.bashrc"
            )

    def step_2_create_folders(self):
        """
        STEP 2 — Workspace Creation (UPDATED)
        AppConfig.create_session_structure() now uses WSLBridge internally
        to create folders inside the WSL filesystem. Previously used
        os.makedirs() which only works on Windows paths.
        Returns a (success, error_msg) tuple instead of just True/False.
        Progress: 50% -> 100%
        """
        success, error_msg = AppConfig.create_session_structure()

        if success:
            self.prog_bar.set(1.0)
            self.lbl_step.configure(
                text=f"Workspace Created: {os.path.basename(AppConfig.current_session_folder)}",
                text_color=res.COLOR_SUCCESS
            )

            # Update status bar to READY
            self.lbl_status_icon.configure(text_color=res.COLOR_SUCCESS)
            self.lbl_status_text.configure(
                text="SYSTEM READY",
                text_color=res.COLOR_SUCCESS
            )

            self.after(1200, self.load_dashboard)
        else:
            self.show_error(
                f"FOLDER CREATION FAILED INSIDE WSL\n"
                f"{error_msg}\n"
                f"Check WSL write permissions for: {AppConfig.BASE_PATH}"
            )

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------

    def load_dashboard(self):
        """
        Destroys loading content and loads the main Dashboard panel.
        This is the home screen researchers return to between modules.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        self.dashboard = DashboardPanel(
            self.container,
            open_gp_callback      = self.show_rupture_module,
            open_results_callback = self.open_results_history,
            open_config_callback  = self.open_configuration_panel
        )
        self.dashboard.pack(fill="both", expand=True)

    def open_configuration_panel(self):
        """Opens the Velocity Model Configuration panel as a popup."""
        ConfigurationPanel(self)

    def open_results_history(self):
        """Opens the ResultsHistoryPanel as a full window from the Dashboard."""
        ResultsHistoryPanel(
            master          = self,
            on_open_results = self.show_results_panel
        )

    def show_rupture_module(self):
        """
        Switches from Dashboard to GravesAndPitarkaPanel.
        Nav bar lives in MainPanel — GravesAndPitarkaPanel is fully self-contained.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        # --- NAVIGATION BAR --- (contains title to save vertical space)
        nav_bar = ctk.CTkFrame(
            self.container,
            height=44,
            fg_color="#111111",
            corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160,
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color="#444444",
            text_color="white",
            hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        # Title in the center of the nav bar
        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="GRAVES & PITARKA",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="GP Method  —  Broadband Ground Motion Simulation  —  LABasin500",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="left", pady=7)

        session_name = os.path.basename(AppConfig.current_session_folder) \
            if AppConfig.current_session_folder else "No session"
        ctk.CTkLabel(
            nav_bar,
            text=f"Session: {session_name}",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="right", padx=15, pady=7)

        # --- GRAVES & PITARKA PANEL ---
        self.gp_module = GravesAndPitarkaPanel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.gp_module.pack(fill="both", expand=True)

    def show_simulation_panel(self):
        """
        Called when RUN BBP is clicked in RupturePanel.
        Clears the container and opens SimulationPanel as a toplevel.
        """
        # Clear main window container so rupture panel disappears
        for widget in self.container.winfo_children():
            widget.destroy()

        # Show a simple waiting label in the background
        ctk.CTkLabel(
            self.container,
            text="Simulation in progress...",
            font=(res.FONT_LABEL[0], 16),
            text_color="gray"
        ).pack(expand=True)

        SimulationPanel(
            master              = self,
            base_name           = AppConfig.current_base_name,
            src_path            = AppConfig.current_src_file,
            stl_path            = AppConfig.current_stl_file,
            on_results_callback = self.show_results_panel
        )

    def show_results_panel(self):
        """
        Called when the user clicks View Results in SimulationPanel.
        Opens ResultsPanel as a full window.
        """
        ResultsPanel(self)

    # ------------------------------------------------------------------
    # ERROR HANDLING
    # ------------------------------------------------------------------

    def show_error(self, msg):
        """
        UPDATED: Displays a styled error box with multiline message support
        and a retry button. More informative than the original single-line
        error, helping researchers diagnose WSL/BBP configuration issues.
        """
        self.lbl_status_icon.configure(text_color=res.COLOR_ERROR)
        self.lbl_status_text.configure(
            text="SYSTEM ERROR",
            text_color=res.COLOR_ERROR
        )

        # Clear the step label so it doesn't overlap with the error box
        if hasattr(self, 'lbl_step'):
            self.lbl_step.configure(text="")

        # Styled error detail box
        error_box = ctk.CTkFrame(
            self.container,
            fg_color="#2a0000",
            border_width=1,
            border_color=res.COLOR_ERROR,
            corner_radius=8
        )
        error_box.pack(pady=20, padx=60, fill="x")

        ctk.CTkLabel(
            error_box,
            text=msg,
            font=(res.FONT_LABEL[0], 12),
            text_color=res.COLOR_ERROR,
            wraplength=500,
            justify="left"
        ).pack(pady=15, padx=20)

        ctk.CTkButton(
            self.container,
            text="⟳  Retry",
            width=120,
            height=38,
            fg_color=res.COLOR_PRIMARY,
            command=self.run_startup_sequence
        ).pack(pady=10)


# ------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------
if __name__ == "__main__":
    app = MainPanel()
    app.mainloop()