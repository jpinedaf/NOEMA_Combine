How to Configure Different Aspects of NOEMA_Combine
===================================================

Folders and File Handling
-------------------------

The main configuration options for NOEMA_Combine are set using configuration files. 
These files allow you to specify folders, file handling options, and other 
parameters used throughout the package.
The file name is `config.ini` and an example configuration file is shown below.   

.. code-block:: ini

    [folders]
    uvt_dir = D/
    uvt_dir_out = D30m/
    dir_sd = 30m/
    inputdir = raw_data/, additional_data/, more_data/

    [catalogues]
    line_catalogue = line_catalogue_3mm.csv
    source_catalogue = region_catalogue.yml

    [file_handling]
    ignorefiles_1 = raw_data/FTSOdp20220220.30m
    ignorefiles_2 = raw_data/FTSOdp20220731.30m

    [file_extensions]
    selfcal = _sc
    uvsub = _contsub

    [single_dish]
    telescope = iram30m

The different sections of the configuration file are described below:

- **[folders]**: This section specifies the directories used for input and output data. 
    - `uvt_dir`: Folder with calibrated uv-tables.
    - `uvt_dir_out`: Folder to store calibrated uv-tables output.
    - `dir_sd`: Folder to store calibrated and gridded single dish data.
    - `inputdir`: list of directories on which to search for raw single dish data.
- **[catalogues]**: This section allows you to specify the line and source catalogue files used in the analysis.
    - `line_catalogue`: File containing the line catalogue. It is a CSV file with the list of lines, spectroscopic parameters and processing parameters (see below).
    - `source_catalogue`: File containing the source catalogue. It is a YAML file with the list of sources and their properties (see below).
- **[file_handling]**: Here, you can list files to be ignored during processing. 
  This is useful for excluding specific datasets that may not be relevant, or to avoid unreliable scans.
- **[file_extensions]**: This section defines custom file extensions for self-calibrated and continuum-subtracted files.
- **[single_dish]**: This section specifies the single dish telescope used for the observations. 
  This information is important for correctly processing the single dish data, as different telescopes may have different data formats and characteristics.
  Currently, the only supported telescopes are IRAM 30m ("iram30m") and APEX ("apex"), but support for other telescopes may be added in the future.


Avoid Bad Single Dish Scans
---------------------------

In some cases, certain scans from the single dish telescope may be unreliable or contain bad data.
To avoid processing these bad scans, you can specify them in the configuration file
under the **[file_handling]** section using the ``ignorefiles_1`` and ``ignorefiles_2`` options.
For example:

.. code-block:: ini

    [file_handling]
    ignorefiles_1 = raw_data/FTSOdp20220220.30m


The following ``CLASS`` script will create a new single dish file excluding the bad scans. 
Here from scan 1 until 53, the **LO** and **UO** scans are compromised and 
will be removed.
The output file will be named ``FTSOdp20220220_fix.30m`` and when combined with 
**[file_handling]** this ensures that only the right scans are processed to 
make the cubes.

.. code-block:: fortran

    !
    ! script to comment remove compromised scans seen on 2022-feb-21
    !
    file in FTSOdp20220220.30m
    file out FTSOdp20220220_fix.30m single

    set scan 1 53
    ! only inner units are kept
    set telescope 30ME0*I-*
    find
    get zero
    sic message class s-i
    for i 1 to found
        get n
        write
    next

    !
    ! now save all other data
    !
    set scan 54 *
    set telescope *
    find
    get zero
    for i 1 to found
        get n
        write
    next
    sic message class s+i


Line and Source Catalogues
--------------------------
The line and source catalogues are essential components of the NOEMA_Combine package,
providing necessary information for data processing and analysis.  

- **Line Catalogue**: This is a CSV file that contains a list of spectral lines along with their spectroscopic parameters and processing parameters. 
  Each row in the CSV file corresponds to a different spectral line, and the columns include information such as line frequency, transition details, and any specific processing instructions.
- **Source Catalogue**: This is a YAML file that contains a list of sources and their properties. 
  Each entry in the YAML file represents a different source, with details such as source


Source Catalogue
^^^^^^^^^^^^^^^^

The source catalogue is a YAML file that contains a list of sources and their properties.
Each entry in the YAML file represents a different source, and 
an example of a source catalogue entry in YAML format is shown below:

.. code-block:: yaml

    L1448N:
    RA0: "3h25m36.44s"
    Dec0: "30d45m18.3s"
    height: "33 arcsec"
    width: "30 arcsec"
    fig_width: 6.0
    fig_height: 6.0
    Vlsr: 9.0
    source_sd: "L1448N"
    source_out: "L1448N"
    B5-IRS1:
    RA0: "03h47m41.591s"
    Dec0: "32d51m43.672s"
    height: "40 arcsec"
    width: "40 arcsec"
    fig_width: 6.0
    fig_height: 6.0
    Vlsr: 9.0
    source_sd: "B5-IRS1 B5-Cond*"
    source_out: "B5-IRS1"

- The ``RA0`` and ``Dec0`` fields specify the coordinates of the source to be used for the single dish cubes.
- The ``Vlsr`` is also used for the single dish gridding, and it is in ``km/s``, it is also used to extract uv-tables around the systemic velocity of the source.
- The ``source_sd`` field is used to identify the single dish data files corresponding to the source. It is a string that can include a list of names to be later used in the ``find /source source_sd`` within ``CLASS`` 
- The ``source_out`` field specifies the name to be used for output files related to the source.

Line Catalogue
^^^^^^^^^^^^^^

The line catalogue is a CSV file that contains a list of spectral lines along with their spectroscopic parameters and processing parameters. 
The first line of the CSV file contains the column headers, and each subsequent row corresponds to a different spectral line.

An example of a line catalogue entry in CSV format is shown below:

.. code-block:: text

    #name,QN(filename),freq(GHz),mol(plot),QN(plot),Aul(logs^-1),Eul(K),cat,NOEMAbb,unit,width(km/s),30msetup,30mbb,30mwidth(km/s),30mline(km/s)
    SO,5_5_4_4,215.22065300,SO,"5(5)-4(4)",-3.91491,44.10371,JPL,lo,l009l048,10.0,Setup1,LO,20,5.0
    DCO+,3_2,216.11258220,DCO\u+,"3-2",-2.62283,20.74365,CDMS,lo,l012l051,10.0,Setup2,LO,20,3.0
    c-HCCCH,3_3_0_2_2_1,216.27875600,c-C\d3H\d2,"3(3,0)-2(2,1)",-3.59211,19.46594,CDMS,lo,l013l052,10.0,Setup2,LO,20,3.0


- The ``#name`` column specifies the common name of the spectral line to be used as identifing the molecule and used in the filename.
- The ``QN(filename)`` column indicates the quantum numbers used for the line identification and in the filename.
- The ``freq(GHz)`` column provides the frequency of the line in ``GHz``.
- The ``mol(plot)`` and ``QN(plot)`` columns specify the molecule and quantum numbers to be used for the ``GILDAS`` header.
- The ``Aul(logs^-1)`` and ``Eul(K)`` columns to provide the Einstein A coefficient and upper energy level of the transition, good information to access easily.
- The ``cat`` column indicates the catalogue source (e.g., JPL, CDMS).
- The ``NOEMAbb`` column specifies whether the line is observed with the lower sideband (``lo`` or ``li``) or upper sideband (``ui`` or ``uo``).
- The ``unit`` column indicates the unit for processing. This is the narrow unit name, this is used for the folder and filename.
- The ``width(km/s)`` column specifies the velocity width for processing in ``km/s``. It is used to 
- The ``30msetup`` and ``30mbb`` columns refer to the 30m setup (e.g., Setup1 or Setup2) and the unit that covers the line (``LO``, ``LI``, ``UI``, or ``UO``). This information is not used currently when serching for the scans covering the lines.
- The ``30mwidth(km/s)`` and ``30mline(km/s)`` columns provide parameters specific to 30m data processing. 
    - ``30mwidth(km/s)`` is the with of the cube to be made around the line in ``km/s`` (cubes covers ``Vlsr - 30mwidth(km/s)`` until ``Vlsr + 30mwidth(km/s)``).
    - ``30mline(km/s)`` is the velocity width used to define the window in ``CLASS`` to avoid the line for baseline fitting. The baseline is using the following range of velocities: from ``Vlsr - 30mwidth(km/s)`` until ``Vlsr - 30mline(km/s)``  and ``Vlsr + 30mline(km/s)`` until ``Vlsr + 30mwidth(km/s)``.