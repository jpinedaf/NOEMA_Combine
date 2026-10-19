"""Configuration loader for NOEMA Combine package."""

import os
import re
import warnings
import configparser
from pathlib import Path
import yaml
import numpy as np
from importlib.resources import files
from .naming import FileNaming


def _normalize_window(value: str) -> str:
    """Normalize a window identifier without importing workflow modules."""
    text = "".join(str(value).strip().lower().split())
    match = re.fullmatch(r"l(\d+)l(\d+)", text)
    if match:
        return f"l{int(match.group(1)):03d}l{int(match.group(2)):03d}"
    return text


class Config:
    """Singleton configuration class for NOEMA Combine."""

    _instance = None

    def __new__(cls, config_file: str | None = None, isolated: bool = False):
        """Ensure only one instance of Config exists."""
        if isolated:
            instance = super().__new__(cls)
            instance._initialized = False
            instance._isolated = True
            return instance
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._isolated = False
        return cls._instance

    def __init__(self, config_file: str | None = None, isolated: bool = False):
        """Initialize configuration on first use only."""
        if self._initialized and not self._isolated:
            return

        self._load_config_file(config_file)
        self._load_catalogues()
        self._load_telescope_params()
        self._load_line_data()
        self._load_file_handling()
        self._load_naming()
        self._load_continuum_ranges()
        self._load_imaging()
        self._initialized = True

    def _load_config_file(self, config_file: str | None = None):
        """Load the main configuration file."""
        self.config = configparser.ConfigParser()
        requested_file = Path(config_file).expanduser() if config_file else None
        if requested_file is not None:
            if not requested_file.is_file():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            # Start from packaged defaults, then apply project overrides.
            pack_file = str(files("noema_combine").joinpath("config.ini"))
            self.config.read(pack_file)
            self.config.read(str(requested_file))
            self.config_file = requested_file.resolve()
            self._resolve_relative_paths = True
        elif os.path.isfile("config.ini"):
            self.config.read("config.ini")
            self.config_file = Path("config.ini").resolve()
            self._resolve_relative_paths = self.config.has_section("project")
        else:
            pack_file = str(files("noema_combine").joinpath("config.ini"))
            self.config.read(pack_file)
            self.config_file = Path(pack_file).resolve()
            # Keep the historical package defaults relative to the process cwd.
            self._resolve_relative_paths = False

        configured_base = self.config.get("project", "base_dir", fallback=None)
        if configured_base:
            base = Path(configured_base).expanduser()
            if not base.is_absolute():
                base = self.config_file.parent / base
            self._resolve_relative_paths = True
        elif self._resolve_relative_paths:
            base = self.config_file.parent
        else:
            base = Path.cwd()
        self._base_dir = base.resolve()

    def _resolve_path(self, value: str) -> str:
        """Resolve a configured path while preserving legacy relative paths."""
        path = Path(value).expanduser()
        if path.is_absolute() or not self._resolve_relative_paths:
            return str(path)
        return str((self._base_dir / path).resolve())

    def _load_catalogues(self):
        """Load source and line catalogues."""
        # Load source catalogue
        configured_source = self.config["catalogues"]["source_catalogue"]
        self.file_source_catalogue = self._resolve_path(configured_source)
        if not os.path.isfile(self.file_source_catalogue):
            self.file_source_catalogue = str(
                files("noema_combine").joinpath(configured_source)
            )
            if not os.path.isfile(self.file_source_catalogue):
                raise FileNotFoundError(
                    f"File not found: {configured_source}"
                )

        with open(self.file_source_catalogue, "r") as fh:
            self.region_catalogue: dict[str, dict[str, str]] = yaml.safe_load(fh)

        # Load line catalogue
        configured_line = self.config["catalogues"]["line_catalogue"]
        self.file_line_catalogue = self._resolve_path(configured_line)
        if not os.path.isfile(self.file_line_catalogue):
            self.file_line_catalogue = str(
                files("noema_combine").joinpath(configured_line)
            )
            if not os.path.isfile(self.file_line_catalogue):
                raise FileNotFoundError(
                    f"File not found: {configured_line}"
                )

    def _load_telescope_params(self):
        """Load single dish telescope parameters."""
        # File extensions from config file
        self.selfcal_ext = self.config.get("file_extensions", "selfcal", fallback="_sc")
        self.uvsub_ext = self.config.get("file_extensions", "uvsub", fallback="_uvsub")

        # Handle single dish parameters (defaults to IRAM 30m)
        telescope_sd = self.config.get("single_dish", "telescope", fallback="IRAM30m")
        if telescope_sd.lower() == "iram30m":
            self.file_extensions_sd = ".30m"
            self.telescope_class = "30M-MRT"
        elif telescope_sd.lower() == "apex":
            self.file_extensions_sd = ".apex"
            self.telescope_class = "APEX"
        else:
            raise ValueError(f"Unknown single dish telescope: {telescope_sd}")

    def _load_line_data(self):
        """Load line catalogue data."""
        (
            self.line_name,
            self.qn,
            self.freq,
            self.name_str,
            self.qn_str,
            self.Lid,
            self.vel_width,
            self.vel_width_sd,
            self.vel_width_base_sd,
        ) = np.loadtxt(
            self.file_line_catalogue,
            dtype="U",
            delimiter=",",
            quotechar='"',
            comments="#",
            skiprows=1,
            usecols=(0, 1, 2, 3, 4, 9, 10, 13, 14),
            unpack=True,
        )

    def _load_file_handling(self):
        """Load file handling configuration."""
        self.ignorefiles: list[str] = []
        for key, item in self.config.items("file_handling"):
            if key.startswith("ignorefiles"):
                self.ignorefiles.append(item)

    def _load_naming(self):
        """Load optional naming templates while retaining legacy defaults."""
        templates = {}
        self.naming_custom = False
        if self.config.has_section("naming"):
            self.naming_custom = self.config.has_option("naming", "root")
            for key, value in self.config.items("naming"):
                if key != "root":
                    templates[key] = value
                    self.naming_custom = True

        root = self._resolve_path(
            self.config.get("naming", "root", fallback=".")
        )
        self.naming = FileNaming(
            templates,
            root=root,
            uvt_root=self.uvt_dir,
            uvt_out_root=self.uvt_dir_out,
            sd_root=self.dir_sd,
            selfcal_suffix=self.selfcal_ext,
            uvsub_suffix=self.uvsub_ext,
            sd_ext=self.file_extensions_sd,
        )

    def _load_continuum_ranges(self):
        """Load optional per-window continuum subtraction channel ranges."""
        self.continuum_wideband_ranges: dict[str, str] = {}
        self.continuum_narrowband_ranges: dict[str, str] = {}
        self.narrowband_windows: list[str] = [
            f"l{i:03d}l{i + 39:03d}" for i in range(9, 48)
        ]
        if self.config.has_section("narrowband"):
            configured_windows = self.config.get("narrowband", "windows", fallback="")
            if configured_windows.strip():
                self.narrowband_windows = [
                    _normalize_window(value)
                    for value in configured_windows.split(",")
                    if value.strip()
                ]
        if self.config.has_section("continuum_subtraction"):
            for key, value in self.config.items("continuum_subtraction"):
                if key.startswith("wideband_") and value.strip():
                    self.continuum_wideband_ranges[_normalize_window(key[9:])] = value.strip()
        if self.config.has_section("narrowband_channel_ranges"):
            for key, value in self.config.items("narrowband_channel_ranges"):
                if value.strip():
                    self.continuum_narrowband_ranges[_normalize_window(key)] = value.strip()

    def _load_imaging(self):
        """Load optional dirty-imaging window settings."""
        self.imaging_wideband_windows = ["lo", "li", "ui", "uo"]
        self.imaging_include_narrowband = True
        if self.config.has_section("imaging"):
            configured = self.config.get("imaging", "wideband_windows", fallback="")
            if configured.strip():
                self.imaging_wideband_windows = [
                    value.strip().lower()
                    for value in configured.split(",")
                    if value.strip()
                ]
            self.imaging_include_narrowband = self.config.getboolean(
                "imaging", "include_narrowband", fallback=True
            )
        self.cleaning_weighting = self.config.get("cleaning", "weighting", fallback="natural")
        self.cleaning_threshold_factor = self.config.getfloat(
            "cleaning", "threshold_factor", fallback=5.0
        )
        self.cleaning_niter = self.config.getint("cleaning", "niter", fallback=0)
        self.cleaning_primary_beam = self.config.getboolean(
            "cleaning", "primary_beam_correction", fallback=True
        )
        self.cleaning_pb_truncate = self.config.getint(
            "cleaning", "primary_beam_truncate", fallback=20
        )

    def _reload_all(self):
        """Reload all configuration sections."""
        self._load_catalogues()
        self._load_telescope_params()
        self._load_line_data()
        self._load_file_handling()
        self._load_naming()
        self._load_continuum_ranges()
        self._load_imaging()

    @property
    def uvt_dir(self) -> str:
        """Get UVT directory."""
        return self._resolve_path(self.config["folders"]["uvt_dir"])

    @property
    def dir_sd(self) -> str:
        """Get single dish data directory."""
        if self.config.has_option("folders", "dir_30m"):
            warnings.warn(
                "The 'dir_30m' configuration option is deprecated and will be removed in a future version. "
                "Use 'dir_sd' instead to specify the directory for single dish data.",
                DeprecationWarning,
                stacklevel=2,
            )
            return self._resolve_path(self.config["folders"]["dir_30m"])
        return self._resolve_path(self.config["folders"]["dir_sd"])

    @property
    def uvt_dir_out(self) -> str:
        """Get output UVT directory."""
        return self._resolve_path(self.config["folders"]["uvt_dir_out"])

    @property
    def inputdir(self) -> list[str]:
        """Get input directories."""
        inputdir_str = self.config["folders"]["inputdir"]
        return [self._resolve_path(path.strip()) for path in inputdir_str.split(",")]

    @property
    def base_dir(self) -> Path:
        """Get the project base directory used for relative paths."""
        return self._base_dir

    @property
    def gildas_execute(self) -> bool:
        """Whether generated GILDAS scripts should execute by default."""
        return self.config.getboolean("gildas", "execute", fallback=True)

    @property
    def gildas_workdir(self) -> str:
        """Get the working directory for GILDAS commands."""
        return self._resolve_path(self.config.get("gildas", "workdir", fallback="."))

    @property
    def gildas_commands(self) -> dict[str, str]:
        """Get configured GILDAS executable names."""
        return {
            name: self.config.get("gildas", name, fallback=name)
            for name in ("class", "mapping", "clic")
        }

    @property
    def gildas_setup(self) -> str:
        """Get the optional shell command used to initialize GILDAS."""
        return self.config.get("gildas", "setup", fallback="").strip()

    @property
    def gildas_shell(self) -> str:
        """Get the shell used for optional GILDAS setup commands."""
        return self.config.get("gildas", "shell", fallback="/bin/bash").strip()

    @property
    def gildas_timeout(self) -> float | None:
        """Get the optional GILDAS command timeout in seconds."""
        value = self.config.get("gildas", "timeout", fallback="").strip()
        return float(value) if value else None

    def make_gildas_runner(self, **kwargs: object):
        """Create a GILDAS runner using this configuration's defaults."""
        from .gildas import GildasRunner

        defaults = {
            "execute": self.gildas_execute,
            "workdir": self.gildas_workdir,
            "commands": self.gildas_commands,
            "timeout": self.gildas_timeout,
            "setup": self.gildas_setup,
            "shell": self.gildas_shell,
        }
        defaults.update(kwargs)
        return GildasRunner(**defaults)


# Global configuration instance
_config = Config()


# Module-level accessors for backward compatibility
def get_config() -> Config:
    """Get the global configuration instance."""
    return _config


def reload_config(config_file: str | None = None):
    """Reload configuration from a specific file."""
    global _config
    Config._instance = None  # Reset singleton
    cfg = Config(config_file=config_file)  # Creates new instance
    _config = cfg
    # Keep data_handler's compatibility aliases synchronized after a reload.
    try:
        from . import data_handler

        data_handler.refresh_config()
    except ImportError:
        # This can occur during package import before data_handler is available.
        pass
    return cfg
