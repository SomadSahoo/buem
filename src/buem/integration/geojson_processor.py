"""
GeoJson_Processor

Processes incoming GeoJSON (Feature or FeatureCollection) or a plain JSON
containing a top-level "buem" object. For each feature it:
 - extracts building_attributes (optionally enriches via db_fetcher),
 - requires structured `components` (no legacy flat-key inference),
 - builds a normalized configuration via CfgBuilding,
 - validates it (validate_cfg),
 - runs the BUEM thermal model (run_model),
 - writes a compact thermal_load_profile back into feature.properties.buem.

By default only compact summaries are embedded (start_time, end_time,
n_points, totals, peaks). Set include_timeseries=True to embed full
time-series arrays (may be large for 8760 points).
"""
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import time
import os
import uuid
import gzip
import pandas as pd
import numpy as np
import traceback
from flask import current_app
import logging

from buem.config.cfg_building import CfgBuilding
from buem.main import run_model
from buem.config.validator import validate_cfg

DEFAULT_RESULT_SAVE = None  # set to a path string to persist last result

logger = logging.getLogger(__name__)

class GeoJsonProcessor:
    def __init__(
        self,
        payload: Dict[str, Any],
        include_timeseries: bool = False,
        db_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
        result_save_path: Optional[str] = DEFAULT_RESULT_SAVE,
        result_save_dir: Optional[str] = None,  # dir to save large timeseries files
    ):
        self.payload = payload
        self.include_timeseries = include_timeseries
        self.db_fetcher = db_fetcher
        self.result_save_path = result_save_path
        self.result_save_dir = result_save_dir or os.environ.get("BUEM_RESULTS_DIR", r"C:\test\buem\results")

    # ---------- payload detection / normalization ----------
    def _is_feature_collection(self, doc: Dict[str, Any]) -> bool:
        return doc.get("type") == "FeatureCollection" and isinstance(doc.get("features"), list)

    def _is_feature(self, doc: Dict[str, Any]) -> bool:
        return doc.get("type") == "Feature" and "properties" in doc

    def _has_top_buem(self, doc: Dict[str, Any]) -> bool:
        return "buem" in doc

    def _iter_features(self) -> List[Dict[str, Any]]:
        """
        Normalize payload into list of Feature dicts.
        Raises ValueError if payload cannot be interpreted.
        """
        if self._is_feature_collection(self.payload):
            return list(self.payload["features"])
        if self._is_feature(self.payload):
            return [self.payload]
        if self._has_top_buem(self.payload):
            # wrap a top-level buem object into a single Feature
            return [{
                "type": "Feature",
                "id": self.payload.get("id"),
                "geometry": self.payload.get("geometry"),
                "properties": {"buem": self.payload["buem"]}
            }]
        raise ValueError("Payload is not a Feature, FeatureCollection, or a top-level buem object")

    # ---------- core processing ----------
    def process(self) -> Dict[str, Any]:
        """
        Process all features and return a FeatureCollection with updated
        properties.buem.thermal_load_profile for each feature.
        """
        start_all = time.time()
        features = self._iter_features()
        out_features = []
        for feat in features:
            try:
                processed = self._process_single_feature(feat)
                out_features.append(processed)
            except Exception as exc:
                # attach structured error to the feature and continue
                props = feat.setdefault("properties", {})
                buem_obj = props.setdefault("buem", {})
                err_info = {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                # include traceback when Flask debug is enabled for easier debugging
                try:
                    app_debug = bool(current_app.debug)
                except Exception:
                    app_debug = False
                if app_debug:
                    err_info["traceback"] = traceback.format_exc()
                buem_obj["thermal_load_profile"] = err_info
                out_features.append(feat)

        out = {
            "type": "FeatureCollection",
            "features": out_features,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "processing_elapsed_s": round(time.time() - start_all, 3),
        }

        if self.result_save_path:
            try:
                with open(self.result_save_path, "w", encoding="utf-8") as f:
                    json.dump(out, f, indent=2, default=str)
            except Exception:
                # best-effort persistence only
                pass
        return out

    def _save_timeseries_file(self, times, heating, cooling) -> str:
        """
        Save times, heating, cooling as gzipped JSON in result_save_dir.
        Returns filename (basename). Caller maps to /api/files/<filename>.
        """
        Path(self.result_save_dir).mkdir(parents=True, exist_ok=True)
        fname = f"buem_ts_{uuid.uuid4().hex}.json.gz"
        full = Path(self.result_save_dir) / fname
        payload = {
            "index": [ts.isoformat() for ts in list(times)],
            "heat": [float(x) for x in list(heating)],
            "cool": [float(x) for x in list(cooling)],
        }
        with gzip.open(full, "wt", encoding="utf-8") as gz:
            json.dump(payload, gz, indent=None)
        return fname

    def _process_single_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single GeoJSON Feature.

        Steps:
         - read properties.buem.building_attributes
         - optionally enrich attributes via db_fetcher(building_id)
         - require structured 'components' in the attributes (no legacy keys)
         - normalize with CfgBuilding and validate
         - run run_model(cfg_dict)
         - write summary (and optionally full time-series) into properties.buem.thermal_load_profile

        Returns modified feature dict.
        """
        props = feature.setdefault("properties", {})
        buem = props.get("buem")
        if not buem:
            raise ValueError("Feature missing properties.buem")

        # gather building attributes, allow db enrichment if available
        b_attrs = buem.get("building_attributes", {}) or {}
        building_id = feature.get("id") or b_attrs.get("building_id") or buem.get("building_id")

        if self.db_fetcher and building_id:
            try:
                fetched = self.db_fetcher(building_id) or {}
            except Exception:
                fetched = {}
            # payload attributes override fetched defaults
            merged_attrs = {**fetched, **b_attrs}
        else:
            merged_attrs = dict(b_attrs)  # make a shallow copy

        # ---- Enforce structured configuration: require 'components' object ----
        if "components" not in merged_attrs or not isinstance(merged_attrs["components"], dict):
            raise ValueError(
                "Missing required 'components' object in building_attributes. "
                "Legacy flat-key inputs (A_ref, U_Walls, ...) are not accepted. "
                "Please provide a structured 'components' dictionary per documentation."
            )

        # ---- Normalization: convert plain lists to pandas Series/DataFrame where appropriate ----
        # Convert building-level time series (commonly 'elecLoad', 'Q_ig') from lists -> pd.Series
        for k in ("elecLoad", "Q_ig", "internalGains", "Q_int"):
            if k in merged_attrs and isinstance(merged_attrs[k], list):
                merged_attrs[k] = pd.Series(merged_attrs[k])

        # If a weather object is present inside buem (not necessarily in building_attributes),
        # ensure weather columns are DataFrame/Series with proper index if given as lists.
        weather_obj = buem.get("weather") or merged_attrs.get("weather")
        if isinstance(weather_obj, dict):
            idx = None
            if "index" in weather_obj and isinstance(weather_obj["index"], list):
                try:
                    idx = pd.to_datetime(weather_obj["index"])
                except Exception:
                    idx = None
            df_cols = {}
            for col in ("T", "GHI", "DNI", "DHI"):
                if col in weather_obj and isinstance(weather_obj[col], list):
                    ser = pd.Series(weather_obj[col], index=idx) if idx is not None else pd.Series(weather_obj[col])
                    df_cols[col] = ser
            if df_cols:
                weather_df = pd.DataFrame(df_cols)
                if idx is not None:
                    weather_df.index = idx
                merged_attrs["weather"] = weather_df

        # Pass the Python object straight into CfgBuilding so pandas objects are preserved.
        # CfgBuilding now accepts dicts (and still accepts JSON strings for backwards compatibility).
        cfgb = CfgBuilding(merged_attrs)
        # Get the normalized cfg dict that the model expects
        cfg = cfgb.to_cfg_dict()

        # Log prepared cfg keys safely (Flask logger preferred)
        try:
            current_app.logger.debug("Prepared cfg keys: %s", sorted(cfg.keys()))
        except Exception:
            logger.debug("Prepared cfg keys: %s", sorted(cfg.keys()))

        # Run validator and catch any unexpected validator failures.
        try:
            issues = validate_cfg(cfg)
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError("validate_cfg raised an exception:\n" + tb) from exc

        if issues:
            raise ValueError("Configuration validation failed: " + "; ".join(issues))

        # run model (use use_milp if requested in buem)
        use_milp = bool(buem.get("use_milp", False))
        res = run_model(cfg, plot=False, use_milp=use_milp)

        times = res["times"]
        heating = np.asarray(res["heating"])
        cooling = np.asarray(res["cooling"])

        # build compact profile
        profile: Dict[str, Any] = {
            "start_time": times[0].isoformat(),
            "end_time": times[-1].isoformat(),
            "n_points": int(len(times)),
            "heating_total_kWh": float(np.sum(heating)),
            "cooling_total_kWh": float(np.sum(np.abs(cooling))),
            "heating_peak_kW": float(np.max(heating)) if heating.size else 0.0,
            "cooling_peak_kW": float(np.max(np.abs(cooling))) if cooling.size else 0.0,
            "elapsed_s": float(res.get("elapsed_s", 0.0)),
        }

        if self.include_timeseries:
            if self.result_save_dir:
                try:
                    fname = self._save_timeseries_file(times, heating, cooling)
                    profile["timeseries_file"] = f"/api/files/{fname}"
                except Exception:
                    profile["index"] = [ts.isoformat() for ts in list(times)]
                    profile["heat"] = [float(x) for x in heating.tolist()]
                    profile["cool"] = [float(x) for x in cooling.tolist()]
            else:
                profile["index"] = [ts.isoformat() for ts in list(times)]
                profile["heat"] = [float(x) for x in heating.tolist()]
                profile["cool"] = [float(x) for x in cooling.tolist()]

        # embed results into feature
        out_buem = dict(buem)
        out_buem["building_attributes"] = merged_attrs
        out_buem["thermal_load_profile"] = profile
        props["buem"] = out_buem
        return feature