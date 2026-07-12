"""
GenslipPanel.py
===============
Popup panel that generates a Genslip (GP Rupture Only) run using the
fault geometry already set in ExSimPanel, extracts the slip distribution
from the resulting .srf file, and auto-fills the ExSIM islipweight fields.

Located at:  ui/ExSIM/GenslipPanel.py
"""

import customtkinter as ctk
import threading
import os

from core.WSLBridge   import WSLBridge
from core.AppConfig   import AppConfig
from core.XMLGenerator import save_xml
import core.Resources as res


class GenslipPanel(ctk.CTkToplevel):
    """
    A self-contained popup that:

      1. Displays the fault geometry read from ExSimPanel (read-only).
      2. On "Run Genslip", writes a minimal .src + .stl to WSL and runs
         BBP with the Rupture Only pipeline (Genslip only — no wave propagation).
      3. Tracks progress with a progress bar (3 stages):
            Stage 1 — Running Genslip via BBP
            Stage 2 — Locating the .srf output file
            Stage 3 — Extracting and normalizing slip weights
      4. On completion, calls on_done(slip_weights_path, dl, dw) so
         ExSimPanel can auto-fill islipweight fields.

    Args:
        master          : parent Tk window
        params          : dict of fault geometry pulled from ExSimPanel src_inputs
        stations        : list of (lon, lat, name) tuples from ExSimPanel
        experimenter    : str — experimenter name from ExSimPanel
        exp_name        : str — experiment name from ExSimPanel
        dlen            : str — DLEN/dl value from ExSimPanel
        dwid            : str — DWID/dw value from ExSimPanel
        seed            : str — SEED value
        on_done         : callable(slip_weights_path, dl, dw)
    """

    # Progress stage fractions
    _STAGE_BBP   = 0.60   # BBP run takes most of the time
    _STAGE_FIND  = 0.80   # locating srf
    _STAGE_PARSE = 1.00   # extracting slip

    def __init__(self, master, params, stations, experimenter,
                 exp_name, dlen, dwid, seed, on_done):
        super().__init__(master)

        self._params       = params
        self._stations     = stations
        self._experimenter = experimenter
        self._exp_name     = exp_name
        self._dlen         = dlen
        self._dwid         = dwid
        self._seed         = seed
        self._on_done      = on_done
        self._running      = False

        # Auto-generated run name so the session is easily identifiable
        clean_user = experimenter.replace(" ", "_")
        clean_exp  = exp_name.replace(" ", "_")
        self._base_name = f"{clean_user}_{clean_exp}_just_Genslip"

        self.title("Generate islipweight — Genslip Runner")
        self.geometry("680x640")
        self.configure(fg_color="#1a1a1a")
        self.resizable(False, False)
        self.transient(master)

        self._build_ui()

        # Center relative to parent
        self.update_idletasks()
        px = master.winfo_rootx()
        py = master.winfo_rooty()
        pw = master.winfo_width()
        ph = master.winfo_height()
        w, h = 680, 640
        self.geometry(f"{w}x{h}+{px + (pw-w)//2}+{py + (ph-h)//2}")

        self.deiconify()
        self.lift()
        self.focus_force()
        self.after(120, self.grab_set)

    # ------------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Builds the full popup UI."""

        # ── HEADER ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="Generate islipweight file",
            font=(res.FONT_LABEL[0], 15, "bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=14)

        ctk.CTkLabel(
            hdr,
            text=f"Run: {self._base_name}",
            font=(res.FONT_LABEL[0], 10),
            text_color="#888888"
        ).pack(side="right", padx=16, pady=14)

        # ── PURPOSE EXPLANATION ────────────────────────────────────────
        info_frame = ctk.CTkFrame(self, fg_color="#1a2a1a",
                                   border_width=1, border_color="#2a4a2a",
                                   corner_radius=6)
        info_frame.pack(fill="x", padx=14, pady=(10, 6))

        ctk.CTkLabel(
            info_frame,
            text=(
                "This panel runs Genslip (GP Rupture Only) using the fault geometry "
                "already set in the ExSIM panel. It does NOT compute ground motion — "
                "it only generates a deterministic slip distribution on the fault plane.\n\n"
                "The resulting slip pattern is extracted from the .srf file, normalized "
                "to relative weights (0–1), and written as a plain text file. That file "
                "is then automatically loaded into the ExSIM islipweight field so both "
                "ExSIM and Genslip use the same source model — removing slip distribution "
                "as a variable in the comparison with Sanaz's SW4 results."
            ),
            font=(res.FONT_LABEL[0], 10),
            text_color="#aaccaa",
            wraplength=620,
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=10)

        # ── FAULT GEOMETRY SUMMARY ─────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Fault Parameters (read from ExSIM panel)",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=16, pady=(8, 2))

        geo_frame = ctk.CTkFrame(self, fg_color="#222222",
                                   border_width=1, border_color="#333",
                                   corner_radius=6)
        geo_frame.pack(fill="x", padx=14, pady=(0, 6))

        # Display key geometry params in two columns
        geo_items = [
            ("Magnitude",     self._params.get("MAGNITUDE",      "—")),
            ("Fault Length",  self._params.get("FAULT_LENGTH",   "—") + " km"),
            ("Fault Width",   self._params.get("FAULT_WIDTH",    "—") + " km"),
            ("Depth to Top",  self._params.get("DEPTH_TO_TOP",   "—") + " km"),
            ("Strike",        self._params.get("STRIKE",         "—") + "°"),
            ("Dip",           self._params.get("DIP",            "—") + "°"),
            ("Rake",          self._params.get("RAKE",           "—") + "°"),
            ("Hypo Stk",      self._params.get("HYPO_ALONG_STK","—") + " km"),
            ("Hypo Dip",      self._params.get("HYPO_DOWN_DIP",  "—") + " km"),
            ("SEED",          self._seed),
            ("DLEN / DWID",   f"{self._dlen} km / {self._dwid} km"),
            ("Stations",      f"{len(self._stations)} station(s) from ExSIM panel"),
        ]

        col_frames = [
            ctk.CTkFrame(geo_frame, fg_color="transparent"),
            ctk.CTkFrame(geo_frame, fg_color="transparent"),
        ]
        col_frames[0].pack(side="left", fill="both", expand=True, padx=8, pady=6)
        col_frames[1].pack(side="left", fill="both", expand=True, padx=8, pady=6)

        for i, (label, value) in enumerate(geo_items):
            col = col_frames[i % 2]
            row = ctk.CTkFrame(col, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"{label}:",
                         font=(res.FONT_LABEL[0], 10, "bold"),
                         text_color="#aaaaaa", anchor="w", width=90
                         ).pack(side="left")
            ctk.CTkLabel(row, text=value,
                         font=("Courier", 10),
                         text_color="white", anchor="w"
                         ).pack(side="left")

        # ── PROGRESS SECTION ───────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Progress",
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="#ffaa44",
            anchor="w"
        ).pack(anchor="w", padx=16, pady=(8, 2))

        prog_frame = ctk.CTkFrame(self, fg_color="#222222",
                                    border_width=1, border_color="#333",
                                    corner_radius=6)
        prog_frame.pack(fill="x", padx=14, pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(prog_frame, height=18)
        self.progress_bar.pack(fill="x", padx=12, pady=(12, 6))
        self.progress_bar.set(0)

        self.lbl_stage = ctk.CTkLabel(
            prog_frame,
            text="Ready — click Run Genslip to start",
            font=(res.FONT_LABEL[0], 10),
            text_color="#888888"
        )
        self.lbl_stage.pack(anchor="w", padx=12, pady=(0, 10))

        # ── BUTTONS ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(4, 14))

        ctk.CTkButton(
            btn_row, text="Cancel",
            width=100, height=36,
            fg_color="#333333", hover_color="#444444",
            command=self._cancel
        ).pack(side="right", padx=(6, 0))

        self.btn_run = ctk.CTkButton(
            btn_row,
            text="▶  Run Genslip",
            width=160, height=36,
            fg_color="#1a4a1a", hover_color="#2a6a2a",
            text_color="#88dd88",
            font=(res.FONT_LABEL[0], 12, "bold"),
            command=self._run
        )
        self.btn_run.pack(side="right")

    # ------------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------------

    def _cancel(self):
        if not self._running:
            self.destroy()

    def _set_progress(self, value, msg, color="#888888"):
        """Thread-safe progress update."""
        self.after(0, lambda: self._apply_progress(value, msg, color))

    def _apply_progress(self, value, msg, color):
        self.progress_bar.set(value)
        self.lbl_stage.configure(text=msg, text_color=color)

    def _run(self):
        """Validates then kicks off the Genslip run in a background thread."""
        if self._running:
            return

        # Validate base name
        if not self._base_name.strip():
            self._set_progress(0, "Error: run name is empty.", res.COLOR_ERROR)
            return

        self._running = True
        self.btn_run.configure(state="disabled", text="Running…")

        thread = threading.Thread(target=self._run_thread, daemon=True)
        thread.start()

    def _run_thread(self):
        """Background thread — runs Genslip, finds .srf, extracts slip."""
        import time

        # ── STAGE 1: Write .src and .stl, generate XML, run BBP ──────
        self._set_progress(0.05, "Stage 1/3 — Writing source files…")

        home = WSLBridge.get_wsl_home()
        bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{home}/bbp_data"

        # Build .src content (same format as ExSimPanel)
        src_lines = [f"# EXPERIMENTER: {self._experimenter}\n"]
        for k, v in self._params.items():
            src_lines.append(f"{k} = {v}\n")
        src_lines.append(f"DLEN = {self._dlen}\n")
        src_lines.append(f"DWID = {self._dwid}\n")
        src_lines.append(f"SEED = {self._seed}\n")
        src_lines.append("# METHOD = GP\n")
        src_content = "".join(src_lines)

        # Build .stl content — use ExSIM stations (real coords)
        stl_content = "".join(
            f"{lon:.5f}  {lat:.5f}  {name}\n"
            for lon, lat, name in self._stations
        )

        # Derive WSL session paths from AppConfig
        session_folder = AppConfig.current_session_folder or f"{home}/bbp_projects/genslip_tmp"
        src_dir  = AppConfig.src_path  if hasattr(AppConfig, "src_path")  else f"{session_folder}/src"
        stl_dir  = AppConfig.stl_path  if hasattr(AppConfig, "stl_path")  else f"{session_folder}/stl"

        # Ensure dirs exist
        WSLBridge.run_command(f"mkdir -p '{src_dir}' '{stl_dir}'")

        src_wsl = f"{src_dir}/{self._base_name}.src"
        stl_wsl = f"{stl_dir}/{self._base_name}.stl"

        ok, err = WSLBridge.write_wsl_file(src_wsl, src_content)
        if not ok:
            self._finish_error(f"Could not write .src: {err}")
            return

        ok, err = WSLBridge.write_wsl_file(stl_wsl, stl_content)
        if not ok:
            self._finish_error(f"Could not write .stl: {err}")
            return

        # Set AppConfig so XMLGenerator knows what to use
        AppConfig.current_src_file  = src_wsl
        AppConfig.current_stl_file  = stl_wsl
        AppConfig.current_base_name = self._base_name
        AppConfig.simulation_profile = "rupture"
        AppConfig.simulation_method  = "GP"

        # Generate XML
        self._set_progress(0.10, "Stage 1/3 — Generating XML…")
        ok, xml_result = save_xml(
            self._base_name,
            src_wsl,
            stl_wsl,
            profile="rupture",
            custom_modules=None,
            method="GP"
        )
        if not ok:
            self._finish_error(f"XML generation failed: {xml_result}")
            return

        xml_path = xml_result
        self._set_progress(0.15, "Stage 1/3 — Running Genslip via BBP…")

        # Run BBP (blocking in this thread)
        run_success = [False]
        run_error   = [""]
        run_id_out  = [""]
        done_event  = threading.Event()

        out_path = AppConfig.out_path if hasattr(AppConfig, "out_path") \
                   else f"{session_folder}/output"
        WSLBridge.run_command(f"mkdir -p '{out_path}'")

        def _on_finish(success, err_msg, run_id):
            run_success[0] = success
            run_error[0]   = err_msg
            run_id_out[0]  = run_id
            done_event.set()

        # Pulse progress while BBP runs
        WSLBridge.run_bbp_simulation_stream(
            xml_path            = xml_path,
            session_output_path = out_path,
            on_output           = lambda line: None,  # suppress console
            on_finish           = _on_finish
        )

        # Animate progress bar while waiting
        progress = 0.15
        while not done_event.is_set():
            progress = min(progress + 0.005, self._STAGE_BBP - 0.02)
            self._set_progress(progress, "Stage 1/3 — Running Genslip via BBP…")
            time.sleep(0.3)

        if not run_success[0]:
            self._finish_error(f"BBP failed: {run_error[0]}")
            return

        run_id = run_id_out[0]
        self._set_progress(self._STAGE_BBP, "Stage 1/3 — Genslip complete ✓")
        time.sleep(0.3)

        # ── STAGE 2: Locate the .srf file ────────────────────────────
        self._set_progress(self._STAGE_BBP + 0.02, "Stage 2/3 — Locating .srf file…")

        srf_path = ""
        if run_id:
            r = WSLBridge.run_command(
                f"find '{bbp_data}/outdata/{run_id}' -name '*.srf' 2>/dev/null | head -1"
            )
            srf_path = r.stdout.strip()

        if not srf_path:
            # Fallback: search session output
            r = WSLBridge.run_command(
                f"find '{out_path}' -name '*.srf' 2>/dev/null | head -1"
            )
            srf_path = r.stdout.strip()

        if not srf_path:
            self._finish_error(
                "Could not locate .srf file in BBP output.\n"
                f"Run ID: {run_id}\nExpected in: {bbp_data}/outdata/{run_id}/"
            )
            return

        self._set_progress(self._STAGE_FIND, f"Stage 2/3 — Found: {srf_path.rsplit('/', 1)[-1]} ✓")
        time.sleep(0.3)

        # ── STAGE 3: Extract and normalize slip weights ───────────────
        self._set_progress(self._STAGE_FIND + 0.02, "Stage 3/3 — Reading .srf file…")

        ok, srf_content = WSLBridge.read_wsl_file(srf_path)
        if not ok or not srf_content:
            self._finish_error(f"Could not read .srf file:\n{srf_path}")
            return

        self._set_progress(self._STAGE_FIND + 0.08, "Stage 3/3 — Extracting slip distribution…")

        try:
            nstk, ndip, slip_values = self._parse_srf_slip(srf_content)
        except Exception as e:
            self._finish_error(f"SRF parse error:\n{e}")
            return

        max_slip = max(slip_values) if slip_values else 0
        if max_slip == 0:
            self._finish_error("All slip values are zero — cannot normalize.")
            return

        normalized   = [v / max_slip for v in slip_values]
        srf_dir      = "/".join(srf_path.rsplit("/", 1)[:-1])
        srf_base     = os.path.splitext(srf_path.rsplit("/", 1)[-1])[0]
        weights_path = f"{srf_dir}/{srf_base}_slip_weights.txt"

        file_content = "".join(f"{v:.6f}\n" for v in normalized)
        ok_w, err_w  = WSLBridge.write_wsl_file(weights_path, file_content)
        if not ok_w:
            self._finish_error(f"Could not write slip weights file:\n{err_w}")
            return

        # Compute dl/dw from SRF grid
        try:
            fault_len = float(self._params.get("FAULT_LENGTH", "0"))
            fault_wid = float(self._params.get("FAULT_WIDTH",  "0"))
            dl_out = round(fault_len / nstk, 4) if nstk else float(self._dlen)
            dw_out = round(fault_wid / ndip, 4) if ndip else float(self._dwid)
        except (ValueError, ZeroDivisionError):
            dl_out = float(self._dlen)
            dw_out = float(self._dwid)

        self._set_progress(1.0, "Stage 3/3 — Done ✓", "#88dd88")
        time.sleep(0.5)

        # ── DONE: call back to ExSimPanel ─────────────────────────────
        self.after(0, lambda: self._finish_success(
            weights_path, dl_out, dw_out, len(normalized), nstk, ndip
        ))

    def _finish_success(self, weights_path, dl, dw, n_vals, nstk, ndip):
        """Called on the main thread after successful extraction."""
        import tkinter.messagebox as mb
        fname = weights_path.rsplit("/", 1)[-1]
        mb.showinfo(
            "islipweight Generated",
            f"Slip weights file ready:\n\n"
            f"{fname}\n\n"
            f"{n_vals} subfaults ({nstk} along strike × {ndip} down dip)\n"
            f"DL={dl} km  DW={dw} km\n\n"
            "ExSIM panel has been updated automatically.",
            parent=self
        )
        if self._on_done:
            self._on_done(weights_path, dl, dw)
        self.destroy()

    def _finish_error(self, msg):
        """Called from background thread on error."""
        self.after(0, lambda: self._apply_error(msg))

    def _apply_error(self, msg):
        import tkinter.messagebox as mb
        self._running = False
        self.btn_run.configure(state="normal", text="▶  Run Genslip")
        self._set_progress(0, f"Error — {msg[:60]}…", res.COLOR_ERROR)
        mb.showerror("Genslip Error", msg, parent=self)

    # ------------------------------------------------------------------
    # SRF PARSER (same logic as ExSimPanel._parse_srf_slip)
    # ------------------------------------------------------------------

    def _parse_srf_slip(self, srf_content):
        """
        Parses PEAK1 values from Line B of each SRF POINT block.
        Returns (nstk, ndip, slip_values).
        """
        lines = srf_content.splitlines()
        nstk = ndip = None
        slip_values = []
        in_points = False
        prev_was_A = False

        for raw in lines:
            parts = raw.strip().split()
            if not parts:
                continue

            if not in_points and len(parts) == 6:
                try:
                    nt = int(parts[2])
                    nd = int(parts[3])
                    if 1 <= nt <= 1000 and 1 <= nd <= 1000:
                        nstk, ndip = nt, nd
                except (ValueError, IndexError):
                    pass

            if raw.strip().startswith("POINTS"):
                in_points = True
                continue

            if not in_points:
                continue

            if len(parts) == 10:
                prev_was_A = True
            elif len(parts) == 7 and prev_was_A:
                slip_values.append(float(parts[1]))
                prev_was_A = False
            else:
                prev_was_A = False

        if nstk is None or ndip is None:
            raise ValueError("Could not read PLANE header (nstk, ndip).")
        if len(slip_values) != nstk * ndip:
            raise ValueError(
                f"Expected {nstk * ndip} slip values ({nstk}×{ndip}), "
                f"got {len(slip_values)}."
            )

        return nstk, ndip, slip_values