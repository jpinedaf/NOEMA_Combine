"""Export narrowband UV tables to CASA UVFITS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config, get_config
from ..gildas import GildasResult
from ..naming import lid_pair_values
from ..uvfits import build_uvfits_export_script


@dataclass
class UVFITSExportResult:
    source: str
    configuration: str
    window: str
    input_file: Path
    output_file: Path
    script_path: Path
    execution: GildasResult


def export_uvfits(source: str, configuration: str, *, basebands="all", windows=None,
                  selfcal: bool = True, contsub: bool = True, execute: bool | None = None,
                  keep_script: bool = True, config_file: str | None = None) -> list[UVFITSExportResult]:
    """Export selected narrowband UVTs to CASA-compatible UVFITS files."""
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    if windows is None:
        selected = list(cfg.narrowband_windows)
    elif isinstance(windows, str):
        selected = [windows.lower()]
    else:
        selected = [value.lower() for value in windows]
    unknown = sorted(set(selected) - set(cfg.narrowband_windows))
    if unknown:
        raise ValueError(f"Unknown narrowband window(s): {', '.join(unknown)}")
    if basebands != "all":
        chosen = [basebands] if isinstance(basebands, str) else list(basebands)
        selected = [window for window in selected if any(window in _windows(cfg, bb) for bb in chosen)]
    source_out = cfg.region_catalogue.get(source, {}).get("source_out", source)
    results = []
    for window in selected:
        pair = lid_pair_values(window)
        values = {"source": source, "source_out": source_out, "config": configuration,
                  "window": window, "lid": window, **pair,
                  "selfcal": cfg.selfcal_ext if selfcal else "",
                  "contsub": cfg.uvsub_ext if contsub else ""}
        input_file = Path(cfg.naming.render("uvfits_input_narrowband", **values))
        output_file = Path(cfg.naming.render("uvfits_output_narrowband", **values))
        script_path = Path(cfg.naming.render("uvfits_script", **values))
        run_enabled = cfg.gildas_execute if execute is None else execute
        if run_enabled and not input_file.is_file():
            raise FileNotFoundError(f"UVFITS input UVT not found: {input_file}")
        script = build_uvfits_export_script(str(input_file), str(output_file))
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script)
        runner_kwargs = {"workdir": str(script_path.parent)}
        if execute is not None:
            runner_kwargs["execute"] = execute
        runner = cfg.make_gildas_runner(**runner_kwargs)
        try:
            execution = runner.run_mapping(script, expected_outputs=[output_file], keep_script=keep_script)
        except Exception:
            if not keep_script:
                script_path.unlink(missing_ok=True)
            raise
        if not keep_script:
            script_path.unlink(missing_ok=True)
        results.append(UVFITSExportResult(source, configuration, window, input_file,
                                          output_file, script_path, execution))
    return results


def _windows(cfg: Config, baseband: str) -> set[str]:
    if baseband not in cfg.spectral_window_starts:
        raise ValueError(f"Unknown baseband: {baseband}")
    starts = sorted(cfg.spectral_window_starts.values())
    start = cfg.spectral_window_starts[baseband]
    following = [value for value in starts if value > start]
    end = min(following) - 1 if following else cfg.spectral_narrowband_end
    return {window for window in cfg.narrowband_windows if start <= int(window[1:4]) <= end}


__all__ = ["UVFITSExportResult", "export_uvfits"]
