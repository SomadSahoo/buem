import logging
import pvlib
import sympy as sp

import cvxpy as cp

from scipy.sparse.linalg import spsolve
from scipy.sparse import lil_matrix, vstack

import pandas as pd
import numpy as np



class ModelBUEM(object):
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
        "R_se": 0.04 * 1000,  # external heat transfer coefficient m²K/W
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

    def __init__(self, cfg, maxLoad = None):
        """

        maxLoad: float, optional (default: DesignHeatLoad)
            Maximal load of the heating system.

        """
        self.cfg = cfg 
        self.ventControl = False

        self.maxLoad = maxLoad

        self.times = self.cfg["weather"].index

        # initialize dataframe for irradiance on all surface directions
        self._irrad_surf = pd.DataFrame(index=cfg["weather"].index)


        # initialize result dictionary and dataframes
        self.static_results = {}
        self.detailedResults = pd.DataFrame(index=self.times)
        self.detailedRefurbish = pd.DataFrame()


        # storage for orignal U-values for scaling of the heat demand
        self._orig_U_Values={}

        # Dynamically building components and subcomponents lists from cfg
        self.components = ["Walls", "Roof", "Floor", "Windows", "Ventilation"]
        self.walls = [k.replace('U_', '') for k in cfg if k.startswith('U_Wall')]
        self.roofs = [k.replace('U_', '') for k in cfg if k.startswith('U_Roof')]
        self.floors = [k.replace('U_', '') for k in cfg if k.startswith('U_Floor')]
        self.windows = [k.replace('U_', '') for k in cfg if k.startswith('U_Window')]
        self.ventilations = [k.replace('U_', '') for k in cfg if k.startswith('U_Ventilation')]


        # Symbolic variables for areas, U-values, and transmission factors
        self.A = {name: sp.Symbol(f'A_{name}') for name in self.walls + self.roofs + self.floors}
        self.U_existing = {name: sp.Symbol(f'U_{name}') for name in self.walls + self.roofs + self.floors}
        self.b_Transmission = {name: sp.Symbol(f'b_Transmission_{name}') for name in self.walls + self.roofs + self.floors}




        # for each component, which refurbishment is chosen
        self.bInsul = {}
        # specific heat transfer coefficients for each component for each refurbishment decision
        self.bH = {comp: {} for comp in self.components}
        # specific u values for each component for each refurbishment decision
        self.U = {}

        # raw insulation/refurbishment data
        self.refRaw = {}

        # define refurbishment/extract refurbishment boolean from cfg
        self.bRefurbishment = self.cfg["refurbishment"]

        return
    
    def _initPara(self):
        """
        Initilizes all required list and dicts for indices and params of 
        building model for optmization
        """
        # get profiles dict for all considered time series
        if not hasattr(self, "profiles"):
            self.profiles = {}
        if not hasattr(self, "profilesEval"):
            self.profilesEval = {}
        if not hasattr(self, "exVarIx"):
            self.exVarIx = []
        if not hasattr(self, "exVarActive"):
            self.exVarActive = []
        if not hasattr(self, "exVarInActive"):
            self.exVarInActive = []
        if not hasattr(self, "insulIx"):
            self.insulIx = []
        return

    def _initEnvelop(self):
        """
        Parameterize heat flow for different refurbishment options using numeric values.
        
        keys
        ----------
        components configuration keys required for parameterization and refurbishment decisions:
        - example: Walls: 'U_Wall_1', 'U_Wall_2', ...
        """

        for comp in self.components:
            df = pd.read_excel(self.cfg['costdatapath'], sheet_name=comp, skiprows=[1], index_col=0)
            df = df.dropna(how="all")
            self.refRaw[comp] = df

            if self.bRefurbishment:
                if self.cfg["force_refurbishment"]:
                    self.bInsul[comp] = df.index.unique()[1:]
                else:
                    self.bInsul[comp] = df.index.unique()
                for dec in self.bInsul[comp]:
                    self.exVarIx.append((comp, dec))
                    self.insulIx.append((comp, dec))
            else:
                ix = df.index.unique()[0]
                self.bInsul[comp] = [ix]
                self.exVarIx.append((comp, ix))
                self.insulIx.append((comp, ix))

        # OPAQUE COMPONENTS
        for comp, sublist in zip(["Walls", "Roof", "Floor"], [self.walls, self.roofs, self.floors]):
            df = self.refRaw[comp]
            # Calculate U-values for each refurbishment option (vectorized)
            df["U_Value"] = df["Lambda"] / df["Thickness"]
            df["U_Value"] = df["U_Value"].replace([np.inf, -np.inf], 0.0).fillna(0.0)


            # Calculate bH for each refurbishment option
            for option in self.bInsul[comp]:
                bH = 0.0
                for sub in sublist:
                    U_vals_insul = df.loc[option, "U_Value"]
                    # Handle both scalar and array cases
                    if np.isscalar(U_vals_insul):
                        U_list = [U_vals_insul, self.cfg["U_" + sub]]
                    else:
                        U_list = list(U_vals_insul.values) + [self.cfg["U_" + sub]]

                    U_val = self._calcUVal(U_list)
                    bH += U_val * self.cfg["A_" + sub] * self.cfg["b_Transmission_" + sub] / 1000
                self.bH[comp][option] = bH


        # WINDOWS
        # Add original windows if not present
        df_windows = self.refRaw["Windows"]
        self.g_gl = {}
        self.bH["Windows"] = {}
        self.bU = {"Windows": {}}        
        
        if "Nothing" not in df_windows.index:
            df_windows.loc["Nothing", "g_gl"] = self.cfg["g_gl_n_Window"]
            df_windows.loc["Nothing", "U_Value"] = self.cfg["U_Window"]
        
        else:
            # Fill missing values if present
            if pd.isna(df_windows.loc["Nothing", "g_gl"]):
                df_windows.loc["Nothing", "g_gl"] = self.cfg.get("g_gl_n_Window", 0.5)
            if pd.isna(df_windows.loc["Nothing", "U_Value"]):
                df_windows.loc["Nothing", "U_Value"] = self.cfg.get("U_Window", 1.1)        

        for option in self.bInsul["Windows"]:
            U_val = float(df_windows.loc[option, "U_Value"])
            self.bH["Windows"][option] = self.cfg["A_Window"] * U_val / 1000
            self.bU["Windows"][option] = U_val / 1000
            self.g_gl[option] = float(df_windows.loc[option, "g_gl"])

        # VENTILATION
        df_ventilation = self.refRaw["Ventilation"]
        self.bH["Ventilation"] = {}
        C_air = (
            self.cfg["A_ref"]
            *self.cfg["h_room"]
            *self.CONST["rho_air"]
            *self.CONST["C_air"]
        )
        for option in self.bInsul["Ventilation"]:
            # ventilation heat flow corrected by the recovery rate for usable air
            recovery = float(df_ventilation.loc[option, "Recovery rate"])
            self.bH["Ventilation"][option] = (
                C_air
                * (
                    self.cfg["n_air_use"]
                    * (1 - recovery)
                    + self.cfg["n_air_infiltration"]
                )
                / 3600            
                ) #kW/K

    @staticmethod
    def _calcUVal(U_list):
        U_list = [u for u in U_list if u > 0]
        if not U_list:
            return 0.0
        return 1.0 / sum(1.0 / u for u in U_list)

    def _init5R1C(self):
        """
        Initialize all required parameters required for the 5R1C model (DIN EN ISO 13790). 
        """
        # Constants
        self.bConst = self.CONST

        # Thermal capacity class definition of the building --> also algebraic
        # variant possible
        bClass_f_lb = {
            "very light": 0.0,
            "light": 95.0,
            "medium": 137.5,
            "heavy": 212.5,
            "very heavy": 313.5,
        }
        bClass_f_ub = {
            "very light": 95.0,
            "light": 137.5,
            "medium": 212.5,
            "heavy": 313.5,
            "very heavy": 313.5 * 2,
        }
        bClass_f_a = {
            "very light": 2.5,
            "light": 2.5,
            "medium": 2.5,
            "heavy": 3.0,
            "very heavy": 3.5,
        }

        # heated floor area
        self.bA_f = self.cfg["A_ref"]

        # calculate effective heat transfer of heat capacity
        self.bA_m = self.bA_f * bClass_f_a[self.cfg["thermalClass"]]
        # effective transfer coefficient [kW/K]
        self.bH_ms = self.bA_m * self.bConst["h_ms"] # Eq. 7 Schuetz et al. 2017 

        # specific heat [kJ/m^2/K] (Note: The standard value is overwritten!)
        self.cfg["c_m"] = (
            bClass_f_lb[self.cfg["thermalClass"]]
            + bClass_f_ub[self.cfg["thermalClass"]]
        ) / 2.0
        # internal heat capacity [kWh/K]
        self.bC_m = self.cfg["A_ref"] * self.cfg["c_m"] / 3600.0

        # through door [kW/K]
        self.bH_door = (self.cfg["A_Door_1"] * self.cfg["U_Door_1"]) / 1000

        # internal surface area
        self.bA_tot = self.cfg["A_ref"] * self.bConst["lambda_at"]
        # heat transfer between surface and air node [kW/k] (Schuetz et al. 2017 - eq. 11)
        self.bH_is = self.bA_tot * self.bConst["h_is"]

        # comfort temperature
        self.bT_comf_lb = self.cfg["comfortT_lb"]
        self.bT_comf_ub = self.cfg["comfortT_ub"]

        # shorten code
        #rt = self.cfg["roofTilt"]
        #ro = self.cfg["roofOrientation"]

        ## set relevant geometrical data
        #surf_az = {
        #    "North": 0.0 + ro,
        #    "East": 90.0 + ro,
        #    "South": 180.0 + ro,
        #    "West": 270.0 + ro,
        #    "Horizontal": 180.0,
        #    "Roof 1": 90.0 + ro,
        #    "Roof 2": 270.0 + ro,
        #}
        #surf_tilt = {
        #    "North": 90.0,
        #    "East": 90.0,
        #    "South": 90.0,
        #    "West": 90.0,
        #    "Horizontal": 0.0,
        #    "Roof 1": rt,
        #    "Roof 2": rt,
        #}
        #changed by myj
        # Geometry for solar radiation calculation
        surf_az = {
            "North": 0.0,
            "East": 90.0,
            "South": 180.0,
            "West": 270.0,
            "Horizontal": 180.0,
        }
        surf_tilt = {
            "North": 90.0,
            "East": 90.0,
            "South": 90.0,
            "West": 90.0,
            "Horizontal": 0.0,
        }
        for i, roof in enumerate(self.cfg['roofs'], 1):
            surf_az[f'Roof {i}'] = roof['roofOrientation']
            surf_tilt[f'Roof {i}'] = roof['roofTilt']
    
        F_r = {"North": 0.5, "East": 0.5, "South": 0.5, "West": 0.5, "Horizontal": 1.0}

        self._calcRadiation(surf_az, surf_tilt)

        # solar radiation dict [kW]
        self.bQ_sol = {}

        # WINDOWS
        # get relevant window area for solar irradiance
        window_area_s = {
            di: self.cfg["A_Window_" + di] * self.cfg["F_sh_vert"]
            for di in ["North", "East", "South", "West"]
        }
        window_area_s["Horizontal"] = (
            self.cfg["A_Window_Horizontal"] * self.cfg["F_sh_hor"]
        )

        # get relevant window area for thermal irradiance
        window_area_t = sum(self.cfg["A_Window_" + key] * F_r[key] for key in F_r)
        
        # total_solar_gain=0
        # get solar radiation on window area
        irrad_on_windows = (
            self._irrad_surf.mul(pd.Series(window_area_s)).sum(axis=1).values
        )

        # solar gain time series depending on the investment decision
        for option in self.bInsul["Windows"]:
            # thermal radiation [kW] (Schuetz et al. 2017 - eq. 13)
            thermal_rad = (
                window_area_t
                * self.bConst["h_r"]
                * self.bU["Windows"][option]
                * self.bConst["R_se"]
                * self.bConst["delta_T_sky"]
            )
            self.profiles["bQ_sol_Windows" + option] = (
                irrad_on_windows
                * (1.0 - self.cfg["F_f"])
                * self.cfg["F_w"]
                * self.g_gl[option]
                - thermal_rad
            )
            # total_solar_gain +=self.profiles["bQ_sol_Windows"+var].sum()#myj

        # WALLS
        mean_ver_irr = (
            self._irrad_surf.loc[:, ["North", "East", "South", "West"]]
            .mean(axis=1)
            .values
        )
        for option in self.bInsul["Walls"]:
            # thermal radiation [kW] (Schuetz et al. 2017 - eq. 13)
            thermal_rad = (
                self.bH["Walls"][option]
                * self.bConst["h_r"]
                * self.bConst["R_se"]
                * self.bConst["delta_T_sky"]
            )
            solar_radiation = (
                mean_ver_irr
                * self.bH["Walls"][option]
                * self.cfg["F_sh_vert"]
                * self.bConst["R_se"]
                * self.bConst["alpha"]
            )
            self.profiles["bQ_sol_Walls" + option] = solar_radiation - thermal_rad
            # total_solar_gain += self.profiles["bQ_sol_Walls" + var].sum()

        # ROOF
        mean_roof_irr = self._irrad_surf[[f'Roof {i}' for i in range(1, len(self.cfg['roofs'])+1)]].mean(axis=1).values #changed by myj
        #mean_roof_irr = self._irrad_surf.loc[:, ["Roof 1", "Roof 2"]].mean(axis=1).values
        for option in self.bInsul["Roof"]:
            # thermal radiation (Schuetz et al. 2017 - eq. 13)
            thermal_rad = (
                self.bH["Roof"][option]
                * self.bConst["h_r"]
                * self.bConst["R_se"]
                * self.bConst["delta_T_sky"]
            )
            solar_radiation = (
                mean_roof_irr
                * self.bH["Roof"][option]
                * self.cfg["F_sh_hor"]
                * self.bConst["R_se"]
                * self.bConst["alpha"]
            )
            self.profiles["bQ_sol_Roof" + option] = solar_radiation - thermal_rad
            # total_solar_gain += self.profiles["bQ_sol_Roof" + var].sum()
        return

    def _calcRadiation(self, surf_az, surf_tilt):
        """
        Calculates the radiation to all considered walls and roofs.
        """
        # init required time series
        SOL_POS = pvlib.solarposition.get_solarposition(
            self.cfg["weather"].index, self.cfg["latitude"], self.cfg["longitude"]
        )
        AM = pvlib.atmosphere.get_relative_airmass(SOL_POS["apparent_zenith"])
        DNI_ET = pvlib.irradiance.get_extra_radiation(self.cfg["weather"].index.dayofyear)

        for key in surf_az:
            # calculate total irradiance depending on surface tilt and azimuth
            total = pvlib.irradiance.get_total_irradiance(
                surf_tilt[key],
                surf_az[key],
                SOL_POS["apparent_zenith"],
                SOL_POS["azimuth"],
                dni=self.cfg["weather"]["DNI"],
                ghi=self.cfg["weather"]["GHI"],
                dhi=self.cfg["weather"]["DHI"],
                dni_extra=DNI_ET,
                airmass=AM,
                model="perez",
                surface_type="urban",
            )
            # get plane of array (POA) irradiance and replace nan
            self._irrad_surf[key] = total["poa_global"].fillna(0)

        # W to kW
        self._irrad_surf = self._irrad_surf / 1000
        return   

    def calcDesignHeatLoad(self, symbolic=False):
        """
        Calculates the design heat load which is needed to satisfy the
        nominal outdoor temperature.
        If symbolic is True, returns a sympy expression, instead of numeric values.
        
        Returns
        -------
        designHeatLoad [kW]
        """
        if symbolic:
            # SymPy symbolic version
            b = self.cfg
            A_Roof_1, U_Roof_1, b_Transmission_Roof_1 = sp.symbols('A_Roof_1 U_Roof_1 b_Transmission_Roof_1')
            A_Roof_2, U_Roof_2, b_Transmission_Roof_2 = sp.symbols('A_Roof_2 U_Roof_2 b_Transmission_Roof_2')
            A_Wall_1, U_Wall_1, b_Transmission_Wall_1 = sp.symbols('A_Wall_1 U_Wall_1 b_Transmission_Wall_1')
            A_Wall_2, U_Wall_2, b_Transmission_Wall_2 = sp.symbols('A_Wall_2 U_Wall_2 b_Transmission_Wall_2')
            A_Wall_3, U_Wall_3, b_Transmission_Wall_3 = sp.symbols('A_Wall_3 U_Wall_3 b_Transmission_Wall_3')
            A_Window, U_Window = sp.symbols('A_Window U_Window')
            A_Door_1, U_Door_1 = sp.symbols('A_Door_1 U_Door_1')
            A_Floor_1, U_Floor_1, b_Transmission_Floor_1 = sp.symbols('A_Floor_1 U_Floor_1 b_Transmission_Floor_1')
            A_Floor_2, U_Floor_2, b_Transmission_Floor_2 = sp.symbols('A_Floor_2 U_Floor_2 b_Transmission_Floor_2')
            A_ref, h_room, n_air_infiltration, n_air_use = sp.symbols('A_ref h_room n_air_infiltration n_air_use')
            design_T_min = sp.symbols('design_T_min')

            expr = (
                A_Roof_1 * U_Roof_1 * b_Transmission_Roof_1
                + A_Roof_2 * U_Roof_2 * b_Transmission_Roof_2
                + A_Wall_1 * U_Wall_1 * b_Transmission_Wall_1
                + A_Wall_2 * U_Wall_2 * b_Transmission_Wall_2
                + A_Wall_3 * U_Wall_3 * b_Transmission_Wall_3
                + A_Window * U_Window
                + A_Door_1 * U_Door_1
                + (
                    A_ref
                    * h_room
                    * 1.2
                    * 1006
                    * (n_air_infiltration + n_air_use)
                    / 3600
                )
            ) * (22.917 - design_T_min) + (
                (
                    A_Floor_1 * U_Floor_1 * b_Transmission_Floor_1
                    + A_Floor_2 * U_Floor_2 * b_Transmission_Floor_2
                )
                * (22.917 - design_T_min)
                * 1.45
            )
            return expr / 1000
        b = self.cfg
        designHeatLoad = (
            b["A_Roof_1"] * b["U_Roof_1"] * b["b_Transmission_Roof_1"]
            + b["A_Roof_2"] * b["U_Roof_2"] * b["b_Transmission_Roof_2"]
            + b["A_Wall_1"] * b["U_Wall_1"] * b["b_Transmission_Wall_1"]
            + b["A_Wall_2"] * b["U_Wall_2"] * b["b_Transmission_Wall_2"]
            + b["A_Wall_3"] * b["U_Wall_3"] * b["b_Transmission_Wall_3"]
            + b["A_Window"] * b["U_Window"]
            + b["A_Door_1"] * b["U_Door_1"]
            + (
                b["A_ref"]
                * b["h_room"]
                * 1.2
                * 1006
                * (b["n_air_infiltration"] + b["n_air_use"])
                / 3600
            )
        ) * (22.917 - self.cfg["design_T_min"]) + (
            (
                b["A_Floor_1"] * b["U_Floor_1"] * b["b_Transmission_Floor_1"]
                + b["A_Floor_2"] * b["U_Floor_2"] * b["b_Transmission_Floor_2"]
            )
            * (22.917 - self.cfg["design_T_min"])
            * 1.45
        )
        return designHeatLoad / 1000  

    def _addPara(self):
        """
        Add indices and parameters of the building to the parameterization model.
        """

        self._initPara()

        if hasattr(self, "bMaxLoad"):
            raise NotImplementedError(
                "At the moment only single building"
                + " initialization for enercore network"
                + " possible."
            )

        # limit maximal heat or cooling load
        if self.maxLoad is None:
            designLoad = self.calcDesignHeatLoad()
            self.bMaxLoad = designLoad
            self.maxLoad = designLoad
        else:
            self.bMaxLoad = self.maxLoad
        # define refurbishment
        self.bRefurbishment = self.cfg["refurbishment"]

        # get all envelop values
        self._initEnvelop()

        # get all radiation values
        self._init5R1C()

        # get occupancy data and internal heat gains and electricity load
        # evaluate all profiles with 0 in case of time series aggregation
        self.profiles["bQ_ig"] = self.cfg["Q_ig"]
        self.profiles["bOccNotHome"] = self.cfg["occ_nothome"].values
        self.profiles["bOccSleeping"] = self.cfg["occ_sleeping"].values
        self.profiles["bElecLoad"] = self.cfg["elecLoad"].values
        self.profilesEval["bElecLoad"] = 1.0
        #M.profiles["HeatingLoad"] = self.calcDesignHeatLoad()
        
        # environment temperature
        self.profiles["T_e"] = self.cfg["weather"]["T"].values
        self.profilesEval["T_e"] = 1.0
        #print(M.profiles["HeatingLoad"])
        
        # subsets
        self.bX_opaque = []
        for comp in ["Walls", "Roof", "Floor"]:
            for dec in self.bInsul[comp]:
                self.bX_opaque.append((comp, dec))
        self.bX_windows = []
        for comp in ["Windows"]:
            for dec in self.bInsul[comp]:
                self.bX_windows.append((comp, dec))
        self.bX_vent = []
        for comp in ["Ventilation"]:
            for dec in self.bInsul[comp]:
                self.bX_vent.append((comp, dec))
        self.bX_solar = []
        for comp in ["Windows", "Walls", "Roof"]:
            for dec in self.bInsul[comp]:
                self.bX_solar.append((comp, dec))
 
        # activate or deactivate ventilation control
        if self.cfg["ventControl"]:
            logging.warning("Ventilation control is not validated")
            self.bVentControl = True
        else:
            self.bVentControl = False

        # calculate big M and small m representing max and min heat flow
        self.bM_q = {}
        self.bm_q = {}
        for comp in self.bInsul:
            self.bM_q[comp] = {}
            self.bm_q[comp] = {}
            for dec in self.bInsul[comp]:
                self.bM_q[comp][dec] = self.bH[comp][dec] * (
                    self.bT_comf_ub - (self.cfg["weather"]["T"].min() - 10)
                )
                self.bm_q[comp][dec] = self.bH[comp][dec] * (
                    self.bT_comf_lb - (self.cfg["weather"]["T"].max() + 10)
                )

            # test the values of bM_q and bm_q for NaN values
            for comp in self.bM_q:
                for dec in self.bM_q[comp]:
                    if np.isnan(self.bM_q[comp][dec]):
                        print(f"NaN in bM_q[{comp}][{dec}]")
                    if np.isnan(self.bm_q[comp][dec]):
                        print(f"NaN in bm_q[{comp}][{dec}]")
        
        # define design temperature
        self.bT_des = self.cfg["design_T_min"]       
        
        return 

    def _addVariables(self):   
        """
        Static method to add dimensioning variables to the parameterization
        """
        # Refurbishment decision variables (binary or continuous)
        self.exVars = {}   # Decision variables for each component and refurbishment decision
        self.bQ_comp = {}  # Heat flow through components 
        for comp in self.components:
            for dec in self.bInsul[comp]:
                self.exVars[(comp, dec)] = sp.Symbol(f'exVar_{comp}_{dec}', real=True, nonnegative=True)
                for t1, t2 in self.timeIndex:
                    self.bQ_comp[(comp, dec, t1, t2)] = sp.Symbol(f'bQ_comp_{comp}_{dec}_{t1}_{t2}', real=True)

        # define/declare auxiliary variable for modeling heat flow on thermal mass surface
        self.bP_X = {}
        for (dec_w, comp_w) in self.bX_windows:
            for (dec_x, comp_x) in self.bX_solar:
                self.bP_X[(dec_w, comp_w, dec_x, comp_x)] = sp.Symbol(
                    f'bP_X_{dec_w}_{comp_w}_{dec_x}_{comp_x}', real=True, nonnegative=True
                ) 

        if self.hasTypPeriods: #example: 365 days, 24 steps per day
            num_periods = 365  # or set dynamically
            steps_per_period = 24  # or set dynamically
            self.typPeriodIx = range(num_periods)
            self.intraIx = range(steps_per_period)

        # temperatures variables
        self.bT_m = {}  # thermal mass node temperature
        self.bT_air = {}  # air node temperature
        self.bT_s = {}  # surface node temperature
        for t1, t2 in self.timeIndex:
            self.bT_m[(t1, t2)] = sp.Symbol(f'bT_m_{t1}_{t2}', real=True)
            self.bT_air[(t1, t2)] = sp.Symbol(f'bT_air_{t1}_{t2}', real=True)
            self.bT_s[(t1, t2)] = sp.Symbol(f'bT_s_{t1}_{t2}', real=True)

        # heat flow variables
        self.bQ_ia = {}  # heat flow to air node [kW]
        self.bQ_m = {}  # heat flow to thermal mass node [kW]
        self.bQ_st = {}  # heat flow to surface node [kW]
        for t1, t2 in self.timeIndex:
            self.bQ_ia[(t1, t2)] = sp.Symbol(f'bQ_ia_{t1}_{t2}', real=True)  
            self.bQ_m[(t1, t2)] = sp.Symbol(f'bQ_m_{t1}_{t2}', real=True)  
            self.bQ_st[(t1, t2)] = sp.Symbol(f'bQ_st_{t1}_{t2}', real=True)  

        # ventilation heat flow
        self.bQ_ve = {}  # heat flow through ventilation [kW]
        for t1, t2 in self.timeIndex:
            self.bQ_ve[(t1, t2)] = sp.Symbol(f'bQ_ve_{t1}_{t2}', real=True)

        # external heat losses including heat exchange
        self.bQ_comp = {}  
        for (comp, dec) in self.insulIx:
            for t1, t2 in self.timeIndex:
                self.bQ_comp[(comp, dec, t1, t2)] = sp.Symbol(f'bQ_comp_{comp}_{dec}_{t1}_{t2}', real=True)

        # design heat load
        self.bQ_des = sp.Symbol('bQ_des', real=True, nonnegative=True)

        return            
                                    
    def _readResults(self):
        """
        Extracts results as a pandas dataframe.
        
        """

        self.detailedResults = pd.DataFrame({
            "Heating Load": self.heating_load,
            "Cooling Load": self.cooling_load,
            "T_air": self.T_air,
            "T_sur": self.T_sur,
            "T_m": self.T_m,
            "T_e": self.cfg["weather"]["T"].values,
            "Electricity Load": self.cfg["elecLoad"].values,
        }, index=[t for t in self.fullTimeIndex])

        return

    def scaleHeatLoad(self, scale=1):
        """
        Scales the original heat demand of the model to a relative value 
        by scaling all U-values and the infiltration rate.
        
        scale
        """
        # check if original values have already been saved
        if not bool(self._orig_U_Values):
            for key in self.cfg:
                if str(key).startswith("U_"):
                    self._orig_U_Values[key] = self.cfg[key]
            self._orig_U_Values["n_air_infiltration"] = self.cfg["n_air_infiltration"]
            self._orig_U_Values["n_air_use"] = self.cfg["n_air_use"]
        
        # replace the values in the model
        for key in self._orig_U_Values:
            self.cfg[key] = self._orig_U_Values[key] * scale

        return 

    def _addConstraints(self, use_inequality_constraints:False):
        """
        Builds the coefficient matrices for the time-stepped 5R1C model (with surface node).
        Variable order: [T_air_0, ..., T_air_n-1, T_m_0, ..., T_m_n-1, T_sur_0, ..., T_sur_n-1, Q_heat_0, ..., Q_heat_n-1, Q_cool_0, ..., Q_cool_n-1]
        
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

        # Initialization of series of Q_sol for plotting 
        self.Q_sol_win_series = []
        self.Q_sol_opaque_series = []

        # --- Calculate conductances for each component group ---
        # Walls, Roofs, Floors, Windows, Doors
        def H_sum(component_list, prefix="U_", area_prefix="A_", trans_prefix="b_Transmission_"):
            H = 0.0
            for comp in component_list:
                U = self.cfg.get(prefix + comp, 0)
                A = self.cfg.get(area_prefix + comp, 0)
                bT = self.cfg.get(trans_prefix + comp, 1)
                H += U * A * bT / 1000  # [kW/K]
            return H

        H_walls = H_sum(self.walls)
        H_roofs = H_sum(self.roofs)
        H_floors = H_sum(self.floors)
        H_windows = self.cfg.get("U_Window", 0) * self.cfg.get("A_Window", 0) / 1000
        H_doors = self.cfg.get("U_Door_1", 0) * self.cfg.get("A_Door_1", 0) / 1000

        # Ventilation/infiltration
        A_ref = self.cfg.get("A_ref", 1)
        h_room = self.cfg.get("h_room", 2.5)
        rho_air = self.CONST["rho_air"]
        C_air = self.CONST["C_air"]
        n_air_infiltration = self.cfg.get("n_air_infiltration", 0.5)
        n_air_use = self.cfg.get("n_air_use", 0.5)
        H_ve = (
            A_ref * h_room * rho_air * C_air * (n_air_infiltration + n_air_use) / 3600
        )  # [kW/K]

        # Total transmission
        H_tot = H_ve + H_walls + H_roofs + H_floors + H_windows + H_doors

        #mass-surface and surface-air conductances 
        C_m = self.bC_m
        H_ms = self.bH_ms
        H_is = self.bH_is if hasattr(self, "bH_is") else 3.6 /1000  # fallback

        step = self.stepSize
        # comfortT_lb = self.cfg.get("comfortT_lb", 21.0)
        # comfortT_ub = self.cfg.get("comfortT_ub", 24.0)
        T_set = self.T_set
        sleeping_factor = 0.5

        # Solar gains (windows, per direction)
        window_dirs = ["North", "East", "South", "West", "Horizontal"]
        g_gl = self.cfg.get("g_gl_n_Window", 0.5)
        F_sh_vert = self.cfg.get("F_sh_vert", 1.0)
        F_sh_hor = self.cfg.get("F_sh_hor", 1.0)
        F_w = self.cfg.get("F_w", 1.0)
        F_f = self.cfg.get("F_f", 0.0)
        alpha = self.CONST["alpha"]        

        # Temperature bounds if for inequality constraints
        if use_inequality_constraints:
            T_air_min, T_air_max = 15.0, 30.0
            T_sur_min, T_sur_max = 10.0, 35.0
            T_m_min, T_m_max = 15.0, 30.0
            max_delta_T = 2.0  # Maximum temperature change per hour        

        t = 0
        # Main loop for Building equations
        for i, (t1, t2) in enumerate(self.timeIndex):
            # print(f"t: {t}")
            t = t + 1

            # --- Solar gains ---
            # --- Windows ---
            Q_sol_win = 0.0
            for dir in window_dirs:
                A_win = self.cfg.get(f"A_Window_{dir}", 0)
                F_sh = F_sh_hor if dir == "Horizontal" else F_sh_vert
                if dir in self._irrad_surf:  # by direction, using POA from _irrad_surf
                    irrad = self._irrad_surf.loc[self.times[t2], dir]
                else: # Approximate, or use directional if available
                    irrad = self.cfg["weather"].loc[self.times[t2], "GHI"]

                Q_sol_win += (
                    A_win * g_gl * F_sh * F_w * (1 - F_f) * irrad
                )  # [W], but all areas in m2, G in W/m2 # Check
                
            Q_sol_win = Q_sol_win / 1000  # [kW]
            self.Q_sol_win_series.append(Q_sol_win)


            # Opaque solar gains (walls, roofs, floors)
            Q_sol_opaque = 0.0
            if hasattr(self, "_irrad_surf"):
                # Walls
                for wall in self.walls:
                    A = self.cfg.get(f"A_{wall}", 0)
                    F_sh = F_sh_vert
                    irrad = self._irrad_surf.loc[self.times[t2], wall] if wall in self._irrad_surf else 0
                    Q_sol_opaque += A * alpha * F_sh * irrad  # [kW]
                # Roofs
                for roof in self.roofs:
                    A = self.cfg.get(f"A_{roof}", 0)
                    F_sh = F_sh_hor
                    irrad = self._irrad_surf.loc[self.times[t2], roof] if roof in self._irrad_surf else 0
                    Q_sol_opaque += A * alpha * F_sh * irrad  # [kW]
                # Floors (usually no solar gain, but included for completeness)
                for floor in self.floors:
                    A = self.cfg.get(f"A_{floor}", 0)
                    F_sh = 1.0
                    irrad = self._irrad_surf.loc[self.times[t2], floor] if floor in self._irrad_surf else 0
                    Q_sol_opaque += A * alpha * F_sh * irrad  # [kW]
            else:
                for comp, H_comp in zip(
                    [self.walls, self.roofs, self.floors], [H_walls, H_roofs, H_floors]
                ):
                    for c in comp:
                        A = self.cfg.get(f"A_{c}", 0)
                        F_sh = F_sh_vert if "Wall" in c else F_sh_hor
                        irrad = self.cfg["weather"].loc[self.times[t2], "GHI"]
                        Q_sol_opaque += (
                            A * alpha * F_sh * irrad
                        ) / 1000  # [kW] # Check units for if and else

            self.Q_sol_opaque_series.append(Q_sol_opaque)

            # --- 1. Air node: Energy balance for the air node
            # T_air = (H_is * T_sur + Q_ia + H_ve * T_e) / (H_is + H_ve) ---
            # Internal gains = Q_ig + elecLoad
            occ = 1 - self.profiles["occ_nothome"][(t1, t2)]
            sleeping = self.profiles["occ_sleeping"][(t1, t2)]
            Q_ig = self.profiles["Q_ig"][(t1, t2)]
            elecLoad = self.cfg.get("elecLoad", pd.Series([0], index=[self.times[0]])).iloc[t2]
            Q_ia = (Q_ig + elecLoad) * (occ * (1 - sleeping) + sleeping_factor * sleeping)

            T_e = self.profiles["T_e"][(t1, t2)]

            # Add solar gains to air node (ISO: usually split between air and mass/surface)
            # currently, we are doing a 50-50% split
            Q_air = Q_ia + 0.5 * Q_sol_win

            # T_air * (H_is + H_ve) - H_is * T_sur = Q_ia + H_ve * T_e
            # Equality: air node energy balance
            row = lil_matrix((1, self.n_vars))
            row[0, idx_T_air(i)] = H_is + H_ve
            row[0, idx_T_sur(i)] = -H_is
            row[0, idx_Q_HC(i)] = -1
            # row[0, idx_Q_cool(i)] = -1
            eq_rows.append(row)
            eq_vals.append(Q_air + H_ve * T_e)

            # --- 2. Surface node: Energy balance for the surface node, coupled to air and mass nodes
            # Add solar gains to surface node (ISO: usually split between surface and mass)
            # currently, we are doing a 50-50% split
            Q_surface = Q_sol_opaque + 0.5 * Q_sol_win

            # T_sur = (H_is * T_air + H_ms * T_m + Q_sur) / (H_is + H_ms) ---
            # T_sur * (H_is + H_ms) - H_is * T_air - H_ms * T_m = Q_sur
            # Equality: surface node energy balance
            row = lil_matrix((1, self.n_vars))
            row[0, idx_T_sur(i)] = H_is + H_ms + H_windows
            row[0, idx_T_air(i)] = -H_is
            row[0, idx_T_m(i)] = -H_ms
            eq_rows.append(row)
            eq_vals.append(Q_surface + H_windows*T_e)  

            # --- 3. Mass node: Dynamic energy balance for the mass node, including coupling to surface and transmission to outside
            # C_m * (T_m_next - T_m) / step = H_ms * (T_sur - T_m) - H_tr * (T_m - T_e) ---
            # Equality: Mass node energy balance
            if i == 0:
                row = lil_matrix((1, self.n_vars))
                # Initial condition for T_m at first time step (set to comfort range)
                row[0, idx_T_m(i)] = 1
                eq_rows.append(row)
                eq_vals.append(T_set)

            elif i < n - 1:
                # Mass node dynamics
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

            # --- 4. Heating load: Q_heat = H_tot * T_air ---
            # --- EQUALITY: Q_heat and Q_cool for fixed comfort temperature ---
            # For equality-only solve, set T_air = (comfortT_lb + comfortT_ub)/2
            if not use_inequality_constraints:
                
                # Q_heat = H_tot * max(0, T_set - T_air)
                row = lil_matrix((1, self.n_vars))
                row[0, idx_Q_HC(i)] = 1
                row[0, idx_T_air(i)] = H_tot
                eq_rows.append(row)
                eq_vals.append(H_tot * T_set)

                # Q_cool = H_tot * max(0, T_air - T_set)
                # row = lil_matrix((1, self.n_vars))
                # row[0, idx_Q_HC(i)] = 1
                # row[0, idx_T_air(i)] = -H_tot
                # eq_rows.append(row)
                # eq_vals.append(-H_tot * T_set)
            
            else:
                # Comfort bounds (inequality) comfort_ub >= T_air >= comfort_lb
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_air(i)] = 1
                ineq_rows.append(row)
                ineq_vals.append(T_air_max)
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_air(i)] = -1
                ineq_rows.append(row)
                ineq_vals.append(-T_air_min)
                
                # Q_heat >= H_tot * (comfort_lb - T_air), Q_heat >= 0
                # row = lil_matrix((1, self.n_vars))
                # row[0, idx_Q_heat(i)] = -1
                # row[0, idx_T_air(i)] = H_tot
                # ineq_rows.append(row)
                # ineq_vals.append(H_tot * comfortT_lb)
                # row = lil_matrix((1, self.n_vars))
                # row[0, idx_Q_heat(i)] = -1
                # ineq_rows.append(row)
                # ineq_vals.append(0)
                
                # Q_cool >= H_tot * (T_air - comfort_ub), Q_cool >= 0
                # row = lil_matrix((1, self.n_vars))
                # row[0, idx_Q_cool(i)] = -1
                # row[0, idx_T_air(i)] = -H_tot
                # ineq_rows.append(row)
                # ineq_vals.append(-H_tot * comfortT_ub)
                # row = lil_matrix((1, self.n_vars))
                # row[0, idx_Q_cool(i)] = -1
                # ineq_rows.append(row)
                # ineq_vals.append(0) 

                # --- INEQUALITY: Surface and mass node bounds ---
                # --- T_{sur, m}_min <= T_{sur, m}(t) <= T_{sur, m}_max
                # surface
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_sur(i)] = 1
                ineq_rows.append(row)
                ineq_vals.append(T_sur_max)
                row = lil_matrix((1, self.n_vars))
                row[0, idx_T_sur(i)] = -1
                ineq_rows.append(row)
                ineq_vals.append(-T_sur_min)

                # mass
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

        # ---adding initializations---
        self._initPara()
        self._initEnvelop()
        self._init5R1C()

        self.timeIndex = [(1, t) for t in range(len(self.times))]
        self.fullTimeIndex = self.timeIndex
        timediff = self.times[1] - self.times[0]
        self.stepSize = timediff.total_seconds() / 3600
        self.hasTypPeriods = False

        # Prepare profiles (ensure bQ_ig, occ_nothome, occ_sleeping, T_e are dicts)
        if not hasattr(self, "profiles"):
            self.profiles = {}
        
        # Convert time series into dictionary format
        for key in ["Q_ig", "occ_nothome", "occ_sleeping"]:
            if key not in self.profiles:
                self.profiles[key] = self.cfg[key]
            if isinstance(self.profiles[key], (pd.Series, np.ndarray, list)):
                self.profiles[key] = {
                    timeIndex: self.cfg[key].iloc[i] if hasattr(self.cfg[key], 'iloc') else self.cfg[key][i]
                    for i, timeIndex in enumerate(self.timeIndex)
                }
        
        #set up separate runs for heating and cooling
        if comfort_mode == 'heating':
            T_set = self.cfg["comfortT_lb"]  # e.g., 21.0
        elif comfort_mode == 'cooling':
            T_set = self.cfg["comfortT_ub"]  # e.g., 24.0
        else:
            raise ValueError("comfort_mode must be 'heating' or 'cooling'")  

        #Pass T_set to _addConstraints
        self.T_set = T_set      

        # External temperature profile
        if "T_e" not in self.profiles:
            self.profiles["T_e"] = self.cfg["weather"]["T"]
        if isinstance(self.profiles["T_e"], (pd.Series, np.ndarray, list)):
            self.profiles["T_e"] = {
                timeIndex: self.cfg["weather"]["T"].iloc[i] if hasattr(self.cfg["weather"]["T"], 'iloc') else self.cfg["weather"]["T"][i]
                for i, timeIndex in enumerate(self.timeIndex)
            }

        # Build constraint matrices ---
        A_eq, b_eq, A_ineq, b_ineq = self._addConstraints(use_inequality_constraints=use_inequality_constraints) 

        # --- Solver selection ---
        if use_inequality_constraints:
            solver = 'cvxpy'
        else:
            solver = 'spsolve'

        n = len(self.timeIndex)

        if solver == 'spsolve':
            # Only equality constraints, must be square
            print(f"A_eq shape: {A_eq.shape}, A_eq.shape[0]: {A_eq.shape[0]}, A_eq.shape[1]: {A_eq.shape[1]} n_vars: {self.n_vars}")
            if A_eq.shape[0] != A_eq.shape[1]:
                raise ValueError("A_eq must be square for spsolve.")
            x = spsolve(A_eq.tocsr(), b_eq)
        elif solver == 'cvxpy':
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
            
            prob = cp.Problem(cp.Minimize(cp.sum(x_var[3*n:4*n]) + cp.sum(x_var[4*n:5*n])), constraints)
            # prob = cp.Problem(cp.Minimize(0), constraints)
            prob.solve(solver=cp.OSQP, verbose=False)
            # prob.solve(solver=cp.CBC, verbose=True) # CBC supports MILP
            if prob.status not in ["optimal", "optimal_inaccurate"]:
                raise RuntimeError(f"cvxpy failed: {prob.status}")
            x = x_var.value
        else:
            raise ValueError("Unknown solver specified.")
        
        self.T_air = x[0:n]
        self.T_m = x[n:2*n]
        self.T_sur = x[2*n:3*n]
        self.Q_HC = x[3*n:4*n]
        # self.heating_load = np.maximum(0, x[3*n:4*n])  # enforce non-negativity
        # self.cooling_load = np.maximum(0, x[4*n:5*n])  # enforce non-negativity
        if comfort_mode == "heating": 
            self.heating_load = np.maximum(0, self.Q_HC)
            self.cooling_load = np.zeros_like(self.Q_HC)
        else: 
            self.heating_load = np.zeros_like(self.Q_HC)
            self.cooling_load = -np.minimum(0, self.Q_HC)

        # Call _readResults to process/store results further
        self._readResults()
        return        

