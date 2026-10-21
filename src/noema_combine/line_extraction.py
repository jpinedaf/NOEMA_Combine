"""GILDAS script generation for extracting individual spectral lines."""

from __future__ import annotations


def build_line_extraction_script(
    input_file: str,
    output_file: str,
    *,
    line_name: str,
    rest_frequency_mhz: float,
    velocity_range: tuple[float, float],
) -> str:
    """Build a MAPPING script that extracts one line from a UV table."""
    vmin, vmax = velocity_range
    return "\n".join(
        [
            "sic message mapping s-i",
            f'modify "{input_file}" /frequency {line_name} {rest_frequency_mhz:g}',
            f'let name "{input_file.removesuffix(".uvt")}"',
            "let type uvt",
            "go setup",
            f"uv_extract /range {vmin:.2f} {vmax:.2f} velocity",
            f'write uv "{output_file}" new',
            "sic message mapping s+i",
            "exit",
        ]
    ) + "\n"


__all__ = ["build_line_extraction_script"]
