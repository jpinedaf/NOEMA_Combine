"""Workflow for extracting individual spectral lines from UV tables."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import re

from ..config import Config, get_config
from ..continuum import normalize_window
from ..gildas import GildasResult
from ..line_catalogue import lines_in_window
from ..line_extraction import build_line_extraction_script
from ..naming import lid_pair_values


@dataclass
class LineExtractionResult:
    """Paths and execution metadata for one extracted line UV table."""

    source: str
    configuration: str
    line: str
    qn: str
    window: str
    input_file: Path
    output_file: Path
    script_path: Path
    velocity_range: tuple[float, float]
    rest_frequency_mhz: float
    execution: GildasResult


def _key(value: object) -> str:
    return (
        str(value).strip().lower().replace("\\", "").replace("p", "+")
        .replace("_", "-").replace(" ", "")
    )


def _find_line(cfg: Config, line: str, qn: str) -> int:
    matches: list[int] = []
    for index, name in enumerate(cfg.line_name):
        if _key(name) != _key(line):
            continue
        if _key(cfg.qn[index]) == _key(qn) or _key(cfg.qn_str[index]) == _key(qn):
            matches.append(index)
    if not matches:
        raise ValueError(f"Line not found in the catalogue: {line} ({qn})")
    if len(matches) > 1:
        raise ValueError(f"Line is not unique in the catalogue: {line} ({qn})")
    return matches[0]


def _narrow_pair(value: str, cfg: Config) -> str:
    normalized = normalize_window(value)
    if re.fullmatch(r"l\d+l\d+", normalized):
        return normalized
    match = re.fullmatch(r"l(\d+)", normalized)
    if match:
        start = int(match.group(1))
        for window in cfg.narrowband_windows:
            if window.startswith(f"l{start:03d}l"):
                return window
    raise ValueError(f"Unknown narrowband window: {value}")


def _velocity_range(
    cfg: Config,
    source: str,
    index: int,
    explicit: tuple[float, float] | None,
    dv: float | None,
) -> tuple[float, float]:
    if explicit is not None:
        if len(explicit) != 2 or explicit[0] >= explicit[1]:
            raise ValueError("velocity_range must be an increasing (minimum, maximum) pair")
        return float(explicit[0]), float(explicit[1])
    try:
        vlsr = float(cfg.region_catalogue[source]["Vlsr"])
    except KeyError as exc:
        raise ValueError(f"Region '{source}' not found in region_catalogue") from exc
    width = float(dv) if dv is not None else float(cfg.vel_width[index])
    if width <= 0:
        raise ValueError("dv and catalogue line widths must be positive")
    return vlsr - width, vlsr + width


def extract_line(
    source: str,
    configuration: str,
    line: str,
    qn: str,
    window: str,
    *,
    selfcal: bool = False,
    contsub: bool = False,
    velocity_range: tuple[float, float] | None = None,
    dv: float | None = None,
    keep_script: bool = True,
    execute: bool | None = None,
    config_file: str | None = None,
) -> LineExtractionResult:
    """Extract one catalogue line from a configured wide or narrow window."""
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    index = _find_line(cfg, line, qn)
    requested = normalize_window(window)
    matches = lines_in_window(requested, config=cfg)
    matching = [row for row in matches if _key(row["line"]) == _key(cfg.line_name[index]) and (
        _key(row["qn"]) == _key(cfg.qn[index])
        or _key(row["qn"]) == _key(cfg.qn_str[index])
    )]
    if not matching:
        raise ValueError(f"Line {line} ({qn}) is not covered by window {window}")

    is_wideband = requested in {key.lower() for key in cfg.spectral_window_starts}
    if is_wideband:
        canonical_window = requested
        pair_context: dict[str, str] = {}
        folder = "wideband"
    else:
        canonical_window = _narrow_pair(matching[0]["narrowband_window"], cfg)
        pair_context = lid_pair_values(canonical_window)
        folder = pair_context["lid_pair_folder"]

    source_out = cfg.region_catalogue.get(source, {}).get("source_out", source)
    values = {
        "source": source,
        "source_out": source_out,
        "config": configuration,
        "window": canonical_window,
        "window_upper": canonical_window.upper(),
        "window_folder": folder,
        "lid": canonical_window,
        "lid_pair": canonical_window if not is_wideband else "",
        **pair_context,
        "line": str(cfg.line_name[index]),
        "qn": str(cfg.qn[index]),
        "selfcal": cfg.selfcal_ext if selfcal else "",
        "contsub": cfg.uvsub_ext if contsub else "",
    }
    input_template = "clean_input" if is_wideband else "clean_input_narrowband"
    input_file = Path(cfg.naming.render(input_template, **values)).expanduser()
    output_file = Path(cfg.naming.render("line_uvt", **values)).expanduser()
    script_path = Path(cfg.naming.render("line_script", **values)).expanduser()
    selected_range = _velocity_range(cfg, source, index, velocity_range, dv)
    if execute is not False and not input_file.is_file():
        raise FileNotFoundError(f"Line-extraction input UVT not found: {input_file}")

    script = build_line_extraction_script(
        str(input_file),
        str(output_file),
        line_name=str(cfg.name_str[index]),
        rest_frequency_mhz=str(Decimal(str(cfg.freq[index])) * 1000),
        velocity_range=selected_range,
    )
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script)
    runner_kwargs = {} if execute is None else {"execute": execute}
    runner = cfg.make_gildas_runner(**runner_kwargs)
    try:
        execution = runner.run_mapping(
            script,
            expected_outputs=[output_file],
            keep_script=keep_script,
        )
    except Exception:
        if not keep_script:
            script_path.unlink(missing_ok=True)
        raise
    if not keep_script:
        script_path.unlink(missing_ok=True)
    return LineExtractionResult(
        source=source,
        configuration=configuration,
        line=str(cfg.line_name[index]),
        qn=str(cfg.qn[index]),
        window=canonical_window,
        input_file=input_file,
        output_file=output_file,
        script_path=script_path,
        velocity_range=selected_range,
        rest_frequency_mhz=float(cfg.freq[index]) * 1000.0,
        execution=execution,
    )


__all__ = ["LineExtractionResult", "extract_line"]
