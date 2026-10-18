"""GILDAS script builders for imaging workflows."""

from __future__ import annotations


def build_dirty_image_script(
    input_file: str,
    output_name: str,
    *,
    configuration: str,
) -> str:
    """Build a MAPPING script for a dirty UVT image."""
    if configuration.upper() in {"A", "ACD"}:
        beam_lines = ["let map_beam_step 2032", "let map_size 0 0"]
    else:
        beam_lines = ["let map_beam_step 1"]
    return "\n".join(
        [
            "sic message mapping s-i",
            f"modify {input_file}",
            f"let name {output_name}",
            "let type uvt",
            "go setup",
            *beam_lines,
            "go uvmap",
            "sic message mapping s+i",
            "exit",
        ]
    ) + "\n"


def build_clean_image_script(
    input_file: str,
    output_name: str,
    *,
    baseband: str,
    configuration: str,
    weighting: str = "natural",
    threshold_factor: float = 5.0,
    niter: int = 0,
    primary_beam_correction: bool = True,
    primary_beam_truncate: int = 20,
) -> str:
    """Build a MAPPING script for a cleaned wideband UVT."""
    if configuration.upper() in {"A", "ACD"}:
        beam_lines = ["let map_beam_step 2032", "let map_size 0 0"]
    else:
        beam_lines = ["let map_beam_step -1", "let map_size 0 0"]
    lines = [
        "sic message mapping s-i",
        f"modify {input_file}",
        f"let name {output_name}",
        "let type uvt",
        "go setup",
        f"define header H '{output_name}'.uvt Write",
        f"let H%line {baseband}",
        "delete /VARIABLE H",
        "let map_cell 0 0",
        *beam_lines,
        f"let weight_mode {weighting}",
        "let uv_cell[2] 1",
        "go uvmap",
        "let fres 0",
        f"let niter {niter}",
        f"define header H '{output_name}.lmv' read /global",
        f"let ares {threshold_factor}*'H%noise'",
        "delete /VARIABLE H",
        "go clean",
        f"fits '{output_name}.fits' from '{output_name}.lmv-clean' /overwrite",
    ]
    if primary_beam_correction:
        lines.extend(
            [
                f"read clean '{output_name}'",
                f"primary /truncate {primary_beam_truncate}",
                f"write sky '{output_name}-pbcor'",
                f"fits '{output_name}-pbcor.fits' from '{output_name}-pbcor.lmv-sky' /bit -32 /overwrite",
            ]
        )
    lines.extend(["sic message mapping s+i", "exit"])
    return "\n".join(lines) + "\n"


def build_restore_image_script(
    uv_input: str,
    clean_image: str,
    components: str,
    output_name: str,
    *,
    primary_beam_correction: bool = True,
    primary_beam_truncate: int = 20,
) -> str:
    """Build a MAPPING script that restores clean components with UV data.

    The same GILDAS operations apply to continuum maps and spectral cubes;
    the workflow supplies the appropriate configured filenames for each.
    ``output_name`` is the restored image name without the ``.fits`` suffix.
    """
    lines = [
        "sic message mapping s-i",
        f"define header H '{clean_image}' Read",
        "let map_cell 'H%convert[3,2]*60*60*360/2/pi'",
        "let map_size 'H%dim[1]' 'H%dim[2]'",
        "delete /VARIABLE H",
        "let map_weight robust",
        "let map_robust 1",
        f"read uv {uv_input}",
        f"read cct {components}",
        "uv_restore",
        f"write * {output_name}",
        f"fits '{output_name}.fits' from '{output_name}.lmv-clean' /overwrite",
    ]
    if primary_beam_correction:
        lines.extend(
            [
                f"read clean '{output_name}'",
                f"primary /truncate {primary_beam_truncate}",
                f"write sky '{output_name}-pbcor'",
                f"fits '{output_name}-pbcor.fits' from '{output_name}-pbcor.lmv-sky' /bit -32 /overwrite",
            ]
        )
    lines.extend(["sic message mapping s+i", "exit"])
    return "\n".join(lines) + "\n"
