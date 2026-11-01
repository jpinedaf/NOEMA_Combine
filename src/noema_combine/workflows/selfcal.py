"""Self-calibration application workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from ..config import Config, get_config
from ..gildas import GildasResult
from ..naming import lid_pair_values
from ..selfcal import build_selfcal_init, build_selfcal_script


@dataclass
class SelfcalResult:
    """Paths and execution metadata for one self-calibration operation."""

    source: str
    configuration: str
    window: str
    window_kind: str
    input_file: Path
    gain_file: Path
    output_file: Path
    script_path: Path
    init_path: Path
    execution: GildasResult


def _window_number(value: str) -> int:
    match = re.fullmatch(r"l0*(\d+)", value.strip().lower())
    if match is None:
        raise ValueError(f"Invalid narrowband window: {value}")
    return int(match.group(1))


def _pair_start(value: str) -> int:
    match = re.fullmatch(r"l0*(\d+)l\d+", value.strip().lower())
    if match is None:
        raise ValueError(f"Invalid narrowband window: {value}")
    return int(match.group(1))


def _windows_for_baseband(cfg: Config, baseband: str) -> list[str]:
    starts = cfg.spectral_window_starts
    if baseband not in starts:
        raise ValueError(f"Unknown baseband: {baseband}")
    ordered = sorted(starts.items(), key=lambda item: item[1])
    start = starts[baseband]
    following = [number for name, number in ordered if number > start]
    end = (min(following) - 1) if following else cfg.spectral_narrowband_end
    return [
        window for window in cfg.narrowband_windows
        if start <= _pair_start(window) <= end
    ]


def apply_selfcal_solutions(
    source: str,
    configuration: str,
    *,
    basebands: str | list[str] | tuple[str, ...] | None = None,
    windows: str | list[str] | tuple[str, ...] | None = None,
    execute: bool | None = None,
    keep_script: bool = True,
    config_file: str | None = None,
) -> list[SelfcalResult]:
    """Apply wideband self-calibration gains and optionally narrowband gains.

    When ``windows`` is omitted, all narrowband windows belonging to the
    selected basebands are processed.  Supplying ``windows`` limits the
    narrowband operations while the selected wideband operations remain.
    """
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    allowed = tuple(cfg.spectral_window_starts)
    if basebands is None:
        selected_basebands = list(allowed)
    elif isinstance(basebands, str):
        selected_basebands = [basebands]
    else:
        selected_basebands = list(basebands)
    selected_basebands = [value.strip().lower() for value in selected_basebands]
    unknown = sorted(set(selected_basebands) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown baseband(s): {', '.join(unknown)}")
    if windows is None:
        selected_windows = {
            window for baseband in selected_basebands
            for window in _windows_for_baseband(cfg, baseband)
        }
    elif isinstance(windows, str):
        selected_windows = {windows.strip().lower()}
    else:
        selected_windows = {value.strip().lower() for value in windows}
    available = set(cfg.narrowband_windows)
    unknown_windows = sorted(selected_windows - available)
    if unknown_windows:
        raise ValueError(f"Unknown narrowband window(s): {', '.join(unknown_windows)}")
    baseband_windows = {
        baseband: set(_windows_for_baseband(cfg, baseband))
        for baseband in selected_basebands
    }
    covered_windows = (
        set().union(*baseband_windows.values()) if baseband_windows else set()
    )
    unassigned = sorted(selected_windows - covered_windows)
    if unassigned:
        raise ValueError(
            "Narrowband window(s) are not covered by the selected baseband(s): "
            + ", ".join(unassigned)
        )

    source_out = cfg.region_catalogue.get(source, {}).get("source_out", source)
    results: list[SelfcalResult] = []
    for baseband in selected_basebands:
        values = {
            "source": source, "source_out": source_out, "config": configuration,
            "window": baseband, "window_folder": "wideband",
            "selfcal": cfg.selfcal_ext, "contsub": cfg.uvsub_ext,
        }
        input_file = Path(cfg.naming.render("selfcal_input_wideband", **values))
        gain_file = Path(cfg.naming.render("selfcal_gain_wideband", **values))
        output_file = Path(cfg.naming.render("selfcal_output_wideband", **values))
        results.append(_run_selfcal(
            cfg, source, configuration, baseband, "wideband", input_file,
            gain_file, output_file, values, execute, keep_script,
        ))

    for window in sorted(selected_windows):
        pair = lid_pair_values(window)
        values = {
            "source": source, "source_out": source_out, "config": configuration,
            "window": window, "window_folder": pair["lid_pair_folder"],
            "lid": window, **pair, "selfcal": cfg.selfcal_ext, "contsub": cfg.uvsub_ext,
        }
        input_file = Path(cfg.naming.render("selfcal_input_narrowband", **values))
        gain_values = dict(values, window=next(
            (baseband for baseband in selected_basebands
             if window in baseband_windows[baseband]),
            selected_basebands[0],
        ), window_folder="wideband")
        gain_file = Path(cfg.naming.render("selfcal_gain_wideband", **gain_values))
        output_file = Path(cfg.naming.render("selfcal_output_narrowband", **values))
        results.append(_run_selfcal(
            cfg, source, configuration, window, "narrowband", input_file,
            gain_file, output_file, values, execute, keep_script,
        ))
    return results


def _run_selfcal(
    cfg: Config, source: str, configuration: str, window: str, window_kind: str,
    input_file: Path, gain_file: Path, output_file: Path, values: dict[str, object],
    execute: bool | None, keep_script: bool,
) -> SelfcalResult:
    script_path = Path(cfg.naming.render("selfcal_script", **values))
    script = build_selfcal_script()
    init_path = script_path.parent / "uv_cal.init"
    flag_uncalibrated = configuration.upper() not in {"A", "C", "ACD"}
    runner_execute = cfg.gildas_execute if execute is None else execute
    if runner_execute:
        if not input_file.is_file():
            raise FileNotFoundError(f"Self-calibration input UVT not found: {input_file}")
        if not gain_file.is_file():
            raise FileNotFoundError(f"Self-calibration gain UVT not found: {gain_file}")
    init_path.parent.mkdir(parents=True, exist_ok=True)
    init_path.write_text(build_selfcal_init(
        str(input_file), str(gain_file), str(output_file),
        flag_uncalibrated=flag_uncalibrated,
    ))
    script_path.write_text(script)
    runner_kwargs = {"workdir": str(script_path.parent)}
    if execute is not None:
        runner_kwargs["execute"] = execute
    runner = cfg.make_gildas_runner(**runner_kwargs)
    try:
        execution = runner.run_mapping(
            script, expected_outputs=[output_file], keep_script=keep_script,
        )
    except Exception:
        if not keep_script:
            script_path.unlink(missing_ok=True)
            init_path.unlink(missing_ok=True)
        raise
    if not keep_script:
        script_path.unlink(missing_ok=True)
        init_path.unlink(missing_ok=True)
    return SelfcalResult(
        source=source, configuration=configuration, window=window,
        window_kind=window_kind, input_file=input_file, gain_file=gain_file,
        output_file=output_file, script_path=script_path, init_path=init_path,
        execution=execution,
    )


__all__ = ["SelfcalResult", "apply_selfcal_solutions"]
