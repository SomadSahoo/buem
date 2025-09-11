import time
from buem.thermal.model_buem import ModelBUEM
from buem.config.cfg_attribute import cfg

def main():
    starttime = time.time()
    # Create and run the model
    # starttime = time.time()
    model = ModelBUEM(cfg)
    model.sim_model(use_inequality_constraints=False)

    print("Detailed Results:")
    print(model.detailedResults)
    print(f"Heating load total: {model.heating_load.sum()}")
    print(f"Cooling load total: {model.cooling_load.sum()}")

    print("Execution Time:", f"{time.time() - starttime:.2f}", "seconds")
    
    # plot the model
    model.plot_variables(period ='year')    # 8760 hours

if __name__=="__main__":
    main()