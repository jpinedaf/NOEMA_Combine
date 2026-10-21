"""Wideband continuum-subtraction workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config, get_config
from ..continuum import (
    build_continuum_subtraction_script,
    build_narrowband_continuum_subtraction_script,
    normalize_window,
    resolve_channel_range,
)
from ..gildas import GildasResult
from ..naming import lid_pair_values


@dataclass
class ContinuumSubtractionResult:
    """Files and execution results produced by continuum subtraction."""

    source: str
    configuration: str
    lid: str
    input_file: Path
    output_file: Path
    continuum_file: Path | None
    range_file: Path | None
    filter_file: Path | None
    scripts: list[Path]
    executions: list[GildasResult]


@dataclass
class NarrowbandSubtractionResult:
    """Files and execution result for one narrowband window."""

    source: str
    configuration: str
    window: str
    input_file: Path
    output_file: Path
    script_path: Path
    channel_range: str | None
    execution: GildasResult


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _read_optional_file(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    value = path.read_text().strip()
    return value or None


def _render(naming, product: str, **values: object) -> Path:
    return _path(naming.render(product, **values))


def _build_continuum_table_script(
    input_file: str,
    output_file: str,
    channel_range: str | None,
) -> str:
    lines = [
        "sic message mapping s-i",
        f'let name "{input_file.removesuffix(".uvt")}"',
        "let type uvt",
        "go setup",
    ]
    if channel_range:
        lines.append(f"uv_filter /range {channel_range} channel")
    lines.extend(
        [
            "uv_cont",
            f'write uv "{output_file}" new',
            "sic message mapping s+i",
            "exit",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_plot_script(
    cube_file: str,
    plot_file: str,
    channel_range: str | None,
) -> str:
    window = channel_range or "0 10"
    return "\n".join(
        [
            "sic message class s-i",
            "file out continuum_plot.30m single /over",
            f'lmv "{cube_file}"',
            "file in continuum_plot.30m",
            "set match 0",
            "set range -0.5 0.5 -0.5 0.5",
            "find",
            "average /resample /nocheck position /weight equal",
            "set unit c f",
            f"set window {window}",
            "plot",
            "draw window /pen 1",
            f'hardcopy "{plot_file}" /geometry 1000p 0.8r /device PNG COLOR /FITPAGE /over',
            "sic message class s+i",
            "exit",
        ]
    ) + "\n"


def _build_cube_script(input_file: str, cube_file: str) -> str:
    cube_name = cube_file.removesuffix(".lmv-clean")
    return "\n".join(
        [
            f'modify "{input_file}"',
            f'let name "{cube_name}"',
            "let type uvt",
            "go setup",
            "go uvmap",
            "go view",
            f'define header H "{cube_name}.lmv" read',
            "let ares 4*'H%noise'",
            "let nmajor 5000",
            "go clean",
            "exit",
        ]
    ) + "\n"


def make_continuum_subtraction(
    source: str,
    configuration: str,
    lid: str,
    *,
    channel_range: str | None = None,
    range_file: str | Path | None = None,
    filter_channels: str | None = None,
    no_cube: bool = False,
    make_continuum: bool = False,
    make_plot: bool = False,
    execute: bool | None = None,
    config_file: str | None = None,
) -> ContinuumSubtractionResult:
    """Generate and optionally execute a wideband subtraction workflow."""
    window = normalize_window(lid)
    if window not in {"lo", "li", "ui", "uo"}:
        raise ValueError("lid must be one of: lo, li, ui, uo")
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    naming = cfg.naming
    values = {"source": source, "config": configuration, "lid": lid, "lid_lower": window}
    input_file = _render(naming, "continuum_input", **values)
    output_file = _render(
        naming, "continuum_subtracted_file", contsub=cfg.uvsub_ext, **values
    )
    continuum_file = (
        _render(naming, "continuum_file", **values) if make_continuum else None
    )
    configured_range_file = _render(naming, "continuum_range_file", **values)
    selected_range_file = _path(range_file) if range_file else configured_range_file
    selected_range = resolve_channel_range(
        window,
        channel_range=channel_range,
        range_file=selected_range_file,
        config=cfg,
    )
    configured_filter_file = _render(naming, "continuum_filter_file", **values)
    selected_filter_file = configured_filter_file if configured_filter_file.is_file() else None
    selected_filter = filter_channels or _read_optional_file(selected_filter_file)
    if execute is not False and not input_file.is_file():
        raise FileNotFoundError(f"Continuum input UVT not found: {input_file}")

    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    scripts: list[Path] = []
    executions: list[GildasResult] = []
    main_script = build_continuum_subtraction_script(
        str(input_file), str(output_file), channel_range=selected_range, filter_channels=selected_filter
    )
    main_result = runner.run_mapping(
        main_script,
        expected_outputs=[output_file],
    )
    scripts.append(main_result.script_path)
    executions.append(main_result)

    if make_continuum and continuum_file is not None:
        table_result = runner.run_mapping(
            _build_continuum_table_script(str(input_file), str(continuum_file), selected_range),
            expected_outputs=[continuum_file],
        )
        scripts.append(table_result.script_path)
        executions.append(table_result)

    if not no_cube:
        cube_file = _render(naming, "continuum_cube", **values)
        cube_result = runner.run_mapping(
            _build_cube_script(str(output_file), str(cube_file)),
            expected_outputs=[cube_file],
        )
        scripts.append(cube_result.script_path)
        executions.append(cube_result)

    if make_plot:
        plot_file = _render(naming, "continuum_plot", **values)
        plot_result = runner.run_class(
            _build_plot_script(str(_render(naming, "continuum_cube", **values)), str(plot_file), selected_range),
            expected_outputs=[plot_file],
        )
        scripts.append(plot_result.script_path)
        executions.append(plot_result)

    return ContinuumSubtractionResult(
        source=source,
        configuration=configuration,
        lid=lid,
        input_file=input_file,
        output_file=output_file,
        continuum_file=continuum_file,
        range_file=selected_range_file if selected_range_file.is_file() else None,
        filter_file=selected_filter_file,
        scripts=scripts,
        executions=executions,
    )


def make_narrowband_continuum_subtraction(
    source: str,
    configuration: str,
    spectral_windows: list[str] | tuple[str, ...] | None = None,
    *,
    channel_range: str | None = None,
    channel_ranges: dict[str, str] | None = None,
    execute: bool | None = None,
    config_file: str | None = None,
) -> list[NarrowbandSubtractionResult]:
    """Generate and optionally execute narrowband subtraction scripts."""
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    source_out = cfg.region_catalogue.get(source, {}).get("source_out", source)
    requested = spectral_windows or cfg.narrowband_windows
    windows = [normalize_window(window) for window in requested]
    if channel_range is not None and len(windows) != 1:
        raise ValueError(
            "channel_range can only be used when one narrowband window is requested"
        )
    if channel_range is not None and channel_ranges:
        raise ValueError("Use either channel_range or channel_ranges, not both")
    configured = {normalize_window(key): value for key, value in (channel_ranges or {}).items()}
    unknown = sorted(set(windows) - set(cfg.narrowband_windows))
    if unknown:
        raise ValueError(f"Unknown narrowband spectral window(s): {', '.join(unknown)}")

    naming = cfg.naming
    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    results: list[NarrowbandSubtractionResult] = []
    for window in windows:
        pair_context = lid_pair_values(window)
        folder = _render(
            naming,
            "narrowband_folder",
            source=source,
            config=configuration,
            lid=window,
            **pair_context,
        )
        values = {
            "source": source,
            "source_out": source_out,
            "config": configuration,
            "lid": window,
            "lid_pair": window,
            **pair_context,
            "narrowband_folder": str(folder),
        }
        input_file = _render(naming, "narrowband_input", **values)
        output_file = _render(
            naming, "narrowband_output", contsub=cfg.uvsub_ext, **values
        )
        script_target = _render(naming, "narrowband_script", **values)
        selected_range = resolve_channel_range(
            window,
            channel_range=channel_range if channel_range is not None else configured.get(window),
            narrowband=True,
            config=cfg,
        )
        if execute is not False and not input_file.is_file():
            raise FileNotFoundError(f"Narrowband input UVT not found: {input_file}")
        script = build_narrowband_continuum_subtraction_script(
            str(input_file),
            str(output_file),
            channel_range=selected_range,
        )
        execution = runner.run_mapping(
            script,
            expected_outputs=[output_file],
            keep_script=True,
        )
        # The runner owns the generated temporary script; copy its path into
        # the configured script location for the script-only workflow.
        script_target.parent.mkdir(parents=True, exist_ok=True)
        script_target.write_text(script)
        results.append(
            NarrowbandSubtractionResult(
                source=source,
                configuration=configuration,
                window=window,
                input_file=input_file,
                output_file=output_file,
                script_path=script_target,
                channel_range=selected_range,
                execution=execution,
            )
        )
    return results
