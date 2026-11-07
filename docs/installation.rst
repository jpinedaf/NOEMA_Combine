Installing NOEMA_Combine
========================

Requirements
------------
The following packages are required to run the code:

* astropy
* numpy
* pyyaml
 
 
Installation
------------
To install the latest stable release, you can type::
    
    pip install NOEMA_Combine


Developer version
-----------------
Install by cloning locally the repository on `GitHub <https://github.com/jpinedaf/NOEMA_Combine>`_.
If you want to install the latest developer version of the ``NOEMA_Combine`` code, you
can do so from the git repository::

    git clone https://github.com/jpinedaf/NOEMA_Combine.git
    cd NOEMA_Combine
    pip install .

Documentation dependencies
---------------------------
To build the documentation locally, install the optional documentation
dependencies with::

    pip install .[docs]

Development dependencies
------------------------
Install the test and code-quality tools with the ``dev`` extra::

    pip install .[dev]

GILDAS runtime
--------------
GILDAS is an external runtime dependency and is not installed by this Python
package. Workflows that only generate scripts can be used without GILDAS by
passing ``execute=False``. To execute generated CLASS, CLIC, or MAPPING
scripts, install GILDAS separately and configure its command or setup function
in the ``[gildas]`` section of the project configuration.

Then build the HTML documentation with::

    sphinx-build -W -b html docs /tmp/noema-combine-docs

