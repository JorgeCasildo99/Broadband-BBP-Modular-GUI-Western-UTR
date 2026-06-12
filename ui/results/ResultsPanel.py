# ResultsPanel.py — ui/Results/ResultsPanel.py
# -------------------------------------------------------
# Main BBP Results Viewer window.
# Shows station list, Simulation Info, Source & Stations,
# Station Map and Rupture Map tabs.
# Station clicks open StationDetailPanel.
# Image clicks open ImageFullscreenPanel.
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge

from ui.results.ResultsHelpers import (
    _section_label, _textbox, _image_tab, _parse_status_file
)
from ui.results.ImageFullscreenPanel  import ImageFullscreenPanel
from ui.results.StationDetailPanel    import StationDetailPanel
from ui.results.ComparisonPanel       import ComparisonPanel
from ui.results.SlipDistributionPanel import SlipDistributionPanel
from ui.VelocityModelPanel            import VelocityModelPanel


class ResultsPanel(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.title("BBP Results Viewer")
        self.geometry("1400x860")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._run_id      = AppConfig.current_run_id
        self._base_name   = AppConfig.current_base_name
        self._outdata     = AppConfig.out_path
        self._param_files = f"{self._outdata}/param_files"
        self._fas_folder  = f"{self._outdata}/FAS"
        self._stations    = []

        self._src_file        = self._find_param_file(".src")
        self._stl_file        = self._find_param_file(".stl")
        self._bbp_xml_content = self._read_bbp_xml()

        # Detect if this is a validation run by looking for GoF files
        self._is_validation   = self._detect_validation()
        self._val_event_name  = self._detect_val_event_name()
        self._val_event_short = self._detect_val_event_short()

        self._build_ui()
        self.after(200, self._on_ready)
        self.after(400, self._load_all)

    # ------------------------------------------------------------------
    # FILE FINDING HELPERS
    # ------------------------------------------------------------------

    def _find_param_file(self, ext):
        """
        Searches 4 locations in order for a file with the given extension:
        1. $BBP_DATA_DIR/indata/<run_id>/
        2. param_files/ inside outdata
        3. Root of outdata
        4. Anywhere inside outdata recursively
        """
        bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"

        for search_dir in [
            f"{bbp_data}/indata/{self._run_id}",
            self._param_files,
        ]:
            result = WSLBridge.run_command(
                f"find '{search_dir}' -name '*{ext}' 2>/dev/null | head -1"
            )
            found = result.stdout.strip()
            if found:
                return found

        result = WSLBridge.run_command(
            f"find '{self._outdata}' -maxdepth 1 -name '*{ext}' 2>/dev/null | head -1"
        )
        found = result.stdout.strip()
        if found:
            return found

        result = WSLBridge.run_command(
            f"find '{self._outdata}' -name '*{ext}' 2>/dev/null | head -1"
        )
        found = result.stdout.strip()
        if found:
            return found

        return f"{self._param_files}/{self._base_name}{ext}"

    def _read_bbp_xml(self):
        """Reads the BBP simulation XML from outdata folder."""
        xml_path = f"{self._outdata}/{self._run_id}.xml"
        ok, content = WSLBridge.read_wsl_file(xml_path)
        return content if ok else ""

    def _detect_validation(self):
        """
        Returns True if this run is a validation simulation.
        Detection: checks for GoF PNG files in outdata folder.
        GoF files only exist in validation runs.
        """
        result = WSLBridge.run_command(
            f"ls '{self._outdata}'/gof-*.png 2>/dev/null | head -1"
        )
        return bool(result.stdout.strip())

    def _detect_val_event_name(self):
        """
        Extracts validation event name from GoF filename.
        e.g. gof-map-CHINOH-79241-rotd50.png → Chino Hills
        """
        if not self._is_validation:
            return ""
        result = WSLBridge.run_command(
            f"ls '{self._outdata}'/gof-*.png 2>/dev/null | head -1"
        )
        fname = os.path.basename(result.stdout.strip())
        # Map short codes to full names
        name_map = {
            "CHINOH": "Chino Hills",
            "NR"    : "Northridge 1994",
            "WHITT" : "Whittier Narrows 1987",
            "GMPE"  : "GMPE Validation",
        }
        for code, name in name_map.items():
            if code in fname.upper():
                return name
        # Fallback: extract from filename
        parts = fname.split("-")
        return parts[1] if len(parts) > 1 else "Validation"

    def _detect_val_event_short(self):
        """Extracts the short event code from GoF filename for file pattern matching."""
        if not self._is_validation:
            return ""
        result = WSLBridge.run_command(
            f"ls '{self._outdata}'/gof-map-*.png 2>/dev/null | head -1"
        )
        fname = os.path.basename(result.stdout.strip())
        # gof-map-CHINOH-79241-rotd50.png → CHINOH
        parts = fname.split("-")
        return parts[2] if len(parts) > 2 else ""

    def _get_velocity_model(self):
        """Extracts velocity model name from BBP XML."""
        import re
        if self._bbp_xml_content:
            m = re.search(
                r'(?:velocity_model|vel_model|LABasin|CentralJapan|WesternUS)[^<\n]*',
                self._bbp_xml_content, re.IGNORECASE
            )
            if m:
                val = m.group(0).strip()
                if "LABasin" in val or "labasin" in val.lower():
                    return "LABasin500"
            m2 = re.search(r'([\w\-]+\.fk1d)', self._bbp_xml_content)
            if m2:
                return m2.group(1).replace(".fk1d", "")
        ok, src = WSLBridge.read_wsl_file(self._src_file)
        if ok and "LABasin" in src:
            return "LABasin500"
        return "LABasin500 (GP default)"

    def _open_velocity_model(self, model_name):
        """Opens the VelocityModelPanel popup for the given model."""
        # Clean up model name — strip any extra text
        name = model_name.strip().split()[0]
        if "LABasin" in name or "labasin" in name.lower():
            name = "LABasin500"
        VelocityModelPanel(self, model_name=name)

    def _get_modules_ran(self):
        """Extracts the list of modules that ran from the BBP XML."""
        import re
        if not self._bbp_xml_content:
            return []
        return re.findall(r'<name>([^<]+)</name>', self._bbp_xml_content)

    def _on_ready(self):
        try:
            self.lift()
            self.focus_force()
            self.state("zoomed")
        except Exception:
            pass

    def _go_to_dashboard(self):
        try:
            master = self.master
            if hasattr(master, "load_dashboard"):
                master.load_dashboard()
        except Exception:
            pass
        self.destroy()

    def _open_comparison(self):
        """Opens the seismogram comparison panel."""
        ComparisonPanel(self)

    # ------------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------------

    def _build_ui(self):

        # --- TITLE BAR ---
        bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=55)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkButton(
            bar,
            text="<- Back to Dashboard",
            width=160, height=32,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="white", hover_color="#2a2a2a",
            command=self._go_to_dashboard
        ).pack(side="left", padx=15, pady=11)

        ctk.CTkLabel(
            bar, text="BBP Results Viewer",
            font=(res.FONT_TITLE[0], 18, "bold"), text_color="white"
        ).pack(side="left", padx=10, pady=12)

        # Validation badge — only shown for validation runs
        self._val_badge = ctk.CTkLabel(
            bar,
            text=f"✓ VALIDATION — {self._val_event_name}" if self._is_validation else "",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffdd00",
            fg_color="#1a1500",
            corner_radius=4,
            padx=8, pady=3
        )
        if self._is_validation:
            self._val_badge.pack(side="left", padx=(0, 10), pady=12)

        session = os.path.basename(AppConfig.current_session_folder) \
            if AppConfig.current_session_folder else "N/A"
        ctk.CTkLabel(
            bar,
            text=f"Experiment: {self._base_name}   |   Run ID: {self._run_id}   |   Session: {session}",
            font=(res.FONT_LABEL[0], 11), text_color="gray"
        ).pack(side="right", padx=20)

        # Compare button — opens ComparisonPanel
        ctk.CTkButton(
            bar,
            text="⚡ Compare Seismograms",
            width=180, height=32,
            fg_color="#1a3a1a",
            border_width=1, border_color="#22c55e",
            text_color="#22c55e",
            hover_color="#2a4a2a",
            font=(res.FONT_LABEL[0], 11, "bold"),
            command=self._open_comparison
        ).pack(side="right", padx=(0, 8), pady=11)

        # --- MAIN SPLIT ---
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=3)
        split.grid_rowconfigure(0, weight=1)

        # --- LEFT — Station Table ---
        left = ctk.CTkFrame(
            split, fg_color="#1e1e1e",
            border_width=1, border_color="#333333", corner_radius=8
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        hdr = ctk.CTkFrame(left, fg_color="#111111", corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="Station List",
            font=(res.FONT_LABEL[0], 13, "bold"), text_color=res.COLOR_PRIMARY
        ).pack(side="left", padx=12, pady=10)

        self.lbl_count = ctk.CTkLabel(
            hdr, text="Loading...",
            font=(res.FONT_LABEL[0], 11), text_color="gray"
        )
        self.lbl_count.pack(side="right", padx=12)

        self.ent_search = ctk.CTkEntry(
            left, placeholder_text="Search station...", height=30
        )
        self.ent_search.pack(fill="x", padx=8, pady=6)
        self.ent_search.bind("<KeyRelease>", self._filter_stations)

        self.station_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.station_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        # --- RIGHT — Tabview ---
        right = ctk.CTkFrame(split, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.tabs = ctk.CTkTabview(
            right,
            fg_color="#1e1e1e",
            segmented_button_fg_color="#111111",
            segmented_button_selected_color=res.COLOR_PRIMARY,
            segmented_button_selected_hover_color="#004070",
            text_color="white"
        )
        self.tabs.pack(fill="both", expand=True)

        tab_names = ["Simulation Info", "Source & Stations", "Station Map", "Rupture Map", "Slip Distribution"]
        if self._is_validation:
            tab_names.append("GoF Summary")

        for name in tab_names:
            self.tabs.add(name)

        self._profile = AppConfig.simulation_profile

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def _load_all(self):
        """
        Loads all results by checking which files actually exist
        in $BBP_DATA_DIR/outdata/<run_id>/.
        Works for all profiles without assumptions.
        """
        self._build_info_tab()
        self._build_src_tab()

        # Station Map
        station_map = f"{self._outdata}/station_map.png"
        if WSLBridge.wsl_path_exists(station_map):
            self._build_image_tab_content("Station Map", station_map)
        else:
            self._build_unavailable_tab(
                "Station Map",
                "Station map (Plot_Map) was not included in this simulation.\n"
                "Add Plot_Map to your pipeline to generate this output."
            )

        # Rupture Map
        rupture_map    = f"{self._outdata}/{self._base_name}.png"
        rupture_map_fb = f"{self._outdata}/{self._run_id}.png"
        if WSLBridge.wsl_path_exists(rupture_map):
            self._build_image_tab_content("Rupture Map", rupture_map)
        elif WSLBridge.wsl_path_exists(rupture_map_fb):
            self._build_image_tab_content("Rupture Map", rupture_map_fb)
        else:
            self._build_unavailable_tab(
                "Rupture Map",
                "Rupture map (Genslip) was not found.\n"
                "This is generated automatically when Genslip runs."
            )

        # Station List
        check = WSLBridge.run_command(
            f"ls '{self._outdata}' 2>/dev/null | grep -c '.vel.bbp' || echo 0"
        )
        has_stations = check.stdout.strip() not in ("", "0")
        if has_stations:
            self._load_stations()
        else:
            self.lbl_count.configure(text="No station output files found")
            self._render_table([])

        # GoF Summary — validation only
        if self._is_validation:
            self._build_gof_tab()

        # Slip Distribution
        self._build_slip_tab()

    def _build_unavailable_tab(self, tab_name, message):
        tab   = self.tabs.tab(tab_name)
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="Not available for this profile",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(expand=True, pady=(0, 6))

        ctk.CTkLabel(
            frame, text=message,
            font=(res.FONT_LABEL[0], 12),
            text_color="gray",
            wraplength=500, justify="center"
        ).pack(expand=True)

    # ------------------------------------------------------------------
    # GoF SUMMARY TAB (validation only)
    # ------------------------------------------------------------------

    def _build_gof_tab(self):
        """
        Builds the GoF Summary tab for validation runs.
        Shows all 5 GoF plots: Map, Dist Linear, Dist Log, Vs30, FAS GoF.
        """
        tab    = self.tabs.tab("GoF Summary")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        hdr = ctk.CTkFrame(
            scroll, fg_color="#1a1500",
            corner_radius=6, border_width=1, border_color="#3a3000"
        )
        hdr.pack(fill="x", pady=(0, 12))

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            title_row,
            text=f"Goodness-of-Fit Summary — {self._val_event_name}",
            font=(res.FONT_LABEL[0], 15, "bold"),
            text_color="#ffdd00"
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=f"Run ID: {self._run_id}",
            font=(res.FONT_LABEL[0], 11),
            text_color="#888800"
        ).pack(side="right")

        ctk.CTkLabel(
            hdr,
            text=(
                "GoF plots compare synthetic seismograms against real recordings. "
                "Green = good fit, red = poor fit. "
                "These plots are only available for validation simulations."
            ),
            font=(res.FONT_LABEL[0], 11),
            text_color="#888855",
            wraplength=900, justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Find all GoF files dynamically
        gof_result = WSLBridge.run_command(
            f"ls '{self._outdata}'/gof-*.png 2>/dev/null"
        )
        gof_files = [
            f.strip() for f in gof_result.stdout.strip().splitlines()
            if f.strip()
        ]

        if not gof_files:
            ctk.CTkLabel(
                scroll,
                text="No GoF plots found in output folder.\n"
                     "GoF plots are generated by RotD50GoF and FASGoF modules.",
                font=(res.FONT_LABEL[0], 13),
                text_color="gray"
            ).pack(pady=40)
            return

        # GoF plot labels based on filename patterns
        def _gof_label(fname):
            base = os.path.basename(fname)
            if "gof-map"         in base: return "RotD50 Map GoF"
            if "dist-linear"     in base: return "RotD50 Distance Bias (Linear)"
            if "dist-log"        in base: return "RotD50 Distance Bias (Log)"
            if "vs30"            in base: return "RotD50 Vs30 GoF"
            if "-fas"            in base: return "FAS GoF"
            return os.path.basename(fname)

        def _gof_desc(fname):
            base = os.path.basename(fname)
            if "gof-map"     in base:
                return "Geographic map showing GoF score per station. Green = good, red = poor fit."
            if "dist-linear" in base:
                return "GoF score vs epicentral distance (linear scale). Reveals distance-dependent bias."
            if "dist-log"    in base:
                return "GoF score vs epicentral distance (log scale). Better resolution at close distances."
            if "vs30"        in base:
                return "GoF score vs Vs30 site condition. Reveals site amplification modeling quality."
            if "-fas"        in base:
                return "Fourier Amplitude Spectra GoF across all stations and frequency ranges."
            return ""

        # Preferred display order
        order = ["gof-map", "dist-linear", "dist-log", "vs30", "-fas"]
        def _sort_key(f):
            base = os.path.basename(f)
            for i, pat in enumerate(order):
                if pat in base:
                    return i
            return 99

        gof_files.sort(key=_sort_key)

        # Render each GoF plot
        for gof_path in gof_files:
            label = _gof_label(gof_path)
            desc  = _gof_desc(gof_path)

            # Section header
            sec_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            sec_frame.pack(fill="x", pady=(8, 2))
            ctk.CTkLabel(
                sec_frame, text=label,
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color=res.COLOR_PRIMARY
            ).pack(side="left")
            sep = ctk.CTkFrame(sec_frame, fg_color="#2a2a2a", height=1)
            sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)

            if desc:
                ctk.CTkLabel(
                    scroll, text=desc,
                    font=(res.FONT_LABEL[0], 10),
                    text_color="#555555",
                    justify="left"
                ).pack(anchor="w", pady=(0, 4))

            # Image
            img_frame = ctk.CTkFrame(
                scroll, fg_color="#0d0d0d",
                corner_radius=6, border_width=1, border_color="#222222"
            )
            img_frame.pack(fill="x", pady=(0, 12))

            _image_tab(img_frame, gof_path,
                       fallback_msg=f"{label} not found.",
                       master=self)

    # ------------------------------------------------------------------
    # SLIP DISTRIBUTION TAB
    # ------------------------------------------------------------------

    def _build_slip_tab(self):
        """
        Builds the Slip Distribution tab with a button to open
        the full interactive SlipDistributionPanel popup.
        """
        tab    = self.tabs.tab("Slip Distribution")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        srf_path = f"{self._outdata}/{self._base_name}.srf"
        srf_exists = WSLBridge.wsl_path_exists(srf_path)

        # Header
        hdr = ctk.CTkFrame(
            scroll, fg_color="#1a0d00",
            corner_radius=6, border_width=1, border_color="#3a2000"
        )
        hdr.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr,
            text="Kinematic Slip Distribution (Genslip .srf)",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#ffaa44"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            hdr,
            text=(
                "Visualizes how slip was distributed across the fault plane "
                "during the earthquake simulation.\n"
                "Generated by the Genslip module from the Standard Rupture Format (.srf) file.\n\n"
                "Available parameters:\n"
                "  •  Slip (cm) — total slip magnitude per subfault patch\n"
                "  •  Rake (°) — direction of slip motion\n"
                "  •  Rise Time (s) — duration of the slip pulse per patch\n"
                "  •  Rupture Time (s) — when the rupture wave reached each patch"
            ),
            font=(res.FONT_LABEL[0], 11),
            text_color="#aaaaaa",
            wraplength=860, justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            hdr,
            text=f"SRF file:  {srf_path}",
            font=("Courier", 10),
            text_color="#8a6a30"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        if not srf_exists:
            ctk.CTkLabel(
                scroll,
                text="⚠  SRF file not found",
                font=(res.FONT_LABEL[0], 14, "bold"),
                text_color="#888855"
            ).pack(pady=(20, 6))
            ctk.CTkLabel(
                scroll,
                text=(
                    "The .srf file is generated by Genslip.\n"
                    "Make sure Genslip was included in the simulation pipeline."
                ),
                font=(res.FONT_LABEL[0], 12),
                text_color="#555555",
                justify="center"
            ).pack()
            return

        # Open button
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Open Slip Distribution Viewer",
            width=280, height=48,
            fg_color="#3a2000",
            hover_color="#5a3200",
            border_width=1,
            border_color="#ffaa44",
            text_color="#ffaa44",
            font=(res.FONT_LABEL[0], 13, "bold"),
            command=lambda: SlipDistributionPanel(
                self, srf_path, self._run_id
            )
        ).pack()

        ctk.CTkLabel(
            btn_frame,
            text="Opens an interactive viewer with parameter toggle,\ncontour lines, and fullscreen export.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555",
            justify="center"
        ).pack(pady=(8, 0))

        # Preview thumbnail from BBP rupture map PNG
        rupture_png = f"{self._outdata}/{self._base_name}.png"
        if WSLBridge.wsl_path_exists(rupture_png):
            _section_label(scroll, "BBP Rupture Map (preview)")
            img_frame = ctk.CTkFrame(
                scroll, fg_color="#0d0d0d", corner_radius=6
            )
            img_frame.pack(fill="x", pady=(0, 10))
            _image_tab(img_frame, rupture_png,
                       "Rupture map not found.", master=self)

    def _build_info_tab(self):
        tab    = self.tabs.tab("Simulation Info")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        status_path = f"{self._outdata}/software_status-{self._run_id}.txt"
        ok, raw_status = WSLBridge.read_wsl_file(status_path)
        meta           = _parse_status_file(raw_status if ok else "")

        velocity_model = self._get_velocity_model()
        modules_ran    = self._get_modules_ran()
        session_folder = AppConfig.current_session_folder or "N/A (opened from history)"

        _section_label(scroll, "Simulation Metadata")

        meta_frame = ctk.CTkFrame(
            scroll, fg_color="#222222",
            border_width=1, border_color="#444", corner_radius=6
        )
        meta_frame.pack(fill="x", pady=(0, 12))
        meta_frame.grid_columnconfigure(1, weight=1)

        # Read SEED from .src file
        seed_value = "N/A"
        ok_src, src_content = WSLBridge.read_wsl_file(self._src_file)
        if ok_src:
            for line in src_content.splitlines():
                line = line.strip()
                if line.upper().startswith("SEED") and "=" in line:
                    seed_value = line.split("=", 1)[-1].strip()
                    break

        rows = [
            ("Broadband Version",  "22.4.0"),
            ("Velocity Model",     velocity_model),
            ("Simulation ID",      self._run_id),
            ("Simulation Method",  "GP — Graves & Pitarka"),
            ("Simulation Profile", AppConfig.get_profile_label()),
            ("Seed",               seed_value),
            ("Experiment Name",    self._base_name),
            ("Session Folder",     session_folder),
            ("Output Folder",      self._outdata),
        ]

        for i, (label, value) in enumerate(rows):
            ctk.CTkLabel(
                meta_frame, text=f"{label}:",
                font=(res.FONT_LABEL[0], 12, "bold"), text_color="gray"
            ).grid(row=i, column=0, padx=(15, 8), pady=5, sticky="w")

            if label == "Velocity Model":
                # Row with value + button to open visualization
                val_frame = ctk.CTkFrame(meta_frame, fg_color="transparent")
                val_frame.grid(row=i, column=1, padx=(0, 15), pady=5, sticky="w")
                ctk.CTkLabel(
                    val_frame, text=str(value),
                    font=("Courier", 11), text_color="white",
                    anchor="w"
                ).pack(side="left")
                ctk.CTkButton(
                    val_frame,
                    text="View Model",
                    width=90, height=24,
                    fg_color="#1a3a2a",
                    hover_color="#2a5a3a",
                    border_width=1,
                    border_color="#11CAA0",
                    text_color="#11CAA0",
                    font=(res.FONT_LABEL[0], 10),
                    command=lambda m=str(value): self._open_velocity_model(m)
                ).pack(side="left", padx=(12, 0))
            else:
                ctk.CTkLabel(
                    meta_frame, text=str(value),
                    font=("Courier", 11), text_color="white",
                    wraplength=700, justify="left", anchor="w"
                ).grid(row=i, column=1, padx=(0, 15), pady=5, sticky="w")

        if modules_ran:
            _section_label(scroll, "Modules Executed")
            mod_frame = ctk.CTkFrame(
                scroll, fg_color="#1a2a1a",
                border_width=1, border_color="#2a4a2a", corner_radius=6
            )
            mod_frame.pack(fill="x", pady=(0, 12))
            chip_row = ctk.CTkFrame(mod_frame, fg_color="transparent")
            chip_row.pack(fill="x", padx=12, pady=10, anchor="w")

            for i, mod in enumerate(modules_ran):
                ctk.CTkLabel(
                    chip_row, text=mod,
                    font=(res.FONT_LABEL[0], 11, "bold"),
                    text_color="#11CAA0", fg_color="#0a2a1a",
                    corner_radius=4, padx=8, pady=4
                ).pack(side="left", padx=(0, 2))
                if i < len(modules_ran) - 1:
                    ctk.CTkLabel(
                        chip_row, text="→",
                        font=(res.FONT_LABEL[0], 11),
                        text_color="#444444"
                    ).pack(side="left", padx=(0, 2))

        # ------------------------------------------------------------------
        # ADVANCED GP PARAMETERS SECTION
        # Values are read from the comment block appended to the .src file
        # at the time generate_files() was called — lines starting with
        # "# ADV_KEY = value  [TAG]"
        # Falls back to live velmodel config if no comment block found.
        # ------------------------------------------------------------------
        _section_label(scroll, "Advanced GP Parameters")

        adv_frame = ctk.CTkFrame(
            scroll, fg_color="#1a1a2a",
            border_width=1, border_color="#333355", corner_radius=6
        )
        adv_frame.pack(fill="x", pady=(0, 12))

        # --- Parse advanced params from .src file comment block ---
        adv_defs = [
            {"key": "KAPPA",         "label": "KAPPA (κ)",    "default": 0.04,  "unit": "s",       "desc": "Near-surface HF attenuation operator (hfsims)"},
            {"key": "QFEXP",         "label": "QFEXP",         "default": 0.6,   "unit": "—",       "desc": "Quality factor frequency exponent Q(f)=Q0×f^QFEXP (hfsims)"},
            {"key": "SDROP",         "label": "SDROP",         "default": 50,    "unit": "bars",    "desc": "Stress drop — HF energy at source (hfsims)"},
            {"key": "MEAN_RVFAC",    "label": "MEAN_RVFAC",    "default": 0.775, "unit": "× Vs",    "desc": "Mean rupture velocity fraction (genslip + hfsims)"},
            {"key": "RANGE_RVFAC",   "label": "RANGE_RVFAC",   "default": 0.1,   "unit": "× Vs",    "desc": "Rupture velocity randomization range (genslip + hfsims)"},
            {"key": "RISETIME_COEF", "label": "RISETIME_COEF", "default": 2.3,   "unit": "s/√km²",  "desc": "Rise time coefficient (genslip)"},
        ]

        snapshot        = {}
        snapshot_source = "current config (no .src block found)"

        # Try reading from .src comment block first
        ok_src, src_raw = WSLBridge.read_wsl_file(self._src_file)
        if ok_src and src_raw:
            found_any = False
            for line in src_raw.splitlines():
                line = line.strip()
                # Format: # ADV_KAPPA = 0.04  [BBP_DEFAULT]
                if not line.startswith("# ADV_"):
                    continue
                try:
                    # Strip leading "# ADV_"
                    body    = line[6:]                         # "KAPPA = 0.04  [BBP_DEFAULT]"
                    key_val = body.split("[")[0].strip()       # "KAPPA = 0.04"
                    tag     = body.split("[")[1].rstrip("]")   # "BBP_DEFAULT"
                    key, val_str = key_val.split("=", 1)
                    key     = key.strip()
                    val     = float(val_str.strip())
                    enabled = tag.strip() in ("CUSTOM", "ACTIVE")
                    is_cust = tag.strip() == "CUSTOM"
                    snapshot[key] = {
                        "value"    : val,
                        "enabled"  : enabled,
                        "is_custom": is_cust,
                        "tag"      : tag.strip(),
                    }
                    found_any = True
                except Exception:
                    continue

            if found_any:
                snapshot_source = ".src file (saved at run time)"

        # Fallback: read live velmodel config
        if not snapshot:
            snapshot_source = "current config (no .src block — old run)"
            home        = WSLBridge.get_wsl_home()
            cfg_path    = f"{home}/bbp_gf/LABasin500/labasin500_velmodel_config.txt"
            raw_params  = WSLBridge.read_advanced_params(cfg_path)
            bbp_defaults = {d["key"]: d["default"] for d in adv_defs}
            for key, default in bbp_defaults.items():
                info = raw_params.get(key)
                if info is None or not info["enabled"]:
                    snapshot[key] = {"value": default, "enabled": False,
                                     "is_custom": False, "tag": "BBP_DEFAULT"}
                else:
                    is_custom = abs(info["value"] - default) > 1e-9
                    snapshot[key] = {"value": info["value"], "enabled": True,
                                     "is_custom": is_custom,
                                     "tag": "CUSTOM" if is_custom else "ACTIVE"}

        # --- Column headers ---
        hdr_row = ctk.CTkFrame(adv_frame, fg_color="#111122", corner_radius=0)
        hdr_row.pack(fill="x")
        hdr_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        for col, txt in enumerate(["Parameter", "Value Used", "BBP Default", "Unit", "Notes"]):
            ctk.CTkLabel(
                hdr_row, text=txt,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=res.COLOR_PRIMARY
            ).grid(row=0, column=col, padx=12, pady=6, sticky="w")

        # --- Parameter rows ---
        for i, d in enumerate(adv_defs):
            key      = d["key"]
            info     = snapshot.get(key, {"value": d["default"], "enabled": False,
                                          "is_custom": False, "tag": "BBP_DEFAULT"})
            row_bg   = "#1e1e2e" if i % 2 == 0 else "#181828"

            row = ctk.CTkFrame(adv_frame, fg_color=row_bg, corner_radius=0)
            row.pack(fill="x")
            row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

            val       = info.get("value", d["default"])
            tag       = info.get("tag", "BBP_DEFAULT")
            enabled   = info.get("enabled", False)
            is_custom = info.get("is_custom", False)

            # Format value
            val_text = f"{val:.4f}" if isinstance(val, float) and (val % 1 != 0) else str(int(val) if val == int(val) else val)

            # Badge colours
            if not enabled:
                val_color  = "#aaaaaa"
                badge_fg   = "#2a2a2a"
                badge_tc   = "#666666"
            elif is_custom:
                val_color  = "#ffdd88"
                badge_fg   = "#2a1a00"
                badge_tc   = "#ffdd88"
            else:
                val_color  = res.COLOR_SUCCESS
                badge_fg   = "#0a1f0a"
                badge_tc   = res.COLOR_SUCCESS

            # Col 0 — name
            ctk.CTkLabel(
                row, text=d["label"],
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color="white", anchor="w"
            ).grid(row=0, column=0, padx=12, pady=6, sticky="w")

            # Col 1 — value + badge
            cell = ctk.CTkFrame(row, fg_color="transparent")
            cell.grid(row=0, column=1, padx=12, pady=6, sticky="w")
            ctk.CTkLabel(
                cell, text=val_text,
                font=("Courier", 12, "bold"),
                text_color=val_color
            ).pack(side="left")
            ctk.CTkLabel(
                cell, text=f"  {tag}",
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color=badge_tc, fg_color=badge_fg,
                corner_radius=3, padx=5, pady=1
            ).pack(side="left", padx=(6, 0))

            # Col 2 — default
            ctk.CTkLabel(
                row, text=str(d["default"]),
                font=("Courier", 11), text_color="#555555", anchor="w"
            ).grid(row=0, column=2, padx=12, pady=6, sticky="w")

            # Col 3 — unit
            ctk.CTkLabel(
                row, text=d["unit"],
                font=(res.FONT_LABEL[0], 10), text_color="#444466", anchor="w"
            ).grid(row=0, column=3, padx=12, pady=6, sticky="w")

            # Col 4 — description
            ctk.CTkLabel(
                row, text=d["desc"],
                font=(res.FONT_LABEL[0], 10), text_color="#555566",
                anchor="w", justify="left", wraplength=320
            ).grid(row=0, column=4, padx=12, pady=6, sticky="w")

        # Footer
        ctk.CTkLabel(
            adv_frame,
            text=(
                f"Source: {snapshot_source}  —  "
                "CUSTOM = user-modified  |  ACTIVE = BBP default explicitly set  |  "
                "BBP_DEFAULT = built-in fallback (commented or absent in config)"
            ),
            font=(res.FONT_LABEL[0], 9),
            text_color="#444455", justify="left", anchor="w"
        ).pack(anchor="w", padx=12, pady=(2, 8))

        # ------------------------------------------------------------------
        _section_label(scroll, "Linked Files")
        links_frame = ctk.CTkFrame(
            scroll, fg_color="#222222",
            border_width=1, border_color="#444", corner_radius=6
        )
        links_frame.pack(fill="x", pady=(0, 12))
        links_frame.grid_columnconfigure(1, weight=1)

        all_file_rows = [
            ("Sim Spec (XML)",      f"{self._outdata}/{self._run_id}.xml"),
            ("Station List (.stl)", self._stl_file),
            ("Source File (.src)",  self._src_file),
            ("Rupture File (.srf)", f"{self._outdata}/{self._base_name}.srf"),
            ("Station Map (PNG)",   f"{self._outdata}/station_map.png"),
            ("Rupture Map (PNG)",   f"{self._outdata}/{self._base_name}.png"),
            ("HTML Report",         f"{self._outdata}/index-{self._run_id}.html"),
        ]

        shown = 0
        for label, path in all_file_rows:
            if path and WSLBridge.wsl_path_exists(path):
                ctk.CTkLabel(
                    links_frame, text=f"{label}:",
                    font=(res.FONT_LABEL[0], 11, "bold"), text_color="gray"
                ).grid(row=shown, column=0, padx=(15, 8), pady=4, sticky="w")
                ctk.CTkLabel(
                    links_frame, text=path,
                    font=("Courier", 10), text_color=res.COLOR_SUCCESS,
                    wraplength=700, justify="left", anchor="w"
                ).grid(row=shown, column=1, padx=(0, 15), pady=4, sticky="w")
                shown += 1

        if shown == 0:
            ctk.CTkLabel(
                links_frame, text="No output files found.",
                font=(res.FONT_LABEL[0], 11), text_color="gray"
            ).grid(row=0, column=0, columnspan=2, padx=15, pady=10)

        _section_label(scroll, "Raw Software Status")
        _textbox(scroll, raw_status if ok else "Status file not found.", height=180, color="#aaaaaa")

    # ------------------------------------------------------------------
    # SOURCE & STATIONS TAB
    # ------------------------------------------------------------------

    def _build_src_tab(self):
        tab    = self.tabs.tab("Source & Stations")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ok_src, src_content = WSLBridge.read_wsl_file(self._src_file)

        _section_label(
            scroll,
            f"Fault Source Parameters — {os.path.basename(self._src_file)}"
        )

        if ok_src:
            param_frame = ctk.CTkFrame(
                scroll, fg_color="#222222",
                border_width=1, border_color="#444", corner_radius=6
            )
            param_frame.pack(fill="x", pady=(0, 12))
            param_frame.grid_columnconfigure(1, weight=1)

            row_idx = 0
            for line in src_content.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    ctk.CTkLabel(
                        param_frame, text=line,
                        font=("Courier", 11), text_color="#555555", anchor="w"
                    ).grid(row=row_idx, column=0, columnspan=2,
                           padx=15, pady=2, sticky="w")
                elif "=" in line:
                    parts = line.split("=", 1)
                    ctk.CTkLabel(
                        param_frame, text=parts[0].strip(),
                        font=(res.FONT_LABEL[0], 12, "bold"),
                        text_color=res.COLOR_PRIMARY, anchor="w"
                    ).grid(row=row_idx, column=0, padx=(15, 8), pady=5, sticky="w")
                    ctk.CTkLabel(
                        param_frame, text=parts[1].strip(),
                        font=("Courier", 12), text_color="white", anchor="w"
                    ).grid(row=row_idx, column=1, padx=(0, 15), pady=5, sticky="w")
                row_idx += 1
        else:
            ctk.CTkLabel(
                scroll,
                text=f"Source file not found.\nSearched in:\n"
                     f"  {AppConfig.out_path}/param_files/\n"
                     f"  $BBP_DATA_DIR/indata/{self._run_id}/",
                font=(res.FONT_LABEL[0], 11),
                text_color="gray", justify="left"
            ).pack(anchor="w", padx=10, pady=8)

        ok_stl, stl_content = WSLBridge.read_wsl_file(self._stl_file)

        _section_label(
            scroll,
            f"Station List — {os.path.basename(self._stl_file)}"
            if ok_stl else "Station List (.stl)"
        )

        if ok_stl:
            stations = []
            for line in stl_content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        lon  = float(parts[0])
                        lat  = float(parts[1])
                        name = parts[2]
                        stations.append((name, lon, lat))
                    except ValueError:
                        continue

            if stations:
                tbl = ctk.CTkFrame(
                    scroll, fg_color="#1a1a1a",
                    border_width=1, border_color="#333", corner_radius=6
                )
                tbl.pack(fill="x", pady=(0, 8))

                hdr = ctk.CTkFrame(tbl, fg_color="#111111", corner_radius=0)
                hdr.pack(fill="x")
                hdr.grid_columnconfigure((0, 1, 2, 3), weight=1)

                for col, txt in enumerate(["#", "Station ID", "Longitude (°)", "Latitude (°)"]):
                    ctk.CTkLabel(
                        hdr, text=txt,
                        font=(res.FONT_LABEL[0], 11, "bold"),
                        text_color=res.COLOR_PRIMARY
                    ).grid(row=0, column=col, padx=12, pady=6, sticky="w")

                for i, (name, lon, lat) in enumerate(stations):
                    row_bg = "#1e1e1e" if i % 2 == 0 else "#252525"
                    row_f  = ctk.CTkFrame(tbl, fg_color=row_bg, corner_radius=0)
                    row_f.pack(fill="x")
                    row_f.grid_columnconfigure((0, 1, 2, 3), weight=1)

                    for col, val in enumerate([
                        str(i + 1), name, f"{lon:.5f}", f"{lat:.5f}"
                    ]):
                        ctk.CTkLabel(
                            row_f, text=val,
                            font=("Courier", 11),
                            text_color="white" if col == 1 else "#aaaaaa",
                            anchor="w"
                        ).grid(row=0, column=col, padx=12, pady=4, sticky="w")

                ctk.CTkLabel(
                    scroll,
                    text=f"Total: {len(stations)} stations",
                    font=(res.FONT_LABEL[0], 10), text_color="#555555"
                ).pack(anchor="w", padx=10, pady=(0, 8))
            else:
                ctk.CTkLabel(
                    scroll, text="Station list file is empty or could not be parsed.",
                    font=(res.FONT_LABEL[0], 11), text_color="gray"
                ).pack(anchor="w", padx=10, pady=8)
        else:
            ctk.CTkLabel(
                scroll,
                text=f"Station list file not found.\nSearched in:\n"
                     f"  {AppConfig.out_path}/param_files/\n"
                     f"  $BBP_DATA_DIR/indata/{self._run_id}/",
                font=(res.FONT_LABEL[0], 11),
                text_color="gray", justify="left"
            ).pack(anchor="w", padx=10, pady=8)

    # ------------------------------------------------------------------
    # MAP TABS
    # ------------------------------------------------------------------

    def _build_image_tab_content(self, tab_name, path, fallback=None):
        tab   = self.tabs.tab(tab_name)
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        result = WSLBridge.run_command(f"base64 '{path}' 2>/dev/null")
        actual_path = path
        if (result.returncode != 0 or not result.stdout.strip()) and fallback:
            actual_path = fallback

        _image_tab(frame, actual_path, master=self)

    # ------------------------------------------------------------------
    # STATION TABLE
    # ------------------------------------------------------------------

    def _load_stations(self):
        ok, files, _ = WSLBridge.list_wsl_dir(self._outdata)
        if not ok:
            self.lbl_count.configure(text="Error reading folder")
            return

        ids = set()
        for f in files:
            fname = os.path.basename(f)
            if fname.endswith(".vel.bbp"):
                parts = fname.split(".")
                if len(parts) >= 2:
                    ids.add(parts[1])

        self._stations = sorted(list(ids))
        self.lbl_count.configure(text=f"{len(self._stations)} stations")
        self._render_table(self._stations)

    def _render_table(self, stations):
        for w in self.station_scroll.winfo_children():
            w.destroy()

        if not stations:
            ctk.CTkLabel(
                self.station_scroll,
                text="No stations found.",
                font=(res.FONT_LABEL[0], 12), text_color="gray"
            ).pack(pady=20)
            return

        hdr = ctk.CTkFrame(
            self.station_scroll, fg_color="#1a1a3a", corner_radius=4, height=28
        )
        hdr.pack(fill="x", pady=(0, 4))
        hdr.pack_propagate(False)
        hdr.grid_columnconfigure((0, 1), weight=1)

        for col, txt in enumerate(["#", "Station ID"]):
            ctk.CTkLabel(
                hdr, text=txt,
                font=(res.FONT_LABEL[0], 11, "bold"), text_color=res.COLOR_PRIMARY
            ).grid(row=0, column=col, padx=8, sticky="w")

        for i, sid in enumerate(stations):
            row = ctk.CTkFrame(
                self.station_scroll,
                fg_color="#252525" if i % 2 == 0 else "#1e1e1e",
                corner_radius=4, height=32
            )
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            row.grid_columnconfigure((0, 1), weight=1)

            ctk.CTkLabel(
                row, text=str(i + 1),
                font=(res.FONT_LABEL[0], 11), text_color="gray"
            ).grid(row=0, column=0, padx=8, sticky="w")

            ctk.CTkButton(
                row, text=sid,
                font=(res.FONT_LABEL[0], 11),
                fg_color="transparent", text_color=res.COLOR_SUCCESS,
                hover_color="#1a2a1a", anchor="w", height=28,
                command=lambda s=sid: self._open_station(s)
            ).grid(row=0, column=1, padx=4, sticky="ew")

    def _filter_stations(self, event=None):
        q = self.ent_search.get().strip().lower()
        self._render_table([s for s in self._stations if q in s.lower()])

    def _open_station(self, station_id):
        StationDetailPanel(
            self, station_id,
            self._outdata, self._fas_folder,
            self._run_id, self._profile,
            is_validation    = self._is_validation,
            val_event_short  = self._val_event_short
        )