"""Configurable folder and filename construction.

The naming layer keeps workflow code independent of a particular project
directory convention.  Templates are deliberately small and declarative;
projects that need conditional rules can subclass :class:`FileNaming`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from string import Formatter


DEFAULT_TEMPLATES: dict[str, str] = {
    "uvt_file": "{uvt_root}/{lid}/{source}_{line}_{qn}_{lid}.uvt",
    "uvt_file_merge": "{uvt_out_root}/{lid}/{source}_{line}_{qn}_{lid}.uvt",
    "uvt_window": "{uvt_root}/{lid}/{source}_{lid}{selfcal}{uvsub}.uvt",
    "sd_file": "{sd_root}/{source}_{line}_{qn}{lid_suffix}{sd_ext}",
    "sd_file_merge": "{sd_root}/{source}_{line}_{qn}_{lid}{sd_ext}",
    "narrowband_folder": "{root}/{config}/narrowband/{lid_folder}",
    "search_uvt": "{uvt_root}/{lid}/*{source}*{line}*{qn}*{lid}*.uvt",
    "continuum_file": "{root}/{config}/wideband/{source}_{config}_{lid}_continuum.uvt",
    "continuum_input": "{uvt_root}/{lid}/{source}_{lid}.uvt",
    "continuum_subtracted_file": "{root}/{config}/wideband/{source}_{config}_{lid}{contsub}.uvt",
    "continuum_range_file": "{root}/{config}/{source}_{config}_{lid}_linerange.txt",
    "continuum_filter_file": "{root}/{config}/{source}_{config}_{lid}_filter.txt",
    "continuum_plot": "{root}/{config}/wideband/{source}_{config}_{lid}.png",
    "continuum_cube": "{root}/{config}/wideband/{source}_{config}_{lid}.lmv-clean",
    "narrowband_input": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}_sc.uvt",
    "narrowband_output": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}_sc{contsub}.uvt",
    "narrowband_script": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}_contsub.map",
    "dirty_folder": "{root}/{config}/{window_folder}",
    "dirty_input": "{dirty_folder}/{source}_{config}_{window}{selfcal}{contsub}.uvt",
    "dirty_script": "{dirty_folder}/{source}_{config}_{window}{selfcal}{contsub}_dirty.map",
    "dirty_map": "{dirty_folder}/{source}_{config}_{window}{selfcal}{contsub}.lmv",
    "clean_input": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.uvt",
    "clean_script": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_clean.map",
    "clean_cube": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.lmv-clean",
    "clean_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.fits",
    "clean_pb_cube": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}-pbcor.lmv-sky",
    "clean_pb_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}-pbcor.fits",
    "clean_input_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.uvt",
    "clean_script_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_clean.map",
    "clean_cube_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.lmv-clean",
    "clean_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.fits",
    "clean_pb_cube_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}-pbcor.lmv-sky",
    "clean_pb_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}-pbcor.fits",
    "restore_uvt": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.uvt",
    "restore_cct": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.cct",
    "restore_clean": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}.lmv-clean",
    "restore_output": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script": "{root}/{config}/wideband/{source}_{config}_{window}{selfcal}{contsub}_restore.map",
    "restore_uvt_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.uvt",
    "restore_cct_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.cct",
    "restore_clean_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}.lmv-clean",
    "restore_output_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script_narrowband": "{root}/{config}/narrowband/{lid_pair}/{source}_{config}_{lid_pair}{selfcal}{contsub}_restore.map",
    "restore_uvt_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}.uvt",
    "restore_cct_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}.cct",
    "restore_clean_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}.lmv-clean",
    "restore_output_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres.lmv-clean",
    "restore_fits_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres.fits",
    "restore_pb_cube_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres-pbcor.lmv-sky",
    "restore_pb_fits_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_uvres-pbcor.fits",
    "restore_script_line": "{root}/{config}/lines/{source}_{config}_{line}_{qn}_{lid}{selfcal}{contsub}_restore.map",
    "clean_image": "{root}/{config}/images/{source}_{config}_{lid}{suffix}.fits",
    "line_cube": "{root}/{config}30m/{source}_{line}_{qn}_{lid}{suffix}.fits",
    "merged_cube": "{root}/{config}30m/{source}_{line}_{qn}_{lid}{suffix}.fits",
    "mask_file": "{root}/{config}/masks/{source}_{config}_{lid}{suffix}.mask",
    "uvfits_file": "{root}/{config}/uvfits/{source}_{config}_{lid}.uvfits",
}

_ALLOWED_FIELDS = {
    "root", "uvt_root", "uvt_out_root", "sd_root", "sd_ext",
    "source", "source_out", "source_sd", "config", "line", "qn",
    "lid", "lid_lower", "lid_upper", "lid_folder", "lid_pair",
    "narrowband_folder", "window", "window_upper", "window_folder", "dirty_folder",
    "selfcal", "contsub", "uvsub", "lid_suffix", "suffix", "product",
    "resolution", "weighting", "beam", "smoothing", "extension", "product_type",
}


class FileNaming:
    """Render configured paths for package and project-specific products.

    ``*`` is supported in search templates, but output templates should be
    exact filenames.  Unknown template fields raise ``ValueError`` with a
    useful message instead of failing while a GILDAS script is running.
    """

    def __init__(
        self,
        templates: Mapping[str, str] | None = None,
        *,
        uvt_root: str = "D/",
        uvt_out_root: str = "D30m/",
        sd_root: str = "30m/",
        selfcal_suffix: str = "_sc",
        uvsub_suffix: str = "_contsub",
        sd_ext: str = ".30m",
        root: str = ".",
    ) -> None:
        self.templates = dict(DEFAULT_TEMPLATES)
        if templates:
            self.templates.update(templates)
        self.values = {
            "root": root,
            "uvt_root": uvt_root,
            "uvt_out_root": uvt_out_root,
            "sd_root": sd_root,
            "selfcal_suffix": selfcal_suffix,
            "uvsub_suffix": uvsub_suffix,
            "sd_ext": sd_ext,
        }
        self.validate()

    def validate(self) -> None:
        """Validate configured templates before a workflow uses them."""
        formatter = Formatter()
        for product, template in self.templates.items():
            if not isinstance(template, str) or not template:
                raise ValueError(f"Naming template {product!r} must be a non-empty string")
            try:
                fields = [field for _, field, _, _ in formatter.parse(template) if field]
            except ValueError as exc:
                raise ValueError(f"Invalid naming template {product!r}: {exc}") from exc
            unknown = sorted({field.split(".", 1)[0].split("[", 1)[0] for field in fields} - _ALLOWED_FIELDS)
            if unknown:
                raise ValueError(
                    f"Naming template {product!r} uses unknown variable(s): {', '.join(unknown)}"
                )
            if not product.startswith("search_") and any(char in template for char in "*?"):
                raise ValueError(
                    f"Output naming template {product!r} cannot contain wildcard characters"
                )

    @staticmethod
    def _lid_values(lid: str, lid_pair: str | None = None) -> dict[str, str]:
        lid_text = str(lid)
        return {
            "lid": lid_text,
            "lid_lower": lid_text.lower(),
            "lid_upper": lid_text.upper(),
            "lid_folder": lid_text.lower(),
            "lid_pair": lid_pair or lid_text.lower(),
        }

    def render(self, template_name: str, **values: object) -> str:
        """Render a named template using common and product-specific values."""
        if template_name not in self.templates:
            raise ValueError(f"Unknown naming template: {template_name}")
        context = dict(self.values)
        context.update(values)
        if "lid" in context:
            context.update(self._lid_values(str(context["lid"]), context.get("lid_pair")))
        context.setdefault("window", context.get("lid", ""))
        context.setdefault("window_upper", str(context["window"]).upper())
        context.setdefault("window_folder", context.get("lid_folder", context["window"]))
        context.setdefault("dirty_folder", context.get("root", "."))
        context.setdefault("selfcal", "")
        context.setdefault("contsub", "")
        context.setdefault("uvsub", context.get("contsub", ""))
        context.setdefault("lid_suffix", "")
        context.setdefault("suffix", "")
        try:
            return os.path.normpath(self.templates[template_name].format_map(context))
        except KeyError as exc:
            raise ValueError(
                f"Naming template {template_name!r} uses unknown variable {exc.args[0]!r}"
            ) from exc

    def uvt_file(
        self, source: str, line: str, qn: str, lid: str, *, merge: bool = False, **kwargs: object
    ) -> str:
        product = "uvt_file_merge" if merge else "uvt_file"
        return self.render(product, source=source, line=line, qn=qn, lid=lid, **kwargs)

    def uvt_window(
        self, source: str, lid: str, *, selfcal: bool = False, uvsub: bool = True, **kwargs: object
    ) -> str:
        return self.render(
            "uvt_window",
            source=source,
            lid=lid,
            selfcal=self.values["selfcal_suffix"] if selfcal else "",
            uvsub=self.values["uvsub_suffix"] if uvsub else "",
            **kwargs,
        )

    def sd_file(
        self, source: str, line: str, qn: str, lid: str, *, merge: bool = False, **kwargs: object
    ) -> str:
        product = "sd_file_merge" if merge else "sd_file"
        return self.render(
            product,
            source=source,
            line=line,
            qn=qn,
            lid=lid,
            lid_suffix=f"_{lid}" if merge else "",
            **kwargs,
        )

    def narrowband_folder(
        self, source: str, config: str, lid: str, *, lid_pair: str | None = None, **kwargs: object
    ) -> str:
        return self.render(
            "narrowband_folder",
            source=source,
            config=config,
            lid=lid,
            lid_pair=lid_pair,
            **kwargs,
        )

    def search_pattern(self, product: str = "search_uvt", **values: object) -> str:
        """Render a wildcard pattern for locating existing products."""
        return self.render(product, **values)

    def continuum_file(self, source: str, config: str, lid: str, **kwargs: object) -> str:
        return self.render("continuum_file", source=source, config=config, lid=lid, **kwargs)

    def continuum_subtracted_file(self, source: str, config: str, lid: str, **kwargs: object) -> str:
        return self.render(
            "continuum_subtracted_file", source=source, config=config, lid=lid, **kwargs
        )

    def clean_image(self, source: str, config: str, lid: str, **kwargs: object) -> str:
        return self.render("clean_image", source=source, config=config, lid=lid, **kwargs)

    def line_cube(self, source: str, config: str, line: str, qn: str, lid: str, **kwargs: object) -> str:
        return self.render(
            "line_cube", source=source, config=config, line=line, qn=qn, lid=lid, **kwargs
        )

    def merged_cube(self, source: str, config: str, line: str, qn: str, lid: str, **kwargs: object) -> str:
        return self.render(
            "merged_cube", source=source, config=config, line=line, qn=qn, lid=lid, **kwargs
        )

    def mask_file(self, source: str, config: str, lid: str, **kwargs: object) -> str:
        return self.render("mask_file", source=source, config=config, lid=lid, **kwargs)

    def uvfits_file(self, source: str, config: str, lid: str, **kwargs: object) -> str:
        return self.render("uvfits_file", source=source, config=config, lid=lid, **kwargs)

    def preview(self, **values: object) -> dict[str, str]:
        """Render every active template for a representative set of values."""
        preview_values = {
            "source": "SOURCE", "source_out": "SOURCE", "source_sd": "SOURCE",
            "config": "CD", "line": "LINE", "qn": "QN", "lid": "l10",
            "lid_pair": "l10l49", "selfcal": "_sc", "contsub": "_contsub",
            "uvsub": "_contsub", "lid_suffix": "_l10", "suffix": "_product",
            "product": "product", "product_type": "continuum", "resolution": "natural", "weighting": "natural",
            "beam": "pb", "smoothing": "smooth", "extension": ".fits",
        }
        preview_values.update(values)
        return {product: self.render(product, **preview_values) for product in self.templates}

    def describe(self) -> dict[str, str]:
        """Return the active templates for diagnostics and configuration UIs."""
        return dict(self.templates)


def preview_naming(
    source: str,
    config: str,
    line: str,
    qn: str,
    lid: str,
    *,
    lid_pair: str | None = None,
    config_file: str | None = None,
    **values: object,
) -> dict[str, object]:
    """Return resolved naming paths without changing global configuration.

    ``config_file`` is loaded in an isolated configuration instance. When it
    is omitted, the package's active configuration is used. Additional values
    are available for templates that use fields such as ``suffix`` or
    ``weighting``.
    """
    # Import lazily to avoid a config -> naming import cycle.
    from .config import Config, get_config

    cfg = (
        Config(config_file=config_file, isolated=True)
        if config_file
        else get_config()
    )
    context: dict[str, object] = {
        "source": source,
        "source_out": source,
        "source_sd": source,
        "config": config,
        "line": line,
        "qn": qn,
        "lid": lid,
        "lid_pair": lid_pair or lid.lower(),
        "selfcal": "_sc",
        "contsub": "_contsub",
        "uvsub": "_contsub",
        "lid_suffix": f"_{lid}",
        "suffix": "_product",
        "product": "product",
        "resolution": "natural",
        "weighting": "natural",
        "beam": "pb",
        "smoothing": "smooth",
        "extension": ".fits",
    }
    context.update(values)

    outputs: dict[str, str] = {}
    search_patterns: dict[str, str] = {}
    for product in cfg.naming.describe():
        rendered = cfg.naming.render(product, **context)
        if product.startswith("search_"):
            search_patterns[product] = rendered
        else:
            outputs[product] = rendered

    return {
        "configuration": {
            "config_file": str(cfg.config_file),
            "base_dir": str(cfg.base_dir),
        },
        "templates": cfg.naming.describe(),
        "outputs": outputs,
        "search_patterns": search_patterns,
    }
