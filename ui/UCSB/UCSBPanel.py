import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))
sys.path.insert(0, os.path.join(BASE_DIR, "ui", "PanelResources"))

from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge
import core.Resources as res
from ui.PanelResources.StationPanel import StationPanel
from ui.GravesAndPitarka.ChinoHillsPanel import ChinoHillsPanel
from ui.SimulationPanel import SimulationPanel


class UCSBPanel(ctk.CTkFrame):
    """
    UCSB simulation panel.
    Uses UCrmg (rupture generator) + Syn1D (combined LF+HF synthesis)
    instead of the rupture+Jbsim+Hfsims+Match pattern every other
    method in this GUI follows — UCSB has its own codebase and does
    NOT use GP's Jbsim/Hfsims, so the GP Advanced Settings panel
    (KAPPA/QFEXP/SDROP/MEAN_RVFAC/RANGE_RVFAC/RISETIME_COEF) does not
    apply here and is intentionally omitted.
    Corner frequencies (CORNER_FREQ_1, CORNER_FREQ_2) are calculated
    automatically from Magnitude using the JA19_2S double-corner-
    frequency scaling relations (Ji and Archuleta, 2020), valid for
    Mw 3.3-7.3. CORNER_FREQ is set equal to CORNER_FREQ_1, per BBP
    22.4's documented requirement. A manual override is available
    since Dr. Ghofrani noted these may need adjusting by an informed
    user.
    Color theme: #cc3366.
    Reference: Crempien and Archuleta (2015); Ji and Archuleta (2020).
    """
    def __init__(self, master, on_run_callback=None):
        super().__init__(master, fg_color="#1a1a1a")

        self._on_run_callback = on_run_callback

        self.manual_station_list = []

        self.descriptions = {
            "EXPERIMENTER"    : "Full name of the researcher for documentation.",
            "EXP_NAME"        : "Unique session identifier for filenames.",
            "MAGNITUDE"       : "Moment Magnitude (Mw) — total energy released by the earthquake.",
            "FAULT_LENGTH"    : "Fault Length (km) — length along the strike direction.",
            "FAULT_WIDTH"     : "Fault Width (km) — width measured down the dip direction.",
            "DEPTH_TO_TOP"    : "Depth to Top (km) — depth to the uppermost edge of the fault plane.",
            "STRIKE"          : "Strike (°) — angle of the fault trace measured clockwise from North (0–360°).",
            "DIP"             : "Dip (°) — angle of the fault plane relative to the horizontal surface (0–90°).",
            "RAKE"            : "Rake (°) — direction of slip on the fault plane (-180° to 180°).",
            "LAT_TOP_CENTER"  : "Latitude Top Center (°) — latitude of the top center point of the fault.",
            "LON_TOP_CENTER"  : "Longitude Top Center (°) — longitude of the top center point of the fault.",
            "HYPO_ALONG_STK"  : "Hypocenter Along Strike (km) — hypocenter position measured along strike from top center.",
            "HYPO_DOWN_DIP"   : "Hypocenter Down Dip (km) — hypocenter position measured down the dip direction.",
            "DLEN"            : "Discretization Length (km) — subfault length along strike. Default: 0.1 km.",
            "DWID"            : "Discretization Width (km) — subfault width down dip. Default: 0.1 km.",
            "SEED"            : "Random Seed — integer for reproducibility of stochastic elements.",
            "CORNER_FREQ"     : "Corner Frequency (Hz) — required by BBP 22.4 to equal CORNER_FREQ_1 (a known pipeline duplication).",
            "CORNER_FREQ_1"   : "Low Corner Frequency fc1 (Hz) — sets rupture duration. Auto-calculated from Magnitude via the JA19_2S relation (Ji & Archuleta, 2020).",
            "CORNER_FREQ_2"   : "High Corner Frequency fc2 (Hz) — sets average rise time. Auto-calculated from Magnitude via the JA19_2S relation (Ji & Archuleta, 2020).",
        }

        # --- METADATA ---
        self.meta_frame = ctk.CTkFrame(
            self, border_width=2, border_color="#cc3366", fg_color="#222222"
        )
        self.meta_frame.pack(fill="x", padx=30, pady=5)
        self.meta_frame.grid_columnconfigure((1, 3), weight=1)

        for i, meta in enumerate(["EXPERIMENTER", "EXP_NAME"]):
            lbl = ctk.CTkLabel(
                self.meta_frame, text=f"{meta}:", font=(res.FONT_LABEL[0], 12, "bold")
            )
            lbl.grid(row=0, column=i * 2, padx=15, pady=8)
            lbl.bind("<Enter>", lambda e, m=meta: self.show_help(m))

            entry = ctk.CTkEntry(self.meta_frame, height=32)
            entry.grid(row=0, column=i * 2 + 1, sticky="ew", padx=(0, 15))

            if meta == "EXPERIMENTER":
                self.ent_experimenter = entry
            else:
                self.ent_exp_name = entry

        # --- MAIN SPLIT ---
        self.main_split = ctk.CTkFrame(self, fg_color="transparent")
        self.main_split.pack(fill="both", expand=True, padx=20, pady=5)
        # Left column narrower (weight=2), map wider (weight=3)
        self.main_split.grid_columnconfigure(0, weight=2, minsize=380)
        self.main_split.grid_columnconfigure(1, weight=3)
        self.main_split.grid_rowconfigure(0, weight=1)
        self.main_split.grid_rowconfigure(1, weight=0)

        self.left_scroll = ctk.CTkScrollableFrame(
            self.main_split, fg_color="transparent"
        )
        self.left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.left_column = ctk.CTkFrame(self.left_scroll, fg_color="transparent")
        self.left_column.pack(fill="both", expand=True)

        # --- FIXED BOTTOM BAR (always visible, outside scroll) ---
        self.bottom_bar = ctk.CTkFrame(
            self.main_split,
            fg_color="#1a1a1a",
            height=70
        )
        self.bottom_bar.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(4, 0))
        self.bottom_bar.grid_propagate(False)

        # --- FAULT GEOMETRY PANEL ---
        self.src_panel = ctk.CTkFrame(
            self.left_column, fg_color="#252525", border_width=1, border_color="#444"
        )
        self.src_panel.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.src_panel,
            text="Fault Geometry Parameters (.src)",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#cc3366"
        ).pack(pady=8)

        # Two independent columns — each reads top to bottom
        # matching Dr. Ghofrani's layout exactly
        cols_frame = ctk.CTkFrame(self.src_panel, fg_color="transparent")
        cols_frame.pack(fill="x", padx=10, pady=6)
        cols_frame.grid_columnconfigure(0, weight=1)
        cols_frame.grid_columnconfigure(1, weight=1)

        left_col  = ctk.CTkFrame(cols_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        right_col = ctk.CTkFrame(cols_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.src_inputs = {}

        # LEFT column — top to bottom (6 params)
        left_params = [
            ("Magnitude",     "MAGNITUDE",      "6.5",      "Mw"),
            ("Fault Width",   "FAULT_WIDTH",    "10.0",     "km"),
            ("Fault Length",  "FAULT_LENGTH",   "20.0",     "km"),
            ("Depth to Top",  "DEPTH_TO_TOP",   "5.0",      "km"),
            ("Strike",        "STRIKE",         "180",      "°"),
            ("Dip",           "DIP",            "90",       "°"),
        ]

        # RIGHT column — top to bottom (5 params)
        right_params = [
            ("Rake",               "RAKE",           "0",        "°"),
            ("Hypo. Down Dip",     "HYPO_DOWN_DIP",  "5.0",      "km"),
            ("Hypo. Along Strike", "HYPO_ALONG_STK", "10.0",     "km"),
            ("Lon. Top Center",    "LON_TOP_CENTER",  "-118.500", "°"),
            ("Lat. Top Center",    "LAT_TOP_CENTER",  "34.000",   "°"),
        ]

        def _build_col(parent, params):
            parent.grid_columnconfigure(1, weight=1)
            for i, (name, key, default, unit) in enumerate(params):
                lbl = ctk.CTkLabel(
                    parent, text=name,
                    font=(res.FONT_LABEL[0], 11), anchor="w"
                )
                lbl.grid(row=i, column=0, padx=(4, 4), pady=3, sticky="w")
                lbl.bind("<Enter>", lambda e, p=key: self.show_help(p))
                lbl.bind("<Leave>", lambda e: self.show_help(""))

                ent = ctk.CTkEntry(parent, height=28)
                ent.insert(0, default)
                ent.grid(row=i, column=1, padx=(0, 2), pady=3, sticky="ew")
                ent.bind("<KeyRelease>", lambda e, k=key: self._on_src_field_change(k))
                self.src_inputs[key] = ent

                ctk.CTkLabel(
                    parent, text=unit,
                    font=(res.FONT_LABEL[0], 10),
                    text_color="gray", width=22, anchor="w"
                ).grid(row=i, column=2, padx=(2, 4), pady=3, sticky="w")

        _build_col(left_col,  left_params)
        _build_col(right_col, right_params)

        # --- ADVANCED PARAMETERS (collapsed section) ---
        self.adv_frame = ctk.CTkFrame(
            self.left_column, fg_color="#252525", border_width=1, border_color="#444"
        )
        self.adv_frame.pack(fill="x", pady=(0, 5))

        self.adv_visible = False
        self.btn_adv_toggle = ctk.CTkButton(
            self.adv_frame,
            text="▶  Advanced Parameters",
            fg_color="transparent",
            text_color="gray",
            hover_color="#333333",
            anchor="w",
            command=self.toggle_advanced
        )
        self.btn_adv_toggle.pack(fill="x", padx=10, pady=5)

        self.adv_content = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        adv_grid = ctk.CTkFrame(self.adv_content, fg_color="transparent")
        adv_grid.pack(fill="x", padx=15, pady=5)
        adv_grid.grid_columnconfigure((1, 3), weight=1)

        self.adv_inputs = {}
        adv_params = [
            ("DLEN", "0.1"),
            ("DWID", "0.1"),
            ("SEED", "1234567"),
        ]

        for i, (param, default) in enumerate(adv_params):
            lbl = ctk.CTkLabel(adv_grid, text=param, font=(res.FONT_LABEL[0], 11))
            lbl.grid(row=0, column=i * 2, padx=8, pady=6, sticky="w")
            lbl.bind("<Enter>", lambda e, p=param: self.show_help(p))

            entry = ctk.CTkEntry(adv_grid, height=30)
            entry.insert(0, default)
            entry.grid(row=0, column=i * 2 + 1, padx=(0, 8), pady=6, sticky="ew")
            self.adv_inputs[param] = entry

        # Caption explaining DLEN/DWID meaning
        ctk.CTkLabel(
            adv_grid,
            text=(
                "DLEN/DWID set the UCrmg subfault grid:\n"
                "nstk = round(Fault Length / DLEN)  along strike\n"
                "ndip = round(Fault Width / DWID)   down dip"
            ),
            font=(res.FONT_LABEL[0], 9),
            text_color="#555555",
            justify="left",
            anchor="w"
        ).grid(row=1, column=0, columnspan=6, padx=8, pady=(0, 4), sticky="w")

        # --- CORNER FREQUENCY SECTION (UCSB-specific, JA19_2S) ---
        # fc1/fc2 are calculated automatically from Magnitude and are
        # read-only by default. CORNER_FREQ always mirrors CORNER_FREQ_1
        # (BBP 22.4 requirement). A manual override checkbox is provided
        # per Dr. Ghofrani's guidance, since an informed user may need
        # to substitute a region-specific stress-drop-based value.
        cf_frame = ctk.CTkFrame(self.adv_content, fg_color="transparent")
        cf_frame.pack(fill="x", padx=15, pady=(4, 8))

        ctk.CTkLabel(
            cf_frame,
            text="Corner Frequencies (JA19_2S — Ji & Archuleta, 2020)",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#cc3366"
        ).pack(anchor="w", pady=(0, 4))

        self.corner_manual_override = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            cf_frame,
            text="Manual override (default: auto-calculated from Magnitude)",
            variable=self.corner_manual_override,
            font=(res.FONT_LABEL[0], 10),
            command=self._on_corner_override_toggle
        ).pack(anchor="w", pady=(0, 6))

        cf_grid = ctk.CTkFrame(cf_frame, fg_color="transparent")
        cf_grid.pack(fill="x")
        cf_grid.grid_columnconfigure((1, 3), weight=1)

        self.corner_inputs = {}
        for i, param in enumerate(["CORNER_FREQ_1", "CORNER_FREQ_2"]):
            lbl = ctk.CTkLabel(cf_grid, text=f"{param} (Hz)", font=(res.FONT_LABEL[0], 11))
            lbl.grid(row=0, column=i * 2, padx=8, pady=6, sticky="w")
            lbl.bind("<Enter>", lambda e, p=param: self.show_help(p))

            entry = ctk.CTkEntry(cf_grid, height=30, state="disabled")
            entry.grid(row=0, column=i * 2 + 1, padx=(0, 8), pady=6, sticky="ew")
            self.corner_inputs[param] = entry

        self.lbl_corner_note = ctk.CTkLabel(
            cf_frame,
            text="",
            font=(res.FONT_LABEL[0], 9),
            text_color="#777777",
            justify="left",
            anchor="w",
            wraplength=340
        )
        self.lbl_corner_note.pack(anchor="w", pady=(2, 0))

        # --- MANUAL STATION PANEL ---
        self.manual_panel = ctk.CTkFrame(
            self.left_column, fg_color="#252525", border_width=1, border_color="gold"
        )
        self.manual_panel.pack(fill="x", pady=5)

        ctk.CTkLabel(
            self.manual_panel,
            text="Add Manual Station (Custom)",
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color="gold"
        ).pack(pady=5)

        man_f = ctk.CTkFrame(self.manual_panel, fg_color="transparent")
        man_f.pack(fill="x", padx=10, pady=5)

        self.ent_man_lon  = ctk.CTkEntry(man_f, placeholder_text="Lon",  width=70)
        self.ent_man_lon.pack(side="left", padx=5)
        self.ent_man_lat  = ctk.CTkEntry(man_f, placeholder_text="Lat",  width=70)
        self.ent_man_lat.pack(side="left", padx=5)
        self.ent_man_name = ctk.CTkEntry(man_f, placeholder_text="Name", width=80)
        self.ent_man_name.pack(side="left", padx=5)

        ctk.CTkButton(
            man_f,
            text="+ ADD",
            width=60,
            fg_color="gold",
            text_color="black",
            command=self.add_manual_station
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            man_f,
            text="CLEAR",
            width=60,
            fg_color="#444444",
            text_color="white",
            command=self.clear_manual_stations
        ).pack(side="left", padx=5)

        # --- STATION LIST — hidden until first station is added ---
        self.station_list_frame = ctk.CTkFrame(
            self.manual_panel,
            fg_color="#1a1a1a",
            corner_radius=6,
            border_width=1,
            border_color="#333333"
        )
        # Not packed yet — revealed by _refresh_station_list when list is non-empty

        # --- SECONDARY BUTTONS (above Generate/Run) ---
        self.btn_f2 = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.btn_f2.pack(fill="x", pady=(8, 4), padx=5)

        self.btn_real_stations = ctk.CTkButton(
            self.btn_f2,
            text="Show Real Stations",
            height=36,
            fg_color="#333333",
            border_width=1,
            border_color="orange",
            text_color="orange",
            hover_color="#2a2a2a",
            command=self.toggle_real_stations
        )
        self.btn_real_stations.pack(side="left", expand=True, padx=(0, 5))

        self.btn_chino_ref = ctk.CTkButton(
            self.btn_f2,
            text="Chino Hills Reference",
            height=36,
            fg_color="#333333",
            border_width=1,
            border_color="#cc3366",
            text_color="white",
            hover_color="#2a2a2a",
            command=self.open_chino_hills_panel
        )
        self.btn_chino_ref.pack(side="left", expand=True, padx=(5, 0))

        # --- SIMULATION PROFILE SELECTOR ---
        self.profile_frame = ctk.CTkFrame(
            self.left_column,
            fg_color="#1e1e1e",
            border_width=1,
            border_color="#333333",
            corner_radius=6
        )
        self.profile_frame.pack(fill="x", pady=(8, 4), padx=5)

        ctk.CTkLabel(
            self.profile_frame,
            text="Simulation Profile:",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="gray"
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.profile_var = ctk.StringVar(value="Full Pipeline")
        self.seg_profile = ctk.CTkSegmentedButton(
            self.profile_frame,
            values=["Full Pipeline", "Custom"],
            variable=self.profile_var,
            command=self._on_profile_change,
            height=32
        )
        self.seg_profile.pack(fill="x", padx=10, pady=(0, 4))

        self.lbl_profile_desc = ctk.CTkLabel(
            self.profile_frame,
            text="All 9 modules — complete results including seismograms, spectra, maps and HTML report.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#aaaaaa",
            wraplength=320,
            justify="left",
            anchor="w"
        )
        self.lbl_profile_desc.pack(anchor="w", padx=10, pady=(0, 4))

        # Custom pipeline configure button — shown only for Custom profile
        self.btn_custom_configure = ctk.CTkButton(
            self.profile_frame,
            text="Configure Custom Pipeline",
            height=30,
            fg_color="#cc3366",
            hover_color="#004070",
            font=(res.FONT_LABEL[0], 11),
            command=self._open_custom_pipeline
        )
        # Not packed yet — shown only when Custom is selected

        # Custom summary label — shows selected modules after configuration
        self.lbl_custom_summary = ctk.CTkLabel(
            self.profile_frame,
            text="",
            font=("Courier", 9),
            text_color=res.COLOR_SUCCESS,
            wraplength=320,
            justify="left",
            anchor="w"
        )
        # Not packed yet

        # --- FIXED HELP LABEL — inside a fixed-size container so it NEVER shifts layout ---
        help_container = ctk.CTkFrame(
            self.bottom_bar,
            fg_color="transparent",
            width=420,
            height=46
        )
        help_container.pack(side="left", padx=10, pady=12)
        help_container.pack_propagate(False)  # Container never resizes

        self.help_label = ctk.CTkLabel(
            help_container,
            text="Hover over a parameter label for description",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray",
            wraplength=415,
            anchor="w",
            justify="left",
            width=420,
            height=46
        )
        self.help_label.place(x=0, y=0)

        self.btn_run = ctk.CTkButton(
            self.bottom_bar,
            text="RUN BBP SIMULATION",
            height=42,
            width=180,
            fg_color="#cc3366",
            state="disabled",
            command=self.run_bbp
        )
        self.btn_run.pack(side="right", padx=(5, 8), pady=14)

        self.btn_save = ctk.CTkButton(
            self.bottom_bar,
            text="GENERATE FILES",
            height=42,
            width=155,
            fg_color=res.COLOR_SUCCESS,
            command=self.generate_files
        )
        self.btn_save.pack(side="right", padx=(0, 5), pady=14)

        # --- STATION MODULE (right column, spans both rows) ---
        self.station_module = StationPanel(self.main_split)
        self.station_module.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.station_module.update_callback = self.trigger_map_update

        # --- AUTO FULLSCREEN ---
        self.after(100, self._set_fullscreen)

        self.trigger_map_update()
        self._update_corner_freqs()

    # ------------------------------------------------------------------
    # FULLSCREEN
    # ------------------------------------------------------------------

    def _set_fullscreen(self):
        """Maximizes the parent window when RupturePanel is loaded."""
        try:
            top = self.winfo_toplevel()
            top.state("zoomed")
        except:
            try:
                top = self.winfo_toplevel()
                top.attributes("-zoomed", True)
            except:
                pass

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def show_help(self, tag):
        """Updates the fixed-size help label with parameter description on hover."""
        try:
            if tag:
                text  = self.descriptions.get(tag, "")
                color = "white"
            else:
                text  = "Hover over a parameter label for description"
                color = "gray"
            self.help_label.configure(text=text, text_color=color)
        except:
            pass

    def toggle_advanced(self):
        """Shows or hides the advanced parameters section."""
        if self.adv_visible:
            self.adv_content.pack_forget()
            self.btn_adv_toggle.configure(text="▶  Advanced Parameters")
            self.adv_visible = False
        else:
            self.adv_content.pack(fill="x", padx=5, pady=(0, 8))
            self.btn_adv_toggle.configure(text="▼  Advanced Parameters")
            self.adv_visible = True

    def trigger_map_update(self):
        """
        Schedules a map redraw with 350ms debounce.
        Cancels any pending redraw before scheduling a new one.
        This prevents lag when the user types quickly in parameter fields.
        """
        if not self.winfo_exists():
            return
        # Cancel any pending redraw
        if hasattr(self, "_map_timer") and self._map_timer:
            try:
                self.after_cancel(self._map_timer)
            except Exception:
                pass
        # Schedule new redraw after 350ms idle
        self._map_timer = self.after(350, self._execute_map_update)

    def _execute_map_update(self):
        """Performs the actual map redraw after debounce delay."""
        self._map_timer = None
        if not self.winfo_exists():
            return
        try:
            fault_params = {
                "lat_top"    : float(self.src_inputs["LAT_TOP_CENTER"].get()),
                "lon_top"    : float(self.src_inputs["LON_TOP_CENTER"].get()),
                "strike"     : float(self.src_inputs["STRIKE"].get()),
                "fault_len"  : float(self.src_inputs["FAULT_LENGTH"].get()),
                "fault_wid"  : float(self.src_inputs["FAULT_WIDTH"].get()),
                "dip"        : float(self.src_inputs["DIP"].get()),
                "depth_top"  : float(self.src_inputs["DEPTH_TO_TOP"].get()),
                "hypo_stk"   : float(self.src_inputs["HYPO_ALONG_STK"].get()),
                "hypo_dip"   : float(self.src_inputs["HYPO_DOWN_DIP"].get()),
            }
            self.station_module.redraw(fault_params, self.manual_station_list)
        except Exception:
            pass

    def _on_src_field_change(self, key):
        """Dispatches a fault-parameter field change: always refreshes
        the map, and additionally recalculates corner frequencies when
        Magnitude changes, since fc1/fc2 depend on it directly."""
        self.trigger_map_update()
        if key == "MAGNITUDE":
            self._update_corner_freqs()

    # ------------------------------------------------------------------
    # CORNER FREQUENCY CALCULATION (JA19_2S — Ji & Archuleta, 2020)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_fc1(magnitude):
        """Low corner frequency (Hz). Branch depends on magnitude —
        confirmed against BBP's UCSB_21.3_c.pdf release notes."""
        if magnitude <= 5.3:
            log_fc1 = 1.474 - 0.415 * magnitude
        else:
            log_fc1 = 2.375 - 0.585 * magnitude
        return 10 ** log_fc1

    @staticmethod
    def _compute_fc2(magnitude):
        """High corner frequency (Hz) — single relation across the
        full 3.3-7.3 Mw range."""
        log_fc2 = 3.250 - 0.5 * magnitude
        return 10 ** log_fc2

    def _on_corner_override_toggle(self):
        """Enables/disables manual editing of fc1/fc2. Re-enabling
        auto mode immediately recalculates from the current Magnitude."""
        if self.corner_manual_override.get():
            for entry in self.corner_inputs.values():
                entry.configure(state="normal")
            self.lbl_corner_note.configure(
                text="Manual override active — values will NOT be recalculated automatically.",
                text_color="#ffaa44"
            )
        else:
            self._update_corner_freqs()

    def _update_corner_freqs(self):
        """Recalculates fc1/fc2 from the current Magnitude field and
        writes them into the (read-only, unless overridden) entries.
        No-op while manual override is active."""
        if self.corner_manual_override.get():
            return
        try:
            magnitude = float(self.src_inputs["MAGNITUDE"].get())
        except (ValueError, KeyError):
            return

        fc1 = self._compute_fc1(magnitude)
        fc2 = self._compute_fc2(magnitude)

        for param, value in (("CORNER_FREQ_1", fc1), ("CORNER_FREQ_2", fc2)):
            entry = self.corner_inputs[param]
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, f"{value:.8f}")
            entry.configure(state="disabled")

        if 3.3 <= magnitude <= 7.3:
            self.lbl_corner_note.configure(
                text=f"Auto-calculated for Mw {magnitude:.2f} (JA19_2S valid range: 3.3-7.3).",
                text_color="#777777"
            )
        else:
            self.lbl_corner_note.configure(
                text=f"⚠ Mw {magnitude:.2f} is outside the JA19_2S validated range (3.3-7.3) — "
                     "these values are an extrapolation, not a validated result.",
                text_color="#ff6666"
            )

    # ------------------------------------------------------------------
    # STATION MANAGEMENT
    # ------------------------------------------------------------------

    def add_manual_station(self):
        """Validates and adds a manual station to the map."""
        try:
            lon  = float(self.ent_man_lon.get())
            lat  = float(self.ent_man_lat.get())
            name = self.ent_man_name.get().strip() or f"M{len(self.manual_station_list)}"

            self.manual_station_list.append((lon, lat, name))
            self._refresh_station_list()
            self.trigger_map_update()

            if StationPanel.is_inside_basin(lon, lat):
                self.help_label.configure(
                    text=f"Station {name} added at ({lat:.4f}, {lon:.4f}).",
                    text_color="gold"
                )
            else:
                self.help_label.configure(
                    text=(
                        f"⚠ Station {name} added at ({lat:.4f}, {lon:.4f}) — this is OUTSIDE "
                        f"the LABasin500 model boundary. Results for this station will not be "
                        f"scientifically reliable."
                    ),
                    text_color="#ff6666"
                )
            self.ent_man_lon.delete(0, "end")
            self.ent_man_lat.delete(0, "end")
            self.ent_man_name.delete(0, "end")

        except ValueError:
            self.help_label.configure(
                text="Invalid Lon/Lat — enter numeric values only.",
                text_color=res.COLOR_ERROR
            )

    def clear_manual_stations(self):
        """Removes all manually added stations and refreshes the map."""
        self.manual_station_list.clear()
        self._refresh_station_list()
        self.trigger_map_update()
        self.help_label.configure(
            text="Manual stations cleared.", text_color="gray"
        )

    def _refresh_station_list(self):
        """
        Rebuilds the station list UI from manual_station_list.
        The list frame is hidden when empty and grows dynamically
        with each station added. Called after every add, delete, or edit.
        """
        for widget in self.station_list_frame.winfo_children():
            widget.destroy()

        if not self.manual_station_list:
            self.station_list_frame.pack_forget()
            return

        self.station_list_frame.pack(fill="x", padx=10, pady=(4, 8))

        for idx, (lon, lat, name) in enumerate(self.manual_station_list):
            row = ctk.CTkFrame(
                self.station_list_frame,
                fg_color="#2a2a2a",
                corner_radius=4
            )
            row.pack(fill="x", pady=(4, 0), padx=6)

            # Index badge
            ctk.CTkLabel(
                row,
                text=f"{idx + 1}",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="#666666",
                width=22,
                anchor="e"
            ).pack(side="left", padx=(8, 4), pady=6)

            # Station name
            ctk.CTkLabel(
                row,
                text=f"{name}",
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color="gold",
                anchor="w",
                width=65
            ).pack(side="left", padx=(0, 6))

            # Coordinates
            ctk.CTkLabel(
                row,
                text=f"lat {lat:.5f}   lon {lon:.5f}",
                font=(res.FONT_LABEL[0], 12),
                text_color="#cccccc",
                anchor="w"
            ).pack(side="left", padx=(0, 6), fill="x", expand=True)

            # Edit button
            ctk.CTkButton(
                row,
                text="Edit",
                width=48,
                height=26,
                font=(res.FONT_LABEL[0], 11),
                fg_color="#1a3a5c",
                hover_color="#1e4a7a",
                text_color="#5ab4ff",
                border_width=1,
                border_color="#2a5a8c",
                corner_radius=4,
                command=lambda i=idx: self._edit_station(i)
            ).pack(side="right", padx=(2, 6), pady=6)

            # Delete button
            ctk.CTkButton(
                row,
                text="✕",
                width=30,
                height=26,
                font=(res.FONT_LABEL[0], 11),
                fg_color="#3a1a1a",
                hover_color="#5a2a2a",
                text_color="#ff6666",
                border_width=1,
                border_color="#6a2a2a",
                corner_radius=4,
                command=lambda i=idx: self._delete_station(i)
            ).pack(side="right", padx=(6, 2), pady=6)

        # Bottom padding inside the frame
        ctk.CTkFrame(
            self.station_list_frame, fg_color="transparent", height=4
        ).pack()

    def _delete_station(self, idx):
        """Removes the station at the given index and refreshes the list and map."""
        if 0 <= idx < len(self.manual_station_list):
            name = self.manual_station_list[idx][2]
            self.manual_station_list.pop(idx)
            self._refresh_station_list()
            self.trigger_map_update()
            self.help_label.configure(
                text=f"Station {name} removed.",
                text_color="gray"
            )

    def _edit_station(self, idx):
        """
        Populates the entry fields with the selected station's values
        and removes it from the list, ready for the user to modify and re-add.
        """
        if 0 <= idx < len(self.manual_station_list):
            lon, lat, name = self.manual_station_list[idx]
            self.manual_station_list.pop(idx)
            self._refresh_station_list()
            self.trigger_map_update()

            self.ent_man_lon.delete(0, "end")
            self.ent_man_lon.insert(0, str(lon))
            self.ent_man_lat.delete(0, "end")
            self.ent_man_lat.insert(0, str(lat))
            self.ent_man_name.delete(0, "end")
            self.ent_man_name.insert(0, name)

            self.help_label.configure(
                text=f"Editing station {name} — modify the fields above and click + ADD to save.",
                text_color="#5ab4ff"
            )

    # ------------------------------------------------------------------
    # INPUT VALIDATION
    # ------------------------------------------------------------------

    def _validate_inputs(self):
        """
        Validates all src parameter ranges before generating files.
        Returns (bool: valid, str: error message).
        """
        rules = {
            "MAGNITUDE"      : (0.0,    10.0),
            "FAULT_LENGTH"   : (0.1,    1000.0),
            "FAULT_WIDTH"    : (0.1,    500.0),
            "DEPTH_TO_TOP"   : (0.0,    100.0),
            "STRIKE"         : (0.0,    360.0),
            "DIP"            : (0.0,    90.0),
            "RAKE"           : (-180.0, 180.0),
            "LAT_TOP_CENTER" : (-90.0,  90.0),
            "LON_TOP_CENTER" : (-180.0, 180.0),
            "HYPO_ALONG_STK" : (0.0,    1000.0),
            "HYPO_DOWN_DIP"  : (0.0,    500.0),
        }

        for param, (min_val, max_val) in rules.items():
            raw = self.src_inputs[param].get().strip()
            try:
                val = float(raw)
            except ValueError:
                return False, f"{param}: must be a number."
            if not (min_val <= val <= max_val):
                return False, f"{param}: must be between {min_val} and {max_val}."

        # Validate advanced params
        for param in ["DLEN", "DWID"]:
            try:
                val = float(self.adv_inputs[param].get())
                if val <= 0:
                    return False, f"{param}: must be greater than 0."
            except ValueError:
                return False, f"{param}: must be a number."

        try:
            int(self.adv_inputs["SEED"].get())
        except ValueError:
            return False, "SEED: must be an integer."

        # Corner frequencies — only need re-validating if the user
        # overrode the auto-calculated values, since those are always
        # numeric and positive by construction.
        if self.corner_manual_override.get():
            for param in ["CORNER_FREQ_1", "CORNER_FREQ_2"]:
                try:
                    val = float(self.corner_inputs[param].get())
                    if val <= 0:
                        return False, f"{param}: must be greater than 0."
                except ValueError:
                    return False, f"{param}: must be a number."

        return True, ""

    # ------------------------------------------------------------------
    # FILE GENERATION
    # ------------------------------------------------------------------

    def generate_files(self):
        """
        Validates inputs, builds the .src and .stl file content,
        and writes both files into the WSL filesystem via WSLBridge.
        Enables the RUN button on success.
        """
        user = self.ent_experimenter.get().strip().replace(" ", "_")
        exp  = self.ent_exp_name.get().strip().replace(" ", "_")

        if not user or not exp:
            self.help_label.configure(
                text="CRITICAL: Experimenter and Experiment Name are required.",
                text_color=res.COLOR_ERROR
            )
            return

        valid, err_msg = self._validate_inputs()
        if not valid:
            self.help_label.configure(text=f"Validation Error: {err_msg}", text_color=res.COLOR_ERROR)
            return

        base = f"{user}_{exp}"

        # --- BUILD .src CONTENT ---
        src_lines = [f"# EXPERIMENTER: {user}\n"]
        for k, v in self.src_inputs.items():
            src_lines.append(f"{k} = {v.get()}\n")

        # --- MODEL SPECIFIC PARAMETERS ---
        src_lines.append("#\n# Model specific parameters\n#\n")
        src_lines.append(f"DLEN = {self.adv_inputs['DLEN'].get()}\n")
        src_lines.append(f"DWID = {self.adv_inputs['DWID'].get()}\n")

        # CORNER_FREQ_1/CORNER_FREQ_2 come from the (auto-calculated or
        # manually overridden) corner-frequency entries. CORNER_FREQ is
        # always set equal to CORNER_FREQ_1 — required by BBP 22.4's
        # UCrmg (confirmed both from BBP's own File-Format-Guide.md and
        # from a real KeyError crash when it was missing).
        fc1 = self.corner_inputs["CORNER_FREQ_1"].get()
        fc2 = self.corner_inputs["CORNER_FREQ_2"].get()
        src_lines.append(f"CORNER_FREQ = {fc1}\n")
        src_lines.append(f"CORNER_FREQ_1 = {fc1}\n")
        src_lines.append(f"CORNER_FREQ_2 = {fc2}\n")
        src_lines.append(f"SEED = {self.adv_inputs['SEED'].get()}\n")

        # --- CORNER FREQUENCY PROVENANCE ---
        # Records whether fc1/fc2 came from the JA19_2S auto-calculation
        # or a manual override, so a future researcher looking at this
        # .src file (or re-opening the run in ResultsPanel) knows
        # exactly where these values came from — same purpose as the
        # snapshot comments other methods write for their own
        # method-specific parameters.
        src_lines.append("\n")
        src_lines.append("# --- CORNER FREQUENCY SOURCE (at time of run) ---\n")
        if self.corner_manual_override.get():
            src_lines.append("# CORNER_FREQ_1/2 = MANUAL_OVERRIDE\n")
        else:
            src_lines.append("# CORNER_FREQ_1/2 = JA19_2S (Ji & Archuleta, 2020), auto-calculated from MAGNITUDE\n")

        src_lines.append("\n")
        src_lines.append("# --- SIMULATION METHOD (at time of run) ---\n")
        src_lines.append("# METHOD = UCSB\n")
        src_content = "".join(src_lines)

        # --- BUILD .stl CONTENT ---
        lat = float(self.src_inputs["LAT_TOP_CENTER"].get())
        lon = float(self.src_inputs["LON_TOP_CENTER"].get())
        stations = self.station_module.get_stations()

        # Include any manual stations not already in the list
        for m_lon, m_lat, m_name in self.manual_station_list:
            if (m_lon, m_lat, m_name) not in stations:
                stations.append((m_lon, m_lat, m_name))

        stl_content = "".join(
            f"{s_lon:.5f}  {s_lat:.5f}  {s_id}\n"
            for s_lon, s_lat, s_id in stations
        )

        # --- WRITE FILES VIA WSLBRIDGE ---
        src_wsl_path = f"{AppConfig.src_path}/{base}.src"
        stl_wsl_path = f"{AppConfig.stl_path}/{base}.stl"

        ok_src, err_src = WSLBridge.write_wsl_file(src_wsl_path, src_content)
        if not ok_src:
            self.help_label.configure(
                text=f"Error writing .src file: {err_src}", text_color=res.COLOR_ERROR
            )
            return

        ok_stl, err_stl = WSLBridge.write_wsl_file(stl_wsl_path, stl_content)
        if not ok_stl:
            self.help_label.configure(
                text=f"Error writing .stl file: {err_stl}", text_color=res.COLOR_ERROR
            )
            return

        # Store filenames for use by the simulation stage.
        # simulation_method is set explicitly here (not just left as
        # whatever default AppConfig has) because it's a class-level
        # attribute shared across the whole app — if the user opened
        # ExSimPanel earlier in this session, AppConfig.simulation_method
        # would still read "EXSIM" here otherwise, causing SimulationPanel
        # to build and run the wrong method's pipeline entirely.
        AppConfig.current_src_file  = src_wsl_path
        AppConfig.current_stl_file  = stl_wsl_path
        AppConfig.current_base_name = base
        AppConfig.simulation_method  = "UCSB"

        self.btn_run.configure(state="normal")
        self.help_label.configure(
            text=f"SUCCESS — Files saved for experiment: {base}",
            text_color=res.COLOR_SUCCESS
        )

    def _on_profile_change(self, value):
        """Updates profile, description, and shows/hides Custom button."""
        profile_map = {
            "Full Pipeline" : "full",
            "Custom"        : "custom",
        }
        desc_map = {
            "Full Pipeline" : "All 9 modules — complete results: seismograms, spectra, maps and HTML report.",
            "Custom"        : "Click 'Configure' to select exactly which modules to run.",
        }
        AppConfig.simulation_profile = profile_map.get(value, "full")
        self.lbl_profile_desc.configure(text=desc_map.get(value, ""))

        if value == "Custom":
            self.btn_custom_configure.pack(fill="x", padx=10, pady=(0, 6))
        else:
            self.btn_custom_configure.pack_forget()
            self.lbl_custom_summary.pack_forget()
            AppConfig.custom_modules = []

    def _open_custom_pipeline(self):
        """Opens the CustomPipelinePanel with UCSB-specific modules."""
        from ui.PanelResources.CustomPipelinePanel import CustomPipelinePanel
        CustomPipelinePanel(
            master     = self.winfo_toplevel(),
            on_confirm = self._on_custom_confirmed,
            method     = "UCSB"
        )

    def _on_custom_confirmed(self, selected_modules):
        """
        Called when the user confirms their custom module selection.
        Updates the summary label to show what was selected.
        """
        self.lbl_custom_summary.configure(
            text=" → ".join(selected_modules)
        )
        self.lbl_custom_summary.pack(
            anchor="w", padx=10, pady=(0, 8)
        )

    def _get_custom_modules(self):
        """Returns the stored custom module list from AppConfig."""
        return AppConfig.custom_modules

    def toggle_real_stations(self):
        """Toggles the real Chino Hills station layer on the map."""
        is_visible = self.station_module.toggle_real_stations()
        if is_visible:
            self.btn_real_stations.configure(
                text="Hide Real Stations",
                fg_color="#2a1a00",
                border_color="orange",
                text_color="orange"
            )
        else:
            self.btn_real_stations.configure(
                text="Show Real Stations",
                fg_color="#333333",
                border_color="orange",
                text_color="orange"
            )

    def open_chino_hills_panel(self):
        """Opens the Chino Hills read-only reference panel as a popup."""
        ChinoHillsPanel(self.winfo_toplevel())

    # ------------------------------------------------------------------
    # BBP SIMULATION
    # ------------------------------------------------------------------

    def run_bbp(self):
        """
        Validates custom module selection if Custom profile is active,
        then triggers the simulation via MainPanel callback.

        simulation_method is set again here (not just in generate_files)
        as a second safety net against AppConfig.simulation_method
        leaking "EXSIM" from a previous ExSimPanel session into a GP run.
        """
        AppConfig.simulation_method = "UCSB"

        if AppConfig.simulation_profile == "custom":
            if not AppConfig.custom_modules:
                self.help_label.configure(
                    text="Custom profile: click 'Configure Custom Pipeline' first.",
                    text_color=res.COLOR_ERROR
                )
                return

        if self._on_run_callback:
            self._on_run_callback()

    def load_from_src(self, params, stations):
        """
        Pre-fills all GP panel fields from a parsed .src parameter dict
        and a station list [(lon, lat, name), ...].

        Called by main.py when the user clicks Edit on a history row.
        Handles auto-naming: appends _1, _2, ... to avoid name collisions.
        """
        import re as _re

        def _set(entry, val):
            if val is not None:
                entry.delete(0, "end")
                entry.insert(0, str(val))

        # --- Experimenter / EXP_NAME ---
        experimenter = params.get("EXPERIMENTER", "")
        exp_name_raw = params.get("_suggested_exp_name", "") or params.get("EXP_NAME", "")

        # Generate a unique _N suffix for the experiment name
        base = _re.sub(r'_\d+$', '', exp_name_raw) if exp_name_raw else exp_name_raw
        new_exp = f"{base}_1" if base else "resim_1"

        _set(self.ent_experimenter, experimenter)
        _set(self.ent_exp_name, new_exp)

        # --- Fault geometry ---
        gp_keys = [
            "MAGNITUDE", "FAULT_LENGTH", "FAULT_WIDTH", "DEPTH_TO_TOP",
            "STRIKE", "DIP", "RAKE", "HYPO_DOWN_DIP", "HYPO_ALONG_STK",
            "LON_TOP_CENTER", "LAT_TOP_CENTER",
        ]
        for key in gp_keys:
            if key in params and key in self.src_inputs:
                _set(self.src_inputs[key], params[key])

        # --- DLEN, DWID, SEED ---
        for adv_key in ("DLEN", "DWID", "SEED"):
            if adv_key in params and adv_key in self.adv_inputs:
                _set(self.adv_inputs[adv_key], params[adv_key])

        # --- Corner frequencies ---
        # Loaded as a manual override rather than left on auto-calculate,
        # since the original run's fc1/fc2 may have come from a manual
        # override themselves (recorded in the CORNER_FREQ_1/2 SOURCE
        # comment), and silently recalculating them from Magnitude here
        # could quietly replace values the original researcher chose
        # deliberately.
        if "CORNER_FREQ_1" in params or "CORNER_FREQ_2" in params:
            self.corner_manual_override.set(True)
            for entry in self.corner_inputs.values():
                entry.configure(state="normal")
            if "CORNER_FREQ_1" in params:
                _set(self.corner_inputs["CORNER_FREQ_1"], params["CORNER_FREQ_1"])
            if "CORNER_FREQ_2" in params:
                _set(self.corner_inputs["CORNER_FREQ_2"], params["CORNER_FREQ_2"])
            self.lbl_corner_note.configure(
                text="Loaded from previous run as a manual override — verify before running.",
                text_color="#ffaa44"
            )

        # --- Stations ---
        self.manual_station_list.clear()
        for lon, lat, name in stations:
            self.manual_station_list.append((lon, lat, name))
        self._refresh_station_list()
        self.trigger_map_update()

        # Surface a confirmation message
        self.help_label.configure(
            text=f"Fields pre-filled from previous run. "
                 f"Experiment renamed to '{new_exp}'. "
                 "Review all values then click Generate Files.",
            text_color=res.COLOR_SUCCESS
        )