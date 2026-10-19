"""Helpers for creating editable project configuration files."""

from __future__ import annotations

from configparser import ConfigParser
from importlib.resources import files
from pathlib import Path
from typing import Literal


ConfigStyle = Literal["prodige", "propstar"]


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
    "clean_input_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.uvt",
    "clean_script_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_clean.map",
    "clean_cube_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.lmv-clean",
    "clean_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.fits",
    "clean_pb_cube_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}-pbcor.lmv-sky",
    "clean_pb_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}-pbcor.fits",
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
    "restore_uvt_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.uvt",
    "restore_cct_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.cct",
    "restore_clean_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.lmv-clean",
    "restore_output_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_restore.map",
    "restore_uvt_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}.uvt",
    "restore_cct_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}.cct",
    "restore_clean_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}.lmv-clean",
    "restore_output_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_restore.map",
}


def _profile_naming(style: str) -> dict[str, str]:
    naming = {**_WIDEBAND, **_NARROWBAND, **_RESTORE}
    naming["narrowband_folder"] = "{root}/{config}/narrowband/{lid_pair}"
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
    catalogue: Literal["3mm", "miop"] | None = None,
    catalogue_filename: str | Path | None = None,
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
    selected_catalogue = catalogue or ("miop" if selected == "prodige" else "3mm")
    if selected_catalogue not in {"3mm", "miop"}:
        raise ValueError("catalogue must be '3mm' or 'miop'")
    parser["catalogues"] = {
        "line_catalogue": str(
            catalogue_filename
            or {
                "3mm": "line_catalogue_3mm.csv",
                "miop": "line_catalogue_MIOP.csv",
            }[selected_catalogue]
        ),
        "source_catalogue": "region_catalogue.yml",
    }
    parser["file_handling"] = {}
    parser["file_extensions"] = {"selfcal": "_sc", "uvsub": "_contsub"}
    parser["single_dish"] = {"telescope": "iram30m"}
    parser["gildas"] = {
        "execute": "true", "workdir": ".", "class": "class",
        "mapping": "mapping", "clic": "clic",
    }
    parser["continuum_subtraction"] = {
        "wideband_lo": "", "wideband_li": "", "wideband_ui": "", "wideband_uo": "",
    }
    parser["narrowband_channel_ranges"] = {}
    parser["narrowband"] = {"windows": "l009l048, l010l049"}
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
    catalogue: Literal["3mm", "miop"] = "3mm",
    filename: str | Path | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Copy a packaged starter line catalogue into the current folder."""
    selected = catalogue.lower()
    names = {"3mm": "line_catalogue_3mm.csv", "miop": "line_catalogue_MIOP.csv"}
    if selected not in names:
        raise ValueError("catalogue must be '3mm' or 'miop'")
    source = files("noema_combine").joinpath(names[selected])
    target = Path(filename or names[selected]).expanduser()
    return _write_new(target, source.read_text(), overwrite=overwrite)


def create_project_files(
    style: ConfigStyle = "prodige",
    *,
    catalogue: Literal["3mm", "miop"] | None = None,
    config_filename: str | Path = "config.ini",
    catalogue_filename: str | Path | None = None,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Create a configuration and starter line catalogue together."""
    selected_style = _check_style(style)
    selected_catalogue = catalogue or ("miop" if selected_style == "prodige" else "3mm")
    config = create_config(
        selected_style,
        config_filename,
        catalogue=selected_catalogue,
        catalogue_filename=catalogue_filename,
        overwrite=overwrite,
    )
    try:
        catalogue_path = create_line_catalogue(
            selected_catalogue, catalogue_filename, overwrite=overwrite
        )
    except Exception:
        if not overwrite:
            config.unlink(missing_ok=True)
        raise
    return config, catalogue_path


__all__ = ["create_config", "create_line_catalogue", "create_project_files"]
