"""GILDAS UV_CAL script generation for self-calibration products."""

from __future__ import annotations


def build_selfcal_init(
    input_file: str,
    gain_file: str,
    output_file: str,
    *,
    flag_uncalibrated: bool,
) -> str:
    """Build the ``uv_cal.init`` file consumed by GILDAS ``UV_CAL``."""
    flag = "YES" if flag_uncalibrated else "NO"
    return "\n".join(
        [
            "!",
            "! Task UV_CAL initialization file",
            "!",
            f'TASK\\CHARACTER  "UV data table "        UVDATA$ "{input_file}"',
            f'TASK\\CHARACTER  "UV gain table "        UVGAIN$ "{gain_file}"',
            f'TASK\\CHARACTER  "UV calibrated table "  UVCAL$ "{output_file}"',
            "TASK\\REAL       \"Amplitude gain\"        AMPLI_GAIN$ 0",
            "TASK\\REAL       \"Phase gain\"   PHASE_GAIN$ 1",
            f'TASK\\LOGICAL "Flag uncalibrated data"    FLAG$  {flag}',
            "TASK\\GO",
            "",
        ]
    )


def build_selfcal_script() -> str:
    """Build the mapping script that runs ``UV_CAL`` from ``uv_cal.init``."""
    return "\n".join(
        [
            "sic message mapping s-i",
            "run uv_cal /nowindow",
            "sic message mapping s+i",
            "exit",
            "",
        ]
    )


__all__ = ["build_selfcal_init", "build_selfcal_script"]
