import pvlib
import cvxpy as cp
from scipy.sparse.linalg import spsolve
from scipy.sparse import lil_matrix, vstack
import pandas as pd
import numpy as np

class ModelBUEM(object):
    """
    Parameterized ISO-13790 5R1C building model.
    
    Key aspects:
    - Use of the following input modules: Occupancy, weather, and 3D-building + Tabula
    - Output: Heating and cooling load at a building level with hourly resolution
    - Consideration of pvlib python package for calculating solar gains
    - Following building components' consideration: walls, roofs, windows, doors, and floor
    - solve with scipy (equality) or cvxpy (inequalities)
    """
    CONST = {
        # Constants for calculation of A_m, dependent of building class
        # (DIN EN ISO 13790, section 12.3.1.2, page 81, table 12)
        "f_Am": [2.5, 2.5, 2.5, 3.0, 3.5],
        # specific heat transfer coefficient between internal air and surface [kW/m^2/K]
        # (DIN EN ISO 13790, section 7.2.2.2, page 35)
        "h_is": 3.45 / 1000,
        # non-dimensional relation between the area of all indoor surfaces
        # and the effective floor area A["f"]
        # (DIN EN ISO 13790, section 7.2.2.2, page 36)
        "lambda_at": 4.5,
        # specific heat transfer coefficient thermal capacity [kW/m^2/K]
        # (DIN EN ISO 13790, section 12.2.2, page 79)
        "h_ms": 9.1 / 1000,
        # ISO 6946 Table 1, Heat transfer resistances for opaque components
        "R_se": 0.04 * 1000,  # external heat transfer coefficient m²K/kW
        # ASHRAE 140 : 2011, Table 5.3, page 18 (infrared emittance) (unused --> look at h_r)
        "epsilon": 0.9,
        # external specific radiative heat transfer [kW/m^2/K] (ISO 13790, Schuetz et al. 2017, 2.3.4)
        "h_r": 0.9 * 5.0 / 1000.0,
        # ASHRAE 140 : 2011, Table 5.3, page 18 (absorption opaque comps)
        "alpha": 0.6,
        # average difference external air temperature and sky temperature
        "delta_T_sky": 11.0,  # K
        # density air
        "rho_air": 1.2,  # kg/m^3
        # heat capacity air
        "C_air": 1.006,  # kJ/kg/K
        }

    def __init__(self, cfg: dict, maxLoad: float = None):
        """
        Initialize model instance and declare cross-method attributes.

        Parameters
        ----------
        cfg: dict
            Configuration / attributes 
            (expected keys: 'weather', 'building_components', etc.)
        maxLoad: float, optional 
            (default: DesignHeatLoad)
            Maximal load of the heating system.

        """
        self.cfg = cfg 
        self.maxLoad = maxLoad

        # time series index
        self.times = self.cfg["weather"].index

        # irradiance per surface element (DataFrame indexed by time, cols = element ids)
        self._irrad_surf = pd.DataFrame(index=self.times)

        # component tree and per-component parameters
        # component_elements: dict[component] -> list[element dicts {id, area, azimuth, tilt, ...}]
        self.component_elements = {}
        # component-level U (same for all elements)
        self.bU = {}
        # component conductance [kW/K] aggregated over elements (Original state)
        self.bH = {}
        # window element list (shortcut)
        self.windows = []

        # 5R1C thermal parameters (initialized later in _init5R1C)
        self.bA_f = None
        self.bA_m = None
        self.bH_ms = None
        self.bC_m = None
        self.bA_tot = None
        self.bH_is = None
        self.bT_comf_lb = None
        self.bT_comf_ub = None

        # profiles (internal gains, occupancy, solar gains created in _init5R1C)
        self.profiles = {}
        self.profilesEval = {}

        # results containers
        self.static_results = {}
        self.detailedResults = pd.DataFrame(index=self.times)

        # solver/runtime bookkeeping
        self.components = ["Walls", "Roof", "Floor", "Windows", "Ventilation"]
        self.hasTypPeriods = False
        self.ventControl = bool(self.cfg.get("ventControl", False))

    # -------- utilities --------
    def _cfg_float(self, key, default=0.0):
        """Consistent float read helper for cfg values (handles Series fallback)."""
        v = self.cfg.get(key, default)
        try:
            return float(v)
        except Exception:
            # allow Series/array -> take mean as fallback if provided
            try:
                return float(np.mean(v))
            except Exception:
                return float(default)
            
    # -------- parameter parsing --------
    def _initPara(self):
        """
        Ensure required dictionaries/lists are present before building parameters.
        """
        if not hasattr(self, "profiles"):
            self.profiles = {}
        if not hasattr(self, "profilesEval"):
            self.profilesEval = {}

    def _initEnvelop(self):
        """
        Parse cfg['components'] or fallback legacy keys.
        - Populate self.component_elements: component -> list of {id, area, azimuth, tilt, ...}
        - Populate component-level U in self.bU
        - Compute aggregated conductance self.bH[component]['Original'] = U * sum(area) * b_trans / 1000 (kW/K)
        - Compute ventilation conductance and include under 'Ventilation'
        """
        comps = self.cfg.get("components")
        if isinstance(comps, dict) and comps:
            # structured component tree provided
            for comp_name, comp_data in comps.items():
                elems = comp_data.get("elements", [])
                parsed = []
                for e in elems:
                    parsed.append(
                        {
                            "id": e.get("id"),
                            "area": float(e.get("area", 0.0)),
                            "azimuth": float(e["azimuth"]) if e.get("azimuth") is not None else None,
                            "tilt": float(e["tilt"]) if e.get("tilt") is not None else None,
                            # preserve other properties (e.g., surface mapping for windows)
                            **{k: v for k, v in e.items() if k not in ("id", "area", "azimuth", "tilt")}
                        }
                    )
                self.component_elements[comp_name] = parsed

                # component U
                self.bU[comp_name] = float(comp_data.get("U", self.cfg.get(f"U_{comp_name}", 0.0)))
                
                # transmission factor (optional)
                b_trans = float(comp_data.get("b_transmission", comp_data.get("b_transmission", 1.0)))
                total_area = sum(e["area"] for e in parsed)
                self.bH[comp_name] = {"Original": self.bU[comp_name] * total_area * b_trans / 1000.0}
        else:
            # legacy flat config: build minimal component_elements for compatibility
            # Walls, Roof, Floor based on A_* and U_* keys
            for comp in ["Walls", "Roof", "Floor", "Windows", "Ventilation"]:
                elems = []
                # search for keys A_<Comp>_n or A_<Comp> keys
                # Try A_<Comp>_1, A_<Comp>_2 pattern
                i = 1
                found = False
                while True:
                    key = f"A_{comp}_{i}"
                    if key in self.cfg:
                        found = True
                        elems.append({"id": f"{comp}_{i}", "area": float(self.cfg.get(key, 100.0))})
                        i += 1
                    else:
                        break
                if not found and f"A_{comp}" in self.cfg:
                    elems.append({"id": f"{comp}_1", "area": float(self.cfg.get(key, 100.0))})
                self.component_elements[comp] = elems
                # component-level U fallback
                self.bU[comp] = float(self.cfg.get(f"U_{comp}"))
                total_area = sum(e["area"] for e in elems)
                b_trans = float(self.cfg.get(f"b_Transmission_{comp}_1", 1.0))
                self.bH[comp] = {"Original": self.bU[comp] * total_area * b_trans / 1000.0}

        # build helper lists and windows element list
        self.walls = [e["id"] for e in self.component_elements.get("Walls", [])]
        self.roofs = [e["id"] for e in self.component_elements.get("Roof", [])]
        self.floors = [e["id"] for e in self.component_elements.get("Floor", [])]
        self.windows = self.component_elements.get("Windows", [])


        # ventilation aggregated conductance (kW/K)
        A_ref = self._cfg_float("A_ref", 1.0)
        h_room = self._cfg_float("h_room", 2.5)
        rho_air = self.CONST["rho_air"]
        C_air = self.CONST["C_air"]
        n_air_inf = self._cfg_float("n_air_infiltration", 0.0)
        n_air_use = self._cfg_float("n_air_use", 0.0)
        H_ve = A_ref * h_room * rho_air * C_air * (n_air_inf + n_air_use) / 3600.0
        self.bH.setdefault("Ventilation", {})["Original"] = H_ve

    # -------- 5R1C & solar --------        
    def _init5R1C(self):
        """
        Compute 5R1C thermal parameters and build solar gain profiles.
        - Thermal capacity: uses cfg['thermalClass'] to derive c_m and A_m per ISO/DIN table.
        - Compute POA irradiance per element from self.component_elements (via pvlib).
        - Build and store time series in self.profiles:
            bQ_sol_Windows, bQ_sol_Walls, bQ_sol_Roof, bQ_sol_Opaque
        """
        # store constants reference
        self.bConst = self.CONST

        # thermal capacity classes (DIN/ISO values)
        bClass_f_lb = {"very light": 0.0, "light": 95.0, "medium": 137.5, "heavy": 212.5, "very heavy": 313.5}
        bClass_f_ub = {"very light": 95.0, "light": 137.5, "medium": 212.5, "heavy": 313.5, "very heavy": 627.0}
        bClass_f_a = {"very light": 2.5, "light": 2.5, "medium": 2.5, "heavy": 3.0, "very heavy": 3.5}


        # Heated floor area and basic derived thermal params
        self.bA_f = float(self.cfg.get("A_ref", 100.0))
        thermalClass = self.cfg.get("thermalClass", "medium")
        self.bA_m = self.bA_f * bClass_f_a.get(thermalClass, 2.5)
        self.bH_ms = self.bA_m * self.bConst["h_ms"]

        # specific heat c_m (kJ/m2/K) -> internal heat capacity [kWh/K]
        if "c_m" not in self.cfg:
            self.cfg["c_m"] = (bClass_f_lb.get(thermalClass, 137.5) + bClass_f_ub.get(thermalClass, 137.5)) / 2.0
        self.bC_m = self.bA_f * float(self.cfg["c_m"]) / 3600.0

        # internal surface area and surface-air conductance
        self.bA_tot = self.bA_f * self.bConst["lambda_at"]
        self.bH_is = self.bA_tot * self.bConst["h_is"]

        # comfort bounds
        self.bT_comf_lb = float(self.cfg.get("comfortT_lb", 21.0))
        self.bT_comf_ub = float(self.cfg.get("comfortT_ub", 24.0))

        # Build surface azimuth/tilt dicts from component elements (element ids as keys)
        surf_az = {}
        surf_tilt = {}
        for comp, elems in self.component_elements.items():
            for e in elems:
                eid = e.get("id")
                if eid is None:
                    continue
                if e.get("azimuth") is not None:
                    surf_az[eid] = float(e["azimuth"])
                if e.get("tilt") is not None:
                    surf_tilt[eid] = float(e["tilt"])

        # Fallback defaults (cardinal + horizontal) surfaces if not provided
        defaults_az = {"North": 0.0, "East": 90.0, "South": 180.0, "West": 270.0, "Horizontal": 180.0}
        defaults_tilt = {"North": 90.0, "East": 90.0, "South": 90.0, "West": 90.0, "Horizontal": 0.0}
        for k, v in defaults_az.items():
            surf_az.setdefault(k, v)
        for k, v in defaults_tilt.items():
            surf_tilt.setdefault(k, v)

        # compute POA irradiance per element (populates self._irrad_surf in kW/m2)
        self._calcRadiation(surf_az, surf_tilt)
        print("POA for all elements: \n", self._irrad_surf.columns, self._irrad_surf.head(20)) # test

        # Build solar gain profiles (kW time series arrays)
        # WINDOWS: each window element may reference a surface (surface field) or be its own surface
        self.g_gl = float(self.cfg.get("g_gl_n_Window", 0.5))
        self.F_sh_vert = float(self.cfg.get("F_sh_vert", 1.0))
        self.F_sh_hor = float(self.cfg.get("F_sh_hor", 1.0))
        self.F_w = float(self.cfg.get("F_w", 1.0))
        self.F_f = float(self.cfg.get("F_f", 0.6))
        # alpha (absorptance) used for opaque solar gains
        alpha = float(self.bConst.get("alpha", 0.6))

        # windows: POA (kW/m2) * area (m2) * g * fractions -> kW
        win_list = []
        for w in self.windows:
            wid = w.get("id")
            area = float(w.get("area", 5.0))
            # window may reference a parent surface (e.g., "surface": "Wall_1")
            surf_ref = w.get("surface", wid)
            if surf_ref in self._irrad_surf.columns:
                poa = self._irrad_surf[surf_ref].values  # kW/m2
            elif wid in self._irrad_surf.columns:
                poa = self._irrad_surf[wid].values
            else:
                # fallback to GHI (kW/m2)
                poa = self.cfg["weather"]["GHI"].values / 1000.0
            
            gwin = float(w.get("g_gl", self.g_gl))
            # Q [kW] = area * g_gl * irr * fraction factors - small thermal sky term handled below
            qwin = poa * area * gwin * (1.0 - self.F_f) * self.F_w
            win_list.append(qwin)
        
        self.profiles["bQ_sol_Windows"] = np.sum(np.vstack(win_list), axis=0) if win_list else np.zeros(len(self.times))

        # thermal sky loss for windows (use H_windows if available, else total area-based fallback)
        H_windows = self.bH.get("Windows", {}).get("Original", 0.0)
        if H_windows > 0:
            thermal_rad_win = H_windows * self.bConst["h_r"] * self.bConst["R_se"] * self.bConst["delta_T_sky"]
        else:
            total_window_area = sum(float(w.get("area", 0.0)) for w in self.windows)      
            U_win = self.bU.get("Windows", float(self.cfg.get("U_Window", 0.0)))
            # U_win likely in W/m2/K -> convert to kW/m2/K for consistent units when needed
            thermal_rad_win = (
                total_window_area
                * self.bConst["h_r"]
                * (U_win/1000)
                * self.bConst["R_se"]
                * self.bConst["delta_T_sky"]
            )
        # ensure thermal_rad_win is kW and subtract
        self.profiles["bQ_sol_Windows"] = self.profiles["bQ_sol_Windows"] - float(thermal_rad_win)

        # OPAQUE: Walls and Roof (use element POA * area * alpha * shading)
        wall_q = []
        for e in self.component_elements.get("Walls", []):
            eid = e.get("id")
            area = float(e.get("area", 0.0))
            poa = self._irrad_surf[eid].values if eid in self._irrad_surf.columns else (self.cfg["weather"]["GHI"].values / 1000.0)
            wall_q.append(area * alpha * self.F_sh_vert * poa)
        self.profiles["bQ_sol_Walls"] = np.sum(np.vstack(wall_q), axis=0) if wall_q else np.zeros(len(self.times))

        roof_q = []
        for e in self.component_elements.get("Roof", []):
            eid = e.get("id")
            area = float(e.get("area", 0.0))
            poa = self._irrad_surf[eid].values if eid in self._irrad_surf.columns else (self.cfg["weather"]["GHI"].values / 1000.0)
            roof_q.append(area * alpha * self.F_sh_hor * poa)
        self.profiles["bQ_sol_Roof"] = np.sum(np.vstack(roof_q), axis=0) if roof_q else np.zeros(len(self.times))

        self.profiles["bQ_sol_Floor"] = np.zeros(len(self.times))
        self.profiles["bQ_sol_Opaque"] = self.profiles["bQ_sol_Walls"] + self.profiles["bQ_sol_Roof"] + self.profiles["bQ_sol_Floor"]

        # provide debug sums (kWh per timestep is kW * 1h)
        print("DEBUG solar sums (kW·h totals): windows:", self.profiles["bQ_sol_Windows"].sum(),
              "opaque:", self.profiles["bQ_sol_Opaque"].sum())

    def _calcRadiation(self, surf_az:dict, surf_tilt:dict):
        """
        Compute plane-of-array (POA) irradiance for each surface element via pvlib.
        Results assigned to self._irrad_surf[col = element id] in kW/m2.
        This implementation iterates all configured elements so _irrad_surf is
        always populated for use by the solar-gain routines.
        """
        # compute solar position and helpers
        solpos = pvlib.solarposition.get_solarposition(
            self.cfg["weather"].index,
            self.cfg.get("latitude", 52.0),
            self.cfg.get("longitude", 5.0),
        )
        AM = pvlib.atmosphere.get_relative_airmass(solpos["apparent_zenith"])
        dni_extra = pvlib.irradiance.get_extra_radiation(self.cfg["weather"].index.dayofyear)

        # ensure weather contains DNI/DHI/GHI (pvlib needs them)
        if not all(k in self.cfg["weather"] for k in ("DNI", "DHI", "GHI")):
            raise RuntimeError("Weather must include 'DNI','DHI' and 'GHI' series for POA calculations.")

        df = pd.DataFrame(index=self.times)
        for comp, elems in self.component_elements.items():
            for e in elems:
                eid = e.get("id")
                if eid is None:
                    continue
                # pvlib tilt convention: 0 = horizontal up, 90 = vertical
                if e.get("tilt") is not None:
                    tilt = float(e.get("tilt"))
                elif eid in surf_tilt:
                    tilt = float(surf_tilt[eid])
                else:
                    # pvlib tilt: 0° horizontal up (roof/floor), 90° vertical (walls/windows)
                    tilt = 0.0 if comp in ("Roof", "Floor") else 90.0
                
                # Resolve azimuth precedence: element -> surf_az dict -> default (180° south)
                if e.get("azimuth") is not None:
                    az = float(e.get("azimuth"))
                elif eid in surf_az:
                    az = float(surf_az[eid])
                else:
                    az = 180.0

                # calculate total irradiance depending on surface tilt and azimuth
                total = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=float(tilt),
                    surface_azimuth=float(az),
                    solar_zenith=solpos["apparent_zenith"],
                    solar_azimuth=solpos["azimuth"],
                    dni=self.cfg["weather"]["DNI"],
                    ghi=self.cfg["weather"]["GHI"],
                    dhi=self.cfg["weather"]["DHI"],
                    dni_extra=dni_extra,
                    airmass=AM,
                    model="perez",
                )
                # store POA in kW/m2
                df[eid] = total["poa_global"].fillna(0) / 1000.0
        self._irrad_surf = df
        return df

    # -------- design load --------
    def calcDesignHeatLoad(self) -> float:
        """
        Approximate design heat load [kW]. Uses aggregated conductances (self.bH).
        """
        # ensure envelope parsed
        if not self.bH:
            self._initEnvelop()
        H_tot = sum(self.bH.get(c, {}).get("Original", 0.0) for c in self.bH)
        deltaT = 22.917 - float(self.cfg.get("design_T_min", 0.0))
        return H_tot * deltaT

    def _addPara(self):
        """
        Prepare additional parameters and subsets required for optimization/simulation.
        Calls _initEnvelop and _init5R1C to ensure derived profiles and bH are available.
        """

        self._initPara()
        self._initEnvelop()
        self._init5R1C()

        # sizing
        if self.maxLoad is None:
            self.BMaxLoad = self.calcDesignHeatLoad()
            self.maxLoad = self.bMaxLoad
        else:
            self.bMaxLoad = self.maxLoad



        # Prepare basic profiles references for other code paths
        self.profiles["bQ_ig"] = self.cfg.get("Q_ig", pd.Series(0.0, index=self.times))
        self.profiles["occ_nothome"] = self.cfg.get("occ_nothome", pd.Series(0.0, index=self.times))
        self.profiles["occ_sleeping"] = self.cfg.get("occ_sleeping", pd.Series(0.0, index=self.times))
 
        # compute big-M bounds for aggregated heat flows (for compatibility)
        self.bM_q = {}
        self.bm_q = {}
        for comp, d in self.bH.items():
            self.bM_q[comp] = {}
            self.bm_q[comp] = {}
            for state, H_val in d.items():
                # conservative bounds based on comfort temps and weather extremes
                high = (self.bT_comf_ub - (self.cfg["weather"]["T"].min() - 10)) * H_val
                low = (self.bT_comf_lb - (self.cfg["weather"]["T"].max() + 10)) * H_val
                self.bM_q[comp][state] = high
                self.bm_q[comp][state] = low

    def _addVariables(self):   
        """
        Declare placeholders for variable containers used by other methods.
        This method does not create solver variables; it sets up dicts/lists only.
        """

        self.bQ_comp = {}  # Heat flow through components 

        # define/declare auxiliary variable for modeling heat flow on thermal mass surface
        self.bP_X = {}

        # temperatures variables
        self.bT_m = {}  # thermal mass node temperature
        self.bT_air = {}  # air node temperature
        self.bT_s = {}  # surface node temperature

        # heat flow variables
        self.bQ_ia = {}  # heat flow to air node [kW]
        self.bQ_m = {}  # heat flow to thermal mass node [kW]
        self.bQ_st = {}  # heat flow to surface node [kW]

        # ventilation heat flow
        self.bQ_ve = {}  # heat flow through ventilation [kW]         
                                    
    def scaleHeatLoad(self, scale=1):
        """
        Scale original U-values and infiltration rates by `scale` to obtain relative heat loads.
        Saves original values on first call.
        """
        if not hasattr(self, "_orig_U_Values"):
            self._orig_U_Values = {}
            # capture legacy U_* keys
            for key in self.cfg:
                if str(key).startswith("U_"):
                    self._orig_U_Values[key] = self.cfg[key]
            self._orig_U_Values["n_air_infiltration"] = self.cfg.get("n_air_infiltration", 0.0)
            self._orig_U_Values["n_air_use"] = self.cfg.get("n_air_use", 0.0)

        for key, val in self._orig_U_Values.items():
            self.cfg[key] = val * scale

    # -------- constraints & solver --------
    def _addConstraints(self, use_inequality_constraints: bool = False):
        """
        Assemble linear equality and optional inequality constraints for the time-stepped 5R1C model.
        Variable order: [T_air_0, ..., T_air_n-1, T_m_0, ..., T_m_n-1, T_sur_0, ..., 
        T_sur_n-1, Q_heat_0, ..., Q_heat_n-1, Q_cool_0, ..., Q_cool_n-1]
        
        Parameters
        ----------
        use_inequality_constraints : bool
            If true, returns (A_eq, b_eq, A_ineq, b_ineq) as sparse matrices, which adds temperature 
            bounds, comfort temperature ranges, and the rate of change constraints. 
            Otherwise, returns (A_eq, b_eq, None, None) for equality-only solve
        """
        
        n = len(self.timeIndex)
        print(f"n: {n}")
        self.n_vars = 4 * n   # [T_air, T_m, T_sur, Q_HC] for each timestep
        print(f"self.n_vars: {self.n_vars}")

        # Helper to get variable indices
        def idx_T_air(i): return i
        def idx_T_m(i): return n + i
        def idx_T_sur(i): return 2 * n + i
        def idx_Q_HC(i): return 3 * n + i
        # def idx_Q_cool(i): return 4 * n + i

        # Prepare lists for equality and inequality constraints
        eq_rows, eq_vals = [], []
        ineq_rows, ineq_vals = [], []

        # aggregated conductances from self.bH (Original state)
        H_walls = self.bH.get("Walls", {}).get("Original", 0.0)
        H_roofs = self.bH.get("Roof", {}).get("Original", 0.0)
        H_floors = self.bH.get("Floor", {}).get("Original", 0.0)
        H_windows = self.bH.get("Windows", {}).get("Original", 0.0)
        H_doors = self.bH.get("Doors", {}).get("Original", 0.0)
        H_ve = self.bH.get("Ventilation", {}).get("Original", 0.0)

        # Total transmission
        H_tot = H_ve + H_walls + H_roofs + H_floors + H_windows + H_doors

        #mass-surface and surface-air conductances 
        C_m = self.bC_m
        H_ms = self.bH_ms
        H_is = self.bH_is if hasattr(self, "bH_is") else 3.6 /1000  # fallback

        step = self.stepSize
        sleeping_factor = 0.5

        # use precomputed solar profiles from _init5R1C
        Q_win_profile = self.profiles.get("bQ_sol_Windows", np.zeros(len(self.times)))
        Q_opaque_profile = self.profiles.get("bQ_sol_Opaque", np.zeros(len(self.times)))

        # Main loop for Building equations
        for i, (t1, t2) in enumerate(self.timeIndex):
            Q_sol_win = float(Q_win_profile[i])
            Q_sol_opaque = float(Q_opaque_profile[i])

            # internal gains and occupancy
            if isinstance(self.profiles.get("occ_nothome"), dict):
                occ = 1 - self.profiles["occ_nothome"][(t1, t2)]
            else:
                occ = 1 - float(self.profiles.get("occ_nothome", pd.Series(0, index=self.times)).iloc[i])
            sleeping = float(self.profiles.get("occ_sleeping", pd.Series(0, index=self.times)).iloc[i])
            Q_ig = float(self.profiles.get("bQ_ig", pd.Series(0, index=self.times)).iloc[i])
            elecLoad = float(self.cfg.get("elecLoad", pd.Series(0, index=self.times)).iloc[i])
            Q_ia = (Q_ig + elecLoad) * (occ * (1 - sleeping) + sleeping_factor * sleeping)

            T_e = self.profiles["T_e"][(t1, t2)] if isinstance(self.profiles.get("T_e"), dict) else float(self.cfg["weather"]["T"].iloc[i])
            
            # split solar gains: 50% to air, 50% to surface (ISO simplification)
            Q_air = Q_ia + 0.5 * Q_sol_win
            Q_surface = Q_sol_opaque + 0.5 * Q_sol_win

            # 1) Air node balance: (H_is + H_ve) * T_air - H_is * T_sur - Q_HC = Q_air + H_ve * T_e
            row = lil_matrix((1, self.n_vars))
            row[0, idx_T_air(i)] = H_is + H_ve
            row[0, idx_T_sur(i)] = -H_is
            row[0, idx_Q_HC(i)] = -1
            # row[0, idx_Q_cool(i)] = -1
            eq_rows.append(row)
            eq_vals.append(Q_air + H_ve * T_e)

            # 2) Surface node balance: (H_is + H_ms + H_windows) * T_sur - H_is * T_air - H_ms * T_m = Q_surface + H_windows * T_e
            row = lil_matrix((1, self.n_vars))
            row[0, idx_T_sur(i)] = H_is + H_ms + H_windows
            row[0, idx_T_air(i)] = -H_is
            row[0, idx_T_m(i)] = -H_ms
            eq_rows.append(row)
            eq_vals.append(Q_surface + H_windows*T_e)  

            # 3) Mass node dynamics (implicit-forward Euler):
            # C_m * (T_m_next - T_m)/step = H_ms*(T_sur - T_m) - H_tot*(T_m - T_e)
            if i == 0:
                row = lil_matrix((1, self.n_vars))
                # Initial condition for T_m at first time step (set to comfort range)
                row[0, idx_T_m(i)] = 1
                eq_rows.append(row)
                eq_vals.append(self.T_set)

            elif i < n - 1:
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_m(i)] = -C_m / step - H_ms - H_tot
                row[0, idx_T_m(i+1)] = C_m / step
                row[0, idx_T_sur(i)] = H_ms
                eq_rows.append(row)
                eq_vals.append(-H_tot * T_e)             
            
            else:
                # Periodic boundary: T_m at last = T_m at first
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_m(i)] = -1
                row[0, idx_T_m(0)] = 1
                eq_rows.append(row)
                eq_vals.append(0)

            # 4) HVAC equality for fixed-comfort solve: Q_HC = H_tot * T_set - H_tot * T_air
            if not use_inequality_constraints:
                row = lil_matrix((1, self.n_vars))
                row[0, idx_Q_HC(i)] = 1
                row[0, idx_T_air(i)] = H_tot
                eq_rows.append(row)
                eq_vals.append(H_tot * self.T_set)
            
            else:
                 # add simple bounds on T_air, T_sur, T_m
                T_air_min, T_air_max = 15.0, 30.0
                T_sur_min, T_sur_max = 10.0, 35.0
                T_m_min, T_m_max = 15.0, 30.0
                max_delta_T = 2.0  # Maximum temperature change per hour        

                # T_air <= T_air_max
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_air(i)] = 1
                ineq_rows.append(row)
                ineq_vals.append(T_air_max)

                # -T_air <= -min  => T_air >= T_air_min
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_air(i)] = -1
                ineq_rows.append(row)
                ineq_vals.append(-T_air_min)

                # surface bounds
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_sur(i)] = 1
                ineq_rows.append(row)
                ineq_vals.append(T_sur_max)

                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_sur(i)] = -1
                ineq_rows.append(row)
                ineq_vals.append(-T_sur_min)

                # mass bounds
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_m(i)] = 1
                ineq_rows.append(row)
                ineq_vals.append(T_m_max)
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_m(i)] = -1
                ineq_rows.append(row)
                ineq_vals.append(-T_m_min)

                # --- INEQUALITY: Rate of change constraints ---
                # if i > 0:
                #     for temp_idx in [idx_T_air, idx_T_sur, idx_T_m]:
                        # Forward difference
                #         row = lil_matrix((1, self.n_vars))
                #         row[0, temp_idx(i)] = 1
                #         row[0, temp_idx(i-1)] = -1
                #         ineq_rows.append(row)
                #         ineq_vals.append(max_delta_T * step)  

                        # Reverse difference (negative direction)
                #         row = lil_matrix((1, self.n_vars))
                #         row[0, temp_idx(i)] = -1
                #         row[0, temp_idx(i-1)] = 1
                #         ineq_rows.append(row)
                #         ineq_vals.append(max_delta_T * step)                                 


        A_eq = vstack(eq_rows) if eq_rows else None
        b_eq = np.array(eq_vals) if eq_vals else None
        A_ineq = vstack(ineq_rows) if ineq_rows else None
        b_ineq = np.array(ineq_vals) if ineq_vals else None

        return A_eq, b_eq, A_ineq, b_ineq
    
    def sim_model(self, use_inequality_constraints:False, comfort_mode="heating"):
        """
        ISO-compliant parameterization run for the building model with sparse matrix solve 
        (with surface node, all components, and detailed solar gains).
        
        Parameter
        ---------
        Boolean: use_hard_constraints: default=False
        If use_hard_constraints is True, use scipy.optimize.linprog to handle inequalities
        """

        # prepare parameters and profiles
        self._initPara()
        self._initEnvelop()
        self._init5R1C()

        # time indexing used in constraints (tuples for compatibility)
        self.timeIndex = [(1, t) for t in range(len(self.times))]
        self.fullTimeIndex = self.timeIndex
        timediff = self.times[1] - self.times[0]
        self.stepSize = timediff.total_seconds() / 3600
        
        # ensure profiles present
        self.profiles.setdefault("bQ_ig", self.cfg.get("Q_ig", pd.Series(0.0, index=self.times)))
        self.profiles.setdefault("occ_nothome", self.cfg.get("occ_nothome", pd.Series(0.0, index=self.times)))
        self.profiles.setdefault("occ_sleeping", self.cfg.get("occ_sleeping", pd.Series(0.0, index=self.times)))
        
        #set up separate runs for heating and cooling
        if comfort_mode == 'heating':
            self.T_set = self.bT_comf_lb
        elif comfort_mode == 'cooling':
            self.T_set = self.bT_comf_ub  
        else:
            raise ValueError("comfort_mode must be 'heating' or 'cooling'")  

        # Ensure external temperature profile access in expected format
        if "T_e" not in self.profiles:
            self.profiles["T_e"] = self.cfg["weather"]["T"]
        if isinstance(self.profiles["T_e"], (pd.Series, np.ndarray, list)):
            self.profiles["T_e"] = {
                timeIndex: float(self.cfg["weather"]["T"].iloc[i]) if hasattr(self.cfg["weather"]["T"], 'iloc') else self.cfg["weather"]["T"][i]
                for i, timeIndex in enumerate(self.timeIndex)
            }

        # Build constraint matrices ---
        A_eq, b_eq, A_ineq, b_ineq = self._addConstraints(use_inequality_constraints=use_inequality_constraints) 

        # --- Solver selection ---
        n = len(self.timeIndex)
        if not use_inequality_constraints:
            if A_eq is None:
                raise RuntimeError("No equality constraints assembled.")
            # Only equality constraints, must be square
            print(f"A_eq shape: {A_eq.shape}, A_eq.shape[0]: {A_eq.shape[0]}, A_eq.shape[1]: {A_eq.shape[1]} n_vars: {self.n_vars}")
            if A_eq.shape[0] != A_eq.shape[1]:
                raise ValueError("A_eq must be square for spsolve.")
            x = spsolve(A_eq.tocsr(), b_eq)            

        else:
            x_var = cp.Variable(self.n_vars)
            # y = cp.Variable(n, boolean=True) # added a variable to setup MILP for switching between heat and cooling load, instead of both
            constraints = []
            if A_eq is not None:
                print(f"A_eq.shape: {A_eq.shape}, b_eq.shape: {b_eq.shape}, A_ineq.shape: {A_ineq.shape}, b_ineq.shape: {b_ineq.shape}")
                constraints.append(A_eq @ x_var == b_eq)
            if A_ineq is not None:
                constraints.append(A_ineq @ x_var <= b_ineq)
            
            # M = 1e4 # or a realistic max load for MILP setup

            # for i in range(n): # add constraints related to MILP
                # constraints.append(x_var[3*n + i] <= M * y[i])         # Q_heat <= M * y
                # constraints.append(x_var[4*n + i] <= M * (1 - y[i]))   # Q_cool <= M * (1 - y)
            
            obj = cp.Minimize(cp.sum(x_var[3*n:4*n]))
            prob = cp.Problem( obj, constraints)
            # prob = cp.Problem(cp.Minimize(0), constraints)
            prob.solve(solver=cp.OSQP, verbose=False)
            # prob.solve(solver=cp.CBC, verbose=True) # CBC supports MILP
            if prob.status not in ["optimal", "optimal_inaccurate"]:
                raise RuntimeError(f"cvxpy failed: {prob.status}")
            x = x_var.value
        
        # unpack results
        self.T_air = x[0:n]
        self.T_m = x[n:2*n]
        self.T_sur = x[2*n:3*n]
        self.Q_HC = x[3*n:4*n]

        if comfort_mode == "heating": 
            self.heating_load = np.maximum(0.0, self.Q_HC)
            self.cooling_load = np.zeros_like(self.Q_HC)
        else: 
            self.heating_load = np.zeros_like(self.Q_HC)
            self.cooling_load = np.minimum(0.0, self.Q_HC)

        # Call _readResults to process/store results further
        self._readResults()
        return        

    def _readResults(self):
        """
        Extracts results as a pandas dataframe.
        Populate detailedResults dataframe
        """

        self.detailedResults = pd.DataFrame({
            "Heating Load": self.heating_load,
            "Cooling Load": self.cooling_load,
            "T_air": self.T_air,
            "T_sur": self.T_sur,
            "T_m": self.T_m,
            "T_e": self.cfg["weather"]["T"].values,
            "Electricity Load": self.cfg.get("elecLoad", pd.Series(0.0, index=self.times)).values,
        }, index=[t for t in self.fullTimeIndex]
        )
        # Provide legacy/plotting-friendly attributes expected by standard_plots
        # Use profiles produced in _init5R1C; fall back to zero arrays if missing
        self.Q_sol_win_series = np.asarray(self.profiles.get("bQ_sol_Windows", np.zeros(len(self.times))))
        print(f"Solar gains windows: {self.Q_sol_win_series.sum()}")
        self.Q_sol_opaque_series = np.asarray(self.profiles.get("bQ_sol_Opaque", np.zeros(len(self.times))))
        print(f"Solar gain all opaque components together: {self.Q_sol_opaque_series.sum()}")

        # Ensure temperature arrays exist as 1D numpy arrays (aliases used by plotting)
        self.T_air = np.asarray(self.T_air)
        self.T_m = np.asarray(self.T_m)
        self.T_sur = np.asarray(self.T_sur)

        det = self.diagnostics_solar_components()
        print(f"Diagnostic solar components: {det}")

    def diagnostics_solar_components(self):
        """
        Print and return diagnostics for solar terms and component geometry:
        - per-component total area
        - mean POA (kW/m2) across elements
        - H (kW/K), H * R_se, thermal_rad (kW) and profile sums (kWh)
        """
        det = {}
        R_se = float(self.bConst.get("R_se", 0.0))
        h_r = float(self.bConst.get("h_r", 0.0))
        delta_T_sky = float(self.bConst.get("delta_T_sky", 0.0))
        n = len(self.times)

        for comp, elems in self.component_elements.items():
            areas = [float(e.get("area", 0.0)) for e in elems]
            total_area = float(np.sum(areas)) if areas else 0.0

            # area-weighted mean POA (kW/m2)
            poa_vals = []
            for e in elems:
                eid = e.get("id")
                if eid in self._irrad_surf.columns:
                    poa_vals.append(float(self._irrad_surf[eid].mean()))
            mean_poa = float(np.mean(poa_vals)) if poa_vals else 0.0

            # H (aggregated conductance) and derived terms
            H_comp = float(self.bH.get(comp, {}).get("Original", 0.0))
            H_times_Rse = H_comp * R_se
            thermal_rad = H_comp * h_r * R_se * delta_T_sky

            # profile-based solar (kWh/year) if available in profiles
            profile_key = {
                "Windows": "bQ_sol_Windows",
                "Walls": "bQ_sol_Walls",
                "Roof": "bQ_sol_Roof",
                "Floor": "bQ_sol_Floor",
            }.get(comp, None)
            profile_sum = float(np.sum(self.profiles.get(profile_key, np.zeros(n)))) if profile_key else 0.0

            det[comp] = {
                "total_area_m2": total_area,
                "mean_poa_kW_m2": mean_poa,
                "H_kW_per_K": H_comp,
                "H_times_R_se": H_times_Rse,
                "thermal_rad_kW": thermal_rad,
                "profile_sum_kWh": profile_sum,
            }

        # Print concise table-like diagnostics
        print("SOLAR/COMPONENT DIAGNOSTICS")
        for comp, info in det.items():
            print(
                f" - {comp}: area={info['total_area_m2']:.1f} m2, mean_poa={info['mean_poa_kW_m2']:.4f} kW/m2, "
                f"H={info['H_kW_per_K']:.4f} kW/K, H*R_se={info['H_times_R_se']:.4f}, "
                f"thermal_rad={info['thermal_rad_kW']:.4f} kW, profile_sum={info['profile_sum_kWh']:.2f} kWh"
            )
        # additional global checks
        windows_sum = float(np.sum(self.profiles.get("bQ_sol_Windows", np.zeros(n))))
        opaque_sum = float(np.sum(self.profiles.get("bQ_sol_Opaque", np.zeros(n))))
        print(f" GLOBAL: windows_total_kWh={windows_sum:.2f}, opaque_total_kWh={opaque_sum:.2f}")
        return det
