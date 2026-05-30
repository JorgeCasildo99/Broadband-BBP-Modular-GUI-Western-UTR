# StationDetailPanel.py — ui/Results/StationDetailPanel.py
# -------------------------------------------------------
# Per-station popup panel. Shows all BBP outputs for
# a single station: Velocity, Acceleration, RotD50,
# RotD100, FAS, Raw Data. Opens when a station is
# clicked in the ResultsPanel station list.
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge
from ui.results.ResultsHelpers import (
    _section_label, _textbox, _image_tab
)
from ui.results.ImageFullscreenPanel import ImageFullscreenPanel

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class StationDetailPanel(ctk.CTkToplevel):
    """
    Popup showing ALL BBP results for a single station,
    matching the BBP HTML report:
    Velocity, Acceleration, RotD50, RotD100, FAS, Raw Data.
    """

    def __init__(self, master, station_id, outdata,
                 fas_folder, run_id, profile="full"):
        super().__init__(master)

        self.sid        = station_id
        self.outdata    = outdata
        self.fas_folder = fas_folder
        self.run_id     = run_id
        self.profile    = profile

        self.title(f"Station — {station_id}")
        self.geometry("1050x780")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self.after(200, self._on_ready)

    def _on_ready(self):
        try:
            self.lift()
            self.focus_force()
            self.update_idletasks()
        except Exception:
            pass

    def _p(self, filename):
        """Shorthand: full outdata path for a file."""
        return f"{self.outdata}/{filename}"

    def _f(self, filename):
        """Shorthand: full FAS folder path for a file."""
        return f"{self.fas_folder}/{filename}"

    def _build_ui(self):

        # --- TITLE BAR ---
        bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=55)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text=f"Station: {self.sid}",
            font=(res.FONT_TITLE[0], 18, "bold"), text_color="white"
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            bar, text=f"Run ID: {self.run_id}",
            font=(res.FONT_LABEL[0], 11), text_color="gray"
        ).pack(side="right", padx=20)

        # --- TABS ---
        self.tabs = ctk.CTkTabview(
            self,
            fg_color="#1e1e1e",
            segmented_button_fg_color="#111111",
            segmented_button_selected_color=res.COLOR_PRIMARY,
            segmented_button_selected_hover_color="#004070",
            text_color="white"
        )
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        for name in ["Velocity", "Acceleration", "RotD50", "RotD100", "FAS", "Raw Data"]:
            self.tabs.add(name)

        # Build each tab based on what files actually exist — profile agnostic
        self._build_velocity_tab()
        self._build_acceleration_tab()
        self._build_rotd_tab("RotD50",  "rd50",  "rd50.vertical")
        self._build_rotd_tab("RotD100", "rd100", "rd100.vertical")
        self._build_fas_tab()
        self._build_raw_tab()

        ctk.CTkButton(
            self, text="Close", width=120, height=34,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(pady=8)

    # ------------------------------------------------------------------
    # UNAVAILABLE TAB HELPER
    # ------------------------------------------------------------------

    def _build_unavailable_station_tab(self, tab_name, message):
        tab   = self.tabs.tab(tab_name)
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="Not available for this profile",
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(expand=True, pady=(0, 6))

        ctk.CTkLabel(
            frame, text=message,
            font=(res.FONT_LABEL[0], 11),
            text_color="gray",
            wraplength=460, justify="center"
        ).pack(expand=True)

    # ------------------------------------------------------------------
    # VELOCITY TAB
    # ------------------------------------------------------------------

    def _build_velocity_tab(self):
        tab    = self.tabs.tab("Velocity")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        _section_label(scroll, f"Velocity Seismogram — {self.sid}")

        png_path   = self._p(f"{self.run_id}.{self.sid}_velocity_seis.png")
        png_exists = WSLBridge.wsl_path_exists(png_path)

        if png_exists:
            img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
            img_frame.pack(fill="x", pady=(0, 10))
            _image_tab(img_frame, png_path, "Velocity seismogram plot not found.", master=self)
        else:
            ok, content = WSLBridge.read_wsl_file(
                self._p(f"{self.run_id}.{self.sid}.vel.bbp")
            )
            if ok:
                _section_label(scroll, "Generated Velocity Plot (from raw data)")
                plot_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
                plot_frame.pack(fill="x", pady=(0, 10))
                self._build_bbp_plot(plot_frame, content, "Velocity", "cm/s")
            else:
                ctk.CTkLabel(
                    scroll, text="Velocity data not found.",
                    font=(res.FONT_LABEL[0], 12), text_color="gray"
                ).pack(pady=20)

        _section_label(scroll, "Raw Velocity Data (.vel.bbp)")
        ok, content = WSLBridge.read_wsl_file(
            self._p(f"{self.run_id}.{self.sid}.vel.bbp")
        )
        lines   = content.splitlines() if ok else []
        preview = "\n".join(lines[:80])
        _textbox(scroll, preview if ok else "File not found.", height=200)
        if ok and len(lines) > 80:
            ctk.CTkLabel(
                scroll,
                text=f"Showing 80 of {len(lines)} lines.",
                font=(res.FONT_LABEL[0], 10), text_color="#555555"
            ).pack(anchor="w", pady=(0, 8))

    # ------------------------------------------------------------------
    # ACCELERATION TAB
    # ------------------------------------------------------------------

    def _build_acceleration_tab(self):
        tab    = self.tabs.tab("Acceleration")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        _section_label(scroll, f"Acceleration Seismogram — {self.sid}")

        png_path   = self._p(f"{self.run_id}.{self.sid}_acceleration_seis.png")
        png_exists = WSLBridge.wsl_path_exists(png_path)

        if png_exists:
            img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
            img_frame.pack(fill="x", pady=(0, 10))
            _image_tab(img_frame, png_path, "Acceleration seismogram plot not found.", master=self)
        else:
            ok, content = WSLBridge.read_wsl_file(
                self._p(f"{self.run_id}.{self.sid}.acc.bbp")
            )
            if ok:
                _section_label(scroll, "Generated Acceleration Plot (from raw data)")
                plot_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
                plot_frame.pack(fill="x", pady=(0, 10))
                self._build_bbp_plot(plot_frame, content, "Acceleration", "cm/s²")
            else:
                ctk.CTkLabel(
                    scroll, text="Acceleration data not found.",
                    font=(res.FONT_LABEL[0], 12), text_color="gray"
                ).pack(pady=20)

        _section_label(scroll, "Raw Acceleration Data (.acc.bbp)")
        ok, content = WSLBridge.read_wsl_file(
            self._p(f"{self.run_id}.{self.sid}.acc.bbp")
        )
        lines   = content.splitlines() if ok else []
        preview = "\n".join(lines[:80])
        _textbox(scroll, preview if ok else "File not found.", height=200)
        if ok and len(lines) > 80:
            ctk.CTkLabel(
                scroll,
                text=f"Showing 80 of {len(lines)} lines.",
                font=(res.FONT_LABEL[0], 10), text_color="#555555"
            ).pack(anchor="w", pady=(0, 8))

    # ------------------------------------------------------------------
    # BBP DATA PLOT — matplotlib when PNG not available
    # ------------------------------------------------------------------

    def _build_bbp_plot(self, parent, content, label, unit):
        """
        Parses a .vel.bbp or .acc.bbp file and renders a 3-component
        seismogram (N-S, E-W, U-D) using matplotlib embedded in the frame.
        Saves the figure as PIL Image so the user can click it to open
        the fullscreen viewer with zoom and download.
        """
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        try:
            time_vals, ns_vals, ew_vals, ud_vals = [], [], [], []

            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        time_vals.append(float(parts[0]))
                        ns_vals.append(float(parts[1]))
                        ew_vals.append(float(parts[2]))
                        ud_vals.append(float(parts[3]))
                    except ValueError:
                        continue

            if not time_vals:
                ctk.CTkLabel(
                    parent,
                    text="Could not parse data for plotting.",
                    font=(res.FONT_LABEL[0], 11), text_color="gray"
                ).pack(pady=20)
                return

            plt.style.use("dark_background")
            fig, axes = plt.subplots(3, 1, figsize=(9, 5),
                                     facecolor="#0d0d0d", sharex=True)
            fig.subplots_adjust(hspace=0.35)

            components = [
                (ns_vals, "N-S", "#3b8ed0"),
                (ew_vals, "E-W", "#11CAA0"),
                (ud_vals, "U-D", "#f59e0b"),
            ]

            for ax, (vals, comp, color) in zip(axes, components):
                ax.set_facecolor("#1a1a1a")
                ax.plot(time_vals, vals, color=color, linewidth=0.7)
                ax.set_ylabel(f"{comp}\n({unit})", color="gray",
                              fontsize=8, labelpad=4)
                ax.tick_params(colors="gray", labelsize=7)
                for spine in ax.spines.values():
                    spine.set_edgecolor("#333333")
                ax.axhline(0, color="#333333", linewidth=0.5)

            axes[-1].set_xlabel("Time (s)", color="gray", fontsize=8)
            fig.suptitle(
                f"{label} Seismogram — Station {self.sid}",
                color="white", fontsize=10, y=0.98
            )

            # Save as PIL Image for fullscreen viewer
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150,
                        bbox_inches="tight", facecolor="#0d0d0d")
            buf.seek(0)
            pil_img = Image.open(buf).copy()
            buf.close()

            canvas_widget = FigureCanvasTkAgg(fig, master=parent)
            canvas_widget.draw()
            tk_canvas = canvas_widget.get_tk_widget()
            tk_canvas.pack(fill="both", expand=True, padx=6, pady=(6, 0))

            # Use _mpl_* prefix to avoid conflict with CTkFrame._canvas
            parent._mpl_fig    = fig
            parent._mpl_canvas = canvas_widget
            parent._mpl_pil    = pil_img

            hint = ctk.CTkLabel(
                parent,
                text="🔍  Click image to enlarge, zoom and download",
                font=(res.FONT_LABEL[0], 10),
                text_color="#555555",
                cursor="hand2"
            )
            hint.pack(anchor="w", padx=8, pady=(2, 6))

            def _open_fullscreen(event=None, p=pil_img, l=label, s=self.sid):
                ImageFullscreenPanel(
                    self.winfo_toplevel(),
                    pil_image=p,
                    title=f"{l} Seismogram — Station {s}"
                )

            tk_canvas.bind("<Button-1>", _open_fullscreen)
            hint.bind("<Button-1>",      _open_fullscreen)

        except Exception as e:
            ctk.CTkLabel(
                parent,
                text=f"Plot error: {e}",
                font=(res.FONT_LABEL[0], 11), text_color="gray"
            ).pack(pady=20)

    # ------------------------------------------------------------------
    # ROTD TABS
    # ------------------------------------------------------------------

    def _build_rotd_tab(self, tab_name, hor_ext, ver_ext):
        tab    = self.tabs.tab(tab_name)
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        for label, ext in [("Horizontal", hor_ext), ("Vertical", ver_ext)]:
            _section_label(scroll, f"{tab_name} — {label}")
            ok, content = WSLBridge.read_wsl_file(
                self._p(f"{self.run_id}.{self.sid}.{ext}")
            )
            _textbox(scroll, content if ok else "File not found.", height=180, color="#aaaaaa")

    # ------------------------------------------------------------------
    # FAS TAB
    # ------------------------------------------------------------------

    def _build_fas_tab(self):
        tab    = self.tabs.tab("FAS")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        _section_label(scroll, f"Fourier Amplitude Spectrum — {self.sid}")

        img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
        img_frame.pack(fill="x", pady=(0, 10))
        _image_tab(
            img_frame,
            self._f(f"{self.run_id}.{self.sid}.fas.png"),
            "FAS plot not found.",
            master=self
        )

    # ------------------------------------------------------------------
    # RAW DATA TAB
    # ------------------------------------------------------------------

    def _build_raw_tab(self):
        tab    = self.tabs.tab("Raw Data")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        _section_label(scroll, f"All Files for Station {self.sid}")

        files = [
            (f"{self.run_id}.{self.sid}.vel.bbp",        "Velocity (.vel.bbp)"),
            (f"{self.run_id}.{self.sid}.acc.bbp",        "Acceleration (.acc.bbp)"),
            (f"{self.run_id}.{self.sid}.rd50",           "RotD50 Horizontal"),
            (f"{self.run_id}.{self.sid}.rd50.vertical",  "RotD50 Vertical"),
            (f"{self.run_id}.{self.sid}.rd100",          "RotD100 Horizontal"),
            (f"{self.run_id}.{self.sid}.rd100.vertical", "RotD100 Vertical"),
        ]

        file_frame = ctk.CTkFrame(
            scroll, fg_color="#222222",
            border_width=1, border_color="#444", corner_radius=6
        )
        file_frame.pack(fill="x", pady=(0, 12))
        file_frame.grid_columnconfigure(1, weight=1)

        for i, (fname, label) in enumerate(files):
            full_path = self._p(fname)
            exists    = WSLBridge.wsl_path_exists(full_path)
            color     = res.COLOR_SUCCESS if exists else res.COLOR_ERROR
            status    = "Found" if exists else "Not found"

            ctk.CTkLabel(
                file_frame, text=f"{label}:",
                font=(res.FONT_LABEL[0], 11, "bold"), text_color="gray"
            ).grid(row=i, column=0, padx=(15, 8), pady=5, sticky="w")

            ctk.CTkLabel(
                file_frame,
                text=f"{full_path}  [{status}]",
                font=("Courier", 10), text_color=color,
                anchor="w", wraplength=700
            ).grid(row=i, column=1, padx=(0, 15), pady=5, sticky="w")