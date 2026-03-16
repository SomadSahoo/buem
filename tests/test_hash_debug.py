"""Debug: check if cfg hash is deterministic across two invocations."""
import json
from pathlib import Path

from buem.integration.scripts.attribute_builder import AttributeBuilder
from buem.config.cfg_building import CfgBuilding
from buem.integration.scripts.result_cache import compute_cfg_hash

building = str(Path(__file__).resolve().parent.parent / "src" / "buem" / "data" / "buildings" / "dummy" / "building_01_small_residential.json")
with open(building) as f:
    payload = json.load(f)

feat = payload["features"][0]
payload_attrs = feat["properties"]["buem"]["building_attributes"]

# First build
builder1 = AttributeBuilder(payload_attrs=payload_attrs, building_id="test1")
merged1 = builder1.build()
cfg1 = CfgBuilding(merged1).to_cfg_dict()
h1 = compute_cfg_hash(cfg1)

# Second build (same process)
builder2 = AttributeBuilder(payload_attrs=payload_attrs, building_id="test2")
merged2 = builder2.build()
cfg2 = CfgBuilding(merged2).to_cfg_dict()
h2 = compute_cfg_hash(cfg2)

print(f"Hash 1: {h1}")
print(f"Hash 2: {h2}")
print(f"Same:   {h1 == h2}")

# Check what differs
if h1 != h2:
    for k in cfg1:
        import pandas as pd
        import numpy as np
        v1, v2 = cfg1[k], cfg2[k]
        if isinstance(v1, pd.DataFrame):
            if not v1.equals(v2):
                print(f"  DIFF: {k} (DataFrame)")
        elif isinstance(v1, pd.Series):
            if not v1.equals(v2):
                print(f"  DIFF: {k} (Series)")
        elif isinstance(v1, np.ndarray):
            if not np.array_equal(v1, v2):
                print(f"  DIFF: {k} (ndarray)")
        elif isinstance(v1, dict):
            if v1 != v2:
                print(f"  DIFF: {k} (dict)")
        else:
            if v1 != v2:
                print(f"  DIFF: {k}: {v1!r} vs {v2!r}")
