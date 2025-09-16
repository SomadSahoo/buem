import os
from pathlib import Path
import pandas as pd

class CsvWeatherData:
    def __init__(self, csv_relative_path=None, cache_path=None):
        buem_root = Path(__file__).parent.parent
        self.csv_path = buem_root / csv_relative_path
        self.cache_path = buem_root / cache_path if cache_path else None
        self.df = self._load_and_prepare()

    def _load_and_prepare(self):
        if self.cache_path and os.path.exists(self.cache_path):
            return pd.read_feather(self.cache_path)
        df = pd.read_csv(self.csv_path)
        df.set_index(df.columns[0], inplace=True)
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = 'datetime'
        if self.cache_path:
            df.reset_index().to_feather(self.cache_path)
        return df       
    
    def extract_weather_columns(self):
        """Extracts required weather columns and renames them."""
        if self.df is None:
            raise ValueError("CSV data not loaded. Call read_csv() first.")
        # Map CSV columns to desired names
        columns_map = {
            "T": "T",
            "GHI": "GHI",
            "DNI": "DNI",
            "DHI": "DHI"
        }
        self.df = self.df[list(columns_map.keys())]
        self.df.rename(columns=columns_map, inplace=True)
        return self.df
    
    def get_hourly(self, method='mean'):
        """Return hourly resampled data."""
        if method == 'mean':
            return self.df.resample('H').mean()
        elif method == 'interpolate':
            return self.df.resample('H').interpolate()
        else:
            raise ValueError("Unknown method")

    def get_daily(self, method='mean'):
        """Return daily resampled data."""
        if method == 'mean':
            return self.df.resample('D').mean()
        else:
            raise ValueError("Unknown method")

if __name__=="__main__":
    import time
    start_time = time.time()
    loader = CsvWeatherData("data\\COSMO_Year__ix_389_660.csv")
    df = loader.extract_weather_columns()
    print(f"total time taken: {time.time() - start_time}")
    print(f"df: {df}")