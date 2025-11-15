import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
from typing import Optional

class OccupancyProfile:
    """
    Generates stochastic occupancy profiles for a single building based on the number of occupants and year.
    The model produces hourly profiles for the entire year, distinguishing between weekdays and weekends,
    and classifies occupancy into 'not_home', 'at_home_inactive', and 'at_home_active' states.

    Initialization Parameters
    ------------------------
    num_persons : int
        Number of occupants in the building.
    year : int
        Year for which the occupancy profile is generated (used for calendar and leap year handling).
    seed : int, optional
        Random seed for reproducibility. If None, results will vary on each run.

    Example
    -------
    >>> occ = OccupancyProfile(num_persons=3, year=2025, seed=42)
    >>> profile = occ.generate()
    """

    def __init__(self, num_persons: int, year: int, seed: Optional[int] = None):
        """
        Initialize the OccupancyProfile class.

        Parameters
        ----------
        num_persons : int
            Number of occupants in the building.
        year : int
            Year for which the occupancy profile is generated.
        seed : int, optional
            Random seed for reproducibility.
        """
        self.num_persons = num_persons
        self.year = year
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.index = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31 23:00", freq="H")
        self.profile: Optional[pd.DataFrame] = None

    def generate(self, seed: Optional[int] = None) -> pd.DataFrame:
        """
        Generate occupancy profile for the year with hourly resolution.
        Returns
        -------
        pd.DataFrame
        a DataFrame indexed by hourly timestamps, with columns:
        - 'n_home': number of persons at home
        - 'n_active': number of active persons at home
        - 'activity': main activity state (e.g., 'not_home', 'at_home_inactive', 'at_home_active')
        """
        # (optional) seed override for reproducible generation without changing object seed permanently
        if seed is not None:
            rng = np.random.default_rng(seed)
        else:
            rng = self.rng

        df = pd.DataFrame(index=self.index)
        df['weekday'] = df.index.weekday
        df['is_weekend'] = df['weekday'] >= 5

        # Define base probabilities for being at home and being active (hour x [weekday, weekend])
        # These can be refined or made person-specific
        # Example: [hour][0]=weekday, [hour][1]=weekend
        p_home = np.array([
            [0.1, 0.2],  # 0:00
            [0.1, 0.2],  # 1:00
            [0.1, 0.2],  # 2:00
            [0.1, 0.2],  # 3:00
            [0.2, 0.3],  # 4:00
            [0.3, 0.4],  # 5:00
            [0.5, 0.7],  # 6:00
            [0.7, 0.9],  # 7:00
            [0.8, 0.95], # 8:00
            [0.7, 0.95], # 9:00
            [0.6, 0.9],  # 10:00
            [0.6, 0.9],  # 11:00
            [0.6, 0.9],  # 12:00
            [0.6, 0.9],  # 13:00
            [0.6, 0.9],  # 14:00
            [0.6, 0.9],  # 15:00
            [0.6, 0.9],  # 16:00
            [0.7, 0.95], # 17:00
            [0.8, 0.95], # 18:00
            [0.9, 0.98], # 19:00
            [0.95, 0.99],# 20:00
            [0.98, 0.99],# 21:00
            [0.98, 0.99],# 22:00
            [0.95, 0.98],# 23:00
        ])
        p_active = np.array([
            [0.05, 0.1],  # 0:00
            [0.02, 0.05], # 1:00
            [0.01, 0.03], # 2:00
            [0.01, 0.03], # 3:00
            [0.01, 0.03], # 4:00
            [0.05, 0.1],  # 5:00
            [0.2, 0.3],   # 6:00
            [0.4, 0.5],   # 7:00
            [0.5, 0.6],   # 8:00
            [0.5, 0.6],   # 9:00
            [0.5, 0.6],   # 10:00
            [0.5, 0.6],   # 11:00
            [0.5, 0.6],   # 12:00
            [0.5, 0.6],   # 13:00
            [0.5, 0.6],   # 14:00
            [0.5, 0.6],   # 15:00
            [0.5, 0.6],   # 16:00
            [0.6, 0.7],   # 17:00
            [0.7, 0.8],   # 18:00
            [0.7, 0.8],   # 19:00
            [0.5, 0.6],   # 20:00
            [0.2, 0.3],   # 21:00
            [0.1, 0.2],   # 22:00
            [0.05, 0.1],  # 23:00
        ])

        n_home = []
        n_active = []
        activity = []

        for ts in df.itertuples():
            hour = ts.Index.hour
            weekend = ts.is_weekend
            # Choose probabilities for this hour and day type
            p_h = p_home[hour][1 if weekend else 0]
            p_a = p_active[hour][1 if weekend else 0]

            # For each person, decide if at home and if active
            persons_home = rng.binomial(self.num_persons, p_h)
            persons_active = rng.binomial(persons_home, p_a) if persons_home > 0 else 0

            n_home.append(persons_home)
            n_active.append(persons_active)

            if persons_home == 0:
                activity.append("not_home")
            elif persons_active == 0:
                activity.append("at_home_inactive")
            else:
                activity.append("at_home_active")

        df['n_home'] = n_home
        df['n_active'] = n_active
        df['activity'] = activity

        self.profile = df[['n_home', 'n_active', 'activity']]
        return self.profile

    def get_profile(self):
        """
        Returns the generated occupancy profile, or generates it if not already done.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by hourly timestamps, with columns:
            - 'n_home': number of persons at home
            - 'n_active': number of active persons at home
            - 'activity': main activity state (e.g., 'not_home', 'at_home_inactive', 'at_home_active')
        """
        if self.profile is None:
            return self.generate()
        return self.profile
    
def plot_weekly_active_occupants(profile, week_start='2025-01-01'):
    """
    Plot the number of active occupants for each day in a week, similar to Richardson et al. (2008).

    Parameters
    ----------
    profile : pd.DataFrame
        Occupancy profile DataFrame with 'n_active' column.
    week_start : str
        Start date of the week (YYYY-MM-DD).
    """
    week = pd.date_range(start=week_start, periods=7, freq='D')
    fig, axes = plt.subplots(4, 1, figsize=(6, 10), sharex=True)
    days = week[:4]  # Plot first 4 days for clarity, as in the Richardson figure

    for i, day in enumerate(days):
        day_profile = profile.loc[day.strftime('%Y-%m-%d')]
        axes[i].step(day_profile.index.hour, day_profile['n_active'], where='post', linewidth=2)
        axes[i].set_ylim(0, profile['n_active'].max() + 0.5)
        axes[i].set_xlim(0, 24)
        axes[i].set_ylabel('Number of\nactive occupants')
        axes[i].set_title(f"{day.strftime('%A, %Y-%m-%d')}")
        axes[i].grid(True, axis='y', linestyle='--', alpha=0.5)

    axes[-1].set_xlabel('Time of day (h)')
    plt.tight_layout()
    plt.show()

# usage:
if __name__ == "__main__":
    start_time = time.time()
    occ = OccupancyProfile(num_persons=3, year=2025, seed=42)
    profile = occ.generate()
    week_profile = profile.loc['2025-01-01 00:00':'2025-01-07 23:00']
    print("Total time taken: ", time.time() - start_time)
    print(week_profile)
    plot_weekly_active_occupants(profile, week_start='2025-01-01')
    print(profile.head(24))