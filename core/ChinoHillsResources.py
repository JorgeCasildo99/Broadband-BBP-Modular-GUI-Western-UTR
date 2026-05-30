# ChinoHillsResources.py — core/ChinoHillsResources.py
# -------------------------------------------------------
# Reference data for the Chino Hills 2008 earthquake validation event.
# Used by RupturePanel to display real seismic stations on the map
# and to open the Chino Hills reference panel.
#
# Source: SCEC Broadband Platform v22.4.0 — LA Basin package
# Method: Graves & Pitarka (GP) — most recent update 2021
# -------------------------------------------------------


# --- FAULT GEOMETRY ---
# Real source parameters for the Chino Hills 2008 (Mw 5.39) earthquake
CHINO_HILLS_SRC = {
    "MAGNITUDE"      : 5.39,
    "FAULT_LENGTH"   : 6.30,
    "FAULT_WIDTH"    : 4.60,
    "DEPTH_TO_TOP"   : 12.79,
    "STRIKE"         : 296,
    "RAKE"           : 146,
    "DIP"            : 66,
    "LAT_TOP_CENTER" : 33.939,
    "LON_TOP_CENTER" : -117.771,
    "HYPO_ALONG_STK" : 0.0,
    "HYPO_DOWN_DIP"  : 2.30,
    "DWID"           : 0.1,
    "DLEN"           : 0.1,
    "SEED"           : 2379646,
}

# Event metadata
CHINO_HILLS_META = {
    "event_name"     : "Chino Hills",
    "date"           : "July 29, 2008",
    "magnitude"      : "Mw 5.39",
    "depth_km"       : 14.7,
    "epicenter_lat"  : 33.953,
    "epicenter_lon"  : -117.761,
    "region"         : "LA Basin, Southern California",
    "method"         : "Graves & Pitarka (GP)",
    "bbp_version"    : "SCEC BBP v22.4.0",
    "gp_update"      : "2021 (most recent)",
    "description"    : (
        "The 2008 Chino Hills earthquake was felt across a wide area of "
        "Southern California. It is one of the key validation events for "
        "the LA Basin region in the SCEC Broadband Platform, providing a "
        "well-constrained source model and dense strong-motion recordings."
    )
}

# --- REAL STATION LIST ---
# Format: (Lon, Lat, StationId, Vs30, HP_Freq, LP_Freq)
# Source: BBP LA Basin package — Chino Hills validation event
CHINO_HILLS_STATIONS = [
    (-118.178, 34.037, "25001-24400",  349,  0.2750, 35.2001),
    (-118.299, 34.687, "25002-CIALP",  347,  0.2500, 10.0000),
    (-116.846, 32.891, "25003-CIEML",  805,  0.2500, 10.0000),
    (-118.294, 33.713, "25004-CIFMP",  393,  0.2875, 23.2002),
    (-117.439, 34.100, "25005-CIFON",  335,  0.4000, 10.0000),
    (-118.102, 34.150, "25006-CIKIK",  383,  0.2500, 10.0000),
    (-117.879, 33.597, "25007-CIKML",  389,  0.2750, 10.0000),
    (-117.367, 34.366, "25008-CILUG",  365,  0.2875, 10.0000),
    (-116.041, 34.227, "25009-CIMCT", 1188,  0.2875, 10.0000),
    (-117.562, 34.005, "25010-CIMLS",  335,  0.3625, 10.0000),
    (-118.905, 34.281, "25011-CIMOP",  355,  0.1375, 10.0000),
    (-118.058, 34.224, "25012-CIMWC",  760,  0.3000, 10.0000),
    (-117.844, 33.788, "25013-CIOGC",  318,  0.2625, 10.0000),
    (-117.638, 34.121, "25014-CIPDU",  388,  0.3250, 10.0000),
    (-117.609, 33.795, "25015-CIPLS",  699,  0.4250, 10.0000),
    (-116.378, 33.648, "25016-CIPMD",  786,  0.2625, 10.0000),
    (-117.807, 34.092, "25017-CIPSR",  462,  0.3250, 10.0000),
    (-118.404, 33.743, "25018-CIRPV",  530,  0.3000, 10.0000),
    (-117.235, 34.232, "25019-CSBPX",  393,  0.4750, 10.0000),
    (-119.138, 34.437, "25020-CISES",  351,  0.2125, 10.0000),
    (-118.646, 34.059, "25021-CISPF",  750,  0.2375, 10.0000),
    (-117.789, 33.829, "25022-CISRN",  440,  0.4750, 10.0000),
    (-116.226, 33.575, "25023-CITOR", 1100,  0.2500, 10.0000),
    (-117.951, 34.010, "25024-CIWLT",  342,  0.3375, 10.0000),
    (-116.959, 33.787, "25025-12102",  306,  0.1125, 38.3995),
    (-116.931, 33.744, "25026-12923",  351,  0.1375, 41.6008),
    (-117.817, 33.854, "25027-13849",  359,  0.1000, 48.7995),
    (-117.896, 33.933, "25028-13873",  396,  0.1000, 56.7988),
    (-117.803, 33.927, "25029-13882",  378,  0.0633, 48.7995),
    (-118.315, 33.909, "25030-14988",  354,  0.0674, 32.7998),
    (-117.911, 34.132, "25031-23178",  363,  0.1000, 41.6008),
    (-118.230, 34.096, "25032-24813",  370,  0.1250, 35.9997),
    (-116.717, 33.708, "25033-N5232",  845,  0.1375, 39.2003),
    (-118.377, 33.896, "25034-N5243",  332,  0.1000, 32.7998),
    (-117.321, 33.920, "25035-U5275",  557,  0.1750, 35.9997),
    (-117.365, 34.205, "25036-N5371",  495,  0.1875, 54.4010),
    (-118.560, 34.277, "25037-N5425",  450,  0.1125, 32.0000),
    (-116.390, 33.917, "25038-U5435",  388,  0.2000, 28.0002),
    (-117.230, 32.875, "25039-N5440",  388,  0.3125, 30.3998),
    (-117.820, 33.912, "25040-NS698",  374,  0.1375, 36.7999),
]


def get_station_coords():
    """
    Returns only (lon, lat, station_id) tuples for map plotting.
    Vs30 and frequency info excluded — not needed for visualization.
    """
    return [(s[0], s[1], s[2]) for s in CHINO_HILLS_STATIONS]


def get_station_full(station_id):
    """
    Returns full data for a specific station by ID.
    Used by the click info handler to show Vs30 and frequency details.

    Returns dict or None if not found.
    """
    for s in CHINO_HILLS_STATIONS:
        if s[2] == station_id:
            return {
                "lon"     : s[0],
                "lat"     : s[1],
                "id"      : s[2],
                "vs30"    : s[3],
                "hp_freq" : s[4],
                "lp_freq" : s[5],
            }
    return None