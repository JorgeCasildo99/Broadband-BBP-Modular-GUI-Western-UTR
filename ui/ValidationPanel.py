# ValidationPanel.py — ui/ValidationPanel.py
# -------------------------------------------------------
# Panel for configuring and running BBP validation
# simulations against historical earthquake events.
# Mirrors BBP's interactive question flow but in a
# clean GUI, detecting available events from installed
# velocity models automatically.
# -------------------------------------------------------

import customtkinter as ctk
import threading
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge       import WSLBridge
from core.ValidationEvents import (
    get_events_with_status,
    VALIDATION_METHODS,
    VALIDATION_MODULES,
)


class ValidationPanel(ctk.CTkToplevel):
    """
    Full window for selecting and running BBP validation simulations.
    Detects available events from installed velocity models,
    lets the user configure the run, then launches BBP and
    streams live output — exactly mirroring the BBP interactive flow.
    """

    def __init__(self, master, on_results_callback=None):
        super().__init__(master)

        self._on_results_callback = on_results_callback
        self._events              = []
        self._selected_event      = None
        self._selected_method     = VALIDATION_METHODS[0]  # GP default
        self._simulation_running  = False
        self._run_id              = ""

        self.title("BBP Validation Simulation")
        self.geometry("1200x800")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)
        self.after(100, lambda: self.wm_attributes('-zoomed', True))

        self._back_callback = getattr(master, 'load_dashboard', None)

        self._build_ui()
        self.after(200, self._on_ready)
        self.after(400, self._load_events)

    def _on_ready(self):
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):

        # ── TOP BAR ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="#0d0d0d",
                           corner_radius=0, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkButton(
            top,
            text="← Back to Dashboard",
            width=160, height=30,
            fg_color="transparent",
            border_width=1,
            border_color="#444444",
            text_color="white",
            hover_color="#2a2a2a",
            command=self.destroy
        ).pack(side="left", padx=10, pady=13)

        ctk.CTkLabel(
            top,
            text="BBP Validation Simulation  —  Simulates a historical earthquake and compares against real recordings",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(side="left", padx=10, pady=14)

        ctk.CTkLabel(
            top,
            text="GP Method  —  LABasin500",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="right", padx=20)

        # ── INFO BAR ─────────────────────────────────────────────────
        info = ctk.CTkFrame(self, fg_color="#111111",
                            corner_radius=0, height=32)
        info.pack(fill="x")
        info.pack_propagate(False)

        self.lbl_scan = ctk.CTkLabel(
            info,
            text="Scanning installed velocity models...",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        )
        self.lbl_scan.pack(side="left", padx=16, pady=6)

        self.lbl_count = ctk.CTkLabel(
            info,
            text="",
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color=res.COLOR_SUCCESS
        )
        self.lbl_count.pack(side="right", padx=16)

        # ── MAIN SPLIT LAYOUT ────────────────────────────────────────
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=10)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=5)
        main.grid_rowconfigure(0, weight=1)

        # ── LEFT: EVENT LIST + METHOD ─────────────────────────────────
        left = ctk.CTkFrame(main, fg_color="#111111", corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Event list header
        ev_header = ctk.CTkFrame(left, fg_color="transparent")
        ev_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(
            ev_header,
            text="VALIDATION EVENTS",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color="#666666"
        ).pack(side="left")

        ctk.CTkLabel(
            ev_header,
            text="● available  ○ missing model",
            font=(res.FONT_LABEL[0], 9),
            text_color="#444444"
        ).pack(side="right")

        # Scrollable event list
        self._event_scroll = ctk.CTkScrollableFrame(
            left, fg_color="transparent"
        )
        self._event_scroll.grid(row=1, column=0, sticky="nsew", padx=8)

        # Loading placeholder
        self._event_placeholder = ctk.CTkLabel(
            self._event_scroll,
            text="Scanning WSL for installed models...",
            font=(res.FONT_LABEL[0], 11),
            text_color="#444444"
        )
        self._event_placeholder.pack(pady=20)

        # Method selector — visual cards
        ctk.CTkLabel(
            left,
            text="SIMULATION METHOD",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color="#666666"
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(12, 4))

        self._method_frame = ctk.CTkScrollableFrame(
            left, fg_color="transparent", height=160
        )
        self._method_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))

        self._method_buttons = {}
        self._method_var = ctk.StringVar(value=VALIDATION_METHODS[0]["name"])

        for method in VALIDATION_METHODS:
            is_gp = method["short"] == "GP"
            btn = ctk.CTkButton(
                self._method_frame,
                text=f"  {method['name']}",
                height=36,
                anchor="w",
                fg_color=res.COLOR_PRIMARY if is_gp else "#1e1e1e",
                hover_color="#004070",
                border_width=1,
                border_color=res.COLOR_PRIMARY if is_gp else "#2a2a2a",
                font=(res.FONT_LABEL[0], 12),
                command=lambda m=method: self._select_method(m)
            )
            btn.pack(fill="x", padx=2, pady=2)
            self._method_buttons[method["name"]] = btn

        # Run button
        self._btn_run = ctk.CTkButton(
            left,
            text="▶  Run Validation",
            height=42,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            font=(res.FONT_LABEL[0], 13, "bold"),
            state="disabled",
            command=self._confirm_and_run
        )
        self._btn_run.grid(row=4, column=0, sticky="ew",
                           padx=10, pady=(4, 10))

        # ── RIGHT: EVENT DETAIL + CONSOLE ────────────────────────────
        right = ctk.CTkFrame(main, fg_color="#111111", corner_radius=8)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=3)   # detail gets 3 parts
        right.grid_rowconfigure(2, weight=2)   # console gets 2 parts
        right.grid_columnconfigure(0, weight=1)

        # Detail panel (top right) — expands vertically
        self._detail_frame = ctk.CTkScrollableFrame(
            right, fg_color="transparent"
        )
        self._detail_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self._show_detail_placeholder()

        # Console label
        ctk.CTkLabel(
            right,
            text="SIMULATION CONSOLE",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color="#444444"
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(4, 2))

        self._console = ctk.CTkTextbox(
            right,
            fg_color="#0d0d0d",
            text_color="#00ff88",
            font=("Courier", 10),
            border_width=1,
            border_color="#222222",
            state="disabled"
        )
        self._console.grid(row=2, column=0, sticky="nsew",
                           padx=10, pady=(0, 4))

        # Progress bar
        self._progress_frame = ctk.CTkFrame(
            right, fg_color="transparent"
        )
        self._progress_frame.grid(row=3, column=0, sticky="ew",
                                  padx=10, pady=(0, 4))

        self._progress_bar = ctk.CTkProgressBar(
            self._progress_frame, height=6,
            fg_color="#222222",
            progress_color=res.COLOR_PRIMARY
        )
        self._progress_bar.pack(fill="x")
        self._progress_bar.set(0)

        self._lbl_module = ctk.CTkLabel(
            self._progress_frame,
            text="Waiting to start...",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        )
        self._lbl_module.pack(anchor="w", pady=(2, 0))

        # Status + View Results button
        bottom = ctk.CTkFrame(right, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        self._lbl_status = ctk.CTkLabel(
            bottom,
            text="Select an event from the list to begin.",
            font=(res.FONT_LABEL[0], 11),
            text_color="#555555"
        )
        self._lbl_status.pack(side="left")

        self._btn_results = ctk.CTkButton(
            bottom,
            text="View Results →",
            width=140, height=34,
            fg_color=res.COLOR_SUCCESS,
            hover_color="#009070",
            font=(res.FONT_LABEL[0], 11, "bold"),
            state="disabled",
            command=self._open_results
        )
        self._btn_results.pack(side="right")

    # ------------------------------------------------------------------
    # EVENT LOADING
    # ------------------------------------------------------------------

    def _load_events(self):
        """Scans WSL for installed models and builds the event list."""
        def _scan():
            events = get_events_with_status()
            self.after(0, lambda: self._on_events_loaded(events))

        threading.Thread(target=_scan, daemon=True).start()

    def _on_events_loaded(self, events):
        self._events = events

        available = [e for e in events if e["available"] and e["val_files_ok"]]
        missing   = [e for e in events if not e["available"]]

        self._event_placeholder.destroy()

        self.lbl_scan.configure(
            text=f"GF Directory: {WSLBridge.get_wsl_home()}/bbp_gf",
            text_color="#333333"
        )
        self.lbl_count.configure(
            text=f"{len(available)} available  |  {len(missing)} require model install  |  {len(events)} total"
        )

        # Sort: available first, then missing — show ALL events like BBP does
        sorted_events = (
            [e for e in events if e["available"] and e["val_files_ok"]] +
            [e for e in events if not (e["available"] and e["val_files_ok"])]
        )

        for event in sorted_events:
            self._add_event_row(event)

        # Auto-select first available event
        if available:
            self._select_event(available[0])

    def _add_event_row(self, event):
        """Adds a clickable event row to the list."""
        available = event["available"] and event["val_files_ok"]

        bg     = "#0d1a0d" if available else "#141414"
        border = "#1e3a1e" if available else "#222222"
        t_name = res.COLOR_SUCCESS if available else "#444444"
        t_sub  = "#555555" if available else "#333333"
        badge  = "● AVAILABLE" if available else f"○ NEEDS {event['missing_model']}"
        b_col  = res.COLOR_SUCCESS if available else "#333333"

        row = ctk.CTkFrame(
            self._event_scroll,
            fg_color=bg, corner_radius=6,
            border_width=1, border_color=border
        )
        row.pack(fill="x", pady=2)

        top_row = ctk.CTkFrame(row, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(6, 1))

        ctk.CTkLabel(
            top_row,
            text=event["name"],
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color=t_name
        ).pack(side="left")

        ctk.CTkLabel(
            top_row,
            text=badge,
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color=b_col
        ).pack(side="right")

        bot_row = ctk.CTkFrame(row, fg_color="transparent")
        bot_row.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            bot_row,
            text=f"{event['magnitude']}  |  {event['region']}",
            font=(res.FONT_LABEL[0], 10),
            text_color=t_sub
        ).pack(side="left")

        ctk.CTkLabel(
            bot_row,
            text=f"{event['stations']} stations",
            font=(res.FONT_LABEL[0], 10),
            text_color=t_sub
        ).pack(side="right")

        # Only make available events clickable
        if available:
            for w in [row, top_row, bot_row]:
                w.bind("<Button-1>",
                       lambda e, ev=event, r=row: self._select_event(ev, r))
                w.configure(cursor="hand2")

        event["_row_widget"] = row

    def _select_event(self, event, row_widget=None):
        """Highlights selected event and updates detail panel."""
        # Reset all row borders
        for ev in self._events:
            if "_row_widget" in ev:
                try:
                    ev["_row_widget"].configure(border_color="#1e3a1e")
                except Exception:
                    pass

        # Highlight selected
        if row_widget:
            row_widget.configure(border_color="white")
        elif "_row_widget" in event:
            event["_row_widget"].configure(border_color="white")

        self._selected_event = event
        self._show_detail(event)
        self._btn_run.configure(state="normal")

    # ------------------------------------------------------------------
    # DETAIL PANEL
    # ------------------------------------------------------------------

    def _show_detail_placeholder(self):
        ctk.CTkLabel(
            self._detail_frame,
            text="← Select a validation event to see details",
            font=(res.FONT_LABEL[0], 13),
            text_color="#333333"
        ).pack(pady=40)

    def _show_detail(self, event):
        for w in self._detail_frame.winfo_children():
            w.destroy()

        # Header
        hdr = ctk.CTkFrame(
            self._detail_frame,
            fg_color="#0d1a0d", corner_radius=8,
            border_width=1, border_color="#1e3a1e"
        )
        hdr.pack(fill="x", pady=(0, 10))

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            title_row,
            text=event["name"],
            font=(res.FONT_LABEL[0], 16, "bold"),
            text_color="white"
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=event["magnitude"],
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color=res.COLOR_SUCCESS
        ).pack(side="right")

        ctk.CTkLabel(
            hdr,
            text=event["description"],
            font=(res.FONT_LABEL[0], 11),
            text_color="#aaaaaa",
            wraplength=560,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # Specs grid
        self._section_label("Event Specifications")

        specs = ctk.CTkFrame(
            self._detail_frame, fg_color="#1a1a1a",
            corner_radius=6, border_width=1, border_color="#2a2a2a"
        )
        specs.pack(fill="x", pady=(0, 10))
        specs.grid_columnconfigure((1, 3), weight=1)

        fields = [
            ("Date",              event.get("date", "N/A")),
            ("Magnitude",         event["magnitude"]),
            ("Region",            event["region"]),
            ("Depth",             f"{event['depth_km']} km"),
            ("Stations",          str(event["stations"])),
            ("Required Model",    event["required_model"]),
            ("BBP Event Number",  str(event["bbp_number"])),
            ("BBP Folder",        event.get("bbp_folder", "N/A")),
            ("SRC File",          event.get("src_file", "N/A")),
            ("STL File",          event.get("stl_file", "N/A")),
            ("SRC Full Path",     event.get("src_path", "N/A")),
            ("STL Full Path",     event.get("stl_path", "N/A")),
        ]

        for i, (label, value) in enumerate(fields):
            r, c = i // 2, (i % 2) * 2
            ctk.CTkLabel(
                specs,
                text=f"{label}:",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="#666666"
            ).grid(row=r, column=c, padx=(14, 6), pady=6, sticky="w")
            ctk.CTkLabel(
                specs,
                text=str(value),
                font=(res.FONT_LABEL[0], 11),
                text_color="white",
                wraplength=220
            ).grid(row=r, column=c+1, padx=(0, 14), pady=6, sticky="w")

        # File status
        self._section_label("Validation Files Status")

        fstatus = ctk.CTkFrame(
            self._detail_frame, fg_color="#1a1a1a",
            corner_radius=6, border_width=1, border_color="#2a2a2a"
        )
        fstatus.pack(fill="x", pady=(0, 10))

        files_ok = event.get("val_files_ok", False)
        model_ok = event.get("available", False)

        status_items = [
            (
                f"Velocity model ({event['required_model']})",
                "✓  Installed" if model_ok else "✗  Not installed",
                res.COLOR_SUCCESS if model_ok else res.COLOR_ERROR
            ),
            (
                "SRC fault parameters",
                "✓  Found" if files_ok else "✗  Not found",
                res.COLOR_SUCCESS if files_ok else res.COLOR_ERROR
            ),
            (
                "STL station list",
                "✓  Found" if files_ok else "✗  Not found",
                res.COLOR_SUCCESS if files_ok else res.COLOR_ERROR
            ),
        ]

        for label, status, color in status_items:
            row = ctk.CTkFrame(fstatus, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(
                row, text=label,
                font=(res.FONT_LABEL[0], 11),
                text_color="#aaaaaa"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=status,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=color
            ).pack(side="right")

        ctk.CTkFrame(fstatus, fg_color="transparent", height=6).pack()

        # SRC file content preview
        if event.get("val_files_ok") and event.get("src_path"):
            self._section_label("Source Parameters (.src preview)")

            src_frame = ctk.CTkFrame(
                self._detail_frame, fg_color="#0d0d0d",
                corner_radius=6, border_width=1, border_color="#222222"
            )
            src_frame.pack(fill="x", pady=(0, 10))

            # Read SRC file from WSL
            ok, content = WSLBridge.read_wsl_file(event["src_path"])
            if ok and content.strip():
                # Show first 30 lines
                lines   = content.strip().splitlines()
                preview = "\n".join(lines[:30])
                if len(lines) > 30:
                    preview += f"\n... ({len(lines) - 30} more lines)"
            else:
                preview = "Could not read SRC file."

            src_box = ctk.CTkTextbox(
                src_frame,
                fg_color="#0d0d0d",
                text_color="#44ff88",
                font=("Courier", 9),
                height=160,
                border_width=0
            )
            src_box.pack(fill="x", padx=6, pady=6)
            src_box.insert("1.0", preview)
            src_box.configure(state="disabled")
        self._section_label("Validation Pipeline")

        pipe_frame = ctk.CTkFrame(
            self._detail_frame, fg_color="#1a1a1a",
            corner_radius=6, border_width=1, border_color="#2a2a2a"
        )
        pipe_frame.pack(fill="x", pady=(0, 10))

        pipeline_text = (
            "Genslip → Jbsim → Hfsims → WccSiteamp → Match → "
            "Plot_Map → PlotSeis → RotD100 → RotD50 GoF → FAS → FAS GoF → GenHTML"
        )
        ctk.CTkLabel(
            pipe_frame,
            text=pipeline_text,
            font=("Courier", 9),
            text_color="#555555",
            wraplength=560,
            justify="left"
        ).pack(anchor="w", padx=14, pady=10)

    def _section_label(self, text):
        frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        frame.pack(fill="x", pady=(6, 2))
        ctk.CTkLabel(
            frame, text=text,
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(side="left")
        sep = ctk.CTkFrame(frame, fg_color="#2a2a2a", height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)

    # ------------------------------------------------------------------
    # METHOD SELECTION
    # ------------------------------------------------------------------

    def _select_method(self, method):
        """Highlights selected method button and stores selection."""
        for name, btn in self._method_buttons.items():
            if name == method["name"]:
                btn.configure(
                    fg_color=res.COLOR_PRIMARY,
                    border_color=res.COLOR_PRIMARY
                )
            else:
                btn.configure(
                    fg_color="#1e1e1e",
                    border_color="#2a2a2a"
                )
        self._selected_method = method
        self._method_var.set(method["name"])

    def _on_method_changed(self, value):
        for m in VALIDATION_METHODS:
            if m["name"] == value:
                self._selected_method = m
                break

    # ------------------------------------------------------------------
    # RUN CONFIRMATION
    # ------------------------------------------------------------------

    def _safe_grab(self, window):
        """Safely grabs focus after window is fully rendered."""
        try:
            window.grab_set()
            window.lift()
            window.focus_force()
        except Exception:
            pass

    def _confirm_and_run(self):
        if not self._selected_event:
            return
        if self._simulation_running:
            return

        event  = self._selected_event
        method = self._selected_method

        # Confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Validation Run")
        dialog.geometry("460x240")
        dialog.configure(fg_color="#1a1a1a")
        dialog.transient(self)
        dialog.after(150, lambda: self._safe_grab(dialog))

        ctk.CTkLabel(
            dialog,
            text="Confirm Validation Simulation",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color="white"
        ).pack(pady=(20, 8))

        ctk.CTkLabel(
            dialog,
            text=(
                f"Event:   {event['name']}  ({event['magnitude']})\n"
                f"Method:  {method['name']}\n"
                f"Model:   {event['required_model']}\n"
                f"Stations: {event['stations']}"
            ),
            font=(res.FONT_LABEL[0], 12),
            text_color="#aaaaaa",
            justify="left"
        ).pack(padx=30, pady=4)

        ctk.CTkLabel(
            dialog,
            text="This simulation may take 10–60 minutes depending on station count.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        ).pack(pady=4)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=12)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=110, height=34,
            fg_color="#333333",
            hover_color="#444444",
            command=dialog.destroy
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="▶  Start Simulation",
            width=150, height=34,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            command=lambda: (dialog.destroy(), self._start_run())
        ).pack(side="left", padx=8)

    # ------------------------------------------------------------------
    # RUN
    # ------------------------------------------------------------------

    def _start_run(self):
        if not self._selected_event or not self._selected_method:
            return

        self._simulation_running = True
        self._btn_run.configure(state="disabled", text="Running...")
        self._btn_results.configure(state="disabled")
        self._progress_bar.set(0)
        self._current_module_idx = 0

        self._console_clear()
        self._console_write(
            f"Starting BBP validation: {self._selected_event['name']}\n"
            f"Method: {self._selected_method['name']}\n"
            f"{'='*60}\n"
        )

        self._lbl_status.configure(
            text="Simulation running...",
            text_color="white"
        )

        WSLBridge.run_validation_stream(
            event_number  = self._selected_event["bbp_number"],
            method_number = self._selected_method["bbp_number"],
            on_output     = self._on_output,
            on_finish     = self._on_finish
        )

    # ------------------------------------------------------------------
    # STREAMING OUTPUT HANDLERS
    # ------------------------------------------------------------------

    def _on_output(self, line):
        """Called from background thread for each output line."""
        self.after(0, lambda l=line: self._handle_output(l))

    def _handle_output(self, line):
        self._console_write(line)
        self._detect_module_progress(line)

    def _detect_module_progress(self, line):
        """Updates progress bar by detecting BBP module header lines."""
        total = len(VALIDATION_MODULES)
        for idx, (module_name, module_desc) in enumerate(VALIDATION_MODULES):
            if module_name.lower() in line.lower() and (
                "running" in line.lower() or
                "completed" in line.lower() or
                "processing" in line.lower() or
                "---" in line
            ):
                progress = (idx + 1) / total
                self._progress_bar.set(progress)
                self._lbl_module.configure(
                    text=f"[{idx+1}/{total}] {module_desc}",
                    text_color=res.COLOR_SUCCESS
                )
                break

    def _on_finish(self, success, error_msg, run_id):
        """Called from background thread when BBP finishes."""
        self.after(0, lambda: self._handle_finish(success, error_msg, run_id))

    def _handle_finish(self, success, error_msg, run_id):
        self._simulation_running = False
        self._run_id = run_id

        if success:
            self._progress_bar.set(1.0)
            self._progress_bar.configure(progress_color=res.COLOR_SUCCESS)
            self._lbl_module.configure(
                text="Simulation completed successfully.",
                text_color=res.COLOR_SUCCESS
            )
            self._lbl_status.configure(
                text=f"✓  Run ID: {run_id}   Results in ~/bbp_data/outdata/{run_id}/",
                text_color=res.COLOR_SUCCESS
            )
            self._btn_results.configure(state="normal")
            self._btn_run.configure(
                state="normal", text="▶  Run Again"
            )
            self._console_write(
                f"\n{'='*60}\n"
                f"✓ Validation completed successfully.\n"
                f"Run ID: {run_id}\n"
                f"Results: ~/bbp_data/outdata/{run_id}/\n"
            )
        else:
            self._progress_bar.configure(progress_color=res.COLOR_ERROR)
            self._lbl_status.configure(
                text=f"✗  Simulation failed: {error_msg}",
                text_color=res.COLOR_ERROR
            )
            self._lbl_module.configure(
                text="Simulation failed — check console for details.",
                text_color=res.COLOR_ERROR
            )
            self._btn_run.configure(
                state="normal", text="▶  Run Again"
            )
            self._console_write(
                f"\n{'='*60}\n"
                f"✗ Simulation failed.\n{error_msg}\n"
            )

    # ------------------------------------------------------------------
    # CONSOLE HELPERS
    # ------------------------------------------------------------------

    def _console_clear(self):
        self._console.configure(state="normal")
        self._console.delete("1.0", "end")
        self._console.configure(state="disabled")

    def _console_write(self, text):
        self._console.configure(state="normal")
        self._console.insert("end", text)
        self._console.see("end")
        self._console.configure(state="disabled")

    # ------------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------------

    def _open_results(self):
        if self._on_results_callback and self._run_id:
            self._on_results_callback(self._run_id,
                                      self._selected_event)