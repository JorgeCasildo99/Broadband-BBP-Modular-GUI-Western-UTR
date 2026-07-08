# SimulationPanel.py — ui/SimulationPanel.py
# -------------------------------------------------------
# Full window that appears when the user clicks RUN BBP.
# Generates the XML, triggers BBP via WSLBridge, streams
# live output, tracks module progress, and shows results
# location on completion.
# -------------------------------------------------------

import customtkinter as ctk
import threading
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge
from core.XMLGenerator import save_xml, BBP_MODULES, get_modules_for_profile


class SimulationPanel(ctk.CTkToplevel):
    """
    Full window that opens when the user triggers a BBP simulation.
    Shows a progress bar, live module status, streaming console log,
    and a results location message on completion.
    """

    def __init__(self, master, base_name, src_path, stl_path, on_results_callback=None, on_dashboard_callback=None):
        super().__init__(master)

        self.base_name              = base_name
        self.src_path               = src_path
        self.stl_path               = stl_path
        self._on_results_callback   = on_results_callback
        self._on_dashboard_callback = on_dashboard_callback

        # Get the module list for the selected profile
        self._profile         = AppConfig.simulation_profile
        self._method          = getattr(AppConfig, "simulation_method", "GP")
        self._custom_modules  = list(AppConfig.custom_modules) if AppConfig.simulation_profile == "custom" else []
        self._active_modules  = get_modules_for_profile(self._profile, self._custom_modules, method=self._method)

        # Track current module index for progress
        self._current_module  = 0
        self._total_modules   = len(self._active_modules)
        self._failed_module   = None
        self._simulation_done = False
        self._xml_path        = None

        self.title("BBP Simulation — Running")
        self.geometry("900x700")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()

        # Delay start so window is fully visible before BBP begins
        self.after(300, self._start_simulation)
        self.after(200, self._on_ready)

    def _on_ready(self):
        try:
            self.lift()
            self.focus_force()
            self.update_idletasks()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------------

    def _build_ui(self):

        # --- TITLE BAR ---
        title_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=70)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        ctk.CTkLabel(
            title_frame,
            text="Running BBP Simulation",
            font=(res.FONT_TITLE[0], 22, "bold"),
            text_color="white"
        ).pack(side="left", padx=25, pady=15)

        if self._method in ("GP", "EXSIM"):
            method_colors = {
                "GP"   : ("#0a2a3a", "#3b8ed0"),
                "EXSIM": ("#3a1a00", "#ffaa44"),
            }
            bg_color, fg_color = method_colors[self._method]
            ctk.CTkLabel(
                title_frame,
                text=self._method,
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color=fg_color,
                fg_color=bg_color,
                corner_radius=4,
                padx=8, pady=3
            ).pack(side="left", padx=(0, 25), pady=15)

        ctk.CTkLabel(
            title_frame,
            text=f"Experiment: {self.base_name}   |   Profile: {AppConfig.get_profile_label()}",
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        ).pack(side="right", padx=25)

        # --- PROGRESS SECTION ---
        prog_frame = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        prog_frame.pack(fill="x", padx=25, pady=(20, 10))

        # Module name label
        self.lbl_module = ctk.CTkLabel(
            prog_frame,
            text="Preparing simulation...",
            font=(res.FONT_LABEL[0], 15, "bold"),
            text_color="white"
        )
        self.lbl_module.pack(pady=(18, 4), padx=20, anchor="w")

        # Module description label
        self.lbl_desc = ctk.CTkLabel(
            prog_frame,
            text="Generating XML options file...",
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        )
        self.lbl_desc.pack(pady=(0, 10), padx=20, anchor="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            prog_frame, height=18, corner_radius=6
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 8))
        self.progress_bar.set(0)

        # Step counter label
        self.lbl_step = ctk.CTkLabel(
            prog_frame,
            text=f"Step 0 of {self._total_modules}",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        )
        self.lbl_step.pack(pady=(0, 15), padx=20, anchor="e")

        # --- MODULE PIPELINE DISPLAY ---
        pipeline_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=8)
        pipeline_frame.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(
            pipeline_frame,
            text="Module Pipeline:",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(10, 6))

        modules_row = ctk.CTkFrame(pipeline_frame, fg_color="transparent")
        modules_row.pack(fill="x", padx=15, pady=(0, 10))

        self.module_labels = []
        for i, (name, _) in enumerate(self._active_modules):
            lbl = ctk.CTkLabel(
                modules_row,
                text=name,
                font=(res.FONT_LABEL[0], 10),
                text_color="#555555",
                fg_color="#2a2a2a",
                corner_radius=4,
                padx=6, pady=3
            )
            lbl.pack(side="left", padx=3)
            self.module_labels.append(lbl)

        # --- LIVE LOG CONSOLE ---
        ctk.CTkLabel(
            self,
            text="Live Console Output:",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="gray"
        ).pack(anchor="w", padx=25, pady=(0, 4))

        self.log_box = ctk.CTkTextbox(
            self,
            fg_color="#0d0d0d",
            text_color="#00ff88",
            font=("Courier", 11),
            corner_radius=6,
            border_width=1,
            border_color="#333333"
        )
        self.log_box.pack(fill="both", expand=True, padx=25, pady=(0, 10))
        self.log_box.configure(state="disabled")

        # --- BOTTOM BAR ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=60)
        self.bottom_frame.pack(fill="x", side="bottom")
        self.bottom_frame.pack_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            self.bottom_frame,
            text="Simulation initializing...",
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        )
        self.lbl_status.pack(side="left", padx=20, pady=15)

        # Results button — hidden until simulation completes
        self.btn_results = ctk.CTkButton(
            self.bottom_frame,
            text="View Results",
            height=36,
            fg_color=res.COLOR_SUCCESS,
            state="disabled",
            command=self._show_results_location
        )
        self.btn_results.pack(side="right", padx=20, pady=12)

        # Retry button — hidden until an error occurs
        self.btn_retry = ctk.CTkButton(
            self.bottom_frame,
            text="Retry Simulation",
            height=36,
            fg_color=res.COLOR_ERROR,
            state="disabled",
            command=self._retry_simulation
        )
        self.btn_retry.pack(side="right", padx=(0, 10), pady=12)

        # Back to Dashboard — always visible, lets user exit on failure
        self.btn_dashboard = ctk.CTkButton(
            self.bottom_frame,
            text="← Back to Dashboard",
            height=36,
            fg_color="#333333",
            hover_color="#444444",
            text_color="white",
            command=self._go_to_dashboard
        )
        self.btn_dashboard.pack(side="left", padx=(10, 0), pady=12)

    # ------------------------------------------------------------------
    # SIMULATION CONTROL
    # ------------------------------------------------------------------

    def _start_simulation(self):
        """
        Step 1: Generate and save the XML file.
        Step 2: Launch BBP in a background thread via WSLBridge.
        """
        self._log("=" * 60)
        self._log(f"BBP Simulation Starting")
        self._log(f"Method      : {self._method}")
        self._log(f"Experiment  : {self.base_name}")
        self._log(f"Session     : {AppConfig.current_session_folder}")
        self._log(f"Source file : {self.src_path}")
        self._log(f"Station file: {self.stl_path}")
        self._log("=" * 60)
        self._log("")

        # --- GENERATE XML ---
        self._log("Generating XML options file...")
        ok, result = save_xml(
            self.base_name,
            self.src_path,
            self.stl_path,
            profile=self._profile,
            custom_modules=self._custom_modules if self._custom_modules else None,
            method=self._method
        )

        if not ok:
            self._on_error("XML Generation", result)
            return

        self._xml_path = result
        self._log(f"XML saved to: {self._xml_path}")
        self._log("")

        # Update title to show XML is ready
        self.title("BBP Simulation — Running")

        # --- LAUNCH BBP ---
        self._log("Launching BBP simulation...")
        self._log("")

        WSLBridge.run_bbp_simulation_stream(
            xml_path            = self._xml_path,
            session_output_path = AppConfig.out_path,
            on_output           = self._on_bbp_output,
            on_finish           = self._on_bbp_finish
        )

    def _retry_simulation(self):
        """Resets the panel state and reruns the simulation from scratch."""
        self._current_module  = 0
        self._failed_module   = None
        self._simulation_done = False

        self.progress_bar.set(0)
        self.lbl_module.configure(text="Retrying simulation...", text_color="white")
        self.lbl_desc.configure(text="Restarting from the beginning...")
        self.lbl_step.configure(text=f"Step 0 of {self._total_modules}")
        self.lbl_status.configure(text="Retrying...", text_color="gray")

        for lbl in self.module_labels:
            lbl.configure(text_color="#555555", fg_color="#2a2a2a")

        self.btn_retry.configure(state="disabled")
        self.btn_results.configure(state="disabled")

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.after(300, self._start_simulation)

    # ------------------------------------------------------------------
    # BBP OUTPUT HANDLER
    # ------------------------------------------------------------------

    def _on_bbp_output(self, line):
        """
        Called for every line of BBP stdout output.
        Detects which module is running and updates the progress bar.
        Must schedule GUI updates via self.after() since this runs in a thread.
        """
        self.after(0, lambda: self._process_line(line))

    def _process_line(self, line):
        """Processes a BBP output line on the main thread."""
        stripped = line.strip()
        if not stripped:
            return

        self._log(stripped)

        # Detect module start from BBP output. BBP prints module banners
        # like "-------NAME-------" and/or "==> Running NAME..." rather
        # than the "Starting module NAME" style originally assumed here —
        # confirmed against real GP and ExSIM run logs. Some modules
        # print a banner that differs from their internal module name
        # (e.g. Plot_Map prints "Plot MAP", RotD100 prints "RotDXX"),
        # so explicit aliases are used for those rather than relying on
        # name matching alone.
        banner_aliases = {
            "Plot_Map": ["PLOT MAP", "PLOTMAP"],
            "RotD100" : ["ROTDXX", "ROTD100"],
            "ExSim"   : ["EXSIM"],
        }

        stripped_upper = stripped.upper()
        compact_upper  = stripped_upper.replace("-", "").replace(" ", "")
        for i, (module_name, module_desc) in enumerate(self._active_modules):
            if i < self._current_module:
                continue
            name_upper = module_name.upper()
            candidates = [name_upper] + banner_aliases.get(module_name, [])
            if any(c.replace("_", "") in compact_upper for c in candidates) \
               or f"RUNNING {name_upper}" in stripped_upper \
               or f"{name_upper}:" in stripped_upper:
                self._current_module = i
                self._update_progress(i, module_name, module_desc)
                break

    def _update_progress(self, step_index, module_name, module_desc):
        """Updates progress bar and module labels for the given step."""
        progress = (step_index + 1) / self._total_modules

        self.progress_bar.set(progress)
        self.lbl_module.configure(
            text=f"Running: {module_name}",
            text_color=res.COLOR_SUCCESS
        )
        self.lbl_desc.configure(text=module_desc, text_color="white")
        self.lbl_step.configure(
            text=f"Step {step_index + 1} of {self._total_modules}"
        )
        self.lbl_status.configure(
            text=f"Running {module_name}...",
            text_color=res.COLOR_SUCCESS
        )

        # Update pipeline label colors
        for i, lbl in enumerate(self.module_labels):
            if i < step_index:
                lbl.configure(text_color=res.COLOR_SUCCESS, fg_color="#0d2a1a")
            elif i == step_index:
                lbl.configure(text_color="white", fg_color=res.COLOR_PRIMARY)
            else:
                lbl.configure(text_color="#555555", fg_color="#2a2a2a")

    # ------------------------------------------------------------------
    # COMPLETION HANDLERS
    # ------------------------------------------------------------------

    def _on_bbp_finish(self, success, error_msg, run_id):
        """
        Called when BBP process ends.
        Scheduled on main thread via self.after().
        """
        self.after(0, lambda: self._handle_finish(success, error_msg, run_id))

    def _handle_finish(self, success, error_msg, run_id):
        """Handles simulation completion on the main thread."""
        if success:
            self._simulation_done = True

            # Store run ID in AppConfig
            AppConfig.current_run_id = run_id

            # Point out_path directly to BBP_DATA_DIR/outdata/<run_id>
            # This is where BBP actually saves all results
            bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
            if not bbp_data:
                bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"
            AppConfig.out_path = f"{bbp_data}/outdata/{run_id}"

            # Fill progress bar to 100%
            self.progress_bar.set(1.0)

            # Mark all modules complete
            for lbl in self.module_labels:
                lbl.configure(text_color=res.COLOR_SUCCESS, fg_color="#0d2a1a")

            self.lbl_module.configure(
                text="Simulation Complete",
                text_color=res.COLOR_SUCCESS
            )
            self.lbl_desc.configure(
                text="All modules finished successfully.",
                text_color=res.COLOR_SUCCESS
            )
            self.lbl_step.configure(
                text=f"Step {self._total_modules} of {self._total_modules}"
            )
            self.lbl_status.configure(
                text="BBP simulation finished successfully.",
                text_color=res.COLOR_SUCCESS
            )
            self.title("BBP Simulation — Complete")

            self._log("")
            self._log("=" * 60)
            self._log("SIMULATION COMPLETED SUCCESSFULLY")
            self._log(f"BBP Run ID  : {run_id}")
            self._log(f"Results in  : {AppConfig.out_path}")
            self._log("=" * 60)

            self.btn_results.configure(state="normal")
            self._restore_par_defaults()

        else:
            failed = self._failed_module or "Unknown module"
            self._on_error(failed, error_msg)

    def _on_error(self, module_name, error_msg):
        """Handles a simulation error — shows message and enables retry."""
        self.progress_bar.configure(progress_color=res.COLOR_ERROR)
        self.lbl_module.configure(
            text=f"Error in module: {module_name}",
            text_color=res.COLOR_ERROR
        )
        self.lbl_desc.configure(
            text=error_msg if error_msg else "An unexpected error occurred.",
            text_color=res.COLOR_ERROR
        )
        self.lbl_status.configure(
            text=f"Simulation failed at: {module_name}",
            text_color=res.COLOR_ERROR
        )
        self.title("BBP Simulation — Failed")

        self._log("")
        self._log("=" * 60)
        self._log(f"SIMULATION FAILED — Module: {module_name}")
        self._log(f"Error: {error_msg}")
        self._log("=" * 60)

        self.btn_retry.configure(state="normal")
        self._restore_par_defaults()

    # ------------------------------------------------------------------
    # GO TO DASHBOARD
    # ------------------------------------------------------------------

    def _go_to_dashboard(self):
        """Restores par defaults then navigates back to the Dashboard."""
        self._restore_par_defaults()
        if self._on_dashboard_callback:
            self._on_dashboard_callback()
        self.after(200, self.destroy)

    def _restore_par_defaults(self):
        """
        Restores labasin_exsim.par to clean template state and
        crustal_amps.txt to original California values after every
        simulation — success or failure.
        """
        home = WSLBridge.get_wsl_home()
        par_path = f"{home}/bbp_gf/LABasin500/uwo/labasin_exsim.par"

        ok, content_par = WSLBridge.read_wsl_file(par_path)
        if not ok or not content_par:
            return

        import re as _re
        lines = content_par.splitlines()
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Restore Q factor
            if _re.match(r'^\s*\d+\.?\d*\s+\d+\.?\d*\s+\d*\.?\d+\s*$', stripped)                     and i > 0 and "Quality factor" in lines[i-1]:
                new_lines.append("  600  680.0  0.35")
                i += 1
                continue

            # Restore beta/rho
            if _re.match(r'^\s*\d+\.?\d*\s+\d+\.?\d*\s*$', stripped)                     and i > 0 and ("beta" in lines[i-1].lower() or "rho" in lines[i-1].lower()):
                new_lines.append("  3.7  2.8")
                i += 1
                continue

            # Restore G(R) to default bilinear
            if _re.match(r'^\s*\d+\s*$', stripped)                     and i > 0                     and ("r_ref" in lines[i-1].lower() or "nseg" in lines[i-1].lower()):
                original_nseg = int(stripped.strip())
                new_lines.append("    2")
                new_lines.append("      1.0 -1.0")
                new_lines.append("     40.0 -0.5")
                i += 1 + original_nseg
                continue

            # Restore D(R) to default 2-hinge
            if _re.match(r'^\s*\d+\s*$', stripped)                     and i > 0                     and "duration" in lines[i-1].lower():
                original_ndur = int(stripped.strip())
                new_lines.append("    2")
                new_lines.append("    0.0 1.0")
                new_lines.append("   50.0 10.0")
                new_lines.append("  0.05")
                i += 1 + original_ndur
                continue

            # Restore islipweight to 1 (Random)
            if _re.match(r'^\s*-?[01]\s*$', stripped)                     and i > 0 and "random weights" in lines[i-1].lower():
                new_lines.append("   1")
                i += 1
                continue

            new_lines.append(line)
            i += 1

        WSLBridge.write_wsl_file(par_path, "\n".join(new_lines) + "\n")

        # Restore crustal_amps.txt to original LABasin500 content.
        # CRITICAL FORMAT: after ! comment lines, Fortran reads ONE INTEGER
        # (the count of data pairs), then that many frequency/amp pairs.
        amp_path = f"{home}/bbp_gf/LABasin500/uwo/crustal_amps.txt"
        california_content = (
            "! Crustal amplification for LABasin500\n"
            "! Frequency(Hz)   Amplification\n"
            " 9\n"
            "  0.1    1.00\n"
            "  0.2    1.01\n"
            "  0.5    1.04\n"
            "  1.0    1.07\n"
            "  2.0    1.10\n"
            "  5.0    1.15\n"
            " 10.0    1.18\n"
            " 20.0    1.20\n"
            " 50.0    1.20\n"
        )
        WSLBridge.write_wsl_file(amp_path, california_content)

    # ------------------------------------------------------------------
    # RESULTS LOCATION
    # ------------------------------------------------------------------

    def _show_results_location(self):
        """Opens ResultsPanel via MainPanel callback, then destroys self."""
        if self._on_results_callback:
            self._on_results_callback()
        self.after(500, self.destroy)

    # ------------------------------------------------------------------
    # LOG HELPER
    # ------------------------------------------------------------------

    def _log(self, text):
        """Appends a line to the console log box."""
        try:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass