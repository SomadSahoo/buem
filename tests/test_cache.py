"""Quick smoke test: feather cache + result cache."""
import json, time, os
from pathlib import Path

from buem.integration.scripts.geojson_processor import GeoJsonProcessor

building = str(Path(__file__).resolve().parent.parent / "src" / "buem" / "data" / "buildings" / "dummy" / "building_01_small_residential.json")
with open(building) as f:
    payload = json.load(f)

# First run (cold — may create feather + result caches)
t0 = time.time()
proc = GeoJsonProcessor(payload=payload, include_timeseries=False)
resp = proc.process()
t1 = time.time()
meta = resp["metadata"]
print(f"First run:  {t1 - t0:.2f}s  ({meta['successful_features']}/{meta['total_features']} OK)")

# Second run (should hit result cache)
t2 = time.time()
proc2 = GeoJsonProcessor(payload=payload, include_timeseries=False)
resp2 = proc2.process()
t3 = time.time()
meta2 = resp2["metadata"]
print(f"Second run: {t3 - t2:.2f}s  ({meta2['successful_features']}/{meta2['total_features']} OK)")

# Verify feather cache exists
feather_path = os.path.join("src", "buem", "data", "weather", "COSMO_Year__ix_390_650_processed.feather")
print(f"Feather cache exists: {os.path.exists(feather_path)}")

# Verify result cache dir
from buem.integration.scripts.result_cache import CACHE_DIR
cache_dir = str(CACHE_DIR)
if os.path.isdir(cache_dir):
    pkl_files = [f for f in os.listdir(cache_dir) if f.endswith(".pkl")]
    print(f"Result cache files: {len(pkl_files)}")
else:
    print("Result cache dir not yet created")
