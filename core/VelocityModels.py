# VelocityModels.py — core/VelocityModels.py
# -------------------------------------------------------
# Registry of all known BBP v22.4.0 velocity models.
# Source: https://github.com/SCECcode/bbp
# Handles detection of installed models by scanning the
# WSL Green's Functions directory for velmodel_config files.
# -------------------------------------------------------

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.WSLBridge import WSLBridge


# ------------------------------------------------------------------
# FULL CATALOG — BBP v22.4.0 official velocity models
# Source: https://github.com/SCECcode/bbp (README + wiki + FAQ)
# ------------------------------------------------------------------

KNOWN_MODELS = [
    {
        "name"        : "LABasin500",
        "full_name"   : "LA Basin 500 m/s",
        "region"      : "Southern California — Los Angeles Basin",
        "coverage"    : "Los Angeles Basin and surrounding area",
        "gf_distance" : "0.1 – 500 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~25 GB",
        "codebases"   : ["GP", "UCSB", "SDSU", "EXSIM"],
        "config_file" : "labasin500_velmodel_config.txt",
        "note"        : "Required for BBP unit and acceptance tests.",
        "description" : (
            "The standard velocity model for Southern California simulations. "
            "Based on the NR02 crustal model with Vs30 = 500 m/s reference. "
            "Green's Functions pre-computed at 715 distances from 0.1 to 500 km. "
            "Most commonly used model for LA Basin validation studies including "
            "Chino Hills, Northridge, and other Southern California events."
        ),
        "validation_events": ["Chino Hills 2008", "Northridge 1994", "GMPE SoCal"],
        "boundary_lons": [
            -119.30, -119.00, -118.70, -118.40, -118.10,
            -117.80, -117.50, -117.30, -117.20, -117.30,
            -117.50, -117.80, -118.00, -118.20, -118.50,
            -118.70, -119.00, -119.20, -119.40, -119.30
        ],
        "boundary_lats": [
            34.00, 33.70, 33.50, 33.40, 33.42,
            33.50, 33.60, 33.75, 34.00, 34.30,
            34.50, 34.55, 34.60, 34.55, 34.45,
            34.30, 34.20, 34.10, 34.05, 34.00
        ],
    },
    {
        "name"        : "NOCAL500",
        "full_name"   : "Northern California 500 m/s",
        "region"      : "Northern California — San Francisco Bay Area",
        "coverage"    : "San Francisco Bay Area and Northern California",
        "gf_distance" : "0.1 – 400 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~27 GB",
        "codebases"   : ["GP", "UCSB", "SDSU", "EXSIM"],
        "config_file" : "nocal500_velmodel_config.txt",
        "note"        : "",
        "description" : (
            "Velocity model for Northern California and the San Francisco Bay Area. "
            "Covers the region around the San Andreas fault in Northern California. "
            "Used for Loma Prieta and other Bay Area validation events."
        ),
        "validation_events": ["Loma Prieta 1989", "GMPE NoCal"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
    {
        "name"        : "CentralCal500",
        "full_name"   : "Central California 500 m/s",
        "region"      : "Central California Coast",
        "coverage"    : "Central California coastal region and Central Valley",
        "gf_distance" : "0.1 – 400 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~14 GB",
        "codebases"   : ["GP", "UCSB", "SDSU", "EXSIM"],
        "config_file" : "centralcal500_velmodel_config.txt",
        "note"        : "",
        "description" : (
            "Velocity model for the Central California coast region. "
            "Covers the central part of California including the Central Coast. "
            "Used for San Simeon and other Central California validation events."
        ),
        "validation_events": ["San Simeon 2003"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
    {
        "name"        : "Mojave500",
        "full_name"   : "Mojave Desert 500 m/s",
        "region"      : "Mojave Desert — Eastern California",
        "coverage"    : "Mojave Desert and surrounding desert regions",
        "gf_distance" : "0.1 – 400 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~27 GB",
        "codebases"   : ["GP", "UCSB", "SDSU", "EXSIM"],
        "config_file" : "mojave500_velmodel_config.txt",
        "note"        : "",
        "description" : (
            "Velocity model for the Mojave Desert region of Eastern California. "
            "Covers the Mojave Desert and surrounding areas. "
            "Used for Landers, Hector Mine, and other desert earthquake validations."
        ),
        "validation_events": ["Landers 1992", "Hector Mine 1999"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
    {
        "name"        : "SWalkerLane500",
        "full_name"   : "Southern Walker Lane 500 m/s",
        "region"      : "Southern Walker Lane — Southern Sierra Nevada",
        "coverage"    : "Southern Sierra Nevada and Eastern California",
        "gf_distance" : "0.1 – 400 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~20 GB",
        "codebases"   : ["GP"],
        "config_file" : "swalkerlane500_velmodel_config.txt",
        "note"        : "Added in BBP v22.4.0. Includes 2019 Ridgecrest sequence.",
        "description" : (
            "Velocity model for the Southern Walker Lane region (Southern Sierra Nevada). "
            "Added in BBP v22.4.0. Covers Eastern California near the Sierra Nevada. "
            "Used for the 2019 Ridgecrest earthquake sequence validation."
        ),
        "validation_events": ["Ridgecrest 2019 M6.4", "Ridgecrest 2019 M7.1"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
    {
        "name"        : "CentralJapan500",
        "full_name"   : "Central Japan 500 m/s",
        "region"      : "Japan — Central Honshu",
        "coverage"    : "Central Japan including Tokyo metropolitan area",
        "gf_distance" : "0.1 – 400 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~28 GB",
        "codebases"   : ["GP", "SDSU", "EXSIM"],
        "config_file" : "centraljapan500_velmodel_config.txt",
        "note"        : "",
        "description" : (
            "Velocity model for Central Japan including the Tokyo metropolitan area. "
            "Supports simulation of Japanese earthquakes using BBP methods. "
            "Used for validation of historical Central Japan events."
        ),
        "validation_events": ["Tottori 2000", "Niigata 2004"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
    {
        "name"        : "WesternJapan500",
        "full_name"   : "Western Japan 500 m/s",
        "region"      : "Japan — Western Honshu and Kyushu",
        "coverage"    : "Western Japan including Osaka and surrounding regions",
        "gf_distance" : "0.1 – 400 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~25 GB",
        "codebases"   : ["GP", "SDSU", "EXSIM"],
        "config_file" : "westernjapan500_velmodel_config.txt",
        "note"        : "",
        "description" : (
            "Velocity model for Western Japan including the Osaka region. "
            "Supports simulation of Western Japan earthquakes using BBP methods. "
            "Used for validation of historical Western Japan events."
        ),
        "validation_events": ["Kobe 1995"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
    {
        "name"        : "ENA500",
        "full_name"   : "Eastern North America 500 m/s",
        "region"      : "Eastern North America — Virginia & Eastern Canada",
        "coverage"    : "Eastern United States and Eastern Canada",
        "gf_distance" : "0.1 – 1800 km (epicentral)",
        "vs30_ref"    : 500,
        "install_size": "~20 GB",
        "codebases"   : ["GP", "EXSIM"],
        "config_file" : "ena500_velmodel_config.txt",
        "note"        : "Longest GF range: up to 1800 km.",
        "description" : (
            "Velocity model for Eastern North America including Virginia and Eastern Canada. "
            "Features the longest Green's Function range of all BBP models (up to 1800 km), "
            "reflecting the efficient wave propagation in the stable continental crust. "
            "Used for Eastern US and Canadian earthquake simulations."
        ),
        "validation_events": ["Virginia 2011", "Saguenay 1988"],
        "boundary_lons": [],
        "boundary_lats": [],
    },
]


# ------------------------------------------------------------------
# DETECTION — scans WSL bbp_gf/ directory
# ------------------------------------------------------------------

def get_gf_dir():
    """Returns the Green's Functions directory path in WSL."""
    home = WSLBridge.get_wsl_home()
    return f"{home}/bbp_gf"


def scan_installed_models():
    """
    Scans the WSL bbp_gf/ directory for installed velocity models.
    A model is considered installed if its folder exists AND contains
    a *velmodel_config.txt file.
    Returns a list of installed model folder names (strings).
    """
    gf_dir = get_gf_dir()

    result = WSLBridge.run_command(
        f"ls -d {gf_dir}/*/ 2>/dev/null | xargs -I{{}} basename {{}}"
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    installed = []
    for folder in result.stdout.strip().splitlines():
        folder = folder.strip()
        if not folder:
            continue
        check = WSLBridge.run_command(
            f"ls {gf_dir}/{folder}/*velmodel_config.txt 2>/dev/null"
        )
        if check.returncode == 0 and check.stdout.strip():
            installed.append(folder)

    return installed


def get_all_models_with_status():
    """
    Returns the full catalog with an 'installed' boolean added to each entry.
    Also detects any installed models not in the known catalog.
    """
    installed_names = scan_installed_models()

    result = []
    for model in KNOWN_MODELS:
        entry = dict(model)
        entry["installed"] = (model["name"] in installed_names)
        result.append(entry)

    # Catch any installed models not in our catalog
    known_names = {m["name"] for m in KNOWN_MODELS}
    for name in installed_names:
        if name not in known_names:
            result.append({
                "name"             : name,
                "full_name"        : name,
                "region"           : "Unknown",
                "coverage"         : "Not in catalog — may be custom or newer",
                "gf_distance"      : "Unknown",
                "vs30_ref"         : "Unknown",
                "install_size"     : "Unknown",
                "codebases"        : [],
                "config_file"      : "",
                "note"             : "Custom or unrecognized model.",
                "description"      : (
                    "This model was found in ~/bbp_gf/ but is not in the "
                    "known catalog. It may be a custom or newer model."
                ),
                "validation_events": [],
                "installed"        : True,
                "boundary_lons"    : [],
                "boundary_lats"    : [],
            })

    return result


def get_model_by_name(name):
    """Returns a single model dict (with installed status) by name, or None."""
    for model in get_all_models_with_status():
        if model["name"] == name:
            return model
    return None


def get_installed_models():
    """Returns only installed models with full details."""
    return [m for m in get_all_models_with_status() if m["installed"]]