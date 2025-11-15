import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
from buem.occupancy.occupancy_profile import OccupancyProfile

class ElectricityConsumptionProfile:
    """
    Generates an hourly electricity consumption profile for a single building,
    based on occupancy and appliance usage, following Richardson et al. (2010).

    The profile is generated for one year with hourly resolution, using the
    occupancy profile as input. Each appliance can be enabled or disabled.
    The total power consumption is the sum of all enabled appliances.
    Appliance usage probabilities and weights are determined by:
    - Day type (weekday/weekend)
    - Hour of day
    - Percentage of persons at home and active/inactive
    - Behavioral patterns (e.g., TV more likely in evening, cleaning more likely on weekends)
    """

    def __init__(
        self,
        occupancy_profile: OccupancyProfile,
        has_cooking=True,
        has_tv=True,
        has_laundry=True,
        has_cleaning=True,
        has_ironing=True,
        has_fridge=True,
        has_other=True,
        seed=None,
    ):
        """
        Initialize the ElectricityConsumptionProfile class.

        Parameters
        ----------
        occupancy_profile : OccupancyProfile
            An instance of OccupancyProfile (already initialized).
        has_cooking : bool, optional
            Whether cooking appliance is present (default: True).
        has_tv : bool, optional
            Whether TV is present (default: True).
        has_laundry : bool, optional
            Whether washing machine is present (default: True).
        has_cleaning : bool, optional
            Whether house cleaning appliance (e.g., vacuum) is present (default: True).
        has_ironing : bool, optional
            Whether iron is present (default: True).
        has_fridge : bool, optional
            Whether refrigerator is present (default: True).
        has_other : bool, optional
            Whether other background loads are present (default: True).
        seed : int, optional
            Random seed for reproducibility. If None, uses the seed from occupancy_profile.
        """

        self.occ = occupancy_profile
        # Use the same seed as occupancy profile if not provided
        self.seed = seed if seed is not None else getattr(occupancy_profile, 'seed', None)
        self.rng = np.random.default_rng(self.seed)
        self.has_cooking = has_cooking
        self.has_tv = has_tv
        self.has_laundry = has_laundry
        self.has_cleaning = has_cleaning
        self.has_ironing = has_ironing
        self.has_fridge = has_fridge
        self.has_other = has_other

        self.profile = None

    def get_weightage_table(self):
        """
        Returns a dictionary of weightage tables for each appliance/activity.
        Each table is a dict with keys 'weekday' and 'weekend', and values are arrays of length 24 (hours).
        These weights are used to modulate the probability of appliance use by hour and day type.

        Returns
        -------
        dict
            Dictionary of weightage tables for each appliance/activity.
        """
        # Example: weights between 0 and 1 for each hour of the day
        table = {
            'tv': {
                'weekday': np.array([
                    0.05, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.1, 0.1, 0.1, 0.1, 0.1,
                    0.15, 0.15, 0.15, 0.15, 0.2, 0.4, 0.6, 0.7, 0.8, 0.7, 0.5, 0.2
                ]),
                'weekend': np.array([
                    0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5,
                    0.6, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8, 0.8, 0.7, 0.6, 0.4, 0.2
                ])
            },
            'cooking': {
                'weekday': np.array([
                    0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.2, 0.4, 0.2, 0.1, 0.1, 0.1,
                    0.7, 0.7, 0.2, 0.1, 0.1, 0.7, 0.8, 0.7, 0.2, 0.1, 0.05, 0.01
                ]),
                'weekend': np.array([
                    0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6,
                    0.8, 0.8, 0.7, 0.5, 0.3, 0.7, 0.8, 0.8, 0.5, 0.2, 0.05, 0.01
                ])
            },
            'laundry': {
                'weekday': np.array([
                    0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.1, 0.2, 0.2, 0.2, 0.2,
                    0.2, 0.2, 0.2, 0.2, 0.2, 0.1, 0.05, 0.01, 0.01, 0.01, 0.01, 0.01
                ]),
                'weekend': np.array([
                    0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.2, 0.4, 0.5, 0.5, 0.4, 0.3,
                    0.2, 0.2, 0.2, 0.2, 0.2, 0.1, 0.05, 0.01, 0.01, 0.01, 0.01, 0.01
                ])
            },
            'cleaning': {
                'weekday': np.array([
                    0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, 0.05, 0.1, 0.1, 0.1,
                    0.1, 0.1, 0.1, 0.2, 0.3, 0.4, 0.4, 0.3, 0.2, 0.1, 0.05, 0.01
                ]),
                'weekend': np.array([
                    0.05, 0.05, 0.05, 0.05, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7,
                    0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1
                ])
            }
            # More can be added if required
        }
        return table

    def generate(self):
        """
        Generate the total electricity consumption profile for the year.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by hourly timestamps, with columns:
            - 'n_home': number of persons at home
            - 'n_active': number of active persons at home
            - 'activity': main activity state
            - 'total_power_kwh': total electricity consumption (kWh) for each hour
        """
        occ_profile = self.occ.get_profile().copy()
        n = len(occ_profile)

        # Appliances: hourly power consumption arrays (kWh per hour)
        total = np.zeros(n)

        if self.has_fridge:
            total += self.fridge_profile(occ_profile)

        if self.has_tv:
            total += self.tv_profile(occ_profile)

        if self.has_cooking:
            total += self.cooking_profile(occ_profile)

        if self.has_laundry:
            total += self.laundry_profile(occ_profile)

        if self.has_cleaning:
            total += self.cleaning_profile(occ_profile)

        if self.has_ironing:
            total += self.ironing_profile(occ_profile)

        if self.has_other:
            total += self.other_profile(occ_profile)

        occ_profile['total_power_kwh'] = total
        self.profile = occ_profile
        return self.profile

    def fridge_profile(self, occ_profile):
        """
        Generate the refrigerator power consumption profile.

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Returns
        -------
        np.ndarray
            Hourly refrigerator power consumption (kWh).
        """
        # Fridge runs all the time, ~0.04 kWh per hour (1 kWh/day)
        standby = 0.04  # kWh/h
        return np.full(len(occ_profile), standby)

    def tv_profile(self, occ_profile):
        """
        Generate the TV power consumption profile.

        TV usage probability is determined by:
        - The proportion of people at home and active (higher if more are active).
        - Lower probability if most are inactive (likely sleeping).
        - Higher probability in the evening (18~23h) on weekdays.
        - Higher probability in late morning/afternoon (10~18h) on weekends.
        - TV is not on when nobody is at home

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Returns
        -------
        np.ndarray
            Hourly TV power consumption (kWh).
        """
        # Standby: 0.002 kWh/h (2W), On: 0.25 kWh/h (250W)
        standby = 0.002
        on = 0.25
        n = len(occ_profile)
        tv_power = np.full(n, standby)
        weights = self.get_weightage_table()['tv']
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        n_home = occ_profile['n_home'].values
        n_active = occ_profile['n_active'].values
        percent_active = np.divide(n_active, n_home, out=np.zeros_like(n_active, dtype=float), where=n_home > 0)
        # TV more likely if more people are active, less if most are inactive
        base_prob = 0.2 + 0.6 * percent_active  # 0.2 to 0.8
        # Apply hourly and day-type weights
        hour_weights = np.where(is_weekend, weights['weekend'][hours], weights['weekday'][hours])
        p_tv_on = base_prob * hour_weights
        # TV never on if nobody at home
        p_tv_on[n_home == 0] = 0
        tv_on_hours = self.rng.binomial(1, p_tv_on)
        tv_power[(n_home > 0) & (tv_on_hours == 1)] = on
        tv_power[n_home == 0] = 0
        return tv_power

    def cooking_profile(self, occ_profile):
        """
        Generate the cooking appliance power consumption profile.

        Cooking probability is weighted:
        - Higher in the hour before lunch (12~14h) and dinner (18~20h) on weekdays.
        - Higher in late morning and afternoon on weekends, with breakfast possibly skipped or delayed.
        - Only when at least one person is at home and active.

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Returns
        -------
        np.ndarray
            Hourly cooking power consumption (kWh).
        """
        n = len(occ_profile)
        cooking_power = np.zeros(n)
        weights = self.get_weightage_table()['cooking']
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        n_active = occ_profile['n_active'].values
        n_home = occ_profile['n_home'].values
        percent_active = np.divide(n_active, n_home, out=np.zeros_like(n_active, dtype=float), where=n_home > 0)
        # Base probability: higher if more people are active
        base_prob = 0.2 + 0.6 * percent_active  # 0.2 to 0.8
        hour_weights = np.where(is_weekend, weights['weekend'][hours], weights['weekday'][hours])
        p_cook = base_prob * hour_weights
        # Only possible if at least one person is active
        p_cook[n_active == 0] = 0
        cook_events = self.rng.binomial(1, p_cook)
        cooking_power[(n_active > 0) & (cook_events == 1)] = 1.5
        return cooking_power

    def laundry_profile(self, occ_profile):
        """
        Generate the washing machine (laundry) power consumption profile.

        Washing machine usage probability is determined by:
        - Higher probability on weekends, especially in the morning (8~10h).
        - On weekdays, higher probability mid-week (Wednesdays/Thursdays).
        - Only when someone is at home and active.

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Returns
        -------
        np.ndarray
            Hourly laundry power consumption (kWh).
        """
        n = len(occ_profile)
        laundry_power = np.zeros(n)
        weights = self.get_weightage_table()['laundry']
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        weekday = occ_profile.index.weekday
        n_active = occ_profile['n_active'].values
        # Base probability: higher on weekends, and mid-week (Wed/Thu) on weekdays
        base_prob = np.where(is_weekend, 0.15, 0.05)
        # Boost for Wed/Thu because laundry normally happens every 3-4 days
        base_prob[(weekday == 2) | (weekday == 3)] += 0.05
        hour_weights = np.where(is_weekend, weights['weekend'][hours], weights['weekday'][hours])
        p_laundry = base_prob * hour_weights
        # Only possible if at least one person is active
        p_laundry[n_active == 0] = 0
        laundry_events = self.rng.binomial(1, p_laundry)
        laundry_power[(n_active > 0) & (laundry_events == 1)] = 0.5
        return laundry_power

    def cleaning_profile(self, occ_profile):
        """
        Generate the house cleaning appliance power consumption profile.

        Cleaning probability is weighted:
        - Heavily during the whole day on weekends.
        - On weekdays, more likely in the evening (16~20h), not at night.
        - More likely when a moderate percentage of total persons are present and active (not all, not zero).
        - Not likely if most are inactive (sleeping).

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Returns
        -------
        np.ndarray
            Hourly cleaning power consumption (kWh).
        """
        n = len(occ_profile)
        cleaning_power = np.zeros(n)
        weights = self.get_weightage_table()['cleaning']
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        n_home = occ_profile['n_home'].values
        n_active = occ_profile['n_active'].values
        percent_active = np.divide(n_active, n_home, out=np.zeros_like(n_active, dtype=float), where=n_home > 0)
        # Cleaning more likely if 20-80% of people are active (not all, not zero)
        mask = (percent_active > 0.2) & (percent_active < 0.8) & (n_active > 0)
        # Base probability: higher on weekends
        base_prob = np.where(is_weekend, 0.2, 0.05)
        hour_weights = np.where(is_weekend, weights['weekend'][hours], weights['weekday'][hours])
        p_clean = base_prob * hour_weights
        # Only possible if mask is True
        p_clean[~mask] = 0
        cleaning_events = self.rng.binomial(1, p_clean)
        cleaning_power[mask & (cleaning_events == 1)] = 0.4
        return cleaning_power

    def ironing_profile(self, occ_profile):
        """
        Generate the ironing appliance power consumption profile.

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Ironing probability is uniform, but only when someone is at home and active.

        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame
        
        Returns
        -------
        np.ndarray
            Hourly ironing power consumption (kWh).
        """
        n = len(occ_profile)
        ironing_power = np.zeros(n)
        n_active = occ_profile['n_active'].values
        # 1 session per week, randomly distributed among hours with at least one active person
        possible_hours = np.where(n_active > 0)[0]
        n_sessions = int(len(occ_profile) / (24*7))  # 1 per week
        if len(possible_hours) > 0 and n_sessions > 0:
            chosen_hours = self.rng.choice(possible_hours, size=n_sessions, replace=False)
            ironing_power[chosen_hours] = 1.0
        return ironing_power

    def other_profile(self, occ_profile):
        """
        Generate the other/background loads power consumption profile.
        Other activities include background loads, computers, chargers, etc. 
        - works only when someone is at home
        
        Other loads are slightly higher on weekends.
        
        Parameters
        ----------
        occ_profile : pd.DataFrame
            Occupancy profile DataFrame.

        Returns
        -------
        np.ndarray
            Hourly other/background power consumption (kWh).
        """
        n_home = occ_profile['n_home'].values
        is_weekend = occ_profile.index.weekday >= 5
        # 0.05 kWh/h per person at home, 20% higher on weekends
        base = 0.05 * n_home
        base[is_weekend] *= 1.2
        return base

    def get_profile(self):
        """
        Returns the generated electricity consumption profile, or generates it if not already done.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by hourly timestamps, with columns:
            - 'n_home': number of persons at home
            - 'n_active': number of active persons at home
            - 'activity': main activity state
            - 'total_power_kwh': total electricity consumption (kWh) for each hour
        """
        if self.profile is None:
            return self.generate()
        return self.profile
    
def plot_weekly_total_power(profile, week_start='2025-01-01'):
    """
    Plot the total power consumption for each day in a week.

    Parameters
    ----------
    profile : pd.DataFrame
        Electricity consumption profile with 'total_power_kwh' column.
    week_start : str
        Start date of the week (YYYY-MM-DD).
    """

    week = pd.date_range(start=week_start, periods=7, freq='D')
    fig, axes = plt.subplots(4, 1, figsize=(8, 10), sharex=True)
    days = week[:4]

    for i, day in enumerate(days):
        day_profile = profile.loc[day.strftime('%Y-%m-%d')]
        axes[i].step(day_profile.index.hour, day_profile['total_power_kwh'], where='post', linewidth=2)
        axes[i].set_ylim(0, profile['total_power_kwh'].max() + 0.5)
        axes[i].set_xlim(0, 24)
        axes[i].set_ylabel('Total power (kWh)')
        axes[i].set_title(f"{day.strftime('%A, %Y-%m-%d')}")
        axes[i].grid(True, axis='y', linestyle='--', alpha=0.5)

    axes[-1].set_xlabel('Time of day (h)')
    plt.tight_layout()
    plt.show()

def plot_weekly_appliance_usage(elec, week_start='2025-01-01'):
    """
    Plot on/off timeline for each appliance over one week using horizontal lines.

    - Each appliance is represented by a horizontal baseline (OFF).
    - Standby intervals are drawn as slightly thicker segments over the baseline.
    - Active/ON intervals are drawn as thick segments (visually prominent).
    - X-axis shows days of the week (midnight ticks). Y-axis lists appliances.
    - Timeline resolution is hourly and uses the instance's occupancy slice for the given period.

    Parameters
    ----------
    elec : ElectricityConsumptionProfile
        Initialized ElectricityConsumptionProfile instance. The function uses appliance
        methods (tv_profile, cooking_profile, etc.) on the occupancy slice for the week.
    week_start : str
        Start date of the week (YYYY-MM-DD).

    Returns
    -------
    matplotlib.figure.Figure
        The matplotlib figure object containing the plot.
    """
    # obtain full profile and slice the requested week
    occ_profile = elec.get_profile()
    start = pd.to_datetime(week_start)
    end = start + pd.Timedelta(days=7) - pd.Timedelta(hours=1)
    idx = pd.date_range(start=start, end=end, freq='h')
    occ_week = occ_profile.loc[idx].copy()

    # compute per-appliance power (kWh) for the week using the instance methods
    tv_power = elec.tv_profile(occ_week)
    cooking_power = elec.cooking_profile(occ_week)
    laundry_power = elec.laundry_profile(occ_week)
    cleaning_power = elec.cleaning_profile(occ_week)
    ironing_power = elec.ironing_profile(occ_week)
    fridge_power = elec.fridge_profile(occ_week)
    other_power = elec.other_profile(occ_week)

    # Define thresholds and states:
    # state: 0 = OFF, 1 = STANDBY, 2 = ON
    # For appliances that are binary (0 or >0), standby will not be used.
    thresholds = {
        'Fridge': {'standby_min': 0.01, 'on_min': 0.5},   # fridge modeled as continuous small load -> treat as standby/on accordingly
        'TV': {'standby_min': 0.001, 'on_min': 0.1},
        'Cooking': {'standby_min': 0.01, 'on_min': 0.5},
        'Laundry': {'standby_min': 0.01, 'on_min': 0.1},
        'Cleaning': {'standby_min': 0.01, 'on_min': 0.1},
        'Ironing': {'standby_min': 0.01, 'on_min': 0.5},
        'Other': {'standby_min': 0.01, 'on_min': 0.1},
    }

    powers = {
        'Fridge': fridge_power,
        'TV': tv_power,
        'Cooking': cooking_power,
        'Laundry': laundry_power,
        'Cleaning': cleaning_power,
        'Ironing': ironing_power,
        'Other': other_power,
    }


    # helper to convert boolean mask to contiguous datetime segments
    def mask_to_segments(mask, times):
        """
        Convert boolean mask (length N) and corresponding DatetimeIndex times to list of segments.
        Each segment returned as (start_datetime, end_datetime) where end is exclusive (end = last_true + 1 hour).
        """
        segments = []
        if not mask.any():
            return segments
        arr = mask.astype(int)
        diff = np.diff(np.concatenate(([0], arr, [0])))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        for s, e in zip(starts, ends):
            start_t = times[s]
            end_t = times[e - 1] + pd.Timedelta(hours=1)
            segments.append((start_t, end_t))
        return segments

    appliance_names = list(powers.keys())
    fig, ax = plt.subplots(figsize=(14, 1.2 * len(appliance_names) + 1))

    # visual parameters
    baseline_color = "#dcdcdc"
    standby_color = "#7f7f7f"
    on_color = "#111111"
    baseline_lw = 0.8            # thin baseline for OFF
    standby_lw = 2.0             # slightly thicker for standby
    on_lw = 5.0                  # thick for ON (visually prominent)

    # plot baseline for each appliance across whole week (OFF appearance)
    for i, name in enumerate(appliance_names):
        y = len(appliance_names) - 1 - i  # invert so first item at top
        ax.hlines(y, idx[0], idx[-1] + pd.Timedelta(hours=1), colors=baseline_color, linewidth=baseline_lw)

    # overlay standby and on segments
    for i, name in enumerate(appliance_names):
        y = len(appliance_names) - 1 - i
        power = np.asarray(powers[name])
        th = thresholds.get(name, {'standby_min': 0.01, 'on_min': 0.1})
        standby_min = th['standby_min']
        on_min = th['on_min']

        # masks
        mask_on = power >= on_min
        mask_standby = (power >= standby_min) & (power < on_min)

        # convert to segments
        standby_segments = mask_to_segments(mask_standby, idx)
        on_segments = mask_to_segments(mask_on, idx)

        # draw standby segments
        for (s, e) in standby_segments:
            ax.hlines(y, s, e, colors=standby_color, linewidth=standby_lw)

        # draw ON segments
        for (s, e) in on_segments:
            ax.hlines(y, s, e, colors=on_color, linewidth=on_lw)

    # formatting
    # x ticks at each midnight with day labels
    midnight_idx = np.where(idx.hour == 0)[0]
    xticks = [idx[i] for i in midnight_idx] + [idx[-1] + pd.Timedelta(hours=1)]
    ax.set_xticks(xticks)
    xtick_labels = [t.strftime('%a %d') for t in xticks[:-1]] + [(xticks[-1] - pd.Timedelta(hours=1)).strftime('%a %d')]
    ax.set_xticklabels(xtick_labels, rotation=45, ha='right')

    # y ticks
    y_pos = np.arange(len(appliance_names))
    ax.set_yticks(len(appliance_names) - 1 - y_pos)
    ax.set_yticklabels(appliance_names)

    ax.set_xlim(idx[0], idx[-1] + pd.Timedelta(hours=1))
    ax.set_ylabel('Appliance', fontsize=12)
    ax.set_title(f'Appliance ON / STANDBY timeline (week starting {start.date()})')
    ax.grid(axis='x', linestyle='--', alpha=0.3)

    ax.set_xlabel('Day of the week', fontsize=12)
    plt.tight_layout()
    plt.show()
    return fig


# Example usage:
if __name__ == "__main__":
    start_time = time.time()
    occ = OccupancyProfile(num_persons=4, year=2025, seed=123)
    elec = ElectricityConsumptionProfile(occ)
    profile = elec.generate()
    print("Total time taken: ", time.time() - start_time)
    week_profile = profile.loc['2025-01-01 00:00':'2025-01-07 23:00']
    print(week_profile[['n_home', 'n_active', 'total_power_kwh']])
    plot_weekly_total_power(profile, week_start='2025-01-01')
    plot_weekly_appliance_usage(elec)