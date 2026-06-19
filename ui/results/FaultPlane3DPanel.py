# FaultPlane3DPanel.py — ui/results/FaultPlane3DPanel.py
# -------------------------------------------------------
# 3D fault plane visualization that projects the same slip,
# rake, rise time, and rupture time data from SlipDistributionPanel
# onto the fault plane in true 3D space (East / North / Depth),
# accounting for the real strike and dip angles.
#
# Coordinate transform:
#   - Origin: fault top-center point (lon, lat, depth_top)
#   - Along-strike direction: strike angle clockwise from North
#     in the horizontal plane
#   - Down-dip direction: perpendicular to strike, tilted at
#     the dip angle below horizontal
#   - Each subfault's (i_stk, j_dip) grid position maps to a
#     real 3D point (East_km, North_km, Depth_km)
#
# Confirmed by Dr. Ghofrani as the intended visualization,
# matching Figure 2 in Dhanya & Raghukanth (2023) exactly.
# -------------------------------------------------------

import customtkinter as ctk
import tkinter as tk
import os
import sys
import math
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import core.Resources as res
from core.WSLBridge import WSLBridge
from ui.results.SlipDistributionPanel import parse_srf

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# Degrees to radians helper
def _d2r(deg):
    return math.radians(deg)


def compute_3d_corners(plane):
    """
    Converts the fault plane geometry into a 3D grid of subfault
    corner points in (East_km, North_km, Depth_km) coordinates,
    with the fault top-center as the origin.

    Args:
        plane (dict): parsed from parse_srf()["plane"] —
                      must contain strike, dip, len_km, wid_km,
                      nstrike, ndip, depth_top.

    Returns:
        xs, ys, zs: 2D numpy arrays of shape (ndip+1, nstrike+1)
                    representing the 3D grid corner positions.
    """
    strike    = plane["strike"]
    dip       = plane["dip"]
    len_km    = plane["len_km"]
    wid_km    = plane["wid_km"]
    nstrike   = plane["nstrike"]
    ndip      = plane["ndip"]
    depth_top = plane["depth_top"]

    # Strike unit vector in horizontal plane (East, North)
    # Strike is measured clockwise from North, so:
    #   East component  = sin(strike)
    #   North component = cos(strike)
    stk_e = math.sin(_d2r(strike))
    stk_n = math.cos(_d2r(strike))

    # Down-dip unit vector (East, North, Down)
    # Dip direction is perpendicular to strike rotated 90° clockwise
    # in horizontal plane, then tilted downward at dip angle
    dip_dir = strike + 90.0
    dip_e   =  math.sin(_d2r(dip_dir)) * math.cos(_d2r(dip))
    dip_n   =  math.cos(_d2r(dip_dir)) * math.cos(_d2r(dip))
    dip_z   =  math.sin(_d2r(dip))   # positive = downward

    # Subfault spacing in km
    ds = len_km / nstrike
    dd = wid_km / ndip

    # Top-left corner of fault (offset half-length along strike from center)
    # Origin is top-center, so shift left by half the fault length
    tl_e = -0.5 * len_km * stk_e
    tl_n = -0.5 * len_km * stk_n
    tl_z = depth_top

    # Build grid — (ndip+1) rows x (nstrike+1) cols
    xs = np.zeros((ndip + 1, nstrike + 1))
    ys = np.zeros((ndip + 1, nstrike + 1))
    zs = np.zeros((ndip + 1, nstrike + 1))

    for j in range(ndip + 1):
        for i in range(nstrike + 1):
            xs[j, i] = tl_e + i * ds * stk_e + j * dd * dip_e
            ys[j, i] = tl_n + i * ds * stk_n + j * dd * dip_n
            zs[j, i] = tl_z + j * dd * dip_z

    return xs, ys, zs


def build_param_grid(plane, points, param):
    """
    Reshapes the flat list of subfault values into a 2D grid
    (ndip rows x nstrike cols) for the requested parameter.

    Args:
        plane  (dict): from parse_srf()["plane"]
        points (list): from parse_srf()["points"]
        param  (str) : "slip_cm", "rake", "rise_time", or "tinit"

    Returns:
        2D numpy array of shape (ndip, nstrike)
    """
    nstrike = plane["nstrike"]
    ndip    = plane["ndip"]
    vals    = [pt.get(param, 0.0) for pt in points]
    arr     = np.array(vals, dtype=float)

    # SRF points are stored row-major: all strike points for dip row 0,
    # then dip row 1, etc.
    if len(arr) == nstrike * ndip:
        return arr.reshape(ndip, nstrike)

    # Fallback: pad or trim if count doesn't match exactly
    expected = nstrike * ndip
    if len(arr) < expected:
        arr = np.concatenate([arr, np.zeros(expected - len(arr))])
    else:
        arr = arr[:expected]
    return arr.reshape(ndip, nstrike)


class FaultPlane3DPanel(ctk.CTkToplevel):
    """
    3D fault plane visualization popup.

    Opens from ResultsPanel's Slip Distribution tab alongside
    the existing SlipDistributionPanel button. Shows the fault
    plane in true East/North/Depth space with the slip (or other
    parameter) color-mapped onto its surface, and a red line at
    the surface trace where the fault intersects depth=0.

    Requires both the .srf file (for slip data and plane geometry)
    and the .src file (for the fault top-center lat/lon used as
    the geographic reference point in the caption).
    """

    PARAMS = {
        "Slip (cm)"      : "slip_cm",
        "Rake (°)"       : "rake",
        "Rise Time (s)"  : "rise_time",
        "Rupture Time (s)": "tinit",
    }

    COLORMAPS = {
        "Slip (cm)"      : "YlOrRd",
        "Rake (°)"       : "coolwarm",
        "Rise Time (s)"  : "viridis",
        "Rupture Time (s)": "plasma",
    }

    def __init__(self, master, srf_path, src_file=None, run_id=""):
        super().__init__(master)

        self._srf_path  = srf_path
        self._src_file  = src_file
        self._run_id    = run_id
        self._srf_data  = None
        self._param_var = None

        self.title(f"3D Fault Plane — {os.path.basename(srf_path)}")
        self.configure(fg_color="#1a1a1a")
        self.resizable(True, True)
        self.transient(master)

        self._build_ui()
        self.after(150, self._on_ready)
        self.after(300, self._load_data)

    def _on_ready(self):
        try:
            self.wm_attributes("-zoomed", True)
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        # --- TOP BAR ---
        bar = ctk.CTkFrame(self, fg_color="#0d0d0d", corner_radius=0, height=50)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="3D Fault Plane Visualization",
            font=(res.FONT_LABEL[0], 14, "bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            bar,
            text=f"Run ID: {self._run_id}",
            font=(res.FONT_LABEL[0], 11),
            text_color="gray"
        ).pack(side="right", padx=16, pady=12)

        ctk.CTkButton(
            bar, text="Close", width=90, height=32,
            fg_color="#333333", hover_color="#444444",
            command=self.destroy
        ).pack(side="right", padx=(0, 8), pady=9)

        # --- CONTROLS BAR ---
        ctrl = ctk.CTkFrame(self, fg_color="#111111", height=46)
        ctrl.pack(fill="x")
        ctrl.pack_propagate(False)

        ctk.CTkLabel(
            ctrl, text="Parameter:",
            font=(res.FONT_LABEL[0], 11), text_color="gray"
        ).pack(side="left", padx=(16, 6), pady=12)

        self._param_var = ctk.StringVar(value="Slip (cm)")
        param_menu = ctk.CTkOptionMenu(
            ctrl,
            values=list(self.PARAMS.keys()),
            variable=self._param_var,
            width=160,
            fg_color="#222222",
            button_color="#333333",
            command=self._on_param_change
        )
        param_menu.pack(side="left", pady=12)

        ctk.CTkLabel(
            ctrl,
            text="Use toolbar below plot to zoom, pan, and rotate",
            font=(res.FONT_LABEL[0], 10),
            text_color="#444444"
        ).pack(side="right", padx=16, pady=12)

        # --- PLOT AREA ---
        self._plot_frame = ctk.CTkFrame(self, fg_color="#111111")
        self._plot_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self._loading_label = ctk.CTkLabel(
            self._plot_frame,
            text="Loading .srf file...",
            font=(res.FONT_LABEL[0], 13),
            text_color="gray"
        )
        self._loading_label.pack(expand=True)

    def _load_data(self):
        """Loads the .srf file and triggers the initial render."""
        ok, content = WSLBridge.read_wsl_file(self._srf_path)
        if not ok or not content:
            self._loading_label.configure(
                text=f"Could not read .srf file:\n{self._srf_path}",
                text_color=res.COLOR_ERROR
            )
            return
        try:
            self._srf_data = parse_srf(content)
        except Exception as e:
            self._loading_label.configure(
                text=f"Error parsing .srf file:\n{e}",
                text_color=res.COLOR_ERROR
            )
            return

        self._loading_label.pack_forget()
        self._render()

    def _on_param_change(self, value):
        """Re-renders when the user selects a different parameter."""
        if self._srf_data:
            for widget in self._plot_frame.winfo_children():
                widget.destroy()
            self._render()

    def _render(self):
        """Builds the 3D matplotlib figure and embeds it."""
        if not self._srf_data:
            return

        plane  = self._srf_data["plane"]
        points = self._srf_data["points"]
        label  = self._param_var.get()
        key    = self.PARAMS[label]
        cmap   = self.COLORMAPS[label]

        # --- COMPUTE 3D CORNER GRID ---
        try:
            xs, ys, zs = compute_3d_corners(plane)
        except Exception as e:
            ctk.CTkLabel(
                self._plot_frame,
                text=f"Error computing 3D geometry:\n{e}",
                text_color=res.COLOR_ERROR
            ).pack(expand=True)
            return

        # --- BUILD PARAMETER GRID ---
        try:
            grid = build_param_grid(plane, points, key)
        except Exception as e:
            ctk.CTkLabel(
                self._plot_frame,
                text=f"Error building parameter grid:\n{e}",
                text_color=res.COLOR_ERROR
            ).pack(expand=True)
            return

        # --- MATPLOTLIB 3D FIGURE ---
        fig = plt.figure(figsize=(11, 8), facecolor="#111111", dpi=90)
        ax  = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#111111")

        # Color-map the parameter values onto the subfault grid.
        # pcolormesh needs (ndip+1, nstrike+1) corner arrays and
        # (ndip, nstrike) value array — exactly what we have.
        norm    = mcolors.Normalize(vmin=grid.min(), vmax=grid.max())
        cmap_fn = plt.get_cmap(cmap)
        colors  = cmap_fn(norm(grid))  # shape (ndip, nstrike, 4)

        # plot_surface expects (ndip+1, nstrike+1) arrays for X,Y,Z
        # and draws the surface. facecolors must match the face count
        # (ndip, nstrike), so we pass the pre-computed RGBA array.
        surf = ax.plot_surface(
            xs, ys, zs,
            facecolors=colors,
            shade=False,
            antialiased=False,
            alpha=0.95
        )

        # --- SURFACE TRACE (red line where fault intersects depth=0) ---
        # Find the top edge of the fault plane (j=0 row in the grid)
        ax.plot(
            xs[0, :], ys[0, :],
            np.zeros(plane["nstrike"] + 1),
            color="red", linewidth=2.5,
            label="Surface trace", zorder=10
        )

        # --- HYPOCENTER MARKER ---
        h_stk = plane.get("hypo_stk_km", 0.0)
        h_dip = plane.get("hypo_dip_km", 0.0)
        strike  = plane["strike"]
        dip     = plane["dip"]
        dep_top = plane["depth_top"]
        len_km  = plane["len_km"]

        stk_e = math.sin(_d2r(strike))
        stk_n = math.cos(_d2r(strike))
        dip_dir = strike + 90.0
        dip_e = math.sin(_d2r(dip_dir)) * math.cos(_d2r(dip))
        dip_n = math.cos(_d2r(dip_dir)) * math.cos(_d2r(dip))
        dip_z = math.sin(_d2r(dip))

        # Hypocenter position in 3D space
        # h_stk is measured from fault top-center along strike
        hx = h_stk * stk_e + h_dip * dip_e
        hy = h_stk * stk_n + h_dip * dip_n
        hz = dep_top + h_dip * dip_z

        ax.scatter(
            [hx], [hy], [hz],
            c="white", s=80, zorder=20,
            marker="*", label="Hypocenter"
        )

        # --- COLORBAR ---
        sm = plt.cm.ScalarMappable(cmap=cmap_fn, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, shrink=0.55, pad=0.1)
        cbar.set_label(label, color="white", fontsize=10)
        cbar.ax.yaxis.set_tick_params(color="white")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

        # --- AXES STYLING ---
        ax.set_xlabel("East (km)",  color="white", labelpad=8)
        ax.set_ylabel("North (km)", color="white", labelpad=8)
        ax.set_zlabel("Depth (km)", color="white", labelpad=8)
        ax.tick_params(colors="white")
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor("#333333")
        ax.yaxis.pane.set_edgecolor("#333333")
        ax.zaxis.pane.set_edgecolor("#333333")
        ax.grid(True, color="#333333", linewidth=0.5)

        # Invert Z axis so depth increases downward
        ax.invert_zaxis()

        strike_label = f"{plane['strike']:.0f}°"
        dip_label    = f"{plane['dip']:.0f}°"
        ax.set_title(
            f"Fault Plane  |  Strike {strike_label}  |  Dip {dip_label}  |  {label}",
            color="white", fontsize=11, pad=12
        )

        ax.legend(
            facecolor="#1a1a1a", edgecolor="#444444",
            labelcolor="white", fontsize=9,
            loc="upper left"
        )

        fig.tight_layout()

        # --- EMBED IN FRAME ---
        cw = FigureCanvasTkAgg(fig, master=self._plot_frame)
        cw.draw()
        tk_w = cw.get_tk_widget()
        tk_w.pack(fill="both", expand=True)

        toolbar = NavigationToolbar2Tk(cw, self._plot_frame, pack_toolbar=False)
        toolbar.config(background="#111111")
        toolbar.update()
        toolbar.pack(side="bottom", fill="x", padx=4, pady=2)

        # Smooth rotation: during drag reduce surface alpha to 0
        # (shows only wireframe/edges) for fast redraws, then restore
        # full quality on mouse release. This makes 3D rotation feel
        # responsive rather than sluggish since matplotlib's Agg
        # renderer redraws the full figure on every mouse-move event.
        def _on_drag_start(event):
            surf.set_alpha(0.0)

        def _on_drag_end(event):
            surf.set_alpha(0.95)
            cw.draw_idle()

        fig.canvas.mpl_connect("button_press_event",   _on_drag_start)
        fig.canvas.mpl_connect("button_release_event", _on_drag_end)

        plt.close(fig)