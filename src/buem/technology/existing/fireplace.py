from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Mapping, Any, TYPE_CHECKING
import pandas as pd
import numpy as np

if TYPE_CHECKING:
    from buem.occupancy.occupancy_profile import OccupancyProfile  # type: ignore
    from buem.weather.from_csv import CsvWeatherData  # type: ignore




@dataclass
class ExistingFireplace:
    """
    Simple single-fireplace model that produces an hourly on/off profile
    (0/1) based on occupancy activity (weekly-normalised peaks) and external
    temperature.

    Behaviour summary
    - Uses an OccupancyProfile instance to obtain hourly 'n_active'.
      Activity is normalised by the weekly maximum (per-week) so that hours
      with relatively high activity in a given week get higher weight.
    - Uses CsvWeatherData to obtain hourly external temperature (column 'T').
    - If temperature <= T_on: fireplace is forced ON (1.0).
    - If temperature >= T_off: fireplace is forced OFF (0.0).
    - For temperatures between T_on and T_off: probability of being ON is
      activity_factor * linear_temp_factor. Actual hourly state is sampled
      with a RNG (seedable).
    - Single fireplace only (no n_ovens, no fullload_hours).
    """

    is_fireplace: bool = True
    T_on: float = 5.0   # below or equal -> definitely on
    T_off: float = 21.0  # at/above -> definitely off (per requirement)
    seed: Optional[int] = None

    def is_available(self, features: Mapping[str, Any]) -> bool:
        """Check availability flag ('is_fireplace') in provided features mapping."""
        return bool(features.get("is_fireplace", self.is_fireplace))

    def generate_profile(
        self,
        occupancy: "OccupancyProfile", 
        weather: "CsvWeatherData",
    ) -> pd.Series:
        """
        Generate hourly fireplace on/off profile.

        Parameters
        ----------
        occupancy : OccupancyProfile
            OccupancyProfile instance for the dwelling (uses .get_profile() or .generate()).
        weather : CsvWeatherData
            CsvWeatherData instance (uses extract_weather_columns() to obtain 'T').

        Returns
        -------
        pd.Series
            Hourly on/off profile (float 0.0 or 1.0) indexed by datetime.
        """
        if not self.is_fireplace:
            raise ValueError("Fireplace not available (is_fireplace=False).")

        # Validate by required interface rather than concrete class identity.
        if not hasattr(occupancy, "get_profile"):
            raise RuntimeError("occupancy must provide .get_profile()")
        if not hasattr(weather, "extract_weather_columns"):
            raise RuntimeError("weather must provide .extract_weather_columns()")

        # ensure occupancy profile exists
        occ_df = occupancy.get_profile()
        if "n_active" not in occ_df.columns:
            raise KeyError("Occupancy profile must contain 'n_active' column.")

        # weekly-normalised activity: n_active / weekly_max -> [0..1]
        n_active = occ_df["n_active"].astype(float)
        weekly_max = n_active.resample("W").transform("max")
        # avoid division by zero
        activity_factor = (n_active / weekly_max).fillna(0.0).clip(0.0, 1.0)

        # get external temperature series (assumes column 'T' present)
        weather_df = weather.extract_weather_columns()
        if "T" not in weather_df.columns:
            raise KeyError("Weather data must contain column 'T' for external temperature.")
        temp = weather_df["T"].reindex(activity_factor.index).fillna(method="ffill").fillna(method="bfill")

        # Masks and factors
        force_on_mask = temp <= self.T_on
        force_off_mask = temp >= self.T_off
        between_mask = (~force_on_mask) & (~force_off_mask)

        # temp factor: 1 at T_on, 0 at T_off, linear in between
        temp_factor = pd.Series(0.0, index=temp.index)
        if (self.T_off - self.T_on) > 0:
            temp_factor.loc[between_mask] = ((self.T_off - temp.loc[between_mask]) /
                                            (self.T_off - self.T_on)).clip(0.0, 1.0)
        temp_factor.loc[force_on_mask] = 1.0
        temp_factor.loc[force_off_mask] = 0.0

        # probability (0..1): activity-weighted unless forced on/off
        prob = (activity_factor * temp_factor).astype(float)
        prob.loc[force_on_mask] = 1.0
        prob.loc[force_off_mask] = 0.0

        # stochastic draw for each hour (reproducible with seed)
        rng = np.random.default_rng(self.seed)
        draws = rng.random(len(prob))
        on_series = (draws < prob.values).astype(float)

        profile = pd.Series(on_series, index=prob.index, name="fireplace")
        # ensure forced values respected (protect against any numerical issues)
        profile[force_on_mask] = 1.0
        profile[force_off_mask] = 0.0

        return profile

    def generate_profile_from_sources(
        self,
        occupancy: Optional["OccupancyProfile"] = None,
        occupancy_kwargs: Optional[Mapping[str, Any]] = None,
        weather: Optional["CsvWeatherData"] = None,
        weather_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> pd.Series:
        """
        Convenience wrapper: accept either ready instances or kwargs to construct
        OccupancyProfile and CsvWeatherData, then delegate to generate_profile.

        Parameters
        - occupancy: OccupancyProfile instance or None
        - occupancy_kwargs: dict for OccupancyProfile(num_persons, year, seed)
        - weather: CsvWeatherData instance or None
        - weather_kwargs: dict for CsvWeatherData(csv_relative_path, cache_path)

        Returns
        - pd.Series: fireplace profile (same as generate_profile)
        """
        if occupancy is None:
            if OccupancyProfile is None:
                raise RuntimeError("OccupancyProfile not importable")
            if not occupancy_kwargs:
                raise ValueError("occupancy_kwargs required when occupancy is not provided")
            occupancy = OccupancyProfile(**occupancy_kwargs)

        if weather is None:
            if CsvWeatherData is None:
                raise RuntimeError("CsvWeatherData not importable")
            if not weather_kwargs:
                raise ValueError("weather_kwargs required when weather is not provided")
            weather = CsvWeatherData(**weather_kwargs)

        return self.generate_profile(occupancy=occupancy, weather=weather)