import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res


class ModuleCard(ctk.CTkFrame):
    """
    A dashboard card representing one BBP simulation method.
    is_enabled=True  → colored border + Configure button
    is_enabled=False → gray border + Locked button (disabled)
    color            → accent color when enabled (default: teal COLOR_PRIMARY)
    """
    def __init__(self, master, number, title, subtitle,
                 desc, is_enabled=False, command=None, color=None):
        _color = color if (color and is_enabled) else \
                 (res.COLOR_PRIMARY if is_enabled else "#333333")
        _hover = "#004070"
        if color and is_enabled:
            # Darken the color slightly for hover
            _hover = color

        super().__init__(
            master,
            corner_radius=10,
            border_width=2,
            fg_color="#1a1a1a" if is_enabled else "#141414"
        )
        self.configure(border_color=_color)

        # Top accent bar
        accent = ctk.CTkFrame(
            self,
            fg_color=_color,
            height=4, corner_radius=0
        )
        accent.pack(fill="x")

        # Number badge
        ctk.CTkLabel(
            self,
            text=number,
            font=(res.FONT_LABEL[0], 10),
            text_color=_color
        ).pack(anchor="w", padx=14, pady=(10, 0))

        # Title
        ctk.CTkLabel(
            self,
            text=title,
            font=(res.FONT_LABEL[0], 15, "bold"),
            text_color="white" if is_enabled else "#555555",
            wraplength=200,
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=14, pady=(2, 0))

        # Subtitle
        ctk.CTkLabel(
            self,
            text=subtitle,
            font=(res.FONT_LABEL[0], 10),
            text_color=_color,
            anchor="w"
        ).pack(anchor="w", padx=14, pady=(0, 6))

        # Description
        ctk.CTkLabel(
            self,
            text=desc,
            font=(res.FONT_LABEL[0], 10),
            text_color="#888888" if is_enabled else "#333333",
            wraplength=200,
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=14, pady=(0, 12), fill="x")

        # Action button
        btn_text  = "Configure" if is_enabled else "Coming Soon"
        btn_color = _color if is_enabled else "#222222"
        self.btn  = ctk.CTkButton(
            self,
            text=btn_text,
            height=32,
            fg_color=btn_color,
            hover_color=_hover,
            text_color="white" if is_enabled else "#444444",
            state="normal" if is_enabled else "disabled",
            command=command
        )
        self.btn.pack(pady=(0, 14), padx=14, fill="x")


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master,
                 open_gp_callback=None,
                 open_exsim_callback=None,
                 open_irikura1_callback=None,
                 open_song_callback=None,
                 open_results_callback=None,
                 open_config_callback=None,
                 open_validation_callback=None,
                 open_rupture_generator_callback=None):
        super().__init__(master, fg_color="transparent")

        self._open_results_callback           = open_results_callback
        self._open_config_callback            = open_config_callback
        self._open_validation_callback        = open_validation_callback
        self._open_rupture_generator_callback = open_rupture_generator_callback

        # --- TOP BAR: title left, buttons right ---
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(20, 0))

        title_left = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_left.pack(side="left")

        ctk.CTkLabel(
            title_left,
            text="BBP Modular Interface — Method Selection",
            font=res.FONT_TITLE,
            text_color="white"
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_left,
            text="SCEC Broadband Platform v22.4.0  —  Select a simulation method to configure",
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        ).pack(anchor="w", pady=(2, 0))

        # Right side buttons
        btn_right = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_right.pack(side="right")

        ctk.CTkButton(
            btn_right,
            text="⚙  Velocity Models",
            width=160, height=36,
            fg_color="transparent",
            border_width=1, border_color="#444444",
            text_color="#aaaaaa",
            hover_color="#2a2a2a",
            font=(res.FONT_LABEL[0], 12),
            command=self._open_config
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_right,
            text="✓  Validation",
            width=130, height=36,
            fg_color="transparent",
            border_width=1, border_color="#7a6a00",
            text_color="#ffdd00",
            hover_color="#1a1600",
            font=(res.FONT_LABEL[0], 12),
            command=self._open_validation
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_right,
            text="Rupture Generator",
            width=170, height=36,
            fg_color="transparent",
            border_width=1, border_color="#aaaaaa",
            text_color="white",
            hover_color="#2a2a2a",
            font=(res.FONT_LABEL[0], 12),
            command=self._open_rupture_generator
        ).pack(side="right", padx=(8, 0))

        # --- CARD GRID: 4 columns ---
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20, pady=(12, 0))

        for col in range(4):
            grid.grid_columnconfigure(col, weight=1)
        for row in range(2):
            grid.grid_rowconfigure(row, weight=1)

        # --- METHOD CARDS ---
        # (row, col, number, title, subtitle, desc, enabled, command, color)
        cards = [
            (0, 0, "Method 1", "Graves & Pitarka", "GP — Broadband",
             "Deterministic LF + stochastic HF synthesis. Full pipeline with rupture generation, seismograms, spectra and reports.",
             True,  open_gp_callback,         None),
            (0, 1, "Method 2", "UCSB", "University of California Santa Barbara",
             "Broadband simulation using the UCSB method by Crempien & Archuleta (2015). LF + HF synthesis.",
             False, None,                      None),
            (0, 2, "Method 3", "SDSU", "San Diego State University",
             "Broadband simulation using the SDSU method by Olsen & Takedatsu (2015). LF + HF synthesis.",
             False, None,                      None),
            (0, 3, "Method 4", "EXSIM", "Stochastic — Boore (2003)",
             "Stochastic broadband simulation using the ExSIM code. Generates broadband directly without LF/HF split.",
             True,  open_exsim_callback,       "#ffaa44"),
            (1, 0, "Method 5", "Song RMG", "Pseudo-dynamic Rupture Generator",
             "Pseudo-dynamic rupture model generator by Song (SongRMGSS). Single-segment ruptures — LF + HF synthesis on the GP codebase.",
             True,  open_song_callback,       "#8855cc"),
            (1, 1, "Method 6", "Irikura Recipe 1", "Irikura & Miyake (2011)",
             "Broadband simulation using Irikura Recipe Method 1. LF + HF synthesis with recipe-based source parameters.",
             True,  open_irikura1_callback,    "#22aa55"),
            (1, 2, "Method 7", "Irikura Recipe 2", "Kamae et al. (1998)",
             "Broadband simulation using Irikura Recipe Method 2. Alternative recipe formulation for source characterization.",
             False, None,                      None),
            (1, 3, "Results", "Results Viewer", "All simulation runs",
             "Browse all past simulation runs. View seismograms, response spectra, Fourier spectra, station maps and reports.",
             True,  self._open_results_history, "#888888"),
        ]

        for row, col, number, title, subtitle, desc, enabled, cmd, color in cards:
            ModuleCard(
                grid,
                number=number, title=title, subtitle=subtitle, desc=desc,
                is_enabled=enabled, command=cmd, color=color
            ).grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def _open_results_history(self):
        if self._open_results_callback:
            self._open_results_callback()

    def _open_config(self):
        if self._open_config_callback:
            self._open_config_callback()

    def _open_validation(self):
        if self._open_validation_callback:
            self._open_validation_callback()

    def _open_rupture_generator(self):
        if self._open_rupture_generator_callback:
            self._open_rupture_generator_callback()