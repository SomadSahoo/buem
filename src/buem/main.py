import time
from buem.thermal.model_buem import ModelBUEM
from buem.results.standard_plots import PlotVariables as pvar
from buem.config.cfg_attribute import cfg

# from multiprocessing import Process, Manager

# def run_model(cfg, mode, return_dict):
#     model = ModelBUEM(cfg)
#     model.sim_model(use_inequality_constraints=False, comfort_mode=mode)
#     if mode == "heating":
#         return_dict['model_heat'] = model
#     else:
#         return_dict['model_cool'] = model


def run_model(cfg_dict, plot=False):
    """
    Run ModelBUEM for heating and cooling and return results.
    Returns dict: {"times": DatetimeIndex, "heating": pd.Series, "cooling": pd.Series}
    """
    starttime = time.time()
    
    # model run for heating
    model_heat = ModelBUEM(cfg_dict)
    model_heat.sim_model(use_inequality_constraints=False, comfort_mode="heating")
    heating_load = model_heat.heating_load.copy()
    
    # model run for cooling
    model_cool = ModelBUEM(cfg_dict)
    model_cool.sim_model(use_inequality_constraints=False, comfort_mode="cooling")
    cooling_load = model_cool.cooling_load.copy()
    elapsed = time.time() - starttime


    if plot:
        try:
            plotter = pvar()
            plotter.plot_variables(model_heat, model_cool, period='year')
        except Exception:
            pass

    return {"times": model_heat.times, "heating": heating_load, "cooling": cooling_load, "elapsed_s": elapsed}


def main():
    res = run_model(cfg, plot=True)
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

    print(f"Heating load total: {res["heating"].sum()}")

    print(f"Cooling load total: {res["cooling"].sum()}")

    # Combine results for plotting, using one model as base
    # model_heat.cooling_load = cooling_load
    # model_heat.detailedResults["Heating Load"] = heating_load
    # model_heat.detailedResults["Cooling Load"] = cooling_load
    # model_heat = return_dict["model_heat"]
    # model_cool = return_dict["model_cool"]


    # print("Detailed Results:")
    # print(model_heat.detailedResults)

    print("Execution Time:", f"{res["elapsed_s"]:.2f}", "seconds")


if __name__=="__main__":
    main()