"""GILDAS UV-table merge script generation."""

from __future__ import annotations


def build_uv_merge_init(
    input_file_a: str,
    input_file_b: str,
    output_file: str,
) -> str:
    """Build the ``uv_merge.init`` file used by GILDAS ``UV_MERGE``."""
    return "\n".join([
        "!",
        "! Task UV_MERGE initialization file",
        "!",
        f'TASK\\CHARACTER  "First input UV Table " TABLE_IN$ "{input_file_a}"',
        "TASK\\REAL  \"Weight multiplicative factors \" WEIGHT$ 1",
        "TASK\\REAL  \"Data multiplicative factors \" FACTOR$ 1",
        f'TASK\\CHARACTER  "Second input UV Table " TABLE_REF$ "{input_file_b}"',
        f'TASK\\CHARACTER  "Output merged UV Table " TABLE_OUT$ "{output_file}"',
        "TASK\\INTEGER  \"Merging mode \" MODE$ 0",
        "TASK\\REAL  \"Spectral index for continuum merging \" ALPHA$ 0",
        "TASK\\GO",
        "",
    ])


def build_uv_merge_script() -> str:
    """Build the MAPPING script that runs ``UV_MERGE``."""
    return "run uv_merge uv_merge.init /nowindow\nexit\n"


__all__ = ["build_uv_merge_init", "build_uv_merge_script"]
