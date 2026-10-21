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


def _window_bounds(value: str, configured: list[str]) -> tuple[int, int] | None:
    """Return the numeric bounds represented by a narrowband identifier."""
    normalized = "".join(str(value).strip().lower().split())
    pair = re.fullmatch(r"l0*(\d+)l0*(\d+)", normalized)
    if pair:
        start, end = int(pair.group(1)), int(pair.group(2))
        if start > end:
            raise ValueError(f"Invalid narrowband window: {value!r}")
        return start, end
    single = re.fullmatch(r"l0*(\d+)", normalized)
    if not single:
        return None
    start = int(single.group(1))
    for window in configured:
        match = re.fullmatch(r"l(\d+)l(\d+)", window)
        if match and int(match.group(1)) == start:
            return start, int(match.group(2))
    return start, start


def _catalogue_window(value: str, configured: list[str]) -> tuple[int, str | None]:
    """Return a catalogue row's start identifier and normalized window."""
    normalized = "".join(str(value).strip().lower().split())
    pair = re.fullmatch(r"l0*(\d+)l0*(\d+)", normalized)
    if pair:
        start, end = int(pair.group(1)), int(pair.group(2))
        return start, f"l{start:03d}l{end:03d}"
    start = _lid_number(normalized)
    return start, _narrowband_window(start, configured) or f"l{start:03d}"


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
    narrow_bounds = _window_bounds(normalized, cfg.narrowband_windows)
    requested_pair = re.fullmatch(r"l0*(\d+)l0*(\d+)", normalized)
    requested_pair_name = (
        f"l{int(requested_pair.group(1)):03d}l{int(requested_pair.group(2)):03d}"
        if requested_pair
        else None
    )
    if narrow_bounds is not None:
        start, end = narrow_bounds
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
            lid_number, catalogue_window = _catalogue_window(
                lid_text, cfg.narrowband_windows
            )
        except ValueError:
            if narrow_bounds is not None or lid_text != normalized:
                continue
            lid_number = None
            catalogue_window = None
        if lid_number is not None:
            if narrow_bounds is None:
                if not start <= lid_number <= end:
                    continue
            elif requested_pair_name is not None:
                if catalogue_window != requested_pair_name and not re.fullmatch(
                    r"l0*\d+", lid_text
                ):
                    continue
            elif lid_number != start:
                continue
        if lid_number is None and str(baseband).strip().lower() != normalized:
            continue
        rows.append(
            {
                "line": str(name),
                "qn": str(qn),
                "frequency_ghz": float(frequency),
                "molecule": str(molecule),
                "quantum_number": str(qn_plot),
                "narrowband_window": catalogue_window,
                "window": normalized,
            }
        )
    return sorted(rows, key=lambda row: row["frequency_ghz"])


__all__ = ["lines_in_window"]
