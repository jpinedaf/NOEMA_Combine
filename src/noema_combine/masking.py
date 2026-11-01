"""Support-mask copy operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .config import Config, get_config


@dataclass(frozen=True)
class MaskCopy:
    """One support-mask copy operation."""

    source: Path
    destination: Path


def copy_support_masks(
    source: str,
    configuration: str,
    source_baseband: str,
    target_basebands: str | list[str] | tuple[str, ...] | None = None,
    *,
    include_selfcal: bool = True,
    overwrite: bool = False,
    config_file: str | None = None,
) -> list[MaskCopy]:
    """Copy a wideband support mask to other basebands and self-cal stages."""
    cfg = Config(config_file=config_file, isolated=True) if config_file else get_config()
    source_baseband = source_baseband.strip().lower()
    allowed = tuple(cfg.spectral_window_starts)
    if source_baseband not in allowed:
        raise ValueError(f"Unknown baseband: {source_baseband}")
    if target_basebands is None or target_basebands == "all":
        targets = list(allowed)
    elif isinstance(target_basebands, str):
        targets = [target_basebands]
    else:
        targets = list(target_basebands)
    targets = [value.strip().lower() for value in targets]
    unknown = sorted(set(targets) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown target baseband(s): {', '.join(unknown)}")

    source_out = cfg.region_catalogue.get(source, {}).get("source_out", source)
    source_path = Path(cfg.naming.render(
        "support_mask", source=source, source_out=source_out,
        config=configuration, window=source_baseband,
    )).expanduser()
    if not source_path.is_file():
        raise FileNotFoundError(f"Support mask not found: {source_path}")

    copies: list[MaskCopy] = []
    destinations: list[Path] = []
    for target in targets:
        values = {
            "source": source, "source_out": source_out, "config": configuration,
            "window": target,
        }
        if target != source_baseband:
            destinations.append(Path(cfg.naming.render("support_mask", **values)))
        if include_selfcal:
            for iteration in ("", "-1", "-2", "-3", "-selfcal"):
                destinations.append(Path(cfg.naming.render(
                    "support_mask_selfcal", mask_iteration=iteration, **values
                )))

    for destination in destinations:
        destination = destination.expanduser()
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Support mask already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        copies.append(MaskCopy(source=source_path, destination=destination))
    return copies


__all__ = ["MaskCopy", "copy_support_masks"]
