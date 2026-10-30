"""Workflow for imaging line cubes after NOEMA/single-dish combination."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config, get_config
from ..continuum import normalize_window
from ..gildas import GildasResult
from ..line_catalogue import lines_in_window
from ..merged_line import (
    build_merged_line_image_script,
    build_merged_line_prepare_script,
)
from ..naming import lid_pair_values
from .line import _find_line, _narrow_pair, _velocity_range


@dataclass
class MergedLineImageResult:
    """Paths and execution results for one merged line-cube workflow."""

    source: str
    configuration: str
    line: str
    qn: str
    window: str
    input_file: Path
    single_dish_table: Path
    prepared_uvt: Path
    merged_uvt: Path
    dirty_map: Path | None
    clean_cube: Path | None
    clean_fits: Path | None
    primary_beam_cube: Path | None
    primary_beam_fits: Path | None
    prepare_script: Path
    image_script: Path
    executions: list[GildasResult]


def _render(naming, product: str, **values: object) -> Path:
    return Path(naming.render(product, **values)).expanduser()


def _source_out(cfg: Config, source: str) -> str:
    return cfg.region_catalogue.get(source, {}).get("source_out", source)


def make_merged_line_images(
    source: str,
    configuration: str,
    line: str,
    qn: str,
    window: str,
    *,
    selfcal: bool = True,
    contsub: bool = True,
    velocity_range: tuple[float, float] | None = None,
    velocity_resolution: float | None = None,
    dirty: bool = True,
    clean: bool = True,
    method: str = "SDI",
    niter: int = 5000,
    keep_script: bool = True,
    execute: bool | None = None,
    config_file: str | None = None,
) -> MergedLineImageResult:
    """Prepare, merge, and image one line with single-dish data."""
    if configuration.upper() not in {"CD", "ACD"}:
        raise ValueError("merged line imaging requires configuration 'CD' or 'ACD'")
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    index = _find_line(cfg, line, qn)
    requested = normalize_window(window)
    matches = lines_in_window(requested, config=cfg)
    matching = [
        row for row in matches
        if str(row["line"]) == str(cfg.line_name[index])
        and (str(row["qn"]) == str(cfg.qn[index]) or str(row["qn"]) == str(cfg.qn_str[index]))
    ]
    if not matching:
        raise ValueError(f"Line {line} ({qn}) is not covered by window {window}")

    is_wideband = requested in {key.lower() for key in cfg.spectral_window_starts}
    canonical_window = requested if is_wideband else _narrow_pair(
        matching[0]["narrowband_window"], cfg
    )
    pair_context = {} if is_wideband else lid_pair_values(canonical_window)
    source_out = _source_out(cfg, source)
    values = {
        "source": source,
        "source_out": source_out,
        "config": configuration,
        "window": canonical_window,
        "window_folder": "wideband" if is_wideband else pair_context["lid_pair_folder"],
        "lid": canonical_window,
        "lid_pair": canonical_window if not is_wideband else "",
        "line": str(cfg.line_name[index]),
        "qn": str(cfg.qn[index]),
        "selfcal": cfg.selfcal_ext if selfcal else "",
        "contsub": cfg.uvsub_ext if contsub else "",
        **pair_context,
    }
    input_template = "clean_input" if is_wideband else "clean_input_narrowband"
    input_file = _render(cfg.naming, input_template, **values)
    prepared_uvt = _render(cfg.naming, "merged_line_uvt", **values)
    single_dish_table = _render(
        cfg.naming,
        "merged_line_single_dish",
        **{**values, "sd_root": cfg.dir_sd, "sd_ext": cfg.file_extensions_sd},
    )
    merged_uvt = _render(cfg.naming, "merged_line_merged_uvt", **values)
    dirty_map = _render(cfg.naming, "merged_line_dirty_map", **values) if dirty else None
    clean_cube = _render(cfg.naming, "merged_line_clean_cube", **values) if clean else None
    clean_fits = _render(cfg.naming, "merged_line_clean_fits", **values) if clean else None
    pb_cube = (
        _render(cfg.naming, "merged_line_clean_pb_cube", **values)
        if clean and cfg.cleaning_primary_beam else None
    )
    pb_fits = (
        _render(cfg.naming, "merged_line_clean_pb_fits", **values)
        if clean and cfg.cleaning_primary_beam else None
    )
    prepare_script = _render(cfg.naming, "merged_line_prepare_script", **values)
    image_script = _render(cfg.naming, "merged_line_image_script", **values)
    if execute is not False:
        for label, path in (("line UVT", input_file), ("single-dish table", single_dish_table)):
            if not path.is_file():
                raise FileNotFoundError(f"Merged line {label} not found: {path}")

    vlsr = float(cfg.region_catalogue[source]["Vlsr"])
    selected_range = _velocity_range(cfg, source, index, velocity_range, None)
    resolution = (
        3.0 if is_wideband else 0.1
    ) if velocity_resolution is None else velocity_resolution
    if resolution <= 0:
        raise ValueError("velocity_resolution must be positive")
    prepare_text = build_merged_line_prepare_script(
        str(input_file), str(prepared_uvt),
        line_name=str(cfg.line_name[index]),
        rest_frequency_mhz=cfg.freq[index],
        velocity_range=selected_range,
        systemic_velocity=vlsr,
        velocity_resolution=resolution,
    )
    output_name = str(clean_cube or merged_uvt).removesuffix(".lmv-clean")
    support_mask = Path(f"{output_name}.msk").is_file()
    image_text = build_merged_line_image_script(
        str(prepared_uvt), str(single_dish_table), str(merged_uvt), output_name,
        configuration=configuration,
        map_size=(2000, 2000) if configuration.upper() == "ACD" else (500, 500),
        map_cell=(0.035, 0.035) if configuration.upper() == "ACD" else (0.17, 0.17),
        niter=niter,
        method=method,
        support_mask=support_mask,
        dirty=dirty,
        clean=clean,
    )
    prepare_script.parent.mkdir(parents=True, exist_ok=True)
    image_script.parent.mkdir(parents=True, exist_ok=True)
    prepare_script.write_text(prepare_text)
    image_script.write_text(image_text)
    runner = cfg.make_gildas_runner(**({} if execute is None else {"execute": execute}))
    executions: list[GildasResult] = []
    try:
        executions.append(runner.run_mapping(prepare_text, expected_outputs=[prepared_uvt], keep_script=keep_script))
        expected = [merged_uvt]
        if dirty_map is not None:
            expected.append(dirty_map)
        if clean_fits is not None:
            expected.append(clean_fits)
        if pb_fits is not None:
            expected.append(pb_fits)
        executions.append(runner.run_mapping(image_text, expected_outputs=expected, keep_script=keep_script))
    except Exception:
        if not keep_script:
            prepare_script.unlink(missing_ok=True)
            image_script.unlink(missing_ok=True)
        raise
    if not keep_script:
        prepare_script.unlink(missing_ok=True)
        image_script.unlink(missing_ok=True)
    return MergedLineImageResult(
        source=source, configuration=configuration, line=str(cfg.line_name[index]),
        qn=str(cfg.qn[index]), window=canonical_window, input_file=input_file,
        single_dish_table=single_dish_table, prepared_uvt=prepared_uvt, merged_uvt=merged_uvt,
        dirty_map=dirty_map, clean_cube=clean_cube, clean_fits=clean_fits,
        primary_beam_cube=pb_cube, primary_beam_fits=pb_fits,
        prepare_script=prepare_script, image_script=image_script, executions=executions,
    )


__all__ = ["MergedLineImageResult", "make_merged_line_images"]
