from pathlib import Path

from noema_combine.config import Config
from noema_combine.masking import copy_support_masks
from noema_combine.project import create_project_files
from noema_combine.selfcal import build_selfcal_init, build_selfcal_script


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
    source_out = cfg.region_catalogue["B5"].get("source_out", "B5")
    source = Path(cfg.naming.render(
        "support_mask", source="B5", source_out=source_out, config="CD", window="li"
    ))
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("mask")

    copies = copy_support_masks(
        "B5", "CD", "li", "lo", config_file=str(config_path)
    )

    assert len(copies) == 6
    assert (source.parent / "B5_CD_lo_cont_rob1.msk").read_text() == "mask"
    assert all(copy.destination.exists() for copy in copies)
