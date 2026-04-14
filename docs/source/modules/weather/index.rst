weather — Weather Data Processing
==================================

The ``buem.weather`` package acquires, processes, and exports
COSMO-REA6 reanalysis data from the DWD OpenData archive into compressed
NetCDF-4 files ready for BuEM's thermal model.

It is designed as a **standalone module** — it can run independently on an
HPC cluster or in a container without the rest of the BuEM codebase.

.. toctree::
   :maxdepth: 2

   overview
   pipeline
   grid_and_projections
   containerisation
   cli
   csv_weather


Version History
---------------

See the project-wide `CHANGELOG.md <https://github.com/SomadSahoo/buem/blob/main/CHANGELOG.md>`_
for all version changes across BuEM, including the weather module.
