import os
import subprocess
import sys
from configparser import ConfigParser
from pathlib import Path
from subprocess import CompletedProcess

import pytest

import noema_combine.data_handler as data_handler
import noema_combine.project as project_module
from noema_combine import (
    create_config,
    create_line_catalogue,
    create_project_files,
    create_region_catalogue,
)
from noema_combine.config import Config, get_config, reload_config
from noema_combine.continuum import (
    baseline_command,
    build_continuum_subtraction_script,
    resolve_channel_range,
)
from noema_combine.naming import FileNaming, preview_naming
from noema_combine.workflows import (
    make_clean_images,
    make_continuum_subtraction,
    make_dirty_images,
    make_merged_line_images,
    make_narrowband_continuum_subtraction,
    restore_image,
)


def test_default_naming_matches_package_paths():
    naming = FileNaming()

    assert naming.uvt_file("B5", "CO", "1-0", "L09") == "D/L09/B5_CO_1-0_L09.uvt"
    assert naming.uvt_window("B5", "L09") == "D/L09/B5_L09_contsub.uvt"
    assert naming.sd_file("B5", "CO", "1-0", "L09") == "30m/B5_CO_1-0.30m"


@pytest.mark.parametrize(
    "name", ["sd_file_merge", "merged_line_uvt", "merged_line_single_dish"]
)
def test_merge_naming_warns_for_independent_templates(name: str):
    with pytest.warns(UserWarning, match="customize 'uvt_file_merge'"):
        naming = FileNaming({name: "{root}/different"})
    assert naming.describe()[name] != "{root}/different"


@pytest.mark.parametrize("style", ["prodige", "propstar"])
@pytest.mark.parametrize(
    "selfcal,contsub", [("", ""), ("_sc", ""), ("", "_contsub"), ("_sc", "_contsub")]
)
def test_merge_products_share_uvt_basename(
    tmp_path: Path, style: str, selfcal: str, contsub: str
):
    config_path, _ = create_project_files(
        style,
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    cfg = Config(config_file=str(config_path), isolated=True)
    values = {
        "source": "B5",
        "source_out": "B5-IRS1",
        "line": "N2D+",
        "qn": "3_2",
        "lid": "l034l073",
        "config": "CD",
        "selfcal": selfcal,
        "contsub": contsub,
        "merge_uvt_base": "/ignored/unrelated",
    }

    sd = Path(cfg.naming.render("sd_file_merge", **values))
    uvt = Path(cfg.naming.render("merged_line_uvt", **values))
    table = Path(cfg.naming.render("merged_line_single_dish", **values))
    assert sd.with_suffix("") == uvt.with_suffix("") == table.with_suffix("")
    assert (sd.suffix, uvt.suffix, table.suffix) == (".30m", ".uvt", ".tab")
    assert uvt.name == f"B5-IRS1_N2D+_3_2_l034l073{selfcal}{contsub}.uvt"


@pytest.mark.parametrize(
    "style, folder",
    [("prodige", "l34l73"), ("propstar", "l034l073")],
)
def test_generated_profile_line_uvt_pair_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, style: str, folder: str
):
    config_path, _ = create_project_files(
        style,
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.setattr(data_handler, "_cfg", cfg)

    for merge, root in [(False, cfg.uvt_dir), (True, cfg.uvt_dir_out)]:
        actual = data_handler.get_uvt_file(
            "B5-IRS1", "N2D+", "3_2", "l034l073", merge=merge
        )
        assert Path(actual) == Path(root) / folder / "B5-IRS1_N2D+_3_2_l034l073.uvt"

    assert Path(data_handler.get_uvt_file("B5", "CO", "1-0", "L09")) == (
        Path(cfg.uvt_dir) / "L09" / "B5_CO_1-0_L09.uvt"
    )


def test_prodige_line_uvt_explicit_template_is_respected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    with config_path.open("a") as config:
        config.write("uvt_file = {uvt_root}/custom/{lid}/{source}.uvt\n")
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.setattr(data_handler, "_cfg", cfg)

    assert Path(data_handler.get_uvt_file("B5", "CO", "1-0", "l034l073")) == (
        Path(cfg.uvt_dir) / "custom/l034l073/B5.uvt"
    )


def test_prodige_line_uvt_custom_template_uses_configured_suffixes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    with config_path.open("a") as config:
        config.write(
            "uvt_file = {uvt_root}/custom/{source}{selfcal}{uvsub}.uvt\n"
        )
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.setattr(data_handler, "_cfg", cfg)
    monkeypatch.setattr(data_handler, "selfcal_ext", "_self")
    monkeypatch.setattr(data_handler, "uvsub_ext", "_sub")

    assert Path(
        data_handler.get_uvt_file(
            "B5", "CO", "1-0", "l034l073", selfcal=True, contsub=True
        )
    ) == Path(cfg.uvt_dir) / "custom/B5_self_sub.uvt"


def test_merge_single_dish_uses_custom_uvt_template_and_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    with config_path.open("a") as config:
        config.write(
            "uvt_file_merge = {uvt_out_root}/custom/{source}{selfcal}{contsub}.uvt\n"
        )
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.setattr(data_handler, "_cfg", cfg)
    monkeypatch.setattr(data_handler, "file_extensions_sd", ".apex")
    monkeypatch.setattr(data_handler, "selfcal_ext", "_self")
    monkeypatch.setattr(data_handler, "uvsub_ext", "_sub")

    expected = Path(cfg.uvt_dir_out) / "custom/B5_self_sub.apex"
    assert Path(data_handler.get_sd_file(
        "B5", "CO", "1-0", "l034l073", merge=True, selfcal=True, contsub=True
    )) == expected
    assert Path(cfg.naming.sd_file(
        "B5", "CO", "1-0", "l034l073", merge=True,
        selfcal="_self", contsub="_sub", sd_ext=".apex",
    )) == expected
    values = {
        "source": "B5", "source_out": "B5", "line": "CO", "qn": "1-0",
        "lid": "l034l073", "selfcal": "_self", "contsub": "_sub",
    }
    assert Path(cfg.naming.render("merged_line_uvt", **values)) == expected.with_suffix(".uvt")
    assert Path(cfg.naming.render("merged_line_single_dish", **values)) == expected.with_suffix(".tab")


def test_prodige_pair_folder_without_naming_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    parser = ConfigParser()
    parser.read(config_path)
    parser.remove_section("naming")
    with config_path.open("w") as config:
        parser.write(config)
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.setattr(data_handler, "_cfg", cfg)

    assert Path(data_handler.get_uvt_file("B5", "CO", "1-0", "l034l073")) == (
        Path(cfg.uvt_dir) / "l34l73/B5_CO_1-0_l034l073.uvt"
    )


@pytest.mark.parametrize(
    "selfcal, contsub, suffix",
    [(False, False, ""), (True, False, "_sc"), (False, True, "_contsub"),
     (True, True, "_sc_contsub")],
)
def test_prodige_line_prepare_merge_uses_pair_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    selfcal: bool, contsub: bool, suffix: str,
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(data_handler, "_cfg", cfg)
    for name in (
        "region_catalogue", "line_name", "qn", "qn_str",
        "freq_mhz", "Lid", "name_str", "selfcal_ext", "uvsub_ext",
    ):
        monkeypatch.setattr(data_handler, name, getattr(cfg, name))

    result = data_handler.line_prepare_merge(
        "B5-IRS1", "N2D+", "3-2", execute=False, selfcal=selfcal, contsub=contsub
    )
    script = result.script_path.read_text()

    basename = f"B5-IRS1_N2D+_3_2_l034l073{suffix}"
    assert f'/like "{tmp_path / "CD/l34l73" / (basename + ".uvt")}"' in script
    assert f'table "{tmp_path / "CD30m/l34l73" / basename}"' in script
    assert f'file in "{tmp_path / "30m/B5-IRS1_N2D+_3_2.30m"}"' in script
    expected_sd = tmp_path / "CD30m/l34l73" / f"{basename}.30m"
    assert f'file out "{expected_sd}"' in script
    assert f'file in "{expected_sd}"' in script
    assert Path(data_handler.get_sd_file(
        "B5-IRS1", "N2D+", "3_2", "l034l073",
        merge=True, selfcal=selfcal, contsub=contsub,
    )) == expected_sd
    assert Path(cfg.naming.sd_file(
        "B5-IRS1", "N2D+", "3_2", "l034l073", merge=True,
        selfcal=cfg.selfcal_ext if selfcal else "",
        contsub=cfg.uvsub_ext if contsub else "",
    )) == expected_sd


@pytest.mark.parametrize("custom_output", [False, True])
def test_prodige_line_prepare_merge_copies_selected_uvt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, custom_output: bool
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    if custom_output:
        with config_path.open("a") as config:
            config.write(
                "uvt_file_merge = {uvt_out_root}/custom/renamed{selfcal}{contsub}.uvt\n"
            )
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(data_handler, "_cfg", cfg)
    for name in (
        "region_catalogue", "line_name", "qn", "qn_str",
        "freq_mhz", "Lid", "name_str", "selfcal_ext", "uvsub_ext",
    ):
        monkeypatch.setattr(data_handler, name, getattr(cfg, name))
    input_file = tmp_path / "CD/l34l73/B5-IRS1_N2D+_3_2_l034l073_sc_contsub.uvt"
    input_file.parent.mkdir(parents=True)
    input_file.write_text("selected UVT")
    monkeypatch.setattr(
        "noema_combine.gildas.runner.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )

    result = data_handler.line_prepare_merge(
        "B5-IRS1", "N2D+", "3-2", execute=True, selfcal=True, contsub=True
    )

    assert result.executed
    destination = (
        tmp_path / "CD30m/custom/renamed_sc_contsub.uvt"
        if custom_output else tmp_path / "CD30m/l34l73" / input_file.name
    )
    assert destination.read_text() == "selected UVT"


def test_merged_line_imaging_uses_prepared_single_dish_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    cfg = Config(config_file=str(config_path), isolated=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(data_handler, "_cfg", cfg)
    for name in (
        "region_catalogue", "line_name", "qn", "qn_str",
        "freq_mhz", "Lid", "name_str", "selfcal_ext", "uvsub_ext",
    ):
        monkeypatch.setattr(data_handler, name, getattr(cfg, name))
    preparation = data_handler.line_prepare_merge(
        "B5-IRS1", "N2D+", "3-2", selfcal=True, contsub=True, execute=False
    )
    imaging = make_merged_line_images(
        "B5-IRS1", "CD", "N2D+", "3-2", "l034l073",
        selfcal=True, contsub=True, execute=False, config_file=str(config_path),
    )

    table = tmp_path / "CD30m/l34l73/B5-IRS1_N2D+_3_2_l034l073_sc_contsub.tab"
    assert imaging.single_dish_table == table
    assert imaging.prepared_uvt == table.with_suffix(".uvt")
    assert f'table "{table.with_suffix("")}"' in preparation.script_path.read_text()
    assert f'sic copy "{table}" "{table}"' not in imaging.image_script.read_text()


def test_default_narrowband_naming_uses_prodige_pair_forms():
    naming = FileNaming(root="/project")

    path = naming.render(
        "clean_input_narrowband",
        source="B5",
        source_out="B5-IRS1",
        config="CD",
        lid="l034l073",
        lid_pair_folder="l34l73",
        selfcal="_sc",
        contsub="_contsub",
    )

    assert path == ("/project/CD/l34l73/B5-IRS1_CD_l034l073_sc_contsub.uvt")


def test_prodige_naming_matrix_matches_representative_project_tree(tmp_path: Path):
    """Validate the default naming profile across the main product families."""
    naming = FileNaming(root=tmp_path, uvt_out_root=str(tmp_path / "CD30m"))
    common = {
        "source": "B5",
        "source_out": "B5-IRS1",
        "config": "CD",
        "window": "l034l073",
        "lid": "l034l073",
        "lid_pair": "l034l073",
        "lid_pair_folder": "l34l73",
        "lid_pair_filename": "l034l073",
        "line": "N2D+",
        "qn": "3-2",
        "selfcal": "_sc",
        "contsub": "_contsub",
    }
    paths = {
        "wideband": Path(naming.render("clean_input", **common)),
        "narrowband": Path(naming.render("clean_input_narrowband", **common)),
        "line": Path(naming.render("line_clean_cube", **common)),
        "merged": Path(naming.render("merged_line_uvt", **common)),
    }

    assert paths["wideband"] == (tmp_path / "CD/wideband/B5_CD_l034l073_sc_contsub.uvt")
    assert paths["narrowband"] == (
        tmp_path / "CD/l34l73/B5-IRS1_CD_l034l073_sc_contsub.uvt"
    )
    assert paths["line"].parent == tmp_path / "CD/l34l73"
    assert paths["merged"].parent == tmp_path / "CD30m/l034l073"
    assert "/narrowband/" not in str(paths["narrowband"])


def test_new_merge_selfcal_and_uvfits_templates_render(tmp_path: Path):
    naming = FileNaming(root=tmp_path)
    values = {
        "source": "B5",
        "source_out": "B5-IRS1",
        "config": "ACD",
        "config_a": "A",
        "config_b": "CD",
        "config_out": "ACD",
        "window": "l034l073",
        "lid": "l034l073",
        "lid_pair_folder": "l34l73",
        "lid_pair_filename": "l034l073",
        "selfcal": "_sc",
        "contsub": "_contsub",
        "suffix": "_sc_contsub",
        "window_folder": "l34l73",
    }
    assert naming.render("merge_input_a_narrowband", **values).endswith(
        "/A/l34l73/B5-IRS1_A_l034l073_sc_contsub.uvt"
    )
    assert naming.render("merge_output_narrowband", **values).endswith(
        "/ACD/l34l73/B5-IRS1_ACD_l034l073_sc_contsub.uvt"
    )
    assert naming.render("uvfits_output_narrowband", **values).endswith(
        "/ACD/l34l73/B5-IRS1_ACD_l034l073_sc_contsub.uvfits"
    )


def test_create_config_writes_style_profile_and_protects_existing_file(tmp_path: Path):
    config_path = tmp_path / "config.ini"
    assert create_config("propstar", config_path) == config_path
    content = config_path.read_text()
    assert "style = propstar" in content
    assert "line_catalogue = line_catalogue_propstar.csv" in content
    assert "inputdir = raw_data" in content
    assert "restore_output = {root}/{config}config/" in content
    assert "[narrowband]" in content
    assert "windows =" in content
    with pytest.raises(FileExistsError):
        create_config("propstar", config_path)


@pytest.mark.parametrize(
    "hostname",
    ["cas-alma.mpe.mpg.de", "cas2alma.mpe.mpg.de", "cas3alma.mpe.mpg.de"],
)
def test_create_config_enables_gildas_setup_on_casalma_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hostname: str
):
    monkeypatch.setattr(project_module.socket, "gethostname", lambda: hostname)
    monkeypatch.setattr(project_module.socket, "getfqdn", lambda: hostname)

    config_path = tmp_path / "casalma.ini"
    create_config("prodige", config_path)
    content = config_path.read_text()

    assert "setup = gildas_latest" in content
    assert "setup_file = /etc/profile.d/gildas.sh" in content


def test_create_config_keeps_gildas_setup_empty_on_other_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(project_module.socket, "gethostname", lambda: "workstation")
    monkeypatch.setattr(project_module.socket, "getfqdn", lambda: "workstation.example")

    config_path = tmp_path / "workstation.ini"
    create_config("prodige", config_path)
    content = config_path.read_text()

    assert "setup = \n" in content
    assert "setup_file = \n" in content


def test_prodige_config_contains_raw_script_narrowband_ranges(tmp_path: Path):
    prodige = tmp_path / "prodige.ini"
    propstar = tmp_path / "propstar.ini"
    create_config("prodige", prodige)
    create_config("propstar", propstar)

    prodige_text = prodige.read_text()
    propstar_text = propstar.read_text()
    assert (
        "inputdir = /projects/MIOP/30mDATA/164-23/, /projects/MIOP/30mDATA/162-24/"
        in prodige_text
    )
    assert "inputdir = raw_data" in propstar_text
    assert "uvt_dir_out = CD30m\n" in prodige_text
    assert "uvt_dir_out = D30m\n" in propstar_text
    assert "l034l073 = 0 20 3200 3280 4800 4900 8172 8192" in prodige_text
    assert "l010l049 = 0 20 1004 1024" in prodige_text
    assert "[narrowband_channel_ranges]" in propstar_text
    assert "l034l073 =" not in propstar_text


def test_create_config_defaults_to_prodige_output_directory(tmp_path: Path):
    config_path = create_config(filename=tmp_path / "default.ini")

    assert "uvt_dir_out = CD30m\n" in config_path.read_text()


def test_create_line_catalogue_and_project_files(tmp_path: Path):
    catalogue_path = tmp_path / "lines.csv"
    assert create_line_catalogue("propstar", catalogue_path) == catalogue_path
    assert "#name" in catalogue_path.read_text()
    with pytest.raises(FileExistsError):
        create_line_catalogue("propstar", catalogue_path)

    config_path, default_catalogue = create_project_files(
        "prodige",
        config_filename=tmp_path / "project.ini",
        catalogue_filename=tmp_path / "project_lines.csv",
        region_catalogue_filename=tmp_path / "regions.yml",
    )
    assert config_path.exists()
    assert default_catalogue.exists()
    assert "line_catalogue = " + str(default_catalogue) in config_path.read_text()
    assert (
        default_catalogue.read_text()
        == (
            Path(__file__).parents[1] / "src/noema_combine/line_catalogue_MIOP.csv"
        ).read_text()
    )

    custom_config, custom_catalogue = create_project_files(
        "propstar",
        catalogue="prodige",
        config_filename=tmp_path / "custom.ini",
        catalogue_filename=tmp_path / "catalogues/custom.csv",
        region_catalogue_filename=tmp_path / "catalogues/custom_regions.yml",
    )
    assert custom_config.exists() and custom_catalogue.exists()
    assert "line_catalogue = " + str(custom_catalogue) in custom_config.read_text()

    region_path = tmp_path / "standalone_regions.yml"
    assert create_region_catalogue(region_path) == region_path
    assert "RA0" in region_path.read_text()


def test_preview_naming_covers_merged_line_project_tree(tmp_path: Path):
    config_path, _ = create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "line_catalogue_prodige.csv",
        region_catalogue_filename=tmp_path / "region_catalogue.yml",
    )
    preview = preview_naming(
        "B5",
        "CD",
        line="N2D+",
        qn="3-2",
        lid="l034l073",
        config_file=str(config_path),
    )
    outputs = preview["outputs"]
    assert outputs["merged_line_uvt"].endswith(
        "/CD30m/l34l73/B5_N2D+_3-2_l034l073_sc_contsub.uvt"
    )
    assert outputs["merged_line_clean_cube"].endswith(
        "/CD30m/l34l73/B5_CD_N2D+_3-2_sc_contsub-merged.lmv-clean"
    )


def test_import_succeeds_with_generated_config_in_current_directory(tmp_path: Path):
    create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "line_catalogue_prodige.csv",
        region_catalogue_filename=tmp_path / "region_catalogue.yml",
    )
    source_root = Path(__file__).parents[1] / "src"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = (
        str(source_root) + os.pathsep + environment.get("PYTHONPATH", "")
    )
    completed = subprocess.run(
        [sys.executable, "-c", "from noema_combine import create_project_files"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_custom_case_and_pair_templates():
    naming = FileNaming(
        {
            "uvt_file": "{root}/{config}/wideband/{source}_{config}_{lid_upper}_{line}_{selfcal}{contsub}.uvt",
            "narrowband_folder": "{root}/{config}/narrowband/{lid_pair}",
        },
        root="/data/project",
    )

    assert (
        naming.uvt_file(
            "B5",
            "CO",
            "1-0",
            "l10",
            config="CD",
            selfcal="_sc",
            contsub="_contsub",
        )
        == "/data/project/CD/wideband/B5_CD_L10_CO__sc_contsub.uvt"
    )
    assert (
        naming.narrowband_folder("B5", "CD", "L10", lid_pair="l10l49")
        == "/data/project/CD/narrowband/l10l49"
    )


def test_search_patterns_allow_wildcards():
    naming = FileNaming(
        {"search_uvt": "{root}/{config}/**/{source}*{lid}*{line}*.uvt"},
        root="/data/project",
    )
    assert (
        naming.search_pattern(source="B5", config="CD", lid="L10", line="CO")
        == "/data/project/CD/**/B5*L10*CO*.uvt"
    )


def test_output_templates_reject_wildcards():
    with pytest.raises(ValueError, match="wildcard"):
        FileNaming({"uvt_file": "{root}/*{source}.uvt"})


def test_preview_naming_returns_outputs_and_search_patterns():
    preview = preview_naming(
        source="B5", config="CD", line="CO", qn="1-0", lid="l10", lid_pair="l10l49"
    )

    assert "configuration" in preview
    assert "outputs" in preview
    assert "search_patterns" in preview
    assert preview["outputs"]["uvt_file"] == "D/l10/B5_CO_1-0_l10_sc_contsub.uvt"
    assert "search_uvt" in preview["search_patterns"]


def test_naming_uses_catalogue_source_out_for_wideband_and_narrowband(tmp_path: Path):
    """Output names use the catalogue output identifier for both clean products."""
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    region_file = tmp_path / "region_catalogue.yml"
    region_file.write_text(
        "B5-IRS1:\n"
        '  RA0: "03h47m41.591s"\n'
        '  Dec0: "32d51m43.672s"\n'
        '  height: "40 arcsec"\n'
        '  width: "40 arcsec"\n'
        "  fig_width: 6.0\n"
        "  fig_height: 6.0\n"
        "  Vlsr: 9.0\n"
        '  source_sd: "B5*"\n'
        '  source_out: "B5-IRS1"\n'
    )
    config_file = tmp_path / "naming.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged_uvts\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {region_file}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[file_extensions]\nselfcal = _sc\nuvsub = _contsub\n\n[naming]\nroot = .\nclean_input = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.uvt\n"""
    )

    preview = preview_naming(
        source="B5-IRS1",
        config="CD",
        lid="l10",
        lid_pair="l10l49",
        config_file=str(config_file),
    )

    assert preview["outputs"]["clean_input"] == (
        str(tmp_path / "CD/wideband/B5-IRS1_CD_l10_sc_contsub.uvt")
    )
    assert preview["outputs"]["clean_input_narrowband"] == (
        str(tmp_path / "CD/l10l49/B5-IRS1_CD_l010l049_sc_contsub.uvt")
    )


def test_preview_naming_allows_single_dish_only_context():
    preview = preview_naming(source="B5", config="CD", line="N2Dp", qn="3-2")

    assert "outputs" in preview
    assert preview["outputs"]["restore_output_line"].endswith(
        "/B5_CD_N2Dp_3-2_sc_contsub_uvres.lmv-clean"
    )
    assert preview["outputs"]["merged_cube"].endswith("/B5_N2Dp_3-2_product.fits")


def test_preview_naming_defaults_style_to_prodige_for_custom_templates():
    naming = FileNaming({"style_marker": "{style}"})
    assert naming.render("style_marker") == "prodige"


def test_preview_naming_infers_lid_from_line_catalogue(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "preview_prodige.ini"
    config_file.write_text(
        f"""[project]\nstyle = prodige\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_MIOP.csv"}\n\n[naming]\nroot = .\n"""
    )

    preview = preview_naming(
        source="B5",
        config="CD",
        line="N2Dp",
        qn="3-2",
        config_file=str(config_file),
    )

    assert preview["outputs"]["restore_output_line"].endswith(
        "/B5_CD_N2Dp_3-2_l034l073_sc_contsub_uvres.lmv-clean"
    )
    assert preview["outputs"]["merged_cube"].endswith(
        "/B5_N2Dp_3-2_l034l073_product.fits"
    )


def test_explicit_config_resolves_relative_paths_from_base_dir(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "project.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data, extra\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[naming]\nroot = .\nnarrowband_folder = {{root}}/{{config}}/narrowband/{{lid_pair}}\n"""
    )

    cfg = reload_config(str(config_file))
    try:
        assert cfg.base_dir == tmp_path.resolve()
        assert cfg.uvt_dir == str((tmp_path / "uvts").resolve())
        assert cfg.inputdir == [
            str((tmp_path / "raw_data").resolve()),
            str((tmp_path / "extra").resolve()),
        ]
        assert cfg.naming.narrowband_folder(
            "B5", "CD", "L10", lid_pair="l10l49"
        ) == str((tmp_path / "CD/narrowband/l10l49").resolve())
    finally:
        reload_config()


def test_preview_with_explicit_config_does_not_replace_global_config(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "preview.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[naming]\nroot = .\nuvt_file = {{root}}/{{config}}/{{source}}_{{lid_upper}}.uvt\n"""
    )
    before = str(get_config().config_file)
    result = preview_naming(
        source="B5",
        config="CD",
        line="CO",
        qn="1-0",
        lid="l10",
        config_file=str(config_file),
    )
    after = str(get_config().config_file)

    assert result["outputs"]["uvt_file"].endswith("/CD/B5_L10.uvt")
    assert before == after


def test_wideband_continuum_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "workflow.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[naming]\nroot = .\ncontinuum_input = {{root}}/input/{{source}}_{{config}}_{{lid}}.uvt\ncontinuum_subtracted_file = {{root}}/output/{{source}}_{{config}}_{{lid}}{{contsub}}.uvt\ncontinuum_cube = {{root}}/output/{{source}}_{{config}}_{{lid}}.lmv-clean\ncontinuum_plot = {{root}}/output/{{source}}_{{config}}_{{lid}}.png\ncontinuum_range_file = {{root}}/{{source}}_{{config}}_{{lid}}_linerange.txt\ncontinuum_filter_file = {{root}}/{{source}}_{{config}}_{{lid}}_filter.txt\n"""
    )

    result = make_continuum_subtraction(
        "B5", "CD", "li", no_cube=True, execute=False, config_file=str(config_file)
    )

    assert result.output_file == tmp_path / "output/B5_CD_li_contsub.uvt"
    assert result.executions[0].executed is False
    assert result.scripts[0].exists()
    assert "uv_baseline 0\n" in result.scripts[0].read_text()


def test_wideband_continuum_script_retention_is_explicit(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "retention.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\n\n[naming]\nroot = .\ncontinuum_input = {{root}}/input/{{source}}_{{config}}_{{lid}}.uvt\ncontinuum_subtracted_file = {{root}}/output/{{source}}_{{config}}_{{lid}}{{contsub}}.uvt\ncontinuum_range_file = {{root}}/{{source}}_{{config}}_{{lid}}_linerange.txt\ncontinuum_filter_file = {{root}}/{{source}}_{{config}}_{{lid}}_filter.txt\n"""
    )

    retained = make_continuum_subtraction(
        "B5", "CD", "li", no_cube=True, execute=False, config_file=str(config_file)
    )
    assert retained.scripts and all(path.exists() for path in retained.scripts)

    removed = make_continuum_subtraction(
        "B5",
        "CD",
        "li",
        no_cube=True,
        keep_script=False,
        execute=False,
        config_file=str(config_file),
    )
    assert removed.scripts and all(not path.exists() for path in removed.scripts)


def test_continuum_cube_clean_uses_support_mask_defaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "continuum-mask.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\n\n[naming]\nroot = .\ncontinuum_input = {{root}}/input/{{source}}_{{config}}_{{lid}}.uvt\ncontinuum_subtracted_file = {{root}}/output/{{source}}_{{config}}_{{lid}}{{contsub}}.uvt\ncontinuum_cube = {{root}}/output/{{source}}_{{config}}_{{lid}}.lmv-clean\ncontinuum_range_file = {{root}}/{{source}}_{{config}}_{{lid}}_linerange.txt\ncontinuum_filter_file = {{root}}/{{source}}_{{config}}_{{lid}}_filter.txt\n"""
    )

    unmasked = make_continuum_subtraction(
        "B5", "CD", "li", execute=False, config_file=str(config_file)
    )
    unmasked_script = unmasked.scripts[-1].read_text()
    assert "let ares 3.0*'H%noise'" in unmasked_script
    assert "let MYCLEAN%SUPPORT NO\ngo clean" in unmasked_script

    mask = tmp_path / "output/B5_CD_li.msk"
    mask.parent.mkdir(parents=True, exist_ok=True)
    mask.touch()
    masked = make_continuum_subtraction(
        "B5", "CD", "li", execute=False, config_file=str(config_file)
    )
    masked_script = masked.scripts[-1].read_text()
    assert "let ares 2.0*'H%noise'" in masked_script
    assert "let MYCLEAN%SUPPORT YES\ngo clean" in masked_script
    assert "Support mask found, cleaning with support" in capsys.readouterr().out


def test_narrowband_continuum_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "narrowband.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[narrowband]\nwindows = l009l048\n\n[naming]\nroot = .\nnarrowband_folder = {{root}}/{{config}}/narrowband/{{lid_pair}}\nnarrowband_input = {{narrowband_folder}}/{{source}}_{{config}}_{{lid_pair}}_sc.uvt\nnarrowband_output = {{narrowband_folder}}/{{source}}_{{config}}_{{lid_pair}}_sc{{contsub}}.uvt\nnarrowband_script = {{narrowband_folder}}/{{source}}_{{config}}_{{lid_pair}}_contsub.map\n"""
    )

    results = make_narrowband_continuum_subtraction(
        "B5", "CD", ["L9L48"], execute=False, config_file=str(config_file)
    )

    assert len(results) == 1
    result = results[0]
    assert result.window == "l009l048"
    assert result.channel_range is None
    assert (
        result.script_path
        == tmp_path / "CD/narrowband/l009l048/B5_CD_l009l048_contsub.map"
    )
    assert "uv_baseline 0\n" in result.script_path.read_text()


def test_narrowband_continuum_single_channel_range(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "narrowband-range.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[narrowband]\nwindows = l009l048\n"""
    )

    results = make_narrowband_continuum_subtraction(
        "B5",
        "CD",
        ["l009l048"],
        channel_range="0 20 100 260 1004 1024",
        execute=False,
        config_file=str(config_file),
    )

    assert results[0].channel_range == "0 20 100 260 1004 1024"


def test_narrowband_continuum_accepts_single_window_string(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "narrowband-string.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[narrowband]\nwindows = l034l073\n"""
    )

    results = make_narrowband_continuum_subtraction(
        "B5",
        "CD",
        "l034l073",
        channel_range="0 50 95 96 160 190",
        execute=False,
        config_file=str(config_file),
    )

    assert len(results) == 1
    assert results[0].window == "l034l073"
    assert results[0].channel_range == "0 50 95 96 160 190"


def test_narrowband_continuum_single_channel_range_rejects_multiple_windows(
    tmp_path: Path,
):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "narrowband-range.ini"
    config_file.write_text(
        f"""[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[narrowband]\nwindows = l009l048, l010l049\n"""
    )

    with pytest.raises(ValueError, match="only be used when one"):
        make_narrowband_continuum_subtraction(
            "B5",
            "CD",
            ["l009l048", "l010l049"],
            channel_range="0 20",
            execute=False,
            config_file=str(config_file),
        )


def test_dirty_image_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "imaging.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[imaging]\nwideband_windows = li\ninclude_narrowband = false\n\n[naming]\nroot = .\ndirty_folder = {{root}}/{{config}}/{{window_folder}}\ndirty_input = {{dirty_folder}}/{{source}}_{{config}}_{{window}}.uvt\ndirty_script = {{dirty_folder}}/{{source}}_{{config}}_{{window}}_dirty.map\ndirty_map = {{dirty_folder}}/{{source}}_{{config}}_{{window}}.lmv\n"""
    )

    results = make_dirty_images("B5", "CD", execute=False, config_file=str(config_file))

    assert len(results) == 1
    result = results[0]
    assert result.window == "li"
    assert result.input_file == tmp_path / "CD/wideband/B5_CD_li.uvt"
    assert "map_beam_step 1" in result.script_path.read_text()


def test_dirty_images_support_selfcal_and_contsub_for_both_window_types(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "suffixes.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[narrowband]\nwindows = l009l048\n\n[imaging]\nwideband_windows = li\ninclude_narrowband = true\n\n[naming]\nroot = .\ndirty_folder = {{root}}/{{config}}/{{window_folder}}\ndirty_input = {{dirty_folder}}/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.uvt\ndirty_script = {{dirty_folder}}/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}_dirty.map\ndirty_map = {{dirty_folder}}/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.lmv\n"""
    )

    wideband = make_dirty_images(
        "B5",
        "CD",
        ["li"],
        selfcal=True,
        contsub=True,
        execute=False,
        config_file=str(config_file),
    )[0]
    narrowband = make_dirty_images(
        "B5", "CD", ["L9L48"], selfcal=True, execute=False, config_file=str(config_file)
    )[0]

    assert wideband.input_file.name == "B5_CD_li_sc_contsub.uvt"
    assert narrowband.input_file.name == "B5_CD_l009l048_sc.uvt"


def test_clean_image_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "cleaning.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / "region_catalogue.yml"}\nline_catalogue = {package_dir / "line_catalogue_3mm.csv"}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[imaging]\nwideband_windows = li\n\n[cleaning]\nweighting = natural\nthreshold_factor = 5\nniter = 0\nprimary_beam_correction = true\nprimary_beam_truncate = 20\n\n[naming]\nroot = .\nclean_input = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.uvt\nclean_script = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}_clean.map\nclean_cube = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.lmv-clean\nclean_fits = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.fits\nclean_pb_cube = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}-pbcor.lmv-sky\nclean_pb_fits = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}-pbcor.fits\n"""
    )

    result = make_clean_images(
        "B5",
        "CD",
        "li",
        selfcal=True,
        contsub=True,
        execute=False,
        config_file=str(config_file),
    )[0]

    assert result.input_file.name == "B5_CD_li_sc_contsub.uvt"
    assert result.cleaned_fits.name == "B5_CD_li_sc_contsub.fits"
    script = result.script_path.read_text()
    assert "go clean" in script
    assert "primary /truncate 20" in script

    mixed = make_clean_images(
        "B5",
        "CD",
        windows=["li", "L9L48"],
        selfcal=True,
        contsub=True,
        execute=False,
        config_file=str(config_file),
    )
    assert [item.window_kind for item in mixed] == ["wideband", "narrowband"]
    assert mixed[1].input_file.name == "B5_CD_l009l048_sc_contsub.uvt"


def _restoration_config(tmp_path: Path, *, include_narrowband: bool = True) -> Path:
    package_dir = Path(__file__).parents[1] / "src" / "noema_combine"
    config_file = tmp_path / "restoration.ini"
    config_file.write_text(
        f"""[project]
base_dir = .

[folders]
uvt_dir = uvts
uvt_dir_out = merged
dir_sd = single_dish
inputdir = raw_data

[catalogues]
source_catalogue = {package_dir / "region_catalogue.yml"}
line_catalogue = {package_dir / "line_catalogue_3mm.csv"}

[gildas]
execute = false
workdir = .

[imaging]
wideband_windows = li
include_narrowband = {str(include_narrowband).lower()}

[narrowband]
windows = l009l048

[naming]
root = .
"""
    )
    return config_file


def test_restore_image_supports_wideband_and_narrowband_script_only(tmp_path: Path):
    config_file = _restoration_config(tmp_path)

    results = restore_image(
        "B5",
        "CD",
        windows=["li", "L9L48"],
        product_type="cube",
        selfcal=True,
        contsub=True,
        execute=False,
        config_file=str(config_file),
    )

    assert [result.window_kind for result in results] == ["wideband", "narrowband"]
    assert results[0].input_uv == tmp_path / "CD/wideband/B5_CD_li_sc_contsub.uvt"
    assert results[1].input_uv == (tmp_path / "CD/l09l48/B5_CD_l009l048_sc_contsub.uvt")
    assert results[0].restored_cube.name == "B5_CD_li_sc_contsub_uvres.lmv-clean"
    assert results[0].script_path.exists()
    script = results[0].script_path.read_text()
    assert "read uv" in script
    assert "read cct" in script
    assert "uv_restore" in script
    assert "primary /truncate 20" in script
    assert results[0].execution.executed is False


def test_restore_image_supports_individual_line_with_custom_lid(tmp_path: Path):
    config_file = _restoration_config(tmp_path, include_narrowband=False)

    result = restore_image(
        "B5",
        "CD",
        line="CO",
        qn="1-0",
        lid="l123l162",
        product_type="line",
        execute=False,
        config_file=str(config_file),
    )[0]

    assert result.product_type == "line"
    assert result.line == "CO"
    assert result.qn == "1-0"
    assert result.window == "l123l162"
    assert result.input_uv == tmp_path / "CD/l123l162/B5_CD_CO_1-0_l123l162.uvt"
    assert result.restored_fits.name == "B5_CD_CO_1-0_l123l162_uvres.fits"
    assert "B5_CD_CO_1-0_l123l162" in result.script_path.read_text()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"product_type": "invalid"}, "product_type"),
        ({"product_type": "line", "line": "CO", "qn": "1-0"}, "requires line"),
        (
            {
                "product_type": "line",
                "line": "CO",
                "qn": "1-0",
                "lid": "l9",
                "windows": ["li"],
            },
            "combined",
        ),
        ({"product_type": "cube", "line": "CO"}, "only valid"),
    ],
)
def test_restore_image_validates_product_selection(tmp_path: Path, kwargs, message):
    config_file = _restoration_config(tmp_path)
    with pytest.raises(ValueError, match=message):
        restore_image("B5", "CD", execute=False, config_file=str(config_file), **kwargs)


def test_channel_range_precedence_and_no_range_command(tmp_path: Path):
    cfg = get_config()
    original_wideband = cfg.continuum_wideband_ranges
    original_narrowband = cfg.continuum_narrowband_ranges
    cfg.continuum_wideband_ranges = {"li": "0 20 100 200"}
    cfg.continuum_narrowband_ranges = {"l009l048": "0 10 900 1000"}
    range_file = tmp_path / "channels.txt"
    range_file.write_text("0 30 500 600\n")
    try:
        assert resolve_channel_range("li", config=cfg) == "0 20 100 200"
        assert resolve_channel_range("li", channel_range="0 5", config=cfg) == "0 5"
        assert (
            resolve_channel_range("li", range_file=range_file, config=cfg)
            == "0 30 500 600"
        )
        assert (
            resolve_channel_range("l009l048", narrowband=True, config=cfg)
            == "0 10 900 1000"
        )
        assert resolve_channel_range("uo", config=cfg) is None
        assert baseline_command() == "uv_baseline 0"
        assert (
            baseline_command("0 20 100 200")
            == "uv_baseline 0 /range 0 20 100 200 channel"
        )
        script = build_continuum_subtraction_script("input.uvt", "output.uvt")
        assert "uv_baseline 0\n" in script
        assert "/range" not in script
    finally:
        cfg.continuum_wideband_ranges = original_wideband
        cfg.continuum_narrowband_ranges = original_narrowband
