# ConfigurationPanel.py — ui/ConfigurationPanel.py
# -------------------------------------------------------
# Panel for browsing, inspecting, and getting installation
# guidance for all BBP v22.4.0 velocity models.
# Source: https://github.com/SCECcode/bbp
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.VelocityModels import get_all_models_with_status, get_gf_dir


class ConfigurationPanel(ctk.CTkToplevel):
    """
    Popup window for browsing all BBP velocity models — installed and available.
    Shows detection results, full specs, validation events, and install guide.
    """

    def __init__(self, master):
        super().__init__(master)

        self.title("Velocity Model Configuration — BBP v22.4.0")
        self.geometry("1280x800")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._models         = []
        self._selected_model = None
        self._btn_map        = {}   # model name -> button widget

        self._build_ui()
        self.after(200, self._on_ready)
        self.after(300, self._load_models)

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

        # --- TOP BAR ---
        top = ctk.CTkFrame(self, fg_color="#0d0d0d", corner_radius=0, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(
            top,
            text="⚙  Velocity Model Configuration",
            font=(res.FONT_LABEL[0], 15, "bold"),
            text_color="white"
        ).pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            top,
            text="Source: github.com/SCECcode/bbp  —  BBP v22.4.0",
            font=(res.FONT_LABEL[0], 11),
            text_color="#555555"
        ).pack(side="right", padx=20)

        # --- STATS BAR ---
        self.stats_bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=36)
        self.stats_bar.pack(fill="x")
        self.stats_bar.pack_propagate(False)

        self.lbl_gf_path = ctk.CTkLabel(
            self.stats_bar,
            text=f"GF Directory: {get_gf_dir()}",
            font=("Courier", 10),
            text_color="#444444"
        )
        self.lbl_gf_path.pack(side="left", padx=16, pady=8)

        self.lbl_stats = ctk.CTkLabel(
            self.stats_bar,
            text="Scanning...",
            font=(res.FONT_LABEL[0], 11),
            text_color="#555555"
        )
        self.lbl_stats.pack(side="right", padx=16)

        # --- MAIN SPLIT LAYOUT ---
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=10)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=7)
        main.grid_rowconfigure(0, weight=1)

        # LEFT PANEL
        left = ctk.CTkFrame(main, fg_color="#111111", corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(2, weight=1)   # installed frame expands
        left.grid_rowconfigure(4, weight=2)   # available frame expands more
        left.grid_columnconfigure(0, weight=1)

        # Active model card
        active_card = ctk.CTkFrame(
            left, fg_color="#0d1f0d", corner_radius=6,
            border_width=1, border_color="#1e4a1e"
        )
        active_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            active_card,
            text="ACTIVE MODEL",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color="#44aa44"
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self.lbl_active_name = ctk.CTkLabel(
            active_card,
            text="Scanning...",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        )
        self.lbl_active_name.pack(anchor="w", padx=10, pady=(0, 2))

        self.lbl_active_region = ctk.CTkLabel(
            active_card,
            text="",
            font=(res.FONT_LABEL[0], 10),
            text_color="#666666"
        )
        self.lbl_active_region.pack(anchor="w", padx=10, pady=(0, 8))

        # Installed section
        ctk.CTkLabel(
            left,
            text="INSTALLED ON THIS DEVICE",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color="#44aa44"
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 2))

        self._installed_frame = ctk.CTkScrollableFrame(
            left, fg_color="transparent"
        )
        self._installed_frame.grid(row=2, column=0, sticky="nsew", padx=8)

        self._installed_placeholder = ctk.CTkLabel(
            self._installed_frame,
            text="Scanning WSL...",
            font=(res.FONT_LABEL[0], 11),
            text_color="#444444"
        )
        self._installed_placeholder.pack(pady=12)

        # Available section
        ctk.CTkLabel(
            left,
            text="AVAILABLE — NOT INSTALLED",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color="#666666"
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(10, 2))

        self._available_frame = ctk.CTkScrollableFrame(
            left, fg_color="transparent"
        )
        self._available_frame.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self._available_placeholder = ctk.CTkLabel(
            self._available_frame,
            text="Scanning WSL...",
            font=(res.FONT_LABEL[0], 11),
            text_color="#444444"
        )
        self._available_placeholder.pack(pady=12)

        # Refresh button at bottom of left panel
        ctk.CTkButton(
            left,
            text="⟳  Refresh Detection",
            height=32,
            fg_color="#1e1e1e",
            hover_color="#2a2a2a",
            border_width=1,
            border_color="#333333",
            font=(res.FONT_LABEL[0], 11),
            command=self._refresh
        ).grid(row=5, column=0, sticky="ew", padx=10, pady=(4, 10))

        # RIGHT PANEL
        self.right_scroll = ctk.CTkScrollableFrame(
            main, fg_color="#111111", corner_radius=8
        )
        self.right_scroll.grid(row=0, column=1, sticky="nsew")

        self._show_placeholder()

    # ------------------------------------------------------------------
    # MODEL LIST BUTTONS
    # ------------------------------------------------------------------

    def _add_model_btn(self, parent, model):
        is_installed = model["installed"]
        bg    = "#0d1a0d" if is_installed else "#1a1a1a"
        border= "#1e3a1e" if is_installed else "#2a2a2a"

        btn_frame = ctk.CTkFrame(
            parent, fg_color=bg, corner_radius=5,
            border_width=1, border_color=border
        )
        btn_frame.pack(fill="x", pady=2)
        btn_frame.configure(cursor="hand2")

        row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            row,
            text=model["name"],
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color=res.COLOR_SUCCESS if is_installed else "#888888"
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text="● INSTALLED" if is_installed else "○ NOT INSTALLED",
            font=(res.FONT_LABEL[0], 9, "bold"),
            text_color=res.COLOR_SUCCESS if is_installed else "#444444"
        ).pack(side="right")

        # Region + size row
        bottom_row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        bottom_row.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            bottom_row,
            text=model["region"],
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        ).pack(side="left")

        ctk.CTkLabel(
            bottom_row,
            text=model.get("install_size", ""),
            font=(res.FONT_LABEL[0], 10),
            text_color="#444444"
        ).pack(side="right")

        for w in [btn_frame, row, bottom_row]:
            w.bind("<Button-1>", lambda e, m=model: self._show_detail(m))

        self._btn_map[model["name"]] = btn_frame

    # ------------------------------------------------------------------
    # LOADING
    # ------------------------------------------------------------------

    def _load_models(self):
        def _scan():
            models = get_all_models_with_status()
            self.after(0, lambda: self._on_loaded(models))
        threading.Thread(target=_scan, daemon=True).start()

    def _on_loaded(self, models):
        self._models = models
        installed = [m for m in models if m["installed"]]
        available = [m for m in models if not m["installed"]]

        # Update stats bar
        self.lbl_stats.configure(
            text=f"{len(installed)} installed  |  {len(available)} available  |  {len(models)} total",
            text_color=res.COLOR_SUCCESS if installed else res.COLOR_ERROR
        )

        # Update active card
        if installed:
            self.lbl_active_name.configure(text=installed[0]["name"])
            self.lbl_active_region.configure(text=installed[0]["region"])
        else:
            self.lbl_active_name.configure(text="None detected", text_color=res.COLOR_ERROR)

        # Clear placeholders
        self._installed_placeholder.destroy()
        self._available_placeholder.destroy()

        # Populate installed
        if installed:
            for m in installed:
                self._add_model_btn(self._installed_frame, m)
        else:
            ctk.CTkLabel(
                self._installed_frame,
                text="No models found in ~/bbp_gf/",
                font=(res.FONT_LABEL[0], 11),
                text_color=res.COLOR_ERROR
            ).pack(pady=8)

        # Populate available
        for m in available:
            self._add_model_btn(self._available_frame, m)

        # Auto-select first installed
        if installed:
            self._show_detail(installed[0])

    # ------------------------------------------------------------------
    # DETAIL PANEL
    # ------------------------------------------------------------------

    def _show_placeholder(self):
        ctk.CTkLabel(
            self.right_scroll,
            text="← Select a model from the list to view details",
            font=(res.FONT_LABEL[0], 13),
            text_color="#333333"
        ).pack(expand=True, pady=100)

    def _show_detail(self, model):
        self._selected_model = model

        for w in self.right_scroll.winfo_children():
            w.destroy()

        is_inst      = model["installed"]
        status_color = res.COLOR_SUCCESS if is_inst else "#ff8800"
        status_text  = "✓  INSTALLED ON THIS DEVICE" if is_inst else "⚠  NOT INSTALLED"

        # --- HEADER ---
        hdr = ctk.CTkFrame(
            self.right_scroll,
            fg_color="#0d1a0d" if is_inst else "#1a1000",
            corner_radius=8,
            border_width=1,
            border_color="#1e3a1e" if is_inst else "#3a2800"
        )
        hdr.pack(fill="x", pady=(0, 10))

        top_row = ctk.CTkFrame(hdr, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            top_row,
            text=model["full_name"],
            font=(res.FONT_LABEL[0], 17, "bold"),
            text_color="white"
        ).pack(side="left")

        ctk.CTkLabel(
            top_row,
            text=status_text,
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color=status_color
        ).pack(side="right")

        ctk.CTkLabel(
            hdr,
            text=model["description"],
            font=(res.FONT_LABEL[0], 11),
            text_color="#aaaaaa",
            wraplength=620,
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 6))

        if model.get("note"):
            ctk.CTkLabel(
                hdr,
                text=f"ℹ  {model['note']}",
                font=(res.FONT_LABEL[0], 10),
                text_color="#888888",
                wraplength=620,
                justify="left"
            ).pack(anchor="w", padx=16, pady=(0, 12))
        else:
            ctk.CTkFrame(hdr, fg_color="transparent", height=8).pack()

        # --- SPECS GRID ---
        self._section_label("Model Specifications")

        specs = ctk.CTkFrame(
            self.right_scroll, fg_color="#1a1a1a",
            corner_radius=6, border_width=1, border_color="#2a2a2a"
        )
        specs.pack(fill="x", pady=(0, 10))
        specs.grid_columnconfigure((1, 3), weight=1)

        fields = [
            ("Model Name",          model["name"]),
            ("Install Size",        model.get("install_size", "Unknown")),
            ("Region",              model["region"]),
            ("Coverage Area",       model["coverage"]),
            ("GF Distance Range",   model["gf_distance"]),
            ("Vs30 Reference",      f"{model['vs30_ref']} m/s"),
            ("Supported Methods",   ", ".join(model["codebases"]) if model["codebases"] else "Unknown"),
            ("GF Config File",      model.get("config_file", "Unknown")),
        ]

        for i, (label, value) in enumerate(fields):
            r, c = i // 2, (i % 2) * 2
            ctk.CTkLabel(
                specs,
                text=f"{label}:",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="#666666"
            ).grid(row=r, column=c, padx=(14, 6), pady=7, sticky="w")
            ctk.CTkLabel(
                specs,
                text=str(value),
                font=(res.FONT_LABEL[0], 11),
                text_color="white"
            ).grid(row=r, column=c+1, padx=(0, 14), pady=7, sticky="w")

        # --- VALIDATION EVENTS ---
        events = model.get("validation_events", [])
        if events:
            self._section_label("Known Validation Events")
            ev_frame = ctk.CTkFrame(
                self.right_scroll, fg_color="#1a1a1a",
                corner_radius=6, border_width=1, border_color="#2a2a2a"
            )
            ev_frame.pack(fill="x", pady=(0, 10))

            for ev in events:
                row = ctk.CTkFrame(ev_frame, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=3)
                ctk.CTkLabel(
                    row, text="▸",
                    font=(res.FONT_LABEL[0], 11),
                    text_color=res.COLOR_PRIMARY
                ).pack(side="left", padx=(0, 8))
                ctk.CTkLabel(
                    row, text=ev,
                    font=(res.FONT_LABEL[0], 11),
                    text_color="#cccccc"
                ).pack(side="left")

            ctk.CTkFrame(ev_frame, fg_color="transparent", height=6).pack()

        # --- INSTALLATION DETAILS (installed) or GUIDE (not installed) ---
        if is_inst:
            self._section_label("Installation Details")
            path_frame = ctk.CTkFrame(
                self.right_scroll, fg_color="#0d1a0d",
                corner_radius=6, border_width=1, border_color="#1e3a1e"
            )
            path_frame.pack(fill="x", pady=(0, 10))

            ctk.CTkLabel(
                path_frame,
                text="Detected at:",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="#666666"
            ).pack(anchor="w", padx=14, pady=(10, 2))

            ctk.CTkLabel(
                path_frame,
                text=f"{get_gf_dir()}/{model['name']}/",
                font=("Courier", 11),
                text_color=res.COLOR_SUCCESS
            ).pack(anchor="w", padx=14, pady=(0, 10))

        else:
            self._section_label("Installation Guide")

            warn = ctk.CTkFrame(
                self.right_scroll, fg_color="#1a1000",
                corner_radius=6, border_width=1, border_color="#3a2800"
            )
            warn.pack(fill="x", pady=(0, 6))

            ctk.CTkLabel(
                warn,
                text=(
                    "This velocity model is not installed on your device.\n"
                    "To install it, open your Ubuntu/WSL terminal and follow these steps:"
                ),
                font=(res.FONT_LABEL[0], 11),
                text_color="#ccaa44",
                wraplength=620,
                justify="left"
            ).pack(anchor="w", padx=14, pady=(12, 10))

            steps = [
                (
                    "Step 1 — Open your WSL/Ubuntu terminal",
                    "Press the Windows key, search for 'Ubuntu', and open it.",
                    None
                ),
                (
                    "Step 2 — Go to your BBP directory and run the installer",
                    "Navigate to your BBP installation and run the setup script:",
                    "cd ~/bbp-22.4.0/setup\n./easy_install_bbp_22.4.0.sh"
                ),
                (
                    "Step 3 — Select the model during installation",
                    f"When the installer asks about velocity models, answer '1' (Yes) for {model['name']}:\n"
                    f"The installer will download and set up the Green's Functions (~{model.get('install_size', '?')}).",
                    f"==> Would you like to install the {model['full_name']} region?\n1) Yes\n2) No\n#? 1"
                ),
                (
                    "Step 4 — Verify the installation",
                    "After installation, check that the model folder exists:",
                    f"ls ~/bbp_gf/\n# You should see '{model['name']}' in the list"
                ),
                (
                    "Step 5 — Refresh the GUI",
                    "Close this panel and click 'Refresh Detection' — the GUI will detect the new model automatically.",
                    None
                ),
            ]

            for step_title, step_desc, step_cmd in steps:
                sf = ctk.CTkFrame(warn, fg_color="#111100", corner_radius=4)
                sf.pack(fill="x", padx=12, pady=3)

                ctk.CTkLabel(
                    sf, text=step_title,
                    font=(res.FONT_LABEL[0], 11, "bold"),
                    text_color=res.COLOR_PRIMARY
                ).pack(anchor="w", padx=10, pady=(7, 1))

                ctk.CTkLabel(
                    sf, text=step_desc,
                    font=(res.FONT_LABEL[0], 10),
                    text_color="#aaaaaa",
                    wraplength=580,
                    justify="left"
                ).pack(anchor="w", padx=10)

                if step_cmd:
                    n_lines = len(step_cmd.splitlines())
                    box = ctk.CTkTextbox(
                        sf,
                        fg_color="#0a0a00",
                        text_color="#44ff88",
                        font=("Courier", 10),
                        height=max(40, n_lines * 18 + 12),
                        border_width=1,
                        border_color="#2a2a00"
                    )
                    box.pack(fill="x", padx=10, pady=(4, 8))
                    box.insert("1.0", step_cmd)
                    box.configure(state="disabled")
                else:
                    ctk.CTkFrame(sf, fg_color="transparent", height=6).pack()

            ctk.CTkLabel(
                warn,
                text="⚠  Installing a new model requires a stable internet connection and sufficient disk space.",
                font=(res.FONT_LABEL[0], 10),
                text_color="#666666"
            ).pack(anchor="w", padx=14, pady=(6, 12))

        # --- CLOSE BUTTON ---
        ctk.CTkButton(
            self.right_scroll,
            text="Close",
            width=160,
            height=34,
            fg_color="#222222",
            hover_color="#333333",
            font=(res.FONT_LABEL[0], 12),
            command=self.destroy
        ).pack(pady=(12, 16))

    def _section_label(self, text):
        frame = ctk.CTkFrame(self.right_scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(
            frame, text=text,
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(side="left")
        sep = ctk.CTkFrame(frame, fg_color="#2a2a2a", height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)

    # ------------------------------------------------------------------
    # REFRESH
    # ------------------------------------------------------------------

    def _refresh(self):
        for w in self._installed_frame.winfo_children():
            w.destroy()
        for w in self._available_frame.winfo_children():
            w.destroy()
        for w in self.right_scroll.winfo_children():
            w.destroy()

        self._btn_map = {}
        self.lbl_active_name.configure(text="Scanning...", text_color="white")
        self.lbl_active_region.configure(text="")
        self.lbl_stats.configure(text="Scanning...", text_color="#555555")

        ctk.CTkLabel(
            self._installed_frame,
            text="Scanning WSL...",
            font=(res.FONT_LABEL[0], 11),
            text_color="#444444"
        ).pack(pady=12)
        ctk.CTkLabel(
            self._available_frame,
            text="Scanning WSL...",
            font=(res.FONT_LABEL[0], 11),
            text_color="#444444"
        ).pack(pady=12)

        self._show_placeholder()
        self._load_models()