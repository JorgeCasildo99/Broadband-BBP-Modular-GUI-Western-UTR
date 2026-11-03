"""
WSLShell.py — core/WSLShell.py

Runs the GUI's short WSL commands through a few long-lived `bash`
processes instead of launching wsl.exe for every command. Starting
wsl.exe costs ~100 ms per call no matter what the command is, and some
screens make well over a hundred calls; a command sent to an already
running shell costs a few milliseconds.

How a command travels (the only way, so the protocol cannot desync):
  1. The command is base64-encoded, so quotes, newlines, `exit` or a
     syntax error in it can never confuse the long-lived shell.
  2. The shell decodes it and runs it in a FRESH `bash -c`, exactly the
     way the old per-call approach did (no state leaks between calls).
  3. stdout, stderr and the exit code come back between random markers.

Safe by design: run() returns None whenever it cannot help (not on
Windows, disabled in config, all shells busy, shell died), and the
caller then uses its normal one-process-per-call path. After repeated
failures the feature switches itself off for the session.

Turn it off manually with  "persistent_shell": false  in
%APPDATA%\\BBP-GUI\\config.json.
"""

import atexit
import base64
import subprocess
import threading
import uuid

from core import WSLRuntime

_MAX_SHELLS = 3        # concurrent commands beyond this use a plain spawn
_MAX_FAILURES = 3      # shell crashes tolerated before giving up

_lock = threading.Lock()
_idle = []
_total = 0
_failures = 0
_disabled = False
_generation = 0
_config_enabled = None


class ShellDied(Exception):
    """The long-lived shell exited or its pipe broke."""


class _Shell:
    def __init__(self, argv, preamble, signature):
        self.signature = signature
        self._proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            **WSLRuntime.hidden_window_kwargs()
        )
        # Handshake: apply the captured BBP environment, prove it's alive.
        token = uuid.uuid4().hex
        self._send(f"{preamble}echo @@{token}:READY\n")
        self._read_until(f"@@{token}:READY")

    def alive(self):
        return self._proc.poll() is None

    def close(self):
        for closer in (self._proc.stdin.close, self._proc.terminate):
            try:
                closer()
            except (OSError, ValueError):
                pass

    def _send(self, text):
        try:
            self._proc.stdin.write(text.encode("utf-8"))
            self._proc.stdin.flush()
        except (OSError, ValueError):
            raise ShellDied("could not write to shell")

    def _read_until(self, marker):
        """Reads raw lines until one starts with `marker`; returns all."""
        chunks = []
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise ShellDied("shell closed its output")
            chunks.append(line)
            if line.startswith(marker.encode("ascii")):
                return b"".join(chunks)

    def execute(self, cmd):
        """Runs cmd; returns a CompletedProcess-like result."""
        if not self.alive():
            raise ShellDied("shell already exited")
        token = uuid.uuid4().hex
        encoded = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
        self._send(
            f"__c=$(printf %s '{encoded}' | base64 -d); "
            f"__o=$(mktemp); __e=$(mktemp)\n"
            f"bash -c \"$__c\" </dev/null >\"$__o\" 2>\"$__e\"; __rc=$?\n"
            f"printf '\\n@@{token}:OUT\\n'; cat \"$__o\"\n"
            f"printf '\\n@@{token}:ERR\\n'; cat \"$__e\"\n"
            f"printf '\\n@@{token}:RC:%s\\n' \"$__rc\"; rm -f \"$__o\" \"$__e\"\n"
        )
        raw = self._read_until(f"@@{token}:RC:")
        text = raw.decode("utf-8", errors="replace")

        out_mark = f"\n@@{token}:OUT\n"
        err_mark = f"\n@@{token}:ERR\n"
        rc_mark = f"\n@@{token}:RC:"
        try:
            i = text.index(out_mark) + len(out_mark)
            j = text.index(err_mark, i)
            k = text.index(rc_mark, j)
            returncode = int(text[k + len(rc_mark):].strip())
        except ValueError:
            raise ShellDied("malformed reply")

        # Same newline handling as subprocess text mode.
        def norm(s):
            return s.replace("\r\n", "\n").replace("\r", "\n")

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout=norm(text[i:j]),
            stderr=norm(text[j + len(err_mark):k]),
        )


# ----------------------------------------------------------------------
# POOL
# ----------------------------------------------------------------------

def _signature():
    return WSLRuntime.shell_signature() + (_generation,)


def enabled():
    global _config_enabled
    if _disabled or not WSLRuntime.IS_WINDOWS:
        return False
    if _config_enabled is None:
        _config_enabled = bool(WSLRuntime.load_config().get("persistent_shell", True))
    return _config_enabled


def _acquire(spec, signature):
    global _total, _failures, _disabled
    with _lock:
        while _idle:
            shell = _idle.pop()
            if shell.signature == signature and shell.alive():
                return shell
            shell.close()
            _total -= 1
        if _total >= _MAX_SHELLS:
            return None
        _total += 1
    try:
        return _Shell(spec[0], spec[1], signature)
    except (OSError, ShellDied):
        with _lock:
            _total -= 1
            _failures += 1
            if _failures >= _MAX_FAILURES:
                _disabled = True
        return None


def _release(shell):
    global _total
    with _lock:
        if shell.signature == _signature() and shell.alive():
            _idle.append(shell)
        else:
            shell.close()
            _total -= 1


def run(cmd):
    """
    Runs `cmd` through a persistent shell. Returns a CompletedProcess,
    or None when the caller must use its normal spawn path instead.
    """
    global _total, _failures, _disabled
    if not enabled():
        return None
    spec = WSLRuntime.build_persistent_shell()
    if spec is None:
        return None
    shell = _acquire(spec, _signature())
    if shell is None:
        return None
    try:
        result = shell.execute(cmd)
    except ShellDied:
        shell.close()
        with _lock:
            _total -= 1
            _failures += 1
            if _failures >= _MAX_FAILURES:
                _disabled = True
        return None
    _release(shell)
    return result


def reset():
    """Closes every shell; the next call starts fresh ones. Call when the
    distro, shell mode or BBP environment changes."""
    global _total, _generation, _config_enabled
    with _lock:
        _generation += 1
        _config_enabled = None
        while _idle:
            _idle.pop().close()
            _total -= 1


atexit.register(reset)