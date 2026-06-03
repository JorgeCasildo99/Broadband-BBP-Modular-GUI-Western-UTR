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
                 fas_folder, run_id, profile="full",
                 is_validation=False, val_event_short=""):
        super().__init__(master)

        self.sid             = station_id
        self.outdata         = outdata
        self.fas_folder      = fas_folder
        self.run_id          = run_id
        self.profile         = profile
        self.is_validation   = is_validation
        self.val_event_short = val_event_short

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

        if self.is_validation:
            ctk.CTkLabel(
                bar,
                text="✓ VALIDATION",
                font=(res.FONT_LABEL[0], 10, "bold"),
                text_color="#ffdd00",
                fg_color="#1a1500",
                corner_radius=4,
                padx=6, pady=2
            ).pack(side="left", padx=(0, 10), pady=12)

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

        # Base tabs always present
        tab_names = ["Velocity", "Acceleration", "RotD50/100", "FAS", "Raw Data"]

        # Validation-only tabs
        if self.is_validation:
            tab_names.insert(2, "Overlay")
            tab_names.insert(3, "RotD50 GoF")
            tab_names.append("FAS Comparison")

        for name in tab_names:
            self.tabs.add(name)

        # Build base tabs
        self._build_velocity_tab()
        self._build_acceleration_tab()

        # Build validation-only tabs if applicable
        if self.is_validation:
            self._build_overlay_tab()
            self._build_rotd50_gof_tab()

        self._build_rotd_combined_tab()
        self._build_fas_tab()

        if self.is_validation:
            self._build_fas_comparison_tab()

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

    def _parse_rotd_file(self, content):
        """
        Parses a .rd50 or .rd100 file.
        .rd50  columns: Period  Psa5_N  Psa5_E  RotD50
        .rd100 columns: Period  Psa5_N  Psa5_E  RotD50  RotD100
        Returns (periods, rotd50, rotd100).
        """
        periods, rotd50, rotd100 = [], [], []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    periods.append(float(parts[0]))
                    rotd50.append(float(parts[3]))
                    if len(parts) >= 5:
                        rotd100.append(float(parts[4]))
                except ValueError:
                    continue
        return periods, rotd50, rotd100

    def _build_rotd_combined_tab(self):
        """Combined RotD50/100 tab with log-log chart."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        tab    = self.tabs.tab("RotD50/100")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        sections = [
            ("Horizontal", "rd100", "rd50"),
            ("Vertical",   "rd100.vertical", "rd50.vertical"),
        ]

        for label, primary_ext, fallback_ext in sections:
            _section_label(scroll, f"Response Spectra — {label}")

            ok, content = WSLBridge.read_wsl_file(
                self._p(f"{self.run_id}.{self.sid}.{primary_ext}")
            )
            used_ext = primary_ext
            if not ok or not content.strip():
                ok, content = WSLBridge.read_wsl_file(
                    self._p(f"{self.run_id}.{self.sid}.{fallback_ext}")
                )
                used_ext = fallback_ext

            # GUI-generated notice
            notice = ctk.CTkFrame(
                scroll, fg_color="#0d1a2a", corner_radius=4,
                border_width=1, border_color="#1a3a5a"
            )
            notice.pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(
                notice,
                text=f"ℹ  Chart generated by GUI from raw .{used_ext} data file.",
                font=(res.FONT_LABEL[0], 10),
                text_color="#4a8ab0"
            ).pack(anchor="w", padx=10, pady=6)

            plot_frame = ctk.CTkFrame(
                scroll, fg_color="#0d0d0d", corner_radius=6
            )
            plot_frame.pack(fill="x", pady=(0, 6))

            if not ok or not content.strip():
                ctk.CTkLabel(
                    plot_frame,
                    text=f"Response spectra data not found for {label}.",
                    font=(res.FONT_LABEL[0], 12), text_color="gray"
                ).pack(pady=30)
            else:
                periods, rotd50, rotd100 = self._parse_rotd_file(content)
                if not periods or not rotd50:
                    ctk.CTkLabel(
                        plot_frame,
                        text="Could not parse response spectra data.",
                        font=(res.FONT_LABEL[0], 12), text_color="gray"
                    ).pack(pady=30)
                else:
                    try:
                        plt.style.use("dark_background")
                        fig, ax = plt.subplots(figsize=(9, 4), facecolor="#0d0d0d")
                        ax.set_facecolor("#1a1a1a")

                        ax.plot(periods, rotd50, color="#3b8ed0",
                                linewidth=0.9, label="RotD50 — median horizontal")
                        if rotd100:
                            ax.plot(periods, rotd100, color="#11CAA0",
                                    linewidth=0.9, linestyle="--",
                                    label="RotD100 — maximum horizontal")
                            ax.fill_between(periods, rotd50, rotd100,
                                            alpha=0.12, color="#3b8ed0")

                        ax.set_xscale("log")
                        ax.set_yscale("log")
                        ax.set_xlabel("Period (s)", color="gray", fontsize=9)
                        ax.set_ylabel("Spectral Acceleration (g)", color="gray", fontsize=9)
                        ax.set_title(
                            f"Response Spectra ({label}) — Station {self.sid}",
                            color="white", fontsize=10
                        )
                        ax.tick_params(colors="gray", labelsize=8)
                        ax.grid(True, which="both", color="#2a2a2a",
                                linewidth=0.5, linestyle="--")
                        for spine in ax.spines.values():
                            spine.set_edgecolor("#333333")
                        ax.legend(facecolor="#111111", edgecolor="#444444",
                                  labelcolor="white", fontsize=9)
                        fig.tight_layout()

                        buf = io.BytesIO()
                        fig.savefig(buf, format="png", dpi=150,
                                    bbox_inches="tight", facecolor="#0d0d0d")
                        buf.seek(0)
                        pil_img = Image.open(buf).copy()
                        buf.close()

                        cw = FigureCanvasTkAgg(fig, master=plot_frame)
                        cw.draw()
                        tk_canvas = cw.get_tk_widget()
                        tk_canvas.pack(fill="both", expand=True, padx=6, pady=(6, 0))

                        hint = ctk.CTkLabel(
                            plot_frame,
                            text="🔍  Click chart to enlarge, zoom and download",
                            font=(res.FONT_LABEL[0], 10),
                            text_color="#555555", cursor="hand2"
                        )
                        hint.pack(anchor="w", padx=8, pady=(2, 6))

                        def _open_fs(event=None, p=pil_img,
                                     t=f"Response Spectra {label} — {self.sid}"):
                            ImageFullscreenPanel(self.winfo_toplevel(),
                                                 pil_image=p, title=t)

                        tk_canvas.bind("<Button-1>", _open_fs)
                        hint.bind("<Button-1>",      _open_fs)

                    except Exception as e:
                        ctk.CTkLabel(
                            plot_frame,
                            text=f"Chart error: {e}",
                            font=(res.FONT_LABEL[0], 11), text_color="gray"
                        ).pack(pady=20)

            # Raw data preview
            _section_label(scroll, f"Raw Data (.{used_ext})")
            lines   = content.splitlines() if ok else []
            preview = "\n".join(lines[:80])
            _textbox(scroll, preview if ok else "File not found.",
                     height=160, color="#aaaaaa")
            if ok and len(lines) > 80:
                ctk.CTkLabel(
                    scroll,
                    text=f"Showing 80 of {len(lines)} lines.",
                    font=(res.FONT_LABEL[0], 10),
                    text_color="#555555"
                ).pack(anchor="w", pady=(0, 12))

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

    def _build_overlay_tab(self):
        """Validation only: synthetic vs real waveform overlay plot."""
        tab    = self.tabs.tab("Overlay")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        notice = ctk.CTkFrame(
            scroll, fg_color="#1a1500", corner_radius=4,
            border_width=1, border_color="#3a3000"
        )
        notice.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            notice,
            text="✓  Validation Only — Synthetic vs Real Waveform Overlay",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffdd00"
        ).pack(anchor="w", padx=10, pady=6)
        ctk.CTkLabel(
            notice,
            text="This plot compares the BBP synthetic seismogram (colored) "
                 "against the real recorded seismogram (gray) for this station. "
                 "Good overlap indicates a good simulation fit.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#888855",
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        _section_label(scroll, f"Waveform Overlay — {self.sid}")
        img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
        img_frame.pack(fill="x", pady=(0, 10))
        _image_tab(
            img_frame,
            self._p(f"{self.val_event_short}_{self.run_id}_{self.sid}_overlay.png"),
            "Overlay plot not found.",
            master=self
        )

    def _build_rotd50_gof_tab(self):
        """Validation only: RotD50 response spectra comparison (synthetic vs real)."""
        tab    = self.tabs.tab("RotD50 GoF")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        notice = ctk.CTkFrame(
            scroll, fg_color="#1a1500", corner_radius=4,
            border_width=1, border_color="#3a3000"
        )
        notice.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            notice,
            text="✓  Validation Only — RotD50 Response Spectra Comparison",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffdd00"
        ).pack(anchor="w", padx=10, pady=6)
        ctk.CTkLabel(
            notice,
            text="This plot overlays the synthetic RotD50 response spectrum against "
                 "the real observed spectrum for this station across all periods.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#888855",
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        _section_label(scroll, f"RotD50 Comparison — {self.sid}")
        img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
        img_frame.pack(fill="x", pady=(0, 10))
        _image_tab(
            img_frame,
            self._p(f"{self.val_event_short}_{self.run_id}_{self.sid}_rotd50.png"),
            "RotD50 GoF plot not found.",
            master=self
        )

    def _build_fas_comparison_tab(self):
        """Validation only: FAS synthetic, observed, and comparison plots."""
        tab    = self.tabs.tab("FAS Comparison")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        notice = ctk.CTkFrame(
            scroll, fg_color="#1a1500", corner_radius=4,
            border_width=1, border_color="#3a3000"
        )
        notice.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            notice,
            text="✓  Validation Only — Fourier Amplitude Spectra Comparison",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffdd00"
        ).pack(anchor="w", padx=10, pady=6)
        ctk.CTkLabel(
            notice,
            text="Three FAS plots: synthetic (BBP output), observed (real recording), "
                 "and a direct comparison showing both on the same axes.",
            font=(res.FONT_LABEL[0], 10),
            text_color="#888855",
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        fas_plots = [
            (f"{self.run_id}.{self.sid}.fas.png",           "Synthetic FAS (BBP output)"),
            (f"obs.{self.sid}.fas.png",                     "Observed FAS (real recording)"),
            (f"{self.run_id}.{self.sid}.fas.comparison.png","FAS Comparison (synthetic vs observed)"),
        ]

        for fname, label in fas_plots:
            _section_label(scroll, label)
            img_frame = ctk.CTkFrame(scroll, fg_color="#0d0d0d", corner_radius=6)
            img_frame.pack(fill="x", pady=(0, 12))
            _image_tab(
                img_frame,
                self._f(fname),
                f"{label} not found.",
                master=self
            )

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