import pandas as pd
import numpy as np
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from buem.weather.from_csv import CsvWeatherData
# --- changed code: make weather CSV path configurable via BUEM_WEATHER_DIR env var ---
# Default to package-local data folder if env var is not set so behavior is backwards-compatible.
DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
WEATHER_DIR = os.environ.get("BUEM_WEATHER_DIR", DEFAULT_DATA_DIR)
WEATHER_CSV = os.path.join(WEATHER_DIR, "COSMO_Year__ix_390_650.csv")

if not os.path.exists(WEATHER_CSV):
    raise FileNotFoundError(
        f"Weather CSV not found at {WEATHER_CSV}. "
        "Provide the file there or set BUEM_WEATHER_DIR to a folder containing "
        "COSMO_Year__ix_390_650.csv (e.g. mount ./data/weather and set env var accordingly)."
    )

loader = CsvWeatherData(WEATHER_CSV) #Loenen weather data
df_weather = loader.extract_weather_columns()
df_weather.index = df_weather.index.tz_convert(None)

# Dummy time index and profiles for testing
# n_hours = 8760
main_index = df_weather.index
n_hours = len(main_index)
temp_profile = df_weather["T"]
ghi_profile = df_weather["GHI"]
dni_profile = df_weather["DNI"]
dhi_profile = df_weather["DHI"]

class AttributeCategory(Enum):
    """Category of attribute used by the API and builder."""
    WEATHER = "weather"
    TABULA = "tabula"
    BOOLEAN = "boolean"
    FIXED = "fixed"
    OTHER = "other"

class AttrType(Enum):
    """Type hints for attribute values to help parsing/validation."""
    DATAFRAME = "dataframe"   # full weather DataFrame
    SERIES = "series"         # time series (pd.Series)
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STR = "str"
    LIST = "list"             # generic list (e.g., roofs)
    OBJECT = "object"         # complex object (dict)
    UNKNOWN = "unknown"

@dataclass
class AttributeSpec:
    """Specification for a configuration attribute."""
    name: str
    category: AttributeCategory
    type: AttrType
    default: Any = None
    doc: Optional[str] = None

# Build attribute specs using the same defaults used in legacy cfg dict.
# This centralizes attribute metadata so cfg_building can infer how to parse/serialize.
ATTRIBUTE_SPECS: Dict[str, AttributeSpec] = {
    "weather": AttributeSpec(
        name="weather",
        category=AttributeCategory.WEATHER,
        type=AttrType.DATAFRAME,
        default=pd.DataFrame({
            "T": temp_profile,
            "GHI": ghi_profile,
            "DNI": dni_profile,
            "DHI": dhi_profile,
        }, index=main_index),
        doc="Weather DataFrame with columns T, GHI, DNI, DHI indexed by datetimes."
    ),
    "bldg_tabula_id": AttributeSpec("bldg_tabula_id", AttributeCategory.FIXED, AttrType.STR, "NL.N.MFH.01.Gen"),
    "costdatapath": AttributeSpec("costdatapath", AttributeCategory.FIXED, AttrType.STR,
                                 os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "default_2016.xlsx"))),
    "refurbishment": AttributeSpec("refurbishment", AttributeCategory.BOOLEAN, AttrType.BOOL, False, doc="Deprecated: refurbishment decisions not used in parameterized model"),
    "force_refurbishment": AttributeSpec("force_refurbishment", AttributeCategory.BOOLEAN, AttrType.BOOL, False, doc="Deprecated"),
    "occControl": AttributeSpec("occControl", AttributeCategory.BOOLEAN, AttrType.BOOL, False, doc="Deprecated"),
    "nightReduction": AttributeSpec("nightReduction", AttributeCategory.BOOLEAN, AttrType.BOOL, False, doc="Deprecated"),
    "capControl": AttributeSpec("capControl", AttributeCategory.BOOLEAN, AttrType.BOOL, False, doc="Deprecated"),
    "elecLoad": AttributeSpec("elecLoad", AttributeCategory.FIXED, AttrType.SERIES,
                              default=pd.Series([0.5] * n_hours, index=main_index),
                              doc="Electric internal load profile (pd.Series)"),
    "Q_ig": AttributeSpec("Q_ig", AttributeCategory.FIXED, AttrType.SERIES,
                         default=pd.Series([0.1] * n_hours, index=main_index),
                         doc="Internal gains profile (pd.Series)"),
    "occ_nothome": AttributeSpec("occ_nothome", AttributeCategory.FIXED, AttrType.SERIES,
                                 default=pd.Series(0.5 * (1 + np.sin(np.linspace(-np.pi/2, 3*np.pi/2, n_hours))), index=main_index),
                                 doc="Occupancy away profile"),
    "occ_sleeping": AttributeSpec("occ_sleeping", AttributeCategory.FIXED, AttrType.SERIES,
                                  default=pd.Series(0.5 * (1 - np.cos(np.linspace(0, 2*np.pi, n_hours))), index=main_index),
                                  doc="Sleeping occupancy profile"),
    "latitude": AttributeSpec("latitude", AttributeCategory.FIXED, AttrType.FLOAT, 52.0),
    "longitude": AttributeSpec("longitude", AttributeCategory.FIXED, AttrType.FLOAT, 5.0),
    # New structured component tree: component-level U (same for all elements) + element list
    "components": AttributeSpec(
        "components",
        AttributeCategory.OTHER,
        AttrType.OBJECT,
        default={
            "Walls": {
                "U": 1.61,
                "b_transmission": 1.0,
                "elements": [
                    {"id": "Wall_1", "area": 1226.9, "azimuth": 0.0, "tilt": 00.0},
                     {"id": "Wall_2", "area": 2000, "azimuth": 90.0, "tilt": 00.0},
                ],
            },
            "Roof": {
                "U": 1.54,
                "elements": [
                    {"id": "Roof_1", "area": 497.7, "azimuth": 135.0, "tilt": 30.0},
                ],
            },
            "Floor": {"U": 1.72, "elements": [{"id": "Floor_1", "area": 469.0, "azimuth": 180.0, "tilt": 90.0}]},
            "Windows": {
                "U": 5.2,
                "g_gl": 0.5,
                "elements": [
                    {"id": "Win_1", "area": 78.4, "surface": "Wall_1", "azimuth": 0.0, "tilt": 0.0},
                    {"id": "Win_2", "area": 347.2, "surface": "Wall_2", "azimuth": 90.0, "tilt": 0.0},
                ],
            },
            "Doors": {
                "U": 3.5,
                "elements": [
                    {"id": "Door_1", "area": 58.8, "surface": "Wall_1", "azimuth": 0.0, "tilt": 90.0}
                ]
            },
            "Ventilation": {"elements": [{"id": "Vent_1", "air_changes": 0.5}]},
        },
        doc="Structured component tree. Component-level 'U' applies to all elements; elements list carries per-surface geometry and area."
    ),
    "A_ref": AttributeSpec("A_ref", AttributeCategory.FIXED, AttrType.FLOAT, 2064),
    "h_room": AttributeSpec("h_room", AttributeCategory.FIXED, AttrType.FLOAT, 2.5),
    "n_air_infiltration": AttributeSpec("n_air_infiltration", AttributeCategory.FIXED, AttrType.FLOAT, 0.5),
    "n_air_use": AttributeSpec("n_air_use", AttributeCategory.FIXED, AttrType.FLOAT, 0.5),
    "design_T_min": AttributeSpec("design_T_min", AttributeCategory.FIXED, AttrType.FLOAT, -12.0),
    "onlyEnergyInvest": AttributeSpec("onlyEnergyInvest", AttributeCategory.BOOLEAN, AttrType.BOOL, False),
    "g_gl_n_Window": AttributeSpec("g_gl_n_Window", AttributeCategory.FIXED, AttrType.FLOAT, 0.5),
    "thermalClass": AttributeSpec("thermalClass", AttributeCategory.FIXED, AttrType.STR, "medium"),
    "comfortT_lb": AttributeSpec("comfortT_lb", AttributeCategory.FIXED, AttrType.FLOAT, 21.0),
    "comfortT_ub": AttributeSpec("comfortT_ub", AttributeCategory.FIXED, AttrType.FLOAT, 24.0),
    "roofs": AttributeSpec("roofs", AttributeCategory.FIXED, AttrType.LIST, [{'roofTilt': 45.0, 'roofOrientation': 135.0, 'roofArea': 30.0}], doc="List of roof dicts"),
    "A_Window_North": AttributeSpec("A_Window_North", AttributeCategory.FIXED, AttrType.FLOAT, 5.0),
    "A_Window_East": AttributeSpec("A_Window_East", AttributeCategory.FIXED, AttrType.FLOAT, 5.0),
    "A_Window_South": AttributeSpec("A_Window_South", AttributeCategory.FIXED, AttrType.FLOAT, 5.0),
    "A_Window_West": AttributeSpec("A_Window_West", AttributeCategory.FIXED, AttrType.FLOAT, 5.0),
    "A_Window_Horizontal": AttributeSpec("A_Window_Horizontal", AttributeCategory.FIXED, AttrType.FLOAT, 5.0),
    "F_sh_vert": AttributeSpec("F_sh_vert", AttributeCategory.FIXED, AttrType.FLOAT, 1.0),
    "F_sh_hor": AttributeSpec("F_sh_hor", AttributeCategory.FIXED, AttrType.FLOAT, 1.0),
    "F_f": AttributeSpec("F_f", AttributeCategory.FIXED, AttrType.FLOAT, 0.2),
    "F_w": AttributeSpec("F_w", AttributeCategory.FIXED, AttrType.FLOAT, 1.0),
    "ventControl": AttributeSpec("ventControl", AttributeCategory.BOOLEAN, AttrType.BOOL, False),
    "control": AttributeSpec("control", AttributeCategory.BOOLEAN, AttrType.BOOL, False),
}

# multi Family house (MFH), existing state refurbishment - NL.N.MFH.01.Gen
##cfg =  {
##        "weather": pd.DataFrame({
##            "T": temp_profile,  # external temp
##            "GHI": ghi_profile,  # global horizontal irradiance
##            "DNI": dni_profile,  # direct normal irradiance
##            "DHI": dhi_profile,  # diffuse horizontal irradiance
##        }, index=df_weather.index),
##        "bldg_tabula_id": "NL.N.MFH.01.Gen",
##        "costdatapath": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "default_2016.xlsx")),  
##        "refurbishment": True,
##        "force_refurbishment": False,
##        "occControl": False,
##        "nightReduction": False,
##        "capControl": False,
##        "elecLoad": pd.Series([0.5]*n_hours, index=main_index),
##        "Q_ig": pd.Series([0.1]*n_hours, index=main_index),
#         "Q_ig": pd.Series([0.3, 0.2], index=dummy_index),
##        "occ_nothome": pd.Series(0.5 * (1 + np.sin(np.linspace(-np.pi/2, 3*np.pi/2, n_hours))), index=main_index),  # 0 (home) at night, 1 (away) at noon
##        "occ_sleeping": pd.Series(0.5 * (1 - np.cos(np.linspace(0, 2*np.pi, n_hours))), index=main_index), # 1 at night, 0 during day
##        "latitude": 52.0,
##        "longitude": 5.0,
##        "A_Roof_1": 497.7,
#         "A_Roof_2": 128.1,
##        "U_Roof_1": 1.54,
#         "U_Roof_2": 1.54,
##        "b_Transmission_Roof_1": 1.0,
#         "b_Transmission_Roof_2": 1.0,
##        "A_Wall_1": 1226.9,
#         "A_Wall_2": 136.7,
#         "A_Wall_3": 136.7,
##        "U_Wall_1": 1.61,
#         "U_Wall_2": 1.61,
#         "U_Wall_3": 1.61,
##        "b_Transmission_Wall_1": 1.0,
#        "b_Transmission_Wall_2": 1.0,
#        "b_Transmission_Wall_3": 1.0,
##        "A_Floor_1": 469.0,
#         "A_Floor_2": 93.0,
##        "U_Floor_1": 1.72,
#         "U_Floor_2": 1.72,
##        "b_Transmission_Floor_1": 1.0,
#         "b_Transmission_Floor_2": 1.0,
##        "A_Window": 78.4,
##        "U_Window": 5.2,
##        "A_Door_1": 58.8,
##        "U_Door_1": 3.5,
##        "A_ref": 2064,
##        "h_room": 2.5,
##        "n_air_infiltration": 0.5,
##        "n_air_use": 0.5,
##        "design_T_min": -12.0,
##        "onlyEnergyInvest": False,
##        "g_gl_n_Window": 0.5, # Window g-value (solar energy transmittance)
##        "thermalClass": "medium",
##        "comfortT_lb": 21.0,  # lower bound of the comfortable temperature if active
##        "comfortT_ub": 24.0,  # upper bound of the comfortable temperature if active
##        "roofs":[{'roofTilt': 45.0,
##            'roofOrientation': 135.0,
##            'roofArea': 30.0
##        },],
        # Window areas and U-values for each orientation
##        "A_Window_North": 5.0,
##        "A_Window_East": 5.0,
##        "A_Window_South": 5.0,
##        "A_Window_West": 5.0,
##        "A_Window_Horizontal": 5.0,
        # Shading and orientation factors (set to 1.0 for no shading as default)
##        "F_sh_vert": 1.0,  # vertical shading factor for windows
##        "F_sh_hor": 1.0, # horizontal shading factor for windows
##        "F_f": 0.2, # fraction of the window area that is shaded
##        "F_w": 1.0,  # window orientation factor (1.0 for no orientation effect)
##        "ventControl": False,  # ventilation control flag
##        "control": False, # flaf for controling strategies, include smart thermostat, occupancy control, night reduction, temp control
##    }

# Legacy default cfg dict (keeps existing API for other modules)
cfg: Dict[str, Any] = {spec.name: spec.default for spec in ATTRIBUTE_SPECS.values()}
# Ensure the DataFrame is the actual DataFrame object (already set in spec defaults)
cfg["weather"] = ATTRIBUTE_SPECS["weather"].default