import pandas as pd 
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

class PlotVariables:   
    def plot_variables(self, model_heat, model_cool, period='day'):
        """
        Plot building thermal variables and loads.
        
        Parameters
        ----------
        period : str
            Time period to plot: 'day' (24h), 'month' (720h), or 'year' (8760h)
        """        

        # Basic validation: ensure required attributes exist so errors are clear
        required_attrs = [
            'T_air','T_m','T_sur',
            'heating_load','cooling_load',
            'Q_sol_win_series','Q_sol_opaque_series',
            'profiles','cfg'
        ]
        missing = [a for a in required_attrs if not hasattr(model_heat, a)]
        if missing:
            raise AttributeError(f"model_heat missing attributes required for plotting: {missing}")

        # Define time periods
        periods = {
            'day': 24,
            'month': 720,
            'year': 8760
        }
        n_hours = periods.get(period, 24)  # default to day if invalid period

        # Determine available length from model (defensive)
        total_len = None
        if hasattr(model_heat, 'times'):
            try:
                total_len = len(model_heat.times)
            except Exception:
                total_len = None
        if total_len is None and hasattr(model_heat, 'timeIndex'):
            try:
                total_len = len(model_heat.timeIndex)
            except Exception:
                total_len = None
        if total_len is None:
            # fallback: use lengths of arrays we checked exist
            total_len = min(len(model_heat.T_air), len(model_heat.heating_load))
        n_hours = min(n_hours, total_len)
        time_hours = range(n_hours)
        
        # Store Q_ia values during simulation if not already stored
        if not hasattr(model_heat, 'Q_ia'):
            # build Q_ia defensively — profiles or indexing may vary between runs
            try:
                elec = model_heat.cfg.get("elecLoad", None)
                if elec is None:
                    elec_vals = np.zeros(total_len)
                else:
                    # ensure elec_vals has at least total_len entries
                    elec_vals = np.asarray(elec).ravel()
                    if len(elec_vals) < total_len:
                        elec_vals = np.pad(elec_vals, (0, total_len - len(elec_vals)))

                qia = []
                for t in range(total_len):
                    q_ig = model_heat.profiles.get("Q_ig", {}).get((1, t), 0)
                    occ_nh = model_heat.profiles.get("occ_nothome", {}).get((1, t), 0)
                    occ_sl = model_heat.profiles.get("occ_sleeping", {}).get((1, t), 0)
                    qia_val = (q_ig + elec_vals[t]) * ((1 - occ_nh) * (1 - occ_sl) + 0.5 * occ_sl)
                    qia.append(qia_val)
                model_heat.Q_ia = np.array(qia)
            except Exception:
                # last-resort: zero array
                model_heat.Q_ia = np.zeros(total_len)
        
        # Create figure with subplots
        fig = plt.figure(figsize=(18, 10))
        gs = GridSpec(3, 1, height_ratios=[1, 1, 1])
        
        # 1. Temperature plot
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(time_hours, model_heat.T_air[:n_hours], label='Air Temperature', linewidth=2)
        ax1.plot(time_hours, model_heat.T_m[:n_hours], label='Mass Temperature', linewidth=2)
        ax1.plot(time_hours, model_heat.T_sur[:n_hours], label='Surface Temperature', linewidth=2)
        
        # Add comfort bounds
        ax1.axhline(y=model_heat.cfg["comfortT_lb"], color='r', linestyle='--', alpha=0.5, label='Min Comfort')
        ax1.axhline(y=model_heat.cfg["comfortT_ub"], color='r', linestyle='--', alpha=0.5, label='Max Comfort')

        # Add external temperature
        T_e = [model_heat.profiles.get("T_e", {}).get((1, t), np.nan) for t in range(n_hours)]
        ax1.plot(time_hours, T_e, label='External Temperature', color='gray', alpha=0.5)
        
        ax1.set_ylabel('Temperature [°C]', fontsize=18)
        ax1.set_title(f'Building Temperatures ({period}) [A]', fontsize=20, pad=20)
        ax1.grid(True)
        ax1.legend(fontsize=16, loc='lower center', bbox_to_anchor=(0.5, -0.05), ncol=2, framealpha=0.5)
        
        # 2. Loads plot
        ax2 = fig.add_subplot(gs[1])
        ax2.plot(time_hours, model_heat.heating_load[:n_hours], label='Heating Demand', color='red')
        ax2.plot(time_hours, model_cool.cooling_load[:n_hours], label='Cooling Demand', color='blue')
        ax2.set_ylabel('Demand [kWh/h]', fontsize=18)
        ax2.set_title(f'Heating and Cooling Demands ({period}) [B]', fontsize=20, pad=20)
        ax2.grid(True)
        ax2.legend(fontsize=16, loc='best', framealpha=0.8)
        
        # 3. Solar gains plot
        ax3 = fig.add_subplot(gs[2])
        ax3.plot(time_hours, model_heat.Q_sol_win_series[:n_hours], label='Solar Gains Windows', color='darkgreen')
        ax3.plot(time_hours, model_heat.Q_sol_opaque_series[:n_hours], label='Solar Gains Opaque', color='magenta')
        ax3.set_xlabel('Time [hours]', fontsize=20, labelpad=15)
        ax3.set_ylabel('Solar Gains [kWh/h]', fontsize=18)
        ax3.set_title(f'Solar Gains ({period}) [C]', fontsize=20, pad=20)
        ax3.grid(True)
        ax3.legend(fontsize=16, loc='best', framealpha=0.8)

        # Set font size for axis tick labels
        for ax in [ax1, ax2, ax3]:
            ax.tick_params(axis='x', labelsize=16)
            ax.tick_params(axis='y', labelsize=16)

        # Align y-labels for all subplots
        fig.align_ylabels([ax1, ax2, ax3])
        
        # Adjust layout and display
        plt.tight_layout()
        plt.show()

        # Print some statistics
        print(f"\nStatistics for the {period}:")
        print(f"Total heating energy: {model_heat.heating_load[:n_hours].sum():.2f} kWh")
        print(f"Total cooling energy: {model_cool.cooling_load[:n_hours].sum():.2f} kWh")    