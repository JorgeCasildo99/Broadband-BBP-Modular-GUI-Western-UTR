# ValidationEvents.py — core/ValidationEvents.py
# -------------------------------------------------------
# Registry of all known BBP v22.4.0 validation events.
# Maps each event to its required velocity model,
# BBP event number, file paths, and metadata.
# Source: https://github.com/SCECcode/bbp
# -------------------------------------------------------

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.WSLBridge import WSLBridge


# ------------------------------------------------------------------
# COMPLETE EVENT CATALOG — BBP v22.4.0
# bbp_number: the number you type when BBP asks "? [event number]"
# ------------------------------------------------------------------

VALIDATION_EVENTS = [
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
        "bbp_number"    : 4,
        "name"          : "GMPE 5.5rv SoCal 20km",
        "short_name"    : "GMPE_5p5rv_SoCal_20km",
        "bbp_folder"    : "GMPE_5p5rv_SoCal_20km",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_5p5rv_socal_20km.src",
        "stl_file"      : "common/gmpe_5p5rv_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 5,
        "name"          : "GMPE 5.5rv SoCal 50km",
        "short_name"    : "GMPE_5p5rv_SoCal_50km",
        "bbp_folder"    : "GMPE_5p5rv_SoCal_50km",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_5p5rv_socal_50km.src",
        "stl_file"      : "common/gmpe_5p5rv_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 50 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 8,
        "name"          : "GMPE 6.2ss SoCal 20km",
        "short_name"    : "GMPE_6p2ss_SoCal_20km",
        "bbp_folder"    : "GMPE_6p2ss_SoCal_20km",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_6p2ss_socal_20km.src",
        "stl_file"      : "common/gmpe_6p2ss_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 9,
        "name"          : "GMPE 6.2ss SoCal 50km",
        "short_name"    : "GMPE_6p2ss_SoCal_50km",
        "bbp_folder"    : "GMPE_6p2ss_SoCal_50km",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_6p2ss_socal_50km.src",
        "stl_file"      : "common/gmpe_6p2ss_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 50 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 12,
        "name"          : "GMPE 6.6rv SoCal 20km",
        "short_name"    : "GMPE_6p6rv_SoCal_20km",
        "bbp_folder"    : "GMPE_6p6rv_SoCal_20km",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_6p6rv_socal_20km.src",
        "stl_file"      : "common/gmpe_6p6rv_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 13,
        "name"          : "GMPE 6.6rv SoCal 50km",
        "short_name"    : "GMPE_6p6rv_SoCal_50km",
        "bbp_folder"    : "GMPE_6p6rv_SoCal_50km",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_6p6rv_socal_50km.src",
        "stl_file"      : "common/gmpe_6p6rv_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 50 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 16,
        "name"          : "GMPE 6.6ss SoCal 20km",
        "short_name"    : "GMPE_6p6ss_SoCal_20km",
        "bbp_folder"    : "GMPE_6p6ss_SoCal_20km",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_6p6ss_socal_20km.src",
        "stl_file"      : "common/gmpe_6p6ss_socal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 20 km distance in Southern California."
        ),
    },
    {
        "bbp_number"    : 17,
        "name"          : "GMPE 6.6ss SoCal 50km",
        "short_name"    : "GMPE_6p6ss_SoCal_50km",
        "bbp_folder"    : "GMPE_6p6ss_SoCal_50km",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Southern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "LABasin500",
        "src_file"      : "common/gmpe_6p6ss_socal_50km.src",
        "stl_file"      : "common/gmpe_6p6ss_socal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 50 km distance in Southern California."
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
            "across the Los Angeles area. It is one of the most important "
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
        "src_file"      : "common/whittier_v19_06_1.src",
        "stl_file"      : "common/whittier_v19_06_1.stl",
        "description"   : (
            "The 1987 Whittier Narrows earthquake was a moderate event "
            "that caused significant damage in the Los Angeles area. "
            "Used as a validation event for the LA Basin velocity model."
        ),
    },
    # --- NOCAL500 events (require NOCAL500) ---
    {
        "bbp_number"    : 2,
        "name"          : "GMPE 5.5rv NoCal 20km",
        "short_name"    : "GMPE_5p5rv_NoCal_20km",
        "bbp_folder"    : "GMPE_5p5rv_NoCal_20km",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_5p5rv_nocal_20km.src",
        "stl_file"      : "common/gmpe_5p5rv_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 3,
        "name"          : "GMPE 5.5rv NoCal 50km",
        "short_name"    : "GMPE_5p5rv_NoCal_50km",
        "bbp_folder"    : "GMPE_5p5rv_NoCal_50km",
        "magnitude"     : "Mw 5.5 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_5p5rv_nocal_50km.src",
        "stl_file"      : "common/gmpe_5p5rv_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 5.5 reverse-fault event "
            "at 50 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 6,
        "name"          : "GMPE 6.2ss NoCal 20km",
        "short_name"    : "GMPE_6p2ss_NoCal_20km",
        "bbp_folder"    : "GMPE_6p2ss_NoCal_20km",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_6p2ss_nocal_20km.src",
        "stl_file"      : "common/gmpe_6p2ss_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 7,
        "name"          : "GMPE 6.2ss NoCal 50km",
        "short_name"    : "GMPE_6p2ss_NoCal_50km",
        "bbp_folder"    : "GMPE_6p2ss_NoCal_50km",
        "magnitude"     : "Mw 6.2 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_6p2ss_nocal_50km.src",
        "stl_file"      : "common/gmpe_6p2ss_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.2 strike-slip event "
            "at 50 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 10,
        "name"          : "GMPE 6.6rv NoCal 20km",
        "short_name"    : "GMPE_6p6rv_NoCal_20km",
        "bbp_folder"    : "GMPE_6p6rv_NoCal_20km",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_6p6rv_nocal_20km.src",
        "stl_file"      : "common/gmpe_6p6rv_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 11,
        "name"          : "GMPE 6.6rv NoCal 50km",
        "short_name"    : "GMPE_6p6rv_NoCal_50km",
        "bbp_folder"    : "GMPE_6p6rv_NoCal_50km",
        "magnitude"     : "Mw 6.6 (reverse)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_6p6rv_nocal_50km.src",
        "stl_file"      : "common/gmpe_6p6rv_nocal_50km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 reverse-fault event "
            "at 50 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 14,
        "name"          : "GMPE 6.6ss NoCal 20km",
        "short_name"    : "GMPE_6p6ss_NoCal_20km",
        "bbp_folder"    : "GMPE_6p6ss_NoCal_20km",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_6p6ss_nocal_20km.src",
        "stl_file"      : "common/gmpe_6p6ss_nocal_20km.stl",
        "description"   : (
            "GMPE validation scenario: Mw 6.6 strike-slip event "
            "at 20 km distance in Northern California."
        ),
    },
    {
        "bbp_number"    : 15,
        "name"          : "GMPE 6.6ss NoCal 50km",
        "short_name"    : "GMPE_6p6ss_NoCal_50km",
        "bbp_folder"    : "GMPE_6p6ss_NoCal_50km",
        "magnitude"     : "Mw 6.6 (strike-slip)",
        "date"          : "Synthetic",
        "region"        : "Northern California",
        "depth_km"      : 8.0,
        "stations"      : 20,
        "required_model": "NOCAL500",
        "src_file"      : "common/gmpe_6p6ss_nocal_50km.src",
        "stl_file"      : "common/gmpe_6p6ss_nocal_50km.stl",
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
    ("Jbsim",         "Computing low frequency seismograms (0–1 Hz)..."),
    ("Hfsims",        "Computing high frequency seismograms (1–10+ Hz)..."),
    ("WccSiteamp",    "Applying Vs30 site amplification corrections..."),
    ("Match",         "Merging LF and HF broadband seismograms..."),
    ("Plot_Map",      "Generating station map..."),
    ("PlotSeis",      "Plotting seismograms and overlay comparisons..."),
    ("RotD100",       "Computing RotD50/100 response spectra + GoF..."),
    ("RotD50GoF",     "Computing RotD50 goodness-of-fit metrics..."),
    ("FAS",           "Computing Fourier Amplitude Spectra..."),
    ("FASGoF",        "Computing FAS goodness-of-fit metrics..."),
    ("GenHTML",       "Generating HTML summary report..."),
]


# ------------------------------------------------------------------
# DETECTION — checks installed models and flags available events
# ------------------------------------------------------------------

def get_bbp_val_dir():
    """Returns the BBP validation data directory in WSL."""
    home = WSLBridge.get_wsl_home()
    return f"{home}/bbp_val"


def get_events_with_status(installed_model_names=None):
    """
    Returns all validation events with availability status.

    Args:
        installed_model_names (list|None): List of installed model name strings.
            If None, scans WSL automatically via VelocityModels.

    Returns:
        list of dicts — each event dict plus:
            'available'  : bool — True if required model is installed
            'missing_model': str — name of missing model, or ""
            'val_files_ok' : bool — True if src/stl files exist in bbp_val/
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

        # Check if validation input files exist in bbp_val/
        src_path = f"{val_dir}/{event['bbp_folder']}/{event['src_file']}"
        stl_path = f"{val_dir}/{event['bbp_folder']}/{event['stl_file']}"
        src_ok   = WSLBridge.wsl_path_exists(src_path)
        stl_ok   = WSLBridge.wsl_path_exists(stl_path)
        entry["val_files_ok"] = src_ok and stl_ok
        entry["src_path"]     = src_path
        entry["stl_path"]     = stl_path

        result.append(entry)

    return result


def get_available_events(installed_model_names=None):
    """Returns only events where all requirements are met."""
    return [e for e in get_events_with_status(installed_model_names)
            if e["available"] and e["val_files_ok"]]