import customtkinter as ctk

from core.AppConfig  import AppConfig
from core.WSLBridge   import WSLBridge
import core.Resources as res
from ui.SimulationPanel import SimulationPanel
from ui.PanelResources.FaultMapPanel import FaultMapPanel


class RuptureGeneratorPanel(ctk.CTkFrame):
    """
    Standalone rupture-model generator.

    Unlike GravesAndPitarkaPanel / IrikuraPanel / SongPanel, this panel
    does not run a full broadband pipeline. It only produces .srf files
    (rupture-only profile) so a researcher can inspect / compare how
    different rupture generators (Genslip, IrikuraGenSrf, SongRMGSS)
    respond to the exact same fault geometry, without needing to pick
    stations, run Jbsim/Hfsims, or generate an HTML report.

    Confirmed against XMLGenerator.py: all three methods' .src
    parameters are identical (MAGNITUDE, FAULT_LENGTH, FAULT_WIDTH,
    DEPTH_TO_TOP, STRIKE, DIP, RAKE, HYPO_ALONG_STK, HYPO_DOWN_DIP,
    LAT_TOP_CENTER, LON_TOP_CENTER, DLEN, DWID, SEED), and each already
    has a dedicated rupture-only XML generator
    (_generate_rupture_xml for GP, _generate_irikura1_rupture_xml,
    _generate_song_rupture_xml) and a single-module BBP_MODULES_*_RUPTURE
    list. That means this panel needs no changes to XMLGenerator.py —
    it only needs to write one .src file per selected method (each
    carrying its own "# METHOD = X" marker) plus one shared dummy .stl,
    then drive SimulationPanel with profile="rupture" for each.

    The user may select one, two, or three methods at once. Generate
    Files writes one .src per selected method and a single shared .stl
    with one placeholder station (rupture-only profiles never reach
    Plot_Map/PlotSeis, so the station's exact location has no scientific
    effect — it exists only because BBP's XML header still references
    a station-list path). Simulate then runs the selected methods one
    after another automatically: this panel opens SimulationPanel
    directly (as GP/Irikura1/Song panels already do), and chains to the
    next queued method via SimulationPanel's on_dashboard_callback
    instead of returning to the real Dashboard until the queue is
    empty. If the user opens Results mid-queue instead of continuing,
    the chain stops there — they would need to reopen this panel and
    re-run the remaining methods. That trade-off is a reasonable first
    version, not a final design decision; worth revisiting with Dr.
    Ghofrani once the panel is in use.
    """

    METHOD_INFO = {
        "GP"      : ("Graves & Pitarka",   "#3b8ed0"),
        "IRIKURA1": ("Irikura Recipe 1",   "#22aa55"),
        "SONG"    : ("Song RMG",           "#8855cc"),
    }
    # Fixed run order — deterministic regardless of click order.
    METHOD_ORDER = ["GP", "IRIKURA1", "SONG"]

    def __init__(self, master, app_root, on_dashboard_callback=None,
                 on_results_callback=None):
        super().__init__(master, fg_color="transparent")

        # app_root is the actual Tk root (main.App instance), needed
        # because SimulationPanel is a CTkToplevel and requires a real
        # window as master — self.master here is just the container
        # Frame this panel is packed into, which cannot parent a
        # Toplevel correctly.
        self._app_root             = app_root
        self.on_dashboard_callback = on_dashboard_callback
        self.on_results_callback   = on_results_callback

        self._selected_methods = set()
        self._run_queue        = []   # populated by generate_files()

        # Same hover-help convention as GravesAndPitarkaPanel/IrikuraPanel/
        # SongPanel: field labels bind <Enter> to show_help(tag), which
        # writes into the shared help_label (also used for status/
        # validation messages, same dual-use as the other panels).
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
        }

        self._build_ui()

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 0))

        ctk.CTkLabel(
            header,
            text="Rupture Generator",
            font=res.FONT_TITLE,
            text_color="white"
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=("Generate rupture models (.srf) from a single fault "
                  "geometry using one or more rupture generators — no "
                  "stations or broadband pipeline required."),
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        ).pack(anchor="w", pady=(2, 12))

        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        main_split.grid_columnconfigure(0, weight=3)
        main_split.grid_columnconfigure(1, weight=2)
        main_split.grid_rowconfigure(0, weight=1)

        outer = ctk.CTkScrollableFrame(main_split, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # --- EXPERIMENTER / EXPERIMENT NAME ---
        name_frame = ctk.CTkFrame(outer, fg_color="#1a1a1a", corner_radius=8)
        name_frame.pack(fill="x", pady=(0, 12))
        name_frame.grid_columnconfigure((1, 3), weight=1)

        lbl_experimenter = ctk.CTkLabel(
            name_frame, text="Experimenter",
            font=(res.FONT_LABEL[0], 11)
        )
        lbl_experimenter.grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        lbl_experimenter.bind("<Enter>", lambda e: self.show_help("EXPERIMENTER"))
        self.ent_experimenter = ctk.CTkEntry(name_frame, height=30)
        self.ent_experimenter.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")

        lbl_exp_name = ctk.CTkLabel(
            name_frame, text="Experiment Name",
            font=(res.FONT_LABEL[0], 11)
        )
        lbl_exp_name.grid(row=0, column=2, padx=(0, 6), pady=10, sticky="w")
        lbl_exp_name.bind("<Enter>", lambda e: self.show_help("EXP_NAME"))
        self.ent_exp_name = ctk.CTkEntry(name_frame, height=30)
        self.ent_exp_name.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="ew")

        # --- FAULT GEOMETRY ---
        geo_frame = ctk.CTkFrame(outer, fg_color="#1a1a1a", corner_radius=8)
        geo_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            geo_frame, text="Fault Geometry",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        cols_frame = ctk.CTkFrame(geo_frame, fg_color="transparent")
        cols_frame.pack(fill="x", padx=14, pady=(0, 12))
        cols_frame.grid_columnconfigure((0, 1), weight=1)

        left_col  = ctk.CTkFrame(cols_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        right_col = ctk.CTkFrame(cols_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.src_inputs = {}

        left_params = [
            ("Magnitude",     "MAGNITUDE",      "6.5",      "Mw"),
            ("Fault Width",   "FAULT_WIDTH",    "10.0",     "km"),
            ("Fault Length",  "FAULT_LENGTH",   "20.0",     "km"),
            ("Depth to Top",  "DEPTH_TO_TOP",   "5.0",      "km"),
            ("Strike",        "STRIKE",         "180",      "°"),
            ("Dip",           "DIP",            "90",       "°"),
        ]
        right_params = [
            ("Rake",               "RAKE",            "0",        "°"),
            ("Hypo. Down Dip",     "HYPO_DOWN_DIP",   "5.0",      "km"),
            ("Hypo. Along Strike", "HYPO_ALONG_STK",  "10.0",     "km"),
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
                lbl.bind("<Enter>", lambda e, k=key: self.show_help(k))

                ent = ctk.CTkEntry(parent, height=28)
                ent.insert(0, default)
                ent.grid(row=i, column=1, padx=(0, 2), pady=3, sticky="ew")
                ent.bind("<KeyRelease>", lambda e: self.trigger_map_update())
                self.src_inputs[key] = ent

                ctk.CTkLabel(
                    parent, text=unit,
                    font=(res.FONT_LABEL[0], 10),
                    text_color="gray", width=22, anchor="w"
                ).grid(row=i, column=2, padx=(2, 4), pady=3, sticky="w")

        _build_col(left_col,  left_params)
        _build_col(right_col, right_params)

        # --- SUBFAULT GRID: DLEN / DWID / SEED ---
        grid_frame = ctk.CTkFrame(outer, fg_color="#1a1a1a", corner_radius=8)
        grid_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            grid_frame, text="Subfault Grid",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        adv_grid = ctk.CTkFrame(grid_frame, fg_color="transparent")
        adv_grid.pack(fill="x", padx=14, pady=(0, 12))
        adv_grid.grid_columnconfigure((1, 3, 5), weight=1)

        self.adv_inputs = {}
        # SEED is included alongside DLEN/DWID (not just the two
        # requested) because all three rupture generators need it to
        # produce a reproducible run — without it there is no default
        # to fall back on in the .src file this panel writes.
        adv_params = [("DLEN", "0.1"), ("DWID", "0.1"), ("SEED", "1234567")]
        for i, (param, default) in enumerate(adv_params):
            lbl = ctk.CTkLabel(
                adv_grid, text=param, font=(res.FONT_LABEL[0], 11)
            )
            lbl.grid(row=0, column=i * 2, padx=8, pady=6, sticky="w")
            lbl.bind("<Enter>", lambda e, p=param: self.show_help(p))

            entry = ctk.CTkEntry(adv_grid, height=30)
            entry.insert(0, default)
            entry.grid(row=0, column=i * 2 + 1, padx=(0, 8), pady=6, sticky="ew")
            self.adv_inputs[param] = entry

        # --- METHOD SELECTION (multi-select) ---
        method_frame = ctk.CTkFrame(outer, fg_color="#1a1a1a", corner_radius=8)
        method_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            method_frame, text="Rupture Generators",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            method_frame,
            text="Select one, two, or three — each generates its own .srf from the same geometry above.",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(anchor="w", padx=14, pady=(0, 8))

        btn_row = ctk.CTkFrame(method_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        self._method_buttons = {}
        for i, method in enumerate(self.METHOD_ORDER):
            label, color = self.METHOD_INFO[method]
            btn = ctk.CTkButton(
                btn_row,
                text=label,
                height=40,
                fg_color="#222222",
                border_width=2,
                border_color=color,
                text_color=color,
                hover_color="#2a2a2a",
                command=lambda m=method: self._toggle_method(m)
            )
            btn.grid(row=0, column=i, padx=6, sticky="ew")
            self._method_buttons[method] = btn

        # --- ACTIONS ---
        action_frame = ctk.CTkFrame(outer, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 8))
        action_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_generate = ctk.CTkButton(
            action_frame,
            text="Generate Files",
            height=40,
            fg_color="#444444",
            hover_color="#555555",
            command=self.generate_files
        )
        self.btn_generate.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_simulate = ctk.CTkButton(
            action_frame,
            text="Simulate",
            height=40,
            fg_color="#666666",
            hover_color="#777777",
            state="disabled",
            command=self.run_simulation
        )
        self.btn_simulate.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.help_label = ctk.CTkLabel(
            outer, text="Hover over a parameter label for description",
            font=(res.FONT_LABEL[0], 11), text_color="gray",
            wraplength=760, justify="left"
        )
        self.help_label.pack(anchor="w", pady=(6, 0))

        # --- RIGHT COLUMN: read-only fault/hypocenter map ---
        # No station list exists in this panel (rupture-only profiles
        # never reach Plot_Map/PlotSeis), so FaultMapPanel is used
        # instead of StationPanel — same fault-geometry math, but with
        # every station control/scatter/manual-add feature removed.
        self.fault_map = FaultMapPanel(main_split, update_callback=self.trigger_map_update)
        self.fault_map.grid(row=0, column=1, sticky="nsew")

        # Initial draw with the default field values, same convention
        # as GP/Irikura1/Song panels (debounced redraw on <KeyRelease>).
        self._execute_map_update()

    # ------------------------------------------------------------
    # MAP UPDATE (debounced, same pattern as GP/Irikura1/Song panels)
    # ------------------------------------------------------------
    def trigger_map_update(self):
        if not self.winfo_exists():
            return
        if hasattr(self, "_map_timer") and self._map_timer:
            try:
                self.after_cancel(self._map_timer)
            except Exception:
                pass
        self._map_timer = self.after(350, self._execute_map_update)

    def _execute_map_update(self):
        self._map_timer = None
        if not self.winfo_exists():
            return
        try:
            fault_params = {
                "lat_top"   : float(self.src_inputs["LAT_TOP_CENTER"].get()),
                "lon_top"   : float(self.src_inputs["LON_TOP_CENTER"].get()),
                "strike"    : float(self.src_inputs["STRIKE"].get()),
                "fault_len" : float(self.src_inputs["FAULT_LENGTH"].get()),
                "fault_wid" : float(self.src_inputs["FAULT_WIDTH"].get()),
                "dip"       : float(self.src_inputs["DIP"].get()),
                "depth_top" : float(self.src_inputs["DEPTH_TO_TOP"].get()),
                "hypo_stk"  : float(self.src_inputs["HYPO_ALONG_STK"].get()),
                "hypo_dip"  : float(self.src_inputs["HYPO_DOWN_DIP"].get()),
            }
            self.fault_map.redraw(fault_params)
        except Exception:
            pass

    # ------------------------------------------------------------
    # HOVER HELP
    # ------------------------------------------------------------
    def show_help(self, tag):
        """Updates the shared help label with a parameter description on hover."""
        try:
            if tag:
                text  = self.descriptions.get(tag, "")
                color = "white"
            else:
                text  = "Hover over a parameter label for description"
                color = "gray"
            self.help_label.configure(text=text, text_color=color)
        except Exception:
            pass

    # ------------------------------------------------------------
    # METHOD SELECTION
    # ------------------------------------------------------------
    def _toggle_method(self, method):
        label, color = self.METHOD_INFO[method]
        btn = self._method_buttons[method]

        if method in self._selected_methods:
            self._selected_methods.discard(method)
            btn.configure(fg_color="#222222", text_color=color)
        else:
            self._selected_methods.add(method)
            btn.configure(fg_color=color, text_color="white")

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------
    def _validate_inputs(self):
        for key, entry in self.src_inputs.items():
            try:
                float(entry.get())
            except ValueError:
                return False, f"{key} must be a number."
        for key, entry in self.adv_inputs.items():
            try:
                float(entry.get())
            except ValueError:
                return False, f"{key} must be a number."
        return True, ""

    # ------------------------------------------------------------
    # GENERATE FILES
    # ------------------------------------------------------------
    def generate_files(self):
        """
        Writes one .src file per selected method (each with its own
        "# METHOD = X" marker) plus one shared dummy .stl file, then
        queues each method for a rupture-only run.
        """
        user = self.ent_experimenter.get().strip().replace(" ", "_")
        exp  = self.ent_exp_name.get().strip().replace(" ", "_")

        if not user or not exp:
            self.help_label.configure(
                text="CRITICAL: Experimenter and Experiment Name are required.",
                text_color=res.COLOR_ERROR
            )
            return

        if not self._selected_methods:
            self.help_label.configure(
                text="CRITICAL: Select at least one rupture generator (GP, Irikura Recipe 1, or Song RMG).",
                text_color=res.COLOR_ERROR
            )
            return

        valid, err_msg = self._validate_inputs()
        if not valid:
            self.help_label.configure(text=f"Validation Error: {err_msg}", text_color=res.COLOR_ERROR)
            return

        base_stem = f"{user}_{exp}"

        # --- SHARED DUMMY .stl ---
        # Rupture-only profiles never reach Plot_Map/PlotSeis, so this
        # station has no scientific role. It exists only because BBP's
        # XML header still references a station-list path — a run
        # without one is not a configuration this panel needs to
        # support. Placed near the fault's own top-center coordinates
        # so it is at least geographically sensible, not because the
        # rupture generators read it.
        try:
            lat = float(self.src_inputs["LAT_TOP_CENTER"].get())
            lon = float(self.src_inputs["LON_TOP_CENTER"].get())
        except ValueError:
            lat, lon = 34.000, -118.500
        stl_content  = f"{lon:.5f}  {lat:.5f}  DUMMY\n"
        stl_wsl_path = f"{AppConfig.stl_path}/{base_stem}_dummy.stl"

        ok_stl, err_stl = WSLBridge.write_wsl_file(stl_wsl_path, stl_content)
        if not ok_stl:
            self.help_label.configure(
                text=f"Error writing .stl file: {err_stl}", text_color=res.COLOR_ERROR
            )
            return

        # --- ONE .src PER SELECTED METHOD ---
        self._run_queue = []
        for method in self.METHOD_ORDER:
            if method not in self._selected_methods:
                continue

            base = f"{base_stem}_{method}"

            src_lines = [f"# EXPERIMENTER: {user}\n"]
            for k, v in self.src_inputs.items():
                src_lines.append(f"{k} = {v.get()}\n")
            src_lines.append(f"DLEN = {self.adv_inputs['DLEN'].get()}\n")
            src_lines.append(f"DWID = {self.adv_inputs['DWID'].get()}\n")
            src_lines.append(f"SEED = {self.adv_inputs['SEED'].get()}\n")
            src_lines.append("\n")
            src_lines.append("# --- SIMULATION METHOD (at time of run) ---\n")
            src_lines.append(f"# METHOD = {method}\n")
            src_content = "".join(src_lines)

            src_wsl_path = f"{AppConfig.src_path}/{base}.src"
            ok_src, err_src = WSLBridge.write_wsl_file(src_wsl_path, src_content)
            if not ok_src:
                self.help_label.configure(
                    text=f"Error writing .src file for {method}: {err_src}",
                    text_color=res.COLOR_ERROR
                )
                return

            self._run_queue.append({
                "method"    : method,
                "base_name" : base,
                "src_path"  : src_wsl_path,
                "stl_path"  : stl_wsl_path,
            })

        self.btn_simulate.configure(state="normal")
        queued = " -> ".join(entry["method"] for entry in self._run_queue)
        self.help_label.configure(
            text=f"SUCCESS — Files saved for {base_stem}. Queued: {queued}",
            text_color=res.COLOR_SUCCESS
        )

    # ------------------------------------------------------------
    # SIMULATE — runs the queue one method at a time, automatically
    # chaining to the next until it's empty.
    # ------------------------------------------------------------
    def run_simulation(self):
        self._run_next_in_queue()

    def _run_next_in_queue(self):
        if not self._run_queue:
            # Queue exhausted — hand control back to the real
            # Dashboard/Results navigation, same as every other panel.
            if self.on_dashboard_callback:
                self.on_dashboard_callback()
            return

        entry = self._run_queue.pop(0)

        AppConfig.simulation_method  = entry["method"]
        AppConfig.simulation_profile = "rupture"
        AppConfig.current_src_file   = entry["src_path"]
        AppConfig.current_stl_file   = entry["stl_path"]
        AppConfig.current_base_name  = entry["base_name"]

        is_last = not self._run_queue

        SimulationPanel(
            master                = self._app_root,
            base_name             = entry["base_name"],
            src_path              = entry["src_path"],
            stl_path              = entry["stl_path"],
            on_results_callback   = self.on_results_callback,
            on_dashboard_callback = (
                self.on_dashboard_callback if is_last
                else self._run_next_in_queue
            ),
        )