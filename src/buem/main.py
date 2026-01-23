import time
from buem.thermal.model_buem import ModelBUEM
from buem.results.standard_plots import PlotVariables as pvar
from buem.config.cfg_attribute import cfg
from buem.config.validator import validate_cfg
import numpy as np
import sys

# from multiprocessing import Process, Manager

# def run_model(cfg, mode, return_dict):
#     model = ModelBUEM(cfg)
#     model.sim_model(use_inequality_constraints=False, comfort_mode=mode)
#     if mode == "heating":
#         return_dict['model_heat'] = model
#     else:
#         return_dict['model_cool'] = model


def run_model(cfg_dict, plot: bool = False, use_milp: bool = False, return_models: bool = False, fill_missing_components: bool = False):
    """
    Run ModelBUEM for heating and cooling and return results.

    Parameters
    ----------
    cfg_dict : dict
        Normalized configuration dictionary accepted by ModelBUEM.
    plot : bool, optional
        If True, attempt to plot results (best-effort).
    use_milp : bool, optional
        If True attempt the MILP solver path.
    return_models : bool, optional
        If True the returned dict will include "model_heat" and "model_cool" objects.
    fill_missing_components : bool, optional
        If True, attempt to auto-create empty lists for missing components
        (e.g. components.Doors) to allow quick test runs. Use with caution.
    """
    start_time = time.time()

    if cfg_dict is None:
        raise ValueError("cfg_dict must be provided to run_model")

    # Pre-validate configuration and optionally fill missing component lists
    issues = validate_cfg(cfg_dict)
    if issues:
        if fill_missing_components:
            comps = cfg_dict.setdefault("components", {})
            for k in ("Doors", "Windows", "Walls", "Floor", "Roof"):
                if k not in comps:
                    comps[k] = []
            issues = validate_cfg(cfg_dict)  # re-validate after filling defaults

        if issues:
            # fail early with clear message
            raise ValueError("Configuration validation failed: " + "; ".join(issues))

    try:
        if use_milp:
            # Try MILP solver path once. Expect ModelBUEM to set both heating_load and cooling_load.
            model = ModelBUEM(cfg_dict)
            model.sim_model(use_inequality_constraints=True, comfort_mode="heating", use_milp=True)
            if not hasattr(model, "heating_load") or not hasattr(model, "cooling_load"):
                raise RuntimeError("MILP run did not produce heating and/or cooling arrays")
            heating_load = model.heating_load.copy()
            cooling_load = model.cooling_load.copy()
            elapsed = time.time() - start_time

            out = {
                "times": model.times,
                "heating": heating_load,
                "cooling": cooling_load,
                "elapsed_s": elapsed,
            }
            if return_models:
                out["model_heat"] = model
                out["model_cool"] = model
            return out

        # Non-MILP: run two deterministic simulations (heating then cooling)
        model_heat = ModelBUEM(cfg_dict)
        model_heat.sim_model(use_inequality_constraints=False, comfort_mode="heating", use_milp=False)
        heating_load = model_heat.heating_load.copy()

        model_cool = ModelBUEM(cfg_dict)
        model_cool.sim_model(use_inequality_constraints=False, comfort_mode="cooling", use_milp=False)
        cooling_load = model_cool.cooling_load.copy()

        elapsed = time.time() - start_time

        if plot:
            try:
                plotter = pvar()
                plotter.plot_variables(model_heat, model_cool, period='year')
            except Exception:
                import traceback
                traceback.print_exc()

        out = {
            "times": model_heat.times,
            "heating": heating_load,
            "cooling": cooling_load,
            "elapsed_s": elapsed,
        }
        if return_models:
            out["model_heat"] = model_heat
            out["model_cool"] = model_cool
        return out

    except Exception as exc:
        raise RuntimeError(f"Model run failed: {exc}") from exc

def main():
    try:
        # consider enabling fill_missing_components=True for quick ad-hoc runs
        res = run_model(cfg, plot=True, use_milp=False, fill_missing_components=False)
    except ValueError as ve:
        # config validation problems are common; show clear message and exit non-zero
        print("Configuration validation error:", ve)
        sys.exit(2)
    except RuntimeError as re:
        print("Model execution error:", re)
        sys.exit(3)

    heating = res["heating"]
    cooling = res["cooling"]

    total_abs = float(np.sum(heating) + np.sum(np.abs(cooling)))
    print("Total absolute HVAC (heating + |cooling|):", total_abs)

    # check simultaneous hours (if model exposes Q_heat/Q_cool arrays)
    mh = res.get("model_heat")
    if mh is not None and hasattr(mh, "Q_heat") and hasattr(mh, "Q_cool"):
        qh = np.asarray(mh.Q_heat)
        qc = np.asarray(mh.Q_cool)
        sim_hours = int(np.sum((qh > 1e-6) & (qc > 1e-6)))
        print("Simultaneous heating+cooling hours (model_heat):", sim_hours)

    # Create and run the model
    # starttime = time.time()
    # manager = Manager()
    # return_dict = manager.dict()
    # p1 = Process(target = run_model, args=(cfg, "heating", return_dict))
    # p2 = Process(target = run_model, args=(cfg, "cooling", return_dict))

    # p1.start()
    # p2.start()
    # p1.join()
    # p2.join()

    print(f"Heating load total: {res['heating'].sum()} kWh")

    print(f"Cooling load total: {res['cooling'].sum()} kWh")

    # Combine results for plotting, using one model as base
    # model_heat.cooling_load = cooling_load
    # model_heat.detailedResults["Heating Load"] = heating_load
    # model_heat.detailedResults["Cooling Load"] = cooling_load
    # model_heat = return_dict["model_heat"]
    # model_cool = return_dict["model_cool"]


    # print("Detailed Results:")
    # print(model_heat.detailedResults)

    print(f"Execution Time: {res['elapsed_s']:.2f} seconds")

    mh = res.get("model_heat")
    mc = res.get("model_cool")

    # print per-component solar diagnostics from the model instances
    if mh is not None:
        print("\n=== Diagnostics: model_heat ===")
        mh.diagnostics_solar_components()
        # Additional low level diagnostics
        try:
            print("\nLOW-LEVEL PARAMS (model_heat):")
            print(" bU (U-values W/m2K):", mh.bU)
            print(" bH (kW/K):", mh.bH)
            print(" bC_m (kJ/K or stored):", getattr(mh, 'bC_m', None))
            print(" floor_area (m2):", sum(e.get('area',0.0) for e in mh.component_elements.get('Floor', [])))
            print(" total_floor_area (m2):", sum(e.get('area',0.0) for comp in ('Floor','Walls','Roof') for e in mh.component_elements.get(comp, [])))
            # per-m2 energy
            floor_area = sum(e.get('area',0.0) for e in mh.component_elements.get('Floor', [])) or 1.0
            print(f" Heating per floor area: {res['heating'].sum()/floor_area:.1f} kWh/m2-yr")
            print(f" Cooling per floor area: {abs(res['cooling'].sum())/floor_area:.1f} kWh/m2-yr")
        except Exception as _e:
            print("Could not print low-level params:", _e)
    if mc is not None:
        print("\n=== Diagnostics: model_cool ===")
        mc.diagnostics_solar_components()

    # Count hours with heating and cooling active (cooling stored as <= 0 in this model)
    heating = res["heating"]
    cooling = res["cooling"]
    # heating active if > 0, cooling active if < 0 (model stores cooling as negative)
    heat_active = np.asarray(heating) > 0.0
    cool_active = np.asarray(cooling) < 0.0
    both_active = np.logical_and(heat_active, cool_active)
    n_heat_hours = int(np.sum(heat_active))
    n_cool_hours = int(np.sum(cool_active))
    n_both_hours = int(np.sum(both_active))
    n_total = len(res["times"])
    print(f"\nOPERATION COUNTS (year, {n_total} h): heating_hours={n_heat_hours}, cooling_hours={n_cool_hours}, simultaneous_hours={n_both_hours}")


if __name__=="__main__":
    main()