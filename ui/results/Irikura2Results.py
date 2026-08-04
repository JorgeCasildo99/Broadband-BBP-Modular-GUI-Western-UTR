# Irikura2Results.py — ui/results/Irikura2Results.py
# Builds all result tabs for Irikura Recipe 2 runs.
# Identical to IrikuraResults (Method 1) except the "Simulation Method"
# label below — the rupture generator is the same (IrikuraGenSrf), only
# the HF module differs (IrikuraHF vs Hfsims), which doesn't appear in
# this file at all.

import os
import customtkinter as ctk

import core.Resources as res
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge

from ui.results.ResultsHelpers import (
    _section_label, _textbox, _image_tab, _parse_status_file
)
from ui.results.SlipDistributionPanel import SlipDistributionPanel
from ui.results.FaultPlane3DPanel     import FaultPlane3DPanel


class Irikura2Results:
    """
    Builds tab content for Irikura Recipe 2 simulation results.
    Identical to IrikuraResults (Method 1) — only the "Simulation
    Method" row in Simulation Info differs.
    """

    def __init__(self, panel):
        """
        Args:
            panel: the parent ResultsPanel instance.
                   All shared state and helpers are accessed via panel.xxx
        """
        self.p = panel   # shorthand

    def build_all(self):
        """Called by ResultsPanel._load_all() — builds every tab."""
        self._build_info_tab()
        self._build_src_tab()
        self._build_station_map()
        self._build_rupture_map()
        self._build_slip_tab()

        if self.p._is_validation:
            self.p._build_gof_tab()

        # Set active tab AFTER all content is built.
        # SlipDistributionPanel adds widgets to Slip Distribution last,
        # which causes CTkTabview to auto-focus that tab — this resets it.
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
            ("Simulation Method",  "Kamae et al. (1998) — Irikura Recipe 2"),
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

        # Advanced GP Parameters snapshot
        adv_snapshot = p._read_advanced_params_snapshot(src_content if ok_src else "")
        if adv_snapshot:
            _section_label(scroll, "Advanced GP Parameters")
            adv_frame = ctk.CTkFrame(
                scroll, fg_color="#222222",
                border_width=1, border_color="#444", corner_radius=6
            )
            adv_frame.pack(fill="x", pady=(0, 12))

            hdr_row = ctk.CTkFrame(adv_frame, fg_color="#111122", corner_radius=0)
            hdr_row.pack(fill="x")
            hdr_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="adv_col")
            for col, txt in enumerate(["Parameter", "Value Used", "Status"]):
                ctk.CTkLabel(
                    hdr_row, text=txt,
                    font=(res.FONT_LABEL[0], 11, "bold"),
                    text_color=res.COLOR_PRIMARY, anchor="w"
                ).grid(row=0, column=col, padx=12, pady=6, sticky="ew")

            status_colors = {"ACTIVE": "#ffaa55", "BBP_DEFAULT": "#888888"}
            param_order = ["KAPPA", "QFEXP", "SDROP",
                           "MEAN_RVFAC", "RANGE_RVFAC", "RISETIME_COEF"]

            for row_i, key in enumerate(param_order):
                if key not in adv_snapshot:
                    continue
                val, tag = adv_snapshot[key]
                row_bg = "#1a1a1a" if row_i % 2 == 0 else "#222222"
                row_frame = ctk.CTkFrame(adv_frame, fg_color=row_bg, corner_radius=0)
                row_frame.pack(fill="x")
                row_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="adv_col")
                ctk.CTkLabel(
                    row_frame, text=key,
                    font=("Courier", 11, "bold"), text_color="white", anchor="w"
                ).grid(row=0, column=0, padx=12, pady=5, sticky="ew")
                ctk.CTkLabel(
                    row_frame, text=val,
                    font=("Courier", 11), text_color="white", anchor="w"
                ).grid(row=0, column=1, padx=12, pady=5, sticky="ew")
                ctk.CTkLabel(
                    row_frame, text=tag,
                    font=(res.FONT_LABEL[0], 10, "bold"),
                    text_color=status_colors.get(tag, "white"), anchor="w"
                ).grid(row=0, column=2, padx=12, pady=5, sticky="ew")

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

    def _build_rupture_map(self):
        p = self.p
        rupture_map    = f"{p._outdata}/{p._base_name}.png"
        rupture_map_fb = f"{p._outdata}/{p._run_id}.png"
        if WSLBridge.wsl_path_exists(rupture_map):
            p._build_image_tab_content("Rupture Map", rupture_map)
        elif WSLBridge.wsl_path_exists(rupture_map_fb):
            p._build_image_tab_content("Rupture Map", rupture_map_fb)
        else:
            p._build_unavailable_tab(
                "Rupture Map",
                "Rupture map (IrikuraGenSrf) was not found.\n"
                "This is generated automatically when IrikuraGenSrf runs."
            )

    # ------------------------------------------------------------------
    # SLIP DISTRIBUTION TAB
    # ------------------------------------------------------------------

    def _build_slip_tab(self):
        """
        Builds the Slip Distribution tab with buttons to open the
        SlipDistributionPanel and FaultPlane3DPanel popups on click.
        Matches original behaviour — does NOT open any popup automatically.
        """
        p   = self.p
        tab = p.tabs.tab("Slip Distribution")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        srf_path   = f"{p._outdata}/{p._base_name}.srf"
        srf_exists = WSLBridge.wsl_path_exists(srf_path)

        # Header
        hdr = ctk.CTkFrame(
            scroll, fg_color="#1a0d00",
            corner_radius=6, border_width=1, border_color="#3a2000"
        )
        hdr.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr,
            text="Kinematic Slip Distribution (IrikuraGenSrf .srf)",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="#ffaa44"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            hdr,
            text=(
                "Visualizes how slip was distributed across the fault plane "
                "during the earthquake simulation.\n"
                "Generated by the IrikuraGenSrf module from the Standard Rupture Format (.srf) file.\n\n"
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
                    "The .srf file is generated by IrikuraGenSrf.\n"
                    "Make sure IrikuraGenSrf was included in the simulation pipeline."
                ),
                font=(res.FONT_LABEL[0], 12),
                text_color="#555555",
                justify="center"
            ).pack()
            return

        # Buttons — open popups on click, not automatically
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Open Slip Distribution Viewer",
            width=280, height=48,
            fg_color="#3a2000", hover_color="#5a3200",
            border_width=1, border_color="#ffaa44",
            text_color="#ffaa44",
            font=(res.FONT_LABEL[0], 13, "bold"),
            command=lambda: SlipDistributionPanel(p, srf_path, p._run_id)
        ).pack()

        ctk.CTkButton(
            btn_frame,
            text="Open 3D Fault Plane Viewer",
            width=280, height=48,
            fg_color="#0a1a2a", hover_color="#0f2a3a",
            border_width=1, border_color="#3b8ed0",
            text_color="#3b8ed0",
            font=(res.FONT_LABEL[0], 13, "bold"),
            command=lambda: FaultPlane3DPanel(
                p, srf_path,
                src_file=p._src_file,
                run_id=p._run_id
            )
        ).pack(pady=(10, 0))

        ctk.CTkLabel(
            btn_frame,
            text="Opens an interactive viewer with parameter toggle,\ncontour lines, and fullscreen export.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555",
            justify="center"
        ).pack(pady=(8, 0))

        # Preview thumbnail from BBP rupture map PNG
        rupture_png = f"{p._outdata}/{p._base_name}.png"
        if WSLBridge.wsl_path_exists(rupture_png):
            from ui.results.ResultsHelpers import _section_label, _image_tab
            _section_label(scroll, "BBP Rupture Map (preview)")
            img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
            img_frame.pack(fill="x", pady=(0, 10))
            _image_tab(img_frame, rupture_png, "Rupture map not found.", master=p)