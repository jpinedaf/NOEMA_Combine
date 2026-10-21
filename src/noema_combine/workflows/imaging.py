"""Dirty-image workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from ..config import Config, get_config
from ..continuum import normalize_window
from ..gildas import GildasResult
from ..naming import lid_pair_values
from .line import _find_line, _narrow_pair
from ..line_catalogue import lines_in_window
from ..imaging import (
    build_clean_image_script,
    build_dirty_image_script,
    build_restore_image_script,
)


@dataclass
class DirtyImageResult:
    """Paths and execution result for one dirty image."""

    source: str
    configuration: str
    window: str
    input_file: Path
    output_map: Path
    script_path: Path
    execution: GildasResult


@dataclass
class CleanImageResult:
    """Paths and execution result for one cleaned wideband image."""

    source: str
    configuration: str
    baseband: str
    window_kind: str
    input_file: Path
    cleaned_cube: Path
    cleaned_fits: Path
    primary_beam_cube: Path | None
    primary_beam_fits: Path | None
    script_path: Path
    execution: GildasResult


@dataclass
class LineImageResult:
    """Paths and execution results for one extracted-line image workflow."""

    source: str
    configuration: str
    line: str
    qn: str
    window: str
    input_file: Path
    dirty_map: Path | None
    clean_cube: Path | None
    clean_fits: Path | None
    primary_beam_cube: Path | None
    primary_beam_fits: Path | None
    dirty_script: Path | None
    clean_script: Path | None
    executions: list[GildasResult]


@dataclass
class RestoreImageResult:
    """Paths and execution result for one UV-restored image or cube."""

    source: str
    configuration: str
    product_type: str
    window: str
    window_kind: str
    line: str | None
    qn: str | None
    input_uv: Path
    clean_image: Path
    components: Path
    restored_cube: Path
    restored_fits: Path
    primary_beam_cube: Path | None
    primary_beam_fits: Path | None
    script_path: Path
    execution: GildasResult


def _render(naming, product: str, **values: object) -> Path:
    return Path(naming.render(product, **values)).expanduser()


def _source_out(cfg: Config, source: str) -> str:
    return cfg.region_catalogue.get(source, {}).get("source_out", source)


def make_dirty_images(
    source: str,
    configuration: str,
    windows: Iterable[str] | None = None,
    *,
    selfcal: bool = False,
    contsub: bool = False,
    execute: bool | None = None,
    config_file: str | None = None,
) -> list[DirtyImageResult]:
    """Generate and optionally execute dirty images for selected windows."""
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    source_out = _source_out(cfg, source)
    wideband = {normalize_window(value) for value in cfg.imaging_wideband_windows}
    narrowband_windows = list(cfg.narrowband_windows) if cfg.imaging_include_narrowband else []
    narrowband = set(narrowband_windows)
    available = wideband | narrowband
    selected = (
        list(windows)
        if windows is not None
        else list(cfg.imaging_wideband_windows) + narrowband_windows
    )
    canonical = [normalize_window(value) for value in selected]
    unknown = sorted(set(canonical) - available)
    if unknown:
        raise ValueError(f"Unknown imaging window(s): {', '.join(unknown)}")

    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    results: list[DirtyImageResult] = []
    for window in canonical:
        is_wideband = window in wideband
        pair = window if not is_wideband else ""
        pair_context = lid_pair_values(pair) if pair else {}
        folder_name = (
            "wideband"
            if is_wideband
            else pair_context.get("lid_pair_folder", pair)
        )
        values = {
            "source": source,
            "source_out": source_out,
            "config": configuration,
            "window": window,
            "window_upper": window.upper(),
            "window_folder": folder_name,
            "lid": window,
            "lid_pair": pair,
            **pair_context,
            "selfcal": cfg.selfcal_ext if selfcal else "",
            "contsub": cfg.uvsub_ext if contsub else "",
        }
        values["dirty_folder"] = str(_render(cfg.naming, "dirty_folder", **values))
        input_file = _render(cfg.naming, "dirty_input", **values)
        output_map = _render(cfg.naming, "dirty_map", **values)
        script_target = _render(cfg.naming, "dirty_script", **values)
        if execute is not False and not input_file.is_file():
            raise FileNotFoundError(f"Dirty-image input UVT not found: {input_file}")
        script = build_dirty_image_script(
            str(input_file),
            str(output_map.with_suffix("")),
            configuration=configuration,
        )
        execution = runner.run_mapping(
            script,
            expected_outputs=[output_map],
            keep_script=True,
        )
        script_target.parent.mkdir(parents=True, exist_ok=True)
        script_target.write_text(script)
        results.append(
            DirtyImageResult(
                source=source,
                configuration=configuration,
                window=window,
                input_file=input_file,
                output_map=output_map,
                script_path=script_target,
                execution=execution,
            )
        )
    return results


def make_clean_images(
    source: str,
    configuration: str,
    baseband: str = "all",
    *,
    windows: Iterable[str] | None = None,
    selfcal: bool = False,
    contsub: bool = False,
    keep_script: bool = True,
    execute: bool | None = None,
    config_file: str | None = None,
) -> list[CleanImageResult]:
    """Generate and optionally execute cleaned wideband or narrowband images.

    ``baseband`` is retained for compatibility. Use ``windows`` to process a
    mixed list of wideband and narrowband windows.
    """
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    source_out = _source_out(cfg, source)
    wideband = {normalize_window(value) for value in cfg.imaging_wideband_windows}
    narrowband = set(cfg.narrowband_windows) if cfg.imaging_include_narrowband else set()
    allowed = wideband | narrowband
    if windows is not None:
        selected = list(windows)
    else:
        selected = list(cfg.imaging_wideband_windows) if baseband == "all" else [baseband]
    selected = [normalize_window(value) for value in selected]
    unknown = sorted(set(selected) - allowed)
    if unknown:
        raise ValueError(f"Unknown wideband baseband(s): {', '.join(unknown)}")

    suffix_values = {
        "selfcal": cfg.selfcal_ext if selfcal else "",
        "contsub": cfg.uvsub_ext if contsub else "",
    }
    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    results: list[CleanImageResult] = []
    for window in selected:
        is_wideband = window in wideband
        window_kind = "wideband" if is_wideband else "narrowband"
        suffix = "" if is_wideband else "_narrowband"
        pair = "" if is_wideband else window
        pair_context = lid_pair_values(pair) if pair else {}
        values = {
            "source": source,
            "source_out": source_out,
            "config": configuration,
            "window": window,
            "window_upper": window.upper(),
            "lid": window,
            "lid_pair": pair,
            **pair_context,
            "window_folder": (
                "wideband"
                if is_wideband
                else pair_context.get("lid_pair_folder", pair)
            ),
            **suffix_values,
        }
        input_file = _render(cfg.naming, f"clean_input{suffix}", **values)
        cleaned_cube = _render(cfg.naming, f"clean_cube{suffix}", **values)
        cleaned_fits = _render(cfg.naming, f"clean_fits{suffix}", **values)
        primary_beam_cube = (
            _render(cfg.naming, f"clean_pb_cube{suffix}", **values)
            if cfg.cleaning_primary_beam
            else None
        )
        primary_beam_fits = (
            _render(cfg.naming, f"clean_pb_fits{suffix}", **values)
            if cfg.cleaning_primary_beam
            else None
        )
        script_path = _render(cfg.naming, f"clean_script{suffix}", **values)
        if execute is not False and not input_file.is_file():
            raise FileNotFoundError(f"Clean-image input UVT not found: {input_file}")
        output_name = str(cleaned_cube).removesuffix(".lmv-clean")
        script = build_clean_image_script(
            str(input_file),
            output_name,
            baseband=window,
            configuration=configuration,
            weighting=cfg.cleaning_weighting,
            threshold_factor=cfg.cleaning_threshold_factor,
            niter=cfg.cleaning_niter,
            primary_beam_correction=cfg.cleaning_primary_beam,
            primary_beam_truncate=cfg.cleaning_pb_truncate,
        )
        expected = [cleaned_fits]
        if primary_beam_fits is not None:
            expected.append(primary_beam_fits)
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script)
        try:
            execution = runner.run_mapping(
                script,
                expected_outputs=expected,
                keep_script=keep_script,
            )
        except Exception:
            if not keep_script:
                script_path.unlink(missing_ok=True)
            raise
        if not keep_script:
            script_path.unlink(missing_ok=True)
        results.append(
            CleanImageResult(
                source=source,
                configuration=configuration,
                baseband=window,
                window_kind=window_kind,
                input_file=input_file,
                cleaned_cube=cleaned_cube,
                cleaned_fits=cleaned_fits,
                primary_beam_cube=primary_beam_cube,
                primary_beam_fits=primary_beam_fits,
                script_path=script_path,
                execution=execution,
            )
        )
    return results


def make_line_images(
    source: str,
    configuration: str,
    line: str,
    qn: str,
    window: str,
    *,
    dirty: bool = True,
    clean: bool = True,
    selfcal: bool = False,
    contsub: bool = False,
    keep_script: bool = True,
    execute: bool | None = None,
    config_file: str | None = None,
) -> LineImageResult:
    """Create dirty and/or CLEAN images for one extracted spectral line."""
    if not dirty and not clean:
        raise ValueError("At least one of dirty or clean must be True")
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    index = _find_line(cfg, line, qn)
    requested = normalize_window(window)
    matches = lines_in_window(requested, config=cfg)
    matching = [
        row for row in matches
        if str(row["line"]) == str(cfg.line_name[index])
        and str(row["qn"]) == str(cfg.qn[index])
    ]
    if not matching:
        raise ValueError(f"Line {line} ({qn}) is not covered by window {window}")

    wideband = {normalize_window(value) for value in cfg.imaging_wideband_windows}
    is_wideband = requested in wideband
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
        "window_upper": canonical_window.upper(),
        "window_folder": "wideband"
        if is_wideband
        else pair_context["lid_pair_folder"],
        "lid": canonical_window,
        "lid_pair": "" if is_wideband else canonical_window,
        "line": str(cfg.line_name[index]),
        "qn": str(cfg.qn[index]),
        **pair_context,
        "selfcal": cfg.selfcal_ext if selfcal else "",
        "contsub": cfg.uvsub_ext if contsub else "",
    }
    input_file = _render(cfg.naming, "line_uvt", **values)
    dirty_map = _render(cfg.naming, "line_dirty_map", **values) if dirty else None
    clean_cube = _render(cfg.naming, "line_clean_cube", **values) if clean else None
    clean_fits = _render(cfg.naming, "line_clean_fits", **values) if clean else None
    primary_beam_cube = (
        _render(cfg.naming, "line_clean_pb_cube", **values)
        if clean and cfg.cleaning_primary_beam
        else None
    )
    primary_beam_fits = (
        _render(cfg.naming, "line_clean_pb_fits", **values)
        if clean and cfg.cleaning_primary_beam
        else None
    )
    dirty_script = _render(cfg.naming, "line_dirty_script", **values) if dirty else None
    clean_script = _render(cfg.naming, "line_clean_script", **values) if clean else None
    if execute is not False and not input_file.is_file():
        raise FileNotFoundError(f"Line-image input UVT not found: {input_file}")

    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    executions: list[GildasResult] = []

    if dirty and dirty_map is not None and dirty_script is not None:
        dirty_script_text = build_dirty_image_script(
            str(input_file), str(dirty_map).removesuffix(".lmv"), configuration=configuration
        )
        dirty_script.parent.mkdir(parents=True, exist_ok=True)
        dirty_script.write_text(dirty_script_text)
        try:
            executions.append(
                runner.run_mapping(
                    dirty_script_text,
                    expected_outputs=[dirty_map],
                    keep_script=keep_script,
                )
            )
        except Exception:
            if not keep_script:
                dirty_script.unlink(missing_ok=True)
            raise
        if not keep_script:
            dirty_script.unlink(missing_ok=True)

    if clean and clean_cube is not None and clean_fits is not None and clean_script is not None:
        output_name = str(clean_cube).removesuffix(".lmv-clean")
        clean_script_text = build_clean_image_script(
            str(input_file),
            output_name,
            baseband=canonical_window,
            configuration=configuration,
            weighting=cfg.cleaning_weighting,
            threshold_factor=cfg.cleaning_threshold_factor,
            niter=cfg.cleaning_niter,
            primary_beam_correction=cfg.cleaning_primary_beam,
            primary_beam_truncate=cfg.cleaning_pb_truncate,
            header_line=str(cfg.name_str[index]),
        )
        clean_script.parent.mkdir(parents=True, exist_ok=True)
        clean_script.write_text(clean_script_text)
        expected = [clean_fits]
        if primary_beam_fits is not None:
            expected.append(primary_beam_fits)
        try:
            executions.append(
                runner.run_mapping(
                    clean_script_text,
                    expected_outputs=expected,
                    keep_script=keep_script,
                )
            )
        except Exception:
            if not keep_script:
                clean_script.unlink(missing_ok=True)
            raise
        if not keep_script:
            clean_script.unlink(missing_ok=True)

    return LineImageResult(
        source=source,
        configuration=configuration,
        line=str(cfg.line_name[index]),
        qn=str(cfg.qn[index]),
        window=canonical_window,
        input_file=input_file,
        dirty_map=dirty_map,
        clean_cube=clean_cube,
        clean_fits=clean_fits,
        primary_beam_cube=primary_beam_cube,
        primary_beam_fits=primary_beam_fits,
        dirty_script=dirty_script,
        clean_script=clean_script,
        executions=executions,
    )


def restore_image(
    source: str,
    configuration: str,
    *,
    windows: Iterable[str] | None = None,
    line: str | None = None,
    qn: str | None = None,
    lid: str | None = None,
    product_type: Literal["continuum", "cube", "line"] = "continuum",
    selfcal: bool = False,
    contsub: bool = False,
    execute: bool | None = None,
    config_file: str | None = None,
) -> list[RestoreImageResult]:
    """Restore cleaned images or cubes with their UV data.

    ``continuum`` and ``cube`` process configured wideband or narrowband
    windows.  ``line`` processes one individual line and requires ``line``,
    ``qn`` and ``lid``.  Naming is fully controlled by the ``restore_*``
    templates in :class:`~noema_combine.naming.FileNaming`.
    """
    if product_type not in {"continuum", "cube", "line"}:
        raise ValueError("product_type must be 'continuum', 'cube', or 'line'")
    if product_type == "line":
        if not line or not qn or not lid:
            raise ValueError("line restoration requires line, qn, and lid")
        if windows is not None:
            raise ValueError("windows cannot be combined with product_type='line'")
        selected = [lid]
    else:
        if line is not None or qn is not None or lid is not None:
            raise ValueError("line, qn, and lid are only valid for product_type='line'")
        selected = list(windows) if windows is not None else None

    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    source_out = _source_out(cfg, source)
    wideband = {normalize_window(value) for value in cfg.imaging_wideband_windows}
    narrowband = (
        {normalize_window(value) for value in cfg.narrowband_windows}
        if cfg.imaging_include_narrowband
        else set()
    )
    if selected is None:
        selected = list(cfg.imaging_wideband_windows) + (
            list(cfg.narrowband_windows) if cfg.imaging_include_narrowband else []
        )
    selected = [normalize_window(value) for value in selected]
    if product_type != "line":
        unknown = sorted(set(selected) - (wideband | narrowband))
        if unknown:
            raise ValueError(f"Unknown restoration window(s): {', '.join(unknown)}")

    suffix_values = {
        "selfcal": cfg.selfcal_ext if selfcal else "",
        "contsub": cfg.uvsub_ext if contsub else "",
    }
    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    results: list[RestoreImageResult] = []
    for window in selected:
        is_line = product_type == "line"
        is_wideband = window in wideband
        window_kind = "wideband" if is_wideband else "narrowband"
        if is_line:
            template_suffix = "_line"
        elif is_wideband:
            template_suffix = ""
        else:
            template_suffix = "_narrowband"
        pair = "" if is_wideband else window
        pair_context = lid_pair_values(pair) if pair else {}
        values = {
            "source": source,
            "source_out": source_out,
            "config": configuration,
            "window": window,
            "window_upper": window.upper(),
            "window_folder": (
                "wideband"
                if is_wideband
                else pair_context.get("lid_pair_folder", pair)
            ),
            "lid": window,
            "lid_pair": pair,
            **pair_context,
            "line": line or "",
            "qn": qn or "",
            "product_type": product_type,
            **suffix_values,
        }
        input_uv = _render(cfg.naming, f"restore_uvt{template_suffix}", **values)
        components = _render(cfg.naming, f"restore_cct{template_suffix}", **values)
        clean_image = _render(cfg.naming, f"restore_clean{template_suffix}", **values)
        restored_cube = _render(cfg.naming, f"restore_output{template_suffix}", **values)
        restored_fits = _render(cfg.naming, f"restore_fits{template_suffix}", **values)
        primary_beam_cube = (
            _render(cfg.naming, f"restore_pb_cube{template_suffix}", **values)
            if cfg.cleaning_primary_beam
            else None
        )
        primary_beam_fits = (
            _render(cfg.naming, f"restore_pb_fits{template_suffix}", **values)
            if cfg.cleaning_primary_beam
            else None
        )
        script_path = _render(cfg.naming, f"restore_script{template_suffix}", **values)
        if execute is not False:
            for label, path in (("UV", input_uv), ("component", components), ("clean-image", clean_image)):
                if not path.is_file():
                    raise FileNotFoundError(f"Restore {label} input not found: {path}")
        output_name = str(restored_cube).removesuffix(".lmv-clean")
        script = build_restore_image_script(
            str(input_uv),
            str(clean_image),
            str(components),
            output_name,
            primary_beam_correction=cfg.cleaning_primary_beam,
            primary_beam_truncate=cfg.cleaning_pb_truncate,
        )
        expected = [restored_cube, restored_fits]
        if primary_beam_cube is not None:
            expected.append(primary_beam_cube)
        if primary_beam_fits is not None:
            expected.append(primary_beam_fits)
        execution = runner.run_mapping(script, expected_outputs=expected, keep_script=True)
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script)
        results.append(
            RestoreImageResult(
                source=source,
                configuration=configuration,
                product_type=product_type,
                window=window,
                window_kind=window_kind,
                line=line,
                qn=qn,
                input_uv=input_uv,
                clean_image=clean_image,
                components=components,
                restored_cube=restored_cube,
                restored_fits=restored_fits,
                primary_beam_cube=primary_beam_cube,
                primary_beam_fits=primary_beam_fits,
                script_path=script_path,
                execution=execution,
            )
        )
    return results
