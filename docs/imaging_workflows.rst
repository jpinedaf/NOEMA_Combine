Imaging Workflows
=================

NOEMA_Combine provides Python workflows for continuum subtraction, dirty
imaging, CLEAN imaging, and UV restoration. Each workflow can generate a
GILDAS script without running it, or execute the script through the configured
``GildasRunner``.

Execution modes
---------------

GILDAS execution is enabled by default. Set ``execute=False`` for a
script-only run. The generated script is retained in both modes when it is
written to the configured naming path.

The default can also be set in the configuration file:

.. code-block:: ini

    [gildas]
    execute = false
    workdir = .
    mapping = mapping
    # Set this when GILDAS is not already available in PATH.
    setup = gildas_latest
    # Use these when setup is defined as a shell function.
    setup_file = ~/.bashrc
    interactive = true

Continuum subtraction
----------------------

For a wideband window, use :func:`noema_combine.make_continuum_subtraction`:

.. code-block:: python

    from noema_combine import make_continuum_subtraction

    result = make_continuum_subtraction(
        "B5",
        "CD",
        "li",
        no_cube=True,
        execute=False,
    )

For narrowband windows, use
:func:`noema_combine.make_narrowband_continuum_subtraction`:

.. code-block:: python

    from noema_combine import make_narrowband_continuum_subtraction

    results = make_narrowband_continuum_subtraction(
        "B5",
        "CD",
        ["l009l048", "l010l049"],
        execute=False,
    )

Channel ranges are optional. The precedence is:

1. An explicit ``channel_range`` or ``channel_ranges`` argument.
2. A range file, when the wideband workflow is given one.
3. A per-window range in ``[continuum_subtraction]`` or
   ``[narrowband_channel_ranges]``.
4. ``uv_baseline 0`` when no range is available.

When exactly one narrowband window is requested, a single ``channel_range``
can be supplied directly:

.. code-block:: python

    make_narrowband_continuum_subtraction(
        "B5",
        "CD",
        ["l034l073"],
        channel_range="0 20 3200 3280 4800 4900 8172 8192",
        execute=False,
    )

Use ``channel_ranges`` with a dictionary when processing multiple windows.

The narrowband subtraction script operates on the existing UVT metadata and
does not emit a ``modify`` command. Its generated script therefore contains
the input name, ``go setup``, the baseline command, and the output write.

Dirty images
------------

Use :func:`noema_combine.make_dirty_images` for one or more wideband or
narrowband windows:

.. code-block:: python

    from noema_combine import make_dirty_images

    results = make_dirty_images(
        "B5",
        "CD",
        windows=["li", "l009l048"],
        selfcal=True,
        contsub=True,
        execute=False,
    )

If ``windows`` is omitted, the workflow processes the configured wideband
windows and, when enabled, the configured narrowband windows.

CLEAN images
------------

Use :func:`noema_combine.make_clean_images`. The legacy ``baseband`` argument
remains supported for wideband processing; ``windows`` can process wideband
and narrowband windows together:

.. code-block:: python

    from noema_combine import make_clean_images

    results = make_clean_images(
        "B5",
        "CD",
        windows=["li", "l009l048"],
        selfcal=True,
        execute=False,
    )

Clean-image scripts are retained by default, including when GILDAS reports an
error. Use ``keep_script=False`` only when the generated ``.map`` files should
be removed.

The CLEAN method, weighting, threshold, iteration count, and primary-beam
correction are configured in ``[cleaning]``. The supported methods are
``HOGBOM`` (the default) and ``SDI``. A method can also be selected per call:

.. code-block:: python

    results = make_clean_images(..., method="SDI")

The workflow returns the CLEAN image, FITS
export, primary-beam products, generated script, and GILDAS execution result.

UV restoration
--------------

Use :func:`noema_combine.restore_image` to restore a continuum image, a cube,
or an individual line with the corresponding UV data and clean components.
The same function supports wideband and narrowband windows:

.. code-block:: python

    from noema_combine import restore_image

    continuum = restore_image(
        "B5", "CD", windows=["li"],
        product_type="continuum",
        execute=False,
    )

    cube = restore_image(
        "B5", "CD", windows=["l009l048"],
        product_type="cube",
        execute=False,
    )

    line = restore_image(
        "B5", "CD",
        line="CO", qn="1-0", lid="l009l048",
        product_type="line",
        execute=False,
    )

Restoration reads the UV data, clean image, and clean component file. It
produces a UV-restored ``.lmv-clean`` product, a FITS export, and optional
primary-beam-corrected products. The paths are controlled by the
``restore_*`` naming templates described in :doc:`configuration_files`.

Naming and configuration
------------------------

All imaging workflows use the configured naming templates. Wideband,
narrowband, and line restoration can be customized independently with
``restore_*``, ``restore_*_narrowband``, and ``restore_*_line`` templates.
Narrowband folders use ``{lid_pair_folder}`` and filenames use
``{lid_pair_filename}``. Output names use the catalogue ``source_out`` value
when it is available.
See :doc:`configuration_files` and
``examples/config_raw_scripts.ini`` for a complete example.

The workflows return structured result objects. For example:

.. code-block:: python

    result = make_dirty_images("B5", "CD", windows=["li"], execute=False)[0]
    print(result.script_path)
    print(result.execution.succeeded)
