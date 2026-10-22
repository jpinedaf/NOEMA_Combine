import pytest
from io import StringIO
from typing import Dict
from datetime import datetime

from noema_combine.generate_uvt import (
    make_header,
    make_uvt_names,
    print_makespw,
    calibration_type,
    look_spw,
    # prepare_config,  # TODO
    # process_source,  # TODO
)


# Tests for make_header
def test_make_header_output():
    """Test that header is correctly written"""
    mock_file = StringIO()

    make_header(mock_file)

    output = mock_file.getvalue()
    assert "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" in output
    assert "Generate LR + HR chunk UVT files" in output
    assert "Created for MIOP L19MB project" in output
    assert "def integer new_file /global" in output
    assert "let new_file 1" in output


def test_make_header_contains_date():
    """Test that header contains current date"""
    mock_file = StringIO()

    make_header(mock_file)

    output = mock_file.getvalue()
    current_date = datetime.today().strftime("%Y-%m-%d")
    assert current_date in output


def test_make_header_format():
    """Test that header has correct format markers"""
    mock_file = StringIO()

    make_header(mock_file)

    output = mock_file.getvalue()
    assert output.count("!") > 10
    assert "generate_miop_uvt" in output


def test_make_header_returns_none():
    """Test that make_header returns None"""
    mock_file = StringIO()
    result = make_header(mock_file)
    assert result is None


# Tests for make_uvt_names
def test_make_uvt_names_valid_input():
    """Test generating UVT names with valid input"""
    sources = ["SOURCE1", "SOURCE2"]
    config = "C"

    result = make_uvt_names(sources, config)

    assert len(result) == 2
    assert "../../uvts/SOURCE1/Cconfig/SOURCE1_C" == result[0]
    assert "../../uvts/SOURCE2/Cconfig/SOURCE2_C" == result[1]


def test_make_uvt_names_different_config():
    """Test generating UVT names with different config"""
    sources = ["SRC1", "SRC2"]
    config = "D"

    result = make_uvt_names(sources, config)

    assert "Dconfig" in result[0]
    assert "SRC1_D" in result[0]
    assert "Dconfig" in result[1]
    assert "SRC2_D" in result[1]


def test_make_uvt_names_wrong_number_of_sources():
    """Test that ValueError is raised with wrong number of sources"""
    sources = ["SOURCE1"]
    config = "C"

    with pytest.raises(ValueError, match="exactly two elements"):
        make_uvt_names(sources, config)


def test_make_uvt_names_too_many_sources():
    """Test that ValueError is raised with too many sources"""
    sources = ["SOURCE1", "SOURCE2", "SOURCE3"]
    config = "C"

    with pytest.raises(ValueError, match="exactly two elements"):
        make_uvt_names(sources, config)


def test_make_uvt_names_path_structure():
    """Test that path structure is correct"""
    sources = ["TEST1", "TEST2"]
    config = "A"

    result = make_uvt_names(sources, config)

    assert result[0].startswith("../../uvts/")
    assert "/Aconfig/" in result[0]
    assert result[1].startswith("../../uvts/")
    assert "/Aconfig/" in result[1]


def test_make_uvt_names_empty_list():
    """Test with empty source list"""
    sources: list[str] = []
    config = "C"

    with pytest.raises(ValueError):
        make_uvt_names(sources, config)


# Tests for print_makespw
def test_print_makespw_output():
    """Test that makespw procedure is correctly written"""
    mock_file = StringIO()
    sources = ["SOURCE1", "SOURCE2"]
    uvt_out = ["path/to/source1", "path/to/source2"]

    print_makespw(mock_file, uvt_out, sources)

    output = mock_file.getvalue()
    assert "begin procedure makespw" in output
    assert "end procedure makespw" in output
    assert "SOURCE1" in output
    assert "SOURCE2" in output


def test_print_makespw_contains_both_sources():
    """Test that both sources are referenced in output"""
    mock_file = StringIO()
    sources = ["SRC1", "SRC2"]
    uvt_out = ["out1", "out2"]

    print_makespw(mock_file, uvt_out, sources)

    output = mock_file.getvalue()
    assert "find /proc corr /sou SRC1" in output
    assert "find /proc corr /sou SRC2" in output


def test_print_makespw_contains_conditional_logic():
    """Test that conditional logic for new_file is present"""
    mock_file = StringIO()
    sources = ["SOURCE1", "SOURCE2"]
    uvt_out = ["out1", "out2"]

    print_makespw(mock_file, uvt_out, sources)

    output = mock_file.getvalue()
    assert "if (new_file.eq.1) then" in output
    assert "else" in output
    assert "endif" in output


def test_print_makespw_wrong_number_sources():
    """Test error handling with wrong number of sources"""
    mock_file = StringIO()
    sources = ["SOURCE1"]
    uvt_out = ["out1"]

    with pytest.raises(ValueError, match="exactly two elements"):
        print_makespw(mock_file, uvt_out, sources)


def test_print_makespw_table_commands():
    """Test that table commands are present"""
    mock_file = StringIO()
    sources = ["SOURCE1", "SOURCE2"]
    uvt_out = ["uvt1", "uvt2"]

    print_makespw(mock_file, uvt_out, sources)

    output = mock_file.getvalue()
    assert 'table "uvt1_&1" new' in output
    assert 'table "uvt2_&1" new' in output


def test_print_makespw_returns_none():
    """Test that print_makespw returns None"""
    mock_file = StringIO()
    sources = ["SOURCE1", "SOURCE2"]
    uvt_out = ["out1", "out2"]

    result = print_makespw(mock_file, uvt_out, sources)
    assert result is None


# Tests for calibration_type
def test_calibration_type_basic():
    """Test basic calibration type output"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="1mm",
        file_name="test.30m",
        phase_cal="antenna",
        amp_cal="antenna",
        RF_cal="antenna",
    )

    output = mock_file.getvalue()
    assert "set receiver 1mm" in output
    assert 'file in "test.30m"' in output
    assert "set default" in output


def test_calibration_type_all_settings():
    """Test that all settings are written"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="3mm",
        file_name="data.fits",
        phase_cal="sky",
        amp_cal="sky",
        RF_cal="sky",
    )

    output = mock_file.getvalue()
    assert "set scan 0 10000" in output
    assert "set offset 0 0" in output
    assert "set quality average" in output
    assert "set weight tsys on" in output
    assert "set weight calibration on" in output
    assert "set drop 0.00000001 0.00000001" in output


def test_calibration_type_antenna_phase():
    """Test antenna phase calibration"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="2mm",
        file_name="test.30m",
        phase_cal="antenna",
        amp_cal="antenna",
        RF_cal="antenna",
    )

    output = mock_file.getvalue()
    assert "set phase antenna atmospher internal relative" in output


def test_calibration_type_baseline_phase(capsys: pytest.CaptureFixture[str]):
    """Test baseline phase calibration (not available)"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="1mm",
        file_name="data.30m",
        phase_cal="baseline",
        amp_cal="antenna",
        RF_cal="antenna",
    )

    captured = capsys.readouterr()
    assert "Phase calibration requested as baseline" in captured.out


def test_calibration_type_antenna_amplitude():
    """Test antenna amplitude calibration"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="1mm",
        file_name="test.30m",
        phase_cal="antenna",
        amp_cal="antenna",
        RF_cal="antenna",
    )

    output = mock_file.getvalue()
    assert "set amplitude antenna absolute jansky relative" in output


def test_calibration_type_baseline_amplitude():
    """Test baseline amplitude calibration"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="1mm",
        file_name="test.30m",
        phase_cal="antenna",
        amp_cal="baseline",
        RF_cal="antenna",
    )

    output = mock_file.getvalue()
    assert "set amplitude baseline relative" in output


def test_calibration_type_rf_baseline():
    """Test RF baseline calibration"""
    mock_file = StringIO()

    calibration_type(
        mock_file,
        receiver="1mm",
        file_name="test.30m",
        phase_cal="antenna",
        amp_cal="antenna",
        RF_cal="baseline",
    )

    output = mock_file.getvalue()
    assert "set rf baseline on" in output


def test_calibration_type_returns_none():
    """Test that calibration_type returns None"""
    mock_file = StringIO()
    result = calibration_type(
        mock_file, "1mm", "test.30m", "antenna", "antenna", "antenna"
    )
    assert result is None


# Tests for look_spw
def test_look_spw_default_parameters():
    """Test look_spw with default parameters"""
    mock_file = StringIO()
    high_res_params: Dict[str, int] = {}

    look_spw(mock_file, high_res_params)

    output = mock_file.getvalue()
    assert "begin procedure loopspw" in output
    assert "end procedure loopspw" in output
    assert "set selection line lsb l001 and l005" in output
    assert "@ makespw lo" in output


def test_look_spw_custom_parameters():
    """Test look_spw with custom parameters"""
    mock_file = StringIO()
    high_res_params = {
        "number_windows": 40,
        "LI_start": 25,
        "UI_start": 35,
        "UO_start": 42,
    }

    look_spw(mock_file, high_res_params)

    output = mock_file.getvalue()
    assert "begin procedure loopspw" in output
    assert len(output) > 0


def test_look_spw_contains_all_bands():
    """Test that all bands (lo, li, ui, uo) are present"""
    mock_file = StringIO()
    high_res_params: Dict[str, int] = {}

    look_spw(mock_file, high_res_params)

    output = mock_file.getvalue()
    assert "@ makespw lo" in output
    assert "@ makespw li" in output
    assert "@ makespw ui" in output
    assert "@ makespw uo" in output


def test_look_spw_wideband_chunks():
    """Test that wideband chunks are defined"""
    mock_file = StringIO()
    high_res_params: Dict[str, int] = {}

    look_spw(mock_file, high_res_params)

    output = mock_file.getvalue()
    assert "Wideband chunks" in output
    assert "LO chunks" in output


def test_look_spw_chunk_transitions():
    """Test that chunk transitions are marked"""
    mock_file = StringIO()
    high_res_params = {
        "number_windows": 38,
        "LI_start": 23,
        "UI_start": 32,
        "UO_start": 40,
    }

    look_spw(mock_file, high_res_params)

    output = mock_file.getvalue()
    assert "LI chunks" in output
    assert "UI chunks" in output
    assert "UO chunks" in output


def test_look_spw_sideband_switch():
    """Test that sideband switches from lsb to usb"""
    mock_file = StringIO()
    high_res_params = {"number_windows": 38, "UI_start": 32}

    look_spw(mock_file, high_res_params)

    output = mock_file.getvalue()
    assert "lsb" in output
    assert "usb" in output


def test_look_spw_returns_none():
    """Test that look_spw returns None"""
    mock_file = StringIO()
    result = look_spw(mock_file, {})
    assert result is None


# Integration tests
def test_full_workflow():
    """Test complete workflow from make_header to look_spw"""
    output = StringIO()

    # Generate header
    make_header(output)

    # Generate UVT names
    sources = ["SOURCE1", "SOURCE2"]
    uvt_names = make_uvt_names(sources, "C")

    # Print makespw
    print_makespw(output, uvt_names, sources)

    # Add calibration
    calibration_type(
        output,
        receiver="1mm",
        file_name="test.30m",
        phase_cal="antenna",
        amp_cal="antenna",
        RF_cal="antenna",
    )

    # Add look_spw
    look_spw(output, {})

    result = output.getvalue()
    assert len(result) > 0
    assert "begin procedure makespw" in result
    assert "set receiver 1mm" in result
    assert "begin procedure loopspw" in result


def test_uvt_names_consistency():
    """Test that UVT names are consistent across calls"""
    sources = ["SRC1", "SRC2"]
    config = "C"

    result1 = make_uvt_names(sources, config)
    result2 = make_uvt_names(sources, config)

    assert result1 == result2


def test_multiple_configs_workflow():
    """Test workflow with multiple configurations"""
    configs = ["A", "C", "D"]
    sources = ["SRC1", "SRC2"]

    results: list[list[str]] = []
    for config in configs:
        uvt_names: list[str] = make_uvt_names(sources, config)
        results.append(uvt_names)

    # Each config should produce different paths
    assert len(set([tuple(r) for r in results])) == len(configs)
