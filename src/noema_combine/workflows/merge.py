"""Merge A and CD UV tables with GILDAS UV_MERGE."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from ..config import Config, get_config
from ..gildas import GildasResult
from ..merge import build_uv_merge_init, build_uv_merge_script
from ..naming import lid_pair_values


@dataclass
class UVMergeResult:
    source: str
    input_config_a: str
    input_config_b: str
    output_config: str
    window: str
    product_type: str
    input_file_a: Path
    input_file_b: Path
    output_file: Path
    script_path: Path
    init_path: Path
    execution: GildasResult


def _pair_start(value: str) -> int:
    match = re.fullmatch(r"l0*(\d+)l\d+", value.lower())
    if match is None:
        raise ValueError(f"Invalid narrowband window: {value}")
    return int(match.group(1))


def _windows_for_baseband(cfg: Config, baseband: str) -> list[str]:
    if baseband not in cfg.spectral_window_starts:
        raise ValueError(f"Unknown baseband: {baseband}")
    starts = sorted(cfg.spectral_window_starts.values())
    start = cfg.spectral_window_starts[baseband]
    following = [value for value in starts if value > start]
    end = min(following) - 1 if following else cfg.spectral_narrowband_end
    return [window for window in cfg.narrowband_windows if start <= _pair_start(window) <= end]


def merge_uv_tables(
    source: str,
    *,
    baseband: str | None = "li",
    windows: str | list[str] | tuple[str, ...] | None = None,
    products: str | list[str] | tuple[str, ...] = ("wideband_contsub", "narrowband_contsub"),
    config_a: str = "A",
    config_b: str = "CD",
    output_config: str = "ACD",
    execute: bool | None = None,
    keep_script: bool = True,
    config_file: str | None = None,
) -> list[UVMergeResult]:
    """Merge configured A and CD UVTs for wideband and narrowband products."""
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    if isinstance(products, str):
        products = [products]
    products = list(products)
    valid = {"wideband_continuum", "wideband_contsub", "narrowband", "narrowband_contsub"}
    unknown = sorted(set(products) - valid)
    if unknown:
        raise ValueError(f"Unknown merge product(s): {', '.join(unknown)}")
    basebands = list(cfg.spectral_window_starts) if baseband == "all" else [baseband or "li"]
    unknown_bb = sorted(set(basebands) - set(cfg.spectral_window_starts))
    if unknown_bb:
        raise ValueError(f"Unknown baseband(s): {', '.join(unknown_bb)}")
    if windows is None:
        selected_windows = sorted({window for bb in basebands for window in _windows_for_baseband(cfg, bb)})
    elif isinstance(windows, str):
        selected_windows = [windows.lower()]
    else:
        selected_windows = [value.lower() for value in windows]
    if windows is not None:
        unknown_windows = sorted(set(selected_windows) - set(cfg.narrowband_windows))
        if unknown_windows:
            raise ValueError(f"Unknown narrowband window(s): {', '.join(unknown_windows)}")

    source_out = cfg.region_catalogue.get(source, {}).get("source_out", source)
    results: list[UVMergeResult] = []
    for product in products:
        is_wideband = product.startswith("wideband")
        suffix = {
            "wideband_continuum": "_cont_rob1-selfcal",
            "wideband_contsub": "_contsub_sc",
            "narrowband": "_sc",
            "narrowband_contsub": "_sc_contsub",
        }[product]
        targets = basebands if is_wideband else selected_windows
        for window in targets:
            pair = lid_pair_values(window) if not is_wideband else {}
            values = {
                "source": source, "source_out": source_out,
                "config_a": config_a, "config_b": config_b, "config_out": output_config,
                "config": output_config, "window": window,
                "window_folder": "wideband" if is_wideband else pair["lid_pair_folder"],
                "suffix": suffix, "lid": window, **pair,
            }
            family = "wideband" if is_wideband else "narrowband"
            input_a = Path(cfg.naming.render(f"merge_input_a_{family}", **values))
            input_b = Path(cfg.naming.render(f"merge_input_b_{family}", **values))
            output = Path(cfg.naming.render(f"merge_output_{family}", **values))
            script_path = Path(cfg.naming.render("merge_script", **values))
            results.append(_run_merge(
                cfg, source, config_a, config_b, output_config, window, product,
                input_a, input_b, output, script_path, execute, keep_script,
            ))
    return results


def _run_merge(cfg, source, config_a, config_b, output_config, window, product,
               input_a, input_b, output, script_path, execute, keep_script):
    run_enabled = cfg.gildas_execute if execute is None else execute
    if run_enabled:
        for label, path in (("A", input_a), ("CD", input_b)):
            if not path.is_file():
                raise FileNotFoundError(f"Merge {label} input not found: {path}")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    init_path = script_path.parent / "uv_merge.init"
    init_path.write_text(build_uv_merge_init(str(input_a), str(input_b), str(output)))
    script = build_uv_merge_script()
    script_path.write_text(script)
    runner_kwargs = {"workdir": str(script_path.parent)}
    if execute is not None:
        runner_kwargs["execute"] = execute
    runner = cfg.make_gildas_runner(**runner_kwargs)
    try:
        execution = runner.run_mapping(script, expected_outputs=[output], keep_script=keep_script)
    except Exception:
        if not keep_script:
            script_path.unlink(missing_ok=True)
            init_path.unlink(missing_ok=True)
        raise
    if not keep_script:
        script_path.unlink(missing_ok=True)
        init_path.unlink(missing_ok=True)
    return UVMergeResult(source, config_a, config_b, output_config, window, product,
                         input_a, input_b, output, script_path, init_path, execution)


__all__ = ["UVMergeResult", "merge_uv_tables"]
