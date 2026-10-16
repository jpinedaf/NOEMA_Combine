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
    make_dirty_images,
    restore_image,
)

__all__ = [
    "ContinuumSubtractionResult",
    "NarrowbandSubtractionResult",
    "make_continuum_subtraction",
    "make_narrowband_continuum_subtraction",
    "DirtyImageResult",
    "make_dirty_images",
    "CleanImageResult",
    "make_clean_images",
    "RestoreImageResult",
    "restore_image",
]
