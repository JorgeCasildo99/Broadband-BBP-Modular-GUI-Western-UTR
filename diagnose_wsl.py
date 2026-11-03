"""
diagnose_wsl.py — shows what the GUI sees when it talks to WSL.

Run from the project root (the folder that contains main.py):
    python diagnose_wsl.py
Copy everything it prints when reporting a "BBP not detected" problem.
Changes nothing except reading files and running read-only shell commands.
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import WSLRuntime as RT
from core.WSLBridge import WSLBridge as WB


def section(title):
    print(f"\n=== {title} ===")


def raw(distro, flags, cmd):
    """Runs cmd in bash with explicit flags in one distro, bypassing the
    saved settings, so every shell mode can be compared side by side."""
    full = ["wsl.exe", "-d", distro, "--exec", "bash", flags, cmd] \
        if RT.IS_WINDOWS else ["bash", flags, cmd]
    try:
        r = subprocess.run(full, capture_output=True,
                           **RT.subprocess_kwargs())
    except Exception as e:
        return f"[could not run: {e}]"
    out = (r.stdout or "").strip()
    err = "\n".join(l for l in (r.stderr or "").strip().splitlines()
                    if not RT.is_shell_noise(l))
    text = out if out else "(empty)"
    if err:
        text += f"\n    stderr: {err}"
    return text


def indent(text):
    return "\n".join("    " + line for line in text.splitlines())


def main():
    print("BBP-GUI WSL diagnostic")
    print(f"Python: {sys.version.split()[0]} on {sys.platform}")

    section("1. WSL distributions")
    distros = RT.list_distros()
    if not distros:
        print("    none found (normal on native Linux)")
    for d in distros:
        mark = "*" if d["default"] else " "
        print(f"    {mark} {d['name']:<22} {d['state']:<10} WSL{d['version']}")

    chosen = RT.initialize()
    print(f"    GUI would use: {chosen}")
    print(f"    config file:   {RT.config_path()}")
    cfg = RT.load_config()
    print(f"    saved config:  {cfg}")

    targets = [d["name"] for d in distros
               if not d["name"].lower().startswith("docker-desktop")] \
        or [chosen or "(native)"]

    for distro in targets:
        section(f"2. Who and where, in distro '{distro}'")
        print(indent(raw(distro, "-c",
                         "echo user=$(whoami); echo HOME=$HOME; echo SHELL=$SHELL")))

        section(f"3. BBP-looking folders in the home of '{distro}'")
        print(indent(raw(distro, "-c",
                         "ls -d ~/bbp* ~/*bbp* 2>/dev/null; echo ---; ls ~ | head -40")))

        section(f"4. Where BBP is configured in '{distro}'")
        print(indent(raw(distro, "-c",
                         "grep -n -i 'bbp' ~/.bashrc ~/.profile ~/.bash_profile "
                         "~/bbp_env/bin/activate 2>/dev/null | head -40")))

        section(f"5. BBP variables under each shell mode in '{distro}'")
        probe = ("echo BBP_DIR=$BBP_DIR; echo BBP_DATA_DIR=$BBP_DATA_DIR; "
                 "echo run_bbp=$(command -v run_bbp.py)")
        src_probe = ("source ~/bbp_env/bin/activate 2>/dev/null; " + probe)
        for flags, label in (("-c", "plain      (what the GUI tries first)"),
                             ("-ic", "interactive (the automatic fallback)"),
                             ("-lc", "login       (reads ~/.profile)")):
            print(f"  {flags}  {label}")
            print(indent(raw(distro, flags, probe)))
            print(f"  {flags}  ...after sourcing ~/bbp_env/bin/activate")
            print(indent(raw(distro, flags, src_probe)))

    if RT.IS_WINDOWS and chosen:
        section("5b. Does wsl.exe's outer shell swallow $VARIABLES?")
        test = "echo BBP_DIR=$BBP_DIR"
        old_form = subprocess.run(
            ["wsl.exe", "-d", chosen, "bash", "-ic", test],
            capture_output=True, **RT.subprocess_kwargs())
        new_form = subprocess.run(
            ["wsl.exe", "-d", chosen, "--exec", "bash", "-ic", test],
            capture_output=True, **RT.subprocess_kwargs())
        print(f"    without --exec: {(old_form.stdout or '').strip()}")
        print(f"    with    --exec: {(new_form.stdout or '').strip()}")

    section("6. What auto-detection finds (distro the GUI would use)")
    for flags in ("-c", "-ic"):
        RT.set_shell_flags(flags)
        found = RT.detect_bbp_activate(WB.run_command)
        print(f"    flags {flags}: {found}")
    RT.set_shell_flags("-c")

    section("7. The GUI's own BBP check")
    status = WB.check_bbp_environment()
    print(f"    connected: {status['connected']}")
    print(f"    version:   {status['version']}")
    print(f"    details:   {status['details']}")
    print(f"    shell flags now: {RT.get_shell_flags()}")
    print(f"    env path now:    {WB.BBP_ENV_PATH or WB._get_bbp_env_path()}")
    section("8. Speed: milliseconds per WSL call (5 runs each)")
    if RT.IS_WINDOWS and chosen:
        def timed(argv, runs=5):
            samples = []
            for _ in range(runs):
                t0 = time.perf_counter()
                subprocess.run(argv, capture_output=True, **RT.subprocess_kwargs())
                samples.append((time.perf_counter() - t0) * 1000)
            return sum(samples) / len(samples), min(samples), max(samples)

        base = ["wsl.exe", "-d", chosen, "--exec", "bash"]
        modes = [
            ("plain  bash -c                 ", base + ["-c", "echo ok"]),
            ("interactive  bash -ic (reloads ~/.bashrc every call)",
             base + ["-ic", "echo ok"]),
        ]
        t0 = time.perf_counter()
        preamble = RT.capture_env_preamble(chosen)
        capture_ms = (time.perf_counter() - t0) * 1000
        if preamble:
            modes.append(("plain + captured environment (what the GUI now uses)",
                          base + ["-c", preamble + "echo ok"]))
        for label, argv in modes:
            avg, lo, hi = timed(argv)
            print(f"    {label:<56} avg {avg:6.0f}   min {lo:6.0f}   max {hi:6.0f}")
        from core import WSLShell
        WSLShell.reset()
        t0 = time.perf_counter()
        first = WSLShell.run("echo ok")
        start_ms = (time.perf_counter() - t0) * 1000
        if first is None:
            print("    persistent shell: NOT AVAILABLE (GUI falls back to the "
                  "slower per-call mode)")
        else:
            samples = []
            for _ in range(10):
                t0 = time.perf_counter()
                WSLShell.run("echo ok")
                samples.append((time.perf_counter() - t0) * 1000)
            avg = sum(samples) / len(samples)
            print(f"    persistent shell (what the GUI now uses)                 "
                  f"avg {avg:6.1f}   min {min(samples):6.1f}   max {max(samples):6.1f}"
                  f"   (first call/startup {start_ms:.0f} ms)")
        print(f"    one-time environment capture: {capture_ms:.0f} ms, "
              f"{len(preamble)} characters, "
              f"{'OK' if preamble else 'FAILED (GUI will use slow interactive mode)'}")
    else:
        print("    (Windows only)")

    section("9. Display scale (why the window may look bigger)")
    try:
        import customtkinter as ctk
        root = ctk.CTk()
        dpi = ctk.ScalingTracker.get_window_dpi_scaling(root)
        root.destroy()
        factor = RT.ui_scale(dpi)
        print(f"    Windows display scale: {dpi:.2f}  ({dpi * 100:.0f}%)")
        print(f"    GUI compensation factor: {factor:.2f}   "
              f"(set \"ui_scale\" in {RT.config_path()} to resize)")
    except Exception as e:
        print(f"    could not read display scale: {e}")

    print(f"\nLog file (if the .exe is ever used): {RT.log_path()}")


if __name__ == "__main__":
    main()