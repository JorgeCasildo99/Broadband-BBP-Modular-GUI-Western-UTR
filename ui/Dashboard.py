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
    is_enabled=True  → teal border + Configure button
    is_enabled=False → gray border + Locked button (disabled)
    """
    def __init__(self, master, number, title, subtitle,
                 desc, is_enabled=False, command=None):
        super().__init__(
            master,
            corner_radius=10,
            border_width=2,
            fg_color="#1a1a1a" if is_enabled else "#141414"
        )
        self.configure(
            border_color=res.COLOR_PRIMARY if is_enabled else "#333333"
        )

        # Top accent bar
        accent = ctk.CTkFrame(
            self,
            fg_color=res.COLOR_PRIMARY if is_enabled else "#2a2a2a",
            height=4, corner_radius=0
        )
        accent.pack(fill="x")

        # Number badge
        ctk.CTkLabel(
            self,
            text=number,
            font=(res.FONT_LABEL[0], 10),
            text_color=res.COLOR_PRIMARY if is_enabled else "#444444"
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

        # Subtitle (method abbreviation)
        ctk.CTkLabel(
            self,
            text=subtitle,
            font=(res.FONT_LABEL[0], 10),
            text_color=res.COLOR_PRIMARY if is_enabled else "#333333",
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
        btn_color = res.COLOR_PRIMARY if is_enabled else "#222222"
        self.btn  = ctk.CTkButton(
            self,
            text=btn_text,
            height=32,
            fg_color=btn_color,
            hover_color="#004070" if is_enabled else "#222222",
            text_color="white" if is_enabled else "#444444",
            state="normal" if is_enabled else "disabled",
            command=command
        )
        self.btn.pack(pady=(0, 14), padx=14, fill="x")


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master,
                 open_gp_callback=None,
                 open_results_callback=None):
        super().__init__(master, fg_color="transparent")

        self._open_results_callback = open_results_callback

        # --- TITLE ---
        ctk.CTkLabel(
            self,
            text="BBP Modular Interface — Method Selection",
            font=res.FONT_TITLE,
            text_color="white"
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            self,
            text="SCEC Broadband Platform v22.4.0  —  Select a simulation method to configure",
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        ).pack(pady=(0, 16))

        # --- CARD GRID: 4 columns ---
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20)

        for col in range(4):
            grid.grid_columnconfigure(col, weight=1)
        for row in range(2):
            grid.grid_rowconfigure(row, weight=1)

        # --- METHOD CARDS ---
        cards = [
            # (row, col, number, title, subtitle, desc, enabled, command)
            (0, 0,
             "Method 1",
             "Graves & Pitarka",
             "GP — Broadband",
             "Deterministic LF + stochastic HF synthesis. Full pipeline with rupture generation, seismograms, spectra and reports.",
             True,
             open_gp_callback),

            (0, 1,
             "Method 2",
             "UCSB",
             "University of California Santa Barbara",
             "Broadband simulation using the UCSB method by Crempien & Archuleta (2015). LF + HF synthesis.",
             False,
             None),

            (0, 2,
             "Method 3",
             "SDSU",
             "San Diego State University",
             "Broadband simulation using the SDSU method by Olsen & Takedatsu (2015). LF + HF synthesis.",
             False,
             None),

            (0, 3,
             "Method 4",
             "EXSIM",
             "Stochastic — Boore (2003)",
             "Stochastic broadband simulation using the ExSIM code. Generates broadband directly without LF/HF split.",
             False,
             None),

            (1, 0,
             "Method 5",
             "Song RMG",
             "Pseudo-dynamic Rupture Generator",
             "Pseudo-dynamic rupture model generator by Song. Supports single-segment and multi-segment ruptures.",
             False,
             None),

            (1, 1,
             "Method 6",
             "Irikura Recipe 1",
             "Irikura & Miyake (2011)",
             "Broadband simulation using Irikura Recipe Method 1. LF + HF synthesis with recipe-based source parameters.",
             False,
             None),

            (1, 2,
             "Method 7",
             "Irikura Recipe 2",
             "Kamae et al. (1998)",
             "Broadband simulation using Irikura Recipe Method 2. Alternative recipe formulation for source characterization.",
             False,
             None),

            (1, 3,
             "Results",
             "Results Viewer",
             "All simulation runs",
             "Browse all past simulation runs. View seismograms, response spectra, Fourier spectra, station maps and reports.",
             True,
             self._open_results_history),
        ]

        for row, col, number, title, subtitle, desc, enabled, cmd in cards:
            ModuleCard(
                grid,
                number=number,
                title=title,
                subtitle=subtitle,
                desc=desc,
                is_enabled=enabled,
                command=cmd
            ).grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def _open_results_history(self):
        if self._open_results_callback:
            self._open_results_callback()