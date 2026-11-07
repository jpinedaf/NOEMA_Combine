import numpy as np
from unittest.mock import MagicMock, patch

import noema_combine.data_handler as dh
from noema_combine.data_handler import refresh_config


@patch("noema_combine.data_handler.get_config")
def test_refresh_config_updates_aliases(
    mock_get_config: MagicMock, monkeypatch
):
    """Test refresh_config updates module-level aliases."""
    cfg = MagicMock()
    cfg.file_source_catalogue = "/catalogue/source.yml"
    cfg.region_catalogue = {}
    cfg.selfcal_ext = "_sc"
    cfg.uvsub_ext = "_uvsub"
    cfg.file_line_catalogue = "/catalogue/line.csv"
    cfg.file_extensions_sd = ".apex"
    cfg.telescope_class = "APEX"
    cfg.ignorefiles = []
    cfg.line_name = np.array(["CO"])
    cfg.qn = np.array(["1-0"])
    cfg.freq = np.array(["115.271"])
    cfg.freq_ghz = cfg.freq.copy()
    cfg.freq_mhz = np.array(["115271"])
    cfg.name_str = np.array(["CO(1-0)"])
    cfg.qn_str = np.array(["1-0"])
    cfg.Lid = np.array(["L09"])
    cfg.vel_width = np.array(["5.0"])
    cfg.vel_width_sd = np.array(["3.0"])
    cfg.vel_width_base_sd = np.array(["5.0"])
    cfg.uvt_dir = "/uvt"
    cfg.dir_sd = "/sd"
    cfg.uvt_dir_out = "/uvt_out"
    cfg.inputdir = ["/input"]
    mock_get_config.return_value = cfg

    bound_names = (
        "_cfg", "file_source_catalogue", "region_catalogue", "selfcal_ext",
        "uvsub_ext", "file_line_catalogue", "file_extensions_sd", "telescope_class",
        "ignorefiles", "line_name", "qn", "freq", "freq_mhz", "name_str",
        "qn_str", "Lid", "vel_width", "vel_width_sd", "vel_width_base_sd",
        "uvt_dir", "dir_sd", "uvt_dir_out", "inputdir",
    )
    original_values = {name: getattr(dh, name) for name in bound_names}
    with monkeypatch.context() as context:
        for name, value in original_values.items():
            context.setattr(dh, name, value)

        refresh_config()

        assert dh._cfg is cfg
        assert dh.dir_sd == "/sd"
        assert dh.telescope_class == "APEX"
        assert dh.uvt_dir == "/uvt"

    for name, value in original_values.items():
        assert getattr(dh, name) is value
