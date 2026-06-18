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


class ExSimPanel(ctk.CTkFrame):
    """
    Configuration panel for the ExSIM stochastic broadband method.

    ExSIM uses the same .src/.stl fault geometry and station description
    format as GP, but has no kinematic rupture model (no Genslip, no .srf)
    and no separate LF/HF split (no Jbsim/Hfsims/Match). The full pipeline
    is: ExSim -> Plot_Map -> PlotSeis -> RotD100 -> FAS -> GenHTML.

    Only the "Full Pipeline" profile is supported for ExSIM — there is no
    Custom module picker, since the pipeline is already short and every
    module depends on the previous one's output.

    There is no Advanced Settings button here: ExSIM's path parameters
    (quality factor, geometric spreading) are hardcoded directly inside
    the labasin_exsim.par template, not read from the velocity model
    config file the way GP's KAPPA/QFEXP/SDROP/etc. are. Exposing those
    would require editing the template + ExSim's source, which is a
    separate, larger investigation — not a config-file toggle.
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
            "SEED"            : "Random Seed — integer for reproducibility of stochastic elements.",
        }

        # --- METADATA ---
        self.meta_frame = ctk.CTkFrame(
            self, border_width=2, border_color="#ffaa44", fg_color="#222222"
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
            text="Fault Geometry Parameters (.src) — ExSIM",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#ffaa44"
        ).pack(pady=8)

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
                ent.bind("<KeyRelease>", lambda e: self.trigger_map_update())
                self.src_inputs[key] = ent

                ctk.CTkLabel(
                    parent, text=unit,
                    font=(res.FONT_LABEL[0], 10),
                    text_color="gray", width=22, anchor="w"
                ).grid(row=i, column=2, padx=(2, 4), pady=3, sticky="w")

        _build_col(left_col,  left_params)
        _build_col(right_col, right_params)

        # --- SEED ---
        # No DLEN/DWID widgets shown here — ExSIM's own logic never
        # uses subfault discretization (no Genslip step), so exposing
        # these to the user would be misleading. Fixed default values
        # are still written silently into the .src file at generate
        # time (see generate_files) purely to satisfy BBP's shared
        # .src parser, which requires both keys for every method.
        self.seed_frame = ctk.CTkFrame(
            self.left_column, fg_color="#252525", border_width=1, border_color="#444"
        )
        self.seed_frame.pack(fill="x", pady=(0, 5))

        seed_row = ctk.CTkFrame(self.seed_frame, fg_color="transparent")
        seed_row.pack(fill="x", padx=15, pady=8)

        lbl = ctk.CTkLabel(seed_row, text="SEED", font=(res.FONT_LABEL[0], 11))
        lbl.pack(side="left", padx=(0, 8))
        lbl.bind("<Enter>", lambda e: self.show_help("SEED"))
        lbl.bind("<Leave>", lambda e: self.show_help(""))

        self.ent_seed = ctk.CTkEntry(seed_row, height=30, width=120)
        self.ent_seed.insert(0, "1234567")
        self.ent_seed.pack(side="left")

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
            border_color=res.COLOR_PRIMARY,
            text_color="white",
            hover_color="#2a2a2a",
            command=self.open_chino_hills_panel
        )
        self.btn_chino_ref.pack(side="left", expand=True, padx=(5, 0))

        # --- SIMULATION PROFILE (informational only — ExSIM is Full Pipeline only) ---
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

        ctk.CTkLabel(
            self.profile_frame,
            text="Full Pipeline",
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color="#ffaa44"
        ).pack(anchor="w", padx=10, pady=(0, 2))

        ctk.CTkLabel(
            self.profile_frame,
            text=(
                "6 modules — ExSim → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML.\n"
                "ExSIM has no kinematic rupture step and no LF/HF split, "
                "so this is the only profile available."
            ),
            font=(res.FONT_LABEL[0], 10),
            text_color="#aaaaaa",
            wraplength=320,
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        AppConfig.simulation_profile = "full"

        # --- FIXED HELP LABEL ---
        help_container = ctk.CTkFrame(
            self.bottom_bar,
            fg_color="transparent",
            width=420,
            height=46
        )
        help_container.pack(side="left", padx=10, pady=12)
        help_container.pack_propagate(False)

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
            fg_color="#3b8ed0",
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

    # ------------------------------------------------------------------
    # FULLSCREEN
    # ------------------------------------------------------------------

    def _set_fullscreen(self):
        """Maximizes the parent window when ExSimPanel is loaded."""
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

    def trigger_map_update(self):
        """
        Schedules a map redraw with 350ms debounce.
        Cancels any pending redraw before scheduling a new one.
        """
        if not self.winfo_exists():
            return
        if hasattr(self, "_map_timer") and self._map_timer:
            try:
                self.after_cancel(self._map_timer)
            except Exception:
                pass
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

    # ------------------------------------------------------------------
    # STATION MANAGEMENT
    # ------------------------------------------------------------------

    def add_manual_station(self):
        """
        Validates and adds a manual station to the map. If the station
        falls outside the LABasin500 model extent, it is still added
        (BBP silently clips to the nearest available Green's Function
        entry rather than erroring), but a clear warning is shown.
        """
        try:
            lon  = float(self.ent_man_lon.get())
            lat  = float(self.ent_man_lat.get())
            name = self.ent_man_name.get().strip() or f"M{len(self.manual_station_list)}"

            self.manual_station_list.append((lon, lat, name))
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
        self.trigger_map_update()
        self.help_label.configure(
            text="Manual stations cleared.", text_color="gray"
        )

    def toggle_real_stations(self):
        """Toggles the real station reference layer on the map."""
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
        """
        Opens the Chino Hills 2008 reference panel — same panel GP
        uses. The reference data (real magnitude, fault geometry,
        station list) is useful context regardless of simulation
        method; some fields (DLEN/DWID) are GP-specific subfault
        discretization values ExSIM doesn't use, but they're shown
        as-is rather than maintaining a separate ExSIM-trimmed copy.
        """
        ChinoHillsPanel(self.winfo_toplevel())

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

        try:
            int(self.ent_seed.get())
        except ValueError:
            return False, "SEED: must be an integer."

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
        # ExSIM reads the same .src fields as GP for fault geometry.
        # DLEN/DWID — ExSIM's own logic never reads these (no Genslip
        # subfault discretization step), but BBP's shared .src parser
        # (bband_utils.parse_src_file, used by every method including
        # ExSIM) unconditionally requires both keys to be present or
        # it raises ParameterError. Confirmed directly via traceback:
        # "ParameterError: key dlen missing in src file" when these
        # were omitted. 0.1 km matches GP's own default subfault size,
        # used here purely to satisfy the parser.
        src_lines = [f"# EXPERIMENTER: {user}\n"]
        for k, v in self.src_inputs.items():
            src_lines.append(f"{k} = {v.get()}\n")
        src_lines.append("DLEN = 0.1\n")
        src_lines.append("DWID = 0.1\n")
        src_lines.append(f"SEED = {self.ent_seed.get()}\n")
        src_lines.append("\n")
        src_lines.append("# --- SIMULATION METHOD (at time of run) ---\n")
        src_lines.append("# METHOD = EXSIM\n")
        src_content = "".join(src_lines)

        # --- BUILD .stl CONTENT ---
        stations = self.station_module.get_stations()

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

        # Store filenames for use by the simulation stage
        AppConfig.current_src_file  = src_wsl_path
        AppConfig.current_stl_file  = stl_wsl_path
        AppConfig.current_base_name = base
        AppConfig.simulation_profile = "full"
        AppConfig.simulation_method  = "EXSIM"

        self.btn_run.configure(state="normal")
        self.help_label.configure(
            text=f"SUCCESS — Files saved for experiment: {base}",
            text_color=res.COLOR_SUCCESS
        )

    # ------------------------------------------------------------------
    # BBP SIMULATION
    # ------------------------------------------------------------------

    def run_bbp(self):
        """Triggers the ExSIM simulation via the MainPanel callback."""
        AppConfig.simulation_method = "EXSIM"
        if self._on_run_callback:
            self._on_run_callback()