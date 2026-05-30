# ComparisonPanel.py — ui/results/ComparisonPanel.py
# -------------------------------------------------------
# BBP Seismogram Comparison Panel — Dynamic Version.
#
# Plot updates automatically when any control changes:
#   - Run / station change  → reload data + redraw (500ms debounce)
#   - Opacity slider change → redraw only (100ms debounce)
#   - Normalize / datatype  → redraw only (150ms debounce)
#
# Each signal has its own independent opacity slider.
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
from ui.results.ImageFullscreenPanel import ImageFullscreenPanel

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------
OBS_SEIS_PATH = "/home/black/bbp-22.4.0/bbp/tests/ref_data/rzz2015/obs_seis"
OBS_STATIONS  = ["2001-SCE", "2002-SYL", "2004-JGB", "2005-LDM", "2006-PAC"]
_PLACEHOLDER  = "— loading —"

COLORS = {
    "A"        : "#3b8ed0",
    "B"        : "#ef4444",
    "observed" : "#22c55e",
}


def _option_menu(parent, values, command=None, state="normal"):
    kw = dict(
        values=values or [_PLACEHOLDER],
        font=(res.FONT_LABEL[0], 10),
        height=30,
        fg_color="#2a2a2a",
        button_color="#333333",
        button_hover_color="#444444",
        dropdown_fg_color="#1e1e1e",
        dropdown_hover_color="#2a2a2a",
        dropdown_text_color="white",
        state=state,
    )
    if command:
        kw["command"] = command
    m = ctk.CTkOptionMenu(parent, **kw)
    m.set(values[0] if values else _PLACEHOLDER)
    return m


def _opacity_row(parent, label, color, default=1.0):
    """
    Creates a labeled opacity slider row.
    Returns (slider_var, pct_label).
    """
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=14, pady=(2, 4))

    ctk.CTkLabel(
        frame, text=label,
        font=(res.FONT_LABEL[0], 9),
        text_color=color, width=60, anchor="w"
    ).pack(side="left")

    var = ctk.DoubleVar(value=default)

    lbl_pct = ctk.CTkLabel(
        frame, text=f"{int(default*100)}%",
        font=(res.FONT_LABEL[0], 9),
        text_color="#888888", width=36
    )
    lbl_pct.pack(side="right")

    slider = ctk.CTkSlider(
        frame,
        from_=0.05, to=1.0,
        variable=var,
        width=130,
        button_color=color,
        button_hover_color=color,
        progress_color=color,
        fg_color="#2a2a2a"
    )
    slider.pack(side="left", fill="x", expand=True, padx=(4, 4))

    return var, lbl_pct, slider


class ComparisonPanel(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.title("BBP Seismogram Comparison")
        self.geometry("1420x880")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._runs      = []
        self._pil_img   = None
        self._cache_a   = None   # cached parsed data for Signal A
        self._cache_b   = None   # cached parsed data for Signal B
        self._cache_obs = None   # cached parsed data for Observed

        # Debounce job IDs
        self._job_load   = None
        self._job_redraw = None

        self._build_ui()
        self.after(200, self._on_ready)
        self.after(350, self._load_runs)

    def _on_ready(self):
        try:
            self.lift()
            self.focus_force()
            self.state("zoomed")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------------

    def _build_ui(self):

        bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=50)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="BBP SEISMOGRAM COMPARISON",
            font=(res.FONT_TITLE[0], 15, "bold"), text_color="white"
        ).pack(side="left", padx=15, pady=12)

        ctk.CTkLabel(
            bar,
            text="Plot updates automatically when controls change",
            font=(res.FONT_LABEL[0], 11), text_color="gray"
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            bar, text="Close", width=80, height=32,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=10, pady=9)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.grid_columnconfigure(0, weight=0, minsize=370)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(
            main, fg_color="#1e1e1e",
            border_width=1, border_color="#333333",
            corner_radius=8
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_controls(left)

        self.plot_frame = ctk.CTkFrame(
            main, fg_color="#111111",
            border_width=1, border_color="#333333",
            corner_radius=8
        )
        self.plot_frame.grid(row=0, column=1, sticky="nsew")

        self.lbl_plot_hint = ctk.CTkLabel(
            self.plot_frame,
            text="Select a simulation run\nto generate the plot",
            font=(res.FONT_LABEL[0], 13),
            text_color="#444444", justify="center"
        )
        self.lbl_plot_hint.pack(expand=True)

    def _build_controls(self, parent):

        def _sep(text, color=res.COLOR_PRIMARY):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", pady=(10, 2), padx=8)
            ctk.CTkLabel(f, text=text,
                         font=(res.FONT_LABEL[0], 11, "bold"),
                         text_color=color).pack(side="left")
            ctk.CTkFrame(f, fg_color="#333333", height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=6)

        def _lbl(text, color="gray"):
            ctk.CTkLabel(parent, text=text,
                         font=(res.FONT_LABEL[0], 10),
                         text_color=color).pack(anchor="w", padx=14)

        # ── SIGNAL A ────────────────────────────────────────────────
        _sep("Signal A  (required)", COLORS["A"])

        _lbl("Simulation Run:")
        self.menu_run_a = _option_menu(
            parent, [_PLACEHOLDER],
            command=lambda v: self._on_run_changed("A")
        )
        self.menu_run_a.pack(fill="x", padx=14, pady=(2, 5))

        _lbl("Station:")
        self.menu_sta_a = _option_menu(
            parent, [_PLACEHOLDER],
            command=lambda v: self._schedule_load()
        )
        self.menu_sta_a.pack(fill="x", padx=14, pady=(2, 4))

        self._alpha_a_var, self._lbl_alpha_a, self._slider_a = \
            _opacity_row(parent, "● Opacity A:", COLORS["A"], default=1.0)
        self._slider_a.configure(command=lambda v: self._on_opacity_changed("A", v))

        # ── SIGNAL B ────────────────────────────────────────────────
        _sep("Signal B  (optional)", COLORS["B"])

        self._use_b = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            parent, text="Enable Signal B",
            variable=self._use_b,
            command=self._on_use_b_toggled,
            font=(res.FONT_LABEL[0], 10),
            fg_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=14, pady=(4, 3))

        _lbl("Simulation Run:")
        self.menu_run_b = _option_menu(
            parent, [_PLACEHOLDER],
            command=lambda v: self._on_run_changed("B"),
            state="disabled"
        )
        self.menu_run_b.pack(fill="x", padx=14, pady=(2, 5))

        _lbl("Station:")
        self.menu_sta_b = _option_menu(
            parent, ["— enable Signal B first —"],
            command=lambda v: self._schedule_load(),
            state="disabled"
        )
        self.menu_sta_b.pack(fill="x", padx=14, pady=(2, 4))

        self._alpha_b_var, self._lbl_alpha_b, self._slider_b = \
            _opacity_row(parent, "● Opacity B:", COLORS["B"], default=1.0)
        self._slider_b.configure(command=lambda v: self._on_opacity_changed("B", v))

        # ── OBSERVED ────────────────────────────────────────────────
        _sep("Observed — Northridge 1994  (optional)", COLORS["observed"])

        self._use_obs = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            parent, text="Enable Observed Overlay",
            variable=self._use_obs,
            command=self._on_use_obs_toggled,
            font=(res.FONT_LABEL[0], 10),
            fg_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=14, pady=(4, 3))

        _lbl("Northridge Station:")
        self.menu_sta_obs = _option_menu(
            parent, OBS_STATIONS,
            command=lambda v: self._schedule_load(),
            state="disabled"
        )
        self.menu_sta_obs.pack(fill="x", padx=14, pady=(2, 4))

        self._alpha_obs_var, self._lbl_alpha_obs, self._slider_obs = \
            _opacity_row(parent, "● Opacity Obs:", COLORS["observed"], default=0.85)
        self._slider_obs.configure(command=lambda v: self._on_opacity_changed("obs", v))

        # Chino Hills note
        info = ctk.CTkFrame(parent, fg_color="#1a1a0d",
                            border_width=1, border_color="#3a3a1a",
                            corner_radius=6)
        info.pack(fill="x", padx=14, pady=(6, 0))
        ctk.CTkLabel(
            info,
            text="⚠  Northridge observed amplitudes are\n"
                 "   typically 100× larger than synthetics\n"
                 "   (Mw 6.7 vs hypothetical scenario).\n"
                 "   Use Normalize for shape comparison.\n\n"
                 "   Chino Hills recordings are not\n"
                 "   available in BBP v22.4.0.",
            font=(res.FONT_LABEL[0], 9),
            text_color="#888855", justify="left"
        ).pack(anchor="w", padx=8, pady=6)

        # ── DATA TYPE ───────────────────────────────────────────────
        _sep("Data Type")

        self._data_type = ctk.StringVar(value="Acceleration")
        ctk.CTkSegmentedButton(
            parent, values=["Acceleration", "Velocity"],
            variable=self._data_type,
            command=self._on_data_type_changed,
            font=(res.FONT_LABEL[0], 10), height=28
        ).pack(fill="x", padx=14, pady=(4, 2))
        ctk.CTkLabel(parent, text="Observed is always acceleration.",
                     font=(res.FONT_LABEL[0], 9),
                     text_color="#444444").pack(anchor="w", padx=14)

        # ── NORMALIZE ───────────────────────────────────────────────
        _sep("Amplitude")

        self._normalize = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            parent, text="Normalize to peak amplitude",
            variable=self._normalize,
            command=self._schedule_redraw,
            font=(res.FONT_LABEL[0], 10),
            fg_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=14, pady=(4, 2))
        ctk.CTkLabel(
            parent,
            text="Scales each signal to ±1 for shape comparison.",
            font=(res.FONT_LABEL[0], 9),
            text_color="#444444"
        ).pack(anchor="w", padx=14)

        # ── EXPORT ──────────────────────────────────────────────────
        ctk.CTkFrame(parent, fg_color="#333333", height=1).pack(
            fill="x", padx=14, pady=12)

        ctk.CTkButton(
            parent, text="Open Fullscreen",
            height=32, fg_color="#2a2a2a", hover_color="#3a3a3a",
            font=(res.FONT_LABEL[0], 11),
            command=self._open_fullscreen
        ).pack(fill="x", padx=14, pady=(0, 5))

        ctk.CTkButton(
            parent, text="Export as PNG",
            height=32, fg_color="#2a2a2a", hover_color="#3a3a3a",
            font=(res.FONT_LABEL[0], 11),
            command=self._export_plot
        ).pack(fill="x", padx=14, pady=(0, 5))

        self.lbl_status = ctk.CTkLabel(
            parent, text="Loading simulation runs...",
            font=(res.FONT_LABEL[0], 10),
            text_color="gray",
            wraplength=340, justify="left"
        )
        self.lbl_status.pack(anchor="w", padx=14, pady=(8, 8))

    # ------------------------------------------------------------------
    # DEBOUNCE SCHEDULERS
    # ------------------------------------------------------------------

    def _schedule_load(self, delay=500):
        """Schedule a full data reload + redraw (slow, for run/station changes)."""
        if self._job_load:
            self.after_cancel(self._job_load)
        self._job_load = self.after(delay, self._load_and_draw)

    def _schedule_redraw(self, *args, delay=120):
        """Schedule a redraw using cached data (fast, for opacity/normalize)."""
        if self._job_redraw:
            self.after_cancel(self._job_redraw)
        self._job_redraw = self.after(delay, self._draw)

    # ------------------------------------------------------------------
    # EVENT HANDLERS
    # ------------------------------------------------------------------

    def _on_use_b_toggled(self):
        state = "normal" if self._use_b.get() else "disabled"
        self.menu_run_b.configure(state=state)
        self.menu_sta_b.configure(state=state)
        if self._use_b.get():
            self._on_run_changed("B")
        else:
            self._cache_b = None
            self._schedule_redraw()

    def _on_use_obs_toggled(self):
        state = "normal" if self._use_obs.get() else "disabled"
        self.menu_sta_obs.configure(state=state)
        if not self._use_obs.get():
            self._cache_obs = None
        self._schedule_load(delay=200)

    def _on_run_changed(self, signal):
        """When a run changes: refresh station list, then reload data."""
        menu_run = self.menu_run_a if signal == "A" else self.menu_run_b
        menu_sta = self.menu_sta_a if signal == "A" else self.menu_sta_b

        run = self._get_run_by_label(menu_run.get())
        if not run:
            menu_sta.configure(values=["— no run selected —"])
            menu_sta.set("— no run selected —")
            return

        stations = self._get_stations_for_run(run)
        if stations:
            menu_sta.configure(values=stations)
            menu_sta.set(stations[0])
        else:
            menu_sta.configure(values=["— no stations found —"])
            menu_sta.set("— no stations found —")

        self._schedule_load()

    def _on_data_type_changed(self, *args):
        """Data type change: refresh station lists AND reload data."""
        self._on_run_changed("A")
        if self._use_b.get():
            self._on_run_changed("B")

    def _on_opacity_changed(self, signal, value):
        """Opacity slider moved: update label + fast redraw."""
        pct = int(float(value) * 100)
        if signal == "A":
            self._lbl_alpha_a.configure(text=f"{pct}%")
        elif signal == "B":
            self._lbl_alpha_b.configure(text=f"{pct}%")
        else:
            self._lbl_alpha_obs.configure(text=f"{pct}%")
        self._schedule_redraw(delay=80)

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def _load_runs(self):
        bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"

        outdata = f"{bbp_data}/outdata"
        result  = WSLBridge.run_command(f"ls -t '{outdata}' 2>/dev/null")

        if result.returncode != 0 or not result.stdout.strip():
            self._set_status("No simulation runs found.", error=True)
            return

        self._runs = []
        for run_id in result.stdout.strip().splitlines():
            run_id = run_id.strip()
            if not run_id:
                continue
            folder = f"{outdata}/{run_id}"
            r = WSLBridge.run_command(
                f"ls '{folder}/param_files/' 2>/dev/null | grep '[.]src' | head -1"
            )
            src = r.stdout.strip()
            exp = src[:-4] if src.endswith(".src") else f"Run {run_id}"
            self._runs.append({
                "run_id"      : run_id,
                "exp_name"    : exp,
                "outdata_path": folder,
                "label"       : f"{run_id}  \u2014  {exp}"
            })

        if not self._runs:
            self._set_status("No runs found.", error=True)
            return

        labels = [r["label"] for r in self._runs]
        self.menu_run_a.configure(values=labels)
        self.menu_run_a.set(labels[0])
        self.menu_run_b.configure(values=labels)
        self.menu_run_b.set(labels[0])

        self._on_run_changed("A")

    def _get_run_by_label(self, label):
        if not label or label == _PLACEHOLDER or not self._runs:
            return None
        return next((r for r in self._runs if r["label"] == label), None)

    def _get_stations_for_run(self, run):
        if not run:
            return []
        ext    = ".acc.bbp" if self._data_type.get() == "Acceleration" else ".vel.bbp"
        result = WSLBridge.run_command(
            f"ls '{run['outdata_path']}' 2>/dev/null | grep '{ext}'"
        )
        stations = set()
        for fname in result.stdout.strip().splitlines():
            fname = fname.strip()
            if fname.endswith(ext):
                parts = fname.split(".")
                if len(parts) >= 2:
                    stations.add(parts[1])
        return sorted(list(stations))

    def _load_and_draw(self):
        """Full cycle: load all data into cache, then draw."""
        self._set_status("Loading data...", error=False)

        # Signal A
        run_a = self._get_run_by_label(self.menu_run_a.get())
        sta_a = self.menu_sta_a.get()
        self._cache_a = self._load_synthetic(run_a, sta_a)

        # Signal B
        if self._use_b.get():
            run_b = self._get_run_by_label(self.menu_run_b.get())
            sta_b = self.menu_sta_b.get()
            self._cache_b = self._load_synthetic(run_b, sta_b)
        else:
            self._cache_b = None

        # Observed
        if self._use_obs.get():
            obs_sta = self.menu_sta_obs.get()
            self._cache_obs = self._load_observed(obs_sta)
        else:
            self._cache_obs = None

        self._draw()

    # ------------------------------------------------------------------
    # FILE PARSING
    # ------------------------------------------------------------------

    def _parse_bbp(self, wsl_path):
        ok, content = WSLBridge.read_wsl_file(wsl_path)
        if not ok or not content.strip():
            return None
        t, ns, ew, ud = [], [], [], []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t.append(float(parts[0]))
                    ns.append(float(parts[1]))
                    ew.append(float(parts[2]))
                    ud.append(float(parts[3]))
                except ValueError:
                    continue
        return (t, ns, ew, ud) if t else None

    def _load_synthetic(self, run, station_id):
        if not run or not station_id:
            return None
        if station_id.startswith("—") or station_id == _PLACEHOLDER:
            return None
        ext  = "acc" if self._data_type.get() == "Acceleration" else "vel"
        path = f"{run['outdata_path']}/{run['run_id']}.{station_id}.{ext}.bbp"
        return self._parse_bbp(path)

    def _load_observed(self, station_id):
        if not station_id or station_id not in OBS_STATIONS:
            return None
        return self._parse_bbp(f"{OBS_SEIS_PATH}/{station_id}.bbp")

    def _normalize_signal(self, vals):
        peak = max(abs(v) for v in vals) if vals else 1.0
        return [v / peak for v in vals] if peak != 0 else vals

    def _peak(self, data):
        if not data:
            return None
        return max(abs(v) for v in data[1])  # NS component

    # ------------------------------------------------------------------
    # DRAW (uses cached data)
    # ------------------------------------------------------------------

    def _draw(self):
        """Redraws the plot using cached data and current opacity values."""

        if self._cache_a is None:
            self._set_status(
                "Signal A has no data.\n"
                "Check that the selected run and station are valid.",
                error=True
            )
            return

        data_a   = self._cache_a
        data_b   = self._cache_b   if self._use_b.get()  else None
        data_obs = self._cache_obs if self._use_obs.get() else None

        normalize = self._normalize.get()
        unit      = ("normalized" if normalize
                     else "cm/s²" if self._data_type.get() == "Acceleration"
                     else "cm/s")

        alpha_a   = float(self._alpha_a_var.get())
        alpha_b   = float(self._alpha_b_var.get())
        alpha_obs = float(self._alpha_obs_var.get())

        # Labels with peak amplitude info
        run_a = self._get_run_by_label(self.menu_run_a.get())
        sta_a = self.menu_sta_a.get()
        peak_a = self._peak(data_a)
        label_a = (f"A — {run_a['run_id'] if run_a else '?'} / {sta_a}"
                   + (f"  (peak: {peak_a:.4f})" if peak_a else ""))

        label_b, label_obs = None, None
        if data_b:
            run_b  = self._get_run_by_label(self.menu_run_b.get())
            sta_b  = self.menu_sta_b.get()
            peak_b = self._peak(data_b)
            label_b = (f"B — {run_b['run_id'] if run_b else '?'} / {sta_b}"
                       + (f"  (peak: {peak_b:.4f})" if peak_b else ""))

        if data_obs:
            obs_sta  = self.menu_sta_obs.get()
            peak_obs = self._peak(data_obs)
            label_obs = (f"Observed — {obs_sta}  (Northridge 1994)"
                         + (f"  (peak: {peak_obs:.2f} cm/s²)" if peak_obs else ""))

        # Clear plot frame
        for w in self.plot_frame.winfo_children():
            w.destroy()

        plt.style.use("dark_background")
        fig, axes = plt.subplots(
            3, 1, figsize=(11, 7),
            facecolor="#111111", sharex=True
        )
        fig.subplots_adjust(hspace=0.45, top=0.90, bottom=0.07,
                            left=0.09, right=0.97)

        for i, (ax, comp) in enumerate(zip(axes, ["N-S", "E-W", "U-D"])):
            ax.set_facecolor("#1a1a1a")
            ax.axhline(0, color="#2a2a2a", linewidth=0.5, zorder=1)

            def _v(data, idx):
                vals = [data[1], data[2], data[3]][idx]
                return self._normalize_signal(vals) if normalize else vals

            # Signal A — blue solid
            ax.plot(data_a[0], _v(data_a, i),
                    color=COLORS["A"], linewidth=0.9,
                    alpha=alpha_a, label=label_a, zorder=3)

            # Signal B — red solid
            if data_b:
                ax.plot(data_b[0], _v(data_b, i),
                        color=COLORS["B"], linewidth=0.9,
                        alpha=alpha_b, label=label_b, zorder=3)

            # Observed — green dashed
            if data_obs:
                ax.plot(data_obs[0], _v(data_obs, i),
                        color=COLORS["observed"], linewidth=1.0,
                        linestyle="--", alpha=alpha_obs,
                        label=label_obs, zorder=3)

            ax.set_ylabel(f"{comp}\n({unit})",
                          color="gray", fontsize=8, labelpad=4)
            ax.tick_params(colors="gray", labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor("#2a2a2a")

            if i == 0:
                legend = ax.legend(
                    loc="upper right", fontsize=6.5,
                    framealpha=0.4, facecolor="#1a1a1a",
                    edgecolor="#444444"
                )
                for txt in legend.get_texts():
                    txt.set_color("white")

        axes[-1].set_xlabel("Time (s)", color="gray", fontsize=8)

        obs_note = ("\n* Observed U-D = copy of N-S (known BBP dataset limitation)"
                    if data_obs else "")
        norm_note = "  [normalized]" if normalize else ""
        fig.suptitle(f"Seismogram Comparison{norm_note}{obs_note}",
                     color="#888888" if obs_note else "white",
                     fontsize=9, y=0.97)

        # Save PIL image
        if PIL_AVAILABLE:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150,
                        bbox_inches="tight", facecolor="#111111")
            buf.seek(0)
            self._pil_img = Image.open(buf).copy()
            buf.close()

        # Embed in frame
        cw = FigureCanvasTkAgg(fig, master=self.plot_frame)
        cw.draw()
        tk_w = cw.get_tk_widget()
        tk_w.pack(fill="both", expand=True, padx=4, pady=4)

        self.plot_frame._mpl_fig    = fig
        self.plot_frame._mpl_canvas = cw
        self.plot_frame._mpl_pil    = self._pil_img if PIL_AVAILABLE else None

        tk_w.bind("<Button-1>", lambda e: self._open_fullscreen())

        hint = ctk.CTkLabel(self.plot_frame,
                            text="Click plot to open fullscreen",
                            font=(res.FONT_LABEL[0], 9),
                            text_color="#333333", cursor="hand2")
        hint.pack(pady=(0, 4))
        hint.bind("<Button-1>", lambda e: self._open_fullscreen())

        self._set_status("Plot ready.")

    # ------------------------------------------------------------------
    # FULLSCREEN / EXPORT
    # ------------------------------------------------------------------

    def _open_fullscreen(self):
        if not PIL_AVAILABLE or self._pil_img is None:
            self._set_status("No plot to show yet.", error=True)
            return
        ImageFullscreenPanel(self, pil_image=self._pil_img,
                             title="Comparison Plot")

    def _export_plot(self):
        if not PIL_AVAILABLE or self._pil_img is None:
            self._set_status("No plot to export yet.", error=True)
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self, title="Save Comparison Plot",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialfile="comparison.png"
        )
        if not path:
            return
        try:
            self._pil_img.save(path)
            self._set_status(f"Saved: {os.path.basename(path)}")
        except Exception as e:
            self._set_status(f"Save failed: {e}", error=True)

    def _set_status(self, text, error=False):
        self.lbl_status.configure(
            text=text,
            text_color=res.COLOR_ERROR if error else "gray"
        )