from pathlib import Path

import pytest

from noema_combine.merge import build_uv_merge_init, build_uv_merge_script
from noema_combine.uvfits import build_uvfits_export_script
from noema_combine.project import create_project_files
from noema_combine.workflows.merge import merge_uv_tables
from noema_combine.workflows.uvfits import export_uvfits


def test_uv_merge_scripts_define_inputs_and_output():
    init = build_uv_merge_init("a.uvt", "b.uvt", "merged.uvt")
    assert 'TABLE_IN$ "a.uvt"' in init
    assert 'TABLE_REF$ "b.uvt"' in init
    assert 'TABLE_OUT$ "merged.uvt"' in init
    assert "run uv_merge uv_merge.init /nowindow" in build_uv_merge_script()


def test_uvfits_export_script_quotes_paths():
    script = build_uvfits_export_script("input.uvt", "output.uvfits")
    assert 'fits "output.uvfits" from "input.uvt" /style CASA_UVFITS /overwrite' in script


def _project(tmp_path: Path) -> Path:
    config, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    return config


def test_merge_workflow_generates_script_only_without_input_data(tmp_path: Path):
    result = merge_uv_tables(
        "B5", baseband="li", products="wideband_contsub",
        execute=False, config_file=str(_project(tmp_path)),
    )[0]

    assert result.product_type == "wideband_contsub"
    assert result.input_file_a.name.endswith("_A_li_contsub_sc.uvt")
    assert result.input_file_b.name.endswith("_CD_li_contsub_sc.uvt")
    assert result.output_file.name.endswith("_ACD_li_contsub_sc.uvt")
    assert result.script_path.is_file()
    assert result.init_path.is_file()
    assert "run uv_merge uv_merge.init /nowindow" in result.script_path.read_text()


def test_merge_workflow_rejects_unknown_product(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown merge product"):
        merge_uv_tables(
            "B5", products="unsupported", execute=False,
            config_file=str(_project(tmp_path)),
        )


def test_uvfits_workflow_generates_selected_window_script_only(tmp_path: Path):
    result = export_uvfits(
        "B5", "CD", windows="l034l073", execute=False,
        config_file=str(_project(tmp_path)),
    )[0]

    assert result.window == "l034l073"
    assert result.input_file.name.endswith("_l034l073_sc_contsub.uvt")
    assert result.output_file.suffix == ".uvfits"
    assert result.script_path.is_file()
    assert "CASA_UVFITS" in result.script_path.read_text()


def test_uvfits_workflow_rejects_unknown_window(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown narrowband window"):
        export_uvfits(
            "B5", "CD", windows="l999l999", execute=False,
            config_file=str(_project(tmp_path)),
        )
