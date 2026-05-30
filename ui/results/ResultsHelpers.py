# ResultsHelpers.py — ui/Results/ResultsHelpers.py
# -------------------------------------------------------
# Shared helper functions used by ResultsPanel,
# StationDetailPanel and ImageFullscreenPanel.
# Kept separate so all Results sub-panels can import
# them without circular dependencies.
# -------------------------------------------------------

import customtkinter as ctk
import os
import sys
import io
import base64

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _load_wsl_image(wsl_path, max_w=900, max_h=650):
    """
    Reads an image from WSL via base64 and returns a (CTkImage, PIL.Image) tuple.
    Returns (None, None) if the file cannot be loaded or PIL is unavailable.
    """
    if not PIL_AVAILABLE:
        return None, None
    try:
        result = WSLBridge.run_command(f"base64 '{wsl_path}' 2>/dev/null")
        if result.returncode != 0 or not result.stdout.strip():
            return None, None
        img_bytes = base64.b64decode(result.stdout.strip())
        pil_img   = Image.open(io.BytesIO(img_bytes))
        w, h      = pil_img.size
        scale     = min(max_w / w, max_h / h, 1.0)
        size      = (int(w * scale), int(h * scale))
        ctk_img   = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        return ctk_img, pil_img
    except Exception as e:
        print(f"[Image] {wsl_path}: {e}")
        return None, None


def _image_tab(parent, wsl_path, fallback_msg="Image not found.", master=None):
    """
    Fills a frame with a clickable image loaded from WSL.
    Clicking opens ImageFullscreenPanel.
    Shows a fallback message if the image cannot be loaded.
    """
    # Import here to avoid circular dependency
    from ui.results.ImageFullscreenPanel import ImageFullscreenPanel

    ctk_img, _ = _load_wsl_image(wsl_path)
    if ctk_img:
        lbl = ctk.CTkLabel(parent, image=ctk_img, text="", cursor="hand2")
        lbl.image = ctk_img
        lbl.pack(expand=True, pady=4)

        ctk.CTkLabel(
            parent,
            text="Click image to view fullscreen / download",
            font=(res.FONT_LABEL[0], 10),
            text_color="#555555"
        ).pack(pady=(0, 4))

        def _open_fullscreen(event, path=wsl_path, m=master):
            win = m if m else parent.winfo_toplevel()
            ImageFullscreenPanel(win, path, title=os.path.basename(path))

        lbl.bind("<Button-1>", _open_fullscreen)
    else:
        ctk.CTkLabel(
            parent,
            text=f"{fallback_msg}\n{wsl_path}",
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        ).pack(expand=True)


def _section_label(parent, text):
    """Styled section divider label."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=(10, 4))
    ctk.CTkLabel(
        frame, text=text,
        font=(res.FONT_LABEL[0], 13, "bold"),
        text_color=res.COLOR_PRIMARY
    ).pack(side="left")
    sep = ctk.CTkFrame(frame, fg_color="#333333", height=1)
    sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)


def _textbox(parent, content, height=160, color="#00ff88"):
    """Readonly monospace textbox."""
    box = ctk.CTkTextbox(
        parent,
        fg_color="#0d0d0d",
        text_color=color,
        font=("Courier", 10),
        height=height,
        border_width=1,
        border_color="#333333"
    )
    box.pack(fill="x", pady=(0, 8))
    box.insert("1.0", content or "File not found.")
    box.configure(state="disabled")
    return box


def _parse_status_file(content):
    """
    Parses the BBP software_status file to extract key metadata.
    Returns a dict with start_time, end_time, velocity_model, seed.
    """
    data = {
        "start_time"     : "N/A",
        "end_time"       : "N/A",
        "velocity_model" : "N/A",
        "seed"           : "N/A",
        "bbp_version"    : "N/A",
        "method"         : "N/A",
    }
    if not content:
        return data

    for line in content.splitlines():
        line = line.strip()
        low  = line.lower()
        if "start" in low and "time" in low:
            data["start_time"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif "end" in low and "time" in low:
            data["end_time"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif "velocity" in low or "labasin" in low.replace(" ", ""):
            data["velocity_model"] = line
        elif "seed" in low:
            parts = line.split()
            for i, p in enumerate(parts):
                if "seed" in p.lower() and i + 1 < len(parts):
                    data["seed"] = parts[i + 1]
        elif "version" in low and "22." in line:
            data["bbp_version"] = line.split(":")[-1].strip() if ":" in line else line
        elif "method" in low or " gp" in low:
            data["method"] = line.split(":")[-1].strip() if ":" in line else line

    return data