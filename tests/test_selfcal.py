from pathlib import Path

import pytest

from noema_combine.config import Config
from noema_combine.masking import copy_support_masks
from noema_combine.project import create_project_files
from noema_combine.selfcal import build_selfcal_init, build_selfcal_script
from noema_combine.workflows.selfcal import apply_selfcal_solutions


def test_selfcal_script_and_init_use_uv_cal():
    init = build_selfcal_init(
        "/data/input.uvt",
        "/data/gain.uvt",
        "/data/output.uvt",
        flag_uncalibrated=False,
    )
    script = build_selfcal_script()

    assert 'UVDATA$ "/data/input.uvt"' in init
    assert 'UVGAIN$ "/data/gain.uvt"' in init
    assert "FLAG$  NO" in init
    assert "run uv_cal /nowindow" in script


def test_copy_support_masks_copies_standard_and_selfcal_variants(tmp_path: Path):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    cfg = Config(config_file=str(config_path), isolated=True)
    source_out = cfg.region_catalogue["B5-IRS1"].get("source_out", "B5-IRS1")
    source = Path(
        cfg.naming.render(
            "support_mask",
            source="B5-IRS1",
            source_out=source_out,
            config="CD",
            window="li",
        )
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("mask")

    copies = copy_support_masks(
        "B5-IRS1", "CD", "li", "lo", config_file=str(config_path)
    )

    assert len(copies) == 6
    assert (source.parent / "B5-IRS1_CD_lo_cont_rob1.msk").read_text() == "mask"
    assert all(copy.destination.exists() for copy in copies)


def test_selfcal_workflow_generates_wideband_and_narrowband_scripts_without_data(
    tmp_path: Path,
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )

    results = apply_selfcal_solutions(
        "B5-IRS1",
        "CD",
        basebands=["ui"],
        windows=["l034l073"],
        execute=False,
        config_file=str(config_path),
    )

    assert [result.window_kind for result in results] == ["wideband", "narrowband"]
    assert results[0].output_file.name.endswith("_ui_contsub_sc.uvt")
    assert results[1].output_file.name.endswith("_l034l073_sc.uvt")
    assert all(result.script_path.is_file() for result in results)
    assert all(result.init_path.is_file() for result in results)


def test_selfcal_workflow_rejects_window_outside_selected_baseband(tmp_path: Path):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )

    with pytest.raises(ValueError, match="not covered"):
        apply_selfcal_solutions(
            "B5",
            "CD",
            basebands=["li"],
            windows=["l009l048"],
            execute=False,
            config_file=str(config_path),
        )


def test_copy_support_masks_honors_overwrite_flag(tmp_path: Path):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    cfg = Config(config_file=str(config_path), isolated=True)
    source_out = cfg.region_catalogue["B5-IRS1"].get("source_out", "B5-IRS1")
    source = Path(
        cfg.naming.render(
            "support_mask",
            source="B5-IRS1",
            source_out=source_out,
            config="CD",
            window="li",
        )
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("new")
    destination = source.parent / "B5-IRS1_CD_lo_cont_rob1.msk"
    destination.write_text("old")

    with pytest.raises(FileExistsError):
        copy_support_masks(
            "B5-IRS1",
            "CD",
            "li",
            "lo",
            include_selfcal=False,
            config_file=str(config_path),
        )
    copy_support_masks(
        "B5-IRS1",
        "CD",
        "li",
        "lo",
        include_selfcal=False,
        overwrite=True,
        config_file=str(config_path),
    )
    assert destination.read_text() == "new"
