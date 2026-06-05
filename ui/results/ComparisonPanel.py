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

        # Frequency band for Signal A
        freq_a_frame = ctk.CTkFrame(parent, fg_color="transparent")
        freq_a_frame.pack(fill="x", padx=14, pady=(2, 4))
        ctk.CTkLabel(
            freq_a_frame, text="Band:",
            font=(res.FONT_LABEL[0], 10), text_color="gray"
        ).pack(side="left", padx=(0, 6))
        self._freq_band_a = ctk.StringVar(value="Broadband")
        ctk.CTkSegmentedButton(
            freq_a_frame,
            values=["Broadband", "LF Only", "HF Only"],
            variable=self._freq_band_a,
            command=lambda v: self._schedule_load(),
            font=(res.FONT_LABEL[0], 9), height=24
        ).pack(side="left", fill="x", expand=True)

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

        # Frequency band for Signal B
        freq_b_frame = ctk.CTkFrame(parent, fg_color="transparent")
        freq_b_frame.pack(fill="x", padx=14, pady=(2, 4))
        ctk.CTkLabel(
            freq_b_frame, text="Band:",
            font=(res.FONT_LABEL[0], 10), text_color="gray"
        ).pack(side="left", padx=(0, 6))
        self._freq_band_b = ctk.StringVar(value="Broadband")
        self._freq_seg_b = ctk.CTkSegmentedButton(
            freq_b_frame,
            values=["Broadband", "LF Only", "HF Only"],
            variable=self._freq_band_b,
            command=lambda v: self._schedule_load(),
            font=(res.FONT_LABEL[0], 9), height=24,
            state="disabled"
        )
        self._freq_seg_b.pack(side="left", fill="x", expand=True)

        self._alpha_b_var, self._lbl_alpha_b, self._slider_b = \
            _opacity_row(parent, "● Opacity B:", COLORS["B"], default=1.0)
        self._slider_b.configure(command=lambda v: self._on_opacity_changed("B", v))

        # ── DATA TYPE ───────────────────────────────────────────────
        _sep("Data Type")

        self._data_type = ctk.StringVar(value="Acceleration")
        ctk.CTkSegmentedButton(
            parent, values=["Acceleration", "Velocity"],
            variable=self._data_type,
            command=self._on_data_type_changed,
            font=(res.FONT_LABEL[0], 10), height=28
        ).pack(fill="x", padx=14, pady=(4, 2))

        # ── PLOT MODE ───────────────────────────────────────────────
        _sep("Plot Mode")

        self._plot_mode = ctk.StringVar(value="Seismogram")
        ctk.CTkSegmentedButton(
            parent, values=["Seismogram", "RotD50/100", "FAS"],
            variable=self._plot_mode,
            command=self._on_plot_mode_changed,
            font=(res.FONT_LABEL[0], 10), height=28
        ).pack(fill="x", padx=14, pady=(4, 2))

        # RotD component selector — shown in both modes, disabled in Seismogram mode
        self._rotd_comp_frame = ctk.CTkFrame(
            parent, fg_color="#1a1a1a", corner_radius=6,
            border_width=1, border_color="#2a2a2a"
        )
        self._rotd_comp_frame.pack(fill="x", padx=14, pady=(4, 6))

        ctk.CTkLabel(
            self._rotd_comp_frame,
            text="RotD Component:",
            font=(res.FONT_LABEL[0], 10),
            text_color="gray"
        ).pack(side="left", padx=(10, 8), pady=6)

        self._rotd_comp = ctk.StringVar(value="Horizontal")
        self._rotd_seg = ctk.CTkSegmentedButton(
            self._rotd_comp_frame,
            values=["Horizontal", "Vertical"],
            variable=self._rotd_comp,
            command=lambda v: self._schedule_load(),
            font=(res.FONT_LABEL[0], 10), height=26,
            state="disabled"
        )
        self._rotd_seg.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=4)

        # FAS component selector
        self._fas_comp_frame = ctk.CTkFrame(
            parent, fg_color="#1a1a1a", corner_radius=6,
            border_width=1, border_color="#2a2a2a"
        )
        self._fas_comp_frame.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkLabel(
            self._fas_comp_frame,
            text="FAS Component:",
            font=(res.FONT_LABEL[0], 10),
            text_color="gray"
        ).pack(side="left", padx=(10, 8), pady=6)

        self._fas_comp = ctk.StringVar(value="Smoothed EAS")
        self._fas_seg = ctk.CTkSegmentedButton(
            self._fas_comp_frame,
            values=["NS (H1)", "EW (H2)", "EAS", "Smoothed EAS"],
            variable=self._fas_comp,
            command=lambda v: self._schedule_load(),
            font=(res.FONT_LABEL[0], 10), height=26,
            state="disabled"
        )
        self._fas_seg.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=4)

        # ── SEPARATOR ───────────────────────────────────────────────
        ctk.CTkFrame(parent, fg_color="#333333", height=1).pack(
            fill="x", padx=14, pady=12)

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

    def _on_plot_mode_changed(self, mode):
        """Switch between Seismogram, RotD50/100 and FAS plot modes."""
        self._rotd_seg.configure(
            state="normal" if mode == "RotD50/100" else "disabled"
        )
        self._fas_seg.configure(
            state="normal" if mode == "FAS" else "disabled"
        )
        self._schedule_load()

    def _on_use_b_toggled(self):
        state = "normal" if self._use_b.get() else "disabled"
        self.menu_run_b.configure(state=state)
        self.menu_sta_b.configure(state=state)
        self._freq_seg_b.configure(state=state)
        if self._use_b.get():
            self._on_run_changed("B")
        else:
            self._cache_b = None
            self._schedule_redraw()

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
        if self._plot_mode.get() == "RotD50/100":
            result = WSLBridge.run_command(
                f"ls '{run['outdata_path']}' 2>/dev/null | grep '.rd100$'"
            )
            if not result.stdout.strip():
                result = WSLBridge.run_command(
                    f"ls '{run['outdata_path']}' 2>/dev/null | grep '.rd50$'"
                )
            ext = ".rd100" if ".rd100" in result.stdout else ".rd50"
        elif self._plot_mode.get() == "FAS":
            result = WSLBridge.run_command(
                f"ls '{run['outdata_path']}/FAS/' 2>/dev/null | grep '.smc8.smooth.fs.col'"
            )
            stations = set()
            for fname in result.stdout.strip().splitlines():
                fname = fname.strip()
                if fname.endswith(".smc8.smooth.fs.col"):
                    parts = fname.split(".")
                    if len(parts) >= 2:
                        stations.add(parts[1])
            return sorted(list(stations))
        else:
            ext = ".acc.bbp" if self._data_type.get() == "Acceleration" else ".vel.bbp"
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

        if self._plot_mode.get() == "RotD50/100":
            self._load_and_draw_rotd()
            return

        if self._plot_mode.get() == "FAS":
            self._load_and_draw_fas()
            return

        # Warn if LF/HF selected — tmpdata may be cleared between runs
        band_a = self._freq_band_a.get()
        band_b = self._freq_band_b.get() if self._use_b.get() else "Broadband"
        if "LF Only" in (band_a, band_b) or "HF Only" in (band_a, band_b):
            self._set_status(
                "Loading LF/HF from tmpdata — files may not exist for older runs.",
                error=False
            )

        # Signal A
        run_a = self._get_run_by_label(self.menu_run_a.get())
        sta_a = self.menu_sta_a.get()
        self._cache_a = self._load_synthetic(run_a, sta_a, signal="A")

        # Signal B
        if self._use_b.get():
            run_b = self._get_run_by_label(self.menu_run_b.get())
            sta_b = self.menu_sta_b.get()
            self._cache_b = self._load_synthetic(run_b, sta_b, signal="B")
        else:
            self._cache_b = None

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

    def _load_synthetic(self, run, station_id, signal="A"):
        if not run or not station_id:
            return None
        if station_id.startswith("—") or station_id == _PLACEHOLDER:
            return None

        band = self._freq_band_a.get() if signal == "A" else self._freq_band_b.get()
        ext  = "acc" if self._data_type.get() == "Acceleration" else "vel"

        if band == "Broadband":
            path = f"{run['outdata_path']}/{run['run_id']}.{station_id}.{ext}.bbp"
            return self._parse_bbp(path)

        elif band == "LF Only":
            home    = WSLBridge.get_wsl_home()
            lf_path = f"{home}/bbp_data/tmpdata/{run['run_id']}/{run['run_id']}.{station_id}-lf.bbp"
            data    = self._parse_bbp(lf_path)
            if data:
                return data
            lf_path2 = f"{home}/bbp_data/tmpdata/{run['run_id']}/{run['run_id']}.{station_id}.lf.bbp"
            return self._parse_bbp(lf_path2)

        elif band == "HF Only":
            home = WSLBridge.get_wsl_home()
            if self._data_type.get() == "Acceleration":
                hf_path = f"{home}/bbp_data/tmpdata/{run['run_id']}/{run['run_id']}.{station_id}-hf.acc.bbp"
            else:
                hf_path = f"{home}/bbp_data/tmpdata/{run['run_id']}/{run['run_id']}.{station_id}-hf.bbp"
            data = self._parse_bbp(hf_path)
            if data:
                return data
            hf_path2 = f"{home}/bbp_data/tmpdata/{run['run_id']}/{run['run_id']}.{station_id}.hf.bbp"
            return self._parse_bbp(hf_path2)

        return None

    def _load_observed(self, station_id):
        if not station_id or station_id not in OBS_STATIONS:
            return None
        return self._parse_bbp(f"{OBS_SEIS_PATH}/{station_id}.bbp")

    def _normalize_signal(self, vals):
        peak = max(abs(v) for v in vals) if vals else 1.0
        return [v / peak for v in vals] if peak != 0 else vals

    # ------------------------------------------------------------------
    # RotD50/100 PARSING AND DRAWING
    # ------------------------------------------------------------------

    def _parse_rotd(self, wsl_path):
        """
        Parses a .rd100 or .rd50 file.
        Columns: Period  Psa5_N  Psa5_E  RotD50  [RotD100]
        Returns (periods, rotd50, rotd100) — rotd100 may be empty.
        """
        ok, content = WSLBridge.read_wsl_file(wsl_path)
        if not ok or not content.strip():
            return None
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
        return (periods, rotd50, rotd100) if periods else None

    def _load_rotd(self, run, station_id):
        """Loads .rd100 (preferred) or .rd50 for a given run/station."""
        if not run or not station_id:
            return None
        if station_id.startswith("—") or station_id == _PLACEHOLDER:
            return None
        comp = self._rotd_comp.get()
        ext  = "rd100.vertical" if comp == "Vertical" else "rd100"
        path = f"{run['outdata_path']}/{run['run_id']}.{station_id}.{ext}"
        data = self._parse_rotd(path)
        if data:
            return data
        # Fallback to rd50
        ext2 = "rd50.vertical" if comp == "Vertical" else "rd50"
        path2 = f"{run['outdata_path']}/{run['run_id']}.{station_id}.{ext2}"
        return self._parse_rotd(path2)

    def _load_and_draw_rotd(self):
        """Loads RotD data and draws the response spectra comparison."""
        run_a = self._get_run_by_label(self.menu_run_a.get())
        sta_a = self.menu_sta_a.get()
        rotd_a = self._load_rotd(run_a, sta_a)

        rotd_b = None
        if self._use_b.get():
            run_b = self._get_run_by_label(self.menu_run_b.get())
            sta_b = self.menu_sta_b.get()
            rotd_b = self._load_rotd(run_b, sta_b)

        self._draw_rotd(rotd_a, rotd_b, run_a, sta_a,
                        self._get_run_by_label(self.menu_run_b.get()) if self._use_b.get() else None,
                        self.menu_sta_b.get() if self._use_b.get() else None)

    def _draw_rotd(self, rotd_a, rotd_b, run_a, sta_a, run_b, sta_b):
        """Draws RotD50/100 response spectra comparison on a log-log chart."""

        for w in self.plot_frame.winfo_children():
            w.destroy()
        plt.close("all")

        if rotd_a is None:
            self._set_status(
                "No RotD data found for Signal A.\n"
                "Make sure the simulation ran RotD100 module.",
                error=True
            )
            ctk.CTkLabel(
                self.plot_frame,
                text="No RotD data found for Signal A.\nCheck that RotD100 module was included in the pipeline.",
                font=(res.FONT_LABEL[0], 13),
                text_color="#555555", justify="center"
            ).pack(expand=True)
            return

        comp   = self._rotd_comp.get()
        alpha_a = float(self._alpha_a_var.get())
        alpha_b = float(self._alpha_b_var.get())

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(11, 7), facecolor="#111111")
        ax.set_facecolor("#1a1a1a")

        periods_a, rotd50_a, rotd100_a = rotd_a

        # Signal A — RotD50 thicker, RotD100 thinner — both solid
        label_a_50  = f"A RotD50  — {run_a['run_id'] if run_a else '?'} / {sta_a}"
        label_a_100 = f"A RotD100 — {run_a['run_id'] if run_a else '?'} / {sta_a}"

        ax.plot(periods_a, rotd50_a,
                color=COLORS["A"], linewidth=1.2,
                alpha=alpha_a, label=label_a_50, zorder=3)
        if rotd100_a:
            ax.plot(periods_a, rotd100_a,
                    color=COLORS["A"], linewidth=0.7,
                    alpha=alpha_a * 0.7,
                    label=label_a_100, zorder=3)
            ax.fill_between(periods_a, rotd50_a, rotd100_a,
                            alpha=alpha_a * 0.10, color=COLORS["A"])

            # Peak annotation for A
            peak_idx_a = max(range(len(rotd50_a)), key=lambda k: rotd50_a[k])
            ax.scatter([periods_a[peak_idx_a]], [rotd50_a[peak_idx_a]],
                       color="white", s=50, zorder=6,
                       edgecolors=COLORS["A"], linewidths=1.5)
            ax.annotate(
                f"Peak A RotD50: {rotd50_a[peak_idx_a]:.4f} g\n"
                f"at T = {periods_a[peak_idx_a]:.3f} s",
                xy=(periods_a[peak_idx_a], rotd50_a[peak_idx_a]),
                xytext=(periods_a[peak_idx_a] * 1.5, rotd50_a[peak_idx_a] * 1.3),
                color=COLORS["A"], fontsize=7,
                arrowprops=dict(arrowstyle="->", color=COLORS["A"], lw=0.8)
            )

        # Signal B
        if rotd_b:
            periods_b, rotd50_b, rotd100_b = rotd_b
            label_b_50  = f"B RotD50  — {run_b['run_id'] if run_b else '?'} / {sta_b}"
            label_b_100 = f"B RotD100 — {run_b['run_id'] if run_b else '?'} / {sta_b}"

            ax.plot(periods_b, rotd50_b,
                    color=COLORS["B"], linewidth=1.0,
                    alpha=alpha_b, label=label_b_50, zorder=3)
            if rotd100_b:
                ax.plot(periods_b, rotd100_b,
                        color=COLORS["B"], linewidth=0.7,
                        alpha=alpha_b * 0.7,
                        label=label_b_100, zorder=3)
                ax.fill_between(periods_b, rotd50_b, rotd100_b,
                                alpha=alpha_b * 0.10, color=COLORS["B"])

                # Peak annotation for B
                peak_idx_b = max(range(len(rotd50_b)), key=lambda k: rotd50_b[k])
                ax.scatter([periods_b[peak_idx_b]], [rotd50_b[peak_idx_b]],
                           color="white", s=50, zorder=6,
                           edgecolors=COLORS["B"], linewidths=1.5)
                ax.annotate(
                    f"Peak B RotD50: {rotd50_b[peak_idx_b]:.4f} g\n"
                    f"at T = {periods_b[peak_idx_b]:.3f} s",
                    xy=(periods_b[peak_idx_b], rotd50_b[peak_idx_b]),
                    xytext=(periods_b[peak_idx_b] * 1.5, rotd50_b[peak_idx_b] * 0.6),
                    color=COLORS["B"], fontsize=7,
                    arrowprops=dict(arrowstyle="->", color=COLORS["B"], lw=0.8)
                )

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Period (s)", color="gray", fontsize=9)
        ax.set_ylabel("Spectral Acceleration (g)", color="gray", fontsize=9)
        ax.set_title(
            f"Response Spectra Comparison — {comp}  "
            f"(thick = RotD50, thin = RotD100)",
            color="white", fontsize=10
        )
        ax.tick_params(colors="gray", labelsize=8)
        ax.grid(True, which="both", color="#2a2a2a",
                linewidth=0.5, linestyle="--")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")

        legend = ax.legend(
            loc="upper right", fontsize=7,
            framealpha=0.4, facecolor="#1a1a1a",
            edgecolor="#444444"
        )
        for txt in legend.get_texts():
            txt.set_color("white")

        fig.tight_layout()

        # Save PIL
        if PIL_AVAILABLE:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150,
                        bbox_inches="tight", facecolor="#111111")
            buf.seek(0)
            self._pil_img = Image.open(buf).copy()
            buf.close()

        cw = FigureCanvasTkAgg(fig, master=self.plot_frame)
        cw.draw()
        tk_w = cw.get_tk_widget()
        tk_w.pack(fill="both", expand=True, padx=4, pady=4)
        tk_w.bind("<Button-1>", lambda e: self._open_fullscreen())

        # Summary card
        if rotd_a:
            summary = ctk.CTkFrame(
                self.plot_frame, fg_color="#1a1a2e",
                corner_radius=6, border_width=1, border_color="#2a2a4a"
            )
            summary.pack(fill="x", padx=6, pady=(0, 2))
            ctk.CTkLabel(
                summary,
                text="Peak Response Spectra Summary",
                font=(res.FONT_LABEL[0], 10, "bold"),
                text_color="#aaaacc"
            ).pack(anchor="w", padx=10, pady=(6, 2))

            peak_idx_a = max(range(len(rotd50_a)), key=lambda k: rotd50_a[k])
            ctk.CTkLabel(
                summary,
                text=(f"  Signal A RotD50  →  Peak: {rotd50_a[peak_idx_a]:.5f} g   "
                      f"at T = {periods_a[peak_idx_a]:.3f} s"),
                font=("Courier", 10),
                text_color=COLORS["A"]
            ).pack(anchor="w", padx=10, pady=(0, 2))

            if rotd_b:
                peak_idx_b = max(range(len(rotd50_b)), key=lambda k: rotd50_b[k])
                ctk.CTkLabel(
                    summary,
                    text=(f"  Signal B RotD50  →  Peak: {rotd50_b[peak_idx_b]:.5f} g   "
                          f"at T = {periods_b[peak_idx_b]:.3f} s"),
                    font=("Courier", 10),
                    text_color=COLORS["B"]
                ).pack(anchor="w", padx=10, pady=(0, 6))
            else:
                ctk.CTkFrame(summary, fg_color="transparent", height=4).pack()

        hint = ctk.CTkLabel(
            self.plot_frame,
            text="Click plot to open fullscreen",
            font=(res.FONT_LABEL[0], 9),
            text_color="#333333", cursor="hand2"
        )
        hint.pack(pady=(0, 4))
        hint.bind("<Button-1>", lambda e: self._open_fullscreen())

        self._set_status("RotD plot ready.")

    # ------------------------------------------------------------------
    # FAS PARSING AND DRAWING
    # ------------------------------------------------------------------

    def _parse_fas(self, wsl_path):
        """
        Parses a .smc8.smooth.fs.col file.
        Columns: Freq(Hz)  FAS_H1  FAS_H2  EAS  Smoothed_EAS
        Returns (freqs, h1, h2, eas, smoothed_eas) or None.
        """
        ok, content = WSLBridge.read_wsl_file(wsl_path)
        if not ok or not content.strip():
            return None
        freqs, h1, h2, eas, smoothed = [], [], [], [], []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    freqs.append(float(parts[0]))
                    h1.append(float(parts[1]))
                    h2.append(float(parts[2]))
                    eas.append(float(parts[3]))
                    smoothed.append(float(parts[4]))
                except ValueError:
                    continue
        return (freqs, h1, h2, eas, smoothed) if freqs else None

    def _load_fas(self, run, station_id):
        """Loads the FAS .smc8.smooth.fs.col file for a given run/station."""
        if not run or not station_id:
            return None
        if station_id.startswith("—") or station_id == _PLACEHOLDER:
            return None
        path = (f"{run['outdata_path']}/FAS/"
                f"{run['run_id']}.{station_id}.smc8.smooth.fs.col")
        return self._parse_fas(path)

    def _load_and_draw_fas(self):
        """Loads FAS data and draws the Fourier spectra comparison."""
        run_a  = self._get_run_by_label(self.menu_run_a.get())
        sta_a  = self.menu_sta_a.get()
        fas_a  = self._load_fas(run_a, sta_a)

        fas_b  = None
        run_b  = None
        sta_b  = None
        if self._use_b.get():
            run_b = self._get_run_by_label(self.menu_run_b.get())
            sta_b = self.menu_sta_b.get()
            fas_b = self._load_fas(run_b, sta_b)

        self._draw_fas(fas_a, fas_b, run_a, sta_a, run_b, sta_b)

    def _draw_fas(self, fas_a, fas_b, run_a, sta_a, run_b, sta_b):
        """Draws FAS comparison on a log-log chart."""
        for w in self.plot_frame.winfo_children():
            w.destroy()
        plt.close("all")

        if fas_a is None:
            self._set_status(
                "No FAS data found for Signal A.\n"
                "Make sure the simulation ran the FAS module.",
                error=True
            )
            ctk.CTkLabel(
                self.plot_frame,
                text="No FAS data found for Signal A.\n"
                     "Check that the FAS module was included in the pipeline.",
                font=(res.FONT_LABEL[0], 13),
                text_color="#555555", justify="center"
            ).pack(expand=True)
            return

        # Which component to plot
        comp_map = {
            "NS (H1)"     : (1, "FAS NS / H1 (cm/s)"),
            "EW (H2)"     : (2, "FAS EW / H2 (cm/s)"),
            "EAS"         : (3, "EAS (cm/s)"),
            "Smoothed EAS": (4, "Smoothed EAS (cm/s)"),
        }
        comp_key  = self._fas_comp.get()
        col_idx, col_label = comp_map.get(comp_key, (4, "Smoothed EAS (cm/s)"))

        alpha_a = float(self._alpha_a_var.get())
        alpha_b = float(self._alpha_b_var.get())

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(11, 7), facecolor="#111111")
        ax.set_facecolor("#1a1a1a")

        freqs_a = fas_a[0]
        vals_a  = fas_a[col_idx]
        label_a = (f"A — {run_a['run_id'] if run_a else '?'} / {sta_a}"
                   f"  [{comp_key}]")

        ax.plot(freqs_a, vals_a,
                color=COLORS["A"], linewidth=1.0,
                alpha=alpha_a, label=label_a, zorder=3)

        # Peak marker A
        peak_idx_a = max(range(len(vals_a)), key=lambda k: vals_a[k])
        ax.scatter([freqs_a[peak_idx_a]], [vals_a[peak_idx_a]],
                   color="white", s=50, zorder=6,
                   edgecolors=COLORS["A"], linewidths=1.5)
        ax.annotate(
            f"Peak A: {vals_a[peak_idx_a]:.4f} cm/s\n"
            f"at f = {freqs_a[peak_idx_a]:.3f} Hz",
            xy=(freqs_a[peak_idx_a], vals_a[peak_idx_a]),
            xytext=(freqs_a[peak_idx_a] * 1.5, vals_a[peak_idx_a] * 1.3),
            color=COLORS["A"], fontsize=7,
            arrowprops=dict(arrowstyle="->", color=COLORS["A"], lw=0.8)
        )

        # Signal B
        if fas_b:
            freqs_b = fas_b[0]
            vals_b  = fas_b[col_idx]
            label_b = (f"B — {run_b['run_id'] if run_b else '?'} / {sta_b}"
                       f"  [{comp_key}]")

            ax.plot(freqs_b, vals_b,
                    color=COLORS["B"], linewidth=1.0,
                    alpha=alpha_b, label=label_b, zorder=3)

            # Peak marker B
            peak_idx_b = max(range(len(vals_b)), key=lambda k: vals_b[k])
            ax.scatter([freqs_b[peak_idx_b]], [vals_b[peak_idx_b]],
                       color="white", s=50, zorder=6,
                       edgecolors=COLORS["B"], linewidths=1.5)
            ax.annotate(
                f"Peak B: {vals_b[peak_idx_b]:.4f} cm/s\n"
                f"at f = {freqs_b[peak_idx_b]:.3f} Hz",
                xy=(freqs_b[peak_idx_b], vals_b[peak_idx_b]),
                xytext=(freqs_b[peak_idx_b] * 1.5, vals_b[peak_idx_b] * 0.6),
                color=COLORS["B"], fontsize=7,
                arrowprops=dict(arrowstyle="->", color=COLORS["B"], lw=0.8)
            )

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Frequency (Hz)", color="gray", fontsize=9)
        ax.set_ylabel(col_label, color="gray", fontsize=9)
        ax.set_title(
            f"Fourier Amplitude Spectra Comparison — {comp_key}",
            color="white", fontsize=10
        )
        ax.tick_params(colors="gray", labelsize=8)
        ax.grid(True, which="both", color="#2a2a2a",
                linewidth=0.5, linestyle="--")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")

        legend = ax.legend(
            loc="upper right", fontsize=7,
            framealpha=0.4, facecolor="#1a1a1a",
            edgecolor="#444444"
        )
        for txt in legend.get_texts():
            txt.set_color("white")

        fig.tight_layout()

        if PIL_AVAILABLE:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150,
                        bbox_inches="tight", facecolor="#111111")
            buf.seek(0)
            self._pil_img = Image.open(buf).copy()
            buf.close()

        cw = FigureCanvasTkAgg(fig, master=self.plot_frame)
        cw.draw()
        tk_w = cw.get_tk_widget()
        tk_w.pack(fill="both", expand=True, padx=4, pady=4)
        tk_w.bind("<Button-1>", lambda e: self._open_fullscreen())

        # Summary card
        summary = ctk.CTkFrame(
            self.plot_frame, fg_color="#1a1a2e",
            corner_radius=6, border_width=1, border_color="#2a2a4a"
        )
        summary.pack(fill="x", padx=6, pady=(0, 2))
        ctk.CTkLabel(
            summary,
            text="Peak Fourier Amplitude Summary",
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color="#aaaacc"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            summary,
            text=(f"  Signal A  [{comp_key}]  →  "
                  f"Peak: {vals_a[peak_idx_a]:.5f} cm/s   "
                  f"at f = {freqs_a[peak_idx_a]:.3f} Hz   "
                  f"(T = {1/freqs_a[peak_idx_a]:.3f} s)"),
            font=("Courier", 10),
            text_color=COLORS["A"]
        ).pack(anchor="w", padx=10, pady=(0, 2))

        if fas_b:
            ctk.CTkLabel(
                summary,
                text=(f"  Signal B  [{comp_key}]  →  "
                      f"Peak: {vals_b[peak_idx_b]:.5f} cm/s   "
                      f"at f = {freqs_b[peak_idx_b]:.3f} Hz   "
                      f"(T = {1/freqs_b[peak_idx_b]:.3f} s)"),
                font=("Courier", 10),
                text_color=COLORS["B"]
            ).pack(anchor="w", padx=10, pady=(0, 6))
        else:
            ctk.CTkFrame(summary, fg_color="transparent", height=4).pack()

        hint = ctk.CTkLabel(
            self.plot_frame,
            text="Click plot to open fullscreen",
            font=(res.FONT_LABEL[0], 9),
            text_color="#333333", cursor="hand2"
        )
        hint.pack(pady=(0, 4))
        hint.bind("<Button-1>", lambda e: self._open_fullscreen())

        self._set_status("FAS plot ready.")

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
        data_b   = self._cache_b if self._use_b.get() else None
        data_obs = None

        unit = ("cm/s²" if self._data_type.get() == "Acceleration" else "cm/s")

        alpha_a   = float(self._alpha_a_var.get())
        alpha_b   = float(self._alpha_b_var.get())

        # Detect if bands are different — need dual Y-axis
        band_a = self._freq_band_a.get()
        band_b = self._freq_band_b.get() if (data_b and self._use_b.get()) else band_a
        dual_axis = (data_b is not None) and (band_a != band_b)

        # Labels with peak amplitude info
        run_a = self._get_run_by_label(self.menu_run_a.get())
        sta_a = self.menu_sta_a.get()
        peak_a = self._peak(data_a)
        band_labels = {"Broadband": "BB", "LF Only": "LF", "HF Only": "HF"}
        label_a = (f"A [{band_labels.get(band_a, band_a)}] — "
                   f"{run_a['run_id'] if run_a else '?'} / {sta_a}"
                   + (f"  (peak: {peak_a:.4f})" if peak_a else ""))

        label_b = None
        if data_b:
            run_b  = self._get_run_by_label(self.menu_run_b.get())
            sta_b  = self.menu_sta_b.get()
            peak_b = self._peak(data_b)
            label_b = (f"B [{band_labels.get(band_b, band_b)}] — "
                       f"{run_b['run_id'] if run_b else '?'} / {sta_b}"
                       + (f"  (peak: {peak_b:.4f})" if peak_b else ""))

        # Clear plot frame and close old figures
        for w in self.plot_frame.winfo_children():
            w.destroy()
        plt.close("all")

        plt.style.use("dark_background")
        fig, axes = plt.subplots(
            3, 1, figsize=(11, 7),
            facecolor="#111111", sharex=True
        )
        fig.subplots_adjust(hspace=0.45, top=0.90, bottom=0.07,
                            left=0.09, right=0.97)

        comp_names = ["N-S", "E-W", "U-D"]

        # --- COMPUTE PEAKS PER COMPONENT ---
        def _component_peaks(data):
            results = []
            for idx in range(3):
                vals = [data[1], data[2], data[3]][idx]
                times = data[0]
                if not vals:
                    results.append((0.0, 0.0, 0.0))
                    continue
                peak_abs = max(abs(v) for v in vals)
                peak_idx = max(range(len(vals)), key=lambda k: abs(vals[k]))
                results.append((peak_abs, vals[peak_idx], times[peak_idx]))
            return results

        peaks_a = _component_peaks(data_a)
        dominant_a_idx = max(range(3), key=lambda i: peaks_a[i][0])

        peaks_b = _component_peaks(data_b) if data_b else None
        dominant_b_idx = max(range(3), key=lambda i: peaks_b[i][0]) if peaks_b else None

        for i, (ax, comp) in enumerate(zip(axes, comp_names)):
            ax.set_facecolor("#1a1a1a")
            ax.axhline(0, color="#2a2a2a", linewidth=0.5, zorder=1)

            def _v(data, idx):
                vals = [data[1], data[2], data[3]][idx]
                return vals

            # Signal A
            ax.plot(data_a[0], _v(data_a, i),
                    color=COLORS["A"], linewidth=0.9,
                    alpha=alpha_a, label=label_a, zorder=3)
            ax.set_ylabel(f"{comp}\n({unit})",
                          color=COLORS["A"] if dual_axis else "gray",
                          fontsize=8, labelpad=4)

            # Peak marker for Signal A on dominant component
            if i == dominant_a_idx:
                pv = peaks_a[i][1]
                ax.scatter([peaks_a[i][2]], [pv],
                           color="#ffffff", s=40, zorder=6,
                           edgecolors=COLORS["A"], linewidths=1.5)
                ax.annotate(
                    f"  Peak A: {pv:.4f} {unit}",
                    xy=(peaks_a[i][2], pv),
                    xytext=(peaks_a[i][2], pv * 1.15 if pv > 0 else pv * 0.85),
                    color=COLORS["A"], fontsize=6.5,
                    arrowprops=dict(arrowstyle="->", color=COLORS["A"], lw=0.8)
                )

            # Signal B
            if data_b:
                if dual_axis:
                    # Twin axis so each signal uses its own scale
                    ax2 = ax.twinx()
                    ax2.set_facecolor("none")
                    ax2.plot(data_b[0], _v(data_b, i),
                             color=COLORS["B"], linewidth=0.9,
                             alpha=alpha_b, label=label_b, zorder=3)
                    ax2.set_ylabel(f"({unit})", color=COLORS["B"],
                                   fontsize=8, labelpad=4)
                    ax2.tick_params(colors=COLORS["B"], labelsize=7)
                    for spine in ax2.spines.values():
                        spine.set_edgecolor("#2a2a2a")

                    if i == dominant_b_idx:
                        pv_b = peaks_b[i][1]
                        ax2.scatter([peaks_b[i][2]], [pv_b],
                                    color="#ffffff", s=40, zorder=6,
                                    edgecolors=COLORS["B"], linewidths=1.5)
                        ax2.annotate(
                            f"  Peak B: {pv_b:.4f} {unit}",
                            xy=(peaks_b[i][2], pv_b),
                            xytext=(peaks_b[i][2], pv_b * 0.75 if pv_b > 0 else pv_b * 1.25),
                            color=COLORS["B"], fontsize=6.5,
                            arrowprops=dict(arrowstyle="->", color=COLORS["B"], lw=0.8)
                        )

                    if i == 0:
                        # Combine legends from both axes
                        lines1, labels1 = ax.get_legend_handles_labels()
                        lines2, labels2 = ax2.get_legend_handles_labels()
                        legend = ax.legend(
                            lines1 + lines2, labels1 + labels2,
                            loc="upper right", fontsize=6.5,
                            framealpha=0.4, facecolor="#1a1a1a",
                            edgecolor="#444444"
                        )
                        for txt in legend.get_texts():
                            txt.set_color("white")
                else:
                    ax.plot(data_b[0], _v(data_b, i),
                            color=COLORS["B"], linewidth=0.9,
                            alpha=alpha_b, label=label_b, zorder=3)

                    if i == dominant_b_idx:
                        pv_b = peaks_b[i][1]
                        ax.scatter([peaks_b[i][2]], [pv_b],
                                   color="#ffffff", s=40, zorder=6,
                                   edgecolors=COLORS["B"], linewidths=1.5)
                        ax.annotate(
                            f"  Peak B: {pv_b:.4f} {unit}",
                            xy=(peaks_b[i][2], pv_b),
                            xytext=(peaks_b[i][2], pv_b * 0.75 if pv_b > 0 else pv_b * 1.25),
                            color=COLORS["B"], fontsize=6.5,
                            arrowprops=dict(arrowstyle="->", color=COLORS["B"], lw=0.8)
                        )

            ax.tick_params(colors="gray", labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor("#2a2a2a")

            if i == 0 and not dual_axis:
                legend = ax.legend(
                    loc="upper right", fontsize=6.5,
                    framealpha=0.4, facecolor="#1a1a1a",
                    edgecolor="#444444"
                )
                for txt in legend.get_texts():
                    txt.set_color("white")            # Signal B — red solid
            if data_b:
                ax.plot(data_b[0], _v(data_b, i),
                        color=COLORS["B"], linewidth=0.9,
                        alpha=alpha_b, label=label_b, zorder=3)

                # Peak marker for Signal B on dominant component
                if i == dominant_b_idx:
                    pv_b = peaks_b[i][1]
                    ax.scatter([peaks_b[i][2]], [pv_b],
                               color="#ffffff", s=40, zorder=6,
                               edgecolors=COLORS["B"], linewidths=1.5)
                    ax.annotate(
                        f"  Peak B: {pv_b:.4f} {unit}",
                        xy=(peaks_b[i][2], pv_b),
                        xytext=(peaks_b[i][2], pv_b * 0.75 if pv_b > 0 else pv_b * 1.25),
                        color=COLORS["B"], fontsize=6.5,
                        arrowprops=dict(arrowstyle="->",
                                       color=COLORS["B"], lw=0.8)
                    )

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

        band_a = self._freq_band_a.get()
        band_b = self._freq_band_b.get() if self._use_b.get() else None
        band_labels = {"Broadband": "BB", "LF Only": "LF", "HF Only": "HF"}
        if band_b and band_b != band_a:
            title_band = f"A:{band_labels[band_a]}  vs  B:{band_labels[band_b]}"
        else:
            title_band = {"Broadband": "Broadband", "LF Only": "LF (0–1 Hz)", "HF Only": "HF (1–10 Hz)"}.get(band_a, band_a)
        fig.suptitle(f"Seismogram Comparison — {title_band}",
                     color="white", fontsize=9, y=0.97)

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

        # --- PEAK MOTION SUMMARY CARD ---
        summary = ctk.CTkFrame(
            self.plot_frame,
            fg_color="#1a1a2e",
            corner_radius=6,
            border_width=1,
            border_color="#2a2a4a"
        )
        summary.pack(fill="x", padx=6, pady=(0, 2))

        dom_comp_a    = comp_names[dominant_a_idx]
        dom_peak_a    = peaks_a[dominant_a_idx][0]
        dom_val_a     = peaks_a[dominant_a_idx][1]
        dom_time_a    = peaks_a[dominant_a_idx][2]

        # Header
        ctk.CTkLabel(
            summary,
            text="Peak Ground Motion Summary",
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color="#aaaacc"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        # Signal A summary
        sign_a = "+" if dom_val_a >= 0 else "-"
        ctk.CTkLabel(
            summary,
            text=(f"  Signal A  →  Strongest axis: {dom_comp_a}   "
                  f"Peak: {sign_a}{dom_peak_a:.5f} {unit}   "
                  f"at t = {dom_time_a:.2f} s"),
            font=("Courier", 10),
            text_color=COLORS["A"]
        ).pack(anchor="w", padx=10, pady=(0, 2))

        # Signal B summary (if active)
        if data_b and peaks_b:
            dom_comp_b = comp_names[dominant_b_idx]
            dom_peak_b = peaks_b[dominant_b_idx][0]
            dom_val_b  = peaks_b[dominant_b_idx][1]
            dom_time_b = peaks_b[dominant_b_idx][2]
            sign_b     = "+" if dom_val_b >= 0 else "-"
            ctk.CTkLabel(
                summary,
                text=(f"  Signal B  →  Strongest axis: {dom_comp_b}   "
                      f"Peak: {sign_b}{dom_peak_b:.5f} {unit}   "
                      f"at t = {dom_time_b:.2f} s"),
                font=("Courier", 10),
                text_color=COLORS["B"]
            ).pack(anchor="w", padx=10, pady=(0, 6))
        else:
            ctk.CTkFrame(summary, fg_color="transparent", height=4).pack()

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