import subprocess
import platform


class WSLBridge:
    """
    WSLBridge.py — core/WSLBridge.py
    ---------------------------------
    Central communication layer between the Windows-based GUI (CustomTkinter)
    and the Linux-based BBP software running inside WSL.

    ALL interactions with the WSL filesystem, environment variables, and
    BBP executables must go through this class. No other module should call
    subprocess with "wsl" directly.

    This design means:
    - If the project is ever moved to a native Linux machine, only this
      file needs to change (see IS_WINDOWS flag below).
    - Every other module (AppConfig, RupturePanel, etc.) stays untouched.
    """

    # Detect if we are running on Windows (WSL needed) or native Linux
    IS_WINDOWS = platform.system() == "Windows"

    # Path to the BBP Python virtual environment.
    # Sourced before every BBP call to ensure all dependencies are available.
    # Dynamically resolved from WSL home at first use.
    BBP_ENV_PATH = ""

    @classmethod
    def _get_bbp_env_path(cls):
        """
        Returns the bbp_env activation path, resolving it dynamically
        from the WSL home directory if not already set.
        """
        if not cls.BBP_ENV_PATH:
            home = cls.get_wsl_home()
            cls.BBP_ENV_PATH = f"{home}/bbp_env/bin/activate"
        return cls.BBP_ENV_PATH

    @classmethod
    def _bbp_cmd(cls, xml_path):
        """
        Builds the shell command to activate bbp_env and run BBP.
        Note: the real run_bbp.py is at bbp-22.4.0/bbp/comps/run_bbp.py
        and is directly on PATH after activating bbp_env.
        """
        env_path = cls._get_bbp_env_path()
        return f"source '{env_path}' && run_bbp.py --xml '{xml_path}'"

    # ------------------------------------------------------------------
    # CORE COMMAND RUNNER
    # ------------------------------------------------------------------

    @classmethod
    def run_command(cls, cmd, input_data=None, capture=True):
        """
        Core method — runs a bash command inside WSL (Windows) or
        directly in bash (native Linux).

        Args:
            cmd         (str) : The bash command to execute.
            input_data  (str) : Optional stdin input for the command.
            capture     (bool): If True, captures stdout/stderr.
                                If False, output goes to terminal (useful for
                                streaming BBP simulation output).

        Returns:
            subprocess.CompletedProcess object with:
                .returncode : 0 = success, non-zero = error
                .stdout     : captured output (str) or None
                .stderr     : captured error output (str) or None

        Example:
            result = WSLBridge.run_command("echo $HOME")
            print(result.stdout)  # /home/username
        """
        try:
            if cls.IS_WINDOWS:
                # Run inside WSL from Windows
                full_cmd = ["wsl", "bash", "-c", cmd]
            else:
                # Run directly in bash on native Linux
                full_cmd = ["bash", "-c", cmd]

            result = subprocess.run(
                full_cmd,
                input=input_data,
                capture_output=capture,
                text=True
            )
            return result

        except FileNotFoundError:
            # wsl.exe not found on this Windows machine
            class _FailedResult:
                returncode = 1
                stdout = ""
                stderr = "WSL executable not found on this system."
            return _FailedResult()

        except Exception as e:
            class _FailedResult:
                returncode = 1
                stdout = ""
                stderr = str(e)
            return _FailedResult()

    # ------------------------------------------------------------------
    # WSL AVAILABILITY CHECK
    # ------------------------------------------------------------------

    @classmethod
    def check_wsl_available(cls):
        """
        Checks whether WSL is installed and reachable from Windows Python.
        Called as the very first step in MainPanel's startup sequence.

        Returns:
            tuple: (bool: wsl_ok, str: wsl_version)

        Example:
            ok, version = WSLBridge.check_wsl_available()
            # ok      -> True
            # version -> "Ubuntu 22.04" or "WSL2" or similar
        """
        if not cls.IS_WINDOWS:
            # Running on native Linux — WSL not needed
            return True, "Native Linux"

        try:
            result = subprocess.run(
                ["wsl", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Extract a short version string from the output
                lines = result.stdout.strip().splitlines()
                version = lines[0] if lines else "WSL Available"
                return True, version
            else:
                # wsl --version failed, try a simple echo as fallback
                fallback = subprocess.run(
                    ["wsl", "echo", "ok"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if fallback.returncode == 0:
                    return True, "WSL Available"
                return False, "WSL not responding"

        except FileNotFoundError:
            return False, "wsl.exe not found"
        except subprocess.TimeoutExpired:
            return False, "WSL timed out"
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # BBP ENVIRONMENT CHECK
    # ------------------------------------------------------------------

    @classmethod
    def check_bbp_environment(cls):
        """
        Checks whether BBP is properly installed and configured inside WSL.
        Replaces the original shutil.which() + os.environ approach which
        only checked the Windows environment, not WSL.

        Verifies:
            1. BBP_DIR environment variable is set in WSL
            2. BBP_DATA_DIR environment variable is set in WSL
            3. run_bbp.py is reachable inside WSL

        Returns:
            dict: {
                "connected" : bool   — True if BBP is fully ready,
                "version"   : str    — BBP version string or "Unknown",
                "details"   : str    — Human-readable status summary
            }

        Example:
            status = WSLBridge.check_bbp_environment()
            if status["connected"]:
                print(status["version"])
        """
        # Check environment variables inside WSL — source bbp_env first
        env_path = cls._get_bbp_env_path()
        source_cmd = f"source '{env_path}' 2>/dev/null || true"

        bbp_dir  = cls.run_command(f"{source_cmd} && echo $BBP_DIR").stdout.strip()
        bbp_data = cls.run_command(f"{source_cmd} && echo $BBP_DATA_DIR").stdout.strip()
        env_ok   = bool(bbp_dir) and bool(bbp_data)

        which_result = cls.run_command(f"{source_cmd} && which run_bbp.py")
        path_ok      = which_result.returncode == 0 and bool(which_result.stdout.strip())

        version = "Unknown"
        if path_ok:
            ver_result = cls.run_command(f"{source_cmd} && run_bbp.py --version 2>&1")
            if ver_result.returncode == 0 and ver_result.stdout.strip():
                version = ver_result.stdout.strip().splitlines()[0]

        # Build human-readable detail string for error messages
        details = (
            f"BBP_DIR: {'OK (' + bbp_dir + ')' if bbp_dir else 'NOT SET'} | "
            f"BBP_DATA_DIR: {'OK' if bbp_data else 'NOT SET'} | "
            f"run_bbp.py: {'Found' if path_ok else 'Not found in WSL PATH'}"
        )

        return {
            "connected" : env_ok and path_ok,
            "version"   : version,
            "details"   : details
        }

    # ------------------------------------------------------------------
    # WSL HOME DIRECTORY
    # ------------------------------------------------------------------

    @classmethod
    def get_wsl_home(cls):
        """
        Returns the home directory of the current WSL user dynamically.
        Replaces the hardcoded "/home/black/" in AppConfig so the project
        works on any researcher's machine automatically.

        Returns:
            str: WSL home path (e.g. "/home/john") or "/home/user" as fallback.

        Example:
            home = WSLBridge.get_wsl_home()
            # "/home/black"  on your machine
            # "/home/carlos" on another researcher's machine
        """
        result = cls.run_command("echo $HOME")
        home = result.stdout.strip()
        return home if home else "/home/user"

    # ------------------------------------------------------------------
    # WSL USERNAME
    # ------------------------------------------------------------------

    @classmethod
    def get_wsl_username(cls):
        """
        Returns the current WSL username.
        Useful for labeling sessions or building user-specific paths.

        Returns:
            str: WSL username (e.g. "black") or "user" as fallback.

        Example:
            user = WSLBridge.get_wsl_username()
            # "black"
        """
        result = cls.run_command("whoami")
        username = result.stdout.strip()
        return username if username else "user"

    # ------------------------------------------------------------------
    # DIRECTORY CREATION IN WSL
    # ------------------------------------------------------------------

    @classmethod
    def make_wsl_dirs(cls, *paths):
        """
        Creates one or more directories inside the WSL filesystem.
        Replaces os.makedirs() which only works on Windows paths.

        Args:
            *paths (str): One or more WSL paths to create.
                          Uses mkdir -p so nested paths are created safely
                          and no error is raised if they already exist.

        Returns:
            tuple: (bool: success, str: error_message or "")

        Example:
            ok, err = WSLBridge.make_wsl_dirs(
                "/home/black/bbp_projects/20240101_120000/src",
                "/home/black/bbp_projects/20240101_120000/stl"
            )
        """
        for path in paths:
            result = cls.run_command(f"mkdir -p '{path}'")
            if result.returncode != 0:
                return False, f"Failed to create {path}: {result.stderr.strip()}"
        return True, ""

    # ------------------------------------------------------------------
    # FILE WRITING INTO WSL
    # ------------------------------------------------------------------

    @classmethod
    def write_wsl_file(cls, wsl_path, content):
        """
        Writes a text file directly into the WSL filesystem.
        Replaces the open() calls in RupturePanel.generate_files() which
        fail because Windows Python cannot write to /home/... paths.

        Args:
            wsl_path (str) : Full WSL path for the file (e.g. /home/black/...)
            content  (str) : Full text content to write into the file.

        Returns:
            tuple: (bool: success, str: error_message or "")

        Example:
            ok, err = WSLBridge.write_wsl_file(
                "/home/black/bbp_projects/session/src/exp.src",
                "MAGNITUDE = 6.5\nSTRIKE = 180\n..."
            )
        """
        try:
            # Use 'cat >' to write content via stdin into the WSL file
            if cls.IS_WINDOWS:
                full_cmd = ["wsl", "bash", "-c", f"cat > '{wsl_path}'"]
            else:
                full_cmd = ["bash", "-c", f"cat > '{wsl_path}'"]

            result = subprocess.run(
                full_cmd,
                input=content,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return False, result.stderr.strip()
            return True, ""

        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # FILE READING FROM WSL
    # ------------------------------------------------------------------

    @classmethod
    def read_wsl_file(cls, wsl_path):
        """
        Reads a text file from the WSL filesystem.
        Useful for reading BBP output files (logs, result files) after
        a simulation completes.

        Args:
            wsl_path (str): Full WSL path of the file to read.

        Returns:
            tuple: (bool: success, str: file_content or error_message)

        Example:
            ok, content = WSLBridge.read_wsl_file(
                "/home/black/bbp_projects/session/output/results.txt"
            )
        """
        result = cls.run_command(f"cat '{wsl_path}'")
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, result.stdout

    # ------------------------------------------------------------------
    # LIST FILES IN WSL DIRECTORY
    # ------------------------------------------------------------------

    @classmethod
    def list_wsl_dir(cls, wsl_path, extension=None):
        """
        Lists files inside a WSL directory, optionally filtered by extension.
        Useful for the Results panel to discover BBP output files.

        Args:
            wsl_path  (str)       : Full WSL path of the directory.
            extension (str|None)  : Optional filter e.g. ".png", ".csv", ".bbp"

        Returns:
            tuple: (bool: success, list: filenames or [], str: error)

        Example:
            ok, files, err = WSLBridge.list_wsl_dir(
                "/home/black/bbp_projects/session/output", ".png"
            )
        """
        if extension:
            cmd = f"ls '{wsl_path}'/*{extension} 2>/dev/null"
        else:
            cmd = f"ls '{wsl_path}' 2>/dev/null"

        result = cls.run_command(cmd)

        if result.returncode != 0:
            return False, [], result.stderr.strip()

        files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
        return True, files, ""

    # ------------------------------------------------------------------
    # CHECK IF PATH EXISTS IN WSL
    # ------------------------------------------------------------------

    @classmethod
    def wsl_path_exists(cls, wsl_path):
        """
        Checks whether a file or directory exists inside WSL.

        Args:
            wsl_path (str): Full WSL path to check.

        Returns:
            bool: True if the path exists, False otherwise.

        Example:
            if WSLBridge.wsl_path_exists("/home/black/bbp_projects"):
                print("Project folder found")
        """
        result = cls.run_command(f"test -e '{wsl_path}' && echo exists")
        return "exists" in result.stdout

    # ------------------------------------------------------------------
    # RUN BBP SIMULATION (BLOCKING)
    # ------------------------------------------------------------------

    @classmethod
    def run_bbp_simulation(cls, xml_path):
        """
        Runs the BBP simulation inside WSL using the provided XML options file.
        This is a BLOCKING call — it waits for BBP to finish before returning.
        For real-time output streaming, use run_bbp_simulation_stream() instead.
        """
        cmd = cls._bbp_cmd(xml_path)
        result = cls.run_command(cmd)
        success = result.returncode == 0
        return success, result.stdout, result.stderr

    # ------------------------------------------------------------------
    # BBP RUN ID DETECTION
    # ------------------------------------------------------------------

    @classmethod
    def get_bbp_run_id(cls):
        """
        Returns the most recently created BBP run ID by checking
        the outdata folder for the newest subdirectory.
        BBP names run folders with a numeric ID (e.g. 8956506).

        Returns:
            str: The run ID string, or "" if not found.
        """
        bbp_data = cls.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            return ""

        # List outdata subdirs sorted by creation time, get the newest
        result = cls.run_command(
            f"ls -t '{bbp_data}/outdata/' 2>/dev/null | head -1"
        )
        run_id = result.stdout.strip()
        return run_id if run_id else ""

    # ------------------------------------------------------------------
    # COLLECT BBP RESULTS INTO SESSION FOLDER
    # ------------------------------------------------------------------

    @classmethod
    def collect_bbp_results(cls, run_id, session_output_path):
        """
        Copies BBP output files from BBP's own data directories into
        the GUI session output folder so all results are organized
        under the session created by AppConfig.

        Copies from:
            $BBP_DATA_DIR/outdata/<run_id>/   -> session/output/outdata/
            $BBP_DATA_DIR/logs/<run_id>/      -> session/output/logs/
            $BBP_DATA_DIR/xml/<run_id>.xml    -> session/output/

        Args:
            run_id              (str): BBP run ID (e.g. "8956506")
            session_output_path (str): WSL path to the session output/ folder

        Returns:
            tuple: (bool: success, str: error message or "")
        """
        if not run_id:
            return False, "No BBP run ID found — cannot collect results."

        bbp_data = cls.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            return False, "BBP_DATA_DIR not set in WSL environment."

        # Build source paths
        src_outdata = f"{bbp_data}/outdata/{run_id}"
        src_logs    = f"{bbp_data}/logs/{run_id}"
        src_xml     = f"{bbp_data}/xml/{run_id}.xml"

        # Build destination paths inside session output folder
        dst_outdata = f"{session_output_path}/outdata"
        dst_logs    = f"{session_output_path}/logs"

        # Create destination directories
        ok, err = cls.make_wsl_dirs(dst_outdata, dst_logs)
        if not ok:
            return False, f"Could not create output dirs: {err}"

        # Copy outdata folder
        result = cls.run_command(
            f"cp -r '{src_outdata}/.' '{dst_outdata}/' 2>&1"
        )
        if result.returncode != 0:
            return False, f"Failed to copy outdata: {result.stdout.strip()}"

        # Copy logs folder
        result = cls.run_command(
            f"cp -r '{src_logs}/.' '{dst_logs}/' 2>/dev/null || true"
        )

        # Copy XML file
        cls.run_command(
            f"cp '{src_xml}' '{session_output_path}/' 2>/dev/null || true"
        )

        return True, ""

    # ------------------------------------------------------------------
    # RUN BBP SIMULATION (STREAMING — for live GUI log panel)
    # ------------------------------------------------------------------

    @classmethod
    def run_bbp_simulation_stream(cls, xml_path, session_output_path,
                                  on_output, on_finish):
        """
        Runs the BBP simulation inside WSL and streams stdout line by line
        to a callback function. After completion, automatically collects
        BBP results into the GUI session output folder.

        Args:
            xml_path            (str)     : Full WSL path to the BBP XML file.
            session_output_path (str)     : WSL path to session output/ folder.
            on_output           (callable): Called with each output line (str).
            on_finish           (callable): Called on end with (bool, str, str).
                                            Args: success, error_msg, run_id
        """
        import threading

        def _run():
            try:
                # Capture run ID before simulation so we know which
                # folder BBP will create (newest after run completes)
                bbp_cmd = cls._bbp_cmd(xml_path)

                if cls.IS_WINDOWS:
                    full_cmd = ["wsl", "bash", "-c", bbp_cmd]
                else:
                    full_cmd = ["bash", "-c", bbp_cmd]

                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process.stdout:
                    on_output(line)

                process.wait()
                success = process.returncode == 0

                if success:
                    # Get the run ID BBP just created
                    run_id = cls.get_bbp_run_id()

                    # Copy results into our session folder
                    ok, err = cls.collect_bbp_results(
                        run_id, session_output_path
                    )

                    if ok:
                        on_finish(True, "", run_id)
                    else:
                        # Simulation succeeded but copy failed
                        on_finish(True, f"Results copy failed: {err}", run_id)
                else:
                    on_finish(False, "BBP exited with errors.", "")

            except Exception as e:
                on_finish(False, str(e), "")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    # ------------------------------------------------------------------
    # RUN BBP VALIDATION (STREAMING — interactive stdin mode)
    # ------------------------------------------------------------------

    @classmethod
    def run_validation_stream(cls, event_number, method_number,
                              on_output, on_finish):
        """
        Runs a BBP validation simulation in interactive mode by piping
        the three answers BBP expects: y, event_number, method_number.
        Streams stdout line by line to on_output callback.

        Args:
            event_number  (int)     : BBP event number (e.g. 1 for Chino Hills)
            method_number (int)     : BBP method number (e.g. 1 for GP)
            on_output     (callable): Called with each output line (str)
            on_finish     (callable): Called on end with (bool, str, str)
                                      Args: success, error_msg, run_id
        """
        import threading

        def _run():
            try:
                env_path = cls._get_bbp_env_path()

                # Build the command — pipe three answers to run_bbp.py
                # BBP asks: validation? → y
                #           event?      → event_number
                #           method?     → method_number
                answers  = f"y\n{event_number}\n{method_number}\n"
                bbp_cmd  = (
                    f"source '{env_path}' && "
                    f"echo -e '{answers.strip()}' | run_bbp.py"
                )

                if cls.IS_WINDOWS:
                    full_cmd = ["wsl", "bash", "-c", bbp_cmd]
                else:
                    full_cmd = ["bash", "-c", bbp_cmd]

                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process.stdout:
                    on_output(line)

                process.wait()

                # BBP sometimes exits with non-zero code even on success
                # (e.g. FAS module exits non-zero on GMPE events).
                # Detect success by checking if output files were generated
                # rather than trusting the return code.
                run_id = cls.get_bbp_run_id()

                if run_id:
                    # Check if .vel.bbp files exist — definitive success indicator
                    bbp_data = cls.run_command("echo $BBP_DATA_DIR").stdout.strip()
                    if not bbp_data:
                        home = cls.get_wsl_home()
                        bbp_data = f"{home}/bbp_data"
                    check = cls.run_command(
                        f"ls '{bbp_data}/outdata/{run_id}'/*.vel.bbp 2>/dev/null | wc -l"
                    )
                    has_output = check.stdout.strip() not in ("", "0")
                    if has_output:
                        on_finish(True, "", run_id)
                    else:
                        on_finish(False, "BBP validation exited with errors.", "")
                else:
                    on_finish(False, "BBP validation exited with errors.", "")

            except Exception as e:
                on_finish(False, str(e), "")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()