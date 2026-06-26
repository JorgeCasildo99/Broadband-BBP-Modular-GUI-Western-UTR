import customtkinter as ctk
import os
import sys
import math
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.path import Path as MplPath

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.ChinoHillsResources import get_station_coords, get_station_full


class StationPanel(ctk.CTkFrame):

    # LABasin500 model extent polygon — same coordinates used for the
    # green dashed boundary line drawn in redraw(). Kept as a class
    # constant so the plotting code and the containment check (used for
    # the outside-boundary warning) always agree on the exact same shape.
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
        """
        Returns True if (lon, lat) falls inside the LABasin500 model
        extent polygon, False otherwise.

        Stations placed outside this polygon are not guaranteed to have
        valid Green's Functions for the GP method — BBP does not raise
        an error for this, it silently clips to the nearest available
        Green's Function entry, which can silently produce inaccurate
        results. This check exists purely to warn the user up front.
        """
        boundary_path = MplPath(
            list(zip(cls.LABASIN500_BOUNDARY_LONS, cls.LABASIN500_BOUNDARY_LATS))
        )
        return bool(boundary_path.contains_point((lon, lat)))

    def __init__(self, master, update_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._last_stations   = []
        self._show_real       = False
        self.update_callback  = update_callback

        # Tile cache — avoids re-fetching from internet on every redraw
        self._tile_img         = None   # cached tile image (numpy array)
        self._tile_extent      = None   # (lon_min, lon_max, lat_min, lat_max)
        self._tile_source_name = None   # track which provider is cached

        # --- HEADER & COUNTER ---
        self.stl_group = ctk.CTkFrame(self, fg_color="#252525")
        self.stl_group.pack(fill="x", pady=(0, 8))

        self.header_frame = ctk.CTkFrame(self.stl_group, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(
            self.header_frame,
            text="Station List Map",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(side="left")

        self.lbl_counter = ctk.CTkLabel(
            self.header_frame,
            text="STATIONS: 0",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        )
        self.lbl_counter.pack(side="right", padx=10)

        # --- ZOOM CONTROL ---
        self.zoom_frame = ctk.CTkFrame(self.stl_group, fg_color="transparent")
        self.zoom_frame.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkLabel(
            self.zoom_frame,
            text="Zoom Level:",
            font=(res.FONT_LABEL[0], 11)
        ).pack(side="left")

        self.zoom_var = ctk.DoubleVar(value=0.6)
        self.zoom_slider = ctk.CTkSlider(
            self.zoom_frame,
            from_=0.1, to=2.0,
            variable=self.zoom_var,
            command=self.update_map_externally
        )
        self.zoom_slider.pack(side="left", fill="x", expand=True, padx=10)

        # --- RANGE SELECTOR (renamed) ---
        ctk.CTkLabel(
            self.stl_group,
            text="Range & Density:",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(6, 0))

        self.station_mode = ctk.StringVar(value="Medium Range")
        self.seg_range = ctk.CTkSegmentedButton(
            self.stl_group,
            values=["Small Range", "Medium Range", "Wide Range"],
            variable=self.station_mode,
            command=self._on_range_changed
        )
        self.seg_range.pack(pady=(4, 8), padx=15, fill="x")

        # --- STATION COUNT INPUT ---
        count_frame = ctk.CTkFrame(self.stl_group, fg_color="transparent")
        count_frame.pack(fill="x", padx=15, pady=(0, 6))

        ctk.CTkLabel(
            count_frame,
            text="Number of Stations:",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="left")

        self._station_count_var = ctk.StringVar(value="50")
        self._station_count_entry = ctk.CTkEntry(
            count_frame,
            textvariable=self._station_count_var,
            width=70, height=28,
            font=(res.FONT_LABEL[0], 12),
            justify="center"
        )
        self._station_count_entry.pack(side="left", padx=(10, 6))
        self._station_count_entry.bind("<Return>",   lambda e: self.update_map_externally())
        self._station_count_entry.bind("<FocusOut>", lambda e: self.update_map_externally())

        ctk.CTkLabel(
            count_frame,
            text="(press Enter to apply)",
            font=(res.FONT_LABEL[0], 9),
            text_color="#555555"
        ).pack(side="left")
        ctk.CTkLabel(
            self.stl_group,
            text="Station Distribution Pattern:",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(4, 0))

        self.distribution_mode = ctk.StringVar(value="Random Distribution")

        btn_frame = ctk.CTkFrame(self.stl_group, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(4, 10))
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.dist_buttons = {}
        patterns = ["Horizontal Distribution", "Vertical Distribution", "Random Distribution"]

        for i, pattern in enumerate(patterns):
            btn = ctk.CTkButton(
                btn_frame,
                text=pattern,
                height=30,
                corner_radius=6,
                fg_color=res.COLOR_PRIMARY if pattern == "Random Distribution" else "#333333",
                hover_color="#004070",
                font=(res.FONT_LABEL[0], 11),
                command=lambda p=pattern: self._select_distribution(p)
            )
            btn.grid(row=0, column=i, padx=3, sticky="ew")
            self.dist_buttons[pattern] = btn

        # --- MAP LAYER TOGGLES ---
        toggle_frame = ctk.CTkFrame(
            self.stl_group, fg_color="#1a1a1a",
            border_width=1, border_color="#333333",
            corner_radius=6
        )
        toggle_frame.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(
            toggle_frame,
            text="Map Layers:",
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color="gray"
        ).pack(side="left", padx=(10, 8), pady=4)

        # Layer toggle variables
        self._show_basin_boundary  = ctk.BooleanVar(value=True)
        self._show_station_boundary= ctk.BooleanVar(value=True)
        self._show_fault_trace     = ctk.BooleanVar(value=True)
        self._show_terrain         = ctk.BooleanVar(value=True)
        self._show_legend          = ctk.BooleanVar(value=True)

        toggle_defs = [
            ("Terrain",     self._show_terrain),
            ("Basin",       self._show_basin_boundary),
            ("Boundary",    self._show_station_boundary),
            ("Fault Trace", self._show_fault_trace),
            ("Legend",      self._show_legend),
        ]

        def _make_toggle_cmd(var, is_terrain=False):
            def cmd():
                if is_terrain:
                    # Clear tile cache so new toggle state fetches fresh
                    self._tile_img    = None
                    self._tile_extent = None
                self.update_map_externally()
            return cmd

        for label, var in toggle_defs:
            is_t = (label == "Terrain")
            ctk.CTkCheckBox(
                toggle_frame,
                text=label,
                variable=var,
                font=(res.FONT_LABEL[0], 10),
                height=24,
                checkbox_width=16,
                checkbox_height=16,
                command=_make_toggle_cmd(var, is_terrain=is_t)
            ).pack(side="left", padx=6, pady=4)

        # --- MAP AREA ---
        self.map_group = ctk.CTkFrame(
            self, fg_color="#111111", border_width=1, border_color="#444",
            height=520
        )
        self.map_group.pack(fill="both", expand=True)
        self.map_group.pack_propagate(False)

        # --- CLICK INFO BAR — outside map_group, always visible ---
        self.click_info_frame = ctk.CTkFrame(
            self.map_group, fg_color="#1a1a2e", corner_radius=0, height=28
        )
        self.click_info_frame.pack(fill="x", side="bottom")
        self.click_info_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.click_info_frame,
            text=">>",
            font=("Arial", 12)
        ).pack(side="left", padx=(8, 2), pady=4)

        self.lbl_click_info = ctk.CTkLabel(
            self.click_info_frame,
            text="Click on the map to inspect a location or station",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray",
            anchor="w"
        )
        self.lbl_click_info.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=4)

        plt.style.use("dark_background")
        self.fig, self.ax = plt.subplots(figsize=(6, 5), facecolor="#111111")
        self.ax.set_facecolor("#1a1a1a")

        # Stores the current highlight scatter so it can be removed on next click
        self._highlight_scatter = None

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_group)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(8, 0))

        # Connect matplotlib click event
        self.canvas.mpl_connect("button_press_event", self._on_map_click)

    # ------------------------------------------------------------------
    # DISTRIBUTION BUTTON SELECTION
    # ------------------------------------------------------------------

    def _select_distribution(self, pattern):
        """
        Highlights the selected distribution button and triggers a map redraw.
        Only one distribution pattern can be active at a time.
        """
        self.distribution_mode.set(pattern)
        for name, btn in self.dist_buttons.items():
            btn.configure(fg_color=res.COLOR_PRIMARY if name == pattern else "#333333")
        self.update_map_externally()

    def _on_range_changed(self, *args):
        """
        Called when the range selector changes.
        Updates the station count entry with the default for that range,
        but only if the user hasn't manually edited it.
        """
        mode = self.station_mode.get()
        defaults = {
            "Small Range"  : "20",
            "Medium Range" : "50",
            "Wide Range"   : "100",
        }
        self._station_count_var.set(defaults.get(mode, "50"))
        self.update_map_externally()

    def _get_station_count(self):
        """
        Reads the station count from the input box.
        Clamps between 1 and 500. Falls back to range default if invalid.
        """
        mode = self.station_mode.get()
        defaults = {
            "Small Range"  : 20,
            "Medium Range" : 50,
            "Wide Range"   : 100,
        }
        try:
            n = int(self._station_count_var.get())
            n = max(0, min(500, n))
            self._station_count_var.set(str(n))
            return n
        except (ValueError, AttributeError):
            return defaults.get(mode, 50)

    # ------------------------------------------------------------------
    # MAP CLICK HANDLER
    # ------------------------------------------------------------------

    def _on_map_click(self, event):
        """
        Fires when the user clicks anywhere on the matplotlib canvas.
        - Always shows the clicked lat/lon coordinates.
        - If the click is close enough to a known station, also shows
          its station ID and highlights it on the map.
        Proximity threshold is 2% of the current axis range.
        """
        # Ignore clicks outside the axes area
        if event.inaxes != self.ax:
            self.lbl_click_info.configure(
                text="Click inside the map area to inspect a location.",
                text_color="gray"
            )
            return

        click_lon = event.xdata
        click_lat = event.ydata

        if click_lon is None or click_lat is None:
            return

        # Compute proximity threshold based on current zoom level
        x_range = self.ax.get_xlim()
        y_range = self.ax.get_ylim()
        threshold_lon = (x_range[1] - x_range[0]) * 0.02
        threshold_lat = (y_range[1] - y_range[0]) * 0.02

        # Check if click is near any known station
        nearest_station = None
        nearest_dist    = float("inf")

        # Check generated/manual stations
        for s_lon, s_lat, s_id in self._last_stations:
            dist = math.sqrt((click_lon - s_lon)**2 + (click_lat - s_lat)**2)
            if dist < nearest_dist:
                nearest_dist    = dist
                nearest_station = (s_lon, s_lat, s_id, "generated")

        # Also check real stations if visible
        if self._show_real:
            for s_lon, s_lat, s_id in get_station_coords():
                dist = math.sqrt((click_lon - s_lon)**2 + (click_lat - s_lat)**2)
                if dist < nearest_dist:
                    nearest_dist    = dist
                    nearest_station = (s_lon, s_lat, s_id, "real")

        if nearest_station and nearest_dist < max(threshold_lon, threshold_lat):
            s_lon, s_lat, s_id, s_type = nearest_station

            if s_type == "real":
                full = get_station_full(s_id)
                vs30_text = f"  |  Vs30: {full['vs30']} m/s  |  HP/LP: {full['hp_freq']}/{full['lp_freq']} Hz" if full else ""
                self.lbl_click_info.configure(
                    text=f"Real Station: {s_id}   |   Lat: {s_lat:.5f}   |   Lon: {s_lon:.5f}{vs30_text}",
                    text_color="orange"
                )
            else:
                if self.is_inside_basin(s_lon, s_lat):
                    self.lbl_click_info.configure(
                        text=f"Station: {s_id}   |   Lat: {s_lat:.5f}°   |   Lon: {s_lon:.5f}°",
                        text_color=res.COLOR_SUCCESS
                    )
                else:
                    self.lbl_click_info.configure(
                        text=(
                            f"⚠ Station: {s_id}   |   Lat: {s_lat:.5f}°   |   Lon: {s_lon:.5f}°   "
                            f"—   outside LABasin500, Green's Functions are not reliable here"
                        ),
                        text_color="#ff6666"
                    )

            # Remove previous highlight before drawing a new one
            if self._highlight_scatter is not None:
                try:
                    self._highlight_scatter.remove()
                except:
                    pass
            highlight_color = "orange" if s_type == "real" else res.COLOR_SUCCESS
            self._highlight_scatter = self.ax.scatter(
                [s_lon], [s_lat],
                s=120, facecolors="none",
                edgecolors=highlight_color,
                linewidths=2, zorder=20
            )
            self.canvas.draw()
        else:
            # No station nearby — show raw coordinates of the clicked point,
            # plus a warning if the point falls outside the LABasin500 extent
            if self.is_inside_basin(click_lon, click_lat):
                self.lbl_click_info.configure(
                    text=f"Empty Location   |   Lat: {click_lat:.5f}   |   Lon: {click_lon:.5f}",
                    text_color="#aaaaaa"
                )
            else:
                self.lbl_click_info.configure(
                    text=(
                        f"⚠ Outside LABasin500 boundary   |   Lat: {click_lat:.5f}   |   "
                        f"Lon: {click_lon:.5f}   —   a station here will not have reliable "
                        f"Green's Functions"
                    ),
                    text_color="#ff6666"
                )
            # Remove any existing highlight since no station was selected
            if self._highlight_scatter is not None:
                try:
                    self._highlight_scatter.remove()
                    self._highlight_scatter = None
                    self.canvas.draw()
                except:
                    pass

    # ------------------------------------------------------------------
    # TERRAIN TILE CACHING
    # ------------------------------------------------------------------

    def _draw_terrain(self, lon_min, lon_max, lat_min, lat_max):
        """
        Fast polygon-based map background.
        Accurate LA Basin coastline — no elevation, no tiles, instant rendering.
        Colors match the reference image: teal ocean, green land.
        """

        # --- OCEAN (teal, like the reference image) ---
        self.ax.set_facecolor("#2d8fa0")

        # Shallow coastal water — slightly lighter teal band
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
        self.ax.fill(
            shallow_lons, shallow_lats,
            color="#3daabb", alpha=0.5, zorder=1
        )

        # --- MAINLAND LAND POLYGON ---
        # Traced carefully point-by-point along real coast then closed inland
        land_lons = [
            # Ventura coast going SE
            -120.50, -119.69, -119.30, -119.20,
            # Point Mugu to Malibu
            -119.06, -118.85, -118.72,
            # Santa Monica Bay arc
            -118.55, -118.50, -118.46,
            # Down Palos Verdes west side
            -118.42, -118.40, -118.43,
            # Palos Verdes tip (south)
            -118.42,
            # San Pedro and Long Beach
            -118.30, -118.22, -118.07,
            # Newport to Laguna to San Clemente
            -117.97, -117.93, -117.80, -117.63,
            # Close polygon inland
            -116.50, -116.50,
            # Top edge back to start
            -120.50, -120.50
        ]
        land_lats = [
            # Ventura
            34.50, 34.42, 34.28, 34.15,
            # Point Mugu to Malibu
            34.11, 34.03, 34.04,
            # Santa Monica Bay
            34.03, 34.01, 33.98,
            # Palos Verdes west
            33.92, 33.85, 33.80,
            # PV tip
            33.74,
            # San Pedro, Long Beach
            33.71, 33.73, 33.74,
            # Newport to San Clemente
            33.66, 33.63, 33.54, 33.43,
            # inland
            33.00, 36.00,
            # top
            36.00, 34.50
        ]
        self.ax.fill(
            land_lons, land_lats,
            color="#5a8a45", alpha=1.0, zorder=2
        )

        # --- COASTLINE ---
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
        self.ax.plot(
            coast_lons, coast_lats,
            color="#1a6070", linewidth=0.8,
            alpha=0.9, zorder=5, solid_capstyle="round"
        )

        # --- CHANNEL ISLANDS (accurate positions & shapes) ---
        # San Miguel Island
        self.ax.fill(
            [-120.47, -120.35, -120.28, -120.25, -120.35, -120.47],
            [34.07,   34.07,   34.03,   34.01,   33.99,   34.07],
            color="#5a8a45", zorder=3
        )
        # Santa Rosa Island
        self.ax.fill(
            [-120.15, -119.99, -119.95, -120.00, -120.10, -120.15],
            [34.02,   34.02,   33.95,   33.87,   33.90,   34.02],
            color="#5a8a45", zorder=3
        )
        # Santa Cruz Island (largest)
        self.ax.fill(
            [-119.92, -119.70, -119.55, -119.51, -119.60,
             -119.80, -119.92],
            [34.10,   34.08,   34.05,   33.97,   33.88,
             33.90,   34.10],
            color="#5a8a45", zorder=3
        )
        # Anacapa Island (small)
        self.ax.fill(
            [-119.43, -119.37, -119.35, -119.41, -119.43],
            [34.02,   34.01,   33.99,   33.99,   34.02],
            color="#5a8a45", zorder=3
        )
        # Santa Catalina Island
        self.ax.fill(
            [-118.63, -118.55, -118.42, -118.30, -118.27,
             -118.35, -118.50, -118.60, -118.63],
            [33.48,   33.50,   33.50,   33.40,   33.33,
             33.30,   33.32,   33.38,   33.48],
            color="#5a8a45", zorder=3
        )
        # San Clemente Island
        self.ax.fill(
            [-118.62, -118.45, -118.35, -118.43, -118.58, -118.62],
            [33.05,   33.00,   32.82,   32.79,   32.88,   33.05],
            color="#5a8a45", zorder=3
        )
        # Santa Barbara Island (small)
        self.ax.fill(
            [-119.05, -119.01, -119.02, -119.06, -119.05],
            [33.50,   33.48,   33.44,   33.45,   33.50],
            color="#5a8a45", zorder=3
        )

    # ------------------------------------------------------------------
    # STATION DISTRIBUTION ALGORITHMS
    # ------------------------------------------------------------------

    def _generate_horizontal(self, lat_c, lon_c, radius_km, count, km_per_lat, km_per_lon):
        """
        Distributes stations in evenly spaced horizontal lines across
        the circular boundary area, maximizing east-west coverage.
        Lines are spaced vertically to fill the full diameter.
        Stations along each line are evenly spaced within the chord.
        """
        stations = []
        # Number of horizontal lines — sqrt gives balanced line/station ratio
        n_lines = max(3, int(math.sqrt(count)))
        # Evenly space lines from bottom to top of the circle
        lat_offsets_km = [
            -radius_km + (2 * radius_km / (n_lines + 1)) * (i + 1)
            for i in range(n_lines)
        ]

        idx = 0
        for line_offset_km in lat_offsets_km:
            # Calculate chord width at this latitude offset
            chord_half_km = math.sqrt(max(0, radius_km**2 - line_offset_km**2))
            if chord_half_km < 0.5:
                continue

            # Stations per line proportional to chord length
            n_on_line = max(2, int(round(count / n_lines)))
            for j in range(n_on_line):
                # Evenly space across the chord
                frac   = -1.0 + (2.0 / (n_on_line + 1)) * (j + 1)
                s_lon  = lon_c + (frac * chord_half_km / km_per_lon)
                s_lat  = lat_c + (line_offset_km / km_per_lat)
                stations.append((s_lon, s_lat, f"SH_{idx:03d}"))
                idx += 1

            if idx >= count:
                break

        return stations[:count]

    def _generate_vertical(self, lat_c, lon_c, radius_km, count, km_per_lat, km_per_lon):
        """
        Distributes stations in evenly spaced vertical lines across
        the circular boundary area, maximizing north-south coverage.
        Lines are spaced horizontally to fill the full diameter.
        Stations along each line are evenly spaced within the chord.
        """
        stations = []
        n_lines = max(3, int(math.sqrt(count)))
        # Evenly space lines from left to right of the circle
        lon_offsets_km = [
            -radius_km + (2 * radius_km / (n_lines + 1)) * (i + 1)
            for i in range(n_lines)
        ]

        idx = 0
        for line_offset_km in lon_offsets_km:
            chord_half_km = math.sqrt(max(0, radius_km**2 - line_offset_km**2))
            if chord_half_km < 0.5:
                continue

            n_on_line = max(2, int(round(count / n_lines)))
            for j in range(n_on_line):
                frac   = -1.0 + (2.0 / (n_on_line + 1)) * (j + 1)
                s_lat  = lat_c + (frac * chord_half_km / km_per_lat)
                s_lon  = lon_c + (line_offset_km / km_per_lon)
                stations.append((s_lon, s_lat, f"SV_{idx:03d}"))
                idx += 1

            if idx >= count:
                break

        return stations[:count]

    def _generate_random(self, lat_c, lon_c, radius_km, count, km_per_lat, km_per_lon):
        """
        Distributes stations randomly but uniformly across the full circular
        boundary area using rejection-free polar sampling. sqrt(r) ensures
        uniform density — without it stations cluster near the center.
        Fixed seed guarantees reproducibility across sessions.
        """
        stations = []
        random.seed(42)
        for i in range(count):
            # Uniform sampling in polar coordinates
            r = radius_km * math.sqrt(random.random())
            t = random.random() * 2 * math.pi
            s_lat = lat_c + (r * math.sin(t) / km_per_lat)
            s_lon = lon_c + (r * math.cos(t) / km_per_lon)
            stations.append((s_lon, s_lat, f"SR_{idx:03d}".replace("idx", str(i)))
                            if False else (s_lon, s_lat, f"SR_{i:03d}"))
        return stations

    def toggle_real_stations(self):
        """
        Toggles the real Chino Hills station layer on/off.
        Called by the button in RupturePanel.
        Returns the new state (True = visible).
        """
        self._show_real = not self._show_real
        self.update_map_externally()
        return self._show_real

    # ------------------------------------------------------------------
    # EXTERNAL TRIGGER
    # ------------------------------------------------------------------

    def update_map_externally(self, *args):
        """Called by zoom slider and range selector to trigger a parent redraw."""
        if self.update_callback:
            try:
                self.update_callback()
            except:
                pass

    # ------------------------------------------------------------------
    # STATION ACCESS
    # ------------------------------------------------------------------

    def get_stations(self):
        """
        Returns the last computed station list without redrawing the map.
        Called by RupturePanel.generate_files() to build the .stl content.
        """
        return list(self._last_stations)

    # ------------------------------------------------------------------
    # MAP REDRAW
    # ------------------------------------------------------------------

    def redraw(self, fault_params, manual_stations=None):
        """
        Redraws the station network map with fault trace and real hypocenter.

        Args:
            fault_params    (dict): Full fault geometry from RupturePanel containing:
                                    lat_top, lon_top, strike, fault_len, fault_wid,
                                    dip, depth_top, hypo_stk, hypo_dip
            manual_stations (list): List of (lon, lat, name) manual stations.

        Returns:
            list of tuples: [(lon, lat, station_id), ...]
        """
        if not self.winfo_exists():
            return []

        manual_stations = manual_stations or []

        # Unpack fault geometry
        lat_top   = fault_params["lat_top"]
        lon_top   = fault_params["lon_top"]
        strike    = fault_params["strike"]
        fault_len = fault_params["fault_len"]
        fault_wid = fault_params["fault_wid"]
        dip       = fault_params["dip"]
        depth_top = fault_params["depth_top"]
        hypo_stk  = fault_params["hypo_stk"]
        hypo_dip  = fault_params["hypo_dip"]

        try:
            # --- RANGE SETTINGS ---
            mode = self.station_mode.get()
            if mode == "Small Range":
                radius_km = 15.0
            elif mode == "Medium Range":
                radius_km = 35.0
            else:
                radius_km = 65.0

            # Use user-defined count from input box
            count = self._get_station_count()

            km_per_lat = 111.32
            km_per_lon = 40075 * math.cos(math.radians(lat_top)) / 360

            # ------------------------------------------------------------------
            # FAULT GEOMETRY CALCULATIONS
            # ------------------------------------------------------------------

            strike_rad = math.radians(strike)
            dip_rad    = math.radians(dip)

            # --- FAULT TRACE (surface projection along strike) ---
            # Half length in each direction from top center along strike
            half_len = fault_len / 2.0
            trace_start_lon = lon_top - (half_len * math.sin(strike_rad)) / km_per_lon
            trace_start_lat = lat_top - (half_len * math.cos(strike_rad)) / km_per_lat
            trace_end_lon   = lon_top + (half_len * math.sin(strike_rad)) / km_per_lon
            trace_end_lat   = lat_top + (half_len * math.cos(strike_rad)) / km_per_lat

            # --- REAL HYPOCENTER (surface projection) ---
            # Move along strike by hypo_stk from top center
            hypo_lon = lon_top + (hypo_stk * math.sin(strike_rad)) / km_per_lon
            hypo_lat = lat_top + (hypo_stk * math.cos(strike_rad)) / km_per_lat
            # Move along dip direction (projected to surface) by hypo_dip
            dip_surface_km = hypo_dip * math.cos(dip_rad)
            # Dip direction is 90 degrees clockwise from strike
            dip_dir_rad = strike_rad + math.pi / 2
            hypo_lon += (dip_surface_km * math.sin(dip_dir_rad)) / km_per_lon
            hypo_lat += (dip_surface_km * math.cos(dip_dir_rad)) / km_per_lat

            # --- GENERATE STATIONS BY DISTRIBUTION PATTERN ---
            pattern = self.distribution_mode.get()
            if pattern == "Horizontal Distribution":
                stations = self._generate_horizontal(lat_top, lon_top, radius_km, count, km_per_lat, km_per_lon)
            elif pattern == "Vertical Distribution":
                stations = self._generate_vertical(lat_top, lon_top, radius_km, count, km_per_lat, km_per_lon)
            else:
                stations = self._generate_random(lat_top, lon_top, radius_km, count, km_per_lat, km_per_lon)

            total = len(stations) + len(manual_stations)
            self.lbl_counter.configure(text=f"STATIONS: {total}")

            # --- DRAW ---
            self.ax.clear()
            self.ax.set_facecolor("#2a6070")
            self._highlight_scatter = None

            # Correct geographic aspect ratio
            aspect   = 1.0 / math.cos(math.radians(lat_top))
            self.ax.set_aspect(aspect)
            zoom     = self.zoom_var.get()
            lat_zoom = zoom * (1.0 / aspect)
            lon_min, lon_max = lon_top - zoom,     lon_top + zoom
            lat_min, lat_max = lat_top - lat_zoom, lat_top + lat_zoom
            self.ax.set_xlim(lon_min, lon_max)
            self.ax.set_ylim(lat_min, lat_max)

            # ------------------------------------------------------------------
            # TERRAIN BACKGROUND — cached real map tiles via contextily
            # Tiles are fetched ONCE for a large padded extent and cached
            # in memory. Subsequent redraws use imshow (instant, no network).
            # ------------------------------------------------------------------
            if self._show_terrain.get():
                self._draw_terrain(lon_min, lon_max, lat_min, lat_max)

            # ------------------------------------------------------------------
            # LA BASIN BOUNDARY (toggleable)
            # ------------------------------------------------------------------
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

            # Station network boundary circle (toggleable)
            if self._show_station_boundary.get():
                theta = [math.radians(i) for i in range(361)]
                bx = [lon_top + (radius_km * math.cos(t) / km_per_lon) for t in theta]
                by = [lat_top + (radius_km * math.sin(t) / km_per_lat) for t in theta]
                self.ax.plot(
                    bx, by,
                    color="#4da6ff", alpha=0.9, linewidth=1.5,
                    label=f"Station Boundary ({int(radius_km)} km)"
                )

            # --- FAULT TRACE (toggleable) ---
            if self._show_fault_trace.get():
                self.ax.plot(
                    [trace_start_lon, trace_end_lon],
                    [trace_start_lat, trace_end_lat],
                    color="white", linewidth=2.0,
                    zorder=13, label="Fault Trace"
                )
                # Fault top center marker
                self.ax.scatter(
                    [lon_top], [lat_top],
                    color="white", marker="s", s=40,
                    edgecolors="#aaaaaa", zorder=14,
                    label="Fault Top Center"
                )

            # Auto-generated stations — split by LABasin500 boundary
            # containment so stations outside the model extent are
            # immediately visible in red rather than blending in.
            if stations:
                in_lons,  in_lats  = [], []
                out_lons, out_lats = [], []
                for s_lon, s_lat, _s_id in stations:
                    if self.is_inside_basin(s_lon, s_lat):
                        in_lons.append(s_lon)
                        in_lats.append(s_lat)
                    else:
                        out_lons.append(s_lon)
                        out_lats.append(s_lat)

                if in_lons:
                    self.ax.scatter(
                        in_lons, in_lats,
                        color="#3b8ed0", s=25, alpha=0.7, zorder=5,
                        label="Synthetic Stations (BBP output points)"
                    )
                if out_lons:
                    self.ax.scatter(
                        out_lons, out_lats,
                        color="#ff3b3b", s=30, alpha=0.85, zorder=6,
                        edgecolors="#ffaaaa", linewidths=0.6,
                        label="Outside LABasin500 (unreliable GF)"
                    )

            # Manual stations — gold if inside the LABasin500 boundary,
            # red if outside (same warning color as auto-generated stations)
            for m_lon, m_lat, m_name in manual_stations:
                stations.append((m_lon, m_lat, m_name))
                is_inside = self.is_inside_basin(m_lon, m_lat)
                marker_color = "gold" if is_inside else "#ff3b3b"
                label_color  = "gold" if is_inside else "#ff6666"
                self.ax.scatter(
                    m_lon, m_lat,
                    color=marker_color, s=55, edgecolors="white", zorder=12
                )
                self.ax.annotate(
                    m_name if is_inside else f"{m_name} ⚠",
                    (m_lon, m_lat),
                    textcoords="offset points", xytext=(5, 5),
                    fontsize=7, color=label_color
                )

            # --- REAL STATIONS LAYER (Chino Hills) ---
            if self._show_real:
                real_stations = get_station_coords()
                r_lons = [s[0] for s in real_stations]
                r_lats = [s[1] for s in real_stations]
                self.ax.scatter(
                    r_lons, r_lats,
                    color="orange", marker="^", s=45,
                    edgecolors="white", linewidths=0.5,
                    zorder=11, alpha=0.9,
                    label="Real Stations (Chino Hills)"
                )

            # --- REAL HYPOCENTER ---
            self.ax.scatter(
                [hypo_lon], [hypo_lat],
                color="#ff4b4b", marker="*", s=280,
                edgecolors="white", linewidths=0.8,
                zorder=15, label="Hypocenter"
            )

            self.ax.legend(
                loc="upper right",
                facecolor="#111111",
                edgecolor="#444",
                prop={"size": 8}
            ) if self._show_legend.get() else self.ax.legend().set_visible(False)
            self.ax.set_title(
                f"{pattern} Pattern — {mode}  "
                f"(boundary radius: {int(radius_km)} km)",
                color="white", size=10
            )
            self.ax.set_xlabel("Longitude (°)", color="gray", fontsize=9)
            self.ax.set_ylabel("Latitude (°)",  color="gray", fontsize=9)
            self.ax.tick_params(colors="gray", labelsize=8)

            # Distance scale bar
            scale_km  = radius_km / 2
            scale_deg = scale_km / km_per_lon
            x0 = lon_top - zoom * 0.85
            y0 = lat_top - lat_zoom * 0.88
            self.ax.annotate(
                "", xy=(x0 + scale_deg, y0), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<->", color="#888888", lw=1.2)
            )
            self.ax.text(
                x0 + scale_deg / 2, y0 + lat_zoom * 0.035,
                f"{int(scale_km)} km",
                color="#888888", fontsize=7, ha="center"
            )

            self.fig.tight_layout()
            self.canvas.draw()

            self._last_stations = list(stations)
            return stations

        except Exception as e:
            print(f"[StationPanel] redraw error: {e}")
            return []

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------

    def destroy(self):
        """Properly closes the matplotlib figure before destroying the widget."""
        plt.close(self.fig)
        super().destroy()