"""
WSLRuntime.py — core/WSLRuntime.py

Windows-side runtime helpers used by WSLBridge so the GUI can run as a
packaged Windows app that reaches BBP inside WSL. Everything here is
inert on native Linux except the config file and BBP auto-detection.

Handles four things the plain `wsl bash -c` calls do not:
  1. Text decoding   — Windows decodes subprocess output with the legacy
                       code page; WSL output is UTF-8.
  2. Console windows — a windowed .exe flashes a console on every call
                       unless CREATE_NO_WINDOW is set; it also needs an
                       explicit stdin when none is piped in.
  3. Distro choice   — plain `wsl` uses the default distro, which may be
                       docker-desktop. `wsl -l -v` prints UTF-16.
  4. User settings   — chosen distro and BBP environment live in
                       %APPDATA%\\BBP-GUI\\config.json instead of being
                       assumed (~/bbp_env).
  5. Shell mode      — `bash -c` skips ~/.bashrc, where BBP's variables
                       often live. WSLBridge falls back to `bash -ic`
                       only when the BBP check fails, and the choice is
                       remembered here.
  6. Log file        — a windowed .exe has no console, so tracebacks are
                       redirected to bbp-gui.log next to the config.
  7. Speed           — an interactive shell reloads ~/.bashrc on every
                       call. The BBP-related exports are captured ONCE
                       and re-applied to fast plain shells afterwards.
  8. UI scale        — native Windows applies the display scale (125%,
                       150%...) that WSLg never did; ui_scale() computes
                       the compensation so the layout keeps its design size.
  9. Persistent shell — launching wsl.exe costs ~100 ms per command, so
                       WSLShell keeps a few bash processes alive; this
                       module only describes how to start them.
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"

APP_NAME = "BBP-GUI"
_CREATE_NO_WINDOW = 0x08000000
_NON_USER_DISTROS = ("docker-desktop",)
_DEFAULT_CONFIG = {"distro": None, "bbp_activate": None,
                   "shell_flags": "-c", "ui_scale": None,
                   "persistent_shell": True}
_VALID_SHELL_FLAGS = ("-c", "-ic")

# Lines an interactive bash prints to stderr when it has no terminal.
# Harmless, but they would show up in the live simulation console.
_SHELL_NOISE_PREFIXES = (
    "bash: cannot set terminal process group",
    "bash: no job control in this shell",
)

# Prints `export NAME=value` for the variables BBP needs, as an
# interactive shell sees them (so ~/.bashrc has been applied).
_ENV_CAPTURE_SCRIPT = (
    'for v in $(compgen -e); do case "$v" in '
    'BBP_*|PYTHONPATH|PATH|LD_LIBRARY_PATH) '
    'echo "export $v=$(printf %q "${!v}")";; esac; done'
)

_active_distro = None
_shell_flags = "-c"
_env_preamble = ""


# ----------------------------------------------------------------------
# SUBPROCESS SETTINGS
# ----------------------------------------------------------------------

def subprocess_kwargs(has_input=False):
    """
    Keyword arguments to pass to every subprocess.run / Popen that talks
    to WSL. Pass has_input=True when the call also uses input=..., since
    subprocess rejects an explicit stdin together with input.
    """
    kwargs = {"encoding": "utf-8", "errors": "replace"}
    if IS_WINDOWS:
        kwargs["creationflags"] = _CREATE_NO_WINDOW
    if not has_input:
        kwargs["stdin"] = subprocess.DEVNULL
    return kwargs


def hidden_window_kwargs():
    """Only the no-console flag, for calls that must stay in bytes mode."""
    return {"creationflags": _CREATE_NO_WINDOW} if IS_WINDOWS else {}


def is_shell_noise(line):
    """True for harmless startup chatter from an interactive bash."""
    return line.startswith(_SHELL_NOISE_PREFIXES)


# ----------------------------------------------------------------------
# DISTRO DETECTION
# ----------------------------------------------------------------------

def decode_wsl_output(raw):
    """
    Decodes the raw bytes printed by wsl.exe's own commands (-l, -v...),
    which are UTF-16 on most Windows builds and UTF-8 when WSL_UTF8 is
    set. Returns text with BOMs and carriage returns removed.
    """
    if not raw:
        return ""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16", errors="replace")
    elif b"\x00" in raw:
        text = raw.decode("utf-16-le", errors="replace")
    else:
        text = raw.decode("utf-8", errors="replace")
    return text.replace("\ufeff", "").replace("\r", "")


def list_distros():
    """
    Returns installed WSL distros as a list of dicts:
        {"name", "state", "version", "default"}
    Empty list if WSL is missing or has no distros. The header row is
    skipped by position, not by text, because it is localized.
    """
    if not IS_WINDOWS:
        return []
    try:
        proc = subprocess.run(
            ["wsl.exe", "-l", "-v"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode != 0:
        return []

    lines = [ln for ln in decode_wsl_output(proc.stdout).split("\n") if ln.strip()]
    distros = []
    for line in lines[1:]:
        is_default = line.lstrip().startswith("*")
        tokens = line.replace("*", " ").split()
        # A real row is: NAME STATE VERSION. The version check also
        # filters out the "no installed distributions" message.
        if len(tokens) < 3 or tokens[-1] not in ("1", "2"):
            continue
        distros.append({
            "name": tokens[0],
            "state": tokens[1],
            "version": tokens[-1],
            "default": is_default,
        })
    return distros


def pick_distro(distros, preferred=None):
    """
    Chooses which distro to run BBP in: the saved choice if it still
    exists, else the default distro, else the first Ubuntu, else the
    first distro. Docker's internal distros are never chosen.
    """
    usable = [d for d in distros
              if not d["name"].lower().startswith(_NON_USER_DISTROS)]
    if not usable:
        return None
    if preferred:
        for d in usable:
            if d["name"] == preferred:
                return d["name"]
    for d in usable:
        if d["default"]:
            return d["name"]
    for d in usable:
        if d["name"].lower().startswith("ubuntu"):
            return d["name"]
    return usable[0]["name"]


def set_active_distro(name):
    global _active_distro
    _active_distro = name


def get_active_distro():
    return _active_distro


def shell_signature():
    """Identity of the current shell setup; a long-lived shell is only
    reused while this is unchanged."""
    return (_active_distro, _shell_flags, _env_preamble)


def build_persistent_shell():
    """
    How to start a long-lived bash for WSLShell: (argv, preamble), or
    None when the current mode needs a real interactive shell per call
    (interactive mode without a captured environment) or on Linux.
    """
    if not IS_WINDOWS:
        return None
    if _shell_flags == "-ic" and not _env_preamble:
        return None
    prefix = ["wsl.exe", "-d", _active_distro] if _active_distro else ["wsl.exe"]
    preamble = _env_preamble if _shell_flags == "-ic" else ""
    return prefix + ["--exec", "bash", "--noprofile", "--norc"], preamble


def capture_env_preamble(distro=None):
    """
    Runs ONE interactive shell and stores its BBP-related exports
    (BBP_*, PYTHONPATH, PATH, LD_LIBRARY_PATH) as a preamble that
    build_command() prepends to plain `bash -c` calls. This keeps the
    correct environment without paying for ~/.bashrc on every call.
    Returns the preamble, or "" if capture failed (every call then
    falls back to a full interactive shell: correct, just slower).
    """
    global _env_preamble
    _env_preamble = ""
    if not IS_WINDOWS:
        return ""
    target = distro or _active_distro
    prefix = ["wsl.exe", "-d", target] if target else ["wsl.exe"]
    try:
        proc = subprocess.run(
            prefix + ["--exec", "bash", "-ic", _ENV_CAPTURE_SCRIPT],
            capture_output=True, timeout=30, **subprocess_kwargs())
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines()
             if ln.startswith("export ")]
    if not any(ln.startswith("export BBP_") for ln in lines):
        return ""
    _env_preamble = "; ".join(lines) + "; "
    return _env_preamble


def set_shell_flags(flags):
    global _shell_flags
    if flags in _VALID_SHELL_FLAGS:
        _shell_flags = flags


def get_shell_flags():
    return _shell_flags


def build_command(cmd, distro=None):
    """
    Builds the argument list that runs `cmd` in bash: through wsl.exe
    --exec (targeting the active distro, using the active shell flags)
    on Windows, directly on Linux.
    """
    if not IS_WINDOWS:
        return ["bash", "-c", cmd]
    target = distro or _active_distro
    prefix = ["wsl.exe", "-d", target] if target else ["wsl.exe"]
    # Fast path: the interactive environment was captured once, so every
    # call can use a plain shell instead of reloading ~/.bashrc.
    if _shell_flags == "-ic" and _env_preamble:
        return prefix + ["--exec", "bash", "-c", _env_preamble + cmd]
    # --exec matters: without it, wsl.exe first passes the whole command
    # line through the default Linux shell, which expands every $VARIABLE
    # in `cmd` (BBP_DIR, BBP_DATA_DIR...) before bash ever sees it. That
    # outer shell does not load ~/.bashrc, so they always came out empty.
    return prefix + ["--exec", "bash", _shell_flags, cmd]


# ----------------------------------------------------------------------
# USER CONFIG
# ----------------------------------------------------------------------

def config_path():
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_NAME, "config.json")


def load_config():
    cfg = dict(_DEFAULT_CONFIG)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def remember(**updates):
    """Merges `updates` into the saved config. Never raises."""
    cfg = load_config()
    cfg.update(updates)
    try:
        save_config(cfg)
    except OSError:
        pass


def ui_scale(dpi_scale):
    """
    Value for customtkinter's set_widget_scaling / set_window_scaling.
    CustomTkinter multiplies everything by the monitor's display scale
    on Windows (and by 1 under WSLg), so the layout looks bigger than it
    was designed. Dividing by it restores the design size; the optional
    "ui_scale" in config.json (e.g. 1.2 for 20% larger) is applied on top.
    """
    if not IS_WINDOWS:
        return 1.0
    wanted = load_config().get("ui_scale") or 1.0
    try:
        wanted = float(wanted)
    except (TypeError, ValueError):
        wanted = 1.0
    return max(0.4, min(3.0, wanted / max(dpi_scale, 0.5)))


# ----------------------------------------------------------------------
# LOG FILE (windowed executable has no console)
# ----------------------------------------------------------------------

def log_path():
    return os.path.join(os.path.dirname(config_path()), "bbp-gui.log")


def redirect_output_to_log():
    """
    Call as early as possible. When stdout/stderr do not exist (windowed
    .exe, pythonw), sends both to bbp-gui.log so tracebacks and print()
    output are not lost. Does nothing when a console is attached.
    Returns the log path if it redirected, else None.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None
    path = log_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
            os.replace(path, path + ".old")
        stream = open(path, "a", encoding="utf-8", buffering=1)
    except OSError:
        return None
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    stream.write(f"\n--- BBP-GUI started {datetime.now():%Y-%m-%d %H:%M:%S} ---\n")
    return path


# ----------------------------------------------------------------------
# STARTUP + BBP ENVIRONMENT DETECTION
# ----------------------------------------------------------------------

def initialize():
    """
    Call once at startup, before any WSL command. On Windows, picks and
    remembers the distro to use. Returns the chosen distro name, or None
    (also None on native Linux, where no distro is needed).
    """
    if not IS_WINDOWS:
        return None
    cfg = load_config()
    set_shell_flags(cfg.get("shell_flags"))
    chosen = pick_distro(list_distros(), cfg.get("distro"))
    set_active_distro(chosen)
    if chosen and get_shell_flags() == "-ic":
        capture_env_preamble(chosen)
    if chosen and cfg.get("distro") != chosen:
        cfg["distro"] = chosen
        try:
            save_config(cfg)
        except OSError:
            pass
    return chosen


def detect_bbp_activate(run):
    """
    Finds the Python environment activate script that provides BBP.
    Judged by behavior, not by folder name: a candidate counts only if
    sourcing it puts run_bbp.py on PATH.

    Args:
        run (callable): run(cmd) -> object with .returncode and .stdout,
                        executing cmd in bash inside WSL (e.g.
                        WSLBridge.run_command).
    Returns:
        str | None: absolute path to the activate script.
    """
    found = run("find \"$HOME\" -maxdepth 4 -path '*/bin/activate' "
                "-type f 2>/dev/null | head -20")
    candidates = [ln.strip() for ln in (found.stdout or "").splitlines()
                  if ln.strip()]
    candidates.sort(key=lambda p: "bbp" not in p.lower())

    for path in candidates:
        probe = run(f"source '{path}' && command -v run_bbp.py")
        if probe.returncode == 0 and (probe.stdout or "").strip():
            return path
    return None