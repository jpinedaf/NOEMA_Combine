Processing Single Dish Data
===========================

This page documents the single-dish processing functions from
``noema_combine.data_handler`` used to prepare data products for
NOEMA + single-dish combination.

After the configuration file is set up with the correct single-dish telescope and file paths (see :doc:`configuration`), the following functions can be used to prepare the single-dish data.

First, we use the :py:func:`noema_combine.data_handler.line_reduce_sd` function to perform a simple reduction of the single-dish data to Ta* scale. This function supports all configured single-dish telescopes, including APEX and IRAM 30m. 
For example:

.. code-block:: python

    from noema_combine.data_handler import line_reduce_sd
    source_name = "B5-IRS1"
    line_i = "CO"
    qn_i = "1-0"
    line_reduce_sd(source_name, line_i, qn_i)

This will produce a reduced single-dish data file in the output directory (``dir_sd``) defined in the config file, for the targeted line with a suffix indicating that it has been reduced (e.g., ``B5-IRS1_CO_1-0_reduced.30m`` or ``B5-IRS1_CO_1-0_reduced.apex``). These data are in Ta*, and an ``lmv``-cube and ``tab``-files are also created.

Next, we use the :py:func:`noema_combine.data_handler.line_prepare_merge` function to prepare the reduced single-dish data for merging with NOEMA data. This function resolves source and line metadata from the configured catalogues, builds output file names for single-dish and merged products, rewrites CLASS headers (line name, frequency, source, beam efficiency), and creates a ``.tab`` product matched to the NOEMA UV table spectral setup in Tmb units.
These data are now ready to be merged with the NOEMA data using the :py:func:`noema_combine.combine_uvt_sd` function.

.. code-block:: python

    from noema_combine.data_handler import line_prepare_merge
    source_name = "B5-IRS1"
    line_i = "CO"
    qn_i = "1-0"
    # uses Ruze formula for beam efficiency by default
    line_prepare_merge(source_name, line_i, qn_i) 
    # user defined beam efficiency
    line_prepare_merge(source_name, line_i, qn_i, Beam_Eff=0.82)

