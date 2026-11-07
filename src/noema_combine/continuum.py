"""Shared channel-range handling for continuum subtraction workflows."""

from __future__ import annotations

from pathlib import Path
import re

from .config import Config, get_config


def normalize_window(window: str) -> str:
    """Normalize a wideband or narrowband spectral-window identifier."""
    value = "".join(str(window).strip().lower().split())
    match = re.fullmatch(r"l(\d+)l(\d+)", value)
    if match:
        return f"l{int(match.group(1)):03d}l{int(match.group(2)):03d}"
    return value


def _read_range_file(path: str | Path) -> str | None:
    range_path = Path(path).expanduser()
    if not range_path.is_file():
        return None
    value = range_path.read_text().strip()
    return value or None


def resolve_channel_range(
    window: str,
    *,
    channel_range: str | None = None,
    range_file: str | Path | None = None,
    narrowband: bool = False,
    config: Config | None = None,
) -> str | None:
    """Resolve a subtraction range by explicit, file, and config precedence.

    ``None`` means that the generated GILDAS command should use
    ``uv_baseline 0`` without a ``/range`` clause.
    """
    if channel_range is not None:
        value = channel_range.strip()
        if not value:
            raise ValueError("channel_range cannot be empty when provided")
        return value

    if range_file is not None:
        value = _read_range_file(range_file)
        if value is not None:
            return value

    cfg = config or get_config()
    ranges = (
        cfg.continuum_narrowband_ranges
        if narrowband
        else cfg.continuum_wideband_ranges
    )
    return ranges.get(normalize_window(window))


def baseline_command(channel_range: str | None = None) -> str:
    """Build the GILDAS baseline command for a resolved channel range."""
    if channel_range is None:
        return "uv_baseline 0"
    return f"uv_baseline 0 /range {channel_range} channel"


def build_continuum_subtraction_script(
    input_file: str,
    output_file: str,
    *,
    channel_range: str | None = None,
    filter_channels: str | None = None,
    include_modify: bool = True,
) -> str:
    """Build a MAPPING script for continuum subtraction.

    When ``channel_range`` is absent, the script contains ``uv_baseline 0``.
    ``filter_channels`` is optional and adds the channel filter used by the
    wideband raw-script workflow.
    """
    lines = ["sic message mapping s-i"]
    if include_modify:
        lines.append(f'modify "{input_file}"')
    lines.extend([
        f'let name "{input_file.removesuffix(".uvt")}"',
        "let type uvt",
        "go setup",
        baseline_command(channel_range),
    ])
    if filter_channels:
        lines.append(f"uv_filter /channels {filter_channels} /zero")
    lines.extend(
        [
            f'write uv "{output_file}" new',
            "sic message mapping s+i",
            "exit",
        ]
    )
    return "\n".join(lines) + "\n"


def build_narrowband_continuum_subtraction_script(
    input_file: str,
    output_file: str,
    *,
    channel_range: str | None = None,
) -> str:
    """Build a MAPPING script for one narrowband spectral window."""
    return build_continuum_subtraction_script(
        input_file,
        output_file,
        channel_range=channel_range,
        include_modify=False,
    )
