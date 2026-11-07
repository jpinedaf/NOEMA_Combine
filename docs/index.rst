Welcome to NOEMA_Combine's documentation!
==========================================

The ``NOEMA_Combine`` is a Python package to help with the processing of 30m and NOEMA data. 
It is developed to support a simple data reduction of single-dish cubes and the combination of single-dish and interferometric data in the GILDAS package.
Note that it is designed for single-dish mapping observed with position switching, and not for frequency switching (this could be further configured and developed as a new feature).

The package includes the following capabilities:

* Generate calibrated UV tables.
* Reduce single-dish data and prepare it for combination.
* Subtract continuum emission with configurable channel ranges.
* Create dirty and CLEAN images for wideband and narrowband data.
* Restore continuum images, spectral cubes, and individual-line products.
* Combine UV and single-dish data.


Getting Started
^^^^^^^^^^^^^^^

.. toctree::
     :maxdepth: 2
     :includehidden:

     installation.rst

Configuration files
^^^^^^^^^^^^^^^^^^^

.. toctree::
     :maxdepth: 2

     configuration_files.rst

Creating uvt tables
^^^^^^^^^^^^^^^^^^^
.. toctree::
     :maxdepth: 2

     generate_uvt.rst

Imaging workflows
^^^^^^^^^^^^^^^^^
.. toctree::
     :maxdepth: 2

     imaging_workflows.rst

Line extraction
^^^^^^^^^^^^^^^
.. toctree::
     :maxdepth: 2

     line_extraction.rst
     

Reduce single dish data
^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
     :maxdepth: 2

     reduce_single_dish.rst


Combination of single dish and interferometric data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
     :maxdepth: 2

     merge_sd_interferometer.rst



Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
