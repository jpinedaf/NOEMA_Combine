# NOEMA_Combine

![PyPI - License](https://img.shields.io/pypi/l/NOEMA_Combine?color=green)
![PyPI - Version](https://img.shields.io/pypi/v/NOEMA_Combine)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fjpinedaf%2FNOEMA_Combine%2Fmaster%2Fpyproject.toml)
[![codecov](https://codecov.io/gh/jpinedaf/NOEMA_Combine/graph/badge.svg?token=U9QXKNY7UK)](https://codecov.io/gh/jpinedaf/NOEMA_Combine)



Python functions for processing NOEMA and 30-m data.

The package supports:

- generating calibrated UV tables;
- reducing single-dish data and preparing it for combination;
- configurable continuum subtraction;
- dirty imaging and CLEAN imaging for wideband and narrowband windows;
- UV restoration of continuum images, cubes, and individual lines; and
- preparation of combined NOEMA and single-dish products.

The imaging workflows generate GILDAS scripts and execute them by default.
Pass ``execute=False`` to generate scripts without running GILDAS. Folder and
filename conventions are configured through naming templates; see
``docs/configuration_files.rst`` and ``examples/config_raw_scripts.ini``.

To start a project without copying files from the installation, create an
editable configuration and starter line catalogue in the current directory:

```python
from noema_combine import create_project_files

create_project_files(style="prodige")
```

Use `style="propstar"` for the ProPStar naming profile. PRODIGE defaults to
the packaged 1 mm PRODIGE catalogue, while ProPStar defaults to the packaged 3 mm
catalogue. The starter `region_catalogue.yml` is also copied. Existing files
are protected unless `overwrite=True` is supplied.


Credits
-------
-------

This is developed by:
* Jaime E Pineda ([@jpinedaf](http://github.com/jpinedaf))
