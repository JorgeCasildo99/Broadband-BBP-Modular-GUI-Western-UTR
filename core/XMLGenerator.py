# XMLGenerator.py — core/XMLGenerator.py
# -------------------------------------------------------
# Builds the BBP XML options file for a Graves & Pitarka
# scenario simulation using the LA Basin velocity model.
# Supports 3 simulation profiles:
#   "full"    — all 9 modules (default)
#   "quick"   — Genslip + Jbsim + Hfsims + Match only
#   "rupture" — Genslip only
# -------------------------------------------------------

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.AppConfig import AppConfig
from core.WSLBridge import WSLBridge


# Fixed constants for GP + LA Basin
VELOCITY_MODEL  = "LABasin500"
GF_FILE         = "nr02-vs500.fk1d"
GF_PATH         = f"$BBP_INSTALL_GF/{VELOCITY_MODEL}/gp/{GF_FILE}"
BBP_VERSION     = "22.4.0"
BBP_METHOD      = "GP"

# Fixed constants for ExSIM + LA Basin
EXSIM_PAR_FILE  = "labasin_exsim.par"
EXSIM_PAR_PATH  = f"$BBP_INSTALL_GF/{VELOCITY_MODEL}/uwo/{EXSIM_PAR_FILE}"
EXSIM_METHOD    = "EXSIM"


# ------------------------------------------------------------------
# MODULE DEFINITIONS
# Reusable XML blocks for each module — shared across all profiles
# ------------------------------------------------------------------

def _genslip_block(src_path, src_name, srf_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>Genslip</name>
\t\t\t<staged_files>
\t\t\t\t<file>{GF_PATH}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{GF_FILE}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _irikura_gen_srf_block(src_path, src_name, srf_name):
    """IrikuraGenSrf — rupture generator for Irikura Recipe Method 1.
    Replaces Genslip as the first module; everything downstream is identical."""
    return f"""\t\t<BBP_Module>
\t\t\t<n>IrikuraGenSrf</n>
\t\t\t<staged_files>
\t\t\t\t<file>{GF_PATH}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{GF_FILE}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>Jbsim</name>
\t\t\t<staged_files>
\t\t\t\t<file>{GF_PATH}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{GF_FILE}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>Hfsims</name>
\t\t\t<staged_files>
\t\t\t\t<file>{GF_PATH}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{GF_FILE}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _match_block(stl_path, stl_name, acc_value):
    return f"""\t\t<BBP_Module>
\t\t\t<name>Match</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t\t<keyword_arguments>
\t\t\t\t<keyword_argument keyword="acc" type="bool">{acc_value}</keyword_argument>
\t\t\t</keyword_arguments>
\t\t</BBP_Module>"""


def _plot_map_block(src_path, stl_path, src_name, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>Plot_Map</name>
\t\t\t<staged_files>
\t\t\t\t<file>{src_path}</file>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _plotseis_block(src_path, stl_path, src_name, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>PlotSeis</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="bool">True</argument>
\t\t\t\t<argument type="bool">True</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _rotd100_block(stl_path, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>RotD100</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _fas_block(stl_path, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>FAS</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _genhtml_block(src_path, stl_path, src_name, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>GenHTML</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t\t<argument type="NoneType">None</argument>
\t\t\t\t<argument type="str">{BBP_METHOD}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


# ------------------------------------------------------------------
# EXSIM MODULE DEFINITIONS
# ExSIM collapses Genslip+Jbsim+Hfsims+Match into a single stochastic
# module — no kinematic rupture (.srf), no separate LF/HF split.
# Confirmed against a real BBP-generated ExSIM XML (run 1722857).
# ------------------------------------------------------------------

def _exsim_block(src_path, stl_path, src_name, stl_name):
    return f"""\t\t<BBP_Module>
\t\t\t<name>ExSim</name>
\t\t\t<staged_files>
\t\t\t\t<file>{src_path}</file>
\t\t\t\t<file>{EXSIM_PAR_PATH}</file>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{EXSIM_PAR_FILE}</argument>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _genhtml_block_exsim(src_path, stl_path, src_name, stl_name):
    """Same as _genhtml_block but with method argument 'EXSIM' instead of 'GP'."""
    return f"""\t\t<BBP_Module>
\t\t\t<name>GenHTML</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t\t<argument type="NoneType">None</argument>
\t\t\t\t<argument type="str">{EXSIM_METHOD}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


# ------------------------------------------------------------------
# XML HEADER / FOOTER
# ------------------------------------------------------------------

def _xml_header(stl_path):
    return f"""<BBP_Run_Specification>
\t<Scenario_Run input_station_file="{stl_path}" version="{BBP_VERSION}"/>
\t<BBP_Modules>"""

def _xml_footer():
    return """\t</BBP_Modules>
</BBP_Run_Specification>"""


# ------------------------------------------------------------------
# PROFILE XML GENERATORS
# ------------------------------------------------------------------

def _generate_full_xml(base_name, src_path, stl_path, acc_output=False):
    """
    Full Pipeline — all 9 modules.
    Genslip → Jbsim → Hfsims → Match → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML
    Produces complete results: seismograms, spectra, FAS, maps, HTML report.
    """
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _genslip_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
        _plot_map_block(src_path, stl_path, src_name, stl_name),
        _plotseis_block(src_path, stl_path, src_name, stl_name),
        _rotd100_block(stl_path, stl_name),
        _fas_block(stl_path, stl_name),
        _genhtml_block(src_path, stl_path, src_name, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_irikura1_full_xml(base_name, src_path, stl_path, acc_output=False):
    """
    Irikura Recipe 1 — Full Pipeline.
    IrikuraGenSrf → Jbsim → Hfsims → Match → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML
    Identical to GP full pipeline but replaces Genslip with IrikuraGenSrf.
    """
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _irikura_gen_srf_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
        _plot_map_block(src_path, stl_path, src_name, stl_name),
        _plotseis_block(src_path, stl_path, src_name, stl_name),
        _rotd100_block(stl_path, stl_name),
        _fas_block(stl_path, stl_name),
        _genhtml_block(src_path, stl_path, src_name, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_irikura1_quick_xml(base_name, src_path, stl_path, acc_output=False):
    """Irikura Recipe 1 — Quick Run (IrikuraGenSrf + Jbsim + Hfsims + Match)."""
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _irikura_gen_srf_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_irikura1_rupture_xml(base_name, src_path, stl_path, acc_output=False):
    """Irikura Recipe 1 — Rupture Only (IrikuraGenSrf alone)."""
    srf_name = f"{base_name}.srf"
    src_name = f"{base_name}.src"

    modules = _irikura_gen_srf_block(src_path, src_name, srf_name)

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_quick_xml(base_name, src_path, stl_path, acc_output=False):
    """
    Quick Run — 4 core modules only.
    Genslip → Jbsim → Hfsims → Match
    Produces broadband .vel.bbp and .acc.bbp seismograms.
    Skips all plotting and reporting — much faster for parameter iteration.
    """
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _genslip_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_rupture_xml(base_name, src_path, stl_path, acc_output=False):
    """
    Rupture Only — Genslip alone.
    Produces the slip distribution .srf file and rupture map PNG.
    Useful for source studies focused on fault rupture patterns.
    acc_output is accepted for API consistency but has no effect here.
    """
    srf_name = f"{base_name}.srf"
    src_name = f"{base_name}.src"

    modules = _genslip_block(src_path, src_name, srf_name)

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_exsim_xml(base_name, src_path, stl_path, acc_output=False):
    """
    ExSIM Full Pipeline — 6 modules.
    ExSim → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML
    Stochastic broadband simulation — no kinematic rupture model,
    no LF/HF split, no Match step. acc_output is accepted for API
    consistency with the GP generators but has no effect here, since
    ExSim always produces both velocity and acceleration directly.
    """
    src_name = f"{base_name}.src"
    stl_name = f"{base_name}.stl"

    modules = "\n".join([
        _exsim_block(src_path, stl_path, src_name, stl_name),
        _plot_map_block(src_path, stl_path, src_name, stl_name),
        _plotseis_block(src_path, stl_path, src_name, stl_name),
        _rotd100_block(stl_path, stl_name),
        _fas_block(stl_path, stl_name),
        _genhtml_block_exsim(src_path, stl_path, src_name, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


# ------------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------------

def generate_xml(base_name, src_path, stl_path,
                 acc_output=False, profile="full", custom_modules=None,
                 method="GP"):
    """
    Builds the BBP XML options file for the selected simulation profile.

    Args:
        method (str): "GP", "EXSIM", or "IRIKURA1"
        profile (str): "full", "quick", "rupture", or "custom"
    """
    if method == "EXSIM":
        return _generate_exsim_xml(base_name, src_path, stl_path, acc_output)

    if method == "IRIKURA1":
        if profile == "quick":
            return _generate_irikura1_quick_xml(base_name, src_path, stl_path, acc_output)
        elif profile == "rupture":
            return _generate_irikura1_rupture_xml(base_name, src_path, stl_path, acc_output)
        else:
            return _generate_irikura1_full_xml(base_name, src_path, stl_path, acc_output)

    # GP (default)
    if profile == "quick":
        return _generate_quick_xml(base_name, src_path, stl_path, acc_output)
    elif profile == "rupture":
        return _generate_rupture_xml(base_name, src_path, stl_path, acc_output)
    elif profile == "custom" and custom_modules:
        return _generate_custom_xml(base_name, src_path, stl_path,
                                    acc_output, custom_modules)
    else:
        return _generate_full_xml(base_name, src_path, stl_path, acc_output)


def save_xml(base_name, src_path, stl_path,
             acc_output=False, profile="full", custom_modules=None,
             method="GP"):
    """
    Generates the XML content for the selected profile and writes it
    to the session xml/ folder inside WSL via WSLBridge.
    """
    xml_content  = generate_xml(base_name, src_path, stl_path,
                                acc_output, profile, custom_modules, method)
    xml_wsl_path = f"{AppConfig.xml_path}/{base_name}.xml"

    ok, err = WSLBridge.write_wsl_file(xml_wsl_path, xml_content)
    if not ok:
        return False, f"Failed to write XML: {err}"

    return True, xml_wsl_path


# ------------------------------------------------------------------
# MODULE LISTS PER PROFILE
# Used by SimulationPanel for progress tracking
# ------------------------------------------------------------------

BBP_MODULES_FULL = [
    ("Genslip",  "Generating slip distribution on fault plane..."),
    ("Jbsim",    "Computing low frequency seismograms (0-1 Hz)..."),
    ("Hfsims",   "Computing high frequency seismograms (1-10+ Hz)..."),
    ("Match",    "Merging low and high frequency broadband seismograms..."),
    ("Plot_Map", "Generating fault trace and station map..."),
    ("PlotSeis", "Plotting seismograms for all stations..."),
    ("RotD100",  "Computing RotD50/RotD100 response spectra..."),
    ("FAS",      "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",  "Generating HTML summary report..."),
]

BBP_MODULES_QUICK = [
    ("Genslip", "Generating slip distribution on fault plane..."),
    ("Jbsim",   "Computing low frequency seismograms (0-1 Hz)..."),
    ("Hfsims",  "Computing high frequency seismograms (1-10+ Hz)..."),
    ("Match",   "Merging low and high frequency broadband seismograms..."),
]

BBP_MODULES_RUPTURE = [
    ("Genslip", "Generating slip distribution on fault plane..."),
]

BBP_MODULES_IRIKURA1_FULL = [
    ("IrikuraGenSrf", "Generating rupture model (Irikura Recipe 1)..."),
    ("Jbsim",         "Computing low-frequency seismograms..."),
    ("Hfsims",        "Computing high-frequency seismograms..."),
    ("Match",         "Combining LF + HF broadband seismograms..."),
    ("Plot_Map",      "Generating station map..."),
    ("PlotSeis",      "Plotting seismograms..."),
    ("RotD100",       "Computing RotD50/100 response spectra..."),
    ("FAS",           "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",       "Generating HTML report..."),
]

BBP_MODULES_IRIKURA1_QUICK = [
    ("IrikuraGenSrf", "Generating rupture model (Irikura Recipe 1)..."),
    ("Jbsim",         "Computing low-frequency seismograms..."),
    ("Hfsims",        "Computing high-frequency seismograms..."),
    ("Match",         "Combining LF + HF broadband seismograms..."),
]

BBP_MODULES_IRIKURA1_RUPTURE = [
    ("IrikuraGenSrf", "Generating rupture model (Irikura Recipe 1)..."),
]

BBP_MODULES_EXSIM = [
    ("ExSim",    "Running stochastic ExSIM broadband simulation..."),
    ("Plot_Map", "Generating fault trace and station map..."),
    ("PlotSeis", "Plotting seismograms for all stations..."),
    ("RotD100",  "Computing RotD50/RotD100 response spectra..."),
    ("FAS",      "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",  "Generating HTML summary report..."),
]

# Default — kept for backward compatibility with any existing imports
BBP_MODULES = BBP_MODULES_FULL


def _generate_custom_xml(base_name, src_path, stl_path,
                          acc_output=False, custom_modules=None):
    """
    Custom profile — builds XML with only the selected modules
    in the correct execution order.
    """
    if not custom_modules:
        return _generate_full_xml(base_name, src_path, stl_path, acc_output)

    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    # Map of module name to its XML block builder
    block_builders = {
        "Genslip"  : lambda: _genslip_block(src_path, src_name, srf_name),
        "Jbsim"    : lambda: _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        "Hfsims"   : lambda: _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        "Match"    : lambda: _match_block(stl_path, stl_name, acc_value),
        "Plot_Map" : lambda: _plot_map_block(src_path, stl_path, src_name, stl_name),
        "PlotSeis" : lambda: _plotseis_block(src_path, stl_path, src_name, stl_name),
        "RotD100"  : lambda: _rotd100_block(stl_path, stl_name),
        "FAS"      : lambda: _fas_block(stl_path, stl_name),
        "GenHTML"  : lambda: _genhtml_block(src_path, stl_path, src_name, stl_name),
    }

    # Enforce correct order regardless of user selection order
    correct_order = ["Genslip", "Jbsim", "Hfsims", "Match",
                     "Plot_Map", "PlotSeis", "RotD100", "FAS", "GenHTML"]

    modules = "\n".join([
        block_builders[m]()
        for m in correct_order
        if m in custom_modules and m in block_builders
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def get_modules_for_profile(profile, custom_modules=None, method="GP"):
    """
    Returns the module list for a given profile.
    Used by SimulationPanel to build the progress bar.
    """
    if method == "EXSIM":
        return BBP_MODULES_EXSIM

    if method == "IRIKURA1":
        if profile == "quick":
            return BBP_MODULES_IRIKURA1_QUICK
        elif profile == "rupture":
            return BBP_MODULES_IRIKURA1_RUPTURE
        elif profile == "custom" and custom_modules:
            all_desc = {m: d for m, d in BBP_MODULES_IRIKURA1_FULL}
            return [(m, all_desc.get(m, f"Running {m}..."))
                    for m in custom_modules if m in all_desc]
        else:
            return BBP_MODULES_IRIKURA1_FULL

    # GP (default)
    if profile == "quick":
        return BBP_MODULES_QUICK
    elif profile == "rupture":
        return BBP_MODULES_RUPTURE
    elif profile == "custom" and custom_modules:
        all_desc = {m: d for m, d in BBP_MODULES_FULL}
        return [(m, all_desc.get(m, f"Running {m}..."))
                for m in custom_modules if m in all_desc]
    else:
        return BBP_MODULES_FULL