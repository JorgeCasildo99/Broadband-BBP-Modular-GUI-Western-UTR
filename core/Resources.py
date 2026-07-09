import customtkinter as ctk
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

from core.WSLBridge import WSLBridge

# --- UI CONSTANTS ---
COLOR_PRIMARY = "#005088"
COLOR_SUCCESS = "#11caa0"
COLOR_ERROR   = "#ef4444"

FONT_TITLE = ("Merriweather", 24, "bold")
FONT_LABEL = ("DM Sans", 14)


def center_window(window, width, height):
    """Centers a window on screen and locks its size."""
    window.update_idletasks()
    screen_width  = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = int((screen_width  / 2) - (width  / 2))
    y = int((screen_height / 2) - (height / 2))
    window.geometry(f'{width}x{height}+{x}+{y}')
    window.resizable(False, False)


def center_on_screen(window, width=None, height=None):
    """
    Centers any CTk window or Toplevel exactly in the middle of the screen.

    If width and height are provided the window is also sized.
    If omitted the window is centered using its current requested size.

    Always call AFTER setting geometry but BEFORE mainloop / deiconify.

    Usage:
        center_on_screen(window, 1200, 800)   # size + center
        center_on_screen(window)               # center only
    """
    # First pass — let Tk compute internal layout
    window.update_idletasks()

    if width and height:
        window.geometry(f"{width}x{height}")
        # Second pass — apply the new size before reading dimensions
        window.update_idletasks()

    # Use winfo_reqwidth/height — they return the correct requested
    # dimensions even before the window is fully drawn on screen
    w = width  or window.winfo_reqwidth()
    h = height or window.winfo_reqheight()

    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()

    x = (screen_w - w) // 2
    y = (screen_h - h) // 2

    window.geometry(f"{w}x{h}+{x}+{y}")


def center_toplevel(toplevel, width=None, height=None, parent=None):
    """
    Centers a CTkToplevel popup exactly in the middle of its parent window,
    or exactly in the middle of the screen if no parent is given.

    Usage:
        center_toplevel(popup, 600, 400, parent=self)  # relative to parent
        center_toplevel(popup, 600, 400)               # center on screen
    """
    toplevel.update_idletasks()

    if width and height:
        toplevel.geometry(f"{width}x{height}")
        toplevel.update_idletasks()

    w = width  or toplevel.winfo_reqwidth()
    h = height or toplevel.winfo_reqheight()

    if parent:
        # Exact center of the parent window
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
    else:
        # Exact center of the screen
        screen_w = toplevel.winfo_screenwidth()
        screen_h = toplevel.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2

    # Clamp to screen bounds so popup never goes off-screen
    x = max(0, x)
    y = max(0, y)

    toplevel.geometry(f"{w}x{h}+{x}+{y}")


def check_bbp_status():
    """
    Checks BBP status inside WSL. Replaces the original shutil.which()
    and os.environ approach which only checked the Windows environment.
    Returns a dict with connected (bool), version (str), and details (str).
    """
    return WSLBridge.check_bbp_environment()