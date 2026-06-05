# ValidationEvents.py — core/ValidationEvents.py
# -------------------------------------------------------
# Registry of all known BBP v22.4.0 validation events.
# Folder names and file paths verified against actual
# BBP installation on the target machine.
# Source: https://github.com/SCECcode/bbp
# -------------------------------------------------------

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.WSLBridge import WSLBridge


# ------------------------------------------------------------------
# COMPLETE EVENT CATALOG — BBP v22.4.0
# bbp_number: the number BBP shows when asking "? [event number]"
# bbp_folder:  exact folder name inside ~/bbp_val/
# src_file:    path relative to bbp_folder/
# stl_file:    path relative to bbp_folder/
# ------------------------------------------------------------------

VALIDATION_EVENTS = [
    # ── REAL HISTORICAL EVENTS ──────────────────────────────────────
    {
        "bbp_number"    : 1,
        "name"          : "Chino Hills",
        "short_name"    : "ChinoHills",
        "bbp_folder"    : "ChinoHills",
        "magnitude"     : "Mw 5.39",
        "date"          : "July 29, 2008",
        "region"        : "Southern California — LA Basin",
        "depth_km"      : 14.7,
        "stations"      : 40,
        "required_model": "LABasin500",
        "src_file"      : "common/ch_v14_2_2.src",
        "stl_file"      : "common/ch_v19_06_2.stl",
        "description"   : (
            "The 2008 Chino Hills earthquake was widely felt across "
            "Southern California. One of the key validation events for "
            "the LA Basin region with well-constrained source model and "
            "dense strong-motion recordings."
        ),
    },
    {
        "bbp_number"    : 18,
        "name"          : "Northridge 1994",
        "short_name"    : "NR",
        "bbp_folder"    : "NR",
        "magnitude"     : "Mw 6.69",
        "date"          : "January 17, 1994",
        "region"        : "Southern California — LA Basin",
        "depth_km"      : 19.0,
        "stations"      : 40,
        "required_model": "LABasin500",
        "src_file"      : "gp/nr_v20_07_1.src",
        "stl_file"      : "common/nr_v19_06_2.stl",
        "description"   : (
            "The 1994 Northridge earthquake caused widespread damage "
            "across the Los Angeles area. One of the most important "
            "validation events for the LA Basin velocity model."
        ),
    },
    {
        "bbp_number"    : 19,
        "name"          : "Whittier Narrows 1987",
        "short_name"    : "Whittier",
        "bbp_folder"    : "Whittier",
        "magnitude"     : "Mw 5.99",
        "date"          : "October 1, 1987",
        "region"        : "Southern California — LA Basin",
        "depth_km"      : 14.6,
        "stations"      : 30,
        "required_model": "LABasin500",
        "src_file"      : "common/whittier_v12_11_0_fs.src",
        "stl_file"      : "common/whittier_v19_06_2.stl",
        "description"   : (
            "The 1987 Whittier Narrows earthquake caused significant "
            "damage in the Los Angeles area. Used as a validation event "
            "for the LA Basin velocity model."
        ),
    },

    # ── GMPE SoCal EVENTS (require LABasin500) ───────────────────────
    {
        "bbp_number"    : 4,
        "name"          : "GMPE 5.5rv SoCal 20km",
        "short_name"    : "GMPE55RV-20-SOCAL",
        "bbp_folder"    : "GMPE55RV-20-SOCAL",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m5_5_rv_socal.src",
        "stl_file"      : "common/m5_5_rv_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 5,
        "name"          : "GMPE 5.5rv SoCal 50km",
        "short_name"    : "GMPE55RV-50-SOCAL",
        "bbp_folder"    : "GMPE55RV-50-SOCAL",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m5_5_rv_socal.src",
        "stl_file"      : "common/m5_5_rv_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 50 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 8,
        "name"          : "GMPE 6.2ss SoCal 20km",
        "short_name"    : "GMPE62SS-20-SOCAL",
        "bbp_folder"    : "GMPE62SS-20-SOCAL",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m6_2_ss_socal.src",
        "stl_file"      : "common/m6_2_ss_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 9,
        "name"          : "GMPE 6.2ss SoCal 50km",
        "short_name"    : "GMPE62SS-50-SOCAL",
        "bbp_folder"    : "GMPE62SS-50-SOCAL",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m6_2_ss_socal.src",
        "stl_file"      : "common/m6_2_ss_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 50 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 12,
        "name"          : "GMPE 6.6rv SoCal 20km",
        "short_name"    : "GMPE66RV-20-SOCAL",
        "bbp_folder"    : "GMPE66RV-20-SOCAL",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m6_6_rv_socal.src",
        "stl_file"      : "common/m6_6_rv_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 13,
        "name"          : "GMPE 6.6rv SoCal 50km",
        "short_name"    : "GMPE66RV-50-SOCAL",
        "bbp_folder"    : "GMPE66RV-50-SOCAL",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m6_6_rv_socal.src",
        "stl_file"      : "common/m6_6_rv_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 50 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 16,
        "name"          : "GMPE 6.6ss SoCal 20km",
        "short_name"    : "GMPE66SS-20-SOCAL",
        "bbp_folder"    : "GMPE66SS-20-SOCAL",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m6_6_ss_socal.src",
        "stl_file"      : "common/m6_6_ss_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 17,
        "name"          : "GMPE 6.6ss SoCal 50km",
        "short_name"    : "GMPE66SS-50-SOCAL",
        "bbp_folder"    : "GMPE66SS-50-SOCAL",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/m6_6_ss_socal.src",
        "stl_file"      : "common/m6_6_ss_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 50 km distance in Southern California."
        ),
    },

    # ── GMPE NoCal EVENTS (require NOCAL500) ─────────────────────────
    {
        "bbp_number"    : 2,
        "name"          : "GMPE 5.5rv NoCal 20km",
        "short_name"    : "GMPE55RV-20-NOCAL",
        "bbp_folder"    : "GMPE55RV-20-NOCAL",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m5_5_rv_nocal.src",
        "stl_file"      : "common/m5_5_rv_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 3,
        "name"          : "GMPE 5.5rv NoCal 50km",
        "short_name"    : "GMPE55RV-50-NOCAL",
        "bbp_folder"    : "GMPE55RV-50-NOCAL",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m5_5_rv_nocal.src",
        "stl_file"      : "common/m5_5_rv_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 50 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 6,
        "name"          : "GMPE 6.2ss NoCal 20km",
        "short_name"    : "GMPE62SS-20-NOCAL",
        "bbp_folder"    : "GMPE62SS-20-NOCAL",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m6_2_ss_nocal.src",
        "stl_file"      : "common/m6_2_ss_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 7,
        "name"          : "GMPE 6.2ss NoCal 50km",
        "short_name"    : "GMPE62SS-50-NOCAL",
        "bbp_folder"    : "GMPE62SS-50-NOCAL",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m6_2_ss_nocal.src",
        "stl_file"      : "common/m6_2_ss_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 50 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 10,
        "name"          : "GMPE 6.6rv NoCal 20km",
        "short_name"    : "GMPE66RV-20-NOCAL",
        "bbp_folder"    : "GMPE66RV-20-NOCAL",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m6_6_rv_nocal.src",
        "stl_file"      : "common/m6_6_rv_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 11,
        "name"          : "GMPE 6.6rv NoCal 50km",
        "short_name"    : "GMPE66RV-50-NOCAL",
        "bbp_folder"    : "GMPE66RV-50-NOCAL",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m6_6_rv_nocal.src",
        "stl_file"      : "common/m6_6_rv_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 50 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 14,
        "name"          : "GMPE 6.6ss NoCal 20km",
        "short_name"    : "GMPE66SS-20-NOCAL",
        "bbp_folder"    : "GMPE66SS-20-NOCAL",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m6_6_ss_nocal.src",
        "stl_file"      : "common/m6_6_ss_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 15,
        "name"          : "GMPE 6.6ss NoCal 50km",
        "short_name"    : "GMPE66SS-50-NOCAL",
        "bbp_folder"    : "GMPE66SS-50-NOCAL",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/m6_6_ss_nocal.src",
        "stl_file"      : "common/m6_6_ss_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 50 km distance in Northern California."
        ),
    },
]

# Supported simulation methods and their BBP number
VALIDATION_METHODS = [
    {"bbp_number": 1, "name": "GP (Graves & Pitarka)", "short": "GP"},
    {"bbp_number": 2, "name": "UCSB",                  "short": "UCSB"},
    {"bbp_number": 3, "name": "SDSU",                  "short": "SDSU"},
    {"bbp_number": 4, "name": "EXSIM",                 "short": "EXSIM"},
    {"bbp_number": 5, "name": "Song",                  "short": "Song"},
    {"bbp_number": 6, "name": "Irikura Recipe 1",      "short": "Irikura1"},
    {"bbp_number": 7, "name": "Irikura Recipe 2",      "short": "Irikura2"},
]

# Validation pipeline modules in order (for progress tracking)
VALIDATION_MODULES = [
    ("Genslip",       "Generating slip distribution on fault plane..."),
    ("Jbsim",         "Computing low frequency seismograms (0-1 Hz)..."),
    ("Hfsims",        "Computing high frequency seismograms (1-10+ Hz)..."),
    ("WccSiteamp",    "Applying Vs30 site amplification corrections..."),
    ("Match",         "Merging LF and HF broadband seismograms..."),
    ("Plot_Map",      "Generating station map..."),
    ("PlotSeis",      "Plotting seismograms and overlay comparisons..."),
    ("RotD100",       "Computing RotD50/100 response spectra..."),
    ("RotD50GoF",     "Computing RotD50 goodness-of-fit metrics..."),
    ("FAS",           "Computing Fourier Amplitude Spectra..."),
    ("FASGoF",        "Computing FAS goodness-of-fit metrics..."),
    ("GenHTML",       "Generating HTML summary report..."),
]


# ------------------------------------------------------------------
# DETECTION
# ------------------------------------------------------------------

def get_bbp_val_dir():
    """Returns the BBP validation data directory in WSL."""
    home = WSLBridge.get_wsl_home()
    return f"{home}/bbp_val"


def get_events_with_status(installed_model_names=None):
    """
    Returns all validation events with availability status.
    Checks both model installation and file existence.
    """
    if installed_model_names is None:
        from core.VelocityModels import scan_installed_models
        installed_model_names = scan_installed_models()

    installed_set = set(installed_model_names)
    val_dir       = get_bbp_val_dir()

    result = []
    for event in VALIDATION_EVENTS:
        entry          = dict(event)
        model_ok       = event["required_model"] in installed_set
        entry["available"]     = model_ok
        entry["missing_model"] = "" if model_ok else event["required_model"]

        # Check validation input files
        src_path = f"{val_dir}/{event['bbp_folder']}/{event['src_file']}"
        stl_path = f"{val_dir}/{event['bbp_folder']}/{event['stl_file']}"
        src_ok   = WSLBridge.wsl_path_exists(src_path)
        stl_ok   = WSLBridge.wsl_path_exists(stl_path)
        entry["val_files_ok"] = src_ok and stl_ok
        entry["src_path"]     = src_path
        entry["stl_path"]     = stl_path

        result.append(entry)

    # Sort by bbp_number to match BBP's own ordering
    result.sort(key=lambda e: e["bbp_number"])
    return result


def get_available_events(installed_model_names=None):
    """Returns only events where all requirements are met."""
    return [e for e in get_events_with_status(installed_model_names)
            if e["available"] and e["val_files_ok"]]