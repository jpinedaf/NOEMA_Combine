from noema_combine import lines_in_window


HEADER = (
    "#name,QN(filename),freq(GHz),mol(plot),QN(plot),Aul(logs^-1),Eul(K),"
    "cat,NOEMAbb,unit,width(km/s),30msetup,30mbb,30mwidth(km/s),30mline(km/s)\n"
)


def _write_config(tmp_path):
    catalogue = tmp_path / "lines.csv"
    catalogue.write_text(
        HEADER
        + "LOW,1_0,100.0,LOW,1-0,-4,5,CDMS,lo,L010,10,Setup,LO,20,5\n"
        + "MID,1_0,200.0,MID,1-0,-4,5,CDMS,li,L020,10,Setup,LI,20,5\n"
        + "HIGH,1_0,300.0,HIGH,1-0,-4,5,CDMS,uo,L040,10,Setup,UO,20,5\n"
    )
    config = tmp_path / "config.ini"
    config.write_text(
        "[catalogues]\n"
        f"line_catalogue = {catalogue.name}\n"
        "source_catalogue = region_catalogue.yml\n"
        "\n[spectral_windows]\n"
        "narrowband_start = l009\n"
        "narrowband_end = l047\n"
        "lo_start = l009\n"
        "li_start = l020\n"
        "ui_start = l032\n"
        "uo_start = l040\n"
    )
    return config


def test_lines_in_window_uses_configured_broadband_boundaries(tmp_path):
    config = _write_config(tmp_path)

    lines = lines_in_window("li", config_file=str(config))

    assert [line["line"] for line in lines] == ["MID"]
    assert lines[0]["window"] == "li"


def test_lines_in_window_normalizes_narrowband_identifiers(tmp_path):
    config = _write_config(tmp_path)

    lines = lines_in_window("L010L049", config_file=str(config))

    assert [line["line"] for line in lines] == ["LOW", "MID", "HIGH"]
    assert lines[0]["narrowband_window"] == "l010l049"


def test_lines_in_window_includes_catalogue_rows_tagged_by_broadband(tmp_path):
    config = _write_config(tmp_path)
    catalogue = tmp_path / "lines.csv"
    catalogue.write_text(
        catalogue.read_text()
        + "BROAD,1_0,350.0,BROAD,1-0,-4,5,CDMS,uo,uo,10,Setup,UO,20,5\n"
    )

    lines = lines_in_window("uo", config_file=str(config))

    assert [line["line"] for line in lines] == ["HIGH", "BROAD"]
