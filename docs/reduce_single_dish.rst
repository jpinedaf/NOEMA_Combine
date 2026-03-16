Reducing Single Dish Data
=========================

Overview
--------

The NOEMA Combine package provides functionality to reduce single dish data from various telescopes (IRAM 30m, APEX, etc.) and prepare it for merging with interferometric observations.
This guide walks through the full workflow for a specific molecular line: reduction to Ta* and preparation of merge-ready products in Tmb.

Basic Usage
-----------

To reduce single dish data, use the :py:func:`~noema_combine.data_handler.line_reduce_sd` function:

.. code-block:: python

    import noema_combine

    source_name = "B5"
    molecule = "N2D+"
    quantum_number = "1-0"

    noema_combine.data_handler.line_reduce_sd(source_name, molecule, quantum_number)

This function will:

1. Locate the source and line parameters from the catalogues
2. Find all input single dish files matching the configured file extensions
3. Extract spectra at the specified frequency with the correct velocity window
4. Apply baseline subtraction and coordinate centering
5. Regrid the data and output to the configured format

The reduction step supports all configured single-dish telescopes (including IRAM 30m and APEX) and produces reduced spectra on the Ta* scale.

Required Parameters
-------------------

**source_name** : str
    Name of the source to reduce (e.g., ``"B5"``, ``"B5-IRS1"``).
    Must exist in the ``region_catalogue`` configuration.

**molecule** : str
    Molecule name (e.g., ``"CO"``, ``"N2D+"``, ``"HCN"``).
    Must exist in the line catalogue.

**quantum_number** : str
    Quantum numbers of the line (e.g., ``"1-0"``, ``"N=1-0,J=3/2-1/2,F=1/2-1/2"``).
    Combined with the molecule name, must uniquely identify a line in the catalogue.

Configuration
-------------

The reduction process uses settings from your configuration file:

- **inputdir** : List of directories containing input single dish data files
- **dir_sd** : Output directory for reduced single dish data
- **file_extensions_sd** : File extension pattern for single dish data (e.g., ``.fits``)
- **telescope_sd** : Specification of the single dish telescope type
- **telescope_class** : Telescope class for GILDAS/CLASS processing
- **ignorefiles** : List of file patterns to skip during processing
- **vel_width_sd** : Velocity width for spectral extraction (from line catalogue)
- **vel_width_base_sd** : Velocity width for baseline definition (from line catalogue)

Processing Steps
----------------

The reduction involves the following steps:

1. **Source Parameter Retrieval**: The function retrieves source coordinates, LSR velocity, and other metadata
2. **File Discovery**: Scans input directories for matching single dish data
3. **Frequency Correction**: Applies Doppler correction based on source LSR velocity
4. **GILDAS/CLASS Processing**:
   - Loads each input file
   - Finds observations at the target frequency
   - Modifies observation parameters (line name, frequency, source name, coordinate centering)
   - Extracts spectra within the velocity window
   - Applies first-order baseline subtraction
5. **Output Generation**: Creates output files in the configured format (CLASS, lmv, and tab)

Output Files
------------

The reduced data will be saved to a file with the individual spectra and a regridded cube in the specified output directory. 
The filenames will follow the pattern:

.. code-block:: text

    {dir_sd}/{source_name}_{molecule}_{quantum_numbers}{single_dish_extension}
    {dir_sd}/{source_name}_{molecule}_{quantum_numbers}.lmv
    {dir_sd}/{source_name}_{molecule}_{quantum_numbers}.tab

For example:

.. code-block:: text

    /path/to/data/B5_N2D+_1-0{single_dish_extension}
    /path/to/data/B5_N2D+_1-0.lmv

For IRAM 30m and APEX setups, typical reduced output names are:

.. code-block:: text

    /path/to/data/B5-IRS1_CO_1_0.30m
    /path/to/data/B5-IRS1_CO_1_0.apex

Preparing Data for Merging
==========================

After reducing single dish data, prepare it for merging with NOEMA observations using:

.. code-block:: python

    noema_combine.data_handler.line_prepare_merge(source_name, molecule, quantum_number)

This function:

1. Reads the reduced single dish data
2. Resolves source and line metadata from the configured catalogues
3. Builds output names for single-dish and merged products
4. Rewrites CLASS headers (line name, frequency, source, and beam efficiency)
5. Regrids the spectral axis to match NOEMA observations
6. Updates antenna efficiency to convert to Main Beam Temperature (Tmb)
7. Generates merge-ready output files in the merge directory, including a ``.tab`` product matched to the NOEMA UV table spectral setup

By default, beam efficiency is computed with the Ruze formula. You can override this with the ``beam_eff`` argument.

Example Workflow
----------------

.. code-block:: python

    import noema_combine

    # Step 1: Reduce single dish data
    noema_combine.data_handler.line_reduce_sd("B5", "N2D+", "1-0")

    # Step 2: Prepare for merging
    noema_combine.data_handler.line_prepare_merge("B5", "N2D+", "1-0")

    # Optional: user-defined beam efficiency instead of default Ruze estimate
    noema_combine.data_handler.line_prepare_merge("B5", "N2D+", "1-0", beam_eff=0.82)

    # Task complete - data is ready for MAPPING uv_merge

Troubleshooting
---------------

**No files found in input directory**
    Verify that ``inputdir`` in your configuration points to directories containing data files with the correct extension specified in ``file_extensions_sd``.

**Line not found in catalogue**
    Ensure the molecule name and quantum numbers exactly match entries in the line catalogue. Use ``get_line_param()`` to verify available lines.

**Source not found**
    Check that the source name exists in ``region_catalogue`` with proper coordinate and velocity information.

**Velocity window issues**
    The velocity window is determined from ``vel_width_sd`` and ``vel_width_base_sd`` in the line catalogue. Verify these are appropriate for your science goals.

See Also
--------

- :py:func:`~noema_combine.data_handler.line_make_uvt` - Extract NOEMA data for a specific line
- :py:func:`~noema_combine.data_handler.get_source_param` - Retrieve source parameters
- :py:func:`~noema_combine.data_handler.get_line_param` - Find line parameters in catalogue