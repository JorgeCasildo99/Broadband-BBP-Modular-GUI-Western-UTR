# SlipDistributionPanel.py — ui/results/SlipDistributionPanel.py
# -------------------------------------------------------
# Visualizes the kinematic slip distribution from a BBP
# Genslip .srf file (Standard Rupture Format v2.0).
# Shows: Slip, Rake, Rise Time, Rupture Time on the fault
# plane with contour lines and hypocenter marker.
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys
import math
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.colors import LinearSegmentedColormap
    MPLOT_OK = True
except ImportError:
    MPLOT_OK = False

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

from ui.results.ImageFullscreenPanel import ImageFullscreenPanel


# ──────────────────────────────────────────────────────────────────────────────
# SRF PARSER
# ──────────────────────────────────────────────────────────────────────────────

def parse_srf(content):
    """
    Parses BBP Standard Rupture Format v2.0.

    Returns dict:
      plane: {nstrike, ndip, len_km, wid_km, strike, dip, depth_top,
              hypo_along_strike, hypo_along_dip}
      points: list of dicts with keys:
              lon, lat, dep, tinit, rake, slip_cm (total), slip1, slip2,
              rise_time, dt
    """
    lines  = content.strip().splitlines()
    result = {"plane": {}, "points": []}
    i      = 0

    # Version line
    i += 1

    # Skip comment lines and command line
    while i < len(lines) and (
        lines[i].startswith("#") or lines[i].strip() == ""
    ):
        i += 1

    # PLANE header
    while i < len(lines) and "PLANE" not in lines[i]:
        i += 1
    i += 1  # skip PLANE N line

    # Plane geometry line 1: lon lat nstrike ndip len_km wid_km
    p1 = lines[i].split()
    nstrike = int(p1[2])
    ndip    = int(p1[3])
    len_km  = float(p1[4])
    wid_km  = float(p1[5])
    i += 1

    # Plane geometry line 2: strike dip depth_top hypo_along_stk hypo_along_dip
    p2 = lines[i].split()
    strike       = float(p2[0])
    dip          = float(p2[1])
    depth_top    = float(p2[2])
    hypo_stk_km  = float(p2[3])
    hypo_dip_km  = float(p2[4])
    i += 1

    result["plane"] = {
        "nstrike"      : nstrike,
        "ndip"         : ndip,
        "len_km"       : len_km,
        "wid_km"       : wid_km,
        "strike"       : strike,
        "dip"          : dip,
        "depth_top"    : depth_top,
        "hypo_stk_km"  : hypo_stk_km,
        "hypo_dip_km"  : hypo_dip_km,
    }

    # POINTS header
    while i < len(lines) and "POINTS" not in lines[i]:
        i += 1
    total_points = int(lines[i].split()[1])
    i += 1

    # Parse each point
    for _ in range(total_points):
        if i >= len(lines):
            break

        # Line 1: lon lat dep stk dip area tinit dt vs density
        h = lines[i].split()
        i += 1
        if len(h) < 8:
            continue
        lon   = float(h[0])
        lat   = float(h[1])
        dep   = float(h[2])
        tinit = float(h[6])
        dt    = float(h[7])

        # Line 2: rake slip1 nt1 slip2 nt2 slip3 nt3
        d = lines[i].split()
        i += 1
        if len(d) < 7:
            continue
        rake  = float(d[0])
        slip1 = float(d[1])   # strike-slip (cm)
        nt1   = int(d[2])
        slip2 = float(d[3])   # dip-slip (cm)
        nt2   = int(d[4])
        slip3 = float(d[5])   # tensile (cm), usually 0
        nt3   = int(d[6])

        # Total slip magnitude
        slip_cm = math.sqrt(slip1**2 + slip2**2 + slip3**2)

        # Rise time: nt1 * dt (duration of slip pulse)
        rise_time = nt1 * dt if nt1 > 0 else 0.0

        # Skip slip time series (ceil((nt1+nt2+nt3)/6) lines)
        total_nt = nt1 + nt2 + nt3
        skip     = math.ceil(total_nt / 6) if total_nt > 0 else 0
        i       += skip

        result["points"].append({
            "lon"       : lon,
            "lat"       : lat,
            "dep"       : dep,
            "tinit"     : tinit,
            "rake"      : rake,
            "slip_cm"   : slip_cm,
            "slip1"     : slip1,
            "slip2"     : slip2,
            "rise_time" : rise_time,
            "dt"        : dt,
        })

    return result


# ──────────────────────────────────────────────────────────────────────────────
# PANEL
# ──────────────────────────────────────────────────────────────────────────────

class SlipDistributionPanel(ctk.CTkToplevel):
    """
    Popup window showing the kinematic slip distribution from a Genslip .srf file.
    Displays Slip, Rake, Rise Time, or Rupture Time as a 2D color map
    on the fault plane with rupture time contours and hypocenter star.
    """

    PARAMS = [
        ("Slip (cm)",        "slip_cm",   "YlOrRd",  "Slip (cm)"),
        ("Rake (°)",         "rake",      "RdBu",    "Rake (degrees)"),
        ("Rise Time (s)",    "rise_time", "plasma",  "Rise Time (s)"),
        ("Rupture Time (s)", "tinit",     "viridis", "Rupture Time (s)"),
    ]

    def __init__(self, master, srf_path, run_id=""):
        super().__init__(master)

        self._srf_path = srf_path
        self._run_id   = run_id
        self._srf_data = None
        self._grid     = {}   # cached numpy grids keyed by param name
        self._pil_img  = None
        self._param_var = None

        self.title(f"Slip Distribution — {os.path.basename(srf_path)}")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self.after(150, self._on_ready)
        self.after(300, self._load_srf)

    def _on_ready(self):
        try:
            self.wm_attributes("-zoomed", True)
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # ── UI BUILD ─────────────────────────────────────────────────────────────

    def _build_ui(self):

        # Top bar
        bar = ctk.CTkFrame(self, fg_color="#0d0d0d",
                           corner_radius=0, height=50)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="Kinematic Slip Distribution",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            bar,
            text="Click the plot to open fullscreen",
            font=(res.FONT_LABEL[0], 10),
            text_color="#444444"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            bar, text="Close", width=80, height=30,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=10, pady=10)

        # Main layout
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=8)
        main.grid_columnconfigure(0, weight=0, minsize=240)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # Left controls
        left = ctk.CTkFrame(main, fg_color="#111111",
                            corner_radius=8, border_width=1,
                            border_color="#2a2a2a")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_controls(left)

        # Right plot area
        self.plot_frame = ctk.CTkFrame(
            main, fg_color="#0d0d0d",
            corner_radius=8, border_width=1, border_color="#2a2a2a"
        )
        self.plot_frame.grid(row=0, column=1, sticky="nsew")

        self._loading_lbl = ctk.CTkLabel(
            self.plot_frame,
            text="Loading SRF file...",
            font=(res.FONT_LABEL[0], 14),
            text_color="#444444"
        )
        self._loading_lbl.pack(expand=True)

    def _build_controls(self, parent):

        def _section(text):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=(12, 2))
            ctk.CTkLabel(
                f, text=text,
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color="#666666"
            ).pack(side="left")
            ctk.CTkFrame(f, fg_color="#333333", height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=6)

        # Parameter selector with descriptions
        _section("PARAMETER TO DISPLAY")

        self._param_var = ctk.StringVar(value=self.PARAMS[0][0])

        DESCRIPTIONS = {
            "Slip (cm)"        : "Total slip magnitude per subfault.\nHigh-slip zones = asperities (main energy sources).",
            "Rake (°)"         : "Direction of fault motion.\n0°/180° = strike-slip, 90° = reverse, -90° = normal.",
            "Rise Time (s)"    : "Duration of the slip pulse at each patch.\nLonger rise time = slower, smoother rupture.",
            "Rupture Time (s)" : "Time when the rupture wave reached each patch.\nShows how the rupture front propagated.",
        }

        for label, key, cmap, cbar_label in self.PARAMS:
            param_frame = ctk.CTkFrame(parent, fg_color="transparent")
            param_frame.pack(fill="x", padx=12, pady=(4, 0))

            ctk.CTkRadioButton(
                param_frame,
                text=label,
                variable=self._param_var,
                value=label,
                command=self._on_param_changed,
                font=(res.FONT_LABEL[0], 11, "bold"),
                fg_color=res.COLOR_PRIMARY
            ).pack(anchor="w")

            ctk.CTkLabel(
                param_frame,
                text=DESCRIPTIONS.get(label, ""),
                font=(res.FONT_LABEL[0], 9),
                text_color="#555555",
                justify="left",
                wraplength=210
            ).pack(anchor="w", padx=(22, 0), pady=(0, 4))

        # Contour options
        _section("RUPTURE TIME CONTOURS")

        self._show_contours = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            parent,
            text="Show contour lines",
            variable=self._show_contours,
            command=self._redraw,
            font=(res.FONT_LABEL[0], 11),
            fg_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=16, pady=3)

        ctk.CTkLabel(
            parent,
            text="Contour divisor (BBP default = 2.0):",
            font=(res.FONT_LABEL[0], 10),
            text_color="gray"
        ).pack(anchor="w", padx=16, pady=(6, 0))

        ctk.CTkLabel(
            parent,
            text="n_levels = (max_t − min_t) / divisor\n"
                 "min 10 levels enforced (BBP rule)\n"
                 "Each level = one rupture time isochrone\n"
                 "One level can draw many curve segments",
            font=("Courier", 8),
            text_color="#444444",
            justify="left"
        ).pack(anchor="w", padx=16)

        self._contour_interval = ctk.StringVar(value="2.0")
        ctk.CTkEntry(
            parent,
            textvariable=self._contour_interval,
            width=80, height=28,
            font=(res.FONT_LABEL[0], 11)
        ).pack(anchor="w", padx=16, pady=(2, 4))

        # Contour line width slider
        ctk.CTkLabel(
            parent,
            text="Line thickness:",
            font=(res.FONT_LABEL[0], 10),
            text_color="gray"
        ).pack(anchor="w", padx=16, pady=(4, 0))

        width_row = ctk.CTkFrame(parent, fg_color="transparent")
        width_row.pack(fill="x", padx=16, pady=(2, 4))

        self._contour_width_var = ctk.DoubleVar(value=0.6)
        self._contour_width_lbl = ctk.CTkLabel(
            width_row,
            text="0.6",
            font=(res.FONT_LABEL[0], 10),
            text_color="white",
            width=28
        )
        self._contour_width_lbl.pack(side="right")

        ctk.CTkSlider(
            width_row,
            from_=0.2, to=3.0,
            variable=self._contour_width_var,
            command=self._on_contour_width_changed,
            width=140, height=16
        ).pack(side="left", fill="x", expand=True)

        # Contour line color selector
        ctk.CTkLabel(
            parent,
            text="Line color:",
            font=(res.FONT_LABEL[0], 10),
            text_color="gray"
        ).pack(anchor="w", padx=16, pady=(4, 0))

        self._contour_color = ctk.StringVar(value="white")
        color_frame = ctk.CTkFrame(parent, fg_color="transparent")
        color_frame.pack(anchor="w", padx=16, pady=(2, 4))

        ctk.CTkRadioButton(
            color_frame, text="White",
            variable=self._contour_color, value="white",
            command=self._redraw,
            font=(res.FONT_LABEL[0], 11),
            fg_color=res.COLOR_PRIMARY
        ).pack(side="left", padx=(0, 10))

        ctk.CTkRadioButton(
            color_frame, text="Black",
            variable=self._contour_color, value="black",
            command=self._redraw,
            font=(res.FONT_LABEL[0], 11),
            fg_color=res.COLOR_PRIMARY
        ).pack(side="left")

        ctk.CTkButton(
            parent, text="Apply",
            width=80, height=26,
            fg_color=res.COLOR_PRIMARY, hover_color="#004070",
            font=(res.FONT_LABEL[0], 10),
            command=self._redraw
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Hypocenter
        _section("HYPOCENTER")

        self._show_hypo = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            parent,
            text="Show hypocenter (★)",
            variable=self._show_hypo,
            command=self._redraw,
            font=(res.FONT_LABEL[0], 11),
            fg_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=16, pady=3)

        # Info box (filled after loading)
        _section("FAULT GEOMETRY")
        self._info_frame = ctk.CTkFrame(
            parent, fg_color="#1a1a1a",
            corner_radius=4, border_width=1, border_color="#2a2a2a"
        )
        self._info_frame.pack(fill="x", padx=10, pady=(0, 8))

        self._info_lbl = ctk.CTkLabel(
            self._info_frame,
            text="Loading...",
            font=("Courier", 9),
            text_color="#555555",
            justify="left"
        )
        self._info_lbl.pack(anchor="w", padx=8, pady=6)

        # Scientific note
        _section("SCIENTIFIC NOTE")
        ctk.CTkLabel(
            parent,
            text=(
                "The slip distribution shows how\n"
                "much each patch of the fault\n"
                "moved during the earthquake.\n\n"
                "High-slip zones (asperities) are\n"
                "the main sources of energy.\n\n"
                "Contour lines show when the\n"
                "rupture wave reached each patch\n"
                "(rupture time isochrones).\n\n"
                "★ marks the hypocenter where\n"
                "rupture initiated."
            ),
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555",
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 12))

    # ── SRF LOADING ───────────────────────────────────────────────────────────

    def _load_srf(self):
        import threading

        def _do():
            ok, content = WSLBridge.read_wsl_file(self._srf_path)
            if not ok or not content.strip():
                self.after(0, self._on_load_error,
                           f"Cannot read SRF file:\n{self._srf_path}")
                return
            try:
                data = parse_srf(content)
                self.after(0, self._on_load_done, data)
            except Exception as e:
                self.after(0, self._on_load_error, f"SRF parse error: {e}")

        threading.Thread(target=_do, daemon=True).start()

    def _on_load_error(self, msg):
        self._loading_lbl.configure(
            text=msg, text_color=res.COLOR_ERROR
        )

    def _on_load_done(self, data):
        self._srf_data = data
        plane = data["plane"]

        # Update info box
        hypo_dep = (plane["depth_top"] +
                    plane["hypo_dip_km"] * math.sin(math.radians(plane["dip"])))
        # Check if tinit came from .tinit file or SRF fallback
        home     = WSLBridge.get_wsl_home()
        tmp_path = f"{home}/bbp_data/tmpdata/{self._run_id}"
        tinit_check = WSLBridge.run_command(
            f"ls '{tmp_path}'/*_seg0.tinit 2>/dev/null | head -1"
        )
        tinit_source = "from .tinit file ✓" if tinit_check.stdout.strip() else "from .srf file (fallback)"

        self._info_lbl.configure(
            text=(
                f"Strike:   {plane['strike']}°\n"
                f"Dip:      {plane['dip']}°\n"
                f"Length:   {plane['len_km']} km\n"
                f"Width:    {plane['wid_km']} km\n"
                f"Top dep.: {plane['depth_top']} km\n"
                f"Hypo dep: {hypo_dep:.2f} km\n"
                f"Patches:  {plane['nstrike']}×{plane['ndip']}\n"
                f"Points:   {len(data['points'])}\n"
                f"Tinit:    {tinit_source}"
            ),
            text_color="#aaaaaa"
        )

        # Pre-compute grids
        self._build_grids()

        # Draw initial plot
        self._loading_lbl.destroy()
        self._redraw()

    def _build_grids(self):
        """
        Reshapes flat point list into 2D numpy grids.
        For tinit: reads from the .tinit file using BBP's exact
        read_xy_file algorithm (x-fast ordering, column 3).
        For slip, rake, rise_time: reads from parsed SRF points.
        """
        if not MPLOT_OK:
            return
        plane  = self._srf_data["plane"]
        ns     = plane["nstrike"]
        nd     = plane["ndip"]
        pts    = self._srf_data["points"]

        # Clamp in case parse returned fewer points
        total    = min(len(pts), ns * nd)
        pts      = pts[:total]
        ns_actual = total // nd if nd > 0 else ns

        # Along-strike and along-dip axes (km)
        dx = plane["len_km"] / ns
        dz = plane["wid_km"] / nd
        x  = np.arange(ns_actual) * dx + dx / 2
        z  = np.arange(nd)        * dz + dz / 2

        # Slip, rake, rise_time from SRF points
        for key in ("slip_cm", "rake", "rise_time"):
            vals = np.array([p[key] for p in pts])
            pad  = ns_actual * nd - len(vals)
            if pad > 0:
                vals = np.append(vals, np.zeros(pad))
            grid = vals.reshape(nd, ns_actual)
            self._grid[key] = (x, z, grid)

        # Tinit — try to read from .tinit file exactly like BBP does
        # File: {srf_basename}_seg0.tinit in tmpdata/{run_id}/
        # Format: x_km  y_km  tinit  (x-fast ordering, numx=nstrike, numy=ndip)
        tinit_grid = self._read_tinit_file(ns_actual, nd)

        if tinit_grid is not None:
            self._grid["tinit"] = (x, z, tinit_grid)
        else:
            # Fallback: use tinit from SRF points (less accurate for contours)
            vals = np.array([p["tinit"] for p in pts])
            pad  = ns_actual * nd - len(vals)
            if pad > 0:
                vals = np.append(vals, np.zeros(pad))
            grid = vals.reshape(nd, ns_actual)
            self._grid["tinit"] = (x, z, grid)

    def _read_tinit_file(self, numx, numy):
        """
        Reads the .tinit file using BBP's exact read_xy_file algorithm.
        File is in ~/bbp_data/tmpdata/{run_id}/{basename}_seg0.tinit
        Returns ndarray of shape (numy, numx) or None if not found.
        """
        if not self._run_id:
            return None

        home     = WSLBridge.get_wsl_home()
        tmp_path = f"{home}/bbp_data/tmpdata/{self._run_id}"

        # Find the .tinit file — pattern: *_seg0.tinit
        result = WSLBridge.run_command(
            f"ls '{tmp_path}'/*_seg0.tinit 2>/dev/null | head -1"
        )
        tinit_path = result.stdout.strip()
        if not tinit_path:
            return None

        ok, content = WSLBridge.read_wsl_file(tinit_path)
        if not ok or not content.strip():
            return None

        lines = content.strip().splitlines()
        if len(lines) < numx * numy:
            return None

        # BBP read_xy_file: x-fast ordering, column index 2 (0-based)
        data = np.zeros((numy, numx), dtype=float)
        try:
            for y in range(numy):
                for x in range(numx):
                    tokens = lines[y * numx + x].split()
                    data[y][x] = float(tokens[2])
        except (IndexError, ValueError):
            return None

        return data

    # ── DRAWING ───────────────────────────────────────────────────────────────

    def _on_contour_width_changed(self, value):
        """Update label and redraw when slider moves."""
        self._contour_width_lbl.configure(text=f"{value:.1f}")
        self._redraw()

    def _on_param_changed(self):
        self._redraw()

    def _redraw(self):
        if not self._srf_data or not self._grid:
            return
        if not MPLOT_OK:
            ctk.CTkLabel(
                self.plot_frame,
                text="matplotlib / numpy not available",
                font=(res.FONT_LABEL[0], 13), text_color="gray"
            ).pack(expand=True)
            return

        # Clear
        for w in self.plot_frame.winfo_children():
            w.destroy()
        plt.close("all")

        # Find which param is selected
        sel_label = self._param_var.get()
        param_key = "slip_cm"
        cmap_name = "hot_r"
        cbar_lbl  = "Slip (cm)"
        for label, key, cmap, cbl in self.PARAMS:
            if label == sel_label:
                param_key = key
                cmap_name = cmap
                cbar_lbl  = cbl
                break

        x, z, grid = self._grid[param_key]
        plane       = self._srf_data["plane"]

        # ── MATCH BBP EXACTLY ────────────────────────────────────────
        # BBP centers X at 0: extent = [-(len/2), +(len/2), wid, 0]
        half_len = plane["len_km"] / 2.0
        wid      = plane["wid_km"]
        extents  = [-half_len, half_len, wid, 0]

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0d0d0d")
        ax.set_facecolor("#1a1a1a")

        # Reserve right space manually
        fig.subplots_adjust(left=0.08, right=0.70, top=0.90, bottom=0.12)

        # Color map — match BBP exactly
        # BBP uses YlOrRd for slip, vmin=0 (white=zero slip), vmax=max
        if param_key == "slip_cm":
            # BBP: vmin=0 anchors white at exactly zero
            vmin = 0
            vmax = np.nanmax(grid)
            # BBP uses YlOrRd for slip
            if cmap_name == "hot_r":
                cmap_name = "YlOrRd"
        else:
            vmin = np.nanmin(grid)
            vmax = np.nanmax(grid)

        norm = plt.Normalize(vmin=vmin, vmax=vmax)

        # BBP uses equal aspect (square pixels) — set on the axes, not imshow
        ax.set_aspect("equal", adjustable="box")
        im = ax.imshow(
            grid,
            cmap=cmap_name,
            norm=norm,
            extent=extents,
            origin="upper"
        )

        # Freeze axis extents (BBP does this too)
        ax.set_xlim(-half_len, half_len)
        ax.set_ylim(wid, 0)

        # Colorbar — explicit axes position
        cbar_ax = fig.add_axes([0.85, 0.12, 0.03, 0.78])
        cbar = fig.colorbar(im, cax=cbar_ax)
        cbar.set_label(cbar_lbl, color="white", fontsize=10, labelpad=8)
        cbar.ax.yaxis.set_tick_params(color="gray", labelcolor="white")
        cbar.outline.set_edgecolor("#333333")

        # ── CONTOURS — match BBP algorithm exactly ───────────────────
        if self._show_contours.get():
            lw    = float(self._contour_width_var.get())
            color = self._contour_color.get()

            # Use tinit grid for contours regardless of displayed param
            _, _, tinit_grid = self._grid["tinit"]

            # BBP: contour_intervals = (max - min) / PLOT_SRF_DEFAULT_CONTOUR_INTERVALS
            # PLOT_SRF_DEFAULT_CONTOUR_INTERVALS = 2.0 (divisor, not seconds)
            mintinit = np.nanmin(tinit_grid)
            maxtinit = np.nanmax(tinit_grid)

            try:
                divisor = float(self._contour_interval.get())
            except ValueError:
                divisor = 2.0

            n_contours = int(round((maxtinit - mintinit) / divisor))
            # BBP enforces minimum of 10 contour lines
            n_contours = max(n_contours, 10)

            if n_contours > 1:
                levels = np.linspace(mintinit, maxtinit, n_contours)
                cs = ax.contour(
                    tinit_grid,
                    levels=levels,
                    colors=color,
                    linewidths=lw,
                    alpha=0.8,
                    # Match BBP: use same extent and origin
                    extent=extents,
                    origin="upper"
                )
                lbl_color = "white" if color == "black" else "black"
                ax.clabel(cs, inline=True, fontsize=7,
                          fmt="%.1fs", colors=lbl_color)

        # ── HYPOCENTER ────────────────────────────────────────────────
        if self._show_hypo.get():
            # shypo is hypo_along_stk from the .src file — distance from
            # CENTER of fault, already in the same coordinate system as
            # the plot (-half_len to +half_len). No subtraction needed.
            hx = plane["hypo_stk_km"]
            hz = plane["hypo_dip_km"]
            ax.plot(hx, hz, "b*", markersize=18, markeredgewidth=0.8,
                    markeredgecolor="white", zorder=10,
                    label="Hypocenter")

        # ── AXES LABELS (match BBP) ───────────────────────────────────
        ax.set_xlabel("Along Strike (km)", color="gray", fontsize=10)
        ax.set_ylabel("Down Dip (km)", color="gray", fontsize=10)
        ax.tick_params(colors="gray", labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")

        # ── DEPTH TWIN AXIS ───────────────────────────────────────────
        depth_top = plane["depth_top"]
        depth_bot = (depth_top +
                     wid * math.sin(math.radians(plane["dip"])))
        ax2 = ax.twinx()
        ax2.set_ylim(depth_bot, depth_top)
        ax2.set_ylabel("Depth (km)", color="#aaaaaa", fontsize=10, labelpad=8)
        ax2.tick_params(colors="#aaaaaa", labelsize=9)
        ax2.set_facecolor("none")
        for spine in ax2.spines.values():
            spine.set_edgecolor("#444444")

        # ── TITLE (match BBP style) ───────────────────────────────────
        avg_slip = np.nanmean(self._grid["slip_cm"][2])
        max_slip = np.nanmax(self._grid["slip_cm"][2])
        _, _, tinit_grid = self._grid["tinit"]
        try:
            divisor = float(self._contour_interval.get())
        except ValueError:
            divisor = 2.0
        n_cont = max(int(round((np.nanmax(tinit_grid) - np.nanmin(tinit_grid)) / divisor)), 10)
        if param_key == "slip_cm":
            subtitle = f"Avg/Max Slip = {avg_slip:.0f}/{max_slip:.0f} cm   |   {n_cont} rupture time levels"
        else:
            subtitle = f"{sel_label}   |   {n_cont} rupture time levels"

        fig.suptitle(
            f"Rupture Model — {os.path.basename(self._srf_path)}\n{subtitle}"
            + (f"  (Run {self._run_id})" if self._run_id else ""),
            color="white", fontsize=11, y=0.98
        )

        if self._show_hypo.get():
            ax.legend(loc="lower right", fontsize=9,
                      framealpha=0.4, facecolor="#1a1a1a",
                      edgecolor="#444444", labelcolor="white")

        # ── EMBED ────────────────────────────────────────────────────
        if PIL_OK:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150,
                        bbox_inches="tight", facecolor="#0d0d0d")
            buf.seek(0)
            self._pil_img = Image.open(buf).copy()
            buf.close()

        cw = FigureCanvasTkAgg(fig, master=self.plot_frame)
        cw.draw()
        tk_w = cw.get_tk_widget()
        tk_w.pack(fill="both", expand=True, padx=6, pady=6)
        tk_w.bind("<Button-1>", lambda e: self._open_fullscreen())

        self._build_stats(grid, param_key, sel_label, cbar_lbl)

    def _build_stats(self, grid, param_key, label, unit_label):
        """Shows min/max/mean stats below the plot."""
        stats = ctk.CTkFrame(
            self.plot_frame, fg_color="#111111",
            corner_radius=0, height=36
        )
        stats.pack(fill="x")
        stats.pack_propagate(False)

        vals = grid.flatten()
        vals = vals[~np.isnan(vals)]
        if len(vals) == 0:
            return

        peak_val = np.max(np.abs(vals))
        peak_idx = np.argmax(np.abs(vals))
        mean_val = np.mean(vals)

        ctk.CTkLabel(
            stats,
            text=(
                f"  {label}:   "
                f"Max = {np.max(vals):.3f}   "
                f"Min = {np.min(vals):.3f}   "
                f"Mean = {mean_val:.3f}   "
                f"Peak abs = {peak_val:.3f}   {unit_label}"
            ),
            font=("Courier", 10),
            text_color="#aaaaaa"
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkLabel(
            stats,
            text="Click plot to fullscreen",
            font=(res.FONT_LABEL[0], 9),
            text_color="#333333",
            cursor="hand2"
        ).pack(side="right", padx=10)

    # ── FULLSCREEN ────────────────────────────────────────────────────────────

    def _open_fullscreen(self):
        if self._pil_img:
            ImageFullscreenPanel(
                self, pil_image=self._pil_img,
                title=f"Slip Distribution — {os.path.basename(self._srf_path)}"
            )