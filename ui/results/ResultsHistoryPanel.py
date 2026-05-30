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
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge


class ResultsHistoryPanel(ctk.CTkToplevel):
    """
    Full window showing all past BBP simulation sessions.
    Each session shows its status (complete/incomplete),
    experiment name, date, and run ID if available.
    Clicking a completed session opens the ResultsPanel.
    """

    def __init__(self, master, on_open_results=None):
        super().__init__(master)

        self._on_open_results = on_open_results
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
        hdr.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        headers = ["Run ID", "Date", "Experimenter / Experiment", "Stations", "Profile", "Action"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(
                hdr, text=h,
                font=(res.FONT_LABEL[0], 11, "bold"),
                text_color=res.COLOR_PRIMARY
            ).grid(row=0, column=i, padx=12, pady=8, sticky="w")

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

        return {
            "run_id"        : run_id,
            "exp_name"      : exp_name,
            "experimenter"  : experimenter,
            "date_str"      : date_str,
            "profile_label" : profile_label,
            "outdata_path"  : folder,
            "station_count" : station_count,
            "complete"      : True,
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
        row_color = "#252525" if index % 2 == 0 else "#1e1e1e"

        row = ctk.CTkFrame(
            self.session_scroll,
            fg_color=row_color,
            corner_radius=6,
            height=52
        )
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)
        row.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

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

        # Experimenter + Experiment name
        experimenter = session.get("experimenter", "")
        exp_name     = session.get("exp_name", "")

        if experimenter and exp_name:
            full_name = f"{experimenter}  /  {exp_name}"
        elif exp_name:
            full_name = exp_name
        else:
            full_name = f"Run {session['run_id']}"

        ctk.CTkLabel(
            row,
            text=full_name,
            font=(res.FONT_LABEL[0], 11, "bold"),
            text_color="white"
        ).grid(row=0, column=2, padx=12, pady=15, sticky="w")

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

        # View Results — ALWAYS shown for every row
        ctk.CTkButton(
            row,
            text="View Results",
            width=110, height=32,
            fg_color=res.COLOR_PRIMARY,
            hover_color="#004070",
            font=(res.FONT_LABEL[0], 11),
            command=lambda s=session: self._open_session(s)
        ).grid(row=0, column=5, padx=12, pady=10, sticky="e")

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
    # OPEN SESSION
    # ------------------------------------------------------------------

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