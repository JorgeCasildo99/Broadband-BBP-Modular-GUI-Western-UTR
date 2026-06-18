import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

from core.WSLBridge import WSLBridge


class AppConfig:

    # Dynamically resolved at runtime from WSL — no hardcoded username
    BASE_PATH = ""

    # Updated when a session is created
    current_session_folder = ""
    src_path        = ""
    stl_path        = ""
    xml_path        = ""
    log_path        = ""
    out_path        = ""

    # Updated after files are generated
    current_src_file   = ""
    current_stl_file   = ""
    current_base_name  = ""

    # Updated after simulation completes
    current_run_id     = ""   # BBP numeric run ID e.g. "8956506"

    # Simulation profile selected by the user in RupturePanel
    # "full", "quick", "rupture", or "custom"
    simulation_profile  = "full"

    # Simulation method selected — "GP" or "EXSIM". Set by whichever
    # panel (GravesAndPitarkaPanel or ExSimPanel) generates files,
    # and read by XMLGenerator.save_xml() / SimulationPanel to build
    # the correct module pipeline.
    simulation_method   = "GP"

    # For custom profile — list of selected module names in order
    custom_modules      = []

    # Whether the user has saved custom Advanced GP Parameters this
    # session (set True by AdvancedSettingsPanel._do_save, reset to
    # False whenever the user returns to the Dashboard — see
    # MainPanel.load_dashboard / WSLBridge.reset_advanced_params_to_defaults).
    advanced_params_active = False

    # Snapshot of the six Advanced GP Parameter values currently active,
    # e.g. {"KAPPA": 0.0292, "SDROP": 76, ...}. Empty when not active.
    advanced_params        = {}

    @classmethod
    def _resolve_base_path(cls):
        """Resolves BASE_PATH from WSL home if not already set."""
        if not cls.BASE_PATH:
            cls.BASE_PATH = f"{WSLBridge.get_wsl_home()}/bbp_projects"

    @classmethod
    def create_session_structure(cls):
        """
        Creates a unique timestamped session folder inside WSL with only
        the input file directories needed to run a simulation.
        Results are read directly from $BBP_DATA_DIR/outdata/<run_id>/
        and are never copied into the session folder.
        Returns (success: bool, error_msg: str).
        """
        cls._resolve_base_path()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.current_session_folder = f"{cls.BASE_PATH}/{timestamp}"

        cls.src_path = f"{cls.current_session_folder}/src"
        cls.stl_path = f"{cls.current_session_folder}/stl"
        cls.xml_path = f"{cls.current_session_folder}/xml"
        cls.log_path = f"{cls.current_session_folder}/logs"
        # out_path is NOT created here — it is set after simulation
        # to $BBP_DATA_DIR/outdata/<run_id> (BBP's native output location)
        cls.out_path = ""

        success, error = WSLBridge.make_wsl_dirs(
            cls.src_path,
            cls.stl_path,
            cls.xml_path,
            cls.log_path
        )

        if not success:
            return False, error
        return True, ""

    @classmethod
    def get_session_info(cls):
        """
        Returns a summary dict of the current session paths.
        Useful for displaying session details in the GUI or for debugging.
        """
        return {
            "session" : cls.current_session_folder,
            "src"     : cls.src_path,
            "stl"     : cls.stl_path,
            "xml"     : cls.xml_path,
            "logs"    : cls.log_path,
            "output"  : cls.out_path,
        }

    @classmethod
    def session_is_active(cls):
        """Returns True if a session has been created and the folder exists in WSL."""
        if not cls.current_session_folder:
            return False
        return WSLBridge.wsl_path_exists(cls.current_session_folder)

    @classmethod
    def get_profile_label(cls):
        """Returns a human-readable label for the current simulation profile."""
        labels = {
            "full"    : "Full Pipeline",
            "quick"   : "Quick Run",
            "rupture" : "Rupture Only",
            "custom"  : f"Custom ({len(cls.custom_modules)} modules)",
        }
        return labels.get(cls.simulation_profile, "Full Pipeline")