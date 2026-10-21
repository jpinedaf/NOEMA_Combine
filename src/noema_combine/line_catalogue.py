"""Queries for lines covered by configured spectral windows."""

from __future__ import annotations

import re
from typing import Any

from .config import Config, get_config


def _lid_number(value: str) -> int:
    """Return the numeric narrowband identifier from a catalogue value."""
    match = re.fullmatch(r"l0*(\d+)", str(value).strip().lower())
    if match is None:
        raise ValueError(f"Invalid narrowband identifier in line catalogue: {value!r}")
    return int(match.group(1))


def _narrowband_window(number: int, configured: list[str]) -> str | None:
    for window in configured:
        match = re.fullmatch(r"l(\d+)l(\d+)", window)
        if match and int(match.group(1)) == number:
            return window
    return None


def _broadband_bounds(cfg: Config, window: str) -> tuple[int, int]:
    starts = cfg.spectral_window_starts
    name = window.strip().lower()
    if name not in starts:
        available = ", ".join(starts) or "none"
        raise ValueError(
            f"Unknown broadband window {window!r}; configured windows: {available}"
        )
    ordered = sorted(starts.items(), key=lambda item: item[1])
    index = next(i for i, (key, _) in enumerate(ordered) if key == name)
    start = ordered[index][1]
    end = (
        ordered[index + 1][1] - 1
        if index + 1 < len(ordered)
        else cfg.spectral_narrowband_end
    )
    return start, end


def lines_in_window(
    window: str,
    *,
    config_file: str | None = None,
    config: Config | None = None,
) -> list[dict[str, Any]]:
    """Return catalogue lines covered by a narrowband or broadband window.

    Broadband membership is determined exclusively by the configured
    ``[spectral_windows]`` starting-window mapping. Narrowband identifiers are
    normalized, so values such as ``l34``, ``L034``, and ``l034l073`` are
    accepted. Results are sorted by catalogue frequency.
    """
    cfg = config or (
        Config(config_file=config_file, isolated=True)
        if config_file is not None
        else get_config()
    )
    normalized = "".join(str(window).strip().lower().split())
    pair = re.fullmatch(r"l0*(\d+)l0*(\d+)", normalized)
    if pair:
        start, end = int(pair.group(1)), int(pair.group(2))
        if start > end:
            raise ValueError(f"Invalid narrowband window: {window!r}")
    else:
        start, end = _broadband_bounds(cfg, normalized)

    rows: list[dict[str, Any]] = []
    for name, qn, frequency, molecule, qn_plot, lid, baseband in zip(
        cfg.line_name,
        cfg.qn,
        cfg.freq,
        cfg.name_str,
        cfg.qn_str,
        cfg.Lid,
        cfg.line_baseband,
    ):
        lid_text = str(lid).strip().lower()
        try:
            lid_number = _lid_number(lid_text)
        except ValueError:
            if pair or lid_text != normalized:
                continue
            lid_number = None
        if lid_number is not None and not start <= lid_number <= end:
            continue
        if lid_number is None and str(baseband).strip().lower() != normalized:
            continue
        narrowband = (
            _narrowband_window(lid_number, cfg.narrowband_windows)
            if lid_number is not None
            else None
        )
        rows.append(
            {
                "line": str(name),
                "qn": str(qn),
                "frequency_ghz": float(frequency),
                "molecule": str(molecule),
                "quantum_number": str(qn_plot),
                "narrowband_window": narrowband
                or (f"l{lid_number:03d}" if lid_number is not None else None),
                "window": normalized,
            }
        )
    return sorted(rows, key=lambda row: row["frequency_ghz"])


__all__ = ["lines_in_window"]
