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


def check_bbp_status():
    """
    Checks BBP status inside WSL. Replaces the original shutil.which()
    and os.environ approach which only checked the Windows environment.
    Returns a dict with connected (bool), version (str), and details (str).
    """
    return WSLBridge.check_bbp_environment()