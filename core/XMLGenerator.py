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

# Song RMG uses the same GP codebase downstream (Jbsim/Hfsims/Match/...),
# so it shares GF_PATH/GF_FILE/VELOCITY_MODEL with GP — no new constants needed
# beyond the method label itself.
SONG_METHOD     = "SONG"

# Irikura Recipe 2 shares IrikuraGenSrf and Jbsim with Irikura1, but
# replaces Hfsims with a distinct high-frequency module (IrikuraHF,
# Kamae et al. 1998) — confirmed against a real BBP-generated Irikura2
# XML (run 5874832), not assumed from the Irikura1/Song pattern.
IRIKURA2_METHOD = "IRIKURA2"

# UCSB uses its own low-frequency Green's Function file, under a
# different GF subdirectory (ucsb/lf/) than GP/Irikura/Song (gp/) —
# confirmed against a real BBP-generated UCSB scenario XML (run
# 6907992). UCSB's rupture generator (UCrmg) and its combined LF+HF
# synthesis module (Syn1D) both stage this same file.
UCSB_GF_FILE  = "nr02-vs500_lf.vel"
UCSB_GF_PATH  = f"$BBP_INSTALL_GF/{VELOCITY_MODEL}/ucsb/lf/{UCSB_GF_FILE}"
UCSB_METHOD   = "UCSB"


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
\t\t\t<name>IrikuraGenSrf</name>
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


def _song_rmg_ss_block(src_path, src_name, srf_name):
    """SongRMGSS — single-segment rupture generator for the Song method.
    Confirmed against BBP source (bbp/comps/build_workflow.py): Song uses
    codebase 'GP' downstream, and its __init__ signature
    (r_velmodel, r_srcfile, o_r_srffile, i_vmodel_name) matches
    Genslip/IrikuraGenSrf exactly, so this block is structurally
    identical to _irikura_gen_srf_block — only the module name differs.
    Multi-segment Song (module name 'SongRMGMS') is not yet supported
    by this GUI."""
    return f"""\t\t<BBP_Module>
\t\t\t<name>SongRMGSS</name>
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


def _irikura_hf_block(src_path, stl_path, src_name, srf_name, stl_name):
    """IrikuraHF — Irikura Recipe 2's high-frequency module (Kamae et al.
    1998 stochastic Green's function method), replacing Hfsims. Confirmed
    against a real BBP-generated Irikura2 XML (run 5874832) — the
    argument order is src_name, srf_name, GF_FILE, stl_name,
    VELOCITY_MODEL, which is NOT the same order Hfsims/Jbsim use
    (GF_FILE first) — this was verified from real data, not guessed by
    analogy. staged_files order in the real file is src_path, GF_PATH,
    stl_path."""
    return f"""\t\t<BBP_Module>
\t\t\t<name>IrikuraHF</name>
\t\t\t<staged_files>
\t\t\t\t<file>{src_path}</file>
\t\t\t\t<file>{GF_PATH}</file>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{GF_FILE}</argument>
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
# UCSB MODULE DEFINITIONS
# UCSB does NOT use the rupture + separate-LF + separate-HF + Match
# pattern every other method in this GUI follows. It has only two
# simulation modules: UCrmg (rupture generator) feeds directly into
# Syn1D (combined broadband LF+HF synthesis, one step, no Match).
# A CopySeismograms step follows Syn1D before the shared plotting/
# analysis modules — this does not exist in any other method's
# pipeline. All of this is confirmed against a real BBP-generated
# UCSB scenario XML (run 6907992), not inferred by analogy.
# ------------------------------------------------------------------

def _ucrmg_block(src_path, src_name, srf_name):
    """UCrmg — UCSB's rupture generator. Requires CORNER_FREQ,
    CORNER_FREQ_1, and CORNER_FREQ_2 to be present in the .src file
    (JA19_2S double-corner-frequency source model) — confirmed by a
    real KeyError crash ('corner_freq_1') when they were missing."""
    return f"""\t\t<BBP_Module>
\t\t\t<name>UCrmg</name>
\t\t\t<staged_files>
\t\t\t\t<file>{UCSB_GF_PATH}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{UCSB_GF_FILE}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _syn1d_block(src_path, stl_path, src_name, srf_name, stl_name):
    """Syn1D — UCSB's combined low+high frequency broadband synthesis.
    Unlike Jbsim/Hfsims, there is no separate HF module and no Match
    step afterward — Syn1D produces the final broadband seismograms
    directly from the .srf UCrmg generated."""
    return f"""\t\t<BBP_Module>
\t\t\t<name>Syn1D</name>
\t\t\t<staged_files>
\t\t\t\t<file>{UCSB_GF_PATH}</file>
\t\t\t\t<file>{src_path}</file>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{UCSB_GF_FILE}</argument>
\t\t\t\t<argument type="str">{src_name}</argument>
\t\t\t\t<argument type="str">{srf_name}</argument>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t\t<argument type="str">{VELOCITY_MODEL}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _copyseismograms_block(stl_path, stl_name):
    """CopySeismograms — UCSB-only step that runs after Syn1D and
    before Plot_Map/PlotSeis/RotD100/FAS/GenHTML. No equivalent exists
    in GP/Irikura/Song/ExSIM. The hybrid=True keyword argument is
    confirmed from the real reference XML; its exact purpose (likely
    staging Syn1D's output into the naming convention the shared
    plotting/analysis modules expect) is not yet confirmed against
    BBP's source."""
    return f"""\t\t<BBP_Module>
\t\t\t<name>CopySeismograms</name>
\t\t\t<staged_files>
\t\t\t\t<file>{stl_path}</file>
\t\t\t</staged_files>
\t\t\t<arguments>
\t\t\t\t<argument type="str">{stl_name}</argument>
\t\t\t</arguments>
\t\t\t<keyword_arguments>
\t\t\t\t<keyword_argument keyword="hybrid" type="bool">True</keyword_argument>
\t\t\t</keyword_arguments>
\t\t</BBP_Module>"""


def _genhtml_block_ucsb(src_path, stl_path, src_name, stl_name):
    """Same as _genhtml_block but with method argument 'UCSB' instead
    of 'GP'. Confirmed against a real BBP-generated UCSB scenario XML
    (run 6907992)."""
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
\t\t\t\t<argument type="str">{UCSB_METHOD}</argument>
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


def _genhtml_block_song(src_path, stl_path, src_name, stl_name):
    """Same as _genhtml_block but with method argument 'SONG' instead of
    'GP'. Confirmed against a real BBP-generated Song XML (run 4182486):
    the final GenHTML argument is the top-level method name ('SONG'),
    not the internal codebase ('GP') that Jbsim/Hfsims run under —
    these are two different things in BBP's build_workflow.py."""
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
\t\t\t\t<argument type="str">{SONG_METHOD}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _generate_song_full_xml(base_name, src_path, stl_path, acc_output=False):
    """
    Song — Full Pipeline.
    SongRMGSS → Jbsim → Hfsims → Match → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML
    Identical to GP/Irikura1 full pipeline but replaces the rupture
    generator with SongRMGSS. Uses _genhtml_block_song (method='SONG'),
    confirmed against a real BBP-generated Song XML — unlike Irikura1,
    which reuses the plain GP-labeled _genhtml_block. That difference
    is a confirmed fact from the reference file, not an assumption.
    """
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _song_rmg_ss_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
        _plot_map_block(src_path, stl_path, src_name, stl_name),
        _plotseis_block(src_path, stl_path, src_name, stl_name),
        _rotd100_block(stl_path, stl_name),
        _fas_block(stl_path, stl_name),
        _genhtml_block_song(src_path, stl_path, src_name, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_song_quick_xml(base_name, src_path, stl_path, acc_output=False):
    """Song — Quick Run (SongRMGSS + Jbsim + Hfsims + Match)."""
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _song_rmg_ss_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _hfsims_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_song_rupture_xml(base_name, src_path, stl_path, acc_output=False):
    """Song — Rupture Only (SongRMGSS alone)."""
    srf_name = f"{base_name}.srf"
    src_name = f"{base_name}.src"

    modules = _song_rmg_ss_block(src_path, src_name, srf_name)

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _genhtml_block_irikura2(src_path, stl_path, src_name, stl_name):
    """Same as _genhtml_block but with method argument 'IRIKURA2' instead
    of 'GP'. Confirmed against a real BBP-generated Irikura2 XML (run
    5874832) — same pattern as Song's GenHTML step. This also makes it
    more likely (though still not directly confirmed) that Irikura1's
    reuse of the plain GP-labeled _genhtml_block is the same kind of
    bug this and Song's GenHTML step needed fixing for — worth checking
    against a real Irikura1 XML if one becomes available."""
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
\t\t\t\t<argument type="str">{IRIKURA2_METHOD}</argument>
\t\t\t</arguments>
\t\t</BBP_Module>"""


def _generate_irikura2_full_xml(base_name, src_path, stl_path, acc_output=False):
    """
    Irikura Recipe 2 — Full Pipeline.
    IrikuraGenSrf → Jbsim → IrikuraHF → Match → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML
    Reuses Irikura1's rupture generator and LF module unchanged — only
    the HF step differs (IrikuraHF instead of Hfsims). Confirmed against
    a real BBP-generated Irikura2 XML (run 5874832), including the
    GenHTML method argument.
    """
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _irikura_gen_srf_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _irikura_hf_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
        _plot_map_block(src_path, stl_path, src_name, stl_name),
        _plotseis_block(src_path, stl_path, src_name, stl_name),
        _rotd100_block(stl_path, stl_name),
        _fas_block(stl_path, stl_name),
        _genhtml_block_irikura2(src_path, stl_path, src_name, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_irikura2_quick_xml(base_name, src_path, stl_path, acc_output=False):
    """Irikura Recipe 2 — Quick Run (IrikuraGenSrf + Jbsim + IrikuraHF + Match)."""
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"
    acc_value = "True" if acc_output else "False"

    modules = "\n".join([
        _irikura_gen_srf_block(src_path, src_name, srf_name),
        _jbsim_block(src_path, stl_path, src_name, srf_name, stl_name),
        _irikura_hf_block(src_path, stl_path, src_name, srf_name, stl_name),
        _match_block(stl_path, stl_name, acc_value),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_irikura2_rupture_xml(base_name, src_path, stl_path, acc_output=False):
    """Irikura Recipe 2 — Rupture Only (IrikuraGenSrf alone — identical
    to Irikura1's rupture-only output, since both methods share the
    same rupture generator)."""
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


def _generate_ucsb_full_xml(base_name, src_path, stl_path, acc_output=False):
    """
    UCSB — Full Pipeline.
    UCrmg → Syn1D → CopySeismograms → Plot_Map → PlotSeis → RotD100 → FAS → GenHTML
    No separate HF module and no Match step — Syn1D produces the final
    broadband seismograms directly. Matches a real BBP-generated UCSB
    scenario XML exactly (run 6907992), module-for-module and
    argument-for-argument. acc_output is accepted for API consistency
    but has no effect here, same as ExSIM.
    """
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"

    modules = "\n".join([
        _ucrmg_block(src_path, src_name, srf_name),
        _syn1d_block(src_path, stl_path, src_name, srf_name, stl_name),
        _copyseismograms_block(stl_path, stl_name),
        _plot_map_block(src_path, stl_path, src_name, stl_name),
        _plotseis_block(src_path, stl_path, src_name, stl_name),
        _rotd100_block(stl_path, stl_name),
        _fas_block(stl_path, stl_name),
        _genhtml_block_ucsb(src_path, stl_path, src_name, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_ucsb_quick_xml(base_name, src_path, stl_path, acc_output=False):
    """UCSB — Quick Run (UCrmg + Syn1D + CopySeismograms).
    Produces broadband seismograms, skips plotting/analysis. NOTE: this
    stopping point is inferred by analogy to GP/Irikura/Song's quick
    profile (stop after broadband seismograms exist, before Plot_Map)
    — the reference XML available is a full run only, so this specific
    3-module combination has not been confirmed against a real
    BBP-generated UCSB quick-run XML."""
    srf_name  = f"{base_name}.srf"
    src_name  = f"{base_name}.src"
    stl_name  = f"{base_name}.stl"

    modules = "\n".join([
        _ucrmg_block(src_path, src_name, srf_name),
        _syn1d_block(src_path, stl_path, src_name, srf_name, stl_name),
        _copyseismograms_block(stl_path, stl_name),
    ])

    return f"{_xml_header(stl_path)}\n{modules}\n{_xml_footer()}"


def _generate_ucsb_rupture_xml(base_name, src_path, stl_path, acc_output=False):
    """UCSB — Rupture Only (UCrmg alone).
    Produces the .srf slip distribution file only, same intent as
    Genslip/IrikuraGenSrf/SongRMGSS rupture-only profiles."""
    srf_name = f"{base_name}.srf"
    src_name = f"{base_name}.src"

    modules = _ucrmg_block(src_path, src_name, srf_name)

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
        method (str): "GP", "EXSIM", "IRIKURA1", "IRIKURA2", "SONG", or "UCSB"
        profile (str): "full", "quick", "rupture", or "custom"
    """
    if method == "EXSIM":
        return _generate_exsim_xml(base_name, src_path, stl_path, acc_output)

    if method == "UCSB":
        if profile == "quick":
            return _generate_ucsb_quick_xml(base_name, src_path, stl_path, acc_output)
        elif profile == "rupture":
            return _generate_ucsb_rupture_xml(base_name, src_path, stl_path, acc_output)
        else:
            return _generate_ucsb_full_xml(base_name, src_path, stl_path, acc_output)

    if method == "IRIKURA1":
        if profile == "quick":
            return _generate_irikura1_quick_xml(base_name, src_path, stl_path, acc_output)
        elif profile == "rupture":
            return _generate_irikura1_rupture_xml(base_name, src_path, stl_path, acc_output)
        else:
            return _generate_irikura1_full_xml(base_name, src_path, stl_path, acc_output)

    if method == "IRIKURA2":
        if profile == "quick":
            return _generate_irikura2_quick_xml(base_name, src_path, stl_path, acc_output)
        elif profile == "rupture":
            return _generate_irikura2_rupture_xml(base_name, src_path, stl_path, acc_output)
        else:
            return _generate_irikura2_full_xml(base_name, src_path, stl_path, acc_output)

    if method == "SONG":
        if profile == "quick":
            return _generate_song_quick_xml(base_name, src_path, stl_path, acc_output)
        elif profile == "rupture":
            return _generate_song_rupture_xml(base_name, src_path, stl_path, acc_output)
        else:
            return _generate_song_full_xml(base_name, src_path, stl_path, acc_output)

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

BBP_MODULES_IRIKURA2_FULL = [
    ("IrikuraGenSrf", "Generating rupture model (Irikura Recipe 2)..."),
    ("Jbsim",         "Computing low-frequency seismograms..."),
    ("IrikuraHF",     "Computing high-frequency seismograms (Kamae et al. 1998)..."),
    ("Match",         "Combining LF + HF broadband seismograms..."),
    ("Plot_Map",      "Generating station map..."),
    ("PlotSeis",      "Plotting seismograms..."),
    ("RotD100",       "Computing RotD50/100 response spectra..."),
    ("FAS",           "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",       "Generating HTML report..."),
]

BBP_MODULES_IRIKURA2_QUICK = [
    ("IrikuraGenSrf", "Generating rupture model (Irikura Recipe 2)..."),
    ("Jbsim",         "Computing low-frequency seismograms..."),
    ("IrikuraHF",     "Computing high-frequency seismograms (Kamae et al. 1998)..."),
    ("Match",         "Combining LF + HF broadband seismograms..."),
]

BBP_MODULES_IRIKURA2_RUPTURE = [
    ("IrikuraGenSrf", "Generating rupture model (Irikura Recipe 2)..."),
]

BBP_MODULES_SONG_FULL = [
    ("SongRMGSS", "Generating rupture model (Song RMG)..."),
    ("Jbsim",     "Computing low-frequency seismograms..."),
    ("Hfsims",    "Computing high-frequency seismograms..."),
    ("Match",     "Combining LF + HF broadband seismograms..."),
    ("Plot_Map",  "Generating station map..."),
    ("PlotSeis",  "Plotting seismograms..."),
    ("RotD100",   "Computing RotD50/100 response spectra..."),
    ("FAS",       "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",   "Generating HTML report..."),
]

BBP_MODULES_SONG_QUICK = [
    ("SongRMGSS", "Generating rupture model (Song RMG)..."),
    ("Jbsim",     "Computing low-frequency seismograms..."),
    ("Hfsims",    "Computing high-frequency seismograms..."),
    ("Match",     "Combining LF + HF broadband seismograms..."),
]

BBP_MODULES_SONG_RUPTURE = [
    ("SongRMGSS", "Generating rupture model (Song RMG)..."),
]

BBP_MODULES_EXSIM = [
    ("ExSim",    "Running stochastic ExSIM broadband simulation..."),
    ("Plot_Map", "Generating fault trace and station map..."),
    ("PlotSeis", "Plotting seismograms for all stations..."),
    ("RotD100",  "Computing RotD50/RotD100 response spectra..."),
    ("FAS",      "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",  "Generating HTML summary report..."),
]

BBP_MODULES_UCSB_FULL = [
    ("UCrmg",           "Generating rupture model (UCSB kinematic source)..."),
    ("Syn1D",           "Computing broadband seismograms (combined LF+HF)..."),
    ("CopySeismograms", "Preparing seismograms for analysis..."),
    ("Plot_Map",        "Generating fault trace and station map..."),
    ("PlotSeis",        "Plotting seismograms for all stations..."),
    ("RotD100",         "Computing RotD50/RotD100 response spectra..."),
    ("FAS",             "Computing Fourier Amplitude Spectra..."),
    ("GenHTML",         "Generating HTML summary report..."),
]

BBP_MODULES_UCSB_QUICK = [
    ("UCrmg",           "Generating rupture model (UCSB kinematic source)..."),
    ("Syn1D",           "Computing broadband seismograms (combined LF+HF)..."),
    ("CopySeismograms", "Preparing seismograms for analysis..."),
]

BBP_MODULES_UCSB_RUPTURE = [
    ("UCrmg", "Generating rupture model (UCSB kinematic source)..."),
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

    if method == "IRIKURA2":
        if profile == "quick":
            return BBP_MODULES_IRIKURA2_QUICK
        elif profile == "rupture":
            return BBP_MODULES_IRIKURA2_RUPTURE
        elif profile == "custom" and custom_modules:
            all_desc = {m: d for m, d in BBP_MODULES_IRIKURA2_FULL}
            return [(m, all_desc.get(m, f"Running {m}..."))
                    for m in custom_modules if m in all_desc]
        else:
            return BBP_MODULES_IRIKURA2_FULL

    if method == "SONG":
        if profile == "quick":
            return BBP_MODULES_SONG_QUICK
        elif profile == "rupture":
            return BBP_MODULES_SONG_RUPTURE
        elif profile == "custom" and custom_modules:
            all_desc = {m: d for m, d in BBP_MODULES_SONG_FULL}
            return [(m, all_desc.get(m, f"Running {m}..."))
                    for m in custom_modules if m in all_desc]
        else:
            return BBP_MODULES_SONG_FULL

    if method == "UCSB":
        if profile == "quick":
            return BBP_MODULES_UCSB_QUICK
        elif profile == "rupture":
            return BBP_MODULES_UCSB_RUPTURE
        elif profile == "custom" and custom_modules:
            all_desc = {m: d for m, d in BBP_MODULES_UCSB_FULL}
            return [(m, all_desc.get(m, f"Running {m}..."))
                    for m in custom_modules if m in all_desc]
        else:
            return BBP_MODULES_UCSB_FULL

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