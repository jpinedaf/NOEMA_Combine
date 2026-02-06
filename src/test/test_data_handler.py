import pytest
from unittest.mock import patch, MagicMock  # , mock_open, call
import numpy as np
import warnings

import noema_combine.data_handler as dh
from noema_combine.data_handler import (
    get_line_param,
    get_source_param,
    get_uvt_window,
    get_uvt_file,
    get_30m_file,
    get_sd_file,
    refresh_config,
    # line_prepare_merge,
    line_reduce_30m,
    line_reduce_sd,
    line_make_uvt,
)


# Tests for get_line_param
@patch("noema_combine.data_handler.line_name", np.array(["CO", "13CO", "N2H+"]))
@patch("noema_combine.data_handler.qn_str", np.array(["1-0", "1-0", "1-0"]))
def test_get_line_param_with_qn_found():
    """Test finding line index with quantum number"""
    index = get_line_param("CO", "1-0")
    assert index == 0


@patch("noema_combine.data_handler.line_name", np.array(["CO", "13CO"]))
@patch("noema_combine.data_handler.qn_str", np.array(["1-0", "1-0"]))
def test_get_line_param_without_qn_single_entry():
    """Test finding line index without QN when only one entry exists"""
    index = get_line_param("13CO", None)
    assert index == 1


@patch("noema_combine.data_handler.line_name", np.array(["CO", "CO", "13CO"]))
@patch("noema_combine.data_handler.qn_str", np.array(["1-0", "2-1", "1-0"]))
def test_get_line_param_without_qn_multiple_entries_raises_error():
    """Test that error is raised when multiple entries exist without QN"""
    with pytest.raises(ValueError, match="Line name is not unique"):
        get_line_param("CO", None)


@patch("noema_combine.data_handler.line_name", np.array(["CO", "13CO"]))
@patch("noema_combine.data_handler.qn_str", np.array(["1-0", "1-0"]))
def test_get_line_param_not_found():
    """Test that error is raised when line is not found"""
    with pytest.raises(ValueError, match="Line not found in the catalogue"):
        get_line_param("N2H+", "1-0")


@patch("noema_combine.data_handler.line_name", np.array(["CO", "CO"]))
@patch("noema_combine.data_handler.qn_str", np.array(["1-0", "2-1"]))
def test_get_line_param_with_qn_second_entry():
    """Test finding second line entry with specific QN"""
    index = get_line_param("CO", "2-1")
    assert index == 1


# Tests for get_source_param
@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "B5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        }
    },
    clear=True,
)
def test_get_source_param_found():
    """Test retrieving source parameters"""
    result = get_source_param("B5")
    assert result == ("B5", "B5", "B5_out", 50.5, 30.2, 10.0)


@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        },
        "B5_HMS": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "03h22m0s",
            "Dec0": "30d12m0s",
            "Vlsr": "10.0",
        },
        "B5_HMS_v2": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "03:22:00",
            "Dec0": "30:12:00",
            "Vlsr": "10.0",
        },
    },
    clear=True,
)
def test_get_source_param_coordinates():
    """Test retrieving source parameters with coordinates"""
    result = get_source_param("B5")
    assert result[0] == "B5"
    assert result[1] == "b5"
    assert result[2] == "B5_out"
    assert result[5] == 10.0
    np.testing.assert_approx_equal(result[3], 50.5, significant=4)
    np.testing.assert_approx_equal(result[4], 30.2, significant=4)
    result = get_source_param("B5_HMS")
    assert result[0] == "B5_HMS"
    assert result[1] == "b5"
    assert result[2] == "B5_out"
    assert result[5] == 10.0
    np.testing.assert_approx_equal(result[3], 50.5, significant=4)
    np.testing.assert_approx_equal(result[4], 30.2, significant=4)
    result = get_source_param("B5_HMS_v2")
    assert result[0] == "B5_HMS_v2"
    assert result[1] == "b5"
    assert result[2] == "B5_out"
    assert result[5] == 10.0
    np.testing.assert_approx_equal(result[3], 50.5, significant=4)
    np.testing.assert_approx_equal(result[4], 30.2, significant=4)


@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "B5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        },
        "NGC1333": {
            "source_sd": "NGC1333",
            "source_out": "NGC1333_out",
            "RA0": "52.3",
            "Dec0": "31.1",
            "Vlsr": "8.5",
        },
    },
    clear=True,
)
def test_get_source_param_second_source():
    """Test retrieving second source parameters"""
    result = get_source_param("NGC1333")
    assert result == ("NGC1333", "NGC1333", "NGC1333_out", 52.3, 31.1, 8.5)


@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "B5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        },
        "NGC1333": {
            "source_sd": "NGC1333",
            "source_out": "NGC1333_out",
            "RA0": "52.3",
            "Dec0": "31.1",
            "Vlsr": "8.5",
        },
    },
    clear=True,
)
def test_get_source_param_not_found():
    """Test that error is raised when source is not found"""
    with pytest.raises(ValueError, match="Region .* not found in region_catalogue"):
        get_source_param("Unknown")


# Tests for get_uvt_window
@patch("noema_combine.data_handler.uvt_dir", "/path/to/uvt")
@patch("noema_combine.data_handler.uvsub_ext", "_uvsub")
def test_get_uvt_window_default():
    """Test default uvt window filename generation"""
    result = get_uvt_window("B5", "L09")
    assert result == "/path/to/uvt/L09/B5_L09_uvsub.uvt"


@patch("noema_combine.data_handler.uvt_dir", "/path/to/uvt")
def test_get_uvt_window_no_uvsub():
    """Test uvt window filename without uvsub"""
    result = get_uvt_window("B5", "L09", uvsub=False)
    assert result == "/path/to/uvt/L09/B5_L09.uvt"


@patch("noema_combine.data_handler.uvt_dir", "/path/to/uvt")
@patch("noema_combine.data_handler.selfcal_ext", "_sc")
@patch("noema_combine.data_handler.uvsub_ext", "_uvsub")
def test_get_uvt_window_with_selfcal():
    """Test uvt window filename with selfcal"""
    result = get_uvt_window("B5", "L09", selfcal=True)
    assert result == "/path/to/uvt/L09/B5_L09_sc_uvsub.uvt"


@patch("noema_combine.data_handler.uvt_dir", "/path/to/uvt")
def test_get_uvt_window_no_uvsub_with_selfcal():
    """Test uvt window filename with selfcal but no uvsub"""
    result = get_uvt_window("B5", "L09", uvsub=False, selfcal=True)
    assert result == "/path/to/uvt/L09/B5_L09_sc.uvt"


@patch("noema_combine.data_handler.uvt_dir", "/data/uvt")
@patch("noema_combine.data_handler.uvsub_ext", "_uvsub")
def test_get_uvt_window_different_lid():
    """Test uvt window filename with different Lid"""
    result = get_uvt_window("NGC1333", "L11", uvsub=True, selfcal=False)
    assert result == "/data/uvt/L11/NGC1333_L11_uvsub.uvt"


# Tests for get_uvt_file
@patch("noema_combine.data_handler.uvt_dir", "/path/to/uvt")
def test_get_uvt_file_no_merge():
    """Test uvt filename generation without merge"""
    result = get_uvt_file("B5", "CO", "1-0", "L09", merge=False)
    assert result == "/path/to/uvt/L09/B5_CO_1-0_L09.uvt"


@patch("noema_combine.data_handler.uvt_dir_out", "/path/to/uvt_out")
def test_get_uvt_file_with_merge():
    """Test uvt filename generation with merge"""
    result = get_uvt_file("B5", "CO", "1-0", "L09", merge=True)
    assert result == "/path/to/uvt_out/L09/B5_CO_1-0_L09.uvt"


@patch("noema_combine.data_handler.uvt_dir", "/data/uvt")
def test_get_uvt_file_complex_qn():
    """Test uvt filename with complex quantum number"""
    result = get_uvt_file("B5", "N2H+", "J=1-0,F=2-1", "L09", merge=False)
    assert result == "/data/uvt/L09/B5_N2H+_J=1-0,F=2-1_L09.uvt"


# Tests for get_30m_file (deprecated, use get_sd_file instead)
@patch("noema_combine.data_handler.dir_sd", "/path/to/30m")
def test_get_30m_file_no_merge():
    """Test 30m filename generation without merge - deprecated function"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = get_30m_file("B5", "CO", "1-0", "L09", merge=False)
        assert result == "/path/to/30m/B5_CO_1-0.30m"
        # Check that deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "get_30m_file() is deprecated" in str(w[0].message)


@patch("noema_combine.data_handler.dir_sd", "/path/to/30m")
def test_get_30m_file_with_merge():
    """Test 30m filename generation with merge - deprecated function"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = get_30m_file("B5", "CO", "1-0", "L09", merge=True)
        assert result == "/path/to/30m/B5_CO_1-0_L09.30m"
        # Check that deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "get_30m_file() is deprecated" in str(w[0].message)


@patch("noema_combine.data_handler.dir_sd", "/data/30m")
def test_get_30m_file_different_molecule():
    """Test 30m filename with different molecule - deprecated function"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = get_30m_file("NGC1333", "13CO", "2-1", "L11", merge=False)
        assert result == "/data/30m/NGC1333_13CO_2-1.30m"
        # Check that deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)


# Tests for get_sd_file (new generic single-dish function)
@patch("noema_combine.data_handler.dir_sd", "/path/to/sd")
def test_get_sd_file_no_merge():
    """Test single-dish filename generation without merge"""
    result = get_sd_file("B5", "CO", "1-0", "L09", merge=False)
    assert result == "/path/to/sd/B5_CO_1-0.30m"


@patch("noema_combine.data_handler.dir_sd", "/path/to/sd")
def test_get_sd_file_with_merge():
    """Test single-dish filename generation with merge"""
    result = get_sd_file("B5", "CO", "1-0", "L09", merge=True)
    assert result == "/path/to/sd/B5_CO_1-0_L09.30m"


@patch("noema_combine.data_handler.dir_sd", "/data/sd")
def test_get_sd_file_different_molecule():
    """Test single-dish filename with different molecule"""
    result = get_sd_file("NGC1333", "13CO", "2-1", "L11", merge=False)
    assert result == "/data/sd/NGC1333_13CO_2-1.30m"


@patch("noema_combine.data_handler.get_config")
def test_refresh_config_updates_aliases(mock_get_config: MagicMock):
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

    refresh_config()

    assert dh.dir_sd == "/sd"
    assert dh.telescope_class == "APEX"
    assert dh.uvt_dir == "/uvt"


# Tests for line_reduce_30m (deprecated, use line_reduce_sd instead)
@patch("noema_combine.data_handler.line_reduce_sd")
@patch("noema_combine.data_handler.get_source_param")
def test_line_reduce_30m_deprecated(
    mock_get_source_param: MagicMock, mock_line_reduce_sd: MagicMock
):
    """Test that line_reduce_30m shows deprecation warning and calls line_reduce_sd"""
    mock_get_source_param.return_value = ("B5", "B5", "B5_out", 50.5, 30.2, 10.0)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        line_reduce_30m("B5", "CO", "1-0")

        # Check that deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "line_reduce_30m() is deprecated" in str(w[0].message)
        assert "line_reduce_sd()" in str(w[0].message)
        mock_line_reduce_sd.assert_called_once_with("B5", "CO", "1-0")


# # Tests for line_reduce_sd (new generic single-dish function)
# @patch("noema_combine.data_handler.glob")
# @patch("noema_combine.data_handler.tempfile.NamedTemporaryFile")
# @patch("noema_combine.data_handler.os.system")
# @patch("noema_combine.data_handler.get_source_param")
# @patch("noema_combine.data_handler.get_line_param")
# @patch("noema_combine.data_handler.get_sd_file")
# @patch("noema_combine.data_handler.line_name", np.array(["CO"]))
# @patch("noema_combine.data_handler.qn", np.array(["1-0"]))
# @patch("noema_combine.data_handler.Lid", np.array(["L09"]))
# @patch("noema_combine.data_handler.freq", np.array(["115.271"]))
# @patch("noema_combine.data_handler.vel_width_base_30m", np.array(["5.0"]))
# @patch("noema_combine.data_handler.vel_width_30m", np.array(["3.0"]))
# @patch("noema_combine.data_handler.name_str", np.array(["CO(1-0)"]))
# @patch("noema_combine.data_handler.telescope_class", "APEX")
# @patch("noema_combine.data_handler.inputdir", ["./input"])
# @patch("noema_combine.data_handler.file_extensions_sd", ".apex")
# def test_line_reduce_sd_basic():
#     """Test line_reduce_sd basic functionality"""
#     mock_get_source_param.return_value = ("B5", "B5", "B5_out", 50.5, 30.2, 10.0)
#     mock_get_line_param.return_value = 0
#     mock_get_sd_file.return_value = "/data/sd/B5_CO_1-0.apex"
#     mock_glob.return_value = ["./input/file1.apex", "./input/file2.apex"]
#     line_reduce_sd(source_name, line_i, qn_i)
#     mock_file = MagicMock()
#     mock_temp.return_value.__enter__.return_value = mock_file
#     mock_file.name = "temp.class"

#     # Should not raise any error
#     line_reduce_sd("B5", "CO", "1-0")

#     # Verify get_sd_file was called
#     mock_get_sd_file.assert_called()


# Tests for line_make_uvt
@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        }
    },
    clear=True,
)
@patch("noema_combine.data_handler.get_line_param")
@patch("noema_combine.data_handler.get_uvt_window")
@patch("noema_combine.data_handler.get_uvt_file")
@patch("noema_combine.data_handler.line_name", np.array(["CO"]))
@patch("noema_combine.data_handler.qn", np.array(["1-0"]))
@patch("noema_combine.data_handler.Lid", np.array(["L09"]))
@patch("noema_combine.data_handler.freq", np.array(["115.271"]))
@patch("noema_combine.data_handler.vel_width", np.array(["5.0"]))
@patch("noema_combine.data_handler.name_str", np.array(["CO(1-0)"]))
@patch("os.system")
@patch("tempfile.NamedTemporaryFile")
def test_line_make_uvt_default_parameters(
    mock_temp: MagicMock,
    mock_os: MagicMock,
    mock_get_uvt_file: MagicMock,
    mock_get_uvt_window: MagicMock,
    mock_get_line: MagicMock,
):
    """Test line_make_uvt with default parameters"""
    mock_get_line.return_value = 0
    mock_get_uvt_window.return_value = "/uvt/L09/B5_L09_uvsub.uvt"
    mock_get_uvt_file.return_value = "/uvt/L09/B5_CO_1-0_L09.uvt"
    mock_file = MagicMock()
    mock_temp.return_value.__enter__.return_value = mock_file
    mock_file.name = "temp.map"
    line_make_uvt("B5", "CO", "1-0")
    mock_get_line.assert_called_once_with("CO", "1-0")


@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        }
    },
    clear=True,
)
@patch("noema_combine.data_handler.get_line_param")
@patch("noema_combine.data_handler.get_uvt_window")
@patch("noema_combine.data_handler.get_uvt_file")
@patch("noema_combine.data_handler.line_name", np.array(["CO"]))
@patch("noema_combine.data_handler.qn", np.array(["1-0"]))
@patch("noema_combine.data_handler.Lid", np.array(["L09"]))
@patch("noema_combine.data_handler.freq", np.array(["115.271"]))
@patch("noema_combine.data_handler.vel_width", np.array(["5.0"]))
@patch("noema_combine.data_handler.name_str", np.array(["CO(1-0)"]))
@patch("os.system")
@patch("tempfile.NamedTemporaryFile")
def test_line_make_uvt_with_custom_dv(
    mock_temp: MagicMock,
    mock_os: MagicMock,
    mock_get_uvt_file: MagicMock,
    mock_get_uvt_window: MagicMock,
    mock_get_line: MagicMock,
):
    """Test line_make_uvt with custom dv parameter"""
    mock_get_line.return_value = 0
    mock_get_uvt_window.return_value = "/uvt/L09/B5_L09_uvsub.uvt"
    mock_get_uvt_file.return_value = "/uvt/L09/B5_CO_1-0_L09.uvt"
    mock_file = MagicMock()
    mock_temp.return_value.__enter__.return_value = mock_file
    mock_file.name = "temp.map"

    line_make_uvt("B5", "CO", "1-0", dv=7.0)

    # mock_get_source.assert_called_once_with("B5")
    # assert mock_file.write.called


@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        }
    },
    clear=True,
)
@patch("noema_combine.data_handler.get_line_param")
@patch("noema_combine.data_handler.get_uvt_window")
@patch("noema_combine.data_handler.get_uvt_file")
@patch("noema_combine.data_handler.line_name", np.array(["CO"]))
@patch("noema_combine.data_handler.qn", np.array(["1-0"]))
@patch("noema_combine.data_handler.Lid", np.array(["L09"]))
@patch("noema_combine.data_handler.freq", np.array(["115.271"]))
@patch("noema_combine.data_handler.vel_width", np.array(["5.0"]))
@patch("noema_combine.data_handler.name_str", np.array(["CO(1-0)"]))
@patch("os.system")
@patch("tempfile.NamedTemporaryFile")
def test_line_make_uvt_with_dv_min_max(
    mock_temp: MagicMock,
    mock_os: MagicMock,
    mock_get_uvt_file: MagicMock,
    mock_get_uvt_window: MagicMock,
    mock_get_line: MagicMock,
):
    """Test line_make_uvt with dv_min and dv_max parameters"""
    mock_get_line.return_value = 0
    mock_get_uvt_window.return_value = "/uvt/L09/B5_L09_uvsub.uvt"
    mock_get_uvt_file.return_value = "/uvt/L09/B5_CO_1-0_L09.uvt"
    mock_file = MagicMock()
    mock_temp.return_value.__enter__.return_value = mock_file
    mock_file.name = "temp.map"

    line_make_uvt("B5", "CO", "1-0", dv_min=3.0, dv_max=8.0)

    # assert mock_file.write.called


@patch.dict(
    "noema_combine.data_handler.region_catalogue",
    {
        "B5": {
            "source_sd": "b5",
            "source_out": "B5_out",
            "RA0": "50.5",
            "Dec0": "30.2",
            "Vlsr": "10.0",
        }
    },
    clear=True,
)
@patch("noema_combine.data_handler.get_line_param")
@patch("noema_combine.data_handler.get_uvt_window")
@patch("noema_combine.data_handler.get_uvt_file")
@patch("noema_combine.data_handler.line_name", np.array(["CO"]))
@patch("noema_combine.data_handler.qn", np.array(["1-0"]))
@patch("noema_combine.data_handler.Lid", np.array(["L09"]))
@patch("noema_combine.data_handler.freq", np.array(["115.271"]))
@patch("noema_combine.data_handler.vel_width", np.array(["5.0"]))
@patch("noema_combine.data_handler.name_str", np.array(["CO(1-0)"]))
@patch("os.system")
@patch("tempfile.NamedTemporaryFile")
def test_line_make_uvt_with_selfcal(
    mock_temp: MagicMock,
    mock_os: MagicMock,
    mock_get_uvt_file: MagicMock,
    mock_get_uvt_window: MagicMock,
    mock_get_line: MagicMock,
):
    """Test line_make_uvt with selfcal enabled"""
    mock_get_line.return_value = 0
    mock_get_uvt_window.return_value = "/uvt/L09/B5_L09_uvsub_sc.uvt"
    mock_get_uvt_file.return_value = "/uvt/L09/B5_CO_1-0_L09.uvt"
    mock_file = MagicMock()
    mock_temp.return_value.__enter__.return_value = mock_file
    mock_file.name = "temp.map"

    line_make_uvt("B5", "CO", "1-0", selfcal=True)

    mock_get_uvt_window.assert_called_once_with(
        "B5_out", "L09", uvsub=True, selfcal=True
    )
