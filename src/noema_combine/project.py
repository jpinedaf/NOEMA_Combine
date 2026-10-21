"""Helpers for creating editable project configuration files."""

from __future__ import annotations

from configparser import ConfigParser
from importlib.resources import files
from pathlib import Path
from typing import Literal


ConfigStyle = Literal["prodige", "propstar"]


_PRODIGE_NARROWBAND_RANGES = {
    "l009l048": "0 20 100 260 1004 1024",
    "l012l051": "0 20 80 170 1004 1024",
    "l013l052": "0 20 680 790 1004 1024",
    "l014l053": "0 20 2028 2048",
    "l015l054": "0 20 2028 2048",
    "l017l056": "0 20 690 770 1004 1024",
    "l019l058": "0 20 800 890 1004 1024",
    "l020l059": "0 20 650 720 2028 2048",
    "l021l060": "0 20 40 120 2028 2048",
    "l025l064": "0 20 910 1090 2028 2048",
    "l026l065": "0 20 30 120 3052 3072",
    "l027l066": "0 20 1005 1190 2028 2048",
    "l028l067": "0 20 4076 4096",
    "l032l071": "0 20 250 720 1004 1024",
    "l034l073": "0 20 3200 3280 4800 4900 8172 8192",
    "l039l078": "0 20 2028 2048",
    "l041l080": "0 20 5100 5120",
    "l043l082": "0 20 3052 3072",
    "l044l083": "0 20 2028 2048",
    "l045l084": "0 20 1160 1280 2028 2048",
}
for _window_start in range(9, 48):
    _PRODIGE_NARROWBAND_RANGES.setdefault(
        f"l{_window_start:03d}l{_window_start + 39:03d}",
        "0 20 1004 1024",
    )


_WIDEBAND = {
    "dirty_folder": "{root}/{config}/{window_folder}",
    "dirty_input": "{dirty_folder}/{source}_{config}_{window}{selfcal}{contsub}.uvt",
    "dirty_script": "{dirty_folder}/{source}_{config}_{window}{selfcal}{contsub}_dirty.map",
    "dirty_map": "{dirty_folder}/{source}_{config}_{window}{selfcal}{contsub}.lmv",
    "clean_input": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.uvt",
    "clean_script": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_clean.map",
    "clean_cube": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.lmv-clean",
    "clean_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.fits",
    "clean_pb_cube": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}-pbcor.lmv-sky",
    "clean_pb_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}-pbcor.fits",
}

_NARROWBAND = {
    "clean_input_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}.uvt",
    "clean_script_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}_clean.map",
    "clean_cube_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}.lmv-clean",
    "clean_fits_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}.fits",
    "clean_pb_cube_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}-pbcor.lmv-sky",
    "clean_pb_fits_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}-pbcor.fits",
}

_RESTORE = {
    "restore_uvt": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.uvt",
    "restore_cct": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.cct",
    "restore_clean": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.lmv-clean",
    "restore_output": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_restore.map",
    "restore_uvt_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}.uvt",
    "restore_cct_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}.cct",
    "restore_clean_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}.lmv-clean",
    "restore_output_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script_narrowband": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{lid_pair_filename}{selfcal}{contsub}_restore.map",
    "restore_uvt_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}.uvt",
    "restore_cct_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}.cct",
    "restore_clean_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}.lmv-clean",
    "restore_output_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script_line": "{root}/{config}/{lid_pair_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_restore.map",
    "line_uvt": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}_{window}{selfcal}{contsub}.uvt",
    "line_script": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}_{window}{selfcal}{contsub}_extract.map",
    "line_dirty_map": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}.lmv",
    "line_dirty_script": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_dirty.map",
    "line_clean_script": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}_clean.map",
    "line_clean_cube": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}.lmv-clean",
    "line_clean_fits": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}.fits",
    "line_clean_pb_cube": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}-pbcor.lmv-sky",
    "line_clean_pb_fits": "{root}/{config}/{window_folder}/{source_out}_{config}_{line}_{qn}{lid_suffix}{selfcal}{contsub}-pbcor.fits",
}


def _profile_naming(style: str) -> dict[str, str]:
    naming = {**_WIDEBAND, **_NARROWBAND, **_RESTORE}
    naming["narrowband_folder"] = "{root}/{config}/{lid_pair_folder}"
    if style == "propstar":
        naming = {
            key: value.replace("{root}/{config}/", "{root}/{config}config/")
            for key, value in naming.items()
        }
    return naming


def _check_style(style: str) -> str:
    selected = style.lower()
    if selected not in {"prodige", "propstar"}:
        raise ValueError("style must be 'prodige' or 'propstar'")
    return selected


def _write_new(path: Path, content: str, *, overwrite: bool) -> Path:
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def create_config(
    style: ConfigStyle = "prodige",
    filename: str | Path = "config.ini",
    *,
    catalogue: Literal["prodige", "propstar"] | None = None,
    catalogue_filename: str | Path | None = None,
    region_catalogue_filename: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Create an editable style-specific configuration in the current folder."""
    selected = _check_style(style)
    parser = ConfigParser()
    parser["project"] = {"style": selected, "base_dir": "."}
    parser["folders"] = {
        "uvt_dir": "uvts", "uvt_dir_out": "merged_uvts", "dir_sd": "30m",
        "inputdir": "raw_data",
    }
    selected_catalogue = catalogue or selected
    if selected_catalogue not in {"prodige", "propstar"}:
        raise ValueError("catalogue must be 'prodige' or 'propstar'")
    parser["catalogues"] = {
        "line_catalogue": str(
            catalogue_filename
            or {
            "prodige": "line_catalogue_prodige.csv",
            "propstar": "line_catalogue_propstar.csv",
            }[selected_catalogue]
        ),
        "source_catalogue": str(region_catalogue_filename or "region_catalogue.yml"),
    }
    parser["file_handling"] = {}
    parser["file_extensions"] = {"selfcal": "_sc", "uvsub": "_contsub"}
    parser["single_dish"] = {"telescope": "iram30m"}
    parser["gildas"] = {
        "execute": "true", "workdir": ".", "setup": "", "setup_file": "",
        "shell": "/bin/bash", "interactive": "false",
        "class": "class",
        "mapping": "mapping", "clic": "clic",
    }
    parser["continuum_subtraction"] = {
        "wideband_lo": "", "wideband_li": "", "wideband_ui": "", "wideband_uo": "",
    }
    parser["narrowband_channel_ranges"] = (
        _PRODIGE_NARROWBAND_RANGES.copy() if selected == "prodige" else {}
    )
    parser["narrowband"] = {"windows": "l009l048, l010l049"}
    parser["spectral_windows"] = {
        "narrowband_start": "l009",
        "narrowband_end": "l047",
        "lo_start": "l009",
        "li_start": "l023",
        "ui_start": "l032",
        "uo_start": "l040",
    }
    parser["imaging"] = {"wideband_windows": "lo, li, ui, uo", "include_narrowband": "true"}
    parser["cleaning"] = {
        "weighting": "natural", "threshold_factor": "5", "niter": "0",
        "primary_beam_correction": "true", "primary_beam_truncate": "20",
    }
    parser["naming"] = {"root": ".", **_profile_naming(selected)}
    from io import StringIO

    output = StringIO()
    parser.write(output)
    return _write_new(Path(filename).expanduser(), f"# Generated profile: {selected}\n\n{output.getvalue()}", overwrite=overwrite)


def create_line_catalogue(
    catalogue: Literal["prodige", "propstar"] = "prodige",
    filename: str | Path | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Copy a packaged starter line catalogue into the current folder."""
    selected = catalogue.lower()
    sources = {
        "prodige": "line_catalogue_MIOP.csv",
        "propstar": "line_catalogue_3mm.csv",
    }
    targets = {
        "prodige": "line_catalogue_prodige.csv",
        "propstar": "line_catalogue_propstar.csv",
    }
    if selected not in sources:
        raise ValueError("catalogue must be 'prodige' or 'propstar'")
    source = files("noema_combine").joinpath(sources[selected])
    target = Path(filename or targets[selected]).expanduser()
    return _write_new(target, source.read_text(), overwrite=overwrite)


def create_region_catalogue(
    filename: str | Path = "region_catalogue.yml",
    *,
    overwrite: bool = False,
) -> Path:
    """Copy the packaged starter source-region catalogue into the project."""
    source = files("noema_combine").joinpath("region_catalogue.yml")
    return _write_new(Path(filename).expanduser(), source.read_text(), overwrite=overwrite)


def create_project_files(
    style: ConfigStyle = "prodige",
    *,
    catalogue: Literal["prodige", "propstar"] | None = None,
    config_filename: str | Path = "config.ini",
    catalogue_filename: str | Path | None = None,
    region_catalogue_filename: str | Path | None = None,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Create a configuration and starter catalogues together.

    The return value remains ``(config_path, line_catalogue_path)`` for
    compatibility. The region catalogue is also copied to the configured
    ``region_catalogue_filename`` path.
    """
    selected_style = _check_style(style)
    selected_catalogue = catalogue or selected_style
    config = create_config(
        selected_style,
        config_filename,
        catalogue=selected_catalogue,
        catalogue_filename=catalogue_filename,
        region_catalogue_filename=region_catalogue_filename,
        overwrite=overwrite,
    )
    try:
        catalogue_path = create_line_catalogue(
            selected_catalogue, catalogue_filename, overwrite=overwrite
        )
        create_region_catalogue(
            region_catalogue_filename or "region_catalogue.yml",
            overwrite=overwrite,
        )
    except Exception:
        if not overwrite:
            config.unlink(missing_ok=True)
        raise
    return config, catalogue_path


__all__ = [
    "create_config",
    "create_line_catalogue",
    "create_region_catalogue",
    "create_project_files",
]
