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


class WSLFileBrowser(ctk.CTkToplevel):
    """
    A file browser dialog that navigates the WSL filesystem.
    Shows folders and files separately. Double-click a folder to enter it,
    double-click a file to select it. Filters by extension if provided.

    Usage:
        WSLFileBrowser(
            master     = self,
            start_path = "/home/black/bbp_data/outdata",
            extension  = ".srf",
            title      = "Select SRF File",
            on_select  = callback_fn   # called with the full WSL path
        )
    """

    def __init__(self, master, start_path, on_select,
                 extension=None, title="Browse WSL Files"):
        super().__init__(master)
        self._on_select  = on_select
        self._extension  = extension
        self._cur_path   = start_path

        self.title(title)
        self.geometry("700x480")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self._load_dir(start_path)

        # Center on parent and grab after window is visible
        self.update_idletasks()
        px = master.winfo_rootx()
        py = master.winfo_rooty()
        pw = master.winfo_width()
        ph = master.winfo_height()
        w, h = 700, 480
        self.geometry(f"{w}x{h}+{px + (pw-w)//2}+{py + (ph-h)//2}")
        self.deiconify()
        self.lift()
        self.focus_force()
        self.after(100, self.grab_set)

    def _build_ui(self):
        # Path bar
        top = ctk.CTkFrame(self, fg_color="#111111", height=40)
        top.pack(fill="x", padx=8, pady=(8, 4))
        top.pack_propagate(False)

        ctk.CTkButton(
            top, text="↑ Up", width=60, height=28,
            fg_color="#333333", hover_color="#444444",
            command=self._go_up
        ).pack(side="left", padx=(6, 4), pady=6)

        self.lbl_path = ctk.CTkLabel(
            top, text="", font=("Courier", 11),
            text_color="#aaaaaa", anchor="w"
        )
        self.lbl_path.pack(side="left", fill="x", expand=True, padx=4)

        # Folder list
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=8, pady=4)
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(mid, text="Folders", font=(res.FONT_LABEL[0], 11, "bold"),
                     text_color="#aaaacc").grid(row=0, column=0, sticky="w", padx=4)
        ctk.CTkLabel(mid, text=f"Files ({self._extension or 'all'})",
                     font=(res.FONT_LABEL[0], 11, "bold"),
                     text_color="#aaccaa").grid(row=0, column=1, sticky="w", padx=4)

        # Folder listbox
        folder_frame = ctk.CTkFrame(mid, fg_color="#111122")
        folder_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        self.lb_folders = ctk.CTkScrollableFrame(folder_frame, fg_color="#111122")
        self.lb_folders.pack(fill="both", expand=True)

        # File listbox
        file_frame = ctk.CTkFrame(mid, fg_color="#112211")
        file_frame.grid(row=1, column=1, sticky="nsew")
        self.lb_files = ctk.CTkScrollableFrame(file_frame, fg_color="#112211")
        self.lb_files.pack(fill="both", expand=True)

        # Bottom bar
        bot = ctk.CTkFrame(self, fg_color="#111111", height=50)
        bot.pack(fill="x", padx=8, pady=(4, 8))
        bot.pack_propagate(False)

        self.lbl_selected = ctk.CTkLabel(
            bot, text="No file selected",
            font=("Courier", 10), text_color="#777777", anchor="w"
        )
        self.lbl_selected.pack(side="left", fill="x", expand=True, padx=8, pady=12)

        ctk.CTkButton(
            bot, text="Cancel", width=80, height=32,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=(4, 8), pady=8)

        self.btn_select = ctk.CTkButton(
            bot, text="Select", width=100, height=32,
            fg_color="#1a4a1a", hover_color="#2a6a2a",
            text_color="#88dd88", state="disabled",
            command=self._confirm_select
        )
        self.btn_select.pack(side="right", padx=4, pady=8)

        self._selected_path = None

    def _load_dir(self, path):
        self._cur_path = path
        self.lbl_path.configure(text=path)
        self._selected_path = None
        self.lbl_selected.configure(text="No file selected")
        self.btn_select.configure(state="disabled")

        # Clear existing buttons
        for widget in self.lb_folders.winfo_children():
            widget.destroy()
        for widget in self.lb_files.winfo_children():
            widget.destroy()

        ok, folders, files, err = WSLBridge.list_wsl_dir_detailed(path)
        if not ok:
            ctk.CTkLabel(self.lb_folders,
                         text=f"Error: {err}",
                         text_color="#ff6666").pack(anchor="w", padx=6, pady=2)
            return

        # Render folders
        for folder in folders:
            ctk.CTkButton(
                self.lb_folders,
                text=f"📁 {folder}",
                fg_color="transparent", hover_color="#2a2a4a",
                text_color="#aaaadd", anchor="w", height=28,
                font=(res.FONT_LABEL[0], 10),
                command=lambda f=folder: self._load_dir(f"{self._cur_path}/{f}")
            ).pack(fill="x", padx=2, pady=1)

        if not folders:
            ctk.CTkLabel(self.lb_folders,
                         text="(no subfolders)",
                         text_color="#555555",
                         font=(res.FONT_LABEL[0], 9)).pack(anchor="w", padx=6, pady=4)

        # Render files filtered by extension
        shown = [f for f in files
                 if self._extension is None or f.endswith(self._extension)]

        for fname in shown:
            full_path = f"{self._cur_path}/{fname}"
            ctk.CTkButton(
                self.lb_files,
                text=f"📄 {fname}",
                fg_color="transparent", hover_color="#1a3a1a",
                text_color="#aaddaa", anchor="w", height=28,
                font=(res.FONT_LABEL[0], 10),
                command=lambda p=full_path, n=fname: self._select_file(p, n)
            ).pack(fill="x", padx=2, pady=1)

        if not shown:
            ext_txt = self._extension or "files"
            ctk.CTkLabel(self.lb_files,
                         text=f"(no {ext_txt} here)",
                         text_color="#555555",
                         font=(res.FONT_LABEL[0], 9)).pack(anchor="w", padx=6, pady=4)

    def _go_up(self):
        parent = "/".join(self._cur_path.rstrip("/").rsplit("/", 1)[:-1])
        if parent:
            self._load_dir(parent)

    def _select_file(self, full_path, fname):
        self._selected_path = full_path
        self.lbl_selected.configure(
            text=fname, text_color="#88dd88"
        )
        self.btn_select.configure(state="normal")

    def _confirm_select(self):
        if self._selected_path and self._on_select:
            self._on_select(self._selected_path)
        self.destroy()


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

        # --- ADVANCED PATH PARAMETERS ---
        # These are the Q and geometric spreading values hardcoded as
        # plain numbers in labasin_exsim.par. Confirmed editable by
        # empirical test (10x Q reduction produced ~12x amplitude
        # difference at T=0.1s — June 2026). Exposing them here lets
        # the user adapt ExSIM for different regions (e.g. Eastern
        # North America for Charlevoix) without manually editing the
        # .par file. Defaults match the distributed labasin_exsim.par.
        self.adv_exsim_expanded = False

        self.adv_exsim_frame = ctk.CTkFrame(
            self.left_column, fg_color="#1e1e1e",
            border_width=1, border_color="#3a1a00", corner_radius=6
        )
        self.adv_exsim_frame.pack(fill="x", pady=(6, 0), padx=5)

        self.btn_adv_exsim_toggle = ctk.CTkButton(
            self.adv_exsim_frame,
            text="▶  Advanced Path Parameters",
            fg_color="transparent",
            text_color="#ffaa44",
            hover_color="#2a1500",
            font=(res.FONT_LABEL[0], 12, "bold"),
            anchor="w",
            command=self._toggle_adv_exsim
        )
        self.btn_adv_exsim_toggle.pack(fill="x", padx=6, pady=4)

        self.adv_exsim_content = ctk.CTkFrame(
            self.adv_exsim_frame, fg_color="transparent"
        )
        # Not packed yet — revealed on toggle

        # Defaults matching labasin_exsim.par exactly
        self._adv_exsim_defaults = {
            "QMIN"   : "150",
            "Q0"     : "187",
            "ETA"    : "0.55",
            "BETA"   : "3.7",
            "RHO"    : "2.8",
        }
        # Subfault grid defaults (dl, dw in km) — must match Genslip DLEN/DWID
        self._adv_exsim_defaults["DL"] = "0.1"
        self._adv_exsim_defaults["DW"] = "0.1"

        # Crustal amplification: "default", "ena_hardrock", or "custom"
        self._crustal_amp_mode = "default"
        self._crustal_amp_custom_path = ""

        # Default geometric spreading segments: list of (R_km_str, slope_str).
        # AB06 trilinear uses [(70, -1.3), (140, +0.2), (300, -0.5)]
        self._gs_segments_default = [
            ("1.0",  "-1.0"),
            ("40.0", "-0.5"),
        ]
        # Live segment list — each entry: (CTkEntry_R, CTkEntry_S, row_frame)
        self._gs_segment_rows = []

        # Default D(R) segments: list of (R_km_str, coeff_str) tuples.
        # AB06: (10, 0.0), (70, 0.16), (130, 0.03), (300, 0.04)
        # Each pair = (distance cutoff km, duration growth coefficient d)
        # Final segment's coefficient applies beyond its cutoff.
        self._dr_segments_default = [
            ("10",  "0.0"),
            ("70",  "0.16"),
            ("130", "0.03"),
            ("300", "0.04"),
        ]
        # Live D(R) segment rows — (CTkEntry_R, CTkEntry_d, row_frame)
        self._dr_segment_rows = []

        self.adv_exsim_inputs = {}

        adv_descriptions = {
            "QMIN"        : "Minimum quality factor — lower Q = more attenuation. ENA typical: 600+.",
            "Q0"          : "Q scale factor — Q = max(Qmin, Q0 × F^eta). ENA typical: 600–900.",
            "ETA"         : "Q frequency exponent — controls how Q grows with frequency.",
            "BETA"        : "Reference shear wave velocity (km/s) at the source depth.",
            "RHO"         : "Crustal density (g/cm³) at the source depth.",
            "ISLIPWEIGHT" : (
                "Controls how slip is distributed across the fault subfaults. "
                "Uniform: same slip everywhere. "
                "Random: ExSIM generates a random slip pattern (controlled by SEED). "
                "From file: load a specific slip distribution from a text file."
            ),
            "SLIP_FILE"   : "Path to the slip weights text file (required when islipweight = 0).",
        }

        param_rows = [
            ("Quality Factor",     [("Qmin",  "QMIN"), ("Q0",   "Q0"),   ("eta", "ETA")]),
            ("Crustal Properties", [("β (km/s)", "BETA"), ("ρ (g/cm³)", "RHO")]),
        ]

        for section_title, params in param_rows:
            if section_title:
                ctk.CTkLabel(
                    self.adv_exsim_content,
                    text=section_title,
                    font=(res.FONT_LABEL[0], 11, "bold"),
                    text_color="#ffaa44",
                    anchor="w"
                ).pack(anchor="w", padx=12, pady=(8, 2))

            row_frame = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
            row_frame.pack(fill="x", padx=12, pady=(0, 4))

            for col, (label, key) in enumerate(params):
                col_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                col_frame.pack(side="left", expand=True, padx=(0, 10))

                lbl = ctk.CTkLabel(
                    col_frame, text=label,
                    font=(res.FONT_LABEL[0], 10), anchor="w"
                )
                lbl.pack(anchor="w")
                lbl.bind("<Enter>", lambda e, k=key: self.show_help(k))
                lbl.bind("<Leave>", lambda e: self.show_help(""))

                ent = ctk.CTkEntry(col_frame, height=28, width=80)
                ent.insert(0, self._adv_exsim_defaults[key])
                ent.pack(anchor="w")
                self.adv_exsim_inputs[key] = ent

        # Add descriptions to main descriptions dict for hover help
        self.descriptions.update(adv_descriptions)

        # ── SUBFAULT GRID — dl and dw ──
        ctk.CTkLabel(
            self.adv_exsim_content,
            text="Subfault Grid",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        sf_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        sf_row.pack(fill="x", padx=12, pady=(0, 2))

        for sf_label, sf_key in [("dl — along strike (km)", "DL"), ("dw — down dip (km)", "DW")]:
            sf_col = ctk.CTkFrame(sf_row, fg_color="transparent")
            sf_col.pack(side="left", expand=True, padx=(0, 10))
            ctk.CTkLabel(sf_col, text=sf_label,
                         font=(res.FONT_LABEL[0], 10), anchor="w").pack(anchor="w")
            ent = ctk.CTkEntry(sf_col, height=28, width=80)
            ent.insert(0, self._adv_exsim_defaults[sf_key])
            ent.pack(anchor="w")
            self.adv_exsim_inputs[sf_key] = ent

        ctk.CTkLabel(
            self.adv_exsim_content,
            text="Set dl = DLEN and dw = DWID from the GP Rupture Only run "
                 "so Genslip and ExSIM share the same subfault grid — no resampling needed.",
            font=(res.FONT_LABEL[0], 9), text_color="#555555",
            wraplength=480, justify="left", anchor="w"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # ── GEOMETRIC SPREADING — dynamic multi-segment UI ──
        ctk.CTkLabel(
            self.adv_exsim_content,
            text="Geometric Spreading  G(R)",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 2))

        # Column headers
        gs_hdr = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        gs_hdr.pack(fill="x", padx=12, pady=(0, 2))
        for col_txt in ["#", "Distance cutoff (km)", "Slope", ""]:
            ctk.CTkLabel(
                gs_hdr, text=col_txt,
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color="#888888", width=110 if col_txt != "#" else 24, anchor="w"
            ).pack(side="left", padx=(0, 4))

        # Container that holds all segment rows (packed dynamically)
        self._gs_rows_container = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        self._gs_rows_container.pack(fill="x", padx=12)

        # "Add segment" button
        gs_add_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        gs_add_row.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkButton(
            gs_add_row, text="+ Add Segment", width=130, height=26,
            fg_color="#1a3a1a", hover_color="#2a4a2a",
            text_color="#88dd88", font=(res.FONT_LABEL[0], 10),
            command=self._gs_add_segment
        ).pack(side="left")
        ctk.CTkLabel(
            gs_add_row,
            text="AB06 trilinear: 70 km / −1.3  →  140 km / +0.2  →  300 km / −0.5",
            font=(res.FONT_LABEL[0], 9), text_color="#555555"
        ).pack(side="left", padx=(10, 0))

        # Build default GS segments
        for r_val, s_val in self._gs_segments_default:
            self._gs_add_segment(r_val, s_val)

        # ── GS INFO CARD (collapsible) ──
        self._make_collapsible_info_card(
            parent      = self.adv_exsim_content,
            title       = "What does Geometric Spreading control?",
            color       = "#1a1a2a",
            label_color = "#aaaacc",
            text_color  = "#777788",
            btn_text    = "ℹ  Show G(R) info",
            lines       = [
                ("Amplitude decay",
                 "Controls how fast ground motion amplitude drops with distance. "
                 "A slope of −1.0 means amplitude halves every time distance doubles "
                 "(body wave behaviour, typical close to the source). "
                 "A slope of −0.5 means slower decay (surface wave / Lg behaviour, "
                 "typical at larger distances)."),
                ("Moho bounce (+0.2)",
                 "In ENA, between ~70–140 km, amplitudes can temporarily increase "
                 "because seismic waves reflect off the base of the crust (the Moho). "
                 "AB06 models this as a positive slope segment (+0.2). "
                 "This is why ENA earthquakes are felt much farther than California events."),
                ("Segments",
                 "Each segment defines a distance range and the decay rate within it. "
                 "Add segments to build the bilinear (2), trilinear (3, AB06 standard), "
                 "or any N-segment model you need. "
                 "The amplitude is continuous — each segment picks up exactly where the previous one left off."),
                ("ENA vs California",
                 "California uses approximately −1.0 for all distances. "
                 "ENA uses a steeper −1.3 close in, then the Moho bounce, then −0.5 far out. "
                 "Using the wrong model for your region will over- or under-predict amplitudes "
                 "at all distances."),
            ]
        )

        # ── PATH DURATION — dynamic multi-segment UI ──
        ctk.CTkLabel(
            self.adv_exsim_content,
            text="Path Duration  D(R)",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        # Column headers
        dr_hdr = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        dr_hdr.pack(fill="x", padx=12, pady=(0, 2))
        for col_txt in ["#", "Distance cutoff (km)", "Coeff d", ""]:
            ctk.CTkLabel(
                dr_hdr, text=col_txt,
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color="#888888", width=110 if col_txt != "#" else 24, anchor="w"
            ).pack(side="left", padx=(0, 4))

        # Container
        self._dr_rows_container = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        self._dr_rows_container.pack(fill="x", padx=12)

        # Add segment button
        dr_add_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        dr_add_row.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkButton(
            dr_add_row, text="+ Add Segment", width=130, height=26,
            fg_color="#1a3a1a", hover_color="#2a4a2a",
            text_color="#88dd88", font=(res.FONT_LABEL[0], 10),
            command=self._dr_add_segment
        ).pack(side="left")
        ctk.CTkLabel(
            dr_add_row,
            text="AB06: 10 km/0.0  →  70 km/0.16  →  130 km/0.03  →  300 km/0.04",
            font=(res.FONT_LABEL[0], 9), text_color="#555555"
        ).pack(side="left", padx=(10, 0))

        # Build default D(R) segments
        for r_val, d_val in self._dr_segments_default:
            self._dr_add_segment(r_val, d_val)

        # ── D(R) INFO CARD (collapsible) ──
        self._make_collapsible_info_card(
            parent      = self.adv_exsim_content,
            title       = "What does Path Duration control?",
            color       = "#1a2a1a",
            label_color = "#aaccaa",
            text_color  = "#778877",
            btn_text    = "ℹ  Show D(R) info",
            lines       = [
                ("What it is",
                 "Path duration is how much longer the shaking lasts because of the "
                 "travel path — on top of the source duration (which depends on magnitude). "
                 "Scattered and reflected waves arrive at the site after the direct wave, "
                 "stretching the total signal window."),
                ("Coefficient d",
                 "Each segment has a coefficient d (seconds per km). "
                 "d = 0.0 means duration does not grow in that distance range. "
                 "d = 0.16 means shaking lasts 0.16 seconds longer for every extra km of distance. "
                 "Higher d = longer shaking at farther stations."),
                ("Why segments?",
                 "Duration does not grow at a constant rate with distance. "
                 "Close in (0–10 km) the path adds almost nothing. "
                 "Between 10–70 km it grows fast as scattered waves accumulate. "
                 "Beyond 70 km growth slows because the wavefield becomes more diffuse. "
                 "AB06 uses 4 segments to capture this behaviour."),
                ("Effect on simulations",
                 "Longer duration increases the energy in the simulated signal "
                 "and affects the FAS at low frequencies and the response spectra at long periods. "
                 "Underestimating duration will make far-field simulations look too short and spiky. "
                 "Overestimating it will spread energy over too long a window and underpredict peaks."),
                ("ENA vs California",
                 "ENA has longer path duration than California at the same distance — "
                 "the rigid, low-attenuation crust keeps scattered waves bouncing around "
                 "much longer. This is one reason ENA earthquakes cause felt shaking "
                 "hundreds of kilometres from the epicentre."),
            ]
        )

        # Reset button
        reset_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        reset_row.pack(fill="x", padx=12, pady=(4, 4))

        ctk.CTkButton(
            reset_row,
            text="Reset to LABasin500 Defaults",
            height=28, width=200,
            fg_color="#333333",
            text_color="#aaaaaa",
            hover_color="#2a2a2a",
            command=self._reset_adv_exsim
        ).pack(side="left")

        ctk.CTkLabel(
            reset_row,
            text="For ENA/Charlevoix: Qmin≈600, Q0≈680, eta≈0.35",
            font=(res.FONT_LABEL[0], 9),
            text_color="#666666"
        ).pack(side="left", padx=(10, 0))

        # --- PREVIEW PATH FUNCTIONS BUTTON ---
        preview_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        preview_row.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkButton(
            preview_row,
            text="Preview Path Functions",
            height=30, width=220,
            fg_color="#1a2a3a",
            hover_color="#1e3a5a",
            border_width=1,
            border_color="#2a5a8c",
            text_color="#5ab4ff",
            font=(res.FONT_LABEL[0], 11),
            command=self._preview_path_functions
        ).pack(side="left")

        ctk.CTkLabel(
            preview_row,
            text="Visualize GR×Q attenuation and path duration from current values",
            font=(res.FONT_LABEL[0], 9),
            text_color="#555555"
        ).pack(side="left", padx=(10, 0))

        # --- ISLIPWEIGHT ---
        ctk.CTkLabel(
            self.adv_exsim_content,
            text="Slip Weighting (islipweight)",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        slip_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        slip_row.pack(fill="x", padx=12, pady=(0, 2))

        lbl_slip = ctk.CTkLabel(
            slip_row, text="Mode",
            font=(res.FONT_LABEL[0], 10), anchor="w"
        )
        lbl_slip.pack(side="left", padx=(0, 8))
        lbl_slip.bind("<Enter>", lambda e: self.show_help("ISLIPWEIGHT"))
        lbl_slip.bind("<Leave>", lambda e: self.show_help(""))

        self.islipweight_var = ctk.StringVar(value="Random (1)")
        self.slip_mode_menu = ctk.CTkOptionMenu(
            slip_row,
            values=["Uniform (-1)", "From file (0)", "Random (1)"],
            variable=self.islipweight_var,
            width=160,
            height=28,
            fg_color="#333333",
            button_color="#444444",
            command=self._on_islipweight_change
        )
        self.slip_mode_menu.pack(side="left")

        # "Generate islipweight" button — always visible in the slip section
        ctk.CTkButton(
            slip_row,
            text="⚙ Generate islipweight",
            width=180, height=28,
            fg_color="#1a2a3a",
            hover_color="#2a3a4a",
            border_width=1,
            border_color="#334455",
            text_color="#88aadd",
            font=(res.FONT_LABEL[0], 10),
            command=self._open_genslip_panel
        ).pack(side="left", padx=(12, 0))

        # --- RUPTURE GENERATOR CHOICE (single-select) for the islipweight
        # run above — GP/Genslip, Irikura Recipe 1/IrikuraGenSrf, or
        # Song/SongRMGSS. Unlike RuptureGeneratorPanel's multi-select
        # (which runs several generators independently), only one can
        # ever be selected here, since this single choice feeds directly
        # into ExSIM's own islipweight file. Defaults to GP, matching
        # this panel's behavior before this option existed.
        rupture_choice_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        rupture_choice_row.pack(fill="x", padx=12, pady=(4, 2))

        ctk.CTkLabel(
            rupture_choice_row, text="Rupture generator for islipweight:",
            font=(res.FONT_LABEL[0], 10), text_color="#aaaaaa", anchor="w"
        ).pack(side="left", padx=(0, 8))

        self._islipweight_method = "GP"
        self._islipweight_method_buttons = {}

        RUPTURE_CHOICE_INFO = {
            "GP"      : ("GP",       "#3b8ed0"),
            "IRIKURA1": ("Irikura",  "#22aa55"),
            "SONG"    : ("Song",     "#8855cc"),
        }

        def _select_islipweight_method(method):
            self._islipweight_method = method
            for m, btn in self._islipweight_method_buttons.items():
                label, color = RUPTURE_CHOICE_INFO[m]
                if m == method:
                    btn.configure(fg_color=color, text_color="white")
                else:
                    btn.configure(fg_color="#222222", text_color=color)

        for method, (label, color) in RUPTURE_CHOICE_INFO.items():
            btn = ctk.CTkButton(
                rupture_choice_row,
                text=label,
                width=70, height=26,
                border_width=2,
                border_color=color,
                fg_color=color if method == "GP" else "#222222",
                text_color="white" if method == "GP" else color,
                hover_color="#2a2a2a",
                font=(res.FONT_LABEL[0], 10),
                command=lambda m=method: _select_islipweight_method(m)
            )
            btn.pack(side="left", padx=3)
            self._islipweight_method_buttons[method] = btn

        # File picker row — child of a wrapper placed directly below the dropdown.
        # Using a wrapper means pack()/pack_forget() positions it right here,
        # not at the bottom of adv_exsim_content.
        self._slip_file_wrapper = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        # Not packed yet — only appears when From file (0) is selected
        self.slip_file_row = ctk.CTkFrame(self._slip_file_wrapper, fg_color="transparent")
        # Not packed yet — revealed by _on_islipweight_change

        lbl_sf = ctk.CTkLabel(
            self.slip_file_row, text="Slip file",
            font=(res.FONT_LABEL[0], 10), anchor="w"
        )
        lbl_sf.pack(side="left", padx=(0, 6))
        lbl_sf.bind("<Enter>", lambda e: self.show_help("SLIP_FILE"))
        lbl_sf.bind("<Leave>", lambda e: self.show_help(""))

        self.ent_slip_file = ctk.CTkEntry(
            self.slip_file_row, height=28, width=220,
            placeholder_text="/path/to/slip_weights.txt"
        )
        self.ent_slip_file.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            self.slip_file_row,
            text="Browse…",
            height=28, width=70,
            fg_color="#333333",
            text_color="white",
            hover_color="#444444",
            command=self._browse_slip_file
        ).pack(side="left")

        ctk.CTkButton(
            self.slip_file_row,
            text="⚙ Extract from SRF",
            height=28, width=150,
            fg_color="#1a3a2a",
            hover_color="#2a5a3a",
            border_width=1,
            border_color="#336644",
            text_color="#88ddaa",
            font=(res.FONT_LABEL[0], 10),
            command=self._extract_from_srf
        ).pack(side="left", padx=(8, 0))

        # ── SLIP INFO CARD (collapsible) ──
        self._make_collapsible_info_card(
            parent      = self.adv_exsim_content,
            title       = "What does each option do?",
            color       = "#1a2a1a",
            label_color = "#aaaaaa",
            text_color  = "#777777",
            btn_text    = "ℹ  Show slip weight info",
            lines       = [
                ("Uniform (-1)",
                 "Every subfault receives the same slip amount. "
                 "Simplest option — use when you want a smooth, "
                 "homogeneous rupture with no spatial variation."),
                ("Random (1)",
                 "ExSIM generates a random slip distribution across "
                 "the fault using its internal algorithm. The SEED value "
                 "above controls which random pattern is produced — "
                 "same SEED always gives the same result. "
                 "Recommended default for most simulations."),
                ("From file (0)",
                 "ExSIM reads slip values from a text file you provide. "
                 "Each value represents the slip on one subfault. "
                 "Use this when you have a specific rupture model "
                 "from an external source and want ExSIM to reproduce "
                 "that exact slip pattern."),
            ]
        )

        # ── CRUSTAL AMPLIFICATION ──
        ctk.CTkLabel(
            self.adv_exsim_content,
            text="Crustal Amplification",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        amp_mode_row = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        amp_mode_row.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(amp_mode_row, text="Mode:",
                     font=(res.FONT_LABEL[0], 10), anchor="w",
                     width=50).pack(side="left")

        self.crustal_amp_var = ctk.StringVar(value="BBP Default (California)")
        amp_dropdown = ctk.CTkComboBox(
            amp_mode_row,
            values=["BBP Default (California)", "ENA Hard Rock (AB06)", "Custom file"],
            variable=self.crustal_amp_var,
            width=240, height=28,
            command=self._on_crustal_amp_change
        )
        amp_dropdown.pack(side="left", padx=(4, 8))

        self.btn_amp_preview = ctk.CTkButton(
            amp_mode_row, text="Preview Curve",
            width=120, height=28,
            fg_color="#1a2a3a", hover_color="#2a3a4a",
            text_color="#88aadd",
            font=(res.FONT_LABEL[0], 10),
            command=self._preview_crustal_amp
        )
        self.btn_amp_preview.pack(side="left")

        # Custom file row — child of a wrapper placed directly below the dropdown.
        self._amp_file_wrapper = ctk.CTkFrame(self.adv_exsim_content, fg_color="transparent")
        # Not packed yet — only appears when Custom file is selected
        self.amp_file_row = ctk.CTkFrame(self._amp_file_wrapper, fg_color="transparent")
        # not packed yet

        ctk.CTkLabel(self.amp_file_row, text="File (WSL path):",
                     font=(res.FONT_LABEL[0], 10), anchor="w"
                     ).pack(side="left", padx=(12, 4))
        self.ent_amp_file = ctk.CTkEntry(self.amp_file_row, height=28, width=280,
                                          placeholder_text="/home/user/my_amp.txt")
        self.ent_amp_file.pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            self.amp_file_row, text="Browse…",
            height=28, width=70,
            fg_color="#333333", text_color="white", hover_color="#444444",
            command=self._browse_amp_file
        ).pack(side="left")

        # ── AMP INFO CARD (collapsible) ──
        self._make_collapsible_info_card(
            parent      = self.adv_exsim_content,
            title       = "What does Crustal Amplification do?",
            color       = "#1a1a2a",
            label_color = "#aaaacc",
            text_color  = "#777788",
            btn_text    = "ℹ  Show amplification info",
            lines       = [
                ("What it is",
                 "When seismic waves travel up through the crust, the rock gets softer near "
                 "the surface and the waves slow down. Slower waves = bigger amplitude. "
                 "ExSIM applies a frequency-dependent amplification factor to account for this."),
                ("BBP Default (California)",
                 "Uses the LABasin500 amplification file shipped with BBP. This is calibrated "
                 "for California near-surface rock — it over-amplifies ENA hard-rock sites "
                 "at frequencies above 2 Hz."),
                ("ENA Hard Rock (AB06)",
                 "Uses values from Atkinson & Boore (2006) Table 3, calibrated for ENA "
                 "hard-rock sites (NEHRP Class A, Vs ≥ 2000 m/s). "
                 "Amplification ranges from 1.00 at 0.5 Hz to 1.41 at 10+ Hz. "
                 "This is the correct choice for Charlevoix."),
                ("Custom file",
                 "Provide your own two-column text file (frequency Hz, amplification factor). "
                 "ExSIM interpolates between your points. If no file is given, ExSIM assumes "
                 "flat amplification = 1.0 at all frequencies."),
            ]
        )

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
        with each station added.
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

            ctk.CTkLabel(
                row,
                text=f"{idx + 1}",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="#666666",
                width=22,
                anchor="e"
            ).pack(side="left", padx=(8, 4), pady=6)

            ctk.CTkLabel(
                row,
                text=f"{name}",
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color="gold",
                anchor="w",
                width=65
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                row,
                text=f"lat {lat:.5f}   lon {lon:.5f}",
                font=(res.FONT_LABEL[0], 12),
                text_color="#cccccc",
                anchor="w"
            ).pack(side="left", padx=(0, 6), fill="x", expand=True)

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

        ctk.CTkFrame(
            self.station_list_frame, fg_color="transparent", height=4
        ).pack()

    def _delete_station(self, idx):
        """Removes the station at the given index and refreshes list and map."""
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
        Populates entry fields with the selected station's values
        and removes it from the list, ready to modify and re-add.
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
    # ADVANCED PATH PARAMETERS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # GEOMETRIC SPREADING — dynamic segment management
    # ------------------------------------------------------------------

    def _gs_add_segment(self, r_val="1.0", s_val="-1.0"):
        """Adds one geometric spreading segment row to the container."""
        idx = len(self._gs_segment_rows)

        row = ctk.CTkFrame(self._gs_rows_container, fg_color="transparent")
        row.pack(fill="x", pady=(0, 3))

        # Index label
        ctk.CTkLabel(
            row, text=f"{idx+1}", width=24,
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color="#666666", anchor="center"
        ).pack(side="left", padx=(0, 4))

        # Distance cutoff entry
        ent_r = ctk.CTkEntry(row, height=28, width=110)
        ent_r.insert(0, str(r_val))
        ent_r.pack(side="left", padx=(0, 8))

        # Slope entry
        ent_s = ctk.CTkEntry(row, height=28, width=80)
        ent_s.insert(0, str(s_val))
        ent_s.pack(side="left", padx=(0, 8))

        # Remove button — only shown when more than 1 segment exists
        btn_remove = ctk.CTkButton(
            row, text="−", width=28, height=26,
            fg_color="#3a1a1a", hover_color="#5a2a2a",
            text_color="#ff6666", font=(res.FONT_LABEL[0], 12),
            corner_radius=4,
            command=lambda r=row: self._gs_remove_segment(r)
        )
        btn_remove.pack(side="left")

        self._gs_segment_rows.append((ent_r, ent_s, row))
        self._gs_refresh_remove_buttons()

    def _gs_remove_segment(self, row_frame):
        """Removes the segment row whose frame matches row_frame."""
        self._gs_segment_rows = [
            (er, es, rf) for (er, es, rf) in self._gs_segment_rows
            if rf is not row_frame
        ]
        row_frame.destroy()
        self._gs_refresh_remove_buttons()
        # Renumber index labels
        for i, (er, es, rf) in enumerate(self._gs_segment_rows):
            for child in rf.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text=f"{i+1}")
                    break

    def _gs_refresh_remove_buttons(self):
        """Shows remove buttons only when there are 2+ segments."""
        show = len(self._gs_segment_rows) > 1
        for (er, es, rf) in self._gs_segment_rows:
            children = rf.winfo_children()
            # The remove button is always the last child
            if children:
                btn = children[-1]
                if show:
                    btn.pack(side="left")
                else:
                    btn.pack_forget()

    def _get_gs_segments(self):
        """
        Reads all segment rows and returns a list of (R_km, slope) floats.
        Raises ValueError if any entry is invalid.
        """
        segments = []
        for i, (ent_r, ent_s, _) in enumerate(self._gs_segment_rows):
            try:
                r = float(ent_r.get())
                s = float(ent_s.get())
            except ValueError:
                raise ValueError(f"Segment {i+1}: distance and slope must be numbers.")
            if r <= 0:
                raise ValueError(f"Segment {i+1}: distance cutoff must be > 0.")
            segments.append((r, s))
        if not segments:
            raise ValueError("At least one geometric spreading segment is required.")
        return segments

    # ------------------------------------------------------------------
    # PATH DURATION — dynamic segment management
    # ------------------------------------------------------------------

    def _dr_add_segment(self, r_val="50.0", d_val="0.05"):
        """Adds one D(R) segment row to the container."""
        idx = len(self._dr_segment_rows)

        row = ctk.CTkFrame(self._dr_rows_container, fg_color="transparent")
        row.pack(fill="x", pady=(0, 3))

        ctk.CTkLabel(
            row, text=f"{idx+1}", width=24,
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color="#666666", anchor="center"
        ).pack(side="left", padx=(0, 4))

        ent_r = ctk.CTkEntry(row, height=28, width=110)
        ent_r.insert(0, str(r_val))
        ent_r.pack(side="left", padx=(0, 8))

        ent_d = ctk.CTkEntry(row, height=28, width=80)
        ent_d.insert(0, str(d_val))
        ent_d.pack(side="left", padx=(0, 8))

        btn_remove = ctk.CTkButton(
            row, text="−", width=28, height=26,
            fg_color="#3a1a1a", hover_color="#5a2a2a",
            text_color="#ff6666", font=(res.FONT_LABEL[0], 12),
            corner_radius=4,
            command=lambda r=row: self._dr_remove_segment(r)
        )
        btn_remove.pack(side="left")

        self._dr_segment_rows.append((ent_r, ent_d, row))
        self._dr_refresh_remove_buttons()

    def _dr_remove_segment(self, row_frame):
        """Removes the D(R) segment row matching row_frame."""
        self._dr_segment_rows = [
            (er, ed, rf) for (er, ed, rf) in self._dr_segment_rows
            if rf is not row_frame
        ]
        row_frame.destroy()
        self._dr_refresh_remove_buttons()
        for i, (er, ed, rf) in enumerate(self._dr_segment_rows):
            for child in rf.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text=f"{i+1}")
                    break

    def _dr_refresh_remove_buttons(self):
        """Shows remove buttons only when 2+ segments exist."""
        show = len(self._dr_segment_rows) > 1
        for (er, ed, rf) in self._dr_segment_rows:
            children = rf.winfo_children()
            if children:
                btn = children[-1]
                if show:
                    btn.pack(side="left")
                else:
                    btn.pack_forget()

    def _get_dr_segments(self):
        """
        Returns list of (R_km, coeff_d) floats from UI.
        Raises ValueError on bad input.
        The last segment's coeff applies beyond its cutoff distance.
        """
        segments = []
        for i, (ent_r, ent_d, _) in enumerate(self._dr_segment_rows):
            try:
                r = float(ent_r.get())
                d = float(ent_d.get())
            except ValueError:
                raise ValueError(f"D(R) Segment {i+1}: distance and coefficient must be numbers.")
            if r <= 0:
                raise ValueError(f"D(R) Segment {i+1}: distance cutoff must be > 0.")
            segments.append((r, d))
        if not segments:
            raise ValueError("At least one path duration segment is required.")
        return segments

    # ------------------------------------------------------------------
    # CRUSTAL AMPLIFICATION HANDLERS
    # ------------------------------------------------------------------

    def _on_crustal_amp_change(self, choice):
        """Shows/hides the custom file row directly below the dropdown."""
        if choice == "Custom file":
            self._amp_file_wrapper.pack(fill="x", padx=12, pady=(2, 2))
            self.amp_file_row.pack(fill="x")
        else:
            self.amp_file_row.pack_forget()
            self._amp_file_wrapper.pack_forget()

    def _browse_amp_file(self):
        """Opens a file dialog to select a custom amplification file."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Crustal Amplification File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            import subprocess
            r = subprocess.run(
                ["wsl.exe", "wslpath", "-u", path.replace("\\", "/")],
                capture_output=True, text=True
            )
            wsl_path = r.stdout.strip() if r.returncode == 0 else path
            self.ent_amp_file.delete(0, "end")
            self.ent_amp_file.insert(0, wsl_path)

    def _apply_crustal_amp_file(self):
        """
        Handles crustal amplification by writing values directly to the
        amplification file that BBP's template_replace() will substitute
        for <CRUSTAL_AMP_FILE>.

        Strategy: instead of touching the <CRUSTAL_AMP_FILE> placeholder
        (which breaks BBP's sequential parser), we overwrite the actual
        amplification file that BBP points to in its velocity model.

        BBP substitutes <CRUSTAL_AMP_FILE> with the path from its own
        velocity model config. The default file is:
          ~/bbp_gf/LABasin500/uwo/crustal_amps.txt
        We overwrite that file with ENA or custom values when needed,
        and restore it to California defaults on BBP Default selection.

        Returns (ok: bool, err: str).
        """
        mode = self.crustal_amp_var.get() if hasattr(self, "crustal_amp_var") \
               else "BBP Default (California)"

        home = WSLBridge.get_wsl_home()
        # This is the file BBP points to for crustal amplification
        amp_file = f"{home}/bbp_gf/LABasin500/uwo/crustal_amps.txt"

        if mode == "BBP Default (California)":
            # Leave the file as-is — don't touch it
            return True, ""

        elif mode == "ENA Hard Rock (AB06)":
            # CRITICAL: Fortran reads this with list-directed I/O.
            # First non-blank line MUST be an integer (number of data points).
            # No comment lines (!) before the count.
            ena_content = (
                " 6\n"
                "  0.5    1.00\n"
                "  1.0    1.13\n"
                "  2.0    1.22\n"
                "  5.0    1.36\n"
                " 10.0    1.41\n"
                " 50.0    1.41\n"
            )
            ok, err = WSLBridge.write_wsl_file(amp_file, ena_content)
            if not ok:
                return False, f"Could not write ENA amplification file: {err}"
            return True, ""

        elif mode == "Custom file":
            custom_path = self.ent_amp_file.get().strip()
            if not custom_path:
                return False, "Custom amplification file: no path specified."
            # Read the custom file and write it to the target location
            ok_r, custom_content = WSLBridge.read_wsl_file(custom_path)
            if not ok_r or not custom_content:
                return False, f"Could not read custom amplification file: {custom_path}"
            ok_w, err = WSLBridge.write_wsl_file(amp_file, custom_content)
            if not ok_w:
                return False, f"Could not apply custom amplification file: {err}"
            return True, ""

        return True, ""

    def _get_crustal_amp_path(self):
        """
        Returns the WSL path to the crustal amplification file to use,
        or None if BBP default should be used.

        - BBP Default  → None  (leave <CRUSTAL_AMP_FILE> untouched)
        - ENA Hard Rock → writes the AB06 file to WSL and returns its path
        - Custom file   → returns the user-entered path
        """
        mode = self.crustal_amp_var.get()

        if mode == "BBP Default (California)":
            return None

        if mode == "ENA Hard Rock (AB06)":
            home = WSLBridge.get_wsl_home()
            amp_path = f"{home}/bbp_gf/LABasin500/uwo/ena_hardrock_ab06.txt"
            # Write the file if it doesn't already exist
            ok_exist, _ = WSLBridge.read_wsl_file(amp_path)
            if not ok_exist:
                ena_content = (
                    " 6\n"
                    "  0.5    1.00\n"
                    "  1.0    1.13\n"
                    "  2.0    1.22\n"
                    "  5.0    1.36\n"
                    " 10.0    1.41\n"
                    " 50.0    1.41\n"
                )
                WSLBridge.write_wsl_file(amp_path, ena_content)
            return amp_path

        if mode == "Custom file":
            return self.ent_amp_file.get().strip() or None

        return None

    def _preview_crustal_amp(self):
        """Plots the current crustal amplification curve in a popup window."""
        import numpy as np
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        mode = self.crustal_amp_var.get()

        # AB06 ENA values
        ena_f   = [0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
        ena_amp = [1.00, 1.13, 1.22, 1.36, 1.41, 1.41]

        popup = ctk.CTkToplevel(self.winfo_toplevel())
        popup.title("Crustal Amplification Preview")
        popup.geometry("620x420")
        popup.configure(fg_color="#111111")

        fig, ax = plt.subplots(figsize=(7, 4), facecolor="#111111")
        ax.set_facecolor("#1a1a1a")

        if mode == "BBP Default (California)":
            ax.semilogx([0.1, 0.5, 1, 2, 5, 10, 50],
                        [1.0, 1.4, 1.7, 2.1, 2.3, 2.4, 2.5],
                        color="#5ab4ff", linewidth=2, label="LABasin500 (California)")
            ax.semilogx(ena_f, ena_amp, color="#88dd88", linewidth=1.5,
                        linestyle="--", label="ENA Hard Rock AB06 (reference)")

        elif mode == "ENA Hard Rock (AB06)":
            ax.semilogx(ena_f, ena_amp, color="#88dd88", linewidth=2,
                        label="ENA Hard Rock — AB06 Table 3")
            ax.semilogx([0.1, 0.5, 1, 2, 5, 10, 50],
                        [1.0, 1.4, 1.7, 2.1, 2.3, 2.4, 2.5],
                        color="#5ab4ff", linewidth=1.5,
                        linestyle="--", label="LABasin500 California (reference)")

        elif mode == "Custom file":
            path = self.ent_amp_file.get().strip()
            ok, txt = WSLBridge.read_wsl_file(path) if path else (False, "")
            if ok and txt:
                freqs, amps = [], []
                for ln in txt.splitlines():
                    ln = ln.strip()
                    if not ln or ln.startswith("!") or ln.startswith("#"):
                        continue
                    parts = ln.split()
                    if len(parts) >= 2:
                        try:
                            freqs.append(float(parts[0]))
                            amps.append(float(parts[1]))
                        except ValueError:
                            pass
                if freqs:
                    ax.semilogx(freqs, amps, color="#ffaa44", linewidth=2,
                                label="Custom amplification")
            ax.semilogx(ena_f, ena_amp, color="#88dd88", linewidth=1.5,
                        linestyle="--", label="ENA Hard Rock AB06 (reference)")
        else:
            ax.semilogx([0.1, 50], [1.0, 1.0], color="#aaaaaa",
                        linewidth=2, label="Flat (= 1.0)")

        ax.set_xlabel("Frequency (Hz)", color="white")
        ax.set_ylabel("Amplification factor", color="white")
        ax.set_title(f"Crustal Amplification — {mode}", color="white", fontsize=11)
        ax.tick_params(colors="white")
        ax.spines["bottom"].set_color("#444")
        ax.spines["left"].set_color("#444")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(facecolor="#1a1a1a", edgecolor="#333", labelcolor="white",
                  fontsize=9)
        ax.grid(True, color="#333", linestyle="--", alpha=0.5)
        ax.axhline(1.0, color="#555", linewidth=0.8, linestyle=":")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        canvas.draw()

    # ------------------------------------------------------------------
    # COLLAPSIBLE INFO CARD HELPER
    # ------------------------------------------------------------------

    def _make_collapsible_info_card(self, parent, title, color, lines,
                                     label_color, text_color, btn_text="ℹ  Show info"):
        """
        Builds a collapsible info card with a centered toggle button.
        The card expands directly below the button — not at the bottom of the panel.
        Hidden by default.
        """
        # Wrapper holds both the button and the card together in place
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.pack(fill="x", pady=(6, 2))

        # Toggle button — centered inside the wrapper
        toggle_btn = ctk.CTkButton(
            wrapper,
            text=btn_text,
            width=260, height=32,
            fg_color="#1e1e2e",
            hover_color="#2a2a3a",
            border_width=1,
            border_color="#333355",
            text_color="#8899dd",
            font=(res.FONT_LABEL[0], 10),
            anchor="center"
        )
        toggle_btn.pack(anchor="center")

        # Card frame — packed inside the same wrapper, directly below the button
        card = ctk.CTkFrame(
            wrapper,
            fg_color=color,
            border_width=1,
            border_color="#2a2a4a",
            corner_radius=6
        )
        # NOT packed yet — hidden until toggle

        # Header
        ctk.CTkLabel(
            card,
            text=title,
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color=label_color,
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Content rows
        for lbl, explanation in lines:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=(2, 4))
            ctk.CTkLabel(
                row,
                text=f"• {lbl}:",
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color=label_color,
                anchor="w",
                width=120
            ).pack(side="left", anchor="n")
            ctk.CTkLabel(
                row,
                text=explanation,
                font=(res.FONT_LABEL[0], 9),
                text_color=text_color,
                wraplength=260,
                justify="left",
                anchor="w"
            ).pack(side="left", anchor="n", pady=(0, 2))

        ctk.CTkFrame(card, fg_color="transparent", height=4).pack()

        # Toggle logic
        _state = {"open": False}

        def _toggle():
            if _state["open"]:
                card.pack_forget()
                toggle_btn.configure(text=btn_text)
                _state["open"] = False
            else:
                card.pack(fill="x", padx=4, pady=(4, 2))
                toggle_btn.configure(
                    text=btn_text.replace("Show", "Hide")
                )
                _state["open"] = True

        toggle_btn.configure(command=_toggle)
        return toggle_btn

    def _toggle_adv_exsim(self):
        """Expands or collapses the Advanced Path Parameters section."""
        self.adv_exsim_expanded = not self.adv_exsim_expanded
        if self.adv_exsim_expanded:
            self.adv_exsim_content.pack(fill="x", pady=(0, 4))
            self.btn_adv_exsim_toggle.configure(text="▼  Advanced Path Parameters")
        else:
            self.adv_exsim_content.pack_forget()
            self.btn_adv_exsim_toggle.configure(text="▶  Advanced Path Parameters")

    def _reset_adv_exsim(self):
        """Resets all Advanced Path Parameters to LABasin500 defaults."""
        for key, ent in self.adv_exsim_inputs.items():
            ent.delete(0, "end")
            ent.insert(0, self._adv_exsim_defaults[key])
        # Reset DL/DW
        for key in ("DL", "DW"):
            if key in self.adv_exsim_inputs:
                self.adv_exsim_inputs[key].delete(0, "end")
                self.adv_exsim_inputs[key].insert(0, self._adv_exsim_defaults[key])
        # Reset crustal amplification
        self.crustal_amp_var.set("BBP Default (California)")
        self._on_crustal_amp_change("BBP Default (California)")
        for _, _, rf in self._gs_segment_rows:
            rf.destroy()
        self._gs_segment_rows = []
        for r_val, s_val in self._gs_segments_default:
            self._gs_add_segment(r_val, s_val)
        # Reset D(R) segments to default (AB06 quadlinear)
        for _, _, rf in self._dr_segment_rows:
            rf.destroy()
        self._dr_segment_rows = []
        for r_val, d_val in self._dr_segments_default:
            self._dr_add_segment(r_val, d_val)
        self.islipweight_var.set("Random (1)")
        self._on_islipweight_change("Random (1)")
        self.ent_slip_file.delete(0, "end")
        self.help_label.configure(
            text="Advanced Path Parameters reset to LABasin500 defaults.",
            text_color="gray"
        )

    def _preview_path_functions(self):
        """
        Opens a popup window showing three plots based on the current
        Advanced Path Parameters values:
          1. Geometric spreading GR(R) alone
          2. Combined attenuation GR(R) × exp(-pi*f*R / Q(f)*beta)
             at f=1 Hz and f=10 Hz on the same axes
          3. Path duration vs distance
        These correspond to Boore (2005) SMSIM Figures 3, 4 and 5.
        """
        import numpy as np
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import (
            FigureCanvasTkAgg, NavigationToolbar2Tk
        )

        # --- READ CURRENT VALUES ---
        try:
            Qmin  = float(self.adv_exsim_inputs["QMIN"].get())
            Q0    = float(self.adv_exsim_inputs["Q0"].get())
            eta   = float(self.adv_exsim_inputs["ETA"].get())
            beta  = float(self.adv_exsim_inputs["BETA"].get())
            gs_segs = self._get_gs_segments()
        except ValueError as ve:
            self.help_label.configure(
                text=f"Cannot preview — {ve}",
                text_color=res.COLOR_ERROR
            )
            return

        # --- DISTANCE ARRAY ---
        R = np.logspace(0, np.log10(300), 300)  # 1 to 300 km

        # --- GEOMETRIC SPREADING GR(R) — N segments ---
        # Each segment i covers distances from R_prev to R_i with slope S_i.
        # Amplitude is continuous across segment boundaries.
        def compute_GR(r_arr, segments):
            GR = np.ones_like(r_arr)
            r_prev = segments[0][0]   # first cutoff = reference distance
            GR_boundary = 1.0
            for seg_i, (r_cut, slope) in enumerate(segments):
                if seg_i == 0:
                    # First segment: normalise to 1 at r_prev
                    mask = r_arr <= r_cut
                    GR[mask] = (r_arr[mask] / r_prev) ** slope
                    GR_boundary = (r_cut / r_prev) ** slope
                else:
                    r_prev_cut = segments[seg_i - 1][0]
                    is_last = (seg_i == len(segments) - 1)
                    if is_last:
                        mask = r_arr > r_prev_cut
                    else:
                        mask = (r_arr > r_prev_cut) & (r_arr <= r_cut)
                    GR[mask] = GR_boundary * (r_arr[mask] / r_prev_cut) ** slope
                    if not is_last:
                        GR_boundary = GR_boundary * (r_cut / r_prev_cut) ** slope
            return GR

        GR = compute_GR(R, gs_segs)

        # --- Q(f) AND COMBINED ATTENUATION ---
        def Q_f(f):
            return max(Qmin, Q0 * (f ** eta))

        def combined(f):
            Qval = Q_f(f)
            return GR * np.exp(-np.pi * f * R / (Qval * beta))

        C1  = combined(1.0)
        C10 = combined(10.0)

        try:
            dr_segs = self._get_dr_segments()
        except ValueError as ve:
            self.help_label.configure(
                text=f"Cannot preview — {ve}", text_color=res.COLOR_ERROR
            )
            return

        # --- PATH DURATION D(R) — N segments, linear interpolation ---
        # Each segment i: from R_prev to R_i, duration grows at rate d_i per km.
        # D(0) = 0 (path contribution only; source duration added separately by ExSIM).
        def compute_DR(r_arr, segments):
            D = np.zeros_like(r_arr)
            r_prev = 0.0
            d_accum = 0.0
            for seg_r, seg_d in segments:
                mask = (r_arr > r_prev) & (r_arr <= seg_r)
                D[mask] = d_accum + seg_d * (r_arr[mask] - r_prev)
                d_accum += seg_d * (seg_r - r_prev)
                r_prev = seg_r
            # Beyond last segment: continue with last coefficient
            last_d = segments[-1][1]
            mask_beyond = r_arr > segments[-1][0]
            D[mask_beyond] = d_accum + last_d * (r_arr[mask_beyond] - segments[-1][0])
            return D

        D = compute_DR(R, dr_segs)

        # --- BUILD POPUP WINDOW ---
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Path Function Preview")
        win.configure(fg_color="#0d0d0d")
        win.geometry("1000x780")
        win.transient(self.winfo_toplevel())
        win.lift()
        win.focus_force()

        # Header
        hdr = ctk.CTkFrame(win, fg_color="#111111", corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="Path Function Preview — based on current Advanced Path Parameters",
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color="#5ab4ff"
        ).pack(side="left", padx=15, pady=14)

        ctk.CTkButton(
            hdr, text="Close", width=80, height=30,
            fg_color="#333333", hover_color="#444444",
            command=win.destroy
        ).pack(side="right", padx=12, pady=10)

        # Parameter summary strip
        param_strip = ctk.CTkFrame(win, fg_color="#1a1a1a", corner_radius=0, height=32)
        param_strip.pack(fill="x")
        param_strip.pack_propagate(False)

        gs_summary = "  →  ".join(
            f"R{i+1}={r:.0f} km (s={s:.1f})" for i, (r, s) in enumerate(gs_segs)
        )
        param_text = (
            f"Qmin={Qmin:.0f}  Q0={Q0:.0f}  η={eta:.2f}  β={beta:.2f} km/s  "
            f"GS: {gs_summary}  "
            f"Q(1Hz)={Q_f(1.0):.0f}  Q(10Hz)={Q_f(10.0):.0f}"
        )
        ctk.CTkLabel(
            param_strip,
            text=param_text,
            font=(res.FONT_LABEL[0], 10),
            text_color="#888888"
        ).pack(side="left", padx=14, pady=6)

        # --- EXPLANATION SECTION ---
        explain_frame = ctk.CTkFrame(win, fg_color="#111111", corner_radius=0)
        explain_frame.pack(fill="x", padx=0, pady=0)

        explain_cols = ctk.CTkFrame(explain_frame, fg_color="transparent")
        explain_cols.pack(fill="x", padx=14, pady=10)
        explain_cols.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")

        def _explain_card(parent, col, title, color, body):
            card = ctk.CTkFrame(
                parent,
                fg_color="#1a1a1a",
                corner_radius=6,
                border_width=1,
                border_color="#2a2a2a"
            )
            card.grid(row=0, column=col, padx=6, sticky="nsew")

            ctk.CTkLabel(
                card,
                text=title,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=color,
                anchor="w"
            ).pack(anchor="w", padx=10, pady=(8, 2))

            ctk.CTkLabel(
                card,
                text=body,
                font=(res.FONT_LABEL[0], 10),
                text_color="#777777",
                wraplength=270,
                justify="left",
                anchor="w"
            ).pack(anchor="w", padx=10, pady=(0, 10))

        _explain_card(
            explain_cols, 0,
            "Plot 1 — Geometric Spreading  GR(R)",
            "#5ab4ff",
            (
                "Shows how seismic wave amplitude decays with distance due to "
                "geometric spreading alone — the physical spreading of energy over "
                "a growing wavefront. Modeled as a piecewise power law:\n"
                "  GR(R) = (R/R₁)^s₁   for R ≤ R₂\n"
                "  GR(R) = GR(R₂) × (R/R₂)^s₂   for R > R₂\n\n"
                "s₁ ≈ −1.0 represents body wave spreading; "
                "s₂ ≈ −0.5 the slower surface wave decay at larger distances. "
                "The transition distance R₂ marks where the dominant wave type changes.\n\n"
                "Source: Boore (2005) SMSIM, Figure 3."
            )
        )

        _explain_card(
            explain_cols, 1,
            "Plot 2 — Combined Attenuation  GR(R) × Q",
            "#ff6666",
            (
                "Shows the total amplitude decay combining geometric spreading "
                "with anelastic attenuation (energy absorbed by the crust). "
                "The full path term is:\n"
                "  A(R, f) = GR(R) × exp(−π f R / Q(f) β)\n\n"
                "where Q(f) = max(Qmin, Q₀ × f^η) is the quality factor — "
                "higher Q means less absorption. Two curves are shown:\n"
                "  Blue  → f = 1 Hz  (low frequency)\n"
                "  Red   → f = 10 Hz (high frequency)\n\n"
                "High-frequency waves always attenuate faster. "
                "ENA rock has high Q (>600), so waves travel farther than in California.\n\n"
                "Source: Boore (2005) SMSIM, Figure 4."
            )
        )

        _explain_card(
            explain_cols, 2,
            "Plot 3 — Path Duration  D(R)",
            "#88dd88",
            (
                "Shows how the duration of strong shaking grows with distance. "
                "This is the path contribution to total ground motion duration — "
                "separate from the source duration (which depends on magnitude).\n\n"
                "Modeled as a piecewise linear function: each segment has a "
                "growth coefficient d (seconds per km). "
                "d=0.0 means no growth; d=0.16 means 0.16 s added per km.\n\n"
                "AB06 uses 4 segments: "
                "0→10 km (d=0.0), 10→70 km (d=0.16), 70→130 km (d=0.03), >130 km (d=0.04).\n\n"
                "Source: Atkinson & Boore (2006), Table 1."
            )
        )

        # --- MATPLOTLIB FIGURE ---
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
        fig.patch.set_facecolor("#0d0d0d")

        def style_ax(ax, title, xlabel, ylabel):
            ax.set_facecolor("#111111")
            ax.set_title(title, color="#aaaaaa", fontsize=10, pad=8)
            ax.set_xlabel(xlabel, color="#777777", fontsize=9)
            ax.set_ylabel(ylabel, color="#777777", fontsize=9)
            ax.tick_params(colors="#666666", labelsize=8)
            for spine in ax.spines.values():
                spine.set_edgecolor("#333333")
            ax.grid(True, color="#222222", linewidth=0.5, linestyle="--")

        # Plot 1 — Geometric Spreading (N segments)
        ax1 = axes[0]
        ax1.loglog(R, GR, color="#5ab4ff", linewidth=2, label="GR(R)")
        seg_colors = ["#ffaa44", "#88dd88", "#ff6699", "#aaaaff"]
        for seg_i, (r_cut, slope) in enumerate(gs_segs):
            ax1.axvline(
                r_cut, color=seg_colors[seg_i % len(seg_colors)],
                linewidth=1, linestyle="--",
                label=f"R{seg_i+1}={r_cut:.0f} km (s={slope:.1f})"
            )
        ax1.legend(fontsize=8, facecolor="#1a1a1a",
                   edgecolor="#333333", labelcolor="white")
        style_ax(ax1, "Geometric Spreading GR(R)",
                 "Distance (km)", "GR (dimensionless)")

        # Plot 2 — Combined attenuation GR × Q
        ax2 = axes[1]
        ax2.loglog(R, C1,  color="#5ab4ff", linewidth=2,
                   label=f"f=1 Hz  [Q={Q_f(1.0):.0f}]")
        ax2.loglog(R, C10, color="#ff6666", linewidth=2,
                   label=f"f=10 Hz [Q={Q_f(10.0):.0f}]")
        ax2.legend(fontsize=8, facecolor="#1a1a1a",
                   edgecolor="#333333", labelcolor="white")
        style_ax(ax2, "Combined Attenuation  GR(R) × exp(−πfR/Qβ)",
                 "Distance (km)", "Amplitude (relative)")

        # Plot 3 — Path Duration (linear x-axis, N segments)
        ax3 = axes[2]
        ax3.plot(R, D, color="#88dd88", linewidth=2)
        dr_colors = ["#ffaa44", "#88dd88", "#ff6699", "#aaaaff"]
        for seg_i, (r_cut, d_coeff) in enumerate(dr_segs):
            ax3.axvline(
                r_cut, color=dr_colors[seg_i % len(dr_colors)],
                linewidth=1, linestyle="--",
                label=f"R{seg_i+1}={r_cut:.0f} km (d={d_coeff:.3f})"
            )
        ax3.legend(fontsize=8, facecolor="#1a1a1a",
                   edgecolor="#333333", labelcolor="white")
        style_ax(ax3, "Path Duration  D(R)",
                 "Distance (km)", "Duration (s)")

        fig.tight_layout(pad=2.0)

        # Embed in popup
        canvas_frame = ctk.CTkFrame(win, fg_color="#0d0d0d")
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=(6, 0))

        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = ctk.CTkFrame(win, fg_color="#111111", corner_radius=0)
        toolbar_frame.pack(fill="x")
        NavigationToolbar2Tk(canvas, toolbar_frame)

        # Bottom note
        ctk.CTkLabel(
            win,
            text=(
                "All plots are computed live from the current Advanced Path Parameter values. "
                "Change a value in the panel and click Preview again to update."
            ),
            font=(res.FONT_LABEL[0], 9),
            text_color="#444444",
            wraplength=960,
            justify="center"
        ).pack(pady=(4, 10))

    def _on_islipweight_change(self, choice):
        """Shows or hides the slip file picker directly below the dropdown."""
        if choice == "From file (0)":
            self._slip_file_wrapper.pack(fill="x", padx=12, pady=(2, 2))
            self.slip_file_row.pack(fill="x")
        else:
            self.slip_file_row.pack_forget()
            self._slip_file_wrapper.pack_forget()

    def _open_genslip_panel(self):
        """
        Validates that all fault geometry fields are filled and at least
        one station exists, then opens GenslipPanel to run the selected
        rupture generator (self._islipweight_method — GP, IRIKURA1, or
        SONG) and auto-generate the islipweight file.
        """
        from ui.ExSIM.GenslipPanel import GenslipPanel

        # --- Validate fault geometry fields ---
        required_keys = [
            "MAGNITUDE", "FAULT_LENGTH", "FAULT_WIDTH", "DEPTH_TO_TOP",
            "STRIKE", "DIP", "RAKE", "HYPO_ALONG_STK", "HYPO_DOWN_DIP",
            "LON_TOP_CENTER", "LAT_TOP_CENTER"
        ]
        missing = []
        params  = {}
        for key in required_keys:
            if key not in self.src_inputs:
                missing.append(key)
                continue
            val = self.src_inputs[key].get().strip()
            if not val:
                missing.append(key)
            else:
                params[key] = val

        if missing:
            self.help_label.configure(
                text=f"Cannot generate islipweight — missing fields: "
                     f"{', '.join(missing)}",
                text_color=res.COLOR_ERROR
            )
            return

        # --- Validate at least one station ---
        stations = list(self.manual_station_list)
        module_stations = self.station_module.get_stations() \
            if hasattr(self, "station_module") else []
        all_stations = stations + [
            s for s in module_stations if s not in stations
        ]

        if not all_stations:
            self.help_label.configure(
                text="Cannot generate islipweight — add at least one station first.",
                text_color=res.COLOR_ERROR
            )
            return

        # --- Validate experimenter / exp name ---
        experimenter = self.ent_experimenter.get().strip()
        exp_name     = self.ent_exp_name.get().strip()
        if not experimenter or not exp_name:
            self.help_label.configure(
                text="Cannot generate islipweight — set Experimenter and "
                     "Experiment Name first.",
                text_color=res.COLOR_ERROR
            )
            return

        # --- Read DL/DW and SEED ---
        dl   = self.adv_exsim_inputs["DL"].get().strip()   \
               if "DL" in self.adv_exsim_inputs else "0.1"
        dw   = self.adv_exsim_inputs["DW"].get().strip()   \
               if "DW" in self.adv_exsim_inputs else "0.1"
        seed = self.ent_seed.get().strip() or "1234567"

        # --- Callback: auto-fill ExSIM fields when done ---
        def on_done(slip_path, dl_out, dw_out):
            self.islipweight_var.set("From file (0)")
            self._on_islipweight_change("From file (0)")
            self.ent_slip_file.delete(0, "end")
            self.ent_slip_file.insert(0, slip_path)
            if "DL" in self.adv_exsim_inputs:
                self.adv_exsim_inputs["DL"].delete(0, "end")
                self.adv_exsim_inputs["DL"].insert(0, str(dl_out))
            if "DW" in self.adv_exsim_inputs:
                self.adv_exsim_inputs["DW"].delete(0, "end")
                self.adv_exsim_inputs["DW"].insert(0, str(dw_out))
            self.help_label.configure(
                text=f"islipweight file generated and loaded: "
                     f"{slip_path.rsplit('/', 1)[-1]}",
                text_color=res.COLOR_SUCCESS
            )

        # --- Open the panel ---
        GenslipPanel(
            master       = self.winfo_toplevel(),
            params       = params,
            stations     = all_stations,
            experimenter = experimenter,
            exp_name     = exp_name,
            dlen         = dl,
            dwid         = dw,
            seed         = seed,
            method       = self._islipweight_method,
            on_done      = on_done
        )

    def _browse_slip_file(self):
        """Opens a file dialog to select the slip weights text file."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Slip Weights File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.ent_slip_file.delete(0, "end")
            self.ent_slip_file.insert(0, path)

    def _extract_from_srf(self):
        """
        Opens a WSL file browser dialog so the user can navigate and pick
        an .srf file. Extracts slip weights, normalizes, writes output,
        and auto-fills the slip file path + DL/DW fields.
        """
        def on_srf_selected(srf_wsl_path):
            import tkinter.messagebox as mb
            import os

            ok, srf_content = WSLBridge.read_wsl_file(srf_wsl_path)
            if not ok or not srf_content:
                mb.showerror("SRF Read Error",
                             f"Could not read:\n{srf_wsl_path}",
                             parent=self.winfo_toplevel())
                return

            try:
                nstk, ndip, slip_values = self._parse_srf_slip(srf_content)
            except Exception as e:
                mb.showerror("SRF Parse Error", str(e),
                             parent=self.winfo_toplevel())
                return

            if not slip_values:
                mb.showerror("SRF Parse Error",
                             "No slip values found in SRF file.",
                             parent=self.winfo_toplevel())
                return

            max_slip = max(slip_values)
            if max_slip == 0:
                mb.showerror("SRF Error",
                             "All slip values are zero — cannot normalize.",
                             parent=self.winfo_toplevel())
                return

            normalized   = [v / max_slip for v in slip_values]
            srf_dir      = "/".join(srf_wsl_path.rsplit("/", 1)[:-1])
            srf_base     = os.path.splitext(srf_wsl_path.rsplit("/", 1)[-1])[0]
            out_path     = f"{srf_dir}/{srf_base}_slip_weights.txt"
            file_content = "".join(f"{v:.6f}\n" for v in normalized)

            ok_w, err = WSLBridge.write_wsl_file(out_path, file_content)
            if not ok_w:
                mb.showerror("Write Error", err,
                             parent=self.winfo_toplevel())
                return

            self.ent_slip_file.delete(0, "end")
            self.ent_slip_file.insert(0, out_path)

            try:
                fault_len = float(self.src_inputs["FAULT_LENGTH"].get())
                fault_wid = float(self.src_inputs["FAULT_WIDTH"].get())
                dl = round(fault_len / nstk, 4)
                dw = round(fault_wid / ndip, 4)
                if "DL" in self.adv_exsim_inputs:
                    self.adv_exsim_inputs["DL"].delete(0, "end")
                    self.adv_exsim_inputs["DL"].insert(0, str(dl))
                if "DW" in self.adv_exsim_inputs:
                    self.adv_exsim_inputs["DW"].delete(0, "end")
                    self.adv_exsim_inputs["DW"].insert(0, str(dw))
                dl_dw_msg = f"  DL={dl} km, DW={dw} km auto-filled."
            except (ValueError, KeyError):
                dl_dw_msg = "  (DL/DW not auto-filled — set fault dimensions first.)"

            self.help_label.configure(
                text=(
                    f"SRF extracted: {len(normalized)} subfaults "
                    f"({nstk}×{ndip}). "
                    f"Saved: {srf_base}_slip_weights.txt."
                    f"{dl_dw_msg}"
                ),
                text_color=res.COLOR_SUCCESS
            )

        home = WSLBridge.get_wsl_home()
        WSLFileBrowser(
            master     = self.winfo_toplevel(),
            start_path = f"{home}/bbp_data/outdata",
            extension  = ".srf",
            title      = "Select SRF File",
            on_select  = on_srf_selected
        )

    def _parse_srf_slip(self, srf_content):
        """
        Parses per-point slip values from an SRF POINTS block.

        Two SRF point layouts are supported, auto-detected from the
        token count of the first data line after POINTS — not assumed,
        both confirmed against real GUI-generated .srf files:

        - Legacy 2-line layout (Genslip / IrikuraGenSrf output, what
          this method originally supported): a 10-token header line,
          then a 7-token line whose index [1] is the real,
          spatially-varying slip value ("PEAK1"). Index [8] of the
          header line, which looks like it should be "slip1", is
          constant across every point in this writer's output and
          must not be used.
        - Standard 3-line layout (SongRMGSS output — matches the
          official SRF 2.0 point spec more closely than the legacy
          layout does): an 8-token geometry line (lon lat dep stk dip
          area tinit dt), a 7-token line (rake slip1 nt1 slip2 nt2
          slip3 nt3), then the slip-rate time series wrapped across as
          many lines as nt1 (+nt2+nt3) need — confirmed against a real
          Song .srf containing a point with nt1=11, which wraps 6+5
          across two lines. Here slip1 (second line, index 1) DOES
          vary meaningfully point to point (confirmed against the real
          file), so it's used directly — no rate-function math needed,
          just correctly skipping past the wrapped values so point
          boundaries stay aligned.
        """
        lines = srf_content.splitlines()
        nstk = ndip = None
        points_idx = None

        for i, raw in enumerate(lines):
            parts = raw.strip().split()
            if points_idx is None and len(parts) == 6:
                try:
                    nstk_try = int(parts[2])
                    ndip_try = int(parts[3])
                    if 1 <= nstk_try <= 1000 and 1 <= ndip_try <= 1000:
                        nstk, ndip = nstk_try, ndip_try
                except (ValueError, IndexError):
                    pass
            if raw.strip().startswith("POINTS"):
                points_idx = i
                break

        if nstk is None or ndip is None:
            raise ValueError(
                "Could not read PLANE header (nstk, ndip) from SRF file."
            )
        if points_idx is None:
            raise ValueError("Could not find POINTS marker in SRF file.")

        i = points_idx + 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            raise ValueError("No point data found after POINTS marker.")

        first_token_count = len(lines[i].strip().split())
        slip_values = []

        if first_token_count == 10:
            # Legacy 2-line layout (Genslip / IrikuraGenSrf)
            prev_was_A = False
            while i < len(lines):
                parts = lines[i].strip().split()
                if not parts:
                    i += 1
                    continue
                if len(parts) == 10:
                    prev_was_A = True
                elif len(parts) == 7 and prev_was_A:
                    slip_values.append(float(parts[1]))
                    prev_was_A = False
                else:
                    prev_was_A = False
                i += 1

        elif first_token_count == 8:
            # Standard 3-line layout (SongRMGSS)
            for _ in range(nstk * ndip):
                while i < len(lines) and not lines[i].strip():
                    i += 1
                i += 1  # geometry line (8 tokens) — not needed here

                while i < len(lines) and not lines[i].strip():
                    i += 1
                parts = lines[i].strip().split()
                if len(parts) != 7:
                    raise ValueError(
                        f"Expected a 7-token rake/slip/nt line at SRF "
                        f"line {i + 1}, got {len(parts)} tokens."
                    )
                slip1 = float(parts[1])
                nt1, nt2, nt3 = int(float(parts[2])), int(float(parts[4])), int(float(parts[6]))
                slip_values.append(slip1)
                i += 1

                for nt in (nt1, nt2, nt3):
                    remaining = nt
                    while remaining > 0:
                        while i < len(lines) and not lines[i].strip():
                            i += 1
                        remaining -= len(lines[i].strip().split())
                        i += 1
        else:
            raise ValueError(
                f"Unrecognized SRF point layout — first data line after "
                f"POINTS has {first_token_count} tokens (expected 8 or 10)."
            )

        if len(slip_values) != nstk * ndip:
            raise ValueError(
                f"Expected {nstk * ndip} slip values ({nstk}×{ndip}) "
                f"but found {len(slip_values)}."
            )

        return nstk, ndip, slip_values

    def _write_adv_exsim_to_par(self):
        """
        Writes the current Advanced Path Parameters into labasin_exsim.par
        before the simulation runs. Only called from generate_files() when
        the user has expanded and modified this section.

        Uses WSLBridge.read_wsl_file / write_wsl_file to edit the .par
        file in-place, replacing only the two target lines:
          - Q line:                  'Qmin  Q0  eta'
          - Beta/rho line:           'beta  rho'
          - Geometric spreading segs: '  R1  slope1' / '  R2  slope2'
        All other lines are preserved exactly.

        Returns (ok: bool, err: str).
        """
        try:
            qmin = float(self.adv_exsim_inputs["QMIN"].get())
            q0   = float(self.adv_exsim_inputs["Q0"].get())
            eta  = float(self.adv_exsim_inputs["ETA"].get())
            beta = float(self.adv_exsim_inputs["BETA"].get())
            rho  = float(self.adv_exsim_inputs["RHO"].get())
            gs_segs = self._get_gs_segments()
            dr_segs = self._get_dr_segments()
        except ValueError as e:
            return False, f"Invalid Advanced Path Parameter value: {e}"

        # islipweight: map dropdown string to integer
        slip_mode_str = self.islipweight_var.get()
        slip_mode_map = {"Uniform (-1)": -1, "From file (0)": 0, "Random (1)": 1}
        islipweight = slip_mode_map.get(slip_mode_str, 1)

        # Slip file path — used only when islipweight=0
        slip_file_path = self.ent_slip_file.get().strip() if islipweight == 0 else "none"

        home     = WSLBridge.get_wsl_home()
        par_path = f"{home}/bbp_gf/LABasin500/uwo/labasin_exsim.par"
        ok, content = WSLBridge.read_wsl_file(par_path)
        if not ok or not content:
            return False, f"Could not read labasin_exsim.par: {par_path}"

        import re
        lines = content.splitlines()
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Q factor line: three numbers matching Qmin Q0 eta pattern
            # Identified by the comment line immediately before it.
            # Case-insensitive to match every other check in this
            # function — this one was the odd one out (previously
            # required an exact-case "Quality factor" match), which
            # meant it could silently never fire if the real file's
            # comment capitalization didn't match exactly, with zero
            # error raised either way.
            if re.match(r'^\s*\d+\.?\d*\s+\d+\.?\d*\s+\d*\.?\d+\s*$', stripped) \
                    and i > 0 and "quality factor" in lines[i-1].lower():
                new_lines.append(f"  {int(qmin)}  {q0}  {eta}")
                i += 1
                continue

            # Beta/rho line: two numbers, preceded by comment about beta/rho
            if re.match(r'^\s*\d+\.?\d*\s+\d+\.?\d*\s*$', stripped) \
                    and i > 0 and ("beta" in lines[i-1].lower() or "rho" in lines[i-1].lower()):
                new_lines.append(f"  {beta}  {rho}")
                i += 1
                continue

            # NOTE: DL/DW (subfault size) are NOT written to the .par file.
            # BBP's exsim.py wrapper reads DLEN/DWID from the .src file and
            # passes them to ExSIM directly — changing them in the .par breaks
            # BBP's internal filename expectations and causes FileNotFoundError.

            # NOTE: We deliberately do NOT touch the <CRUSTAL_AMP_FILE>
            # placeholder line. BBP's exsim.py substitutes all <...>
            # placeholders via template_replace() after our par write.
            # If we replace or remove the placeholder, BBP's sequential
            # scanner loses position and misreads NUM_STATIONS — causing
            # FileNotFoundError. Crustal amplification is handled by
            # overwriting the target amp file directly (see
            # _apply_crustal_amp_file() called from generate_files).

            # Geometric spreading — nseg count line + N data lines.
            # The nseg count line is a single integer preceded by a comment
            # containing "r_ref" or "nseg". Replace the count and write all
            # N new segment lines, skipping the original data lines.
            if re.match(r'^\s*\d+\s*$', stripped) \
                    and i > 0 \
                    and ("r_ref" in lines[i-1].lower() or "nseg" in lines[i-1].lower()):
                original_nseg = int(stripped.strip())
                n_new = len(gs_segs)
                new_lines.append(f"      {n_new}")
                for gs_r, gs_s in gs_segs:
                    new_lines.append(f"      {gs_r} {gs_s}")
                i += 1 + original_nseg  # skip nseg count line + original data lines
                continue

            # Path duration — ndur count line + N data lines.
            # Identified by a comment containing "duration" on the preceding line.
            if re.match(r'^\s*\d+\s*$', stripped) \
                    and i > 0 \
                    and "duration" in lines[i-1].lower():
                original_ndur = int(stripped.strip())
                n_new_dr = len(dr_segs)
                new_lines.append(f"      {n_new_dr}")
                for dr_r, dr_d in dr_segs:
                    new_lines.append(f"      {dr_r}  {dr_d}")
                i += 1 + original_ndur
                continue

            # islipweight value line: single integer (-1, 0, or 1),
            # preceded by a comment containing "random weights"
            if re.match(r'^\s*-?[01]\s*$', stripped) \
                    and i > 0 and "random weights" in lines[i-1].lower():
                new_lines.append(f"   {islipweight}")
                i += 1
                continue

            # NOTE: We deliberately do NOT touch the <SLIP_WEIGHTS_FILE>
            # placeholder line. BBP's exsim.py substitutes this itself
            # via template_replace(). If we write "none" here we destroy
            # the placeholder and BBP's sequential scanner reads past
            # <NUM_STATIONS> looking for <SLIP_WEIGHTS_FILE>, leaving
            # <NUM_STATIONS> unsubstituted — causing exsim14 exit code 2.

            new_lines.append(line)
            i += 1

        new_content = "\n".join(new_lines) + "\n"
        ok_w, err = WSLBridge.write_wsl_file(par_path, new_content)
        if not ok_w:
            return False, f"Could not write labasin_exsim.par: {err}"

        return True, ""

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

        # islipweight=0 requires a slip file path
        if self.islipweight_var.get() == "From file (0)":
            slip_path = self.ent_slip_file.get().strip()
            if not slip_path:
                return False, "Slip Weighting is set to 'From file (0)' but no slip file path was provided."

        # HYPO_ALONG_STK must be strictly within fault length
        # (ExSIM crashes if hypocenter is at or beyond the fault edge)
        try:
            hypo_stk = float(self.src_inputs["HYPO_ALONG_STK"].get())
            fault_len = float(self.src_inputs["FAULT_LENGTH"].get())
            if hypo_stk >= fault_len:
                return False, (
                    f"Hypo. Along Strike ({hypo_stk} km) must be less than "
                    f"Fault Length ({fault_len} km). ExSIM requires the hypocenter "
                    f"to be strictly inside the fault plane."
                )
        except ValueError:
            pass

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
        # DLEN/DWID — read from the Subfault Grid UI fields.
        # BBP's exsim.py reads these from the .src file and passes them
        # to ExSIM directly. Do NOT write them to labasin_exsim.par.
        dl_val = self.adv_exsim_inputs.get("DL")
        dw_val = self.adv_exsim_inputs.get("DW")
        dlen = dl_val.get().strip() if dl_val else "0.1"
        dwid = dw_val.get().strip() if dw_val else "0.1"
        if not dlen:
            dlen = "0.1"
        if not dwid:
            dwid = "0.1"
        src_lines.append(f"DLEN = {dlen}\n")
        src_lines.append(f"DWID = {dwid}\n")
        src_lines.append(f"SEED = {self.ent_seed.get()}\n")
        src_lines.append("\n")
        src_lines.append("# --- SIMULATION METHOD (at time of run) ---\n")
        src_lines.append("# METHOD = EXSIM\n")

        # --- EXSIM PATH PARAMETERS SNAPSHOT ---
        # Saved as comments — BBP ignores # lines, ResultsPanel reads them back.
        src_lines.append("\n")
        src_lines.append("# --- EXSIM PATH PARAMETERS (at time of run) ---\n")

        if self.adv_exsim_expanded:
            try:
                snap_segs = self._get_gs_segments()
            except ValueError:
                snap_segs = list(self._gs_segments_default)
            src_lines.append("# EXSIM_PARAMS_SOURCE = USER\n")
            src_lines.append(f"# EXSIM_QMIN = {self.adv_exsim_inputs['QMIN'].get()}\n")
            src_lines.append(f"# EXSIM_Q0   = {self.adv_exsim_inputs['Q0'].get()}\n")
            src_lines.append(f"# EXSIM_ETA  = {self.adv_exsim_inputs['ETA'].get()}\n")
            src_lines.append(f"# EXSIM_BETA = {self.adv_exsim_inputs['BETA'].get()}\n")
            src_lines.append(f"# EXSIM_RHO  = {self.adv_exsim_inputs['RHO'].get()}\n")
            src_lines.append(f"# EXSIM_DL   = {self.adv_exsim_inputs['DL'].get()}\n")
            src_lines.append(f"# EXSIM_DW   = {self.adv_exsim_inputs['DW'].get()}\n")
            src_lines.append(f"# EXSIM_CRUSTAL_AMP = {self.crustal_amp_var.get()}\n")
        else:
            snap_segs = [(float(r), float(s)) for r, s in self._gs_segments_default]
            src_lines.append("# EXSIM_PARAMS_SOURCE = DEFAULT\n")
            src_lines.append(f"# EXSIM_QMIN = {self._adv_exsim_defaults['QMIN']}\n")
            src_lines.append(f"# EXSIM_Q0   = {self._adv_exsim_defaults['Q0']}\n")
            src_lines.append(f"# EXSIM_ETA  = {self._adv_exsim_defaults['ETA']}\n")
            src_lines.append(f"# EXSIM_BETA = {self._adv_exsim_defaults['BETA']}\n")
            src_lines.append(f"# EXSIM_RHO  = {self._adv_exsim_defaults['RHO']}\n")
            src_lines.append(f"# EXSIM_DL   = {self._adv_exsim_defaults['DL']}\n")
            src_lines.append(f"# EXSIM_DW   = {self._adv_exsim_defaults['DW']}\n")
            src_lines.append("# EXSIM_CRUSTAL_AMP = BBP Default (California)\n")

        # Save GS segments: EXSIM_GS_NSEG then one line per segment
        src_lines.append(f"# EXSIM_GS_NSEG = {len(snap_segs)}\n")
        for seg_i, (r_val, s_val) in enumerate(snap_segs):
            src_lines.append(f"# EXSIM_GS_SEG{seg_i+1} = {r_val} {s_val}\n")

        # Save D(R) segments: EXSIM_DR_NSEG then one line per segment
        try:
            dr_snap_segs = self._get_dr_segments() if self.adv_exsim_expanded \
                           else [(float(r), float(d)) for r, d in self._dr_segments_default]
        except ValueError:
            dr_snap_segs = [(float(r), float(d)) for r, d in self._dr_segments_default]
        src_lines.append(f"# EXSIM_DR_NSEG = {len(dr_snap_segs)}\n")
        for seg_i, (r_val, d_val) in enumerate(dr_snap_segs):
            src_lines.append(f"# EXSIM_DR_SEG{seg_i+1} = {r_val} {d_val}\n")

        # islipweight + slip file path
        slip_mode_snap = self.islipweight_var.get() if hasattr(self, "islipweight_var") else "Random (1)"
        islip_map = {"Uniform (-1)": "-1", "From file (0)": "0", "Random (1)": "1"}
        islip_num = islip_map.get(slip_mode_snap, "1")
        src_lines.append(f"# EXSIM_ISLIPWEIGHT = {islip_num}\n")
        if islip_num == "0" and hasattr(self, "ent_slip_file"):
            slip_path_snap = self.ent_slip_file.get().strip()
            if slip_path_snap:
                src_lines.append(f"# EXSIM_SLIP_FILE = {slip_path_snap}\n")

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

        # --- SLIP FILE COPY (islipweight=0 only) ---
        # When the user selects "From file (0)", their slip weights file
        # must be copied to ~/bbp_gf/LABasin500/uwo/slip_weights.txt
        # BEFORE the simulation runs. BBP's exsim.py substitutes
        # <SLIP_WEIGHTS_FILE> with os.path.basename(self.slip_weights)
        # which resolves to "slip_weights.txt" in that folder.
        # This copy is independent of whether Advanced Path Parameters
        # is expanded — it applies whenever islipweight=0 is selected.
        slip_mode_str = self.islipweight_var.get() if hasattr(self, "islipweight_var") else "Random (1)"
        if slip_mode_str == "From file (0)":
            user_slip_path = self.ent_slip_file.get().strip()
            if user_slip_path:
                home = WSLBridge.get_wsl_home()
                dest_path = f"{home}/bbp_gf/LABasin500/uwo/slip_weights.txt"
                ok_cp = WSLBridge.run_command(
                    f"cp '{user_slip_path}' '{dest_path}'"
                )
                if ok_cp.returncode != 0:
                    self.help_label.configure(
                        text=f"Could not copy slip file to BBP: {ok_cp.stderr.strip()}",
                        text_color=res.COLOR_ERROR
                    )
                    return

        # --- WRITE ADVANCED PATH PARAMETERS TO .par ---
        if self.adv_exsim_expanded:
            # Crustal amplification — write to the target amp file before par write
            ok_amp, err_amp = self._apply_crustal_amp_file()
            if not ok_amp:
                self.help_label.configure(
                    text=f"Crustal amplification error: {err_amp}",
                    text_color=res.COLOR_ERROR
                )
                return

        ok_par, err_par = self._write_adv_exsim_to_par()

        self.btn_run.configure(state="normal")

        # Previously, this SUCCESS message was written unconditionally
        # right after the par-write warning above — meaning even a
        # correctly-detected par-write failure was invisible, since
        # this line overwrote it on the same help_label widget one
        # statement later. Now: .src/.stl genuinely did save either
        # way, but if labasin_exsim.par could not be updated, the
        # warning stays visible instead of being silently replaced.
        if not ok_par:
            self.help_label.configure(
                text=(f"Files saved for experiment: {base}, BUT Advanced "
                      f"Path Parameters could NOT be written to "
                      f"labasin_exsim.par — {err_par}"),
                text_color="#ffaa44"
            )
        else:
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

    def load_from_src(self, params, stations):
        """
        Pre-fills all ExSIM panel fields from a parsed .src parameter dict
        and a station list [(lon, lat, name), ...].

        Restores: fault geometry, SEED, experimenter/exp name,
        Advanced Path Parameters (Q, beta, rho, G(R) segments, D(R) segments,
        islipweight) from the EXSIM_* snapshot stored in the .src comments.
        """
        import re as _re

        def _set(entry, val):
            if val is not None:
                entry.delete(0, "end")
                entry.insert(0, str(val))

        # --- Experimenter / EXP_NAME ---
        experimenter = params.get("EXPERIMENTER", "")
        exp_name_raw = params.get("_suggested_exp_name", "") or params.get("EXP_NAME", "")
        base = _re.sub(r'_\d+$', '', exp_name_raw) if exp_name_raw else exp_name_raw
        new_exp = f"{base}_1" if base else "resim_1"

        _set(self.ent_experimenter, experimenter)
        _set(self.ent_exp_name, new_exp)

        # --- Fault geometry ---
        exsim_keys = [
            "MAGNITUDE", "FAULT_LENGTH", "FAULT_WIDTH", "DEPTH_TO_TOP",
            "STRIKE", "DIP", "RAKE", "HYPO_DOWN_DIP", "HYPO_ALONG_STK",
            "LON_TOP_CENTER", "LAT_TOP_CENTER",
        ]
        for key in exsim_keys:
            if key in params and key in self.src_inputs:
                _set(self.src_inputs[key], params[key])

        # --- SEED ---
        if "SEED" in params:
            _set(self.ent_seed, params["SEED"])

        # --- Advanced Path Parameters from EXSIM_* snapshot ---
        adv_key_map = {
            "EXSIM_QMIN" : "QMIN",
            "EXSIM_Q0"   : "Q0",
            "EXSIM_ETA"  : "ETA",
            "EXSIM_BETA" : "BETA",
            "EXSIM_RHO"  : "RHO",
            "EXSIM_DL"   : "DL",
            "EXSIM_DW"   : "DW",
        }
        has_adv_snapshot = any(k in params for k in adv_key_map)

        if has_adv_snapshot:
            # Expand the Advanced Path Parameters section
            if not self.adv_exsim_expanded:
                self._toggle_adv_exsim()

            for snap_key, adv_key in adv_key_map.items():
                if snap_key in params and adv_key in self.adv_exsim_inputs:
                    _set(self.adv_exsim_inputs[adv_key], params[snap_key])

            # --- G(R) segments ---
            nseg_gs = int(params.get("EXSIM_GS_NSEG", "0") or "0")
            if nseg_gs > 0:
                # Clear existing segments
                for _, _, rf in self._gs_segment_rows:
                    rf.destroy()
                self._gs_segment_rows = []
                # Rebuild from snapshot
                for seg_i in range(1, nseg_gs + 1):
                    seg_str = params.get(f"EXSIM_GS_SEG{seg_i}", "")
                    parts = seg_str.split()
                    if len(parts) == 2:
                        self._gs_add_segment(parts[0], parts[1])

            # --- D(R) segments ---
            nseg_dr = int(params.get("EXSIM_DR_NSEG", "0") or "0")
            if nseg_dr > 0:
                for _, _, rf in self._dr_segment_rows:
                    rf.destroy()
                self._dr_segment_rows = []
                for seg_i in range(1, nseg_dr + 1):
                    seg_str = params.get(f"EXSIM_DR_SEG{seg_i}", "")
                    parts = seg_str.split()
                    if len(parts) == 2:
                        self._dr_add_segment(parts[0], parts[1])

            # --- islipweight ---
            islip_val = params.get("EXSIM_ISLIPWEIGHT", "")
            islip_reverse = {"-1": "Uniform (-1)", "0": "From file (0)", "1": "Random (1)"}
            if islip_val in islip_reverse:
                self.islipweight_var.set(islip_reverse[islip_val])
                self._on_islipweight_change(islip_reverse[islip_val])

            # --- Crustal amplification ---
            amp_snap = params.get("EXSIM_CRUSTAL_AMP", "")
            if amp_snap and hasattr(self, "crustal_amp_var"):
                self.crustal_amp_var.set(amp_snap)
                self._on_crustal_amp_change(amp_snap)

        # --- Stations ---
        self.manual_station_list.clear()
        for lon, lat, name in stations:
            self.manual_station_list.append((lon, lat, name))
        self._refresh_station_list()
        self.trigger_map_update()

        self.help_label.configure(
            text=f"Fields pre-filled from previous run. "
                 f"Experiment renamed to '{new_exp}'. "
                 "Review all values then click Generate Files.",
            text_color="#88dd88"
        )