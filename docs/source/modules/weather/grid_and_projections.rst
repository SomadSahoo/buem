Grid and Projections
====================

COSMO-REA6 uses a **rotated-pole** coordinate system where the grid appears
regular (evenly spaced in the rotated longitude/latitude), but the pole is
shifted from the geographic North Pole to reduce metric distortion over
Europe.

Why No Reprojection Is Needed
-----------------------------

At first glance the rotated-pole grid might seem to require reprojection to
WGS84 before use.  In practice this is **not necessary** for BuEM, for two
reasons:

1. **Auxiliary WGS84 coordinates are already embedded in the GRIB files.**
   Each grid point carries pre-computed ``latitude`` and ``longitude``
   values in standard WGS84 (EPSG:4326).  When the NetCDF is opened with
   xarray, these appear as 2-D coordinate arrays alongside the native
   rotated indices.  Point extraction uses these WGS84 coordinates directly
   — no coordinate transformation is required at query time.

2. **Scalar fields are projection-invariant.**
   Temperature, irradiance, and wind speed are scalar quantities.  Their
   numeric values do not change under coordinate rotation — a grid cell
   holding 293.15 K holds the same value regardless of how the grid is
   oriented.  Only **vector** fields (wind U/V components) are
   direction-dependent, and BuEM uses only the scalar wind *speed*
   (``WS_10M = sqrt(U² + V²)``), which is rotationally invariant.

Wind Components (U_10M, V_10M)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The raw U and V wind components are defined relative to the **rotated-pole
grid north**, not geographic north.  This means the direction implied by
U and V is rotated relative to true north.  However:

- ``WS_10M = sqrt(U² + V²)`` is the same in any orthogonal coordinate system.
- BuEM's thermal model only uses wind **speed**, not direction.
- If wind direction were needed in the future, a rotation matrix using the
  pole coordinates (available in the GRIB metadata) would convert rotated
  U/V to geographic U/V.  This is a simple linear transform, not a grid
  resampling.

Grid Dimensions
---------------

.. list-table::
   :header-rows: 1

   * - Property
     - Value
   * - Grid size
     - 848 × 824 (longitude × latitude)
   * - Resolution
     - ~0.055° rotated (~6 km)
   * - Temporal resolution
     - Hourly
   * - Coverage
     - 1995–2019, Europe
   * - Pole (rotated)
     - (−170.0, 40.0) — as encoded in GRIB metadata
   * - CRS
     - Rotated latitude-longitude (non-standard EPSG)
   * - Auxiliary coords
     - WGS84 ``latitude``, ``longitude`` per grid point
