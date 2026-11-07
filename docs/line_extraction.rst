Extracting individual spectral lines
====================================

Use :py:func:`~noema_combine.extract_line` to extract one catalogue line from
a calibrated, self-calibrated, or continuum-subtracted UV table. The requested
window may be narrowband or broadband:

.. code-block:: python

    from noema_combine import extract_line

    result = extract_line(
        source="B5-IRS1",
        configuration="CD",
        line="N2D+",
        qn="3-2",
        window="l034l073",
        selfcal=True,
        contsub=True,
        execute=False,
    )

The line frequency and GILDAS line label are read from the configured line
catalogue. The function validates that the line is covered by the requested
window before generating the MAPPING script.

Velocity range
--------------

If no range is supplied, the catalogue ``width (km/s)`` is applied around the
source ``Vlsr``. Use ``dv`` for a different symmetric width or provide an
explicit absolute range:

.. code-block:: python

    extract_line(..., dv=5.0)
    extract_line(..., velocity_range=(4.0, 14.0))

Set ``execute=False`` to generate the script without running GILDAS. Scripts
are retained by default and are written using the configured ``line_uvt`` and
``line_script`` naming templates.

Imaging an extracted line
-------------------------

The extracted UV table can be imaged with the same dirty and CLEAN stages used
for full spectral windows:

.. code-block:: python

    from noema_combine import make_line_images

    images = make_line_images(
        source="B5-IRS1",
        configuration="CD",
        line="N2D+",
        qn="3-2",
        window="l034l073",
        selfcal=True,
        contsub=True,
        execute=False,
    )

Set ``dirty=False`` or ``clean=False`` to run only one imaging stage. The
result contains the generated paths and execution records for both stages.

Merged NOEMA and single-dish line cubes
---------------------------------------

Use ``make_merged_line_images`` to prepare a line UV table on a common
velocity grid, combine it with the configured single-dish table, and create
merged dirty and CLEAN products:

.. code-block:: python

    from noema_combine import make_merged_line_images

    merged = make_merged_line_images(
        "B5", "CD", "N2D+", "3-2", "l034l073",
        selfcal=True,
        contsub=True,
        execute=False,
    )

Narrowband windows use ``0.1 km/s`` and wideband windows use ``3 km/s`` by
default. ``velocity_range`` and ``velocity_resolution`` can override these
values. CD and ACD configurations are supported; the result contains the
preparation and imaging scripts as well as the merged products.
