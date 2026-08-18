# CustomPipelinePanel.py — ui/PanelResources/CustomPipelinePanel.py
# -------------------------------------------------------
# Shared panel resource — used by all simulation methods.
# Visual flowchart pipeline selector.
# Modules displayed as clickable boxes connected by arrows.
# Click any box to toggle it on/off.
# Dependencies enforced automatically.
# -------------------------------------------------------

import customtkinter as ctk
import tkinter as tk
import os
import sys

# ui/PanelResources/ → up two levels to reach project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.AppConfig import AppConfig


# ------------------------------------------------------------------
# MODULE DEFINITIONS
# ------------------------------------------------------------------
MODULES = {
    "Genslip": {
        "role"    : "Source Generator",
        "desc"    : "Generates slip distribution\nacross fault plane.\nProduces .srf + rupture map.",
        "req_text": "Always required",
        "requires": [],
        "always"  : True,
    },
    "Jbsim": {
        "role"    : "LF Synthesis  0–1 Hz",
        "desc"    : "Low frequency seismograms\nusing deterministic wave\npropagation physics.",
        "req_text": "Requires: Genslip",
        "requires": ["Genslip"],
        "always"  : False,
    },
    "Hfsims": {
        "role"    : "HF Synthesis  1–10+ Hz",
        "desc"    : "High frequency seismograms\nusing stochastic approach\nfor crustal scattering.",
        "req_text": "Requires: Genslip",
        "requires": ["Genslip"],
        "always"  : False,
    },
    "Plot_Map": {
        "role"    : "Map — Independent",
        "desc"    : "Geographic station and\nfault trace map PNG.\nIndependent of LF/HF.",
        "req_text": "Requires: Genslip",
        "requires": ["Genslip"],
        "always"  : False,
    },
    "Match": {
        "role"    : "Broadband Merge",
        "desc"    : "Merges LF + HF using\ncosine taper at ~1 Hz\ncrossover frequency.",
        "req_text": "Requires: Jbsim + Hfsims",
        "requires": ["Jbsim", "Hfsims"],
        "always"  : False,
    },
    "PlotSeis": {
        "role"    : "Seismogram Plots",
        "desc"    : "Velocity + acceleration\nseismogram plots per\nstation as PNG files.",
        "req_text": "Requires: Match",
        "requires": ["Match"],
        "always"  : False,
    },
    "RotD100": {
        "role"    : "Response Spectra",
        "desc"    : "RotD50 and RotD100\nresponse spectra for\neach station.",
        "req_text": "Requires: Match",
        "requires": ["Match"],
        "always"  : False,
    },
    "FAS": {
        "role"    : "Fourier Spectrum",
        "desc"    : "Fourier Amplitude\nSpectrum per station\n(NS, EW, Smoothed EAS).",
        "req_text": "Requires: Match",
        "requires": ["Match"],
        "always"  : False,
    },
    "GenHTML": {
        "role"    : "HTML Report",
        "desc"    : "Complete HTML summary\nreport with all results\nand linked output files.",
        "req_text": "Requires: Match",
        "requires": ["Match"],
        "always"  : False,
    },
}

# Arrow connections: (source, target)
ARROWS = [
    ("Genslip", "Jbsim"),
    ("Genslip", "Hfsims"),
    ("Genslip", "Plot_Map"),
    ("Jbsim",   "Match"),
    ("Hfsims",  "Match"),
    ("Match",   "PlotSeis"),
    ("Match",   "RotD100"),
    ("Match",   "FAS"),
    ("Match",   "GenHTML"),
]

# Module positions as fractions of canvas (cx, cy)
MODULE_POS = {
    "Genslip"  : (0.10, 0.46),
    "Jbsim"    : (0.30, 0.25),
    "Hfsims"   : (0.30, 0.60),
    "Plot_Map" : (0.30, 0.86),
    "Match"    : (0.52, 0.42),
    "PlotSeis" : (0.74, 0.16),
    "RotD100"  : (0.74, 0.38),
    "FAS"      : (0.74, 0.60),
    "GenHTML"  : (0.74, 0.82),
}

# Visual states colors
STATE_COLORS = {
    "always": {
        "fill": "#0D2A1A", "outline": "#11CAA0", "accent": "#11CAA0",
        "name": "#11CAA0", "role": "#0a9060", "desc": "#0a6040", "req": "#0a5030",
    },
    "selected": {
        "fill": "#0D1A30", "outline": "#3b8ed0", "accent": "#3b8ed0",
        "name": "white",   "role": "#3b8ed0", "desc": "#7aaccc", "req": "#3a6a88",
    },
    "available": {
        "fill": "#1a1a28", "outline": "#555577", "accent": "#555577",
        "name": "#aaaacc", "role": "#666688", "desc": "#555566", "req": "#444455",
    },
    "locked": {
        "fill": "#111111", "outline": "#222222", "accent": "#222222",
        "name": "#2a2a2a", "role": "#1a1a1a", "desc": "#181818", "req": "#151515",
    },
}

EXECUTION_ORDER = [
    "Genslip", "Jbsim", "Hfsims", "Match",
    "Plot_Map", "PlotSeis", "RotD100", "FAS", "GenHTML"
]


class CustomPipelinePanel(ctk.CTkToplevel):

    def __init__(self, master, on_confirm=None, method="GP"):
        super().__init__(master)

        self._on_confirm   = on_confirm
        self._method       = method
        self._box_coords   = {}
        self._resize_timer = None

        # Each method's rupture generator has a different BBP module name.
        # Confirmed against real BBP-generated XML for each method (Song:
        # run 4182486, Irikura2: run 5874832) rather than assumed —
        # Irikura2 shares IrikuraGenSrf with Irikura1 (same rupture
        # generator either way). Unrecognized methods fall back to
        # "Genslip" (GP).
        RUPTURE_KEYS = {
            "GP"      : "Genslip",
            "IRIKURA1": "IrikuraGenSrf",
            "IRIKURA2": "IrikuraGenSrf",
            "SONG"    : "SongRMGSS",
            "UCSB"    : "UCrmg",
        }
        self._rupture_key = RUPTURE_KEYS.get(method, "Genslip")

        # Unlike the rupture generator, the HF module genuinely differs
        # for Irikura2 — IrikuraHF (Kamae et al. 1998), not Hfsims —
        # confirmed against the same real Irikura2 XML. Every other
        # method still uses Hfsims. UCSB has no entry here at all: it
        # does not have a separate LF/HF split — UCrmg feeds directly
        # into Syn1D, a single combined broadband synthesis module, with
        # no Match step. UCSB's pipeline shape is built entirely
        # separately in _build_modules/_build_arrows/_build_positions/
        # _build_order rather than through this rk/hf substitution
        # pattern, since it genuinely doesn't fit the fork-then-merge
        # shape every other method shares — confirmed against a real
        # BBP-generated UCSB scenario XML (run 6907992).
        HF_KEYS = {
            "GP"      : "Hfsims",
            "IRIKURA1": "Hfsims",
            "IRIKURA2": "IrikuraHF",
            "SONG"    : "Hfsims",
        }
        self._hf_key = HF_KEYS.get(method, "Hfsims")

        # Build the active module definitions for this method
        self._modules        = self._build_modules()
        self._arrows         = self._build_arrows()
        self._module_pos     = self._build_positions()
        self._execution_order = self._build_order()

        # Start with only the rupture generator selected (always required)
        self._selected = {self._rupture_key}

        TITLES = {
            "GP"      : "Custom Pipeline Selector — Graves & Pitarka",
            "IRIKURA1": "Custom Pipeline Selector — Irikura Recipe 1",
            "IRIKURA2": "Custom Pipeline Selector — Irikura Recipe 2",
            "SONG"    : "Custom Pipeline Selector — Song RMG",
            "UCSB"    : "Custom Pipeline Selector — UCSB",
        }
        self.title(TITLES.get(method, "Custom Pipeline Selector"))
        self.configure(fg_color="#0d0d0d")
        self.resizable(True, True)
        self.transient(master)

        try:
            self.state("zoomed")
        except Exception:
            self.geometry("1400x820")

        self._build_ui()
        self.after(250, self._draw_all)

    def _build_modules(self):
        """Returns module definitions with the correct rupture generator
        and HF module names."""
        if self._method == "UCSB":
            return {
                "UCrmg": {
                    "role"    : "Source Generator",
                    "desc"    : "UCSB kinematic rupture model\n(JA19_2S double-corner-freq.\nsource spectrum). Produces .srf.",
                    "req_text": "Always required",
                    "requires": [],
                    "always"  : True,
                },
                "Syn1D": {
                    "role"    : "Broadband Synthesis",
                    "desc"    : "Combined LF+HF broadband\nseismograms in one step —\nno separate HF module, no Match.",
                    "req_text": "Requires: UCrmg",
                    "requires": ["UCrmg"],
                    "always"  : False,
                },
                "CopySeismograms": {
                    "role"    : "Seismogram Finalize",
                    "desc"    : "UCSB-only step. Prepares\nSyn1D output for the shared\nplotting/analysis modules.",
                    "req_text": "Requires: Syn1D",
                    "requires": ["Syn1D"],
                    "always"  : False,
                },
                "Plot_Map": {
                    "role"    : "Map — Independent",
                    "desc"    : "Geographic station and\nfault trace map PNG.\nIndependent of Syn1D.",
                    "req_text": "Requires: UCrmg",
                    "requires": ["UCrmg"],
                    "always"  : False,
                },
                "PlotSeis": {
                    "role"    : "Seismogram Plots",
                    "desc"    : "Velocity + acceleration\nseismogram plots per\nstation as PNG files.",
                    "req_text": "Requires: CopySeismograms",
                    "requires": ["CopySeismograms"],
                    "always"  : False,
                },
                "RotD100": {
                    "role"    : "Response Spectra",
                    "desc"    : "RotD50 and RotD100\nresponse spectra for\neach station.",
                    "req_text": "Requires: CopySeismograms",
                    "requires": ["CopySeismograms"],
                    "always"  : False,
                },
                "FAS": {
                    "role"    : "Fourier Spectrum",
                    "desc"    : "Fourier Amplitude\nSpectrum per station\n(NS, EW, Smoothed EAS).",
                    "req_text": "Requires: CopySeismograms",
                    "requires": ["CopySeismograms"],
                    "always"  : False,
                },
                "GenHTML": {
                    "role"    : "HTML Report",
                    "desc"    : "Complete HTML summary\nreport with all results\nand linked output files.",
                    "req_text": "Requires: CopySeismograms",
                    "requires": ["CopySeismograms"],
                    "always"  : False,
                },
            }

        rk = self._rupture_key
        hf = self._hf_key
        RK_DESCRIPTIONS = {
            "GP"      : "Generates slip distribution\nacross fault plane.\nProduces .srf + rupture map.",
            "IRIKURA1": "Irikura recipe rupture model.\nGenerates slip distribution\nProduces .srf + rupture map.",
            "IRIKURA2": "Irikura recipe rupture model.\nGenerates slip distribution\nProduces .srf + rupture map.",
            "SONG"    : "Song pseudo-dynamic rupture\nmodel. Generates slip distribution\nProduces .srf + rupture map.",
        }
        rk_desc = RK_DESCRIPTIONS.get(self._method, RK_DESCRIPTIONS["GP"])

        HF_DESCRIPTIONS = {
            "Hfsims"  : "High frequency seismograms\nusing stochastic approach\nfor crustal scattering.",
            "IrikuraHF": "High frequency seismograms\nvia Kamae et al. (1998)\nstochastic Green's functions.",
        }
        hf_desc = HF_DESCRIPTIONS.get(hf, HF_DESCRIPTIONS["Hfsims"])

        return {
            rk: {
                "role"    : "Source Generator",
                "desc"    : rk_desc,
                "req_text": "Always required",
                "requires": [],
                "always"  : True,
            },
            "Jbsim": {
                "role"    : "LF Synthesis  0–1 Hz",
                "desc"    : "Low frequency seismograms\nusing deterministic wave\npropagation physics.",
                "req_text": f"Requires: {rk}",
                "requires": [rk],
                "always"  : False,
            },
            hf: {
                "role"    : "HF Synthesis  1–10+ Hz",
                "desc"    : hf_desc,
                "req_text": f"Requires: {rk}",
                "requires": [rk],
                "always"  : False,
            },
            "Plot_Map": {
                "role"    : "Map — Independent",
                "desc"    : "Geographic station and\nfault trace map PNG.\nIndependent of LF/HF.",
                "req_text": f"Requires: {rk}",
                "requires": [rk],
                "always"  : False,
            },
            "Match": {
                "role"    : "Broadband Merge",
                "desc"    : "Merges LF + HF using\ncosine taper at ~1 Hz\ncrossover frequency.",
                "req_text": f"Requires: Jbsim + {hf}",
                "requires": ["Jbsim", hf],
                "always"  : False,
            },
            "PlotSeis": {
                "role"    : "Seismogram Plots",
                "desc"    : "Velocity + acceleration\nseismogram plots per\nstation as PNG files.",
                "req_text": "Requires: Match",
                "requires": ["Match"],
                "always"  : False,
            },
            "RotD100": {
                "role"    : "Response Spectra",
                "desc"    : "RotD50 and RotD100\nresponse spectra for\neach station.",
                "req_text": "Requires: Match",
                "requires": ["Match"],
                "always"  : False,
            },
            "FAS": {
                "role"    : "Fourier Spectrum",
                "desc"    : "Fourier Amplitude\nSpectrum per station\n(NS, EW, Smoothed EAS).",
                "req_text": "Requires: Match",
                "requires": ["Match"],
                "always"  : False,
            },
            "GenHTML": {
                "role"    : "HTML Report",
                "desc"    : "Complete HTML summary\nreport with all results\nand linked output files.",
                "req_text": "Requires: Match",
                "requires": ["Match"],
                "always"  : False,
            },
        }

    def _build_arrows(self):
        if self._method == "UCSB":
            return [
                ("UCrmg", "Syn1D"),
                ("UCrmg", "Plot_Map"),
                ("Syn1D", "CopySeismograms"),
                ("CopySeismograms", "PlotSeis"),
                ("CopySeismograms", "RotD100"),
                ("CopySeismograms", "FAS"),
                ("CopySeismograms", "GenHTML"),
            ]

        rk = self._rupture_key
        hf = self._hf_key
        return [
            (rk,      "Jbsim"),
            (rk,      hf),
            (rk,      "Plot_Map"),
            ("Jbsim", "Match"),
            (hf,      "Match"),
            ("Match", "PlotSeis"),
            ("Match", "RotD100"),
            ("Match", "FAS"),
            ("Match", "GenHTML"),
        ]

    def _build_positions(self):
        if self._method == "UCSB":
            return {
                "UCrmg"           : (0.10, 0.46),
                "Syn1D"           : (0.32, 0.46),
                "Plot_Map"        : (0.32, 0.86),
                "CopySeismograms" : (0.54, 0.46),
                "PlotSeis"        : (0.76, 0.16),
                "RotD100"         : (0.76, 0.38),
                "FAS"             : (0.76, 0.60),
                "GenHTML"         : (0.76, 0.82),
            }

        rk = self._rupture_key
        hf = self._hf_key
        return {
            rk          : (0.10, 0.46),
            "Jbsim"     : (0.30, 0.25),
            hf          : (0.30, 0.60),
            "Plot_Map"  : (0.30, 0.86),
            "Match"     : (0.52, 0.42),
            "PlotSeis"  : (0.74, 0.16),
            "RotD100"   : (0.74, 0.38),
            "FAS"       : (0.74, 0.60),
            "GenHTML"   : (0.74, 0.82),
        }

    def _build_order(self):
        if self._method == "UCSB":
            return ["UCrmg", "Syn1D", "CopySeismograms",
                    "Plot_Map", "PlotSeis", "RotD100", "FAS", "GenHTML"]

        rk = self._rupture_key
        hf = self._hf_key
        return [rk, "Jbsim", hf, "Match",
                "Plot_Map", "PlotSeis", "RotD100", "FAS", "GenHTML"]

    def _on_ready(self):
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
            self.update_idletasks()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------------

    def _build_ui(self):

        # --- TITLE BAR ---
        bar = ctk.CTkFrame(self, fg_color="#111111",
                           corner_radius=0, height=55)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="Custom Pipeline Selector",
            font=(res.FONT_TITLE[0], 17, "bold"),
            text_color="white"
        ).pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            bar,
            text="Click any box to toggle  —  Arrows show dependencies  —  Gray boxes are locked",
            font=(res.FONT_LABEL[0], 11),
            text_color="#666666"
        ).pack(side="left", padx=20)

        HEADER_LABELS = {
            "GP"      : "Graves & Pitarka  —  LA Basin",
            "IRIKURA1": "Irikura Recipe 1  —  LA Basin",
            "IRIKURA2": "Irikura Recipe 2  —  LA Basin",
            "SONG"    : "Song RMG  —  LA Basin",
            "UCSB"    : "UCSB  —  LA Basin",
        }
        ctk.CTkLabel(
            bar,
            text=HEADER_LABELS.get(self._method, "LA Basin"),
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="right", padx=20)

        # --- LEGEND ---
        leg = ctk.CTkFrame(self, fg_color="#0d0d0d",
                           corner_radius=0, height=30)
        leg.pack(fill="x")
        leg.pack_propagate(False)

        for color, label in [
            ("#11CAA0", "Always required"),
            ("#3b8ed0", "Selected"),
            ("#555577", "Available — click to select"),
            ("#2a2a2a", "Locked — select required modules first"),
        ]:
            ctk.CTkLabel(leg, text="■", font=("Arial", 12),
                         text_color=color).pack(side="left", padx=(14, 3), pady=4)
            ctk.CTkLabel(leg, text=label,
                         font=(res.FONT_LABEL[0], 10),
                         text_color="#555555").pack(side="left", padx=(0, 16))

        # --- CANVAS ---
        self.canvas = tk.Canvas(
            self,
            bg="#0d0d0d",
            highlightthickness=0,
            cursor="arrow"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._on_resize)

        # --- BOTTOM BAR ---
        bot = ctk.CTkFrame(self, fg_color="#111111",
                           corner_radius=0, height=52)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        ctk.CTkButton(
            bot, text="Cancel",
            width=100, height=34,
            fg_color="#2a2a2a", hover_color="#333333",
            command=self.destroy
        ).pack(side="left", padx=12, pady=9)

        ctk.CTkButton(
            bot, text="Select All",
            width=110, height=34,
            fg_color="#2a2a2a",
            border_width=1, border_color="#444444",
            command=self._select_all
        ).pack(side="left", padx=4, pady=9)

        ctk.CTkButton(
            bot, text="Reset to Core",
            width=120, height=34,
            fg_color="#2a2a2a",
            border_width=1, border_color="#444444",
            command=self._reset_to_core
        ).pack(side="left", padx=4, pady=9)

        # Pipeline summary label
        self.lbl_summary = ctk.CTkLabel(
            bot, text="",
            font=("Courier", 10),
            text_color="#3b8ed0"
        )
        self.lbl_summary.pack(side="left", padx=16, pady=9)

        ctk.CTkButton(
            bot, text="Confirm Selection",
            width=160, height=34,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            font=(res.FONT_LABEL[0], 12, "bold"),
            command=self._confirm
        ).pack(side="right", padx=12, pady=9)

    # ------------------------------------------------------------------
    # RESIZE HANDLER WITH DEBOUNCE
    # ------------------------------------------------------------------

    def _on_resize(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(80, self._draw_all)

    # ------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------

    def _draw_all(self):
        """Redraws the entire flowchart on the canvas."""
        self.canvas.delete("all")
        self._box_coords.clear()

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 100 or ch < 100:
            return

        # Box dimensions proportional to canvas
        bw = int(cw * 0.145)
        bh = int(ch * 0.200)

        # Compute absolute box centers
        centers = {}
        for key, (fx, fy) in self._module_pos.items():
            centers[key] = (int(fx * cw), int(fy * ch))

        # Draw arrows FIRST (behind boxes)
        self._draw_arrows(centers, bw, bh)

        # Draw boxes ON TOP
        for key, (cx, cy) in centers.items():
            self._draw_box(key, cx, cy, bw, bh)

        # Update summary
        self._update_summary()

    def _draw_arrows(self, centers, bw, bh):
        """Draws orthogonal arrows between connected modules."""
        for src, dst in self._arrows:
            sx, sy = centers[src]
            dx, dy = centers[dst]

            # Determine arrow color based on state
            src_selected = src in self._selected
            dst_state    = self._get_state(dst)

            if not src_selected:
                color = "#1a1a1a"
                width = 1
            elif dst_state == "locked":
                color = "#222233"
                width = 1
            elif dst_state in ("selected", "always"):
                color = "#3b8ed0"
                width = 2
            else:
                color = "#444466"
                width = 1

            # Source right edge → destination left edge
            x1 = sx + bw // 2  # right edge of source
            y1 = sy
            x2 = dx - bw // 2  # left edge of dest
            y2 = dy

            # Midpoint x for the bend
            mx = (x1 + x2) // 2

            # Draw orthogonal path: right → bend → right
            if abs(y1 - y2) < 8:
                # Same height — straight line
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=color, width=width,
                    arrow=tk.LAST, arrowshape=(8, 10, 4)
                )
            else:
                # L-shaped path
                self.canvas.create_line(
                    x1, y1,
                    mx, y1,
                    mx, y2,
                    x2, y2,
                    fill=color, width=width,
                    smooth=False,
                    arrow=tk.LAST, arrowshape=(8, 10, 4)
                )

    def _draw_box(self, key, cx, cy, bw, bh):
        """Draws a single module box — text spaced by actual font heights."""
        mod   = self._modules[key]
        state = self._get_state(key)
        col   = STATE_COLORS[state]

        x1 = cx - bw // 2
        y1 = cy - bh // 2
        x2 = cx + bw // 2
        y2 = cy + bh // 2

        self._box_coords[key] = (x1, y1, x2, y2)

        # Main rectangle
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=col["fill"], outline=col["outline"],
            width=2, tags=f"box_{key}"
        )

        # Accent bar (top)
        accent_h = max(4, bh // 22)
        self.canvas.create_rectangle(
            x1, y1, x2, y1 + accent_h,
            fill=col["accent"], outline=col["accent"],
            tags=f"box_{key}"
        )

        # --- FONT SIZES ---
        # Capped so text never overflows even on small screens
        fs_name = max(9,  min(int(bw * 0.092), int(bh * 0.13), 17))
        fs_role = max(8,  min(int(bw * 0.063), int(bh * 0.10), 12))
        fs_desc = max(7,  min(int(bw * 0.058), int(bh * 0.09), 11))
        fs_req  = max(7,  min(int(bw * 0.056), int(bh * 0.08), 10))

        # --- VERTICAL LAYOUT ---
        # Approximate line heights (font_size * 1.55 for single line)
        lh_name  = fs_name * 1.55
        lh_role  = fs_role * 1.55
        lh_desc  = fs_desc * 1.40   # per line
        lh_req   = fs_req  * 1.55

        # Total content height
        n_desc_lines = 3
        total_h = (lh_name + lh_role +
                   lh_desc * n_desc_lines + lh_req +
                   3 * 4)   # 4px gap between each element x 3 gaps

        # Start y — center the content block vertically inside the box
        top_pad   = accent_h + 4
        available = bh - top_pad - 4
        start_y   = y1 + top_pad + max(0, (available - total_h) / 2)

        # Locked state — show lock icon + name + req only
        if state == "locked":
            mid_y = y1 + bh * 0.35
            self.canvas.create_text(
                cx, mid_y,
                text="🔒  " + key,
                font=("Calibri", fs_name, "bold"),
                fill=col["name"],
                tags=f"box_{key}"
            )
            self.canvas.create_text(
                cx, y2 - lh_req * 0.5 - 4,
                text=mod["req_text"],
                font=("Courier", fs_req),
                fill=col["req"],
                tags=f"box_{key}"
            )
            return

        # --- NORMAL STATE: name → role → desc → req ---
        cur = start_y + lh_name * 0.5

        # Name
        self.canvas.create_text(
            cx, cur,
            text=key,
            font=("Calibri", fs_name, "bold"),
            fill=col["name"],
            tags=f"box_{key}"
        )
        cur += lh_name * 0.5 + 4 + lh_role * 0.5

        # Role
        self.canvas.create_text(
            cx, cur,
            text=mod["role"],
            font=("Calibri", fs_role),
            fill=col["role"],
            tags=f"box_{key}"
        )
        cur += lh_role * 0.5 + 4 + lh_desc * n_desc_lines * 0.5

        # Description (multiline)
        self.canvas.create_text(
            cx, cur,
            text=mod["desc"],
            font=("Calibri", fs_desc),
            fill=col["desc"],
            justify="center",
            tags=f"box_{key}"
        )
        cur += lh_desc * n_desc_lines * 0.5 + 4 + lh_req * 0.5

        # Requirements
        self.canvas.create_text(
            cx, min(cur, y2 - 4),
            text=mod["req_text"],
            font=("Courier", fs_req),
            fill=col["req"],
            tags=f"box_{key}"
        )

        # Cursor hand for clickable boxes
        if not mod["always"]:
            self.canvas.tag_bind(
                f"box_{key}", "<Enter>",
                lambda e, k=key: self.canvas.config(cursor="hand2")
            )
            self.canvas.tag_bind(
                f"box_{key}", "<Leave>",
                lambda e: self.canvas.config(cursor="arrow")
            )

    # ------------------------------------------------------------------
    # STATE LOGIC
    # ------------------------------------------------------------------

    def _get_state(self, key):
        mod = self._modules[key]
        if mod["always"]:
            return "always"
        deps_met = all(r in self._selected for r in mod["requires"])
        if not deps_met:
            return "locked"
        if key in self._selected:
            return "selected"
        return "available"

    def _cascade_deselect(self, key):
        """Deselects all modules that depend on the given key."""
        for mod_key, mod in self._modules.items():
            if key in mod["requires"] and mod_key in self._selected:
                self._selected.discard(mod_key)
                self._cascade_deselect(mod_key)

    # ------------------------------------------------------------------
    # CLICK HANDLING
    # ------------------------------------------------------------------

    def _on_canvas_click(self, event):
        x, y = event.x, event.y

        for key, (x1, y1, x2, y2) in self._box_coords.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._toggle(key)
                return

    def _toggle(self, key):
        mod   = self._modules[key]
        state = self._get_state(key)

        if mod["always"] or state == "locked":
            return

        if key in self._selected:
            # Deselect — cascade downstream
            self._selected.discard(key)
            self._cascade_deselect(key)
        else:
            # Select — deps already met
            self._selected.add(key)

        self._draw_all()

    # ------------------------------------------------------------------
    # QUICK HELPERS
    # ------------------------------------------------------------------

    def _select_all(self):
        self._selected = set(self._modules.keys())
        self._draw_all()

    def _reset_to_core(self):
        if self._method == "UCSB":
            self._selected = {"UCrmg", "Syn1D", "CopySeismograms"}
        else:
            self._selected = {self._rupture_key, "Jbsim", self._hf_key, "Match"}
        self._draw_all()

    def _update_summary(self):
        ordered = [m for m in self._execution_order if m in self._selected]
        self.lbl_summary.configure(
            text=" → ".join(ordered) if ordered else ""
        )

    # ------------------------------------------------------------------
    # CONFIRM
    # ------------------------------------------------------------------

    def _confirm(self):
        ordered = [m for m in self._execution_order if m in self._selected]
        if not ordered:
            return

        AppConfig.simulation_profile = "custom"
        AppConfig.custom_modules     = ordered

        if self._on_confirm:
            self._on_confirm(ordered)

        self.destroy()