"""Mapping subpackage — converts raw data into canonical Building objects.

Modules
-------
lod2_mapper
    Core LOD2 + TABULA → Building mapper (orchestration).
wall_classifier
    Pre-computed shared (party) wall detection.
element_factory
    Factory functions for windows, doors, and ventilation elements.
tabula_helpers
    TABULA variant selection, window ratios, and safe numeric extraction.
"""

from buem.buildings.mapping.lod2_mapper import LOD2Mapper
from buem.buildings.mapping.wall_classifier import SharedWallDetector

__all__ = ["LOD2Mapper", "SharedWallDetector"]
