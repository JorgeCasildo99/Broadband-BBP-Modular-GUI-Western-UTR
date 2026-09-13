# ResultsHistoryPanel.py — ui/ResultsHistoryPanel.py
# -------------------------------------------------------
# Session history browser. Lists all past bbp_projects
# sessions, marks which ones have completed simulation
# results and which don't. Clicking a completed session
# loads it into AppConfig and opens ResultsPanel.
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge
from ui.results.ComparisonPanel import ComparisonPanel


class ResultsHistoryPanel(ctk.CTkToplevel):
    """
    Full window showing all past BBP simulation sessions.
    Each session shows its status (complete/incomplete),
    experiment name, date, and run ID if available.
    Clicking a completed session opens the ResultsPanel.
    """

    def __init__(self, master, on_open_results=None, on_edit_run=None):
        super().__init__(master)

        self._on_open_results = on_open_results
        self._on_edit_run     = on_edit_run
        self._sessions        = []

        self.title("BBP Session History")
        self.geometry("1100x700")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self.after(200, self._on_ready)
        self.after(400, self._load_sessions)

    def _on_ready(self):
        try:
            self.state("zoomed")
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
        bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=60)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="BBP Session History",
            font=(res.FONT_TITLE[0], 20, "bold"),
            text_color="white"
        ).pack(side="left", padx=20, pady=15)

        ctk.CTkButton(
            bar,
            text="Close",
            width=90, height=32,
            fg_color="#333333",
            hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=15, pady=14)

        ctk.CTkButton(
            bar,
            text="⇄  Compare Runs",
            width=140, height=32,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            font=(res.FONT_LABEL[0], 11),
            command=self._open_comparison
        ).pack(side="right", padx=(0, 8), pady=14)

        self.lbl_count = ctk.CTkLabel(
            bar,
            text="Loading sessions...",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        )
        self.lbl_count.pack(side="right", padx=20)

        # --- SEARCH BAR ---
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.pack(fill="x", padx=20, pady=(10, 6))

        self.ent_search = ctk.CTkEntry(
            filter_bar,
            placeholder_text="Search by experiment name, run ID or date...",
            height=34
        )
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ent_search.bind("<KeyRelease>", self._filter_sessions)

        self.btn_refresh = ctk.CTkButton(
            filter_bar,
            text="Refresh",
            width=90, height=34,
            fg_color="#333333",
            hover_color="#444444",
            command=self._load_sessions
        )
        self.btn_refresh.pack(side="right")

        # --- COLUMN HEADERS ---
        hdr = ctk.CTkFrame(self, fg_color="#1a1a3a", corner_radius=0, height=36)
        hdr.pack(fill="x", padx=20)
        hdr.pack_propagate(False)
        hdr.grid_columnconfigure(0, weight=0, minsize=110)   # Run ID
        hdr.grid_columnconfigure(1, weight=0, minsize=180)   # Date
        hdr.grid_columnconfigure(2, weight=1)                # Experimenter / Experiment
        hdr.grid_columnconfigure(3, weight=0, minsize=100)   # Stations
        hdr.grid_columnconfigure(4, weight=0, minsize=130)   # Profile
        hdr.grid_columnconfigure(5, weight=0, minsize=220)   # Action

        headers = ["Run ID", "Date", "Experimenter / Experiment", "Stations", "Profile", "Action"]
        for i, h in enumerate(headers):
            anchor = "e" if i == 5 else "w"
            ctk.CTkLabel(
                hdr, text=h,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=res.COLOR_PRIMARY
            ).grid(row=0, column=i, padx=12, pady=8, sticky=anchor)

        # --- SCROLLABLE SESSION LIST ---
        self.session_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent"
        )
        self.session_scroll.pack(
            fill="both", expand=True, padx=20, pady=(4, 15)
        )

    # ------------------------------------------------------------------
    # SESSION DISCOVERY — reads directly from $BBP_DATA_DIR/outdata/
    # ------------------------------------------------------------------

    def _load_sessions(self):
        """
        Reads $BBP_DATA_DIR/outdata/ directly.
        Every subfolder is a simulation run — no mapping needed.
        Shows ALL runs regardless of profile or module count.
        """
        for widget in self.session_scroll.winfo_children():
            widget.destroy()

        self.lbl_count.configure(text="Reading simulation results...")

        # Resolve BBP data path
        bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"

        outdata = f"{bbp_data}/outdata"

        # List all run folders sorted newest first
        result = WSLBridge.run_command(
            f"ls -t '{outdata}' 2>/dev/null"
        )
        if result.returncode != 0 or not result.stdout.strip():
            self.lbl_count.configure(text="No simulation results found")
            ctk.CTkLabel(
                self.session_scroll,
                text=f"No results found in:\n{outdata}",
                font=(res.FONT_LABEL[0], 13),
                text_color="gray"
            ).pack(pady=40)
            return

        run_ids = [
            r.strip() for r in result.stdout.strip().splitlines()
            if r.strip()
        ]

        sessions = []
        for run_id in run_ids:
            s = self._parse_run(outdata, run_id)
            if s:
                sessions.append(s)

        self._sessions = sessions
        self.lbl_count.configure(
            text=f"{len(sessions)} simulation runs found"
        )
        self._render_sessions(sessions)

    def _parse_run(self, outdata, run_id):
        """
        Parses a single $BBP_DATA_DIR/outdata/<run_id>/ folder.
        Reads experimenter + experiment name from the .src file.
        """
        folder = f"{outdata}/{run_id}"

        # --- FIND .SRC FILE ---
        # Try param_files first, then indata
        bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"

        src_path = ""
        for search_dir in [
            f"{folder}/param_files",
            f"{bbp_data}/indata/{run_id}",
        ]:
            r = WSLBridge.run_command(
                f"find '{search_dir}' -name '[.]src' 2>/dev/null | head -1"
            )
            # use ls as fallback
            if not r.stdout.strip():
                r = WSLBridge.run_command(
                    f"ls '{search_dir}' 2>/dev/null | grep '[.]src' | head -1"
                )
                fname = r.stdout.strip()
                if fname:
                    src_path = f"{search_dir}/{fname}"
                    break
            else:
                src_path = r.stdout.strip()
                break

        # --- EXPERIMENT NAME from filename ---
        exp_name = f"Run {run_id}"
        if src_path:
            basename = os.path.basename(src_path)
            if basename.endswith(".src"):
                exp_name = basename[:-4]

        # --- EXPERIMENTER NAME from inside the .src file ---
        experimenter = ""
        src_content  = ""
        if src_path:
            ok, src_content = WSLBridge.read_wsl_file(src_path)
            if ok:
                for line in src_content.splitlines():
                    line = line.strip()
                    # Look for: # EXPERIMENTER: Jorge
                    # or: EXPERIMENTER = Jorge
                    if "EXPERIMENTER" in line.upper():
                        if ":" in line:
                            experimenter = line.split(":", 1)[-1].strip()
                        elif "=" in line:
                            experimenter = line.split("=", 1)[-1].strip()
                        # Remove leading # if present
                        experimenter = experimenter.lstrip("#").strip()
                        break

        # --- DATE from folder modification time ---
        date_result = WSLBridge.run_command(
            f"stat -c '%y' '{folder}' 2>/dev/null | cut -d'.' -f1"
        )
        raw_date = date_result.stdout.strip()
        try:
            from datetime import datetime
            dt       = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%B %d, %Y   %H:%M")
        except Exception:
            date_str = raw_date or run_id

        # --- LIST FILES in outdata folder ---
        files_result = WSLBridge.run_command(
            f"ls '{folder}' 2>/dev/null"
        )
        files = files_result.stdout

        # --- DETECT PROFILE from what files exist ---
        has_vel      = ".vel.bbp"      in files
        has_smap     = "station_map"   in files
        has_html     = "index-"        in files
        has_srf      = ".srf"          in files
        has_fas      = WSLBridge.wsl_path_exists(f"{folder}/FAS")
        has_rotd     = ".rd50"         in files

        if has_html and has_smap and has_vel:
            profile_label = "Full Pipeline"
        elif has_vel and has_rotd and not has_smap:
            profile_label = "Custom"
        elif has_vel and not has_smap:
            profile_label = "Quick Run"
        elif has_srf and not has_vel:
            profile_label = "Rupture Only"
        else:
            profile_label = "Custom"

        # --- COUNT STATIONS ---
        count_result = WSLBridge.run_command(
            f"ls '{folder}' 2>/dev/null | grep -c '[.]vel[.]bbp' || echo 0"
        )
        n = count_result.stdout.strip()
        station_count = f"{n} stations" if n and n != "0" else "No stations"

        # --- DETECT VALIDATION RUN ---
        # GoF files only exist in validation runs — same logic as ResultsPanel
        has_gof = WSLBridge.run_command(
            f"ls '{folder}'/gof-*.png 2>/dev/null | head -1"
        ).stdout.strip() != ""

        # Also check for GMPE-style GoF (different naming pattern)
        if not has_gof:
            has_gof = WSLBridge.run_command(
                f"ls '{folder}'/*_r0-*.png 2>/dev/null | head -1"
            ).stdout.strip() != ""

        # Detect validation event name from GoF filename if available
        val_event_name = ""
        if has_gof:
            gof_result = WSLBridge.run_command(
                f"ls '{folder}'/gof-*.png 2>/dev/null | head -1"
            )
            gof_fname = os.path.basename(gof_result.stdout.strip())
            name_map = {
                "CHINOH"  : "Chino Hills",
                "NR"      : "Northridge 1994",
                "WHITT"   : "Whittier 1987",
                "GMPE55RV": "GMPE Mw5.5 Reverse",
                "GMPE62SS": "GMPE Mw6.2 Strike-Slip",
                "GMPE66RV": "GMPE Mw6.6 Reverse",
                "GMPE66SS": "GMPE Mw6.6 Strike-Slip",
            }
            for code, name in name_map.items():
                if code in gof_fname.upper():
                    val_event_name = name
                    break
            if not val_event_name:
                # Fallback: extract from filename
                parts = gof_fname.split("-")
                val_event_name = parts[1] if len(parts) > 1 else "Validation"

        # --- DETECT SIMULATION METHOD (GP vs EXSIM) ---
        # Primary source: "# METHOD = ..." comment appended to the .src
        # file at generate-files time (same mechanism as the Advanced
        # GP Parameters block — a BBP-ignored comment that travels with
        # the run permanently). Reuses src_content already read above
        # for the experimenter name, avoiding a redundant file read.
        # Falls back to the 'Simulation Method' field in
        # index-<run_id>.html for runs made before this marker existed.
        sim_method = ""
        if src_content:
            m = re.search(r'#\s*METHOD\s*=\s*(\w+)', src_content, re.IGNORECASE)
            if m and m.group(1).strip().upper() in ("GP", "EXSIM", "IRIKURA1", "IRIKURA2", "SONG", "UCSB", "SDSU"):
                sim_method = m.group(1).strip().upper()
        if not sim_method:
            sim_method = WSLBridge.detect_simulation_method(run_id, folder)

        return {
            "run_id"          : run_id,
            "exp_name"        : exp_name,
            "experimenter"    : experimenter,
            "date_str"        : date_str,
            "profile_label"   : profile_label,
            "outdata_path"    : folder,
            "station_count"   : station_count,
            "complete"        : True,
            "is_validation"   : has_gof,
            "val_event_name"  : val_event_name,
            "sim_method"      : sim_method,
        }

    def _build_run_id_map(self, bbp_xml_path, base_path):
        """
        Scans $BBP_DATA_DIR/xml/ for XML files and extracts the
        session timestamp from each file's station list path.
        Returns dict: {session_folder_name: run_id}

        Example XML contains:
            input_station_file="/home/black/bbp_projects/20260517_130659/stl/..."
        We extract "20260517_130659" as the session key.
        """
        run_id_map = {}

        result = WSLBridge.run_command(
            f"ls -t '{bbp_xml_path}' 2>/dev/null | grep '.xml'"
        )
        if result.returncode != 0:
            return run_id_map

        xml_files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]

        for xml_file in xml_files:
            run_id = xml_file.replace(".xml", "").strip()
            if not run_id.isdigit():
                continue

            xml_path       = f"{bbp_xml_path}/{xml_file}"
            content_result = WSLBridge.run_command(
                f"cat '{xml_path}' 2>/dev/null"
            )
            content = content_result.stdout

            # Try matching via stl path (Full and Quick Run)
            import re
            match = re.search(r'bbp_projects[/\\](\d{8}_\d{6})', content)
            if match:
                session_ts = match.group(1)
                run_id_map[session_ts] = run_id
                continue

            # Fallback: try matching via src path (Rupture Only — no stl)
            match = re.search(r'bbp_projects[/\\](\d{8}_\d{6})', content)
            if match:
                session_ts = match.group(1)
                run_id_map[session_ts] = run_id

        return run_id_map

    def _parse_session(self, base_path, folder_name, bbp_outdata, run_id_map):
        """
        Reads a session folder and extracts metadata.
        Marks complete=True if $BBP_DATA_DIR/outdata/<run_id> exists.
        Tries multiple strategies to find the run_id.
        """
        import re
        session_path = f"{base_path}/{folder_name}"

        # --- GET EXPERIMENT NAME ---
        exp_name   = "Unknown"
        src_result = WSLBridge.run_command(
            f"ls '{session_path}/src/' 2>/dev/null | head -1"
        )
        src_file = src_result.stdout.strip()
        if src_file.endswith(".src"):
            exp_name = src_file[:-4]

        # --- DETECT PROFILE FROM SESSION XML ---
        profile_label    = "Unknown"
        xml_session_path = f"{session_path}/xml/{exp_name}.xml"
        xml_ok           = WSLBridge.wsl_path_exists(xml_session_path)
        xml_content      = ""

        if xml_ok:
            xml_result  = WSLBridge.run_command(
                f"cat '{xml_session_path}' 2>/dev/null"
            )
            xml_content  = xml_result.stdout
            module_count = xml_content.count("<name>")

            if module_count == 0:
                profile_label = "Not run"
            elif module_count <= 1:
                profile_label = "Rupture Only"
            elif module_count <= 4:
                profile_label = "Quick Run"
            elif module_count < 9:
                profile_label = "Custom"
            else:
                profile_label = "Full Pipeline"
        else:
            profile_label = "Not run"

        # --- FIND RUN ID ---
        # Strategy 1: use pre-built map from BBP XML folder
        run_id = run_id_map.get(folder_name, "")

        # Strategy 2: scan the session XML directly for a run_id
        # BBP XML often has <optfile> or log entries with the run_id
        if not run_id and xml_content:
            m = re.search(r'<sim_id>(\d+)</sim_id>', xml_content)
            if m:
                run_id = m.group(1)

        # Strategy 3: search BBP_DATA_DIR/xml for any XML referencing this session
        if not run_id:
            search = WSLBridge.run_command(
                f"grep -rl '{folder_name}' '{bbp_outdata}/../xml/' 2>/dev/null | head -1"
            )
            found_xml = search.stdout.strip()
            if found_xml:
                basename = os.path.basename(found_xml)
                candidate = basename.replace(".xml", "").strip()
                if candidate.isdigit():
                    run_id = candidate

        # Strategy 4: list all outdata dirs and find one whose XML references this session
        if not run_id:
            all_runs = WSLBridge.run_command(
                f"ls -t '{bbp_outdata}' 2>/dev/null | head -50"
            )
            for candidate_id in all_runs.stdout.strip().splitlines():
                candidate_id = candidate_id.strip()
                if not candidate_id.isdigit():
                    continue
                # Check param_files folder for matching src name
                check = WSLBridge.run_command(
                    f"ls '{bbp_outdata}/{candidate_id}/param_files/' 2>/dev/null"
                )
                if exp_name in check.stdout and exp_name != "Unknown":
                    run_id = candidate_id
                    break

        # --- CHECK COMPLETE ---
        complete     = False
        outdata_path = ""
        station_count = "N/A"

        if run_id:
            outdata_path = f"{bbp_outdata}/{run_id}"
            complete     = WSLBridge.wsl_path_exists(outdata_path)

            if complete:
                count_result = WSLBridge.run_command(
                    f"ls '{outdata_path}' 2>/dev/null | grep -c '.vel.bbp' || echo 0"
                )
                n = count_result.stdout.strip()
                if n and n != "0":
                    station_count = f"{n} stations"
                else:
                    station_count = "No stations"

        # --- PARSE DATE ---
        try:
            from datetime import datetime
            dt       = datetime.strptime(folder_name, "%Y%m%d_%H%M%S")
            date_str = dt.strftime("%B %d, %Y   %H:%M:%S")
        except Exception:
            date_str = folder_name

        # --- DETECT SIMULATION METHOD (GP / EXSIM / IRIKURA1) ---
        sim_method = "UNKNOWN"
        # Try reading .src from indata first (most reliable — has # METHOD = ...)
        if run_id and run_id != "N/A" and complete:
            bbp_data = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
            if not bbp_data:
                bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"
            ok_src, src_txt = WSLBridge.read_src_file(run_id)
            if ok_src and src_txt:
                import re as _re
                m2 = _re.search(r'#\s*METHOD\s*=\s*(\w+)', src_txt, _re.IGNORECASE)
                if m2 and m2.group(1).strip().upper() in ("GP", "EXSIM", "IRIKURA1", "IRIKURA2", "SONG", "UCSB", "SDSU"):
                    sim_method = m2.group(1).strip().upper()
            if sim_method == "UNKNOWN":
                sim_method = WSLBridge.detect_simulation_method(run_id, outdata_path)

        return {
            "folder_name"   : folder_name,
            "session_path"  : session_path,
            "outdata_path"  : outdata_path,
            "date_str"      : date_str,
            "exp_name"      : exp_name,
            "run_id"        : run_id or "N/A",
            "station_count" : station_count,
            "complete"      : complete,
            "profile_label" : profile_label,
            "is_validation" : False,
            "val_event_name": "",
            "sim_method"    : sim_method,
        }

    # ------------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------------

    def _render_sessions(self, sessions):
        """Renders the session list rows."""
        for widget in self.session_scroll.winfo_children():
            widget.destroy()

        if not sessions:
            ctk.CTkLabel(
                self.session_scroll,
                text="No sessions found.",
                font=(res.FONT_LABEL[0], 13),
                text_color="gray"
            ).pack(pady=40)
            return

        for i, session in enumerate(sessions):
            self._render_session_row(i, session)

    def _render_session_row(self, index, session):
        """Renders a single session row. Every row has a View Results button."""
        is_val    = session.get("is_validation", False)
        row_color = "#1a1500" if is_val else ("#252525" if index % 2 == 0 else "#1e1e1e")
        brd_color = "#3a3000" if is_val else "#333333"
        brd_width = 1 if is_val else 0

        row = ctk.CTkFrame(
            self.session_scroll,
            fg_color=row_color,
            corner_radius=6,
            border_width=brd_width,
            border_color=brd_color,
            height=52
        )
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)
        row.grid_columnconfigure(0, weight=0, minsize=110)   # Run ID
        row.grid_columnconfigure(1, weight=0, minsize=180)   # Date
        row.grid_columnconfigure(2, weight=1)                # Experimenter / Experiment
        row.grid_columnconfigure(3, weight=0, minsize=100)   # Stations
        row.grid_columnconfigure(4, weight=0, minsize=130)   # Profile
        row.grid_columnconfigure(5, weight=0, minsize=220)   # Action

        # Run ID
        ctk.CTkLabel(
            row,
            text=f"#{session['run_id']}",
            font=("Courier", 11, "bold"),
            text_color=res.COLOR_PRIMARY
        ).grid(row=0, column=0, padx=12, pady=15, sticky="w")

        # Date
        ctk.CTkLabel(
            row,
            text=session["date_str"],
            font=(res.FONT_LABEL[0], 11),
            text_color="white"
        ).grid(row=0, column=1, padx=12, pady=15, sticky="w")

        # Experimenter + Experiment name OR Validation badge
        is_validation  = session.get("is_validation", False)
        val_event_name = session.get("val_event_name", "")
        experimenter   = session.get("experimenter", "")
        exp_name       = session.get("exp_name", "")

        name_frame = ctk.CTkFrame(row, fg_color="transparent")
        name_frame.grid(row=0, column=2, padx=12, pady=10, sticky="w")

        # Method badge (GP / EXSIM / IRIKURA1 / IRIKURA2 / SONG / UCSB) — shown for every row
        sim_method = session.get("sim_method", "UNKNOWN")
        if sim_method in ("GP", "EXSIM", "IRIKURA1", "IRIKURA2", "SONG", "UCSB", "SDSU"):
            method_colors = {
                "GP"      : ("#0a2a3a", "#3b8ed0"),
                "EXSIM"   : ("#3a1a00", "#ffaa44"),
                "IRIKURA1": ("#0a2a0a", "#22aa55"),
                "IRIKURA2": ("#0a2a28", "#22ccaa"),
                "SONG"    : ("#2a0a3a", "#8855cc"),
                "UCSB"    : ("#3a0a20", "#cc3366"),
                "SDSU"    : ("#12123a", "#5566ee"),
            }
            method_labels = {
                "GP"      : "GP",
                "EXSIM"   : "EXSIM",
                "IRIKURA1": "IRIKURA 1",
                "IRIKURA2": "IRIKURA 2",
                "SONG"    : "SONG",
                "UCSB"    : "UCSB",
                "SDSU"    : "SDSU",
            }
            bg_color, fg_color = method_colors[sim_method]
            ctk.CTkLabel(
                name_frame,
                text=method_labels[sim_method],
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color=fg_color,
                fg_color=bg_color,
                corner_radius=4,
                padx=6, pady=2
            ).pack(side="left", padx=(0, 6))

        if is_validation:
            # Yellow validation badge
            ctk.CTkLabel(
                name_frame,
                text="✓ VALIDATION",
                font=(res.FONT_LABEL[0], 9, "bold"),
                text_color="#1a1200",
                fg_color="#ffdd00",
                corner_radius=4,
                padx=6, pady=2
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                name_frame,
                text=val_event_name or exp_name or f"Run {session['run_id']}",
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="#ffdd00"
            ).pack(side="left")
        else:
            if experimenter and exp_name:
                full_name = f"{experimenter}  /  {exp_name}"
            elif exp_name:
                full_name = exp_name
            else:
                full_name = f"Run {session['run_id']}"

            ctk.CTkLabel(
                name_frame,
                text=full_name,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color="white"
            ).pack(side="left")

        # Station count
        ctk.CTkLabel(
            row,
            text=session["station_count"],
            font=(res.FONT_LABEL[0], 10),
            text_color="#888888"
        ).grid(row=0, column=3, padx=12, pady=15, sticky="w")

        # Profile label
        profile = session.get("profile_label", "Full Pipeline")
        profile_color = {
            "Full Pipeline" : res.COLOR_SUCCESS,
            "Quick Run"     : "#f59e0b",
            "Rupture Only"  : "#3b82f6",
            "Custom"        : "#a78bfa",
        }.get(profile, "#888888")
        ctk.CTkLabel(
            row,
            text=profile,
            font=(res.FONT_LABEL[0], 10, "bold"),
            text_color=profile_color
        ).grid(row=0, column=4, padx=12, pady=15, sticky="w")

        # --- BUTTON GROUP: View Results + Edit + Delete ---
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=5, padx=12, pady=10, sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="View Results",
            width=110, height=32,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            font=(res.FONT_LABEL[0], 11),
            command=lambda s=session: self._open_session(s)
        ).pack(side="left", padx=(0, 4))

        # Edit button — scenario runs only (not validation)
        if not is_val and self._on_edit_run:
            ctk.CTkButton(
                btn_frame,
                text="Edit",
                width=60, height=32,
                fg_color="#1a3a1a",
                hover_color="#2a5a2a",
                border_width=1,
                border_color="#336633",
                text_color="#88dd88",
                font=(res.FONT_LABEL[0], 11),
                command=lambda s=session: self._edit_session(s)
            ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_frame,
            text="D",
            width=32, height=32,
            fg_color="#2a0000",
            hover_color="#440000",
            border_width=1,
            border_color="#661111",
            text_color="#ff6666",
            font=(res.FONT_LABEL[0], 13, "bold"),
            command=lambda s=session: self._confirm_delete(s)
        ).pack(side="left")

    # ------------------------------------------------------------------
    # FILTER
    # ------------------------------------------------------------------

    def _filter_sessions(self, *args):
        """Filters sessions by search query only."""
        query = self.ent_search.get().strip().lower()

        if not query:
            self._render_sessions(self._sessions)
            return

        filtered = [
            s for s in self._sessions
            if query in s["exp_name"].lower()
            or query in s["date_str"].lower()
            or query in s["run_id"].lower()
            or query in s.get("profile_label", "").lower()
        ]
        self._render_sessions(filtered)

    # ------------------------------------------------------------------
    # DELETE RUN
    # ------------------------------------------------------------------

    def _confirm_delete(self, session):
        """
        Shows a confirmation dialog listing exactly what will be deleted
        before performing any destructive operation.
        Deletes:
          - ~/bbp_data/outdata/{run_id}/   (all results)
          - ~/bbp_data/indata/{run_id}/    (input copies BBP made)
          - ~/bbp_projects/{session}/      (original session folder)
        """
        run_id       = session.get("run_id", "N/A")
        outdata_path = session.get("outdata_path", "")
        session_path = session.get("session_path", "")
        exp_name     = session.get("exp_name", "Unknown")

        # Resolve indata path
        bbp_data  = WSLBridge.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{WSLBridge.get_wsl_home()}/bbp_data"
        indata_path = f"{bbp_data}/indata/{run_id}"

        # Build the list of folders that actually exist
        to_delete = []
        for path, label in [
            (outdata_path, "Results (outdata)"),
            (indata_path,  "Input copies (indata)"),
            (session_path, "Session folder (bbp_projects)"),
        ]:
            if path and WSLBridge.wsl_path_exists(path):
                to_delete.append((path, label))

        # --- CONFIRMATION WINDOW ---
        win = ctk.CTkToplevel(self)
        win.title("Confirm Delete")
        win.geometry("540x360")
        win.configure(fg_color="#1a0000")
        win.transient(self)
        win.resizable(False, False)

        def _ready():
            try:
                win.grab_set()
                win.lift()
                win.focus_force()
            except Exception:
                pass
        win.after(150, _ready)

        # Header
        ctk.CTkLabel(
            win,
            text="⚠  Delete Simulation Run",
            font=(res.FONT_LABEL[0], 15, "bold"),
            text_color="#ff6666"
        ).pack(pady=(20, 4), padx=20, anchor="w")

        ctk.CTkLabel(
            win,
            text=f"Run ID: {run_id}  —  {exp_name}",
            font=("Courier", 11),
            text_color="#aaaaaa"
        ).pack(padx=20, anchor="w")

        ctk.CTkLabel(
            win,
            text="This action cannot be undone. The following folders will be permanently deleted:",
            font=(res.FONT_LABEL[0], 11),
            text_color="#ccaaaa",
            wraplength=500,
            justify="left"
        ).pack(pady=(12, 4), padx=20, anchor="w")

        # List of folders to delete
        folder_frame = ctk.CTkFrame(
            win, fg_color="#2a0000",
            border_width=1, border_color="#661111",
            corner_radius=6
        )
        folder_frame.pack(fill="x", padx=20, pady=(0, 12))

        if to_delete:
            for path, label in to_delete:
                row = ctk.CTkFrame(folder_frame, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=3)
                ctk.CTkLabel(
                    row,
                    text=f"  {label}:",
                    font=(res.FONT_LABEL[0], 10, "bold"),
                    text_color="#ff8888",
                    width=180, anchor="w"
                ).pack(side="left")
                ctk.CTkLabel(
                    row,
                    text=path,
                    font=("Courier", 9),
                    text_color="#cc6666",
                    anchor="w",
                    wraplength=300,
                    justify="left"
                ).pack(side="left")
        else:
            ctk.CTkLabel(
                folder_frame,
                text="  No folders found for this run.",
                font=(res.FONT_LABEL[0], 11),
                text_color="#888888"
            ).pack(padx=12, pady=8)

        # Buttons
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100, height=36,
            fg_color="#333333",
            hover_color="#444444",
            command=win.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Delete Permanently",
            width=180, height=36,
            fg_color="#660000",
            hover_color="#880000",
            border_width=1,
            border_color="#ff4444",
            text_color="#ff9999",
            font=(res.FONT_LABEL[0], 12, "bold"),
            command=lambda: self._do_delete(session, to_delete, win)
        ).pack(side="right")

    def _do_delete(self, session, to_delete, confirm_win):
        """
        Performs the actual deletion after user confirms.
        Removes all listed folders via WSLBridge then refreshes the list.
        """
        confirm_win.destroy()

        errors = []
        for path, label in to_delete:
            result = WSLBridge.run_command(f"rm -rf '{path}' 2>&1")
            if result.returncode != 0:
                errors.append(f"{label}: {result.stderr.strip() or result.stdout.strip()}")

        if errors:
            # Show error popup
            err_win = ctk.CTkToplevel(self)
            err_win.title("Delete Error")
            err_win.geometry("480x200")
            err_win.configure(fg_color="#1a0000")
            err_win.transient(self)
            err_win.after(150, lambda: err_win.grab_set())

            ctk.CTkLabel(
                err_win,
                text="Some folders could not be deleted:",
                font=(res.FONT_LABEL[0], 12, "bold"),
                text_color="#ff6666"
            ).pack(pady=(20, 8), padx=20, anchor="w")

            for e in errors:
                ctk.CTkLabel(
                    err_win,
                    text=f"  • {e}",
                    font=("Courier", 10),
                    text_color="#cc6666",
                    justify="left"
                ).pack(padx=20, anchor="w")

            ctk.CTkButton(
                err_win,
                text="OK",
                width=80, height=32,
                fg_color="#333333",
                command=err_win.destroy
            ).pack(pady=16)

        # Refresh the session list regardless of errors
        self._load_sessions()

    # ------------------------------------------------------------------
    # OPEN SESSION
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # EDIT (re-simulate) a previous run
    # ------------------------------------------------------------------

    def _edit_session(self, session):
        """
        Reads the .src and .stl from indata/<run_id>/, parses them into
        a dict, then calls on_edit_run(method, params_dict, stations).
        Closes the history window so the user lands on the correct panel
        with all fields pre-filled.
        """
        run_id = session.get("run_id", "")
        method = session.get("sim_method", "UNKNOWN")

        if method not in ("GP", "EXSIM", "IRIKURA1", "IRIKURA2", "SONG", "UCSB", "SDSU"):
            import tkinter.messagebox as mb
            mb.showwarning(
                "Cannot Edit",
                f"Run {run_id}: simulation method '{method}' is not supported for editing yet.",
                parent=self
            )
            return

        # --- Read .src ---
        ok_src, src_content = WSLBridge.read_src_file(run_id)
        if not ok_src or not src_content:
            import tkinter.messagebox as mb
            mb.showerror(
                "Cannot Edit",
                f"Could not read .src file for run {run_id}.\n"
                "The indata folder may have been deleted.",
                parent=self
            )
            return

        # --- Read .stl ---
        ok_stl, stl_content = WSLBridge.read_stl_file(run_id)

        # --- Parse .src ---
        params = self._parse_src_for_edit(src_content)

        # --- Parse .stl into station list [(lon, lat, name), ...] ---
        stations = []
        if ok_stl and stl_content:
            for line in stl_content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        stations.append((float(parts[0]), float(parts[1]), parts[2]))
                    except ValueError:
                        pass
                elif len(parts) == 2:
                    try:
                        stations.append((float(parts[0]), float(parts[1]), f"STA{len(stations)+1}"))
                    except ValueError:
                        pass

        # --- Build a suggested new experiment name ---
        exp_name = session.get("exp_name", f"run_{run_id}")
        # Strip any trailing _N suffix so we start fresh numbering
        import re as _re
        base = _re.sub(r'_\d+$', '', exp_name)
        params["_suggested_exp_name"] = base

        # --- Fire callback and close ---
        if self._on_edit_run:
            self._on_edit_run(method, params, stations)
        self.destroy()

    def _parse_src_for_edit(self, src_content):
        """
        Parses a BBP .src file and returns a flat dict of all parameters
        needed to pre-fill GP or ExSIM panels.

        Handles both:
          KEY = VALUE          (standard BBP keys)
          # EXSIM_KEY = VALUE  (ExSIM path parameter snapshot)
          # KEY = VALUE [TAG]  (GP advanced parameter snapshot)
        """
        import re as _re
        params = {}

        for raw_line in src_content.splitlines():
            line = raw_line.strip()

            # Skip blank lines and pure comment lines that aren't snapshots
            if not line:
                continue

            # --- Standard BBP key = value (non-comment) ---
            if not line.startswith("#"):
                if "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip().upper()
                    val = val.split("#")[0].strip()  # strip inline comments
                    if key and val:
                        params[key] = val
                continue

            # --- Comment lines: check for snapshots ---
            body = line.lstrip("#").strip()
            if "=" not in body:
                continue

            # ExSIM path parameter snapshot: "EXSIM_KEY = value"
            if body.upper().startswith("EXSIM_"):
                key, _, val = body.partition("=")
                key = key.strip().upper()
                val = val.strip()
                if key and val:
                    params[key] = val
                continue

            # METHOD marker
            if body.upper().startswith("METHOD"):
                key, _, val = body.partition("=")
                params["_METHOD"] = val.strip().upper()
                continue

            # GP Advanced Parameter snapshot: "KEY = value [TAG]"
            # Tag is ACTIVE or BBP_DEFAULT, optional
            m = _re.match(
                r'^(CODEBASE_GP_\w+)\s*=\s*([^\[]+?)(?:\s*\[.*\])?\s*$',
                body, _re.IGNORECASE
            )
            if m:
                key = m.group(1).strip().upper()
                val = m.group(2).strip()
                params[key] = val

            # GS and DR segments: "EXSIM_GS_SEG1 = R slope" etc.
            # (Already handled above by EXSIM_ prefix)

        return params

    def _open_comparison(self):
        """Opens the ComparisonPanel directly from the history panel."""
        ComparisonPanel(self)

    def _open_session(self, session):
        """
        Loads the selected run into AppConfig and opens ResultsPanel.
        All data comes from $BBP_DATA_DIR/outdata/<run_id>/ directly.
        """
        # Map profile label to AppConfig profile string
        profile_map = {
            "Full Pipeline" : "full",
            "Quick Run"     : "quick",
            "Rupture Only"  : "rupture",
            "Custom"        : "custom",
        }
        AppConfig.simulation_profile = profile_map.get(
            session.get("profile_label", "Full Pipeline"), "full"
        )

        # Set the essential AppConfig fields
        AppConfig.current_run_id    = session["run_id"]
        AppConfig.current_base_name = session["exp_name"]
        AppConfig.out_path          = session["outdata_path"]

        # Try to find src/stl from param_files inside outdata
        param_path = f"{session['outdata_path']}/param_files"
        AppConfig.current_src_file  = f"{param_path}/{session['exp_name']}.src"
        AppConfig.current_stl_file  = f"{param_path}/{session['exp_name']}.stl"

        if self._on_open_results:
            self._on_open_results()

        self.destroy()