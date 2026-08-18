# UCSBResults.py — ui/results/UCSBResults.py
# -------------------------------------------------------
# Builds all result tabs for UCSB runs.
# Instantiated by ResultsPanel when _sim_method == "UCSB".
# Receives a reference to the parent ResultsPanel so it
# can access all shared state and helper methods.
# -------------------------------------------------------

import os
import customtkinter as ctk

import core.Resources as res
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge

from ui.results.ResultsHelpers import (
    _section_label, _textbox, _image_tab, _parse_status_file
)


class UCSBResults:
    """
    Builds tab content for UCSB simulation results.
    Tabs: Simulation Info, Source & Stations, Station Map,
          Rupture Map, Slip Distribution, GoF Summary (validation only).
    Rupture generator is UCrmg, not Genslip — all rupture-related
    labels/text below say "UCrmg", unlike this file's GPResults.py
    origin. NOTE: the .srf slip-parsing layout has NOT been confirmed
    against a real UCSB .srf file (SRF format is confirmed to differ
    across methods — Song uses a different layout than Genslip/
    IrikuraGenSrf — so UCrmg's layout should not be assumed identical
    to either until checked against a real file).
    """

    def __init__(self, panel):
        """
        Args:
            panel: the parent ResultsPanel instance.
                   All shared state and helpers are accessed via panel.xxx
        """
        self.p = panel   # shorthand

    def build_all(self):
        """
        Called by ResultsPanel._load_all() — builds every tab.
        Unlike GPResults, does NOT call a rupture-map or slip-distribution
        builder: ResultsPanel.py's tab_names excludes both tabs entirely
        for UCSB (_has_rupture_output == False), the same way it does for
        ExSIM, since UCrmg's FFSP output has no BBP-standard .srf or
        rupture map PNG to show. Calling either builder here would crash
        trying to open a tab that was never created.
        """
        self._build_info_tab()
        self._build_src_tab()
        self._build_station_map()

        if self.p._is_validation:
            self.p._build_gof_tab()

        # Set active tab AFTER all content is built, for consistency
        # with the other method views (kept even though UCSB has no
        # Slip Distribution tab to cause the auto-focus issue this
        # guards against elsewhere).
        try:
            self.p.tabs.set("Simulation Info")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # SIMULATION INFO TAB
    # ------------------------------------------------------------------

    def _build_info_tab(self):
        p   = self.p
        tab    = p.tabs.tab("Simulation Info")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        status_path = f"{p._outdata}/software_status-{p._run_id}.txt"
        ok, raw_status = WSLBridge.read_wsl_file(status_path)
        meta           = _parse_status_file(raw_status if ok else "")

        velocity_model = p._get_velocity_model()
        modules_ran    = p._get_modules_ran()
        session_folder = AppConfig.current_session_folder or "N/A (opened from history)"

        _section_label(scroll, "Simulation Metadata")

        meta_frame = ctk.CTkFrame(
            scroll, fg_color="#222222",
            border_width=1, border_color="#444", corner_radius=6
        )
        meta_frame.pack(fill="x", pady=(0, 12))
        meta_frame.grid_columnconfigure(1, weight=1)

        seed_value = "N/A"
        ok_src, src_content = WSLBridge.read_wsl_file(p._src_file)
        if ok_src:
            for line in src_content.splitlines():
                line = line.strip()
                if line.upper().startswith("SEED") and "=" in line:
                    seed_value = line.split("=", 1)[-1].strip()
                    break

        rows = [
            ("Broadband Version",  "22.4.0"),
            ("Velocity Model",     velocity_model),
            ("Simulation ID",      p._run_id),
            ("Simulation Method",  "Crempien & Archuleta (2015) — UCSB"),
            ("Simulation Profile", AppConfig.get_profile_label()),
            ("Seed",               seed_value),
            ("Experiment Name",    p._base_name),
            ("Session Folder",     session_folder),
            ("Output Folder",      p._outdata),
        ]

        for i, (label, value) in enumerate(rows):
            ctk.CTkLabel(
                meta_frame, text=f"{label}:",
                font=(res.FONT_LABEL[0], 12, "bold"), text_color="gray"
            ).grid(row=i, column=0, padx=(15, 8), pady=5, sticky="w")

            if label == "Velocity Model":
                val_frame = ctk.CTkFrame(meta_frame, fg_color="transparent")
                val_frame.grid(row=i, column=1, padx=(0, 15), pady=5, sticky="w")
                ctk.CTkLabel(
                    val_frame, text=str(value),
                    font=("Courier", 11), text_color="white", anchor="w"
                ).pack(side="left")
                ctk.CTkButton(
                    val_frame,
                    text="View Model",
                    width=90, height=24,
                    fg_color="#1a3a2a", hover_color="#2a5a3a",
                    border_width=1, border_color="#11CAA0",
                    text_color="#11CAA0",
                    font=(res.FONT_LABEL[0], 10),
                    command=lambda m=str(value): p._open_velocity_model(m)
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
                        font=(res.FONT_LABEL[0], 11), text_color="#444444"
                    ).pack(side="left", padx=(0, 2))

        # Corner Frequency section (UCSB-specific — replaces the GP
        # Advanced Parameters snapshot, which doesn't apply here since
        # UCSB doesn't use GP's Jbsim/Hfsims codebase). Parses the
        # CORNER_FREQ_1/CORNER_FREQ_2 values and the provenance comment
        # UCSBPanel.generate_files() writes into the .src file.
        cf1 = cf2 = None
        cf_source = "Unknown"
        if ok_src:
            for line in src_content.splitlines():
                stripped = line.strip()
                if stripped.upper().startswith("CORNER_FREQ_1") and "=" in stripped:
                    cf1 = stripped.split("=", 1)[-1].strip()
                elif stripped.upper().startswith("CORNER_FREQ_2") and "=" in stripped:
                    cf2 = stripped.split("=", 1)[-1].strip()
                elif "CORNER_FREQ_1/2 = JA19_2S" in stripped:
                    cf_source = "JA19_2S (Ji & Archuleta, 2020) — auto-calculated from Magnitude"
                elif "CORNER_FREQ_1/2 = MANUAL_OVERRIDE" in stripped:
                    cf_source = "Manual override"

        if cf1 or cf2:
            _section_label(scroll, "Corner Frequency Source (JA19_2S)")
            cf_frame = ctk.CTkFrame(
                scroll, fg_color="#222222",
                border_width=1, border_color="#444", corner_radius=6
            )
            cf_frame.pack(fill="x", pady=(0, 12))
            cf_frame.grid_columnconfigure(1, weight=1)

            for i, (label, value) in enumerate([
                ("fc1 (CORNER_FREQ_1)", cf1 or "N/A"),
                ("fc2 (CORNER_FREQ_2)", cf2 or "N/A"),
                ("Source",              cf_source),
            ]):
                ctk.CTkLabel(
                    cf_frame, text=f"{label}:",
                    font=(res.FONT_LABEL[0], 12, "bold"), text_color="gray"
                ).grid(row=i, column=0, padx=(15, 8), pady=5, sticky="w")
                ctk.CTkLabel(
                    cf_frame, text=str(value),
                    font=("Courier", 11), text_color="white", anchor="w"
                ).grid(row=i, column=1, padx=(0, 15), pady=5, sticky="w")

        # Linked Files
        _section_label(scroll, "Linked Files")
        links_frame = ctk.CTkFrame(
            scroll, fg_color="#222222",
            border_width=1, border_color="#444", corner_radius=6
        )
        links_frame.pack(fill="x", pady=(0, 12))
        links_frame.grid_columnconfigure(1, weight=1)

        all_file_rows = [
            ("Sim Spec (XML)",      f"{p._outdata}/{p._run_id}.xml"),
            ("Station List (.stl)", p._stl_file),
            ("Source File (.src)",  p._src_file),
            ("Rupture File (.srf)", f"{p._outdata}/{p._base_name}.srf"),
            ("Station Map (PNG)",   f"{p._outdata}/station_map.png"),
            ("Rupture Map (PNG)",   f"{p._outdata}/{p._base_name}.png"),
            ("HTML Report",         f"{p._outdata}/index-{p._run_id}.html"),
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
        _textbox(scroll, raw_status if ok else "Status file not found.",
                 height=180, color="#aaaaaa")

    # ------------------------------------------------------------------
    # SOURCE & STATIONS TAB
    # ------------------------------------------------------------------

    def _build_src_tab(self):
        p      = self.p
        tab    = p.tabs.tab("Source & Stations")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ok_src, src_content = WSLBridge.read_wsl_file(p._src_file)

        _section_label(
            scroll,
            f"Fault Source Parameters — {os.path.basename(p._src_file)}"
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
                     f"  $BBP_DATA_DIR/indata/{p._run_id}/",
                font=(res.FONT_LABEL[0], 11),
                text_color="gray", justify="left"
            ).pack(anchor="w", padx=10, pady=8)

        ok_stl, stl_content = WSLBridge.read_wsl_file(p._stl_file)

        _section_label(
            scroll,
            f"Station List — {os.path.basename(p._stl_file)}"
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
                     f"  $BBP_DATA_DIR/indata/{p._run_id}/",
                font=(res.FONT_LABEL[0], 11),
                text_color="gray", justify="left"
            ).pack(anchor="w", padx=10, pady=8)

    # ------------------------------------------------------------------
    # MAP TABS
    # ------------------------------------------------------------------

    def _build_station_map(self):
        p = self.p
        station_map = f"{p._outdata}/station_map.png"
        if WSLBridge.wsl_path_exists(station_map):
            p._build_image_tab_content("Station Map", station_map)
        else:
            p._build_unavailable_tab(
                "Station Map",
                "Station map (Plot_Map) was not included in this simulation.\n"
                "Add Plot_Map to your pipeline to generate this output."
            )