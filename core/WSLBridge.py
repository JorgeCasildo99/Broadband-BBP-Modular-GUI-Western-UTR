import subprocess
import platform

from core import WSLRuntime, WSLShell


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

    Windows-specific behavior (distro choice, UTF-8 decoding, hidden
    console windows, shell mode, saved settings) lives in WSLRuntime.
    """

    # Detect if we are running on Windows (WSL needed) or native Linux
    IS_WINDOWS = platform.system() == "Windows"

    # Path to the BBP Python virtual environment.
    # Sourced before every BBP call to ensure all dependencies are available.
    # Dynamically resolved from WSL home at first use.
    BBP_ENV_PATH = ""

    # Answers that cannot change during a session. Each uncached call
    # costs a wsl.exe launch, and the project asks for these ~25 times.
    _CACHEABLE_QUERIES = ("echo $HOME", "echo $BBP_DATA_DIR")
    _query_cache = {}

    @classmethod
    def clear_query_cache(cls):
        """Forget cached answers (distro, shell mode or BBP env changed)."""
        cls._query_cache.clear()

    @classmethod
    def _get_bbp_env_path(cls):
        """
        Returns the bbp_env activation path, resolving it dynamically
        from the WSL home directory if not already set.
        """
        if not cls.BBP_ENV_PATH:
            saved = WSLRuntime.load_config().get("bbp_activate")
            if saved:
                cls.BBP_ENV_PATH = saved
            else:
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
            key = cmd.strip()
            cacheable = (input_data is None and capture
                         and key in cls._CACHEABLE_QUERIES)
            if cacheable and key in cls._query_cache:
                return cls._query_cache[key]

            # Fast path: a long-lived shell avoids the ~100 ms wsl.exe
            # launch. Returns None whenever it can't help (not Windows,
            # busy, disabled), and the normal path below takes over.
            if capture and input_data is None:
                fast = WSLShell.run(cmd)
                if fast is not None:
                    if (cacheable and fast.returncode == 0
                            and (fast.stdout or "").strip()):
                        cls._query_cache[key] = fast
                    return fast

            # WSLRuntime targets the chosen distro through wsl.exe on
            # Windows, or runs bash directly on native Linux.
            full_cmd = WSLRuntime.build_command(cmd)

            result = subprocess.run(
                full_cmd,
                input=input_data,
                capture_output=capture,
                **WSLRuntime.subprocess_kwargs(has_input=input_data is not None)
            )
            if (cacheable and result.returncode == 0
                    and (result.stdout or "").strip()):
                cls._query_cache[key] = result
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
            # Pick (and remember) which installed distro to use. A
            # machine with WSL but no Linux distribution cannot run BBP.
            distro = WSLRuntime.initialize()
            cls.clear_query_cache()
            WSLShell.reset()
            if not distro:
                return False, "No Linux distribution found in WSL"
            label = f" ({distro})"

            # `wsl --version` prints UTF-16, so read bytes and decode.
            result = subprocess.run(
                ["wsl.exe", "--version"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=10,
                **WSLRuntime.hidden_window_kwargs()
            )

            if result.returncode == 0:
                text = WSLRuntime.decode_wsl_output(result.stdout).strip()
                lines = text.splitlines()
                version = lines[0] if lines else "WSL Available"
                return True, version + label
            else:
                # wsl --version failed (older WSL), try a simple echo
                fallback = cls.run_command("echo ok")
                if fallback.returncode == 0:
                    return True, "WSL Available" + label
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
        Checks BBP and, if the first attempt fails, tries to repair the
        connection automatically before reporting failure:

          1. Windows only: retry with an interactive shell (`bash -ic`),
             because `bash -c` skips ~/.bashrc where BBP_DIR and
             BBP_DATA_DIR are usually exported.
          2. Look for the Python environment that actually provides
             run_bbp.py, in case it is not at ~/bbp_env.

        Whatever works is saved to the user's config so later launches
        skip the search. If nothing works, the status of the first
        (default) attempt is returned so its details are what the user
        sees. Returns the same dict as _probe_bbp_environment().
        """
        first_status = cls._probe_bbp_environment()
        if first_status["connected"]:
            return first_status

        original_flags = WSLRuntime.get_shell_flags()
        original_env   = cls.BBP_ENV_PATH

        flag_options = [original_flags]
        if cls.IS_WINDOWS and original_flags != "-ic":
            flag_options.append("-ic")

        for flags in flag_options:
            WSLRuntime.set_shell_flags(flags)

            if flags != original_flags:
                status = cls._probe_bbp_environment()
                if status["connected"]:
                    WSLRuntime.remember(shell_flags=flags)
                    cls._finish_interactive_repair(flags)
                    return status

            detected = WSLRuntime.detect_bbp_activate(cls.run_command)
            if detected and detected != cls._get_bbp_env_path():
                cls.BBP_ENV_PATH = detected
                status = cls._probe_bbp_environment()
                if status["connected"]:
                    WSLRuntime.remember(shell_flags=flags, bbp_activate=detected)
                    cls._finish_interactive_repair(flags)
                    return status
                cls.BBP_ENV_PATH = original_env

        WSLRuntime.set_shell_flags(original_flags)
        return first_status

    @classmethod
    def _finish_interactive_repair(cls, flags):
        """
        Interactive mode works but reloads ~/.bashrc on every call, which
        is slow. Capture its BBP environment once so later calls can use
        a fast plain shell, and drop any answers cached before the repair.
        """
        if flags == "-ic":
            WSLRuntime.capture_env_preamble()
        cls.clear_query_cache()
        WSLShell.reset()

    @classmethod
    def _probe_bbp_environment(cls):
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
    # WINDOWS PATH -> WSL PATH
    # ------------------------------------------------------------------

    @classmethod
    def windows_to_wsl_path(cls, path):
        """
        Converts a Windows path (e.g. from a file dialog) into the WSL
        path of the same file, using `wslpath` inside the chosen distro.
        Panels must call this instead of invoking wsl.exe themselves, so
        the distro choice and hidden-window settings are always applied.
        On native Linux the path is returned unchanged.

        Returns:
            tuple: (bool: success, str: wsl_path or error_message)
        """
        if not cls.IS_WINDOWS:
            return True, path
        safe = path.replace("'", "'\\''")
        result = cls.run_command(f"wslpath -u '{safe}'")
        out = (result.stdout or "").strip()
        if result.returncode == 0 and out:
            return True, out
        return False, (result.stderr or "wslpath failed").strip()

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
            # Encode as UTF-8 with Unix line endings (\n only).
            # Using bytes + text=False prevents Windows from converting
            # \n → \r\n, which breaks Fortran file readers in ExSIM/BBP.
            content_bytes = content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")

            full_cmd = WSLRuntime.build_command(f"cat > '{wsl_path}'")

            result = subprocess.run(
                full_cmd,
                input=content_bytes,
                capture_output=True,
                text=False,
                **WSLRuntime.hidden_window_kwargs()
            )

            if result.returncode != 0:
                return False, result.stderr.decode("utf-8", errors="replace").strip()
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
    def list_wsl_dir_detailed(cls, wsl_path):
        """
        Lists the contents of a WSL directory, separating folders from files.

        Returns:
            tuple: (bool: success, list: folders, list: files, str: error)
            folders and files are sorted lists of names (not full paths).
        """
        cmd = f"ls -1p '{wsl_path}' 2>/dev/null"
        result = cls.run_command(cmd)
        if result.returncode != 0:
            return False, [], [], result.stderr.strip()

        folders = []
        files   = []
        for entry in result.stdout.strip().splitlines():
            entry = entry.strip()
            if not entry:
                continue
            if entry.endswith("/"):
                folders.append(entry.rstrip("/"))
            else:
                files.append(entry)

        return True, sorted(folders), sorted(files), ""

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

                full_cmd = WSLRuntime.build_command(bbp_cmd)

                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    **WSLRuntime.subprocess_kwargs()
                )

                for line in process.stdout:
                    if not WSLRuntime.is_shell_noise(line):
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

                full_cmd = WSLRuntime.build_command(bbp_cmd)

                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    **WSLRuntime.subprocess_kwargs()
                )

                for line in process.stdout:
                    if not WSLRuntime.is_shell_noise(line):
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

    # ------------------------------------------------------------------
    # ADVANCED GP PARAMETERS (velmodel config file read/write)
    # ------------------------------------------------------------------
    #
    # These read/write the six GP Advanced Settings parameters from/to
    # the velocity model config file (e.g. labasin500_velmodel_config.txt).
    # Lines look like:
    #   CODEBASE_GP_KAPPA = 0.0400          <- active (uncommented)
    #   #CODEBASE_GP_SDROP = 50             <- override/absent (commented)
    #
    # Mapping between the short key used throughout the GUI (KAPPA,
    # QFEXP, SDROP, MEAN_RVFAC, RANGE_RVFAC, RISETIME_COEF) and the
    # full config-file key (CODEBASE_GP_<key>) is fixed and mirrors
    # PARAM_DEFS in AdvancedSettingsPanel.py exactly.

    _ADV_PARAM_FULL_KEYS = {
        "KAPPA"        : "CODEBASE_GP_KAPPA",
        "QFEXP"        : "CODEBASE_GP_QFEXP",
        "SDROP"        : "CODEBASE_GP_SDROP",
        "MEAN_RVFAC"   : "CODEBASE_GP_MEAN_RVFAC",
        "RANGE_RVFAC"  : "CODEBASE_GP_RANGE_RVFAC",
        "RISETIME_COEF": "CODEBASE_GP_RISETIME_COEF",
    }

    # Mirrors PARAM_DEFS["decimals"] in AdvancedSettingsPanel.py exactly.
    # write_advanced_params() needs this because the params dict passed
    # in from AdvancedSettingsPanel._save_all() only carries "value" and
    # "enabled" — never "decimals" — so the display precision used when
    # formatting each line has to be looked up here, not guessed.
    _ADV_PARAM_DECIMALS = {
        "KAPPA"        : 4,
        "QFEXP"        : 3,
        "SDROP"        : 0,
        "MEAN_RVFAC"   : 3,
        "RANGE_RVFAC"  : 3,
        "RISETIME_COEF": 2,
    }

    @classmethod
    def read_advanced_params(cls, cfg_path):
        """
        Reads the six GP Advanced Settings parameters from a velmodel
        config file.

        Returns a dict: { short_key: {"value": float, "enabled": bool} }
        for every recognized parameter line found (commented or not).
        A key is absent from the returned dict entirely if no matching
        line (commented or active) exists in the file at all.

        Returns None if the file could not be read.
        """
        ok, content = cls.read_wsl_file(cfg_path)
        if not ok or content is None:
            return None

        full_to_short = {v: k for k, v in cls._ADV_PARAM_FULL_KEYS.items()}
        result = {}

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            enabled = not line.startswith("#")
            uncommented = line.lstrip("#").strip()

            if "=" not in uncommented:
                continue

            full_key, _, val_str = uncommented.partition("=")
            full_key = full_key.strip()
            val_str  = val_str.strip()

            short_key = full_to_short.get(full_key)
            if short_key is None:
                continue

            try:
                value = float(val_str)
            except ValueError:
                continue

            result[short_key] = {"value": value, "enabled": enabled}

        return result

    @classmethod
    def write_advanced_params(cls, cfg_path, params):
        """
        Writes the six GP Advanced Settings parameters to a velmodel
        config file, preserving every other line untouched.

        Args:
            cfg_path (str)  : WSL path to the velmodel config file.
            params   (dict) : { short_key: {"value": float, ...} }
                               Only "value" and "enabled" are read;
                               any extra keys (e.g. is_custom) are
                               ignored. "enabled" controls whether the
                               written line is active (uncommented) or
                               an override placeholder (commented).

        Returns:
            (ok: bool, msg: str)
        """
        ok, content = cls.read_wsl_file(cfg_path)
        if not ok or content is None:
            return False, f"Could not read config file: {cfg_path}"

        full_to_short = {v: k for k, v in cls._ADV_PARAM_FULL_KEYS.items()}
        lines = content.splitlines()
        written_keys = set()

        for i, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line:
                continue

            uncommented = line.lstrip("#").strip()
            if "=" not in uncommented:
                continue

            full_key = uncommented.partition("=")[0].strip()
            short_key = full_to_short.get(full_key)
            if short_key is None or short_key not in params:
                continue

            p   = params[short_key]
            dec = cls._ADV_PARAM_DECIMALS.get(short_key, 4)
            val_str = f"{p['value']:.{dec}f}" if dec > 0 else str(int(round(p["value"])))
            new_line = f"{full_key} = {val_str}"
            if not p.get("enabled", False):
                new_line = f"#{new_line}"

            lines[i] = new_line
            written_keys.add(short_key)

        # Any param not found as an existing line (truly absent, e.g.
        # SDROP by default) gets appended — active if enabled, otherwise
        # appended commented so it's visible for future manual editing.
        for short_key, p in params.items():
            if short_key in written_keys:
                continue
            full_key = cls._ADV_PARAM_FULL_KEYS.get(short_key)
            if not full_key:
                continue
            dec = cls._ADV_PARAM_DECIMALS.get(short_key, 4)
            val_str = f"{p['value']:.{dec}f}" if dec > 0 else str(int(round(p["value"])))
            new_line = f"{full_key} = {val_str}"
            if not p.get("enabled", False):
                new_line = f"#{new_line}"
            lines.append(new_line)

        new_content = "\n".join(lines) + "\n"
        ok_write, err = cls.write_wsl_file(cfg_path, new_content)
        if not ok_write:
            return False, f"Failed to write config file: {err}"

        return True, "Saved successfully."

    # BBP's own hardcoded defaults (genslip_cfg.py / hfsims_cfg.py),
    # mirrors BBP_DEFAULTS in AdvancedSettingsPanel.py exactly.
    _ADV_PARAM_DEFAULTS = {
        "KAPPA"        : 0.04,
        "QFEXP"        : 0.6,
        "SDROP"        : 50,
        "MEAN_RVFAC"   : 0.775,
        "RANGE_RVFAC"  : 0.1,
        "RISETIME_COEF": 2.3,
    }

    @classmethod
    def reset_advanced_params_to_defaults(cls, cfg_path):
        """
        Resets all six GP Advanced Settings parameters in the velmodel
        config file back to BBP's own hardcoded defaults, all commented
        out — i.e. restores the file to the same state BBP ships with
        (KAPPA/QFEXP active at their BBP defaults, the rest commented).

        This exists separately from AdvancedSettingsPanel._reset_all_
        defaults() — that method only resets the *widgets* inside an
        open panel and does nothing until the user clicks Save. This
        method writes directly to disk, intended to be called whenever
        the user returns to the Dashboard, so leftover custom overrides
        from a previous session never silently carry into a future run
        without the user explicitly re-enabling them.

        Returns:
            (ok: bool, msg: str)
        """
        # KAPPA and QFEXP ship active (uncommented) in BBP's distributed
        # config; the other four ship commented out / absent.
        active_by_default = {"KAPPA", "QFEXP"}

        params = {
            key: {
                "value"  : default,
                "enabled": key in active_by_default,
            }
            for key, default in cls._ADV_PARAM_DEFAULTS.items()
        }

        return cls.write_advanced_params(cfg_path, params)

    @classmethod
    def detect_simulation_method(cls, run_id, outdata_path=None):
        """
        Detects which BBP method produced a given run by reading the
        'Simulation Method' field out of index-<run_id>.html. This is
        the single most reliable source for this — confirmed directly
        against a real ExSIM run, where the field reads 'EXSIM' (vs
        'GP' for Graves & Pitarka runs). More reliable than inferring
        from file presence/absence (e.g. .srf existing), since that
        requires guessing which files are method-specific.

        This is a FALLBACK ONLY — the primary detection source for
        every method is the "# METHOD = X" comment in the .src file,
        which is unambiguous and already correctly distinguishes all
        5 methods. This function only runs when that marker is missing
        (very old runs, or runs made outside the GUI).

        Args:
            run_id       (str)      : BBP numeric run ID.
            outdata_path (str|None) : Full WSL path to the run's outdata
                                       folder. If None, defaults to
                                       $BBP_DATA_DIR/outdata/<run_id>.

        Returns:
            str: "GP", "EXSIM", "IRIKURA1", "IRIKURA2", "SONG", "UCSB",
                 "SDSU", or "UNKNOWN" if detection fails.
        """
        if not run_id:
            return "UNKNOWN"

        if not outdata_path:
            bbp_data = cls.run_command("echo $BBP_DATA_DIR").stdout.strip()
            if not bbp_data:
                return "UNKNOWN"
            outdata_path = f"{bbp_data}/outdata/{run_id}"

        html_path = f"{outdata_path}/index-{run_id}.html"
        ok, content = cls.read_wsl_file(html_path)
        if not ok or not content:
            return "UNKNOWN"

        import re
        m = re.search(
            r'Simulation Method</td>\s*<td>\s*([^<]+)\s*</td>',
            content, re.IGNORECASE
        )
        if m:
            method = m.group(1).strip().upper()
            if "EXSIM" in method:
                return "EXSIM"
            if "SONG" in method:
                return "SONG"
            if "IRIKURA" in method:
                # Distinguish Method 1 from Method 2 by looking for a
                # "2" in the displayed text (e.g. "Irikura Recipe
                # Method 2" or "IRIKURA2"). NOT confirmed against a
                # real Irikura2 index.html — no such file has been
                # available to check BBP's exact wording here, unlike
                # the ExSIM confirmation above. If this fallback ever
                # misclassifies a real Irikura2 run, check the actual
                # HTML text and adjust this condition accordingly.
                if "2" in method:
                    return "IRIKURA2"
                return "IRIKURA1"
            if "GP" in method:
                return "GP"
            if "UCSB" in method:
                # Confirmed directly against a real UCSB index.html
                # (run 6907992): the field reads exactly "UCSB", the
                # same confirmation strength as the EXSIM case above.
                # This fallback matters more for UCSB than for other
                # methods: UCSB's .src file has NO "# METHOD = UCSB"
                # marker at all (unlike every other method), so UCSB
                # runs may rely on this HTML fallback more often in
                # practice, not just for very old runs.
                return "UCSB"
            if "SDSU" in method:
                # NOT confirmed against a real SDSU index.html — no
                # such file has been available to check BBP's exact
                # wording here, unlike the ExSIM/UCSB confirmations
                # above. Inferred from the literal "SDSU" method
                # argument used consistently throughout a real SDSU
                # XML (GenHTML/GPGof/FASGof/WccSiteamp all take "SDSU"
                # as a plain string argument) — same confidence level
                # as the Irikura2 fallback below GP. If this ever
                # misclassifies a real SDSU run, check the actual HTML
                # text and adjust this condition accordingly.
                return "SDSU"
            return method

        return "UNKNOWN"

    @classmethod
    def read_src_file(cls, run_id):
        """
        Reads the .src file for a given run_id from indata/<run_id>/.
        Returns (ok, content_str). Content is the full .src text.
        """
        bbp_data = cls.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{cls.get_wsl_home()}/bbp_data"

        indata_path = f"{bbp_data}/indata/{run_id}"

        # Try find first, then ls fallback
        r = cls.run_command(
            f"find '{indata_path}' -maxdepth 1 -name '*.src' 2>/dev/null | head -1"
        )
        src_path = r.stdout.strip()
        if not src_path:
            r = cls.run_command(
                f"ls '{indata_path}' 2>/dev/null | grep '[.]src' | head -1"
            )
            fname = r.stdout.strip()
            if fname:
                src_path = f"{indata_path}/{fname}"

        if not src_path:
            return False, ""

        return cls.read_wsl_file(src_path)

    @classmethod
    def read_stl_file(cls, run_id):
        """
        Reads the .stl file for a given run_id from indata/<run_id>/.
        Returns (ok, content_str). Each line: lon lat name.
        """
        bbp_data = cls.run_command("echo $BBP_DATA_DIR").stdout.strip()
        if not bbp_data:
            bbp_data = f"{cls.get_wsl_home()}/bbp_data"

        indata_path = f"{bbp_data}/indata/{run_id}"

        r = cls.run_command(
            f"find '{indata_path}' -maxdepth 1 -name '*.stl' 2>/dev/null | head -1"
        )
        stl_path = r.stdout.strip()
        if not stl_path:
            r = cls.run_command(
                f"ls '{indata_path}' 2>/dev/null | grep '[.]stl' | head -1"
            )
            fname = r.stdout.strip()
            if fname:
                stl_path = f"{indata_path}/{fname}"

        if not stl_path:
            return False, ""

        return cls.read_wsl_file(stl_path)