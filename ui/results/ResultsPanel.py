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
import re

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
from ui.results.FaultPlane3DPanel     import FaultPlane3DPanel
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

        # Detect simulation method (GP vs EXSIM). Primary source is the
        # "# METHOD = ..." comment block appended to the .src file at
        # generate-files time (same mechanism as the Advanced GP
        # Parameters block) — this travels with the run permanently and
        # doesn't depend on index-<run_id>.html still existing or being
        # parseable. Falls back to the HTML 'Simulation Method' field
        # for older runs made before this marker existed (e.g. runs
        # made during earlier GUI versions), and finally to validation
        # events, which always use GP and never carry this comment.
        self._sim_method = self._detect_simulation_method()
        self._is_exsim   = (self._sim_method == "EXSIM")

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

    def _read_advanced_params_snapshot(self, src_content):
        """
        Parses the "# --- ADVANCED GP PARAMETERS (at time of run) ---"
        comment block out of .src file content, written by
        GravesAndPitarkaPanel.generate_files() at run time.

        Expected line format: "# KEY = value [TAG]" where TAG is
        either "ACTIVE" (custom override was enabled at run time) or
        "BBP_DEFAULT" (no override active, value shown is BBP's own
        hardcoded default).

        Returns a dict: { key: (value_str, tag) } for every parameter
        line found. Returns an empty dict if the block is absent (e.g.
        runs made before this snapshot feature existed) — the caller
        treats an empty dict as "section not shown" rather than an error.
        """
        snapshot = {}
        if not src_content:
            return snapshot

        for raw_line in src_content.splitlines():
            line = raw_line.strip()
            if not line.startswith("#") or "[" not in line or "]" not in line or "=" not in line:
                continue
            try:
                body = line.lstrip("#").strip()      # "KAPPA = 0.0400 [ACTIVE]"
                key_val, _, tag_part = body.partition("[")
                tag = tag_part.rstrip("]").strip()
                if tag not in ("ACTIVE", "BBP_DEFAULT"):
                    continue
                key, _, val = key_val.partition("=")
                key = key.strip()
                val = val.strip()
                if not key or not val:
                    continue
                snapshot[key] = (val, tag)
            except Exception:
                continue

        return snapshot

    def _read_exsim_params_snapshot(self, src_content):
        """
        Parses EXSIM path parameter comments from the .src file.
        Returns a dict with scalar keys and a special 'GS_SEGMENTS' key
        containing a list of (R_km, slope) tuples for N-segment display.
        """
        snap = {}
        if not src_content:
            return snap

        for raw_line in src_content.splitlines():
            line = raw_line.strip()
            if not line.startswith("#") or "=" not in line:
                continue
            body = line.lstrip("#").strip()
            if not body.startswith("EXSIM_"):
                continue
            key, _, val = body.partition("=")
            key = key.strip()
            val = val.strip()
            if key and val:
                snap[key] = val

        # Parse GS segments from EXSIM_GS_NSEG + EXSIM_GS_SEGn keys
        try:
            nseg = int(snap.get("EXSIM_GS_NSEG", "0"))
            segs = []
            for seg_i in range(1, nseg + 1):
                seg_str = snap.get(f"EXSIM_GS_SEG{seg_i}", "")
                parts = seg_str.split()
                if len(parts) == 2:
                    segs.append((parts[0], parts[1]))
            if segs:
                snap["GS_SEGMENTS"] = segs
        except (ValueError, KeyError):
            pass

        # Parse D(R) segments from EXSIM_DR_NSEG + EXSIM_DR_SEGn keys
        try:
            ndur = int(snap.get("EXSIM_DR_NSEG", "0"))
            dr_segs = []
            for seg_i in range(1, ndur + 1):
                seg_str = snap.get(f"EXSIM_DR_SEG{seg_i}", "")
                parts = seg_str.split()
                if len(parts) == 2:
                    dr_segs.append((parts[0], parts[1]))
            if dr_segs:
                snap["DR_SEGMENTS"] = dr_segs
        except (ValueError, KeyError):
            pass

        return snap

    def _detect_simulation_method(self):
        """
        Returns "GP", "EXSIM", or "UNKNOWN".

        Primary source: the "# METHOD = ..." comment appended to the
        .src file at generate-files time (same mechanism as the
        Advanced GP Parameters block — a BBP-ignored comment that
        travels with the run permanently via indata/<run_id>/).

        Fallback: the 'Simulation Method' field in index-<run_id>.html,
        used for runs made before this .src marker existed.

        Note: validation runs no longer automatically return "GP" —
        ExSIM validation runs are now possible and must be detected
        correctly so the right tabs and content are shown.
        """
        if self._src_file:
            ok, src_content = WSLBridge.read_wsl_file(self._src_file)
            if ok and src_content:
                m = re.search(r'#\s*METHOD\s*=\s*(\w+)', src_content, re.IGNORECASE)
                if m:
                    method = m.group(1).strip().upper()
                    if method in ("GP", "EXSIM"):
                        return method

        # Fallback: read from BBP's HTML report
        detected = WSLBridge.detect_simulation_method(self._run_id, self._outdata)
        if detected in ("GP", "EXSIM"):
            return detected

        # Final fallback: if this is a validation run and method is still
        # unknown, default to GP (BBP's built-in validation events use GP)
        if self._detect_validation():
            return "GP"

        return "UNKNOWN"

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

        # Method badge — shown for every run (GP or EXSIM)
        if self._sim_method in ("GP", "EXSIM"):
            method_colors = {
                "GP"   : ("#0a2a3a", "#3b8ed0"),
                "EXSIM": ("#3a1a00", "#ffaa44"),
            }
            bg_color, fg_color = method_colors[self._sim_method]
            ctk.CTkLabel(
                bar,
                text=self._sim_method,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=fg_color,
                fg_color=bg_color,
                corner_radius=4,
                padx=8, pady=3
            ).pack(side="left", padx=(8, 0), pady=12)

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

        if self._is_exsim:
            # ExSIM has no kinematic rupture model — no .srf file exists,
            # so Rupture Map and Slip Distribution are not applicable.
            # Source & Stations IS included — ExSIM generates a .src and
            # .stl file just like GP, so the fault parameters and station
            # list are always available to review.
            tab_names = ["Simulation Info", "Source & Stations", "Station Map"]
        else:
            tab_names = ["Simulation Info", "Source & Stations", "Station Map", "Rupture Map", "Slip Distribution"]

        if self._is_validation:
            tab_names.append("GoF Summary")

        for name in tab_names:
            self.tabs.add(name)

        # Set Simulation Info as default — CTkTabview otherwise
        # defaults to the last tab added (Slip Distribution for GP)
        self.tabs.set("Simulation Info")

        self._profile = AppConfig.simulation_profile

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def _load_all(self):
        """
        Delegates tab building to the appropriate method-specific view class.
        """
        try:
            from ui.results.GPResults    import GPResults
            from ui.results.ExSimResults import ExSimResults

            if self._is_exsim:
                view = ExSimResults(self)
            else:
                view = GPResults(self)

            view.build_all()

        except Exception as e:
            import traceback
            print(f"[ResultsPanel] Error in _load_all: {e}")
            traceback.print_exc()
            # Show error in Simulation Info tab so user sees it
            try:
                tab = self.tabs.tab("Simulation Info")
                ctk.CTkLabel(
                    tab,
                    text=f"Error loading results:\n{e}",
                    font=(res.FONT_LABEL[0], 12),
                    text_color=res.COLOR_ERROR,
                    wraplength=600, justify="left"
                ).pack(padx=20, pady=20, anchor="w")
            except Exception:
                pass

        # Station List — shared regardless of method
        check = WSLBridge.run_command(
            f"ls '{self._outdata}' 2>/dev/null | grep -c '.vel.bbp' || echo 0"
        )
        has_stations = check.stdout.strip() not in ("", "0")
        if has_stations:
            self._load_stations()
        else:
            self.lbl_count.configure(text="No station output files found")
            self._render_table([])

        # Always set Simulation Info as the active tab
        # Use after() to ensure CTkTabview has finished rendering
        # before we switch — otherwise the last-added tab wins visually.
        self.after(50, lambda: self._safe_set_tab("Simulation Info"))

    def _safe_set_tab(self, tab_name):
        """Sets the active tab safely after rendering is complete."""
        try:
            self.tabs.set(tab_name)
        except Exception:
            pass

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
            val_event_short  = self._val_event_short,
            is_exsim         = self._is_exsim
        )