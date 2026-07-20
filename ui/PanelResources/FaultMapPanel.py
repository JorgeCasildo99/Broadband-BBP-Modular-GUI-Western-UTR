import customtkinter as ctk
import os
import sys
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.path import Path as MplPath

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res


class FaultMapPanel(ctk.CTkFrame):
    """
    Read-only fault geometry map: fault trace + hypocenter only.

    Derived from StationPanel — same geometry math (fault trace
    projection, hypocenter surface projection) and the same optional
    terrain/basin-boundary background layers, but with every
    station-related piece removed: no station count/range/distribution
    controls, no manual station placement, no station scatter layer,
    no click-to-identify-station lookup. RuptureGeneratorPanel has no
    station list at all (rupture-only profiles never reach
    Plot_Map/PlotSeis), so none of that applies here.

    NOTE ON GEOGRAPHY: the terrain background and "LA Basin" boundary
    layer are the same hand-drawn California-coastline polygons
    StationPanel uses — they are only meaningful for LA Basin runs.
    Both default ON here (per explicit request) but remain toggleable;
    switch them off manually for non-California geometries such as
    Charlevoix, where they would otherwise draw the wrong coastline
    under the fault.
    """

    LABASIN500_BOUNDARY_LONS = [
        -119.30, -119.00, -118.70, -118.40, -118.10,
        -117.80, -117.50, -117.30, -117.20, -117.30,
        -117.50, -117.80, -118.00, -118.20, -118.50,
        -118.70, -119.00, -119.20, -119.40, -119.30
    ]
    LABASIN500_BOUNDARY_LATS = [
        34.00, 33.70, 33.50, 33.40, 33.42,
        33.50, 33.60, 33.75, 34.00, 34.30,
        34.50, 34.55, 34.60, 34.55, 34.45,
        34.30, 34.20, 34.10, 34.05, 34.00
    ]

    @classmethod
    def is_inside_basin(cls, lon, lat):
        """Same LABasin500 containment check as StationPanel — informational only here."""
        boundary_path = MplPath(
            list(zip(cls.LABASIN500_BOUNDARY_LONS, cls.LABASIN500_BOUNDARY_LATS))
        )
        return bool(boundary_path.contains_point((lon, lat)))

    def __init__(self, master, update_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.update_callback = update_callback

        self._tile_img         = None
        self._tile_extent      = None
        self._tile_source_name = None

        # --- HEADER ---
        self.hdr_group = ctk.CTkFrame(self, fg_color="#252525")
        self.hdr_group.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            self.hdr_group,
            text="Fault Geometry Map",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=12, pady=6)

        # --- ZOOM CONTROL ---
        zoom_frame = ctk.CTkFrame(self.hdr_group, fg_color="transparent")
        zoom_frame.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(
            zoom_frame, text="Zoom Level:",
            font=(res.FONT_LABEL[0], 11)
        ).pack(side="left")

        self.zoom_var = ctk.DoubleVar(value=0.6)
        self.zoom_slider = ctk.CTkSlider(
            zoom_frame,
            from_=0.1, to=2.0,
            variable=self.zoom_var,
            command=self.update_map_externally
        )
        self.zoom_slider.pack(side="left", fill="x", expand=True, padx=10)

        # --- MAP LAYER TOGGLES ---
        toggle_frame = ctk.CTkFrame(
            self.hdr_group, fg_color="#1a1a1a",
            border_width=1, border_color="#333333",
            corner_radius=6
        )
        toggle_frame.pack(fill="x", padx=15, pady=(0, 8))

        # Terrain/Basin default ON per Jorge's request — still toggleable
        # via the checkboxes below. Note: both layers are hand-drawn
        # California coastline/LABasin500 polygons (same as
        # StationPanel), so they should be switched off manually for
        # non-California geometries such as Charlevoix.
        self._show_basin_boundary = ctk.BooleanVar(value=True)
        self._show_fault_trace    = ctk.BooleanVar(value=True)
        self._show_terrain        = ctk.BooleanVar(value=True)
        self._show_legend         = ctk.BooleanVar(value=True)

        toggle_defs = [
            ("Terrain (LA Basin only)", self._show_terrain,        True),
            ("LA Basin Boundary",       self._show_basin_boundary, False),
            ("Fault Trace",             self._show_fault_trace,    False),
            ("Legend",                  self._show_legend,         False),
        ]

        def _make_toggle_cmd(is_terrain):
            def cmd():
                if is_terrain:
                    self._tile_img    = None
                    self._tile_extent = None
                self.update_map_externally()
            return cmd

        for label, var, is_terrain in toggle_defs:
            ctk.CTkCheckBox(
                toggle_frame,
                text=label,
                variable=var,
                font=(res.FONT_LABEL[0], 10),
                height=24,
                checkbox_width=16,
                checkbox_height=16,
                command=_make_toggle_cmd(is_terrain)
            ).pack(side="left", padx=6, pady=4)

        # --- MAP AREA ---
        self.map_group = ctk.CTkFrame(
            self, fg_color="#111111", border_width=1, border_color="#444",
            height=460
        )
        self.map_group.pack(fill="both", expand=True)
        self.map_group.pack_propagate(False)

        # --- CLICK INFO BAR ---
        self.click_info_frame = ctk.CTkFrame(
            self.map_group, fg_color="#1a1a2e", corner_radius=0, height=28
        )
        self.click_info_frame.pack(fill="x", side="bottom")
        self.click_info_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.click_info_frame, text=">>", font=("Arial", 12)
        ).pack(side="left", padx=(8, 2), pady=4)

        self.lbl_click_info = ctk.CTkLabel(
            self.click_info_frame,
            text="Click on the map to inspect a location",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray",
            anchor="w"
        )
        self.lbl_click_info.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=4)

        plt.style.use("dark_background")
        self.fig, self.ax = plt.subplots(figsize=(6, 5), facecolor="#111111")
        self.ax.set_facecolor("#1a1a1a")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_group)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.canvas.mpl_connect("button_press_event", self._on_map_click)

    # ------------------------------------------------------------------
    # MAP CLICK HANDLER — coordinates only, no station lookup (there
    # are no stations in this panel).
    # ------------------------------------------------------------------
    def _on_map_click(self, event):
        if event.inaxes != self.ax:
            self.lbl_click_info.configure(
                text="Click inside the map area to inspect a location.",
                text_color="gray"
            )
            return

        click_lon, click_lat = event.xdata, event.ydata
        if click_lon is None or click_lat is None:
            return

        if self._show_basin_boundary.get() and self.is_inside_basin(click_lon, click_lat):
            self.lbl_click_info.configure(
                text=f"Lat: {click_lat:.5f}   |   Lon: {click_lon:.5f}   |   inside LABasin500 extent",
                text_color=res.COLOR_SUCCESS
            )
        else:
            self.lbl_click_info.configure(
                text=f"Lat: {click_lat:.5f}   |   Lon: {click_lon:.5f}",
                text_color="#aaaaaa"
            )

    # ------------------------------------------------------------------
    # TERRAIN — identical to StationPanel._draw_terrain. Hand-drawn
    # California coastline; only meaningful when the fault is in the
    # LA Basin region. Off by default here (see class docstring).
    # ------------------------------------------------------------------
    def _draw_terrain(self, lon_min, lon_max, lat_min, lat_max):
        self.ax.set_facecolor("#2d8fa0")

        shallow_lons = [
            -120.50, -119.69, -119.30, -119.20, -119.06,
            -118.85, -118.72, -118.55, -118.50, -118.46,
            -118.42, -118.40, -118.43, -118.42, -118.30,
            -118.22, -118.07, -117.97, -117.93, -117.80,
            -117.63, -116.50, -116.50, -120.50
        ]
        shallow_lats = [
            34.70, 34.55, 34.40, 34.27, 34.23,
            34.15, 34.15, 34.14, 34.12, 34.09,
            34.03, 33.85, 33.80, 33.74, 33.61,
            33.63, 33.64, 33.56, 33.53, 33.44,
            33.33, 33.20, 36.00, 36.00
        ]
        self.ax.fill(shallow_lons, shallow_lats, color="#3daabb", alpha=0.5, zorder=1)

        land_lons = [
            -120.50, -119.69, -119.30, -119.20,
            -119.06, -118.85, -118.72,
            -118.55, -118.50, -118.46,
            -118.42, -118.40, -118.43,
            -118.42,
            -118.30, -118.22, -118.07,
            -117.97, -117.93, -117.80, -117.63,
            -116.50, -116.50,
            -120.50, -120.50
        ]
        land_lats = [
            34.50, 34.42, 34.28, 34.15,
            34.11, 34.03, 34.04,
            34.03, 34.01, 33.98,
            33.92, 33.85, 33.80,
            33.74,
            33.71, 33.73, 33.74,
            33.66, 33.63, 33.54, 33.43,
            33.00, 36.00,
            36.00, 34.50
        ]
        self.ax.fill(land_lons, land_lats, color="#5a8a45", alpha=1.0, zorder=2)

        coast_lons = [
            -120.50, -119.69, -119.30, -119.20, -119.06,
            -118.85, -118.72, -118.55, -118.50, -118.46,
            -118.42, -118.40, -118.43, -118.42,
            -118.30, -118.22, -118.07,
            -117.97, -117.93, -117.80, -117.63
        ]
        coast_lats = [
            34.50, 34.42, 34.28, 34.15, 34.11,
            34.03, 34.04, 34.03, 34.01, 33.98,
            33.92, 33.85, 33.80, 33.74,
            33.71, 33.73, 33.74,
            33.66, 33.63, 33.54, 33.43
        ]
        self.ax.plot(coast_lons, coast_lats, color="#1a6070", linewidth=0.8,
                     alpha=0.9, zorder=5, solid_capstyle="round")

        for lons, lats in [
            ([-120.47, -120.35, -120.28, -120.25, -120.35, -120.47],
             [34.07,   34.07,   34.03,   34.01,   33.99,   34.07]),
            ([-120.15, -119.99, -119.95, -120.00, -120.10, -120.15],
             [34.02,   34.02,   33.95,   33.87,   33.90,   34.02]),
            ([-119.92, -119.70, -119.55, -119.51, -119.60, -119.80, -119.92],
             [34.10,   34.08,   34.05,   33.97,   33.88,   33.90,   34.10]),
            ([-119.43, -119.37, -119.35, -119.41, -119.43],
             [34.02,   34.01,   33.99,   33.99,   34.02]),
            ([-118.63, -118.55, -118.42, -118.30, -118.27, -118.35, -118.50, -118.60, -118.63],
             [33.48,   33.50,   33.50,   33.40,   33.33,   33.30,   33.32,   33.38,   33.48]),
            ([-118.62, -118.45, -118.35, -118.43, -118.58, -118.62],
             [33.05,   33.00,   32.82,   32.79,   32.88,   33.05]),
            ([-119.05, -119.01, -119.02, -119.06, -119.05],
             [33.50,   33.48,   33.44,   33.45,   33.50]),
        ]:
            self.ax.fill(lons, lats, color="#5a8a45", zorder=3)

    # ------------------------------------------------------------------
    # EXTERNAL TRIGGER
    # ------------------------------------------------------------------
    def update_map_externally(self, *args):
        """Called by zoom slider / toggles to ask the parent to redraw."""
        if self.update_callback:
            try:
                self.update_callback()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # MAP REDRAW — fault trace + hypocenter only, no stations.
    # ------------------------------------------------------------------
    def redraw(self, fault_params):
        """
        Redraws the fault trace and hypocenter.

        Args:
            fault_params (dict): lat_top, lon_top, strike, fault_len,
                                  fault_wid, dip, depth_top, hypo_stk,
                                  hypo_dip — same shape StationPanel
                                  expects, so RuptureGeneratorPanel can
                                  build it once and hand it to either.
        """
        if not self.winfo_exists():
            return

        lat_top   = fault_params["lat_top"]
        lon_top   = fault_params["lon_top"]
        strike    = fault_params["strike"]
        fault_len = fault_params["fault_len"]
        dip       = fault_params["dip"]
        hypo_stk  = fault_params["hypo_stk"]
        hypo_dip  = fault_params["hypo_dip"]

        try:
            km_per_lat = 111.32
            km_per_lon = 40075 * math.cos(math.radians(lat_top)) / 360

            strike_rad = math.radians(strike)
            dip_rad    = math.radians(dip)

            # --- FAULT TRACE (surface projection along strike) ---
            half_len = fault_len / 2.0
            trace_start_lon = lon_top - (half_len * math.sin(strike_rad)) / km_per_lon
            trace_start_lat = lat_top - (half_len * math.cos(strike_rad)) / km_per_lat
            trace_end_lon   = lon_top + (half_len * math.sin(strike_rad)) / km_per_lon
            trace_end_lat   = lat_top + (half_len * math.cos(strike_rad)) / km_per_lat

            # --- HYPOCENTER (surface projection) ---
            hypo_lon = lon_top + (hypo_stk * math.sin(strike_rad)) / km_per_lon
            hypo_lat = lat_top + (hypo_stk * math.cos(strike_rad)) / km_per_lat
            dip_surface_km = hypo_dip * math.cos(dip_rad)
            dip_dir_rad = strike_rad + math.pi / 2
            hypo_lon += (dip_surface_km * math.sin(dip_dir_rad)) / km_per_lon
            hypo_lat += (dip_surface_km * math.cos(dip_dir_rad)) / km_per_lat

            # --- DRAW ---
            self.ax.clear()
            self.ax.set_facecolor("#2a6070")

            aspect = 1.0 / math.cos(math.radians(lat_top))
            self.ax.set_aspect(aspect)
            zoom     = self.zoom_var.get()
            lat_zoom = zoom * (1.0 / aspect)
            lon_min, lon_max = lon_top - zoom,     lon_top + zoom
            lat_min, lat_max = lat_top - lat_zoom, lat_top + lat_zoom
            self.ax.set_xlim(lon_min, lon_max)
            self.ax.set_ylim(lat_min, lat_max)

            if self._show_terrain.get():
                self._draw_terrain(lon_min, lon_max, lat_min, lat_max)

            if self._show_basin_boundary.get():
                la_basin_lons = self.LABASIN500_BOUNDARY_LONS
                la_basin_lats = self.LABASIN500_BOUNDARY_LATS
                self.ax.plot(
                    la_basin_lons + [la_basin_lons[0]],
                    la_basin_lats + [la_basin_lats[0]],
                    color="#44ee88", linewidth=1.0,
                    linestyle="--", alpha=0.7, zorder=4,
                    label="LABasin500 Model Extent"
                )

            if self._show_fault_trace.get():
                self.ax.plot(
                    [trace_start_lon, trace_end_lon],
                    [trace_start_lat, trace_end_lat],
                    color="white", linewidth=2.0,
                    zorder=13, label="Fault Trace"
                )
                self.ax.scatter(
                    [lon_top], [lat_top],
                    color="white", marker="s", s=40,
                    edgecolors="#aaaaaa", zorder=14,
                    label="Fault Top Center"
                )

            self.ax.scatter(
                [hypo_lon], [hypo_lat],
                color="#ff4b4b", marker="*", s=280,
                edgecolors="white", linewidths=0.8,
                zorder=15, label="Hypocenter"
            )

            if self._show_legend.get():
                self.ax.legend(
                    loc="upper right",
                    facecolor="#111111", edgecolor="#444",
                    prop={"size": 8}
                )
            else:
                self.ax.legend().set_visible(False)

            self.ax.set_title("Fault Geometry Preview", color="white", size=10)
            self.ax.set_xlabel("Longitude (°)", color="gray", fontsize=9)
            self.ax.set_ylabel("Latitude (°)",  color="gray", fontsize=9)
            self.ax.tick_params(colors="gray", labelsize=8)

            self.fig.tight_layout()
            self.canvas.draw()

        except Exception as e:
            print(f"[FaultMapPanel] redraw error: {e}")

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------
    def destroy(self):
        plt.close(self.fig)
        super().destroy()