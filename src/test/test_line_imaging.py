from pathlib import Path

from noema_combine import make_line_images
from noema_combine.imaging import build_clean_image_script


HEADER = (
    "#name,QN(filename),freq(GHz),mol(plot),QN(plot),Aul(logs^-1),Eul(K),"
    "cat,NOEMAbb,unit,width(km/s),30msetup,30mbb,30mwidth(km/s),30mline(km/s)\n"
)


def _config(tmp_path: Path) -> Path:
    (tmp_path / "lines.csv").write_text(
        HEADER
        + "N2D+,3_2,231.3218283,N\\d2D\\u+,3-2,-2,22,CDMS,ui,l034l073,10,Setup,UI,20,5\n"
    )
    config = tmp_path / "config.ini"
    config.write_text(
        "[catalogues]\n"
        "line_catalogue = lines.csv\n"
        "source_catalogue = region_catalogue.yml\n"
        "\n[spectral_windows]\n"
        "narrowband_start = l009\n"
        "narrowband_end = l047\n"
        "lo_start = l009\n"
        "li_start = l023\n"
        "ui_start = l032\n"
        "uo_start = l040\n"
    )
    return config


def test_make_line_images_generates_narrowband_dirty_and_clean_scripts(tmp_path):
    result = make_line_images(
        "B5-IRS1",
        "CD",
        "N2D+",
        "3-2",
        "l034l073",
        execute=False,
        config_file=str(_config(tmp_path)),
    )

    assert result.window == "l034l073"
    assert result.input_file.as_posix().endswith(
        "/CD/l34l73/B5-IRS1_CD_N2D+_3_2_l034l073.uvt"
    )
    assert result.dirty_map is not None
    assert result.clean_cube is not None
    assert result.dirty_script is not None and result.dirty_script.is_file()
    assert result.clean_script is not None and result.clean_script.is_file()
    assert 'let H%line N\\d2D\\u+' in result.clean_script.read_text()


def test_make_line_images_can_generate_only_clean_products(tmp_path):
    result = make_line_images(
        "B5-IRS1",
        "CD",
        "N2D+",
        "3-2",
        "l034",
        dirty=False,
        clean=True,
        method="SDI",
        execute=False,
        config_file=str(_config(tmp_path)),
    )

    assert result.dirty_map is None
    assert result.dirty_script is None
    assert result.clean_cube is not None
    assert len(result.executions) == 1
    assert "let method SDI\nlet MYCLEAN%SUPPORT NO\ngo clean" in result.clean_script.read_text()


def test_clean_builder_emits_explicit_method():
    hogbom = build_clean_image_script(
        "/data/input.uvt", "/data/output", baseband="ui", configuration="CD"
    )
    sdi = build_clean_image_script(
        "/data/input.uvt",
        "/data/output",
        baseband="ui",
        configuration="CD",
        method="sdi",
    )

    assert "let method HOGBOM\nlet MYCLEAN%SUPPORT NO\ngo clean" in hogbom
    assert "let method SDI\nlet MYCLEAN%SUPPORT NO\ngo clean" in sdi


def test_clean_builder_uses_support_mask_settings():
    masked = build_clean_image_script(
        "/data/input.uvt",
        "/data/output",
        baseband="l034l073",
        configuration="CD",
        threshold_factor=2.0,
        support_mask=True,
    )
    unmasked = build_clean_image_script(
        "/data/input.uvt",
        "/data/output",
        baseband="l034l073",
        configuration="CD",
        threshold_factor=3.0,
        support_mask=False,
    )

    assert "let ares 2.0*'H%noise'" in masked
    assert "let MYCLEAN%SUPPORT YES\ngo clean" in masked
    assert "let ares 3.0*'H%noise'" in unmasked
    assert "let MYCLEAN%SUPPORT NO\ngo clean" in unmasked


def test_clean_builder_rejects_unknown_method():
    import pytest

    with pytest.raises(ValueError, match="method must be 'HOGBOM' or 'SDI'"):
        build_clean_image_script(
            "/data/input.uvt",
            "/data/output",
            baseband="ui",
            configuration="CD",
            method="clark",
        )
