"""GILDAS UVFITS export script generation."""

from __future__ import annotations


def build_uvfits_export_script(input_file: str, output_file: str) -> str:
    """Build a MAPPING script that exports one UVT to CASA UVFITS."""
    return "\n".join([
        f'let name "{input_file.removesuffix(".uvt")}"',
        f'fits "{output_file}" from "{input_file}" /style CASA_UVFITS /overwrite',
        "exit",
        "",
    ])


__all__ = ["build_uvfits_export_script"]
