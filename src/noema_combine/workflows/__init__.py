"""High-level NOEMA processing workflows."""

from .continuum import (
    ContinuumSubtractionResult,
    NarrowbandSubtractionResult,
    make_continuum_subtraction,
    make_narrowband_continuum_subtraction,
)
from .imaging import (
    CleanImageResult,
    DirtyImageResult,
    RestoreImageResult,
    make_clean_images,
    LineImageResult,
    make_line_images,
    make_dirty_images,
    restore_image,
)
from .line import LineExtractionResult, extract_line
from .merged import MergedLineImageResult, make_merged_line_images

__all__ = [
    "ContinuumSubtractionResult",
    "NarrowbandSubtractionResult",
    "make_continuum_subtraction",
    "make_narrowband_continuum_subtraction",
    "DirtyImageResult",
    "make_dirty_images",
    "CleanImageResult",
    "make_clean_images",
    "LineImageResult",
    "make_line_images",
    "RestoreImageResult",
    "restore_image",
    "LineExtractionResult",
    "extract_line",
    "MergedLineImageResult",
    "make_merged_line_images",
]
