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
sys.path.insert(0, os.path.join(BASE_DIR, "ui", "ExSIM"))           # bbp_gui/ui/ExSIM/
sys.path.insert(0, os.path.join(BASE_DIR, "ui", "results"))        # bbp_gui/ui/results/

# A windowed .exe has no console, so tracebacks would vanish. This sends
# them to %APPDATA%\BBP-GUI\bbp-gui.log (no-op when a console exists).
from core import WSLRuntime
WSLRuntime.redirect_output_to_log()

# --- CORE IMPORTS ---
# AppConfig and WSLBridge live in bbp_gui/core/
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge

# --- UI IMPORTS ---
# Resources.py lives in bbp_gui/core/
import core.Resources as res
from ui.Dashboard import DashboardPanel
from ui.GravesAndPitarka.GravesAndPitarkaPanel import GravesAndPitarkaPanel
from ui.Irikura.IrikuraPanel                   import IrikuraPanel
from ui.Irikura2.Irikura2Panel                 import Irikura2Panel
from ui.Song.SongPanel                         import SongPanel
from ui.SDSU.SDSUPanel                         import SDSUPanel
from ui.UCSB.UCSBPanel                         import UCSBPanel
from ui.RuptureGenerator.RuptureGeneratorPanel import RuptureGeneratorPanel
from ui.ExSIM.ExSimPanel             import ExSimPanel
from ui.SimulationPanel import SimulationPanel
from ui.results.ResultsPanel        import ResultsPanel
from ui.results.ResultsHistoryPanel import ResultsHistoryPanel
from ui.ConfigurationPanel          import ConfigurationPanel
from ui.ValidationPanel             import ValidationPanel


def _apply_ui_scale(window):
    """
    Keeps the layout at its design size on Windows. CustomTkinter scales
    every widget by the monitor's display scale (125%, 150%...), which
    WSLg never did, so without this everything looks too big. The factor
    is computed by WSLRuntime.ui_scale(); set "ui_scale" in
    %APPDATA%\\BBP-GUI\\config.json to make the interface larger/smaller.
    """
    try:
        dpi_scale = ctk.ScalingTracker.get_window_dpi_scaling(window)
    except Exception:
        dpi_scale = window.winfo_fpixels("1i") / 96.0
    factor = WSLRuntime.ui_scale(dpi_scale)
    if abs(factor - 1.0) > 0.01:
        ctk.set_widget_scaling(factor)
        ctk.set_window_scaling(factor)
    print(f"[BBP-GUI] display scale {dpi_scale:.2f} -> CustomTkinter scaling {factor:.2f}")


class MainPanel(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- FORCE DARK THEME ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        _apply_ui_scale(self)

        self.title("BBP Modular Interface - Research System")
        self.minsize(1000, 750)

        # Center exactly on screen before anything is drawn
        self.update_idletasks()
        _w, _h = 1100, 800
        _x = (self.winfo_screenwidth()  - _w) // 2
        _y = (self.winfo_screenheight() - _h) // 2
        self.geometry(f"{_w}x{_h}+{_x}+{_y}")

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
                f"WSL NOT DETECTED\n"
                f"Details: {wsl_version}\n"
                f"Please install WSL with an Ubuntu distribution and ensure it is accessible.\n"
                f"Run: wsl --install -d Ubuntu in PowerShell as Administrator."
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

        Resets Advanced GP Parameters back to BBP defaults on disk
        every time the Dashboard loads. This is intentional: custom
        overrides saved via AdvancedSettingsPanel are session-scoped —
        leaving the GP panel without resetting should never silently
        carry custom values into a future, unrelated run.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        try:
            home     = WSLBridge.get_wsl_home()
            cfg_path = f"{home}/bbp_gf/LABasin500/labasin500_velmodel_config.txt"
            WSLBridge.reset_advanced_params_to_defaults(cfg_path)
        except Exception:
            # Non-fatal — if WSL isn't reachable yet (e.g. very first
            # launch before the environment check completes), just
            # skip the reset rather than blocking the Dashboard.
            pass

        AppConfig.advanced_params_active = False
        AppConfig.advanced_params        = {}

        self.dashboard = DashboardPanel(
            self.container,
            open_gp_callback                = self.show_rupture_module,
            open_exsim_callback              = self.show_exsim_module,
            open_irikura1_callback           = self.show_irikura_module,
            open_irikura2_callback           = self.show_irikura2_module,
            open_song_callback               = self.show_song_module,
            open_ucsb_callback               = self.show_ucsb_module,
            open_sdsu_callback               = self.show_sdsu_module,
            open_results_callback            = self.open_results_history,
            open_config_callback             = self.open_configuration_panel,
            open_validation_callback         = self.open_validation_panel,
            open_rupture_generator_callback  = self.show_rupture_generator_module
        )
        self.dashboard.pack(fill="both", expand=True)

    def open_results_history(self):
        """Opens the ResultsHistoryPanel as a full window from the Dashboard."""
        ResultsHistoryPanel(
            master          = self,
            on_open_results = self.show_results_panel,
            on_edit_run     = self.open_run_for_edit
        )

    def open_configuration_panel(self):
        """Opens the Velocity Model Configuration panel as a popup."""
        ConfigurationPanel(self)

    def open_validation_panel(self):
        """Opens the Validation Simulation panel as a popup."""
        ValidationPanel(
            self,
            on_results_callback=self._on_validation_results
        )

    def _on_validation_results(self, run_id, event):
        """Called when a validation run completes and user clicks View Results."""
        if not run_id:
            return

        # Set AppConfig so ResultsPanel can find the output files
        bbp_home = __import__('core.WSLBridge', fromlist=['WSLBridge']).WSLBridge.get_wsl_home()
        bbp_data_result = __import__('core.WSLBridge', fromlist=['WSLBridge']).WSLBridge.run_command(
            "echo $BBP_DATA_DIR"
        )
        bbp_data = bbp_data_result.stdout.strip() or f"{bbp_home}/bbp_data"

        AppConfig.current_run_id    = run_id
        AppConfig.current_base_name = event.get("short_name", run_id) if event else run_id
        AppConfig.out_path          = f"{bbp_data}/outdata/{run_id}"

        ResultsPanel(self)

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

    def show_exsim_module(self):
        """
        Switches from Dashboard to ExSimPanel.
        Nav bar lives in MainPanel — ExSimPanel is fully self-contained,
        mirroring how show_rupture_module wires GravesAndPitarkaPanel.
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
            text="EXSIM",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#ffaa44"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Stochastic Method (Boore 2003)  —  Broadband Ground Motion Simulation  —  LABasin500",
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

        # --- EXSIM PANEL ---
        self.exsim_module = ExSimPanel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.exsim_module.pack(fill="both", expand=True)

    def show_irikura_module(self):
        """
        Switches from Dashboard to IrikuraPanel.
        Same structure as show_rupture_module but with Irikura green theme.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        nav_bar = ctk.CTkFrame(
            self.container, height=44, fg_color="#111111", corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="IRIKURA RECIPE 1",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#22aa55"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Irikura & Miyake (2011)  —  Broadband Ground Motion Simulation  —  LABasin500",
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

        AppConfig.simulation_method = "IRIKURA1"

        self.irikura_module = IrikuraPanel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.irikura_module.pack(fill="both", expand=True)

    def show_irikura2_module(self):
        """
        Switches from Dashboard to Irikura2Panel.
        Same structure as show_irikura_module but with the teal
        (#22ccaa) theme — a new color, not reused from any other
        method's card.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        nav_bar = ctk.CTkFrame(
            self.container, height=44, fg_color="#111111", corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="IRIKURA RECIPE 2",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#22ccaa"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Kamae et al. (1998)  —  Broadband Ground Motion Simulation  —  LABasin500",
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

        AppConfig.simulation_method = "IRIKURA2"

        self.irikura2_module = Irikura2Panel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.irikura2_module.pack(fill="both", expand=True)

    def show_song_module(self):
        """
        Switches from Dashboard to SongPanel.
        Same structure as show_irikura_module but with Song purple theme.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        nav_bar = ctk.CTkFrame(
            self.container, height=44, fg_color="#111111", corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="SONG RMG",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#8855cc"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Song Pseudo-dynamic Rupture Generator  —  Broadband Ground Motion Simulation  —  LABasin500",
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

        AppConfig.simulation_method = "SONG"

        self.song_module = SongPanel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.song_module.pack(fill="both", expand=True)

    def show_ucsb_module(self):
        """
        Switches from Dashboard to UCSBPanel.
        Same structure as show_song_module but with UCSB's theme.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        nav_bar = ctk.CTkFrame(
            self.container, height=44, fg_color="#111111", corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="UCSB",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#cc3366"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Crempien & Archuleta (2015), JA19_2S source spectrum  —  Broadband Ground Motion Simulation  —  LABasin500",
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

        AppConfig.simulation_method = "UCSB"

        self.ucsb_module = UCSBPanel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.ucsb_module.pack(fill="both", expand=True)

    def show_sdsu_module(self):
        """
        Switches from Dashboard to SDSUPanel.
        Same structure as show_ucsb_module but with SDSU's theme.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        nav_bar = ctk.CTkFrame(
            self.container, height=44, fg_color="#111111", corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="SDSU",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#5566ee"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Olsen & Takedatsu (2015)  —  Broadband Ground Motion Simulation  —  LABasin500",
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

        AppConfig.simulation_method = "SDSU"

        self.sdsu_module = SDSUPanel(
            self.container,
            on_run_callback=self.show_simulation_panel
        )
        self.sdsu_module.pack(fill="both", expand=True)

    def show_rupture_generator_module(self):
        """
        Switches from Dashboard to RuptureGeneratorPanel.
        Unlike the method panels, this one owns its own run queue and
        drives SimulationPanel directly (chaining through multiple
        selected methods), so it needs a reference to the app root
        (self) rather than just on_run_callback=self.show_simulation_panel.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        nav_bar = ctk.CTkFrame(
            self.container, height=44, fg_color="#111111", corner_radius=6
        )
        nav_bar.pack(fill="x", pady=(0, 6))
        nav_bar.pack_propagate(False)

        ctk.CTkButton(
            nav_bar,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self.load_dashboard
        ).pack(side="left", padx=10, pady=7)

        title_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both")

        ctk.CTkLabel(
            title_frame,
            text="RUPTURE GENERATOR",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(side="left", padx=(0, 6), pady=7)

        ctk.CTkLabel(
            title_frame,
            text="Compare GP, Irikura Recipe 1, and Song rupture models from the same fault geometry",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="left", pady=7)

        self.rupture_generator_module = RuptureGeneratorPanel(
            self.container,
            app_root=self,
            on_dashboard_callback=self.load_dashboard,
            on_results_callback=self.show_results_panel
        )
        self.rupture_generator_module.pack(fill="both", expand=True)

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
            master                = self,
            base_name             = AppConfig.current_base_name,
            src_path              = AppConfig.current_src_file,
            stl_path              = AppConfig.current_stl_file,
            on_results_callback   = self.show_results_panel,
            on_dashboard_callback = self.load_dashboard
        )

    def show_results_panel(self):
        """
        Called when the user clicks View Results in SimulationPanel.
        Opens ResultsPanel as a full window.
        """
        ResultsPanel(self)

    # ------------------------------------------------------------------
    # EDIT / RE-SIMULATE A PREVIOUS RUN
    # ------------------------------------------------------------------

    def open_run_for_edit(self, method, params, stations):
        """
        Called by ResultsHistoryPanel when the user clicks Edit on a run.
        Navigates to the correct method panel and pre-fills all fields.
        """
        if method == "GP":
            self.show_rupture_module()
            if hasattr(self, "gp_module") and self.gp_module:
                self.gp_module.load_from_src(params, stations)
        elif method == "IRIKURA1":
            self.show_irikura_module()
            if hasattr(self, "irikura_module") and self.irikura_module:
                self.irikura_module.load_from_src(params, stations)
        elif method == "IRIKURA2":
            self.show_irikura2_module()
            if hasattr(self, "irikura2_module") and self.irikura2_module:
                self.irikura2_module.load_from_src(params, stations)
        elif method == "SONG":
            self.show_song_module()
            if hasattr(self, "song_module") and self.song_module:
                self.song_module.load_from_src(params, stations)
        elif method == "UCSB":
            self.show_ucsb_module()
            if hasattr(self, "ucsb_module") and self.ucsb_module:
                self.ucsb_module.load_from_src(params, stations)
        elif method == "SDSU":
            self.show_sdsu_module()
            if hasattr(self, "sdsu_module") and self.sdsu_module:
                self.sdsu_module.load_from_src(params, stations)
        elif method == "EXSIM":
            self.show_exsim_module()
            if hasattr(self, "exsim_module") and self.exsim_module:
                self.exsim_module.load_from_src(params, stations)

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
            text="Retry",
            width=120,
            height=38,
            fg_color=res.COLOR_PRIMARY,
            command=self.run_startup_sequence
        ).pack(pady=10)


# ------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    def _on_close():
        """
        Clean shutdown handler - cancels any pending after() callbacks
        before destroying the window so Tkinter doesn't fire them into
        a destroyed application and print bgerror messages.
        """
        try:
            # Cancel all pending after() callbacks
            for after_id in app.tk.call("after", "info"):
                try:
                    app.after_cancel(after_id)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            app.quit()
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass
        sys.exit(0)

    app = MainPanel()
    app.protocol("WM_DELETE_WINDOW", _on_close)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        sys.exit(0)