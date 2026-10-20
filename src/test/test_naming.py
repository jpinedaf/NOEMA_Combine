from pathlib import Path
import os
import subprocess
import sys

import pytest

from noema_combine.config import get_config, reload_config
from noema_combine.continuum import (
    baseline_command,
    build_continuum_subtraction_script,
    resolve_channel_range,
)
from noema_combine.workflows import make_continuum_subtraction
from noema_combine.workflows import make_narrowband_continuum_subtraction
from noema_combine.workflows import make_dirty_images
from noema_combine.workflows import make_clean_images
from noema_combine.workflows import restore_image
from noema_combine.naming import FileNaming, preview_naming
from noema_combine import (
    create_config,
    create_line_catalogue,
    create_project_files,
    create_region_catalogue,
)


def test_default_naming_matches_package_paths():
    naming = FileNaming()

    assert naming.uvt_file("B5", "CO", "1-0", "L09") == "D/L09/B5_CO_1-0_L09.uvt"
    assert naming.uvt_window("B5", "L09") == "D/L09/B5_L09_contsub.uvt"
    assert naming.sd_file("B5", "CO", "1-0", "L09") == "30m/B5_CO_1-0.30m"


def test_create_config_writes_style_profile_and_protects_existing_file(tmp_path: Path):
    config_path = tmp_path / "config.ini"
    assert create_config("propstar", config_path) == config_path
    content = config_path.read_text()
    assert "style = propstar" in content
    assert "line_catalogue = line_catalogue_propstar.csv" in content
    assert "restore_output = {root}/{config}config/" in content
    with pytest.raises(FileExistsError):
        create_config("propstar", config_path)


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
    assert default_catalogue.read_text() == (
        Path(__file__).parents[1] / "noema_combine/line_catalogue_MIOP.csv"
    ).read_text()

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


def test_import_succeeds_with_generated_config_in_current_directory(tmp_path: Path):
    create_project_files(
        "prodige",
        config_filename=tmp_path / "config.ini",
        catalogue_filename=tmp_path / "line_catalogue_prodige.csv",
        region_catalogue_filename=tmp_path / "region_catalogue.yml",
    )
    source_root = Path(__file__).parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source_root) + os.pathsep + environment.get("PYTHONPATH", "")
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

    assert naming.uvt_file(
        "B5",
        "CO",
        "1-0",
        "l10",
        config="CD",
        selfcal="_sc",
        contsub="_contsub",
    ) == "/data/project/CD/wideband/B5_CD_L10_CO__sc_contsub.uvt"
    assert naming.narrowband_folder(
        "B5", "CD", "L10", lid_pair="l10l49"
    ) == "/data/project/CD/narrowband/l10l49"


def test_search_patterns_allow_wildcards():
    naming = FileNaming(
        {"search_uvt": "{root}/{config}/**/{source}*{lid}*{line}*.uvt"},
        root="/data/project",
    )
    assert naming.search_pattern(
        source="B5", config="CD", lid="L10", line="CO"
    ) == "/data/project/CD/**/B5*L10*CO*.uvt"


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
    assert preview["outputs"]["uvt_file"] == "D/l10/B5_CO_1-0_l10.uvt"
    assert "search_uvt" in preview["search_patterns"]


def test_naming_uses_catalogue_source_out_for_wideband_and_narrowband(tmp_path: Path):
    """Output names use the catalogue output identifier for both clean products."""
    package_dir = Path(__file__).parents[1] / "noema_combine"
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
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged_uvts\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {region_file}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[file_extensions]\nselfcal = _sc\nuvsub = _contsub\n\n[naming]\nroot = .\nclean_input = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.uvt\n"""
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
    assert preview["outputs"]["merged_cube"].endswith(
        "/B5_N2Dp_3-2_product.fits"
    )


def test_preview_naming_defaults_style_to_prodige_for_custom_templates():
    naming = FileNaming({"style_marker": "{style}"})
    assert naming.render("style_marker") == "prodige"


def test_preview_naming_infers_lid_from_line_catalogue(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "preview_prodige.ini"
    config_file.write_text(
        f"""[project]\nstyle = prodige\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_MIOP.csv'}\n\n[naming]\nroot = .\n"""
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
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "project.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data, extra\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[naming]\nroot = .\nnarrowband_folder = {{root}}/{{config}}/narrowband/{{lid_pair}}\n"""
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
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "preview.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[naming]\nroot = .\nuvt_file = {{root}}/{{config}}/{{source}}_{{lid_upper}}.uvt\n"""
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
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "workflow.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[naming]\nroot = .\ncontinuum_input = {{root}}/input/{{source}}_{{config}}_{{lid}}.uvt\ncontinuum_subtracted_file = {{root}}/output/{{source}}_{{config}}_{{lid}}{{contsub}}.uvt\ncontinuum_cube = {{root}}/output/{{source}}_{{config}}_{{lid}}.lmv-clean\ncontinuum_plot = {{root}}/output/{{source}}_{{config}}_{{lid}}.png\ncontinuum_range_file = {{root}}/{{source}}_{{config}}_{{lid}}_linerange.txt\ncontinuum_filter_file = {{root}}/{{source}}_{{config}}_{{lid}}_filter.txt\n"""
    )

    result = make_continuum_subtraction(
        "B5", "CD", "li", no_cube=True, execute=False, config_file=str(config_file)
    )

    assert result.output_file == tmp_path / "output/B5_CD_li_contsub.uvt"
    assert result.executions[0].executed is False
    assert result.scripts[0].exists()
    assert "uv_baseline 0\n" in result.scripts[0].read_text()


def test_narrowband_continuum_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "narrowband.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[narrowband]\nwindows = l009l048\n\n[naming]\nroot = .\nnarrowband_folder = {{root}}/{{config}}/narrowband/{{lid_pair}}\nnarrowband_input = {{narrowband_folder}}/{{source}}_{{config}}_{{lid_pair}}_sc.uvt\nnarrowband_output = {{narrowband_folder}}/{{source}}_{{config}}_{{lid_pair}}_sc{{contsub}}.uvt\nnarrowband_script = {{narrowband_folder}}/{{source}}_{{config}}_{{lid_pair}}_contsub.map\n"""
    )

    results = make_narrowband_continuum_subtraction(
        "B5", "CD", ["L9L48"], execute=False, config_file=str(config_file)
    )

    assert len(results) == 1
    result = results[0]
    assert result.window == "l009l048"
    assert result.channel_range is None
    assert result.script_path == tmp_path / "CD/narrowband/l009l048/B5_CD_l009l048_contsub.map"
    assert "uv_baseline 0\n" in result.script_path.read_text()


def test_dirty_image_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "imaging.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[imaging]\nwideband_windows = li\ninclude_narrowband = false\n\n[naming]\nroot = .\ndirty_folder = {{root}}/{{config}}/{{window_folder}}\ndirty_input = {{dirty_folder}}/{{source}}_{{config}}_{{window}}.uvt\ndirty_script = {{dirty_folder}}/{{source}}_{{config}}_{{window}}_dirty.map\ndirty_map = {{dirty_folder}}/{{source}}_{{config}}_{{window}}.lmv\n"""
    )

    results = make_dirty_images("B5", "CD", execute=False, config_file=str(config_file))

    assert len(results) == 1
    result = results[0]
    assert result.window == "li"
    assert result.input_file == tmp_path / "CD/wideband/B5_CD_li.uvt"
    assert "map_beam_step 1" in result.script_path.read_text()


def test_dirty_images_support_selfcal_and_contsub_for_both_window_types(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "suffixes.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[narrowband]\nwindows = l009l048\n\n[imaging]\nwideband_windows = li\ninclude_narrowband = true\n\n[naming]\nroot = .\ndirty_folder = {{root}}/{{config}}/{{window_folder}}\ndirty_input = {{dirty_folder}}/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.uvt\ndirty_script = {{dirty_folder}}/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}_dirty.map\ndirty_map = {{dirty_folder}}/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.lmv\n"""
    )

    wideband = make_dirty_images(
        "B5", "CD", ["li"], selfcal=True, contsub=True,
        execute=False, config_file=str(config_file)
    )[0]
    narrowband = make_dirty_images(
        "B5", "CD", ["L9L48"], selfcal=True,
        execute=False, config_file=str(config_file)
    )[0]

    assert wideband.input_file.name == "B5_CD_li_sc_contsub.uvt"
    assert narrowband.input_file.name == "B5_CD_l009l048_sc.uvt"


def test_clean_image_workflow_script_only(tmp_path: Path):
    package_dir = Path(__file__).parents[1] / "noema_combine"
    config_file = tmp_path / "cleaning.ini"
    config_file.write_text(
        f"""[project]\nbase_dir = .\n\n[folders]\nuvt_dir = uvts\nuvt_dir_out = merged\ndir_sd = single_dish\ninputdir = raw_data\n\n[catalogues]\nsource_catalogue = {package_dir / 'region_catalogue.yml'}\nline_catalogue = {package_dir / 'line_catalogue_3mm.csv'}\n\n[gildas]\nexecute = false\nworkdir = .\n\n[imaging]\nwideband_windows = li\n\n[cleaning]\nweighting = natural\nthreshold_factor = 5\nniter = 0\nprimary_beam_correction = true\nprimary_beam_truncate = 20\n\n[naming]\nroot = .\nclean_input = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.uvt\nclean_script = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}_clean.map\nclean_cube = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.lmv-clean\nclean_fits = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}.fits\nclean_pb_cube = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}-pbcor.lmv-sky\nclean_pb_fits = {{root}}/{{config}}/wideband/{{source}}_{{config}}_{{window}}{{selfcal}}{{contsub}}-pbcor.fits\n"""
    )

    result = make_clean_images(
        "B5", "CD", "li", selfcal=True, contsub=True,
        execute=False, config_file=str(config_file)
    )[0]

    assert result.input_file.name == "B5_CD_li_sc_contsub.uvt"
    assert result.cleaned_fits.name == "B5_CD_li_sc_contsub.fits"
    script = result.script_path.read_text()
    assert "go clean" in script
    assert "primary /truncate 20" in script

    mixed = make_clean_images(
        "B5", "CD", windows=["li", "L9L48"], selfcal=True,
        contsub=True, execute=False, config_file=str(config_file)
    )
    assert [item.window_kind for item in mixed] == ["wideband", "narrowband"]
    assert mixed[1].input_file.name == "B5_CD_l009l048_sc_contsub.uvt"


def _restoration_config(tmp_path: Path, *, include_narrowband: bool = True) -> Path:
    package_dir = Path(__file__).parents[1] / "noema_combine"
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
source_catalogue = {package_dir / 'region_catalogue.yml'}
line_catalogue = {package_dir / 'line_catalogue_3mm.csv'}

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
    assert results[1].input_uv == (
        tmp_path / "CD/l9l48/B5_CD_l009l048_sc_contsub.uvt"
    )
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
        ({"product_type": "line", "line": "CO", "qn": "1-0", "lid": "l9", "windows": ["li"]}, "combined"),
        ({"product_type": "cube", "line": "CO"}, "only valid"),
    ],
)
def test_restore_image_validates_product_selection(tmp_path: Path, kwargs, message):
    config_file = _restoration_config(tmp_path)
    with pytest.raises(ValueError, match=message):
        restore_image(
            "B5", "CD", execute=False, config_file=str(config_file), **kwargs
        )


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
        assert resolve_channel_range("li", range_file=range_file, config=cfg) == "0 30 500 600"
        assert resolve_channel_range("l009l048", narrowband=True, config=cfg) == "0 10 900 1000"
        assert resolve_channel_range("uo", config=cfg) is None
        assert baseline_command() == "uv_baseline 0"
        assert baseline_command("0 20 100 200") == "uv_baseline 0 /range 0 20 100 200 channel"
        script = build_continuum_subtraction_script("input.uvt", "output.uvt")
        assert "uv_baseline 0\n" in script
        assert "/range" not in script
    finally:
        cfg.continuum_wideband_ranges = original_wideband
        cfg.continuum_narrowband_ranges = original_narrowband
