import pandas as pd
import numpy as np
import os

# Dummy time index and profiles for testing
n_hours = 8760
dummy_index = pd.date_range("2025-01-01", periods=n_hours, freq="h")
# Sinusoidal profile: mean 20°C, amplitude 5°C, period 24h (1 day), min 15°C, max 25°C
temp_profile = 18 + 5 * np.sin(2 * np.pi * (np.arange(n_hours) % 24) / 24)
ghi_profile = np.full(n_hours, 200)
dni_profile = np.full(n_hours, 100)
dhi_profile = np.full(n_hours, 50)

cfg =  {
        "weather": pd.DataFrame({
            "T": temp_profile,  # external temp
            "GHI": ghi_profile,  # global horizontal irradiance
            "DNI": dni_profile,  # direct normal irradiance
            "DHI": dhi_profile,  # diffuse horizontal irradiance
        }, index=dummy_index),
        "costdatapath": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "default_2016.xlsx")),  
        "refurbishment": True,
        "force_refurbishment": False,
        "occControl": False,
        "nightReduction": False,
        "capControl": False,
        "elecLoad": pd.Series([0.5]*n_hours, index=dummy_index),
        "Q_ig": pd.Series([0.1]*n_hours, index=dummy_index),
#         "Q_ig": pd.Series([0.3, 0.2], index=dummy_index),
        "occ_nothome": pd.Series(0.5 * (1 + np.sin(np.linspace(-np.pi/2, 3*np.pi/2, n_hours))), index=dummy_index),  # 0 (home) at night, 1 (away) at noon
        "occ_sleeping": pd.Series(0.5 * (1 - np.cos(np.linspace(0, 2*np.pi, n_hours))), index=dummy_index), # 1 at night, 0 during day
        "latitude": 52.0,
        "longitude": 5.0,
        "A_Roof_1": 92.3,
        "A_Roof_2": 50.0,
        "U_Roof_1": 0.15,
        "U_Roof_2": 0.2,
        "b_Transmission_Roof_1": 1.0,
        "b_Transmission_Roof_2": 1.0,
        "A_Wall_1": 105.7,
        "A_Wall_2": 162.0,
        "A_Wall_3": 100.0,
        "U_Wall_1": 0.27,
        "U_Wall_2": 0.27,
        "U_Wall_3": 0.3,
        "b_Transmission_Wall_1": 1.0,
        "b_Transmission_Wall_2": 1.0,
        "b_Transmission_Wall_3": 1.0,
        "A_Floor_1": 21.5,
        "A_Floor_2": 70.8,
        "U_Floor_1": 0.29,
        "U_Floor_2": 0.19,
        "b_Transmission_Floor_1": 1.0,
        "b_Transmission_Floor_2": 1.0,
        "A_Window": 19.1,
        "U_Window": 1.4,
        "A_Door_1": 1.8,
        "U_Door_1": 1.7,
        "A_ref": 159.0,
        "h_room": 2.5,
        "n_air_infiltration": 0.5,
        "n_air_use": 0.5,
        "design_T_min": -12.0,
        "onlyEnergyInvest": False,
        "g_gl_n_Window": 0.5, # Window g-value (solar energy transmittance)
        "thermalClass": "medium",
        "comfortT_lb": 21.0,  # lower bound of the comfortable temperature if active
        "comfortT_ub": 24.0,  # upper bound of the comfortable temperature if active
        "roofs":[{'roofTilt': 45.0,
            'roofOrientation': 135.0,
            'roofArea': 30.0
        },],
        # Window areas and U-values for each orientation
        "A_Window_North": 5.0,
        "A_Window_East": 5.0,
        "A_Window_South": 5.0,
        "A_Window_West": 5.0,
        "A_Window_Horizontal": 5.0,
        # Shading and orientation factors (set to 1.0 for no shading as default)
        "F_sh_vert": 1.0,  # vertical shading factor for windows
        "F_sh_hor": 1.0, # horizontal shading factor for windows
        "F_f": 0.2, # fraction of the window area that is shaded
        "F_w": 1.0,  # window orientation factor (1.0 for no orientation effect)
        "ventControl": False,  # ventilation control flag
        "control": False, # flaf for controling strategies, include smart thermostat, occupancy control, night reduction, temp control
    }