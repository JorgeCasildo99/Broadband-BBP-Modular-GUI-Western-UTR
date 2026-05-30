# ChinoHillsPanel.py — ui/Rupture/ChinoHillsPanel.py

import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.ChinoHillsResources import CHINO_HILLS_SRC, CHINO_HILLS_META, CHINO_HILLS_STATIONS


class ChinoHillsPanel(ctk.CTkToplevel):
    """
    Read-only popup window showing the Chino Hills 2008 earthquake
    reference data used for Graves & Pitarka validation in BBP.
    """

    def __init__(self, master):
        super().__init__(master)

        self.title("Chino Hills 2008 - G&P Reference Event")
        self.geometry("860x720")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)

        # transient links this window to the parent without blocking it
        self.transient(master)

        # Build content first, then grab focus after window is visible
        self._build_ui()

        # Delay grab_set and render until window is fully drawn
        self.after(200, self._on_ready)

    def _on_ready(self):
        """Called after the window is fully visible and rendered."""
        try:
            self.grab_set()
        except Exception:
            pass
        self.lift()
        self.focus_force()
        self.update_idletasks()

    def _build_ui(self):

        # --- TITLE BAR ---
        title_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        ctk.CTkLabel(
            title_frame,
            text="Chino Hills 2008  -  Graves & Pitarka Validation Reference",
            font=(res.FONT_TITLE[0], 16, "bold"),
            text_color="white"
        ).pack(side="left", padx=20, pady=15)

        ctk.CTkLabel(
            title_frame,
            text="GP UPDATE: 2021  |  MOST RECENT",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color=res.COLOR_SUCCESS
        ).pack(side="right", padx=20)

        # --- SCROLLABLE CONTENT ---
        scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        # --- EVENT METADATA ---
        self._section_header(scroll, "Event Information")

        meta_frame = ctk.CTkFrame(
            scroll, fg_color="#222222", border_width=1, border_color="#444"
        )
        meta_frame.pack(fill="x", pady=(0, 12), padx=5)
        meta_frame.grid_columnconfigure((1, 3), weight=1)

        meta_fields = [
            ("Event",         CHINO_HILLS_META["event_name"]),
            ("Date",          CHINO_HILLS_META["date"]),
            ("Magnitude",     CHINO_HILLS_META["magnitude"]),
            ("Depth",         f"{CHINO_HILLS_META['depth_km']} km"),
            ("Epicenter Lat", f"{CHINO_HILLS_META['epicenter_lat']}°"),
            ("Epicenter Lon", f"{CHINO_HILLS_META['epicenter_lon']}°"),
            ("Region",        CHINO_HILLS_META["region"]),
            ("Method",        CHINO_HILLS_META["method"]),
            ("BBP Version",   CHINO_HILLS_META["bbp_version"]),
            ("GP Update",     CHINO_HILLS_META["gp_update"]),
        ]

        for i, (label, value) in enumerate(meta_fields):
            row, col = i // 2, (i % 2) * 2
            ctk.CTkLabel(
                meta_frame,
                text=f"{label}:",
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color="gray"
            ).grid(row=row, column=col, padx=(15, 5), pady=6, sticky="w")
            ctk.CTkLabel(
                meta_frame,
                text=str(value),
                font=(res.FONT_LABEL[0], 12),
                text_color="white"
            ).grid(row=row, column=col + 1, padx=(0, 15), pady=6, sticky="w")

        ctk.CTkLabel(
            meta_frame,
            text=CHINO_HILLS_META["description"],
            font=(res.FONT_LABEL[0], 11),
            text_color="#aaaaaa",
            wraplength=780,
            justify="left"
        ).grid(row=6, column=0, columnspan=4, padx=15, pady=(0, 12), sticky="w")

        # --- FAULT GEOMETRY ---
        self._section_header(scroll, "Fault Source Parameters (.src)")

        src_frame = ctk.CTkFrame(
            scroll, fg_color="#222222", border_width=1, border_color="#444"
        )
        src_frame.pack(fill="x", pady=(0, 12), padx=5)
        src_frame.grid_columnconfigure((1, 3), weight=1)

        src_descriptions = {
            "MAGNITUDE"      : "Moment Magnitude (Mw)",
            "FAULT_LENGTH"   : "Length along strike (km)",
            "FAULT_WIDTH"    : "Width down-dip (km)",
            "DEPTH_TO_TOP"   : "Depth to top edge (km)",
            "STRIKE"         : "Angle from North (degrees)",
            "RAKE"           : "Direction of slip (degrees)",
            "DIP"            : "Dip angle (degrees)",
            "LAT_TOP_CENTER" : "Latitude of top center",
            "LON_TOP_CENTER" : "Longitude of top center",
            "HYPO_ALONG_STK" : "Hypocenter along strike (km)",
            "HYPO_DOWN_DIP"  : "Hypocenter down-dip (km)",
            "DWID"           : "Discretization width (km)",
            "DLEN"           : "Discretization length (km)",
            "SEED"           : "Random seed",
        }

        for i, (param, value) in enumerate(CHINO_HILLS_SRC.items()):
            row, col = i // 2, (i % 2) * 2
            desc = src_descriptions.get(param, "")

            ctk.CTkLabel(
                src_frame,
                text=f"{param}:",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=res.COLOR_PRIMARY
            ).grid(row=row, column=col, padx=(15, 5), pady=5, sticky="w")

            val_frame = ctk.CTkFrame(src_frame, fg_color="transparent")
            val_frame.grid(row=row, column=col + 1, padx=(0, 15), pady=5, sticky="w")

            ctk.CTkLabel(
                val_frame,
                text=str(value),
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color="white"
            ).pack(side="left")

            ctk.CTkLabel(
                val_frame,
                text=f"  -  {desc}",
                font=(res.FONT_LABEL[0], 10),
                text_color="#666666"
            ).pack(side="left")

        # --- STATION LIST ---
        self._section_header(scroll, f"Real Seismic Stations ({len(CHINO_HILLS_STATIONS)} stations)")

        # Column headers
        hdr = ctk.CTkFrame(scroll, fg_color="#1a1a3a", corner_radius=4)
        hdr.pack(fill="x", padx=5, pady=(0, 2))
        hdr.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        headers = ["#", "Station ID", "Longitude", "Latitude", "Vs30 (m/s)", "HP / LP Freq (Hz)"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(
                hdr,
                text=h,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=res.COLOR_PRIMARY
            ).grid(row=0, column=i, padx=8, pady=6, sticky="w")

        # Station rows
        for idx, (lon, lat, sid, vs30, hp, lp) in enumerate(CHINO_HILLS_STATIONS):
            row_color = "#222222" if idx % 2 == 0 else "#1e1e1e"
            row_frame = ctk.CTkFrame(
                scroll, fg_color=row_color, corner_radius=2, height=28
            )
            row_frame.pack(fill="x", padx=5, pady=1)
            row_frame.pack_propagate(False)
            row_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

            values = [
                str(idx + 1),
                sid,
                f"{lon:.3f}",
                f"{lat:.3f}",
                str(vs30),
                f"{hp} / {lp}"
            ]
            colors = ["gray", "white", "#aaaaaa", "#aaaaaa", res.COLOR_SUCCESS, "#aaaaaa"]

            for col, (val, color) in enumerate(zip(values, colors)):
                ctk.CTkLabel(
                    row_frame,
                    text=val,
                    font=(res.FONT_LABEL[0], 11),
                    text_color=color,
                    anchor="w"
                ).grid(row=0, column=col, padx=8, pady=3, sticky="w")

        # --- CLOSE BUTTON ---
        ctk.CTkButton(
            scroll,
            text="Close",
            width=120,
            height=36,
            fg_color="#333333",
            hover_color="#444444",
            command=self.destroy
        ).pack(pady=20)

    def _section_header(self, parent, text):
        """Renders a styled section divider with label."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=(10, 4))

        ctk.CTkLabel(
            frame,
            text=text,
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(side="left")

        sep = ctk.CTkFrame(frame, fg_color="#333333", height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)