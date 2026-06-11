# AdvancedSettingsPanel.py — ui/AdvancedSettingsPanel.py
# -------------------------------------------------------
# GUI panel for viewing and editing the GP simulation
# parameters that BBP reads from the velocity model
# config file at runtime.
#
# ALL writes target:
#   ~/bbp_gf/LABasin500/labasin500_velmodel_config.txt
#
# BBP source files (genslip_cfg.py, hfsims_cfg.py) are
# NEVER modified — the velmodel config overrides them.
#
# Parameter states:
#   ACTIVE   — line exists, uncommented  (KAPPA, QFEXP)
#   OVERRIDE — line exists but commented (MEAN_RVFAC etc.)
#              user must explicitly enable override
#   ABSENT   — line does not exist yet   (SDROP)
#              we add it when user enables override
#
# Verified against BBP v22.4.0 source:
#   hfsims.py  reads: KAPPA, QFEXP, SDROP, MEAN_RVFAC, RANGE_RVFAC
#   genslip.py reads: MEAN_RVFAC, RANGE_RVFAC, RISETIME_COEF
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge
from core.AppConfig  import AppConfig


# ------------------------------------------------------------------
# PARAMETER DEFINITIONS
# ------------------------------------------------------------------
# Each entry describes one BBP parameter:
#   key        — exact key in velmodel config (after CODEBASE_GP_)
#   full_key   — full line key as written in the file
#   label      — display name in GUI
#   default    — BBP hardcoded default (from genslip_cfg / hfsims_cfg)
#   unit       — physical unit string
#   min/max    — valid range for input validation
#   decimals   — decimal places for display
#   state      — "active" (uncommented), "override" (commented), "absent"
#   source_tag — which BBP module reads this
#   description — scientific explanation shown in GUI
# ------------------------------------------------------------------

PARAM_DEFS = [
    # ── HF Synthesis parameters (hfsims.py) ─────────────────────────
    {
        "key"       : "KAPPA",
        "full_key"  : "CODEBASE_GP_KAPPA",
        "label"     : "KAPPA  (κ)",
        "default"   : 0.04,
        "unit"      : "seconds",
        "min"       : 0.001,
        "max"       : 0.15,
        "decimals"  : 4,
        "state"     : "active",
        "source_tag": "hfsims",
        "description": (
            "Near-surface high-frequency attenuation operator. "
            "Controls how much the shallow crust damps HF energy before it reaches the surface. "
            "LA Basin default: 0.04s. Eastern North America (hard rock): ~0.005–0.02s. "
            "Lower κ → sharper waveforms, higher PGA."
        ),
    },
    {
        "key"       : "QFEXP",
        "full_key"  : "CODEBASE_GP_QFEXP",
        "label"     : "QFEXP",
        "default"   : 0.6,
        "unit"      : "dimensionless",
        "min"       : 0.1,
        "max"       : 1.5,
        "decimals"  : 3,
        "state"     : "active",
        "source_tag": "hfsims",
        "description": (
            "Quality factor frequency exponent. BBP models Q(f) = Q0 × f^QFEXP. "
            "Controls how attenuation varies with frequency. "
            "0.6 = Q increases moderately with frequency (California). "
            "ENA stable crust typically uses ~0.5. "
            "Affects the spectral shape of synthetic seismograms."
        ),
    },
    {
        "key"       : "SDROP",
        "full_key"  : "CODEBASE_GP_SDROP",
        "label"     : "SDROP",
        "default"   : 50,
        "unit"      : "bars",
        "min"       : 10,
        "max"       : 500,
        "decimals"  : 0,
        "state"     : "absent",
        "source_tag": "hfsims",
        "description": (
            "Stress drop — difference in stress on fault before and after rupture. "
            "Controls HF energy radiated at the source. "
            "California active crust default: 50 bars. "
            "Eastern North America stable crust: typically 100–200 bars. "
            "Higher SDROP → more HF energy → higher PGA and PGV."
        ),
    },
    # ── Rupture generation parameters (genslip.py + hfsims.py) ──────
    {
        "key"       : "MEAN_RVFAC",
        "full_key"  : "CODEBASE_GP_MEAN_RVFAC",
        "label"     : "MEAN_RVFAC",
        "default"   : 0.775,
        "unit"      : "fraction of Vs",
        "min"       : 0.5,
        "max"       : 1.0,
        "decimals"  : 3,
        "state"     : "override",
        "source_tag": "genslip + hfsims",
        "description": (
            "Mean rupture velocity as a fraction of local shear-wave velocity Vs. "
            "0.775 means rupture travels at 77.5% of Vs. "
            "Higher → stronger directivity effects. "
            "Values > 1.0 produce supershear rupture (large strike-slip events). "
            "Used in sensitivity studies on directivity."
        ),
    },
    {
        "key"       : "RANGE_RVFAC",
        "full_key"  : "CODEBASE_GP_RANGE_RVFAC",
        "label"     : "RANGE_RVFAC",
        "default"   : 0.1,
        "unit"      : "fraction of Vs",
        "min"       : 0.0,
        "max"       : 0.5,
        "decimals"  : 3,
        "state"     : "override",
        "source_tag": "genslip + hfsims",
        "description": (
            "Half-width of uniform random distribution around MEAN_RVFAC. "
            "Rupture velocity per subfault is drawn from "
            "[MEAN_RVFAC - RANGE, MEAN_RVFAC + RANGE]. "
            "0.0 = deterministic, uniform rupture velocity (controlled experiments). "
            "Higher → more heterogeneous rupture, more realistic variability."
        ),
    },
    {
        "key"       : "RISETIME_COEF",
        "full_key"  : "CODEBASE_GP_RISETIME_COEF",
        "label"     : "RISETIME_COEF",
        "default"   : 2.3,
        "unit"      : "s / sqrt(km²)",
        "min"       : 0.5,
        "max"       : 5.0,
        "decimals"  : 2,
        "state"     : "override",
        "source_tag": "genslip",
        "description": (
            "Rise time coefficient. Rise time per subfault = RISETIME_COEF × sqrt(slip_area). "
            "Controls duration of slip at each subfault — smoothness of the source time function. "
            "Higher → longer rise times → more LF energy, less HF. "
            "Lower → shorter, more impulsive source → more HF content."
        ),
    },
]

# BBP default values as a quick-lookup dict  {key: default}
BBP_DEFAULTS = {p["key"]: p["default"] for p in PARAM_DEFS}


# ------------------------------------------------------------------
# MAIN PANEL
# ------------------------------------------------------------------

class AdvancedSettingsPanel(ctk.CTkToplevel):
    """
    Popup for viewing and editing BBP GP simulation parameters.
    Writes only to labasin500_velmodel_config.txt — never to BBP source files.
    """

    def __init__(self, master, model_name="LABasin500"):
        super().__init__(master)

        self.model_name  = model_name
        self._cfg_path   = (
            f"{WSLBridge.get_wsl_home()}/bbp_gf/"
            f"{model_name}/{model_name.lower()}_velmodel_config.txt"
        )

        # Live state: {key: {"value": float, "enabled": bool}}
        # "enabled" = True means the override line is active (uncommented or added)
        self._state = {}

        self.title(f"Advanced Simulation Settings — {model_name}")
        self.geometry("920x760")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self.after(200, self._on_ready)
        self.after(350, self._load_current_values)

    def _on_ready(self):
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):

        # --- TOP BAR ---
        top = ctk.CTkFrame(self, fg_color="#0d0d0d", corner_radius=0, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(
            top,
            text="Advanced Simulation Settings",
            font=(res.FONT_TITLE[0], 16, "bold"),
            text_color="white"
        ).pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            top,
            text=f"Editing: {self.model_name} velocity model config",
            font=(res.FONT_LABEL[0], 11),
            text_color="#888888"
        ).pack(side="right", padx=20, pady=14)

        # --- WARNING BANNER ---
        warn = ctk.CTkFrame(
            self,
            fg_color="#1a1200",
            border_width=1,
            border_color="#554400",
            corner_radius=0
        )
        warn.pack(fill="x")

        ctk.CTkLabel(
            warn,
            text=(
                "⚠  Changes are written to the velocity model config file and affect ALL "
                "future runs with this model until reset.  Use 'Reset to Defaults' to restore BBP values."
            ),
            font=(res.FONT_LABEL[0], 11),
            text_color="#ffdd88",
            wraplength=860,
            justify="left"
        ).pack(padx=16, pady=8, anchor="w")

        # --- SCROLLABLE CONTENT ---
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # --- SOURCE INFO ---
        info = ctk.CTkFrame(
            self._scroll,
            fg_color="#1e1e2e",
            border_width=1,
            border_color="#333355",
            corner_radius=6
        )
        info.pack(fill="x", padx=20, pady=(14, 6))

        ctk.CTkLabel(
            info,
            text="How BBP reads these parameters",
            font=(res.FONT_LABEL[0], 12, "bold"),
            text_color=res.COLOR_PRIMARY
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            info,
            text=(
                "BBP reads parameters from the velocity model config file at runtime. "
                "Active lines (uncommented) override BBP's built-in defaults. "
                "Commented lines (#) mean BBP uses the value from genslip_cfg.py / hfsims_cfg.py.\n"
                "KAPPA and QFEXP are already active for LABasin500. "
                "MEAN_RVFAC, RANGE_RVFAC, RISETIME_COEF are commented (BBP default applies). "
                "SDROP is absent from the config — enabling it adds the line."
            ),
            font=(res.FONT_LABEL[0], 11),
            text_color="#aaaaaa",
            wraplength=840,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # --- HF SYNTHESIS SECTION ---
        self._section_header(self._scroll, "HF Synthesis Parameters", "hfsims.py")
        self._param_widgets = {}

        for p in PARAM_DEFS:
            if p["source_tag"].startswith("hfsims"):
                self._build_param_row(self._scroll, p)

        # --- RUPTURE GENERATION SECTION ---
        self._section_header(
            self._scroll, "Rupture Generation Parameters", "genslip.py + hfsims.py"
        )

        for p in PARAM_DEFS:
            if p["source_tag"].startswith("genslip"):
                self._build_param_row(self._scroll, p)

        # --- STATUS LABEL ---
        self._lbl_status = ctk.CTkLabel(
            self._scroll,
            text="",
            font=(res.FONT_LABEL[0], 12),
            text_color=res.COLOR_SUCCESS,
            wraplength=860,
            justify="left"
        )
        self._lbl_status.pack(padx=20, pady=(6, 2))

        # --- BOTTOM BUTTONS ---
        btn_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(8, 20))

        ctk.CTkButton(
            btn_row,
            text="Reset ALL to BBP Defaults",
            width=200, height=38,
            fg_color="#3a1a00",
            border_width=1,
            border_color="#884400",
            hover_color="#4a2a00",
            text_color="#ffaa55",
            command=self._reset_all_defaults
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Close",
            width=100, height=38,
            fg_color="#333333",
            hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row,
            text="Save to Config File",
            width=180, height=38,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            command=self._save_all
        ).pack(side="right")

    def _section_header(self, parent, title, subtitle):
        """Styled section divider."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            f, text=title,
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white"
        ).pack(side="left")

        ctk.CTkLabel(
            f, text=f"  —  {subtitle}",
            font=(res.FONT_LABEL[0], 11),
            text_color="#555555"
        ).pack(side="left", pady=1)

        sep = ctk.CTkFrame(f, fg_color="#333333", height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)

    def _build_param_row(self, parent, p):
        """
        Builds one parameter row containing:
          - Enable checkbox (for override/absent params) or active badge
          - Label + unit + source tag
          - Slider
          - Entry box (linked to slider)
          - Reset-to-default button
          - Description text
        """
        key = p["key"]

        card = ctk.CTkFrame(
            parent,
            fg_color="#222222",
            border_width=1,
            border_color="#333333",
            corner_radius=6
        )
        card.pack(fill="x", padx=20, pady=4)

        # Top row: enable toggle + label + badges + entry + reset
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 4))

        # --- Enable toggle ---
        var_enabled = ctk.BooleanVar(value=(p["state"] == "active"))

        if p["state"] == "active":
            # Always active — show badge instead of checkbox
            ctk.CTkLabel(
                top_row,
                text="● ACTIVE",
                font=(res.FONT_LABEL[0], 10, "bold"),
                text_color=res.COLOR_SUCCESS,
                fg_color="#0a1f0a",
                corner_radius=4,
                padx=6, pady=2
            ).pack(side="left", padx=(0, 10))
        else:
            # override or absent — user controls activation
            chk = ctk.CTkCheckBox(
                top_row,
                text="Override BBP default",
                variable=var_enabled,
                font=(res.FONT_LABEL[0], 11),
                text_color="#aaaaaa",
                fg_color=res.COLOR_PRIMARY,
                hover_color="#004070",
                border_color="#555555",
                command=lambda k=key: self._on_toggle(k)
            )
            chk.pack(side="left", padx=(0, 10))

        # --- Parameter label ---
        ctk.CTkLabel(
            top_row,
            text=p["label"],
            font=(res.FONT_LABEL[0], 13, "bold"),
            text_color="white",
            width=160,
            anchor="w"
        ).pack(side="left")

        # --- Unit badge ---
        ctk.CTkLabel(
            top_row,
            text=p["unit"],
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        ).pack(side="left", padx=(0, 12))

        # --- Source tag ---
        ctk.CTkLabel(
            top_row,
            text=p["source_tag"],
            font=(res.FONT_LABEL[0], 9),
            text_color="#444488",
            fg_color="#111122",
            corner_radius=3,
            padx=5, pady=1
        ).pack(side="left", padx=(0, 14))

        # --- BBP default badge ---
        ctk.CTkLabel(
            top_row,
            text=f"BBP default: {p['default']}",
            font=(res.FONT_LABEL[0], 10),
            text_color="#666666"
        ).pack(side="left", padx=(0, 10))

        # --- Entry box (right side) ---
        var_entry = ctk.StringVar(value=str(p["default"]))
        entry = ctk.CTkEntry(
            top_row,
            textvariable=var_entry,
            width=90, height=30,
            font=("Courier", 12),
            fg_color="#111111",
            border_color="#444444",
            justify="center"
        )
        entry.pack(side="right", padx=(8, 0))

        # --- Reset button ---
        ctk.CTkButton(
            top_row,
            text="↺",
            width=30, height=30,
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            font=(res.FONT_LABEL[0], 14),
            command=lambda k=key, v=var_entry: self._reset_one(k, v)
        ).pack(side="right", padx=(4, 0))

        # --- Slider row ---
        slider_row = ctk.CTkFrame(card, fg_color="transparent")
        slider_row.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            slider_row,
            text=str(p["min"]),
            font=(res.FONT_LABEL[0], 9),
            text_color="#555555",
            width=40
        ).pack(side="left")

        slider = ctk.CTkSlider(
            slider_row,
            from_=p["min"],
            to=p["max"],
            number_of_steps=max(100, int((p["max"] - p["min"]) / 10**(-p["decimals"]))),
            fg_color="#333333",
            progress_color=res.COLOR_PRIMARY,
            button_color="#5599cc",
            button_hover_color="#77bbee",
            command=lambda val, k=key, v=var_entry, dec=p["decimals"]: self._on_slider(k, val, v, dec)
        )
        slider.set(p["default"])
        slider.pack(side="left", fill="x", expand=True, padx=8)

        ctk.CTkLabel(
            slider_row,
            text=str(p["max"]),
            font=(res.FONT_LABEL[0], 9),
            text_color="#555555",
            width=40,
            anchor="e"
        ).pack(side="left")

        # Sync entry → slider on Return/FocusOut
        entry.bind("<Return>",    lambda e, k=key, s=slider, v=var_entry, p=p: self._on_entry(k, s, v, p))
        entry.bind("<FocusOut>",  lambda e, k=key, s=slider, v=var_entry, p=p: self._on_entry(k, s, v, p))

        # --- Description ---
        ctk.CTkLabel(
            card,
            text=p["description"],
            font=(res.FONT_LABEL[0], 10),
            text_color="#777777",
            wraplength=840,
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Store widget references for later reads
        self._param_widgets[key] = {
            "var_enabled" : var_enabled,
            "var_entry"   : var_entry,
            "slider"      : slider,
            "card"        : card,
            "p"           : p,
        }

    # ------------------------------------------------------------------
    # WIDGET CALLBACKS
    # ------------------------------------------------------------------

    def _on_slider(self, key, val, var_entry, decimals):
        """Slider moved → update entry box."""
        fmt = f"{val:.{decimals}f}" if decimals > 0 else str(int(round(val)))
        var_entry.set(fmt)

    def _on_entry(self, key, slider, var_entry, p):
        """Entry changed → validate and update slider."""
        try:
            val = float(var_entry.get())
            val = max(p["min"], min(p["max"], val))
            slider.set(val)
            fmt = f"{val:.{p['decimals']}f}" if p["decimals"] > 0 else str(int(round(val)))
            var_entry.set(fmt)
        except ValueError:
            # Restore last valid value from slider
            var_entry.set(str(p["default"]))

    def _on_toggle(self, key):
        """Checkbox toggled — visually dim/brighten the card."""
        w = self._param_widgets[key]
        enabled = w["var_enabled"].get()
        w["slider"].configure(
            state="normal" if enabled else "disabled",
            button_color="#5599cc" if enabled else "#444444"
        )

    def _reset_one(self, key, var_entry):
        """Reset a single parameter to BBP default."""
        default = BBP_DEFAULTS[key]
        w = self._param_widgets[key]
        p = w["p"]
        fmt = f"{default:.{p['decimals']}f}" if p["decimals"] > 0 else str(int(round(default)))
        var_entry.set(fmt)
        w["slider"].set(default)

    def _reset_all_defaults(self):
        """Reset all parameters to BBP defaults and disable overrides."""
        for key, w in self._param_widgets.items():
            self._reset_one(key, w["var_entry"])
            p = w["p"]
            # Only reset enable state for override/absent params
            if p["state"] != "active":
                w["var_enabled"].set(False)
                self._on_toggle(key)
        self._lbl_status.configure(
            text="All values reset to BBP defaults. Click 'Save to Config File' to apply.",
            text_color="#ffaa55"
        )

    # ------------------------------------------------------------------
    # LOAD CURRENT VALUES FROM WSL
    # ------------------------------------------------------------------

    def _load_current_values(self):
        """
        Reads the current velmodel config file from WSL and populates
        the widgets with whatever is currently active.
        """
        params = WSLBridge.read_advanced_params(self._cfg_path)
        if not params:
            self._lbl_status.configure(
                text=f"Could not read config file: {self._cfg_path}",
                text_color=res.COLOR_ERROR
            )
            return

        for key, w in self._param_widgets.items():
            p      = w["p"]
            result = params.get(key)   # {"value": float, "enabled": bool} or None

            if result is None:
                # Line absent — use BBP default, leave disabled
                continue

            val     = result["value"]
            enabled = result["enabled"]

            # Update entry and slider
            fmt = f"{val:.{p['decimals']}f}" if p["decimals"] > 0 else str(int(round(val)))
            w["var_entry"].set(fmt)
            w["slider"].set(val)

            # Update enable state for override/absent params
            if p["state"] != "active":
                w["var_enabled"].set(enabled)
                self._on_toggle(key)

        self._lbl_status.configure(
            text="Current values loaded from config file.",
            text_color="#888888"
        )

    # ------------------------------------------------------------------
    # SAVE TO WSL
    # ------------------------------------------------------------------

    def _save_all(self):
        """
        Reads current widget values, builds the params dict, and
        calls WSLBridge.write_advanced_params() to update the config file.
        Shows a confirmation before writing.
        """
        # Build params dict from widgets
        params = {}
        for key, w in self._param_widgets.items():
            p = w["p"]
            try:
                val = float(w["var_entry"].get())
                val = max(p["min"], min(p["max"], val))
            except ValueError:
                val = p["default"]

            enabled = w["var_enabled"].get()
            params[key] = {"value": val, "enabled": enabled}

        # Show confirmation dialog
        self._show_confirm(params)

    def _show_confirm(self, params):
        """Shows a confirmation popup before writing to disk."""
        win = ctk.CTkToplevel(self)
        win.title("Confirm Save")
        win.geometry("520x400")
        win.configure(fg_color="#1a1a1a")
        win.transient(self)
        win.grab_set()
        win.lift()

        ctk.CTkLabel(
            win,
            text="Confirm: Write to Config File",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color="white"
        ).pack(pady=(20, 6), padx=20)

        ctk.CTkLabel(
            win,
            text=(
                f"This will modify:\n{self._cfg_path}\n\n"
                "Changes affect ALL future runs with this model until reset.\n"
                "The following values will be written:"
            ),
            font=(res.FONT_LABEL[0], 11),
            text_color="#aaaaaa",
            wraplength=480,
            justify="left"
        ).pack(padx=20, anchor="w")

        # Summary of changes
        summary_frame = ctk.CTkFrame(win, fg_color="#111111", corner_radius=6)
        summary_frame.pack(fill="x", padx=20, pady=8)

        for key, info in params.items():
            w    = self._param_widgets[key]
            p    = w["p"]
            val  = info["value"]
            enab = info["enabled"]
            fmt  = f"{val:.{p['decimals']}f}" if p["decimals"] > 0 else str(int(round(val)))

            if p["state"] == "active":
                state_str = f"  ← set to {fmt}"
                color     = "white"
            elif enab:
                state_str = f"  ← OVERRIDE ENABLED = {fmt}"
                color     = res.COLOR_SUCCESS
            else:
                state_str = "  ← BBP default (commented out)"
                color     = "#555555"

            ctk.CTkLabel(
                summary_frame,
                text=f"  {p['full_key']}{state_str}",
                font=("Courier", 10),
                text_color=color,
                anchor="w"
            ).pack(anchor="w", padx=10, pady=2)

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(12, 20))

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100, height=36,
            fg_color="#333333",
            command=win.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Confirm Save",
            width=140, height=36,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            command=lambda: self._do_save(params, win)
        ).pack(side="right")

    def _do_save(self, params, confirm_win):
        """Performs the actual write after user confirms."""
        confirm_win.destroy()

        ok, msg = WSLBridge.write_advanced_params(self._cfg_path, params)

        if ok:
            # Update AppConfig so simulation knows advanced params are active
            AppConfig.advanced_params_active = True
            AppConfig.advanced_params        = {k: v["value"] for k, v in params.items()}

            self._lbl_status.configure(
                text=f"✓ Saved successfully to {self._cfg_path}",
                text_color=res.COLOR_SUCCESS
            )
        else:
            self._lbl_status.configure(
                text=f"✗ Save failed: {msg}",
                text_color=res.COLOR_ERROR
            )