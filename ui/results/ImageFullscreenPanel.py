# ImageFullscreenPanel.py — ui/Results/ImageFullscreenPanel.py
# -------------------------------------------------------
# Fullscreen image viewer with zoom in/out/reset, pan
# and download. Opens when any image in the Results
# Viewer is clicked. Accepts either a WSL file path OR
# a pre-loaded PIL Image directly.
# -------------------------------------------------------

import customtkinter as ctk
import tkinter as tk
import os
import sys
import io
import base64
from tkinter import filedialog

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


class ImageFullscreenPanel(ctk.CTkToplevel):
    """
    Fullscreen image viewer with zoom in/out/reset and download.
    Opens when the user clicks any image in the Results Viewer.
    Accepts either:
      - wsl_path: loads image from WSL via base64
      - pil_image: uses a pre-loaded PIL Image directly
        (used for matplotlib-generated plots)
    """

    ZOOM_STEP = 0.15
    ZOOM_MIN  = 0.1
    ZOOM_MAX  = 5.0

    def __init__(self, master, wsl_path=None, title="Image Viewer",
                 pil_image=None):
        super().__init__(master)

        self._wsl_path   = wsl_path or ""
        self._pil_image  = pil_image
        self._zoom_level = 1.0
        self._base_w     = 1
        self._base_h     = 1

        display_title = (
            os.path.basename(wsl_path) if wsl_path
            else title
        )

        self.title(display_title)
        self.configure(fg_color="#0d0d0d")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui(display_title)
        self.after(150, self._on_ready)

    def _on_ready(self):
        try:
            self.state("zoomed")
            self.lift()
            self.focus_force()
            self.update_idletasks()
        except Exception:
            pass

    def _build_ui(self, display_title="Image Viewer"):

        # --- TOP BAR ---
        bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0, height=50)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text=display_title,
            font=(res.FONT_LABEL[0], 12),
            text_color="gray"
        ).pack(side="left", padx=15, pady=12)

        ctk.CTkButton(
            bar, text="Close", width=90, height=32,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=10, pady=9)

        self.btn_download = ctk.CTkButton(
            bar, text="Download Image", width=140, height=32,
            fg_color=res.COLOR_PRIMARY, hover_color="#004070",
            state="disabled",
            command=self._download_image
        )
        self.btn_download.pack(side="right", padx=(0, 8), pady=9)

        self.lbl_download_status = ctk.CTkLabel(
            bar, text="", font=(res.FONT_LABEL[0], 11),
            text_color=res.COLOR_SUCCESS
        )
        self.lbl_download_status.pack(side="right", padx=10)

        # --- ZOOM CONTROLS BAR ---
        zoom_bar = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0, height=40)
        zoom_bar.pack(fill="x")
        zoom_bar.pack_propagate(False)

        ctk.CTkButton(
            zoom_bar, text="Zoom In  +", width=100, height=28,
            fg_color="#2a2a2a", hover_color="#3a3a3a",
            font=(res.FONT_LABEL[0], 11),
            command=self._zoom_in
        ).pack(side="left", padx=(15, 4), pady=6)

        ctk.CTkButton(
            zoom_bar, text="Zoom Out  -", width=100, height=28,
            fg_color="#2a2a2a", hover_color="#3a3a3a",
            font=(res.FONT_LABEL[0], 11),
            command=self._zoom_out
        ).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(
            zoom_bar, text="Reset", width=70, height=28,
            fg_color="#2a2a2a", hover_color="#3a3a3a",
            font=(res.FONT_LABEL[0], 11),
            command=self._zoom_reset
        ).pack(side="left", padx=4, pady=6)

        self.lbl_zoom = ctk.CTkLabel(
            zoom_bar, text="Zoom: 100%",
            font=(res.FONT_LABEL[0], 11), text_color="gray"
        )
        self.lbl_zoom.pack(side="left", padx=12)

        ctk.CTkLabel(
            zoom_bar,
            text="Scroll wheel to zoom  |  Click and drag to pan",
            font=(res.FONT_LABEL[0], 10), text_color="#444444"
        ).pack(side="right", padx=15)

        # --- SCROLLABLE CANVAS AREA ---
        canvas_frame = ctk.CTkFrame(self, fg_color="#0d0d0d")
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            canvas_frame, bg="#0d0d0d",
            highlightthickness=0,
            cursor="fleur"
        )
        self._scrollbar_x = tk.Scrollbar(
            canvas_frame, orient="horizontal",
            command=self._canvas.xview
        )
        self._scrollbar_y = tk.Scrollbar(
            canvas_frame, orient="vertical",
            command=self._canvas.yview
        )
        self._canvas.configure(
            xscrollcommand=self._scrollbar_x.set,
            yscrollcommand=self._scrollbar_y.set
        )

        self._scrollbar_x.pack(side="bottom", fill="x")
        self._scrollbar_y.pack(side="right",  fill="y")
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<MouseWheel>",    self._on_mousewheel)
        self._canvas.bind("<Button-4>",      self._on_mousewheel)
        self._canvas.bind("<Button-5>",      self._on_mousewheel)
        self._canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self._canvas.bind("<B1-Motion>",     self._on_pan_move)
        self.bind("<Configure>", lambda e: self.after(50, self._render_image) if self._pil_image else None)

        self._canvas_image_id = None

        self.img_label = ctk.CTkLabel(
            self._canvas,
            text="Loading image...",
            font=(res.FONT_LABEL[0], 13),
            text_color="gray"
        )
        self._canvas.create_window(0, 0, anchor="nw", window=self.img_label)

        self.after(300, self._load_image)

    # ------------------------------------------------------------------
    # IMAGE LOADING
    # ------------------------------------------------------------------

    def _load_image(self):
        if not PIL_AVAILABLE:
            self.img_label.configure(
                text="Pillow not installed. Run: pip install Pillow"
            )
            return

        try:
            if self._pil_image is not None:
                sw = self.winfo_screenwidth()  - 60
                sh = self.winfo_screenheight() - 160
                w, h = self._pil_image.size
                scale = min(sw / w, sh / h, 1.0)
                self._base_w = max(1, int(w * scale))
                self._base_h = max(1, int(h * scale))
                self._canvas.delete("all")
                self._zoom_level = 1.0
                self.after(100, self._render_image)
                self.btn_download.configure(state="normal")
                return

            result = WSLBridge.run_command(f"base64 '{self._wsl_path}' 2>/dev/null")
            if result.returncode != 0 or not result.stdout.strip():
                self.img_label.configure(
                    text=f"Image not found:\n{self._wsl_path}",
                    text_color=res.COLOR_ERROR
                )
                return

            img_bytes       = base64.b64decode(result.stdout.strip())
            self._pil_image = Image.open(io.BytesIO(img_bytes))

            sw = self.winfo_screenwidth()  - 60
            sh = self.winfo_screenheight() - 160
            w, h = self._pil_image.size
            scale = min(sw / w, sh / h, 1.0)
            self._base_w = max(1, int(w * scale))
            self._base_h = max(1, int(h * scale))

            self._canvas.delete("all")
            self._zoom_level = 1.0
            self.after(100, self._render_image)
            self.btn_download.configure(state="normal")

        except Exception as e:
            self.img_label.configure(
                text=f"Error loading image:\n{e}",
                text_color=res.COLOR_ERROR
            )

    def _render_image(self):
        if self._pil_image is None:
            return

        from PIL import ImageTk

        disp_w = max(1, int(self._base_w * self._zoom_level))
        disp_h = max(1, int(self._base_h * self._zoom_level))

        resized      = self._pil_image.resize((disp_w, disp_h), Image.LANCZOS)
        self._tk_photo = ImageTk.PhotoImage(resized)

        self._canvas.delete("all")
        self._canvas.update_idletasks()
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()

        cx = max(disp_w // 2, cw // 2)
        cy = max(disp_h // 2, ch // 2)

        self._canvas_image_id = self._canvas.create_image(
            cx, cy, anchor="center", image=self._tk_photo
        )

        scroll_w = max(disp_w, cw)
        scroll_h = max(disp_h, ch)
        self._canvas.configure(scrollregion=(0, 0, scroll_w, scroll_h))
        self.lbl_zoom.configure(text=f"Zoom: {int(self._zoom_level * 100)}%")

    # ------------------------------------------------------------------
    # ZOOM
    # ------------------------------------------------------------------

    def _zoom_in(self):
        self._zoom_level = min(self.ZOOM_MAX, self._zoom_level + self.ZOOM_STEP)
        self._render_image()

    def _zoom_out(self):
        self._zoom_level = max(self.ZOOM_MIN, self._zoom_level - self.ZOOM_STEP)
        self._render_image()

    def _zoom_reset(self):
        self._zoom_level = 1.0
        self._render_image()

    def _on_mousewheel(self, event):
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self._zoom_in()
        else:
            self._zoom_out()

    # ------------------------------------------------------------------
    # PAN
    # ------------------------------------------------------------------

    def _on_pan_start(self, event):
        self._canvas.scan_mark(event.x, event.y)

    def _on_pan_move(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)

    # ------------------------------------------------------------------
    # DOWNLOAD
    # ------------------------------------------------------------------

    def _download_image(self):
        if self._pil_image is None:
            return

        filename = os.path.basename(self._wsl_path) if self._wsl_path else "image.png"
        ext      = os.path.splitext(filename)[1].lower() or ".png"
        ftypes   = [("PNG Image", "*.png"), ("All Files", "*.*")]
        if ext in (".jpg", ".jpeg"):
            ftypes = [("JPEG Image", "*.jpg"), ("All Files", "*.*")]

        save_path = filedialog.asksaveasfilename(
            parent=self, title="Save Image As",
            initialfile=filename,
            defaultextension=ext,
            filetypes=ftypes
        )

        if not save_path:
            return

        try:
            self._pil_image.save(save_path)
            self.lbl_download_status.configure(
                text=f"Saved: {os.path.basename(save_path)}",
                text_color=res.COLOR_SUCCESS
            )
        except Exception as e:
            self.lbl_download_status.configure(
                text=f"Save failed: {e}",
                text_color=res.COLOR_ERROR
            )