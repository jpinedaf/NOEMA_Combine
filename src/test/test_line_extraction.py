from pathlib import Path

import pytest

from noema_combine import build_line_extraction_script, extract_line


HEADER = (
    "#name,QN(filename),freq(GHz),mol(plot),QN(plot),Aul(logs^-1),Eul(K),"
    "cat,NOEMAbb,unit,width(km/s),30msetup,30mbb,30mwidth(km/s),30mline(km/s)\n"
)


def _config(tmp_path: Path) -> Path:
    (tmp_path / "lines.csv").write_text(
        HEADER
        + "N2D+,3_2,231.3218283,N2D+,3-2,-2,22,CDMS,ui,l034l073,10,Setup,UI,20,5\n"
        + "CO,1_0,230.538,CO,1-0,-4,5,CDMS,ui,L040,10,Setup,UI,20,5\n"
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


def test_build_line_extraction_script_uses_frequency_and_velocity_range():
    script = build_line_extraction_script(
        "/data/input.uvt",
        "/data/output.uvt",
        line_name=r"N\d2D\u+",
        rest_frequency_mhz=231321.8283,
        velocity_range=(4.0, 14.0),
    )

    assert 'modify "/data/input.uvt" /frequency N\\d2D\\u+ 231322' in script
    assert "uv_extract /range 4.00 14.00 velocity" in script
    assert 'write uv "/data/output.uvt" new' in script


def test_extract_line_supports_pair_window_and_dv(tmp_path):
    result = extract_line(
        "B5-IRS1",
        "CD",
        "N2D+",
        "3-2",
        "l034",
        dv=5.0,
        execute=False,
        config_file=str(_config(tmp_path)),
    )

    assert result.window == "l034l073"
    assert result.velocity_range == (4.0, 14.0)
    assert result.rest_frequency_mhz == pytest.approx(231.3218283 * 1000)
    assert result.output_file.name == "B5-IRS1_CD_N2D+_3_2_l034l073.uvt"
    assert result.script_path.is_file()


def test_extract_line_supports_broadband_window(tmp_path):
    result = extract_line(
        "B5-IRS1",
        "CD",
        "CO",
        "1-0",
        "uo",
        execute=False,
        config_file=str(_config(tmp_path)),
    )

    assert result.window == "uo"
    assert result.input_file.as_posix().endswith("/CD/wideband/B5-IRS1_CD_uo.uvt")


def test_extract_line_rejects_line_outside_window(tmp_path):
    with pytest.raises(ValueError, match="not covered"):
        extract_line(
            "B5-IRS1",
            "CD",
            "N2D+",
            "3-2",
            "lo",
            execute=False,
            config_file=str(_config(tmp_path)),
        )
