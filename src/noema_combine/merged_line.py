"""GILDAS script generation for merged NOEMA and single-dish line cubes."""

from __future__ import annotations

from decimal import Decimal


def _frequency(value: object) -> str:
    """Format a catalogue frequency in MHz without losing its digits."""
    text = format(Decimal(str(value)), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def build_merged_line_prepare_script(
    input_file: str,
    output_file: str,
    *,
    line_name: str,
    rest_frequency_mhz: object,
    velocity_range: tuple[float, float],
    systemic_velocity: float,
    velocity_resolution: float,
) -> str:
    """Build the MAPPING script that extracts and resamples a line UVT."""
    if velocity_resolution <= 0:
        raise ValueError("velocity_resolution must be positive")
    lower, upper = velocity_range
    if lower >= upper:
        raise ValueError("velocity_range must be increasing")
    channels = max(1, round((upper - lower) / velocity_resolution))
    center = channels // 2
    return "\n".join(
        [
            "sic message mapping s-i",
            f'modify "{input_file}" /frequency {line_name} {_frequency(rest_frequency_mhz)} /velocity {systemic_velocity:g}',
            f'read uv "{input_file.removesuffix(".uvt")}"',
            f"uv_extract /range {lower:.1f} {upper:.1f} V",
            f"uv_resample {channels} {center} {systemic_velocity:g} {velocity_resolution:g}",
            f'write uv "{output_file}" /overwrite',
            "sic message mapping s+i",
            "exit",
        ]
    ) + "\n"


def build_merged_line_image_script(
    prepared_uvt: str,
    single_dish_table: str,
    merged_uvt: str,
    output_name: str,
    *,
    configuration: str,
    map_size: tuple[int, int],
    map_cell: tuple[float, float],
    niter: int = 5000,
    method: str = "SDI",
    support_mask: bool = False,
    dirty: bool = True,
    clean: bool = True,
) -> str:
    """Build the MAPPING script that merges and images a line cube."""
    normalized_method = method.strip().upper()
    if normalized_method not in {"HOGBOM", "SDI"}:
        raise ValueError("method must be 'HOGBOM' or 'SDI'")
    if configuration.upper() not in {"CD", "ACD"}:
        raise ValueError("merged line imaging requires configuration 'CD' or 'ACD'")
    if niter < 0:
        raise ValueError("niter must not be negative")
    if not dirty and not clean:
        raise ValueError("At least one of dirty or clean must be True")
    prepared_name = prepared_uvt.removesuffix(".uvt")
    merged_name = merged_uvt.removesuffix(".uvt")
    lines = [
        "sic message mapping s-i",
        f'let name "{prepared_name}"',
        "go setup",
        f'sic copy "{single_dish_table}" "{prepared_name}.tab"',
        'let uvshort%unit "K (Tmb)"',
        "go uvshort",
    ]
    default_merged = f"{prepared_name}-merged.uvt"
    if merged_uvt != default_merged:
        lines.append(f'sic copy "{default_merged}" "{merged_uvt}"')
    lines.extend([
        f'let name "{merged_name}"',
        "go setup",
        f"let map_size {map_size[0]} {map_size[1]}",
        f"let map_cell {map_cell[0]:g} {map_cell[1]:g}",
        "let weight_mode natural",
        "let uv_cell[2] 1",
    ])
    if dirty or clean:
        lines.append("go uvmap")
    if clean:
        lines.extend([
            "let fres 0",
            f"let niter {niter}",
            f'define header H "{merged_name}.lmv" read /global',
            f"let ares {2.0 if support_mask else 3.0}*'H%noise'",
            "delete /VARIABLE H",
            f"let method {normalized_method}",
            f"let MYCLEAN%SUPPORT {'YES' if support_mask else 'NO'}",
            "go clean",
            f'fits "{output_name}.fits" from "{merged_name}.lmv-clean" /overwrite',
            f'read clean "{merged_name}"',
            "primary /truncate 20",
            f'write sky "{merged_name}-pbcor"',
            f'fits "{output_name}-pbcor.fits" from "{merged_name}-pbcor.lmv-sky" /bit -32 /overwrite',
        ])
    lines.extend(["sic message mapping s+i", "exit"])
    return "\n".join(lines) + "\n"


__all__ = ["build_merged_line_prepare_script", "build_merged_line_image_script"]
