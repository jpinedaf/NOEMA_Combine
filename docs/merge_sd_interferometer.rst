Merging Single Dish and Interferometer Data
=============================================

Overview
--------

This guide describes how to merge single dish (SD) and interferometer data using the NOEMA Combine package. The merging process combines the short-spacing information from single dish observations with the high-resolution interferometer data from NOEMA to produce combined maps with improved uv-coverage.

Preparation Steps
-----------------

Before merging, you need to prepare both the single dish and interferometer data:

1. **Reduce Single Dish Data**

    Use :func:`noema_combine.data_handler.line_reduce_sd` to process the single dish observations:

    .. code-block:: python

         import noema_combine

         noema_combine.data_handler.line_reduce_sd('B5', 'N2D+', '1-0')

    This function:
    - Performs baseline subtraction on the single dish spectra
    - Sets the correct frequency and source coordinates
    - Outputs spectra in Ta* scale
    - Supports all single dish telescopes (IRAM 30m, APEX, etc.)

    For detailed instructions on reducing single dish data, see :doc:`reduce_single_dish`.


2. **Extract Molecular Lines from NOEMA Data**

    Use :func:`noema_combine.data_handler.line_make_uvt` to extract the target line from NOEMA observations:

    .. code-block:: python

         noema_combine.data_handler.line_make_uvt('B5', 'N2D+', '1-0')

    This function:
    - Extracts the specified molecular line from already calibrated NOEMA data
    - Defines the velocity range based on the line catalogue
    - Allows custom velocity ranges via the `dv`, `dv_min`, and `dv_max` parameters

Merging Process
---------------

The merging is performed using :func:`noema_combine.data_handler.line_prepare_merge`:

.. code-block:: python

    noema_combine.data_handler.line_prepare_merge('B5', 'N2D+', '1-0')

This function prepares the single dish data for combination with NOEMA observations by:

1. Reading the reduced single dish data
2. Converting to Tmb scale
3. Regridding the spectral axis to match NOEMA observations
4. Generating output files for further processing

For detailed information about the reduction and preparation steps, see :doc:`reduce_single_dish`.

Complete Example
----------------

Here is a complete workflow for merging single dish and interferometer data:

.. code-block:: python

    import noema_combine

    # Configuration
    source = 'B5'
    molecule = 'N2D+'
    quantum_numbers = '1-0'

    # Step 1: Reduce single dish data
    print(f"Reducing single dish data for {molecule}...")
    noema_combine.data_handler.line_reduce_sd(source, molecule, quantum_numbers)

    # Step 2: Extract line from NOEMA data
    print(f"Extracting {molecule} from NOEMA observations...")
    noema_combine.data_handler.line_make_uvt(source, molecule, quantum_numbers)

    # Step 3: Prepare for merging
    print(f"Preparing data for merging...")
    noema_combine.data_handler.line_prepare_merge(source, molecule, quantum_numbers)

    print("Merging process complete!")

Velocity Range Specification
-----------------------------

By default, velocity ranges are defined in the line catalogue. To use custom velocity ranges:

.. code-block:: python

    # Use a symmetric velocity range around vlsr
    noema_combine.data_handler.line_make_uvt(
        'B5', 'N2D+', '1-0',
        dv=2.5  # Extract [vlsr - 2.5, vlsr + 2.5] km/s
    )

    # Use an asymmetric velocity range
    noema_combine.data_handler.line_make_uvt(
        'B5', 'N2D+', '1-0',
        dv_min=1.0,  # vlsr - 1.0 km/s
        dv_max=3.0   # vlsr + 3.0 km/s
    )

Tips and Best Practices
-----------------------

- Always reduce the single dish data before merging
- Ensure the NOEMA data are properly calibrated before extraction
- Check that the source coordinates in the region catalogue are accurate
- Use the same quantum numbers for both single dish and interferometer data
- Verify the output files exist in the expected directories before proceeding

Troubleshooting
---------------

**No files found in input directory**
     Ensure the input directory path is correct and contains single dish data files with the expected extension.

**Line not found in catalogue**
     Verify that the molecule name and quantum numbers match the line catalogue exactly.

**Frequency mismatch**
     Check that the frequency in the line catalogue matches the observation setup.