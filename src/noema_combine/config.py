"""Configuration loader for NOEMA Combine package."""

import os
import warnings
import configparser
import yaml
import numpy as np
from importlib.resources import files


class Config:
    """Singleton configuration class for NOEMA Combine."""

    _instance = None

    def __new__(cls):
        """Ensure only one instance of Config exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize configuration on first use only."""
        if self._initialized:
            return

        self._load_config_file()
        self._load_catalogues()
        self._load_telescope_params()
        self._load_line_data()
        self._load_file_handling()
        self._initialized = True

    def _load_config_file(self):
        """Load the main configuration file."""
        self.config = configparser.ConfigParser()
        config_file = "config.ini"

        if os.path.isfile(config_file):
            self.config.read(config_file)
        else:
            pack_file = str(files("noema_combine").joinpath(config_file))
            self.config.read(pack_file)

    def _load_catalogues(self):
        """Load source and line catalogues."""
        # Load source catalogue
        self.file_source_catalogue = self.config["catalogues"]["source_catalogue"]
        if not os.path.isfile(self.file_source_catalogue):
            self.file_source_catalogue = str(
                files("noema_combine").joinpath(self.file_source_catalogue)
            )
            if not os.path.isfile(self.file_source_catalogue):
                raise FileNotFoundError(
                    f"File not found: {self.config['catalogues']['source_catalogue']}"
                )

        with open(self.file_source_catalogue, "r") as fh:
            self.region_catalogue: dict[str, dict[str, str]] = yaml.safe_load(fh)

        # Load line catalogue
        self.file_line_catalogue = self.config["catalogues"]["line_catalogue"]
        if not os.path.isfile(self.file_line_catalogue):
            self.file_line_catalogue = str(
                files("noema_combine").joinpath(self.file_line_catalogue)
            )
            if not os.path.isfile(self.file_line_catalogue):
                raise FileNotFoundError(
                    f"File not found: {self.config['catalogues']['line_catalogue']}"
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

    @property
    def uvt_dir(self) -> str:
        """Get UVT directory."""
        return self.config["folders"]["uvt_dir"]

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
            return self.config["folders"]["dir_30m"]
        return self.config["folders"]["dir_sd"]

    @property
    def uvt_dir_out(self) -> str:
        """Get output UVT directory."""
        return self.config["folders"]["uvt_dir_out"]

    @property
    def inputdir(self) -> list[str]:
        """Get input directories."""
        inputdir_str = self.config["folders"]["inputdir"]
        return [path.strip() for path in inputdir_str.split(",")]


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
    cfg = Config()  # Creates new instance
    _config = cfg
    if config_file:
        cfg.config.read(config_file)
    return cfg
