# ComparisonMapWidget.py — ui/results/ComparisonMapWidget.py
# -------------------------------------------------------
# Dual interactive station map for ComparisonPanel.
# Shows two side-by-side matplotlib maps — one per run.
# Clicking a station dot on either map fires a callback
# that updates ComparisonPanel's station selectors and
# triggers a data reload.
#
# Public API:
#   ComparisonMapWidget(master, on_station_selected_a,
#                       on_station_selected_b)
#   .load_run_a(run_dict)  — populate map A
#   .load_run_b(run_dict)  — populate map B
#   .set_selected_a(name)  — highlight station on map A
#   .set_selected_b(name)  — highlight station on map B
#   .clear()               — reset both maps
# -------------------------------------------------------

import os
import sys
import math
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge


# Click proximity threshold — fraction of axis range
_CLICK_THRESHOLD = 0.04


class ComparisonMapWidget(ctk.CTkFrame):
    """
    Two clickable matplotlib maps embedded in a CTkFrame.
    Left map = Run A stations, Right map = Run B stations.
    Clicking a dot fires on_station_selected_a / _b(station_name).
    """

    def __init__(self, master,
                 on_station_selected_a=None,
                 on_station_selected_b=None,
                 **kwargs):
        kwargs.setdefault("fg_color", "#111111")
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self._cb_a = on_station_selected_a  # callable(station_name)
        self._cb_b = on_station_selected_b

        # Station data: list of (lon, lat, name)
        self._stations_a = []
        self._stations_b = []

        # Fault geometry from .src file
        self._src_a = None
        self._src_b = None

        # Currently selected station names
        self._selected_a = None
        self._selected_b = None

        # Run info dicts
        self._run_a = None
        self._run_b = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Header strip
        hdr = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0, height=30)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="Click a station on the map to compare it — both maps show the same station list per run",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        ).pack(side="left", padx=12, pady=6)

        # Map container — two columns
        map_frame = ctk.CTkFrame(self, fg_color="#0d0d0d", corner_radius=0)
        map_frame.pack(fill="both", expand=True)
        map_frame.grid_columnconfigure(0, weight=1, uniform="map")
        map_frame.grid_columnconfigure(1, weight=1, uniform="map")

        # --- MAP A ---
        frame_a = ctk.CTkFrame(map_frame, fg_color="#0d0d0d", corner_radius=0)
        frame_a.grid(row=0, column=0, sticky="nsew", padx=(0, 1))

        self.lbl_run_a = ctk.CTkLabel(
            frame_a,
            text="Run A — no run selected",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#5ab4ff",
            anchor="w"
        )
        self.lbl_run_a.pack(anchor="w", padx=10, pady=(6, 2))

        self.lbl_sel_a = ctk.CTkLabel(
            frame_a,
            text="No station selected",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555",
            anchor="w"
        )
        self.lbl_sel_a.pack(anchor="w", padx=10, pady=(0, 4))

        self._fig_a, self._ax_a = self._make_figure()
        self._canvas_a = FigureCanvasTkAgg(self._fig_a, master=frame_a)
        self._canvas_a.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._canvas_a.mpl_connect("button_press_event",
                                   lambda e: self._on_click(e, "A"))

        # --- MAP B ---
        frame_b = ctk.CTkFrame(map_frame, fg_color="#0d0d0d", corner_radius=0)
        frame_b.grid(row=0, column=1, sticky="nsew")

        self.lbl_run_b = ctk.CTkLabel(
            frame_b,
            text="Run B — no run selected",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        )
        self.lbl_run_b.pack(anchor="w", padx=10, pady=(6, 2))

        self.lbl_sel_b = ctk.CTkLabel(
            frame_b,
            text="No station selected",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555",
            anchor="w"
        )
        self.lbl_sel_b.pack(anchor="w", padx=10, pady=(0, 4))

        self._fig_b, self._ax_b = self._make_figure()
        self._canvas_b = FigureCanvasTkAgg(self._fig_b, master=frame_b)
        self._canvas_b.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._canvas_b.mpl_connect("button_press_event",
                                   lambda e: self._on_click(e, "B"))

    def _make_figure(self):
        fig, ax = plt.subplots(figsize=(5, 3.2), dpi=90)
        fig.patch.set_facecolor("#0d0d0d")
        ax.set_facecolor("#111111")
        ax.tick_params(colors="#555555", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")
        ax.set_xlabel("Longitude (°)", color="#555555", fontsize=8)
        ax.set_ylabel("Latitude (°)",  color="#555555", fontsize=8)
        ax.text(0.5, 0.5, "No run selected",
                transform=ax.transAxes,
                ha="center", va="center",
                color="#333333", fontsize=10)
        fig.tight_layout(pad=1.2)
        return fig, ax

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def load_run_a(self, run_dict):
        """Load and draw station map for Run A."""
        self._run_a = run_dict
        self._selected_a = None
        self._stations_a = self._parse_stations(run_dict)
        self._src_a      = self._parse_src(run_dict)
        label = run_dict["label"] if run_dict else "No run selected"
        short = label.split("—")[-1].strip() if "—" in label else label
        self.lbl_run_a.configure(text=f"Run A  —  {short}")
        self.lbl_sel_a.configure(text="Click a station to select", text_color="#555555")
        self._draw_map(self._ax_a, self._canvas_a, self._stations_a,
                       self._selected_a, self._src_a,
                       color_dot="#5ab4ff", color_sel="#ffdd00")

    def load_run_b(self, run_dict):
        """Load and draw station map for Run B."""
        self._run_b = run_dict
        self._selected_b = None
        self._stations_b = self._parse_stations(run_dict)
        self._src_b      = self._parse_src(run_dict)
        label = run_dict["label"] if run_dict else "No run selected"
        short = label.split("—")[-1].strip() if "—" in label else label
        self.lbl_run_b.configure(text=f"Run B  —  {short}")
        self.lbl_sel_b.configure(text="Click a station to select", text_color="#555555")
        self._draw_map(self._ax_b, self._canvas_b, self._stations_b,
                       self._selected_b, self._src_b,
                       color_dot="#ffaa44", color_sel="#ffdd00")

    def set_selected_a(self, name):
        """Highlight a station on map A (called from ComparisonPanel dropdown)."""
        self._selected_a = name
        self._draw_map(self._ax_a, self._canvas_a, self._stations_a,
                       name, self._src_a,
                       color_dot="#5ab4ff", color_sel="#ffdd00")
        self._update_sel_label(self.lbl_sel_a, name, self._stations_a)

    def set_selected_b(self, name):
        """Highlight a station on map B (called from ComparisonPanel dropdown)."""
        self._selected_b = name
        self._draw_map(self._ax_b, self._canvas_b, self._stations_b,
                       name, self._src_b,
                       color_dot="#ffaa44", color_sel="#ffdd00")
        self._update_sel_label(self.lbl_sel_b, name, self._stations_b)

    def clear(self):
        """Reset both maps."""
        self._stations_a = []
        self._stations_b = []
        self._selected_a = None
        self._selected_b = None
        self._run_a = None
        self._run_b = None
        for ax, canvas in [(self._ax_a, self._canvas_a),
                           (self._ax_b, self._canvas_b)]:
            ax.cla()
            ax.set_facecolor("#111111")
            ax.text(0.5, 0.5, "No run selected",
                    transform=ax.transAxes,
                    ha="center", va="center",
                    color="#333333", fontsize=10)
            canvas.draw_idle()
        self.lbl_run_a.configure(text="Run A — no run selected")
        self.lbl_run_b.configure(text="Run B — no run selected")
        self.lbl_sel_a.configure(text="No station selected", text_color="#555555")
        self.lbl_sel_b.configure(text="No station selected", text_color="#555555")

    # ------------------------------------------------------------------
    # STL PARSING
    # ------------------------------------------------------------------

    def _parse_stations(self, run_dict):
        """
        Reads the .stl file from the run's indata folder and returns
        a list of (lon, lat, name) tuples.
        Falls back to reading from param_files/ if indata is unavailable.
        """
        if not run_dict:
            return []

        run_id = run_dict.get("run_id", "")
        home   = WSLBridge.get_wsl_home()

        # Try indata first (most reliable — copied by BBP at run time)
        stl_paths = [
            f"{home}/bbp_data/indata/{run_id}",
            f"{run_dict['outdata_path']}/param_files",
        ]

        content = ""
        for folder in stl_paths:
            result = WSLBridge.run_command(
                f"find '{folder}' -name '*.stl' 2>/dev/null | head -1"
            )
            stl_file = result.stdout.strip()
            if stl_file:
                ok, text = WSLBridge.read_wsl_file(stl_file)
                if ok and text:
                    content = text
                    break

        if not content:
            return []

        stations = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    lon  = float(parts[0])
                    lat  = float(parts[1])
                    name = parts[2]
                    stations.append((lat, lon, name))
                except ValueError:
                    continue

        return stations

    # ------------------------------------------------------------------
    # SRC PARSING
    # ------------------------------------------------------------------

    def _parse_src(self, run_dict):
        """
        Reads the .src file for a run and returns fault geometry dict.
        Uses the same indata path that proved reliable in testing.
        """
        if not run_dict:
            return None

        import re
        run_id = run_dict.get("run_id", "")
        home   = WSLBridge.get_wsl_home()

        # Find the .src file — check indata first, then param_files
        search_paths = [
            f"{home}/bbp_data/indata/{run_id}",
            f"{run_dict['outdata_path']}/param_files",
        ]

        content = ""
        for folder in search_paths:
            result = WSLBridge.run_command(
                f"find '{folder}' -maxdepth 1 -name '*.src' 2>/dev/null | head -1"
            )
            src_file = result.stdout.strip()
            if not src_file:
                continue
            ok, text = WSLBridge.read_wsl_file(src_file)
            if ok and text.strip():
                content = text
                break

        if not content:
            return None

        def _get(key):
            m = re.search(
                rf'^\s*{re.escape(key)}\s*=\s*([^\s#\r\n]+)',
                content, re.IGNORECASE | re.MULTILINE
            )
            if m:
                try:
                    return float(m.group(1).strip())
                except ValueError:
                    pass
            return None

        lat_top   = _get("LAT_TOP_CENTER")
        lon_top   = _get("LON_TOP_CENTER")
        strike    = _get("STRIKE")
        fault_len = _get("FAULT_LENGTH")
        fault_wid = _get("FAULT_WIDTH")
        dip       = _get("DIP")
        depth_top = _get("DEPTH_TO_TOP")
        hypo_stk  = _get("HYPO_ALONG_STK")
        hypo_dip  = _get("HYPO_DOWN_DIP")
        magnitude = _get("MAGNITUDE")

        # Must have at minimum these four to draw anything useful
        if None in (lat_top, lon_top, strike, fault_len):
            return None

        fw = fault_wid if fault_wid is not None else 10.0
        return {
            "lat_top"  : lat_top,
            "lon_top"  : lon_top,
            "strike"   : strike,
            "fault_len": fault_len,
            "fault_wid": fw,
            "dip"      : dip       if dip       is not None else 90.0,
            "depth_top": depth_top if depth_top is not None else 0.0,
            "hypo_stk" : hypo_stk  if hypo_stk  is not None else fault_len / 2.0,
            "hypo_dip" : hypo_dip  if hypo_dip  is not None else fw / 2.0,
            "magnitude": magnitude if magnitude is not None else 0.0,
        }

    # ------------------------------------------------------------------
    # MAP DRAWING
    # ------------------------------------------------------------------

    def _draw_map(self, ax, canvas, stations, selected_name, src,
                  color_dot="#5ab4ff", color_sel="#ffdd00"):
        ax.cla()
        ax.set_facecolor("#111111")
        ax.tick_params(colors="#555555", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")
        ax.set_xlabel("Longitude (°)", color="#555555", fontsize=8)
        ax.set_ylabel("Latitude (°)",  color="#555555", fontsize=8)
        ax.grid(True, color="#1e1e1e", linewidth=0.5, linestyle="--")

        if not stations and src is None:
            ax.text(0.5, 0.5, "No stations found",
                    transform=ax.transAxes,
                    ha="center", va="center",
                    color="#333333", fontsize=9)
            canvas.draw_idle()
            return

        # stations stored as (lat, lon, name)
        lons = [s[1] for s in stations]
        lats = [s[0] for s in stations]

        # --- FAULT GEOMETRY ---
        hypo_lon = None
        hypo_lat = None

        if src:
            lat_top   = src["lat_top"]
            lon_top   = src["lon_top"]
            strike    = src["strike"]
            fault_len = src["fault_len"]
            dip       = src["dip"]
            hypo_stk  = src["hypo_stk"]
            hypo_dip  = src["hypo_dip"]
            magnitude = src["magnitude"]

            km_per_lat = 111.32
            km_per_lon = 111.32 * math.cos(math.radians(lat_top))
            strike_rad = math.radians(strike)
            dip_rad    = math.radians(dip)

            # Fault trace — half-length each side of top center along strike
            half = fault_len / 2.0
            t_start_lon = lon_top - (half * math.sin(strike_rad)) / km_per_lon
            t_start_lat = lat_top - (half * math.cos(strike_rad)) / km_per_lat
            t_end_lon   = lon_top + (half * math.sin(strike_rad)) / km_per_lon
            t_end_lat   = lat_top + (half * math.cos(strike_rad)) / km_per_lat

            ax.plot(
                [t_start_lon, t_end_lon],
                [t_start_lat, t_end_lat],
                color="white", linewidth=1.2, zorder=5, alpha=0.45,
                solid_capstyle="round",
                label=f"Fault trace (L={fault_len:.1f} km)"
            )

            # Top center marker
            ax.scatter(lon_top, lat_top, marker="s", s=20,
                       color="white", zorder=6, linewidths=0)

            # Hypocenter — project from top center
            hypo_lon = lon_top + (hypo_stk * math.sin(strike_rad)) / km_per_lon
            hypo_lat = lat_top + (hypo_stk * math.cos(strike_rad)) / km_per_lat
            dip_surface_km = hypo_dip * math.cos(dip_rad)
            dip_dir_rad    = strike_rad + math.pi / 2.0
            hypo_lon += (dip_surface_km * math.sin(dip_dir_rad)) / km_per_lon
            hypo_lat += (dip_surface_km * math.cos(dip_dir_rad)) / km_per_lat

            # Large star — visible at any zoom level
            ax.scatter(hypo_lon, hypo_lat,
                       marker="*", s=150, color="#ff5555",
                       zorder=8, alpha=0.7, linewidths=0.5, edgecolors="white",
                       label=f"Hypocenter  Mw {magnitude:.1f}")

            # Text label next to hypocenter
            ax.annotate(
                f"Mw {magnitude:.1f}",
                (hypo_lon, hypo_lat),
                textcoords="offset points", xytext=(8, 6),
                fontsize=7, color="#ff8888",
                fontweight="normal", zorder=9, alpha=0.75
            )

        # --- STATIONS --- (lat, lon, name)
        for lat, lon, name in stations:
            if name == selected_name:
                continue
            ax.scatter(lon, lat, s=40, color=color_dot,
                       zorder=3, alpha=0.85, linewidths=0)
            ax.annotate(
                name, (lon, lat),
                textcoords="offset points", xytext=(4, 4),
                fontsize=6, color="#888888", zorder=4
            )

        # Selected station on top
        if selected_name:
            for lat, lon, name in stations:
                if name == selected_name:
                    ax.scatter(lon, lat, s=180, color=color_sel,
                               zorder=9, alpha=0.35, linewidths=0)
                    ax.scatter(lon, lat, s=70, color=color_sel,
                               zorder=10, linewidths=0)
                    ax.annotate(
                        name, (lon, lat),
                        textcoords="offset points", xytext=(6, 5),
                        fontsize=8, color=color_sel,
                        fontweight="normal", zorder=9, alpha=0.75
                    )
                    break

        # Axis limits — encompass stations AND fault/hypocenter always
        all_lons = list(lons)
        all_lats = list(lats)

        if hypo_lon is not None:
            all_lons.append(hypo_lon)
            all_lats.append(hypo_lat)
        if src:
            all_lons += [t_start_lon, t_end_lon, src["lon_top"]]
            all_lats += [t_start_lat, t_end_lat, src["lat_top"]]

        if all_lons:
            lon_range = max(all_lons) - min(all_lons)
            lat_range = max(all_lats) - min(all_lats)
            pad_lon   = max(lon_range * 0.12, 0.05)
            pad_lat   = max(lat_range * 0.12, 0.05)
            ax.set_xlim(min(all_lons) - pad_lon, max(all_lons) + pad_lon)
            ax.set_ylim(min(all_lats) - pad_lat, max(all_lats) + pad_lat)

        if src or stations:
            ax.legend(
                fontsize=7,
                facecolor="#1a1a1a",
                edgecolor="#333333",
                labelcolor="white",
                loc="upper left",
                framealpha=0.8
            )

        fig = self._fig_a if ax is self._ax_a else self._fig_b
        fig.tight_layout(pad=1.2)
        canvas.draw_idle()

    # ------------------------------------------------------------------
    # CLICK HANDLING
    # ------------------------------------------------------------------

    def _on_click(self, event, side):
        """Handles a matplotlib click event on either map."""
        ax       = self._ax_a if side == "A" else self._ax_b
        stations = self._stations_a if side == "A" else self._stations_b

        if event.inaxes is not ax or not stations:
            return

        click_lon = event.xdata
        click_lat = event.ydata
        if click_lon is None or click_lat is None:
            return

        # Dynamic proximity threshold based on current axis range
        x_range = ax.get_xlim()
        y_range = ax.get_ylim()
        thr_lon = (x_range[1] - x_range[0]) * _CLICK_THRESHOLD
        thr_lat = (y_range[1] - y_range[0]) * _CLICK_THRESHOLD

        nearest      = None
        nearest_dist = float("inf")

        for lat, lon, name in stations:
            dist = math.sqrt(((click_lon - lon) / max(thr_lon, 1e-9)) ** 2 +
                             ((click_lat - lat) / max(thr_lat, 1e-9)) ** 2)
            if dist < 1.0 and dist < nearest_dist:
                nearest_dist = dist
                nearest      = (lat, lon, name)

        if nearest is None:
            return

        lat, lon, name = nearest

        if side == "A":
            self._selected_a = name
            self._draw_map(self._ax_a, self._canvas_a, self._stations_a,
                           name, self._src_a,
                           color_dot="#5ab4ff", color_sel="#ffdd00")
            self._update_sel_label(self.lbl_sel_a, name, stations)
            if self._cb_a:
                self._cb_a(name)
        else:
            self._selected_b = name
            self._draw_map(self._ax_b, self._canvas_b, self._stations_b,
                           name, self._src_b,
                           color_dot="#ffaa44", color_sel="#ffdd00")
            self._update_sel_label(self.lbl_sel_b, name, stations)
            if self._cb_b:
                self._cb_b(name)

    def _update_sel_label(self, label_widget, name, stations):
        """Updates the 'selected station' label below the run title."""
        if not name:
            label_widget.configure(
                text="Click a station to select",
                text_color="#555555"
            )
            return

        coords = next(
            (f"lat {lat:.5f}   lon {lon:.5f}"
             for lat, lon, n in stations if n == name),
            ""
        )
        label_widget.configure(
            text=f"Selected: {name}   {coords}",
            text_color="#ffdd00"
        )