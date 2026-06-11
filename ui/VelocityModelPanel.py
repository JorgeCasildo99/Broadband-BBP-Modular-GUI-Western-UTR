# VelocityModelPanel.py — ui/VelocityModelPanel.py
# -------------------------------------------------------
# Displays the 1D velocity model used in a BBP simulation.
# Plots Vp, Vs, and Density vs Depth with depth increasing
# downward (geological convention), as requested by Dr. Ghofrani.
# Reads the .fk1d file from the GP velocity model directory.
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge

try:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPLOT_OK = True
except ImportError:
    MPLOT_OK = False

try:
    from PIL import Image
    import io
    PIL_OK = True
except ImportError:
    PIL_OK = False

from ui.results.ImageFullscreenPanel import ImageFullscreenPanel


# ──────────────────────────────────────────────────────────────────────────────
# PARSER
# ──────────────────────────────────────────────────────────────────────────────

def parse_fk1d(content):
    """
    Parses a BBP .fk1d velocity model file.

    Format:
      Line 1: N (number of layers)
      Lines 2..N+1: thickness(km)  Vp(km/s)  Vs(km/s)  Density(g/cm³)  Qp  Qs

    Returns list of dicts with keys:
      depth_top, depth_bot, thickness, vp, vs, density, qp, qs
    The last layer has thickness=999 (half-space).
    """
    lines  = [l.strip() for l in content.strip().splitlines()
              if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return []

    try:
        n = int(lines[0])
    except ValueError:
        return []

    layers = []
    depth  = 0.0
    for i in range(1, n + 1):
        if i >= len(lines):
            break
        parts = lines[i].split()
        if len(parts) < 4:
            continue
        thick   = float(parts[0])
        vp      = float(parts[1])
        vs      = float(parts[2])
        density = float(parts[3])
        qp      = float(parts[4]) if len(parts) > 4 else 0.0
        qs      = float(parts[5]) if len(parts) > 5 else 0.0

        layers.append({
            "depth_top" : depth,
            "depth_bot" : depth + thick if thick < 500 else depth + 50,
            "thickness" : thick,
            "vp"        : vp,
            "vs"        : vs,
            "density"   : density,
            "qp"        : qp,
            "qs"        : qs,
        })
        if thick < 500:
            depth += thick

    return layers


# ──────────────────────────────────────────────────────────────────────────────
# PANEL
# ──────────────────────────────────────────────────────────────────────────────

class VelocityModelPanel(ctk.CTkToplevel):
    """
    Popup window showing the 1D velocity model (Vp, Vs, Density vs Depth).
    Opens from the Results Panel Simulation Info tab or Configuration Panel.
    """

    def __init__(self, master, model_name="LABasin500", title="Velocity Model"):
        super().__init__(master)

        self._model_name = model_name
        self._layers     = []
        self._pil_img    = None

        self.title(f"Velocity Model — {model_name}")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self.after(150, self._on_ready)
        self.after(300, self._load)

    def _on_ready(self):
        try:
            self.wm_attributes("-zoomed", True)
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        bar = ctk.CTkFrame(self, fg_color="#0d0d0d",
                           corner_radius=0, height=50)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text=f"1D Velocity Model — {self._model_name}",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            bar,
            text="Click plot to open fullscreen",
            font=(res.FONT_LABEL[0], 10),
            text_color="#444444"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            bar, text="Close", width=80, height=30,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=10, pady=10)

        # Main layout — left info panel + right plot
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=8)
        main.grid_columnconfigure(0, weight=0, minsize=220)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # Left info panel
        left_outer = ctk.CTkFrame(main, fg_color="#111111",
                                  corner_radius=8, border_width=1,
                                  border_color="#2a2a2a")
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left = ctk.CTkScrollableFrame(
            left_outer, fg_color="transparent"
        )
        left.pack(fill="both", expand=True)
        self._build_info(left)

        # Right plot area — scrollable so plots + full table are accessible
        right_outer = ctk.CTkFrame(
            main, fg_color="#0d0d0d",
            corner_radius=8, border_width=1, border_color="#2a2a2a"
        )
        right_outer.grid(row=0, column=1, sticky="nsew")

        self.plot_frame = ctk.CTkScrollableFrame(
            right_outer, fg_color="transparent",
            scrollbar_button_color="#2a2a2a",
            scrollbar_button_hover_color="#444444"
        )
        self.plot_frame.pack(fill="both", expand=True)

        self._loading_lbl = ctk.CTkLabel(
            self.plot_frame,
            text="Loading velocity model...",
            font=(res.FONT_LABEL[0], 14),
            text_color="#444444"
        )
        self._loading_lbl.pack(pady=80)

    def _build_info(self, parent):
        def _sec(text):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=(12, 2))
            ctk.CTkLabel(
                f, text=text,
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color="#666666"
            ).pack(side="left")
            ctk.CTkFrame(f, fg_color="#333333", height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=6)

        _sec("MODEL INFO")
        self._info_lbl = ctk.CTkLabel(
            parent,
            text="Loading...",
            font=("Courier", 9),
            text_color="#555555",
            justify="left"
        )
        self._info_lbl.pack(anchor="w", padx=14, pady=4)

        _sec("SCIENTIFIC NOTE")
        ctk.CTkLabel(
            parent,
            text=(
                "A 1D velocity model assumes\n"
                "Earth properties change only\n"
                "with depth, not horizontally.\n\n"
                "Vp = P-wave velocity\n"
                "(compressional waves, faster)\n\n"
                "Vs = S-wave velocity\n"
                "(shear waves, slower,\n"
                "more damaging to structures)\n\n"
                "ρ = Density (g/cm³)\n\n"
                "Each horizontal band is one\n"
                "layer. The last layer extends\n"
                "to infinity (half-space)."
            ),
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555",
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 12))

    # ── LOADING ───────────────────────────────────────────────────────────────

    def _load(self):
        import threading

        def _do():
            home = WSLBridge.get_wsl_home()
            # Try GP .fk1d file first (most complete)
            fk1d_path = f"{home}/bbp_gf/{self._model_name}/gp/nr02-vs500.fk1d"
            ok, content = WSLBridge.read_wsl_file(fk1d_path)

            if not ok or not content.strip():
                # Fallback: search for any .fk1d in model folder
                result = WSLBridge.run_command(
                    f"find '{home}/bbp_gf/{self._model_name}' "
                    f"-name '*.fk1d' | head -1"
                )
                fk1d_path = result.stdout.strip()
                if fk1d_path:
                    ok, content = WSLBridge.read_wsl_file(fk1d_path)

            if not ok or not content.strip():
                self.after(0, self._on_error,
                           f"Velocity model file not found for {self._model_name}")
                return

            layers = parse_fk1d(content)
            if not layers:
                self.after(0, self._on_error, "Could not parse velocity model file.")
                return

            self.after(0, self._on_loaded, layers, fk1d_path)

        threading.Thread(target=_do, daemon=True).start()

    def _on_error(self, msg):
        self._loading_lbl.configure(text=msg, text_color=res.COLOR_ERROR)

    def _on_loaded(self, layers, file_path):
        self._layers = layers
        self._loading_lbl.destroy()

        # Update info label
        max_depth = layers[-1]["depth_top"]
        self._info_lbl.configure(
            text=(
                f"Model:    {self._model_name}\n"
                f"Layers:   {len(layers)}\n"
                f"Max dep:  {max_depth:.1f} km\n"
                f"Vp range: {min(l['vp'] for l in layers):.2f} – "
                f"{max(l['vp'] for l in layers):.2f} km/s\n"
                f"Vs range: {min(l['vs'] for l in layers):.2f} – "
                f"{max(l['vs'] for l in layers):.2f} km/s\n"
                f"File: .../{os.path.basename(file_path)}"
            ),
            text_color="#aaaaaa"
        )

        # Populate layer table
        # (table is now shown below the plots, not in the left panel)

        self._draw()

    # ── DRAWING ───────────────────────────────────────────────────────────────

    def _draw(self):
        if not MPLOT_OK or not self._layers:
            return

        for w in self.plot_frame.winfo_children():
            w.destroy()
        plt.close("all")

        layers = self._layers

        # Build step-function arrays for plotting
        # Each layer: draw horizontal line at top depth, then at bottom depth
        def _step(layers, key):
            depths = []
            vals   = []
            for layer in layers:
                depths.append(layer["depth_top"])
                vals.append(layer[key])
                depths.append(layer["depth_bot"])
                vals.append(layer[key])
            return depths, vals

        depths_vp,  vp      = _step(layers, "vp")
        depths_vs,  vs      = _step(layers, "vs")
        depths_rho, density = _step(layers, "density")

        plt.style.use("dark_background")
        fig, (ax1, ax2, ax3) = plt.subplots(
            1, 3, figsize=(12, 8),
            facecolor="#0d0d0d",
            sharey=True
        )
        fig.subplots_adjust(
            left=0.08, right=0.97,
            top=0.90, bottom=0.08,
            wspace=0.08
        )

        max_depth = layers[-1]["depth_top"]
        y_max     = max_depth + 2   # small buffer below last layer top

        # Common axis settings
        for ax in (ax1, ax2, ax3):
            ax.set_facecolor("#1a1a1a")
            ax.set_ylim(y_max, 0)   # depth increases downward
            ax.tick_params(colors="gray", labelsize=9)
            ax.grid(True, color="#2a2a2a", linewidth=0.5, linestyle="--")
            for spine in ax.spines.values():
                spine.set_edgecolor("#333333")

        # Vp
        ax1.plot(vp, depths_vp, color="#4a9fd4", linewidth=2.0)
        ax1.fill_betweenx(depths_vp, 0, vp,
                          alpha=0.15, color="#4a9fd4")
        ax1.set_xlabel("Vp (km/s)", color="gray", fontsize=11)
        ax1.set_ylabel("Depth (km)", color="gray", fontsize=11)
        ax1.set_title("P-wave Velocity", color="#4a9fd4",
                      fontsize=11, fontweight="bold")

        # Vs
        ax2.plot(vs, depths_vs, color="#e07040", linewidth=2.0)
        ax2.fill_betweenx(depths_vs, 0, vs,
                          alpha=0.15, color="#e07040")
        ax2.set_xlabel("Vs (km/s)", color="gray", fontsize=11)
        ax2.set_title("S-wave Velocity", color="#e07040",
                      fontsize=11, fontweight="bold")

        # Density
        ax3.plot(density, depths_rho, color="#11CAA0", linewidth=2.0)
        ax3.fill_betweenx(depths_rho, 0, density,
                          alpha=0.15, color="#11CAA0")
        ax3.set_xlabel("Density (g/cm³)", color="gray", fontsize=11)
        ax3.set_title("Density", color="#11CAA0",
                      fontsize=11, fontweight="bold")

        # Add layer boundary lines across all panels
        for layer in layers[:-1]:
            d = layer["depth_bot"]
            for ax in (ax1, ax2, ax3):
                ax.axhline(d, color="#333333",
                           linewidth=0.8, linestyle="--", alpha=0.6)

        fig.suptitle(
            f"1D Velocity Model — {self._model_name}   "
            f"({len(layers)} layers, max depth {max_depth:.0f} km)",
            color="white", fontsize=12, y=0.96
        )

        # Save for fullscreen
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
        tk_w.configure(height=600)
        tk_w.pack(fill="x", padx=6, pady=(6, 0))
        tk_w.bind("<Button-1>", lambda e: self._open_fullscreen())

        # Stats bar
        stats = ctk.CTkFrame(self.plot_frame, fg_color="#111111", corner_radius=4)
        stats.pack(fill="x", padx=6, pady=(0, 4))
        ctk.CTkLabel(
            stats,
            text=(
                f"  Vp: {min(l['vp'] for l in layers):.2f} – "
                f"{max(l['vp'] for l in layers):.2f} km/s   |   "
                f"Vs: {min(l['vs'] for l in layers):.2f} – "
                f"{max(l['vs'] for l in layers):.2f} km/s   |   "
                f"ρ: {min(l['density'] for l in layers):.2f} – "
                f"{max(l['density'] for l in layers):.2f} g/cm³   |   "
                f"Click plot to view fullscreen"
            ),
            font=("Courier", 9),
            text_color="#555555"
        ).pack(side="left", padx=10, pady=6)

        # ── DATA TABLE ───────────────────────────────────────────────
        # Spreadsheet-style table showing all layer values
        table_outer = ctk.CTkFrame(
            self.plot_frame, fg_color="#111111",
            corner_radius=0, border_width=1, border_color="#2a2a2a"
        )
        table_outer.pack(fill="x", padx=6, pady=(0, 6))

        # Table title
        title_row = ctk.CTkFrame(table_outer, fg_color="#1a1a1a", height=28)
        title_row.pack(fill="x")
        title_row.pack_propagate(False)
        ctk.CTkLabel(
            title_row,
            text="Layer Data Table",
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(side="left", padx=10, pady=4)
        ctk.CTkLabel(
            title_row,
            text="H = thickness (km)  |  All velocities in km/s  |  ρ in g/cm³",
            font=(res.FONT_LABEL[0], 9),
            text_color="#444444"
        ).pack(side="right", padx=10, pady=4)

        # Table content — no scroll, shows all rows at once
        table_content = ctk.CTkFrame(table_outer, fg_color="transparent")
        table_content.pack(fill="x", padx=0, pady=0)

        # Alias so the rest of the code works unchanged
        table_scroll = table_content
        table_scroll.pack(fill="x", padx=0, pady=0)

        # Column definitions
        cols = [
            ("Layer",    "#",          40),
            ("Depth Top","Dep (km)",   72),
            ("H (km)",   "H (km)",     60),
            ("Vp",       "Vp (km/s)",  80),
            ("Vs",       "Vs (km/s)",  80),
            ("Density",  "ρ (g/cm³)", 80),
            ("Qp",       "Qp",         60),
            ("Qs",       "Qs",         60),
            ("Vp/Vs",    "Vp/Vs",      60),
        ]

        COLORS = {
            "header"  : "#1e1e1e",
            "even"    : "#181818",
            "odd"     : "#1e1e1e",
            "text_hdr": "#aaaaaa",
            "vp"      : "#4a9fd4",
            "vs"      : "#e07040",
            "density" : "#11CAA0",
            "other"   : "#888888",
        }

        # Header row
        hdr_row = ctk.CTkFrame(table_scroll, fg_color=COLORS["header"])
        hdr_row.pack(fill="x", pady=(0, 1))

        for _, label, width in cols:
            ctk.CTkLabel(
                hdr_row, text=label,
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color=COLORS["text_hdr"],
                width=width, anchor="center"
            ).pack(side="left", padx=1)

        # Data rows
        for idx, layer in enumerate(layers):
            row_color = COLORS["even"] if idx % 2 == 0 else COLORS["odd"]
            row = ctk.CTkFrame(table_scroll, fg_color=row_color)
            row.pack(fill="x", pady=0)
            thick_str = f"{layer['thickness']:.3f}" if layer['thickness'] < 500 else "∞"
            vp_vs     = f"{layer['vp']/layer['vs']:.2f}" if layer['vs'] > 0 else "—"
            is_halfspace = layer['thickness'] >= 500

            cell_data = [
                (str(idx + 1),                  40, "#666666"),
                (f"{layer['depth_top']:.3f}",   72, "#aaaaaa"),
                (thick_str,                      60, "#aaaaaa"),
                (f"{layer['vp']:.3f}",           80, COLORS["vp"]),
                (f"{layer['vs']:.3f}",           80, COLORS["vs"]),
                (f"{layer['density']:.3f}",      80, COLORS["density"]),
                (f"{layer['qp']:.1f}",           60, COLORS["other"]),
                (f"{layer['qs']:.1f}",           60, COLORS["other"]),
                (vp_vs,                          60, "#777777"),
            ]

            for val, width, color in cell_data:
                ctk.CTkLabel(
                    row, text=val,
                    font=("Courier", 9),
                    text_color=color,
                    width=width, anchor="center"
                ).pack(side="left", padx=1, pady=2)

            # Highlight half-space row
            if is_halfspace:
                ctk.CTkLabel(
                    row, text="← half-space",
                    font=(res.FONT_LABEL[0], 8),
                    text_color="#444444"
                ).pack(side="left", padx=4)

    def _open_fullscreen(self):
        if self._pil_img:
            ImageFullscreenPanel(
                self, pil_image=self._pil_img,
                title=f"Velocity Model — {self._model_name}"
            )